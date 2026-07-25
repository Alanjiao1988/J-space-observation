#!/usr/bin/env python3
"""Emit the Track D artifact pack for the parser-v3-v1 seal gate.

Pack schema is the existing one and is not extended: ``00_stage_manifest.json``
through ``08_deviations.json`` plus ``artifact_manifest.json``, which is always
written last.  Files that do not apply to this stage are still emitted, and are
marked ``status = "not_applicable"`` with a ``reason`` in the manifest.

Allowed final states, and nothing else:

* ``SEALED``                   the cross-check passed and all twelve objects sealed
* ``BLOCKED_COLLISION``        the cross-check found at least one collision
* ``BLOCKED_INFRASTRUCTURE``   the cross-check could not be executed, or a guard
                               or transport fault stopped the run

Run without ``--job-summary`` to record the pre-execution state honestly: the
cross-check is ``NOT PERFORMED`` and the state is ``BLOCKED_INFRASTRUCTURE``.
After the Container Apps job finishes, rebuild the pack under a new run id from
the two durable Blob artifacts:

    --crosscheck-report <crosscheck_report.json> --seal-record <seal_record.json>

That path is preferred over ``--job-summary`` because the in-container summary is
ephemeral, whereas those two objects are the sealed evidence.  Facts that are not
recoverable from them, such as execution ids and teardown measurements, are read
from an operator-attested ``--execution-record`` and are labelled as attestation
rather than as Track D measurement.  A NOT PERFORMED cross-check is never
rendered as a pass.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _datetime
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from parser_v3_seal_job import (  # noqa: E402
    RETIRED_INPUTS_PREFIX,
    SEAL_OBJECTS,
    SEAL_ROOT,
    canonical_json_bytes,
    sha256_bytes,
)

TRACK_DIRECTORY = "track-d1"
PACK_ROOT = PROJECT_ROOT / "artifacts" / "phase1-evaluator-validation" / TRACK_DIRECTORY
PHASE = "phase-1.2C"
TRACK = "D"

ALLOWED_STATES = ("SEALED", "BLOCKED_COLLISION", "BLOCKED_INFRASTRUCTURE")

WRITE_ORDER = (
    "00_stage_manifest.json",
    "01_protocol_snapshot.json",
    "02_records.jsonl",
    "03_metrics.csv",
    "04_decision.json",
    "05_summary.md",
    "06_paper_table.csv",
    "07_figure_data.csv",
    "08_deviations.json",
)
MANIFEST_NAME = "artifact_manifest.json"

METRICS_HEADER = (
    "run_id,phase,track,metric,stratum,condition,n,numerator,denominator,"
    "value,ci_lower,ci_upper,threshold,passed,not_applicable_reason"
)
METRICS_COLUMNS = METRICS_HEADER.split(",")
PAPER_TABLE_HEADER = "table_id,row_label,measure,value,denominator,note"
FIGURE_HEADER = "figure_id,series,stratum,measure,value,note"

PROHIBITED_INTERPRETATIONS = (
    "NO PARSER-V3 EVALUATION WAS RUN IN THIS ROUND AND NO PARSER-V3 RESULT EXISTS.",
    "Sealing a holdout does not validate parser v3; it fixes the instrument in time.",
    "Do not read any number in this pack as a parser-v3 accuracy, precision, "
    "recall or error rate.",
    "Do not treat the labels as human ground truth; they are a two-reviewer plus "
    "arbiter LLM operational consensus.",
    "Do not treat zero overlap as unconditional; it holds only against the corpora "
    "actually compared.",
    "Do not describe the isolation as a security or RBAC boundary; it is procedural.",
    "A NOT PERFORMED cross-check is not a passed cross-check.",
)


def utc_now() -> str:
    return (
        _datetime.datetime.now(_datetime.timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )


def head_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "unknown"
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else "unknown"


def csv_bytes(header: str, rows: Sequence[Sequence[Any]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header.split(","))
    for row in rows:
        writer.writerow(["" if value is None else value for value in row])
    return buffer.getvalue().encode("utf-8")


def jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return (
        "\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for row in rows
        )
        + "\n"
    ).encode("utf-8")


def resolve_state(summary: Mapping[str, Any] | None) -> tuple[str, str]:
    """Map a job summary onto exactly one allowed Track D final state."""
    if summary is None:
        return (
            "BLOCKED_INFRASTRUCTURE",
            "the pre-seal cross-check has not been executed; no job summary exists",
        )
    state = str(summary.get("state", "")).upper()
    if state == "SEALED":
        return "SEALED", "the cross-check passed and all twelve objects sealed"
    if state == "BLOCKED_COLLISION":
        return (
            "BLOCKED_COLLISION",
            "the cross-check found at least one fingerprint collision, so the set "
            "was not sealed",
        )
    if state == "CROSSCHECK_PASS":
        return (
            "BLOCKED_INFRASTRUCTURE",
            "the cross-check passed but the seal was not executed in the same run",
        )
    return (
        "BLOCKED_INFRASTRUCTURE",
        f"the run stopped before a scientific outcome (job state {state or 'ABSENT'})",
    )


class EvidenceMismatch(RuntimeError):
    """The durable evidence does not agree with itself or with the staged bytes."""


def summary_from_evidence(
    crosscheck_report: Path | str, seal_record: Path | str | None = None
) -> dict[str, Any]:
    """Rebuild the ephemeral job summary from the two durable Blob artifacts.

    Nothing is invented: every field is copied from the objects that were
    actually written to immutable storage.  Three bindings are re-checked here,
    because a pack built from evidence is only as good as the evidence's own
    consistency:

    1. the seal record's pinned digest of the cross-check report must equal the
       measured digest of the report file on disk,
    2. the verdict and the three collision counts must agree between the two
       objects,
    3. every sealed object's digest, byte count and order must equal the
       registered staging pin in ``SEAL_OBJECTS``.

    Any disagreement raises rather than degrading quietly, because a pack that
    silently disagrees with the seal is worse than no pack.
    """
    report_path = Path(crosscheck_report)
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes.decode("utf-8"))
    evidence = [
        {
            "artifact": "crosscheck_report.json",
            "sha256": sha256_bytes(report_bytes),
            "bytes": len(report_bytes),
            "blob_class": "runlog sidecar",
        }
    ]
    summary: dict[str, Any] = {"crosscheck": report, "seal": None}
    if seal_record is None:
        verdict = str(report.get("cross_check", "NOT PERFORMED"))
        summary["state"] = {"PASS": "CROSSCHECK_PASS", "FAIL": "BLOCKED_COLLISION"}.get(
            verdict, "BLOCKED_INFRASTRUCTURE"
        )
        summary["evidence"] = evidence
        return summary

    record_path = Path(seal_record)
    record_bytes = record_path.read_bytes()
    record = json.loads(record_bytes.decode("utf-8"))
    evidence.append(
        {
            "artifact": "seal_record.json",
            "sha256": sha256_bytes(record_bytes),
            "bytes": len(record_bytes),
            "blob_class": "runlog sidecar",
        }
    )

    pinned = record.get("crosscheck_report_sha256")
    if pinned and pinned != evidence[0]["sha256"]:
        raise EvidenceMismatch(
            "the seal record pins a different cross-check report: "
            f"{pinned} != {evidence[0]['sha256']}"
        )
    linked = record.get("crosscheck") or {}
    if str(linked.get("verdict", "")) != str(report.get("cross_check", "")):
        raise EvidenceMismatch("verdict disagrees between the seal record and the report")
    for field in (
        "exact_collision_count",
        "normalised_collision_count",
        "numeric_normalised_collision_count",
    ):
        if linked.get(field) != report.get(field):
            raise EvidenceMismatch(f"{field} disagrees between the two evidence objects")

    status = str(record.get("status") or "").upper()
    if status == "SEALED":
        objects = record.get("objects") or []
        if len(objects) != len(SEAL_OBJECTS):
            raise EvidenceMismatch(
                f"the seal record lists {len(objects)} objects, not {len(SEAL_OBJECTS)}"
            )
        membership = record.get("membership_check") or {}
        if not membership.get("exact_match") or membership.get("observed") != len(
            SEAL_OBJECTS
        ):
            raise EvidenceMismatch("the seal record does not report exact membership")
        if record.get("overwrite") is not False:
            raise EvidenceMismatch("the seal record does not report overwrite=false")
        expected_last = f"{SEAL_OBJECTS[-1]['leaf']}/{SEAL_OBJECTS[-1]['name']}"
        if not str(record.get("written_last", "")).endswith(expected_last):
            raise EvidenceMismatch(f"the closure record is not {expected_last}")
        by_order = {int(row["order"]): row for row in objects}
        for item in SEAL_OBJECTS:
            row = by_order.get(int(item["order"]))
            leaf = f"{item['leaf']}/{item['name']}"
            if row is None or not str(row.get("blob_name", "")).endswith("/" + leaf):
                raise EvidenceMismatch(f"order {item['order']} is not {leaf}")
            if row.get("sha256") != item["sha256"] or int(row.get("bytes", -1)) != int(
                item["bytes"]
            ):
                raise EvidenceMismatch(
                    f"the sealed bytes of {leaf} differ from the staged bytes"
                )
            if not row.get("roundtrip_verified"):
                raise EvidenceMismatch(f"{leaf} was not round-trip verified")

    summary["seal"] = record
    summary["state"] = status or "BLOCKED_INFRASTRUCTURE"
    summary["evidence"] = evidence
    return summary


def crosscheck_view(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    """Never renders an absent or aborted cross-check as a pass."""
    if summary is None:
        return {
            "verdict": "NOT PERFORMED",
            "executed": False,
            "new_count": 120,
            "retired_count": None,
            "exact_collision_count": None,
            "normalised_collision_count": None,
            "numeric_normalised_collision_count": None,
            "reason": (
                "the check was moved off the orchestrator VM, whose Run Command "
                "extension wedged last round, onto a Container Apps job that has "
                "not been executed yet; the VM has since been repaired but the "
                "Container Apps job remains the authoritative path and the check "
                "is performed only when that job runs"
            ),
        }
    report = summary.get("crosscheck") or {}
    verdict = str(report.get("cross_check", "NOT PERFORMED"))
    return {
        "verdict": verdict,
        "executed": verdict in {"PASS", "FAIL", "ABORT"},
        "new_count": report.get("new_count"),
        "retired_count": report.get("retired_count"),
        "exact_collision_count": report.get("exact_collision_count"),
        "normalised_collision_count": report.get("normalised_collision_count"),
        "numeric_normalised_collision_count": report.get(
            "numeric_normalised_collision_count"
        ),
        "reason": "; ".join(report.get("abort_reasons") or []) or None,
    }


def stage_manifest(
    run_id: str,
    generated_at: str,
    state: str,
    state_reason: str,
    check: Mapping[str, Any],
    summary: Mapping[str, Any] | None,
    commit: str,
    protocol_hash: str,
    execution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    seal = (summary or {}).get("seal") or {}
    job = (execution or {}).get("job") or {}
    image = (execution or {}).get("image") or {}
    return {
        "schema_version": "jspace-stage-manifest/v1",
        "run_id": run_id,
        "phase": PHASE,
        "track": TRACK,
        "track_directory": TRACK_DIRECTORY,
        "code_commit": commit,
        "protocol_hash": protocol_hash,
        "subagents": [
            {
                "name": "holdout-sealing-opus5",
                "role": "authored the container job payload, the Azure job "
                "specification, the artifact pack and the targeted tests; executed "
                "no Azure command and no git write",
            }
        ],
        "start_time_utc": generated_at,
        "end_time_utc": generated_at,
        "time_basis": (
            "pack generation time; the job's own start and finish times are carried "
            "in the cross-check report and the seal record"
        ),
        "model_id": "claude-opus-5",
        "model_revision": "not-reported-by-provider",
        "objective": (
            "Execute the outstanding registered pre-seal overlap cross-check against "
            "the retired parser-v2-v1 locked inputs, and seal the parser-v3-v1 "
            "holdout to immutable Blob storage if and only if that cross-check passes."
        ),
        "hypothesis": (
            "The new 120-case parser-v3-v1 holdout shares no output text with the "
            "retired parser-v2-v1 locked inputs under the registered exact, "
            "normalised and numeric-normalised fingerprints. This is an instrument "
            "property, not a parser-v3 result."
        ),
        "scope": [
            "authoring the container job payload for the cross-check and the seal",
            "authoring the Azure Container Apps job specification and the minimum "
            "prefix-conditioned ABAC grants",
            "authoring the staging path for an out-of-tree build context",
            "recording the decision rule and the current state honestly",
        ],
        "out_of_scope": [
            "running any parser-v3 evaluation or producing any parser-v3 prediction",
            "scoring anything",
            "modifying any parser or any parser-v3 fixture, decision rule or protocol",
            "re-running, re-scoring or re-opening the retired parser-v2 holdout",
            "reading parser-v2 locked labels, parser-v2 scores or the parser-v2 "
            "scoring ledger",
            "committing locked inputs or locked labels to GitHub",
            "executing any Azure command or any git write from this track",
        ],
        "hardware": {
            "execution": (
                "Azure Container Apps Consumption job, 2 CPU / 4Gi"
                if seal
                else "local workstation authoring only"
            ),
            "accelerator": "none",
            "workload_profile": job.get("workload_profile", "Consumption"),
            "environment": job.get("environment", "cae-jspace-observation-sea-vnet2"),
            "environment_workload_profiles": ["Consumption", "gpu-t4"],
            "gpu_contention": "none; the single gpu-t4 profile is occupied by "
            "another track and this job does not request it",
            "azure_used": bool(seal),
            "os": "Windows_NT",
        },
        "image_digest": (
            {
                "digest": image["digest"],
                "base_image": image.get("base_image"),
                "staged_dockerfile_sha256": image.get("staged_dockerfile_sha256"),
                "attested_by": "main agent execution record; Track D holds no Azure "
                "access and did not re-measure it",
            }
            if image.get("digest")
            else {
                "status": "not_applicable",
                "reason": (
                    "the temporary single-use image is built by the main agent; its "
                    "digest belongs in the main agent's execution record"
                ),
            }
        ),
        "inputs": [
            {
                "path": "evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json",
                "role": "the new set's fingerprints; the only carrier of its identity",
                "records": 120,
                "sha256": (
                    "ec954093648cb68ce8e6a83db07639bf7de426cc14e35c0a4503b0a6d75ede9d"
                ),
            },
            {
                "path": "scripts/build_parser_v3_validation_set.py",
                "role": "registered fingerprint functions, reused not reimplemented",
            },
            {
                "blob_prefix": RETIRED_INPUTS_PREFIX,
                "role": "retired parser-v2 locked INPUTS, read for overlap diagnosis "
                "only; labels, scores and the scoring ledger are never touched",
                "read_leaves": ["locked_inputs.jsonl"],
            },
        ],
        "output_files": list(WRITE_ORDER) + [MANIFEST_NAME],
        "cross_check": dict(check),
        "evidence_sources": (summary or {}).get("evidence")
        or [
            {
                "status": "not_applicable",
                "reason": "no durable Blob evidence exists before the job runs",
            }
        ],
        "execution": (
            {
                "job_name": job.get("name"),
                "seal_timestamp": (execution or {}).get("timestamps", {}).get(
                    "resolved"
                ),
                "executions": [
                    {
                        "id": row.get("id"),
                        "mode": row.get("mode"),
                        "result": row.get("result"),
                    }
                    for row in (execution or {}).get("executions", [])
                ],
                "attested_by": "main agent execution record; Track D holds no Azure "
                "access and did not re-measure any of it",
            }
            if execution
            else {
                "status": "not_applicable",
                "reason": "the job had not been executed when this pack was emitted",
            }
        ),
        "status": state,
        "status_reason": state_reason,
    }


def protocol_snapshot(run_id: str, commit: str) -> dict[str, Any]:
    body = {
        "schema_version": "jspace-protocol-snapshot/v1",
        "run_id": run_id,
        "phase": PHASE,
        "track": TRACK,
        "code_commit": commit,
        "registered_in": [
            "docs/phase1_parser_v3_sealing_run.md sections 1 to 9",
            "docs/phase1_parser_v3_seal_job_spec.md",
        ],
        "conditions": [
            {
                "id": "preseal_crosscheck_1",
                "description": "new parser-v3-v1 fingerprints against the retired "
                "parser-v2-v1 locked inputs",
            },
            {
                "id": "seal",
                "description": "twelve registered objects to an append-only prefix, "
                "set manifest written last",
            },
        ],
        "decision_rules": [
            "the cross-check must reuse the registered fingerprint functions; a "
            "divergent normaliser invalidates the result and the job must refuse to run",
            "cross_check = PASS if and only if exact, normalised and "
            "numeric-normalised collision counts are all zero",
            "any collision greater than zero is FAIL: do not seal, do not swap cases "
            "this round, do not run any evaluation, and record the conflicting hashes",
            "a guard, provenance or transport fault is ABORT, which is neither PASS "
            "nor FAIL and never licenses a seal",
            "the seal proceeds only on PASS",
            "every seal write uses overwrite=false; a conflict is a hard failure",
            "exact twelve-object membership and per-object round-trip SHA-256 and "
            "ETag verification must both pass",
            "manifests/set_manifest.json is the last write of the entire operation",
            "cross-check 3 against the 18-record historical audit extract is VACUOUS "
            "because that extract has no output-bearing field, and is never reported "
            "as passed",
        ],
        "exclusion_rules": [
            "no blob outside the retired locked-inputs prefix may be listed or read",
            "no retired record may carry a field outside the frozen label-free "
            "parser-v2 locked-input key set",
            "no retired input body text may be emitted, logged or returned",
            "no account key and no SAS may be created, referenced or logged",
        ],
        "registered_constants": {
            "retired_inputs_prefix": RETIRED_INPUTS_PREFIX,
            "retired_inputs_leaf_read": "locked_inputs.jsonl",
            "seal_root": SEAL_ROOT,
            "seal_object_count": len(SEAL_OBJECTS),
            "seal_write_order": [
                f"{item['leaf']}/{item['name']}" for item in SEAL_OBJECTS
            ],
            "fingerprint_fields": [
                "exact_sha256",
                "normalized_sha256",
                "numeric_normalized_sha256",
            ],
        },
        "prohibited_interpretations": list(PROHIBITED_INTERPRETATIONS),
    }
    body["protocol_hash"] = sha256_bytes(
        canonical_json_bytes(
            {
                "decision_rules": body["decision_rules"],
                "exclusion_rules": body["exclusion_rules"],
                "registered_constants": body["registered_constants"],
            }
        )
    )
    return body


def records(
    run_id: str, check: Mapping[str, Any], summary: Mapping[str, Any] | None
) -> list[dict[str, Any]]:
    seal = (summary or {}).get("seal") or {}
    sealed = {row["blob_name"]: row for row in seal.get("objects", [])}
    rows: list[dict[str, Any]] = []
    for item in SEAL_OBJECTS:
        blob_leaf = f"{item['leaf']}/{item['name']}"
        landed = next(
            (row for name, row in sealed.items() if name.endswith("/" + blob_leaf)),
            None,
        )
        rows.append(
            {
                "record_id": f"{run_id}:seal-object-{int(item['order']):02d}",
                "run_id": run_id,
                "phase": PHASE,
                "track": TRACK,
                "condition": "seal",
                "source_item_id": blob_leaf,
                "input_hash": item["sha256"],
                "output_hash": (landed or {}).get("etag") or None,
                "status": "sealed" if landed else "staged_not_sealed",
                "evaluation": {
                    "order": int(item["order"]),
                    "bytes": int(item["bytes"]),
                    "content_class": item["content_class"],
                    "written_last": int(item["order"]) == len(SEAL_OBJECTS),
                    "roundtrip_verified": bool((landed or {}).get("roundtrip_verified")),
                    "content_disclosure": "digests only; no case text, no label values",
                },
            }
        )
    rows.append(
        {
            "record_id": f"{run_id}:crosscheck-1",
            "run_id": run_id,
            "phase": PHASE,
            "track": TRACK,
            "condition": "preseal_crosscheck_1",
            "source_item_id": RETIRED_INPUTS_PREFIX,
            "input_hash": (
                "ec954093648cb68ce8e6a83db07639bf7de426cc14e35c0a4503b0a6d75ede9d"
            ),
            "output_hash": None,
            "status": "not_performed" if not check["executed"] else check["verdict"].lower(),
            "evaluation": dict(check),
        }
    )
    return rows


def metrics(
    run_id: str, check: Mapping[str, Any], summary: Mapping[str, Any] | None
) -> list[list[Any]]:
    seal = (summary or {}).get("seal") or {}
    sealed_count = len(seal.get("objects", []))
    executed = bool(check["executed"])
    not_run = None if executed else "cross-check NOT PERFORMED, so nothing was measured"

    def verdict_cell(field: str) -> str:
        if not executed:
            return ""
        return "true" if check[field] == 0 else "false"

    rows = [
        [
            run_id, PHASE, TRACK, "seal_objects_registered", "", "seal", 12, 12, 12,
            12, "", "", 12, "true", "",
        ],
        [
            run_id, PHASE, TRACK, "seal_objects_sealed", "", "seal", 12, sealed_count,
            12, sealed_count, "", "", 12, "true" if sealed_count == 12 else "",
            "" if sealed_count == 12 else "the seal was not executed in this round",
        ],
        [
            run_id, PHASE, TRACK, "fingerprint_registration_vectors", "",
            "preseal_crosscheck_1", 5, 5, 5, 5, "", "", 5, "true", "",
        ],
        [
            run_id, PHASE, TRACK, "manifest_reproduction_records", "",
            "preseal_crosscheck_1", 120, 120, 120, 120, "", "", 120, "true", "",
        ],
        [
            run_id, PHASE, TRACK, "exact_collision_count", "", "preseal_crosscheck_1",
            check["retired_count"], check["exact_collision_count"],
            check["retired_count"], check["exact_collision_count"], "", "", 0,
            verdict_cell("exact_collision_count"), not_run,
        ],
        [
            run_id, PHASE, TRACK, "normalised_collision_count", "",
            "preseal_crosscheck_1", check["retired_count"],
            check["normalised_collision_count"], check["retired_count"],
            check["normalised_collision_count"], "", "", 0,
            verdict_cell("normalised_collision_count"), not_run,
        ],
        [
            run_id, PHASE, TRACK, "numeric_normalised_collision_count", "",
            "preseal_crosscheck_1", check["retired_count"],
            check["numeric_normalised_collision_count"], check["retired_count"],
            check["numeric_normalised_collision_count"], "", "", 0,
            verdict_cell("numeric_normalised_collision_count"), not_run,
        ],
        [
            run_id, PHASE, TRACK, "crosscheck_2_adversarial_development_set", "",
            "preseal_crosscheck_2", 65, 0, 65, 0, "", "", 0, "true",
            "already executed by scripts/crosscheck_parser_v3_locked_set.py; zero on "
            "all three fingerprints",
        ],
        [
            run_id, PHASE, TRACK, "crosscheck_2b_parser_v2_development_set", "",
            "preseal_crosscheck_2", 60, 0, 60, 0, "", "", 0, "true",
            "public parser-v2 development set; zero on all three fingerprints",
        ],
        [
            run_id, PHASE, TRACK, "crosscheck_3_historical_audit_extract", "",
            "preseal_crosscheck_3", 18, "", 18, "", "", "", "", "",
            "VACUOUS: the 18-record extract carries no output-bearing field, so it "
            "cannot collide; never report this as passed",
        ],
    ]
    return rows


def decision(
    run_id: str,
    state: str,
    state_reason: str,
    check: Mapping[str, Any],
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    passed: list[str] = [
        "the job reuses the registered fingerprint functions and refuses to run if "
        "they do not reproduce the pinned vectors and the committed manifest",
        "the job can list and read only the retired locked-INPUTS leaf, and only one "
        "blob inside it",
        "no parser was imported, no prediction was produced and nothing was scored",
        "all twelve seal objects verify locally against the Track D build digests",
    ]
    failed: list[str] = []
    not_applicable: list[dict[str, str]] = [
        {
            "criterion": "parser-v3 extraction accuracy against the locked set",
            "reason": "this round is sealing only; running an evaluation is "
            "explicitly forbidden",
        },
        {
            "criterion": "cross-check 3 against the full historical model outputs",
            "reason": "only an 18-record audit extract is reachable and it carries no "
            "output-bearing field, so the check is vacuous, not passed",
        },
    ]
    if check["executed"] and check["verdict"] == "PASS":
        passed.append(
            "cross-check 1: exact, normalised and numeric-normalised collision counts "
            "against the retired parser-v2 locked inputs are all zero"
        )
    elif check["executed"] and check["verdict"] == "FAIL":
        failed.append(
            "cross-check 1: at least one fingerprint collision against the retired "
            "parser-v2 locked inputs"
        )
    else:
        not_applicable.append(
            {
                "criterion": "cross-check 1 against the retired parser-v2 locked inputs",
                "reason": check.get("reason")
                or "the check was not executed in this round",
            }
        )
    if state == "SEALED":
        passed.append(
            "twelve-object exact membership, overwrite=false on every write, "
            "round-trip SHA-256 and ETag verification, set manifest written last"
        )
        failed.append(
            "RBAC-enforced isolation: the sealing identity already held an "
            "unconditioned account-scope Storage Blob Data Contributor assignment, so "
            "the two temporary prefix-conditioned ABAC grants narrowed nothing. "
            "Isolation of the retired parser-v2 label, score and ledger material rests "
            "on the payload code path, the Track D tests and the report's own "
            "attestations, not on RBAC. See deviation D13."
        )
    else:
        not_applicable.append(
            {
                "criterion": "seal completion and Blob object verification",
                "reason": state_reason,
            }
        )
    if state == "SEALED":
        text = (
            "The parser-v3-v1 holdout is sealed. The seal establishes only that a "
            "specific 120-case instrument existed, with specific bytes, at a specific "
            "time, before any parser-v3 result was known."
        )
        next_gate = (
            "Teardown is done and measured: both temporary grants deleted, "
            "container-scope assignments 0, job reset to the base image with "
            "/bin/true, job secrets 0, storage public network access Disabled, "
            "single-use image deleted. One expectation was NOT met and is disclosed "
            "rather than restated as met: subscription-wide blob roles for the sealing "
            "identity are 1, not 0, because of a pre-existing unconditioned "
            "account-scope assignment. Next: update the paper ledgers so EV-0007 is "
            "sealed and CL-06 records holdout sealed = yes while parser-v3 formal "
            "validation stays unsupported, then schedule the one-shot parser-v3 locked "
            "evaluation as a separate, later round."
        )
    elif state == "BLOCKED_COLLISION":
        text = (
            "The new holdout overlaps the retired parser-v2 locked inputs. The set "
            "is not sealed and must not be used. The colliding case ids and hashes "
            "are recorded so the affected cases can be rebuilt in a later round."
        )
        next_gate = (
            "Do not seal, do not swap cases in this round and do not run any "
            "evaluation. Return the offending case ids to the set builder."
        )
    else:
        text = (
            "No scientific outcome was produced. The outstanding cross-check remains "
            "outstanding and the holdout remains unsealed, so no parser-v3 evaluation "
            "may be run and no parser-v3 result may be claimed."
        )
        next_gate = (
            "Apply docs/phase1_parser_v3_seal_job_spec.md: stage the payload "
            "out-of-tree, build the single-use image, create the two "
            "prefix-conditioned grants, run the job once in mode seal, then remove "
            "the grants and verify their removal."
        )
    return {
        "schema_version": "jspace-decision/v1",
        "run_id": run_id,
        "status": state,
        "status_reason": state_reason,
        "cross_check": dict(check),
        "criteria_passed": passed,
        "criteria_failed": failed,
        "criteria_not_applicable": not_applicable,
        "decision": text,
        "next_gate": next_gate,
        "scientific_interpretation": (
            "This track produced a gate, not a measurement. A passing cross-check "
            "shows only that the new instrument does not reuse retired holdout text "
            "under three registered fingerprints; it says nothing about parser-v3 "
            "accuracy. The labels being sealed are an LLM operational consensus, not "
            "human ground truth. Isolation between set construction and parser-v3 "
            "development is procedural and hash-audited, not security-enforced."
        ),
        "deviations": [
            "the cross-check moved from the orchestrator VM to a Container Apps job "
            "after the VM Run Command extension wedged; the VM was later repaired "
            "but the Container Apps job stays the authoritative path",
            "the cross-check report and the seal record are written to a sibling "
            "runlog prefix, not into the sealed prefix, because the sealed prefix has "
            "an exact twelve-object membership rule",
        ],
        "prohibited_interpretations": list(PROHIBITED_INTERPRETATIONS)
        + ["Do not restate a NOT PERFORMED cross-check as a passed cross-check."],
    }


def summary_markdown(
    run_id: str,
    state: str,
    state_reason: str,
    check: Mapping[str, Any],
    summary: Mapping[str, Any] | None,
    commit: str,
) -> bytes:
    seal = (summary or {}).get("seal") or {}
    verdict = check["verdict"]
    counts = (
        f"exact {check['exact_collision_count']}, normalised "
        f"{check['normalised_collision_count']}, numeric-normalised "
        f"{check['numeric_normalised_collision_count']}"
        if check["executed"]
        else "not measured"
    )
    lines = [
        "# Summary",
        "",
        f"Run id: `{run_id}`  ",
        f"Phase: {PHASE}  ",
        f"Track: {TRACK} (`{TRACK_DIRECTORY}`)  ",
        f"Code commit: `{commit}`  ",
        f"Final state: **{state}**",
        "",
        "## Objective",
        "",
        "Execute the one outstanding registered pre-seal cross-check, the new",
        "`parser-v3-v1` locked set against the **retired** `parser-v2-v1` locked",
        "inputs, and seal the holdout if and only if that check passes.",
        "",
        "## Scope",
        "",
        "* the container job payload that performs the cross-check and the gated seal",
        "* the Azure Container Apps job specification and the minimum temporary grants",
        "* the honest record of what was and was not executed",
        "",
        "Out of scope, and not done: any parser-v3 evaluation, any parser-v3",
        "prediction, any scoring, any parser change, any re-opening of the retired",
        "parser-v2 holdout, and any read of parser-v2 labels, scores or the scoring",
        "ledger.",
        "",
        "## Provenance",
        "",
        "* the new set's identity comes from the committed",
        "  `evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json`, which carries",
        "  fingerprints and no case text",
        "* the fingerprint functions are imported from",
        "  `scripts/build_parser_v3_validation_set.py` and are never reimplemented",
        f"* the retired source is `{RETIRED_INPUTS_PREFIX}`, read for diagnosis only",
        "",
        "## Execution",
        "",
    ]
    if seal:
        lines += [
            f"* Container Apps job executed; parent prefix `{seal.get('parent_prefix')}`",
            f"* objects sealed: {len(seal.get('objects', []))}",
            f"* closure record written last: `{seal.get('written_last')}`",
            f"* every write used `overwrite={str(seal.get('overwrite')).lower()}`; "
            f"{seal.get('roundtrip_verification')}",
            "* membership was also verified independently, by listing the sealed",
            "  parent under a separate identity rather than trusting the job's own",
            "  record: 12 objects in the parent, 2 in the sibling runlog",
            "* this pack is built from the two durable Blob artifacts",
            "  `crosscheck_report.json` and `seal_record.json`, not from the",
            "  in-container summary, which was ephemeral and is gone",
        ]
    else:
        lines += [
            "* **The Container Apps job has not been executed.** This pack records the",
            "  authored, verified, not-yet-run state.",
            "* The previous attempt on the orchestrator VM did not complete: the Run",
            "  Command extension wedged. That is a transport fault, not a result. The",
            "  VM has since been repaired, which does not convert that attempt into a",
            "  result and does not change the plan.",
        ]
    lines += [
        "",
        "## Results",
        "",
        f"* cross-check 1 verdict: **{verdict}**",
        f"* collision counts: {counts}",
        f"* new set records: {check['new_count']}",
        f"* retired records compared: {check['retired_count']}",
        "* cross-check 2, the parser-v3 public adversarial development set: 0",
        "  collisions on all three fingerprints, already executed locally",
        "* cross-check 3, the 18-record historical audit extract: **VACUOUS**, that",
        "  extract has no output-bearing field, so it cannot collide and must never",
        "  be reported as passed",
        "",
        "## Decision",
        "",
        f"{state}: {state_reason}",
        "",
        "## Deviations and errors",
        "",
        "* the check moved from the orchestrator VM to a Container Apps job after the",
        "  VM Run Command extension wedged; the VM was later repaired but the",
        "  Container Apps job stays the authoritative path and the VM is a fallback",
        "  transport only",
        "* the cross-check report and the seal record are written to a sibling",
        "  `-runlog` prefix, because the sealed prefix has an exact twelve-object",
        "  membership rule that extra objects would violate",
    ]
    if seal:
        lines += [
            "* the first seal attempt aborted on its own `overwrite=false` guard,",
            "  because the recommended dry pass had already written the cross-check",
            "  report under that timestamp. The guard worked; the timestamp was",
            "  rotated and the seal ran once under the new one",
            "* the rotated timestamp reused the identical image digest by retag, so",
            "  the bytes that sealed the set are the bytes that were reviewed",
            "* **the ABAC grants enforced nothing.** The sealing identity already held",
            "  an unconditioned account-scope blob-write role created sixteen days",
            "  earlier, so the two prefix-conditioned grants did not narrow its",
            "  effective permissions. Isolation of the retired label, score and ledger",
            "  material rests on the payload code path, the Track D tests and the",
            "  report's own attestations, not on RBAC. See deviation D13",
        ]
    lines += [
        "",
        "## Scientific interpretation",
        "",
        "This is a gate, not a measurement. A passing cross-check shows only that the",
        "new instrument does not reuse retired holdout text under three registered",
        "fingerprints. It licenses no claim about parser-v3 accuracy. Sealing fixes",
        "the instrument in time; it does not validate anything.",
        "",
        "## Limitations",
        "",
        "* the sealed labels are an LLM operational consensus, not human ground truth",
        "* zero overlap is proven only against the corpora actually compared",
        "* isolation between set construction and parser-v3 development is procedural",
        "  and hash-audited, not security-enforced, and this round produced a concrete",
        "  instance of that: the temporary ABAC conditions were not the enforcement",
        "  mechanism, the code path and its tests were",
        "* the retired holdout is spent and retired; it was fingerprinted for overlap",
        "  diagnosis only and was neither re-run nor re-scored",
        "* no parser-v3 evaluation was run, no parser-v3 prediction exists, and",
        "  nothing here supports any parser-v3 accuracy claim",
        "",
        "## Paper relevance",
        "",
        "The seal, plus this record, is what would make a later parser-v3 evaluation a",
        "genuine pre-registered holdout evaluation rather than a retrospective one.",
        "Until the seal exists, no such claim is available.",
        "",
        "## Next gate",
        "",
        f"{decision(run_id, state, state_reason, check, summary)['next_gate']}",
        "",
    ]
    return ("\n".join(lines)).encode("utf-8")


def paper_table(check: Mapping[str, Any], state: str) -> list[list[Any]]:
    return [
        [
            "parser_v3_seal_gate", "Cases in the holdout", "count", 120, 120,
            "12 strata x 10",
        ],
        [
            "parser_v3_seal_gate", "Registered seal objects", "count", 12, 12,
            "set manifest written last",
        ],
        [
            "parser_v3_seal_gate", "Cross-check 1 verdict", "state",
            check["verdict"], "", "retired parser-v2 locked inputs",
        ],
        [
            "parser_v3_seal_gate", "Cross-check 1 retired records compared", "count",
            "" if not check["executed"] else check["retired_count"], "",
            "not measured" if not check["executed"] else "retired locked inputs",
        ],
        [
            "parser_v3_seal_gate", "Cross-check 1 exact collisions", "count",
            "" if not check["executed"] else check["exact_collision_count"], "",
            "not measured" if not check["executed"] else "zero required",
        ],
        [
            "parser_v3_seal_gate", "Cross-check 1 normalised collisions", "count",
            "" if not check["executed"] else check["normalised_collision_count"], "",
            "not measured" if not check["executed"] else "zero required",
        ],
        [
            "parser_v3_seal_gate", "Cross-check 1 numeric-normalised collisions",
            "count",
            "" if not check["executed"]
            else check["numeric_normalised_collision_count"], "",
            "not measured" if not check["executed"] else "zero required",
        ],
        [
            "parser_v3_seal_gate", "Cross-check 2 collisions", "count", 0, 65,
            "parser-v3 adversarial development set, executed locally",
        ],
        [
            "parser_v3_seal_gate", "Cross-check 3", "state", "VACUOUS", 18,
            "no output-bearing field in the audit extract",
        ],
        ["parser_v3_seal_gate", "Final state", "state", state, "", "Track D vocabulary"],
    ]


def build_pack(
    run_id: str,
    *,
    generated_at: str | None = None,
    job_summary: Mapping[str, Any] | None = None,
    execution: Mapping[str, Any] | None = None,
    out_root: Path | None = None,
) -> Path:
    generated_at = generated_at or utc_now()
    commit = head_commit()
    state, state_reason = resolve_state(job_summary)
    if state not in ALLOWED_STATES:  # pragma: no cover - defensive
        raise RuntimeError(f"illegal Track D final state: {state}")
    check = crosscheck_view(job_summary)
    root = Path(out_root) if out_root is not None else PACK_ROOT
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    snapshot = protocol_snapshot(run_id, commit)

    payloads: dict[str, bytes] = {
        "00_stage_manifest.json": canonical_json_bytes(
            stage_manifest(
                run_id,
                generated_at,
                state,
                state_reason,
                check,
                job_summary,
                commit,
                snapshot["protocol_hash"],
                execution,
            )
        ),
        "01_protocol_snapshot.json": canonical_json_bytes(snapshot),
        "02_records.jsonl": jsonl_bytes(records(run_id, check, job_summary)),
        "03_metrics.csv": csv_bytes(METRICS_HEADER, metrics(run_id, check, job_summary)),
        "04_decision.json": canonical_json_bytes(
            decision(run_id, state, state_reason, check, job_summary)
        ),
        "05_summary.md": summary_markdown(
            run_id, state, state_reason, check, job_summary, commit
        ),
        "06_paper_table.csv": csv_bytes(PAPER_TABLE_HEADER, paper_table(check, state)),
        "07_figure_data.csv": csv_bytes(FIGURE_HEADER, []),
        "08_deviations.json": canonical_json_bytes(deviations(job_summary)),
    }
    statuses: dict[str, dict[str, str]] = {
        "07_figure_data.csv": {
            "status": "not_applicable",
            "reason": "a sealing gate produces no figure series; the file is emitted "
            "with its registered header and no rows",
        }
    }
    if not check["executed"]:
        statuses["06_paper_table.csv"] = {
            "status": "not_applicable",
            "reason": "no publishable measurement exists until the cross-check runs; "
            "the table records state only",
        }
    for name in WRITE_ORDER:
        (run_dir / name).write_bytes(payloads[name])

    manifest = {
        "schema_version": "jspace-artifact-manifest/v1",
        "run_id": run_id,
        "phase": PHASE,
        "track": TRACK,
        "track_directory": TRACK_DIRECTORY,
        "code_commit": commit,
        "generated_at_utc": generated_at,
        "protocol_hash": json.loads(
            payloads["01_protocol_snapshot.json"].decode("utf-8")
        )["protocol_hash"],
        "status": state,
        "status_reason": state_reason,
        "cross_check": dict(check),
        "evidence_sources": (job_summary or {}).get("evidence")
        or [
            {
                "status": "not_applicable",
                "reason": "no durable Blob evidence exists before the job runs",
            }
        ],
        "seal": (
            {
                "parent_prefix": ((job_summary or {}).get("seal") or {}).get(
                    "parent_prefix"
                ),
                "object_count": ((job_summary or {}).get("seal") or {}).get(
                    "object_count"
                ),
                "written_last": ((job_summary or {}).get("seal") or {}).get(
                    "written_last"
                ),
                "overwrite": ((job_summary or {}).get("seal") or {}).get("overwrite"),
                "roundtrip_verification": (
                    (job_summary or {}).get("seal") or {}
                ).get("roundtrip_verification"),
            }
            if (job_summary or {}).get("seal")
            else {"status": "not_applicable", "reason": "nothing was sealed"}
        ),
        "manifest_written_last": True,
        "write_order": list(WRITE_ORDER) + [MANIFEST_NAME],
        "files": [
            {
                "path": name,
                "bytes": len(payloads[name]),
                "sha256": sha256_bytes(payloads[name]),
                **statuses.get(name, {"status": "ok"}),
            }
            for name in WRITE_ORDER
        ],
        "referenced_artifacts": [
            {
                "path": "scripts/parser_v3_seal_job.py",
                "role": "container job payload: cross-check and gated seal",
                "committed_to_git": True,
            },
            {
                "path": "scripts/stage_parser_v3_seal_payload.py",
                "role": "out-of-tree build context staging",
                "committed_to_git": True,
            },
            {
                "path": "docs/phase1_parser_v3_seal_job_spec.md",
                "role": "Azure job specification and ABAC conditions",
                "committed_to_git": True,
            },
            {
                "path": "evaluator_sets/parser_v3_v1/locked_inputs.jsonl",
                "role": "private holdout inputs",
                "committed_to_git": False,
                "note": "gitignored; sealed, never committed",
            },
            {
                "path": "evaluator_sets/parser_v3_v1/locked_labels.jsonl",
                "role": "private holdout labels",
                "committed_to_git": False,
                "note": "gitignored; must never be committed",
            },
        ],
        "content_disclosure": (
            "this pack contains no case text, no label values, no retired input text "
            "and no per-case stratum; only digests, counts and states"
        ),
    }
    (run_dir / MANIFEST_NAME).write_bytes(canonical_json_bytes(manifest))
    return run_dir


def deviations(job_summary: Mapping[str, Any] | None) -> dict[str, Any]:
    executed_rows: list[dict[str, Any]] = []
    rows = [
        {
            "id": "D6-transport-moved-to-container-apps",
            "description": "The registered pre-seal cross-check was attempted on the "
            "orchestrator VM and did not complete: the Azure Run Command extension "
            "wedged in a Conflict state and did not clear.",
            "detected_by": "roughly 25 minutes of retries, including a trivial echo probe",
            "effect": "the check was recorded as NOT PERFORMED, never as skipped, "
            "inferred or passed",
            "resolution": "the comparison was rebuilt as a short-lived Container Apps "
            "CPU job in the VNet-integrated environment, which also removes the need "
            "for the storage account to be reachable from outside the VNet",
            "later_infrastructure_note": "the VM was subsequently repaired: the root "
            "cause was provisioningState Failed with zero extensions installed, an "
            "az vm update on tags reconciled it to Succeeded, and a Run Command probe "
            "now returns Enable succeeded. The Container Apps job remains the "
            "authoritative path and the VM is a fallback transport only. The repair "
            "does not convert the failed attempt into a performed check.",
        },
        {
            "id": "D7-runlog-prefix-outside-the-seal",
            "description": "The sealed prefix has an exact twelve-object membership "
            "rule, so the cross-check report and the seal record cannot be written "
            "inside it without failing that rule.",
            "detected_by": "docs/phase1_parser_v3_sealing_run.md section 6",
            "effect": "the seal keeps exactly twelve objects; the evidence is still "
            "durable and still inside the same VNet-only account",
            "resolution": "both are written to a sibling prefix "
            "`<parent>-runlog/`, which the write grant covers and the membership "
            "listing does not",
        },
        {
            "id": "D8-public-document-line-endings",
            "description": "Four of the twelve registered objects are stored with CRLF "
            "line endings on the curator's disk, while the sealing specification says "
            "Track D artifacts are written with LF.",
            "detected_by": "byte-level digest verification of all twelve objects",
            "effect": "none on integrity: the recorded Track D digests are the digests "
            "of the exact on-disk bytes, and the seal uploads those exact bytes with "
            "no re-serialisation or newline translation, as section 4 requires",
            "resolution": "the job pins the on-disk digest and byte count of every "
            "object and aborts on any mismatch, so no silent normalisation is possible",
        },
    ]
    executed_rows = [
        {
            "id": "D10-seal-timestamp-rotated-after-an-overwrite-false-abort",
            "description": "The first seal attempt, under timestamp 20260725T155224Z, "
            "aborted. The recommended dry pass in mode crosscheck had already written "
            "crosscheck_report.json to that timestamp's runlog prefix, and seal mode "
            "re-runs the cross-check and re-writes that report, so the upload hit its "
            "own overwrite=false guard with ResourceExistsError.",
            "detected_by": "the job's own overwrite=false guard, execution "
            "job-jspace-parser-v3-seal-0fz4tkj, which failed closed with "
            "state=BLOCKED_INFRASTRUCTURE",
            "effect": "none on integrity, and this is the guard working as designed "
            "rather than a defect: no seal object was written under the aborted "
            "timestamp, and no object was ever overwritten",
            "resolution": "the timestamp was rotated to 20260725T160340Z, the old "
            "write grant was deleted, a fresh write grant was pinned to the new "
            "timestamp, and mode seal was run exactly once and succeeded",
            "specification_update": "running mode crosscheck and then mode seal under "
            "one timestamp is guaranteed to abort; the dry pass must use its own "
            "throwaway timestamp or be skipped when the grants are already trusted",
        },
        {
            "id": "D11-image-retagged-not-rebuilt-for-the-second-timestamp",
            "description": "The rotated timestamp did not trigger a rebuild. The "
            "existing image was imported to the new tag with az acr import.",
            "detected_by": "the main agent's execution record; both tags resolve to "
            "digest sha256:f13220aed82c320150a63868e4519ec8d3d4dae7331ae4d421257f191c7d2388",
            "effect": "strictly positive for provenance: no source changed between the "
            "two attempts, so the bytes that sealed the set are provably the same bytes "
            "that were reviewed and that ran the passing cross-check",
            "resolution": "recorded, with the shared digest, as the binding between the "
            "two executions",
        },
        {
            "id": "D12-shared-identity-instead-of-a-dedicated-one",
            "description": "The seal ran under the shared Container Apps job identity "
            "id-jspace-aca-acrpull-sea, principal 78d4348b-57eb-4fb9-aaa7-99148b303292, "
            "not under a dedicated single-purpose managed identity as the round "
            "specification asked.",
            "detected_by": "the main agent's teardown measurement",
            "effect": "the sealing principal is not separable from other Container Apps "
            "workloads, so per-identity audit cannot attribute blob activity to this "
            "seal alone",
            "resolution": "recorded, not repaired: see D13, which is the consequence "
            "that actually matters",
        },
        {
            "id": "D13-standing-unconditioned-role-meant-abac-enforced-nothing",
            "description": "The sealing identity already held an unconditioned Storage "
            "Blob Data Contributor assignment at ACCOUNT scope, created 2026-07-09, "
            "sixteen days before this round. The two temporary prefix-conditioned ABAC "
            "grants created for this run therefore did not narrow its effective "
            "permissions at all.",
            "detected_by": "the main agent's post-run teardown query: subscription-wide "
            "blob roles for the sealing identity returned 1, not the 0 the "
            "specification expected, and the surviving assignment carries no condition",
            "effect": "material and must not be softened. The two ABAC conditions were "
            "defence in depth on paper and enforced nothing in practice. Isolation of "
            "the retired parser-v2 labels, scores and scoring ledger therefore rests "
            "entirely on the payload's code path, on the Track D tests that pin that "
            "code path, and on the cross-check report's own attestations "
            "label_material_touched=false and score_material_touched=false. It does "
            "not rest on RBAC. This is a concrete, evidenced instance of the project's "
            "standing caveat that isolation is procedural, not security-enforced, and "
            "it should be cited as that instance rather than left abstract.",
            "resolution": "not removed, and deliberately so: the assignment pre-dates "
            "this round and other Container Apps jobs depend on it to write results, so "
            "removing it was out of scope and would have broken unrelated "
            "infrastructure. The teardown expectation in "
            "docs/phase1_parser_v3_seal_job_spec.md section 9 was corrected to require "
            "recording the actual value and disclosing a non-zero result as a "
            "limitation, rather than presenting 0 as a pass condition to be met.",
            "residual_risk": "any future round that wants RBAC-enforced isolation must "
            "run under a dedicated identity that holds no standing account-scope blob "
            "role, and must verify that before granting, not after running",
        },
    ]
    if job_summary is None:
        rows.append(
            {
                "id": "D9-not-executed-in-this-round",
                "description": "This track has no Azure access and no git write access, "
                "so it authored and verified the job but could not run it.",
                "detected_by": "round constraints",
                "effect": "the cross-check remains outstanding and the holdout remains "
                "unsealed; no parser-v3 evaluation may be run",
                "resolution": "the main agent executes "
                "docs/phase1_parser_v3_seal_job_spec.md and re-emits this pack with "
                "--job-summary",
            }
        )
    else:
        rows.extend(executed_rows)
    return {
        "deviations": rows,
        "unregistered_changes": [],
        "effect_on_interpretation": (
            "none on any scientific claim: the transport changed, the evidence "
            "location for the report changed, the seal timestamp rotated after a "
            "guard fired, and the digest discipline tightened. No decision rule, no "
            "fixture, no parser and no gate was altered or waived. The one deviation "
            "with real interpretive weight is D13: the prefix-conditioned ABAC grants "
            "did not narrow anything, so the isolation of the retired parser-v2 label "
            "and score material is procedural and test-enforced, not RBAC-enforced. "
            "That weakens the security argument for isolation; it does not weaken the "
            "integrity argument for the seal, which rests on digests."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--generated-at", default=None)
    parser.add_argument(
        "--job-summary",
        default=None,
        help="JSON written by parser_v3_seal_job.py --out; omit before execution",
    )
    parser.add_argument(
        "--crosscheck-report",
        default=None,
        help="the durable runlog crosscheck_report.json; preferred over --job-summary",
    )
    parser.add_argument(
        "--seal-record",
        default=None,
        help="the durable runlog seal_record.json; requires --crosscheck-report",
    )
    parser.add_argument(
        "--execution-record",
        default=None,
        help="operator-attested execution and teardown facts that the durable Blob "
        "artifacts do not carry, e.g. "
        "docs/phase1_parser_v3_seal_execution_record.json",
    )
    parser.add_argument("--out-root", default=None)
    args = parser.parse_args(argv)
    if args.seal_record and not args.crosscheck_report:
        parser.error("--seal-record requires --crosscheck-report")
    if args.crosscheck_report and args.job_summary:
        parser.error("use either --crosscheck-report or --job-summary, not both")
    stamp = _datetime.datetime.now(_datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"{stamp}-track-d1-parser-v3-seal"
    if args.crosscheck_report:
        summary = summary_from_evidence(args.crosscheck_report, args.seal_record)
    elif args.job_summary:
        summary = json.loads(Path(args.job_summary).read_text(encoding="utf-8"))
    else:
        summary = None
    execution = (
        json.loads(Path(args.execution_record).read_text(encoding="utf-8"))
        if args.execution_record
        else None
    )
    run_dir = build_pack(
        run_id,
        generated_at=args.generated_at,
        job_summary=summary,
        execution=execution,
        out_root=Path(args.out_root) if args.out_root else None,
    )
    manifest = json.loads((run_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    print(f"{manifest['status']} {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
