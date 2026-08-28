"""Merge lens shards WITHIN one half and report fitting stability.

OD-010 is enforced structurally: this tool takes a single role and refuses to
accept shards from more than one. There is no code path here that can produce
merge(lens_A, lens_B).

Stability quantities reported, chosen to stay comparable with EV-0015, which
recorded a maximum A/B relative Frobenius difference of 0.073860 on the 1.5B:

  * per-layer relative Frobenius difference between lens_A and lens_B, and its
    maximum over layers;
  * save/load round-trip max absolute difference (expected exactly 0);
  * shard merge versus an independent n_prompts-weighted recomputation
    (expected exactly 0).

The 7B value is a new measurement with no pass threshold. It is reported beside
the 1.5B value, not compared against it as a gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

EV0015_1_5B_MAX_RELATIVE_FROBENIUS = 0.073860


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def load_shard(path: Path):
    import torch
    from jlens.lens import JacobianLens

    blob = torch.load(str(path), map_location="cpu", weights_only=True)
    return JacobianLens(
        jacobians=blob["jacobians"],
        n_prompts=int(blob["n_prompts"]),
        d_model=int(blob["d_model"]),
    )


def merge_one_half(shard_paths: list[Path], role: str, out_dir: Path) -> dict:
    import torch
    from jlens.lens import JacobianLens

    shards = [load_shard(p) for p in shard_paths]
    roles_seen = set()
    for p in shard_paths:
        receipt = p.parent / p.name.replace("lens_", "receipt_").replace(".pt", ".json")
        if receipt.is_file():
            roles_seen.add(json.loads(receipt.read_text(encoding="utf-8"))["role"])
    if roles_seen and roles_seen != {role}:
        raise RuntimeError(
            f"OD-010 violation: shards for half {role} carry roles {sorted(roles_seen)}"
        )

    merged = JacobianLens.merge(shards)

    # Two separate checks, because they answer different questions.
    #
    # 1. Bookkeeping: replicate merge()'s arithmetic exactly - same float32
    #    precision, same accumulation order - written independently here. This
    #    must be EXACTLY 0. It catches a wrong shard set, wrong n_prompts
    #    weighting or a wrong total, which are the errors that would silently
    #    corrupt the lens.
    # 2. Numerical accuracy: a float64 reference. This is NOT expected to be 0,
    #    because merge() accumulates in float32; it bounds the rounding error
    #    rather than asserting its absence. Reporting it as though it should be
    #    zero would be reporting a float32 sum as if it were exact.
    n_total = sum(s.n_prompts for s in shards)
    bookkeeping_max_abs = 0.0
    float64_reference_max_abs = 0.0
    for layer in merged.source_layers:
        replicated = sum(s.jacobians[layer] * s.n_prompts for s in shards) / n_total
        bookkeeping_max_abs = max(
            bookkeeping_max_abs,
            (replicated - merged.jacobians[layer]).abs().max().item(),
        )

        acc = torch.zeros_like(merged.jacobians[layer], dtype=torch.float64)
        for s in shards:
            acc += s.jacobians[layer].double() * s.n_prompts
        acc /= n_total
        float64_reference_max_abs = max(
            float64_reference_max_abs,
            (acc - merged.jacobians[layer].double()).abs().max().item(),
        )

    if bookkeeping_max_abs != 0.0:
        raise RuntimeError(
            f"half {role}: independent recomputation of the merge differs by "
            f"{bookkeeping_max_abs}; expected exactly 0"
        )

    lens_path = out_dir / f"lens_{role}.pt"
    # float32, not the fp16 default, so the round trip is exact and the saved
    # blob preserves the fitted values.
    merged.save(str(lens_path), dtype=torch.float32)

    reloaded = JacobianLens.load(str(lens_path))
    roundtrip_max_abs = 0.0
    for layer in merged.source_layers:
        diff = (
            (reloaded.jacobians[layer] - merged.jacobians[layer]).abs().max().item()
        )
        roundtrip_max_abs = max(roundtrip_max_abs, diff)

    return {
        "role": role,
        "shards": [str(p.name) for p in shard_paths],
        "shard_n_prompts": [s.n_prompts for s in shards],
        "n_prompts_total": n_total,
        "source_layers": merged.source_layers,
        "d_model": merged.d_model,
        "lens_path": str(lens_path),
        "lens_sha256": sha256_file(lens_path),
        "lens_bytes": lens_path.stat().st_size,
        "save_load_roundtrip_max_abs_diff": roundtrip_max_abs,
        "shard_merge_vs_independent_recompute_max_abs_diff": bookkeeping_max_abs,
        "shard_merge_vs_independent_recompute_note": (
            "float32, replicating merge()'s precision and accumulation order; "
            "asserted to be exactly 0"
        ),
        "shard_merge_vs_float64_reference_max_abs_diff": float64_reference_max_abs,
        "shard_merge_vs_float64_reference_note": (
            "NOT expected to be 0: merge() accumulates in float32, so this "
            "bounds the rounding error rather than asserting its absence"
        ),
        "lens": merged,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lens-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--out-report", required=True)
    args = parser.parse_args()

    import torch

    lens_dir = Path(args.lens_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    halves = {}
    for role in ("A", "B"):
        shard_paths = sorted(lens_dir.glob(f"lens_{role}_shard*.pt"))
        if not shard_paths:
            raise RuntimeError(f"no shards found for half {role}")
        halves[role] = merge_one_half(shard_paths, role, out_dir)

    lens_a = halves["A"].pop("lens")
    lens_b = halves["B"].pop("lens")

    if lens_a.source_layers != lens_b.source_layers:
        raise RuntimeError("halves disagree on source layers")

    per_layer = []
    max_rel = 0.0
    for layer in lens_a.source_layers:
        ja = lens_a.jacobians[layer].double()
        jb = lens_b.jacobians[layer].double()
        denom = (ja.norm() + jb.norm()).item() / 2.0
        rel = ((ja - jb).norm().item() / denom) if denom > 0 else float("nan")
        per_layer.append({"layer": layer, "relative_frobenius_difference": rel})
        max_rel = max(max_rel, rel)

    report = {
        "schema_version": "study5-eq1-p2-lens-merge-v1",
        "phase": "P-2",
        "step": "P2-002",
        "od_010": {
            "merged_within_each_half_only": True,
            "cross_half_merge_performed": False,
            "structural_guarantee": (
                "this tool merges one role at a time and has no code path that "
                "combines the A and B halves"
            ),
        },
        "halves": halves,
        "cross_fit_stability": {
            "definition": (
                "relative Frobenius difference = ||J_A(l) - J_B(l)||_F divided by "
                "the mean of ||J_A(l)||_F and ||J_B(l)||_F"
            ),
            "per_layer": per_layer,
            "max_over_layers_7b": max_rel,
            "ev_0015_max_over_layers_1_5b": EV0015_1_5B_MAX_RELATIVE_FROBENIUS,
            "comparison_is_descriptive_no_pass_threshold": True,
        },
        "claim_ceiling": (
            "These are instrument stability numbers. They license no claim about "
            "the model or about J-space."
        ),
    }
    Path(args.out_report).write_bytes(canonical_json_bytes(report))
    print(json.dumps({k: v for k, v in report.items() if k != "halves"}, indent=1)[:2500])
    print(f"max relative Frobenius A vs B (7B): {max_rel:.6f}")
    print(f"EV-0015 (1.5B) for comparison:      {EV0015_1_5B_MAX_RELATIVE_FROBENIUS:.6f}")
    for role in ("A", "B"):
        h = halves[role]
        print(
            f"half {role}: n={h['n_prompts_total']} "
            f"roundtrip={h['save_load_roundtrip_max_abs_diff']} "
            f"bookkeeping={h['shard_merge_vs_independent_recompute_max_abs_diff']} "
            f"float64_ref={h['shard_merge_vs_float64_reference_max_abs_diff']:.3e}"
        )
    print("P2-CHECK-MERGE-STABILITY PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
