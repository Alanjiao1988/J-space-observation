"""Post-seal preregistration and the one-shot Stage P -> Stage E evaluation.

This module is the *executable* path for the formal parser-v3 evaluation, not a
description of one. Phase A of the controlling protocol requires the public
synthetic rehearsal to drive the same functions the private run will drive,
because the round-5 defect this programme exists to avoid was validating a
named definition that the live job never executed. Every guarantee below is
therefore expressed as a function that the runner must call in order to make
progress, rather than as a document the runner may agree with.

Three separations carry the science and none of them are advisory:

* Stage P is given inputs and a parser and is structurally unable to receive a
  label, because the label-bearing key check runs over the payload it is
  handed and refuses before the parser is invoked.
* The prediction stream seals create-only and completely, so the predictions
  that Stage E scores are the predictions Stage P produced, in full.
* Stage E is given labels and sealed predictions and is structurally unable to
  run the parser, because it never receives one and refuses if parser modules
  are resident in its process.

The evaluation ordinal, the state machine, and the status exclusivity rules
live in :mod:`jspace_observation.parser_v3_v2_lifecycle`; this module composes
them rather than restating them, so there is exactly one definition of each.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Callable

from jspace_observation import parser_v3_v2_lifecycle as lifecycle

__all__ = [
    "EvaluationError",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PREREGISTERED_BINDINGS",
    "LABEL_BEARING_FIELDS",
    "ZERO_ERROR_RESIDUAL_STRATA",
    "PINNED_ZERO_ERROR_GATES",
    "NONBINDING_DIAGNOSTICS",
    "PARSER_V2_COMPARISON_STATES",
    "ANSWER_PRESENCE_CLASSES",
    "canonical_digest",
    "create_preregistration_lock",
    "assert_lock_unchanged",
    "assert_stage_p_payload_carries_no_label",
    "assert_stage_p_import_is_scorer_free",
    "run_stage_p",
    "seal_prediction_stream",
    "run_stage_e",
]


class EvaluationError(Exception):
    """Raised when an evaluation invariant would be violated.

    Distinct from :class:`~jspace_observation.parser_v3_v2_lifecycle.
    LifecycleError` so that a caller cannot catch one and accidentally swallow
    the other.
    """


PREREGISTRATION_SCHEMA_VERSION = "phase1-parser-v3-v2-preregistration/v1"

#: Everything the preregistration lock must bind, closed. A lock that is
#: missing a key is refused and a lock that carries an unknown key is refused,
#: because a binding set that can quietly grow is not a binding set: the run
#: could then be authorised against a field nobody registered.
PREREGISTERED_BINDINGS: tuple[str, ...] = (
    "sealed_set_manifest_digest",
    "sealed_set_listing_witness_digest",
    "set_facts_digest",
    "final_contract_digest",
    "policy_full_file_digest",
    "policy_semantic_digest",
    "parser_v3_digest",
    "scorer_digest",
    "dependency_lock_digest",
    "base_image_digest",
    "image_payload_manifest_digest",
    "evaluation_image_digest",
    "cuda_runtime",
    "stage_p_entrypoint",
    "stage_p_command",
    "stage_p_identity",
    "stage_p_read_classes",
    "stage_e_entrypoint",
    "stage_e_command",
    "stage_e_identity",
    "stage_e_read_classes",
    "prediction_member_layout",
    "prediction_completeness_rule",
    "prediction_seal_mode",
    "prediction_listing_schema",
    "prediction_receipt_schema",
    "state_machine_digest",
    "evaluation_ordinal",
    "retry_rule",
    "binding_acceptance_criteria",
    "nonbinding_diagnostics",
    "formal_result_schema",
    "public_redaction_projection",
)

#: Keys whose presence in a Stage P payload means a label leaked into the
#: prediction stage. Matched as substrings of the case-folded key, because the
#: leak that matters is the one nobody named exactly as expected.
#:
#: This guard is deliberately broad, unlike the template-family collision rule
#: in the construction module, which was deliberately narrowed. The asymmetry is
#: the point: a false positive here refuses a run that can simply be re-issued
#: with a clean payload, while a false positive there silently destroys a sound
#: 120-case set. Tune each guard in the direction where being wrong is cheap.
LABEL_BEARING_FIELDS: tuple[str, ...] = (
    "label",
    "gold",
    "ground_truth",
    "groundtruth",
    "answer_key",
    "expected",
    "reference_answer",
    "target",
    "truth",
    "correct",
)

#: Strata carrying the zero-error residual rule: pooled maximum 0 *and*
#: per-stratum maximum 0.
ZERO_ERROR_RESIDUAL_STRATA: tuple[str, ...] = ("S04", "S05", "S06", "S09")

#: The pinned zero-error gates that the remaining cases must satisfy. Together
#: with the residual rule these imply 120/120 finite-suite conformance, so no
#: duplicate percentage threshold is registered; a second, differently-rounded
#: expression of the same requirement is a way for two gates to disagree.
PINNED_ZERO_ERROR_GATES: tuple[str, ...] = (
    "canonical_present_value_exact",
    "answer_presence_class_exact",
    "no_answer_not_fabricated",
    "ambiguity_not_resolved_silently",
)

#: Diagnostics that are computed and published but can never reach status.
NONBINDING_DIAGNOSTICS: tuple[str, ...] = (
    "answer_presence_confusion_matrix",
    "per_class_precision",
    "per_class_recall",
    "per_class_f1",
    "macro_f1",
    "parser_v2_comparison",
)

#: The only values the parser-v2 comparison may take in this round.
PARSER_V2_COMPARISON_STATES: frozenset[str] = frozenset(
    {"FINAL", "NOT_RUN", "REPORT_ONLY"}
)

#: The three answer-presence classes used by the nonbinding confusion matrix.
ANSWER_PRESENCE_CLASSES: tuple[str, ...] = ("present", "no_answer", "ambiguous")


def canonical_digest(payload: Any) -> str:
    """Return a stable SHA-256 over a JSON-serialisable payload.

    Keys are sorted and text is NFC-normalised so that two structurally equal
    payloads cannot produce two different digests and be mistaken for two
    different bindings.
    """

    def normalise(value: Any) -> Any:
        if isinstance(value, str):
            return unicodedata.normalize("NFC", value)
        if isinstance(value, Mapping):
            return {normalise(k): normalise(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalise(item) for item in value]
        return value

    encoded = json.dumps(
        normalise(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def create_preregistration_lock(
    *,
    bindings: Mapping[str, Any],
    existing_lock_digest: str | None = None,
) -> tuple[Mapping[str, Any], str]:
    """Create the immutable preregistration lock exactly once.

    Returns the frozen bindings and their digest. Refuses if a lock already
    exists, because "create the lock again" and "change a bound byte" are the
    same operation wearing different clothes.
    """
    if existing_lock_digest is not None:
        raise EvaluationError(
            "a preregistration lock already exists; bound bytes cannot change"
        )
    supplied = set(bindings)
    registered = set(PREREGISTERED_BINDINGS)
    missing = sorted(registered - supplied)
    if missing:
        raise EvaluationError(f"preregistration lock is missing bindings: {missing}")
    unknown = sorted(supplied - registered)
    if unknown:
        raise EvaluationError(f"preregistration lock carries unknown bindings: {unknown}")

    ordinal = bindings["evaluation_ordinal"]
    if ordinal != 0:
        raise EvaluationError(
            f"preregistration must bind evaluation ordinal 0, got {ordinal!r}"
        )
    comparison = bindings["nonbinding_diagnostics"]
    if not isinstance(comparison, (list, tuple)) or set(comparison) != set(
        NONBINDING_DIAGNOSTICS
    ):
        raise EvaluationError(
            "preregistration must bind exactly the registered nonbinding diagnostics"
        )
    if bindings["prediction_seal_mode"] != "create_only":
        raise EvaluationError("the prediction seal mode must be create_only")

    frozen = dict(bindings)
    frozen["schema_version"] = PREREGISTRATION_SCHEMA_VERSION
    return frozen, canonical_digest(frozen)


def assert_lock_unchanged(lock: Mapping[str, Any], expected_digest: str) -> None:
    """Refuse to proceed if any bound byte moved after the lock was created."""
    actual = canonical_digest(lock)
    if actual != expected_digest:
        raise EvaluationError(
            "preregistration lock changed after creation: "
            f"expected {expected_digest}, computed {actual}"
        )


def _label_hits(payload: Any, path: str) -> list[str]:
    hits: list[str] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            folded = str(key).casefold()
            here = f"{path}.{key}"
            if any(marker in folded for marker in LABEL_BEARING_FIELDS):
                hits.append(here)
            hits.extend(_label_hits(value, here))
    elif isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            hits.extend(_label_hits(item, f"{path}[{index}]"))
    return hits


def assert_stage_p_payload_carries_no_label(payload: Any, *, path: str = "payload") -> None:
    """Refuse a Stage P payload that carries a scoring label at any depth.

    The check runs over the payload actually handed to Stage P rather than over
    a declared schema, because a schema describes what was intended and the
    payload is what arrives.
    """
    hits = _label_hits(payload, path)
    if hits:
        raise EvaluationError(f"label-bearing field(s) reached Stage P: {sorted(hits)}")


def assert_stage_p_import_is_scorer_free(
    loaded_module_names: Iterable[str],
    *,
    scorer_markers: Sequence[str] = (
        "scorer",
        "scoring",
        "comparator",
        "label",
        "grading",
    ),
) -> None:
    """Refuse a Stage P process holding scoring-label or comparator code.

    The mirror of the Stage E parser check in the lifecycle module. Stage P
    that can import the comparator can compute its own score, and a stage that
    can see its score can be tuned against it.
    """
    hits = sorted(
        {
            name
            for name in loaded_module_names
            for marker in scorer_markers
            if marker in name.casefold()
        }
    )
    if hits:
        raise EvaluationError(
            f"scoring-bearing module(s) present in a Stage P process: {hits}"
        )


def run_stage_p(
    *,
    lock: Mapping[str, Any],
    lock_digest: str,
    state: str,
    ordinal: int,
    locked_inputs: Sequence[Mapping[str, Any]],
    parser: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    loaded_module_names: Iterable[str] = (),
) -> Mapping[str, Any]:
    """Run the single Stage P pass and return an unsealed prediction stream.

    The parser is invoked exactly once per locked input, in the registered
    order, and never sees a label. Sealing is a separate call so that a partial
    stream is representable and therefore testable: a design in which producing
    and sealing are one step cannot demonstrate that a partial stream is
    refused.
    """
    assert_lock_unchanged(lock, lock_digest)
    if state != "PREREGISTERED":
        raise EvaluationError(f"Stage P may only start from PREREGISTERED, not {state}")
    if ordinal != 0:
        raise EvaluationError(f"Stage P requires evaluation ordinal 0, got {ordinal}")
    lifecycle.assert_transition_permitted(state, "PREDICTION_RUNNING")
    lifecycle.assert_stage_p_scope(lock["stage_p_read_classes"])
    assert_stage_p_import_is_scorer_free(loaded_module_names)

    if len(locked_inputs) != lifecycle.EXPECTED_SET_MEMBER_COUNT:
        raise EvaluationError(
            f"Stage P requires exactly {lifecycle.EXPECTED_SET_MEMBER_COUNT} locked "
            f"inputs, got {len(locked_inputs)}"
        )
    assert_stage_p_payload_carries_no_label(locked_inputs, path="locked_inputs")

    seen: set[str] = set()
    members: list[dict[str, Any]] = []
    for position, case in enumerate(locked_inputs):
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise EvaluationError(f"locked input at position {position} has no case_id")
        if case_id in seen:
            raise EvaluationError(f"locked input {case_id!r} appears twice")
        seen.add(case_id)
        prediction = parser(case)
        if not isinstance(prediction, Mapping):
            raise EvaluationError(f"parser returned a non-mapping for {case_id!r}")
        assert_stage_p_payload_carries_no_label(prediction, path=f"prediction[{case_id}]")
        member = {
            "case_id": case_id,
            "position": position,
            "source_digest": canonical_digest(case),
            "prediction": dict(prediction),
        }
        member["member_digest"] = canonical_digest(member)
        members.append(member)

    return {
        "state": "PREDICTION_RUNNING",
        "ordinal": 0,
        "lock_digest": lock_digest,
        "members": members,
    }


def seal_prediction_stream(
    *,
    stream: Mapping[str, Any],
    sealed_case_ids: Sequence[str],
    write_order: Sequence[str],
    terminal_manifest: str,
    existing_objects: Iterable[str] = (),
) -> Mapping[str, Any]:
    """Seal the prediction stream create-only and completely.

    Delegates completeness, terminal-manifest ordering, and create-only
    enforcement to the lifecycle module so that the prediction seal and the set
    seal cannot drift apart into two different notions of "sealed".
    """
    if stream.get("state") != "PREDICTION_RUNNING":
        raise EvaluationError(
            f"only a running prediction stream can seal, not {stream.get('state')!r}"
        )
    members = stream["members"]
    lifecycle.assert_prediction_stream_complete(
        sealed_case_ids=list(sealed_case_ids),
        prediction_case_ids=[member["case_id"] for member in members],
    )
    lifecycle.assert_terminal_manifest_last(
        write_order=write_order, terminal_manifest=terminal_manifest
    )
    lifecycle.assert_create_only_plan(
        existing_objects=existing_objects,
        planned_objects=list(write_order),
        terminal_manifest=terminal_manifest,
    )
    lifecycle.assert_transition_permitted("PREDICTION_RUNNING", "PREDICTION_SEALED")

    listing = [
        {"case_id": member["case_id"], "member_digest": member["member_digest"]}
        for member in members
    ]
    receipt = {
        "state": "PREDICTION_SEALED",
        "ordinal": 0,
        "lock_digest": stream["lock_digest"],
        "member_count": len(members),
        "listing_witness_digest": canonical_digest(listing),
        "stream_digest": canonical_digest(members),
        "write_order": list(write_order),
    }
    receipt["receipt_digest"] = canonical_digest(receipt)
    return receipt


def _presence_class(record: Mapping[str, Any], field: str = "answer_presence") -> str:
    value = record.get(field)
    if value not in ANSWER_PRESENCE_CLASSES:
        raise EvaluationError(
            f"{field}={value!r} is not one of {list(ANSWER_PRESENCE_CLASSES)}"
        )
    return str(value)


def _confusion_matrix(
    pairs: Sequence[tuple[str, str]],
) -> dict[str, dict[str, int]]:
    matrix = {
        truth: {predicted: 0 for predicted in ANSWER_PRESENCE_CLASSES}
        for truth in ANSWER_PRESENCE_CLASSES
    }
    for truth, predicted in pairs:
        matrix[truth][predicted] += 1
    return matrix


def _per_class_metrics(
    matrix: Mapping[str, Mapping[str, int]],
) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for klass in ANSWER_PRESENCE_CLASSES:
        true_positive = matrix[klass][klass]
        predicted_total = sum(matrix[truth][klass] for truth in ANSWER_PRESENCE_CLASSES)
        actual_total = sum(matrix[klass].values())
        precision = true_positive / predicted_total if predicted_total else 0.0
        recall = true_positive / actual_total if actual_total else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        metrics[klass] = {"precision": precision, "recall": recall, "f1": f1}
    return metrics


def run_stage_e(
    *,
    lock: Mapping[str, Any],
    lock_digest: str,
    prediction_receipt: Mapping[str, Any],
    sealed_members: Sequence[Mapping[str, Any]],
    labels: Mapping[str, Mapping[str, Any]],
    strata: Mapping[str, str],
    parser_v2_comparison: str = "NOT_RUN",
    loaded_module_names: Iterable[str] = (),
) -> Mapping[str, Any]:
    """Open labels and produce the unique formal result.

    Every binding gate is a zero-error gate, so status is decided by counting
    mismatches, not by comparing a rate against a threshold. The confusion
    matrix and macro-F1 are computed after status is fixed and are passed
    through the lifecycle reachability check, which proves they had no path to
    it: a diagnostic that can move a verdict is not a diagnostic.
    """
    assert_lock_unchanged(lock, lock_digest)
    if prediction_receipt.get("state") != "PREDICTION_SEALED":
        raise EvaluationError(
            "Stage E cannot begin before the prediction stream is sealed "
            f"(receipt state {prediction_receipt.get('state')!r})"
        )
    if prediction_receipt.get("lock_digest") != lock_digest:
        raise EvaluationError("the prediction receipt is bound to a different lock")
    recomputed = canonical_digest(
        {k: v for k, v in prediction_receipt.items() if k != "receipt_digest"}
    )
    if recomputed != prediction_receipt.get("receipt_digest"):
        raise EvaluationError("the Stage P receipt does not verify")
    if canonical_digest(list(sealed_members)) != prediction_receipt["stream_digest"]:
        raise EvaluationError(
            "the supplied predictions are not the sealed prediction stream"
        )
    lifecycle.assert_stage_e_scope(lock["stage_e_read_classes"])
    lifecycle.assert_stage_e_import_is_parser_free(loaded_module_names)

    before = prediction_receipt["ordinal"]
    after = lifecycle.next_ordinal("PREDICTION_SEALED", "LABELS_OPENED", before)
    lifecycle.assert_ordinal_succession(before, after)

    missing = sorted({m["case_id"] for m in sealed_members} - set(labels))
    if missing:
        raise EvaluationError(f"no label for sealed prediction(s): {missing}")

    residual_mismatches: dict[str, int] = {s: 0 for s in ZERO_ERROR_RESIDUAL_STRATA}
    pinned_mismatches: dict[str, int] = {g: 0 for g in PINNED_ZERO_ERROR_GATES}
    presence_pairs: list[tuple[str, str]] = []
    eligible = 0

    for member in sealed_members:
        case_id = member["case_id"]
        label = labels[case_id]
        prediction = member["prediction"]
        if label.get("eligible") is not True:
            raise EvaluationError(
                f"sealed case {case_id!r} is marked ineligible at scoring time. "
                "Construction admits only mandatory, eligible cases, so there is "
                "no legitimate reason to drop one here -- and a scorer that can "
                "shrink its own denominator can turn a failing run into a "
                "passing one."
            )
        eligible += 1
        truth_class = _presence_class(label)
        predicted_class = _presence_class(prediction)
        presence_pairs.append((truth_class, predicted_class))

        mismatched = False
        if predicted_class != truth_class:
            pinned_mismatches["answer_presence_class_exact"] += 1
            mismatched = True
        if prediction.get("canonical_value") != label.get("canonical_value"):
            pinned_mismatches["canonical_present_value_exact"] += 1
            mismatched = True
        if truth_class == "no_answer" and predicted_class == "present":
            pinned_mismatches["no_answer_not_fabricated"] += 1
            mismatched = True
        if truth_class == "ambiguous" and predicted_class != "ambiguous":
            pinned_mismatches["ambiguity_not_resolved_silently"] += 1
            mismatched = True

        stratum = strata.get(case_id)
        if stratum is None:
            raise EvaluationError(f"case {case_id!r} has no stratum assignment")
        if mismatched and stratum in residual_mismatches:
            residual_mismatches[stratum] += 1

    pooled_residual = sum(residual_mismatches.values())
    binding_gates = {
        "residual_pooled_zero_error": pooled_residual == 0,
        **{
            f"residual_{stratum}_zero_error": count == 0
            for stratum, count in residual_mismatches.items()
        },
        **{gate: count == 0 for gate, count in pinned_mismatches.items()},
    }

    if parser_v2_comparison not in PARSER_V2_COMPARISON_STATES:
        raise EvaluationError(
            f"parser-v2 comparison {parser_v2_comparison!r} is not one of "
            f"{sorted(PARSER_V2_COMPARISON_STATES)}"
        )

    status = "PASS" if all(binding_gates.values()) else "FAIL"
    lifecycle.assert_status_is_exclusive(
        binding_gate_results=binding_gates, declared_status=status
    )

    matrix = _confusion_matrix(presence_pairs)
    per_class = _per_class_metrics(matrix)
    macro_f1 = sum(m["f1"] for m in per_class.values()) / len(ANSWER_PRESENCE_CLASSES)
    diagnostics = {
        "answer_presence_confusion_matrix": matrix,
        "per_class_precision": {k: v["precision"] for k, v in per_class.items()},
        "per_class_recall": {k: v["recall"] for k, v in per_class.items()},
        "per_class_f1": {k: v["f1"] for k, v in per_class.items()},
        "macro_f1": macro_f1,
        "parser_v2_comparison": parser_v2_comparison,
        "note": (
            "Class metrics can hide wrong canonical present values: a run may "
            "classify presence correctly and still return the wrong answer."
        ),
    }
    lifecycle.assert_report_only_metrics_cannot_reach_status(
        binding_gate_names=binding_gates,
        report_only_metric_names=NONBINDING_DIAGNOSTICS,
    )

    terminal = "EVALUATED_ACCEPTED" if status == "PASS" else "EVALUATED_NOT_ACCEPTED"
    lifecycle.assert_transition_permitted("LABELS_OPENED", terminal)

    result = {
        "schema_version": "phase1-parser-v3-v2-formal-result/v1",
        "state": terminal,
        "ordinal": after,
        "lock_digest": lock_digest,
        "prediction_receipt_digest": prediction_receipt["receipt_digest"],
        "eligible_case_count": eligible,
        "status": status,
        "binding_gates": binding_gates,
        "residual_mismatches": residual_mismatches,
        "pinned_mismatches": pinned_mismatches,
        "nonbinding_diagnostics": diagnostics,
    }
    result["result_digest"] = canonical_digest(result)
    return result
