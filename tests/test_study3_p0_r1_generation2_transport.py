"""Study 3 P0-R1 generation-2 transport and exception-safety tests.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
section 10, over the two prior P0-R1 authorities.

Every test here is production-bound. Each one either drives a real generation-2
entry point or mutates the live input that production code reads, and every one
fails at the required baseline `71f4ab903295d1320881b654bda2d49cf1808794`, where
none of the generation-2 modules existed at all.

The defects these nodes close were demonstrated, not hypothesised. The
generation-1 image could not have invoked its own job command; a truncated log
was the only result transport; a crash could make a possibly-started
irreversible operation look like a zero-operation non-attempt; and the launcher
had no mandatory-input discipline.

No test in this module constructs a real tokenizer, downloads or loads a
checkpoint, exposes a GPU, performs a model operation, runs the live replay gate
against the published lock, or consumes the one-shot envelope. Synthetic
transports, Azure CLI shims, forced failures and fixture layouts are used
throughout, and each mutation reaches production code.
"""

import base64
import hashlib
import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P0_R1_DIR = os.path.join(REPO_ROOT, "studies", "study3", "pilot", "p0_r1")
CONTAINER_DIR = os.path.join(P0_R1_DIR, "container")
EXECUTION_DIR = os.path.join(P0_R1_DIR, "execution")

if P0_R1_DIR not in sys.path:
    sys.path.insert(0, P0_R1_DIR)

import p0_r1_blob_transport as BLOB  # noqa: E402
import p0_r1_counters as COUNTERS  # noqa: E402
import p0_r1_execution_lock as LOCK1  # noqa: E402
import p0_r1_execution_lock_v2 as LOCK  # noqa: E402
import p0_r1_journal as JOURNAL  # noqa: E402
import p0_r1_model_runner_v2 as RUNNER  # noqa: E402
import p0_r1_replay_gate_v2 as GATE  # noqa: E402
import p0_r1_runtime_binding as RUNTIME  # noqa: E402
import p0_r1_transport as TRANSPORT  # noqa: E402

DIGEST = "sha256:" + "ab" * 32
OTHER_DIGEST = "sha256:" + "cd" * 32
COMMIT = "1" * 40
TREE = "2" * 40
OTHER_COMMIT = "9" * 40
ATTEMPT = "gen2-aad14c45e968-20260101T000000Z"
OTHER_ATTEMPT = "gen2-aad14c45e968-20260101T111111Z"


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def _read(path):
    with open(path, "rb") as handle:
        return handle.read()


def _text(path):
    return _read(path).decode("utf-8")


# ---------------------------------------------------------------------------
# Fixtures: a standalone image layout, a valid lock, a valid receipt
# ---------------------------------------------------------------------------

def _fixture_layout(tmp_path, omit=(), non_executable=()):
    """Build a fixture standalone image layout on disk.

    Real files, real permissions, driven through the real
    :func:`verify_standalone_layout`. Nothing here is a string-presence check.
    """
    src = tmp_path / "opt" / "jspace" / "src"
    for relative in RUNTIME.REQUIRED_SOURCE_PATHS:
        if relative in omit:
            continue
        target = src / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x")
    bin_dir = tmp_path / "usr" / "local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    entrypoints = []
    for absolute in RUNTIME.STANDALONE_ENTRYPOINTS:
        name = absolute.rsplit("/", 1)[-1]
        path = bin_dir / name
        if name in omit:
            entrypoints.append(str(path))
            continue
        path.write_bytes(b"#!/usr/bin/env bash\n")
        path.chmod(0o755 if name not in non_executable else 0o644)
        entrypoints.append(str(path))
    return str(src), entrypoints


def _executable_probe(non_executable=()):
    def is_executable(path):
        return os.path.basename(path) not in non_executable \
            and os.path.exists(path)
    return is_executable


def _canary_receipts():
    """Model-free canary receipts of the shape the real lock builder requires."""
    return {name: {"passed": True, "canary": name,
                   "tokenizer_constructions": 0, "tokenizer_encodes": 0,
                   "checkpoint_downloads": 0, "model_operations_performed": 0,
                   "gpu_workload_allocated": False}
            for name in LOCK.CANARY_NAMES}


def _valid_lock():
    """A real generation-2 lock, built by the production builder from live bytes.

    Building rather than hand-writing matters: the fixture then re-hashes every
    bound executable path, so a test that accepts this lock is asserting against
    the code that actually exists, not against a convenient stub.
    """
    return LOCK.build_lock(
        executable_code_commit=COMMIT,
        executable_code_tree=TREE,
        image_digest=DIGEST,
        ready_commit_parent=COMMIT,
        canary_receipts=_canary_receipts())


def _valid_receipt(lock=None, attempt=ATTEMPT, passed=True, digest=None,
                   commit=None, lock_bytes=None):
    """A replay receipt that agrees with ``lock`` on every bound identity."""
    lock = lock if lock is not None else _valid_lock()
    if lock_bytes is None:
        lock_bytes = json.dumps(lock, indent=1, sort_keys=True,
                                ensure_ascii=True).encode("utf-8")
    return {
        "schema_version": RUNTIME.REPLAY_RECEIPT_SCHEMAS[0],
        "attempt_id": attempt,
        "state": RUNTIME.REPLAY_PASS_STATE if passed
                 else "STUDY3_P0_R1_REPLAY_GATE_DEFECT",
        "passed": passed,
        "authorizes_model_pilot": passed,
        "image_digest": digest or lock["image"]["digest"],
        "executable_code_commit":
            commit or lock["executable_code"]["commit"],
        "executable_code_tree": lock["executable_code"]["tree"],
        "ready_commit": commit or lock["executable_code"]["commit"],
        "authorities": lock["authorities"],
        "corpus_and_p0_t": lock["corpus_and_p0_t"],
        "execution_lock": {"bytes": len(lock_bytes),
                           "sha256": _sha256(lock_bytes)},
        "tokenizer_encodes": 0,
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "model_operations_performed": 0,
        "gpu_allocated": False,
        "transport": {"complete_byte_recovery_verified": True},
    }


def _synthetic_gate_artifacts(out_dir):
    """Deterministic, realistically shaped replay bytes."""
    os.makedirs(out_dir, exist_ok=True)
    result = {
        "schema_version": "study3-p0-r1-replay-gate-result-v2",
        "attempt_id": ATTEMPT,
        "rows": [{"row": index, "cell": "s%d" % (index % 4)}
                 for index in range(120)],
    }
    receipt = _valid_receipt()
    counters = {"tokenizer_encodes": 0, "rows_examined": 120}
    payloads = {
        "p0_r1_replay_result.json": json.dumps(result, indent=1,
                                               sort_keys=True).encode("utf-8"),
        "p0_r1_replay_receipt.json": json.dumps(receipt, indent=1,
                                                sort_keys=True).encode("utf-8"),
        "p0_r1_replay_counters.json": json.dumps(counters, indent=1,
                                                 sort_keys=True).encode("utf-8"),
        "P0_R1_REPLAY_DISPOSITION.md":
            ("# P0-R1 replay disposition\n\n"
             + "A synthetic fixture line.\n" * 40).encode("utf-8"),
    }
    for name, payload in payloads.items():
        with open(os.path.join(out_dir, name), "wb") as handle:
            handle.write(payload)
    return payloads


# ---------------------------------------------------------------------------
# 10.1  The standalone image contains and can invoke the entry point
# ---------------------------------------------------------------------------

def test_every_bound_generation_2_byte_is_lf_only_and_registered_as_such():
    """A CRLF entry point cannot be executed by bash on the Linux agent.

    It also cannot compare equal to its own in-repo checkout, which would break
    the byte-exact executable-code binding in the lock. The repository already
    registers this hazard for Stage T; generation 2 is registered the same way.
    """
    for relative in LOCK.GENERATION_2_CODE_PATHS:
        path = os.path.join(REPO_ROOT, *relative.split("/"))
        raw = open(path, "rb").read()
        assert b"\r" not in raw, relative
        assert not raw.startswith(b"\xef\xbb\xbf"), relative
    attributes = _text(os.path.join(REPO_ROOT, ".gitattributes"))
    for pattern in ("studies/study3/pilot/p0_r1/*.py text eol=lf",
                    "studies/study3/pilot/p0_r1/execution/*.py text eol=lf",
                    "studies/study3/pilot/p0_r1/container/* text eol=lf"):
        assert pattern in attributes, pattern
    # Every container entry point is a real shebanged script, not a fragment.
    for name in os.listdir(CONTAINER_DIR):
        if name.endswith(".sh"):
            raw = open(os.path.join(CONTAINER_DIR, name), "rb").read()
            assert raw.startswith(b"#!/"), name
            assert b"set -euo pipefail" in raw, name


def test_the_standalone_image_can_invoke_its_own_entry_point_with_no_mount(
        tmp_path):
    src, entrypoints = _fixture_layout(tmp_path)
    report = RUNTIME.verify_standalone_layout(
        src=src, entrypoints=entrypoints,
        is_executable=_executable_probe())
    assert report["standalone_source_root"] == src
    assert report["depends_on_the_acr_workspace_mount"] is False
    assert report["required_source_paths"] == len(RUNTIME.REQUIRED_SOURCE_PATHS)
    # The registered root is not the mount generation 1 depended on.
    assert RUNTIME.STANDALONE_SRC == "/opt/jspace/src"
    assert not RUNTIME.STANDALONE_SRC.startswith("/workspace")


def test_a_layout_missing_the_entry_point_refuses(tmp_path):
    name = RUNTIME.MODEL_PILOT_ENTRYPOINT.rsplit("/", 1)[-1]
    src, entrypoints = _fixture_layout(tmp_path, omit=(name,))
    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.verify_standalone_layout(
            src=src, entrypoints=entrypoints,
            is_executable=_executable_probe())
    assert "does not exist inside the image" in str(excinfo.value)


def test_a_non_executable_entry_point_refuses(tmp_path):
    name = RUNTIME.MODEL_PILOT_ENTRYPOINT.rsplit("/", 1)[-1]
    src, entrypoints = _fixture_layout(tmp_path, non_executable=(name,))
    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.verify_standalone_layout(
            src=src, entrypoints=entrypoints,
            is_executable=_executable_probe(non_executable=(name,)))
    assert "is not executable inside the image" in str(excinfo.value)


def test_a_layout_missing_a_bound_source_file_refuses(tmp_path):
    victim = RUNTIME.REQUIRED_SOURCE_PATHS[0]
    src, entrypoints = _fixture_layout(tmp_path, omit=(victim,))
    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.verify_standalone_layout(
            src=src, entrypoints=entrypoints,
            is_executable=_executable_probe())
    assert victim in str(excinfo.value)


# ---------------------------------------------------------------------------
# 10.2  The actual GPU job command path exists inside the built image
# ---------------------------------------------------------------------------

def _uncommented(text, marker="#"):
    """Only the operative lines: a comment explaining a defect is not the defect."""
    return "\n".join(line for line in text.splitlines()
                     if not line.strip().startswith(marker))


def test_the_gpu_job_command_is_a_path_the_image_installs():
    job = _text(os.path.join(CONTAINER_DIR, "p0_r1_gpu_job_v2.yaml"))
    dockerfile = _text(os.path.join(CONTAINER_DIR,
                                    "Dockerfile.study3-p0-r1-v2"))
    command = RUNTIME.MODEL_PILOT_ENTRYPOINT
    assert '"%s"' % command in job
    # The command is not merely named: the build installs exactly that path.
    assert "install -m 0755" in dockerfile
    assert command in dockerfile
    # Generation 1's command was a mount path that the image never contained.
    assert "/workspace/p0_r1_model_pilot.sh" not in _uncommented(job)


def test_every_declared_entry_point_is_installed_by_the_build():
    dockerfile = _text(os.path.join(CONTAINER_DIR,
                                    "Dockerfile.study3-p0-r1-v2"))
    for entrypoint in RUNTIME.STANDALONE_ENTRYPOINTS:
        source = entrypoint.rsplit("/", 1)[-1]
        assert entrypoint in dockerfile
        assert os.path.exists(os.path.join(CONTAINER_DIR, source)), source


def test_the_image_manifest_emitter_binds_the_standalone_root():
    emitter = _text(os.path.join(CONTAINER_DIR, "p0_r1_image_manifest_v2.py"))
    assert "/opt/jspace/src" in emitter
    assert "verify_standalone_layout" in emitter
    dockerfile = _text(os.path.join(CONTAINER_DIR,
                                    "Dockerfile.study3-p0-r1-v2"))
    assert "p0_r1_image_manifest_v2.py" in dockerfile


# ---------------------------------------------------------------------------
# 10.3  The lock is absent from the image and injected at runtime
# ---------------------------------------------------------------------------

def test_the_final_lock_is_deliberately_absent_from_the_image(tmp_path):
    dockerfile = _text(os.path.join(CONTAINER_DIR,
                                    "Dockerfile.study3-p0-r1-v2"))
    assert "rm -f /opt/jspace/src/studies/study3/pilot/p0_r1/" \
           "p0_r1_execution_lock_v2.json" in dockerfile
    assert "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json" \
        in RUNTIME.FORBIDDEN_IMAGE_CONTENT
    assert "studies/study3/pilot/p0_r1/results" \
        in RUNTIME.FORBIDDEN_IMAGE_CONTENT

    src, entrypoints = _fixture_layout(tmp_path)
    planted = os.path.join(src, "studies", "study3", "pilot", "p0_r1",
                           "p0_r1_execution_lock_v2.json")
    os.makedirs(os.path.dirname(planted), exist_ok=True)
    with open(planted, "wb") as handle:
        handle.write(b"{}")
    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.verify_standalone_layout(
            src=src, entrypoints=entrypoints,
            is_executable=_executable_probe())
    assert "no outcome-conditioned byte" in str(excinfo.value)


def test_injected_lock_and_receipt_bytes_round_trip_exactly(tmp_path):
    lock_bytes = json.dumps(_valid_lock(), indent=1,
                            sort_keys=True).encode("utf-8")
    receipt_bytes = json.dumps(_valid_receipt(), indent=1,
                               sort_keys=True).encode("utf-8")
    environ = RUNTIME.build_injection(lock_bytes, receipt_bytes)
    out_dir = str(tmp_path / "injected")
    written = RUNTIME.reconstruct_injection(environ=environ, out_dir=out_dir)

    assert _read(os.path.join(out_dir, RUNTIME.INJECTED_LOCK_NAME)) \
        == lock_bytes
    assert _read(os.path.join(out_dir, RUNTIME.INJECTED_RECEIPT_NAME)) \
        == receipt_bytes
    assert written[RUNTIME.INJECTED_LOCK_NAME]["sha256"] == _sha256(lock_bytes)
    assert written[RUNTIME.INJECTED_LOCK_NAME]["bytes"] == len(lock_bytes)


def _flip_one_encoded_byte(blob):
    """Change one payload byte without changing the declared byte count.

    Truncation is caught by the length check, so a length-preserving mutation is
    what actually exercises the digest check.
    """
    head, _, encoded = blob.rpartition("|")
    raw = bytearray(base64.b64decode(encoded))
    raw[len(raw) // 2] ^= 0x01
    return head + "|" + base64.b64encode(bytes(raw)).decode("ascii")


@pytest.mark.parametrize("mutate,reason", [
    (lambda blob: blob.replace("study3-p0-r1-runtime-injection-v2",
                               "study3-p0-r1-runtime-injection-v1"),
     "is not the registered"),
    (_flip_one_encoded_byte, "sha256"),
    (lambda blob: blob[:-4], "not the declared"),
    (lambda blob: blob.split("|")[0] + "|999|" + "|".join(blob.split("|")[2:]),
     "not the declared"),
    (lambda blob: "|".join(blob.split("|")[:-1]), "malformed"),
])
def test_a_mutated_injection_payload_refuses(mutate, reason):
    payload = json.dumps(_valid_lock()).encode("utf-8")
    encoded = RUNTIME.encode_injection(payload)
    assert RUNTIME.decode_injection(encoded) == payload
    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.decode_injection(mutate(encoded))
    assert reason in str(excinfo.value)


def test_an_oversize_injection_payload_demands_the_object_route():
    payload = b"x" * (RUNTIME.MAX_INJECTION_PAYLOAD_BYTES + 1)
    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.encode_injection(payload)
    message = str(excinfo.value)
    assert "exceeds the registered ceiling" in message
    assert "rather than truncating" in message


def test_a_missing_injection_refuses_rather_than_defaulting(tmp_path):
    with pytest.raises(RUNTIME.RuntimeBindingDefect):
        RUNTIME.reconstruct_injection(environ={},
                                      out_dir=str(tmp_path / "injected"))


# ---------------------------------------------------------------------------
# 10.4  Bad launch inputs refuse before any create or start command
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lock_mutation,receipt_mutation,digest,commit,reason", [
    (None, None, None, None, None),  # the accepting control
    (lambda lock: "not a mapping", None, None, None, "not a document"),
    (None, lambda receipt: "not a mapping", None, None, "not a document"),
    (None, lambda receipt: dict(receipt, passed=False,
                                authorizes_model_pilot=False),
     None, None, "does not record a pass"),
    (None, lambda receipt: dict(receipt, attempt_id=""),
     None, None, "attempt id"),
    (None, None, OTHER_DIGEST, None, "image digest"),
    (None, None, None, OTHER_COMMIT, "ready commit"),
    (lambda lock: dict(lock, generation=1), None, None, None, "generation"),
    (lambda lock: dict(lock, superseded=True), None, None, None, "superseded"),
    (lambda lock: dict(lock, state="STUDY3_P0_R1_PILOT_CONSUMED"),
     None, None, None, "state"),
    (None, lambda receipt: dict(receipt, tokenizer_encodes=1),
     None, None, "replay-only"),
    (None, lambda receipt: dict(receipt, gpu_allocated=True),
     None, None, "GPU allocation"),
    (None, lambda receipt: {key: value for key, value in receipt.items()
                            if key != "checkpoint_downloads"},
     None, None, "not a zero-operation proof"),
])
def test_bad_launch_input_refuses_before_any_job_command(
        lock_mutation, receipt_mutation, digest, commit, reason):
    lock = _valid_lock()
    receipt = _valid_receipt(lock)
    if lock_mutation is not None:
        lock = lock_mutation(lock)
    if receipt_mutation is not None:
        receipt = receipt_mutation(receipt)

    if reason is None:
        report = RUNTIME.validate_launch_inputs(lock, receipt, DIGEST, COMMIT)
        assert report["job_name"] == RUNTIME.JOB_NAME
        assert report["entrypoint"] == RUNTIME.MODEL_PILOT_ENTRYPOINT
        assert report["replica_retry_limit"] == 0
        assert report["parallelism"] == 1
        assert report["replica_completion_count"] == 1
        return

    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.validate_launch_inputs(
            lock, receipt, digest or DIGEST, commit or COMMIT)
    assert reason.lower() in str(excinfo.value).lower()


def test_a_superseded_lock_refuses_and_generation_1_is_never_launchable():
    lock = _valid_lock()
    receipt = _valid_receipt(lock)
    superseded = dict(lock, superseded=True)
    with pytest.raises(RUNTIME.RuntimeBindingDefect):
        RUNTIME.validate_launch_inputs(superseded, receipt, DIGEST, COMMIT)
    report = LOCK.verify_generation_1_is_preserved_and_inert()
    assert report["launchable"] is False
    assert report["superseded"] is True
    assert report["consumed"] is False


def test_a_receipt_bound_to_a_different_lock_refuses():
    lock = _valid_lock()
    receipt = _valid_receipt(lock)
    other_bytes = json.dumps(dict(lock, state="OTHER")).encode("utf-8")
    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.validate_launch_inputs(lock, receipt, DIGEST, COMMIT,
                                       lock_bytes=other_bytes)
    assert "different execution lock" in str(excinfo.value)


def test_the_launcher_refuses_when_an_execution_history_already_exists():
    lock = _valid_lock()
    receipt = _valid_receipt(lock)
    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.validate_launch_inputs(
            lock, receipt, DIGEST, COMMIT,
            existing_executions=[{"name": "an-earlier-execution"}])
    message = str(excinfo.value)
    assert "one-shot" in message
    assert "no execution is ever deleted" in message


def test_a_hash_only_receipt_is_not_a_receipt():
    """A digest of a receipt is not the receipt, and never authorizes a job."""
    lock = _valid_lock()
    receipt = _valid_receipt(lock)
    payload = json.dumps(receipt, sort_keys=True).encode("utf-8")
    hash_only = {"sha256": _sha256(payload), "bytes": len(payload)}
    with pytest.raises(RUNTIME.RuntimeBindingDefect):
        RUNTIME.validate_launch_inputs(lock, hash_only, DIGEST, COMMIT)


def test_injected_receipt_bytes_must_be_the_receipt_that_was_validated():
    lock = _valid_lock()
    receipt = _valid_receipt(lock)
    tampered = json.dumps(dict(receipt, attempt_id=OTHER_ATTEMPT)) \
        .encode("utf-8")
    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.validate_launch_inputs(lock, receipt, DIGEST, COMMIT,
                                       receipt_bytes=tampered)
    assert "only the exact recovered receipt" in str(excinfo.value)


def test_the_ready_commit_argument_is_checked_rather_than_ignored():
    lock = _valid_lock()
    receipt = _valid_receipt(lock)
    accepted = RUNTIME.validate_launch_inputs(lock, receipt, DIGEST, COMMIT)
    assert accepted["ready_commit"] == COMMIT
    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.validate_launch_inputs(lock, receipt, DIGEST, OTHER_COMMIT)
    assert "ready commit" in str(excinfo.value).lower()
    # An absent ready commit is a refusal, not a silently accepted default.
    with pytest.raises(RUNTIME.RuntimeBindingDefect) as excinfo:
        RUNTIME.validate_launch_inputs(lock, receipt, DIGEST, None)
    assert "validated, never ignored" in str(excinfo.value)


def _write_launch_inputs(tmp_path, lock=None, digest_source=None):
    """Write lock and receipt files whose exact bytes agree with each other."""
    lock = lock if lock is not None else _valid_lock()
    lock_bytes = json.dumps(lock, indent=1, sort_keys=True,
                            ensure_ascii=True).encode("utf-8")
    receipt = _valid_receipt(digest_source if digest_source is not None
                             else lock, lock_bytes=lock_bytes)
    receipt_bytes = json.dumps(receipt, indent=1, sort_keys=True,
                               ensure_ascii=True).encode("utf-8")
    lock_path = tmp_path / "lock.json"
    receipt_path = tmp_path / "receipt.json"
    lock_path.write_bytes(lock_bytes)
    receipt_path.write_bytes(receipt_bytes)
    return str(lock_path), str(receipt_path)


def test_the_prestart_guard_refuses_a_wrong_image_before_any_az_command(
        tmp_path):
    lock_path, receipt_path = _write_launch_inputs(tmp_path)
    completed = subprocess.run(
        [sys.executable, os.path.join(CONTAINER_DIR, "p0_r1_prestart_guard.py"),
         "--lock-file", lock_path, "--receipt-file", receipt_path,
         "--image-digest", OTHER_DIGEST, "--ready-commit", COMMIT,
         "--src", REPO_ROOT],
        capture_output=True, text=True)
    assert completed.returncode == 1
    assert "P0_R1_LAUNCH_REFUSED=1" in completed.stdout
    assert "P0_R1_LAUNCH_INPUTS_VALIDATED=1" not in completed.stdout


def test_the_prestart_guard_accepts_the_matching_inputs(tmp_path):
    lock_path, receipt_path = _write_launch_inputs(tmp_path)
    completed = subprocess.run(
        [sys.executable, os.path.join(CONTAINER_DIR, "p0_r1_prestart_guard.py"),
         "--lock-file", lock_path, "--receipt-file", receipt_path,
         "--image-digest", DIGEST, "--ready-commit", COMMIT,
         "--src", REPO_ROOT],
        capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "P0_R1_LAUNCH_INPUTS_VALIDATED=1" in completed.stdout
    assert RUNTIME.MODEL_PILOT_ENTRYPOINT in completed.stdout


def test_the_prestart_guard_reads_the_attempt_id_without_authorizing(tmp_path):
    _, receipt_path = _write_launch_inputs(tmp_path)
    completed = subprocess.run(
        [sys.executable, os.path.join(CONTAINER_DIR, "p0_r1_prestart_guard.py"),
         "--receipt-file", receipt_path, "--print-attempt-id",
         "--src", REPO_ROOT],
        capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == ATTEMPT
    assert "P0_R1_LAUNCH_INPUTS_VALIDATED=1" not in completed.stdout


# ---------------------------------------------------------------------------
# 10.5  Complete-byte transport of synthetic replay artifacts
# ---------------------------------------------------------------------------

def test_synthetic_replay_bytes_survive_the_transport_and_recover_exactly(
        tmp_path):
    out_dir = str(tmp_path / "results")
    payloads = _synthetic_gate_artifacts(out_dir)
    log_text = "\n".join(TRANSPORT.encode(ATTEMPT, payloads))
    recovered = TRANSPORT.recover(log_text, attempt_id=ATTEMPT)
    assert sorted(recovered) == sorted(payloads)
    for name, payload in payloads.items():
        assert recovered[name] == payload
    receipt = TRANSPORT.reconstruction_receipt(ATTEMPT, recovered)
    assert [entry["name"] for entry in receipt["artifacts"]] == sorted(payloads)
    assert sum(entry["bytes"] for entry in receipt["artifacts"]) \
        == sum(len(p) for p in payloads.values())
    for entry in receipt["artifacts"]:
        assert entry["sha256"] == _sha256(payloads[entry["name"]])
    assert receipt["recovered_without_rerunning_the_gate"] is True
    assert receipt["hashes_alone_do_not_make_bytes_recoverable"] is True
    for counter in ("tokenizer_encodes", "tokenizer_constructions",
                    "checkpoint_downloads", "model_operations_performed"):
        assert receipt[counter] == 0
    assert receipt["gpu_allocated"] is False


@pytest.mark.parametrize("corrupt,accepts", [
    ("intact", True),
    ("missing", False),
    ("truncated", False),
    ("chunks_out_of_index_order", True),
    ("completion_line_moved_first", False),
    ("duplicated_identical", True),
    ("conflicting_duplicate", False),
    ("prefixed", True),
    ("wrong_attempt", False),
    ("interleaved_noise", True),
    ("no_completion", False),
])
def test_log_fixtures_have_the_registered_accept_or_refuse_behavior(
        tmp_path, corrupt, accepts):
    out_dir = str(tmp_path / "results")
    payloads = _synthetic_gate_artifacts(out_dir)
    lines = list(TRANSPORT.encode(ATTEMPT, payloads))

    if corrupt == "missing":
        del lines[len(lines) // 2]
    elif corrupt == "truncated":
        lines[len(lines) // 2] = lines[len(lines) // 2][:-6]
    elif corrupt == "chunks_out_of_index_order":
        # Interleaving is a real container-log behaviour. Recovery is by index,
        # so scrambled chunk order must still recover exactly; only the
        # manifest-then-completion tail order is structural.
        chunks = [line for line in lines
                  if line.startswith(TRANSPORT.CHUNK_MARKER)]
        tail = [line for line in lines
                if not line.startswith(TRANSPORT.CHUNK_MARKER)]
        lines = list(reversed(chunks)) + tail
    elif corrupt == "completion_line_moved_first":
        completion = [line for line in lines
                      if line.startswith(TRANSPORT.COMPLETE_MARKER)]
        rest = [line for line in lines
                if not line.startswith(TRANSPORT.COMPLETE_MARKER)]
        lines = completion + rest
    elif corrupt == "duplicated_identical":
        lines = lines + list(lines)
    elif corrupt == "conflicting_duplicate":
        victim = next(index for index, line in enumerate(lines)
                      if line.startswith(TRANSPORT.CHUNK_MARKER))
        parts = lines[victim].split("|")
        parts[-1] = "d=" + base64.b64encode(b"tampered").decode("ascii")
        lines.append("|".join(parts))
    elif corrupt == "prefixed":
        lines = ["2026-01-01T00:00:00Z stdout F " + line for line in lines]
    elif corrupt == "wrong_attempt":
        lines = [line.replace(ATTEMPT, OTHER_ATTEMPT) for line in lines]
    elif corrupt == "interleaved_noise":
        noisy = []
        for index, line in enumerate(lines):
            noisy.append(line)
            noisy.append("an unrelated container log line %d" % index)
        lines = noisy
    elif corrupt == "no_completion":
        lines = [line for line in lines
                 if not line.startswith(TRANSPORT.COMPLETE_MARKER)]

    log_text = "\n".join(lines)
    if accepts:
        recovered = TRANSPORT.recover(log_text, attempt_id=ATTEMPT)
        for name, payload in payloads.items():
            assert recovered[name] == payload
    else:
        with pytest.raises(TRANSPORT.TransportDefect):
            TRANSPORT.recover(log_text, attempt_id=ATTEMPT)


def test_a_recovery_that_loses_one_byte_refuses_to_authorize(tmp_path,
                                                             monkeypatch):
    """An almost-complete recovery is a defect, never a pass."""
    out_dir = str(tmp_path / "results")
    _synthetic_gate_artifacts(out_dir)

    real_recover = TRANSPORT.recover

    def lossy(log_text, attempt_id=None, allowed=None):
        recovered = real_recover(log_text, attempt_id=attempt_id,
                                 allowed=allowed)
        name = "p0_r1_replay_result.json"
        recovered[name] = recovered[name][:-1]
        return recovered

    monkeypatch.setattr(TRANSPORT, "recover", lossy)
    with pytest.raises(GATE.GateRefused) as excinfo:
        GATE.transport_and_verify(out_dir, ATTEMPT, stream=_Sink())
    assert "byte" in str(excinfo.value).lower()


def test_the_canary_exercises_more_than_the_projected_replay_volume():
    """Headroom is demonstrated, not assumed.

    The registered projection for the combined replay artifacts is a bound, not
    a measurement. The canary therefore drives the transport at twice that bound
    so a pass is evidence the route survives more than the real gate will emit.
    """
    assert TRANSPORT.CANARY_MINIMUM_TOTAL_BYTES >= \
        2 * TRANSPORT.MAX_PROJECTED_COMBINED_REPLAY_ARTIFACT_BYTES
    report = TRANSPORT.self_check()
    assert report["total_bytes"] >= TRANSPORT.CANARY_MINIMUM_TOTAL_BYTES
    assert report["artifacts"] == len(TRANSPORT.REPLAY_ARTIFACTS)
    assert report["max_line_bytes"] <= TRANSPORT.MAX_LINE_BYTES
    assert report["lines"] > 0


def test_an_envelope_line_never_exceeds_the_registered_truncation_boundary():
    payloads = {name: bytes(bytearray((index * 7 + offset) % 256
                                      for offset in range(4096)))
                for index, name in enumerate(TRANSPORT.REPLAY_ARTIFACTS)}
    for line in TRANSPORT.encode(ATTEMPT, payloads):
        assert len(line.encode("utf-8")) <= TRANSPORT.MAX_LINE_BYTES


class _Sink(object):
    def __init__(self):
        self.lines = []

    def write(self, text):
        self.lines.append(text)

    def flush(self):
        pass


# ---------------------------------------------------------------------------
# 10.6  The private object writer: identity, no overwrite, readback, order
# ---------------------------------------------------------------------------

def test_the_private_writer_uses_managed_identity_and_no_secret():
    source = _uncommented(_text(os.path.join(P0_R1_DIR,
                                             "p0_r1_blob_transport.py")))
    assert "ManagedIdentityCredential" in source
    # The secret-bearing authentication routes are absent, not merely unused.
    for forbidden in ("from_connection_string", "account_key=",
                      "credential=account", "generate_blob_sas",
                      "AccountSasPermissions"):
        assert forbidden not in source, forbidden
    assert BLOB.ACCOUNT == "stjspacefiles0709085305"
    assert BLOB.CONTAINER == "jspace-results"
    assert BLOB.IDENTITY_ROLE == "Storage Blob Data Contributor"
    assert BLOB.ACCOUNT_URL.startswith("https://")
    assert "AZURE_STORAGE_CONNECTION_STRING" \
        in BLOB.FORBIDDEN_CREDENTIAL_ENVIRONMENT


@pytest.mark.parametrize("variable", list(BLOB.FORBIDDEN_CREDENTIAL_ENVIRONMENT))
def test_a_secret_in_the_environment_refuses_the_production_backend(
        monkeypatch, variable):
    monkeypatch.setenv(variable, "a-secret-that-must-never-be-used")
    with pytest.raises(BLOB.BlobTransportDefect) as excinfo:
        BLOB.assert_no_forbidden_credential()
    assert variable in str(excinfo.value)


def test_the_private_writer_reads_back_and_writes_the_manifest_last():
    backend = BLOB.InMemoryBackend()
    report = BLOB.canary(ATTEMPT, backend=backend)
    assert report["manifest_last"] is True
    assert report["recovered_byte_exact"] is True
    assert report["overwrite_used"] is False
    assert backend.writes[-1].endswith(BLOB.MANIFEST_NAME)
    assert backend.writes[-1].startswith(report["prefix"])
    for record in report["artifacts"]:
        stored = backend.download(report["prefix"] + record["name"])
        assert _sha256(stored) == record["sha256"]
        assert len(stored) == record["bytes"]


def test_the_private_writer_refuses_to_overwrite_an_existing_object():
    backend = BLOB.InMemoryBackend()
    transport = BLOB.PrivateBlobTransport(ATTEMPT, backend=backend)
    transport.upload_and_verify("p0_r1_replay_result.json", b"first")
    with pytest.raises(BLOB.BlobTransportDefect) as excinfo:
        transport.upload_and_verify("p0_r1_replay_result.json", b"second")
    assert "never overwritten" in str(excinfo.value)
    assert backend.objects[transport.prefix + "p0_r1_replay_result.json"] \
        == b"first"


def test_each_attempt_writes_under_its_own_disjoint_prefix():
    first = BLOB.attempt_prefix(ATTEMPT)
    second = BLOB.attempt_prefix(OTHER_ATTEMPT)
    assert first != second
    assert not first.startswith(second) and not second.startswith(first)
    assert first.endswith("/")
    backend = BLOB.InMemoryBackend()
    BLOB.PrivateBlobTransport(ATTEMPT, backend=backend) \
        .upload_and_verify("p0_r1_replay_result.json", b"first attempt")
    other = BLOB.PrivateBlobTransport(OTHER_ATTEMPT, backend=backend)
    other.assert_prefix_unused(["p0_r1_replay_result.json"])
    other.upload_and_verify("p0_r1_replay_result.json", b"second attempt")
    assert backend.objects[first + "p0_r1_replay_result.json"] \
        == b"first attempt"
    assert backend.objects[second + "p0_r1_replay_result.json"] \
        == b"second attempt"


def test_a_reused_prefix_is_refused_before_the_first_write():
    backend = BLOB.InMemoryBackend()
    first = BLOB.PrivateBlobTransport(ATTEMPT, backend=backend)
    first.upload_and_verify("p0_r1_replay_result.json", b"an observation")
    with pytest.raises(BLOB.BlobTransportDefect):
        BLOB.PrivateBlobTransport(ATTEMPT, backend=backend) \
            .assert_prefix_unused(["p0_r1_replay_result.json"])
    assert backend.objects[first.prefix + "p0_r1_replay_result.json"] \
        == b"an observation"


def test_a_tampered_object_fails_readback_verification():
    backend = BLOB.InMemoryBackend()
    transport = BLOB.PrivateBlobTransport(ATTEMPT, backend=backend)
    transport.upload_and_verify("p0_r1_replay_result.json", b"authentic")
    transport.write_manifest(["p0_r1_replay_result.json"])
    backend.objects[transport.prefix + "p0_r1_replay_result.json"] = b"forged"
    with pytest.raises(BLOB.BlobTransportDefect) as excinfo:
        transport.recover_all()
    assert "does not read back" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 10.7  A production launcher fixture injects exact bytes and the right prefix
# ---------------------------------------------------------------------------

def test_the_launcher_injects_the_exact_receipt_and_lock_bytes(tmp_path):
    lock_bytes = json.dumps(_valid_lock(), indent=1,
                            sort_keys=True).encode("utf-8")
    receipt_bytes = json.dumps(_valid_receipt(), indent=1,
                               sort_keys=True).encode("utf-8")
    lock_path = tmp_path / "lock.json"
    receipt_path = tmp_path / "receipt.json"
    lock_path.write_bytes(lock_bytes)
    receipt_path.write_bytes(receipt_bytes)

    encoded = subprocess.run(
        [sys.executable, os.path.join(P0_R1_DIR, "p0_r1_runtime_binding.py"),
         "--encode", "--file", str(lock_path)],
        capture_output=True, text=True, check=True).stdout
    assert RUNTIME.decode_injection(encoded) == lock_bytes

    environ = {RUNTIME.INJECTION_LOCK_ENV: encoded,
               RUNTIME.INJECTION_RECEIPT_ENV:
                   RUNTIME.encode_injection(receipt_bytes)}
    out_dir = str(tmp_path / "injected")
    RUNTIME.reconstruct_injection(environ=environ, out_dir=out_dir)
    assert _read(os.path.join(out_dir, RUNTIME.INJECTED_LOCK_NAME)) \
        == lock_bytes
    assert _read(os.path.join(out_dir, RUNTIME.INJECTED_RECEIPT_NAME)) \
        == receipt_bytes


def test_the_launcher_pins_retry_to_zero_and_a_single_completion():
    launcher = _text(os.path.join(CONTAINER_DIR,
                                  "p0_r1_launch_gpu_pilot_v2.sh"))
    assert "--replica-retry-limit 0" in launcher
    assert "--parallelism 1" in launcher
    assert "--replica-completion-count 1" in launcher
    job = _text(os.path.join(CONTAINER_DIR, "p0_r1_gpu_job_v2.yaml"))
    assert "replicaRetryLimit: 0" in job
    assert "parallelism: 1" in job
    assert "replicaCompletionCount: 1" in job


def test_the_launcher_requires_every_input_and_has_no_defaults():
    launcher = _text(os.path.join(CONTAINER_DIR,
                                  "p0_r1_launch_gpu_pilot_v2.sh"))
    for flag in ("--image-digest", "--ready-commit", "--lock-file",
                 "--receipt-file"):
        assert flag in launcher
    assert "is mandatory; this launcher has no defaults" in launcher
    assert "--confirm-single-model-operating-execution" in launcher


def test_the_launcher_refuses_when_an_execution_already_exists():
    launcher = _text(os.path.join(CONTAINER_DIR,
                                  "p0_r1_launch_gpu_pilot_v2.sh"))
    assert "az containerapp job execution list" in launcher
    assert "already has" in launcher
    # It must not delete history to make the count look like zero.
    assert "execution delete" not in launcher
    assert "job delete" not in launcher


def test_the_successor_wrapper_has_no_default_mode_and_names_the_live_gate():
    successor = _text(os.path.join(CONTAINER_DIR, "p0_r1_successor.sh"))
    assert "a mode is required; there is no default" in successor
    for mode in ("preflight)", "live-replay)", "launch-pilot)"):
        assert mode in successor
    assert "--confirm-consumes-the-one-shot-replay-envelope" in successor
    assert "THIS IS NOT A DRY RUN" in successor


# ---------------------------------------------------------------------------
# 10.8  Forced failures retain conservative counters and partial bytes
# ---------------------------------------------------------------------------

class _FailingExecutor(object):
    """A synthetic executor that fails at an exact registered stage.

    It appends to the caller-owned partial-result object rather than to a local
    variable, which is precisely the property under test: an exception inside
    the executor must not take the observations with it.
    """

    def __init__(self, stage, rows=0):
        self.stage = stage
        self.rows = rows

    def execute(self, authorized, counters, partial, journal, **kwargs):
        for index in range(self.rows):
            token = journal.admit("scored_row", {"s1_scored_rows": 1,
                                                 "total_scored_rows": 1})
            partial.scored_rows.append({
                "role": "RT", "profile": "P1", "row_id": "r%04d" % index,
                "cell": "s1", "observed": index,
            })
            journal.complete(token)
        journal.admit(self.stage)
        raise RuntimeError("forced failure at %s" % self.stage)


def _authorization(lock=None, receipt=None, attempt=ATTEMPT):
    """The execution authorization the production runner actually requires."""
    lock = lock if lock is not None else _valid_lock()
    lock_bytes = json.dumps(lock, indent=1, sort_keys=True,
                            ensure_ascii=True).encode("utf-8")
    receipt = receipt if receipt is not None else _valid_receipt(
        lock, attempt=attempt, lock_bytes=lock_bytes)
    return {
        "p0_r1_pilot_execution_authorized": True,
        "replay_gate_passed_in_this_session": True,
        "execution_lock": lock,
        "replay_receipt": receipt,
        "attempt_id": attempt,
        "ready_commit": COMMIT,
        "image_digest": DIGEST,
    }, lock_bytes, json.dumps(receipt, indent=1, sort_keys=True,
                              ensure_ascii=True).encode("utf-8")


def _run_pilot(out_dir, executor, blob_transport=None, sinks=None):
    authorization, lock_bytes, receipt_bytes = _authorization()
    return RUNNER.run(
        authorization=authorization, out_dir=out_dir,
        lock_bytes=lock_bytes, receipt_bytes=receipt_bytes,
        ready_commit=COMMIT, image_digest=DIGEST,
        executor=executor, blob_transport=blob_transport, sinks=sinks)


@pytest.mark.parametrize("stage", [
    "tokenizer_construction",
    "prompt_encode",
    "checkpoint_download_or_load",
    "prefill",
    "generation_or_decode",
    "parser_call",
    "scored_row",
])
def test_a_forced_failure_retains_partial_bytes_and_conservative_counters(
        tmp_path, stage):
    out_dir = str(tmp_path / "results")
    report = _run_pilot(out_dir, _FailingExecutor(stage, rows=3))

    assert report["state"] == RUNNER.STATE_STOPPED_WITH_PARTIAL_RESULT
    written = {artifact["name"] for artifact in report["artifacts"]}
    for name in RUNNER.PILOT_ARTIFACTS:
        assert name in written
        assert os.path.getsize(os.path.join(out_dir, name)) > 0

    result = json.loads(_text(os.path.join(out_dir,
                                           "p0_r1_model_pilot_result.json")))
    assert len(result["scored_rows"]) == 3
    assert result["every_valid_row_and_partial_result_is_retained"] is True
    assert result["no_counter_was_reset_and_no_row_was_repaired"] is True
    assert result["terminating_exception"]["exception"] == "RuntimeError"
    assert result["terminating_exception"][
        "reached_the_exception_boundary"] is True
    assert result["counters"]["exceptions_observed"] == 1
    assert stage in json.dumps(result)

    receipt = json.loads(_text(os.path.join(
        out_dir, "p0_r1_model_pilot_receipt.json")))
    possibly = receipt["conservative_report"][
        "operations_possibly_started_without_a_durable_completion"]
    assert any(entry["operation"] == stage for entry in possibly)
    # A stopped attempt is never silently retried.
    assert receipt["retry_requires_a_separate_operator_decision"] is True
    assert receipt["authorizes_retry"] is False


def test_a_failure_before_the_first_admission_still_writes_every_artifact(
        tmp_path):
    class _ImmediateFailure(object):
        def execute(self, *args, **kwargs):
            raise MemoryError("forced failure before any admission")

    out_dir = str(tmp_path / "results")
    report = _run_pilot(out_dir, _ImmediateFailure())
    assert report["state"] == RUNNER.STATE_STOPPED_WITH_PARTIAL_RESULT
    for name in RUNNER.PILOT_ARTIFACTS:
        assert os.path.getsize(os.path.join(out_dir, name)) > 0
    result = json.loads(_text(os.path.join(out_dir,
                                           "p0_r1_model_pilot_result.json")))
    assert result["scored_rows"] == []
    assert result["terminating_exception"]["exception"] == "MemoryError"
    # An empty partial result is still a published partial result.
    assert result["state"] == RUNNER.STATE_STOPPED_WITH_PARTIAL_RESULT
    assert result["counters"]["total_scored_rows"] == 0


@pytest.mark.parametrize("raised,name", [
    (KeyboardInterrupt, "KeyboardInterrupt"),
    (SystemExit, "SystemExit"),
    (GeneratorExit, "GeneratorExit"),
])
def test_a_baseexception_does_not_escape_the_boundary(tmp_path, raised, name):
    class _Aborted(object):
        def execute(self, *args, **kwargs):
            raise raised()

    out_dir = str(tmp_path / "results")
    report = _run_pilot(out_dir, _Aborted())
    assert report["state"] == RUNNER.STATE_STOPPED_WITH_PARTIAL_RESULT
    result = json.loads(_text(os.path.join(out_dir,
                                           "p0_r1_model_pilot_result.json")))
    assert result["terminating_exception"]["exception"] == name


def test_a_primary_journal_sink_failure_refuses_instead_of_degrading(tmp_path):
    """A mirror is redundancy; the primary sink *is* the evidence."""
    class _BrokenPrimary(object):
        kind = "broken-primary"
        names = ()

        def write(self, name, payload):
            raise JOURNAL.JournalDefect("the primary journal is unwritable")

        def read(self, name):
            raise JOURNAL.JournalDefect("the primary journal is unreadable")

    with pytest.raises(JOURNAL.JournalDefect) as excinfo:
        JOURNAL.AttemptJournal(ATTEMPT, [_BrokenPrimary()]).open_attempt()
    assert "unwritable" in str(excinfo.value)
    # And the refusal happens before a single operation can be admitted.
    journal = JOURNAL.AttemptJournal(ATTEMPT, [_BrokenPrimary()])
    with pytest.raises(JOURNAL.JournalDefect):
        journal.admit("prefill")
    assert journal.open_admissions() == []


def test_an_upload_failure_does_not_discard_the_local_artifacts(tmp_path):
    class _BrokenBackend(object):
        def exists(self, name):
            raise BLOB.BlobTransportDefect("forced sink failure")

        def upload(self, name, payload, overwrite=False):
            raise BLOB.BlobTransportDefect("forced sink failure")

        def download(self, name):
            raise BLOB.BlobTransportDefect("forced sink failure")

        def list_names(self, prefix):
            raise BLOB.BlobTransportDefect("forced sink failure")

    class _BrokenTransport(object):
        prefix = BLOB.attempt_prefix(ATTEMPT)
        backend = _BrokenBackend()

        def upload_directory(self, *args, **kwargs):
            raise BLOB.BlobTransportDefect("forced upload failure")

        def upload_and_verify(self, *args, **kwargs):
            raise BLOB.BlobTransportDefect("forced sink failure")

    out_dir = str(tmp_path / "results")
    report = _run_pilot(out_dir, _FailingExecutor("prefill", rows=2),
                        blob_transport=_BrokenTransport())
    assert "forced upload failure" in report["blob_error"]
    for name in RUNNER.PILOT_ARTIFACTS:
        assert os.path.getsize(os.path.join(out_dir, name)) > 0
    result = json.loads(_text(os.path.join(out_dir,
                                           "p0_r1_model_pilot_result.json")))
    assert len(result["scored_rows"]) == 2
    # The lost remote mirror is published as a degradation, never swallowed:
    # a silent mirror failure would be indistinguishable from a durable one.
    conservative = result["conservative_report"]
    assert conservative["durable_mirror_degraded"] is True
    assert conservative["mirror_failures"]
    for failure in conservative["mirror_failures"]:
        assert "forced sink failure" in failure["detail"]
        assert failure[
            "the_primary_journal_and_the_artifacts_are_unaffected"] is True
    # The primary local journal is complete despite the mirror being gone.
    journal_dir = os.path.join(out_dir, "journal")
    assert len(os.listdir(os.path.join(journal_dir, JOURNAL.JOURNAL_OBJECT_PREFIX
                                       ))) == conservative["journal_entries"]


def test_a_summariser_refusal_never_discards_the_rows_it_could_not_summarise(
        tmp_path):
    """The rows are the observation; the summary is only a report of them."""
    class _MalformedRows(object):
        def execute(self, authorized, counters, partial, journal, **kwargs):
            # Two rows that a real crash could plausibly leave behind: the
            # second is a duplicate identity the summariser refuses to accept.
            for _ in range(2):
                token = journal.admit("scored_row", {"s1_scored_rows": 1,
                                                     "total_scored_rows": 1})
                partial.scored_rows.append({"role": "RT", "profile": "P1",
                                            "row_id": "r0001", "cell": "s1"})
                journal.complete(token)
            raise RuntimeError("forced failure after a duplicate row identity")

    out_dir = str(tmp_path / "results")
    report = _run_pilot(out_dir, _MalformedRows())
    assert report["state"] == RUNNER.STATE_STOPPED_WITH_PARTIAL_RESULT
    for name in RUNNER.PILOT_ARTIFACTS:
        assert os.path.getsize(os.path.join(out_dir, name)) > 0

    result = json.loads(_text(os.path.join(out_dir,
                                           "p0_r1_model_pilot_result.json")))
    assert len(result["scored_rows"]) == 2
    assert result["summary_unavailable"]["summariser_refused"] is True
    assert result["summary_unavailable"][
        "no_row_was_discarded_to_obtain_a_summary"] is True
    assert result["no_counter_was_reset_and_no_row_was_repaired"] is True


def test_an_unauthorized_run_refuses_before_the_journal_exists(tmp_path):
    """The only path that raises is a refusal before any irreversible step."""
    out_dir = str(tmp_path / "results")
    with pytest.raises(RUNNER.ExecutionRefused):
        RUNNER.run(authorization=None, out_dir=out_dir,
                   executor=_FailingExecutor("prefill"))
    assert not os.path.exists(out_dir)


def test_a_consumed_lock_is_never_re_armed(tmp_path):
    lock = _valid_lock()
    lock["legal_status"] = dict(lock["legal_status"],
                                p0_r1_pilot_execution_consumed=True)
    authorization, lock_bytes, receipt_bytes = _authorization(lock=lock)
    with pytest.raises(RUNNER.ExecutionRefused) as excinfo:
        RUNNER.run(authorization=authorization,
                   out_dir=str(tmp_path / "results"),
                   lock_bytes=lock_bytes, receipt_bytes=receipt_bytes,
                   ready_commit=COMMIT, image_digest=DIGEST,
                   executor=_FailingExecutor("prefill"))
    assert "one-shot and is never re-armed" in str(excinfo.value)


def test_a_receipt_from_another_attempt_refuses(tmp_path):
    authorization, lock_bytes, receipt_bytes = _authorization()
    authorization["attempt_id"] = OTHER_ATTEMPT
    with pytest.raises(RUNNER.ExecutionRefused) as excinfo:
        RUNNER.run(authorization=authorization,
                   out_dir=str(tmp_path / "results"),
                   lock_bytes=lock_bytes, receipt_bytes=receipt_bytes,
                   ready_commit=COMMIT, image_digest=DIGEST,
                   executor=_FailingExecutor("prefill"))
    assert "same authorized attempt" in str(excinfo.value)


def test_an_unverified_transport_never_authorizes_a_model_operation(tmp_path):
    lock = _valid_lock()
    lock_bytes = json.dumps(lock, indent=1, sort_keys=True,
                            ensure_ascii=True).encode("utf-8")
    receipt = _valid_receipt(lock, lock_bytes=lock_bytes)
    receipt["transport"] = {"complete_byte_recovery_verified": False}
    authorization, _, _ = _authorization(lock=lock, receipt=receipt)
    with pytest.raises(RUNNER.ExecutionRefused) as excinfo:
        RUNNER.run(authorization=authorization,
                   out_dir=str(tmp_path / "results"),
                   lock_bytes=lock_bytes,
                   ready_commit=COMMIT, image_digest=DIGEST,
                   executor=_FailingExecutor("prefill"))
    assert "verified complete-byte recovery" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 10.9  A hard-terminated subprocess leaves an unmistakable journal
# ---------------------------------------------------------------------------

def test_a_hard_terminated_attempt_leaves_a_last_admitted_operation(tmp_path):
    journal_dir = str(tmp_path / "journal")
    script = tmp_path / "hard_kill.py"
    script.write_text(
        "import os, sys\n"
        "sys.path.insert(0, %r)\n"
        "import p0_r1_journal as J\n"
        "journal = J.AttemptJournal(%r, [J.LocalSequenceSink(%r)])\n"
        "journal.open_attempt()\n"
        "token = journal.admit('checkpoint_download_or_load', "
        "{'checkpoint_downloads': 1})\n"
        "os._exit(137)\n" % (P0_R1_DIR, ATTEMPT, journal_dir),
        encoding="utf-8")

    completed = subprocess.run([sys.executable, str(script)],
                               capture_output=True)
    assert completed.returncode == 137

    sink = JOURNAL.LocalSequenceSink(journal_dir)
    entries = [json.loads(sink.read(name).decode("utf-8"))
               for name in sink.names()
               if name.startswith(JOURNAL.JOURNAL_OBJECT_PREFIX + "/")]
    entries.sort(key=lambda entry: entry["sequence"])
    assert entries, "a hard kill must still leave a durable journal"

    report = JOURNAL.restart_report(ATTEMPT, entries)
    possibly = report["operations_possibly_started_without_a_durable_completion"]
    assert [entry["operation"] for entry in possibly] \
        == ["checkpoint_download_or_load"]
    assert report["last_admitted_operation"] == "checkpoint_download_or_load"
    for key in ("resume_authorized", "repair_authorized",
                "replace_authorized", "rerun_authorized"):
        assert report[key] is False

    # The decisive property: this cannot be read as a zero-operation attempt.
    # The validator is a fail-closed refusal, not a predicate that can return
    # a convenient True, so the absence of a retry authorization is structural.
    with pytest.raises(JOURNAL.JournalDefect) as excinfo:
        JOURNAL.validate_infrastructure_retry(journal_entries=entries)
    message = str(excinfo.value)
    assert "admits 1 irreversible operation(s)" in message
    assert "an admitted operation may have started" in message


def test_a_zero_operation_journal_is_distinguishable_from_a_dangling_one(
        tmp_path):
    clean = JOURNAL.AttemptJournal(
        ATTEMPT, [JOURNAL.LocalSequenceSink(str(tmp_path / "clean"))])
    clean.open_attempt()
    clean_report = JOURNAL.restart_report(ATTEMPT, clean.entries())
    assert clean_report[
        "operations_possibly_started_without_a_durable_completion"] == []
    assert clean_report["last_admitted_operation"] is None

    dangling = JOURNAL.AttemptJournal(
        ATTEMPT, [JOURNAL.LocalSequenceSink(str(tmp_path / "dangling"))])
    dangling.open_attempt()
    dangling.admit("prompt_encode", {"tokenizer_encoded_sequences": 1})
    dangling_report = JOURNAL.restart_report(ATTEMPT, dangling.entries())
    assert [entry["operation"] for entry in dangling_report[
        "operations_possibly_started_without_a_durable_completion"]] \
        == ["prompt_encode"]

    # Both refuse a retry, but only the dangling one refuses *because* an
    # irreversible operation may already have run. The two are never conflated.
    with pytest.raises(JOURNAL.JournalDefect) as clean_error:
        JOURNAL.validate_infrastructure_retry(journal_entries=clean.entries())
    with pytest.raises(JOURNAL.JournalDefect) as dangling_error:
        JOURNAL.validate_infrastructure_retry(
            journal_entries=dangling.entries())
    assert "irreversible operation" not in str(clean_error.value)
    assert "admits 1 irreversible operation(s)" in str(dangling_error.value)


def test_a_completed_admission_is_not_reported_as_possibly_started(tmp_path):
    journal = JOURNAL.AttemptJournal(
        ATTEMPT, [JOURNAL.LocalSequenceSink(str(tmp_path / "journal"))])
    journal.open_attempt()
    token = journal.admit("prompt_encode", {"tokenizer_encoded_sequences": 1})
    journal.complete(token)
    report = JOURNAL.restart_report(ATTEMPT, journal.entries())
    assert report[
        "operations_possibly_started_without_a_durable_completion"] == []
    assert journal.open_admissions() == []


@pytest.mark.parametrize("operation", list(JOURNAL.IRREVERSIBLE_OPERATIONS))
def test_every_irreversible_operation_is_admitted_before_it_can_run(
        tmp_path, operation):
    journal = JOURNAL.AttemptJournal(
        ATTEMPT, [JOURNAL.LocalSequenceSink(str(tmp_path / operation))])
    journal.open_attempt()
    journal.admit(operation)
    report = JOURNAL.restart_report(ATTEMPT, journal.entries())
    assert [entry["operation"] for entry in report[
        "operations_possibly_started_without_a_durable_completion"]] \
        == [operation]


def test_a_journal_sequence_number_is_written_exactly_once(tmp_path):
    sink = JOURNAL.LocalSequenceSink(str(tmp_path / "journal"))
    journal = JOURNAL.AttemptJournal(ATTEMPT, [sink])
    journal.open_attempt()
    name = [n for n in sink.names()
            if n.startswith(JOURNAL.JOURNAL_OBJECT_PREFIX + "/")][0]
    with pytest.raises(JOURNAL.JournalDefect) as excinfo:
        sink.write(name, b"a replacement observation")
    assert "written once" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 10.10  The shell emits a receipt on every recoverable exit path
# ---------------------------------------------------------------------------

def test_the_pilot_shell_traps_every_premature_exit():
    shell = _text(os.path.join(CONTAINER_DIR, "p0_r1_model_pilot_v2.sh"))
    assert "trap on_premature_exit EXIT" in shell
    assert "--infrastructure-receipt" in shell
    assert "P0_R1_RETRY_AUTHORIZED=false" in shell
    # The trap is installed before the first thing that can fail.
    assert shell.index("trap on_premature_exit EXIT") \
        < shell.index("verify-layout")


def test_the_infrastructure_receipt_refuses_rather_than_authorizes(tmp_path):
    out = tmp_path / "infra.json"
    completed = subprocess.run(
        [sys.executable, os.path.join(P0_R1_DIR, "p0_r1_journal.py"),
         "--infrastructure-receipt", "--attempt", ATTEMPT,
         "--stage", "checkpoint_access", "--detail", "forced",
         "--image-digest", DIGEST, "--ready-commit", COMMIT,
         "--out", str(out)],
        capture_output=True, text=True)
    assert completed.returncode == 0
    document = json.loads(_text(str(out)))
    assert document["schema_version"] \
        == JOURNAL.INFRASTRUCTURE_RECEIPT_SCHEMA_VERSION
    assert document["authorizes_retry"] is False
    assert document["authorizes_model_pilot"] is False
    assert document["retry_requires_a_separate_operator_decision"] is True
    assert document["gpu_workload_allocated"] is True
    assert document["an_allocated_job_is_not_a_zero_event_non_attempt"] is True
    assert document["state"] == JOURNAL.STATE_INFRASTRUCTURE


def test_the_replay_shell_requires_a_verified_transport_before_authorizing():
    shell = _text(os.path.join(CONTAINER_DIR, "p0_r1_replay_v2.sh"))
    assert "p0_r1_replay_transport_receipt.json" in shell
    assert "p0_r1_verify_replay_receipt.py" in shell
    checker = _text(os.path.join(CONTAINER_DIR,
                                 "p0_r1_verify_replay_receipt.py"))
    assert "not backed by a verified transport" in checker


def test_the_replay_shell_runs_the_installed_entry_point_not_a_mount():
    task = _text(os.path.join(CONTAINER_DIR, "p0_r1_acr_task_v2.yaml"))
    assert RUNTIME.REPLAY_ENTRYPOINT in task
    assert "/workspace/p0_r1_replay.sh" not in _uncommented(task)
    assert "P0_R1_SRC=/opt/jspace/src" in task


# ---------------------------------------------------------------------------
# 10.11  Generation 1 and every protected byte remain unchanged
# ---------------------------------------------------------------------------

def test_the_generation_1_lock_and_image_digest_are_unchanged():
    path = os.path.join(P0_R1_DIR, "p0_r1_execution_lock.json")
    raw = _read(path)
    assert len(raw) == LOCK.GENERATION_1_LOCK["bytes"]
    assert _sha256(raw) == LOCK.GENERATION_1_LOCK["sha256"]
    document = json.loads(raw.decode("utf-8"))
    assert document["image"]["digest"] == LOCK.GENERATION_1_IMAGE_DIGEST
    assert document["legal_status"]["p0_r1_pilot_execution_consumed"] is False
    assert document["executable_code"]["commit"] \
        == LOCK.GENERATION_1_EXECUTABLE_CODE_COMMIT


def test_the_generation_1_executable_paths_still_rehash_correctly():
    """Generation 2 is strictly additive: no bound generation-1 byte moved."""
    lock = LOCK1.load_lock()
    LOCK1.verify_executable_bytes(lock)


def test_generation_2_is_strictly_additive():
    for path in LOCK1.EXECUTABLE_CODE_PATHS:
        assert path in LOCK.EXECUTABLE_CODE_PATHS
    assert set(LOCK.GENERATION_2_CODE_PATHS).isdisjoint(
        LOCK1.EXECUTABLE_CODE_PATHS)
    assert len(LOCK.EXECUTABLE_CODE_PATHS) \
        == len(LOCK1.EXECUTABLE_CODE_PATHS) + len(LOCK.GENERATION_2_CODE_PATHS)


def test_the_three_authorities_reproduce_their_registered_identities():
    for entry in LOCK.AUTHORITIES:
        raw = _read(os.path.join(REPO_ROOT, *entry["path"].split("/")))
        assert len(raw) == entry["bytes"], entry["path"]
        assert _sha256(raw) == entry["sha256"], entry["path"]


def test_the_immutable_p0_namespace_and_registry_are_untouched():
    for relative in (
            "studies/study3/protocol/"
            "interface_calibration_rendering_registry_v0_6.json",
            "studies/study3/pilot/p0/corpus/p0_corpus.json"):
        assert os.path.exists(os.path.join(REPO_ROOT, *relative.split("/")))
    import p0_r1_validate as VALIDATE
    import p0_r1_factorization as FACT
    assert VALIDATE.check_corpus() == []
    assert VALIDATE.check_no_results_published() == []
    # The generation-2 lock re-derives the same immutable-source identities.
    assert FACT.verify_immutable_sources() == _valid_lock()["corpus_and_p0_t"]


def test_generation_1_is_recorded_as_superseded_and_inert_not_consumed():
    report = LOCK.verify_generation_1_is_preserved_and_inert()
    assert report["superseded"] is True
    assert report["launchable"] is False
    assert report["consumed"] is False
    assert report["superseded_by"] == \
        "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json"
    assert report["image_digest"] == LOCK.GENERATION_1_IMAGE_DIGEST
    assert report["executable_code_commit"] \
        == LOCK.GENERATION_1_EXECUTABLE_CODE_COMMIT
    assert report["bytes"] == LOCK.GENERATION_1_LOCK["bytes"]
    assert report["sha256"] == LOCK.GENERATION_1_LOCK["sha256"]
    # An unconsumed historical object: every irreversible counter is still zero.
    for counter in ("executions", "gpu_allocations", "model_weight_loads",
                    "checkpoint_downloads", "tokenizer_constructions",
                    "tokenizer_encodes"):
        assert report[counter] == 0, counter
    assert "unconsumed historical object" in report["reason"]
    assert "inert for execution" in report["reason"]


# ---------------------------------------------------------------------------
# 10.12  Nothing here touches a model, a checkpoint, a GPU or the live gate
# ---------------------------------------------------------------------------

#: Built by concatenation so this module never literally contains the tokens it
#: forbids. A scanner that trips on its own scanner is a vacuous scanner.
_FORBIDDEN_LIBRARY_TOKENS = (
    "import " + "torch",
    "import " + "transformers",
    "import " + "tokenizers",
    "from " + "transformers",
    "Auto" + "Tokenizer",
    "Auto" + "Model",
)

_FORBIDDEN_OPERATION_TOKENS = _FORBIDDEN_LIBRARY_TOKENS + (
    "snapshot_" + "download",
    "from_" + "pretrained",
    "torch." + "cuda",
    "device" + "_count()",
)


def test_no_generation_2_module_imports_a_model_or_tokenizer_library():
    scanned = 0
    for name in sorted(os.listdir(P0_R1_DIR)):
        if not name.endswith(".py"):
            continue
        scanned += 1
        source = _text(os.path.join(P0_R1_DIR, name))
        for token in _FORBIDDEN_LIBRARY_TOKENS:
            assert token not in source, "%s names %s" % (name, token)
    assert scanned >= len(LOCK.GENERATION_2_CODE_PATHS) // 2, \
        "the scan must actually reach the generation-2 modules"

    # The v2 executor is deliberately outside this namespace, and the guard
    # above would be vacuous if it silently skipped it.
    executor = os.path.join(P0_R1_DIR, "execution",
                            "p0_r1_model_execution_v2.py")
    assert os.path.exists(executor)


def test_this_module_performs_no_model_checkpoint_gpu_or_live_gate_operation():
    source = _text(os.path.abspath(__file__))
    for token in _FORBIDDEN_OPERATION_TOKENS:
        assert token not in source, token
    # The live gate is never called: only the transport helper is exercised.
    # These tokens are assembled, never written, so this scan cannot trip on
    # its own source text.
    for token in ("GATE." + "gate_run_v2(", "GATE." + "run(",
                  "RUNNER." + "_load_executor("):
        assert token not in source, token
    # No Azure control-plane mutation is ever issued from a test.
    for token in ("az containerapp job " + "start", "az acr " + "build",
                  "az containerapp job " + "create"):
        assert token not in source, token


def test_the_image_build_runs_only_model_free_checks():
    dockerfile = _text(os.path.join(CONTAINER_DIR,
                                    "Dockerfile.study3-p0-r1-v2"))
    build_steps = [line for line in dockerfile.splitlines()
                   if line.startswith("RUN ")]
    joined = "\n".join(build_steps)
    for token in ("p0_r1_replay_gate", "p0_r1_model_runner") \
            + _FORBIDDEN_OPERATION_TOKENS:
        assert token not in joined, token
    assert "--self-check" in dockerfile
    assert "p0_r1_image_manifest_v2.py" in dockerfile


def test_the_canary_entry_point_is_model_free_and_consumes_nothing():
    canary = _text(os.path.join(CONTAINER_DIR,
                                "p0_r1_transport_canary_v2.sh"))
    assert "TOKENIZER_CONSTRUCTIONS=0" in canary
    assert "MODEL_OPERATIONS=0" in canary
    assert "GPU_WORKLOAD_ALLOCATED=false" in canary
    assert "ONE_SHOT_ENVELOPE_CONSUMED=false" in canary
    assert "REPLAY_GATE_RUN=false" in canary
    assert "p0_r1_replay_gate" not in canary
    assert "p0_r1_model_runner" not in canary


def test_the_v2_gate_imports_every_scientific_decision_unchanged():
    """No scoring rule, acceptance condition or terminal state is restated."""
    import p0_r1_replay_gate as GEN1
    assert GATE.SUCCESSOR_AUTHORIZATION is GEN1.SUCCESSOR_AUTHORIZATION
    assert GATE.STATE_AFTER_REPLAY_PASS == GEN1.STATE_AFTER_REPLAY_PASS
    assert GATE.STATE_REPLAY_DEFECT == GEN1.STATE_REPLAY_DEFECT
    assert GATE.ROLES == GEN1.ROLES
    identity = GATE.implementation_identity()
    assert identity["scientific_logic_is_imported_unchanged_from"] \
        == "studies/study3/pilot/p0_r1/p0_r1_replay_gate.py"


def test_the_partial_result_state_is_new_not_a_reinterpretation():
    import p0_r1_model_runner as GEN1
    assert RUNNER.STATE_STOPPED_WITH_PARTIAL_RESULT == JOURNAL.STATE_PARTIAL
    existing = {value for name, value in vars(GEN1).items()
                if name.startswith("STATE_")}
    assert RUNNER.STATE_STOPPED_WITH_PARTIAL_RESULT not in existing
    assert RUNNER.STATE_COMPLETE == GEN1.STATE_COMPLETE
