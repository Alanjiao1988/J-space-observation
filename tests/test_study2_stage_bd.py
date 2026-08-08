"""Study 2 Stage B-D focused tests.

Everything here runs without a model, without weights and without a network.
The fake-model fixtures produce deterministic logits so the *registered*
calculations are exercised on known answers, and the adversarial cases prove the
closed implementation rejects the failure modes the operator authority names.

No test in this file may create a scientific evidence row, open a
behavioral-confirmation behavioral object, or make a claim about the target
model.  Gate A is a feasibility decision about the frozen interface only.
"""

from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "jspace_observation"))

import study2_protocol as s2  # noqa: E402
import study2_stage_bd as bd  # noqa: E402

SCHEMA_PATH = ROOT / "studies/study2/protocol/stage_bd_pack.schema.json"


# --------------------------------------------------------------------------
# fixtures: a fake model whose outcome is fixed by content, never by accuracy
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def items() -> list[dict]:
    return bd.load_development_bank(ROOT)


@pytest.fixture(scope="module")
def by_id(items) -> dict:
    return {item["item_id"]: item for item in items}


@pytest.fixture(scope="module")
def index() -> dict:
    return bd.load_stage_t_development_index(ROOT)


@pytest.fixture(scope="module")
def tokens(index) -> dict:
    return bd.option_token_ids(index)


@pytest.fixture(scope="module")
def manifest(items) -> dict:
    return bd.build_shard_manifest(items)


@pytest.fixture(scope="module")
def identities() -> dict:
    return {
        role: {"model_id": model_id, "resolved_revision": revision}
        for role, model_id, revision in s2.MODEL_IDENTITIES
    }


def _logits(correct_label: str, *, hit: bool) -> dict[str, float]:
    values = {"A": 0.5, "B": 0.25, "C": 0.125, "D": 0.0625}
    wrong = next(label for label in s2.LABELS if label != correct_label)
    values[correct_label if hit else wrong] = 4.0
    return values


def _hit(role: str, item_id: str, arm: str, threshold: int) -> bool:
    digest = bd.sha256_text(f"{role}{item_id}{arm}")
    return int(digest[:2], 16) < (threshold if role == "target" else 128)


def _pack(items, by_id, index, tokens, manifest, identities, threshold=220):
    shards: dict[str, list[dict]] = {shard["shard_id"]: [] for shard in manifest["shards"]}
    for role, item_id, arm in bd.expected_row_keys(items):
        item = by_id[item_id]
        shards[bd.shard_id(role, item["family"], item["depth"])].append(
            bd.behavioral_row(
                item=item,
                role=role,
                arm=arm,
                identity=identities[role],
                prompt_identity=index[(role, item_id, arm)],
                tokens=tokens,
                option_logits=_logits(
                    item["correct_label"], hit=_hit(role, item_id, arm, threshold)
                ),
                option_ranks=[1, 2, 3, 4],
                top1_token_id=tokens["A"],
            )
        )
    return shards


@pytest.fixture(scope="module")
def shards(items, by_id, index, tokens, manifest, identities) -> dict:
    return _pack(items, by_id, index, tokens, manifest, identities)


@pytest.fixture(scope="module")
def rows(shards, manifest) -> list[dict]:
    return bd.merge_shard_rows(shards, manifest)


# --------------------------------------------------------------------------
# frozen inputs, contract shape and row-space completeness
# --------------------------------------------------------------------------


def test_frozen_inputs_match_the_registered_manifest() -> None:
    verified = bd.verify_frozen_inputs(ROOT)
    assert bd.AUTHORITY_PATH in verified
    assert verified[bd.AUTHORITY_PATH]["sha256"] == bd.AUTHORITY_SHA256
    assert verified[bd.AUTHORITY_PATH]["bytes"] == bd.AUTHORITY_BYTES


def test_row_space_is_exactly_the_registered_size(items, index) -> None:
    assert len(items) == bd.DEVELOPMENT_ITEMS == 384
    keys = bd.expected_row_keys(items)
    assert len(keys) == bd.TOTAL_ROWS == 3072
    assert len({key for key in keys if key[0] == "target"}) == bd.ROWS_PER_MODEL == 1024
    assert set(keys) == set(index)


def test_arm_applicability_is_exactly_the_frozen_depth_rule(items) -> None:
    seen: dict[int, set[str]] = {}
    for item in items:
        seen.setdefault(item["depth"], set()).update(bd.item_arms(item))
    assert seen == {1: {"NT"}, 2: {"NT", "PT", "WT"}, 3: {"NT", "PT", "WT", "ST"}}


def test_behavioral_row_field_set_is_the_frozen_future_table_contract(rows) -> None:
    frozen = json.loads(
        (ROOT / "studies/study2/protocol/reasoning_internalization_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    table = next(
        entry
        for entry in frozen["output_contract"]["future_tables"]
        if entry["name"] == "behavioral_row"
    )
    declared = {field.split(":", 1)[0] for field in table["fields"]}
    assert declared == bd.BEHAVIORAL_ROW_KEYS
    assert set(rows[0]) == bd.BEHAVIORAL_ROW_KEYS
    assert table["primary_key"] == ["run_id", "model_role", "item_id", "arm"]

    gate_table = next(
        entry
        for entry in frozen["output_contract"]["future_tables"]
        if entry["name"] == "feasibility_gate_row"
    )
    gate_declared = {field.split(":", 1)[0] for field in gate_table["fields"]}
    gate = bd.gate_a(rows, bd.load_development_bank(ROOT))
    assert set(gate["feasibility_rows"][0]) == gate_declared
    assert gate_table["primary_key"] == ["run_id", "model_role", "family"]


def test_rows_carry_no_mutable_timestamp_or_cloud_identifier(rows) -> None:
    banned = ("timestamp", "created", "job", "run_name", "correlation", "trace")
    assert not [key for key in bd.BEHAVIORAL_ROW_KEYS if key.startswith(banned)]
    assert {row["run_id"] for row in rows} == {bd.RUN_ID}


# --------------------------------------------------------------------------
# registered calculations, on fake outputs
# --------------------------------------------------------------------------


def test_final_position_and_mask_are_padding_invariant() -> None:
    assert bd.final_position(5, 5, left_padded=False) == 4
    assert bd.final_position(5, 9, left_padded=False) == 4
    assert bd.final_position(5, 9, left_padded=True) == 8
    assert bd.attention_mask(3, 5, left_padded=True) == [0, 0, 1, 1, 1]
    assert bd.attention_mask(3, 5, left_padded=False) == [1, 1, 1, 0, 0]
    assert bd.position_ids([0, 0, 1, 1, 1]) == [0, 0, 0, 1, 2]
    assert bd.position_ids([1, 1, 1, 0, 0]) == [0, 1, 2, 2, 2]
    with pytest.raises(bd.StageBDError):
        bd.final_position(6, 5, left_padded=True)


def test_batch_and_single_evaluation_are_identical(tokens) -> None:
    vocab = max(tokens.values()) + 3
    single = [[0.0] * vocab for _ in range(4)]
    single[3][tokens["C"]] = 2.0
    pad = [[9.9] * vocab for _ in range(2)]

    alone = bd.read_option_logits(single, input_length=4, tokens=tokens, left_padded=False)
    left = bd.read_option_logits(
        pad + single, input_length=4, tokens=tokens, left_padded=True
    )
    right = bd.read_option_logits(
        single + pad, input_length=4, tokens=tokens, left_padded=False
    )
    assert alone == left == right
    assert alone[0]["C"] == 2.0


def test_only_the_final_position_is_ever_read(tokens) -> None:
    vocab = max(tokens.values()) + 3
    rows_logits = [[0.0] * vocab for _ in range(3)]
    rows_logits[0][tokens["A"]] = 99.0
    rows_logits[2][tokens["D"]] = 1.0
    logits, _, _ = bd.read_option_logits(
        rows_logits, input_length=3, tokens=tokens, left_padded=False
    )
    assert logits["A"] == 0.0 and logits["D"] == 1.0


def test_exact_tie_resolves_in_registered_label_order() -> None:
    tie = {label: 1.0 for label in s2.LABELS}
    assert s2.restricted_prediction(tie) == "A"
    assert s2.restricted_prediction({"A": 0.0, "B": 1.0, "C": 1.0, "D": 0.0}) == "B"
    assert s2.restricted_prediction({"A": 0.0, "B": 0.0, "C": 1.0, "D": 1.0}) == "C"


def test_restricted_softmax_is_shift_stable_and_normalised() -> None:
    base = {"A": 800.0, "B": 799.0, "C": 798.0, "D": 797.0}
    shifted = {label: value - 800.0 for label, value in base.items()}
    first = s2.restricted_probabilities(base)
    second = s2.restricted_probabilities(shifted)
    assert math.isclose(math.fsum(first.values()), 1.0, rel_tol=0, abs_tol=1e-12)
    for label in s2.LABELS:
        assert math.isclose(first[label], second[label], rel_tol=1e-12)
        assert math.isfinite(first[label])


def test_correct_margin_is_correct_minus_best_incorrect() -> None:
    values = {"A": 2.0, "B": 3.5, "C": -1.0, "D": 0.25}
    assert s2.correct_margin(values, "A") == pytest.approx(2.0 - 3.5)
    assert s2.correct_margin(values, "B") == pytest.approx(3.5 - 2.0)


def test_full_vocabulary_diagnostics_are_ranks_and_top1(tokens) -> None:
    vocab = [0.0] * (max(tokens.values()) + 5)
    vocab[tokens["A"]] = 1.0
    vocab[tokens["B"]] = 3.0
    vocab[tokens["C"]] = 2.0
    vocab[tokens["D"]] = -1.0
    vocab[0] = 5.0
    ranks, top1 = bd.full_vocab_ranks(vocab, tokens)
    # 5.0 sits at index 0, then B=3.0, C=2.0, A=1.0, the zero block, then D=-1.0.
    assert ranks == [4, 2, 3, len(vocab)]
    assert ranks[1] < ranks[2] < ranks[0] < ranks[3]
    assert top1 == 0


def test_wilson_interval_and_exact_binomial_tail_are_registered_values() -> None:
    lower, upper = s2.wilson_interval(43, 128)
    assert 0.0 < lower < 43 / 128 < upper < 1.0
    assert s2.binomial_upper_tail(128, 0.25, 43) == pytest.approx(0.018218515933, abs=1e-12)
    assert s2.binomial_upper_tail(128, 0.25, 42) == pytest.approx(0.028760674518, abs=1e-12)


def test_bootstrap_is_deterministic_ten_thousand_replicate_paired(rows, by_id) -> None:
    first = bd.bootstrap_diagnostics(rows[:0] or rows, by_id)
    second = bd.bootstrap_diagnostics(rows, by_id)
    assert first == second
    assert {row["replicates"] for row in first} == {10_000}
    assert {row["schema_version"] for row in first} == {bd.BOOTSTRAP_ROW_VERSION}
    for row in first:
        assert row["bootstrap_lower_95"] <= row["bootstrap_upper_95"]
        assert math.isfinite(row["observed"])


def test_bootstrap_quantiles_use_the_registered_interpolation() -> None:
    ordered = [float(value) for value in range(1, 101)]
    assert s2.finite_quantile(ordered, 0.025) == pytest.approx(
        ordered[2] + 0.475 * (ordered[3] - ordered[2])
    )
    assert s2.finite_quantile(ordered, 0.975) == pytest.approx(
        ordered[96] + 0.525 * (ordered[97] - ordered[96])
    )


def test_summaries_cover_every_registered_cell(rows) -> None:
    summaries = bd.summarize(rows)
    assert len(summaries) == 96
    assert sum(row["n"] for row in summaries) == bd.TOTAL_ROWS
    for row in summaries:
        assert row["finite_rows"] == row["execution_complete"] == row["n"]
        assert 0.0 <= row["wilson_lower_95"] <= row["restricted_accuracy"] <= row["wilson_upper_95"]
        assert row["n"] == 32


# --------------------------------------------------------------------------
# Gate A: target-only, no rescue, exact boundary
# --------------------------------------------------------------------------


def test_gate_a_is_decided_only_by_the_two_target_families(rows, items) -> None:
    gate = bd.gate_a(rows, items)
    assert len(gate["feasibility_rows"]) == 6
    target = [row for row in gate["feasibility_rows"] if row["model_role"] == "target"]
    assert len(target) == 2
    assert gate["overall_gate_pass"] == all(row["family_gate_pass"] for row in target)
    for row in gate["feasibility_rows"]:
        assert row["n_nt_compositional"] == 128
        assert row["confirmation_opened_before_decision"] is False
        assert row["alpha"] == 0.025 and row["critical_successes"] == 43


def test_control_success_cannot_rescue_a_failing_target(
    items, by_id, index, tokens, manifest, identities
) -> None:
    failing = bd.merge_shard_rows(
        _pack(items, by_id, index, tokens, manifest, identities, threshold=40), manifest
    )
    gate = bd.gate_a(failing, items)
    controls = [
        row
        for row in gate["feasibility_rows"]
        if row["model_role"] != "target"
    ]
    assert all(row["family_gate_pass"] for row in controls)
    assert gate["overall_gate_pass"] is False
    assert gate["terminal_state"] == bd.GATE_A_FAIL_STATE


def test_gate_a_boundary_is_exactly_forty_three_of_one_hundred_twenty_eight() -> None:
    assert s2.feasibility_gate_pass(
        permutation_correct=43,
        affine_correct=43,
        n_per_family=128,
        execution_complete=True,
        balance_ok=True,
        confirmation_unopened=True,
    )
    assert not s2.feasibility_gate_pass(
        permutation_correct=43,
        affine_correct=42,
        n_per_family=128,
        execution_complete=True,
        balance_ok=True,
        confirmation_unopened=True,
    )
    assert not s2.feasibility_gate_pass(
        permutation_correct=42,
        affine_correct=128,
        n_per_family=128,
        execution_complete=True,
        balance_ok=True,
        confirmation_unopened=True,
    )


def test_gate_a_refuses_pooling_or_depth_fallback(rows, items) -> None:
    """Dropping one depth must fail loudly, not silently fall back to n=64."""

    reduced = [row for row in rows if not (row["arm"] == "NT" and row["depth"] == 3)]
    with pytest.raises(bd.StageBDError, match="Gate A population"):
        bd.gate_a(reduced, items)

    cross_family = [row for row in rows if row["family"] != "affine_mod10"]
    with pytest.raises(bd.StageBDError, match="Gate A population"):
        bd.gate_a(cross_family, items)


def test_gate_a_refuses_to_run_after_confirmation_is_opened(rows, items) -> None:
    with pytest.raises(bd.StageBDError, match="confirmation"):
        bd.gate_a(rows, items, confirmation_opened_before_decision=True)


def test_gate_inputs_digest_binds_every_gate_input(rows, items) -> None:
    gate = bd.gate_a(rows, items)
    mutated = copy.deepcopy(rows)
    victim = next(
        row
        for row in mutated
        if row["model_role"] == "target" and row["arm"] == "NT" and row["depth"] == 2
    )
    victim["restricted_prediction"] = "A" if victim["restricted_prediction"] != "A" else "B"
    assert bd.gate_a(mutated, items)["gate_inputs_sha256"] != gate["gate_inputs_sha256"]


def test_gate_a_terminal_states_are_the_registered_strings() -> None:
    assert bd.GATE_A_PASS_STATE == (
        "NONTERMINAL_CHECKPOINT_STUDY2_STAGE_BD_GATE_A_PASSED_AWAITING_BC_AUTHORITY"
    )
    assert bd.GATE_A_FAIL_STATE == "STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY"


# --------------------------------------------------------------------------
# adversarial rejection
# --------------------------------------------------------------------------


def test_wrong_model_revision_is_rejected(by_id, index, tokens, identities) -> None:
    role, item_id, arm = "target", sorted(by_id)[0], "NT"
    item = by_id[item_id]
    row = bd.behavioral_row(
        item=item,
        role=role,
        arm=arm,
        identity=identities[role],
        prompt_identity=index[(role, item_id, arm)],
        tokens=tokens,
        option_logits=_logits(item["correct_label"], hit=True),
        option_ranks=[1, 2, 3, 4],
        top1_token_id=tokens["A"],
    )
    stale = dict(row, model_revision="0" * 40)
    with pytest.raises(bd.StageBDError):
        bd.verify_behavioral_row(
            stale,
            item=item,
            identity=identities[role],
            prompt_identity=index[(role, item_id, arm)],
            tokens=tokens,
        )


@pytest.mark.parametrize(
    "field, value",
    [
        ("prompt_sha256", "f" * 64),
        ("input_ids_sha256", "e" * 64),
        ("input_length", 3),
        ("answer_position", 0),
        ("option_token_ids", [1, 2, 3, 4]),
        ("correct_label", "D"),
        ("restricted_prediction", "D"),
        ("correct", True),
        ("execution_status", "failed"),
        ("finite", False),
        ("semantic_id", "a" * 64),
    ],
)
def test_row_verification_recomputes_every_derived_field(
    by_id, index, tokens, identities, field, value
) -> None:
    role, arm = "target", "NT"
    item_id = sorted(by_id)[0]
    item = by_id[item_id]
    prompt = index[(role, item_id, arm)]
    row = bd.behavioral_row(
        item=item,
        role=role,
        arm=arm,
        identity=identities[role],
        prompt_identity=prompt,
        tokens=tokens,
        option_logits=_logits(item["correct_label"], hit=False),
        option_ranks=[1, 2, 3, 4],
        top1_token_id=tokens["A"],
    )
    bd.verify_behavioral_row(
        row, item=item, identity=identities[role], prompt_identity=prompt, tokens=tokens
    )
    if row[field] == value:
        pytest.skip("mutation is a no-op for this row")
    with pytest.raises(bd.StageBDError):
        bd.verify_behavioral_row(
            dict(row, **{field: value}),
            item=item,
            identity=identities[role],
            prompt_identity=prompt,
            tokens=tokens,
        )


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_logits_are_refused(by_id, index, tokens, identities, bad) -> None:
    role, arm = "target", "NT"
    item_id = sorted(by_id)[0]
    item = by_id[item_id]
    values = _logits(item["correct_label"], hit=True)
    values["B"] = bad
    with pytest.raises(bd.StageBDError, match="non-finite"):
        bd.behavioral_row(
            item=item,
            role=role,
            arm=arm,
            identity=identities[role],
            prompt_identity=index[(role, item_id, arm)],
            tokens=tokens,
            option_logits=values,
            option_ranks=[1, 2, 3, 4],
            top1_token_id=tokens["A"],
        )


def test_inapplicable_arm_is_refused(by_id, index, tokens, identities) -> None:
    item = next(item for item in by_id.values() if item["depth"] == 1)
    with pytest.raises(bd.StageBDError, match="not applicable"):
        bd.behavioral_row(
            item=item,
            role="target",
            arm="ST",
            identity=identities["target"],
            prompt_identity=index[("target", item["item_id"], "NT")],
            tokens=tokens,
            option_logits=_logits(item["correct_label"], hit=True),
            option_ranks=[1, 2, 3, 4],
            top1_token_id=tokens["A"],
        )


def test_wrong_label_order_is_refused(by_id, index, tokens, identities) -> None:
    item_id = sorted(by_id)[0]
    item = by_id[item_id]
    with pytest.raises(bd.StageBDError, match="A/B/C/D"):
        bd.behavioral_row(
            item=item,
            role="target",
            arm="NT",
            identity=identities["target"],
            prompt_identity=index[("target", item_id, "NT")],
            tokens=tokens,
            option_logits={"A": 1.0, "B": 2.0, "C": 3.0, "E": 4.0},
            option_ranks=[1, 2, 3, 4],
            top1_token_id=tokens["A"],
        )


def test_duplicate_missing_and_out_of_shard_rows_are_refused(shards, manifest) -> None:
    victim = manifest["shards"][0]["shard_id"]
    other = next(
        shard["shard_id"]
        for shard in manifest["shards"]
        if shard["model_role"] != manifest["shards"][0]["model_role"]
    )

    duplicated = {key: list(value) for key, value in shards.items()}
    duplicated[victim] = duplicated[victim][:-1] + [duplicated[victim][0]]
    with pytest.raises(bd.StageBDError, match="duplicate"):
        bd.merge_shard_rows(duplicated, manifest)

    short = {key: list(value) for key, value in shards.items()}
    short[victim] = short[victim][:-1]
    with pytest.raises(bd.StageBDError, match="contributed"):
        bd.merge_shard_rows(short, manifest)

    crossed = {key: list(value) for key, value in shards.items()}
    crossed[victim] = crossed[victim][:-1] + [shards[other][0]]
    with pytest.raises(bd.StageBDError, match="out-of-shard"):
        bd.merge_shard_rows(crossed, manifest)


def test_partial_pack_cannot_be_merged(shards, manifest) -> None:
    partial = {key: value for key, value in list(shards.items())[:-1]}
    with pytest.raises(bd.StageBDError, match="shard set drift"):
        bd.merge_shard_rows(partial, manifest)


def test_shard_manifest_is_immutable_and_complete(manifest, items) -> None:
    assert manifest["shard_count"] == bd.SHARD_COUNT == 18
    assert manifest["total_rows"] == bd.TOTAL_ROWS
    assert bd.build_shard_manifest(items) == manifest
    assert bd.build_shard_manifest(list(reversed(items))) == manifest
    digest = manifest["shard_manifest_sha256"]
    recomputed = dict(manifest)
    recomputed.pop("shard_manifest_sha256")
    assert bd.sha256_bytes(bd.canonical_json_bytes(recomputed)) == digest


def test_attempt_ids_are_idempotent_and_bounded() -> None:
    assert bd.attempt_id("target/affine_mod10/d1", 1) == bd.attempt_id(
        "target/affine_mod10/d1", 1
    )
    assert bd.attempt_id("target/affine_mod10/d1", 1) != bd.attempt_id(
        "target/affine_mod10/d1", 2
    )
    assert bd.attempt_id("target/affine_mod10/d1", 1) != bd.attempt_id(
        "target/affine_mod10/d2", 1
    )
    with pytest.raises(bd.StageBDError):
        bd.attempt_id("target/affine_mod10/d1", bd.MAX_SHARD_ATTEMPTS + 1)
    with pytest.raises(bd.StageBDError):
        bd.attempt_id("target/affine_mod10/d1", 0)


def test_retry_reasons_are_exactly_the_registered_codes() -> None:
    assert set(bd.RETRY_REASONS) == {
        "NONFINITE_OUTPUT",
        "MISSING_ROW",
        "HASH_MISMATCH",
        "SOURCE_IMAGE_MISMATCH",
        "ARTIFACT_WRITE_FAILURE",
        "RUNTIME_EXCEPTION",
        "CAPACITY_UNAVAILABLE",
    }


def test_confirmation_objects_are_unaddressable_in_an_inference_context(tmp_path) -> None:
    receipt = bd.assert_confirmation_unaddressable(tmp_path)
    assert receipt["behavioral_confirmation_forwards"] == 0
    assert receipt["behavioral_confirmation_tokenizations"] == 0
    assert receipt["confirmation_prompt_identities_loaded"] == 0
    assert receipt["development_only_prompt_rows"] == bd.TOTAL_ROWS

    planted = tmp_path / bd.CONFIRMATION_PATHS[0]
    planted.parent.mkdir(parents=True, exist_ok=True)
    planted.write_text("{}", encoding="utf-8")
    with pytest.raises(bd.StageBDError, match="addressable"):
        bd.assert_confirmation_unaddressable(tmp_path)


def test_stage_t_index_never_exposes_a_confirmation_prompt(index) -> None:
    assert len(index) == bd.TOTAL_ROWS
    assert {key[0] for key in index} == set(bd.MODEL_ROLES)
    development = {item["item_id"] for item in bd.load_development_bank(ROOT)}
    assert {key[1] for key in index} == development


def test_generated_tokens_and_hidden_state_are_structurally_impossible(rows) -> None:
    banned = {
        "generated_text",
        "generated_tokens",
        "completion",
        "hidden_states",
        "activations",
        "residual",
        "probe",
        "lens",
        "patched",
        "ablated",
    }
    assert not (bd.BEHAVIORAL_ROW_KEYS & banned)
    assert not (set(rows[0]) & banned)
    assert bd.GENERATED_TOKENS == 0


# --------------------------------------------------------------------------
# schema and manifest-last packaging
# --------------------------------------------------------------------------


def test_schema_is_closed_and_lf_terminated() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    s2.verify_schema_closed(schema)
    assert SCHEMA_PATH.read_bytes().endswith(b"\n")
    assert b"\r\n" not in SCHEMA_PATH.read_bytes()


def test_emitted_rows_validate_against_the_closed_schema(rows, items, by_id) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    gate = bd.gate_a(rows, items)
    for row in rows[::311]:
        s2.validate_json_schema(row, {**defs["behavioral_row"], "$defs": defs})
    for row in gate["feasibility_rows"]:
        s2.validate_json_schema(row, {**defs["feasibility_gate_row"], "$defs": defs})
    for row in bd.summarize(rows)[::7]:
        s2.validate_json_schema(row, {**defs["summary_row"], "$defs": defs})
    for row in bd.bootstrap_diagnostics(rows, by_id)[::11]:
        s2.validate_json_schema(row, {**defs["bootstrap_row"], "$defs": defs})


def test_pack_writes_the_core_manifest_last(tmp_path, rows, items, by_id, manifest) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    gate = bd.gate_a(rows, items)
    result = bd.write_pack(
        tmp_path,
        rows=rows,
        items=items,
        shard_manifest=manifest,
        weight_identity=_weight_identity(),
        confirmation=bd.assert_confirmation_unaddressable(tmp_path),
        gate=gate,
        summaries=bd.summarize(rows),
        diagnostics=bd.bootstrap_diagnostics(rows, by_id),
        frozen=bd.verify_frozen_inputs(ROOT),
        environment=_environment(),
        execution=_execution(manifest),
    )

    written = sorted(path.name for path in tmp_path.iterdir())
    assert written == sorted((*bd.PACK_FILES, bd.CORE_MANIFEST_NAME))
    newest = max(tmp_path.iterdir(), key=lambda path: path.stat().st_mtime_ns)
    assert newest.name == bd.CORE_MANIFEST_NAME

    s2.validate_json_schema(result["manifest"], {**defs["core_manifest"], "$defs": defs})
    s2.validate_json_schema(
        json.loads((tmp_path / "stage_bd_gate_a_decision.json").read_text("utf-8")),
        {**defs["gate_a_decision"], "$defs": defs},
    )
    s2.validate_json_schema(manifest, {**defs["shard_manifest"], "$defs": defs})
    assert result["manifest"]["operation_counts"]["generations"] == 0
    assert result["manifest"]["operation_counts"]["forward_passes"] == bd.TOTAL_ROWS
    assert result["manifest"]["observed_row_count"] == bd.TOTAL_ROWS


def test_pack_refuses_an_incomplete_row_set(tmp_path, rows, items, by_id, manifest) -> None:
    gate = bd.gate_a(rows, items)
    with pytest.raises(bd.StageBDError, match="pack carries 3071 rows"):
        bd.write_pack(
            tmp_path,
            rows=rows[:-1],
            items=items,
            shard_manifest=manifest,
            weight_identity=_weight_identity(),
            confirmation=bd.assert_confirmation_unaddressable(tmp_path),
            gate=gate,
            summaries=bd.summarize(rows),
            diagnostics=bd.bootstrap_diagnostics(rows, by_id),
            frozen=bd.verify_frozen_inputs(ROOT),
            environment=_environment(),
            execution=_execution(manifest),
        )
    assert not (tmp_path / bd.CORE_MANIFEST_NAME).exists()


def test_weight_identity_receipt_rejects_a_mismatched_snapshot() -> None:
    snapshots = _snapshots()
    snapshots["target"]["resolved_revision"] = "0" * 40
    with pytest.raises(bd.StageBDError, match="revision"):
        bd.weight_identity_receipt(snapshots)


def test_preinference_seal_binds_the_execution_inputs(items, index, tokens, manifest) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    blob = {"bytes": 1, "path": "x", "sha256": "0" * 64}
    seal = bd.build_preinference_seal(
        frozen=bd.verify_frozen_inputs(ROOT),
        shard_manifest=manifest,
        expected_keys=bd.expected_row_keys(items),
        source=blob,
        schema=blob,
        confirmation=bd.assert_confirmation_unaddressable(Path("/nonexistent-bd-root")),
        tokens=tokens,
    )
    s2.validate_json_schema(seal, {**defs["preinference_seal"], "$defs": defs})
    assert seal["expected_row_count"] == bd.TOTAL_ROWS
    assert seal["starting_commit"] == bd.STAGE_BD_START_COMMIT
    assert seal["shard_manifest_sha256"] == manifest["shard_manifest_sha256"]


# --------------------------------------------------------------------------
# fake weight/runtime identities
# --------------------------------------------------------------------------


def _snapshots() -> dict:
    return {
        role: {
            "dtype_inventory": {"torch.float16": 2},
            "files": [
                {"bytes": 4, "name": "config.json", "sha256": "1" * 64},
                {"bytes": 8, "name": "model.safetensors", "sha256": "2" * 64},
            ],
            "model_class": "Qwen2ForCausalLM",
            "model_id": model_id,
            "parameter_count": 1_543_714_304,
            "parameter_dtype": "torch.float16",
            "requested_revision": revision,
            "resolved_revision": revision,
            "tokenizer_class": "Qwen2TokenizerFast",
        }
        for role, model_id, revision in s2.MODEL_IDENTITIES
    }


def _weight_identity() -> dict:
    return bd.weight_identity_receipt(_snapshots())


def _environment() -> dict:
    return {
        "cuda_device_name": "Tesla T4",
        "image_digest": "sha256:" + "3" * 64,
        "platform_machine": "x86_64",
        "python_version": "3.11.9",
        "pythonhashseed": "0",
        "source_commit": "0" * 40,
        "source_tree": "1" * 40,
        "torch_version": "2.4.1",
        "transformers_version": "4.46.3",
    }


def _execution(manifest) -> dict:
    return {
        "attempts": [
            {
                "attempt": 1,
                "attempt_id": bd.attempt_id(shard["shard_id"], 1),
                "elapsed_seconds_bucket": 10,
                "outcome": "complete",
                "retry_reason": "",
                "row_count": shard["row_count"],
                "row_keys_sha256": shard["row_keys_sha256"],
                "shard_id": shard["shard_id"],
            }
            for shard in manifest["shards"]
        ],
        "batch_size": 1,
        "retries": 0,
        "schema_version": bd.EXECUTION_RECEIPT_VERSION,
        "shards_complete": bd.SHARD_COUNT,
    }
