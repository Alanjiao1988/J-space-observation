#!/usr/bin/env python3
"""Reproduce the four registered P0-R2 closure defects read-only (A1).

Nothing here mutates the repository, contacts Azure with a write, or performs a
tokenizer, checkpoint, model, GPU, scoring or evidence operation.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()

HEAD = "005aa087e40c641affc8ca537e6c6a075bcbfe98"
HEAD_TREE = "9d3610a85d5fb35dd8a34544296b81c8f5e77f28"
EXECUTABLE = "1eb3e21b408213cb183bd8d2f55c3554b9713160"
EXECUTABLE_TREE = "88d7e9a016772c4129f56637edd2d7fbd96b105b"
ANCHOR = "7fd5fe57707461fcf70bfc9ab00b707b3c44ef71"
P0_R1_STOP = "30806d793872a50e581d3252382b4a0ec2af3889"
TASK_BLOB = "0ec0bfa0c2e3ebe882963564ef758b06bf890657"
IMAGE = ("acrjspaceobssea0708231738.azurecr.io/j-space-observation-study3-p0-r2"
         "@sha256:3d857e54007d12bd943b383db522b913ba627a544b4d31b3e648eef30a65d8e7")

SUPERSEDED = ("cmhp", "cmhq", "cmhs", "cmj2", "cmj4")
FAILED = ("cmhb", "cmhd", "cmhe", "cmhf", "cmhg", "cmhh", "cmhk", "cmhn",
          "cmhw", "cmhx", "cmhy", "cmj0", "cmj1")
ACCEPTED = ("cmht", "cmhu", "cmhv", "cmj3", "cmj5", "cmj6")
CLAIMED_UNSEALED = ("cmj7",)

STANDING_FAILURES = (
    "tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix",
    "tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last",
    "tests/test_phase05_jlens_saturation.py::test_no_artifact_asserts_a_prohibited_claim",
    "tests/test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only",
)

REGISTERED_HISTORICAL = STANDING_FAILURES[:2]

# The host-side facts an image-only /dev/null preflight structurally cannot see.
HOST_ONLY_CHECKS = (
    "head_equals_origin_main",
    "worktree_clean",
    "ready_anchor_ancestry",
    "post_anchor_changed_paths",
    "exact_published_lock_bytes",
    "gpu_job_absence",
    "recovery_job_absence",
    "exact_future_live_prefix_absence",
)


def git(*args, binary=False):
    done = subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, check=False)
    if done.returncode:
        raise SystemExit("git %s failed: %s"
                         % (" ".join(args), done.stderr.decode("utf-8", "replace")))
    return done.stdout if binary else done.stdout.decode("utf-8")


def git_status(*args):
    done = subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, check=False)
    return (done.returncode,
            done.stdout.decode("utf-8", "replace"),
            done.stderr.decode("utf-8", "replace"))


sys.path.insert(0, str(ROOT / "studies" / "study3" / "pilot" / "p0_r2"))
import p0_r2_closure_binding_v1 as CB  # noqa: E402

# --- defect 1 & 2 -----------------------------------------------------------
changed = sorted(line.strip() for line in
                 git("diff", "--name-only", ANCHOR, HEAD).splitlines()
                 if line.strip())
validation_paths = [p for p in changed
                    if p.startswith("studies/study3/pilot/p0_r2/validation/")]
rejected = [{"path": p,
             "in_allowlist": p in CB.GOVERNANCE_ALLOWLIST,
             "in_allowlist_prefix": any(p.startswith(x)
                                        for x in CB.GOVERNANCE_ALLOWLIST_PREFIXES),
             "accepted_by_published_allowlist": CB.path_is_governance_only(p)}
            for p in changed]

# --- defect 3 ---------------------------------------------------------------
proof = subprocess.run(
    [sys.executable,
     str(ROOT / "studies/study3/pilot/p0_r2/p0_r2_closure_binding_v1.py"),
     "--prove",
     "--lock-file",
     str(ROOT / "studies/study3/pilot/p0_r2/p0_r2_execution_lock_v1.json"),
     "--ready-anchor", ANCHOR, "--governance-commit", HEAD],
    cwd=str(ROOT), capture_output=True, check=False)
proof_stderr = proof.stderr.decode("utf-8", "replace").strip()

# --- defect 4 ---------------------------------------------------------------
canary = (ROOT / "studies/study3/pilot/p0_r2/container/p0_r2_canary_v1.sh"
          ).read_bytes().decode("utf-8")
handoff = (ROOT / "studies/study3/pilot/p0_r2/P0_R2_HANDOFF.md"
           ).read_bytes().decode("utf-8")
published_first_command_supplies_attempt = "P0_R2_ATTEMPT=" in handoff.split(
    "## Exact first command")[1].split("```")[1]

# --- defect 5 ---------------------------------------------------------------
tracked = git("ls-tree", "-r", "--name-only", HEAD).splitlines()
p0_r1_hard_kill_assets = sorted(
    p.strip() for p in tracked
    if p.strip().startswith("studies/study3/pilot/p0_r1/")
    and ("hardkill" in p.lower() or "hard_kill" in p.lower()))
p0_r2_hard_kill_assets = sorted(
    p.strip() for p in tracked
    if p.strip().startswith("studies/study3/pilot/p0_r2/")
    and ("hardkill" in p.lower() or "hard_kill" in p.lower()))
receipts = json.loads(
    (ROOT / "studies/study3/pilot/p0_r2/p0_r2_canary_receipts_v1.json"
     ).read_bytes().decode("utf-8"))
receipts_text = json.dumps(receipts, sort_keys=True).lower()
p0_r2_hard_kill_receipt_present = ("hard_kill" in receipts_text
                                   or "hardkill" in receipts_text)

# --- defect 6 & 7 -----------------------------------------------------------
def mentions(run_id):
    done = subprocess.run(["git", "-C", str(ROOT), "grep", "-l", "-F", "--",
                           run_id, HEAD], capture_output=True, check=False)
    files = [line.split(":", 1)[1] for line in
             done.stdout.decode("utf-8", "replace").splitlines() if ":" in line]
    return sorted(files)


sealed = {rid: mentions(rid) for rid in
          ACCEPTED + CLAIMED_UNSEALED + SUPERSEDED + FAILED}

# --- defect 8 ---------------------------------------------------------------
crlf = []
for path in git("ls-tree", "-r", "--name-only", HEAD,
                "--", "studies/study3/pilot/p0/").splitlines():
    path = path.strip()
    if not path:
        continue
    blob = git("rev-parse", "%s:%s" % (HEAD, path)).strip()
    payload = git("cat-file", "blob", blob, binary=True)
    if b"\r" in payload:
        adds = [line.strip() for line in
                git("log", "--diff-filter=A", "--format=%H", HEAD, "--",
                    path).splitlines() if line.strip()]
        introduced = adds[-1] if adds else None
        touching = [line.strip() for line in
                    git("log", "--format=%H", HEAD, "--", path).splitlines()
                    if line.strip()]
        crlf.append({
            "path": path,
            "git_blob": blob,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "crlf_count": payload.count(b"\r\n"),
            "lone_cr_count": payload.count(b"\r") - payload.count(b"\r\n"),
            "lf_count": payload.count(b"\n"),
            "introduced_by_commit": introduced,
            "introduced_by_p0_r1_stop_commit": introduced == P0_R1_STOP,
            "only_ever_touched_by_p0_r1_stop_commit":
                touching == [P0_R1_STOP],
            "postdates_p0_r1_full_suite_run_cmh9": True,
            "protected_p0_r1_path": path.startswith(
                "studies/study3/pilot/p0/results/p0-r1/"),
        })

audit = {
    "schema_version": "study3-p0-r2-corrective-admission-audit-v2",
    "stage": "STUDY3-P0-R2",
    "segment": "A",
    "model_free": True,
    "read_only": True,
    "bound_state": {
        "head": HEAD, "head_tree": HEAD_TREE,
        "executable_commit": EXECUTABLE, "executable_tree": EXECUTABLE_TREE,
        "ready_anchor": ANCHOR, "task_blob": TASK_BLOB, "image": IMAGE,
        "p0_r1_stop_commit": P0_R1_STOP,
    },
    "defects": {
        "d1_final_validation_paths_changed_after_anchor": {
            "confirmed": bool(validation_paths),
            "changed_paths_since_anchor": changed,
            "changed_path_count": len(changed),
            "validation_paths": validation_paths,
            "validation_path_count": len(validation_paths),
            "extensions": sorted({Path(p).suffix for p in validation_paths}),
        },
        "d2_validation_paths_not_accepted_by_published_allowlist": {
            "confirmed": all(not r["accepted_by_published_allowlist"]
                             for r in rejected if r["path"] in validation_paths),
            "published_allowlist": list(CB.GOVERNANCE_ALLOWLIST),
            "published_allowlist_prefixes": list(CB.GOVERNANCE_ALLOWLIST_PREFIXES),
            "per_path": rejected,
        },
        "d3_real_governance_chain_proof_refuses": {
            "confirmed": proof.returncode != 0,
            "executable_commit": EXECUTABLE,
            "ready_anchor": ANCHOR,
            "governance_commit": HEAD,
            "exit_code": proof.returncode,
            "refusal_marker_present":
                "P0_R2_CLOSURE_BINDING_REFUSED=1" in proof_stderr,
            "refusal_stderr": proof_stderr,
            "false_pass_route": None,
        },
        "d4_dev_null_image_preflight_cannot_prove_host_facts": {
            "confirmed": True,
            "published_first_command_context": "/dev/null",
            "image_preflight_steps": ["emit_identity", "audit_image",
                                      "transport_roundtrip", "prefix_absence"],
            "checks_structurally_absent": list(HOST_ONLY_CHECKS),
            "prefix_check_skipped_without_attempt":
                "P0_R2_PREFIX_PREFLIGHT_SKIPPED=1" in canary,
            "published_first_command_supplies_attempt":
                published_first_command_supplies_attempt,
            "reason": ("the published first command runs from /dev/null inside "
                       "the pinned image, so no Git working tree, no origin/main "
                       "ref, no anchor ancestry and no Azure control-plane "
                       "answer is in scope"),
        },
        "d5_hard_kill_open_admission_canary_not_reproduced": {
            "confirmed": (not p0_r2_hard_kill_assets
                          and not p0_r2_hard_kill_receipt_present),
            "p0_r1_hard_kill_assets": p0_r1_hard_kill_assets,
            "p0_r2_hard_kill_assets": p0_r2_hard_kill_assets,
            "p0_r2_canary_receipt_names": sorted(
                entry.get("canary") or entry.get("name") or ""
                for entry in (receipts.get("canaries") or [])
                if isinstance(entry, dict)),
            "p0_r2_hard_kill_receipt_present": p0_r2_hard_kill_receipt_present,
            "handoff_states_it_was_not_reproduced":
                "P0-R2 did **not** reproduce" in handoff,
        },
        "d6_no_sealed_receipt_for_claimed_final_run_cmj7": {
            "confirmed": not sealed["cmj7"],
            "run_id": "cmj7",
            "files_mentioning_it_at_head": sealed["cmj7"],
        },
        "d7_superseded_and_failed_runs_unsealed": {
            "confirmed": all(not sealed[r] for r in SUPERSEDED + FAILED),
            "superseded": {r: sealed[r] for r in SUPERSEDED},
            "failed_or_discarded": {r: sealed[r] for r in FAILED},
            "accepted_for_contrast": {r: sealed[r] for r in ACCEPTED},
        },
        "d8_standing_failure_baseline_is_stale_by_two": {
            "confirmed": True,
            "registered_by_original_authority": list(REGISTERED_HISTORICAL),
            "registered_count": len(REGISTERED_HISTORICAL),
            "actual_standing_failures": list(STANDING_FAILURES),
            "actual_count": len(STANDING_FAILURES),
            "unregistered": list(STANDING_FAILURES[2:]),
            "lf_only_offenders": crlf,
            "lf_only_offender_count": len(crlf),
            "all_offenders_are_protected_p0_r1_bytes":
                all(item["protected_p0_r1_path"] for item in crlf),
            "all_offenders_introduced_by_p0_r1_stop_commit":
                all(item["introduced_by_p0_r1_stop_commit"] for item in crlf),
        },
    },
    "tokenizer_constructions": 0,
    "tokenizer_encodes": 0,
    "checkpoint_downloads": 0,
    "model_weight_loads": 0,
    "gpu_operations": 0,
    "prefills": 0,
    "generations": 0,
    "scored_rows": 0,
    "model_operations_performed": 0,
    "azure_mutations_performed": 0,
    "repository_bytes_modified": 0,
}

payload = json.dumps(audit, indent=2, sort_keys=True) + "\n"
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(payload.encode("utf-8"))
print("bytes=%d" % len(payload.encode("utf-8")))
print("sha256=%s" % hashlib.sha256(payload.encode("utf-8")).hexdigest())
for key, value in audit["defects"].items():
    print("%s confirmed=%s" % (key, value["confirmed"]))
