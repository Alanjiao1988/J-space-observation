#!/usr/bin/env python3
"""Compute the canonical Phase-B admission document from evidence (the gate).

This module exists to make one thing impossible: asserting that Segment B is
authorized. Every one of the twenty-eight registered conditions is *derived* --
from Git, from a published receipt, from a read-only Azure answer, or from the
host preflight's own transaction -- and any condition that cannot be derived is
recorded ``false`` with the reason, never ``unknown-so-probably-fine``.

``phase_b_authorized`` is the conjunction of all twenty-eight. There is no
override, no ``--force``, and no way for a caller to supply a condition's value.

It is run from a **fresh** short-path checkout of the new ``origin/main``, after
Segment A has been published, and its own output is published as a
governance-only commit which is then re-proved from another fresh checkout.

Model-free and read-only: it creates, updates, starts and deletes nothing, and
performs no tokenizer, checkpoint, model weight, prefill, generation, scoring,
evidence or GPU operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


P0_R2_DIR = Path(__file__).resolve().parent.parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_azure_query_v1 as AZ  # noqa: E402
import p0_r2_closure_binding_v2 as CB2  # noqa: E402
import p0_r2_host_preflight_v2 as HOST  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-phase-b-admission-v2"
STAGE = "STUDY3-P0-R2"

STOP_DISPOSITION = "P0_R2_CORRECTIVE_CLOSURE_STOP_NO_REPLAY"

#: The twenty-eight registered conditions, in the operator's order.
CONDITION_ORDER = (
    "head_equals_origin_main_at_the_corrected_final_head",
    "worktree_is_clean",
    "corrective_authority_is_published_and_bound",
    "p0_r1_protected_bytes_are_unchanged",
    "p0_r1_remains_terminal_and_nonlaunchable",
    "v1_p0_r2_closure_is_preserved_but_superseded_and_nonlaunchable",
    "the_v2_governance_chain_proves_successfully",
    "no_disallowed_path_changed_after_the_v2_anchor",
    "the_exact_active_lock_schema_image_and_task_all_verify",
    "the_true_host_side_preflight_passes",
    "focused_and_correction_suites_pass",
    "full_differential_suite_has_zero_collection_errors",
    "exactly_the_four_registered_standing_failures_at_baseline_and_head",
    "zero_new_failure_is_introduced",
    "the_hard_kill_open_admission_recovery_canary_passes",
    "the_complete_attempt_ledger_is_published",
    "the_designated_packing_canary_used_the_active_task_and_image",
    "windows_native_path_maximum_is_at_most_240",
    "the_replay_gate_has_never_run",
    "the_replay_envelope_is_unconsumed",
    "canonical_p0_r2_replay_artifacts_are_absent",
    "the_exact_preregistered_live_attempt_id_is_new",
    "its_blob_prefix_is_proved_unused",
    "the_gpu_pilot_job_is_proved_absent",
    "the_cpu_recovery_job_is_proved_absent",
    "all_replay_model_gpu_and_scoring_counters_are_zero",
    "azure_cli_and_log_capture_are_available",
    "no_query_run_id_image_prefix_receipt_or_ancestry_result_is_ambiguous",
)


class AdmissionDefect(Exception):
    """The admission document cannot be computed honestly."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(root, *args, check=True):
    done = subprocess.run(  # noqa: S603 - fixed executable
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        check=False)
    if check and done.returncode:
        raise AdmissionDefect("git %s failed: %s"
                              % (" ".join(args), done.stderr.strip()))
    return done.stdout.strip(), done.returncode


class Gate:
    def __init__(self, root, lock_path):
        self.root = Path(root).resolve()
        self.lock_raw = Path(lock_path).read_bytes()
        self.lock = json.loads(self.lock_raw.decode("utf-8"))
        self.conditions = {}

    def set(self, name, value, evidence):
        if name not in CONDITION_ORDER:
            raise AdmissionDefect("unregistered condition %r" % name)
        self.conditions[name] = {"value": bool(value), "evidence": evidence}

    # -- derivations -------------------------------------------------------
    def derive(self, *, preflight_report, differential, focused,
               hard_kill_receipt, ledger, prefix_receipt, azure_runner=None):
        root = self.root
        lock = self.lock

        _git(root, "fetch", "--quiet", "origin", "main", check=False)
        head, _ = _git(root, "rev-parse", "HEAD")
        published, _ = _git(root, "rev-parse", "origin/main")
        self.set("head_equals_origin_main_at_the_corrected_final_head",
                 head == published, {"head": head, "origin_main": published})

        status, _ = _git(root, "status", "--porcelain")
        self.set("worktree_is_clean", not status.strip(),
                 {"dirty_entries": status.splitlines()[:16]})

        authority = next((entry for entry in (lock.get("authorities") or [])
                          if entry.get("role") == "corrective"), None)
        bound = False
        detail = {"authority": authority}
        if authority:
            try:
                actual = CB2.blob_identity(root, head, authority["path"])
                detail["observed"] = actual
                bound = (actual["sha256"] == authority["sha256"]
                         and actual["bytes"] == authority["bytes"])
            except CB2.ClosureBindingDefect as exc:
                detail["error"] = str(exc)
        self.set("corrective_authority_is_published_and_bound", bound, detail)

        terminal = lock.get("p0_r1_terminal") or {}
        changed, _ = _git(root, "diff", "--name-only", terminal.get("stop_commit"),
                          head, "--", *CB2.PROTECTED_P0_R1_PREFIXES)
        self.set("p0_r1_protected_bytes_are_unchanged", not changed.strip(),
                 {"changed": changed.splitlines()[:16],
                  "stop_commit": terminal.get("stop_commit")})
        self.set("p0_r1_remains_terminal_and_nonlaunchable",
                 terminal.get("state") == "STOP_NO_MODEL_OPERATION"
                 and terminal.get("replay_envelope_consumed") is True
                 and terminal.get("launchable") is False,
                 {"state": terminal.get("state"),
                  "launchable": terminal.get("launchable")})

        supersession = lock.get("v1_supersession") or {}
        preserved = False
        try:
            v1_lock = CB2.blob_identity(root, head, supersession["v1_lock_path"])
            preserved = (v1_lock["sha256"] == supersession["v1_lock_sha256"]
                         and supersession.get("superseded") is True
                         and supersession.get("launchable") is False)
            detail = {"v1_lock": v1_lock, "supersession": supersession}
        except (CB2.ClosureBindingDefect, KeyError) as exc:
            detail = {"error": str(exc)}
        self.set("v1_p0_r2_closure_is_preserved_but_superseded_and_nonlaunchable",
                 preserved, detail)

        anchor = (lock.get("ready_commit_relationship") or {}).get(
            "ready_anchor_commit")
        chain_ok = False
        chain_detail = {}
        try:
            proof = CB2.prove_v2_chain(
                root=root, lock=lock, ready_anchor=anchor,
                governance_commit=head, require_head=True, require_clean=True,
                lock_identity={"path": (lock.get("self") or {}).get("path"),
                               "bytes": len(self.lock_raw),
                               "sha256": _sha256(self.lock_raw)})
            chain_ok = proof["outcome"] == "GOVERNANCE_CHAIN_PROVED"
            chain_detail = {"ancestry": proof["ancestry_proved"],
                            "changed_since_anchor": proof["changed_since_anchor"]}
            self.set("no_disallowed_path_changed_after_the_v2_anchor", True,
                     {"classification": proof["post_anchor_classification"]})
            self.set("the_exact_active_lock_schema_image_and_task_all_verify",
                     bool(proof.get("execution_lock"))
                     and proof["task_object"]["git_blob"]
                     == (lock.get("transport") or {}).get("task_blob")
                     and (proof.get("image") or {}).get("digest")
                     == (lock.get("image") or {}).get("digest"),
                     {"execution_lock": proof.get("execution_lock"),
                      "task_object": proof["task_object"],
                      "image": proof.get("image")})
        except CB2.ClosureBindingDefect as exc:
            chain_detail = {"refusal": str(exc)}
            self.set("no_disallowed_path_changed_after_the_v2_anchor", False,
                     {"reason": "the chain proof refused"})
            self.set("the_exact_active_lock_schema_image_and_task_all_verify",
                     False, {"reason": "the chain proof refused"})
        self.set("the_v2_governance_chain_proves_successfully", chain_ok,
                 chain_detail)

        self.set("the_true_host_side_preflight_passes",
                 (preflight_report or {}).get("outcome")
                 == "HOST_PREFLIGHT_PROVED",
                 {"outcome": (preflight_report or {}).get("outcome"),
                  "refusals": (preflight_report or {}).get("refusals")})

        self.set("focused_and_correction_suites_pass",
                 bool(focused) and focused.get("failed") == 0
                 and focused.get("errors") == 0,
                 focused or {"reason": "no focused-suite receipt was supplied"})

        differential = differential or {}
        self.set("full_differential_suite_has_zero_collection_errors",
                 differential.get("zero_collection_errors") is True,
                 {"baseline": differential.get("baseline_collection_errors"),
                  "corrected": differential.get("corrected_collection_errors")})
        registered = list((lock.get("standing_failures") or {}).get("node_ids")
                          or ())
        self.set(
            "exactly_the_four_registered_standing_failures_at_baseline_and_head",
            differential.get("baseline_non_passing") == registered
            and differential.get("corrected_non_passing") == registered
            and differential.get("signatures_agree") is True,
            {"registered": registered,
             "baseline": differential.get("baseline_non_passing"),
             "corrected": differential.get("corrected_non_passing"),
             "signatures_agree": differential.get("signatures_agree")})
        self.set("zero_new_failure_is_introduced",
                 differential.get("new_failure_count") == 0
                 and differential.get("fixed_failures") == [],
                 {"new_failures": differential.get("new_failures"),
                  "fixed_failures": differential.get("fixed_failures")})

        hard_kill_receipt = hard_kill_receipt or {}
        self.set("the_hard_kill_open_admission_recovery_canary_passes",
                 hard_kill_receipt.get("result", "").startswith("PASS")
                 and hard_kill_receipt.get("waived") is False
                 and hard_kill_receipt.get("recovered_rows_byte_exact") is True
                 and hard_kill_receipt.get(
                     "journal_sequence_continuous_and_create_only") is True
                 and hard_kill_receipt.get(
                     "recursive_manifest_written_last") is True,
                 hard_kill_receipt)

        ledger = ledger or {}
        self.set("the_complete_attempt_ledger_is_published",
                 ledger.get("complete_and_admissible") is True
                 and ledger.get("ambiguous_count") == 0
                 and not ledger.get("stops"),
                 {"run_count": ledger.get("run_count"),
                  "sealed": ledger.get("sealed_count"),
                  "unavailable": ledger.get("unavailable_count"),
                  "ambiguous": ledger.get("ambiguous_count")})

        canary = lock.get("designated_packing_canary") or {}
        image = lock.get("image") or {}
        transport = lock.get("transport") or {}
        self.set("the_designated_packing_canary_used_the_active_task_and_image",
                 canary.get("task_blob") == transport.get("task_blob")
                 and canary.get("digest") == image.get("digest")
                 and canary.get("image") == image.get("reference"),
                 {"canary": canary, "active_task_blob": transport.get(
                     "task_blob"), "active_digest": image.get("digest")})

        native = None
        for entry in ((preflight_report or {}).get("checks") or []):
            if entry["check"] == "native_windows_packer_paths_within_budget":
                native = entry["detail"]
        self.set("windows_native_path_maximum_is_at_most_240",
                 bool(native) and native.get("context_max_native_path_chars",
                                             10 ** 6) <= 240,
                 native or {"reason": "the preflight did not measure a context"})

        envelope = lock.get("replay_envelope") or {}
        self.set("the_replay_gate_has_never_run",
                 envelope.get("consumed") is False
                 and int(envelope.get("invocations", 1)) == 0, envelope)
        self.set("the_replay_envelope_is_unconsumed",
                 envelope.get("consumed") is False, envelope)

        artifacts_present = []
        for entry in ((preflight_report or {}).get("checks") or []):
            if entry["check"] == "canonical_p0_r2_replay_artifacts_absent":
                artifacts_present = entry["detail"].get("found") or []
        self.set("canonical_p0_r2_replay_artifacts_are_absent",
                 not artifacts_present, {"found": artifacts_present})

        attempt = (lock.get("attempt") or {}).get("live_replay_attempt_id")
        prefix_receipt = prefix_receipt or {}
        self.set("the_exact_preregistered_live_attempt_id_is_new",
                 bool(attempt) and prefix_receipt.get("attempt_id") == attempt
                 and prefix_receipt.get("object_count") == 0,
                 {"attempt_id": attempt,
                  "receipt_attempt": prefix_receipt.get("attempt_id")})
        self.set("its_blob_prefix_is_proved_unused",
                 prefix_receipt.get("outcome") == "PROVED_UNUSED"
                 and prefix_receipt.get("object_count") == 0
                 and prefix_receipt.get("wrote_any_object") is False
                 and bool(prefix_receipt.get("execution_identity")),
                 prefix_receipt)

        azure = lock.get("azure") or {}
        ambiguities = []
        for label, job in (("gpu", azure.get("gpu_job")),
                           ("recovery", azure.get("recovery_job"))):
            receipt = AZ.job_presence(
                job, resource_group=azure.get("resource_group"),
                subscription=azure.get("subscription"), runner=azure_runner)
            if receipt.get("outcome") == "AMBIGUOUS":
                ambiguities.append("%s job query" % label)
            self.set("the_%s_job_is_proved_absent"
                     % ("gpu_pilot" if label == "gpu" else "cpu_recovery"),
                     receipt.get("outcome") == "PROVED_ABSENT",
                     {"job": job, "outcome": receipt.get("outcome"),
                      "query_error_is_absence": False})

        counters = lock.get("pre_replay_counters") or {}
        nonzero = {name: value for name, value in counters.items() if value != 0}
        self.set("all_replay_model_gpu_and_scoring_counters_are_zero",
                 bool(counters) and not nonzero,
                 {"counters": counters, "nonzero": nonzero})

        import shutil
        cli = shutil.which("az")
        self.set("azure_cli_and_log_capture_are_available",
                 bool(cli) and bool(ledger.get("sealed_count")),
                 {"az": cli, "sealed_logs": ledger.get("sealed_count")})

        if (ledger.get("ambiguous_count") or 0):
            ambiguities.append("attempt ledger")
        if not chain_ok:
            ambiguities.append("governance chain")
        self.set(
            "no_query_run_id_image_prefix_receipt_or_ancestry_result_is_ambiguous",
            not ambiguities, {"ambiguities": ambiguities})

    # -- assembly ----------------------------------------------------------
    def document(self) -> dict:
        missing = [name for name in CONDITION_ORDER
                   if name not in self.conditions]
        for name in missing:
            self.conditions[name] = {
                "value": False,
                "evidence": {"reason": "the condition was never derived; an "
                                       "underived condition is false, not "
                                       "unknown"}}
        failed = [name for name in CONDITION_ORDER
                  if not self.conditions[name]["value"]]
        authorized = not failed
        return {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase_b_authorized": authorized,
            "condition_count": len(CONDITION_ORDER),
            "conditions": {name: self.conditions[name]
                           for name in CONDITION_ORDER},
            "failed_conditions": failed,
            "failed_condition_count": len(failed),
            "underived_conditions": missing,
            "disposition": (None if authorized else STOP_DISPOSITION),
            "every_field_is_derived_from_evidence": True,
            "caller_may_supply_a_condition_value": False,
            "override_available": False,
            "lock_sha256": _sha256(self.lock_raw),
            "tokenizer_constructions": 0,
            "checkpoint_downloads": 0,
            "model_weight_loads": 0,
            "prefills": 0,
            "generations": 0,
            "scored_rows": 0,
            "gpu_operations": 0,
            "model_operations_performed": 0,
            "created_updated_or_started_anything": False,
        }


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_phase_b_admission_v2.py",
        "stage": STAGE,
        "condition_count": len(CONDITION_ORDER),
        "conditions": list(CONDITION_ORDER),
        "stop_disposition": STOP_DISPOSITION,
        "underived_condition_is_false": True,
        "override_available": False,
        "caller_may_supply_a_condition_value": False,
        "read_only": True,
        "model_operations_performed": 0,
    }


def _maybe(path):
    if not path:
        return None
    return json.loads(Path(path).read_bytes().decode("utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--admit", action="store_true")
    parser.add_argument("--root", default=".")
    parser.add_argument("--lock-file")
    parser.add_argument("--preflight-report")
    parser.add_argument("--differential")
    parser.add_argument("--focused")
    parser.add_argument("--hard-kill-receipt")
    parser.add_argument("--ledger")
    parser.add_argument("--prefix-receipt")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    if not args.lock_file:
        parser.error("--admit requires --lock-file")
    try:
        gate = Gate(args.root, args.lock_file)
        gate.derive(preflight_report=_maybe(args.preflight_report),
                    differential=_maybe(args.differential),
                    focused=_maybe(args.focused),
                    hard_kill_receipt=_maybe(args.hard_kill_receipt),
                    ledger=_maybe(args.ledger),
                    prefix_receipt=_maybe(args.prefix_receipt))
        document = gate.document()
    except (AdmissionDefect, OSError, ValueError) as exc:
        print("P0_R2_PHASE_B_ADMISSION_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    print(payload, end="")
    print("P0_R2_PHASE_B_AUTHORIZED=%s"
          % ("1" if document["phase_b_authorized"] else "0"))
    if not document["phase_b_authorized"]:
        print("P0_R2_DISPOSITION=%s" % STOP_DISPOSITION)
        for name in document["failed_conditions"]:
            print("  failed: %s" % name)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
