"""Versioned eligibility classifier for Study 3 P0-R1.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` section 4.

This is the *successor* classifier. It does not import, call, wrap, subclass or
mutate the historical P0-T classifier, and it never edits the published P0-T
result. The historical role-level eligibility flag is deliberately not consulted:
it is the object being replaced.

The repaired rule computes eligibility at the **narrowest applicable key**:

======================================  ==========================================
quantity                                key
======================================  ==========================================
candidate-surface eligibility           role x profile
presentation-pair distinctness          role x profile x contrast
structural absence                      profile x contrast
target-role executability               role
======================================  ==========================================

Four invariants are enforced mechanically rather than trusted:

* an ineligible cell carries at least one exact, *local* reason. Every reason
  carries its own scope, and a reason whose scope is not a prefix of the cell it
  is attached to is a propagation defect, not a reason;
* ``S4`` is diagnostic-only and can never satisfy target-role executability;
* ``not_applicable`` is structural absence. It is never instantiated as a cell,
  never eligible, never ineligible, never a pass, never a zero, never a
  denominator row and never robustness evidence; and
* a failure never crosses a profile, a role or a contrast.
"""

import json

CLASSIFIER_VERSION = "study3-p0-r1-eligibility-classifier-v2"

ELIGIBLE = "eligible"
INELIGIBLE = "INELIGIBLE_TOKEN_IDS"
NOT_APPLICABLE = "not_applicable"

# The never-selectable diagnostic profile. Section 4 forbids it from satisfying
# target-role executability.
DIAGNOSTIC_ONLY_PROFILES = ("S4",)

# The profiles that may carry a genuine gate-bearing I3 contrast.
SELECTABLE_PROFILES = ("S1", "S2", "S3")

# The unambiguous successor stop label. The old label read as though *every*
# target role had lost every contrast; the registered semantics were the
# opposite quantifier.
STOP_SOME_ROLE_HAS_NO_EXECUTABLE_CONTRAST = (
    "STUDY3_P0_R1_STOPPED_SOME_TARGET_ROLE_HAS_NO_EXECUTABLE_GENUINE_I3_CONTRAST")

STOP_LABEL_SEMANTICS = (
    "one or more target roles has no executable genuine I3 contrast")

HISTORICAL_STOP_LABEL = (
    "STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE")

HISTORICAL_STOP_LABEL_STATUS = (
    "historical text attached to the consumed P0-T result only. It is never "
    "emitted again and it is never rewritten in place.")


class EligibilityDefect(Exception):
    """A fail-closed classifier or validator stop."""


def reason(code, detail, role=None, profile=None, contrast=None):
    """Build one exact, locally scoped reason."""
    if not code or not detail:
        raise EligibilityDefect("a reason needs both a code and a detail")
    return {
        "code": code,
        "detail": detail,
        "scope": {"role": role, "profile": profile, "contrast": contrast},
    }


def _scope_is_local_to(scope, role, profile, contrast):
    """A reason may only narrow the cell it is attached to, never cross it."""
    if scope.get("role") is not None and scope["role"] != role:
        return False
    if scope.get("profile") is not None and scope["profile"] != profile:
        return False
    if scope.get("contrast") is not None and scope["contrast"] != contrast:
        return False
    return True


# ---------------------------------------------------------------------------
# Narrowest-key quantities.
# ---------------------------------------------------------------------------

def structural_absence_index(records):
    """profile x contrast -> structural absence. Never role-scoped."""
    absent = {}
    for record in records:
        key = (record["profile"], record["contrast"])
        if record.get("structural_absence"):
            absent.setdefault(key, True)
            if record.get("members"):
                raise EligibilityDefect(
                    "structurally absent %s/%s carries members; not_applicable "
                    "is absence, never an instantiated row" % key)
        else:
            if absent.get(key):
                raise EligibilityDefect(
                    "%s/%s is recorded both structurally absent and "
                    "instantiated" % key)
            absent.setdefault(key, False)
    return absent


def candidate_surface_eligibility(factorization, s1_by_role):
    """role x profile -> candidate-surface eligibility, with local reasons.

    ``factorization`` is the replay document of ``p0_r1_factorization``; it
    carries the derived first-discriminative-token verdict per role. ``s1_by_role``
    carries the published S1 label-surface encodes per role and alphabet.
    """
    surface = {}
    by_role = {entry["role"]: entry for entry in factorization["roles"]}
    for role in sorted(set(by_role) | set(s1_by_role)):
        reasons = []
        alphabets = s1_by_role.get(role, {})
        if not alphabets:
            reasons.append(reason(
                "S1_CANDIDATE_SURFACES_UNOBSERVED",
                "no S1 label-surface encode is published for this role",
                role=role, profile="S1"))
        for alphabet in sorted(alphabets):
            body = alphabets[alphabet]
            if not body.get("all_single_token"):
                reasons.append(reason(
                    "S1_CANDIDATE_SURFACES_NOT_SINGLE_TOKEN",
                    "the %s label surfaces are not four single tokens"
                    % alphabet, role=role, profile="S1"))
            if not body.get("pairwise_distinct"):
                reasons.append(reason(
                    "S1_CANDIDATE_SURFACES_NOT_DISTINCT",
                    "the %s label surfaces are not four pairwise-distinct "
                    "tokens" % alphabet, role=role, profile="S1"))
        surface[(role, "S1")] = {
            "eligible": not reasons,
            "reasons": reasons,
        }

        entry = by_role.get(role)
        s23_reasons = []
        if entry is None:
            s23_reasons.append(reason(
                "S2_S3_FACTORIZATION_UNOBSERVED",
                "no S2/S3 candidate factorization is derived for this role",
                role=role))
        elif not entry["eligible"]:
            for text in entry["reasons"]:
                s23_reasons.append(reason(
                    "S2_S3_FIRST_DISCRIMINATIVE_TOKEN_FACTORIZATION_FAILED",
                    text, role=role))
        for profile in ("S2", "S3"):
            surface[(role, profile)] = {
                "eligible": not s23_reasons,
                "reasons": [dict(item, scope=dict(item["scope"],
                                                  profile=profile))
                            for item in s23_reasons],
            }
        surface[(role, "S4")] = {
            "eligible": True,
            "diagnostic_only": True,
            "reasons": [],
            "note": ("S4 has no closed candidate set; candidate-surface "
                     "eligibility does not apply and can never make S4 "
                     "count toward target-role executability"),
        }
    return surface


def pair_distinctness(records):
    """role x profile x contrast -> presentation-pair distinctness."""
    index = {}
    for record in records:
        if record.get("structural_absence"):
            continue
        key = (record["role"], record["profile"], record["contrast"])
        cell = index.setdefault(key, {"collision_rows": [], "checked_rows": 0})
        cell["checked_rows"] += 1
        if record.get("pair_bytes_distinct") \
                and not record.get("pair_token_ids_distinct"):
            cell["collision_rows"].append(
                record.get("row_id") or record.get("branch_id"))
    return index


# ---------------------------------------------------------------------------
# The matrix.
# ---------------------------------------------------------------------------

def build_matrix(records, factorization, s1_by_role):
    """Compute the corrected eligibility matrix at the narrowest keys."""
    absent = structural_absence_index(records)
    surface = candidate_surface_eligibility(factorization, s1_by_role)
    pairs = pair_distinctness(records)

    matrix = []
    for (role, profile, contrast), pair in sorted(pairs.items()):
        if absent.get((profile, contrast)):
            raise EligibilityDefect(
                "%s/%s is structurally absent but an instantiated cell was "
                "produced for role %s" % (profile, contrast, role))
        reasons = []
        surface_cell = surface.get((role, profile))
        if surface_cell is None:
            raise EligibilityDefect(
                "no candidate-surface verdict for %s/%s" % (role, profile))
        for item in surface_cell["reasons"]:
            if not _scope_is_local_to(item["scope"], role, profile, contrast):
                raise EligibilityDefect(
                    "candidate-surface reason %r would propagate from %r onto "
                    "%s/%s/%s" % (item["code"], item["scope"], role, profile,
                                  contrast))
            reasons.append(item)
        if pair["collision_rows"]:
            reasons.append(reason(
                "PRESENTATION_PAIR_TOKEN_IDS_COLLIDE",
                "a byte-distinct applicable pair produced identical full "
                "token-ID sequences in rows %s"
                % ", ".join(sorted(str(row) for row in pair["collision_rows"])),
                role=role, profile=profile, contrast=contrast))
        matrix.append({
            "role": role,
            "profile": profile,
            "contrast": contrast,
            "status": INELIGIBLE if reasons else ELIGIBLE,
            "reasons": reasons,
            "collision_rows": sorted(str(row) for row in pair["collision_rows"]),
            "checked_rows": pair["checked_rows"],
            "diagnostic_only": profile in DIAGNOSTIC_ONLY_PROFILES,
            "genuine_gate_bearing_i3_contrast":
                profile not in DIAGNOSTIC_ONLY_PROFILES,
        })
    return matrix


def structurally_absent_pairs(records):
    """The profile x contrast pairs recorded as structural absence."""
    absent = structural_absence_index(records)
    return [
        {
            "profile": profile,
            "contrast": contrast,
            "applicability": NOT_APPLICABLE,
            "instantiated": False,
            "counted": False,
            "semantics": (
                "structural absence. Never a pass, never a zero, never a "
                "denominator row and never robustness evidence."),
        }
        for (profile, contrast), value in sorted(absent.items()) if value
    ]


def target_role_executability(matrix):
    """role -> the eligible, genuine, gate-bearing I3 contrasts that remain."""
    executable = {}
    for cell in matrix:
        executable.setdefault(cell["role"], [])
        if cell["profile"] in DIAGNOSTIC_ONLY_PROFILES:
            continue
        if cell["profile"] not in SELECTABLE_PROFILES:
            continue
        if cell["status"] != ELIGIBLE:
            continue
        executable[cell["role"]].append(
            "%s/%s" % (cell["profile"], cell["contrast"]))
    return {role: sorted(values) for role, values in executable.items()}


def roles_without_executable_contrast(matrix, roles):
    executable = target_role_executability(matrix)
    return [role for role in roles if not executable.get(role)]


# ---------------------------------------------------------------------------
# The production validator.
# ---------------------------------------------------------------------------

def validate_matrix(matrix, roles=None):
    """Reject any matrix that violates a section 4 invariant.

    This is the production validator. Every negative mutation of section 8 must
    be rejected here, on live input, not in a test-local copy.
    """
    if not isinstance(matrix, list) or not matrix:
        raise EligibilityDefect("the eligibility matrix is empty")
    seen = set()
    for cell in matrix:
        for field in ("role", "profile", "contrast", "status", "reasons"):
            if field not in cell:
                raise EligibilityDefect(
                    "an eligibility cell is missing %r" % field)
        key = (cell["role"], cell["profile"], cell["contrast"])
        if key in seen:
            raise EligibilityDefect(
                "duplicate eligibility cell %s/%s/%s" % key)
        seen.add(key)
        if cell["status"] not in (ELIGIBLE, INELIGIBLE):
            raise EligibilityDefect(
                "%s/%s/%s carries status %r; not_applicable is structural "
                "absence and is never a cell status"
                % (key + (cell["status"],)))
        if cell["status"] == INELIGIBLE and not cell["reasons"]:
            raise EligibilityDefect(
                "%s/%s/%s is ineligible with an empty reason list; an "
                "ineligible row must carry at least one exact, local reason"
                % key)
        if cell["status"] == ELIGIBLE and cell["reasons"]:
            raise EligibilityDefect(
                "%s/%s/%s is eligible but carries reasons" % key)
        for item in cell["reasons"]:
            if not isinstance(item, dict) or "scope" not in item \
                    or not item.get("code") or not item.get("detail"):
                raise EligibilityDefect(
                    "%s/%s/%s carries a reason that is not an exact, scoped "
                    "reason" % key)
            if not _scope_is_local_to(item["scope"], *key):
                raise EligibilityDefect(
                    "%s/%s/%s carries reason %r scoped to %r; a failure in one "
                    "profile, role or contrast never propagates to another"
                    % (key + (item["code"], item["scope"])))
        if cell["profile"] in DIAGNOSTIC_ONLY_PROFILES:
            if cell.get("genuine_gate_bearing_i3_contrast"):
                raise EligibilityDefect(
                    "%s/%s/%s claims to be a genuine gate-bearing I3 contrast; "
                    "S4 is diagnostic-only and can never satisfy target-role "
                    "executability" % key)
            if not cell.get("diagnostic_only"):
                raise EligibilityDefect(
                    "%s/%s/%s does not carry the diagnostic-only marker" % key)
        if cell.get("status") == INELIGIBLE and not cell.get("collision_rows") \
                and all(item["code"] == "PRESENTATION_PAIR_TOKEN_IDS_COLLIDE"
                        for item in cell["reasons"]):
            raise EligibilityDefect(
                "%s/%s/%s cites a pair collision with no collision row" % key)
    if roles:
        for role in roles:
            if not any(cell["role"] == role for cell in matrix):
                raise EligibilityDefect(
                    "the matrix covers no cell for target role %s" % role)
    return True


def validate_no_propagation(matrix, historical_matrix):
    """Prove the specific P0-T propagation defect is gone on live input."""
    historical = {(cell["role"], cell["profile"], cell["contrast"]): cell
                  for cell in historical_matrix}
    repaired = []
    for cell in matrix:
        key = (cell["role"], cell["profile"], cell["contrast"])
        before = historical.get(key)
        if before is None:
            continue
        if before.get("status") == INELIGIBLE and not before.get("reasons"):
            if cell["status"] == INELIGIBLE and not cell["reasons"]:
                raise EligibilityDefect(
                    "%s/%s/%s is still ineligible with an empty reason list"
                    % key)
            repaired.append({
                "role": cell["role"],
                "profile": cell["profile"],
                "contrast": cell["contrast"],
                "historical_status": before.get("status"),
                "historical_reasons": list(before.get("reasons") or []),
                "corrected_status": cell["status"],
                "corrected_reasons": [item["code"] for item in cell["reasons"]],
            })
    return repaired


def classify(records, factorization, s1_by_role, roles):
    """Run the repaired classifier end to end and validate its own output."""
    matrix = build_matrix(records, factorization, s1_by_role)
    validate_matrix(matrix, roles=roles)
    executable = target_role_executability(matrix)
    missing = roles_without_executable_contrast(matrix, roles)
    return {
        "classifier_version": CLASSIFIER_VERSION,
        "eligibility_keys": {
            "candidate_surface_eligibility": "role x profile",
            "presentation_pair_distinctness": "role x profile x contrast",
            "structural_absence": "profile x contrast",
            "target_role_executability": "role",
        },
        "matrix": matrix,
        "structurally_absent": structurally_absent_pairs(records),
        "executable_genuine_i3_contrasts": executable,
        "roles_without_executable_contrast": missing,
        "diagnostic_only_profiles": list(DIAGNOSTIC_ONLY_PROFILES),
        "selectable_profiles": list(SELECTABLE_PROFILES),
        "stop_label_if_any_role_has_none":
            STOP_SOME_ROLE_HAS_NO_EXECUTABLE_CONTRAST,
        "stop_label_semantics": STOP_LABEL_SEMANTICS,
        "historical_stop_label": HISTORICAL_STOP_LABEL,
        "historical_stop_label_status": HISTORICAL_STOP_LABEL_STATUS,
        "not_applicable_semantics": (
            "structural absence. It can never become eligible, ineligible, a "
            "pass, a zero, a denominator row or robustness evidence."),
    }


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
