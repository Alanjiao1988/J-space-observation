#!/usr/bin/env python3
"""Normalize captured failure text into a comparable signature.

A raw pytest ``longrepr`` embeds the checkout path, temporary directory names,
object addresses and line numbers that move whenever unrelated code moves. Two
runs of the *same* failure therefore never produce identical raw text, and
comparing raw text would make the differential suite unusable. Comparing only
the node id would make it vacuous.

The normalization removes exactly the things that cannot carry meaning across
two checkouts in one container, and nothing else:

* the checkout roots ``/workspace/base`` and ``/workspace/src``;
* pytest and OS temporary directories;
* hexadecimal object addresses;
* absolute site-packages paths;
* trailing whitespace and blank-line runs.

Everything that does carry meaning -- the assertion, the exception type, the
message, the order of frames -- is preserved verbatim.

This module is model-free and never writes into a checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys

SCHEMA_VERSION = "study3-p0-r2-normalized-failure-signature-v2"

_SUBSTITUTIONS = (
    # The checkout root is the one thing that is guaranteed to differ between
    # the two clones and guaranteed to mean nothing. The negative lookahead
    # ends the match at a non-path character -- a quote, a bracket, a comma,
    # whitespace or end of line -- so PosixPath('/workspace/base') normalizes
    # exactly like /workspace/base/tests/x.py does, while /workspace/baseline
    # would not be touched.
    (re.compile(r"/workspace/(?:base|src|head)(?![A-Za-z0-9_-])"), "<CHECKOUT>"),
    (re.compile(r"/tmp/pytest-of-[^/\s]+/pytest-\d+(?:/[^\s:'\"]*)?"), "<PYTEST_TMP>"),
    (re.compile(r"/tmp/[A-Za-z0-9_]{6,}"), "<TMP>"),
    (re.compile(r"0x[0-9a-fA-F]{6,}"), "<ADDR>"),
    (re.compile(r"/usr/local/lib/python3\.\d+/site-packages"), "<SITE_PACKAGES>"),
    (re.compile(r"\bat 0x[0-9a-fA-F]+\b"), "at <ADDR>"),
    (re.compile(r"[ \t]+$", re.MULTILINE), ""),
    (re.compile(r"\n{3,}"), "\n\n"),
)


def normalize(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    for pattern, replacement in _SUBSTITUTIONS:
        normalized = pattern.sub(replacement, normalized)
    return normalized.strip() + "\n"


def signature(record: dict) -> dict:
    normalized = normalize(record.get("longrepr") or "")
    return {
        "nodeid": record["nodeid"],
        "phase": record.get("phase"),
        "kind": record.get("kind"),
        "normalized_longrepr": normalized,
        "normalized_bytes": len(normalized.encode("utf-8")),
        "normalized_sha256":
            hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "first_line": normalized.splitlines()[0] if normalized.strip() else "",
    }


def summarize(capture: dict) -> dict:
    records = capture.get("non_passing") or []
    signatures = sorted((signature(item) for item in records),
                        key=lambda item: (item["nodeid"], item["phase"] or ""))
    return {
        "schema_version": SCHEMA_VERSION,
        "label": capture.get("label"),
        "exitstatus": capture.get("exitstatus"),
        "counts": capture.get("counts"),
        "collection_error_count": capture.get("collection_error_count"),
        "python_version": capture.get("python_version"),
        "pytest_version": capture.get("pytest_version"),
        "non_passing_node_ids": [item["nodeid"] for item in signatures],
        "non_passing_count": len(signatures),
        "signatures": signatures,
        "signature_set_sha256": hashlib.sha256(
            json.dumps([[item["nodeid"], item["normalized_sha256"]]
                        for item in signatures],
                       sort_keys=True).encode("utf-8")).hexdigest(),
        "model_operations_performed": 0,
    }


def compare(baseline: dict, corrected: dict) -> dict:
    base = {item["nodeid"]: item for item in baseline["signatures"]}
    head = {item["nodeid"]: item for item in corrected["signatures"]}
    new = sorted(set(head) - set(base))
    fixed = sorted(set(base) - set(head))
    shared = sorted(set(base) & set(head))
    disagreeing = [nodeid for nodeid in shared
                   if base[nodeid]["normalized_sha256"]
                   != head[nodeid]["normalized_sha256"]]
    return {
        "schema_version": "study3-p0-r2-differential-comparison-v2",
        "baseline_label": baseline.get("label"),
        "corrected_label": corrected.get("label"),
        "baseline_non_passing": baseline["non_passing_node_ids"],
        "corrected_non_passing": corrected["non_passing_node_ids"],
        "new_failures": new,
        "new_failure_count": len(new),
        "fixed_failures": fixed,
        "shared_failures": shared,
        "signatures_disagreeing_on_shared_failures": disagreeing,
        "signatures_agree": not disagreeing,
        "baseline_collection_errors": baseline.get("collection_error_count"),
        "corrected_collection_errors": corrected.get("collection_error_count"),
        "zero_collection_errors":
            baseline.get("collection_error_count") == 0
            and corrected.get("collection_error_count") == 0,
        "baseline_counts": baseline.get("counts"),
        "corrected_counts": corrected.get("counts"),
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="append", default=[])
    parser.add_argument("--summarize")
    parser.add_argument("--compare", nargs=2, metavar=("BASELINE", "CORRECTED"))
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    if args.compare:
        with open(args.compare[0], encoding="utf-8") as handle:
            baseline = json.load(handle)
        with open(args.compare[1], encoding="utf-8") as handle:
            corrected = json.load(handle)
        payload = compare(baseline, corrected)
    elif args.summarize:
        with open(args.summarize, encoding="utf-8") as handle:
            payload = summarize(json.load(handle))
    else:
        parser.error("name --summarize or --compare")

    body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
    print(body, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
