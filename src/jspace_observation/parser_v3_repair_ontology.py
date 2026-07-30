"""Parser-v3 evaluation ontology: the formal three-class contract and its validator.

Phase 1.2E. This module exists because Phase 1.2D discovered that the sealed
``parser-v3-v1`` set, the frozen scoring instrument and the parser-v3 gate
contract described three different things (findings ``H1``-``H9``).

Nothing here reads a private set, a sealed blob, or a locked label, and nothing
here imports or invokes a parser. It defines the ontology a future
``parser-v3-v2`` set must satisfy, and validates candidate records against it.

The vocabulary is reused from :mod:`jspace_observation.evaluator_validation`
rather than restated, so that a record admitted here is admissible to the
instrument that would score it. That reuse is the point: ``H5`` existed because
the set registered spans the scoring instrument would have rejected.

Public sources of truth for the rules encoded here:

``docs/phase1_parser_v3_v2_stratum_policy.md``
    Stratum roles, the registered presence of each stratum, the 12 x 10
    population, the clean/critical split and the cross-cutting quotas. This
    file is public and contains no case text and no labels. Phase 1.2F
    re-derived it under v2 identity; the retired
    ``evaluator_sets/parser_v3_v1/strata_definitions.md`` is design ancestry
    only and is no longer a live binding.

``src/jspace_observation/evaluator_validation.py``
    Enum vocabularies, canonical numeric grammar and span admissibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from . import evaluator_validation as frozen

__all__ = [
    "OntologyError",
    "TYPED_DECISION_CLASSES",
    "RESEARCH_ONLY_TYPED_DECISION_CLASSES",
    "SPAN_CONVENTION",
    "STRATUM_PRESENCE",
    "TRUTH_TABLE_ID",
    "TRUTH_TABLE",
    "TruthTableRow",
    "derive_typed_decision",
    "typed_decision_class",
    "validate_ontology_record",
    "validate_ontology_set",
]


class OntologyError(ValueError):
    """One record, or one set, violates the formal parser-v3 ontology."""


#: The three decisions the candidate parser and the frozen scoring semantics
#: can both represent. ``present`` carries its canonical value.
TYPED_DECISION_CLASSES: tuple[str, ...] = (
    "present:<canonical_value>",
    "ambiguous",
    "no_answer",
)

#: Observed in ``parser-v3-v1`` but deliberately excluded from the formal set.
#: It must never be collapsed into another class; see the Phase 1.2E protocol.
RESEARCH_ONLY_TYPED_DECISION_CLASSES: tuple[str, ...] = ("present_unextractable",)

#: Evidence spans register the numeric literal itself, never an enclosing
#: marker phrase. Chosen because all three parsers emit literal-only spans.
SPAN_CONVENTION = "literal_only"

TRUTH_TABLE_ID = "phase1-parser-v3-v2-three-class-truth-table/v1"

#: Registered answer presence of each stratum, from the public stratum
#: definitions. This single mapping is what makes an ``S10`` case labelled
#: ``present`` a set defect rather than a matter of opinion.
STRATUM_PRESENCE: Mapping[str, str] = {
    "S01": "present",
    "S02": "present",
    "S03": "present",
    "S04": "present",
    "S05": "present",
    "S06": "present",
    "S07": "no_answer",
    "S08": "no_answer",
    "S09": "present",
    "S10": "no_answer",
    "S11": "ambiguous",
    "S12": "present",
}

_PRESENCE_VALUES: tuple[str, ...] = ("present", "ambiguous", "no_answer")

_PRESENT_STRATEGIES: frozenset[str] = frozenset(
    {
        "boxed_answer",
        "explicit_final_marker",
        "explicit_answer_marker",
        "terminal_equation",
        "single_candidate",
    }
)

#: ``present`` requires a recoverable answer, so the two qualities that assert
#: nothing is recoverable are refused.
_PRESENT_QUALITIES: frozenset[str] = frozenset(
    {"complete", "truncated", "malformed_recoverable"}
)

_AMBIGUOUS_QUALITIES: frozenset[str] = frozenset(
    {"complete", "truncated", "malformed_recoverable"}
)

_NO_ANSWER_QUALITIES: frozenset[str] = frozenset(
    {
        "complete",
        "truncated",
        "malformed_recoverable",
        "malformed_unrecoverable",
        "placeholder",
        "empty",
    }
)


@dataclass(frozen=True)
class TruthTableRow:
    """One admissible combination of extraction fields."""

    typed_decision: str
    answer_presence: str
    parse_valid: bool
    parse_ambiguous: bool
    parsed_answer_null: bool
    minimum_candidates: int
    maximum_candidates: int | None
    minimum_spans: int
    maximum_spans: int | None
    required_span_dispositions: tuple[str, ...]
    allowed_extraction_strategies: tuple[str, ...]
    allowed_output_qualities: tuple[str, ...]


TRUTH_TABLE: tuple[TruthTableRow, ...] = (
    TruthTableRow(
        typed_decision="present:<canonical_value>",
        answer_presence="present",
        parse_valid=True,
        parse_ambiguous=False,
        parsed_answer_null=False,
        minimum_candidates=1,
        maximum_candidates=1,
        minimum_spans=1,
        maximum_spans=None,
        required_span_dispositions=("selected",),
        allowed_extraction_strategies=tuple(sorted(_PRESENT_STRATEGIES)),
        allowed_output_qualities=tuple(sorted(_PRESENT_QUALITIES)),
    ),
    TruthTableRow(
        typed_decision="ambiguous",
        answer_presence="ambiguous",
        parse_valid=True,
        parse_ambiguous=True,
        parsed_answer_null=True,
        minimum_candidates=2,
        maximum_candidates=None,
        minimum_spans=2,
        maximum_spans=None,
        required_span_dispositions=("ambiguous_candidate",),
        allowed_extraction_strategies=("ambiguous_candidates",),
        allowed_output_qualities=tuple(sorted(_AMBIGUOUS_QUALITIES)),
    ),
    TruthTableRow(
        typed_decision="no_answer",
        answer_presence="no_answer",
        parse_valid=False,
        parse_ambiguous=False,
        parsed_answer_null=True,
        minimum_candidates=0,
        maximum_candidates=0,
        minimum_spans=0,
        maximum_spans=0,
        required_span_dispositions=(),
        allowed_extraction_strategies=("none",),
        allowed_output_qualities=tuple(sorted(_NO_ANSWER_QUALITIES)),
    ),
)

_ROW_BY_PRESENCE: Mapping[str, TruthTableRow] = {
    row.answer_presence: row for row in TRUTH_TABLE
}


def typed_decision_class(decision: str) -> str:
    """Return the class of one typed decision, without its canonical value."""
    if not isinstance(decision, str) or not decision:
        raise OntologyError("typed decision must be a non-empty string")
    if decision.startswith("present:"):
        return "present"
    if decision in ("ambiguous", "no_answer"):
        return decision
    if decision in RESEARCH_ONLY_TYPED_DECISION_CLASSES:
        raise OntologyError(
            f"typed decision {decision!r} is research-only and is not admissible "
            "to the formal parser-v3 set"
        )
    raise OntologyError(f"typed decision {decision!r} is not in the formal ontology")


def derive_typed_decision(record: Mapping[str, Any]) -> str:
    """Derive the typed decision implied by one record's extraction fields.

    The derivation is total over the formal ontology and refuses anything
    outside it. It never guesses: a record that does not match exactly one
    truth-table row raises rather than being coerced.
    """
    presence = record.get("expected_answer_presence")
    if presence not in _PRESENCE_VALUES:
        raise OntologyError(
            f"expected_answer_presence {presence!r} is not in the formal ontology"
        )
    row = _ROW_BY_PRESENCE[presence]
    if bool(record.get("expected_parse_valid")) is not row.parse_valid:
        raise OntologyError(
            f"{presence} requires expected_parse_valid={row.parse_valid}"
        )
    if bool(record.get("expected_parse_ambiguous")) is not row.parse_ambiguous:
        raise OntologyError(
            f"{presence} requires expected_parse_ambiguous={row.parse_ambiguous}"
        )
    parsed = record.get("expected_parsed_answer")
    if row.parsed_answer_null:
        if parsed is not None:
            raise OntologyError(f"{presence} requires a null expected_parsed_answer")
        return row.typed_decision
    if parsed is None:
        raise OntologyError(
            "present requires a canonical expected_parsed_answer; a present case "
            "with no extractable answer is research-only, not formal"
        )
    canonical = _require_canonical(parsed, "expected_parsed_answer")
    return f"present:{canonical}"


def _require_canonical(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise OntologyError(f"{name} must be a string")
    try:
        canonical = frozen.normalize_rational_literal(value)
    except frozen.ValidationSetError as error:
        raise OntologyError(f"{name} is not a registered numeric literal") from error
    if canonical != value:
        raise OntologyError(f"{name} is not in canonical form")
    return canonical


def _require_enum(value: Any, allowed: Iterable[str], name: str) -> str:
    if value not in tuple(allowed):
        raise OntologyError(f"{name} {value!r} is not an admissible value")
    return str(value)


def _validate_spans(
    spans: Any, output_text: str, row: TruthTableRow, parsed: str | None
) -> list[dict[str, Any]]:
    if not isinstance(spans, list):
        raise OntologyError("expected_evidence_spans must be a list")
    if len(spans) < row.minimum_spans:
        raise OntologyError(
            f"{row.answer_presence} requires at least {row.minimum_spans} evidence spans"
        )
    if row.maximum_spans is not None and len(spans) > row.maximum_spans:
        raise OntologyError(
            f"{row.answer_presence} allows at most {row.maximum_spans} evidence spans"
        )

    checked: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    previous: tuple[int, int] | None = None
    for index, span in enumerate(spans):
        if not isinstance(span, Mapping):
            raise OntologyError(f"evidence span {index} must be an object")
        name = f"expected_evidence_spans[{index}]"
        try:
            # Admissibility is decided by the instrument that would score the
            # set, not by this module. This is what forecloses H5.
            validated = frozen.validate_evidence_span(span, output_text, name=name)
        except frozen.ValidationSetError as error:
            raise OntologyError(
                f"{name} is not admissible to the scoring instrument: {error}"
            ) from error
        literal = output_text[validated["start"] : validated["end"]]
        if validated["text"] != literal:
            raise OntologyError(f"{name} text does not equal its output_text slice")
        if frozen.normalize_rational_literal(validated["text"]) != validated[
            "normalized_answer"
        ]:
            raise OntologyError(
                f"{name} is not literal-only; the registered span convention is "
                f"{SPAN_CONVENTION}"
            )
        key = (validated["start"], validated["end"])
        if key in seen:
            raise OntologyError(f"{name} duplicates an earlier span")
        seen.add(key)
        if previous is not None and key < previous:
            raise OntologyError("expected_evidence_spans must be ordered by offset")
        previous = key
        checked.append(validated)

    if row.required_span_dispositions:
        allowed = set(row.required_span_dispositions)
        if row.answer_presence == "present":
            allowed |= {"equivalent"}
            selected = [
                span for span in checked if span["disposition"] == "selected"
            ]
            if len(selected) != 1:
                raise OntologyError(
                    "present requires exactly one selected evidence span"
                )
            if selected[0]["normalized_answer"] != parsed:
                raise OntologyError(
                    "the selected evidence span must carry the parsed answer"
                )
            if any(span["normalized_answer"] != parsed for span in checked):
                raise OntologyError(
                    "every present evidence span must carry the parsed answer"
                )
        for span in checked:
            if span["disposition"] not in allowed:
                raise OntologyError(
                    f"{row.answer_presence} does not admit a "
                    f"{span['disposition']!r} evidence span"
                )
    return checked


def _validate_candidates(
    candidates: Any, spans: Sequence[Mapping[str, Any]], row: TruthTableRow
) -> list[str]:
    if not isinstance(candidates, list):
        raise OntologyError("expected_candidate_answers must be a list")
    for index, candidate in enumerate(candidates):
        _require_canonical(candidate, f"expected_candidate_answers[{index}]")
    derived: list[str] = []
    for span in spans:
        value = span["normalized_answer"]
        if value not in derived:
            derived.append(value)
    if candidates != derived:
        raise OntologyError(
            "expected_candidate_answers must equal the evidence values in "
            "first-source order"
        )
    distinct = len(set(candidates))
    if distinct < row.minimum_candidates:
        raise OntologyError(
            f"{row.answer_presence} requires at least {row.minimum_candidates} "
            "distinct canonical candidates"
        )
    if row.maximum_candidates is not None and distinct > row.maximum_candidates:
        raise OntologyError(
            f"{row.answer_presence} allows at most {row.maximum_candidates} candidates"
        )
    return list(candidates)


#: The label fields the frozen scoring instrument reads. A record missing any
#: of them cannot be bound to the instrument, and is therefore inadmissible.
_FROZEN_EXTRACTION_FIELDS: tuple[str, ...] = (
    "expected_answer_presence",
    "expected_parse_valid",
    "expected_parse_ambiguous",
    "expected_parsed_answer",
    "expected_candidate_answers",
    "expected_evidence_spans",
    "expected_extraction_strategy",
    "expected_output_quality",
    "expected_failure_reasons",
    "expected_format_warnings",
)


def _bind_to_scoring_instrument(
    record: Mapping[str, Any], output_text: str, typed: str
) -> None:
    """Require the frozen scorer to accept the record and agree on its decision.

    This is the load-bearing anti-H8/H9 check. Every rule above it is a
    restatement, and a restatement can drift away from the instrument it
    paraphrases -- which is exactly how the parser-v3-v1 gate contract came to
    describe a different evaluation problem from the set it scored. Here the
    module stops paraphrasing and *binds*: the instrument that would score the
    set is asked to validate the record and to derive its own typed decision,
    and any disagreement -- in either direction -- invalidates the record.

    A consequence worth stating plainly: this module can no longer admit a
    label the scorer would reject, so an ``UNSCORABLE`` set cannot be built
    from records that pass here.
    """
    missing = [field for field in _FROZEN_EXTRACTION_FIELDS if field not in record]
    if missing:
        raise OntologyError(
            "record omits scoring-instrument fields: " + ", ".join(sorted(missing))
        )
    try:
        frozen._validate_extraction_fields(  # noqa: SLF001
            record, output_text, prefix="expected_", expected=True
        )
        instrument_decision = frozen.derive_typed_decision(record)
    except frozen.ValidationSetError as error:
        raise OntologyError(
            f"the scoring instrument rejects this record: {error}"
        ) from error
    if instrument_decision != typed:
        raise OntologyError(
            "the scoring instrument derives typed decision "
            f"{instrument_decision!r} where this ontology derives {typed!r}"
        )


def validate_ontology_record(
    record: Mapping[str, Any], output_text: str, *, name: str = "record"
) -> dict[str, Any]:
    """Validate one label record against the formal three-class ontology.

    Fails closed. Returns the derived facts a set-facts manifest needs, and
    never returns a partially validated record.
    """
    try:
        return _validate_ontology_record(record, output_text)
    except OntologyError as error:
        raise OntologyError(f"{name}: {error}") from None


def _validate_ontology_record(
    record: Mapping[str, Any], output_text: str
) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise OntologyError("record must be an object")
    if not isinstance(output_text, str):
        raise OntologyError("output_text must be a string")

    case_id = record.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise OntologyError("case_id must be a non-empty string")

    stratum = _require_enum(record.get("stratum"), frozen.STRATA, "stratum")
    presence = record.get("expected_answer_presence")
    if presence not in _PRESENCE_VALUES:
        raise OntologyError(
            f"expected_answer_presence {presence!r} is not in the formal ontology"
        )
    registered = STRATUM_PRESENCE[stratum]
    if presence != registered:
        raise OntologyError(
            f"stratum {stratum} registers answer presence {registered!r}, "
            f"but the record declares {presence!r}"
        )

    row = _ROW_BY_PRESENCE[presence]
    quality = _require_enum(
        record.get("expected_output_quality"),
        frozen.OUTPUT_QUALITIES,
        "expected_output_quality",
    )
    if quality not in row.allowed_output_qualities:
        raise OntologyError(
            f"{presence} does not admit expected_output_quality={quality!r}"
        )
    if (quality == "empty") != (output_text.strip() == ""):
        raise OntologyError(
            "expected_output_quality=empty holds exactly when output_text is "
            "empty after stripping whitespace"
        )

    strategy = _require_enum(
        record.get("expected_extraction_strategy"),
        frozen.EXTRACTION_STRATEGIES,
        "expected_extraction_strategy",
    )
    if strategy not in row.allowed_extraction_strategies:
        raise OntologyError(
            f"{presence} does not admit expected_extraction_strategy={strategy!r}"
        )

    typed = derive_typed_decision(record)
    declared = record.get("typed_decision")
    if declared is not None and declared != typed:
        raise OntologyError(
            "typed_decision disagrees with the extraction fields it must follow"
        )

    parsed = record.get("expected_parsed_answer")
    if parsed is not None:
        parsed = _require_canonical(parsed, "expected_parsed_answer")

    spans = _validate_spans(
        record.get("expected_evidence_spans"), output_text, row, parsed
    )
    candidates = _validate_candidates(
        record.get("expected_candidate_answers"), spans, row
    )
    if parsed is not None and parsed not in candidates:
        raise OntologyError("expected_parsed_answer must appear among the candidates")

    reference = _require_canonical(
        record.get("registered_reference_answer"), "registered_reference_answer"
    )
    correctness = record.get("expected_correctness")
    if not isinstance(correctness, bool):
        raise OntologyError("expected_correctness must be a boolean")
    implied = presence == "present" and parsed == reference
    if correctness is not implied:
        raise OntologyError(
            "expected_correctness must follow exact canonical reference equality"
        )

    critical = record.get("critical_case")
    if not isinstance(critical, bool):
        raise OntologyError("critical_case must be a boolean")
    if critical is not (stratum in frozen.CRITICAL_STRATA):
        raise OntologyError("critical_case disagrees with the stratum's registered role")

    if stratum in frozen.ANSWER_BEARING_STRATA and presence != "present":
        raise OntologyError(
            f"{stratum} is an answer-bearing stratum and must register present"
        )

    _bind_to_scoring_instrument(record, output_text, typed)

    return {
        "case_id": case_id,
        "stratum": stratum,
        "typed_decision": typed,
        "typed_decision_class": typed_decision_class(typed),
        "answer_presence": presence,
        "output_quality": quality,
        "extraction_strategy": strategy,
        "expected_correctness": correctness,
        "critical_case": critical,
        "candidate_count": len(candidates),
        "distinct_candidate_count": len(set(candidates)),
        "span_count": len(spans),
    }


def validate_ontology_set(
    records: Sequence[Mapping[str, Any]],
    output_texts: Mapping[str, str],
    *,
    total_case_count: int = 120,
    cases_per_stratum: int = 10,
) -> list[dict[str, Any]]:
    """Validate a whole candidate set, including its population invariants."""
    if not isinstance(records, Sequence):
        raise OntologyError("records must be a sequence")
    if len(records) != total_case_count:
        raise OntologyError(
            f"set must contain exactly {total_case_count} cases, found {len(records)}"
        )

    seen: set[str] = set()
    facts: list[dict[str, Any]] = []
    per_stratum: dict[str, int] = {stratum: 0 for stratum in frozen.STRATA}
    for record in records:
        case_id = record.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise OntologyError("every case_id must be a non-empty string")
        if case_id in seen:
            raise OntologyError("case_id values must be unique across the set")
        seen.add(case_id)
        if case_id not in output_texts:
            raise OntologyError("every case must have a registered locked input")
        fact = validate_ontology_record(
            record, output_texts[case_id], name=f"case {len(facts)}"
        )
        per_stratum[fact["stratum"]] += 1
        facts.append(fact)

    for stratum in frozen.STRATA:
        if per_stratum[stratum] != cases_per_stratum:
            raise OntologyError(
                f"stratum {stratum} must hold exactly {cases_per_stratum} cases, "
                f"found {per_stratum[stratum]}"
            )
    return facts
