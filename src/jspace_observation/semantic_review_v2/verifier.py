"""Independent v2 recomputation from generations and sealed judgments."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..phase1_0d_execution import (
    annotate_review_selection,
    apply_judgments,
    build_decision,
    ingest_judgments,
)
from ..semantic_review.addendum import canonical_json, sha256_text


class IndependentVerificationError(RuntimeError):
    """The finalized pack differs from an independent frozen recomputation."""


def _counts(values: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def verify_final_result(
    *,
    source_records: Sequence[Mapping[str, Any]],
    finalized_records: Sequence[Mapping[str, Any]],
    decision: Mapping[str, Any],
    combined: Sequence[Mapping[str, Any]],
    required_secondary: Sequence[str],
    required_third: Sequence[str],
) -> dict[str, Any]:
    """Rebuild labels, cell metrics, gates, candidates and decision from inputs."""

    failures: list[str] = []
    source_ids = [str(row["record_id"]) for row in source_records]
    if len(source_ids) != len(set(source_ids)):
        failures.append("source records contain duplicate record IDs")

    by_role: dict[str, dict[str, str]] = {
        "primary": {},
        "secondary": {},
        "third": {},
    }
    for item in combined:
        role = str(item.get("role"))
        record_id = str(item.get("record_id"))
        if role not in by_role:
            failures.append(f"judgment has an unknown role: {role}")
            continue
        if record_id in by_role[role]:
            failures.append(f"duplicate {role} judgment for {record_id}")
            continue
        by_role[role][record_id] = str(item.get("label"))

    expected_coverage = {
        "primary": set(source_ids),
        "secondary": set(str(value) for value in required_secondary),
        "third": set(str(value) for value in required_third),
    }
    for role, expected in expected_coverage.items():
        actual = set(by_role[role])
        if actual != expected:
            failures.append(f"{role} judgments differ from the registered coverage")
    if failures:
        raise IndependentVerificationError("; ".join(failures))

    ingested = ingest_judgments(source_records, combined)
    selected = annotate_review_selection(ingested)
    recomputed_secondary = sorted(
        str(row["record_id"])
        for row in selected
        if row["evaluation"]["secondary_review_required"]
    )
    if recomputed_secondary != sorted(str(value) for value in required_secondary):
        raise IndependentVerificationError(
            "secondary selection differs from independent recomputation"
        )

    recomputed_third = sorted(
        record_id
        for record_id, secondary_label in by_role["secondary"].items()
        if by_role["primary"][record_id] != secondary_label
    )
    if recomputed_third != sorted(str(value) for value in required_third):
        raise IndependentVerificationError(
            "third-review disagreements differ from independent recomputation"
        )

    recomputed_records = apply_judgments(selected)
    pending = [
        str(row["record_id"])
        for row in recomputed_records
        if row["evaluation"].get("arbitration_pending") is True
    ]
    if pending:
        raise IndependentVerificationError(
            f"{len(pending)} rows remain pending after registered arbitration"
        )
    if canonical_json(list(finalized_records)) != canonical_json(recomputed_records):
        raise IndependentVerificationError(
            "finalized records differ from independent judgment ingestion and arbitration"
        )

    recomputed_decision = build_decision(recomputed_records)
    observed_decision = dict(decision)
    provenance = observed_decision.pop("provenance", None)
    if not isinstance(provenance, Mapping):
        raise IndependentVerificationError("final decision carries no provenance object")
    if canonical_json(observed_decision) != canonical_json(recomputed_decision):
        raise IndependentVerificationError(
            "final decision differs from independent metric and gate recomputation"
        )

    labels = [
        str(row["evaluation"]["final_label"]) for row in recomputed_records
    ]
    return {
        "records": len(recomputed_records),
        "final_label_counts": _counts(labels),
        "cell_count": recomputed_decision["cell_count"],
        "cells_sha256": sha256_text(
            canonical_json({"cells": recomputed_decision["cells"]})
        ),
        "decision_result": recomputed_decision["result"],
        "rq2_pilot_candidates": recomputed_decision["rq2_pilot_candidates"],
        "rq2_pilot_candidate_count": len(
            recomputed_decision["rq2_pilot_candidates"]
        ),
        "records_sha256": sha256_text(canonical_json(recomputed_records)),
        "judgments_sha256": sha256_text(canonical_json(list(combined))),
        "decision_sha256": sha256_text(canonical_json(dict(decision))),
        "recomputed_decision_sha256": sha256_text(
            canonical_json(recomputed_decision)
        ),
        "recomputed_only": True,
        "changed_nothing": True,
    }
