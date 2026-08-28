"""D-1: is this negative about the models, or about our J construction?

Registered in d1/D-1_preregistration.json BEFORE running, with the decision rule
frozen there. This tool only applies it.

  negative-A   J departs substantially from the identity, yet the J-lens adds
               nothing readable over the unembedding. A finding about the models.
  negative-B   J is approximately the identity, so the J-lens degenerates into a
               plain logit lens by construction. A finding about US, and EQ2
               would then amount to having failed to adjudicate.

Reads ONLY the external lenses acquired and byte-verified in R-0. lens_A and
lens_B are never opened; the tool refuses paths that look like them.

OD-011: failing cases in tests/test_eq2_d1_degeneracy.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# The sealed EQ1 lenses, by their committed digests. D-1 must not read these.
SEALED_LENS_SHA256 = {
    "2910b7bf80784a48f4e0d41f1a6fd002781f1d3f4f6bc3df83fb547848164083",
    "e6d7eec9cb33035edb4b702bc3fae807a48d42c29270f40b9c461e6116ee528a",
}

NEGATIVE_B_BELOW = 0.5
NEGATIVE_A_AT_OR_ABOVE = 1.0

# OD-016's registered interval, and the lower gate whose weaker basis was
# flagged when it was registered.
OD016_LOWER_GATE = 0.130071
OD016_UPPER_FENCE = 1.446260


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def analyse_lens(path: Path) -> dict:
    import torch

    digest = sha256_file(path)
    if digest in SEALED_LENS_SHA256:
        raise SystemExit(
            f"REFUSED: {path} is a sealed EQ1 lens. D-1 may not read it."
        )

    blob = torch.load(str(path), map_location="cpu", weights_only=True)
    jacobians = blob["J"] if "J" in blob else blob["jacobians"]
    d_model = int(blob["d_model"])

    per_layer = []
    for layer in sorted(jacobians):
        J = jacobians[layer].double()
        rows, cols = J.shape
        square = rows == cols

        identity = torch.eye(rows, cols, dtype=torch.float64)
        norm_J = float(J.norm())
        norm_I = float(identity.norm())

        # Relative distance from the identity. The registered decision rule
        # reads this quantity.
        rel_distance_from_identity = float((J - identity).norm() / identity.norm())

        # Best scaled identity: the alpha minimising ||J - alpha*I||_F is
        # trace(J) / ||I||^2 for square J. Decomposing this way separates
        # "J is the identity up to a scale" from "J is genuinely something else".
        alpha = float((J * identity).sum() / (identity * identity).sum())
        residual = J - alpha * identity
        norm_residual = float(residual.norm())
        identity_share = (
            (abs(alpha) * norm_I) ** 2 / (norm_J**2) if norm_J > 0 else 0.0
        )
        residual_share = (norm_residual**2) / (norm_J**2) if norm_J > 0 else 0.0

        singular = torch.linalg.svdvals(J)
        s = singular.tolist()
        s_sorted = sorted(s, reverse=True)
        total = sum(s_sorted)
        top1_share = s_sorted[0] / total if total > 0 else 0.0
        # Participation-style effective rank: how many directions carry the map.
        probs = [v / total for v in s_sorted if total > 0]
        effective_rank = (
            1.0 / sum(p * p for p in probs) if probs else 0.0
        )

        per_layer.append(
            {
                "layer": int(layer),
                "shape": [rows, cols],
                "square": square,
                "frobenius_norm": norm_J,
                "relative_distance_from_identity": rel_distance_from_identity,
                "best_scaled_identity_alpha": alpha,
                "identity_attributable_share_of_energy": identity_share,
                "residual_share_of_energy": residual_share,
                "singular_value_max": s_sorted[0],
                "singular_value_min": s_sorted[-1],
                "singular_value_median": s_sorted[len(s_sorted) // 2],
                "top_singular_value_share": top1_share,
                "effective_rank_participation": effective_rank,
                "full_rank_would_be": min(rows, cols),
            }
        )

    distances = sorted(p["relative_distance_from_identity"] for p in per_layer)
    median_distance = distances[len(distances) // 2]
    shares = sorted(p["identity_attributable_share_of_energy"] for p in per_layer)
    median_identity_share = shares[len(shares) // 2]

    return {
        "lens_path": str(path),
        "lens_sha256": digest,
        "is_a_sealed_eq1_lens": False,
        "d_model": d_model,
        "layers": len(per_layer),
        "per_layer": per_layer,
        "median_relative_distance_from_identity": median_distance,
        "min_relative_distance_from_identity": distances[0],
        "max_relative_distance_from_identity": distances[-1],
        "median_identity_attributable_share": median_identity_share,
        "median_effective_rank": sorted(
            p["effective_rank_participation"] for p in per_layer
        )[len(per_layer) // 2],
    }


def categorise(median_distance: float) -> tuple[str, str]:
    if median_distance < NEGATIVE_B_BELOW:
        return (
            "negative-B",
            "J is close to the identity, so the J-lens degenerates into a plain "
            "logit lens by construction; this negative does NOT adjudicate the "
            "construct and EQ2 amounts to having failed to adjudicate",
        )
    if median_distance >= NEGATIVE_A_AT_OR_ABOVE:
        return (
            "negative-A",
            "J departs substantially from the identity and yet the J-lens adds "
            "nothing readable over the unembedding; this is a substantive finding "
            "about these models under this implementation",
        )
    return (
        "INTERMEDIATE",
        "the median distance falls between the two registered thresholds; the "
        "category is recorded as mixed rather than forced",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lens", action="append", required=True,
                        help="role=path")
    parser.add_argument("--out-report", required=True)
    args = parser.parse_args()

    results = {}
    for spec in args.lens:
        role, _, path = spec.partition("=")
        print(f"=== {role}")
        results[role] = analyse_lens(Path(path))
        r = results[role]
        print(f"    layers {r['layers']}  d_model {r['d_model']}")
        print(f"    median ||J-I||/||I||        : {r['median_relative_distance_from_identity']:.4f}")
        print(f"    median identity energy share: {r['median_identity_attributable_share']:.6f}")
        print(f"    median effective rank       : {r['median_effective_rank']:.1f} of {r['d_model']}")

    primary = results.get("positive") or results[list(results)[0]]
    category, meaning = categorise(primary["median_relative_distance_from_identity"])

    # Would OD-016 have fired, had its lower fence been effective? OD-016's
    # quantity is final_identity_distance, which the external configs publish.
    od016 = {
        "what_od016_was_written_to_catch": (
            "a lens whose Jacobian has degenerated toward the identity, i.e. a "
            "J-lens collapsed into an ordinary logit lens"
        ),
        "od016_primary_rule_lower_fence": "negative, therefore non-binding below",
        "od016_registered_lower_gate": OD016_LOWER_GATE,
        "od016_registered_upper_fence": OD016_UPPER_FENCE,
        "external_published_final_identity_distance": {
            "positive_control": 0.578094,
            "depth_test": 0.524690,
            "negative_control": 1.305569,
        },
        "would_od016_have_fired_on_these_lenses": {
            "positive_control": not (OD016_LOWER_GATE <= 0.578094 <= OD016_UPPER_FENCE),
            "depth_test": not (OD016_LOWER_GATE <= 0.524690 <= OD016_UPPER_FENCE),
            "negative_control": not (OD016_LOWER_GATE <= 1.305569 <= OD016_UPPER_FENCE),
        },
        "note": (
            "these are the EXTERNAL lenses' own published values, not ours; ours "
            "was never computed because it requires lens_A, which remains unread"
        ),
    }

    report = {
        "schema_version": "study5-eq2-d1-degeneracy-v1",
        "registration": "d1/D-1_preregistration.json",
        "decision_rule_frozen_before_measurement": {
            "negative_B_if_median_below": NEGATIVE_B_BELOW,
            "negative_A_if_median_at_or_above": NEGATIVE_A_AT_OR_ABOVE,
            "uncorrelated_matched_norm_reference": 1.4142135623730951,
        },
        "results": results,
        "category": category,
        "category_meaning": meaning,
        "od016_retrospective": od016,
        "sealed_lenses_read": False,
        "target_touched": False,
        "cannot_alter_the_terminal_ruling": True,
        "claim_ceiling": (
            "An instrument-validity diagnostic. It licenses no claim of any kind "
            "and cannot alter the terminal ruling."
        ),
    }
    Path(args.out_report).write_bytes(canonical_json_bytes(report))

    print(f"\ncategory : {category}")
    print(f"meaning  : {meaning}")
    print("EQ2-CHECK-D1-DEGENERACY PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
