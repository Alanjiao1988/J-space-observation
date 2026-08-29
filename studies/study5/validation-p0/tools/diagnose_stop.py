"""Diagnostic characterisation of the two P-0 stop conditions.

This tool CHANGES NOTHING. It re-decides nothing, it recomputes no verdict
under any alternative rule, and it touches no registered constant. It exists
because a stop that says only "a gate failed" leaves the operator unable to
tell a broken instrument from a mis-specified threshold, and those have
opposite consequences.

Motivation asymmetry, disclosed as OD-018 requires: I would not have written
this file had both gates passed. Its legitimacy rests on the fact that it
cannot change the outcome - the registered rule has already run, its verdict
is committed, and nothing here is permitted to supersede it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision", required=True)
    parser.add_argument("--merged", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    decision = json.loads(Path(args.decision).read_text(encoding="utf-8"))
    merged = json.loads(Path(args.merged).read_text(encoding="utf-8"))
    summary = decision["summary"]
    curves = merged["curves"]
    layers = merged["layers"]

    # ---- defect 1: the ceiling is dominated by one site ---------------------
    per_site_max: dict[str, dict[str, float]] = {}
    for key in sorted(summary):
        if key == "REAL":
            continue
        per_site_max[key] = {
            site: max(stats["ucb"] for stats in by_layer.values())
            for site, by_layer in summary[key].items()
        }
    across_nulls = {}
    for site in ("CUE", "BRIDGE", "READOUT"):
        values = [row[site] for row in per_site_max.values() if site in row]
        if values:
            across_nulls[site] = max(values)

    # ---- defect 2: is the integrity offset a patch effect or a baseline one? -
    # PREFIX at the LAST layer is a structurally guaranteed no-op that is
    # stronger than the causal-masking argument: the last block's output at any
    # non-final position is read by nothing at all, because only the final
    # position reaches the head. If that reads non-zero, the offset cannot have
    # come from the patch.
    last_layer = max(layer for layer in layers)
    prefix = summary["REAL"]["PREFIX"]
    structural_no_op = prefix[str(last_layer)]
    embedding_no_op = prefix["-1"]

    raw_last = curves["REAL"]["PREFIX"][str(last_layer)]
    raw_emb = curves["REAL"]["PREFIX"]["-1"]
    per_unit_identical = all(
        abs(a - b) < 1e-9
        for cluster in raw_last
        for a, b in zip(raw_last[cluster], raw_emb.get(cluster, []))
    )
    nonzero_units = sum(
        1 for cluster in raw_last for value in raw_last[cluster] if abs(value) > 1e-6
    )
    total_units = sum(len(v) for v in raw_last.values())

    report = {
        "schema_version": "study5-p0-diagnostic-v1",
        "phase": "P-0",
        "status": "DIAGNOSTIC ONLY. No criterion is changed and no verdict is recomputed.",
        "motivation_asymmetry": (
            "this characterisation would not have been written had both gates "
            "passed; it is admissible because it cannot change the outcome, "
            "which was produced by the registered rule and is already committed"
        ),

        "registered_outcome_as_produced": {
            "verdict_from_the_registered_rule": decision["verdict"],
            "verdict_is_reportable": False,
            "why_not": (
                "the registered gates did not all pass, and the registration "
                "states that a verdict means nothing until they do"
            ),
            "ceiling": decision["ceiling"],
            "ceiling_source": decision["ceiling_source"],
            "gates": decision["gates"],
        },

        "defect_1_the_ceiling_is_governed_by_a_site_it_was_never_meant_to_govern": {
            "what_the_registration_says": (
                "the ceiling is the maximum over every null construction, every "
                "replicate, every site other than PREFIX, and every layer"
            ),
            "what_that_produced": decision["ceiling"],
            "worst_null_upper_bound_per_site": across_nulls,
            "why_it_happens": (
                "a norm-matched random vector written at the READOUT position "
                "destroys the state the answer is read from, and the normalised "
                "restoration of a destroyed run is unbounded; the same "
                "construction at BRIDGE perturbs a position the answer is not "
                "read from and stays small. Taking one scalar maximum across "
                "sites therefore imports the READOUT scale into a BRIDGE test"
            ),
            "why_the_OD_011_demonstration_did_not_catch_it": (
                "the demonstration used synthetic nulls at sigma 0.05 and 0.15, "
                "which is where an in-distribution null sits; it did not "
                "anticipate that one construction at one site would be an order "
                "of magnitude wider. The demonstration proved the rule cannot "
                "manufacture a positive from a quiet null, and that remains "
                "true; it did not prove the ceiling is on the right scale"
            ),
            "this_is_a_registration_error_not_an_implementation_error": True,
            "the_implementation_did_exactly_what_was_registered": True,
            "why_it_is_not_repaired_here": (
                "the BRIDGE means are already in hand. Choosing a per-site "
                "ceiling now would move the registered text toward the data, "
                "which the directionality precedent calls p-hacking regardless "
                "of whether the new rule is better. The registration itself "
                "lists 'any situation in which the operator wishes to revise a "
                "pre-registered criterion' as a stop-and-ask condition"
            ),
        },

        "defect_2_the_integrity_offset_is_in_the_baseline_not_in_the_patch": {
            "gate_value": decision["gates"]["integrity"]["max_abs_mean"],
            "tolerance": decision["gates"]["integrity"]["tolerance"],
            "the_decisive_observation": {
                "site": "PREFIX",
                "layer": last_layer,
                "why_it_is_a_guaranteed_no_op": (
                    "the last block's output at a non-final position is read by "
                    "nothing whatsoever, because only the final position reaches "
                    "the unembedding. This is stronger than the causal-masking "
                    "argument: it holds even if the patched values were arbitrary"
                ),
                "observed_mean": structural_no_op["mean"],
                "observed_lcb": structural_no_op["lcb"],
                "observed_ucb": structural_no_op["ucb"],
                "units_with_a_non_zero_value": nonzero_units,
                "units_total": total_units,
            },
            "embedding_layer_no_op_for_comparison": {
                "layer": -1,
                "why_it_is_also_a_no_op": (
                    "the patched positions carry identical tokens, so their "
                    "embeddings are bit-identical"
                ),
                "observed_mean": embedding_no_op["mean"],
            },
            "the_two_no_ops_agree_unit_by_unit": per_unit_identical,
            "conclusion": (
                "a patch that provably cannot influence the output still moves "
                "the metric, so the offset is not produced by patching. It is "
                "produced by the comparison: the clean baseline LD is measured "
                "in a batch-of-one forward while every patched LD is measured "
                "in a batch-of-48 forward, and bfloat16 kernels do not select "
                "the same reduction order at both batch sizes"
            ),
            "consequence_for_every_curve": (
                "each unit's restoration carries a constant additive offset of "
                "this size. It is common to the real construction and to both "
                "null constructions, so it does not favour either, but it is "
                "uncontrolled and the registered tolerance is right to refuse it"
            ),
            "this_is_an_implementation_error": True,
            "the_fix_that_is_NOT_applied_here": (
                "measure the clean baseline inside the same batch as the "
                "patched runs, by including an explicit self-patch job. That is "
                "an implementation change in the direction the precedent allows, "
                "but it requires re-running the measurement, and the "
                "registration says to stop and report rather than self-repair"
            ),
        },

        "what_survived_intact": {
            "harness_positive_control": {
                "verdict": decision["gates"]["harness_positive_control"]["verdict"],
                "mean": decision["gates"]["harness_positive_control"]["mean"],
                "lcb": decision["gates"]["harness_positive_control"]["lcb"],
                "what_it_establishes": (
                    "patching the differing positions at the embedding output "
                    "converts the recipient run into the donor run, recovering "
                    "0.986 of the contrast. The patching instrument moves what "
                    "it claims to move"
                ),
                "why_it_matters_beyond_this_phase": (
                    "this is the first passing positive control obtained "
                    "anywhere in Study 5. It certifies the INSTRUMENT only, and "
                    "says nothing about whether the model computes an "
                    "intermediate"
                ),
            },
            "independence_from_the_instrument_under_test": (
                merged["instrument_under_test_imported"] is False
            ),
            "units_measured": merged["n_units_measured"],
            "units_dropped": merged["n_units_dropped"],
            "clusters": merged["n_clusters"],
        },

        "claim_ceiling": (
            "A diagnostic record for a halted phase. It licenses no claim of "
            "any kind, and it is not a finding."
        ),
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print("registered verdict (NOT reportable, gates failed):", decision["verdict"])
    print("ceiling:", round(decision["ceiling"], 6), decision["ceiling_source"])
    print("worst null ucb per site:", {k: round(v, 4) for k, v in across_nulls.items()})
    print(
        f"PREFIX at layer {last_layer} (a guaranteed no-op) reads "
        f"{structural_no_op['mean']:.6f}; embedding no-op reads "
        f"{embedding_no_op['mean']:.6f}; identical unit by unit: "
        f"{per_unit_identical}"
    )
    print("P0-DIAGNOSTIC WRITTEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
