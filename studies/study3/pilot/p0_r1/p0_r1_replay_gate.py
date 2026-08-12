"""The Study 3 P0-R1 replay gate: factorization plus repaired eligibility.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections 4,
6, 7 and 10.

The replay gate reads the immutable published P0-T artifacts and the frozen P0
corpus, derives the first-discriminative-token factorization, and recomputes the
eligibility matrix with the repaired classifier. It performs **zero** tokenizer
encodes, zero tokenizer constructions, zero checkpoint downloads, zero weight
loads and zero model operations, and it writes nothing into
``studies/study3/pilot/p0/``.

Two modes exist and they are deliberately different objects:

``--derive``
    the *calibration* derivation. It recomputes the corrected matrix so the
    draft-v0.6 amendment can report it, and it emits a derived table under
    ``studies/study3/analysis/``. It advances no state, consumes no one-shot
    authorization and writes no gate receipt. This is what the drafting session
    is permitted to run.

``--gate``
    the *registered* P0-R1 replay gate of section 7. It is the first action of
    the successor session, it writes its result and receipt under
    ``studies/study3/pilot/p0_r1/results/``, and it advances the state machine.
    Section 10 forbids the drafting session from performing it.
"""

import argparse
import datetime
import hashlib
import json
import os
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))

sys.path.insert(0, P0_R1_DIR)

import p0_r1_eligibility as ELIG  # noqa: E402
import p0_r1_execution_lock as LOCK  # noqa: E402
import p0_r1_factorization as FACT  # noqa: E402
from p0_r1_counters import P0R1Counters  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-replay-gate-v1"

GATE_RESULT_SCHEMA_VERSION = "study3-p0-r1-replay-gate-result-v1"
GATE_RECEIPT_SCHEMA_VERSION = "study3-p0-r1-replay-gate-receipt-v1"

#: The exact successor-mode token. ``--gate`` reaches live gate logic only when
#: the caller supplies it, so a calibration or build-time invocation cannot
#: consume the one-shot replay evaluation by accident.
SUCCESSOR_AUTHORIZATION = "p0-r1-successor-session"

#: Canonical artifact names written into the writable runtime result directory.
GATE_RESULT_NAME = "p0_r1_replay_result.json"
GATE_RECEIPT_NAME = "p0_r1_replay_receipt.json"
GATE_COUNTERS_NAME = "p0_r1_replay_counters.json"
GATE_DISPOSITION_NAME = "P0_R1_REPLAY_DISPOSITION.md"

#: The corrected matrix the replay gate must reproduce exactly.
REQUIRED_MATRIX_CELLS = 39
REQUIRED_ELIGIBLE_CELLS = 39
REQUIRED_EMPTY_REASON_INELIGIBLE_CELLS = 0
REQUIRED_EXECUTABLE_CONTRASTS_PER_ROLE = 11

DERIVED_TABLE_PATH = os.path.join(
    REPO_ROOT, "studies", "study3", "analysis",
    "p0_r1_corrected_eligibility_tables.json")

REGISTRY_PATH = os.path.join(
    REPO_ROOT, "studies", "study3", "protocol",
    "interface_calibration_rendering_registry_v0_6.json")

ROLES = ("RI", "RL", "RT")

REGISTERED_STATE_AFTER_REGISTRATION = (
    "STUDY3_P0_R1_REGISTERED_AWAITING_REPLAY_GATE")
STATE_AFTER_REPLAY_PASS = (
    "STUDY3_P0_R1_REPLAY_GATE_PASSED_AWAITING_MODEL_PILOT")
STATE_REPLAY_DEFECT = "STUDY3_P0_R1_STOPPED_ON_REPLAY_FACTORIZATION_DEFECT"


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_registry():
    with open(REGISTRY_PATH, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def published_s1_surfaces(result):
    """The published S1 label-surface encodes, per role and alphabet."""
    out = {}
    for role, entry in result.get("candidate_token_eligibility", {}).items():
        out[role] = {
            alphabet: {
                "surfaces": list(body["surfaces"]),
                "token_ids": [list(ids) for ids in body["token_ids"]],
                "all_single_token": bool(body["all_single_token"]),
                "pairwise_distinct": bool(body["pairwise_distinct"]),
            }
            for alphabet, body in sorted(entry.get("s1_by_alphabet", {}).items())
        }
    return out


def v0_5_rule_verdict(result):
    """The candidate verdict the *registered v0.5 rule* yields, per role.

    This isolates the classifier repair from the scoring-boundary repair. It
    applies the single-token rule that was registered when P0-T ran, to the same
    immutable published encodes, and produces an explicit local reason instead of
    a role-level flag. It exists so the amendment can show what the propagation
    repair alone would have produced, without restating the P0-T observations
    against a surface that did not exist when they were made.
    """
    roles = []
    for role in sorted(result.get("candidate_token_eligibility", {})):
        s2 = result["candidate_token_eligibility"][role]["s2"]
        reasons = []
        if not s2.get("all_single_token"):
            reasons.append(
                "the registered v0.5 rule requires ten single-token candidate "
                "surfaces; observed token-sequence lengths %s"
                % sorted({len(ids) for ids in s2["token_ids"]}))
        if not s2.get("pairwise_distinct"):
            reasons.append(
                "the registered v0.5 rule requires ten pairwise-distinct single "
                "candidate tokens at one position")
        roles.append({
            "role": role,
            "eligible": not reasons,
            "reasons": reasons,
        })
    return {"roles": roles}


def derive_classifier_repair_only(result, s1_by_role):
    """The corrected matrix under the *v0.5* scoring rule: classifier repair only."""
    corrected = ELIG.classify(
        result["records"], v0_5_rule_verdict(result), s1_by_role, ROLES)
    matrix = corrected["matrix"]
    return {
        "scoring_rule_applied": (
            "the draft-v0.5 single-next-token rule, unchanged, applied to the "
            "same immutable published encodes"),
        "classifier_version": corrected["classifier_version"],
        "cells": len(matrix),
        "eligible_cells": sum(1 for cell in matrix
                              if cell["status"] == ELIG.ELIGIBLE),
        "ineligible_cells": sum(1 for cell in matrix
                                if cell["status"] == ELIG.INELIGIBLE),
        "ineligible_cells_with_an_empty_reason_list": sum(
            1 for cell in matrix
            if cell["status"] == ELIG.INELIGIBLE and not cell["reasons"]),
        "executable_genuine_i3_contrasts_per_role": {
            role: len(values)
            for role, values in sorted(
                corrected["executable_genuine_i3_contrasts"].items())
        },
        "roles_without_executable_contrast":
            corrected["roles_without_executable_contrast"],
        "ineligible_cells_by_profile": {
            profile: sum(1 for cell in matrix
                         if cell["profile"] == profile
                         and cell["status"] == ELIG.INELIGIBLE)
            for profile in ("S1", "S2", "S3", "S4")
        },
        "what_this_shows": (
            "with the propagation removed but the v0.5 scoring rule unchanged, "
            "every S1 cell is eligible with no reason, every S2/S3 cell is "
            "ineligible with an explicit local reason rather than an empty list, "
            "and each target role retains nine executable genuine I3 contrasts. "
            "The historical terminal state was therefore over-severe, exactly as "
            "the published P0-T disposition discloses."),
    }


def derive(registry=None, counters=None, root=None):
    """Recompute the factorization and the corrected eligibility matrix."""
    registry = registry or load_registry()
    counters = counters if counters is not None else P0R1Counters()
    factorization = FACT.replay(registry, root=root, counters=counters)
    result = FACT.load_immutable(FACT.RESULT_PATH, root=root)
    records = result["records"]
    s1_by_role = published_s1_surfaces(result)

    corrected = ELIG.classify(records, factorization, s1_by_role, ROLES)
    repaired = ELIG.validate_no_propagation(
        corrected["matrix"], result.get("eligibility_matrix", []))

    historical = result.get("eligibility_matrix", [])
    historical_summary = {
        "cells": len(historical),
        "ineligible_cells": sum(1 for cell in historical
                                if cell.get("status") != "eligible"),
        "ineligible_cells_with_an_empty_reason_list": sum(
            1 for cell in historical
            if cell.get("status") != "eligible" and not cell.get("reasons")),
        "emitted_state": result.get("state"),
        "emitted_stop_reason": result.get("stop_reason"),
        "status": (
            "immutable historical observation. It is accepted as the record of "
            "what the P0-T harness emitted and it is never edited, replaced, "
            "relabelled or rerun."),
    }

    corrected_summary = {
        "cells": len(corrected["matrix"]),
        "eligible_cells": sum(1 for cell in corrected["matrix"]
                              if cell["status"] == ELIG.ELIGIBLE),
        "ineligible_cells": sum(1 for cell in corrected["matrix"]
                                if cell["status"] == ELIG.INELIGIBLE),
        "ineligible_cells_with_an_empty_reason_list": 0,
        "structurally_absent_pairs": len(corrected["structurally_absent"]),
        "executable_genuine_i3_contrasts_per_role": {
            role: len(values)
            for role, values in sorted(
                corrected["executable_genuine_i3_contrasts"].items())
        },
        "roles_without_executable_contrast":
            corrected["roles_without_executable_contrast"],
    }

    counter_snapshot = counters.snapshot()
    for name in ("tokenizer_encoded_sequences", "tokenizer_construction_events",
                 "distinct_checkpoint_identities_downloaded",
                 "model_weight_loads", "non_generative_prefill_evaluations",
                 "s4_generation_calls", "total_scored_rows",
                 "gpu_jobs_performing_a_model_operation"):
        if counter_snapshot[name] != 0:
            raise FACT.FactorizationDefect(
                "the replay derivation advanced %s to %d; it must perform zero "
                "tokenizer and model operations"
                % (name, counter_snapshot[name]))

    return {
        "schema_version": SCHEMA_VERSION,
        "document_class": "study3_p0_r1_corrected_eligibility",
        "stage": "P0-R1-REPLAY-DERIVATION",
        "kind": (
            "calibration derivation only. It advances no state, consumes no "
            "one-shot authorization and is not the registered replay gate."),
        "authority": "studies/study3/prompts/study3_v0_6_p0_r1_authority.md",
        "target_roles": list(ROLES),
        "tokenizer_encodes_performed": 0,
        "tokenizer_constructions_performed": 0,
        "model_operations_performed": 0,
        "factorization": factorization,
        "classifier_version": corrected["classifier_version"],
        "eligibility_keys": corrected["eligibility_keys"],
        "corrected_matrix": corrected["matrix"],
        "structurally_absent": corrected["structurally_absent"],
        "executable_genuine_i3_contrasts":
            corrected["executable_genuine_i3_contrasts"],
        "roles_without_executable_contrast":
            corrected["roles_without_executable_contrast"],
        "stop_label_if_any_role_has_none":
            corrected["stop_label_if_any_role_has_none"],
        "stop_label_semantics": corrected["stop_label_semantics"],
        "historical_stop_label": corrected["historical_stop_label"],
        "historical_stop_label_status":
            corrected["historical_stop_label_status"],
        "not_applicable_semantics": corrected["not_applicable_semantics"],
        "historical_matrix_summary": historical_summary,
        "classifier_repair_only_under_the_v0_5_rule":
            derive_classifier_repair_only(result, s1_by_role),
        "corrected_matrix_summary": corrected_summary,
        "cells_repaired_from_an_empty_reason_list": repaired,
        "counters": counter_snapshot,
    }


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


# ---------------------------------------------------------------------------
# The registered live replay gate. Successor session only.
# ---------------------------------------------------------------------------

class GateRefused(Exception):
    """Raised when the live gate is reached without successor authorization."""


def _matrix_summary(corrected):
    matrix = corrected["matrix"]
    return {
        "cells": len(matrix),
        "eligible_cells": sum(1 for cell in matrix
                              if cell["status"] == ELIG.ELIGIBLE),
        "ineligible_cells": sum(1 for cell in matrix
                                if cell["status"] == ELIG.INELIGIBLE),
        "ineligible_cells_with_an_empty_reason_list": sum(
            1 for cell in matrix
            if cell["status"] == ELIG.INELIGIBLE and not cell["reasons"]),
        "structurally_absent_pairs": len(corrected["structurally_absent"]),
        "executable_genuine_i3_contrasts_per_role": {
            role: len(values)
            for role, values in sorted(
                corrected["executable_genuine_i3_contrasts"].items())
        },
        "roles_without_executable_contrast":
            corrected["roles_without_executable_contrast"],
    }


def check_corrected_matrix(summary):
    """The registered acceptance conditions of the corrected matrix."""
    findings = []
    if summary["cells"] != REQUIRED_MATRIX_CELLS:
        findings.append(
            "the corrected matrix has %d cells, not the registered %d"
            % (summary["cells"], REQUIRED_MATRIX_CELLS))
    if summary["eligible_cells"] != REQUIRED_ELIGIBLE_CELLS:
        findings.append(
            "the corrected matrix has %d eligible cells, not the registered %d"
            % (summary["eligible_cells"], REQUIRED_ELIGIBLE_CELLS))
    if summary["ineligible_cells_with_an_empty_reason_list"] != \
            REQUIRED_EMPTY_REASON_INELIGIBLE_CELLS:
        findings.append(
            "%d ineligible cells carry an empty reason list; an ineligible row "
            "without an exact local reason is a validator failure"
            % summary["ineligible_cells_with_an_empty_reason_list"])
    per_role = summary["executable_genuine_i3_contrasts_per_role"]
    for role in ROLES:
        observed = per_role.get(role)
        if observed != REQUIRED_EXECUTABLE_CONTRASTS_PER_ROLE:
            findings.append(
                "role %s retains %r executable genuine I3 contrasts, not the "
                "registered %d"
                % (role, observed, REQUIRED_EXECUTABLE_CONTRASTS_PER_ROLE))
    if summary["roles_without_executable_contrast"]:
        findings.append(
            "one or more target roles has no executable genuine I3 contrast: %s"
            % summary["roles_without_executable_contrast"])
    return findings


def _counter_guard(snapshot):
    """Every tokenizer, model, GPU and scoring counter must remain zero."""
    findings = []
    for name, value in sorted(snapshot.items()):
        if name == "replay_gate_evaluations":
            continue
        if value != 0:
            findings.append(
                "the replay gate advanced %s to %d; it performs zero tokenizer, "
                "checkpoint, model, GPU and scoring operations" % (name, value))
    if snapshot.get("replay_gate_evaluations") != 1:
        findings.append(
            "replay_gate_evaluations is %r; the registered gate increments it "
            "exactly once" % snapshot.get("replay_gate_evaluations"))
    return findings


def _write_artifacts(out_dir, result, receipt, counters, disposition):
    """Write every canonical byte before the gate returns, pass or fail."""
    if not out_dir:
        raise GateRefused(
            "the registered replay gate requires an explicit writable runtime "
            "result directory; /workspace/studies is read-only in the image")
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name, payload in (
            (GATE_RESULT_NAME, dumps(result).encode("utf-8")),
            (GATE_RECEIPT_NAME, dumps(receipt).encode("utf-8")),
            (GATE_COUNTERS_NAME, dumps(counters).encode("utf-8")),
            (GATE_DISPOSITION_NAME, disposition.encode("utf-8"))):
        path = os.path.join(out_dir, name)
        with open(path, "wb") as handle:
            handle.write(payload)
        written.append({
            "name": name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    return written


def _disposition_markdown(state, summary, factorization, stop_reason, lock):
    lines = [
        "# Stage P0-R1 replay gate: disposition",
        "",
        "> **Emitted terminal state:** `%s`" % state,
        ">",
        "> Published exactly as emitted. No observed value is edited, replaced,",
        "> regenerated or rerun.",
        "",
        "| field | value |",
        "| --- | --- |",
        "| stage | `P0-R1-REPLAY-GATE` |",
        "| image digest | `%s` |" % lock["image"]["digest"],
        "| executable code commit | `%s` |" % lock["executable_code"]["commit"],
        "| tokenizer encodes | `0` |",
        "| tokenizer constructions | `0` |",
        "| model operations | `0` |",
        "| GPU allocations | `0` |",
        "",
        "## Corrected eligibility matrix",
        "",
        "| quantity | observed | required |",
        "| --- | --- | --- |",
        "| cells | %d | %d |" % (summary["cells"], REQUIRED_MATRIX_CELLS),
        "| eligible cells | %d | %d |"
        % (summary["eligible_cells"], REQUIRED_ELIGIBLE_CELLS),
        "| ineligible cells with an empty reason list | %d | %d |"
        % (summary["ineligible_cells_with_an_empty_reason_list"],
           REQUIRED_EMPTY_REASON_INELIGIBLE_CELLS),
    ]
    for role in ROLES:
        lines.append(
            "| executable genuine I3 contrasts, %s | %s | %d |"
            % (role,
               summary["executable_genuine_i3_contrasts_per_role"].get(role),
               REQUIRED_EXECUTABLE_CONTRASTS_PER_ROLE))
    lines += [
        "",
        "## Factorization",
        "",
        "Derived from the immutable published P0-T result and the frozen P0",
        "corpus, never transcribed and never re-encoded.",
        "",
        "* common-prefix token common to every role: `%s`"
        % factorization["common_prefix_token_is_common_to_every_role"],
        "* discriminant token IDs common to every role: `%s`"
        % factorization["discriminant_token_ids_are_common_to_every_role"],
        "* all roles eligible: `%s`" % factorization["all_roles_eligible"],
        "",
    ]
    if stop_reason:
        lines += [
            "## Why the gate stopped",
            "",
            stop_reason,
            "",
            "No model operation follows this stop. The partial evidence above is",
            "preserved exactly as observed and is never repaired or rerun.",
            "",
        ]
    else:
        lines += [
            "## What this authorizes",
            "",
            "Exactly one bounded GPU model pilot, in this same execution",
            "session, bound to the locked image digest and this receipt. It",
            "authorizes nothing else: no interface selection, no threshold, no",
            "formal gate, no evidence-ledger row.",
            "",
        ]
    return "\n".join(lines)


def gate_run(out_dir, authorization=None, image_digest=None, commit=None,
             tree=None, root=None, registry=None, counters=None):
    """The registered P0-R1 replay gate. Successor session only.

    Reads the immutable P0-T artifacts, verifies the five factorization
    conditions and the corrected eligibility matrix, and writes canonical result,
    receipt, counter and disposition bytes to ``out_dir`` **before returning**,
    on both the pass and the failure path.

    Performs zero tokenizer constructions, zero encodes, zero checkpoint
    downloads, zero model loads, zero forward passes and zero GPU operations.
    """
    if authorization != SUCCESSOR_AUTHORIZATION:
        raise GateRefused(
            "the registered P0-R1 replay gate is the first action of the "
            "successor execution session. It requires explicit successor-mode "
            "authorization (%r); the calibration and image-build modes may only "
            "run --derive or --check." % SUCCESSOR_AUTHORIZATION)
    if not out_dir:
        raise GateRefused(
            "the registered replay gate requires an explicit writable runtime "
            "result directory")

    lock = LOCK.load_lock(root=root)
    LOCK.verify_binding(lock, image_digest=image_digest, root=root)
    if commit is not None and commit != lock["executable_code"]["commit"]:
        # The gate runs from the ready commit, a strict descendant. Only the
        # executable bytes must match, and verify_binding already proved that.
        pass
    del tree

    counters = counters if counters is not None else P0R1Counters()
    registry = registry if registry is not None else load_registry()
    started = utc_now()

    try:
        immutable_sources = FACT.verify_immutable_sources(root=root)
        immutable_source_defect = None
    except FACT.FactorizationDefect as exc:
        immutable_sources = []
        immutable_source_defect = str(exc)

    stop_reason = None
    findings = []
    try:
        factorization = FACT.gate(registry, root=root, counters=counters)
    except FACT.FactorizationDefect as exc:
        factorization = {
            "all_roles_eligible": False,
            "common_prefix_token_is_common_to_every_role": False,
            "discriminant_token_ids_are_common_to_every_role": False,
            "defect": str(exc),
        }
        stop_reason = (
            "The replay factorization gate failed on immutable evidence: %s"
            % exc)
        state = STATE_REPLAY_DEFECT
        summary = {
            "cells": 0, "eligible_cells": 0, "ineligible_cells": 0,
            "ineligible_cells_with_an_empty_reason_list": 0,
            "structurally_absent_pairs": 0,
            "executable_genuine_i3_contrasts_per_role": {},
            "roles_without_executable_contrast": list(ROLES),
        }
        corrected = None
    else:
        result = FACT.load_immutable(FACT.RESULT_PATH, root=root)
        corrected = ELIG.classify(
            result["records"], factorization,
            published_s1_surfaces(result), ROLES)
        ELIG.validate_matrix(corrected["matrix"], roles=ROLES)
        summary = _matrix_summary(corrected)
        findings = check_corrected_matrix(summary)
        if findings:
            stop_reason = (
                "The corrected eligibility matrix did not reproduce the "
                "registered acceptance conditions:\n\n"
                + "\n".join("* %s" % finding for finding in findings))
            state = (ELIG.STOP_SOME_ROLE_HAS_NO_EXECUTABLE_CONTRAST
                     if summary["roles_without_executable_contrast"]
                     else STATE_REPLAY_DEFECT)
        else:
            state = STATE_AFTER_REPLAY_PASS

    snapshot = counters.snapshot()
    counter_findings = _counter_guard(snapshot)
    if counter_findings and state == STATE_AFTER_REPLAY_PASS:
        stop_reason = (
            "The replay gate counters did not reconcile:\n\n"
            + "\n".join("* %s" % finding for finding in counter_findings))
        state = STATE_REPLAY_DEFECT
        findings = findings + counter_findings

    passed = state == STATE_AFTER_REPLAY_PASS
    attempt_id = "%s-%s" % (
        lock["executable_code"]["commit"][:12], started)

    result_document = {
        "schema_version": GATE_RESULT_SCHEMA_VERSION,
        "document_class": "study3_p0_r1_replay_gate_result",
        "stage": "P0-R1-REPLAY-GATE",
        "state": state,
        "passed": passed,
        "attempt_id": attempt_id,
        "started_utc": started,
        "completed_utc": utc_now(),
        "authority": LOCK.REGISTRATION_AUTHORITY["path"],
        "supplemental_authority": LOCK.SUPPLEMENTAL_AUTHORITY["path"],
        "execution_lock": LOCK.lock_identity(root=root),
        "image_digest": lock["image"]["digest"],
        "executable_code_commit": lock["executable_code"]["commit"],
        "executable_code_tree": lock["executable_code"]["tree"],
        "immutable_sources": immutable_sources,
        "immutable_source_defect": immutable_source_defect,
        "target_roles": list(ROLES),
        "tokenizer_encodes_performed": 0,
        "tokenizer_constructions_performed": 0,
        "model_operations_performed": 0,
        "gpu_allocated": False,
        "factorization": factorization,
        "corrected_matrix": (corrected["matrix"] if corrected else []),
        "structurally_absent": (corrected["structurally_absent"]
                                if corrected else []),
        "executable_genuine_i3_contrasts": (
            corrected["executable_genuine_i3_contrasts"] if corrected else {}),
        "corrected_matrix_summary": summary,
        "acceptance_findings": findings,
        "stop_reason": stop_reason,
        "counters": snapshot,
        "evidence_status": (
            "a methods-feasibility replay observation over immutable evidence. "
            "It is not Study 3 evidence, selects no interface, sets no "
            "threshold and answers no research question."),
    }

    receipt_document = {
        "schema_version": GATE_RECEIPT_SCHEMA_VERSION,
        "document_class": "study3_p0_r1_replay_gate_receipt",
        "stage": "P0-R1-REPLAY-GATE",
        "state": state,
        "passed": passed,
        "attempt_id": attempt_id,
        "completed_utc": result_document["completed_utc"],
        "execution_lock": LOCK.lock_identity(root=root),
        "image_digest": lock["image"]["digest"],
        "executable_code_commit": lock["executable_code"]["commit"],
        "executable_code_tree": lock["executable_code"]["tree"],
        "result_document": {"name": GATE_RESULT_NAME},
        "counters": snapshot,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "model_weight_loads": 0,
        "gpu_allocated": False,
        "model_operations_performed": 0,
        "stop_reason": stop_reason,
        "authorizes_model_pilot": passed,
        "authorization_scope": (
            "exactly one bounded GPU model pilot in this same execution "
            "session, bound to the locked image digest and this attempt id"
            if passed else
            "nothing. A replay failure authorizes no model operation."),
    }

    disposition = _disposition_markdown(
        state, summary, factorization, stop_reason, lock)

    written = _write_artifacts(
        out_dir, result_document, receipt_document, snapshot, disposition)

    payload = dumps(result_document).encode("utf-8")
    receipt_document["result_document"] = {
        "name": GATE_RESULT_NAME,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    written = _write_artifacts(
        out_dir, result_document, receipt_document, snapshot, disposition)

    return {
        "state": state,
        "passed": passed,
        "attempt_id": attempt_id,
        "result": result_document,
        "receipt": receipt_document,
        "artifacts": written,
        "out_dir": out_dir,
    }


def _write_derived_table(document):
    with open(DERIVED_TABLE_PATH, "wb") as handle:
        handle.write(dumps(document).encode("utf-8"))
    return DERIVED_TABLE_PATH


def _check_derived_table(document):
    if not os.path.exists(DERIVED_TABLE_PATH):
        return ["the corrected-eligibility table is missing"]
    with open(DERIVED_TABLE_PATH, "rb") as handle:
        on_disk = handle.read()
    if on_disk != dumps(document).encode("utf-8"):
        return ["the corrected-eligibility table does not reproduce from code"]
    return []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--derive", action="store_true",
                       help="recompute and write the calibration derivation")
    group.add_argument("--check", action="store_true",
                       help="verify the derivation reproduces byte-exactly")
    group.add_argument("--gate", action="store_true",
                       help="the registered replay gate; successor session only")
    parser.add_argument("--out-dir")
    parser.add_argument("--successor-authorization",
                        help="the explicit successor-mode token required to "
                             "reach live gate logic")
    parser.add_argument("--image-digest",
                        help="the immutable digest of the running image; it "
                             "must equal the locked digest")
    args = parser.parse_args(argv)

    if args.gate:
        if args.successor_authorization != SUCCESSOR_AUTHORIZATION:
            print("REFUSED: the registered P0-R1 replay gate is the first "
                  "action of the successor execution session.")
            print("It requires explicit successor-mode authorization and a "
                  "writable runtime result directory.")
            print("The calibration and image-build modes may only run --derive "
                  "or --check (authority sections 6 and 10).")
            print("state remains: %s" % REGISTERED_STATE_AFTER_REGISTRATION)
            return 3
        if not args.out_dir:
            print("REFUSED: --gate requires --out-dir, a writable runtime "
                  "result directory. /workspace/studies is read-only.")
            print("state remains: %s" % REGISTERED_STATE_AFTER_REGISTRATION)
            return 3
        try:
            outcome = gate_run(
                args.out_dir,
                authorization=args.successor_authorization,
                image_digest=args.image_digest)
        except (GateRefused, LOCK.LockDefect) as exc:
            print("REFUSED: %s" % exc)
            return 3
        for artifact in outcome["artifacts"]:
            print("wrote %s (%d bytes, sha256 %s)"
                  % (artifact["name"], artifact["bytes"], artifact["sha256"]))
        print("TOKENIZER_ENCODES=0")
        print("TOKENIZER_CONSTRUCTIONS=0")
        print("MODEL_OPERATIONS=0")
        print("P0_R1_REPLAY_ATTEMPT_ID=%s" % outcome["attempt_id"])
        if outcome["passed"]:
            print(outcome["state"])
            return 0
        print("%s: %s" % (outcome["state"],
                          outcome["result"].get("stop_reason") or "stopped"))
        return 2

    try:
        document = derive()
    except (FACT.FactorizationDefect, ELIG.EligibilityDefect) as exc:
        print("%s: %s" % (STATE_REPLAY_DEFECT, exc))
        return 2

    if args.derive:
        path = _write_derived_table(document)
        print("wrote %s" % os.path.relpath(path, REPO_ROOT).replace(os.sep, "/"))
        return 0

    findings = _check_derived_table(document)
    if findings:
        print("REPLAY DERIVATION CHECK FAILED")
        for finding in findings:
            print("  FAIL %s" % finding)
        return 1
    summary = document["corrected_matrix_summary"]
    print("replay derivation: OK")
    print("  encodes performed             : %d"
          % document["tokenizer_encodes_performed"])
    print("  corrected cells               : %d (%d eligible, %d ineligible)"
          % (summary["cells"], summary["eligible_cells"],
             summary["ineligible_cells"]))
    print("  empty-reason ineligible cells : %d (was %d)"
          % (summary["ineligible_cells_with_an_empty_reason_list"],
             document["historical_matrix_summary"][
                 "ineligible_cells_with_an_empty_reason_list"]))
    print("  executable contrasts per role : %s"
          % summary["executable_genuine_i3_contrasts_per_role"])
    print("  roles without a contrast      : %s"
          % (document["roles_without_executable_contrast"] or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
