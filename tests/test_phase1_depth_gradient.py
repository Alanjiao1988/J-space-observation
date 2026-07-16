"""Model-free tests for prospective Phase 1 experiment routing."""

import pytest

from experiments import phase1_depth_gradient as experiment


def _forbidden(*_args, **_kwargs):
    raise AssertionError("dry-run crossed an execution side-effect boundary")


def test_strict_answer_only_prompt_is_model_independent_and_has_no_think_tags():
    for _model_name in (
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        "Qwen/Qwen2.5-Math-1.5B",
    ):
        prompt, method, metadata, token_ids = experiment.prepare_condition_prompt(
            "strict_answer_only",
            "What is 2+2?",
            tokenizer=_forbidden,
        )
        assert "<think>" not in prompt
        assert "</think>" not in prompt
        assert method == "answer_only_prompt"
        assert metadata == {}
        assert token_ids is None


def test_stopped_and_postprocessed_conditions_start_from_prompt_only_input():
    for condition in (
        "strict_answer_only_stopped",
        "strict_answer_only_postprocessed",
    ):
        prompt, method, metadata, token_ids = experiment.prepare_condition_prompt(
            condition,
            "What is 2+2?",
        )
        assert "<think>" not in prompt
        assert not prompt.endswith("Answer:")
        assert method == "answer_only_prompt"
        assert metadata == {}
        assert token_ids is None


def test_unknown_condition_fails_before_run_directory_or_execution(
    monkeypatch,
    tmp_path,
):
    output_dir = tmp_path / "must-not-exist"
    monkeypatch.setattr(experiment, "generate_all_pilot_prompt_sets", _forbidden)
    monkeypatch.setattr(experiment, "ExperimentConfig", _forbidden)
    monkeypatch.setattr(experiment, "load_model_and_tokenizer", _forbidden)
    monkeypatch.setattr(experiment, "upload_directory_to_blob", _forbidden)

    with pytest.raises(SystemExit) as exc_info:
        experiment.main(
            [
                "--conditions",
                "strict_answer_only,unknown_condition",
                "--output-dir",
                str(output_dir),
            ]
        )

    assert exc_info.value.code == 2
    assert not output_dir.exists()


def test_dry_run_enumerates_v2_without_execution_side_effects(
    monkeypatch,
    tmp_path,
    capsys,
):
    output_dir = tmp_path / "must-not-exist"
    monkeypatch.setattr(experiment, "ExperimentConfig", _forbidden)
    monkeypatch.setattr(experiment, "RunLogger", _forbidden)
    monkeypatch.setattr(experiment, "load_model_and_tokenizer", _forbidden)
    monkeypatch.setattr(experiment, "run_generation", _forbidden)
    monkeypatch.setattr(experiment, "upload_directory_to_blob", _forbidden)

    conditions = (
        "strict_answer_only,"
        "strict_answer_only_prefill_answer,"
        "strict_answer_only_empty_think_prefill,"
        "strict_answer_only_stopped,"
        "strict_answer_only_postprocessed,"
        "visible_cot,"
        "r1_style_thinking"
    )
    experiment.main(
        [
            "--dry-run",
            "--models",
            "model-a,model-b",
            "--task-families",
            "arithmetic",
            "--depths",
            "1",
            "--conditions",
            conditions,
            "--items-per-cell",
            "1",
            "--output-dir",
            str(output_dir),
        ]
    )

    output = capsys.readouterr().out
    assert "Branch taxonomy: v2" in output
    assert (
        "strict_answer_only: legacy=raw_strict, "
        "prospective=prompt_only_raw_strict"
    ) in output
    assert (
        "strict_answer_only_empty_think_prefill: legacy=unclassified, "
        "prospective=prefill_intervention"
    ) in output
    assert "[DRY RUN] Conditions: 7" in output
    assert "[DRY RUN] Not running actual experiments" in output
    assert not output_dir.exists()
