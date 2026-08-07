#!/usr/bin/env python3
"""Emit exact model-free Study 2 sample-size sensitivity calculations."""

from __future__ import annotations

import argparse
import json
import math
import os
from statistics import NormalDist
from typing import Any


CHANCE = 0.25
ALPHAS = (0.05, 0.025)
POWER_TARGETS = (0.80, 0.90)
ACCURACY_GRID = (0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75)
FLOOR_GRID = (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)
DISCORDANT_COUNTS = (26, 51, 77, 102, 128)


def binomial_upper_tail(n: int, probability: float, threshold: int) -> float:
    if n <= 0 or not 0 <= probability <= 1 or not 0 <= threshold <= n + 1:
        raise ValueError("invalid binomial-tail inputs")
    return math.fsum(
        math.comb(n, successes)
        * probability**successes
        * (1 - probability) ** (n - successes)
        for successes in range(threshold, n + 1)
    )


def critical_successes(n: int, null_probability: float, alpha: float) -> int:
    for threshold in range(n + 1):
        if binomial_upper_tail(n, null_probability, threshold) <= alpha:
            return threshold
    return n + 1


def probability_for_power(
    *,
    n: int,
    threshold: int,
    target_power: float,
    null_probability: float,
) -> float:
    lower = null_probability
    upper = 1.0
    for _ in range(120):
        midpoint = (lower + upper) / 2
        if binomial_upper_tail(n, midpoint, threshold) >= target_power:
            upper = midpoint
        else:
            lower = midpoint
    return upper


def rounded(value: float) -> float:
    return round(value, 12)


def exact_binomial_section() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for n in (64, 256):
        for alpha in ALPHAS:
            threshold = critical_successes(n, CHANCE, alpha)
            rows.append(
                {
                    "n": n,
                    "one_sided_alpha": alpha,
                    "critical_successes": threshold,
                    "critical_accuracy": rounded(threshold / n),
                    "null_upper_tail": rounded(binomial_upper_tail(n, CHANCE, threshold)),
                    "power_by_true_accuracy": {
                        f"{probability:.2f}": rounded(
                            binomial_upper_tail(n, probability, threshold)
                        )
                        for probability in ACCURACY_GRID
                    },
                }
            )
    return rows


def substantive_floor_section() -> dict[str, Any]:
    n = 256
    threshold = 128
    return {
        "n": n,
        "observed_success_threshold": threshold,
        "observed_accuracy_floor": 0.50,
        "pass_probability_by_true_accuracy": {
            f"{probability:.2f}": rounded(
                binomial_upper_tail(n, probability, threshold)
            )
            for probability in FLOOR_GRID
        },
        "scope": (
            "Accuracy-floor component only. Full NT_PASS also conjunctively requires "
            "execution integrity, balance, Wilson lower95 above 0.25, and margin "
            "bootstrap lower95 above zero."
        ),
    }


def paired_difference_section() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    n = 256
    for discordant in DISCORDANT_COUNTS:
        for alpha in ALPHAS:
            threshold = critical_successes(discordant, 0.5, alpha)
            sensitivity = []
            for target_power in POWER_TARGETS:
                target_win_probability = probability_for_power(
                    n=discordant,
                    threshold=threshold,
                    target_power=target_power,
                    null_probability=0.5,
                )
                marginal_difference = (
                    discordant / n * (2 * target_win_probability - 1)
                )
                sensitivity.append(
                    {
                        "target_power": target_power,
                        "minimum_target_win_probability_among_discordants": rounded(
                            target_win_probability
                        ),
                        "minimum_marginal_accuracy_difference": rounded(
                            marginal_difference
                        ),
                    }
                )
            rows.append(
                {
                    "n_pairs": n,
                    "discordant_pairs": discordant,
                    "discordant_pair_proportion": rounded(discordant / n),
                    "one_sided_alpha": alpha,
                    "critical_target_wins": threshold,
                    "null_upper_tail": rounded(
                        binomial_upper_tail(discordant, 0.5, threshold)
                    ),
                    "sensitivity": sensitivity,
                }
            )
    return rows


def mechanistic_section() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    n = 128
    normal = NormalDist()
    for alpha in ALPHAS:
        critical_z = normal.inv_cdf(1 - alpha)
        for target_power in POWER_TARGETS:
            power_z = normal.inv_cdf(target_power)
            rows.append(
                {
                    "n_pairs": n,
                    "one_sided_alpha": alpha,
                    "target_power": target_power,
                    "minimum_standardized_paired_effect_normal_approximation": rounded(
                        (critical_z + power_z) / math.sqrt(n)
                    ),
                }
            )
    return rows


def build_report(source_commit: str, source_tree: str, acr_run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "jspace-study2-stage-p-sensitivity/v1",
        "status": "ADVISORY_DESIGN_SENSITIVITY_NOT_SCIENTIFIC_EVIDENCE",
        "source_commit": source_commit,
        "source_tree": source_tree,
        "acr_run_id": acr_run_id,
        "conventions": {
            "exact_binomial": "P(X>=k) from the finite binomial sum",
            "paired_binary": (
                "Conditional exact sign/McNemar sensitivity with a fixed number of "
                "discordant pairs; marginal accuracy difference is "
                "q*(2*pi_target_win-1)."
            ),
            "mechanistic": (
                "Normal approximation for a standardized paired mean effect; actual "
                "bootstrap power depends on the finite effect distribution."
            ),
            "alpha_values": list(ALPHAS),
            "power_targets": list(POWER_TARGETS),
        },
        "exact_binomial_against_chance": exact_binomial_section(),
        "confirmation_accuracy_floor": substantive_floor_section(),
        "paired_target_control_sensitivity": paired_difference_section(),
        "mechanistic_pair_sensitivity": mechanistic_section(),
        "conjunctive_gate_interpretation": [
            "Each reported component sensitivity is marginal, not composite power.",
            "Requiring all gates to pass does not inflate a union-style false-positive rate, but it can sharply reduce power.",
            "Composite power cannot be identified without the joint distribution and correlations among accuracy, margin, patch, probe, control, and family gates.",
            "Passing-probability calculations do not authorize changing a registered sample size, threshold, task, model, pair, or control.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--acr-run-id", default=os.environ.get("ACR_RUN_ID", ""))
    args = parser.parse_args()
    if len(args.source_commit) != 40 or len(args.source_tree) != 40:
        raise SystemExit("source commit and tree must be full 40-character identities")
    print(
        json.dumps(
            build_report(args.source_commit, args.source_tree, args.acr_run_id),
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
