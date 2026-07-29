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


POLICY_SCHEMA_VERSION = "phase1-parser-v3-prospective-evaluation-policy/v1"
FACTS_SCHEMA_VERSION = "phase1-parser-v3-set-derived-facts/v1"
CONTRACT_SCHEMA_VERSION = "phase1-parser-v3-compiled-acceptance-contract/v1"


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

    thresholds = policy.get("acceptance_thresholds")
    if not isinstance(thresholds, Mapping):
        raise ContractError("policy.acceptance_thresholds must be an object")
    if thresholds.get("status") not in ("FINAL", "REVIEW_REQUIRED"):
        raise ContractError("policy.acceptance_thresholds.status is not recognised")

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
