"""Tests for the exact host-side P0-R2 ACR submission seam."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
P0_R2_DIR = ROOT / "studies" / "study3" / "pilot" / "p0_r2"
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))


def _load(name):
    path = P0_R2_DIR / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTEXT = _load("p0_r2_submission_context")
SUBMIT = _load("p0_r2_acr_submission")

TASK_PATH = "ops/task.yaml"


def _run(cwd, *args):
    return subprocess.run(
        list(args), cwd=str(cwd), check=True, capture_output=True,
        text=True).stdout.strip()


@pytest.fixture()
def admitted(tmp_path):
    root = tmp_path / "source"
    (root / "ops").mkdir(parents=True)
    (root / TASK_PATH).write_text("version: v1.1.0\n")
    _run(root, "git", "init", "-q")
    _run(root, "git", "config", "user.name", "P0-R2 Test")
    _run(root, "git", "config", "user.email", "p0-r2@example.invalid")
    _run(root, "git", "add", "ops/task.yaml")
    _run(root, "git", "commit", "-qm", "fixture")
    commit = _run(root, "git", "rev-parse", "HEAD")
    context_dir = tmp_path / "operation" / "acrctx"
    CONTEXT.build(root, context_dir, commit, TASK_PATH)
    admission = CONTEXT.verify(
        root, context_dir, expected_commit=commit,
        expected_task_path=TASK_PATH)
    admission_path = tmp_path / "operation" / "admission.json"
    CONTEXT.write_receipt(admission_path, admission, context_dir)
    task_blob = admission["context"]["task"]["git_blob"]
    return {
        "root": root, "commit": commit, "context": context_dir,
        "admission": admission_path, "task_blob": task_blob,
        "work": tmp_path / "submission",
        "image": "example.azurecr.io/p0-r2@sha256:" + "1" * 64,
        "digest": "sha256:" + "1" * 64,
        "anchor": "2" * 40,
    }


def _completed(stdout, code=0, stderr=b""):
    return subprocess.CompletedProcess(
        args=[], returncode=code, stdout=stdout, stderr=stderr)


def _kwargs(admitted, mode, attempt, runner, canary=None):
    return {
        "root": admitted["root"],
        "source_commit": admitted["commit"],
        "task_path": TASK_PATH,
        "context_dir": admitted["context"],
        "context_admission": admitted["admission"],
        "work_dir": admitted["work"],
        "registry": "exampleacr",
        "subscription": "00000000-0000-0000-0000-000000000000",
        "image": admitted["image"],
        "digest": admitted["digest"],
        "ready_anchor": admitted["anchor"],
        "mode": mode,
        "attempt": attempt,
        "packing_canary_receipt": canary,
        "runner": runner,
        "azure_cli_version": {"azure-cli": "test"},
    }


def test_packing_canary_captures_one_run_and_exact_logs(admitted):
    calls = []
    raw = (b"Packing source code into tar to upload...\nRun ID: cmtest1\n" +
           b"P0_R2_PACKING_CANARY_COMPLETE=1\n" +
           b"P0_R2_REPLAY_GATE_RUN=false\n" +
           b"P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=false\n" +
           b"P0_R2_MODEL_OPERATIONS_PERFORMED=0\n")

    def runner(command, cwd):
        calls.append((command, cwd))
        return _completed(raw, stderr=b"packer warning\n")

    receipt = SUBMIT.submit(**_kwargs(
        admitted, "packing-canary", "p0r2-g1-packing-canary-test", runner))
    assert receipt["outcome"] == "PASS"
    assert receipt["acr_run_id"] == "cmtest1"
    assert receipt["one_shot_envelope_consumed"] is False
    assert (admitted["work"] / SUBMIT.RAW_LOG_NAME).read_bytes() == raw
    assert (admitted["work"] / SUBMIT.STDERR_NAME).read_bytes() == \
        b"packer warning\n"
    command, cwd = calls[0]
    assert command[command.index("--file") + 1] == "task.yaml"
    assert command[-1] == str(admitted["context"].resolve())
    assert cwd == admitted["context"].resolve()


def test_context_defect_refuses_before_runner(admitted):
    called = []
    (admitted["context"] / "full-repository-file").write_text("forbidden")
    with pytest.raises(SUBMIT.SubmissionDefect, match="context"):
        SUBMIT.submit(**_kwargs(
            admitted, "packing-canary", "p0r2-g1-packing-canary-test",
            lambda command, cwd: called.append(command)))
    assert called == []
    assert not admitted["work"].exists()


@pytest.mark.parametrize("raw", [
    b"no run id\nP0_R2_PACKING_CANARY_COMPLETE=1\n",
    b"Run ID: cmone\nRun ID: cmtwo\n",
])
def test_missing_or_ambiguous_run_id_refuses(admitted, raw):
    with pytest.raises(SUBMIT.SubmissionDefect, match="run-id"):
        SUBMIT.submit(**_kwargs(
            admitted, "packing-canary", "p0r2-g1-packing-canary-test",
            lambda command, cwd: _completed(raw)))
    receipt = json.loads(
        (admitted["work"] / SUBMIT.RECEIPT_NAME).read_text())
    assert receipt["outcome"] == "STOP"
    assert receipt["acr_run_id"] is None
    assert "run-id" in receipt["failure_detail"]


def test_failed_azure_cli_retains_stop_receipt_and_logs(admitted):
    with pytest.raises(SUBMIT.SubmissionDefect, match="stopped"):
        SUBMIT.submit(**_kwargs(
            admitted, "packing-canary", "p0r2-g1-packing-canary-test",
            lambda command, cwd: _completed(
                b"", code=1, stderr=b"local packing failed\n")))
    receipt = json.loads(
        (admitted["work"] / SUBMIT.RECEIPT_NAME).read_text())
    assert receipt["outcome"] == "STOP"
    assert receipt["acr_run_id"] is None
    assert receipt["one_shot_envelope_consumed"] is False
    assert receipt["model_operations_performed"] == 0


def test_local_cli_exception_retains_zero_operation_stop(admitted):
    def missing_cli(command, cwd):
        raise FileNotFoundError("az is unavailable")

    with pytest.raises(SUBMIT.SubmissionDefect, match="az is unavailable"):
        SUBMIT.submit(**_kwargs(
            admitted, "packing-canary", "p0r2-g1-packing-canary-test",
            missing_cli))
    receipt = json.loads(
        (admitted["work"] / SUBMIT.RECEIPT_NAME).read_text())
    assert receipt["exit_code"] == 127
    assert receipt["outcome"] == "STOP"
    assert receipt["acr_run_id"] is None
    assert receipt["one_shot_envelope_consumed"] is False


def test_missing_canary_marker_retains_stop_receipt(admitted):
    raw = b"Run ID: cmnomarker\n"
    with pytest.raises(SUBMIT.SubmissionDefect, match="marker"):
        SUBMIT.submit(**_kwargs(
            admitted, "packing-canary", "p0r2-g1-packing-canary-test",
            lambda command, cwd: _completed(raw)))
    receipt = json.loads(
        (admitted["work"] / SUBMIT.RECEIPT_NAME).read_text())
    assert receipt["outcome"] == "STOP"
    assert receipt["acr_run_id"] == "cmnomarker"
    assert "marker" in receipt["failure_detail"]


def test_live_requires_passing_same_binding_canary(admitted):
    called = []
    with pytest.raises(SUBMIT.SubmissionDefect, match="requires"):
        SUBMIT.submit(**_kwargs(
            admitted, "live", "p0r2-g1-live-test",
            lambda command, cwd: called.append(command)))
    assert called == []


def test_live_accepts_only_exact_final_canary_binding(admitted, tmp_path):
    canary = {
        "schema_version": SUBMIT.SCHEMA_VERSION,
        "mode": "packing-canary",
        "outcome": "PASS",
        "exit_code": 0,
        "acr_run_id": "cmcanary",
        "binding": {
            "source_commit": admitted["commit"],
            "task_blob": admitted["task_blob"],
            "image": admitted["image"],
            "digest": admitted["digest"],
        },
        "replay_gate_ran": False,
        "one_shot_envelope_consumed": False,
        "model_operations_performed": 0,
    }
    canary_path = tmp_path / "packing_canary.json"
    canary_path.write_text(json.dumps(canary) + "\n")
    raw = b"Run ID: cmlive1\nP0_R2_REPLAY_ENVELOPE_BEGIN=1\n"
    receipt = SUBMIT.submit(**_kwargs(
        admitted, "live", "p0r2-g1-live-test",
        lambda command, cwd: _completed(raw), canary=canary_path))
    assert receipt["outcome"] == "PASS"
    assert receipt["acr_run_id"] == "cmlive1"
    assert receipt["one_shot_envelope_consumed"] is True
    assert receipt["authorizes_model_pilot"] is False

    admitted["work"] = tmp_path / "foreign-submission"
    canary["binding"]["digest"] = "sha256:" + "3" * 64
    canary_path.write_text(json.dumps(canary) + "\n")
    with pytest.raises(SUBMIT.SubmissionDefect, match="digest"):
        SUBMIT.submit(**_kwargs(
            admitted, "live", "p0r2-g1-live-test",
            lambda command, cwd: _completed(raw), canary=canary_path))


def test_cli_requires_explicit_confirmation(admitted):
    completed = subprocess.run(
        [sys.executable, str(P0_R2_DIR / "p0_r2_acr_submission.py"),
         "--packing-canary"], capture_output=True, text=True, check=False)
    assert completed.returncode == 2
    assert "--i-am-sure" in completed.stderr


def test_submission_module_is_model_free():
    source = (P0_R2_DIR / "p0_r2_acr_submission.py").read_text()
    assert "import torch" not in source
    assert "import transformers" not in source
    assert "containerapp job start" not in source
