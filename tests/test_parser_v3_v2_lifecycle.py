"""Tests for the one-shot ``parser-v3-v2`` evaluation lifecycle.

Phase 1.2H-R2 / 1.2J. These are not only positive-path tests. The recurrent
finding in this repository --- five separate occurrences --- is a check bound to
something other than the thing that runs, so several tests here mutate the
module's declared constants and assert that the *behaviour* changes. A rule that
keeps passing after its own table is emptied is not enforcing that table.

Nothing here reads a private set, a sealed blob or a locked label. Every fixture
is public synthetic material constructed in-test.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from jspace_observation import parser_v3_v2_lifecycle as lifecycle
from jspace_observation.parser_v3_v2_lifecycle import LifecycleError

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
COMMIT = "a99d1e8341af85b8db32cb97a46ed5095c3f7978"


def _synthetic_case_ids(count: int = lifecycle.EXPECTED_SET_MEMBER_COUNT) -> list[str]:
    return [f"synthetic-case-{index:04d}" for index in range(count)]


# ---------------------------------------------------------------------------
# transition relation
# ---------------------------------------------------------------------------


class TestTransitionRelation:
    def test_the_declared_happy_path_is_permitted_end_to_end(self) -> None:
        path = [
            "SET_SEALED",
            "PREREGISTERED",
            "PREDICTION_RUNNING",
            "PREDICTION_SEALED",
            "LABELS_OPENED",
            "EVALUATED_ACCEPTED",
        ]
        for current, proposed in zip(path, path[1:]):
            lifecycle.assert_transition_permitted(current, proposed)

    @pytest.mark.parametrize(
        ("current", "proposed"),
        [
            # skipping preregistration entirely
            ("SET_SEALED", "PREDICTION_RUNNING"),
            # opening labels before the predictions are sealed
            ("PREDICTION_RUNNING", "LABELS_OPENED"),
            # scoring before any prediction exists
            ("PREREGISTERED", "LABELS_OPENED"),
            # producing a result without ever opening labels
            ("PREDICTION_SEALED", "EVALUATED_ACCEPTED"),
            # going backwards to regenerate predictions after seeing labels
            ("LABELS_OPENED", "PREDICTION_RUNNING"),
            # re-sealing a set after preregistration
            ("PREREGISTERED", "SET_SEALED"),
        ],
    )
    def test_out_of_order_transitions_are_refused(self, current: str, proposed: str) -> None:
        with pytest.raises(LifecycleError, match="not permitted"):
            lifecycle.assert_transition_permitted(current, proposed)

    @pytest.mark.parametrize("terminal", sorted(lifecycle.TERMINAL_STATES))
    def test_no_transition_leaves_a_terminal_state(self, terminal: str) -> None:
        for proposed in lifecycle.STATES:
            with pytest.raises(LifecycleError, match="terminal"):
                lifecycle.assert_transition_permitted(terminal, proposed)

    def test_an_unregistered_state_name_is_refused_before_the_relation(self) -> None:
        with pytest.raises(LifecycleError, match="not a registered state"):
            lifecycle.assert_transition_permitted("SET_SEALED", "PREDICTION_DONE")
        with pytest.raises(LifecycleError, match="not a registered state"):
            lifecycle.assert_transition_permitted("SEALED", "PREREGISTERED")

    def test_the_relation_table_is_the_thing_that_runs(self, monkeypatch) -> None:
        """Mutation control: empty the table and the permitted path must fail.

        This is the check that the repository's recurrent finding demands. If
        ``assert_transition_permitted`` passed a hard-coded path rather than
        consulting :data:`PERMITTED_TRANSITIONS`, this test would not fail.
        """
        monkeypatch.setattr(lifecycle, "PERMITTED_TRANSITIONS", frozenset())
        with pytest.raises(LifecycleError, match="not permitted"):
            lifecycle.assert_transition_permitted("SET_SEALED", "PREREGISTERED")

    def test_every_permitted_transition_uses_registered_states(self) -> None:
        for current, proposed in lifecycle.PERMITTED_TRANSITIONS:
            assert current in lifecycle.STATES
            assert proposed in lifecycle.STATES

    def test_every_terminal_state_is_a_registered_state(self) -> None:
        assert lifecycle.TERMINAL_STATES.issubset(set(lifecycle.STATES))

    def test_every_non_terminal_state_can_reach_a_terminal_state(self) -> None:
        """A reachable dead end would strand a round with no honest status."""
        reaching = set(lifecycle.TERMINAL_STATES)
        changed = True
        while changed:
            changed = False
            for current, proposed in lifecycle.PERMITTED_TRANSITIONS:
                if proposed in reaching and current not in reaching:
                    reaching.add(current)
                    changed = True
        assert set(lifecycle.STATES) == reaching


# ---------------------------------------------------------------------------
# ordinal
# ---------------------------------------------------------------------------


class TestOrdinal:
    def test_the_ordinal_advances_only_when_labels_are_opened(self) -> None:
        assert lifecycle.next_ordinal("SET_SEALED", "PREREGISTERED", 0) == 0
        assert lifecycle.next_ordinal("PREREGISTERED", "PREDICTION_RUNNING", 0) == 0
        assert lifecycle.next_ordinal("PREDICTION_RUNNING", "PREDICTION_SEALED", 0) == 0
        assert lifecycle.next_ordinal("PREDICTION_SEALED", "LABELS_OPENED", 0) == 1

    def test_generating_predictions_does_not_spend_the_one_shot(self) -> None:
        """Stage P is repeatable in principle; opening labels is not."""
        assert lifecycle.next_ordinal("PREREGISTERED", "PREDICTION_RUNNING", 0) == 0

    def test_a_second_label_opening_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="only once"):
            lifecycle.next_ordinal("PREDICTION_SEALED", "LABELS_OPENED", 1)

    def test_an_ordinal_above_the_maximum_is_refused_on_any_transition(self) -> None:
        with pytest.raises(LifecycleError, match="exceeds the maximum"):
            lifecycle.next_ordinal("SET_SEALED", "PREREGISTERED", 2)

    @pytest.mark.parametrize("bad", [-1, "0", 1.0, True, None])
    def test_a_non_integer_or_negative_ordinal_is_refused(self, bad) -> None:
        with pytest.raises(LifecycleError):
            lifecycle.next_ordinal("SET_SEALED", "PREREGISTERED", bad)

    def test_succession_refuses_a_reset(self) -> None:
        with pytest.raises(LifecycleError, match="never decrease"):
            lifecycle.assert_ordinal_succession(1, 0)

    def test_succession_refuses_exceeding_the_maximum(self) -> None:
        with pytest.raises(LifecycleError, match="never exceed"):
            lifecycle.assert_ordinal_succession(1, 2)

    def test_succession_refuses_a_double_increment(self, monkeypatch) -> None:
        monkeypatch.setattr(lifecycle, "MAX_FORMAL_EVALUATION_ORDINAL", 5)
        with pytest.raises(LifecycleError, match="at most 1"):
            lifecycle.assert_ordinal_succession(0, 2)

    def test_succession_permits_holding_and_single_advance(self) -> None:
        lifecycle.assert_ordinal_succession(0, 0)
        lifecycle.assert_ordinal_succession(0, 1)
        lifecycle.assert_ordinal_succession(1, 1)

    def test_the_advancing_transition_is_itself_permitted(self) -> None:
        assert lifecycle.ORDINAL_ADVANCING_TRANSITION in lifecycle.PERMITTED_TRANSITIONS


# ---------------------------------------------------------------------------
# create-only sealing
# ---------------------------------------------------------------------------


class TestCreateOnlySealing:
    def test_a_clean_namespace_accepts_the_plan(self) -> None:
        lifecycle.assert_create_only_plan(
            existing_objects=[],
            planned_objects=["case-0", "case-1", "manifest.json"],
            terminal_manifest="manifest.json",
        )

    def test_an_occupied_namespace_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="create-only violated"):
            lifecycle.assert_create_only_plan(
                existing_objects=["case-0"],
                planned_objects=["case-0", "case-1", "manifest.json"],
                terminal_manifest="manifest.json",
            )

    def test_resuming_a_partially_written_seal_is_refused(self) -> None:
        """Resume is the same failure as overwrite from the outside."""
        with pytest.raises(LifecycleError, match="rather than resume"):
            lifecycle.assert_create_only_plan(
                existing_objects=["case-0", "case-1"],
                planned_objects=["case-0", "case-1", "case-2", "manifest.json"],
                terminal_manifest="manifest.json",
            )

    def test_duplicate_planned_names_are_refused(self) -> None:
        with pytest.raises(LifecycleError, match="duplicates"):
            lifecycle.assert_create_only_plan(
                existing_objects=[],
                planned_objects=["case-0", "case-0", "manifest.json"],
                terminal_manifest="manifest.json",
            )

    def test_a_plan_without_its_terminal_manifest_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="terminal manifest"):
            lifecycle.assert_create_only_plan(
                existing_objects=[],
                planned_objects=["case-0", "case-1"],
                terminal_manifest="manifest.json",
            )

    def test_an_empty_plan_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="at least one object"):
            lifecycle.assert_create_only_plan(
                existing_objects=[], planned_objects=[], terminal_manifest="manifest.json"
            )

    def test_the_manifest_must_be_written_last(self) -> None:
        lifecycle.assert_terminal_manifest_last(
            write_order=["case-0", "case-1", "manifest.json"],
            terminal_manifest="manifest.json",
        )

    def test_a_manifest_first_write_order_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="written last"):
            lifecycle.assert_terminal_manifest_last(
                write_order=["manifest.json", "case-0", "case-1"],
                terminal_manifest="manifest.json",
            )

    def test_a_manifest_in_the_middle_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="written last"):
            lifecycle.assert_terminal_manifest_last(
                write_order=["case-0", "manifest.json", "case-1"],
                terminal_manifest="manifest.json",
            )

    def test_an_absent_manifest_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="does not appear"):
            lifecycle.assert_terminal_manifest_last(
                write_order=["case-0", "case-1"], terminal_manifest="manifest.json"
            )


# ---------------------------------------------------------------------------
# prediction stream completeness
# ---------------------------------------------------------------------------


class TestPredictionStreamCompleteness:
    def test_a_complete_aligned_stream_is_accepted(self) -> None:
        ids = _synthetic_case_ids()
        lifecycle.assert_prediction_stream_complete(
            sealed_case_ids=ids, prediction_case_ids=list(reversed(ids))
        )

    def test_a_partial_stream_cannot_seal(self) -> None:
        ids = _synthetic_case_ids()
        with pytest.raises(LifecycleError, match="incomplete"):
            lifecycle.assert_prediction_stream_complete(
                sealed_case_ids=ids, prediction_case_ids=ids[:-1]
            )

    def test_a_duplicated_prediction_cannot_seal(self) -> None:
        ids = _synthetic_case_ids()
        with pytest.raises(LifecycleError, match="duplicated"):
            lifecycle.assert_prediction_stream_complete(
                sealed_case_ids=ids, prediction_case_ids=ids[:-1] + [ids[0]]
            )

    def test_a_right_sized_stream_from_the_wrong_set_is_refused(self) -> None:
        """A count check alone would pass this; identifier alignment must not."""
        ids = _synthetic_case_ids()
        wrong = [f"other-case-{index:04d}" for index in range(len(ids))]
        with pytest.raises(LifecycleError, match="incomplete"):
            lifecycle.assert_prediction_stream_complete(
                sealed_case_ids=ids, prediction_case_ids=wrong
            )

    def test_extra_predictions_outside_the_sealed_set_are_refused(self) -> None:
        ids = _synthetic_case_ids()
        with pytest.raises(LifecycleError, match="not in the sealed set"):
            lifecycle.assert_prediction_stream_complete(
                sealed_case_ids=ids, prediction_case_ids=ids + ["smuggled-case"]
            )

    def test_a_sealed_set_of_the_wrong_size_is_refused(self) -> None:
        ids = _synthetic_case_ids(119)
        with pytest.raises(LifecycleError, match="exactly 120"):
            lifecycle.assert_prediction_stream_complete(
                sealed_case_ids=ids, prediction_case_ids=ids
            )

    def test_a_sealed_set_with_duplicate_identifiers_is_refused(self) -> None:
        ids = _synthetic_case_ids(119)
        ids.append(ids[0])
        with pytest.raises(LifecycleError, match="duplicate case identifiers"):
            lifecycle.assert_prediction_stream_complete(
                sealed_case_ids=ids, prediction_case_ids=ids
            )

    def test_the_expected_count_constant_is_the_thing_that_runs(self) -> None:
        """Mutation control: the size rule must follow the declared constant."""
        ids = _synthetic_case_ids(10)
        lifecycle.assert_prediction_stream_complete(
            sealed_case_ids=ids, prediction_case_ids=ids, expected_count=10
        )
        with pytest.raises(LifecycleError):
            lifecycle.assert_prediction_stream_complete(
                sealed_case_ids=ids, prediction_case_ids=ids, expected_count=11
            )

    def test_the_declared_member_count_matches_the_stratum_policy_shape(self) -> None:
        assert lifecycle.EXPECTED_SET_MEMBER_COUNT == 120
        assert lifecycle.EXPECTED_SET_MEMBER_COUNT % 12 == 0


# ---------------------------------------------------------------------------
# scope separation
# ---------------------------------------------------------------------------


class TestScopeSeparation:
    def test_stage_p_may_read_its_own_lane(self) -> None:
        lifecycle.assert_stage_p_scope(["sealed_v2_inputs", "frozen_parser_assets"])

    @pytest.mark.parametrize(
        "forbidden", sorted(lifecycle.STAGE_P_FORBIDDEN_READ_CLASSES)
    )
    def test_stage_p_cannot_reach_any_label_class(self, forbidden: str) -> None:
        with pytest.raises(LifecycleError):
            lifecycle.assert_stage_p_scope(["sealed_v2_inputs", forbidden])

    def test_stage_e_may_read_its_own_lane(self) -> None:
        lifecycle.assert_stage_e_scope(
            ["sealed_predictions", "scoring_labels", "policy", "final_contract"]
        )

    @pytest.mark.parametrize(
        "forbidden", sorted(lifecycle.STAGE_E_FORBIDDEN_READ_CLASSES)
    )
    def test_stage_e_cannot_reach_parser_or_construction_state(self, forbidden: str) -> None:
        with pytest.raises(LifecycleError):
            lifecycle.assert_stage_e_scope(["sealed_predictions", forbidden])

    def test_an_unlisted_read_class_is_refused_even_if_not_forbidden(self) -> None:
        """Absence is denial. An unknown lane must not default to permitted."""
        with pytest.raises(LifecycleError, match="outside its lane"):
            lifecycle.assert_stage_p_scope(["sealed_v2_inputs", "some_new_bucket"])

    def test_an_unregistered_role_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="not a registered role"):
            lifecycle._assert_scope("nobody", ["x"], frozenset())

    def test_stage_p_and_stage_e_read_lanes_are_disjoint_on_labels(self) -> None:
        stage_p = set(lifecycle.ROLE_LANES["stage_p"]["reads"])
        stage_e = set(lifecycle.ROLE_LANES["stage_e"]["reads"])
        assert "scoring_labels" in stage_e
        assert "scoring_labels" not in stage_p

    def test_no_role_writes_into_another_roles_write_lane(self) -> None:
        """Two roles sharing a write lane makes attribution unrecoverable."""
        seen: dict[str, str] = {}
        for role, lanes in lifecycle.ROLE_LANES.items():
            for lane in lanes["writes"]:
                assert lane not in seen, (
                    f"{role} and {seen.get(lane)} both write {lane}"
                )
                seen[lane] = role

    def test_the_two_reviewers_do_not_share_a_write_lane(self) -> None:
        a = set(lifecycle.ROLE_LANES["reviewer_a"]["writes"])
        b = set(lifecycle.ROLE_LANES["reviewer_b"]["writes"])
        assert not a.intersection(b)

    def test_neither_reviewer_can_read_the_others_decisions(self) -> None:
        for role, other in (("reviewer_a", "reviewer_b"), ("reviewer_b", "reviewer_a")):
            reads = set(lifecycle.ROLE_LANES[role]["reads"])
            writes = set(lifecycle.ROLE_LANES[other]["writes"])
            assert not reads.intersection(writes)


# ---------------------------------------------------------------------------
# status derivation
# ---------------------------------------------------------------------------


class TestStatusDerivation:
    def test_all_gates_passing_derives_pass(self) -> None:
        lifecycle.assert_status_is_exclusive(
            binding_gate_results={"gate_a": True, "gate_b": True},
            declared_status="PASS",
        )

    def test_one_failing_gate_derives_fail(self) -> None:
        lifecycle.assert_status_is_exclusive(
            binding_gate_results={"gate_a": True, "gate_b": False},
            declared_status="FAIL",
        )

    def test_a_declared_pass_over_a_failing_gate_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="does not match"):
            lifecycle.assert_status_is_exclusive(
                binding_gate_results={"gate_a": True, "gate_b": False},
                declared_status="PASS",
            )

    def test_a_declared_fail_over_passing_gates_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="does not match"):
            lifecycle.assert_status_is_exclusive(
                binding_gate_results={"gate_a": True}, declared_status="FAIL"
            )

    def test_zero_gates_cannot_derive_a_status(self) -> None:
        """An empty gate set makes ``all()`` true and would silently PASS."""
        with pytest.raises(LifecycleError, match="zero binding gates"):
            lifecycle.assert_status_is_exclusive(
                binding_gate_results={}, declared_status="PASS"
            )

    @pytest.mark.parametrize("truthy", [1, "yes", [1], 0, "", None])
    def test_a_non_boolean_gate_result_is_refused(self, truthy) -> None:
        with pytest.raises(LifecycleError, match="not boolean"):
            lifecycle.assert_status_is_exclusive(
                binding_gate_results={"gate_a": truthy}, declared_status="PASS"
            )

    def test_an_unregistered_status_word_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="not PASS, FAIL or INVALID"):
            lifecycle.assert_status_is_exclusive(
                binding_gate_results={"gate_a": True}, declared_status="ACCEPTED"
            )

    def test_report_only_metrics_must_not_be_binding_gates(self) -> None:
        lifecycle.assert_report_only_metrics_cannot_reach_status(
            binding_gate_names=["exact_match_rate", "no_crash"],
            report_only_metric_names=["macro_f1", "confusion_matrix"],
        )

    def test_a_promoted_report_only_metric_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="macro_f1"):
            lifecycle.assert_report_only_metrics_cannot_reach_status(
                binding_gate_names=["exact_match_rate", "macro_f1"],
                report_only_metric_names=["macro_f1"],
            )


# ---------------------------------------------------------------------------
# final contract
# ---------------------------------------------------------------------------


class TestFinalContract:
    def _compile(self, **overrides):
        kwargs = dict(
            policy_sha256=SHA_A,
            set_manifest_sha256=SHA_B,
            listing_witness_sha256=SHA_C,
            parser_source_sha256=SHA_D,
            scorer_source_sha256=SHA_E,
            prospective_protocol_commit=COMMIT,
            existing_contract_objects=[],
            contract_object_name="final_contract.json",
        )
        kwargs.update(overrides)
        return lifecycle.compile_final_contract_once(**kwargs)

    def test_it_compiles_and_is_deterministic(self) -> None:
        first = self._compile()
        second = self._compile()
        assert first == second
        assert len(first["contract_sha256"]) == 64

    def test_it_binds_the_listing_witness_not_only_the_manifest(self) -> None:
        """L-32: a manifest-only binding accepts a set never observed at storage."""
        baseline = self._compile()["contract_sha256"]
        changed = self._compile(listing_witness_sha256="f" * 64)["contract_sha256"]
        assert baseline != changed

    @pytest.mark.parametrize(
        "field",
        [
            "policy_sha256",
            "set_manifest_sha256",
            "listing_witness_sha256",
            "parser_source_sha256",
            "scorer_source_sha256",
        ],
    )
    def test_every_bound_digest_changes_the_contract_hash(self, field: str) -> None:
        baseline = self._compile()["contract_sha256"]
        assert self._compile(**{field: "9" * 64})["contract_sha256"] != baseline

    def test_the_prospective_commit_changes_the_contract_hash(self) -> None:
        baseline = self._compile()["contract_sha256"]
        other = self._compile(prospective_protocol_commit="0" * 40)["contract_sha256"]
        assert other != baseline

    def test_recompilation_over_an_existing_contract_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="exactly once"):
            self._compile(existing_contract_objects=["final_contract.json"])

    @pytest.mark.parametrize("bad", ["", "abc", "A" * 64, "g" * 64, None, 123])
    def test_a_malformed_digest_is_refused(self, bad) -> None:
        with pytest.raises(LifecycleError, match="SHA-256"):
            self._compile(set_manifest_sha256=bad)

    @pytest.mark.parametrize("bad", ["a99d1e8", "z" * 40, "", COMMIT.upper()])
    def test_an_abbreviated_or_malformed_commit_is_refused(self, bad: str) -> None:
        with pytest.raises(LifecycleError, match="40-character Git SHA-1"):
            self._compile(prospective_protocol_commit=bad)

    def test_the_contract_hash_is_not_stored_inside_its_own_preimage(self) -> None:
        contract = self._compile()
        assert "contract_sha256" in contract
        recomputed = lifecycle.compile_final_contract_once(
            policy_sha256=contract["policy_sha256"],
            set_manifest_sha256=contract["set_manifest_sha256"],
            listing_witness_sha256=contract["listing_witness_sha256"],
            parser_source_sha256=contract["parser_source_sha256"],
            scorer_source_sha256=contract["scorer_source_sha256"],
            prospective_protocol_commit=contract["prospective_protocol_commit"],
            existing_contract_objects=[],
            contract_object_name="final_contract.json",
        )
        assert recomputed["contract_sha256"] == contract["contract_sha256"]


# ---------------------------------------------------------------------------
# parser isolation
# ---------------------------------------------------------------------------


class TestParserIsolation:
    def test_this_module_adds_no_parser_dependency(self) -> None:
        """AST control: no import in this module reaches parser-bearing code.

        A substring scan is the wrong instrument here and was the first version
        of this test. It failed, correctly, because the module *must* carry the
        strings ``eval_parsing``, ``parser_v3_repair`` and ``model_loader`` as
        the denylist that :func:`assert_stage_e_import_is_parser_free` matches
        against. A denylist entry is data, not a dependency. The supportable
        claim is about the import graph, so that is what is checked.
        """
        source = Path(lifecycle.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0, "relative import would reach the package __init__"
                if node.module:
                    imported.add(node.module)
        assert imported, "the AST walk found no imports at all, so it proves nothing"
        for name in imported:
            root = name.split(".")[0]
            assert root != "jspace_observation", f"{name} imports from the package"
            for marker in ("eval_parsing", "parser_v3_repair", "model_loader", "torch"):
                assert marker not in name, f"{name} reaches parser-bearing code"

    def test_the_ast_control_would_notice_a_parser_import(self) -> None:
        """Mutation control: the same walk must flag a module that does import one."""
        tree = ast.parse("from jspace_observation import eval_parsing\n")
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert any(name.split(".")[0] == "jspace_observation" for name in imported)

    def test_it_loads_from_a_path_without_running_the_package_init(self, tmp_path) -> None:
        module_path = tmp_path / "standalone_probe.py"
        module_path.write_text("VALUE = 42\n", encoding="utf-8")
        name = "jspace_standalone_probe_for_tests"
        try:
            module = lifecycle.load_module_without_package(module_path, name)
            assert module.VALUE == 42
        finally:
            sys.modules.pop(name, None)

    def test_loading_a_missing_path_is_refused(self, tmp_path) -> None:
        with pytest.raises(LifecycleError, match="cannot load"):
            lifecycle.load_module_without_package(
                tmp_path / "does_not_exist.py", "jspace_missing_probe"
            )

    def test_a_parser_bearing_stage_e_process_is_refused(self) -> None:
        with pytest.raises(LifecycleError, match="parser-bearing"):
            lifecycle.assert_stage_e_import_is_parser_free(
                ["json", "jspace_observation.eval_parsing"]
            )

    def test_a_clean_stage_e_process_is_accepted(self) -> None:
        lifecycle.assert_stage_e_import_is_parser_free(["json", "hashlib", "pathlib"])

    def test_the_marker_list_is_the_thing_that_runs(self) -> None:
        """Mutation control: an empty marker list must stop refusing."""
        lifecycle.assert_stage_e_import_is_parser_free(
            ["jspace_observation.eval_parsing"], parser_markers=()
        )


# ---------------------------------------------------------------------------
# cross-cutting invariants
# ---------------------------------------------------------------------------


class TestDeclaredSurface:
    def test_every_exported_name_exists(self) -> None:
        for name in lifecycle.__all__:
            assert hasattr(lifecycle, name), f"{name} is exported but missing"

    def test_the_schema_version_is_pinned(self) -> None:
        assert lifecycle.LIFECYCLE_SCHEMA_VERSION == (
            "phase1-parser-v3-v2-evaluation-lifecycle/v1"
        )

    def test_the_module_computes_no_threshold_and_holds_no_score(self) -> None:
        """AST control: acceptance must not be decided in a second place.

        A threshold is a number. Rather than scanning prose for the word, this
        walks the module for module-level numeric constants and for the
        statistical imports a scorer would need. Either would be evidence that
        acceptance logic had migrated here from the FINAL policy.
        """
        source = Path(lifecycle.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, float):
                raise AssertionError(f"module-level float constant found: {ast.dump(node)}")
        imported = {
            alias.name
            for stmt in ast.walk(tree)
            if isinstance(stmt, ast.Import)
            for alias in stmt.names
        } | {
            stmt.module
            for stmt in ast.walk(tree)
            if isinstance(stmt, ast.ImportFrom) and stmt.module
        }
        for scorer_import in ("statistics", "numpy", "sklearn", "scipy", "math"):
            assert scorer_import not in imported, f"{scorer_import} suggests scoring logic"

    def test_the_only_numeric_policy_constant_is_the_member_count(self) -> None:
        """The member count is structural, not an acceptance threshold."""
        assert isinstance(lifecycle.EXPECTED_SET_MEMBER_COUNT, int)
        assert isinstance(lifecycle.MAX_FORMAL_EVALUATION_ORDINAL, int)
