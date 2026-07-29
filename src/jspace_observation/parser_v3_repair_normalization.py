"""Deterministic representational normalisations ``N1``-``N6`` for parser-v3 labels.

Phase 1.2E. Phase 1.2D established that 105 of the 120 ``parser-v3-v1`` cases
differ from the frozen scoring instrument only in *representation*, and that six
recorded rewrites reconcile them without changing any typed decision. This
module implements those six rules as pure functions so that a future
``parser-v3-v2`` migration is mechanical, auditable and repeatable.

Design constraints, each of which is enforced by a test:

* deterministic and idempotent;
* typed-decision preserving, or the case is quarantined instead of forced;
* no parser import and no parser invocation;
* no value-bearing logging: the audit receipt carries counts and hashes only;
* fail closed whenever a rule would have to guess outside its registered
  tie-break.

Rules ``N1`` and ``N4`` deliberately delegate to the frozen instrument's own
definition of a registered numeric literal. Restating that definition here
would recreate the class of disagreement that Phase 1.2D found.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from . import evaluator_validation as frozen
from .parser_v3_repair_ontology import OntologyError, validate_ontology_record

__all__ = [
    "NormalizationError",
    "NORMALIZATION_RULES",
    "QuarantineReason",
    "NormalizationReceipt",
    "raw_typed_decision",
    "apply_n1_literal_only_spans",
    "apply_n2_canonical_reference",
    "apply_n3_output_text",
    "apply_n4_last_number_distractor",
    "apply_n5_secondary_tags",
    "apply_n6_candidate_answers",
    "normalize_record",
    "normalize_set",
    "scoring_projection",
    "assert_parser_free_source",
]


class NormalizationError(ValueError):
    """A normalisation rule could not be applied without guessing.

    Carries its own stable ``reason`` code. Classifying a quarantine by
    matching substrings of the message was fragile: any future wording
    containing the matched phrase would be misfiled silently.
    """

    def __init__(self, message: str, *, reason: str = "rule_failed") -> None:
        super().__init__(message)
        self.reason = reason


NORMALIZATION_RULES: tuple[tuple[str, str], ...] = (
    ("N1", "rewrite marker-inclusive evidence spans to the numeric literal"),
    ("N2", "canonicalise the registered reference answer"),
    ("N3", "attach the registered locked output text"),
    ("N4", "register the S06 last-number distractor span"),
    ("N5", "derive the quota-diagnostic secondary tags from content"),
    ("N6", "recompute candidate answers from the evidence spans"),
)


class QuarantineReason:
    """Stable reason codes for cases that must not be migrated mechanically."""

    RESEARCH_ONLY_CLASS = "research_only_class"
    AMBIGUOUS_SPAN_LITERAL = "ambiguous_span_literal"
    NO_SPAN_LITERAL = "no_span_literal"
    MISSING_LOCKED_INPUT = "missing_locked_input"
    DECISION_WOULD_CHANGE = "decision_would_change"
    DISTRACTOR_UNAVAILABLE = "distractor_unavailable"
    CANDIDATE_CARDINALITY = "candidate_cardinality"
    FAILS_ONTOLOGY = "fails_ontology"
    RULE_FAILED = "rule_failed"


@dataclass(frozen=True)
class NormalizationReceipt:
    """Content-free audit record for one normalisation run."""

    input_case_count: int
    normalized_case_count: int
    quarantined_case_count: int
    rule_application_counts: Mapping[str, int]
    quarantine_reason_counts: Mapping[str, int]
    input_digest: str
    output_digest: str
    normalized_content_digest: str
    quarantined_case_id_digest: str
    rules: tuple[tuple[str, str], ...] = field(default=NORMALIZATION_RULES)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "phase1-parser-v3-normalization-receipt/v1",
            "input_case_count": self.input_case_count,
            "normalized_case_count": self.normalized_case_count,
            "quarantined_case_count": self.quarantined_case_count,
            "rule_application_counts": dict(sorted(self.rule_application_counts.items())),
            "quarantine_reason_counts": dict(
                sorted(self.quarantine_reason_counts.items())
            ),
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
            "normalized_content_digest": self.normalized_content_digest,
            "quarantined_case_id_digest": self.quarantined_case_id_digest,
            "rules": [{"rule": rule, "effect": effect} for rule, effect in self.rules],
        }


def _digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return frozen.normalize_rational_literal(value)
    except frozen.ValidationSetError:
        return None


def raw_typed_decision(record: Mapping[str, Any]) -> str:
    """Return the decision a record asserts, including research-only classes.

    This is the pre-image used for the typed-decision preservation check. It
    recognises ``present_unextractable`` explicitly so that such a case is
    quarantined rather than silently reinterpreted.
    """
    presence = record.get("expected_answer_presence")
    if presence == "no_answer":
        return "no_answer"
    if presence == "ambiguous":
        return "ambiguous"
    if presence == "present":
        parsed = record.get("expected_parsed_answer")
        if not record.get("expected_parse_valid") or parsed is None:
            return "present_unextractable"
        canonical = _canonical(parsed)
        if canonical is None:
            raise NormalizationError(
                "present case carries a non-numeric parsed answer",
                reason=QuarantineReason.RULE_FAILED,
            )
        return f"present:{canonical}"
    raise NormalizationError(
        f"answer presence {presence!r} has no recognised typed decision"
    )


def _contained_matches(output_text: str, start: int, end: int) -> list[Any]:
    return [
        match
        for match in frozen._registered_numeric_matches(output_text)
        if match.start() >= start and match.end() <= end
    ]


def apply_n1_literal_only_spans(
    record: Mapping[str, Any], output_text: str
) -> dict[str, Any]:
    """``N1``: rewrite each evidence span to the numeric literal it contains.

    A span already registering exactly its literal is left untouched, which is
    what makes the rule idempotent.
    """
    spans = record.get("expected_evidence_spans")
    if spans is None:
        return dict(record)
    if not isinstance(spans, list):
        raise NormalizationError("expected_evidence_spans must be a list")

    rewritten: list[dict[str, Any]] = []
    for index, span in enumerate(spans):
        if not isinstance(span, Mapping):
            raise NormalizationError(f"evidence span {index} must be an object")
        updated = dict(span)
        start, end = span.get("start"), span.get("end")
        if not isinstance(start, int) or not isinstance(end, int) or start >= end:
            raise NormalizationError(f"evidence span {index} has invalid offsets")
        declared = span.get("normalized_answer")
        text = output_text[start:end]
        if _canonical(text) is not None and _canonical(text) == declared:
            rewritten.append(updated)
            continue
        contained = _contained_matches(output_text, start, end)
        if not contained:
            raise NormalizationError(
                f"evidence span {index} contains no registered numeric literal",
                reason=QuarantineReason.NO_SPAN_LITERAL,
            )
        exact = [m for m in contained if _canonical(m.group(0)) == declared]
        if exact:
            chosen = exact[-1]
        else:
            # No contained literal carries the declared answer. Rewriting the
            # span to some other literal would change what the case asserts,
            # which is a relabelling, not a representational normalisation.
            # N1 is registered to relocate a span, never to revalue it.
            values = sorted(
                {value for value in (_canonical(m.group(0)) for m in contained)
                 if value is not None}
            )
            raise NormalizationError(
                f"evidence span {index} registers answer {declared!r} but "
                f"contains only {values!r}; N1 may relocate a span, never "
                "change the value it asserts",
                reason=QuarantineReason.AMBIGUOUS_SPAN_LITERAL,
            )
        updated["start"] = chosen.start()
        updated["end"] = chosen.end()
        updated["text"] = chosen.group(0)
        updated["normalized_answer"] = _canonical(chosen.group(0))
        rewritten.append(updated)

    result = dict(record)
    result["expected_evidence_spans"] = rewritten
    return result


def apply_n2_canonical_reference(record: Mapping[str, Any]) -> dict[str, Any]:
    """``N2``: express the registered reference answer in canonical form."""
    reference = record.get("registered_reference_answer")
    canonical = _canonical(reference)
    if canonical is None:
        raise NormalizationError(
            "registered_reference_answer is not a registered numeric literal"
        )
    result = dict(record)
    result["registered_reference_answer"] = canonical
    return result


def apply_n3_output_text(
    record: Mapping[str, Any], output_texts: Mapping[str, str]
) -> dict[str, Any]:
    """``N3``: attach the locked output text registered for this case."""
    case_id = record.get("case_id")
    if not isinstance(case_id, str) or case_id not in output_texts:
        raise NormalizationError(
            "case has no registered locked input",
            reason=QuarantineReason.MISSING_LOCKED_INPUT,
        )
    result = dict(record)
    result["output_text"] = output_texts[case_id]
    return result


def apply_n4_last_number_distractor(
    record: Mapping[str, Any], output_text: str
) -> dict[str, Any]:
    """``N4``: register the S06 distractor as the rightmost numeric literal.

    The rule is the frozen instrument's own definition, not a new one.
    """
    if record.get("stratum") != "S06":
        # A no-op default is not an application of the rule. Counting it would
        # report ~120 applications for a rule that governs 10 cases.
        return dict(record)
    matches = frozen._registered_numeric_matches(output_text)
    if not matches:
        raise NormalizationError(
            "S06 case registers no numeric literal",
            reason=QuarantineReason.DISTRACTOR_UNAVAILABLE,
        )
    last = matches[-1]
    distractor = _canonical(last.group(0))
    parsed = _canonical(record.get("expected_parsed_answer"))
    if parsed is not None and distractor == parsed:
        raise NormalizationError(
            "S06 distractor does not differ canonically from the parsed answer",
            reason=QuarantineReason.DISTRACTOR_UNAVAILABLE,
        )
    result = dict(record)
    result["last_number_distractor_span"] = {
        "start": last.start(),
        "end": last.end(),
        "text": last.group(0),
    }
    return result


def apply_n5_secondary_tags(record: Mapping[str, Any]) -> dict[str, Any]:
    """``N5``: derive the quota-diagnostic secondary tags from record content.

    Requires ``output_text``, which ``N3`` attaches; this is why the rule order
    is load-bearing. The requirement is raised as a normalisation failure so
    that a caller quarantines the case instead of aborting the whole run.
    """
    if "output_text" not in record:
        raise NormalizationError(
            "N5 requires the locked output text attached by N3",
            reason=QuarantineReason.RULE_FAILED,
        )
    derived = frozen._surface_features(record) & set(frozen.QUOTA_DIAGNOSTIC_TAGS)
    declared = record.get("secondary_tags") or []
    if not isinstance(declared, list):
        raise NormalizationError("secondary_tags must be a list")
    preserved = [
        tag for tag in declared if tag not in set(frozen.QUOTA_DIAGNOSTIC_TAGS)
    ]
    result = dict(record)
    result["secondary_tags"] = sorted(set(preserved) | derived)
    return result


def apply_n6_candidate_answers(record: Mapping[str, Any]) -> dict[str, Any]:
    """``N6``: recompute candidate answers from the spans, in first-source order."""
    spans = record.get("expected_evidence_spans") or []
    if not isinstance(spans, list):
        raise NormalizationError("expected_evidence_spans must be a list")
    for span in spans:
        if not isinstance(span, Mapping) or not isinstance(
            span.get("start"), int
        ) or not isinstance(span.get("end"), int):
            # N1 normally validates offsets first, but N6 is exported as a
            # standalone pure function and must not leak a bare KeyError.
            raise NormalizationError(
                "evidence span has no usable offsets",
                reason=QuarantineReason.RULE_FAILED,
            )
    ordered: list[str] = []
    for span in sorted(spans, key=lambda item: (item["start"], item["end"])):
        value = span.get("normalized_answer")
        if not isinstance(value, str):
            raise NormalizationError("evidence span carries no normalized answer")
        if value not in ordered:
            ordered.append(value)
    result = dict(record)
    result["expected_candidate_answers"] = ordered
    result["expected_evidence_spans"] = sorted(
        (dict(span) for span in spans), key=lambda item: (item["start"], item["end"])
    )
    return result


def scoring_projection(record: Mapping[str, Any]) -> dict[str, Any]:
    """Project a record onto everything the scorer can see.

    ``raw_typed_decision`` is deliberately coarse -- for ``ambiguous`` and
    ``no_answer`` it discards the candidate set entirely -- so comparing it
    before and after normalisation cannot witness most of the changes
    ``N1``-``N6`` are capable of making. This projection is the pre-image the
    preservation check actually needs: two records with the same projection are
    indistinguishable to the scoring instrument.
    """
    spans = record.get("expected_evidence_spans")
    span_view: Any
    if isinstance(spans, list):
        span_view = [
            (
                span.get("start"),
                span.get("end"),
                span.get("normalized_answer"),
                span.get("disposition"),
            )
            if isinstance(span, Mapping)
            else None
            for span in spans
        ]
    else:
        span_view = spans
    candidates = record.get("expected_candidate_answers")
    return {
        "typed_decision": raw_typed_decision(record),
        "answer_presence": record.get("expected_answer_presence"),
        "parse_valid": record.get("expected_parse_valid"),
        "parse_ambiguous": record.get("expected_parse_ambiguous"),
        "parsed_answer": record.get("expected_parsed_answer"),
        "candidates": list(candidates) if isinstance(candidates, list) else candidates,
        "spans": span_view,
        "extraction_strategy": record.get("expected_extraction_strategy"),
        "output_quality": record.get("expected_output_quality"),
    }


def _licensed_projection(projection: Mapping[str, Any]) -> dict[str, Any]:
    """Drop exactly the fields the six rules are licensed to change.

    ``N1`` may relocate a span (its offsets) while preserving the value it
    asserts; ``N6`` may reorder spans and deduplicate candidates. Nothing else
    is licensed, so everything else must survive normalisation untouched.
    """
    view = dict(projection)
    spans = view.get("spans")
    if isinstance(spans, list):
        view["spans"] = sorted(
            (
                (span[2], span[3]) if isinstance(span, tuple) else span
                for span in spans
            ),
            key=repr,
        )
    candidates = view.get("candidates")
    if isinstance(candidates, list):
        view["candidates"] = sorted(set(map(repr, candidates)))
    return view


def normalize_record(
    record: Mapping[str, Any], output_texts: Mapping[str, str]
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Apply ``N1``-``N6`` to one record.

    Returns the normalised record and the tuple of rules that changed it.
    Raises :class:`NormalizationError` rather than producing a forced result.
    """
    before = raw_typed_decision(record)
    if before == "present_unextractable":
        raise NormalizationError(
            "present_unextractable is research-only and has no formal image",
            reason=QuarantineReason.RESEARCH_ONLY_CLASS,
        )
    before_projection = _licensed_projection(scoring_projection(record))

    case_id = record.get("case_id")
    if not isinstance(case_id, str) or case_id not in output_texts:
        raise NormalizationError(
            "case has no registered locked input",
            reason=QuarantineReason.MISSING_LOCKED_INPUT,
        )
    output_text = output_texts[case_id]

    applied: list[str] = []
    current: Mapping[str, Any] = record
    for rule, step in (
        ("N1", lambda rec: apply_n1_literal_only_spans(rec, output_text)),
        ("N2", apply_n2_canonical_reference),
        ("N3", lambda rec: apply_n3_output_text(rec, output_texts)),
        ("N4", lambda rec: apply_n4_last_number_distractor(rec, output_text)),
        ("N5", apply_n5_secondary_tags),
        ("N6", apply_n6_candidate_answers),
    ):
        updated = step(current)
        if updated != dict(current):
            applied.append(rule)
        current = updated

    after = raw_typed_decision(current)
    if after != before:
        raise NormalizationError(
            "normalisation would change the typed decision; quarantine the case",
            reason=QuarantineReason.DECISION_WOULD_CHANGE,
        )
    if _licensed_projection(scoring_projection(current)) != before_projection:
        raise NormalizationError(
            "normalisation would change what the scorer sees beyond the "
            "transformations N1-N6 are licensed to make; quarantine the case",
            reason=QuarantineReason.DECISION_WOULD_CHANGE,
        )
    if record.get("expected_answer_presence") == "ambiguous":
        candidates = current.get("expected_candidate_answers") or []
        if len(set(candidates)) < 2:
            raise NormalizationError(
                "an ambiguous case must retain at least two distinct candidate "
                "answers; normalisation collapsed its candidate cardinality",
                reason=QuarantineReason.CANDIDATE_CARDINALITY,
            )

    # The projection comparison above catches changes to the fields it
    # covers, but it is a whitelist and a whitelist can have holes. The
    # authoritative check is the ontology validator itself: a migrated
    # record must still be admissible under the three-class ontology,
    # which in turn binds to the frozen scoring instrument. Without this,
    # an unlicensed change escapes normalisation and is only caught later
    # by whole-set validation, which rejects the entire set instead of
    # quarantining the one case that caused it.
    try:
        validate_ontology_record(current, output_text)
    except OntologyError as error:
        raise NormalizationError(
            f"normalised record is not admissible under the formal ontology: "
            f"{error}",
            reason=QuarantineReason.FAILS_ONTOLOGY,
        ) from error

    return dict(current), tuple(applied)


def normalize_set(
    records: Sequence[Mapping[str, Any]], output_texts: Mapping[str, str]
) -> tuple[list[dict[str, Any]], dict[str, str], NormalizationReceipt]:
    """Normalise a whole set, quarantining every case a rule cannot decide.

    Returns the normalised records, a mapping of quarantined case id to reason
    code, and a content-free receipt.
    """
    normalized: list[dict[str, Any]] = []
    quarantined: dict[str, str] = {}
    rule_counts: dict[str, int] = {rule: 0 for rule, _ in NORMALIZATION_RULES}
    reason_counts: dict[str, int] = {}

    for index, record in enumerate(records):
        case_id = record.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise NormalizationError(f"record {index} has no usable case id")
        try:
            updated, applied = normalize_record(record, output_texts)
        except NormalizationError as error:
            reason = error.reason
            quarantined[case_id] = reason
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            continue
        for rule in applied:
            rule_counts[rule] += 1
        normalized.append(updated)

    receipt = NormalizationReceipt(
        input_case_count=len(records),
        normalized_case_count=len(normalized),
        quarantined_case_count=len(quarantined),
        rule_application_counts=rule_counts,
        quarantine_reason_counts=reason_counts,
        input_digest=_digest([_shape(record) for record in records]),
        output_digest=_digest([_shape(record) for record in normalized]),
        # A commitment to the actual normalisation output, so an auditor can
        # verify that a rerun reproduced this run. The shape digests above
        # cannot do that: two different N1 outcomes share the same shape.
        # A digest discloses nothing, so this remains content-free to publish.
        normalized_content_digest=_digest(
            sorted(normalized, key=lambda item: str(item.get("case_id")))
        ),
        quarantined_case_id_digest=_digest(sorted(quarantined)),
    )
    return normalized, quarantined, receipt


def _shape(record: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce a record to a value-free shape so receipts leak no answers."""
    spans = record.get("expected_evidence_spans") or []
    return {
        "case_id_digest": hashlib.sha256(
            str(record.get("case_id")).encode("utf-8")
        ).hexdigest(),
        "stratum": record.get("stratum"),
        "answer_presence": record.get("expected_answer_presence"),
        "parse_valid": bool(record.get("expected_parse_valid")),
        "parse_ambiguous": bool(record.get("expected_parse_ambiguous")),
        "output_quality": record.get("expected_output_quality"),
        "extraction_strategy": record.get("expected_extraction_strategy"),
        "span_count": len(spans) if isinstance(spans, list) else None,
        "candidate_count": len(record.get("expected_candidate_answers") or []),
        "field_names": sorted(record),
    }


def assert_parser_free_source(paths: Iterable[str]) -> None:
    """Fail if any given source file references a parser module or symbol.

    A *runtime* check that no parser module is in ``sys.modules`` cannot work
    in this repository: the package ``__init__`` eagerly imports the parser
    module, so importing anything at all loads a parser. An assertion that
    appeared to prove otherwise would be false comfort.

    What is actually provable, and what this checks, is that the repair sources
    never reference a parser. The companion runtime obligation -- that importing
    the repair modules pulls in nothing beyond the package baseline -- is proved
    differentially in the test suite.

    The searched symbols are assembled from fragments so that this scanner does
    not report itself, and so that no docstring in this file can mask a real
    reference by making the scan unconditionally noisy.
    """
    import re

    module = "eval" + "_parsing"
    entry = "parse" + "_model_output"
    pattern = re.compile(rf"{module}(_v2|_v3)?\b|{entry}\b")
    offenders: list[str] = []
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("--"):
                continue
            if pattern.search(line):
                offenders.append(f"{path}:{number}")
    if offenders:
        raise NormalizationError(
            "repair sources must not reference a parser: " + ", ".join(offenders)
        )
