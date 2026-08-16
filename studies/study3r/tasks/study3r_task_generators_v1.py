"""Study 3R clean-room task-population generators.

Authority: ``studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md``

This module is the frozen *specification* of every Study 3R task population. It
is written from scratch for Study 3R; no generator, ontology, renderer or
eligibility rule is carried forward from any earlier Study 3 draft.

Two strictly separated kinds of item exist here:

``tokenizer fixture``
    A small, literal, hand-fixed item used only to freeze byte and token
    surfaces during protocol authoring. Fixtures carry
    ``is_scientific_item = False`` and never enter an estimand, a gate or a
    statistical unit.

``scientific item``
    A seeded item belonging to a development, confirmation, control, ceiling or
    negative-control bank. No scientific item is realized in the authoring
    session: :func:`realize_bank` fails closed while
    ``formal_execution_authorized`` is false, and no execution seed is drawn.
"""

from __future__ import annotations

import hashlib
import random
from typing import Dict, Iterable, List, Sequence, Tuple

# ---------------------------------------------------------------------------
# Answer domain and label alphabet
# ---------------------------------------------------------------------------

#: The frozen label alphabet. ``len(LABELS)`` is the chance level denominator of
#: every label-answering gate in Study 3R.
LABELS: Tuple[str, ...] = ("A", "B", "C", "D")

#: Chance level as an exact rational pair ``(numerator, denominator)``.
CHANCE_LEVEL: Tuple[int, int] = (1, len(LABELS))

#: The frozen operation ontology. Every registered operation is a total,
#: closed function on the registered operand domain.
OPERATIONS: Dict[str, str] = {"ADD": "+", "SUB": "-", "MUL": "*"}

#: Operand domain for every generated operand.
OPERAND_MIN = 0
OPERAND_MAX = 9

#: Admissible result range for a fully evaluated expression.
RESULT_MIN = 0
RESULT_MAX = 999

#: Admissible absolute distractor offsets, in registered order.
DISTRACTOR_OFFSETS: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

# ---------------------------------------------------------------------------
# Rendering rules
# ---------------------------------------------------------------------------

#: The item body. Both E0 wrapper arms wrap *these exact bytes*; the arms differ
#: only in the envelope placed around this body.
ITEM_BODY_TEMPLATE = (
    "You are answering a multiple-choice item.\n"
    "Reply with exactly one option label and nothing else.\n"
    "\n"
    "Item: {stem}\n"
    "A) {option_a}\n"
    "B) {option_b}\n"
    "C) {option_c}\n"
    "D) {option_d}"
)

#: The answer cue. It terminates with a newline so that the first generated
#: token begins a line; no wrapper ever ends in a bare space.
ANSWER_CUE = "Answer:\n"

#: Separator between the item body and the answer cue in the raw arm.
RAW_ENVELOPE_SEPARATOR = "\n\n"

#: Stem templates, one per registered family.
STEM_TEMPLATES: Dict[str, str] = {
    "REC": "The stored value is {value}. Report the stored value.",
    "BIND": "Report the label bound to the value {value}.",
    "PRIM": "Compute {a} {op1} {b}.",
    "D2": "Compute ({a} {op1} {b}) {op2} {c}.",
    "D3": "Compute (({a} {op1} {b}) {op2} {c}) {op3} {d}.",
    "NEG": "Compute ({a} {op1} {b}) {op2} {c}.",
}

#: Registered families and their depth, in registered order.
FAMILY_DEPTH: Dict[str, int] = {
    "REC": 0,
    "BIND": 0,
    "PRIM": 1,
    "D2": 2,
    "D3": 3,
    "NEG": 2,
}

#: Families whose registered answer is derivable from the rendered item.
DERIVABLE_FAMILIES: Tuple[str, ...] = ("REC", "BIND", "PRIM", "D2", "D3")

#: The single deliberately invalid family.
NEGATIVE_CONTROL_FAMILY = "NEG"


class Study3RExecutionNotAuthorizedError(RuntimeError):
    """Raised when scientific bank realization is attempted before execution."""


class Study3RItemIneligibleError(ValueError):
    """Raised when a candidate item violates a registered eligibility rule."""


# ---------------------------------------------------------------------------
# Operation semantics
# ---------------------------------------------------------------------------


def apply_operation(name: str, left: int, right: int) -> int:
    """Total semantics of a registered operation on the registered domain."""
    if name == "ADD":
        return left + right
    if name == "SUB":
        return left - right
    if name == "MUL":
        return left * right
    raise Study3RItemIneligibleError("unregistered operation: %r" % (name,))


def evaluate(operands: Sequence[int], operations: Sequence[str]) -> int:
    """Left-associated evaluation of ``(((o0 op0 o1) op1 o2) op2 o3)``."""
    if len(operands) != len(operations) + 1:
        raise Study3RItemIneligibleError("operand/operation arity mismatch")
    value = operands[0]
    for index, operation in enumerate(operations):
        value = apply_operation(operation, value, operands[index + 1])
    return value


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


def check_eligibility(family: str, value: int, options: Sequence[int],
                      correct_index: int) -> None:
    """Enforce every registered eligibility rule. Raises on violation."""
    if family not in FAMILY_DEPTH:
        raise Study3RItemIneligibleError("unregistered family: %r" % (family,))
    if len(options) != len(LABELS):
        raise Study3RItemIneligibleError("option arity must equal len(LABELS)")
    if len(set(options)) != len(options):
        raise Study3RItemIneligibleError("option values must be distinct")
    if any(option < 0 for option in options):
        raise Study3RItemIneligibleError("option values must be non-negative")
    if not RESULT_MIN <= value <= RESULT_MAX:
        raise Study3RItemIneligibleError("value outside the registered range")
    if not 0 <= correct_index < len(LABELS):
        raise Study3RItemIneligibleError("correct index outside the alphabet")
    if family == NEGATIVE_CONTROL_FAMILY:
        if value in options:
            raise Study3RItemIneligibleError(
                "the negative control must not expose a derivable option")
    else:
        if options[correct_index] != value:
            raise Study3RItemIneligibleError(
                "the registered label must carry the derivable value")


# ---------------------------------------------------------------------------
# Item construction and rendering
# ---------------------------------------------------------------------------


def render_stem(family: str, operands: Sequence[int],
                operations: Sequence[str], value: int) -> str:
    """Render the frozen stem for one item."""
    template = STEM_TEMPLATES[family]
    if family in ("REC", "BIND"):
        return template.format(value=value)
    fields: Dict[str, object] = {"a": operands[0], "b": operands[1]}
    fields["op1"] = OPERATIONS[operations[0]]
    if len(operands) > 2:
        fields["c"] = operands[2]
        fields["op2"] = OPERATIONS[operations[1]]
    if len(operands) > 3:
        fields["d"] = operands[3]
        fields["op3"] = OPERATIONS[operations[2]]
    return template.format(**fields)


def render_item_body(stem: str, options: Sequence[int]) -> str:
    """Render the arm-independent item body."""
    return ITEM_BODY_TEMPLATE.format(
        stem=stem,
        option_a=options[0],
        option_b=options[1],
        option_c=options[2],
        option_d=options[3],
    )


def item_key(family: str, stem: str, options: Sequence[int]) -> str:
    """Canonical duplicate/collision key. Item-disjointness is enforced on it."""
    canonical = "|".join([family, stem] + [str(option) for option in options])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_item(family: str, operands: Sequence[int],
               operations: Sequence[str], options: Sequence[int],
               correct_index: int, *, is_scientific_item: bool,
               value=None) -> Dict[str, object]:
    """Assemble, validate and render one item."""
    if family in ("REC", "BIND"):
        resolved = options[correct_index] if value is None else int(value)
    elif value is None:
        resolved = evaluate(operands, operations)
    else:
        resolved = int(value)
    stem = render_stem(family, operands, operations, resolved)
    check_eligibility(family, resolved, options, correct_index)
    body = render_item_body(stem, options)
    return {
        "family": family,
        "depth": FAMILY_DEPTH[family],
        "operands": list(operands),
        "operations": list(operations),
        "value": resolved,
        "options": list(options),
        "correct_index": correct_index,
        "correct_label": LABELS[correct_index],
        "stem": stem,
        "item_body": body,
        "item_key": item_key(family, stem, options),
        "is_scientific_item": bool(is_scientific_item),
    }


# ---------------------------------------------------------------------------
# Seeded generation (specification; not executed in the authoring session)
# ---------------------------------------------------------------------------


def _draw_options(rng: random.Random, value: int,
                  derivable: bool):
    """Draw four distinct non-negative options under the registered rules."""
    for _ in range(1024):
        offsets = rng.sample(DISTRACTOR_OFFSETS, 3)
        signs = [rng.choice((-1, 1)) for _ in offsets]
        distractors = [value + sign * offset
                       for sign, offset in zip(signs, offsets)]
        if any(distractor < 0 for distractor in distractors):
            continue
        if derivable:
            pool = distractors + [value]
        else:
            remaining = [offset for offset in DISTRACTOR_OFFSETS
                         if offset not in offsets]
            extra = value + rng.choice(remaining)
            pool = distractors + [extra]
        if len(set(pool)) != len(LABELS):
            continue
        rng.shuffle(pool)
        if derivable:
            return pool, pool.index(value)
        return pool, rng.randrange(len(LABELS))
    raise Study3RItemIneligibleError("option draw did not converge")


def generate_item(family: str, rng: random.Random) -> Dict[str, object]:
    """Draw one scientific item of ``family`` from ``rng``.

    This function is the frozen generative rule. It is deterministic given the
    generator state, and it is never invoked on a scientific seed during the
    authoring session.
    """
    depth = FAMILY_DEPTH[family]
    for _ in range(1024):
        if family in ("REC", "BIND"):
            operands: List[int] = []
            operations: List[str] = []
            value = rng.randint(OPERAND_MIN, RESULT_MAX)
        else:
            arity = max(depth, 1) + 1
            operands = [rng.randint(OPERAND_MIN, OPERAND_MAX)
                        for _ in range(arity)]
            operations = [rng.choice(sorted(OPERATIONS))
                          for _ in range(arity - 1)]
            partial = operands[0]
            rejected = False
            for index, operation in enumerate(operations):
                if operation == "SUB" and partial < operands[index + 1]:
                    rejected = True
                    break
                partial = apply_operation(operation, partial,
                                          operands[index + 1])
            if rejected:
                continue
            value = partial
        if not RESULT_MIN <= value <= RESULT_MAX:
            continue
        derivable = family in DERIVABLE_FAMILIES
        try:
            options, correct_index = _draw_options(rng, value, derivable)
        except Study3RItemIneligibleError:
            continue
        return build_item(family, operands, operations, options,
                          correct_index, is_scientific_item=True, value=value)
    raise Study3RItemIneligibleError(
        "item draw did not converge for family %r" % (family,))


def bank_generator(execution_seed_hex: str, bank_id: str,
                   counter: int) -> random.Random:
    """Derive the registered per-bank generator.

    The execution seed is *not* drawn in the authoring session. At execution
    time the operator publishes a seed-commitment receipt containing
    ``execution_seed_hex`` before any bank is realized, and every bank is then
    derived deterministically from it by this rule.
    """
    material = "%s|%s|%d" % (execution_seed_hex, bank_id, counter)
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest, "big"))


def realize_bank(bank_id: str, family: str, size: int, *,
                 execution_seed_hex=None,
                 formal_execution_authorized: bool = False,
                 excluded_item_keys: Iterable[str] = ()) -> List[Dict[str, object]]:
    """Realize a scientific bank. Fails closed while execution is unauthorized."""
    if not formal_execution_authorized:
        raise Study3RExecutionNotAuthorizedError(
            "Study 3R bank realization requires formal_execution_authorized=True; "
            "the protocol candidate registers it as False")
    if not execution_seed_hex:
        raise Study3RExecutionNotAuthorizedError(
            "Study 3R bank realization requires a committed execution seed")
    excluded = set(excluded_item_keys)
    items: List[Dict[str, object]] = []
    counter = 0
    while len(items) < size:
        rng = bank_generator(execution_seed_hex, bank_id, counter)
        counter += 1
        item = generate_item(family, rng)
        if item["item_key"] in excluded:
            continue
        excluded.add(str(item["item_key"]))
        items.append(item)
        if counter > 1_000_000:  # pragma: no cover - registered stop rule
            raise Study3RItemIneligibleError("bank realization did not converge")
    return items


# ---------------------------------------------------------------------------
# Tokenizer fixtures (surface freezing only, never scientific)
# ---------------------------------------------------------------------------

#: Literal fixtures used only to freeze byte and token surfaces. They are fixed
#: constants, not draws, and they are excluded from every bank by construction.
TOKENIZER_FIXTURE_SPECS: Tuple[Dict[str, object], ...] = (
    {"family": "REC", "operands": (), "operations": (), "value": 47,
     "options": (12, 47, 5, 88), "correct_index": 1},
    {"family": "BIND", "operands": (), "operations": (), "value": 9,
     "options": (3, 21, 9, 40), "correct_index": 2},
    {"family": "PRIM", "operands": (7, 6), "operations": ("MUL",),
     "value": None, "options": (36, 48, 42, 40), "correct_index": 2},
    {"family": "D2", "operands": (8, 3, 4), "operations": ("ADD", "MUL"),
     "value": None, "options": (44, 33, 51, 38), "correct_index": 0},
    {"family": "D3", "operands": (9, 2, 5, 3), "operations": ("MUL", "SUB", "ADD"),
     "value": None, "options": (16, 22, 9, 31), "correct_index": 0},
    {"family": "NEG", "operands": (6, 5, 2), "operations": ("ADD", "MUL"),
     "value": None, "options": (14, 27, 35, 8), "correct_index": 3},
)


def tokenizer_fixtures() -> List[Dict[str, object]]:
    """Build the deterministic tokenizer fixtures, in registered order."""
    built: List[Dict[str, object]] = []
    for spec in TOKENIZER_FIXTURE_SPECS:
        built.append(build_item(
            str(spec["family"]),
            tuple(spec["operands"]),
            tuple(spec["operations"]),
            tuple(spec["options"]),
            int(spec["correct_index"]),
            is_scientific_item=False,
            value=spec["value"],
        ))
    return built


#: The single fixture whose rendered bytes freeze every wrapper surface.
CANONICAL_FIXTURE_INDEX = 3


def canonical_fixture() -> Dict[str, object]:
    """The depth-2 fixture used to freeze both E0 wrapper arms."""
    return tokenizer_fixtures()[CANONICAL_FIXTURE_INDEX]


def raw_arm_prompt(item_body: str) -> str:
    """Render the ``W1_RAW_DIRECT`` arm around an item body."""
    return item_body + RAW_ENVELOPE_SEPARATOR + ANSWER_CUE
