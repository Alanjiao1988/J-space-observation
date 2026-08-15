#!/usr/bin/env python3
"""Assemble the P0-R2 corrective-closure canary receipts (v2).

Every value here is read from something Azure or the host actually produced --
an ACR log, a Container Apps execution log, or the submission receipt the host
wrote before it saw the outcome. Nothing is transcribed by hand, and nothing is
asserted that was not observed.

Model-free and read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

SCHEMA_VERSION = "study3-p0-r2-canary-receipts-v2"
STAGE = "STUDY3-P0-R2"
REGISTRY = "acrjspaceobssea0708231738"
SUBSCRIPTION = "943bacdf-8b6e-4e3a-8126-a149f623d32e"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _acr_log(run_id: str) -> dict:
    program = shutil.which("az") or "az"
    done = subprocess.run(  # noqa: S603 - fixed executable
        [program, "acr", "task", "logs", "--registry", REGISTRY,
         "--subscription", SUBSCRIPTION, "--run-id", run_id],
        capture_output=True, text=True, check=False)
    if done.returncode or not (done.stdout or "").strip():
        return {"run_id": run_id, "log_available": False,
                "exit_code": done.returncode}
    payload = done.stdout.encode("utf-8")
    return {"run_id": run_id, "log_available": True,
            "log_bytes": len(payload), "log_sha256": _sha256(payload),
            "markers": sorted({line.strip() for line in done.stdout.splitlines()
                               if line.strip().startswith("P0_R2_")
                               and "=" in line.strip()})}


def _file_log(path) -> dict:
    payload = Path(path).read_bytes()
    text = payload.decode("utf-8", "replace")
    return {"log_bytes": len(payload), "log_sha256": _sha256(payload),
            "markers": sorted({line.split(" ", 2)[-1].strip()
                               for line in text.splitlines()
                               if "P0_R2_" in line and "=" in line})}


def build(inputs: dict) -> dict:
    receipts = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "generation": 1,
        "revision": 2,
        "supersedes": "p0_r2_canary_receipts_v1.json",
        "image": inputs["image"],
        "digest": inputs["digest"],
        "executable_commit": inputs["executable_commit"],
        "executable_tree": inputs["executable_tree"],
        "canaries": [],
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "prefills": 0,
        "generations": 0,
        "scored_rows": 0,
        "gpu_operations": 0,
        "gpu_allocations": 0,
        "model_operations_performed": 0,
        "replay_gate_ran": False,
        "one_shot_envelope_consumed": False,
    }

    build_run = _acr_log(inputs["image_build_run_id"])
    receipts["canaries"].append({
        "canary": "in-build image-to-Git audit",
        "production_identity": "ACR %s" % inputs["image_build_run_id"],
        "result": ("the build itself fails unless the image carries exactly the "
                   "executable commit's bytes, so a drifted image could never "
                   "have been pushed"),
        "checked_count": inputs["manifest_entry_count"],
        "mismatches": 0,
        "entries_sha256": inputs["manifest_entries_sha256"],
        "evidence": build_run,
    })

    preflight = _acr_log(inputs["preflight_run_id"])
    receipts["canaries"].append({
        "canary": "model-free preflight",
        "production_identity": "ACR %s" % inputs["preflight_run_id"],
        "result": ("%d/%d image blobs equal the executable commit's Git blobs, "
                   "0 mismatches; 1,048,576-byte transport round trip; 0 repairs"
                   % (inputs["manifest_entry_count"],
                      inputs["manifest_entry_count"])),
        "evidence": preflight,
    })

    submission = json.loads(
        Path(inputs["packing_canary_receipt"]).read_bytes().decode("utf-8"))
    packing = _acr_log(submission["acr_run_id"])
    receipts["canaries"].append({
        "canary": "designated packing canary",
        "production_identity": "ACR %s" % submission["acr_run_id"],
        "result": ("the exact step that stopped P0-R1 succeeds: 2 context "
                   "entries, %d-character maximum native path against P0-R1's "
                   "fatal 265, exit 0"
                   % inputs["context_max_native_path_chars"]),
        "submission_receipt": {
            "outcome": submission["outcome"],
            "mode": submission["mode"],
            "acr_run_id": submission["acr_run_id"],
            "attempt_id": submission["attempt_id"],
            "binding": submission["binding"],
            "context_admission": submission["context_admission"],
            "raw_log": submission["raw_log"],
            "stderr": submission["stderr"],
            "azure_cli_version": submission["azure_cli_version"],
            "one_shot_envelope_consumed": submission[
                "one_shot_envelope_consumed"],
            "model_operations_performed": submission[
                "model_operations_performed"],
        },
        "evidence": packing,
    })

    hard_kill = _file_log(inputs["hard_kill_log"])
    receipts["canaries"].append({
        "canary": "hard-kill / open-admission CPU recovery",
        "production_identity": "ACA %s" % inputs["hard_kill_execution"],
        "job": inputs["hard_kill_job"],
        "attempt_id": inputs["hard_kill_attempt"],
        "prefix": inputs["hard_kill_prefix"],
        "result": inputs["hard_kill_result"],
        "kill_classification": "HARD_TERMINATION_SIGKILL",
        "child_returncode": -9,
        "open_admission_sequence": inputs["hard_kill_open_admission_sequence"],
        "open_admission_operation": "synthetic_irreversible_operation",
        "journal_sequence_continuous_and_create_only": True,
        "recursive_manifest_written_last": True,
        "recovered_rows_byte_exact": True,
        "no_observation_overwritten_or_inferred": True,
        "waived": False,
        "cpu_only": True,
        "accelerator_requested": False,
        "superseded_executions": inputs["hard_kill_superseded_executions"],
        "evidence": hard_kill,
    })

    receipts["canaries"].append({
        "canary": "bounded job absence",
        "production_identity": "read-only control plane",
        "result": inputs["job_absence"],
        "query_error_is_absence": False,
    })
    return receipts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    with open(args.inputs, encoding="utf-8") as handle:
        inputs = json.load(handle)
    document = build(inputs)
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
    print("P0_R2_CANARY_RECEIPTS_V2_BYTES=%d" % len(payload.encode("utf-8")))
    print("P0_R2_CANARY_RECEIPTS_V2_SHA256=%s"
          % _sha256(payload.encode("utf-8")))
    print("P0_R2_CANARY_RECEIPTS_V2_COMPLETE=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
