"""The frozen Phase 1.0D semantic-review v2 contract.

Why this is a separate package rather than an edit to
``jspace_observation.semantic_review``:

The v1 reviewer instrument, its rubric, its fixture bank and its terminal gate
are immutable history.  ``phase1_0d_review_build_provenance.json`` hashes
``src/jspace_observation/semantic_review/*.py`` into the bundle baked into the
locked v1 image, so adding one file to that package would break the v1 record
and, with it, the ability to prove what the v1 image contained.  v2 therefore
lives beside v1 and *imports* it.  Nothing here writes to a v1 path.

What v2 changes, exactly:

* a rewritten rubric whose commitment-selection rule is explicit, including the
  negative cases (prose after the last complete literal surface cannot retract
  the selection it makes);
* a fresh 20-fixture conformance bank with four fixtures per label;
* a 60/60 pass criterion with no majority rule and no tolerance;
* create-only Blob persistence of the gate receipt, including on mismatch.

What v2 does not change: the base protocol, the 300 task IDs, the three arms,
the locked generation image, the reviewer panel, or the request profiles.

This module establishes nothing scientific.  It loads bytes and refuses to
proceed when they are not the frozen bytes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from jspace_observation.semantic_review import addendum as v1

SCHEMA_VERSION = "phase1-0d-semantic-review-addendum/v2"
ADDENDUM_PATH = "docs/phase1_0d_semantic_review_addendum_v2.json"
RUBRIC_PATH = "docs/phase1_0d_semantic_review_rubric_v2.md"

FIXTURE_COUNT = 20
FIXTURES_PER_LABEL = 4
ROLE_COUNT = 3
REQUIRED_CALLS = FIXTURE_COUNT * ROLE_COUNT

# Re-exported so callers need one import, and so a v2 caller can never
# accidentally bind the v1 label set or the v1 presented form.
PRESENTED_FIELDS = v1.PRESENTED_FIELDS
LABELS = v1.LABELS
ROLES = v1.ROLES
AddendumError = v1.AddendumError
TransportError = v1.TransportError
MalformedResponseError = v1.MalformedResponseError

# The v1 bank is retired.  Naming it here makes silent reuse a load failure
# rather than a thing a reader has to notice.
RETIRED_V1_FIXTURE_IDS: frozenset[str] = frozenset(
    {
        "smoke_exact_correct",
        "smoke_equivalent_correct",
        "smoke_incorrect",
        "smoke_no_answer",
        "smoke_unresolved",
        "smoke_invalid",
    }
)


def canonical_bank(fixtures: Sequence[Mapping[str, Any]]) -> str:
    """The exact serialisation the frozen ``fixture_bank_sha256`` covers."""

    return json.dumps(
        list(fixtures), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def fixture_bank_sha256(fixtures: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(canonical_bank(fixtures).encode("utf-8")).hexdigest()


def _profile(role: str, raw: Mapping[str, Any]) -> v1.RoleProfile:
    return v1.RoleProfile(
        role=role,
        provider=str(raw["provider"]),
        api_kind=str(raw["api_kind"]),
        endpoint=str(raw["endpoint"]).rstrip("/"),
        path_candidates=tuple(str(path) for path in raw["path_candidates"]),
        api_version_candidates=tuple(str(v) for v in raw["api_version_candidates"]),
        deployment=str(raw["deployment"]),
        model=str(raw["model"]),
        model_version=str(raw["model_version"]),
        sku=str(raw["sku"]),
        region=str(raw["region"]),
        token_scope=str(raw["token_scope"]),
        request=dict(raw["request"]),
        max_visible_output_tokens=int(raw["max_visible_output_tokens"]),
        reasoning_content_fields=tuple(
            str(name) for name in raw.get("reasoning_content_fields", ())
        ),
    )


def _check_bank(fixtures: Sequence[Mapping[str, Any]], recorded_sha256: str) -> None:
    if len(fixtures) != FIXTURE_COUNT:
        raise AddendumError(
            f"the v2 bank holds {len(fixtures)} fixtures, expected {FIXTURE_COUNT}"
        )

    ids = [str(fixture["fixture_id"]) for fixture in fixtures]
    if len(set(ids)) != FIXTURE_COUNT:
        raise AddendumError("the v2 bank repeats a fixture id")

    reused = sorted(set(ids) & RETIRED_V1_FIXTURE_IDS)
    if reused:
        raise AddendumError(
            f"the retired v1 bank may not be reused as a v2 pass item: {reused}"
        )

    counts: dict[str, int] = {label: 0 for label in LABELS}
    for fixture in fixtures:
        label = str(fixture["expected_label"])
        if label not in counts:
            raise AddendumError(f"a v2 fixture registers an unknown label: {label!r}")
        counts[label] += 1
        row = fixture["row"]
        if tuple(sorted(row)) != tuple(sorted(PRESENTED_FIELDS)):
            raise AddendumError(
                f"v2 fixture {fixture['fixture_id']} does not carry exactly the "
                "four presented fields"
            )
        if str(row["record_id"]) != str(fixture["fixture_id"]):
            raise AddendumError(
                f"v2 fixture {fixture['fixture_id']} carries a different record_id"
            )
    unbalanced = {label: n for label, n in counts.items() if n != FIXTURES_PER_LABEL}
    if unbalanced:
        raise AddendumError(
            f"the v2 bank is not balanced at {FIXTURES_PER_LABEL} per label: {unbalanced}"
        )

    computed = fixture_bank_sha256(fixtures)
    if computed != recorded_sha256:
        raise AddendumError(
            f"the v2 fixture bank hashes to {computed}, addendum records "
            f"{recorded_sha256}"
        )


def assert_no_target_leakage(
    fixtures: Sequence[Mapping[str, Any]], task_ids: Sequence[str]
) -> None:
    """Refuse a bank that mentions any selected Phase 1.0D item.

    The conformance bank must be synthetic.  A fixture that quoted a target
    task id, or a target output, would make the smoke a peek at the experiment
    it is supposed to qualify a reviewer for.
    """

    haystack = canonical_bank(fixtures)
    hit = sorted({str(task_id) for task_id in task_ids if str(task_id) in haystack})
    if hit:
        raise AddendumError(f"the v2 bank quotes selected target task ids: {hit[:5]}")


def load_addendum_v2(project_root: Path) -> v1.Addendum:
    """Load, hash and validate the frozen v2 addendum and its rubric.

    Returns the v1 ``Addendum`` shape on purpose: every downstream helper
    (request building, label parsing, the deterministic review stages) is
    already written against it and does not need a v2 variant.
    """

    path = project_root / ADDENDUM_PATH
    rubric_path = project_root / RUBRIC_PATH
    document = json.loads(path.read_text(encoding="utf-8"))

    if document.get("schema_version") != SCHEMA_VERSION:
        raise AddendumError(
            f"addendum schema is {document.get('schema_version')!r}, "
            f"expected {SCHEMA_VERSION!r}"
        )
    if tuple(document["presented_fields"]) != PRESENTED_FIELDS:
        raise AddendumError("the v2 addendum presents fields the frozen form does not")
    if tuple(document["labels"]) != LABELS:
        raise AddendumError("the v2 addendum label set is not the frozen label set")
    if tuple(document["roles"]) != ROLES:
        raise AddendumError(
            "the v2 addendum must declare exactly primary/secondary/third"
        )

    rubric = rubric_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    rubric_sha256 = v1.sha256_file(rubric_path)
    if document["rubric_sha256"] != rubric_sha256:
        raise AddendumError(
            f"the v2 rubric hashes to {rubric_sha256}, addendum records "
            f"{document['rubric_sha256']}"
        )

    _check_bank(
        document["smoke_fixtures"],
        str(document["conformance_bank"]["fixture_bank_sha256"]),
    )

    criterion = document["smoke_rules"]["pass_criterion"]
    if int(criterion["exact_expected_label_matches"]) != REQUIRED_CALLS:
        raise AddendumError(
            "the v2 pass criterion is not the registered "
            f"{REQUIRED_CALLS}/{REQUIRED_CALLS}"
        )
    if document["smoke_rules"].get("no_majority_rule") is not True:
        raise AddendumError("the v2 addendum must forbid a majority rule")

    roles = {role: _profile(role, document["roles"][role]) for role in ROLES}
    seen: dict[str, str] = {}
    for role, profile in roles.items():
        key = f"{profile.provider}/{profile.deployment}"
        if key in seen:
            raise AddendumError(
                f"roles {seen[key]} and {role} share deployment {key}; "
                "one reviewer identity may not hold two roles"
            )
        seen[key] = role

    return v1.Addendum(
        document=document,
        sha256=v1.sha256_file(path),
        rubric=rubric,
        rubric_sha256=rubric_sha256,
        roles=roles,
    )
