"""Targeted tests for enabling the parser-v3 one-shot locked evaluation.

These cover only the parts of the frozen parser-v2 machinery that had to change
so parser v3 can be evaluated through it. They are deliberately synthetic and
never touch a sealed holdout, a locked input, or a locked label.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).parent.parent
PARSER_V3_PATH = ROOT / "src" / "jspace_observation" / "eval_parsing_v3.py"
GATE_CONTRACT_PATH = ROOT / "docs" / "phase1_parser_v3_acceptance_gates.json"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


finalizer = _load_module(
    "_test_v3_finalize_parser_v2_locked_evaluation",
    ROOT / "scripts" / "finalize_parser_v2_locked_evaluation.py",
)


def _lf_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


class TestStageEBlocksParserV3:
    """Stage E must be parser-free, including for the candidate parser."""

    def test_v3_filename_is_forbidden(self):
        assert "eval_parsing_v3.py" in finalizer.FORBIDDEN_FILENAMES

    def test_v3_module_part_is_forbidden(self):
        assert "eval_parsing_v3" in finalizer.FORBIDDEN_MODULE_PARTS

    def test_v3_entry_symbol_is_a_forbidden_code_name(self):
        assert "parse_v3" in finalizer._FORBIDDEN_CODE_NAMES

    def test_real_v3_source_path_is_blocked(self):
        assert PARSER_V3_PATH.exists()
        assert finalizer._forbidden_parser_path(PARSER_V3_PATH) is True

    @pytest.mark.parametrize(
        "name",
        [
            "eval_parsing_v3.pyc",
            "eval_parsing_v3.cpython-311.pyc",
            "eval_parsing_v3.cpython-311.opt-2.pyc",
        ],
    )
    def test_v3_bytecode_is_blocked(self, tmp_path, name):
        assert finalizer._forbidden_parser_path(tmp_path / name) is True

    def test_real_v3_source_trips_the_definition_probe(self):
        """The probe must fire on the actual frozen parser, not just a stub."""
        assert finalizer._source_defines_parser(PARSER_V3_PATH.read_text("utf-8"))

    def test_definition_probe_matches_parse_v3(self):
        assert finalizer._source_defines_parser("def parse_v3(request):\n    pass\n")

    def test_definition_probe_still_ignores_unrelated_sources(self):
        assert not finalizer._source_defines_parser("def parse_v4(request):\n    pass\n")
        assert not finalizer._source_defines_parser("value = parse_v3\n")

    def test_import_blocker_rejects_v3_module(self):
        blocker = finalizer._ParserImportBlocker()
        with pytest.raises(ImportError):
            blocker.find_spec("jspace_observation.eval_parsing_v3")

    def test_import_blocker_still_allows_unrelated_modules(self):
        blocker = finalizer._ParserImportBlocker()
        assert blocker.find_spec("json") is None

    def test_all_three_parsers_are_blocked_together(self):
        """v3 must not be protected only by the 'eval_parsing' substring."""
        for name in ("eval_parsing.py", "eval_parsing_v2.py", "eval_parsing_v3.py"):
            assert name in finalizer.FORBIDDEN_FILENAMES
            assert (
                finalizer._forbidden_parser_path(
                    ROOT / "src" / "jspace_observation" / name
                )
                is True
            )


class TestParserV3Identity:
    """The candidate parser must remain byte-frozen and self-consistent."""

    @staticmethod
    @pytest.fixture(scope="class")
    def parser() -> ModuleType:
        """Load the frozen parser inside a synthetic package for relative imports."""
        source_root = ROOT / "src" / "jspace_observation"
        package_name = "_test_v3_isolated_package"
        package = ModuleType(package_name)
        package.__path__ = [str(source_root)]
        package.__package__ = package_name
        sys.modules[package_name] = package
        try:
            _load_module(
                f"{package_name}.evaluator_validation",
                source_root / "evaluator_validation.py",
            )
            yield _load_module(
                f"{package_name}.eval_parsing_v3", PARSER_V3_PATH
            )
        finally:
            for name in [n for n in sys.modules if n.startswith(package_name)]:
                sys.modules.pop(name, None)

    def test_declared_digests_match_the_canonical_recomputation(self, parser):
        source = PARSER_V3_PATH.read_bytes()
        assert parser.compute_parser_source_sha256(source) == parser.PARSER_SOURCE_SHA256
        assert (
            parser.compute_parser_version(parser.PARSER_SOURCE_SHA256)
            == parser.PARSER_VERSION
        )

    def test_frozen_identity_values_are_the_preregistered_ones(self, parser):
        assert parser.PARSER_SOURCE_SHA256 == (
            "76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9"
        )
        assert parser.PARSER_VERSION == (
            "0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace"
        )

    def test_parse_v3_matches_the_parse_v2_call_shape(self, parser):
        """The sibling worker is only valid if the entry shape is identical."""
        import inspect

        assert list(inspect.signature(parser.parse_v3).parameters) == ["request"]


class TestParserEvaluationProfiles:
    """Profile selection must be explicit, immutable, and default to v2."""

    @staticmethod
    def _load(name: str, **kwargs):
        loader = _load_module(
            "_test_v3_core_loader", ROOT / "scripts" / "load_locked_evaluation_core.py"
        )
        return loader.load_locked_evaluation_core(name, **kwargs)

    def test_default_profile_is_parser_v2(self):
        core = self._load("_test_v3_core_default")
        assert core.ACTIVE_PARSER_PROFILE_ID == "parser-v2-v1"

    def test_default_profile_preserves_every_frozen_v2_value(self):
        """Existing callers must observe exactly the identity they had before."""
        core = self._load("_test_v3_core_default_values")
        assert core.FROZEN_PARSER_SOURCE_SHA256 == (
            "f538add0bdd6e5a3281d0298b374a99fecea962a91a4cbaa5b4a20795d9a6918"
        )
        assert core.FROZEN_PARSER_GIT_BLOB_OID == (
            "7428dd3fe5be621e32a6331e2d34fd62cea0fb91"
        )
        assert core.FROZEN_PARSER_VERSION == (
            "6cfaec62db37562930a4cb7d3a252bcbf80e1eaf748de98213863ff2566a7f86"
        )
        assert core.FROZEN_PARSER_IMPLEMENTATION_COMMIT == (
            "ab6abec42a13d0e1c193fad7db420dbd512c2f03"
        )
        assert core.FROZEN_ACCEPTANCE_GATE_SHA256 == (
            "a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988"
        )

    def test_v3_profile_binds_the_v3_identity(self):
        core = self._load("_test_v3_core_v3", profile_id="parser-v3-v1")
        assert core.FROZEN_PARSER_VERSION == (
            "0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace"
        )
        assert core.FROZEN_PARSER_GIT_BLOB_OID == (
            "18676eefff3e4f3ed0ce4e592e41e1794365006e"
        )
        assert core.FROZEN_PARSER_IMPLEMENTATION_COMMIT == (
            "310277bcadd67ca9e77986fc292fae47dc5ceda2"
        )
        assert core.FROZEN_ACCEPTANCE_GATE_SHA256 == (
            "2fcc323481221fbc5c1f56b5beccd238fd835303c46df61087e1483dfc28dda7"
        )

    def test_protocol_bundle_is_shared_because_v3_binds_the_v2_bundle(self):
        v2 = self._load("_test_v3_core_bundle_v2")
        v3 = self._load("_test_v3_core_bundle_v3", profile_id="parser-v3-v1")
        assert v2.FROZEN_PROTOCOL_BUNDLE_SHA256 == v3.FROZEN_PROTOCOL_BUNDLE_SHA256
        assert v2.FROZEN_PROTOCOL_COMMIT == v3.FROZEN_PROTOCOL_COMMIT

    def test_v3_binds_its_own_parser_worker_and_gate_contract(self):
        v2 = self._load("_test_v3_core_paths_v2")
        v3 = self._load("_test_v3_core_paths_v3", profile_id="parser-v3-v1")
        added = set(v3.IMAGE_BINDING_SOURCE_PATHS) - set(v2.IMAGE_BINDING_SOURCE_PATHS)
        assert added == {
            "Dockerfile.parser-v3-eval",
            "infra/azure/scripts/09_build_parser_v3_eval.sh",
            "infra/azure/scripts/10_run_parser_v3_locked_eval.sh",
            "scripts/parser_v3_azure_contract.py",
            "src/jspace_observation/eval_parsing_v3.py",
            "scripts/parser_v3_process_worker.py",
            "scripts/run_parser_v3_locked_predictions.py",
            "scripts/finalize_parser_v3_locked_evaluation.py",
            "scripts/stage_p_v3_entrypoint.sh",
            "scripts/stage_p_adopt_v3_entrypoint.sh",
            "scripts/stage_e_v3_entrypoint.sh",
            "docs/phase1_parser_v3_acceptance_gates.json",
            "docs/phase1_parser_v3_locked_evaluation_protocol.md",
        }
        removed = set(v2.IMAGE_BINDING_SOURCE_PATHS) - set(
            v3.IMAGE_BINDING_SOURCE_PATHS
        )
        assert removed == {
            "Dockerfile.parser-v2-eval",
            "infra/azure/scripts/09_build_parser_v2_eval.sh",
            "infra/azure/scripts/10_run_parser_v2_locked_eval.sh",
            "scripts/parser_v2_azure_contract.py",
        }

    def test_v2_binding_paths_are_unchanged_by_the_new_profile(self):
        v2 = self._load("_test_v3_core_paths_unchanged")
        assert "eval_parsing_v3.py" not in " ".join(v2.IMAGE_BINDING_SOURCE_PATHS)
        assert "eval_parsing_v3.py" not in " ".join(v2.RUNTIME_SOURCE_BINDING_PATHS)

    def test_v3_declares_parser_v2_as_a_comparator(self):
        v3 = self._load("_test_v3_core_comparators", profile_id="parser-v3-v1")
        assert v3.ACTIVE_PARSER_PROFILE["comparator_parsers"] == ("parser_v2", "legacy")

    def test_v2_prediction_members_are_byte_identical_to_the_frozen_list(self):
        v2 = self._load("_test_v3_core_members_v2")
        assert v2.PREDICTION_MEMBER_NAMES == (
            ".prediction_reservation.json",
            "prediction_request_manifest.json",
            "parser_v2_locked_predictions.jsonl",
            "legacy_locked_predictions.jsonl",
            "prediction_seal.json",
            "prediction_artifact_manifest.json",
        )

    def test_v3_adds_a_candidate_stream_without_mislabelling_it(self):
        """v3 predictions must never land in a file named for parser v2."""
        v3 = self._load("_test_v3_core_members_v3", profile_id="parser-v3-v1")
        assert (
            v3.CANDIDATE_PREDICTION_FILENAME == "parser_v3_candidate_predictions.jsonl"
        )
        assert v3.PREDICTION_MEMBER_NAMES == (
            ".prediction_reservation.json",
            "prediction_request_manifest.json",
            "parser_v3_candidate_predictions.jsonl",
            "parser_v2_comparator_predictions.jsonl",
            "legacy_comparator_predictions.jsonl",
            "prediction_seal.json",
            "prediction_artifact_manifest.json",
        )

    def test_v3_stream_names_state_their_role(self):
        """Role must be readable from the artifact name, not inferred."""
        v3 = self._load("_test_v3_core_roles", profile_id="parser-v3-v1")
        assert "candidate" in v3.CANDIDATE_PREDICTION_FILENAME
        assert all(
            "comparator" in name for name in v3.COMPARATOR_PREDICTION_FILENAMES
        )

    def test_candidate_algorithm_ids_match_the_parser_sources(self):
        """Guard against a transcribed identifier drifting from the parser."""
        import re

        for profile_id, filename in (
            ("parser-v2-v1", "eval_parsing_v2.py"),
            ("parser-v3-v1", "eval_parsing_v3.py"),
        ):
            core = self._load(f"_test_v3_core_algo_{profile_id}", profile_id=profile_id)
            source = (ROOT / "src" / "jspace_observation" / filename).read_text("utf-8")
            declared = re.search(
                r'^PARSER_ALGORITHM_ID = "([^"]+)"', source, re.MULTILINE
            )
            assert declared is not None
            assert (
                core.ACTIVE_PARSER_PROFILE["candidate_parser_algorithm_id"]
                == declared.group(1)
            )

    def test_v3_runs_three_parsers_because_v2_is_now_a_comparator(self):
        v3 = self._load("_test_v3_core_arity", profile_id="parser-v3-v1")
        assert len(v3.ACTIVE_PARSER_PROFILE["comparator_parsers"]) + 1 == 3

    def test_unknown_profile_is_rejected(self):
        with pytest.raises(Exception):
            self._load("_test_v3_core_bogus", profile_id="parser-v9-v1")

    def test_profile_seed_does_not_leak_into_the_module(self):
        core = self._load("_test_v3_core_no_leak", profile_id="parser-v3-v1")
        assert "_PRESEEDED_PARSER_PROFILE_ID" not in core.__dict__


class TestParserV3Worker:
    """The candidate worker must pin v3 rather than accept it from a caller."""

    WORKER = ROOT / "scripts" / "parser_v3_process_worker.py"

    def test_worker_exists(self):
        assert self.WORKER.exists()

    def test_worker_is_the_faithful_derivation_of_the_v2_worker(self):
        import subprocess

        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "derive_parser_v3_process_worker.py"),
                "--check",
            ],
            capture_output=True,
            cwd=str(ROOT),
        )
        assert completed.returncode == 0, completed.stdout.decode("utf-8", "replace")
        assert b"DERIVATION_FAITHFUL" in completed.stdout

    def test_worker_pins_the_v3_identity_and_never_the_v2_identity(self):
        source = self.WORKER.read_text("utf-8")
        assert (
            "0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace" in source
        )
        assert (
            "6cfaec62db37562930a4cb7d3a252bcbf80e1eaf748de98213863ff2566a7f86"
            not in source
        )
        assert "eval_parsing_v2" not in source
        assert "parse_v2" not in source

    def test_worker_takes_no_arguments_so_it_cannot_be_redirected(self):
        source = self.WORKER.read_text("utf-8")
        assert "argparse" not in source
        assert "sys.argv" not in source

    def test_worker_keeps_the_total_environment_lock(self):
        source = self.WORKER.read_text("utf-8")
        assert 'if dict(os.environ) != _EXPECTED_ENVIRONMENT:' in source


class TestParserV3GateContract:
    """The derived contract must stay loadable by the frozen scoring code."""

    def test_contract_exists_and_is_lf_normalised(self):
        assert GATE_CONTRACT_PATH.exists()
        assert b"\r" not in GATE_CONTRACT_PATH.read_bytes()

    def test_contract_digest_is_the_preregistered_one(self):
        digest = hashlib.sha256(_lf_bytes(GATE_CONTRACT_PATH)).hexdigest()
        assert digest == (
            "2fcc323481221fbc5c1f56b5beccd238fd835303c46df61087e1483dfc28dda7"
        )

    def test_contract_keeps_the_key_the_frozen_loader_requires(self):
        contract = json.loads(GATE_CONTRACT_PATH.read_text("utf-8"))
        assert "legacy_comparison_gates" in contract
        assert set(contract["legacy_comparison_gates"]) == {
            "legacy_adapter",
            "clean_pooled_non_regression",
            "critical_strict_improvement",
        }

    def test_contract_keeps_the_asserted_pass_status_string(self):
        contract = json.loads(GATE_CONTRACT_PATH.read_text("utf-8"))
        assert (
            contract["status_logic"]["PASS"]
            == "all_absolute_and_legacy_comparison_gates_pass"
        )


# ---------------------------------------------------------------------------
# End-to-end coverage of the three-stream path, exercised through the core.
# ---------------------------------------------------------------------------


def _v3_core():
    loader = _load_module(
        "_test_v3_e2e_loader", ROOT / "scripts" / "load_locked_evaluation_core.py"
    )
    return loader.load_locked_evaluation_core(
        "_test_v3_e2e_core", profile_id="parser-v3-v1"
    )


@pytest.fixture(scope="module")
def v3_bundle():
    """Three synthetic streams over the frozen validation dataset.

    Nothing here touches a sealed holdout, a locked input or a locked label.

    The frozen dataset is the parser-v2 fixture, so its case IDs carry the
    ``PV2`` family prefix. The parser-v3 profile owns the ``PV3`` family and
    rejects foreign IDs, so the identifiers are remapped onto the v3 family
    before anything consumes them. Only the family prefix changes; the
    20-hex case suffix, and therefore case identity within the fixture, is
    preserved exactly.
    """
    from copy import deepcopy

    from tests import test_evaluator_validation as frozen_tests

    core = _v3_core()

    def _to_v3_family(value):
        if isinstance(value, str):
            if value.startswith("PV2-"):
                return "PV3-" + value[4:]
            return value
        if isinstance(value, list):
            return [_to_v3_family(item) for item in value]
        if isinstance(value, tuple):
            return tuple(_to_v3_family(item) for item in value)
        if isinstance(value, dict):
            return {key: _to_v3_family(item) for key, item in value.items()}
        return value

    dataset = frozen_tests._dataset()
    labels = deepcopy(dataset["materialized"]["locked_draft_labels"])
    locked_inputs = deepcopy(dataset["materialized"]["locked_inputs"])

    # The frozen builder is the parser-v2 instrument and only accepts PV2 IDs,
    # so it is fed the fixture unchanged. Everything handed to the parser-v3
    # core is remapped onto the v3 family instead.
    candidate = frozen_tests._prediction_envelopes(labels, locked_inputs)
    legacy_source = frozen_tests._legacy_predictions(labels)

    labels = _to_v3_family(labels)
    locked_inputs = _to_v3_family(locked_inputs)
    candidate = _to_v3_family(candidate)
    locked_by_id = {item["case_id"]: item for item in locked_inputs}

    # Remapping the family changes the locked-input bytes, so the envelope's
    # input_record_sha256 and parser_request_sha256 have to be rebuilt over the
    # remapped record. The parser_result payload is carried across untouched
    # apart from the candidate's parser version, which the builder validates.
    for row in candidate:
        row["parser_result"]["parser_version"] = core.FROZEN_PARSER_VERSION

    candidate = [
        core.build_prediction_envelope(
            locked_by_id[row["case_id"]], row["parser_result"]
        )
        for row in candidate
    ]

    v2_version = core.FROZEN_COMPARATOR_PARSER_IDENTITIES["parser_v2"][
        "parser_version"
    ]
    comparator = deepcopy(candidate)
    for row in comparator:
        row["parser_result"]["parser_version"] = v2_version

    legacy_rows = []
    for row in legacy_source:
        parsed = row["parsed_answer"]
        legacy_rows.append(
            core.build_legacy_prediction(
                locked_by_id["PV3-" + row["case_id"][4:]],
                {
                    "parsed_answer": parsed,
                    "parse_valid": row["parse_valid"],
                    "parse_error_type": (
                        None if row["parse_valid"] else "no_numeric_found"
                    ),
                    "parse_ambiguous": row["parse_ambiguous"],
                    "parse_strategy": "synthetic_frozen_legacy",
                    "candidate_answers": [] if parsed is None else [parsed],
                    "answer_format_warning": None,
                },
            )
        )
    return {
        "core": core,
        "labels": labels,
        "locked_inputs": locked_inputs,
        "candidate": candidate,
        "comparator": comparator,
        "legacy": legacy_rows,
        "gates": core.load_frozen_gate_bytes(ROOT),
    }


class TestParserV3ThreeStreamScoring:
    """The v3 contract gates against parser v2, so the scorer must too."""

    def test_gating_comparator_is_parser_v2_not_legacy(self, v3_bundle):
        core = v3_bundle["core"]
        gates = core.load_acceptance_gates(v3_bundle["gates"])
        assert core._gating_comparator_parser_version(gates) == (
            core.FROZEN_COMPARATOR_PARSER_IDENTITIES["parser_v2"][
                "parser_version"
            ]
        )

    def test_scoring_the_v2_comparator_stream_succeeds(self, v3_bundle):
        core = v3_bundle["core"]
        metrics, _failures = core.score_locked_evaluation(
            v3_bundle["labels"],
            v3_bundle["candidate"],
            v3_bundle["comparator"],
            v3_bundle["gates"],
            raise_on_invalid=True,
        )
        assert metrics["status"] in {"PASS", "FAIL"}

    def test_metrics_name_the_parsers_behind_the_legacy_field_names(
        self, v3_bundle
    ):
        core = v3_bundle["core"]
        metrics, _failures = core.score_locked_evaluation(
            v3_bundle["labels"],
            v3_bundle["candidate"],
            v3_bundle["comparator"],
            v3_bundle["gates"],
            raise_on_invalid=True,
        )
        attribution = metrics["parser_attribution"]
        assert attribution["candidate_parser"] == "parser_v3"
        assert attribution["gating_comparator_parser"] == "parser_v2"
        assert attribution["gating_comparator_field_prefix"] == "legacy"
        assert attribution["reporting_only_comparators"] == ["legacy"]

    def test_scoring_ledger_accepts_the_envelope_shaped_comparator(
        self, v3_bundle
    ):
        """The gating stream is a parser envelope, not a legacy adapter row."""
        core = v3_bundle["core"]
        gates = core.load_acceptance_gates(v3_bundle["gates"])
        label = v3_bundle["labels"][0]
        case_id = label["case_id"]
        prediction = next(
            row for row in v3_bundle["candidate"] if row["case_id"] == case_id
        )
        comparator = next(
            row for row in v3_bundle["comparator"] if row["case_id"] == case_id
        )
        row = core._scoring_ledger_row(
            label,
            prediction,
            comparator,
            label_row_bytes=core.canonical_json_bytes(label),
            prediction_row_bytes=core.canonical_json_bytes(prediction),
            legacy_row_bytes=core.canonical_json_bytes(comparator),
            row_index=0,
            context={},
            gates=gates,
        )
        assert row["case_id"] == case_id

    def test_reporting_only_legacy_pass_has_no_verdict(self, v3_bundle):
        core = v3_bundle["core"]
        aggregates = core.score_reporting_only_legacy_comparator(
            core.canonical_jsonl_bytes(v3_bundle["labels"]),
            core.canonical_jsonl_bytes(v3_bundle["candidate"]),
            core.canonical_jsonl_bytes(v3_bundle["legacy"]),
            v3_bundle["gates"],
        )
        assert "status" not in aggregates


class TestParserV3StreamMembership:
    """Membership, ordering and identity must be exact across three streams."""

    def test_registered_upload_order_places_streams_in_member_order(
        self, v3_bundle
    ):
        core = v3_bundle["core"]
        assert core.PREDICTION_MEMBER_NAMES[2:5] == (
            "parser_v3_candidate_predictions.jsonl",
            "parser_v2_comparator_predictions.jsonl",
            "legacy_comparator_predictions.jsonl",
        )

    def test_candidate_never_writes_into_the_v2_member_path(self, v3_bundle):
        core = v3_bundle["core"]
        assert (
            core.CANDIDATE_PREDICTION_FILENAME
            != "parser_v2_locked_predictions.jsonl"
        )
        assert "parser_v2_locked_predictions.jsonl" not in (
            core.PREDICTION_MEMBER_NAMES
        )

    def test_all_three_streams_share_one_case_membership(self, v3_bundle):
        ids = [row["case_id"] for row in v3_bundle["candidate"]]
        assert [row["case_id"] for row in v3_bundle["comparator"]] == ids
        assert [row["case_id"] for row in v3_bundle["legacy"]] == ids

    def test_swapped_candidate_and_comparator_streams_are_rejected(
        self, v3_bundle
    ):
        core = v3_bundle["core"]
        with pytest.raises(core.LockedEvaluationError):
            core.score_locked_evaluation(
                v3_bundle["labels"],
                v3_bundle["comparator"],
                v3_bundle["candidate"],
                v3_bundle["gates"],
                raise_on_invalid=True,
            )

    def test_comparator_identity_cannot_be_invented_by_a_caller(
        self, v3_bundle
    ):
        core = v3_bundle["core"]
        locked = v3_bundle["locked_inputs"][0]
        envelope = next(
            row
            for row in v3_bundle["candidate"]
            if row["case_id"] == locked["case_id"]
        )
        with pytest.raises(core.LockedEvaluationError):
            core.validate_prediction_envelope(
                envelope, locked, expected_parser_version="0" * 64
            )


class TestParserV3ProfileIsNotOverridable:
    """The candidate is chosen by entrypoint, never by argv or environment."""

    def test_candidate_identity_is_not_taken_from_argv(self):
        source = (
            ROOT / "scripts" / "run_parser_v3_locked_predictions.py"
        ).read_text("utf-8")
        assert 'PROFILE_ID = "parser-v3-v1"' in source
        assert "argv" not in source.split("def main")[0]

    def test_candidate_identity_is_not_taken_from_the_environment(self):
        source = (
            ROOT / "scripts" / "run_parser_v3_locked_predictions.py"
        ).read_text("utf-8")
        assert "os.environ" not in source
        assert "getenv" not in source

    def test_profile_is_immutable_after_import(self):
        core = _v3_core()
        assert "_PRESEEDED_PARSER_PROFILE_ID" not in core.__dict__
        assert core.ACTIVE_PARSER_PROFILE_ID == "parser-v3-v1"

    def test_stage_e_launcher_pins_the_scoring_profile(self):
        source = (
            ROOT / "scripts" / "finalize_parser_v3_locked_evaluation.py"
        ).read_text("utf-8")
        assert 'PROFILE_ID = "parser-v3-v1"' in source
        assert "os.environ" not in source


class TestFrozenSourcesRemainByteIdentical:
    """A source freeze that is not checked is not a freeze."""

    @pytest.mark.parametrize(
        "relative,digest",
        [
            (
                "src/jspace_observation/eval_parsing_v3.py",
                "dd729c3c23771fb112811e382bf7e55f531ce534cbbd1cfec4f0527056c8908e",
            ),
            (
                "src/jspace_observation/eval_parsing_v2.py",
                "fe02781545e26c2f97d1731e985d081a2f1468950bec4d88700647849243d182",
            ),
            (
                "src/jspace_observation/eval_parsing.py",
                "4b07b91859aca33b51af9c15b08f07026f11b0141f1300fd3f942138b731177e",
            ),
        ],
    )
    def test_frozen_parser_source_bytes_are_unchanged(self, relative, digest):
        """Plain byte identity of the checked-in source, newline-normalised."""
        path = ROOT.joinpath(*relative.split("/"))
        assert hashlib.sha256(_lf_bytes(path)).hexdigest() == digest

    def test_registered_canonical_parser_identities_are_unchanged(self):
        """The registered digests are domain-separated, not plain file hashes."""
        core = _v3_core()
        assert core.FROZEN_PARSER_SOURCE_SHA256 == (
            "76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9"
        )
        assert core.FROZEN_PARSER_VERSION == (
            "0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace"
        )
        assert core.FROZEN_COMPARATOR_PARSER_IDENTITIES["parser_v2"][
            "parser_source_sha256"
        ] == (
            "f538add0bdd6e5a3281d0298b374a99fecea962a91a4cbaa5b4a20795d9a6918"
        )
        assert core.FROZEN_LEGACY_PARSER_SOURCE_SHA256 == (
            "4b07b91859aca33b51af9c15b08f07026f11b0141f1300fd3f942138b731177e"
        )


class TestStageEStillRefusesEveryParserV3Artefact:
    """The deny lists must cover the derived worker and the v3 launchers."""

    @pytest.mark.parametrize(
        "name",
        [
            "eval_parsing_v3.py",
            "eval_parsing_v3.pyc",
            "eval_parsing_v3.cpython-311.pyc",
            "parser_v3_process_worker.py",
            "run_parser_v3_locked_predictions.py",
        ],
    )
    def test_forbidden_artefact_name(self, name, tmp_path):
        candidate = tmp_path / name
        candidate.write_bytes(b"")
        assert finalizer._forbidden_parser_path(candidate) is True

    def test_dynamic_import_string_for_v3_is_rejected(self, tmp_path):
        core = _v3_core()
        bad = tmp_path / "sneaky.py"
        bad.write_text(
            "import importlib\n"
            "m = importlib.import_module('jspace_observation.eval_parsing_v3')\n",
            encoding="utf-8",
        )
        with pytest.raises(core.LockedEvaluationError):
            core.assert_parser_free_source(bad.read_bytes(), "sneaky")

    def test_stage_e_entrypoint_source_stays_parser_free(self):
        core = _v3_core()
        for name in (
            "finalize_parser_v2_locked_evaluation.py",
            "finalize_parser_v3_locked_evaluation.py",
        ):
            path = ROOT / "scripts" / name
            core.assert_parser_free_source(path.read_bytes(), name)


class TestParserV3BuildProvenance:
    """The v3 image must be built from v3 bytes and tagged immutably."""

    DOCKERFILE = ROOT / "Dockerfile.parser-v3-eval"
    BUILD_SCRIPT = ROOT / "infra" / "azure" / "scripts" / "09_build_parser_v3_eval.sh"
    LAUNCHER = ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v3_locked_eval.sh"
    CONTRACT = ROOT / "scripts" / "parser_v3_azure_contract.py"

    def test_every_derived_build_file_exists(self):
        for path in (self.DOCKERFILE, self.BUILD_SCRIPT, self.LAUNCHER,
                     self.CONTRACT):
            assert path.exists(), path

    def test_dockerfile_installs_the_three_v3_entrypoints(self):
        source = _lf_bytes(self.DOCKERFILE).decode()
        for name in ("stage-p-v3", "stage-p-adopt-v3", "stage-e-v3"):
            assert f"/workspace/bin/{name}" in source

    def test_dockerfile_copies_the_candidate_parser_and_worker(self):
        source = _lf_bytes(self.DOCKERFILE).decode()
        assert "src/jspace_observation/eval_parsing_v3.py" in source
        assert "scripts/parser_v3_process_worker.py" in source
        assert "scripts/run_parser_v3_locked_predictions.py" in source
        assert "scripts/finalize_parser_v3_locked_evaluation.py" in source

    def test_dockerfile_pins_the_v3_gate_contract_digest(self):
        source = _lf_bytes(self.DOCKERFILE).decode()
        digest = hashlib.sha256(_lf_bytes(GATE_CONTRACT_PATH)).hexdigest()
        assert f"'phase1_parser_v3_acceptance_gates.json':'{digest}'" in source

    def test_dockerfile_pins_the_protocol_document_digest(self):
        source = _lf_bytes(self.DOCKERFILE).decode()
        protocol = ROOT / "docs" / "phase1_parser_v3_locked_evaluation_protocol.md"
        digest = hashlib.sha256(_lf_bytes(protocol)).hexdigest()
        assert (
            f"'phase1_parser_v3_locked_evaluation_protocol.md':'{digest}'"
            in source
        )

    def test_no_runtime_dependency_installation_or_floating_tag(self):
        source = _lf_bytes(self.DOCKERFILE).decode()
        assert "--require-hashes" in source
        assert "--only-binary=:all:" in source
        assert ":latest" not in source
        assert source.count("pip install") == 1

    def test_build_script_targets_the_v3_repository_and_dockerfile(self):
        source = _lf_bytes(self.BUILD_SCRIPT).decode()
        assert 'IMAGE_REPOSITORY="j-space-observation-parser-v3-eval"' in source
        assert "scripts/parser_v3_azure_contract.py" in source
        assert "Dockerfile.parser-v2-eval" not in source

    def test_build_script_tag_is_the_immutable_source_commit(self):
        source = _lf_bytes(self.BUILD_SCRIPT).decode()
        assert 'FINAL_TAG="$SOURCE_SHA"' in source
        assert 'FINAL_TAG="latest"' not in source
        assert "Mutable latest is forbidden" in source

    def test_azure_contract_points_at_the_v3_dockerfile(self):
        source = _lf_bytes(self.CONTRACT).decode()
        assert 'BUILD_DOCKERFILE_PATH = "Dockerfile.parser-v3-eval"' in source

    def test_build_inputs_match_the_registered_image_binding_paths(self):
        core = _v3_core()
        source = _lf_bytes(self.BUILD_SCRIPT).decode()
        for path in core.IMAGE_BINDING_SOURCE_PATHS:
            assert f'"{path}"' in source, path

    def test_launcher_expects_exactly_the_registered_source_bindings(self):
        core = _v3_core()
        source = _lf_bytes(self.LAUNCHER).decode()
        for path in core.RUNTIME_SOURCE_BINDING_PATHS:
            assert f'"{path}"' in source, path
        assert "Dockerfile.parser-v2-eval" not in source
        assert "scripts/parser_v2_azure_contract.py" not in source

    def test_profile_scoped_build_identity_is_exported(self):
        core = _v3_core()
        v2 = _load_module(
            "_test_v3_build_loader", ROOT / "scripts" / "load_locked_evaluation_core.py"
        ).load_locked_evaluation_core("_test_v3_build_core_v2")
        assert core.EVAL_DOCKERFILE_PATH == "Dockerfile.parser-v3-eval"
        assert core.EVAL_IMAGE_REPOSITORY == "j-space-observation-parser-v3-eval"
        assert v2.EVAL_DOCKERFILE_PATH == "Dockerfile.parser-v2-eval"
        assert v2.EVAL_IMAGE_REPOSITORY == "j-space-observation-parser-eval"

    def test_v2_binding_tuples_are_unchanged_by_parameterisation(self):
        v2 = _load_module(
            "_test_v3_build_loader2",
            ROOT / "scripts" / "load_locked_evaluation_core.py",
        ).load_locked_evaluation_core("_test_v3_build_core_v2b")
        assert v2.RUNTIME_SOURCE_BINDING_PATHS == (
            "Dockerfile.parser-v2-eval",
            "requirements-parser-v2-eval.txt",
            "infra/azure/scripts/09_build_parser_v2_eval.sh",
            "infra/azure/scripts/10_run_parser_v2_locked_eval.sh",
            "scripts/create_parser_v2_runtime_config.py",
            "scripts/bootstrap_parser_v2_locked_evaluation.py",
            "scripts/parser_v2_azure_contract.py",
            "scripts/parser_v2_process_worker.py",
            "scripts/run_parser_v2_locked_predictions.py",
            "scripts/finalize_parser_v2_locked_evaluation.py",
            "scripts/stage_p_entrypoint.sh",
            "scripts/stage_p_adopt_entrypoint.sh",
            "scripts/stage_e_entrypoint.sh",
            "src/jspace_observation/evaluator_validation.py",
            "src/jspace_observation/eval_parsing.py",
            "src/jspace_observation/eval_parsing_v2.py",
            "src/jspace_observation/parser_v2_locked_evaluation.py",
        )

    def test_every_v3_runtime_file_is_committed_as_lf(self):
        core = _v3_core()
        import subprocess

        paths = sorted(
            set(core.IMAGE_BINDING_SOURCE_PATHS)
            | set(core.RUNTIME_SOURCE_BINDING_PATHS)
        )
        result = subprocess.run(
            ["git", "-C", str(ROOT), "check-attr", "eol", "--"] + paths,
            capture_output=True,
            text=True,
            check=True,
        )
        unspecified = [
            line
            for line in result.stdout.splitlines()
            if line.strip() and not line.endswith(": eol: lf")
        ]
        assert unspecified == []


class TestAzureContractHelpersBindTheirOwnProfile:
    """The Azure provenance helpers must validate against their own profile."""

    def test_v3_helper_loads_the_parser_v3_profile(self):
        helper = _load_module(
            "_test_v3_azure_contract", ROOT / "scripts" / "parser_v3_azure_contract.py"
        )
        core = helper._load_core()
        assert core.ACTIVE_PARSER_PROFILE_ID == "parser-v3-v1"
        assert core.EVAL_DOCKERFILE_PATH == "Dockerfile.parser-v3-eval"
        assert core.EVAL_IMAGE_REPOSITORY == "j-space-observation-parser-v3-eval"
        assert "_PRESEEDED_PARSER_PROFILE_ID" not in core.__dict__

    def test_v2_helper_still_loads_the_parser_v2_profile(self):
        helper = _load_module(
            "_test_v2_azure_contract", ROOT / "scripts" / "parser_v2_azure_contract.py"
        )
        core = helper._load_core()
        assert core.ACTIVE_PARSER_PROFILE_ID == "parser-v2-v1"
        assert core.EVAL_DOCKERFILE_PATH == "Dockerfile.parser-v2-eval"
        assert core.EVAL_IMAGE_REPOSITORY == "j-space-observation-parser-eval"

    def test_v3_helper_accepts_a_v3_image_binding_the_v2_profile_rejects(self):
        helper3 = _load_module(
            "_test_v3_azure_contract_b", ROOT / "scripts" / "parser_v3_azure_contract.py"
        )
        helper2 = _load_module(
            "_test_v2_azure_contract_b", ROOT / "scripts" / "parser_v2_azure_contract.py"
        )
        core3 = helper3._load_core()
        core2 = helper2._load_core()
        assert core3.EVAL_IMAGE_REPOSITORY != core2.EVAL_IMAGE_REPOSITORY
        assert core3.EVAL_DOCKERFILE_PATH != core2.EVAL_DOCKERFILE_PATH
        assert core3.EVAL_BUILD_SCRIPT_PATH != core2.EVAL_BUILD_SCRIPT_PATH
        assert core3.EVAL_AZURE_CONTRACT_PATH != core2.EVAL_AZURE_CONTRACT_PATH
        assert core3.EVAL_RUNTIME_LAUNCHER_PATH != core2.EVAL_RUNTIME_LAUNCHER_PATH


# ---------------------------------------------------------------------------
# Namespace isolation between the sealed families, and the protocol/candidate
# split in the state chain.
# ---------------------------------------------------------------------------


def _core(name: str, profile_id: str | None = None):
    loader = _load_module(
        f"_test_ns_loader_{name}", ROOT / "scripts" / "load_locked_evaluation_core.py"
    )
    if profile_id is None:
        return loader.load_locked_evaluation_core(f"_test_ns_core_{name}")
    return loader.load_locked_evaluation_core(
        f"_test_ns_core_{name}", profile_id=profile_id
    )


V3_PARENT = "phase1-evaluator-validation/parser-v3-v1/20260725T160340Z"
V2_PARENT = "phase1-evaluator-validation/parser-v2-v1/20260715T000000Z"


def _draft(core, parent):
    return {
        "schema_version": core.STATE_RECEIPT_SCHEMA_VERSION,
        "authorization_id": "synthetic-authorization",
        "state": "DRAFT_PROTOCOL",
        "previous_state": None,
        "previous_receipt_sha256": None,
        "timestamp_utc": "2026-07-25T16:03:40Z",
        "execution_id": "synthetic-execution",
        "actor": "synthetic",
        "visibility": [],
        "registered_parent_prefix": parent,
        "protocol_commit": core.FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": core.FROZEN_PROTOCOL_BUNDLE_SHA256,
        "acceptance_gates_sha256": core.PROTOCOL_ACCEPTANCE_GATES_SHA256,
        "implementation_commit": None,
        "image_digest": None,
        "config_sha256": None,
        "authorization_lock_sha256": None,
        "artifact_manifest_hashes": {},
        "retry_kind": "none",
        "outcome": None,
        "holdout_spent": False,
        "holdout_retired": False,
    }


def _protocol_frozen(core, draft):
    receipt = dict(draft)
    receipt.update(
        {
            "state": "PROTOCOL_FROZEN",
            "previous_state": "DRAFT_PROTOCOL",
            "previous_receipt_sha256": core.state_receipt_sha256(draft),
            "timestamp_utc": "2026-07-25T16:04:40Z",
            "artifact_manifest_hashes": {
                "protocol_manifest": "b" * 64,
                "acceptance_gates": core.FROZEN_ACCEPTANCE_GATE_SHA256,
            },
        }
    )
    return receipt


class TestSealedFamilyNamespaceIsolation:
    """A candidate may only ever touch its own sealed family."""

    def test_v2_translation_is_a_no_op_by_construction(self):
        v2 = _core("v2_identity")
        assert v2._NAMESPACE_TRANSLATION_REQUIRED is False
        for value in (V2_PARENT, "PV2-0123456789abcdef0123", {"a": ["b"]}):
            assert v2._to_frozen_namespace(value) is value
            assert v2._from_frozen_namespace(value) is value

    def test_v3_case_ids_round_trip_exactly(self):
        v3 = _core("v3_roundtrip", "parser-v3-v1")
        assert v3._NAMESPACE_TRANSLATION_REQUIRED is True
        case = "PV3-0123456789abcdef0123"
        translated = v3._to_frozen_namespace(case)
        assert translated == "PV2-0123456789abcdef0123"
        assert v3._from_frozen_namespace(translated) == case

    def test_v3_parent_prefixes_round_trip_exactly(self):
        v3 = _core("v3_parent", "parser-v3-v1")
        translated = v3._to_frozen_namespace(V3_PARENT)
        assert translated.startswith("phase1-evaluator-validation/parser-v2-v1/")
        assert v3._from_frozen_namespace(translated) == V3_PARENT

    def test_translation_reaches_nested_structures(self):
        v3 = _core("v3_nested", "parser-v3-v1")
        payload = {"rows": [{"case_id": "PV3-0123456789abcdef0123"}]}
        translated = v3._to_frozen_namespace(payload)
        assert translated["rows"][0]["case_id"] == "PV2-0123456789abcdef0123"
        assert v3._from_frozen_namespace(translated) == payload

    def test_each_profile_rejects_the_other_family_parent_prefix(self):
        v2 = _core("v2_reject", )
        v3 = _core("v3_reject", "parser-v3-v1")
        with pytest.raises(Exception):
            v2.validate_registered_parent_prefix(V3_PARENT)
        with pytest.raises(Exception):
            v3.validate_registered_parent_prefix(V2_PARENT)
        assert v2.validate_registered_parent_prefix(V2_PARENT) == V2_PARENT
        assert v3.validate_registered_parent_prefix(V3_PARENT) == V3_PARENT

    def test_each_profile_rejects_the_other_family_case_ids(self):
        v2 = _core("v2_case")
        v3 = _core("v3_case", "parser-v3-v1")
        with pytest.raises(Exception):
            v2._require_case_id("PV3-0123456789abcdef0123")
        with pytest.raises(Exception):
            v3._require_case_id("PV2-0123456789abcdef0123")

    def test_authorization_locks_are_written_into_the_owning_family(self):
        v2 = _core("v2_lock")
        v3 = _core("v3_lock", "parser-v3-v1")
        assert v2.AUTHORIZATION_LOCK_BLOB_PREFIX != v3.AUTHORIZATION_LOCK_BLOB_PREFIX
        assert "parser-v2-v1" in v2.AUTHORIZATION_LOCK_BLOB_PREFIX
        assert "parser-v3-v1" in v3.AUTHORIZATION_LOCK_BLOB_PREFIX

    def test_holdout_identity_is_family_scoped(self):
        v2 = _core("v2_holdout")
        v3 = _core("v3_holdout", "parser-v3-v1")
        manifest = "1" * 64
        assert v3.HOLDOUT_ID_DOMAIN == "phase1-parser-v3-holdout-id/v1"
        assert v2.HOLDOUT_ID_DOMAIN == "phase1-parser-v2-holdout-id/v1"
        assert v3.derive_holdout_id(V3_PARENT, manifest) != v2.derive_holdout_id(
            V2_PARENT, manifest
        )

    def test_v2_holdout_identity_still_comes_from_the_frozen_instrument(self):
        v2 = _core("v2_holdout_frozen")
        manifest = "1" * 64
        assert v2.derive_holdout_id(V2_PARENT, manifest) == v2._load_frozen_validation(
        ).derive_holdout_id(V2_PARENT, manifest)

    def test_public_report_guard_covers_every_family(self):
        v3 = _core("v3_guard", "parser-v3-v1")
        assert set(v3.ALL_CASE_ID_PREFIXES) == {"PV2", "PV3"}


class TestStateChainProtocolVersusCandidateBinding:
    """The protocol triple names the protocol; the candidate binds separately."""

    def test_protocol_gate_hash_is_not_profile_scoped(self):
        v2 = _core("v2_triple")
        v3 = _core("v3_triple", "parser-v3-v1")
        assert (
            v2.PROTOCOL_ACCEPTANCE_GATES_SHA256
            == v3.PROTOCOL_ACCEPTANCE_GATES_SHA256
        )
        assert v2.PROTOCOL_ACCEPTANCE_GATES_SHA256 == (
            v2._load_frozen_validation().FROZEN_ACCEPTANCE_GATE_SHA256
        )

    def test_candidate_gate_contract_is_profile_scoped(self):
        v2 = _core("v2_candidate_gate")
        v3 = _core("v3_candidate_gate", "parser-v3-v1")
        assert v2.FROZEN_ACCEPTANCE_GATE_SHA256 != v3.FROZEN_ACCEPTANCE_GATE_SHA256

    def test_the_candidate_gate_contract_is_still_bound_into_the_chain(self):
        v3 = _core("v3_bound_gate", "parser-v3-v1")
        receipt = _protocol_frozen(v3, _draft(v3, V3_PARENT))
        assert (
            receipt["artifact_manifest_hashes"]["acceptance_gates"]
            == v3.FROZEN_ACCEPTANCE_GATE_SHA256
        )
        assert receipt["acceptance_gates_sha256"] == (
            v3.PROTOCOL_ACCEPTANCE_GATES_SHA256
        )

    @pytest.mark.parametrize(
        "profile,parent",
        [(None, V2_PARENT), ("parser-v3-v1", V3_PARENT)],
    )
    def test_state_receipts_validate_under_both_profiles(self, profile, parent):
        core = _core(f"receipt_{profile}", profile)
        assert core.validate_state_receipt(_draft(core, parent))["state"] == (
            "DRAFT_PROTOCOL"
        )

    @pytest.mark.parametrize(
        "profile,parent",
        [(None, V2_PARENT), ("parser-v3-v1", V3_PARENT)],
    )
    def test_chain_graph_and_transition_validate_under_both_profiles(
        self, profile, parent
    ):
        core = _core(f"chain_{profile}", profile)
        draft = _draft(core, parent)
        nxt = _protocol_frozen(core, draft)
        assert core.validate_state_receipt_chain([draft, nxt])["receipt_count"] == 2
        assert core.validate_state_receipt_graph([draft, nxt])["receipt_count"] == 2
        core.validate_state_transition(draft, nxt)

    def test_persisted_links_are_reproducible_from_the_stored_bytes(self):
        """An auditor must reproduce every link from the receipts on disk."""
        v3 = _core("v3_links", "parser-v3-v1")
        draft = _draft(v3, V3_PARENT)
        nxt = _protocol_frozen(v3, draft)
        recomputed = v3.sha256_bytes(v3.canonical_json_bytes(dict(draft)))
        assert nxt["previous_receipt_sha256"] == recomputed
        assert (
            v3.validate_state_receipt_chain([draft, nxt])["chain_sha256"]
            == v3.sha256_bytes(v3.canonical_json_bytes(dict(nxt)))
        )

    def test_persisted_receipts_never_carry_a_foreign_family(self):
        v3 = _core("v3_no_leak", "parser-v3-v1")
        draft = _draft(v3, V3_PARENT)
        nxt = _protocol_frozen(v3, draft)
        v3.validate_state_receipt_chain([draft, nxt])
        for receipt in (draft, nxt):
            assert "parser-v2-v1" not in json.dumps(receipt)
            assert "PV2-" not in json.dumps(receipt)


class TestRuntimeGeneratorBindsItsProfile:
    """The runtime-config generator must fix the profile before the core runs."""

    def test_generator_defaults_to_parser_v2(self):
        generator = _load_module(
            "_test_ns_runtime_generator",
            ROOT / "scripts" / "create_parser_v2_runtime_config.py",
        )
        assert generator.DEFAULT_EVALUATION_PROFILE == "parser-v2-v1"
        assert "parser-v3-v1" in generator.SUPPORTED_EVALUATION_PROFILES

    def test_generator_seeds_and_verifies_the_profile(self):
        source = _lf_bytes(
            ROOT / "scripts" / "create_parser_v2_runtime_config.py"
        ).decode("utf-8")
        assert 'module.__dict__["_PRESEEDED_PARSER_PROFILE_ID"] = profile_id' in source
        assert "if core_module.ACTIVE_PARSER_PROFILE_ID != profile_id:" in source
        assert 'if "_PRESEEDED_PARSER_PROFILE_ID" in core_module.__dict__:' in source

    def test_runtime_config_declares_the_profile_only_when_non_default(self):
        v2 = _core("v2_runtime_field")
        v3 = _core("v3_runtime_field", "parser-v3-v1")
        assert v2._RUNTIME_CONFIG_PROFILE_FIELDS == frozenset()
        assert v3._RUNTIME_CONFIG_PROFILE_FIELDS == frozenset({"evaluation_profile"})


class TestBootstrapBindsItsProfile:
    """The state-chain bootstrap must fix the profile before the core runs."""

    SCRIPT = ROOT / "scripts" / "bootstrap_parser_v2_locked_evaluation.py"

    def test_bootstrap_defaults_to_parser_v2(self):
        source = _lf_bytes(self.SCRIPT).decode("utf-8")
        assert 'DEFAULT_EVALUATION_PROFILE = "parser-v2-v1"' in source
        assert '"parser-v3-v1"' in source
        assert "SUPPORTED_EVALUATION_PROFILES" in source

    def test_bootstrap_seeds_and_verifies_the_profile(self):
        source = _lf_bytes(self.SCRIPT).decode("utf-8")
        assert 'module.__dict__["_PRESEEDED_PARSER_PROFILE_ID"] = profile_id' in source
        assert "if module.ACTIVE_PARSER_PROFILE_ID != profile_id:" in source
        assert 'if "_PRESEEDED_PARSER_PROFILE_ID" in module.__dict__:' in source

    def test_bootstrap_exposes_the_profile_on_the_command_line(self):
        source = _lf_bytes(self.SCRIPT).decode("utf-8")
        assert '"--evaluation-profile"' in source
        assert "evaluation_profile=cli.evaluation_profile" in source

    def test_bootstrap_reads_the_parser_source_path_from_the_profile(self):
        source = _lf_bytes(self.SCRIPT).decode("utf-8")
        assert 'core.ACTIVE_PARSER_PROFILE["parser_source_path"]' in source
        assert "PARSER_SOURCE_PATH = " not in source

    def test_bootstrap_receipts_use_the_protocol_gate_binding(self):
        source = _lf_bytes(self.SCRIPT).decode("utf-8")
        assert "core.PROTOCOL_ACCEPTANCE_GATES_SHA256" in source
        assert "core.FROZEN_ACCEPTANCE_GATE_SHA256" not in source.split(
            "def _receipt("
        )[1].split("\ndef ")[0]


class TestRuntimeValidatorUsesTheProfileLauncherAndStages:
    """Validation must accept what the builder emits, under either profile."""

    def test_validator_reads_the_launcher_path_from_the_profile(self):
        source = _lf_bytes(
            ROOT / "src" / "jspace_observation" / "parser_v2_locked_evaluation.py"
        ).decode("utf-8")
        assert 'launcher = checked[EVAL_RUNTIME_LAUNCHER_PATH]' in source
        assert (
            'launcher_path = "infra/azure/scripts/10_run_parser_v2_locked_eval.sh"'
            not in source
        )
        assert '"command": ["/workspace/bin/stage-p"]' not in source

    def test_each_profile_registers_its_own_launcher(self):
        v2 = _core("v2_launcher_binding")
        v3 = _core("v3_launcher_binding", "parser-v3-v1")
        assert v2.EVAL_RUNTIME_LAUNCHER_PATH.endswith("10_run_parser_v2_locked_eval.sh")
        assert v3.EVAL_RUNTIME_LAUNCHER_PATH.endswith("10_run_parser_v3_locked_eval.sh")
        for core in (v2, v3):
            assert core.EVAL_RUNTIME_LAUNCHER_PATH in core.RUNTIME_SOURCE_BINDING_PATHS
            assert core.EVAL_RUNTIME_LAUNCHER_PATH in core.IMAGE_BINDING_SOURCE_PATHS

    def test_stage_commands_round_trip_under_the_v3_profile(self):
        v3 = _core("v3_stage_command_roundtrip", "parser-v3-v1")
        suffix = v3.ACTIVE_PARSER_PROFILE["stage_command_suffix"]
        assert suffix == "-v3"
        expected = {
            "P": {"command": [f"/workspace/bin/stage-p{suffix}"], "args_prefix": []},
            "P_ADOPT": {
                "command": [f"/workspace/bin/stage-p-adopt{suffix}"],
                "args_prefix": [],
            },
            "E": {"command": [f"/workspace/bin/stage-e{suffix}"], "args_prefix": []},
        }
        assert expected["P"]["command"] == ["/workspace/bin/stage-p-v3"]
        assert expected["E"]["command"] == ["/workspace/bin/stage-e-v3"]


class TestPreflightAuditFindingsRemainFixed:
    """Regression cover for the twelve profile-binding defects found in audit.

    Every one of these had the same shape: a builder that reads the active
    profile paired with a consumer that hardcodes the parser-v2 literal. Under
    the default profile the literal is correct, so the defect is invisible
    until a parser-v3 run reaches it.
    """

    LAUNCHER = ROOT / "infra" / "azure" / "scripts" / "10_run_parser_v3_locked_eval.sh"
    BOOTSTRAP = ROOT / "scripts" / "bootstrap_parser_v2_locked_evaluation.py"
    GENERATOR = ROOT / "scripts" / "create_parser_v2_runtime_config.py"
    FINALIZER = ROOT / "scripts" / "finalize_parser_v2_locked_evaluation.py"
    CORE = ROOT / "src" / "jspace_observation" / "parser_v2_locked_evaluation.py"

    def _launcher(self) -> str:
        return _lf_bytes(self.LAUNCHER).decode("utf-8")

    # Findings 1 and 2 - both launcher core loads must seed the profile.
    def test_launcher_seeds_the_profile_on_every_core_load(self):
        source = self._launcher()
        seeds = source.count('_PRESEEDED_PARSER_PROFILE_ID"] = "parser-v3-v1"')
        assert seeds == 2, f"expected two seeded core loads, found {seeds}"
        guards = source.count('ACTIVE_PARSER_PROFILE_ID != "parser-v3-v1"')
        assert guards >= 2, f"expected a guard per seeded load, found {guards}"

    # Finding 3 - the launcher must not index bindings by the v2 literal.
    def test_launcher_indexes_bindings_by_the_profile_launcher(self):
        source = self._launcher()
        assert "source_bindings[core.EVAL_RUNTIME_LAUNCHER_PATH]" in source
        assert "10_run_parser_v2_locked_eval.sh" not in source

    # Finding 4 - both bootstrap invocations must pass the profile.
    def test_launcher_passes_the_profile_to_every_bootstrap_invocation(self):
        source = self._launcher()
        invocations = source.count('python "$BOOTSTRAP"')
        flags = source.count("--evaluation-profile parser-v3-v1")
        assert invocations >= 2
        assert flags == invocations, (
            f"{invocations} bootstrap invocations but {flags} profile flags"
        )

    # Findings 5 and 6 - git source bindings must be resolved per profile.
    def test_bootstrap_resolves_source_bindings_under_its_own_profile(self):
        source = _lf_bytes(self.BOOTSTRAP).decode("utf-8")
        assert "10_run_parser_v2_locked_eval.sh" not in source
        assert "launcher = source_bindings[active_core.EVAL_RUNTIME_LAUNCHER_PATH]" in source
        assert "launcher = source_bindings[core.EVAL_RUNTIME_LAUNCHER_PATH]" in source
        assert source.count("profile_id=active_core.ACTIVE_PARSER_PROFILE_ID") >= 1
        assert source.count("profile_id=core.ACTIVE_PARSER_PROFILE_ID") >= 1

    def test_frozen_parser_blob_check_is_reachable_under_the_v3_profile(self):
        """The only check that the frozen v3 source exists at the commit."""
        source = _lf_bytes(self.BOOTSTRAP).decode("utf-8")
        body = source.split("def _git_source_bindings(")[1].split("\ndef ")[0]
        assert "FROZEN_PARSER_GIT_BLOB_OID" in body
        assert "profile_id" in body.split("\n")[0] or "profile_id:" in body

    # Finding 7 - the sealed public report must name its own candidate.
    def test_public_report_title_comes_from_the_profile(self):
        source = _lf_bytes(self.CORE).decode("utf-8")
        assert '"# Phase 1.2B Parser-v2 Locked Evaluation"' not in source
        assert "f\"# {ACTIVE_PARSER_PROFILE['report_title']}\"" in source

    def test_v2_public_report_title_is_byte_identical(self):
        v2 = _core("v2_report_title")
        assert (
            v2.ACTIVE_PARSER_PROFILE["report_title"]
            == "Phase 1.2B Parser-v2 Locked Evaluation"
        )
        assert v2.ACTIVE_PARSER_PROFILE["report_declares_candidate_identity"] is False

    def test_v3_public_report_declares_the_candidate(self):
        v3 = _core("v3_report_title", "parser-v3-v1")
        assert (
            v3.ACTIVE_PARSER_PROFILE["report_title"]
            == "Phase 1.2D Parser-v3 Locked Evaluation"
        )
        assert v3.ACTIVE_PARSER_PROFILE["report_declares_candidate_identity"] is True
        lines = "\n".join(v3._candidate_identity_report_lines())
        assert "parser-v3-v1" in lines
        assert v3.FROZEN_PARSER_VERSION in lines
        assert v3.FROZEN_PARSER_SOURCE_SHA256 in lines
        assert "jspace-parser-v3-reference-blind-extraction/v1" in lines
        assert "orchestrator-schema compatibility" in lines
        # The report must not silently imply parser v2 produced the result.
        assert "Candidate parser algorithm" in lines

    def test_public_report_never_leaks_a_case_id_under_either_profile(self):
        for name, profile in (("v2_leak", None), ("v3_leak", "parser-v3-v1")):
            core = _core(name, profile)
            body = _lf_bytes(self.CORE).decode("utf-8").split(
                "def render_public_report("
            )[1]
            assert "ALL_CASE_ID_PREFIXES" in body.split("\ndef ")[0]
            assert len(core.ALL_CASE_ID_PREFIXES) >= 2

    # Finding 8 - the finalizer leak guard must cover every family prefix.
    def test_finalizer_leak_guard_covers_all_case_id_prefixes(self):
        source = _lf_bytes(self.FINALIZER).decode("utf-8")
        assert 'b"PV2-" in payloads' not in source
        assert "for prefix in core.ALL_CASE_ID_PREFIXES" in source

    # Finding 9 - the image repository profile field must be enforced.
    def test_generator_enforces_the_profile_image_repository(self):
        source = _lf_bytes(self.GENERATOR).decode("utf-8")
        assert "core_module.EVAL_IMAGE_REPOSITORY" in source
        v2 = _core("v2_image_repo")
        v3 = _core("v3_image_repo", "parser-v3-v1")
        assert v2.EVAL_IMAGE_REPOSITORY != v3.EVAL_IMAGE_REPOSITORY
        assert v3.EVAL_IMAGE_REPOSITORY == "j-space-observation-parser-v3-eval"

    # Findings 10, 11, 12 - provenance labels must not be permanently wrong.
    def test_launcher_carries_no_parser_v2_provenance_labels(self):
        source = self._launcher()
        assert "phase1-parser-v2-custodian" not in source
        assert "parser-v2-eval-${AUTHORIZATION_ID}" not in source
        assert '"name": "parser-v2-locked-eval"' not in source
        assert "phase1-parser-v3-custodian" in source
        assert "parser-v3-eval-${AUTHORIZATION_ID}" in source
        assert '"name": "parser-v3-locked-eval"' in source

    def test_bootstrap_accepts_the_v3_custodian_actor(self):
        source = _lf_bytes(self.BOOTSTRAP).decode("utf-8")
        assert '"phase1-parser-v3-custodian"' in source
        assert '"phase1-parser-v2-custodian"' in source
