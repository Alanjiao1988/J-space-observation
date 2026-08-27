#!/usr/bin/env python3
"""Append-only run journal for Study 5-EQ1.

Implements authority section 9.1. The journal is the primary paper-traceability
artifact, so this module is deliberately strict:

* a record is appended and ``fsync``-ed before the next step is allowed to
  begin, so an interrupted invocation still leaves a complete prefix;
* the journal key ``<phase>/<step_id>`` is unique across every journal file in
  the namespace; a duplicate key is a hard blocker (authority section 9.1) and
  is raised, never silently resolved;
* an existing record is never rewritten. The only supported mutation is append.

The module is importable and also usable from a shell step:

    python tools/journal.py append --phase P-0 --step-id P0-001 ...
    python tools/journal.py verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

JOURNAL_DIRNAME = "journal"

RECORD_FIELDS = (
    "ts_start_utc",
    "ts_end_utc",
    "duration_s",
    "phase",
    "step_id",
    "host",
    "gpu_index",
    "gpu_seconds",
    "command_sha256",
    "inputs_sha256",
    "outputs_sha256",
    "exit_status",
    "blocker_id",
    "note",
)


class DuplicateJournalKey(RuntimeError):
    """Raised when a journal key would be written twice.

    Authority section 9.1 registers this as a hard blocker, so it is an error
    and not a warning.
    """


class JournalIntegrityError(RuntimeError):
    """Raised when an existing journal file cannot be parsed or is malformed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def journal_key(phase: str, step_id: str) -> str:
    return f"{phase}/{step_id}"


@dataclass(frozen=True)
class JournalRecord:
    ts_start_utc: str
    ts_end_utc: str
    phase: str
    step_id: str
    host: str
    exit_status: str
    command_sha256: str
    duration_s: float | None = None
    gpu_index: int | None = None
    gpu_seconds: float = 0.0
    inputs_sha256: list[str] = field(default_factory=list)
    outputs_sha256: list[str] = field(default_factory=list)
    blocker_id: str | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        duration = self.duration_s
        if duration is None:
            duration = (
                parse_utc(self.ts_end_utc) - parse_utc(self.ts_start_utc)
            ).total_seconds()
        payload = {
            "ts_start_utc": self.ts_start_utc,
            "ts_end_utc": self.ts_end_utc,
            "duration_s": round(float(duration), 3),
            "phase": self.phase,
            "step_id": self.step_id,
            "host": self.host,
            "gpu_index": self.gpu_index,
            "gpu_seconds": round(float(self.gpu_seconds), 3),
            "command_sha256": self.command_sha256,
            "inputs_sha256": list(self.inputs_sha256),
            "outputs_sha256": list(self.outputs_sha256),
            "exit_status": self.exit_status,
            "blocker_id": self.blocker_id,
            "note": self.note,
        }
        missing = [name for name in RECORD_FIELDS if name not in payload]
        if missing:
            raise JournalIntegrityError(f"record is missing fields: {missing}")
        return payload


class Journal:
    """Append-only journal rooted at a Study 5-EQ1 namespace directory."""

    def __init__(self, namespace: str | os.PathLike[str]) -> None:
        self.namespace = Path(namespace)
        self.journal_dir = self.namespace / JOURNAL_DIRNAME

    def path_for(self, phase: str) -> Path:
        return self.journal_dir / f"{phase}.jsonl"

    def iter_records(self) -> Iterator[tuple[Path, int, dict[str, Any]]]:
        if not self.journal_dir.is_dir():
            return
        for path in sorted(self.journal_dir.glob("*.jsonl")):
            with open(path, "r", encoding="utf-8") as handle:
                for lineno, line in enumerate(handle, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise JournalIntegrityError(
                            f"{path}:{lineno} is not valid JSON: {exc}"
                        ) from exc
                    yield path, lineno, record

    def existing_keys(self) -> dict[str, str]:
        keys: dict[str, str] = {}
        for path, lineno, record in self.iter_records():
            try:
                key = journal_key(record["phase"], record["step_id"])
            except KeyError as exc:
                raise JournalIntegrityError(
                    f"{path}:{lineno} has no {exc.args[0]} field"
                ) from exc
            if key in keys:
                raise DuplicateJournalKey(
                    f"duplicate journal key {key!r}: {keys[key]} and {path}:{lineno}"
                )
            keys[key] = f"{path}:{lineno}"
        return keys

    def append(self, record: JournalRecord) -> dict[str, Any]:
        key = journal_key(record.phase, record.step_id)
        existing = self.existing_keys()
        if key in existing:
            raise DuplicateJournalKey(
                f"journal key {key!r} already written at {existing[key]}; "
                "authority 9.1 registers a duplicate key as a hard blocker"
            )
        payload = record.to_dict()
        path = self.path_for(record.phase)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False, sort_keys=False) + "\n"
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        return payload

    def verify(self) -> dict[str, Any]:
        keys = self.existing_keys()
        per_phase: dict[str, int] = {}
        blockers: list[str] = []
        gpu_seconds = 0.0
        duration_s = 0.0
        for _path, _lineno, record in self.iter_records():
            per_phase[record["phase"]] = per_phase.get(record["phase"], 0) + 1
            gpu_seconds += float(record.get("gpu_seconds") or 0.0)
            duration_s += float(record.get("duration_s") or 0.0)
            if record.get("blocker_id"):
                blockers.append(record["blocker_id"])
        rollup = sha256_text("\n".join(sorted(keys)))
        return {
            "records": len(keys),
            "unique_keys": len(keys),
            "duplicate_keys": 0,
            "records_per_phase": per_phase,
            "blocker_ids": blockers,
            "total_gpu_seconds": round(gpu_seconds, 3),
            "total_accelerator_hours": round(gpu_seconds / 3600.0, 6),
            "total_wall_seconds": round(duration_s, 3),
            "journal_key_rollup_sha256": rollup,
        }


def _default_namespace() -> Path:
    return Path(__file__).resolve().parent.parent


def _cmd_append(args: argparse.Namespace) -> int:
    journal = Journal(args.namespace)
    record = JournalRecord(
        ts_start_utc=args.ts_start_utc,
        ts_end_utc=args.ts_end_utc or utc_now(),
        phase=args.phase,
        step_id=args.step_id,
        host=args.host or platform.node(),
        exit_status=args.exit_status,
        command_sha256=args.command_sha256,
        gpu_index=args.gpu_index,
        gpu_seconds=args.gpu_seconds,
        inputs_sha256=args.input or [],
        outputs_sha256=args.output or [],
        blocker_id=args.blocker_id,
        note=args.note,
    )
    payload = journal.append(record)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    journal = Journal(args.namespace)
    try:
        summary = journal.verify()
    except (DuplicateJournalKey, JournalIntegrityError) as exc:
        print(f"JOURNAL VERIFY FAILED: {exc}", file=sys.stderr)
        return 1
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0


def _cmd_hash(args: argparse.Namespace) -> int:
    for path in args.path:
        print(f"{sha256_file(path)}  {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", default=str(_default_namespace()))
    sub = parser.add_subparsers(dest="command", required=True)

    append = sub.add_parser("append", help="append one journal record")
    append.add_argument("--phase", required=True)
    append.add_argument("--step-id", required=True)
    append.add_argument("--ts-start-utc", required=True)
    append.add_argument("--ts-end-utc")
    append.add_argument("--host")
    append.add_argument("--gpu-index", type=int)
    append.add_argument("--gpu-seconds", type=float, default=0.0)
    append.add_argument("--command-sha256", required=True)
    append.add_argument("--input", action="append")
    append.add_argument("--output", action="append")
    append.add_argument("--exit-status", required=True)
    append.add_argument("--blocker-id")
    append.add_argument("--note", default="")
    append.set_defaults(func=_cmd_append)

    verify = sub.add_parser("verify", help="verify uniqueness and integrity")
    verify.set_defaults(func=_cmd_verify)

    hash_cmd = sub.add_parser("hash", help="sha256 one or more files")
    hash_cmd.add_argument("path", nargs="+")
    hash_cmd.set_defaults(func=_cmd_hash)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
