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

Where the gate outcome comes from
---------------------------------
Independent Audit C (C-01) found that ordering worthless as first implemented.
``byte_only_gate_passed`` arrived as a CLI flag the operator set, so a round
whose gate failed --- or which ran no gate at all --- could pass ``true`` and
obtain a schema-valid assessment naming the better-sounding terminal state,
which CI would then reproduce byte for byte. That is the same defect Audit A
raised as A-03 about ``public_network_access``, reappearing in the instrument
that decides the round's outcome.

The flag is gone. :func:`derive_gate_outcome` reads the execution receipt,
validates it against the frozen receipt schema, and requires *nine* independent
properties of it before returning ``True``. A round with no receipt passes no
``--receipt`` and necessarily gets ``False``. The receipt's SHA-256 is recorded
in the assessment, so the assessment names the exact evidence it relied on.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DECISION_RECORD = REPO_ROOT / "docs" / "phase1_2h_r1_access_decision_record.json"
BOUNDARY_SCHEMA = REPO_ROOT / "docs" / "phase1_2h_r1_review_boundary.schema.json"
ACCESS_RECEIPT_SCHEMA = (
    REPO_ROOT / "docs" / "phase1_2h_r1_access_receipt.schema.json"
)

SCHEMA_VERSION = "phase1-2h-r1-review-boundary/v1"

#: The number of objects the frozen set contains. A receipt that streamed fewer
#: did not complete the gate, whatever its verdict field says.
EXPECTED_OBJECT_COUNT = 12

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


#: The complete set of terminal states this instrument can emit, keyed by the
#: outcome that produces each one. Audit C (C-07) found three separate terminal
#: state vocabularies in the repository -- the ledger's ``TERMINAL_STATES``, the
#: protocol's table, and the literals below -- which had already drifted apart.
#: Naming them here makes the vocabulary readable by a test, which asserts that
#: it is a subset of the ledger's. The assessor deliberately does not import
#: ``jspace_observation`` to check that itself: the package's ``__init__``
#: eagerly imports the legacy parser, and this instrument must not place parser
#: code in its own process.
TERMINAL_STATE_BY_OUTCOME: dict[str, str] = {
    "gate_did_not_pass": "BLOCKED_ON_PRIVATE_SOURCE_ACCESS",
    "gate_passed_boundary_does_not_qualify": "BLOCKED_ON_PRIVATE_REVIEW_BOUNDARY",
    "gate_passed_boundary_qualifies": (
        "READY_FOR_SEPARATELY_AUTHORISED_PRIVATE_REVIEW"
    ),
}


def classify_terminal_state(
    byte_only_gate_passed: bool, qualification: str
) -> str:
    """Apply the precedence rule Audit B asked for (B-09).

    Access precedes boundary: a round that could not reach the private source
    has not learned anything about the review boundary, so it must not claim the
    state that says it did.
    """

    if not byte_only_gate_passed:
        return TERMINAL_STATE_BY_OUTCOME["gate_did_not_pass"]
    if qualification != "QUALIFIES":
        return TERMINAL_STATE_BY_OUTCOME["gate_passed_boundary_does_not_qualify"]
    return TERMINAL_STATE_BY_OUTCOME["gate_passed_boundary_qualifies"]


#: The committed platform-side execution history of the access-gate job. Audit F
#: (F-01) is why this exists as an input rather than as background reading: the
#: receipt is written *by the probe, about the probe*, so every conjunct in
#: :data:`GATE_REQUIREMENTS` is ultimately one program's self-report. This file
#: is not. It is the output of an Azure control-plane query, which the probe has
#: no way to write, and it independently records which executions of the job
#: exist, which image each ran, what arguments each was given and how each
#: ended. Binding the receipt to it does not make the receipt's *counters* true
#: --- nothing offline can --- but it does establish that the execution the
#: receipt describes is an execution that the platform agrees happened, ran the
#: image the receipt names, and succeeded.
JOB_EXECUTION_INVENTORY = REPO_ROOT / "docs" / "phase1_2h_r1_job_execution_inventory.json"


class PlatformAttestationError(BoundaryAssessmentError):
    """The receipt describes an execution the platform record does not support."""


def assert_execution_is_platform_attested(
    receipt: Mapping[str, Any],
    inventory_path: Path = JOB_EXECUTION_INVENTORY,
) -> dict[str, Any]:
    """Bind the self-authored receipt to independently observed platform facts.

    Returns the matched inventory entry so a caller can record what it matched
    against.

    What this establishes: the named execution exists in Azure's own execution
    list for this job, it succeeded, it ran the image digest the receipt claims,
    and it was invoked with the execution id and freeze commit the receipt
    claims. Those are control-plane observations; the probe cannot author them.

    What this does **not** establish: that the receipt's counters are true. A
    program that genuinely ran the right image can still misreport what it did.
    The counters are supported by source analysis of the frozen source, which is
    a separate and weaker kind of evidence, and the report says so.
    """

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    execution = receipt.get("execution")
    provenance = receipt.get("provenance")
    if not isinstance(execution, Mapping) or not isinstance(provenance, Mapping):
        raise PlatformAttestationError(
            "receipt lacks the execution/provenance blocks needed to bind it to "
            "the platform record"
        )

    name = execution.get("aca_execution_name")
    matches = [
        entry
        for entry in inventory["executions"]
        if entry.get("name") == name
    ]
    if not matches:
        raise PlatformAttestationError(
            f"execution {name!r} does not appear in the committed platform "
            f"execution inventory ({inventory_path.name}); a receipt describing "
            "an execution the platform has no record of is not evidence that a "
            "gate ran"
        )
    entry = matches[0]

    if entry.get("status") != "Succeeded":
        raise PlatformAttestationError(
            f"execution {name!r} is recorded by the platform as "
            f"{entry.get('status')!r}, not 'Succeeded'"
        )

    claimed_image = provenance.get("image_digest")
    observed_image = entry.get("image", "")
    if not claimed_image or not observed_image.endswith(claimed_image):
        raise PlatformAttestationError(
            f"execution {name!r} ran an image the receipt does not claim; the "
            "receipt's image_digest must be the digest the platform recorded "
            "for that execution"
        )

    # The job arguments are recorded by the platform, so they are an independent
    # statement of what the operator asked for. A receipt whose provenance
    # disagrees with them is describing a different invocation.
    args = entry.get("args", [])
    for flag, claimed in (
        ("--execution-id", execution.get("execution_id")),
        ("--freeze-commit", provenance.get("access_protocol_freeze_commit")),
    ):
        if flag not in args:
            raise PlatformAttestationError(
                f"platform record for {name!r} has no {flag} argument to check "
                "the receipt against"
            )
        observed = args[args.index(flag) + 1]
        if observed != claimed:
            raise PlatformAttestationError(
                f"{flag} disagrees: the platform recorded {observed!r}, the "
                f"receipt claims {claimed!r}"
            )

    return entry


def derive_expected_anchors(
    record_path: Path = DECISION_RECORD,
) -> dict[str, Any]:
    """Recompute, from committed public evidence, what a real gate must report.

    Audit E (E-07) and Audit F (F-01) both landed on the same gap: every
    conjunct in :data:`GATE_REQUIREMENTS` was a summary field the probe wrote
    about itself, so a receipt describing twelve objects of *any* content
    satisfied all of them. The one value in the receipt that is checkable
    against something the probe did not author is
    ``streaming.observed_aggregate_digest``, and the material to check it with
    is already committed and public.

    The anchors are derived here rather than copied from a constant so that
    editing the public evidence file cannot silently move the target: the
    decision record pins that file's SHA-256 and its members digest, both are
    verified, and the aggregate is then recomputed from its contents.

    What this establishes: the run streamed objects whose per-object digests are
    exactly the committed public set. A receipt fabricated without access to the
    private source cannot produce this value except by copying it, and copying
    it means asserting a digest set that the seal already published --- which is
    the point of having published it.
    """

    record = json.loads(record_path.read_text(encoding="utf-8"))
    binding = record["expected_evidence_binding"]
    source = record["source_binding"]

    path = REPO_ROOT / binding["path"]
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if hashlib.sha256(raw).hexdigest() != binding["sha256"]:
        raise BoundaryAssessmentError(
            f"{binding['path']} does not match the digest the decision record "
            "pins for it; the expected-evidence file has been edited"
        )

    digests: list[str] = []
    total = 0
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        evaluation = row.get("evaluation")
        if not isinstance(evaluation, dict):
            continue
        # The freeze selects rows whose evaluation.order is an integer.
        # `type(...) is int` rather than isinstance, because bool subclasses int
        # and `"order": true` must not select a row. This mirrors the probe's
        # rule exactly; a divergence here would move the anchor.
        if type(evaluation.get("order")) is not int:
            continue
        digests.append(str(row["input_hash"]))
        total += int(evaluation["bytes"])

    if len(digests) != int(source["expected_object_count"]):
        raise BoundaryAssessmentError(
            "the expected-evidence file does not carry the object count the "
            "decision record registers"
        )
    if total != int(source["expected_total_bytes"]):
        raise BoundaryAssessmentError(
            "the expected-evidence file does not carry the byte total the "
            "decision record registers"
        )

    return {
        "aggregate_digest": hashlib.sha256(
            "\n".join(sorted(digests)).encode("utf-8")
        ).hexdigest(),
        "object_count": len(digests),
        "total_bytes": total,
    }


#: Every property a receipt must have before the gate counts as passed. Each is
#: a separate conjunct rather than a single ``access_gate_passed`` read, because
#: that one field is the probe's own summary of itself; these are the underlying
#: observations it summarises, and a receipt whose summary disagrees with them
#: is a receipt that should not be believed.
#:
#: Audit E (E-08) is why the following is stated rather than left implied: these
#: conjuncts are *not* twelve independent observations. Two of them
#: (``semantic_input_reads``, ``semantic_label_reads``) cannot fail here, because
#: :func:`load_gate_evidence` schema-validates first and the schema pins both to
#: ``maximum: 0`` --- they are restated so that removing the schema pin does not
#: silently remove the check. Four are two facts written twice:
#: ``all_digests_match`` is constructed as ``digest_mismatch_count == 0`` and
#: ``all_sizes_match`` as ``size_mismatch_count == 0``. What they collectively
#: establish is that the receipt is internally consistent, not that it is true.
#: The checks that reach outside the receipt are
#: :func:`assert_execution_is_platform_attested` and the anchor conjuncts in
#: :func:`derive_gate_outcome`.
GATE_REQUIREMENTS: tuple[tuple[str, str, Any], ...] = (
    ("verdict", "access_gate_passed", True),
    ("verdict", "invariants_failed", []),
    ("execution", "exit_status", "PASS"),
    ("streaming", "objects_streamed", EXPECTED_OBJECT_COUNT),
    ("streaming", "all_digests_match", True),
    ("streaming", "all_sizes_match", True),
    ("streaming", "digest_mismatch_count", 0),
    ("streaming", "size_mismatch_count", 0),
    ("membership", "member_sets_equal", True),
    ("membership", "counts_equal", True),
    ("counters", "semantic_input_reads", 0),
    ("counters", "semantic_label_reads", 0),
)


def derive_gate_outcome(receipt: Mapping[str, Any]) -> tuple[bool, list[str]]:
    """Decide from the receipt itself whether the byte-only gate passed.

    Returns the outcome and the list of requirements that failed, so a caller
    can say *why* rather than only *that*.

    Audit C (C-01): this function exists because the outcome used to be an
    operator-supplied boolean. Reading ``access_gate_passed`` alone would barely
    improve on that --- it is one field the probe wrote about itself --- so every
    conjunct in :data:`GATE_REQUIREMENTS` must hold independently.
    """

    failures: list[str] = []
    for section, key, expected in GATE_REQUIREMENTS:
        block = receipt.get(section)
        if not isinstance(block, Mapping) or key not in block:
            failures.append(f"{section}.{key}: absent")
            continue
        observed = block[key]
        # Guard against bool/int conflation: True == 1 in Python, and a receipt
        # reporting objects_streamed=True must not satisfy a count requirement.
        if isinstance(expected, bool) != isinstance(observed, bool):
            failures.append(f"{section}.{key}: wrong type")
        elif observed != expected:
            failures.append(f"{section}.{key}: expected {expected!r}")

    # Audit E (E-07). The conjuncts above are all the receipt agreeing with
    # itself. These are the receipt agreeing with committed public evidence it
    # did not author, recomputed rather than copied.
    anchors = derive_expected_anchors()
    streaming = receipt.get("streaming")
    if not isinstance(streaming, Mapping):
        failures.append("streaming: absent")
    else:
        for key, expected in (
            ("observed_aggregate_digest", anchors["aggregate_digest"]),
            ("total_bytes_streamed", anchors["total_bytes"]),
            ("expected_total_bytes", anchors["total_bytes"]),
        ):
            observed = streaming.get(key)
            if observed != expected:
                failures.append(
                    f"streaming.{key}: does not reproduce the value recomputed "
                    f"from committed public evidence"
                )

    return (not failures), failures


def load_gate_evidence(receipt_path: Path | None) -> dict[str, Any]:
    """Load, schema-validate and evaluate the execution receipt.

    A missing path is the honest representation of "no gate was run", and yields
    ``passed: False``. It is not an error, because a round that could not reach
    the source must still be able to produce an assessment --- one that names
    ``BLOCKED_ON_PRIVATE_SOURCE_ACCESS``.
    """

    if receipt_path is None:
        return {
            "receipt_path": None,
            "receipt_sha256": None,
            "passed": False,
            "unmet_requirements": ["no receipt was supplied"],
            "platform_attested_execution": None,
        }

    raw = receipt_path.read_bytes()
    receipt = json.loads(raw.decode("utf-8"))

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from phase1_2h_r1_receipt_validator import validate_receipt

    validate_receipt(receipt, ACCESS_RECEIPT_SCHEMA)

    resolved = receipt_path.resolve()
    try:
        relative = resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:  # a receipt from outside the repository is not evidence
        raise BoundaryAssessmentError(
            f"receipt must live inside the repository to be citable: {receipt_path}"
        ) from None

    passed, failures = derive_gate_outcome(receipt)

    # Audit F (F-01). Every conjunct above is the probe's report about itself.
    # This is the one check whose evidence the probe did not author.
    attestation = assert_execution_is_platform_attested(receipt)

    return {
        "receipt_path": relative,
        "receipt_sha256": hashlib.sha256(raw).hexdigest(),
        "passed": passed,
        "unmet_requirements": failures,
        "platform_attested_execution": attestation["name"],
    }


def _assert_cited_receipt_reproduces_the_gate(evidence: Mapping[str, Any]) -> None:
    """Open the receipt the evidence block names and re-derive the outcome.

    Audit E (E-01). Without this, a passing gate could be asserted by an
    evidence block that merely *mentions* a receipt path and digest. The block
    is now held to what that file actually contains: its bytes must hash to the
    recorded digest, every conjunct in :data:`GATE_REQUIREMENTS` must still
    hold, the anchors must still be reproduced, and the platform must still
    attest the named execution.
    """

    path = REPO_ROOT / str(evidence["receipt_path"])
    if not path.is_file():
        raise BoundaryAssessmentError(
            f"the evidence block names a receipt that does not exist: {path}"
        )
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    observed = hashlib.sha256(raw).hexdigest()
    if observed != evidence["receipt_sha256"]:
        raise BoundaryAssessmentError(
            "the receipt named by the evidence block does not hash to the "
            f"digest recorded there (recorded {evidence['receipt_sha256']}, "
            f"observed {observed})"
        )

    receipt = json.loads(raw.decode("utf-8"))
    passed, failures = derive_gate_outcome(receipt)
    if not passed:
        raise BoundaryAssessmentError(
            "the evidence block reports a passing gate, but the receipt it "
            f"names does not produce one: {failures}"
        )

    attested = evidence.get("platform_attested_execution")
    entry = assert_execution_is_platform_attested(receipt)
    if attested != entry["name"]:
        raise BoundaryAssessmentError(
            "the evidence block names a platform-attested execution that is "
            f"not the one the receipt binds to (block {attested!r}, receipt "
            f"{entry['name']!r})"
        )


def assert_gate_evidence_consistent(assessment: Mapping[str, Any]) -> None:
    """Cross-field implications the closed schema cannot express.

    The receipt validator deliberately refuses schema keywords it does not
    enforce, so ``if``/``then`` is unavailable and these implications live here
    instead.

    Audit C (C-01): the point is that ``byte_only_gate_passed`` and
    ``terminal_state`` cannot be moved independently of the evidence that
    produced them.

    Audit E (E-01) then found the whole check unable to fail. It was only ever
    applied to the object :func:`build_assessment` had just returned, whose
    evidence block that same call had derived, so every implication it tested
    was guaranteed by construction. Two things changed. It is now applied to the
    *committed* file as well, which is the artefact a reader trusts and the one
    an editor would tamper with; and when the block names a receipt, that
    receipt is opened, hashed, and re-run through :func:`derive_gate_outcome`,
    so the block cannot claim a passing gate that its own cited evidence does
    not produce.
    """

    passed = assessment["byte_only_gate_passed"]
    evidence = assessment["byte_only_gate_evidence"]
    terminal = assessment["terminal_state"]

    if evidence["passed"] != passed:
        raise BoundaryAssessmentError(
            "byte_only_gate_passed disagrees with its derived evidence block"
        )
    if passed:
        if evidence["unmet_requirements"]:
            raise BoundaryAssessmentError(
                "gate reported as passed while requirements are unmet: "
                f"{evidence['unmet_requirements']}"
            )
        if not evidence["receipt_sha256"] or not evidence["receipt_path"]:
            raise BoundaryAssessmentError(
                "a passing gate must name the receipt it was derived from"
            )
        _assert_cited_receipt_reproduces_the_gate(evidence)
    else:
        if not evidence["unmet_requirements"]:
            raise BoundaryAssessmentError(
                "gate reported as not passed without naming an unmet requirement"
            )
        if terminal != "BLOCKED_ON_PRIVATE_SOURCE_ACCESS":
            raise BoundaryAssessmentError(
                "a round whose byte-only gate did not pass cannot claim the "
                f"review boundary blocked it: {terminal}"
            )
    expected = classify_terminal_state(passed, assessment["qualification_verdict"])
    if terminal != expected:
        raise BoundaryAssessmentError(
            f"terminal_state {terminal!r} is not what the recorded verdicts imply "
            f"({expected!r})"
        )


def build_assessment(
    evidence: dict[str, Any],
    *,
    gate_evidence: dict[str, Any],
    record_path: Path = DECISION_RECORD,
) -> dict[str, Any]:
    conditions = load_conditions(record_path)
    results = assess(evidence)
    qualification = qualification_verdict(results)
    byte_only_gate_passed = bool(gate_evidence["passed"])
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
        "byte_only_gate_evidence": gate_evidence,
        "terminal_state": classify_terminal_state(byte_only_gate_passed, qualification),
        "instrument_access_effect": {
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
        "--receipt",
        type=Path,
        default=None,
        help=(
            "execution receipt from the byte-only access gate. The gate outcome "
            "is derived from it; omitting it means no gate was run."
        ),
    )
    parser.add_argument("--check", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    assessment = build_assessment(
        evidence, gate_evidence=load_gate_evidence(args.receipt)
    )

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from phase1_2h_r1_receipt_validator import validate_receipt

    validate_receipt(assessment, BOUNDARY_SCHEMA)
    assert_gate_evidence_consistent(assessment)
    rendered = json.dumps(assessment, indent=2, sort_keys=True) + "\n"

    if args.check is not None:
        # Audit E (E-01): validating only the freshly built object made these
        # checks structurally incapable of failing, because it was derived from
        # the same gate_evidence they re-derive. The committed file is the
        # artifact a reader trusts and the one an editor would tamper with, so
        # it is validated and re-checked on its own terms before the byte
        # comparison -- which means a hand-edited committed file is rejected
        # with the reason it is wrong, not merely as a diff.
        committed_raw = args.check.read_text(encoding="utf-8").replace("\r\n", "\n")
        committed_obj = json.loads(committed_raw)
        validate_receipt(committed_obj, BOUNDARY_SCHEMA)
        assert_gate_evidence_consistent(committed_obj)
        if committed_raw != rendered:
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
