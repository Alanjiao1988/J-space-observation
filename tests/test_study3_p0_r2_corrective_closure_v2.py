"""Tests for the Study 3 P0-R2 corrective closure (v2).

These are the tests the v1 closure did not have. Each one exists because
something specific went wrong:

* the v1 governance validator decided whether a path was inert by looking it up
  in a literal list, so eight executable validation inputs slipped past review
  and the real proof refused while the readiness claim was published anyway;
* the v1 first command ran from ``/dev/null`` inside the image and therefore
  could not observe a single host-side fact it was cited for;
* the hard-kill / open-admission recovery property was asserted and never
  demonstrated;
* the run record was incomplete and the standing-failure baseline was stale.

Every test here is offline and model-free. Nothing constructs a tokenizer,
downloads a checkpoint, loads a model weight, allocates a GPU or contacts
Azure.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
P0_R2_DIR = REPO_ROOT / "studies" / "study3" / "pilot" / "p0_r2"
VALIDATION_DIR = P0_R2_DIR / "validation"

for candidate in (P0_R2_DIR, VALIDATION_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import p0_r2_attempt_ledger_v2 as LEDGER  # noqa: E402
import p0_r2_blob_transport as BLOB  # noqa: E402
import p0_r2_closure_binding_v2 as CB2  # noqa: E402
import p0_r2_execution_lock_v2 as LOCK2  # noqa: E402
import p0_r2_hard_kill_canary_v2 as HARDKILL  # noqa: E402
import p0_r2_host_preflight_v2 as HOST  # noqa: E402
import p0_r2_image_manifest_v2 as MANIFEST2  # noqa: E402
import p0_r2_normalize_signatures_v2 as SIG  # noqa: E402


CORRECTIVE_AUTHORITY = (
    REPO_ROOT / "studies" / "study3" / "prompts"
    / "study3_p0_r2_corrective_closure_and_conditional_execution_authority.md")
SUPERSESSION = P0_R2_DIR / "p0_r2_v1_supersession_v2.json"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    """A tiny repository with an executable commit, an anchor and a head."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "canary@example.invalid")
    _git(root, "config", "user.name", "canary")

    (root / "code.py").write_text("print('operational')\n", encoding="utf-8")
    (root / "task.yaml").write_text("version: v1.1.0\n", encoding="utf-8")
    (root / "science.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "executable")
    executable = _git(root, "rev-parse", "HEAD")

    (root / "base.md").write_text("closure base\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "closure base")
    base = _git(root, "rev-parse", "HEAD")

    (root / "lock.json").write_text("{}\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "anchor")
    anchor = _git(root, "rev-parse", "HEAD")
    return types.SimpleNamespace(root=root, executable=executable, base=base,
                                 anchor=anchor)


def _lock_for(repo, *, closure=(), extra=None):
    lock = {
        "image_executable": {
            "commit": repo.executable,
            "tree": _git(repo.root, "rev-parse", "%s^{tree}" % repo.executable),
            "files": [{"path": "code.py"}],
        },
        "host_closure_executable": {
            "commit": repo.executable,
            "tree": _git(repo.root, "rev-parse", "%s^{tree}" % repo.executable),
            "files": [],
        },
        "closure_base": {"commit": repo.base},
        "transport": {"task_path": "task.yaml",
                      "task_blob": _git(repo.root, "rev-parse",
                                        "%s:task.yaml" % repo.executable)},
        "image": {"reference": "registry.invalid/image@sha256:" + "a" * 64,
                  "digest": "sha256:" + "a" * 64},
        "p0_r1_terminal": {"stop_commit": repo.executable},
        "governance_evidence_closure": [
            {"path": path, "class": "evidence"} for path in closure],
        "immutable_sources": [],
        "validation_inputs": [],
        "job_specifications": [],
    }
    if extra:
        lock.update(extra)
    return lock


# --------------------------------------------------------------------------
# classification: the v1 defect, and why a list could not have caught it
# --------------------------------------------------------------------------

def test_a_shell_script_is_classified_executable_from_its_own_bytes(repo):
    (repo.root / "run.sh").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "add script")
    head = _git(repo.root, "rev-parse", "HEAD")

    entry = CB2.classify_committed_path(repo.root, head, "run.sh")
    assert entry["classification"] == CB2.EXECUTABLE
    assert "shebang" in entry["reasons"]
    assert "executable-extension:.sh" in entry["reasons"]


def test_a_task_definition_is_executable_even_without_a_shebang(repo):
    (repo.root / "job.yaml").write_text("steps: []\n", encoding="utf-8")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "add job")
    head = _git(repo.root, "rev-parse", "HEAD")

    entry = CB2.classify_committed_path(repo.root, head, "job.yaml")
    assert entry["classification"] == CB2.EXECUTABLE
    assert entry["reasons"] == ["executable-extension:.yaml"]


def test_a_document_is_classified_non_executable(repo):
    (repo.root / "notes.md").write_text("# notes\n", encoding="utf-8")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "add notes")
    head = _git(repo.root, "rev-parse", "HEAD")

    entry = CB2.classify_committed_path(repo.root, head, "notes.md")
    assert entry["classification"] == CB2.NON_EXECUTABLE
    assert entry["reasons"] == []


def test_a_deleted_path_is_never_admitted_as_inert(repo):
    os.remove(repo.root / "science.py")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "delete science")
    head = _git(repo.root, "rev-parse", "HEAD")

    entry = CB2.classify_committed_path(repo.root, head, "science.py")
    assert entry["classification"] == CB2.EXECUTABLE
    assert "deletion-of-a-path-cannot-be-proved-inert" in entry["reasons"]


# --------------------------------------------------------------------------
# the corrected chain proof
# --------------------------------------------------------------------------

def test_the_chain_refuses_an_executable_input_committed_after_the_anchor(repo):
    """This is exactly the published v1 failure, reproduced in miniature."""
    (repo.root / "validate.sh").write_text("#!/bin/sh\ntrue\n", encoding="utf-8")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "post-anchor validation script")
    head = _git(repo.root, "rev-parse", "HEAD")

    lock = _lock_for(repo, closure=("validate.sh",))
    with pytest.raises(CB2.ClosureBindingDefect) as excinfo:
        CB2.prove_v2_chain(root=repo.root, lock=lock, ready_anchor=repo.anchor,
                           governance_commit=head, require_head=False)
    message = str(excinfo.value)
    assert "validate.sh" in message
    assert "classifies_non_executable" in message


def test_the_chain_refuses_a_document_that_is_not_in_the_published_closure(repo):
    (repo.root / "surprise.md").write_text("late\n", encoding="utf-8")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "unlisted document")
    head = _git(repo.root, "rev-parse", "HEAD")

    lock = _lock_for(repo, closure=())
    with pytest.raises(CB2.ClosureBindingDefect) as excinfo:
        CB2.prove_v2_chain(root=repo.root, lock=lock, ready_anchor=repo.anchor,
                           governance_commit=head, require_head=False)
    assert "member_of_published_closure" in str(excinfo.value)


def test_the_chain_admits_a_listed_inert_document(repo):
    (repo.root / "handoff.md").write_text("handoff\n", encoding="utf-8")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "handoff")
    head = _git(repo.root, "rev-parse", "HEAD")

    lock = _lock_for(repo, closure=("handoff.md",))
    proof = CB2.prove_v2_chain(root=repo.root, lock=lock,
                               ready_anchor=repo.anchor,
                               governance_commit=head, require_head=False)
    assert proof["outcome"] == "GOVERNANCE_CHAIN_PROVED"
    assert proof["changed_since_anchor"] == ["handoff.md"]
    assert proof["every_post_anchor_path_proved_non_executable"] is True
    assert proof["caller_supplied_allowlist_accepted"] is False


def test_the_chain_keeps_the_nine_identities_apart(repo):
    lock = _lock_for(repo, closure=())
    proof = CB2.prove_v2_chain(root=repo.root, lock=lock,
                               ready_anchor=repo.anchor,
                               governance_commit=repo.anchor,
                               require_head=False)
    assert proof["identities"] == list(CB2.IDENTITIES)
    assert len(CB2.IDENTITIES) == 9
    for key in ("immutable_science", "image_executable",
                "host_closure_executable", "task_object", "image",
                "closure_base", "ready_anchor", "governance_source"):
        assert key in proof


def test_the_chain_refuses_a_bound_path_that_moved_after_the_image_build(repo):
    (repo.root / "code.py").write_text("print('drifted')\n", encoding="utf-8")
    (repo.root / "handoff.md").write_text("handoff\n", encoding="utf-8")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "drift")
    head = _git(repo.root, "rev-parse", "HEAD")

    lock = _lock_for(repo, closure=("handoff.md", "code.py"))
    with pytest.raises(CB2.ClosureBindingDefect) as excinfo:
        CB2.prove_v2_chain(root=repo.root, lock=lock, ready_anchor=repo.anchor,
                           governance_commit=head, require_head=False)
    assert "outside_bound_executable_closure" in str(excinfo.value) \
        or "image-bound" in str(excinfo.value)


def test_adding_a_host_tool_after_the_image_build_is_not_image_drift(repo):
    """The defect this module found in itself.

    A host-side tool committed after the image was built is not image drift:
    it was never in the image. Merging the two closures made a correct closure
    refuse, and -- worse -- told the operator to discard a perfectly good image
    and rebuild.
    """
    (repo.root / "host_tool.py").write_text("#!/usr/bin/env python3\n",
                                            encoding="utf-8")
    (repo.root / "handoff.md").write_text("handoff\n", encoding="utf-8")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "host tool plus handoff")
    host_commit = _git(repo.root, "rev-parse", "HEAD")

    lock = _lock_for(repo, closure=("handoff.md",))
    lock["host_closure_executable"] = {
        "commit": host_commit,
        "tree": _git(repo.root, "rev-parse", "%s^{tree}" % host_commit),
        "files": [{"path": "host_tool.py"}]}
    lock["closure_base"] = {"commit": host_commit}

    _git(repo.root, "commit", "-q", "--allow-empty", "-m", "anchor v2")
    anchor = _git(repo.root, "rev-parse", "HEAD")

    proof = CB2.prove_v2_chain(root=repo.root, lock=lock, ready_anchor=anchor,
                               governance_commit=anchor, require_head=False)
    assert proof["bound_paths_changed_after_image_build"] == []
    assert proof["host_closure_paths_changed_after_freeze"] == []
    assert proof["image_bound_closure_size"] >= 1
    assert proof["host_bound_closure_size"] >= 1


def test_the_chain_refuses_a_host_tool_that_moved_after_the_freeze(repo):
    (repo.root / "host_tool.py").write_text("#!/usr/bin/env python3\n",
                                            encoding="utf-8")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "host tool")
    host_commit = _git(repo.root, "rev-parse", "HEAD")

    (repo.root / "host_tool.py").write_text("#!/usr/bin/env python3\n# moved\n",
                                            encoding="utf-8")
    (repo.root / "handoff.md").write_text("handoff\n", encoding="utf-8")
    _git(repo.root, "add", "-A")
    _git(repo.root, "commit", "-q", "-m", "host tool drift")
    head = _git(repo.root, "rev-parse", "HEAD")

    lock = _lock_for(repo, closure=("handoff.md",))
    lock["host_closure_executable"] = {
        "commit": host_commit,
        "tree": _git(repo.root, "rev-parse", "%s^{tree}" % host_commit),
        "files": [{"path": "host_tool.py"}]}
    lock["closure_base"] = {"commit": host_commit}

    _git(repo.root, "commit", "-q", "--allow-empty", "-m", "anchor v2")
    anchor = _git(repo.root, "rev-parse", "HEAD")

    with pytest.raises(CB2.ClosureBindingDefect) as excinfo:
        CB2.prove_v2_chain(root=repo.root, lock=lock, ready_anchor=anchor,
                           governance_commit=anchor, require_head=False)
    assert "host-closure" in str(excinfo.value)


def test_the_closure_is_an_exact_path_set_and_rejects_patterns(repo):
    lock = _lock_for(repo, closure=("docs/*.md",))
    with pytest.raises(CB2.ClosureBindingDefect) as excinfo:
        CB2.prove_v2_chain(root=repo.root, lock=lock, ready_anchor=repo.anchor,
                           governance_commit=repo.anchor, require_head=False)
    assert "exact path set" in str(excinfo.value)


def test_the_validator_offers_no_caller_supplied_allowlist():
    import argparse
    import io
    import contextlib

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), \
            contextlib.redirect_stderr(buffer), \
            pytest.raises(SystemExit):
        CB2.main(["--identity", "--allow-path", "anything"])
    assert "unrecognized arguments" in buffer.getvalue() \
        or "--allow-path" in buffer.getvalue()

    identity = CB2.implementation_identity()
    assert identity["accepts_caller_supplied_allowlist"] is False
    assert identity["has_allow_path_option"] is False
    assert identity["module_level_path_allowlist"] is False
    assert identity["classification_is_derived_from_committed_bytes"] is True
    assert not hasattr(CB2, "GOVERNANCE_ALLOWLIST")
    assert not hasattr(CB2, "GOVERNANCE_ALLOWLIST_PREFIXES")
    assert isinstance(argparse.ArgumentParser, type)


def test_the_v1_relationship_is_still_refused_by_the_corrected_validator():
    """7fd5fe5 -> 005aa087 must never become admissible."""
    lock = {
        "image_executable": {
            "commit": "1eb3e21b408213cb183bd8d2f55c3554b9713160",
            "tree": "88d7e9a016772c4129f56637edd2d7fbd96b105b",
            "files": []},
        "host_closure_executable": {
            "commit": "1eb3e21b408213cb183bd8d2f55c3554b9713160",
            "tree": "88d7e9a016772c4129f56637edd2d7fbd96b105b",
            "files": []},
        "closure_base": {"commit": "1eb3e21b408213cb183bd8d2f55c3554b9713160"},
        "transport": {
            "task_path": ("studies/study3/pilot/p0_r2/container/"
                          "p0_r2_acr_task_v1.yaml"),
            "task_blob": "0ec0bfa0c2e3ebe882963564ef758b06bf890657"},
        "image": {"reference": "registry.invalid/image@sha256:" + "b" * 64,
                  "digest": "sha256:" + "b" * 64},
        "p0_r1_terminal": {
            "stop_commit": "30806d793872a50e581d3252382b4a0ec2af3889"},
        "governance_evidence_closure": [],
        "immutable_sources": [], "validation_inputs": [],
        "job_specifications": [],
    }
    with pytest.raises(CB2.ClosureBindingDefect):
        CB2.prove_v2_chain(
            root=REPO_ROOT, lock=lock,
            ready_anchor="7fd5fe57707461fcf70bfc9ab00b707b3c44ef71",
            governance_commit="005aa087e40c641affc8ca537e6c6a075bcbfe98",
            require_head=False)


# --------------------------------------------------------------------------
# host preflight: the checks a /dev/null image command cannot make
# --------------------------------------------------------------------------

def test_the_host_preflight_names_every_required_marker_exactly_once():
    identity = HOST.implementation_identity()
    assert identity["required_markers"] == list(HOST.REQUIRED_MARKERS)
    assert len(set(HOST.REQUIRED_MARKERS)) == len(HOST.REQUIRED_MARKERS)
    for marker in ("P0_R2_HOST_PREFLIGHT_COMPLETE=1",
                   "P0_R2_GOVERNANCE_CHAIN_PROVED=1",
                   "P0_R2_HEAD_EQUALS_ORIGIN_MAIN=1",
                   "P0_R2_WORKTREE_CLEAN=1",
                   "P0_R2_P0_R1_TERMINAL=1",
                   "P0_R2_REPLAY_ENVELOPE_UNCONSUMED=1",
                   "P0_R2_LIVE_PREFIX_PROVED_UNUSED=1",
                   "P0_R2_GPU_JOB_PROVED_ABSENT=1",
                   "P0_R2_RECOVERY_JOB_PROVED_ABSENT=1",
                   "P0_R2_MODEL_OPERATIONS_PERFORMED=0"):
        assert marker in HOST.REQUIRED_MARKERS


def test_the_host_preflight_is_not_satisfied_by_an_image_only_command():
    identity = HOST.implementation_identity()
    assert identity["image_only_dev_null_command_is_sufficient"] is False
    assert identity["runs_from_a_fresh_clean_checkout"] is True
    assert identity["azure_query_error_is_absence"] is False


def _preflight(tmp_path, lock):
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    return HOST.Preflight(REPO_ROOT, lock_path)


def test_the_host_preflight_refuses_a_foreign_head(tmp_path):
    preflight = _preflight(tmp_path, {})
    preflight.check_exact_published_commit_and_tree("f" * 40, None)
    assert preflight.refusals == ["exact_final_published_commit_and_tree"]


def test_the_host_preflight_refuses_a_dirty_worktree(tmp_path, monkeypatch):
    preflight = _preflight(tmp_path, {})
    monkeypatch.setattr(preflight, "git",
                        lambda *args, **kwargs: (" M some/file\n", 0))
    preflight.check_worktree_clean()
    assert preflight.refusals == ["worktree_clean"]


def test_the_host_preflight_refuses_an_altered_lock(tmp_path):
    preflight = _preflight(tmp_path, {"self": {"path": "no/such/lock.json"}})
    preflight.check_lock_self_binding()
    assert preflight.refusals == ["active_lock_on_disk_is_the_committed_lock"]


def test_the_host_preflight_refuses_an_unpinned_image(tmp_path):
    preflight = _preflight(tmp_path, {
        "image": {"reference": "registry.invalid/image:latest",
                  "digest": "sha256:" + "c" * 64},
        "transport": {"task_path": "x", "task_blob": "d" * 40},
        "image_executable": {"commit": "e" * 40}})
    preflight.check_image_digest_and_task_blob()
    assert preflight.refusals == ["exact_image_digest_and_task_blob"]


def test_the_host_preflight_refuses_an_ambiguous_job_query(tmp_path):
    preflight = _preflight(tmp_path, {
        "azure": {"resource_group": "rg-jspace-observation-sea",
                  "subscription": "943bacdf-8b6e-4e3a-8126-a149f623d32e"}})

    class _Ambiguous:
        returncode = 1
        stdout = ""
        stderr = "AuthorizationFailed: the client does not have permission"

    preflight.check_jobs_absent(runner=lambda command: _Ambiguous())
    assert preflight.refusals == ["gpu_job_proved_absent",
                                  "recovery_job_proved_absent"]
    for entry in preflight.checks:
        assert entry["detail"]["query_error_is_absence"] is False


def test_the_host_preflight_refuses_a_present_job(tmp_path):
    preflight = _preflight(tmp_path, {
        "azure": {"resource_group": "rg-jspace-observation-sea",
                  "subscription": "943bacdf-8b6e-4e3a-8126-a149f623d32e"}})

    class _Present:
        returncode = 0
        stdout = json.dumps({"name": "job-jspace-s3-p0r2-pilot-g1"})
        stderr = ""

    preflight.check_jobs_absent(runner=lambda command: _Present())
    assert "gpu_job_proved_absent" in preflight.refusals


def test_the_host_preflight_refuses_an_occupied_prefix(tmp_path):
    receipt = tmp_path / "prefix.json"
    receipt.write_text(json.dumps({
        "schema_version": "study3-p0-r2-prefix-preflight-v1",
        "attempt_id": "p0r2-g1-live-replay",
        "outcome": "PROVED_IN_USE", "object_count": 4,
        "wrote_any_object": False,
        "execution_identity": "job/exec"}), encoding="utf-8")
    preflight = _preflight(tmp_path, {
        "attempt": {"live_replay_attempt_id": "p0r2-g1-live-replay"}})
    preflight.check_prefix_unused(str(receipt))
    assert preflight.refusals == ["preregistered_live_attempt_prefix_unused"]


def test_the_host_preflight_refuses_a_missing_prefix_receipt(tmp_path):
    preflight = _preflight(tmp_path, {
        "attempt": {"live_replay_attempt_id": "p0r2-g1-live-replay"}})
    preflight.check_prefix_unused(None)
    assert preflight.refusals == ["preregistered_live_attempt_prefix_unused"]
    detail = preflight.checks[0]["detail"]
    assert detail["query_error_is_absence"] is False


def test_the_host_preflight_refuses_a_nonzero_counter(tmp_path):
    counters = {name: 0 for name in HOST.PRE_REPLAY_COUNTERS}
    counters["prefills"] = 1
    preflight = _preflight(tmp_path, {"pre_replay_counters": counters})
    preflight.check_counters_zero()
    assert preflight.refusals == ["all_pre_replay_counters_zero"]


def test_the_host_preflight_accepts_only_all_zero_counters(tmp_path):
    counters = {name: 0 for name in HOST.PRE_REPLAY_COUNTERS}
    preflight = _preflight(tmp_path, {"pre_replay_counters": counters})
    preflight.check_counters_zero()
    assert preflight.refusals == []


def test_the_host_preflight_refuses_a_long_native_packer_path(tmp_path):
    # Deliberately not created on disk: the point is the measured length of the
    # native path the packer would walk, and Windows refuses to create it --
    # which is precisely the class of failure that stopped P0-R1 at 265 chars.
    deep = tmp_path / ("d" * 120) / ("e" * 120)
    preflight = _preflight(tmp_path, {})
    preflight.check_native_path_budget(deep)
    assert preflight.refusals == ["native_windows_packer_paths_within_budget"]
    detail = preflight.checks[0]["detail"]
    assert detail["context_max_native_path_chars"] > HOST.MAX_NATIVE_PATH_CHARS
    assert detail["p0_r1_fatal_length"] == 265


def test_the_host_preflight_accepts_a_short_native_packer_path(tmp_path):
    context = tmp_path / "ctx"
    context.mkdir()
    (context / "task.yaml").write_text("x\n", encoding="utf-8")
    (context / "context_manifest.json").write_text("{}\n", encoding="utf-8")
    preflight = _preflight(tmp_path, {})
    preflight.check_native_path_budget(context)
    assert preflight.refusals == []
    assert preflight.checks[0]["detail"]["limit"] == 240


def test_the_host_preflight_refuses_a_canary_bound_to_another_image(tmp_path):
    preflight = _preflight(tmp_path, {
        "image": {"reference": "registry.invalid/image@sha256:" + "1" * 64,
                  "digest": "sha256:" + "1" * 64},
        "transport": {"task_path": "task.yaml", "task_blob": "a" * 40},
        "image_executable": {"commit": "b" * 40, "tree": "c" * 40},
        "designated_packing_canary": {
            "executable_commit": "b" * 40, "executable_tree": "c" * 40,
            "task_path": "task.yaml", "task_blob": "a" * 40,
            "image": "registry.invalid/image@sha256:" + "2" * 64,
            "digest": "sha256:" + "2" * 64}})
    preflight.check_packing_canary()
    assert preflight.refusals == [
        "designated_packing_canary_matches_active_identity"]


def test_the_host_preflight_refuses_a_present_replay_artifact(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "p0_r2_replay_result.json").write_text("{}", encoding="utf-8")
    preflight = _preflight(tmp_path, {
        "replay_envelope": {"consumed": False, "invocations": 0}})
    preflight.check_replay_unconsumed(results)
    assert "p0_r2_replay_envelope_unconsumed" in preflight.refusals
    assert "canonical_p0_r2_replay_artifacts_absent" in preflight.refusals


# --------------------------------------------------------------------------
# hard-kill / open-admission recovery
# --------------------------------------------------------------------------

@pytest.fixture()
def hard_kill_attempt():
    return "p0r2-g1-hardkill-canary-unit"


def _write_killed_attempt(attempt_id, backend, rows=2, seal_manifest=False,
                          skip_sequence=False):
    """Reproduce exactly what a killed child leaves behind."""
    HARDKILL.register_synthetic_kind()
    transport = BLOB.PrivateBlobTransport(attempt_id, backend=backend)
    journal = HARDKILL.JOURNAL.DurableJournal(
        attempt_id, HARDKILL.JOURNAL.BlobJournalSink(transport))
    journal.start()
    journal.record("counter_snapshot",
                   HARDKILL.synthetic_counter_snapshot(attempt_id))
    journal.admit(HARDKILL.SYNTHETIC_KIND, {"synthetic": True})
    for ordinal in range(1, rows + 1):
        journal.record("scored_row", HARDKILL.synthetic_row(attempt_id, ordinal))
    if skip_sequence:
        journal.index += 1
    if seal_manifest:
        journal.manifest()
    return journal


def test_recovery_finds_the_open_admission_and_every_payload_byte(
        hard_kill_attempt):
    backend = BLOB.InMemoryBackend()
    _write_killed_attempt(hard_kill_attempt, backend)

    report = HARDKILL.recover_independently(hard_kill_attempt, rows=2,
                                            backend=backend)
    assert report["open_admission_operation"] == HARDKILL.SYNTHETIC_KIND
    assert report["journal_sequence_continuous"] is True
    assert report["journal_is_create_only"] is True
    assert len(report["recovered_rows"]) == 2
    for row in report["recovered_rows"]:
        assert row["byte_exact_against_independent_regeneration"] is True
    assert report["no_observation_inferred_from_name_or_hash_alone"] is True
    assert report["model_operations_performed"] == 0


def test_the_recovery_manifest_is_written_last_and_covers_everything(
        hard_kill_attempt):
    backend = BLOB.InMemoryBackend()
    _write_killed_attempt(hard_kill_attempt, backend)
    before = sorted(backend.list_names(BLOB.attempt_prefix(hard_kill_attempt)))

    report = HARDKILL.recover_independently(hard_kill_attempt, rows=2,
                                            backend=backend)
    after = sorted(backend.list_names(BLOB.attempt_prefix(hard_kill_attempt)))
    assert len(after) == len(before) + 1
    assert report["manifest_identity"]["name"] == \
        HARDKILL.RECOVERY_MANIFEST_NAME
    assert report["written_last"] is True
    assert report["recursive_enumeration"] is True
    assert report["object_count"] == len(before)


def test_recovery_refuses_when_a_manifest_already_exists(hard_kill_attempt):
    backend = BLOB.InMemoryBackend()
    _write_killed_attempt(hard_kill_attempt, backend, seal_manifest=True)
    with pytest.raises(HARDKILL.HardKillCanaryDefect) as excinfo:
        HARDKILL.recover_independently(hard_kill_attempt, rows=2,
                                       backend=backend)
    assert "manifest already exists" in str(excinfo.value)


def test_recovery_refuses_a_gap_in_the_journal_sequence(hard_kill_attempt):
    backend = BLOB.InMemoryBackend()
    _write_killed_attempt(hard_kill_attempt, backend, skip_sequence=True)
    # The gap only exists once a later entry is written past it.
    transport = BLOB.PrivateBlobTransport(hard_kill_attempt, backend=backend)
    journal = HARDKILL.JOURNAL.DurableJournal(
        hard_kill_attempt, HARDKILL.JOURNAL.BlobJournalSink(transport))
    journal.index = 9
    journal.record("counter_snapshot",
                   HARDKILL.synthetic_counter_snapshot(hard_kill_attempt))
    with pytest.raises(HARDKILL.HardKillCanaryDefect) as excinfo:
        HARDKILL.recover_independently(hard_kill_attempt, rows=2,
                                       backend=backend)
    assert "not continuous" in str(excinfo.value)


def test_recovery_refuses_an_empty_prefix(hard_kill_attempt):
    backend = BLOB.InMemoryBackend()
    with pytest.raises(HARDKILL.HardKillCanaryDefect) as excinfo:
        HARDKILL.recover_independently(hard_kill_attempt, rows=2,
                                       backend=backend)
    assert "disproved, not waived" in str(excinfo.value)


def test_the_synthetic_row_is_deterministic_and_model_free():
    first = HARDKILL.synthetic_row("p0r2-g1-hardkill-canary-x", 1)
    second = HARDKILL.synthetic_row("p0r2-g1-hardkill-canary-x", 1)
    other = HARDKILL.synthetic_row("p0r2-g1-hardkill-canary-y", 1)
    assert first == second
    assert first != other
    assert first["model_operations_performed"] == 0
    assert first["contains_model_bytes"] is False


def test_the_hard_kill_canary_is_not_waivable():
    identity = HARDKILL.implementation_identity()
    assert identity["waivable"] is False
    assert identity["kill_signal"] == "SIGKILL"
    assert identity["kill_is_catchable"] is False
    assert identity["recovery_is_independent"] is True
    assert identity["requests_accelerator"] is False


def test_the_canary_registers_its_synthetic_kind_without_editing_the_journal():
    source = (P0_R2_DIR / "p0_r2_journal_v1.py").read_text(encoding="utf-8")
    assert HARDKILL.SYNTHETIC_KIND not in source


# --------------------------------------------------------------------------
# attempt ledger
# --------------------------------------------------------------------------

def test_the_ledger_registers_every_disclosed_run_id():
    registered = {run_id for run_id, _, _, _ in LEDGER.REGISTERED_RUNS}
    for run_id in ("cmht", "cmhu", "cmhv", "cmj3", "cmj5", "cmj6", "cmj7",
                   "cmhp", "cmhq", "cmhs", "cmj2", "cmj4", "cmhb", "cmhd",
                   "cmhe", "cmhf", "cmhg", "cmhh", "cmhk", "cmhn", "cmhw",
                   "cmhx", "cmhy", "cmj0", "cmj1"):
        assert run_id in registered
    assert len(registered) == 25


def test_the_ledger_treats_a_query_error_as_ambiguous_not_absent():
    class _Failed:
        returncode = 1
        stdout = ""
        stderr = "AuthorizationFailed"

    document = LEDGER.build(runner=lambda command: _Failed())
    assert document["ambiguous_count"] == document["run_count"]
    assert document["complete_and_admissible"] is False
    assert document["stops"]
    assert all("ambiguous" in stop for stop in document["stops"])


def test_the_ledger_never_calls_an_unavailable_run_a_pass():
    identity = LEDGER.implementation_identity()
    assert identity["unavailable_is_a_pass"] is False
    assert identity["fabricates_hashes"] is False
    assert identity["query_error_is_absence"] is False


def test_the_ledger_refuses_to_drop_an_earlier_run():
    previous = {"runs": [{"run_id": "cmht", "category": "accepted",
                          "registered_purpose": "build",
                          "evidence_outcome": "SEALED",
                          "log_sha256": "a" * 64, "log_bytes": 10}]}
    current = {"runs": []}
    with pytest.raises(LEDGER.LedgerDefect) as excinfo:
        LEDGER.verify_append_only(previous, current)
    assert "drops" in str(excinfo.value)


def test_the_ledger_refuses_to_rewrite_an_earlier_run():
    entry = {"run_id": "cmht", "category": "accepted",
             "registered_purpose": "build", "evidence_outcome": "SEALED",
             "log_sha256": "a" * 64, "log_bytes": 10}
    previous = {"runs": [entry]}
    current = {"runs": [dict(entry, log_sha256="b" * 64)]}
    with pytest.raises(LEDGER.LedgerDefect) as excinfo:
        LEDGER.verify_append_only(previous, current)
    assert "rewrites" in str(excinfo.value)


def test_the_ledger_accepts_a_pure_addition():
    entry = {"run_id": "cmht", "category": "accepted",
             "registered_purpose": "build", "evidence_outcome": "SEALED",
             "log_sha256": "a" * 64, "log_bytes": 10}
    proof = LEDGER.verify_append_only(
        {"runs": [entry]},
        {"runs": [entry, dict(entry, run_id="cmj9")]})
    assert proof["added_runs"] == ["cmj9"]
    assert proof["append_only"] is True


# --------------------------------------------------------------------------
# lock and schema
# --------------------------------------------------------------------------

def _minimal_lock():
    return {
        "schema_version": LOCK2.SCHEMA_VERSION,
        "stage": "STUDY3-P0-R2",
        "generation": 1,
        "revision": 2,
        "terminal_state": LOCK2.TERMINAL_STATE,
        "self": {"path": "x"}, "schema": {"path": "y"},
        "authorities": [{"path": "a", "bytes": 1, "sha256": "a" * 64},
                        {"path": "b", "bytes": 1, "sha256": "b" * 64}],
        "image_executable": {"commit": "a" * 40, "tree": "b" * 40,
                             "files": [{"path": "p"}]},
        "host_closure_executable": {"commit": "c" * 40, "tree": "d" * 40,
                                    "files": [{"path": "q"}]},
        "closure_base": {"commit": "e" * 40},
        "ready_commit_relationship": {"ready_anchor_parent": "f" * 40,
                                      "lock_records_its_own_commit": False,
                                      "anchor_is_resolved_by_ancestry": True},
        "validation_inputs": [{"path": "v", "bytes": 1, "sha256": "c" * 64}],
        "job_specifications": [{"path": "j", "bytes": 1, "sha256": "d" * 64}],
        "immutable_sources": [{"path": "s%d" % i, "bytes": 1,
                               "sha256": "%064d" % i} for i in range(4)],
        "governance_bytes": [{"path": "g1", "bytes": 1, "sha256": "e" * 64},
                             {"path": "g2", "bytes": 1, "sha256": "f" * 64}],
        "transport": {"task_path": "t", "task_blob": "0" * 40,
                      "task_sha256": "0" * 64, "context_entry_count": 2,
                      "context_is_executable_code": False},
        "image": {"reference": "r@sha256:" + "1" * 64,
                  "digest": "sha256:" + "1" * 64,
                  "base_digest": "sha256:" + "2" * 64,
                  "build_run_id": "cmj9",
                  "manifest_entries_sha256": "3" * 64},
        "p0_r1_terminal": {"stop_commit": "9" * 40,
                           "state": "STOP_NO_MODEL_OPERATION",
                           "replay_envelope_consumed": True,
                           "launchable": False,
                           "protected_bytes": [
                               {"path": "p%d" % i, "bytes": 1,
                                "sha256": "%064d" % i} for i in range(8)]},
        "v1_supersession": {"superseded": True, "launchable": False,
                            "record_path": "rec", "v1_lock_path": "lock",
                            "v1_lock_sha256": "4" * 64, "v1_bytes_edited": 0},
        "replay_envelope": {"consumed": False, "invocations": 0,
                            "consumed_on_invocation_even_without_a_run_id": True,
                            "rerunnable": False},
        "attempt": {"prefix_root": "study3/p0_r2/g1",
                    "live_replay_attempt_id": "p0r2-g1-live",
                    "pilot_attempt_id": "p0r2-g1-pilot"},
        "azure": {}, "designated_packing_canary": {}, "canaries": {},
        "attempt_ledger": {}, "validation": {},
        "standing_failures": {"count": 4,
                              "node_ids": list(LOCK2.STANDING_FAILURES),
                              "conditionally_accepted": True},
        "governance_evidence_closure": [{"path": "doc.md", "class": "evidence"}],
        "caps": dict(LOCK2.CAPS),
        "caps_are_enforced_not_reported": True,
        "pre_replay_counters": dict(LOCK2.PRE_REPLAY_COUNTERS),
        "legal_state": dict(LOCK2.LEGAL_STATE),
        "prohibitions": {name: True for name in
                         ("a", "b", "c", "d", "e", "f", "g", "h")},
    }


def test_a_well_formed_lock_satisfies_its_schema():
    assert LOCK2.validate(_minimal_lock(), LOCK2.schema())["outcome"] == \
        "LOCK_VALID"


def test_the_schema_refuses_a_consumed_envelope():
    lock = _minimal_lock()
    lock["replay_envelope"]["consumed"] = True
    with pytest.raises(LOCK2.LockDefect):
        LOCK2.validate(lock, LOCK2.schema())


def test_the_schema_refuses_a_moved_cap():
    lock = _minimal_lock()
    lock["caps"]["max_s4_generations"] = 13
    with pytest.raises(LOCK2.LockDefect):
        LOCK2.validate(lock, LOCK2.schema())


def test_the_schema_refuses_a_nonzero_pre_replay_counter():
    lock = _minimal_lock()
    lock["pre_replay_counters"]["prefills"] = 1
    with pytest.raises(LOCK2.LockDefect):
        LOCK2.validate(lock, LOCK2.schema())


def test_the_schema_refuses_a_fifth_standing_failure():
    lock = _minimal_lock()
    lock["standing_failures"]["node_ids"] = list(LOCK2.STANDING_FAILURES) + [
        "tests/test_other.py::test_new"]
    lock["standing_failures"]["count"] = 5
    with pytest.raises(LOCK2.LockDefect):
        LOCK2.validate(lock, LOCK2.schema())


def test_the_schema_refuses_a_wildcard_in_the_governance_closure():
    lock = _minimal_lock()
    lock["governance_evidence_closure"] = [{"path": "docs/*.md",
                                            "class": "evidence"}]
    with pytest.raises(LOCK2.LockDefect):
        LOCK2.validate(lock, LOCK2.schema())


def test_the_schema_refuses_a_changed_legal_state():
    lock = _minimal_lock()
    lock["legal_state"]["formal_execution_authorized"] = True
    with pytest.raises(LOCK2.LockDefect):
        LOCK2.validate(lock, LOCK2.schema())


def test_the_lock_never_records_its_own_commit_or_a_future_hash():
    identity = LOCK2.implementation_identity()
    assert identity["lock_records_its_own_commit"] is False
    assert identity["lock_records_future_hashes"] is False


def test_the_registered_caps_are_exactly_the_authorized_maxima():
    assert LOCK2.CAPS == {
        "max_smoke_prefills_before_extension": 60,
        "max_non_generative_prefills": 180,
        "max_s4_generations": 12,
        "max_model_evaluation_equivalents": 228,
        "possible_scored_rows": 210,
    }


# --------------------------------------------------------------------------
# image manifest v2
# --------------------------------------------------------------------------

def test_the_v2_manifest_is_v1_plus_a_named_delta():
    import p0_r2_image_manifest_v1 as V1
    assert set(V1.OPERATIONAL_PATHS) <= set(MANIFEST2.OPERATIONAL_PATHS)
    assert set(V1.ENTRYPOINT_PATHS) <= set(MANIFEST2.ENTRYPOINT_PATHS)
    assert MANIFEST2.SCIENTIFIC_PATHS == V1.SCIENTIFIC_PATHS
    delta = set(MANIFEST2.OPERATIONAL_PATHS) - set(V1.OPERATIONAL_PATHS)
    assert delta == set(MANIFEST2.ADDED_OPERATIONAL_PATHS)


def test_the_v2_manifest_does_not_edit_v1():
    identity = MANIFEST2.implementation_identity()
    assert identity["edits_v1"] is False
    assert identity["derives_its_sets_from_v1"] is True


def test_every_added_image_path_is_committed():
    for path in (MANIFEST2.ADDED_OPERATIONAL_PATHS
                 + MANIFEST2.ADDED_ENTRYPOINT_PATHS):
        assert (REPO_ROOT / path).is_file(), path


# --------------------------------------------------------------------------
# failure-signature comparison
# --------------------------------------------------------------------------

def test_normalization_removes_only_what_cannot_carry_meaning():
    raw = ("/workspace/base/tests/test_x.py:12: AssertionError\n"
           "object at 0x7f2c1a0b4d90\n"
           "/tmp/pytest-of-root/pytest-3/test_x0/artifact.json\n")
    normalized = SIG.normalize(raw)
    assert "<CHECKOUT>" in normalized
    assert "<ADDR>" in normalized
    assert "<PYTEST_TMP>" in normalized
    assert "AssertionError" in normalized


def test_two_checkouts_of_the_same_failure_normalize_identically():
    base = SIG.normalize("/workspace/base/tests/t.py:1: AssertionError x\n")
    head = SIG.normalize("/workspace/head/tests/t.py:1: AssertionError x\n")
    assert base == head


def test_a_quoted_checkout_root_normalizes_too():
    """The exact miss that made differential run cmja refuse.

    ``repo_root = PosixPath('/workspace/base')`` and its ``/workspace/head``
    twin are the same failure. The first normalizer only ended the checkout
    root at ``/``, whitespace, ``:`` or end of line, so a closing quote left the
    two signatures different by two characters and the differential correctly
    refused. Ending the match at any non-path character fixes it without
    loosening anything that carries meaning.
    """
    base = SIG.normalize("repo_root = PosixPath('/workspace/base'), x = 1\n")
    head = SIG.normalize("repo_root = PosixPath('/workspace/head'), x = 1\n")
    assert base == head
    assert "<CHECKOUT>" in base


def test_normalization_does_not_swallow_a_longer_name():
    text = SIG.normalize("/workspace/baseline/tests/t.py:1: AssertionError\n")
    assert "/workspace/baseline" in text
    assert "<CHECKOUT>" not in text


def test_the_comparison_detects_a_changed_signature_on_the_same_node_id():
    baseline = SIG.summarize({
        "label": "BASELINE", "exitstatus": 1, "counts": {"failed": 1},
        "collection_error_count": 0,
        "non_passing": [{"nodeid": "tests/t.py::test_a", "phase": "call",
                         "kind": "failed", "longrepr": "assert 1 == 2"}]})
    corrected = SIG.summarize({
        "label": "CORRECTED", "exitstatus": 1, "counts": {"failed": 1},
        "collection_error_count": 0,
        "non_passing": [{"nodeid": "tests/t.py::test_a", "phase": "call",
                         "kind": "failed", "longrepr": "assert 3 == 4"}]})
    report = SIG.compare(baseline, corrected)
    assert report["new_failures"] == []
    assert report["signatures_agree"] is False
    assert report["signatures_disagreeing_on_shared_failures"] == [
        "tests/t.py::test_a"]


def test_the_comparison_detects_a_new_failure():
    baseline = SIG.summarize({
        "label": "BASELINE", "exitstatus": 1, "counts": {"failed": 0},
        "collection_error_count": 0, "non_passing": []})
    corrected = SIG.summarize({
        "label": "CORRECTED", "exitstatus": 1, "counts": {"failed": 1},
        "collection_error_count": 0,
        "non_passing": [{"nodeid": "tests/t.py::test_new", "phase": "call",
                         "kind": "failed", "longrepr": "boom"}]})
    report = SIG.compare(baseline, corrected)
    assert report["new_failures"] == ["tests/t.py::test_new"]
    assert report["new_failure_count"] == 1


# --------------------------------------------------------------------------
# published corrective artifacts
# --------------------------------------------------------------------------

def test_the_corrective_authority_is_published_lf_only_and_without_a_bom():
    payload = CORRECTIVE_AUTHORITY.read_bytes()
    assert payload, "the corrective authority must exist"
    assert b"\r" not in payload
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert payload.endswith(b"\n")


def test_the_corrective_authority_records_every_bound_identity():
    text = CORRECTIVE_AUTHORITY.read_text(encoding="utf-8")
    for identity in (
            "005aa087e40c641affc8ca537e6c6a075bcbfe98",
            "9d3610a85d5fb35dd8a34544296b81c8f5e77f28",
            "1eb3e21b408213cb183bd8d2f55c3554b9713160",
            "88d7e9a016772c4129f56637edd2d7fbd96b105b",
            "7fd5fe57707461fcf70bfc9ab00b707b3c44ef71",
            "0ec0bfa0c2e3ebe882963564ef758b06bf890657",
            "30806d793872a50e581d3252382b4a0ec2af3889",
            "943bacdf-8b6e-4e3a-8126-a149f623d32e",
            "sha256:3d857e54007d12bd943b383db522b913ba627a544b4d31b3e648eef30a65d8e7"):
        assert identity in text, identity


def test_the_corrective_authority_records_the_conditional_segment_b_rule():
    text = CORRECTIVE_AUTHORITY.read_text(encoding="utf-8")
    assert "conditional" in text
    assert "may never be rerun" in text
    assert "P0_R2_CORRECTIVE_CLOSURE_STOP_NO_REPLAY" in text
    assert "even if failure occurs before an ACR run id" in text.replace(
        "\n", " ")
    assert "STUDY3_P0_R2_EXECUTION_READY_AWAITING_REPLAY_GATE" in text


def test_the_supersession_record_edits_no_v1_byte():
    record = json.loads(SUPERSESSION.read_text(encoding="utf-8"))
    assert record["v1_bytes_edited"] == 0
    assert record["v1_launchable"] is False
    assert record["outcome"] == "V1_CLOSURE_SUPERSEDED_AND_NONLAUNCHABLE"
    assert record["replay_envelope_still_unconsumed"] is True
    assert record["generation_remains"] == 1
    assert record["model_operations_performed"] == 0


def test_the_supersession_record_binds_the_published_v1_lock_bytes():
    record = json.loads(SUPERSESSION.read_text(encoding="utf-8"))
    lock = (P0_R2_DIR / "p0_r2_execution_lock_v1.json").read_bytes()
    entry = next(item for item in record["superseded_objects"]
                 if item["path"].endswith("p0_r2_execution_lock_v1.json"))
    assert entry["bytes"] == len(lock)
    assert entry["sha256"] == _sha256(lock)


def test_the_v1_closure_binding_module_is_untouched():
    """v1 is historical. Superseding it may not edit a single byte."""
    committed = _git(REPO_ROOT, "show",
                     "1eb3e21b408213cb183bd8d2f55c3554b9713160:"
                     "studies/study3/pilot/p0_r2/p0_r2_closure_binding_v1.py")
    current = (P0_R2_DIR / "p0_r2_closure_binding_v1.py").read_text(
        encoding="utf-8")
    assert current.replace("\r\n", "\n").strip() == committed.strip()
    assert "GOVERNANCE_ALLOWLIST" in current


def test_p0_r1_protected_prefixes_are_registered():
    assert CB2.PROTECTED_P0_R1_PREFIXES == (
        "studies/study3/pilot/p0_r1/",
        "studies/study3/pilot/p0/results/p0-r1/",
    )
