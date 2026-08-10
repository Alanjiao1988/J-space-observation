"""Validation for the Study 3-P0 feasibility pilot.

Authority: ``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md``
sections 6 and 11.

This tool answers, mechanically:

* is every changed path on the authorized allowlist;
* is every byte-protected object unchanged against the required baseline;
* is the authority copy byte-identical to its registered identity;
* does the frozen corpus reproduce byte-exactly;
* does the P0 protocol document reproduce byte-exactly;
* are all pre-P0 operation counters zero;
* does the evidence ledger still end at EV-0016 and remain byte-identical;
* does the counter arithmetic reconcile.

It is deliberately usable before publication (``--pre-execution``) and after a
measurement stage (``--post-measurement``). It never edits a scientific value.

Usage::

    python p0_validate.py --pre-execution --baseline <commit>
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p0_counters import P0Counters  # noqa: E402
from p0_protocol import (  # noqa: E402
    AUTHORIZED_WRITE_PATHS,
    BYTE_PROTECTED_PATHS,
    PROTOCOL_PATH,
)
from p0_renderer import REPO_ROOT  # noqa: E402

BASELINE_COMMIT = "5b15e0ed0ee109955ef805adab3fc3e25b93e5ed"
BASELINE_TREE = "62cbfb371fdf273f0b8642c06c05b0741000e6a5"
AUTHORITY_SHA256 = (
    "80efc7ef8bfe5e3b5e5235f530a44730f185187aa52b85945875fe68ef1eda11")
AUTHORITY_BYTES = 29282
EVIDENCE_LEDGER = "paper/evidence_ledger.csv"
EVIDENCE_LAST_ROW = "EV-0016"


class ValidationFailure(Exception):
    """A fail-closed validation stop. P0 never publishes past one of these."""


def git(*args):
    result = subprocess.run(
        ["git", "-C", REPO_ROOT] + list(args),
        capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ValidationFailure(
            "git %s failed: %s" % (" ".join(args), result.stderr.strip()))
    return result.stdout


def changed_paths(baseline):
    out = git("diff", "--name-status", "%s..HEAD" % baseline)
    changes = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        changes.append({"status": parts[0], "path": parts[-1]})
    return changes


def path_is_authorized(path):
    for allowed in AUTHORIZED_WRITE_PATHS:
        if allowed.endswith("/"):
            if path.startswith(allowed):
                return True
        elif path == allowed:
            return True
    return False


def check_allowlist(baseline):
    findings = []
    for change in changed_paths(baseline):
        if not path_is_authorized(change["path"]):
            findings.append(
                "unauthorized changed path %s (%s)"
                % (change["path"], change["status"]))
    return findings


def check_protected_bytes(baseline):
    findings = []
    for path in BYTE_PROTECTED_PATHS:
        try:
            before = git("rev-parse", "%s:%s" % (baseline, path)).strip()
        except ValidationFailure:
            findings.append("baseline object missing for %s" % path)
            continue
        try:
            after = git("rev-parse", "HEAD:%s" % path).strip()
        except ValidationFailure:
            findings.append("protected object deleted: %s" % path)
            continue
        if before != after:
            findings.append(
                "protected bytes changed: %s (%s -> %s)" % (path, before, after))
    return findings


def check_authority_identity():
    path = os.path.join(
        REPO_ROOT, "studies", "study3", "prompts",
        "study3_p0_feasibility_pilot_authority.md")
    if not os.path.exists(path):
        return ["the authority copy is missing"]
    with open(path, "rb") as handle:
        raw = handle.read()
    findings = []
    if len(raw) != AUTHORITY_BYTES:
        findings.append(
            "the authority copy is %d bytes, not the registered %d"
            % (len(raw), AUTHORITY_BYTES))
    digest = hashlib.sha256(raw).hexdigest()
    if digest != AUTHORITY_SHA256:
        findings.append(
            "the authority copy sha256 is %s, not the registered %s"
            % (digest, AUTHORITY_SHA256))
    if b"\r" in raw:
        findings.append("the authority copy carries CR; LF only is registered")
    return findings


def check_authority_ordering(baseline):
    """The authority commit must precede every P0 drafting artifact."""
    authority = ("studies/study3/prompts/"
                 "study3_p0_feasibility_pilot_authority.md")
    out = git("log", "--format=%H", "--reverse", "%s..HEAD" % baseline,
              "--", authority)
    commits = [line.strip() for line in out.splitlines() if line.strip()]
    if not commits:
        return ["the authority copy was never committed in this round"]
    first_authority = commits[0]
    drafting = git("log", "--format=%H", "--reverse", "%s..HEAD" % baseline,
                   "--", "studies/study3/pilot/p0/",
                   "tests/test_study3_p0_feasibility_pilot.py")
    drafting_commits = [line.strip() for line in drafting.splitlines()
                        if line.strip()]
    if not drafting_commits:
        return []
    ordered = git("log", "--format=%H", "--reverse", "%s..HEAD" % baseline)
    sequence = [line.strip() for line in ordered.splitlines() if line.strip()]
    if sequence.index(first_authority) > sequence.index(drafting_commits[0]):
        return ["a P0 drafting artifact was committed before the authority copy"]
    return []


def check_evidence_ledger(baseline):
    findings = []
    try:
        before = git("rev-parse", "%s:%s" % (baseline, EVIDENCE_LEDGER)).strip()
        after = git("rev-parse", "HEAD:%s" % EVIDENCE_LEDGER).strip()
    except ValidationFailure as exc:
        return [str(exc)]
    if before != after:
        findings.append("paper/evidence_ledger.csv is not byte-identical")
    content = git("show", "HEAD:%s" % EVIDENCE_LEDGER)
    rows = [line for line in content.splitlines() if line.strip()]
    last = rows[-1].split(",")[0] if rows else ""
    if last != EVIDENCE_LAST_ROW:
        findings.append(
            "the evidence ledger ends at %r, not %r" % (last, EVIDENCE_LAST_ROW))
    return findings


def check_reproducible_artifacts():
    findings = []
    here = os.path.dirname(os.path.abspath(__file__))
    for script in ("p0_freeze_corpus.py", "p0_protocol.py"):
        result = subprocess.run(
            [sys.executable, os.path.join(here, script), "--check"],
            capture_output=True, text=True, check=False)
        if result.returncode != 0:
            findings.append(
                "%s --check failed: %s"
                % (script, (result.stdout + result.stderr).strip()))
    return findings


def check_zero_pre_execution_counters():
    counters = P0Counters()
    if not counters.all_zero():
        return ["a pre-execution P0 counter is non-zero"]
    counters.reconcile_totals()
    return []


def check_protocol_state(expected_state):
    if not os.path.exists(PROTOCOL_PATH):
        return ["the P0 protocol document is missing"]
    with open(PROTOCOL_PATH, "rb") as handle:
        document = json.loads(handle.read().decode("utf-8"))
    findings = []
    if document["state"] != expected_state:
        findings.append(
            "the P0 protocol records state %r, not %r"
            % (document["state"], expected_state))
    legal = document["legal_status"]
    if legal["formal_execution_authorized"] is not False:
        findings.append("formal_execution_authorized must remain false")
    if legal["draft_v0_5_frozen"] is not False:
        findings.append("draft-v0.5 must remain unfrozen")
    if legal["evidence_ledger_last_row"] != EVIDENCE_LAST_ROW:
        findings.append("the protocol misrecords the evidence ledger tail")
    return findings


def check_worktree_clean():
    status = git("status", "--porcelain=v1")
    if status.strip():
        return ["the worktree is not clean:\n" + status.strip()]
    return []


def run(baseline, expected_state, post_measurement=False):
    findings = []
    findings += check_authority_identity()
    findings += check_authority_ordering(baseline)
    findings += check_allowlist(baseline)
    findings += check_protected_bytes(baseline)
    findings += check_evidence_ledger(baseline)
    findings += check_reproducible_artifacts()
    findings += check_protocol_state(expected_state)
    findings += check_worktree_clean()
    if not post_measurement:
        findings += check_zero_pre_execution_counters()
    if findings:
        print("VALIDATION FAILED")
        for finding in findings:
            print("  FAIL " + finding)
        return 1
    print("VALIDATION PASSED")
    print("  baseline               : %s" % baseline)
    print("  authority sha256       : %s" % AUTHORITY_SHA256)
    print("  protected objects      : %d unchanged" % len(BYTE_PROTECTED_PATHS))
    print("  evidence ledger        : byte-identical, ends at %s"
          % EVIDENCE_LAST_ROW)
    print("  frozen corpus/protocol : reproduce byte-exactly")
    print("  state                  : %s" % expected_state)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=BASELINE_COMMIT)
    parser.add_argument(
        "--expected-state",
        default="STUDY3_P0_REGISTERED_AWAITING_TOKENIZER_GATE")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pre-execution", action="store_true")
    group.add_argument("--post-measurement", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.baseline, args.expected_state,
                   post_measurement=args.post_measurement)
    except ValidationFailure as exc:
        print("VALIDATION FAILED")
        print("  FAIL %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
