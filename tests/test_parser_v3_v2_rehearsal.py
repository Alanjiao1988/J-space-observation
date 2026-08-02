"""Public synthetic end-to-end rehearsal of the one-shot evaluation.

Phase A of the controlling protocol requires a full rehearsal through
construction, a fake seal, preregistration, Stage P, prediction sealing and
Stage E, using synthetic public cases and a synthetic parser only. It also
requires the rehearsal to drive the *real* entrypoints, because the defect this
programme exists not to repeat was validating a named definition that the live
job never executed.

Every function called below is the same function the private run calls. The
only synthetic things are the cases, the parser and the storage: no invariant is
stubbed, relaxed or re-implemented for the rehearsal's convenience. A rehearsal
that ran a simplified copy of the pipeline would prove that the copy works.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from jspace_observation import parser_v3_v2_construction as construction
from jspace_observation import parser_v3_v2_evaluation as evaluation
from jspace_observation import parser_v3_v2_lifecycle as lifecycle
from jspace_observation.parser_v3_v2_evaluation import EvaluationError

# ---------------------------------------------------------------------------
# synthetic public material
# ---------------------------------------------------------------------------

_SUBJECTS = ("depot", "harbour", "registry", "warehouse", "terminal")
_OBJECTS = ("consignment", "parcel", "charter", "sailing")
_QUALIFIERS = ("earliest", "shortest", "cheapest", "safest", "latest", "nearest")


def _prompt(index: int) -> str:
    """A digit-free phrasing unique to this case.

    The obvious fixture -- one template plus the case identifier -- is exactly
    what the template-family collision rule exists to reject, and it rejected
    it. Five subjects times four objects times six qualifiers gives 120 distinct
    literal frames, so each case is its own template family.
    """
    qualifier = _QUALIFIERS[index % len(_QUALIFIERS)]
    obj = _OBJECTS[(index // len(_QUALIFIERS)) % len(_OBJECTS)]
    subject = _SUBJECTS[index // (len(_QUALIFIERS) * len(_OBJECTS))]
    return f"the {qualifier} {obj} recorded at the {subject}"


def _case_id(index: int) -> str:
    return f"synthetic-{index:03d}"


def _stratum(index: int) -> str:
    return construction.STRATA[index // construction.STRATUM_QUOTA]


def _decision_class(index: int) -> str:
    if index < construction.DECISION_CLASS_QUOTA["present"]:
        return "present"
    if index < 110:
        return "no_answer"
    return "ambiguous"


def _canonical_value(index: int) -> str | None:
    return f"value-{index:03d}" if _decision_class(index) == "present" else None


def _locked_input(index: int) -> dict[str, Any]:
    """A Stage P input. Deliberately carries no field a scorer would need."""
    return {
        "case_id": _case_id(index),
        "stratum": _stratum(index),
        "prompt": _prompt(index),
        "context": "synthetic public context, held free of any scoring signal",
    }


def _label(index: int) -> dict[str, Any]:
    return {
        "case_id": _case_id(index),
        "eligible": True,
        "answer_presence": _decision_class(index),
        "canonical_value": _canonical_value(index),
    }


def _locked_inputs() -> list[dict[str, Any]]:
    return [_locked_input(index) for index in range(construction.TOTAL_CASES)]


def _labels() -> dict[str, dict[str, Any]]:
    return {_case_id(index): _label(index) for index in range(construction.TOTAL_CASES)}


def _strata() -> dict[str, str]:
    return {_case_id(index): _stratum(index) for index in range(construction.TOTAL_CASES)}


def _perfect_parser(case: dict[str, Any]) -> dict[str, Any]:
    """A synthetic parser that answers every synthetic case correctly.

    It reads only the input it is given. It has no access to the labels, and
    reproduces them only because the synthetic fixture makes them a pure
    function of the case identifier.
    """
    index = int(case["case_id"].rsplit("-", 1)[1])
    return {
        "answer_presence": _decision_class(index),
        "canonical_value": _canonical_value(index),
    }


def _bindings(**overrides: Any) -> dict[str, Any]:
    digest = "0" * 64
    bindings: dict[str, Any] = {
        name: digest for name in evaluation.PREREGISTERED_BINDINGS
    }
    bindings.update(
        {
            "cuda_runtime": None,
            "stage_p_entrypoint": "jspace_observation.parser_v3_v2_evaluation:run_stage_p",
            "stage_p_command": ["python", "-m", "stage_p"],
            "stage_p_identity": "uami-stage-p",
            "stage_p_read_classes": ["locked_inputs", "final_contract", "policy"],
            "stage_e_entrypoint": "jspace_observation.parser_v3_v2_evaluation:run_stage_e",
            "stage_e_command": ["python", "-m", "stage_e"],
            "stage_e_identity": "uami-stage-e",
            "stage_e_read_classes": [
                "scoring_labels",
                "sealed_predictions",
                "policy",
                "set_facts",
                "final_contract",
            ],
            "prediction_member_layout": "one object per case plus a terminal manifest",
            "prediction_completeness_rule": "exact sealed case identifiers, no more, no fewer",
            "prediction_seal_mode": "create_only",
            "prediction_listing_schema": "phase1-prediction-listing/v1",
            "prediction_receipt_schema": "phase1-prediction-receipt/v1",
            "evaluation_ordinal": 0,
            "retry_rule": "infrastructure-only, never after a prediction-bearing write",
            "binding_acceptance_criteria": list(evaluation.PINNED_ZERO_ERROR_GATES),
            "nonbinding_diagnostics": list(evaluation.NONBINDING_DIAGNOSTICS),
            "formal_result_schema": "phase1-parser-v3-v2-formal-result/v1",
            "public_redaction_projection": "aggregate counts only, no case-level errors",
        }
    )
    bindings.update(overrides)
    return bindings


def _write_order(case_ids: list[str]) -> tuple[list[str], str]:
    manifest = "predictions/manifest.json"
    return [f"predictions/{case_id}.json" for case_id in case_ids] + [manifest], manifest


# ---------------------------------------------------------------------------
# the rehearsal
# ---------------------------------------------------------------------------


def _set_case(index: int) -> dict[str, Any]:
    """A construction-shaped case, for driving the real set invariants."""
    case: dict[str, Any] = {
        "case_id": _case_id(index),
        "stratum": _stratum(index),
        "decision_class": _decision_class(index),
        "eligible": True,
        "adjudicable": True,
        "mandatory": True,
        "unresolved": False,
        "subtype_slot": f"slot-{index % 5}",
        "literal_spans": [{"literal": True, "start": 0, "end": 4}],
    }
    if case["stratum"] == "S06":
        case["rightmost_distractor_registration"] = True
    if case["stratum"] == "S11":
        case["ambiguity_registration"] = True
    return case


def _rehearse(
    *,
    parser: Any = _perfect_parser,
    labels: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Drive the whole pipeline once and return every intermediate artefact."""
    inputs = _locked_inputs()
    case_ids = [case["case_id"] for case in inputs]
    labels = labels if labels is not None else _labels()

    construction.assert_final_set_invariants(
        [_set_case(index) for index in range(construction.TOTAL_CASES)]
    )
    construction.assert_no_prohibited_collision(
        set_contents={case["case_id"]: case["prompt"] for case in inputs}
    )

    lock, lock_digest = evaluation.create_preregistration_lock(bindings=_bindings())

    stream = evaluation.run_stage_p(
        lock=lock,
        lock_digest=lock_digest,
        state="PREREGISTERED",
        ordinal=0,
        locked_inputs=inputs,
        parser=parser,
    )
    order, manifest = _write_order(case_ids)
    receipt = evaluation.seal_prediction_stream(
        stream=stream,
        sealed_case_ids=case_ids,
        write_order=order,
        terminal_manifest=manifest,
    )
    result = evaluation.run_stage_e(
        lock=lock,
        lock_digest=lock_digest,
        prediction_receipt=receipt,
        sealed_members=stream["members"],
        labels=labels,
        strata=_strata(),
    )
    return {
        "inputs": inputs,
        "case_ids": case_ids,
        "lock": lock,
        "lock_digest": lock_digest,
        "stream": stream,
        "receipt": receipt,
        "result": result,
        "write_order": order,
        "terminal_manifest": manifest,
    }


class TestEndToEndRehearsal:
    def test_the_whole_pipeline_runs_once_and_produces_one_result(self) -> None:
        run = _rehearse()
        assert run["stream"]["state"] == "PREDICTION_RUNNING"
        assert run["receipt"]["state"] == "PREDICTION_SEALED"
        assert run["receipt"]["member_count"] == construction.TOTAL_CASES
        assert run["result"]["state"] == "EVALUATED_ACCEPTED"
        assert run["result"]["status"] == "PASS"
        assert run["result"]["ordinal"] == 1
        assert run["result"]["eligible_case_count"] == construction.TOTAL_CASES

    def test_the_result_is_bound_to_the_lock_and_the_prediction_seal(self) -> None:
        run = _rehearse()
        assert run["result"]["lock_digest"] == run["lock_digest"]
        assert (
            run["result"]["prediction_receipt_digest"]
            == run["receipt"]["receipt_digest"]
        )

    def test_one_eligible_mismatch_produces_fail_not_a_review(self) -> None:
        def one_wrong(case: dict[str, Any]) -> dict[str, Any]:
            prediction = _perfect_parser(case)
            if case["case_id"] == _case_id(0):
                prediction["canonical_value"] = "wrong"
            return prediction

        run = _rehearse(parser=one_wrong)
        assert run["result"]["status"] == "FAIL"
        assert run["result"]["state"] == "EVALUATED_NOT_ACCEPTED"
        assert run["result"]["pinned_mismatches"]["canonical_present_value_exact"] == 1


class TestStagePCannotReachLabels:
    def test_a_label_bearing_input_is_refused_before_the_parser_runs(self) -> None:
        inputs = _locked_inputs()
        inputs[7]["gold_answer"] = "leaked"
        calls: list[str] = []

        def counting_parser(case: dict[str, Any]) -> dict[str, Any]:
            calls.append(case["case_id"])
            return _perfect_parser(case)

        lock, digest = evaluation.create_preregistration_lock(bindings=_bindings())
        with pytest.raises(EvaluationError, match="label-bearing field"):
            evaluation.run_stage_p(
                lock=lock,
                lock_digest=digest,
                state="PREREGISTERED",
                ordinal=0,
                locked_inputs=inputs,
                parser=counting_parser,
            )
        assert calls == [], "the parser ran before the label check refused the payload"

    def test_a_stage_p_scope_that_requests_labels_is_refused(self) -> None:
        bindings = _bindings(
            stage_p_read_classes=["locked_inputs", "scoring_labels"]
        )
        lock, digest = evaluation.create_preregistration_lock(bindings=bindings)
        with pytest.raises(lifecycle.LifecycleError):
            evaluation.run_stage_p(
                lock=lock,
                lock_digest=digest,
                state="PREREGISTERED",
                ordinal=0,
                locked_inputs=_locked_inputs(),
                parser=_perfect_parser,
            )

    def test_a_stage_p_process_holding_comparator_code_is_refused(self) -> None:
        lock, digest = evaluation.create_preregistration_lock(bindings=_bindings())
        with pytest.raises(EvaluationError, match="scoring-bearing module"):
            evaluation.run_stage_p(
                lock=lock,
                lock_digest=digest,
                state="PREREGISTERED",
                ordinal=0,
                locked_inputs=_locked_inputs(),
                parser=_perfect_parser,
                loaded_module_names=["json", "jspace_observation.answer_comparator"],
            )

    def test_the_label_check_reaches_a_nested_field(self) -> None:
        payload = {"outer": [{"inner": {"ground_truth": "x"}}]}
        with pytest.raises(EvaluationError, match=r"outer\[0\]\.inner\.ground_truth"):
            evaluation.assert_stage_p_payload_carries_no_label(payload)

    def test_every_registered_label_marker_is_actually_detected(self) -> None:
        """Mutation control: a marker nobody checks protects nothing."""
        for marker in evaluation.LABEL_BEARING_FIELDS:
            with pytest.raises(EvaluationError):
                evaluation.assert_stage_p_payload_carries_no_label({marker: "x"})


class TestPredictionSeal:
    def test_a_partial_stream_cannot_seal(self) -> None:
        run_inputs = _locked_inputs()
        lock, digest = evaluation.create_preregistration_lock(bindings=_bindings())
        stream = evaluation.run_stage_p(
            lock=lock,
            lock_digest=digest,
            state="PREREGISTERED",
            ordinal=0,
            locked_inputs=run_inputs,
            parser=_perfect_parser,
        )
        truncated = dict(stream)
        truncated["members"] = stream["members"][:-1]
        case_ids = [case["case_id"] for case in run_inputs]
        order, manifest = _write_order(case_ids)
        with pytest.raises(lifecycle.LifecycleError):
            evaluation.seal_prediction_stream(
                stream=truncated,
                sealed_case_ids=case_ids,
                write_order=order,
                terminal_manifest=manifest,
            )

    def test_a_duplicated_stream_cannot_seal(self) -> None:
        run = _rehearse()
        duplicated = dict(run["stream"])
        duplicated["members"] = list(run["stream"]["members"])
        duplicated["members"][1] = duplicated["members"][0]
        with pytest.raises(lifecycle.LifecycleError):
            evaluation.seal_prediction_stream(
                stream=duplicated,
                sealed_case_ids=run["case_ids"],
                write_order=run["write_order"],
                terminal_manifest=run["terminal_manifest"],
            )

    def test_sealing_into_a_non_empty_namespace_is_refused(self) -> None:
        run = _rehearse()
        with pytest.raises(lifecycle.LifecycleError, match="create-only"):
            evaluation.seal_prediction_stream(
                stream=run["stream"],
                sealed_case_ids=run["case_ids"],
                write_order=run["write_order"],
                terminal_manifest=run["terminal_manifest"],
                existing_objects=[run["write_order"][0]],
            )

    def test_a_manifest_written_first_is_refused(self) -> None:
        run = _rehearse()
        reordered = [run["terminal_manifest"]] + run["write_order"][:-1]
        with pytest.raises(lifecycle.LifecycleError, match="written last"):
            evaluation.seal_prediction_stream(
                stream=run["stream"],
                sealed_case_ids=run["case_ids"],
                write_order=reordered,
                terminal_manifest=run["terminal_manifest"],
            )


class TestStageEOrdering:
    def test_stage_e_cannot_start_before_the_prediction_seal(self) -> None:
        run = _rehearse()
        unsealed = dict(run["receipt"])
        unsealed["state"] = "PREDICTION_RUNNING"
        with pytest.raises(EvaluationError, match="before the prediction stream is sealed"):
            evaluation.run_stage_e(
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                prediction_receipt=unsealed,
                sealed_members=run["stream"]["members"],
                labels=_labels(),
                strata=_strata(),
            )

    def test_stage_e_refuses_predictions_that_are_not_the_sealed_stream(self) -> None:
        run = _rehearse()
        swapped = copy.deepcopy(run["stream"]["members"])
        swapped[0]["prediction"]["canonical_value"] = "substituted after sealing"
        with pytest.raises(EvaluationError, match="not the sealed prediction stream"):
            evaluation.run_stage_e(
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                prediction_receipt=run["receipt"],
                sealed_members=swapped,
                labels=_labels(),
                strata=_strata(),
            )

    def test_stage_e_refuses_a_forged_receipt(self) -> None:
        run = _rehearse()
        forged = dict(run["receipt"])
        forged["member_count"] = 1
        with pytest.raises(EvaluationError, match="does not verify"):
            evaluation.run_stage_e(
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                prediction_receipt=forged,
                sealed_members=run["stream"]["members"],
                labels=_labels(),
                strata=_strata(),
            )

    def test_stage_e_holding_parser_code_is_refused(self) -> None:
        run = _rehearse()
        with pytest.raises(lifecycle.LifecycleError, match="parser-bearing module"):
            evaluation.run_stage_e(
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                prediction_receipt=run["receipt"],
                sealed_members=run["stream"]["members"],
                labels=_labels(),
                strata=_strata(),
                loaded_module_names=["jspace_observation.eval_parsing"],
            )

    def test_the_ordinal_advances_exactly_once(self) -> None:
        run = _rehearse()
        assert run["result"]["ordinal"] == lifecycle.MAX_FORMAL_EVALUATION_ORDINAL
        with pytest.raises(lifecycle.LifecycleError):
            lifecycle.assert_ordinal_succession(
                run["result"]["ordinal"], run["result"]["ordinal"] + 1
            )


class TestResidualRule:
    def test_a_single_residual_stratum_error_fails_pooled_and_per_stratum(self) -> None:
        residual_index = construction.STRATA.index("S04") * construction.STRATUM_QUOTA

        def wrong_in_s04(case: dict[str, Any]) -> dict[str, Any]:
            prediction = _perfect_parser(case)
            if case["case_id"] == _case_id(residual_index):
                prediction["canonical_value"] = "wrong"
            return prediction

        run = _rehearse(parser=wrong_in_s04)
        gates = run["result"]["binding_gates"]
        assert gates["residual_pooled_zero_error"] is False
        assert gates["residual_S04_zero_error"] is False
        assert gates["residual_S05_zero_error"] is True
        assert run["result"]["status"] == "FAIL"

    def test_every_residual_stratum_has_its_own_gate(self) -> None:
        run = _rehearse()
        for stratum in evaluation.ZERO_ERROR_RESIDUAL_STRATA:
            assert f"residual_{stratum}_zero_error" in run["result"]["binding_gates"]

    def test_an_ineligible_label_is_refused_rather_than_skipped(self) -> None:
        """A scorer that can drop a case can pass a run that should fail.

        Construction admits only mandatory, eligible cases, so an ineligible
        label at scoring time is a contradiction, not a filter. Refusing it
        closes the one path by which the 120-case denominator could shrink
        after the predictions were sealed.
        """
        labels = _labels()
        labels[_case_id(3)]["eligible"] = False
        with pytest.raises(EvaluationError, match="ineligible at scoring time"):
            _rehearse(labels=labels)


class TestDiagnosticsAreInert:
    def test_report_only_names_never_overlap_the_binding_gates(self) -> None:
        run = _rehearse()
        overlap = set(evaluation.NONBINDING_DIAGNOSTICS) & set(
            run["result"]["binding_gates"]
        )
        assert overlap == set()

    def test_a_perfect_macro_f1_cannot_rescue_a_failing_gate(self) -> None:
        """Presence can be perfect while the canonical value is wrong."""

        def right_class_wrong_value(case: dict[str, Any]) -> dict[str, Any]:
            prediction = _perfect_parser(case)
            if prediction["canonical_value"] is not None:
                prediction["canonical_value"] = "wrong"
            return prediction

        run = _rehearse(parser=right_class_wrong_value)
        diagnostics = run["result"]["nonbinding_diagnostics"]
        assert diagnostics["macro_f1"] == pytest.approx(1.0)
        assert run["result"]["status"] == "FAIL"

    def test_the_parser_v2_comparison_is_confined_to_three_values(self) -> None:
        run = _rehearse()
        assert (
            run["result"]["nonbinding_diagnostics"]["parser_v2_comparison"] == "NOT_RUN"
        )
        with pytest.raises(EvaluationError, match="not one of"):
            evaluation.run_stage_e(
                lock=run["lock"],
                lock_digest=run["lock_digest"],
                prediction_receipt=run["receipt"],
                sealed_members=run["stream"]["members"],
                labels=_labels(),
                strata=_strata(),
                parser_v2_comparison="BETTER_THAN_V2",
            )


class TestPreregistrationLock:
    def test_the_lock_is_create_only(self) -> None:
        with pytest.raises(EvaluationError, match="already exists"):
            evaluation.create_preregistration_lock(
                bindings=_bindings(), existing_lock_digest="a" * 64
            )

    def test_a_missing_binding_is_refused(self) -> None:
        bindings = _bindings()
        del bindings["scorer_digest"]
        with pytest.raises(EvaluationError, match="missing bindings"):
            evaluation.create_preregistration_lock(bindings=bindings)

    def test_an_unregistered_binding_is_refused(self) -> None:
        bindings = _bindings()
        bindings["convenient_extra_knob"] = "yes"
        with pytest.raises(EvaluationError, match="unknown bindings"):
            evaluation.create_preregistration_lock(bindings=bindings)

    def test_a_bound_byte_moving_after_creation_is_detected(self) -> None:
        lock, digest = evaluation.create_preregistration_lock(bindings=_bindings())
        mutated = dict(lock)
        mutated["parser_v3_digest"] = "f" * 64
        with pytest.raises(EvaluationError, match="changed after creation"):
            evaluation.assert_lock_unchanged(mutated, digest)

    def test_a_lock_that_does_not_preregister_ordinal_zero_is_refused(self) -> None:
        with pytest.raises(EvaluationError, match="ordinal 0"):
            evaluation.create_preregistration_lock(
                bindings=_bindings(evaluation_ordinal=1)
            )

    def test_a_lock_that_weakens_the_seal_mode_is_refused(self) -> None:
        with pytest.raises(EvaluationError, match="create_only"):
            evaluation.create_preregistration_lock(
                bindings=_bindings(prediction_seal_mode="overwrite_if_present")
            )

    def test_a_lock_that_drops_a_diagnostic_is_refused(self) -> None:
        with pytest.raises(EvaluationError, match="nonbinding diagnostics"):
            evaluation.create_preregistration_lock(
                bindings=_bindings(nonbinding_diagnostics=["macro_f1"])
            )
