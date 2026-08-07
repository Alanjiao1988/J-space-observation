#!/usr/bin/env python3
"""Validate the frozen, model-free Study 2 Stage P package."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "jspace_observation"))

import study2_protocol as protocol  # noqa: E402


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _verify_protected_record(root: Path, relative: str, domain: str, expected_rollup: str, expected_count: int) -> dict[str, Any]:
    document = protocol.load_json(root / relative)
    if document["file_count"] != expected_count or len(document["files"]) != expected_count:
        raise protocol.ProtocolError(f"protected record count mismatch: {relative}")
    rows: list[dict[str, Any]] = []
    for registered in document["files"]:
        path = root / registered["path"]
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        observed = {
            "path": registered["path"],
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
        if observed != registered:
            raise protocol.ProtocolError(f"protected byte differs: {registered['path']}")
        rows.append(observed)
    payload = "\n".join(f"{row['path']} {row['sha256']}" for row in rows)
    rollup = hashlib.sha256(f"{domain}\n{payload}\n".encode("utf-8")).hexdigest()
    if rollup != expected_rollup or document["rollup_sha256"] != expected_rollup:
        raise protocol.ProtocolError(f"protected rollup differs: {relative}")
    return {"file_count": expected_count, "rollup_sha256": rollup}


def _verify_starting_state(root: Path) -> dict[str, Any]:
    start_tree = _git(root, "rev-parse", f"{protocol.START_COMMIT}^{{tree}}")
    if start_tree != protocol.START_TREE:
        raise protocol.ProtocolError("operator-supplied starting commit/tree mismatch")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", protocol.START_COMMIT, "HEAD"],
        cwd=root,
        check=False,
    ).returncode != 0:
        raise protocol.ProtocolError("starting commit is not an ancestor of HEAD")
    if _git(root, "status", "--porcelain"):
        raise protocol.ProtocolError("validation checkout is dirty")
    authority = root / "studies/study2/prompts/stage_p_protocol_design_prompt.md"
    if authority.stat().st_size != protocol.AUTHORITY_BYTES or protocol.sha256_file(authority) != protocol.AUTHORITY_SHA256:
        raise protocol.ProtocolError("Stage P authority bytes differ")
    receipt = protocol.load_json(root / "studies/study2/handoff_receipt.json")
    if receipt["authority_prompt"]["sha256"] != protocol.AUTHORITY_SHA256 or receipt["authority_prompt"]["bytes"] != protocol.AUTHORITY_BYTES:
        raise protocol.ProtocolError("handoff receipt authority binding differs")
    if _git(root, "rev-parse", "db8c100db0c16306a702d348a49a90480f440629^{tree}") != "032109e20e32f43126ade0d45c0abffa5c2de85f":
        raise protocol.ProtocolError("Study 2 bootstrap authority tree differs")
    if _git(root, "rev-parse", "6409d2c6d665187e4459d94d490a20d7b085e8af^{tree}") != "bc8b80cb0e66f9426dcdedd52b624c892caa3fc9":
        raise protocol.ProtocolError("Study 1 terminal tree differs")
    decisions = (root / "docs/decision_log.md").read_text(encoding="utf-8")
    if "## D32 - Close the frozen S3 E0 on insufficient behavioral support" not in decisions:
        raise protocol.ProtocolError("D32 terminal decision missing")
    if "## D33 - Close the original program as Study 1 and open independent Study 2" not in decisions:
        raise protocol.ProtocolError("D33 boundary decision missing")
    evidence_lines = [line for line in (root / "paper/evidence_ledger.csv").read_text(encoding="utf-8").splitlines() if line]
    if not evidence_lines[-1].startswith("EV-0016,"):
        raise protocol.ProtocolError("scientific evidence ledger no longer ends at EV-0016")
    return {
        "starting_commit": protocol.START_COMMIT,
        "starting_tree": start_tree,
        "head": _git(root, "rev-parse", "HEAD"),
        "tree": _git(root, "rev-parse", "HEAD^{tree}"),
        "authority_sha256": protocol.AUTHORITY_SHA256,
        "authority_bytes": protocol.AUTHORITY_BYTES,
        "evidence_tail": "EV-0016",
        "decision_boundary": "D33",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true", help="candidate-only validation before commit")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    try:
        document = protocol.load_and_validate_protocol(root)
        banks = protocol.verify_task_banks(root, require_manifest=True)
        if not args.allow_dirty:
            if document["status"] != "FROZEN_AWAITING_STAGE_T":
                raise protocol.ProtocolError("final validation requires the frozen protocol lifecycle")
            if banks["manifest"]["status"] != "FROZEN_MODEL_FREE_BANKS":
                raise protocol.ProtocolError("final validation requires the frozen bank-manifest lifecycle")
        anchors = protocol.verify_protected_anchors(root)
        if args.allow_dirty:
            start = {
                "starting_commit": protocol.START_COMMIT,
                "starting_tree": _git(root, "rev-parse", f"{protocol.START_COMMIT}^{{tree}}"),
                "head": _git(root, "rev-parse", "HEAD"),
                "tree": _git(root, "rev-parse", "HEAD^{tree}"),
                "candidate_dirty_validation": True,
            }
        else:
            start = _verify_starting_state(root)
        protected_v1 = _verify_protected_record(
            root,
            "docs/phase1_0d_protected_bytes.json",
            "jspace-phase1-0d/protected-bytes/v1",
            "436ed331c7dd53fa6387d6b52447bc72edf166bbb3640b7f7723a8766bdf51dd",
            152,
        )
        protected_v2 = _verify_protected_record(
            root,
            "docs/phase1_0d_rv2_protected_bytes.json",
            "jspace-phase1-0d/rv2-protected-bytes/v1",
            "ef5a417c572f7da94a562411b752d74b48da2e28aa3aa1491db9bc34dfbde82a",
            36,
        )
    except (protocol.ProtocolError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"BLOCKED_ON_STUDY2_PREREGISTRATION_INTEGRITY: {exc}", file=sys.stderr)
        return 1
    result = {
        "status": "NONTERMINAL_CHECKPOINT_STUDY2_PROTOCOL_FROZEN_AWAITING_TOKENIZER_GATE_AND_EXECUTION",
        "protocol_sha256": protocol.sha256_file(root / "studies/study2/protocol/reasoning_internalization_protocol.json"),
        "schema_sha256": protocol.sha256_file(root / "studies/study2/protocol/reasoning_internalization_protocol.schema.json"),
        "markdown_sha256": protocol.sha256_file(root / "studies/study2/protocol/reasoning_internalization_protocol.md"),
        "manifest_sha256": protocol.sha256_file(root / "studies/study2/data/task_bank_manifest.json"),
        "models": document["identities"]["models"],
        "start": start,
        "banks": banks,
        "protected_anchors": anchors,
        "phase1_0d_protected_v1": protected_v1,
        "phase1_0d_protected_v2": protected_v2,
        "zero_operations": document["operation_limits"],
    }
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(f"STATUS={result['status']}")
        print(f"PROTOCOL_SHA256={result['protocol_sha256']}")
        print(f"SCHEMA_SHA256={result['schema_sha256']}")
        print(f"MARKDOWN_SHA256={result['markdown_sha256']}")
        print(f"MANIFEST_SHA256={result['manifest_sha256']}")
        print(f"ROLE_COUNTS={json.dumps(banks['role_counts'], sort_keys=True)}")
        print("PROTECTED_BYTES=152/v1 36/v2")
        print("MODEL_TOKENIZER_LENS_ACTIVATION_OPERATIONS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
