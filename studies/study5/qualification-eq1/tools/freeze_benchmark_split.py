#!/usr/bin/env python3
"""Freeze the development / confirmation split for Study 5-EQ1.

Authority section 10.1 requires the split to be a deterministic hash split,
frozen and committed at P-0, before any model call. Section 10.2 restricts this
invocation to development items only, and section 10.5 requires a committed
check that recomputes the split and proves no confirmation item id appears in
any journal record.

This runs **on the cloud VM**, which is where all byte transfer happens. The VM
cannot reach the HuggingFace origin, so the benchmark is fetched through the
mirror and checked against the origin-published authority recorded in the
acquisition manifest workflow -- the same discipline used for model weights.

The split rule is fixed here, before any measurement:

    digest(item) = sha256(f"{STUDY_ID}|{repo}|{revision}|{item_id}")

Items are ordered by that digest and the first ``--development-n`` become the
development slice. The rule depends only on registered identities, so it is
reproducible by anyone holding this file and the benchmark, and it cannot be
nudged by an outcome because no outcome exists yet.

Committing the confirmation *ids* is deliberate and is not a section 10.2
violation: no confirmation item is tokenized, prefilled, generated from, scored
or inspected. The ids are required precisely so the section 10.5 isolation proof
can be run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STUDY_ID = "STUDY5_EQ1"
PRIMARY_REPO = "HuggingFaceH4/MATH-500"
PRIMARY_REVISION = "6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be"
PRIMARY_FILE = "test.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(mirror: str, repo: str, revision: str, name: str) -> bytes:
    url = f"{mirror}/datasets/{repo}/resolve/{revision}/{name}"
    req = urllib.request.Request(url, headers={"User-Agent": "study5-eq1-split"})
    with urllib.request.urlopen(req, timeout=600) as response:
        return response.read()


def item_id(row: dict[str, Any], index: int) -> str:
    """A stable id for a benchmark row.

    MATH-500 publishes a ``unique_id``. If a future revision drops it, the
    problem text is hashed instead, which is stable across shuffles but would
    change if the benchmark itself changed -- and that is the correct behaviour,
    because it would no longer be the registered benchmark.
    """

    for key in ("unique_id", "id", "problem_id"):
        if row.get(key):
            return str(row[key])
    return "sha1:" + hashlib.sha1(str(row.get("problem", index)).encode()).hexdigest()


def digest_for(identifier: str, repo: str, revision: str) -> str:
    payload = f"{STUDY_ID}|{repo}|{revision}|{identifier}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build(raw: bytes, repo: str, revision: str, development_n: int) -> dict[str, Any]:
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    ids = [item_id(row, i) for i, row in enumerate(rows)]
    if len(set(ids)) != len(ids):
        raise SystemExit(
            f"benchmark ids are not unique ({len(ids)} rows, {len(set(ids))} ids); "
            "a hash split over duplicate ids would not be reproducible"
        )
    if development_n > len(ids):
        raise SystemExit(
            f"development_n {development_n} exceeds the {len(ids)} available items"
        )

    ranked = sorted(ids, key=lambda i: digest_for(i, repo, revision))
    development = sorted(ranked[:development_n])
    confirmation = sorted(ranked[development_n:])

    def rollup(values: list[str]) -> str:
        return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()

    return {
        "schema_version": "study5-eq1-benchmark-split-v1",
        "authority_section": "10.1",
        "frozen_at_utc": utc_now(),
        "frozen_at_phase": "P-0",
        "frozen_before_any_model_call": True,
        "study_id": STUDY_ID,
        "benchmark_repo": repo,
        "benchmark_revision": revision,
        "benchmark_file": PRIMARY_FILE,
        "benchmark_bytes": len(raw),
        "benchmark_sha256": hashlib.sha256(raw).hexdigest(),
        "split_rule": (
            "rank every item by sha256(f'{STUDY_ID}|{repo}|{revision}|{item_id}') "
            "ascending; the first development_n are development, the remainder "
            "are confirmation"
        ),
        "split_rule_depends_only_on_registered_identities": True,
        "total_items": len(ids),
        "development_n": len(development),
        "confirmation_n": len(confirmation),
        "development_ids": development,
        "confirmation_ids": confirmation,
        "development_rollup_sha256": rollup(development),
        "confirmation_rollup_sha256": rollup(confirmation),
        "disjoint": not (set(development) & set(confirmation)),
        "covers_every_item": len(development) + len(confirmation) == len(ids),
        "confirmation_items_touched_by_this_invocation": 0,
        "confirmation_bank_realized": False,
        "note": (
            "Confirmation ids are committed so the section 10.5 isolation proof "
            "can be run. No confirmation item is tokenized, prefilled, generated "
            "from, scored or inspected by this invocation."
        ),
    }


def git_blob_sha1(payload: bytes) -> str:
    """git's blob object id: SHA-1 over b"blob <len>\\0" + content.

    MATH-500's `test.jsonl` is not an LFS file, so the origin publishes only
    this id. It is the only origin-anchored authority available for it, and it
    is deliberately not confused with a content SHA-256.
    """

    return hashlib.sha1(b"blob %d\0" % len(payload) + payload).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mirror", default="https://hf-mirror.com")
    parser.add_argument("--development-n", type=int, default=200)
    parser.add_argument(
        "--expected-git-blob-sha1",
        required=True,
        help="the origin-published git blob id for the benchmark file",
    )
    parser.add_argument("--expected-bytes", type=int)
    args = parser.parse_args(argv)

    raw = fetch(args.mirror, PRIMARY_REPO, PRIMARY_REVISION, PRIMARY_FILE)

    if args.expected_bytes and len(raw) != args.expected_bytes:
        raise SystemExit(
            f"benchmark is {len(raw)} bytes, origin says {args.expected_bytes}; "
            "mirrored bytes rejected"
        )
    actual_blob = git_blob_sha1(raw)
    if actual_blob != args.expected_git_blob_sha1:
        raise SystemExit(
            f"benchmark git blob id is {actual_blob}, origin says "
            f"{args.expected_git_blob_sha1}; mirrored bytes rejected"
        )

    payload = build(raw, PRIMARY_REPO, PRIMARY_REVISION, args.development_n)
    payload["benchmark_git_blob_sha1"] = actual_blob
    payload["benchmark_authority_kind"] = "git_blob_sha1"
    payload["benchmark_authority_verified_against_origin"] = True
    payload["benchmark_fetched_via"] = args.mirror
    payload["benchmark_fetched_by"] = "the cloud VM, not the operator workstation"

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

    print(f"{args.out}  sha256 {hashlib.sha256(text.encode('utf-8')).hexdigest()}")
    print(
        f"items={payload['total_items']} development={payload['development_n']} "
        f"confirmation={payload['confirmation_n']} disjoint={payload['disjoint']}"
    )
    print(f"benchmark_sha256={payload['benchmark_sha256']}")
    print(f"benchmark_git_blob_sha1={actual_blob} (matches origin)")
    print(f"development_rollup={payload['development_rollup_sha256']}")
    print(f"confirmation_rollup={payload['confirmation_rollup_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
