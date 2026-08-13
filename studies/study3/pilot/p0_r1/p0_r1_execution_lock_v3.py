#!/usr/bin/env python3
"""Build, validate and publish the Study 3 P0-R1 generation-3 execution lock.

The lock is the object a fresh successor session trusts, so it records exactly
what can be checked mechanically and nothing that can only be believed.

Three things are represented here that generation 2 left to prose:

* the **executable commit and tree** whose bytes were built into the image,
  with a sha256 for every bound path;
* the **ready anchor**, the commit that carries this lock, recorded as its
  parent plus the permitted governance-only descendant rule -- a commit cannot
  contain its own hash, so the anchor is proved at successor time rather than
  asserted here; and
* the **published head**, which is whatever ``origin/main`` is when the
  successor runs and is therefore never written into the lock at all.

Generations 1 and 2 are recorded as unconsumed, superseded and explicitly
``launchable = false``, with their exact bytes preserved so both remain
auditable.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, P0_R1_DIR)
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))

SCHEMA_VERSION = "study3-p0-r1-execution-lock-v3"
GENERATION = 3

STATE = "STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE"

LOCK_NAME = "p0_r1_execution_lock_v3.json"
SCHEMA_NAME = "p0_r1_execution_lock_v3.schema.json"

REGISTRY = "acrjspaceobssea0708231738.azurecr.io"
REPOSITORY = "j-space-observation-study3-p0-r1"

GPU_JOB_NAME = "job-jspace-s3-p0r1-pilot-g3"
RECOVERY_JOB_NAME = "job-jspace-s3-p0r1-recover-g3"

CANARY_NAMES = (
    "standalone_layout", "exact_cli_wiring", "replay_capture_recovery",
    "private_prefix", "blob_journal", "hard_kill_recovery",
    "cpu_managed_identity_recovery", "image_bound_bytes",
)

#: The four controlling authorities, in the order they were issued.
AUTHORITY_PATHS = (
    "studies/study3/prompts/study3_v0_6_p0_r1_authority.md",
    "studies/study3/prompts/"
    "study3_p0_r1_pre_replay_execution_completion_authority_rev2.md",
    "studies/study3/prompts/"
    "study3_p0_r1_post_ready_transport_exception_safety_authority.md",
    "studies/study3/prompts/"
    "study3_p0_r1_generation3_execution_closure_authority.md",
)

#: Every generation-3 executable byte. Changing any of these after the image is
#: built invalidates the image, and the successor preflight proves it did not
#: happen.
GENERATION_3_CODE_PATHS = (
    "studies/study3/pilot/p0_r1/p0_r1_azure_query_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_ready_anchor_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_replay_capture_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_authorization_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_journal_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_blob_transport_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_prefix_preflight_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_model_runner_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_replay_gate_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_recovery_v3.py",
    "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v3.py",
    "studies/study3/pilot/p0_r1/execution/p0_r1_model_execution_v3.py",
    "studies/study3/pilot/p0_r1/container/p0_r1_successor_v3.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_model_pilot_v3.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_replay_v3.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_recovery_v3.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_canary_v3.sh",
    "studies/study3/pilot/p0_r1/container/p0_r1_infrastructure_receipt_v3.py",
    "studies/study3/pilot/p0_r1/container/p0_r1_cli_wiring_canary_v3.py",
    "studies/study3/pilot/p0_r1/container/p0_r1_private_journal_canary_v3.py",
    "studies/study3/pilot/p0_r1/container/p0_r1_hard_kill_canary_v3.py",
    "studies/study3/pilot/p0_r1/container/p0_r1_image_manifest_v3.py",
    "studies/study3/pilot/p0_r1/container/Dockerfile.study3-p0-r1-v3",
    "studies/study3/pilot/p0_r1/container/p0_r1_acr_task_v3.yaml",
    "studies/study3/pilot/p0_r1/container/p0_r1_gpu_job_v3.yaml",
    "studies/study3/pilot/p0_r1/container/p0_r1_recovery_job_v3.yaml",
    "tests/test_study3_p0_r1_generation3_execution_closure.py",
)

#: Generation-1 and generation-2 executable bytes, re-hashed here so the lock
#: proves they were preserved rather than merely claiming it.
INHERITED_CODE_PATHS = (
    "studies/study3/pilot/p0_r1/p0_r1_protocol.py",
    "studies/study3/pilot/p0_r1/p0_r1_factorization.py",
    "studies/study3/pilot/p0_r1/p0_r1_replay_gate.py",
    "studies/study3/pilot/p0_r1/p0_r1_model_runner.py",
    "studies/study3/pilot/p0_r1/p0_r1_execution_lock.py",
    "studies/study3/pilot/p0_r1/execution/p0_r1_model_execution.py",
    "studies/study3/pilot/p0_r1/p0_r1_transport.py",
    "studies/study3/pilot/p0_r1/p0_r1_blob_transport.py",
    "studies/study3/pilot/p0_r1/p0_r1_journal.py",
    "studies/study3/pilot/p0_r1/p0_r1_runtime_binding.py",
    "studies/study3/pilot/p0_r1/p0_r1_model_runner_v2.py",
    "studies/study3/pilot/p0_r1/p0_r1_replay_gate_v2.py",
    "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.py",
    "studies/study3/pilot/p0_r1/execution/p0_r1_model_execution_v2.py",
)

DEPENDENCY_PATHS = (
    "studies/study3/pilot/p0_r1/container/requirements-study3-p0-r1.txt",
    "studies/study3/pilot/p0_r1/container/"
    "requirements-study3-p0-r1-transport-v2.txt",
)

GENERATION_1 = {
    "lock": "studies/study3/pilot/p0_r1/p0_r1_execution_lock.json",
    "handoff": "studies/study3/pilot/p0_r1/P0_R1_HANDOFF.md",
    "image_digest": ("sha256:7e2690feb6854a53f096d5b321e69fddebd2b744289c760e"
                     "2fe74ed1ccec8176"),
    "executable_code_commit": "aad14c45e9681a34f382aa95c55ac875d2ca98ce",
    "executable_code_tree": "a26c02bc230857b5fa8002b0b1b31a570b1c95be",
    "reason": (
        "the generation-1 image could not have run: its job command "
        "/workspace/p0_r1_model_pilot.sh is not a path in the image, its entry "
        "point defaults SRC to a checkout mount no GPU job provides, and the "
        "executor loads a lock the image cannot contain."),
}

GENERATION_2 = {
    "lock": "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json",
    "handoff": "studies/study3/pilot/p0_r1/P0_R1_HANDOFF_V2.md",
    "image_digest": ("sha256:5f964edb414b8a22682693d8314063693daca3b915398094"
                     "ec008d2c03308827"),
    "executable_code_commit": "863aca8b3a2ac73d9e8c031f762bda6fae125059",
    "executable_code_tree": "f48f577fa008d3e0ecfabff281bdae2e4a14a6b0",
    "ready_commit": "c7e02b43e1dbf811d1b35ae0fc0fe9d1a1d12947",
    "published_head": "c04ec748a4b2b63af22f50595816b5e6b6805ff6",
    "reason": (
        "the generation-2 successor path could not perform the authorized "
        "sequence without an unrecoverable one-shot failure. Its documented "
        "preflight command exits 2 on unrecognized arguments; its production "
        "runner CLI never builds the authorization it requires and refuses "
        "itself; the receipt it emits records complete_byte_recovery_verified "
        "as false while its launcher requires true, so no genuine replay could "
        "authorize the pilot; its live-replay mode captures no run identity or "
        "raw log; and its journal is not durable on the production command."),
}

COUNTERS = (
    "additional_gpu_attempt_with_signed_zero_operation_receipt",
    "bank_rows_written", "common_prefix_tokens_processed",
    "distinct_checkpoint_identities_downloaded",
    "distinct_tokenizer_identities_constructed", "exceptions_observed",
    "generated_tokens", "gpu_jobs_performing_a_model_operation",
    "hosted_provider_inference_calls", "model_weight_loads",
    "non_generative_prefill_evaluations", "parser_calls",
    "positive_reference_operations", "registered_prompt_tokens_processed",
    "replay_gate_evaluations", "restricted_logit_reads",
    "runtime_batched_forward_calls", "runtime_batched_tokenizer_calls",
    "s1_scored_rows", "s2_scored_rows", "s3_cpu_only_reuse_scored_rows",
    "s4_generation_calls", "s4_incremental_decode_evaluations",
    "s4_prefill_evaluations", "s4_scored_generation_rows",
    "scoring_context_tokens_processed", "seeds_drawn",
    "tokenizer_construction_events", "tokenizer_encoded_sequences",
    "total_scored_rows", "total_sequence_level_model_evaluation_equivalents",
)


class LockDefect(Exception):
    """The lock cannot be built or does not validate."""


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def _require_sha(value, label):
    if not isinstance(value, str) or len(value) != 40 \
            or any(character not in "0123456789abcdef" for character in value):
        raise LockDefect("%s is not a 40-character lowercase hex object" % label)
    if set(value) == {"0"}:
        raise LockDefect("%s is an all-zero placeholder" % label)
    return value


def _require_digest(value, label):
    if not isinstance(value, str) or not value.startswith("sha256:") \
            or len(value) != 71 \
            or any(character not in "0123456789abcdef"
                   for character in value[7:]):
        raise LockDefect("%s is not an immutable sha256 digest" % label)
    if set(value[7:]) == {"0"}:
        raise LockDefect("%s is an all-zero placeholder" % label)
    return value


def _load_json(root, relative):
    with open(os.path.join(root, relative.replace("/", os.sep)), "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def _file_identity(root, relative):
    path = os.path.join(root, relative.replace("/", os.sep))
    if not os.path.exists(path):
        raise LockDefect("bound path %s does not exist" % relative)
    with open(path, "rb") as handle:
        payload = handle.read()
    return {"path": relative, "bytes": len(payload),
            "sha256": _sha256(payload)}


def _git(args, root=None):
    completed = subprocess.run(  # noqa: S603 - fixed executable
        ["git"] + list(args), cwd=root or REPO_ROOT, capture_output=True,
        text=True)
    if completed.returncode != 0:
        raise LockDefect("git %s failed: %s"
                         % (" ".join(args), completed.stderr.strip()))
    return completed.stdout.strip()


def _inherited_lock_identity(root, relative):
    identity = _file_identity(root, relative)
    with open(os.path.join(root, relative.replace("/", os.sep)), "rb") as fh:
        document = json.loads(fh.read().decode("utf-8"))
    identity["state"] = document.get("state")
    identity["generation"] = document.get("generation", 1)
    return identity


def build(root=None, executable_commit=None, executable_tree=None,
          ready_anchor_parent=None, image_digest=None, base_digest=None,
          canary_receipts=None):
    """Assemble the complete generation-3 lock document."""
    root = root or REPO_ROOT
    _require_sha(executable_commit, "executable commit")
    _require_sha(executable_tree, "executable tree")
    _require_sha(ready_anchor_parent, "ready anchor parent")
    _require_digest(image_digest, "image digest")
    _require_digest(base_digest, "base digest")
    if not isinstance(canary_receipts, dict):
        raise LockDefect("the final lock requires model-free canary receipts")
    missing_canaries = [name for name in CANARY_NAMES
                        if not isinstance(canary_receipts.get(name), dict)
                        or canary_receipts[name].get("passed") is not True]
    if missing_canaries:
        raise LockDefect(
            "missing passing canary receipt(s): %s"
            % ", ".join(sorted(missing_canaries)))

    generation_3_files = [_file_identity(root, path)
                          for path in GENERATION_3_CODE_PATHS]
    inherited_files = [_file_identity(root, path)
                       for path in INHERITED_CODE_PATHS]
    authorities = [_file_identity(root, path) for path in AUTHORITY_PATHS]
    dependencies = [_file_identity(root, path) for path in DEPENDENCY_PATHS]
    v2 = _load_json(
        root, "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json")

    generation_1 = dict(GENERATION_1)
    generation_1.update(_inherited_lock_identity(root, GENERATION_1["lock"]))
    generation_1.update({
        "path": GENERATION_1["lock"], "superseded": True, "consumed": False,
        "launchable": False, "executions": 0, "gpu_allocations": 0,
        "tokenizer_constructions": 0, "tokenizer_encodes": 0,
        "checkpoint_downloads": 0, "model_weight_loads": 0,
        "superseded_by": "studies/study3/pilot/p0_r1/" + LOCK_NAME,
    })
    generation_2 = dict(GENERATION_2)
    generation_2.update(_inherited_lock_identity(root, GENERATION_2["lock"]))
    generation_2.update({
        "path": GENERATION_2["lock"], "superseded": True, "consumed": False,
        "launchable": False, "executions": 0, "gpu_allocations": 0,
        "tokenizer_constructions": 0, "tokenizer_encodes": 0,
        "checkpoint_downloads": 0, "model_weight_loads": 0,
        "model_free_canary_executions": 2,
        "superseded_by": "studies/study3/pilot/p0_r1/" + LOCK_NAME,
    })

    document = {
        "schema_version": SCHEMA_VERSION,
        "document_class": "study3_p0_r1_execution_lock",
        "generation": GENERATION,
        "superseded": False,
        "state": STATE,
        "stage": "STUDY3-P0-R1",
        "built_at": datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authorities": authorities,
        "executable_code": {
            "commit": executable_commit,
            "tree": executable_tree,
            "generation_3_file_count": len(generation_3_files),
            "inherited_file_count": len(inherited_files),
            "files": generation_3_files + inherited_files,
        },
        "ready_commit_relationship": {
            "ready_anchor_parent": ready_anchor_parent,
            "ready_anchor_commit": None,
            "rule": (
                "the ready anchor is the commit that carries this lock. A "
                "commit cannot contain its own hash, so it is recorded as a "
                "parent here and proved at successor time by "
                "p0_r1_ready_anchor_v3.prove, which requires HEAD == "
                "origin/main, a clean tree, executable -> anchor -> head "
                "ancestry, and every post-anchor change inside the governance "
                "allowlist."),
            "published_head_is_recorded_in_the_lock": False,
            "resolution": (
                "resolve the direct first-parent child of ready_anchor_parent "
                "and require that commit to carry this exact lock blob"),
        },
        "image": {
            "registry": REGISTRY,
            "repository": REPOSITORY,
            "digest": image_digest,
            "base_digest": base_digest,
            "reference": "%s/%s@%s" % (REGISTRY, REPOSITORY, image_digest),
            "standalone_source_root": "/opt/jspace/src",
            "requires_a_context_mount": False,
        },
        "runtime_binding": {
            "entrypoints": [
                "/usr/local/bin/p0_r1_model_pilot_v3.sh",
                "/usr/local/bin/p0_r1_replay_v3.sh",
                "/usr/local/bin/p0_r1_recovery_v3.sh",
            ],
            "gpu_job_name": GPU_JOB_NAME,
            "recovery_job_name": RECOVERY_JOB_NAME,
            "model_pilot_job_command": "/usr/local/bin/p0_r1_model_pilot_v3.sh",
            "authorization_inputs_are_mandatory": True,
            "authorization_construction_path": "p0_r1_authorization_v3.build",
            "injection_version": "study3-p0-r1-runtime-injection-v3",
            "injection_environment": [
                "P0_R1_LOCK_V3_B64", "P0_R1_REPLAY_RECEIPT_V3_B64",
                "P0_R1_RECONSTRUCTION_RECEIPT_V3_B64",
                "P0_R1_HEAD_PROOF_V3_B64",
            ],
        },
        "transport": {
            "prefix_root": "study3/p0_r1/gen3",
            "primary_journal_sink": "private_blob",
            "local_filesystem_is": "cache_only",
            "journal_is_create_only": True,
            "journal_stores_complete_payloads": True,
            "manifest_enumerates_recursively": True,
            "secondary_route": "bounded complete-byte console envelope",
            "canaries": canary_receipts or {},
        },
        "successor_context": {
            "source": "git archive of the exact published HEAD",
            "archive_format": "tar",
            "archive_is_hashed_before_submission": True,
            "archive_is_extracted_to_a_new_empty_directory": True,
            "mutable_worktree_is_submitted": False,
            "acr_task": (
                "studies/study3/pilot/p0_r1/container/"
                "p0_r1_acr_task_v3.yaml"),
            "required_task_values": [
                "IMAGE", "LOCK_B64", "DIGEST", "READY_ANCHOR", "MODE"],
        },
        "replay_contract": {
            "gate_receipt_is_never_rewritten": True,
            "emitted_receipt_claims_its_own_recovery": False,
            "recovery_proof_document":
                "p0_r1_replay_reconstruction_receipt_v3.json",
            "authorization_tuple": [
                "the exact recovered replay receipt",
                "the independent reconstruction receipt from the raw log",
                "the active generation-3 lock",
                "the published-head proof",
            ],
            "either_receipt_alone_authorizes": False,
            "gate_result_schema": "study3-p0-r1-replay-gate-result-v3",
            "gate_receipt_schema": "study3-p0-r1-replay-gate-receipt-v3",
            "reconstruction_receipt_schema":
                "study3-p0-r1-replay-reconstruction-v3",
            "authorization_schema": "study3-p0-r1-model-authorization-v3",
        },
        "azure_query_contract": {
            "outcomes": ["PROVED_ABSENT", "PROVED_PRESENT", "ERROR"],
            "error_is_treated_as_absence": False,
            "only_proved_absent_may_create_or_start": True,
        },
        "dependency_lock": {
            "frozen_science": dependencies[0],
            "durable_transport": dependencies[1],
            "generation_1_dependency_set_edited": False,
        },
        "registration": v2["registration"],
        "corpus_and_p0_t": v2["corpus_and_p0_t"],
        "immutable_sources": v2["immutable_sources"],
        "roles": v2["roles"],
        "caps": v2["caps"],
        "smoke_exact_allocation": v2["smoke_exact_allocation"],
        "state_transition": v2["state_transition"],
        "generation_1": generation_1,
        "generation_2": generation_2,
        "superseded_generations": 2,
        "counters_before_execution": {name: 0 for name in COUNTERS},
        "legal_status": {
            "p0_r1_pilot_execution_authorized": True,
            "p0_r1_pilot_execution_consumed": False,
            "formal_execution_authorized": False,
            "draft_v0_6_frozen": False,
            "draft_v0_6_reviewed": False,
            "interface_selected": None,
            "positive_reference": None,
            "rp_wrapper": None,
            "od2": "UNRESOLVED_BLOCKING_OPERATOR_DECISION",
            "ur22": "UNRESOLVED",
            "evidence_ledger_last_row": "EV-0016",
            "research_question_answered": False,
        },
        "permitted_sequence": [
            "the replay gate runs first, CPU-only, inside the image bound by "
            "the digest above, and emits its four exact artifacts through the "
            "verified complete-byte transport",
            "the operator captures the run identity and the complete raw log "
            "and builds an independent reconstruction receipt from it",
            "only the recovered receipt plus that reconstruction receipt plus "
            "this lock plus a published-head proof authorize the single "
            "bounded GPU model pilot",
            "a replay failure, capture failure, reconstruction failure or any "
            "ambiguity publishes the registered stop and performs no model "
            "operation",
        ],
        "attempt_binding": {
            "one_replay_attempt_authorizes_at_most_one_model_pilot": True,
            "envelopes_are_per_study_not_per_lock_generation": True,
            "remaining_overall_envelopes": 1,
            "attempt_id_rule": (
                "the replay gate mints exactly one attempt id of the form "
                "gen3-<executable_code_commit[:12]>-<utc>; the pilot consumes "
                "that same attempt id, writes only under that generation-3 "
                "Blob prefix, and refuses a receipt minted for any other "
                "attempt"),
        },
        "claim_boundary": (
            "this lock authorizes routing and execution mechanics only. It "
            "makes no scientific claim, selects no interface, freezes no "
            "draft, and adds no evidence row."),
    }
    return document


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True,
                      ensure_ascii=True) + "\n"


def schema():
    """A minimal structural schema, checked by --validate."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Study 3 P0-R1 generation-3 execution lock",
        "type": "object",
        "required": [
            "schema_version", "generation", "state", "superseded",
            "authorities",
            "executable_code", "ready_commit_relationship", "image",
            "runtime_binding", "transport", "replay_contract",
            "azure_query_contract", "dependency_lock", "generation_1",
            "generation_2", "counters_before_execution", "legal_status",
            "permitted_sequence", "attempt_binding",
            "registration", "corpus_and_p0_t", "immutable_sources", "roles",
            "caps", "smoke_exact_allocation", "state_transition",
            "successor_context",
        ],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "generation": {"const": GENERATION},
            "state": {"const": STATE},
            "superseded": {"const": False},
            "executable_code": {
                "type": "object",
                "required": ["commit", "tree", "files"],
            },
            "legal_status": {
                "type": "object",
                "required": ["p0_r1_pilot_execution_authorized",
                             "p0_r1_pilot_execution_consumed",
                             "formal_execution_authorized"],
            },
        },
    }


def validate(document, root=None, image_digest=None):
    """Re-check every bound byte and every invariant the lock asserts."""
    root = root or REPO_ROOT
    if document.get("schema_version") != SCHEMA_VERSION:
        raise LockDefect("schema %r is not %r"
                         % (document.get("schema_version"), SCHEMA_VERSION))
    if document.get("generation") != GENERATION:
        raise LockDefect("this is not a generation-3 lock")
    if document.get("state") != STATE:
        raise LockDefect("state %r is not %r" % (document.get("state"), STATE))
    if document.get("superseded") is not False:
        raise LockDefect("the active generation-3 lock is marked superseded")
    executable = document.get("executable_code") or {}
    _require_sha(executable.get("commit"), "executable commit")
    _require_sha(executable.get("tree"), "executable tree")
    _require_digest((document.get("image") or {}).get("digest"),
                    "image digest")
    _require_digest((document.get("image") or {}).get("base_digest"),
                    "base digest")
    _require_sha(
        (document.get("ready_commit_relationship") or {}).get(
            "ready_anchor_parent"),
        "ready anchor parent")

    for entry in document["executable_code"]["files"]:
        actual = _file_identity(root, entry["path"])
        if actual["sha256"] != entry["sha256"]:
            raise LockDefect(
                "bound path %s hashes to %s, not the locked %s"
                % (entry["path"], actual["sha256"], entry["sha256"]))
        if actual["bytes"] != entry["bytes"]:
            raise LockDefect(
                "bound path %s is %d bytes, not the locked %d"
                % (entry["path"], actual["bytes"], entry["bytes"]))

    for entry in document["authorities"]:
        actual = _file_identity(root, entry["path"])
        if actual["sha256"] != entry["sha256"]:
            raise LockDefect("authority %s changed" % entry["path"])

    counters = document["counters_before_execution"]
    non_zero = {name: value for name, value in counters.items() if value != 0}
    if non_zero:
        raise LockDefect("counters must all be zero, found %r" % non_zero)
    if sorted(counters) != sorted(COUNTERS):
        raise LockDefect("the counter set does not match the registered set")

    legal = document["legal_status"]
    if not legal["p0_r1_pilot_execution_authorized"]:
        raise LockDefect("the pilot authorization flag is not set")
    if legal["p0_r1_pilot_execution_consumed"]:
        raise LockDefect("the envelope is already consumed")
    if legal["formal_execution_authorized"]:
        raise LockDefect("formal execution must remain unauthorized")

    for key in ("generation_1", "generation_2"):
        block = document[key]
        if not block.get("superseded") or block.get("launchable") \
                or block.get("consumed"):
            raise LockDefect(
                "%s must be superseded, unconsumed and not launchable" % key)
        actual = _file_identity(root, block["path"])
        if actual["sha256"] != block["sha256"]:
            raise LockDefect(
                "%s lock bytes changed; superseded generations are preserved "
                "byte-for-byte" % key)

    canaries = (document.get("transport") or {}).get("canaries")
    if not isinstance(canaries, dict):
        raise LockDefect("transport.canaries must be a non-empty mapping")
    missing_canaries = [name for name in CANARY_NAMES
                        if not isinstance(canaries.get(name), dict)
                        or canaries[name].get("passed") is not True]
    if missing_canaries:
        raise LockDefect(
            "transport.canaries lacks passing receipt(s): %s"
            % ", ".join(sorted(missing_canaries)))

    v2 = _load_json(
        root, "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v2.json")
    for key in ("registration", "corpus_and_p0_t", "immutable_sources",
                "roles", "caps", "smoke_exact_allocation",
                "state_transition"):
        if document.get(key) != v2.get(key):
            raise LockDefect(
                "the generation-3 lock changed inherited scientific binding %s"
                % key)

    if image_digest and document["image"]["digest"] != image_digest:
        raise LockDefect(
            "the lock binds image %s, not the supplied %s"
            % (document["image"]["digest"], image_digest))

    if document["attempt_binding"]["remaining_overall_envelopes"] != 1:
        raise LockDefect("exactly one overall envelope must remain")
    return True


def supersession(document):
    """The record a preflight prints to prove both predecessors are inert."""
    return {
        "active": {"path": "studies/study3/pilot/p0_r1/" + LOCK_NAME,
                   "generation": GENERATION, "state": document["state"]},
        "generation_1": document["generation_1"],
        "generation_2": document["generation_2"],
        "superseded_without_consumption": True,
        "remaining_overall_envelopes":
            document["attempt_binding"]["remaining_overall_envelopes"],
    }


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_execution_lock_v3.py",
        "generation": GENERATION,
        "generation_3_paths": len(GENERATION_3_CODE_PATHS),
        "inherited_paths": len(INHERITED_CODE_PATHS),
        "authorities": len(AUTHORITY_PATHS),
        "records_published_head": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--supersession", action="store_true")
    parser.add_argument("--lock-file")
    parser.add_argument("--executable-code-commit")
    parser.add_argument("--executable-code-tree")
    parser.add_argument("--ready-anchor-parent")
    parser.add_argument("--image-digest")
    parser.add_argument("--base-digest")
    parser.add_argument("--canary-receipts")
    parser.add_argument("--root")
    parser.add_argument("--out")
    parser.add_argument("--schema-out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    root = args.root or REPO_ROOT

    if args.build:
        receipts = None
        if args.canary_receipts:
            with open(args.canary_receipts, "rb") as handle:
                receipts = json.loads(handle.read().decode("utf-8"))
        document = build(
            root=root, executable_commit=args.executable_code_commit,
            executable_tree=args.executable_code_tree,
            ready_anchor_parent=args.ready_anchor_parent,
            image_digest=args.image_digest, base_digest=args.base_digest,
            canary_receipts=receipts)
        payload = dumps(document).encode("utf-8")
        out = args.out or os.path.join(P0_R1_DIR, LOCK_NAME)
        with open(out, "wb") as handle:
            handle.write(payload)
        schema_payload = (json.dumps(schema(), indent=1, sort_keys=True)
                          + "\n").encode("utf-8")
        schema_out = args.schema_out or os.path.join(P0_R1_DIR, SCHEMA_NAME)
        with open(schema_out, "wb") as handle:
            handle.write(schema_payload)
        print("P0_R1_EXECUTION_LOCK_V3_BUILT=1")
        print("  bytes  %d" % len(payload))
        print("  sha256 %s" % _sha256(payload))
        print("  schema %d bytes / %s"
              % (len(schema_payload), _sha256(schema_payload)))
        return 0

    lock_file = args.lock_file or os.path.join(P0_R1_DIR, LOCK_NAME)
    if args.validate or args.supersession:
        if not os.path.exists(lock_file):
            print("FAIL: %s does not exist" % lock_file, file=sys.stderr)
            return 2
        with open(lock_file, "rb") as handle:
            payload = handle.read()
        document = json.loads(payload.decode("utf-8"))
        if args.supersession:
            print(json.dumps(supersession(document), indent=2, sort_keys=True))
            return 0
        try:
            validate(document, root=root, image_digest=args.image_digest)
        except LockDefect as exc:
            print("P0_R1_EXECUTION_LOCK_V3_INVALID=1", file=sys.stderr)
            print("  %s" % exc, file=sys.stderr)
            return 3
        print("P0_R1_EXECUTION_LOCK_V3_VALID=1")
        print("  bytes  %d" % len(payload))
        print("  sha256 %s" % _sha256(payload))
        print("  bound  %d paths"
              % len(document["executable_code"]["files"]))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
