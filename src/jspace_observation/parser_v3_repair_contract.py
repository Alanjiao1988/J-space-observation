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

Nothing here reads a private set, a sealed blob or a locked label, and nothing
here imports or invokes a parser.
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
    "THRESHOLD_BASIS_TYPES",
    "THRESHOLD_DISPOSITIONS",
    "BINDING_DISPOSITIONS",
    "NON_BINDING_DISPOSITIONS",
    "REQUIRED_THRESHOLD_FIELDS",
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


POLICY_SCHEMA_VERSION = "phase1-parser-v3-prospective-evaluation-policy/v2"
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

#: Provenance every gate must declare so that ``maximum_errors`` has a meaning.
REQUIRED_GATE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "error_definition",
    "error_scope",
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
    if not isinstance(boundary.get("at_threshold_passes"), bool):
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
    """
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [text for entry in value.values() for text in _collect_clause_text(entry)]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [text for entry in value for text in _collect_clause_text(entry)]
    if value is None:
        return []
    return [str(value)]


def _validate_gate_semantics(gate: Mapping[str, Any]) -> None:
    """Require every gate to declare what one of its errors is.

    Audit finding A2. Without this, ``maximum_errors: 0`` has no meaning, and
    the coverage baseline that every threshold disposition rests on can be read
    three incompatible ways from the same field.
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
    if gate["error_scope"] not in GATE_ERROR_SCOPES:
        raise ContractError(
            f"gate {gate_id} declares an unrecognised error_scope "
            f"{gate['error_scope']!r}"
        )
    if not isinstance(gate["pins_exact_typed_decision"], bool):
        raise ContractError(
            f"gate {gate_id} must declare pins_exact_typed_decision as a boolean"
        )
    if gate["error_scope"] == "set_level" and gate["pins_exact_typed_decision"]:
        raise ContractError(
            f"gate {gate_id} declares a set-level error scope and cannot pin any "
            "individual case to exact typed-decision agreement"
        )


def validate_acceptance_thresholds(thresholds: Mapping[str, Any]) -> set[str]:
    """Validate the acceptance-threshold block and its provenance.

    Phase 1.2F requirement. A numeric hard threshold is only prospective if it
    can be derived without observing the candidate parser and without observing
    the future holdout, so every FINAL hard threshold must name a recognised
    basis type and carry a complete derivation.

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

    thresholds = policy.get("acceptance_thresholds")
    non_binding = validate_acceptance_thresholds(thresholds)

    # A metric that was removed, merged away, or demoted to report-only must
    # not be reachable from the PASS/FAIL logic under any spelling. Audit
    # finding B5: restricting this to string clauses under two fixed keys meant
    # a list, a nested object, or an extra outcome key bypassed it entirely.
    status_logic = policy.get("status_logic") or {}
    if not isinstance(status_logic, Mapping):
        raise ContractError("policy.status_logic must be an object")
    reserved_keys = {"non_binding_rule", "note", "notes"}
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

    status = policy.get("status")
    if status not in ("FINAL", "REVIEW_REQUIRED"):
        raise ContractError("policy.status is not recognised")
    if thresholds.get("status") == "REVIEW_REQUIRED" and status != "REVIEW_REQUIRED":
        raise ContractError(
            "a policy with unresolved thresholds cannot declare itself FINAL"
        )
    return dict(policy)


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
