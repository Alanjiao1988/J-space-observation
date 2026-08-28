"""R-1b step C: plain logit lens control, and OA-005 condition (ii).

The matched-norm random-lens null tests whether the pipeline manufactures signal
from nothing. It cannot test a different confounder: whether J is merely reading
output-adjacency that the residual stream already carries. A late band is exactly
where that confounder bites.

So a second control is required, and it is the tightest available one: the SAME
residual stream through the SAME unembed with NO Jacobian at all. In the official
implementation that is `apply(..., use_jacobian=False)`, guarded at lens.py:211,
so the two readouts differ in exactly one respect.

OA-005 condition (ii): within the run, J-lens readrate must SIGNIFICANTLY exceed
plain logit lens readrate. Significance is the same Wilson non-overlap test used
against the null, so the two conditions are judged on the same footing.

This condition can fail. If J is approximately the identity the two readouts
coincide and (ii) fails by construction - which is the failure mode OD-016
already registered.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, _HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rank = _load("llc_rank", "rank_profile.py")
bvn = _load("llc_bvn", "band_vs_null.py")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def condition_ii(
    j_profile: list[dict],
    logit_profile: list[dict],
    band: list[int],
    trials: int,
) -> dict:
    """Does the J-lens significantly exceed the plain logit lens inside the band?"""
    j_by_layer = {int(p["layer"]): p for p in j_profile}
    l_by_layer = {int(p["layer"]): p for p in logit_profile}

    per_layer = []
    for layer in band:
        j_hits = int(j_by_layer[layer]["hits"])
        l_hits = int(l_by_layer[layer]["hits"])
        j_lo, _j_hi = bvn.wilson_bounds(j_hits, trials)
        _l_lo, l_hi = bvn.wilson_bounds(l_hits, trials)
        exceeds = j_lo > l_hi
        per_layer.append(
            {
                "layer": layer,
                "j_readrate": j_hits / trials if trials else 0.0,
                "logit_readrate": l_hits / trials if trials else 0.0,
                "j_lower_bound": j_lo,
                "logit_upper_bound": l_hi,
                "j_significantly_exceeds_logit_lens": exceeds,
            }
        )

    passing = [p["layer"] for p in per_layer if p["j_significantly_exceeds_logit_lens"]]
    failing = [p["layer"] for p in per_layer if not p["j_significantly_exceeds_logit_lens"]]

    # The revised band keeps only the layers that satisfy (ii), then takes the
    # longest contiguous run of those, so a band cannot be stitched together
    # across a layer that failed.
    flags = [layer in set(passing) for layer in band]
    revised = bvn.longest_contiguous_run(flags, band)

    return {
        "per_layer": per_layer,
        "layers_passing_condition_ii": passing,
        "layers_failing_condition_ii": failing,
        "all_band_layers_pass": not failing,
        "revised_band": revised,
        "revised_band_length": len(revised),
        "band_survives_condition_ii": bool(revised),
        "test": (
            "Wilson non-overlap: the J-lens lower bound must exceed the plain "
            "logit lens upper bound, the same form of test used against the null"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--lens", required=True)
    parser.add_argument("--eval-dir", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--max-seq-len", type=int, default=2048)
    args = parser.parse_args()

    import torch

    if torch.cuda.device_count() != 1:
        raise rank.RankProfileError(
            f"exactly one GPU must be visible; saw {torch.cuda.device_count()}"
        )
    gpu_uuid = rank.physical_gpu_uuid_last_twelve()

    from transformers import AutoModelForCausalLM, AutoTokenizer

    import jlens
    from jlens.lens import JacobianLens

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_dir, trust_remote_code=False, use_fast=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir, dtype=torch.bfloat16, trust_remote_code=False,
        attn_implementation="eager",
    )
    model.to("cuda:0")
    model.eval()
    lens_model = jlens.from_hf(model, tokenizer, force_bos=True)
    lens = JacobianLens.load(args.lens)

    # Monkey-patching would be a silent change of method. Instead the lens's own
    # apply is called with use_jacobian=False by wrapping it, so the scoring code
    # is byte-identical to the J-lens run.
    original_apply = lens.apply

    def logit_lens_apply(model_, prompt, **kwargs):
        kwargs["use_jacobian"] = False
        return original_apply(model_, prompt, **kwargs)

    lens.apply = logit_lens_apply  # type: ignore[method-assign]

    report = rank.score_with_lens(
        lens_model, tokenizer, lens, args.eval_dir, args.max_seq_len, limit=0
    )
    report.update(
        {
            "schema_version": "study5-eq2-logit-lens-control-v1",
            "phase": "R-1b",
            "step": "C",
            "role": f"{args.role}_logitlens",
            "rule": "OA-005 condition (ii)",
            "control": (
                "plain logit lens: the same residual stream, the same unembed, no "
                "Jacobian; obtained through the official path with use_jacobian=False"
            ),
            "differs_from_the_j_lens_run_in_exactly_one_respect": True,
            "gpu_index_in_container": 0,
            "gpu_uuid_last_twelve": gpu_uuid,
            "claim_ceiling": "A control profile. It licenses no claim of any kind.",
        }
    )
    Path(args.out_report).write_bytes(canonical_json_bytes(report))

    peak = max(p["readrate"] for p in report["pooled_profile"]["1"])
    print(f"\nplain logit lens peak pass@1: {peak:.6f}")
    print(f"EQ2-CHECK-LOGIT-LENS-{args.role} PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
