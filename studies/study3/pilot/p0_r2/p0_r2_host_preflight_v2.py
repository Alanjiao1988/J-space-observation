#!/usr/bin/env python3
"""The corrected P0-R2 first command: a host-side preflight that fails closed.

The published v1 first command was

    az acr run --cmd '<image> /usr/local/bin/p0_r2_successor_v1.sh preflight' /dev/null

and its context was ``/dev/null``. That command is useful -- it audits the image
against Git and round-trips the transport -- but it is structurally incapable of
observing the facts a successor actually has to know before spending a one-shot
envelope. Inside that container there is no working tree, no ``origin/main``
ref, no ready anchor, no post-anchor diff and no bound lock blob, so the
questions "is HEAD the published head?", "is the worktree clean?", "did anything
executable move after the anchor?" and "is the live prefix still free?" were not
merely unanswered: they could not be asked.

This module asks them, from a fresh clean checkout, in one transaction, and
refuses unless **every** one of them is proved. It may invoke the pinned image's
internal model-free canary as a subordinate check, and it consumes an in-VNet
prefix-preflight receipt for the one question a host outside the VNet cannot
answer -- but it never accepts an image-only ``/dev/null`` command as
sufficient, and it never reads a query error as an absence.

Refusal is the default. Every check must return ``PROVED``; anything else,
including ``AMBIGUOUS``, stops the preflight with a non-zero exit and prints no
success marker.

This module is model-free: no tokenizer construction or encode, no checkpoint
download or load, no model weight load, no prefill, no generation, no scoring,
no evidence row and no GPU operation. It creates, updates, starts and deletes
nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_closure_binding_v2 as CB2  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-host-preflight-v2"
STAGE = "STUDY3-P0-R2"

#: Printed exactly once each, and only when every check proved.
REQUIRED_MARKERS = (
    "P0_R2_HOST_PREFLIGHT_COMPLETE=1",
    "P0_R2_GOVERNANCE_CHAIN_PROVED=1",
    "P0_R2_HEAD_EQUALS_ORIGIN_MAIN=1",
    "P0_R2_WORKTREE_CLEAN=1",
    "P0_R2_P0_R1_TERMINAL=1",
    "P0_R2_REPLAY_ENVELOPE_UNCONSUMED=1",
    "P0_R2_LIVE_PREFIX_PROVED_UNUSED=1",
    "P0_R2_GPU_JOB_PROVED_ABSENT=1",
    "P0_R2_RECOVERY_JOB_PROVED_ABSENT=1",
    "P0_R2_MODEL_OPERATIONS_PERFORMED=0",
)

REFUSAL_MARKER = "P0_R2_HOST_PREFLIGHT_REFUSED=1"

GPU_JOB = "job-jspace-s3-p0r2-pilot-g1"
RECOVERY_JOB = "job-jspace-s3-p0r2-recover-g1"

#: The four canonical replay artifacts. Their presence before the gate runs
#: means the envelope is already spent.
CANONICAL_REPLAY_ARTIFACTS = (
    "p0_r2_replay_result.json",
    "p0_r2_replay_receipt.json",
    "p0_r2_replay_counters.json",
    "P0_R2_REPLAY_DISPOSITION.md",
)

#: Counters that must all be zero before the replay envelope is opened.
PRE_REPLAY_COUNTERS = (
    "tokenizer_constructions", "tokenizer_encodes", "checkpoint_downloads",
    "checkpoint_loads", "model_weight_loads", "prefills", "generations",
    "scored_rows", "evidence_rows_added", "gpu_allocations",
    "gpu_operations", "live_replay_invocations", "pilot_executions_started",
)

#: The native Windows packer limit this stage is bound to. P0-R1 stopped at 265.
MAX_NATIVE_PATH_CHARS = 240

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class HostPreflightRefused(Exception):
    """A required fact was not proved. Nothing may proceed."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(root, args, *, check=True, binary=False):
    completed = subprocess.run(  # noqa: S603 - fixed executable
        ["git", "-C", str(root), *args], capture_output=True,
        text=not binary, check=False)
    if check and completed.returncode:
        stderr = completed.stderr if isinstance(completed.stderr, str) \
            else completed.stderr.decode("utf-8", "replace")
        raise HostPreflightRefused(
            "git %s failed (%d): %s"
            % (" ".join(args), completed.returncode, stderr.strip()))
    return (completed.stdout, completed.returncode)


class Preflight:
    """Accumulate proofs. Any refusal poisons the whole transaction."""

    def __init__(self, root: Path, lock_path: Path):
        self.root = Path(root).resolve()
        self.lock_path = Path(lock_path).resolve()
        self.lock_raw = self.lock_path.read_bytes()
        self.lock = json.loads(self.lock_raw.decode("utf-8"))
        self.checks = []
        self.refusals = []

    # -- plumbing ----------------------------------------------------------
    def record(self, name: str, proved: bool, detail: dict) -> bool:
        entry = {"check": name,
                 "outcome": "PROVED" if proved else "REFUSED",
                 "detail": detail}
        self.checks.append(entry)
        if not proved:
            self.refusals.append(name)
        return proved

    def require(self, name: str, proved: bool, detail: dict) -> None:
        self.record(name, proved, detail)

    def git(self, *args, **kwargs):
        return _git(self.root, list(args), **kwargs)

    def blob(self, commit: str, path: str) -> dict:
        return CB2.blob_identity(self.root, commit, path)

    # -- checks ------------------------------------------------------------
    def check_head_equals_origin_main(self, *, fetch=True, remote="origin",
                                      branch="main") -> None:
        detail = {"fetch_attempted": bool(fetch)}
        if fetch:
            _, code = self.git("fetch", "--quiet", remote, branch, check=False)
            detail["fetch_exit_code"] = code
            if code != 0:
                # A host that could not fetch has not observed the remote. That
                # is an ambiguity, never a licence to trust a stale ref.
                self.require("head_equals_origin_main", False,
                             dict(detail, reason="the fetch failed; a stale "
                                  "remote ref is not a proof"))
                return
        head, _ = self.git("rev-parse", "HEAD")
        published, _ = self.git("rev-parse", "%s/%s" % (remote, branch))
        detail["head"] = head.strip()
        detail["origin_main"] = published.strip()
        self.require("head_equals_origin_main",
                     head.strip() == published.strip(), detail)

    def check_worktree_clean(self) -> None:
        out, _ = self.git("status", "--porcelain")
        dirty = [line for line in out.splitlines() if line.strip()]
        self.require("worktree_clean", not dirty,
                     {"dirty_entry_count": len(dirty), "dirty_entries": dirty[:32]})

    def check_exact_published_commit_and_tree(self, expect_commit=None,
                                              expect_tree=None) -> None:
        head, _ = self.git("rev-parse", "HEAD")
        tree, _ = self.git("rev-parse", "HEAD^{tree}")
        actual = {"commit": head.strip(), "tree": tree.strip()}
        detail = {"expected": {"commit": expect_commit, "tree": expect_tree},
                  "actual": actual,
                  "note": ("when no exact head is admitted yet, the final "
                           "published head is whatever origin/main proves it "
                           "to be, and the chain proof covers the rest")}
        proved = True
        if expect_commit:
            proved = proved and expect_commit == actual["commit"]
        if expect_tree:
            proved = proved and expect_tree == actual["tree"]
        self.require("exact_final_published_commit_and_tree", proved, detail)

    def check_exact_governance_bytes(self) -> None:
        head, _ = self.git("rev-parse", "HEAD")
        head = head.strip()
        entries = self.lock.get("governance_bytes") or []
        results = []
        proved = bool(entries)
        for entry in entries:
            try:
                actual = self.blob(head, entry["path"])
            except CB2.ClosureBindingDefect as exc:
                results.append({"path": entry.get("path"), "error": str(exc)})
                proved = False
                continue
            agrees = (actual["bytes"] == entry.get("bytes")
                      and actual["sha256"] == entry.get("sha256"))
            results.append({"path": entry["path"], "expected_bytes": entry.get("bytes"),
                            "actual_bytes": actual["bytes"],
                            "expected_sha256": entry.get("sha256"),
                            "actual_sha256": actual["sha256"],
                            "agrees": agrees})
            proved = proved and agrees
        self.require("exact_v2_authority_lock_schema_and_handoff_bytes", proved,
                     {"entries": results, "count": len(results)})

    def check_lock_self_binding(self) -> None:
        declared = self.lock.get("self") or {}
        actual = {"bytes": len(self.lock_raw), "sha256": _sha256(self.lock_raw)}
        head, _ = self.git("rev-parse", "HEAD")
        committed = None
        try:
            committed = self.blob(head.strip(),
                                  declared.get("path") or CB2.LOCK_PATH)
        except CB2.ClosureBindingDefect:
            committed = None
        proved = bool(committed) and committed["sha256"] == actual["sha256"] \
            and committed["bytes"] == actual["bytes"]
        self.require("active_lock_on_disk_is_the_committed_lock", proved,
                     {"on_disk": actual, "committed": committed,
                      "path": declared.get("path") or CB2.LOCK_PATH})

    def check_image_digest_and_task_blob(self) -> None:
        image = self.lock.get("image") or {}
        transport = self.lock.get("transport") or {}
        exec_commit = (self.lock.get("image_executable") or {}).get("commit")
        detail = {"image": image.get("reference"), "digest": image.get("digest"),
                  "task_path": transport.get("task_path"),
                  "bound_task_blob": transport.get("task_blob")}
        proved = True
        try:
            actual = self.blob(exec_commit, transport.get("task_path"))
            detail["committed_task_blob"] = actual["git_blob"]
            proved = actual["git_blob"] == transport.get("task_blob")
        except (CB2.ClosureBindingDefect, TypeError) as exc:
            detail["error"] = str(exc)
            proved = False
        reference = image.get("reference") or ""
        digest = image.get("digest") or ""
        proved = proved and bool(digest) and reference.endswith("@" + digest)
        detail["image_is_digest_pinned"] = reference.endswith("@" + digest)
        self.require("exact_image_digest_and_task_blob", proved, detail)

    def resolve_ready_anchor(self):
        """Resolve the anchor by ancestry, never by a field in the lock.

        The lock cannot record its own commit, so it records the anchor's
        *parent*. The anchor is the first first-parent descendant of that parent
        that actually carries the bound lock blob. Reading a ``ready_anchor``
        field instead would either be empty -- which is what refused here the
        first time -- or would be a value the lock could not honestly know.
        """
        relationship = self.lock.get("ready_commit_relationship") or {}
        declared = relationship.get("ready_anchor_commit")
        if declared:
            return declared, {"source": "declared"}
        parent = relationship.get("ready_anchor_parent")
        if not parent:
            return None, {"source": "unresolvable",
                          "reason": "the lock records neither a ready anchor "
                                    "nor its parent"}
        out, code = self.git("rev-list", "--first-parent", "--reverse",
                             "%s..HEAD" % parent, check=False)
        candidates = [line.strip() for line in out.splitlines() if line.strip()]
        if not candidates:
            return None, {"source": "ancestry", "parent": parent,
                          "reason": "no first-parent descendant of the "
                                    "recorded parent exists"}
        lock_path = (self.lock.get("self") or {}).get("path") or CB2.LOCK_PATH
        expected = _sha256(self.lock_raw)
        for candidate in candidates:
            try:
                blob = self.blob(candidate, lock_path)
            except CB2.ClosureBindingDefect:
                continue
            if blob["sha256"] == expected:
                return candidate, {"source": "ancestry", "parent": parent,
                                   "carries_the_bound_lock_bytes": True,
                                   "candidates_examined": candidates.index(
                                       candidate) + 1}
        return None, {"source": "ancestry", "parent": parent,
                      "reason": "no first-parent descendant carries the bound "
                                "lock bytes", "candidates": candidates[:8]}

    def check_governance_chain(self, *, require_head=True, require_clean=True):
        anchor, resolution = self.resolve_ready_anchor()
        head, _ = self.git("rev-parse", "HEAD")
        detail = {"ready_anchor": anchor, "anchor_resolution": resolution,
                  "governance_commit": head.strip()}
        if not anchor:
            self.require("governance_chain_proved", False, detail)
            for name in ("every_post_anchor_path_is_governance_or_evidence",
                         "no_bound_executable_or_scientific_path_changed",
                         "task_blob_unchanged"):
                self.require(name, False,
                             {"reason": "the ready anchor could not be "
                                        "resolved by ancestry"})
            return None
        try:
            proof = CB2.prove_v2_chain(
                root=self.root, lock=self.lock, ready_anchor=anchor,
                governance_commit=head.strip(),
                require_head=require_head, require_clean=require_clean,
                lock_identity={"path": (self.lock.get("self") or {}).get("path")
                               or CB2.LOCK_PATH,
                               "bytes": len(self.lock_raw),
                               "sha256": _sha256(self.lock_raw)})
        except CB2.ClosureBindingDefect as exc:
            self.require("governance_chain_proved", False,
                         dict(detail, refusal=str(exc)))
            self.require("every_post_anchor_path_is_governance_or_evidence",
                         False, {"reason": "the chain proof refused"})
            self.require("no_bound_executable_or_scientific_path_changed",
                         False, {"reason": "the chain proof refused"})
            self.require("task_blob_unchanged", False,
                         {"reason": "the chain proof refused"})
            return None
        detail["ancestry_proved"] = proof["ancestry_proved"]
        detail["changed_since_anchor"] = proof["changed_since_anchor"]
        self.require("governance_chain_proved", True, detail)
        self.require("every_post_anchor_path_is_governance_or_evidence", True,
                     {"paths": proof["changed_since_anchor"],
                      "classification": proof["post_anchor_classification"],
                      "caller_supplied_allowlist_accepted": False})
        self.require("no_bound_executable_or_scientific_path_changed",
                     not proof["bound_paths_changed_after_image_build"],
                     {"changed": proof["bound_paths_changed_after_image_build"]})
        self.require("task_blob_unchanged",
                     bool(proof["task_blob_identical_at_governance_source"]),
                     {"task_object": proof["task_object"]})
        return proof

    def check_p0_r1_terminal(self) -> None:
        terminal = self.lock.get("p0_r1_terminal") or {}
        stop = terminal.get("stop_commit")
        head, _ = self.git("rev-parse", "HEAD")
        detail = {"stop_commit": stop, "state": terminal.get("state")}
        proved = terminal.get("state") == "STOP_NO_MODEL_OPERATION" \
            and bool(terminal.get("replay_envelope_consumed")) \
            and terminal.get("launchable") is False
        try:
            out, _ = self.git("diff", "--name-only", stop, head.strip(), "--",
                              *CB2.PROTECTED_P0_R1_PREFIXES)
            changed = [line.strip() for line in out.splitlines() if line.strip()]
        except HostPreflightRefused as exc:
            detail["error"] = str(exc)
            changed = None
            proved = False
        detail["protected_paths_changed_since_stop_commit"] = changed
        proved = proved and changed == []
        bound = terminal.get("protected_bytes") or []
        byte_results = []
        for entry in bound:
            try:
                actual = self.blob(head.strip(), entry["path"])
            except CB2.ClosureBindingDefect as exc:
                byte_results.append({"path": entry.get("path"), "error": str(exc)})
                proved = False
                continue
            agrees = actual["sha256"] == entry.get("sha256") \
                and actual["bytes"] == entry.get("bytes")
            byte_results.append({"path": entry["path"], "agrees": agrees,
                                 "actual_sha256": actual["sha256"]})
            proved = proved and agrees
        detail["protected_bytes"] = byte_results
        self.require("p0_r1_terminal_and_nonlaunchable", proved, detail)

    def check_v1_superseded(self) -> None:
        supersession = self.lock.get("v1_supersession") or {}
        head, _ = self.git("rev-parse", "HEAD")
        detail = dict(supersession)
        proved = bool(supersession.get("superseded")) \
            and supersession.get("launchable") is False
        for key in ("record_path", "v1_lock_path"):
            entry = supersession.get(key)
            if not entry:
                proved = False
                continue
            try:
                actual = self.blob(head.strip(), entry)
                detail.setdefault("observed", {})[key] = actual
            except CB2.ClosureBindingDefect as exc:
                detail.setdefault("observed", {})[key] = {"error": str(exc)}
                proved = False
        expected = supersession.get("v1_lock_sha256")
        observed = (detail.get("observed") or {}).get("v1_lock_path") or {}
        if expected and observed.get("sha256") != expected:
            proved = False
        self.require("p0_r2_v1_superseded_and_nonlaunchable", proved, detail)

    def check_replay_unconsumed(self, results_dir) -> None:
        results_dir = Path(results_dir)
        present = []
        for name in CANONICAL_REPLAY_ARTIFACTS:
            candidate = results_dir / name
            if candidate.exists():
                present.append(str(candidate))
        try:
            relative = results_dir.resolve().relative_to(self.root).as_posix()
        except ValueError:
            relative = results_dir.as_posix()
        tracked = []
        out, code = self.git("ls-files", "--", relative, check=False)
        if code == 0:
            for line in out.splitlines():
                if Path(line.strip()).name in CANONICAL_REPLAY_ARTIFACTS:
                    tracked.append(line.strip())
        envelope = self.lock.get("replay_envelope") or {}
        proved = not present and not tracked \
            and envelope.get("consumed") is False \
            and int(envelope.get("invocations", 0)) == 0
        self.require("p0_r2_replay_envelope_unconsumed", proved,
                     {"results_dir": str(results_dir),
                      "results_dir_repository_path": relative,
                      "artifacts_present_on_disk": present,
                      "artifacts_tracked_in_git": tracked,
                      "envelope": envelope})
        self.require("canonical_p0_r2_replay_artifacts_absent",
                     not present and not tracked,
                     {"expected_names": list(CANONICAL_REPLAY_ARTIFACTS),
                      "found": present + tracked})

    def check_prefix_unused(self, receipt_path) -> None:
        attempt = ((self.lock.get("attempt") or {}).get("live_replay_attempt_id"))
        detail = {"preregistered_attempt_id": attempt,
                  "host_can_reach_the_private_account": False,
                  "query_error_is_absence": False}
        if not receipt_path:
            self.require("preregistered_live_attempt_prefix_unused", False,
                         dict(detail, reason="no in-VNet prefix-preflight "
                              "receipt was supplied; a host outside the VNet "
                              "cannot list the private account and an "
                              "unreachable listing is never an absence"))
            return
        try:
            receipt = json.loads(Path(receipt_path).read_bytes().decode("utf-8"))
        except (OSError, ValueError) as exc:
            self.require("preregistered_live_attempt_prefix_unused", False,
                         dict(detail, reason="unreadable receipt: %s" % exc))
            return
        detail["receipt"] = {k: receipt.get(k) for k in
                             ("schema_version", "attempt_id", "prefix",
                              "outcome", "object_count", "wrote_any_object",
                              "execution_identity")}
        proved = (receipt.get("schema_version", "").startswith(
                      "study3-p0-r2-prefix-preflight")
                  and receipt.get("attempt_id") == attempt
                  and receipt.get("outcome") == "PROVED_UNUSED"
                  and receipt.get("object_count") == 0
                  and receipt.get("wrote_any_object") is False
                  and bool(receipt.get("execution_identity")))
        self.require("preregistered_live_attempt_prefix_unused", proved, detail)

    def check_jobs_absent(self, *, runner=None) -> None:
        import p0_r2_azure_query_v1 as AZ
        azure = self.lock.get("azure") or {}
        for label, name in (("gpu", GPU_JOB), ("recovery", RECOVERY_JOB)):
            receipt = AZ.job_presence(
                name, resource_group=azure.get("resource_group"),
                subscription=azure.get("subscription"), runner=runner)
            self.require("%s_job_proved_absent" % label,
                         receipt.get("outcome") == "PROVED_ABSENT",
                         {"job": name, "outcome": receipt.get("outcome"),
                          "exit_code": receipt.get("exit_code"),
                          "stderr_excerpt": receipt.get("stderr_excerpt"),
                          "query_error_is_absence": False})

    def check_packing_canary(self) -> None:
        canary = self.lock.get("designated_packing_canary") or {}
        image = self.lock.get("image") or {}
        transport = self.lock.get("transport") or {}
        executable = self.lock.get("image_executable") or {}
        live = {
            "executable_commit": executable.get("commit"),
            "executable_tree": executable.get("tree"),
            "task_path": transport.get("task_path"),
            "task_blob": transport.get("task_blob"),
            "image": image.get("reference"),
            "digest": image.get("digest"),
        }
        detail = {"canary": canary, "live": live}
        try:
            agreement = CB2.verify_canary_live_agreement(
                {key: canary.get(key) for key in CB2.IMMUTABLE_BINDING_KEYS},
                live)
            detail["agreement"] = agreement
            proved = True
        except CB2.ClosureBindingDefect as exc:
            detail["refusal"] = str(exc)
            proved = False
        self.require("designated_packing_canary_matches_active_identity",
                     proved, detail)

    def check_native_path_budget(self, context_dir) -> None:
        measured = []
        longest = 0
        if context_dir:
            base = Path(context_dir).resolve()
            for path in [base, *base.rglob("*")]:
                native = str(path)
                measured.append({"path": native, "chars": len(native)})
                longest = max(longest, len(native))
        worktree_longest = 0
        out, _ = self.git("ls-files")
        for line in out.splitlines():
            entry = line.strip()
            if entry:
                worktree_longest = max(
                    worktree_longest, len(str(self.root / entry)))
        self.require("native_windows_packer_paths_within_budget",
                     bool(context_dir) and longest <= MAX_NATIVE_PATH_CHARS,
                     {"context_dir": str(context_dir) if context_dir else None,
                      "context_max_native_path_chars": longest,
                      "limit": MAX_NATIVE_PATH_CHARS,
                      "worktree_max_native_path_chars": worktree_longest,
                      "entries": sorted(measured,
                                        key=lambda item: -item["chars"])[:8],
                      "p0_r1_fatal_length": 265})

    def check_counters_zero(self) -> None:
        counters = self.lock.get("pre_replay_counters") or {}
        nonzero = {name: counters.get(name) for name in PRE_REPLAY_COUNTERS
                   if counters.get(name) not in (0,)}
        missing = [name for name in PRE_REPLAY_COUNTERS if name not in counters]
        self.require("all_pre_replay_counters_zero",
                     not nonzero and not missing,
                     {"counters": counters, "nonzero": nonzero,
                      "missing": missing})

    def check_image_canary(self, receipt_path) -> None:
        if not receipt_path:
            self.record("subordinate_image_canary", True,
                        {"supplied": False,
                         "note": "optional; an image-only /dev/null command is "
                                 "never sufficient on its own"})
            return
        try:
            receipt = json.loads(Path(receipt_path).read_bytes().decode("utf-8"))
        except (OSError, ValueError) as exc:
            self.require("subordinate_image_canary", False,
                         {"supplied": True, "error": str(exc)})
            return
        image = (self.lock.get("image") or {}).get("reference")
        proved = receipt.get("image") == image \
            and receipt.get("model_operations_performed") == 0 \
            and receipt.get("outcome") in ("PASS", "PROVED", "COMPLETE")
        self.require("subordinate_image_canary", proved,
                     {"supplied": True, "receipt": receipt})

    # -- assembly ----------------------------------------------------------
    def report(self) -> dict:
        proved = not self.refusals
        return {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "outcome": "HOST_PREFLIGHT_PROVED" if proved
                       else "HOST_PREFLIGHT_REFUSED",
            "root": str(self.root),
            "runs_from_a_fresh_clean_checkout": True,
            "image_only_dev_null_command_is_sufficient": False,
            "azure_query_error_is_absence": False,
            "checks": self.checks,
            "check_count": len(self.checks),
            "refusals": self.refusals,
            "refusal_count": len(self.refusals),
            "tokenizer_constructions": 0,
            "tokenizer_encodes": 0,
            "checkpoint_downloads": 0,
            "model_weight_loads": 0,
            "prefills": 0,
            "generations": 0,
            "scored_rows": 0,
            "gpu_operations": 0,
            "model_operations_performed": 0,
            "created_updated_or_started_anything": False,
        }


def run(root, lock_path, *, results_dir=None, prefix_receipt=None,
        image_canary_receipt=None, context_dir=None, fetch=True,
        expect_commit=None, expect_tree=None, job_runner=None) -> dict:
    preflight = Preflight(root, lock_path)
    preflight.check_head_equals_origin_main(fetch=fetch)
    preflight.check_worktree_clean()
    preflight.check_exact_published_commit_and_tree(expect_commit, expect_tree)
    preflight.check_exact_governance_bytes()
    preflight.check_lock_self_binding()
    preflight.check_image_digest_and_task_blob()
    preflight.check_governance_chain()
    preflight.check_p0_r1_terminal()
    preflight.check_v1_superseded()
    preflight.check_replay_unconsumed(
        Path(results_dir or (Path(root) / "studies/study3/pilot/p0/results/p0-r2")))
    preflight.check_prefix_unused(prefix_receipt)
    preflight.check_jobs_absent(runner=job_runner)
    preflight.check_packing_canary()
    preflight.check_native_path_budget(context_dir)
    preflight.check_counters_zero()
    preflight.check_image_canary(image_canary_receipt)
    return preflight.report()


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_host_preflight_v2.py",
        "stage": STAGE,
        "required_markers": list(REQUIRED_MARKERS),
        "refusal_marker": REFUSAL_MARKER,
        "runs_from_a_fresh_clean_checkout": True,
        "image_only_dev_null_command_is_sufficient": False,
        "may_invoke_image_canary_as_subordinate_check": True,
        "azure_query_error_is_absence": False,
        "max_native_path_chars": MAX_NATIVE_PATH_CHARS,
        "canonical_replay_artifacts": list(CANONICAL_REPLAY_ARTIFACTS),
        "pre_replay_counters": list(PRE_REPLAY_COUNTERS),
        "gpu_job": GPU_JOB,
        "recovery_job": RECOVERY_JOB,
        "supersedes": "the /dev/null image-only preflight",
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    parser.add_argument("--root", default=".")
    parser.add_argument("--lock-file")
    parser.add_argument("--results-dir")
    parser.add_argument("--prefix-receipt")
    parser.add_argument("--image-canary-receipt")
    parser.add_argument("--context-dir")
    parser.add_argument("--expect-head")
    parser.add_argument("--expect-tree")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if not args.lock_file:
        parser.error("--preflight requires --lock-file")
    try:
        report = run(args.root, args.lock_file,
                     results_dir=args.results_dir,
                     prefix_receipt=args.prefix_receipt,
                     image_canary_receipt=args.image_canary_receipt,
                     context_dir=args.context_dir,
                     expect_commit=args.expect_head,
                     expect_tree=args.expect_tree,
                     fetch=not args.no_fetch)
    except (HostPreflightRefused, OSError, ValueError) as exc:
        print(REFUSAL_MARKER, file=sys.stderr)
        print("  %s" % exc, file=sys.stderr)
        return 3

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload.encode("utf-8"))
    print(payload, end="")

    if report["outcome"] != "HOST_PREFLIGHT_PROVED":
        print(REFUSAL_MARKER, file=sys.stderr)
        for name in report["refusals"]:
            print("  refused: %s" % name, file=sys.stderr)
        return 3

    for marker in REQUIRED_MARKERS:
        print(marker)
    return 0


if __name__ == "__main__":
    sys.exit(main())
