"""OD-011 rev-2 demonstration of the C1 PIPELINE, on a real model.

The OD-022 sweep was not enough, and the reason is recorded in my own honesty
note: C1's flatten column there was exactly 0.000000 because the minuend and the
subtrahend were the same deterministic function, so the cancellation was BY
IDENTITY. The sweep therefore carries no information about C1's flatten
robustness. This file fills that cell.

What is validated here is the DECISION RULE, not the functional form, and it is
validated by running the actual pipeline on the actual model, with the actual
null subtraction.

  no_op                   patch the recipient's own state -> exactly 0
  random_vector           norm-matched Gaussian, through the pipeline -> approx 0
  flatten_only            a flattening patch, through the pipeline -> approx 0
                          THE CELL THE SWEEP CANNOT SEE: here the true patch and
                          the null flatten by DIFFERENT amounts, drawn
                          independently, so no identity cancellation is available
  full_donor              transplant the donor's whole state -> CAUSALLY_USED
  attenuated_transfer     a partial transplant -> significantly positive AND
                          strictly below full_donor

The last two are what OD-011 revision 2 requires: a rule that can only return
the negative is as uninformative as one that can only return the positive.

On any failure C1 is out, the surviving candidate count falls to zero, and the
phase stops. C1 is not repaired and no candidate is added.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent

#: "Approximately zero" is decided by the registered decision rule itself: the
#: cluster-bootstrap interval must contain zero at every layer. No separate
#: numeric tolerance is invented, because a tolerance chosen after the failure it
#: judges is not evidence.
BOOTSTRAP_RESAMPLES = 4000
BOOTSTRAP_SEED = 20260829
ATTENUATION = 0.5

REQUIRED = {
    "no_op": "EXACTLY_ZERO",
    "random_vector": "APPROXIMATELY_ZERO",
    "flatten_only": "APPROXIMATELY_ZERO",
    "full_donor": "CAUSALLY_USED",
    "attenuated_transfer": "POSITIVE_AND_BELOW_FULL",
}


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def bootstrap(values_by_cluster, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED):
    import numpy as np

    clusters = sorted(values_by_cluster)
    sums = np.array([float(sum(values_by_cluster[c])) for c in clusters])
    counts = np.array([float(len(values_by_cluster[c])) for c in clusters])
    if counts.sum() == 0:
        raise RuntimeError("nothing to bootstrap")
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(clusters), size=(resamples, len(clusters)))
    means = np.sort(sums[draws].sum(axis=1) / counts[draws].sum(axis=1))
    return {
        "mean": float(sums.sum() / counts.sum()),
        "lcb": float(np.percentile(means, 2.5)),
        "ucb": float(np.percentile(means, 97.5)),
        "n_clusters": len(clusters),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--object", required=True)
    parser.add_argument("--inclusion", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--batch", type=int, default=48)
    parser.add_argument("--replicates", type=int, default=20)
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    pipeline = load("c1_pipeline", "c1_pipeline.py")
    started = time.time()

    obj = json.loads(Path(args.object).read_text(encoding="utf-8"))
    inclusion = json.loads(Path(args.inclusion).read_text(encoding="utf-8"))
    keep = {row["unit_id"] for row in inclusion["correct_both_units_detail"]}
    units = [u for u in obj["units"] if u["unit_id"] in keep][: args.limit]

    AutoTokenizer.from_pretrained(args.model_dir, trust_remote_code=False, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir, dtype=torch.bfloat16, trust_remote_code=False,
        attn_implementation="eager",
    )
    model.to("cuda:0")
    model.eval()
    harness = pipeline.Harness(model)

    ids_by_name = {}
    for unit in obj["units"]:
        ids_by_name[unit["donor"]] = unit["donor_ids"]
        ids_by_name[unit["recipient"]] = unit["recipient_ids"]

    site = pipeline.DECISIVE_SITE
    half = args.replicates // 2
    cases: dict[str, dict[str, dict]] = {name: {} for name in REQUIRED}

    for unit in units:
        caches = {}
        for name in (unit["donor"], unit["recipient"]):
            ids = torch.tensor(ids_by_name[name], dtype=torch.long, device="cuda:0")
            states, _ = harness.capture_at_width(ids, args.batch, torch)
            caches[name] = {"states": states, "ids": ids}
        donor = caches[unit["donor"]]
        recipient = caches[unit["recipient"]]

        donor_tok = unit["donor_answer_token_ids"]
        recipient_tok = unit["recipient_answer_token_ids"]
        gather = torch.tensor(
            list(donor_tok) + list(recipient_tok), dtype=torch.long, device="cuda:0"
        )
        split = len(donor_tok)
        index = torch.tensor(
            unit["sites"][site], dtype=torch.long, device="cuda:0"
        )
        every = sorted({p for ps in unit["sites"].values() for p in ps})
        every_index = torch.tensor(every, dtype=torch.long, device="cuda:0")

        generator = torch.Generator(device="cuda:0")
        for layer in harness.layers:
            own = recipient["states"][layer].index_select(0, index)
            donor_slice = donor["states"][layer].index_select(0, index)

            jobs = [
                {"layer": layer, "index": index, "values": own},
                {
                    "layer": layer,
                    "index": every_index,
                    "values": donor["states"][layer].index_select(0, every_index),
                },
            ]
            labels = ["BASELINE", "FULL_REF"]

            # the case patches
            jobs.append({"layer": layer, "index": index, "values": own})
            labels.append("no_op")

            generator.manual_seed(pipeline.stable_seed(unit["unit_id"], "case", layer))
            jobs.append(
                {
                    "layer": layer,
                    "index": index,
                    "values": pipeline.destructive_values(
                        own, generator, "resample", torch
                    ),
                }
            )
            labels.append("random_vector")

            # flatten with an INDEPENDENT magnitude from the null's, so no
            # identity cancellation is available - the cell the sweep cannot see
            jobs.append(
                {
                    "layer": layer,
                    "index": index,
                    "values": (own.float() * 0.02).to(own.dtype),
                }
            )
            labels.append("flatten_only")

            jobs.append({"layer": layer, "index": index, "values": donor_slice})
            labels.append("full_donor")

            jobs.append(
                {
                    "layer": layer,
                    "index": index,
                    "values": (
                        (1.0 - ATTENUATION) * own.float()
                        + ATTENUATION * donor_slice.float()
                    ).to(own.dtype),
                }
            )
            labels.append("attenuated_transfer")

            # the null subtrahend, drawn independently of every case
            for replicate in range(half):
                generator.manual_seed(
                    pipeline.stable_seed(unit["unit_id"], "null", layer, replicate)
                )
                jobs.append(
                    {
                        "layer": layer,
                        "index": index,
                        "values": pipeline.destructive_values(
                            own, generator, "resample", torch
                        ),
                    }
                )
                labels.append(f"NULL_{replicate}")

            gaps = harness.run_jobs(
                recipient["ids"], jobs, gather, split, args.batch, torch
            )
            by_label = dict(zip(labels, gaps))
            baseline = by_label["BASELINE"]
            full_ref = by_label["FULL_REF"]
            nulls = [by_label[f"NULL_{r}"] for r in range(half)]

            for name in REQUIRED:
                value = pipeline.c1_effect(by_label[name], baseline, full_ref, nulls)
                if value is not None:
                    cases[name].setdefault(str(layer), {}).setdefault(
                        unit["cluster_id"], []
                    ).append(value)
        del caches

    results: dict[str, dict] = {}
    all_passed = True
    for name, requirement in REQUIRED.items():
        stats = {
            layer: bootstrap(bucket)
            for layer, bucket in sorted(
                cases[name].items(), key=lambda kv: int(kv[0])
            )
        }
        means = [s["mean"] for s in stats.values()]
        worst = max(abs(m) for m in means)
        contains_zero = all(s["lcb"] <= 0.0 <= s["ucb"] for s in stats.values())
        any_positive = any(s["lcb"] > 0.0 for s in stats.values())

        if requirement == "EXACTLY_ZERO":
            passed = worst == 0.0
            detail = f"worst |mean| {worst:.3e}, required exactly 0"
        elif requirement == "APPROXIMATELY_ZERO":
            passed = contains_zero
            detail = (
                f"worst |mean| {worst:.6f}; every layer's 95% interval contains "
                f"zero: {contains_zero}"
            )
        elif requirement == "CAUSALLY_USED":
            passed = any_positive
            detail = (
                f"max mean {max(means):.6f}; at least one layer strictly above "
                f"zero: {any_positive}"
            )
        elif requirement == "POSITIVE_AND_BELOW_FULL":
            full_means = [
                bootstrap(bucket)["mean"]
                for _, bucket in sorted(
                    cases["full_donor"].items(), key=lambda kv: int(kv[0])
                )
            ]
            below = max(means) < max(full_means)
            passed = any_positive and below
            detail = (
                f"max mean {max(means):.6f} vs full_donor {max(full_means):.6f}; "
                f"positive: {any_positive}, strictly below full: {below}"
            )
        else:
            raise RuntimeError(requirement)

        all_passed = all_passed and passed
        results[name] = {
            "must_be": requirement,
            "per_layer": stats,
            "worst_abs_mean": worst,
            "max_mean": max(means),
            "every_layer_interval_contains_zero": contains_zero,
            "any_layer_strictly_positive": any_positive,
            "detail": detail,
            "passed": passed,
        }
        print(f"  {name:22} must_be={requirement:24} "
              f"{'PASS' if passed else 'FAIL'}   {detail}")

    report = {
        "schema_version": "study5-p0c2-c1-nonvacuity-v1",
        "rule": "OD-011 revision 2",
        "what_is_validated": "the DECISION RULE running through the real C1 pipeline, not the functional form",
        "why_the_sweep_was_not_enough": (
            "C1's flatten column in the OD-022 sweep was exactly 0.000000 because "
            "the minuend and the subtrahend were the same deterministic function, "
            "so the cancellation was BY IDENTITY and the sweep carried no "
            "information about that cell"
        ),
        "what_the_flatten_only_case_adds": (
            "in the real pipeline the case patch and the null are drawn "
            "independently and flatten by different amounts, so no identity "
            "cancellation is available; this is the cell the sweep cannot see"
        ),
        "model_dir": args.model_dir,
        "n_units": len(units),
        "replicates_used_as_subtrahend": half,
        "attenuation": ATTENUATION,
        "cases": results,
        "all_passed": all_passed,
        "consequence_of_failure": (
            "C1 is out, the surviving candidate count falls to zero, and the "
            "phase stops; C1 is not repaired and no candidate is added"
        ),
        "wall_seconds": round(time.time() - started, 3),
        "claim_ceiling": "A governance demonstration. It licenses no claim.",
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))
    if not all_passed:
        print("P0C2-CHECK-C1-NONVACUITY FAILED", file=sys.stderr)
        return 1
    print("P0C2-CHECK-C1-NONVACUITY PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
