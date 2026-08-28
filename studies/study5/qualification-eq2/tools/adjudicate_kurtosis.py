"""Step C: adjudicate the kurtosis convention V versus D on the positive control.

Both conventions consume the identical official readout (jlens apply, raw
logits). They differ only in which axis the fourth moment is taken along:

  V  vocabulary axis  - for a fixed (position, layer), excess kurtosis over the
                        vocabulary dimension of that single readout. This is
                        what EQ1 computed.
  D  dataset axis     - for a fixed (position, layer) and a fixed vocabulary
                        entry, collect that logit across many activations and
                        take the excess kurtosis of THAT distribution, then
                        average over vocabulary entries.

The criterion, registered in OA-004 and OD-015 before any curve existed, is
which convention's band agrees better with the rank-derived band, measured by
Jaccard index.

Per OA-004 this cannot stop the invocation: if neither agrees, that is recorded
and the rank method continues as the primary locator. There is deliberately no
outcome in which agreement must be found.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MAX_SEQ_LEN = 2048
VOCAB_SAMPLE = 4096

REGISTERED_GPU_UUIDS = {
    "e85524f36fdf", "b29579ca41a6", "0ec45dca0dfc", "5767cc3ad060",
}


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def excess_kurtosis_rows(x):
    """Excess kurtosis along the last axis, float64, standardised first."""
    x = x.double()
    mean = x.mean(dim=-1, keepdim=True)
    centred = x - mean
    var = centred.pow(2).mean(dim=-1)
    std = var.clamp_min(1e-300).sqrt()
    z = centred / std.unsqueeze(-1)
    return z.pow(4).mean(dim=-1) - 3.0


def longest_contiguous_run(flags, layers):
    best, current = [], []
    for flag, layer in zip(flags, layers, strict=True):
        if flag:
            current.append(layer)
            if len(current) > len(best):
                best = list(current)
        else:
            current = []
    return best


def band_from_curve(curve: list[dict]) -> list[int]:
    """Half-height contiguous run.

    This is the shape rule EQ1 used for its kurtosis curves, applied here so the
    two conventions are compared on the same footing as EQ1 measured them. It is
    used ONLY to give each kurtosis convention a band to compare against the
    rank band; it is not the rank band rule, which is OA-004's null test.
    """
    layers = [int(p["layer"]) for p in curve]
    values = [float(p["excess_kurtosis"]) for p in curve]
    lo, hi = min(values), max(values)
    if hi <= lo:
        return []
    tau = lo + 0.5 * (hi - lo)
    return longest_contiguous_run([v >= tau for v in values], layers)


def jaccard(a: list[int], b: list[int]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--lens", required=True)
    parser.add_argument("--eval-dir", required=True)
    parser.add_argument("--rank-band", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--rows", type=int, default=120)
    args = parser.parse_args()

    import torch

    if torch.cuda.device_count() != 1:
        raise RuntimeError(
            f"exactly one GPU must be visible; saw {torch.cuda.device_count()}"
        )

    uuid = None
    try:
        import pynvml

        pynvml.nvmlInit()
        raw = pynvml.nvmlDeviceGetUUID(pynvml.nvmlDeviceGetHandleByIndex(0))
        uuid = (raw.decode() if isinstance(raw, bytes) else str(raw))
    except Exception:
        attr = getattr(torch.cuda.get_device_properties(0), "uuid", None)
        uuid = str(attr) if attr is not None else None
    gpu_uuid = uuid.replace("-", "")[-12:].lower() if uuid else None
    if gpu_uuid not in REGISTERED_GPU_UUIDS:
        raise RuntimeError(f"physical GPU {gpu_uuid} is not registered")

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
    layers = list(lens.source_layers)

    # The same prompts the rank measurement used, so both conventions and the
    # rank band see the same activations.
    prompts = []
    for slug in sorted(("association", "multihop", "multilingual",
                        "order-ops", "poetry", "typo")):
        path = Path(args.eval_dir) / f"lens-eval-{slug}.json"
        for item in json.loads(path.read_text(encoding="utf-8"))["items"]:
            prompts.append(item["prompt"])
    prompts = prompts[: args.rows]

    # Convention V accumulates directly. Convention D needs the logits held
    # across rows, so a fixed vocabulary subsample is used to bound memory; the
    # subsample is the same for every row and layer.
    generator = torch.Generator().manual_seed(20260828)
    vocab_size = int(model.config.vocab_size)
    vocab_idx = torch.randperm(vocab_size, generator=generator)[:VOCAB_SAMPLE]

    v_sums = {layer: 0.0 for layer in layers}
    v_counts = {layer: 0 for layer in layers}
    d_stack = {layer: [] for layer in layers}

    for index, prompt in enumerate(prompts):
        lens_logits, _m, _i = lens.apply(
            lens_model, prompt, layers=layers, positions=[-1],
            max_seq_len=MAX_SEQ_LEN, use_jacobian=True,
        )
        for layer in layers:
            row = lens_logits[layer][0]
            v_sums[layer] += float(excess_kurtosis_rows(row.unsqueeze(0))[0])
            v_counts[layer] += 1
            d_stack[layer].append(row[vocab_idx].double().cpu())
        del lens_logits
        if (index + 1) % 20 == 0:
            print(f"  {index + 1}/{len(prompts)} rows", flush=True)

    kappa_v = [
        {"layer": layer, "excess_kurtosis": v_sums[layer] / v_counts[layer]}
        for layer in layers
    ]

    kappa_d = []
    for layer in layers:
        # [n_rows, vocab_sample] -> kurtosis along the ROW axis for each
        # vocabulary entry, then averaged over entries.
        stacked = torch.stack(d_stack[layer], dim=0).T.contiguous()
        per_entry = excess_kurtosis_rows(stacked)
        kappa_d.append(
            {"layer": layer, "excess_kurtosis": float(per_entry.mean())}
        )

    band_v = band_from_curve(kappa_v)
    band_d = band_from_curve(kappa_d)

    rank_band = json.loads(Path(args.rank_band).read_text(encoding="utf-8"))["band"]

    j_v = jaccard(band_v, rank_band)
    j_d = jaccard(band_d, rank_band)

    if j_v == j_d:
        selected = None
        verdict = "NEITHER CONVENTION DISCRIMINATES"
    else:
        selected = "V" if j_v > j_d else "D"
        verdict = f"convention {selected} agrees better with the rank-derived band"

    report = {
        "schema_version": "study5-eq2-kurtosis-adjudication-v1",
        "phase": "R-1",
        "step": "R1-009",
        "criterion": "OA-004 / OD-015: whichever convention's band agrees better with the rank-derived band, by Jaccard",
        "model": args.model_dir,
        "lens": args.lens,
        "rows": len(prompts),
        "vocab_subsample_for_convention_D": VOCAB_SAMPLE,
        "vocab_subsample_note": (
            "convention D needs the logits retained across rows, so a fixed "
            "random vocabulary subsample bounds memory; the same subsample is "
            "used for every row and every layer, and convention V uses the FULL "
            "vocabulary"
        ),
        "readout_position": "the final prompt token, position -1, for both conventions",
        "rank_band": rank_band,
        "convention_V": {
            "axis": "vocabulary",
            "this_is_what_EQ1_computed": True,
            "curve": kappa_v,
            "band": band_v,
            "jaccard_with_rank_band": j_v,
        },
        "convention_D": {
            "axis": "dataset",
            "curve": kappa_d,
            "band": band_d,
            "jaccard_with_rank_band": j_d,
        },
        "selected_convention": selected,
        "verdict": verdict,
        "if_neither_agrees_rule": (
            "per OA-004 this does not stop the invocation; it records that "
            "kurtosis is not a valid locator under this method and the rank "
            "method continues as the primary locator"
        ),
        "kurtosis_never_overrides_rank": True,
        "gpu_uuid_last_twelve": gpu_uuid,
        "claim_ceiling": "An adjudication between two measurement conventions. It licenses no claim of any kind.",
    }
    Path(args.out_report).write_bytes(canonical_json_bytes(report))

    print("\nlayer   kappa_V     kappa_D")
    for a, b in zip(kappa_v, kappa_d, strict=True):
        print(f"{a['layer']:5d}  {a['excess_kurtosis']:9.4f}  {b['excess_kurtosis']:9.4f}")
    print(f"\nrank band : {rank_band}")
    print(f"band V    : {band_v}   jaccard {j_v:.4f}")
    print(f"band D    : {band_d}   jaccard {j_d:.4f}")
    print(f"verdict   : {verdict}")
    print("EQ2-CHECK-KURTOSIS-ADJUDICATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
