#!/usr/bin/env python3
"""Prove the published ready identity instead of propagating a claimed one.

Generation 2 stored a parent commit and a prose sentence describing how the
ready commit related to it. Runtime validation then accepted *any* coordinated
40-character hex string that appeared in both the gate receipt and the launcher
argument. Two coordinated lies validated cleanly, and the published closeout
called ``c04ec748`` the final ready commit while the handoff called
``c7e02b43`` the ready commit, with nothing mechanical to reconcile them.

Generation 3 represents three distinct identities and proves the relationships
between them rather than asserting them:

``executable_code``
    the commit and tree whose bytes were built into the image. Nothing under
    the lock's bound paths may differ from this tree.

``ready_anchor``
    the commit and tree that carry the active execution lock. This is a strict
    descendant of the executable commit, and it is the object a successor
    session must be able to name.

``published_head``
    whatever ``origin/main`` actually is when the successor runs. It is a
    descendant of the ready anchor, and **every** path that changed between
    the anchor and the head must fall inside the governance allowlist below.

The self-reference problem is handled by construction. A commit cannot contain
its own hash, so the lock never tries to record the head that will contain it.
It records the executable identity and the anchor's *parent*, and the successor
computes the anchor and head at run time and proves the chain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys

SCHEMA_VERSION = "study3-p0-r1-ready-anchor-v3"
LOCK_PATH = "studies/study3/pilot/p0_r1/p0_r1_execution_lock_v3.json"

# Paths that may legitimately change after the ready anchor. Every one of them
# is documentation, governance or navigation: none is executable, none is bound
# by the lock, and none can alter what the image runs. A change outside this
# set means the published head no longer matches the validated executable
# bytes, and the successor must refuse.
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
    "studies/study3/pilot/p0_r1/README.md",
)

GOVERNANCE_ALLOWLIST_PREFIXES = (
    "studies/study3/prompts/",
)


class ReadyAnchorDefect(Exception):
    """The published head cannot be proved to carry the validated bytes."""


def _git(args, root=None, check=True):
    completed = subprocess.run(  # noqa: S603 - fixed executable
        ["git"] + list(args), cwd=root, capture_output=True, text=True)
    if check and completed.returncode != 0:
        raise ReadyAnchorDefect(
            "git %s failed (%s): %s"
            % (" ".join(args), completed.returncode,
               (completed.stderr or "").strip()))
    return completed.stdout.strip(), completed.returncode


def _git_bytes(args, root=None):
    completed = subprocess.run(  # noqa: S603 - fixed executable
        ["git"] + list(args), cwd=root, capture_output=True)
    if completed.returncode != 0:
        raise ReadyAnchorDefect(
            "git %s failed: %s"
            % (" ".join(args),
               completed.stderr.decode("utf-8", "replace").strip()))
    return completed.stdout


def _require_sha(value, label):
    if not isinstance(value, str) or len(value) != 40:
        raise ReadyAnchorDefect(
            "%s must be a 40-character object name, got %r" % (label, value))
    lowered = value.lower()
    if any(character not in "0123456789abcdef" for character in lowered):
        raise ReadyAnchorDefect("%s is not hexadecimal: %r" % (label, value))
    return lowered


def path_is_governance_only(path):
    """True when a changed path cannot affect what the image executes."""
    if path in GOVERNANCE_ALLOWLIST:
        return True
    return any(path.startswith(prefix)
               for prefix in GOVERNANCE_ALLOWLIST_PREFIXES)


def changed_paths(base, head, root=None):
    """Every path that differs between two commits, as a sorted list."""
    out, _ = _git(["diff", "--name-only", base, head], root=root)
    return sorted(line.strip() for line in out.splitlines() if line.strip())


def resolve_ready_anchor(ready_anchor_parent, root=None, head=None, git=None):
    """Resolve the direct first-parent child that introduced the active lock."""
    runner = git or (lambda args, check=True: _git(args, root=root,
                                                    check=check))
    parent = _require_sha(ready_anchor_parent, "ready_anchor_parent")
    if head is None:
        head, _ = runner(["rev-parse", "HEAD"])
    head = _require_sha(head, "HEAD")
    out, _ = runner([
        "rev-list", "--first-parent", "--reverse", "%s..%s" % (parent, head)])
    candidates = [line.strip() for line in out.splitlines() if line.strip()]
    if not candidates:
        raise ReadyAnchorDefect(
            "no first-parent descendant of ready anchor parent %s exists"
            % parent)
    anchor = _require_sha(candidates[0], "resolved ready anchor")
    actual_parent, _ = runner(["rev-parse", "%s^1" % anchor])
    if _require_sha(actual_parent, "ready anchor parent") != parent:
        raise ReadyAnchorDefect(
            "resolved anchor %s is not a direct child of %s"
            % (anchor, parent))
    return anchor


def prove(root=None, executable_commit=None, executable_tree=None,
          ready_anchor=None, ready_anchor_parent=None, bound_paths=None,
          lock_identity=None, require_clean=True, remote="origin",
          branch="main", git=None):
    """Build a head proof, or raise with the exact reason it cannot be built.

    ``git`` may be supplied as a callable for tests; production passes None
    and the real repository answers.
    """
    runner = git or (lambda args, check=True: _git(args, root=root,
                                                   check=check))

    head, _ = runner(["rev-parse", "HEAD"])
    head = _require_sha(head, "HEAD")
    head_tree, _ = runner(["rev-parse", "HEAD^{tree}"])
    head_tree = _require_sha(head_tree, "HEAD^{tree}")

    remote_ref = "%s/%s" % (remote, branch)
    published, _ = runner(["rev-parse", remote_ref])
    published = _require_sha(published, remote_ref)
    if head != published:
        raise ReadyAnchorDefect(
            "HEAD %s is not the published %s %s; a successor must run the "
            "exact published object, never a local variant"
            % (head, remote_ref, published))

    if require_clean:
        status, _ = runner(["status", "--porcelain"])
        if status.strip():
            raise ReadyAnchorDefect(
                "the working tree is not clean; refusing to prove a ready "
                "identity for uncommitted bytes:\n%s" % status.strip())

    executable_commit = _require_sha(executable_commit, "executable_commit")
    executable_tree = _require_sha(executable_tree, "executable_tree")
    ready_anchor = _require_sha(ready_anchor, "ready_anchor")
    if ready_anchor_parent:
        parent = _require_sha(ready_anchor_parent, "ready_anchor_parent")
        actual_parent, _ = runner(["rev-parse", "%s^1" % ready_anchor])
        if _require_sha(actual_parent, "ready anchor parent") != parent:
            raise ReadyAnchorDefect(
                "ready anchor %s has parent %s, not locked parent %s"
                % (ready_anchor, actual_parent, parent))
    else:
        parent = None

    for older, newer, label in (
            (executable_commit, ready_anchor, "executable commit -> anchor"),
            (ready_anchor, head, "anchor -> published head")):
        _, code = runner(["merge-base", "--is-ancestor", older, newer],
                         check=False)
        if code != 0:
            raise ReadyAnchorDefect(
                "ancestry %s is not satisfied: %s is not an ancestor of %s"
                % (label, older, newer))

    actual_exec_tree, _ = runner(["rev-parse", "%s^{tree}" % executable_commit])
    if _require_sha(actual_exec_tree, "executable tree") != executable_tree:
        raise ReadyAnchorDefect(
            "the executable commit %s carries tree %s, not the locked %s"
            % (executable_commit, actual_exec_tree, executable_tree))

    anchor_tree, _ = runner(["rev-parse", "%s^{tree}" % ready_anchor])
    anchor_tree = _require_sha(anchor_tree, "anchor tree")

    lock_proof = None
    if lock_identity:
        path = lock_identity.get("path") or LOCK_PATH
        if git is None:
            payload = _git_bytes(
                ["cat-file", "blob", "%s:%s" % (ready_anchor, path)],
                root=root)
        else:
            body, _ = runner(["show", "%s:%s" % (ready_anchor, path)])
            payload = body.encode("utf-8")
        actual = {
            "path": path,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if actual["bytes"] != lock_identity.get("bytes") \
                or actual["sha256"] != lock_identity.get("sha256"):
            raise ReadyAnchorDefect(
                "ready anchor %s does not carry the injected lock bytes"
                % ready_anchor)
        lock_proof = actual

    out, _ = runner(["diff", "--name-only", ready_anchor, head])
    changed = sorted(line.strip() for line in out.splitlines() if line.strip())
    disallowed = [path for path in changed if not path_is_governance_only(path)]
    if disallowed:
        raise ReadyAnchorDefect(
            "the published head changed %d path(s) outside the governance "
            "allowlist after the ready anchor; the image no longer matches "
            "the repository: %s" % (len(disallowed), ", ".join(disallowed)))

    bound_changed = []
    if bound_paths:
        out, _ = runner(["diff", "--name-only", executable_commit, head])
        since_exec = set(line.strip() for line in out.splitlines()
                         if line.strip())
        bound_changed = sorted(since_exec.intersection(set(bound_paths)))
        if bound_changed:
            raise ReadyAnchorDefect(
                "%d bound executable path(s) changed after the image build: "
                "%s. Discard the unexecuted image, rebuild and relock."
                % (len(bound_changed), ", ".join(bound_changed)))

    return {
        "schema_version": SCHEMA_VERSION,
        "published_head": {"commit": head, "tree": head_tree},
        "ready_anchor": {"commit": ready_anchor, "tree": anchor_tree,
                         "parent": parent},
        "executable_code": {"commit": executable_commit,
                            "tree": executable_tree},
        "remote_ref": remote_ref,
        "head_equals_published": True,
        "worktree_clean": bool(require_clean),
        "changed_since_anchor": changed,
        "changed_since_anchor_count": len(changed),
        "all_changes_are_governance_only": True,
        "bound_paths_checked": len(bound_paths or ()),
        "bound_paths_changed_after_image_build": bound_changed,
        "execution_lock": lock_proof,
    }


def validate_proof(proof, executable_commit=None, executable_tree=None,
                   ready_anchor=None, ready_anchor_parent=None,
                   lock_sha256=None):
    """Re-check a serialized proof against the identities it must bind."""
    if not isinstance(proof, dict):
        raise ReadyAnchorDefect("the head proof must be a document")
    if proof.get("schema_version") != SCHEMA_VERSION:
        raise ReadyAnchorDefect(
            "the head proof schema %r is not %r"
            % (proof.get("schema_version"), SCHEMA_VERSION))
    for key in ("published_head", "ready_anchor", "executable_code"):
        block = proof.get(key)
        if not isinstance(block, dict):
            raise ReadyAnchorDefect("the head proof is missing %r" % key)
        _require_sha(block.get("commit"), "%s.commit" % key)
        _require_sha(block.get("tree"), "%s.tree" % key)
    if not proof.get("head_equals_published"):
        raise ReadyAnchorDefect(
            "the head proof does not record HEAD == origin/main")
    if not proof.get("worktree_clean"):
        raise ReadyAnchorDefect(
            "the head proof does not record a clean worktree")
    if not proof.get("all_changes_are_governance_only"):
        raise ReadyAnchorDefect(
            "the head proof records non-governance changes after the anchor")
    if proof.get("bound_paths_changed_after_image_build"):
        raise ReadyAnchorDefect(
            "the head proof records bound executable paths changed after the "
            "image build")
    pairs = (
        (executable_commit, proof["executable_code"]["commit"],
         "executable commit"),
        (executable_tree, proof["executable_code"]["tree"], "executable tree"),
        (ready_anchor, proof["ready_anchor"]["commit"], "ready anchor"),
    )
    for expected, actual, label in pairs:
        if expected and _require_sha(expected, label) != actual:
            raise ReadyAnchorDefect(
                "the head proof binds %s %s, not the required %s"
                % (label, actual, expected))
    if ready_anchor_parent:
        actual_parent = proof["ready_anchor"].get("parent")
        if _require_sha(actual_parent, "ready anchor parent") != \
                _require_sha(ready_anchor_parent, "ready_anchor_parent"):
            raise ReadyAnchorDefect(
                "the proof binds ready anchor parent %s, not %s"
                % (actual_parent, ready_anchor_parent))
    if lock_sha256:
        lock = proof.get("execution_lock")
        if not isinstance(lock, dict) or lock.get("path") != LOCK_PATH \
                or lock.get("sha256") != lock_sha256:
            raise ReadyAnchorDefect(
                "the ready anchor proof does not bind the active lock bytes")
    return proof


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r1_ready_anchor_v3.py",
        "identities": ["executable_code", "ready_anchor", "published_head"],
        "governance_allowlist": list(GOVERNANCE_ALLOWLIST),
        "governance_allowlist_prefixes": list(GOVERNANCE_ALLOWLIST_PREFIXES),
        "accepts_a_claimed_ready_commit": False,
        "closes": "G2-10",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    parser.add_argument("--prove", action="store_true")
    parser.add_argument("--lock-file")
    parser.add_argument("--root")
    parser.add_argument("--out")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.prove:
        if not args.lock_file:
            print("FAIL: --prove requires --lock-file", file=sys.stderr)
            return 2
        with open(args.lock_file, "rb") as handle:
            lock_raw = handle.read()
        lock = json.loads(lock_raw.decode("utf-8"))
        executable = lock["executable_code"]
        relationship = lock["ready_commit_relationship"]
        anchor = relationship.get("ready_anchor_commit")
        if anchor is None:
            try:
                anchor = resolve_ready_anchor(
                    relationship.get("ready_anchor_parent"), root=args.root)
            except ReadyAnchorDefect as exc:
                print("P0_R1_READY_ANCHOR_REFUSED=1", file=sys.stderr)
                print("  %s" % exc, file=sys.stderr)
                return 3
        bound = [entry["path"] for entry in executable["files"]]
        lock_identity = {
            "path": LOCK_PATH,
            "bytes": len(lock_raw),
            "sha256": hashlib.sha256(lock_raw).hexdigest(),
        }
        try:
            proof = prove(
                root=args.root, executable_commit=executable["commit"],
                executable_tree=executable["tree"], ready_anchor=anchor,
                ready_anchor_parent=relationship.get("ready_anchor_parent"),
                bound_paths=bound, lock_identity=lock_identity,
                require_clean=not args.allow_dirty)
        except ReadyAnchorDefect as exc:
            print("P0_R1_READY_ANCHOR_REFUSED=1", file=sys.stderr)
            print("  %s" % exc, file=sys.stderr)
            return 3
        payload = json.dumps(proof, indent=2, sort_keys=True) + "\n"
        if args.out:
            with open(args.out, "wb") as handle:
                handle.write(payload.encode("utf-8"))
        print(payload, end="")
        print("P0_R1_READY_ANCHOR_PROVED=1")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
