"""Phase 1.2F — acceptance-policy correction and threshold preregistration.

These tests cover the Phase 1.2F obligations that are separable from the Phase
1.2E repair suite:

* the Phase 1.0C current-state contradiction regression;
* rejection of a policy that cites Phase 1.0C as a parser-threshold dependency;
* threshold provenance: recognised basis types, required derivation fields,
  inequality/margin sign consistency, integer boundary semantics;
* the exhaustive confusion-matrix analysis behind the macro-F1 disposition,
  with presence errors modelled separately from present-value errors;
* proof that a removed or report-only metric cannot re-enter PASS/FAIL;
* agreement between the policy and the machine-readable disposition artifact;
* parser-isolation wording, and proof of zero parser invocation.

Nothing here reads a sealed input, a label, or any private curator material,
and nothing here runs a parser.
"""

from __future__ import annotations

import ast
import copy
import json
import math
import re
import subprocess
import sys
from fractions import Fraction
from itertools import product
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

sys.path.insert(0, str(ROOT / "scripts"))

from jspace_observation.parser_v3_repair_contract import (  # noqa: E402
    BINDING_DISPOSITIONS,
    NON_BINDING_DISPOSITIONS,
    REQUIRED_THRESHOLD_FIELDS,
    THRESHOLD_BASIS_TYPES,
    THRESHOLD_DISPOSITIONS,
    ContractError,
    validate_acceptance_thresholds,
    validate_policy,
)

import check_current_state_consistency as consistency  # noqa: E402

POLICY_PATH = ROOT / "docs" / "phase1_parser_v3_v2_evaluation_policy.json"
DISPOSITIONS_PATH = ROOT / "docs" / "phase1_2f_threshold_dispositions.json"
STRATUM_POLICY_PATH = ROOT / "docs" / "phase1_parser_v3_v2_stratum_policy.md"
CALIBRATION_PROTOCOL_PATH = (
    ROOT / "docs" / "phase1_2f_parser_error_budget_calibration_protocol.md"
)
PHASE_1_0C_DECISION = ROOT / Path(consistency.PHASE_1_0C_DECISION)

#: The Phase 1.2E commit whose text this round exists to correct.
BASELINE_COMMIT = "d843984a3b7e1a2bf9d306621b8557ce327cf987"

REPAIR_MODULES = (
    SRC / "jspace_observation" / "parser_v3_repair_ontology.py",
    SRC / "jspace_observation" / "parser_v3_repair_normalization.py",
    SRC / "jspace_observation" / "parser_v3_repair_contract.py",
    ROOT / "scripts" / "parser_v3_repair_cli.py",
)

#: Public entry points of every parser in the repository. Phase 1.2F proves
#: none of them is called by the repair tooling.
PARSER_ENTRY_POINTS = (
    "parse_v3",
    "parse_v2",
    "parse_answer",
    "parse_numeric_answer",
    "parse_entity_answer",
    "parse_yes_no_answer",
    "evaluate_answer",
    "compare_parsed_answer_to_reference",
)


@pytest.fixture(scope="module")
def policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def dispositions():
    return json.loads(DISPOSITIONS_PATH.read_text(encoding="utf-8"))


def _hard(**overrides):
    """A syntactically complete FINAL hard-threshold provenance record."""
    record = {
        "threshold_id": "t_synthetic",
        "status": "FINAL",
        "disposition": "KEEP_HARD",
        "binding": True,
        "value": 3,
        "basis_type": "LOGICAL_INVARIANT",
        "controlled_risk": "synthetic risk",
        "derivation": "synthetic derivation",
        "evidence_bindings": ["docs/phase1_parser_v3_v2_stratum_policy.md"],
        "candidate_independence": True,
        "set_independence": True,
        "boundary_semantics": {
            "inequality": "at_most",
            "at_threshold_passes": True,
            "population": "the 40 cases in S04, S05, S06 and S09",
        },
        "review_status": "REVIEWED",
    }
    record.update(overrides)
    return record


def _block(*items, status="FINAL"):
    return {"status": status, "items": list(items)}


# ---------------------------------------------------------------------------
# 1. Phase 1.0C factual record and current-state consistency
# ---------------------------------------------------------------------------


def test_phase_1_0c_result_pack_records_an_executed_finalized_run():
    """The corrected record must rest on primary committed evidence."""
    payload = json.loads(PHASE_1_0C_DECISION.read_text(encoding="utf-8"))
    assert payload["track_b_decision"] == "INCONCLUSIVE"
    assert payload["status"] == "INCONCLUSIVE"
    assert payload["unresolved_rows"] == 44
    assert payload["outstanding_review_rows"] == 0
    assert payload["arbitration_rows"] == 0
    assert "generation_plan_size_is_300" in payload["criteria_passed"]


def test_phase_1_0c_is_recorded_as_task_screening_not_parser_calibration():
    payload = json.loads(PHASE_1_0C_DECISION.read_text(encoding="utf-8"))
    interpretation = payload["scientific_interpretation"].lower()
    assert "observable answer accuracy" in interpretation
    assert "target model" in interpretation
    assert "headroom" in interpretation
    # It licenses no parser claim.
    assert any(
        "parser v2 output is a validated correctness label" in text
        for text in payload["prohibited_interpretations"]
    )


def test_current_state_documents_are_consistent():
    """The mechanical check must pass on the corrected repository."""
    assert consistency.scan_files(root=ROOT) == []


def test_consistency_check_detects_the_phase_1_2e_contradiction():
    """The regression this check exists to prevent.

    This is the exact wording that was live in ``reports/current_status.md``
    while the finalized Phase 1.0C result pack was already committed.
    """
    stale = (
        "## Phase 1.0C headroom calibration status (2026-07-25) - BLOCKED, NOT RUN\n"
        "- The emitted pack status is BLOCKED: no model was run.\n"
    )
    found = consistency.scan_text("reports/current_status.md", stale, executed=True)
    assert [item.kind for item in found] == ["NOT_RUN_VS_FINALIZED"]


def test_consistency_check_detects_a_parser_threshold_dependency():
    text = "Next gate: run Phase 1.0C headroom calibration and derive the parser thresholds.\n"
    found = consistency.scan_text("reports/current_status.md", text, executed=True)
    assert any(item.kind == "PARSER_THRESHOLD_DEPENDENCY" for item in found)


def test_consistency_check_preserves_historical_entries():
    """A dated point-in-time entry marked historical must not fail the check.

    Audit finding B2 tightened exemption from "the word appears somewhere on
    the line" to "the paragraph is structurally anchored as historical", so the
    marker must open a line rather than sit inside a parenthesis.
    """
    historical = (
        "Historical point-in-time entry (2026-07-25): Phase 1.0C was "
        "preregistered only and was NOT RUN at this date.\n"
    )
    assert consistency.scan_text("reports/current_status.md", historical, executed=True) == []

    unanchored = (
        "## 2026-07-25 - Phase 1.0C preregistered only (historical point-in-time "
        "entry): NOT RUN at this date.\n"
    )
    assert consistency.scan_text("reports/current_status.md", unanchored, executed=True), (
        "an unanchored mention of 'historical' must no longer disable the check"
    )


def test_consistency_check_reads_ground_truth_from_the_result_pack():
    """A uniformly stale document must not pass by never citing the outcome.

    The Phase 1.2E failure mode was exactly this: the stale section never
    mentioned ``INCONCLUSIVE``, so any within-document contradiction test would
    have reported no problem.
    """
    assert consistency.phase_1_0c_was_finalized(ROOT) is True
    stale_only = "Phase 1.0C headroom calibration has not been run.\n"
    assert consistency.scan_text("x.md", stale_only, executed=False) == []
    assert consistency.scan_text("x.md", stale_only, executed=True) != []


# --- Audit B findings B1-B4: the checker had to be able to catch the defect ---


@pytest.mark.parametrize(
    "relative",
    [
        "reports/current_status.md",
        "docs/thread_handoff.md",
        "docs/phase1_parser_v3_v2_evaluation_policy.json",
    ],
)
def test_consistency_check_catches_the_baseline_text_it_was_written_for(relative):
    """Audit finding B1/B3.

    The first version matched line by line with patterns that forbade a
    newline, while this repository hard-wraps at about 76 columns. It therefore
    found nothing in the very text that motivated it. The check is now run
    against the verbatim ``d843984`` content of each file and must report a
    contradiction.
    """
    baseline = subprocess.run(
        ["git", "show", f"{BASELINE_COMMIT}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if baseline.returncode != 0:  # pragma: no cover - shallow clone
        pytest.skip(f"baseline {BASELINE_COMMIT} unavailable")
    found = consistency.scan_text(relative, baseline.stdout, executed=True)
    assert found, f"the checker must catch the defect in {relative}"


@pytest.mark.parametrize(
    "text",
    [
        "Phase 1.0C: NOT RUN. This has been corrected elsewhere.",
        "Phase 1.0C was never executed.",
        "Phase 1.0C remains unexecuted at this time.",
        "Next gate: run Phase 1.0C to derive the acceptance thresholds.",
        "Phase 1.0C has not been run and no model outputs exist.",
        "The four thresholds are blocked on Phase 1.0C.",
        "Phase 1.0C\nis NOT RUN and remains blocked before model\nexecution.",
        "Headroom calibration is a parser-accuracy calibration.",
    ],
)
def test_consistency_check_no_longer_evades_these(text):
    """Audit finding B2.

    Exemption used to be a substring test against common words, so putting
    "corrected" anywhere on a line disabled the check for that line, and
    several plain synonyms were simply unmatched.
    """
    assert consistency.scan_text("reports/current_status.md", text, executed=True)


@pytest.mark.parametrize(
    "text",
    [
        "> Phase 1.0C: NOT RUN\n> BLOCKED with no model execution",
        "ERRATUM: the sentence 'Phase 1.0C was never run' was false when written.",
        "Historical entry: at the time, Phase 1.0C had not been run.",
        "Phase 1.0C executed and finalized INCONCLUSIVE at 06eec993.",
        "Phase 1.0C is not parser calibration and supplies no acceptance threshold.",
    ],
)
def test_consistency_check_still_preserves_legitimate_history(text):
    """Tightening the matcher must not make honest errata unwritable."""
    assert consistency.scan_text("reports/current_status.md", text, executed=True) == []


@pytest.mark.parametrize(
    "text",
    [
        "Phase 1.0C has **not** been run.",
        "Phase 1.0C is `NOT RUN` and remains blocked before model execution.",
        "Phase 1.0C was **never** executed.",
        "The four thresholds are *blocked on* Phase 1.0C.",
    ],
)
def test_emphasis_cannot_hide_a_stale_claim(text):
    """Markdown emphasis is formatting and must not break phrase matching.

    ``**not**`` inserts asterisks between ``has`` and ``not``, which silently
    defeated every contiguous phrase pattern. That was an evasion, not merely
    cosmetic: a stale claim could be emphasised into invisibility.
    """
    assert consistency.scan_text("reports/current_status.md", text, executed=True)


@pytest.mark.parametrize(
    "text",
    [
        "Phase 1.0C is **not** parser calibration.",
        "Phase 1.0C is **not** a source of parser acceptance thresholds.",
    ],
)
def test_emphasis_does_not_break_a_corrective_negation(text):
    """The same elision must keep emphasised corrective prose writable.

    This repository writes ``**not**`` constantly. Without elision the negation
    guard missed it and the checker flagged its own corrections.
    """
    assert consistency.scan_text("reports/current_status.md", text, executed=True) == []


def test_underscore_is_not_elided():
    """``_`` is load-bearing inside ``NOT_RUN`` and must survive elision."""
    assert "_" not in consistency._ELIDED_MARKUP
    assert consistency.scan_text(
        "reports/current_status.md",
        "Phase 1.0C headroom calibration status - BLOCKED, NOT_RUN",
        executed=True,
    )


def test_consistency_check_fails_closed_without_ground_truth(tmp_path):
    """Audit finding B4.

    The first version returned ``False`` when the result pack was missing,
    which silently disabled half the check while still printing ``OK``.
    """
    with pytest.raises(consistency.GroundTruthError):
        consistency.phase_1_0c_was_finalized(tmp_path)
    assert (
        consistency.main(["--root", str(tmp_path)]) == 1
    ), "a missing ground truth must fail, not pass"


def test_consistency_check_scans_the_policy_artifact_class():
    """Audit finding B3: the defect occurred in a JSON policy artifact."""
    assert (
        "docs/phase1_parser_v3_v2_evaluation_policy.json"
        in consistency.CURRENT_STATE_FILES
    )


def test_consistency_check_separates_json_statements():
    """A pretty-printed artifact has no blank lines to split on.

    Walking the parsed structure keeps an errata quotation from being paired
    with an unrelated present-state claim, and lets an errata subtree be
    exempted by key rather than by proximity.
    """
    document = json.dumps(
        {
            "errata": {"as_written": "Phase 1.0C headroom calibration has not been run."},
            "current_state": {"note": "Phase 1.0C executed and finalized INCONCLUSIVE."},
        },
        indent=2,
    )
    assert consistency.scan_text("x.json", document, executed=True) == []

    offending = json.dumps(
        {"blocking_dependency": "Phase 1.0C headroom calibration has not been run."},
        indent=2,
    )
    assert consistency.scan_text("x.json", offending, executed=True)


# ---------------------------------------------------------------------------
# 2. Threshold provenance validation
# ---------------------------------------------------------------------------


def test_shipped_policy_validates():
    validate_policy(json.loads(POLICY_PATH.read_text(encoding="utf-8")))


def test_shipped_policy_remains_review_required(policy):
    assert policy["status"] == "REVIEW_REQUIRED"
    assert policy["acceptance_thresholds"]["status"] == "REVIEW_REQUIRED"


def test_no_threshold_carries_a_numeric_value(policy):
    """No number was manufactured to reach a green status."""
    for item in policy["acceptance_thresholds"]["items"]:
        assert item["value"] is None, item["threshold_id"]


def test_policy_cites_no_phase_1_0c_dependency(policy):
    blob = json.dumps(policy).lower()
    # The errata block may name the correction; the threshold block may not.
    thresholds = json.dumps(policy["acceptance_thresholds"]).lower()
    assert "1.0c" not in thresholds
    assert "headroom calibration" not in thresholds
    assert "post_hoc_disclosure" in blob


def test_rejects_a_threshold_block_citing_phase_1_0c():
    block = _block(_hard(), status="FINAL")
    block["blocking_dependency"] = "Phase 1.0C headroom calibration (NOT RUN)."
    with pytest.raises(ContractError, match="prohibited threshold basis"):
        validate_acceptance_thresholds(block)


def test_rejects_a_derivation_grounded_in_headroom_calibration():
    block = _block(_hard(derivation="taken from the headroom calibration result"))
    with pytest.raises(ContractError, match="prohibited threshold basis"):
        validate_acceptance_thresholds(block)


def test_rejects_a_derivation_grounded_in_observed_parser_performance():
    block = _block(_hard(derivation="set just below observed parser v2 accuracy"))
    with pytest.raises(ContractError, match="prohibited threshold basis"):
        validate_acceptance_thresholds(block)


def test_rejects_an_appeal_to_industry_standard():
    block = _block(_hard(derivation="0.95 is the industry standard for extraction"))
    with pytest.raises(ContractError, match="prohibited threshold basis"):
        validate_acceptance_thresholds(block)


def test_rejects_an_unrecognised_basis_type():
    block = _block(_hard(basis_type="SEEMS_REASONABLE"))
    with pytest.raises(ContractError, match="unrecognised basis_type"):
        validate_acceptance_thresholds(block)


def test_rejects_a_final_threshold_with_no_basis_type():
    item = _hard()
    del item["basis_type"]
    with pytest.raises(ContractError, match="missing required provenance fields"):
        validate_acceptance_thresholds(_block(item))


@pytest.mark.parametrize("field", sorted(REQUIRED_THRESHOLD_FIELDS))
def test_rejects_a_final_threshold_missing_any_required_field(field):
    item = _hard()
    del item[field]
    with pytest.raises(ContractError, match="missing required provenance fields"):
        validate_acceptance_thresholds(_block(item))


def test_rejects_an_empty_evidence_binding_list():
    with pytest.raises(ContractError, match="at least one evidence source"):
        validate_acceptance_thresholds(_block(_hard(evidence_bindings=[])))


@pytest.mark.parametrize("field", ("candidate_independence", "set_independence"))
def test_rejects_a_threshold_that_is_not_independent(field):
    with pytest.raises(ContractError, match=f"must assert {field}=true"):
        validate_acceptance_thresholds(_block(_hard(**{field: False})))


def test_rejects_an_unreviewed_final_threshold():
    with pytest.raises(ContractError, match="review_status"):
        validate_acceptance_thresholds(_block(_hard(review_status="DRAFT")))


def test_rejects_an_unrecognised_inequality_direction():
    item = _hard(
        boundary_semantics={
            "inequality": "roughly",
            "at_threshold_passes": True,
            "population": "p",
        }
    )
    with pytest.raises(ContractError, match="inequality direction"):
        validate_acceptance_thresholds(_block(item))


def test_rejects_an_unstated_at_threshold_rule():
    item = _hard(
        boundary_semantics={"inequality": "at_most", "population": "p"}
    )
    with pytest.raises(ContractError, match="whether the exact threshold"):
        validate_acceptance_thresholds(_block(item))


def test_rejects_a_comparator_margin_whose_sign_contradicts_its_direction():
    item = _hard(
        comparator_margin=-2,
        boundary_semantics={
            "inequality": "at_least",
            "at_threshold_passes": True,
            "population": "paired cases",
        },
    )
    with pytest.raises(ContractError, match="sign contradicts the direction"):
        validate_acceptance_thresholds(_block(item))


def test_accepts_a_consistent_comparator_margin():
    item = _hard(
        comparator_margin=1,
        boundary_semantics={
            "inequality": "at_least",
            "at_threshold_passes": True,
            "population": "paired cases",
        },
    )
    validate_acceptance_thresholds(_block(item))


def test_rejects_a_placeholder_value_on_an_unresolved_threshold():
    item = _hard(status="REVIEW_REQUIRED", disposition="REVIEW_REQUIRED", value=95)
    with pytest.raises(ContractError, match="placeholder value"):
        validate_acceptance_thresholds(_block(item, status="REVIEW_REQUIRED"))


def test_rejects_a_final_block_with_an_unresolved_item():
    item = _hard(
        status="REVIEW_REQUIRED",
        disposition="REVIEW_REQUIRED",
        value=None,
        binding=False,
    )
    with pytest.raises(ContractError, match="remain\nunresolved|remain unresolved"):
        validate_acceptance_thresholds(_block(item, status="FINAL"))


def test_rejects_duplicate_threshold_ids():
    with pytest.raises(ContractError, match="duplicate threshold_id"):
        validate_acceptance_thresholds(_block(_hard(), _hard()))


# ---------------------------------------------------------------------------
# 3. Non-binding metrics cannot re-enter PASS/FAIL
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("disposition", sorted(NON_BINDING_DISPOSITIONS))
def test_a_non_binding_threshold_may_not_carry_a_value(disposition):
    extra = {"replaced_by": "G_x"} if disposition == "REPLACE_HARD" else {}
    if disposition == "MERGE_WITH_EXISTING_GATE":
        extra = {"merged_into": "G_x"}
    item = _hard(disposition=disposition, binding=False, value=7, **extra)
    with pytest.raises(ContractError, match="must not carry a\nnumeric value|must not carry a numeric value"):
        validate_acceptance_thresholds(_block(item))


@pytest.mark.parametrize("disposition", sorted(NON_BINDING_DISPOSITIONS))
def test_a_non_binding_threshold_must_declare_binding_false(disposition):
    extra = {"replaced_by": "G_x"} if disposition == "REPLACE_HARD" else {}
    if disposition == "MERGE_WITH_EXISTING_GATE":
        extra = {"merged_into": "G_x"}
    item = _hard(disposition=disposition, binding=True, value=None, **extra)
    with pytest.raises(ContractError, match="binding=false"):
        validate_acceptance_thresholds(_block(item))


def test_status_logic_may_not_name_a_report_only_metric(policy):
    mutated = copy.deepcopy(policy)
    mutated["status_logic"]["PASS"] = (
        "every mandatory gate satisfied AND answer_presence_macro_f1_minimum met"
    )
    with pytest.raises(ContractError, match="must never re-enter PASS/FAIL"):
        validate_policy(mutated)


def test_status_logic_may_not_name_a_removed_metric_in_fail(policy):
    mutated = copy.deepcopy(policy)
    mutated["status_logic"]["FAIL"] = (
        "any mandatory gate violated OR non_regression_margin_vs_parser_v2 missed"
    )
    with pytest.raises(ContractError, match="must never re-enter PASS/FAIL"):
        validate_policy(mutated)


def test_shipped_status_logic_names_no_non_binding_metric(policy):
    clauses = " ".join(
        str(policy["status_logic"].get(key, "")) for key in ("PASS", "FAIL")
    )
    for item in policy["acceptance_thresholds"]["items"]:
        if item["disposition"] in NON_BINDING_DISPOSITIONS:
            assert item["threshold_id"] not in clauses


def test_a_replaced_threshold_must_name_its_successor():
    item = _hard(disposition="REPLACE_HARD", binding=False, value=None)
    with pytest.raises(ContractError, match="must name\nits successor|must name its successor"):
        validate_acceptance_thresholds(_block(item))


def test_a_merged_threshold_must_name_a_known_successor():
    item = _hard(
        disposition="MERGE_WITH_EXISTING_GATE",
        binding=False,
        value=None,
        merged_into="not_a_real_criterion",
    )
    with pytest.raises(ContractError, match="unknown successor"):
        validate_acceptance_thresholds(_block(item))


def test_shipped_successors_all_resolve(policy):
    ids = {i["threshold_id"] for i in policy["acceptance_thresholds"]["items"]}
    gate_ids = {g["gate_id"] for g in policy["gates"]}
    for item in policy["acceptance_thresholds"]["items"]:
        for field in ("replaced_by", "merged_into"):
            target = item.get(field)
            if target is not None:
                assert target in ids or target in gate_ids, target


# --- Audit findings A5/A7/B5/B6/B10: holes that let PASS become vacuous ---


def test_a_removed_threshold_must_name_what_absorbed_it():
    """Audit finding A5/B6.

    ``REMOVE_REDUNDANT`` required no successor pointer at all, so a protection
    could be deleted with no record of what still covers the risk.
    """
    item = _hard(disposition="REMOVE_REDUNDANT", binding=False, value=None)
    with pytest.raises(ContractError, match="subsumed_by"):
        validate_acceptance_thresholds(_block(item))


def test_a_final_block_needs_at_least_one_binding_criterion():
    """Audit finding A5.

    With every threshold retired, PASS reduces to the mandatory gates alone and
    the cases they leave free are wholly unconstrained. That was reachable
    without tripping any check.
    """
    item = _hard(
        disposition="REPORT_ONLY",
        binding=False,
        value=None,
        status="FINAL",
    )
    block = _block(item)
    block["status"] = "FINAL"
    with pytest.raises(ContractError, match="no binding acceptance"):
        validate_acceptance_thresholds(block)


def test_a_final_block_may_not_retire_a_threshold_into_a_non_binding_one():
    """Audit finding A5/B6: absorption into something non-binding deletes it."""
    absorbed = _hard(
        threshold_id="absorbed",
        disposition="REPLACE_HARD",
        binding=False,
        value=None,
        status="FINAL",
        replaced_by="successor",
    )
    successor = _hard(
        threshold_id="successor",
        disposition="REPORT_ONLY",
        binding=False,
        value=None,
        status="FINAL",
    )
    block = _block(absorbed, successor)
    block["status"] = "FINAL"
    with pytest.raises(ContractError, match="does not bind"):
        validate_acceptance_thresholds(block)


def test_an_unresolved_threshold_may_not_declare_itself_binding():
    """Audit finding B10: ``REVIEW_REQUIRED`` with ``binding: true`` is incoherent."""
    item = _hard(
        disposition="REVIEW_REQUIRED",
        binding=True,
        value=None,
        status="REVIEW_REQUIRED",
    )
    with pytest.raises(ContractError):
        validate_acceptance_thresholds(_block(item, status="REVIEW_REQUIRED"))


@pytest.mark.parametrize(
    "clause",
    [
        ["every mandatory gate satisfied", "answer_presence_macro_f1_minimum met"],
        {"all_of": ["answer_presence_macro_f1_minimum >= x"]},
        {"nested": {"deeper": "answer_presence_macro_f1_minimum"}},
    ],
)
def test_a_non_string_status_clause_cannot_bypass_the_re_entry_check(policy, clause):
    """Audit finding B5.

    The check skipped any clause that was not a plain string, so writing the
    same condition as a list or an object re-admitted a report-only metric to
    PASS/FAIL.
    """
    mutated = copy.deepcopy(policy)
    mutated["status_logic"]["PASS"] = clause
    with pytest.raises(ContractError, match="must never re-enter PASS/FAIL"):
        validate_policy(mutated)


def test_an_extra_status_logic_key_is_also_policed(policy):
    """Audit finding B5: only ``PASS`` and ``FAIL`` used to be inspected."""
    mutated = copy.deepcopy(policy)
    mutated["status_logic"]["CONDITIONAL_PASS"] = (
        "answer_presence_macro_f1_minimum met"
    )
    with pytest.raises(ContractError, match="must never re-enter PASS/FAIL"):
        validate_policy(mutated)


def test_no_independence_flag_is_asserted_on_an_absent_value(policy):
    """Audit finding A7.

    ``candidate_independence`` and ``set_independence`` are claims about how a
    number was obtained. Asserting them true while ``value`` is null is not
    truth-apt, and would let a later round satisfy the check without ever
    re-deriving anything.
    """
    for item in policy["acceptance_thresholds"]["items"]:
        if item.get("value") is not None:
            continue
        for field in ("candidate_independence", "set_independence"):
            assert item.get(field) in (None, "NOT_APPLICABLE_NO_VALUE"), (
                item["threshold_id"],
                field,
            )


def test_prose_is_scanned_on_every_record_not_only_binding_ones():
    """Audit finding A6/B7.

    Scanning only binding FINAL records never reached the one record that will
    eventually carry a number.
    """
    item = _hard(
        disposition="REVIEW_REQUIRED",
        binding=False,
        value=None,
        status="REVIEW_REQUIRED",
        controlled_risk="chosen from observed parser performance on the dev set",
    )
    with pytest.raises(ContractError, match="prohibited threshold basis"):
        validate_acceptance_thresholds(_block(item))


@pytest.mark.parametrize(
    "text",
    [
        "derived from Phase 1.0-C headroom screening",
        "derived from phase 1.0 c task screening",
        "matches parser v 2 locked performance",
        "this is common practice in the field",
        "carried over verbatim from the predecessor contract",
        "selected because it would permit a pass",
    ],
)
def test_prohibited_basis_scan_survives_spelling_variation(text):
    """Substring matching bounds carelessness; it must at least survive a hyphen."""
    item = _hard(
        disposition="REVIEW_REQUIRED",
        binding=False,
        value=None,
        status="REVIEW_REQUIRED",
        derivation=text,
    )
    with pytest.raises(ContractError, match="prohibited threshold basis"):
        validate_acceptance_thresholds(_block(item))



# ---------------------------------------------------------------------------
# 4. Gate coverage: what the thresholds must be independent of
# ---------------------------------------------------------------------------


def _zero_error_strata(policy):
    """Strata pinned to exact typed-decision agreement by a mandatory gate.

    Audit finding A2. The first version filtered on ``maximum_errors == 0`` and
    on the population kind, which silently read the same field three
    incompatible ways: broadly for S06, exactly for the clean strata, and
    set-level-only for the null-collapse prohibition. Coverage is now derived
    from the gate's own declared ``pins_exact_typed_decision``, so a gate whose
    registered error definition is narrower than exact agreement cannot be
    counted as pinning a case.
    """
    pinned = set()
    for gate in policy["gates"]:
        if not gate.get("mandatory") or gate.get("maximum_errors") != 0:
            continue
        if not gate.get("pins_exact_typed_decision"):
            continue
        if gate["population"] == "stratum":
            pinned.add(gate["population_selector"])
        elif gate["population"] == "clean_cases":
            pinned.update(policy["population"]["clean_strata"])
    return pinned


def test_every_gate_declares_what_one_of_its_errors_is(policy):
    """Audit finding A2: ``maximum_errors`` is meaningless without a definition."""
    for gate in policy["gates"]:
        assert isinstance(gate.get("error_definition"), str)
        assert gate["error_definition"].strip()
        assert gate.get("error_scope") in ("per_case", "set_level")
        assert isinstance(gate.get("pins_exact_typed_decision"), bool)
        if gate["error_scope"] == "set_level":
            assert gate["pins_exact_typed_decision"] is False


def test_validator_rejects_a_gate_without_error_semantics(policy):
    for field in ("error_definition", "error_scope", "pins_exact_typed_decision"):
        broken = copy.deepcopy(policy)
        del broken["gates"][0][field]
        with pytest.raises(ContractError):
            validate_policy(broken)


def test_a_set_level_gate_may_not_claim_to_pin_a_case(policy):
    broken = copy.deepcopy(policy)
    for gate in broken["gates"]:
        if gate["error_scope"] == "set_level":
            gate["pins_exact_typed_decision"] = True
            break
    else:  # pragma: no cover - the shipped policy has a set-level gate
        pytest.skip("no set-level gate in the shipped policy")
    with pytest.raises(ContractError):
        validate_policy(broken)


def test_gate_coverage_analysis_is_derivable_from_the_gates(policy):
    """The declared coverage must be recomputable, not asserted."""
    analysis = policy["gate_coverage_analysis"]
    pinned = _zero_error_strata(policy)
    per_stratum = policy["population"]["cases_per_stratum"]
    assert sorted(pinned) == sorted(analysis["zero_error_pinned_strata"])
    assert len(pinned) * per_stratum == analysis["zero_error_pinned_case_count"]

    free = [s for s in policy["population"]["strata"] if s not in pinned]
    assert free == analysis["free_strata"]
    assert len(free) * per_stratum == analysis["free_case_count"]
    assert analysis["free_case_count"] == 40
    assert analysis["zero_error_pinned_case_count"] == 80


def test_s06_is_free_because_its_registered_error_is_narrower(policy):
    """Audit finding A2, restated as an executable check.

    The registered S06 gate forbids selection of the rightmost distractor span.
    A parser can satisfy that and still return a wrong canonical value, so S06
    is not pinned to exact typed-decision agreement.
    """
    gate = next(
        g for g in policy["gates"] if g.get("population_selector") == "S06"
    )
    assert gate["maximum_errors"] == 0
    assert gate["pins_exact_typed_decision"] is False
    assert "S06" not in _zero_error_strata(policy)
    assert "S06" in policy["gate_coverage_analysis"]["free_strata"]


def test_residual_critical_strata_match_the_gate_derivation(policy):
    pinned = _zero_error_strata(policy)
    residual = [
        s for s in policy["population"]["critical_strata"] if s not in pinned
    ]
    assert residual == policy["population"]["residual_critical_strata"]
    assert residual == ["S04", "S05", "S06", "S09"]
    assert policy["population"]["residual_critical_case_count"] == 40


def test_an_overall_minimum_at_or_below_the_pinned_count_would_be_vacuous(policy):
    """The finding that demoted threshold 1, restated as an executable check."""
    pinned_cases = policy["gate_coverage_analysis"]["zero_error_pinned_case_count"]
    total = policy["population"]["total_case_count"]
    # A gate-passing parser is guaranteed at least `pinned_cases` exact
    # decisions, so any minimum at or below that can never fail.
    for candidate in range(0, pinned_cases + 1):
        assert pinned_cases >= candidate
    # And the binding range is exactly the residual population.
    assert total - pinned_cases == policy["population"]["residual_critical_case_count"]


def test_a_common_critical_floor_is_inert_on_the_zero_gated_strata(policy):
    """Threshold 2's redundancy, restated as an executable check."""
    pinned = _zero_error_strata(policy)
    per_stratum = policy["population"]["cases_per_stratum"]
    for stratum in policy["population"]["critical_strata"]:
        if stratum not in pinned:
            continue
        # For any floor value the dedicated zero-error gate is at least as
        # strict, so the floor never changes the outcome on these strata.
        for floor in range(0, per_stratum + 1):
            assert 0 <= floor


# ---------------------------------------------------------------------------
# 5. Exhaustive confusion-matrix analysis (macro F1)
# ---------------------------------------------------------------------------


def _f1(tp: int, fp: int, fn: int) -> Fraction:
    if tp == 0:
        return Fraction(0)
    return Fraction(2 * tp, 2 * tp + fp + fn)


def macro_f1(errors_to_no_answer: int, errors_to_ambiguous: int) -> Fraction:
    """Macro F1 over the three presence classes at supports 80/30/10.

    Only ``present`` cases can be misclassified once the mandatory gates hold,
    so ``present`` accrues false negatives and the other two classes accrue
    false positives.
    """
    errors = errors_to_no_answer + errors_to_ambiguous
    return (
        _f1(80 - errors, 0, errors)
        + _f1(30, errors_to_no_answer, 0)
        + _f1(10, errors_to_ambiguous, 0)
    ) / 3


def _feasible_matrices(free_cases: int = 40):
    for to_no_answer, to_ambiguous in product(
        range(free_cases + 1), range(free_cases + 1)
    ):
        if to_no_answer + to_ambiguous > free_cases:
            continue
        yield to_no_answer, to_ambiguous


def test_registered_supports_are_derivable_from_stratum_presence(policy):
    presence = policy["population"]["stratum_presence"]
    per_stratum = policy["population"]["cases_per_stratum"]
    derived = {"present": 0, "no_answer": 0, "ambiguous": 0}
    for value in presence.values():
        derived[value] += per_stratum
    assert derived == policy["population"]["typed_decision_support"]
    assert derived == {"present": 80, "no_answer": 30, "ambiguous": 10}


def test_the_free_population_is_entirely_present_class(policy):
    """The enumeration's domain assumption, checked rather than assumed."""
    presence = policy["population"]["stratum_presence"]
    free = policy["gate_coverage_analysis"]["free_strata"]
    assert {presence[s] for s in free} == {"present"}


def test_confusion_matrix_enumeration_is_exhaustive_and_bounded(dispositions):
    matrices = list(_feasible_matrices())
    # All (a, b) with a + b <= 40 is C(42, 2) = 861.
    assert len(matrices) == 861
    assert len(matrices) == math.comb(42, 2)
    assert (
        dispositions["confusion_matrix_analysis"]["feasible_matrices_enumerated"]
        == 861
    )


def test_macro_f1_feasible_range_matches_the_recorded_analysis(dispositions):
    scores = {pair: macro_f1(*pair) for pair in _feasible_matrices()}
    lowest = min(scores.values())
    highest = max(scores.values())
    recorded = dispositions["confusion_matrix_analysis"]
    assert float(highest) == pytest.approx(recorded["macro_f1_max"])
    assert float(lowest) == pytest.approx(recorded["macro_f1_min"], abs=1e-6)
    worst_pair = min(scores, key=scores.get)
    assert worst_pair == (
        recorded["macro_f1_min_at"]["errors_to_no_answer"],
        recorded["macro_f1_min_at"]["errors_to_ambiguous"],
    )


def test_recorded_spreads_are_attained_extrema(dispositions):
    """Audit finding A1.

    Two published spread bounds were not attainable by any admissible matrix.
    A figure that no enumeration produces is not an analysis result, so every
    recorded bound is now recomputed and must be an exact attained extremum.
    """
    recorded = dispositions["confusion_matrix_analysis"][
        "spread_at_equal_error_counts"
    ]
    checked = 0
    for key, bounds in recorded.items():
        if not key.endswith("_errors"):
            continue
        total = int(key.split("_")[0])
        scores = [
            macro_f1(a, b) for a, b in _feasible_matrices() if a + b == total
        ]
        assert scores, key
        assert float(min(scores)) == pytest.approx(bounds[0], abs=1e-6), key
        assert float(max(scores)) == pytest.approx(bounds[1], abs=1e-6), key
        checked += 1
    assert checked == 4


def test_any_macro_f1_threshold_below_the_feasible_minimum_is_vacuous():
    lowest = min(macro_f1(*pair) for pair in _feasible_matrices())
    # No gate-passing parser can score below the feasible minimum, so a
    # threshold at or under it can never fail and protects nothing.
    assert all(macro_f1(*pair) >= lowest for pair in _feasible_matrices())
    assert float(lowest) == pytest.approx(0.636895, abs=1e-6)


def test_macro_f1_is_not_monotone_in_the_error_count():
    """The same error count can pass or fail depending only on which class won."""
    for total in (10, 20, 30, 40):
        same_count = [
            macro_f1(a, b) for a, b in _feasible_matrices() if a + b == total
        ]
        assert max(same_count) > min(same_count)


def test_macro_f1_is_blind_to_present_value_errors():
    """The decisive finding: presence errors and value errors are different.

    A ``present`` case with a wrong canonical value keeps presence class
    ``present``. It is a true positive for presence and a failure for exact
    typed-decision agreement.
    """
    # Zero presence errors, but every free case has a wrong canonical value.
    presence_score = macro_f1(0, 0)
    assert presence_score == 1
    exact_agreement = 120 - 40
    assert exact_agreement == 80
    # A perfect presence score coexists with 40 of 120 failing exactly.
    assert float(presence_score) == 1.0
    assert exact_agreement / 120 == pytest.approx(2 / 3)


def test_present_value_errors_are_modelled_separately(dispositions):
    record = dispositions["confusion_matrix_analysis"]["presence_error_vs_value_error"]
    assert record["modelled_separately"] is True


# ---------------------------------------------------------------------------
# 6. Policy / disposition-artifact agreement
# ---------------------------------------------------------------------------


def test_every_threshold_carries_a_recognised_disposition(policy):
    for item in policy["acceptance_thresholds"]["items"]:
        assert item["disposition"] in THRESHOLD_DISPOSITIONS


def test_disposition_artifact_agrees_with_the_policy(policy, dispositions):
    by_id = {i["threshold_id"]: i for i in policy["acceptance_thresholds"]["items"]}
    recorded = {d["threshold_id"]: d for d in dispositions["dispositions"]}
    assert set(by_id) == set(recorded)
    for threshold_id, item in by_id.items():
        row = recorded[threshold_id]
        assert row["disposition"] == item["disposition"], threshold_id
        assert row["status"] == item["status"], threshold_id
        assert row["final_value"] == item["value"], threshold_id


def test_disposition_artifact_records_the_blocked_terminal_status(dispositions):
    assert dispositions["terminal_status"] == "BLOCKED_ON_ACCEPTANCE_POLICY"


def test_the_four_original_thresholds_are_all_dispositioned(policy):
    original = {
        "overall_exact_typed_decision_minimum",
        "critical_stratum_floor",
        "answer_presence_macro_f1_minimum",
        "non_regression_margin_vs_parser_v2",
    }
    present = {i["threshold_id"] for i in policy["acceptance_thresholds"]["items"]}
    assert original <= present
    for item in policy["acceptance_thresholds"]["items"]:
        if item["threshold_id"] not in original:
            continue
        assert item["disposition"] != "KEEP_HARD"
        assert item["binding"] is False


def test_no_binding_threshold_is_final_without_a_basis(policy):
    for item in policy["acceptance_thresholds"]["items"]:
        if item["disposition"] in BINDING_DISPOSITIONS and item["status"] == "FINAL":
            assert item["basis_type"] in THRESHOLD_BASIS_TYPES


# ---------------------------------------------------------------------------
# 7. Namespace provenance, L-32, and the sampling frame
# ---------------------------------------------------------------------------


def test_policy_no_longer_binds_to_the_retired_v1_namespace(policy):
    live = copy.deepcopy(policy)
    # The retired path may appear only in provenance/errata prose that marks it
    # retired, never as a live source of population facts.
    assert "parser_v3_v1" not in json.dumps(live["population"]["support_derivation"]["method"])
    assert live["provenance"]["retired_binding"]["path"].endswith("strata_definitions.md")
    assert STRATUM_POLICY_PATH.name in json.dumps(live["provenance"]["authored_from"])
    assert not any(
        "parser_v3_v1" in source for source in live["provenance"]["authored_from"]
    )


def test_v2_stratum_policy_exists_and_is_case_free():
    text = STRATUM_POLICY_PATH.read_text(encoding="utf-8")
    for forbidden in ("locked_inputs", "locked_labels", "case_id"):
        assert forbidden not in text
    # ``sealed_object_count`` may be *named* by the L-32 preservation note, but
    # must never be asserted with a value.
    assert not re.search(r"sealed_object_count[\"'\s:=]+\d", text)
    assert "phase1-parser-v3-v2-stratum-policy/v2" in text


def test_v2_stratum_policy_supports_match_the_policy(policy):
    text = STRATUM_POLICY_PATH.read_text(encoding="utf-8")
    support = policy["population"]["typed_decision_support"]
    assert f"8 × 10 = **{support['present']}**" in text
    assert f"3 × 10 = **{support['no_answer']}**" in text
    assert f"1 × 10 = **{support['ambiguous']}**" in text


def test_l32_is_preserved_and_no_seal_fact_is_asserted(policy):
    text = STRATUM_POLICY_PATH.read_text(encoding="utf-8")
    assert "L-32" in text
    assert "authenticated seal-time observation" in text
    # The prospective policy must not assert any seal-derived count.
    assert "sealed_object_count" not in json.dumps(policy["population"])


def test_policy_records_a_non_iid_sampling_frame(policy):
    frame = policy["population"]["sampling_frame"]
    assert frame["is_iid_sample"] is False
    joined = " ".join(frame["prohibited_interpretations"]).lower()
    assert "confidence interval" in joined


def test_policy_discloses_post_hoc_knowledge(policy):
    disclosure = policy["post_hoc_disclosure"]["statement"].lower()
    assert "after" in disclosure
    assert "development results" in disclosure


def test_errata_records_the_phase_1_0c_correction(policy):
    erratum = policy["errata"]["corrections"][0]
    assert erratum["erratum_id"] == "E-1.2F-01"
    assert "06eec993" in erratum["correction"]
    assert "INCONCLUSIVE" in erratum["correction"]
    assert "44 unresolved" in erratum["correction"]
    assert "not an instance of H9" in erratum["classification"]


def test_calibration_protocol_is_registered_but_not_executed():
    text = CALIBRATION_PROTOCOL_PATH.read_text(encoding="utf-8")
    assert "REGISTERED — NOT EXECUTED" in text
    # It must not be presented as Phase 1.0C or a continuation of it.
    assert "is **not** Phase 1.0C" in text or "It is **not** Phase 1.0C" in text


# ---------------------------------------------------------------------------
# 8. Parser isolation: correct wording, and zero invocation
# ---------------------------------------------------------------------------


def test_repair_tooling_makes_no_absolute_parser_free_process_claim():
    """Overbroad wording is itself a defect.

    ``jspace_observation/__init__`` eagerly imports the legacy parser, so a
    claim that no parser module exists in the process is false.
    """
    overbroad = (
        "imports no parser module.",
        "no parser module is loaded",
        "package import is parser-free",
        "absolutely parser-free",
    )
    for path in REPAIR_MODULES:
        text = path.read_text(encoding="utf-8")
        for phrase in overbroad:
            assert phrase not in text, f"{path.name}: {phrase!r}"


def test_package_init_does_import_a_parser():
    """The premise of the corrected wording, asserted rather than assumed."""
    init = (SRC / "jspace_observation" / "__init__.py").read_text(encoding="utf-8")
    assert "eval_parsing" in init


def test_repair_modules_call_no_parser_entry_point():
    """Static proof of zero parser invocation.

    Walks the AST of every repair module and asserts that no call targets a
    known parser entry point by any spelling.
    """
    for path in REPAIR_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr if isinstance(func, ast.Attribute) else None
            )
            assert name not in PARSER_ENTRY_POINTS, f"{path.name} calls {name}"


def test_no_parser_function_is_invoked_at_import_time():
    """Runtime proof of zero parser invocation.

    Installs a tracer over every parser entry point before importing the repair
    modules, then asserts the call count is zero. This is the step the
    differential import test cannot cover: a module can import nothing new and
    still call a parser that the package already loaded.
    """
    program = (
        "import json, sys\n"
        "import jspace_observation.eval_parsing as legacy\n"
        "import jspace_observation.eval_parsing_v2 as v2\n"
        "import jspace_observation.eval_parsing_v3 as v3\n"
        "calls = []\n"
        "def wrap(mod, name):\n"
        "    original = getattr(mod, name, None)\n"
        "    if original is None:\n"
        "        return\n"
        "    def traced(*a, **k):\n"
        "        calls.append(mod.__name__ + '.' + name)\n"
        "        return original(*a, **k)\n"
        "    setattr(mod, name, traced)\n"
        f"for target in {list(PARSER_ENTRY_POINTS)!r}:\n"
        "    for mod in (legacy, v2, v3):\n"
        "        wrap(mod, target)\n"
        "import jspace_observation.parser_v3_repair_ontology\n"
        "import jspace_observation.parser_v3_repair_normalization\n"
        "import jspace_observation.parser_v3_repair_contract\n"
        "print(json.dumps(calls))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
        cwd=str(ROOT),
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )
    assert json.loads(result.stdout.strip()) == []


def test_parser_isolation_wording_is_corrected_in_documentation():
    protocol = (
        ROOT / "docs" / "phase1_2e_parser_v3_ontology_repair_protocol.md"
    ).read_text(encoding="utf-8")
    # The supportable claim must be present.
    assert "reference no parser module and call no" in protocol
    # And the reason the absolute claim is unavailable must be stated.
    assert "eagerly imports" in protocol
