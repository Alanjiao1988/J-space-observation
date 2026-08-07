"""Model-free tests for the Study 2 canonical protocol and truth tables."""

from __future__ import annotations

import ast
import copy
import json
import math
import sys
from itertools import product
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "jspace_observation"))

import study2_protocol as s2  # noqa: E402

PROTOCOL_PATH = ROOT / "studies/study2/protocol/reasoning_internalization_protocol.json"
SCHEMA_PATH = ROOT / "studies/study2/protocol/reasoning_internalization_protocol.schema.json"
MARKDOWN_PATH = ROOT / "studies/study2/protocol/reasoning_internalization_protocol.md"


@pytest.fixture(scope="module")
def document() -> dict:
    return s2.load_json(PROTOCOL_PATH)


@pytest.fixture(scope="module")
def schema() -> dict:
    return s2.load_json(SCHEMA_PATH)


def test_candidate_protocol_is_canonical_closed_and_model_free(document: dict, schema: dict) -> None:
    loaded = s2.load_and_validate_protocol(ROOT)
    assert loaded == document
    assert PROTOCOL_PATH.read_bytes() == s2.canonical_json_bytes(document)
    s2.verify_schema_closed(schema)
    s2.validate_json_schema(document, schema)
    s2.validate_markdown_crosswalk(MARKDOWN_PATH, document)
    assert document["status"] in {"CANDIDATE_AWAITING_REVIEW", "FROZEN_AWAITING_STAGE_T"}


def test_schema_rejects_every_missing_extra_or_changed_top_level_section(document: dict, schema: dict) -> None:
    for key in document:
        missing = copy.deepcopy(document)
        missing.pop(key)
        with pytest.raises(s2.ProtocolError, match="missing"):
            s2.validate_json_schema(missing, schema)
    extra = copy.deepcopy(document)
    extra["unregistered"] = True
    with pytest.raises(s2.ProtocolError, match="extra"):
        s2.validate_json_schema(extra, schema)
    changed = copy.deepcopy(document)
    changed["metrics"]["behavior"]["nt_point_floor"] = 0.49
    with pytest.raises(s2.ProtocolError, match="const"):
        s2.validate_json_schema(changed, schema)


def test_strict_json_rejects_duplicate_and_nonfinite_values(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"a":1,"a":2}\n', encoding="utf-8")
    with pytest.raises(s2.ProtocolError, match="duplicate"):
        s2.load_json(duplicate)
    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"a":NaN}\n', encoding="utf-8")
    with pytest.raises(s2.ProtocolError, match="non-finite"):
        s2.load_json(nonfinite)
    with pytest.raises(s2.ProtocolError, match="non-finite"):
        s2.canonical_json_bytes({"x": math.inf})


def test_exact_models_revisions_jlens_and_zero_operations(document: dict) -> None:
    observed = tuple((row["role"], row["model_id"], row["revision"]) for row in document["identities"]["models"])
    assert observed == s2.MODEL_IDENTITIES
    assert document["identities"]["jlens"]["commit"] == s2.JLENS_COMMIT
    assert document["identities"]["jlens"]["m1200_seal_sha256"] == s2.M1200_SEAL
    assert tuple(document["classification"]["internal_axis_states"]) == s2.INTERNAL_AXIS_STATES
    assert tuple(document["classification"]["distillation_axis_states"]) == s2.DISTILLATION_AXIS_STATES
    assert tuple(document["classification"]["execution_blocker_reason_codes"]) == s2.EXECUTION_BLOCKER_REASONS
    assert all(value == 0 for value in document["operation_limits"].values())


@pytest.mark.parametrize(
    "relative",
    [
        "src/jspace_observation/study2_protocol.py",
        "src/jspace_observation/study2_task_bank.py",
        "scripts/build_study2_task_bank.py",
        "scripts/validate_study2_protocol.py",
    ],
)
def test_stage_p_source_has_no_forbidden_import_or_provider_path(relative: str) -> None:
    path = ROOT / relative
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert not imports & {
        "torch",
        "transformers",
        "accelerate",
        "safetensors",
        "tokenizers",
        "azure",
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "jlens",
        "jacobian_lens",
    }
    source = path.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "from_pretrained(",
        "autotokenizer",
        "automodelforcausallm",
        "cuda(",
        "semantic_review",
        "phase1_0d_execution",
        "jlens_s3_e0_runtime",
    ):
        assert forbidden not in source


def test_restricted_probabilities_margin_and_exact_tie_order() -> None:
    logits = {label: 0.0 for label in s2.LABELS}
    assert s2.restricted_probabilities(logits) == {label: 0.25 for label in s2.LABELS}
    assert s2.restricted_prediction(logits) == "A"
    logits = {"A": 0.0, "B": 1.0, "C": -1.0, "D": 0.5}
    probabilities = s2.restricted_probabilities(logits)
    assert math.isclose(sum(probabilities.values()), 1.0)
    assert s2.restricted_prediction(logits) == "B"
    assert s2.correct_margin(logits, "B") == 0.5


def test_wilson_and_registered_127_versus_128_cell_gate() -> None:
    lower127, _ = s2.wilson_interval(127, 256)
    lower128, _ = s2.wilson_interval(128, 256)
    assert lower127 > 0.25 and lower128 > 0.25
    assert not s2.nt_pass(n=256, correct=127, margin_lower95=0.01, integrity_complete=True, balance_ok=True)
    assert s2.nt_pass(n=256, correct=128, margin_lower95=0.01, integrity_complete=True, balance_ok=True)
    assert not s2.nt_pass(n=255, correct=200, margin_lower95=0.01, integrity_complete=True, balance_ok=True)
    assert not s2.nt_pass(n=256, correct=200, margin_lower95=0.0, integrity_complete=True, balance_ok=True)


def test_quantile_is_registered_linear_finite_rule() -> None:
    assert s2.finite_quantile([0.0, 10.0], 0.25) == 2.5
    assert s2.finite_quantile([3.0], 0.975) == 3.0
    with pytest.raises(s2.ProtocolError):
        s2.finite_quantile([1.0, float("nan")], 0.5)


def test_trace_effects_and_pt_support_are_hand_calculable() -> None:
    effects = s2.trace_effects(
        nt_correct_probability=0.25,
        pt_correct_probability=0.75,
        nt_counterfactual_probability=0.10,
        wt_counterfactual_probability=0.60,
        st_correct_probability=0.40,
    )
    assert effects == {
        "TRACE_GAIN": 0.5,
        "WRONG_TRACE_PULL": 0.5,
        "SHUFFLE_DAMAGE": 0.35,
    }
    assert s2.pt_support(
        depth=3,
        n=256,
        correct=128,
        trace_gain_lower95=0.01,
        wrong_trace_pull_lower95=0.01,
        shuffle_damage_lower95=0.01,
        integrity_complete=True,
    )
    assert not s2.pt_support(
        depth=3,
        n=256,
        correct=128,
        trace_gain_lower95=0.01,
        wrong_trace_pull_lower95=0.01,
        shuffle_damage_lower95=0.0,
        integrity_complete=True,
    )


def test_paired_bootstrap_constant_difference_has_exact_interval() -> None:
    replicates = s2.paired_bootstrap_mean_differences(
        [2.0, 3.0, 4.0],
        [1.0, 2.0, 3.0],
        seed=s2.SEEDS["bootstrap"],
        domain="hand-calculated-constant-difference",
        replicates=17,
    )
    assert replicates == [1.0] * 17
    assert s2.finite_quantile(replicates, 0.025) == 1.0
    assert s2.finite_quantile(replicates, 0.975) == 1.0


@pytest.mark.parametrize(
    ("d2", "d3", "expected"),
    [(False, False, None), (True, False, 2), (False, True, 3), (True, True, 3)],
)
def test_mechanistic_cell_precedence(d2: bool, d3: bool, expected: int | None) -> None:
    assert s2.select_mechanistic_depth(d2, d3) == expected


def test_window_selection_uses_three_layers_and_lowest_exact_tie() -> None:
    flat = {layer: 1.0 for layer in range(9, 23)}
    assert s2.select_window(flat) == (9, 10, 11)
    peaked = {layer: 0.0 for layer in range(9, 23)}
    peaked.update({15: 2.0, 16: 2.0, 17: 2.0})
    assert s2.select_window(peaked) == (15, 16, 17)


def test_hand_calculated_gx_gd_distinguishes_recombination_and_copy() -> None:
    clean = {"A": 0.0, "B": 2.0, "C": 1.0, "D": -1.0}
    recombinant = {"A": 0.0, "B": 1.0, "C": 4.0, "D": -1.0}
    gx, gd = s2.gx_gd(clean=clean, patched=recombinant, a_x="C", a_d="A", a_r="B")
    assert gx == 4.0
    assert gd == 1.0
    donor_copy = {"A": 5.0, "B": 1.0, "C": 1.0, "D": -1.0}
    copy_gx, copy_gd = s2.gx_gd(clean=clean, patched=donor_copy, a_x="C", a_d="A", a_r="B")
    assert copy_gd > copy_gx
    noop_gx, noop_gd = s2.gx_gd(clean=clean, patched=clean, a_x="C", a_d="A", a_r="B")
    assert noop_gx == noop_gd == 0.0
    random_control = {"A": 0.5, "B": 2.0, "C": 1.5, "D": -1.0}
    random_gx, _ = s2.gx_gd(clean=clean, patched=random_control, a_x="C", a_d="A", a_r="B")
    assert gx > random_gx


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"operationally_complete": False, "integrity_ok": True, "internal_families": 2, "distillation_stronger_than_both": True, "nt_compositional_families": 2, "pt_support_families": 2, "nt_depth1_any": True}, "STUDY2_RESULT_NOT_ESTIMABLE"),
        ({"operationally_complete": True, "integrity_ok": True, "internal_families": 2, "distillation_stronger_than_both": True, "nt_compositional_families": 2, "pt_support_families": 0, "nt_depth1_any": True}, "STUDY2_DISTILLATION_ASSOCIATED_CAUSAL_INTERNAL_REASONING_SUPPORTED"),
        ({"operationally_complete": True, "integrity_ok": True, "internal_families": 2, "distillation_stronger_than_both": False, "nt_compositional_families": 2, "pt_support_families": 0, "nt_depth1_any": True}, "STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_WITHOUT_DISTILLATION_ATTRIBUTION"),
        ({"operationally_complete": True, "integrity_ok": True, "internal_families": 1, "distillation_stronger_than_both": False, "nt_compositional_families": 1, "pt_support_families": 0, "nt_depth1_any": True}, "STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_ONE_FAMILY_ONLY"),
        ({"operationally_complete": True, "integrity_ok": True, "internal_families": 0, "distillation_stronger_than_both": False, "nt_compositional_families": 1, "pt_support_families": 2, "nt_depth1_any": True}, "STUDY2_BEHAVIOR_ONLY_WITHOUT_CAUSAL_SUPPORT"),
        ({"operationally_complete": True, "integrity_ok": True, "internal_families": 0, "distillation_stronger_than_both": False, "nt_compositional_families": 0, "pt_support_families": 2, "nt_depth1_any": False}, "STUDY2_EXTERNAL_TRACE_DEPENDENCE_ONLY"),
        ({"operationally_complete": True, "integrity_ok": True, "internal_families": 0, "distillation_stronger_than_both": False, "nt_compositional_families": 0, "pt_support_families": 1, "nt_depth1_any": False}, "STUDY2_EXTERNAL_TRACE_SUPPORT_ONE_FAMILY_ONLY"),
        ({"operationally_complete": True, "integrity_ok": True, "internal_families": 0, "distillation_stronger_than_both": False, "nt_compositional_families": 0, "pt_support_families": 0, "nt_depth1_any": True}, "STUDY2_NO_COMPOSITIONAL_BEHAVIORAL_SUPPORT"),
        ({"operationally_complete": True, "integrity_ok": True, "internal_families": 0, "distillation_stronger_than_both": False, "nt_compositional_families": 0, "pt_support_families": 0, "nt_depth1_any": False}, "STUDY2_TASK_INTERFACE_UNQUALIFIED"),
    ],
)
def test_composite_truth_table_is_closed(kwargs: dict, expected: str) -> None:
    assert s2.classify_composite(**kwargs) == expected
    assert expected in s2.SCIENTIFIC_STATES


@pytest.mark.parametrize(
    ("complete", "integrity", "readout", "causal", "expected"),
    [
        (False, True, True, True, "STUDY2_JLENS_NOT_ESTIMABLE"),
        (True, False, True, True, "STUDY2_JLENS_NOT_VALIDATED"),
        (True, True, True, True, "STUDY2_JLENS_VALIDATED"),
        (True, True, True, False, "STUDY2_JLENS_PARTIAL"),
        (True, True, False, True, "STUDY2_JLENS_PARTIAL"),
        (True, True, False, False, "STUDY2_JLENS_NOT_VALIDATED"),
    ],
)
def test_jlens_axis_is_closed(complete: bool, integrity: bool, readout: bool, causal: bool, expected: str) -> None:
    assert s2.classify_jlens(complete=complete, integrity_ok=integrity, readout_pass=readout, causal_pass=causal) == expected


def test_distillation_axis_is_closed() -> None:
    assert s2.classify_distillation(
        operationally_complete=True,
        target_internal_supported=True,
        stronger_than_both=True,
        contradicted=False,
    ) == "DISTILLATION_ASSOCIATION_STRONGER_THAN_BOTH_CONTROLS"
    assert s2.classify_distillation(
        operationally_complete=True,
        target_internal_supported=True,
        stronger_than_both=False,
        contradicted=True,
    ) == "DISTILLATION_ASSOCIATION_CONTRADICTED"
    assert s2.classify_distillation(
        operationally_complete=True,
        target_internal_supported=True,
        stronger_than_both=False,
        contradicted=False,
    ) == "DISTILLATION_ASSOCIATION_NOT_DISTINGUISHED"
    assert s2.classify_distillation(
        operationally_complete=False,
        target_internal_supported=True,
        stronger_than_both=False,
        contradicted=False,
    ) == "DISTILLATION_ASSOCIATION_NOT_ESTIMABLE"


def test_composite_is_independent_of_every_jlens_axis_state() -> None:
    for internal_families, stronger, jlens_state in product(
        (0, 1, 2),
        (False, True),
        s2.JLENS_STATES,
    ):
        if stronger and internal_families != 2:
            with pytest.raises(s2.ProtocolError):
                s2.classify_composite(
                    operationally_complete=True,
                    integrity_ok=True,
                    internal_families=internal_families,
                    distillation_stronger_than_both=stronger,
                    nt_compositional_families=max(1, internal_families),
                    pt_support_families=0,
                    nt_depth1_any=True,
                )
            continue
        state = s2.classify_composite(
            operationally_complete=True,
            integrity_ok=True,
            internal_families=internal_families,
            distillation_stronger_than_both=stronger,
            nt_compositional_families=max(1, internal_families),
            pt_support_families=0,
            nt_depth1_any=True,
        )
        assert jlens_state in s2.JLENS_STATES
        assert state in s2.SCIENTIFIC_STATES


def test_operational_blocker_cannot_be_synthesized_as_scientific_negative() -> None:
    s2.validate_blocker("BLOCKED_ON_STUDY2_MODEL_IDENTITY")
    s2.validate_blocker("BLOCKED_ON_STUDY2_EXECUTION", "NONFINITE_OUTPUT")
    with pytest.raises(s2.ProtocolError):
        s2.validate_blocker("BLOCKED_ON_STUDY2_EXECUTION", "")
    with pytest.raises(s2.ProtocolError):
        s2.validate_blocker("BLOCKED_ON_STUDY2_EXECUTION", "UNREGISTERED")
    with pytest.raises(s2.ProtocolError):
        s2.validate_blocker("BLOCKED_ON_STUDY2_MODEL_IDENTITY", "HASH_MISMATCH")
    with pytest.raises(s2.ProtocolError):
        s2.validate_blocker("STUDY2_TASK_INTERFACE_UNQUALIFIED")


def test_protocol_contains_all_future_closed_output_rows(document: dict) -> None:
    tables = {row["name"]: row for row in document["output_contract"]["future_tables"]}
    assert set(tables) == {
        "behavioral_row",
        "patch_row",
        "probe_row",
        "jlens_readout_row",
        "jlens_causal_row",
        "classification_row",
    }
    for table in tables.values():
        names = [field.split(":", 1)[0] for field in table["fields"]]
        assert len(names) == len(set(names))
        assert set(table["primary_key"]) <= set(names)
    assert document["output_contract"]["closed_pack"] == {
        "unknown_fields_allowed": False,
        "missing_rows_allowed": False,
        "nonfinite_rows_allowed": False,
        "partial_scientific_classification_allowed": False,
        "manifest_last": True,
        "semantic_interpretation_required": False,
    }


def test_review_allowance_is_exact_and_checklist_has_fifteen_questions(document: dict) -> None:
    review = document["review"]
    assert review["candidate_reviews"] == 1
    assert review["consolidated_corrections"] == 1
    assert review["same_checklist_verifications"] == 1
    assert len(review["checklist"]) == 15
    assert review["status"] in {"UNSPENT", "SPENT_VERIFIED"}
