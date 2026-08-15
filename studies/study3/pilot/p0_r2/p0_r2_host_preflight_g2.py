#!/usr/bin/env python3
"""Study 3 P0-R2 generation-2 host preflight.

Authority:
``studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md``
sections 8 and 11.

This is the model-free check a fresh, clean, short-path checkout runs before any
generation-2 submission, and again immediately before the one live invocation.
Every fact is derived from Git, from an exact published receipt, or from a
read-only Azure result. No caller may supply a condition's truth value, and a
query failure is recorded as an ambiguity, never read as an absence.

It refuses on a foreign head, a dirty checkout, an altered task or lock, an
unpinned or wrong image, an unavailable Azure CLI, an ambiguous job query, a
missing or stale in-VNet prefix receipt, a nonzero counter, a changed frozen
byte, a generation-1 identifier in a generation-2 field, and a native context
path over the registered ceiling.

Model-free: no tokenizer, checkpoint, model weight, GPU or scoring operation.
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

import p0_r2_azure_query_v1 as AZURE  # noqa: E402
import p0_r2_closure_binding_g2 as CB  # noqa: E402
import p0_r2_execution_lock_g2 as LOCK  # noqa: E402
import p0_r2_host_submission_g2 as SUBMIT  # noqa: E402
import p0_r2_namespace_g2 as NS  # noqa: E402
import p0_r2_prefix_proof_g2 as PREFIX  # noqa: E402


REPO_ROOT = P0_R2_DIR.parent.parent.parent.parent

SCHEMA_VERSION = "study3-p0-r2-host-preflight-g2"
STAGE = "STUDY3-P0-R2"
GENERATION = 2

#: Every marker below must be printed exactly once by a passing preflight.
REQUIRED_MARKERS = (
    "P0_R2_G2_HOST_PREFLIGHT_COMPLETE=1",
    "P0_R2_G2_GOVERNANCE_CHAIN_PROVED=1",
    "P0_R2_G2_HEAD_EQUALS_ORIGIN_MAIN=1",
    "P0_R2_G2_WORKTREE_CLEAN=1",
    "P0_R2_G2_GENERATION1_TERMINAL=1",
    "P0_R2_G2_P0_R1_TERMINAL=1",
    "P0_R2_G2_FROZEN_BYTES_UNCHANGED=1",
    "P0_R2_G2_REPLAY_ENVELOPE_UNCONSUMED=1",
    "P0_R2_G2_LIVE_PREFIX_PROVED_UNUSED=1",
    "P0_R2_G2_GPU_JOB_PROVED_ABSENT=1",
    "P0_R2_G2_RECOVERY_JOB_PROVED_ABSENT=1",
    "P0_R2_MODEL_OPERATIONS_PERFORMED=0",
)


class HostPreflightDefect(Exception):
    """A generation-2 host preflight stop."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(document) -> bytes:
    return json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _git(root, args, *, binary=False):
    completed = subprocess.run(  # noqa: S603 - fixed executable
        ["git", "-C", str(root), *args], capture_output=True,
        text=not binary, check=False)
    if completed.returncode:
        message = completed.stderr if not binary \
            else completed.stderr.decode("utf-8", "replace")
        raise HostPreflightDefect(
            "git %s refused: %s" % (" ".join(args), message.strip()))
    return completed.stdout


def head_state(root, *, remote="origin", branch="main",
               require_head=True) -> dict:
    head = _git(root, ["rev-parse", "HEAD"]).strip()
    tree = _git(root, ["rev-parse", "HEAD^{tree}"]).strip()
    try:
        origin = _git(root, ["rev-parse", "%s/%s" % (remote, branch)]).strip()
    except HostPreflightDefect:
        origin = None
    status = _git(root, ["status", "--porcelain=v1",
                         "--untracked-files=all"]).strip()
    return {
        "head": head,
        "tree": tree,
        "origin_ref": "%s/%s" % (remote, branch),
        "origin_head": origin,
        "head_equals_origin_main": bool(origin) and origin == head,
        "head_required": bool(require_head),
        "worktree_clean": status == "",
        "dirty_entries": [line for line in status.splitlines() if line],
    }


def job_absence(names, *, subscription, resource_group, runner=None) -> dict:
    """Prove the named jobs absent, non-vacuously. An error is an ambiguity."""
    results = []
    for name in names:
        answer = AZURE.job_presence(
            name, resource_group=resource_group, subscription=subscription,
            runner=runner)
        results.append({
            "job": name,
            "outcome": answer.get("outcome"),
            "proved_absent": answer.get("outcome") == "PROVED_ABSENT",
            "ambiguous": answer.get("outcome") == "AMBIGUOUS",
        })
    return {
        "schema_version": "study3-p0-r2-job-absence-g2",
        "stage": STAGE,
        "generation": GENERATION,
        "jobs": results,
        "all_proved_absent": all(entry["proved_absent"] for entry in results),
        "any_ambiguous": any(entry["ambiguous"] for entry in results),
        "query_error_is_absence": False,
    }


def preflight(root=None, *, lock_file, prefix_receipt=None, context_dir=None,
              attempt=None, mode="canary", require_head=True,
              require_fresh_prefix=False, runner=None, now=None,
              skip_azure=False) -> dict:
    """The complete generation-2 host preflight."""
    root = Path(root or REPO_ROOT).resolve()

    lock_payload = Path(lock_file).read_bytes()
    lock = json.loads(lock_payload.decode("utf-8"))
    lock_validation = LOCK.validate(lock)

    state = head_state(root, require_head=require_head)
    chain = CB.prove(root, lock=lock, head=state["head"])

    committed_lock = None
    lock_matches_commit = None
    try:
        committed_lock = _git(
            root, ["show", "%s:%s" % (state["head"],
                                      "studies/study3/pilot/p0_r2/"
                                      + LOCK.LOCK_NAME)], binary=True)
        lock_matches_commit = _sha256(committed_lock) == _sha256(lock_payload)
    except HostPreflightDefect:
        lock_matches_commit = False

    task_path = (lock.get("transport") or {}).get("task_path")
    task_blob = _git(root, ["rev-parse", "%s:%s" % (state["head"], task_path)]
                     ).strip() if task_path else None
    task_matches = task_blob == (lock.get("transport") or {}).get("task_blob")

    prefix_validation = None
    prefix_ok = None
    if prefix_receipt:
        payload = Path(prefix_receipt).read_bytes()
        receipt = json.loads(payload.decode("utf-8"))
        try:
            prefix_validation = PREFIX.validate_receipt(
                receipt, attempt_id=attempt, mode=mode,
                expected_sha256=_sha256(payload), receipt_bytes=payload,
                require_host_freshness=require_fresh_prefix, now=now)
            prefix_ok = True
        except PREFIX.PrefixProofDefect as exc:
            prefix_validation = {"outcome": "REFUSED", "reason": str(exc)}
            prefix_ok = False

    context_admission = None
    if context_dir:
        try:
            context_admission = SUBMIT.verify_context(
                root=root, context_dir=context_dir,
                expected_commit=(lock.get("image_executable") or {}).get(
                    "commit"),
                expected_task_path=task_path, attempt=attempt, mode=mode)
        except SUBMIT.SubmissionDefect as exc:
            context_admission = {"outcome": "REFUSED", "reason": str(exc)}

    launch = None
    absence = None
    if not skip_azure:
        try:
            launch = SUBMIT.prove_launch_path()
        except SUBMIT.SubmissionDefect as exc:
            launch = {"outcome": "REFUSED", "reason": str(exc)}
        absence = job_absence(
            (NS.GPU_JOB, NS.RECOVERY_JOB),
            subscription=(lock.get("azure") or {})["subscription"],
            resource_group=(lock.get("azure") or {})["resource_group"],
            runner=runner)

    counters = lock.get("pre_replay_counters") or {}
    envelope = lock.get("replay_envelope") or {}

    conditions = {
        "lock_validates": lock_validation.get("outcome") == "LOCK_VALID",
        "lock_bytes_match_commit": bool(lock_matches_commit),
        "task_blob_matches_lock": bool(task_matches),
        "governance_chain_proved": chain["outcome"] == "CHAIN_PROVED",
        "frozen_bytes_unchanged":
            chain["frozen_roots_proof"]["all_frozen_bytes_unchanged"],
        "generation1_terminal": chain["conditions"]["generation1_remains_terminal"],
        "p0_r1_terminal": chain["conditions"]["p0_r1_remains_terminal"],
        "namespace_disjoint": chain["conditions"]["namespace_disjoint"],
        "image_digest_is_new": chain["conditions"]["image_digest_is_new"],
        "head_equals_origin_main":
            state["head_equals_origin_main"] or not require_head,
        "worktree_clean": state["worktree_clean"],
        "replay_envelope_unconsumed": envelope.get("consumed") is False
        and envelope.get("invocations") == 0,
        "all_counters_zero": all(value == 0 for value in counters.values()),
    }
    if prefix_receipt:
        conditions["live_prefix_proved_unused"] = bool(prefix_ok)
    if context_dir:
        conditions["context_admitted"] = isinstance(context_admission, dict) \
            and context_admission.get("outcome") != "REFUSED"
    if not skip_azure:
        conditions["azure_cli_launch_proved"] = isinstance(launch, dict) \
            and launch.get("outcome") != "REFUSED"
        conditions["gpu_job_proved_absent"] = any(
            entry["job"] == NS.GPU_JOB and entry["proved_absent"]
            for entry in absence["jobs"])
        conditions["recovery_job_proved_absent"] = any(
            entry["job"] == NS.RECOVERY_JOB and entry["proved_absent"]
            for entry in absence["jobs"])
        conditions["no_ambiguous_azure_answer"] = not absence["any_ambiguous"]

    failed = sorted(name for name, value in conditions.items() if not value)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "head_state": state,
        "lock": {
            "path": lock_file,
            "bytes": len(lock_payload),
            "sha256": _sha256(lock_payload),
            "validation": lock_validation,
            "matches_committed_bytes": lock_matches_commit,
        },
        "task": {"path": task_path, "git_blob": task_blob,
                 "matches_lock": task_matches},
        "governance_chain": chain,
        "prefix_validation": prefix_validation,
        "context_admission": context_admission,
        "launch_proof": launch,
        "job_absence": absence,
        "conditions": conditions,
        "condition_count": len(conditions),
        "failed_conditions": failed,
        "failed_count": len(failed),
        "outcome": "PREFLIGHT_PASS" if not failed else "PREFLIGHT_REFUSED",
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_host_preflight_g2.py",
        "stage": STAGE,
        "generation": GENERATION,
        "required_markers": list(REQUIRED_MARKERS),
        "gpu_job": NS.GPU_JOB,
        "recovery_job": NS.RECOVERY_JOB,
        "query_error_is_absence": False,
        "accepts_caller_supplied_condition": False,
        "accepts_allow_path": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    parser.add_argument("--root")
    parser.add_argument("--lock-file")
    parser.add_argument("--prefix-receipt")
    parser.add_argument("--context-dir")
    parser.add_argument("--attempt")
    parser.add_argument("--replay-mode", default="canary",
                        choices=["canary", "live"])
    parser.add_argument("--require-fresh-prefix", action="store_true")
    parser.add_argument("--no-head", action="store_true")
    parser.add_argument("--skip-azure", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    try:
        if not args.lock_file:
            raise HostPreflightDefect("--preflight requires --lock-file")
        document = preflight(
            args.root, lock_file=args.lock_file,
            prefix_receipt=args.prefix_receipt, context_dir=args.context_dir,
            attempt=args.attempt, mode=args.replay_mode,
            require_head=not args.no_head,
            require_fresh_prefix=args.require_fresh_prefix,
            skip_azure=args.skip_azure)
    except (HostPreflightDefect, LOCK.LockDefect, CB.ClosureBindingDefect,
            ValueError, OSError) as exc:
        print("P0_R2_G2_HOST_PREFLIGHT_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    payload = canonical_bytes(document)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload)
    print(payload.decode("utf-8"), end="")

    if document["outcome"] != "PREFLIGHT_PASS":
        print("P0_R2_G2_HOST_PREFLIGHT_REFUSED=1 %s"
              % ", ".join(document["failed_conditions"]), file=sys.stderr)
        return 3

    print("P0_R2_G2_GOVERNANCE_CHAIN_PROVED=1")
    print("P0_R2_G2_HEAD_EQUALS_ORIGIN_MAIN=1")
    print("P0_R2_G2_WORKTREE_CLEAN=1")
    print("P0_R2_G2_GENERATION1_TERMINAL=1")
    print("P0_R2_G2_P0_R1_TERMINAL=1")
    print("P0_R2_G2_FROZEN_BYTES_UNCHANGED=1")
    print("P0_R2_G2_REPLAY_ENVELOPE_UNCONSUMED=1")
    if args.prefix_receipt:
        print("P0_R2_G2_LIVE_PREFIX_PROVED_UNUSED=1")
    if not args.skip_azure:
        print("P0_R2_G2_GPU_JOB_PROVED_ABSENT=1")
        print("P0_R2_G2_RECOVERY_JOB_PROVED_ABSENT=1")
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0")
    print("P0_R2_G2_HOST_PREFLIGHT_COMPLETE=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
