#!/usr/bin/env python3
"""Resolve the registered secondary benchmark for Study 5-EQ1.

Authority section 4.3 registers `Idavidrein/gpqa` (diamond split) as the
secondary benchmark, marks it ``gated: auto``, and registers
`TIGER-Lab/MMLU-Pro` (STEM slice) as the fallback if access is not obtained.
The section is explicit about *when*:

    The GPQA gate is resolved at P-0, before any model call. If access is not
    obtained at P-0, the registered fallback secondary is MMLU-Pro STEM. This
    choice is made before any outcome is observed and may not be revisited
    afterwards.

So this tool exists to make the decision auditable rather than asserted. It
probes only what the authority pins -- the exact revisions in section 4.3 --
and it decides on *file* access, not on repository metadata, because a gated
dataset still serves public metadata and would otherwise look available.

It performs unauthenticated HTTP GETs against the HuggingFace API and touches
no Azure resource and no model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USER_AGENT = "study5-eq1-secondary-benchmark-gate"

# Exactly the identities registered in authority section 4.3.
PRIMARY = ("HuggingFaceH4/MATH-500", "6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be")
REGISTERED_SECONDARY = ("Idavidrein/gpqa", "633f5ee89ab8ad4522a9f850766b73f62147ffdd")
REGISTERED_FALLBACK = (
    "TIGER-Lab/MMLU-Pro",
    "b189ec765aa7ed75c8acfea42df31fdae71f97be",
)
CONTAMINATION_REFERENCE = (
    "nathu0/transcoder-adapters-openthoughts3-stratified-55k",
    "b6d6ca48ac7e12517bd16411687a28e404cc2692",
)

# The file whose readability decides the gate for each repository. For GPQA this
# is deliberately the diamond split named in section 4.3, not an arbitrary file.
DECIDING_FILE = {
    "HuggingFaceH4/MATH-500": "test.jsonl",
    "Idavidrein/gpqa": "gpqa_diamond.csv",
    "TIGER-Lab/MMLU-Pro": "data/test-00000-of-00001.parquet",
    "nathu0/transcoder-adapters-openthoughts3-stratified-55k": "data/train.jsonl",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def _probe_file(url: str) -> dict[str, Any]:
    """Read the first bytes of a file, so the result reflects real readability."""

    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-1023"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read()
            return {
                "http_status": response.status,
                "readable": True,
                "bytes_read": len(body),
                "content_length_header": response.headers.get("Content-Range")
                or response.headers.get("Content-Length"),
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        return {
            "http_status": exc.code,
            "readable": False,
            "bytes_read": 0,
            "content_length_header": None,
            "error": str(exc.reason)[:200],
        }
    except Exception as exc:  # pragma: no cover - network-shape dependent
        return {
            "http_status": None,
            "readable": False,
            "bytes_read": 0,
            "content_length_header": None,
            "error": f"{type(exc).__name__}: {exc}"[:200],
        }


def probe_dataset(repo: str, revision: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "repo": repo,
        "registered_revision": revision,
        "probed_at_utc": utc_now(),
        "authenticated": False,
        "token_used": False,
    }
    try:
        meta = _get_json(f"https://huggingface.co/api/datasets/{repo}")
        record["metadata_http_status"] = 200
        record["gated"] = meta.get("gated")
        record["private"] = meta.get("private")
    except urllib.error.HTTPError as exc:
        record["metadata_http_status"] = exc.code
        record["gated"] = None
        record["private"] = None

    try:
        tree = _get_json(
            f"https://huggingface.co/api/datasets/{repo}/tree/{revision}?recursive=true"
        )
        files = sorted(t["path"] for t in tree if t["type"] == "file")
        record["revision_resolves"] = True
        record["file_count"] = len(files)
        record["files"] = files
    except urllib.error.HTTPError as exc:
        record["revision_resolves"] = False
        record["revision_http_status"] = exc.code
        record["files"] = []

    deciding = DECIDING_FILE.get(repo)
    record["deciding_file"] = deciding
    if deciding and deciding in record.get("files", []):
        url = f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{deciding}"
        record["file_probe"] = _probe_file(url)
        record["accessible"] = bool(record["file_probe"]["readable"])
    else:
        record["file_probe"] = None
        record["accessible"] = False
    return record


def resolve() -> dict[str, Any]:
    primary = probe_dataset(*PRIMARY)
    secondary = probe_dataset(*REGISTERED_SECONDARY)
    fallback = probe_dataset(*REGISTERED_FALLBACK)
    contamination = probe_dataset(*CONTAMINATION_REFERENCE)

    gpqa_access_obtained = bool(secondary["accessible"])
    selected = REGISTERED_SECONDARY if gpqa_access_obtained else REGISTERED_FALLBACK

    return {
        "schema_version": "study5-eq1-secondary-benchmark-gate-v1",
        "authority_section": "4.3",
        "resolved_at_utc": utc_now(),
        "resolved_at_phase": "P-0",
        "resolved_before_any_model_call": True,
        "resolved_before_any_outcome_observed": True,
        "may_be_revisited_afterwards": False,
        "huggingface_token_available_on_execution_host": False,
        "gpqa_access_obtained": gpqa_access_obtained,
        "selected_secondary_repo": selected[0],
        "selected_secondary_revision": selected[1],
        "selected_secondary_is_the_registered_fallback": not gpqa_access_obtained,
        "selected_secondary_slice": (
            "diamond" if gpqa_access_obtained else "STEM"
        ),
        "primary_benchmark": primary,
        "registered_secondary": secondary,
        "registered_fallback": fallback,
        "contamination_reference": contamination,
        "note": (
            "The gate is decided on readability of the deciding data file at the "
            "registered revision, not on repository metadata, because a gated "
            "dataset still serves public metadata and would otherwise appear "
            "available."
        ),
    }


def write(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    payload = resolve()
    digest = write(Path(args.out), payload)
    print(f"{args.out}  sha256 {digest}")
    print(
        f"gpqa_access_obtained={payload['gpqa_access_obtained']}  "
        f"selected={payload['selected_secondary_repo']} "
        f"({payload['selected_secondary_slice']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
