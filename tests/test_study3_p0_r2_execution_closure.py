"""Tests for the Study 3 P0-R2 generation-1 execution closure.

The centre of gravity here is the closure-binding cycle. P0-R1 stopped because
a host-side packing failure was indistinguishable from a scientific stop; P0-R2
replaces the transport, and the binding that makes the replacement trustworthy
must be *proved*, not granted. So the negative cases below are the real
content: a foreign commit, a broken ancestry, an altered task blob, changed
executable bytes, a mismatched digest, a forged lock, and a descendant that
touches something other than governance must each be refused.

Everything in this file is model-free. No test constructs a tokenizer,
downloads or loads a checkpoint, loads a model weight, performs a prefill or a
generation, scores a row, writes an evidence row, or allocates a GPU.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
P0_R2_DIR = ROOT / "studies" / "study3" / "pilot" / "p0_r2"
P0_R1_DIR = ROOT / "studies" / "study3" / "pilot" / "p0_r1"
CONTAINER = P0_R2_DIR / "container"
for _candidate in (P0_R2_DIR, P0_R1_DIR):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))


def _load(name, directory=None):
    path = (directory or P0_R2_DIR) / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


CLOSURE = _load("p0_r2_closure_binding_v1")
AZQUERY = _load("p0_r2_azure_query_v1")
CAPTURE = _load("p0_r2_replay_capture_v1")
VERIFY = _load("p0_r2_verify_replay_receipt")
AUTHZ = _load("p0_r2_authorization_v1")
JOBSPEC = _load("p0_r2_job_spec_v1")
GATE = _load("p0_r2_replay_gate_v1")
PREFIX = _load("p0_r2_prefix_preflight_v1")
RECOVERY = _load("p0_r2_recovery_v1")
RUNNER = _load("p0_r2_model_runner_v1")
IMAGE = _load("p0_r2_image_manifest_v1")
LOCK = _load("p0_r2_execution_lock_v1")
TRANSPORT = _load("p0_r2_transport")
BLOB = _load("p0_r2_blob_transport")

TASK_PATH = "studies/study3/pilot/p0_r2/container/p0_r2_acr_task_v1.yaml"
DIGEST = "sha256:" + "a1" * 32
BASE_DIGEST = "sha256:" + "b2" * 32
OTHER_DIGEST = "sha256:" + "c3" * 32


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-C", str(cwd)] + list(args), check=True,
        capture_output=True, text=True).stdout.strip()


def _commit(root, message):
    _git(root, "add", "-A")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@e",
         "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture()
def repo(tmp_path):
    """A miniature repository with the exact paths the binding cares about."""
    root = tmp_path / "repo"
    (root / "studies/study3/pilot/p0_r2/container").mkdir(parents=True)
    (root / "studies/study3/prompts").mkdir(parents=True)
    (root / TASK_PATH).write_text("version: v1.1.0\nsteps: []\n")
    (root / "studies/study3/pilot/p0_r2/p0_r2_transport.py").write_text(
        "# executable bytes\n")
    _git(root.parent, "init", "-q", str(root))
    executable = _commit(root, "executable bytes")

    # A governance-only descendant: it adds a lock and a prompt, and touches
    # nothing that the binding calls immutable.
    (root / "studies/study3/pilot/p0_r2/"
            "p0_r2_execution_lock_v1.json").write_text("{}\n")
    anchor = _commit(root, "governance: ready anchor")
    (root / "studies/study3/prompts/note.md").write_text("governance note\n")
    head = _commit(root, "governance: note")
    return {"root": root, "executable": executable, "anchor": anchor,
            "head": head}


# -- identity ---------------------------------------------------------------


@pytest.mark.parametrize("module", [
    CLOSURE, AZQUERY, CAPTURE, VERIFY, AUTHZ, JOBSPEC, GATE, PREFIX,
    RECOVERY, RUNNER, IMAGE, LOCK,
])
def test_every_module_declares_a_model_free_identity(module):
    identity = module.implementation_identity()
    assert identity["schema_version"].startswith("study3-p0-r2-")
    assert identity["model_operations_performed"] == 0


def test_the_immutable_binding_keys_are_exactly_the_six_registered_names():
    assert set(CLOSURE.IMMUTABLE_BINDING_KEYS) == {
        "executable_commit", "executable_tree", "task_path", "task_blob",
        "image", "digest"}


# -- the closure-binding cycle, positively ----------------------------------


def _binding(repo, **overrides):
    binding = {
        "executable_commit": repo["executable"],
        "executable_tree": _git(repo["root"], "rev-parse",
                                repo["executable"] + "^{tree}"),
        "task_path": TASK_PATH,
        "task_blob": _git(repo["root"], "rev-parse",
                          "%s:%s" % (repo["executable"], TASK_PATH)),
        "image": "reg.example/repo",
        "digest": DIGEST,
    }
    binding.update(overrides)
    return binding


def test_a_governance_only_descendant_satisfies_the_binding(repo):
    proof = CLOSURE.prove_governance_chain(
        root=repo["root"], executable_commit=repo["executable"],
        executable_tree=_git(repo["root"], "rev-parse",
                             repo["executable"] + "^{tree}"),
        ready_anchor=repo["anchor"], governance_commit=repo["head"],
        task_path=TASK_PATH, bound_paths=(TASK_PATH,),
        require_head=False, require_clean=False)
    assert proof["outcome"] == "GOVERNANCE_CHAIN_PROVED"
    assert CLOSURE.validate_proof(proof) is proof


def test_the_live_submission_agrees_with_the_canary_on_the_immutable_set(repo):
    canary = _binding(repo, source_commit=repo["executable"])
    # The live submission runs from a later governance commit, which is the
    # whole point: the source commit differs, the immutable set does not.
    live = dict(canary, source_commit=repo["head"])
    agreement = CLOSURE.verify_canary_live_agreement(canary, live)
    assert agreement["immutable_identity_agrees"] is True
    assert agreement["source_commit_may_differ"] is True
    assert set(agreement["immutable_keys_checked"]) == set(
        CLOSURE.IMMUTABLE_BINDING_KEYS)


def test_a_legacy_canary_binding_is_completed_by_proof_not_by_grant(repo):
    minimal = {"source_commit": repo["executable"], "task_blob":
               _git(repo["root"], "rev-parse",
                    "%s:%s" % (repo["executable"], TASK_PATH)),
               "task_path": TASK_PATH, "image": "reg.example/repo",
               "digest": DIGEST}
    resolved = CLOSURE.resolve_canary_binding(
        repo["root"], minimal, task_path=TASK_PATH)
    assert resolved["executable_commit"] == repo["executable"]
    assert resolved["executable_tree"] == _git(
        repo["root"], "rev-parse", repo["executable"] + "^{tree}")


# -- the closure-binding cycle, negatively ----------------------------------


def test_a_foreign_commit_is_refused(repo, tmp_path):
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _git(tmp_path, "init", "-q", str(foreign))
    (foreign / "unrelated.txt").write_text("not this project\n")
    stranger = _commit(foreign, "foreign")
    with pytest.raises(CLOSURE.ClosureBindingDefect):
        CLOSURE.prove_governance_chain(
            root=repo["root"], executable_commit=stranger,
            executable_tree=_git(foreign, "rev-parse", stranger + "^{tree}"),
            ready_anchor=repo["anchor"], governance_commit=repo["head"],
            task_path=TASK_PATH, require_head=False, require_clean=False)


def test_a_reversed_ancestry_is_refused(repo):
    # The anchor must descend from the executable commit, not precede it.
    with pytest.raises(CLOSURE.ClosureBindingDefect):
        CLOSURE.prove_governance_chain(
            root=repo["root"], executable_commit=repo["head"],
            executable_tree=_git(repo["root"], "rev-parse",
                                 repo["head"] + "^{tree}"),
            ready_anchor=repo["executable"], governance_commit=repo["head"],
            task_path=TASK_PATH, require_head=False, require_clean=False)


def test_the_anchor_may_not_be_the_executable_commit_itself(repo):
    with pytest.raises(CLOSURE.ClosureBindingDefect):
        CLOSURE.prove_governance_chain(
            root=repo["root"], executable_commit=repo["executable"],
            executable_tree=_git(repo["root"], "rev-parse",
                                 repo["executable"] + "^{tree}"),
            ready_anchor=repo["executable"], governance_commit=repo["head"],
            task_path=TASK_PATH, require_head=False, require_clean=False)


def test_a_descendant_that_changes_a_bound_path_is_refused(repo):
    (repo["root"] / TASK_PATH).write_text("version: v1.1.0\nsteps: [tampered]\n")
    tampered = _commit(repo["root"], "not governance: task changed")
    with pytest.raises(CLOSURE.ClosureBindingDefect):
        CLOSURE.prove_governance_chain(
            root=repo["root"], executable_commit=repo["executable"],
            executable_tree=_git(repo["root"], "rev-parse",
                                 repo["executable"] + "^{tree}"),
            ready_anchor=repo["anchor"], governance_commit=tampered,
            task_path=TASK_PATH, bound_paths=(TASK_PATH,),
            require_head=False, require_clean=False)


def test_changed_executable_bytes_are_refused(repo):
    target = repo["root"] / "studies/study3/pilot/p0_r2/p0_r2_transport.py"
    target.write_text("# different executable bytes\n")
    drifted = _commit(repo["root"], "operational drift")
    with pytest.raises(CLOSURE.ClosureBindingDefect):
        CLOSURE.prove_governance_chain(
            root=repo["root"], executable_commit=repo["executable"],
            executable_tree=_git(repo["root"], "rev-parse",
                                 repo["executable"] + "^{tree}"),
            ready_anchor=repo["anchor"], governance_commit=drifted,
            task_path=TASK_PATH,
            bound_paths=("studies/study3/pilot/p0_r2/p0_r2_transport.py",),
            require_head=False, require_clean=False)


@pytest.mark.parametrize("key,value", [
    ("executable_commit", "0" * 40),
    ("executable_tree", "1" * 40),
    ("task_path", "somewhere/else.yaml"),
    ("task_blob", "2" * 40),
    ("image", "reg.example/other"),
    ("digest", OTHER_DIGEST),
])
def test_disagreement_on_any_immutable_key_is_refused(repo, key, value):
    canary = _binding(repo)
    live = dict(canary)
    live[key] = value
    with pytest.raises(CLOSURE.ClosureBindingDefect):
        CLOSURE.verify_canary_live_agreement(canary, live)


def test_a_task_path_is_accepted_only_when_git_stores_that_blob_there(repo):
    minimal = {"source_commit": repo["executable"],
               "task_blob": "3" * 40, "task_path": TASK_PATH,
               "image": "reg.example/repo", "digest": DIGEST}
    with pytest.raises(CLOSURE.ClosureBindingDefect):
        CLOSURE.resolve_canary_binding(
            repo["root"], minimal, task_path=TASK_PATH)


# -- the lock ---------------------------------------------------------------


def _canaries():
    return {
        "packing_canary": {"outcome": "PASS", "run_id": "ca1"},
        "transport_roundtrip": {"outcome": "PASS", "run_id": "ca2"},
    }


def test_a_lock_is_refused_without_passing_canary_evidence():
    with pytest.raises(LOCK.LockDefect):
        LOCK.build(root=ROOT, executable_commit="0" * 40, image_digest=DIGEST,
                   base_digest=BASE_DIGEST, anchor_parent="1" * 40,
                   build_run_id="r1", canaries={})


def test_a_lock_is_refused_when_a_canary_failed():
    failing = _canaries()
    failing["transport_roundtrip"]["outcome"] = "FAIL"
    with pytest.raises(LOCK.LockDefect):
        LOCK.build(root=ROOT, executable_commit="0" * 40, image_digest=DIGEST,
                   base_digest=BASE_DIGEST, anchor_parent="1" * 40,
                   build_run_id="r1", canaries=failing)


def test_a_lock_is_refused_when_the_packing_canary_has_no_run_id():
    canaries = _canaries()
    canaries["packing_canary"]["run_id"] = None
    with pytest.raises(LOCK.LockDefect):
        LOCK.build(root=ROOT, executable_commit="0" * 40, image_digest=DIGEST,
                   base_digest=BASE_DIGEST, anchor_parent="1" * 40,
                   build_run_id="r1", canaries=canaries)


def test_a_lock_is_refused_without_a_pinned_digest():
    with pytest.raises(LOCK.LockDefect):
        LOCK.build(root=ROOT, executable_commit="0" * 40,
                   image_digest="latest", base_digest=BASE_DIGEST,
                   anchor_parent="1" * 40, build_run_id="r1",
                   canaries=_canaries())


def test_a_forged_lock_is_refused_by_verification(repo):
    forged = {
        "schema_version": LOCK.SCHEMA_VERSION,
        "executable_code": {"commit": repo["executable"], "tree": "9" * 40},
        "transport": {"task_path": TASK_PATH, "task_blob": "9" * 40},
        "delegated_scientific_modules": [],
        "counters": {},
    }
    with pytest.raises(LOCK.LockDefect):
        LOCK.verify(forged, root=repo["root"])


def test_a_lock_with_a_nonzero_counter_is_refused(repo):
    document = {
        "schema_version": LOCK.SCHEMA_VERSION,
        "executable_code": {
            "commit": repo["executable"],
            "tree": _git(repo["root"], "rev-parse",
                         repo["executable"] + "^{tree}")},
        "transport": {
            "task_path": TASK_PATH,
            "task_blob": _git(repo["root"], "rev-parse",
                              "%s:%s" % (repo["executable"], TASK_PATH))},
        "delegated_scientific_modules": [],
        "counters": {"generations": 1},
    }
    with pytest.raises(LOCK.LockDefect):
        LOCK.verify(document, root=repo["root"])


def test_the_lock_schema_matches_the_generator():
    schema = json.loads(
        (P0_R2_DIR / "p0_r2_execution_lock_v1.schema.json")
        .read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == \
        LOCK.SCHEMA_VERSION
    assert schema["properties"]["terminal_state"]["const"] == \
        LOCK.TERMINAL_STATE
    assert schema["properties"]["namespace"]["properties"]["gpu_job"][
        "const"] == LOCK.GPU_JOB
    assert schema["properties"]["predecessor"]["properties"]["stop_commit"][
        "const"] == LOCK.P0_R1_STOP_COMMIT
    for cap, value in RUNNER.CAPS.items():
        assert schema["properties"]["caps"]["properties"][cap]["const"] == value


# -- the model runner refuses -----------------------------------------------


def test_the_default_executor_is_the_sentinel_and_authorizes_nothing():
    document = RUNNER.run({"attempt_id": "p0r2-g1-x"})
    assert document["executor"] == "sentinel"
    assert document["authorizes_anything"] is False
    for key in ("tokenizer_constructions", "checkpoint_downloads",
                "model_weight_loads", "prefills", "generations",
                "scored_rows", "evidence_rows_added", "gpu_allocations"):
        assert document[key] == 0


def test_production_refuses_without_an_accelerator_requirement():
    with pytest.raises(RUNNER.ModelRunnerRefused):
        RUNNER.require_production_preconditions(
            authorization={"outcome": "AUTHORIZED"},
            lock={"image": {"digest": DIGEST}}, accelerator_required=False)


def test_production_refuses_without_an_authorization():
    with pytest.raises(RUNNER.ModelRunnerRefused):
        RUNNER.require_production_preconditions(
            authorization=None, lock={"image": {"digest": DIGEST}},
            accelerator_required=True)


def test_production_refuses_when_the_caps_were_changed():
    caps = dict(RUNNER.CAPS)
    caps["max_s4_generations"] = 13
    with pytest.raises(RUNNER.ModelRunnerRefused):
        RUNNER.require_production_preconditions(
            authorization={"outcome": "AUTHORIZED", "image_digest": DIGEST},
            lock={"image": {"digest": DIGEST}, "caps": caps},
            accelerator_required=True)


def test_production_refuses_when_the_digest_does_not_match_the_lock():
    with pytest.raises(RUNNER.ModelRunnerRefused):
        RUNNER.require_production_preconditions(
            authorization={"outcome": "AUTHORIZED",
                           "image_digest": OTHER_DIGEST},
            lock={"image": {"digest": DIGEST}, "caps": dict(RUNNER.CAPS)},
            accelerator_required=True)


# -- job specifications never touch Azure -----------------------------------


def test_the_gpu_specification_is_refused_without_an_authorization():
    with pytest.raises(JOBSPEC.JobSpecDefect):
        JOBSPEC.gpu_spec(image="reg.example/repo@" + DIGEST,
                         attempt="p0r2-g1-pilot", authorization=None)


def test_the_gpu_specification_forbids_a_retried_replica():
    spec = JOBSPEC.gpu_spec(
        image="reg.example/repo@" + DIGEST, attempt="p0r2-g1-pilot",
        authorization={"outcome": "AUTHORIZED", "image_digest": DIGEST,
                       "attempt_id": "p0r2-g1-pilot",
                       "attempt": "p0r2-g1-pilot"})
    configuration = spec["properties"]["configuration"]
    assert configuration["replicaRetryLimit"] == 0
    assert configuration["manualTriggerConfig"]["parallelism"] == 1
    assert configuration["triggerType"] == "Manual"


def test_a_recovery_specification_never_requests_an_accelerator():
    spec = JOBSPEC.recovery_spec(
        "recover", image="reg.example/repo@" + DIGEST,
        attempt="p0r2-g1-recover")
    rendered = json.dumps(spec)
    assert "gpu" not in rendered.lower()
    assert spec["properties"]["configuration"]["replicaRetryLimit"] == 0


def test_an_unpinned_image_is_refused():
    with pytest.raises(JOBSPEC.JobSpecDefect):
        JOBSPEC.recovery_spec("recover", image="reg.example/repo:latest",
                              attempt="p0r2-g1-recover")


def test_an_unrecognised_recovery_mode_is_refused():
    with pytest.raises(JOBSPEC.JobSpecDefect):
        JOBSPEC.recovery_spec("launch-the-model",
                              image="reg.example/repo@" + DIGEST,
                              attempt="p0r2-g1-recover")


def test_the_registered_job_yaml_agrees_with_the_renderer():
    gpu = (CONTAINER / "p0_r2_gpu_job_v1.yaml").read_text(encoding="utf-8")
    recovery = (CONTAINER / "p0_r2_recovery_job_v1.yaml").read_text(
        encoding="utf-8")
    assert "name: %s" % JOBSPEC.GPU_JOB in gpu
    assert "replicaRetryLimit: 0" in gpu
    assert "parallelism: 1" in gpu
    assert "name: %s" % JOBSPEC.RECOVERY_JOB in recovery
    assert "cpu_only: true" in recovery


# -- fail-closed control-plane queries --------------------------------------


def test_a_query_error_is_never_an_absence():
    assert AZQUERY.classify(1, "", "AuthorizationFailed") == "AMBIGUOUS"
    assert AZQUERY.classify(1, "", "TooManyRequests") == "AMBIGUOUS"
    assert AZQUERY.classify(1, "", "connection reset by peer") == "AMBIGUOUS"


def test_a_success_with_no_payload_proves_nothing():
    assert AZQUERY.classify(0, "", "") == "AMBIGUOUS"
    assert AZQUERY.classify(0, "not json", "") == "AMBIGUOUS"


def test_an_empty_successful_listing_proves_absence():
    assert AZQUERY.classify(0, "[]", "") == "PROVED_ABSENT"
    assert AZQUERY.classify(1, "", "ResourceNotFound") == "PROVED_ABSENT"


def test_a_nonempty_successful_listing_proves_presence():
    assert AZQUERY.classify(0, '[{"name": "job-x"}]', "") == "PROVED_PRESENT"


def test_an_absence_marker_combined_with_an_authorization_failure_is_ambiguous():
    # A "not found" that arrives alongside an authorization problem is not a
    # proof of absence; it is a proof that the question was not answered.
    assert AZQUERY.classify(
        1, "", "AuthorizationFailed: ResourceNotFound") == "AMBIGUOUS"


def test_an_unsafe_azure_name_is_refused():
    with pytest.raises(AZQUERY.AzureQueryDefect):
        AZQUERY.job_presence("job; rm -rf /", resource_group="rg",
                             subscription="sub")


# -- prefix preflight and recovery ------------------------------------------


class _Backend:
    credential_kind = "managed-identity"

    def __init__(self, names=(), payloads=None, fail=False):
        self._names = list(names)
        self._payloads = payloads or {}
        self._fail = fail

    def list_names(self, prefix):
        if self._fail:
            raise RuntimeError("listing failed")
        return [name[len(prefix):] for name in self._names
                if name.startswith(prefix)]

    def download(self, name):
        return self._payloads[name]


def test_an_empty_prefix_is_proved_unused():
    report = PREFIX.probe("p0r2-g1-x", backend=_Backend())
    assert report["outcome"] == "PROVED_UNUSED"
    assert PREFIX.require_unused(report) is report


def test_an_occupied_prefix_is_refused():
    prefix = BLOB.attempt_prefix("p0r2-g1-x")
    report = PREFIX.probe("p0r2-g1-x", backend=_Backend([prefix + "a.json"]))
    assert report["outcome"] == "PROVED_IN_USE"
    with pytest.raises(PREFIX.PrefixPreflightDefect):
        PREFIX.require_unused(report)


def test_a_failed_listing_is_not_an_absence():
    with pytest.raises(PREFIX.PrefixPreflightDefect):
        PREFIX.probe("p0r2-g1-x", backend=_Backend(fail=True))


def test_recovery_refuses_on_an_accelerator_replica():
    with pytest.raises(RECOVERY.RecoveryDefect):
        RECOVERY.assert_model_free({"NVIDIA_VISIBLE_DEVICES": "all"})


def test_recovery_of_an_empty_prefix_claims_nothing():
    with pytest.raises(RECOVERY.RecoveryDefect):
        RECOVERY.recover("p0r2-g1-x", backend=_Backend(), environ={})


def test_a_partial_attempt_never_authorizes_a_retry():
    prefix = BLOB.attempt_prefix("p0r2-g1-x")
    payloads = {prefix + "row-0.json": b'{"row": 0}'}
    report = RECOVERY.recover(
        "p0r2-g1-x", backend=_Backend(list(payloads), payloads), environ={})
    assert report["classification"] == "PARTIAL"
    assert report["retry_authorized"] is False
    assert report["wrote_repaired_or_deleted_any_object"] is False
    assert report["model_operations_performed"] == 0


# -- transport reconstruction -----------------------------------------------


def _realistic_artifacts(attempt):
    """The four canonical artifacts with the structure capture insists on."""
    counters = {name: 0 for name in (
        "tokenizer_constructions", "checkpoint_downloads", "model_weight_loads",
        "prefills", "generations", "scored_rows", "evidence_rows_added",
        "gpu_allocations", "model_operations_performed")}
    result = {"attempt": attempt, "stage": "STUDY3-P0-R2",
              "outcome": "GATE_COMPLETE", "counters": counters}
    receipt = {"attempt": attempt, "stage": "STUDY3-P0-R2",
               "artifacts": list(TRANSPORT.REPLAY_ARTIFACTS),
               "counters": counters}
    return {
        "p0_r2_replay_result.json":
            (json.dumps(result, indent=2, sort_keys=True) + "\n").encode(),
        "p0_r2_replay_receipt.json":
            (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(),
        "p0_r2_replay_counters.json":
            (json.dumps(counters, indent=2, sort_keys=True) + "\n").encode(),
        "P0_R2_REPLAY_DISPOSITION.md":
            ("# P0-R2 replay disposition\n\nattempt %s\n" % attempt).encode(),
    }


def _capture(tmp_path, log, attempt, out_dir=None):
    raw = tmp_path / "raw.log"
    raw.write_text(log, encoding="utf-8")
    return CAPTURE.capture(
        raw_log_path=raw, out_dir=out_dir or (tmp_path / "out"),
        attempt=attempt, run_id="ca1", exit_code=0,
        executable_commit="0" * 40, image_digest=DIGEST)


def test_the_four_artifacts_are_rebuilt_from_the_raw_log_alone(tmp_path):
    attempt = "p0r2-g1-capture"
    artifacts = _realistic_artifacts(attempt)
    log = "\n".join(TRANSPORT.encode(attempt, artifacts))
    out = tmp_path / "out"
    report = _capture(tmp_path, log, attempt, out_dir=out)
    assert report["attempt_id"] == attempt
    assert report["outcome"] == "PASS"
    assert report["reconstructed_from_log_alone"] is True
    assert report["emitted_receipt_trusted"] is False
    assert report["authorizes_model_pilot"] is False
    assert report["artifact_count"] == 4
    for name, payload in artifacts.items():
        assert (out / name).read_bytes() == payload


def test_a_truncated_log_is_refused_rather_than_partially_accepted(tmp_path):
    attempt = "p0r2-g1-capture"
    lines = TRANSPORT.encode(attempt, _realistic_artifacts(attempt))
    with pytest.raises(CAPTURE.CaptureDefect):
        _capture(tmp_path, "\n".join(lines[: len(lines) // 2]), attempt)


def test_a_log_from_a_different_attempt_is_refused(tmp_path):
    log = "\n".join(TRANSPORT.encode(
        "p0r2-g1-capture", _realistic_artifacts("p0r2-g1-capture")))
    with pytest.raises(CAPTURE.CaptureDefect):
        _capture(tmp_path, log, "p0r2-g1-someone-else")


def test_a_nonzero_exit_is_never_reconstructed_as_a_pass(tmp_path):
    attempt = "p0r2-g1-capture"
    raw = tmp_path / "raw.log"
    raw.write_text("\n".join(TRANSPORT.encode(
        attempt, _realistic_artifacts(attempt))), encoding="utf-8")
    with pytest.raises(CAPTURE.CaptureDefect):
        CAPTURE.capture(
            raw_log_path=raw, out_dir=tmp_path / "out", attempt=attempt,
            run_id="ca1", exit_code=1, executable_commit="0" * 40,
            image_digest=DIGEST)


def test_the_canary_fixture_exceeds_the_registered_minimum():
    fixture = TRANSPORT.canary_fixture("p0r2-g1-capture")
    total = sum(len(payload) for payload in fixture.values())
    assert total >= TRANSPORT.CANARY_MINIMUM_TOTAL_BYTES


# -- container assets --------------------------------------------------------


def test_the_successor_script_has_no_default_mode():
    text = (CONTAINER / "p0_r2_successor_v1.sh").read_text(encoding="utf-8")
    assert "no mode was named" in text
    for mode in ("preflight", "live-replay", "launch-pilot"):
        assert mode in text
    assert "P0_R2_LIVE_REPLAY_AUTHORIZED" in text
    assert "P0_R2_PILOT_AUTHORIZED" in text


def test_the_dockerfile_pins_its_base_by_digest_and_audits_itself():
    text = (CONTAINER / "Dockerfile.study3-p0-r2").read_text(encoding="utf-8")
    assert "@sha256:" in text
    assert "p0_r2_image_manifest_v1.py" in text
    assert "--audit" in text


def test_the_canary_script_is_model_free():
    text = (CONTAINER / "p0_r2_canary_v1.sh").read_text(encoding="utf-8")
    assert "P0_R2_MODEL_OPERATIONS_PERFORMED=0" in text
    assert "P0_R2_REPLAY_GATE_RUN=false" in text
    assert "P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=false" in text


def test_the_pilot_script_refuses_before_it_reaches_a_model():
    text = (CONTAINER / "p0_r2_model_pilot_v1.sh").read_text(encoding="utf-8")
    for required in ("P0_R2_REPLAY_RECEIPT", "P0_R2_RECONSTRUCTION_RECEIPT",
                     "P0_R2_HEAD_PROOF", "P0_R2_PILOT_AUTHORIZED"):
        assert required in text
    assert "P0_R2_PILOT_REFUSED=1" in text


def test_the_image_manifest_covers_every_operational_and_scientific_module():
    assert TASK_PATH not in IMAGE.OPERATIONAL_PATHS
    for path in IMAGE.SCIENTIFIC_PATHS:
        assert path.startswith("studies/study3/pilot/p0_r1/")
        assert (ROOT / path).is_file()
    for path in IMAGE.OPERATIONAL_PATHS:
        assert path.startswith("studies/study3/pilot/p0_r2/")
        assert (ROOT / path).is_file()


def test_the_image_audit_refuses_when_a_carried_byte_differs(tmp_path):
    manifest = {
        "schema_version": IMAGE.SCHEMA_VERSION,
        "image_root": str(tmp_path),
        "entries": [{"kind": "operational", "path": "a.py", "bytes": 3,
                     "sha256": "0" * 64, "git_blob": "1" * 40,
                     "image_path": "a.py"}],
    }
    (tmp_path / "a.py").write_text("abc")
    with pytest.raises(IMAGE.ImageManifestDefect):
        IMAGE.audit(manifest, image_root=tmp_path)


# -- P0-R1 is untouched and terminal ----------------------------------------


def test_p0_r2_delegates_science_and_does_not_copy_it():
    identity = GATE.implementation_identity()
    assert identity["copies_or_edits_science"] is False
    assert identity["verifies_science_by_sha256_before_import"] is True
    assert identity["authorizes_model_pilot"] is False


def test_the_predecessor_stop_is_recorded_and_not_reopened():
    assert LOCK.P0_R1_STOP_STATE == "STOP_NO_MODEL_OPERATION"
    assert LOCK.P0_R1_STOP_COMMIT == \
        "30806d793872a50e581d3252382b4a0ec2af3889"


def test_the_terminal_state_is_the_registered_string():
    assert LOCK.TERMINAL_STATE == \
        "STUDY3_P0_R2_EXECUTION_READY_AWAITING_REPLAY_GATE"
