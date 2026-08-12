"""The Study 3 P0-R1 execution lock.

Authority: ``studies/study3/prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md``
section 7, over the operative
``studies/study3/prompts/study3_v0_6_p0_r1_authority.md``.

The lock is the single object that binds *what may run* to *exactly which bytes*.
It exists because the registration published an execution path whose image digest
was ``null``: a replay gate cannot legally bind itself to an image that had not
been built, and a model pilot cannot legally start from a prose log line.

Two commits are deliberately distinct, and the distinction is the point.

``executable_code_commit``
    the commit whose bytes the image was built from. The image digest is a
    function of these bytes, so this commit cannot itself contain the digest.

``ready_commit``
    the later commit that carries this lock. It contains the digest precisely
    because it comes after the build. Section 7 forbids pretending that a digest
    can be embedded in the same image whose digest it defines.

Between them, section 7 requires that **no executable byte changes**. That is not
a promise here, it is a check: :func:`verify_executable_bytes` recomputes every
bound code blob from the working tree and fails closed on any difference. If an
executable byte does change, the unexecuted image is discarded and rebuilt from
the new code commit before any measurement, which is pre-observation build
iteration rather than a replay or model retry.

This module performs zero tokenizer, checkpoint, model and GPU operations. It
never imports ``torch``, ``transformers`` or ``tokenizers``.
"""

import argparse
import hashlib
import json
import os
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))

sys.path.insert(0, P0_R1_DIR)

import p0_r1_factorization as FACT  # noqa: E402
from p0_r1_counters import CAPS, SMOKE_EXACT, ZERO_BEFORE_EXECUTION  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-execution-lock-v1"

LOCK_PATH = "studies/study3/pilot/p0_r1/p0_r1_execution_lock.json"
LOCK_SCHEMA_PATH = "studies/study3/pilot/p0_r1/p0_r1_execution_lock.schema.json"

#: The operative registration authority. Unchanged by the supplement.
REGISTRATION_AUTHORITY = {
    "path": "studies/study3/prompts/study3_v0_6_p0_r1_authority.md",
    "bytes": 19632,
    "sha256": "f72292e75ebf128e90c5cd73588786afa11d9f156f37392a9a9200845ddc19d2",
    "role": "the operative P0-R1 scientific and operational boundary",
}

#: The pre-replay execution-completion supplement that authorized this lock.
SUPPLEMENTAL_AUTHORITY = {
    "path": ("studies/study3/prompts/"
             "study3_p0_r1_pre_replay_execution_completion_authority_rev2.md"),
    "bytes": 23486,
    "sha256": "ffe75ba42c023e959f3beb23927604c3ae72c07fb4b25be346f504c8ea2930de",
    "role": ("the model-free execution-completion supplement; it corrects "
             "pre-replay implementation and sequencing defects and changes no "
             "scoring rule, corpus, allocation, cap or claim boundary"),
}

#: The commit that published the P0-R1 registration this lock completes.
REGISTRATION_COMMIT = "167d3067d7d9a2866999a51ec49c3c57c1d31546"
REGISTRATION_TREE = "f7166f0441780bf0d034eb88a03c0d61e9049a2a"

#: Every executable byte the lock binds. A change to any of these invalidates the
#: image and requires a rebuild before any measurement.
EXECUTABLE_CODE_PATHS = (
    "studies/study3/pilot/p0_r1/p0_r1_counters.py",
    "studies/study3/pilot/p0_r1/p0_r1_eligibility.py",
    "studies/study3/pilot/p0_r1/p0_r1_execution_lock.py",
    "studies/study3/pilot/p0_r1/p0_r1_factorization.py",
    "studies/study3/pilot/p0_r1/p0_r1_model_runner.py",
    "studies/study3/pilot/p0_r1/execution/p0_r1_model_execution.py",
    "studies/study3/pilot/p0_r1/p0_r1_protocol.py",
    "studies/study3/pilot/p0_r1/p0_r1_replay_gate.py",
    "studies/study3/pilot/p0_r1/p0_r1_schemas.py",
    "studies/study3/pilot/p0_r1/p0_r1_summarize.py",
    "studies/study3/pilot/p0_r1/p0_r1_validate.py",
    "studies/study3/pilot/p0_r1/container/Dockerfile.study3-p0-r1",
    "studies/study3/pilot/p0_r1/container/p0_r1_acr_task.yaml",
    "studies/study3/pilot/p0_r1/container/p0_r1_checkout.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_gpu_job.yaml",
    "studies/study3/pilot/p0_r1/container/p0_r1_image_manifest.py",
    "studies/study3/pilot/p0_r1/container/p0_r1_launch_gpu_pilot.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_model_pilot.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_replay.sh",
    "studies/study3/pilot/p0_r1/container/requirements-study3-p0-r1.txt",
)

#: The three pinned roles. Identical to the registration; not widened here.
ROLE_IDENTITIES = {
    "RT": {
        "repository": "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        "revision": "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562",
    },
    "RL": {
        "repository": "Qwen/Qwen2.5-Math-1.5B",
        "revision": "4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2",
    },
    "RI": {
        "repository": "Qwen/Qwen2.5-Math-1.5B-Instruct",
        "revision": "aafeb0fc6f22cbf0eaeed126eff8be45b0360a35",
    },
}

IMAGE_REPOSITORY = "j-space-observation-study3-p0-r1"
REGISTRY = "acrjspaceobssea0708231738.azurecr.io"
BASE_IMAGE = "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"
BASE_IMAGE_DIGEST = (
    "sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126")

#: The only state transition this lock permits, in order.
STATE_TRANSITION = (
    "STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE",
    "STUDY3_P0_R1_REPLAY_GATE_PASSED_AWAITING_MODEL_PILOT",
)

STATE_READY = STATE_TRANSITION[0]
STATE_REPLAY_PASSED = STATE_TRANSITION[1]

_DIGEST_PREFIX = "sha256:"
_DIGEST_LENGTH = len(_DIGEST_PREFIX) + 64


class LockDefect(Exception):
    """A fail-closed execution-lock stop. Nothing runs past one of these."""


def _read(repo_relative_path, root=None):
    path = os.path.join(root or REPO_ROOT, *repo_relative_path.split("/"))
    if not os.path.exists(path):
        raise LockDefect("the bound path %s is missing" % repo_relative_path)
    with open(path, "rb") as handle:
        return handle.read()


def blob_identity(repo_relative_path, root=None):
    raw = _read(repo_relative_path, root=root)
    return {
        "path": repo_relative_path,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def executable_code_blobs(root=None):
    """The identity of every executable byte the lock binds."""
    return [blob_identity(path, root=root) for path in EXECUTABLE_CODE_PATHS]


def dependency_lock_identity(root=None):
    return blob_identity(
        "studies/study3/pilot/p0_r1/container/requirements-study3-p0-r1.txt",
        root=root)


def _validate_digest(digest, label):
    if not isinstance(digest, str) or not digest.startswith(_DIGEST_PREFIX) \
            or len(digest) != _DIGEST_LENGTH:
        raise LockDefect(
            "%s must be an immutable sha256 manifest digest, not %r; a tag is "
            "never sufficient" % (label, digest))
    body = digest[len(_DIGEST_PREFIX):]
    if any(character not in "0123456789abcdef" for character in body):
        raise LockDefect("%s is not a lowercase hexadecimal digest" % label)
    return digest


def _validate_sha(value, label):
    if not isinstance(value, str) or len(value) != 40 \
            or any(character not in "0123456789abcdef" for character in value):
        raise LockDefect("%s must be a full 40-character git object ID" % label)
    return value


def build_lock(executable_code_commit, executable_code_tree, image_digest,
               ready_commit_parent, root=None):
    """Build the execution lock from live bytes and the resolved image digest.

    ``ready_commit_parent`` is the commit this lock is committed on top of. The
    ready commit itself cannot be named inside its own content, so the lock binds
    its parent and the relationship instead, and
    :func:`verify_ready_commit_relationship` checks it after publication.
    """
    _validate_sha(executable_code_commit, "executable_code_commit")
    _validate_sha(executable_code_tree, "executable_code_tree")
    _validate_sha(ready_commit_parent, "ready_commit_parent")
    _validate_digest(image_digest, "image_digest")

    authorities = []
    for entry in (REGISTRATION_AUTHORITY, SUPPLEMENTAL_AUTHORITY):
        identity = blob_identity(entry["path"], root=root)
        if identity["bytes"] != entry["bytes"] \
                or identity["sha256"] != entry["sha256"]:
            raise LockDefect(
                "%s does not reproduce its registered identity; the operative "
                "authority may never be edited" % entry["path"])
        record = dict(identity)
        record["role"] = entry["role"]
        authorities.append(record)

    zero = {name: 0 for name in ZERO_BEFORE_EXECUTION}

    return {
        "schema_version": SCHEMA_VERSION,
        "document_class": "study3_p0_r1_execution_lock",
        "stage": "P0-R1",
        "state": STATE_READY,
        "authorities": authorities,
        "registration": {
            "commit": REGISTRATION_COMMIT,
            "tree": REGISTRATION_TREE,
            "state": "STUDY3_P0_R1_REGISTERED_AWAITING_REPLAY_GATE",
        },
        "executable_code": {
            "commit": executable_code_commit,
            "tree": executable_code_tree,
            "blobs": executable_code_blobs(root=root),
            "no_executable_byte_may_change_after_the_image_build": True,
        },
        "ready_commit_relationship": {
            "parent": ready_commit_parent,
            "rule": (
                "the ready commit carries this lock and is a strict descendant "
                "of the executable code commit; the image digest is a function "
                "of the executable code commit, so it cannot be embedded in the "
                "image whose digest it defines"),
            "executable_code_commit_is_an_ancestor_of_the_ready_commit": True,
        },
        "image": {
            "registry": REGISTRY,
            "repository": IMAGE_REPOSITORY,
            "digest": image_digest,
            "reference": "%s/%s@%s" % (REGISTRY, IMAGE_REPOSITORY, image_digest),
            "base_image": BASE_IMAGE,
            "base_image_digest": BASE_IMAGE_DIGEST,
            "built_from_commit": executable_code_commit,
            "bound_by_digest_never_by_tag": True,
            "contains_no_model_weights": True,
            "build_performed_no_replay_gate_tokenizer_checkpoint_or_gpu_operation":
                True,
        },
        "dependency_lock": dependency_lock_identity(root=root),
        "immutable_sources": FACT.verify_immutable_sources(root=root),
        "roles": {
            role: dict(ROLE_IDENTITIES[role])
            for role in sorted(ROLE_IDENTITIES)
        },
        "caps": dict(CAPS),
        "smoke_exact_allocation": dict(SMOKE_EXACT),
        "counters_before_execution": zero,
        "state_transition": list(STATE_TRANSITION),
        "legal_status": {
            "formal_execution_authorized": False,
            "p0_r1_pilot_execution_authorized": True,
            "p0_r1_pilot_execution_consumed": False,
            "draft_v0_6_frozen": False,
            "draft_v0_6_reviewed": False,
            "interface_selected": None,
            "positive_reference": None,
            "rp_wrapper": None,
            "od2": "UNRESOLVED_BLOCKING_OPERATOR_DECISION",
            "ur22": "UNRESOLVED",
            "evidence_ledger_last_row": "EV-0016",
        },
        "claim_boundary": (
            "a methods-feasibility continuation. It selects no interface, sets "
            "no threshold, passes no formal gate, answers no research question, "
            "resolves neither OD2 nor UR-22, freezes nothing and produces no "
            "evidence-ledger row."),
        "permitted_sequence": [
            "the replay gate runs first, from a clean checkout of the ready "
            "commit, inside the image bound by digest above",
            "only a replay pass authorizes the single bounded GPU model pilot",
            "a replay failure publishes the registered stop and performs no "
            "model operation",
        ],
    }


def verify_executable_bytes(lock, root=None):
    """Recompute every bound executable blob. Section 7's no-drift check."""
    findings = []
    bound = {entry["path"]: entry for entry in lock["executable_code"]["blobs"]}
    if sorted(bound) != sorted(EXECUTABLE_CODE_PATHS):
        findings.append(
            "the lock binds a different executable path set than the registered "
            "one; bound=%s registered=%s"
            % (sorted(bound), sorted(EXECUTABLE_CODE_PATHS)))
        return findings
    for path in EXECUTABLE_CODE_PATHS:
        live = blob_identity(path, root=root)
        if live["sha256"] != bound[path]["sha256"] \
                or live["bytes"] != bound[path]["bytes"]:
            findings.append(
                "executable byte drift in %s: the lock binds %d bytes / %s but "
                "the checkout carries %d bytes / %s. The unexecuted image must "
                "be discarded and rebuilt from the new code commit before any "
                "measurement."
                % (path, bound[path]["bytes"], bound[path]["sha256"],
                   live["bytes"], live["sha256"]))
    return findings


def validate_lock(lock, root=None):
    """Fail closed on any structurally or scientifically invalid lock."""
    if not isinstance(lock, dict):
        raise LockDefect("an execution lock must be a mapping")
    if lock.get("schema_version") != SCHEMA_VERSION:
        raise LockDefect(
            "unknown execution-lock schema %r" % lock.get("schema_version"))
    if lock.get("state") != STATE_READY:
        raise LockDefect(
            "the execution lock records state %r, not the registered ready "
            "state %r" % (lock.get("state"), STATE_READY))
    if list(lock.get("state_transition", [])) != list(STATE_TRANSITION):
        raise LockDefect(
            "the execution lock permits a transition other than the registered "
            "replay-then-model sequence")

    _validate_digest(lock.get("image", {}).get("digest"), "image.digest")
    _validate_digest(lock.get("image", {}).get("base_image_digest"),
                     "image.base_image_digest")
    _validate_sha(lock.get("executable_code", {}).get("commit"),
                  "executable_code.commit")
    _validate_sha(lock.get("executable_code", {}).get("tree"),
                  "executable_code.tree")

    if lock["image"].get("built_from_commit") != lock["executable_code"]["commit"]:
        raise LockDefect(
            "the image was not built from the bound executable code commit")

    legal = lock.get("legal_status", {})
    if legal.get("formal_execution_authorized") is not False:
        raise LockDefect("formal_execution_authorized must remain false")
    if legal.get("p0_r1_pilot_execution_authorized") is not True:
        raise LockDefect(
            "the execution lock must carry the narrow "
            "p0_r1_pilot_execution_authorized flag")
    if legal.get("p0_r1_pilot_execution_consumed") is not False:
        raise LockDefect(
            "the execution lock is already consumed; the P0-R1 envelope is "
            "one-shot and is never re-armed")
    if legal.get("evidence_ledger_last_row") != "EV-0016":
        raise LockDefect("the evidence ledger must still end at EV-0016")
    for item in ("interface_selected", "positive_reference", "rp_wrapper"):
        if legal.get(item) is not None:
            raise LockDefect("%s must remain null" % item)

    counters = lock.get("counters_before_execution", {})
    if sorted(counters) != sorted(ZERO_BEFORE_EXECUTION):
        raise LockDefect(
            "the execution lock does not carry the registered counter set")
    for name, value in counters.items():
        if value != 0:
            raise LockDefect(
                "counter %s is %r before execution; every P0-R1 counter is zero "
                "until the successor session runs" % (name, value))

    if dict(lock.get("caps", {})) != dict(CAPS):
        raise LockDefect(
            "the execution lock caps differ from the registered caps; no cap is "
            "widened by the execution-completion supplement")
    if dict(lock.get("smoke_exact_allocation", {})) != dict(SMOKE_EXACT):
        raise LockDefect(
            "the execution lock smoke allocation differs from the registered "
            "exact smoke allocation")

    if {role: dict(body) for role, body in lock.get("roles", {}).items()} != \
            {role: dict(ROLE_IDENTITIES[role]) for role in ROLE_IDENTITIES}:
        raise LockDefect(
            "the execution lock pins a different role identity or revision set")

    registered = {
        path: body for path, body in FACT.IMMUTABLE_SOURCES.items()
    }
    for entry in lock.get("immutable_sources", []):
        expected = registered.get(entry.get("path"))
        if expected is None:
            raise LockDefect(
                "%s is not a registered immutable source" % entry.get("path"))
        if entry.get("sha256") != expected["sha256"] \
                or entry.get("bytes") != expected["bytes"]:
            raise LockDefect(
                "the execution lock binds a different identity for %s than the "
                "registered immutable source" % entry["path"])
    if len(lock.get("immutable_sources", [])) != len(registered):
        raise LockDefect(
            "the execution lock does not bind every registered immutable source")

    findings = verify_executable_bytes(lock, root=root)
    if findings:
        raise LockDefect("; ".join(findings))
    return True


def load_lock(root=None):
    raw = _read(LOCK_PATH, root=root)
    return json.loads(raw.decode("utf-8"))


def lock_identity(root=None):
    return blob_identity(LOCK_PATH, root=root)


def verify_binding(lock, commit=None, tree=None, image_digest=None, root=None):
    """Verify the running checkout and image against the lock. Fail closed."""
    validate_lock(lock, root=root)
    findings = []
    if image_digest is not None and image_digest != lock["image"]["digest"]:
        findings.append(
            "the running image digest %s is not the locked digest %s"
            % (image_digest, lock["image"]["digest"]))
    if commit is not None and commit != lock["executable_code"]["commit"]:
        # The ready commit is a descendant, so an exact match is only required
        # when the caller states it is running the executable code commit.
        findings.append(
            "the running commit %s is not the locked executable code commit %s"
            % (commit, lock["executable_code"]["commit"]))
    if tree is not None and tree != lock["executable_code"]["tree"]:
        findings.append(
            "the running tree %s is not the locked executable code tree %s"
            % (tree, lock["executable_code"]["tree"]))
    if findings:
        raise LockDefect("; ".join(findings))
    return True


LOCK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://j-space-observation/study3/p0_r1_execution_lock.schema.json",
    "title": "Study 3 P0-R1 execution lock",
    "type": "object",
    "required": [
        "schema_version", "document_class", "stage", "state", "authorities",
        "registration", "executable_code", "ready_commit_relationship", "image",
        "dependency_lock", "immutable_sources", "roles", "caps",
        "smoke_exact_allocation", "counters_before_execution",
        "state_transition", "legal_status", "claim_boundary",
        "permitted_sequence",
    ],
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION},
        "document_class": {"const": "study3_p0_r1_execution_lock"},
        "stage": {"const": "P0-R1"},
        "state": {"const": STATE_READY},
        "authorities": {"type": "array"},
        "registration": {"type": "object"},
        "executable_code": {
            "type": "object",
            "required": ["commit", "tree", "blobs"],
        },
        "ready_commit_relationship": {"type": "object"},
        "image": {
            "type": "object",
            "required": ["registry", "repository", "digest", "reference",
                         "base_image", "base_image_digest", "built_from_commit"],
        },
        "dependency_lock": {"type": "object"},
        "immutable_sources": {"type": "array"},
        "roles": {"type": "object"},
        "caps": {"type": "object"},
        "smoke_exact_allocation": {"type": "object"},
        "counters_before_execution": {"type": "object"},
        "state_transition": {"type": "array"},
        "legal_status": {"type": "object"},
        "claim_boundary": {"type": "string"},
        "permitted_sequence": {"type": "array"},
    },
}


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--emit", action="store_true",
                       help="write the execution lock and its schema")
    group.add_argument("--check", action="store_true",
                       help="verify the committed lock against live bytes")
    parser.add_argument("--executable-code-commit")
    parser.add_argument("--executable-code-tree")
    parser.add_argument("--image-digest")
    parser.add_argument("--ready-commit-parent")
    args = parser.parse_args(argv)

    if args.emit:
        missing = [name for name, value in (
            ("--executable-code-commit", args.executable_code_commit),
            ("--executable-code-tree", args.executable_code_tree),
            ("--image-digest", args.image_digest),
            ("--ready-commit-parent", args.ready_commit_parent),
        ) if not value]
        if missing:
            print("REFUSED: the execution lock requires %s" % ", ".join(missing))
            return 2
        try:
            lock = build_lock(
                args.executable_code_commit, args.executable_code_tree,
                args.image_digest, args.ready_commit_parent)
            validate_lock(lock)
        except (LockDefect, FACT.FactorizationDefect) as exc:
            print("EXECUTION LOCK DEFECT: %s" % exc)
            return 2
        with open(os.path.join(REPO_ROOT, *LOCK_PATH.split("/")), "wb") as handle:
            handle.write(dumps(lock).encode("utf-8"))
        with open(os.path.join(REPO_ROOT, *LOCK_SCHEMA_PATH.split("/")),
                  "wb") as handle:
            handle.write(dumps(LOCK_SCHEMA).encode("utf-8"))
        print("wrote %s" % LOCK_PATH)
        print("wrote %s" % LOCK_SCHEMA_PATH)
        return 0

    try:
        lock = load_lock()
        validate_lock(lock)
    except (LockDefect, FACT.FactorizationDefect) as exc:
        print("EXECUTION LOCK CHECK FAILED: %s" % exc)
        return 1
    print("execution lock: OK")
    print("  image digest          : %s" % lock["image"]["digest"])
    print("  executable code commit: %s" % lock["executable_code"]["commit"])
    print("  bound executable blobs: %d" % len(lock["executable_code"]["blobs"]))
    print("  counters before run   : all zero")
    return 0


if __name__ == "__main__":
    sys.exit(main())
