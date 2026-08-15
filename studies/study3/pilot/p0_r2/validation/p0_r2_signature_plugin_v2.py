#!/usr/bin/env python3
"""Capture the exact node id and complete failure text of every non-passing test.

The published v1 harness ran pytest with ``--tb=no`` and compared only
``FAILED``/``ERROR`` *lines*. That is enough to count failures and not nearly
enough to prove that the same four failures are the *same* failures at two
different commits: two different assertions on the same node id would compare
equal. This plugin records what pytest itself produced, so a signature can be
derived from evidence rather than from a summary line.

It is loaded with ``-p`` from a path outside both checkouts, so neither
checkout is made dirty by running it.

It performs no tokenizer, checkpoint, model, GPU, scoring or evidence
operation, and it never influences the outcome of any test.
"""

from __future__ import annotations

import json
import os
import platform
import sys

SCHEMA_VERSION = "study3-p0-r2-failure-signature-capture-v2"

_RECORDS = []
_COLLECT_ERRORS = []
_COUNTS = {"passed": 0, "failed": 0, "skipped": 0, "error": 0, "xfailed": 0,
           "xpassed": 0}


def _text(report):
    text = getattr(report, "longreprtext", None)
    if text:
        return text
    longrepr = getattr(report, "longrepr", None)
    return "" if longrepr is None else str(longrepr)


def pytest_runtest_logreport(report):
    if report.when == "call":
        if report.passed:
            _COUNTS["xpassed" if hasattr(report, "wasxfail") else "passed"] += 1
        elif report.skipped:
            _COUNTS["xfailed" if hasattr(report, "wasxfail") else "skipped"] += 1
    elif report.when == "setup" and report.skipped:
        _COUNTS["skipped"] += 1

    if not report.failed:
        return
    kind = "failed" if report.when == "call" else "error"
    _COUNTS["failed" if kind == "failed" else "error"] += 1
    _RECORDS.append({
        "nodeid": report.nodeid,
        "phase": report.when,
        "kind": kind,
        "longrepr": _text(report),
    })


def pytest_collectreport(report):
    if report.failed:
        _COLLECT_ERRORS.append({
            "nodeid": report.nodeid,
            "phase": "collect",
            "kind": "collect-error",
            "longrepr": _text(report),
        })


def pytest_sessionfinish(session, exitstatus):
    out = os.environ.get("P0_R2_SIGNATURE_OUT")
    if not out:
        return
    payload = {
        "schema_version": SCHEMA_VERSION,
        "label": os.environ.get("P0_R2_SIGNATURE_LABEL", ""),
        "rootdir": str(session.config.rootpath),
        "exitstatus": int(exitstatus),
        "counts": dict(_COUNTS),
        "collection_error_count": len(_COLLECT_ERRORS),
        "non_passing": sorted(_RECORDS + _COLLECT_ERRORS,
                              key=lambda item: (item["nodeid"], item["phase"])),
        "python_version": platform.python_version(),
        "pytest_version": __import__("pytest").__version__,
        "platform": sys.platform,
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
    }
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
