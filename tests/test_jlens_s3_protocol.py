"""Model-free tests for the design-only J-lens S3 validity protocol."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "jspace_observation"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import jlens_s3_protocol as s3  # noqa: E402
import phase1_0d_protected_bytes as protected  # noqa: E402

PROTOCOL_PATH = ROOT / "docs" / "jlens_s3_validity_protocol.json"
SCHEMA_PATH = ROOT / "docs" / "jlens_s3_validity_protocol.schema.json"
MARKDOWN_PATH = ROOT / "docs" / "jlens_s3_validity_protocol.md"
VENDORED = (
    ROOT
    / "third_party"
    / "jacobian-lens"
    / "581d398613e5602a5af361e1c34d3a92ea82ba8e"
)


@pytest.fixture(scope="module")
def protocol() -> dict:
    return s3.load_json(PROTOCOL_PATH)


@pytest.fixture(scope="module")
def schema() -> dict:
    return s3.load_json(SCHEMA_PATH)


def _semantic_mutation(protocol: dict, mutate) -> None:
    candidate = copy.deepcopy(protocol)
    mutate(candidate)
    with pytest.raises(s3.ProtocolError):
        s3.validate_protocol_semantics(candidate)


def _row_for(table: dict) -> dict:
    row = {}
    for column in table["columns"]:
        name, specification = column.split(":", 1)
        if specification.startswith("null_or_"):
            row[name] = None
        elif specification.startswith("enum["):
            row[name] = specification[5:-1].split(",")[0]
        elif specification == "sha256":
            row[name] = "0" * 64
        elif specification == "immutable_ref":
            row[name] = "0" * 40
        elif specification == "string":
            row[name] = "x"
        elif specification == "boolean":
            row[name] = True
        elif specification == "integer":
            row[name] = 1
        elif specification == "number":
            row[name] = 1.0
        elif specification in {"array_string", "array_integer"}:
            row[name] = []
        else:  # pragma: no cover - a newly invented output type must fail visibly
            raise AssertionError(f"unhandled output type {specification}")
    return row


# ---------------------------------------------------------------------------
# package, upstream bytes, closure, and fail-closed rejection
# ---------------------------------------------------------------------------


def test_complete_candidate_package_validates_model_free() -> None:
    document = s3.load_and_validate_protocol(ROOT)
    assert document["schema_version"] == s3.SCHEMA_VERSION
    assert PROTOCOL_PATH.read_bytes() == s3.canonical_json_bytes(document)


def test_exact_upstream_hashes_bytes_counts_roles_and_counterparts(protocol: dict) -> None:
    report = s3.verify_vendored_sources(ROOT, protocol)
    assert set(report["files"]) == set(s3.EXPECTED_UPSTREAM_FILES)
    for relative, (byte_count, digest, item_count, _role) in s3.EXPECTED_UPSTREAM_FILES.items():
        raw = VENDORED.joinpath(*relative.split("/")).read_bytes()
        assert len(raw) == byte_count
        assert hashlib.sha256(raw).hexdigest() == digest
        assert report["files"][relative]["item_count"] == item_count
    assert report["counterparts"] == {
        "oriented_matches": 29,
        "unique_unordered_pairs": 24,
    }


def test_model_free_counterpart_builder_reproduces_29_and_24() -> None:
    items = s3.load_json(VENDORED / "data" / "experiments" / "probe-swap.json")["items"]
    built = s3.build_counterparts(items)
    assert len(built["oriented_matches"]) == 29
    assert len(built["unordered_pairs"]) == 24
    assert len({row["unordered_pair_id"] for row in built["unordered_pairs"]}) == 24


def test_counterpart_duplicate_base_triple_uses_first_official_item() -> None:
    items = [
        {
            "name": "first",
            "category": "c",
            "intermediate": "base",
            "answer": "answer",
            "swap_to": "none",
            "swap_answer": "none",
        },
        {
            "name": "duplicate",
            "category": "c",
            "intermediate": "BASE",
            "answer": "ANSWER",
            "swap_to": "none",
            "swap_answer": "none",
        },
        {
            "name": "source",
            "category": "c",
            "intermediate": "other",
            "answer": "other-answer",
            "swap_to": "base",
            "swap_answer": "answer",
        },
    ]
    built = s3.build_counterparts(items)
    assert built["oriented_matches"] == (
        {
            "source_item_id": "source",
            "counterpart_item_id": "first",
            "unordered_pair_id": hashlib.sha256(b"first\nsource").hexdigest(),
        },
    )


def test_schema_is_closed_and_markdown_crosswalk_is_complete(
    protocol: dict, schema: dict
) -> None:
    s3.validate_json_schema(protocol, schema)
    s3.validate_markdown_crosswalk(MARKDOWN_PATH)

    def walk(node):
        if not isinstance(node, dict):
            return
        declared = node.get("type")
        if declared == "object" or isinstance(declared, list) and "object" in declared:
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])
        for key in ("properties", "$defs"):
            for child in node.get(key, {}).values():
                walk(child)
        if "items" in node:
            walk(node["items"])

    walk(schema)
    for path in s3.REQUIRED_CROSSWALK_PATHS:
        assert f"`{path}`" in MARKDOWN_PATH.read_text(encoding="utf-8")


def test_schema_rejects_missing_and_extra_fields(protocol: dict, schema: dict) -> None:
    missing = copy.deepcopy(protocol)
    missing.pop("readout")
    with pytest.raises(s3.ProtocolError, match="missing"):
        s3.validate_json_schema(missing, schema)
    extra = copy.deepcopy(protocol)
    extra["unregistered"] = True
    with pytest.raises(s3.ProtocolError, match="extra"):
        s3.validate_json_schema(extra, schema)


def test_schema_engine_rejects_unsupported_keywords_and_unclosed_objects() -> None:
    with pytest.raises(s3.ProtocolError, match="unsupported"):
        s3._check_schema_definition({"type": "string", "oneOf": []})
    with pytest.raises(s3.ProtocolError, match="not closed"):
        s3._check_schema_definition(
            {"type": "object", "properties": {}, "required": []}
        )
    with pytest.raises(s3.ProtocolError, match="every closed object property"):
        s3._check_schema_definition(
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {"x": {"type": "string"}},
                "required": [],
            }
        )
    with pytest.raises(s3.ProtocolError, match="every closed object property"):
        s3._check_schema_definition(
            {"type": "object", "additionalProperties": False, "properties": {}}
        )


def test_strict_json_loader_rejects_nonfinite_literals(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"x":NaN}\n', encoding="utf-8")
    with pytest.raises(s3.ProtocolError, match="non-finite"):
        s3.load_json(bad)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p["authority"].__setitem__("question", "TODO"),
        lambda p: p["causal"]["coordinate_swap"]["alphas"].__setitem__(
            "primary", float("nan")
        ),
        lambda p: p["identities"]["target_model"].__setitem__("revision", "main"),
        lambda p: p["role_separation"]["allowed_selection_signals"].append("rank"),
        lambda p: p["role_separation"]["role_identity"].__setitem__(
            "row_id", "SHA-256(canonical_item_bytes)"
        ),
        lambda p: p["eligibility"]["order_ops"]["numeric_forms"]["3"].append("third"),
        lambda p: p["eligibility"]["targets"].__setitem__(
            "primary_readout", "accept any numeric synonym"
        ),
        lambda p: p["layers"]["bands"]["primary_middle"].__setitem__("start", 8),
        lambda p: p["split"].__setitem__("seed", "later-seed"),
        lambda p: p["split"]["floors"].__setitem__("causal_swap_confirmation", 29),
        lambda p: p["classification"]["hard_scientific_gates"].pop(),
        lambda p: p["classification"]["hard_scientific_gates"].__setitem__(
            0, "lower95(label) >= 0"
        ),
        lambda p: p["classification"]["terminal_values"].append("MAYBE_VALID"),
        lambda p: p["classification"]["truth_table"][0].__setitem__(
            "result", "JLENS_PARTIALLY_VALIDATED"
        ),
        lambda p: p["outputs"]["e0_item"]["columns"].pop(),
        lambda p: p["outputs"]["e0_item"]["columns"].__setitem__(
            1, "item_id:integer"
        ),
        lambda p: p["outputs"]["readout_rank"].__setitem__("create_only", False),
        lambda p: p["outputs"]["readout_rank"].__setitem__(
            "primary_key", ["item_id"]
        ),
        lambda p: p["review"]["questions"].pop(),
    ],
)
def test_semantic_validator_rejects_registered_drift(protocol: dict, mutation) -> None:
    _semantic_mutation(protocol, mutation)


def test_role_overlap_is_rejected_mechanically() -> None:
    with pytest.raises(s3.ProtocolError, match="role overlap"):
        s3.validate_role_sets(
            {"development items": {"a", "b"}, "confirmation items": {"b", "c"}},
            [("development items", "confirmation items")],
        )
    s3.validate_role_sets(
        {"development items": {"a"}, "confirmation items": {"b"}},
        [("development items", "confirmation items")],
    )


def test_role_row_identity_qualifies_cross_distribution_duplicates() -> None:
    item = {"name": "same", "prompt": "p", "target": "t", "intermediates": ["i"]}
    multihop = s3.canonical_role_row_bytes("multihop", item)
    causal = s3.canonical_role_row_bytes("causal_swap", item)
    assert multihop == b"multihop\0" + s3.canonical_item_bytes(item)
    assert causal == b"causal_swap\0" + s3.canonical_item_bytes(item)
    assert multihop != causal
    assert s3.canonical_role_row_hash(
        "multihop", item
    ) != s3.canonical_role_row_hash("causal_swap", item)
    with pytest.raises(s3.ProtocolError, match="unknown official distribution"):
        s3.canonical_role_row_bytes("merged", item)


def test_output_rows_are_closed_typed_and_output_pack_is_all_or_nothing(
    protocol: dict,
) -> None:
    pack = {}
    for table_name in protocol["outputs"]["required_tables"]:
        row = _row_for(protocol["outputs"][table_name])
        s3.validate_output_row(protocol, table_name, row)
        pack[table_name] = [row]
    s3.validate_output_pack(protocol, pack)

    malformed = copy.deepcopy(pack["e0_item"][0])
    malformed["extra"] = 1
    with pytest.raises(s3.ProtocolError, match="extra"):
        s3.validate_output_row(protocol, "e0_item", malformed)
    partial = copy.deepcopy(pack)
    partial.pop("classification")
    with pytest.raises(s3.ProtocolError, match="partial"):
        s3.validate_output_pack(protocol, partial)


# ---------------------------------------------------------------------------
# immutable split, finite vocabulary, and mechanical eligibility
# ---------------------------------------------------------------------------


def test_split_uses_only_canonical_bytes_seed_and_is_disjoint() -> None:
    items = [
        {"name": "a", "prompt": "raw A", "target": "1", "intermediates": ["x"]},
        {"name": "b", "prompt": "raw B", "target": "2", "intermediates": ["y"]},
        {"name": "c", "prompt": "raw C", "target": "3", "intermediates": ["z"]},
    ]
    assigned = s3.assign_hash_split(items, development_count=1)
    expected = sorted(
        (
            hashlib.sha256(
                s3.canonical_item_bytes(item) + s3.SPLIT_SEED.encode("utf-8")
            ).hexdigest(),
            item["name"],
        )
        for item in items
    )
    assert [(row["split_hash"], row["item_id"]) for row in assigned] == expected
    development = {row["item_id"] for row in assigned if row["split_role"] == "development"}
    confirmation = {row["item_id"] for row in assigned if row["split_role"] == "confirmation"}
    assert len(development) == 1
    assert development.isdisjoint(confirmation)
    assert development | confirmation == {"a", "b", "c"}


def test_order_ops_synonym_table_has_exact_finite_coverage(protocol: dict) -> None:
    registered = protocol["eligibility"]["order_ops"]
    assert list(s3.NUMERIC_FORMS) == [
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "13",
        "15",
        "16",
        "20",
        "24",
    ]
    assert list(s3.OPERATION_FORMS) == [
        "addition",
        "division",
        "mod",
        "multiplication",
        "squared",
        "subtraction",
    ]
    assert {key: tuple(value) for key, value in registered["numeric_forms"].items()} == (
        dict(s3.NUMERIC_FORMS)
    )
    assert {
        key: tuple(value) for key, value in registered["operation_forms"].items()
    } == dict(s3.OPERATION_FORMS)
    with pytest.raises(TypeError):
        s3.NUMERIC_FORMS["25"] = ("25", "twenty-five")
    with pytest.raises(TypeError):
        s3.OPERATION_FORMS["power"] = ("power",)


def test_nfkc_whitespace_boundary_casefold_and_single_token_rules() -> None:
    assert s3.normalize_surface("\u212b\t  X") == "\u00c5 X"
    assert s3.normalize_surface("  Stra\u00dfe ", casefold=True) == "strasse"
    assert s3.token_matches_surface(" Brazil", "brazil")
    assert s3.token_matches_surface("BRAZIL", "Brazil")
    assert not s3.token_matches_surface("  Brazil", "Brazil")
    assert not s3.token_matches_surface("\tBrazil", "Brazil")
    resolved = s3.resolve_single_token_ids(
        ["Brazil", "twenty-four"],
        {1: " Brazil", 2: "brazil", 3: "twenty", 4: " twenty-four"},
    )
    assert resolved == {"Brazil": (1, 2), "twenty-four": (4,)}


def test_surface_and_answer_leakage_filtering_is_mechanical() -> None:
    result = s3.filter_leaking_surfaces(
        ["Brazil", "cloud", "Portuguese", "rail"],
        "Fact: Brazil's rain-forest is large; a BRAZIL fact.",
        "Portuguese",
    )
    assert result == {
        "kept": ("cloud", "rail"),
        "prompt_surface": ("Brazil",),
        "target_overlap": ("Portuguese",),
    }
    exact_only = s3.filter_leaking_surfaces(["3", "three"], "", "3")
    assert exact_only == {
        "kept": ("three",),
        "prompt_surface": (),
        "target_overlap": ("3",),
    }
    assert s3.token_bounded_literal("a rain-forest", "rain")
    assert not s3.token_bounded_literal("a train", "rain")


def test_hard_surface_gate_is_reconstructible_from_registered_rows() -> None:
    items = [
        {
            "distribution": "multihop",
            "item_id": "item",
            "mechanical_eligible": True,
            "behavioral_eligible": True,
            "split_role": "confirmation",
        }
    ]
    surfaces = [
        {
            "distribution": "multihop",
            "item_id": "item",
            "surface_role": "intermediate",
            "intermediate_index": 0,
            "token_ids": [7, 3],
            "prompt_leakage": False,
            "target_overlap": False,
            "single_token": True,
            "primary_retained": True,
        }
    ]
    ranks = [
        {
            "distribution": "multihop",
            "item_id": "item",
            "intermediate_index": 0,
            "control_kind": "true",
            "registered_token_ids": [3, 7],
        }
    ]
    assert s3.hard_surface_gate(items, surfaces, ranks)

    target_leak = copy.deepcopy(surfaces)
    target_leak[0]["target_overlap"] = True
    assert not s3.hard_surface_gate(items, target_leak, ranks)
    wrong_tokens = copy.deepcopy(ranks)
    wrong_tokens[0]["registered_token_ids"] = [3]
    assert not s3.hard_surface_gate(items, surfaces, wrong_tokens)


def test_control_position_and_clean_behavior_eligibility_are_mechanical() -> None:
    positions = s3.eligible_control_positions(
        ["safe", " Brazil", "also safe", "final"],
        ["Brazil"],
    )
    assert positions == (0, 2)
    item = {"name": "x", "prompt": "p", "target": "t", "intermediates": ["i"]}
    first = s3.deterministic_position_controls(item, positions)
    assert first == s3.deterministic_position_controls(item, positions)
    assert len(first) == 5 and set(first) <= {0, 2}
    assert s3.clean_behavior_eligible(7, [5, 7])
    assert not s3.clean_behavior_eligible(8, [5, 7])
    with pytest.raises(s3.ProtocolError, match="no eligible"):
        s3.deterministic_position_controls(item, ())


def test_label_derangement_is_deterministic_complete_and_has_no_fixed_point() -> None:
    items = [
        {"name": name, "prompt": name, "target": name, "intermediates": [name]}
        for name in ("a", "b", "c", "d")
    ]
    first = s3.deterministic_label_derangement(items, "multihop", 0)
    second = s3.deterministic_label_derangement(items, "multihop", 0)
    assert first == second
    assert set(first) == set(first.values()) == {"a", "b", "c", "d"}
    assert all(source != target for source, target in first.items())


# ---------------------------------------------------------------------------
# readout, bootstrap, vector algebra, and frozen classification
# ---------------------------------------------------------------------------


def test_pass_at_k_auc_hand_computed_positive_zero_and_tie_examples() -> None:
    positive_curve, positive = s3.pass_at_k_auc([1, 1])
    zero_curve, zero = s3.pass_at_k_auc([101, 200])
    tie_curve, tie = s3.pass_at_k_auc([1, 100])
    assert positive_curve == {k: 1.0 for k in s3.K_GRID}
    assert positive == pytest.approx(1.0)
    assert zero_curve == {k: 0.0 for k in s3.K_GRID}
    assert zero == pytest.approx(0.0)
    assert tie_curve[1] == 0.5 and tie_curve[50] == 0.5 and tie_curve[100] == 1.0
    expected_tie = 0.5 + 0.25 * math.log(2.0) / math.log(100.0)
    assert tie == pytest.approx(expected_tie)


def test_equal_distribution_pool_is_half_each_with_unequal_n() -> None:
    assert s3.equal_distribution_pool([1.0], [0.0] * 99) == pytest.approx(0.5)
    assert s3.equal_distribution_pool([0.2, 0.4], [0.8]) == pytest.approx(0.55)


def test_paired_bootstrap_is_deterministic_item_paired_and_equal_weighted() -> None:
    paired = {
        "multihop": [(2.0, 1.0), (4.0, 3.0)],
        "order_ops": [(10.0, 10.0)],
    }
    first = s3.paired_bootstrap(paired, replicates=40)
    second = s3.paired_bootstrap(paired, replicates=40)
    assert first == second
    assert first == pytest.approx((0.5,) * 40)
    lower, upper = s3.percentile_interval(first)
    assert lower == pytest.approx(0.5)
    assert upper == pytest.approx(0.5)


def test_coordinate_swap_exchanges_coordinates_preserves_orthogonal_component() -> None:
    swapped = s3.coordinate_swap(
        (2.0, 5.0, 7.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
    )
    assert swapped == pytest.approx((5.0, 2.0, 7.0))
    assert s3.coordinate_swap(
        (2.0, 5.0, 7.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        alpha=0.0,
    ) == (2.0, 5.0, 7.0)
    assert s3.ablate_direction((2.0, 5.0, 7.0), (1.0, 0.0, 0.0)) == (
        0.0,
        5.0,
        7.0,
    )


def test_gram_matched_random_pairs_are_deterministic_and_within_frozen_tolerance() -> None:
    source = (2.0, 0.0, 1.0, -1.0)
    target = (1.0, 3.0, 0.0, 2.0)
    expected = s3.gram_matrix(source, target)
    first = s3.deterministic_gram_matched_pairs(source, target, context="item/layer")
    second = s3.deterministic_gram_matched_pairs(source, target, context="item/layer")
    assert first == second
    assert len(first) == 5
    for pair in first:
        observed = s3.gram_matrix(*pair)
        for row in range(2):
            for column in range(2):
                assert abs(observed[row][column] - expected[row][column]) <= (
                    s3.GRAM_TOLERANCE
                )


def test_spearman_alignment_uses_average_tie_ranks() -> None:
    assert s3.spearman_correlation([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert s3.spearman_correlation([1, 1, 2], [1, 1, 2]) == pytest.approx(1.0)


@pytest.mark.parametrize("hard", [False, True])
@pytest.mark.parametrize("readout", [False, True])
@pytest.mark.parametrize("causal", [False, True])
def test_complete_classification_truth_table(hard: bool, readout: bool, causal: bool) -> None:
    result = s3.classify(
        floors_pass=True,
        integrity_pass=True,
        hard_gates_pass=hard,
        readout_pass=readout,
        causal_pass=causal,
    )
    if not hard or not (readout or causal):
        expected = "JLENS_NOT_VALIDATED"
    elif readout and causal:
        expected = "JLENS_VALIDATED_FOR_RQ2_PILOT"
    else:
        expected = "JLENS_PARTIALLY_VALIDATED"
    assert result == {"operational_status": "COMPLETE", "classification": expected}


def test_floor_failure_and_operational_blocker_precede_scientific_classification() -> None:
    assert s3.classify(
        floors_pass=False,
        integrity_pass=False,
        hard_gates_pass=True,
        readout_pass=True,
        causal_pass=True,
    ) == {
        "operational_status": "COMPLETE",
        "classification": "INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY",
    }
    assert s3.classify(
        floors_pass=True,
        integrity_pass=False,
        hard_gates_pass=False,
        readout_pass=False,
        causal_pass=False,
    ) == {"operational_status": "OPERATIONAL_BLOCKER", "classification": None}


# ---------------------------------------------------------------------------
# static reachability and protected historical state
# ---------------------------------------------------------------------------


def test_design_validator_has_no_forbidden_import_or_call_reachability() -> None:
    forbidden_imports = {
        "azure",
        "numpy",
        "scipy",
        "torch",
        "transformers",
        "jspace_observation.model_loader",
        "jspace_observation.eval_parsing",
    }
    forbidden_calls = {
        "from_pretrained",
        "generate",
        "forward",
        "load_model",
        "load_tokenizer",
        "fit",
        "apply_lens",
        "submit",
        "create_job",
        "begin_create_or_update",
    }
    for path in (
        ROOT / "src" / "jspace_observation" / "jlens_s3_protocol.py",
        ROOT / "scripts" / "validate_jlens_s3_protocol.py",
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        assert not any(
            imported == denied or imported.startswith(denied + ".")
            for imported in imports
            for denied in forbidden_imports
        )
        assert calls.isdisjoint(forbidden_calls)


def test_phase1_0d_anchor_hashes_and_protected_namespaces_remain_unchanged(
    protocol: dict,
) -> None:
    for anchor in protocol["authority"]["phase1_0d_anchors"]:
        raw = ROOT.joinpath(*anchor["path"].split("/")).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == anchor["sha256"]
    baseline = ROOT / protected.BASELINE_FILENAME
    assert protected.verify(ROOT, baseline) == []


def test_only_two_historical_parser_seal_failures_are_accepted(protocol: dict) -> None:
    baseline = protocol["verification"]["accepted_historical_full_suite_baseline"]
    assert baseline == {
        "failed": 2,
        "failure_file": "tests/test_parser_v3_seal_job.py",
        "passed": 3372,
        "skipped": 15,
    }
    assert baseline["failure_file"] != str(Path(__file__).relative_to(ROOT)).replace("\\", "/")
