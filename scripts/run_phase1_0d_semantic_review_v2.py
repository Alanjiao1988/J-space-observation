#!/usr/bin/env python
"""Container entrypoint for the Phase 1.0D semantic review, v2 instrument.

Three modes, deliberately separate processes:

``qualify``
    One trivial synthetic request per role, proving the exact pinned
    deployments still answer over a registered route with managed-identity
    authentication.  Section 10.1.
``smoke``
    The 20 registered fixtures against all three roles: 60 isolated calls, one
    prospectively registered batch, 60/60 or the route closes.  Section 10.2.
``review``
    The nine deterministic stages over one verified generation pack, licensed
    only by a persisted 60/60 gate receipt.  Sections 11 and 12.

Three things are different from the v1 runner, and each of them exists because
the v1 round demonstrated the need:

*Evidence survives failure.*  L-51 records that the v1 receipts died with the
ephemeral replica because the job stopped before its upload stage.  Here the
complete receipt and its manifest are uploaded create-only **before** the
verdict is applied, so a mismatch is preserved rather than lost, and the
manifest is written last so a partial upload can never read as complete.

*The batch completes.*  Section 10.2 registers 60 calls in advance.  An early
mismatch, a malformed envelope or an exhausted transport retry is recorded as
that pair's outcome and the remaining registered calls still run.  Cancelling
them would turn a fixed denominator into one chosen after seeing the data.

*Qualification does not consume a fixture.*  v1 qualified on
``smoke_fixtures[0]``, which under the v2 batch rule would submit that pair
twice.  The probe below is synthetic, outside the bank, and asserted to be so.

Nothing in ``qualify`` or ``smoke`` can reach target storage: the blob handle
they receive exposes create-only writes under one registered gate prefix and
nothing else, and the pack-download helper is imported only inside ``review``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from jspace_observation.phase1_0d_confirmation import (  # noqa: E402
    REVIEW_FORM_PRESENTED_FIELDS,
)
from jspace_observation.semantic_review import addendum as contract  # noqa: E402
from jspace_observation.semantic_review import transport  # noqa: E402
from jspace_observation.semantic_review_v2 import addendum_v2  # noqa: E402

# One trivial synthetic exchange, outside the registered bank on purpose.
QUALIFICATION_PROBE: dict[str, str] = {
    "record_id": "v2_qualification_probe",
    "question": "What is 1 + 1?",
    "registered_answer": "2",
    "output_text": "Final answer: 2",
}

TERMINAL_PERSISTENCE = "BLOCKED_ON_PHASE_1_0D_RV2_GATE_EVIDENCE_PERSISTENCE"
TERMINAL_UNQUALIFIED = "CLOSED_PHASE_1_0D_WITHOUT_GENERATION_REVIEW_INSTRUMENT_UNQUALIFIED"
TERMINAL_PROVIDER = "CLOSED_PHASE_1_0D_WITHOUT_GENERATION_REVIEW_PROVIDER_UNAVAILABLE"


class GateEvidenceError(RuntimeError):
    """Raised when gate evidence exists but cannot be persisted."""


def _write(path: Path, payload: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


class GatePublisher:
    """Create-only writes under exactly one registered gate prefix.

    This is a capability boundary, not a convention.  ``qualify`` and ``smoke``
    never hold an object that can list or read a blob, so the isolation clause
    in the addendum ("no code path that lists or reads target-generation
    storage") is a property of the process rather than a promise about it.
    """

    def __init__(self, account: str, container: str, prefix: str, tokens: Any) -> None:
        if not prefix or prefix.strip("/") != prefix.strip():
            raise GateEvidenceError(f"refusing an unnormalised gate prefix: {prefix!r}")
        self._client = transport.BlobClient(account, container, tokens)
        self._prefix = prefix.rstrip("/")
        self.account = account
        self.container = container

    @property
    def prefix(self) -> str:
        return self._prefix

    def publish(self, files: Mapping[str, bytes], run_id: str) -> dict[str, Any]:
        """Upload every file, then the manifest that hashes them."""

        from jspace_observation.semantic_review import stages  # noqa: PLC0415

        manifest = stages.bundle_manifest(files, run_id)
        uploaded: list[str] = []
        for name in sorted(files):
            self._client.put_create_only(f"{self._prefix}/{name}", files[name])
            uploaded.append(name)
        manifest_bytes = contract.canonical_json(manifest).encode("utf-8")
        self._client.put_create_only(
            f"{self._prefix}/artifact_manifest.json", manifest_bytes
        )
        return {
            "account": self.account,
            "container": self.container,
            "prefix": self._prefix,
            "uploaded": uploaded,
            "uploaded_count": len(uploaded),
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "manifest_written_last": True,
            "create_only": True,
            "manifest": manifest,
        }


class GateReader:
    """Read exactly one registered gate prefix and nothing beside it."""

    def __init__(self, account: str, container: str, prefix: str, tokens: Any) -> None:
        normalised = prefix.rstrip("/")
        if not normalised or normalised != prefix.strip().rstrip("/"):
            raise GateEvidenceError(f"refusing an unnormalised gate prefix: {prefix!r}")
        self._client = transport.BlobClient(account, container, tokens)
        self._prefix = normalised

    @property
    def prefix(self) -> str:
        return self._prefix

    def get(self, name: str) -> bytes:
        expected = f"{self._prefix}/"
        if not name.startswith(expected) or name == expected:
            raise GateEvidenceError(
                f"gate reader for {self._prefix!r} refuses {name!r}"
            )
        return self._client.get(name)


class LiveCaller:
    """Calls one pinned deployment, remembering the route that answered."""

    def __init__(self, book: contract.Addendum, tokens: transport.TokenProvider) -> None:
        self._addendum = book
        self._tokens = tokens
        self.resolved: dict[str, tuple[str, str]] = {}

    def call_route(
        self,
        profile: contract.RoleProfile,
        body: Mapping[str, Any],
        path: str,
        api_version: str,
    ):
        return transport.call_row(
            profile=profile,
            addendum=self._addendum,
            body=body,
            path=path,
            api_version=api_version,
            tokens=self._tokens,
        )

    def __call__(self, profile: contract.RoleProfile, body: Mapping[str, Any]):
        route = self.resolved.get(profile.role)
        if route is None:
            raise contract.AddendumError(
                f"{profile.role} was called before its route was qualified"
            )
        path, api_version = route
        return self.call_route(profile, body, path, api_version)


def assert_probe_is_not_a_fixture(book: contract.Addendum) -> None:
    """The probe must not consume one of the 60 registered pairs."""

    registered_ids = {str(f["fixture_id"]) for f in book.smoke_fixtures}
    registered_records = {str(f["row"]["record_id"]) for f in book.smoke_fixtures}
    if QUALIFICATION_PROBE["record_id"] in registered_ids | registered_records:
        raise addendum_v2.AddendumError(
            "the qualification probe collides with a registered fixture"
        )
    bank = addendum_v2.canonical_bank(book.smoke_fixtures)
    if QUALIFICATION_PROBE["output_text"] in bank:
        raise addendum_v2.AddendumError(
            "the qualification probe reuses a registered fixture output"
        )


def _qualify(book: contract.Addendum, caller: LiveCaller) -> dict[str, Any]:
    """Run exactly three qualification calls and preserve every outcome."""

    assert_probe_is_not_a_fixture(book)
    calls: list[dict[str, Any]] = []
    roles: dict[str, Any] = {}
    for role in contract.ROLES:
        profile = book.roles[role]
        if len(profile.path_candidates) != 1 or len(profile.api_version_candidates) != 1:
            raise addendum_v2.AddendumError(
                "v2 qualification requires exactly one frozen route candidate "
                f"for {role}, got {profile.path_candidates} and "
                f"{profile.api_version_candidates}"
            )
        path = profile.path_candidates[0]
        api_version = profile.api_version_candidates[0]
        body = contract.build_request(profile, book, QUALIFICATION_PROBE)
        fixture = {
            "fixture_id": QUALIFICATION_PROBE["record_id"],
            "expected_label": "correct",
        }
        record = _blank_call(fixture, profile)
        record["request_body_sha256"] = contract.sha256_text(
            contract.request_bytes(body).decode("utf-8")
        )
        started = time.monotonic()
        try:
            response = caller.call_route(profile, body, path, api_version)
        except contract.TransportError as error:
            record["latency_seconds"] = round(time.monotonic() - started, 3)
            record["retry_count"] = (
                int(book.retry["max_attempts"]) - 1
                if "exhausted" in str(error)
                else 0
            )
            record["terminal_transport_status"] = f"transport_exhausted: {error}"
        except contract.MalformedResponseError as error:
            record["latency_seconds"] = round(time.monotonic() - started, 3)
            record["retry_count"] = 0
            record["terminal_transport_status"] = f"malformed_envelope: {error}"
        else:
            _record_response(record, response)
            try:
                label = contract.parse_label(response.payload, profile)
            except contract.MalformedResponseError as error:
                record["terminal_transport_status"] = f"malformed_label: {error}"
            else:
                record["observed_label"] = label
                record["match"] = label == "correct"
                visible = record["visible_completion_tokens"]
                if not isinstance(visible, int) or visible > profile.max_visible_output_tokens:
                    record["terminal_transport_status"] = (
                        "malformed_visible_token_count: "
                        f"{visible!r} exceeds or cannot prove cap "
                        f"{profile.max_visible_output_tokens}"
                    )
                    record["match"] = False
                else:
                    caller.resolved[role] = (path, api_version)

        roles[role] = {
            "provider": profile.provider,
            "deployment": profile.deployment,
            "model": profile.model,
            "model_version": profile.model_version,
            "sku": profile.sku,
            "region": profile.region,
            "proven_path": path,
            "proven_api_version": api_version,
            "reviewer_id": profile.reviewer_id,
            "request_profile_sha256": profile.request_profile_sha256(),
            "max_visible_output_tokens": profile.max_visible_output_tokens,
            "seconds": round(time.monotonic() - started, 2),
        }
        calls.append(record)

    transport_failures = sum(
        str(call["terminal_transport_status"]).startswith("transport_exhausted")
        for call in calls
    )
    malformed = sum(
        str(call["terminal_transport_status"]).startswith("malformed")
        for call in calls
    )
    matches = sum(bool(call["match"]) for call in calls)
    passed = len(calls) == len(contract.ROLES) and matches == len(contract.ROLES)
    if passed:
        verdict = "QUALIFIED"
    elif transport_failures:
        verdict = TERMINAL_PROVIDER
    else:
        verdict = TERMINAL_UNQUALIFIED
    return {
        "calls": calls,
        "roles": roles,
        "counts": {
            "registered_calls": len(contract.ROLES),
            "completed_calls": len(calls),
            "valid_expected_label_matches": matches,
            "transport_failures_after_registered_retry": transport_failures,
            "malformed_responses": malformed,
            "semantic_retries": 0,
        },
        "passed": passed,
        "verdict": verdict,
        "counts_towards_scientific_totals": False,
    }


def _envelope_field(payload: Mapping[str, Any], key: str) -> Any:
    value = payload.get(key)
    return value if isinstance(value, (str, int, float)) else None


def _finish_reason(payload: Mapping[str, Any]) -> str | None:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], Mapping):
        reason = choices[0].get("finish_reason")
        return reason if isinstance(reason, str) else None
    return None


def _total_tokens(payload: Mapping[str, Any]) -> int | None:
    usage = payload.get("usage")
    if isinstance(usage, Mapping) and isinstance(usage.get("total_tokens"), int):
        return int(usage["total_tokens"])
    return None


def _record_response(record: dict[str, Any], response: Any) -> None:
    """Copy the observable provider envelope into a per-call receipt."""

    if record["request_body_sha256"] != response.request_sha256:
        raise addendum_v2.AddendumError(
            "the transport response describes request bytes different from the "
            "frozen body recorded before the call"
        )
    payload = response.payload
    record.update(
        {
            "response_body_sha256": response.response_sha256,
            "request_id": _envelope_field(payload, "id"),
            "provider_model_fingerprint": _envelope_field(payload, "model")
            or _envelope_field(payload, "system_fingerprint"),
            "finish_reason": _finish_reason(payload),
            "visible_completion_tokens": contract.visible_token_count(payload),
            "total_tokens": _total_tokens(payload),
            "latency_seconds": round(response.latency_seconds, 3),
            "retry_count": response.retries,
            "terminal_transport_status": "ok",
        }
    )


def _blank_call(fixture: Mapping[str, Any], profile: contract.RoleProfile) -> dict[str, Any]:
    """Every registered field, present even when the exchange failed.

    A receipt with holes in it invites the reader to guess.  A failed call
    records its status and leaves the observable fields explicitly null.
    """

    return {
        "fixture_id": str(fixture["fixture_id"]),
        "expected_label": str(fixture["expected_label"]),
        "role": profile.role,
        "provider": profile.provider,
        "deployment": profile.deployment,
        "model": profile.model,
        "model_version": profile.model_version,
        "request_body_sha256": None,
        "response_body_sha256": None,
        "observed_label": None,
        "match": False,
        "request_id": None,
        "provider_model_fingerprint": None,
        "finish_reason": None,
        "visible_completion_tokens": None,
        "total_tokens": None,
        "latency_seconds": None,
        "retry_count": None,
        "terminal_transport_status": "not_attempted",
    }


def _smoke(book: contract.Addendum, caller: LiveCaller) -> dict[str, Any]:
    """Run all 60 registered pairs, recording every outcome before judging."""

    calls: list[dict[str, Any]] = []
    for fixture in book.smoke_fixtures:
        for role in contract.ROLES:
            profile = book.roles[role]
            record = _blank_call(fixture, profile)
            expected = str(fixture["expected_label"])
            body = contract.build_request(profile, book, fixture["row"])
            record["request_body_sha256"] = contract.sha256_text(
                contract.request_bytes(body).decode("utf-8")
            )
            started = time.monotonic()
            try:
                response = caller(profile, body)
            except contract.TransportError as error:
                record["latency_seconds"] = round(time.monotonic() - started, 3)
                record["retry_count"] = (
                    int(book.retry["max_attempts"]) - 1
                    if "exhausted" in str(error)
                    else 0
                )
                record["terminal_transport_status"] = f"transport_exhausted: {error}"
                calls.append(record)
                continue
            except contract.MalformedResponseError as error:
                record["latency_seconds"] = round(time.monotonic() - started, 3)
                record["retry_count"] = 0
                record["terminal_transport_status"] = f"malformed_envelope: {error}"
                calls.append(record)
                continue

            payload = response.payload
            _record_response(record, response)
            try:
                label = contract.parse_label(payload, profile)
            except contract.MalformedResponseError as error:
                record["terminal_transport_status"] = f"malformed_label: {error}"
                calls.append(record)
                continue
            record["observed_label"] = label
            record["match"] = label == expected
            calls.append(record)

    return summarise_smoke(book, calls)


def summarise_smoke(book: contract.Addendum, calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply section 10.2's seven criteria to a completed batch.

    Separated from the calling loop so the verdict is computed from the same
    receipt that gets persisted, and so it can be tested without a provider.
    """

    required = addendum_v2.REQUIRED_CALLS
    caps = {role: book.roles[role].max_visible_output_tokens for role in contract.ROLES}

    valid = [call for call in calls if call["terminal_transport_status"] == "ok"]
    malformed = [
        call
        for call in calls
        if str(call["terminal_transport_status"]).startswith("malformed")
    ]
    transport_failures = [
        call
        for call in calls
        if str(call["terminal_transport_status"]).startswith("transport_exhausted")
    ]
    labelled = [call for call in valid if call["observed_label"] is not None]
    within_cap = [
        call
        for call in valid
        if isinstance(call["visible_completion_tokens"], int)
        and call["visible_completion_tokens"] <= caps[call["role"]]
    ]
    matches = [call for call in calls if call["match"]]
    mismatches = [
        f"{call['fixture_id']}/{call['role']}: "
        f"{call['observed_label']} != {call['expected_label']}"
        for call in calls
        if not call["match"]
    ]

    counts = {
        "registered_calls": required,
        "completed_calls": len(calls),
        "valid_responses": len(valid),
        "schema_valid_one_key_labels": len(labelled),
        "visible_completions_within_cap": len(within_cap),
        "exact_expected_label_matches": len(matches),
        "transport_failures_after_registered_retry": len(transport_failures),
        "malformed_responses": len(malformed),
        "semantic_retries": 0,
    }
    passed = (
        counts["completed_calls"] == required
        and counts["valid_responses"] == required
        and counts["schema_valid_one_key_labels"] == required
        and counts["visible_completions_within_cap"] == required
        and counts["exact_expected_label_matches"] == required
        and counts["transport_failures_after_registered_retry"] == 0
        and counts["malformed_responses"] == 0
        and counts["semantic_retries"] == 0
    )
    return {
        "calls": calls,
        "counts": counts,
        "visible_token_caps": caps,
        "mismatches": mismatches,
        "passed": passed,
        "verdict": "QUALIFIED" if passed else TERMINAL_UNQUALIFIED,
        "no_majority_rule": True,
        "counts_towards_scientific_totals": False,
    }


def _instrument_header(book: contract.Addendum) -> dict[str, Any]:
    document = book.document
    return {
        "round": "v2",
        "authority_prompt": document["authority_prompt"],
        "authority_prompt_sha256": document["authority_prompt_sha256"],
        "addendum_sha256": book.sha256,
        "rubric_sha256": book.rubric_sha256,
        "fixture_bank_sha256": document["conformance_bank"]["fixture_bank_sha256"],
        "base_protocol_sha256": document["base_protocol_sha256"],
        "task_ids_sha256": document["task_ids_sha256"],
        "generation_image_digest": document["generation_image_digest"],
        "v1_gate_receipt_sha256": document["historical_parents"]["v1_gate_receipt_sha256"],
        "expected_labels_committed_before_calls": True,
        "scientific": False,
    }


def _persist(
    publisher: GatePublisher | None,
    receipt: Mapping[str, Any],
    out_dir: Path,
    filename: str,
    run_id: str,
) -> tuple[dict[str, Any] | None, str]:
    """Write the receipt locally, then publish it create-only, manifest last."""

    payload = contract.canonical_json(receipt).encode("utf-8")
    local = out_dir / filename
    receipt_sha = _write(local, contract.canonical_json(receipt))
    print(f"RECEIPT_SHA256={receipt_sha}")
    print(f"RECEIPT_PATH={local}")
    if publisher is None:
        raise GateEvidenceError(
            "no gate evidence prefix was configured; refusing to run a gate "
            "whose receipt cannot outlive the replica"
        )
    published = publisher.publish({"00_gate_receipt.json": payload}, run_id)
    print(f"GATE_EVIDENCE_PREFIX={published['prefix']}")
    print(f"GATE_EVIDENCE_MANIFEST_SHA256={published['manifest_sha256']}")
    print("GATE_EVIDENCE_PERSISTED=1")
    return published, receipt_sha


def _load_persisted_receipt(
    client: Any,
    prefix: str,
    book: contract.Addendum,
    expected_artifact: str,
) -> dict[str, Any]:
    """Load one manifest-complete receipt and verify its instrument binding."""

    prefix = prefix.rstrip("/")
    manifest = json.loads(client.get(f"{prefix}/artifact_manifest.json"))
    raw = client.get(f"{prefix}/00_gate_receipt.json")
    recorded = {
        str(entry["name"]): str(entry["sha256"])
        for entry in manifest.get("files", [])
    }
    digest = hashlib.sha256(raw).hexdigest()
    if recorded.get("00_gate_receipt.json") != digest:
        raise addendum_v2.AddendumError(
            "the persisted gate receipt does not match its manifest hash"
        )
    receipt = json.loads(raw)
    if receipt.get("addendum_sha256") != book.sha256:
        raise addendum_v2.AddendumError(
            "the persisted gate receipt was produced by a different addendum"
        )
    if receipt.get("artifact") != expected_artifact:
        raise addendum_v2.AddendumError(
            f"gate receipt artifact is {receipt.get('artifact')!r}, expected "
            f"{expected_artifact!r}"
        )
    receipt["_receipt_sha256"] = digest
    return receipt


def _validate_receipt_routes(
    receipt: Mapping[str, Any], book: contract.Addendum
) -> None:
    roles = receipt.get("roles")
    if not isinstance(roles, Mapping) or set(roles) != set(contract.ROLES):
        raise addendum_v2.AddendumError(
            "a gate receipt must bind exactly primary/secondary/third"
        )
    for role in contract.ROLES:
        recorded = roles[role]
        profile = book.roles[role]
        if not isinstance(recorded, Mapping):
            raise addendum_v2.AddendumError(f"gate role {role} is not an object")
        if recorded.get("reviewer_id") != profile.reviewer_id:
            raise addendum_v2.AddendumError(f"gate role {role} moved reviewer identity")
        if recorded.get("request_profile_sha256") != profile.request_profile_sha256():
            raise addendum_v2.AddendumError(f"gate role {role} moved request profile")
        if recorded.get("proven_path") not in profile.path_candidates:
            raise addendum_v2.AddendumError(f"gate role {role} used an unregistered path")
        if recorded.get("proven_api_version") not in profile.api_version_candidates:
            raise addendum_v2.AddendumError(
                f"gate role {role} used an unregistered api-version"
            )


def _load_qualification_receipt(
    client: Any, prefix: str, book: contract.Addendum
) -> dict[str, Any]:
    receipt = _load_persisted_receipt(
        client,
        prefix,
        book,
        "phase1_0d_rv2_provider_qualification_receipt",
    )
    counts = receipt.get("counts", {})
    if (
        not receipt.get("passed")
        or int(counts.get("completed_calls", -1)) != len(contract.ROLES)
        or int(counts.get("valid_expected_label_matches", -1)) != len(contract.ROLES)
    ):
        raise addendum_v2.AddendumError(
            "smoke is licensed only by a persisted 3/3 qualification pass"
        )
    _validate_receipt_routes(receipt, book)
    return receipt


def _load_gate_receipt(client: Any, prefix: str, book: contract.Addendum) -> dict[str, Any]:
    """Refuse to review unless a persisted 60/60 v2 gate receipt says so."""

    receipt = _load_persisted_receipt(
        client, prefix, book, "phase1_0d_rv2_provider_smoke_receipt"
    )
    counts = receipt.get("counts", {})
    if not receipt.get("passed") or int(
        counts.get("exact_expected_label_matches", -1)
    ) != addendum_v2.REQUIRED_CALLS:
        raise addendum_v2.AddendumError(
            "review is licensed only by a persisted "
            f"{addendum_v2.REQUIRED_CALLS}/{addendum_v2.REQUIRED_CALLS} smoke pass"
        )
    _validate_receipt_routes(receipt, book)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("qualify", "smoke", "review"))
    parser.add_argument("--project-root", default=str(REPO_ROOT))
    parser.add_argument("--pack-dir", default="")
    parser.add_argument("--pack-blob-prefix", default="")
    parser.add_argument("--blob-account", default="")
    parser.add_argument("--blob-container", default="")
    parser.add_argument("--gate-blob-prefix", default="")
    parser.add_argument("--qualification-receipt-prefix", default="")
    parser.add_argument("--gate-receipt-prefix", default="")
    parser.add_argument("--out-blob-prefix", default="")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--client-id", default="")
    parser.add_argument("--code-commit", default="")
    parser.add_argument("--image-digest", default="")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    book = addendum_v2.load_addendum_v2(root)
    contract.assert_matches_frozen_form(REVIEW_FORM_PRESENTED_FIELDS)
    selection = json.loads(
        (root / "docs/phase1_0d_protocol_snapshot.json").read_text(encoding="utf-8")
    )["snapshot"]["selection"]
    if selection["task_ids_sha256"] != book.document["task_ids_sha256"]:
        raise SystemExit(
            "the selected task-id hash moved; the v2 addendum is bound to "
            f"{book.document['task_ids_sha256']}"
        )
    addendum_v2.assert_no_target_leakage(book.smoke_fixtures, selection["task_ids"])
    out_dir = Path(args.out_dir).resolve() if args.out_dir else root / "_review_v2_out"
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    header = _instrument_header(book)

    print(f"ROUND=v2 RUN_ID={run_id}")
    print(f"ADDENDUM_SHA256={book.sha256}")
    print(f"RUBRIC_SHA256={book.rubric_sha256}")
    print(f"FIXTURE_BANK_SHA256={header['fixture_bank_sha256']}")
    print(f"BASE_PROTOCOL_SHA256={header['base_protocol_sha256']}")
    print(f"REGISTERED_CALLS={addendum_v2.REQUIRED_CALLS}")

    if args.mode in ("qualify", "smoke") and (args.pack_dir or args.pack_blob_prefix):
        raise SystemExit(
            "the v2 qualification and smoke stages take no generation pack; "
            "target isolation is not optional"
        )

    tokens = transport.TokenProvider(args.client_id or None)

    publisher: GatePublisher | None = None
    if args.blob_account and args.blob_container and args.gate_blob_prefix:
        publisher = GatePublisher(
            args.blob_account, args.blob_container, args.gate_blob_prefix, tokens
        )

    if args.mode == "qualify":
        caller = LiveCaller(book, tokens)
        qualification = _qualify(book, caller)
        for call in qualification["calls"]:
            print(
                f"QUALIFICATION role={call['role']} "
                f"observed={call['observed_label']} match={call['match']} "
                f"status={call['terminal_transport_status']}"
            )
        receipt = {
            "artifact": "phase1_0d_rv2_provider_qualification_receipt",
            "run_id": run_id,
            **header,
            "review_code_commit": args.code_commit or "not_recorded",
            "review_image_digest": args.image_digest or "not_recorded",
            "probe": QUALIFICATION_PROBE,
            "probe_is_outside_the_registered_bank": True,
            "claim_boundary": (
                "proves only that the exact pinned deployments answer over a "
                "registered route with managed-identity authentication; "
                "establishes nothing about reviewer accuracy"
            ),
            **qualification,
        }
        try:
            _persist(publisher, receipt, out_dir, f"qualification_{run_id}.json", run_id)
        except Exception as error:  # noqa: BLE001 - any persistence failure is terminal
            print(f"GATE_EVIDENCE_PERSISTENCE_FAILED: {error}")
            print(TERMINAL_PERSISTENCE)
            return 3
        if not qualification["passed"]:
            print(qualification["verdict"])
            return 2 if qualification["verdict"] == TERMINAL_PROVIDER else 1
        print("QUALIFY_COMPLETE=1")
        print("QUALIFICATION_3_OF_3=1")
        return 0

    if args.mode == "smoke":
        if not (args.blob_account and args.blob_container):
            raise SystemExit("smoke mode needs --blob-account and --blob-container")
        if not args.qualification_receipt_prefix:
            raise SystemExit("smoke mode needs --qualification-receipt-prefix")
        qualification_reader = GateReader(
            args.blob_account,
            args.blob_container,
            args.qualification_receipt_prefix,
            tokens,
        )
        qualification = _load_qualification_receipt(
            qualification_reader,
            qualification_reader.prefix,
            book,
        )
        if args.code_commit and qualification.get("review_code_commit") != args.code_commit:
            raise addendum_v2.AddendumError(
                "the qualification receipt came from a different review commit"
            )
        if args.image_digest and qualification.get("review_image_digest") != args.image_digest:
            raise addendum_v2.AddendumError(
                "the qualification receipt came from a different review image"
            )
        caller = LiveCaller(book, tokens)
        for role in contract.ROLES:
            route = qualification["roles"][role]
            caller.resolved[role] = (
                str(route["proven_path"]),
                str(route["proven_api_version"]),
            )
            print(
                f"QUALIFICATION_REUSED role={role} "
                f"path={route['proven_path']} "
                f"api_version={route['proven_api_version'] or '-'}"
            )
        result = _smoke(book, caller)
        for call in result["calls"]:
            print(
                f"SMOKE fixture={call['fixture_id']} role={call['role']} "
                f"expected={call['expected_label']} "
                f"observed={call['observed_label']} match={call['match']} "
                f"status={call['terminal_transport_status']}"
            )
        receipt = {
            "artifact": "phase1_0d_rv2_provider_smoke_receipt",
            "run_id": run_id,
            **header,
            "roles": qualification["roles"],
            "qualification_parent": {
                "prefix": qualification_reader.prefix,
                "run_id": qualification["run_id"],
                "receipt_sha256": qualification["_receipt_sha256"],
            },
            "review_code_commit": args.code_commit or "not_recorded",
            "review_image_digest": args.image_digest or "not_recorded",
            "smoke_rules": book.document["smoke_rules"],
            "claim_boundary": book.document["claim_boundary"],
            **result,
        }
        # Persist before judging: a mismatch is evidence, not a reason to exit.
        try:
            _persist(publisher, receipt, out_dir, f"smoke_{run_id}.json", run_id)
        except Exception as error:  # noqa: BLE001 - any persistence failure is terminal
            print(f"GATE_EVIDENCE_PERSISTENCE_FAILED: {error}")
            print(TERMINAL_PERSISTENCE)
            return 3

        counts = result["counts"]
        for key in sorted(counts):
            print(f"SMOKE_COUNT {key}={counts[key]}")
        if not result["passed"]:
            for line in result["mismatches"]:
                print(f"SMOKE_MISMATCH {line}")
            print(TERMINAL_UNQUALIFIED)
            return 1
        print("SMOKE_COMPLETE=1")
        print("SMOKE_60_OF_60=1")
        return 0

    # ---- review: target storage is reachable only from here -----------------
    import run_phase1_0d_semantic_review as v1runner  # noqa: PLC0415, E402

    if not (args.blob_account and args.blob_container):
        raise SystemExit("review mode needs --blob-account and --blob-container")
    blob = transport.BlobClient(args.blob_account, args.blob_container, tokens)

    if not args.gate_receipt_prefix:
        raise SystemExit("review mode needs --gate-receipt-prefix")
    gate = _load_gate_receipt(blob, args.gate_receipt_prefix, book)
    if args.code_commit and gate.get("review_code_commit") != args.code_commit:
        raise addendum_v2.AddendumError(
            "the smoke receipt came from a different review commit"
        )
    if args.image_digest and gate.get("review_image_digest") != args.image_digest:
        raise addendum_v2.AddendumError(
            "the smoke receipt came from a different review image"
        )
    print(f"GATE_RECEIPT_RUN_ID={gate['run_id']}")
    print("GATE_60_OF_60_VERIFIED=1")
    caller = LiveCaller(book, tokens)
    for role in contract.ROLES:
        route = gate["roles"][role]
        caller.resolved[role] = (
            str(route["proven_path"]),
            str(route["proven_api_version"]),
        )

    pack_dir = Path(args.pack_dir).resolve() if args.pack_dir else out_dir / "generation"
    download: dict[str, Any] | None = None
    if args.pack_blob_prefix:
        download = v1runner.download_pack(
            blob, args.pack_blob_prefix.rstrip("/"), pack_dir
        )
        print(f"PACK_FILES={download['file_count']}")
    elif not args.pack_dir:
        raise SystemExit("review mode requires --pack-dir or --pack-blob-prefix")

    summary = v1runner._review(book, caller, pack_dir, out_dir, run_id)
    summary["round"] = "v2"
    summary["provider_qualification"] = gate["qualification_parent"]
    summary["gate_receipt"] = {
        "prefix": args.gate_receipt_prefix.rstrip("/"),
        "run_id": gate["run_id"],
        "counts": gate["counts"],
    }
    summary["pack_download"] = download

    final_dir = out_dir / "final"
    finalization = v1runner.finalize_pack(
        project_root=root,
        pack_dir=pack_dir,
        judgments_path=Path(summary["judgments_path"]),
        out_root=final_dir,
        run_id=run_id,
        code_commit=args.code_commit or "not_recorded",
        image_digest=args.image_digest or "not_recorded",
    )
    final_pack = Path(finalization["output_dir"])
    summary["finalization"] = finalization
    print(f"FINAL_RESULT={finalization['result']}")

    from jspace_observation.semantic_review import stages  # noqa: PLC0415

    finalized_records = stages.load_records(final_pack / "02_records.jsonl")
    decision = json.loads((final_pack / "05_decision.json").read_text(encoding="utf-8"))
    combined = json.loads(Path(summary["judgments_path"]).read_text(encoding="utf-8"))
    check = stages.independent_check(
        records=finalized_records,
        decision=decision,
        combined=combined,
        required_secondary=summary["secondary_selection"]["required_ids"],
        required_third=summary["third_selection"]["required_ids"],
    )
    summary["independent_check"] = check
    print(f"INDEPENDENT_CHECK_DECISION_SHA256={check['decision_sha256']}")

    summary["execution_receipt"] = stages.outer_receipt(
        artifact="phase1_0d_rv2_semantic_review_execution_receipt",
        run_id=run_id,
        addendum_sha256=book.sha256,
        rubric_sha256=book.rubric_sha256,
        base_protocol_sha256=book.document["base_protocol_sha256"],
        generation_pack_manifest_sha256=summary["verification"]["manifest_sha256"],
        generation_records_sha256=summary["verification"]["records_sha256"],
        all_judgments_sha256=summary["all_judgments_sha256"],
        review_image_digest=args.image_digest or "not_recorded",
        review_code_commit=args.code_commit or "not_recorded",
        reviewer_authority=(
            "registered under DR-01; LLM operational consensus, not human "
            "ground truth; v2 instrument, independence cost disclosed as L-52"
        ),
    )
    path = out_dir / "review_stage_summary.json"
    print(f"SUMMARY_SHA256={_write(path, contract.canonical_json(summary))}")
    _write(
        out_dir / "00_execution_receipt.json",
        contract.canonical_json(summary["execution_receipt"]),
    )

    if args.out_blob_prefix:
        files: dict[str, bytes] = {
            f"generation/{name}": payload
            for name, payload in v1runner._read_tree(pack_dir).items()
        }
        files.update(
            {
                f"final/{name}": payload
                for name, payload in v1runner._read_tree(final_pack).items()
            }
        )
        for name, payload in v1runner._read_tree(out_dir).items():
            if name.startswith("generation/") or name.startswith("final/"):
                continue
            files[name] = payload
        published = v1runner.publish_bundle(
            blob, args.out_blob_prefix.rstrip("/"), files, run_id
        )
        print(f"BUNDLE_FILES={published['uploaded_count']}")
        print(f"BUNDLE_MANIFEST_SHA256={published['manifest_sha256']}")

    print(f"ALL_JUDGMENTS_SHA256={summary['all_judgments_sha256']}")
    print(f"SECONDARY_REQUIRED={summary['secondary_selection']['required_count']}")
    print(f"THIRD_REQUIRED={summary['third_selection']['required_count']}")
    print("REVIEW_STAGES_COMPLETE=1")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
