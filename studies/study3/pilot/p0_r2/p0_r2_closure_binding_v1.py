#!/usr/bin/env python3
"""Resolve the P0-R2 closure-binding cycle without hand-waving it.

The cycle is real and must be stated exactly.

``p0_r2_submission_context.py`` builds the ACR context by reading ``task.yaml``
and every embedded governance object *from one source commit*. The packing
canary receipt is then supposed to prove that a future live submission carries
the same identities. But the final lock -- which is exactly the governance
object the live context has to embed -- can only be published in a commit that
does not yet exist when the canary runs. Requiring "same source commit" would
therefore make the canary unsatisfiable: publishing the lock necessarily
creates a later governance commit, which invalidates the very canary the lock
is supposed to bind.

The naive escapes are all wrong:

* binding nothing about the commit lets a foreign tree submit the run;
* letting the caller declare which later commit is "fine" is a grant, not a
  proof;
* re-running the canary after publishing the lock just moves the cycle, because
  the canary receipt is itself published and becomes another later commit.

The resolution splits one overloaded notion of "the source commit" into six
identities and proves the relations between them instead of asserting them.

``executable_code``
    the commit and tree whose bytes were built into the image. This is
    immutable and is what the canary and any future live submission must agree
    on. Its identity is fixed before the image build.

``task_object``
    the exact Git blob of the registered ACR task path. A blob id is content
    addressed, so it is stable across any descendant commit that does not touch
    the task file. This is what actually has to be identical between canary and
    live -- not the commit that happened to contain it.

``image``
    the digest-pinned final image and its base digest. Immutable.

``ready_anchor``
    the governance commit that carries the active lock. A commit cannot contain
    its own hash, so the lock never records it; the lock records the anchor's
    *parent* and the successor resolves the anchor at run time.

``governance_source``
    the commit the *live* context reads its embedded objects from. It is a
    descendant of the ready anchor and is normally the published head at
    submission time.

``published_head``
    whatever ``origin/main`` is when the successor runs.

The canary binds only the immutable identities. The governance chain is proved
separately and mechanically: ancestry executable -> anchor -> governance source
-> head, governance-only diffs after the anchor, zero drift on any bound
operational or scientific path, and embedded lock bytes equal to the bytes the
lock itself declares. A governance-only descendant therefore cannot invalidate
a valid same-executable canary, and it cannot smuggle operational-byte drift.

This module is model-free. It imports only the standard library, contacts no
network, and performs no tokenizer, checkpoint, model, GPU, scoring, or
evidence operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


SCHEMA_VERSION = "study3-p0-r2-closure-binding-v1"
PROOF_SCHEMA_VERSION = "study3-p0-r2-governance-chain-proof-v1"
AGREEMENT_SCHEMA_VERSION = "study3-p0-r2-canary-live-agreement-v1"
STAGE = "STUDY3-P0-R2"

LOCK_PATH = "studies/study3/pilot/p0_r2/p0_r2_execution_lock_v1.json"
TASK_PATH = "studies/study3/pilot/p0_r2/container/p0_r2_acr_task_v1.yaml"

# Identities that the packing canary and any future live submission must share
# byte-for-byte. None of them can change without a new image and a new canary.
IMMUTABLE_BINDING_KEYS = (
    "executable_commit",
    "executable_tree",
    "task_path",
    "task_blob",
    "image",
    "digest",
)

# Paths that may legitimately differ between the ready anchor and a later
# governance commit. Every entry is documentation, governance, navigation or
# retained evidence: none is executable, none is built into the image, and none
# can change what the image runs.
GOVERNANCE_ALLOWLIST = (
    ".gitattributes",
    "README.md",
    "docs/decision_log.md",
    "docs/run_log.md",
    "paper/artifact_index.csv",
    "paper/methods_ledger.md",
    "reports/current_status.md",
    "studies/study3/NEXT_THREAD_HANDOFF.md",
    "studies/study3/README.md",
    "studies/study3/RESEARCH_CHARTER_DRAFT.md",
    "studies/study3/pilot/p0_r2/README.md",
    "studies/study3/pilot/p0_r2/P0_R2_HANDOFF.md",
    "studies/study3/pilot/p0_r2/p0_r2_execution_lock_v1.json",
    "studies/study3/pilot/p0_r2/p0_r2_execution_lock_v1.schema.json",
    "studies/study3/pilot/p0_r2/p0_r2_canary_receipts_v1.json",
    "studies/study3/pilot/p0_r2/p0_r2_validation_receipts_v1.json",
    "studies/study3/pilot/p0_r2/p0_r2_image_manifest_v1.json",
)

GOVERNANCE_ALLOWLIST_PREFIXES = (
    "studies/study3/prompts/",
    "studies/study3/pilot/p0/results/p0-r2/",
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class ClosureBindingDefect(Exception):
    """The closure binding cannot be proved non-circular and drift-free."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_sha40(value, label: str) -> str:
    if not isinstance(value, str) or not _SHA40.fullmatch(value):
        raise ClosureBindingDefect(
            "%s must be a lowercase 40-character Git object name, got %r"
            % (label, value))
    return value


def _require_digest(value, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise ClosureBindingDefect(
            "%s must be sha256:<64 hex>, got %r" % (label, value))
    return value


def _safe_repo_path(value, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ClosureBindingDefect("%s is required" % label)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) in (".", "") \
            or "\\" in value:
        raise ClosureBindingDefect(
            "%s is not a safe repository path: %r" % (label, value))
    return str(path)


def _git(root, args, *, check=True, binary=False):
    completed = subprocess.run(  # noqa: S603 - fixed executable
        ["git", *args], cwd=None if root is None else str(root),
        capture_output=True, text=not binary, check=False)
    if check and completed.returncode:
        stderr = completed.stderr if isinstance(completed.stderr, str) \
            else completed.stderr.decode("utf-8", "replace")
        raise ClosureBindingDefect(
            "git %s failed (%d): %s"
            % (" ".join(args), completed.returncode, stderr.strip()))
    return completed.stdout, completed.returncode


def path_is_governance_only(path: str) -> bool:
    """True when a changed path cannot affect what the image executes."""
    if path in GOVERNANCE_ALLOWLIST:
        return True
    return any(path.startswith(prefix)
               for prefix in GOVERNANCE_ALLOWLIST_PREFIXES)


def blob_identity(root, commit: str, repo_path: str, *, runner=None) -> dict:
    """Read one regular committed blob; never trust the mutable worktree."""
    commit = _require_sha40(commit, "commit")
    repo_path = _safe_repo_path(repo_path, "repository path")
    run = runner or (lambda args, check=True, binary=False:
                     _git(root, args, check=check, binary=binary))
    listing, _ = run(["ls-tree", commit, "--", repo_path])
    fields = listing.strip().split(None, 3)
    if len(fields) != 4 or fields[0] != "100644" or fields[1] != "blob" \
            or fields[3] != repo_path:
        raise ClosureBindingDefect(
            "%s is not exactly one regular 100644 blob at %s"
            % (repo_path, commit))
    blob = _require_sha40(fields[2], "%s blob" % repo_path)
    payload, _ = run(["cat-file", "blob", blob], binary=True)
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return {
        "path": repo_path,
        "git_blob": blob,
        "bytes": len(payload),
        "sha256": _sha256(payload),
    }


def canary_binding(*, executable_commit: str, executable_tree: str,
                   task_path: str, task_blob: str, image: str,
                   digest: str) -> dict:
    """The immutable identity set a canary and a live run must share.

    Deliberately excludes any commit that will later contain the lock. That
    omission is the whole point: it is what makes the binding non-circular.
    """
    binding = {
        "executable_commit": _require_sha40(executable_commit,
                                            "executable_commit"),
        "executable_tree": _require_sha40(executable_tree, "executable_tree"),
        "task_path": _safe_repo_path(task_path, "task_path"),
        "task_blob": _require_sha40(task_blob, "task_blob"),
        "image": image,
        "digest": _require_digest(digest, "digest"),
    }
    if not isinstance(image, str) or not image.endswith("@" + binding["digest"]):
        raise ClosureBindingDefect(
            "the image reference is not pinned by the supplied digest")
    return binding


def resolve_canary_binding(root, binding: dict, *, task_path: str,
                           runner=None) -> dict:
    """Complete a canary binding by proof from Git, never by caller grant.

    A canary receipt that predates this module may record only the source
    commit it ran from. That is enough, but only because the missing fields can
    be *derived and checked* against committed objects:

    * the executable commit defaults to the canary's own source commit, since a
      canary runs at the executable commit by construction;
    * the executable tree is read from Git for that commit, not accepted;
    * the task path is accepted only if the blob actually stored at that path in
      that commit equals the task blob the canary already declared.

    Anything that cannot be proved raises instead of defaulting. This is the
    opposite of letting the caller declare which identities are acceptable.
    """
    if not isinstance(binding, dict):
        raise ClosureBindingDefect("the canary binding must be a document")
    resolved = dict(binding)

    executable_commit = resolved.get("executable_commit") \
        or resolved.get("source_commit")
    executable_commit = _require_sha40(
        executable_commit, "canary executable commit")
    resolved["executable_commit"] = executable_commit

    declared_blob = _require_sha40(resolved.get("task_blob"),
                                   "canary task blob")

    if not resolved.get("executable_tree"):
        run = runner or (lambda args, check=True, binary=False:
                         _git(root, args, check=check, binary=binary))
        out, _ = run(["rev-parse", "%s^{tree}" % executable_commit])
        resolved["executable_tree"] = _require_sha40(
            out.strip(), "canary executable tree")
    else:
        _require_sha40(resolved["executable_tree"], "canary executable tree")

    if not resolved.get("task_path"):
        candidate = _safe_repo_path(task_path, "task_path")
    else:
        candidate = _safe_repo_path(resolved["task_path"], "canary task path")
    # The path is never taken on the caller's word, whether it was declared or
    # defaulted. Git must actually store the declared blob at that path in that
    # commit, otherwise the binding would be a grant rather than a proof.
    actual = blob_identity(root, executable_commit, candidate, runner=runner)
    if actual["git_blob"] != declared_blob:
        raise ClosureBindingDefect(
            "%s at %s is blob %s rather than the declared canary task blob "
            "%s; the canary binding cannot be completed by assumption"
            % (candidate, executable_commit, actual["git_blob"],
               declared_blob))
    resolved["task_path"] = candidate
    return resolved


def verify_canary_live_agreement(canary: dict, live: dict) -> dict:
    """Require immutable agreement; allow a governance-only source change.

    ``canary`` and ``live`` are binding blocks. The governance source commit is
    *expected* to differ, because publishing the lock creates a descendant. The
    immutable executable/task/image identity may not differ at all.
    """
    if not isinstance(canary, dict) or not isinstance(live, dict):
        raise ClosureBindingDefect("both bindings must be documents")
    mismatched = []
    for key in IMMUTABLE_BINDING_KEYS:
        if key not in canary or key not in live:
            raise ClosureBindingDefect(
                "binding key %r is missing; the canary cannot be compared"
                % key)
        if canary[key] != live[key]:
            mismatched.append(key)
    if mismatched:
        raise ClosureBindingDefect(
            "the packing canary and the live submission disagree on immutable "
            "identity: %s. Rebuild the image and rerun the canary; a "
            "governance commit never repairs this."
            % ", ".join(sorted(mismatched)))
    return {
        "schema_version": AGREEMENT_SCHEMA_VERSION,
        "stage": STAGE,
        "immutable_keys_checked": list(IMMUTABLE_BINDING_KEYS),
        "immutable_identity_agrees": True,
        "canary_source_commit": canary.get("source_commit"),
        "live_source_commit": live.get("source_commit"),
        "source_commit_may_differ": True,
        "source_commit_difference_requires_governance_proof": True,
    }


def prove_governance_chain(*, root=None, executable_commit: str,
                           executable_tree: str, ready_anchor: str,
                           governance_commit: str, bound_paths=None,
                           lock_identity=None, task_path: str = TASK_PATH,
                           task_blob: str = None, require_head=True,
                           require_clean=True, remote="origin", branch="main",
                           runner=None) -> dict:
    """Prove the whole chain mechanically instead of trusting a declaration."""
    run = runner or (lambda args, check=True, binary=False:
                     _git(root, args, check=check, binary=binary))

    executable_commit = _require_sha40(executable_commit, "executable_commit")
    executable_tree = _require_sha40(executable_tree, "executable_tree")
    ready_anchor = _require_sha40(ready_anchor, "ready_anchor")
    governance_commit = _require_sha40(governance_commit, "governance_commit")

    out, _ = run(["rev-parse", "%s^{tree}" % executable_commit])
    if _require_sha40(out.strip(), "executable tree") != executable_tree:
        raise ClosureBindingDefect(
            "the executable commit %s carries tree %s, not the bound %s"
            % (executable_commit, out.strip(), executable_tree))

    out, _ = run(["rev-parse", "%s^{tree}" % ready_anchor])
    anchor_tree = _require_sha40(out.strip(), "anchor tree")
    out, _ = run(["rev-parse", "%s^{tree}" % governance_commit])
    governance_tree = _require_sha40(out.strip(), "governance tree")

    head = None
    head_tree = None
    if require_head:
        out, _ = run(["rev-parse", "HEAD"])
        head = _require_sha40(out.strip(), "HEAD")
        out, _ = run(["rev-parse", "HEAD^{tree}"])
        head_tree = _require_sha40(out.strip(), "HEAD^{tree}")
        remote_ref = "%s/%s" % (remote, branch)
        out, _ = run(["rev-parse", remote_ref])
        published = _require_sha40(out.strip(), remote_ref)
        if head != published:
            raise ClosureBindingDefect(
                "HEAD %s is not the published %s %s; a successor must run the "
                "exact published object" % (head, remote_ref, published))
        if require_clean:
            out, _ = run(["status", "--porcelain"])
            if out.strip():
                raise ClosureBindingDefect(
                    "the working tree is not clean; refusing to prove a "
                    "closure binding for uncommitted bytes:\n%s" % out.strip())

    # Ancestry is proved, never assumed. Each link is a separate refusal.
    links = [
        (executable_commit, ready_anchor, "executable commit -> ready anchor"),
        (ready_anchor, governance_commit, "ready anchor -> governance source"),
    ]
    if head is not None:
        links.append((governance_commit, head,
                      "governance source -> published head"))
    for older, newer, label in links:
        if older == newer:
            continue
        _, code = run(["merge-base", "--is-ancestor", older, newer],
                      check=False)
        if code != 0:
            raise ClosureBindingDefect(
                "ancestry %s is not satisfied: %s is not an ancestor of %s"
                % (label, older, newer))
    if executable_commit == ready_anchor:
        raise ClosureBindingDefect(
            "the ready anchor must be a strict descendant of the executable "
            "commit; a commit cannot carry a lock over its own bytes")

    # Everything that changed after the anchor must be governance-only.
    out, _ = run(["diff", "--name-only", ready_anchor, governance_commit])
    changed = sorted(line.strip() for line in out.splitlines() if line.strip())
    disallowed = [path for path in changed if not path_is_governance_only(path)]
    if disallowed:
        raise ClosureBindingDefect(
            "the governance source changed %d path(s) outside the governance "
            "allowlist after the ready anchor; this is not a governance-only "
            "descendant: %s" % (len(disallowed), ", ".join(disallowed)))

    changed_since_head = []
    if head is not None and head != governance_commit:
        out, _ = run(["diff", "--name-only", governance_commit, head])
        changed_since_head = sorted(
            line.strip() for line in out.splitlines() if line.strip())
        disallowed_head = [path for path in changed_since_head
                           if not path_is_governance_only(path)]
        if disallowed_head:
            raise ClosureBindingDefect(
                "the published head changed %d path(s) outside the governance "
                "allowlist after the governance source: %s"
                % (len(disallowed_head), ", ".join(disallowed_head)))

    # No bound operational or scientific byte may drift after the image build.
    bound_paths = tuple(bound_paths or ())
    bound_changed = []
    if bound_paths:
        newest = head if head is not None else governance_commit
        out, _ = run(["diff", "--name-only", executable_commit, newest])
        drifted = set(line.strip() for line in out.splitlines() if line.strip())
        bound_changed = sorted(drifted.intersection(set(bound_paths)))
        if bound_changed:
            raise ClosureBindingDefect(
                "%d bound path(s) changed after the image build: %s. Discard "
                "the unexecuted image, rebuild and relock."
                % (len(bound_changed), ", ".join(bound_changed)))

    # The task blob must be identical at the executable commit and at the
    # governance source. A blob id is content addressed, so this is the exact
    # property the canary needs and the commit id is not.
    task_at_exec = blob_identity(root, executable_commit, task_path,
                                 runner=runner)
    task_at_gov = blob_identity(root, governance_commit, task_path,
                                runner=runner)
    if task_at_exec["git_blob"] != task_at_gov["git_blob"]:
        raise ClosureBindingDefect(
            "the ACR task blob changed between the executable commit (%s) and "
            "the governance source (%s); the canary no longer describes the "
            "live submission"
            % (task_at_exec["git_blob"], task_at_gov["git_blob"]))
    if task_blob and task_at_exec["git_blob"] != _require_sha40(
            task_blob, "task_blob"):
        raise ClosureBindingDefect(
            "the bound task blob %s is not the committed task blob %s"
            % (task_blob, task_at_exec["git_blob"]))

    # The anchor must actually carry the exact lock bytes it claims.
    lock_proof = None
    if lock_identity:
        path = _safe_repo_path(lock_identity.get("path") or LOCK_PATH,
                               "lock path")
        actual = blob_identity(root, ready_anchor, path, runner=runner)
        expected_bytes = lock_identity.get("bytes")
        expected_sha = lock_identity.get("sha256")
        if expected_sha is not None and not _SHA256.fullmatch(
                str(expected_sha)):
            raise ClosureBindingDefect("the bound lock sha256 is malformed")
        if (expected_bytes is not None and actual["bytes"] != expected_bytes) \
                or (expected_sha is not None
                    and actual["sha256"] != expected_sha):
            raise ClosureBindingDefect(
                "ready anchor %s does not carry the bound lock bytes "
                "(found %d bytes sha256 %s)"
                % (ready_anchor, actual["bytes"], actual["sha256"]))
        gov_lock = blob_identity(root, governance_commit, path, runner=runner)
        if gov_lock["git_blob"] != actual["git_blob"]:
            raise ClosureBindingDefect(
                "the governance source carries a different lock blob than the "
                "ready anchor; the embedded lock bytes are not the bound lock")
        lock_proof = dict(actual)
        lock_proof["identical_at_governance_source"] = True

    return {
        "schema_version": PROOF_SCHEMA_VERSION,
        "stage": STAGE,
        "outcome": "GOVERNANCE_CHAIN_PROVED",
        "executable_code": {"commit": executable_commit,
                            "tree": executable_tree},
        "ready_anchor": {"commit": ready_anchor, "tree": anchor_tree},
        "governance_source": {"commit": governance_commit,
                              "tree": governance_tree},
        "published_head": (
            None if head is None else {"commit": head, "tree": head_tree}),
        "head_equals_published": bool(require_head),
        "worktree_clean": bool(require_head and require_clean),
        "ancestry_proved": [label for _, _, label in links],
        "changed_since_anchor": changed,
        "changed_since_anchor_count": len(changed),
        "changed_since_governance_source": changed_since_head,
        "all_changes_are_governance_only": True,
        "governance_allowlist": list(GOVERNANCE_ALLOWLIST),
        "governance_allowlist_prefixes": list(GOVERNANCE_ALLOWLIST_PREFIXES),
        "bound_paths_checked": len(bound_paths),
        "bound_paths_changed_after_image_build": bound_changed,
        "task_object": task_at_exec,
        "task_blob_identical_at_governance_source": True,
        "execution_lock": lock_proof,
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
    }


def validate_proof(proof, *, executable_commit=None, ready_anchor=None,
                   governance_commit=None, lock_sha256=None,
                   task_blob=None) -> dict:
    """Re-check a serialized proof against the identities it must bind."""
    if not isinstance(proof, dict):
        raise ClosureBindingDefect("the governance chain proof must be a document")
    if proof.get("schema_version") != PROOF_SCHEMA_VERSION:
        raise ClosureBindingDefect(
            "the proof schema %r is not %r"
            % (proof.get("schema_version"), PROOF_SCHEMA_VERSION))
    if proof.get("outcome") != "GOVERNANCE_CHAIN_PROVED":
        raise ClosureBindingDefect(
            "the proof outcome %r is not GOVERNANCE_CHAIN_PROVED"
            % proof.get("outcome"))
    for key in ("executable_code", "ready_anchor", "governance_source"):
        block = proof.get(key)
        if not isinstance(block, dict):
            raise ClosureBindingDefect("the proof is missing %r" % key)
        _require_sha40(block.get("commit"), "%s.commit" % key)
        _require_sha40(block.get("tree"), "%s.tree" % key)
    if not proof.get("all_changes_are_governance_only"):
        raise ClosureBindingDefect(
            "the proof records non-governance changes after the ready anchor")
    if proof.get("bound_paths_changed_after_image_build"):
        raise ClosureBindingDefect(
            "the proof records bound paths changed after the image build")
    if not proof.get("task_blob_identical_at_governance_source"):
        raise ClosureBindingDefect(
            "the proof does not record an identical task blob at the "
            "governance source")
    pairs = (
        (executable_commit, proof["executable_code"]["commit"],
         "executable commit"),
        (ready_anchor, proof["ready_anchor"]["commit"], "ready anchor"),
        (governance_commit, proof["governance_source"]["commit"],
         "governance source"),
    )
    for expected, actual, label in pairs:
        if expected and _require_sha40(expected, label) != actual:
            raise ClosureBindingDefect(
                "the proof binds %s %s, not the required %s"
                % (label, actual, expected))
    if task_blob:
        actual = (proof.get("task_object") or {}).get("git_blob")
        if actual != _require_sha40(task_blob, "task_blob"):
            raise ClosureBindingDefect(
                "the proof binds task blob %s, not %s" % (actual, task_blob))
    if lock_sha256:
        lock = proof.get("execution_lock")
        if not isinstance(lock, dict) or lock.get("sha256") != lock_sha256:
            raise ClosureBindingDefect(
                "the proof does not bind the active lock bytes")
    return proof


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_closure_binding_v1.py",
        "stage": STAGE,
        "identities": [
            "executable_code", "task_object", "image", "ready_anchor",
            "governance_source", "published_head",
        ],
        "immutable_binding_keys": list(IMMUTABLE_BINDING_KEYS),
        "governance_allowlist": list(GOVERNANCE_ALLOWLIST),
        "governance_allowlist_prefixes": list(GOVERNANCE_ALLOWLIST_PREFIXES),
        "lock_records_its_own_commit": False,
        "accepts_caller_supplied_governance_grant": False,
        "governance_descendant_invalidates_canary": False,
        "governance_descendant_may_drift_operational_bytes": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--prove", action="store_true")
    parser.add_argument("--root")
    parser.add_argument("--lock-file")
    parser.add_argument("--governance-commit")
    parser.add_argument("--ready-anchor")
    parser.add_argument("--out")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if not args.lock_file:
        parser.error("--prove requires --lock-file")
    try:
        lock_raw = Path(args.lock_file).read_bytes()
        lock = json.loads(lock_raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print("P0_R2_CLOSURE_BINDING_REFUSED=1 unreadable lock: %s" % exc,
              file=sys.stderr)
        return 2

    executable = lock.get("executable_code") or {}
    relationship = lock.get("ready_commit_relationship") or {}
    anchor = args.ready_anchor or relationship.get("ready_anchor_commit")
    root = args.root
    if anchor is None:
        parent = relationship.get("ready_anchor_parent")
        try:
            out, _ = _git(root, [
                "rev-list", "--first-parent", "--reverse",
                "%s..HEAD" % _require_sha40(parent, "ready_anchor_parent")])
            candidates = [line.strip() for line in out.splitlines()
                          if line.strip()]
            if not candidates:
                raise ClosureBindingDefect(
                    "no first-parent descendant of %s exists" % parent)
            anchor = candidates[0]
        except ClosureBindingDefect as exc:
            print("P0_R2_CLOSURE_BINDING_REFUSED=1 %s" % exc, file=sys.stderr)
            return 3

    governance = args.governance_commit
    if not governance:
        out, _ = _git(root, ["rev-parse", "HEAD"])
        governance = out.strip()

    bound = [entry["path"] for entry in (executable.get("files") or [])
             if isinstance(entry, dict) and entry.get("path")]
    bound += [entry["path"] for entry in (lock.get("immutable_sources") or [])
              if isinstance(entry, dict) and entry.get("path")]
    lock_identity = {
        "path": LOCK_PATH,
        "bytes": len(lock_raw),
        "sha256": _sha256(lock_raw),
    }
    try:
        proof = prove_governance_chain(
            root=root,
            executable_commit=executable.get("commit"),
            executable_tree=executable.get("tree"),
            ready_anchor=anchor, governance_commit=governance,
            bound_paths=bound, lock_identity=lock_identity,
            task_path=(lock.get("transport") or {}).get(
                "task_path", TASK_PATH),
            task_blob=(lock.get("transport") or {}).get("task_blob"),
            require_clean=not args.allow_dirty)
    except ClosureBindingDefect as exc:
        print("P0_R2_CLOSURE_BINDING_REFUSED=1", file=sys.stderr)
        print("  %s" % exc, file=sys.stderr)
        return 3

    payload = json.dumps(proof, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    print("P0_R2_CLOSURE_BINDING_PROVED=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
