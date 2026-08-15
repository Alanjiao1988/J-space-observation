#!/usr/bin/env python3
"""Prove the corrected P0-R2 closure without granting anything to the caller.

The v1 binding failed in a specific, instructive way. It carried a module-level
``GOVERNANCE_ALLOWLIST`` of literal paths and asked one question of every path
that changed after the ready anchor: *is this string in the list?* Eight
executable validation inputs -- four shell scripts, an ACR task definition, a
Container Apps job definition and two receipts -- were then committed after the
anchor, the list did not contain them, and the real proof refused. The published
readiness claim was made anyway.

There are two wrong ways to repair that and one right one.

The first wrong repair is to add the eight paths to the list. That would make
the proof pass by asserting that executable shell scripts and job definitions
are "governance-only", which is false: a shell script committed after the anchor
changes what a later validation run executes.

The second wrong repair is to let the caller pass an allow-list. That converts a
proof into a grant, and a grant is exactly what the ready anchor exists to
prevent.

The right repair is to stop asking whether a *string* is listed and start
proving what the *bytes* are. This module classifies every path from its
committed blob and file mode:

* an entry is EXECUTABLE if its mode is 100755, or its blob begins with a
  shebang, or its extension is one this repository actually executes
  (``.py``, ``.sh``, ``.bash``, ``.bicep``, ``.ps1``, ``.bat``, ``.cmd``) or
  defines work to be executed (``.yaml``, ``.yml``), or its basename is a
  Dockerfile;
* anything else is NON-EXECUTABLE.

A path may appear after the ready anchor only when **three independent gates**
all admit it:

1. it classifies NON-EXECUTABLE from its own committed bytes;
2. it is a member of the exact ``governance_evidence_closure`` the active lock
   itself publishes -- an exact path set, sealed at the anchor, with no
   wildcard and no caller entry point;
3. it is not a member of the bound executable, validation, task, job, image or
   immutable-scientific closure.

No command-line option of this module can extend any of those sets. There is
deliberately no ``--allow-path``.

The module also splits the single overloaded notion of "the source commit" into
the nine identities the corrected closure has to keep apart:

``immutable_science``        the delegated P0-R1 commit and blob identities
``image_executable``         the commit and tree whose bytes are in the image
``host_closure_executable``  the commit and tree of the host-side tooling
``task_object``              the exact Git blob of the registered ACR task
``image``                    the digest-pinned image and its digest
``closure_base``             the commit the corrected closure was derived from
``ready_anchor``             the governance commit carrying the active lock
``governance_source``        the commit a live context reads its objects from
``published_head``           whatever ``origin/main`` is when this runs

This module is model-free. It imports only the standard library, contacts no
network, and performs no tokenizer, checkpoint, model weight, prefill,
generation, scoring, GPU or evidence operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


SCHEMA_VERSION = "study3-p0-r2-closure-binding-v2"
PROOF_SCHEMA_VERSION = "study3-p0-r2-governance-chain-proof-v2"
CLASSIFICATION_SCHEMA_VERSION = "study3-p0-r2-path-classification-v2"
STAGE = "STUDY3-P0-R2"

LOCK_PATH = "studies/study3/pilot/p0_r2/p0_r2_execution_lock_v2.json"
TASK_PATH = "studies/study3/pilot/p0_r2/container/p0_r2_acr_task_v1.yaml"

#: The nine identities the corrected closure keeps apart. Naming them here is
#: not decoration: the v1 defect was that six of them were collapsed into one.
IDENTITIES = (
    "immutable_science",
    "image_executable",
    "host_closure_executable",
    "task_object",
    "image",
    "closure_base",
    "ready_anchor",
    "governance_source",
    "published_head",
)

#: Identities a packing canary and any future live submission must share
#: byte-for-byte. None can change without a new image and a new canary.
IMMUTABLE_BINDING_KEYS = (
    "executable_commit",
    "executable_tree",
    "task_path",
    "task_blob",
    "image",
    "digest",
)

#: Extensions this repository executes, or which define work to be executed.
EXECUTABLE_EXTENSIONS = (
    ".py", ".sh", ".bash", ".bicep", ".ps1", ".bat", ".cmd", ".yaml", ".yml",
)

#: P0-R1 is terminal. Nothing in the corrected closure may change these roots,
#: before or after the anchor.
PROTECTED_P0_R1_PREFIXES = (
    "studies/study3/pilot/p0_r1/",
    "studies/study3/pilot/p0/results/p0-r1/",
)

EXECUTABLE = "EXECUTABLE"
NON_EXECUTABLE = "NON_EXECUTABLE"

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class ClosureBindingDefect(Exception):
    """The corrected closure cannot be proved non-circular and drift-free."""


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


def classify_committed_path(root, commit: str, path: str, *, runner=None) -> dict:
    """Classify one committed path from its own bytes and mode.

    A path that no longer exists at ``commit`` -- a deletion -- is classified
    from the name alone and is never admitted as non-executable, because a
    deletion of an executable path changes what runs just as surely as an edit.
    """
    commit = _require_sha40(commit, "commit")
    path = _safe_repo_path(path, "path")
    run = runner or (lambda args, check=True, binary=False:
                     _git(root, args, check=check, binary=binary))

    listing, _ = run(["ls-tree", commit, "--", path])
    reasons = []
    fields = listing.strip().split(None, 3)
    name = PurePosixPath(path).name
    suffix = PurePosixPath(path).suffix.lower()

    if len(fields) != 4:
        reasons.append("absent-at-commit")
        mode = None
        blob = None
        payload = b""
    else:
        mode, kind, blob, listed = fields[0], fields[1], fields[2], fields[3]
        if kind != "blob" or listed != path:
            raise ClosureBindingDefect(
                "%s is not exactly one blob at %s" % (path, commit))
        _require_sha40(blob, "%s blob" % path)
        payload, _ = run(["cat-file", "blob", blob], binary=True)
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        if mode == "100755":
            reasons.append("executable-mode-bit")
        if payload.startswith(b"#!"):
            reasons.append("shebang")

    if suffix in EXECUTABLE_EXTENSIONS:
        reasons.append("executable-extension:%s" % suffix)
    if name.startswith("Dockerfile"):
        reasons.append("dockerfile")
    if len(fields) != 4:
        reasons.append("deletion-of-a-path-cannot-be-proved-inert")

    classification = EXECUTABLE if reasons else NON_EXECUTABLE
    return {
        "schema_version": CLASSIFICATION_SCHEMA_VERSION,
        "path": path,
        "commit": commit,
        "mode": mode,
        "git_blob": blob,
        "bytes": len(payload),
        "sha256": _sha256(payload) if blob else None,
        "classification": classification,
        "reasons": reasons,
        "starts_with_shebang": bool(payload.startswith(b"#!")),
    }


def blob_identity(root, commit: str, repo_path: str, *, runner=None) -> dict:
    """Read one regular committed blob; never trust the mutable worktree."""
    commit = _require_sha40(commit, "commit")
    repo_path = _safe_repo_path(repo_path, "repository path")
    run = runner or (lambda args, check=True, binary=False:
                     _git(root, args, check=check, binary=binary))
    listing, _ = run(["ls-tree", commit, "--", repo_path])
    fields = listing.strip().split(None, 3)
    if len(fields) != 4 or fields[0] not in ("100644", "100755") \
            or fields[1] != "blob" or fields[3] != repo_path:
        raise ClosureBindingDefect(
            "%s is not exactly one regular blob at %s" % (repo_path, commit))
    blob = _require_sha40(fields[2], "%s blob" % repo_path)
    payload, _ = run(["cat-file", "blob", blob], binary=True)
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return {
        "path": repo_path,
        "mode": fields[0],
        "git_blob": blob,
        "bytes": len(payload),
        "sha256": _sha256(payload),
    }


def canary_binding(*, executable_commit: str, executable_tree: str,
                   task_path: str, task_blob: str, image: str,
                   digest: str) -> dict:
    """The immutable identity set a canary and a live run must share."""
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


def verify_canary_live_agreement(canary: dict, live: dict) -> dict:
    """Require immutable agreement; allow a governance-only source change."""
    if not isinstance(canary, dict) or not isinstance(live, dict):
        raise ClosureBindingDefect("both bindings must be documents")
    mismatched = []
    for key in IMMUTABLE_BINDING_KEYS:
        if key not in canary or key not in live:
            raise ClosureBindingDefect(
                "binding key %r is missing; the canary cannot be compared" % key)
        if canary[key] != live[key]:
            mismatched.append(key)
    if mismatched:
        raise ClosureBindingDefect(
            "the packing canary and the live submission disagree on immutable "
            "identity: %s. Rebuild the image and rerun the canary; a governance "
            "commit never repairs this." % ", ".join(sorted(mismatched)))
    return {
        "schema_version": "study3-p0-r2-canary-live-agreement-v2",
        "stage": STAGE,
        "immutable_keys_checked": list(IMMUTABLE_BINDING_KEYS),
        "immutable_identity_agrees": True,
        "canary_source_commit": canary.get("source_commit"),
        "live_source_commit": live.get("source_commit"),
        "source_commit_may_differ": True,
        "source_commit_difference_requires_governance_proof": True,
    }


def _closure_from_lock(lock: dict) -> dict:
    """Derive the bound closures from the lock. Nothing here is caller input."""
    executable = lock.get("image_executable") or {}
    host = lock.get("host_closure_executable") or {}

    def paths(entries):
        return [entry["path"] for entry in (entries or [])
                if isinstance(entry, dict) and entry.get("path")]

    bound = set()
    bound.update(paths(executable.get("files")))
    bound.update(paths(host.get("files")))
    bound.update(paths(lock.get("immutable_sources")))
    bound.update(paths(lock.get("validation_inputs")))
    transport = lock.get("transport") or {}
    if transport.get("task_path"):
        bound.add(transport["task_path"])
    for entry in (lock.get("job_specifications") or []):
        if isinstance(entry, dict) and entry.get("path"):
            bound.add(entry["path"])

    closure = lock.get("governance_evidence_closure") or []
    admitted = {}
    for entry in closure:
        if not isinstance(entry, dict) or not entry.get("path"):
            raise ClosureBindingDefect(
                "every governance_evidence_closure entry needs a path")
        path = _safe_repo_path(entry["path"], "governance_evidence path")
        if "*" in path or "?" in path:
            raise ClosureBindingDefect(
                "the governance/evidence closure is an exact path set; %r is a "
                "pattern" % path)
        admitted[path] = entry.get("class") or "evidence"
    return {"bound": bound, "admitted": admitted}


def prove_v2_chain(*, root=None, lock: dict, ready_anchor: str,
                   governance_commit: str, require_head=True,
                   require_clean=True, remote="origin", branch="main",
                   lock_identity=None, runner=None) -> dict:
    """Prove the corrected chain mechanically. The caller grants nothing."""
    run = runner or (lambda args, check=True, binary=False:
                     _git(root, args, check=check, binary=binary))

    image_exec = lock.get("image_executable") or {}
    host_exec = lock.get("host_closure_executable") or {}
    transport = lock.get("transport") or {}
    image_block = lock.get("image") or {}

    executable_commit = _require_sha40(image_exec.get("commit"),
                                       "image_executable.commit")
    executable_tree = _require_sha40(image_exec.get("tree"),
                                     "image_executable.tree")
    host_commit = _require_sha40(host_exec.get("commit"),
                                 "host_closure_executable.commit")
    host_tree = _require_sha40(host_exec.get("tree"),
                               "host_closure_executable.tree")
    closure_base = _require_sha40((lock.get("closure_base") or {}).get("commit"),
                                  "closure_base.commit")
    ready_anchor = _require_sha40(ready_anchor, "ready_anchor")
    governance_commit = _require_sha40(governance_commit, "governance_commit")
    task_path = _safe_repo_path(transport.get("task_path") or TASK_PATH,
                                "task_path")
    task_blob = _require_sha40(transport.get("task_blob"), "task_blob")
    digest = _require_digest(image_block.get("digest"), "image.digest")
    image_ref = image_block.get("reference")
    if not isinstance(image_ref, str) or not image_ref.endswith("@" + digest):
        raise ClosureBindingDefect(
            "the bound image reference is not pinned by the bound digest")

    for label, commit, tree in (("image_executable", executable_commit,
                                 executable_tree),
                                ("host_closure_executable", host_commit,
                                 host_tree)):
        out, _ = run(["rev-parse", "%s^{tree}" % commit])
        if _require_sha40(out.strip(), "%s tree" % label) != tree:
            raise ClosureBindingDefect(
                "%s commit %s carries tree %s, not the bound %s"
                % (label, commit, out.strip(), tree))

    out, _ = run(["rev-parse", "%s^{tree}" % ready_anchor])
    anchor_tree = _require_sha40(out.strip(), "anchor tree")
    out, _ = run(["rev-parse", "%s^{tree}" % governance_commit])
    governance_tree = _require_sha40(out.strip(), "governance tree")

    head = head_tree = None
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
                    "the working tree is not clean; refusing to prove a closure "
                    "binding for uncommitted bytes:\n%s" % out.strip())

    links = [
        (executable_commit, closure_base, "image executable -> closure base"),
        (host_commit, closure_base, "host closure executable -> closure base"),
        (closure_base, ready_anchor, "closure base -> ready anchor"),
        (ready_anchor, governance_commit, "ready anchor -> governance source"),
    ]
    if head is not None:
        links.append((governance_commit, head,
                      "governance source -> published head"))
    for older, newer, label in links:
        if older == newer:
            continue
        _, code = run(["merge-base", "--is-ancestor", older, newer], check=False)
        if code != 0:
            raise ClosureBindingDefect(
                "ancestry %s is not satisfied: %s is not an ancestor of %s"
                % (label, older, newer))
    if closure_base == ready_anchor:
        raise ClosureBindingDefect(
            "the ready anchor must be a strict descendant of the closure base; "
            "a commit cannot carry a lock over its own bytes")

    closures = _closure_from_lock(lock)
    admitted = closures["admitted"]
    bound = closures["bound"]

    newest = head if head is not None else governance_commit
    out, _ = run(["diff", "--name-only", ready_anchor, newest])
    changed = sorted(line.strip() for line in out.splitlines() if line.strip())

    classifications = []
    refusals = []
    for path in changed:
        entry = classify_committed_path(root, newest, path, runner=runner)
        entry["in_published_governance_evidence_closure"] = path in admitted
        entry["declared_class"] = admitted.get(path)
        entry["in_bound_executable_closure"] = path in bound
        entry["protected_p0_r1"] = any(
            path.startswith(prefix) for prefix in PROTECTED_P0_R1_PREFIXES)
        gates = {
            "classifies_non_executable":
                entry["classification"] == NON_EXECUTABLE,
            "member_of_published_closure": entry[
                "in_published_governance_evidence_closure"],
            "outside_bound_executable_closure": not entry[
                "in_bound_executable_closure"],
            "outside_protected_p0_r1": not entry["protected_p0_r1"],
        }
        entry["gates"] = gates
        entry["admitted"] = all(gates.values())
        classifications.append(entry)
        if not entry["admitted"]:
            refusals.append("%s (%s)" % (
                path, ", ".join(sorted(name for name, ok in gates.items()
                                       if not ok))))
    if refusals:
        raise ClosureBindingDefect(
            "%d path(s) changed after the ready anchor without passing every "
            "gate; an executable validation input is not governance: %s"
            % (len(refusals), "; ".join(refusals)))

    bound_changed = []
    if bound:
        out, _ = run(["diff", "--name-only", executable_commit, newest])
        drifted_exec = {line.strip() for line in out.splitlines() if line.strip()}
        out, _ = run(["diff", "--name-only", host_commit, newest])
        drifted_host = {line.strip() for line in out.splitlines() if line.strip()}
        bound_changed = sorted((drifted_exec | drifted_host) & bound)
        if bound_changed:
            raise ClosureBindingDefect(
                "%d bound path(s) changed after the image build or the host "
                "closure: %s. Discard the unexecuted image, rebuild and relock."
                % (len(bound_changed), ", ".join(bound_changed)))

    p0_r1_changed = []
    for reference in (closure_base, ready_anchor, newest):
        out, _ = run(["diff", "--name-only",
                      _require_sha40((lock.get("p0_r1_terminal") or {}).get(
                          "stop_commit"), "p0_r1.stop_commit"), reference,
                      "--", *PROTECTED_P0_R1_PREFIXES])
        p0_r1_changed += [line.strip() for line in out.splitlines() if line.strip()]
    p0_r1_changed = sorted(set(p0_r1_changed))
    if p0_r1_changed:
        raise ClosureBindingDefect(
            "P0-R1 protected bytes changed: %s" % ", ".join(p0_r1_changed))

    task_at_exec = blob_identity(root, executable_commit, task_path,
                                 runner=runner)
    task_at_gov = blob_identity(root, governance_commit, task_path, runner=runner)
    if task_at_exec["git_blob"] != task_at_gov["git_blob"]:
        raise ClosureBindingDefect(
            "the ACR task blob changed between the image executable commit (%s) "
            "and the governance source (%s)"
            % (task_at_exec["git_blob"], task_at_gov["git_blob"]))
    if task_at_exec["git_blob"] != task_blob:
        raise ClosureBindingDefect(
            "the bound task blob %s is not the committed task blob %s"
            % (task_blob, task_at_exec["git_blob"]))

    lock_proof = None
    if lock_identity:
        path = _safe_repo_path(lock_identity.get("path") or LOCK_PATH,
                               "lock path")
        actual = blob_identity(root, ready_anchor, path, runner=runner)
        expected_bytes = lock_identity.get("bytes")
        expected_sha = lock_identity.get("sha256")
        if expected_sha is not None and not _SHA256.fullmatch(str(expected_sha)):
            raise ClosureBindingDefect("the bound lock sha256 is malformed")
        if (expected_bytes is not None and actual["bytes"] != expected_bytes) \
                or (expected_sha is not None
                    and actual["sha256"] != expected_sha):
            raise ClosureBindingDefect(
                "ready anchor %s does not carry the bound lock bytes (found %d "
                "bytes sha256 %s)" % (ready_anchor, actual["bytes"],
                                      actual["sha256"]))
        gov_lock = blob_identity(root, governance_commit, path, runner=runner)
        if gov_lock["git_blob"] != actual["git_blob"]:
            raise ClosureBindingDefect(
                "the governance source carries a different lock blob than the "
                "ready anchor; the embedded lock bytes are not the bound lock")
        lock_proof = dict(actual)
        lock_proof["identical_at_governance_source"] = True

    immutable = []
    for entry in (lock.get("immutable_sources") or []):
        if not isinstance(entry, dict) or not entry.get("path"):
            continue
        actual = blob_identity(root, executable_commit, entry["path"],
                               runner=runner)
        if entry.get("sha256") and actual["sha256"] != entry["sha256"]:
            raise ClosureBindingDefect(
                "immutable scientific source %s is sha256 %s, not the bound %s"
                % (entry["path"], actual["sha256"], entry["sha256"]))
        immutable.append(actual)

    return {
        "schema_version": PROOF_SCHEMA_VERSION,
        "stage": STAGE,
        "outcome": "GOVERNANCE_CHAIN_PROVED",
        "identities": list(IDENTITIES),
        "immutable_science": {"count": len(immutable), "sources": immutable},
        "image_executable": {"commit": executable_commit,
                             "tree": executable_tree},
        "host_closure_executable": {"commit": host_commit, "tree": host_tree},
        "task_object": task_at_exec,
        "image": {"reference": image_ref, "digest": digest},
        "closure_base": {"commit": closure_base},
        "ready_anchor": {"commit": ready_anchor, "tree": anchor_tree},
        "governance_source": {"commit": governance_commit,
                              "tree": governance_tree},
        "published_head": (None if head is None
                           else {"commit": head, "tree": head_tree}),
        "head_equals_published": bool(require_head),
        "worktree_clean": bool(require_head and require_clean),
        "ancestry_proved": [label for _, _, label in links],
        "changed_since_anchor": changed,
        "changed_since_anchor_count": len(changed),
        "post_anchor_classification": classifications,
        "every_post_anchor_path_proved_non_executable": True,
        "every_post_anchor_path_in_published_closure": True,
        "caller_supplied_allowlist_accepted": False,
        "published_governance_evidence_closure": sorted(admitted),
        "bound_executable_closure_size": len(bound),
        "bound_paths_changed_after_image_build": bound_changed,
        "p0_r1_protected_paths_changed": p0_r1_changed,
        "task_blob_identical_at_governance_source": True,
        "execution_lock": lock_proof,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "prefills": 0,
        "generations": 0,
        "scored_rows": 0,
        "model_operations_performed": 0,
    }


def validate_proof(proof, *, image_executable=None, host_executable=None,
                   ready_anchor=None, governance_commit=None, lock_sha256=None,
                   task_blob=None, digest=None) -> dict:
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
    if list(proof.get("identities") or []) != list(IDENTITIES):
        raise ClosureBindingDefect(
            "the proof does not keep the nine corrected identities apart")
    for key in ("image_executable", "host_closure_executable", "ready_anchor",
                "governance_source", "closure_base"):
        block = proof.get(key)
        if not isinstance(block, dict):
            raise ClosureBindingDefect("the proof is missing %r" % key)
        _require_sha40(block.get("commit"), "%s.commit" % key)
    for flag in ("every_post_anchor_path_proved_non_executable",
                 "every_post_anchor_path_in_published_closure",
                 "task_blob_identical_at_governance_source"):
        if not proof.get(flag):
            raise ClosureBindingDefect("the proof does not record %s" % flag)
    if proof.get("caller_supplied_allowlist_accepted"):
        raise ClosureBindingDefect(
            "the proof accepted a caller-supplied allow-list")
    for key in ("bound_paths_changed_after_image_build",
                "p0_r1_protected_paths_changed"):
        if proof.get(key):
            raise ClosureBindingDefect("the proof records %s" % key)
    pairs = (
        (image_executable, proof["image_executable"]["commit"],
         "image executable commit"),
        (host_executable, proof["host_closure_executable"]["commit"],
         "host closure executable commit"),
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
    if digest and (proof.get("image") or {}).get("digest") != digest:
        raise ClosureBindingDefect("the proof does not bind the active digest")
    if lock_sha256:
        lock = proof.get("execution_lock")
        if not isinstance(lock, dict) or lock.get("sha256") != lock_sha256:
            raise ClosureBindingDefect(
                "the proof does not bind the active lock bytes")
    return proof


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_closure_binding_v2.py",
        "stage": STAGE,
        "identities": list(IDENTITIES),
        "identity_count": len(IDENTITIES),
        "immutable_binding_keys": list(IMMUTABLE_BINDING_KEYS),
        "executable_extensions": list(EXECUTABLE_EXTENSIONS),
        "protected_p0_r1_prefixes": list(PROTECTED_P0_R1_PREFIXES),
        "post_anchor_gates": [
            "classifies_non_executable",
            "member_of_published_closure",
            "outside_bound_executable_closure",
            "outside_protected_p0_r1",
        ],
        "classification_is_derived_from_committed_bytes": True,
        "accepts_caller_supplied_allowlist": False,
        "has_allow_path_option": False,
        "module_level_path_allowlist": False,
        "lock_records_its_own_commit": False,
        "supersedes": "p0_r2_closure_binding_v1.py",
        "v1_defect": (
            "a module-level literal path allow-list admitted or refused paths by "
            "name; eight executable validation inputs committed after the ready "
            "anchor were neither listed nor inert, and the readiness claim was "
            "published even though the real proof refused"),
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--prove", action="store_true")
    mode.add_argument("--classify", metavar="PATH")
    parser.add_argument("--root")
    parser.add_argument("--lock-file")
    parser.add_argument("--commit")
    parser.add_argument("--governance-commit")
    parser.add_argument("--ready-anchor")
    parser.add_argument("--out")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--no-head", action="store_true")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if args.classify:
        commit = args.commit
        if not commit:
            out, _ = _git(args.root, ["rev-parse", "HEAD"])
            commit = out.strip()
        try:
            print(json.dumps(
                classify_committed_path(args.root, commit, args.classify),
                indent=2, sort_keys=True))
        except ClosureBindingDefect as exc:
            print("P0_R2_CLOSURE_BINDING_V2_REFUSED=1 %s" % exc, file=sys.stderr)
            return 3
        return 0

    if not args.lock_file:
        parser.error("--prove requires --lock-file")
    try:
        lock_raw = Path(args.lock_file).read_bytes()
        lock = json.loads(lock_raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print("P0_R2_CLOSURE_BINDING_V2_REFUSED=1 unreadable lock: %s" % exc,
              file=sys.stderr)
        return 2

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
            print("P0_R2_CLOSURE_BINDING_V2_REFUSED=1 %s" % exc, file=sys.stderr)
            return 3

    governance = args.governance_commit
    if not governance:
        out, _ = _git(root, ["rev-parse", "HEAD"])
        governance = out.strip()

    lock_identity = {
        "path": (lock.get("self") or {}).get("path") or LOCK_PATH,
        "bytes": len(lock_raw),
        "sha256": _sha256(lock_raw),
    }
    try:
        proof = prove_v2_chain(
            root=root, lock=lock, ready_anchor=anchor,
            governance_commit=governance, lock_identity=lock_identity,
            require_head=not args.no_head, require_clean=not args.allow_dirty)
    except ClosureBindingDefect as exc:
        print("P0_R2_CLOSURE_BINDING_V2_REFUSED=1", file=sys.stderr)
        print("  %s" % exc, file=sys.stderr)
        return 3

    payload = json.dumps(proof, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")
    print("P0_R2_CLOSURE_BINDING_V2_PROVED=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
