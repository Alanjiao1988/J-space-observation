"""Tests for the Study 5-EQ1 append-only run journal.

Authority gate Q-7 requires create-only journaling to be *demonstrated*, and
section 9.1 registers a duplicate journal key as a hard blocker. These tests are
the demonstration, so they assert the failure modes and not only the happy path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location(
    "study5_eq1_journal", _TOOLS / "journal.py"
)
assert _SPEC is not None and _SPEC.loader is not None
journal_module = importlib.util.module_from_spec(_SPEC)
sys.modules["study5_eq1_journal"] = journal_module
_SPEC.loader.exec_module(journal_module)

Journal = journal_module.Journal
JournalRecord = journal_module.JournalRecord
DuplicateJournalKey = journal_module.DuplicateJournalKey
JournalIntegrityError = journal_module.JournalIntegrityError
RECORD_FIELDS = journal_module.RECORD_FIELDS


def _record(step_id: str = "S-001", phase: str = "P-0") -> JournalRecord:
    return JournalRecord(
        ts_start_utc="2026-08-27T00:00:00Z",
        ts_end_utc="2026-08-27T00:00:30Z",
        phase=phase,
        step_id=step_id,
        host="test-host",
        exit_status="ok",
        command_sha256="0" * 64,
        note="unit test",
    )


def test_record_carries_every_registered_field(tmp_path: Path) -> None:
    payload = Journal(tmp_path).append(_record())
    assert tuple(payload) == RECORD_FIELDS


def test_duration_is_derived_from_the_timestamps(tmp_path: Path) -> None:
    payload = Journal(tmp_path).append(_record())
    assert payload["duration_s"] == 30.0


def test_append_is_create_only_for_a_repeated_key(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    journal.append(_record())
    with pytest.raises(DuplicateJournalKey):
        journal.append(_record())
    lines = (tmp_path / "journal" / "P-0.jsonl").read_text(encoding="utf-8")
    assert lines.count("\n") == 1, "the rejected write must not have been appended"


def test_the_same_step_id_in_another_phase_is_a_distinct_key(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    journal.append(_record(phase="P-0"))
    journal.append(_record(phase="P-1"))
    assert journal.verify()["unique_keys"] == 2


def test_duplicate_keys_across_two_phase_files_are_detected(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    journal.append(_record())
    smuggled = json.loads((tmp_path / "journal" / "P-0.jsonl").read_text("utf-8"))
    other = tmp_path / "journal" / "P-1.jsonl"
    other.write_text(json.dumps(smuggled) + "\n", encoding="utf-8")
    with pytest.raises(DuplicateJournalKey):
        journal.verify()


def test_an_earlier_record_is_never_rewritten(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    first = journal.append(_record("S-001"))
    journal.append(_record("S-002"))
    path = tmp_path / "journal" / "P-0.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0]) == first


def test_a_truncated_journal_still_verifies_as_a_complete_prefix(
    tmp_path: Path,
) -> None:
    journal = Journal(tmp_path)
    journal.append(_record("S-001"))
    journal.append(_record("S-002"))
    path = tmp_path / "journal" / "P-0.jsonl"
    kept = path.read_text(encoding="utf-8").splitlines()[0]
    path.write_text(kept + "\n", encoding="utf-8")
    assert journal.verify()["records"] == 1


def test_malformed_json_is_an_integrity_error_not_a_silent_skip(
    tmp_path: Path,
) -> None:
    journal = Journal(tmp_path)
    journal.append(_record())
    path = tmp_path / "journal" / "P-0.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{not json}\n")
    with pytest.raises(JournalIntegrityError):
        journal.verify()


def test_gpu_seconds_roll_up_into_accelerator_hours(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    journal.append(
        JournalRecord(
            ts_start_utc="2026-08-27T00:00:00Z",
            ts_end_utc="2026-08-27T01:00:00Z",
            phase="P-1",
            step_id="S-001",
            host="test-host",
            exit_status="ok",
            command_sha256="0" * 64,
            gpu_index=0,
            gpu_seconds=3600.0,
        )
    )
    summary = journal.verify()
    assert summary["total_accelerator_hours"] == 1.0


def test_blocker_ids_are_surfaced_and_not_suppressed(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    journal.append(
        JournalRecord(
            ts_start_utc="2026-08-27T00:00:00Z",
            ts_end_utc="2026-08-27T00:00:01Z",
            phase="P-0",
            step_id="S-001",
            host="test-host",
            exit_status="blocked",
            command_sha256="0" * 64,
            blocker_id="HB-05",
        )
    )
    assert journal.verify()["blocker_ids"] == ["HB-05"]
