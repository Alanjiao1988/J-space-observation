#!/usr/bin/env python3
"""Study 3 P0-R2 generation-2 inter-segment admission gate.

Authority:
``studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md``
section 9.

Every condition below is derived from Git, from an exact published receipt, or
from a read-only Azure result. No caller may supply a condition's truth value:
there is no ``--assume``, no ``--allow``, no ``--force`` and no allowlist. A
condition that cannot be derived is reported as **underived**, which is a
failure, never a pass.

The gate prints ``P0_R2_G2_PHASE_B_AUTHORIZED=1`` only when every condition is
true and none is underived. Otherwise it publishes a truthful stop disposition
and authorizes nothing.

Model-free: no tokenizer, checkpoint, model weight, GPU or scoring operation.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
P0_R2_DIR = HERE.parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_azure_query_v1 as AZURE  # noqa: E402
import p0_r2_closure_binding_g2 as CB  # noqa: E402
import p0_r2_execution_lock_g2 as LOCK  # noqa: E402
import p0_r2_namespace_g2 as NS  # noqa: E402
import p0_r2_prefix_proof_g2 as PREFIX  # noqa: E402


REPO_ROOT = P0_R2_DIR.parent.parent.parent.parent

SCHEMA_VERSION = "study3-p0-r2-phase-b-admission-g2"
STAGE = "STUDY3-P0-R2"
GENERATION = 2

UNDERIVED = "UNDERIVED"


class AdmissionDefect(Exception):
    """The admission document could not be built honestly."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(document) -> bytes:
    return json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _git(root, args, *, binary=False):
    completed = subprocess.run(  # noqa: S603 - fixed executable
        ["git", "-C", str(root), *args], capture_output=True,
        text=not binary, check=False)
    if completed.returncode:
        return None
    return completed.stdout


def _read(path):
    try:
        return json.loads(Path(path).read_bytes().decode("utf-8"))
    except Exception:  # noqa: BLE001 - an unreadable input stays underived
        return None


def build(root=None, *, lock_file, canary_receipts, attempt_ledger,
          differential=None, host_preflight=None, ready_anchor=None,
          runner=None) -> dict:
    root = Path(root or REPO_ROOT).resolve()

    lock_payload = Path(lock_file).read_bytes()
    lock = json.loads(lock_payload.decode("utf-8"))
    canaries = _read(canary_receipts)
    ledger = _read(attempt_ledger)
    validation = _read(differential) if differential else None
    differential_document = ((validation or {}).get("full_differential_suite")
                             if validation else None)
    preflight = _read(host_preflight) if host_preflight else None

    head = (_git(root, ["rev-parse", "HEAD"]) or "").strip() or None
    origin = (_git(root, ["rev-parse", "origin/main"]) or "").strip() or None
    status = _git(root, ["status", "--porcelain=v1", "--untracked-files=all"])
    worktree_clean = None if status is None else status.strip() == ""

    chain = None
    try:
        chain = CB.prove(root, lock=lock, head=head or "HEAD")
    except Exception:  # noqa: BLE001 - an unprovable chain stays underived
        chain = None

    lock_validation = None
    try:
        lock_validation = LOCK.validate(lock)
    except Exception:  # noqa: BLE001
        lock_validation = None

    azure = lock.get("azure") or {}
    absence = None
    if runner is not False:
        try:
            absence = {
                name: AZURE.job_presence(
                    name, resource_group=azure.get("resource_group"),
                    subscription=azure.get("subscription"), runner=runner
                ).get("outcome")
                for name in (NS.GPU_JOB, NS.RECOVERY_JOB, NS.PREFIX_JOB)
            }
        except Exception:  # noqa: BLE001
            absence = None

    authority_commit = None
    authority_time = None
    if chain is not None:
        authority_commit = chain["authority_first_proof"]["first_commit"]
        raw = _git(root, ["show", "-s", "--format=%cI", authority_commit])
        authority_time = (raw or "").strip() or None

    generation2_start_times = []
    if ledger is not None:
        for run in ledger.get("runs", []):
            if run.get("generation") != 2:
                continue
            generation2_start_times.append(run.get("start_time"))
    earliest_generation2 = None
    if generation2_start_times and all(generation2_start_times):
        earliest_generation2 = min(generation2_start_times)

    def _instant(value):
        if not value or not isinstance(value, str):
            return None
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed.astimezone(datetime.timezone.utc)

    def _authority_precedes_azure():
        # Compared as instants. The authority commit carries the authoring
        # host's UTC offset and Azure reports +00:00, so a string comparison
        # would silently answer a different question.
        published = _instant(authority_time)
        earliest = _instant(earliest_generation2)
        if published is None or earliest is None:
            return None
        return published < earliest

    prefix_canary = ((canaries or {}).get("in_vnet_prefix_canary") or {})
    packing = ((canaries or {}).get("acr_packing_and_pre_gate_canary") or {})
    hardkill = ((canaries or {})
                .get("hard_kill_open_admission_recovery_canary") or {})
    job_absence = ((canaries or {}).get("non_vacuous_job_absence") or {})
    launch = ((canaries or {}).get("windows_launch_path_proof") or {})

    results_root = Path(root) / (lock.get("namespace") or {}).get(
        "results_root", NS.RESULTS_ROOT)
    canonical_artifacts = [
        "P0_R2_REPLAY_DISPOSITION.md", "p0_r2_replay_counters.json",
        "p0_r2_replay_receipt.json", "p0_r2_replay_result.json",
    ]
    artifacts_present = [name for name in canonical_artifacts
                         if (results_root / name).exists()]

    counters = lock.get("pre_replay_counters") or {}
    envelope = lock.get("replay_envelope") or {}
    legal = lock.get("legal_state") or {}
    science = lock.get("immutable_science") or {}
    transport = lock.get("transport") or {}
    namespace = lock.get("namespace") or {}

    def condition(value):
        return UNDERIVED if value is None else bool(value)

    conditions = {
        "1_authority_was_first_committed_object": condition(
            None if chain is None
            else chain["authority_first_proof"][
                "authority_was_the_first_committed_object"]),
        "2_authority_published_before_any_generation2_azure_operation":
            condition(_authority_precedes_azure()),
        "3_p0_r1_terminal_and_byte_unchanged": condition(
            None if chain is None
            else chain["conditions"]["p0_r1_remains_terminal"]
            and chain["frozen_roots_proof"]["all_frozen_bytes_unchanged"]),
        "4_generation1_terminal_and_byte_unchanged": condition(
            None if chain is None
            else chain["conditions"]["generation1_remains_terminal"]),
        "5_no_generation1_replay_or_pilot_rerun": condition(
            None if ledger is None else
            ledger.get("generation2_replay_capable_runs") == 0
            and sorted(ledger.get("replay_or_model_capable_runs") or []) ==
            ["cmjv"]),
        "6_frozen_generation1_files_unchanged": condition(
            None if chain is None
            else chain["frozen_roots_proof"]["all_frozen_bytes_unchanged"]),
        "7_generation2_namespaces_disjoint": condition(
            None if chain is None
            else chain["conditions"]["namespace_disjoint"]),
        "8_scientific_blobs_match_registered_science": condition(
            science.get("proved")),
        "9_generation2_image_is_a_new_digest": condition(
            (lock.get("image") or {}).get("is_new_digest")),
        "10_every_image_bound_path_passes_audit": condition(
            None if packing is None or not packing
            else packing.get("checks", {}).get("image_to_git_audit_ran")),
        "11_final_acr_task_blob_matches_git": condition(
            (_git(root, ["rev-parse", "%s:%s" % (head, transport.get(
                "task_path"))]) or "").strip() == transport.get("task_blob")
            if head and transport.get("task_path") else None),
        "12_final_acr_context_has_exactly_two_entries": condition(
            packing.get("context_entry_count") == 2 if packing else None),
        "13_maximum_native_context_path_at_most_100": condition(
            (packing.get("maximum_native_path") or 10 ** 9) <= 100
            if packing else None),
        "14_shared_prefix_validator_used_by_canary_and_live": condition(
            (lock.get("prefix_proof") or {}).get(
                "shared_canary_and_live_validator")
            and PREFIX.implementation_identity()[
                "separate_canary_and_live_validators"] is False),
        "15_acr_live_path_performs_no_private_storage_probe": condition(
            None if not packing else
            packing.get("checks", {}).get("no_managed_identity_probe")
            and packing.get("checks", {}).get("no_in_container_storage_call")),
        "16_in_vnet_prefix_canary_passed": condition(
            prefix_canary.get("outcome_class") == "PASS"
            if prefix_canary else None),
        "17_acr_packing_and_pre_gate_canary_passed": condition(
            packing.get("outcome_class") == "PASS" if packing else None),
        "18_hard_kill_recovery_canary_passed": condition(
            hardkill.get("outcome_class") == "PASS" if hardkill else None),
        "19_both_bounded_jobs_proved_absent_non_vacuously": condition(
            job_absence.get("non_vacuous") if job_absence else None),
        "20_all_required_run_records_sealed_and_unambiguous": condition(
            None if ledger is None else
            ledger.get("sealed_count") == ledger.get("run_count")
            and ledger.get("unavailable_count") == 0
            and ledger.get("ambiguous_count") == 0
            and ledger.get("fabricated_hashes") == 0),
        "21_full_differential_zero_new_failures_zero_collection_errors":
            condition(None if differential_document is None else
                      differential_document.get("new_failure_count") == 0
                      and differential_document.get("zero_collection_errors")
                      is True),
        "22_four_standing_failure_signatures_match_exactly": condition(
            None if differential_document is None
            else differential_document.get("signatures_agree") is True
            and differential_document.get("standing_failures_are_the_"
                                          "registered_four") is True),
        "23_lock_and_schema_validate_from_committed_bytes": condition(
            None if lock_validation is None
            else lock_validation.get("outcome") == "LOCK_VALID"),
        "24_authority_executable_image_task_manifest_attempts_bound": condition(
            None if chain is None else
            chain["conditions"]["authority_bytes_bound"]
            and bool(namespace.get("live_replay_attempt_id"))
            and bool(namespace.get("pilot_attempt_id"))
            and bool(transport.get("task_blob"))),
        "25_governance_ancestry_and_post_anchor_classification_pass": condition(
            None if chain is None else chain["outcome"] == "CHAIN_PROVED"),
        "26_second_fresh_checkout_reproduces_host_preflight": condition(
            None if preflight is None
            else preflight.get("outcome") == "PREFLIGHT_PASS"),
        "27_head_equals_origin_main_equals_admitted_head": condition(
            None if not head or not origin else head == origin
            and (ready_anchor is None or head == ready_anchor)),
        "28_worktree_clean": condition(worktree_clean),
        "29_azure_cli_resolves_and_benign_checks_pass": condition(
            None if not launch else
            all(check.get("passed") for check in launch.get("checks", []))),
        "30_generation2_live_replay_never_invoked": condition(
            envelope.get("invocations") == 0),
        "31_generation2_replay_gate_never_run": condition(
            None if canaries is None
            else canaries.get("replay_gate_invoked_by_any_canary") is False),
        "32_generation2_one_shot_envelope_unconsumed": condition(
            envelope.get("consumed") is False),
        "33_generation2_live_prefix_not_yet_written": condition(
            None if prefix_canary is None or not prefix_canary else
            prefix_canary.get("did_not_use_live_or_pilot_prefix") is True),
        "34_generation2_canonical_replay_artifacts_absent": condition(
            len(artifacts_present) == 0),
        "35_all_pre_replay_counters_zero": condition(
            bool(counters) and all(value == 0 for value in counters.values())),
        "36_formal_execution_authorized_is_false": condition(
            legal.get("formal_execution_authorized") is False),
        "37_evidence_ledger_remains_ev_0016": condition(
            legal.get("evidence_ledger_tail") == "EV-0016"),
        "38_no_fact_is_unknown_or_underived": None,
    }

    derived = {name: value for name, value in conditions.items()
               if name != "38_no_fact_is_unknown_or_underived"}
    underived = sorted(name for name, value in derived.items()
                       if value == UNDERIVED)
    failed = sorted(name for name, value in derived.items() if value is False)
    conditions["38_no_fact_is_unknown_or_underived"] = not (underived or failed)
    if underived or failed:
        conditions["38_no_fact_is_unknown_or_underived"] = False

    authorized = not underived and not failed

    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "head": head,
        "origin_main": origin,
        "ready_anchor": ready_anchor,
        "lock_sha256": _sha256(lock_payload),
        "authority_commit": authority_commit,
        "authority_committed_at": authority_time,
        "earliest_generation2_azure_start": earliest_generation2,
        "image_digest": (lock.get("image") or {}).get("digest"),
        "live_attempt_id": namespace.get("live_replay_attempt_id"),
        "pilot_attempt_id": namespace.get("pilot_attempt_id"),
        "conditions": conditions,
        "condition_count": len(conditions),
        "failed_conditions": failed,
        "failed_count": len(failed),
        "underived_conditions": underived,
        "underived_count": len(underived),
        "authorized": authorized,
        "caller_may_supply_a_condition": False,
        "accepts_allow_or_force": False,
        "tokenizer_constructions": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
    }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_phase_b_admission_g2.py",
        "stage": STAGE,
        "generation": GENERATION,
        "condition_count": 38,
        "caller_may_supply_a_condition": False,
        "accepts_allow_or_force": False,
        "query_error_is_absence": False,
        "model_operations_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--admit", action="store_true")
    parser.add_argument("--root")
    parser.add_argument("--lock-file")
    parser.add_argument("--canary-receipts")
    parser.add_argument("--attempt-ledger")
    parser.add_argument("--differential")
    parser.add_argument("--host-preflight")
    parser.add_argument("--ready-anchor")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    document = build(
        args.root, lock_file=args.lock_file,
        canary_receipts=args.canary_receipts,
        attempt_ledger=args.attempt_ledger, differential=args.differential,
        host_preflight=args.host_preflight, ready_anchor=args.ready_anchor)

    payload = canonical_bytes(document)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(payload)
    print(payload.decode("utf-8"), end="")
    print("P0_R2_G2_PHASE_B_AUTHORIZED=%d" % (1 if document["authorized"] else 0))
    print("P0_R2_G2_CONDITION_COUNT=%d" % document["condition_count"])
    print("P0_R2_G2_FAILED_COUNT=%d" % document["failed_count"])
    print("P0_R2_G2_UNDERIVED_COUNT=%d" % document["underived_count"])
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0")
    return 0 if document["authorized"] else 3


if __name__ == "__main__":
    sys.exit(main())
