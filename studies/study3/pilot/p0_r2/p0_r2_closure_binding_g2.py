#!/usr/bin/env python3
"""Study 3 P0-R2 generation-2 closure binding.

Authority:
``studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md``
sections 2, 6.1, 8 and 9.

The v2 closure binding already keeps nine identities apart and classifies every
post-anchor path from its own committed bytes and file mode. That logic is
correct and is imported here rather than restated, so the two generations cannot
drift and no v2 byte is edited.

Generation 2 adds exactly what generation 2 needs:

* proof that every file existing under the four frozen roots at the generation-1
  closure head is byte-unchanged at the generation-2 head;
* proof that the generation-2 namespace is disjoint from generation 1's;
* proof that generation 1 remains terminal, consumed and unre-run;
* proof that this authority was the first object committed after the
  generation-1 closure head.

There is deliberately no ``--allow-path``. Nothing a caller passes can widen any
set: the post-anchor classification is the v2 implementation's own, driven by
the lock's published closure.

Model-free: this module reads Git objects and hashes bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_closure_binding_v2 as CB2  # noqa: E402
import p0_r2_execution_lock_g2 as LOCK  # noqa: E402
import p0_r2_namespace_g2 as NS  # noqa: E402


REPO_ROOT = P0_R2_DIR.parent.parent.parent.parent

SCHEMA_VERSION = "study3-p0-r2-closure-binding-g2"
PROOF_SCHEMA_VERSION = "study3-p0-r2-governance-chain-proof-g2"
STAGE = "STUDY3-P0-R2"
GENERATION = 2

GENERATION1_CLOSURE_HEAD = LOCK.GENERATION1_TERMINAL["closure_head"]
AUTHORITY_PATH = LOCK.AUTHORITY_PATH
FROZEN_ROOTS = tuple(LOCK.FROZEN_ROOTS)

#: The nine identities v2 keeps apart, plus the two generation 2 adds.
IDENTITIES = tuple(CB2.IDENTITIES) + ("generation1_closure", "authority_object")


class ClosureBindingDefect(Exception):
    """A generation-2 closure stop."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(document) -> bytes:
    return json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _git(root, args, *, binary=False):
    completed = subprocess.run(  # noqa: S603 - fixed executable
        ["git", "-C", str(root), *args], capture_output=True,
        text=not binary, check=False)
    if completed.returncode:
        message = completed.stderr if not binary \
            else completed.stderr.decode("utf-8", "replace")
        raise ClosureBindingDefect(
            "git %s refused: %s" % (" ".join(args), message.strip()))
    return completed.stdout


def _tree_entries(root, commit, prefix):
    listing = _git(root, ["ls-tree", "-r", "--full-tree", commit, "--", prefix])
    entries = {}
    for line in listing.splitlines():
        if not line.strip():
            continue
        meta, _, path = line.partition("\t")
        mode, kind, blob = meta.split()
        if kind != "blob":
            continue
        entries[path] = {"mode": mode, "blob": blob}
    return entries


def prove_frozen_roots(root=None, *, head="HEAD",
                       baseline=GENERATION1_CLOSURE_HEAD) -> dict:
    """Every file under a frozen root must be byte-unchanged at ``head``."""
    root = Path(root or REPO_ROOT).resolve()
    roots = []
    changed = []
    removed = []
    total = 0
    for prefix in FROZEN_ROOTS:
        before = _tree_entries(root, baseline, prefix)
        after = _tree_entries(root, head, prefix)
        total += len(before)
        for path, identity in sorted(before.items()):
            current = after.get(path)
            if current is None:
                removed.append(path)
            elif current["blob"] != identity["blob"] \
                    or current["mode"] != identity["mode"]:
                changed.append(path)
        roots.append({
            "root": prefix,
            "baseline_file_count": len(before),
            "head_file_count": len(after),
            "added_under_root": sorted(set(after) - set(before)),
        })
    return {
        "schema_version": "study3-p0-r2-frozen-roots-proof-g2",
        "stage": STAGE,
        "generation": GENERATION,
        "baseline": baseline,
        "head": _git(root, ["rev-parse", head]).strip(),
        "roots": roots,
        "protected_file_count": total,
        "changed_paths": sorted(changed),
        "removed_paths": sorted(removed),
        "changed_count": len(changed),
        "removed_count": len(removed),
        "all_frozen_bytes_unchanged": not changed and not removed,
        "model_operations_performed": 0,
    }


def prove_authority_was_first(root=None, *,
                              baseline=GENERATION1_CLOSURE_HEAD,
                              head="HEAD") -> dict:
    """The authority must be the first object committed after the baseline."""
    root = Path(root or REPO_ROOT).resolve()
    revisions = _git(root, ["rev-list", "--first-parent", "--reverse",
                            "%s..%s" % (baseline, head)]).split()
    if not revisions:
        raise ClosureBindingDefect(
            "no commit exists after the generation-1 closure head")
    first = revisions[0]
    parents = _git(root, ["rev-list", "--parents", "-n", "1", first]).split()
    names = _git(root, ["diff-tree", "--no-commit-id", "--name-only", "-r",
                        first]).split("\n")
    names = sorted(name for name in names if name.strip())
    return {
        "schema_version": "study3-p0-r2-authority-first-proof-g2",
        "stage": STAGE,
        "generation": GENERATION,
        "baseline": baseline,
        "first_commit": first,
        "first_commit_parents": parents[1:],
        "first_commit_paths": names,
        "authority_path": AUTHORITY_PATH,
        "authority_was_the_first_committed_object":
            names == [AUTHORITY_PATH] and parents[1:] == [baseline],
        "commit_count_after_baseline": len(revisions),
        "model_operations_performed": 0,
    }


def prove_generation1_terminal(root=None, *, head="HEAD") -> dict:
    """Generation 1 stays terminal, consumed and unre-run."""
    root = Path(root or REPO_ROOT).resolve()
    terminal = dict(LOCK.GENERATION1_TERMINAL)
    receipt_path = ("studies/study3/pilot/p0/results/p0-r2/"
                    "p0_r2_acr_submission_receipt.json")
    payload = _git(root, ["show", "%s:%s" % (head, receipt_path)], binary=True)
    receipt = json.loads(payload.decode("utf-8"))
    agrees = (
        receipt.get("acr_run_id") == terminal["acr_run_id"]
        and receipt.get("attempt_id") == terminal["consumed_attempt"]
        and receipt.get("one_shot_envelope_consumed") is True
        and receipt.get("model_operations_performed") == 0
        and (receipt.get("binding") or {}).get("digest")
        == terminal["image_digest"])
    return {
        "schema_version": "study3-p0-r2-generation1-terminal-proof-g2",
        "stage": STAGE,
        "generation": GENERATION,
        "closure_head": terminal["closure_head"],
        "closure_head_is_ancestor": _is_ancestor(
            root, terminal["closure_head"], head),
        "p0_r1_stop_commit_is_ancestor": _is_ancestor(
            root, LOCK.P0_R1_TERMINAL["stop_commit"], head),
        "receipt_path": receipt_path,
        "receipt_sha256": _sha256(payload),
        "consumed_attempt": receipt.get("attempt_id"),
        "acr_run_id": receipt.get("acr_run_id"),
        "envelope_consumed": receipt.get("one_shot_envelope_consumed"),
        "model_operations_performed": receipt.get(
            "model_operations_performed"),
        "agrees_with_registered_terminal_facts": bool(agrees),
        "state": terminal["state"],
    }


def _is_ancestor(root, candidate, head):
    completed = subprocess.run(  # noqa: S603 - fixed executable
        ["git", "-C", str(root), "merge-base", "--is-ancestor", candidate,
         head], capture_output=True, text=True, check=False)
    return completed.returncode == 0


def prove_namespace_disjoint(lock: dict) -> dict:
    namespace = lock.get("namespace") or {}
    values = [namespace.get("live_replay_attempt_id"),
              namespace.get("pilot_attempt_id"),
              namespace.get("live_blob_prefix"),
              namespace.get("pilot_blob_prefix"),
              namespace.get("prefix_root"),
              (lock.get("azure") or {}).get("gpu_job"),
              (lock.get("azure") or {}).get("recovery_job")]
    try:
        NS.assert_disjoint_from_generation1(values)
        disjoint = True
        reason = None
    except NS.NamespaceDefect as exc:
        disjoint = False
        reason = str(exc)
    return {
        "schema_version": "study3-p0-r2-namespace-disjointness-proof-g2",
        "stage": STAGE,
        "generation": GENERATION,
        "checked_values": [value for value in values if value],
        "generation1_prefix_root": NS.GENERATION1_PREFIX_ROOT,
        "generation1_attempt_id_prefix": NS.GENERATION1_ATTEMPT_ID_PREFIX,
        "disjoint": disjoint,
        "reason": reason,
    }


def prove(root=None, *, lock: dict, head="HEAD",
          baseline=GENERATION1_CLOSURE_HEAD) -> dict:
    """Assemble the complete generation-2 governance chain proof."""
    root = Path(root or REPO_ROOT).resolve()
    frozen = prove_frozen_roots(root, head=head, baseline=baseline)
    first = prove_authority_was_first(root, baseline=baseline, head=head)
    terminal = prove_generation1_terminal(root, head=head)
    disjoint = prove_namespace_disjoint(lock)

    authority = lock.get("authority") or {}
    committed = _git(root, ["show", "%s:%s" % (head, AUTHORITY_PATH)],
                     binary=True)
    authority_agrees = (_sha256(committed) == authority.get("sha256")
                        and len(committed) == authority.get("bytes"))

    conditions = {
        "frozen_roots_unchanged": frozen["all_frozen_bytes_unchanged"],
        "authority_was_first_committed_object":
            first["authority_was_the_first_committed_object"],
        "generation1_remains_terminal":
            terminal["agrees_with_registered_terminal_facts"]
            and terminal["closure_head_is_ancestor"],
        "p0_r1_remains_terminal": terminal["p0_r1_stop_commit_is_ancestor"],
        "namespace_disjoint": disjoint["disjoint"],
        "authority_bytes_bound": bool(authority_agrees),
        "image_digest_is_new": (lock.get("image") or {}).get("is_new_digest")
        is True,
        "immutable_science_proved":
            (lock.get("immutable_science") or {}).get("proved") is True,
    }
    failed = sorted(name for name, value in conditions.items() if not value)
    return {
        "schema_version": PROOF_SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "identities": list(IDENTITIES),
        "head": frozen["head"],
        "baseline": baseline,
        "frozen_roots_proof": frozen,
        "authority_first_proof": first,
        "generation1_terminal_proof": terminal,
        "namespace_disjointness_proof": disjoint,
        "authority": {
            "path": AUTHORITY_PATH,
            "bytes": len(committed),
            "sha256": _sha256(committed),
            "agrees_with_lock": bool(authority_agrees),
        },
        "conditions": conditions,
        "condition_count": len(conditions),
        "failed_conditions": failed,
        "failed_count": len(failed),
        "outcome": "CHAIN_PROVED" if not failed else "CHAIN_REFUSED",
        "caller_supplied_allowlist": False,
        "model_operations_performed": 0,
    }


def classify_committed_path(root, commit, path, *, runner=None) -> dict:
    """Delegated verbatim to the v2 classifier, which is imported not copied."""
    return CB2.classify_committed_path(root, commit, path, runner=runner)


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_closure_binding_g2.py",
        "stage": STAGE,
        "generation": GENERATION,
        "proof_schema_version": PROOF_SCHEMA_VERSION,
        "identities": list(IDENTITIES),
        "frozen_roots": list(FROZEN_ROOTS),
        "generation1_closure_head": GENERATION1_CLOSURE_HEAD,
        "authority_path": AUTHORITY_PATH,
        "delegates_classification_to_v2": True,
        "edits_v1_or_v2": False,
        "accepts_allow_path": False,
        "caller_supplied_governance_allowlist": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--prove", action="store_true")
    mode.add_argument("--frozen-roots", action="store_true")
    parser.add_argument("--root")
    parser.add_argument("--lock-file")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--baseline", default=GENERATION1_CLOSURE_HEAD)
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    try:
        if args.frozen_roots:
            document = prove_frozen_roots(args.root, head=args.head,
                                          baseline=args.baseline)
            passed = document["all_frozen_bytes_unchanged"]
        else:
            if not args.lock_file:
                raise ClosureBindingDefect("--prove requires --lock-file")
            lock = json.loads(Path(args.lock_file).read_bytes().decode("utf-8"))
            document = prove(args.root, lock=lock, head=args.head,
                             baseline=args.baseline)
            passed = document["outcome"] == "CHAIN_PROVED"
    except (ClosureBindingDefect, ValueError) as exc:
        print("P0_R2_G2_CLOSURE_BINDING_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    payload = canonical_bytes(document)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload)
    print(payload.decode("utf-8"), end="")
    if not passed:
        print("P0_R2_G2_CLOSURE_BINDING_REFUSED=1 the chain did not prove",
              file=sys.stderr)
        return 3
    print("P0_R2_G2_FROZEN_BYTES_UNCHANGED=1")
    if not args.frozen_roots:
        print("P0_R2_G2_GOVERNANCE_CHAIN_PROVED=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
