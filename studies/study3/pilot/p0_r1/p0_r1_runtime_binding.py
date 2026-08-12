"""Study 3 P0-R1 generation-2 standalone runtime binding and launch guard.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
section 5.

Generation 1 could not have run. Its Container Apps job command was
``/workspace/p0_r1_model_pilot.sh`` while the image carried that script only
under ``/workspace/studies/study3/pilot/p0_r1/container/``; its entry point
defaulted ``SRC`` to ``/workspace/src``, which exists only when the ACR task
mounts a checkout, and the GPU job has no such mount; and the final execution
lock necessarily postdated the image digest, so the executor called
``load_lock`` against bytes the image could not contain.

This module fixes all three by making the standalone layout a value that the
Dockerfile, the entry points, the launcher, the tests and the handoff all read
from one place, and by turning the lock and the replay receipt into explicit,
size-checked, hash-checked runtime injections rather than pretended image
content.

It also owns the pre-start launch guard. Every refusal the authority names
happens here, in production code, **before** any ``az containerapp job create``,
``update`` or ``start`` can be reached.

This module performs zero tokenizer, checkpoint, model and GPU operations.
"""

import argparse
import base64
import binascii
import hashlib
import json
import os
import sys

#: The one canonical standalone runtime root. The GPU job never depends on the
#: ACR task's ``/workspace`` source mount, so the immutable source lives at a
#: path no context upload can shadow.
STANDALONE_SRC = "/opt/jspace/src"

#: Entry points are installed at stable absolute paths as well as living inside
#: the source tree, so a job command is a real file rather than a hope.
ENTRYPOINT_DIR = "/usr/local/bin"
MODEL_PILOT_ENTRYPOINT = ENTRYPOINT_DIR + "/p0_r1_model_pilot_v2.sh"
REPLAY_ENTRYPOINT = ENTRYPOINT_DIR + "/p0_r1_replay_v2.sh"
CANARY_ENTRYPOINT = ENTRYPOINT_DIR + "/p0_r1_transport_canary_v2.sh"
STANDALONE_ENTRYPOINTS = (MODEL_PILOT_ENTRYPOINT, REPLAY_ENTRYPOINT,
                          CANARY_ENTRYPOINT)

#: The writable runtime namespace. Nothing outside it is ever written.
RUNTIME_ROOT = "/workspace/runtime"
RESULTS_DIR = RUNTIME_ROOT + "/results"
INJECTION_DIR = RUNTIME_ROOT + "/injected"

#: The relative paths that must exist under the standalone source root for the
#: image to be able to run anything at all.
REQUIRED_SOURCE_PATHS = (
    "studies/study3/pilot/p0_r1/p0_r1_execution_lock.py",
    "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.py",
    "studies/study3/pilot/p0_r1/p0_r1_factorization.py",
    "studies/study3/pilot/p0_r1/p0_r1_model_runner.py",
    "studies/study3/pilot/p0_r1/p0_r1_model_runner_v2.py",
    "studies/study3/pilot/p0_r1/p0_r1_replay_gate.py",
    "studies/study3/pilot/p0_r1/p0_r1_replay_gate_v2.py",
    "studies/study3/pilot/p0_r1/p0_r1_transport.py",
    "studies/study3/pilot/p0_r1/p0_r1_blob_transport.py",
    "studies/study3/pilot/p0_r1/p0_r1_journal.py",
    "studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py",
    "studies/study3/pilot/p0_r1/execution/p0_r1_model_execution_v2.py",
    "studies/study3/pilot/p0/corpus/p0_corpus.json",
    "studies/study3/prompts/study3_v0_6_p0_r1_authority.md",
    "studies/study3/prompts/"
    "study3_p0_r1_pre_replay_execution_completion_authority_rev2.md",
    "studies/study3/prompts/"
    "study3_p0_r1_post_ready_transport_exception_safety_authority.md",
)

#: Bytes that must never be inside the image.
FORBIDDEN_IMAGE_CONTENT = (
    "studies/study3/pilot/p0_r1/results",
    "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json",
)

INJECTION_VERSION = "study3-p0-r1-runtime-injection-v2"
INJECTION_LOCK_ENV = "P0_R1_LOCK_V2_B64"
INJECTION_RECEIPT_ENV = "P0_R1_REPLAY_RECEIPT_B64"

#: A conservative ceiling for environment-carried injection. Above it the
#: launcher must use the immutable private-Blob object route instead of
#: silently truncating.
MAX_INJECTION_PAYLOAD_BYTES = 262144

INJECTED_LOCK_NAME = "p0_r1_execution_lock_v2.json"
INJECTED_RECEIPT_NAME = "p0_r1_replay_receipt.json"

JOB_NAME = "job-jspace-study3-p0-r1-pilot-g2"

REPLAY_RECEIPT_SCHEMAS = (
    "study3-p0-r1-replay-gate-receipt-v2",
)

REPLAY_PASS_STATE = "STUDY3_P0_R1_REPLAY_GATE_PASSED_AWAITING_MODEL_PILOT"

#: Every replay counter that must be exactly zero in the consumed receipt.
REPLAY_ZERO_COUNTERS = (
    "tokenizer_constructions",
    "tokenizer_encodes",
    "checkpoint_downloads",
    "model_weight_loads",
    "model_operations_performed",
)


class RuntimeBindingDefect(Exception):
    """A fail-closed runtime or launch stop. Nothing is created past one."""


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Standalone layout
# ---------------------------------------------------------------------------

def verify_standalone_layout(src=None, entrypoints=None, exists=None,
                             is_executable=None):
    """Prove the standalone image can actually invoke what the job commands.

    ``exists`` and ``is_executable`` are injectable so the check is exercised
    against fixture layouts in CPU-only tests as well as against a real image.
    """
    src = src or STANDALONE_SRC
    entrypoints = tuple(entrypoints or STANDALONE_ENTRYPOINTS)
    exists = exists or os.path.exists
    if is_executable is None:
        def is_executable(path):
            return os.access(path, os.X_OK)

    findings = []
    if not exists(src):
        findings.append(
            "the standalone source root %s does not exist; the GPU job has no "
            "ACR checkout to fall back on" % src)
    for relative in REQUIRED_SOURCE_PATHS:
        candidate = src.rstrip("/") + "/" + relative
        if not exists(candidate):
            findings.append("the standalone source root is missing %s"
                            % relative)
    for entrypoint in entrypoints:
        if not exists(entrypoint):
            findings.append(
                "the job command %s does not exist inside the image" % entrypoint)
        elif not is_executable(entrypoint):
            findings.append("%s is not executable inside the image" % entrypoint)
    for forbidden in FORBIDDEN_IMAGE_CONTENT:
        candidate = src.rstrip("/") + "/" + forbidden
        if exists(candidate):
            findings.append(
                "%s is inside the image; the image carries no result and no "
                "outcome-conditioned byte" % forbidden)
    if findings:
        raise RuntimeBindingDefect("; ".join(findings))
    return {
        "standalone_source_root": src,
        "entrypoints": list(entrypoints),
        "required_source_paths": len(REQUIRED_SOURCE_PATHS),
        "depends_on_the_acr_workspace_mount": False,
    }


# ---------------------------------------------------------------------------
# Lossless, size-checked runtime injection
# ---------------------------------------------------------------------------

def encode_injection(payload):
    """A lossless, size-checked, hash-checked encoding of exact bytes."""
    if not isinstance(payload, bytes):
        raise RuntimeBindingDefect("an injection payload must be raw bytes")
    if not payload:
        raise RuntimeBindingDefect("an empty injection payload is refused")
    if len(payload) > MAX_INJECTION_PAYLOAD_BYTES:
        raise RuntimeBindingDefect(
            "an injection payload of %d bytes exceeds the registered ceiling "
            "of %d; use the immutable private-Blob object route rather than "
            "truncating" % (len(payload), MAX_INJECTION_PAYLOAD_BYTES))
    return "%s|%d|%s|%s" % (INJECTION_VERSION, len(payload), _sha256(payload),
                            base64.b64encode(payload).decode("ascii"))


def decode_injection(encoded):
    """Reconstruct exact bytes, refusing any lossy or mismatched carrier."""
    if not isinstance(encoded, str) or not encoded:
        raise RuntimeBindingDefect("no injected payload was supplied")
    parts = encoded.strip().split("|")
    if len(parts) != 4:
        raise RuntimeBindingDefect("the injected payload is malformed")
    version, declared_bytes, declared_sha, body = parts
    if version != INJECTION_VERSION:
        raise RuntimeBindingDefect(
            "injection version %r is not the registered %r"
            % (version, INJECTION_VERSION))
    if not declared_bytes.isdigit():
        raise RuntimeBindingDefect("the injected byte count is not a number")
    try:
        payload = base64.b64decode(body.encode("ascii"), validate=True)
    except (binascii.Error, ValueError, UnicodeEncodeError):
        raise RuntimeBindingDefect(
            "the injected payload is not a lossless encoding")
    if len(payload) != int(declared_bytes):
        raise RuntimeBindingDefect(
            "the injected payload is %d bytes, not the declared %s"
            % (len(payload), declared_bytes))
    if _sha256(payload) != declared_sha:
        raise RuntimeBindingDefect(
            "the injected payload fails its declared sha256")
    return payload


def build_injection(lock_bytes, receipt_bytes):
    """The exact environment the launcher must set on the job."""
    return {
        INJECTION_LOCK_ENV: encode_injection(lock_bytes),
        INJECTION_RECEIPT_ENV: encode_injection(receipt_bytes),
    }


INJECTION_TARGETS = {
    "lock": (INJECTION_LOCK_ENV, INJECTED_LOCK_NAME),
    "receipt": (INJECTION_RECEIPT_ENV, INJECTED_RECEIPT_NAME),
}


def reconstruct_injection(environ=None, out_dir=None, required=None):
    """Rebuild the lock and receipt bytes in the writable runtime namespace.

    ``required`` selects which injections must be present. The replay stage
    reconstructs the lock alone, because the replay-pass receipt does not exist
    until the replay gate has produced it.
    """
    environ = os.environ if environ is None else environ
    out_dir = out_dir or INJECTION_DIR
    required = tuple(required or ("lock", "receipt"))
    unknown = [name for name in required if name not in INJECTION_TARGETS]
    if unknown:
        raise RuntimeBindingDefect(
            "unknown injection target(s) %s" % ", ".join(sorted(unknown)))
    os.makedirs(out_dir, exist_ok=True)
    written = {}
    for target in required:
        env_name, file_name = INJECTION_TARGETS[target]
        encoded = environ.get(env_name)
        if not encoded:
            raise RuntimeBindingDefect(
                "%s was not injected; the container reconstructs the exact "
                "lock and receipt bytes and never invents them" % env_name)
        payload = decode_injection(encoded)
        path = os.path.join(out_dir, file_name)
        with open(path, "wb") as handle:
            handle.write(payload)
        with open(path, "rb") as handle:
            if handle.read() != payload:
                raise RuntimeBindingDefect(
                    "%s did not read back exactly" % file_name)
        written[file_name] = {
            "path": path,
            "bytes": len(payload),
            "sha256": _sha256(payload),
        }
    return written


# ---------------------------------------------------------------------------
# The pre-start launch guard
# ---------------------------------------------------------------------------

def _require_mapping(document, label):
    if not isinstance(document, dict):
        raise RuntimeBindingDefect(
            "%s is not a document; a prose log line, a printed SHA-256 or a "
            "bare hash is never authorization" % label)
    return document


def validate_launch_inputs(lock, receipt, image_digest, ready_commit,
                           lock_bytes=None, receipt_bytes=None,
                           lock_module=None, root=None,
                           existing_executions=None):
    """Refuse every illegal launch before any Azure job command is reached.

    ``lock`` and ``receipt`` are the parsed documents; ``lock_bytes`` and
    ``receipt_bytes`` are their exact bytes, which are what the container
    actually receives. Returns the launch plan on acceptance.
    """
    findings = []
    _require_mapping(lock, "the execution lock")
    _require_mapping(receipt, "the replay-pass receipt")

    if lock_module is None:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import p0_r1_execution_lock_v2 as lock_module  # noqa: F401

    # 1. the lock must be the active, unconsumed generation-2 lock.
    try:
        lock_module.validate_lock(lock, root=root)
    except Exception as exc:  # LockDefect, surfaced as a launch refusal
        raise RuntimeBindingDefect(
            "the supplied execution lock is not a valid active generation-2 "
            "lock: %s" % exc)
    if lock.get("generation") != 2:
        findings.append(
            "the supplied lock is generation %r; generation 1 is superseded and "
            "inert and may never be launched" % lock.get("generation"))
    if lock.get("superseded") is True:
        findings.append("the supplied lock is itself superseded")

    # 2. the receipt must be a byte-valid pass receipt, not prose or a hash.
    if receipt.get("schema_version") not in REPLAY_RECEIPT_SCHEMAS:
        findings.append(
            "the replay receipt schema %r is not a registered generation-2 "
            "receipt schema" % receipt.get("schema_version"))
    if receipt.get("passed") is not True \
            or receipt.get("authorizes_model_pilot") is not True:
        findings.append(
            "the replay receipt does not record a pass; a replay failure "
            "authorizes no model operation")
    if receipt.get("state") != REPLAY_PASS_STATE:
        findings.append(
            "the replay receipt records state %r, not %r"
            % (receipt.get("state"), REPLAY_PASS_STATE))
    if not receipt.get("attempt_id"):
        findings.append("the replay receipt carries no attempt id")

    # 3. attempt agreement.
    if receipt.get("attempt_id") and lock.get("attempt_binding", {}).get(
            "attempt_id_rule") is None:
        findings.append("the lock does not register an attempt binding rule")

    # 4. the receipt and lock must bind the same image, code and authorities.
    for field, expected, label in (
            ("image_digest", lock.get("image", {}).get("digest"),
             "image digest"),
            ("executable_code_commit",
             lock.get("executable_code", {}).get("commit"),
             "executable code commit"),
            ("executable_code_tree",
             lock.get("executable_code", {}).get("tree"),
             "executable code tree"),
            ("ready_commit", ready_commit, "ready commit")):
        if receipt.get(field) != expected:
            findings.append(
                "the replay receipt %s %r does not agree with the launch %s %r"
                % (field, receipt.get(field), label, expected))

    if image_digest != lock.get("image", {}).get("digest"):
        findings.append(
            "the launch image digest %r is not the locked digest %r"
            % (image_digest, lock.get("image", {}).get("digest")))

    locked_ready = lock.get("ready_commit_relationship", {}).get("ready_commit")
    if locked_ready is not None and locked_ready != ready_commit:
        findings.append(
            "the ready commit %r is not the lock's ready commit %r"
            % (ready_commit, locked_ready))
    if not ready_commit or len(str(ready_commit)) != 40:
        findings.append(
            "the ready-commit argument is missing or is not a full git object "
            "id; it is validated, never ignored")

    for group, key in (("authorities", "authorities"),
                       ("corpus_and_p0_t", "corpus_and_p0_t")):
        expected = lock.get(group)
        observed = receipt.get(key)
        if expected is None:
            findings.append("the lock does not bind %s" % group)
        elif observed != expected:
            findings.append(
                "the replay receipt does not bind the locked %s" % group)

    locked_lock_identity = receipt.get("execution_lock", {})
    if lock_bytes is not None:
        actual = {"bytes": len(lock_bytes), "sha256": _sha256(lock_bytes)}
        if locked_lock_identity.get("sha256") != actual["sha256"] \
                or locked_lock_identity.get("bytes") != actual["bytes"]:
            findings.append(
                "the replay receipt was produced against a different execution "
                "lock than the one being injected; a superseded or swapped lock "
                "refuses")
    elif not locked_lock_identity.get("sha256"):
        findings.append(
            "the replay receipt does not identify the execution lock it ran "
            "against")

    # 5. every replay counter must be zero.
    for name in REPLAY_ZERO_COUNTERS:
        value = receipt.get(name)
        if value is None:
            findings.append(
                "the replay receipt does not carry %s; a missing counter is not "
                "a zero-operation proof" % name)
        elif value != 0:
            findings.append(
                "the replay receipt records %s=%r; the replay gate is "
                "replay-only" % (name, value))
    if receipt.get("gpu_allocated") is not False:
        findings.append("the replay receipt records a GPU allocation")

    # 6. the job may not already have a model-operating execution.
    if existing_executions:
        findings.append(
            "%s already has %d execution(s); the P0-R1 model pilot is one-shot "
            "and no execution is ever deleted to make the count appear zero"
            % (JOB_NAME, len(existing_executions)))

    if receipt_bytes is not None:
        try:
            reparsed = json.loads(receipt_bytes.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            findings.append("the injected receipt bytes are not valid JSON")
        else:
            if reparsed != receipt:
                findings.append(
                    "the injected receipt bytes are not the receipt that was "
                    "validated; only the exact recovered receipt may be "
                    "consumed")

    if findings:
        raise RuntimeBindingDefect("; ".join(findings))

    import p0_r1_blob_transport as BLOB
    return {
        "job_name": JOB_NAME,
        "image_reference": lock["image"]["reference"],
        "image_digest": image_digest,
        "ready_commit": ready_commit,
        "attempt_id": receipt["attempt_id"],
        "blob_prefix": BLOB.attempt_prefix(receipt["attempt_id"]),
        "entrypoint": MODEL_PILOT_ENTRYPOINT,
        "standalone_source_root": STANDALONE_SRC,
        "replica_retry_limit": 0,
        "parallelism": 1,
        "replica_completion_count": 1,
    }


def bound_identities(lock, receipt, ready_commit, execution_name=None,
                     blob_prefix=None):
    """The identity block every generation-2 result and receipt must carry."""
    return {
        "ready_commit": ready_commit,
        "executable_code_commit": lock["executable_code"]["commit"],
        "executable_code_tree": lock["executable_code"]["tree"],
        "execution_lock": lock.get("lock_identity_rule", "injected at runtime"),
        "execution_lock_sha256": receipt.get("execution_lock", {}).get("sha256"),
        "replay_attempt_id": receipt.get("attempt_id"),
        "image_digest": lock["image"]["digest"],
        "azure_job_execution_name": execution_name,
        "output_prefix": blob_prefix,
        "standalone_source_root": STANDALONE_SRC,
    }


def implementation_identity(root=None):
    path = os.path.abspath(__file__) if root is None else os.path.join(
        root, "studies", "study3", "pilot", "p0_r1", "p0_r1_runtime_binding.py")
    with open(path, "rb") as handle:
        raw = handle.read()
    return {
        "path": "studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py",
        "bytes": len(raw),
        "sha256": _sha256(raw),
        "standalone_source_root": STANDALONE_SRC,
        "entrypoints": list(STANDALONE_ENTRYPOINTS),
        "injection_version": INJECTION_VERSION,
        "job_name": JOB_NAME,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-layout", action="store_true")
    parser.add_argument("--reconstruct", action="store_true")
    parser.add_argument("--encode", action="store_true",
                        help="emit the injection payload for one file")
    parser.add_argument("--file")
    parser.add_argument("--require", action="append", default=None,
                        choices=sorted(INJECTION_TARGETS))
    parser.add_argument("--src")
    parser.add_argument("--out-dir")
    args = parser.parse_args(argv)

    try:
        if args.encode:
            if not args.file:
                print("--encode requires --file")
                return 2
            with open(args.file, "rb") as handle:
                sys.stdout.write(encode_injection(handle.read()))
            return 0
        if args.verify_layout:
            report = verify_standalone_layout(src=args.src)
            print("P0_R1_STANDALONE_LAYOUT_OK=1")
            for key in sorted(report):
                print("  %-32s %s" % (key, report[key]))
            return 0
        if args.reconstruct:
            written = reconstruct_injection(out_dir=args.out_dir,
                                            required=args.require)
            for name in sorted(written):
                print("INJECTED=%s BYTES=%d SHA256=%s"
                      % (name, written[name]["bytes"], written[name]["sha256"]))
            print("P0_R1_RUNTIME_INJECTION_COMPLETE=1")
            return 0
        parser.print_help()
        return 2
    except RuntimeBindingDefect as exc:
        print("RUNTIME BINDING REFUSED")
        print("  FAIL %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
