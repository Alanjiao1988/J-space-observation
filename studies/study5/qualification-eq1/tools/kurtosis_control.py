"""Control measurement: excess kurtosis of the model's OWN final-layer logits.

Why this exists. The four Q-4a curves came out near 1.0, which for a
152064-dimensional logit distribution is close to Gaussian and is not what one
would expect of a language model's logits. Before a FAIL verdict is recorded,
the possibility that the kurtosis code or the readout path is simply wrong has
to be excluded - a gate that fails for a spurious reason is as damaging as one
that passes for a spurious reason.

apply() already returns model_logits, the model's actual final-layer logits at
the same positions, through the same unembed. Running the identical statistic
over those gives a control with a known expectation:

  * if the model's own logits score in the tens or hundreds, the statistic is
    working and the near-Gaussian lens readout is a real property of the lens;
  * if the model's own logits also score near 1, the fault is in this code and
    no verdict may be drawn from the curves.

This is a diagnostic. It is not part of Q-4a and no criterion depends on it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MAX_SEQ_LEN = 128
SKIP_FIRST = 16


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def excess_kurtosis_rowwise(logits) -> list[float]:
    """Identical statistic to measure_kurtosis.py, deliberately duplicated so
    the control does not depend on the code it is controlling."""
    x = logits.double()
    mean = x.mean(dim=-1, keepdim=True)
    centred = x - mean
    var = centred.pow(2).mean(dim=-1)
    std = var.clamp_min(1e-300).sqrt()
    z = centred / std.unsqueeze(-1)
    return (z.pow(4).mean(dim=-1) - 3.0).tolist()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", required=True)
    parser.add_argument("--lens-a", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    import torch

    rows = []
    with Path(args.rows).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    heldout = sorted(
        (r for r in rows if r["role"] == "heldout"), key=lambda r: r["role_index"]
    )[: args.limit]
    prompts = [r["raw_text"] for r in heldout]

    from transformers import AutoModelForCausalLM, AutoTokenizer

    import jlens
    from jlens.lens import JacobianLens

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_dir, trust_remote_code=False, use_fast=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir,
        dtype=torch.bfloat16,
        trust_remote_code=False,
        attn_implementation="eager",
    )
    model.to("cuda:0")
    model.eval()
    lens_model = jlens.from_hf(model, tokenizer, force_bos=True)
    lens = JacobianLens.load(args.lens_a)

    model_vals: list[float] = []
    lens_l0_vals: list[float] = []
    raw_residual_vals: list[float] = []
    top1_gaps: list[float] = []

    for prompt in prompts:
        lens_logits, model_logits, _ids = lens.apply(
            lens_model,
            prompt,
            layers=[0],
            positions=None,
            max_seq_len=MAX_SEQ_LEN,
            use_jacobian=True,
        )
        model_vals.extend(excess_kurtosis_rowwise(model_logits[1:, :]))
        lens_l0_vals.extend(excess_kurtosis_rowwise(lens_logits[0][1:, :]))

        # A third reading: the untransported residual at the FINAL layer read
        # out through the same unembed. This is the model's own logits by
        # another route and should agree with model_vals.
        sorted_logits = model_logits[1:, :].double().sort(dim=-1, descending=True)[0]
        top1_gaps.extend(
            (sorted_logits[:, 0] - sorted_logits[:, 1]).tolist()
        )

        # Logit-lens readout at layer 0, i.e. no transport at all.
        ll, _m, _i = lens.apply(
            lens_model,
            prompt,
            layers=[0],
            positions=None,
            max_seq_len=MAX_SEQ_LEN,
            use_jacobian=False,
        )
        raw_residual_vals.extend(excess_kurtosis_rowwise(ll[0][1:, :]))

    def summarise(values: list[float]) -> dict:
        ordered = sorted(values)
        n = len(ordered)
        return {
            "n": n,
            "mean": sum(ordered) / n,
            "min": ordered[0],
            "p50": ordered[n // 2],
            "max": ordered[-1],
        }

    report = {
        "schema_version": "study5-eq1-p2-kurtosis-control-v1",
        "phase": "P-2",
        "purpose": (
            "control for the near-Gaussian kurtosis seen in the Q-4a curves; "
            "diagnostic only, no criterion depends on it"
        ),
        "rows_used": len(prompts),
        "statistic": "excess kurtosis over the vocabulary axis, float64",
        "model_own_final_logits": summarise(model_vals),
        "jlens_readout_layer_0": summarise(lens_l0_vals),
        "logit_lens_readout_layer_0": summarise(raw_residual_vals),
        "model_top1_minus_top2_logit_gap": summarise(top1_gaps),
        "interpretation_rule_fixed_before_reading": {
            "if_model_own_logits_are_large": (
                "the statistic works and the near-Gaussian lens readout is a "
                "real property of the lens readout, so the Q-4a curves stand"
            ),
            "if_model_own_logits_are_also_near_one": (
                "the fault is in the measurement and NO Q-4a verdict may be "
                "drawn from the curves"
            ),
        },
        "claim_ceiling": "A diagnostic. It licenses no claim of any kind.",
    }
    Path(args.out_report).write_bytes(canonical_json_bytes(report))
    print(json.dumps(report, indent=1))
    print("P2-CHECK-KURTOSIS-CONTROL PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
