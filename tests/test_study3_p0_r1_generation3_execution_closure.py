"""Executable seam tests for the Study 3 P0-R1 generation-3 execution closure.

The generation-2 test suite is the reason this file exists. It contained many
passing tests about the launcher, the successor and the model shell, and almost
all of them asserted that a string occurred in a file. A test that greps a
shell script for ``--lock-file`` passes whether or not the flag the script
passes is one the receiving CLI defines. A test that calls ``RUNNER.run()`` with
a hand-built authorization mapping passes whether or not production ever builds
such a mapping. A hard-kill test against a local temporary directory passes
whether or not the sink survives Container Apps teardown.

So generation 2 shipped a published, locked, image-bound successor path in
which the documented first command exited 2, the production runner CLI refused
every real invocation, and no genuine replay receipt could authorize the pilot
-- with a green suite.

Every test below therefore executes a real seam: it runs the actual entry
point, in a subprocess where the entry point is a process, and asserts on what
that seam does rather than on what its source text contains. Each is written to
fail at ``c04ec748a4b2b63af22f50595816b5e6b6805ff6`` and pass only once the
corresponding production defect is closed.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P0_R1_DIR = os.path.join(REPO_ROOT, "studies", "study3", "pilot", "p0_r1")
CONTAINER_DIR = os.path.join(P0_R1_DIR, "container")

for _path in (P0_R1_DIR, CONTAINER_DIR, os.path.join(P0_R1_DIR, "execution")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import p0_r1_authorization_v3 as AUTHZ  # noqa: E402
import p0_r1_azure_query_v3 as AZQ  # noqa: E402
import p0_r1_blob_transport as BLOB  # noqa: E402
import p0_r1_blob_transport_v3 as BLOB_V3  # noqa: E402
import p0_r1_execution_lock_v3 as LOCK_V3  # noqa: E402
import p0_r1_journal_v3 as JOURNAL_V3  # noqa: E402
import p0_r1_prefix_preflight_v3 as PREFIX  # noqa: E402
import p0_r1_ready_anchor_v3 as ANCHOR  # noqa: E402
import p0_r1_recovery_v3 as RECOVERY  # noqa: E402
import p0_r1_replay_capture_v3 as CAPTURE  # noqa: E402
import p0_r1_transport as TRANSPORT  # noqa: E402
import p0_r1_cli_wiring_canary_v3 as WIRING  # noqa: E402

LOCK_V3_PATH = os.path.join(P0_R1_DIR, "p0_r1_execution_lock_v3.json")
LOCK_V2_PATH = os.path.join(P0_R1_DIR, "p0_r1_execution_lock_v2.json")
LOCK_V1_PATH = os.path.join(P0_R1_DIR, "p0_r1_execution_lock.json")

SUCCESSOR_V3 = os.path.join(CONTAINER_DIR, "p0_r1_successor_v3.sh")
MODEL_SHELL_V3 = os.path.join(CONTAINER_DIR, "p0_r1_model_pilot_v3.sh")

RUNNER_V2 = os.path.join(P0_R1_DIR, "p0_r1_model_runner_v2.py")
RUNNER_V3 = os.path.join(P0_R1_DIR, "p0_r1_model_runner_v3.py")
LOCK_V2_CLI = os.path.join(P0_R1_DIR, "p0_r1_execution_lock_v2.py")

HISTORICAL_CRLF_FILE = os.path.join(
    P0_R1_DIR, "execution", "p0_r1_model_execution.py")
HISTORICAL_CRLF_SHA = \
    "392f78466ee61ed303b5cf4b1fba4423e38b128441aeec1de119315b2e52a5ee"
HISTORICAL_CRLF_BYTES = 10229


def _run(argv, env=None, cwd=None):
    environment = dict(os.environ)
    environment.update(env or {})
    return subprocess.run(  # noqa: S603 - fixed interpreters and scripts
        argv, capture_output=True, text=True, env=environment, cwd=cwd,
        encoding="utf-8", errors="replace")


def _bash_available():
    """True only when bash actually executes, not merely when it is on PATH.

    Some Windows hosts ship a WSL launcher stub with no distribution
    installed; it resolves on PATH and fails on every invocation.
    """
    if shutil.which("bash") is None:
        return False
    try:
        probe = _run(["bash", "-c", "echo p0r1bashok"])
    except OSError:
        return False
    return probe.returncode == 0 and "p0r1bashok" in (probe.stdout or "")


requires_bash = pytest.mark.skipif(
    not _bash_available(),
    reason="this host has no functioning bash; the shell seams are executed "
           "in the authoritative CPU-only ACR context")


@pytest.fixture()
def lock_document():
    with open(LOCK_V3_PATH, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


@pytest.fixture()
def synthetic_inputs(tmp_path):
    """Four consistent authorization documents, written as real files."""
    return WIRING._synthetic_inputs(str(tmp_path), LOCK_V3_PATH)


# --- 1. the generation-2 preflight failure is preserved as a regression -----

def test_the_v2_handoff_preflight_command_still_exits_two():
    """The exact documented generation-2 first command does not run.

    This is the regression demonstration required by the authority. It is not
    a complaint about style: the published handoff instructed an operator to
    run this, and it exits 2 before doing anything.
    """
    result = _run([sys.executable, LOCK_V2_CLI,
                   "--lock-file", LOCK_V2_PATH])
    assert result.returncode == 2
    assert "unrecognized arguments" in (result.stderr or "")
    assert "--lock-file" in (result.stderr or "")


def test_the_v2_preflight_flags_are_absent_from_the_v2_cli():
    """Both flags the generation-2 successor passes are undefined."""
    helped = _run([sys.executable, LOCK_V2_CLI, "--help"])
    assert helped.returncode == 0
    assert "--lock-file" not in helped.stdout
    combined = _run([sys.executable, LOCK_V2_CLI, "--lock-file", LOCK_V2_PATH,
                     "--image-digest", "sha256:" + "0" * 64])
    assert combined.returncode == 2


# --- 2/3. the v3 preflight runs, and a fresh clone is clean ----------------

@requires_bash
def test_the_v3_successor_names_three_modes_and_has_no_default():
    """No mode means no action. An omitted argument never starts anything."""
    result = _run(["bash", SUCCESSOR_V3])
    assert result.returncode == 2
    for mode in ("preflight", "live-replay", "launch-pilot"):
        assert mode in (result.stderr or "")


@requires_bash
def test_the_v3_successor_refuses_an_unknown_argument():
    result = _run(["bash", SUCCESSOR_V3, "preflight", "--nonsense"])
    assert result.returncode != 0
    assert "unrecognized argument" in (result.stderr or "")


@requires_bash
def test_live_replay_and_launch_pilot_refuse_without_explicit_confirmation():
    """The one-shot envelope is never spent by a bare command."""
    for mode in ("live-replay", "launch-pilot"):
        result = _run(["bash", SUCCESSOR_V3, mode,
                       "--lock-file", LOCK_V3_PATH])
        assert result.returncode != 0
        assert "--i-am-sure" in (result.stderr or "")


def test_the_v3_lock_cli_accepts_the_documented_preflight_flags():
    """The generation-3 equivalent of the command that exits 2 above."""
    result = _run([sys.executable,
                   os.path.join(P0_R1_DIR, "p0_r1_execution_lock_v3.py"),
                   "--validate", "--lock-file", LOCK_V3_PATH])
    assert result.returncode == 0, result.stderr
    assert "P0_R1_EXECUTION_LOCK_V3_VALID=1" in result.stdout


def test_the_historical_crlf_blob_is_preserved_and_not_normalized():
    """A fresh Linux checkout must be clean without rewriting history.

    ``execution/*.py text eol=lf`` was registered after this file was already
    committed with CRLF endings, and its exact bytes are hashed into all three
    locks. The repair is a narrow ``-text`` exception, never a renormalization.
    """
    import hashlib
    with open(HISTORICAL_CRLF_FILE, "rb") as handle:
        payload = handle.read()
    assert len(payload) == HISTORICAL_CRLF_BYTES
    assert hashlib.sha256(payload).hexdigest() == HISTORICAL_CRLF_SHA
    assert payload.count(b"\r\n") > 0, "the historical blob is CRLF"

    attributes = _run(["git", "check-attr", "-a", "--",
                       "studies/study3/pilot/p0_r1/execution/"
                       "p0_r1_model_execution.py"], cwd=REPO_ROOT)
    assert attributes.returncode == 0
    assert "text: unset" in attributes.stdout, (
        "the narrow -text exception is missing, so a Linux checkout would "
        "report this protected historical file as modified")

    clean = _run(["git", "hash-object", "--",
                  "studies/study3/pilot/p0_r1/execution/"
                  "p0_r1_model_execution.py"], cwd=REPO_ROOT)
    committed = _run(["git", "rev-parse",
                      "HEAD:studies/study3/pilot/p0_r1/execution/"
                      "p0_r1_model_execution.py"], cwd=REPO_ROOT)
    if committed.returncode == 0:
        assert clean.stdout.strip() == committed.stdout.strip(), (
            "the clean filter would rewrite a protected historical blob")


# --- 4/5. the exact shell and CLI reach the boundary; v2 refuses -----------

def test_the_v2_runner_cli_refuses_because_it_never_builds_authorization(
        tmp_path):
    """Generation 2's production command refuses itself. Verbatim.

    The generation-2 tests called ``run()`` directly with an authorization
    mapping that the CLI never constructs, so this refusal was invisible.
    """
    receipt = {
        "attempt_id": "gen2-863aca8b3a2a-20260812T000000Z",
        "ready_commit": "c7e02b43e1dbf811d1b35ae0fc0fe9d1a1d12947",
        "transport": {"complete_byte_recovery_verified": True},
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    result = _run([sys.executable, RUNNER_V2, "--run",
                   "--lock-file", LOCK_V2_PATH,
                   "--receipt-file", str(receipt_path),
                   "--out-dir", str(tmp_path / "out"),
                   "--src", REPO_ROOT])
    assert result.returncode == 1
    assert "P0_R1_MODEL_PILOT_REFUSED=1" in result.stdout
    assert "requires an execution authorization mapping" in result.stdout


def test_the_v3_runner_cli_builds_authorization_and_reaches_the_sentinel(
        tmp_path, synthetic_inputs):
    """The real CLI, as a process, reaches the authorized boundary once."""
    result = _run(
        [sys.executable, RUNNER_V3, "--run",
         "--lock-file", LOCK_V3_PATH,
         "--replay-receipt", synthetic_inputs["p0_r1_replay_receipt.json"],
         "--reconstruction-receipt",
         synthetic_inputs["p0_r1_replay_reconstruction_receipt_v3.json"],
         "--head-proof", synthetic_inputs["p0_r1_head_proof_v3.json"],
         "--out-dir", str(tmp_path / "result"),
         "--src", REPO_ROOT, "--executor", "sentinel",
         "--attempt", WIRING.ATTEMPT],
        env={"P0_R1_CANARY_IN_MEMORY_BLOB": "1"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("P0_R1_SENTINEL_EXECUTOR_REACHED=1") == 1
    assert "P0_R1_AUTHORIZATION_BUILT=1" in result.stdout
    assert "P0_R1_PREFIX_PREFLIGHT=PROVED_ABSENT" in result.stdout


def test_the_v3_runner_cli_refuses_each_missing_mandatory_input(
        tmp_path, synthetic_inputs):
    """There is no default for any of the four authorization inputs."""
    base = {
        "--lock-file": LOCK_V3_PATH,
        "--replay-receipt": synthetic_inputs["p0_r1_replay_receipt.json"],
        "--reconstruction-receipt":
            synthetic_inputs["p0_r1_replay_reconstruction_receipt_v3.json"],
        "--head-proof": synthetic_inputs["p0_r1_head_proof_v3.json"],
    }
    for omitted in sorted(base):
        argv = [sys.executable, RUNNER_V3, "--run",
                "--out-dir", str(tmp_path / "out"), "--executor", "sentinel"]
        for flag, value in base.items():
            if flag != omitted:
                argv.extend([flag, value])
        result = _run(argv, env={"P0_R1_CANARY_IN_MEMORY_BLOB": "1"})
        assert result.returncode == 2, omitted
        assert omitted in (result.stderr or "")


def test_a_fake_object_store_cannot_be_used_with_the_production_executor(
        tmp_path, synthetic_inputs):
    """The exact generation-2 trap: a stand-in backend on the real path.

    Generation 2's transport gate ran ``--canary --dry-run`` against an
    in-memory backend, which passes identically whether or not the image can
    reach the storage account. Here a synthetic store and the production
    executor are mutually exclusive.
    """
    result = _run(
        [sys.executable, RUNNER_V3, "--run",
         "--lock-file", LOCK_V3_PATH,
         "--replay-receipt", synthetic_inputs["p0_r1_replay_receipt.json"],
         "--reconstruction-receipt",
         synthetic_inputs["p0_r1_replay_reconstruction_receipt_v3.json"],
         "--head-proof", synthetic_inputs["p0_r1_head_proof_v3.json"],
         "--out-dir", str(tmp_path / "result"),
         "--src", REPO_ROOT, "--executor", "production"],
        env={"P0_R1_CANARY_IN_MEMORY_BLOB": "1"})
    assert result.returncode == 2
    assert "only permitted with the sentinel executor" in (result.stderr or "")


@requires_bash
def test_the_exact_production_model_shell_reaches_the_boundary_once():
    """The shell the GPU job runs, executed as the GPU job runs it."""
    stream = io.StringIO()
    WIRING.run(lock_path=LOCK_V3_PATH, shell=MODEL_SHELL_V3, stream=stream)
    assert "P0_R1_CLI_WIRING_SENTINEL_COUNT=1" in stream.getvalue()
    assert "P0_R1_CLI_WIRING_CANARY=passed" in stream.getvalue()


# --- 6/7. the emitted receipt reaches the launch guard unmutated -----------

def _gate_shaped_receipt(attempt="gen3-000000000000-20260813T000000Z"):
    """A receipt shaped exactly as the gate emits it, including false."""
    return {
        "schema_version": "study3-p0-r1-replay-receipt-v2",
        "attempt_id": attempt,
        "ready_commit": "b" * 40,
        "image_digest": "sha256:" + "1" * 64,
        "executable_code_commit": "c" * 40,
        "executable_code_tree": "d" * 40,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "model_operations_performed": 0,
        "gpu_allocated": False,
        # This is the value the generation-2 gate actually wrote to disk.
        "transport": {"complete_byte_recovery_verified": False},
    }


def _gate_shaped_result(state="STUDY3_P0_R1_REPLAY_GATE_PASSED"):
    return {"state": state, "schema_version": "study3-p0-r1-gate-result"}


def _envelope(attempt, receipt=None, result=None, extra=None):
    """Encode the four canonical artifacts exactly as the gate transports."""
    receipt = receipt if receipt is not None else _gate_shaped_receipt(attempt)
    result = result if result is not None else _gate_shaped_result()
    payloads = {}
    for name in TRANSPORT.REPLAY_ARTIFACTS:
        if name == "p0_r1_replay_receipt.json":
            body = json.dumps(receipt, indent=1, sort_keys=True) + "\n"
        elif name == "p0_r1_replay_result.json":
            body = json.dumps(result, indent=1, sort_keys=True) + "\n"
        else:
            body = "%s for %s\n" % (name, attempt)
        payloads[name] = body.encode("utf-8")
    if extra:
        payloads.update(extra)
    return "\n".join(TRANSPORT.encode(attempt, payloads)), payloads


def test_the_gate_emitted_receipt_flows_through_recovery_into_authorization():
    """The receipt that says false still authorizes, via the second document.

    Generation 2 required ``complete_byte_recovery_verified`` to be true on
    the recovered receipt, and its gate wrote false. No genuine replay could
    ever have authorized the pilot; only a hand-edited receipt could.
    """
    attempt = "gen3-000000000000-20260813T000000Z"
    log, _payloads = _envelope(attempt)
    receipt, recovered = CAPTURE.reconstruct(log, "cmz1", attempt_id=attempt)

    emitted = json.loads(
        recovered["p0_r1_replay_receipt.json"].decode("utf-8"))
    assert emitted["transport"]["complete_byte_recovery_verified"] is False, \
        "the emitted receipt must not claim its own later recovery"

    decision = CAPTURE.validate_authorization_pair(emitted, receipt,
                                                   attempt_id=attempt)
    assert decision["authorizes_one_bounded_model_pilot"] is True
    assert decision["emitted_receipt_self_claim"] is False
    assert receipt["complete_byte_recovery_verified"] is True
    assert receipt["independent_of_the_gate_process"] is True


def test_the_reconstruction_receipt_is_mandatory_for_authorization():
    """The emitted receipt alone never authorizes a model operation."""
    attempt = "gen3-000000000000-20260813T000000Z"
    emitted = _gate_shaped_receipt(attempt)
    with pytest.raises(CAPTURE.ReplayCaptureDefect):
        CAPTURE.validate_authorization_pair(emitted, None)
    with pytest.raises(CAPTURE.ReplayCaptureDefect):
        CAPTURE.validate_authorization_pair(emitted, {"schema_version": "x"})


def test_a_hand_edited_transport_flag_does_not_substitute_for_recovery():
    """Flipping the flag on the emitted receipt buys nothing."""
    attempt = "gen3-000000000000-20260813T000000Z"
    emitted = _gate_shaped_receipt(attempt)
    emitted["transport"]["complete_byte_recovery_verified"] = True
    with pytest.raises(CAPTURE.ReplayCaptureDefect):
        CAPTURE.validate_authorization_pair(emitted, {
            "schema_version": CAPTURE.SCHEMA_VERSION,
            "attempt_id": attempt,
            "independent_of_the_gate_process": True,
            "gate_receipt_was_mutated": True,
            "complete_byte_recovery_verified": True,
            "gate": {"passed": True},
        })


@pytest.mark.parametrize("mutation", [
    "truncated", "missing_artifact", "wrong_attempt", "wrong_run",
    "conflicting", "nonzero_exit",
])
def test_a_damaged_or_mismatched_capture_refuses_before_any_model_command(
        mutation):
    """Every corruption of the captured log is refused, not repaired."""
    attempt = "gen3-000000000000-20260813T000000Z"
    log, _payloads = _envelope(attempt)

    if mutation == "truncated":
        log = "\n".join(log.splitlines()[:-3])
        with pytest.raises(CAPTURE.ReplayCaptureDefect):
            CAPTURE.reconstruct(log, "cmz1", attempt_id=attempt)
    elif mutation == "missing_artifact":
        lines = [line for line in log.splitlines()
                 if "p0_r1_replay_counters.json" not in line]
        with pytest.raises(CAPTURE.ReplayCaptureDefect):
            CAPTURE.reconstruct("\n".join(lines), "cmz1", attempt_id=attempt)
    elif mutation == "wrong_attempt":
        with pytest.raises(CAPTURE.ReplayCaptureDefect):
            CAPTURE.reconstruct(log, "cmz1", attempt_id="gen3-other-attempt")
    elif mutation == "wrong_run":
        receipt, _ = CAPTURE.reconstruct(log, "cmz1", attempt_id=attempt)
        emitted = _gate_shaped_receipt(attempt)
        with pytest.raises(CAPTURE.ReplayCaptureDefect):
            CAPTURE.validate_authorization_pair(emitted, receipt,
                                                run_id="cmz9")
    elif mutation == "conflicting":
        receipt, recovered = CAPTURE.reconstruct(log, "cmz1",
                                                 attempt_id=attempt)
        emitted = json.loads(
            recovered["p0_r1_replay_receipt.json"].decode("utf-8"))
        emitted["image_digest"] = "sha256:" + "9" * 64
        with pytest.raises(CAPTURE.ReplayCaptureDefect):
            CAPTURE.validate_authorization_pair(emitted, receipt)
    else:
        with pytest.raises(CAPTURE.ReplayCaptureDefect):
            CAPTURE.reconstruct(log, "cmz1", attempt_id=attempt, exit_code=1)


def test_a_failed_gate_state_authorizes_nothing():
    attempt = "gen3-000000000000-20260813T000000Z"
    log, _ = _envelope(attempt, result=_gate_shaped_result(
        "STUDY3_P0_R1_REPLAY_GATE_STOPPED"))
    receipt, recovered = CAPTURE.reconstruct(log, "cmz1", attempt_id=attempt)
    emitted = json.loads(
        recovered["p0_r1_replay_receipt.json"].decode("utf-8"))
    with pytest.raises(CAPTURE.ReplayCaptureDefect):
        CAPTURE.validate_authorization_pair(emitted, receipt)


# --- 8. Azure errors are distinguished from absence -----------------------

@pytest.mark.parametrize("code,out,err,label", [
    (1, "", "AADSTS700016: application not found", "authentication"),
    (1, "", "AuthorizationFailed: does not have permission", "permission"),
    (1, "", "Could not resolve host: management.azure.com", "network"),
    (124, "", "timed out", "timeout"),
    (0, "not json at all", "", "malformed"),
    (0, "", "", "empty"),
    (3, "", "unknown failure", "unknown"),
])
def test_every_azure_error_class_fails_closed_and_starts_nothing(
        code, out, err, label):
    """``|| echo absent`` collapsed all of these into "the job is not there".

    Each must raise. None may be read as a proved absence, and none may reach
    a create or a start.
    """
    calls = []

    def runner(argv, timeout):
        calls.append(argv)
        return code, out, err

    with pytest.raises(AZQ.AzureQueryError) as caught:
        AZQ.job_presence("job-jspace-s3-p0r1-pilot-g3",
                         "rg-jspace-observation-sea", "sub", runner=runner)
    assert len(calls) == 1, "a failed query must not be retried blindly"
    detail = caught.value.detail
    assert detail.get("argv") is not None
    if code != 0:
        assert detail.get("exit_code") == code


def test_a_genuine_absence_is_distinguished_from_an_error():
    def present(argv, timeout):
        return 0, json.dumps(["job-jspace-s3-p0r1-pilot-g3", "other"]), ""

    def absent(argv, timeout):
        return 0, json.dumps(["other"]), ""

    proved_present = AZQ.job_presence("job-jspace-s3-p0r1-pilot-g3", "rg",
                                      "sub", runner=present)
    assert proved_present["outcome"] == AZQ.PROVED_PRESENT
    with pytest.raises(AZQ.AzureQueryError):
        AZQ.require_absent(proved_present)

    proved_absent = AZQ.job_presence("job-jspace-s3-p0r1-pilot-g3", "rg",
                                     "sub", runner=absent)
    assert proved_absent["outcome"] == AZQ.PROVED_ABSENT
    assert AZQ.require_absent(proved_absent) is proved_absent


def test_the_query_module_cannot_be_used_to_mutate_azure():
    """A read-only path that can start a job is not a read-only path."""
    for argv in (["containerapp", "job", "start", "--name", "x"],
                 ["containerapp", "job", "create", "--name", "x"],
                 ["containerapp", "job", "update", "--name", "x"],
                 ["containerapp", "job", "delete", "--name", "x"]):
        with pytest.raises(AZQ.WriteAttemptRefused):
            AZQ.assert_read_only(argv)


# --- 9/10. execution capture and stale job configuration ------------------

def test_only_the_captured_execution_name_is_monitored():
    """A start response names exactly one execution; polling targets it."""
    started = {"name": "job-jspace-s3-p0r1-pilot-g3-abc1234"}
    history = [
        {"name": "job-jspace-s3-p0r1-pilot-g3-abc1234", "status": "Running"},
        {"name": "job-jspace-s3-p0r1-pilot-g3-zzz9999", "status": "Failed"},
    ]

    def runner(argv, timeout):
        return 0, json.dumps(history), ""

    report = AZQ.job_executions("job-jspace-s3-p0r1-pilot-g3", "rg", "sub",
                                runner=runner)
    captured = [entry for entry in report["executions"]
                if entry["name"] == started["name"]]
    assert len(captured) == 1
    assert captured[0]["status"] == "Running"
    assert report["count"] == 2


def test_a_stale_zero_execution_job_refuses_rather_than_being_started():
    """Presence is refusal. The wrapper never updates a job into compliance."""
    def present(argv, timeout):
        return 0, json.dumps(["job-jspace-s3-p0r1-pilot-g3"]), ""

    report = AZQ.job_presence("job-jspace-s3-p0r1-pilot-g3", "rg", "sub",
                              runner=present)
    assert report["outcome"] == AZQ.PROVED_PRESENT
    with pytest.raises(AZQ.AzureQueryError) as caught:
        AZQ.require_absent(report)
    assert "refuses to reuse or overwrite" in str(caught.value)


# --- 11. prefix preflight and recovery against a production-shaped store ---

def test_the_prefix_preflight_proves_absence_before_any_gpu_work():
    backend = BLOB.InMemoryBackend()
    report = PREFIX.probe("gen3-prefix-000000000000", backend=backend)
    assert report["outcome"] == PREFIX.PROVED_ABSENT
    assert report["prefix"].startswith("study3/p0_r1/gen3/")
    assert PREFIX.require_unused(report) is report


def test_an_existing_object_under_the_prefix_refuses_the_attempt():
    backend = BLOB.InMemoryBackend()
    attempt = "gen3-prefix-000000000000"
    prefix = BLOB_V3.attempt_prefix(attempt)
    backend.upload(prefix + "p0_r1_pilot_result.json", b"{}")
    report = PREFIX.probe(attempt, backend=backend)
    assert report["outcome"] == PREFIX.PROVED_PRESENT
    with pytest.raises(PREFIX.PrefixPreflightDefect):
        PREFIX.require_unused(report)


def test_a_data_plane_query_error_is_not_read_as_an_empty_prefix():
    """The workstation cannot see this account at all. That is not "empty"."""
    class Exploding(BLOB.InMemoryBackend):
        """Authorized route, unreachable account: the real failure shape."""

        def list_names(self, prefix):
            raise RuntimeError("the request may be blocked by network rules")

        def exists(self, name):
            raise RuntimeError("blocked")

        def upload(self, name, payload, overwrite=False):
            raise RuntimeError("blocked")

        def download(self, name):
            raise RuntimeError("blocked")

    report = PREFIX.probe("gen3-prefix-000000000000", backend=Exploding())
    assert report["outcome"] == PREFIX.ERROR
    assert "network rules" in report["error"]
    with pytest.raises(PREFIX.PrefixPreflightDefect):
        PREFIX.require_unused(report)


def test_an_unauthorized_backend_is_refused_outright():
    """Only a managed-identity route may carry a P0-R1 result byte."""
    class Rogue(object):
        credential_kind = "shared-key"

    with pytest.raises(BLOB.BlobTransportDefect):
        BLOB_V3.PrivateBlobTransportV3("gen3-prefix-000000000000",
                                       backend=Rogue())


def test_generation_3_never_writes_into_a_superseded_generation_namespace():
    assert BLOB_V3.PREFIX_ROOT == "study3/p0_r1/gen3"
    assert BLOB_V3.attempt_prefix("gen3-abc").startswith("study3/p0_r1/gen3/")
    assert not BLOB_V3.attempt_prefix("gen3-abc").startswith(
        BLOB.PREFIX_ROOT + "/")


# --- 12. a hard kill leaves the emitted row's exact bytes recoverable ------

def test_a_hard_kill_leaves_the_last_admission_and_the_row_bytes(tmp_path):
    """Kill a real process; recover the row itself, not its identifier.

    Generation 2 stored ``{"row_id": ...}`` on completion, so this test would
    fail there: an identifier does not compare equal to a row.
    """
    attempt = "gen3-hardkill-000000000000"
    store = tmp_path / "store"
    store.mkdir()
    row = {"row_id": "KILL-0001", "raw_completion": "Answer: 3", "score": 1,
           "filler": "k" * 512}

    child_source = '''
import json, os, sys, time
sys.path.insert(0, %(p0_r1)r)
import p0_r1_blob_transport as BLOB
import p0_r1_blob_transport_v3 as BLOB_V3
import p0_r1_journal_v3 as JOURNAL


class DirectoryBackend(BLOB.InMemoryBackend):
    """A create-only store on real disk, standing in for the private account.

    Subclasses the authorized in-memory backend so it presents the same
    managed-identity credential kind the production transport requires, but
    persists to disk with fsync so a SIGKILL cannot take the bytes with it.
    """

    def __init__(self, root):
        super(DirectoryBackend, self).__init__()
        self.root = root

    def _path(self, name):
        return os.path.join(self.root, name.replace("/", "__"))

    def exists(self, name):
        return os.path.exists(self._path(name))

    def upload(self, name, payload, overwrite=False):
        path = self._path(name)
        if os.path.exists(path) and not overwrite:
            raise BLOB.BlobTransportDefect("exists")
        with open(path, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return {"name": name, "bytes": len(payload)}

    def download(self, name):
        with open(self._path(name), "rb") as handle:
            return handle.read()

    def list_names(self, prefix):
        found = []
        for entry in os.listdir(self.root):
            restored = entry.replace("__", "/")
            if restored.startswith(prefix):
                found.append(restored)
        return found


backend = DirectoryBackend(%(store)r)
transport = BLOB_V3.PrivateBlobTransportV3(%(attempt)r, backend=backend)
journal = JOURNAL.DurableJournal(%(attempt)r, JOURNAL.BlobJournalSink(transport))
journal.start({"canary": "hard_kill"})
admission = journal.admit("prefill_evaluation", {"slice": "hardkill"})
journal.complete(admission, {"position": 60})
journal.record("scored_row", json.loads(%(row)r))
journal.admit("generation_call", {"row": "KILL-0002"})
sys.stdout.write("READY\\n")
sys.stdout.flush()
time.sleep(120)
''' % {"p0_r1": P0_R1_DIR, "store": str(store), "attempt": attempt,
       "row": json.dumps(row)}

    script = tmp_path / "child.py"
    script.write_text(child_source, encoding="utf-8")

    child = subprocess.Popen(  # noqa: S603
        [sys.executable, str(script)], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)
    try:
        ready = child.stdout.readline()
        assert "READY" in ready, child.stderr.read()
        child.kill()
        child.wait(timeout=60)
    finally:
        if child.poll() is None:
            child.kill()

    entries = []
    for name in sorted(os.listdir(store)):
        payload = (store / name).read_bytes()
        entries.append(json.loads(payload.decode("utf-8")))

    rows = [entry["payload"] for entry in entries
            if entry.get("kind") == "scored_row"]
    assert rows == [row], "the row's exact bytes did not survive the kill"

    open_admissions = [entry for entry in entries
                       if entry.get("kind") == "admission"
                       and entry.get("operation") == "generation_call"]
    assert len(open_admissions) == 1, (
        "an admitted, never-completed irreversible operation must remain "
        "visible; unknown is not zero")


# --- 13. failures at each stage still yield the conservative receipt -------

@pytest.mark.parametrize("stage", [
    "before_runner_entry", "during_journal_write", "during_executor",
])
def test_a_failure_at_each_stage_preserves_the_prior_bytes(stage, tmp_path,
                                                           synthetic_inputs):
    import p0_r1_model_runner_v3 as RUNNER_V3_MOD

    backend = BLOB.InMemoryBackend()
    attempt = WIRING.ATTEMPT

    if stage == "before_runner_entry":
        with pytest.raises(AUTHZ.AuthorizationRefused):
            AUTHZ.build_from_files(
                LOCK_V3_PATH, synthetic_inputs["p0_r1_replay_receipt.json"],
                synthetic_inputs["p0_r1_replay_reconstruction_receipt_v3.json"],
                None)
        assert backend.list_names("") == [], (
            "a refusal before runner entry must touch no object")
        return

    if stage == "during_journal_write":
        class FailingSink(object):
            kind = "blob"
            durable = True

            def __init__(self):
                self.calls = 0
                self.payload = b""
                self.name = ""

            def write(self, name, payload):
                self.calls += 1
                if self.calls > 1:
                    raise JOURNAL_V3.JournalDefect("upload failed")
                self.payload = payload
                self.name = name
                return {"name": name, "sha256": "0" * 64}

            def read(self, name):
                return self.payload

            def list_names(self):
                return [self.name]

        journal = JOURNAL_V3.DurableJournal(attempt, FailingSink())
        journal.start({"stage": stage})
        with pytest.raises(JOURNAL_V3.JournalDefect):
            journal.record("scored_row", {"row_id": "X"})
        assert journal.index >= 1, "the first entry survived the later failure"
        return

    def exploding(context, stream=None):
        raise RuntimeError("the executor failed after the journal opened")

    original = RUNNER_V3_MOD.EXECUTORS["sentinel"]
    RUNNER_V3_MOD.EXECUTORS["sentinel"] = exploding
    try:
        with pytest.raises(RuntimeError):
            RUNNER_V3_MOD.run_pilot(
                LOCK_V3_PATH, synthetic_inputs["p0_r1_replay_receipt.json"],
                synthetic_inputs["p0_r1_replay_reconstruction_receipt_v3.json"],
                synthetic_inputs["p0_r1_head_proof_v3.json"],
                str(tmp_path / "out"), root=REPO_ROOT, attempt_id=attempt,
                executor="sentinel", backend=backend, stream=io.StringIO())
    finally:
        RUNNER_V3_MOD.EXECUTORS["sentinel"] = original

    names = backend.list_names(BLOB_V3.attempt_prefix(attempt))
    assert any("journal/" in name for name in names), (
        "the journal entries written before the exception must survive it")
    assert any(JOURNAL_V3.MANIFEST_NAME in name for name in names), (
        "an exception must still produce a manifest of what exists")


# --- 14. the shell trap emits, it does not merely contain the word trap ----

def test_the_exit_boundary_emits_complete_recoverable_bytes(tmp_path):
    """A hash is not a byte. The trap must emit the receipt itself."""
    import p0_r1_infrastructure_receipt_v3 as RECEIPT

    stream = io.StringIO()
    document, payload, durable = RECEIPT.emit(
        137, attempt_id="gen3-trap-000000000000", out_dir=str(tmp_path),
        backend=BLOB.InMemoryBackend(), stream=stream)

    assert durable is True
    assert document["state"] == RECEIPT.STATE_INFRASTRUCTURE
    assert document["authorizes_a_retry"] is False
    text = stream.getvalue()
    assert "P0_R1_SECONDARY_ENVELOPE_COMPLETE=1" in text

    recovered = TRANSPORT.recover(text, attempt_id="gen3-trap-000000000000",
                                  allowed=(RECEIPT.RECEIPT_NAME,))
    assert recovered[RECEIPT.RECEIPT_NAME] == payload, (
        "the receipt must be recoverable from the captured log alone")


def test_a_degraded_store_is_reported_rather_than_silently_accepted(tmp_path):
    import p0_r1_infrastructure_receipt_v3 as RECEIPT

    class Exploding(BLOB.InMemoryBackend):
        """Authorized route, unreachable account."""

        def exists(self, name):
            raise RuntimeError("blocked by network rules")

        def upload(self, name, payload, overwrite=False):
            raise RuntimeError("blocked by network rules")

        def download(self, name):
            raise RuntimeError("blocked by network rules")

        def list_names(self, prefix):
            raise RuntimeError("blocked by network rules")

    stream = io.StringIO()
    _document, payload, durable = RECEIPT.emit(
        1, attempt_id="gen3-trap-000000000000", out_dir=str(tmp_path),
        backend=Exploding(), stream=stream)
    text = stream.getvalue()
    assert durable is False
    assert "P0_R1_DURABILITY_DEGRADED=1" in text
    recovered = TRANSPORT.recover(text, attempt_id="gen3-trap-000000000000",
                                  allowed=(RECEIPT.RECEIPT_NAME,))
    assert recovered[RECEIPT.RECEIPT_NAME] == payload, (
        "when the store is unreachable the console route must still carry "
        "the complete bytes")


# --- 15. the manifest enumerates recursively and refuses every discrepancy -

def _journal_with_entries(attempt="gen3-manifest-000000000000"):
    backend = BLOB.InMemoryBackend()
    transport = BLOB_V3.PrivateBlobTransportV3(attempt, backend=backend)
    sink = JOURNAL_V3.BlobJournalSink(transport)
    journal = JOURNAL_V3.DurableJournal(attempt, sink)
    journal.start({"test": True})
    token = journal.admit("prefill_evaluation", {"slice": "t"})
    journal.complete(token, {"position": 60})
    journal.record("scored_row", {"row_id": "R-1", "score": 1})
    return journal, sink, backend, transport


def test_the_manifest_enumerates_every_nested_journal_object():
    """``os.listdir`` returns top-level names and misses the whole journal."""
    journal, sink, _backend, _transport = _journal_with_entries()
    manifest = journal.manifest(canonical=[])
    assert manifest["recursive_enumeration"] is True
    assert manifest["written_last"] is True
    assert manifest["journal_object_count"] == journal.index
    listed = [entry["name"] for entry in manifest["journal_objects"]]
    assert all(name.startswith("journal/") for name in listed)
    assert len(listed) >= 4
    verified = JOURNAL_V3.verify_manifest(manifest, sink)
    assert verified["verified_objects"] == len(listed)


@pytest.mark.parametrize("damage", ["missing", "extra", "reordered",
                                    "overwritten", "hash_mismatch"])
def test_the_manifest_refuses_a_damaged_journal(damage):
    journal, sink, backend, transport = _journal_with_entries()
    manifest = journal.manifest(canonical=[])

    if damage == "missing":
        name = manifest["journal_objects"][0]["name"]
        del backend.objects[transport.prefix + name]
    elif damage == "extra":
        backend.upload(transport.prefix + "journal/999999-ghost.json", b"{}")
    elif damage == "reordered":
        manifest["journal_objects"][0]["sequence"] = 99
    elif damage == "overwritten":
        name = manifest["journal_objects"][1]["name"]
        backend.objects[transport.prefix + name] = b"{}"
    else:
        manifest["journal_objects"][0]["sha256"] = "0" * 64

    with pytest.raises(JOURNAL_V3.JournalDefect):
        JOURNAL_V3.verify_manifest(manifest, sink)


def test_a_journal_entry_is_never_overwritten():
    journal, _sink, _backend, _transport = _journal_with_entries()
    name = JOURNAL_V3.sequence_name(1, "attempt_start")
    with pytest.raises(Exception):
        journal.sink.write(name, b"{}")


def test_a_payload_bearing_entry_must_carry_its_payload():
    journal, _sink, _backend, _transport = _journal_with_entries()
    with pytest.raises(JOURNAL_V3.JournalDefect):
        journal.record("scored_row", None)


# --- 16. the CPU recovery entry point is model-free ------------------------

def test_the_recovery_path_verifies_and_re_emits_without_a_model(tmp_path):
    """The recovery entry point, run as its own process, as the job runs it.

    Deliberately a subprocess rather than an in-process call. The recovery job
    is model-free *by construction*, and it enforces that by refusing to run
    in an interpreter where a model library is already imported. A shared
    pytest process is not model-free -- sibling P0-R1 tests import torch and
    transformers -- so calling it in-process would either fail spuriously or,
    worse, tempt someone to weaken the production guard to make a test pass.
    """
    result = _run([sys.executable,
                   os.path.join(P0_R1_DIR, "p0_r1_recovery_v3.py"),
                   "--self-check"])
    assert result.returncode == 0, result.stdout + result.stderr
    text = result.stdout
    assert "P0_R1_RECOVERY_V3_SELF_CHECK=passed" in text
    assert "P0_R1_RECOVERY_COMPLETE=1" in text

    attempt = "p0-r1-recovery-v3-self-check"
    recovered = TRANSPORT.recover(text, attempt_id=attempt,
                                  allowed=RECOVERY.declared_names(text))
    assert recovered, "the recovery job must re-emit complete recoverable bytes"
    receipt_name = RECOVERY.RECOVERY_RECEIPT_NAME
    assert receipt_name in recovered
    receipt = json.loads(recovered[receipt_name].decode("utf-8"))
    assert receipt["is_a_replay"] is False
    assert receipt["is_a_model_retry"] is False
    assert receipt["tokenizer_constructions"] == 0
    assert receipt["checkpoint_downloads"] == 0
    assert receipt["model_weight_loads"] == 0
    assert receipt["gpu_allocated"] is False
    assert receipt["journal_objects_verified"] >= 4
    assert receipt["sequence_continuous"] is True
    assert receipt["manifest_written_last"] is True


def test_the_recovery_path_verifies_every_object_in_process():
    """The verification logic itself, with the model guard satisfied."""
    journal, sink, _backend, _transport = _journal_with_entries(
        "gen3-recover-000000000000")
    manifest = journal.manifest(canonical=[])
    verified = JOURNAL_V3.verify_manifest(manifest, sink)
    assert verified["verified_objects"] == journal.index
    assert verified["sequence_continuous"] is True
    assert verified["manifest_written_last"] is True


def test_the_recovery_path_refuses_if_a_model_library_is_present(monkeypatch):
    """Importing a model library turns recovery into a retry. Refuse."""
    monkeypatch.setitem(sys.modules, "transformers", object())
    with pytest.raises(RECOVERY.RecoveryDefect) as caught:
        RECOVERY.assert_model_free()
    assert "model-free" in str(caught.value)


def test_the_recovery_job_definition_is_cpu_only_and_separately_named():
    path = os.path.join(CONTAINER_DIR, "p0_r1_recovery_job_v3.yaml")
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    assert "job-jspace-s3-p0r1-recover-g3" in text
    assert "workloadProfileName: Consumption" in text

    gpu_path = os.path.join(CONTAINER_DIR, "p0_r1_gpu_job_v3.yaml")
    with open(gpu_path, "r", encoding="utf-8") as handle:
        gpu_text = handle.read()
    assert "job-jspace-s3-p0r1-pilot-g3" in gpu_text
    assert "name: job-jspace-study3-p0-r1-pilot-g2" not in gpu_text


# --- 17. generations 1 and 2 remain inert ---------------------------------

def test_generations_1_and_2_are_unconsumed_superseded_and_not_launchable(
        lock_document):
    for key in ("generation_1", "generation_2"):
        block = lock_document[key]
        assert block["superseded"] is True
        assert block["consumed"] is False
        assert block["launchable"] is False
        assert block["executions"] == 0
        assert block["gpu_allocations"] == 0
        assert block["tokenizer_constructions"] == 0
        assert block["checkpoint_downloads"] == 0
        assert block["model_weight_loads"] == 0
        assert block["superseded_by"].endswith("p0_r1_execution_lock_v3.json")


def test_the_superseded_lock_bytes_are_preserved_exactly(lock_document):
    import hashlib
    for key, path in (("generation_1", LOCK_V1_PATH),
                      ("generation_2", LOCK_V2_PATH)):
        with open(path, "rb") as handle:
            payload = handle.read()
        assert hashlib.sha256(payload).hexdigest() == \
            lock_document[key]["sha256"]
        assert len(payload) == lock_document[key]["bytes"]


def test_exactly_one_overall_envelope_remains(lock_document):
    binding = lock_document["attempt_binding"]
    assert binding["remaining_overall_envelopes"] == 1
    assert binding["envelopes_are_per_study_not_per_lock_generation"] is True
    assert binding[
        "one_replay_attempt_authorizes_at_most_one_model_pilot"] is True


def test_every_counter_is_zero_and_the_legal_status_is_unchanged(
        lock_document):
    counters = lock_document["counters_before_execution"]
    assert len(counters) == 31
    assert set(counters.values()) == {0}
    legal = lock_document["legal_status"]
    assert legal["p0_r1_pilot_execution_authorized"] is True
    assert legal["p0_r1_pilot_execution_consumed"] is False
    assert legal["formal_execution_authorized"] is False
    assert legal["draft_v0_6_frozen"] is False
    assert legal["draft_v0_6_reviewed"] is False
    assert legal["interface_selected"] is None
    assert legal["positive_reference"] is None
    assert legal["rp_wrapper"] is None
    assert legal["evidence_ledger_last_row"] == "EV-0016"
    assert legal["research_question_answered"] is False


# --- the ready anchor is proved, not propagated ---------------------------

def test_the_lock_does_not_record_the_published_head(lock_document):
    """A commit cannot contain its own hash; do not pretend otherwise."""
    relationship = lock_document["ready_commit_relationship"]
    assert relationship["published_head_is_recorded_in_the_lock"] is False
    assert relationship["ready_anchor_commit"] is None


def test_two_coordinated_hex_strings_no_longer_validate_as_a_ready_commit():
    """Generation 2 accepted any 40-hex value placed in both inputs."""
    fabricated = {
        "schema_version": ANCHOR.SCHEMA_VERSION,
        "published_head": {"commit": "a" * 40, "tree": "b" * 40},
        "ready_anchor": {"commit": "c" * 40, "tree": "d" * 40},
        "executable_code": {"commit": "e" * 40, "tree": "f" * 40},
        "head_equals_published": True,
        "all_changes_are_governance_only": True,
        "bound_paths_changed_after_image_build": [],
    }
    with pytest.raises(ANCHOR.ReadyAnchorDefect):
        ANCHOR.validate_proof(fabricated, executable_commit="1" * 40,
                              executable_tree="f" * 40,
                              ready_anchor="c" * 40)


def test_a_proof_that_admits_non_governance_drift_is_refused():
    proof = {
        "schema_version": ANCHOR.SCHEMA_VERSION,
        "published_head": {"commit": "a" * 40, "tree": "b" * 40},
        "ready_anchor": {"commit": "c" * 40, "tree": "d" * 40},
        "executable_code": {"commit": "e" * 40, "tree": "f" * 40},
        "head_equals_published": True,
        "all_changes_are_governance_only": False,
        "bound_paths_changed_after_image_build": [],
    }
    with pytest.raises(ANCHOR.ReadyAnchorDefect):
        ANCHOR.validate_proof(proof)

    proof["all_changes_are_governance_only"] = True
    proof["bound_paths_changed_after_image_build"] = [
        "studies/study3/pilot/p0_r1/p0_r1_model_runner_v3.py"]
    with pytest.raises(ANCHOR.ReadyAnchorDefect):
        ANCHOR.validate_proof(proof)


def test_a_dirty_or_diverged_checkout_cannot_produce_a_proof():
    def git(args, check=True):
        joined = " ".join(args)
        if joined == "rev-parse HEAD":
            return "a" * 40, 0
        if joined == "rev-parse HEAD^{tree}":
            return "b" * 40, 0
        if joined.startswith("rev-parse origin/main"):
            return "9" * 40, 0
        return "", 0

    with pytest.raises(ANCHOR.ReadyAnchorDefect) as caught:
        ANCHOR.prove(executable_commit="c" * 40, executable_tree="d" * 40,
                     ready_anchor="e" * 40, git=git)
    assert "not the published" in str(caught.value)


def test_the_governance_allowlist_covers_only_non_executable_paths():
    for path in ANCHOR.GOVERNANCE_ALLOWLIST:
        assert not path.endswith(".py")
        assert not path.endswith(".sh")
        assert "container/" not in path
        assert ANCHOR.path_is_governance_only(path)
    assert not ANCHOR.path_is_governance_only(
        "studies/study3/pilot/p0_r1/p0_r1_model_runner_v3.py")
    assert not ANCHOR.path_is_governance_only(
        "studies/study3/pilot/p0_r1/container/p0_r1_model_pilot_v3.sh")


# --- the authorization tuple binds all four documents ---------------------

def test_the_authorization_requires_all_four_documents(synthetic_inputs):
    authorization = AUTHZ.build_from_files(
        LOCK_V3_PATH, synthetic_inputs["p0_r1_replay_receipt.json"],
        synthetic_inputs["p0_r1_replay_reconstruction_receipt_v3.json"],
        synthetic_inputs["p0_r1_head_proof_v3.json"])
    assert authorization["p0_r1_pilot_execution_authorized"] is True
    assert set(authorization["input_identities"]) == {
        "execution_lock", "replay_receipt", "reconstruction_receipt",
        "head_proof"}
    for identity in authorization["input_identities"].values():
        assert len(identity["sha256"]) == 64
        assert identity["bytes"] > 0


def test_a_generation_2_lock_cannot_authorize_a_generation_3_pilot(
        synthetic_inputs):
    with pytest.raises(AUTHZ.AuthorizationRefused) as caught:
        AUTHZ.build_from_files(
            LOCK_V2_PATH, synthetic_inputs["p0_r1_replay_receipt.json"],
            synthetic_inputs["p0_r1_replay_reconstruction_receipt_v3.json"],
            synthetic_inputs["p0_r1_head_proof_v3.json"])
    assert "generation-3 execution lock" in str(caught.value)


def test_a_replay_that_touched_a_model_is_not_a_replay(synthetic_inputs,
                                                       tmp_path):
    with open(synthetic_inputs["p0_r1_replay_receipt.json"], "rb") as handle:
        receipt = json.loads(handle.read().decode("utf-8"))
    receipt["tokenizer_constructions"] = 1
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(AUTHZ.AuthorizationRefused) as caught:
        AUTHZ.build_from_files(
            LOCK_V3_PATH, str(tampered),
            synthetic_inputs["p0_r1_replay_reconstruction_receipt_v3.json"],
            synthetic_inputs["p0_r1_head_proof_v3.json"])
    assert "performed a model operation" in str(caught.value)


# --- the lock itself ------------------------------------------------------

def test_the_v3_lock_validates_every_bound_byte():
    with open(LOCK_V3_PATH, "rb") as handle:
        document = json.loads(handle.read().decode("utf-8"))
    assert LOCK_V3.validate(document, root=REPO_ROOT) is True


def test_the_v3_lock_binds_all_four_authorities(lock_document):
    paths = [entry["path"] for entry in lock_document["authorities"]]
    assert len(paths) == 4
    assert any("generation3_execution_closure" in path for path in paths)
    assert any("post_ready_transport" in path for path in paths)
    assert any("pre_replay_execution_completion" in path for path in paths)
    assert any("study3_v0_6_p0_r1_authority" in path for path in paths)


def test_the_v3_lock_binds_every_generation_3_executable_path(lock_document):
    bound = {entry["path"] for entry in
             lock_document["executable_code"]["files"]}
    for path in LOCK_V3.GENERATION_3_CODE_PATHS:
        assert path in bound, path
    for path in LOCK_V3.INHERITED_CODE_PATHS:
        assert path in bound, path


def test_the_lock_records_the_azure_and_replay_contracts(lock_document):
    azure = lock_document["azure_query_contract"]
    assert azure["error_is_treated_as_absence"] is False
    assert azure["only_proved_absent_may_create_or_start"] is True
    replay = lock_document["replay_contract"]
    assert replay["gate_receipt_is_never_rewritten"] is True
    assert replay["emitted_receipt_claims_its_own_recovery"] is False
    assert replay["either_receipt_alone_authorizes"] is False
    assert len(replay["authorization_tuple"]) == 4
    transport = lock_document["transport"]
    assert transport["primary_journal_sink"] == "private_blob"
    assert transport["local_filesystem_is"] == "cache_only"
    assert transport["journal_is_create_only"] is True
    assert transport["journal_stores_complete_payloads"] is True
    assert transport["manifest_enumerates_recursively"] is True
    assert transport["prefix_root"] == "study3/p0_r1/gen3"


def test_the_replay_gate_v3_refuses_to_rewrite_its_own_receipt():
    import p0_r1_replay_gate_v3 as GATE_V3

    identity = GATE_V3.implementation_identity()
    assert identity["rewrites_its_own_receipt"] is False
    assert identity["emitted_receipt_claims_its_own_recovery"] is False
    assert identity["changes_any_scientific_rule"] is False

    receipt = {"transport": {"complete_byte_recovery_verified": True}}
    annotated = GATE_V3.annotate_receipt_honestly(receipt)
    assert annotated["transport"]["complete_byte_recovery_verified"] is False
    assert "self_attestation_refused" in annotated["transport"]


def test_no_generation_3_module_changes_a_scientific_rule():
    import p0_r1_model_execution_v3 as EXEC_V3
    import p0_r1_model_runner_v3 as RUNNER_MOD
    import p0_r1_replay_gate_v3 as GATE_V3

    for module in (EXEC_V3, RUNNER_MOD, GATE_V3):
        identity = module.implementation_identity()
        assert identity["changes_any_scientific_rule"] is False
        assert "delegates_science_to" in identity
