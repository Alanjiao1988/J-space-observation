"""Set-derived facts, artifact agreement and the parser-v3 contract compiler.

Phase 1.2E. The Phase 1.2D failure had a single structural cause: the gate
contract, the set and the scoring instrument were three independently authored
descriptions with no mechanical agreement check between them. This module
supplies the missing check.

Two artifacts are kept deliberately separate:

*prospective evaluation policy*
    What the experiment commits to in advance: ontology, construction quotas,
    thresholds, comparator policy and PASS/FAIL logic. Authored by hand,
    registered before a set exists.

*set-derived facts manifest*
    What a candidate set actually contains: enum vocabulary, supports, stratum
    counts, gate denominators, membership and hashes. Produced mechanically
    from the set.

The compiler consumes both and emits a final contract only when every declared
invariant agrees. It never edits the policy to fit the set; a disagreement is
an error about the set, never a licence to move a threshold.

Nothing here reads a private set, a sealed blob or a locked label.

This module introduces no new parser dependency: it references no parser symbol
and invokes no parser. That is a narrower claim than "no parser module is
loaded", and the difference is deliberate. ``jspace_observation/__init__.py``
eagerly imports the legacy parser, so importing this module *through the
package* does place parser code in ``sys.modules``. The supportable and tested
claim is differential — importing this module adds no parser module beyond the
package baseline, and calls no parser function.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import evaluator_validation as frozen
from .parser_v3_repair_ontology import (
    RESEARCH_ONLY_TYPED_DECISION_CLASSES,
    SPAN_CONVENTION,
    STRATUM_PRESENCE,
    TRUTH_TABLE_ID,
    OntologyError,
    validate_ontology_set,
)

__all__ = [
    "ContractError",
    "COUNT_KINDS",
    "SetCounts",
    "SetSource",
    "AgreementFinding",
    "POLICY_SCHEMA_VERSION",
    "FACTS_SCHEMA_VERSION",
    "CONTRACT_SCHEMA_VERSION",
    "GATE_POPULATIONS",
    "GATE_ERROR_DEFINITIONS",
    "GATE_COUNTING_UNITS",
    "GateCoverage",
    "derive_gate_coverage",
    "THRESHOLD_BASIS_TYPES",
    "THRESHOLD_DISPOSITIONS",
    "BINDING_DISPOSITIONS",
    "NON_BINDING_DISPOSITIONS",
    "REQUIRED_THRESHOLD_FIELDS",
    "REQUIRED_BINDING_NARRATIVE_FIELDS",
    "INEQUALITY_DIRECTIONS",
    "validate_acceptance_thresholds",
    "validate_policy",
    "build_set_facts",
    "set_content_digest",
    "seal_facts",
    "verify_facts_integrity",
    "check_agreement",
    "compile_contract",
    "render_contract",
    "write_contract",
    "check_contract",
]


class ContractError(ValueError):
    """A contract artifact is malformed, disagrees, or would be overwritten."""


POLICY_SCHEMA_VERSION = "phase1-parser-v3-prospective-evaluation-policy/v3"
FACTS_SCHEMA_VERSION = "phase1-parser-v3-set-derived-facts/v1"
CONTRACT_SCHEMA_VERSION = "phase1-parser-v3-compiled-acceptance-contract/v1"


#: The only bases on which a numeric hard acceptance threshold may be set.
#: Every one of them can be discharged without observing the candidate parser
#: and without observing the future holdout. Phase 1.2F added this enumeration
#: because Phase 1.2E carried four numeric thresholds whose only stated
#: dependency was an unrelated experiment.
THRESHOLD_BASIS_TYPES: tuple[str, ...] = (
    "LOGICAL_INVARIANT",
    "DOWNSTREAM_ERROR_BUDGET",
    "EXTERNAL_CANDIDATE_INDEPENDENT_CALIBRATION",
    "REVIEWED_OPERATIONAL_REQUIREMENT",
)

#: Dispositions a threshold audit may assign.
THRESHOLD_DISPOSITIONS: tuple[str, ...] = (
    "KEEP_HARD",
    "REPLACE_HARD",
    "MERGE_WITH_EXISTING_GATE",
    "REPORT_ONLY",
    "REMOVE_REDUNDANT",
    "REVIEW_REQUIRED",
)

#: Dispositions under which a threshold participates in PASS/FAIL.
BINDING_DISPOSITIONS: tuple[str, ...] = ("KEEP_HARD",)

#: Dispositions under which a threshold must never influence PASS/FAIL.
#: ``REPLACE_HARD`` retires the identifier in favour of a differently defined
#: hard criterion, so the retired identifier itself stops binding.
NON_BINDING_DISPOSITIONS: tuple[str, ...] = (
    "REPLACE_HARD",
    "MERGE_WITH_EXISTING_GATE",
    "REPORT_ONLY",
    "REMOVE_REDUNDANT",
)

#: Machine-readable provenance every FINAL hard threshold must carry.
REQUIRED_THRESHOLD_FIELDS: tuple[str, ...] = (
    "basis_type",
    "controlled_risk",
    "derivation",
    "evidence_bindings",
    "candidate_independence",
    "set_independence",
    "boundary_semantics",
    "review_status",
)

#: Narrative provenance a FINAL *binding* criterion must carry, added in Phase
#: 1.2G. A Boolean independence flag records a claim; these fields record what
#: the claim rests on and what it does not cover. ``public_design_dependencies``
#: exists because zero tolerance is candidate-independent and set-independent
#: but is *not* context-free: it depends on the registered public ontology and
#: on what the strata are for.
REQUIRED_BINDING_NARRATIVE_FIELDS: tuple[str, ...] = (
    "candidate_observation_independence",
    "sealed_set_independence",
    "public_design_dependencies",
    "post_hoc_disclosure",
    "residual_limitations",
)

#: Recognised inequality directions for a numeric threshold.
INEQUALITY_DIRECTIONS: tuple[str, ...] = ("at_least", "at_most")

#: Sources that can never justify a threshold. ``headroom`` covers the Phase
#: 1.0C target-model task-headroom experiment, which measures whether the model
#: can answer a question. A parser threshold concerns whether the parser can
#: read an answer out of text. The two quantities are about different objects,
#: so no result of the first can bound the second.
PROHIBITED_BASIS_SOURCES: tuple[tuple[str, str], ...] = (
    ("1.0c", "Phase 1.0C is target-model task-headroom screening, not parser calibration"),
    ("headroom", "headroom screening does not measure parser extraction fidelity"),
    ("task screening", "task screening measures the model, not the parser"),
    ("observed parser", "a threshold must not be selected from observed parser performance"),
    ("measured parser", "a threshold must not be selected from measured parser performance"),
    ("parser v2 accuracy", "the predecessor's locked performance is not a candidate-independent basis"),
    ("parser v2 performance", "the predecessor's locked performance is not a candidate-independent basis"),
    ("parser v2 locked", "the predecessor's locked performance is not a candidate-independent basis"),
    ("locked performance", "a locked evaluation result must not be reused as a threshold basis"),
    ("development accuracy", "candidate development accuracy is not candidate-independent"),
    ("development performance", "candidate development performance is not candidate-independent"),
    ("expected performance", "an expectation about the candidate is not candidate-independent"),
    ("expected accuracy", "an expectation about the candidate is not candidate-independent"),
    ("likely to pass", "a value must never be selected because it would permit a pass"),
    ("would permit a pass", "a value must never be selected because it would permit a pass"),
    ("industry standard", "an appeal to industry standard needs a primary source and an applicability analysis"),
    ("industry practice", "an appeal to industry practice needs a primary source and an applicability analysis"),
    ("industry norm", "an appeal to industry norm needs a primary source and an applicability analysis"),
    ("benchmark norm", "an appeal to a benchmark norm needs a primary source and an applicability analysis"),
    ("common practice", "an appeal to common practice needs a primary source and an applicability analysis"),
    ("inherited verbatim", "a threshold must not be carried over verbatim from a predecessor contract"),
    ("carried over verbatim", "a threshold must not be carried over verbatim from a predecessor contract"),
)

#: Prose fields of a threshold record that are scanned for a prohibited basis,
#: whatever the record's disposition. Audit finding A6/B7 established that the
#: earlier scope - binding FINAL records only - never reached the one record
#: that will eventually carry a number.
SCANNED_THRESHOLD_PROSE_FIELDS: tuple[str, ...] = (
    "controlled_risk",
    "derivation",
    "rationale",
    "structural_derivation",
    "independence_analysis",
    "relationship_to_existing_gates",
    "why_numeric_value_is_blocked",
    "next_step",
    "sensitivity_analysis",
    "masking_finding",
)

#: Declared scopes for a gate's error definition. ``per_case`` errors are
#: counted case by case; ``set_level`` errors are properties of the whole run
#: and pin no individual case.
GATE_ERROR_SCOPES: tuple[str, ...] = ("per_case", "set_level")

#: Recognised counting units. A gate that counts cases and a gate that reports
#: a single whole-set property are not interchangeable, and reading the second
#: as the first is what produced the Phase 1.2F coverage error.
GATE_COUNTING_UNITS: tuple[str, ...] = ("case", "set")

#: Closed registry of the error definitions a gate may declare, owned by this
#: module rather than by the policy document.
#:
#: Phase 1.2G requirement. Coverage must be derived from code-owned closed
#: semantics, never from explanatory prose and never from a free-standing
#: Boolean in the policy. Each entry fixes three things that together decide
#: whether zero errors under that definition entails exact typed-decision
#: agreement for every case in the gate's population:
#:
#: ``scope``
#:     ``per_case`` or ``set_level``. A set-level property can never pin an
#:     individual case.
#: ``counting_unit``
#:     what one unit of ``maximum_errors`` counts.
#: ``pins_exact_typed_decision``
#:     whether a zero-error result under this definition *entails* exact typed
#:     decision agreement. This is the field the coverage derivation reads.
#:
#: An unknown definition is a hard error. Adding a definition is a deliberate
#: act that must state its pinning consequence here, in code, next to the
#: reason.
GATE_ERROR_DEFINITIONS: dict[str, dict[str, Any]] = {
    "expected_value_or_registered_selected_span_not_recovered": {
        "scope": "per_case",
        "counting_unit": "case",
        "pins_exact_typed_decision": True,
        "reason": (
            "recovering the registered expected value on a case is exact typed "
            "decision agreement for that case, so zero errors pins the population"
        ),
    },
    "typed_decision_is_not_no_answer": {
        "scope": "per_case",
        "counting_unit": "case",
        "pins_exact_typed_decision": True,
        "reason": (
            "no_answer carries no canonical value, so the typed class is the whole "
            "decision and requiring it exactly pins the population"
        ),
    },
    "typed_decision_is_not_ambiguous": {
        "scope": "per_case",
        "counting_unit": "case",
        "pins_exact_typed_decision": True,
        "reason": (
            "ambiguous carries no canonical value, so the typed class is the whole "
            "decision and requiring it exactly pins the population"
        ),
    },
    "registered_rightmost_distractor_span_selected": {
        "scope": "per_case",
        "counting_unit": "case",
        "pins_exact_typed_decision": False,
        "reason": (
            "this forbids one registered wrong span and nothing else. A parser can "
            "avoid the trailing distractor and still return a different wrong "
            "canonical value, or the wrong typed class, so zero errors here does "
            "not entail exact typed-decision agreement"
        ),
    },
    "reference_support_denominator_is_zero": {
        "scope": "set_level",
        "counting_unit": "set",
        "pins_exact_typed_decision": False,
        "reason": (
            "this constrains the reference supports of the set, not the parser's "
            "output, and cannot pin any case"
        ),
    },
    "parser_emitted_zero_instances_of_a_registered_typed_decision_class_across_the_whole_set": {
        "scope": "set_level",
        "counting_unit": "set",
        "pins_exact_typed_decision": False,
        "reason": (
            "a whole-set collapse property. Reading its zero tolerance as a "
            "per-case exact-agreement requirement would pin all 120 cases and make "
            "every acceptance criterion vacuous"
        ),
    },
}

#: Provenance every gate must declare so that ``maximum_errors`` has a meaning.
#: ``counting_unit`` was added in Phase 1.2G: without it, a set-level zero and a
#: per-case zero are written identically.
REQUIRED_GATE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "error_definition",
    "error_scope",
    "counting_unit",
    "pins_exact_typed_decision",
)


def _normalise_for_basis_scan(text: str) -> str:
    """Collapse spelling variation that would otherwise evade the basis scan.

    Substring matching bounds carelessness rather than intent, but it should at
    least not be defeated by a hyphen or a line wrap.
    """
    lowered = text.lower()
    for separator in ("-", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "_", "/"):
        lowered = lowered.replace(separator, " ")
    lowered = re.sub(r"\s+", " ", lowered)
    # ``1.0 c`` and ``1.0c`` must match the same needle.
    lowered = re.sub(r"\b1\.0\s+c\b", "1.0c", lowered)
    lowered = re.sub(r"\bparser\s+v\s*2\b", "parser v2", lowered)
    lowered = re.sub(r"\bparser\s+v\s*3\b", "parser v3", lowered)
    return lowered


def _reject_prohibited_basis(text: str, subject: str) -> None:
    """Refuse prose that grounds a parser threshold in a disallowed source."""
    lowered = _normalise_for_basis_scan(text)
    for needle, why in PROHIBITED_BASIS_SOURCES:
        if needle in lowered:
            raise ContractError(
                f"{subject} cites a prohibited threshold basis {needle!r}: {why}"
            )


def _scan_item_prose(item: Mapping[str, Any], threshold_id: str) -> None:
    """Scan every registered prose field of one record, whatever its status."""
    for field in SCANNED_THRESHOLD_PROSE_FIELDS:
        value = item.get(field)
        if isinstance(value, str):
            _reject_prohibited_basis(value, f"threshold {threshold_id} field {field}")
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for entry in value:
                if isinstance(entry, str):
                    _reject_prohibited_basis(
                        entry, f"threshold {threshold_id} field {field}"
                    )



def _validate_threshold_item(item: Mapping[str, Any], seen: set[str]) -> None:
    """Validate one acceptance-threshold record."""
    if not isinstance(item, Mapping):
        raise ContractError("each acceptance threshold must be an object")
    threshold_id = item.get("threshold_id")
    if not isinstance(threshold_id, str) or not threshold_id:
        raise ContractError("each acceptance threshold must carry a threshold_id")
    if threshold_id in seen:
        raise ContractError(f"duplicate threshold_id {threshold_id!r}")
    seen.add(threshold_id)

    status = item.get("status")
    if status not in ("FINAL", "REVIEW_REQUIRED"):
        raise ContractError(f"threshold {threshold_id} has an unrecognised status")

    disposition = item.get("disposition")
    if disposition not in THRESHOLD_DISPOSITIONS:
        raise ContractError(
            f"threshold {threshold_id} has an unrecognised disposition "
            f"{disposition!r}; Phase 1.2F requires an explicit audit disposition"
        )

    # The basis scan applies to every record, whatever its disposition. The
    # record most likely to acquire a bad basis is the one still unresolved.
    _scan_item_prose(item, threshold_id)

    # A non-binding threshold must not smuggle a live numeric criterion.
    if disposition in NON_BINDING_DISPOSITIONS:
        if item.get("value") is not None:
            raise ContractError(
                f"threshold {threshold_id} is {disposition} and must not carry a "
                "numeric value that could re-enter PASS/FAIL logic"
            )
        if item.get("binding") is not False:
            raise ContractError(
                f"threshold {threshold_id} is {disposition} and must declare "
                "binding=false"
            )
        return

    if disposition == "REVIEW_REQUIRED":
        if status != "REVIEW_REQUIRED":
            raise ContractError(
                f"threshold {threshold_id} is disposed REVIEW_REQUIRED and cannot "
                "declare itself FINAL"
            )
        if item.get("value") is not None:
            raise ContractError(
                f"threshold {threshold_id} is unresolved and must not carry a "
                "placeholder value"
            )
        if item.get("binding") is True:
            raise ContractError(
                f"threshold {threshold_id} is unresolved and must not declare "
                "binding=true; an undecided criterion cannot bind PASS/FAIL"
            )
        return

    # Remaining dispositions are binding hard thresholds.
    if status != "FINAL":
        # A hard threshold that is still under review carries no provenance
        # burden yet, but it must not carry a number either.
        if item.get("value") is not None:
            raise ContractError(
                f"threshold {threshold_id} is REVIEW_REQUIRED and must not carry a "
                "placeholder value"
            )
        return

    missing = [field for field in REQUIRED_THRESHOLD_FIELDS if field not in item]
    if missing:
        raise ContractError(
            f"threshold {threshold_id} is a FINAL hard criterion and is missing "
            f"required provenance fields: {', '.join(sorted(missing))}"
        )

    if disposition in BINDING_DISPOSITIONS:
        for field in REQUIRED_BINDING_NARRATIVE_FIELDS:
            text = item.get(field)
            if isinstance(text, list):
                text = " ".join(str(part) for part in text)
            if not isinstance(text, str) or not text.strip():
                raise ContractError(
                    f"threshold {threshold_id} binds acceptance and must carry a "
                    f"non-empty {field}"
                )
            _reject_prohibited_basis(text, f"threshold {threshold_id} {field}")

    basis = item.get("basis_type")
    if basis not in THRESHOLD_BASIS_TYPES:
        raise ContractError(
            f"threshold {threshold_id} declares an unrecognised basis_type "
            f"{basis!r}; recognised bases are {', '.join(THRESHOLD_BASIS_TYPES)}"
        )

    for field in ("controlled_risk", "derivation"):
        text = item.get(field)
        if not isinstance(text, str) or not text.strip():
            raise ContractError(
                f"threshold {threshold_id} must carry a non-empty {field}"
            )
        _reject_prohibited_basis(text, f"threshold {threshold_id} {field}")

    bindings = item.get("evidence_bindings")
    if not isinstance(bindings, list) or not bindings:
        raise ContractError(
            f"threshold {threshold_id} must bind at least one evidence source"
        )
    for binding in bindings:
        if not isinstance(binding, str) or not binding.strip():
            raise ContractError(
                f"threshold {threshold_id} has a malformed evidence binding"
            )
        _reject_prohibited_basis(binding, f"threshold {threshold_id} evidence binding")

    for field in ("candidate_independence", "set_independence"):
        if item.get(field) is not True:
            raise ContractError(
                f"threshold {threshold_id} must assert {field}=true; a threshold "
                "derived from the candidate or from the future set is not "
                "prospective"
            )

    if item.get("value") is None:
        raise ContractError(
            f"threshold {threshold_id} is FINAL and must carry a numeric value"
        )
    if item.get("binding") is not True:
        raise ContractError(
            f"threshold {threshold_id} is a hard criterion and must declare "
            "binding=true"
        )

    boundary = item.get("boundary_semantics")
    if not isinstance(boundary, Mapping):
        raise ContractError(
            f"threshold {threshold_id} must declare boundary_semantics"
        )
    direction = boundary.get("inequality")
    if direction not in INEQUALITY_DIRECTIONS:
        raise ContractError(
            f"threshold {threshold_id} must declare an inequality direction of "
            f"{' or '.join(INEQUALITY_DIRECTIONS)}"
        )
    # ``equality_passes`` is the Phase 1.2G name; ``at_threshold_passes`` is the
    # Phase 1.2F spelling. Either may be used, but two spellings of one fact
    # must not be able to disagree.
    equality = boundary.get("equality_passes")
    legacy_equality = boundary.get("at_threshold_passes")
    if equality is not None and legacy_equality is not None:
        if equality != legacy_equality:
            raise ContractError(
                f"threshold {threshold_id} declares equality_passes="
                f"{equality!r} and at_threshold_passes={legacy_equality!r}; two "
                "spellings of one boundary rule must agree"
            )
    if equality is None:
        equality = legacy_equality
    if not isinstance(equality, bool):
        raise ContractError(
            f"threshold {threshold_id} must state whether the exact threshold "
            "value passes"
        )
    if not isinstance(boundary.get("population"), str) or not boundary["population"]:
        raise ContractError(
            f"threshold {threshold_id} must state the population it scores"
        )

    # A comparator margin must not claim to require improvement while pointing
    # the inequality at a ceiling, or vice versa.
    margin = item.get("comparator_margin")
    if margin is not None:
        if not isinstance(margin, (int, float)):
            raise ContractError(
                f"threshold {threshold_id} comparator_margin must be numeric"
            )
        if direction == "at_least" and margin < 0:
            raise ContractError(
                f"threshold {threshold_id} declares an at_least comparison with a "
                "negative margin; the sign contradicts the direction"
            )
        if direction == "at_most" and margin > 0:
            raise ContractError(
                f"threshold {threshold_id} declares an at_most comparison with a "
                "positive margin; the sign contradicts the direction"
            )

    if item.get("review_status") != "REVIEWED":
        raise ContractError(
            f"threshold {threshold_id} is FINAL and must record review_status "
            "REVIEWED"
        )


def _scan_nested_prose(value: Any, subject: str) -> None:
    """Scan a string, list or mapping of prose for a prohibited basis.

    ``blocking_dependency`` grew from a string into a structured record during
    Phase 1.2F. A scanner that only understood strings would have stopped
    checking it at exactly that moment.
    """
    if isinstance(value, str):
        _reject_prohibited_basis(value, subject)
    elif isinstance(value, Mapping):
        for key, entry in value.items():
            _scan_nested_prose(entry, f"{subject}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, entry in enumerate(value):
            _scan_nested_prose(entry, f"{subject}[{index}]")


def _collect_clause_text(value: Any) -> list[str]:
    """Flatten a status-logic clause into the strings it is built from.

    A clause that is not a plain string must not silently bypass the
    non-binding re-entry check.

    Mapping *keys* are collected as well as values. A clause written as
    ``{"legacy_parser": "required"}`` places the reference in the key, and a
    values-only walk would report the clause as clean while the policy reads a
    comparator into its own pass condition. Post-remediation re-review finding
    A-04: the earlier walk collected values only, and a synthetic policy using a
    comparator name as a key validated successfully.
    """
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        collected: list[str] = []
        for key, entry in value.items():
            collected.extend(_collect_clause_text(key))
            collected.extend(_collect_clause_text(entry))
        return collected
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [text for entry in value for text in _collect_clause_text(entry)]
    if value is None:
        return []
    return [str(value)]


#: Fields of a threshold record that describe *its own* population, and are
#: therefore required to agree with the structured population declaration.
#: Phase 1.2G seed defect G-01: the residual criterion named three strata in
#: its metric and numerator while declaring four in its population and a
#: denominator of forty. Prose that contradicts the structure is not a
#: cosmetic problem, because the prose is what a reader acts on.
POPULATION_PROSE_FIELDS: tuple[str, ...] = (
    "metric_definition",
    "numerator",
    "failure_risk_controlled",
    "population_note",
)

_STRATUM_TOKEN_RE = re.compile(r"\bS(?:0[1-9]|1[0-2])\b")

#: Cardinality words that must agree with the size of the declared population.
_CARDINALITY_WORDS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
}


def _check_population_prose(
    item: Mapping[str, Any], strata: Sequence[str], case_count: int
) -> None:
    """Reject prose describing a population other than the declared one."""
    threshold_id = item["threshold_id"]
    expected = set(strata)
    for field in POPULATION_PROSE_FIELDS:
        text = item.get(field)
        if not isinstance(text, str) or not text.strip():
            continue
        mentioned = set(_STRATUM_TOKEN_RE.findall(text))
        if mentioned and mentioned != expected:
            raise ContractError(
                f"threshold {threshold_id} field {field} describes strata "
                f"{sorted(mentioned)} but the declared population is "
                f"{sorted(expected)}; a three-stratum description of a "
                "four-stratum population is the Phase 1.2F defect this check "
                "exists to prevent"
            )
        lowered = text.lower()
        for word, number in _CARDINALITY_WORDS.items():
            if number == len(expected):
                continue
            if re.search(rf"\b{word}\b[^.]{{0,40}}\bstrata\b", lowered):
                raise ContractError(
                    f"threshold {threshold_id} field {field} calls the population "
                    f"{word} strata while it is declared over {len(expected)}"
                )
        for match in re.finditer(r"\b(\d+)\s+cases\b", lowered):
            if int(match.group(1)) != case_count:
                raise ContractError(
                    f"threshold {threshold_id} field {field} says "
                    f"{match.group(1)} cases while the declared population holds "
                    f"{case_count}"
                )


def _require_int(value: Any, subject: str, low: int, high: int | None = None) -> int:
    """Require a plain integer in range, rejecting Booleans and floats.

    ``isinstance(True, int)`` is true in Python, so a Boolean limit would
    otherwise pass every range check and silently mean zero or one.

    ``high`` is optional because some callers know a lower bound but have no
    meaningful upper one; an absent upper bound must not become an excuse to
    skip the type check.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(
            f"{subject} must be an integer, not {type(value).__name__}; a Boolean "
            "or fractional limit has no meaning as an error count"
        )
    if value < low or (high is not None and value > high):
        bound = f"{low}..{high}" if high is not None else f"at least {low}"
        raise ContractError(f"{subject} must lie in {bound}, got {value}")
    return value


def _validate_residual_criterion(
    item: Mapping[str, Any], coverage: GateCoverage, cases_per_stratum: int
) -> None:
    """Validate the residual exact-conformance criterion against the gates.

    The population is not a free parameter. It is exactly the set of strata the
    mandatory gates leave unpinned, so it is checked against the derived
    coverage rather than read from the document.
    """
    threshold_id = item["threshold_id"]
    population = item.get("population")
    if not isinstance(population, Mapping):
        raise ContractError(
            f"threshold {threshold_id} must declare a structured population; a "
            "prose population cannot be checked against the derived coverage"
        )
    derivation = population.get("derivation")
    if derivation != "RESIDUAL_OF_EXACT_TYPED_DECISION_GATES":
        raise ContractError(
            f"threshold {threshold_id} must declare its population derivation as "
            "RESIDUAL_OF_EXACT_TYPED_DECISION_GATES"
        )
    strata = population.get("strata")
    if not isinstance(strata, list) or not strata:
        raise ContractError(f"threshold {threshold_id} must list its residual strata")
    if tuple(strata) != coverage.residual_strata:
        raise ContractError(
            f"threshold {threshold_id} declares residual strata {strata} but the "
            f"gates leave {list(coverage.residual_strata)} unpinned"
        )
    declared_per_stratum = _require_int(
        population.get("cases_per_stratum"),
        f"threshold {threshold_id} population.cases_per_stratum",
        1,
        cases_per_stratum,
    )
    if declared_per_stratum != cases_per_stratum:
        raise ContractError(
            f"threshold {threshold_id} declares {declared_per_stratum} cases per "
            f"stratum but the set registers {cases_per_stratum}"
        )
    case_count = _require_int(
        population.get("case_count"),
        f"threshold {threshold_id} population.case_count",
        0,
        coverage.total_case_count,
    )
    if case_count != coverage.residual_case_count:
        raise ContractError(
            f"threshold {threshold_id} declares a residual population of "
            f"{case_count} cases but the gates leave "
            f"{coverage.residual_case_count}; substituting the superseded "
            "three-stratum count is the Phase 1.2F defect"
        )
    if case_count != len(strata) * declared_per_stratum:
        raise ContractError(
            f"threshold {threshold_id} population.case_count is not the product of "
            "its own strata and cases_per_stratum"
        )

    _check_population_prose(item, strata, case_count)

    limits = item.get("limits")
    if not isinstance(limits, Mapping):
        raise ContractError(
            f"threshold {threshold_id} must declare structured limits; a "
            "concentration cap stated only in prose cannot be enforced"
        )
    pooled = _require_int(
        limits.get("pooled_max_errors"),
        f"threshold {threshold_id} limits.pooled_max_errors",
        0,
        case_count,
    )
    per_stratum_limits = limits.get("per_stratum_max_errors")
    if not isinstance(per_stratum_limits, Mapping) or not per_stratum_limits:
        raise ContractError(
            f"threshold {threshold_id} must declare a per-stratum concentration "
            "cap for every residual stratum"
        )
    if sorted(per_stratum_limits) != sorted(strata):
        raise ContractError(
            f"threshold {threshold_id} declares per-stratum caps for "
            f"{sorted(per_stratum_limits)} but its population is {sorted(strata)}"
        )
    for stratum in sorted(per_stratum_limits):
        _require_int(
            per_stratum_limits[stratum],
            f"threshold {threshold_id} limits.per_stratum_max_errors.{stratum}",
            0,
            declared_per_stratum,
        )

    # A per-stratum cap above the pooled cap is unreachable, and a policy that
    # states one is not merely redundant: it reads as permission. Phase 1.2G
    # records both limits precisely so that relaxing one without the other is
    # caught, which only works if the relation is enforced rather than
    # described. Audit finding A3/B9.
    for stratum in sorted(per_stratum_limits):
        cap = per_stratum_limits[stratum]
        if cap > pooled:
            raise ContractError(
                f"threshold {threshold_id} allows {cap} errors in {stratum} while "
                f"its pooled limit is {pooled}; a per-stratum cap above the "
                "pooled cap is unreachable and misstates the constraint"
            )

    # A legacy generic ``value`` is permitted only as an alias of the pooled
    # limit. Two numbers that can disagree are two policies.
    if "value" in item and item["value"] is not None:
        alias = _require_int(
            item["value"], f"threshold {threshold_id} value", 0, case_count
        )
        if alias != pooled:
            raise ContractError(
                f"threshold {threshold_id} carries value {alias} while its pooled "
                f"limit is {pooled}; the generic value is defined as the pooled "
                "limit and must equal it"
            )

    boundary = item.get("boundary_semantics")
    if not isinstance(boundary, Mapping):
        raise ContractError(f"threshold {threshold_id} must declare boundary_semantics")
    if boundary.get("inequality") != "at_most":
        raise ContractError(
            f"threshold {threshold_id} counts errors and must use an at_most "
            "inequality"
        )
    equality = boundary.get("equality_passes")
    if equality is None:
        equality = boundary.get("at_threshold_passes")
    if equality is not True:
        raise ContractError(
            f"threshold {threshold_id} must declare that the exact limit passes; "
            "at most zero errors means zero errors is a pass"
        )


def _validate_gate_semantics(gate: Mapping[str, Any]) -> dict[str, Any]:
    """Require every gate to declare what one of its errors is, and check it.

    Audit finding A2. Without this, ``maximum_errors: 0`` has no meaning, and
    the coverage baseline that every threshold disposition rests on can be read
    three incompatible ways from the same field.

    Phase 1.2G goes further. The declared semantics are checked against the
    code-owned :data:`GATE_ERROR_DEFINITIONS` registry, and the policy's
    ``pins_exact_typed_decision`` Boolean is treated as a readability
    restatement that must agree with the registry rather than as an independent
    source of truth. Returns the registry entry so the caller can derive
    coverage from it.
    """
    gate_id = gate.get("gate_id", "<unnamed>")
    missing = [f for f in REQUIRED_GATE_SEMANTIC_FIELDS if f not in gate]
    if missing:
        raise ContractError(
            f"gate {gate_id} is missing required error semantics: "
            f"{', '.join(sorted(missing))}; maximum_errors has no meaning without "
            "a declared error definition"
        )
    definition = gate["error_definition"]
    if not isinstance(definition, str) or not definition.strip():
        raise ContractError(f"gate {gate_id} must declare a non-empty error_definition")
    registered = GATE_ERROR_DEFINITIONS.get(definition)
    if registered is None:
        raise ContractError(
            f"gate {gate_id} declares error_definition {definition!r}, which is not "
            "in the closed registry; coverage cannot be derived from an error "
            "definition whose pinning consequence has never been decided"
        )
    if gate["error_scope"] not in GATE_ERROR_SCOPES:
        raise ContractError(
            f"gate {gate_id} declares an unrecognised error_scope "
            f"{gate['error_scope']!r}"
        )
    if gate["error_scope"] != registered["scope"]:
        raise ContractError(
            f"gate {gate_id} declares error_scope {gate['error_scope']!r} but "
            f"{definition!r} is registered as {registered['scope']!r}"
        )
    if gate["counting_unit"] not in GATE_COUNTING_UNITS:
        raise ContractError(
            f"gate {gate_id} declares an unrecognised counting_unit "
            f"{gate['counting_unit']!r}"
        )
    if gate["counting_unit"] != registered["counting_unit"]:
        raise ContractError(
            f"gate {gate_id} declares counting_unit {gate['counting_unit']!r} but "
            f"{definition!r} is registered as {registered['counting_unit']!r}"
        )
    declared_pins = gate["pins_exact_typed_decision"]
    if not isinstance(declared_pins, bool):
        raise ContractError(
            f"gate {gate_id} must declare pins_exact_typed_decision as a boolean"
        )
    if declared_pins != registered["pins_exact_typed_decision"]:
        raise ContractError(
            f"gate {gate_id} declares pins_exact_typed_decision={declared_pins} but "
            f"its registered error definition {definition!r} entails "
            f"{registered['pins_exact_typed_decision']}: {registered['reason']}"
        )
    if gate["error_scope"] == "set_level" and declared_pins:
        raise ContractError(
            f"gate {gate_id} declares a set-level error scope and cannot pin any "
            "individual case to exact typed-decision agreement"
        )
    return dict(registered)


@dataclass(frozen=True)
class GateCoverage:
    """Exact-typed-decision coverage derived from structured gate semantics.

    This is the production derivation. Both :func:`validate_policy` and, through
    it, :func:`compile_contract` read coverage from here, so a test can never
    prove a coverage claim that the compiler does not also enforce.
    """

    pinned_strata: tuple[str, ...]
    pinned_case_count: int
    residual_strata: tuple[str, ...]
    residual_case_count: int
    total_case_count: int
    pinning_gates: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "pinned_strata": list(self.pinned_strata),
            "pinned_case_count": self.pinned_case_count,
            "residual_strata": list(self.residual_strata),
            "residual_case_count": self.residual_case_count,
            "total_case_count": self.total_case_count,
            "pinning_gates": list(self.pinning_gates),
        }


def _resolve_gate_strata(
    gate: Mapping[str, Any], population: Mapping[str, Any]
) -> tuple[str, ...]:
    """Resolve a gate's population to the strata it actually scores.

    Fails closed. An unresolved selector, an unknown population kind, or a
    selector naming a stratum the set does not contain is an error, never an
    empty set that would silently shrink coverage.
    """
    gate_id = gate.get("gate_id", "<unnamed>")
    kind = gate.get("population")
    strata = tuple(population["strata"])

    if kind == "all_cases":
        return strata
    if kind == "clean_cases":
        clean = population.get("clean_strata")
        if not isinstance(clean, list) or not clean:
            raise ContractError(
                f"gate {gate_id} scores the clean cases but "
                "policy.population.clean_strata is not declared"
            )
        unknown = sorted(set(clean) - set(strata))
        if unknown:
            raise ContractError(
                f"policy.population.clean_strata names unregistered strata: "
                f"{', '.join(unknown)}"
            )
        return tuple(sorted(clean))
    if kind == "stratum":
        selector = gate.get("population_selector")
        if selector not in strata:
            raise ContractError(
                f"gate {gate_id} selects stratum {selector!r}, which is not a "
                "registered stratum"
            )
        return (selector,)
    if kind in ("typed_decision_class", "answer_presence"):
        selector = gate.get("population_selector")
        presence = population.get("stratum_presence") or {}
        resolved = tuple(
            sorted(name for name, value in presence.items() if value == selector)
        )
        if not resolved:
            raise ContractError(
                f"gate {gate_id} selects class {selector!r}, which no registered "
                "stratum carries; an unresolvable population is an error, not an "
                "empty gate"
            )
        return resolved
    raise ContractError(
        f"gate {gate_id} declares population kind {kind!r}, which has no "
        "registered resolution rule"
    )


def derive_gate_coverage(policy: Mapping[str, Any]) -> GateCoverage:
    """Derive exact-typed-decision coverage from the gates alone.

    The single production derivation required by Phase 1.2G. A stratum is
    *pinned* when some mandatory gate scores it with a per-case error definition
    that the code-owned registry says entails exact typed-decision agreement.
    Every other stratum is *residual*.

    Fails closed on an unknown error definition, an unknown population kind, an
    unresolvable selector, a missing counting unit, an overlap between two
    pinning gates, or any stratum that is neither pinned nor residual.
    """
    population = policy.get("population")
    if not isinstance(population, Mapping):
        raise ContractError("policy.population must be an object to derive coverage")
    strata = tuple(population["strata"])
    per_stratum = population["cases_per_stratum"]

    pinned: dict[str, str] = {}
    pinning_gates: list[str] = []
    for gate in policy["gates"]:
        registered = _validate_gate_semantics(gate)
        resolved = _resolve_gate_strata(gate, population)
        # ``maximum_errors`` decides whether a gate pins, so it is derivation
        # input, not decoration. It must be a plain non-negative integer, or
        # explicitly ``None`` for a gate that constrains support rather than
        # errors: ``False`` and ``0.0`` both compare equal to zero in Python,
        # so an untyped read would let a malformed gate pin a stratum. Audit
        # finding A5/B7.
        raw_limit = gate.get("maximum_errors")
        if raw_limit is None:
            if registered["pins_exact_typed_decision"]:
                raise ContractError(
                    f"gate {gate.get('gate_id')} pins exact typed-decision "
                    "agreement but declares no maximum_errors; a pinning gate "
                    "must state its error limit"
                )
            limit = None
        else:
            limit = _require_int(
                raw_limit,
                f"gate {gate.get('gate_id')} maximum_errors",
                0,
                len(resolved) * per_stratum if resolved else None,
            )
        if not gate.get("mandatory"):
            continue
        if not registered["pins_exact_typed_decision"]:
            continue
        if limit != 0:
            # A pinning definition only pins at zero tolerance. A non-zero
            # allowance leaves individual cases free and must not be counted.
            continue
        pinning_gates.append(gate["gate_id"])
        for stratum in resolved:
            if stratum in pinned:
                raise ContractError(
                    f"strata {stratum} is pinned by both {pinned[stratum]} and "
                    f"{gate['gate_id']}; overlapping exact-agreement coverage is "
                    "not permitted because it makes the residual population "
                    "ambiguous"
                )
            pinned[stratum] = gate["gate_id"]

    pinned_strata = tuple(sorted(pinned))
    residual_strata = tuple(sorted(set(strata) - set(pinned_strata)))
    if set(pinned_strata) | set(residual_strata) != set(strata):
        raise ContractError(
            "derived coverage does not partition the registered strata"
        )
    coverage = GateCoverage(
        pinned_strata=pinned_strata,
        pinned_case_count=len(pinned_strata) * per_stratum,
        residual_strata=residual_strata,
        residual_case_count=len(residual_strata) * per_stratum,
        total_case_count=population["total_case_count"],
        pinning_gates=tuple(sorted(pinning_gates)),
    )
    if (
        coverage.pinned_case_count + coverage.residual_case_count
        != coverage.total_case_count
    ):
        raise ContractError(
            "derived coverage case counts do not sum to the registered total"
        )
    return coverage


def _check_declared_coverage(
    policy: Mapping[str, Any], coverage: GateCoverage
) -> None:
    """Reject a hand-maintained coverage block that disagrees with derivation.

    The policy keeps a readable coverage section. Phase 1.2G makes it a
    restatement: any disagreement with the derived values is an error, so the
    document can never drift away from the code that enforces it.
    """
    declared = policy.get("gate_coverage_analysis")
    if not isinstance(declared, Mapping):
        raise ContractError("policy.gate_coverage_analysis must be an object")
    expected = {
        "zero_error_pinned_strata": list(coverage.pinned_strata),
        "zero_error_pinned_case_count": coverage.pinned_case_count,
        "residual_strata": list(coverage.residual_strata),
        "residual_case_count": coverage.residual_case_count,
    }
    for field, value in expected.items():
        if field not in declared:
            raise ContractError(
                f"policy.gate_coverage_analysis is missing {field}; the declared "
                "coverage block must restate every derived value"
            )
        if declared[field] != value:
            raise ContractError(
                f"policy.gate_coverage_analysis.{field} is {declared[field]!r} but "
                f"the gates derive {value!r}"
            )


def validate_acceptance_thresholds(
    thresholds: Mapping[str, Any],
    *,
    coverage: GateCoverage | None = None,
    cases_per_stratum: int | None = None,
) -> set[str]:
    """Validate the acceptance-threshold block and its provenance.

    Phase 1.2F requirement. A numeric hard threshold is only prospective if it
    can be derived without observing the candidate parser and without observing
    the future holdout, so every FINAL hard threshold must name a recognised
    basis type and carry a complete derivation.

    When ``coverage`` is supplied, any criterion declaring a residual population
    is additionally checked against the derived gate coverage, so a criterion
    can never claim a population the gates do not leave free.

    Returns the set of threshold identifiers that must never influence
    PASS/FAIL, so that the caller can police the policy's status logic.
    """
    if not isinstance(thresholds, Mapping):
        raise ContractError("policy.acceptance_thresholds must be an object")
    if thresholds.get("status") not in ("FINAL", "REVIEW_REQUIRED"):
        raise ContractError("policy.acceptance_thresholds.status is not recognised")

    for field in ("reason", "blocking_dependency"):
        _scan_nested_prose(thresholds.get(field), f"acceptance_thresholds.{field}")

    items = thresholds.get("items")
    if not isinstance(items, list) or not items:
        raise ContractError("policy.acceptance_thresholds.items must be a list")

    seen: set[str] = set()
    for item in items:
        _validate_threshold_item(item, seen)

    # A criterion whose population is the residual of the gates must be checked
    # against the derived coverage, not against its own description of itself.
    if coverage is not None and cases_per_stratum is not None:
        for item in items:
            population = item.get("population")
            if not isinstance(population, Mapping):
                continue
            if population.get("derivation") is None:
                continue
            _validate_residual_criterion(item, coverage, cases_per_stratum)

    binding_ids = {
        item["threshold_id"]
        for item in items
        if item.get("disposition") in BINDING_DISPOSITIONS
    }

    # A retired threshold must name the criterion that absorbed it, and that
    # criterion must actually bind. Audit finding A5/B6: without the second
    # half, every protection could be "absorbed" into something non-binding and
    # the policy would still compile.
    for item in items:
        disposition = item["disposition"]
        pointer_field = {
            "REPLACE_HARD": "replaced_by",
            "MERGE_WITH_EXISTING_GATE": "merged_into",
            "REMOVE_REDUNDANT": "subsumed_by",
        }.get(disposition)
        if pointer_field is None:
            continue
        target = item.get(pointer_field)
        if not isinstance(target, str) or not target:
            raise ContractError(
                f"threshold {item['threshold_id']} is {disposition} and must name "
                f"its successor in {pointer_field}"
            )
        if target not in seen and not target.startswith("G_"):
            raise ContractError(
                f"threshold {item['threshold_id']} names unknown successor "
                f"{target!r}"
            )
        if (
            thresholds["status"] == "FINAL"
            and not target.startswith("G_")
            and target not in binding_ids
        ):
            raise ContractError(
                f"threshold {item['threshold_id']} is {disposition} into "
                f"{target!r}, which does not bind; retiring a threshold must "
                "never silently delete a protection"
            )

    unresolved = [
        item["threshold_id"]
        for item in items
        if item.get("status") != "FINAL"
    ]
    if thresholds["status"] == "FINAL" and unresolved:
        raise ContractError(
            "acceptance_thresholds.status is FINAL while these thresholds remain "
            f"unresolved: {', '.join(sorted(unresolved))}"
        )

    # A FINAL policy with no binding criterion reduces PASS to a gates-only
    # condition and leaves the free population wholly unconstrained. Audit
    # finding A5/B6: that is the failure this phase exists to prevent, and it
    # was reachable without tripping any check.
    if thresholds["status"] == "FINAL" and not binding_ids:
        raise ContractError(
            "acceptance_thresholds.status is FINAL with no binding acceptance "
            "criterion; PASS would reduce to the mandatory gates alone and the "
            "cases they leave free would be unconstrained"
        )

    # A non-binding metric must not be named by the PASS/FAIL logic.
    non_binding = {
        item["threshold_id"]
        for item in items
        if item.get("disposition") in NON_BINDING_DISPOSITIONS
    }
    return non_binding



#: Distinct countable populations. Phase 1.2D reported "Holdout objects 15" by
#: conflating storage objects with residual invalid cases; the two counts are
#: 12 and 15 respectively and are never interchangeable. Keeping the kinds
#: enumerated makes the confusion a type error rather than a prose slip.
COUNT_KINDS: tuple[str, ...] = (
    "sealed_object_count",
    "total_case_count",
    "residual_semantic_case_count",
    "prediction_stream_count",
    "score_state_object_count",
)


@dataclass(frozen=True)
class SetCounts:
    """Mutually non-substitutable counts for one evaluation set.

    ``sealed_object_count``
        Storage objects under the sealed prefix. A property of the blob layout.

    ``total_case_count``
        Evaluation cases in the set. A property of the population.

    ``residual_semantic_case_count``
        Cases that remain semantically inadmissible after normalisation.

    ``prediction_stream_count``
        Prediction streams generated against the set.

    ``score_state_object_count``
        Score and state objects written for the set.
    """

    sealed_object_count: int
    total_case_count: int
    residual_semantic_case_count: int
    prediction_stream_count: int = 0
    score_state_object_count: int = 0

    def __post_init__(self) -> None:
        for kind in COUNT_KINDS:
            value = getattr(self, kind)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ContractError(f"{kind} must be a non-negative integer")
        if self.residual_semantic_case_count > self.total_case_count:
            raise ContractError(
                "residual_semantic_case_count cannot exceed total_case_count"
            )

    def to_dict(self) -> dict[str, int]:
        return {kind: getattr(self, kind) for kind in COUNT_KINDS}

    def get(self, kind: str) -> int:
        """Read one count by name, refusing any name outside the vocabulary."""
        if kind not in COUNT_KINDS:
            raise ContractError(f"{kind!r} is not a registered count kind")
        return int(getattr(self, kind))


@dataclass(frozen=True)
class SetSource:
    """The set itself, so that any declared fact can be re-derived from it.

    Every entry point that consumes a facts manifest requires one of these.
    A facts manifest is an operator's *claim* about a set; without the set,
    the claim cannot be checked, and an unchecked claim is precisely what
    produced the parser-v3-v1 gate contract.
    """

    set_id: str
    counts: "SetCounts"
    records: tuple[Mapping[str, Any], ...]
    output_texts: Mapping[str, str]
    members: tuple[Mapping[str, Any], ...] = ()
    gates: tuple[Mapping[str, Any], ...] = ()

    def derive(self) -> dict[str, Any]:
        """Re-derive the facts manifest this set actually supports."""
        return build_set_facts(
            list(self.records),
            dict(self.output_texts),
            set_id=self.set_id,
            members=list(self.members),
            counts=self.counts,
            gates=list(self.gates),
        )


def _require_derivable(
    facts: Mapping[str, Any], set_source: "SetSource"
) -> dict[str, Any]:
    """Require the declared manifest to equal one re-derived from the set."""
    if type(set_source) is not SetSource:
        # Exact type, not isinstance: a subclass overriding `derive` would
        # satisfy an isinstance check and defeat re-derivation entirely,
        # which is the hole this function exists to close.
        raise ContractError(
            "a facts manifest can only be used together with the set it "
            "describes; pass a SetSource"
        )
    verify_facts_integrity(facts)
    derived = build_set_facts(
        set_id=set_source.set_id,
        counts=set_source.counts,
        records=set_source.records,
        output_texts=set_source.output_texts,
        members=set_source.members,
        gates=set_source.gates,
    )
    if _canonical_json(dict(facts)) != _canonical_json(derived):
        raise ContractError(
            "the declared facts manifest is not reproducible from the set it "
            "claims to describe"
        )
    return derived


@dataclass(frozen=True)
class AgreementFinding:

    code: str
    subject: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "subject": self.subject, "message": self.message}


#: How a gate's denominator is selected from the set. A gate whose population
#: cannot be resolved is an error, never an ``NA``.
GATE_POPULATIONS: tuple[str, ...] = (
    "all_cases",
    "critical_cases",
    "clean_cases",
    "stratum",
    "typed_decision_class",
    "answer_presence",
)


def _canonical_json(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def validate_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a prospective evaluation policy in isolation from any set."""
    if not isinstance(policy, Mapping):
        raise ContractError("policy must be an object")
    if policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise ContractError("policy schema version is not recognised")

    ontology = policy.get("ontology")
    if not isinstance(ontology, Mapping):
        raise ContractError("policy.ontology must be an object")
    classes = ontology.get("typed_decision_classes")
    if not isinstance(classes, list) or not classes:
        raise ContractError("policy.ontology.typed_decision_classes must be a list")
    if sorted(classes) != sorted(
        ["present:<canonical_value>", "ambiguous", "no_answer"]
    ):
        raise ContractError(
            "policy.ontology.typed_decision_classes must be exactly the three "
            "formal classes"
        )
    if ontology.get("truth_table_id") != TRUTH_TABLE_ID:
        raise ContractError("policy.ontology.truth_table_id is not the registered table")
    if ontology.get("span_convention") != SPAN_CONVENTION:
        raise ContractError("policy.ontology.span_convention must be literal_only")
    if ontology.get("null_collapse_prohibited") is not True:
        raise ContractError("policy.ontology.null_collapse_prohibited must be true")
    research = ontology.get("research_only_classes") or []
    if sorted(research) != sorted(RESEARCH_ONLY_TYPED_DECISION_CLASSES):
        raise ContractError(
            "policy.ontology.research_only_classes must list the excluded classes"
        )

    population = policy.get("population")
    if not isinstance(population, Mapping):
        raise ContractError("policy.population must be an object")
    total = population.get("total_case_count")
    per_stratum = population.get("cases_per_stratum")
    strata = population.get("strata")
    if not isinstance(strata, list) or sorted(strata) != sorted(frozen.STRATA):
        raise ContractError("policy.population.strata must be the registered strata")
    if not isinstance(total, int) or not isinstance(per_stratum, int):
        raise ContractError("policy.population counts must be integers")
    if total != per_stratum * len(strata):
        raise ContractError("policy.population totals are inconsistent")
    presence = population.get("stratum_presence")
    if presence != dict(STRATUM_PRESENCE):
        raise ContractError(
            "policy.population.stratum_presence must match the public stratum "
            "definitions"
        )
    support = population.get("typed_decision_support")
    if not isinstance(support, Mapping) or sorted(support) != [
        "ambiguous",
        "no_answer",
        "present",
    ]:
        raise ContractError(
            "policy.population.typed_decision_support must cover the three classes"
        )
    derived = _support_from_presence(presence, per_stratum)
    if dict(support) != derived:
        raise ContractError(
            "policy.population.typed_decision_support must be derivable from the "
            f"registered stratum presence; expected {derived}"
        )
    if sum(support.values()) != total:
        raise ContractError("policy.population.typed_decision_support must sum to total")

    gates = policy.get("gates")
    if not isinstance(gates, list) or not gates:
        raise ContractError("policy.gates must be a non-empty list")
    seen: set[str] = set()
    for gate in gates:
        if not isinstance(gate, Mapping):
            raise ContractError("each gate must be an object")
        gate_id = gate.get("gate_id")
        if not isinstance(gate_id, str) or not gate_id:
            raise ContractError("each gate must carry a gate_id")
        if gate_id in seen:
            raise ContractError(f"duplicate gate_id {gate_id!r}")
        seen.add(gate_id)
        if not isinstance(gate.get("mandatory"), bool):
            raise ContractError(f"gate {gate_id} must declare mandatory")
        population_kind = gate.get("population")
        if population_kind not in GATE_POPULATIONS:
            raise ContractError(f"gate {gate_id} has an unregistered population")
        if population_kind in ("stratum", "typed_decision_class", "answer_presence"):
            selector = gate.get("population_selector")
            if not isinstance(selector, str) or not selector:
                raise ContractError(f"gate {gate_id} needs a population_selector")
        if not isinstance(gate.get("minimum_denominator"), int):
            raise ContractError(f"gate {gate_id} must declare minimum_denominator")
        if gate["minimum_denominator"] < 1 and gate["mandatory"]:
            raise ContractError(
                f"gate {gate_id} is mandatory and must require a non-zero denominator"
            )
        _validate_gate_semantics(gate)

    # The single production coverage derivation. Everything downstream - the
    # residual criterion's population, the declared coverage block, and the
    # compiled contract - reads from here.
    coverage = derive_gate_coverage(policy)
    _check_declared_coverage(policy, coverage)

    thresholds = policy.get("acceptance_thresholds")
    non_binding = validate_acceptance_thresholds(
        thresholds, coverage=coverage, cases_per_stratum=per_stratum
    )

    # A metric that was removed, merged away, or demoted to report-only must
    # not be reachable from the PASS/FAIL logic under any spelling. Audit
    # finding B5: restricting this to string clauses under two fixed keys meant
    # a list, a nested object, or an extra outcome key bypassed it entirely.
    status_logic = policy.get("status_logic") or {}
    if not isinstance(status_logic, Mapping):
        raise ContractError("policy.status_logic must be an object")
    reserved_keys = {"non_binding_rule", "note", "notes"}
    comparator_names = _registered_comparator_names(policy)
    for outcome, clause in sorted(status_logic.items()):
        if outcome in reserved_keys:
            continue
        for text in _collect_clause_text(clause):
            for threshold_id in sorted(non_binding):
                if threshold_id in text:
                    raise ContractError(
                        f"status_logic.{outcome} references {threshold_id!r}, which "
                        "is not a binding criterion; a report-only or removed metric "
                        "must never re-enter PASS/FAIL logic"
                    )
            if outcome in ("PASS", "FAIL", "INVALID", "binding_criteria"):
                for comparator in sorted(comparator_names):
                    if re.search(rf"\b{re.escape(comparator)}\b", text):
                        raise ContractError(
                            f"status_logic.{outcome} references the registered "
                            f"comparator {comparator!r}; comparator output is "
                            "reported alongside the result and never inside it"
                        )

    # ``binding_criteria`` is a declaration, so it is checked against the set
    # the validator actually computed rather than trusted. An empty list, a
    # stale identifier, or a renamed criterion would otherwise leave the
    # document claiming a binding set the policy does not have. Audit finding
    # A4/B8.
    declared_binding = status_logic.get("binding_criteria")
    if not isinstance(declared_binding, list) or not declared_binding:
        raise ContractError(
            "policy.status_logic.binding_criteria must list the binding criteria; "
            "a FINAL policy whose PASS reduces to the mandatory gates leaves the "
            "residual population unconstrained"
        )
    computed_binding = {
        item["threshold_id"]
        for item in thresholds.get("items", [])
        if item.get("binding") is True
    }
    if set(declared_binding) != computed_binding:
        raise ContractError(
            f"policy.status_logic.binding_criteria declares "
            f"{sorted(declared_binding)} but the binding criteria are "
            f"{sorted(computed_binding)}"
        )

    status = policy.get("status")
    if status not in ("FINAL", "REVIEW_REQUIRED"):
        raise ContractError("policy.status is not recognised")
    if thresholds.get("status") == "REVIEW_REQUIRED" and status != "REVIEW_REQUIRED":
        raise ContractError(
            "a policy with unresolved thresholds cannot declare itself FINAL"
        )

    _validate_comparators(policy, non_binding)
    _validate_policy_top_level(policy)
    _validate_execution_state(policy)
    _reject_superseded_figures(policy, coverage)
    return dict(policy)


#: Comparator fields that would turn reported context back into a criterion.
#: ``binding`` is checked separately because ``False`` is its correct value,
#: while for these fields any value at all - including ``0``, which is a real
#: margin - reintroduces a criterion.
_COMPARATOR_CRITERION_FIELDS: tuple[str, ...] = (
    "margin",
    "minimum_margin",
    "required_margin",
    "acceptance_margin",
    "threshold",
    "minimum",
    "maximum",
    "pass_condition",
    "fail_condition",
)


def _registered_comparator_names(policy: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the registered comparator names, or ``()`` if none are declared.

    Read defensively: this is used by the status-logic check, which must keep
    working on a malformed comparator block long enough for the comparator
    validator to produce the better error message.
    """
    comparators = policy.get("comparators")
    if not isinstance(comparators, Mapping):
        return ()
    registered = comparators.get("registered_comparators")
    if not isinstance(registered, list):
        return ()
    return tuple(name for name in registered if isinstance(name, str) and name)


def _validate_comparators(
    policy: Mapping[str, Any], non_binding: set[str]
) -> None:
    """Require the comparator block to be report-only, and structurally so.

    Phase 1.2G. A comparator is informative for a reader and for error
    analysis, but its value is not derivable before either parser is run on the
    locked set, so it can carry no acceptance weight. The check is structural
    rather than a promise in prose.
    """
    comparators = policy.get("comparators")
    if not isinstance(comparators, Mapping):
        raise ContractError("policy.comparators must be an object")
    if comparators.get("role") != "REPORT_ONLY":
        raise ContractError(
            "policy.comparators.role must be REPORT_ONLY; a comparator result "
            "cannot make a parser that violates an absolute gate acceptable"
        )
    if comparators.get("status") != "FINAL":
        raise ContractError(
            "policy.comparators.status must be FINAL; the comparator's role is "
            "decided even though no comparator has been run"
        )
    if comparators.get("execution_status") != "NOT_RUN":
        raise ContractError(
            "policy.comparators.execution_status must be NOT_RUN; no comparator "
            "has been run on any locked set"
        )
    if comparators.get("binding") is not False:
        raise ContractError(
            "policy.comparators must explicitly declare itself binding=false"
        )
    for field in _COMPARATOR_CRITERION_FIELDS:
        # ``is not None`` rather than a truth test: a margin of 0 is a real
        # margin, and ``0 == False`` in Python would have let it through.
        if comparators.get(field) is not None:
            raise ContractError(
                f"policy.comparators.{field} is set; a report-only comparator "
                "must carry no numeric margin and no pass condition"
            )
    registered = comparators.get("registered_comparators")
    if not isinstance(registered, list):
        raise ContractError(
            "policy.comparators.registered_comparators must be a list"
        )
    purposes = comparators.get("comparator_purposes")
    if not isinstance(purposes, Mapping) or sorted(purposes) != sorted(registered):
        raise ContractError(
            "every registered comparator must declare a distinct report-only "
            "purpose; an unexplained comparator in the live registry invites "
            "informal gating"
        )
    for name in sorted(registered):
        text = purposes[name]
        if not isinstance(text, str) or not text.strip():
            raise ContractError(f"comparator {name} must declare a non-empty purpose")


def _is_zero_count(value: Any) -> bool:
    """True only for a genuine integer zero.

    Third re-review finding R3-NEW-05: the earlier guard tested ``value != 0``,
    which accepts ``0.0`` and ``Decimal(0)``. A count is an integer, and a
    policy that records a float count is malformed whatever it evaluates to.
    ``bool`` is excluded because ``False == 0``.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value == 0


#: Counters that a FINAL policy must carry and must state as integer zero.
EXECUTION_STATE_ZERO_COUNTS: tuple[str, ...] = (
    "predictions_generated",
    "locked_label_reads",
    "parser_v3_runs_against_any_locked_set",
    "parser_v3_v2_sealed_sets_constructed",
)

#: The complete permitted key set of the policy document itself.
#:
#: Audit G finding G-04: only ``execution_state`` was closed, so
#: ``policy["parser_v3_v2_evaluations_run"] = 1`` sat at the *top* level and
#: ``validate_policy`` accepted it. Closing one nested block while leaving its
#: parent open moves the defect rather than fixing it.
POLICY_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "policy_id",
        "status",
        "phase",
        "supersedes",
        "does_not_supersede",
        "purpose",
        "errata",
        "post_hoc_disclosure",
        "ontology",
        "population",
        "gates",
        "gate_coverage_analysis",
        "acceptance_thresholds",
        "comparators",
        "status_logic",
        "provenance",
        "gates_error_semantics",
        "confusion_matrix_analysis_summary",
        "canonical_source_of_truth",
        "execution_state",
    }
)

#: Claims the ``final_policy_is_not_a_result`` statement may never make. The
#: field is free text so that it can be written clearly, but free text is how
#: Audit G turned it into "A formal evaluation was run and parser v3 was
#: validated." while every counter stayed zero.
_FORBIDDEN_RESULT_CLAIMS: tuple[tuple[str, str], ...] = (
    (r"\bevaluation\s+was\s+run\b", "asserts that an evaluation was run"),
    (r"\bwas\s+(?:formally\s+)?evaluated\b", "asserts that an evaluation occurred"),
    (r"\bparser\s+v3\s+(?:was|is)\s+validated\b", "asserts parser-v3 validation"),
    (r"\bhas\s+been\s+validated\b", "asserts validation"),
    (r"\bis\s+(?:now\s+)?(?:accepted|non-regressive|fit for)\b", "asserts acceptance"),
    (r"\bpredictions?\s+(?:were|was)\s+generated\b", "asserts prediction generation"),
)

#: Statements the field must make. Requiring them means the sentence cannot be
#: emptied out into something vacuously true.
_REQUIRED_RESULT_DISCLAIMERS: tuple[tuple[str, str], ...] = (
    (r"\bparser v3 remains unvalidated\b", "parser v3 remains unvalidated"),
    (r"\bno evaluation has been run\b", "no evaluation has been run"),
)

#: The complete permitted key set of ``policy.execution_state``. Closed by
#: finding R3-NEW-05 so that an unrecognised counter cannot assert an execution
#: alongside the validated zeros.
EXECUTION_STATE_KEYS: frozenset[str] = frozenset(
    {
        "formal_evaluation_execution_state",
        "formal_evaluation_ordinal",
        "final_policy_is_not_a_result",
        *EXECUTION_STATE_ZERO_COUNTS,
    }
)


def _validate_execution_state(policy: Mapping[str, Any]) -> None:
    """Require the policy to state, machine-readably, that nothing has run.

    A FINAL policy is a decision about how a future evaluation will be judged.
    It is not a result. Recording the execution state next to the policy status
    is what stops the first from being read as the second.

    Audit E re-review finding R3-NEW-05: validating only the *named* counters
    left the block open. ``"parser_v3_v2_evaluations_run": 1`` sat next to the
    zeroed fields and every check passed, so the policy could assert an
    execution that the contract was written to forbid. The key set is therefore
    closed: an unrecognised counter is a defect, not a free-text annotation.
    Widening it is a deliberate edit to this list, which is the point.
    """
    execution = policy.get("execution_state")
    if not isinstance(execution, Mapping):
        raise ContractError(
            "policy.execution_state must be an object; a FINAL policy must state "
            "that no evaluation has occurred"
        )
    unknown = sorted(set(execution) - EXECUTION_STATE_KEYS)
    if "sealed_sets_constructed" in execution:
        raise ContractError(
            "policy.execution_state.sealed_sets_constructed is unscoped and "
            "contradicts parser-v3-v1 having been sealed; use "
            "parser_v3_v2_sealed_sets_constructed"
        )
    if unknown:
        raise ContractError(
            "policy.execution_state carries unrecognised field(s) "
            f"{unknown}; the execution-state block is a closed schema so that "
            "an unvalidated counter cannot assert an execution beside the "
            "zeroed ones"
        )
    missing = sorted(EXECUTION_STATE_KEYS - set(execution))
    if missing:
        raise ContractError(
            f"policy.execution_state is missing required field(s) {missing}"
        )
    if execution.get("formal_evaluation_execution_state") != "NOT_RUN":
        raise ContractError(
            "policy.execution_state.formal_evaluation_execution_state must be "
            "NOT_RUN"
        )
    ordinal = execution.get("formal_evaluation_ordinal")
    if not _is_zero_count(ordinal):
        raise ContractError(
            "policy.execution_state.formal_evaluation_ordinal must be 0"
        )
    for field in EXECUTION_STATE_ZERO_COUNTS:
        if field not in execution:
            raise ContractError(
                f"policy.execution_state.{field} is required; a FINAL policy "
                f"must state it explicitly rather than leave it unstated"
            )
        if not _is_zero_count(execution[field]):
            raise ContractError(f"policy.execution_state.{field} must be 0")
    note = execution.get("final_policy_is_not_a_result")
    if not isinstance(note, str) or not note.strip():
        raise ContractError(
            "policy.execution_state must state that a FINAL policy is not a "
            "parser validation result"
        )
    for pattern, description in _FORBIDDEN_RESULT_CLAIMS:
        if re.search(pattern, note, re.IGNORECASE):
            raise ContractError(
                "policy.execution_state.final_policy_is_not_a_result "
                f"{description}; this field records that the policy is not a "
                "result and may not be used to assert one"
            )
    for pattern, description in _REQUIRED_RESULT_DISCLAIMERS:
        if not re.search(pattern, note, re.IGNORECASE):
            raise ContractError(
                "policy.execution_state.final_policy_is_not_a_result must state "
                f"that {description}"
            )


def _validate_policy_top_level(policy: Mapping[str, Any]) -> None:
    """Reject any top-level key the schema does not define.

    Audit G finding G-04. A top-level ``parser_v3_v2_evaluations_run`` passed
    every check because validation only ever descended into blocks it already
    knew about. An unrecognised key at the root is a defect for the same reason
    it is inside ``execution_state``: nothing validates it, and it reads as
    though it were part of the policy.
    """

    unknown = sorted(set(policy) - POLICY_TOP_LEVEL_KEYS)
    if unknown:
        raise ContractError(
            f"policy carries unrecognised top-level field(s) {unknown}; the "
            "policy schema is closed so that an unvalidated field cannot assert "
            "an execution, a threshold or a result beside the validated ones"
        )


#: Subtrees whose whole purpose is to quote a superseded figure. Scanning them
#: would make an erratum unwritable, which is how the Phase 1.2E record became
#: false in the first place.
_HISTORICAL_KEYS: frozenset[str] = frozenset(
    {
        "errata",
        "superseded_figures",
        "withdrawn_arguments",
        "withdrawn_argument",
        "as_written",
        "historical_note",
        "historical_notes",
        "supersedes",
        "corrections",
        "previous",
    }
)


def _reject_superseded_figures(
    policy: Mapping[str, Any], coverage: GateCoverage
) -> None:
    """Reject live prose still asserting the superseded coverage figures.

    Phase 1.2G seed defects G-01 and G-02. The corrected split is derived above;
    this stops a document from quietly reasserting the old one outside an
    explicitly historical subtree.
    """
    pinned = coverage.pinned_case_count
    residual = coverage.residual_case_count
    total = coverage.total_case_count
    patterns = (
        (
            rf"\b(?!{pinned}\b)\d+\s+of\s+{total}\b\s+exact",
            "a pinned-coverage figure other than the derived one",
        ),
        (
            r"\bresidual\s+(?:critical\s+)?strata\s+are\s+S04,?\s*S05\s+and\s+S09\b",
            "the superseded three-stratum residual population",
        ),
        (
            rf"\bresidual\s+population\s+of\s+(?!{residual}\b)\d+\s+cases\b",
            "a residual case count other than the derived one",
        ),
    )

    def walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                if key in _HISTORICAL_KEYS:
                    continue
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")
        elif isinstance(node, str):
            collapsed = re.sub(r"\s+", " ", node)
            for pattern, description in patterns:
                if re.search(pattern, collapsed, flags=re.IGNORECASE):
                    raise ContractError(
                        f"policy{path} restates {description}; the gates derive "
                        f"{pinned} pinned and {residual} residual cases"
                    )

    walk(policy, "")


def _support_from_presence(
    presence: Mapping[str, str], cases_per_stratum: int
) -> dict[str, int]:
    support = {"present": 0, "no_answer": 0, "ambiguous": 0}
    for value in presence.values():
        support[value] += cases_per_stratum
    return support


def build_set_facts(
    records: Sequence[Mapping[str, Any]],
    output_texts: Mapping[str, str],
    *,
    set_id: str,
    members: Sequence[Mapping[str, Any]],
    counts: SetCounts,
    gates: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Mechanically derive the facts manifest for a candidate set.

    ``derive from the set`` means exactly this: reproduce and verify what the
    set contains. It never means rewriting a prospective quota to match an
    observed distribution.
    """
    if counts.get("total_case_count") != len(records):
        raise ContractError(
            "total_case_count must equal the number of cases in the set"
        )
    try:
        case_facts = validate_ontology_set(
            list(records),
            output_texts,
            total_case_count=counts.get("total_case_count"),
            cases_per_stratum=counts.get("total_case_count") // len(frozen.STRATA),
        )
    except OntologyError as error:
        raise ContractError(f"set is not admissible to the formal ontology: {error}")

    vocabulary = sorted({fact["typed_decision_class"] for fact in case_facts})
    support = {name: 0 for name in ("present", "no_answer", "ambiguous")}
    stratum_support: dict[str, int] = {stratum: 0 for stratum in frozen.STRATA}
    for fact in case_facts:
        support[fact["typed_decision_class"]] += 1
        stratum_support[fact["stratum"]] += 1

    normalized_members = _normalize_members(members)
    denominators = {
        gate["gate_id"]: _denominator(gate, case_facts) for gate in gates
    }

    facts = {
        "schema_version": FACTS_SCHEMA_VERSION,
        "set_id": set_id,
        "counts": counts.to_dict(),
        "observed_typed_decision_vocabulary": vocabulary,
        "observed_typed_decision_support": support,
        "observed_stratum_support": stratum_support,
        "observed_span_convention": SPAN_CONVENTION,
        "observed_critical_case_count": sum(
            1 for fact in case_facts if fact["critical_case"]
        ),
        "gate_denominators": denominators,
        "members": normalized_members,
        "member_object_count": len(normalized_members),
        "case_fact_digest": _digest(case_facts),
        # A digest of the *set*, not of this manifest. Digesting the manifest
        # with itself would only certify that the manifest is self-consistent,
        # which a fabricated manifest also is.
        "set_sha256": set_content_digest(records, output_texts),
    }
    facts["facts_sha256"] = _digest(facts)
    return facts


def set_content_digest(
    records: Sequence[Mapping[str, Any]], output_texts: Mapping[str, str]
) -> str:
    """Digest the set itself: every label record and every locked output.

    Content-free to publish -- a digest discloses nothing -- but it is a real
    commitment, so a facts manifest carrying it cannot be detached from the set
    it claims to describe.
    """
    payload = []
    for record in sorted(records, key=lambda item: str(item.get("case_id"))):
        case_id = str(record.get("case_id"))
        payload.append([case_id, record, output_texts.get(case_id)])
    return _digest(payload)


def seal_facts(facts: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute a manifest's integrity seal.

    Re-sealing makes a manifest internally consistent again; it does *not*
    make it true. Reproducibility against the set is checked separately, and
    is the check that matters.
    """
    unsealed = {key: value for key, value in facts.items() if key != "facts_sha256"}
    sealed = dict(unsealed)
    sealed["facts_sha256"] = _digest(unsealed)
    return sealed


def verify_facts_integrity(facts: Mapping[str, Any]) -> None:
    """Reject a facts manifest that was hand-authored or edited after derivation.

    This does not, by itself, prove the manifest describes a real set -- only
    re-derivation via :func:`build_set_facts` does that, which is why every
    entry point requires a :class:`SetSource`. It closes the weaker hole of a
    manifest whose fields were altered after being derived.
    """
    if facts.get("schema_version") != FACTS_SCHEMA_VERSION:
        raise ContractError("facts schema version is not recognised")
    seal = facts.get("facts_sha256")
    if not isinstance(seal, str) or len(seal) != 64:
        raise ContractError("facts manifest carries no integrity seal")
    unsealed = {key: value for key, value in facts.items() if key != "facts_sha256"}
    if _digest(unsealed) != seal:
        raise ContractError(
            "facts manifest does not match its own integrity seal; it was "
            "edited after derivation"
        )
    counts = facts.get("counts")
    if not isinstance(counts, Mapping):
        raise ContractError("facts manifest carries no counts block")
    missing = [kind for kind in COUNT_KINDS if kind not in counts]
    if missing:
        raise ContractError(
            "facts counts omit registered kinds: " + ", ".join(sorted(missing))
        )


def _normalize_members(members: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for member in members:
        if not isinstance(member, Mapping):
            raise ContractError("each member must be an object")
        name = member.get("name")
        sha256 = member.get("sha256")
        size = member.get("bytes")
        if not isinstance(name, str) or not name:
            raise ContractError("each member must carry a name")
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise ContractError(f"member {name} must carry a sha256 digest")
        if any(character not in "0123456789abcdef" for character in sha256):
            raise ContractError(
                f"member {name} digest must be lowercase hexadecimal"
            )
        if not isinstance(size, int) or size < 0:
            raise ContractError(f"member {name} must carry a byte count")
        if name in seen:
            raise ContractError(f"duplicate member {name}")
        seen.add(name)
        normalized.append({"name": name, "sha256": sha256, "bytes": size})
    normalized.sort(key=lambda item: item["name"])
    return normalized


def _denominator(gate: Mapping[str, Any], case_facts: Sequence[Mapping[str, Any]]) -> int:
    kind = gate.get("population")
    selector = gate.get("population_selector")
    if kind == "all_cases":
        return len(case_facts)
    if kind == "critical_cases":
        return sum(1 for fact in case_facts if fact["critical_case"])
    if kind == "clean_cases":
        return sum(1 for fact in case_facts if not fact["critical_case"])
    if kind == "stratum":
        return sum(1 for fact in case_facts if fact["stratum"] == selector)
    if kind == "typed_decision_class":
        return sum(1 for fact in case_facts if fact["typed_decision_class"] == selector)
    if kind == "answer_presence":
        return sum(1 for fact in case_facts if fact["answer_presence"] == selector)
    raise ContractError(f"gate {gate.get('gate_id')!r} has an unregistered population")


def check_agreement(
    policy: Mapping[str, Any],
    facts: Mapping[str, Any],
    *,
    set_source: SetSource,
    expected_members: Sequence[str] | None = None,
) -> list[AgreementFinding]:
    """Compare a prospective policy against a set-derived facts manifest.

    Returns every disagreement found. An empty list is the only result that
    permits compilation. Finding codes reuse the Phase 1.2D defect labels so
    that each historical defect has a mechanical detector.

    ``set_source`` is mandatory: the manifest is first required to be
    reproducible from the set it describes, so a fabricated or edited manifest
    is rejected before any comparison is attempted.
    """
    validate_policy(policy)
    facts = _require_derivable(facts, set_source)
    return agreement_findings(policy, facts, expected_members=expected_members)


def agreement_findings(
    policy: Mapping[str, Any],
    facts: Mapping[str, Any],
    *,
    expected_members: Sequence[str] | None = None,
) -> list[AgreementFinding]:
    """The pure comparison, with no provenance check.

    Not exported in ``__all__``. It is deliberately *not* an entry point: it
    trusts its input, and trusting an unverified manifest is what produced the
    parser-v3-v1 gate contract. It is module-level rather than private only so
    that each detector can be exercised directly against a hand-authored
    manifest in the test suite. Production callers must use
    :func:`check_agreement`, which binds the manifest to the set before calling
    this.

    Several detectors here are redundant backstops rather than the primary
    defence -- ``validate_ontology_set`` already makes a fourth class or a
    malformed stratum count impossible to derive. They are kept because a
    backstop that never fires costs nothing, and the round that removed one
    would be the round it was needed.
    """
    validate_policy(policy)
    if facts.get("schema_version") != FACTS_SCHEMA_VERSION:
        raise ContractError("facts schema version is not recognised")

    findings: list[AgreementFinding] = []
    population = policy["population"]
    ontology = policy["ontology"]

    declared_classes = {"present", "ambiguous", "no_answer"}
    observed_classes = set(facts.get("observed_typed_decision_vocabulary") or [])
    extra = sorted(observed_classes - declared_classes)
    if extra:
        findings.append(
            AgreementFinding(
                "H8",
                "typed_decision_vocabulary",
                f"set uses classes outside the formal ontology: {extra}",
            )
        )
    missing = sorted(declared_classes - observed_classes)
    if missing:
        findings.append(
            AgreementFinding(
                "H9",
                "typed_decision_vocabulary",
                f"policy declares classes the set never exercises: {missing}",
            )
        )

    expected_support = dict(population["typed_decision_support"])
    observed_support = dict(facts.get("observed_typed_decision_support") or {})
    if expected_support != observed_support:
        findings.append(
            AgreementFinding(
                "H9",
                "typed_decision_support",
                f"policy declares {expected_support} but the set contains "
                f"{observed_support}",
            )
        )

    per_stratum = population["cases_per_stratum"]
    observed_strata = dict(facts.get("observed_stratum_support") or {})
    bad_strata = {
        stratum: count
        for stratum, count in sorted(observed_strata.items())
        if count != per_stratum
    }
    if bad_strata:
        findings.append(
            AgreementFinding(
                "H9",
                "stratum_support",
                f"strata must each hold {per_stratum} cases; found {bad_strata}",
            )
        )

    counts = dict(facts.get("counts") or {})
    if policy["ontology"].get("truth_table_id") != TRUTH_TABLE_ID:
        findings.append(
            AgreementFinding(
                "H2",
                "truth_table_id",
                f"policy is written against truth table "
                f"{policy['ontology'].get('truth_table_id')!r} but the set was "
                f"validated against {TRUTH_TABLE_ID!r}",
            )
        )
    if counts.get("total_case_count") != population["total_case_count"]:
        findings.append(
            AgreementFinding(
                "H2",
                "total_case_count",
                "set case count disagrees with the registered population",
            )
        )
    if "residual_semantic_case_count" not in counts:
        findings.append(
            AgreementFinding(
                "H8",
                "residual_semantic_case_count",
                "the set declares no residual-case count; absence is not zero",
            )
        )
    elif counts["residual_semantic_case_count"] > 0:
        findings.append(
            AgreementFinding(
                "H8",
                "residual_semantic_case_count",
                "the set still contains semantically inadmissible cases",
            )
        )

    if facts.get("observed_span_convention") != ontology["span_convention"]:
        findings.append(
            AgreementFinding(
                "H5",
                "span_convention",
                "set span convention disagrees with the registered convention",
            )
        )

    denominators = dict(facts.get("gate_denominators") or {})
    for gate in policy["gates"]:
        gate_id = gate["gate_id"]
        if gate_id not in denominators:
            findings.append(
                AgreementFinding(
                    "H3",
                    f"gate:{gate_id}",
                    "gate has no denominator derived from the set",
                )
            )
            continue
        denominator = denominators[gate_id]
        if not isinstance(denominator, int):
            findings.append(
                AgreementFinding(
                    "H3", f"gate:{gate_id}", "gate denominator is not an integer"
                )
            )
            continue
        if gate["mandatory"] and denominator < 1:
            findings.append(
                AgreementFinding(
                    "H3",
                    f"gate:{gate_id}",
                    "mandatory gate has a zero denominator and would be vacuous",
                )
            )
        elif denominator < gate["minimum_denominator"]:
            findings.append(
                AgreementFinding(
                    "H3",
                    f"gate:{gate_id}",
                    f"gate denominator {denominator} is below its registered "
                    f"minimum {gate['minimum_denominator']}",
                )
            )

    if expected_members is not None:
        observed_names = [member["name"] for member in facts.get("members") or []]
        if sorted(observed_names) != sorted(expected_members):
            findings.append(
                AgreementFinding(
                    "H1",
                    "membership",
                    "set membership disagrees with the expected object layout",
                )
            )
    declared_objects = counts.get("sealed_object_count")
    observed_objects = facts.get("member_object_count")
    if (
        isinstance(declared_objects, int)
        and isinstance(observed_objects, int)
        and declared_objects != observed_objects
    ):
        findings.append(
            AgreementFinding(
                "H1",
                "sealed_object_count",
                f"declared {declared_objects} storage objects but enumerated "
                f"{observed_objects}",
            )
        )

    return findings


def compile_contract(
    policy: Mapping[str, Any],
    facts: Mapping[str, Any],
    *,
    set_source: SetSource,
    expected_members: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Emit the final acceptance contract, or refuse.

    Refuses when the policy is not ``FINAL``, when any threshold is still
    ``REVIEW_REQUIRED``, when the facts manifest is not reproducible from
    ``set_source``, or when any declared invariant disagrees with the set.
    """
    validate_policy(policy)
    coverage = derive_gate_coverage(policy)
    if policy["status"] != "FINAL":
        raise ContractError(
            f"policy status is {policy['status']!r}; a contract can only be "
            "compiled from a FINAL policy"
        )
    if policy["acceptance_thresholds"]["status"] != "FINAL":
        raise ContractError(
            "acceptance thresholds are REVIEW_REQUIRED; thresholds must be "
            "resolved before compilation and must never be chosen to fit a set"
        )
    findings = check_agreement(
        policy, facts, set_source=set_source, expected_members=expected_members
    )
    if findings:
        raise ContractError(
            "policy and set disagree: "
            + "; ".join(f"{item.code} {item.subject}" for item in findings)
        )

    contract = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "compiled_from": {
            "policy_id": policy.get("policy_id"),
            "policy_schema_version": policy["schema_version"],
            "policy_sha256": _digest(policy),
            "facts_schema_version": facts["schema_version"],
            "facts_sha256": facts["facts_sha256"],
            "set_id": facts["set_id"],
            "set_sha256": facts["set_sha256"],
            "truth_table_id": policy["ontology"]["truth_table_id"],
        },
        "ontology": dict(policy["ontology"]),
        "population": dict(policy["population"]),
        "counts": dict(facts["counts"]),
        "gates": [
            {
                **dict(gate),
                "denominator": facts["gate_denominators"][gate["gate_id"]],
            }
            for gate in policy["gates"]
        ],
        "acceptance_thresholds": dict(policy["acceptance_thresholds"]),
        "gate_coverage": coverage.as_dict(),
        "status_logic": dict(policy.get("status_logic") or {}),
        "comparators": dict(policy.get("comparators") or {}),
        "members": list(facts["members"]),
    }
    contract["contract_sha256"] = _digest(contract)
    return contract


def render_contract(contract: Mapping[str, Any]) -> bytes:
    """Render a contract to its canonical, byte-stable form."""
    return _canonical_json(contract)


def write_contract(path: str | Path, contract: Mapping[str, Any]) -> Path:
    """Write a compiled contract, refusing to overwrite an existing artifact."""
    target = Path(path)
    if target.exists():
        raise ContractError(
            f"{target} already exists; a compiled contract is never amended in place"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(render_contract(contract))
    return target


def check_contract(
    path: str | Path,
    policy: Mapping[str, Any],
    facts: Mapping[str, Any],
    *,
    set_source: SetSource,
    expected_members: Sequence[str] | None = None,
) -> None:
    """Re-derive a contract and require byte-for-byte reproduction."""
    target = Path(path)
    if not target.exists():
        raise ContractError(f"{target} does not exist")
    recompiled = render_contract(
        compile_contract(
            policy, facts, set_source=set_source, expected_members=expected_members
        )
    )
    if target.read_bytes() != recompiled:
        raise ContractError(
            f"{target} is not byte-identical to a fresh compilation of its inputs"
        )
