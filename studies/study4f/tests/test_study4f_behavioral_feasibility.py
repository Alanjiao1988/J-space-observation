"""Study 4F mechanical preflight and mutation audit.

Authority: ``studies/study4f/prompts/study4f_minimal_behavioral_feasibility_authority.md``

This module lives under ``studies/study4f/tests/`` rather than the repository's
default ``testpaths = ["tests"]``, exactly as the Study 3R review and closure
modules do. It is run explicitly::

    python -m pytest studies/study4f/tests/test_study4f_behavioral_feasibility.py

It implements section 11 in full, plus the coordinated mutation audit that
section 11 requires for the seven survivors the Study 3R focused review
reported. Every bank used here is a **synthetic non-study fixture**: it is
derived from a fixture commit id, never committed, and never used to make a
scientific decision. No study bank is realized, no model is constructed and no
weight file is acquired.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import subprocess
import sys
from fractions import Fraction
from itertools import product
from math import comb

import pytest

TESTS = pathlib.Path(__file__).resolve().parent
STUDY4F = TESTS.parent
ROOT = STUDY4F.parent.parent
ANALYSIS = STUDY4F / "analysis"
sys.path.insert(0, str(ANALYSIS))

import study4f_design_statistics as stats  # noqa: E402
import study4f_interfaces as interfaces  # noqa: E402
import study4f_resource_route as resource_route  # noqa: E402
import study4f_state_machine as machine  # noqa: E402
import study4f_task_banks as banks  # noqa: E402
import study4f_validation as validation  # noqa: E402

PROTOCOL_JSON = STUDY4F / "protocol" / "study4f_protocol_v1.json"
PROTOCOL_SCHEMA = STUDY4F / "protocol" / "study4f_protocol_v1.schema.json"
AUTHORITY = STUDY4F / "prompts" / \
    "study4f_minimal_behavioral_feasibility_authority.md"

AUTHORITY_COMMIT = "7d5ff0837d77af9e6df9f49d580ec0e42bdc2729"
AUTHORITY_SHA256 = \
    "bafba585ba4fe0030f2bae14e7be8d2f060732e56b3696422102605668de0773"
AUTHORITY_BYTES = 17822
STUDY3R_CLOSURE_COMMIT = "ee8a852111d27cb39bf21743e18857485cff1efe"

#: A synthetic, non-study fixture identity. It is deliberately *not* the
#: registered authority commit, so nothing realized in this module can be
#: mistaken for, or reused as, a sealed study bank.
FIXTURE_COMMIT = "f" * 8 + "0" * 32

#: The eight standing repository failure node IDs. Unchanged by Study 4F.
STANDING_FAILURE_NODE_IDS = (
    "tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last",
    "tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix",
    "tests/test_phase1_0d_build_provenance.py::test_the_bundle_digest_ignores_the_checkout_line_endings",
    "tests/test_phase1_0d_generation_launcher_rp_compat.py::test_shim_has_valid_bash_syntax_and_frozen_launcher_remains_in_baseline",
    "tests/test_phase1_0d_protected_bytes.py::test_line_endings_do_not_change_the_rollup",
    "tests/test_phase1_0d_review_image.py::test_v2_refuses_a_rehashed_record_with_moved_metadata",
    "tests/test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only",
    "tests/test_study3_v0_7_focused_review.py::test_the_review_changed_no_reviewed_or_historical_path",
)

#: Study 3R closure bytes Study 4F must not disturb.
STUDY3R_CLOSURE_PATHS = (
    "studies/study3r/STATUS.json",
    "studies/study3r/STATUS.schema.json",
    "studies/study3r/STUDY3R_TERMINAL_CLOSURE.md",
    "studies/study3r/study3r_terminal_closure.json",
    "studies/study3r/study3r_terminal_closure.schema.json",
    "studies/study3r/closure/test_study3r_terminal_closure.py",
    "studies/study3r/README.md",
    "studies/study3r/protocol/study3r_protocol_current.json",
    "studies/study3r/protocol/study3r_protocol_v1.json",
    "studies/study3r/reviews/study3r_protocol_v1_single_focused_review.json",
    "studies/study3r/prompts/study3r_terminal_closure_authority.md",
    "paper/evidence_ledger.csv",
)


def _git(*args: str) -> str:
    return subprocess.run(["git", "--no-pager", *args], cwd=str(ROOT),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=True).stdout


def _load_governance_module():
    """Load the Study 3R governance module by path, without importing ``tests``."""
    import importlib.util

    path = ROOT / "tests" / "test_study3r_operator_governance.py"
    spec = importlib.util.spec_from_file_location(
        "study4f_governance_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def protocol():
    return _json(PROTOCOL_JSON)


@pytest.fixture(scope="module")
def fixture_banks():
    """Two synthetic non-study banks. Never sealed, never committed."""
    d2 = banks.realize_bank("D2_DEVELOPMENT_BANK", FIXTURE_COMMIT)
    d3 = banks.realize_bank(
        "D3_DEVELOPMENT_BANK", FIXTURE_COMMIT,
        excluded_content_hashes={banks.content_hash(item) for item in d2})
    return d2, d3


# ---------------------------------------------------------------------------
# 1. Authority identity and publication order
# ---------------------------------------------------------------------------


def test_the_authority_bytes_match_the_recorded_identity(protocol):
    payload = AUTHORITY.read_bytes()
    recorded = protocol["authority"]
    assert len(payload) == recorded["bytes"] == AUTHORITY_BYTES
    assert hashlib.sha256(payload).hexdigest() == recorded["sha256"] == \
        AUTHORITY_SHA256
    assert b"\r" not in payload
    assert payload.endswith(b"\n")
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert _git("rev-parse", "HEAD:%s" % recorded["path"]).strip() == \
        recorded["git_blob"]


def test_the_authority_was_published_alone_as_the_first_study4f_commit(protocol):
    recorded = protocol["authority"]
    listed = [line.strip() for line
              in _git("show", "--name-only", "--format=", AUTHORITY_COMMIT
                      ).splitlines() if line.strip()]
    assert listed == [recorded["path"]]
    assert recorded["published_alone_as_the_first_study4f_commit"] is True
    assert _git("rev-parse", "%s^" % AUTHORITY_COMMIT).strip() == \
        recorded["parent_commit"] == STUDY3R_CLOSURE_COMMIT


def test_study4f_derives_no_authority_from_study3r(protocol):
    assert protocol["authority"]["derives_authority_from_study3r"] is False
    assert protocol["authority"]["amends_repairs_or_reactivates_study3r"] is False
    assert protocol["study3r_relationship"]["study3r_terminal_status_modified"] \
        is False


def test_the_study3r_closure_is_complete_and_untouched():
    status = _json(ROOT / "studies" / "study3r" / "STATUS.json")
    assert status["lifecycle_state"] == \
        "STUDY3R_TERMINAL_CLOSURE_COMPLETE_RESEARCH_QUESTION_UNANSWERED"
    assert status["active_protocol"] is None
    assert all(value is False for value in status["authorization_flags"].values())
    assert status["evidence_ledger"]["last_row"] == "EV-0016"
    for relative in STUDY3R_CLOSURE_PATHS:
        at_closure = _git("rev-parse",
                          "%s:%s" % (STUDY3R_CLOSURE_COMMIT, relative)).strip()
        now = _git("rev-parse", "HEAD:%s" % relative).strip()
        assert at_closure == now, relative


def test_every_study3r_byte_is_identical_to_the_closure_head():
    """The substantive guarantee the expired closure scope predicate asserted.

    ``studies/study3r/closure/test_study3r_terminal_closure.py::test_the_closure_only_added_its_own_paths_and_touched_one_readme``
    compares ``git diff --name-status <closure authority> HEAD`` against the
    closure's own path set, so it expires the moment any authorized commit is
    added after the closure -- which publishing the Study 4F authority alone
    necessarily is. That module is a Study 3R closure byte and section 11 of the
    Study 4F authority forbids changing it, so the expiry is recorded rather
    than edited or suppressed.

    This test carries the underlying guarantee forward, and strengthens it: it
    compares *every* tracked path under ``studies/study3r/`` at the closure head
    against the current head, not a sampled subset.
    """
    listed = [line.strip() for line
              in _git("ls-tree", "-r", "--name-only", STUDY3R_CLOSURE_COMMIT,
                      "studies/study3r").splitlines() if line.strip()]
    assert len(listed) >= 50, len(listed)
    moved = []
    for relative in listed:
        at_closure = _git("rev-parse",
                          "%s:%s" % (STUDY3R_CLOSURE_COMMIT, relative)).strip()
        now = _git("rev-parse", "HEAD:%s" % relative).strip()
        if at_closure != now:
            moved.append(relative)
    assert moved == [], moved
    # No Study 3R path was deleted either.
    now_listed = [line.strip() for line
                  in _git("ls-tree", "-r", "--name-only", "HEAD",
                          "studies/study3r").splitlines() if line.strip()]
    assert set(listed) <= set(now_listed), sorted(set(listed) - set(now_listed))


def test_study4f_added_paths_live_only_in_its_own_namespace():
    """Everything Study 4F published sits under ``studies/study4f/``.

    The one exception is the governance scope admission, which is named
    explicitly here so it can never be a silent widening.
    """
    statuses = {}
    for line in _git("diff", "--name-status", STUDY3R_CLOSURE_COMMIT,
                     "HEAD").splitlines():
        if not line.strip():
            continue
        code, path = line.split("\t", 1)
        statuses[path.strip()] = code.strip()
    added = {path for path, code in statuses.items() if code == "A"}
    modified = {path for path, code in statuses.items() if code != "A"}
    assert all(path.startswith("studies/study4f/") for path in added), \
        sorted(path for path in added if not path.startswith("studies/study4f/"))
    assert modified <= {"tests/test_study3r_operator_governance.py"}, \
        sorted(modified)


def test_the_history_is_strictly_linear_and_merge_free():
    merges = [line for line
              in _git("rev-list", "--merges",
                      "%s..HEAD" % STUDY3R_CLOSURE_COMMIT).splitlines()
              if line.strip()]
    assert merges == []
    assert _git("merge-base", AUTHORITY_COMMIT, "HEAD").strip() == AUTHORITY_COMMIT


# ---------------------------------------------------------------------------
# 2. Schema conformance and decision-bearing constraint
# ---------------------------------------------------------------------------


def test_the_protocol_validates_against_its_restrictive_schema(protocol):
    jsonschema = pytest.importorskip("jsonschema")
    schema = _json(PROTOCOL_SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(protocol, schema)


def test_no_decision_bearing_object_is_open():
    schema = _json(PROTOCOL_SCHEMA)
    open_objects = []

    def walk(node, trail):
        if isinstance(node, dict):
            if node.get("type") == "object" and "$defs" not in trail:
                if node.get("additionalProperties") is not False:
                    open_objects.append("/".join(trail) + ":additionalProperties")
                if not node.get("required"):
                    open_objects.append("/".join(trail) + ":required")
            for key, value in node.items():
                walk(value, trail + [str(key)])
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, trail + [str(index)])

    walk(schema, [])
    assert open_objects == [], open_objects


def test_every_decoding_field_is_pinned_to_a_literal():
    """No decoding field may be a bare type, and none may be inherited."""
    schema = _json(PROTOCOL_SCHEMA)["properties"]["routes"]["properties"]
    for route in ("primary", "headroom"):
        contract = schema[route]["properties"]["generation_contract"]
        assert contract["additionalProperties"] is False, route
        for name, subschema in contract["properties"].items():
            assert "const" in subschema, (route, name)
        assert set(contract["required"]) == set(contract["properties"]), route


# ---------------------------------------------------------------------------
# 3. Banks: separation, allocation, disjointness
# ---------------------------------------------------------------------------


def test_exactly_two_single_family_banks_are_registered(protocol):
    registered = protocol["banks"]["registered"]
    assert len(registered) == 2
    assert {entry["family"] for entry in registered} == {"D2", "D3"}
    assert {entry["depth"] for entry in registered} == {2, 3}
    assert all(entry["size"] == 104 for entry in registered)
    assert protocol["banks"]["mixed_family_banks_permitted"] is False
    assert protocol["banks"]["confirmation_bank_exists"] is False
    assert set(banks.BANK_FAMILY) == {entry["bank_id"] for entry in registered}


def test_each_bank_realizes_104_unique_eligible_items(fixture_banks):
    d2, d3 = fixture_banks
    for items in (d2, d3):
        assert len(items) == 104
        keys = [item["item_key"] for item in items]
        assert len(set(keys)) == 104


def test_answer_labels_are_exactly_balanced_at_104(fixture_banks):
    for items in fixture_banks:
        counts = banks.label_counts(items)
        assert counts == {"A": 26, "B": 26, "C": 26, "D": 26}, counts


def test_the_deterministic_first_60_items_are_exactly_balanced(fixture_banks):
    for items in fixture_banks:
        counts = banks.label_counts(items[:60])
        assert counts == {"A": 15, "B": 15, "C": 15, "D": 15}, counts
        remainder = banks.label_counts(items[60:])
        assert remainder == {"A": 11, "B": 11, "C": 11, "D": 11}, remainder


def test_the_two_banks_are_disjoint_by_canonical_content_hash(fixture_banks):
    d2, d3 = fixture_banks
    d2_hashes = {banks.content_hash(item) for item in d2}
    d3_hashes = {banks.content_hash(item) for item in d3}
    assert len(d2_hashes) == len(d3_hashes) == 104
    assert d2_hashes & d3_hashes == set()


def test_no_cross_depth_duplicate_content_hash_exists(fixture_banks):
    d2, d3 = fixture_banks
    combined = [banks.content_hash(item) for item in d2 + d3]
    assert len(set(combined)) == len(combined) == 208


def test_no_answer_or_answer_derived_field_reaches_the_prompt(fixture_banks):
    for items in fixture_banks:
        for item in items[:12]:
            validation.validate_no_answer_leak(item)
            prompt = interfaces.render_w1_raw_direct(str(item["item_body"]))
            assert "correct" not in prompt.lower()
            assert str(item["correct_label"]) + ")" in prompt  # only as an option
            cot = interfaces.render_c1_body(str(item["item_body"]))
            assert "FINAL: %s" % item["correct_label"] not in cot


def test_the_bank_seed_is_derived_from_the_authority_commit_and_bank_id(protocol):
    derivation = protocol["banks"]["seed_derivation"]
    assert derivation["authority_commit"] == AUTHORITY_COMMIT
    assert derivation["digest"] == "sha256"
    assert derivation["frozen_before_bank_realization"] is True
    material = banks.bank_seed_material(AUTHORITY_COMMIT, "D2_DEVELOPMENT_BANK")
    assert material == "STUDY4F|%s|D2_DEVELOPMENT_BANK" % AUTHORITY_COMMIT
    expected = int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest(),
                              "big")
    assert banks.bank_seed(AUTHORITY_COMMIT, "D2_DEVELOPMENT_BANK") == expected
    assert banks.bank_seed(AUTHORITY_COMMIT, "D2_DEVELOPMENT_BANK") != \
        banks.bank_seed(AUTHORITY_COMMIT, "D3_DEVELOPMENT_BANK")


def test_bank_realization_is_deterministic():
    first = banks.realize_bank("D2_DEVELOPMENT_BANK", FIXTURE_COMMIT, size=12)
    second = banks.realize_bank("D2_DEVELOPMENT_BANK", FIXTURE_COMMIT, size=12)
    assert [item["item_key"] for item in first] == \
        [item["item_key"] for item in second]


def test_no_study_bank_is_realized_or_committed(protocol):
    assert protocol["banks"]["realized"] is False
    assert protocol["banks"]["realization_requires_a_passed_shakedown"] is True
    committed = _git("ls-files", "studies/study4f").split()
    assert not any("bank" in path and path.endswith(".json")
                   for path in committed), committed


# ---------------------------------------------------------------------------
# 4. Interfaces and parsers
# ---------------------------------------------------------------------------


def test_the_primary_route_uses_no_chat_template_and_no_forced_closure(protocol):
    primary = protocol["routes"]["primary"]
    assert primary["route_id"] == "W1_RAW_DIRECT"
    assert primary["uses_chat_template"] is False
    assert primary["forced_reasoning_closure"] is None
    assert primary["forced_reasoning_closure_is_explicitly_absent"] is True
    prompt = interfaces.render_w1_raw_direct(interfaces.W1_SURFACE_FIXTURE_BODY)
    assert "</think>" not in prompt
    assert "<|" not in prompt
    assert prompt.endswith("Answer:\n")


def test_the_raw_direct_surface_reproduces_the_verified_source_hash():
    """The copied wrapper reproduces the byte surface the review verified."""
    assert interfaces.w1_surface_sha256() == \
        interfaces.W1_PROVENANCE["source_rendered_utf8_sha256"]
    rendered = interfaces.render_w1_raw_direct(interfaces.W1_SURFACE_FIXTURE_BODY)
    assert len(rendered.encode("utf-8")) == \
        interfaces.W1_PROVENANCE["source_rendered_utf8_bytes"]


def test_e0_is_correct_only_for_the_exact_registered_shape():
    ids = {"A": 32, "B": 33, "C": 34, "D": 35}
    eos = 151643
    assert interfaces.parse_e0([32, eos], ids, eos) == ("A", "CORRECT")
    assert interfaces.score_e0([32, eos], "A", ids, eos) is True
    assert interfaces.score_e0([32, eos], "B", ids, eos) is False
    # missing EOS
    assert interfaces.parse_e0([32], ids, eos)[1] == "INCORRECT_MISSING_EOS"
    # extra non-EOS token
    assert interfaces.parse_e0([32, 99], ids, eos)[1] == "INCORRECT_EXTRA_TOKEN"
    assert interfaces.parse_e0([32, eos, 99], ids, eos)[1] == \
        "INCORRECT_EXTRA_TOKEN"
    # unparseable
    assert interfaces.parse_e0([], ids, eos)[1] == "UNPARSEABLE"
    assert interfaces.parse_e0([99, eos], ids, eos)[1] == "UNPARSEABLE"
    for shape in ([32], [32, 99], [], [99, eos], [32, eos, eos]):
        assert interfaces.score_e0(shape, "A", ids, eos) is False, shape


def test_e0_performs_no_prefix_matching_or_normalization():
    ids = {"A": 32, "B": 33, "C": 34, "D": 35}
    eos = 151643
    # A correct answer followed by anything at all is not the registered shape.
    assert interfaces.e0_outcome([32, eos, 32], "A", ids, eos) != "CORRECT"
    # EOS alone carries no label.
    assert interfaces.e0_outcome([eos], "A", ids, eos) == "UNPARSEABLE"


def test_the_cot_parser_accepts_only_the_exact_final_line():
    assert interfaces.parse_cot("FINAL: A") == ("A", "CORRECT")
    assert interfaces.parse_cot("some reasoning\nFINAL: D") == ("D", "CORRECT")
    assert interfaces.parse_cot("FINAL: B\n\n\n") == ("B", "CORRECT")
    for rejected in ("FINAL: A ", " FINAL: A", "FINAL:A", "FINAL: a",
                     "FINAL: E", "final: A", "The answer is FINAL: A",
                     "FINAL: A extra", "", "\n\n", "FINAL: A\nnot a final line"):
        assert interfaces.parse_cot(rejected)[1] == "UNPARSEABLE", rejected


def test_unparseable_cot_responses_are_counted_never_dropped():
    assert interfaces.cot_outcome("garbage", "A") == "UNPARSEABLE"
    assert interfaces.cot_outcome("FINAL: B", "A") == "INCORRECT_WRONG_LABEL"
    assert interfaces.cot_outcome("FINAL: A", "A") == "CORRECT"


def test_cot_seeds_are_derived_and_reproducible():
    first = interfaces.cot_seed("SEAL", "RP_B1", "D2", "item-0001")
    assert first == interfaces.cot_seed("SEAL", "RP_B1", "D2", "item-0001")
    assert first != interfaces.cot_seed("SEAL", "RP_B1", "D3", "item-0001")
    assert first != interfaces.cot_seed("SEAL", "RP_B2", "D2", "item-0001")
    assert first != interfaces.cot_seed("SEAL", "RP_B1", "D2", "item-0002")
    assert first != interfaces.cot_seed("OTHER", "RP_B1", "D2", "item-0001")


def test_the_full_decoding_contract_has_no_unspecified_field():
    validation.validate_decoding_contracts()
    for field in validation.REQUIRED_E0_FIELDS:
        assert field in interfaces.E0_GENERATION_CONTRACT, field
    for field in validation.REQUIRED_C1_FIELDS:
        assert field in interfaces.C1_GENERATION_CONTRACT, field
    assert interfaces.E0_GENERATION_CONTRACT["max_new_tokens"] == 2
    assert interfaces.C1_GENERATION_CONTRACT["max_new_tokens"] == 4096


# ---------------------------------------------------------------------------
# 5. Statistics, recomputed independently of the production module
# ---------------------------------------------------------------------------


def _tail(n: int, k: int, p: Fraction) -> Fraction:
    """A local exact binomial tail. It imports no production calculator."""
    return sum((Fraction(comb(n, i)) * p ** i * (1 - p) ** (n - i)
                for i in range(k, n + 1)), Fraction(0))


def test_the_error_budget_recomputes_exactly(protocol):
    assert Fraction(1, 20) / 16 == Fraction(1, 320)
    assert protocol["statistics"]["alpha_global"] == "1/20"
    assert protocol["statistics"]["m_max"] == 16
    assert protocol["statistics"]["alpha_per_cell"] == "1/320"
    assert stats.ALPHA_PER_CELL == Fraction(1, 320)


def test_the_cot_cell_size_power_and_minimality_recompute():
    alpha = Fraction(1, 320)
    size = _tail(104, 90, Fraction(3, 4))
    power = _tail(104, 90, Fraction(9, 10))
    assert size <= alpha
    assert power >= Fraction(9, 10)
    assert _tail(104, 89, Fraction(3, 4)) > alpha, "boundary 90 is not minimal"
    assert size == stats.exact_size("COT")
    assert power == stats.exact_power("COT")


def test_the_e0_cell_size_power_and_minimality_recompute():
    alpha = Fraction(1, 320)
    size = _tail(60, 41, Fraction(1, 2))
    power = _tail(60, 41, Fraction(3, 4))
    assert size <= alpha
    assert power >= Fraction(9, 10)
    assert _tail(60, 40, Fraction(1, 2)) > alpha, "boundary 41 is not minimal"
    assert size == stats.exact_size("E0")
    assert power == stats.exact_power("E0")


@pytest.mark.parametrize("cell,floor,alt,n,boundary", [
    ("COT", Fraction(3, 4), Fraction(9, 10), 104, 90),
    ("E0", Fraction(1, 2), Fraction(3, 4), 60, 41),
])
def test_each_registered_sample_size_is_minimal(cell, floor, alt, n, boundary):
    alpha = Fraction(1, 320)
    for smaller in range(1, n):
        k = next((candidate for candidate in range(smaller + 1)
                  if _tail(smaller, candidate, floor) <= alpha), None)
        if k is None:
            continue
        assert _tail(smaller, k, alt) < Fraction(9, 10), \
            "n=%d already attains the budget, so %d is not minimal" % (smaller, n)
    assert stats.minimal_design(floor, alt) == (n, boundary)


def test_the_cell_census_is_exactly_sixteen(protocol):
    cells = stats.registered_cells()
    assert len(cells) == len(set(cells)) == 16 == stats.M_MAX
    assert sorted(cells) == sorted(protocol["statistics"]["registered_cells"])
    assert len({cell.split("|")[0] for cell in cells}) == 4
    assert len({cell.split("|")[1] for cell in cells}) == 2
    assert len({cell.split("|")[2] for cell in cells}) == 2


def test_d2_and_d3_can_never_be_pooled():
    with pytest.raises(stats.Study4FPoolingProhibitedError):
        stats.pool(["D2"], ["D3"])
    assert "D2" in stats.DEPTHS and "D3" in stats.DEPTHS
    for cell in stats.registered_cells():
        assert cell.split("|")[1] in ("D2", "D3")


def test_the_pass_rule_is_an_integer_comparison():
    assert stats.passes("COT", 90) is True
    assert stats.passes("COT", 89) is False
    assert stats.passes("E0", 41) is True
    assert stats.passes("E0", 40) is False
    with pytest.raises(ValueError):
        stats.passes("E0", 61)


# ---------------------------------------------------------------------------
# 6. Candidate-local state machine, over every pass/fail pattern
# ---------------------------------------------------------------------------


def test_a_candidate_failure_never_blocks_a_later_candidate():
    """Exhaustive over every candidate-level pass/fail combination."""
    for cot_pattern in product([False, True], repeat=3):
        for e0_pattern in product([False, True], repeat=3):
            results = {}
            for role, cot_ok, e0_ok in zip(machine.LADDER, cot_pattern,
                                           e0_pattern):
                for depth in machine.DEPTHS:
                    results[(role, depth, "COT")] = cot_ok
                    results[(role, depth, "E0")] = e0_ok
            outcome = machine.run_ladder(results)
            expected = next((role for role, cot_ok, e0_ok
                             in zip(machine.LADDER, cot_pattern, e0_pattern)
                             if cot_ok and e0_ok), None)
            assert outcome["qualified_candidate"] == expected, \
                (cot_pattern, e0_pattern)


def test_every_depth_level_failure_pattern_is_candidate_local():
    """A single failing depth cell disqualifies only its own candidate."""
    for role_index, role in enumerate(machine.LADDER):
        for depth in machine.DEPTHS:
            for route in ("COT", "E0"):
                results = {}
                for other in machine.LADDER:
                    for other_depth in machine.DEPTHS:
                        results[(other, other_depth, "COT")] = True
                        results[(other, other_depth, "E0")] = True
                results[(role, depth, route)] = False
                outcome = machine.run_ladder(results)
                expected = machine.LADDER[0] if role_index != 0 else \
                    machine.LADDER[1]
                assert outcome["qualified_candidate"] == expected, \
                    (role, depth, route)


def test_a_failed_cot_cell_skips_the_e0_cells_of_that_candidate_only():
    results = {}
    for role in machine.LADDER:
        for depth in machine.DEPTHS:
            results[(role, depth, "COT")] = True
            results[(role, depth, "E0")] = True
    results[("RP_B1", "D3", "COT")] = False
    outcome = machine.run_ladder(results)
    first = outcome["candidates"][0]
    assert first["role"] == "RP_B1"
    assert first["qualified"] is False
    assert first["e0_cells_run"] == 0
    assert outcome["qualified_candidate"] == "RP_B2"


def test_no_qualified_candidate_stops_without_running_rt():
    results = {}
    for role in machine.LADDER + (machine.TARGET,):
        for depth in machine.DEPTHS:
            results[(role, depth, "COT")] = True
            results[(role, depth, "E0")] = False
    outcome = machine.run_study(results)
    assert outcome["qualified_candidate"] is None
    assert outcome["rt_authorized"] is False
    assert outcome["rt"] is None
    assert outcome["rt_cells_run"] == 0
    assert outcome["state"] == \
        "STUDY4F_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER"


@pytest.mark.parametrize("rt_cot,rt_e0,expected", [
    ((True, True), (True, True),
     "STUDY4F_BEHAVIORAL_FEASIBILITY_SUPPORTED_AWAITING_SEPARATE_CONFIRMATION"),
    ((True, False), (True, True),
     "STUDY4F_RP_DEV_IDENTIFIED_TARGET_NO_COT_HEADROOM"),
    ((True, True), (True, False),
     "STUDY4F_RP_DEV_IDENTIFIED_TARGET_E0_NOT_OBSERVED"),
])
def test_the_rt_route_reaches_only_registered_states(rt_cot, rt_e0, expected):
    results = {}
    for role in machine.LADDER:
        for depth in machine.DEPTHS:
            results[(role, depth, "COT")] = True
            results[(role, depth, "E0")] = True
    for depth, cot_ok, e0_ok in zip(machine.DEPTHS, rt_cot, rt_e0):
        results[(machine.TARGET, depth, "COT")] = cot_ok
        results[(machine.TARGET, depth, "E0")] = e0_ok
    outcome = machine.run_study(results)
    assert outcome["qualified_candidate"] == "RP_B1"
    assert outcome["state"] == expected
    assert machine.state_is_registered(str(outcome["state"]))


def test_the_only_candidate_disposition_is_developmental():
    assert machine.CANDIDATE_QUALIFIED == \
        "RP_B_DEVELOPMENTAL_CANDIDATE_PENDING_CONFIRMATION"
    assert "CONFIRMED" not in machine.CANDIDATE_QUALIFIED
    for state in machine.REGISTERED_TERMINAL_STATES:
        assert "CONFIRMED" not in state.replace("SEPARATE_CONFIRMATION", "")


# ---------------------------------------------------------------------------
# 7. The seven coordinated mutations reported by the Study 3R review
# ---------------------------------------------------------------------------


def test_every_study3r_survivor_has_a_registered_disposition(protocol):
    recorded = protocol["study3r_relationship"]["surviving_mutation_dispositions"]
    assert set(recorded) == set(validation.STUDY3R_SURVIVOR_DISPOSITIONS)
    assert len(recorded) == 7
    assert recorded == validation.STUDY3R_SURVIVOR_DISPOSITIONS
    assert set(recorded.values()) <= {"killed", "structurally_inapplicable"}


def test_adv_cot_parser_regex_unanchored_is_structurally_inapplicable():
    """Study 4F's CoT parser uses exact equality, so there is no regex to unanchor."""
    source = (ANALYSIS / "study4f_interfaces.py").read_text(encoding="utf-8")
    assert "import re" not in source
    assert "re.match" not in source and "re.search" not in source
    # The mutation's intent -- accepting an unanchored match -- is rejected.
    for smuggled in ("FINAL: A somewhere later",
                     "prefix FINAL: A",
                     "  FINAL: A",
                     "FINAL: A\t"):
        assert interfaces.parse_cot(smuggled)[1] == "UNPARSEABLE", smuggled


def test_adv_d2_d3_ceiling_mix_is_structurally_inapplicable(protocol):
    """There is no ceiling bank and no mixed bank in Study 4F to mix."""
    assert protocol["banks"]["confirmation_bank_exists"] is False
    assert protocol["banks"]["mixed_family_banks_permitted"] is False
    assert set(banks.BANK_FAMILY.values()) == {"D2", "D3"}
    assert len(banks.BANK_FAMILY) == 2
    for bank_id, family in banks.BANK_FAMILY.items():
        items = banks.realize_bank(bank_id, FIXTURE_COMMIT, size=8)
        assert {item["family"] for item in items} == {family}, bank_id


def test_adv_d2_d3_family_mix_drops_depth_three_is_killed(fixture_banks):
    """Swapping a D2 item into the D3 bank must fail the validator."""
    d2, d3 = fixture_banks
    mutated = copy.deepcopy(list(d3))
    mutated[0] = copy.deepcopy(d2[0])
    with pytest.raises(validation.Study4FPreflightError):
        validation.validate_bank("D3_DEVELOPMENT_BANK", mutated)
    with pytest.raises(validation.Study4FPreflightError):
        validation.validate_bank_pair(d2, mutated)


def test_adv_d3_family_depth_relabelled_is_killed(fixture_banks):
    """Relabelling the declared depth cannot survive a recomputed depth."""
    _d2, d3 = fixture_banks
    mutated = copy.deepcopy(list(d3))
    mutated[0]["depth"] = 2
    with pytest.raises(validation.Study4FPreflightError):
        validation.validate_bank("D3_DEVELOPMENT_BANK", mutated)
    relabelled = copy.deepcopy(list(d3))
    for item in relabelled:
        item["family"] = "D2"
        item["depth"] = 2
    with pytest.raises(validation.Study4FPreflightError):
        validation.validate_bank("D3_DEVELOPMENT_BANK", relabelled)
    # The recomputed depth is derived from the item's own arity.
    assert validation.recompute_depth(d3[0]) == 3


def test_adv_forced_reasoning_closure_changed_is_killed(monkeypatch):
    """Setting a closure on either route fails preflight."""
    for provenance in (interfaces.W1_PROVENANCE, interfaces.C1_PROVENANCE):
        mutated = dict(provenance)
        mutated["forced_reasoning_closure"] = "</think>\n\n"
        monkeypatch.setattr(
            interfaces,
            "W1_PROVENANCE" if provenance is interfaces.W1_PROVENANCE
            else "C1_PROVENANCE",
            mutated)
        with pytest.raises(validation.Study4FPreflightError):
            validation.validate_no_forced_closure()
        monkeypatch.undo()


def test_adv_forced_reasoning_closure_removed_is_structurally_inapplicable():
    """There is no closure to remove: both routes register its absence."""
    assert interfaces.W1_PROVENANCE["forced_reasoning_closure"] is None
    assert interfaces.C1_PROVENANCE["forced_reasoning_closure"] is None
    assert interfaces.W1_PROVENANCE[
        "forced_reasoning_closure_is_explicitly_absent"] is True
    assert interfaces.C1_PROVENANCE[
        "forced_reasoning_closure_is_explicitly_absent"] is True
    assert interfaces.C1_PROVENANCE["closure_absence_is_decision_bearing"] is True
    validation.validate_no_forced_closure()


def test_adv_surfaces_closure_emptied_while_bytes_unchanged_is_inapplicable():
    """The E0 surface carries no closure bytes that an empty string could hide."""
    prompt = interfaces.render_w1_raw_direct(interfaces.W1_SURFACE_FIXTURE_BODY)
    assert "</think>" not in prompt
    assert "<think>" not in prompt
    # The surface hash binds the exact bytes, so emptying a declared closure
    # while leaving the rendered bytes unchanged cannot go unnoticed: there is
    # no declared closure, and the bytes themselves are hashed.
    assert interfaces.w1_surface_sha256() == \
        interfaces.W1_PROVENANCE["source_rendered_utf8_sha256"]
    mutated = prompt.replace("Answer:\n", "Answer:\n</think>\n\n")
    assert hashlib.sha256(mutated.encode("utf-8")).hexdigest() != \
        interfaces.w1_surface_sha256()


def test_a_preflight_failure_is_never_repaired_by_a_decision_bearing_change():
    assert validation.PREFLIGHT_FAILURE_STATE == \
        "STUDY4F_PREFLIGHT_FAILED_NO_MODEL_EXECUTION"
    assert machine.state_is_registered(validation.PREFLIGHT_FAILURE_STATE)


def test_the_full_preflight_passes_on_synthetic_fixtures(fixture_banks):
    d2, d3 = fixture_banks
    performed = validation.run_preflight(d2, d3)
    assert set(performed) == {
        "statistics", "decoding_contracts", "forced_closure_absence",
        "parsers", "state_machine", "banks"}


# ---------------------------------------------------------------------------
# 8. The unquantized resource route
# ---------------------------------------------------------------------------


def test_the_resource_requirement_is_computed_without_acquiring_weights():
    proof = resource_route.prove_route("RP_B3")
    assert proof["weight_files_acquired"] == 0
    assert proof["model_constructions"] == 0
    assert proof["quantization_attempted"] is False
    assert proof["sharding_attempted"] is False
    assert proof["cpu_or_disk_offload_attempted"] is False
    assert proof["device_map_auto_used"] is False
    # 32e9 bfloat16 parameters is 64 GB before the KV cache and the reserve.
    assert proof["weight_bytes"] == 64_000_000_000
    assert proof["required_bytes"] > proof["weight_bytes"]


def test_an_unavailable_route_registers_its_state_and_never_quantizes():
    proof = resource_route.prove_route("RP_B3")
    if proof["route_available"]:
        assert proof["state"] is None
        assert proof["qualifying_accelerators"] >= 1
    else:
        assert proof["state"] == \
            "STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE"
        assert machine.state_is_registered(str(proof["state"]))
        assert proof["quantization_attempted"] is False


def test_the_loading_contract_forbids_every_offload_route(protocol):
    contract = protocol["model_loading_contract"]
    assert contract["trust_remote_code"] is False
    assert contract["unquantized_weights"] is True
    assert contract["torch_dtype"] == "bfloat16"
    assert contract["adapter"] is None
    assert contract["cpu_offload"] is False
    assert contract["disk_offload"] is False
    assert contract["device_map_auto"] is False
    assert contract["batch_size"] == 1
    assert contract["resource_route_must_be_proven_before_weight_acquisition"] \
        is True
    assert contract["unavailable_route_state"] == \
        "STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE"


# ---------------------------------------------------------------------------
# 9. Claim discipline and repository invariants
# ---------------------------------------------------------------------------


def test_study4f_claims_nothing_scientific(protocol):
    boundary = protocol["claim_boundary"]
    for key, value in boundary.items():
        if key == "may_only_identify":
            continue
        assert value is False, key
    assert boundary["may_only_identify"] == \
        "RP_B_DEVELOPMENTAL_CANDIDATE_PENDING_CONFIRMATION"


def test_the_prohibited_conclusions_are_registered(protocol):
    prohibited = protocol["prohibited_conclusions"]
    assert len(prohibited) == 6
    for phrase in ("J-space does not exist", "J-space is unobservable",
                   "RP-B was confirmed"):
        assert phrase in prohibited


def test_the_evidence_ledger_is_untouched_and_ends_at_ev_0016():
    ledger = ROOT / "paper" / "evidence_ledger.csv"
    payload = ledger.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == \
        "3821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1"
    rows = [line for line in payload.decode("utf-8").splitlines()
            if line.startswith("EV-")]
    assert rows[-1].split(",", 1)[0] == "EV-0016"
    at_closure = _git("rev-parse",
                      "%s:paper/evidence_ledger.csv" % STUDY3R_CLOSURE_COMMIT).strip()
    assert _git("rev-parse", "HEAD:paper/evidence_ledger.csv").strip() == at_closure


def test_no_prohibited_scientific_operation_is_reachable_from_this_module():
    """Study 4F publishes no D0, logit, activation or patching code path."""
    for module in ANALYSIS.glob("study4f_*.py"):
        source = module.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in ("output_hidden_states", "output_attentions",
                          "register_forward_hook", "activation_patch",
                          "from_pretrained", "automodelforcausallm"):
            assert forbidden not in lowered, (module.name, forbidden)


def test_the_governance_admission_is_narrow_and_bound_to_this_authority():
    """Study 4F widened the Study 3R governance scope by exactly one namespace."""
    source = (ROOT / "tests" / "test_study3r_operator_governance.py"
              ).read_text(encoding="utf-8")
    assert 'STUDY4F_NAMESPACE = "studies/study4f/"' in source
    assert AUTHORITY_COMMIT in source
    assert "study4f_minimal_behavioral_feasibility_authority.md" in source
    # The admission must not be a blanket widening.
    assert 'STUDY4F_NAMESPACE = "studies/"' not in source
    assert "AUTHORING_NAMESPACE = \"studies/study3r/\"" in source
    for protected in ("REJECTED_CANDIDATE_PATHS", "REVIEW_ARTIFACTS",
                      "PROTECTED_HISTORICAL"):
        assert protected in source, protected


def test_the_governance_change_is_a_scope_predicate_only_change():
    """Mechanical proof that only scope constants and predicates moved.

    The Study 3R focused-review module classifies
    ``tests/test_study3r_operator_governance.py`` as a candidate path, so
    admitting the Study 4F namespace expires that module's
    ``test_the_review_changed_no_candidate_or_protected_path``. The expiry is
    recorded rather than repaired, and this test carries the substantive
    guarantee forward: the change adds and removes no test, changes no
    assertion, and moves no protected-blob list.
    """
    import ast

    before = _git("show", "%s:tests/test_study3r_operator_governance.py"
                  % STUDY3R_CLOSURE_COMMIT)
    after = (ROOT / "tests" / "test_study3r_operator_governance.py"
             ).read_text(encoding="utf-8")

    def functions(source):
        tree = ast.parse(source)
        return {node.name: ast.dump(node) for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)}

    def literals(source, names):
        tree = ast.parse(source)
        found = {}
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    found[target.id] = ast.literal_eval(node.value)
        return found

    old_functions, new_functions = functions(before), functions(after)
    assert set(old_functions) == set(new_functions), \
        set(old_functions) ^ set(new_functions)

    # Only the two scope predicates may differ, and only in the namespace tuple.
    changed = {name for name in old_functions
               if old_functions[name] != new_functions[name]}
    assert changed == {"test_governance_changed_no_reviewed_candidate_or_protected_path",
                       "test_only_the_readme_was_modified_and_everything_else_was_added"}, \
        sorted(changed)
    for name in changed:
        assert new_functions[name].count("Assert") == \
            old_functions[name].count("Assert"), name

    protected = ("REJECTED_CANDIDATE_PATHS", "REVIEW_ARTIFACTS",
                 "PROTECTED_HISTORICAL", "GOVERNANCE_ADDED",
                 "GOVERNANCE_MODIFIED", "AUTHORING_ADDED", "AUTHORING_MODIFIED")
    old_literals = literals(before, protected)
    new_literals = literals(after, protected)
    assert old_literals == new_literals, \
        {key for key in old_literals if old_literals[key] != new_literals.get(key)}

    admitted = _load_governance_module().ADMITTED_NAMESPACES
    assert admitted == ("studies/study3r/", "studies/study4f/"), admitted


def test_every_scope_expiry_is_recorded_and_none_is_suppressed(status):
    expiries = status["scope_expiries"]
    assert expiries["count"] == len(expiries["expired_assertions"]) == 3
    assert expiries["in_the_registered_repository_baseline"] == 0
    assert expiries["new_repository_failure_node_ids"] == []
    assert expiries["standing_repository_failure_node_ids_unchanged"] is True
    for record in expiries["expired_assertions"]:
        assert record["repaired"] is False
        assert record["suppressed"] is False
        assert record["editable_under_this_authority"] is False
        assert record["inside_the_registered_repository_baseline"] is False
        module, _, name = record["node_id"].partition("::")
        assert (ROOT / module).is_file(), module
        # The expired module itself must be byte-identical to the closure head.
        if module.startswith("studies/study3r/"):
            assert _git("rev-parse", "%s:%s" % (STUDY3R_CLOSURE_COMMIT, module)
                        ).strip() == _git("rev-parse", "HEAD:%s" % module).strip()
        carrier_module, _, carrier = \
            record["guarantee_carried_forward_by"].partition("::")
        assert carrier_module == \
            "studies/study4f/tests/test_study4f_behavioral_feasibility.py"
        assert carrier in globals(), carrier
    governance = expiries["governance_change"]
    assert governance["namespaces_admitted"] == ["studies/study4f/"]
    assert governance["individual_paths_admitted"] == []
    assert governance["test_functions_added"] == 0
    assert governance["test_functions_removed"] == 0
    assert governance["assertions_changed"] == 0
    assert governance["study3r_lifecycle_value_changed"] is False


def test_no_expiry_hides_a_moved_study3r_byte():
    """Every expired predicate's substantive claim still holds at this head."""
    changed = [line.strip() for line
               in _git("diff", "--name-only", STUDY3R_CLOSURE_COMMIT,
                       "HEAD").splitlines() if line.strip()]
    study3r_changed = [path for path in changed
                       if path.startswith("studies/study3r/")]
    assert study3r_changed == [], study3r_changed
    assert "paper/evidence_ledger.csv" not in changed
    assert ".gitattributes" not in changed
    assert "tests/test_study3r_protocol_v1.py" not in changed


def test_the_eight_standing_failure_node_ids_are_recorded_unchanged():
    disclosure = _json(ROOT / "studies" / "study3r" /
                       "study3r_authoring_disclosure_v1.json")
    registered = disclosure["test_results"]["baseline"]["failure_node_ids"]
    assert sorted(STANDING_FAILURE_NODE_IDS) == sorted(registered)
    assert len(STANDING_FAILURE_NODE_IDS) == 8


# ---------------------------------------------------------------------------
# 10. The registered terminal state
# ---------------------------------------------------------------------------

STATUS_JSON = STUDY4F / "STATUS.json"
STATUS_SCHEMA = STUDY4F / "STATUS.schema.json"
SHAKEDOWN = STUDY4F / "shakedown" / "study4f_shakedown_disposition.json"
DISCLOSURE = STUDY4F / "STUDY4F_TERMINAL_DISCLOSURE.md"
README = STUDY4F / "README.md"


@pytest.fixture(scope="module")
def status():
    return _json(STATUS_JSON)


@pytest.fixture(scope="module")
def shakedown():
    return _json(SHAKEDOWN)


def test_status_validates_against_its_restrictive_schema(status):
    jsonschema = pytest.importorskip("jsonschema")
    schema = _json(STATUS_SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(status, schema)


def test_the_final_state_is_exactly_one_registered_state(status, shakedown):
    assert status["lifecycle_state"] == \
        "STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE"
    assert machine.state_is_registered(status["lifecycle_state"])
    assert status["terminal"] is True
    assert shakedown["disposition"] == status["lifecycle_state"]
    assert status["reached_stage"]["shakedown_disposition"] == \
        status["lifecycle_state"]
    text = DISCLOSURE.read_text(encoding="utf-8")
    reached = [state for state in machine.REGISTERED_TERMINAL_STATES
               if state in text and state.startswith("STUDY4F_")]
    assert status["lifecycle_state"] in reached


def test_the_resource_proof_recomputes_from_the_published_module(shakedown):
    recorded = shakedown["resource_route_proof"]
    proof = resource_route.prove_route("RP_B3")
    assert recorded["weight_bytes"] == proof["weight_bytes"] == 64_000_000_000
    assert recorded["max_registered_kv_cache_bytes"] == proof["kv_cache_bytes"]
    assert recorded["safety_reserve_bytes"] == proof["safety_reserve_bytes"]
    assert recorded["required_bytes"] == proof["required_bytes"]
    assert recorded["required_bytes"] == (
        recorded["weight_bytes"] + recorded["max_registered_kv_cache_bytes"]
        + recorded["safety_reserve_bytes"])
    assert recorded["immutable_revision"] == \
        "711ad2ea6aa40cfca18895e8aca02ab92df1a746"


def test_no_prohibited_fallback_was_attempted(shakedown):
    fallbacks = shakedown["prohibited_fallbacks_not_attempted"]
    assert all(value is False for value in fallbacks.values()), fallbacks
    assert shakedown["decision_bearing_value_changed"] is False
    assert shakedown["white_listed_fixes_applied"] == []


def test_the_shakedown_stayed_inside_its_registered_budget(shakedown):
    assert shakedown["attempts_used"] <= shakedown["attempts_permitted"] == 3
    assert shakedown["accelerator_hours_used"] <= \
        shakedown["accelerator_hours_permitted"] == 6
    assert shakedown["fixtures"]["kind"] == "synthetic non-study"
    assert shakedown["fixtures"]["is_the_registered_authority_commit"] is False
    assert shakedown["fixtures"]["study_bank_model_outputs_inspected"] == 0
    assert shakedown["fixtures"]["study_banks_realized"] == 0
    assert shakedown["fixtures"]["fixture_identity"] != AUTHORITY_COMMIT


def test_nothing_downstream_of_the_stop_was_reached(status, shakedown):
    for key, value in status["not_reached"].items():
        assert value is False, key
    assert shakedown["banks_realized"] is False
    assert shakedown["execution_seal_created"] is False
    assert shakedown["developmental_execution_authorized"] is False
    committed = _git("ls-files", "studies/study4f").split()
    assert not any("seal" in path for path in committed), committed


def test_every_authorization_flag_and_counter_is_false_or_zero(status, shakedown):
    assert all(value is False for value in status["authorization_flags"].values())
    assert all(value == 0 for value in status["zero_operation_counters"].values())
    assert all(value == 0 for value in shakedown["counters"].values())
    for key in ("d0_runs", "logit_reads", "activation_collections",
                "activation_patches"):
        assert status["zero_operation_counters"][key] == 0, key


def test_no_scientific_claim_is_recorded(status):
    for key, value in status["claim_boundary"].items():
        assert value is False, key
    assert status["evidence_ledger"]["rows_added_by_study4f"] == 0
    assert status["evidence_ledger"]["last_row"] == "EV-0016"


@pytest.mark.parametrize("claim", [
    "J-space does not exist",
    "J-space is unobservable",
    "the model cannot reason internally",
    "single-forward reasoning was demonstrated",
    "RP-B was confirmed",
])
def test_the_disclosure_asserts_no_prohibited_conclusion(claim):
    """A prohibited phrase may appear only inside an explicit negation.

    The check is paragraph-scoped rather than line-scoped, because Markdown
    line wrapping is arbitrary and can separate a phrase from the negation that
    governs it.
    """
    negations = {"no", "not", "never", "neither", "nor", "prohibited",
                 "prohibits", "unanswered"}
    for path in (DISCLOSURE, README):
        text = path.read_text(encoding="utf-8")
        for paragraph in text.split("\n\n"):
            if claim.lower() not in paragraph.lower():
                continue
            lowered = paragraph.lower()
            for character in "*`_|#>":
                lowered = lowered.replace(character, " ")
            assert negations & set(lowered.split()), (path.name, paragraph)


def test_the_disclosure_states_what_the_state_does_and_does_not_establish(status):
    text = DISCLOSURE.read_text(encoding="utf-8")
    assert "It establishes" in text
    assert "It does not establish" in text
    assert len(status["what_this_state_establishes"]["establishes"]) >= 3
    assert len(status["what_this_state_establishes"]["does_not_establish"]) >= 5
    for phrase in ("AUTHORITY_ONLY_PARTIALLY_EXECUTED",
                   "STUDY3R_TERMINAL_CLOSURE_COMPLETE_RESEARCH_QUESTION_UNANSWERED",
                   "EV-0016", "8 failed, 5,120 passed, 16 skipped"):
        assert phrase in text, phrase


def test_the_disclosure_reports_the_skipped_cells_and_their_reason():
    text = DISCLOSURE.read_text(encoding="utf-8")
    assert "Zero of the sixteen registered cells were executed" in text
    assert "STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE" in text
    assert "skipped" in text.lower()


def test_the_readme_routes_to_the_status_router_first():
    text = README.read_text(encoding="utf-8")
    assert text.index("STATUS.json") < text.index("study4f_protocol_v1.json")
    assert "STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE" in text
    lowered = text.lower()
    assert "no scientific result" in lowered
    assert "ev-0016" in lowered


# ---------------------------------------------------------------------------
# 11. Byte hygiene
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relative", [
    "studies/study4f/prompts/study4f_minimal_behavioral_feasibility_authority.md",
    "studies/study4f/protocol/study4f_protocol_v1.json",
    "studies/study4f/protocol/study4f_protocol_v1.schema.json",
    "studies/study4f/analysis/study4f_task_banks.py",
    "studies/study4f/analysis/study4f_interfaces.py",
    "studies/study4f/analysis/study4f_design_statistics.py",
    "studies/study4f/analysis/study4f_state_machine.py",
    "studies/study4f/analysis/study4f_validation.py",
    "studies/study4f/analysis/study4f_resource_route.py",
    "studies/study4f/tests/test_study4f_behavioral_feasibility.py",
])
def test_every_study4f_artifact_is_lf_only(relative):
    payload = (ROOT / relative).read_bytes()
    assert payload
    assert b"\r" not in payload, relative
    assert payload.endswith(b"\n"), relative
    assert not payload.startswith(b"\xef\xbb\xbf"), relative
