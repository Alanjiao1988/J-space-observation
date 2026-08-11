"""Validation for the Study 3 P0-R1 registration.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections 9
and 10.

This tool answers, mechanically:

* is the authority copy byte-identical to its registered identity, and was it
  the first new repository object of the round;
* is every changed path on the authorized allowlist of section 9;
* is every byte-protected object unchanged against the required baseline,
  including every byte under ``studies/study3/pilot/p0/`` and
  ``tests/test_study3_p0_feasibility_pilot.py``;
* does the frozen corpus reproduce byte-exactly and still hold 35 rows and 70
  members;
* do the draft-v0.6 registry, schema, derived tables, P0-R1 protocol and
  pre-execution receipt reproduce from code;
* does the replay factorization derive with zero tokenizer encodes;
* does the evidence ledger still end at EV-0016 and remain byte-identical; and
* are all P0-R1 counters zero and every authority flag false except the narrow,
  not-yet-consumed ``p0_r1_pilot_execution_authorized``.

Usage::

    python p0_r1_validate.py --pre-execution --baseline <commit>
    python p0_r1_validate.py --image-build
"""

import argparse
import json
import os
import subprocess
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))

sys.path.insert(0, P0_R1_DIR)

import p0_r1_factorization as FACT  # noqa: E402
import p0_r1_schemas as SCHEMAS  # noqa: E402
from p0_r1_counters import P0R1Counters  # noqa: E402
from p0_r1_protocol import (  # noqa: E402
    AUTHORITY_BYTES,
    AUTHORITY_REPO_PATH,
    AUTHORITY_SHA256,
    AUTHORIZED_WRITE_PATHS,
    BYTE_PROTECTED_PATHS,
    PROTOCOL_PATH,
    RECEIPT_PATH,
    REGISTERED_STATE,
    blob_identity,
)

BASELINE_COMMIT = "dfbe6dd6c82fbe0e8906a4aa7f4df6b676496366"
BASELINE_TREE = "7779c8fd28aad434096ff9643c3f294b27157980"
EVIDENCE_LEDGER = "paper/evidence_ledger.csv"
EVIDENCE_LAST_ROW = "EV-0016"

REGISTRY_PATH = (
    "studies/study3/protocol/interface_calibration_rendering_registry_v0_6.json")


class ValidationFailure(Exception):
    """A fail-closed validation stop. P0-R1 never publishes past one of these."""


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
        if change["status"].startswith("D") or change["status"].startswith("R"):
            findings.append(
                "path %s was deleted or renamed (%s); no deletion, rename, copy "
                "or symlink authority exists"
                % (change["path"], change["status"]))
            continue
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


def check_p0_namespace_untouched(baseline):
    """Not one byte under the consumed P0 namespace may change."""
    out = git("diff", "--name-only", "%s..HEAD" % baseline, "--",
              "studies/study3/pilot/p0/",
              "tests/test_study3_p0_feasibility_pilot.py")
    changed = [line.strip() for line in out.splitlines() if line.strip()]
    if changed:
        return ["the consumed P0 namespace was edited: %s"
                % ", ".join(sorted(changed))]
    return []


def check_authority_identity():
    identity = blob_identity(AUTHORITY_REPO_PATH)
    findings = []
    if not identity.get("present"):
        return ["the authority copy is missing"]
    if identity["bytes"] != AUTHORITY_BYTES:
        findings.append(
            "the authority copy is %d bytes, not the registered %d"
            % (identity["bytes"], AUTHORITY_BYTES))
    if identity["sha256"] != AUTHORITY_SHA256:
        findings.append(
            "the authority copy sha256 is %s, not the registered %s"
            % (identity["sha256"], AUTHORITY_SHA256))
    if identity.get("carries_cr"):
        findings.append("the authority copy carries CR; LF only is registered")
    return findings


def check_authority_ordering(baseline):
    """The authority commit must be the first new object of the round."""
    out = git("log", "--format=%H", "--reverse", "%s..HEAD" % baseline,
              "--", AUTHORITY_REPO_PATH)
    commits = [line.strip() for line in out.splitlines() if line.strip()]
    if not commits:
        return ["the authority copy was never committed in this round"]
    first_authority = commits[0]
    ordered = git("log", "--format=%H", "--reverse", "%s..HEAD" % baseline)
    sequence = [line.strip() for line in ordered.splitlines() if line.strip()]
    if sequence and sequence[0] != first_authority:
        return ["the authority copy is not the first new commit of the round"]
    drafting = git(
        "log", "--format=%H", "--reverse", "%s..HEAD" % baseline, "--",
        "studies/study3/pilot/p0_r1/",
        "studies/study3/protocol/"
        "interface_calibration_rendering_registry_v0_6.json")
    drafting_commits = [line.strip() for line in drafting.splitlines()
                        if line.strip()]
    if drafting_commits and sequence.index(first_authority) > \
            sequence.index(drafting_commits[0]):
        return ["a draft-v0.6 or P0-R1 artifact was committed before the "
                "authority copy"]
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
    try:
        SCHEMAS.validate_evidence_ledger_unchanged()
    except SCHEMAS.SchemaDefect as exc:
        findings.append(str(exc))
    return findings


def check_reproducible_artifacts():
    findings = []
    scripts = (
        (os.path.join(P0_R1_DIR, "p0_r1_protocol.py"), ["--check"]),
        (os.path.join(P0_R1_DIR, "p0_r1_replay_gate.py"), ["--check"]),
        (os.path.join(REPO_ROOT, "studies", "study3", "analysis",
                      "scoring_boundary_v0_6.py"), ["--check"]),
    )
    for script, args in scripts:
        result = subprocess.run(
            [sys.executable, script] + args,
            capture_output=True, text=True, check=False)
        if result.returncode != 0:
            findings.append(
                "%s %s failed: %s"
                % (os.path.basename(script), " ".join(args),
                   (result.stdout + result.stderr).strip()))
    return findings


def check_replay_is_encode_free():
    try:
        document = FACT.gate(_load_registry())
    except FACT.FactorizationDefect as exc:
        return ["the replay factorization failed: %s" % exc]
    findings = []
    if document["tokenizer_encodes_performed"] != 0:
        findings.append("the replay performed a tokenizer encode")
    if document["model_operations_performed"] != 0:
        findings.append("the replay performed a model operation")
    for name in ("transformers", "tokenizers", "torch"):
        if name in sys.modules:
            findings.append(
                "%s was imported by the replay path; the verifier must not be "
                "able to encode" % name)
    if not document["all_roles_eligible"]:
        findings.append("a pinned role failed the registered factorization")
    return findings


def check_corpus():
    try:
        corpus = FACT.load_immutable(FACT.CORPUS_PATH)
        SCHEMAS.validate_corpus_reuse(corpus)
    except (FACT.FactorizationDefect, SCHEMAS.SchemaDefect) as exc:
        return [str(exc)]
    return []


def check_zero_pre_execution_counters():
    counters = P0R1Counters()
    if not counters.all_zero():
        return ["a pre-execution P0-R1 counter is non-zero"]
    counters.reconcile_totals()
    return []


def check_registration_state():
    findings = []
    for path, label in ((PROTOCOL_PATH, "the P0-R1 protocol"),
                        (RECEIPT_PATH, "the P0-R1 pre-execution receipt")):
        if not os.path.exists(path):
            findings.append("%s is missing" % label)
            continue
        with open(path, "rb") as handle:
            document = json.loads(handle.read().decode("utf-8"))
        if document.get("state") != REGISTERED_STATE:
            findings.append(
                "%s records state %r, not %r"
                % (label, document.get("state"), REGISTERED_STATE))
    if os.path.exists(RECEIPT_PATH):
        with open(RECEIPT_PATH, "rb") as handle:
            receipt = json.loads(handle.read().decode("utf-8"))
        try:
            SCHEMAS.validate_document(
                receipt, SCHEMAS.PRE_EXECUTION_RECEIPT_SCHEMA,
                "the P0-R1 pre-execution receipt")
            SCHEMAS.validate_authority_flags(receipt["authority_flags"])
            SCHEMAS.validate_historical_counter_snapshot(
                receipt["counters"]["historical_p0_t_snapshot"])
        except SCHEMAS.SchemaDefect as exc:
            findings.append(str(exc))
    return findings


def check_scoring_boundary():
    try:
        SCHEMAS.validate_scoring_boundary(_load_registry())
    except SCHEMAS.SchemaDefect as exc:
        return [str(exc)]
    return []


def check_no_results_published():
    """The calibration session registers P0-R1; it never runs it."""
    results = os.path.join(P0_R1_DIR, "results")
    if os.path.isdir(results) and os.listdir(results):
        return ["a P0-R1 result artifact exists; the calibration session "
                "registers the continuation and never performs the replay gate "
                "or the model pilot"]
    return []


def check_worktree_clean():
    status = git("status", "--porcelain=v1")
    if status.strip():
        return ["the worktree is not clean:\n" + status.strip()]
    return []


def _load_registry():
    path = os.path.join(REPO_ROOT, *REGISTRY_PATH.split("/"))
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def run(baseline, image_build=False, skip_worktree=False):
    findings = []
    findings += check_authority_identity()
    findings += check_corpus()
    findings += check_replay_is_encode_free()
    findings += check_scoring_boundary()
    findings += check_no_results_published()
    findings += check_zero_pre_execution_counters()
    if not image_build:
        findings += check_authority_ordering(baseline)
        findings += check_allowlist(baseline)
        findings += check_protected_bytes(baseline)
        findings += check_p0_namespace_untouched(baseline)
        findings += check_evidence_ledger(baseline)
        findings += check_reproducible_artifacts()
        findings += check_registration_state()
        if not skip_worktree:
            findings += check_worktree_clean()
    if findings:
        print("VALIDATION FAILED")
        for finding in findings:
            print("  FAIL " + finding)
        return 1
    print("VALIDATION PASSED")
    print("  baseline               : %s" % baseline)
    print("  authority sha256       : %s" % AUTHORITY_SHA256)
    print("  authority bytes        : %d, LF only, no trailing newline"
          % AUTHORITY_BYTES)
    if not image_build:
        print("  protected objects      : %d unchanged"
              % len(BYTE_PROTECTED_PATHS))
        print("  evidence ledger        : byte-identical, ends at %s"
              % EVIDENCE_LAST_ROW)
    print("  frozen corpus          : 35 rows, 70 members, byte-exact")
    print("  replay factorization   : derived with 0 tokenizer encodes")
    print("  state                  : %s" % REGISTERED_STATE)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=BASELINE_COMMIT)
    parser.add_argument("--image-build", action="store_true")
    parser.add_argument("--skip-worktree", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pre-execution", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.baseline, image_build=args.image_build,
                   skip_worktree=args.skip_worktree)
    except ValidationFailure as exc:
        print("VALIDATION FAILED")
        print("  FAIL %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
