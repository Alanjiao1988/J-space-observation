"""P-0' step 3: the batch-baseline repair, and the no-op verification it owes.

P-0 measured the clean baseline in a batch-of-one forward and every patched
value in a batch-of-48 forward. bfloat16 kernels do not select the same
reduction order at both batch sizes, so a constant additive offset entered every
value. PREFIX at the last layer - a no-op guaranteed by architecture, since the
last block's output at a non-final position is read by nothing - returned
0.013754 instead of 0, and returned it identically unit by unit.

The repair has three parts, and the first attempt at it only had one:

  1  the baseline is an explicit self-patch job inside the same batch: the
     recipient's own cached state written back over itself;
  2  the CACHE ITSELF is captured at the same batch width as the run that
     consumes it. Capturing at width 1 and patching into a run of width 48
     leaves batch-1-derived values sitting beside batch-48-derived ones, which
     is the same inconsistency one level down;
  3  every chunk is padded to the full width, so a short final chunk does not
     execute a differently-shaped kernel from its predecessors.

Direction: all three move the IMPLEMENTATION back toward the registered text,
which required a no-op to be a no-op. Bug fix, not a change of criterion. That
the repair would also remove the obstacle which voided P-0's verdict does not
alter the adjudication - the direction decides, not the consequence - and it is
disclosed rather than left to be noticed.

Units. The registered tolerance of 1e-4 is on the NORMALISED scale, because that
is the scale the estimand and every P-0 curve live on. A raw logit deviation
compared against it would be a units error of exactly the shape OD-017 exists to
catch, so both scales are computed and the verdict is taken on the normalised
one.

This tool runs ONLY the no-op family. It computes no effect curve, applies no
decision rule, and is indifferent to which estimand is chosen: a no-op has
numerator exactly zero under any recovery ratio of this shape.

  PREFIX_DONOR   donor's states at prefix positions. Identical values by causal
                 masking, so a no-op on content.
  SELF_PATCH     recipient's own states written back over themselves, at every
                 layer. A no-op on identity, the strongest of the three.
  EMBED_NOOP     donor's embedding-layer states at prefix positions.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

P0_TOOLS = Path(__file__).resolve().parent.parent.parent / "validation-p0" / "tools"

#: The registered tolerance, unchanged from P-0, on the NORMALISED scale.
NOOP_TOLERANCE = 1e-4

DTYPES = ("bfloat16", "float32")


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


def load_patch_module():
    """Reuse P-0's harness verbatim.

    The harness is not what failed: it passed every row-isolation and
    position-targeting test and delivered a positive control at 0.9862. What
    failed was the comparison built around it, so it is imported, not rewritten.
    """
    spec = importlib.util.spec_from_file_location(
        "p0p_patch", P0_TOOLS / "patch_effect.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["p0p_patch"] = module
    spec.loader.exec_module(module)
    return module


def capture_at_width(harness, ids, width, torch):
    """Cache the residual stream from a forward of the SAME width as the run
    that will consume it.

    Capturing at width 1 and patching into a run of width 48 leaves
    batch-1-derived values sitting beside batch-48-derived ones. That is the
    original defect one level down, and it is the part the first repair missed.
    """
    cache: dict[int, "torch.Tensor"] = {}
    handles = []

    def make(layer):
        def hook(_module, _inputs, output):
            tensor = output[0] if isinstance(output, tuple) else output
            cache[layer] = tensor.detach()[0].clone()
            return output

        return hook

    for layer, module in harness.modules.items():
        handles.append(module.register_forward_hook(make(layer)))
    try:
        with torch.no_grad():
            batch = ids.unsqueeze(0).expand(width, -1).contiguous()
            out = harness.model(input_ids=batch)
    finally:
        for handle in handles:
            handle.remove()
    return cache, out.logits[0, -1].detach().float()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--units", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--batch", type=int, default=48)
    parser.add_argument("--dtype", choices=DTYPES, default="bfloat16")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    patch = load_patch_module()
    started = time.time()

    frame = json.loads(Path(args.units).read_text(encoding="utf-8"))
    units = frame["units"][: args.limit] if args.limit else frame["units"]

    AutoTokenizer.from_pretrained(args.model_dir, trust_remote_code=False, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir,
        dtype=torch.bfloat16 if args.dtype == "bfloat16" else torch.float32,
        trust_remote_code=False,
        attn_implementation="eager",
    )
    model.to("cuda:0")
    model.eval()
    harness = patch.Harness(model)

    ids_by_name: dict[str, list[int]] = {}
    for unit in frame["units"]:
        ids_by_name[unit["donor"]] = unit["donor_ids"]
        ids_by_name[unit["recipient"]] = unit["recipient_ids"]

    per_layer: dict[str, dict[str, dict]] = {
        name: {} for name in ("PREFIX_DONOR", "SELF_PATCH", "EMBED_NOOP")
    }
    worst_per_unit: list[dict] = []
    baseline_shift: list[float] = []

    for unit in units:
        donor_ids_t = torch.tensor(
            ids_by_name[unit["donor"]], dtype=torch.long, device="cuda:0"
        )
        recipient_ids_t = torch.tensor(
            ids_by_name[unit["recipient"]], dtype=torch.long, device="cuda:0"
        )
        donor_states, donor_last = capture_at_width(
            harness, donor_ids_t, args.batch, torch
        )
        recipient_states, recipient_last = capture_at_width(
            harness, recipient_ids_t, args.batch, torch
        )

        donor_tok = unit["donor_answer_token_ids"]
        recipient_tok = unit["recipient_answer_token_ids"]
        gather = torch.tensor(
            list(donor_tok) + list(recipient_tok), dtype=torch.long, device="cuda:0"
        )
        split = len(donor_tok)
        l_full = patch.logit_difference(donor_last, donor_tok, recipient_tok)
        index_of = {
            site: torch.tensor(positions, dtype=torch.long, device="cuda:0")
            for site, positions in unit["sites"].items()
        }

        jobs: list[dict] = []
        labels: list[tuple[str, int]] = []

        first = harness.layers[0]
        jobs.append(
            {
                "layer": first,
                "index": index_of["BRIDGE"],
                "values": recipient_states[first].index_select(0, index_of["BRIDGE"]),
            }
        )
        labels.append(("BASELINE", first))

        for layer in harness.layers:
            jobs.append(
                {
                    "layer": layer,
                    "index": index_of["PREFIX"],
                    "values": donor_states[layer].index_select(0, index_of["PREFIX"]),
                }
            )
            labels.append(("PREFIX_DONOR", layer))
            jobs.append(
                {
                    "layer": layer,
                    "index": index_of["BRIDGE"],
                    "values": recipient_states[layer].index_select(
                        0, index_of["BRIDGE"]
                    ),
                }
            )
            labels.append(("SELF_PATCH", layer))

        jobs.append(
            {
                "layer": patch.EMBEDDING_LAYER,
                "index": index_of["PREFIX"],
                "values": donor_states[patch.EMBEDDING_LAYER].index_select(
                    0, index_of["PREFIX"]
                ),
            }
        )
        labels.append(("EMBED_NOOP", patch.EMBEDDING_LAYER))

        # Pad to a whole number of full-width chunks so no short final chunk
        # executes a differently-shaped kernel.
        pad = (-len(jobs)) % args.batch
        jobs.extend([dict(jobs[0]) for _ in range(pad)])
        labels.extend([("PAD", first)] * pad)

        gaps = harness.patched_logit_gap(
            recipient_ids_t, jobs, gather, split, args.batch
        )
        baseline = gaps[0]
        denominator = l_full - baseline

        old_clean = patch.logit_difference(
            harness.capture(recipient_ids_t)[1], donor_tok, recipient_tok
        )
        baseline_shift.append(baseline - old_clean)

        unit_worst_raw = 0.0
        unit_worst_norm = 0.0
        for (construction, layer), gap in zip(labels, gaps):
            if construction in ("BASELINE", "PAD"):
                continue
            raw = gap - baseline
            norm = raw / denominator if denominator else float("nan")
            bucket = per_layer[construction].setdefault(
                str(layer), {"raw": [], "norm": []}
            )
            bucket["raw"].append(raw)
            bucket["norm"].append(norm)
            unit_worst_raw = max(unit_worst_raw, abs(raw))
            unit_worst_norm = max(unit_worst_norm, abs(norm))
        worst_per_unit.append(
            {
                "unit_id": unit["unit_id"],
                "worst_abs_deviation_logits": unit_worst_raw,
                "worst_abs_deviation_normalised": unit_worst_norm,
                "denominator": denominator,
            }
        )

    elapsed = time.time() - started

    summary: dict[str, dict] = {}
    for construction, by_layer in per_layer.items():
        rows = {}
        for layer, bucket in by_layer.items():
            rows[layer] = {
                "mean_logits": sum(bucket["raw"]) / len(bucket["raw"]),
                "worst_abs_logits": max(abs(v) for v in bucket["raw"]),
                "mean_normalised": sum(bucket["norm"]) / len(bucket["norm"]),
                "worst_abs_normalised": max(abs(v) for v in bucket["norm"]),
                "n": len(bucket["raw"]),
            }
        summary[construction] = {
            "per_layer": rows,
            "worst_abs_mean_normalised": max(
                abs(r["mean_normalised"]) for r in rows.values()
            ),
            "worst_abs_single_unit_normalised": max(
                r["worst_abs_normalised"] for r in rows.values()
            ),
            "worst_abs_mean_logits": max(abs(r["mean_logits"]) for r in rows.values()),
            "worst_abs_single_unit_logits": max(
                r["worst_abs_logits"] for r in rows.values()
            ),
        }

    worst_mean = max(s["worst_abs_mean_normalised"] for s in summary.values())
    passed = worst_mean <= NOOP_TOLERANCE

    report = {
        "schema_version": "study5-p0c2-baseline-v1",
        "phase": "P-0c-2",
        "dtype": args.dtype,
        "what_this_verifies": (
            "that a patch which cannot influence the output produces no change, "
            "once the baseline, the cache and the chunk width are all consistent"
        ),
        "the_repair_has_three_parts": [
            "the baseline is a self-patch job inside the same batch",
            "the cache is captured at the same batch width as the run consuming it",
            "every chunk is padded to full width",
        ],
        "inherited_from_P0_prime_and_re_proven_here_not_assumed": (
            "the cache was still captured at width 1 while the run executed at "
            "width 48, which is the original inconsistency one level down"
        ),
        "units_note": (
            "the registered 1e-4 tolerance is on the NORMALISED scale, the scale "
            "the estimand and every P-0 curve live on; the verdict is taken "
            "there, and raw logits are reported beside it"
        ),
        "direction_of_the_change": (
            "implementation moved back toward the registered text, which "
            "required a no-op to be a no-op; a bug fix, not a change of criterion"
        ),
        "disclosure": (
            "a successful repair would also remove the obstacle that voided "
            "P-0's verdict; the direction decides rather than the consequence, "
            "and this is stated rather than left to be noticed"
        ),
        "estimand_independent": True,
        "model_dir": args.model_dir,
        "units_file_sha256": sha256_file(Path(args.units)),
        "batch": args.batch,
        "n_units": len(units),
        "layers": harness.layers,
        "tolerance_normalised": NOOP_TOLERANCE,
        "constructions": summary,
        "worst_abs_mean_normalised_over_all": worst_mean,
        "worst_abs_single_unit_normalised_over_all": max(
            s["worst_abs_single_unit_normalised"] for s in summary.values()
        ),
        "worst_abs_mean_logits_over_all": max(
            s["worst_abs_mean_logits"] for s in summary.values()
        ),
        "per_unit_worst": worst_per_unit,
        "old_batch_of_one_baseline_shift_logits": {
            "definition": "in-batch baseline minus a batch-of-one clean forward",
            "mean": sum(baseline_shift) / len(baseline_shift) if baseline_shift else 0.0,
            "worst_abs": max((abs(v) for v in baseline_shift), default=0.0),
        },
        "verdict": "PASS" if passed else "FAIL",
        "wall_seconds": round(elapsed, 3),
        "gpu_uuid_last_twelve": patch.physical_gpu_uuid_last_twelve(),
        "instrument_under_test_imported": patch.instrument_under_test_is_loaded(),
        "claim_ceiling": "An instrument-integrity record. It licenses no claim.",
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print(f"  dtype {args.dtype}, {len(units)} units, batch {args.batch}")
    for construction, stats in sorted(summary.items()):
        print(
            f"  {construction:14} |mean| norm {stats['worst_abs_mean_normalised']:.3e}"
            f"  worst unit norm {stats['worst_abs_single_unit_normalised']:.3e}"
            f"  (|mean| {stats['worst_abs_mean_logits']:.4f} logits)"
        )
    print(f"  tolerance {NOOP_TOLERANCE:.0e} normalised -> {report['verdict']}")
    print(
        f"  baseline shift vs batch-of-one: "
        f"{report['old_batch_of_one_baseline_shift_logits']['mean']:.6f} logits"
    )
    if not passed:
        print("P0C2-CHECK-BASELINE FAILED", file=sys.stderr)
        return 1
    print("P0C2-CHECK-BASELINE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
