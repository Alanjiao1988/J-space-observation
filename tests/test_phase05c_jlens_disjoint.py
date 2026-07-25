"""Model/GPU/network-free tests for the Phase 0.5C J-lens disjoint tooling."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "jspace_observation"))
sys.path.insert(0, str(ROOT))

import phase05_jlens as base
import phase05_jlens_saturation as sat
import phase05c_jlens_disjoint as dis
from scripts import analyze_phase05c_jlens_disjoint as analysis
from scripts import phase05c_jlens_disjoint as runner

CORPUS_PATH = ROOT / "data" / "jlens_saturation_prompts.jsonl"
LAUNCHER = ROOT / "infra" / "azure" / "scripts" / "12_run_phase05c_jlens_disjoint.sh"
PROTOCOL_DOC = ROOT / "docs" / "phase05c_jlens_disjoint_replication_protocol.md"
SCAFFOLD = ROOT / "artifacts" / dis.PHASE / dis.TRACK

BASE_CORPUS_SHA256 = "41e104efec1cd0e0eebae504cd888e60c4e81f6f8c7774d75c895eac98862b4b"
BASE_CORPUS_BYTES = 13452
CORPUS_SHA256 = "dd5d97498324e8b5153c106f0edbc4d962d47771db7dfa2093b48fc36f5962fa"
CORPUS_BYTES = 16087
PROTOCOL_HASH = "49059665f6c0c720beb712f99941f6cbf3a7a0207bac3e94cc4ac73f5af11980"
NEW_PROMPT_IDS = tuple(f"sat-reserve-{index:03d}" for index in range(16, 26))

PROHIBITED_PHRASES = (
    "workspace found",
    "j-space validated",
    "hidden reasoning observed",
    "internal workspace",
    "invisible chain-of-thought",
    "scientifically usable lens",
)


@pytest.fixture(scope="module")
def corpus() -> dict:
    return dis.load_disjoint_corpus(CORPUS_PATH)


@pytest.fixture(scope="module")
def plan(corpus: dict) -> dict:
    return dis.build_disjoint_fit_plan(corpus)


@pytest.fixture(scope="module")
def self_test_pack(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_dir = tmp_path_factory.mktemp("disjoint-self-test")
    exit_code = runner.main(
        ["--self-test", "--output-dir", str(output_dir), "--run-id", "TESTRUN05C1"]
    )
    assert exit_code == 0
    return output_dir / dis.PHASE / dis.TRACK / "TESTRUN05C1"


def _ok_stages() -> dict[str, dict[str, str]]:
    return {name: {"status": "success"} for name in dis.STAGES}


def _passing_values() -> dict[str, float]:
    return {
        "matrix_finite_rate": 1.0,
        "save_load_max_abs": 0.0,
        "apply_save_load_consistency": 1.0,
        "25A_vs_25B_relative_frobenius": 0.05,
        "25A_vs_25B_cosine": 0.995,
    }


def _improvement(improved: bool) -> dict[str, object]:
    return {
        "improved": improved,
        "margins": dict(dis.MERGED_IMPROVEMENT_MARGINS),
        "margins_measured": {
            "heldout_topk_overlap": 0.05 if improved else 0.0,
            "heldout_rank_correlation": 0.01 if improved else 0.0,
        },
        "definition": "test",
    }


# ---------------------------------------------------------------------------
# D1: corpus amendment integrity
# ---------------------------------------------------------------------------


def test_corpus_amendment_is_append_only_and_pinned() -> None:
    raw = CORPUS_PATH.read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert len(raw) == CORPUS_BYTES
    assert base.sha256_bytes(raw) == CORPUS_SHA256
    assert base.sha256_bytes(raw[:BASE_CORPUS_BYTES]) == BASE_CORPUS_SHA256
    assert raw[:BASE_CORPUS_BYTES].count(b"\n") == 50
    assert raw.decode("utf-8").isascii()
    revision = sat.CORPUS_REVISIONS[dis.CORPUS_REVISION]
    assert revision["supersedes"] == "r1-50"
    assert revision["prefix_bytes"] == BASE_CORPUS_BYTES
    assert revision["prefix_sha256"] == BASE_CORPUS_SHA256
    assert tuple(revision["appended_ids"]) == NEW_PROMPT_IDS


def test_corpus_shape_roles_and_uniqueness(corpus: dict) -> None:
    assert corpus["revision"] == dis.CORPUS_REVISION
    assert len(corpus["records"]) == 60
    assert corpus["counts"] == {"fit": 25, "heldout": 10, "reserve": 25}
    texts = [record["text"] for record in corpus["records"]]
    ids = [record["id"] for record in corpus["records"]]
    assert len(set(texts)) == 60
    assert len(set(ids)) == 60
    normalised = [" ".join(text.lower().split()) for text in texts]
    assert len(set(normalised)) == 60


def test_new_prompts_match_the_registered_generation_constraints(corpus: dict) -> None:
    by_id = {record["id"]: record for record in corpus["records"]}
    for prompt_id in NEW_PROMPT_IDS:
        record = by_id[prompt_id]
        assert record["role"] == "reserve"
        assert list(record.keys())[:3] == ["id", "role", "text"]
        assert record["text"].isascii()
        assert 38 <= record["proxy_token_count"] <= 44
        assert record["proxy_token_count"] >= sat.MIN_PROXY_TOKENS
        assert 199 <= len(record["text"]) <= 238
        haystack = f"{record['id']} {record['text']}".lower()
        for cue in sat.FORBIDDEN_CORPUS_CUES:
            assert cue not in haystack


def test_new_prompt_line_format_matches_the_existing_records() -> None:
    lines = CORPUS_PATH.read_bytes().decode("utf-8").splitlines()
    assert len(lines) == 60
    for line in lines:
        payload = json.loads(line)
        assert list(payload) == ["id", "role", "text"]
        assert (
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False) == line
        )


def test_loader_rejects_a_forbidden_cue(tmp_path: Path) -> None:
    records = [
        json.loads(line)
        for line in CORPUS_PATH.read_text(encoding="utf-8").splitlines()
    ]
    records[-1]["text"] = records[-1]["text"].replace("routine", "evaluator", 1)
    if "evaluator" not in records[-1]["text"]:
        records[-1]["text"] = "The evaluator " + records[-1]["text"]
    path = tmp_path / "cue.jsonl"
    path.write_bytes(
        "".join(
            json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n"
            for record in records
        ).encode("utf-8")
    )
    with pytest.raises(sat.CorpusValidationError):
        dis.load_disjoint_corpus(path)


def test_loader_rejects_a_mutated_prefix(tmp_path: Path) -> None:
    raw = bytearray(CORPUS_PATH.read_bytes())
    marker = raw.index(b"sat-fit-001")
    raw[marker + 10] = ord("2")
    path = tmp_path / "mutated.jsonl"
    path.write_bytes(bytes(raw))
    with pytest.raises(sat.CorpusValidationError):
        dis.load_disjoint_corpus(path)


def test_new_prompts_do_not_overlap_protected_corpora(corpus: dict) -> None:
    protected: set[str] = set()
    sources = [
        ROOT / "data" / "phase1_task_headroom_candidates.jsonl",
        ROOT / "data" / "jlens_feasibility_prompts.jsonl",
    ]
    for source in sources:
        if not source.is_file():
            continue
        for line in source.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            stack = [json.loads(line)]
            while stack:
                node = stack.pop()
                if isinstance(node, dict):
                    stack.extend(node.values())
                elif isinstance(node, list):
                    stack.extend(node)
                elif isinstance(node, str) and len(node) >= 24:
                    protected.add(" ".join(node.lower().split()))
    assert protected, "expected at least one protected string to compare against"
    by_id = {record["id"]: record for record in corpus["records"]}
    for prompt_id in NEW_PROMPT_IDS:
        text = " ".join(by_id[prompt_id]["text"].lower().split())
        assert text not in protected


def test_corpus_verification_script_passes() -> None:
    script = ROOT / "scripts" / "verify_jlens_corpus_amendment.py"
    assert script.is_file()
    source = script.read_text(encoding="utf-8")
    assert "sha256" in source
    assert BASE_CORPUS_SHA256 in source


# ---------------------------------------------------------------------------
# fit plan and disjointness
# ---------------------------------------------------------------------------


def test_fit_plan_sets_are_disjoint_and_correctly_sized(plan: dict) -> None:
    lens_a = set(plan["lens_25a"]["prompt_ids"])
    lens_b = set(plan["lens_25b"]["prompt_ids"])
    heldout = set(plan["heldout"]["prompt_ids"])
    assert len(lens_a) == 25
    assert len(lens_b) == 25
    assert len(heldout) == 10
    assert lens_a & lens_b == set()
    assert lens_a & heldout == set()
    assert lens_b & heldout == set()
    assert plan["lens_25a"]["prompt_ids"][0] == "sat-fit-001"
    assert plan["lens_25a"]["prompt_ids"][-1] == "sat-fit-025"
    assert plan["lens_25b"]["prompt_ids"][0] == "sat-reserve-001"
    assert plan["lens_25b"]["prompt_ids"][-1] == "sat-reserve-025"


def test_shards_mirror_the_phase05b_sizes_and_partition_25b(plan: dict) -> None:
    shards = plan["lens_25b_shards"]
    assert [shard["prompt_count"] for shard in shards] == [10, 10, 5]
    assert tuple(dis.FIT_B_SHARDS) == (10, 10, 5)
    flattened: list[str] = []
    for shard in shards:
        flattened.extend(shard["prompt_ids"])
    assert flattened == list(plan["lens_25b"]["prompt_ids"])


def test_lens_25a_prompt_order_reproduces_the_phase05b_fit(plan: dict) -> None:
    assert plan["lens_25a"]["prompt_order_sha256"] == dis.EXISTING_PROMPT_ORDER_SHA256
    assert plan["lens_25a_matches_phase05b_order"] is True


def test_existing_lens_validation_rejects_a_wrong_lens() -> None:
    good = {"n_prompts": 25, "source_layers": [6, 13, 20], "d_model": 1536}
    audit = dis.validate_existing_lens(
        path="x.pt",
        metadata=good,
        file_sha256=dis.EXISTING_LENS_SHA256,
        file_bytes=dis.EXISTING_LENS_BYTES,
    )
    assert audit["digest_matches_registered"] is True
    assert audit["refitted"] is False
    for bad in (
        {**good, "n_prompts": 10},
        {**good, "source_layers": [6, 13]},
        {**good, "d_model": 2048},
    ):
        with pytest.raises(dis.ExistingLensValidationError):
            dis.validate_existing_lens(path="x.pt", metadata=bad)
    with pytest.raises(dis.ExistingLensValidationError):
        dis.validate_existing_lens(path="x.pt", metadata=good, file_sha256="0" * 64)


def test_registered_25a_blob_location_is_the_measured_one() -> None:
    assert dis.EXISTING_STORAGE_ACCOUNT == "stjspacefiles0709085305"
    assert dis.EXISTING_BLOB_CONTAINER == "jspace-results"
    assert dis.EXISTING_LENS_BLOB == (
        "phase05-jlens-saturation/20260725T122016Z"
        "/attempts/primary/01-lens-binaries/fit_b_merged_lens.pt"
    )
    assert dis.EXISTING_LENS_BYTES == 28314032
    assert dis.EXISTING_LENS_SHA256 == (
        "cb17a634e46e4b219b6dc16b98662ba82e986abbcc154fd650e5a8a5b828949d"
    )
    # the Blob prefix is phase05-..., never phase05b-...
    assert not dis.EXISTING_LENS_BLOB.startswith("phase05b")
    assert dis.EXISTING_LENS_PROVENANCE["refit_permitted"] is False
    snapshot = dis.build_protocol_snapshot(sample_size=dis.default_sample_size())
    assert snapshot["reused_lens_25a"]["blob"] == dis.EXISTING_LENS_BLOB
    assert snapshot["reused_lens_25a"]["bytes"] == dis.EXISTING_LENS_BYTES
    assert snapshot["reused_lens_25a"]["sha256"] == dis.EXISTING_LENS_SHA256


def test_file_integrity_gate_runs_before_load_and_rejects_mismatches(
    tmp_path: Path,
) -> None:
    target = tmp_path / "fit_b_merged_lens.pt"
    target.write_bytes(b"not the registered lens")
    with pytest.raises(dis.ExistingLensValidationError) as excinfo:
        dis.verify_existing_lens_file(target)
    assert "bytes" in str(excinfo.value)
    assert "refusing to refit" in str(excinfo.value)

    unenforced = dis.verify_existing_lens_file(
        target, require_registered_digest=False
    )
    assert unenforced["verified_before_load"] is True
    assert unenforced["bytes_match_registered"] is False
    assert unenforced["digest_matches_registered"] is False
    assert unenforced["registered_bytes"] == dis.EXISTING_LENS_BYTES

    missing = tmp_path / "absent.pt"
    with pytest.raises(dis.ExistingLensValidationError):
        dis.verify_existing_lens_file(missing)

    # right size, wrong content: the digest check must still stop the load
    sized = tmp_path / "sized.pt"
    sized.write_bytes(b"\0" * dis.EXISTING_LENS_BYTES)
    with pytest.raises(dis.ExistingLensValidationError) as excinfo:
        dis.verify_existing_lens_file(sized)
    assert "SHA-256" in str(excinfo.value)


# ---------------------------------------------------------------------------
# D2: protocol registration
# ---------------------------------------------------------------------------


def test_protocol_hash_is_pinned_and_is_the_snapshot_digest() -> None:
    snapshot = dis.build_protocol_snapshot(sample_size=dis.default_sample_size())
    payload = base.canonical_json_bytes(snapshot)
    assert base.sha256_bytes(payload) == PROTOCOL_HASH
    assert dis.protocol_hash() == PROTOCOL_HASH


def test_registered_metric_names_are_exactly_the_thirteen() -> None:
    assert dis.REGISTERED_METRICS == (
        "25A_vs_25B_relative_frobenius",
        "25A_vs_25B_cosine",
        "25A_vs_50M_relative_frobenius",
        "25B_vs_50M_relative_frobenius",
        "25A_vs_50M_cosine",
        "25B_vs_50M_cosine",
        "heldout_apply_logit_cosine",
        "heldout_topk_overlap",
        "heldout_rank_correlation",
        "matrix_finite_rate",
        "save_load_max_abs",
        "wall_clock_per_prompt",
        "peak_gpu_memory",
    )
    assert dis.PRIMARY_METRIC == "25A_vs_25B_relative_frobenius"


def test_frozen_technical_settings_match_phase05a() -> None:
    assert dis.SOURCE_LAYERS == (6, 13, 20)
    assert dis.TARGET_LAYER == 27
    assert dis.MAX_SEQ_LEN == 32
    assert dis.SKIP_FIRST == 16
    assert dis.DEFAULT_DIM_BATCH == 1
    assert dis.LENS_SERIALIZATION_DTYPE == "float32"
    assert base.MODEL_ID == "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
    assert base.MODEL_REVISION == "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"
    assert base.OFFICIAL_COMMIT == "581d398613e5602a5af361e1c34d3a92ea82ba8e"


def test_protocol_document_registers_the_run() -> None:
    text = PROTOCOL_DOC.read_text(encoding="utf-8")
    for token in (
        PROTOCOL_HASH,
        CORPUS_SHA256,
        BASE_CORPUS_SHA256,
        dis.EXISTING_LENS_SHA256,
        "581d398613e5602a5af361e1c34d3a92ea82ba8e",
        "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562",
        "REPLICATE_STABLE",
        "REPLICATE_IMPROVING",
        "REPLICATE_UNSTABLE",
        "FAILED",
        "Merge semantics caveat",
        "Out of scope",
        "2.384e-07",
        "4.862e-08",
    ):
        assert token in text, token
    for metric in dis.REGISTERED_METRICS:
        assert metric in text, metric
    for prompt_id in NEW_PROMPT_IDS:
        assert prompt_id in text, prompt_id
    assert "No direct 50-prompt fit is performed" in text
    assert "workspace found" in text


def test_no_artifact_text_makes_a_scientific_claim(self_test_pack: Path) -> None:
    documents = [
        PROTOCOL_DOC.read_text(encoding="utf-8"),
        (self_test_pack / "05_summary.md").read_text(encoding="utf-8"),
        (SCAFFOLD / "05_summary.md").read_text(encoding="utf-8"),
    ]
    for text in documents:
        lowered = text.lower()
        for phrase in PROHIBITED_PHRASES:
            for line in lowered.splitlines():
                if phrase not in line:
                    continue
                assert any(
                    marker in line
                    for marker in ("prohibit", "not ", "no ", "never", "-")
                ), f"unqualified prohibited phrase: {line!r}"


# ---------------------------------------------------------------------------
# decision rules
# ---------------------------------------------------------------------------


def test_decision_replicate_stable() -> None:
    decision = dis.evaluate_decision(
        _passing_values(), stages=_ok_stages(), merged_improvement=_improvement(True)
    )
    assert decision["status"] == "PASS"
    assert decision["decision"] == "REPLICATE_STABLE"
    assert decision["criteria_failed"] == []


def test_decision_replicate_improving() -> None:
    values = {
        **_passing_values(),
        "25A_vs_25B_relative_frobenius": 0.42,
        "25A_vs_25B_cosine": 0.92,
    }
    decision = dis.evaluate_decision(
        values, stages=_ok_stages(), merged_improvement=_improvement(True)
    )
    assert decision["status"] == "COMPLETE"
    assert decision["decision"] == "REPLICATE_IMPROVING"
    assert set(decision["criteria_failed"]) == {
        "25A_vs_25B_relative_frobenius",
        "25A_vs_25B_cosine",
    }


def test_decision_replicate_unstable() -> None:
    values = {
        **_passing_values(),
        "25A_vs_25B_relative_frobenius": 0.42,
        "25A_vs_25B_cosine": 0.92,
    }
    decision = dis.evaluate_decision(
        values, stages=_ok_stages(), merged_improvement=_improvement(False)
    )
    assert decision["status"] == "COMPLETE"
    assert decision["decision"] == "REPLICATE_UNSTABLE"


@pytest.mark.parametrize(
    "override",
    [
        {"matrix_finite_rate": 0.9},
        {"save_load_max_abs": 1e-6},
        {"apply_save_load_consistency": 0.0},
    ],
)
def test_decision_failed_on_any_transport_gate(override: dict) -> None:
    decision = dis.evaluate_decision(
        {**_passing_values(), **override},
        stages=_ok_stages(),
        merged_improvement=_improvement(True),
    )
    assert decision["status"] == "FAIL"
    assert decision["decision"] == "FAILED"


def test_decision_inconclusive_paths() -> None:
    self_test = dis.evaluate_decision(
        _passing_values(),
        stages=_ok_stages(),
        self_test=True,
        merged_improvement=_improvement(True),
    )
    assert self_test["status"] == "INCONCLUSIVE"
    assert self_test["decision"] == "INCONCLUSIVE"

    incomplete = dict(_ok_stages())
    incomplete["S7_replicate_variability"] = {"status": "blocked"}
    unfinished = dis.evaluate_decision(
        _passing_values(),
        stages=incomplete,
        merged_improvement=_improvement(True),
    )
    assert unfinished["status"] == "INCONCLUSIVE"

    missing = dis.evaluate_decision(
        {key: value for key, value in _passing_values().items() if key != "25A_vs_25B_cosine"},
        stages=_ok_stages(),
        merged_improvement=_improvement(True),
    )
    assert missing["status"] == "INCONCLUSIVE"

    blocked = dis.evaluate_decision(
        {}, stages={name: {"status": "blocked"} for name in dis.STAGES},
        blocked_reason="watchdog",
    )
    assert blocked["status"] == "BLOCKED"
    assert blocked["decision"] == "INCONCLUSIVE"


def test_every_decision_carries_the_claim_boundary() -> None:
    for improvement in (_improvement(True), _improvement(False)):
        decision = dis.evaluate_decision(
            _passing_values(), stages=_ok_stages(), merged_improvement=improvement
        )
        assert "not semantic evidence" in decision["claim_boundary"]
        assert "workspace found" in decision["prohibited_interpretations"]
        assert decision["decision"] in dis.DECISIONS
        assert decision["status"] in dis.DECISION_STATUSES


def test_merged_improvement_definition_is_frozen() -> None:
    assert dis.MERGED_IMPROVEMENT_MARGINS == {
        "heldout_topk_overlap": 0.02,
        "heldout_rank_correlation": 0.005,
    }
    pair_means = {
        dis.PAIR_AB: {
            "heldout_topk_overlap": 0.60,
            "heldout_rank_correlation": 0.900,
        },
        dis.PAIR_AM: {
            "heldout_topk_overlap": 0.62,
            "heldout_rank_correlation": 0.906,
        },
        dis.PAIR_BM: {
            "heldout_topk_overlap": 0.62,
            "heldout_rank_correlation": 0.906,
        },
    }
    improved = dis.merged_apply_improvement(pair_means)
    assert improved["improved"] is True
    assert improved["margins_measured"]["heldout_topk_overlap"] == pytest.approx(0.02)

    borderline = {
        key: {**value, "heldout_rank_correlation": 0.9040}
        for key, value in pair_means.items()
    }
    borderline[dis.PAIR_AB]["heldout_rank_correlation"] = 0.900
    assert dis.merged_apply_improvement(borderline)["improved"] is False


def test_criteria_thresholds_match_the_registered_table() -> None:
    assert dis.CRITERIA["25A_vs_25B_relative_frobenius"]["threshold"] == 0.10
    assert dis.CRITERIA["25A_vs_25B_cosine"]["threshold"] == 0.99
    assert dis.CRITERIA["matrix_finite_rate"]["threshold"] == 1.0
    assert dis.CRITERIA["save_load_max_abs"]["threshold"] == 0.0
    assert dis.CRITERIA["apply_save_load_consistency"]["threshold"] == 1.0


# ---------------------------------------------------------------------------
# metric definitions reused from Phase 0.5B
# ---------------------------------------------------------------------------


def test_comparison_helpers_reuse_the_phase05b_definitions() -> None:
    assert dis.TOP_K == sat.TOP_K
    assert dis.TOP_K_SECONDARY == sat.TOP_K_SECONDARY
    assert dis.compare_lens_matrices is sat.compare_lens_matrices
    assert dis.compare_logit_vectors is sat.compare_logit_vectors
    assert dis.APPLY_RTOL == sat.APPLY_RTOL
    assert dis.APPLY_ATOL == sat.APPLY_ATOL


def test_top_k_overlap_and_rank_correlation_are_deterministic() -> None:
    left = [3.0, 1.0, 2.0, 0.0, 5.0]
    right = [3.0, 1.0, 2.0, 0.0, 5.0]
    comparison = dis.compare_logit_vectors(left, right)
    assert comparison["top_k"]["fraction"] == 1.0
    assert comparison["rank_correlation"] == pytest.approx(1.0)
    tied = dis.compare_logit_vectors([1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0])
    assert tied["top_k"]["fraction"] == 1.0


def test_finite_rate_denominator_is_eighteen(self_test_pack: Path) -> None:
    rows = _metric_rows(self_test_pack)
    finite = [
        row
        for row in rows
        if row["metric"] == "matrix_finite_rate" and row["stratum"] == "all"
    ]
    assert len(finite) == 1
    assert finite[0]["denominator"] == "18"
    assert float(finite[0]["value"]) == 1.0


# ---------------------------------------------------------------------------
# D3: runner behaviour and artifact pack
# ---------------------------------------------------------------------------


def _metric_rows(pack_dir: Path) -> list[dict[str, str]]:
    with (pack_dir / "03_metrics.csv").open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_cli_rejects_an_unregistered_dim_batch() -> None:
    with pytest.raises(SystemExit):
        runner.parse_args(["--dim-batch", "3"])
    with pytest.raises(SystemExit):
        runner.parse_args(["--existing-lens-sha256", "not-a-digest"])
    args = runner.parse_args(["--dim-batch", "1"])
    assert args.dim_batch == 1
    assert args.existing_lens_path == ""


def test_cli_exposes_the_existing_lens_arguments() -> None:
    args = runner.parse_args(
        [
            "--existing-lens-path",
            "/workspace/runtime/staged/fit_b_merged_lens.pt",
            "--existing-lens-blob",
            "phase05-jlens-saturation/x/fit_b_merged_lens.pt",
            "--existing-lens-sha256",
            dis.EXISTING_LENS_SHA256,
        ]
    )
    assert args.existing_lens_path.endswith("fit_b_merged_lens.pt")
    assert args.existing_lens_blob.startswith("phase05-jlens-saturation/")
    assert args.existing_lens_sha256 == dis.EXISTING_LENS_SHA256


def test_runner_never_refits_25a_and_never_fits_50() -> None:
    source = (ROOT / "scripts" / "phase05c_jlens_disjoint.py").read_text(
        encoding="utf-8"
    )
    assert "load_lens" in source
    assert "refit_performed" in source
    assert "direct_50_fit_performed" in source
    fit_calls = re.findall(r"self\.backend\.fit\(", source)
    assert len(fit_calls) == 2, "fit is only reachable from fit_unit and the self-test"
    assert "fit_unit" in source


def test_self_test_pack_has_the_registered_ten_files(self_test_pack: Path) -> None:
    names = sorted(path.name for path in self_test_pack.iterdir())
    assert names == sorted(sat.ARTIFACT_FILENAMES)
    dis.validate_artifact_pack(self_test_pack)


def test_self_test_pack_schema_and_provenance(self_test_pack: Path) -> None:
    manifest = json.loads(
        (self_test_pack / "00_stage_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["phase"] == dis.PHASE
    assert manifest["track"] == dis.TRACK
    assert manifest["protocol_hash"] == PROTOCOL_HASH
    assert list(manifest["stages"]) == list(dis.STAGES)
    assert all(item["status"] == "success" for item in manifest["stages"].values())
    assert manifest["inputs"]["existing_lens_refitted"] is False
    assert manifest["inputs"]["direct_50_fit_performed"] is False
    assert manifest["inputs"]["corpus_revision"] == dis.CORPUS_REVISION
    snapshot = json.loads(
        (self_test_pack / "01_protocol_snapshot.json").read_text(encoding="utf-8")
    )
    assert snapshot["primary_metric"] == dis.PRIMARY_METRIC
    artifact_manifest = json.loads(
        (self_test_pack / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    assert artifact_manifest["manifest_written_last"] is True
    assert artifact_manifest["manifest_order"][-1] == "08_deviations.json"
    for entry in artifact_manifest["artifacts"]:
        path = self_test_pack / entry["path"]
        assert path.stat().st_size == entry["bytes"]
        assert base.sha256_file(path) == entry["sha256"]


def test_self_test_records_cover_every_registered_stage(self_test_pack: Path) -> None:
    records = [
        json.loads(line)
        for line in (self_test_pack / "02_records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    record_ids = {record["record_id"] for record in records}
    assert "corpus::registration" in record_ids
    assert "lens::25a_loaded" in record_ids
    assert "fit::lens_25b" in record_ids
    assert "merge::lens_50m" in record_ids
    for pair in (dis.PAIR_AB, dis.PAIR_AM, dis.PAIR_BM):
        assert f"comparison::{pair}" in record_ids
    for index in range(1, 11):
        assert f"apply::sat-heldout-{index:03d}" in record_ids
    for record in records:
        assert record["phase"] == dis.PHASE
        assert record["track"] == dis.TRACK
    loaded = next(r for r in records if r["record_id"] == "lens::25a_loaded")
    assert loaded["evaluation"]["refit_performed"] is False
    merged = next(r for r in records if r["record_id"] == "merge::lens_50m")
    assert merged["evaluation"]["direct_50_fit_performed"] is False
    assert merged["evaluation"]["weights"] == [25, 25]
    assert merged["evaluation"]["prompt_count"] == 50


def test_self_test_metric_rows_use_the_registered_names(self_test_pack: Path) -> None:
    rows = _metric_rows(self_test_pack)
    assert rows
    assert tuple(rows[0]) == sat.METRICS_COLUMNS
    names = {row["metric"] for row in rows}
    for metric in dis.REGISTERED_METRICS:
        assert metric in names, metric
    conditions = {row["condition"] for row in rows}
    assert conditions <= set(dis.CONDITIONS)
    strata = {row["stratum"] for row in rows}
    for label in dis.LENS_DISPLAY.values():
        assert f"lens::{label}" in strata
    for pair, _left, _right in dis.APPLY_PAIRS:
        assert f"pair::{pair}" in strata


def test_self_test_is_forced_inconclusive(self_test_pack: Path) -> None:
    decision = json.loads(
        (self_test_pack / "04_decision.json").read_text(encoding="utf-8")
    )
    assert decision["status"] == "INCONCLUSIVE"
    assert decision["decision"] == "INCONCLUSIVE"


# ---------------------------------------------------------------------------
# D4: pre-run scaffold
# ---------------------------------------------------------------------------


def test_scaffold_exists_and_conforms(self_test_pack: Path) -> None:
    names = sorted(path.name for path in SCAFFOLD.iterdir() if path.is_file())
    assert names == sorted(sat.ARTIFACT_FILENAMES)
    dis.validate_artifact_pack(SCAFFOLD)
    snapshot = SCAFFOLD / "01_protocol_snapshot.json"
    assert base.sha256_file(snapshot) == PROTOCOL_HASH


def test_scaffold_marks_every_derived_file_not_applicable() -> None:
    decision = json.loads((SCAFFOLD / "04_decision.json").read_text(encoding="utf-8"))
    assert decision["status"] == "BLOCKED"
    assert decision["decision"] == "INCONCLUSIVE"
    for name in ("03_metrics.csv", "06_paper_table.csv", "07_figure_data.csv"):
        with (SCAFFOLD / name).open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 1
        assert rows[0]["not_applicable_reason"]
        if "status" in rows[0]:
            assert rows[0]["status"] == "not_applicable"
        else:
            assert rows[0]["value"] == ""
    records = [
        json.loads(line)
        for line in (SCAFFOLD / "02_records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    assert records[0]["status"] == "not_applicable"
    manifest = json.loads(
        (SCAFFOLD / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["manifest_written_last"] is True
    for entry in manifest["artifacts"]:
        path = SCAFFOLD / entry["path"]
        assert base.sha256_file(path) == entry["sha256"]


def test_scaffold_is_deterministically_regenerable(tmp_path: Path) -> None:
    target = tmp_path / "track-a1"
    dis.build_prerun_scaffold(target)
    first = {
        path.name: base.sha256_file(path) for path in sorted(target.iterdir())
    }
    dis.build_prerun_scaffold(target)
    second = {
        path.name: base.sha256_file(path) for path in sorted(target.iterdir())
    }
    assert first == second
    committed = {
        path.name: base.sha256_file(path)
        for path in sorted(SCAFFOLD.iterdir())
        if path.is_file()
    }
    assert first == committed


def test_scaffold_stage_manifest_carries_the_25a_provenance() -> None:
    manifest = json.loads(
        (SCAFFOLD / "00_stage_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["protocol_hash"] == PROTOCOL_HASH
    assert list(manifest["stages"]) == list(dis.STAGES)
    inputs = manifest["inputs"]
    assert inputs["existing_lens_blob"] == dis.EXISTING_LENS_BLOB
    assert inputs["existing_lens_container"] == dis.EXISTING_BLOB_CONTAINER
    assert inputs["existing_lens_storage_account"] == dis.EXISTING_STORAGE_ACCOUNT
    assert inputs["existing_lens_expected_sha256"] == dis.EXISTING_LENS_SHA256
    assert inputs["existing_lens_expected_bytes"] == dis.EXISTING_LENS_BYTES
    assert inputs["existing_lens_refitted"] is False
    assert inputs["direct_50_fit_performed"] is False


# ---------------------------------------------------------------------------
# D5: post-run analysis
# ---------------------------------------------------------------------------


def test_analysis_reproduces_the_runner_numbers(self_test_pack: Path) -> None:
    result = analysis.analyse(self_test_pack)
    assert result["measured"] is True
    recorded = json.loads(
        (self_test_pack / "04_decision.json").read_text(encoding="utf-8")
    )
    observed = {
        item["criterion"]: item["value"] for item in recorded["criteria_detail"]
    }
    for criterion, value in observed.items():
        if value is None:
            continue
        assert result["values"][criterion] == pytest.approx(value)
    assert result["decision"]["decision"] == recorded["decision"]


def test_analysis_write_is_idempotent(self_test_pack: Path, tmp_path: Path) -> None:
    import shutil

    target = tmp_path / "pack"
    shutil.copytree(self_test_pack, target)
    assert analysis.main(["--pack-dir", str(target), "--write"]) == 0
    first = {
        path.name: base.sha256_file(path) for path in sorted(target.iterdir())
    }
    assert analysis.main(["--pack-dir", str(target), "--write"]) == 0
    second = {
        path.name: base.sha256_file(path) for path in sorted(target.iterdir())
    }
    assert first == second
    dis.validate_artifact_pack(target)


def test_analysis_handles_a_pre_run_pack() -> None:
    result = analysis.analyse(SCAFFOLD)
    assert result["measured"] is False
    assert result["decision"]["status"] == "BLOCKED"
    assert result["metric_rows"][0]["not_applicable_reason"]
    assert result["paper_rows"][0]["status"] == "not_applicable"
    assert result["figure_rows"][0]["status"] == "not_applicable"


# ---------------------------------------------------------------------------
# launcher invariants
# ---------------------------------------------------------------------------


def test_launcher_invariants() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "2>/dev/null" not in text
    assert "\r" not in text
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    for token in (
        'CONTAINER_APP_ENV="cae-jspace-observation-sea-vnet2"',
        'BLOB_CONTAINER="jspace-results"',
        'WORKLOAD_PROFILE_NAME="gpu-t4"',
        'JOB_NAME="job-jspace-p05c-jlens-disjoint"',
        'BLOB_PREFIX="phase05c-jlens-disjoint/${RUN_ID}"',
        '"replicaRetryLimit": 0',
        '"replicaCompletionCount": 1',
        '"parallelism": 1',
        '"replicaTimeout": 7200',
        "--auth-mode login",
        "--existing-lens-path",
        "--existing-lens-blob",
        "--existing-lens-sha256",
        "scripts/phase05c_jlens_disjoint.py",
        "UserAssigned",
    ):
        assert token in text, token
    for forbidden in (
        "--account-key",
        "AZURE_STORAGE_KEY",
        "sas-token",
        "--sas",
        "public-network-access",
        ":latest",
    ):
        assert forbidden not in text, forbidden
    assert text.index("EXISTING_JOB_COUNT") < text.index("az rest --method put")
    assert text.index("PRE_START_EXECUTIONS") < text.index(
        "az containerapp job start"
    )
    assert text.count("az containerapp job start") == 1


def test_launcher_registers_the_measured_25a_blob_and_identity_handling() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'BLOB_ACCOUNT="stjspacefiles0709085305"' in text
    assert dis.EXISTING_LENS_BLOB in text
    assert dis.EXISTING_LENS_SHA256 in text
    assert f'EXISTING_LENS_BYTES="${{JSPACE_EXISTING_LENS_BYTES:-{dis.EXISTING_LENS_BYTES}}}"' in text
    # content-length preflight must happen before the job is created
    assert "properties.contentLength" in text
    assert text.index("properties.contentLength") < text.index("az rest --method put")
    # multiple user-assigned identities exist, so the client id must be explicit
    # and the deprecated --username form must never appear
    assert "--username" not in text
    assert '{"name": "AZURE_CLIENT_ID", "value": "$IDENTITY_CLIENT_ID"}' in text
    if "az login --identity" in text:
        assert "az login --identity --client-id" in text


def test_launcher_is_not_covered_by_the_build_script_assertion() -> None:
    feasibility_tests = (
        ROOT / "tests" / "test_phase05_jlens_feasibility.py"
    ).read_text(encoding="utf-8")
    assert "07_build_phase05_jlens.sh" in feasibility_tests
    assert "12_run_phase05c_jlens_disjoint.sh" not in feasibility_tests


def test_container_image_ships_the_disjoint_inputs() -> None:
    dockerfile = (ROOT / "Dockerfile.jlens").read_text(encoding="utf-8")
    assert "COPY scripts/phase05c_jlens_disjoint.py /workspace/scripts/" in dockerfile
    assert (
        "COPY src/jspace_observation/phase05c_jlens_disjoint.py "
        "/workspace/src/jspace_observation/" in dockerfile
    )
    assert "/workspace/runtime/staged" in dockerfile


def test_phase05b_module_behaviour_is_unchanged() -> None:
    assert sat.PHASE == "phase05-jlens-saturation"
    assert sat.TRACK == "track-a"
    assert sat.CORPUS_TOTAL == 50
    assert sat.RESERVE_PROMPTS == 15
    sample_size = {
        "corpus_prompts": sat.CORPUS_TOTAL,
        "fit_a_prompts": sat.FIT_A_PROMPTS,
        "fit_b_prompts": sat.FIT_B_PROMPTS,
        "fit_b_shards": list(sat.FIT_B_SHARDS),
        "control_subset_prompts": sat.CONTROL_SUBSET_SIZE,
        "control_subset_shards": list(sat.CONTROL_SUBSET_SHARDS),
        "heldout_prompts": sat.HELDOUT_PROMPTS,
        "reserve_prompts": sat.RESERVE_PROMPTS,
        "source_layers": list(sat.SOURCE_LAYERS),
        "target_layer": sat.TARGET_LAYER,
    }
    snapshot = sat.build_protocol_snapshot(sample_size=sample_size)
    assert (
        base.sha256_bytes(base.canonical_json_bytes(snapshot))
        == "b4422756bec723534b78981d79837f3cf9422244f4c1bf40eba205fcce29d32e"
    )
    recorded = (
        ROOT
        / "artifacts"
        / "phase05b-jlens-saturation"
        / "track-a"
        / "20260725T122016Z"
        / "01_protocol_snapshot.json"
    )
    assert (
        base.sha256_file(recorded)
        == "b4422756bec723534b78981d79837f3cf9422244f4c1bf40eba205fcce29d32e"
    )
