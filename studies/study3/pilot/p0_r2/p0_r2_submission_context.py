#!/usr/bin/env python3
"""Build and verify P0-R2's minimal, committed-object ACR context.

The P0-R1 host failure happened before Azure accepted a run: Azure CLI walked
an extracted full-repository context and encountered a 265-character Windows
path. P0-R2 never presents a repository tree to the packer. Its context has
exactly two regular files at its root and is independently re-read immediately
before submission.

This module is model-free. It imports only the Python standard library and
never contacts Azure.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


SCHEMA_VERSION = "study3-p0-r2-minimal-acr-context-v1"
RECEIPT_SCHEMA_VERSION = "study3-p0-r2-context-admission-receipt-v1"
CONTEXT_DIRECTORY_NAME = "acrctx"
TASK_CONTEXT_NAME = "task.yaml"
MANIFEST_NAME = "context_manifest.json"
EXPECTED_ENTRIES = (MANIFEST_NAME, TASK_CONTEXT_NAME)
WINDOWS_NATIVE_PATH_CEILING = 240
STAGE = "STUDY3-P0-R2"

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SAFE_LABEL = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class ContextDefect(Exception):
    """The source context is not the exact, small, committed context."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_sha40(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SHA40.fullmatch(value):
        raise ContextDefect("%s is not a lowercase 40-character Git id" % label)
    return value


def _safe_repo_path(value: str, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContextDefect("%s is required" % label)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or \
            str(path) in (".", "") or "\\" in value:
        raise ContextDefect("%s is not a safe repository path: %r" %
                            (label, value))
    return str(path)


def _git(root: Path, args: list[str], *, binary: bool = False):
    completed = subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True,
        text=not binary, check=False)
    if completed.returncode:
        stderr = completed.stderr if isinstance(completed.stderr, str) \
            else completed.stderr.decode("utf-8", "replace")
        raise ContextDefect(
            "git %s failed: %s" % (" ".join(args), stderr.strip()))
    return completed.stdout


def git_object_identity(root: Path, commit: str, repo_path: str) -> dict:
    """Read one regular file from Git, never from the worktree."""
    root = Path(root).resolve()
    commit = _require_sha40(commit, "source commit")
    repo_path = _safe_repo_path(repo_path, "source path")
    resolved = _git(root, ["rev-parse", "%s^{commit}" % commit]).strip()
    if resolved != commit:
        raise ContextDefect("source commit resolved to a different object")
    line = _git(root, ["ls-tree", commit, "--", repo_path]).strip()
    fields = line.split(None, 3)
    if len(fields) != 4 or fields[0] != "100644" or fields[1] != "blob" \
            or fields[3] != repo_path:
        raise ContextDefect(
            "%s is not one regular 100644 blob at %s" % (repo_path, commit))
    blob = _require_sha40(fields[2], "%s blob" % repo_path)
    payload = _git(root, ["cat-file", "blob", blob], binary=True)
    return {
        "source_path": repo_path,
        "git_blob": blob,
        "bytes": len(payload),
        "sha256": _sha256(payload),
        "payload": payload,
    }


def source_identity(root: Path, commit: str) -> dict:
    commit = _require_sha40(commit, "source commit")
    resolved = _git(Path(root), ["rev-parse", "%s^{commit}" % commit]).strip()
    if resolved != commit:
        raise ContextDefect("source commit resolved to %s" % resolved)
    tree = _git(Path(root), ["rev-parse", "%s^{tree}" % commit]).strip()
    return {"commit": commit, "tree": _require_sha40(tree, "source tree")}


def _context_directory(path: Path, *, create: bool) -> Path:
    path = Path(path)
    if path.name != CONTEXT_DIRECTORY_NAME:
        raise ContextDefect(
            "the context directory must use the short fixed name %r" %
            CONTEXT_DIRECTORY_NAME)
    if path.is_symlink():
        raise ContextDefect("the context directory may not be a symlink")
    if create:
        path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise ContextDefect("the context directory does not exist")
    return path.resolve()


def _entries(context_dir: Path) -> list[str]:
    names = []
    for entry in os.scandir(context_dir):
        if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
            raise ContextDefect(
                "context entry %r is not a regular non-symlink file" %
                entry.name)
        names.append(entry.name)
    names.sort()
    if tuple(names) != EXPECTED_ENTRIES:
        raise ContextDefect(
            "context entries %r are not exactly %r" %
            (names, list(EXPECTED_ENTRIES)))
    return names


def _platform_kind(environ=None, os_name=None) -> str:
    environ = os.environ if environ is None else environ
    os_name = os.name if os_name is None else os_name
    if os_name == "nt":
        return "windows-native"
    markers = "%s %s" % (environ.get("MSYSTEM", ""),
                          environ.get("OSTYPE", ""))
    if any(marker in markers.upper()
           for marker in ("MSYS", "MINGW", "CYGWIN")):
        return "windows-posix-shell"
    return "posix"


def _native_path(path: Path, platform_kind: str, converter=None) -> str:
    resolved = str(Path(path).resolve())
    if platform_kind == "windows-native":
        return resolved.replace("\\", "/")
    if platform_kind == "windows-posix-shell":
        if converter is not None:
            converted = converter(resolved)
        else:
            try:
                completed = subprocess.run(
                    ["cygpath", "-aw", resolved], capture_output=True,
                    text=True, check=False)
            except OSError as exc:
                raise ContextDefect(
                    "native Windows path conversion is unavailable: %s" % exc)
            if completed.returncode:
                raise ContextDefect(
                    "native Windows path conversion failed: %s" %
                    completed.stderr.strip())
            converted = completed.stdout.strip()
        if not converted or not re.match(r"^[A-Za-z]:[\\/]", converted):
            raise ContextDefect(
                "native Windows path conversion returned %r" % converted)
        return converted.replace("\\", "/")
    return resolved


def _parse_embedded(values: list[str]) -> dict[str, str]:
    parsed = {}
    for value in values:
        label, separator, repo_path = value.partition("=")
        if not separator or not _SAFE_LABEL.fullmatch(label):
            raise ContextDefect(
                "--embedded-object must be safe_label=repository/path")
        if label in parsed:
            raise ContextDefect("duplicate embedded-object label %r" % label)
        parsed[label] = _safe_repo_path(repo_path, "embedded object path")
    return parsed


def build(root: Path, context_dir: Path, source_commit: str, task_path: str,
          embedded_objects=None) -> dict:
    """Create the two files exclusively from exact committed Git objects."""
    root = Path(root).resolve()
    context_dir = _context_directory(context_dir, create=True)
    if any(os.scandir(context_dir)):
        raise ContextDefect(
            "the minimal context directory must start empty; reruns are refused")
    source = source_identity(root, source_commit)
    task = git_object_identity(root, source_commit, task_path)

    embedded = []
    for label, repo_path in sorted((embedded_objects or {}).items()):
        if not _SAFE_LABEL.fullmatch(label):
            raise ContextDefect("unsafe embedded-object label %r" % label)
        identity = git_object_identity(root, source_commit, repo_path)
        embedded.append({
            "label": label,
            "source_path": identity["source_path"],
            "git_blob": identity["git_blob"],
            "bytes": identity["bytes"],
            "sha256": identity["sha256"],
            "encoding": "base64",
            "payload": base64.b64encode(identity["payload"]).decode("ascii"),
        })

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "context_contract": "two-root-level-regular-files-only",
        "file_set": list(EXPECTED_ENTRIES),
        "source": source,
        "task": {
            "source_path": task["source_path"],
            "context_name": TASK_CONTEXT_NAME,
            "git_blob": task["git_blob"],
            "bytes": task["bytes"],
            "sha256": task["sha256"],
        },
        "embedded_governance_objects": embedded,
        "contains_model_bytes": False,
        "contains_checkpoint_bytes": False,
        "contains_corpus_bytes": False,
        "contains_result_bytes": False,
        "contains_mutable_worktree_bytes": False,
    }
    manifest_payload = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    for name, payload in ((TASK_CONTEXT_NAME, task["payload"]),
                          (MANIFEST_NAME, manifest_payload)):
        path = context_dir / name
        try:
            with path.open("xb") as handle:
                handle.write(payload)
        except FileExistsError as exc:
            raise ContextDefect(
                "context path %s already exists; reruns are refused" % path
            ) from exc
    return manifest


def verify(root: Path, context_dir: Path, *, expected_commit=None,
           expected_task_path=None, native_ceiling=WINDOWS_NATIVE_PATH_CEILING,
           environ=None, os_name=None, converter=None) -> dict:
    """Re-read the context and return its admission receipt."""
    root = Path(root).resolve()
    context_dir = _context_directory(context_dir, create=False)
    names = _entries(context_dir)
    manifest_path = context_dir / MANIFEST_NAME
    task_path = context_dir / TASK_CONTEXT_NAME
    try:
        manifest_raw = manifest_path.read_bytes()
        manifest = json.loads(manifest_raw.decode("utf-8"))
        task_raw = task_path.read_bytes()
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContextDefect("the minimal context is unreadable: %s" % exc)

    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ContextDefect("the context manifest schema is not registered")
    if manifest.get("file_set") != list(EXPECTED_ENTRIES):
        raise ContextDefect("the manifest does not bind the exact file set")
    for field in ("contains_model_bytes", "contains_checkpoint_bytes",
                  "contains_corpus_bytes", "contains_result_bytes",
                  "contains_mutable_worktree_bytes"):
        if manifest.get(field) is not False:
            raise ContextDefect("the manifest does not prove %s=false" % field)

    source = manifest.get("source") or {}
    commit = _require_sha40(source.get("commit"), "manifest source commit")
    tree = _require_sha40(source.get("tree"), "manifest source tree")
    if expected_commit and commit != expected_commit:
        raise ContextDefect(
            "context commit %s is not expected commit %s" %
            (commit, expected_commit))
    actual_source = source_identity(root, commit)
    if actual_source["tree"] != tree:
        raise ContextDefect("the manifest source tree does not match Git")

    task = manifest.get("task") or {}
    source_task_path = _safe_repo_path(task.get("source_path"),
                                       "manifest task source path")
    if expected_task_path and source_task_path != expected_task_path:
        raise ContextDefect("the manifest names a foreign task source path")
    task_git = git_object_identity(root, commit, source_task_path)
    if task.get("context_name") != TASK_CONTEXT_NAME \
            or task.get("git_blob") != task_git["git_blob"] \
            or task.get("bytes") != len(task_raw) \
            or task.get("sha256") != _sha256(task_raw) \
            or task_raw != task_git["payload"]:
        raise ContextDefect("task.yaml is not the exact registered Git blob")

    embedded_receipts = []
    labels = set()
    for entry in manifest.get("embedded_governance_objects") or []:
        label = entry.get("label")
        if not isinstance(label, str) or not _SAFE_LABEL.fullmatch(label) \
                or label in labels:
            raise ContextDefect("embedded governance labels are invalid")
        labels.add(label)
        repo_path = _safe_repo_path(entry.get("source_path"),
                                    "embedded source path")
        try:
            payload = base64.b64decode(
                str(entry.get("payload", "")).encode("ascii"), validate=True)
        except (binascii.Error, UnicodeEncodeError, ValueError) as exc:
            raise ContextDefect(
                "embedded governance object %s is not lossless base64" % label
            ) from exc
        git_identity = git_object_identity(root, commit, repo_path)
        if entry.get("encoding") != "base64" \
                or entry.get("git_blob") != git_identity["git_blob"] \
                or entry.get("bytes") != len(payload) \
                or entry.get("sha256") != _sha256(payload) \
                or payload != git_identity["payload"]:
            raise ContextDefect(
                "embedded governance object %s differs from Git" % label)
        embedded_receipts.append({
            key: entry[key] for key in
            ("label", "source_path", "git_blob", "bytes", "sha256")})

    kind = _platform_kind(environ=environ, os_name=os_name)
    native = {}
    for path in (context_dir, manifest_path, task_path):
        native[path.name if path != context_dir else "context_directory"] = \
            _native_path(path, kind, converter=converter)
    maximum = max(len(value) for value in native.values())
    if kind.startswith("windows") and maximum > int(native_ceiling):
        raise ContextDefect(
            "maximum native context path length %d exceeds ceiling %d" %
            (maximum, int(native_ceiling)))

    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "stage": STAGE,
        "outcome": "PASS",
        "source": actual_source,
        "context": {
            "directory_name": CONTEXT_DIRECTORY_NAME,
            "entries": names,
            "entry_count": len(names),
            "task": {
                "source_path": source_task_path,
                "git_blob": task_git["git_blob"],
                "bytes": len(task_raw),
                "sha256": _sha256(task_raw),
            },
            "manifest": {
                "bytes": len(manifest_raw),
                "sha256": _sha256(manifest_raw),
            },
            "embedded_governance_objects": embedded_receipts,
            "all_entries_regular_non_symlink": True,
            "contains_only_committed_governance_bytes": True,
        },
        "native_paths": {
            "platform_kind": kind,
            "paths": native,
            "maximum_length": maximum,
            "windows_ceiling": int(native_ceiling),
            "windows_ceiling_enforced": kind.startswith("windows"),
        },
        "azure_cli_command_contract": {
            "file_argument": TASK_CONTEXT_NAME,
            "final_context_argument": str(context_dir),
            "full_repository_context_forbidden": True,
            "credentials_recorded": False,
        },
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
        "scored_rows": 0,
    }


def acr_run_command(*, registry: str, subscription: str, image: str,
                    digest: str, ready_anchor: str, mode: str, attempt: str,
                    context_dir: Path) -> list[str]:
    """Return the exact safe command; execution belongs to the successor."""
    if mode not in ("packing-canary", "live"):
        raise ContextDefect("ACR mode must be packing-canary or live")
    if mode == "packing-canary" and not attempt.startswith(
            "p0r2-g1-packing-canary-"):
        raise ContextDefect("packing canary attempt uses a foreign namespace")
    if mode == "live" and not attempt.startswith("p0r2-g1-live-"):
        raise ContextDefect("live attempt uses a foreign namespace")
    if not registry or not subscription or not image \
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest or ""):
        raise ContextDefect("registry, subscription, image and digest are required")
    _require_sha40(ready_anchor, "ready anchor")
    context_dir = _context_directory(context_dir, create=False)
    return [
        "az", "acr", "run",
        "--registry", registry,
        "--subscription", subscription,
        "--file", TASK_CONTEXT_NAME,
        "--set", "IMAGE=%s" % image,
        "--set", "DIGEST=%s" % digest,
        "--set", "READY_ANCHOR=%s" % ready_anchor,
        "--set", "MODE=%s" % mode,
        "--set", "ATTEMPT=%s" % attempt,
        str(context_dir),
    ]


def write_receipt(path: Path, receipt: dict, context_dir: Path) -> None:
    path = Path(path).resolve()
    context_dir = Path(context_dir).resolve()
    try:
        if os.path.commonpath([str(path), str(context_dir)]) == str(context_dir):
            raise ContextDefect(
                "the admission receipt must remain outside the two-file context")
    except ValueError:
        pass
    payload = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(
        "utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise ContextDefect(
            "admission receipt already exists; reruns are refused") from exc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--identity", action="store_true")
    parser.add_argument("--root")
    parser.add_argument("--source-commit")
    parser.add_argument("--task-path")
    parser.add_argument("--context-dir")
    parser.add_argument("--receipt")
    parser.add_argument("--embedded-object", action="append", default=[])
    parser.add_argument("--windows-path-ceiling", type=int,
                        default=WINDOWS_NATIVE_PATH_CEILING)
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "module": "p0_r2_submission_context.py",
            "context_entries": list(EXPECTED_ENTRIES),
            "windows_native_path_ceiling": WINDOWS_NATIVE_PATH_CEILING,
            "reads_task_from_git_object": True,
            "reads_mutable_worktree_task": False,
            "model_operations_performed": 0,
        }, indent=2, sort_keys=True))
        return 0
    required = {
        "--root": args.root,
        "--source-commit": args.source_commit,
        "--task-path": args.task_path,
        "--context-dir": args.context_dir,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        parser.error("%s required" % ", ".join(missing))
    try:
        embedded = _parse_embedded(args.embedded_object)
        if args.build:
            build(args.root, args.context_dir, args.source_commit,
                  args.task_path, embedded_objects=embedded)
        receipt = verify(
            args.root, args.context_dir,
            expected_commit=args.source_commit,
            expected_task_path=args.task_path,
            native_ceiling=args.windows_path_ceiling)
        if args.receipt:
            write_receipt(args.receipt, receipt, args.context_dir)
    except (ContextDefect, OSError) as exc:
        print("P0_R2_CONTEXT_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3
    print("P0_R2_CONTEXT_ADMISSION=PASS")
    print("P0_R2_CONTEXT_ENTRY_COUNT=2")
    print("P0_R2_CONTEXT_MAX_NATIVE_PATH=%d" %
          receipt["native_paths"]["maximum_length"])
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
