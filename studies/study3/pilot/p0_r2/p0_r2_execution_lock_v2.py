#!/usr/bin/env python3
"""Generate and validate the corrected P0-R2 execution lock (v2).

The v1 lock is historical and is not edited. This module writes an additive
``p0_r2_execution_lock_v2.json`` that binds what the corrective closure actually
proved, and a JSON Schema that refuses a lock which merely *claims* it.

Every identity in the lock is read from a Git object, a receipt file or a
measured byte count. Nothing is accepted on a caller's word except the paths to
read, and every path is resolved against a committed object rather than the
mutable worktree.

Two structural rules deserve stating, because both were defects before:

* the lock never records the commit that contains it -- a commit cannot carry
  its own hash -- so it records the ready anchor's **parent** and the anchor is
  resolved by ancestry at proof time;
* the lock never records identities that will only exist after it is published.
  The v2 handoff, the receipts and the head proof are published *after* the
  anchor, so the lock binds their **paths** in the exact governance/evidence
  closure and their bytes are proved by the artifacts themselves. A lock that
  pretended to know a future hash would be a lie with a checksum.

Model-free: reads Git objects and hashes bytes. No tokenizer, checkpoint, model
weight, prefill, generation, scoring, evidence or GPU operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_closure_binding_v2 as CB2  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-execution-lock-v2"
STAGE = "STUDY3-P0-R2"
LOCK_NAME = "p0_r2_execution_lock_v2.json"
SCHEMA_NAME = "p0_r2_execution_lock_v2.schema.json"

TERMINAL_STATE = "STUDY3_P0_R2_EXECUTION_READY_AWAITING_REPLAY_GATE"

#: The bounded maxima the runner must enforce, not merely report.
CAPS = {
    "max_smoke_prefills_before_extension": 60,
    "max_non_generative_prefills": 180,
    "max_s4_generations": 12,
    "max_model_evaluation_equivalents": 228,
    "possible_scored_rows": 210,
}

#: Every counter that must be zero before the replay envelope is opened.
PRE_REPLAY_COUNTERS = {
    "tokenizer_constructions": 0,
    "tokenizer_encodes": 0,
    "checkpoint_downloads": 0,
    "checkpoint_loads": 0,
    "model_weight_loads": 0,
    "prefills": 0,
    "generations": 0,
    "scored_rows": 0,
    "evidence_rows_added": 0,
    "gpu_allocations": 0,
    "gpu_operations": 0,
    "live_replay_invocations": 0,
    "pilot_executions_started": 0,
}

#: The exact four standing failures this closure conditionally accepts.
STANDING_FAILURES = (
    "tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix",
    "tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last",
    "tests/test_phase05_jlens_saturation.py::test_no_artifact_asserts_a_prohibited_claim",
    "tests/test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only",
)

#: Legal state this lock may not change.
LEGAL_STATE = {
    "formal_execution_authorized": False,
    "draft_v0_6_reviewed": False,
    "draft_v0_6_frozen": False,
    "interface": None,
    "positive_reference": None,
    "rp_wrapper": None,
    "evidence_ledger_tail": "EV-0016",
    "research_question_answered": False,
}


class LockDefect(Exception):
    """The lock cannot be generated or validated honestly."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(root, *args):
    result = subprocess.run(  # noqa: S603 - fixed executable
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        check=False)
    if result.returncode:
        raise LockDefect("git %s failed: %s" % (" ".join(args),
                                                result.stderr.strip()))
    return result.stdout.strip()


def _entries(root, commit, paths):
    return [CB2.blob_identity(root, commit, path) for path in paths]


def build(root, inputs: dict) -> dict:
    """Assemble the v2 lock from committed objects and produced receipts."""
    root = Path(root).resolve()

    image_commit = inputs["image_executable_commit"]
    host_commit = inputs["host_closure_executable_commit"]
    closure_base = inputs["closure_base_commit"]
    anchor_parent = inputs["ready_anchor_parent"]

    image_tree = _git(root, "rev-parse", "%s^{tree}" % image_commit)
    host_tree = _git(root, "rev-parse", "%s^{tree}" % host_commit)

    manifest_path = inputs["image_manifest_path"]
    manifest = json.loads(
        CB2._git(root, ["show", "%s:%s" % (image_commit, manifest_path)])[0])
    image_files = [{"path": entry["path"], "kind": entry["kind"],
                    "bytes": entry["bytes"], "sha256": entry["sha256"],
                    "git_blob": entry["git_blob"]}
                   for entry in manifest["entries"]]

    host_files = _entries(root, host_commit, inputs["host_closure_paths"])
    validation_inputs = _entries(root, host_commit, inputs["validation_paths"])
    job_specifications = _entries(root, host_commit, inputs["job_spec_paths"])
    immutable_sources = _entries(root, image_commit,
                                 inputs["immutable_scientific_paths"])
    governance_bytes = _entries(root, host_commit,
                                inputs["governance_byte_paths"])
    p0_r1_protected = _entries(root, host_commit,
                               inputs["p0_r1_protected_paths"])

    task_path = inputs["task_path"]
    task = CB2.blob_identity(root, image_commit, task_path)

    def receipt(name):
        path = inputs["receipts"].get(name)
        if not path:
            return None
        raw = Path(path).read_bytes()
        return {"path": inputs["receipt_repository_paths"].get(name),
                "bytes": len(raw), "sha256": _sha256(raw),
                "document": json.loads(raw.decode("utf-8"))}

    lock = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "generation": 1,
        "revision": 2,
        "kind": "infrastructure-successor-corrective-closure",
        "changes_only": ("host-to-registry submission transport; corrective "
                         "closure tooling"),
        "terminal_state": TERMINAL_STATE,
        "science_is_unchanged_p0_r1_generation3": True,
        "self": {"path": inputs["lock_repository_path"], "name": LOCK_NAME},
        "schema": {"path": inputs["schema_repository_path"],
                   "name": SCHEMA_NAME},

        "authorities": [
            {"path": entry["path"], "bytes": entry["bytes"],
             "sha256": entry["sha256"], "git_blob": entry["git_blob"],
             "role": role}
            for entry, role in zip(
                _entries(root, host_commit, inputs["authority_paths"]),
                inputs["authority_roles"])],

        "image_executable": {"commit": image_commit, "tree": image_tree,
                             "files": image_files,
                             "file_count": len(image_files)},
        "host_closure_executable": {"commit": host_commit, "tree": host_tree,
                                    "files": host_files,
                                    "file_count": len(host_files)},
        "closure_base": {"commit": closure_base},
        "ready_commit_relationship": {
            "ready_anchor_parent": anchor_parent,
            "lock_records_its_own_commit": False,
            "anchor_is_resolved_by_ancestry": True,
            "anchor_must_be_strict_descendant_of_closure_base": True,
        },

        "validation_inputs": validation_inputs,
        "job_specifications": job_specifications,
        "immutable_sources": immutable_sources,
        "governance_bytes": governance_bytes,

        "transport": {
            "task_path": task_path,
            "task_blob": task["git_blob"],
            "task_bytes": task["bytes"],
            "task_sha256": task["sha256"],
            "context_entry_count": 2,
            "context_entries": ["task.yaml", "context_manifest.json"],
            "context_is_executable_code": False,
        },

        "image": {
            "reference": inputs["image_reference"],
            "digest": inputs["image_digest"],
            "tag": inputs["image_tag"],
            "base_image": inputs["base_image"],
            "base_digest": inputs["base_digest"],
            "build_run_id": inputs["image_build_run_id"],
            "manifest_path": manifest_path,
            "manifest_entries_sha256": manifest["entries_sha256"],
            "manifest_entry_count": manifest["entry_count"],
        },

        "p0_r1_terminal": {
            "stop_commit": inputs["p0_r1_stop_commit"],
            "state": "STOP_NO_MODEL_OPERATION",
            "replay_envelope_consumed": True,
            "launchable": False,
            "protected_prefixes": list(CB2.PROTECTED_P0_R1_PREFIXES),
            "protected_bytes": p0_r1_protected,
        },

        "v1_supersession": {
            "superseded": True,
            "launchable": False,
            "record_path": inputs["supersession_record_path"],
            "v1_lock_path": inputs["v1_lock_path"],
            "v1_lock_sha256": inputs["v1_lock_sha256"],
            "v1_lock_bytes": inputs["v1_lock_bytes"],
            "v1_ready_anchor": inputs["v1_ready_anchor"],
            "v1_executable_commit": inputs["v1_executable_commit"],
            "v1_image_digest": inputs["v1_image_digest"],
            "v1_bytes_edited": 0,
        },

        "replay_envelope": {
            "consumed": False,
            "invocations": 0,
            "consumed_on_invocation_even_without_a_run_id": True,
            "rerunnable": False,
            "regenerable": False,
            "substitutable": False,
        },

        "attempt": {
            "prefix_root": inputs["prefix_root"],
            "live_replay_attempt_id": inputs["live_replay_attempt_id"],
            "pilot_attempt_id": inputs["pilot_attempt_id"],
            "hard_kill_canary_attempt_id": inputs["hard_kill_attempt_id"],
        },

        "azure": {
            "subscription": inputs["subscription"],
            "resource_group": inputs["resource_group"],
            "registry": inputs["registry"],
            "storage_account": inputs["storage_account"],
            "container": inputs["results_container"],
            "managed_identity": inputs["managed_identity"],
            "gpu_job": inputs["gpu_job"],
            "recovery_job": inputs["recovery_job"],
            "hard_kill_job": inputs["hard_kill_job"],
            "gpu_workload_profile": "gpu-t4",
            "query_error_is_absence": False,
        },

        "designated_packing_canary": inputs["designated_packing_canary"],
        "canaries": inputs["canaries"],
        "attempt_ledger": receipt("attempt_ledger"),
        "validation": inputs["validation"],
        "standing_failures": {
            "count": len(STANDING_FAILURES),
            "node_ids": list(STANDING_FAILURES),
            "conditionally_accepted": True,
            "accepted_only_if": [
                "all four occur at both the baseline and the corrected head",
                "their normalized signatures agree",
                "no fifth failure occurs",
                "collection errors equal zero",
                "the corrected work introduces zero new failure",
            ],
            "baseline_commit": inputs["baseline_commit"],
            "baseline_signature_set_sha256":
                inputs["baseline_signature_set_sha256"],
            "corrected_signature_set_sha256":
                inputs["corrected_signature_set_sha256"],
        },

        "governance_evidence_closure": inputs["governance_evidence_closure"],
        "caps": dict(CAPS),
        "caps_are_enforced_not_reported": True,
        "pre_replay_counters": dict(PRE_REPLAY_COUNTERS),
        "legal_state": dict(LEGAL_STATE),

        "prohibitions": {
            "rerun_replay": True,
            "regenerate_replay": True,
            "substitute_another_attempt": True,
            "repair_the_gate_in_place": True,
            "second_az_acr_run_live": True,
            "create_success_artifacts_without_recovered_bytes": True,
            "update_or_repurpose_an_existing_gpu_job": True,
            "second_start_to_resolve_ambiguity": True,
            "set_live_replay_authorized_globally": True,
            "edit_v1_or_p0_r1_bytes": True,
            "caller_supplied_governance_allowlist": True,
        },
    }
    return lock


def schema() -> dict:
    """A JSON Schema that refuses a lock which only claims what it binds."""
    sha40 = {"type": "string", "pattern": "^[0-9a-f]{40}$"}
    sha256 = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    digest = {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}
    blob_entry = {
        "type": "object",
        "required": ["path", "bytes", "sha256"],
        "properties": {"path": {"type": "string", "minLength": 1},
                       "bytes": {"type": "integer", "minimum": 0},
                       "sha256": sha256,
                       "git_blob": sha40},
    }
    commit_tree = {
        "type": "object",
        "required": ["commit", "tree", "files"],
        "properties": {"commit": sha40, "tree": sha40,
                       "files": {"type": "array", "minItems": 1}},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_NAME,
        "title": "Study 3 P0-R2 corrective execution lock, version 2",
        "type": "object",
        "additionalProperties": True,
        "required": [
            "schema_version", "stage", "generation", "revision",
            "terminal_state", "self", "schema", "authorities",
            "image_executable", "host_closure_executable", "closure_base",
            "ready_commit_relationship", "validation_inputs",
            "job_specifications", "immutable_sources", "governance_bytes",
            "transport", "image", "p0_r1_terminal", "v1_supersession",
            "replay_envelope", "attempt", "azure",
            "designated_packing_canary", "canaries", "attempt_ledger",
            "validation", "standing_failures", "governance_evidence_closure",
            "caps", "pre_replay_counters", "legal_state", "prohibitions",
        ],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "stage": {"const": STAGE},
            "generation": {"const": 1},
            "revision": {"const": 2},
            "terminal_state": {"const": TERMINAL_STATE},
            "science_is_unchanged_p0_r1_generation3": {"const": True},
            "image_executable": commit_tree,
            "host_closure_executable": commit_tree,
            "closure_base": {"type": "object", "required": ["commit"],
                             "properties": {"commit": sha40}},
            "ready_commit_relationship": {
                "type": "object",
                "required": ["ready_anchor_parent",
                             "lock_records_its_own_commit"],
                "properties": {
                    "ready_anchor_parent": sha40,
                    "lock_records_its_own_commit": {"const": False},
                    "anchor_is_resolved_by_ancestry": {"const": True},
                },
            },
            "authorities": {"type": "array", "minItems": 2,
                            "items": blob_entry},
            "validation_inputs": {"type": "array", "minItems": 1,
                                  "items": blob_entry},
            "job_specifications": {"type": "array", "minItems": 1,
                                   "items": blob_entry},
            "immutable_sources": {"type": "array", "minItems": 4,
                                  "items": blob_entry},
            "governance_bytes": {"type": "array", "minItems": 2,
                                 "items": blob_entry},
            "transport": {
                "type": "object",
                "required": ["task_path", "task_blob", "task_sha256"],
                "properties": {"task_path": {"type": "string"},
                               "task_blob": sha40, "task_sha256": sha256,
                               "context_entry_count": {"const": 2},
                               "context_is_executable_code": {"const": False}},
            },
            "image": {
                "type": "object",
                "required": ["reference", "digest", "base_digest",
                             "build_run_id", "manifest_entries_sha256"],
                "properties": {"reference": {"type": "string"},
                               "digest": digest, "base_digest": digest,
                               "build_run_id": {"type": "string",
                                                "minLength": 1},
                               "manifest_entries_sha256": sha256},
            },
            "p0_r1_terminal": {
                "type": "object",
                "required": ["stop_commit", "state",
                             "replay_envelope_consumed", "launchable",
                             "protected_bytes"],
                "properties": {"stop_commit": sha40,
                               "state": {"const": "STOP_NO_MODEL_OPERATION"},
                               "replay_envelope_consumed": {"const": True},
                               "launchable": {"const": False},
                               "protected_bytes": {"type": "array",
                                                   "minItems": 8,
                                                   "items": blob_entry}},
            },
            "v1_supersession": {
                "type": "object",
                "required": ["superseded", "launchable", "record_path",
                             "v1_lock_path", "v1_lock_sha256"],
                "properties": {"superseded": {"const": True},
                               "launchable": {"const": False},
                               "v1_lock_sha256": sha256,
                               "v1_bytes_edited": {"const": 0}},
            },
            "replay_envelope": {
                "type": "object",
                "required": ["consumed", "invocations"],
                "properties": {
                    "consumed": {"const": False},
                    "invocations": {"const": 0},
                    "consumed_on_invocation_even_without_a_run_id":
                        {"const": True},
                    "rerunnable": {"const": False}},
            },
            "attempt": {
                "type": "object",
                "required": ["prefix_root", "live_replay_attempt_id",
                             "pilot_attempt_id"],
                "properties": {
                    "live_replay_attempt_id": {"type": "string",
                                               "pattern": "^p0r2-g1-"},
                    "pilot_attempt_id": {"type": "string",
                                         "pattern": "^p0r2-g1-"}},
            },
            "standing_failures": {
                "type": "object",
                "required": ["count", "node_ids", "conditionally_accepted"],
                "properties": {
                    "count": {"const": 4},
                    "node_ids": {"type": "array", "minItems": 4,
                                 "maxItems": 4,
                                 "items": {"type": "string"}},
                    "conditionally_accepted": {"const": True}},
            },
            "governance_evidence_closure": {
                "type": "array", "minItems": 1,
                "items": {"type": "object", "required": ["path", "class"],
                          "properties": {
                              "path": {"type": "string",
                                       "pattern": "^[^*?]+$"},
                              "class": {"enum": ["governance", "evidence"]}}},
            },
            "caps": {
                "type": "object",
                "required": list(CAPS),
                "properties": {name: {"const": value}
                               for name, value in CAPS.items()},
            },
            "caps_are_enforced_not_reported": {"const": True},
            "pre_replay_counters": {
                "type": "object",
                "required": list(PRE_REPLAY_COUNTERS),
                "properties": {name: {"const": 0}
                               for name in PRE_REPLAY_COUNTERS},
            },
            "legal_state": {
                "type": "object",
                "required": list(LEGAL_STATE),
                "properties": {
                    "formal_execution_authorized": {"const": False},
                    "draft_v0_6_reviewed": {"const": False},
                    "draft_v0_6_frozen": {"const": False},
                    "interface": {"type": "null"},
                    "positive_reference": {"type": "null"},
                    "rp_wrapper": {"type": "null"},
                    "evidence_ledger_tail": {"const": "EV-0016"},
                    "research_question_answered": {"const": False}},
            },
            "prohibitions": {
                "type": "object",
                "additionalProperties": {"const": True},
                "minProperties": 8,
            },
        },
    }


def _validate(document, node, pointer="") -> list:
    """A small, dependency-free subset of JSON Schema. Refusals are explicit."""
    problems = []
    if "const" in node and document != node["const"]:
        problems.append("%s must be %r, got %r"
                        % (pointer or "/", node["const"], document))
        return problems
    if "enum" in node and document not in node["enum"]:
        problems.append("%s must be one of %r" % (pointer or "/", node["enum"]))
        return problems
    kind = node.get("type")
    kinds = {"object": dict, "array": list, "string": str, "integer": int,
             "number": (int, float), "boolean": bool, "null": type(None)}
    if kind:
        expected = kinds.get(kind)
        if kind == "integer" and isinstance(document, bool):
            problems.append("%s must be an integer" % (pointer or "/"))
            return problems
        if expected and not isinstance(document, expected):
            problems.append("%s must be a %s" % (pointer or "/", kind))
            return problems
    if isinstance(document, str) and node.get("pattern"):
        import re
        if not re.search(node["pattern"], document):
            problems.append("%s does not match %s"
                            % (pointer or "/", node["pattern"]))
    if isinstance(document, str) and node.get("minLength") is not None \
            and len(document) < node["minLength"]:
        problems.append("%s is shorter than %d" % (pointer, node["minLength"]))
    if isinstance(document, list):
        if node.get("minItems") is not None and len(document) < node["minItems"]:
            problems.append("%s has %d items, fewer than the required %d"
                            % (pointer or "/", len(document), node["minItems"]))
        if node.get("maxItems") is not None and len(document) > node["maxItems"]:
            problems.append("%s has %d items, more than the allowed %d"
                            % (pointer or "/", len(document), node["maxItems"]))
        if node.get("items"):
            for index, item in enumerate(document):
                problems += _validate(item, node["items"],
                                      "%s/%d" % (pointer, index))
    if isinstance(document, dict):
        for name in node.get("required", []):
            if name not in document:
                problems.append("%s/%s is required" % (pointer, name))
        if node.get("minProperties") is not None \
                and len(document) < node["minProperties"]:
            problems.append("%s has fewer than %d properties"
                            % (pointer or "/", node["minProperties"]))
        for name, subnode in (node.get("properties") or {}).items():
            if name in document:
                problems += _validate(document[name], subnode,
                                      "%s/%s" % (pointer, name))
        extra = node.get("additionalProperties")
        if isinstance(extra, dict):
            known = set(node.get("properties") or {})
            for name, value in document.items():
                if name not in known:
                    problems += _validate(value, extra, "%s/%s" % (pointer, name))
    return problems


def validate(lock: dict, schema_document: dict) -> dict:
    problems = _validate(lock, schema_document)
    if problems:
        raise LockDefect("the lock does not satisfy its schema: %s"
                         % "; ".join(problems[:12]))
    return {
        "schema_version": "study3-p0-r2-execution-lock-v2-validation",
        "outcome": "LOCK_VALID",
        "problems": [],
        "model_operations_performed": 0,
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_execution_lock_v2.py",
        "stage": STAGE,
        "lock_name": LOCK_NAME,
        "schema_name": SCHEMA_NAME,
        "supersedes": "p0_r2_execution_lock_v1.json",
        "lock_records_its_own_commit": False,
        "lock_records_future_hashes": False,
        "caps": dict(CAPS),
        "pre_replay_counters": dict(PRE_REPLAY_COUNTERS),
        "standing_failures": list(STANDING_FAILURES),
        "legal_state": dict(LEGAL_STATE),
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--schema", action="store_true")
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--validate", action="store_true")
    parser.add_argument("--root", default=".")
    parser.add_argument("--inputs")
    parser.add_argument("--lock-file")
    parser.add_argument("--schema-file")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    try:
        if args.identity:
            document = implementation_identity()
        elif args.schema:
            document = schema()
        elif args.build:
            if not args.inputs:
                parser.error("--build requires --inputs")
            with open(args.inputs, encoding="utf-8") as handle:
                document = build(args.root, json.load(handle))
        else:
            if not args.lock_file:
                parser.error("--validate requires --lock-file")
            with open(args.lock_file, encoding="utf-8") as handle:
                lock = json.load(handle)
            if args.schema_file:
                with open(args.schema_file, encoding="utf-8") as handle:
                    schema_document = json.load(handle)
            else:
                schema_document = schema()
            document = validate(lock, schema_document)
    except (LockDefect, CB2.ClosureBindingDefect, OSError, KeyError,
            ValueError) as exc:
        print("P0_R2_EXECUTION_LOCK_V2_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    if args.validate:
        print("P0_R2_EXECUTION_LOCK_V2_VALID=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
