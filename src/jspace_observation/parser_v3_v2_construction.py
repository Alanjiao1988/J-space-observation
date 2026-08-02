"""Deterministic construction rules for the successor ``parser-v3-v2`` set.

Phase 1.2H-R2 / 1.2J. This module owns the part of the round that decides
*which cases may exist in the set at all*: reviewer blinding, the agreement
surface, arbiter scoping, quarantine, bounded replacement, deterministic
selection, the exact final-set invariants, and collision freedom.

It is deliberately separate from ``parser_v3_v2_lifecycle``. That module decides
whether the evaluation may proceed; this one decides whether the set is
admissible in the first place. Merging them would let a construction rule be
relaxed as a side effect of an ordering change.

Three things this module refuses to do
--------------------------------------

*It does not target the historical split.* The retired v1 round produced 105
repairable and 15 residual cases. The controlling protocol is explicit that this
is an expectation and not a target, and that rules must never be modified to
reproduce it. :func:`assert_split_is_not_a_target` exists so that a rule set
carrying the historical numbers as a threshold is refused rather than reviewed.

*It does not retry without a bound.* Replacement batches are finite and
preregistered per slot. Exhausting a slot yields ``BLOCKED_ON_SET_REPAIR``,
which is an honest terminal state, and not another batch.

*It does not compute or store anything about a parser.* No parser symbol is
referenced and no parser is invoked. Construction artifacts that carry a parser,
prediction or performance field are refused, because a construction record that
knows how the parser did is a record that could have been selected to flatter
it.

Nothing here reads a private set, a sealed blob or a locked label.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "ConstructionError",
    "BlockedOnSetRepair",
    "CONSTRUCTION_SCHEMA_VERSION",
    "STRATA",
    "STRATUM_QUOTA",
    "GATE_PINNED_STRATA",
    "RESIDUAL_STRATA",
    "TOTAL_CASES",
    "DECISION_CLASSES",
    "DECISION_CLASS_QUOTA",
    "AGREEMENT_FIELDS",
    "REVIEWER_FORBIDDEN_INPUTS",
    "ARBITER_FORBIDDEN_INPUTS_BEFORE_ADJUDICATION",
    "PARSER_BEARING_FIELDS",
    "QUARANTINE_REASONS",
    "HISTORICAL_SPLIT",
    "TARGET_KEY_FRAGMENTS",
    "COLLISION_RULES",
    "content_hash",
    "assert_reviewer_packet_is_blind",
    "assert_arbiter_packet_is_scoped",
    "disagreeing_fields",
    "routes_to_arbiter",
    "assert_only_disagreements_reached_arbiter",
    "assert_quarantine_reason_is_registered",
    "assert_replacement_batch_within_limit",
    "select_deterministically",
    "assert_no_prohibited_collision",
    "assert_no_parser_field",
    "assert_split_is_not_a_target",
    "assert_final_set_invariants",
]


class ConstructionError(Exception):
    """Raised when a proposed construction action or artifact is not admissible."""


class BlockedOnSetRepair(ConstructionError):
    """Raised when a slot cannot be filled within its preregistered batch limit.

    A distinct type because this one is not a defect. It is the protocol's
    honest terminal state for a set that cannot be completed, and a caller is
    expected to surface it rather than to treat it as an error to work around.
    """


CONSTRUCTION_SCHEMA_VERSION = "phase1-parser-v3-v2-construction/v1"

STRATA: tuple[str, ...] = tuple(f"S{index:02d}" for index in range(1, 13))
STRATUM_QUOTA = 10
TOTAL_CASES = len(STRATA) * STRATUM_QUOTA

#: Strata whose cases are pinned to the acceptance gates.
GATE_PINNED_STRATA: tuple[str, ...] = ("S01", "S02", "S03", "S07", "S08", "S10", "S11", "S12")

#: Strata carrying residual exact-conformance cases.
RESIDUAL_STRATA: tuple[str, ...] = ("S04", "S05", "S06", "S09")

DECISION_CLASSES: tuple[str, ...] = ("present", "no_answer", "ambiguous")

#: Exact decision-class quotas for the final set.
DECISION_CLASS_QUOTA: Mapping[str, int] = {
    "present": 80,
    "no_answer": 30,
    "ambiguous": 10,
}

#: Every scoring-relevant field two reviewers must agree on.
#:
#: Agreement on the typed decision alone is not agreement. The protocol lists
#: the surface explicitly because a narrower surface would let two reviewers
#: "agree" while differing on the span that makes the decision checkable.
AGREEMENT_FIELDS: tuple[str, ...] = (
    "typed_decision",
    "canonical_value",
    "canonical_candidates",
    "literal_spans",
    "span_roles",
    "ambiguity",
    "equivalence",
    "extraction_strategy",
    "output_quality",
    "warnings",
    "failure_reasons",
    "stratum",
    "subtype",
)

#: Inputs a reviewer packet must never contain.
REVIEWER_FORBIDDEN_INPUTS: frozenset[str] = frozenset(
    {
        "old_label",
        "migrated_label",
        "parser_code",
        "parser_result",
        "prediction",
        "reuse_status",
        "other_reviewer_decision",
        "arbitration_record",
    }
)

#: Inputs an arbiter packet must not contain until adjudication is recorded.
#:
#: The old label is the specific one the protocol names. Letting an arbiter see
#: it first turns adjudication into agreement-with-history, which is exactly the
#: dependence the successor set exists to remove.
ARBITER_FORBIDDEN_INPUTS_BEFORE_ADJUDICATION: frozenset[str] = frozenset(
    {"old_label", "migrated_label", "parser_code", "parser_result", "prediction"}
)

#: Field-name fragments that make a construction artifact parser-aware.
PARSER_BEARING_FIELDS: tuple[str, ...] = (
    "parser",
    "prediction",
    "predicted",
    "accuracy",
    "f1",
    "score",
    "performance",
    "pass_rate",
)

#: The only reasons a case may be quarantined.
#:
#: A closed list, because an open one lets "other" absorb a case that was
#: really removed for being inconvenient.
QUARANTINE_REASONS: frozenset[str] = frozenset(
    {
        "failed_deterministic_validation",
        "semantic_uncertainty",
        "conflicts_with_v2_ontology",
        "cannot_satisfy_mandatory_correct_handling",
        "unresolved_after_arbitration",
        "compromised_blinding",
        "prohibited_collision",
    }
)

#: The retired v1 outcome, recorded so it can be refused as a target.
HISTORICAL_SPLIT: Mapping[str, int] = {"repairable": 105, "residual": 15}

#: Key-name fragments that mark a value as a target rather than an observation.
#:
#: The guard below needs both halves: a value equal to the historical split and
#: a key that treats it as something to hit. Refusing the bare integer 15
#: anywhere in a rule set would reject an unrelated batch limit or timeout, and
#: a check that fires on innocent inputs gets disabled by whoever hits it first.
TARGET_KEY_FRAGMENTS: tuple[str, ...] = (
    "target",
    "expected",
    "quota",
    "must_equal",
    "required_count",
    "repairable",
    "residual_count",
)

_WHITESPACE = re.compile(r"\s+")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")

#: A template's slot fillers: quoted spans, bracketed placeholders, and any
#: token carrying a digit (identifiers, codes, quantities). Deliberately *not*
#: every alphanumeric run — see :func:`_rule_template_family`.
_QUOTED = re.compile("[\"'\u00ab\u00bb\u201c\u201d\u2018\u2019][^\"'\u00ab\u00bb\u201c\u201d\u2018\u2019]*[\"'\u00ab\u00bb\u201c\u201d\u2018\u2019]")
_PLACEHOLDER = re.compile(r"[{<\[][^{}<>\[\]]*[}>\]]")
_SLOT_TOKEN = re.compile(r"\S*\d\S*")
_SLOT = "\x00slot\x00"


def content_hash(payload: str) -> str:
    """Return the SHA-256 of a case's content, over NFC-normalised UTF-8.

    Unicode normalisation is applied first so that two byte sequences a human
    reviewer cannot tell apart do not become two different cases with two
    different tie-break positions.
    """
    if not isinstance(payload, str):
        raise ConstructionError(f"content must be str, got {type(payload).__name__}")
    normalised = unicodedata.normalize("NFC", payload)
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# blinding
# ---------------------------------------------------------------------------


def assert_reviewer_packet_is_blind(packet: Mapping[str, Any]) -> None:
    """Refuse a reviewer packet carrying anything that breaks independence."""
    if not isinstance(packet, Mapping):
        raise ConstructionError("reviewer packet must be a mapping")
    present = sorted(set(packet).intersection(REVIEWER_FORBIDDEN_INPUTS))
    if present:
        raise ConstructionError(f"reviewer packet carries forbidden input(s): {present}")
    required = {"case_content", "public_ontology_packet"}
    missing = sorted(required - set(packet))
    if missing:
        raise ConstructionError(f"reviewer packet is missing required input(s): {missing}")


def assert_arbiter_packet_is_scoped(
    packet: Mapping[str, Any], *, adjudication_permanently_recorded: bool
) -> None:
    """Refuse an arbiter packet that reaches the old label too early."""
    if not isinstance(packet, Mapping):
        raise ConstructionError("arbiter packet must be a mapping")
    if not isinstance(adjudication_permanently_recorded, bool):
        raise ConstructionError("adjudication_permanently_recorded must be a bool")
    if not adjudication_permanently_recorded:
        present = sorted(
            set(packet).intersection(ARBITER_FORBIDDEN_INPUTS_BEFORE_ADJUDICATION)
        )
        if present:
            raise ConstructionError(
                "arbiter packet carries input(s) that are only permitted after the "
                f"adjudication is permanently recorded: {present}"
            )
    required = {"case_content", "public_ontology_packet", "reviewer_a", "reviewer_b"}
    missing = sorted(required - set(packet))
    if missing:
        raise ConstructionError(f"arbiter packet is missing required input(s): {missing}")


# ---------------------------------------------------------------------------
# agreement and routing
# ---------------------------------------------------------------------------


def disagreeing_fields(
    reviewer_a: Mapping[str, Any], reviewer_b: Mapping[str, Any]
) -> tuple[str, ...]:
    """Return the agreement fields on which two reviewers differ.

    A field missing from either decision counts as a disagreement rather than
    as a match. Treating absence as agreement would let an incomplete review
    pass as a concurring one.
    """
    for name, decision in (("reviewer_a", reviewer_a), ("reviewer_b", reviewer_b)):
        if not isinstance(decision, Mapping):
            raise ConstructionError(f"{name} decision must be a mapping")
    differing: list[str] = []
    for field in AGREEMENT_FIELDS:
        if field not in reviewer_a or field not in reviewer_b:
            differing.append(field)
        elif reviewer_a[field] != reviewer_b[field]:
            differing.append(field)
    return tuple(differing)


def routes_to_arbiter(
    reviewer_a: Mapping[str, Any], reviewer_b: Mapping[str, Any]
) -> bool:
    """True when and only when the two decisions differ somewhere that scores."""
    return bool(disagreeing_fields(reviewer_a, reviewer_b))


def assert_only_disagreements_reached_arbiter(
    *,
    arbitrated_case_ids: Iterable[str],
    decisions_by_case: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> None:
    """Refuse an arbitration set that includes an agreed case, or omits a differing one.

    Both directions are checked. Arbitrating an agreed case invents a third
    opinion where none was needed; skipping a differing case leaves an
    unresolved decision inside the set.
    """
    arbitrated = set(arbitrated_case_ids)
    unknown = sorted(arbitrated - set(decisions_by_case))
    if unknown:
        raise ConstructionError(f"arbitrated case(s) have no recorded decisions: {unknown}")
    should = {cid for cid, (a, b) in decisions_by_case.items() if routes_to_arbiter(a, b)}
    spurious = sorted(arbitrated - should)
    if spurious:
        raise ConstructionError(
            f"case(s) reached the arbiter without a disagreement: {spurious}"
        )
    skipped = sorted(should - arbitrated)
    if skipped:
        raise ConstructionError(
            f"case(s) disagreed but never reached the arbiter: {skipped}"
        )


# ---------------------------------------------------------------------------
# quarantine and bounded replacement
# ---------------------------------------------------------------------------


def assert_quarantine_reason_is_registered(reason: str) -> None:
    """Refuse an unregistered quarantine reason."""
    if reason not in QUARANTINE_REASONS:
        raise ConstructionError(
            f"{reason!r} is not a registered quarantine reason; the list is closed "
            "so that a case cannot be removed for an unstated motive"
        )


def assert_replacement_batch_within_limit(
    *, slot: str, batches_used: int, preregistered_batch_limit: int
) -> None:
    """Refuse an unbounded retry; raise the protocol's blocked state instead."""
    for name, value in (
        ("batches_used", batches_used),
        ("preregistered_batch_limit", preregistered_batch_limit),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ConstructionError(f"{name} must be an int, got {value!r}")
        if value < 0:
            raise ConstructionError(f"{name} must not be negative, got {value}")
    if preregistered_batch_limit == 0:
        raise ConstructionError(
            "a preregistered batch limit of 0 leaves no way to fill a slot and no "
            "way to fail one; it must be a positive bound fixed before generation"
        )
    if batches_used >= preregistered_batch_limit:
        raise BlockedOnSetRepair(
            f"slot {slot} exhausted its preregistered limit of "
            f"{preregistered_batch_limit} replacement batch(es); the round is "
            "BLOCKED_ON_SET_REPAIR and must not generate another batch"
        )


# ---------------------------------------------------------------------------
# deterministic selection
# ---------------------------------------------------------------------------


def select_deterministically(
    candidates: Sequence[Mapping[str, Any]], *, count: int
) -> tuple[Mapping[str, Any], ...]:
    """Select ``count`` candidates by the frozen rule with a content-hash tie-break.

    The order of ``candidates`` must not affect the result, so the ranking key
    is total: the declared eligibility rank first, then the content hash. A
    repeated content hash is refused rather than ordered arbitrarily, because
    two candidates with identical content are one candidate counted twice.
    """
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ConstructionError(f"count must be a non-negative int, got {count!r}")
    prepared: list[tuple[int, str, Mapping[str, Any]]] = []
    seen: dict[str, str] = {}
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ConstructionError("each candidate must be a mapping")
        for field in ("case_id", "eligibility_rank", "content"):
            if field not in candidate:
                raise ConstructionError(f"candidate is missing {field!r}")
        rank = candidate["eligibility_rank"]
        if not isinstance(rank, int) or isinstance(rank, bool):
            raise ConstructionError(f"eligibility_rank must be an int, got {rank!r}")
        digest = content_hash(candidate["content"])
        if digest in seen:
            raise ConstructionError(
                "two candidates share a content hash, so the tie-break cannot order "
                f"them: {seen[digest]!r} and {candidate['case_id']!r}"
            )
        seen[digest] = candidate["case_id"]
        prepared.append((rank, digest, candidate))
    if count > len(prepared):
        raise ConstructionError(
            f"cannot select {count} from {len(prepared)} eligible candidate(s)"
        )
    prepared.sort(key=lambda item: (item[0], item[1]))
    return tuple(item[2] for item in prepared[:count])


# ---------------------------------------------------------------------------
# collision freedom
# ---------------------------------------------------------------------------


def _rule_exact(text: str) -> str:
    return text


def _rule_normalized(text: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", text)).strip().casefold()


def _rule_numeric_normalized(text: str) -> str:
    def canonical(match: re.Match[str]) -> str:
        raw = match.group(0)
        try:
            value = float(raw)
        except ValueError:  # pragma: no cover - the pattern guarantees a number
            return raw
        return repr(int(value)) if value.is_integer() else repr(value)

    return _NUMBER.sub(canonical, _rule_normalized(text))


def _rule_template_family(text: str) -> str:
    """Collapse slot fillers so two cases cut from one template collide.

    Only what plausibly varies between siblings of a template is masked:
    quoted spans, bracketed placeholders, and tokens carrying a digit. The
    surrounding words are kept.

    The obvious shortcut -- mask every alphanumeric run -- is wrong, and wrong
    in the direction that does damage. It reduces "alpha one" and "beta two" to
    the same skeleton, so it reports a collision between two unrelated cases and
    sends a perfectly good set to repair. A rule that fires on innocent input is
    a rule someone eventually switches off, and then it protects nothing.
    """
    masked = _rule_normalized(text)
    masked = _QUOTED.sub(_SLOT, masked)
    masked = _PLACEHOLDER.sub(_SLOT, masked)
    return _SLOT_TOKEN.sub(_SLOT, masked)


#: Every registered collision rule. The checker runs all of them.
COLLISION_RULES: Mapping[str, Any] = {
    "exact": _rule_exact,
    "normalized": _rule_normalized,
    "numeric_normalized": _rule_numeric_normalized,
    "template_family": _rule_template_family,
}


def assert_no_prohibited_collision(
    *,
    set_contents: Mapping[str, str],
    external_corpus_fingerprints: Mapping[str, Mapping[str, str]] | None = None,
    authorized_reuse_case_ids: Iterable[str] = (),
) -> None:
    """Refuse any within-set or cross-set collision under every registered rule.

    Every rule in :data:`COLLISION_RULES` is applied; there is no way to run a
    subset, because a checker that silently skips a rule reports freedom it did
    not establish.

    Authorised reuse from the never-evaluated retired v1 set is not a
    prohibited collision, so those case identifiers are exempt from the
    cross-set comparison only. They are still checked within the set, because
    a case may not appear twice regardless of where it came from.
    """
    authorized = set(authorized_reuse_case_ids)
    unknown = sorted(authorized - set(set_contents))
    if unknown:
        raise ConstructionError(
            f"authorized reuse names case(s) that are not in the set: {unknown}"
        )
    for rule_name, rule in COLLISION_RULES.items():
        buckets: dict[str, str] = {}
        for case_id, text in set_contents.items():
            if not isinstance(text, str):
                raise ConstructionError(f"content for {case_id!r} must be str")
            key = rule(unicodedata.normalize("NFC", text))
            if key in buckets:
                raise ConstructionError(
                    f"within-set collision under rule {rule_name!r}: "
                    f"{buckets[key]!r} and {case_id!r}"
                )
            buckets[key] = case_id
        if not external_corpus_fingerprints:
            continue
        for corpus_name, fingerprints in external_corpus_fingerprints.items():
            if rule_name not in fingerprints:
                raise ConstructionError(
                    f"corpus {corpus_name!r} supplied no fingerprint for registered "
                    f"rule {rule_name!r}; collision freedom cannot be claimed"
                )
            foreign = set(fingerprints[rule_name].split(","))
            for key, case_id in buckets.items():
                if case_id in authorized:
                    continue
                if hashlib.sha256(key.encode("utf-8")).hexdigest() in foreign:
                    raise ConstructionError(
                        f"cross-set collision under rule {rule_name!r} against "
                        f"{corpus_name!r} for case {case_id!r}"
                    )


# ---------------------------------------------------------------------------
# artifact hygiene
# ---------------------------------------------------------------------------


def assert_no_parser_field(artifact: Any, *, path: str = "artifact") -> None:
    """Refuse a construction artifact that carries a parser-aware field.

    Walks nested structures. A construction record that knows how the parser
    performed is a record that could have been selected to flatter it, and the
    protocol forbids the field rather than trusting the intent.
    """
    if isinstance(artifact, Mapping):
        for key, value in artifact.items():
            if isinstance(key, str):
                lowered = key.lower()
                for marker in PARSER_BEARING_FIELDS:
                    if marker in lowered:
                        raise ConstructionError(
                            f"{path}.{key} is a parser-bearing field and must not "
                            "appear in a construction artifact"
                        )
            assert_no_parser_field(value, path=f"{path}.{key}")
    elif isinstance(artifact, (list, tuple)):
        for index, value in enumerate(artifact):
            assert_no_parser_field(value, path=f"{path}[{index}]")


def assert_split_is_not_a_target(rule_set: Mapping[str, Any]) -> None:
    """Refuse a rule set that encodes the historical 105/15 split as a target.

    The historical split is an expectation about what the data turned out to
    contain. A rule that reproduces it by construction has stopped measuring
    the data and started asserting the answer.

    Two conditions must hold together for a refusal: the value equals one of
    the historical counts, and the key it sits under names it as a target. The
    conjunction matters. A rule set may legitimately contain the integer 15 as
    a batch limit, and a guard that rejected that would be switched off by the
    first person it inconvenienced.
    """
    if not isinstance(rule_set, Mapping):
        raise ConstructionError("rule set must be a mapping")
    historical = set(HISTORICAL_SPLIT.values())

    def key_is_a_target(key: str) -> bool:
        lowered = key.lower()
        return any(fragment in lowered for fragment in TARGET_KEY_FRAGMENTS)

    def walk(node: Any, path: str, under_target_key: bool) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                marked = under_target_key or (isinstance(key, str) and key_is_a_target(key))
                walk(value, f"{path}.{key}", marked)
        elif isinstance(node, (list, tuple)):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]", under_target_key)
        elif isinstance(node, int) and not isinstance(node, bool):
            if under_target_key and node in historical:
                raise ConstructionError(
                    f"{path} pins the historical split value {node} as a target; the "
                    "105/15 outcome is an expectation and must never become one"
                )

    walk(rule_set, "rule_set", False)


# ---------------------------------------------------------------------------
# final set invariants
# ---------------------------------------------------------------------------


def assert_final_set_invariants(cases: Sequence[Mapping[str, Any]]) -> None:
    """Refuse a final set that violates any exact invariant.

    Every invariant is checked and the first violation raises. The counts are
    derived from the cases rather than read from a summary field, because a
    summary is a claim about the set and this function's job is to test it.
    """
    if len(cases) != TOTAL_CASES:
        raise ConstructionError(f"the set must hold exactly {TOTAL_CASES} cases, got {len(cases)}")

    case_ids = [case.get("case_id") for case in cases]
    if any(cid is None for cid in case_ids):
        raise ConstructionError("every case must carry a case_id")
    if len(set(case_ids)) != len(case_ids):
        raise ConstructionError("case identifiers must be unique")

    per_stratum: dict[str, int] = {stratum: 0 for stratum in STRATA}
    per_class: dict[str, int] = {name: 0 for name in DECISION_CLASSES}
    for case in cases:
        stratum = case.get("stratum")
        if stratum not in per_stratum:
            raise ConstructionError(f"case {case.get('case_id')!r} has unregistered stratum {stratum!r}")
        per_stratum[stratum] += 1

        decision = case.get("decision_class")
        if decision not in per_class:
            raise ConstructionError(
                f"case {case.get('case_id')!r} has decision class {decision!r}, which is "
                "outside the three registered classes; no fourth or research-only "
                "class is permitted"
            )
        per_class[decision] += 1

        for flag in ("eligible", "adjudicable", "mandatory"):
            if case.get(flag) is not True:
                raise ConstructionError(f"case {case.get('case_id')!r} is not {flag}")
        if case.get("unresolved") is True:
            raise ConstructionError(f"case {case.get('case_id')!r} carries an unresolved decision")
        if case.get("subtype_slot") in (None, ""):
            raise ConstructionError(f"case {case.get('case_id')!r} has no subtype slot")

        spans = case.get("literal_spans", ())
        if not isinstance(spans, (list, tuple)):
            raise ConstructionError(f"case {case.get('case_id')!r} has a non-sequence literal_spans")
        for span in spans:
            if not isinstance(span, Mapping) or span.get("literal") is not True:
                raise ConstructionError(
                    f"case {case.get('case_id')!r} carries a non-literal span; only "
                    "literal spans are admissible"
                )

        if stratum == "S06" and case.get("rightmost_distractor_registration") is not True:
            raise ConstructionError(f"S06 case {case.get('case_id')!r} has no valid rightmost-distractor registration")
        if stratum == "S11" and case.get("ambiguity_registration") is not True:
            raise ConstructionError(f"S11 case {case.get('case_id')!r} has no valid ambiguity registration")

    wrong_stratum = sorted(s for s, n in per_stratum.items() if n != STRATUM_QUOTA)
    if wrong_stratum:
        raise ConstructionError(
            f"stratum quota of {STRATUM_QUOTA} violated for: "
            + ", ".join(f"{s}={per_stratum[s]}" for s in wrong_stratum)
        )
    wrong_class = sorted(c for c, n in per_class.items() if n != DECISION_CLASS_QUOTA[c])
    if wrong_class:
        raise ConstructionError(
            "decision-class quota violated for: "
            + ", ".join(f"{c}={per_class[c]} expected {DECISION_CLASS_QUOTA[c]}" for c in wrong_class)
        )

    gate_pinned = sum(per_stratum[s] for s in GATE_PINNED_STRATA)
    residual = sum(per_stratum[s] for s in RESIDUAL_STRATA)
    if gate_pinned != 80:
        raise ConstructionError(f"expected 80 gate-pinned cases, got {gate_pinned}")
    if residual != 40:
        raise ConstructionError(f"expected 40 residual exact-conformance cases, got {residual}")

    for case in cases:
        assert_no_parser_field(case, path=f"case[{case.get('case_id')}]")
