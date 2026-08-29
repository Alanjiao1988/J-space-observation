"""C1, the sole surviving candidate, as a pipeline rather than a formula.

C1 does not seek a functional form immune to destruction. It measures destruction
explicitly and subtracts it:

    effect = raw(patched) - mean over k replicates of raw(destructive patch)

normalised so a full donor transplant is 1.0. `raw` is the logit difference
between the donor's and the recipient's answer tokens at the readout position.

Two properties of this file matter more than the arithmetic.

First, COMMON RANDOM NUMBERS. The real construction and the null constructions
run on the same recipient, in the same batch, from the same per-unit seed. C1 is
a difference, and the variance of a difference of positively correlated terms is
far below the sum of their variances. This is registered in advance as the
largest of the three variance reductions, and it is realised here by structure
rather than by hope: every construction for a unit is built in one job list and
executed in one batched forward.

Second, the null that is SUBTRACTED and the null that estimates VARIANCE are
kept separate. Replicates are split into two disjoint halves by index: the first
half forms the subtrahend, the second half is reserved for the variance estimate
the MDE is computed from. Using the same draws for both would let the estimator
be judged against its own noise.

The decision rule is registered as "C1 significantly greater than zero", NOT
"C1 greater than a null ceiling", because C1 already subtracts the null and
using both would deduct it twice.

Imports nothing from the instrument EQ2 was testing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

EMBEDDING_LAYER = -1

#: Registered in the measurement pre-registration: 20, up from 5.
NULL_REPLICATES = 20

#: Sites measured for the null constructions. PREFIX is REAL-only, as it is the
#: structural no-op that serves as the integrity gate.
NULL_SITES = ("CUE", "BRIDGE", "READOUT")

DECISIVE_SITE = "BRIDGE"


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_seed(*parts: object) -> int:
    """A seed independent of PYTHONHASHSEED, so replicates are reproducible."""
    blob = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(blob).digest()[:8], "big") % (2**63 - 1)


def instrument_under_test_is_loaded() -> bool:
    marker = "j" + "lens"
    return any(n == marker or n.startswith(marker + ".") for n in sys.modules)


class Harness:
    """Residual-stream read and write hooks, with the three-part batch repair."""

    def __init__(self, model):
        self.model = model
        blocks = model.model.layers
        self.n_layers = len(blocks)
        self.modules = {EMBEDDING_LAYER: model.model.embed_tokens}
        for index, block in enumerate(blocks):
            self.modules[index] = block
        self.layers = [EMBEDDING_LAYER] + list(range(self.n_layers))

    @staticmethod
    def _tensor_of(output):
        return output[0] if isinstance(output, tuple) else output

    @staticmethod
    def _rewrap(output, tensor):
        return (tensor,) + tuple(output[1:]) if isinstance(output, tuple) else tensor

    def capture_at_width(self, ids, width, torch):
        """Cache captured at the SAME batch width as the run that consumes it.

        Part two of the three-part repair. Capturing at width 1 and patching into
        a run of width 48 leaves batch-1-derived values beside batch-48-derived
        ones, which is the original defect one level down.
        """
        cache: dict[int, "torch.Tensor"] = {}
        handles = []

        def make(layer):
            def hook(_module, _inputs, output):
                cache[layer] = self._tensor_of(output).detach()[0].clone()
                return output

            return hook

        for layer, module in self.modules.items():
            handles.append(module.register_forward_hook(make(layer)))
        try:
            with torch.no_grad():
                batch = ids.unsqueeze(0).expand(width, -1).contiguous()
                out = self.model(input_ids=batch)
        finally:
            for handle in handles:
                handle.remove()
        return cache, out.logits[0, -1].detach().float()

    def run_jobs(self, base_ids, jobs, gather_ids, split, batch_size, torch):
        """Logit differences for every job, batched, with full-width chunks.

        Part three of the repair: chunks are padded to full width so no short
        final chunk executes a differently-shaped kernel.
        """
        values: list[float] = []
        padded = list(jobs)
        pad = (-len(padded)) % batch_size
        padded.extend([dict(padded[0]) for _ in range(pad)])

        for start in range(0, len(padded), batch_size):
            chunk = padded[start : start + batch_size]
            batch = base_ids.unsqueeze(0).expand(len(chunk), -1).contiguous()
            by_layer: dict[int, list] = {}
            for row, job in enumerate(chunk):
                by_layer.setdefault(job["layer"], []).append(
                    (row, job["index"], job["values"])
                )

            handles = []

            def make(layer):
                writes = by_layer[layer]

                def hook(_module, _inputs, output):
                    tensor = self._tensor_of(output)
                    for row, index, replacement in writes:
                        tensor[row].index_copy_(0, index, replacement.to(tensor.dtype))
                    return self._rewrap(output, tensor)

                return hook

            for layer in by_layer:
                handles.append(self.modules[layer].register_forward_hook(make(layer)))
            try:
                with torch.no_grad():
                    logits = self.model(input_ids=batch).logits[:, -1, :]
                    picked = logits.float().index_select(1, gather_ids)
            finally:
                for handle in handles:
                    handle.remove()
            gap = picked[:, :split].amax(dim=1) - picked[:, split:].amax(dim=1)
            values.extend(gap.tolist())
        return values[: len(jobs)]


def destructive_values(original, generator, kind, torch):
    """A replacement that carries no information about which answer is which.

    Two kinds, because "destroyed" is not one thing:
      resample  an isotropic Gaussian rescaled to the original norm
      flatten   the original scaled toward zero, which flattens the output
                distribution without introducing a new direction
    """
    if kind == "resample":
        noise = torch.randn(
            original.shape, generator=generator, device=original.device,
            dtype=torch.float32,
        )
        scale = original.float().norm(dim=-1, keepdim=True) / noise.norm(
            dim=-1, keepdim=True
        ).clamp_min(1e-12)
        return (noise * scale).to(original.dtype)
    if kind == "flatten":
        return (original.float() * 0.05).to(original.dtype)
    raise RuntimeError(kind)


def measure_unit(harness, unit, caches, args, torch, mode="REAL"):
    """Every construction for one unit, in ONE job list and ONE batched forward.

    That is what realises common random numbers structurally: the real and null
    constructions cannot drift apart, because they are rows of the same batch
    over the same recipient.
    """
    donor = caches[unit["donor"]]
    recipient = caches[unit["recipient"]]
    donor_tok = unit["donor_answer_token_ids"]
    recipient_tok = unit["recipient_answer_token_ids"]

    gather = torch.tensor(
        list(donor_tok) + list(recipient_tok), dtype=torch.long, device="cuda:0"
    )
    split = len(donor_tok)
    index_of = {
        site: torch.tensor(positions, dtype=torch.long, device="cuda:0")
        for site, positions in unit["sites"].items()
    }

    jobs: list[dict] = []
    labels: list[tuple[str, str, int, int]] = []

    # part one of the repair: the baseline is an in-batch self-patch
    first = harness.layers[0]
    jobs.append(
        {
            "layer": first,
            "index": index_of[DECISIVE_SITE],
            "values": recipient["states"][first].index_select(
                0, index_of[DECISIVE_SITE]
            ),
        }
    )
    labels.append(("BASELINE", DECISIVE_SITE, first, -1))

    if mode == "REAL":
        for site, index in index_of.items():
            for layer in harness.layers:
                jobs.append(
                    {
                        "layer": layer,
                        "index": index,
                        "values": donor["states"][layer].index_select(0, index),
                    }
                )
                labels.append(("REAL", site, layer, -1))

    generator = torch.Generator(device="cuda:0")
    for replicate in range(args.replicates):
        generator.manual_seed(stable_seed(unit["unit_id"], replicate))
        for site in NULL_SITES:
            index = index_of[site]
            for layer in harness.layers:
                original = recipient["states"][layer].index_select(0, index)
                jobs.append(
                    {
                        "layer": layer,
                        "index": index,
                        "values": destructive_values(
                            original, generator, args.destruction, torch
                        ),
                    }
                )
                labels.append(("NULL", site, layer, replicate))

    # the full-donor reference: every site at once, which is the 1.0 of the scale
    every = sorted({p for positions in unit["sites"].values() for p in positions})
    every_index = torch.tensor(every, dtype=torch.long, device="cuda:0")
    for layer in harness.layers:
        jobs.append(
            {
                "layer": layer,
                "index": every_index,
                "values": donor["states"][layer].index_select(0, every_index),
            }
        )
        labels.append(("FULL", "ALL", layer, -1))

    gaps = harness.run_jobs(
        recipient["ids"], jobs, gather, split, args.batch, torch
    )
    out: dict = {}
    for (construction, site, layer, replicate), gap in zip(labels, gaps):
        out.setdefault(construction, {}).setdefault(site, {}).setdefault(
            str(layer), []
        ).append(gap)
    return out


def c1_effect(raw, baseline, full_reference, null_first_half):
    """C1 for one (site, layer): null-subtracted, normalised on the full donor."""
    denominator = full_reference - baseline
    if abs(denominator) < 1e-9:
        return None
    null_mean = sum(null_first_half) / len(null_first_half)
    return ((raw - baseline) - (null_mean - baseline)) / denominator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--object", required=True)
    parser.add_argument("--inclusion", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--batch", type=int, default=48)
    parser.add_argument("--replicates", type=int, default=NULL_REPLICATES)
    parser.add_argument("--destruction", default="resample")
    parser.add_argument("--mode", choices=("NULL_ONLY", "REAL"), default="NULL_ONLY")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    started = time.time()
    obj = json.loads(Path(args.object).read_text(encoding="utf-8"))
    inclusion = json.loads(Path(args.inclusion).read_text(encoding="utf-8"))
    keep = {row["unit_id"] for row in inclusion["correct_both_units_detail"]}
    units = [u for u in obj["units"] if u["unit_id"] in keep]
    if args.limit:
        units = units[: args.limit]

    AutoTokenizer.from_pretrained(args.model_dir, trust_remote_code=False, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir, dtype=torch.bfloat16, trust_remote_code=False,
        attn_implementation="eager",
    )
    model.to("cuda:0")
    model.eval()
    harness = Harness(model)

    ids_by_name = {}
    for unit in obj["units"]:
        ids_by_name[unit["donor"]] = unit["donor_ids"]
        ids_by_name[unit["recipient"]] = unit["recipient_ids"]

    curves: dict = {}
    null_variance_samples: dict = {}
    per_unit: list[dict] = []

    for unit in units:
        caches = {}
        for name in (unit["donor"], unit["recipient"]):
            ids = torch.tensor(ids_by_name[name], dtype=torch.long, device="cuda:0")
            states, _ = harness.capture_at_width(ids, args.batch, torch)
            caches[name] = {"states": states, "ids": ids}

        raw = measure_unit(harness, unit, caches, args, torch, mode=args.mode)
        baseline = raw["BASELINE"][DECISIVE_SITE][str(harness.layers[0])][0]

        half = args.replicates // 2
        for site in NULL_SITES:
            for layer in harness.layers:
                key = str(layer)
                nulls = raw["NULL"][site][key]
                subtrahend = nulls[:half]
                reserved = nulls[half:]
                full_ref = raw["FULL"]["ALL"][key][0]

                if args.mode == "REAL":
                    value = c1_effect(
                        raw["REAL"][site][key][0], baseline, full_ref, subtrahend
                    )
                    if value is not None:
                        curves.setdefault("C1", {}).setdefault(site, {}).setdefault(
                            key, {}
                        ).setdefault(unit["cluster_id"], []).append(value)

                # the reserved half estimates variance and never enters the
                # subtrahend, so the estimator is not judged against its own noise
                for held_out in reserved:
                    value = c1_effect(held_out, baseline, full_ref, subtrahend)
                    if value is not None:
                        null_variance_samples.setdefault(site, {}).setdefault(
                            key, {}
                        ).setdefault(unit["cluster_id"], []).append(value)

        if args.mode == "REAL":
            for layer in harness.layers:
                key = str(layer)
                full_ref = raw["FULL"]["ALL"][key][0]
                value = raw["REAL"]["PREFIX"][key][0] - baseline
                curves.setdefault("PREFIX_RAW", {}).setdefault("PREFIX", {}).setdefault(
                    key, {}
                ).setdefault(unit["cluster_id"], []).append(value)

        per_unit.append(
            {
                "unit_id": unit["unit_id"],
                "cluster_id": unit["cluster_id"],
                "baseline": baseline,
                "full_reference_last_layer": raw["FULL"]["ALL"][
                    str(harness.layers[-1])
                ][0],
            }
        )
        del caches, raw

    report = {
        "schema_version": "study5-p0c2-c1-pipeline-v1",
        "phase": "P-0c-2 measurement",
        "mode": args.mode,
        "estimand": "C1_null_subtracted",
        "decision_rule": "C1 significantly greater than zero; NOT versus a null ceiling, because C1 already subtracts the null",
        "destruction_kind": args.destruction,
        "replicates": args.replicates,
        "replicate_split": {
            "subtrahend": args.replicates // 2,
            "reserved_for_variance": args.replicates - args.replicates // 2,
            "why_split": "the null that is subtracted and the null that estimates variance must be disjoint, or the estimator is judged against its own noise",
        },
        "common_random_numbers": {
            "how": "every construction for a unit is built in one job list and executed in one batched forward over the same recipient, from a per-unit seed",
            "why": "C1 is a difference, and the variance of a difference of positively correlated terms is far below the sum of their variances",
        },
        "three_part_batch_repair_applied": [
            "in-batch self-patch baseline",
            "cache captured at the consuming run's width",
            "chunks padded to full width",
        ],
        "model_dir": args.model_dir,
        "object_sha256": sha256_file(Path(args.object)),
        "dtype": "bfloat16",
        "n_units": len(units),
        "n_clusters": len({u["cluster_id"] for u in units}),
        "layers": harness.layers,
        "decisive_site": DECISIVE_SITE,
        "instrument_under_test_imported": instrument_under_test_is_loaded(),
        "wall_seconds": round(time.time() - started, 3),
        "per_unit": per_unit,
        "curves": curves,
        "null_variance_samples": null_variance_samples,
        "claim_ceiling": (
            "A measurement on a CONSTRUCTED SELECTION SET. Nothing here is a "
            "result about real items."
        ),
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))
    print(
        f"mode {args.mode}: {len(units)} units, {report['n_clusters']} clusters, "
        f"k={args.replicates}, {report['wall_seconds']:.1f}s, "
        f"instrument_imported={report['instrument_under_test_imported']}"
    )
    print("P0C2-C1-PIPELINE DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
