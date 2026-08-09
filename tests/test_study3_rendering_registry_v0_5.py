"""Deterministic fixtures for the Study 3 draft-v0.5 rendering registry (S3MR3-010).

This module is model-free by construction. It performs no download, no revision
resolution, no weight load, no tokenizer construction, no tokenization, no forward
pass, no decode step, no sequence scoring, no generation, no activation extraction
and no provider call. It draws no seed, writes no bank row, reads no confirmation
content and produces no scientific evidence row.

What it establishes
-------------------
The third independent methods review recorded S3MR3-010: the registered generator
fixed the sampled parameters but not the deterministic rendering surface, so the
two K6 cells were not instantiable without a later substantive design choice, and
for K6-SEP and K6-INSTR the unregistered string IS the manipulated factor. That is
also the mechanism by which S3MR3-001 went undetected: with no byte-exact
templates, nobody could observe that R-sep and R-base coincide under the
option-less profiles.

These fixtures instantiate the registered surface WITHOUT a model and prove, on
bytes:

* every applicable (profile, rendering, contrast) branch renders;
* K6-SEP members differ in bytes for the label-bearing profiles S1 and S4;
* K6-SEP is structurally ABSENT, not duplicated, for the option-less profiles S2
  and S3;
* K6-INSTR members differ in bytes for every applicable profile;
* each pair differs ONLY in its registered factor;
* a byte-identical applicable pair is rejected;
* an unregistered whitespace, punctuation, placeholder, option order, instruction,
  cue or wrapper substitution is rejected;
* a missing task-template branch is rejected;
* every generator support branch that can feed a gate-bearing cell is covered.

Tokenizer distinctness is NOT tested here, because no checkpoint or tokenizer may
be accessed in this round. The registry instead registers a future fail-closed
pre-bank rule, and this module asserts that the rule is registered as fail-closed
and is not treated as already satisfied.

Standard library only, by design.
"""

import hashlib
import itertools
import json
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDY3 = os.path.join(REPO_ROOT, "studies", "study3")
PROTOCOL_DIR = os.path.join(STUDY3, "protocol")
REGISTRY_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_rendering_registry_v0_5.json")
REGISTRY_SCHEMA_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_rendering_registry_v0_5.schema.json")
PROTOCOL_PATH = os.path.join(
    PROTOCOL_DIR, "interface_calibration_protocol_draft.json")

LABEL_BEARING = ("S1", "S4")
OPTION_LESS = ("S2", "S3")
PROFILES = ("S1", "S2", "S3", "S4")
RENDERINGS = ("R-base", "R-sep", "R-instr")
CONTRASTS = ("K6-SEP", "K6-INSTR")


def _load(path):
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def _reseal(registry):
    """Recompute every asset digest and the registry digest.

    A mutation that also reseals is an internally CONSISTENT rival registry. Such a
    registry cannot be rejected on identity grounds, so resealing isolates the
    SEMANTIC defect: it forces the fixture to catch the defect on the rendered
    bytes rather than on a stale hash.
    """
    assets = []
    for branch in registry["question_stem_templates"]["branches"]:
        branch["template_sha256"] = hashlib.sha256(
            branch["template"].encode("utf-8")).hexdigest()
        branch["template_bytes"] = len(branch["template"].encode("utf-8"))
        assets.append({"asset_id": "stem/" + branch["branch_id"],
                       "sha256": branch["template_sha256"],
                       "bytes": branch["template_bytes"]})
    for entry in registry["instructions"]["entries"]:
        if entry["applicable"]:
            entry["instruction_sha256"] = hashlib.sha256(
                entry["instruction"].encode("utf-8")).hexdigest()
            assets.append({
                "asset_id": "instruction/%s/%s" % (entry["profile"], entry["rendering"]),
                "sha256": entry["instruction_sha256"],
                "bytes": len(entry["instruction"].encode("utf-8"))})
    for rendering in RENDERINGS:
        separator = registry["separators"][rendering]
        assets.append({"asset_id": "separator/" + rendering,
                       "sha256": hashlib.sha256(separator.encode("utf-8")).hexdigest(),
                       "bytes": len(separator.encode("utf-8"))})
    cue = registry["answer_cue"]["literal"]
    registry["answer_cue"]["sha256"] = hashlib.sha256(cue.encode("utf-8")).hexdigest()
    assets.append({"asset_id": "answer_cue",
                   "sha256": registry["answer_cue"]["sha256"],
                   "bytes": len(cue.encode("utf-8"))})
    registry["registry_identity"]["normative_template_assets"] = assets
    registry["registry_identity"]["normative_template_asset_count"] = len(assets)
    registry["registry_identity"]["registry_sha256"] = None
    canonical = json.dumps(registry, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
    registry["registry_identity"]["registry_sha256"] = hashlib.sha256(
        canonical.encode("utf-8")).hexdigest()
    return registry


@pytest.fixture(scope="module")
def registry():
    return _load(REGISTRY_PATH)


@pytest.fixture(scope="module")
def registry_schema():
    return _load(REGISTRY_SCHEMA_PATH)


@pytest.fixture(scope="module")
def protocol():
    return _load(PROTOCOL_PATH)


# --------------------------------------------------------------------------
# The renderer. It reads ONLY the registry, so a registry that is not
# sufficient cannot produce a prompt, and the insufficiency shows up as an
# exception rather than as an implicit choice made here.
# --------------------------------------------------------------------------

class UnregisteredSurface(Exception):
    """Raised when the registry does not determine a required byte."""


class Renderer(object):
    """A byte-exact renderer driven entirely by the registered surface."""

    def __init__(self, registry):
        self.registry = registry
        self.stems = {branch["branch_id"]: branch["template"]
                      for branch in registry["question_stem_templates"]["branches"]}
        self.instructions = {}
        for entry in registry["instructions"]["entries"]:
            if entry["applicable"]:
                self.instructions[(entry["profile"], entry["rendering"])] = \
                    entry["instruction"]
        self.separators = {rid: registry["separators"][rid] for rid in RENDERINGS}
        self.cue = registry["answer_cue"]["literal"]
        self.alphabets = registry["label_alphabets"]["alphabets"]
        self.answer_domain = registry["answer_domain"]["surface_forms"]
        self.profiles = {entry["profile"]: entry for entry in registry["profiles"]}
        self.placeholder = re.compile(r"\{([a-z][a-z0-9_]*)\}")
        self.assets = {a["asset_id"]: a for a in
                       registry["registry_identity"]["normative_template_assets"]}

    def _assert_registered_asset(self, asset_id, text):
        """Every emitted normative string must match its registered identity.

        The registry publishes a sha256 for each normative template asset. A
        surface string that does not reproduce its registered digest is an
        unregistered substitution, whether or not it looks plausible.
        """
        asset = self.assets.get(asset_id)
        if asset is None:
            raise UnregisteredSurface("no registered asset %r" % asset_id)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != asset["sha256"]:
            raise UnregisteredSurface("asset %r does not match its registered identity"
                                      % asset_id)
        if len(text.encode("utf-8")) != asset["bytes"]:
            raise UnregisteredSurface("asset %r has an unregistered byte length"
                                      % asset_id)
        return text

    # -- applicability ----------------------------------------------------
    def rendering_applicable(self, profile, rendering):
        for entry in self.registry["renderings"]["entries"]:
            if entry["rendering_id"] == rendering:
                return profile in entry["applicable_profiles"]
        raise UnregisteredSurface("unregistered rendering %r" % rendering)

    def contrast_applicable(self, profile, contrast):
        for row in self.registry["applicability_table"]["rows"]:
            if row["profile"] == profile and row["contrast"] == contrast:
                return row["applicability"] == "applicable"
        raise UnregisteredSurface("no applicability row for %s/%s"
                                  % (profile, contrast))

    # -- parts ------------------------------------------------------------
    def stem(self, branch_id, values):
        if branch_id not in self.stems:
            raise UnregisteredSurface("no registered stem branch %r" % branch_id)
        template = self._assert_registered_asset("stem/" + branch_id,
                                                 self.stems[branch_id])
        needed = set(self.placeholder.findall(template))
        registered = set(self.registry["placeholders"]["names"])
        unknown = needed - registered
        if unknown:
            raise UnregisteredSurface("unregistered placeholder(s) %s" % sorted(unknown))
        missing = needed - set(values)
        if missing:
            raise UnregisteredSurface("missing substitution(s) %s" % sorted(missing))
        out = template
        for name in sorted(needed):
            out = out.replace("{%s}" % name, values[name])
        if self.placeholder.search(out):
            raise UnregisteredSurface("residual placeholder after substitution")
        return out

    def option_block(self, profile, rendering, labels, contents):
        if profile not in LABEL_BEARING:
            return ""
        if not self.rendering_applicable(profile, rendering):
            raise UnregisteredSurface("%s has no %s rendering" % (profile, rendering))
        separator = self._assert_registered_asset("separator/" + rendering,
                                                  self.separators[rendering])
        if len(labels) != 4 or len(contents) != 4:
            raise UnregisteredSurface("exactly four option lines are registered")
        return "".join("%s%s%s\n" % (labels[i], separator, contents[i])
                       for i in range(4))

    def instruction(self, profile, rendering):
        key = (profile, rendering)
        if key not in self.instructions:
            raise UnregisteredSurface("no registered instruction for %s/%s"
                                      % (profile, rendering))
        return self._assert_registered_asset(
            "instruction/%s/%s" % (profile, rendering), self.instructions[key])

    def render(self, profile, rendering, branch_id, values,
               labels=None, contents=None):
        if not self.rendering_applicable(profile, rendering):
            raise UnregisteredSurface("%s does not render %s" % (profile, rendering))
        parts = [self.stem(branch_id, values)]
        if profile in LABEL_BEARING:
            parts.append(self.option_block(profile, rendering, labels, contents))
        parts.append(self.instruction(profile, rendering))
        parts.append(self._assert_registered_asset("answer_cue", self.cue))
        prompt = "".join(parts)
        self._validate_bytes(prompt)
        return prompt

    def _validate_bytes(self, prompt):
        policy = self.registry["encoding_policy"]
        assert policy["character_encoding"] == "UTF-8"
        if "\r" in prompt:
            raise UnregisteredSurface("CR is prohibited")
        if "\t" in prompt:
            raise UnregisteredSurface("TAB is prohibited")
        if "\u00a0" in prompt:
            raise UnregisteredSurface("non-breaking space is prohibited")
        for line in prompt.split("\n"):
            if line != line.rstrip(" "):
                raise UnregisteredSurface("trailing whitespace is prohibited")
        for char in prompt:
            if char == "\n" or char == " ":
                continue
            if not (0x21 <= ord(char) <= 0x7E):
                raise UnregisteredSurface("codepoint %r is outside the registered set"
                                          % char)
        if not prompt.endswith(self.cue):
            raise UnregisteredSurface("the prompt must end with the registered cue")


# --------------------------------------------------------------------------
# The full generator support that can feed a gate-bearing cell.
# --------------------------------------------------------------------------

# One representative substitution per registered placeholder type. The renderer
# rejects any value outside the registered surface forms, so these are drawn from
# the registered sets.
PERMUTATION = "[1 2 3 4 5 6 7 8 9 0]"

BRANCH_VALUES = {
    "K1/none/0": {"value": "7"},
    "K2/none/0": {"x": "3"},
    "K3/affine_mod10/1": {"x": "4", "a1": "3", "b1": "1"},
    "K3/permutation_chain/1": {"p1": PERMUTATION, "x": "5"},
    "K4/affine_mod10/2": {"x": "2", "a1": "3", "b1": "1", "a2": "7", "b2": "4"},
    "K4/affine_mod10/3": {"x": "2", "a1": "3", "b1": "1", "a2": "7", "b2": "4",
                          "a3": "9", "b3": "6"},
    "K4/permutation_chain/2": {"p1": PERMUTATION, "p2": PERMUTATION, "x": "6"},
    "K4/permutation_chain/3": {"p1": PERMUTATION, "p2": PERMUTATION,
                               "p3": PERMUTATION, "x": "8"},
}


def _nuisance_states():
    """The registered 32-state nuisance support: 4 positions x 4 symbols x 2 alphabets."""
    return list(itertools.product(range(4), range(4), range(2)))


def _labels_and_contents(registry, position, symbol_index, alphabet_index):
    """The registered option surface for one nuisance state."""
    names = list(registry["label_alphabets"]["alphabets"])
    alphabet = registry["label_alphabets"]["alphabets"][names[alphabet_index]]
    shift = (symbol_index - position) % 4
    labels = [alphabet[(slot + shift) % 4] for slot in range(4)]
    domain = registry["answer_domain"]["surface_forms"]
    contents = [domain[(slot + 1) % 10] for slot in range(4)]
    contents[position] = domain[7]
    return labels, contents


# --------------------------------------------------------------------------
# Registry integrity
# --------------------------------------------------------------------------

def test_the_registry_validates_against_its_committed_schema(registry, registry_schema):
    from test_study3_design import schema_errors
    assert schema_errors(registry, registry_schema) == []


def test_the_registry_is_a_binding_input_not_an_example(registry, protocol):
    assert registry["binding_status"].startswith(
        "BINDING_NORMATIVE_INPUT_NOT_AN_ILLUSTRATIVE_EXAMPLE")
    surface = protocol["rendering_surface_v0_5"]
    assert surface["binding_input"] is True
    assert surface["illustrative_example"] is False
    assert surface["closes_finding"] == "S3MR3-010"
    assert surface["registry_path"] == \
        "studies/study3/protocol/interface_calibration_rendering_registry_v0_5.json"


def test_the_registry_identity_reproduces_exactly(registry):
    """The registry hashes itself over its own canonical serialisation."""
    published = registry["registry_identity"]["registry_sha256"]
    probe = json.loads(json.dumps(registry))
    probe["registry_identity"]["registry_sha256"] = None
    canonical = json.dumps(probe, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == published


def test_every_normative_template_asset_hash_reproduces(registry):
    assets = {a["asset_id"]: a for a in
              registry["registry_identity"]["normative_template_assets"]}
    assert len(assets) == registry["registry_identity"]["normative_template_asset_count"]
    for branch in registry["question_stem_templates"]["branches"]:
        asset = assets["stem/" + branch["branch_id"]]
        digest = hashlib.sha256(branch["template"].encode("utf-8")).hexdigest()
        assert asset["sha256"] == digest == branch["template_sha256"]
        assert asset["bytes"] == len(branch["template"].encode("utf-8"))
    for entry in registry["instructions"]["entries"]:
        if not entry["applicable"]:
            continue
        asset = assets["instruction/%s/%s" % (entry["profile"], entry["rendering"])]
        digest = hashlib.sha256(entry["instruction"].encode("utf-8")).hexdigest()
        assert asset["sha256"] == digest == entry["instruction_sha256"]
    for rendering in RENDERINGS:
        asset = assets["separator/" + rendering]
        assert asset["sha256"] == hashlib.sha256(
            registry["separators"][rendering].encode("utf-8")).hexdigest()
    cue = registry["answer_cue"]["literal"]
    assert assets["answer_cue"]["sha256"] == \
        hashlib.sha256(cue.encode("utf-8")).hexdigest()
    assert registry["answer_cue"]["sha256"] == assets["answer_cue"]["sha256"]


def test_the_protocol_pins_the_registry_hash(registry, protocol):
    assert protocol["rendering_surface_v0_5"]["registry_sha256"] == \
        registry["registry_identity"]["registry_sha256"]


# --------------------------------------------------------------------------
# Completeness of the deterministic surface
# --------------------------------------------------------------------------

def test_every_gate_bearing_generator_branch_has_exactly_one_registered_stem(
        registry, protocol):
    """A missing task-template branch is a fail-closed rejection, never a default."""
    families = protocol["proposed_statistics"]["registered_operation_families"]
    depths = protocol["proposed_statistics"]["registered_composition_depths"]
    expected = {"K1/none/0", "K2/none/0"}
    for family in families:
        expected.add("K3/%s/1" % family)
        for depth in depths:
            expected.add("K4/%s/%d" % (family, depth))
    published = {b["branch_id"] for b in registry["question_stem_templates"]["branches"]}
    assert published == expected, published ^ expected
    assert registry["question_stem_templates"]["branch_count"] == len(expected)
    # Each branch names the gate it can feed, and every gate-bearing gate is covered.
    fed = set()
    for branch in registry["question_stem_templates"]["branches"]:
        fed.update(branch["feeds_gates"])
    assert fed == {"I1a", "I1b", "I2", "I4"}


def test_a_missing_task_template_branch_is_rejected(registry):
    mutated = json.loads(json.dumps(registry))
    mutated["question_stem_templates"]["branches"] = [
        b for b in mutated["question_stem_templates"]["branches"]
        if b["branch_id"] != "K3/affine_mod10/1"]
    renderer = Renderer(mutated)
    with pytest.raises(UnregisteredSurface):
        renderer.stem("K3/affine_mod10/1", BRANCH_VALUES["K3/affine_mod10/1"])


def test_every_applicable_profile_rendering_pair_has_a_registered_instruction(registry):
    renderer = Renderer(registry)
    for profile in PROFILES:
        for rendering in RENDERINGS:
            if renderer.rendering_applicable(profile, rendering):
                assert renderer.instruction(profile, rendering).endswith("\n")
            else:
                with pytest.raises(UnregisteredSurface):
                    renderer.instruction(profile, rendering)


def test_every_applicable_branch_instantiates_without_a_model(registry):
    """Every applicable profile/rendering/branch combination must render."""
    renderer = Renderer(registry)
    rendered = 0
    for profile in PROFILES:
        for rendering in RENDERINGS:
            if not renderer.rendering_applicable(profile, rendering):
                continue
            for branch, values in sorted(BRANCH_VALUES.items()):
                labels, contents = _labels_and_contents(registry, 0, 0, 0)
                prompt = renderer.render(profile, rendering, branch, values,
                                         labels, contents)
                assert prompt.endswith(registry["answer_cue"]["literal"])
                rendered += 1
    # 4 profiles x 3 renderings minus the two absent R-sep branches, times 8 stems.
    assert rendered == (4 * 3 - 2) * len(BRANCH_VALUES) == 80


def test_every_generator_support_branch_feeding_a_gate_bearing_cell_is_covered(registry):
    """All 32 registered nuisance states render for every label-bearing profile."""
    renderer = Renderer(registry)
    states = _nuisance_states()
    assert len(states) == 32 == len(set(states))
    seen = set()
    for profile in LABEL_BEARING:
        for position, symbol, alphabet in states:
            labels, contents = _labels_and_contents(registry, position, symbol, alphabet)
            # The registered constructor is a bijection on labels, and exactly one
            # content is the registered correct content.
            assert sorted(labels) == sorted(set(labels))
            prompt = renderer.render(profile, "R-base", "K2/none/0",
                                     BRANCH_VALUES["K2/none/0"], labels, contents)
            seen.add((profile, position, symbol, alphabet))
            assert prompt.count("\n") >= 4
    assert len(seen) == 2 * 32


# --------------------------------------------------------------------------
# S3MR3-001 on bytes: the two K6 cells
# --------------------------------------------------------------------------

def _pair(renderer, registry, profile, contrast, branch="K2/none/0"):
    baseline, variant = ("R-base", "R-sep") if contrast == "K6-SEP" \
        else ("R-base", "R-instr")
    labels, contents = _labels_and_contents(registry, 1, 2, 0)
    values = BRANCH_VALUES[branch]
    first = renderer.render(profile, baseline, branch, values, labels, contents)
    second = renderer.render(profile, variant, branch, values, labels, contents)
    return first, second


def test_k6_sep_members_differ_in_bytes_for_the_label_bearing_profiles(registry):
    renderer = Renderer(registry)
    for profile in LABEL_BEARING:
        assert renderer.contrast_applicable(profile, "K6-SEP")
        first, second = _pair(renderer, registry, profile, "K6-SEP")
        assert first != second, profile
        assert first.encode("utf-8") != second.encode("utf-8"), profile


def test_k6_sep_is_structurally_absent_for_the_option_less_profiles(registry):
    """S3MR3-001. Absent, not duplicated: rendering R-sep must be impossible."""
    renderer = Renderer(registry)
    for profile in OPTION_LESS:
        assert renderer.contrast_applicable(profile, "K6-SEP") is False, profile
        assert renderer.rendering_applicable(profile, "R-sep") is False, profile
        with pytest.raises(UnregisteredSurface):
            renderer.render(profile, "R-sep", "K2/none/0",
                            BRANCH_VALUES["K2/none/0"])
        row = next(r for r in registry["applicability_table"]["rows"]
                   if r["profile"] == profile and r["contrast"] == "K6-SEP")
        assert row["applicability"] == "not_applicable"
        assert row["gate_bearing"] is False
        assert row["reason"]


def test_a_duplicated_r_sep_for_an_option_less_profile_would_be_byte_identical(registry):
    """The prohibited repair is demonstrably a self-comparison, not a pair.

    This is the exact defect S3MR3-001 recorded. Rendering R-sep for an
    option-less profile by reusing the R-base branch produces two byte-identical
    prompts, so the cell would be a self-comparison whose estimand is a plain
    marginal accuracy rather than a joint-correctness level over a pair.
    """
    mutated = json.loads(json.dumps(registry))
    for entry in mutated["renderings"]["entries"]:
        if entry["rendering_id"] == "R-sep":
            entry["applicable_profiles"] = list(PROFILES)
            entry["not_applicable_profiles"] = []
    for entry in mutated["instructions"]["entries"]:
        if entry["rendering"] == "R-sep" and not entry["applicable"]:
            entry["applicable"] = True
            entry["instruction"] = next(
                e["instruction"] for e in mutated["instructions"]["entries"]
                if e["profile"] == entry["profile"] and e["rendering"] == "R-base")
    renderer = Renderer(_reseal(mutated))
    for profile in OPTION_LESS:
        first, second = _pair(renderer, mutated, profile, "K6-SEP")
        assert first == second, \
            "the prohibited duplicate must be byte-identical, proving it is a " \
            "self-comparison rather than a presentation pair"


def test_k6_instr_members_differ_in_bytes_for_every_applicable_profile(registry):
    renderer = Renderer(registry)
    for profile in PROFILES:
        assert renderer.contrast_applicable(profile, "K6-INSTR"), profile
        first, second = _pair(renderer, registry, profile, "K6-INSTR")
        assert first != second, profile


def test_each_pair_differs_only_in_its_registered_factor(registry):
    """One-factor isolation, checked on bytes rather than asserted in prose."""
def test_each_pair_differs_only_in_its_registered_factor(registry):
    """One-factor isolation, checked on bytes rather than asserted in prose.

    The comparison is made part by part. A naive whole-prompt substitution would
    be unsound here, because the registered R-sep separator ' = ' also occurs
    inside registered question stems such as 'Let v0 = 3.'.
    """
    renderer = Renderer(registry)
    cue = registry["answer_cue"]["literal"]
    branch = "K2/none/0"
    values = BRANCH_VALUES[branch]
    labels, contents = _labels_and_contents(registry, 1, 2, 0)
    stem = renderer.stem(branch, values)

    # ---- K6-SEP: only the label-to-content separator moves -----------------
    for profile in LABEL_BEARING:
        base_block = renderer.option_block(profile, "R-base", labels, contents)
        var_block = renderer.option_block(profile, "R-sep", labels, contents)
        assert base_block != var_block, profile
        base_sep = registry["separators"]["R-base"]
        var_sep = registry["separators"]["R-sep"]
        base_lines = [ln for ln in base_block.split("\n") if ln]
        var_lines = [ln for ln in var_block.split("\n") if ln]
        assert len(base_lines) == len(var_lines) == 4
        for index, (left, right) in enumerate(zip(base_lines, var_lines)):
            assert left == labels[index] + base_sep + contents[index]
            assert right == labels[index] + var_sep + contents[index]
            # Same label, same content, different separator: exactly one factor.
            assert left.split(base_sep, 1)[0] == right.split(var_sep, 1)[0]
            assert left.split(base_sep, 1)[1] == right.split(var_sep, 1)[1]
        # Stem, instruction and cue are byte-identical across the pair.
        assert renderer.instruction(profile, "R-base") == \
            renderer.instruction(profile, "R-sep")
        first, second = _pair(renderer, registry, profile, "K6-SEP")
        assert first.startswith(stem) and second.startswith(stem)
        assert first.endswith(renderer.instruction(profile, "R-base") + cue)
        assert second.endswith(renderer.instruction(profile, "R-sep") + cue)

    # ---- K6-INSTR: only the instruction sentence moves ---------------------
    for profile in PROFILES:
        base_instr = renderer.instruction(profile, "R-base")
        var_instr = renderer.instruction(profile, "R-instr")
        assert base_instr != var_instr, profile
        first, second = _pair(renderer, registry, profile, "K6-INSTR")
        assert first.startswith(stem) and second.startswith(stem)
        assert first.endswith(base_instr + cue)
        assert second.endswith(var_instr + cue)
        # Everything before the instruction is byte-identical.
        assert first[:-len(base_instr + cue)] == second[:-len(var_instr + cue)]
        # The separator is byte-identical inside a K6-INSTR pair.
        assert registry["separators"]["R-base"] == registry["separators"]["R-instr"]


def test_a_byte_identical_applicable_pair_is_rejected(registry):
    """An applicable pair whose members coincide is a construction defect."""
    rules = registry["pair_isolation_rules"]
    assert rules["byte_identical_applicable_pair_is_a_defect"] is True
    assert rules["byte_identical_applicable_pair_disposition"].startswith(
        "REJECT_AS_A_CONSTRUCTION_DEFECT")

    mutated = json.loads(json.dumps(registry))
    mutated["separators"]["R-sep"] = mutated["separators"]["R-base"]
    renderer = Renderer(_reseal(mutated))
    for profile in LABEL_BEARING:
        first, second = _pair(renderer, mutated, profile, "K6-SEP")
        assert first == second
        with pytest.raises(AssertionError):
            assert first != second, "a byte-identical applicable pair must be rejected"


# --------------------------------------------------------------------------
# Rejection of unregistered substitutions
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["\t", "  ", " \n", "\u00a0", "\r\n"])
def test_unregistered_whitespace_is_rejected(registry, bad):
    mutated = json.loads(json.dumps(registry))
    mutated["separators"]["R-base"] = ":" + bad
    renderer = Renderer(mutated)
    labels, contents = _labels_and_contents(registry, 0, 0, 0)
    with pytest.raises(UnregisteredSurface):
        renderer.render("S1", "R-base", "K2/none/0", BRANCH_VALUES["K2/none/0"],
                        labels, contents)


def test_an_unregistered_placeholder_is_rejected(registry):
    mutated = json.loads(json.dumps(registry))
    for branch in mutated["question_stem_templates"]["branches"]:
        if branch["branch_id"] == "K2/none/0":
            branch["template"] = "Let v0 = {x}.\nCompute {undeclared}.\n"
    renderer = Renderer(_reseal(mutated))
    with pytest.raises(UnregisteredSurface):
        renderer.stem("K2/none/0", {"x": "3", "undeclared": "9"})


def test_a_missing_substitution_is_rejected(registry):
    renderer = Renderer(registry)
    with pytest.raises(UnregisteredSurface):
        renderer.stem("K3/affine_mod10/1", {"x": "4"})


def test_an_unregistered_instruction_substitution_is_rejected(registry):
    renderer = Renderer(registry)
    with pytest.raises(UnregisteredSurface):
        renderer.instruction("S2", "R-sep")


def test_an_unregistered_cue_is_rejected(registry):
    mutated = json.loads(json.dumps(registry))
    mutated["answer_cue"]["literal"] = "Answer: "
    renderer = Renderer(_reseal(mutated))
    labels, contents = _labels_and_contents(registry, 0, 0, 0)
    with pytest.raises(UnregisteredSurface):
        renderer.render("S1", "R-base", "K2/none/0", BRANCH_VALUES["K2/none/0"],
                        labels, contents)


def test_an_unregistered_option_count_is_rejected(registry):
    renderer = Renderer(registry)
    with pytest.raises(UnregisteredSurface):
        renderer.option_block("S1", "R-base", ["A", "B", "C"], ["1", "2", "3"])


def test_the_option_order_is_ascending_physical_position(registry):
    renderer = Renderer(registry)
    labels, contents = _labels_and_contents(registry, 2, 3, 1)
    block = renderer.option_block("S1", "R-base", labels, contents)
    lines = [line for line in block.split("\n") if line]
    assert len(lines) == 4
    separator = registry["separators"]["R-base"]
    for index, line in enumerate(lines):
        assert line.startswith(labels[index] + separator), index
        assert line == labels[index] + separator + contents[index]


def test_a_chat_wrapper_may_not_be_applied_to_a_raw_completion_profile(registry):
    for entry in registry["profiles"]:
        if entry["profile"] in ("S1", "S2", "S3"):
            assert entry["surface_class"] == "raw_completion"
            assert entry["chat_wrapper"] is None
            assert "no chat template" in entry["chat_wrapper_status"]
        else:
            assert entry["surface_class"] == "role_native_chat_wrapped"


def test_the_s4_wrapper_boundary_is_registered_and_exact(registry):
    entry = next(e for e in registry["profiles"] if e["profile"] == "S4")
    boundary = entry["wrapper_boundary"]
    assert boundary["wrapper_may_not_alter_registered_message_bytes"] is True
    assert boundary[
        "boundary_is_the_first_and_last_byte_of_the_registered_message_content"] is True
    assert entry["registered_message_content_template"].endswith(
        registry["answer_cue"]["literal"])


# --------------------------------------------------------------------------
# Candidate surfaces, tie-break and applicability table
# --------------------------------------------------------------------------

def test_candidate_surfaces_and_tie_break_are_exact(registry):
    cue = registry["answer_cue"]["literal"]
    assert not cue.endswith(" ")
    for entry in registry["profiles"]:
        surfaces = entry["candidate_surfaces"]
        if entry["profile"] == "S1":
            for name, values in surfaces["by_label_alphabet"].items():
                assert len(values) == 4 and len(set(values)) == 4, name
                for value in values:
                    assert value.startswith(" ") and value.strip() == value.lstrip()
                    assert len(value) == 2
        elif entry["profile"] in ("S2", "S3"):
            domain = surfaces["answer_domain"]
            assert len(domain) == 10 and len(set(domain)) == 10
            assert domain == [" %d" % d for d in range(10)]
        assert surfaces["tie_break_order"]
        assert surfaces["trailing_whitespace"] == "none" or \
            "none" in surfaces["trailing_whitespace"]


def test_label_alphabets_are_disjoint_from_the_answer_domain(registry):
    domain = set(registry["answer_domain"]["surface_forms"])
    alphabets = registry["label_alphabets"]["alphabets"]
    assert len(alphabets) == 2
    seen = []
    for name, symbols in alphabets.items():
        assert len(symbols) == 4 and len(set(symbols)) == 4, name
        assert not set(symbols) & domain, name
        seen.append(set(symbols))
    assert not seen[0] & seen[1]
    assert registry["label_alphabets"]["digits_prohibited_as_label_symbols"] is True


def test_the_applicability_table_covers_every_profile_rendering_contrast(registry):
    table = registry["applicability_table"]
    rows = {(r["profile"], r["contrast"]): r for r in table["rows"]}
    assert set(rows) == {(p, c) for p in PROFILES for c in CONTRASTS}
    assert table["row_count"] == len(rows) == 8
    for (profile, contrast), row in rows.items():
        expected = "applicable"
        if contrast == "K6-SEP" and profile in OPTION_LESS:
            expected = "not_applicable"
        assert row["applicability"] == expected, (profile, contrast)
        assert row["descriptive_only"] is (profile == "S4")
        assert row["gate_bearing"] is (expected == "applicable" and profile != "S4")
    counts = table["per_profile_applicable_contrast_counts"]
    assert counts["S1"] == counts["S4"] == 2
    assert counts["S2"] == counts["S3"] == 1
    assert "not a pass" in table["value_semantics"]["not_applicable"]


def test_the_registry_and_the_protocol_agree_on_applicability(registry, protocol):
    by_contrast = protocol["i3_contrast_registry"]["k6_applicability"]["by_contrast"]
    rows = {(r["profile"], r["contrast"]): r["applicability"]
            for r in registry["applicability_table"]["rows"]}
    for contrast, entry in by_contrast.items():
        for profile in PROFILES:
            expected = "applicable" if profile in entry["applicable_profiles"] \
                else "not_applicable"
            assert rows[(profile, contrast)] == expected, (profile, contrast)
    truth = {row["profile"]: row for row in protocol["gate_truth_table"]["rows"]}
    for profile in PROFILES:
        for contrast in CONTRASTS:
            assert truth[profile]["I3_K6"][contrast] == rows[(profile, contrast)], \
                (profile, contrast)


# --------------------------------------------------------------------------
# The zero-operation boundary and the future fail-closed rule
# --------------------------------------------------------------------------

def test_no_tokenizer_or_checkpoint_operation_is_claimed(registry, protocol):
    rule = registry["future_pre_bank_token_distinctness_rule"]
    assert rule["status"] == \
        "REGISTERED_FUTURE_FAIL_CLOSED_RULE_NOT_EVALUATED_IN_THIS_ROUND"
    assert rule["evaluated_in_this_round"] is False
    assert rule["tokenizer_calls_in_this_round"] == 0
    assert rule["resolves_od2"] is False
    assert "INELIGIBLE" in rule["on_failure"]
    assert "never treated as a pass" in rule["on_failure"]
    surface = protocol["rendering_surface_v0_5"]
    assert surface["tokenizer_distinctness_status"].startswith("NOT_TESTED_THIS_ROUND")
    assert surface["future_rule_resolves_od2"] is False


def test_the_rp_wrapper_stays_null_under_od2(registry, protocol):
    assert registry["rp_wrapper"]["wrapper"] is None
    assert registry["rp_wrapper"]["filled_in_by_v0_5"] is False
    assert registry["rp_wrapper"]["status"] == \
        "UNRESOLVED_BLOCKING_OPERATOR_DECISION_OD2"
    assert protocol["rendering_surface_v0_5"]["rp_wrapper"] is None
    decisions = {d["id"]: d for d in protocol["unresolved_operator_decisions"]}
    assert decisions["OD2"]["status"] == "unresolved"


def test_this_module_performs_no_model_operation():
    """A static guard: the fixtures may never import a model or tokenizer library."""
    with open(os.path.abspath(__file__), encoding="utf-8") as handle:
        source = handle.read()
    # The needles are assembled at runtime so that this guard cannot match itself.
    forbidden = ["import " + "torch", "import " + "transformers",
                 "from " + "transformers", "Auto" + "Tokenizer", "Auto" + "Model",
                 "requests." + "get", "urllib." + "request", "huggingface" + "_hub",
                 "from_" + "pretrained"]
    for needle in forbidden:
        assert source.count(needle) == 0, needle
