"""Model/GPU/network-free tests for the Phase 0.5B J-lens saturation tooling."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "jspace_observation"))
sys.path.insert(0, str(ROOT))

import phase05_jlens as base
import phase05_jlens_saturation as sat
from scripts import phase05_jlens_saturation as runner

CORPUS_PATH = ROOT / "data" / "jlens_saturation_prompts.jsonl"
# Phase 0.5B registered the 50-record corpus. Phase 0.5C appended ten
# role=reserve prompts after byte 13452; the first 50 records are byte-identical
# and in unchanged order, so every Phase 0.5B fit and held-out set is unchanged.
BASE_CORPUS_SHA256 = "41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b"
BASE_CORPUS_BYTES = 13452
CORPUS_SHA256 = "dd5d97498324e8b5153c106f0edbc4d962d47771db7dfa2093b48fc36f5962fa"


@pytest.fixture(scope="module")
def corpus() -> dict:
    return sat.load_saturation_corpus(CORPUS_PATH)


@pytest.fixture(scope="module")
def plan(corpus: dict) -> dict:
    return sat.build_fit_plan(corpus)


@pytest.fixture(scope="module")
def self_test_pack(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_dir = tmp_path_factory.mktemp("saturation-self-test")
    exit_code = runner.main(
        [
            "--self-test",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "TESTRUN0001",
        ]
    )
    assert exit_code == 0
    return output_dir / sat.PHASE / sat.TRACK / "TESTRUN0001"


# ---------------------------------------------------------------------------
# corpus
# ---------------------------------------------------------------------------


def test_corpus_bytes_are_lf_utf8_and_pinned() -> None:
    raw = CORPUS_PATH.read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert base.sha256_file(CORPUS_PATH) == CORPUS_SHA256
    assert base.sha256_bytes(raw[:BASE_CORPUS_BYTES]) == BASE_CORPUS_SHA256
    raw.decode("utf-8")


def test_corpus_shape_roles_and_uniqueness(corpus: dict) -> None:
    assert corpus["file_sha256"] == CORPUS_SHA256
    assert corpus["revision"] == "r2-60"
    assert corpus["counts"] == {"fit": 25, "heldout": 10, "reserve": 25}
    assert len(corpus["records"]) == sat.CORPUS_REVISIONS["r2-60"]["records"]
    identifiers = [record["id"] for record in corpus["records"]]
    texts = [record["text"] for record in corpus["records"]]
    assert len(set(identifiers)) == len(identifiers)
    assert len(set(texts)) == len(texts)
    assert corpus["proxy_token_min"] >= sat.MIN_PROXY_TOKENS
    assert corpus["proxy_tokenizer"] == "regex_word_punctuation_proxy_v1"


def test_corpus_is_disjoint_from_every_other_registered_prompt_source() -> None:
    corpus_texts = {
        json.loads(line)["text"].strip().lower()
        for line in CORPUS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    for other in (
        ROOT / "data" / "phase1_task_headroom_candidates.jsonl",
        ROOT / "data" / "jlens_feasibility_prompts.jsonl",
    ):
        if not other.is_file():
            continue
        for line in other.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            for key in ("text", "prompt", "question"):
                value = record.get(key)
                if isinstance(value, str):
                    assert value.strip().lower() not in corpus_texts


def test_corpus_carries_no_labels_and_no_forbidden_cue() -> None:
    for line in CORPUS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        assert set(record) == {"id", "role", "text"}
        lowered = f"{record['id']} {record['text']}".lower()
        for cue in sat.FORBIDDEN_CORPUS_CUES:
            assert cue not in lowered


def test_corpus_loader_rejects_a_short_or_mislabelled_record(tmp_path: Path) -> None:
    lines = CORPUS_PATH.read_text(encoding="utf-8").splitlines()
    broken = tmp_path / "broken.jsonl"
    broken.write_bytes(
        ("\n".join(lines[:-1] + ['{"id":"x","role":"fit","text":"too short"}']) + "\n").encode(
            "utf-8"
        )
    )
    with pytest.raises(sat.CorpusValidationError):
        sat.load_saturation_corpus(broken)


# ---------------------------------------------------------------------------
# fit plan
# ---------------------------------------------------------------------------


def test_fit_plan_sizes_match_the_registered_design(plan: dict) -> None:
    assert plan["fit_a"]["prompt_count"] == sat.FIT_A_PROMPTS
    assert [shard["prompt_count"] for shard in plan["fit_b_shards"]] == list(
        sat.FIT_B_SHARDS
    )
    assert plan["control_direct"]["prompt_count"] == sat.CONTROL_SUBSET_SIZE
    assert [shard["prompt_count"] for shard in plan["control_shards"]] == list(
        sat.CONTROL_SUBSET_SHARDS
    )
    assert plan["heldout"]["prompt_count"] == sat.HELDOUT_PROMPTS
    assert plan["source_layers"] == [6, 13, 20]
    assert plan["target_layer"] == 27


def test_fit_plan_heldout_is_disjoint_from_every_fit_set(plan: dict) -> None:
    heldout = set(plan["heldout"]["prompt_ids"])
    fitted = set(plan["fit_a"]["prompt_ids"])
    for shard in plan["fit_b_shards"] + plan["control_shards"]:
        fitted |= set(shard["prompt_ids"])
    fitted |= set(plan["control_direct"]["prompt_ids"])
    assert heldout & fitted == set()
    assert len(fitted) == sat.FIT_B_PROMPTS


def test_fit_plan_shards_partition_the_25_prompt_set(plan: dict) -> None:
    collected: list[str] = []
    for shard in plan["fit_b_shards"]:
        collected.extend(shard["prompt_ids"])
    assert collected == plan["fit_b_prompt_ids"]
    assert plan["fit_a"]["prompt_ids"] == plan["fit_b_shards"][0]["prompt_ids"]
    assert plan["control_direct"]["prompt_ids"] == plan["fit_b_shards"][2]["prompt_ids"]
    control: list[str] = []
    for shard in plan["control_shards"]:
        control.extend(shard["prompt_ids"])
    assert control == plan["control_direct"]["prompt_ids"]


# ---------------------------------------------------------------------------
# pure math
# ---------------------------------------------------------------------------


def test_relative_frobenius_and_cosine_edges() -> None:
    assert sat.relative_frobenius(0.0, 0.0) == 0.0
    assert sat.relative_frobenius(1.0, 4.0) == pytest.approx(0.25)
    assert sat.cosine_from_flat(0.0, 0.0, 0.0) == 0.0
    assert sat.cosine_from_flat(4.0, 2.0, 2.0) == pytest.approx(1.0)
    assert sat.vector_cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert sat.mean([]) is None
    assert sat.mean([1.0, 3.0]) == pytest.approx(2.0)


def test_top_k_is_deterministic_on_ties() -> None:
    values = [1.0, 1.0, 1.0, 0.5]
    assert sat.top_k_indices(values, 2) == [0, 1]
    assert sat.top_k_indices(values, 99) == [0, 1, 2, 3]
    overlap = sat.top_k_overlap([0, 1, 2], [1, 2, 3])
    assert overlap["overlap"] == 2
    assert overlap["fraction"] == pytest.approx(2 / 3)
    assert overlap["jaccard"] == pytest.approx(0.5)
    assert overlap["interpretation"] == "technical_stability_only_no_semantic_claim"
    with pytest.raises(sat.SaturationValidationError):
        sat.top_k_indices(values, 0)


def test_spearman_handles_ties_and_constants() -> None:
    assert sat.spearman_correlation([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == pytest.approx(1.0)
    assert sat.spearman_correlation([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == pytest.approx(-1.0)
    assert sat.spearman_correlation([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) == 0.0
    assert sat.spearman_correlation([1.0, 1.0, 2.0], [1.0, 1.0, 2.0]) == pytest.approx(1.0)


def test_compare_logit_vectors_reports_stability_only() -> None:
    left = [float(index) for index in range(64)]
    right = list(left)
    right[0] = 999.0
    comparison = sat.compare_logit_vectors(left, right)
    assert comparison["interpretation"] == "technical_stability_only_no_semantic_claim"
    assert comparison["top_k"]["fraction"] <= 1.0
    assert comparison["rank_correlation"] <= 1.0
    assert comparison["top1_match"] is False


def test_pure_lens_math_matches_torch_lens_math() -> None:
    torch = pytest.importorskip("torch")
    pure = sat.PureLensMath()
    backend = sat.TorchLensMath(torch)
    left = [[1.0, 2.0], [3.0, 4.0]]
    right = [[1.5, 2.0], [2.5, 4.5]]
    left_tensor = torch.tensor(left, dtype=torch.float64)
    right_tensor = torch.tensor(right, dtype=torch.float64)
    assert pure.matrix_stats(left)["norm"] == pytest.approx(
        backend.matrix_stats(left_tensor)["norm"]
    )
    assert pure.matrix_difference(left, right)["max_abs"] == pytest.approx(
        backend.matrix_difference(left_tensor, right_tensor)["max_abs"]
    )
    assert pure.matrix_flat_dot(left, right) == pytest.approx(
        backend.matrix_flat_dot(left_tensor, right_tensor)
    )
    pure_mean = pure.matrix_weighted_mean([(left, 3), (right, 2)])
    torch_mean = backend.matrix_weighted_mean([(left_tensor, 3), (right_tensor, 2)])
    flat_pure = [value for row in pure_mean for value in row]
    flat_torch = [value for row in torch_mean.tolist() for value in row]
    assert flat_pure == pytest.approx(flat_torch, rel=1e-6)
    assert pure.matrices_equal(left, left) is True
    assert pure.matrices_equal(left, right) is False


def test_pure_lens_math_reports_non_finite_matrices() -> None:
    stats = sat.PureLensMath().matrix_stats([[float("nan"), 1.0]])
    assert stats["finite"] is False


# ---------------------------------------------------------------------------
# criteria and decision rules
# ---------------------------------------------------------------------------


def _stable_values() -> dict[str, float]:
    return {
        "matrix_finite_rate": 1.0,
        "lens_save_load_max_abs": 0.0,
        "shard_merge_vs_direct_max_abs": 1e-9,
        "shard_merge_vs_direct_relative_frobenius": 1e-12,
        "apply_save_load_consistency": 1.0,
        "convergence_relative_frobenius_10_vs_25": 0.05,
        "convergence_cosine_10_vs_25": 0.999,
        "heldout_topk_overlap_mean": 0.9,
        "heldout_rank_correlation_mean": 0.97,
    }


def _all_success() -> dict[str, dict[str, str]]:
    return {stage: {"status": "success"} for stage in sat.STAGES}


def test_criteria_families_are_registered() -> None:
    assert set(sat.STABILITY_CRITERIA) | set(sat.CONVERGENCE_CRITERIA) == set(sat.CRITERIA)
    assert sat.PRIMARY_METRIC in sat.CRITERIA
    with pytest.raises(sat.SaturationValidationError):
        sat.evaluate_criterion("not_registered", 1.0)


def test_decision_engineering_stable() -> None:
    decision = sat.evaluate_decision(_stable_values(), stages=_all_success())
    assert decision["status"] == "PASS"
    assert decision["decision"] == "ENGINEERING_STABLE"
    assert decision["criteria_failed"] == []
    assert decision["criteria_not_applicable"] == []


def test_decision_engineering_improving_when_only_convergence_fails() -> None:
    values = _stable_values()
    values["convergence_relative_frobenius_10_vs_25"] = 0.42
    decision = sat.evaluate_decision(values, stages=_all_success())
    assert decision["status"] == "COMPLETE"
    assert decision["decision"] == "ENGINEERING_IMPROVING"
    assert "convergence_relative_frobenius_10_vs_25" in decision["criteria_failed"]


def test_decision_engineering_unstable_when_stability_fails() -> None:
    values = _stable_values()
    values["lens_save_load_max_abs"] = 1.0
    decision = sat.evaluate_decision(values, stages=_all_success())
    assert decision["status"] == "FAIL"
    assert decision["decision"] == "ENGINEERING_UNSTABLE"


def test_decision_inconclusive_for_self_test_and_for_missing_metrics() -> None:
    self_test = sat.evaluate_decision(
        _stable_values(), stages=_all_success(), self_test=True
    )
    assert self_test["status"] == "INCONCLUSIVE"
    assert self_test["decision"] == "INCONCLUSIVE"
    values = _stable_values()
    values.pop("heldout_topk_overlap_mean")
    partial = sat.evaluate_decision(values, stages=_all_success())
    assert partial["status"] == "INCONCLUSIVE"
    assert partial["criteria_not_applicable"][0]["criterion"] == "heldout_topk_overlap_mean"


def test_decision_blocked_reports_inconclusive() -> None:
    decision = sat.evaluate_decision(
        _stable_values(), stages=_all_success(), blocked_reason="watchdog fired"
    )
    assert decision["status"] == "BLOCKED"
    assert decision["decision"] == "INCONCLUSIVE"
    assert "watchdog fired" in decision["scientific_interpretation"]


def test_non_finite_metric_fails_its_criterion() -> None:
    evaluation = sat.evaluate_criterion("convergence_cosine_10_vs_25", float("nan"))
    assert evaluation["passed"] is False


def test_every_decision_carries_the_prohibited_interpretations() -> None:
    decision = sat.evaluate_decision(_stable_values(), stages=_all_success())
    assert decision["prohibited_interpretations"] == list(sat.PROHIBITED_INTERPRETATIONS)
    assert "workspace found" in decision["prohibited_interpretations"]
    assert decision["next_gate"] == sat.NEXT_GATE


# ---------------------------------------------------------------------------
# artifact pack
# ---------------------------------------------------------------------------


def _minimal_pack(directory: Path) -> dict:
    decision = sat.evaluate_decision(_stable_values(), stages=_all_success())
    snapshot = sat.build_protocol_snapshot(sample_size={"corpus_prompts": 50})
    manifest = sat.build_stage_manifest(
        run_id="UNITTEST",
        status=decision["status"],
        start_time_utc="2026-01-01T00:00:00Z",
        end_time_utc="2026-01-01T00:01:00Z",
        code_commit=None,
        image_digest=None,
        hardware={"platform": "test"},
        inputs={"corpus_path": "data/jlens_saturation_prompts.jsonl"},
        protocol_hash=base.sha256_bytes(base.canonical_json_bytes(snapshot)),
    )
    summary = sat.render_summary_markdown(
        {"run_id": "UNITTEST", "decision": decision, "stages": {}}
    )
    return sat.write_artifact_pack(
        directory,
        run_id="UNITTEST",
        stage_manifest=manifest,
        protocol_snapshot=snapshot,
        records=[],
        metrics=[],
        decision=decision,
        summary_markdown=summary,
        paper_rows=[],
        figure_rows=[],
        generated_at_utc="2026-01-01T00:01:00Z",
    )


def test_empty_inputs_still_produce_a_valid_not_applicable_pack(tmp_path: Path) -> None:
    _minimal_pack(tmp_path)
    report = sat.validate_artifact_pack(tmp_path)
    assert report["records"] == 1
    record = sat.read_records(tmp_path)[0]
    assert record["status"] == "not_applicable"
    assert record["evaluation"]["reason"]
    with (tmp_path / "03_metrics.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["not_applicable_reason"]
    for name in ("06_paper_table.csv", "07_figure_data.csv"):
        with (tmp_path / name).open(encoding="utf-8", newline="") as handle:
            table = list(csv.DictReader(handle))
        assert table[0]["status"] == "not_applicable"
        assert table[0]["not_applicable_reason"]
    deviations = json.loads((tmp_path / "08_deviations.json").read_text(encoding="utf-8"))
    assert deviations == sat.empty_deviations()


def test_validate_rejects_an_extra_file(tmp_path: Path) -> None:
    _minimal_pack(tmp_path)
    (tmp_path / "99_extra.json").write_bytes(b"{}\n")
    with pytest.raises(sat.ArtifactValidationError):
        sat.validate_artifact_pack(tmp_path)


def test_validate_rejects_a_stale_manifest(tmp_path: Path) -> None:
    _minimal_pack(tmp_path)
    (tmp_path / "05_summary.md").write_bytes(b"# Summary\n")
    with pytest.raises(sat.ArtifactValidationError):
        sat.validate_artifact_pack(tmp_path)


def test_validate_rejects_out_of_order_summary_sections(tmp_path: Path) -> None:
    decision = sat.evaluate_decision(_stable_values(), stages=_all_success())
    summary = sat.render_summary_markdown(
        {"run_id": "UNITTEST", "decision": decision, "stages": {}}
    )
    scrambled = summary.replace("## Objective", "## Zzz", 1)
    snapshot = sat.build_protocol_snapshot(sample_size={"corpus_prompts": 50})
    sat.write_artifact_pack(
        tmp_path,
        run_id="UNITTEST",
        stage_manifest=sat.build_stage_manifest(
            run_id="UNITTEST",
            status=decision["status"],
            start_time_utc="2026-01-01T00:00:00Z",
            end_time_utc="2026-01-01T00:01:00Z",
            code_commit=None,
            image_digest=None,
            hardware={},
            inputs={},
            protocol_hash="0" * 64,
        ),
        protocol_snapshot=snapshot,
        records=[],
        metrics=[],
        decision=decision,
        summary_markdown=scrambled,
        paper_rows=[],
        figure_rows=[],
    )
    with pytest.raises(sat.ArtifactValidationError):
        sat.validate_artifact_pack(tmp_path)


def test_make_record_rejects_an_unregistered_condition() -> None:
    with pytest.raises(sat.ArtifactValidationError):
        sat.make_record(
            record_id="x",
            run_id="UNITTEST",
            source_item_id="x",
            condition="not_a_condition",
            status="success",
            input_payload={},
            evaluation={},
        )


def test_empty_deviations_document_has_the_registered_shape() -> None:
    assert sat.empty_deviations() == {
        "deviations": [],
        "unregistered_changes": [],
        "effect_on_interpretation": "none",
    }


# ---------------------------------------------------------------------------
# self-test end-to-end
# ---------------------------------------------------------------------------


def test_self_test_writes_exactly_the_registered_files(self_test_pack: Path) -> None:
    present = sorted(path.name for path in self_test_pack.iterdir() if path.is_file())
    assert present == sorted(sat.ARTIFACT_FILENAMES)
    assert not [path for path in self_test_pack.iterdir() if path.is_dir()]
    report = sat.validate_artifact_pack(self_test_pack)
    assert report["manifest_written_last"] is True


def test_self_test_manifest_is_written_last(self_test_pack: Path) -> None:
    manifest_mtime = (self_test_pack / sat.MANIFEST_FILENAME).stat().st_mtime_ns
    for name in sat.ARTIFACT_FILENAMES:
        if name == sat.MANIFEST_FILENAME:
            continue
        assert (self_test_pack / name).stat().st_mtime_ns <= manifest_mtime
    manifest = json.loads(
        (self_test_pack / sat.MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    assert manifest["manifest_written_last"] is True
    assert sorted(entry["path"] for entry in manifest["artifacts"]) == sorted(
        name for name in sat.ARTIFACT_FILENAMES if name != sat.MANIFEST_FILENAME
    )


def test_self_test_ran_every_stage_on_the_synthetic_backend(self_test_pack: Path) -> None:
    manifest = json.loads(
        (self_test_pack / "00_stage_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["phase"] == "phase05-jlens-saturation"
    assert manifest["track"] == "track-a"
    assert manifest["errors"] == []
    assert {name: item["status"] for name, item in manifest["stages"].items()} == {
        stage: "success" for stage in sat.STAGES
    }
    assert manifest["inputs"]["backend"] == "self_test"
    assert manifest["inputs"]["mode"] == "self_test"
    assert manifest["inputs"]["dim_batch"] == sat.DEFAULT_DIM_BATCH
    assert manifest["inputs"]["corpus_file_sha256"] == CORPUS_SHA256
    assert manifest["model_revision"] == base.MODEL_REVISION
    assert manifest["output_files"] == list(sat.ARTIFACT_FILENAMES)


def test_self_test_decision_is_forced_inconclusive(self_test_pack: Path) -> None:
    decision = json.loads(
        (self_test_pack / "04_decision.json").read_text(encoding="utf-8")
    )
    assert decision["status"] == "INCONCLUSIVE"
    assert decision["decision"] == "INCONCLUSIVE"
    assert decision["decision"] in sat.DECISIONS
    assert "synthetic self-test backend" in decision["scientific_interpretation"]
    for field in sat.DECISION_FIELDS:
        assert field in decision


def test_self_test_stability_controls_are_exact(self_test_pack: Path) -> None:
    with (self_test_pack / "03_metrics.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert tuple(reader.fieldnames or ()) == sat.METRICS_COLUMNS
        rows = list(reader)
    by_metric = {}
    for row in rows:
        by_metric.setdefault(row["metric"], []).append(row)
    assert float(by_metric["matrix_finite_rate"][0]["value"]) == 1.0
    assert float(by_metric["lens_save_load_max_abs"][0]["value"]) == 0.0
    assert float(by_metric["apply_save_load_consistency"][0]["value"]) == 1.0
    assert (
        float(by_metric["shard_merge_vs_direct_max_abs"][0]["value"])
        <= sat.MERGE_MAX_ABS_TOLERANCE
    )
    assert "heldout_topk_overlap_mean" in by_metric
    assert "heldout_rank_correlation_mean" in by_metric
    assert "fit_wall_clock_seconds_per_prompt" in by_metric


def test_self_test_records_carry_every_required_field(self_test_pack: Path) -> None:
    records = sat.read_records(self_test_pack)
    assert records
    conditions = set()
    for record in records:
        for field in sat.RECORD_FIELDS:
            assert field in record
        assert record["phase"] == sat.PHASE
        assert record["track"] == sat.TRACK
        assert record["condition"] in sat.CONDITIONS
        conditions.add(record["condition"])
    assert {
        "corpus_registration",
        "fit_a_direct",
        "fit_b_shard_1",
        "fit_b_shard_2",
        "fit_b_shard_3",
        "fit_b_merged",
        "control_shard_1",
        "control_shard_2",
        "shard_merge_vs_direct",
        "convergence_10_vs_25",
        "heldout_apply",
    } <= conditions
    heldout = [item for item in records if item["condition"] == "heldout_apply"]
    assert len(heldout) == sat.HELDOUT_PROMPTS
    for item in heldout:
        assert (
            item["evaluation"]["interpretation"]
            == "technical_stability_only_no_semantic_claim"
        )


def test_self_test_paper_and_figure_tables_have_registered_headers(
    self_test_pack: Path,
) -> None:
    for name, columns in (
        ("06_paper_table.csv", sat.PAPER_TABLE_COLUMNS),
        ("07_figure_data.csv", sat.FIGURE_DATA_COLUMNS),
    ):
        with (self_test_pack / name).open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            assert tuple(reader.fieldnames or ()) == columns
            rows = list(reader)
        assert rows
        assert all(row["run_id"] == "TESTRUN0001" for row in rows)
    with (self_test_pack / "07_figure_data.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        figures = {row["figure_id"] for row in csv.DictReader(handle)}
    assert {"fig_fit_cost", "fig_convergence", "fig_heldout_apply_stability"} <= figures


def test_self_test_protocol_snapshot_is_preregistered(self_test_pack: Path) -> None:
    snapshot = json.loads(
        (self_test_pack / "01_protocol_snapshot.json").read_text(encoding="utf-8")
    )
    for field in sat.PROTOCOL_SNAPSHOT_FIELDS:
        assert field in snapshot
    assert snapshot["primary_metric"] == sat.PRIMARY_METRIC
    assert snapshot["seeds"] == sat.SEEDS
    assert snapshot["sample_size"]["fit_b_shards"] == list(sat.FIT_B_SHARDS)
    assert snapshot["decision_rules"]["decisions"] == list(sat.DECISIONS)
    assert snapshot["scientific_claim_boundary"] == sat.SCIENTIFIC_CLAIM_BOUNDARY


def test_self_test_deviations_document_exists_and_is_empty(self_test_pack: Path) -> None:
    deviations = json.loads(
        (self_test_pack / "08_deviations.json").read_text(encoding="utf-8")
    )
    assert deviations["deviations"] == []
    assert deviations["unregistered_changes"] == []
    assert deviations["effect_on_interpretation"] == "none"


def test_self_test_summary_sections_are_present_and_ordered(self_test_pack: Path) -> None:
    summary = (self_test_pack / "05_summary.md").read_text(encoding="utf-8")
    position = -1
    for section in sat.SUMMARY_SECTIONS:
        found = summary.find(f"{section}\n")
        assert found > position, section
        position = found
    assert "technical stability" in summary.lower()


def _summary_sections(summary: str) -> dict[str, str]:
    offsets = [(summary.find(f"{name}\n"), name) for name in sat.SUMMARY_SECTIONS]
    sections = {}
    for index, (start, name) in enumerate(offsets):
        end = offsets[index + 1][0] if index + 1 < len(offsets) else len(summary)
        sections[name] = summary[start:end]
    return sections


def test_no_artifact_asserts_a_prohibited_claim(self_test_pack: Path) -> None:
    summary = (self_test_pack / "05_summary.md").read_text(encoding="utf-8")
    sections = _summary_sections(summary)
    allowed = {"## Scope", "## Scientific interpretation"}
    for phrase in (
        "workspace found",
        "hidden reasoning",
        "invisible chain-of-thought",
        "internal workspace",
        "J-space validated",
    ):
        assert phrase in sections["## Scientific interpretation"]
        for name, body in sections.items():
            if name not in allowed:
                assert phrase not in body, f"{phrase} leaked into {name}"
    for name in ("02_records.jsonl", "03_metrics.csv", "06_paper_table.csv"):
        text = (self_test_pack / name).read_text(encoding="utf-8").lower()
        assert "workspace" not in text
        assert "hidden reasoning" not in text


def test_files_use_lf_newlines(self_test_pack: Path) -> None:
    for name in sat.ARTIFACT_FILENAMES:
        assert b"\r" not in (self_test_pack / name).read_bytes(), name


# ---------------------------------------------------------------------------
# runner wiring
# ---------------------------------------------------------------------------


def test_self_test_backend_merge_reproduces_a_direct_fit() -> None:
    backend = sat.SelfTestBackend()
    prompts = [f"prompt number {index} about a routine procedure" for index in range(5)]
    direct = backend.fit(prompts)
    shards = [backend.fit(prompts[:3]), backend.fit(prompts[3:])]
    merged = backend.merge(shards)
    assert merged.n_prompts == direct.n_prompts
    comparison = sat.compare_lens_matrices(
        backend.math,
        {layer: merged.jacobians[layer] for layer in backend.source_layers},
        {layer: direct.jacobians[layer] for layer in backend.source_layers},
        source_layers=backend.source_layers,
    )
    assert comparison["max_abs"] <= sat.MERGE_MAX_ABS_TOLERANCE


def test_self_test_backend_save_load_is_exact(tmp_path: Path) -> None:
    backend = sat.SelfTestBackend()
    lens = backend.fit(["a routine calibration procedure is documented and reviewed"])
    reloaded, audit = backend.save_lens(lens, tmp_path / "lens.json")
    assert audit["torch_equal_all_layers"] is True
    assert max(audit["exact_max_abs"].values()) == 0.0
    assert reloaded.jacobians == lens.jacobians
    assert audit["lens_save_dtype"] == sat.LENS_SERIALIZATION_DTYPE


def test_runner_rejects_an_unregistered_dim_batch(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        runner.parse_args(["--dim-batch", "3", "--output-dir", str(tmp_path)])


def test_runner_records_a_deviation_when_dim_batch_is_raised(tmp_path: Path) -> None:
    args = runner.parse_args(
        [
            "--self-test",
            "--dim-batch",
            "2",
            "--run-id",
            "DIMBATCH2",
            "--output-dir",
            str(tmp_path),
        ]
    )
    instance = runner.SaturationRunner(args)
    assert instance.deviations[0]["id"] == "dim-batch-raised"
    assert instance.deviations[0]["effect_on_interpretation"] == "none"
    assert "F2" in instance.deviations[0]["justification"]


def test_runner_uses_the_registered_layers_and_shards(tmp_path: Path) -> None:
    args = runner.parse_args(
        ["--self-test", "--run-id", "LAYERS", "--output-dir", str(tmp_path)]
    )
    instance = runner.SaturationRunner(args)
    assert instance.plan["source_layers"] == [6, 13, 20]
    assert instance.plan["target_layer"] == 27
    assert instance.backend.is_synthetic is True
    assert instance.blob is None
    assert instance.pack_dir.name == "LAYERS"
    assert instance.work_dir.name == "LAYERS-work"
    assert instance.work_dir.parent == instance.pack_dir.parent


def test_runner_time_admission_uses_the_registered_budget(tmp_path: Path) -> None:
    args = runner.parse_args(
        ["--self-test", "--run-id", "BUDGET", "--output-dir", str(tmp_path)]
    )
    instance = runner.SaturationRunner(args)
    admission = instance.time_admission("S2_fit_a10", sat.FIT_A_PROMPTS)
    assert admission["admitted"] is True
    assert admission["planning_boundary_seconds"] == base.PLANNING_BUDGET_SECONDS
    assert admission["prompts"] == sat.FIT_A_PROMPTS


def test_runner_marks_a_downstream_stage_blocked_when_a_predecessor_fails(
    tmp_path: Path,
) -> None:
    args = runner.parse_args(
        ["--self-test", "--run-id", "BLOCKED", "--output-dir", str(tmp_path)]
    )
    instance = runner.SaturationRunner(args)

    def explode() -> dict:
        raise RuntimeError("synthetic stage failure")

    assert instance.execute("S0_environment", explode) is False
    assert instance.stages["S0_environment"]["status"] == "failed"
    assert instance.execute("S1_model", lambda: {}) is False
    assert instance.stages["S1_model"]["status"] == "blocked"
    assert instance.errors[0]["stage"] == "S0_environment"


def test_runner_self_test_never_configures_blob_transport(tmp_path: Path) -> None:
    args = runner.parse_args(
        ["--dry-run", "--run-id", "NOBLOB", "--output-dir", str(tmp_path)]
    )
    instance = runner.SaturationRunner(args)
    assert instance.self_test is True
    assert instance.upload() == {"status": "not_configured", "uploaded": 0}


def test_saturation_blob_transport_sorts_the_manifest_last(tmp_path: Path) -> None:
    for name in sat.ARTIFACT_FILENAMES:
        (tmp_path / name).write_bytes(b"{}\n")
    ordered = runner.SaturationBlobTransport.snapshot_files(tmp_path)
    assert ordered[-1].name == sat.MANIFEST_FILENAME


def test_runner_reuses_the_pinned_phase05a_parameters() -> None:
    assert sat.MODEL_ID == base.MODEL_ID
    assert sat.MODEL_REVISION == base.MODEL_REVISION
    assert sat.MAX_SEQ_LEN == base.MAX_SEQ_LEN
    assert sat.SKIP_FIRST == base.SKIP_FIRST
    assert sat.OFFICIAL_COMMIT == base.OFFICIAL_COMMIT
    assert sat.RUNTIME_DTYPE == base.RUNTIME_DTYPE
    assert sat.LENS_SERIALIZATION_DTYPE == "float32"
    assert sat.DEFAULT_DIM_BATCH == 1


def test_protocol_and_run_documents_are_registered() -> None:
    for name in (
        "phase05_jlens_saturation_protocol.md",
        "phase05_jlens_saturation_run.md",
    ):
        path = ROOT / "docs" / name
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "581d398613e5602a5af361e1c34d3a92ea82ba8e" in text
        assert "workspace found" in text


def test_container_image_ships_the_saturation_inputs() -> None:
    dockerfile = (ROOT / "Dockerfile.jlens").read_text(encoding="utf-8")
    assert "COPY scripts/phase05_jlens_saturation.py /workspace/scripts/" in dockerfile
    assert (
        "COPY src/jspace_observation/phase05_jlens_saturation.py "
        "/workspace/src/jspace_observation/" in dockerfile
    )
    assert "COPY data/jlens_saturation_prompts.jsonl /workspace/data/" in dockerfile
