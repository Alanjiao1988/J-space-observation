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
            "scripts/run_parser_v3_locked_predictions.py",
            "scripts/finalize_parser_v3_locked_evaluation.py",
            "scripts/stage_p_v3_entrypoint.sh",
            "scripts/stage_p_adopt_v3_entrypoint.sh",
            "scripts/stage_e_v3_entrypoint.sh",
            "docs/phase1_parser_v3_acceptance_gates.json",
            "docs/phase1_parser_v3_locked_evaluation_protocol.md",
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
    """
    from copy import deepcopy

    from tests import test_evaluator_validation as frozen_tests

    core = _v3_core()
    dataset = frozen_tests._dataset()
    labels = deepcopy(dataset["materialized"]["locked_draft_labels"])
    locked_inputs = deepcopy(dataset["materialized"]["locked_inputs"])
    locked_by_id = {item["case_id"]: item for item in locked_inputs}

    candidate = frozen_tests._prediction_envelopes(labels, locked_inputs)
    for row in candidate:
        row["parser_result"]["parser_version"] = core.FROZEN_PARSER_VERSION

    v2_version = core.FROZEN_COMPARATOR_PARSER_IDENTITIES["parser_v2"][
        "parser_version"
    ]
    comparator = deepcopy(candidate)
    for row in comparator:
        row["parser_result"]["parser_version"] = v2_version

    legacy_rows = []
    for row in frozen_tests._legacy_predictions(labels):
        parsed = row["parsed_answer"]
        legacy_rows.append(
            core.build_legacy_prediction(
                locked_by_id[row["case_id"]],
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
