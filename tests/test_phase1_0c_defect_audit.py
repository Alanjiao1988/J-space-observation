"""Tests for the Phase 1.0C generation-profile defect audit.

These tests recompute the facts the controlling authority states about Phase
1.0C run ``20260725T170041Z`` from the committed artifact pack.  They are
regression tests over an immutable historical record: if a number here moves,
either the pack was edited or the audit is wrong, and both are defects.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation.phase1_0c_defect_audit import (
    AUTHORITY_EXPECTED_FACTS,
    DefectAuditError,
    LITERAL_FORMAT_LINE,
    LITERAL_PLACEHOLDER,
    PHASE_1_0C_RECORDS_PATH,
    REGISTERED_MAX_NEW_TOKENS,
    audit_phase_1_0c_defects,
    build_defect_receipt,
    compare_to_authority,
    load_phase_1_0c_records,
    single_cause_attribution_is_refuted,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def records():
    return load_phase_1_0c_records()


@pytest.fixture(scope="module")
def audit(records):
    return audit_phase_1_0c_defects(records)


def _synthetic_record(
    record_id: str,
    *,
    prompt_text: str,
    output_text: str,
    output_token_count: int,
    reviewed: bool,
    semantic_label: str,
    truncated: bool | None = None,
):
    if truncated is None:
        truncated = output_token_count >= REGISTERED_MAX_NEW_TOKENS
    return {
        "record_id": record_id,
        "condition": "r1_style_thinking",
        "output_text": output_text,
        "provenance": {
            "prompt_text": prompt_text,
            "cell_id": "synthetic|easy|r1_style_thinking",
            "max_new_tokens": REGISTERED_MAX_NEW_TOKENS,
            "output_token_count": output_token_count,
        },
        "evaluation": {
            "review_required": reviewed,
            "truncated": truncated,
            "semantic_label": semantic_label,
        },
    }


# ---------------------------------------------------------------------------
# The committed pack still exists and is still the pack the audit describes
# ---------------------------------------------------------------------------


def test_the_phase_1_0c_record_pack_is_still_committed():
    assert (REPO_ROOT / PHASE_1_0C_RECORDS_PATH).is_file()


def test_every_record_was_generated_at_the_registered_token_cap(records):
    caps = {record["provenance"]["max_new_tokens"] for record in records}
    assert caps == {REGISTERED_MAX_NEW_TOKENS}


def test_the_run_used_only_the_two_registered_visible_reasoning_conditions(audit):
    assert audit.conditions == ("r1_style_thinking", "visible_cot")


# ---------------------------------------------------------------------------
# Section 4.1 facts, recomputed
# ---------------------------------------------------------------------------


def test_the_record_count_is_three_hundred(audit):
    assert audit.record_count == 300


def test_every_prompt_carried_the_literal_answer_placeholder_line(audit):
    assert audit.prompts_with_literal_format_line == 300
    assert audit.prompts_with_literal_format_line == audit.record_count


def test_thirty_one_outputs_echoed_the_literal_placeholder(audit):
    assert audit.outputs_containing_literal_placeholder == 31


def test_five_outputs_echoed_the_whole_format_line(audit):
    assert audit.outputs_containing_format_line_placeholder_form == 5


def test_two_hundred_and_twenty_five_rows_were_flagged_for_review(audit):
    assert audit.reviewed_row_count == 225


def test_seventy_nine_reviewed_rows_reached_the_token_cap(audit):
    assert audit.reviewed_rows_at_token_cap == 79


def test_forty_four_rows_remained_semantically_unresolved(audit):
    assert audit.unresolved_row_count == 44


def test_all_authority_facts_are_reproduced(audit):
    assert compare_to_authority(audit) == {}
    assert set(AUTHORITY_EXPECTED_FACTS) == {
        "record_count",
        "prompts_with_literal_format_line",
        "outputs_containing_literal_placeholder",
        "outputs_containing_format_line_placeholder_form",
        "reviewed_row_count",
        "reviewed_rows_at_token_cap",
        "unresolved_row_count",
    }


# ---------------------------------------------------------------------------
# The two defects are independent, and neither explains the whole outcome
# ---------------------------------------------------------------------------


def test_the_placeholder_echo_is_a_strict_subset_of_the_prompts_carrying_it(audit):
    assert audit.outputs_containing_literal_placeholder < audit.record_count
    assert (
        audit.outputs_containing_format_line_placeholder_form
        <= audit.outputs_containing_literal_placeholder
    )


def test_the_unresolved_rows_partition_exactly_over_the_two_defects(audit):
    assert sum(audit.unresolved_by_defect.values()) == audit.unresolved_row_count


def test_no_single_defect_explains_every_unresolved_row(audit):
    by_defect = audit.unresolved_by_defect
    placeholder_total = by_defect["placeholder_only"] + by_defect["both"]
    token_cap_total = by_defect["token_cap_only"] + by_defect["both"]
    assert placeholder_total < audit.unresolved_row_count
    assert token_cap_total < audit.unresolved_row_count
    assert single_cause_attribution_is_refuted(audit)


def test_the_recorded_truncation_flag_agrees_with_the_token_count(audit):
    assert audit.token_cap_flag_disagreements == 0


# ---------------------------------------------------------------------------
# Synthetic controls: the audit must actually respond to the thing it measures
# ---------------------------------------------------------------------------


def test_a_clean_synthetic_pack_reports_no_defects():
    clean = [
        _synthetic_record(
            f"clean-{index}",
            prompt_text="What is 2 + 2? End with the final answer itself.",
            output_text="4",
            output_token_count=3,
            reviewed=False,
            semantic_label="correct",
        )
        for index in range(4)
    ]
    result = audit_phase_1_0c_defects(clean)
    assert result.prompts_with_literal_format_line == 0
    assert result.outputs_containing_literal_placeholder == 0
    assert result.unresolved_row_count == 0
    assert single_cause_attribution_is_refuted(result) is False


def test_a_placeholder_only_pack_is_not_reported_as_refuting_single_cause():
    rows = [
        _synthetic_record(
            f"placeholder-{index}",
            prompt_text=f"Question {index}. {LITERAL_FORMAT_LINE}",
            output_text=f"{LITERAL_FORMAT_LINE}",
            output_token_count=10,
            reviewed=True,
            semantic_label="unresolved",
        )
        for index in range(3)
    ]
    result = audit_phase_1_0c_defects(rows)
    assert result.unresolved_by_defect["placeholder_only"] == 3
    assert result.unresolved_by_defect["token_cap_only"] == 0
    assert single_cause_attribution_is_refuted(result) is False


def test_a_token_cap_only_pack_is_not_reported_as_refuting_single_cause():
    rows = [
        _synthetic_record(
            f"cap-{index}",
            prompt_text=f"Question {index}. {LITERAL_FORMAT_LINE}",
            output_text="the reasoning runs on and never lands",
            output_token_count=REGISTERED_MAX_NEW_TOKENS,
            reviewed=True,
            semantic_label="unresolved",
        )
        for index in range(3)
    ]
    result = audit_phase_1_0c_defects(rows)
    assert result.unresolved_by_defect["token_cap_only"] == 3
    assert result.unresolved_by_defect["placeholder_only"] == 0
    assert single_cause_attribution_is_refuted(result) is False


def test_a_mixed_pack_refutes_single_cause_attribution():
    rows = [
        _synthetic_record(
            "mixed-placeholder",
            prompt_text=f"Q. {LITERAL_FORMAT_LINE}",
            output_text=LITERAL_PLACEHOLDER,
            output_token_count=5,
            reviewed=True,
            semantic_label="unresolved",
        ),
        _synthetic_record(
            "mixed-cap",
            prompt_text=f"Q. {LITERAL_FORMAT_LINE}",
            output_text="runs on",
            output_token_count=REGISTERED_MAX_NEW_TOKENS,
            reviewed=True,
            semantic_label="unresolved",
        ),
    ]
    result = audit_phase_1_0c_defects(rows)
    assert single_cause_attribution_is_refuted(result) is True


def test_a_mutated_count_is_detected_against_the_authority(records):
    mutated = [copy.deepcopy(record) for record in records]
    target = next(
        index
        for index, record in enumerate(mutated)
        if LITERAL_PLACEHOLDER not in record["output_text"]
    )
    mutated[target]["output_text"] += LITERAL_PLACEHOLDER
    result = audit_phase_1_0c_defects(mutated)
    mismatches = compare_to_authority(result)
    assert "outputs_containing_literal_placeholder" in mismatches
    assert mismatches["outputs_containing_literal_placeholder"] == {
        "authority": AUTHORITY_EXPECTED_FACTS["outputs_containing_literal_placeholder"],
        "observed": AUTHORITY_EXPECTED_FACTS["outputs_containing_literal_placeholder"]
        + 1,
    }


def test_a_record_generated_at_another_cap_is_refused():
    row = _synthetic_record(
        "wrong-cap",
        prompt_text="Q",
        output_text="A",
        output_token_count=1,
        reviewed=False,
        semantic_label="correct",
    )
    row["provenance"]["max_new_tokens"] = 1024
    with pytest.raises(DefectAuditError):
        audit_phase_1_0c_defects([row])


def test_a_record_without_a_prompt_is_refused():
    row = _synthetic_record(
        "no-prompt",
        prompt_text="Q",
        output_text="A",
        output_token_count=1,
        reviewed=False,
        semantic_label="correct",
    )
    del row["provenance"]["prompt_text"]
    with pytest.raises(DefectAuditError):
        audit_phase_1_0c_defects([row])


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


def test_the_receipt_records_both_defects_and_reproduces_the_authority(audit):
    receipt = build_defect_receipt(audit)
    assert receipt["authority_facts_reproduced"] is True
    assert receipt["authority_mismatches"] == {}
    assert receipt["single_cause_attribution_refuted"] is True
    assert receipt["historical_status_preserved"] == "COMPLETE_INCONCLUSIVE"
    assert [defect["id"] for defect in receipt["defects"]] == ["P10C-D1", "P10C-D2"]
    assert json.loads(json.dumps(receipt)) == receipt


def test_the_receipt_carries_no_prompt_or_output_text(audit):
    serialized = json.dumps(build_defect_receipt(audit))
    assert "prompt_text" not in serialized
    assert "output_text" not in serialized
