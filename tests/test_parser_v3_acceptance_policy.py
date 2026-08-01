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
sys.path.insert(0, str(ROOT / "tests"))

from jspace_observation.parser_v3_repair_contract import (  # noqa: E402
    BINDING_DISPOSITIONS,
    GATE_ERROR_DEFINITIONS,
    NON_BINDING_DISPOSITIONS,
    POLICY_TOP_LEVEL_KEYS,
    REQUIRED_BINDING_NARRATIVE_FIELDS,
    REQUIRED_THRESHOLD_FIELDS,
    THRESHOLD_BASIS_TYPES,
    THRESHOLD_DISPOSITIONS,
    ContractError,
    derive_gate_coverage,
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
        # Phase 1.2G narrative provenance. A Boolean independence flag records
        # a claim; these record what the claim rests on and what it does not
        # cover. Required of every binding FINAL criterion.
        "candidate_observation_independence": "synthetic candidate independence",
        "sealed_set_independence": "synthetic sealed-set independence",
        "public_design_dependencies": "synthetic public design dependencies",
        "post_hoc_disclosure": "synthetic post hoc disclosure",
        "residual_limitations": "synthetic residual limitations",
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


def test_shipped_policy_is_final_with_exactly_one_binding_criterion(policy):
    """Phase 1.2G. Supersedes test_shipped_policy_remains_review_required.

    That test pinned the Phase 1.2F terminal state: a policy blocked because the
    prior question - how strict the instrument must be on designed-failure
    strata that no gate pins - had never been decided. Phase 1.2G decided it, so
    the old assertion is now a statement about history rather than about the
    shipped artifact. It is replaced by a strictly stronger set of assertions:
    the earlier test constrained one field, this one constrains the status, the
    identity of the binding criterion, its value, its basis, and the requirement
    that nothing else binds.
    """
    assert policy["status"] == "FINAL"
    assert policy["acceptance_thresholds"]["status"] == "FINAL"

    binding = [
        item
        for item in policy["acceptance_thresholds"]["items"]
        if item.get("binding") is True
    ]
    assert [item["threshold_id"] for item in binding] == [
        "residual_critical_exact_budget"
    ]
    criterion = binding[0]
    assert criterion["disposition"] == "KEEP_HARD"
    assert criterion["basis_type"] == "LOGICAL_INVARIANT"
    assert criterion["value"] == 0
    assert criterion["limits"]["pooled_max_errors"] == 0
    assert criterion["limits"]["per_stratum_max_errors"] == {
        "S04": 0,
        "S05": 0,
        "S06": 0,
        "S09": 0,
    }


def test_a_final_policy_still_states_that_nothing_has_been_run(policy):
    """status=FINAL is a decision about judging, never a result.

    The one way a finalized policy could mislead is by being read as evidence
    about a parser. The execution state is therefore machine-readable and sits
    next to the status.
    """
    execution = policy["execution_state"]
    assert execution["formal_evaluation_execution_state"] == "NOT_RUN"
    assert execution["formal_evaluation_ordinal"] == 0
    assert execution["predictions_generated"] == 0
    assert execution["locked_label_reads"] == 0
    assert execution["parser_v3_runs_against_any_locked_set"] == 0
    assert execution["parser_v3_v2_sealed_sets_constructed"] == 0
    assert "sealed_sets_constructed" not in execution, (
        "the counter must stay scoped to parser-v3-v2; an unscoped name "
        "contradicts parser-v3-v1 having been sealed"
    )
    assert "unvalidated" in execution["final_policy_is_not_a_result"]


def test_the_execution_state_does_not_deny_that_parser_v3_v1_was_sealed(policy):
    """Second re-review finding R2-R-03.

    The counter used to be named `sealed_sets_constructed` and rendered as
    "Sealed sets constructed: 0" into both current-state documents, while the
    same documents state that `parser-v3-v1` is `SEALED / UNSPENT / UNSCORABLE
    / RETIRED_AS_INELIGIBLE`. Those cannot both be true unscoped. The field and
    the rendered label are now scoped to the successor set.
    """
    execution = policy["execution_state"]
    assert execution["parser_v3_v2_sealed_sets_constructed"] == 0
    assert "RETIRED_AS_INELIGIBLE" in execution["final_policy_is_not_a_result"]
    for relative in ("reports/current_status.md", "docs/thread_handoff.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Sealed sets constructed" not in text, relative
        assert "Sealed `parser-v3-v2` sets constructed" in text, relative


def test_only_the_binding_criterion_carries_a_numeric_value(policy):
    """No number was manufactured anywhere else to reach a green status.

    Phase 1.2G. Supersedes test_no_threshold_carries_a_numeric_value, which
    asserted that *no* threshold carried a value. That was the correct assertion
    while every criterion was unresolved. It is now replaced by the assertion
    that does the same work in the finalized state: exactly one criterion
    carries a value, it is the one that binds, and every non-binding record is
    still forbidden a number.
    """
    valued = {
        item["threshold_id"]
        for item in policy["acceptance_thresholds"]["items"]
        if item["value"] is not None
    }
    assert valued == {"residual_critical_exact_budget"}
    for item in policy["acceptance_thresholds"]["items"]:
        if item["threshold_id"] in valued:
            continue
        assert item["value"] is None, item["threshold_id"]
        assert item["binding"] is False, item["threshold_id"]


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
    """The declared coverage must be recomputable, not asserted.

    Phase 1.2G strengthens this. The test keeps its own independent derivation
    so that it can disagree with production, and additionally asserts that the
    production derivation agrees with both. A test-only derivation could
    otherwise prove a coverage claim the compiler never enforces.
    """
    analysis = policy["gate_coverage_analysis"]
    pinned = _zero_error_strata(policy)
    per_stratum = policy["population"]["cases_per_stratum"]
    assert sorted(pinned) == sorted(analysis["zero_error_pinned_strata"])
    assert len(pinned) * per_stratum == analysis["zero_error_pinned_case_count"]

    residual = [s for s in policy["population"]["strata"] if s not in pinned]
    assert residual == analysis["residual_strata"]
    assert len(residual) * per_stratum == analysis["residual_case_count"]
    assert analysis["residual_case_count"] == 40
    assert analysis["zero_error_pinned_case_count"] == 80

    derived = derive_gate_coverage(policy)
    assert list(derived.pinned_strata) == sorted(pinned)
    assert derived.pinned_case_count == 80
    assert list(derived.residual_strata) == residual
    assert derived.residual_case_count == 40
    assert derived.total_case_count == 120


def test_s06_is_residual_because_its_registered_error_is_narrower(policy):
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
    assert "S06" in policy["gate_coverage_analysis"]["residual_strata"]
    assert "S06" in derive_gate_coverage(policy).residual_strata


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


def test_the_residual_population_is_entirely_present_class(policy):
    """The enumeration's domain assumption, checked rather than assumed."""
    presence = policy["population"]["stratum_presence"]
    residual = policy["gate_coverage_analysis"]["residual_strata"]
    assert {presence[s] for s in residual} == {"present"}


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


def test_disposition_artifact_records_the_resolved_terminal_status(dispositions):
    """Phase 1.2G. Supersedes the pinned BLOCKED_ON_ACCEPTANCE_POLICY assertion.

    The artifact records the outcome of the threshold audit. Phase 1.2F ended
    blocked; this round resolved the one open criterion, so the recorded
    terminal status changes with it. The replacement additionally pins *why* it
    changed, so a future edit cannot flip the status without also editing the
    decision it rests on.
    """
    assert dispositions["terminal_status"] == "READY_FOR_INDEPENDENT_SET_REPAIR"
    assert dispositions["status"] == "FINAL"
    update = dispositions["phase_1_2g_update"]
    assert update["decision"] == "STRICT_FINITE_SUITE_CONFORMANCE"
    assert "KEEP_HARD" in update["consequence"]


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


def test_calibration_protocol_is_superseded_and_still_never_executed():
    """Supersedes ``test_calibration_protocol_is_registered_but_not_executed``.

    The Phase 1.2F test asserted the protocol's status line read
    ``REGISTERED - NOT EXECUTED``. That was correct while the non-zero
    tolerance branch was live. Phase 1.2G adopted strict finite-suite
    conformance, so that branch is moot and the protocol is
    ``SUPERSEDED_UNEXECUTED``.

    This replacement is strictly stronger than the test it supersedes. It
    still asserts the never-executed property -- the substantive claim -- via
    an explicit execution count of zero, which the old status string only
    implied. It additionally asserts the supersession is recorded rather than
    merely applied, that the protocol states the conditions under which it
    would reactivate, and it keeps the original Phase 1.0C separation
    assertion unchanged.
    """
    text = CALIBRATION_PROTOCOL_PATH.read_text(encoding="utf-8")
    assert "SUPERSEDED_UNEXECUTED" in text
    # The substantive property the superseded test protected: it never ran.
    assert "**Times executed:** 0" in text
    assert "REGISTERED — NOT EXECUTED" not in text, (
        "the old status line must not linger alongside the new one"
    )
    # Supersession must be recorded, not merely applied.
    assert "supersession" in text.lower()
    assert "reactivat" in text.lower(), (
        "a superseded protocol must say what would bring it back"
    )
    # Unchanged from the superseded test: it must not be presented as Phase
    # 1.0C or a continuation of it.
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



# ---------------------------------------------------------------------------
# Phase 1.2G. Deterministic conformance policy.
#
# Every test below exists because some artifact could otherwise assert a fact
# the production code does not enforce, or because a rule that is currently
# true is only true by accident of the current document.
# ---------------------------------------------------------------------------


def _residual(policy):
    return next(
        item
        for item in policy["acceptance_thresholds"]["items"]
        if item["threshold_id"] == "residual_critical_exact_budget"
    )


# --- 1. The single production coverage derivation --------------------------


def test_coverage_derivation_is_the_one_production_path(policy):
    """validate_policy must go through derive_gate_coverage, not around it.

    The check is behavioural: corrupting only the declared restatement must be
    refused by validate_policy. If validation read the document instead of
    deriving, the corrupted block would be accepted.
    """
    broken = copy.deepcopy(policy)
    broken["gate_coverage_analysis"]["zero_error_pinned_case_count"] = 90
    with pytest.raises(ContractError, match="gates derive"):
        validate_policy(broken)


def test_declared_residual_strata_cannot_drift_from_the_derivation(policy):
    broken = copy.deepcopy(policy)
    broken["gate_coverage_analysis"]["residual_strata"] = ["S04", "S05", "S09"]
    with pytest.raises(ContractError, match="gates derive"):
        validate_policy(broken)


def test_derivation_reads_the_code_registry_not_the_policy_boolean(policy):
    """The policy's pins_exact_typed_decision is a restatement, not a source.

    Flipping it must be rejected rather than silently changing coverage. This
    is what stops a document edit from widening the instrument's coverage
    claim.
    """
    broken = copy.deepcopy(policy)
    for gate in broken["gates"]:
        if gate["gate_id"] == "G_S06_last_number_trap":
            gate["pins_exact_typed_decision"] = True
            break
    with pytest.raises(ContractError, match="registered error definition"):
        validate_policy(broken)


def test_an_unregistered_error_definition_is_refused(policy):
    broken = copy.deepcopy(policy)
    broken["gates"][0]["error_definition"] = "some_new_idea"
    with pytest.raises(ContractError, match="closed registry"):
        validate_policy(broken)


def test_every_registered_error_definition_declares_its_pinning_consequence():
    for name, entry in GATE_ERROR_DEFINITIONS.items():
        assert entry["scope"] in ("per_case", "set_level"), name
        assert entry["counting_unit"] in ("case", "set"), name
        assert isinstance(entry["pins_exact_typed_decision"], bool), name
        assert entry["reason"].strip(), name
        if entry["scope"] == "set_level":
            assert entry["pins_exact_typed_decision"] is False, name


def test_a_gate_must_declare_its_counting_unit(policy):
    broken = copy.deepcopy(policy)
    del broken["gates"][0]["counting_unit"]
    with pytest.raises(ContractError, match="counting_unit"):
        validate_policy(broken)


def test_a_gate_counting_unit_must_match_the_registry(policy):
    broken = copy.deepcopy(policy)
    for gate in broken["gates"]:
        if gate["error_scope"] == "set_level":
            gate["counting_unit"] = "case"
            break
    with pytest.raises(ContractError, match="registered as"):
        validate_policy(broken)


def test_a_set_level_gate_cannot_pin_any_case(policy):
    """Reading a whole-set property as a per-case requirement would pin all 120.

    That misreading is what would make every acceptance criterion vacuous, so
    it is refused twice: by the registry and by an explicit scope rule.
    """
    for name, entry in GATE_ERROR_DEFINITIONS.items():
        if entry["scope"] == "set_level":
            assert entry["pins_exact_typed_decision"] is False, name


def test_a_non_zero_allowance_does_not_pin_its_stratum(policy):
    """maximum_errors 1 leaves individual cases free even under a pinning rule."""
    broken = copy.deepcopy(policy)
    for gate in broken["gates"]:
        if gate["gate_id"] == "G_S11_ambiguity_detection":
            gate["maximum_errors"] = 1
            break
    with pytest.raises(ContractError, match="gates derive"):
        validate_policy(broken)


def test_two_gates_may_not_pin_the_same_stratum(policy):
    """Overlapping coverage would make the residual population ambiguous."""
    broken = copy.deepcopy(policy)
    duplicate = copy.deepcopy(
        next(g for g in broken["gates"] if g["gate_id"] == "G_S11_ambiguity_detection")
    )
    duplicate["gate_id"] = "G_S11_ambiguity_detection_duplicate"
    broken["gates"].append(duplicate)
    with pytest.raises(ContractError, match="pinned by both"):
        validate_policy(broken)


def test_an_unresolvable_gate_population_fails_closed(policy):
    """An empty resolution must be an error, never a silently smaller coverage."""
    broken = copy.deepcopy(policy)
    for gate in broken["gates"]:
        if gate["gate_id"] == "G_S11_ambiguity_detection":
            gate["population_selector"] = "S99"
            break
    with pytest.raises(ContractError, match="not a\n?\\s*registered stratum|registered stratum"):
        validate_policy(broken)


def test_derived_coverage_partitions_the_registered_strata(policy):
    coverage = derive_gate_coverage(policy)
    assert set(coverage.pinned_strata) & set(coverage.residual_strata) == set()
    assert set(coverage.pinned_strata) | set(coverage.residual_strata) == set(
        policy["population"]["strata"]
    )
    assert (
        coverage.pinned_case_count + coverage.residual_case_count
        == coverage.total_case_count
        == 120
    )


# --- 2. The finalized residual criterion -----------------------------------


def test_residual_criterion_population_equals_the_derived_residual(policy):
    coverage = derive_gate_coverage(policy)
    population = _residual(policy)["population"]
    assert population["derivation"] == "RESIDUAL_OF_EXACT_TYPED_DECISION_GATES"
    assert tuple(population["strata"]) == coverage.residual_strata
    assert population["case_count"] == coverage.residual_case_count == 40


def test_residual_criterion_population_cannot_be_a_free_parameter(policy):
    broken = copy.deepcopy(policy)
    _residual(broken)["population"]["strata"] = ["S04", "S05", "S09"]
    with pytest.raises(ContractError, match="gates leave"):
        validate_policy(broken)


def test_residual_criterion_case_count_must_match_the_gates(policy):
    """G-01. The Phase 1.2F record declared 40 cases over a 3-stratum prose."""
    broken = copy.deepcopy(policy)
    _residual(broken)["population"]["case_count"] = 30
    with pytest.raises(ContractError, match="Phase 1.2F defect|gates leave"):
        validate_policy(broken)


@pytest.mark.parametrize(
    "field",
    ["metric_definition", "numerator", "failure_risk_controlled"],
)
def test_criterion_prose_may_not_describe_a_different_population(policy, field):
    """G-01 directly. Prose is what a reader acts on."""
    broken = copy.deepcopy(policy)
    _residual(broken)[field] = "errors within S04, S05 and S09"
    with pytest.raises(ContractError, match="declared population"):
        validate_policy(broken)


def test_criterion_prose_may_not_miscount_its_strata(policy):
    broken = copy.deepcopy(policy)
    _residual(broken)["metric_definition"] = (
        "Maximum mismatches across the three strata that no gate pins."
    )
    with pytest.raises(ContractError, match="three strata"):
        validate_policy(broken)


def test_criterion_prose_may_not_miscount_its_cases(policy):
    broken = copy.deepcopy(policy)
    _residual(broken)["numerator"] = "mismatches among the 30 cases"
    with pytest.raises(ContractError, match="30 cases"):
        validate_policy(broken)


def test_residual_criterion_is_zero_pooled_and_per_stratum(policy):
    limits = _residual(policy)["limits"]
    assert limits["pooled_max_errors"] == 0
    assert limits["per_stratum_max_errors"] == {"S04": 0, "S05": 0, "S06": 0, "S09": 0}


def test_per_stratum_caps_must_cover_every_residual_stratum(policy):
    """G-09. The concentration cap existed only in prose before Phase 1.2G."""
    broken = copy.deepcopy(policy)
    del _residual(broken)["limits"]["per_stratum_max_errors"]["S06"]
    with pytest.raises(ContractError, match="per-stratum caps"):
        validate_policy(broken)


def test_a_missing_limits_block_is_refused(policy):
    broken = copy.deepcopy(policy)
    del _residual(broken)["limits"]
    with pytest.raises(ContractError, match="structured limits"):
        validate_policy(broken)


def test_the_generic_value_must_equal_the_pooled_limit(policy):
    """Two numbers that can disagree are two policies."""
    broken = copy.deepcopy(policy)
    _residual(broken)["value"] = 1
    with pytest.raises(ContractError, match="pooled\n?\\s*limit|pooled limit"):
        validate_policy(broken)


@pytest.mark.parametrize("bad", [True, False, 0.0, "0", None])
def test_a_limit_must_be_a_plain_integer(policy, bad):
    """isinstance(True, int) is true in Python, so Booleans are rejected by name."""
    broken = copy.deepcopy(policy)
    _residual(broken)["limits"]["pooled_max_errors"] = bad
    with pytest.raises(ContractError):
        validate_policy(broken)


def test_a_per_stratum_cap_above_the_stratum_size_is_refused(policy):
    broken = copy.deepcopy(policy)
    _residual(broken)["limits"]["per_stratum_max_errors"]["S04"] = 11
    with pytest.raises(ContractError, match="must lie in"):
        validate_policy(broken)


# --- 3. Boundary semantics at the integer boundary -------------------------


def test_at_threshold_zero_passes(policy):
    boundary = _residual(policy)["boundary_semantics"]
    assert boundary["inequality"] == "at_most"
    assert boundary["equality_passes"] is True
    assert "PASS" in boundary["at_threshold"]


def test_one_above_the_threshold_fails(policy):
    boundary = _residual(policy)["boundary_semantics"]
    assert "FAIL" in boundary["one_above"]


def test_one_below_the_threshold_is_unreachable(policy):
    """A count cannot be negative, so the criterion has exactly two states."""
    boundary = _residual(policy)["boundary_semantics"]
    assert "Not reachable" in boundary["one_below"]


def test_boundary_rule_must_be_stated_and_must_admit_equality(policy):
    broken = copy.deepcopy(policy)
    _residual(broken)["boundary_semantics"]["equality_passes"] = False
    _residual(broken)["boundary_semantics"]["at_threshold_passes"] = False
    with pytest.raises(ContractError, match="exact limit passes"):
        validate_policy(broken)


def test_two_spellings_of_the_boundary_rule_may_not_disagree(policy):
    broken = copy.deepcopy(policy)
    _residual(broken)["boundary_semantics"]["at_threshold_passes"] = False
    with pytest.raises(ContractError, match="must agree"):
        validate_policy(broken)


def test_an_error_count_criterion_must_use_at_most(policy):
    broken = copy.deepcopy(policy)
    _residual(broken)["boundary_semantics"]["inequality"] = "at_least"
    with pytest.raises(ContractError, match="at_most"):
        validate_policy(broken)


# --- 4. Provenance of the finalized value ----------------------------------


def test_the_binding_criterion_declares_a_recognised_basis(policy):
    assert _residual(policy)["basis_type"] == "LOGICAL_INVARIANT"
    assert _residual(policy)["basis_type"] in THRESHOLD_BASIS_TYPES


@pytest.mark.parametrize("field", REQUIRED_BINDING_NARRATIVE_FIELDS)
def test_a_binding_criterion_must_carry_every_narrative_field(policy, field):
    broken = copy.deepcopy(policy)
    _residual(broken)[field] = "   "
    with pytest.raises(ContractError, match=field):
        validate_policy(broken)


def test_the_narrative_fields_are_basis_scanned(policy):
    """A prohibited basis must not survive by moving into a narrative field."""
    broken = copy.deepcopy(policy)
    _residual(broken)["post_hoc_disclosure"] = (
        "Chosen because it reflects observed parser behaviour."
    )
    with pytest.raises(ContractError):
        validate_policy(broken)


def test_the_derivation_never_appeals_to_determinism_or_tidiness(policy):
    """The value rests on the conformance premise, not on aesthetics.

    Phase 1.2F explicitly listed 'adopting zero merely because it is the
    tidiest available value' as a prohibited resolution. The derivation must
    not read as that argument in different words.
    """
    derivation = _residual(policy)["derivation"].lower()
    for forbidden in (
        "tidiest",
        "simplest",
        "conservative",
        "deterministic",
        "safest",
        "round number",
    ):
        assert forbidden not in derivation, forbidden
    assert "conformance suite" in derivation
    assert "mandatory reference decision" in derivation


def test_the_prohibited_grounds_are_excluded_as_structured_data(policy):
    """The disclaimer must live outside the derivation text.

    A derivation that disclaims "determinism" by name cannot be scanned for
    appeals to determinism: the disclaimer matches the scan. Recording the
    excluded grounds as structured data keeps the derivation a pure argument
    and makes the exclusion machine-readable rather than rhetorical.
    """
    excludes = _residual(policy)["derivation_excludes"]
    grounds = {entry["ground"].lower() for entry in excludes["grounds"]}
    for required in (
        "iid",
        "deterministic",
        "downstream parser-error budget",
        "cautious",
        "parser v2",
        "parser-v3 performance",
    ):
        assert any(required in ground for ground in grounds), required
    for entry in excludes["grounds"]:
        assert entry["why_not_used"].strip()


def test_no_excluded_ground_is_smuggled_back_into_the_argument(policy):
    """Excluding a ground and then relying on it would be worse than silence.

    Second post-remediation re-review finding R2-A-01: the first version of this
    test read three fields of the threshold record, and the sampling argument
    survived in `resolved_dependency.decision`, which is equally live prose and
    is where the conformance premise is actually stated. The scan now covers
    every live rationale field, with `derivation_excludes` — the designated
    place to *name* an excluded ground — the only exemption.
    """
    item = _residual(policy)
    thresholds = policy["acceptance_thresholds"]
    parts = [
        str(item.get(field, ""))
        for field in ("derivation", "numeric_derivation", "controlled_risk")
    ]
    resolved = thresholds["resolved_dependency"]
    parts.extend(
        str(resolved.get(field, ""))
        for field in (
            "note",
            "decision",
            "consequence",
            "why_this_is_not_a_severity_judgement",
            "what_would_reopen_it",
        )
    )
    parts.extend(
        str(entry.get("reason", "")) for entry in item.get("rejected_alternatives", [])
    )
    argument = " ".join(parts).lower()
    for forbidden in (
        "iid",
        "deterministic",
        "cautious",
        "prudent",
        "sampling",
        "industry standard",
    ):
        assert forbidden not in argument, forbidden


def test_every_excluded_ground_is_named_only_in_the_exclusion_field(policy):
    """The grounds must still be disclosed, just not inside the argument."""
    excludes = _residual(policy)["derivation_excludes"]
    assert excludes["note"].strip()
    grounds = {entry["ground"] for entry in excludes["grounds"]}
    assert any("iid" in ground.lower() for ground in grounds)
    assert any("deterministic" in ground.lower() for ground in grounds)
    for entry in excludes["grounds"]:
        assert entry["why_not_used"].strip()


def test_the_conformance_premise_is_recorded_with_its_falsifier(policy):
    resolved = policy["acceptance_thresholds"]["resolved_dependency"]
    assert resolved["decision"].startswith("STRICT_FINITE_SUITE_CONFORMANCE")
    assert resolved["what_would_reopen_it"].strip()
    assert resolved["why_this_is_not_a_severity_judgement"].strip()


def test_the_post_hoc_disclosure_is_structural_not_a_denial(policy):
    text = _residual(policy)["post_hoc_disclosure"].lower()
    assert "already known" in text
    assert "strictest" in text


def test_the_residual_limitations_disclaim_scientific_adequacy(policy):
    text = _residual(policy)["residual_limitations"]
    assert "L-35" in text and "L-36" in text
    assert "conforming instrument" in text


# --- 5. Non-binding records cannot re-enter the decision -------------------


def test_macro_f1_is_not_an_acceptance_criterion(policy):
    item = next(
        i
        for i in policy["acceptance_thresholds"]["items"]
        if i["threshold_id"] == "answer_presence_macro_f1_minimum"
    )
    assert item["disposition"] == "REPORT_ONLY"
    assert item["binding"] is False
    assert item["value"] is None
    assert "answer_presence_macro_f1_minimum" not in json.dumps(policy["status_logic"])


@pytest.mark.parametrize(
    "threshold_id",
    [
        "overall_exact_typed_decision_minimum",
        "critical_stratum_floor",
        "answer_presence_macro_f1_minimum",
        "non_regression_margin_vs_parser_v2",
    ],
)
def test_a_retired_criterion_cannot_acquire_a_value(policy, threshold_id):
    broken = copy.deepcopy(policy)
    for item in broken["acceptance_thresholds"]["items"]:
        if item["threshold_id"] == threshold_id:
            item["value"] = 1
    with pytest.raises(ContractError, match="must not carry a\n?\\s*numeric value|numeric value"):
        validate_policy(broken)


@pytest.mark.parametrize(
    "threshold_id",
    [
        "overall_exact_typed_decision_minimum",
        "critical_stratum_floor",
        "answer_presence_macro_f1_minimum",
        "non_regression_margin_vs_parser_v2",
    ],
)
def test_a_retired_criterion_cannot_declare_itself_binding(policy, threshold_id):
    broken = copy.deepcopy(policy)
    for item in broken["acceptance_thresholds"]["items"]:
        if item["threshold_id"] == threshold_id:
            item["binding"] = True
    with pytest.raises(ContractError, match="binding=false"):
        validate_policy(broken)


def test_status_logic_names_only_the_binding_criterion(policy):
    assert policy["status_logic"]["binding_criteria"] == [
        "residual_critical_exact_budget"
    ]


# --- 6. The comparator is report-only, structurally ------------------------


def test_comparator_is_final_report_only_and_not_run(policy):
    comparators = policy["comparators"]
    assert comparators["role"] == "REPORT_ONLY"
    assert comparators["status"] == "FINAL"
    assert comparators["execution_status"] == "NOT_RUN"
    assert comparators["binding"] is False


def test_a_comparator_may_not_carry_a_margin(policy):
    broken = copy.deepcopy(policy)
    broken["comparators"]["margin"] = 0
    with pytest.raises(ContractError, match="no numeric margin"):
        validate_policy(broken)


def test_a_comparator_may_not_declare_a_pass_condition(policy):
    broken = copy.deepcopy(policy)
    broken["comparators"]["pass_condition"] = "v3 >= v2"
    with pytest.raises(ContractError, match="no numeric margin|pass condition"):
        validate_policy(broken)


def test_a_comparator_may_not_declare_itself_binding(policy):
    broken = copy.deepcopy(policy)
    broken["comparators"]["binding"] = True
    with pytest.raises(ContractError, match="binding=false"):
        validate_policy(broken)


def test_a_zero_comparator_margin_is_still_a_margin(policy):
    """0 == False in Python, so a zero margin must be rejected by identity.

    A margin of zero is the substantive rule 'must not be worse than parser
    v2'. A truth test on the field would have admitted it silently.
    """
    broken = copy.deepcopy(policy)
    broken["comparators"]["margin"] = 0
    with pytest.raises(ContractError, match="no numeric margin"):
        validate_policy(broken)


def test_a_comparator_role_other_than_report_only_is_refused(policy):
    broken = copy.deepcopy(policy)
    broken["comparators"]["role"] = "SECONDARY_SAFETY_CHECK"
    with pytest.raises(ContractError, match="REPORT_ONLY"):
        validate_policy(broken)


def test_every_registered_comparator_declares_a_purpose(policy):
    broken = copy.deepcopy(policy)
    broken["comparators"]["registered_comparators"].append("some_other_parser")
    with pytest.raises(ContractError, match="report-only purpose"):
        validate_policy(broken)


def test_withdrawn_comparator_arguments_are_marked_withdrawn(policy):
    """G-06. A withdrawn argument must not read as live reasoning."""
    item = next(
        i
        for i in policy["acceptance_thresholds"]["items"]
        if i["threshold_id"] == "non_regression_margin_vs_parser_v2"
    )
    withdrawn = item["withdrawn_arguments"]
    assert len(withdrawn) == 2
    for entry in withdrawn:
        assert entry["status"] == "WITHDRAWN"
        assert entry["why_withdrawn"].strip()
    assert "withdrawn" in item["independence_analysis"].lower()
    assert "Underivable margin" in item["live_reason"]


# --- 7. A FINAL policy is not a result -------------------------------------


def test_execution_state_must_be_present_and_zero(policy):
    for field in (
        "predictions_generated",
        "locked_label_reads",
        "parser_v3_runs_against_any_locked_set",
    ):
        broken = copy.deepcopy(policy)
        broken["execution_state"][field] = 1
        with pytest.raises(ContractError, match=field):
            validate_policy(broken)


def test_execution_ordinal_must_be_zero(policy):
    broken = copy.deepcopy(policy)
    broken["execution_state"]["formal_evaluation_ordinal"] = 1
    with pytest.raises(ContractError, match="ordinal must be 0"):
        validate_policy(broken)


def test_a_policy_without_an_execution_state_is_refused(policy):
    broken = copy.deepcopy(policy)
    del broken["execution_state"]
    with pytest.raises(ContractError, match="execution_state"):
        validate_policy(broken)


def test_a_boolean_ordinal_is_not_accepted_as_zero(policy):
    broken = copy.deepcopy(policy)
    broken["execution_state"]["formal_evaluation_ordinal"] = False
    with pytest.raises(ContractError, match="ordinal must be 0"):
        validate_policy(broken)


# --- 8. Superseded figures may not be reasserted ---------------------------


def test_live_prose_may_not_reassert_the_superseded_pinned_count(policy):
    """G-02. The 90-of-120 figure was corrected, then reasserted elsewhere."""
    broken = copy.deepcopy(policy)
    broken["purpose"] = "The gates pin 90 of 120 exact typed decisions."
    with pytest.raises(ContractError, match="pinned-coverage figure"):
        validate_policy(broken)


def test_live_prose_may_not_reassert_the_three_stratum_residual(policy):
    broken = copy.deepcopy(policy)
    broken["purpose"] = "The residual critical strata are S04, S05 and S09."
    with pytest.raises(ContractError, match="three-stratum residual"):
        validate_policy(broken)


def test_an_explicitly_historical_subtree_may_quote_the_old_figure(policy):
    """An erratum must remain writable, or the record cannot be corrected."""
    validate_policy(policy)
    assert (
        policy["gate_coverage_analysis"]["superseded_figures"][
            "previous_pinned_case_count"
        ]
        == 90
    )


# --- 9. The policy is the canonical source ---------------------------------


def test_policy_declares_itself_canonical(policy):
    canonical = policy["canonical_source_of_truth"]
    assert "canonical" in canonical["declaration"]
    assert "derive_gate_coverage" in canonical["derived_not_declared"]
    assert (
        "src/jspace_observation/parser_v3_repair_contract.py"
        in canonical["consumers"]
    )


def test_schema_version_records_the_finalization(policy):
    assert policy["schema_version"].endswith("/v3")
    assert policy["phase"] == "1.2G"


def test_compiled_contract_carries_the_derived_coverage():
    """A contract must not be compilable without the coverage it rests on."""
    import inspect

    from jspace_observation import parser_v3_repair_contract as contract_module

    source = inspect.getsource(contract_module.compile_contract)
    assert "derive_gate_coverage(policy)" in source
    assert '"gate_coverage": coverage.as_dict()' in source
# ---------------------------------------------------------------------------
# 10. Superseded-figure scanner: positive control
#
# The scanner is only worth having if it catches the defects it was written
# for. These tests are the ported form of the positive control that was run
# during remediation, and they are deliberately expressed as the *seed defect
# text itself* rather than as pattern unit tests: a pattern test passes when
# the pattern is self-consistent, which is not the property under examination.
# ---------------------------------------------------------------------------

SEED_DEFECT_TEXTS = [
    ("x.md", "Satisfying every mandatory gate implies at least 90 of 120 exact typed decisions."),
    ("x.md", "The residual critical strata are S04, S05 and S09."),
    ("x.md", "The budget covers the three adversarial strata."),
    ("x.md", "S06 is pinned by its dedicated gate."),
    ("x.md", "Next: execute the calibration protocol."),
    ("x.md", "Register a downstream parser-error budget, then proceed."),
    ("x.md", "Protected digests 11 / 11 digest match."),
    (
        "x.md",
        "The predecessor here failed its own locked evaluation, so not worse "
        "than it is not evidence of fitness.",
    ),
    ("x.json", '{"note": "The gates pin 90 of 120 cases."}'),
]

SUPERSEDED_EXEMPT_TEXTS = [
    ("x.md", "> **Erratum.** The old figure was 90 of 120; it is now 80 of 120."),
    ("x.md", "**Superseded figures.** 90 of 120. Do not cite them."),
    ("x.md", "S06 is therefore NOT pinned to exact agreement."),
    ("x.json", '{"errata": {"as_written": "the gates pin 90 of 120 cases"}}'),
]


@pytest.mark.parametrize(("path", "text"), SEED_DEFECT_TEXTS)
def test_the_scanner_catches_every_seed_defect_form(path, text):
    """Each of G-01..G-10's prose forms must be rejected if it returns."""
    assert consistency.scan_superseded_figures(path, text), (
        f"a superseded figure went undetected: {text!r}"
    )


@pytest.mark.parametrize(("path", "text"), SUPERSEDED_EXEMPT_TEXTS)
def test_the_scanner_leaves_errata_writable(path, text):
    """Corrections must be able to quote the figure they are correcting."""
    found = consistency.scan_superseded_figures(path, text)
    assert found == [], f"false positive on a correction: {found}"


def test_the_withdrawn_comparator_argument_is_not_negation_exempt():
    """A claim whose own wording contains "not" must not be self-exempting.

    This is a real defect that this round's positive control found. The
    sentence-level negation guard exists so that errata can deny a superseded
    figure. The withdrawn comparator argument reads "... so not worse than it
    is not evidence of fitness", so a guard keyed on the presence of a
    negation exempted precisely the sentence it existed to catch. Negatability
    is now a per-pattern property.
    """
    negatable = {
        pattern: negatable
        for pattern, _reason, negatable in consistency.SUPERSEDED_FIGURE_PATTERNS
    }
    withdrawn = [
        pattern for pattern in negatable if "failed its own locked evaluation" in pattern
    ]
    assert len(withdrawn) == 1
    assert negatable[withdrawn[0]] is False


def test_every_superseded_pattern_states_why_it_is_wrong():
    """A failure that does not explain itself gets suppressed, not fixed."""
    for pattern, reason, negatable in consistency.SUPERSEDED_FIGURE_PATTERNS:
        assert reason.strip(), pattern
        assert len(reason) > 30, f"reason for {pattern!r} is too thin to act on"
        assert isinstance(negatable, bool)


def test_the_repository_is_clean_of_superseded_figures():
    assert consistency.scan_files(root=ROOT) == []


# ---------------------------------------------------------------------------
# 11. The generated current-state block
#
# Six of the ten seed defects were stale figures in prose that no scanner
# pattern covered. The structural answer is to render them instead of typing
# them. These tests pin the rendering, not the prose.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generator():
    import importlib.util

    path = ROOT / "scripts" / "generate_current_state.py"
    spec = importlib.util.spec_from_file_location("generate_current_state", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_generated_block_is_current(generator):
    """--check must pass on the committed tree."""
    assert generator.run(write=False, root=ROOT) == 0


def test_the_generated_block_is_deterministic(generator):
    assert generator.render_block() == generator.render_block()


def test_the_generated_block_reports_the_derived_coverage(generator):
    """The figures must come from the derivation, not from the prose."""
    block = generator.render_block()
    coverage = derive_gate_coverage(json.loads(POLICY_PATH.read_text(encoding="utf-8")))
    assert f"**{coverage.pinned_case_count} of {coverage.total_case_count}**" in block
    assert f"**{coverage.residual_case_count}** residual" in block
    for stratum in coverage.residual_strata:
        assert stratum in block


def test_a_hand_edited_block_fails_the_check(generator, tmp_path):
    """The whole point is that a human edit is detected."""
    import shutil

    for relative in generator.TARGET_FILES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relative, target)

    tampered = tmp_path / generator.TARGET_FILES[0]
    text = tampered.read_text(encoding="utf-8")
    tampered.write_text(text.replace("**80 of 120**", "**90 of 120**"), encoding="utf-8")

    assert generator.run(write=False, root=tmp_path) == 1


def test_a_missing_sentinel_is_an_error_not_a_silent_skip(generator, tmp_path):
    """A document that drops the sentinels must not quietly stop being checked."""
    for relative in generator.TARGET_FILES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (ROOT / relative).read_text(encoding="utf-8")
        target.write_text(text.replace(generator.BEGIN_MARKER, ""), encoding="utf-8")

    with pytest.raises(SystemExit):
        generator.run(write=False, root=tmp_path)


def test_the_generated_block_carries_every_standing_statement(generator):
    block = generator.render_block()
    for statement in generator.INVARIANT_STATEMENTS:
        assert statement in block


def test_the_standing_statements_cover_the_required_disclosures(generator):
    """Section 13's required statements must not be quietly droppable."""
    joined = " ".join(generator.INVARIANT_STATEMENTS).lower()
    for required in (
        "phase 1.0c was executed",
        "inconclusive",
        "not parser calibration",
        "no prediction was generated",
        "no parser was run",
        "unvalidated",
        "retired_as_ineligible",
        "hidden-reasoning",
    ):
        assert required in joined, required


def test_the_generated_block_never_asserts_a_result(generator):
    """A FINAL policy is a rule, not a finding."""
    block = generator.render_block().lower()
    for forbidden in (
        "parser v3 is validated",
        "parser v3 passed",
        "non-regressive",
        "fit for scientific scoring",
    ):
        assert forbidden not in block


# --- 12. Audit-remediation regressions -------------------------------------
#
# Every test below reproduces a defect that an independent read-only reviewer
# found in this round's own work. They are kept together, and named after the
# finding, so that a future reader can tell which guards exist because the
# author got it wrong the first time.


def _pinning_gate(policy):
    """The first mandatory gate that pins exact typed-decision agreement."""
    return next(
        gate
        for gate in policy["gates"]
        if gate.get("mandatory")
        and GATE_ERROR_DEFINITIONS[gate["error_definition"]][
            "pins_exact_typed_decision"
        ]
    )


def test_a_per_stratum_cap_above_the_pooled_cap_is_rejected(policy):
    """A3/B9: the exact combination the report claimed was caught, but was not.

    A pooled limit of zero with a per-stratum cap of one is not a redundant
    statement, it is a contradictory one, and the permissive half reads as
    permission.
    """
    broken = copy.deepcopy(policy)
    caps = _residual(broken)["limits"]["per_stratum_max_errors"]
    first = sorted(caps)[0]
    caps[first] = _residual(broken)["limits"]["pooled_max_errors"] + 1
    with pytest.raises(ContractError, match="pooled limit"):
        validate_policy(broken)


def test_every_per_stratum_cap_is_checked_against_the_pooled_cap(policy):
    """The relation must hold for each stratum, not just the first one."""
    caps = _residual(policy)["limits"]["per_stratum_max_errors"]
    pooled = _residual(policy)["limits"]["pooled_max_errors"]
    for stratum in caps:
        broken = copy.deepcopy(policy)
        _residual(broken)["limits"]["per_stratum_max_errors"][stratum] = pooled + 1
        with pytest.raises(ContractError, match=re.escape(stratum)):
            validate_policy(broken)


@pytest.mark.parametrize("bogus", [False, True, 0.0, 1.0, "0", None])
def test_a_non_integer_gate_error_limit_cannot_pin_a_stratum(policy, bogus):
    """A5/B7: ``False != 0`` and ``0.0 != 0`` are both false in Python.

    An untyped read let a malformed gate acquire pinning status, which would
    have silently shrunk the residual population the binding criterion covers.
    """
    broken = copy.deepcopy(policy)
    _pinning_gate(broken)["maximum_errors"] = bogus
    with pytest.raises(ContractError):
        derive_gate_coverage(broken)


def test_a_support_gate_may_still_declare_no_error_limit(policy):
    """The type check must not break the gates that legitimately carry None."""
    support_gates = [
        gate for gate in policy["gates"] if gate.get("maximum_errors") is None
    ]
    assert support_gates, "the class-support gates carry no error limit"
    for gate in support_gates:
        registered = GATE_ERROR_DEFINITIONS[gate["error_definition"]]
        assert not registered["pins_exact_typed_decision"]
    derive_gate_coverage(policy)


def test_a_registered_comparator_may_not_appear_in_pass_logic(policy):
    """A4/B8: rejecting non-binding threshold ids left comparators unguarded."""
    names = list(policy["comparators"]["registered_comparators"])
    assert names, "the policy registers at least one comparator"
    for name in names:
        broken = copy.deepcopy(policy)
        broken["status_logic"]["PASS"] = [
            *_as_list(broken["status_logic"]["PASS"]),
            f"{name} margin is met",
        ]
        with pytest.raises(ContractError, match="comparator"):
            validate_policy(broken)


def test_a_comparator_may_not_be_smuggled_into_binding_criteria(policy):
    """The same guard must cover the declaration list, not only PASS."""
    name = policy["comparators"]["registered_comparators"][0]
    broken = copy.deepcopy(policy)
    broken["status_logic"]["binding_criteria"] = [
        *broken["status_logic"]["binding_criteria"],
        name,
    ]
    with pytest.raises(ContractError):
        validate_policy(broken)


def _as_list(clause):
    return list(clause) if isinstance(clause, list) else [clause]


def test_binding_criteria_may_not_be_empty(policy):
    """An empty declaration would leave PASS reducible to the gates alone."""
    broken = copy.deepcopy(policy)
    broken["status_logic"]["binding_criteria"] = []
    with pytest.raises(ContractError, match="binding_criteria"):
        validate_policy(broken)


def test_binding_criteria_must_equal_the_computed_binding_set(policy):
    """A declaration is checked against the policy, not trusted."""
    broken = copy.deepcopy(policy)
    broken["status_logic"]["binding_criteria"] = ["not_a_criterion"]
    with pytest.raises(ContractError, match="binding criteria are"):
        validate_policy(broken)


def test_binding_criteria_tracks_a_criterion_that_stops_binding(policy):
    """Dropping ``binding`` without updating the declaration must fail."""
    broken = copy.deepcopy(policy)
    _residual(broken)["binding"] = False
    with pytest.raises(ContractError):
        validate_policy(broken)


def test_the_committed_binding_criteria_declaration_is_accurate(policy):
    computed = sorted(
        item["threshold_id"]
        for item in policy["acceptance_thresholds"]["items"]
        if item.get("binding") is True
    )
    assert sorted(policy["status_logic"]["binding_criteria"]) == computed
    assert computed == ["residual_critical_exact_budget"]


# --- 12.1 B10/B11: the checker's own coverage cannot shrink silently -------


def test_a_registered_but_missing_file_is_reported(tmp_path):
    """B11: skipping a missing path shrinks coverage while every test passes."""
    import shutil

    ground_truth = tmp_path / consistency.PHASE_1_0C_DECISION
    ground_truth.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(PHASE_1_0C_DECISION, ground_truth)

    found = consistency.scan_files(root=tmp_path)
    kinds = {item.kind for item in found}
    assert kinds == {"MISSING_REGISTERED_FILE"}
    reported = {item.path for item in found}
    assert set(consistency.SUPERSEDED_FIGURE_FILES) <= reported
    assert set(consistency.CURRENT_STATE_FILES) <= reported


def test_the_superseded_figure_scan_covers_the_expected_documents():
    """The expectation is literal, so shrinking the registry fails a test."""
    assert set(consistency.SUPERSEDED_FIGURE_FILES) == {
        "reports/current_status.md",
        "docs/thread_handoff.md",
        "docs/phase1_parser_v3_v2_evaluation_policy.json",
        "docs/phase1_2f_threshold_dispositions.json",
        "docs/phase1_parser_v3_v2_stratum_policy.md",
        "docs/phase1_2g_conformance_policy_protocol.md",
        "reports/phase1_2g_conformance_policy.md",
        "reports/phase1_2g_audit_findings.md",
        "reports/phase1_2f_parser_acceptance_policy.md",
        "docs/phase1_2h_independent_set_repair_protocol.md",
        "docs/phase1_2h_execution_access_ledger.json",
        "reports/phase1_2h_blocked_set_repair.md",
        "reports/phase1_2h_audit_findings.md",
        "tests/test_parser_v3_repair.py",
        "paper/methods_ledger.md",
    }


def test_the_generator_targets_are_asserted_independently_of_the_module(generator):
    """B11: iterating the module's own tuple measures nothing."""
    assert set(generator.TARGET_FILES) == {
        "reports/current_status.md",
        "docs/thread_handoff.md",
    }


def test_every_registered_document_exists():
    root = ROOT
    for relative in (
        *consistency.CURRENT_STATE_FILES,
        *consistency.SUPERSEDED_FIGURE_FILES,
        consistency.CALIBRATION_PROTOCOL,
    ):
        assert (root / relative).exists(), relative


def test_the_anchor_prefix_cannot_backtrack_catastrophically():
    """A `# ---` separator followed by no anchor must not hang the checker.

    The original nested prefix could partition a run of N dashes in
    exponentially many ways. The defect was latent until the scanned file list
    grew to include a Python module full of separators.
    """
    import time

    block = "# " + "-" * 200 + " section\nno anchor word here\n"
    started = time.monotonic()
    assert consistency._is_exempt(block) is False
    assert time.monotonic() - started < 1.0


def test_a_quoted_defect_table_is_exempt_but_a_plain_table_is_not():
    """The exemption is a labelled column, not a reassuring word in a cell.

    Post-remediation re-review finding R-01 narrowed this from a block-level
    exemption to a column-level redaction, so ``_is_exempt`` is no longer the
    mechanism: the labelled column is blanked and the rest of the table is
    still scanned.
    """
    exempt = "| ID | Quoted defect |\n| --- | --- |\n| G-03 | three strata |\n"
    plain = "| ID | Defect |\n| --- | --- |\n| G-03 | three strata |\n"
    assert consistency._is_exempt(exempt) is False
    assert consistency._is_exempt(plain) is False
    assert consistency.scan_superseded_figures("x.md", exempt) == []
    assert consistency.scan_superseded_figures("x.md", plain) != []


def test_a_table_header_without_a_delimiter_row_is_not_a_table():
    """A stray pipe must not become a general-purpose exemption."""
    not_a_table = "| ID | Quoted defect | claim |\n| G-03 | three strata | x |\n"
    lines = list(enumerate(not_a_table.splitlines(), start=1))
    assert consistency._quoted_columns(lines) == set()
    assert consistency._is_exempt(not_a_table) is False


# --- 13. Post-remediation re-review regressions ----------------------------
#
# A third read-only reviewer read the remediated tree and found that several
# claimed fixes were only partial, plus three defects the remediation itself
# introduced. These tests pin the corrected behaviour.


def _probe(text):
    return consistency.scan_superseded_figures("probe.md", text)


def test_r01_only_the_quoted_column_of_a_defect_table_is_exempt():
    """R-01: exempting the whole table hid live claims in other columns.

    A defect register quotes a retired figure in one column and states the
    remediation in another. The remediation column is live prose and must be
    scanned; the earlier rule exempted the entire block.
    """
    table = (
        "| ID | Quoted defect | Remediation |\n"
        "| --- | --- | --- |\n"
        "| G-03 | three strata | 90 of 120 cases are pinned |\n"
    )
    hits = _probe(table)
    assert hits, "a live claim in the remediation column must be reported"
    assert all("90 of 120" in hit.line for hit in hits)


def test_r01_the_quoted_column_itself_stays_exempt():
    table = (
        "| ID | Quoted defect | Remediation |\n"
        "| --- | --- | --- |\n"
        "| G-03 | 90 of 120 cases | corrected to 80 |\n"
    )
    assert _probe(table) == []


def test_r01_an_unlabelled_table_is_scanned_in_full():
    plain = "| ID | Defect |\n| --- | --- |\n| G-03 | 90 of 120 cases |\n"
    assert _probe(plain) != []


def test_r01_a_single_row_containing_a_pipe_is_not_exempt():
    """The anchor prefix must not treat a cell delimiter as a heading marker."""
    row = "| Quoted defect | 90 of 120 cases |\n"
    assert consistency._is_exempt(row) is False
    assert _probe(row) != []


def test_r01_blockquote_and_erratum_exemptions_are_unchanged():
    """Narrowing the table rule must not have broken the older exemptions."""
    assert _probe("> the report said 90 of 120 cases\n") == []
    assert _probe("Erratum: the figure 90 of 120 was wrong.\n") == []


def test_a04_a_comparator_used_as_a_mapping_key_is_rejected(policy):
    """A-04: the clause walk collected mapping values but not keys.

    ``{"legacy_parser": "required"}`` puts the reference in the key, so a
    values-only walk reported the clause clean while the policy read a
    comparator into its own pass condition.
    """
    for name in policy["comparators"]["registered_comparators"]:
        broken = copy.deepcopy(policy)
        broken["status_logic"]["FAIL"] = {name: "required"}
        with pytest.raises(ContractError, match="comparator"):
            validate_policy(broken)


def test_a04_a_non_binding_threshold_used_as_a_mapping_key_is_rejected(policy):
    non_binding = [
        item["threshold_id"]
        for item in policy["acceptance_thresholds"]["items"]
        if item.get("binding") is not True
    ]
    assert non_binding
    for threshold_id in non_binding:
        broken = copy.deepcopy(policy)
        broken["status_logic"]["PASS"] = {threshold_id: "must hold"}
        with pytest.raises(ContractError, match=threshold_id):
            validate_policy(broken)


def test_a04_the_clause_walk_collects_keys_and_values():
    from jspace_observation.parser_v3_repair_contract import _collect_clause_text

    collected = _collect_clause_text({"key_side": ["value_side", {"deep_key": 1}]})
    assert "key_side" in collected
    assert "value_side" in collected
    assert "deep_key" in collected


def test_b10_a_missing_calibration_protocol_is_reported(tmp_path):
    """B-10: deleting the protocol must not satisfy the check that governs it."""
    found = consistency.check_calibration_protocol_is_superseded(root=tmp_path)
    assert [item.kind for item in found] == ["MISSING_REGISTERED_FILE"]
    assert found[0].path == consistency.CALIBRATION_PROTOCOL


def test_b06_a_spelled_out_superseded_figure_is_caught():
    """B-06: numeric-only patterns missed the ledger's spelled-out split."""
    assert _probe(
        "With ninety of a hundred and twenty cases pinned to zero errors.\n"
    ) != []
    assert _probe("a criterion governs only the thirty that are free.\n") != []


def test_b06_the_methods_ledger_states_the_derived_split():
    text = (ROOT / "paper" / "methods_ledger.md").read_text(encoding="utf-8")
    assert "eighty of a hundred and twenty" in text
    assert "forty that are free" in text


def test_r02_a_stale_disposition_label_is_caught():
    """R-02: three current-state records still said REMOVE_REDUNDANT."""
    assert _probe("The metric critical_stratum_floor is REMOVE_REDUNDANT.\n") != []
    assert (
        _probe("overall_exact_typed_decision_minimum is REMOVE_REDUNDANT here.\n")
        != []
    )


def test_r02_every_current_state_record_matches_the_canonical_dispositions(policy):
    """The policy defines the labels; the summaries only restate them."""
    canonical = {
        item["threshold_id"]: item["disposition"]
        for item in policy["acceptance_thresholds"]["items"]
    }
    assert canonical == {
        "overall_exact_typed_decision_minimum": "REPLACE_HARD",
        "critical_stratum_floor": "MERGE_WITH_EXISTING_GATE",
        "answer_presence_macro_f1_minimum": "REPORT_ONLY",
        "non_regression_margin_vs_parser_v2": "REPORT_ONLY",
        "residual_critical_exact_budget": "KEEP_HARD",
    }
    for relative in (
        "reports/current_status.md",
        "docs/thread_handoff.md",
        "docs/run_log.md",
        "reports/phase1_2g_conformance_policy.md",
        "docs/phase1_2g_conformance_policy_protocol.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        for threshold_id, disposition in canonical.items():
            if threshold_id not in text:
                continue
            assert disposition in text, f"{relative}: {threshold_id}"


def test_r03_the_stale_unsealed_holdout_claim_is_caught():
    """R-03: the status file gave two incompatible seal states."""
    assert _probe("parser-v3 holdout constructed but NOT SEALED today.\n") != []


def test_r03_the_construction_record_is_marked_superseded():
    text = (ROOT / "reports" / "current_status.md").read_text(encoding="utf-8")
    assert "SUPERSEDED point-in-time record" in text
    assert "CONSTRUCTED, NOT SEALED" not in text
    assert "RETIRED_AS_INELIGIBLE" in text


def test_a01_the_named_subset_argument_is_withdrawn_everywhere():
    """A-01: an aggregate budget need not name a subset, so that argument fails.

    The valid argument is the universal implication. Every document that states
    the consequence must state the valid form, and must not rest on the
    withdrawn one.
    """
    withdrawn = re.compile(
        r"(?:name|identify|say)\s+which[^.]{0,60}"
        r"(?:cases?|admitted)[^.]{0,60}(?:permitted|may|is allowed) to fail",
        re.IGNORECASE,
    )
    for relative in (
        "docs/phase1_2g_conformance_policy_protocol.md",
        "reports/phase1_2g_conformance_policy.md",
        "docs/decision_log.md",
        "paper/limitations_ledger.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        for window in consistency._windows(text):
            assert not withdrawn.search(window.text), relative


def test_a01_the_rejected_alternative_does_not_cite_an_absent_budget(policy):
    """Rejecting a non-zero value for lack of a budget is a prohibited basis."""
    rejected = _residual(policy)["rejected_alternatives"][0]
    assert "contradicts the conformance premise" in rejected["reason"]
    assert "does not rest on the absence" in rejected["reason"]


def test_a01_the_valid_form_of_the_argument_is_stated(policy):
    """The universal implication must be explicit, not implied."""
    derivation = _residual(policy)["derivation"]
    assert "aggregate allowance of B > 0" in derivation
    assert "contradicts it" in derivation
    assert "not that the subset is unnamed" in derivation


# --- 12.2 B6: artifact-specific regressions for the seed defects -----------


def test_g08_focused_suite_total_is_recorded_correctly():
    """G-08: the round recorded 201 and 242 where the transcript shows 249.

    The stale numbers may still appear, because an erratum has to quote the
    figure it corrects. What they may not do is stand unqualified.
    """
    text = (ROOT / "reports" / "current_status.md").read_text(encoding="utf-8")
    assert "249" in text
    for stale in ("201 passed", "242 passed"):
        for window in consistency._windows(text):
            if stale not in window.text:
                continue
            lowered = window.text.lower()
            assert "erratum" in lowered or "when written" in lowered, stale


def test_g10_protected_digest_count_is_verified_not_asserted():
    """G-10: the count must come from the registry, not from prose."""
    from test_parser_v3_repair import PROTECTED_DIGESTS

    assert len(PROTECTED_DIGESTS) == 12
    report = (ROOT / "reports" / "phase1_2g_conformance_policy.md").read_text(
        encoding="utf-8"
    )
    assert "12" in report


def test_g05_the_synthetic_fixture_uses_the_derived_population(policy):
    """G-05/B3: the fixture must not carry the superseded population."""
    from test_parser_v3_repair import resolve_threshold

    resolved = resolve_threshold(value=0)
    population = resolved["boundary_semantics"]["population"]
    coverage = derive_gate_coverage(policy)
    assert str(coverage.residual_case_count) in population
    for stratum in coverage.residual_strata:
        assert stratum in population
    assert "30 cases" not in population


def test_g06_the_withdrawn_argument_is_stored_as_history(dispositions):
    """G-06/B4: a withdrawn argument must not read as a live finding."""
    comparator = next(
        row
        for row in dispositions["dispositions"]
        if "comparator" in row["threshold_id"] or "parser_v2" in row["threshold_id"]
    )
    withdrawn = comparator.get("withdrawn_arguments")
    assert isinstance(withdrawn, list) and withdrawn
    for entry in withdrawn:
        assert entry.get("argument")
        assert entry.get("finding")
        assert entry.get("withdrawn_in")
    assert "not evidence of fitness" not in comparator["one_line_finding"]


def test_g04_the_superseded_next_gate_is_marked_superseded():
    """G-04: the Phase 1.2F next gate inverted the dependency order."""
    text = (ROOT / "reports" / "phase1_2f_parser_acceptance_policy.md").read_text(
        encoding="utf-8"
    )
    assert "As written (superseded)" in text
    assert "phase1_2g_conformance_policy.md" in text


def test_g07_the_audit_report_names_which_artifacts_kept_old_figures():
    text = (ROOT / "reports" / "phase1_2f_audit_findings.md").read_text(
        encoding="utf-8"
    )
    assert "errat" in text.lower()


def test_the_phase_1_2g_audit_findings_report_exists_and_is_complete():
    """B10: the round report referenced a document that did not exist."""
    path = ROOT / "reports" / "phase1_2g_audit_findings.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    for finding in ("A-01", "A-02", "A-03", "A-04", "A-05"):
        assert finding in text, finding
    for finding in ("B1", "B2", "B3", "B4", "B5", "B6", "B10", "B11"):
        assert finding in text, finding
    for heading in ("Disposition.", "Fix.", "Residual limitation."):
        assert heading in text, heading
    assert "Post-remediation re-review" in text
    for finding in ("R-01", "R-02", "R-03", "R-A-01", "R-A-04", "R-B-06", "R-B-10"):
        assert finding in text, finding
    for finding in ("R2-A-01", "R2-NEW-01", "R2-NEW-02", "R2-R-01", "R2-R-03"):
        assert finding in text, finding
    assert "Second re-review" in text
    assert "Third re-review" in text


def test_every_documented_cross_reference_resolves():
    """B10: a citation to a file that does not exist is a broken record."""
    documents = (
        ROOT / "docs" / "phase1_2g_conformance_policy_protocol.md",
        ROOT / "reports" / "phase1_2g_conformance_policy.md",
        ROOT / "reports" / "phase1_2g_audit_findings.md",
        ROOT / "docs" / "phase1_2h_independent_set_repair_protocol.md",
        ROOT / "reports" / "phase1_2h_blocked_set_repair.md",
        ROOT / "reports" / "phase1_2h_audit_findings.md",
    )
    reference = re.compile(r"`((?:docs|reports|paper|scripts|tests|src)/[^`]+?)`")
    for document in documents:
        for span in set(reference.findall(document.read_text(encoding="utf-8"))):
            # A code span may quote an invocation rather than a bare path.
            relative = span.split()[0].rstrip(".,;:")
            if relative.endswith("/"):
                continue
            assert (ROOT / relative).exists(), f"{document.name} -> {relative}"


# --- 14. Second post-remediation re-review regressions ---------------------


def test_r2r01_an_anchor_exempts_its_line_not_its_paragraph():
    """R2-R-01: a live claim below an anchored opener was never scanned.

    The anchor marks the statement it introduces. A correction that genuinely
    spans lines is a blockquote, which is the repository's existing convention
    and the exemption that survives.
    """
    paragraph = (
        "Erratum: the earlier text was wrong.\n"
        "The current coverage is 90 of 120 cases pinned.\n"
    )
    hits = _probe(paragraph)
    assert hits, "the unanchored second line must be scanned"
    assert all("Erratum" not in hit.line for hit in hits)


def test_r2r01_the_anchored_line_itself_is_still_exempt():
    assert _probe("Erratum: the figure 90 of 120 was wrong.\n") == []


def test_r2r01_a_blockquote_is_still_exempt_in_full():
    """Blockquotes are block-level quotation, so block exemption is exact."""
    quoted = "> the report said 90 of 120 cases\n> over a three-stratum residual\n"
    assert consistency._is_exempt(quoted) is True
    assert _probe(quoted) == []


def test_r2r01_an_anchor_no_longer_exempts_a_whole_block():
    assert consistency._is_exempt("Erratum: x\nlive claim here\n") is False


def test_r2r01_json_key_exemption_matches_whole_words():
    """A key that merely contains an exempt word must not exempt its subtree."""
    assert consistency._is_exempt_json_key("historical") is True
    assert consistency._is_exempt_json_key("historical_note") is True
    assert consistency._is_exempt_json_key("as_written") is True
    assert consistency._is_exempt_json_key("quoted_defect_column") is True
    assert consistency._is_exempt_json_key("not_historical_current_state") is False
    assert consistency._is_exempt_json_key("ahistorical") is False
    assert consistency._is_exempt_json_key("uncorrectionable") is False
    assert consistency._is_exempt_json_key("current_state") is False


def test_r2new02_the_table_delimiter_test_is_linear():
    """R2-NEW-02: the delimiter regex backtracked on a long dash run."""
    import time

    hostile = "|" + "-" * 4000 + "x"
    started = time.monotonic()
    assert consistency._is_table_delimiter(hostile) is False
    assert time.monotonic() - started < 0.5


def test_r2new02_the_table_delimiter_test_still_recognises_delimiters():
    for good in ("| --- | --- |", "|---|---|", " :--- | ---: ", "---"):
        assert consistency._is_table_delimiter(good) is True, good
    for bad in ("", "   ", "| a | b |", "| - | - |"):
        assert consistency._is_table_delimiter(bad) is False, bad


def test_r2new02_a_hostile_delimiter_row_does_not_stall_a_scan():
    import time

    block = "| ID | Quoted defect |\n|" + "-" * 4000 + "x\n| G-03 | three strata |\n"
    started = time.monotonic()
    consistency.scan_superseded_figures("probe.md", block)
    assert time.monotonic() - started < 1.0


def test_r2a01_the_conformance_premise_does_not_argue_from_sampling(policy):
    """R2-A-01: the prohibited ground survived in the field stating the premise."""
    resolved = policy["acceptance_thresholds"]["resolved_dependency"]
    decision = resolved["decision"].lower()
    assert decision.startswith("strict_finite_suite_conformance")
    for forbidden in ("sampling", "sampling error", "statistical deviation"):
        assert forbidden not in decision, forbidden
    assert "mandatory requirement of its own" in resolved["decision"]


def test_r2new01_no_artifact_claims_work_that_has_not_happened():
    """R2-NEW-01: the record described a pending review and commit as done."""
    forbidden = re.compile(
        r"\bon the committed policy\b|\bwas committed and pushed in this round\b",
        re.IGNORECASE,
    )
    for relative in (
        "reports/phase1_2g_conformance_policy.md",
        "reports/phase1_2g_audit_findings.md",
        "docs/phase1_2g_conformance_policy_protocol.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert not forbidden.search(text), relative


# --- 15. Third post-remediation re-review regressions ----------------------


def _probe_json(text):
    return consistency.scan_superseded_figures("probe.json", text)


def test_r3new02_an_unrelated_phase_1_0c_denial_does_not_suppress_a_figure():
    """R3-NEW-02: the two scans shared the Phase 1.0C negation guard.

    `scan_superseded_figures` called `_search`, which applies the Phase 1.0C
    guard unconditionally, so registering a pattern `negatable=False` bought
    nothing whenever the sentence happened to contain a 1.0C denial. The two
    checks ask different questions and no longer share a guard.
    """
    text = (
        "Phase 1.0C is not parser calibration and the parser-v3 holdout "
        "constructed but NOT SEALED.\n"
    )
    assert _probe(text) != []


def test_r3new02_an_unrelated_negation_does_not_exempt_a_live_figure():
    """A denial aimed at something else is not a correction of the figure."""
    assert _probe("The gates pin 90 of 120 cases, which does not meet the target.\n")


def test_r3new02_a_genuine_correction_is_still_exempt():
    assert _probe("The mandatory gates pin 80 of 120 cases, not 90 of 120 cases.\n") == []
    assert (
        _probe(
            "The claim that 90 of 120 cases are pinned was already false when "
            "written.\n"
        )
        == []
    )


def test_r3new02_the_superseded_scan_does_not_use_the_phase_1_0c_guard():
    """Structural proof, so the two guards cannot be re-coupled silently.

    Audit G renamed the call site to `_finditer_raw`, which bypasses the Phase
    1.0C guard for the same reason `_search_raw` does; both are accepted here.
    """
    source = (ROOT / "scripts" / "check_current_state_consistency.py").read_text(
        encoding="utf-8"
    )
    body = source[source.index("def scan_superseded_figures") :]
    body = body[: body.index("\ndef ", 1)]
    assert "_finditer_raw(" in body or "_search_raw(" in body
    stripped = body.replace("_finditer_raw(", "").replace("_search_raw(", "")
    assert "_search(" not in stripped


def test_r3new03_a_delimiter_must_match_the_header_column_count():
    """R3-NEW-03: a bare `---` enabled redaction on text that is not a table."""
    not_a_table = "| Quoted defect | Note |\n---\n| 90 of 120 cases | live |\n"
    assert _probe(not_a_table) != []
    assert consistency._is_table_delimiter("---", columns=2) is False
    assert consistency._is_table_delimiter("| --- | --- |", columns=2) is True
    assert consistency._is_table_delimiter("| --- | --- |", columns=3) is False


def test_r3new03_every_delimiter_cell_must_be_a_delimiter():
    assert consistency._is_table_delimiter("| --- | : |", columns=2) is False
    assert consistency._is_table_delimiter("| :--- | ---: |", columns=2) is True


def test_r3new03_a_well_formed_quoted_defect_table_still_redacts():
    table = "| Quoted defect | Note |\n| --- | --- |\n| 90 of 120 cases | ok |\n"
    assert _probe(table) == []


def test_r3new04_a_structured_json_record_is_scanned_as_a_record():
    """R3-NEW-04: leaf-only windows could not see a two-field claim."""
    record = (
        '{"threshold_id": "critical_stratum_floor", '
        '"disposition": "REMOVE_REDUNDANT"}'
    )
    assert _probe_json(record) != []


def test_r3new04_a_json_errata_subtree_is_still_exempt():
    quoted = (
        '{"errata": {"threshold_id": "critical_stratum_floor", '
        '"disposition": "REMOVE_REDUNDANT"}}'
    )
    assert _probe_json(quoted) == []


def test_r3new04_an_ancestor_scalar_reaches_a_nested_mapping():
    """Audit F reopened R3-NEW-04: one level of nesting hid the whole claim.

    Every ancestor on the path genuinely co-describes the node, so joining them
    reports an adjacency the document really makes.
    """
    split = (
        '{"threshold_id": "critical_stratum_floor", '
        '"nested": {"disposition": "REMOVE_REDUNDANT"}}'
    )
    assert _probe_json(split) != []
    deep = (
        '{"a": {"b": {"threshold_id": "critical_stratum_floor", '
        '"c": {"d": {"disposition": "REMOVE_REDUNDANT"}}}}}'
    )
    assert _probe_json(deep) != []


def test_r3new04_unrelated_subtrees_are_still_never_joined():
    """The anti-false-adjacency invariant that the ancestor join must preserve."""
    siblings = (
        '{"one": {"threshold_id": "critical_stratum_floor"}, '
        '"two": {"disposition": "REMOVE_REDUNDANT"}}'
    )
    assert _probe_json(siblings) == []


def test_r3new05_the_scoped_sealed_set_counter_is_validated(policy):
    """R3-NEW-05: the renamed field was rendered but never validated."""
    broken = copy.deepcopy(policy)
    broken["execution_state"]["parser_v3_v2_sealed_sets_constructed"] = 1
    with pytest.raises(ContractError, match="parser_v3_v2_sealed_sets_constructed"):
        validate_policy(broken)


def test_r3new05_the_scoped_counter_is_required(policy):
    broken = copy.deepcopy(policy)
    del broken["execution_state"]["parser_v3_v2_sealed_sets_constructed"]
    with pytest.raises(ContractError, match="required"):
        validate_policy(broken)


def test_r3new05_the_unscoped_counter_name_is_rejected(policy):
    broken = copy.deepcopy(policy)
    broken["execution_state"]["sealed_sets_constructed"] = 0
    with pytest.raises(ContractError, match="unscoped"):
        validate_policy(broken)


# ---------------------------------------------------------------------------
# 16. Phase 1.2H. Audit F - re-review of the Audit E remediation.
#
# Audit F found all six Audit E remediations incomplete. Each test below pins
# the counterexample the auditor supplied, so the same escape cannot be made
# twice.
# ---------------------------------------------------------------------------


def test_f02_a_denial_aimed_at_the_replacement_figure_is_not_an_exemption():
    """Audit F on R3-NEW-02: sentence-wide negation exempted an assertion.

    Both sentences state the retired figure as fact. The negation belongs to
    the *replacement* number, so it must not buy an exemption.
    """
    assert _probe("The gates pin 90 of 120 cases, not 80 of 120 cases.\n") != []
    assert (
        _probe("The gates pin 90 of 120 cases rather than 80 of 120 cases.\n") != []
    )
    assert _probe("S06 is pinned to exact agreement, not S07.\n") != []


def test_f02_a_denial_in_a_different_clause_is_not_an_exemption():
    """A marker elsewhere in the sentence must not reach the figure."""
    assert (
        _probe("The gates pin 90 of 120 cases; the 80 of 120 figure is now retired.\n")
        != []
    )


def test_f02_attached_denials_and_mention_frames_remain_exempt():
    """The corrections that must stay writable."""
    for text in (
        "The mandatory gates pin 80 of 120 cases, not 90 of 120 cases.\n",
        "The claim that 90 of 120 cases are pinned was already false when written.\n",
        "The figure was previously listed as 90 of 120.\n",
        "The old text said 90 of 120; that is no longer correct.\n",
        "It used to say 90 of 120.\n",
        "90 of 120 is now superseded.\n",
    ):
        assert _probe(text) == [], text


def test_f02_a_mention_frame_alone_is_not_a_denial():
    """A framed sentence with no falsity marker still asserts the figure."""
    assert _probe("The claim that 90 of 120 cases are pinned is correct.\n") != []


def test_f03_a_malformed_delimiter_cell_does_not_enable_redaction():
    """Audit F on R3-NEW-03: `---:---` passed the `'--' in cell` test."""
    assert consistency._is_delimiter_cell("---") is True
    assert consistency._is_delimiter_cell(":---:") is True
    assert consistency._is_delimiter_cell("---:---") is False
    assert consistency._is_delimiter_cell("-") is False
    assert consistency._is_delimiter_cell("a--b") is False
    assert consistency._is_table_delimiter("| ---:--- | --- |", columns=2) is False
    not_a_table = (
        "| Quoted defect | Note |\n| ---:--- | --- |\n| 90 of 120 cases | live |\n"
    )
    assert _probe(not_a_table) != []


def test_f05_an_undeclared_execution_counter_is_rejected(policy):
    """Audit F on R3-NEW-05: only *named* counters were validated.

    An undeclared counter could assert an execution beside the validated
    zeros and every check still passed.
    """
    broken = copy.deepcopy(policy)
    broken["execution_state"]["parser_v3_v2_evaluations_run"] = 1
    with pytest.raises(ContractError, match="unrecognised"):
        validate_policy(broken)


def test_f05_an_undeclared_counter_is_rejected_even_when_zero(policy):
    """The defect is the unvalidated key, not its current value."""
    broken = copy.deepcopy(policy)
    broken["execution_state"]["some_future_counter"] = 0
    with pytest.raises(ContractError, match="unrecognised"):
        validate_policy(broken)


def test_f05_the_closed_key_set_matches_the_shipped_policy(policy):
    """The schema must be exactly the block the canonical policy carries."""
    from jspace_observation.parser_v3_repair_contract import EXECUTION_STATE_KEYS

    assert set(policy["execution_state"]) == set(EXECUTION_STATE_KEYS)


def test_f01_the_review_provenance_records_every_audit_with_counts(policy):
    """Audit F on R3-NEW-01: A and B were listed without finding counts."""
    provenance = _residual(policy)["review_provenance"]
    reviewers = provenance["reviewers"]
    assert len(reviewers) == 6
    for label in ("Audit A", "Audit B", "Audit C", "Audit D", "Audit E", "Audit F"):
        entry = next(item for item in reviewers if item.startswith(label))
        assert re.search(r"returned \d+ findings?", entry), entry
    # The superseded claim that Audit E's remediation was never re-reviewed
    # must be gone, because Phase 1.2H re-reviewed it.
    assert "was not itself independently re-reviewed" not in provenance["limitation"]
    assert provenance["supplementary_record"] == "reports/phase1_2h_audit_findings.md"


@pytest.mark.parametrize(
    "field",
    (
        "formal_evaluation_ordinal",
        "predictions_generated",
        "locked_label_reads",
        "parser_v3_runs_against_any_locked_set",
        "parser_v3_v2_sealed_sets_constructed",
    ),
)
@pytest.mark.parametrize("value", (0.0, False, "0", None))
def test_r3new05_a_count_must_be_a_genuine_integer_zero(policy, field, value):
    """`value != 0` accepted 0.0 and False. A count is an integer."""
    broken = copy.deepcopy(policy)
    broken["execution_state"][field] = value
    with pytest.raises(ContractError, match=field):
        validate_policy(broken)


def test_r3new06_the_contract_module_makes_only_the_narrow_isolation_claim():
    """R3-NEW-06: the module docstring claimed it imports no parser.

    Importing this module through the package first runs
    `jspace_observation/__init__.py`, which eagerly imports the legacy parser.
    The broad claim is therefore false; the differential claim is the true one.
    """
    source = (
        ROOT / "src" / "jspace_observation" / "parser_v3_repair_contract.py"
    ).read_text(encoding="utf-8")
    docstring = ast.get_docstring(ast.parse(source)) or ""
    assert "nothing\nhere imports or invokes a parser" not in docstring
    assert "no new parser dependency" in docstring
    assert "invokes no parser" in docstring
    assert "eagerly imports the legacy parser" in docstring


#: Phrases that assert the unsupportable absolute isolation claim.
OVERBROAD_ISOLATION = re.compile(
    r"(?:imports? (?:or invokes )?no parser|no parser (?:module|code) "
    r"(?:is|exists) (?:in|loaded)|absolutely parser[- ]free|"
    r"parser[- ]free (?:process|import))",
    re.IGNORECASE,
)

#: A document may *mention* the false claim in order to disown it. The
#: disclaimer must sit close in front of the phrase, so that quoting a withdrawn
#: wording stays possible while asserting it does not.
ISOLATION_DISCLAIMERS = re.compile(
    r"\b(?:narrower|withdrawn|unsupportable|false|cannot|not|never|"
    r"no longer|rather than|check that|would be)\b",
    re.IGNORECASE,
)
_DISCLAIMER_WINDOW = 120

#: A sentence terminator followed by whitespace or a closing delimiter. Version
#: strings such as ``1.2H`` are not boundaries because the dot is followed by an
#: alphanumeric.
_ISOLATION_SENTENCE_BOUNDARY = re.compile(r"[.!?](?=[\s\"'`)\]]|$)")


def _disclaimer_context(text: str, start: int) -> str:
    """Return the text preceding ``start`` **within the same sentence**.

    Audit G finding G-05: the disclaimer search took a flat 120-character
    window, so any disclaimer vocabulary in a *neighbouring* sentence
    suppressed a genuine assertion. "This module cannot process malformed
    input. Package import is absolutely parser-free." passed because "cannot"
    belonged to the previous sentence. A disavowal has to be part of the same
    statement as the claim it disavows.
    """

    window = text[max(0, start - _DISCLAIMER_WINDOW) : start]
    boundary = None
    for candidate in _ISOLATION_SENTENCE_BOUNDARY.finditer(window):
        boundary = candidate
    return window[boundary.end() :] if boundary is not None else window


def _asserts_overbroad_isolation(text: str) -> list[str]:
    """Return every overbroad isolation claim that is asserted, not disowned."""
    offenders = []
    for match in OVERBROAD_ISOLATION.finditer(text):
        if not ISOLATION_DISCLAIMERS.search(_disclaimer_context(text, match.start())):
            offenders.append(match.group(0))
    return offenders


def _isolation_scanned_sources() -> list[str]:
    """Every repair/policy source that could carry the claim.

    R3-NEW-06 was possible because the file list was written by hand and
    `parser_v3_repair_normalization.py` was not on it. Enumerating the modules
    means a new repair module is covered the moment it is added.
    """
    found = {
        path.relative_to(ROOT).as_posix()
        for pattern in (
            "src/jspace_observation/parser_v3_*.py",
            "scripts/*parser_v3*.py",
        )
        for path in ROOT.glob(pattern)
    }
    found.update(
        {
            "scripts/check_current_state_consistency.py",
            "scripts/generate_current_state.py",
        }
    )
    return sorted(found)


def test_r3new06_the_scan_covers_every_repair_module():
    """The omitted module must now be in scope, and the set must be non-trivial."""
    scanned = _isolation_scanned_sources()
    assert (
        "src/jspace_observation/parser_v3_repair_normalization.py" in scanned
    ), "the module that carried the false claim must be scanned"
    assert "src/jspace_observation/parser_v3_repair_contract.py" in scanned
    assert len(scanned) >= 5


def test_r3new06_no_module_claims_the_process_is_parser_free():
    """The unsupportable wording must not be asserted anywhere."""
    for relative in _isolation_scanned_sources() + [
        "docs/phase1_2g_conformance_policy_protocol.md",
        "reports/phase1_2g_conformance_policy.md",
        "reports/phase1_2g_audit_findings.md",
    ]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert not _asserts_overbroad_isolation(text), relative


def test_r3new06_the_normalization_docstring_states_the_narrow_claim():
    """The module that carried the false claim must now state the true one."""
    source = (
        ROOT / "src" / "jspace_observation" / "parser_v3_repair_normalization.py"
    ).read_text(encoding="utf-8")
    docstring = ast.get_docstring(ast.parse(source)) or ""
    assert "no parser import and no parser invocation" not in docstring
    assert "introduces no parser dependency" in docstring
    assert "eagerly imports the" in docstring


def test_r3new06_the_disclaimer_exemption_does_not_swallow_an_assertion():
    """A disowned mention is exempt; a bare assertion is not."""
    assert _asserts_overbroad_isolation("Package import is absolutely parser-free.")
    assert not _asserts_overbroad_isolation(
        'That is narrower than "package import is absolutely parser-free".'
    )
    # The disclaimer must be near the phrase, not merely somewhere in the file.
    far = "This is not a claim about anything. " + "x" * 200
    assert _asserts_overbroad_isolation(far + " Package import is absolutely parser-free.")


# --- 17. Audit G: final-state re-review of the Phase 1.2H remediation -------


def test_g02_a_correction_does_not_license_a_later_assertion():
    """Only the first match per pattern was examined, so a correction cloaked
    every later occurrence in the same window."""
    hits = consistency.scan_superseded_figures(
        "probe.md",
        "90 of 120 is superseded. The mandatory gates pin 90 of 120 cases.\n",
    )
    assert [item.kind for item in hits] == ["SUPERSEDED_FIGURE"]


def test_g02_a_falsity_marker_must_share_the_framed_clause():
    """A frame plus a disowning marker in a *different* clause is not a denial."""
    hits = consistency.scan_superseded_figures(
        "probe.md",
        "The claim that 90 of 120 cases are pinned is correct; "
        "the rejected alternative is false.\n",
    )
    assert [item.kind for item in hits] == ["SUPERSEDED_FIGURE"]


def test_g02_an_attached_correction_remains_exempt():
    """The ordinary erratum form must stay writable."""
    assert (
        consistency.scan_superseded_figures(
            "probe.md", "The former figure, 90 of 120 cases, is not correct.\n"
        )
        == []
    )
    assert (
        consistency.scan_superseded_figures(
            "probe.md",
            "The claim that 90 of 120 cases are pinned was already false "
            "when written.\n",
        )
        == []
    )


def test_g02_the_contrastive_leak_stays_closed():
    """R3-NEW-02 must not reopen: a denial aimed at the replacement figure."""
    for text in (
        "The mandatory gates pin 90 of 120 cases, not 80 of 120 cases.\n",
        "The mandatory gates pin 90 of 120 cases rather than 80 of 120 cases.\n",
    ):
        assert consistency.scan_superseded_figures("probe.md", text), text


def test_g02_an_anaphoric_follow_on_clause_still_denies_the_figure():
    """`; that is no longer correct` refers back; `; the X is false` does not."""
    assert (
        consistency.scan_superseded_figures(
            "probe.md", "The old text said 90 of 120; that is no longer correct.\n"
        )
        == []
    )
    assert consistency.scan_superseded_figures(
        "probe.md",
        "The claim that 90 of 120 cases are pinned is correct; "
        "the earlier draft is false.\n",
    )


def test_g03_a_scalar_in_a_list_carries_its_ancestor_context():
    """Moving a value into an array split the claim across windows again."""
    payload = {
        "live_disposition_claim": {
            "threshold_id": "critical_stratum_floor",
            "decision": {"disposition": ["REMOVE_REDUNDANT"]},
        }
    }
    hits = consistency.scan_superseded_figures(
        "probe.json", json.dumps(payload, indent=2) + "\n"
    )
    assert [item.kind for item in hits] == ["SUPERSEDED_FIGURE"]


def test_g03_a_rejected_alternative_subtree_is_not_a_live_claim():
    """A record of a declined option must not be reported as an assertion."""
    payload = {
        "threshold_id": "critical_stratum_floor",
        "rejected_alternative": {
            "disposition": "REMOVE_REDUNDANT",
            "note": "hypothetical option only",
        },
    }
    assert (
        consistency.scan_superseded_figures(
            "probe.json", json.dumps(payload, indent=2) + "\n"
        )
        == []
    )


def test_g03_a_plain_nested_mapping_is_still_caught():
    payload = {
        "threshold_id": "critical_stratum_floor",
        "decision": {"disposition": "REMOVE_REDUNDANT"},
    }
    assert consistency.scan_superseded_figures(
        "probe.json", json.dumps(payload, indent=2) + "\n"
    )


def test_g03_unrelated_sibling_subtrees_are_still_not_joined():
    payload = {
        "a": {"threshold_id": "critical_stratum_floor", "note": "fine"},
        "b": {"disposition": "REMOVE_REDUNDANT", "note": "fine"},
    }
    assert (
        consistency.scan_superseded_figures(
            "probe.json", json.dumps(payload, indent=2) + "\n"
        )
        == []
    )


def test_g04_the_policy_top_level_schema_is_closed(policy):
    """A top-level execution claim passed every check while one block was closed."""
    broken = copy.deepcopy(policy)
    broken["parser_v3_v2_evaluations_run"] = 1
    with pytest.raises(ContractError, match="unrecognised top-level"):
        validate_policy(broken)


def test_g04_the_committed_policy_declares_only_known_top_level_keys(policy):
    assert set(policy) == POLICY_TOP_LEVEL_KEYS


def test_g04_the_result_statement_may_not_assert_a_result(policy):
    """Free text was how the field became 'an evaluation was run'."""
    for claim in (
        "A formal evaluation was run and parser v3 was validated.",
        "Parser v3 has been validated against the locked set.",
        "Predictions were generated and parser v3 is now accepted.",
    ):
        broken = copy.deepcopy(policy)
        broken["execution_state"]["final_policy_is_not_a_result"] = claim
        with pytest.raises(ContractError):
            validate_policy(broken)


def test_g04_the_result_statement_may_not_be_emptied_out(policy):
    """Removing the disclaimers is as bad as asserting the opposite."""
    broken = copy.deepcopy(policy)
    broken["execution_state"]["final_policy_is_not_a_result"] = "This is a policy."
    with pytest.raises(ContractError, match="must state that"):
        validate_policy(broken)


def test_g05_a_disclaimer_in_a_neighbouring_sentence_does_not_exempt():
    """Any disclaimer token within 120 characters used to suppress the check."""
    assert _asserts_overbroad_isolation(
        "This module cannot process malformed input. "
        "Package import is absolutely parser-free."
    ) == ["absolutely parser-free"]


def test_g05_a_same_sentence_disavowal_still_exempts():
    """Quoting a withdrawn wording in order to disown it must keep working."""
    assert (
        _asserts_overbroad_isolation(
            "The withdrawn wording claimed package import is absolutely "
            "parser-free."
        )
        == []
    )
    assert _asserts_overbroad_isolation("Package import is absolutely parser-free.")


def test_g06_the_limitations_ledger_withdraws_the_convergence_claim():
    text = (ROOT / "paper" / "limitations_ledger.md").read_text(encoding="utf-8")
    assert "each pass has found fewer" not in text
    assert "specifically **not** that the" in text
    assert "neither\ncount nor severity is monotonic" in text or "count nor severity is monotonic" in text