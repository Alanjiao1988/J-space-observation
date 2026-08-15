#!/usr/bin/env python3
"""Generate the P0-R2 generation-1 execution lock.

The lock is the single object a future session reads to know exactly what it is
allowed to run. It binds, in one signed-by-content document:

* the six identities that resolve the closure-binding cycle (executable code,
  task object, image, ready anchor, governance source, published head);
* the pinned image digest and its base digest;
* the delegated P0-R1 generation-3 scientific modules by path, size, SHA-256
  and Git blob id, so the gate can verify them before importing them;
* the transport parameters and the four canonical replay artifacts;
* the registered Azure identities, the attempt namespace, and the job names;
* the bounded-pilot caps;
* the model-free canary evidence that made the lock issuable.

The lock never contains its own hash, and the ready anchor commit cannot
contain its own hash either, so the lock records the anchor's *parent* and the
anchor is proved by ancestry rather than by self-reference.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


P0_R2_DIR = Path(__file__).resolve().parent
REPO_ROOT = P0_R2_DIR.parents[3]
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_transport as TX  # noqa: E402
import p0_r2_blob_transport as BLOB  # noqa: E402
import p0_r2_closure_binding_v1 as CLOSURE  # noqa: E402
import p0_r2_image_manifest_v1 as IMAGE  # noqa: E402
import p0_r2_model_runner_v1 as RUNNER  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-execution-lock-v1"
STAGE = "STUDY3-P0-R2"
GENERATION = 1
LOCK_NAME = "p0_r2_execution_lock_v1.json"
SCHEMA_NAME = "p0_r2_execution_lock_v1.schema.json"

SUBSCRIPTION = "943bacdf-8b6e-4e3a-8126-a149f623d32e"
TENANT = "16b3c013-d300-468d-ac64-7eda0820b6d3"
RESOURCE_GROUP = "rg-jspace-observation-sea"
REGISTRY = "acrjspaceobssea0708231738.azurecr.io"
REGISTRY_NAME = "acrjspaceobssea0708231738"
REPOSITORY = "j-space-observation-study3-p0-r2"
ACA_ENVIRONMENT = "cae-jspace-observation-sea-vnet2"
MANAGED_IDENTITY = "id-jspace-aca-acrpull-sea"
LOG_ANALYTICS_WORKSPACE = "8daddd67-1cfd-47c5-857e-af3c4a4e3787"

GPU_JOB = "job-jspace-s3-p0r2-pilot-g1"
RECOVERY_JOB = "job-jspace-s3-p0r2-recover-g1"
RESULTS_PATH = "studies/study3/pilot/p0/results/p0-r2/"
TASK_PATH = "studies/study3/pilot/p0_r2/container/p0_r2_acr_task_v1.yaml"

TERMINAL_STATE = "STUDY3_P0_R2_EXECUTION_READY_AWAITING_REPLAY_GATE"
P0_R1_STOP_COMMIT = "30806d793872a50e581d3252382b4a0ec2af3889"
P0_R1_STOP_STATE = "STOP_NO_MODEL_OPERATION"

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")


class LockDefect(Exception):
    """The lock cannot be issued truthfully."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root)] + list(args),
        capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise LockDefect(
            "git %s failed: %s" % (" ".join(args), result.stderr.strip()))
    return result.stdout.strip()


def canonical_bytes(document) -> bytes:
    """The exact byte form whose SHA-256 every downstream artifact quotes."""
    return json.dumps(document, indent=2, sort_keys=True).encode("utf-8") \
        + b"\n"


def build(*, root=None, executable_commit, image_digest, base_digest,
          anchor_parent, build_run_id, canaries, image_manifest=None,
          governance_source=None, published_head=None,
          full_suite=None, focused_suite=None) -> dict:
    """Assemble the lock from proofs, never from assertions."""
    root = Path(root or REPO_ROOT).resolve()

    if not _DIGEST.fullmatch(str(image_digest or "")):
        raise LockDefect("the image digest must be a pinned sha256 digest")
    if not _DIGEST.fullmatch(str(base_digest or "")):
        raise LockDefect("the base image digest must be a pinned sha256 digest")
    for name, value in (("executable_commit", executable_commit),
                        ("anchor_parent", anchor_parent)):
        if not _SHA1.fullmatch(str(value or "")):
            raise LockDefect("%s must be a full 40-character commit id" % name)

    executable_tree = _git(root, "rev-parse", executable_commit + "^{tree}")
    task_blob = _git(root, "rev-parse",
                     "%s:%s" % (executable_commit, TASK_PATH))

    manifest = image_manifest if image_manifest is not None \
        else IMAGE.build(root, commit=executable_commit)
    if manifest.get("executable_commit") != executable_commit:
        raise LockDefect(
            "the image manifest was built at %s, not the executable commit %s"
            % (manifest.get("executable_commit"), executable_commit))

    delegated = [
        {"path": entry["path"], "bytes": entry["bytes"],
         "sha256": entry["sha256"], "git_blob": entry["git_blob"]}
        for entry in manifest["entries"] if entry["kind"] == "scientific"]
    if not delegated:
        raise LockDefect("the lock must bind the delegated scientific modules")

    if not isinstance(canaries, dict) or not canaries:
        raise LockDefect(
            "the lock is issuable only against recorded model-free canary "
            "evidence")
    failed = sorted(name for name, entry in canaries.items()
                    if not isinstance(entry, dict)
                    or entry.get("outcome") != "PASS")
    if failed:
        raise LockDefect(
            "these canaries did not pass: %s" % ", ".join(failed))
    packing = canaries.get("packing_canary") or {}
    if not packing.get("run_id"):
        raise LockDefect(
            "the designated final packing canary must record exactly one ACR "
            "run id")

    document = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "terminal_state": TERMINAL_STATE,
        "kind": "infrastructure-successor",
        "changes_only": "host-to-registry submission transport",
        "science_is_unchanged_p0_r1_generation3": True,

        "executable_code": {
            "commit": executable_commit,
            "tree": executable_tree,
        },
        "transport": {
            "task_path": TASK_PATH,
            "task_blob": task_blob,
            "envelope_version": TX.ENVELOPE_VERSION,
            "attempt_id_prefix": TX.ATTEMPT_ID_PREFIX,
            "raw_chunk_bytes": TX.RAW_CHUNK_BYTES,
            "max_line_bytes": TX.MAX_LINE_BYTES,
            "max_projected_combined_replay_artifact_bytes":
                TX.MAX_PROJECTED_COMBINED_REPLAY_ARTIFACT_BYTES,
            "canary_minimum_total_bytes": TX.CANARY_MINIMUM_TOTAL_BYTES,
            "replay_artifacts": list(TX.REPLAY_ARTIFACTS),
        },
        "image": {
            "registry": REGISTRY,
            "repository": REPOSITORY,
            "digest": image_digest,
            "base_digest": base_digest,
            "reference": "%s/%s@%s" % (REGISTRY, REPOSITORY, image_digest),
            "build_run_id": build_run_id,
            "manifest_entries_sha256": manifest["entries_sha256"],
            "image_root": manifest["image_root"],
        },
        "ready_commit_relationship": {
            "anchor_parent": anchor_parent,
            "anchor_contains_this_lock": True,
            "anchor_is_proved_by_ancestry_not_self_reference": True,
            "governance_source": governance_source,
            "published_head": published_head,
        },
        "immutable_sources": {
            "immutable_binding_keys": list(CLOSURE.IMMUTABLE_BINDING_KEYS),
            "governance_allowlist": list(CLOSURE.GOVERNANCE_ALLOWLIST),
            "governance_allowlist_prefixes":
                list(CLOSURE.GOVERNANCE_ALLOWLIST_PREFIXES),
        },
        "delegated_scientific_modules": delegated,
        "azure": {
            "subscription_id": SUBSCRIPTION,
            "tenant_id": TENANT,
            "resource_group": RESOURCE_GROUP,
            "registry_name": REGISTRY_NAME,
            "container_apps_environment": ACA_ENVIRONMENT,
            "managed_identity": MANAGED_IDENTITY,
            "log_analytics_workspace": LOG_ANALYTICS_WORKSPACE,
        },
        "namespace": {
            "attempt_prefix": TX.ATTEMPT_ID_PREFIX,
            "gpu_job": GPU_JOB,
            "recovery_job": RECOVERY_JOB,
            "blob_prefix_root": BLOB.PREFIX_ROOT + "/",
            "results_path": RESULTS_PATH,
        },
        "caps": dict(RUNNER.CAPS),
        "canaries": canaries,
        "validation": {
            "focused_suite": focused_suite,
            "full_suite": full_suite,
        },
        "predecessor": {
            "study": "study3-p0-r1",
            "stop_commit": P0_R1_STOP_COMMIT,
            "stop_state": P0_R1_STOP_STATE,
            "bytes_modified_by_p0_r2": 0,
            "reopened": False,
        },
        "prohibitions": {
            "live_replay_run": False,
            "replay_envelope_consumed": False,
            "tokenizer_constructed": False,
            "checkpoint_downloaded_or_loaded": False,
            "model_weight_loaded": False,
            "prefill_or_generation_performed": False,
            "gpu_job_created_or_started": False,
            "evidence_ledger_row_added": False,
        },
        "counters": {
            "tokenizer_constructions": 0,
            "checkpoint_downloads": 0,
            "model_weight_loads": 0,
            "prefills": 0,
            "generations": 0,
            "scored_rows": 0,
            "evidence_rows_added": 0,
            "gpu_allocations": 0,
            "gpu_jobs_created": 0,
            "gpu_jobs_started": 0,
            "model_operations_performed": 0,
        },
    }
    return document


def verify(document, *, root=None) -> dict:
    """Re-derive every checkable claim in an issued lock."""
    root = Path(root or REPO_ROOT).resolve()
    if not isinstance(document, dict) \
            or document.get("schema_version") != SCHEMA_VERSION:
        raise LockDefect("this is not a P0-R2 generation-1 execution lock")

    executable = document.get("executable_code") or {}
    commit = executable.get("commit")
    if _git(root, "rev-parse", str(commit) + "^{tree}") != executable.get("tree"):
        raise LockDefect("the locked executable tree is not that commit's tree")

    transport = document.get("transport") or {}
    actual_blob = _git(root, "rev-parse",
                       "%s:%s" % (commit, transport.get("task_path")))
    if actual_blob != transport.get("task_blob"):
        raise LockDefect(
            "the locked task blob is not the blob stored at %s in %s"
            % (transport.get("task_path"), str(commit)[:12]))

    for entry in document.get("delegated_scientific_modules") or []:
        blob = _git(root, "rev-parse", "%s:%s" % (commit, entry["path"]))
        if blob != entry.get("git_blob"):
            raise LockDefect(
                "%s does not carry the locked blob at the executable commit"
                % entry["path"])

    counters = document.get("counters") or {}
    nonzero = sorted(name for name, value in counters.items() if value != 0)
    if nonzero:
        raise LockDefect(
            "a preparation-round lock must carry all-zero counters; %s is not "
            "zero" % ", ".join(nonzero))
    return {
        "schema_version": SCHEMA_VERSION,
        "outcome": "LOCK_VERIFIED",
        "executable_commit": commit,
        "executable_tree": executable.get("tree"),
        "task_blob": transport.get("task_blob"),
        "image_digest": (document.get("image") or {}).get("digest"),
        "delegated_module_count":
            len(document.get("delegated_scientific_modules") or []),
        "terminal_state": document.get("terminal_state"),
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_execution_lock_v1.py",
        "stage": STAGE,
        "generation": GENERATION,
        "lock_name": LOCK_NAME,
        "schema_name": SCHEMA_NAME,
        "terminal_state": TERMINAL_STATE,
        "contains_own_hash": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify")
    parser.add_argument("--root")
    parser.add_argument("--executable-commit")
    parser.add_argument("--image-digest")
    parser.add_argument("--base-digest")
    parser.add_argument("--anchor-parent")
    parser.add_argument("--build-run-id")
    parser.add_argument("--canaries")
    parser.add_argument("--governance-source")
    parser.add_argument("--published-head")
    parser.add_argument("--focused-suite")
    parser.add_argument("--full-suite")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    def _load(path):
        return json.loads(Path(path).read_text(encoding="utf-8")) \
            if path else None

    try:
        if args.identity:
            print(json.dumps(implementation_identity(), indent=2,
                             sort_keys=True))
            return 0
        if args.verify:
            document = json.loads(
                Path(args.verify).read_text(encoding="utf-8"))
            report = verify(document, root=args.root)
            print(json.dumps(report, indent=2, sort_keys=True))
            print("P0_R2_LOCK_VERIFIED=1")
            return 0
        document = build(
            root=args.root, executable_commit=args.executable_commit,
            image_digest=args.image_digest, base_digest=args.base_digest,
            anchor_parent=args.anchor_parent, build_run_id=args.build_run_id,
            canaries=_load(args.canaries) or {},
            governance_source=args.governance_source,
            published_head=args.published_head,
            focused_suite=_load(args.focused_suite),
            full_suite=_load(args.full_suite))
    except LockDefect as exc:
        print("P0_R2_LOCK_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    payload = canonical_bytes(document)
    if args.out:
        Path(args.out).write_bytes(payload)
    sys.stdout.write(payload.decode("utf-8"))
    print("P0_R2_LOCK_SHA256=%s" % _sha256(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
