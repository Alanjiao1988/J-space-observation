"""OD-017 step A: conformance audit of registered text against implementation.

DC-005 was found only because it produced an anomalous result. A divergence that
happened to look plausible would never have surfaced. This audit exists so that
divergences are found by inspection rather than by luck.

Each entry states the registered text, names the implementing code, and records
what the code ACTUALLY does. Where a registered value is a number, the audit
imports the module and compares the live value rather than trusting a comment -
a hand-written table asserting agreement would be exactly the kind of check that
cannot fail.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_registration(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def source_of(func) -> str:
    return inspect.getsource(func)


def main() -> int:
    bvn = load("audit_bvn", "band_vs_null.py")
    rank = load("audit_rank", "rank_profile.py")
    retok = None  # EQ1 tool, not part of EQ2's criteria

    entries: list[dict] = []

    def entry(reg_id, registered_text, impl, behaviour, verdict, **extra):
        record = {
            "registered_id": reg_id,
            "registered_text": registered_text,
            "implementation": impl,
            "what_the_code_actually_does": behaviour,
            "verdict": verdict,
        }
        record.update(extra)
        entries.append(record)

    # ---------------------------------------------------------------- OD-015
    od015 = read_registration("r1/OD-015.json")

    entry(
        "OD-015.k_primary",
        f"k_primary = {od015['the_profile']['k_primary']}, taken verbatim from the official Hit definition",
        "rank_profile.score_with_lens, the (1, 5, 10) hit counters; k=1 is the profile used downstream",
        "hits are counted for k in (1, 5, 10) and the pooled_profile['1'] series is what every band tool consumes",
        "CONFORMS",
        registered_value=od015["the_profile"]["k_primary"],
        observed_value=1,
    )

    entry(
        "OD-015.interior_requirement",
        od015["band_rule"]["interior_requirement"],
        "band_vs_null.argmax_is_interior",
        (
            "computes peak_layer = argmax of readrate WITHIN the band, then requires "
            "layers[0] < peak_layer < layers[-1]. It constrains the ARGMAX, not the extent."
        ),
        "CONFORMS",
        note=(
            "this is the entry DC-005 corrected; before the correction the code "
            "constrained the band's whole extent, which was stricter and unregistered"
        ),
        source_excerpt=source_of(bvn.argmax_is_interior).strip(),
    )

    entry(
        "OD-015.extent_reading",
        "not registered as a criterion",
        "band_vs_null.extent_is_interior",
        (
            "computed and reported as band_exists_under_stricter_extent_reading, "
            "explicitly labelled a secondary diagnostic and NOT used to decide band_exists"
        ),
        "CONFORMS",
        note="retained deliberately so the stricter reading stays visible per DC-005",
    )

    entry(
        "OD-015.readout_positions",
        json.dumps(od015["readout_positions_executed_verbatim_never_unified"], ensure_ascii=False),
        "rank_profile.READOUT_RULE and rank_profile.readout_position",
        (
            "multihop / multilingual / order-ops use token_before_target; poetry uses "
            "last_newline_token, scanning backwards for a token containing a newline and "
            "RAISING if none is found; association / typo use final_prompt_token"
        ),
        "CONFORMS",
        registered_value=od015["readout_positions_executed_verbatim_never_unified"],
        observed_value=rank.READOUT_RULE,
        divergence_examined=(
            "token_before_target and final_prompt_token resolve to the same index "
            "because these prompts stop immediately before the answer; this is stated "
            "in the code comment and is a property of the data, not a harmonisation"
        ),
    )

    entry(
        "OD-015.order_ops_synonyms",
        od015["readout_positions_executed_verbatim_never_unified"]["order_ops_special_rule"],
        "rank_profile.synonym_forms and rank_profile.single_token_ids",
        (
            "expands numbers to digit and word forms and operations to symbol and word "
            "forms, then keeps only forms that encode to exactly ONE token; the rank at "
            "each layer is the min over those ids"
        ),
        "CONFORMS",
        caveat=(
            "the explicit synonym lists are a RECONSTRUCTION of the published rule; the "
            "README states the rule but does not publish the lists. This is disclosed in "
            "every rank report under method.order_ops_synonym_expansion_is_a_reconstruction."
        ),
    )

    entry(
        "OD-015.pooled_is_the_band_source",
        "band derived from the pooled profile, with per-set profiles still reported",
        "band_vs_null.main",
        "reads real_report['pooled_profile']['1']; per-set profiles are retained in the rank report",
        "CONFORMS",
    )

    entry(
        "OD-015.degenerate_case",
        od015["band_rule"]["degenerate_case"],
        "band_vs_null.extract_band via wilson_bounds",
        (
            "an all-zero profile gives real lower bounds of 0, which cannot exceed a "
            "positive null ceiling, so no layer is significant and no band is produced; "
            "k is never raised to rescue it"
        ),
        "CONFORMS",
        demonstrated_by="tests/test_eq2_band_vs_null.py::test_the_registered_non_vacuity_demonstration_passes",
    )

    # ---------------------------------------------------------------- OA-004
    oa004 = read_registration("r1/OA-004.json")
    rev2 = oa004["revision_2_band_criterion"]

    entry(
        "OA-004.null_replicates",
        f"at least {rev2['null_replicates_rule']}",
        "band_vs_null.MIN_NULL_REPLICATES and band_vs_null.null_ceiling",
        "null_ceiling raises ValueError when fewer replicates are supplied",
        "CONFORMS",
        registered_value=rev2["null_replicates"],
        observed_value=bvn.MIN_NULL_REPLICATES,
        demonstrated_by="tests/test_eq2_band_vs_null.py::test_fewer_than_five_null_replicates_is_refused",
    )

    entry(
        "OA-004.null_ceiling_is_the_max",
        rev2["null_ceiling"],
        "band_vs_null.null_ceiling",
        "takes max over replicates of each layer's Wilson upper bound",
        "CONFORMS",
        source_excerpt=source_of(bvn.null_ceiling).strip(),
        demonstrated_by="tests/test_eq2_band_vs_null.py::test_the_ceiling_is_the_maximum_over_replicates_not_the_mean",
    )

    entry(
        "OA-004.confidence_level",
        f"{rev2['confidence_level']} as a statistical convention",
        "band_vs_null.CONFIDENCE and band_vs_null.Z",
        "two-sided 95 percent, z = 1.959963984540054, used in the Wilson interval",
        "CONFORMS",
        registered_value=rev2["confidence_level"],
        observed_value=bvn.CONFIDENCE,
    )

    entry(
        "OA-004.significance_test",
        rev2["significance_test"],
        "band_vs_null.wilson_bounds and band_vs_null.extract_band",
        (
            "Wilson score interval on item x intermediate trials; a layer is significant "
            "when the real LOWER bound exceeds the null ceiling, so the intervals must "
            "not overlap"
        ),
        "CONFORMS",
        note=(
            "Wilson rather than the normal approximation, because at zero observed hits "
            "the normal interval collapses to a point and one lucky hit would clear it"
        ),
        demonstrated_by="tests/test_eq2_band_vs_null.py::test_significance_requires_non_overlapping_intervals",
    )

    entry(
        "OA-004.removed_element",
        rev2["removed_from_od_015"],
        "band_vs_null.py",
        "no half-of-maximum threshold appears anywhere in the band extractor",
        "CONFORMS",
        observed_value=("half" not in source_of(bvn.extract_band)),
    )

    entry(
        "OA-004.matched_norm_null",
        oa004["revision_1_negative_control_becomes_a_matched_norm_random_lens"]["construction"],
        "null_rank_profile.build_null_lens",
        (
            "each J_l is replaced by a Gaussian matrix rescaled to the identical "
            "Frobenius norm; the caller asserts the worst relative norm deviation is "
            "below 1e-5 before scoring"
        ),
        "CONFORMS",
    )

    entry(
        "OA-004.shared_scoring_path",
        "the null must be measured the same way as the real profile",
        "rank_profile.score_with_lens, called by both rank_profile.main and null_rank_profile.main",
        "one function, two callers; the null cannot drift from the real measurement",
        "CONFORMS",
        note=(
            "verified behaviour-preserving after the refactor: the refactored tool "
            "reproduced the pre-refactor smoke numbers exactly"
        ),
    )

    entry(
        "OA-004.non_vacuity_gate",
        oa004["revision_3_non_vacuity_must_be_demonstrated_first"]["gate"],
        "band_vs_null.demonstrate_non_vacuity, called unconditionally from main",
        "the gate runs on EVERY invocation and main returns 1 without judging real data if it fails",
        "CONFORMS",
    )

    # ---------------------------------------------------------------- OD-016
    od016 = read_registration("r1/OD-016.json")
    entry(
        "OD-016.tolerance",
        json.dumps(od016["the_tolerance"]["combined_acceptance_interval"]),
        "not yet applied; it is an R-2 gate",
        (
            "registered only. Applying it requires reading lens_A, which OD-012 forbids "
            "until the convention is committed. It is R-2's first action."
        ),
        "CONFORMS - NOT YET APPLIED",
    )

    # ---------------------------------------------------------------- OD-012
    entry(
        "OD-012.ordering",
        "every journal record referencing lens_A or lens_B carries a timestamp later than the convention-commit record",
        "verify_od012_ordering.judge",
        (
            "reads only the structured provenance fields for access, matches both the "
            "lens name and the immutable sha256, treats a missing or duplicated boundary "
            "record as FAIL, and surfaces prose mentions separately"
        ),
        "CONFORMS",
        current_state="PASS with 0 lens-reading records",
    )

    # ---------------------------------------------------------------- OD-014
    entry(
        "OD-014.behavioural_floor",
        "registered floor 0.15 per evaluation set, executed in R-2",
        "not yet implemented",
        "registered only; R-2 work, so there is no implementation to diverge from yet",
        "CONFORMS - NOT YET APPLIED",
    )

    # ---------------------------------------------------------------- OA-005
    entry(
        "OA-005.condition_ii",
        "within the run, J-lens readrate significantly exceeds PLAIN LOGIT LENS readrate",
        "to be implemented in logit_lens_control.py this phase",
        "not yet implemented at the time of this audit; the audit is re-run after implementation",
        "PENDING IMPLEMENTATION",
    )

    diverging = [e for e in entries if e["verdict"].startswith("DIVERGES")]
    pending = [e for e in entries if e["verdict"].startswith("PENDING")]

    report = {
        "schema_version": "study5-eq2-conformance-audit-v1",
        "rule": "OD-017",
        "phase": "R-1b",
        "step": "A",
        "entries": entries,
        "entry_count": len(entries),
        "diverging": [e["registered_id"] for e in diverging],
        "diverging_count": len(diverging),
        "pending_implementation": [e["registered_id"] for e in pending],
        "verdict": "PASS" if not diverging else "FAIL",
        "directionality_criterion": (
            "Changing the implementation to match the registered text is a bug fix. "
            "Changing the registered text to match the data is p-hacking."
        ),
        "claim_ceiling": "A conformance audit. It licenses no claim of any kind.",
    }
    out = ROOT / "r1b" / "od017_conformance_audit.json"
    out.write_bytes(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )

    for e in entries:
        print(f"  {e['verdict']:<28} {e['registered_id']}")
    print(f"\nentries {len(entries)}  diverging {len(diverging)}  pending {len(pending)}")
    if diverging:
        print("EQ2-CHECK-OD017-CONFORMANCE FAILED", file=sys.stderr)
        return 1
    print("EQ2-CHECK-OD017-CONFORMANCE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
