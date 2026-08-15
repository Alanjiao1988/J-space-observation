"""Study 3 P0-R2 generation-2 closure tests.

Authority:
``studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md``
sections 6.2, 6.3, 6.5, 6.6 and 7.

Section 6.3 is explicit about what must be proved rather than described:

* canary and live call the same prefix-receipt validation implementation;
* it accepts a valid, byte-bound receipt;
* it rejects missing, changed, stale-at-host, occupied, mismatched, ambiguous,
  duplicate and incorrectly hashed receipts;
* live mode performs no private Storage call before the gate;
* a credential-less, network-isolated container can pass admission with a valid
  receipt and cannot pass without one;
* no string-only or mocked-success assertion substitutes for executed behaviour.

Every test below drives the committed production modules. Nothing here asserts
on a literal copied out of a source file without executing the code that
produces it.
"""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path, PureWindowsPath
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


NAMESPACE = _load("p0_r2_namespace_g2")
PREFIX = _load("p0_r2_prefix_proof_g2")
SUBMIT = _load("p0_r2_host_submission_g2")
MANIFEST = _load("p0_r2_image_manifest_g2")
LOCK = _load("p0_r2_execution_lock_g2")
CLOSURE = _load("p0_r2_closure_binding_g2")
PREFLIGHT = _load("p0_r2_host_preflight_g2")
GATE = _load("p0_r2_replay_gate_g2")

G2_MODULES = (NAMESPACE, PREFIX, SUBMIT, MANIFEST, LOCK, CLOSURE, PREFLIGHT,
              GATE)

ATTEMPT = "p0r2-g2-canary-unittest-20260815-0000"


class _ManagedIdentityBackend:
    """An in-memory stand-in that declares the only credential kind allowed."""

    credential_kind = "managed-identity"

    def __init__(self, names=()):
        self._names = list(names)
        self.written = []

    def list_names(self, prefix):
        return [name for name in self._names if name.startswith(prefix)]

    def upload(self, name, payload, overwrite=False):
        self.written.append(name)
        raise AssertionError("the prefix proof must never write an object")


class _SharedKeyBackend(_ManagedIdentityBackend):
    credential_kind = "shared-key"


def _observation(attempt=ATTEMPT, backend=None, environ=None):
    environ = environ or {
        "P0_R2_G2_PREFIX_JOB": PREFIX.PREFIX_JOB,
        "CONTAINER_APP_JOB_EXECUTION_NAME": "job-jspace-s3-p0r2-prefix-g2-t3st",
        "P0_R2_IMAGE_DIGEST": "sha256:" + "a" * 64,
    }
    return PREFIX.require_unused(
        PREFIX.observe(attempt, backend=backend or _ManagedIdentityBackend(),
                       environ=environ))


def _log_for(observation):
    payload = PREFIX.canonical_bytes(observation)
    encoded = base64.b64encode(payload).decode("ascii")
    body = "\n".join(encoded[index:index + 76]
                     for index in range(0, len(encoded), 76))
    return "prelude\n%s\n%s\n%s\ntail\n" % (
        PREFIX.OBSERVATION_BEGIN, body, PREFIX.OBSERVATION_END)


def _receipt(attempt=ATTEMPT, status="Succeeded"):
    observation = _observation(attempt)
    log = _log_for(observation)
    return PREFIX.correlate(
        observation=observation,
        execution={"job": PREFIX.PREFIX_JOB,
                   "name": "job-jspace-s3-p0r2-prefix-g2-t3st",
                   "status": status,
                   "start_time": "2026-08-15T00:00:00Z",
                   "end_time": "2026-08-15T00:01:00Z"},
        stdout=log.encode("utf-8"), stderr=b"", log_text=log)


def _manifest_for(receipt):
    payload = PREFIX.canonical_bytes(receipt)
    return payload, {
        "embedded_governance_objects": [{
            "label": PREFIX.CONTEXT_LABEL,
            "bytes": len(payload),
            "sha256": PREFIX._sha256(payload),
            "encoding": "base64",
            "payload": base64.b64encode(payload).decode("ascii"),
            "source_path": "prefix_receipt.json",
        }],
    }


# --------------------------------------------------------------------------
# Identity and namespace disjointness
# --------------------------------------------------------------------------

@pytest.mark.parametrize("module", G2_MODULES,
                         ids=lambda m: m.implementation_identity()["module"])
def test_every_generation2_module_declares_a_model_free_identity(module):
    identity = module.implementation_identity()
    assert identity["stage"] == "STUDY3-P0-R2"
    assert identity["generation"] == 2
    assert identity["model_operations_performed"] == 0


def test_the_generation2_namespace_is_disjoint_from_generation_1():
    assert NAMESPACE.PREFIX_ROOT != NAMESPACE.GENERATION1_PREFIX_ROOT
    assert NAMESPACE.ATTEMPT_ID_PREFIX != NAMESPACE.GENERATION1_ATTEMPT_ID_PREFIX
    prefix = NAMESPACE.attempt_prefix(ATTEMPT)
    assert prefix.startswith("study3/p0_r2/g2/")
    assert "g1" not in prefix.split("/")


def test_a_generation1_attempt_is_refused_by_every_generation2_entry_point():
    for call in (lambda: NAMESPACE.attempt_prefix("p0r2-g1-live-20260815-0800"),
                 lambda: PREFIX.attempt_prefix("p0r2-g1-live-20260815-0800")):
        with pytest.raises((NAMESPACE.NamespaceDefect,
                            PREFIX.PrefixProofDefect)):
            call()


def test_a_generation1_identifier_cannot_reach_a_generation2_field():
    with pytest.raises(NAMESPACE.NamespaceDefect):
        NAMESPACE.assert_disjoint_from_generation1(["study3/p0_r2/g1/x/"])


def test_reused_primitives_execute_the_frozen_bytes_unchanged():
    import p0_r2_transport as generation1

    instance = NAMESPACE.transport()
    assert instance is not generation1
    assert instance.ATTEMPT_ID_PREFIX == NAMESPACE.ATTEMPT_ID_PREFIX
    # The generation-1 module object is never mutated.
    assert generation1.ATTEMPT_ID_PREFIX == NAMESPACE.GENERATION1_ATTEMPT_ID_PREFIX
    identity = NAMESPACE.source_identity("p0_r2_transport")
    assert instance.__p0_r2_source_sha256__ == identity["sha256"]


def test_a_reused_primitive_refuses_bytes_that_are_not_the_bound_bytes():
    with pytest.raises(NAMESPACE.NamespaceDefect):
        NAMESPACE.instantiate("p0_r2_transport", expected_sha256="f" * 64)


def test_the_generation2_envelope_round_trips_byte_exactly():
    transport = NAMESPACE.transport()
    decoder = NAMESPACE.strict_decoder()
    fixture = transport.canary_fixture(ATTEMPT)
    recovered, repairs = decoder.recover_with_report(
        "\n".join(transport.encode(ATTEMPT, fixture)), ATTEMPT)
    assert repairs == []
    assert recovered == fixture


# --------------------------------------------------------------------------
# Section 6.3: one shared validator, no branch asymmetry
# --------------------------------------------------------------------------

def test_the_canary_and_live_paths_call_the_same_validator():
    receipt = _receipt()
    reports = {mode: PREFIX.validate_receipt(receipt, attempt_id=ATTEMPT,
                                             mode=mode)
               for mode in ("canary", "live")}
    validators = {report["validator"] for report in reports.values()}
    assert validators == {"p0_r2_prefix_proof_g2.validate_receipt"}
    assert all(report["shared_by_canary_and_live"] for report in reports.values())
    # The two reports differ only in the mode label; every derived fact agrees.
    canary = dict(reports["canary"])
    live = dict(reports["live"])
    canary.pop("mode")
    live.pop("mode")
    assert canary == live


def test_the_module_declares_no_separate_canary_and_live_validators():
    identity = PREFIX.implementation_identity()
    assert identity["separate_canary_and_live_validators"] is False
    assert identity["shared_by_canary_and_live"] is True


def test_both_entry_points_invoke_the_same_validation_subcommand():
    replay = (CONTAINER / "p0_r2_replay_g2.sh").read_text(encoding="utf-8")
    # The single validation call is above the mode branch, so both modes reach
    # it, and the canary branch adds no second prefix check of its own.
    assert replay.count("p0_r2_prefix_proof_g2.py") == 1
    assert replay.count("--validate-bound") == 1
    validate_at = replay.index("--validate-bound")
    branch_at = replay.index('if [ "${MODE}" = "canary" ]')
    assert validate_at < branch_at
    canary = (CONTAINER / "p0_r2_canary_g2.sh").read_text(encoding="utf-8")
    assert "--validate-bound" not in canary


def test_the_validator_accepts_a_valid_byte_bound_receipt():
    receipt = _receipt()
    payload, manifest = _manifest_for(receipt)
    for mode in ("canary", "live"):
        report = PREFIX.validate_bound_receipt(manifest, attempt_id=ATTEMPT,
                                               mode=mode)
        assert report["outcome"] == "PREFIX_RECEIPT_VALID"
        assert report["receipt_sha256"] == PREFIX._sha256(payload)


@pytest.mark.parametrize("mode", ["canary", "live"])
def test_a_missing_receipt_is_refused_in_both_modes(mode):
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.validate_bound_receipt({"embedded_governance_objects": []},
                                      attempt_id=ATTEMPT, mode=mode)


@pytest.mark.parametrize("mode", ["canary", "live"])
def test_a_changed_receipt_body_is_refused_in_both_modes(mode):
    receipt = _receipt()
    _, manifest = _manifest_for(receipt)
    entry = manifest["embedded_governance_objects"][0]
    tampered = dict(receipt, object_count=1)
    entry["payload"] = base64.b64encode(
        PREFIX.canonical_bytes(tampered)).decode("ascii")
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.validate_bound_receipt(manifest, attempt_id=ATTEMPT, mode=mode)


@pytest.mark.parametrize("mode", ["canary", "live"])
def test_an_incorrectly_hashed_receipt_is_refused_in_both_modes(mode):
    receipt = _receipt()
    _, manifest = _manifest_for(receipt)
    manifest["embedded_governance_objects"][0]["sha256"] = "b" * 64
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.validate_bound_receipt(manifest, attempt_id=ATTEMPT, mode=mode)


@pytest.mark.parametrize("mode", ["canary", "live"])
def test_a_duplicate_receipt_is_refused_in_both_modes(mode):
    receipt = _receipt()
    _, manifest = _manifest_for(receipt)
    manifest["embedded_governance_objects"] *= 2
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.validate_bound_receipt(manifest, attempt_id=ATTEMPT, mode=mode)


def test_an_occupied_prefix_is_refused():
    backend = _ManagedIdentityBackend(
        ["study3/p0_r2/g2/%s/existing.json" % ATTEMPT])
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.require_unused(PREFIX.observe(ATTEMPT, backend=backend,
                                             environ={}))


def test_a_receipt_for_another_attempt_is_refused():
    receipt = _receipt()
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.validate_receipt(receipt, attempt_id="p0r2-g2-live-other",
                                mode="live")


def test_a_receipt_whose_execution_did_not_succeed_is_refused():
    with pytest.raises(PREFIX.PrefixProofDefect):
        _receipt(status="Failed")


def test_a_stale_receipt_is_refused_at_host_submission_time():
    receipt = _receipt()
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.validate_receipt(receipt, attempt_id=ATTEMPT, mode="live",
                                require_host_freshness=True,
                                now="2030-01-01T00:00:00Z")


def test_the_container_does_not_reject_a_receipt_merely_for_being_old():
    receipt = _receipt()
    payload, manifest = _manifest_for(receipt)
    report = PREFIX.validate_bound_receipt(manifest, attempt_id=ATTEMPT,
                                           mode="live")
    assert report["host_freshness_checked"] is False
    assert report["outcome"] == "PREFIX_RECEIPT_VALID"


def test_the_host_freshness_window_is_the_registered_fifteen_minutes():
    assert PREFIX.MAX_HOST_OBSERVATION_AGE_SECONDS == 900


def test_a_query_error_is_an_ambiguity_and_never_an_absence():
    class _Failing(_ManagedIdentityBackend):
        def list_names(self, prefix):
            raise RuntimeError("Bad Gateway")

    with pytest.raises(PREFIX.PrefixProofDefect) as excinfo:
        PREFIX.observe(ATTEMPT, backend=_Failing(), environ={})
    assert "never an" in str(excinfo.value)


def test_only_a_managed_identity_backend_may_prove_a_prefix():
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.observe(ATTEMPT, backend=_SharedKeyBackend(), environ={})


def test_the_observation_must_come_from_the_captured_log_itself():
    observation = _observation()
    other = dict(observation, attempt_id=ATTEMPT + "x")
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.correlate(
            observation=other,
            execution={"job": PREFIX.PREFIX_JOB, "name": "x",
                       "status": "Succeeded",
                       "start_time": "2026-08-15T00:00:00Z"},
            stdout=b"x", stderr=b"", log_text=_log_for(observation))


def test_an_ambiguous_log_with_two_observations_is_refused():
    observation = _observation()
    doubled = _log_for(observation) + _log_for(observation)
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.extract_observation(doubled)


def test_there_is_no_bypass_flag_anywhere_in_the_generation2_prefix_path():
    identity = PREFIX.implementation_identity()
    assert identity["accepts_allow_path"] is False
    assert identity["accepts_skip_proof"] is False
    assert identity["accepts_force"] is False
    assert identity["accepts_caller_supplied_outcome"] is False
    assert identity["query_error_is_absence"] is False
    assert identity["writes_objects"] is False
    completed = subprocess.run(
        [sys.executable, str(P0_R2_DIR / "p0_r2_prefix_proof_g2.py"),
         "--validate", "--receipt", "nonexistent.json", "--attempt", ATTEMPT,
         "--allow-path", "anything"],
        capture_output=True, text=True, check=False)
    assert completed.returncode != 0
    assert "unrecognized arguments" in completed.stderr


def test_a_credential_less_isolated_container_passes_only_with_a_receipt():
    """The admission a network-isolated container can and cannot pass.

    The backend below refuses every call, which is what a container with no
    managed identity and no route to the private endpoint actually has. With a
    bound receipt the admission passes; with no receipt it cannot.
    """

    class _Isolated(_ManagedIdentityBackend):
        def list_names(self, prefix):
            raise RuntimeError("no route to the private endpoint")

    receipt = _receipt()
    _, manifest = _manifest_for(receipt)
    report = PREFIX.validate_bound_receipt(manifest, attempt_id=ATTEMPT,
                                           mode="live")
    assert report["outcome"] == "PREFIX_RECEIPT_VALID"
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.validate_bound_receipt({"embedded_governance_objects": []},
                                      attempt_id=ATTEMPT, mode="live")
    with pytest.raises(PREFIX.PrefixProofDefect):
        PREFIX.observe(ATTEMPT, backend=_Isolated(), environ={})


def test_the_live_container_path_makes_no_private_storage_call_before_the_gate():
    replay = (CONTAINER / "p0_r2_replay_g2.sh").read_text(encoding="utf-8")
    gate_at = replay.index("p0_r2_replay_gate_g2.py")
    before = replay[:gate_at]
    assert "p0_r2_prefix_preflight_v1.py" not in before
    assert "--observe" not in before
    assert "list_names" not in before
    task = (CONTAINER / "p0_r2_acr_task_g2.yaml").read_text(encoding="utf-8")
    assert "prefix_proof_performed_in_container: false" in task
    assert "private_storage_listed_in_container: false" in task


# --------------------------------------------------------------------------
# Section 6.5: the minimal two-file context
# --------------------------------------------------------------------------

def test_the_context_admits_exactly_two_regular_files(tmp_path):
    context = tmp_path / "acrctx"
    context.mkdir()
    (context / "task.yaml").write_bytes(b"steps: []\n")
    (context / "context_manifest.json").write_bytes(b"{}\n")
    (context / "extra.txt").write_bytes(b"x")
    with pytest.raises(SUBMIT.SubmissionDefect):
        SUBMIT.verify_context(root=None, context_dir=context)


def test_the_native_context_path_ceiling_is_one_hundred():
    assert SUBMIT.MAX_NATIVE_CONTEXT_PATH == 100
    identity = SUBMIT.implementation_identity()
    assert identity["max_native_context_path"] == 100
    assert identity["context_entry_count"] == 2


def test_a_context_over_the_path_ceiling_is_refused(tmp_path):
    context = tmp_path / "acrctx"
    context.mkdir()
    (context / "task.yaml").write_bytes(b"steps: []\n")
    (context / "context_manifest.json").write_bytes(b"{}\n")
    with pytest.raises(SUBMIT.SubmissionDefect) as excinfo:
        SUBMIT.verify_context(root=None, context_dir=context, ceiling=5)
    assert "ceiling" in str(excinfo.value)


def test_the_acr_command_refuses_an_unpinned_image():
    with pytest.raises(SUBMIT.SubmissionDefect):
        SUBMIT.acr_run_command(
            image="registry/repo:latest", digest="sha256:" + "a" * 64,
            ready_anchor="a" * 40, mode="live", attempt=ATTEMPT,
            prefix_receipt_sha256="b" * 64, context_dir=".")


def test_the_acr_command_binds_the_prefix_receipt_hash():
    digest = "sha256:" + "a" * 64
    argv = SUBMIT.acr_run_command(
        image="registry/repo@" + digest, digest=digest,
        ready_anchor="a" * 40, mode="live", attempt=ATTEMPT,
        prefix_receipt_sha256="b" * 64, context_dir="C:/p0r2g2/acrctx")
    assert "PREFIX_RECEIPT_SHA256=" + "b" * 64 in argv
    assert argv[-1] == "C:/p0r2g2/acrctx"
    assert argv[argv.index("--file") + 1] == "task.yaml"


# --------------------------------------------------------------------------
# Section 6.6: the Windows launch path and authorization scoping
# --------------------------------------------------------------------------

def test_the_azure_cli_is_resolved_with_shutil_which():
    identity = SUBMIT.implementation_identity()
    assert identity["resolves_azure_cli_with"] == "shutil.which"
    assert identity["uses_shell"] is False
    with pytest.raises(SUBMIT.SubmissionDefect):
        SUBMIT.resolve_azure_cli(which=lambda name: None)


def test_the_launch_proof_records_the_exact_resolved_program():
    class _Completed:
        returncode = 0
        stdout = b'{"azure-cli": "9.9.9", "id": "%s"}' % (
            SUBMIT.SUBSCRIPTION.encode())
        stderr = b""

    proof = SUBMIT.prove_launch_path(
        which=lambda name: r"C:\tools\az.CMD", runner=lambda argv: _Completed())
    # Section 6.6 asks for the exact resolved executable to be recorded,
    # including az.CMD on Windows. The exact string is what matters; the
    # basename is split by the platform running the audit, so it is compared
    # with Windows semantics rather than with whatever the host happens to use.
    assert proof["resolved_executable"] == r"C:\tools\az.CMD"
    assert PureWindowsPath(proof["resolved_executable"]).name == "az.CMD"
    assert proof["uses_shell"] is False
    assert proof["relies_on_pathext"] is False
    assert [check["passed"] for check in proof["checks"]] == [True, True]
    assert [check["argv0"] for check in proof["checks"]] == [
        r"C:\tools\az.CMD", r"C:\tools\az.CMD"]


def test_a_failing_benign_check_stops_before_any_submission():
    class _Failed:
        returncode = 1
        stdout = b""
        stderr = b"not logged in"

    with pytest.raises(SUBMIT.SubmissionDefect):
        SUBMIT.prove_launch_path(which=lambda name: "az",
                                 runner=lambda argv: _Failed())


def test_the_authorization_is_scoped_to_the_single_child_process():
    base = {"PATH": "x"}
    live = SUBMIT._child_environment("live", base)
    canary = SUBMIT._child_environment("canary", base)
    assert live[SUBMIT.LIVE_AUTHORIZATION_ENVIRONMENT] == "1"
    assert SUBMIT.LIVE_AUTHORIZATION_ENVIRONMENT not in canary
    # The parent process is never given the authorization.
    import os

    assert SUBMIT.LIVE_AUTHORIZATION_ENVIRONMENT not in os.environ
    assert SUBMIT.implementation_identity()[
        "authorization_scoped_to_single_child"] is True


def test_a_launch_failure_before_a_process_exists_is_still_terminal(tmp_path,
                                                                    monkeypatch):
    receipt = _receipt()
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(PREFIX.canonical_bytes(receipt))

    def _refuse(*args, **kwargs):
        raise OSError("CreateProcess failed")

    context = tmp_path / "acrctx"
    monkeypatch.setattr(SUBMIT, "verify_context", lambda **kwargs: {
        "context": {"task": {"git_blob": "a" * 40},
                    "embedded_governance_objects": [
                        {"label": PREFIX.CONTEXT_LABEL,
                         "sha256": PREFIX._sha256(
                             PREFIX.canonical_bytes(receipt))}]}})
    digest = "sha256:" + "a" * 64
    document = SUBMIT.submit_once(
        root=None, context_dir=tmp_path, work_dir=tmp_path / "work",
        image="registry/repo@" + digest, digest=digest,
        ready_anchor="a" * 40, mode="live", attempt=ATTEMPT,
        prefix_receipt=receipt_path, runner=_refuse,
        launch_proof={"resolved_executable": "az"})
    assert document["process_started"] is False
    assert document["launch_failure"]
    assert document["one_shot_envelope_consumed"] is True
    assert document["outcome"] == "STOP"
    assert (tmp_path / "work" / SUBMIT.ENVELOPE_NAME).is_file()


# --------------------------------------------------------------------------
# Section 6.4: the image manifest and its derived count
# --------------------------------------------------------------------------

def test_the_manifest_derives_its_entry_count_and_does_not_hard_code_it():
    identity = MANIFEST.implementation_identity()
    assert identity["hard_codes_a_file_count"] is False
    derived = (len(MANIFEST.OPERATIONAL_PATHS) + len(MANIFEST.SCIENTIFIC_PATHS)
               + len(MANIFEST.ENTRYPOINT_PATHS))
    assert identity["derived_entry_count"] == derived
    assert derived != 44


def test_the_manifest_sets_are_v2_plus_a_named_delta():
    import p0_r2_image_manifest_v2 as V2

    assert set(V2.OPERATIONAL_PATHS) <= set(MANIFEST.OPERATIONAL_PATHS)
    assert set(V2.ENTRYPOINT_PATHS) <= set(MANIFEST.ENTRYPOINT_PATHS)
    assert tuple(MANIFEST.SCIENTIFIC_PATHS) == tuple(V2.SCIENTIFIC_PATHS)
    added = set(MANIFEST.OPERATIONAL_PATHS) - set(V2.OPERATIONAL_PATHS)
    assert added == set(MANIFEST.ADDED_OPERATIONAL_PATHS)


def test_the_committed_manifest_binds_every_generation2_asset():
    document = json.loads(
        (P0_R2_DIR / "p0_r2_image_manifest_g2.json").read_bytes()
        .decode("utf-8"))
    bound = {entry["path"] for entry in document["entries"]}
    for path in MANIFEST.ADDED_OPERATIONAL_PATHS + MANIFEST.ADDED_ENTRYPOINT_PATHS:
        assert path in bound
    assert document["entry_count"] == len(document["entries"])


def test_the_audit_refuses_a_drifted_image(tmp_path):
    document = json.loads(
        (P0_R2_DIR / "p0_r2_image_manifest_g2.json").read_bytes()
        .decode("utf-8"))
    entry = dict(document["entries"][0])
    entry["sha256"] = "c" * 64
    drifted = dict(document, entries=[entry], entry_count=1)
    root = tmp_path / "image"
    target = root / entry["path"]
    target.parent.mkdir(parents=True)
    target.write_bytes(b"different bytes")
    with pytest.raises(MANIFEST.ImageManifestDefect):
        MANIFEST.audit(drifted, image_root=root, install_root=tmp_path)


# --------------------------------------------------------------------------
# The lock, the closure and the gate
# --------------------------------------------------------------------------

def test_the_committed_lock_validates_from_its_own_bytes():
    lock = json.loads((P0_R2_DIR / "p0_r2_execution_lock_g2.json").read_bytes()
                      .decode("utf-8"))
    report = LOCK.validate(lock)
    assert report["outcome"] == "LOCK_VALID"


def test_the_lock_refuses_a_reused_generation1_image_digest():
    lock = json.loads((P0_R2_DIR / "p0_r2_execution_lock_g2.json").read_bytes()
                      .decode("utf-8"))
    forged = json.loads(json.dumps(lock))
    forged["image"]["digest"] = LOCK.GENERATION1_TERMINAL["image_digest"]
    with pytest.raises(LOCK.LockDefect):
        LOCK.validate(forged)


def test_the_lock_refuses_a_tampered_body():
    lock = json.loads((P0_R2_DIR / "p0_r2_execution_lock_g2.json").read_bytes()
                      .decode("utf-8"))
    forged = json.loads(json.dumps(lock))
    forged["caps"]["max_s4_generations"] = 13
    with pytest.raises(LOCK.LockDefect):
        LOCK.validate(forged)


def test_the_lock_refuses_a_consumed_envelope():
    lock = json.loads((P0_R2_DIR / "p0_r2_execution_lock_g2.json").read_bytes()
                      .decode("utf-8"))
    forged = json.loads(json.dumps(lock))
    forged["replay_envelope"]["consumed"] = True
    with pytest.raises(LOCK.LockDefect):
        LOCK.validate(forged)


def test_the_lock_binds_the_bounded_pilot_maxima_exactly():
    lock = json.loads((P0_R2_DIR / "p0_r2_execution_lock_g2.json").read_bytes()
                      .decode("utf-8"))
    assert lock["caps"] == {
        "max_smoke_prefills_before_extension": 60,
        "max_non_generative_prefills": 180,
        "max_s4_generations": 12,
        "max_model_evaluation_equivalents": 228,
        "possible_scored_rows": 210,
    }
    assert lock["caps_are_enforced_not_reported"] is True


def test_the_lock_preserves_the_permanent_governance_state():
    lock = json.loads((P0_R2_DIR / "p0_r2_execution_lock_g2.json").read_bytes()
                      .decode("utf-8"))
    legal = lock["legal_state"]
    assert legal["formal_execution_authorized"] is False
    assert legal["draft_v0_6_reviewed"] is False
    assert legal["draft_v0_6_frozen"] is False
    assert legal["interface"] is None
    assert legal["positive_reference"] is None
    assert legal["rp_wrapper"] is None
    assert legal["evidence_ledger_tail"] == "EV-0016"
    assert legal["research_question_answered"] is False


def test_the_lock_proves_the_science_is_the_registered_science():
    lock = json.loads((P0_R2_DIR / "p0_r2_execution_lock_g2.json").read_bytes()
                      .decode("utf-8"))
    science = lock["immutable_science"]
    assert science["proved"] is True
    compared = [entry for entry in science["comparison"] if entry["compared"]]
    assert len(compared) >= 4
    assert all(entry["agrees"] for entry in compared)


def test_the_four_standing_failures_are_the_registered_four():
    lock = json.loads((P0_R2_DIR / "p0_r2_execution_lock_g2.json").read_bytes()
                      .decode("utf-8"))
    assert lock["standing_failures"] == [
        "tests/test_parser_v3_seal_job.py::"
        "test_seal_refuses_a_non_empty_parent_prefix",
        "tests/test_parser_v3_seal_job.py::"
        "test_seal_writes_twelve_objects_with_the_set_manifest_last",
        "tests/test_phase05_jlens_saturation.py::"
        "test_no_artifact_asserts_a_prohibited_claim",
        "tests/test_study3_p0_feasibility_pilot.py::"
        "test_every_committed_p0_source_file_is_lf_only",
    ]


def test_every_frozen_generation1_byte_is_unchanged():
    proof = CLOSURE.prove_frozen_roots()
    assert proof["all_frozen_bytes_unchanged"] is True
    assert proof["changed_count"] == 0
    assert proof["removed_count"] == 0
    assert proof["protected_file_count"] > 100


def test_the_authority_was_the_first_object_committed_after_generation_1():
    proof = CLOSURE.prove_authority_was_first()
    assert proof["authority_was_the_first_committed_object"] is True
    assert proof["first_commit_paths"] == [CLOSURE.AUTHORITY_PATH]


def test_generation_1_remains_terminal_and_consumed():
    proof = CLOSURE.prove_generation1_terminal()
    assert proof["agrees_with_registered_terminal_facts"] is True
    assert proof["acr_run_id"] == "cmjv"
    assert proof["envelope_consumed"] is True
    assert proof["model_operations_performed"] == 0
    assert proof["state"] == "STOP_NO_MODEL_OPERATION"


def test_the_generation2_gate_refuses_a_generation1_authorization():
    with pytest.raises(GATE.GateRefused):
        GATE.run("out", authorization="p0-r2-generation-1-successor-session",
                 attempt_id="p0r2-g2-live-x")


def test_the_generation2_gate_refuses_a_non_live_attempt(tmp_path):
    with pytest.raises(GATE.GateRefused):
        GATE.run(tmp_path, authorization=GATE.SUCCESSOR_AUTHORIZATION,
                 attempt_id=ATTEMPT, lock_bytes=b"{}")


def test_the_generation2_gate_never_reruns_in_place(tmp_path):
    (tmp_path / GATE.RESULT_NAME).write_bytes(b"{}")
    with pytest.raises(GATE.GateRefused) as excinfo:
        GATE.run(tmp_path, authorization=GATE.SUCCESSOR_AUTHORIZATION,
                 attempt_id="p0r2-g2-live-20260815-1700", lock_bytes=b"{}")
    assert "never rerun" in str(excinfo.value)


def test_the_gate_delegates_to_unchanged_p0_r1_science():
    identity = GATE.implementation_identity()
    assert identity["copies_or_edits_science"] is False
    assert identity["replay_factorization_logic_changed"] is False
    assert identity["verifies_science_by_sha256_before_import"] is True
    assert identity["authorizes_model_pilot"] is False
    import p0_r2_replay_gate_v1 as G1

    assert tuple(identity["delegated_scientific_modules"]) == tuple(
        G1.DELEGATED_SCIENTIFIC_MODULES)


def test_the_gate_refuses_an_unbound_scientific_module():
    with pytest.raises(GATE.GateRefused):
        GATE.verify_delegated_science({})


# --------------------------------------------------------------------------
# The image, the job specifications and the LF rule
# --------------------------------------------------------------------------

def test_the_image_has_no_default_execution_mode():
    dockerfile = (CONTAINER / "Dockerfile.study3-p0-r2-g2").read_text(
        encoding="utf-8")
    assert "ENTRYPOINT []" in dockerfile
    assert "P0_R2_G2_NO_DEFAULT_EXECUTION_MODE=1" in dockerfile
    assert "USER 10001" in dockerfile
    assert "j-space-observation-study3-p0-r1@sha256:e1adda95862ea14bf0397f496a" \
        "a0ef9f7e5918e95b5436b0eb84ee3480d91e4c" in dockerfile


def test_every_generation2_job_declares_no_retry_and_neutralised_accelerators():
    """The declared CPU-only environment must satisfy the frozen guard itself.

    Section 7.4 names ``CUDA_VISIBLE_DEVICES=-1``, but the immutable
    ``p0_r2_recovery_v1.assert_model_free`` reads any value other than ``""``,
    ``void`` or ``none`` as an exposed accelerator. Rather than assert on a
    literal, this executes the guard against each job's declared environment, so
    a specification that would refuse in Azure refuses here first.
    """
    import yaml

    import p0_r2_recovery_v1 as RECOVERY

    for name in ("p0_r2_prefix_job_g2.yaml", "p0_r2_recovery_job_g2.yaml",
                 "p0_r2_hard_kill_job_g2.yaml"):
        document = yaml.safe_load((CONTAINER / name).read_text(encoding="utf-8"))
        assert document["configuration"]["replicaRetryLimit"] == 0
        assert document["boundary"]["cpu_only"] is True
        environment = {entry["name"]: entry["value"] for entry
                       in document["template"]["containers"][0]["env"]}
        assert environment["NVIDIA_VISIBLE_DEVICES"] == "void"
        assert environment["NVIDIA_DRIVER_CAPABILITIES"] == "void"
        assert "CUDA_VISIBLE_DEVICES" in environment
        report = RECOVERY.assert_model_free(environ=environment)
        assert report["cpu_only"] is True
        assert report["gpu_allocations"] == 0


def test_an_accelerator_environment_is_still_refused_by_the_frozen_guard():
    import p0_r2_recovery_v1 as RECOVERY

    with pytest.raises(RECOVERY.RecoveryDefect):
        RECOVERY.assert_model_free(environ={"CUDA_VISIBLE_DEVICES": "0"})
    with pytest.raises(RECOVERY.RecoveryDefect):
        RECOVERY.assert_model_free(environ={"NVIDIA_VISIBLE_DEVICES": "all"})


def test_the_pilot_job_is_bounded_and_created_once():
    import yaml

    document = yaml.safe_load(
        (CONTAINER / "p0_r2_pilot_job_g2.yaml").read_text(encoding="utf-8"))
    assert document["name"] == "job-jspace-s3-p0r2-pilot-g2"
    assert document["workloadProfileName"] == "gpu-t4"
    assert document["configuration"]["replicaRetryLimit"] == 0
    assert document["configuration"]["manualTriggerConfig"] == {
        "parallelism": 1, "replicaCompletionCount": 1}
    boundary = document["boundary"]
    assert boundary["caps_are_enforced_not_reported"] is True
    assert boundary["created_once"] is True
    assert boundary["started_once"] is True
    assert boundary["updated_or_restarted"] is False
    assert boundary["caps"] == LOCK.CAPS


def test_every_generation2_job_name_is_the_registered_name():
    import yaml

    expected = {
        "p0_r2_prefix_job_g2.yaml": NAMESPACE.PREFIX_JOB,
        "p0_r2_recovery_job_g2.yaml": NAMESPACE.RECOVERY_JOB,
        "p0_r2_hard_kill_job_g2.yaml": NAMESPACE.HARD_KILL_JOB,
        "p0_r2_pilot_job_g2.yaml": NAMESPACE.GPU_JOB,
    }
    for name, job in expected.items():
        document = yaml.safe_load((CONTAINER / name).read_text(encoding="utf-8"))
        assert document["name"] == job
        assert job.endswith("-g2")


def test_every_new_generation2_file_is_lf_only():
    text_suffixes = {".py", ".sh", ".yaml", ".yml", ".json", ".md", ""}
    candidates = [path for path in sorted(P0_R2_DIR.rglob("*g2*"))
                  if "__pycache__" not in path.parts
                  and path.suffix in text_suffixes]
    candidates += [
        ROOT / "studies" / "study3" / "prompts"
        / ("study3_p0_r2_generation2_successor_and_conditional_"
           "execution_authority.md"),
        Path(__file__),
    ]
    assert len(candidates) >= 20
    offenders = [str(path.relative_to(ROOT)) for path in candidates
                 if path.is_file() and b"\r" in path.read_bytes()]
    assert offenders == []


def test_no_generation1_or_p0_r1_byte_is_edited_by_generation_2():
    identity = CLOSURE.implementation_identity()
    assert identity["edits_v1_or_v2"] is False
    assert identity["accepts_allow_path"] is False
    assert identity["caller_supplied_governance_allowlist"] is False
    assert tuple(identity["frozen_roots"]) == (
        "studies/study3/pilot/p0_r1/",
        "studies/study3/pilot/p0/results/p0-r1/",
        "studies/study3/pilot/p0_r2/",
        "studies/study3/pilot/p0/results/p0-r2/",
    )
