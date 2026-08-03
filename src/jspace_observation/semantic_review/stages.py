"""The nine deterministic stages of the Phase 1.0D semantic review.

This is an execution wrapper.  Every scientific decision -- who needs a second
opinion, how two labels arbitrate, which cells pass -- already exists in the
frozen protected modules and is *called* here.  Nothing in this file recomputes
one of them, and the tests assert that the frozen functions are the ones doing
the work.

The stages exist separately because the ordering is itself a control: the
secondary reviewer must not be able to see a primary label, and the third must
not be able to see either prior label or the fact that they disagreed.  Keeping
selection in one stage and inference in the next makes that boundary something
you can point at rather than something you have to trust.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..phase1_0d_confirmation import (
    REVIEW_FORM_PRESENTED_FIELDS,
    SEMANTIC_LABELS,
)
from ..phase1_0d_execution import annotate_review_selection
from .addendum import (
    Addendum,
    AddendumError,
    MalformedResponseError,
    RoleProfile,
    build_request,
    canonical_json,
    judgment as build_judgment,
    parse_label,
    sha256_text,
    visible_token_count,
)

FROZEN_PROTOCOL_SHA256 = (
    "25e96401f8e53b913872eaf77e5585a1b34142c5a73765eba4711a3659c113d8"
)
FROZEN_TASK_IDS_SHA256 = (
    "0d3fe6add211a381a321ea974502d262faf65312dc504e2acceb7c6556b1f524"
)
GENERATION_IMAGE_DIGEST = (
    "sha256:1f504579e8bd3a7a4abb3643d3c153c53cf31e43a4b1a44d1332c37481166aa4"
)
MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
MODEL_REVISION = "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"

AWAITING_REVIEW = "AWAITING_SEMANTIC_REVIEW"
EXPECTED_ITEMS = 300
EXPECTED_RECORDS = 900
EXPECTED_ARMS = 3
MANIFEST_NAME = "artifact_manifest.json"


class StageError(RuntimeError):
    """A stage obligation could not be met.  Never downgraded to a label."""


class IntegrityError(RuntimeError):
    """Terminal state ``BLOCKED_ON_RESULT_PACK_INTEGRITY``."""


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _sha256_bytes(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Stage 1 -- verify-generation-pack (section 4.1)
# ---------------------------------------------------------------------------


def verify_generation_pack(pack_dir: Path) -> dict[str, Any]:
    """Refuse to show a reviewer anything until the pack is exactly right."""

    failures: list[str] = []
    manifest_path = pack_dir / MANIFEST_NAME
    if not manifest_path.exists():
        raise StageError(f"no {MANIFEST_NAME} in {pack_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for entry in manifest["files"]:
        name = str(entry["name"])
        target = pack_dir / name
        if not target.exists():
            failures.append(f"manifest lists a missing file: {name}")
            continue
        if name == MANIFEST_NAME:
            continue  # the manifest hashes itself before it is written
        actual = _sha256_bytes(target.read_bytes().replace(b"\r\n", b"\n"))
        if actual != str(entry["sha256"]):
            failures.append(f"{name} hashes to {actual}, manifest records {entry['sha256']}")

    snapshot = json.loads((pack_dir / "00_protocol_snapshot.json").read_text("utf-8"))
    snapshot = snapshot.get("snapshot", snapshot)
    if snapshot.get("protocol_sha256") != FROZEN_PROTOCOL_SHA256:
        failures.append(
            f"pack protocol is {snapshot.get('protocol_sha256')}, frozen is "
            f"{FROZEN_PROTOCOL_SHA256}"
        )
    task_ids_sha256 = snapshot.get("selection", {}).get("task_ids_sha256")
    if task_ids_sha256 != FROZEN_TASK_IDS_SHA256:
        failures.append(
            f"pack task ids hash to {task_ids_sha256}, frozen is {FROZEN_TASK_IDS_SHA256}"
        )

    decision = json.loads((pack_dir / "05_decision.json").read_text("utf-8"))
    if decision.get("result") != AWAITING_REVIEW:
        failures.append(
            f"pack status is {decision.get('result')!r}, expected {AWAITING_REVIEW!r}"
        )

    selection = json.loads((pack_dir / "01_selection.json").read_text("utf-8"))
    if int(selection.get("item_count", -1)) != EXPECTED_ITEMS:
        failures.append(f"pack selects {selection.get('item_count')} items, expected 300")

    provenance = selection.get("provenance", {})
    if provenance.get("image_digest") != GENERATION_IMAGE_DIGEST:
        failures.append(
            f"pack image digest is {provenance.get('image_digest')}, "
            f"expected {GENERATION_IMAGE_DIGEST}"
        )
    if snapshot.get("model_id") != MODEL_ID:
        failures.append(f"pack model is {snapshot.get('model_id')}, expected {MODEL_ID}")
    if snapshot.get("model_revision") != MODEL_REVISION:
        failures.append(
            f"pack revision is {snapshot.get('model_revision')}, expected {MODEL_REVISION}"
        )

    records = _load_jsonl(pack_dir / "02_records.jsonl")
    record_ids = [str(row["record_id"]) for row in records]
    if len(records) != EXPECTED_RECORDS:
        failures.append(f"pack carries {len(records)} records, expected 900")
    if len(set(record_ids)) != len(record_ids):
        failures.append("pack record ids are not unique")

    by_item: dict[str, set[str]] = {}
    for row in records:
        by_item.setdefault(str(row["task_id"]), set()).add(str(row["arm_id"]))
    wrong = sorted(item for item, arms in by_item.items() if len(arms) != EXPECTED_ARMS)
    if wrong:
        failures.append(f"{len(wrong)} items do not carry exactly three arms")
    if len(by_item) != EXPECTED_ITEMS:
        failures.append(f"pack covers {len(by_item)} items, expected 300")

    labelled = [
        str(row["record_id"])
        for row in records
        if any(
            row["evaluation"].get(key) is not None
            for key in ("primary_label", "secondary_label", "final_label")
        )
    ]
    if labelled:
        failures.append(f"{len(labelled)} records already carry a label")

    form = _load_jsonl(pack_dir / "03_review_form.jsonl")
    if len(form) != EXPECTED_RECORDS:
        failures.append(f"review form carries {len(form)} rows, expected 900")
    for row in form:
        if set(row) != set(REVIEW_FORM_PRESENTED_FIELDS):
            failures.append("a review-form row does not carry exactly the four fields")
            break

    form_by_id = {str(row["record_id"]): row for row in form}
    record_by_id = {str(row["record_id"]): row for row in records}
    if set(form_by_id) != set(record_by_id):
        failures.append("review form and records do not bind one-to-one by record id")
    else:
        for record_id, row in form_by_id.items():
            record = record_by_id[record_id]
            if str(row["registered_answer"]) != str(record["registered_answer"]):
                failures.append(f"{record_id}: review form answer differs from the record")
                break
            if str(row["output_text"]) != str(record["output_text"]):
                failures.append(f"{record_id}: review form output differs from the record")
                break

    if failures:
        raise StageError("; ".join(failures))

    return {
        "pack_dir": str(pack_dir),
        "manifest_sha256": _sha256_bytes(
            manifest_path.read_bytes().replace(b"\r\n", b"\n")
        ),
        "records_sha256": _sha256_bytes(
            (pack_dir / "02_records.jsonl").read_bytes().replace(b"\r\n", b"\n")
        ),
        "review_form_sha256": _sha256_bytes(
            (pack_dir / "03_review_form.jsonl").read_bytes().replace(b"\r\n", b"\n")
        ),
        "protocol_sha256": FROZEN_PROTOCOL_SHA256,
        "task_ids_sha256": FROZEN_TASK_IDS_SHA256,
        "records": EXPECTED_RECORDS,
        "items": EXPECTED_ITEMS,
        "status": AWAITING_REVIEW,
        "failed_generations_are_retained": True,
        "note": (
            "a failed target generation is carried to review as an empty row, so "
            "all 900 rows stay in the denominator"
        ),
    }


# ---------------------------------------------------------------------------
# Stages 2, 4, 6 -- the three review passes
# ---------------------------------------------------------------------------


@dataclass
class ReviewOutcome:
    judgments: list[dict[str, str]] = field(default_factory=list)
    receipts: list[dict[str, Any]] = field(default_factory=list)
    label_counts: dict[str, int] = field(default_factory=dict)
    retries: int = 0
    requests: int = 0


def review_rows(
    *,
    rows: Sequence[Mapping[str, Any]],
    profile: RoleProfile,
    addendum: Addendum,
    caller: Callable[[RoleProfile, Mapping[str, Any]], Any],
    max_workers: int | None = None,
) -> ReviewOutcome:
    """Run one pinned deployment over exactly these rows, one row per request."""

    workers = max_workers or addendum.max_in_flight
    ordered = sorted(rows, key=lambda row: str(row["record_id"]))

    def _one(row: Mapping[str, Any]) -> tuple[Mapping[str, Any], Any]:
        body = build_request(profile, addendum, row)
        return row, caller(profile, body)

    outcome = ReviewOutcome()
    results: list[tuple[Mapping[str, Any], Any]] = []
    if ordered:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            results = list(pool.map(_one, ordered))

    for row, response in results:
        label = parse_label(response.payload, profile)
        visible = visible_token_count(response.payload)
        if visible is not None and visible > profile.max_visible_output_tokens:
            raise MalformedResponseError(
                f"{row['record_id']} returned {visible} visible tokens, "
                f"cap is {profile.max_visible_output_tokens}"
            )
        outcome.judgments.append(
            build_judgment(
                str(row["record_id"]), profile.role, label, profile.reviewer_id
            )
        )
        outcome.receipts.append(
            {
                "record_id": str(row["record_id"]),
                "role": profile.role,
                "deployment": profile.deployment,
                "model": profile.model,
                "model_version": profile.model_version,
                "api_version": response.api_version,
                "path": response.path,
                "request_sha256": response.request_sha256,
                "response_sha256": response.response_sha256,
                "provider_model": response.payload.get("model"),
                "system_fingerprint": response.payload.get("system_fingerprint"),
                "provider_request_id": response.payload.get("id"),
                "usage": response.payload.get("usage"),
                "visible_completion_tokens": visible,
                "latency_seconds": round(response.latency_seconds, 3),
                "retries": response.retries,
                "status": response.status,
                "label": label,
            }
        )
        outcome.retries += response.retries
        outcome.requests += 1 + response.retries
        outcome.label_counts[label] = outcome.label_counts.get(label, 0) + 1

    outcome.judgments.sort(key=lambda item: item["record_id"])
    outcome.receipts.sort(key=lambda item: item["record_id"])
    return outcome


def rows_for(form: Sequence[Mapping[str, Any]], ids: Sequence[str]) -> list[dict[str, Any]]:
    """Select original four-field rows by id, adding nothing."""

    wanted = set(ids)
    by_id = {str(row["record_id"]): row for row in form}
    missing = sorted(wanted - set(by_id))
    if missing:
        raise StageError(f"review form has no row for: {missing[:5]}")
    return [
        {field: by_id[record_id][field] for field in REVIEW_FORM_PRESENTED_FIELDS}
        for record_id in sorted(wanted)
    ]


# ---------------------------------------------------------------------------
# Stage 3 -- select-secondary (section 4.3)
# ---------------------------------------------------------------------------


def select_secondary(
    records: Sequence[Mapping[str, Any]],
    primary_judgments: Sequence[Mapping[str, Any]],
    addendum: Addendum,
) -> dict[str, Any]:
    """Attach only the primary labels, then call the frozen selector."""

    by_id = {str(item["record_id"]): item for item in primary_judgments}
    if set(by_id) != {str(row["record_id"]) for row in records}:
        raise StageError("secondary selection needs exactly one primary judgment per row")

    staged: list[dict[str, Any]] = []
    for record in records:
        row = {
            key: dict(value) if isinstance(value, dict) else value
            for key, value in record.items()
        }
        judgment = by_id[str(row["record_id"])]
        row["evaluation"]["primary_label"] = judgment["label"]
        row["evaluation"]["primary_reviewer_id"] = judgment["reviewer_id"]
        staged.append(row)

    annotated = annotate_review_selection(staged)

    forced = sorted(
        str(row["record_id"])
        for row in annotated
        if row["evaluation"]["secondary_review_forced"]
    )
    sampled = sorted(
        str(row["record_id"])
        for row in annotated
        if row["evaluation"]["secondary_review_sampled"]
    )
    required = sorted(
        str(row["record_id"])
        for row in annotated
        if row["evaluation"]["secondary_review_required"]
    )

    expected_sampled = int(addendum.coverage["sampled_secondary_rows"])
    if len(sampled) != expected_sampled:
        raise StageError(
            f"the stratified sample is {len(sampled)} rows; the registered design "
            f"fixes it at {expected_sampled}"
        )
    if len(required) < expected_sampled:
        raise StageError("the required secondary set is smaller than the fixed sample")

    return {
        "required_ids": required,
        "forced_ids": forced,
        "sampled_ids": sampled,
        "required_count": len(required),
        "forced_count": len(forced),
        "sampled_count": len(sampled),
        "overlap_count": len(set(forced) & set(sampled)),
        "selector": "phase1_0d_execution.annotate_review_selection",
        "primary_label_counts": _counts(item["label"] for item in primary_judgments),
        "note": (
            "selection is a function of the primary labels, the frozen parser "
            "routing comparison and a hash-ranked stratified sample fixed before "
            "any label existed"
        ),
    }


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))


# ---------------------------------------------------------------------------
# Stage 5 -- select-third (section 4.4)
# ---------------------------------------------------------------------------


def select_third(
    primary_judgments: Sequence[Mapping[str, Any]],
    secondary_judgments: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Exactly the rows where the first two pinned reviewers disagree."""

    primary = {str(item["record_id"]): str(item["label"]) for item in primary_judgments}
    secondary = {
        str(item["record_id"]): str(item["label"]) for item in secondary_judgments
    }
    unknown = sorted(set(secondary) - set(primary))
    if unknown:
        raise StageError(f"secondary judgments for rows with no primary: {unknown[:5]}")

    disagreement = sorted(
        record_id for record_id, label in secondary.items() if primary[record_id] != label
    )
    return {
        "required_ids": disagreement,
        "required_count": len(disagreement),
        "agreement_count": len(secondary) - len(disagreement),
        "secondary_count": len(secondary),
        "note": (
            "the third reviewer sees only the original four fields: not either "
            "prior label, not the disagreement, not the parser route, not the arm"
        ),
    }


# ---------------------------------------------------------------------------
# Stage 7 -- verify-judgments (section 4.5)
# ---------------------------------------------------------------------------


def verify_judgments(
    *,
    record_ids: Sequence[str],
    primary: Sequence[Mapping[str, Any]],
    secondary: Sequence[Mapping[str, Any]],
    third: Sequence[Mapping[str, Any]],
    required_secondary: Sequence[str],
    required_third: Sequence[str],
    addendum: Addendum,
    receipts_by_role: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Assert exact role coverage before anything is finalized."""

    failures: list[str] = []
    expected = {
        "primary": sorted(str(value) for value in record_ids),
        "secondary": sorted(str(value) for value in required_secondary),
        "third": sorted(str(value) for value in required_third),
    }
    actual = {
        "primary": sorted(str(item["record_id"]) for item in primary),
        "secondary": sorted(str(item["record_id"]) for item in secondary),
        "third": sorted(str(item["record_id"]) for item in third),
    }
    for role in ("primary", "secondary", "third"):
        if actual[role] != expected[role]:
            extra = sorted(set(actual[role]) - set(expected[role]))
            missing = sorted(set(expected[role]) - set(actual[role]))
            failures.append(
                f"{role} coverage is wrong: {len(extra)} unrequired, {len(missing)} missing"
            )
        if len(actual[role]) != len(set(actual[role])):
            failures.append(f"{role} carries a duplicate row/role pair")

    reviewer_ids = {
        role: {str(item["reviewer_id"]) for item in judgments}
        for role, judgments in (
            ("primary", primary),
            ("secondary", secondary),
            ("third", third),
        )
    }
    for role, ids in reviewer_ids.items():
        if len(ids) > 1:
            failures.append(f"{role} used more than one reviewer identity: {sorted(ids)}")
        expected_id = addendum.roles[role].reviewer_id
        if ids and ids != {expected_id}:
            failures.append(f"{role} reviewer id is {sorted(ids)}, expected {expected_id}")

    used = [next(iter(ids)) for ids in reviewer_ids.values() if ids]
    if len(used) != len(set(used)):
        failures.append("one reviewer identity holds two roles")

    for role, judgments in (("primary", primary), ("secondary", secondary), ("third", third)):
        receipts = {str(item["record_id"]) for item in receipts_by_role.get(role, ())}
        judged = {str(item["record_id"]) for item in judgments}
        if receipts != judged:
            failures.append(
                f"{role} has {len(judged)} judgments but {len(receipts)} raw responses"
            )
        for item in judgments:
            if str(item["label"]) not in SEMANTIC_LABELS:
                failures.append(f"{role} produced an unregistered label")
                break

    for role, receipts in receipts_by_role.items():
        profile = addendum.roles[role]
        for receipt in receipts:
            if str(receipt["deployment"]) != profile.deployment:
                failures.append(f"{role} response came from {receipt['deployment']}")
                break
            if str(receipt["model_version"]) != profile.model_version:
                failures.append(f"{role} response came from a different model version")
                break

    if failures:
        raise StageError("; ".join(failures))

    return {
        "primary_count": len(actual["primary"]),
        "secondary_count": len(actual["secondary"]),
        "third_count": len(actual["third"]),
        "reviewer_ids": {role: sorted(ids) for role, ids in reviewer_ids.items()},
        "request_profile_sha256": {
            role: addendum.roles[role].request_profile_sha256()
            for role in ("primary", "secondary", "third")
        },
        "no_provider_substitution": True,
        "no_prohibited_field_sent": True,
        "every_judgment_has_one_raw_response": True,
    }


def combine_judgments(
    primary: Sequence[Mapping[str, Any]],
    secondary: Sequence[Mapping[str, Any]],
    third: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """The exact closed-form judgment set handed to the frozen finalizer."""

    combined = [dict(item) for item in (*primary, *secondary, *third)]
    combined.sort(key=lambda item: (item["record_id"], item["role"]))
    return combined


# ---------------------------------------------------------------------------
# Stage 9 -- export-result-bundle (section 4.6)
# ---------------------------------------------------------------------------


def outer_receipt(**parts: Any) -> dict[str, Any]:
    """Bind the generation bytes, the reviewer receipts and the final pack.

    The frozen finalizer computes the result but does not make its own source
    manifest part of its provenance, so this receipt is what stops a final pack
    from being readable as the conclusion of a *different* generation run.
    """

    document = dict(parts)
    document.setdefault(
        "claim_boundary",
        "binds bytes to bytes; establishes nothing about reviewer accuracy, "
        "nothing about hidden reasoning, and nothing about a 'J-space'",
    )
    return document


def bundle_manifest(files: Mapping[str, bytes], run_id: str) -> dict[str, Any]:
    """The outer manifest, written last, hashing everything beside it."""

    entries = [
        {"name": name, "sha256": _sha256_bytes(payload.replace(b"\r\n", b"\n"))}
        for name, payload in sorted(files.items())
    ]
    return {
        "artifact": "phase1_0d_semantic_review_bundle",
        "run_id": run_id,
        "files": entries,
        "file_count": len(entries),
        "manifest_written_last": True,
        "upload_semantics": "create-only; an existing prefix is never overwritten",
    }


def independent_check(
    *,
    records: Sequence[Mapping[str, Any]],
    decision: Mapping[str, Any],
    combined: Sequence[Mapping[str, Any]],
    required_secondary: Sequence[str],
    required_third: Sequence[str],
) -> dict[str, Any]:
    """Recompute counts and hashes over the completed pack.

    It may recompute.  It may not choose: a mismatch stops as
    ``BLOCKED_ON_RESULT_PACK_INTEGRITY`` and preserves both objects rather than
    picking the more favourable one.
    """

    failures: list[str] = []
    by_role: dict[str, set[str]] = {}
    for item in combined:
        by_role.setdefault(str(item["role"]), set()).add(str(item["record_id"]))

    if by_role.get("primary", set()) != {str(row["record_id"]) for row in records}:
        failures.append("primary judgments do not cover exactly the records")
    if by_role.get("secondary", set()) != set(required_secondary):
        failures.append("secondary judgments are not exactly the required set")
    if by_role.get("third", set()) != set(required_third):
        failures.append("third judgments are not exactly the disagreement set")

    finals = _counts(row["evaluation"]["final_label"] for row in records)
    unlabelled = [
        str(row["record_id"])
        for row in records
        if row["evaluation"].get("final_label") is None
    ]
    if unlabelled:
        failures.append(f"{len(unlabelled)} rows carry no final label")

    candidates = decision.get("rq2_pilot_candidates")
    if candidates is None:
        failures.append("the decision carries no pilot-candidate list")

    if failures:
        raise IntegrityError("; ".join(failures))

    return {
        "records": len(records),
        "final_label_counts": finals,
        "decision_result": decision.get("result"),
        "rq2_pilot_candidate_count": len(candidates or []),
        "decision_sha256": sha256_text(canonical_json(dict(decision))),
        "recomputed_only": True,
        "changed_nothing": True,
    }
