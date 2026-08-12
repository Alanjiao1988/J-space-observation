"""The Study 3 P0-R1 generation-2 execution lock.

Authority:
``studies/study3/prompts/study3_p0_r1_post_ready_transport_exception_safety_authority.md``
sections 9 and 11, over the operative
``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` and the rev-2
pre-replay execution-completion supplement.

The generation-1 lock is preserved exactly as published. It was never consumed
and it is now inert: the image it binds cannot run its own job command, cannot
find its own source root and cannot contain the lock its executor loads. This
generation-2 lock supersedes it and is the only lock a launcher may consume.

It binds strictly more than generation 1 did:

* all three authorities, by exact byte identity;
* the generation-1 lock's own identity, together with the explicit statement
  that it is unconsumed, superseded and not launchable;
* the new executable code commit and tree, and every generation-2 executable
  byte alongside every generation-1 executable byte;
* the new image manifest digest and its base image digest;
* the transport, journal and runtime-binding implementation identities, and the
  receipts of the model-free canaries that proved them;
* the frozen corpus and the immutable P0-T artifacts;
* the pinned role revisions, the unwidened caps and the zero counters;
* the single permitted replay-then-conditional-GPU sequence.

This module performs zero tokenizer, checkpoint, model and GPU operations.
"""

import argparse
import hashlib
import json
import os
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))

sys.path.insert(0, P0_R1_DIR)

import p0_r1_execution_lock as LOCK1  # noqa: E402
import p0_r1_factorization as FACT  # noqa: E402
from p0_r1_counters import CAPS, SMOKE_EXACT, ZERO_BEFORE_EXECUTION  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-execution-lock-v2"
GENERATION = 2

LOCK_PATH = "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json"
LOCK_SCHEMA_PATH = (
    "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.schema.json")

#: The operative registration authority. Unchanged by either supplement.
REGISTRATION_AUTHORITY = dict(LOCK1.REGISTRATION_AUTHORITY)

#: The rev-2 pre-replay execution-completion supplement.
SUPPLEMENTAL_AUTHORITY = dict(LOCK1.SUPPLEMENTAL_AUTHORITY)

#: The post-ready transport and exception-safety completion authority that
#: authorizes this generation.
POST_READY_AUTHORITY = {
    "path": ("studies/study3/prompts/"
             "study3_p0_r1_post_ready_transport_exception_safety_authority.md"),
    "bytes": 30706,
    "sha256": "5594e9728e8e4eb14635c34fb4895e65f2a8fa152ff2bffe76aec33a3ea84d18",
    "role": ("the model-free post-ready transport, runtime-binding, durable "
             "partial-result and exception-safety completion authority; it "
             "changes no scoring rule, corpus, allocation, cap, model or "
             "tokenizer identity, rendering, parser, statistic, claim "
             "boundary, role meaning, smoke criterion or terminal-state "
             "meaning"),
}

AUTHORITIES = (REGISTRATION_AUTHORITY, SUPPLEMENTAL_AUTHORITY,
               POST_READY_AUTHORITY)

#: The generation-1 lock, preserved and superseded.
GENERATION_1_LOCK = {
    "path": "studies/study3/pilot/p0_r1/p0_r1_execution_lock.json",
    "bytes": 10728,
    "sha256": "f0e0e6b609091adeb063893687659b0df3e919135c11b8e977575f15bec26c40",
}

GENERATION_1_IMAGE_DIGEST = (
    "sha256:7e2690feb6854a53f096d5b321e69fddebd2b744289c760e2fe74ed1ccec8176")

#: The generation-1 executable code commit, preserved for the supersession
#: record. The generation-2 image is built from a strict descendant of it.
GENERATION_1_EXECUTABLE_CODE_COMMIT = (
    "aad14c45e9681a34f382aa95c55ac875d2ca98ce")

#: The generation-2 executable bytes, in addition to every generation-1 path.
GENERATION_2_CODE_PATHS = (
    "studies/study3/pilot/p0_r1/p0_r1_blob_transport.py",
    "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.py",
    "studies/study3/pilot/p0_r1/p0_r1_journal.py",
    "studies/study3/pilot/p0_r1/p0_r1_model_runner_v2.py",
    "studies/study3/pilot/p0_r1/p0_r1_replay_gate_v2.py",
    "studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py",
    "studies/study3/pilot/p0_r1/p0_r1_transport.py",
    "studies/study3/pilot/p0_r1/execution/p0_r1_model_execution_v2.py",
    "studies/study3/pilot/p0_r1/container/Dockerfile.study3-p0-r1-v2",
    "studies/study3/pilot/p0_r1/container/p0_r1_acr_task_v2.yaml",
    "studies/study3/pilot/p0_r1/container/p0_r1_gpu_job_v2.yaml",
    "studies/study3/pilot/p0_r1/container/p0_r1_image_manifest_v2.py",
    "studies/study3/pilot/p0_r1/container/p0_r1_launch_gpu_pilot_v2.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_model_pilot_v2.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_no_accelerator_probe.py",
    "studies/study3/pilot/p0_r1/container/p0_r1_prestart_guard.py",
    "studies/study3/pilot/p0_r1/container/p0_r1_replay_v2.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_require_accelerator.py",
    "studies/study3/pilot/p0_r1/container/p0_r1_transport_canary_v2.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_verify_replay_receipt.py",
    "studies/study3/pilot/p0_r1/container/p0_r1_successor.sh",
    "studies/study3/pilot/p0_r1/container/"
    "requirements-study3-p0-r1-transport-v2.txt",
)

#: Every executable byte this lock binds: generation 1 unchanged, plus
#: generation 2.
EXECUTABLE_CODE_PATHS = tuple(sorted(
    tuple(LOCK1.EXECUTABLE_CODE_PATHS) + GENERATION_2_CODE_PATHS))

#: The implementation modules whose identity the transport and exception-safety
#: repairs live in. Bound separately so a handoff can name them directly.
IMPLEMENTATION_PATHS = (
    "studies/study3/pilot/p0_r1/p0_r1_transport.py",
    "studies/study3/pilot/p0_r1/p0_r1_blob_transport.py",
    "studies/study3/pilot/p0_r1/p0_r1_journal.py",
    "studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py",
)

ROLE_IDENTITIES = {role: dict(body)
                   for role, body in LOCK1.ROLE_IDENTITIES.items()}

IMAGE_REPOSITORY = LOCK1.IMAGE_REPOSITORY
REGISTRY = LOCK1.REGISTRY
BASE_IMAGE = LOCK1.BASE_IMAGE
BASE_IMAGE_DIGEST = LOCK1.BASE_IMAGE_DIGEST

STATE_TRANSITION = tuple(LOCK1.STATE_TRANSITION)
STATE_READY = LOCK1.STATE_READY
STATE_REPLAY_PASSED = LOCK1.STATE_REPLAY_PASSED

ATTEMPT_ID_RULE = (
    "the replay gate mints exactly one attempt id of the form "
    "gen2-<executable_code_commit[:12]>-<utc>; the model pilot consumes that "
    "same attempt id, writes under exactly that Blob prefix and refuses any "
    "receipt minted for a different attempt")

CANARY_NAMES = ("standalone_layout", "replay_transport", "private_blob")

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
    return [blob_identity(path, root=root) for path in EXECUTABLE_CODE_PATHS]


def _validate_digest(digest, label):
    if not isinstance(digest, str) or not digest.startswith(_DIGEST_PREFIX) \
            or len(digest) != _DIGEST_LENGTH:
        raise LockDefect(
            "%s must be an immutable sha256 manifest digest, not %r; a tag is "
            "never sufficient" % (label, digest))
    if any(character not in "0123456789abcdef"
           for character in digest[len(_DIGEST_PREFIX):]):
        raise LockDefect("%s is not a lowercase hexadecimal digest" % label)
    return digest


def _validate_sha(value, label):
    if not isinstance(value, str) or len(value) != 40 \
            or any(character not in "0123456789abcdef" for character in value):
        raise LockDefect("%s must be a full 40-character git object ID" % label)
    return value


def authority_records(root=None):
    records = []
    for entry in AUTHORITIES:
        identity = blob_identity(entry["path"], root=root)
        if identity["bytes"] != entry["bytes"] \
                or identity["sha256"] != entry["sha256"]:
            raise LockDefect(
                "%s does not reproduce its registered identity; an authority "
                "may never be edited" % entry["path"])
        record = dict(identity)
        record["role"] = entry["role"]
        records.append(record)
    return records


def generation_1_supersession(root=None):
    """The preserved, unconsumed, inert generation-1 record."""
    identity = blob_identity(GENERATION_1_LOCK["path"], root=root)
    if identity["sha256"] != GENERATION_1_LOCK["sha256"] \
            or identity["bytes"] != GENERATION_1_LOCK["bytes"]:
        raise LockDefect(
            "the generation-1 execution lock is not preserved byte-identically; "
            "a superseded historical object is never edited")
    record = dict(identity)
    record.update({
        "image_digest": GENERATION_1_IMAGE_DIGEST,
        "executable_code_commit": GENERATION_1_EXECUTABLE_CODE_COMMIT,
        "consumed": False,
        "executions": 0,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_allocations": 0,
        "superseded": True,
        "superseded_by": LOCK_PATH,
        "launchable": False,
        "reason": (
            "the generation-1 image could not have run: its job command "
            "/workspace/p0_r1_model_pilot.sh is not a path in the image, its "
            "entry point defaults SRC to the /workspace/src checkout mount that "
            "no GPU job provides, and the executor loads an execution lock the "
            "image cannot contain because the lock necessarily postdates the "
            "digest it binds. It remains an unconsumed historical object and is "
            "inert for execution."),
    })
    return record


def transport_identity(root=None):
    """The identity of every implementation module the repairs live in."""
    return [blob_identity(path, root=root) for path in IMPLEMENTATION_PATHS]


def build_lock(executable_code_commit, executable_code_tree, image_digest,
               ready_commit_parent, canary_receipts, root=None):
    """Build the generation-2 lock from live bytes and resolved identities."""
    _validate_sha(executable_code_commit, "executable_code_commit")
    _validate_sha(executable_code_tree, "executable_code_tree")
    _validate_sha(ready_commit_parent, "ready_commit_parent")
    _validate_digest(image_digest, "image_digest")

    if not isinstance(canary_receipts, dict):
        raise LockDefect("the canary receipts must be a mapping")
    missing = [name for name in CANARY_NAMES if name not in canary_receipts]
    if missing:
        raise LockDefect(
            "the generation-2 lock requires a receipt for every authorized "
            "model-free canary; missing %s" % ", ".join(sorted(missing)))
    for name, receipt in canary_receipts.items():
        if not isinstance(receipt, dict) or receipt.get("passed") is not True:
            raise LockDefect(
                "the %s canary receipt does not record a pass" % name)

    zero = {name: 0 for name in ZERO_BEFORE_EXECUTION}
    import p0_r1_runtime_binding as RUNTIME

    return {
        "schema_version": SCHEMA_VERSION,
        "document_class": "study3_p0_r1_execution_lock",
        "generation": GENERATION,
        "stage": "P0-R1",
        "state": STATE_READY,
        "superseded": False,
        "authorities": authority_records(root=root),
        "registration": {
            "commit": LOCK1.REGISTRATION_COMMIT,
            "tree": LOCK1.REGISTRATION_TREE,
            "state": "STUDY3_P0_R1_REGISTERED_AWAITING_REPLAY_GATE",
        },
        "generation_1": generation_1_supersession(root=root),
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
                "image whose digest it defines. The launcher therefore receives "
                "the ready commit as an explicit argument, injects this lock's "
                "exact bytes into the container, and the container validates "
                "both before any model library is loaded."),
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
            "contains_no_result_and_no_outcome_conditioned_byte": True,
            "build_performed_no_replay_gate_tokenizer_checkpoint_or_gpu_operation":
                True,
            "supersedes_digest": GENERATION_1_IMAGE_DIGEST,
        },
        "runtime_binding": {
            "standalone_source_root": RUNTIME.STANDALONE_SRC,
            "entrypoints": list(RUNTIME.STANDALONE_ENTRYPOINTS),
            "model_pilot_job_command": RUNTIME.MODEL_PILOT_ENTRYPOINT,
            "writable_runtime_root": RUNTIME.RUNTIME_ROOT,
            "job_name": RUNTIME.JOB_NAME,
            "depends_on_the_acr_workspace_mount": False,
            "injection_version": RUNTIME.INJECTION_VERSION,
            "lock_and_receipt_are_injected_as_exact_size_checked_bytes": True,
        },
        "transport": {
            "implementation": transport_identity(root=root),
            "canaries": {name: canary_receipts[name]
                         for name in sorted(canary_receipts)},
            "complete_byte_recovery_is_verified_before_any_pass_authorization":
                True,
            "artifacts_are_persisted_to_private_blob_under_managed_identity":
                True,
        },
        "dependency_lock": {
            "frozen_science": blob_identity(
                "studies/study3/pilot/p0_r1/container/"
                "requirements-study3-p0-r1.txt", root=root),
            "durable_transport": blob_identity(
                "studies/study3/pilot/p0_r1/container/"
                "requirements-study3-p0-r1-transport-v2.txt", root=root),
            "the_transport_closure_is_installed_under_the_science_set_as_a_"
            "constraint_file": True,
            "generation_2_moves_no_frozen_science_pin": True,
            "the_build_constructs_the_real_managed_identity_client": True,
        },
        "corpus_and_p0_t": FACT.verify_immutable_sources(root=root),
        "immutable_sources": FACT.verify_immutable_sources(root=root),
        "roles": {role: dict(ROLE_IDENTITIES[role])
                  for role in sorted(ROLE_IDENTITIES)},
        "caps": dict(CAPS),
        "smoke_exact_allocation": dict(SMOKE_EXACT),
        "counters_before_execution": zero,
        "state_transition": list(STATE_TRANSITION),
        "attempt_binding": {
            "attempt_id_rule": ATTEMPT_ID_RULE,
            "one_replay_attempt_authorizes_at_most_one_model_pilot": True,
        },
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
            "the replay gate runs first, CPU-only, inside the image bound by "
            "digest above, and emits its four exact artifacts through the "
            "verified complete-byte transport",
            "only a recovered, byte-complete replay pass receipt authorizes the "
            "single bounded GPU model pilot",
            "a replay failure publishes the registered stop and performs no "
            "model operation",
        ],
    }


def verify_executable_bytes(lock, root=None):
    findings = []
    bound = {entry["path"]: entry for entry in lock["executable_code"]["blobs"]}
    if sorted(bound) != sorted(EXECUTABLE_CODE_PATHS):
        findings.append(
            "the lock binds a different executable path set than the registered "
            "generation-2 set")
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
    """Fail closed on any structurally or scientifically invalid v2 lock."""
    if not isinstance(lock, dict):
        raise LockDefect("an execution lock must be a mapping")
    if lock.get("schema_version") != SCHEMA_VERSION:
        raise LockDefect(
            "unknown execution-lock schema %r" % lock.get("schema_version"))
    if lock.get("generation") != GENERATION:
        raise LockDefect(
            "this loader validates generation %d locks only" % GENERATION)
    if lock.get("superseded") is not False:
        raise LockDefect("a superseded lock is never launchable")
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

    if lock["image"].get("built_from_commit") \
            != lock["executable_code"]["commit"]:
        raise LockDefect(
            "the image was not built from the bound executable code commit")
    if lock["image"].get("digest") == GENERATION_1_IMAGE_DIGEST:
        raise LockDefect(
            "the generation-2 lock may not bind the superseded generation-1 "
            "image digest")

    bound_authorities = {entry.get("path"): entry
                         for entry in lock.get("authorities", [])}
    for entry in AUTHORITIES:
        observed = bound_authorities.get(entry["path"])
        if observed is None:
            raise LockDefect("the lock does not bind %s" % entry["path"])
        if observed.get("sha256") != entry["sha256"] \
                or observed.get("bytes") != entry["bytes"]:
            raise LockDefect(
                "the lock binds a different identity for %s than the "
                "registered authority" % entry["path"])
    if len(bound_authorities) != len(AUTHORITIES):
        raise LockDefect("the lock binds an unregistered authority")

    generation_1 = lock.get("generation_1", {})
    if generation_1.get("sha256") != GENERATION_1_LOCK["sha256"]:
        raise LockDefect(
            "the lock does not preserve the generation-1 lock identity")
    if generation_1.get("consumed") is not False \
            or generation_1.get("executions") != 0:
        raise LockDefect(
            "the generation-1 envelope is recorded as consumed; it was never "
            "consumed and is never re-armed")
    if generation_1.get("superseded") is not True \
            or generation_1.get("launchable") is not False:
        raise LockDefect(
            "the generation-1 lock must be recorded as superseded and not "
            "launchable")

    runtime = lock.get("runtime_binding", {})
    if runtime.get("depends_on_the_acr_workspace_mount") is not False:
        raise LockDefect(
            "the generation-2 runtime may not depend on the ACR checkout mount")
    if not str(runtime.get("model_pilot_job_command", "")).startswith("/"):
        raise LockDefect(
            "the model pilot job command must be an absolute path that exists "
            "inside the image")
    if runtime.get("model_pilot_job_command") not in \
            list(runtime.get("entrypoints", [])):
        raise LockDefect(
            "the job command is not one of the installed image entry points")

    transport = lock.get("transport", {})
    bound_impl = {entry.get("path") for entry in
                  transport.get("implementation", [])}
    if bound_impl != set(IMPLEMENTATION_PATHS):
        raise LockDefect(
            "the lock does not bind the registered transport implementation "
            "identity")
    canaries = transport.get("canaries", {})
    for name in CANARY_NAMES:
        receipt = canaries.get(name)
        if not isinstance(receipt, dict) or receipt.get("passed") is not True:
            raise LockDefect(
                "the lock does not carry a passing %s canary receipt" % name)

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
            "widened by the post-ready completion authority")
    if dict(lock.get("smoke_exact_allocation", {})) != dict(SMOKE_EXACT):
        raise LockDefect(
            "the execution lock smoke allocation differs from the registered "
            "exact smoke allocation")
    if {role: dict(body) for role, body in lock.get("roles", {}).items()} != \
            {role: dict(ROLE_IDENTITIES[role]) for role in ROLE_IDENTITIES}:
        raise LockDefect(
            "the execution lock pins a different role identity or revision set")

    registered = dict(FACT.IMMUTABLE_SOURCES)
    for key in ("corpus_and_p0_t", "immutable_sources"):
        entries = lock.get(key, [])
        for entry in entries:
            expected = registered.get(entry.get("path"))
            if expected is None:
                raise LockDefect(
                    "%s is not a registered immutable source"
                    % entry.get("path"))
            if entry.get("sha256") != expected["sha256"] \
                    or entry.get("bytes") != expected["bytes"]:
                raise LockDefect(
                    "the execution lock binds a different identity for %s than "
                    "the registered immutable source" % entry["path"])
        if len(entries) != len(registered):
            raise LockDefect(
                "the execution lock does not bind every registered immutable "
                "source under %s" % key)

    if not lock.get("attempt_binding", {}).get("attempt_id_rule"):
        raise LockDefect("the execution lock does not register an attempt rule")

    findings = verify_executable_bytes(lock, root=root)
    if findings:
        raise LockDefect("; ".join(findings))
    return True


def load_lock(root=None):
    return json.loads(_read(LOCK_PATH, root=root).decode("utf-8"))


def lock_bytes(root=None):
    return _read(LOCK_PATH, root=root)


def lock_identity(root=None):
    return blob_identity(LOCK_PATH, root=root)


def verify_binding(lock, commit=None, tree=None, image_digest=None, root=None):
    """Verify the running checkout and image against the generation-2 lock."""
    validate_lock(lock, root=root)
    findings = []
    if image_digest is not None and image_digest != lock["image"]["digest"]:
        findings.append(
            "the running image digest %s is not the locked digest %s"
            % (image_digest, lock["image"]["digest"]))
    if commit is not None and commit != lock["executable_code"]["commit"]:
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


def verify_generation_1_is_preserved_and_inert(root=None):
    """The generation-1 lock and handoff are preserved, unconsumed and inert."""
    record = generation_1_supersession(root=root)
    gen1 = json.loads(_read(GENERATION_1_LOCK["path"], root=root)
                      .decode("utf-8"))
    if gen1.get("legal_status", {}).get("p0_r1_pilot_execution_consumed") \
            is not False:
        raise LockDefect(
            "the preserved generation-1 lock does not record an unconsumed "
            "envelope")
    return record


LOCK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": ("https://j-space-observation/study3/"
            "p0_r1_execution_lock_v2.schema.json"),
    "title": "Study 3 P0-R1 generation-2 execution lock",
    "type": "object",
    "required": [
        "schema_version", "document_class", "generation", "stage", "state",
        "superseded", "authorities", "registration", "generation_1",
        "executable_code", "ready_commit_relationship", "image",
        "runtime_binding", "transport", "dependency_lock", "corpus_and_p0_t",
        "immutable_sources", "roles", "caps", "smoke_exact_allocation",
        "counters_before_execution", "state_transition", "attempt_binding",
        "legal_status", "claim_boundary", "permitted_sequence",
    ],
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION},
        "document_class": {"const": "study3_p0_r1_execution_lock"},
        "generation": {"const": GENERATION},
        "stage": {"const": "P0-R1"},
        "state": {"const": STATE_READY},
        "superseded": {"const": False},
        "authorities": {"type": "array", "minItems": 3},
        "registration": {"type": "object"},
        "generation_1": {
            "type": "object",
            "required": ["path", "bytes", "sha256", "consumed", "superseded",
                         "launchable", "reason"],
            "properties": {
                "consumed": {"const": False},
                "superseded": {"const": True},
                "launchable": {"const": False},
            },
        },
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
        "runtime_binding": {
            "type": "object",
            "required": ["standalone_source_root", "entrypoints",
                         "model_pilot_job_command", "job_name",
                         "depends_on_the_acr_workspace_mount"],
            "properties": {
                "depends_on_the_acr_workspace_mount": {"const": False},
            },
        },
        "transport": {
            "type": "object",
            "required": ["implementation", "canaries"],
        },
        "dependency_lock": {"type": "object"},
        "corpus_and_p0_t": {"type": "array"},
        "immutable_sources": {"type": "array"},
        "roles": {"type": "object"},
        "caps": {"type": "object"},
        "smoke_exact_allocation": {"type": "object"},
        "counters_before_execution": {"type": "object"},
        "state_transition": {"type": "array"},
        "attempt_binding": {"type": "object"},
        "legal_status": {
            "type": "object",
            "required": ["formal_execution_authorized",
                         "p0_r1_pilot_execution_authorized",
                         "p0_r1_pilot_execution_consumed"],
            "properties": {
                "formal_execution_authorized": {"const": False},
                "p0_r1_pilot_execution_authorized": {"const": True},
                "p0_r1_pilot_execution_consumed": {"const": False},
            },
        },
        "claim_boundary": {"type": "string"},
        "permitted_sequence": {"type": "array"},
    },
}


def dumps(document):
    return json.dumps(document, indent=2, sort_keys=True,
                      ensure_ascii=False) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--supersession", action="store_true")
    parser.add_argument("--executable-code-commit")
    parser.add_argument("--executable-code-tree")
    parser.add_argument("--image-digest")
    parser.add_argument("--ready-commit-parent")
    parser.add_argument("--canary-receipts")
    parser.add_argument("--out")
    parser.add_argument("--schema-out")
    args = parser.parse_args(argv)

    try:
        if args.build:
            with open(args.canary_receipts, "rb") as handle:
                receipts = json.loads(handle.read().decode("utf-8"))
            lock = build_lock(
                args.executable_code_commit, args.executable_code_tree,
                args.image_digest, args.ready_commit_parent, receipts)
            validate_lock(lock)
            payload = dumps(lock).encode("utf-8")
            out = args.out or os.path.join(REPO_ROOT, *LOCK_PATH.split("/"))
            with open(out, "wb") as handle:
                handle.write(payload)
            schema_out = args.schema_out or os.path.join(
                REPO_ROOT, *LOCK_SCHEMA_PATH.split("/"))
            with open(schema_out, "wb") as handle:
                handle.write(dumps(LOCK_SCHEMA).encode("utf-8"))
            print("P0_R1_EXECUTION_LOCK_V2_WRITTEN=%s" % out)
            print("  bytes  %d" % len(payload))
            print("  sha256 %s" % hashlib.sha256(payload).hexdigest())
            return 0
        if args.validate:
            validate_lock(load_lock())
            identity = lock_identity()
            print("P0_R1_EXECUTION_LOCK_V2_VALID=1")
            print("  bytes  %d" % identity["bytes"])
            print("  sha256 %s" % identity["sha256"])
            return 0
        if args.supersession:
            record = verify_generation_1_is_preserved_and_inert()
            print(json.dumps(record, indent=2, sort_keys=True))
            return 0
        parser.print_help()
        return 2
    except LockDefect as exc:
        print("EXECUTION LOCK REFUSED")
        print("  FAIL %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
