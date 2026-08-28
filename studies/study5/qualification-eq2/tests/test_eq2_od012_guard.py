"""OD-011 failing cases for the OD-012 ordering guard.

The guard's entire job is to catch a lens read that happened too early. A guard
that returned PASS on an empty journal, or on a journal with no convention
record, would be exactly the "check that cannot fail" OD-011 was written to
forbid, so those cases are tested explicitly.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location(
    "eq2_od012", _TOOLS / "verify_od012_ordering.py"
)
assert _SPEC is not None and _SPEC.loader is not None
guard = importlib.util.module_from_spec(_SPEC)
sys.modules["eq2_od012"] = guard
_SPEC.loader.exec_module(guard)

COMMIT = {"step_id": "R1-CONVENTION-COMMIT", "ts_start_utc": "2026-08-28T10:00:00Z"}


def rec(step_id, ts, note=""):
    return {"step_id": step_id, "ts_start_utc": ts, "note": note}


def read_rec(step_id, ts, ref):
    """A record that actually READS a lens: recorded in the provenance fields."""
    return {"step_id": step_id, "ts_start_utc": ts, "inputs_sha256": [ref], "note": ""}


# --------------------------------------------------------------------------
# positive path
# --------------------------------------------------------------------------


def test_reads_after_the_convention_commit_pass() -> None:
    records = [
        COMMIT,
        read_rec("R2-001", "2026-08-28T11:00:00Z", "merged/lens_A.pt=2910b7bf"),
    ]
    result = guard.judge(records)
    assert result["verdict"] == "PASS"
    assert result["lens_reading_record_count"] == 1


def test_a_journal_with_no_lens_reads_at_all_passes() -> None:
    result = guard.judge([COMMIT, rec("R1-005", "2026-08-28T10:30:00Z", "external only")])
    assert result["verdict"] == "PASS"
    assert result["lens_reading_record_count"] == 0


def test_prose_saying_the_lenses_were_not_read_is_not_a_read() -> None:
    """The guard must not fire on its own evidence.

    A note asserting the lenses have NOT been read references them without
    reading them. Treating that as a violation would force the record to be
    reworded to satisfy the checker, which is the wrong direction of fit.
    """

    records = [
        COMMIT,
        rec("R0-003", "2026-08-28T05:40:00Z", "lens_A and lens_B have NOT been read"),
    ]
    result = guard.judge(records)
    assert result["verdict"] == "PASS"
    assert result["lens_reading_record_count"] == 0
    assert "R0-003" in result["prose_mentions_not_reads"]


# --------------------------------------------------------------------------
# OD-011 failing cases
# --------------------------------------------------------------------------


def test_a_read_before_the_commit_is_caught() -> None:
    """The violation the rule exists to prevent."""

    records = [
        COMMIT,
        read_rec("R1-003", "2026-08-28T09:00:00Z", "lens_A.pt=2910b7bf"),
    ]
    result = guard.judge(records)
    assert result["verdict"] == "FAIL"
    assert result["violations"][0]["step_id"] == "R1-003"


def test_a_read_at_exactly_the_commit_timestamp_is_caught() -> None:
    """'Later than' must be strict; equal timestamps do not establish ordering."""

    records = [COMMIT, read_rec("R1-004", "2026-08-28T10:00:00Z", "lens_B.pt")]
    assert guard.judge(records)["verdict"] == "FAIL"


def test_renaming_the_file_does_not_evade_the_guard() -> None:
    """The content address is matched, not just the name.

    A lens copied to `scratch/tmp/x.pt` still carries EQ1's immutable sha256,
    so a guard that only matched on the filename would be trivially evaded.
    """

    records = [
        COMMIT,
        read_rec(
            "R1-009",
            "2026-08-28T09:10:00Z",
            "scratch/tmp/x.pt=2910b7bf80784a48f4e0d41f1a6fd002781f1d3f4f6bc3df83fb547848164083",
        ),
    ]
    result = guard.judge(records)
    assert result["verdict"] == "FAIL"
    assert result["violations"][0]["step_id"] == "R1-009"


def test_a_missing_convention_record_is_a_fail_not_a_pass() -> None:
    """The dangerous default.

    With no boundary record there is nothing for reads to be later than. A guard
    that reported PASS here would report PASS on precisely the journal where the
    convention was never committed at all.
    """

    result = guard.judge([read_rec("R2-001", "2026-08-28T11:00:00Z", "lens_A.pt")])
    assert result["verdict"] == "FAIL"
    assert result["convention_commit_present"] is False


def test_an_empty_journal_is_a_fail() -> None:
    result = guard.judge([])
    assert result["verdict"] == "FAIL"


def test_a_lens_read_with_no_timestamp_is_a_fail() -> None:
    """An unordered record cannot be shown to be later than anything."""

    records = [COMMIT, {"step_id": "R2-002", "inputs_sha256": ["lens_A.pt"]}]
    result = guard.judge(records)
    assert result["verdict"] == "FAIL"
    assert result["records_without_timestamp"] == ["R2-002"]


def test_duplicate_convention_records_are_a_fail() -> None:
    """Two boundaries means no single boundary."""

    second = dict(COMMIT, ts_start_utc="2026-08-28T12:00:00Z")
    result = guard.judge(
        [COMMIT, second, read_rec("R2-001", "2026-08-28T13:00:00Z", "lens_A.pt")]
    )
    assert result["verdict"] == "FAIL"


def test_a_lens_reference_hidden_in_inputs_is_still_detected() -> None:
    """A read recorded in the provenance fields is caught wherever it sits."""

    records = [
        COMMIT,
        {
            "step_id": "R1-002",
            "ts_start_utc": "2026-08-28T09:30:00Z",
            "inputs_sha256": ["p2/merged/lens_A.pt=2910b7bf"],
            "note": "nothing to see here",
        },
    ]
    result = guard.judge(records)
    assert result["verdict"] == "FAIL"
    assert result["violations"][0]["step_id"] == "R1-002"


def test_unrelated_words_containing_lens_do_not_trigger_a_false_positive() -> None:
    """The pattern is anchored, so 'lens' or 'lens_model' must not match."""

    records = [
        COMMIT,
        read_rec("R1-006", "2026-08-28T09:45:00Z", "external/lens_model_wrapper.py"),
    ]
    result = guard.judge(records)
    assert result["verdict"] == "PASS"
    assert result["lens_reading_record_count"] == 0
