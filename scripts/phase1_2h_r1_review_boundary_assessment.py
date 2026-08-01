#!/usr/bin/env python3
"""Phase 1.2H-R1 private-review-boundary assessment instrument.

Independent Audit B (B-09) observed that this round's terminal state rested on
prose: the protocol asserted that no qualifying private semantic-review backend
exists, but nothing committed to the repository could be re-executed to check
that claim, and nothing recorded which specific frozen condition failed. A
verdict that cannot be reproduced is an opinion.

This module turns the frozen ``private_review_boundary_requirements`` block of
the decision record into a deterministic function over observed control-plane
facts, and emits a closed, schema-valid receipt.

What it reads
-------------
Only Azure **control-plane** facts, supplied as a committed JSON evidence
bundle: resource types, network posture, private-endpoint counts, egress
configuration. These are infrastructure identifiers and settings. It reads no
sealed object, no private curator file, no prompt, no response, no case, and no
label. It performs no data-plane operation of any kind, and it does not call
Azure at all -- the operator captures the facts with ``az`` and commits them,
so the assessment is reproducible offline by anyone reading the repository.

What it deliberately does not do
--------------------------------
It does not provision anything, it does not decide to build anything, and a
``QUALIFIES`` verdict would not be authorisation to review. It answers exactly
one question: does a backend meeting every frozen condition exist today.

Precedence
----------
Per Audit B (B-09), the two blocked states are ordered rather than overlapping:
if the byte-only access gate fails, the round is blocked on private *source
access*, because the boundary question has not yet been reached. Only once the
gate has passed can the *review boundary* be the thing that blocks. That order
is enforced in :func:`classify_terminal_state` so the more advanced-sounding
state cannot be claimed by a round that never reached the source.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DECISION_RECORD = REPO_ROOT / "docs" / "phase1_2h_r1_access_decision_record.json"
BOUNDARY_SCHEMA = REPO_ROOT / "docs" / "phase1_2h_r1_review_boundary.schema.json"

SCHEMA_VERSION = "phase1-2h-r1-review-boundary/v1"

#: Each frozen condition is mapped to a check over the evidence bundle. A
#: condition with no check is reported as NOT_ASSESSABLE rather than silently
#: passing: an unchecked condition must never look like a satisfied one.
CONDITION_KEYS: tuple[str, ...] = (
    "worker_in_project_vnet_or_approved_private_link_boundary",
    "reviewer_public_network_access_disabled",
    "reviewer_dns_resolves_to_registered_private_endpoint",
    "no_unrestricted_internet_egress_while_holding_private_material",
    "outbound_restricted_to_approved_private_endpoints",
    "no_prompt_or_response_reaches_copilot_actions_or_public_telemetry",
    "raw_prompt_logging_disabled_or_confined_to_boundary",
    "identity_role_and_storage_scopes_least_privilege",
    "r1_and_r2_sessions_isolable",
    "arbiter_receives_only_disagreement_packets",
    "only_aggregates_or_content_free_receipts_leave",
    "public_synthetic_review_packet_completes_end_to_end",
    "boundary_and_synthetic_execution_independently_audited",
)

VERDICTS = ("PASS", "FAIL", "NOT_ASSESSABLE")


class BoundaryAssessmentError(Exception):
    """The evidence bundle or the frozen record is not usable as stated."""


def load_conditions(record_path: Path = DECISION_RECORD) -> list[str]:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    conditions = record["private_review_boundary_requirements"]["conditions"]
    if len(conditions) != len(CONDITION_KEYS):
        raise BoundaryAssessmentError(
            "the frozen condition list and the assessment key list have "
            f"diverged: {len(conditions)} frozen conditions, "
            f"{len(CONDITION_KEYS)} assessment keys. A condition that is not "
            "assessed must not be able to disappear silently."
        )
    return list(conditions)


def _reviewer_accounts(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    return list(evidence.get("candidate_reviewer_endpoints", []))


def assess(evidence: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Evaluate every frozen condition against the observed facts.

    Returns a mapping of condition key to ``{"verdict", "basis"}``. The basis
    strings name what was observed, never what was hoped.
    """

    candidates = _reviewer_accounts(evidence)
    in_boundary = [
        c
        for c in candidates
        if c.get("public_network_access") == "Disabled"
        and int(c.get("private_endpoint_count", 0)) > 0
        and c.get("network_default_action") == "Deny"
    ]

    results: dict[str, dict[str, str]] = {}

    def record(key: str, verdict: str, basis: str) -> None:
        if verdict not in VERDICTS:  # pragma: no cover - defensive
            raise BoundaryAssessmentError(f"unknown verdict {verdict!r}")
        results[key] = {"verdict": verdict, "basis": basis}

    if not candidates:
        record(
            "worker_in_project_vnet_or_approved_private_link_boundary",
            "FAIL",
            "no candidate semantic-review endpoint of any kind was observed in "
            "the project resource group",
        )
    elif in_boundary:
        record(
            "worker_in_project_vnet_or_approved_private_link_boundary",
            "PASS",
            f"{len(in_boundary)} candidate endpoint(s) observed with private "
            "network posture",
        )
    else:
        record(
            "worker_in_project_vnet_or_approved_private_link_boundary",
            "FAIL",
            f"{len(candidates)} candidate endpoint(s) observed, none inside a "
            "private boundary",
        )

    public_only = [c for c in candidates if c.get("public_network_access") == "Enabled"]
    if not candidates:
        record(
            "reviewer_public_network_access_disabled",
            "FAIL",
            "no reviewer endpoint exists, so the condition cannot be met",
        )
    elif public_only and not in_boundary:
        record(
            "reviewer_public_network_access_disabled",
            "FAIL",
            f"{len(public_only)} candidate endpoint(s) have publicNetworkAccess "
            "Enabled",
        )
    else:
        record(
            "reviewer_public_network_access_disabled",
            "PASS",
            "every candidate endpoint has publicNetworkAccess Disabled",
        )

    with_pe = [c for c in candidates if int(c.get("private_endpoint_count", 0)) > 0]
    record(
        "reviewer_dns_resolves_to_registered_private_endpoint",
        "PASS" if with_pe else "FAIL",
        f"{len(with_pe)} of {len(candidates)} candidate endpoint(s) have at "
        "least one private endpoint",
    )

    egress = evidence.get("worker_egress", {})
    unrestricted = (
        egress.get("route_table") in (None, "", "null")
        and not egress.get("restrictive_nsg_outbound_rules")
    )
    record(
        "no_unrestricted_internet_egress_while_holding_private_material",
        "FAIL" if unrestricted else "PASS",
        "worker subnet has no route table and no restrictive outbound NSG rule, "
        "so the platform default AllowInternetOutBound applies"
        if unrestricted
        else "worker subnet egress is constrained by a route table or NSG rules",
    )
    record(
        "outbound_restricted_to_approved_private_endpoints",
        "FAIL" if unrestricted else "PASS",
        "no egress allowlist is in force" if unrestricted else "egress allowlist in force",
    )

    # The remaining conditions are properties of a review *design* that does
    # not exist. Reporting them as NOT_ASSESSABLE is the honest result: they
    # are neither satisfied nor violated, because there is nothing to assess.
    # They are listed rather than dropped so that a future round cannot mistake
    # silence for satisfaction.
    for key in (
        "no_prompt_or_response_reaches_copilot_actions_or_public_telemetry",
        "raw_prompt_logging_disabled_or_confined_to_boundary",
        "identity_role_and_storage_scopes_least_privilege",
        "r1_and_r2_sessions_isolable",
        "arbiter_receives_only_disagreement_packets",
        "only_aggregates_or_content_free_receipts_leave",
        "public_synthetic_review_packet_completes_end_to_end",
        "boundary_and_synthetic_execution_independently_audited",
    ):
        record(
            key,
            "NOT_ASSESSABLE",
            "no review backend exists, so this property of a review design has "
            "nothing to be assessed against",
        )

    missing = set(CONDITION_KEYS) - set(results)
    if missing:  # pragma: no cover - defensive
        raise BoundaryAssessmentError(f"unassessed conditions: {sorted(missing)}")
    return results


def qualification_verdict(results: dict[str, dict[str, str]]) -> str:
    """QUALIFIES only if every condition PASSES.

    NOT_ASSESSABLE is not a pass. A boundary that cannot be shown to meet a
    condition has not met it.
    """

    if any(r["verdict"] == "FAIL" for r in results.values()):
        return "DOES_NOT_QUALIFY"
    if any(r["verdict"] == "NOT_ASSESSABLE" for r in results.values()):
        return "DOES_NOT_QUALIFY"
    return "QUALIFIES"


def classify_terminal_state(
    byte_only_gate_passed: bool, qualification: str
) -> str:
    """Apply the precedence rule Audit B asked for (B-09)."""

    if not byte_only_gate_passed:
        return "BLOCKED_ON_PRIVATE_SOURCE_ACCESS"
    if qualification != "QUALIFIES":
        return "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY"
    return "READY_FOR_SEPARATELY_AUTHORISED_PRIVATE_REVIEW"


def build_assessment(
    evidence: dict[str, Any],
    *,
    byte_only_gate_passed: bool,
    record_path: Path = DECISION_RECORD,
) -> dict[str, Any]:
    conditions = load_conditions(record_path)
    results = assess(evidence)
    qualification = qualification_verdict(results)
    ordered = [
        {
            "key": key,
            "frozen_condition": conditions[index],
            "verdict": results[key]["verdict"],
            "basis": results[key]["basis"],
        }
        for index, key in enumerate(CONDITION_KEYS)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": "1.2H-R1",
        "observed_at": evidence["observed_at"],
        "evidence_source": evidence["evidence_source"],
        "conditions": ordered,
        "summary": {
            "total": len(ordered),
            "passed": sum(1 for c in ordered if c["verdict"] == "PASS"),
            "failed": sum(1 for c in ordered if c["verdict"] == "FAIL"),
            "not_assessable": sum(1 for c in ordered if c["verdict"] == "NOT_ASSESSABLE"),
        },
        "qualification_verdict": qualification,
        "byte_only_gate_passed": byte_only_gate_passed,
        "terminal_state": classify_terminal_state(byte_only_gate_passed, qualification),
        "access_ledger_effect": {
            "sealed_input_semantic_reads": 0,
            "sealed_label_semantic_reads": 0,
            "private_curator_files_read": 0,
            "predictions_generated": 0,
            "parser_invocations": 0,
            "azure_resource_changes": 0,
        },
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument(
        "--byte-only-gate-passed",
        choices=("true", "false"),
        required=True,
        help="whether the Phase 1.2H-R1 access gate completed all 12 objects",
    )
    parser.add_argument("--check", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    assessment = build_assessment(
        evidence, byte_only_gate_passed=args.byte_only_gate_passed == "true"
    )

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from phase1_2h_r1_receipt_validator import validate_receipt

    validate_receipt(assessment, BOUNDARY_SCHEMA)
    rendered = json.dumps(assessment, indent=2, sort_keys=True) + "\n"

    if args.check is not None:
        committed = args.check.read_text(encoding="utf-8").replace("\r\n", "\n")
        if committed != rendered:
            print(
                "committed assessment differs from the one this evidence "
                "produces; regenerate it",
                file=sys.stderr,
            )
            return 1
        print("committed assessment matches the evidence bundle")
        return 0

    print(rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
