"""Model/GPU/network-free tests for the Phase 0.5A J-lens tooling."""

from __future__ import annotations

import csv
import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "jspace_observation"))
sys.path.insert(0, str(ROOT / "infra" / "azure" / "scripts"))
sys.path.insert(0, str(ROOT))

import phase05_jlens as p05
import phase05_claim_election as claim_election
from scripts import phase05_jlens_feasibility as runner_module


class FakeTokenizer:
    def __init__(self, length: int) -> None:
        self.length = length

    def __call__(self, _text, *, truncation, max_length, add_special_tokens):
        assert truncation is True
        assert add_special_tokens is True
        return {"input_ids": list(range(min(self.length, max_length)))}


class FakeJacobianLens:
    def __init__(self, jacobians, *, n_prompts, d_model):
        self.jacobians = {layer: matrix.float() for layer, matrix in jacobians.items()}
        self.source_layers = sorted(self.jacobians)
        self.n_prompts = n_prompts
        self.d_model = d_model

    def save(self, path, *, dtype):
        import torch

        torch.save(
            {
                "J": {
                    layer: matrix.to(dtype)
                    for layer, matrix in self.jacobians.items()
                },
                "n_prompts": self.n_prompts,
                "source_layers": self.source_layers,
                "d_model": self.d_model,
            },
            path,
        )

    @classmethod
    def load(cls, path):
        import torch

        raw = torch.load(path, map_location="cpu", weights_only=True)
        return cls(
            raw["J"],
            n_prompts=raw["n_prompts"],
            d_model=raw["d_model"],
        )


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


def deployment_claim(
    *,
    name,
    prefix,
    timestamp,
    state="Succeeded",
    operation="launch",
    fixed=None,
    dynamic=None,
):
    values = {
        "claimName": name,
        "claimPrefix": prefix,
        "invocationId": name.removeprefix(prefix),
        "operation": operation,
        **(fixed or {}),
        **(dynamic or {}),
    }
    if operation == "launch" and "launcherSha" not in values:
        values["launcherSha"] = "f" * 40
    return {
        "name": name,
        "properties": {
            "timestamp": timestamp,
            "provisioningState": state,
            "outputs": {
                key: {"type": "String", "value": value}
                for key, value in values.items()
            },
        },
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


def test_lossless_lens_save_is_explicit_fp32_and_torch_equal(tmp_path):
    import torch

    lens = FakeJacobianLens(
        {
            1: torch.tensor([[0.1, -0.2], [0.3, 0.4]], dtype=torch.float32),
            2: torch.tensor([[1.1, 1.2], [-1.3, 1.4]], dtype=torch.float32),
        },
        n_prompts=2,
        d_model=2,
    )
    module = SimpleNamespace(JacobianLens=FakeJacobianLens)
    path = tmp_path / "lens.pt"
    loaded, audit = runner_module.save_lossless_jacobian_lens(
        torch, module, lens, path
    )
    raw = torch.load(path, map_location="cpu", weights_only=True)
    assert all(matrix.dtype == torch.float32 for matrix in raw["J"].values())
    assert all(
        torch.equal(loaded.jacobians[layer], lens.jacobians[layer])
        for layer in lens.source_layers
    )
    assert audit["lens_save_dtype"] == "torch.float32"
    assert audit["torch_equal_all_layers"] is True
    assert set(audit["exact_max_abs"].values()) == {0.0}


def test_lossless_lens_save_failures_never_return_success(monkeypatch, tmp_path):
    import torch

    lens = FakeJacobianLens(
        {1: torch.eye(2, dtype=torch.float32)},
        n_prompts=2,
        d_model=2,
    )
    module = SimpleNamespace(JacobianLens=FakeJacobianLens)
    path = tmp_path / "lens.pt"
    path.write_bytes(b"old")

    class WrongDtypeLens(FakeJacobianLens):
        def save(self, target, *, dtype):
            assert dtype == torch.float32
            torch.save(
                {
                    "J": {1: self.jacobians[1].half()},
                    "n_prompts": 2,
                    "source_layers": [1],
                    "d_model": 2,
                },
                target,
            )

    wrong = WrongDtypeLens(lens.jacobians, n_prompts=2, d_model=2)
    with pytest.raises(p05.CheckpointValidationError):
        runner_module.save_lossless_jacobian_lens(torch, module, wrong, path)
    assert path.read_bytes() == b"old"

    calls = 0
    original_validate = runner_module.validate_lossless_lens_payload

    def fail_after_replace(*args, **kwargs):
        nonlocal calls
        calls += 1
        result = original_validate(*args, **kwargs)
        if calls == 2:
            raise p05.CheckpointValidationError("post-replace validation failed")
        return result

    monkeypatch.setattr(
        runner_module, "validate_lossless_lens_payload", fail_after_replace
    )
    with pytest.raises(p05.CheckpointValidationError):
        runner_module.save_lossless_jacobian_lens(torch, module, lens, path)
    assert path.read_bytes() != b"old"


def test_complete_checkpoint_reconstruction_is_exact_and_fail_closed():
    import torch

    module = SimpleNamespace(JacobianLens=FakeJacobianLens)
    state = {
        "jacobian_sum": {
            1: torch.tensor([[2.0, 4.0], [6.0, 8.0]], dtype=torch.float32)
        },
        "n_done": 2,
        "next_idx": 2,
        "source_layers": [1],
        "target_layer": 2,
        "skip_first": 16,
    }
    lens = runner_module.reconstruct_complete_f3_lens(
        torch,
        module,
        state,
        source_layers=[1],
        target_layer=2,
        d_model=2,
    )
    assert torch.equal(
        lens.jacobians[1],
        torch.tensor([[1.0, 2.0], [3.0, 4.0]], dtype=torch.float32),
    )
    tampered = deepcopy(state)
    tampered["jacobian_sum"][1] = tampered["jacobian_sum"][1].half()
    with pytest.raises(p05.CheckpointValidationError):
        runner_module.reconstruct_complete_f3_lens(
            torch,
            module,
            tampered,
            source_layers=[1],
            target_layer=2,
            d_model=2,
        )


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


def test_f3_dim1_time_guard_scales_by_prompt_count_and_layer_span():
    guard = p05.f3_dim1_time_guard(
        elapsed_seconds=100,
        f2_wall_seconds=200,
        f2_source_layer=13,
        f3_source_layers=[6, 13, 20],
        target_layer=27,
    )
    assert guard["f2_layer_span"] == 14
    assert guard["f3_earliest_layer_span"] == 21
    assert guard["layer_span_ratio"] == 1.5
    assert guard["conservative_multiplier"] == 3.0
    assert guard["projected_fit_seconds"] == 600


def test_fresh_segment_admission_blocks_after_slow_persistence():
    class FakeClock:
        def __init__(self):
            self.now = 100.0

        def monotonic(self):
            return self.now

        def advance(self, seconds):
            self.now += seconds

    clock = FakeClock()
    first = p05.f3_segment_time_guard(
        elapsed_seconds=clock.monotonic(),
        estimated_remaining_fit_seconds=1000,
    )
    assert first["admitted"] is True
    clock.advance(5500)
    second = p05.f3_segment_time_guard(
        elapsed_seconds=clock.monotonic(),
        estimated_remaining_fit_seconds=500,
    )
    assert second["admitted"] is False
    assert second["projected_completion_seconds"] > 6120


def test_f3_checkpoint_actions_cover_zero_one_and_two_prompt_states():
    assert p05.f3_checkpoint_actions(0, 0) == [
        "fit_prompt_1",
        "persist_prompt_1",
        "fit_full_resume",
    ]
    assert p05.f3_checkpoint_actions(1, 1) == [
        "persist_prompt_1",
        "fit_full_resume",
    ]
    assert p05.f3_checkpoint_actions(2, 2) == ["load_full_resume"]
    with pytest.raises(p05.CheckpointValidationError):
        p05.f3_checkpoint_actions(1, 2)


def test_f3_memory_stop_is_a_hard_stop():
    assert p05.f3_memory_requires_stop(
        {"details": {"memory": {"classification": "stop"}}}
    )
    assert not p05.f3_memory_requires_stop(
        {"details": {"memory": {"classification": "green"}}}
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
    checkpoint_block = deepcopy(f2_failure)
    checkpoint_block["F2"]["failure_class"] = "checkpoint_failure"
    checkpoint_decision = p05.derive_decision(
        checkpoint_block,
        authorized_compatibility_fix_attempted=True,
        scaling_plan=None,
    )
    assert checkpoint_decision["decision"] == "UNRATED"

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


def build_operational_retry_fixture(monkeypatch, tmp_path):
    import torch

    monkeypatch.delenv("JSPACE_BLOB_ACCOUNT", raising=False)
    monkeypatch.delenv("JSPACE_BLOB_CONTAINER", raising=False)
    monkeypatch.delenv("JSPACE_BLOB_RESUME_PREFIX", raising=False)
    monkeypatch.setenv("JSPACE_ATTEMPT_ID", "operational-fix")
    monkeypatch.setattr(p05, "MODEL_WIDTH", 2)
    args = runner_module.parse_args(
        [
            "--output-dir",
            str(tmp_path),
            "--corpus",
            str(ROOT / "data" / "jlens_feasibility_prompts.jsonl"),
            "--resume",
            "--authorized-compatibility-fix-attempted",
        ]
    )
    runner = runner_module.Phase05Runner(args)
    runner.torch = torch
    runner.jlens = SimpleNamespace(JacobianLens=FakeJacobianLens)
    runner.layers = {
        "target_layer": 27,
        "f2_source_layer": 13,
        "f3_source_layers": [6, 13, 20],
    }
    checkpoint_dir = tmp_path / "checkpoint"
    lens_dir = tmp_path / "lens"
    checkpoint_dir.mkdir()
    lens_dir.mkdir()
    checkpoint_path = checkpoint_dir / "phase05_jlens_f3_fit_checkpoint.pt"
    prefix_checkpoint_path = (
        checkpoint_dir / "phase05_jlens_f3_prompt1_checkpoint.pt"
    )
    manifest_path = checkpoint_dir / "phase05_jlens_f3_checkpoint.manifest.json"
    prefix_manifest_path = (
        checkpoint_dir / "phase05_jlens_f3_prompt1_checkpoint.manifest.json"
    )
    lens_path = lens_dir / "phase05_jlens.pt"
    layers = runner.layers["f3_source_layers"]
    prefix_state = {
        "jacobian_sum": {
            layer: torch.full((2, 2), float(layer), dtype=torch.float32)
            for layer in layers
        },
        "n_done": 1,
        "next_idx": 1,
        "source_layers": layers,
        "target_layer": 27,
        "skip_first": 16,
    }
    complete_state = {
        **prefix_state,
        "jacobian_sum": {
            layer: torch.full((2, 2), float(layer * 2), dtype=torch.float32)
            for layer in layers
        },
        "n_done": 2,
        "next_idx": 2,
    }
    torch.save(prefix_state, prefix_checkpoint_path)
    torch.save(complete_state, checkpoint_path)
    controls = p05.make_checkpoint_controls(
        prompt_order_sha256=runner.corpus_sha256,
        source_layers=layers,
        target_layer=27,
        dim_batch=1,
    )
    manifest = p05.make_checkpoint_manifest(controls)
    progress = {
        "n_done": 1,
        "next_idx": 1,
        "prompt_prefix_count": 1,
        "prompt_prefix_sha256": p05.canonical_jsonl_sha256(
            runner.corpus_records[:1]
        ),
        "controls_sha256": manifest["controls_sha256"],
        "checkpoint": {
            "path": prefix_checkpoint_path.relative_to(tmp_path).as_posix(),
            "bytes": prefix_checkpoint_path.stat().st_size,
            "sha256": p05.sha256_file(prefix_checkpoint_path),
        },
    }
    manifest["progress"] = progress
    manifest["progress_sha256"] = p05.sha256_bytes(
        p05.canonical_json_bytes(progress)
    )
    runner_module.atomic_write_json(prefix_manifest_path, manifest)
    reconstructed = FakeJacobianLens(
        {
            layer: complete_state["jacobian_sum"][layer] / 2
            for layer in layers
        },
        n_prompts=2,
        d_model=2,
    )
    reconstructed.save(str(lens_path), dtype=torch.float16)
    lens_sha = p05.sha256_file(lens_path)
    completion = {
        "n_done": 2,
        "next_idx": 2,
        "complete_corpus_sha256": runner.corpus_sha256,
        "controls_sha256": manifest["controls_sha256"],
        "checkpoint_sha256": p05.sha256_file(checkpoint_path),
        "lens_sha256": lens_sha,
        "prefix_checkpoint_sha256": p05.sha256_file(prefix_checkpoint_path),
        "prefix_progress_sha256": manifest["progress_sha256"],
    }
    manifest["lens"] = {
        "path": lens_path.relative_to(tmp_path).as_posix(),
        "bytes": lens_path.stat().st_size,
        "sha256": lens_sha,
    }
    manifest["completion"] = completion
    manifest["completion_sha256"] = p05.sha256_bytes(
        p05.canonical_json_bytes(completion)
    )
    runner_module.atomic_write_json(manifest_path, manifest)
    details = {
        "dim_batch": 1,
        "checkpoint": {
            "path": checkpoint_path.relative_to(tmp_path).as_posix(),
            "bytes": checkpoint_path.stat().st_size,
            "sha256": p05.sha256_file(checkpoint_path),
        },
        "lens": dict(manifest["lens"]),
        "prompt_1_snapshot": {
            **progress,
            "manifest": {
                "path": prefix_manifest_path.relative_to(tmp_path).as_posix(),
                "sha256": p05.sha256_file(prefix_manifest_path),
            },
        },
        "save_load_max_abs": {"6": 0.0003, "13": 0.0004, "20": 0.0005},
        "memory": {"classification": "green"},
        "scaling_plan": executable_scaling(),
    }
    runner.results = {
        "F2": {"status": "success", "details": {}},
        "F3": {"status": "success", "details": details},
    }
    runner.prior_success = {"F2", "F3"}
    return runner, {
        "checkpoint": checkpoint_path,
        "prefix_checkpoint": prefix_checkpoint_path,
        "manifest": manifest_path,
        "prefix_manifest": prefix_manifest_path,
        "lens": lens_path,
    }


def test_operational_retry_atomically_reserializes_and_updates_completion(
    monkeypatch, tmp_path
):
    import torch

    runner, paths = build_operational_retry_fixture(monkeypatch, tmp_path)
    old_hash = p05.sha256_file(paths["lens"])
    assert runner._reuse_complete_f3() is True
    details = runner.results["F3"]["details"]
    raw = torch.load(paths["lens"], map_location="cpu", weights_only=True)
    assert all(matrix.dtype == torch.float32 for matrix in raw["J"].values())
    assert details["old_lens_sha256"] == old_hash
    assert details["new_lens_sha256"] == p05.sha256_file(paths["lens"])
    assert details["lossless_reserialized_on_operational_retry"] is True
    assert set(details["save_load_max_abs"].values()) == {0.0}
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["lens"]["sha256"] == details["new_lens_sha256"]
    assert manifest["completion"]["lens_sha256"] == details["new_lens_sha256"]
    assert manifest["completion_sha256"] == p05.sha256_bytes(
        p05.canonical_json_bytes(manifest["completion"])
    )
    assert (
        manifest["lossless_reserialization"]["old_lens"]["sha256"]
        == old_hash
    )
    assert manifest["lossless_reserialization"]["exact_fidelity"][
        "torch_equal_all_layers"
    ]
    assert all(
        torch.equal(
            runner.fitted_lens.jacobians[layer],
            runner.loaded_lens.jacobians[layer],
        )
        for layer in runner.layers["f3_source_layers"]
    )


@pytest.mark.parametrize("tamper", ["checkpoint", "prefix", "completion"])
def test_operational_retry_rejects_tampered_f3_bindings(
    monkeypatch, tmp_path, tamper
):
    runner, paths = build_operational_retry_fixture(monkeypatch, tmp_path)
    if tamper == "checkpoint":
        paths["checkpoint"].write_bytes(b"tampered")
    elif tamper == "prefix":
        paths["prefix_manifest"].write_text("{}", encoding="utf-8")
    else:
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        manifest["completion"]["complete_corpus_sha256"] = "0" * 64
        manifest["completion_sha256"] = p05.sha256_bytes(
            p05.canonical_json_bytes(manifest["completion"])
        )
        paths["manifest"].write_bytes(p05.canonical_json_bytes(manifest))
    with pytest.raises(p05.CheckpointValidationError):
        runner._reuse_complete_f3()


def test_operational_retry_manifest_failure_after_replace_is_fail_closed(
    monkeypatch, tmp_path
):
    import torch

    runner, paths = build_operational_retry_fixture(monkeypatch, tmp_path)
    original_write = runner_module.atomic_write_json

    def fail_manifest(path, value):
        if Path(path) == paths["manifest"]:
            raise p05.CheckpointValidationError("simulated manifest failure")
        return original_write(path, value)

    monkeypatch.setattr(runner_module, "atomic_write_json", fail_manifest)
    with pytest.raises(p05.CheckpointValidationError):
        runner._reuse_complete_f3()
    raw = torch.load(paths["lens"], map_location="cpu", weights_only=True)
    assert all(matrix.dtype == torch.float32 for matrix in raw["J"].values())
    stale = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert stale["completion"]["lens_sha256"] != p05.sha256_file(paths["lens"])


@pytest.mark.parametrize("failure_stage", ["F2", "F3"])
def test_operational_retry_never_recomputes_f2_or_f3(
    monkeypatch, tmp_path, failure_stage
):
    monkeypatch.delenv("JSPACE_BLOB_ACCOUNT", raising=False)
    monkeypatch.delenv("JSPACE_BLOB_CONTAINER", raising=False)
    monkeypatch.setenv("JSPACE_ATTEMPT_ID", "operational-fix")
    args = runner_module.parse_args(
        [
            "--output-dir",
            str(tmp_path),
            "--corpus",
            str(ROOT / "data" / "jlens_feasibility_prompts.jsonl"),
            "--authorized-compatibility-fix-attempted",
        ]
    )
    runner = runner_module.Phase05Runner(args)
    runner.results["F2"] = {
        "status": "success",
        "details": {"continue_allowed": True},
    }
    monkeypatch.setattr(runner, "persist", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        runner,
        "execute",
        lambda stage, _function: True
        if stage in {"F0", "F1"}
        else (_ for _ in ()).throw(AssertionError(f"computed {stage}")),
    )
    monkeypatch.setattr(
        runner, "mark_operational_retry_checkpoint_failure", lambda *_args: None
    )
    monkeypatch.setattr(runner, "block_remaining", lambda *_args: None)
    monkeypatch.setattr(
        runner,
        "_valid_prior_artifact",
        lambda *_args: failure_stage != "F2",
    )
    if failure_stage == "F3":
        monkeypatch.setattr(
            runner,
            "_reuse_complete_f3",
            lambda: (_ for _ in ()).throw(
                p05.CheckpointValidationError("invalid prior F3")
            ),
        )
    assert runner.run() == 7


def test_f3_resume_bindings_accept_only_exact_zero_one_two_states():
    controls = p05.make_checkpoint_controls(
        prompt_order_sha256="a" * 64,
        source_layers=[6, 13, 20],
        target_layer=27,
        dim_batch=1,
    )
    prefix_sha = "b" * 64
    checkpoint_sha = "c" * 64
    prefix_checkpoint_sha = "e" * 64
    lens_sha = "d" * 64
    zero = p05.make_checkpoint_manifest(controls)
    p05.validate_f3_resume_binding(
        zero,
        controls,
        n_done=0,
        next_idx=0,
        checkpoint_sha256=None,
        expected_prompt_prefix_sha256=prefix_sha,
        expected_complete_corpus_sha256=controls["prompt_order_sha256"],
    )
    with pytest.raises(p05.CheckpointValidationError):
        p05.validate_f3_resume_binding(
            zero,
            controls,
            n_done=0,
            next_idx=0,
            checkpoint_sha256="0" * 64,
            expected_prompt_prefix_sha256=prefix_sha,
            expected_complete_corpus_sha256=controls["prompt_order_sha256"],
        )

    one = p05.make_checkpoint_manifest(controls)
    one["progress"] = {
        "n_done": 1,
        "next_idx": 1,
        "prompt_prefix_count": 1,
        "prompt_prefix_sha256": prefix_sha,
        "controls_sha256": one["controls_sha256"],
        "checkpoint": {"sha256": prefix_checkpoint_sha},
    }
    one["progress_sha256"] = p05.sha256_bytes(
        p05.canonical_json_bytes(one["progress"])
    )
    p05.validate_f3_resume_binding(
        one,
        controls,
        n_done=1,
        next_idx=1,
        checkpoint_sha256=prefix_checkpoint_sha,
        expected_prompt_prefix_sha256=prefix_sha,
        expected_complete_corpus_sha256=controls["prompt_order_sha256"],
    )

    two = deepcopy(one)
    two["completion"] = {
        "n_done": 2,
        "next_idx": 2,
        "complete_corpus_sha256": controls["prompt_order_sha256"],
        "controls_sha256": two["controls_sha256"],
        "checkpoint_sha256": checkpoint_sha,
        "lens_sha256": lens_sha,
        "prefix_checkpoint_sha256": prefix_checkpoint_sha,
        "prefix_progress_sha256": two["progress_sha256"],
    }
    two["completion_sha256"] = p05.sha256_bytes(
        p05.canonical_json_bytes(two["completion"])
    )
    p05.validate_f3_resume_binding(
        two,
        controls,
        n_done=2,
        next_idx=2,
        checkpoint_sha256=checkpoint_sha,
        expected_prompt_prefix_sha256=prefix_sha,
        expected_complete_corpus_sha256=controls["prompt_order_sha256"],
        lens_sha256=lens_sha,
        prefix_checkpoint_sha256=prefix_checkpoint_sha,
        expected_prefix_progress_sha256=two["progress_sha256"],
    )
    malformed_prefix = deepcopy(two)
    malformed_prefix["progress"]["prompt_prefix_count"] = 2
    malformed_prefix["progress_sha256"] = p05.sha256_bytes(
        p05.canonical_json_bytes(malformed_prefix["progress"])
    )
    malformed_prefix["completion"]["prefix_progress_sha256"] = malformed_prefix[
        "progress_sha256"
    ]
    malformed_prefix["completion_sha256"] = p05.sha256_bytes(
        p05.canonical_json_bytes(malformed_prefix["completion"])
    )
    with pytest.raises(p05.CheckpointValidationError):
        p05.validate_f3_resume_binding(
            malformed_prefix,
            controls,
            n_done=2,
            next_idx=2,
            checkpoint_sha256=checkpoint_sha,
            expected_prompt_prefix_sha256=prefix_sha,
            expected_complete_corpus_sha256=controls["prompt_order_sha256"],
            lens_sha256=lens_sha,
            prefix_checkpoint_sha256=prefix_checkpoint_sha,
            expected_prefix_progress_sha256=malformed_prefix["progress_sha256"],
        )


def test_f3_resume_binding_rejects_prefix_and_checkpoint_mismatch():
    controls = p05.make_checkpoint_controls(
        prompt_order_sha256="a" * 64,
        source_layers=[6, 13, 20],
        target_layer=27,
        dim_batch=1,
    )
    manifest = p05.make_checkpoint_manifest(controls)
    manifest["progress"] = {
        "n_done": 1,
        "next_idx": 1,
        "prompt_prefix_count": 1,
        "prompt_prefix_sha256": "b" * 64,
        "controls_sha256": manifest["controls_sha256"],
        "checkpoint": {"sha256": "c" * 64},
    }
    manifest["progress_sha256"] = p05.sha256_bytes(
        p05.canonical_json_bytes(manifest["progress"])
    )
    with pytest.raises(p05.CheckpointValidationError):
        p05.validate_f3_resume_binding(
            manifest,
            controls,
            n_done=1,
            next_idx=1,
            checkpoint_sha256="c" * 64,
            expected_prompt_prefix_sha256="e" * 64,
            expected_complete_corpus_sha256=controls["prompt_order_sha256"],
        )
    with pytest.raises(p05.CheckpointValidationError):
        p05.validate_f3_resume_binding(
            manifest,
            controls,
            n_done=1,
            next_idx=1,
            checkpoint_sha256="f" * 64,
            expected_prompt_prefix_sha256="b" * 64,
            expected_complete_corpus_sha256=controls["prompt_order_sha256"],
        )


def test_f3_complete_resume_rejects_corpus_and_lens_mismatch():
    controls = p05.make_checkpoint_controls(
        prompt_order_sha256="a" * 64,
        source_layers=[6, 13, 20],
        target_layer=27,
        dim_batch=1,
    )
    manifest = p05.make_checkpoint_manifest(controls)
    prefix_checkpoint_sha = "e" * 64
    manifest["progress"] = {
        "n_done": 1,
        "next_idx": 1,
        "prompt_prefix_count": 1,
        "prompt_prefix_sha256": "b" * 64,
        "controls_sha256": manifest["controls_sha256"],
        "checkpoint": {"sha256": prefix_checkpoint_sha},
    }
    manifest["progress_sha256"] = p05.sha256_bytes(
        p05.canonical_json_bytes(manifest["progress"])
    )
    manifest["completion"] = {
        "n_done": 2,
        "next_idx": 2,
        "complete_corpus_sha256": controls["prompt_order_sha256"],
        "controls_sha256": manifest["controls_sha256"],
        "checkpoint_sha256": "c" * 64,
        "lens_sha256": "d" * 64,
        "prefix_checkpoint_sha256": prefix_checkpoint_sha,
        "prefix_progress_sha256": manifest["progress_sha256"],
    }
    manifest["completion_sha256"] = p05.sha256_bytes(
        p05.canonical_json_bytes(manifest["completion"])
    )
    with pytest.raises(p05.CheckpointValidationError):
        p05.validate_f3_resume_binding(
            manifest,
            controls,
            n_done=2,
            next_idx=2,
            checkpoint_sha256="c" * 64,
            expected_prompt_prefix_sha256="b" * 64,
            expected_complete_corpus_sha256="e" * 64,
            lens_sha256="d" * 64,
            prefix_checkpoint_sha256=prefix_checkpoint_sha,
            expected_prefix_progress_sha256=manifest["progress_sha256"],
        )
    with pytest.raises(p05.CheckpointValidationError):
        p05.validate_f3_resume_binding(
            manifest,
            controls,
            n_done=2,
            next_idx=2,
            checkpoint_sha256="c" * 64,
            expected_prompt_prefix_sha256="b" * 64,
            expected_complete_corpus_sha256=controls["prompt_order_sha256"],
            lens_sha256="f" * 64,
            prefix_checkpoint_sha256=prefix_checkpoint_sha,
            expected_prefix_progress_sha256=manifest["progress_sha256"],
        )


def test_manifest_ordering_hash_and_corpus_order(tmp_path):
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    hidden = tmp_path / ".snapshot-staging"
    hidden.mkdir()
    (hidden / "partial.json").write_text("incomplete", encoding="utf-8")
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


def test_persistence_gate_requires_every_upload_and_final_manifest():
    awaiting = p05.persistence_summary([], configured=True)
    assert awaiting["ready"] is False
    assert awaiting["status"] == "awaiting_final_manifest_completion"

    final = {
        "stage_label": "final",
        "required": True,
        "status": "confirmed",
        "manifest_uploaded_last": True,
    }
    assert p05.persistence_summary([final], configured=True)["ready"] is True

    failed_stage = {
        "stage_label": "F3-prompt-1",
        "required": True,
        "status": "failed",
        "manifest_uploaded_last": False,
    }
    failed = p05.persistence_summary([failed_stage, final], configured=True)
    assert failed["ready"] is False
    assert failed["failure_class"] == "checkpoint_failure"
    assert p05.persistence_summary([], configured=False)["ready"] is True


def test_persistence_failure_blocks_green_after_real_f2():
    persistence = p05.persistence_summary(
        [
            {
                "stage_label": "final",
                "required": True,
                "status": "failed",
                "manifest_uploaded_last": False,
            }
        ],
        configured=True,
    )
    decision = p05.derive_decision(
        successful_results(),
        authorized_compatibility_fix_attempted=False,
        scaling_plan=executable_scaling(),
        persistence=persistence,
    )
    assert decision["decision"] == "AMBER"
    assert decision["gate_status"] == "BLOCKED"
    assert decision["persistence_failure_class"] == "checkpoint_failure"


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


def test_f4_requires_independent_fitted_and_reloaded_lenses(monkeypatch, tmp_path):
    monkeypatch.delenv("JSPACE_BLOB_ACCOUNT", raising=False)
    monkeypatch.delenv("JSPACE_BLOB_CONTAINER", raising=False)
    args = runner_module.parse_args(
        [
            "--output-dir",
            str(tmp_path),
            "--corpus",
            str(ROOT / "data" / "jlens_feasibility_prompts.jsonl"),
        ]
    )
    runner = runner_module.Phase05Runner(args)
    runner.layers = {"f3_source_layers": [6, 13, 20]}
    runner.fitted_lens = None
    runner.loaded_lens = object()
    with pytest.raises(p05.CheckpointValidationError):
        runner.run_f4()
    same = object()
    runner.fitted_lens = same
    runner.loaded_lens = same
    with pytest.raises(p05.CheckpointValidationError):
        runner.run_f4()


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


def test_f3_resumed_persistence_manifest_covers_current_artifacts(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("JSPACE_BLOB_ACCOUNT", raising=False)
    monkeypatch.delenv("JSPACE_BLOB_CONTAINER", raising=False)
    args = runner_module.parse_args(
        [
            "--output-dir",
            str(tmp_path),
            "--corpus",
            str(ROOT / "data" / "jlens_feasibility_prompts.jsonl"),
        ]
    )
    runner = runner_module.Phase05Runner(args)
    relative_paths = [
        "lens/phase05_jlens.pt",
        "checkpoint/phase05_jlens_f3_fit_checkpoint.pt",
        "checkpoint/phase05_jlens_f3_checkpoint.manifest.json",
        "checkpoint/phase05_jlens_f3_prompt1_checkpoint.pt",
        "checkpoint/phase05_jlens_f3_prompt1_checkpoint.manifest.json",
    ]
    for relative in relative_paths:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")
    assert runner.persist("F3-resumed") is True
    runner.assert_artifact_manifest_current(relative_paths)
    (tmp_path / relative_paths[0]).write_text("tampered", encoding="utf-8")
    with pytest.raises(p05.CheckpointValidationError):
        runner.assert_artifact_manifest_current(relative_paths)


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


def test_restore_falls_back_from_incomplete_n2_to_valid_prefix(tmp_path):
    records, corpus_sha = runner_module.load_corpus(
        ROOT / "data" / "jlens_feasibility_prompts.jsonl"
    )
    controls = p05.make_checkpoint_controls(
        prompt_order_sha256=corpus_sha,
        source_layers=[6, 13, 20],
        target_layer=27,
        dim_batch=1,
    )
    prefix_dir = tmp_path / "older-prefix"
    checkpoint_dir = prefix_dir / "checkpoint"
    checkpoint_dir.mkdir(parents=True)
    working = checkpoint_dir / "phase05_jlens_f3_fit_checkpoint.pt"
    durable = checkpoint_dir / "phase05_jlens_f3_prompt1_checkpoint.pt"
    state_1 = {
        "n_done": 1,
        "next_idx": 1,
        "source_layers": [6, 13, 20],
        "target_layer": 27,
        "skip_first": 16,
    }
    checkpoint_bytes = p05.canonical_json_bytes(state_1)
    working.write_bytes(checkpoint_bytes)
    durable.write_bytes(checkpoint_bytes)
    manifest = p05.make_checkpoint_manifest(controls)
    manifest["progress"] = {
        "n_done": 1,
        "next_idx": 1,
        "prompt_prefix_count": 1,
        "prompt_prefix_sha256": p05.canonical_jsonl_sha256(records[:1]),
        "controls_sha256": manifest["controls_sha256"],
        "checkpoint": {
            "path": "checkpoint/phase05_jlens_f3_prompt1_checkpoint.pt",
            "bytes": len(checkpoint_bytes),
            "sha256": p05.sha256_file(durable),
        },
    }
    manifest["progress_sha256"] = p05.sha256_bytes(
        p05.canonical_json_bytes(manifest["progress"])
    )
    for name in (
        "phase05_jlens_f3_checkpoint.manifest.json",
        "phase05_jlens_f3_prompt1_checkpoint.manifest.json",
    ):
        (checkpoint_dir / name).write_bytes(p05.canonical_json_bytes(manifest))

    incomplete_dir = tmp_path / "newer-incomplete-n2"
    shutil.copytree(prefix_dir, incomplete_dir)
    incomplete_working = (
        incomplete_dir / "checkpoint" / "phase05_jlens_f3_fit_checkpoint.pt"
    )
    incomplete_working.write_bytes(
        p05.canonical_json_bytes(
            {
                **state_1,
                "n_done": 2,
                "next_idx": 2,
            }
        )
    )

    selected = runner_module.select_semantically_valid_snapshot(
        [
            {
                "path": incomplete_dir,
                "source_prefix": "run/snapshots/009-F3-failed",
            },
            {
                "path": prefix_dir,
                "source_prefix": "run/snapshots/008-F3-prompt-1",
            },
        ],
        records,
        checkpoint_loader=lambda path: json.loads(path.read_text(encoding="utf-8")),
    )
    assert selected["source_prefix"].endswith("008-F3-prompt-1")
    assert selected["semantics"]["n_done"] == 1
    assert selected["fallback_used"] is True
    assert selected["rejected_newer_snapshots"][0]["source_prefix"].endswith(
        "009-F3-failed"
    )


def test_configured_upload_failure_never_returns_success(monkeypatch, tmp_path):
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
    runner.blob.account = "configured-account"
    runner.blob.container = "configured-container"

    def fail_upload(*_args, **_kwargs):
        raise RuntimeError("simulated upload failure")

    monkeypatch.setattr(runner.blob, "upload_snapshot", fail_upload)
    assert runner.run() == 6
    decision = json.loads(
        (tmp_path / "phase05_jlens_decision.json").read_text(encoding="utf-8")
    )
    assert decision["decision"] == "UNRATED"
    assert decision["gate_status"] == "BLOCKED"
    assert decision["persistence"]["status"] == "checkpoint_failure"
    assert "GREEN" not in (tmp_path / "phase05_jlens_report.md").read_text(
        encoding="utf-8"
    )


def test_final_manifest_snapshot_matches_local_outputs(monkeypatch, tmp_path):
    args = runner_module.parse_args(
        [
            "--output-dir",
            str(tmp_path),
            "--corpus",
            str(ROOT / "data" / "jlens_feasibility_prompts.jsonl"),
        ]
    )
    runner = runner_module.Phase05Runner(args)
    runner.blob.account = "configured-account"
    runner.blob.container = "configured-container"
    runner.results = successful_results()
    runner.scaling_plan = executable_scaling()
    captured = {}

    def successful_upload(output_dir, stage, sequence):
        files = runner.blob.snapshot_files(output_dir)
        captured.update(
            {
                path.relative_to(output_dir).as_posix(): path.read_bytes()
                for path in files
            }
        )
        return {
            "status": "uploaded",
            "uploaded": len(files),
            "prefix": runner.blob.snapshot_destination(stage, sequence),
            "manifest_uploaded_last": True,
        }

    monkeypatch.setattr(runner.blob, "upload_snapshot", successful_upload)
    assert runner.persist("final") is True
    assert runner.persistence_status()["final_manifest_completion_confirmed"] is True
    for relative, blob_bytes in captured.items():
        assert (tmp_path / relative).read_bytes() == blob_bytes
    assert not (tmp_path / ".snapshot-staging").exists()
    decision = json.loads(
        (tmp_path / "phase05_jlens_decision.json").read_text(encoding="utf-8")
    )
    assert decision["decision"] == "GREEN"


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
    assert "lens.save(str(temporary), dtype=torch_module.float32)" in source
    assert "torch_module.equal(raw_matrix, expected_matrix)" in source
    assert "lossless_reserialized_on_operational_retry" in source
    assert "F2 recomputation is forbidden" in source
    assert "F3 recomputation is forbidden" in source
    assert (
        "self.fitted_lens = self.jlens.JacobianLens.load(str(lens_path))"
        not in source
    )
    assert "rtol=5e-3, atol=5e-3" in source
    assert "prompts=prompts[:1]" in source
    assert 'self.persist("F3-prompt-1")' in source
    assert "phase05_jlens_f3_prompt1_checkpoint.pt" in source
    assert source.count("f3_segment_time_guard(") >= 2
    assert source.index('self.persist("F3-prompt-1")') < source.index(
        "segment_2_admission"
    )
    assert source.index("f3_memory_requires_stop") < source.index(
        'self.execute("F4"'
    )


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


def test_durable_claim_election_uses_server_time_before_random_name():
    prefix = "p05l-0123456789abcdef0123--"
    fixed = {
        "operation": "launch",
        "claimPrefix": prefix,
        "runId": "20260718T120000Z",
        "attempt": "primary",
        "primaryProjectSha": "a" * 40,
        "jobName": "job-jspace-p05-jlens",
    }
    early_name = prefix + "f" * 32
    late_name = prefix + "0" * 32
    dynamic = {
        "projectSha": "a" * 40,
        "imageDigest": "sha256:" + "b" * 64,
    }
    winner = claim_election.elect_claim(
        [
            deployment_claim(
                name=late_name,
                prefix=prefix,
                timestamp="2026-07-18T12:00:02Z",
                fixed=fixed,
                dynamic=dynamic,
            ),
            deployment_claim(
                name=early_name,
                prefix=prefix,
                timestamp="2026-07-18T12:00:01Z",
                fixed=fixed,
                dynamic=dynamic,
            ),
        ],
        prefix=prefix,
        fixed=fixed,
    )
    assert winner["name"] == early_name
    assert winner["candidate_count"] == 2


def test_claim_invocation_ids_are_cryptographic_and_unique(capsys):
    assert claim_election.main(["new-id"]) == 0
    first = capsys.readouterr().out.strip()
    assert claim_election.main(["new-id"]) == 0
    second = capsys.readouterr().out.strip()
    assert len(first) == len(second) == 32
    assert int(first, 16) >= 0
    assert first != second


def test_invocation_scratch_paths_are_isolated(tmp_path):
    first = claim_election.invocation_scratch_path(
        tmp_path, "build", "1" * 32
    )
    second = claim_election.invocation_scratch_path(
        tmp_path, "build", "2" * 32
    )
    launch = claim_election.invocation_scratch_path(
        tmp_path, "launch", "1" * 32
    )
    assert first.parent == second.parent == launch.parent == tmp_path.resolve()
    assert len({first, second, launch}) == 3
    assert first.name == ".p05-build-" + "1" * 32
    with pytest.raises(claim_election.ClaimValidationError):
        claim_election.invocation_scratch_path(tmp_path, "build", "../bad")


def test_earliest_failed_or_in_progress_claim_remains_blocking_winner():
    prefix = "p05b-0123456789abcdef0123--"
    fixed = {
        "operation": "build",
        "claimPrefix": prefix,
        "projectSha": "a" * 40,
        "imageRepository": "j-space-observation-jlens",
    }
    dynamic = {
        "buildRunId": "run-1",
        "imageDigest": "sha256:" + "b" * 64,
        "stagingTag": "staging-" + "a" * 40 + "-ticket",
    }
    failed = deployment_claim(
        name=prefix + "1" * 32,
        prefix=prefix,
        timestamp="2026-07-18T12:00:00Z",
        state="Failed",
        operation="build",
        fixed=fixed,
        dynamic=dynamic,
    )
    succeeded = deployment_claim(
        name=prefix + "2" * 32,
        prefix=prefix,
        timestamp="2026-07-18T12:00:01Z",
        operation="build",
        fixed=fixed,
        dynamic=dynamic | {"buildRunId": "run-2"},
    )
    winner = claim_election.elect_claim(
        [succeeded, failed], prefix=prefix, fixed=fixed
    )
    assert winner["name"] == failed["name"]
    assert winner["provisioning_state"] == "Failed"


@pytest.mark.parametrize("mutation", ["timestamp", "outputs", "duplicate", "provenance"])
def test_claim_election_rejects_invalid_or_ambiguous_ticket_sets(mutation):
    prefix = "p05l-fedcba9876543210fedc--"
    fixed = {
        "operation": "launch",
        "claimPrefix": prefix,
        "runId": "20260718T120000Z",
        "attempt": "operational-fix",
        "primaryProjectSha": "a" * 40,
        "jobName": "job-jspace-p05-jlens",
    }
    claim = deployment_claim(
        name=prefix + "3" * 32,
        prefix=prefix,
        timestamp="2026-07-18T12:00:00Z",
        fixed=fixed,
        dynamic={
            "projectSha": "c" * 40,
            "imageDigest": "sha256:" + "d" * 64,
        },
    )
    claims = [claim]
    if mutation == "timestamp":
        claim["properties"].pop("timestamp")
    elif mutation == "outputs":
        claim["properties"].pop("outputs")
    elif mutation == "duplicate":
        claims.append(deepcopy(claim))
    else:
        claim["properties"]["outputs"]["runId"]["value"] = "20260718T130000Z"
    with pytest.raises(claim_election.ClaimValidationError):
        claim_election.elect_claim(claims, prefix=prefix, fixed=fixed)


def test_global_primary_claim_blocks_a_different_run_id():
    prefix = "p05l-global-singleton--"
    earlier_fixed = {
        "operation": "launch",
        "claimPrefix": prefix,
        "runId": "20260718T120000Z",
        "attempt": "primary",
        "primaryProjectSha": "a" * 40,
        "jobName": "job-jspace-p05-jlens",
    }
    earlier = deployment_claim(
        name=prefix + "1" * 32,
        prefix=prefix,
        timestamp="2026-07-18T12:00:00Z",
        fixed=earlier_fixed,
        dynamic={
            "projectSha": "a" * 40,
            "imageDigest": "sha256:" + "b" * 64,
        },
    )
    later_fixed = {**earlier_fixed, "runId": "20260719T120000Z"}
    later = deployment_claim(
        name=prefix + "2" * 32,
        prefix=prefix,
        timestamp="2026-07-19T12:00:00Z",
        fixed=later_fixed,
        dynamic={
            "projectSha": "c" * 40,
            "imageDigest": "sha256:" + "d" * 64,
        },
    )
    with pytest.raises(claim_election.ClaimValidationError):
        claim_election.elect_claim(
            [earlier, later], prefix=prefix, fixed=later_fixed
        )


def test_launch_claim_requires_launcher_sha_provenance():
    prefix = "p05l-launcher-binding--"
    fixed = {
        "operation": "launch",
        "claimPrefix": prefix,
        "runId": "20260719T010000Z",
        "attempt": "primary",
        "primaryProjectSha": "a" * 40,
        "jobName": "job-jspace-p05-jlens",
    }
    claim = deployment_claim(
        name=prefix + "4" * 32,
        prefix=prefix,
        timestamp="2026-07-19T01:00:00Z",
        fixed=fixed,
        dynamic={
            "projectSha": "a" * 40,
            "imageDigest": "sha256:" + "b" * 64,
        },
    )
    claim["properties"]["outputs"].pop("launcherSha")
    with pytest.raises(claim_election.ClaimValidationError):
        claim_election.elect_claim([claim], prefix=prefix, fixed=fixed)


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
    assert "image_digest" in build
    assert "--write-enabled false" in build
    assert "--delete-enabled false" in build
    assert "immutability_verified" in build
    assert "2>/dev/null" not in build
    assert "|| true" not in build
    assert "STAGING_IMAGE_TAG" in build
    assert "--image \"$STAGING_IMAGE_TAG\"" in build
    assert "RUN_OUTPUT_DIGEST" in build
    assert "require_confirmed_absence" in build
    assert "az acr import" in build
    assert "--force" not in build
    assert "phase05_claim_election.py" in build
    assert "az deployment group list" in build
    assert "CLAIM_SETTLE_SECONDS" in build
    assert "FIRST_WINNER_TIME" in build
    assert "SECOND_WINNER_TIME" in build
    assert "winner changed before promotion" in build
    assert "claim_deployment_retained" in build
    assert 'SCRATCH_DIR="$(python "$CLAIM_HELPER" scratch-path' in build
    assert 'rm -rf "$SCRATCH_DIR"' in build
    assert "$RECORD_DIR/.azure_phase05_jlens" not in build
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
    assert "PRIMARY_PROJECT_SHA" in run
    assert "PRIMARY_EXECUTION_STATUS" in run
    assert "properties.provisioningState" in run
    assert '"image": "$IMAGE_DIGEST_REF"' in run
    assert "IMAGE_TAG_REF" in run
    assert "IMAGE_DIGEST_REF" in run
    assert "A succeeded primary execution must never be retried" in run
    assert "JSPACE_PHASE05_RUN_ID" in run
    assert "JSPACE_ATTEMPT_ID" in run
    assert '"primary-project-sha"' in run
    assert run.index("properties.provisioningState") < run.index(
        "az containerapp job start"
    )
    assert "LAUNCH_INVOCATION_ID" in run
    assert '"launch-state": "claimed-for-start"' in run
    assert '"launch-invocation-id": "$LAUNCH_INVOCATION_ID"' in run
    assert "phase05_claim_election.py" in run
    assert "az deployment group list" in run
    assert "CLAIM_SETTLE_SECONDS" in run
    assert "FIRST_WINNER_TIME" in run
    assert "SECOND_WINNER_TIME" in run
    assert "Durable launch winner changed before start" in run
    assert "verify_claimed_job" in run
    assert run.index("PRESTART_WINNER_NAME") < run.index(
        "az containerapp job start"
    )
    assert "STARTED_EXECUTION_COUNT" in run
    assert "execution_name_verified" in run
    assert 'SCRATCH_DIR="$(python "$CLAIM_HELPER" scratch-path' in run
    assert 'rm -rf "$SCRATCH_DIR"' in run
    assert "$RECORD_DIR/.azure_phase05_jlens" not in run
    assert '"${JOB_NAME}|primary"' in run
    assert '"${JOB_NAME}|operational-fix"' in run
    assert '"${RUN_ID}|${ATTEMPT_KIND}"' not in run

    def continued_commands(source, prefixes):
        command = []
        for line in source.splitlines():
            stripped = line.strip()
            if not command:
                matching_prefix = next(
                    (prefix for prefix in prefixes if prefix in stripped),
                    None,
                )
                if matching_prefix is None:
                    continue
                stripped = stripped[stripped.index(matching_prefix) :]
            if command or stripped:
                command.append(stripped.rstrip("\\").strip())
                if not stripped.endswith("\\"):
                    yield " ".join(command)
                    command = []

    repository_commands = [
        *continued_commands(build, ("az acr repository ",)),
        *continued_commands(run, ("az acr repository ",)),
    ]
    assert repository_commands
    assert all("--resource-group" not in command for command in repository_commands)
    attribute_commands = [
        *continued_commands(
            build,
            ("az acr repository show ", "az acr manifest show-metadata "),
        ),
        *continued_commands(
            run,
            ("az acr repository show ", "az acr manifest show-metadata "),
        ),
    ]
    assert len(attribute_commands) == 12
    assert all(
        "--query changeableAttributes.writeEnabled" in command
        or "--query changeableAttributes.deleteEnabled" in command
        for command in attribute_commands
    )
    assert build.rindex("cleanup_own_staging") < build.index(
        "az acr repository update"
    )
    assert "JLENS_FINALIZE_EXISTING_BUILD" in build
    assert 'cat-file -e "${PROJECT_SHA}^{commit}"' in build
    assert 'cat-file blob \\' in build
    assert '"finalize_existing_build": True' in build
    assert '"acr_build_skipped": True' in build
    assert '"image_import_skipped": True' in build
    assert '"new_claim_skipped": True' in build
    assert '"unlock_performed": False' in build
    assert '"source_hash_mode": "historical_git_objects"' in build
    assert '"staging_tag_removed": "$STAGING_TAG_REMOVED" == "true"' in build
    assert "staging_tag_retained_immutable" in build
    assert build.index('if [[ "$FINALIZE_EXISTING_BUILD" == "true" ]]') < build.index(
        'echo "[RUN] Building staging image'
    )
    assert 'LAUNCHER_SHA="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"' in run
    assert '"image-project-sha": "$PROJECT_SHA"' in run
    assert '"launcher-sha": "$LAUNCHER_SHA"' in run
    assert '"launcherSha": launcher_sha' in run
    assert '"image_project_sha": "$PROJECT_SHA"' in run
    assert '"launcher_sha": "$LAUNCHER_SHA"' in run
    assert 'Path("$' not in build
    assert 'Path("$' not in run
    assert build.count("Path(sys.argv[1]).write_text(") == 2
    assert run.count("Path(sys.argv[1]).write_text(") == 2
    assert "az containerapp job list \\" in run
    assert 'JOB_LIST_FILE="$SCRATCH_DIR/job_list.json"' in run
    assert 'record.get("name") == sys.argv[2]' in run
    assert "providers/Microsoft.App/jobs?api-version" not in run
    assert "python - \"$EXISTING_JOB_FILE\" <<'PY' | tr -d '\\r'" in run
    for unsupported in ("If-Match", "If-None-Match", "etag", "ETAG", "ETag"):
        assert unsupported not in build
        assert unsupported not in run
    assert '"volumes"' not in run
    assert '"secrets"' not in run


def test_finalize_existing_build_is_read_only_and_historical():
    build = (
        ROOT / "infra" / "azure" / "scripts" / "07_build_phase05_jlens.sh"
    ).read_text(encoding="utf-8")
    start = build.index('if [[ "$FINALIZE_EXISTING_BUILD" == "true" ]]')
    end = build.index("\nfi\n\nrequire_confirmed_absence", start)
    finalize = build[start:end]
    for forbidden in (
        "az acr build",
        "az acr import",
        "az acr repository update",
        "az acr repository untag",
        "--method put",
    ):
        assert forbidden not in finalize
    assert "az deployment group list" in finalize
    assert "outputs.buildRunId" in finalize
    assert "outputs.imageDigest" in finalize
    assert "outputs.stagingTag" in finalize
    assert "changeableAttributes.writeEnabled" in finalize
    assert "changeableAttributes.deleteEnabled" in finalize
    assert 'cat-file blob \\' in finalize
    assert '"finalize_existing_build": True' in finalize
    assert '"staging_tag_retained_immutable"' in finalize
    assert "exit 0" in finalize


def test_checked_corpus_is_small_generic_and_canonically_hashed():
    records, digest = runner_module.load_corpus(
        ROOT / "data" / "jlens_feasibility_prompts.jsonl"
    )
    assert len(records) == 2
    assert len(digest) == 64
    assert digest == p05.canonical_jsonl_sha256(records)
    assert all(set(record) == {"id", "text"} for record in records)
