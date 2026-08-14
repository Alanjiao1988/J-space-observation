"""Executable tests for P0-R2's host-to-ACR context boundary."""

from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (ROOT / "studies" / "study3" / "pilot" / "p0_r2" /
               "p0_r2_submission_context.py")
SPEC = importlib.util.spec_from_file_location("p0_r2_submission_context", MODULE_PATH)
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)

TASK_PATH = "ops/p0_r2_acr_task_v1.yaml"
LOCK_PATH = "ops/p0_r2_execution_lock_v1.json"


def _run(cwd, *args):
    completed = subprocess.run(
        list(args), cwd=str(cwd), check=True, capture_output=True, text=True)
    return completed.stdout.strip()


@pytest.fixture()
def source_repo(tmp_path):
    root = tmp_path / "source"
    (root / "ops").mkdir(parents=True)
    (root / TASK_PATH).write_bytes(
        b"version: v1.1.0\nsteps:\n  - id: replay\n")
    (root / LOCK_PATH).write_bytes(
        b'{"schema_version":"synthetic-p0-r2-lock"}\n')
    _run(root, "git", "init", "-q")
    _run(root, "git", "config", "user.name", "P0-R2 Test")
    _run(root, "git", "config", "user.email", "p0-r2@example.invalid")
    _run(root, "git", "add", "ops")
    _run(root, "git", "commit", "-qm", "fixture")
    return root, _run(root, "git", "rev-parse", "HEAD")


def _built(source_repo, tmp_path):
    root, commit = source_repo
    context_dir = tmp_path / "work" / "acrctx"
    CONTEXT.build(
        root, context_dir, commit, TASK_PATH,
        embedded_objects={"execution_lock": LOCK_PATH})
    return root, commit, context_dir


def test_builds_exact_two_file_context_from_git_objects(source_repo, tmp_path):
    root, commit, context_dir = _built(source_repo, tmp_path)
    receipt = CONTEXT.verify(
        root, context_dir, expected_commit=commit,
        expected_task_path=TASK_PATH, os_name="posix", environ={})
    assert sorted(path.name for path in context_dir.iterdir()) == [
        "context_manifest.json", "task.yaml"]
    assert (context_dir / "task.yaml").read_bytes() == \
        _run(root, "git", "show", "%s:%s" % (commit, TASK_PATH)).encode() + b"\n"
    assert receipt["outcome"] == "PASS"
    assert receipt["context"]["entry_count"] == 2
    assert receipt["model_operations_performed"] == 0
    manifest = json.loads((context_dir / "context_manifest.json").read_text())
    embedded = manifest["embedded_governance_objects"][0]
    assert base64.b64decode(embedded["payload"]) == (root / LOCK_PATH).read_bytes()


def test_mutable_worktree_task_is_never_used(source_repo, tmp_path):
    root, commit = source_repo
    (root / TASK_PATH).write_text("MUTATED WORKTREE\n")
    context_dir = tmp_path / "work" / "acrctx"
    CONTEXT.build(root, context_dir, commit, TASK_PATH)
    assert (context_dir / "task.yaml").read_bytes() != b"MUTATED WORKTREE\n"
    CONTEXT.verify(root, context_dir, expected_commit=commit,
                   expected_task_path=TASK_PATH)


@pytest.mark.parametrize("mutation", ["task", "extra", "manifest"])
def test_mutation_or_extra_file_refuses(source_repo, tmp_path, mutation):
    root, commit, context_dir = _built(source_repo, tmp_path)
    if mutation == "task":
        (context_dir / "task.yaml").write_bytes(b"changed\n")
    elif mutation == "extra":
        (context_dir / "repository-file.txt").write_bytes(b"forbidden\n")
    else:
        document = json.loads((context_dir / "context_manifest.json").read_text())
        document["source"]["tree"] = "0" * 40
        (context_dir / "context_manifest.json").write_text(json.dumps(document))
    with pytest.raises(CONTEXT.ContextDefect):
        CONTEXT.verify(root, context_dir, expected_commit=commit,
                       expected_task_path=TASK_PATH)


def test_symlink_refuses(source_repo, tmp_path):
    root, commit, context_dir = _built(source_repo, tmp_path)
    (context_dir / "task.yaml").unlink()
    try:
        (context_dir / "task.yaml").symlink_to(root / TASK_PATH)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(CONTEXT.ContextDefect):
        CONTEXT.verify(root, context_dir, expected_commit=commit,
                       expected_task_path=TASK_PATH)


def test_windows_path_failure_is_removed_with_registered_headroom():
    base = (
        "C:/Users/alanjiao/.copilot/session-state/"
        "0658bb9e-8615-4ded-95d4-9f633a6e5a12/files/"
        "p0-r1-gen3-live-replay-20260814T001628Z-e11496c7")
    failed = (
        base + "/context-aed13b7257096963c90a1ae5340d14ef3892392c/"
        "artifacts/jlens-s2-production/20260806T194226Z/analysis/"
        "convergence_per_layer.jsonl")
    repaired_longest = base + "/acrctx/context_manifest.json"
    assert len(failed) == 265
    assert len(failed) > 260
    assert len(repaired_longest) == 161
    assert len(repaired_longest) <= CONTEXT.WINDOWS_NATIVE_PATH_CEILING


def test_windows_posix_shell_requires_a_real_native_conversion(
        source_repo, tmp_path):
    root, commit, context_dir = _built(source_repo, tmp_path)
    with pytest.raises(CONTEXT.ContextDefect, match="returned"):
        CONTEXT.verify(
            root, context_dir, expected_commit=commit,
            expected_task_path=TASK_PATH,
            environ={"MSYSTEM": "MINGW64"}, os_name="posix",
            converter=lambda _: "/still/a/posix/path")


def test_native_windows_ceiling_refuses_before_submission(source_repo, tmp_path):
    root, commit, context_dir = _built(source_repo, tmp_path)
    with pytest.raises(CONTEXT.ContextDefect, match="exceeds ceiling"):
        CONTEXT.verify(
            root, context_dir, expected_commit=commit,
            expected_task_path=TASK_PATH,
            environ={"MSYSTEM": "MINGW64"}, os_name="posix",
            converter=lambda value: "C:/" + "x" * 245)


def test_acr_command_uses_only_root_task_and_minimal_context(source_repo, tmp_path):
    root, commit, context_dir = _built(source_repo, tmp_path)
    CONTEXT.verify(root, context_dir, expected_commit=commit,
                   expected_task_path=TASK_PATH)
    command = CONTEXT.acr_run_command(
        registry="exampleacr", subscription="00000000-0000-0000-0000-000000000000",
        image="example.azurecr.io/p0-r2@sha256:" + "1" * 64,
        digest="sha256:" + "1" * 64, ready_anchor="2" * 40,
        mode="packing-canary", attempt="p0r2-g1-packing-canary-unit",
        context_dir=context_dir)
    assert command[command.index("--file") + 1] == "task.yaml"
    assert command[-1] == str(context_dir.resolve())
    assert not any("artifacts/jlens" in value for value in command)
    assert not any(value == str(root) for value in command)


def test_receipt_cannot_pollute_two_file_context(source_repo, tmp_path):
    root, commit, context_dir = _built(source_repo, tmp_path)
    receipt = CONTEXT.verify(root, context_dir, expected_commit=commit,
                             expected_task_path=TASK_PATH)
    with pytest.raises(CONTEXT.ContextDefect, match="outside"):
        CONTEXT.write_receipt(context_dir / "receipt.json", receipt, context_dir)


def test_p0_r1_terminal_bytes_are_not_modified_by_p0_r2_implementation():
    changed = subprocess.run(
        ["git", "diff", "--name-only",
         "30806d793872a50e581d3252382b4a0ec2af3889", "HEAD", "--",
         "studies/study3/pilot/p0_r1",
         "studies/study3/pilot/p0/results/p0-r1"],
        cwd=str(ROOT), capture_output=True, text=True, check=True).stdout.strip()
    assert changed == ""


def test_module_is_model_free():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "import torch" not in source
    assert "import transformers" not in source
    assert "az acr run" not in source
