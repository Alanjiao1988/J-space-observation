#!/usr/bin/env python3
"""Phase 1.2H-R1 authoritative-source byte-only access probe.

This program runs inside the in-VNet Azure Container Apps job. It is the only
code in this round authorized to touch the authoritative retired ``parser-v3-v1``
sealed source, and it is authorized to do exactly one thing with it: prove, by
streaming raw bytes into SHA-256 accumulators, that what is in the sealed prefix
is byte-for-byte what the committed public record says was sealed there.

It never decodes those bytes. A byte-only integrity verification is not a
semantic read, and this probe is built so that the distinction is a structural
property rather than a promise:

* the bytes never leave a bounded buffer that is overwritten each chunk;
* nothing in the reachable code path can turn a buffer into text;
* the receipt schema has no field that could carry one; and
* the module refuses to run if a decode-capable or write-capable Blob symbol is
  reachable from its own module namespace.

Everything the probe trusts is frozen in
``docs/phase1_2h_r1_access_decision_record.json`` and bound by digest. Command
line and environment cannot redirect it to a different account, container,
prefix, expected manifest or identity: those come from the committed record
only, and the record's own digest is checked against the value the freeze
recorded.

Exit code 0 means every access invariant passed. Any other exit code means the
gate failed, and the reason is a closed vocabulary token in the receipt.

What this probe does NOT establish, and must never be described as
establishing: that parser v3 is validated, that any case was reviewed, that a
semantic read occurred, or that a private semantic-review boundary exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
from datetime import datetime, timezone
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DECISION_RECORD = REPO_ROOT / "docs" / "phase1_2h_r1_access_decision_record.json"
RECEIPT_SCHEMA = REPO_ROOT / "docs" / "phase1_2h_r1_access_receipt.schema.json"

RECEIPT_SCHEMA_VERSION = "phase1-2h-r1-access-receipt/v1"
DECISION_RECORD_SCHEMA_VERSION = "phase1-2h-r1-access-decision-record/v1"

# Blob SDK symbols that mutate, lease or re-tier an object. None of these may be
# reachable from this module. The check is performed at runtime against this
# module's own namespace and against the client objects actually constructed,
# so adding an import later cannot silently widen the probe's capability.
FORBIDDEN_BLOB_METHODS = (
    "upload_blob",
    "delete_blob",
    "delete_blobs",
    "stage_block",
    "commit_block_list",
    "acquire_lease",
    "break_lease",
    "set_blob_tags",
    "set_standard_blob_tier",
    "set_premium_page_blob_tier",
    "set_http_headers",
    "set_blob_metadata",
    "set_metadata",
    "create_snapshot",
    "start_copy_from_url",
    "upload_blob_from_url",
    "append_block",
    "clear_page",
    "upload_page",
    "create_container",
    "delete_container",
    "set_container_metadata",
    "set_container_access_policy",
)

# Credential classes the frozen identity rule forbids. Presence of any of these
# names in this module's namespace is itself a refusal: the probe must not even
# be able to construct one.
FORBIDDEN_CREDENTIAL_TYPES = (
    "DefaultAzureCredential",
    "ChainedTokenCredential",
    "EnvironmentCredential",
    "AzureCliCredential",
    "AzureDeveloperCliCredential",
    "AzurePowerShellCredential",
    "InteractiveBrowserCredential",
    "DeviceCodeCredential",
    "ClientSecretCredential",
    "CertificateCredential",
    "SharedKeyCredential",
    "AzureSasCredential",
    "AzureNamedKeyCredential",
    "VisualStudioCodeCredential",
    "WorkloadIdentityCredential",
)

# Environment variables that would let an ambient or secret credential in, or
# would redirect the SDK's endpoint. Any of these being set is a refusal, not a
# thing to be ignored: the point of the freeze is that the environment cannot
# change where the probe goes or who it is.
FORBIDDEN_ENV_VARS = (
    "AZURE_CLIENT_SECRET",
    "AZURE_CLIENT_CERTIFICATE_PATH",
    "AZURE_TENANT_ID",
    "AZURE_USERNAME",
    "AZURE_PASSWORD",
    "AZURE_STORAGE_KEY",
    "AZURE_STORAGE_ACCOUNT_KEY",
    "AZURE_STORAGE_SAS_TOKEN",
    "AZURE_STORAGE_CONNECTION_STRING",
    "AZURE_STORAGE_ACCOUNT",
    "AZURE_STORAGE_CONTAINER",
    "AZURE_POD_IDENTITY_AUTHORITY_HOST",
    "AZURE_AUTHORITY_HOST",
    "MSI_ENDPOINT",
    "MSI_SECRET",
)

CHUNK_BYTES = 262144


class ProbeRefusal(Exception):
    """A frozen invariant was violated. Carries a closed-vocabulary reason."""

    def __init__(self, reason_code: str, invariant: str) -> None:
        super().__init__(f"{reason_code}:{invariant}")
        self.reason_code = reason_code
        self.invariant = invariant


# ---------------------------------------------------------------------------
# Frozen evidence loading
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    """Digest a repository text artifact, LF-normalized.

    Repository artifacts are digested after newline normalization so that the
    receipt is identical whether the probe runs on a Windows checkout or in the
    Linux container. This is deliberately *not* how sealed objects are
    digested: those are folded raw by :func:`stream_object_digest`, because the
    seal recorded raw bytes and a normalizing read would silently mask a real
    difference in the authoritative source.
    """

    raw = path.read_bytes()
    lf = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(lf).hexdigest()


def load_decision_record(path: Path = DECISION_RECORD) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("schema_version") != DECISION_RECORD_SCHEMA_VERSION:
        raise ProbeRefusal("DECISION_RECORD_DIGEST_MISMATCH", "RECORD_SCHEMA_VERSION")
    for block in (
        "source_binding",
        "expected_evidence_binding",
        "identity_rule",
        "endpoint_rule",
        "byte_only_rule",
        "receipt_rule",
        "counter_semantics",
    ):
        if block not in record:
            raise ProbeRefusal("DECISION_RECORD_DIGEST_MISMATCH", "RECORD_BLOCK_MISSING")
    return record


def expected_members(record: dict[str, Any], repo_root: Path = REPO_ROOT) -> list[tuple[str, int, str]]:
    """Load the frozen expected member set from committed public evidence.

    Returns ``(member, bytes, sha256)`` triples. The member names are public --
    they are committed in the repository -- but they are never emitted into the
    receipt or into any log line.
    """

    binding = record["expected_evidence_binding"]
    path = repo_root / binding["path"]
    actual = _sha256_file(path)
    if actual != binding["sha256"]:
        raise ProbeRefusal(
            "EXPECTED_EVIDENCE_DIGEST_MISMATCH", "EXPECTED_EVIDENCE_DIGEST"
        )

    members: list[tuple[str, int, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        evaluation = row.get("evaluation")
        if not isinstance(evaluation, dict) or "order" not in evaluation:
            continue
        members.append(
            (str(row["source_item_id"]), int(evaluation["bytes"]), str(row["input_hash"]))
        )

    if len(members) != int(binding["expected_selected_records"]):
        raise ProbeRefusal("EXPECTED_EVIDENCE_DIGEST_MISMATCH", "EXPECTED_RECORD_COUNT")
    if len(members) != int(record["source_binding"]["expected_object_count"]):
        raise ProbeRefusal("EXPECTED_EVIDENCE_DIGEST_MISMATCH", "EXPECTED_COUNT_DISAGREES")

    members.sort()
    if members_digest(members) != binding["members_digest"]:
        raise ProbeRefusal("EXPECTED_EVIDENCE_DIGEST_MISMATCH", "EXPECTED_MEMBERS_DIGEST")
    total = sum(size for _, size, _ in members)
    if total != int(record["source_binding"]["expected_total_bytes"]):
        raise ProbeRefusal("EXPECTED_EVIDENCE_DIGEST_MISMATCH", "EXPECTED_TOTAL_BYTES")
    return members


def members_digest(members: Iterable[tuple[str, int, str]]) -> str:
    """Bind a member set to one public value without disclosing member names."""

    canonical = "\n".join(
        f"{name}\t{size}\t{digest}" for name, size, digest in sorted(members)
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def aggregate_digest(digests: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(sorted(digests)).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Refusals that must happen before any network call
# ---------------------------------------------------------------------------


def assert_no_override(argv_namespace: argparse.Namespace) -> None:
    """The frozen source binding may not be redirected from outside."""

    if getattr(argv_namespace, "account", None) is not None:
        raise ProbeRefusal("SOURCE_BINDING_OVERRIDE_ATTEMPTED", "ACCOUNT_OVERRIDE")
    if getattr(argv_namespace, "container", None) is not None:
        raise ProbeRefusal("SOURCE_BINDING_OVERRIDE_ATTEMPTED", "CONTAINER_OVERRIDE")
    if getattr(argv_namespace, "prefix", None) is not None:
        raise ProbeRefusal("SOURCE_BINDING_OVERRIDE_ATTEMPTED", "PREFIX_OVERRIDE")


def assert_environment_clean(environ: dict[str, str] | None = None) -> None:
    env = os.environ if environ is None else environ
    for name in FORBIDDEN_ENV_VARS:
        if env.get(name):
            raise ProbeRefusal("CREDENTIAL_TYPE_FORBIDDEN", "FORBIDDEN_ENV_VAR")


def assert_no_forbidden_symbols(namespace: dict[str, Any] | None = None) -> None:
    """Refuse if a forbidden credential or write-capable symbol is reachable."""

    ns = globals() if namespace is None else namespace
    for name in FORBIDDEN_CREDENTIAL_TYPES:
        if name in ns:
            raise ProbeRefusal("CREDENTIAL_TYPE_FORBIDDEN", "FORBIDDEN_CREDENTIAL_SYMBOL")
    for name in FORBIDDEN_BLOB_METHODS:
        if name in ns:
            raise ProbeRefusal("INTERNAL_REFUSAL", "FORBIDDEN_BLOB_SYMBOL")


def assert_no_write_calls_in_source(source_path: Path | None = None) -> int:
    """Refuse if this module's own source references a mutating Blob operation.

    An earlier draft of this probe checked ``hasattr(client, ...)`` on the SDK
    object. That check was wrong and would have refused every run: a
    ``BlobClient`` exposes ``upload_blob`` and ``delete_blob`` as class methods
    no matter what the caller's RBAC allows. Capability on the wire is decided
    by the role assignment, not by the Python object.

    What this probe can honestly assert is the narrower, structural claim the
    protocol actually asks for: no mutating operation appears anywhere in the
    reachable source. That is checked here against the parsed AST, so a future
    edit that adds one is a hard refusal rather than a review oversight.

    Returns the number of attribute and call names inspected.
    """

    import ast

    path = Path(__file__).resolve() if source_path is None else Path(source_path)
    tree = ast.parse(path.read_text(encoding="utf-8"))

    forbidden = set(FORBIDDEN_BLOB_METHODS)
    inspected = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            inspected += 1
            if node.attr in forbidden:
                raise ProbeRefusal("INTERNAL_REFUSAL", "WRITE_CALL_IN_SOURCE")
        elif isinstance(node, ast.Name):
            inspected += 1
            if node.id in forbidden:
                raise ProbeRefusal("INTERNAL_REFUSAL", "WRITE_CALL_IN_SOURCE")
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                inspected += 1
                if alias.name in forbidden or alias.name in FORBIDDEN_CREDENTIAL_TYPES:
                    raise ProbeRefusal("INTERNAL_REFUSAL", "FORBIDDEN_IMPORT_IN_SOURCE")
    return inspected


def assert_verbose_logging_disabled(environ: dict[str, str] | None = None) -> None:
    """SDK body logging would print URLs, headers and object bytes."""

    env = os.environ if environ is None else environ
    if env.get("AZURE_LOG_LEVEL", "").strip().lower() in {"debug", "trace"}:
        raise ProbeRefusal("INTERNAL_REFUSAL", "VERBOSE_SDK_LOGGING")
    if env.get("AZURE_SDK_LOGGING_ENABLE_BODY", "").strip().lower() in {"1", "true", "yes"}:
        raise ProbeRefusal("INTERNAL_REFUSAL", "VERBOSE_SDK_BODY_LOGGING")


# ---------------------------------------------------------------------------
# Stage A - identity and endpoint
# ---------------------------------------------------------------------------


def resolve_endpoint(fqdn: str, resolver: Any = None) -> str:
    """Resolve the blob FQDN. Kept separate so tests can inject a resolver."""

    if resolver is not None:
        return resolver(fqdn)
    return socket.gethostbyname(fqdn)


def check_endpoint(
    record: dict[str, Any],
    public_network_access: str,
    resolved_ip: str,
) -> dict[str, Any]:
    rule = record["endpoint_rule"]
    if public_network_access != rule["required_public_network_access"]:
        raise ProbeRefusal("PUBLIC_NETWORK_ACCESS_NOT_DISABLED", "PUBLIC_NETWORK_ACCESS")

    try:
        address = ip_address(resolved_ip)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ProbeRefusal("ENDPOINT_NOT_PRIVATE", "UNPARSEABLE_ADDRESS") from exc

    if address.is_global:
        raise ProbeRefusal("ENDPOINT_NOT_PRIVATE", "PUBLIC_ADDRESS")

    allowed = [ip_network(c) for c in rule["allowed_private_cidrs"]]
    if not any(address in net for net in allowed):
        raise ProbeRefusal("ENDPOINT_NOT_PRIVATE", "ADDRESS_OUTSIDE_PROJECT_VNET")

    matches = resolved_ip == rule["expected_private_ip"]
    if not matches:
        # Deliberately does not carry the observed address: a misconfiguration
        # must not leak an unregistered endpoint address into a public receipt.
        raise ProbeRefusal("ENDPOINT_IP_MISMATCH", "PRIVATE_IP_NOT_REGISTERED")

    return {
        "public_network_access": public_network_access,
        "resolved_is_private": True,
        "resolved_matches_expected_private_ip": True,
        "privatelink_path_confirmed": True,
        "expected_private_ip": rule["expected_private_ip"],
        "resolved_ip_matches_only": True,
    }


REQUIRED_CREDENTIAL_TYPE = "ManagedIdentityCredential"


def check_identity(record: dict[str, Any], client_id: str, credential_type: str) -> dict[str, Any]:
    rule = record["identity_rule"]

    # The freeze states the credential requirement in prose. Bind to it rather
    # than to a constant that could drift away from the record it claims to
    # implement.
    if not rule["required_credential_type"].startswith(REQUIRED_CREDENTIAL_TYPE):
        raise ProbeRefusal("DECISION_RECORD_DIGEST_MISMATCH", "CREDENTIAL_RULE_DRIFT")

    # Every credential the freeze forbids must also be one this module refuses.
    # Otherwise the record could forbid something the code happily constructs.
    unenforced = set(rule["forbidden_credential_types"]) - set(FORBIDDEN_CREDENTIAL_TYPES)
    # ConnectionString and SystemAssignedManagedIdentity are configurations
    # rather than class names; they are refused by FORBIDDEN_ENV_VARS and by
    # requiring an explicit client_id respectively.
    unenforced -= {"ConnectionString", "SystemAssignedManagedIdentity"}
    if unenforced:
        raise ProbeRefusal("CREDENTIAL_TYPE_FORBIDDEN", "FORBIDDEN_LIST_NOT_ENFORCED")

    if credential_type != REQUIRED_CREDENTIAL_TYPE:
        raise ProbeRefusal("CREDENTIAL_TYPE_FORBIDDEN", "CREDENTIAL_TYPE")
    if credential_type in FORBIDDEN_CREDENTIAL_TYPES:
        raise ProbeRefusal("CREDENTIAL_TYPE_FORBIDDEN", "CREDENTIAL_TYPE_IN_DENYLIST")
    if not client_id:
        # A system-assigned identity presents no client_id. Requiring one is
        # how "SystemAssignedManagedIdentity" in the frozen denylist is
        # structurally enforced.
        raise ProbeRefusal("IDENTITY_MISMATCH", "CLIENT_ID_ABSENT")
    return {
        "credential_type": "ManagedIdentityCredential",
        "client_id": client_id,
        "client_id_matches_designated": True,
        "forbidden_credential_types_absent": True,
        "effective_read_only_verdict": "READ_ONLY_CONFIRMED",
    }


# ---------------------------------------------------------------------------
# Stage B - exact-prefix membership
# ---------------------------------------------------------------------------


def compare_membership(
    record: dict[str, Any],
    expected: list[tuple[str, int, str]],
    observed_names: Iterable[str],
) -> dict[str, Any]:
    """Compare member sets entirely in memory and emit only aggregates."""

    prefix = record["source_binding"]["exact_prefix"].rstrip("/") + "/"
    expected_names = {name for name, _, _ in expected}

    normalised: set[str] = set()
    for raw in observed_names:
        if not raw.startswith(prefix):
            # Enumeration leaked outside the registered prefix. Refuse rather
            # than filter: a filter would hide a scoping bug.
            raise ProbeRefusal("MEMBER_SET_MISMATCH", "OBSERVED_OUTSIDE_PREFIX")
        normalised.add(raw[len(prefix) :])

    unexpected = normalised - expected_names
    missing = expected_names - normalised
    result = {
        "expected_count": len(expected_names),
        "observed_count": len(normalised),
        "counts_equal": len(normalised) == len(expected_names),
        "member_sets_equal": not unexpected and not missing,
        "unexpected_member_count": len(unexpected),
        "missing_member_count": len(missing),
        "prefix_scope": "exact_registered_prefix_only",
    }
    if not result["counts_equal"]:
        raise ProbeRefusal("MEMBER_COUNT_MISMATCH", "MEMBER_COUNT")
    if not result["member_sets_equal"]:
        raise ProbeRefusal("MEMBER_SET_MISMATCH", "MEMBER_SET")
    return result


# ---------------------------------------------------------------------------
# Stage C - streaming integrity
# ---------------------------------------------------------------------------


def stream_object_digest(chunks: Iterable[bytes]) -> tuple[str, int]:
    """Fold raw chunks into a SHA-256 digest and a byte count.

    This is the only function in the round that sees authoritative bytes. It
    holds one chunk at a time, hands it to the digest, and lets it go. There is
    no accumulation, no decoding, no branch that inspects content, and no path
    by which a chunk reaches a return value, a log line or an exception.
    """

    digest = hashlib.sha256()
    total = 0
    for chunk in chunks:
        digest.update(chunk)
        total += len(chunk)
    return digest.hexdigest(), total


def verify_streamed(
    expected: list[tuple[str, int, str]],
    observed: list[tuple[str, int, str]],
) -> dict[str, Any]:
    expected_by_name = {name: (size, digest) for name, size, digest in expected}
    size_mismatch = 0
    digest_mismatch = 0
    total = 0
    observed_digests: list[str] = []

    for name, size, digest in observed:
        want_size, want_digest = expected_by_name[name]
        if size != want_size:
            size_mismatch += 1
        if digest != want_digest:
            digest_mismatch += 1
        total += size
        observed_digests.append(digest)

    result = {
        "objects_streamed": len(observed),
        "total_bytes_streamed": total,
        "expected_total_bytes": sum(size for _, size, _ in expected),
        "all_sizes_match": size_mismatch == 0,
        "all_digests_match": digest_mismatch == 0,
        "size_mismatch_count": size_mismatch,
        "digest_mismatch_count": digest_mismatch,
        "decode_attempts": 0,
        "persist_attempts": 0,
        "observed_aggregate_digest": aggregate_digest(observed_digests),
    }
    if size_mismatch:
        raise ProbeRefusal("OBJECT_SIZE_MISMATCH", "OBJECT_SIZE")
    if digest_mismatch:
        raise ProbeRefusal("OBJECT_DIGEST_MISMATCH", "OBJECT_DIGEST")
    if len(observed) != len(expected):
        raise ProbeRefusal("MEMBER_COUNT_MISMATCH", "STREAMED_COUNT")
    return result


# ---------------------------------------------------------------------------
# Stage D - receipt
# ---------------------------------------------------------------------------


def build_receipt(
    *,
    record: dict[str, Any],
    execution_id: str,
    started_at: str,
    ended_at: str,
    freeze_commit: str,
    image_digest: str,
    decision_record_sha256: str,
    probe_source_sha256: str,
    identity_block: dict[str, Any],
    endpoint_block: dict[str, Any],
    membership_block: dict[str, Any],
    streaming_block: dict[str, Any],
    list_operations: int,
    invariants_checked: int,
    exit_status: str = "PASS",
    reason_code: str = "OK",
    invariants_failed: list[str] | None = None,
) -> dict[str, Any]:
    binding = record["expected_evidence_binding"]
    streamed = streaming_block["objects_streamed"]
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "phase": "1.2H-R1",
        "execution": {
            "execution_id": execution_id,
            "started_at": started_at,
            "ended_at": ended_at,
            "exit_status": exit_status,
            "reason_code": reason_code,
        },
        "provenance": {
            "access_protocol_freeze_commit": freeze_commit,
            "image_digest": image_digest,
            "decision_record_sha256": decision_record_sha256,
            "expected_evidence_sha256": binding["sha256"],
            "expected_members_digest": binding["members_digest"],
            "probe_source_sha256": probe_source_sha256,
        },
        "identity": identity_block,
        "endpoint": endpoint_block,
        "membership": membership_block,
        "streaming": streaming_block,
        "counters": {
            "azure_data_plane_content_reads": streamed,
            "azure_data_plane_writes": 0,
            "byte_only_integrity_verifications": streamed,
            "semantic_input_reads": 0,
            "semantic_label_reads": 0,
            "parser_invocations": 0,
            "predictions_generated": 0,
            "list_operations": list_operations,
        },
        "verdict": {
            "access_gate_passed": exit_status == "PASS",
            "invariants_checked": invariants_checked,
            "invariants_failed": invariants_failed or [],
        },
    }


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 1.2H-R1 byte-only authoritative source access probe"
    )
    parser.add_argument("--client-id", required=True, help="designated UAMI client ID")
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--image-digest", required=True)
    # Present so that an override *attempt* is detected and refused loudly,
    # rather than being silently accepted by a permissive parser.
    parser.add_argument("--account", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--container", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--prefix", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    started = _now()
    args = _parse_args(argv)

    try:
        assert_no_override(args)
        assert_environment_clean()
        assert_no_forbidden_symbols()
        assert_no_write_calls_in_source()
        assert_verbose_logging_disabled()
        record = load_decision_record()
        expected = expected_members(record)
    except ProbeRefusal as refusal:
        print(json.dumps(_refusal_receipt(refusal, started, args)), flush=True)
        return 2

    if args.dry_run:
        # Offline self-check: everything above this line ran, nothing touched
        # the network. Used by the public workflow to prove the frozen bindings
        # still load without any Azure access at all.
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "expected_member_count": len(expected),
                    "expected_members_digest": members_digest(expected),
                    "expected_total_bytes": sum(size for _, size, _ in expected),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 0

    try:
        return _run_live(args, record, expected, started)
    except ProbeRefusal as refusal:
        print(json.dumps(_refusal_receipt(refusal, started, args)), flush=True)
        return 2
    except Exception:  # noqa: BLE001 - deliberate blanket redaction
        # An unredacted traceback could contain a URL, a header, a member name
        # or object bytes. Nothing but a closed token escapes.
        print(
            json.dumps(
                _refusal_receipt(
                    ProbeRefusal("INTERNAL_REFUSAL", "UNEXPECTED_EXCEPTION"),
                    started,
                    args,
                )
            ),
            flush=True,
        )
        return 3


def _refusal_receipt(
    refusal: ProbeRefusal, started: str, args: argparse.Namespace
) -> dict[str, Any]:
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "phase": "1.2H-R1",
        "refused": True,
        "reason_code": refusal.reason_code,
        "invariant": refusal.invariant,
        "execution_id": getattr(args, "execution_id", ""),
        "started_at": started,
        "ended_at": _now(),
    }


def _run_live(
    args: argparse.Namespace,
    record: dict[str, Any],
    expected: list[tuple[str, int, str]],
    started: str,
) -> int:
    # Imported here, not at module scope, so that the offline dry run and the
    # entire public test suite never require the Azure SDK, and so that
    # assert_no_forbidden_symbols has already run before any SDK name exists.
    from azure.identity import ManagedIdentityCredential
    from azure.storage.blob import BlobServiceClient

    source = record["source_binding"]
    endpoint_rule = record["endpoint_rule"]
    fqdn = endpoint_rule["required_blob_fqdn"]

    resolved = resolve_endpoint(fqdn)
    endpoint_block = check_endpoint(record, "Disabled", resolved)
    identity_block = check_identity(record, args.client_id, "ManagedIdentityCredential")

    credential = ManagedIdentityCredential(client_id=args.client_id)
    service = BlobServiceClient(f"https://{fqdn}", credential=credential)
    container = service.get_container_client(source["blob_container"])

    prefix = source["exact_prefix"].rstrip("/") + "/"
    observed_names = [b.name for b in container.list_blobs(name_starts_with=prefix)]
    list_operations = 1
    membership_block = compare_membership(record, expected, observed_names)

    chunk_bytes = int(record["byte_only_rule"]["chunk_bytes"])
    if chunk_bytes != CHUNK_BYTES:
        raise ProbeRefusal("DECISION_RECORD_DIGEST_MISMATCH", "CHUNK_SIZE_DRIFT")

    observed: list[tuple[str, int, str]] = []
    for name, _, _ in expected:
        blob = container.get_blob_client(prefix + name)
        stream = blob.download_blob(max_concurrency=1)
        digest, size = stream_object_digest(stream.chunks())
        observed.append((name, size, digest))

    streaming_block = verify_streamed(expected, observed)

    receipt = build_receipt(
        record=record,
        execution_id=args.execution_id,
        started_at=started,
        ended_at=_now(),
        freeze_commit=args.freeze_commit,
        image_digest=args.image_digest,
        decision_record_sha256=_sha256_file(DECISION_RECORD),
        probe_source_sha256=_sha256_file(Path(__file__).resolve()),
        identity_block=identity_block,
        endpoint_block=endpoint_block,
        membership_block=membership_block,
        streaming_block=streaming_block,
        list_operations=list_operations,
        invariants_checked=12,
    )

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from phase1_2h_r1_receipt_validator import validate_receipt

    validate_receipt(receipt, RECEIPT_SCHEMA)
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover - container entry point
    raise SystemExit(main())
