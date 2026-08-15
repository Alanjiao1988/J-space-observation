#!/usr/bin/env python3
"""The P0-R2 model-runner wrapper. It refuses by default.

This module is the only P0-R2 code path that could ever reach a model, and its
entire job is to make that path impossible to enter by accident. It is
published, tested and shipped in the image in this preparation round precisely
so that a future session does not have to write it under time pressure while
holding a one-shot envelope.

Two executors exist:

``sentinel_executor``
    the default. Performs zero model work, emits the sentinel line, and returns
    a document that explicitly authorizes nothing. Every test and canary uses
    this path.

``production_executor``
    delegates to the unchanged P0-R1 generation-3 runner. It is reachable only
    when a built authorization document, the exact bound scientific bytes, and
    an explicit accelerator requirement are all present at once. Any missing
    piece raises before a tokenizer, checkpoint, weight, or GPU is touched.

Nothing in this module constructs a tokenizer, downloads or loads a checkpoint,
loads a model weight, performs a prefill or generation, scores a row, or writes
an evidence row. Those all live behind ``production_executor``'s refusals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


P0_R2_DIR = Path(__file__).resolve().parent
P0_R1_DIR = P0_R2_DIR.parent / "p0_r1"
for _candidate in (P0_R2_DIR, P0_R1_DIR):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

import p0_r2_replay_gate_v1 as GATE  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-model-runner-v1"
STAGE = "STUDY3-P0-R2"
SENTINEL_LINE = "P0_R2_MODEL_RUNNER_SENTINEL_REACHED=1"
GPU_JOB = "job-jspace-s3-p0r2-pilot-g1"

#: The exact caps this stage may never exceed. Copied nowhere else; the lock
#: binds the same numbers and the runner refuses if they disagree.
CAPS = {
    "max_smoke_prefills_before_extension": 60,
    "max_non_generative_prefills": 180,
    "max_s4_generations": 12,
    "max_model_evaluation_equivalents": 228,
    "possible_scored_rows": 210,
}

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class ModelRunnerRefused(Exception):
    """The runner refuses; no model operation is performed."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sentinel_executor(context, stream=None) -> dict:
    """Do no model work at all and say so in a machine-checkable way."""
    target = stream if stream is not None else sys.stdout
    print(SENTINEL_LINE, file=target)
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0", file=target)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "executor": "sentinel",
        "attempt_id": (context or {}).get("attempt_id"),
        "sentinel_reached": True,
        "caps": dict(CAPS),
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
        "model_operations_performed": 0,
        "authorizes_anything": False,
    }


def require_production_preconditions(*, authorization, lock, root=None,
                                     accelerator_required=False) -> dict:
    """Every precondition for touching a model, checked before touching one."""
    if not accelerator_required:
        raise ModelRunnerRefused(
            "the production executor requires an explicit accelerator "
            "requirement; a CPU replica never runs the model half")
    if not isinstance(authorization, dict) \
            or authorization.get("outcome") != "AUTHORIZED":
        raise ModelRunnerRefused(
            "a built pilot authorization is required before any model "
            "operation")
    if not isinstance(lock, dict):
        raise ModelRunnerRefused("the execution lock is required")
    digest = (lock.get("image") or {}).get("digest")
    if not _DIGEST.fullmatch(str(digest or "")):
        raise ModelRunnerRefused("the lock does not bind a pinned digest")
    if authorization.get("image_digest") != digest:
        raise ModelRunnerRefused(
            "the authorization digest does not match the locked digest")
    caps = lock.get("caps") or {}
    mismatched = sorted(name for name, value in CAPS.items()
                        if caps.get(name) != value)
    if mismatched:
        raise ModelRunnerRefused(
            "the lock caps disagree with the registered maxima for %s; the "
            "bounded pilot may not run under changed caps"
            % ", ".join(mismatched))
    bound = {entry["path"]: entry
             for entry in (lock.get("delegated_scientific_modules") or [])
             if isinstance(entry, dict) and entry.get("path")}
    verified = GATE.verify_delegated_science(bound, root=root)
    return {"caps": dict(CAPS), "delegated_scientific_modules": verified}


def production_executor(context, stream=None) -> dict:
    """Delegate to unchanged P0-R1 generation-3 science, or refuse."""
    context = context or {}
    preconditions = require_production_preconditions(
        authorization=context.get("authorization"),
        lock=context.get("lock"), root=context.get("root"),
        accelerator_required=bool(context.get("accelerator_required")))

    import p0_r1_model_runner_v3 as RUNNER  # noqa: E402

    result = RUNNER.run_pilot(
        context["lock_file"], context["replay_receipt"],
        context["reconstruction_receipt"], context["head_proof"],
        context["out_dir"], root=context.get("root"),
        attempt_id=context.get("attempt_id"),
        image_digest=context["lock"]["image"]["digest"],
        backend=context.get("backend"), stream=stream,
        run_id=context.get("run_id"))
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "executor": "production",
        "attempt_id": context.get("attempt_id"),
        "delegated_to": "p0_r1_model_runner_v3.run_pilot",
        "science_is_unchanged_p0_r1_generation3": True,
        "preconditions": preconditions,
        "result": result,
    }


def run(context, *, executor=None, stream=None) -> dict:
    """Default to the sentinel. A model run must be asked for explicitly."""
    return (executor or sentinel_executor)(context, stream=stream)


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_model_runner_v1.py",
        "stage": STAGE,
        "default_executor": "sentinel",
        "sentinel_line": SENTINEL_LINE,
        "gpu_job": GPU_JOB,
        "caps": dict(CAPS),
        "delegates_science_to": "p0_r1_model_runner_v3",
        "copies_or_edits_science": False,
        "production_requires_authorization": True,
        "production_requires_accelerator": True,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--sentinel", action="store_true")
    parser.add_argument("--attempt")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0
    document = run({"attempt_id": args.attempt})
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
