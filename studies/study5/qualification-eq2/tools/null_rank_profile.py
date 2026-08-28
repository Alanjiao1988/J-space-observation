"""Compute rank profiles under matched-norm random lenses (OA-004 revision 1).

For each replicate, every J_l is replaced by a random matrix with the SAME
Frobenius norm; the rest of the readout path is untouched. This is the null
construction EQ1 registered for kappa_null, transplanted to the rank pipeline.

The point is that the null differs from the real lens ONLY in whether the matrix
carries Jacobian information. Matching the norm removes scale as an explanation:
beating this null cannot be an artifact of magnitude.

Reuses rank_profile.py's scoring so the null and the real measurement cannot
drift apart - they are literally the same code path.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("eq2_rank", _TOOLS / "rank_profile.py")
assert _SPEC is not None and _SPEC.loader is not None
rank = importlib.util.module_from_spec(_SPEC)
sys.modules["eq2_rank"] = rank
_SPEC.loader.exec_module(rank)

AUTHORITY_SHA256 = "63e4751573586d5ed7c8242d7fcaf1b1d6cb3f3232eb60ec46b0bcde795df894"


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def build_null_lens(reference, seed: int):
    """A lens whose every J_l is random with the same Frobenius norm as J_l."""
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--lens", required=True)
    parser.add_argument("--eval-dir", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--replicates", type=int, default=5)
    parser.add_argument("--out-dir", required=True)
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
        args.model_dir,
        dtype=torch.bfloat16,
        trust_remote_code=False,
        attn_implementation="eager",
    )
    model.to("cuda:0")
    model.eval()
    lens_model = jlens.from_hf(model, tokenizer, force_bos=True)
    reference = JacobianLens.load(args.lens)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for replicate in range(args.replicates):
        # Seeds derive from the authority hash and the replicate index, so they
        # are fixed and reproducible rather than chosen.
        seed = (
            int.from_bytes(
                hashlib.sha256(
                    f"STUDY5_EQ2_NULL|{AUTHORITY_SHA256}|{args.role}|{replicate}".encode()
                ).digest()[:8],
                "big",
            )
            % (2**31)
        )
        null_lens = build_null_lens(reference, seed)

        worst = 0.0
        for layer in reference.source_layers:
            a = reference.jacobians[layer].double().norm().item()
            b = null_lens.jacobians[layer].double().norm().item()
            worst = max(worst, abs(1.0 - b / a))
        if worst > 1e-5:
            raise rank.RankProfileError(
                f"null lens norms are not matched; worst deviation {worst}"
            )

        report = rank.score_with_lens(
            lens_model,
            tokenizer,
            null_lens,
            args.eval_dir,
            args.max_seq_len,
            limit=0,
        )
        report.update(
            {
                "schema_version": "study5-eq2-rank-profile-null-v1",
                "phase": "R-1",
                "role": f"{args.role}_null{replicate}",
                "rule": "OA-004 revision 1",
                "null_construction": (
                    "each J_l replaced by a Gaussian matrix rescaled to the "
                    "identical Frobenius norm; the rest of the readout path is "
                    "unchanged"
                ),
                "replicate": replicate,
                "seed": seed,
                "seed_derivation": "sha256('STUDY5_EQ2_NULL|' + authority_sha256 + '|' + role + '|' + replicate)",
                "norm_match_worst_relative_deviation": worst,
                "reference_lens": args.lens,
                "gpu_index_in_container": 0,
                "gpu_uuid_last_twelve": gpu_uuid,
                "claim_ceiling": "A null profile. It licenses no claim of any kind.",
            }
        )
        path = out_dir / f"null_{args.role}_{replicate}.json"
        path.write_bytes(canonical_json_bytes(report))
        peak = max(p["readrate"] for p in report["pooled_profile"]["1"])
        print(
            f"  replicate {replicate}: peak@1={peak:.6f}  "
            f"scored={report['pooled_scored_intermediates']}",
            flush=True,
        )

    print(f"EQ2-CHECK-NULL-PROFILES-{args.role} PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
