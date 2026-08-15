#!/usr/bin/env python3
"""Submit only the verified P0-R2 two-file context to ACR.

This module owns the host-side boundary where P0-R1 failed. It re-verifies the
minimal context immediately before calling Azure CLI, captures stdout and
stderr from the first byte, requires one unambiguous ACR run ID, and records a
machine-readable submission receipt. It does not reconstruct replay artifacts
or authorize a model pilot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_submission_context as CONTEXT  # noqa: E402
import p0_r2_closure_binding_v1 as CLOSURE  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-acr-submission-receipt-v1"
RECEIPT_NAME = "p0_r2_acr_submission_receipt.json"
RAW_LOG_NAME = "p0_r2_acr_raw_log.txt"
STDERR_NAME = "p0_r2_acr_stderr.txt"
RUN_ID_PATTERN = re.compile(r"Run ID:\s*([a-z0-9]+)")

PACKING_CANARY_MARKERS = (
    "P0_R2_PACKING_CANARY_COMPLETE=1",
    "P0_R2_REPLAY_GATE_RUN=false",
    "P0_R2_ONE_SHOT_ENVELOPE_CONSUMED=false",
    "P0_R2_MODEL_OPERATIONS_PERFORMED=0",
)


class SubmissionDefect(Exception):
    """The host submission cannot be proved safe and unambiguous."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _identity(payload: bytes, name: str) -> dict:
    return {"name": name, "bytes": len(payload), "sha256": _sha256(payload)}


def _bytes(value) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8")


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise SubmissionDefect(
            "%s already exists; a submission is never resumed or rerun" % path
        ) from exc


def parse_run_id(raw_log: bytes, *, required: bool) -> str | None:
    text = raw_log.decode("utf-8", "replace")
    matches = RUN_ID_PATTERN.findall(text)
    if not matches and not required:
        return None
    if len(matches) != 1:
        raise SubmissionDefect(
            "the captured raw log contains %d ACR run-id markers; exactly one "
            "is required" % len(matches))
    return matches[0]


def _load_json(path: Path, label: str) -> tuple[dict, bytes]:
    try:
        raw = Path(path).read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise SubmissionDefect("%s is unreadable: %s" % (label, exc))
    if not isinstance(document, dict):
        raise SubmissionDefect("%s is not a JSON object" % label)
    return document, raw


def require_context_admission(path: Path, recomputed: dict) -> dict:
    published, raw = _load_json(path, "context admission receipt")
    if published != recomputed:
        raise SubmissionDefect(
            "the retained context admission receipt differs from immediate "
            "pre-submission verification")
    if published.get("outcome") != "PASS" \
            or (published.get("context") or {}).get("entry_count") != 2:
        raise SubmissionDefect("the context admission receipt is not a pass")
    return {"document": published, "identity": _identity(raw, Path(path).name)}


def require_packing_canary(path: Path, *, root, task_path: str,
                           executable_commit: str, executable_tree: str,
                           task_blob: str, image: str, digest: str) -> dict:
    """Require immutable agreement, not identical source commits.

    The live submission necessarily reads its embedded governance objects from
    a *later* commit than the canary, because publishing the lock creates that
    commit. Demanding an identical source commit would make the canary
    unsatisfiable by construction. What must be identical is the immutable
    executable/task/image identity, which no governance-only descendant can
    touch. The governance relationship itself is proved separately by
    ``p0_r2_closure_binding_v1.prove_governance_chain``.
    """
    document, raw = _load_json(path, "packing canary receipt")
    if document.get("schema_version") != SCHEMA_VERSION \
            or document.get("mode") != "packing-canary" \
            or document.get("outcome") != "PASS" \
            or document.get("exit_code") != 0 \
            or not document.get("acr_run_id"):
        raise SubmissionDefect("the packing canary receipt is not a pass")
    if document.get("replay_gate_ran") is not False \
            or document.get("one_shot_envelope_consumed") is not False \
            or document.get("model_operations_performed") != 0:
        raise SubmissionDefect(
            "the packing canary is not a disjoint zero-operation canary")
    try:
        resolved = CLOSURE.resolve_canary_binding(
            root, document.get("binding") or {}, task_path=task_path)
        live = CLOSURE.canary_binding(
            executable_commit=executable_commit,
            executable_tree=executable_tree, task_path=task_path,
            task_blob=task_blob, image=image, digest=digest)
        agreement = CLOSURE.verify_canary_live_agreement(resolved, live)
    except CLOSURE.ClosureBindingDefect as exc:
        raise SubmissionDefect(str(exc)) from exc
    return {
        "document": document,
        "identity": _identity(raw, Path(path).name),
        "agreement": agreement,
    }


def classify_packing_canary(raw_log: bytes) -> None:
    text = raw_log.decode("utf-8", "replace")
    for marker in PACKING_CANARY_MARKERS:
        if text.count(marker) != 1:
            raise SubmissionDefect(
                "packing canary marker %r occurred %d times, not once" %
                (marker, text.count(marker)))


def _default_runner(command, cwd):
    # subprocess does not apply PATHEXT, so a bare "az" cannot be launched on
    # Windows, where the Azure CLI ships as az.cmd. This module exists to own
    # the host submission boundary, and a host it cannot launch the CLI on is
    # exactly the kind of failure it is supposed to remove, so the program is
    # resolved the way the shell would resolve it.
    program = shutil.which(command[0]) or command[0]
    return subprocess.run(
        [program] + list(command[1:]), cwd=str(cwd), capture_output=True,
        text=False, check=False)


def submit(*, root: Path, source_commit: str, task_path: str,
           context_dir: Path, context_admission: Path, work_dir: Path,
           registry: str, subscription: str, image: str, digest: str,
           ready_anchor: str, mode: str, attempt: str,
           packing_canary_receipt: Path | None = None, runner=None,
           azure_cli_version=None, executable_commit: str | None = None,
           executable_tree: str | None = None,
           governance_proof: Path | None = None) -> dict:
    """Perform one host submission after every local refusal check."""
    if mode not in ("packing-canary", "live"):
        raise SubmissionDefect("mode must be packing-canary or live")
    if not azure_cli_version:
        raise SubmissionDefect(
            "the exact Azure CLI version is required before submission")
    root = Path(root).resolve()
    context_dir = Path(context_dir).resolve()
    work_dir = Path(work_dir).resolve()
    for name in (RAW_LOG_NAME, STDERR_NAME, RECEIPT_NAME):
        if (work_dir / name).exists():
            raise SubmissionDefect(
                "%s already exists; this work directory has a prior submission"
                % name)

    try:
        recomputed = CONTEXT.verify(
            root, context_dir, expected_commit=source_commit,
            expected_task_path=task_path)
    except CONTEXT.ContextDefect as exc:
        raise SubmissionDefect(
            "immediate context verification refused: %s" % exc) from exc
    admission = require_context_admission(context_admission, recomputed)
    task_blob = recomputed["context"]["task"]["git_blob"]

    # A canary runs at the executable commit itself, so the executable identity
    # defaults to the context source. A live run is a governance descendant and
    # must state the executable identity explicitly from the lock.
    if executable_commit is None:
        executable_commit = source_commit
    if executable_tree is None:
        executable_tree = (
            recomputed["source"]["tree"]
            if executable_commit == source_commit
            else CLOSURE._git(root, ["rev-parse", "%s^{tree}" %
                                     executable_commit])[0].strip())

    canary = None
    governance = None
    if mode == "live":
        if packing_canary_receipt is None:
            raise SubmissionDefect(
                "live submission requires the final packing canary receipt")
        canary = require_packing_canary(
            packing_canary_receipt, root=root, task_path=task_path,
            executable_commit=executable_commit,
            executable_tree=executable_tree, task_blob=task_blob,
            image=image, digest=digest)
        if governance_proof is not None:
            document, raw = _load_json(governance_proof,
                                       "governance chain proof")
            try:
                CLOSURE.validate_proof(
                    document, executable_commit=executable_commit,
                    ready_anchor=ready_anchor, governance_commit=source_commit,
                    task_blob=task_blob)
            except CLOSURE.ClosureBindingDefect as exc:
                raise SubmissionDefect(
                    "the governance chain proof does not bind this live "
                    "submission: %s" % exc) from exc
            governance = _identity(raw, Path(governance_proof).name)

    try:
        command = CONTEXT.acr_run_command(
            registry=registry, subscription=subscription, image=image,
            digest=digest, ready_anchor=ready_anchor, mode=mode,
            attempt=attempt, context_dir=context_dir)
    except CONTEXT.ContextDefect as exc:
        raise SubmissionDefect(str(exc)) from exc

    work_dir.mkdir(parents=True, exist_ok=True)
    runner_error = None
    try:
        completed = (runner or _default_runner)(command, context_dir)
        stdout = _bytes(getattr(completed, "stdout", b""))
        stderr = _bytes(getattr(completed, "stderr", b""))
        exit_code = int(getattr(completed, "returncode", -1))
    except OSError as exc:
        stdout = b""
        stderr = ("Azure CLI invocation failed locally: %s\n" % exc).encode(
            "utf-8", "replace")
        exit_code = 127
        runner_error = str(exc)
    _write_exclusive(work_dir / RAW_LOG_NAME, stdout)
    _write_exclusive(work_dir / STDERR_NAME, stderr)

    classification_error = runner_error
    try:
        run_id = parse_run_id(stdout, required=exit_code == 0)
    except SubmissionDefect as exc:
        run_id = None
        classification_error = str(exc)
    outcome = "STOP"
    if exit_code == 0 and run_id and classification_error is None:
        if mode == "packing-canary":
            try:
                classify_packing_canary(stdout)
            except SubmissionDefect as exc:
                classification_error = str(exc)
        if classification_error is None:
            outcome = "PASS"

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "stage": "STUDY3-P0-R2",
        "mode": mode,
        "outcome": outcome,
        "failure_detail": classification_error,
        "exit_code": exit_code,
        "acr_run_id": run_id,
        "attempt_id": attempt,
        "binding": {
            "source_commit": source_commit,
            "source_tree": recomputed["source"]["tree"],
            "executable_commit": executable_commit,
            "executable_tree": executable_tree,
            "task_path": task_path,
            "task_blob": task_blob,
            "image": image,
            "digest": digest,
            "ready_anchor": ready_anchor,
        },
        "context_admission": admission["identity"],
        "governance_chain_proof": governance,
        "canary_live_agreement": (
            canary["agreement"] if canary is not None else None),
        "packing_canary_receipt": (
            canary["identity"] if canary is not None else None),
        "command": {
            "argv": command,
            "file_argument": "task.yaml",
            "context_argument": str(context_dir),
            "credentials_recorded": False,
        },
        "azure_cli_version": azure_cli_version,
        "raw_log": _identity(stdout, RAW_LOG_NAME),
        "stderr": _identity(stderr, STDERR_NAME),
        "replay_gate_ran": False if mode == "packing-canary" else None,
        "one_shot_envelope_consumed": False if mode == "packing-canary" else True,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
        "scored_rows": 0,
        "authorizes_model_pilot": False,
    }
    receipt_payload = (
        json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _write_exclusive(work_dir / RECEIPT_NAME, receipt_payload)
    if outcome != "PASS":
        raise SubmissionDefect(
            "ACR submission stopped with exit code %d (%s); the retained "
            "receipt authorizes nothing" %
            (exit_code, classification_error or "no proved pass"))
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--packing-canary", action="store_true")
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--identity", action="store_true")
    parser.add_argument("--root")
    parser.add_argument("--source-commit")
    parser.add_argument("--task-path")
    parser.add_argument("--context-dir")
    parser.add_argument("--context-admission")
    parser.add_argument("--work-dir")
    parser.add_argument("--registry")
    parser.add_argument("--subscription")
    parser.add_argument("--image")
    parser.add_argument("--digest")
    parser.add_argument("--ready-anchor")
    parser.add_argument("--attempt")
    parser.add_argument("--packing-canary-receipt")
    parser.add_argument("--executable-commit")
    parser.add_argument("--executable-tree")
    parser.add_argument("--governance-proof")
    parser.add_argument("--azure-cli-version")
    parser.add_argument("--i-am-sure", action="store_true")
    args = parser.parse_args(argv)
    if args.identity:
        print(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "module": "p0_r2_acr_submission.py",
            "modes": ["packing-canary", "live"],
            "full_repository_context_forbidden": True,
            "requires_explicit_confirmation": True,
            "authorizes_model_pilot": False,
        }, indent=2, sort_keys=True))
        return 0
    if not args.i_am_sure:
        print("P0_R2_SUBMISSION_REFUSED=1 --i-am-sure is required",
              file=sys.stderr)
        return 2
    required = (
        "root", "source_commit", "task_path", "context_dir",
        "context_admission", "work_dir", "registry", "subscription",
        "image", "digest", "ready_anchor", "attempt", "azure_cli_version")
    missing = ["--" + name.replace("_", "-") for name in required
               if not getattr(args, name)]
    if missing:
        parser.error("%s required" % ", ".join(missing))
    selected_mode = "packing-canary" if args.packing_canary else "live"
    try:
        receipt = submit(
            root=args.root, source_commit=args.source_commit,
            task_path=args.task_path, context_dir=args.context_dir,
            context_admission=args.context_admission, work_dir=args.work_dir,
            registry=args.registry, subscription=args.subscription,
            image=args.image, digest=args.digest,
            ready_anchor=args.ready_anchor, mode=selected_mode,
            attempt=args.attempt,
            packing_canary_receipt=args.packing_canary_receipt,
            executable_commit=args.executable_commit,
            executable_tree=args.executable_tree,
            governance_proof=args.governance_proof,
            azure_cli_version=args.azure_cli_version)
    except (SubmissionDefect, OSError) as exc:
        print("P0_R2_SUBMISSION_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    print("P0_R2_ACR_SUBMISSION=PASS")
    print("P0_R2_ACR_RUN_ID=%s" % receipt["acr_run_id"])
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
