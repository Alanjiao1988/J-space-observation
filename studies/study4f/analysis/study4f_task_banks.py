"""Study 4F task banks: two strictly separated depth families.

Authority: ``studies/study4f/prompts/study4f_minimal_behavioral_feasibility_authority.md``

Section 5 of that authority forbids mixed-family banks. This module realizes
exactly two banks -- ``D2_DEVELOPMENT_BANK`` (family ``D2``) and
``D3_DEVELOPMENT_BANK`` (family ``D3``) -- of 104 unique eligible items each,
with an exact answer-label allocation that is guaranteed *by construction*
rather than checked after the fact:

* each label ``A``/``B``/``C``/``D`` occurs exactly 26 times in each 104-item bank;
* the deterministic first 60 items of each bank contain exactly 15 of each label;
* consequently the 44-item remainder contains exactly 11 of each label.

Provenance
----------
The arithmetic ontology, the eligibility rules, the option-draw rule and the
item body template are copied into this namespace from the *verified* bytes of
``studies/study3r/tasks/study3r_task_generators_v1.py``, which the single
independent focused review reproduced. They are copied, not imported: Study 4F
must never dynamically treat a rejected Study 3R protocol or pointer as
normative. :data:`PROVENANCE` binds the source path and its hashes.

Nothing here reads a Study 3R pointer, protocol or state machine at runtime.
"""

from __future__ import annotations

import hashlib
import random
from typing import Dict, Iterable, List, Sequence, Tuple

#: Source of the copied, independently verified algorithm. Bound by hash so a
#: later drift in the historical file is detectable, never resolved at runtime.
PROVENANCE: Dict[str, str] = {
    "source_path": "studies/study3r/tasks/study3r_task_generators_v1.py",
    "source_sha256": "47383a8f1c95f9efa868964097be5b2f9dfcce06d527678b1593685cdf52f97e",
    "source_git_blob": "88951091f1efe412458b87acc322813071b3abc2",
    "relationship": "algorithm copied with provenance; never imported, never "
                    "resolved as a runtime pointer",
}

# ---------------------------------------------------------------------------
# Frozen label alphabet and answer domain
# ---------------------------------------------------------------------------

LABELS: Tuple[str, ...] = ("A", "B", "C", "D")
CHANCE_LEVEL: Tuple[int, int] = (1, len(LABELS))

OPERATIONS: Dict[str, str] = {"ADD": "+", "SUB": "-", "MUL": "*"}
OPERAND_MIN = 0
OPERAND_MAX = 9
RESULT_MIN = 0
RESULT_MAX = 999
DISTRACTOR_OFFSETS: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

# ---------------------------------------------------------------------------
# The two registered families. Study 4F registers no other family.
# ---------------------------------------------------------------------------

STEM_TEMPLATES: Dict[str, str] = {
    "D2": "Compute ({a} {op1} {b}) {op2} {c}.",
    "D3": "Compute ((({a} {op1} {b}) {op2} {c}) {op3} {d}).",
}
FAMILY_DEPTH: Dict[str, int] = {"D2": 2, "D3": 3}

#: The two registered banks. Mixed-family banks are prohibited.
BANK_FAMILY: Dict[str, str] = {
    "D2_DEVELOPMENT_BANK": "D2",
    "D3_DEVELOPMENT_BANK": "D3",
}

BANK_SIZE = 104
DETERMINISTIC_PREFIX = 60
PREFIX_LABEL_COUNT = 15
BANK_LABEL_COUNT = 26

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


class Study4FBankCapacityError(RuntimeError):
    """Raised when a registered bank cannot realize its eligible items."""


class Study4FItemIneligibleError(ValueError):
    """Raised when a candidate item violates a registered eligibility rule."""


# ---------------------------------------------------------------------------
# Operation semantics
# ---------------------------------------------------------------------------


def apply_operation(name: str, left: int, right: int) -> int:
    if name == "ADD":
        return left + right
    if name == "SUB":
        return left - right
    if name == "MUL":
        return left * right
    raise Study4FItemIneligibleError("unregistered operation: %r" % (name,))


def evaluate(operands: Sequence[int], operations: Sequence[str]) -> int:
    """Left-associated evaluation of ``(((o0 op0 o1) op1 o2) op2 o3)``."""
    if len(operands) != len(operations) + 1:
        raise Study4FItemIneligibleError("operand/operation arity mismatch")
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
        raise Study4FItemIneligibleError("unregistered family: %r" % (family,))
    if len(options) != len(LABELS):
        raise Study4FItemIneligibleError("option arity must equal len(LABELS)")
    if len(set(options)) != len(options):
        raise Study4FItemIneligibleError("option values must be distinct")
    if any(option < 0 for option in options):
        raise Study4FItemIneligibleError("option values must be non-negative")
    if not RESULT_MIN <= value <= RESULT_MAX:
        raise Study4FItemIneligibleError("value outside the registered range")
    if not 0 <= correct_index < len(LABELS):
        raise Study4FItemIneligibleError("correct index outside the alphabet")
    if options[correct_index] != value:
        raise Study4FItemIneligibleError(
            "the registered label must carry the derivable value")


# ---------------------------------------------------------------------------
# Item construction and rendering
# ---------------------------------------------------------------------------


def render_stem(family: str, operands: Sequence[int],
                operations: Sequence[str]) -> str:
    template = STEM_TEMPLATES[family]
    fields: Dict[str, object] = {
        "a": operands[0], "b": operands[1], "op1": OPERATIONS[operations[0]]}
    if len(operands) > 2:
        fields["c"] = operands[2]
        fields["op2"] = OPERATIONS[operations[1]]
    if len(operands) > 3:
        fields["d"] = operands[3]
        fields["op3"] = OPERATIONS[operations[2]]
    return template.format(**fields)


def render_item_body(stem: str, options: Sequence[int]) -> str:
    """Render the arm-independent item body.

    The body is a pure function of ``(stem, options)``. No answer field and no
    answer-derived field is an argument, so none can leak into the prompt.
    """
    return ITEM_BODY_TEMPLATE.format(
        stem=stem,
        option_a=options[0],
        option_b=options[1],
        option_c=options[2],
        option_d=options[3],
    )


def item_key(family: str, stem: str, options: Sequence[int]) -> str:
    """Canonical content hash. Uniqueness and disjointness are enforced on it."""
    canonical = "|".join([family, stem] + [str(option) for option in options])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def content_hash(item: Dict[str, object]) -> str:
    """Cross-bank disjointness hash. Identical rule to :func:`item_key`."""
    options = [int(value) for value in item["options"]]  # type: ignore[union-attr]
    return item_key(str(item["family"]), str(item["stem"]), options)


def build_item(family: str, operands: Sequence[int], operations: Sequence[str],
               options: Sequence[int], correct_index: int,
               *, is_scientific_item: bool) -> Dict[str, object]:
    """Assemble, validate and render one item."""
    value = evaluate(operands, operations)
    stem = render_stem(family, operands, operations)
    check_eligibility(family, value, options, correct_index)
    body = render_item_body(stem, options)
    return {
        "family": family,
        "depth": FAMILY_DEPTH[family],
        "operands": list(operands),
        "operations": list(operations),
        "value": value,
        "options": list(options),
        "correct_index": correct_index,
        "correct_label": LABELS[correct_index],
        "stem": stem,
        "item_body": body,
        "item_key": item_key(family, stem, options),
        "is_scientific_item": bool(is_scientific_item),
    }


# ---------------------------------------------------------------------------
# Frozen seed derivation
# ---------------------------------------------------------------------------


def bank_seed_material(authority_commit: str, bank_id: str) -> str:
    """The frozen seed material: the authority commit plus the literal bank ID."""
    if bank_id not in BANK_FAMILY:
        raise Study4FItemIneligibleError("unregistered bank id: %r" % (bank_id,))
    if not authority_commit or len(authority_commit) != 40:
        raise Study4FItemIneligibleError(
            "the Study 4F authority commit must be a full 40-hex commit id")
    int(authority_commit, 16)
    return "STUDY4F|%s|%s" % (authority_commit.lower(), bank_id)


def bank_seed(authority_commit: str, bank_id: str) -> int:
    digest = hashlib.sha256(
        bank_seed_material(authority_commit, bank_id).encode("utf-8")).digest()
    return int.from_bytes(digest, "big")


def bank_generator(authority_commit: str, bank_id: str) -> random.Random:
    return random.Random(bank_seed(authority_commit, bank_id))


# ---------------------------------------------------------------------------
# Frozen ordering rule
# ---------------------------------------------------------------------------


def label_plan(rng: random.Random) -> List[int]:
    """The frozen answer-label ordering rule for one 104-item bank.

    Returns the correct-label index for every position. The allocation is exact
    by construction: the deterministic first 60 positions carry 15 of each
    label and the 44-position remainder carries 11 of each, so the whole bank
    carries 26 of each.
    """
    prefix: List[int] = []
    for index in range(len(LABELS)):
        prefix.extend([index] * PREFIX_LABEL_COUNT)
    remainder_count = BANK_LABEL_COUNT - PREFIX_LABEL_COUNT
    remainder: List[int] = []
    for index in range(len(LABELS)):
        remainder.extend([index] * remainder_count)
    if len(prefix) != DETERMINISTIC_PREFIX:
        raise Study4FItemIneligibleError("prefix plan is not 60 positions")
    if len(prefix) + len(remainder) != BANK_SIZE:
        raise Study4FItemIneligibleError("label plan is not 104 positions")
    rng.shuffle(prefix)
    rng.shuffle(remainder)
    return prefix + remainder


# ---------------------------------------------------------------------------
# Item drawing at a required label
# ---------------------------------------------------------------------------


def _draw_options(rng: random.Random, value: int, correct_index: int):
    """Draw four distinct non-negative options placing ``value`` at the label.

    The three distractors are drawn exactly as in the verified source rule and
    then shuffled; the correct value is placed at the position the frozen label
    plan requires. Label position is therefore exactly balanced rather than
    uniform only in expectation.
    """
    for _ in range(1024):
        offsets = rng.sample(DISTRACTOR_OFFSETS, 3)
        signs = [rng.choice((-1, 1)) for _ in offsets]
        distractors = [value + sign * offset
                       for sign, offset in zip(signs, offsets)]
        if any(distractor < 0 for distractor in distractors):
            continue
        if len(set(distractors + [value])) != len(LABELS):
            continue
        rng.shuffle(distractors)
        options = list(distractors)
        options.insert(correct_index, value)
        return options
    raise Study4FItemIneligibleError("option draw did not converge")


def generate_item(family: str, correct_index: int,
                  rng: random.Random) -> Dict[str, object]:
    """Draw one scientific item of ``family`` whose correct label is fixed."""
    depth = FAMILY_DEPTH[family]
    for _ in range(1024):
        arity = depth + 1
        operands = [rng.randint(OPERAND_MIN, OPERAND_MAX) for _ in range(arity)]
        operations = [rng.choice(sorted(OPERATIONS)) for _ in range(arity - 1)]
        partial = operands[0]
        rejected = False
        for index, operation in enumerate(operations):
            if operation == "SUB" and partial < operands[index + 1]:
                rejected = True
                break
            partial = apply_operation(operation, partial, operands[index + 1])
        if rejected:
            continue
        value = partial
        if not RESULT_MIN <= value <= RESULT_MAX:
            continue
        try:
            options = _draw_options(rng, value, correct_index)
        except Study4FItemIneligibleError:
            continue
        return build_item(family, operands, operations, options, correct_index,
                          is_scientific_item=True)
    raise Study4FItemIneligibleError(
        "item draw did not converge for family %r" % (family,))


def realize_bank(bank_id: str, authority_commit: str, *,
                 excluded_content_hashes: Iterable[str] = (),
                 size: int = BANK_SIZE) -> List[Dict[str, object]]:
    """Realize one registered single-family bank.

    ``excluded_content_hashes`` carries the other bank's canonical hashes, so
    cross-bank disjointness is enforced *during* realization rather than
    asserted afterwards.
    """
    family = BANK_FAMILY.get(bank_id)
    if family is None:
        raise Study4FItemIneligibleError("unregistered bank id: %r" % (bank_id,))
    rng = bank_generator(authority_commit, bank_id)
    plan = label_plan(rng)[:size]
    seen = set(excluded_content_hashes)
    items: List[Dict[str, object]] = []
    attempts = 0
    for correct_index in plan:
        while True:
            attempts += 1
            if attempts > 1_000_000:
                raise Study4FBankCapacityError(
                    "STUDY4F_REGISTERED_BANK_CAPACITY_UNAVAILABLE")
            item = generate_item(family, correct_index, rng)
            key = str(item["item_key"])
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
            break
    if len(items) != size:
        raise Study4FBankCapacityError(
            "STUDY4F_REGISTERED_BANK_CAPACITY_UNAVAILABLE")
    return items


def label_counts(items: Sequence[Dict[str, object]]) -> Dict[str, int]:
    counts = {label: 0 for label in LABELS}
    for item in items:
        counts[str(item["correct_label"])] += 1
    return counts
