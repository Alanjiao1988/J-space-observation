"""Compute the four kurtosis-versus-depth curves for Q-4a.

Curves, all through the SAME official readout path (jlens.lens.JacobianLens.apply):

  kappa_A          lens_A, use_jacobian=True
  kappa_B          lens_B, use_jacobian=True
  kappa_null       matched-norm random J, use_jacobian=True   (OD-009 C5)
  kappa_logitlens  use_jacobian=False                          (descriptive only)

Aggregation is the rule frozen in p2/readout_convention.json BEFORE any curve
existed: excess kurtosis over the vocabulary axis per (row, position, layer),
then the arithmetic mean over all (row, position) pairs. Position 0 is excluded
because it carries only the BOS token.

Activations come from heldout rows only. The A and B rows were consumed by
fitting and are not reused here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MAX_SEQ_LEN = 128
SKIP_FIRST = 16
AUTHORITY_SHA256 = (
    "5c45d31a2aab23ffe93bbf5f4a220fb1835c1b98e960a2588fa587efcb9b1a35"
)

REGISTERED_GPU_UUIDS = {
    "e85524f36fdf",
    "b29579ca41a6",
    "0ec45dca0dfc",
    "5767cc3ad060",
}


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def physical_gpu_uuid_last_twelve() -> str:
    import torch

    uuid = None
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        raw = pynvml.nvmlDeviceGetUUID(pynvml.nvmlDeviceGetHandleByIndex(0))
        uuid = raw.decode() if isinstance(raw, bytes) else str(raw)
    except Exception:
        attr = getattr(torch.cuda.get_device_properties(0), "uuid", None)
        if attr is not None:
            uuid = str(attr)
    if not uuid:
        raise RuntimeError("could not resolve the physical GPU UUID (OD-006)")
    last12 = uuid.replace("-", "")[-12:].lower()
    if last12 not in REGISTERED_GPU_UUIDS:
        raise RuntimeError(f"physical GPU {last12} is not registered")
    return last12


def excess_kurtosis_rowwise(logits) -> "list[float]":
    """Excess kurtosis over the last axis, one value per row.

    float64 throughout, and standardised before the fourth moment, because
    E[(x-mu)^4] on raw logits overflows float32 and loses precision badly.
    """
    import torch

    x = logits.double()
    mean = x.mean(dim=-1, keepdim=True)
    centred = x - mean
    var = centred.pow(2).mean(dim=-1)
    std = var.clamp_min(1e-300).sqrt()
    z = centred / std.unsqueeze(-1)
    return (z.pow(4).mean(dim=-1) - 3.0).tolist()


def build_null_lens(reference, seed: int):
    """A lens whose every J_l is random with the SAME Frobenius norm as J_l.

    Only the matrix is replaced. Shapes, layer set, and the entire downstream
    readout path are untouched, so exceeding this null cannot be explained by a
    difference of scale.
    """
    import torch
    from jlens.lens import JacobianLens

    generator = torch.Generator().manual_seed(seed)
    randomised = {}
    for layer, J in reference.jacobians.items():
        target_norm = J.double().norm()
        R = torch.randn(J.shape, generator=generator, dtype=torch.float64)
        R = R * (target_norm / R.norm())
        randomised[layer] = R.float()
    return JacobianLens(
        jacobians=randomised,
        n_prompts=reference.n_prompts,
        d_model=reference.d_model,
    )


def curve_for(lens, lens_model, prompts, *, use_jacobian: bool, label: str):
    """Mean excess kurtosis per layer, accumulated over (row, position).

    Two aggregations are accumulated from the SAME per-position values:

      primary   - positions 1.. , the rule frozen in readout_convention.json
      secondary - positions SKIP_FIRST.. , matching the position convention the
                  fit itself uses (jlens.fitting.valid_position_mask skips the
                  first 16 as attention sinks)

    The primary is the frozen rule and is the only one Q-4a is decided on. The
    secondary costs nothing extra, because the per-position kurtosis is computed
    either way, and it makes the sensitivity to the position convention visible
    instead of leaving it as an unexamined assumption.
    """
    import torch

    sums: dict[int, float] = {l: 0.0 for l in lens.source_layers}
    counts: dict[int, int] = {l: 0 for l in lens.source_layers}
    alt_sums: dict[int, float] = {l: 0.0 for l in lens.source_layers}
    alt_counts: dict[int, int] = {l: 0 for l in lens.source_layers}

    for index, prompt in enumerate(prompts):
        lens_logits, _model_logits, _ids = lens.apply(
            lens_model,
            prompt,
            layers=lens.source_layers,
            positions=None,
            max_seq_len=MAX_SEQ_LEN,
            use_jacobian=use_jacobian,
        )
        for layer, logits in lens_logits.items():
            per_position = excess_kurtosis_rowwise(logits)
            if any(v != v or abs(v) == float("inf") for v in per_position):
                raise RuntimeError(
                    f"{label}: non-finite kurtosis at layer {layer}, row {index}"
                )
            # Position 0 is BOS only; excluded by the frozen aggregation rule.
            primary = per_position[1:]
            secondary = per_position[SKIP_FIRST:]
            sums[layer] += sum(primary)
            counts[layer] += len(primary)
            alt_sums[layer] += sum(secondary)
            alt_counts[layer] += len(secondary)
        del lens_logits
        if (index + 1) % 20 == 0:
            print(f"  {label}: {index + 1}/{len(prompts)} rows", flush=True)

    return [
        {
            "layer": layer,
            "excess_kurtosis": sums[layer] / counts[layer],
            "n_position_samples": counts[layer],
            "excess_kurtosis_skip_first_16": alt_sums[layer] / alt_counts[layer],
            "n_position_samples_skip_first_16": alt_counts[layer],
        }
        for layer in lens.source_layers
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", required=True)
    parser.add_argument("--lens-a", required=True)
    parser.add_argument("--lens-b", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    import torch

    if torch.cuda.device_count() != 1:
        raise RuntimeError(
            f"exactly one GPU must be visible; saw {torch.cuda.device_count()}"
        )
    gpu_uuid = physical_gpu_uuid_last_twelve()

    rows = []
    with Path(args.rows).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    heldout = sorted(
        (r for r in rows if r["role"] == "heldout"), key=lambda r: r["role_index"]
    )
    if args.limit:
        heldout = heldout[: args.limit]
    if not heldout:
        raise RuntimeError("no heldout rows")

    # The A and B halves were consumed by fitting; assert they are not reused.
    heldout_ids = {r["row_id"] for r in heldout}
    fit_ids = {r["row_id"] for r in rows if r["role"] in ("A", "B")}
    if heldout_ids & fit_ids:
        raise RuntimeError("heldout rows overlap the fitting halves")

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

    probe = lens_model.encode("Hello world", max_length=MAX_SEQ_LEN)
    if int(probe[0, 0]) != int(tokenizer.bos_token_id):
        raise RuntimeError("force_bos did not take effect in the lens model")

    lens_a = JacobianLens.load(args.lens_a)
    lens_b = JacobianLens.load(args.lens_b)

    # OD-009 C5 null. Seed is derived from the authority hash so it is fixed and
    # reproducible rather than chosen.
    null_seed = int.from_bytes(
        hashlib.sha256(f"STUDY5_EQ1_NULL|{AUTHORITY_SHA256}".encode()).digest()[:8],
        "big",
    ) % (2**31)
    lens_null = build_null_lens(lens_a, null_seed)

    null_norm_check = []
    for layer in lens_a.source_layers:
        na = lens_a.jacobians[layer].double().norm().item()
        nn_ = lens_null.jacobians[layer].double().norm().item()
        null_norm_check.append(
            {"layer": layer, "j_norm": na, "null_norm": nn_, "ratio": nn_ / na}
        )
    worst_ratio = max(abs(1.0 - c["ratio"]) for c in null_norm_check)
    if worst_ratio > 1e-5:
        raise RuntimeError(
            f"null lens Frobenius norms are not matched; worst deviation {worst_ratio}"
        )

    print("computing kappa_A", flush=True)
    kappa_a = curve_for(lens_a, lens_model, prompts, use_jacobian=True, label="A")
    print("computing kappa_B", flush=True)
    kappa_b = curve_for(lens_b, lens_model, prompts, use_jacobian=True, label="B")
    print("computing kappa_null", flush=True)
    kappa_null = curve_for(
        lens_null, lens_model, prompts, use_jacobian=True, label="null"
    )
    print("computing kappa_logitlens", flush=True)
    kappa_logit = curve_for(
        lens_a, lens_model, prompts, use_jacobian=False, label="logitlens"
    )

    report = {
        "schema_version": "study5-eq1-p2-kurtosis-curves-v1",
        "phase": "P-2",
        "step": "P2-003",
        "readout": {
            "convention_artifact": "p2/readout_convention.json",
            "entry_point": "jlens.lens.JacobianLens.apply",
            "source_file": "jlens/lens.py",
            "apply_line": 146,
            "readout_line": 213,
            "readout_code": "lens_logits[layer] = model.unembed(residual).float().cpu()",
            "transport_line": 135,
            "transport_code": "residual @ J_bar.T",
            "logit_lens_obtained_by": "the same apply() with use_jacobian=False",
            "softmax_applied": False,
            "statistic": "excess kurtosis over the vocabulary axis, float64, standardised before the fourth moment",
            "aggregation": "arithmetic mean over all (row, position) pairs",
            "position_0_excluded": True,
            "frozen_before_computation": True,
            "secondary_aggregation": {
                "field": "excess_kurtosis_skip_first_16",
                "rule": f"same values aggregated over positions {SKIP_FIRST}..",
                "why_reported": (
                    "the fit itself skips the first 16 positions as attention "
                    "sinks (jlens.fitting.valid_position_mask); reporting the "
                    "readout under that convention as well makes the sensitivity "
                    "to the position rule visible rather than assumed"
                ),
                "used_for_the_q4a_decision": False,
                "the_frozen_primary_rule_was_not_changed": True,
            },
        },
        "activations": {
            "role": "heldout",
            "n_rows": len(heldout),
            "row_ids": [r["row_id"] for r in heldout],
            "overlap_with_fitting_halves": 0,
            "max_seq_len": MAX_SEQ_LEN,
        },
        "null_model": {
            "construction": "each J_l replaced by a Gaussian matrix rescaled to the identical Frobenius norm",
            "seed": null_seed,
            "seed_derivation": "sha256('STUDY5_EQ1_NULL|' + authority_sha256)",
            "norm_match_worst_relative_deviation": worst_ratio,
            "per_layer_norms": null_norm_check,
        },
        "curves": {
            "kappa_A": kappa_a,
            "kappa_B": kappa_b,
            "kappa_null": kappa_null,
            "kappa_logitlens": kappa_logit,
        },
        "lenses": {
            "lens_a_sha256": sha256_file(Path(args.lens_a)),
            "lens_b_sha256": sha256_file(Path(args.lens_b)),
            "n_prompts_a": lens_a.n_prompts,
            "n_prompts_b": lens_b.n_prompts,
        },
        "gpu_index_in_container": 0,
        "gpu_uuid_last_twelve": gpu_uuid,
        "claim_ceiling": (
            "A kurtosis curve is not evidence of J-space. It is a gate input."
        ),
    }
    Path(args.out_report).write_bytes(canonical_json_bytes(report))

    print("\nlayer  kappa_A     kappa_B     kappa_null  kappa_logit")
    for i, layer in enumerate(lens_a.source_layers):
        print(
            f"{layer:5d}  {kappa_a[i]['excess_kurtosis']:10.3f}  "
            f"{kappa_b[i]['excess_kurtosis']:10.3f}  "
            f"{kappa_null[i]['excess_kurtosis']:10.3f}  "
            f"{kappa_logit[i]['excess_kurtosis']:10.3f}"
        )
    print("P2-CHECK-KURTOSIS-CURVES PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
