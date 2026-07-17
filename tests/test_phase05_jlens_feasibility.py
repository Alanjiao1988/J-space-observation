"""Model/GPU/network-free tests for the Phase 0.5A J-lens tooling."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "jspace_observation"))
sys.path.insert(0, str(ROOT))

import phase05_jlens as p05
from scripts import phase05_jlens_feasibility as runner_module


class FakeTokenizer:
    def __init__(self, length: int) -> None:
        self.length = length

    def __call__(self, _text, *, truncation, max_length, add_special_tokens):
        assert truncation is True
        assert add_special_tokens is True
        return {"input_ids": list(range(min(self.length, max_length)))}


def successful_results(memory: str = "green"):
    memory_record = {
        "classification": memory,
        "gpu_peak_reserved_ratio": 0.5,
        "gpu_free_gib": 8.0,
    }
    return {
        "F0": {"status": "success", "details": {}},
        "F1": {"status": "success", "details": {}},
        "F2": {"status": "success", "details": {"memory": memory_record}},
        "F3": {"status": "success", "details": {"memory": memory_record}},
        "F4": {"status": "success", "details": {}},
    }


def executable_scaling():
    return {
        "ten_prompt": {"executable": True},
        "sliced_25_prompt": {"executable": True},
    }


def test_exact_official_and_target_constants():
    assert p05.OFFICIAL_REPOSITORY == "https://github.com/anthropics/jacobian-lens"
    assert p05.OFFICIAL_COMMIT == "581d398613e5602a5af361e1c34d3a92ea82ba8e"
    assert p05.JLENS_DISTRIBUTION == p05.JLENS_IMPORT_NAME == "jlens"
    assert p05.JLENS_VERSION == "0.1.0"
    assert p05.MODEL_ID == "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
    assert p05.MODEL_REVISION == "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"
    assert (p05.MODEL_ARCHITECTURE, p05.MODEL_LAYERS, p05.MODEL_WIDTH) == (
        "Qwen2ForCausalLM",
        28,
        1536,
    )
    assert p05.CHECKPOINT_DTYPE == "bfloat16"
    assert p05.RUNTIME_DTYPE == "float16"


def test_source_pin_requires_exact_commit_and_rejects_floating_main():
    exact = (
        "jlens @ git+https://github.com/anthropics/jacobian-lens.git@"
        + p05.OFFICIAL_COMMIT
    )
    assert p05.validate_source_pin(exact) == p05.OFFICIAL_COMMIT
    with pytest.raises(p05.DependencyValidationError):
        p05.validate_source_pin(
            "git+https://github.com/anthropics/jacobian-lens.git@main"
        )
    with pytest.raises(p05.DependencyValidationError):
        p05.validate_source_pin(
            "git+https://github.com/anthropics/jacobian-lens.git@"
            + "0" * 40
        )


def test_nonexistent_import_fallback_is_rejected():
    assert p05.validate_import_name("jlens") == "jlens"
    with pytest.raises(p05.DependencyValidationError):
        p05.validate_import_name("jacobian_lens")


def test_exact_dependency_versions_are_required():
    p05.validate_dependency_versions(dict(p05.EXPECTED_DEPENDENCIES))
    wrong = dict(p05.EXPECTED_DEPENDENCIES)
    wrong["transformers"] = "5.9.1"
    with pytest.raises(p05.DependencyValidationError):
        p05.validate_dependency_versions(wrong)


def test_exact_full_model_revision_dtype_and_loading_controls_are_required():
    p05.validate_model_controls(
        model_id=p05.MODEL_ID,
        revision=p05.MODEL_REVISION,
        dtype="float16",
        trust_remote_code=False,
    )
    mutations = (
        {"model_id": "DeepSeek-R1-Distill-Qwen-1.5B"},
        {"revision": "main"},
        {"dtype": "bfloat16"},
        {"trust_remote_code": True},
        {"quantized": True},
        {"compile_model": True},
    )
    baseline = {
        "model_id": p05.MODEL_ID,
        "revision": p05.MODEL_REVISION,
        "dtype": "float16",
        "trust_remote_code": False,
        "quantized": False,
        "compile_model": False,
    }
    for mutation in mutations:
        with pytest.raises(p05.DependencyValidationError):
            p05.validate_model_controls(**(baseline | mutation))


def test_exact_config_metadata_is_required():
    p05.validate_config_metadata(
        {
            "architectures": ["Qwen2ForCausalLM"],
            "n_layers": 28,
            "d_model": 1536,
            "checkpoint_dtype": "torch.bfloat16",
            "resolved_revision": p05.MODEL_REVISION,
        }
    )
    with pytest.raises(p05.DependencyValidationError):
        p05.validate_config_metadata(
            {
                "architectures": ["Qwen2ForCausalLM"],
                "n_layers": 28,
                "d_model": 1536,
                "checkpoint_dtype": "float16",
                "resolved_revision": p05.MODEL_REVISION,
            }
        )


def test_dynamic_representative_layers_and_source_target_order():
    layers = p05.representative_layers(28)
    assert layers == {
        "target_layer": 27,
        "f2_source_layer": 13,
        "f3_source_layers": [6, 13, 20],
    }
    p05.ensure_source_before_target([6, 13, 20], 27, 28)
    with pytest.raises(p05.Phase05ValidationError):
        p05.ensure_source_before_target([6, 27], 27, 28)
    with pytest.raises(p05.Phase05ValidationError):
        p05.ensure_source_before_target([13, 13], 27, 28)


def test_token_length_guard_uses_fake_tokenizer_without_network():
    assert p05.guarded_token_length(FakeTokenizer(24), "generic") == 24
    assert p05.guarded_token_length(FakeTokenizer(40), "generic") == 32
    with pytest.raises(p05.Phase05ValidationError):
        p05.guarded_token_length(FakeTokenizer(23), "generic")
    assert p05.valid_position_count(32) == 15
    with pytest.raises(p05.Phase05ValidationError):
        p05.valid_position_count(17)


def test_stage_transition_rules_and_failure_blocking():
    assert p05.can_start_stage("F0", {})
    assert not p05.can_start_stage("F1", {})
    assert p05.can_start_stage("F1", {"F0": {"status": "success"}})
    assert not p05.can_start_stage("F2", {"F1": {"status": "failed"}})
    assert p05.stages_after_failure("F2", {}) == ["F3", "F4", "F5"]
    with pytest.raises(p05.Phase05ValidationError):
        p05.can_start_stage("F9", {})


def test_metrics_schema_is_exact():
    assert p05.METRICS_COLUMNS == (
        "stage",
        "status",
        "metric",
        "value",
        "unit",
        "recorded_at_utc",
    )


def test_finite_full_jacobian_validation():
    p05.validate_jacobian_summary(
        shape=[1536, 1536],
        dtype="torch.float32",
        finite=True,
        norm=2.5,
    )
    assert p05.finite_numbers([0.0, 1, -3.5])
    assert not p05.finite_numbers([float("nan")])
    for mutation in (
        {"shape": [1536, 1]},
        {"dtype": "torch.float16"},
        {"finite": False},
        {"norm": 0.0},
    ):
        baseline = {
            "shape": [1536, 1536],
            "dtype": "torch.float32",
            "finite": True,
            "norm": 1.0,
        }
        with pytest.raises(p05.NumericalValidationError):
            p05.validate_jacobian_summary(**(baseline | mutation))


@pytest.mark.parametrize(
    ("error", "stage", "expected"),
    [
        (p05.DependencyValidationError("version"), "F0", "dependency_failure"),
        (p05.AdapterValidationError("layout"), "F1", "adapter_failure"),
        (RuntimeError("derivative for op is not implemented"), "F2", "unsupported_autograd"),
        (RuntimeError("CUDA out of memory"), "F2", "cuda_oom"),
        (p05.ApplicationTimeoutError("watchdog"), "F3", "timeout"),
        (p05.NumericalValidationError("non-finite"), "F2", "numerical_failure"),
        (p05.CheckpointValidationError("manifest"), "F3", "checkpoint_failure"),
        (RuntimeError("unclassified"), "F3", "unknown"),
    ],
)
def test_failure_classification(error, stage, expected):
    assert p05.classify_failure(error, stage) == expected
    assert expected in p05.FAILURE_TAXONOMY


def test_memory_green_borderline_and_stop_rules():
    green = p05.classify_memory(
        gpu_peak_reserved_bytes=int(0.85 * 16 * p05.GIB),
        gpu_total_bytes=16 * p05.GIB,
        gpu_free_bytes=2 * p05.GIB,
        host_rss_bytes=24 * p05.GIB,
        host_total_bytes=32 * p05.GIB,
    )
    assert green["classification"] == "green"
    borderline = p05.classify_memory(
        gpu_peak_reserved_bytes=int(0.86 * 16 * p05.GIB),
        gpu_total_bytes=16 * p05.GIB,
        gpu_free_bytes=2 * p05.GIB,
        host_rss_bytes=20 * p05.GIB,
        host_total_bytes=32 * p05.GIB,
    )
    assert borderline["classification"] == "borderline"
    total_gpu = 16 * p05.GIB
    stopped = p05.classify_memory(
        gpu_peak_reserved_bytes=(92 * total_gpu + 99) // 100,
        gpu_total_bytes=total_gpu,
        gpu_free_bytes=3 * p05.GIB,
        host_rss_bytes=20 * p05.GIB,
        host_total_bytes=32 * p05.GIB,
    )
    assert stopped["classification"] == "stop"


def test_dynamic_dim_batch_uses_registered_f2_margin():
    assert (
        p05.choose_f3_dim_batch(
            {
                "classification": "green",
                "gpu_peak_reserved_ratio": 0.65,
                "gpu_free_gib": 4.0,
            },
            f2_wall_seconds=100,
        )
        == 2
    )
    assert (
        p05.choose_f3_dim_batch(
            {
                "classification": "green",
                "gpu_peak_reserved_ratio": 0.66,
                "gpu_free_gib": 4.0,
            },
            f2_wall_seconds=100,
        )
        == 1
    )


def test_f5_cost_guard_skips_without_time_or_memory_margin():
    allowed = p05.f5_cost_guard(
        elapsed_seconds=100,
        f3_seconds=200,
        memory_classification="green",
    )
    assert allowed["run"] is True
    time_blocked = p05.f5_cost_guard(
        elapsed_seconds=6000,
        f3_seconds=200,
        memory_classification="green",
    )
    assert time_blocked["status"] == "skipped_cost_guard"
    memory_blocked = p05.f5_cost_guard(
        elapsed_seconds=100,
        f3_seconds=200,
        memory_classification="borderline",
    )
    assert memory_blocked["run"] is False


def test_measured_scaling_paths_are_exact():
    plan = p05.measured_scaling_plan(
        seconds_per_prompt=100,
        memory_classification="green",
    )
    assert plan["ten_prompt"]["slices"] == [10]
    assert plan["sliced_25_prompt"]["slices"] == [10, 10, 5]
    assert plan["ten_prompt"]["executable"]
    slow = p05.measured_scaling_plan(
        seconds_per_prompt=600,
        memory_classification="green",
    )
    assert not slow["ten_prompt"]["executable"]


def test_green_amber_red_and_unrated_decisions():
    green = p05.derive_decision(
        successful_results(),
        authorized_compatibility_fix_attempted=False,
        scaling_plan=executable_scaling(),
    )
    assert green["decision"] == "GREEN"
    assert green["plan_b_triggered"] is False

    incomplete = successful_results()
    incomplete["F4"] = {"status": "failed", "details": {}}
    amber = p05.derive_decision(
        incomplete,
        authorized_compatibility_fix_attempted=False,
        scaling_plan=executable_scaling(),
    )
    assert amber["decision"] == "AMBER"

    f2_failure = {
        "F0": {"status": "success"},
        "F1": {"status": "success"},
        "F2": {"status": "failed"},
    }
    unrated = p05.derive_decision(
        f2_failure,
        authorized_compatibility_fix_attempted=False,
        scaling_plan=None,
    )
    assert (unrated["decision"], unrated["gate_status"]) == ("UNRATED", "BLOCKED")
    red = p05.derive_decision(
        f2_failure,
        authorized_compatibility_fix_attempted=True,
        scaling_plan=None,
    )
    assert red["decision"] == "RED"

    dependency_block = p05.derive_decision(
        {"F0": {"status": "failed"}},
        authorized_compatibility_fix_attempted=True,
        scaling_plan=None,
    )
    assert dependency_block["decision"] == "UNRATED"


def test_checkpoint_external_manifest_controls_and_hash():
    controls = p05.make_checkpoint_controls(
        prompt_order_sha256="a" * 64,
        source_layers=[6, 13, 20],
        target_layer=27,
        dim_batch=1,
    )
    manifest = p05.make_checkpoint_manifest(controls)
    p05.validate_checkpoint_manifest(manifest, controls)
    changed = dict(controls)
    changed["dim_batch"] = 2
    with pytest.raises(p05.CheckpointValidationError):
        p05.validate_checkpoint_manifest(manifest, changed)
    tampered = dict(manifest)
    tampered["controls_sha256"] = "0" * 64
    with pytest.raises(p05.CheckpointValidationError):
        p05.validate_checkpoint_manifest(tampered, controls)
    assert controls["model_revision"] == p05.MODEL_REVISION
    assert controls["prompt_order_sha256"] == "a" * 64
    assert controls["backend"] == "official-jlens-fit"


def test_manifest_ordering_hash_and_corpus_order(tmp_path):
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    manifest = p05.build_artifact_manifest(
        tmp_path, generated_at_utc="2026-07-16T00:00:00Z"
    )
    assert manifest["manifest_order"] == ["a.txt", "z.txt"]
    assert all(len(item["sha256"]) == 64 for item in manifest["artifacts"])

    records = [{"id": "a", "text": "one"}, {"id": "b", "text": "two"}]
    assert p05.canonical_jsonl_sha256(records) != p05.canonical_jsonl_sha256(
        list(reversed(records))
    )


def test_managed_identity_auth_rejects_secret_bearing_configuration():
    p05.validate_blob_auth_config(
        {
            "credential_mode": "default_credential_managed_identity_only",
            "managed_identity_client_id": "not-a-secret",
            "account": "example",
            "container": "results",
        }
    )
    with pytest.raises(p05.Phase05ValidationError):
        p05.validate_blob_auth_config(
            {
                "credential_mode": "default_credential_managed_identity_only",
                "storage_secret": "forbidden",
            }
        )
    with pytest.raises(p05.Phase05ValidationError):
        p05.validate_blob_auth_config({"credential_mode": "shared_key"})


def test_default_credential_chain_leaves_only_managed_identity():
    source = (ROOT / "scripts" / "phase05_jlens_feasibility.py").read_text(
        encoding="utf-8"
    )
    for credential in (
        "environment",
        "workload_identity",
        "shared_token_cache",
        "visual_studio_code",
        "cli",
        "powershell",
        "developer_cli",
        "interactive_browser",
        "broker",
    ):
        assert f"exclude_{credential}_credential=True" in source
    assert "exclude_managed_identity_credential=True" not in source
    assert "overwrite=False" in source


def test_logit_lens_substitution_is_rejected():
    p05.validate_apply_controls(use_jacobian=True, layers=[6, 13, 20])
    with pytest.raises(p05.Phase05ValidationError):
        p05.validate_apply_controls(use_jacobian=False, layers=[6])
    with pytest.raises(p05.Phase05ValidationError):
        p05.validate_apply_controls(use_jacobian=True, layers=[])


def test_runner_writes_exact_model_free_output_schema(monkeypatch, tmp_path):
    monkeypatch.delenv("JSPACE_BLOB_ACCOUNT", raising=False)
    monkeypatch.delenv("JSPACE_BLOB_CONTAINER", raising=False)
    monkeypatch.delenv("JSPACE_BLOB_RESUME_PREFIX", raising=False)
    args = runner_module.parse_args(
        [
            "--output-dir",
            str(tmp_path),
            "--corpus",
            str(ROOT / "data" / "jlens_feasibility_prompts.jsonl"),
        ]
    )
    runner = runner_module.Phase05Runner(args)
    runner.persist("tooling-test")
    for filename in p05.REQUIRED_OUTPUT_FILENAMES:
        assert (tmp_path / filename).is_file()
    with (tmp_path / "phase05_jlens_metrics.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        assert tuple(csv.reader(handle).__next__()) == p05.METRICS_COLUMNS
    decision = json.loads(
        (tmp_path / "phase05_jlens_decision.json").read_text(encoding="utf-8")
    )
    assert decision["decision"] == "UNRATED"
    assert decision["gate_status"] == "BLOCKED"
    assert decision["automatic_plan_b"] is False


def test_failed_blob_recovery_blocks_before_model_or_gpu(monkeypatch, tmp_path):
    monkeypatch.delenv("JSPACE_BLOB_ACCOUNT", raising=False)
    monkeypatch.delenv("JSPACE_BLOB_CONTAINER", raising=False)
    monkeypatch.setenv(
        "JSPACE_BLOB_RESUME_PREFIX",
        "phase05-jlens-feasibility/20260716T000000Z/attempts/primary",
    )
    args = runner_module.parse_args(
        [
            "--output-dir",
            str(tmp_path),
            "--corpus",
            str(ROOT / "data" / "jlens_feasibility_prompts.jsonl"),
            "--resume",
        ]
    )
    runner = runner_module.Phase05Runner(args)
    assert runner.run() == 2
    stages = json.loads(
        (tmp_path / "phase05_jlens_stage_results.json").read_text(encoding="utf-8")
    )["stages"]
    assert stages["F0"]["failure_class"] == "checkpoint_failure"
    assert all(stages[stage]["status"] == "blocked" for stage in p05.STAGES[1:])


def test_output_schema_validator_rejects_wrong_metrics_header():
    with pytest.raises(p05.Phase05ValidationError):
        p05.validate_output_schema(
            environment={"schema_version": "phase05-jlens-environment-v1"},
            stage_results={"schema_version": "phase05-jlens-stage-results-v1"},
            decision={"decision": "UNRATED"},
            metrics_header=["wrong"],
            manifest={"artifacts": []},
        )


def test_runner_contains_real_official_calls_and_no_substitution():
    source = (ROOT / "scripts" / "phase05_jlens_feasibility.py").read_text(
        encoding="utf-8"
    )
    assert ".jacobian_for_prompt(" in source
    assert ".autograd.grad" in source
    assert ".fit(" in source
    assert ".JacobianLens.merge(" in source
    assert "use_jacobian=True" in source
    assert "use_jacobian=False" not in source
    assert "import jacobian_lens" not in source
    assert "torch.no_grad" not in source
    assert "protocol.MODEL_ID" in source
    assert "protocol.MODEL_REVISION" in source


def test_requirements_and_image_are_exact_and_isolated():
    requirements = (ROOT / "requirements-jlens.txt").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile.jlens").read_text(encoding="utf-8")
    exact_pin = (
        "git+https://github.com/anthropics/jacobian-lens.git@"
        + p05.OFFICIAL_COMMIT
    )
    assert exact_pin in requirements
    for package, version in p05.EXPECTED_DEPENDENCIES.items():
        if package != "jlens":
            assert f"{package}=={version}" in requirements
    assert p05.OFFICIAL_COMMIT in dockerfile
    assert "python:3.11" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "semantic_audit_build_provenance" not in dockerfile
    assert "COPY . " not in dockerfile
    assert ":latest" not in dockerfile


def test_azure_scripts_enforce_dedicated_immutable_build_and_bounded_job():
    build = (
        ROOT / "infra" / "azure" / "scripts" / "07_build_phase05_jlens.sh"
    ).read_text(encoding="utf-8")
    run = (
        ROOT / "infra" / "azure" / "scripts" / "08_run_phase05_jlens.sh"
    ).read_text(encoding="utf-8")
    assert 'IMAGE_REPOSITORY="j-space-observation-jlens"' in build
    assert "--file \"$PROJECT_ROOT/Dockerfile.jlens\"" in build
    assert ":latest" not in build
    assert "refusing overwrite" in build
    assert "image_digest" in build
    assert 'JOB_NAME="job-jspace-p05-jlens"' in run
    assert 'CONTAINER_APP_ENV="cae-jspace-observation-sea-vnet2"' in run
    assert 'WORKLOAD_PROFILE_NAME="gpu-t4"' in run
    assert 'IDENTITY_NAME="id-jspace-aca-acrpull-sea"' in run
    assert 'BLOB_ACCOUNT="stjspacefiles0709085305"' in run
    assert 'BLOB_CONTAINER="jspace-results"' in run
    assert '"replicaTimeout": 7200' in run
    assert '"replicaRetryLimit": 0' in run
    assert '"replicaCompletionCount": 1' in run
    assert '"parallelism": 1' in run
    assert "6900s" in run
    assert "EXECUTION_COUNT" in run
    assert "operational-fix" in run
    assert '"volumes"' not in run
    assert '"secrets"' not in run


def test_checked_corpus_is_small_generic_and_canonically_hashed():
    records, digest = runner_module.load_corpus(
        ROOT / "data" / "jlens_feasibility_prompts.jsonl"
    )
    assert len(records) == 2
    assert len(digest) == 64
    assert digest == p05.canonical_jsonl_sha256(records)
    assert all(set(record) == {"id", "text"} for record in records)
