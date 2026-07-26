"""Deterministically derive the parser-v3 acceptance gate contract from the frozen parser-v2 contract.

The parser-v2 contract is the single numeric source of truth.  This script never
re-enters a threshold by hand: it loads the frozen v2 contract, applies a small
registered set of identifier substitutions, and then *proves* that no numeric
threshold, metric formula, or population definition changed.

Registered change categories
----------------------------
candidate   the parser under evaluation moves from parser_v2 to parser_v3
comparator  the non-regression comparator moves from legacy to parser_v2
holdout     the sealed holdout moves from parser-v2-v1 to parser-v3-v1
provenance  parser source/version bindings and derivation metadata

Anything else is a bug and makes this script exit non-zero.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from jspace_observation import eval_parsing as legacy_parser  # noqa: E402
from jspace_observation import eval_parsing_v2 as parser_v2  # noqa: E402
from jspace_observation import eval_parsing_v3 as parser_v3  # noqa: E402

SOURCE_CONTRACT = "docs/phase1_parser_v2_acceptance_gates.json"
SOURCE_CONTRACT_SHA256 = (
    "a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988"
)
DERIVED_CONTRACT = "docs/phase1_parser_v3_acceptance_gates.json"
DERIVATION_DIFF = "docs/parser_v2_to_v3_gate_contract_diff.json"

PARSER_V3_IMPLEMENTATION_COMMIT = "310277bcadd67ca9e77986fc292fae47dc5ceda2"

# The sealed parser-v3 holdout, produced and verified in the preceding round.
SEALED_HOLDOUT = {
    "holdout_id": "parser-v3-v1",
    "sealed_prefix": "phase1-evaluator-validation/parser-v3-v1/20260725T160340Z",
    "object_count": 12,
    "set_manifest_sha256": (
        "13f021abd7a052b3b7153b6a0af8ccc13f3bced4b4c280dd3abaa7ab65b949f3"
    ),
    "inputs_manifest_sha256": (
        "ec954093648cb68ce8e6a83db07639bf7de426cc14e35c0a4503b0a6d75ede9d"
    ),
    "labels_manifest_sha256": (
        "ab32c559cd62c72d059fc2527e17d3e806d5ddc9227f8bd8f8f6b0295d7e67a2"
    ),
    "locked_inputs_sha256": (
        "946218357432d6f271e403a883559235a7b59da7832f534bdf7eb33e934c4e06"
    ),
    "locked_labels_sha256": (
        "3e4f1b1bca3862d97a6db37854d1b046ac7a3c606f031b692b58ef1940be2743"
    ),
    "attestation_source": (
        "artifacts/phase1-evaluator-validation/track-d1/"
        "20260725T160340Z-track-d1-parser-v3-seal/02_records.jsonl"
    ),
    "live_verification_required_before_predictions": True,
}

# Registered leaf substitutions: json path -> (old value, new value, category).
LEAF_SUBSTITUTIONS = {
    "/schema_version": (
        "phase1-parser-v2-acceptance-gates/v1",
        "phase1-parser-v3-acceptance-gates/v1",
        "candidate",
    ),
    "/status": (
        "preregistered_before_case_construction",
        "preregistered_before_prediction_generation_and_label_access",
        "provenance",
    ),
    "/legacy_comparison_gates/clean_pooled_non_regression/rule": (
        "parser_v2_correct_count>=legacy_correct_count",
        "parser_v3_correct_count>=parser_v2_correct_count",
        "comparator",
    ),
}

# No container is renamed.  ``load_acceptance_gates`` requires the exact key
# ``legacy_comparison_gates`` and ``_verify_status_logic`` asserts the exact
# string ``all_absolute_and_legacy_comparison_gates_pass`` whenever the result
# is PASS, so renaming either would either break the loader outright or plant a
# landmine that only detonates on a passing run.  The v2-era container name is
# retained and the authoritative comparator is declared by the ``comparator``
# field inside each sub-gate.
PATH_RENAMES: dict[str, str] = {}

# Keys added by the derivation.  Additions may not carry gating thresholds.
ADDED_TOP_LEVEL_KEYS = ("candidate_parser", "comparators", "holdout", "derivation")
ADDED_NESTED_KEYS = {
    "/legacy_comparison_gates/clean_pooled_non_regression/comparator": "comparator",
    "/legacy_comparison_gates/critical_strict_improvement/comparator": "comparator",
    "/legacy_comparison_gates/legacy_adapter/applies_to": "comparator",
}


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(document: object) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def flatten(document: object, prefix: str = "") -> dict[str, object]:
    """Flatten to leaf scalars keyed by json path.  Lists keep positional paths."""
    flat: dict[str, object] = {}
    if isinstance(document, dict):
        for key, value in document.items():
            flat.update(flatten(value, f"{prefix}/{key}"))
    elif isinstance(document, list):
        for index, value in enumerate(document):
            flat.update(flatten(value, f"{prefix}[{index}]"))
    else:
        flat[prefix] = document
    return flat


def apply_renames(flat: dict[str, object]) -> dict[str, object]:
    renamed: dict[str, object] = {}
    for path, value in flat.items():
        for old, new in PATH_RENAMES.items():
            if path == old or path.startswith(old + "/"):
                path = new + path[len(old) :]
                break
        renamed[path] = value
    return renamed


def parser_identity(module: object, name: str, commit: str | None) -> dict[str, object]:
    relative = f"src/jspace_observation/{module.__name__.rsplit('.', 1)[-1]}.py"
    identity = {
        "parser": name,
        "module": relative,
        "source_blob_sha256": git_blob_sha256(relative),
    }
    for attribute, field in (
        ("PARSER_ALGORITHM_ID", "algorithm_id"),
        ("PARSER_SOURCE_SHA256", "source_sha256"),
        ("PARSER_VERSION", "parser_version"),
        ("PARSER_NORMALIZER_ID", "normalizer_id"),
    ):
        if hasattr(module, attribute):
            identity[field] = getattr(module, attribute)
    if commit is not None:
        identity["implementation_commit"] = commit
    return identity


def git_blob_sha256(relative_path: str) -> str:
    blob = subprocess.run(
        ["git", "show", f"HEAD:{relative_path}"],
        capture_output=True,
        cwd=REPO_ROOT,
        check=True,
    ).stdout
    return hashlib.sha256(blob).hexdigest()


def derive(v2_contract: dict) -> dict:
    derived = json.loads(json.dumps(v2_contract))

    derived["schema_version"] = LEAF_SUBSTITUTIONS["/schema_version"][1]
    derived["status"] = LEAF_SUBSTITUTIONS["/status"][1]
    derived["legacy_comparison_gates"]["clean_pooled_non_regression"]["rule"] = (
        LEAF_SUBSTITUTIONS[
            "/legacy_comparison_gates/clean_pooled_non_regression/rule"
        ][1]
    )

    derived["legacy_comparison_gates"]["clean_pooled_non_regression"][
        "comparator"
    ] = "parser_v2"
    derived["legacy_comparison_gates"]["critical_strict_improvement"][
        "comparator"
    ] = "parser_v2"
    derived["legacy_comparison_gates"]["legacy_adapter"]["applies_to"] = (
        "legacy_comparator_reporting_only"
    )

    derived["candidate_parser"] = parser_identity(
        parser_v3, "parser_v3", PARSER_V3_IMPLEMENTATION_COMMIT
    )
    derived["comparators"] = {
        "non_regression": parser_identity(parser_v2, "parser_v2", None),
        "secondary_reporting_only": parser_identity(
            legacy_parser, "legacy", None
        ),
        "note": (
            "parser_v2 is the gating non-regression comparator; the legacy parser is "
            "reported for continuity and gates nothing in this contract"
        ),
    }
    derived["holdout"] = dict(SEALED_HOLDOUT)
    derived["derivation"] = {
        "source_contract": SOURCE_CONTRACT,
        "source_contract_sha256": SOURCE_CONTRACT_SHA256,
        "derivation_script": "scripts/derive_parser_v3_gate_contract.py",
        "manual_threshold_entry": False,
        "thresholds_inherited_verbatim": True,
        "threshold_preregistration_note": (
            "every numeric threshold is inherited unchanged from a contract that was "
            "preregistered before any case of either holdout existed; this v3 "
            "instantiation is preregistered before prediction generation and before "
            "any parser-v3 label access, but after parser-v3 holdout construction"
        ),
        "registered_change_categories": [
            "candidate",
            "comparator",
            "holdout",
            "provenance",
        ],
    }
    return derived


def build_diff(v2_contract: dict, v3_contract: dict) -> dict:
    flat_v2 = apply_renames(flatten(v2_contract))
    flat_v3 = flatten(v3_contract)

    added_prefixes = tuple(f"/{key}" for key in ADDED_TOP_LEVEL_KEYS)
    inherited_v3 = {
        path: value
        for path, value in flat_v3.items()
        if not path.startswith(added_prefixes) and path not in ADDED_NESTED_KEYS
    }

    removed = sorted(set(flat_v2) - set(inherited_v3))
    introduced = sorted(set(inherited_v3) - set(flat_v2))
    changed = [
        {
            "path": path,
            "from": flat_v2[path],
            "to": inherited_v3[path],
            "category": LEAF_SUBSTITUTIONS.get(path, (None, None, "UNREGISTERED"))[2],
        }
        for path in sorted(set(flat_v2) & set(inherited_v3))
        if flat_v2[path] != inherited_v3[path]
    ]

    def numeric_leaves(flat: dict[str, object]) -> dict[str, object]:
        return {
            path: value
            for path, value in flat.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }

    numeric_v2 = numeric_leaves(flat_v2)
    numeric_v3 = numeric_leaves(inherited_v3)
    numeric_changes = sorted(
        path
        for path in set(numeric_v2) | set(numeric_v3)
        if numeric_v2.get(path) != numeric_v3.get(path)
    )

    population_roots = (
        "/dataset_contract",
        "/absolute_gates",
        "/legacy_comparison_gates",
    )
    population_v2 = {
        path: value
        for path, value in flat_v2.items()
        if path.startswith(population_roots)
        and (
            "[" in path
            or path.rsplit("/", 1)[-1]
            in {
                "denominator",
                "population",
                "positive_support",
                "cases_per_stratum",
                "total_cases",
                "stratum",
            }
        )
    }
    population_v3 = {
        path: value for path, value in inherited_v3.items() if path in population_v2
    }
    population_changes = sorted(
        path
        for path in set(population_v2) | set(population_v3)
        if population_v2.get(path) != population_v3.get(path)
    )

    semantic_v2 = {
        path: value for path, value in flat_v2.items() if isinstance(value, str)
    }
    semantic_changes = sorted(
        path
        for path, value in semantic_v2.items()
        if inherited_v3.get(path) != value and path not in LEAF_SUBSTITUTIONS
    )

    unregistered = [entry for entry in changed if entry["category"] == "UNREGISTERED"]

    return {
        "schema_version": "phase1-parser-v2-to-v3-gate-contract-diff/v1",
        "source_contract": SOURCE_CONTRACT,
        "source_contract_sha256": SOURCE_CONTRACT_SHA256,
        "derived_contract": DERIVED_CONTRACT,
        "path_renames": PATH_RENAMES,
        "changed_leaves": changed,
        "added_top_level_keys": list(ADDED_TOP_LEVEL_KEYS),
        "added_nested_keys": ADDED_NESTED_KEYS,
        "removed_paths": removed,
        "unexpectedly_introduced_paths": introduced,
        "numeric_threshold_changes": len(numeric_changes),
        "numeric_threshold_change_paths": numeric_changes,
        "metric_semantic_changes": len(semantic_changes),
        "metric_semantic_change_paths": semantic_changes,
        "population_definition_changes": len(population_changes),
        "population_definition_change_paths": population_changes,
        "unregistered_changes": len(unregistered),
        "unregistered_change_paths": [entry["path"] for entry in unregistered],
        "inherited_numeric_leaf_count": len(numeric_v2),
        "verdict": (
            "DERIVATION_FAITHFUL"
            if not (
                numeric_changes
                or semantic_changes
                or population_changes
                or unregistered
                or removed
                or introduced
            )
            else "DERIVATION_UNFAITHFUL"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify existing outputs instead of writing them",
    )
    args = parser.parse_args()

    source_path = REPO_ROOT / SOURCE_CONTRACT
    actual = git_blob_sha256(SOURCE_CONTRACT)
    if actual != SOURCE_CONTRACT_SHA256:
        print(
            f"FATAL: source contract digest {actual} != frozen {SOURCE_CONTRACT_SHA256}"
        )
        return 2

    v2_contract = json.loads(source_path.read_text(encoding="utf-8"))
    v3_contract = derive(v2_contract)
    diff = build_diff(v2_contract, v3_contract)

    contract_bytes = canonical_bytes(v3_contract)
    diff["derived_contract_sha256"] = hashlib.sha256(contract_bytes).hexdigest()

    # The derived contract must be accepted verbatim by the frozen loader that
    # the scoring stage actually uses.  A contract that cannot be loaded is
    # worse than no contract at all, so this is checked before it is written.
    from jspace_observation import parser_v2_locked_evaluation as locked_eval

    try:
        locked_eval.load_acceptance_gates(
            contract_bytes, expected_sha256=diff["derived_contract_sha256"]
        )
    except Exception as error:  # noqa: BLE001 - surfaced verbatim on purpose
        diff["frozen_loader_accepts_derived_contract"] = False
        diff["frozen_loader_error"] = f"{type(error).__name__}: {error}"
        diff["verdict"] = "DERIVATION_UNFAITHFUL"
    else:
        diff["frozen_loader_accepts_derived_contract"] = True

    diff_bytes = canonical_bytes(diff)

    contract_path = REPO_ROOT / DERIVED_CONTRACT
    diff_path = REPO_ROOT / DERIVATION_DIFF

    if args.check:
        ok = True
        for path, expected in ((contract_path, contract_bytes), (diff_path, diff_bytes)):
            on_disk = path.read_bytes().replace(b"\r\n", b"\n")
            if on_disk != expected:
                print(f"MISMATCH: {path.name} differs from deterministic derivation")
                ok = False
        print("CHECK PASS" if ok else "CHECK FAIL")
        return 0 if ok else 1

    contract_path.write_bytes(contract_bytes)
    diff_path.write_bytes(diff_bytes)
    print(json.dumps({k: v for k, v in diff.items() if not isinstance(v, (list, dict))}, indent=2))
    return 0 if diff["verdict"] == "DERIVATION_FAITHFUL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
