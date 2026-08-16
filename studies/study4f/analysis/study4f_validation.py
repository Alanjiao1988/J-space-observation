"""Study 4F semantic validators and mechanical preflight.

Authority: ``studies/study4f/prompts/study4f_minimal_behavioral_feasibility_authority.md``

Section 11 requires a mechanical preflight before any model execution. A
preflight failure can never be repaired by changing a decision-bearing value;
it stops with ``STUDY4F_PREFLIGHT_FAILED_NO_MODEL_EXECUTION``.

The validators here are *semantic*: they recompute the property from the item
bytes rather than trusting a declared field. That is what makes the seven
coordinated mutations the Study 3R focused review reported either killed or
structurally inapplicable:

===================================================== ===================
Study 3R survivor                                     Study 4F disposition
===================================================== ===================
``adv_cot_parser_regex_unanchored``                   structurally inapplicable
``adv_d2_d3_ceiling_mix_drops_depth_three``           structurally inapplicable
``adv_d2_d3_family_mix_drops_depth_three``            killed
``adv_d3_family_depth_relabelled``                    killed
``adv_forced_reasoning_closure_changed``              killed
``adv_forced_reasoning_closure_removed``              structurally inapplicable
``adv_surfaces_closure_emptied_while_rendered_bytes_unchanged`` structurally inapplicable
===================================================== ===================
"""

from __future__ import annotations

import os
import sys

# Each Study 4F module is individually importable and individually runnable,
# so a sibling import resolves against this directory rather than against an
# ambient package name.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fractions import Fraction
from typing import Dict, List, Mapping, Sequence

import study4f_design_statistics as stats
import study4f_interfaces as interfaces
import study4f_task_banks as banks

PREFLIGHT_FAILURE_STATE = "STUDY4F_PREFLIGHT_FAILED_NO_MODEL_EXECUTION"

#: The seven coordinated mutations reported by the Study 3R focused review, and
#: how Study 4F disposes of each.
STUDY3R_SURVIVOR_DISPOSITIONS: Dict[str, str] = {
    "adv_cot_parser_regex_unanchored": "structurally_inapplicable",
    "adv_d2_d3_ceiling_mix_drops_depth_three": "structurally_inapplicable",
    "adv_d2_d3_family_mix_drops_depth_three": "killed",
    "adv_d3_family_depth_relabelled": "killed",
    "adv_forced_reasoning_closure_changed": "killed",
    "adv_forced_reasoning_closure_removed": "structurally_inapplicable",
    "adv_surfaces_closure_emptied_while_rendered_bytes_unchanged":
        "structurally_inapplicable",
}


class Study4FPreflightError(RuntimeError):
    """Raised on any mechanical preflight violation."""

    def __init__(self, message: str) -> None:
        super().__init__("%s: %s" % (PREFLIGHT_FAILURE_STATE, message))


def _fail(message: str) -> None:
    raise Study4FPreflightError(message)


# ---------------------------------------------------------------------------
# Item-level semantic validation
# ---------------------------------------------------------------------------


def recompute_depth(item: Mapping[str, object]) -> int:
    """Depth recomputed from the item's own operand/operation arity.

    A relabelled ``depth`` field cannot survive this, because the value is
    never read from the item.
    """
    operations = list(item["operations"])  # type: ignore[arg-type]
    return len(operations)


def validate_item(item: Mapping[str, object], expected_family: str) -> None:
    family = str(item["family"])
    if family != expected_family:
        _fail("item family %r is not the bank family %r"
              % (family, expected_family))
    if family not in banks.FAMILY_DEPTH:
        _fail("unregistered family %r" % (family,))
    recomputed = recompute_depth(item)
    if recomputed != banks.FAMILY_DEPTH[family]:
        _fail("family %r has recomputed depth %d, registered depth %d"
              % (family, recomputed, banks.FAMILY_DEPTH[family]))
    if int(item["depth"]) != recomputed:
        _fail("declared depth %r contradicts the recomputed depth %d"
              % (item["depth"], recomputed))
    operands = [int(value) for value in item["operands"]]  # type: ignore[union-attr]
    operations = [str(value) for value in item["operations"]]  # type: ignore[union-attr]
    value = banks.evaluate(operands, operations)
    if value != int(item["value"]):
        _fail("declared value %r is not the evaluated value %d"
              % (item["value"], value))
    options = [int(option) for option in item["options"]]  # type: ignore[union-attr]
    banks.check_eligibility(family, value, options, int(item["correct_index"]))
    if str(item["correct_label"]) != banks.LABELS[int(item["correct_index"])]:
        _fail("correct_label contradicts correct_index")
    stem = banks.render_stem(family, operands, operations)
    if stem != str(item["stem"]):
        _fail("stem does not reproduce from the operands and operations")
    body = banks.render_item_body(stem, options)
    if body != str(item["item_body"]):
        _fail("item body does not reproduce from the stem and options")
    if banks.item_key(family, stem, options) != str(item["item_key"]):
        _fail("item key does not reproduce from the item content")


def validate_no_answer_leak(item: Mapping[str, object]) -> None:
    """The rendered prompt must be a pure function of the stem and options.

    Re-rendering with a different ``correct_index`` and a different
    ``correct_label`` must not move a single byte of either registered route.
    """
    stem = str(item["stem"])
    options = [int(option) for option in item["options"]]  # type: ignore[union-attr]
    body = banks.render_item_body(stem, options)
    if body != str(item["item_body"]):
        _fail("the rendered body is not a pure function of stem and options")
    for label_index in range(len(banks.LABELS)):
        shadow = dict(item)
        shadow["correct_index"] = label_index
        shadow["correct_label"] = banks.LABELS[label_index]
        shadow_body = banks.render_item_body(str(shadow["stem"]), options)
        if shadow_body != body:
            _fail("an answer-derived field leaked into the rendered prompt")
        if interfaces.render_w1_raw_direct(shadow_body) != \
                interfaces.render_w1_raw_direct(body):
            _fail("an answer-derived field leaked into the E0 prompt")
        if interfaces.render_c1_body(shadow_body) != \
                interfaces.render_c1_body(body):
            _fail("an answer-derived field leaked into the CoT prompt")


# ---------------------------------------------------------------------------
# Bank-level semantic validation
# ---------------------------------------------------------------------------


def validate_bank(bank_id: str, items: Sequence[Mapping[str, object]]) -> None:
    family = banks.BANK_FAMILY.get(bank_id)
    if family is None:
        _fail("unregistered bank id %r" % (bank_id,))
    if len(items) != banks.BANK_SIZE:
        _fail("bank %s has %d items, registered size is %d"
              % (bank_id, len(items), banks.BANK_SIZE))

    families = {str(item["family"]) for item in items}
    if families != {family}:
        _fail("bank %s is mixed-family: %s" % (bank_id, sorted(families)))
    depths = {recompute_depth(item) for item in items}
    if depths != {banks.FAMILY_DEPTH[family]}:
        _fail("bank %s carries recomputed depths %s" % (bank_id, sorted(depths)))

    for item in items:
        validate_item(item, family)
        validate_no_answer_leak(item)

    keys = [str(item["item_key"]) for item in items]
    if len(set(keys)) != len(keys):
        _fail("bank %s contains duplicate content hashes" % (bank_id,))

    counts = banks.label_counts(items)
    for label in banks.LABELS:
        if counts[label] != banks.BANK_LABEL_COUNT:
            _fail("bank %s label %s occurs %d times, registered %d"
                  % (bank_id, label, counts[label], banks.BANK_LABEL_COUNT))

    prefix = items[:banks.DETERMINISTIC_PREFIX]
    prefix_counts = banks.label_counts(prefix)
    for label in banks.LABELS:
        if prefix_counts[label] != banks.PREFIX_LABEL_COUNT:
            _fail("bank %s prefix label %s occurs %d times, registered %d"
                  % (bank_id, label, prefix_counts[label],
                     banks.PREFIX_LABEL_COUNT))


def validate_bank_pair(d2_items: Sequence[Mapping[str, object]],
                       d3_items: Sequence[Mapping[str, object]]) -> None:
    validate_bank("D2_DEVELOPMENT_BANK", d2_items)
    validate_bank("D3_DEVELOPMENT_BANK", d3_items)
    d2_hashes = {banks.content_hash(dict(item)) for item in d2_items}
    d3_hashes = {banks.content_hash(dict(item)) for item in d3_items}
    overlap = d2_hashes & d3_hashes
    if overlap:
        _fail("cross-bank content-hash overlap: %s" % sorted(overlap)[:3])
    if len(d2_hashes) != len(d2_items) or len(d3_hashes) != len(d3_items):
        _fail("content hashes are not injective within a bank")


# ---------------------------------------------------------------------------
# Interface and decoding validation
# ---------------------------------------------------------------------------

#: Every E0 decoding field that must be present. No field may be inherited.
REQUIRED_E0_FIELDS = (
    "do_sample", "temperature", "top_p", "top_k", "num_beams",
    "num_return_sequences", "repetition_penalty", "length_penalty",
    "early_stopping", "use_cache", "batch_size", "padding", "max_new_tokens",
)

REQUIRED_C1_FIELDS = (
    "do_sample", "temperature", "top_p", "top_k", "num_beams",
    "num_return_sequences", "k", "aggregation", "repetition_penalty",
    "length_penalty", "early_stopping", "use_cache", "max_new_tokens",
    "batch_size", "padding",
)


def validate_decoding_contracts() -> None:
    for field in REQUIRED_E0_FIELDS:
        if field not in interfaces.E0_GENERATION_CONTRACT:
            _fail("E0 decoding field %r is unspecified" % (field,))
    for field in REQUIRED_C1_FIELDS:
        if field not in interfaces.C1_GENERATION_CONTRACT:
            _fail("CoT decoding field %r is unspecified" % (field,))
    e0 = interfaces.E0_GENERATION_CONTRACT
    if e0["do_sample"] is not False:
        _fail("E0 must be greedy")
    if e0["max_new_tokens"] != 2:
        _fail("E0 max_new_tokens must be exactly 2")
    c1 = interfaces.C1_GENERATION_CONTRACT
    if c1["do_sample"] is not True or c1["temperature"] != 0.6:
        _fail("the CoT sampling contract is not the registered one")
    if c1["max_new_tokens"] != 4096:
        _fail("CoT max_new_tokens must be exactly 4096")


def validate_no_forced_closure() -> None:
    """The forced reasoning closure is explicitly absent on both routes.

    Study 3R finding F-06 recorded a closure injected into a wrapper without
    being named. Study 4F names its absence, and this validator makes that
    absence decision-bearing: setting a closure on either route fails preflight.
    """
    if interfaces.W1_PROVENANCE.get("forced_reasoning_closure") is not None:
        _fail("W1_RAW_DIRECT must not carry a forced reasoning closure")
    if interfaces.W1_PROVENANCE.get("uses_a_chat_template") is not False:
        _fail("W1_RAW_DIRECT must not use a chat template")
    if interfaces.C1_PROVENANCE.get("forced_reasoning_closure") is not None:
        _fail("the generated-CoT route must not force a reasoning closure")
    for provenance in (interfaces.W1_PROVENANCE, interfaces.C1_PROVENANCE):
        if provenance.get("forced_reasoning_closure_is_explicitly_absent") \
                is not True:
            _fail("the closure absence must be explicitly registered")


def validate_parsers() -> None:
    answer_ids = {"A": 32, "B": 33, "C": 34, "D": 35}
    eos = 151643
    if interfaces.parse_e0([32, eos], answer_ids, eos) != ("A", "CORRECT"):
        _fail("the E0 parser does not accept its own registered shape")
    if interfaces.parse_e0([32], answer_ids, eos)[1] != "INCORRECT_MISSING_EOS":
        _fail("the E0 parser accepts a missing EOS")
    if interfaces.parse_e0([32, 33, eos], answer_ids, eos)[1] != \
            "INCORRECT_EXTRA_TOKEN":
        _fail("the E0 parser accepts an extra token")
    if interfaces.parse_cot("FINAL: A") != ("A", "CORRECT"):
        _fail("the CoT parser does not accept its own registered shape")
    for rejected in ("FINAL: A ", " FINAL: A", "the answer is FINAL: A",
                     "FINAL: a", "FINAL:A", "FINAL: E", ""):
        if interfaces.parse_cot(rejected)[1] != "UNPARSEABLE":
            _fail("the CoT parser accepted %r" % (rejected,))


# ---------------------------------------------------------------------------
# Statistical validation
# ---------------------------------------------------------------------------


def validate_statistics() -> None:
    if stats.ALPHA_PER_CELL != Fraction(1, 320):
        _fail("alpha per cell is not 1/320")
    if stats.M_MAX != 16:
        _fail("m_max is not 16")
    if len(stats.registered_cells()) != stats.M_MAX:
        _fail("the registered cell census does not equal m_max")
    for cell in ("COT", "E0"):
        spec = stats.CELLS[cell]
        size = stats.exact_size(cell)
        power = stats.exact_power(cell)
        if size > stats.ALPHA_PER_CELL:
            _fail("cell %s exceeds its per-cell budget" % (cell,))
        if power < stats.TARGET_POWER:
            _fail("cell %s is underpowered" % (cell,))
        minimal = stats.minimal_design(
            spec["null_floor"], spec["design_alternative"])  # type: ignore[arg-type]
        if minimal != (int(spec["n"]), int(spec["pass_boundary"])):
            _fail("cell %s is not the minimal registered design" % (cell,))


# ---------------------------------------------------------------------------
# State-machine validation
# ---------------------------------------------------------------------------


def validate_state_machine() -> None:
    from itertools import product

    import study4f_state_machine as machine

    blocked = []
    for pattern in product([False, True], repeat=len(machine.LADDER)):
        results: Dict[tuple, bool] = {}
        for role, passing in zip(machine.LADDER, pattern):
            for depth in machine.DEPTHS:
                results[(role, depth, "COT")] = True
                results[(role, depth, "E0")] = passing
        outcome = machine.run_ladder(results)
        expected = next((role for role, passing
                         in zip(machine.LADDER, pattern) if passing), None)
        if outcome["qualified_candidate"] != expected:
            blocked.append(pattern)
    if blocked:
        _fail("a candidate failure blocked a later candidate: %s" % (blocked,))


def run_preflight(d2_items: Sequence[Mapping[str, object]],
                  d3_items: Sequence[Mapping[str, object]]) -> List[str]:
    """Run every mechanical check. Raises on the first violation."""
    performed: List[str] = []
    validate_statistics()
    performed.append("statistics")
    validate_decoding_contracts()
    performed.append("decoding_contracts")
    validate_no_forced_closure()
    performed.append("forced_closure_absence")
    validate_parsers()
    performed.append("parsers")
    validate_state_machine()
    performed.append("state_machine")
    validate_bank_pair(d2_items, d3_items)
    performed.append("banks")
    return performed
