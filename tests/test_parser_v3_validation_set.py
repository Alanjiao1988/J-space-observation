"""Model-free tests for the Phase 1.2C parser-v3-v1 locked evaluator set.

The locked inputs, the locked labels and everything under ``private/`` are
gitignored holdout material.  Tests that need them are skipped when they are not
present so that a fresh clone still passes; the tests that guarantee secrecy and
protocol shape always run.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts import build_parser_v3_validation_set as builder

SET_ROOT = builder.SET_ROOT
MANIFEST_ROOT = builder.MANIFEST_ROOT
PRIVATE_ROOT = builder.PRIVATE_ROOT
LOCKED_INPUTS = builder.LOCKED_INPUTS_PATH
LOCKED_LABELS = builder.LOCKED_LABELS_PATH
INPUTS_MANIFEST = builder.INPUTS_MANIFEST_PATH
LABELS_MANIFEST = builder.LABELS_MANIFEST_PATH
SET_MANIFEST = builder.SET_MANIFEST_PATH

SET_PREFIX = "evaluator_sets/parser_v3_v1/"

requires_inputs = pytest.mark.skipif(
    not LOCKED_INPUTS.is_file(), reason="locked inputs are private holdout material"
)
requires_labels = pytest.mark.skipif(
    not LOCKED_LABELS.is_file(), reason="locked labels are private holdout material"
)
requires_manifests = pytest.mark.skipif(
    not SET_MANIFEST.is_file(),
    reason="manifests have not been built in this worktree",
)


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------- label secrecy


def git_check_ignore(relative: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "check-ignore", "-v", relative],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_locked_label_path_is_gitignored():
    result = git_check_ignore(SET_PREFIX + builder.LOCKED_LABELS_NAME)
    assert result.returncode == 0, (
        "locked_labels.jsonl is NOT gitignored; holdout labels must never be committable"
    )
    assert builder.LOCKED_LABELS_NAME in result.stdout


def test_every_private_artifact_is_gitignored():
    private_names = [name for name, kind in builder.SECRECY.items() if kind == "private"]
    assert sorted(private_names) == sorted(
        [
            builder.ARBITRATION_NAME,
            builder.LOCKED_INPUTS_NAME,
            builder.LOCKED_LABELS_NAME,
            builder.REVIEWER_A_NAME,
            builder.REVIEWER_B_NAME,
        ]
    )
    for name in private_names + [
        "private/case_sources.jsonl",
        "private/salts.json",
        "private/reviewer_packet.jsonl",
    ]:
        result = git_check_ignore(SET_PREFIX + name)
        assert result.returncode == 0, f"{name} is not gitignored"


def test_manifests_directory_and_public_manifests_are_not_gitignored():
    """The manifests are the reviewable surface of the set and must be committable.

    ``git check-ignore`` is queried without a trailing slash: for a directory that
    holds no tracked file yet, a trailing-slash query makes git report a spurious
    match against the blank final line of ``.gitignore`` (``scripts/nosuchdir/``
    reproduces it identically), so a trailing-slash probe is not evidence.
    """

    result = git_check_ignore(SET_PREFIX.rstrip("/") + "/manifests")
    assert result.returncode != 0, (
        "the manifests directory is gitignored; the set would not be reviewable"
    )
    public_names = [name for name, kind in builder.SECRECY.items() if kind == "public"]
    assert sorted(public_names) == [
        f"manifests/{builder.INPUTS_MANIFEST_NAME}",
        f"manifests/{builder.LABELS_MANIFEST_NAME}",
        f"manifests/{builder.SET_MANIFEST_NAME}",
    ]
    for name in public_names:
        result = git_check_ignore(SET_PREFIX + name)
        assert result.returncode != 0, f"{name} is gitignored but must be committable"


def test_public_manifests_are_untracked_and_stageable():
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", SET_PREFIX],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    listed = {line[3:].strip().strip('"') for line in result.stdout.splitlines()}
    for name in (
        builder.INPUTS_MANIFEST_NAME,
        builder.LABELS_MANIFEST_NAME,
        builder.SET_MANIFEST_NAME,
    ):
        relative = f"{SET_PREFIX}manifests/{name}"
        if not (MANIFEST_ROOT / name).is_file():
            continue
        assert relative in listed, f"{relative} is not visible to git as a stageable file"


def test_no_holdout_file_is_stageable():
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    forbidden = (
        builder.LOCKED_LABELS_NAME,
        builder.LOCKED_INPUTS_NAME,
        builder.REVIEWER_A_NAME,
        builder.REVIEWER_B_NAME,
        builder.ARBITRATION_NAME,
        "parser_v3_v1/private/",
    )
    offending = [
        line
        for line in result.stdout.splitlines()
        if any(token in line for token in forbidden)
    ]
    assert offending == [], f"holdout material is stageable: {offending}"


def test_builder_source_contains_no_case_text():
    """The committed builder must be reproducible without leaking the holdout."""

    source = (ROOT / "scripts" / "build_parser_v3_validation_set.py").read_text(
        encoding="utf-8"
    )
    assert "private" in source, "the builder must load case text from the private path"
    if not LOCKED_INPUTS.is_file():
        pytest.skip("locked inputs are private holdout material")
    for row in read_jsonl(LOCKED_INPUTS):
        assert row["output_text"] not in source, row["case_id"]
        assert row["case_id"] not in source, row["case_id"]


def test_public_documents_carry_no_label_content():
    case_id_pattern = re.compile(r"PV3-[0-9a-f]{20}")
    texts = (
        [row["output_text"] for row in read_jsonl(LOCKED_INPUTS)]
        if LOCKED_INPUTS.is_file()
        else []
    )
    for relative in (
        "evaluator_sets/parser_v3_v1/strata_definitions.md",
        "docs/phase1_parser_v3_locked_set.md",
        "docs/phase1_parser_v3_sealing_run.md",
        "reports/phase1_parser_v3_validation_set.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "expected_parsed_answer" not in text, relative
        assert case_id_pattern.search(text) is None, relative
        for case_text in texts:
            assert case_text not in text, relative


def test_artifact_pack_carries_no_case_text_or_labels():
    pack_root = ROOT / "artifacts" / "phase1-evaluator-validation" / "track-d"
    if not pack_root.is_dir():
        pytest.skip("the Track D artifact pack has not been generated in this worktree")
    texts = (
        [row["output_text"] for row in read_jsonl(LOCKED_INPUTS)]
        if LOCKED_INPUTS.is_file()
        else []
    )
    files = sorted(path for path in pack_root.rglob("*") if path.is_file())
    assert files, "the artifact pack directory is empty"
    for path in files:
        blob = path.read_text(encoding="utf-8")
        assert "expected_parsed_answer" not in blob, path.name
        assert "expected_answer_presence" not in blob, path.name
        for case_text in texts:
            assert case_text not in blob, (path.name, "case text leaked")


def test_artifact_pack_is_complete_and_manifest_written_last():
    pack_root = ROOT / "artifacts" / "phase1-evaluator-validation" / "track-d"
    if not pack_root.is_dir():
        pytest.skip("the Track D artifact pack has not been generated in this worktree")
    expected = [
        "00_stage_manifest.json",
        "01_protocol_snapshot.json",
        "02_records.jsonl",
        "03_metrics.csv",
        "04_decision.json",
        "05_summary.md",
        "06_paper_table.csv",
        "07_figure_data.csv",
        "08_deviations.json",
    ]
    for run_dir in sorted(p for p in pack_root.iterdir() if p.is_dir()):
        names = sorted(p.name for p in run_dir.iterdir() if p.is_file())
        assert names == sorted(expected + ["artifact_manifest.json"]), run_dir.name
        manifest = load_json(run_dir / "artifact_manifest.json")
        assert manifest["manifest_written_last"] is True
        assert manifest["write_order"] == expected + ["artifact_manifest.json"]
        for entry in manifest["files"]:
            payload = (run_dir / entry["path"]).read_bytes()
            assert len(payload) == entry["bytes"], entry["path"]
            assert builder.sha256_bytes(payload) == entry["sha256"], entry["path"]
        decision = load_json(run_dir / "04_decision.json")
        assert decision["status"] in {
            "PASS", "FAIL", "COMPLETE", "INCONCLUSIVE", "BLOCKED",
        }
        joined = " ".join(decision["prohibited_interpretations"]).lower()
        assert "no parser-v3 evaluation was run" in joined
        assert "no parser-v3 result exists" in joined
        deviations = load_json(run_dir / "08_deviations.json")
        assert set(deviations) == {
            "deviations", "unregistered_changes", "effect_on_interpretation",
        }
        header = (run_dir / "03_metrics.csv").read_text(encoding="utf-8").splitlines()[0]
        assert header == (
            "run_id,phase,track,metric,stratum,condition,n,numerator,denominator,"
            "value,ci_lower,ci_upper,threshold,passed,not_applicable_reason"
        )
        sections = [
            line.strip()
            for line in (run_dir / "05_summary.md").read_text(encoding="utf-8").splitlines()
            if line.startswith("#")
        ]
        assert sections == [
            "# Summary",
            "## Objective",
            "## Scope",
            "## Provenance",
            "## Execution",
            "## Results",
            "## Decision",
            "## Deviations and errors",
            "## Scientific interpretation",
            "## Limitations",
            "## Paper relevance",
            "## Next gate",
        ]


# ------------------------------------------------------------------- schema


@requires_inputs
def test_locked_inputs_schema_and_size():
    rows = read_jsonl(LOCKED_INPUTS)
    assert len(rows) == builder.TOTAL_CASES == 120
    assert len({row["case_id"] for row in rows}) == 120
    for row in rows:
        assert sorted(row) == [
            "case_id",
            "output_text",
            "parse_type",
            "schema_version",
            "set_id",
            "source_kind",
        ]
        assert row["schema_version"] == builder.INPUT_SCHEMA
        assert row["set_id"] == builder.SET_ID
        assert row["parse_type"] == "numeric"
        assert row["case_id"].startswith("PV3-")
        assert isinstance(row["output_text"], str) and row["output_text"]
        assert "stratum" not in row
        assert not any(key.startswith("expected_") for key in row)


@requires_labels
def test_locked_labels_schema_and_size():
    rows = read_jsonl(LOCKED_LABELS)
    assert len(rows) == 120
    assert len({row["case_id"] for row in rows}) == 120
    for row in rows:
        assert row["schema_version"] == builder.LABEL_SCHEMA
        assert row["set_id"] == builder.SET_ID
        assert row["stratum"] in builder.STRATA
        assert row["expected_answer_presence"] in builder.PRESENCE_VALUES
        assert row["expected_extraction_strategy"] in builder.STRATEGY_VALUES
        assert row["expected_output_quality"] in builder.QUALITY_VALUES
        assert set(row["expected_failure_reasons"]) <= set(builder.FAILURE_VALUES)
        assert set(row["expected_format_warnings"]) <= set(builder.WARNING_VALUES)
        assert row["label_source"] in ("consensus", "arbitrated")
        assert "output_text" not in row


@requires_labels
def test_label_internal_consistency():
    for row in read_jsonl(LOCKED_LABELS):
        valid = row["expected_parse_valid"]
        parsed = row["expected_parsed_answer"]
        selected = [
            span
            for span in row["expected_evidence_spans"]
            if span["disposition"] == "selected"
        ]
        if valid:
            assert row["expected_failure_reasons"] == []
        else:
            assert row["expected_failure_reasons"] != []
            assert parsed is None
            assert selected == []
        if row["expected_parse_ambiguous"]:
            assert len(row["expected_candidate_answers"]) >= 2
        else:
            assert row["expected_candidate_answers"] == []
        if parsed is not None:
            assert builder.canonical_numeric(parsed) == parsed
            assert len(selected) == 1
        expected_correct = (
            row["expected_answer_presence"] == "present"
            and parsed is not None
            and parsed == builder.canonical_numeric(row["registered_reference_answer"])
        )
        assert row["expected_correctness"] is expected_correct


@requires_labels
def test_label_and_input_case_ids_match():
    inputs = {row["case_id"] for row in read_jsonl(LOCKED_INPUTS)}
    labels = {row["case_id"] for row in read_jsonl(LOCKED_LABELS)}
    assert inputs == labels


# ------------------------------------------------------------- stratum quotas


@requires_labels
def test_stratum_quotas():
    counts = Counter(row["stratum"] for row in read_jsonl(LOCKED_LABELS))
    assert sorted(counts) == builder.STRATA
    assert len(counts) == 12
    assert set(counts.values()) == {builder.CASES_PER_STRATUM}
    assert sum(counts.values()) == 120


@requires_manifests
def test_registered_composition_in_manifest():
    composition = load_json(SET_MANIFEST)["report"]["composition"]
    assert composition["per_stratum"] == {stratum: 10 for stratum in builder.STRATA}
    assert composition["presence"] == {
        "present": 80,
        "no_answer": 30,
        "ambiguous": 10,
    }
    assert composition["critical_cases"] == 80
    features = composition["features"]
    for key in (
        "negative_answers",
        "decimal_surfaces",
        "fraction_surfaces",
        "balanced_think_regions",
        "malformed_think_regions",
    ):
        assert features[key] >= 10, key


@requires_labels
def test_case_ids_are_derived_from_text():
    salts = json.loads((PRIVATE_ROOT / "salts.json").read_text(encoding="utf-8"))
    for row in read_jsonl(LOCKED_INPUTS):
        assert (
            builder.case_id_for(row["output_text"], "numeric", salts["case_id_salt"])
            == row["case_id"]
        )


# ------------------------------------------------------------------- overlap


@requires_inputs
def test_zero_overlap_against_reachable_corpora():
    salts = builder.load_or_create_salts()
    cases = builder.load_case_sources(salts["case_id_salt"])
    report = builder.overlap_report(cases)
    assert report["hard_exact_overlap"] == 0
    assert report["normalized_overlap"] == 0
    assert report["numeric_normalized_overlap"] == 0
    assert report["internal_exact_duplicates"] == 0
    assert report["internal_normalized_duplicates"] == 0
    assert report["near_duplicates_vs_prior"] == []
    assert report["near_duplicates_internal"] == []
    assert report["checked_sources"], "no prior corpus was reachable"
    builder.require_zero_overlap(report)


@requires_manifests
def test_manifest_records_zero_overlap_and_names_the_gaps():
    overlap = load_json(SET_MANIFEST)["report"]["overlap"]
    assert overlap["hard_exact_overlap"] == 0
    assert overlap["normalized_overlap"] == 0
    assert overlap["numeric_normalized_overlap"] == 0
    assert overlap["hard_failure_count"] == 0
    corpora = {entry["corpus"] for entry in overlap["unreachable_corpora"]}
    assert any("retired locked holdout" in name for name in corpora)


def test_normalization_folds_the_documented_variations():
    base = builder.normalize_text("Final  answer:\r\n  -0.50 ")
    assert base == builder.normalize_text("FINAL ANSWER: -0.50")
    assert builder.normalize_text("a\u2014b") == builder.normalize_text("a-b")
    assert builder.normalize_text("x\uff1ay") == builder.normalize_text("x:y")
    assert builder.numeric_normalized_text("value 6/8") == builder.numeric_normalized_text(
        "value 0.75"
    )
    assert builder.masked_template_text("a 12 b") == builder.masked_template_text("a -3.5 b")


def test_canonical_numeric_rejects_illegal_literals():
    for literal in ("3/0", "--4", "1 2 3", "1e999999999", ""):
        with pytest.raises(builder.BuildError):
            builder.canonical_numeric(literal)
    assert builder.canonical_numeric("+0007") == "7"
    assert builder.canonical_numeric("-0.0") == "0"
    assert builder.canonical_numeric("6/8") == "3/4"
    assert builder.canonical_numeric(".75") == "3/4"
    assert builder.canonical_numeric("1.5e3") == "1500"


# ---------------------------------------------------------- manifest integrity


@requires_manifests
def test_manifest_digests_match_the_files_on_disk():
    overall = load_json(SET_MANIFEST)
    assert overall["set_id"] == builder.SET_ID
    assert overall["written_last"] is True
    seen = set()
    for entry in overall["files"]:
        path = SET_ROOT / entry["path"]
        assert entry["secrecy"] == builder.SECRECY[entry["path"]], entry["path"]
        assert entry["committed_to_git"] is (entry["secrecy"] == "public")
        if not path.is_file():
            pytest.skip(f"{entry['path']} is private holdout material in this worktree")
        payload = path.read_bytes()
        assert len(payload) == entry["bytes"], entry["path"]
        assert builder.sha256_bytes(payload) == entry["sha256"], entry["path"]
        assert entry["leaf"] in ("locked-inputs", "locked-labels", "manifests")
        seen.add(entry["path"])
    assert builder.LOCKED_INPUTS_NAME in seen
    assert f"manifests/{builder.INPUTS_MANIFEST_NAME}" in seen


@requires_inputs
def test_input_manifest_fingerprints_match_the_records():
    manifest = load_json(INPUTS_MANIFEST)
    assert manifest["record_count"] == 120
    assert manifest["file"]["secrecy"] == "private"
    assert manifest["file"]["committed_to_git"] is False
    assert set(manifest["fingerprint_scheme"]) == {
        "exact_sha256",
        "normalized_sha256",
        "numeric_normalized_sha256",
        "masked_template_sha256",
    }
    by_id = {row["case_id"]: row for row in read_jsonl(LOCKED_INPUTS)}
    assert len(manifest["records"]) == 120
    for record in manifest["records"]:
        text = by_id[record["case_id"]]["output_text"]
        expected = builder.fingerprints(text)
        for key, value in expected.items():
            assert record[key] == value, (record["case_id"], key)
        assert record["output_text_chars"] == len(text)
        assert "output_text" not in record


@requires_labels
def test_label_manifest_is_salted_and_leaks_no_label_values():
    manifest = load_json(LABELS_MANIFEST)
    assert manifest["record_count"] == 120
    assert "HMAC" in manifest["fingerprint_scheme"]
    assert manifest["file"]["secrecy"] == "private"
    assert manifest["file"]["committed_to_git"] is False
    payload = LOCKED_LABELS.read_bytes()
    assert manifest["file"]["bytes"] == len(payload)
    assert manifest["file"]["sha256"] == builder.sha256_bytes(payload)
    for record in manifest["records"]:
        assert sorted(record) == ["case_id", "label_bytes", "label_fingerprint"]
        assert len(record["label_fingerprint"]) == 64


@requires_manifests
def test_manifest_reports_resolved_labels_and_arbitration_discipline():
    report = load_json(SET_MANIFEST)["report"]
    if not report["labels_present"]:
        pytest.skip("labels have not been built in this worktree")
    labeling = report["labeling"]
    assert labeling["unresolved"] == 0
    assert labeling["unresolved_case_ids"] == []
    assert labeling["final_labels"] == 120
    agreement = report["agreement"]
    assert agreement["n"] == 120
    assert labeling["arbitrated_rows"] == agreement["row_disagreements"]
    assert labeling["consensus_rows"] == agreement["row_exact_agreement"]
    assert labeling["arbitrated_rows"] + labeling["consensus_rows"] == 120


# ------------------------------------------------------- boundary variation


@requires_inputs
def test_span_boundary_variation_gate_passes_for_the_four_strata():
    salts = builder.load_or_create_salts()
    cases = builder.load_case_sources(salts["case_id_salt"])
    comparison = builder.span_boundary_comparison(
        cases, builder.load_parser_v2_development()
    )
    assert comparison["all_passed"] is True
    for stratum in ("S01", "S02", "S05", "S06"):
        entry = comparison[stratum]
        assert entry["passed"] is True, stratum
        assert entry["windows_missing_from_v3"] == [], stratum
        assert entry["checks"]["more_distinct_windows"] is True, stratum
        assert entry["checks"]["wider_tail_gap_range"] is True, stratum


# ------------------------------------------------------------- determinism


@requires_labels
def test_rebuild_is_byte_identical():
    before = {
        path: path.read_bytes()
        for path in (
            LOCKED_INPUTS,
            LOCKED_LABELS,
            INPUTS_MANIFEST,
            LABELS_MANIFEST,
            SET_MANIFEST,
        )
    }
    assert builder.run("all") == 0
    for path, payload in before.items():
        assert path.read_bytes() == payload, f"{path.name} is not deterministic"
