"""Phase 1.0D semantic-review v2: the re-frozen reviewer instrument.

v1 remains untouched and immutable next door.  See ``addendum_v2`` for why
this is a sibling package rather than an edit.
"""

from __future__ import annotations

from jspace_observation.semantic_review_v2.addendum_v2 import (
    ADDENDUM_PATH,
    FIXTURE_COUNT,
    FIXTURES_PER_LABEL,
    LABELS,
    PRESENTED_FIELDS,
    REQUIRED_CALLS,
    ROLES,
    RUBRIC_PATH,
    SCHEMA_VERSION,
    assert_no_target_leakage,
    canonical_bank,
    fixture_bank_sha256,
    load_addendum_v2,
)

__all__ = [
    "ADDENDUM_PATH",
    "FIXTURE_COUNT",
    "FIXTURES_PER_LABEL",
    "LABELS",
    "PRESENTED_FIELDS",
    "REQUIRED_CALLS",
    "ROLES",
    "RUBRIC_PATH",
    "SCHEMA_VERSION",
    "assert_no_target_leakage",
    "canonical_bank",
    "fixture_bank_sha256",
    "load_addendum_v2",
]
