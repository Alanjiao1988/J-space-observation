"""Model-free validation and statistics for Study 2.

Stage P is deliberately executable with the Python standard library only.  It
does not construct a tokenizer, load a model or lens, read an activation, or
contact an inference provider.  The task-bank verifier below is independently
coded from :mod:`study2_task_bank`: it recomputes every ground-truth value and
rendered prompt from primitive row fields instead of calling generator logic.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "jspace-study2-reasoning-internalization/v1"
TASK_ROW_VERSION = "jspace-study2-task-row/v1"
PAIR_ROW_VERSION = "jspace-study2-pair-row/v1"
MANIFEST_VERSION = "jspace-study2-task-bank-manifest/v1"

START_COMMIT = "191d4a3596ab64b26f54effb6ccaf6005f229139"
START_TREE = "9d1c68d895435928a10ac2b0f44d277b370000c1"
AUTHORITY_SHA256 = "1408c5ae4d09a097c70b0e984150c4947e527ca12b5614905a98b65685ed0b37"
AUTHORITY_BYTES = 53_018

MODEL_IDENTITIES = (
    (
        "target",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562",
    ),
    (
        "lineage_base",
        "Qwen/Qwen2.5-Math-1.5B",
        "4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2",
    ),
    (
        "instruction_control",
        "Qwen/Qwen2.5-Math-1.5B-Instruct",
        "aafeb0fc6f22cbf0eaeed126eff8be45b0360a35",
    ),
)

JLENS_COMMIT = "581d398613e5602a5af361e1c34d3a92ea82ba8e"
M1200_SEAL = "9716c3802625176060b3c2a479f7860cf4045807a45c6de346833a3b66e00138"

LABELS = ("A", "B", "C", "D")
TEMPLATES = ("T-A", "T-B")
FAMILIES = ("permutation_chain", "affine_mod10")
DEPTHS = (1, 2, 3)
COMPOSITIONAL_DEPTHS = (2, 3)
OPERATOR_NAMES = ("P", "Q", "R")
AFFINE_MULTIPLIERS = (1, 3, 7, 9)

SEEDS = {
    "development": "jspace-study2-dev-2026-08-07",
    "behavioral_confirmation": "jspace-study2-behavior-confirm-2026-08-07",
    "mechanistic_development": "jspace-study2-mechanistic-dev-2026-08-07",
    "mechanistic_candidate_confirmation": "jspace-study2-mechanistic-confirm-2026-08-07",
    "option_permutation": "jspace-study2-option-order-2026-08-07",
    "bootstrap": "jspace-study2-bootstrap-2026-08-07",
    "random_controls": "jspace-study2-random-controls-2026-08-07",
    "label_permutations": "jspace-study2-label-permutations-2026-08-07",
}

BANK_FILES = {
    "development": "development.jsonl",
    "behavioral_confirmation": "behavioral_confirmation.jsonl",
    "mechanistic_development": "mechanistic_development_candidate_pairs.jsonl",
    "mechanistic_candidate_confirmation": "mechanistic_candidate_pairs.jsonl",
}

EXPECTED_ROLE_COUNTS = {
    "development": 384,
    "behavioral_confirmation": 1_536,
    "mechanistic_development": 1_024,
    "mechanistic_candidate_confirmation": 1_024,
}
EXPECTED_CELL_COUNTS = {
    "development": 64,
    "behavioral_confirmation": 256,
    "mechanistic_development": 256,
    "mechanistic_candidate_confirmation": 256,
}

SCIENTIFIC_STATES = (
    "STUDY2_DISTILLATION_ASSOCIATED_CAUSAL_INTERNAL_REASONING_SUPPORTED",
    "STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_WITHOUT_DISTILLATION_ATTRIBUTION",
    "STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_ONE_FAMILY_ONLY",
    "STUDY2_BEHAVIOR_ONLY_WITHOUT_CAUSAL_SUPPORT",
    "STUDY2_EXTERNAL_TRACE_DEPENDENCE_ONLY",
    "STUDY2_EXTERNAL_TRACE_SUPPORT_ONE_FAMILY_ONLY",
    "STUDY2_NO_COMPOSITIONAL_BEHAVIORAL_SUPPORT",
    "STUDY2_TASK_INTERFACE_UNQUALIFIED",
    "STUDY2_RESULT_NOT_ESTIMABLE",
)
JLENS_STATES = (
    "STUDY2_JLENS_VALIDATED",
    "STUDY2_JLENS_PARTIAL",
    "STUDY2_JLENS_NOT_VALIDATED",
    "STUDY2_JLENS_NOT_ESTIMABLE",
)
OPERATIONAL_BLOCKERS = (
    "BLOCKED_ON_STUDY2_STARTING_STATE_INTEGRITY",
    "BLOCKED_ON_STUDY2_PREREGISTRATION_INTEGRITY",
    "BLOCKED_ON_STUDY2_MODEL_IDENTITY",
    "BLOCKED_ON_STUDY2_COMMON_OPTION_TOKENIZATION",
    "BLOCKED_ON_STUDY2_MECHANISTIC_TOKEN_SUPPORT",
    "BLOCKED_ON_STUDY2_EXECUTION",
)

PROTECTED_ANCHORS = {
    "docs/jlens_s2_s3_e0_final_handoff.md": "5870c82b15575086f5c29c34661d89d96d265848846e3de74162da8919951f77",
    "docs/jlens_s3_validity_protocol.json": "bb07dc3be90539e88ff8ada8adee879da747ec5b0b0409499b9809f259df4625",
    "docs/decisions/jlens_s3_validity_protocol_freeze.md": "d7d9623e3668b5469b426ba45671f267b631599e44f598f710f6c16564a96b48",
    "artifacts/jlens-s2-production/20260806T194226Z/s2-sealed/s2_manifest.json": "9d10a4b07a8133b7241ce9067649ebf1de48429cf7c04e0495b4c3fe90e58e47",
    "artifacts/jlens-s2-production/20260806T194226Z/s2-sealed/A600_seal.json": "4032c8f30ec6aec2f12cbf0a303466a0fe66745617266dcc0fa3d2289e731dd7",
    "artifacts/jlens-s2-production/20260806T194226Z/s2-sealed/B600_seal.json": "b62cd7f69aaa4a662144d8a8b75e3165330c9369990a52dbee85bb1b06b33ad4",
    "artifacts/jlens-s2-production/20260806T194226Z/s2-sealed/M1200_seal.json": M1200_SEAL,
    "artifacts/jlens-s3-e0/20260807T081017Z/output/artifact_manifest.jsonl": "6d11b09b39bbeead9b38fdb23be47a4247245fb55e6b6b665b817241519df60f",
    "artifacts/jlens-s3-e0/20260807T081017Z/05_terminal_receipt.json": "e7daad69a81377aba05be2617c07522d8d04552e594bc2cdc8318b057a83f218",
    "artifacts/phase1-0d-semantic-review-v2-transport-capacity/20260805T180417Z/00_capacity_certificate.json": "20e486e05a5f076b720ca12db3459b5a1c2c42e95684977dfdcff19d6da055d3",
    "artifacts/phase1-0d-semantic-review-v2-transport-capacity/20260805T180417Z/artifact_manifest.json": "23016ad15430b1720e4b37033a3638bf45e817ac00513292d138d26e0ed0a834",
}

TASK_KEYS = frozenset(
    {
        "schema_version",
        "role",
        "item_id",
        "semantic_id",
        "family",
        "depth",
        "template_id",
        "seed",
        "counter",
        "state_space",
        "operators",
        "start_state",
        "operation_sequence",
        "ground_truth",
        "option_values",
        "option_mapping",
        "correct_label",
        "counterfactual",
        "prompts",
        "prompt_hashes",
        "start_anchor",
        "balance",
    }
)
PAIR_KEYS = frozenset(
    {
        "schema_version",
        "role",
        "pair_id",
        "pair_semantic_id",
        "family",
        "depth",
        "template_id",
        "seed",
        "counter",
        "hash_partition",
        "state_space",
        "option_values",
        "option_mapping",
        "primary",
        "controls",
        "wrong_position_anchor",
        "stage_t_selector",
        "balance",
    }
)
PAIR_TASK_KEYS = frozenset(
    {
        "task_id",
        "semantic_id",
        "family",
        "depth",
        "template_id",
        "state_space",
        "operators",
        "start_state",
        "operation_sequence",
        "ground_truth",
        "option_values",
        "option_mapping",
        "correct_label",
        "nt_prompt",
        "prompt_sha256",
        "start_anchor",
    }
)


class ProtocolError(ValueError):
    """A fail-closed Study 2 protocol or task-bank error."""


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_bytes(value: Any) -> bytes:
    _reject_nonfinite(value, path="$")
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _reject_nonfinite(value: Any, *, path: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ProtocolError(f"non-finite value at {path}")
    if isinstance(value, Mapping):
        for key, child in value.items():
            _reject_nonfinite(child, path=f"{path}/{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_nonfinite(child, path=f"{path}/{index}")


def _pairs_without_duplicates(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=lambda literal: (_ for _ in ()).throw(
                ProtocolError(f"non-finite JSON literal {literal}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"cannot load strict JSON {path}: {exc}") from exc


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw:
                raise ProtocolError(f"blank JSONL line at {path}:{line_number}")
            row = json.loads(
                raw,
                object_pairs_hook=_pairs_without_duplicates,
                parse_constant=lambda literal: (_ for _ in ()).throw(
                    ProtocolError(f"non-finite JSON literal {literal}")
                ),
            )
            if not isinstance(row, dict):
                raise ProtocolError(f"non-object JSONL row at {path}:{line_number}")
            rows.append(row)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"cannot load strict JSONL {path}: {exc}") from exc
    return rows


def normalized_prompt(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _schema_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise ProtocolError(f"unsupported schema type {expected!r}")


def _resolve_ref(schema: Mapping[str, Any], root: Mapping[str, Any]) -> Mapping[str, Any]:
    ref = schema.get("$ref")
    if ref is None:
        return schema
    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
        raise ProtocolError(f"unsupported schema ref {ref!r}")
    name = ref.removeprefix("#/$defs/")
    try:
        resolved = root["$defs"][name]
    except (KeyError, TypeError) as exc:
        raise ProtocolError(f"unresolved schema ref {ref}") from exc
    if not isinstance(resolved, dict):
        raise ProtocolError(f"schema ref {ref} is not an object")
    return resolved


def validate_json_schema(instance: Any, schema: Mapping[str, Any]) -> None:
    """Validate the deliberately small JSON-Schema subset used by Stage P."""

    allowed = {
        "$schema",
        "$id",
        "$defs",
        "$ref",
        "title",
        "description",
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "const",
        "minItems",
        "maxItems",
        "minLength",
        "pattern",
        "minimum",
        "maximum",
    }

    def walk(value: Any, node: Mapping[str, Any], path: str) -> None:
        node = _resolve_ref(node, schema)
        unknown = set(node) - allowed
        if unknown:
            raise ProtocolError(f"unsupported schema keyword(s) at {path}: {sorted(unknown)}")
        if "const" in node:
            if value != node["const"]:
                raise ProtocolError(f"const mismatch at {path}")
            # A const-only schema is complete in standard JSON Schema: once the
            # instance equals the registered value, every nested key, element,
            # type, and scalar is exact.  Do not reinterpret the instance's
            # object/array shape as structural schema keywords that are absent
            # from this node.
            if set(node) <= {"const", "title", "description"}:
                return
        if "enum" in node and value not in node["enum"]:
            raise ProtocolError(f"enum mismatch at {path}: {value!r}")
        declared = node.get("type")
        if declared is not None:
            types = [declared] if isinstance(declared, str) else declared
            if not isinstance(types, list) or not all(isinstance(x, str) for x in types):
                raise ProtocolError(f"invalid type declaration at {path}")
            if not any(_schema_type_matches(value, item) for item in types):
                raise ProtocolError(f"type mismatch at {path}: expected {types}")
        if isinstance(value, dict):
            properties = node.get("properties", {})
            required = node.get("required", [])
            if node.get("additionalProperties") is not False:
                raise ProtocolError(f"schema object is not closed at {path}")
            if set(required) != set(properties):
                raise ProtocolError(f"closed schema object has incomplete required set at {path}")
            missing = set(required) - set(value)
            extra = set(value) - set(properties)
            if missing:
                raise ProtocolError(f"missing field(s) at {path}: {sorted(missing)}")
            if extra:
                raise ProtocolError(f"extra field(s) at {path}: {sorted(extra)}")
            for key, child in value.items():
                walk(child, properties[key], f"{path}/{key}")
        elif isinstance(value, list):
            if "minItems" in node and len(value) < node["minItems"]:
                raise ProtocolError(f"too few items at {path}")
            if "maxItems" in node and len(value) > node["maxItems"]:
                raise ProtocolError(f"too many items at {path}")
            item_schema = node.get("items")
            if item_schema is None:
                raise ProtocolError(f"array schema lacks items at {path}")
            for index, child in enumerate(value):
                walk(child, item_schema, f"{path}/{index}")
        elif isinstance(value, str):
            if len(value) < node.get("minLength", 0):
                raise ProtocolError(f"string too short at {path}")
            if "pattern" in node and re.fullmatch(node["pattern"], value) is None:
                raise ProtocolError(f"pattern mismatch at {path}")
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in node and value < node["minimum"]:
                raise ProtocolError(f"value below minimum at {path}")
            if "maximum" in node and value > node["maximum"]:
                raise ProtocolError(f"value above maximum at {path}")

    walk(instance, schema, "$")


def verify_schema_closed(schema: Mapping[str, Any]) -> None:
    def walk(node: Any, path: str) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "object":
            if node.get("additionalProperties") is not False:
                raise ProtocolError(f"schema object not closed at {path}")
            if set(node.get("required", [])) != set(node.get("properties", {})):
                raise ProtocolError(f"schema required/properties mismatch at {path}")
        for key, value in node.items():
            if key in {"properties", "$defs"}:
                for child_key, child in value.items():
                    walk(child, f"{path}/{key}/{child_key}")
            elif key == "items":
                walk(value, f"{path}/items")

    walk(schema, "$")


def _require_equal(actual: Any, expected: Any, path: str) -> None:
    if actual != expected:
        raise ProtocolError(f"registered value mismatch at {path}: {actual!r} != {expected!r}")


def validate_protocol_semantics(document: Mapping[str, Any]) -> None:
    _require_equal(document["schema_version"], SCHEMA_VERSION, "/schema_version")
    _require_equal(document["study_id"], "study2", "/study_id")
    _require_equal(document["stage"], "P", "/stage")
    if document["status"] not in {"CANDIDATE_AWAITING_REVIEW", "FROZEN_AWAITING_STAGE_T"}:
        raise ProtocolError("unregistered protocol lifecycle status")
    authority = document["authority"]
    _require_equal(authority["starting_commit"], START_COMMIT, "/authority/starting_commit")
    _require_equal(authority["starting_tree"], START_TREE, "/authority/starting_tree")
    _require_equal(authority["prompt_sha256"], AUTHORITY_SHA256, "/authority/prompt_sha256")
    _require_equal(authority["prompt_bytes"], AUTHORITY_BYTES, "/authority/prompt_bytes")
    _require_equal(authority["protected_anchors"], PROTECTED_ANCHORS, "/authority/protected_anchors")

    models = tuple((m["role"], m["model_id"], m["revision"]) for m in document["identities"]["models"])
    _require_equal(models, MODEL_IDENTITIES, "/identities/models")
    _require_equal(document["identities"]["jlens"]["commit"], JLENS_COMMIT, "/identities/jlens/commit")
    _require_equal(document["identities"]["jlens"]["m1200_seal_sha256"], M1200_SEAL, "/identities/jlens/m1200_seal_sha256")

    task = document["task_design"]
    _require_equal(tuple(x["id"] for x in task["families"]), FAMILIES, "/task_design/families")
    _require_equal(tuple(task["depths"]), DEPTHS, "/task_design/depths")
    _require_equal(tuple(x["id"] for x in task["templates"]), TEMPLATES, "/task_design/templates")
    _require_equal(task["seeds"], SEEDS, "/task_design/seeds")
    split_counts = {x["role"]: x["total_rows"] for x in task["splits"]}
    _require_equal(split_counts, EXPECTED_ROLE_COUNTS, "/task_design/splits")

    _require_equal(tuple(document["classification"]["scientific_states"]), SCIENTIFIC_STATES, "/classification/scientific_states")
    _require_equal(tuple(document["classification"]["jlens_states"]), JLENS_STATES, "/classification/jlens_states")
    _require_equal(tuple(document["classification"]["operational_blockers"]), OPERATIONAL_BLOCKERS, "/classification/operational_blockers")
    _require_equal(document["metrics"]["bootstrap"]["replicates"], 10_000, "/metrics/bootstrap/replicates")
    _require_equal(document["metrics"]["bootstrap"]["seed"], SEEDS["bootstrap"], "/metrics/bootstrap/seed")
    _require_equal(document["metrics"]["behavior"]["chance"], 0.25, "/metrics/behavior/chance")
    _require_equal(document["metrics"]["behavior"]["nt_point_floor"], 0.50, "/metrics/behavior/nt_point_floor")
    _require_equal(document["metrics"]["patching"]["alpha_zero_max_abs"], 1e-5, "/metrics/patching/alpha_zero_max_abs")
    _require_equal(document["selection"]["window"]["eligible_layers"], [9, 22], "/selection/window/eligible_layers")
    _require_equal(document["selection"]["window"]["width"], 3, "/selection/window/width")
    _require_equal(document["selection"]["window"]["early_band"], [0, 8], "/selection/window/early_band")
    _require_equal(document["selection"]["window"]["motor_band"], [23, 27], "/selection/window/motor_band")

    review = document["review"]
    _require_equal(len(review["checklist"]), 15, "/review/checklist")
    _require_equal(review["candidate_reviews"], 1, "/review/candidate_reviews")
    _require_equal(review["consolidated_corrections"], 1, "/review/consolidated_corrections")
    _require_equal(review["same_checklist_verifications"], 1, "/review/same_checklist_verifications")
    expected_review_status = "UNSPENT" if document["status"] == "CANDIDATE_AWAITING_REVIEW" else "SPENT_VERIFIED"
    _require_equal(review["status"], expected_review_status, "/review/status")
    if any(value != 0 for value in document["operation_limits"].values()):
        raise ProtocolError("Stage P operation limit is nonzero")
    if any(text.strip().lower() in {"todo", "tbd", "placeholder", "fixme"} for text in _all_strings(document)):
        raise ProtocolError("protocol contains a placeholder")
    _reject_nonfinite(document, path="$")


def _all_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from _all_strings(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from _all_strings(child)


def validate_markdown_crosswalk(path: Path, document: Mapping[str, Any]) -> None:
    text = path.read_text(encoding="utf-8")
    required_paths = (
        "/authority",
        "/identities",
        "/research_question",
        "/task_design",
        "/pair_design",
        "/prompt_arms",
        "/stage_machine",
        "/metrics",
        "/selection",
        "/classification",
        "/output_contract",
        "/review",
        "/operation_limits",
        "/limitations",
        "/claims",
    )
    for pointer in required_paths:
        if f"`{pointer}`" not in text:
            raise ProtocolError(f"Markdown crosswalk missing {pointer}")
    for formula in (
        "p(o) = exp(logit(o)) / sum",
        "TRACE_GAIN",
        "WRONG_TRACE_PULL",
        "SHUFFLE_DAMAGE",
        "G_x",
        "G_d",
        "PATCH_RECOMBINATION",
        "PATCH_RANDOM_SPECIFICITY",
        "PATCH_ANSWER_COPY_SPECIFICITY",
        "PATCH_STRUCTURAL_SPECIFICITY",
        "PATCH_POSITION_SPECIFICITY",
        "PATCH_BAND_SPECIFICITY",
    ):
        if formula not in text:
            raise ProtocolError(f"Markdown omits formula {formula}")
    for state in SCIENTIFIC_STATES + JLENS_STATES + OPERATIONAL_BLOCKERS:
        if state not in text:
            raise ProtocolError(f"Markdown omits registered state {state}")
    if document["research_question"] not in text:
        raise ProtocolError("Markdown omits exact research question")


def load_and_validate_protocol(root: Path) -> dict[str, Any]:
    protocol_path = root / "studies/study2/protocol/reasoning_internalization_protocol.json"
    schema_path = root / "studies/study2/protocol/reasoning_internalization_protocol.schema.json"
    markdown_path = root / "studies/study2/protocol/reasoning_internalization_protocol.md"
    document = load_json(protocol_path)
    schema = load_json(schema_path)
    if not isinstance(document, dict) or not isinstance(schema, dict):
        raise ProtocolError("protocol and schema must be JSON objects")
    verify_schema_closed(schema)
    validate_json_schema(document, schema)
    validate_protocol_semantics(document)
    if protocol_path.read_bytes() != canonical_json_bytes(document):
        raise ProtocolError("protocol JSON is not canonical")
    validate_markdown_crosswalk(markdown_path, document)
    return document


def verify_protected_anchors(root: Path) -> dict[str, dict[str, Any]]:
    report: dict[str, dict[str, Any]] = {}
    for relative, expected in PROTECTED_ANCHORS.items():
        path = root / relative
        if not path.is_file():
            raise ProtocolError(f"protected anchor missing: {relative}")
        digest = sha256_file(path)
        if digest != expected:
            raise ProtocolError(f"protected anchor differs: {relative}")
        report[relative] = {"bytes": path.stat().st_size, "sha256": digest}
    return report


def _state_count(family: str) -> int:
    if family == "permutation_chain":
        return 8
    if family == "affine_mod10":
        return 10
    raise ProtocolError(f"unknown family {family!r}")


def _operator_map(operator: Mapping[str, Any], value: int, family: str) -> int:
    if operator.get("name") not in OPERATOR_NAMES:
        raise ProtocolError("unregistered operator name")
    if family == "permutation_chain":
        if set(operator) != {"name", "kind", "mapping"} or operator["kind"] != "permutation":
            raise ProtocolError("invalid permutation operator")
        mapping = operator["mapping"]
        size = _state_count(family)
        if not isinstance(mapping, list) or sorted(mapping) != list(range(size)):
            raise ProtocolError("permutation mapping is not bijective")
        return mapping[value]
    if set(operator) != {"name", "kind", "a", "b", "modulus"} or operator["kind"] != "affine":
        raise ProtocolError("invalid affine operator")
    if operator["a"] not in AFFINE_MULTIPLIERS or not 0 <= operator["b"] <= 9 or operator["modulus"] != 10:
        raise ProtocolError("invalid affine parameters")
    return (operator["a"] * value + operator["b"]) % 10


def _recompute_states(task: Mapping[str, Any]) -> tuple[list[int], int, int]:
    family = task["family"]
    size = _state_count(family)
    if task["state_space"] != list(range(size)):
        raise ProtocolError("state space mismatch")
    operators = task["operators"]
    if not isinstance(operators, list) or len(operators) != 3:
        raise ProtocolError("exactly three operators are required")
    by_name = {operator["name"]: operator for operator in operators}
    if set(by_name) != set(OPERATOR_NAMES):
        raise ProtocolError("operator set must be P/Q/R")
    sequence = task["operation_sequence"]
    if len(sequence) != task["depth"] or any(name not in by_name for name in sequence):
        raise ProtocolError("operation sequence/depth mismatch")
    value = task["start_state"]
    if not isinstance(value, int) or not 0 <= value < size:
        raise ProtocolError("invalid start state")
    states: list[int] = []
    for name in sequence:
        value = _operator_map(by_name[name], value, family)
        states.append(value)
    pre_answer = task["start_state"] if task["depth"] == 1 else states[-2]
    return states, pre_answer, states[-1]


def _semantic_payload(task: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "family": task["family"],
        "state_space": task["state_space"],
        "operators": task["operators"],
        "start_state": task["start_state"],
        "operation_sequence": task["operation_sequence"],
        "option_value_set": sorted(task["option_values"]),
        "ground_truth": task["ground_truth"],
    }


def _semantic_id(task: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(_semantic_payload(task)))


def _definitions(task: Mapping[str, Any], order: Sequence[str]) -> list[str]:
    by_name = {operator["name"]: operator for operator in task["operators"]}
    lines: list[str] = []
    for name in order:
        operator = by_name[name]
        if task["family"] == "permutation_chain":
            table = " ".join(f"{index}->{value}" for index, value in enumerate(operator["mapping"]))
            lines.append(f"{name}: {table}")
        else:
            lines.append(f"{name}(x)=({operator['a']}*x+{operator['b']}) mod 10")
    return lines


def _trace_line(task: Mapping[str, Any], arm: str) -> str:
    truth = task["ground_truth"]
    pre_states = list(truth["intermediate_states"][:-1])
    if arm == "PT":
        values = pre_states
        prefix = "Trace"
    elif arm == "WT":
        values = pre_states
        values[-1] = task["counterfactual"]["wrong_pre_answer_intermediate"]
        prefix = "Trace"
    elif arm == "ST":
        values = list(reversed(pre_states))
        prefix = "Trace"
    else:
        raise ProtocolError(f"unknown trace arm {arm}")
    return f"{prefix}: " + "; ".join(f"s{index + 1}={value}" for index, value in enumerate(values))


def independent_render_task(task: Mapping[str, Any], arm: str) -> str:
    if arm not in {"NT", "PT", "WT", "ST"}:
        raise ProtocolError(f"unknown prompt arm {arm}")
    if arm != "NT" and task["depth"] == 1:
        raise ProtocolError("trace arm is not defined at depth 1")
    if arm == "ST" and task["depth"] != 3:
        raise ProtocolError("ST is defined only at depth 3")
    options = [f"{label}: {task['option_mapping'][label]}" for label in LABELS]
    operations = " then ".join(task["operation_sequence"])
    states = " ".join(str(value) for value in task["state_space"])
    trace = [] if arm == "NT" else [_trace_line(task, arm)]
    if task["template_id"] == "T-A":
        lines = [
            f"Task family: {task['family']}",
            f"States: {states}",
            "Definitions:",
            *_definitions(task, OPERATOR_NAMES),
            f"Start: {task['start_state']}",
            f"Apply: {operations}",
            "Options:",
            *options,
            *trace,
            "Answer:",
        ]
    elif task["template_id"] == "T-B":
        lines = [
            f"Query: Start: {task['start_state']}; apply {operations}.",
            "Options:",
            *options,
            f"State legend: {states}",
            "Operator definitions:",
            *_definitions(task, tuple(reversed(OPERATOR_NAMES))),
            *trace,
            "Answer:",
        ]
    else:
        raise ProtocolError("unregistered template")
    return "\n".join(lines)


def _validate_anchor(prompt: str, anchor: Mapping[str, Any], start_state: int) -> None:
    if set(anchor) != {"field", "surface", "byte_start", "byte_end"}:
        raise ProtocolError("start anchor is not closed")
    surface = str(start_state)
    if anchor["field"] != "Start:" or anchor["surface"] != surface:
        raise ProtocolError("start anchor metadata mismatch")
    raw = prompt.encode("utf-8")
    if raw[anchor["byte_start"] : anchor["byte_end"]] != surface.encode("utf-8"):
        raise ProtocolError("start anchor byte span mismatch")
    if prompt.count(f"Start: {surface}") != 1:
        raise ProtocolError("Start field is not unique")


def _validate_task_common(task: Mapping[str, Any], *, pair_task: bool) -> None:
    expected_keys = PAIR_TASK_KEYS if pair_task else TASK_KEYS
    if set(task) != expected_keys:
        raise ProtocolError(f"task row keys differ: missing={sorted(expected_keys - set(task))} extra={sorted(set(task) - expected_keys)}")
    if not pair_task:
        _require_equal(task["schema_version"], TASK_ROW_VERSION, "/schema_version")
        if task["role"] not in {"development", "behavioral_confirmation"}:
            raise ProtocolError("invalid task role")
    if task["family"] not in FAMILIES or task["depth"] not in DEPTHS or task["template_id"] not in TEMPLATES:
        raise ProtocolError("invalid task cell")
    states, pre_answer, final = _recompute_states(task)
    expected_truth = {
        "intermediate_states": states,
        "pre_answer_intermediate": pre_answer,
        "final_state": final,
    }
    _require_equal(task["ground_truth"], expected_truth, "/ground_truth")
    if len(task["option_values"]) != 4 or len(set(task["option_values"])) != 4:
        raise ProtocolError("option values are not four distinct values")
    if set(task["option_mapping"]) != set(LABELS) or list(task["option_mapping"]) != list(LABELS):
        raise ProtocolError("option mapping is not canonical A/B/C/D")
    if sorted(task["option_mapping"].values()) != sorted(task["option_values"]):
        raise ProtocolError("option mapping/value set mismatch")
    if task["correct_label"] not in LABELS or task["option_mapping"][task["correct_label"]] != final:
        raise ProtocolError("correct label mismatch")
    if task["semantic_id"] != _semantic_id(task):
        raise ProtocolError("semantic id mismatch")

    counterfactual = task.get("counterfactual")
    if counterfactual is not None:
        if set(counterfactual) != {"wrong_pre_answer_intermediate", "implied_final_state", "implied_label"}:
            raise ProtocolError("counterfactual is not closed")
        wrong = counterfactual["wrong_pre_answer_intermediate"]
        if wrong == pre_answer or not 0 <= wrong < len(task["state_space"]):
            raise ProtocolError("wrong trace intermediate is invalid")
        final_operator = {x["name"]: x for x in task["operators"]}[task["operation_sequence"][-1]]
        implied = _operator_map(final_operator, wrong, task["family"])
        if implied == final or counterfactual["implied_final_state"] != implied:
            raise ProtocolError("counterfactual implied final mismatch")
        label = next((label for label in LABELS if task["option_mapping"][label] == implied), None)
        if label is None or counterfactual["implied_label"] != label:
            raise ProtocolError("counterfactual answer is not registered in options")

    if pair_task:
        expected_prompt = independent_render_task(task, "NT")
        if task["nt_prompt"] != expected_prompt or task["prompt_sha256"] != sha256_bytes(expected_prompt.encode("utf-8")):
            raise ProtocolError("pair task prompt/hash mismatch")
        _validate_anchor(expected_prompt, task["start_anchor"], task["start_state"])
        if task["correct_label"] not in LABELS:
            raise ProtocolError("pair task label invalid")
        return

    expected_arms = {"NT"}
    if task["depth"] in {2, 3}:
        expected_arms.update({"PT", "WT"})
    if task["depth"] == 3:
        expected_arms.add("ST")
    if set(task["prompts"]) != expected_arms or set(task["prompt_hashes"]) != expected_arms:
        raise ProtocolError("task prompt-arm closure mismatch")
    for arm in sorted(expected_arms):
        rendered = independent_render_task(task, arm)
        if task["prompts"][arm] != rendered:
            raise ProtocolError(f"rendered prompt mismatch for {arm}")
        if task["prompt_hashes"][arm] != sha256_bytes(rendered.encode("utf-8")):
            raise ProtocolError(f"prompt hash mismatch for {arm}")
        _validate_anchor(rendered, task["start_anchor"], task["start_state"])
    if not all(prompt.endswith("Answer:") for prompt in task["prompts"].values()):
        raise ProtocolError("prompt does not end in exact Answer: bytes")
    forbidden = ("<think>", "reason step by step", "solution:", "answer: ?")
    if any(token in prompt.casefold() for prompt in task["prompts"].values() for token in forbidden):
        raise ProtocolError("prompt contains a forbidden reasoning/placeholder surface")
    expected_balance = {
        "correct_label": task["correct_label"],
        "template_id": task["template_id"],
        "start_state": task["start_state"],
        "pre_answer_intermediate": pre_answer,
        "final_state": final,
        "final_operator": task["operation_sequence"][-1],
    }
    _require_equal(task["balance"], expected_balance, "/balance")


def verify_task_row(row: Mapping[str, Any]) -> None:
    _validate_task_common(row, pair_task=False)


def _pair_semantic_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "family": row["family"],
        "depth": row["depth"],
        "option_value_set": sorted(row["option_values"]),
        "donor_semantic_id": row["primary"]["donor"]["semantic_id"],
        "recipient_semantic_id": row["primary"]["recipient"]["semantic_id"],
        "same_intermediate_semantic_id": row["controls"]["same_intermediate_donor"]["semantic_id"],
        "same_answer_semantic_id": row["controls"]["same_answer_donor"]["semantic_id"],
        "random_semantic_id": row["controls"]["random_donor"]["semantic_id"],
        "m_d": row["primary"]["donor_intermediate"],
        "m_r": row["primary"]["recipient_intermediate"],
        "a_d": row["primary"]["donor_answer"],
        "a_r": row["primary"]["recipient_answer"],
        "a_x": row["primary"]["recombinant_answer"],
    }


def verify_pair_row(row: Mapping[str, Any]) -> None:
    if set(row) != PAIR_KEYS:
        raise ProtocolError(f"pair row keys differ: missing={sorted(PAIR_KEYS - set(row))} extra={sorted(set(row) - PAIR_KEYS)}")
    _require_equal(row["schema_version"], PAIR_ROW_VERSION, "/schema_version")
    if row["role"] not in {"mechanistic_development", "mechanistic_candidate_confirmation"}:
        raise ProtocolError("invalid pair role")
    if row["family"] not in FAMILIES or row["depth"] not in COMPOSITIONAL_DEPTHS or row["template_id"] not in TEMPLATES:
        raise ProtocolError("invalid pair cell")
    if row["state_space"] != list(range(_state_count(row["family"]))):
        raise ProtocolError("pair state space mismatch")
    if set(row["option_mapping"]) != set(LABELS) or list(row["option_mapping"]) != list(LABELS):
        raise ProtocolError("pair option mapping is not canonical")
    if sorted(row["option_mapping"].values()) != sorted(row["option_values"]) or len(set(row["option_values"])) != 4:
        raise ProtocolError("pair option set mismatch")
    if set(row["primary"]) != {
        "donor",
        "recipient",
        "donor_intermediate",
        "recipient_intermediate",
        "donor_answer",
        "recipient_answer",
        "recombinant_answer",
        "donor_label",
        "recipient_label",
        "recombinant_label",
    }:
        raise ProtocolError("primary pair object is not closed")
    if set(row["controls"]) != {"no_op_donor", "same_intermediate_donor", "same_answer_donor", "random_donor"}:
        raise ProtocolError("pair controls are not closed")
    tasks = [row["primary"]["donor"], row["primary"]["recipient"], *row["controls"].values()]
    for task in tasks:
        _validate_task_common(task, pair_task=True)
        if task["family"] != row["family"] or task["depth"] != row["depth"] or task["template_id"] != row["template_id"]:
            raise ProtocolError("pair task cell mismatch")
        if task["option_values"] != row["option_values"] or task["option_mapping"] != row["option_mapping"]:
            raise ProtocolError("pair task does not share exact option mapping")

    donor = row["primary"]["donor"]
    recipient = row["primary"]["recipient"]
    m_d = donor["ground_truth"]["pre_answer_intermediate"]
    m_r = recipient["ground_truth"]["pre_answer_intermediate"]
    a_d = donor["ground_truth"]["final_state"]
    a_r = recipient["ground_truth"]["final_state"]
    final_operator = {x["name"]: x for x in recipient["operators"]}[recipient["operation_sequence"][-1]]
    a_x = _operator_map(final_operator, m_d, row["family"])
    if len({a_d, a_r, a_x}) != 3:
        raise ProtocolError("donor/recipient/recombinant answers are not pairwise distinct")
    expected_primary = {
        "donor": donor,
        "recipient": recipient,
        "donor_intermediate": m_d,
        "recipient_intermediate": m_r,
        "donor_answer": a_d,
        "recipient_answer": a_r,
        "recombinant_answer": a_x,
        "donor_label": donor["correct_label"],
        "recipient_label": recipient["correct_label"],
        "recombinant_label": next(label for label in LABELS if row["option_mapping"][label] == a_x),
    }
    _require_equal(row["primary"], expected_primary, "/primary")
    if len({expected_primary["donor_label"], expected_primary["recipient_label"], expected_primary["recombinant_label"]}) != 3:
        raise ProtocolError("primary option labels are not pairwise distinct")
    if row["controls"]["no_op_donor"] != recipient:
        raise ProtocolError("no-op donor is not byte-identical to recipient object")
    if row["controls"]["same_intermediate_donor"]["ground_truth"]["pre_answer_intermediate"] != m_r:
        raise ProtocolError("same-intermediate donor does not share recipient intermediate")
    if row["controls"]["same_intermediate_donor"]["semantic_id"] == recipient["semantic_id"]:
        raise ProtocolError("same-intermediate donor is not semantically distinct")
    same_answer = row["controls"]["same_answer_donor"]
    if same_answer["ground_truth"]["final_state"] != a_r or same_answer["ground_truth"]["pre_answer_intermediate"] == m_r:
        raise ProtocolError("same-answer/different-intermediate control mismatch")
    random_donor = row["controls"]["random_donor"]
    if random_donor["ground_truth"]["pre_answer_intermediate"] == m_r or random_donor["ground_truth"]["final_state"] == a_r:
        raise ProtocolError("random donor accidentally matches recipient state or answer")
    if len({donor["semantic_id"], recipient["semantic_id"], same_answer["semantic_id"], row["controls"]["same_intermediate_donor"]["semantic_id"], random_donor["semantic_id"]}) != 5:
        raise ProtocolError("non-no-op pair tasks are not semantically unique")

    if row["pair_semantic_id"] != sha256_bytes(canonical_json_bytes(_pair_semantic_payload(row))):
        raise ProtocolError("pair semantic hash mismatch")
    if row["pair_id"] != f"{row['role']}:{row['family']}:d{row['depth']}:{row['pair_semantic_id'][:16]}":
        raise ProtocolError("pair id mismatch")
    expected_partition = "front" if int(row["pair_semantic_id"][:2], 16) < 128 else "back"
    if row["hash_partition"] != expected_partition:
        raise ProtocolError("pair hash partition mismatch")
    _require_equal(row["wrong_position_anchor"], recipient["start_anchor"], "/wrong_position_anchor")
    selector = row["stage_t_selector"]
    if selector != {
        "sort_key": row["pair_semantic_id"],
        "filter": "all_three_models_exact_pair_length_and_answer_position_alignment",
        "selection": "first_128_per_role_family_depth_by_sort_key",
        "outcome_fields_allowed": [],
    }:
        raise ProtocolError("Stage T selector is not frozen/mechanics-only")
    expected_balance = {
        "recipient_correct_label": recipient["correct_label"],
        "template_id": row["template_id"],
        "recipient_start_state": recipient["start_state"],
        "recipient_pre_answer_intermediate": m_r,
        "recipient_final_state": a_r,
        "recipient_final_operator": recipient["operation_sequence"][-1],
        "hash_partition": row["hash_partition"],
    }
    _require_equal(row["balance"], expected_balance, "/balance")


def _spread(counter: Counter[Any]) -> int:
    return max(counter.values()) - min(counter.values()) if counter else 0


def _complete_counter(rows: Sequence[Mapping[str, Any]], field: str, values: Sequence[Any]) -> Counter[Any]:
    counter = Counter(row["balance"][field] for row in rows)
    for value in values:
        counter.setdefault(value, 0)
    return counter


def _validate_cell_balance(rows: Sequence[Mapping[str, Any]], *, pair_rows: bool) -> dict[str, Any]:
    expected = len(rows)
    labels_field = "recipient_correct_label" if pair_rows else "correct_label"
    labels = _complete_counter(rows, labels_field, LABELS)
    templates = _complete_counter(rows, "template_id", TEMPLATES)
    if set(labels.values()) != {expected // 4}:
        raise ProtocolError(f"answer labels are not exactly balanced: {labels}")
    if set(templates.values()) != {expected // 2}:
        raise ProtocolError(f"templates are not exactly balanced: {templates}")
    size = len(rows[0]["state_space"])
    start_field = "recipient_start_state" if pair_rows else "start_state"
    pre_field = "recipient_pre_answer_intermediate" if pair_rows else "pre_answer_intermediate"
    final_field = "recipient_final_state" if pair_rows else "final_state"
    op_field = "recipient_final_operator" if pair_rows else "final_operator"
    counters = {
        "labels": labels,
        "templates": templates,
        "start": _complete_counter(rows, start_field, tuple(range(size))),
        "pre_answer": _complete_counter(rows, pre_field, tuple(range(size))),
        "final": _complete_counter(rows, final_field, tuple(range(size))),
        "final_operator": _complete_counter(rows, op_field, OPERATOR_NAMES),
    }
    for name in ("start", "pre_answer", "final", "final_operator"):
        if _spread(counters[name]) > 1:
            raise ProtocolError(f"{name} balance spread exceeds one: {counters[name]}")
    # Each registered single field must leave label counts as even as arithmetic
    # permits.  This is the finite-bank anti-option-prior rule.
    surface_fields = ["template_id", start_field, pre_field, final_field, op_field]
    conditional: dict[str, Any] = {}
    for field in surface_fields:
        table: dict[str, dict[str, int]] = {}
        grouped: defaultdict[Any, Counter[str]] = defaultdict(Counter)
        for row in rows:
            grouped[row["balance"][field]][row["balance"][labels_field]] += 1
        for value, counts in grouped.items():
            complete = Counter({label: counts[label] for label in LABELS})
            if _spread(complete) > 1:
                raise ProtocolError(f"label leakage balance fails for {field}={value}: {complete}")
            table[str(value)] = dict(complete)
        conditional[field] = table
    return {
        "counts": {name: dict(counter) for name, counter in counters.items()},
        "conditional_label_tables": conditional,
    }


def _iter_prompts(row: Mapping[str, Any], *, pair_rows: bool) -> Iterable[str]:
    if not pair_rows:
        yield from row["prompts"].values()
        return
    yield row["primary"]["donor"]["nt_prompt"]
    yield row["primary"]["recipient"]["nt_prompt"]
    yield row["controls"]["same_intermediate_donor"]["nt_prompt"]
    yield row["controls"]["same_answer_donor"]["nt_prompt"]
    yield row["controls"]["random_donor"]["nt_prompt"]


def _iter_semantic_ids(row: Mapping[str, Any], *, pair_rows: bool) -> Iterable[str]:
    if not pair_rows:
        yield row["semantic_id"]
        return
    yield row["primary"]["donor"]["semantic_id"]
    yield row["primary"]["recipient"]["semantic_id"]
    yield row["controls"]["same_intermediate_donor"]["semantic_id"]
    yield row["controls"]["same_answer_donor"]["semantic_id"]
    yield row["controls"]["random_donor"]["semantic_id"]


def _collect_strings_for_keys(value: Any, keys: set[str]) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in keys and isinstance(child, str):
                yield child
            yield from _collect_strings_for_keys(child, keys)
    elif isinstance(value, list):
        for child in value:
            yield from _collect_strings_for_keys(child, keys)


def collect_protected_prompts(root: Path) -> set[str]:
    prompts: set[str] = set()
    phase1 = root / "data/phase1_task_headroom_candidates.jsonl"
    for row in load_jsonl(phase1):
        prompts.update(_collect_strings_for_keys(row, {"question"}))
    vendored = root / "third_party/jacobian-lens" / JLENS_COMMIT / "data"
    for relative in (
        "evaluations/lens-eval-multihop.json",
        "evaluations/lens-eval-order-ops.json",
        "experiments/probe-swap.json",
    ):
        prompts.update(_collect_strings_for_keys(load_json(vendored / relative), {"prompt"}))
    return prompts


def verify_task_banks(root: Path, *, require_manifest: bool = True) -> dict[str, Any]:
    data_root = root / "studies/study2/data"
    role_rows: dict[str, list[dict[str, Any]]] = {}
    role_semantics: dict[str, set[str]] = {}
    all_exact: set[str] = set()
    all_normalized: set[str] = set()
    balance_report: dict[str, Any] = {}

    for role, filename in BANK_FILES.items():
        rows = load_jsonl(data_root / filename)
        if len(rows) != EXPECTED_ROLE_COUNTS[role]:
            raise ProtocolError(f"{role} count mismatch: {len(rows)}")
        pair_rows = role.startswith("mechanistic")
        for row in rows:
            if row["role"] != role:
                raise ProtocolError(f"row role mismatch in {filename}")
            if pair_rows:
                verify_pair_row(row)
            else:
                verify_task_row(row)
        role_rows[role] = rows
        flattened = [semantic for row in rows for semantic in _iter_semantic_ids(row, pair_rows=pair_rows)]
        if len(flattened) != len(set(flattened)):
            raise ProtocolError(f"duplicate non-no-op semantic identity within {role}")
        role_semantics[role] = set(flattened)
        for prompt in (prompt for row in rows for prompt in _iter_prompts(row, pair_rows=pair_rows)):
            if prompt in all_exact or normalized_prompt(prompt) in all_normalized:
                raise ProtocolError("exact or normalized Study 2 prompt overlap")
            all_exact.add(prompt)
            all_normalized.add(normalized_prompt(prompt))

        depths = COMPOSITIONAL_DEPTHS if pair_rows else DEPTHS
        for family in FAMILIES:
            for depth in depths:
                cell = [row for row in rows if row["family"] == family and row["depth"] == depth]
                if len(cell) != EXPECTED_CELL_COUNTS[role]:
                    raise ProtocolError(f"cell count mismatch for {role}/{family}/d{depth}")
                balance_report[f"{role}/{family}/d{depth}"] = _validate_cell_balance(cell, pair_rows=pair_rows)
                if pair_rows:
                    front = [row for row in cell if row["hash_partition"] == "front"]
                    back = [row for row in cell if row["hash_partition"] == "back"]
                    if len(front) != 128 or len(back) != 128:
                        raise ProtocolError("mechanistic hash partitions are not 128/128")
                    _validate_cell_balance(front, pair_rows=True)
                    _validate_cell_balance(back, pair_rows=True)

    roles = list(BANK_FILES)
    overlaps: dict[str, int] = {}
    for left_index, left in enumerate(roles):
        for right in roles[left_index + 1 :]:
            overlap = role_semantics[left] & role_semantics[right]
            overlaps[f"{left}|{right}"] = len(overlap)
            if overlap:
                raise ProtocolError(f"semantic identity overlap across roles {left}/{right}")

    protected = collect_protected_prompts(root)
    protected_normalized = {normalized_prompt(prompt) for prompt in protected}
    exact_overlap = all_exact & protected
    normalized_overlap = all_normalized & protected_normalized
    if exact_overlap or normalized_overlap:
        raise ProtocolError("Study 2 prompt overlaps a tracked Phase 1 or official S3 prompt")

    manifest_report: dict[str, Any] | None = None
    if require_manifest:
        manifest = load_json(data_root / "task_bank_manifest.json")
        if manifest.get("schema_version") != MANIFEST_VERSION:
            raise ProtocolError("task-bank manifest schema mismatch")
        if manifest.get("status") not in {"CANDIDATE_MODEL_FREE_BANKS", "FROZEN_MODEL_FREE_BANKS"}:
            raise ProtocolError("task-bank manifest has an unregistered lifecycle status")
        expected_files: dict[str, Any] = {}
        for role, filename in BANK_FILES.items():
            path = data_root / filename
            expected_files[role] = {
                "path": f"studies/study2/data/{filename}",
                "rows": len(role_rows[role]),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        _require_equal(manifest["files"], expected_files, "/files")
        _require_equal(manifest["semantic_overlap_counts"], overlaps, "/semantic_overlap_counts")
        _require_equal(manifest["protected_prompt_overlap"], {"exact": 0, "normalized": 0}, "/protected_prompt_overlap")
        _require_equal(manifest["ground_truth_rows_verified"], sum(EXPECTED_ROLE_COUNTS.values()), "/ground_truth_rows_verified")
        _require_equal(manifest["balance"], balance_report, "/balance")
        manifest_report = manifest

    return {
        "role_counts": {role: len(rows) for role, rows in role_rows.items()},
        "balance": balance_report,
        "semantic_overlap_counts": overlaps,
        "protected_prompt_count": len(protected),
        "protected_prompt_overlap": {"exact": len(exact_overlap), "normalized": len(normalized_overlap)},
        "manifest": manifest_report,
    }


def restricted_probabilities(logits: Mapping[str, float]) -> dict[str, float]:
    if set(logits) != set(LABELS) or any(not math.isfinite(value) for value in logits.values()):
        raise ProtocolError("restricted logits must contain four finite A/B/C/D values")
    maximum = max(logits.values())
    weights = {label: math.exp(logits[label] - maximum) for label in LABELS}
    total = sum(weights.values())
    return {label: weights[label] / total for label in LABELS}


def restricted_prediction(logits: Mapping[str, float]) -> str:
    probabilities = restricted_probabilities(logits)
    return max(LABELS, key=lambda label: (probabilities[label], -LABELS.index(label)))


def correct_margin(logits: Mapping[str, float], correct_label: str) -> float:
    if correct_label not in LABELS:
        raise ProtocolError("unregistered correct label")
    restricted_probabilities(logits)
    return logits[correct_label] - max(logits[label] for label in LABELS if label != correct_label)


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if not 0 <= successes <= n or n <= 0 or not math.isfinite(z) or z <= 0:
        raise ProtocolError("invalid Wilson inputs")
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denominator
    return center - half, center + half


def finite_quantile(values: Sequence[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1 or any(not math.isfinite(value) for value in values):
        raise ProtocolError("invalid finite quantile input")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def nt_pass(*, n: int, correct: int, margin_lower95: float, integrity_complete: bool, balance_ok: bool) -> bool:
    if n != 256 or not integrity_complete or not balance_ok:
        return False
    lower, _ = wilson_interval(correct, n)
    return correct / n >= 0.50 and lower > 0.25 and margin_lower95 > 0


def select_mechanistic_depth(depth2_pass: bool, depth3_pass: bool) -> int | None:
    if depth3_pass:
        return 3
    if depth2_pass:
        return 2
    return None


def select_window(layer_scores: Mapping[int, float]) -> tuple[int, int, int]:
    if set(layer_scores) != set(range(9, 23)) or any(not math.isfinite(value) for value in layer_scores.values()):
        raise ProtocolError("window selection requires finite layers 9..22")
    candidates = []
    for start in range(9, 21):
        score = sum(layer_scores[layer] for layer in range(start, start + 3)) / 3
        candidates.append((score, -start, (start, start + 1, start + 2)))
    return max(candidates)[2]


def gx_gd(*, clean: Mapping[str, float], patched: Mapping[str, float], a_x: str, a_d: str, a_r: str) -> tuple[float, float]:
    for logits in (clean, patched):
        if set(logits) != set(LABELS) or any(not math.isfinite(value) for value in logits.values()):
            raise ProtocolError("G_x/G_d require finite A/B/C/D logits")
    if len({a_x, a_d, a_r}) != 3 or any(label not in LABELS for label in (a_x, a_d, a_r)):
        raise ProtocolError("G_x/G_d labels must be pairwise-distinct registered options")
    gx = (patched[a_x] - patched[a_r]) - (clean[a_x] - clean[a_r])
    gd = (patched[a_d] - patched[a_r]) - (clean[a_d] - clean[a_r])
    return gx, gd


def classify_jlens(*, complete: bool, integrity_ok: bool, readout_pass: bool, causal_pass: bool) -> str:
    if not complete:
        return "STUDY2_JLENS_NOT_ESTIMABLE"
    if not integrity_ok:
        return "STUDY2_JLENS_NOT_VALIDATED"
    if readout_pass and causal_pass:
        return "STUDY2_JLENS_VALIDATED"
    if readout_pass != causal_pass:
        return "STUDY2_JLENS_PARTIAL"
    return "STUDY2_JLENS_NOT_VALIDATED"


def classify_composite(
    *,
    operationally_complete: bool,
    integrity_ok: bool,
    internal_families: int,
    distillation_stronger_than_both: bool,
    nt_compositional_families: int,
    pt_support_families: int,
    nt_depth1_any: bool,
) -> str:
    if internal_families not in {0, 1, 2} or nt_compositional_families not in {0, 1, 2} or pt_support_families not in {0, 1, 2}:
        raise ProtocolError("classification family counts must be 0, 1, or 2")
    if not operationally_complete or not integrity_ok:
        return "STUDY2_RESULT_NOT_ESTIMABLE"
    if internal_families == 2:
        if distillation_stronger_than_both:
            return "STUDY2_DISTILLATION_ASSOCIATED_CAUSAL_INTERNAL_REASONING_SUPPORTED"
        return "STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_WITHOUT_DISTILLATION_ATTRIBUTION"
    if internal_families == 1:
        return "STUDY2_CAUSAL_INTERNAL_REASONING_SUPPORTED_ONE_FAMILY_ONLY"
    if nt_compositional_families > 0:
        return "STUDY2_BEHAVIOR_ONLY_WITHOUT_CAUSAL_SUPPORT"
    if pt_support_families == 2:
        return "STUDY2_EXTERNAL_TRACE_DEPENDENCE_ONLY"
    if pt_support_families == 1:
        return "STUDY2_EXTERNAL_TRACE_SUPPORT_ONE_FAMILY_ONLY"
    if nt_depth1_any:
        return "STUDY2_NO_COMPOSITIONAL_BEHAVIORAL_SUPPORT"
    return "STUDY2_TASK_INTERFACE_UNQUALIFIED"


def validate_blocker(state: str, blocker_reason: str | None = None) -> None:
    if state not in OPERATIONAL_BLOCKERS:
        raise ProtocolError("unregistered operational blocker")
    if state == "BLOCKED_ON_STUDY2_EXECUTION" and (blocker_reason is None or not blocker_reason.strip()):
        raise ProtocolError("execution blocker requires a nonempty registered reason")
    if state in SCIENTIFIC_STATES:
        raise ProtocolError("operational blocker cannot be a scientific state")
