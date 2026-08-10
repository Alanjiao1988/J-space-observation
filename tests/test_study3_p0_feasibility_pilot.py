"""Deterministic tests for the Study 3-P0 feasibility pilot.

This module is model-free by construction. It performs no download, no revision
resolution, no weight load, no tokenizer construction, no tokenization, no
forward pass, no decode step, no sequence scoring, no generation, no activation
extraction and no provider call. It draws no seed, writes no bank row, reads no
confirmation content and produces no scientific evidence row.

What it establishes
-------------------
The operator authority authorizes one physically isolated, tightly capped
feasibility pilot and forbids every shortcut that would let the pilot quietly
become a formal round. These tests are the mechanical part of that boundary:

* the authority copy is byte-identical to its registered identity;
* the frozen corpus and the P0 protocol document re-derive byte-exactly from the
  binding registry, so nothing was hand-edited into them;
* the corpus ground truth, distractors, nuisance states and pair construction
  are recomputed *independently here* and agree;
* the P0 renderer, written from the registry alone, produces byte-identical
  prompts to the committed draft-v0.5 fixture renderer -- which is the section 2
  feasibility question about an independent implementation;
* the registered operation arithmetic reconciles exactly with the corpus;
* `K6-SEP` is structurally absent for `S2` and `S3`, never duplicated;
* `S3` registers no new surface;
* the permanent `study3-p0-only/` exclusion is machine-readable and enforced;
* every fail-closed transition has a negative test that proves it *fails*.

Standard library only, by design.
"""

import hashlib
import importlib.util
import itertools
import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P0_DIR = os.path.join(REPO_ROOT, "studies", "study3", "pilot", "p0")
AUTHORITY_PATH = os.path.join(
    REPO_ROOT, "studies", "study3", "prompts",
    "study3_p0_feasibility_pilot_authority.md")
CORPUS_PATH = os.path.join(P0_DIR, "corpus", "p0_corpus.json")
MANIFEST_PATH = os.path.join(P0_DIR, "corpus", "p0_corpus_manifest.json")
CENSUS_PATH = os.path.join(P0_DIR, "corpus", "p0_corpus_census.md")
PROTOCOL_JSON_PATH = os.path.join(P0_DIR, "p0_protocol.json")
FIXTURE_RENDERER_PATH = os.path.join(
    REPO_ROOT, "tests", "test_study3_rendering_registry_v0_5.py")

AUTHORITY_SHA256 = (
    "80efc7ef8bfe5e3b5e5235f530a44730f185187aa52b85945875fe68ef1eda11")
AUTHORITY_BYTES = 29282

if P0_DIR not in sys.path:
    sys.path.insert(0, P0_DIR)

import p0_corpus  # noqa: E402
import p0_counters  # noqa: E402
import p0_parser  # noqa: E402
import p0_protocol as p0_protocol_module  # noqa: E402
import p0_renderer  # noqa: E402


def _load_json(path):
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def _fixture_module():
    """Load the committed draft-v0.5 fixture renderer by path.

    Importing it by name depends on the collection root being on sys.path, which
    is not guaranteed in a clean clone. It is a byte-protected object; this test
    reads it and never writes it.
    """
    spec = importlib.util.spec_from_file_location(
        "study3_v0_5_fixture_renderer", FIXTURE_RENDERER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def registry():
    return p0_renderer.load_registry()


@pytest.fixture(scope="module")
def protocol():
    return p0_renderer.load_protocol()


@pytest.fixture(scope="module")
def corpus():
    return _load_json(CORPUS_PATH)


@pytest.fixture(scope="module")
def manifest():
    return _load_json(MANIFEST_PATH)


@pytest.fixture(scope="module")
def p0_protocol_document():
    return _load_json(PROTOCOL_JSON_PATH)


@pytest.fixture(scope="module")
def rows(registry, protocol):
    return p0_corpus.build_rows(registry, protocol)


# ---------------------------------------------------------------------------
# Authority identity and ordering
# ---------------------------------------------------------------------------

def test_authority_copy_is_byte_identical():
    with open(AUTHORITY_PATH, "rb") as handle:
        raw = handle.read()
    assert len(raw) == AUTHORITY_BYTES
    assert hashlib.sha256(raw).hexdigest() == AUTHORITY_SHA256


def test_authority_copy_carries_no_cr():
    with open(AUTHORITY_PATH, "rb") as handle:
        raw = handle.read()
    assert b"\r" not in raw


def test_protocol_records_the_authority_identity(p0_protocol_document):
    authority = p0_protocol_document["authority"]
    assert authority["sha256"] == AUTHORITY_SHA256
    assert authority["bytes"] == AUTHORITY_BYTES
    assert authority["carries_cr"] is False


# ---------------------------------------------------------------------------
# Re-derivation: nothing was hand-edited into a frozen artifact
# ---------------------------------------------------------------------------

def _run_p0_script(script, *args):
    return subprocess.run(
        [sys.executable, os.path.join(P0_DIR, script)] + list(args),
        capture_output=True, text=True, check=False)


def test_frozen_corpus_re_derives_byte_exactly():
    result = _run_p0_script("p0_freeze_corpus.py", "--check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_p0_protocol_document_re_derives_byte_exactly():
    result = _run_p0_script("p0_protocol.py", "--check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_corpus_artifacts_are_lf_only_and_end_with_one_newline():
    for path in (CORPUS_PATH, MANIFEST_PATH, PROTOCOL_JSON_PATH):
        with open(path, "rb") as handle:
            raw = handle.read()
        assert b"\r" not in raw, path
        assert raw.endswith(b"\n"), path
        assert not raw.endswith(b"\n\n"), path


def test_manifest_row_digests_match_the_corpus(corpus, manifest):
    by_id = {row["row_id"]: row for row in corpus["rows"]}
    assert len(by_id) == manifest["row_count"]
    for entry in manifest["per_row"]:
        row = by_id[entry["row_id"]]
        assert entry["base_item_id"] == row["base_item_id"]
        for recorded, member in zip(entry["members"], row["members"]):
            assert recorded["prompt_sha256"] == member["prompt_sha256"]
            assert recorded["prompt_bytes"] == member["prompt_bytes"]


def test_every_committed_prompt_hash_recomputes(corpus):
    for row in corpus["rows"]:
        for member in row["members"]:
            encoded = member["prompt"].encode("utf-8")
            assert hashlib.sha256(encoded).hexdigest() == member["prompt_sha256"]
            assert len(encoded) == member["prompt_bytes"]


def test_aggregate_corpus_digest_recomputes(corpus, manifest):
    assert p0_corpus.aggregate_sha256(corpus["rows"]) \
        == manifest["aggregate_prompt_sha256"]


def test_committed_census_matches_the_manifest(manifest):
    with open(CENSUS_PATH, "rb") as handle:
        text = handle.read().decode("utf-8")
    assert manifest["aggregate_prompt_sha256"] in text
    for row in manifest["per_row"]:
        assert row["base_item_id"] in text


# ---------------------------------------------------------------------------
# Independent recomputation of the science
# ---------------------------------------------------------------------------

def test_ground_truth_recomputes_independently(corpus):
    expected = {}
    for row in corpus["rows"]:
        params = row["operation_parameters"]
        x = int(params["x"])
        if row["tuple_class_id"] == "K2-none-0":
            value = x
        elif row["tuple_class_id"] == "K3-affine_mod10-1":
            value = (int(params["a1"]) * x + int(params["b1"])) % 10
        elif row["tuple_class_id"] == "K3-permutation_chain-1":
            image = [int(v) for v in params["p1"].strip("[]").split()]
            assert sorted(image) == list(range(10))
            assert image != list(range(10)), "the permutation must be non-identity"
            value = image[x]
        else:
            raise AssertionError("unregistered tuple class")
        assert row["ground_truth"] == str(value)
        expected[row["tuple_class_id"]] = str(value)
    assert set(expected) == {
        "K2-none-0", "K3-affine_mod10-1", "K3-permutation_chain-1"}


def test_distractors_are_distinct_and_exclude_the_correct_answer(corpus):
    for row in corpus["rows"]:
        triple = row["ordered_distractor_triple"]
        assert len(triple) == 3
        assert len(set(triple)) == 3
        assert row["ground_truth"] not in triple
        for value in triple:
            assert value in [str(v) for v in range(10)]


def test_option_layout_recomputes_from_the_nuisance_state(corpus, registry):
    for row in corpus["rows"]:
        if row["profile"] not in ("S1", "S4"):
            continue
        for member in row["members"]:
            state = member["nuisance_state"]
            position = state["content_position"]
            symbol_index = state["correct_symbol_index"]
            alphabet_index = state["label_alphabet_index"]
            names = list(registry["label_alphabets"]["alphabets"])
            alphabet = registry["label_alphabets"]["alphabets"][
                names[alphabet_index]]
            shift = (symbol_index - position) % 4
            expected = [alphabet[(slot + shift) % 4] for slot in range(4)]
            assert member["displayed_labels"] == expected
            assert member["displayed_contents"][position] == row["ground_truth"]
            assert member["displayed_labels"][position] == alphabet[symbol_index]


def test_label_alphabet_is_disjoint_from_the_answer_domain(registry):
    domain = set(registry["answer_domain"]["surface_forms"])
    for symbols in registry["label_alphabets"]["alphabets"].values():
        assert not set(symbols) & domain


def test_baseline_nuisance_states_cycle_over_the_registered_32_support():
    observed = {p0_corpus.baseline_state(k) for k in range(32)}
    assert observed == set(itertools.product(range(4), range(4), range(2)))
    assert len(observed) == 32


@pytest.mark.parametrize("contrast,factor", [
    ("K5-P1", "content_position"),
    ("K5-P2", "content_position"),
    ("K5-P3", "content_position"),
    ("K5-S1", "correct_symbol_index"),
    ("K5-S2", "correct_symbol_index"),
    ("K5-S3", "correct_symbol_index"),
    ("K5-A1", "label_alphabet_index"),
])
def test_k5_varies_exactly_one_registered_factor(contrast, factor):
    for base_index in range(32):
        baseline = p0_corpus.baseline_state(base_index)
        variant = p0_corpus.variant_state(baseline, contrast)
        names = ("content_position", "correct_symbol_index",
                 "label_alphabet_index")
        changed = [names[i] for i in range(3) if baseline[i] != variant[i]]
        assert changed == [factor], (contrast, base_index, baseline, variant)


def test_k6_holds_the_nuisance_state_byte_identical(corpus):
    for row in corpus["rows"]:
        if not row["contrast"].startswith("K6-"):
            continue
        first, second = row["members"]
        assert first["nuisance_state"] == second["nuisance_state"]
        assert first["displayed_labels"] == second["displayed_labels"]
        assert first["displayed_contents"] == second["displayed_contents"]


# ---------------------------------------------------------------------------
# The section 2 feasibility question: an independent implementation
# ---------------------------------------------------------------------------

def test_p0_renderer_agrees_byte_for_byte_with_the_committed_fixture_renderer(
        registry, corpus):
    fixture = _fixture_module()
    reference = fixture.Renderer(registry)
    compared = 0
    for row in corpus["rows"]:
        for member in row["members"]:
            expected = reference.render(
                row["profile"], member["rendering"], row["branch_id"],
                row["operation_parameters"],
                member["displayed_labels"], member["displayed_contents"])
            assert member["prompt"] == expected, row["base_item_id"]
            compared += 1
    assert compared == 70


def test_p0_renderer_rejects_an_unregistered_instruction(registry):
    renderer = p0_renderer.P0Renderer(registry)
    renderer.instructions[("S1", "R-base")] = "Answer with the correct letter.\n"
    with pytest.raises(p0_renderer.UnregisteredSurface):
        renderer.instruction("S1", "R-base")


def test_p0_renderer_rejects_an_unregistered_separator(registry):
    renderer = p0_renderer.P0Renderer(registry)
    renderer.separators["R-base"] = " - "
    with pytest.raises(p0_renderer.UnregisteredSurface):
        renderer.option_block("S1", "R-base", list("ABCD"), list("1234"))


def test_p0_renderer_rejects_an_unregistered_answer_cue(registry):
    renderer = p0_renderer.P0Renderer(registry)
    renderer.cue = "Answer: "
    with pytest.raises(p0_renderer.UnregisteredSurface):
        renderer.render("S2", "R-base", "K2/none/0", {"x": "3"})


def test_p0_renderer_rejects_an_unregistered_stem_branch(registry):
    renderer = p0_renderer.P0Renderer(registry)
    with pytest.raises(p0_renderer.UnregisteredSurface):
        renderer.stem("K9/none/0", {"x": "3"})


def test_p0_renderer_rejects_a_missing_substitution(registry):
    renderer = p0_renderer.P0Renderer(registry)
    with pytest.raises(p0_renderer.UnregisteredSurface):
        renderer.stem("K3/affine_mod10/1", {"x": "4"})


def test_p0_renderer_rejects_a_wrong_option_line_count(registry):
    renderer = p0_renderer.P0Renderer(registry)
    with pytest.raises(p0_renderer.UnregisteredSurface):
        renderer.option_block("S1", "R-base", list("ABC"), list("123"))


def test_p0_renderer_rejects_a_chat_wrapper_on_a_raw_completion_profile(registry):
    renderer = p0_renderer.P0Renderer(registry)
    stem = renderer.stem("K2/none/0", {"x": "3"})
    prompt = renderer.render("S1", "R-base", "K2/none/0", {"x": "3"},
                             list("ABCD"), list("1234"))
    assert renderer.validate_surface_class("S1", prompt, stem) is True
    for wrapped in ("<|im_start|>user\n" + prompt,
                    "System: be brief.\n" + prompt):
        with pytest.raises(p0_renderer.UnregisteredSurface):
            renderer.validate_surface_class("S1", wrapped, stem)
    for profile in ("S2", "S3"):
        bare = renderer.render(profile, "R-base", "K2/none/0", {"x": "3"})
        with pytest.raises(p0_renderer.UnregisteredSurface):
            renderer.validate_surface_class(
                profile, "<|im_start|>user\n" + bare, stem)


def test_s4_is_the_only_wrapper_bearing_profile(registry):
    renderer = p0_renderer.P0Renderer(registry)
    for profile in ("S1", "S2", "S3"):
        assert renderer.profiles[profile]["surface_class"] == "raw_completion"
        assert renderer.profiles[profile]["chat_wrapper"] is None
    assert renderer.profiles["S4"]["surface_class"] == "role_native_chat_wrapped"
    content = renderer.s4_message_content(
        "R-base", "K2/none/0", {"x": "3"}, list("ABCD"), list("1234"))
    assert content.endswith(registry["answer_cue"]["literal"])


def test_p0_renderer_rejects_prohibited_bytes(registry):
    renderer = p0_renderer.P0Renderer(registry)
    for bad in ("Answer:\r", "Answer:\t", "Answer:\u00a0", "Answer:\u4e2d"):
        with pytest.raises(p0_renderer.UnregisteredSurface):
            renderer.validate_bytes(bad)


def test_p0_renderer_rejects_r_sep_for_an_option_less_profile(registry):
    renderer = p0_renderer.P0Renderer(registry)
    for profile in ("S2", "S3"):
        assert renderer.rendering_applicable(profile, "R-sep") is False
        with pytest.raises(p0_renderer.UnregisteredSurface):
            renderer.render(profile, "R-sep", "K2/none/0", {"x": "3"})


# ---------------------------------------------------------------------------
# Corpus structure and the registered allocation
# ---------------------------------------------------------------------------

def test_corpus_reproduces_from_the_registry(rows, corpus):
    assert len(rows) == len(corpus["rows"])
    for built, committed in zip(rows, corpus["rows"]):
        assert built["base_item_id"] == committed["base_item_id"]
        for a, b in zip(built["members"], committed["members"]):
            assert a["prompt"] == b["prompt"]


def test_every_base_identity_is_unique_and_namespaced(corpus):
    identities = [row["base_item_id"] for row in corpus["rows"]]
    assert len(set(identities)) == len(identities)
    for identity in identities:
        assert identity.startswith("study3-p0-only/")
        assert len(identity.split("/")) == 3


def test_no_base_identity_crosses_a_contrast_cell(corpus):
    seen = {}
    for row in corpus["rows"]:
        cell = (row["profile"], row["contrast"])
        assert row["base_item_id"] not in seen or seen[row["base_item_id"]] == cell
        seen[row["base_item_id"]] = cell
    assert len(seen) == len(corpus["rows"])


def test_registered_profile_allocation(corpus):
    allocation = {}
    for row in corpus["rows"]:
        allocation.setdefault(row["profile"], set()).add(row["contrast"])
    assert allocation["S1"] == {
        "K5-P1", "K5-P2", "K5-P3", "K5-S1", "K5-S2", "K5-S3", "K5-A1",
        "K6-SEP", "K6-INSTR"}
    assert allocation["S2"] == {"K6-INSTR"}
    assert allocation["S3"] == {"K6-INSTR"}
    assert allocation["S4"] == {"K6-SEP", "K6-INSTR"}


def test_s4_uses_only_the_k2_tuple(corpus):
    for row in corpus["rows"]:
        if row["profile"] == "S4":
            assert row["tuple_class_id"] == "K2-none-0"


def test_k6_sep_is_structurally_absent_for_the_option_less_profiles(corpus):
    for row in corpus["rows"]:
        assert not (row["profile"] in ("S2", "S3") and row["contrast"] == "K6-SEP")


def test_s3_registers_no_new_surface(corpus):
    by_key = {(r["tuple_class_id"], r["profile"], r["contrast"]): r
              for r in corpus["rows"]}
    seen = 0
    for (tuple_class, profile, contrast), row in by_key.items():
        if profile != "S3":
            continue
        source = by_key[(tuple_class, "S2", contrast)]
        for a, b in zip(row["members"], source["members"]):
            assert a["prompt"] == b["prompt"]
            assert a["prompt_sha256"] == b["prompt_sha256"]
        seen += 1
    assert seen == 3


def test_every_pair_has_exactly_two_byte_distinct_variants(corpus):
    for row in corpus["rows"]:
        assert len(row["members"]) == 2
        first, second = row["members"]
        assert first["role_in_pair"] == "baseline"
        assert second["role_in_pair"] == "variant"
        assert first["prompt"] != second["prompt"], row["base_item_id"]


def test_a_byte_identical_applicable_pair_is_rejected(registry, protocol):
    original = p0_corpus.renderings_for

    def collapse(contrast):
        return ("R-base", "R-base")

    p0_corpus.renderings_for = collapse
    try:
        with pytest.raises(p0_corpus.CorpusDefect):
            p0_corpus.build_rows(registry, protocol)
    finally:
        p0_corpus.renderings_for = original


def test_k6_pairs_differ_only_in_their_registered_factor(corpus, registry):
    for row in corpus["rows"]:
        first, second = row["members"]
        if row["contrast"] == "K6-INSTR":
            base = registry["instructions"]["entries"]
            instructions = {
                (e["profile"], e["rendering"]): e["instruction"]
                for e in base if e["applicable"]}
            a = instructions[(row["profile"], "R-base")]
            b = instructions[(row["profile"], "R-instr")]
            assert first["prompt"].replace(a, b) == second["prompt"]
        elif row["contrast"] == "K6-SEP":
            assert first["prompt"].replace(": ", " = ") == second["prompt"]


def test_prompts_obey_the_registered_encoding_policy(corpus, registry):
    cue = registry["answer_cue"]["literal"]
    for row in corpus["rows"]:
        for member in row["members"]:
            prompt = member["prompt"]
            assert "\r" not in prompt
            assert "\t" not in prompt
            assert "\u00a0" not in prompt
            assert prompt.endswith(cue)
            assert prompt.encode("utf-8").decode("ascii")
            for line in prompt.split("\n"):
                assert line == line.rstrip(" ")


# ---------------------------------------------------------------------------
# Operation arithmetic
# ---------------------------------------------------------------------------

def _members_by_profile(corpus):
    counts = {}
    for row in corpus["rows"]:
        counts[row["profile"]] = counts.get(row["profile"], 0) + len(row["members"])
    return counts


def test_operation_arithmetic_reconciles_with_the_registered_caps(corpus):
    counts = _members_by_profile(corpus)
    roles = 3
    caps = p0_counters.CAPS
    assert (counts["S1"] + counts["S2"]) * roles \
        == caps["non_generative_prefill_evaluations"] == 180
    assert counts["S1"] * roles == caps["s1_scored_rows"] == 162
    assert counts["S2"] * roles == caps["s2_scored_rows"] == 18
    assert counts["S3"] * roles == caps["s3_cpu_only_reuse_scored_rows"] == 18
    assert counts["S4"] * roles == caps["s4_scored_generation_rows"] == 12
    assert counts["S4"] * roles == caps["s4_generation_calls"] == 12
    assert counts["S4"] * roles == caps["s4_prefill_evaluations"] == 12
    assert counts["S4"] * roles * 3 == caps["s4_incremental_decode_evaluations"] == 36
    total_rows = sum(counts.values()) * roles
    assert total_rows == caps["total_scored_rows"] == 210
    equivalents = ((counts["S1"] + counts["S2"]) * roles
                   + counts["S4"] * roles + counts["S4"] * roles * 3)
    assert equivalents == \
        caps["total_sequence_level_model_evaluation_equivalents"] == 228


def test_the_smoke_allocation_is_exact(corpus):
    roles = 3
    smoke = [r for r in corpus["rows"] if r["tuple_class_id"] == "K2-none-0"]
    prefill = sum(len(r["members"]) for r in smoke
                  if r["profile"] in ("S1", "S2")) * roles
    reuse = sum(len(r["members"]) for r in smoke if r["profile"] == "S3") * roles
    assert prefill == p0_counters.SMOKE_EXACT[
        "non_generative_prefill_evaluations"] == 60
    assert reuse == p0_counters.SMOKE_EXACT["s3_cpu_only_reuse_scored_rows"] == 6
    assert prefill + reuse == p0_counters.SMOKE_EXACT["total_scored_rows"] == 66
    assert p0_counters.SMOKE_EXACT["s4_generation_calls"] == 0


def test_the_bounded_extension_adds_exactly_120_prefill_evaluations(corpus):
    roles = 3
    extension = [r for r in corpus["rows"]
                 if r["tuple_class_id"] != "K2-none-0"
                 and r["profile"] in ("S1", "S2")]
    assert sum(len(r["members"]) for r in extension) * roles == 120


# ---------------------------------------------------------------------------
# Counter ontology: fail-closed behaviour
# ---------------------------------------------------------------------------

def test_all_counters_start_at_zero():
    counters = p0_counters.P0Counters()
    assert counters.all_zero()
    for name in p0_counters.ZERO_BEFORE_EXECUTION:
        assert counters[name] == 0


def test_a_counter_refuses_to_cross_its_registered_cap():
    counters = p0_counters.P0Counters()
    counters.add("non_generative_prefill_evaluations", 180)
    with pytest.raises(p0_counters.CapExceeded):
        counters.add("non_generative_prefill_evaluations", 1)
    assert counters["non_generative_prefill_evaluations"] == 180


def test_a_zero_cap_counter_cannot_advance_at_all():
    counters = p0_counters.P0Counters()
    for name in ("hosted_provider_inference_calls", "seeds_drawn",
                 "bank_rows_written", "positive_reference_operations"):
        with pytest.raises(p0_counters.CapExceeded):
            counters.add(name, 1)
        assert counters[name] == 0


def test_an_unregistered_counter_is_rejected():
    counters = p0_counters.P0Counters()
    with pytest.raises(p0_counters.CounterDefect):
        counters.add("prefill_evaluations_but_misspelled", 1)
    with pytest.raises(p0_counters.CounterDefect):
        counters["not_a_counter"]


def test_counters_may_not_be_reset_or_decrease():
    counters = p0_counters.P0Counters()
    counters.add("tokenizer_encoded_sequences", 100)
    previous = {"tokenizer_encoded_sequences": 250}
    with pytest.raises(p0_counters.CounterDefect):
        counters.merge_cumulative(previous)


def test_counter_totals_must_reconcile():
    counters = p0_counters.P0Counters()
    counters.add("s1_scored_rows", 5)
    with pytest.raises(p0_counters.CounterDefect):
        counters.reconcile_totals()


def test_a_runtime_batched_call_is_not_a_sequence_level_unit():
    ontology = p0_counters.ontology_document()
    assert "runtime_batched_forward_calls" in ontology[
        "uncapped_recorded_observations"]
    assert "runtime_batched_forward_calls" not in ontology["caps"]
    assert "never substituted for a sequence-level quantity" in \
        ontology["unit_semantics"]["runtime_batched_forward_calls"]


def test_the_counter_namespace_is_separate_from_formal_study3_counters():
    ontology = p0_counters.ontology_document()
    assert ontology["namespace"] == "study3-p0-pilot-counters"
    assert ontology["cumulative"] is True
    assert ontology["resettable"] is False


# ---------------------------------------------------------------------------
# The pinned S4 parser
# ---------------------------------------------------------------------------

def test_parser_reads_a_bare_displayed_label():
    result = p0_parser.parse_s4_completion(" B", list("ABCD"))
    assert result["value"] == "B"
    assert result["unparseable"] is False
    assert result["parser_id"] == p0_parser.PARSER_ID


def test_parser_is_deterministic():
    for _ in range(5):
        assert p0_parser.parse_s4_completion("C.", list("ABCD")) \
            == p0_parser.parse_s4_completion("C.", list("ABCD"))


@pytest.mark.parametrize("completion", [
    "", "   ", "the answer is B", "AB", "3", "Z", None, 42,
])
def test_unparseable_is_a_retained_first_class_outcome(completion):
    result = p0_parser.parse_s4_completion(completion, list("ABCD"))
    assert result["unparseable"] is True
    assert result["value"] is None
    assert result["reason"]


def test_an_unparseable_result_never_carries_a_value():
    with pytest.raises(AssertionError):
        p0_parser._result("A", True, "contradictory")


def test_parser_rejects_a_label_outside_the_displayed_set():
    result = p0_parser.parse_s4_completion("W", list("ABCD"))
    assert result["unparseable"] is True


def test_parser_handles_the_second_registered_alphabet():
    result = p0_parser.parse_s4_completion(" Y", list("WXYZ"))
    assert result["value"] == "Y"
    assert result["unparseable"] is False


def test_s2_parser_reads_only_a_bare_mod10_residue():
    assert p0_parser.parse_s2_completion(" 7")["value"] == "7"
    assert p0_parser.parse_s2_completion("seven")["unparseable"] is True


# ---------------------------------------------------------------------------
# Fail-closed corpus construction
# ---------------------------------------------------------------------------

def test_an_unregistered_contrast_is_rejected(registry, protocol):
    with pytest.raises(p0_corpus.CorpusDefect):
        p0_corpus.contrast_applicability(registry, protocol, "S1", "K7-NEW")


def test_a_not_applicable_cell_is_reported_as_absence_not_as_a_pass(
        registry, protocol):
    for profile in ("S2", "S3"):
        assert p0_corpus.contrast_applicability(
            registry, protocol, profile, "K6-SEP") == "not_applicable"
        assert p0_corpus.contrast_applicability(
            registry, protocol, profile, "K5-P1") == "not_applicable"


def test_k5_is_applicable_only_to_the_label_bearing_profiles(registry, protocol):
    for contrast in p0_corpus.K5_CONTRASTS:
        for profile in ("S1", "S4"):
            assert p0_corpus.contrast_applicability(
                registry, protocol, profile, contrast) == "applicable"
        for profile in ("S2", "S3"):
            assert p0_corpus.contrast_applicability(
                registry, protocol, profile, contrast) == "not_applicable"


def test_a_validity_predicate_failure_stops_construction(registry):
    with pytest.raises(p0_corpus.CorpusDefect):
        p0_corpus.check_validity(
            registry, "3", ["3", "3", "1", "2"], list("ABCD"), 0, 0)
    with pytest.raises(p0_corpus.CorpusDefect):
        p0_corpus.check_validity(
            registry, "3", ["1", "2", "4", "5"], list("ABCD"), 0, 0)


def test_an_identity_permutation_is_rejected():
    original = dict(p0_corpus.PERMUTATION_IMAGE)
    p0_corpus.PERMUTATION_IMAGE["K3-permutation_chain-1"] = list(range(10))
    try:
        with pytest.raises(p0_corpus.CorpusDefect):
            p0_corpus.ground_truth("K3-permutation_chain-1")
    finally:
        p0_corpus.PERMUTATION_IMAGE.clear()
        p0_corpus.PERMUTATION_IMAGE.update(original)


def test_a_non_permutation_image_vector_is_rejected():
    original = dict(p0_corpus.PERMUTATION_IMAGE)
    p0_corpus.PERMUTATION_IMAGE["K3-permutation_chain-1"] = [1] * 10
    try:
        with pytest.raises(p0_corpus.CorpusDefect):
            p0_corpus.ground_truth("K3-permutation_chain-1")
    finally:
        p0_corpus.PERMUTATION_IMAGE.clear()
        p0_corpus.PERMUTATION_IMAGE.update(original)


# ---------------------------------------------------------------------------
# Permanent exclusion of the pilot namespace
# ---------------------------------------------------------------------------

def test_the_exclusion_is_machine_readable(corpus):
    assert corpus["namespace"] == "study3-p0-only"
    assert set(corpus["permanently_excluded_from"]) == {
        "development_bank", "confirmation_bank", "p3q_bank",
        "external_validity_bank"}
    assert "may not be relabelled or promoted later" in corpus["exclusion_rule"]


def test_the_pilot_namespace_appears_in_no_other_committed_artifact():
    """No bank, ledger or protocol object may reference a P0 identity."""
    forbidden = os.path.join(REPO_ROOT, "paper", "evidence_ledger.csv")
    with open(forbidden, "rb") as handle:
        assert b"study3-p0-only" not in handle.read()
    for name in ("interface_calibration_protocol_draft.json",
                 "interface_calibration_rendering_registry_v0_5.json"):
        path = os.path.join(REPO_ROOT, "studies", "study3", "protocol", name)
        with open(path, "rb") as handle:
            assert b"study3-p0-only" not in handle.read()


def test_p0_writes_no_seed_and_no_bank_row(corpus):
    assert corpus["seed_policy"].startswith("P0 uses no random seed")
    assert "never Study 3 evidence" in corpus["evidence_status"]


# ---------------------------------------------------------------------------
# Legal status recorded by the P0 protocol document
# ---------------------------------------------------------------------------

def test_formal_execution_remains_unauthorized(p0_protocol_document):
    legal = p0_protocol_document["legal_status"]
    assert legal["formal_execution_authorized"] is False
    assert legal["draft_v0_5_frozen"] is False
    assert legal["draft_v0_5_reviewed"] is False
    assert legal["od2_status"] == "unresolved"
    assert legal["ur22_status"] == "unresolved"
    assert legal["interface_selected"] is None
    assert legal["evidence_ledger_last_row"] == "EV-0016"


def test_rp_is_excluded(p0_protocol_document):
    assert p0_protocol_document["rp_excluded"] is True
    roles = [role["role"] for role in p0_protocol_document["roles"]]
    assert roles == ["RT", "RL", "RI"]
    assert "RP" not in roles


def test_registered_role_revisions_are_immutable_forty_hex(p0_protocol_document):
    for role in p0_protocol_document["roles"]:
        revision = role["immutable_revision"]
        assert len(revision) == 40
        assert all(c in "0123456789abcdef" for c in revision)


def test_trust_remote_code_remains_false(p0_protocol_document):
    route = p0_protocol_document["execution_route"]
    assert route["trust_remote_code"] is False
    assert "no silent trust-policy expansion" in route["trust_remote_code_policy"]


def test_every_terminal_disposition_is_registered(p0_protocol_document):
    terminals = set(p0_protocol_document["state_machine"]["terminal_dispositions"])
    assert terminals == {
        "STUDY3_P0_COMPLETE_MECHANICALLY_FEASIBLE",
        "STUDY3_P0_COMPLETE_MECHANICALLY_FEASIBLE_EMPIRICALLY_LOW_INFORMATION",
        "STUDY3_P0_STOPPED_ON_TOKENIZER_OR_RENDERER_DEFECT",
        "STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE",
        "STUDY3_P0_STOPPED_ON_MODEL_SMOKE_MECHANICAL_FAILURE",
        "STUDY3_P0_INCONCLUSIVE_INFRASTRUCTURE_OR_TRANSPORT_FAILURE",
        "STUDY3_P0_BLOCKED_ON_AUTHORITY_OR_REPOSITORY_INTEGRITY",
    }


def test_every_transition_declares_a_fail_closed_target(p0_protocol_document):
    for transition in p0_protocol_document["state_machine"]["transitions"]:
        assert transition["fail_closed_to"]


def test_the_prohibitions_are_recorded(p0_protocol_document):
    prohibitions = " ".join(p0_protocol_document["prohibitions"])
    for phrase in ("seed or bank", "evidence_ledger.csv", "quantization",
                   "hosted-provider inference", "OD2", "activation extraction",
                   "413/214/448"):
        assert phrase in prohibitions


def test_the_authorized_write_allowlist_is_recorded(p0_protocol_document):
    allowlist = set(p0_protocol_document["authorized_write_paths"])
    assert "studies/study3/pilot/p0/" in allowlist
    assert "tests/test_study3_p0_feasibility_pilot.py" in allowlist
    assert "paper/evidence_ledger.csv" not in allowlist


def test_the_byte_protected_list_covers_the_binding_inputs(p0_protocol_document):
    protected = set(p0_protocol_document["byte_protected_paths"])
    for path in (
            "studies/study3/protocol/interface_calibration_protocol_draft.json",
            "studies/study3/protocol/"
            "interface_calibration_rendering_registry_v0_5.json",
            "studies/study3/design_receipt_v0_5.json",
            "tests/test_study3_rendering_registry_v0_5.py",
            "paper/evidence_ledger.csv"):
        assert path in protected


def test_the_legal_successor_is_not_another_pilot(p0_protocol_document):
    successor = p0_protocol_document["legal_successor"]
    assert "not another pilot" in successor
    assert "not immediate formal execution" in successor
    assert "independent methods review" in successor


# ---------------------------------------------------------------------------
# The tokenizer gate, exercised without constructing a tokenizer
# ---------------------------------------------------------------------------

def test_the_fixture_census_covers_every_registered_nuisance_state():
    import p0_tokenizer_gate

    states = p0_tokenizer_gate.nuisance_states()
    assert len(states) == 32
    assert len(set(states)) == 32


def test_the_fixture_census_records_structural_absence(registry, protocol):
    import p0_tokenizer_gate

    rows = p0_tokenizer_gate.fixture_census(registry, protocol)
    absent = [r for r in rows if r["applicability"] == "not_applicable"]
    assert absent
    for row in absent:
        assert row["profile"] in ("S2", "S3")
        assert row["contrast"] == "K6-SEP"
        assert row["members"] == []
        assert row["structural_absence"] is True


def test_the_planned_census_stays_under_the_registered_encode_cap(
        registry, protocol):
    import p0_tokenizer_gate

    rows = p0_tokenizer_gate.fixture_census(registry, protocol)
    corpus_rows = p0_corpus.build_rows(registry, protocol)
    planned = sum(len(r.get("members", [])) for r in rows + corpus_rows) * 3
    planned += 3 * (8 + 10)
    assert planned <= p0_counters.CAPS["tokenizer_encoded_sequences"]


def test_a_missing_applicability_row_stops_the_census(registry, protocol):
    import p0_tokenizer_gate

    trimmed = json.loads(json.dumps(registry))
    trimmed["applicability_table"]["rows"] = [
        row for row in trimmed["applicability_table"]["rows"]
        if not (row["profile"] == "S1" and row["contrast"] == "K6-SEP")]
    with pytest.raises(p0_tokenizer_gate.TokenizerGateDefect):
        p0_tokenizer_gate.fixture_census(trimmed, protocol)


def test_a_byte_distinct_pair_with_identical_token_ids_is_marked_ineligible():
    import p0_tokenizer_gate

    records = [{
        "role": "RT", "profile": "S1", "contrast": "K6-INSTR",
        "row_id": "p0-000", "structural_absence": False,
        "pair_bytes_distinct": True, "pair_token_ids_distinct": False,
    }]
    matrix = p0_tokenizer_gate.evaluate_eligibility(records, {})
    assert matrix[0]["status"] == p0_tokenizer_gate.INELIGIBLE
    assert matrix[0]["collision_rows"] == ["p0-000"]


def test_ineligibility_is_never_an_executable_contrast():
    import p0_tokenizer_gate

    matrix = [
        {"role": "RT", "profile": "S1", "contrast": "K6-INSTR",
         "status": p0_tokenizer_gate.INELIGIBLE, "reasons": [],
         "collision_rows": []},
        {"role": "RL", "profile": "S1", "contrast": "K6-INSTR",
         "status": "eligible", "reasons": [], "collision_rows": []},
    ]
    executable = p0_tokenizer_gate.executable_contrast_per_role(matrix)
    assert "RT" not in executable
    assert executable["RL"] == ["S1/K6-INSTR"]


def test_s4_alone_does_not_keep_a_role_executable():
    import p0_tokenizer_gate

    matrix = [{"role": "RT", "profile": "S4", "contrast": "K6-INSTR",
               "status": "eligible", "reasons": [], "collision_rows": []}]
    assert p0_tokenizer_gate.executable_contrast_per_role(matrix) == {}


def test_an_s2_s3_parity_break_is_detected():
    import p0_tokenizer_gate

    records = [
        {"role": "RT", "profile": "S2", "contrast": "K6-INSTR",
         "tuple_class_id": "K2-none-0", "branch_id": None, "row_id": "s2",
         "structural_absence": False,
         "members": [{"prompt_sha256": "a", "token_ids": [1]},
                     {"prompt_sha256": "b", "token_ids": [2]}]},
        {"role": "RT", "profile": "S3", "contrast": "K6-INSTR",
         "tuple_class_id": "K2-none-0", "branch_id": None, "row_id": "s3",
         "structural_absence": False,
         "members": [{"prompt_sha256": "a", "token_ids": [1]},
                     {"prompt_sha256": "b", "token_ids": [99]}]},
    ]
    assert p0_tokenizer_gate.check_s2_s3_parity(records)


def test_an_instantiated_s2_k6_sep_row_is_detected():
    import p0_tokenizer_gate

    records = [{"role": "RT", "profile": "S2", "contrast": "K6-SEP",
                "row_id": "bad", "structural_absence": False, "members": []}]
    assert p0_tokenizer_gate.check_structural_absence(records) == ["bad"]


# ---------------------------------------------------------------------------
# Summarization stays inside the claim ceiling
# ---------------------------------------------------------------------------

def test_the_summarizer_computes_no_forbidden_quantity():
    import p0_summarize

    source = open(os.path.join(P0_DIR, "p0_summarize.py"), "rb").read().decode()
    for forbidden in ("scipy", "statsmodels", "ttest", "chisquare",
                      "binomtest", "norm.cdf", "p_value ="):
        assert forbidden not in source
    summary = p0_summarize.summarize({"records": [], "counters": {}})
    assert "no p-value" in summary["claim_boundary"]


def test_the_summarizer_reports_zero_discordance_as_low_information():
    import p0_summarize

    records = [
        {"role": "RT", "profile": "S1", "contrast": "K6-INSTR",
         "tuple_class_id": "K2-none-0", "rendering": "R-base",
         "row_id": "p0-000", "role_in_pair": "baseline", "correct": True,
         "prediction": "A", "token_count": 20},
        {"role": "RT", "profile": "S1", "contrast": "K6-INSTR",
         "tuple_class_id": "K2-none-0", "rendering": "R-instr",
         "row_id": "p0-000", "role_in_pair": "variant", "correct": True,
         "prediction": "A", "token_count": 21},
    ]
    summary = p0_summarize.summarize({"records": records, "counters": {}})
    assert summary["pairwise"]["all_roles"]["discordant_pairs"] == 0
    assert summary["empirical_information"] == \
        "low_information_no_observed_discordance"
    assert summary["pairwise"]["all_roles"]["joint_correct_pairs"] == 1


# ---------------------------------------------------------------------------
# The model pilot module never performs an operation at import time
# ---------------------------------------------------------------------------

def test_the_model_pilot_declares_the_registered_inference_behaviour():
    source = open(os.path.join(P0_DIR, "p0_model_pilot.py"), "rb").read().decode()
    assert "do_sample=False" in source
    assert "max_new_tokens=MAX_NEW_TOKENS" in source
    assert "torch.inference_mode()" in source
    assert "trust_remote_code=False" in source
    assert "temperature" not in source.split("def _apply_role_native_wrapper")[0] \
        .replace("no sampling temperature", "")
    for forbidden in ("output_hidden_states", "output_attentions",
                      "register_forward_hook", "requires_grad_(True)",
                      "load_in_8bit", "load_in_4bit", "quantization_config"):
        assert forbidden not in source


def test_the_model_pilot_caps_generation_at_four_new_tokens():
    import p0_model_pilot

    assert p0_model_pilot.MAX_NEW_TOKENS == 4


def test_the_smoke_gate_rejects_a_short_run():
    import p0_model_pilot

    counters = p0_counters.P0Counters()
    failures = p0_model_pilot.smoke_gate([], counters)
    assert failures
    assert any("scored rows" in failure for failure in failures)


def test_the_container_definition_is_digest_pinned():
    path = os.path.join(P0_DIR, "container", "Dockerfile.study3-p0")
    with open(path, "rb") as handle:
        text = handle.read().decode("utf-8")
    assert "@sha256:" in text.split("\n")[7] or "@sha256:" in text
    assert AUTHORITY_SHA256 in text
    assert "trust-remote-code=\"false\"" in text


def test_the_frozen_dependencies_are_exactly_pinned():
    path = os.path.join(P0_DIR, "container", "requirements-study3-p0.txt")
    with open(path, "rb") as handle:
        lines = handle.read().decode("utf-8").splitlines()
    requirements = [line for line in lines
                    if line.strip() and not line.startswith("#")]
    assert requirements
    for requirement in requirements:
        assert "==" in requirement, requirement
        assert ">" not in requirement and "<" not in requirement, requirement
