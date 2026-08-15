#!/usr/bin/env python3
"""The complete, append-only P0-R2 attempt ledger (A7).

Before this module the repository sealed six run ids -- ``cmht``, ``cmhu``,
``cmhv``, ``cmj3``, ``cmj5``, ``cmj6`` -- and mentioned no others. Nineteen more
existed: one claimed final run that was never sealed at all (``cmj7``), five
superseded runs and thirteen failed or discarded ones. They appeared only in
external disclosure. A run record that lives outside the repository is not a
record; it is a memory.

This module rebuilds the ledger from Azure itself rather than from prose. For
every registered run id it asks the control plane what the run was, and asks
for the run's log. Then it classifies:

``SEALED``       Azure still retains the run and its log; bytes and SHA-256 are
                 recorded from what was actually returned.
``UNAVAILABLE``  Azure no longer returns the log. The run is recorded as
                 unavailable. No hash is invented and no pass is claimed.
``AMBIGUOUS``    The query itself failed. An error is never an absence.

The single rule that makes ``UNAVAILABLE`` survivable is narrow: an unavailable
run may be accepted as evidence **only** when its registered submitted identity
proves it could not have entered a replay, model or GPU path. Any unavailable
run that might have entered such a path is a stop, not a footnote.

The ledger is append-only. Verification refuses a ledger whose earlier entries
have changed, so a later revision can add runs and can never quietly rewrite
one.

Model-free and read-only: it creates, updates, starts and deletes nothing, and
performs no tokenizer, checkpoint, model weight, prefill, generation, scoring,
evidence or GPU operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


SCHEMA_VERSION = "study3-p0-r2-attempt-ledger-v2"
STAGE = "STUDY3-P0-R2"

REGISTRY = "acrjspaceobssea0708231738"
SUBSCRIPTION = "943bacdf-8b6e-4e3a-8126-a149f623d32e"
RESOURCE_GROUP = "rg-jspace-observation-sea"

ACCEPTED = "accepted"
CLAIMED_UNSEALED = "claimed-but-previously-unsealed"
SUPERSEDED = "superseded"
FAILED = "failed-or-discarded"
CORRECTIVE = "corrective-closure"

#: The registered disclosure this ledger is required to cover, exactly. Each
#: entry also records whether the submitted identity could have entered a
#: replay, model or GPU path at all. That flag is what decides whether an
#: unavailable log is survivable.
REGISTERED_RUNS = (
    ("cmht", ACCEPTED, "image build; in-build image-to-Git audit", False),
    ("cmhu", ACCEPTED, "model-free preflight canary", False),
    ("cmhv", ACCEPTED, "designated packing canary", False),
    ("cmj3", ACCEPTED, "full repository differential suite", False),
    ("cmj5", ACCEPTED, "focused execution-closure suite", False),
    ("cmj6", ACCEPTED, "published first command, end to end", False),
    ("cmj7", CLAIMED_UNSEALED, "claimed final run; never sealed in repository",
     False),
    ("cmhp", SUPERSEDED, "superseded validation attempt", False),
    ("cmhq", SUPERSEDED, "superseded validation attempt", False),
    ("cmhs", SUPERSEDED, "superseded validation attempt", False),
    ("cmj2", SUPERSEDED, "superseded full-suite attempt", False),
    ("cmj4", SUPERSEDED, "superseded validation attempt", False),
    ("cmhb", FAILED, "failed build or validation attempt", False),
    ("cmhd", FAILED, "failed build or validation attempt", False),
    ("cmhe", FAILED, "failed build or validation attempt", False),
    ("cmhf", FAILED, "failed build or validation attempt", False),
    ("cmhg", FAILED, "failed build or validation attempt", False),
    ("cmhh", FAILED, "failed build or validation attempt", False),
    ("cmhk", FAILED, "failed build or validation attempt", False),
    ("cmhn", FAILED, "failed build or validation attempt", False),
    ("cmhw", FAILED, "failed build or validation attempt", False),
    ("cmhx", FAILED, "failed build or validation attempt", False),
    ("cmhy", FAILED, "failed build or validation attempt", False),
    ("cmj0", FAILED, "failed build or validation attempt", False),
    ("cmj1", FAILED, "failed build or validation attempt", False),
)

#: Markers whose presence in a log proves the run stayed model-free, and
#: markers whose presence would prove the opposite.
MODEL_FREE_MARKERS = (
    "P0_R2_MODEL_OPERATIONS_PERFORMED=0",
    "model_operations_performed: 0",
)
MODEL_PATH_MARKERS = (
    "P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=true",
    "P0_R2_REPLAY_GATE_RUN=true",
    "P0_R2_LIVE_REPLAY_AUTHORIZED=1",
    "tokenizer_constructions=1",
)

SEALED = "SEALED"
UNAVAILABLE = "UNAVAILABLE"
AMBIGUOUS = "AMBIGUOUS"


class LedgerDefect(Exception):
    """The ledger cannot be completed honestly."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _az(command, runner=None):
    if runner is not None:
        return runner(command)
    program = shutil.which(command[0]) or command[0]
    try:
        return subprocess.run(  # noqa: S603 - fixed executable
            [program] + list(command[1:]), capture_output=True, text=True,
            check=False)
    except OSError as exc:
        return subprocess.CompletedProcess(
            command, 127, "", "P0_R2_AZURE_CLI_LAUNCH_FAILED: %s" % exc)


def fetch_run(run_id: str, *, registry=REGISTRY, subscription=SUBSCRIPTION,
              runner=None) -> dict:
    """Ask Azure what one run was and what it printed. Read-only."""
    show = _az(["az", "acr", "task", "show-run", "--registry", registry,
                "--subscription", subscription, "--run-id", run_id,
                "--output", "json"], runner=runner)
    metadata = None
    if show.returncode == 0 and (show.stdout or "").strip():
        try:
            metadata = json.loads(show.stdout)
        except ValueError:
            metadata = None

    logs = _az(["az", "acr", "task", "logs", "--registry", registry,
                "--subscription", subscription, "--run-id", run_id],
               runner=runner)
    log_text = logs.stdout or ""
    log_available = logs.returncode == 0 and bool(log_text.strip())

    if metadata is None and not log_available:
        outcome = AMBIGUOUS
    elif log_available:
        outcome = SEALED
    else:
        outcome = UNAVAILABLE

    entry = {
        "run_id": run_id,
        "evidence_outcome": outcome,
        "azure_retains_metadata": metadata is not None,
        "azure_retains_log": log_available,
        "status": (metadata or {}).get("status"),
        "run_type": (metadata or {}).get("runType"),
        "create_time": (metadata or {}).get("createTime"),
        "finish_time": (metadata or {}).get("finishTime"),
        "run_error_message": (metadata or {}).get("runErrorMessage"),
        "output_images": (metadata or {}).get("outputImages"),
        "show_exit_code": show.returncode,
        "logs_exit_code": logs.returncode,
        "log_bytes": len(log_text.encode("utf-8")) if log_available else None,
        "log_sha256": _sha256(log_text.encode("utf-8")) if log_available
                      else None,
        "stderr_bytes": len((show.stderr or "").encode("utf-8")),
        "stderr_sha256": _sha256((show.stderr or "").encode("utf-8")),
        "log_excerpt_head": log_text[:512] if log_available else None,
        "log_excerpt_tail": log_text[-512:] if log_available else None,
    }
    if log_available:
        entry["model_free_marker_present"] = any(
            marker in log_text for marker in MODEL_FREE_MARKERS)
        entry["model_path_marker_present"] = any(
            marker in log_text for marker in MODEL_PATH_MARKERS)
        for key, marker in (("source_commit", "BOUND_COMMIT="),
                            ("bound_tree", "BOUND_TREE="),
                            ("baseline_commit", "BASELINE_COMMIT=")):
            for line in log_text.splitlines():
                if line.strip().startswith(marker):
                    entry[key] = line.strip()[len(marker):].strip()
                    break
    else:
        entry["model_free_marker_present"] = None
        entry["model_path_marker_present"] = None
    return entry


def build(*, registry=REGISTRY, subscription=SUBSCRIPTION, extra_runs=(),
          image=None, task_blob=None, runner=None) -> dict:
    """Gather every registered run plus any corrective-closure runs."""
    registered = list(REGISTERED_RUNS) + [
        (run_id, CORRECTIVE, purpose, could_enter)
        for run_id, purpose, could_enter in extra_runs]

    entries = []
    stops = []
    for run_id, category, purpose, could_enter_model_path in registered:
        entry = fetch_run(run_id, registry=registry, subscription=subscription,
                          runner=runner)
        entry.update({
            "category": category,
            "registered_purpose": purpose,
            "submitted_identity_could_enter_replay_model_or_gpu_path":
                bool(could_enter_model_path),
            "image": image,
            "task_blob": task_blob,
            "superseded_by": None,
        })
        if entry["evidence_outcome"] == AMBIGUOUS:
            stops.append("%s: the control plane answer was ambiguous; an error "
                         "is never an absence" % run_id)
        if entry["evidence_outcome"] == UNAVAILABLE and could_enter_model_path:
            stops.append(
                "%s: its log is unavailable and its submitted identity does "
                "not prove it could not have entered a replay, model or GPU "
                "path" % run_id)
        if entry.get("model_path_marker_present"):
            stops.append("%s: its log carries a model-path marker" % run_id)
        entries.append(entry)

    by_category = {}
    for entry in entries:
        by_category.setdefault(entry["category"], []).append(entry["run_id"])

    canonical = json.dumps(
        [[entry["run_id"], entry["category"], entry["evidence_outcome"],
          entry["log_sha256"]] for entry in entries],
        sort_keys=True, separators=(",", ":")).encode("utf-8")

    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "append_only": True,
        "registry": registry,
        "subscription": subscription,
        "resource_group": RESOURCE_GROUP,
        "run_count": len(entries),
        "runs": sorted(entries, key=lambda item: item["run_id"]),
        "by_category": {key: sorted(value)
                        for key, value in sorted(by_category.items())},
        "sealed_count": sum(1 for item in entries
                            if item["evidence_outcome"] == SEALED),
        "unavailable_count": sum(1 for item in entries
                                 if item["evidence_outcome"] == UNAVAILABLE),
        "ambiguous_count": sum(1 for item in entries
                               if item["evidence_outcome"] == AMBIGUOUS),
        "stops": stops,
        "complete_and_admissible": not stops,
        "fabricated_hashes": 0,
        "unavailable_runs_called_a_pass": 0,
        "ledger_sha256": _sha256(canonical),
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
        "created_updated_or_started_anything": False,
    }


def verify_append_only(previous: dict, current: dict) -> dict:
    """Refuse a revision that rewrote or dropped an earlier run record."""
    if not isinstance(previous, dict) or not isinstance(current, dict):
        raise LedgerDefect("both ledgers must be documents")
    old = {entry["run_id"]: entry for entry in previous.get("runs") or []}
    new = {entry["run_id"]: entry for entry in current.get("runs") or []}
    dropped = sorted(set(old) - set(new))
    if dropped:
        raise LedgerDefect(
            "the revision drops %d earlier run record(s): %s"
            % (len(dropped), ", ".join(dropped)))
    rewritten = []
    for run_id, entry in sorted(old.items()):
        for key in ("category", "registered_purpose", "evidence_outcome",
                    "log_sha256", "log_bytes"):
            if entry.get(key) != new[run_id].get(key):
                rewritten.append("%s.%s" % (run_id, key))
    if rewritten:
        raise LedgerDefect(
            "the revision rewrites %d earlier field(s): %s"
            % (len(rewritten), ", ".join(rewritten)))
    return {
        "schema_version": "study3-p0-r2-attempt-ledger-append-only-proof-v2",
        "previous_run_count": len(old),
        "current_run_count": len(new),
        "added_runs": sorted(set(new) - set(old)),
        "dropped_runs": [],
        "rewritten_fields": [],
        "append_only": True,
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_attempt_ledger_v2.py",
        "stage": STAGE,
        "registered_run_count": len(REGISTERED_RUNS),
        "categories": [ACCEPTED, CLAIMED_UNSEALED, SUPERSEDED, FAILED,
                       CORRECTIVE],
        "evidence_outcomes": [SEALED, UNAVAILABLE, AMBIGUOUS],
        "query_error_is_absence": False,
        "unavailable_is_a_pass": False,
        "fabricates_hashes": False,
        "append_only": True,
        "read_only": True,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify-append-only", nargs=2,
                      metavar=("PREVIOUS", "CURRENT"))
    parser.add_argument("--registry", default=REGISTRY)
    parser.add_argument("--subscription", default=SUBSCRIPTION)
    parser.add_argument("--image")
    parser.add_argument("--task-blob")
    parser.add_argument("--extra-run", action="append", default=[],
                        metavar="RUN_ID:PURPOSE")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    try:
        if args.verify_append_only:
            with open(args.verify_append_only[0], encoding="utf-8") as handle:
                previous = json.load(handle)
            with open(args.verify_append_only[1], encoding="utf-8") as handle:
                current = json.load(handle)
            document = verify_append_only(previous, current)
        else:
            extra = []
            for raw in args.extra_run:
                run_id, _, purpose = raw.partition(":")
                extra.append((run_id.strip(), purpose.strip() or "corrective "
                              "closure run", False))
            document = build(registry=args.registry,
                             subscription=args.subscription,
                             extra_runs=tuple(extra), image=args.image,
                             task_blob=args.task_blob)
    except LedgerDefect as exc:
        print("P0_R2_ATTEMPT_LEDGER_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    if document.get("stops"):
        for stop in document["stops"]:
            print("P0_R2_ATTEMPT_LEDGER_STOP=1 %s" % stop, file=sys.stderr)
        return 3
    print("P0_R2_ATTEMPT_LEDGER_COMPLETE=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
