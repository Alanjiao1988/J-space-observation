"""Tests for the Phase 1.0D generation driver.

Nothing here loads a model.  The point of these tests is the boundary between a
run that produced generations and a run that is allowed to report a result: the
authority forbids an automatic evaluator from deciding correctness, so a
generation-only pack must be structurally incapable of carrying a headroom
number.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation.phase1_0d_confirmation import (
    ARMS,
    RUN_BASE_SEED,
    Phase1_0DError,
)
from jspace_observation.phase1_0d_execution import (
    SelfTestBackend,
    build_records,
    compute_cell_outcomes,
    plan_work_units,
)
from jspace_observation.phase1_0d_generation import (
    AWAITING_REVIEW,
    MANIFEST_NAME,
    MODES,
    GenerationTelemetry,
    Phase1_0DRunError,
    RunConfig,
    TransformersBackend,
    describe_backend,
    run_generations,
    run_phase1_0d,
    runtime_environment,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _config(tmp_path: Path, mode: str, **overrides) -> RunConfig:
    settings = {
        "mode": mode,
        "output_root": tmp_path / "pack",
        "repo_root": REPO_ROOT,
        "run_id": "20260802T000000Z",
    }
    settings.update(overrides)
    return RunConfig(**settings)


def _pack(tmp_path: Path, mode: str, **overrides) -> Path:
    result = run_phase1_0d(_config(tmp_path, mode, **overrides))
    return Path(result["output_dir"])


class _ExplodingBackend:
    is_real_model = False
    name = "exploding_backend"

    def generate(self, unit):
        raise RuntimeError("device fell over")


class _ClaimsToBeReal:
    is_real_model = True
    name = "liar"

    def generate(self, unit):
        raise AssertionError("must never be called")


# --------------------------------------------------------------------------
# Mode discipline
# --------------------------------------------------------------------------


def test_the_registered_modes_are_exactly_these_four():
    assert MODES == ("plan", "self-test", "generate", "finalize")


def test_an_unregistered_mode_is_refused(tmp_path):
    with pytest.raises(Phase1_0DRunError):
        run_phase1_0d(_config(tmp_path, "score-it-yourself"))


def test_generate_refuses_a_fabricated_backend(tmp_path):
    with pytest.raises(Phase1_0DRunError, match="real model backend"):
        run_phase1_0d(
            _config(
                tmp_path,
                "generate",
                code_commit="0" * 40,
                image_digest="sha256:" + "a" * 64,
                backend=SelfTestBackend(),
            )
        )


def test_generate_refuses_an_unrecorded_commit(tmp_path):
    with pytest.raises(Phase1_0DRunError, match="code commit"):
        run_phase1_0d(_config(tmp_path, "generate", backend=_ClaimsToBeReal()))


def test_generate_refuses_an_unrecorded_image(tmp_path):
    with pytest.raises(Phase1_0DRunError, match="image digest"):
        run_phase1_0d(
            _config(
                tmp_path,
                "generate",
                code_commit="0" * 40,
                backend=_ClaimsToBeReal(),
            )
        )


def test_self_test_refuses_to_run_the_real_model(tmp_path):
    with pytest.raises(Phase1_0DRunError, match="must not run the real model"):
        run_phase1_0d(_config(tmp_path, "self-test", backend=_ClaimsToBeReal()))


def test_finalize_refuses_without_records_and_judgments(tmp_path):
    with pytest.raises(Phase1_0DRunError, match="records"):
        run_phase1_0d(_config(tmp_path, "finalize"))


# --------------------------------------------------------------------------
# The plan pack
# --------------------------------------------------------------------------


def test_plan_emits_the_protocol_and_every_rendered_prompt(tmp_path):
    directory = _pack(tmp_path, "plan")
    snapshot = json.loads((directory / "00_protocol_snapshot.json").read_text("utf-8"))
    selection = json.loads((directory / "01_selection.json").read_text("utf-8"))

    assert snapshot["protocol_sha256"]
    assert selection["item_count"] == snapshot["expected_item_count"]
    assert selection["work_unit_count"] == selection["item_count"] * len(ARMS)
    assert len(selection["prompts"]) == selection["work_unit_count"]


def test_plan_writes_no_records_and_no_decision(tmp_path):
    directory = _pack(tmp_path, "plan")
    names = {path.name for path in directory.iterdir()}
    assert "02_records.jsonl" not in names
    assert "05_decision.json" not in names


def test_the_plan_seed_is_the_registered_run_seed(tmp_path):
    directory = _pack(tmp_path, "plan")
    selection = json.loads((directory / "01_selection.json").read_text("utf-8"))
    assert selection["provenance"]["run_base_seed"] == RUN_BASE_SEED


# --------------------------------------------------------------------------
# The generation pack
# --------------------------------------------------------------------------


def test_a_generation_pack_reports_no_result(tmp_path):
    directory = _pack(
        tmp_path,
        "generate",
        code_commit="0" * 40,
        image_digest="sha256:" + "a" * 64,
        backend=_RealEnoughBackend(),
    )
    decision = json.loads((directory / "05_decision.json").read_text("utf-8"))
    assert decision["result"] == AWAITING_REVIEW
    assert "rq2_pilot_candidates" not in decision
    assert "cells" not in decision


def test_a_generation_pack_carries_one_review_row_per_record(tmp_path):
    directory = _pack(
        tmp_path,
        "generate",
        code_commit="0" * 40,
        image_digest="sha256:" + "a" * 64,
        backend=_RealEnoughBackend(),
    )
    records = (directory / "02_records.jsonl").read_text("utf-8").splitlines()
    form = (directory / "03_review_form.jsonl").read_text("utf-8").splitlines()
    assert len(form) == len(records)


def test_the_review_form_never_shows_the_reviewer_the_parser_route(tmp_path):
    directory = _pack(
        tmp_path,
        "generate",
        code_commit="0" * 40,
        image_digest="sha256:" + "a" * 64,
        backend=_RealEnoughBackend(),
    )
    for line in (directory / "03_review_form.jsonl").read_text("utf-8").splitlines():
        row = json.loads(line)
        assert "triage" not in row
        assert "route" not in row


def test_the_summary_states_that_no_headroom_number_exists(tmp_path):
    directory = _pack(
        tmp_path,
        "generate",
        code_commit="0" * 40,
        image_digest="sha256:" + "a" * 64,
        backend=_RealEnoughBackend(),
    )
    summary = (directory / "09_summary.md").read_text("utf-8")
    assert AWAITING_REVIEW in summary
    assert "no** cell metric" in summary


def test_a_generation_pack_does_not_preselect_the_secondary_review(tmp_path):
    """Secondary selection is defined by the primary label, so it cannot exist yet."""

    directory = _pack(
        tmp_path,
        "generate",
        code_commit="0" * 40,
        image_digest="sha256:" + "a" * 64,
        backend=_RealEnoughBackend(),
    )
    for line in (directory / "02_records.jsonl").read_text("utf-8").splitlines():
        evaluation = json.loads(line)["evaluation"]
        assert evaluation["primary_label"] is None
        assert evaluation["secondary_review_required"] is None


# --------------------------------------------------------------------------
# The manifest
# --------------------------------------------------------------------------


def test_the_manifest_hashes_every_emitted_file_including_itself(tmp_path):
    directory = _pack(tmp_path, "self-test")
    manifest = json.loads((directory / MANIFEST_NAME).read_text("utf-8"))
    names = {entry["name"] for entry in manifest["files"]}
    on_disk = {path.name for path in directory.iterdir()}
    assert names == on_disk - {MANIFEST_NAME}
    assert manifest["manifest_written_last"] is True


def test_every_manifest_digest_matches_the_file_on_disk(tmp_path):
    from hashlib import sha256

    directory = _pack(tmp_path, "self-test")
    manifest = json.loads((directory / MANIFEST_NAME).read_text("utf-8"))
    for entry in manifest["files"]:
        data = (directory / entry["name"]).read_bytes()
        assert sha256(data).hexdigest() == entry["sha256"], entry["name"]


# --------------------------------------------------------------------------
# Generation failures are rows, not silence
# --------------------------------------------------------------------------


def test_a_failed_generation_still_produces_a_row(tmp_path):
    selected = _selected()
    units = plan_work_units(selected[:2], base_seed=RUN_BASE_SEED)
    outputs, telemetry = run_generations(units, _ExplodingBackend())

    assert len(outputs) == len(units)
    assert all(item.error for item in telemetry)
    assert all(outputs[unit.record_id].output_text == "" for unit in units)


def test_a_failed_generation_is_counted_not_hidden(tmp_path):
    directory = _pack(
        tmp_path,
        "generate",
        code_commit="0" * 40,
        image_digest="sha256:" + "a" * 64,
        backend=_ExplodingRealBackend(),
    )
    summary = json.loads((directory / "04_generation_summary.json").read_text("utf-8"))
    assert summary["failed_generations"] == summary["generations"]
    assert summary["failed_record_ids"]


def test_an_unlabelled_row_cannot_become_a_cell_metric():
    selected = _selected()
    units = plan_work_units(selected[:3], base_seed=RUN_BASE_SEED)
    backend = SelfTestBackend()
    outputs = {unit.record_id: backend.generate(unit) for unit in units}
    records = build_records(units, outputs)

    with pytest.raises(Phase1_0DError, match="no semantic final label"):
        compute_cell_outcomes(records)


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


def test_the_backend_description_records_whether_a_model_ran():
    assert describe_backend(SelfTestBackend())["is_real_model"] is False
    assert describe_backend(_RealEnoughBackend())["is_real_model"] is True


def test_the_runtime_environment_reports_what_it_could_not_import():
    environment = runtime_environment()
    assert environment["python_version"]
    assert "torch_version" in environment
    assert "transformers_version" in environment


def test_the_transformers_backend_declares_itself_real():
    assert TransformersBackend.is_real_model is True
    assert TransformersBackend.name == "phase1_0d_transformers_causal_lm_v1"


def test_telemetry_serializes_to_the_registered_fields():
    row = GenerationTelemetry(record_id="r", backend="b").as_dict()
    assert set(row) == {
        "record_id",
        "backend",
        "prompt_token_count",
        "output_token_count",
        "wall_seconds",
        "error",
    }


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def _selected():
    from jspace_observation.phase1_0d_generation import selection_and_snapshot

    selected, _ = selection_and_snapshot(
        RunConfig(mode="plan", output_root=Path("."), repo_root=REPO_ROOT)
    )
    return selected


class _RealEnoughBackend(SelfTestBackend):
    """A fabricated backend that is *declared* real, for structure tests only.

    It exists so the pack shape of a generate run can be tested without a GPU.
    Its outputs are fixtures and carry no scientific content, which is exactly
    why the pack it produces reports no result.
    """

    is_real_model = True
    name = "structure_test_backend"


class _ExplodingRealBackend(_RealEnoughBackend):
    name = "exploding_structure_test_backend"

    def generate(self, unit):
        raise RuntimeError("device fell over")
