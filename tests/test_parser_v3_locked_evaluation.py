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
            "src/jspace_observation/eval_parsing_v3.py",
            "scripts/parser_v3_process_worker.py",
            "docs/phase1_parser_v3_acceptance_gates.json",
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
