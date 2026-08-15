#!/usr/bin/env python3
"""Study 3 P0-R2 generation-2 guarded host submission.

Authority:
``studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md``
sections 6.5, 6.6 and 11.

This module owns the whole host boundary of a generation-2 ACR invocation:

* it builds the minimal two-file context — ``task.yaml`` and
  ``context_manifest.json`` and nothing else — from exact committed Git objects
  and from explicitly supplied machine receipts, never from an ambient worktree
  copy;
* it re-verifies every admitted byte by SHA-256 immediately before invocation;
* it proves the Windows launch path it is about to use, through the exact
  program ``shutil.which`` resolves, including ``az.CMD``;
* it invokes ``az acr run`` at most once and treats the envelope as consumed the
  moment a child process exists, even if no run id ever comes back;
* it scopes the live authorization environment variable to that single child and
  never exports it into this process.

Generation 1 reached its one irreversible invocation with an ACR-side prefix
proof that could not succeed. Generation 2 therefore also refuses to start the
live process unless a host-verified, byte-bound, fresh in-VNet prefix receipt is
embedded in the very context it is about to upload.

Model-free. No tokenizer, checkpoint, model weight, GPU or scoring operation.
"""

from __future__ import annotations

import argparse
import base64
import datetime
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

import p0_r2_prefix_proof_g2 as PREFIX  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-guarded-host-submission-g2"
CONTEXT_SCHEMA_VERSION = "study3-p0-r2-minimal-acr-context-g2"
RECEIPT_SCHEMA_VERSION = "study3-p0-r2-acr-submission-receipt-g2"
LAUNCH_SCHEMA_VERSION = "study3-p0-r2-windows-launch-proof-g2"
STAGE = "STUDY3-P0-R2"
GENERATION = 2

CONTEXT_DIRECTORY_NAME = "acrctx"
TASK_CONTEXT_NAME = "task.yaml"
MANIFEST_NAME = "context_manifest.json"
EXPECTED_ENTRIES = (MANIFEST_NAME, TASK_CONTEXT_NAME)

#: Section 6.5. Generation 1 accepted 240; generation 2 is held to 100.
MAX_NATIVE_CONTEXT_PATH = 100
#: The short fixed Windows directory the authority names.
DEFAULT_CONTEXT_ROOT = r"C:\p0r2g2\acrctx"

REGISTRY_NAME = "acrjspaceobssea0708231738"
REGISTRY = "acrjspaceobssea0708231738.azurecr.io"
REPOSITORY = "j-space-observation-study3-p0-r2"
SUBSCRIPTION = PREFIX.SUBSCRIPTION

RAW_LOG_NAME = "p0_r2_g2_acr_raw_log.txt"
STDERR_NAME = "p0_r2_g2_acr_stderr.txt"
RECEIPT_NAME = "p0_r2_g2_acr_submission_receipt.json"
ENVELOPE_NAME = "p0_r2_g2_one_shot_envelope.json"
LAUNCH_PROOF_NAME = "p0_r2_g2_windows_launch_proof.json"

#: Scoped to exactly one child process. Never exported into os.environ.
LIVE_AUTHORIZATION_ENVIRONMENT = "P0_R2_LIVE_REPLAY_AUTHORIZED"

VALID_MODES = ("canary", "live")

RUN_ID_PATTERN = re.compile(r"Run ID:\s*([a-z0-9]+)")
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SAFE_LABEL = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

#: Markers the canary path must print exactly once each.
CANARY_MARKERS = (
    "P0_R2_G2_PACKING_CANARY_COMPLETE=1",
    PREFIX.DEFERRED_MARKER,
    "P0_R2_G2_REPLAY_GATE_RUN=false",
)


class SubmissionDefect(Exception):
    """A fail-closed host submission stop."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(document) -> bytes:
    return json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _git(root, args, *, binary=False):
    completed = subprocess.run(  # noqa: S603 - fixed executable, fixed args
        ["git", *args], cwd=None if root is None else str(root),
        capture_output=True, text=not binary, check=False)
    if completed.returncode:
        raise SubmissionDefect(
            "git %s refused: %s" % (" ".join(args), (
                completed.stderr if not binary
                else completed.stderr.decode("utf-8", "replace")).strip()))
    return completed.stdout


def _safe_repo_path(value, label):
    if not value or not isinstance(value, str):
        raise SubmissionDefect("%s is required" % label)
    if value.startswith("/") or "\\" in value or ".." in value.split("/"):
        raise SubmissionDefect("%s %r traverses" % (label, value))
    return value


def git_object_identity(root, commit, repo_path) -> dict:
    repo_path = _safe_repo_path(repo_path, "repository path")
    if not _SHA40.match(commit or ""):
        raise SubmissionDefect("a full 40-character commit is required")
    listing = _git(root, ["ls-tree", commit, "--", repo_path]).strip()
    if not listing:
        raise SubmissionDefect(
            "%s does not exist at commit %s" % (repo_path, commit))
    mode, kind, rest = listing.split(" ", 2)
    blob, _, _ = rest.partition("\t")
    if kind != "blob":
        raise SubmissionDefect("%s is not a regular blob" % repo_path)
    payload = _git(root, ["cat-file", "blob", blob], binary=True)
    return {
        "source_path": repo_path,
        "mode": mode,
        "git_blob": blob,
        "bytes": len(payload),
        "sha256": _sha256(payload),
        "payload": payload,
    }


def _native_path(path: Path) -> str:
    return str(Path(path))


def _entries(context_dir: Path) -> list:
    names = []
    for entry in os.scandir(context_dir):
        if entry.is_symlink():
            raise SubmissionDefect(
                "context entry %r is a link; the context admits regular files "
                "only" % entry.name)
        if not entry.is_file(follow_symlinks=False):
            raise SubmissionDefect(
                "context entry %r is not a regular file" % entry.name)
        if entry.name.startswith("."):
            raise SubmissionDefect(
                "context entry %r is hidden" % entry.name)
        names.append(entry.name)
    return sorted(names)


def build_context(*, root, context_dir, source_commit, task_path,
                  embedded_objects=None, machine_receipts=None) -> dict:
    """Create exactly two regular files from committed objects and receipts."""
    root = Path(root).resolve()
    context_dir = Path(context_dir)
    if context_dir.name != CONTEXT_DIRECTORY_NAME:
        raise SubmissionDefect(
            "the context directory must be named %r" % CONTEXT_DIRECTORY_NAME)
    context_dir.mkdir(parents=True, exist_ok=True)
    if any(os.scandir(context_dir)):
        raise SubmissionDefect(
            "the minimal context directory must start empty; reruns are "
            "refused")

    tree = _git(root, ["rev-parse", "%s^{tree}" % source_commit]).strip()
    task = git_object_identity(root, source_commit, task_path)

    embedded = []
    for label, repo_path in sorted((embedded_objects or {}).items()):
        if not _SAFE_LABEL.fullmatch(label):
            raise SubmissionDefect("unsafe embedded-object label %r" % label)
        identity = git_object_identity(root, source_commit, repo_path)
        embedded.append({
            "label": label,
            "origin": "git",
            "source_path": identity["source_path"],
            "git_blob": identity["git_blob"],
            "bytes": identity["bytes"],
            "sha256": identity["sha256"],
            "encoding": "base64",
            "payload": base64.b64encode(identity["payload"]).decode("ascii"),
        })

    for label, receipt_path in sorted((machine_receipts or {}).items()):
        if not _SAFE_LABEL.fullmatch(label):
            raise SubmissionDefect("unsafe machine-receipt label %r" % label)
        if any(entry["label"] == label for entry in embedded):
            raise SubmissionDefect("duplicate embedded label %r" % label)
        payload = Path(receipt_path).read_bytes()
        embedded.append({
            "label": label,
            "origin": "machine-receipt",
            "source_path": Path(receipt_path).name,
            "git_blob": None,
            "bytes": len(payload),
            "sha256": _sha256(payload),
            "encoding": "base64",
            "payload": base64.b64encode(payload).decode("ascii"),
        })

    manifest = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "context_contract": "two-root-level-regular-files-only",
        "file_set": list(EXPECTED_ENTRIES),
        "source": {"commit": source_commit, "tree": tree},
        "task": {
            "source_path": task["source_path"],
            "context_name": TASK_CONTEXT_NAME,
            "git_blob": task["git_blob"],
            "bytes": task["bytes"],
            "sha256": task["sha256"],
        },
        "embedded_governance_objects": embedded,
        "built_from_committed_objects_only": True,
        "built_from_ambient_worktree": False,
        "contains_model_bytes": False,
        "contains_checkpoint_bytes": False,
        "contains_corpus_bytes": False,
        "contains_result_bytes": False,
        "contains_credentials": False,
    }
    manifest_payload = canonical_bytes(manifest)
    for name, payload in ((TASK_CONTEXT_NAME, task["payload"]),
                          (MANIFEST_NAME, manifest_payload)):
        path = context_dir / name
        try:
            with path.open("xb") as handle:
                handle.write(payload)
        except FileExistsError as exc:
            raise SubmissionDefect(
                "context path %s already exists; reruns are refused" % path
            ) from exc
    return manifest


def verify_context(*, root, context_dir, expected_commit=None,
                   expected_task_path=None, attempt=None, mode="canary",
                   ceiling=MAX_NATIVE_CONTEXT_PATH) -> dict:
    """Re-read the built context and admit it, or refuse."""
    context_dir = Path(context_dir).resolve()
    if not context_dir.is_dir():
        raise SubmissionDefect("the context directory does not exist")
    names = _entries(context_dir)
    if tuple(names) != EXPECTED_ENTRIES:
        raise SubmissionDefect(
            "the context holds %r; exactly %r is admitted"
            % (names, list(EXPECTED_ENTRIES)))

    native_paths = [_native_path(context_dir)] + [
        _native_path(context_dir / name) for name in names]
    longest = max(len(value) for value in native_paths)
    if longest > ceiling:
        raise SubmissionDefect(
            "the maximum native context path is %d characters; the ceiling is "
            "%d" % (longest, ceiling))

    manifest_payload = (context_dir / MANIFEST_NAME).read_bytes()
    task_payload = (context_dir / TASK_CONTEXT_NAME).read_bytes()
    try:
        manifest = json.loads(manifest_payload.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SubmissionDefect("the context manifest is not JSON: %s" % exc)
    if manifest.get("schema_version") != CONTEXT_SCHEMA_VERSION:
        raise SubmissionDefect("the context manifest schema is foreign")
    if manifest.get("generation") != GENERATION:
        raise SubmissionDefect("the context manifest is not generation 2")

    declared = manifest.get("task") or {}
    if declared.get("sha256") != _sha256(task_payload) \
            or declared.get("bytes") != len(task_payload):
        raise SubmissionDefect(
            "the task file on disk disagrees with the manifest it is admitted "
            "under")
    if expected_task_path and declared.get("source_path") != expected_task_path:
        raise SubmissionDefect(
            "the context task is %r, not the registered %r"
            % (declared.get("source_path"), expected_task_path))
    if expected_commit and (manifest.get("source") or {}).get("commit") \
            != expected_commit:
        raise SubmissionDefect("the context was built from a foreign commit")

    if root is not None and declared.get("git_blob"):
        identity = git_object_identity(
            root, (manifest.get("source") or {})["commit"],
            declared["source_path"])
        if identity["sha256"] != _sha256(task_payload):
            raise SubmissionDefect(
                "the context task bytes are not the committed task bytes")

    embedded_receipts = []
    labels = []
    for entry in manifest.get("embedded_governance_objects") or []:
        payload = base64.b64decode(entry.get("payload") or "", validate=True)
        if len(payload) != entry.get("bytes") \
                or _sha256(payload) != entry.get("sha256"):
            raise SubmissionDefect(
                "embedded object %r does not match its admitted identity"
                % entry.get("label"))
        labels.append(entry.get("label"))
        embedded_receipts.append({
            "label": entry.get("label"),
            "origin": entry.get("origin"),
            "source_path": entry.get("source_path"),
            "bytes": entry.get("bytes"),
            "sha256": entry.get("sha256"),
        })
    if len(set(labels)) != len(labels):
        raise SubmissionDefect("the context embeds a duplicate label")

    prefix_validation = None
    if attempt:
        prefix_validation = PREFIX.validate_bound_receipt(
            manifest, attempt_id=attempt, mode=mode)

    return {
        "schema_version": "study3-p0-r2-context-admission-receipt-g2",
        "stage": STAGE,
        "generation": GENERATION,
        "context": {
            "directory_name": CONTEXT_DIRECTORY_NAME,
            "native_directory": _native_path(context_dir),
            "entries": names,
            "entry_count": len(names),
            "maximum_native_path": longest,
            "native_path_ceiling": ceiling,
            "task": declared,
            "manifest_bytes": len(manifest_payload),
            "manifest_sha256": _sha256(manifest_payload),
            "embedded_governance_objects": embedded_receipts,
        },
        "source": manifest.get("source"),
        "prefix_validation": prefix_validation,
        "contains_credentials": False,
        "model_operations_performed": 0,
    }


def resolve_azure_cli(which=None):
    resolver = which or shutil.which
    resolved = resolver("az")
    if not resolved:
        raise SubmissionDefect(
            "the Azure CLI could not be resolved with shutil.which; a bare "
            "'az' cannot be launched by subprocess on Windows")
    return resolved


def prove_launch_path(*, which=None, runner=None) -> dict:
    """Run the benign checks through the exact program that will be used."""
    program = resolve_azure_cli(which)
    execute = runner or (lambda argv: subprocess.run(  # noqa: S603
        argv, capture_output=True, text=False, check=False, shell=False))

    checks = []
    for label, argv in (("version", [program, "version"]),
                        ("account_show", [program, "account", "show",
                                          "-o", "json"])):
        completed = execute(argv)
        stdout = completed.stdout or b""
        stderr = completed.stderr or b""
        checks.append({
            "check": label,
            "argv0": program,
            "returncode": completed.returncode,
            "stdout_bytes": len(stdout),
            "stdout_sha256": _sha256(stdout),
            "stderr_bytes": len(stderr),
            "passed": completed.returncode == 0,
        })
        if completed.returncode != 0:
            raise SubmissionDefect(
                "the benign 'az %s' check failed through %s: %s"
                % (label, program, stderr.decode("utf-8", "replace").strip()))

    version = None
    subscription = None
    try:
        version = json.loads(
            (execute([program, "version"]).stdout or b"{}").decode("utf-8")
        ).get("azure-cli")
        account = json.loads(
            (execute([program, "account", "show", "-o", "json"]).stdout
             or b"{}").decode("utf-8"))
        subscription = account.get("id")
    except Exception:  # noqa: BLE001 - a parse failure is reported, not fatal
        pass

    if subscription and subscription != SUBSCRIPTION:
        raise SubmissionDefect(
            "the resolved Azure CLI is signed in to subscription %r, not the "
            "registered %r" % (subscription, SUBSCRIPTION))

    return {
        "schema_version": LAUNCH_SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "resolved_with": "shutil.which",
        "resolved_executable": program,
        "resolved_basename": Path(program).name,
        "uses_shell": False,
        "relies_on_pathext": False,
        "azure_cli_version": version,
        "subscription": subscription,
        "checks": checks,
        "authorization_environment": LIVE_AUTHORIZATION_ENVIRONMENT,
        "authorization_exported_globally": bool(
            os.environ.get(LIVE_AUTHORIZATION_ENVIRONMENT)),
        "model_operations_performed": 0,
    }


def acr_run_command(*, image, digest, ready_anchor, mode, attempt,
                    prefix_receipt_sha256, context_dir) -> list:
    if mode not in VALID_MODES:
        raise SubmissionDefect("mode must be one of %r" % (VALID_MODES,))
    if not _DIGEST.match(digest or ""):
        raise SubmissionDefect("the image digest must be sha256-pinned")
    if digest not in (image or ""):
        raise SubmissionDefect("the image reference is not digest-pinned")
    if not _SHA40.match(ready_anchor or ""):
        raise SubmissionDefect("a full ready anchor commit is required")
    if not _SHA256.match(prefix_receipt_sha256 or ""):
        raise SubmissionDefect("the prefix receipt SHA-256 is required")
    return [
        "az", "acr", "run",
        "--registry", REGISTRY_NAME,
        "--subscription", SUBSCRIPTION,
        "--file", TASK_CONTEXT_NAME,
        "--set", "IMAGE=%s" % image,
        "--set", "DIGEST=%s" % digest,
        "--set", "READY_ANCHOR=%s" % ready_anchor,
        "--set", "MODE=%s" % mode,
        "--set", "ATTEMPT=%s" % attempt,
        "--set", "PREFIX_RECEIPT_SHA256=%s" % prefix_receipt_sha256,
        str(context_dir),
    ]


def _child_environment(mode, environ=None):
    """The child's environment. The authorization never enters this process."""
    base = dict(os.environ if environ is None else environ)
    base.pop(LIVE_AUTHORIZATION_ENVIRONMENT, None)
    if mode == "live":
        base[LIVE_AUTHORIZATION_ENVIRONMENT] = "1"
    return base


def submit_once(*, root, context_dir, work_dir, image, digest, ready_anchor,
                mode, attempt, prefix_receipt, source_commit=None,
                task_path=None, runner=None, which=None, environ=None,
                launch_proof=None, now=None) -> dict:
    """Perform at most one generation-2 ACR invocation."""
    if mode not in VALID_MODES:
        raise SubmissionDefect("mode must be one of %r" % (VALID_MODES,))
    context_dir = Path(context_dir).resolve()
    work_dir = Path(work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    for name in (RAW_LOG_NAME, STDERR_NAME, RECEIPT_NAME, ENVELOPE_NAME):
        if (work_dir / name).exists():
            raise SubmissionDefect(
                "%s already exists; this work directory has a prior "
                "submission" % name)

    receipt_payload = Path(prefix_receipt).read_bytes()
    receipt_sha256 = _sha256(receipt_payload)
    try:
        receipt_document = json.loads(receipt_payload.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SubmissionDefect("the prefix receipt is not JSON: %s" % exc)

    # The freshness rule is the host's, and it is checked here, immediately
    # before the process starts, not when the receipt was written.
    freshness = PREFIX.validate_receipt(
        receipt_document, attempt_id=attempt, mode=mode,
        expected_sha256=receipt_sha256, receipt_bytes=receipt_payload,
        require_host_freshness=True, now=now)

    admission = verify_context(
        root=root, context_dir=context_dir, expected_commit=source_commit,
        expected_task_path=task_path, attempt=attempt, mode=mode)
    embedded = {entry["label"]: entry for entry
                in admission["context"]["embedded_governance_objects"]}
    bound = embedded.get(PREFIX.CONTEXT_LABEL)
    if not bound:
        raise SubmissionDefect(
            "the context does not embed the prefix receipt")
    if bound["sha256"] != receipt_sha256:
        raise SubmissionDefect(
            "the context embeds a different prefix receipt than the one the "
            "host verified")

    proof = launch_proof or prove_launch_path(which=which)
    program = proof["resolved_executable"]

    command = acr_run_command(
        image=image, digest=digest, ready_anchor=ready_anchor, mode=mode,
        attempt=attempt, prefix_receipt_sha256=receipt_sha256,
        context_dir=context_dir)

    child_environment = _child_environment(mode, environ)
    started_at = PREFIX.utc_now()
    envelope = {
        "schema_version": "study3-p0-r2-one-shot-envelope-g2",
        "stage": STAGE,
        "generation": GENERATION,
        "mode": mode,
        "attempt_id": attempt,
        "consumed": mode == "live",
        "consumed_on_process_start": True,
        "process_started_at_utc": started_at,
        "invocations": 1,
        "rerunnable": False,
    }
    (work_dir / ENVELOPE_NAME).write_bytes(canonical_bytes(envelope))

    launch_failure = None
    try:
        if runner is not None:
            completed = runner([program] + command[1:], context_dir,
                               child_environment)
        else:
            completed = subprocess.run(  # noqa: S603 - resolved program
                [program] + command[1:], cwd=str(context_dir),
                capture_output=True, text=False, check=False, shell=False,
                env=child_environment)
    except OSError as exc:
        launch_failure = "%s: %s" % (type(exc).__name__, exc)
        completed = None

    finished_at = PREFIX.utc_now()
    stdout = b"" if completed is None else (completed.stdout or b"")
    stderr = b"" if completed is None else (completed.stderr or b"")
    exit_code = None if completed is None else completed.returncode
    (work_dir / RAW_LOG_NAME).write_bytes(stdout)
    (work_dir / STDERR_NAME).write_bytes(stderr)

    text = stdout.decode("utf-8", "replace")
    run_ids = sorted(set(RUN_ID_PATTERN.findall(text)))

    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "mode": mode,
        "attempt_id": attempt,
        "acr_run_id": run_ids[0] if len(run_ids) == 1 else None,
        "acr_run_ids": run_ids,
        "acr_run_id_count": len(run_ids),
        "exit_code": exit_code,
        "process_started": completed is not None,
        "launch_failure": launch_failure,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "command": {
            "argv": command,
            "resolved_executable": program,
            "context_argument": str(context_dir),
            "file_argument": TASK_CONTEXT_NAME,
            "uses_shell": False,
            "credentials_recorded": False,
        },
        "binding": {
            "image": image,
            "digest": digest,
            "ready_anchor": ready_anchor,
            "source_commit": source_commit,
            "task_path": task_path,
            "task_blob": admission["context"]["task"].get("git_blob"),
            "prefix_receipt_sha256": receipt_sha256,
            "prefix_receipt_bytes": len(receipt_payload),
        },
        "prefix_freshness": freshness,
        "context_admission": admission,
        "launch_proof": proof,
        "one_shot_envelope_consumed": mode == "live",
        "authorization_exported_globally": bool(
            os.environ.get(LIVE_AUTHORIZATION_ENVIRONMENT)),
        "authorization_scoped_to_child": mode == "live",
        "raw_log": {
            "name": RAW_LOG_NAME,
            "bytes": len(stdout),
            "sha256": _sha256(stdout),
        },
        "stderr": {
            "name": STDERR_NAME,
            "bytes": len(stderr),
            "sha256": _sha256(stderr),
        },
        "outcome": "PASS" if (exit_code == 0 and len(run_ids) == 1)
        else "STOP",
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "scored_rows": 0,
        "model_operations_performed": 0,
    }
    if mode == "canary":
        missing = [marker for marker in CANARY_MARKERS
                   if text.count(marker) != 1]
        receipt["canary_markers_exactly_once"] = not missing
        receipt["canary_markers_missing_or_repeated"] = missing
        if missing:
            receipt["outcome"] = "STOP"
    (work_dir / RECEIPT_NAME).write_bytes(canonical_bytes(receipt))
    return receipt


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_host_submission_g2.py",
        "stage": STAGE,
        "generation": GENERATION,
        "context_entries": list(EXPECTED_ENTRIES),
        "context_entry_count": len(EXPECTED_ENTRIES),
        "context_directory_name": CONTEXT_DIRECTORY_NAME,
        "default_context_root": DEFAULT_CONTEXT_ROOT,
        "max_native_context_path": MAX_NATIVE_CONTEXT_PATH,
        "prefix_validator": "p0_r2_prefix_proof_g2.validate_receipt",
        "shared_by_canary_and_live": True,
        "resolves_azure_cli_with": "shutil.which",
        "uses_shell": False,
        "authorization_environment": LIVE_AUTHORIZATION_ENVIRONMENT,
        "authorization_scoped_to_single_child": True,
        "envelope_consumed_on_process_start": True,
        "rerunnable": False,
        "accepts_allow_path": False,
        "accepts_force": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--prove-launch", action="store_true")
    mode.add_argument("--build-context", action="store_true")
    mode.add_argument("--verify-context", action="store_true")
    mode.add_argument("--submit-once", action="store_true")
    parser.add_argument("--root", default=".")
    parser.add_argument("--context-dir", default=DEFAULT_CONTEXT_ROOT)
    parser.add_argument("--work-dir")
    parser.add_argument("--source-commit")
    parser.add_argument("--task-path")
    parser.add_argument("--embedded-object", action="append", default=[])
    parser.add_argument("--machine-receipt", action="append", default=[])
    parser.add_argument("--image")
    parser.add_argument("--digest")
    parser.add_argument("--ready-anchor")
    parser.add_argument("--attempt")
    parser.add_argument("--prefix-receipt")
    parser.add_argument("--replay-mode", choices=list(VALID_MODES),
                        default="canary")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    def _pairs(values, what):
        parsed = {}
        for value in values:
            label, separator, target = value.partition("=")
            if not separator or not _SAFE_LABEL.fullmatch(label):
                raise SubmissionDefect("%s must be safe_label=value" % what)
            if label in parsed:
                raise SubmissionDefect("duplicate %s label %r" % (what, label))
            parsed[label] = target
        return parsed

    try:
        if args.prove_launch:
            document = prove_launch_path()
            payload = canonical_bytes(document)
            if args.out:
                Path(args.out).write_bytes(payload)
            print(payload.decode("utf-8"), end="")
            print("P0_R2_G2_AZURE_CLI_RESOLVED=%s"
                  % document["resolved_executable"])
            print("P0_R2_G2_LAUNCH_PATH_PROVED=1")
            return 0

        if args.build_context:
            document = build_context(
                root=args.root, context_dir=args.context_dir,
                source_commit=args.source_commit, task_path=args.task_path,
                embedded_objects=_pairs(args.embedded_object,
                                        "--embedded-object"),
                machine_receipts=_pairs(args.machine_receipt,
                                        "--machine-receipt"))
            payload = canonical_bytes(document)
            if args.out:
                Path(args.out).write_bytes(payload)
            print("P0_R2_G2_CONTEXT_BUILT=1")
            print("P0_R2_G2_CONTEXT_ENTRY_COUNT=%d" % len(EXPECTED_ENTRIES))
            return 0

        if args.verify_context:
            document = verify_context(
                root=args.root, context_dir=args.context_dir,
                expected_commit=args.source_commit,
                expected_task_path=args.task_path, attempt=args.attempt,
                mode=args.replay_mode)
            payload = canonical_bytes(document)
            if args.out:
                Path(args.out).write_bytes(payload)
            print(payload.decode("utf-8"), end="")
            print("P0_R2_G2_CONTEXT_ADMISSION=PASS")
            print("P0_R2_G2_CONTEXT_ENTRY_COUNT=%d"
                  % document["context"]["entry_count"])
            print("P0_R2_G2_CONTEXT_MAX_NATIVE_PATH=%d"
                  % document["context"]["maximum_native_path"])
            return 0

        document = submit_once(
            root=args.root, context_dir=args.context_dir,
            work_dir=args.work_dir, image=args.image, digest=args.digest,
            ready_anchor=args.ready_anchor, mode=args.replay_mode,
            attempt=args.attempt, prefix_receipt=args.prefix_receipt,
            source_commit=args.source_commit, task_path=args.task_path)
    except SubmissionDefect as exc:
        print("P0_R2_G2_HOST_SUBMISSION_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    if args.out:
        Path(args.out).write_bytes(canonical_bytes(document))
    print("P0_R2_G2_ACR_SUBMISSION=%s" % document["outcome"])
    print("P0_R2_G2_ACR_RUN_ID=%s" % document["acr_run_id"])
    print("P0_R2_G2_ACR_RUN_ID_COUNT=%d" % document["acr_run_id_count"])
    print("P0_R2_G2_ONE_SHOT_ENVELOPE_CONSUMED=%s"
          % str(document["one_shot_envelope_consumed"]).lower())
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0")
    return 0 if document["outcome"] == "PASS" else 3


if __name__ == "__main__":
    sys.exit(main())
