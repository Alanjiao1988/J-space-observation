"""Schemas and production validators for the Study 3 P0-R1 registration.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections 6,
7, 8 and 10.

Everything here is production code. The registration tests drive these exact
functions on live documents rather than on test-local fabrications, so a
negative mutation that alters a live input and is not rejected here is a real
defect rather than a missing assertion.

The validator is deliberately dependency-free: ``requirements.lock.txt`` pins no
JSON-Schema package, and the authoritative CPU validation route installs nothing
else.
"""

import hashlib
import json
import os
import re
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))

sys.path.insert(0, P0_R1_DIR)

import p0_r1_factorization as FACT  # noqa: E402
from p0_r1_counters import (  # noqa: E402
    IDENTITY_CARDINALITY_COUNTERS,
    ZERO_BEFORE_EXECUTION,
)

CORPUS_PATH = "studies/study3/pilot/p0/corpus/p0_corpus.json"
CORPUS_MANIFEST_PATH = "studies/study3/pilot/p0/corpus/p0_corpus_manifest.json"

REGISTERED_CORPUS_ROW_COUNT = 35
REGISTERED_CORPUS_MEMBER_COUNT = 70

EVIDENCE_LEDGER = "paper/evidence_ledger.csv"
EVIDENCE_LAST_ROW = "EV-0016"

# The one narrow flag this package is permitted to carry, not yet consumed.
PERMITTED_TRUE_AUTHORITY_FLAG = "p0_r1_pilot_execution_authorized"

# Every other authority flag must remain false, and every unresolved item must
# remain null rather than zero.
FALSE_AUTHORITY_FLAGS = (
    "frozen",
    "formal_execution_authorized",
    "draft_v0_6_reviewed",
    "draft_v0_6_selected",
    "positive_reference_selected",
    "seed_authorized",
    "bank_authorized",
    "confirmation_access_authorized",
    "winner_selected",
    "od2_resolved",
    "ur22_resolved",
    "rp_selected",
    "evidence_row_written",
    "selection_map_run",
)

NULL_AUTHORITY_ITEMS = ("interface_selected", "positive_reference", "rp_wrapper")

# The exact identity of the section 3.3 equivalence assertion. Weakening or
# removing any of these is a registered negative mutation.
REQUIRED_EQUIVALENCE_FIELDS = (
    "identity", "consequence", "why_exact", "valid_because",
    "does_not_extend_to", "tie_break_order",
)
REQUIRED_EQUIVALENCE_IDENTITY = "P(u, v_d | x) = P(u | x) * P(v_d | x, u)"
REQUIRED_EQUIVALENCE_CONSEQUENCE = (
    "argmax_d P(u, v_d | x) = argmax_d P(v_d | x, u)")


class SchemaDefect(Exception):
    """A fail-closed schema or invariant stop."""


# ---------------------------------------------------------------------------
# A compact, dependency-free JSON-Schema subset validator.
# ---------------------------------------------------------------------------

_IGNORED = {"$schema", "$id", "$comment", "title", "description", "examples",
            "default"}

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "number": (int, float), "integer": int, "null": type(None),
}


def _type_ok(instance, name):
    """``bool`` is an ``int`` in Python; a count written as ``true`` is rejected."""
    if name in ("integer", "number") and isinstance(instance, bool):
        return False
    if name == "boolean":
        return isinstance(instance, bool)
    return isinstance(instance, _TYPES[name])


def _canonical(value):
    return json.dumps(value, sort_keys=True)


def schema_errors(instance, schema, path="$"):
    """Return a list of validation errors. An empty list means valid."""
    errors = []
    for key, value in schema.items():
        if key in _IGNORED:
            continue
        if key == "type":
            names = value if isinstance(value, list) else [value]
            if not any(_type_ok(instance, name) for name in names):
                errors.append("%s: expected type %s, got %s"
                              % (path, value, type(instance).__name__))
        elif key == "const":
            if instance != value:
                errors.append("%s: expected const %r, got %r"
                              % (path, value, instance))
        elif key == "enum":
            if instance not in value:
                errors.append("%s: %r not in enum %r" % (path, instance, value))
        elif key == "required":
            if isinstance(instance, dict):
                for prop in value:
                    if prop not in instance:
                        errors.append("%s: missing required property %r"
                                      % (path, prop))
        elif key == "properties":
            if isinstance(instance, dict):
                for prop, sub in value.items():
                    if prop in instance:
                        errors.extend(schema_errors(instance[prop], sub,
                                                    "%s.%s" % (path, prop)))
        elif key == "additionalProperties":
            if isinstance(instance, dict):
                allowed = set(schema.get("properties", {}))
                if value is False:
                    for prop in instance:
                        if prop not in allowed:
                            errors.append(
                                "%s: additional property %r is not allowed"
                                % (path, prop))
                elif isinstance(value, dict):
                    for prop, sub_instance in instance.items():
                        if prop not in allowed:
                            errors.extend(schema_errors(
                                sub_instance, value, "%s.%s" % (path, prop)))
        elif key == "items":
            if isinstance(instance, list):
                for index, item in enumerate(instance):
                    errors.extend(schema_errors(item, value,
                                                "%s[%d]" % (path, index)))
        elif key == "uniqueItems":
            if value is True and isinstance(instance, list):
                seen = [_canonical(item) for item in instance]
                if len(set(seen)) != len(seen):
                    errors.append("%s: items are not unique" % path)
        elif key == "minItems":
            if isinstance(instance, list) and len(instance) < value:
                errors.append("%s: %d items, minimum %d"
                              % (path, len(instance), value))
        elif key == "maxItems":
            if isinstance(instance, list) and len(instance) > value:
                errors.append("%s: %d items, maximum %d"
                              % (path, len(instance), value))
        elif key == "minLength":
            if isinstance(instance, str) and len(instance) < value:
                errors.append("%s: length %d, minimum %d"
                              % (path, len(instance), value))
        elif key == "pattern":
            if isinstance(instance, str) and re.search(value, instance) is None:
                errors.append("%s: %r does not match %r" % (path, instance, value))
        elif key == "minimum":
            if isinstance(instance, (int, float)) \
                    and not isinstance(instance, bool) and instance < value:
                errors.append("%s: %r is below the minimum %r"
                              % (path, instance, value))
        elif key == "maximum":
            if isinstance(instance, (int, float)) \
                    and not isinstance(instance, bool) and instance > value:
                errors.append("%s: %r is above the maximum %r"
                              % (path, instance, value))
    return errors


# ---------------------------------------------------------------------------
# The frozen corpus.
# ---------------------------------------------------------------------------

def validate_corpus_binding(corpus, manifest=None):
    """The frozen 35-cell / 70-member corpus and every member hash must hold."""
    if not isinstance(corpus, dict):
        raise SchemaDefect("the frozen corpus must be a mapping")
    rows = corpus.get("rows")
    if not isinstance(rows, list):
        raise SchemaDefect("the frozen corpus carries no rows")
    if corpus.get("row_count") != REGISTERED_CORPUS_ROW_COUNT \
            or len(rows) != REGISTERED_CORPUS_ROW_COUNT:
        raise SchemaDefect(
            "the frozen corpus holds %d rows against the registered %d; no row "
            "may be added, removed or replaced"
            % (len(rows), REGISTERED_CORPUS_ROW_COUNT))
    members = 0
    for row in rows:
        for member in row.get("members", []):
            members += 1
            prompt = member.get("prompt")
            if not isinstance(prompt, str):
                raise SchemaDefect(
                    "frozen corpus row %r carries a non-string prompt"
                    % row.get("row_id"))
            raw = prompt.encode("utf-8")
            if len(raw) != member.get("prompt_bytes"):
                raise SchemaDefect(
                    "frozen corpus row %r member %r no longer matches its "
                    "registered prompt byte length"
                    % (row.get("row_id"), member.get("role_in_pair")))
            if hashlib.sha256(raw).hexdigest() != member.get("prompt_sha256"):
                raise SchemaDefect(
                    "frozen corpus row %r member %r no longer matches its "
                    "registered prompt hash"
                    % (row.get("row_id"), member.get("role_in_pair")))
    if members != REGISTERED_CORPUS_MEMBER_COUNT:
        raise SchemaDefect(
            "the frozen corpus holds %d members against the registered %d"
            % (members, REGISTERED_CORPUS_MEMBER_COUNT))
    if corpus.get("namespace") != "study3-p0-only":
        raise SchemaDefect(
            "the pilot namespace changed; the study3-p0-only namespace is "
            "permanently excluded from every formal bank")
    if manifest is not None:
        declared = manifest.get("row_count")
        if declared is not None and declared != REGISTERED_CORPUS_ROW_COUNT:
            raise SchemaDefect(
                "the corpus manifest declares %r rows" % declared)
    return True


def validate_corpus_reuse(corpus, root=None):
    """P0-R1 must reuse the exact frozen corpus bytes, not a copy of them."""
    identity = FACT.source_identity(CORPUS_PATH, root=root)
    expected = FACT.IMMUTABLE_SOURCES[CORPUS_PATH]
    if identity["bytes"] != expected["bytes"] \
            or identity["sha256"] != expected["sha256"]:
        raise SchemaDefect(
            "the frozen corpus bytes changed; P0-R1 reuses the exact frozen "
            "35-cell / 70-member P0 corpus and its hashes")
    return validate_corpus_binding(corpus)


# ---------------------------------------------------------------------------
# Immutable history.
# ---------------------------------------------------------------------------

def validate_immutable_history(root=None):
    """No byte of the consumed P0-T namespace may be edited or regenerated."""
    return FACT.verify_immutable_sources(root=root)


def validate_historical_counter_snapshot(snapshot, root=None):
    """The immutable P0-T counter snapshot must be carried forward unchanged."""
    result = FACT.load_immutable(FACT.RESULT_PATH, root=root)
    published = result["counters"]
    if snapshot != published:
        differing = sorted(
            name for name in set(published) | set(snapshot)
            if published.get(name) != snapshot.get(name))
        raise SchemaDefect(
            "the historical P0-T counter snapshot was altered at %s; the 4,956 "
            "historical encodes remain cumulative and non-resettable"
            % ", ".join(differing))
    if published.get("tokenizer_encoded_sequences") != 4956:
        raise SchemaDefect(
            "the published P0-T encode count is no longer 4,956")
    return True


# ---------------------------------------------------------------------------
# Counters.
# ---------------------------------------------------------------------------

def validate_counter_progression(previous, current):
    """A cumulative counter never decreases and a construction event is never lost."""
    if not isinstance(previous, dict) or not isinstance(current, dict):
        raise SchemaDefect("counter snapshots must be mappings")
    for name in sorted(set(previous) | set(current)):
        if name not in ZERO_BEFORE_EXECUTION:
            raise SchemaDefect("unregistered counter %r" % name)
        before = previous.get(name, 0)
        after = current.get(name, 0)
        for value in (before, after):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise SchemaDefect(
                    "counter %r carries a non-natural value" % name)
        if after < before:
            raise SchemaDefect(
                "counter %r was reset from %d to %d; P0-R1 counters are "
                "cumulative and non-resettable" % (name, before, after))
    events = current.get("tokenizer_construction_events", 0)
    identities = current.get("distinct_tokenizer_identities_constructed", 0)
    if identities > events:
        raise SchemaDefect(
            "%d distinct tokenizer identities are recorded against %d "
            "construction events; a construction event was omitted"
            % (identities, events))
    for name in IDENTITY_CARDINALITY_COUNTERS:
        if current.get(name, 0) > 3:
            raise SchemaDefect(
                "%s exceeds the three pinned identities; an identity count is a "
                "set cardinality, never a load-event count" % name)
    return True


# ---------------------------------------------------------------------------
# Authority flags.
# ---------------------------------------------------------------------------

def validate_authority_flags(flags):
    """Every formal flag stays false; only the narrow P0-R1 flag may be true."""
    if not isinstance(flags, dict):
        raise SchemaDefect("the authority flag block must be a mapping")
    for name in FALSE_AUTHORITY_FLAGS:
        if name not in flags:
            raise SchemaDefect("the authority flag %r is not recorded" % name)
        if flags[name] is not False:
            raise SchemaDefect(
                "the authority flag %r is %r; it must remain false under this "
                "authority" % (name, flags[name]))
    for name in NULL_AUTHORITY_ITEMS:
        if name not in flags:
            raise SchemaDefect("the unresolved item %r is not recorded" % name)
        if flags[name] is not None:
            raise SchemaDefect(
                "the unresolved item %r is %r; it must remain null rather than "
                "zero, empty or false" % (name, flags[name]))
    if flags.get(PERMITTED_TRUE_AUTHORITY_FLAG) is not True:
        raise SchemaDefect(
            "the narrow %s flag must be recorded true and not yet consumed"
            % PERMITTED_TRUE_AUTHORITY_FLAG)
    if flags.get("p0_r1_pilot_execution_consumed") is not False:
        raise SchemaDefect(
            "the P0-R1 execution authorization must be recorded as not yet "
            "consumed in the calibration session")
    if flags.get("evidence_ledger_last_row") != EVIDENCE_LAST_ROW:
        raise SchemaDefect(
            "the evidence ledger tail must remain %s" % EVIDENCE_LAST_ROW)
    return True


def validate_evidence_ledger_unchanged(root=None):
    """paper/evidence_ledger.csv stays byte-identical and ends at EV-0016."""
    path = os.path.join(root or REPO_ROOT, *EVIDENCE_LEDGER.split("/"))
    if not os.path.exists(path):
        raise SchemaDefect("the evidence ledger is missing")
    with open(path, "rb") as handle:
        raw = handle.read()
    rows = [line for line in raw.decode("utf-8").splitlines() if line.strip()]
    last = rows[-1].split(",")[0] if rows else ""
    if last != EVIDENCE_LAST_ROW:
        raise SchemaDefect(
            "the evidence ledger ends at %r, not %r" % (last, EVIDENCE_LAST_ROW))
    if any(line.startswith("EV-0017") for line in rows):
        raise SchemaDefect("an EV-0017 row was written")
    return True


# ---------------------------------------------------------------------------
# The registered equivalence assertion.
# ---------------------------------------------------------------------------

def validate_equivalence_registration(registry):
    """The section 3.3 identity must be registered in full and unweakened."""
    boundary = registry.get("scoring_boundary")
    if not isinstance(boundary, dict):
        raise SchemaDefect("the registry carries no scoring boundary")
    proof = boundary.get("equivalence_proof")
    if not isinstance(proof, dict):
        raise SchemaDefect(
            "the full-sequence ranking equivalence assertion is missing")
    for field in REQUIRED_EQUIVALENCE_FIELDS:
        if field not in proof:
            raise SchemaDefect(
                "the equivalence assertion was weakened: %r is missing" % field)
    if proof["identity"] != REQUIRED_EQUIVALENCE_IDENTITY:
        raise SchemaDefect(
            "the equivalence identity was altered to %r" % proof["identity"])
    if proof["consequence"] != REQUIRED_EQUIVALENCE_CONSEQUENCE:
        raise SchemaDefect(
            "the equivalence consequence was altered to %r"
            % proof["consequence"])
    if len(proof.get("valid_because", [])) < 4:
        raise SchemaDefect(
            "the equivalence validity conditions were weakened")
    if len(proof.get("does_not_extend_to", [])) < 6:
        raise SchemaDefect(
            "the equivalence claim boundary was weakened")
    if "approximation" in proof["why_exact"].lower() \
            and "not an approximation" not in proof["why_exact"].lower():
        raise SchemaDefect(
            "the equivalence was downgraded from an exact factor cancellation")
    return True


def validate_scoring_boundary(registry):
    """The registered v0.6 scoring boundary must be complete and exact."""
    validate_equivalence_registration(registry)
    boundary = registry["scoring_boundary"]
    conditions = boundary.get("eligibility_conditions")
    if not isinstance(conditions, list) or len(conditions) != 5:
        raise SchemaDefect(
            "the five registered eligibility conditions of section 3.2 are "
            "incomplete")
    ids = [entry.get("id") for entry in conditions]
    if ids != ["SB-1", "SB-2", "SB-3", "SB-4", "SB-5"]:
        raise SchemaDefect("an eligibility condition was removed or reordered")
    visible = boundary.get("visible_answer_surface_unchanged", {})
    if visible.get("answer_cue") != "Answer:":
        raise SchemaDefect("the registered answer cue changed")
    surfaces = visible.get("candidate_surfaces")
    if surfaces != [" %s" % digit for digit in "0123456789"]:
        raise SchemaDefect("the registered candidate surfaces changed")
    if visible.get("each_candidate_carries_exactly_one_leading_u0020") is not True:
        raise SchemaDefect(
            "the registered single leading U+0020 was removed or moved")
    derived = boundary.get("derived_token_identities", {})
    if derived.get("tokenizer_encodes_performed_by_the_derivation") != 0:
        raise SchemaDefect(
            "the token identities were not derived with zero tokenizer encodes")
    for role, entry in sorted(derived.get("by_role", {}).items()):
        if entry.get("common_prefix_bytes") != "\u0020":
            raise SchemaDefect(
                "the common prefix of %s does not decode to exactly one "
                "registered U+0020" % role)
        if entry.get("eligible") is not True:
            raise SchemaDefect(
                "role %s does not satisfy the registered factorization" % role)
    for profile in registry["profiles"]:
        per_profile = profile.get("scoring_boundary")
        if not isinstance(per_profile, dict):
            raise SchemaDefect(
                "profile %s carries no scoring boundary" % profile["profile"])
        expected = (per_profile["registered_prompt_token_count"]
                    + per_profile["common_prefix_token_count"])
        if per_profile["scoring_context_token_count"] != expected:
            raise SchemaDefect(
                "profile %s does not reconcile its registered prompt token "
                "count with its scoring-context token count"
                % profile["profile"])
        if per_profile["common_prefix_token_count"] != (
                per_profile["common_prefix_token_count_per_scored_row"]
                * per_profile["scored_rows"]):
            raise SchemaDefect(
                "profile %s does not reconcile its per-row common-prefix rule "
                "with its aggregate common-prefix token count"
                % profile["profile"])
        if profile["profile"] in ("S2", "S3"):
            if per_profile["common_prefix_token_count_per_scored_row"] != 1:
                raise SchemaDefect(
                    "profile %s must teacher-force exactly one common-prefix "
                    "token per scored row" % profile["profile"])
        elif per_profile["common_prefix_token_count_per_scored_row"] != 0:
            raise SchemaDefect(
                "profile %s must not teacher-force a common-prefix token"
                % profile["profile"])
        if profile["profile"] == "S3":
            if per_profile.get(
                    "sequence_level_model_evaluations_per_scored_row") != 0:
                raise SchemaDefect(
                    "S3 must add exactly zero sequence-level model evaluations")
            if per_profile.get("tokens_processed") != 0:
                raise SchemaDefect(
                    "S3 must process exactly zero tokens of its own; it reuses "
                    "the S2 discriminant-position logit vector")
        elif per_profile.get("tokens_processed") != \
                per_profile["scoring_context_token_count"]:
            raise SchemaDefect(
                "profile %s does not process exactly its scoring context"
                % profile["profile"])
        if profile["profile"] == "S4" and per_profile.get(
                "participates_in_target_role_executability") is not False:
            raise SchemaDefect(
                "S4 is diagnostic-only and can never satisfy target-role "
                "executability")
    return True


# ---------------------------------------------------------------------------
# Document schemas.
# ---------------------------------------------------------------------------

SCORED_ROW_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version", "profile", "role", "row_id",
        "selected_complete_candidate_surface", "selected_discriminant_token",
        "restricted_scores", "registered_prompt_token_count",
        "common_prefix_token_count", "scoring_context_token_count",
        "sequence_level_model_evaluations", "reuses_row_id", "tie_break_order",
    ],
    "properties": {
        "schema_version": {"const": "study3-p0-r1-scored-row-v1",
                           "type": "string"},
        "profile": {"enum": ["S1", "S2", "S3"], "type": "string"},
        "role": {"enum": ["RT", "RL", "RI"], "type": "string"},
        "row_id": {"type": "string", "minLength": 1},
        "selected_complete_candidate_surface": {"type": "string",
                                                "minLength": 2},
        "selected_discriminant_token": {"type": "integer", "minimum": 0},
        "restricted_scores": {"type": "object"},
        "registered_prompt_token_count": {"type": "integer", "minimum": 1},
        "common_prefix_token_count": {"type": "integer", "minimum": 0,
                                      "maximum": 1},
        "scoring_context_token_count": {"type": "integer", "minimum": 1},
        "sequence_level_model_evaluations": {"type": "integer", "minimum": 0,
                                             "maximum": 1},
        "reuses_row_id": {"type": ["string", "null"]},
        "tie_break_order": {"type": "array", "minItems": 4},
    },
}

PRE_EXECUTION_RECEIPT_SCHEMA = {
    "type": "object",
    "additionalProperties": True,
    "required": [
        "schema_version", "document_class", "state", "authority",
        "draft_v0_6_candidate", "corpus", "p0_t_source_artifacts",
        "model_and_tokenizer_revisions", "container", "code_blobs", "counters",
        "caps", "authority_flags", "claim_boundary",
    ],
    "properties": {
        "schema_version": {"const": "study3-p0-r1-pre-execution-receipt-v1",
                           "type": "string"},
        "document_class": {"const": "study3_p0_r1_pre_execution_receipt",
                           "type": "string"},
        "state": {"const": "STUDY3_P0_R1_REGISTERED_AWAITING_REPLAY_GATE",
                  "type": "string"},
        "authority": {"type": "object"},
        "draft_v0_6_candidate": {"type": "object"},
        "corpus": {"type": "object"},
        "p0_t_source_artifacts": {"type": "array", "minItems": 3},
        "model_and_tokenizer_revisions": {"type": "array", "minItems": 3},
        "container": {"type": "object"},
        "code_blobs": {"type": "array", "minItems": 8},
        "counters": {"type": "object"},
        "caps": {"type": "object"},
        "authority_flags": {"type": "object"},
        "claim_boundary": {"type": "string", "minLength": 1},
    },
}


def validate_document(document, schema, label):
    errors = schema_errors(document, schema)
    if errors:
        raise SchemaDefect(
            "%s failed schema validation: %s" % (label, "; ".join(errors[:6])))
    return True


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
