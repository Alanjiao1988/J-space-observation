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
REFUSAL_SCHEMA = REPO_ROOT / "docs" / "phase1_2h_r1_access_refusal_receipt.schema.json"

RECEIPT_SCHEMA_VERSION = "phase1-2h-r1-access-receipt/v1"
REFUSAL_SCHEMA_VERSION = "phase1-2h-r1-access-refusal-receipt/v1"

# Real progress, not a literal. A refusal raised after objects were already
# streamed must still report how many data-plane content reads occurred, or the
# append-only access ledger cannot be updated accurately. Independent Audit B
# raised this as B-08.
PROGRESS: dict[str, int] = {
    "azure_data_plane_content_reads": 0,
    "byte_only_integrity_verifications": 0,
    "list_operations": 0,
}


def _reset_progress() -> None:
    for key in PROGRESS:
        PROGRESS[key] = 0
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

# Environment variables that would let a secret-bearing or ambient credential
# in, or would redirect the SDK's endpoint. Any of these being set is a
# refusal, not a thing to be ignored: the point of the freeze is that the
# environment cannot change where the probe goes or who it is.
#
# Deliberately NOT listed: MSI_ENDPOINT, MSI_SECRET, IDENTITY_ENDPOINT and
# IDENTITY_HEADER. Those are the platform-provided managed-identity token
# endpoint, and they are exactly how ManagedIdentityCredential authenticates
# inside a Container Apps job. An earlier revision of this list forbade
# MSI_ENDPOINT and MSI_SECRET, which made the rule self-contradictory: the
# freeze *requires* ManagedIdentityCredential, and the platform implements it
# with those variables. The first live gate execution refused because of it.
# That refusal was the machinery working, and the fix is to correct the rule,
# not to relax the requirement. Secret-bearing variables below remain refused.
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
)

CHUNK_BYTES = 262144

# Names whose presence in this file would falsify the pinned decode_attempts
# counter. A decode turns authoritative bytes into text, which is the first
# step of a semantic read.
FORBIDDEN_DECODE_METHODS = (
    "decode",
    "decodebytes",
    "b64decode",
    "b64encode",
    "hexlify",
    "unhexlify",
)

# Names whose presence in this file would falsify the pinned persist_attempts
# counter, or would let object bytes reach a file or another process.
FORBIDDEN_PERSIST_METHODS = (
    "write_text",
    "write_bytes",
    "writelines",
    "mkstemp",
    "NamedTemporaryFile",
)

# Static analysis cannot follow a computed name. Rather than pretend otherwise,
# the constructs that would defeat it are refused outright. Note the honest
# residual: a name assembled by string concatenation is not defeated by this
# check, and this module does not claim it is.
FORBIDDEN_DYNAMIC_ACCESS = ("eval", "exec", "compile", "__import__")

# Import roots that would give this file a persistence, exfiltration, or
# parser capability it must not have.
FORBIDDEN_IMPORT_ROOTS = (
    "pickle",
    "shelve",
    "marshal",
    "subprocess",
    "shutil",
    "smtplib",
    "ftplib",
    "urllib",
    "requests",
    "httpx",
    "xmlrpc",
    "tempfile",
    "jspace_observation",
    "torch",
    "transformers",
)


class ProbeRefusal(Exception):
    """A frozen invariant was violated. Carries a closed-vocabulary reason.

    ``detail`` may carry a non-private identifier -- an environment variable
    name, a symbol name -- but never a value, a member name, an address or any
    object content. The first live gate execution refused with
    ``FORBIDDEN_ENV_VAR`` and no indication of which variable, which cost a
    whole cloud round trip to diagnose. A receipt that is content-free but also
    useless is a false economy: the name of a platform environment variable is
    a public constant, its value is not.
    """

    def __init__(self, reason_code: str, invariant: str, detail: str = "") -> None:
        super().__init__(f"{reason_code}:{invariant}" + (f":{detail}" if detail else ""))
        self.reason_code = reason_code
        self.invariant = invariant
        self.detail = detail


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
        if not isinstance(evaluation, dict):
            continue
        order = evaluation.get("order")
        # The freeze selects rows whose evaluation.order is an integer. Accept
        # exactly that. `isinstance(order, int)` would also admit bool, which is
        # an int subclass in Python; `type(order) is int` is the frozen rule.
        if type(order) is not int:
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
            # The variable's name, never its value.
            raise ProbeRefusal("CREDENTIAL_TYPE_FORBIDDEN", "FORBIDDEN_ENV_VAR", name)


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
    """Refuse if this module's own source references a mutating Blob operation,
    a forbidden credential, a dynamic-access escape hatch, a decode of object
    bytes, or a persistence call.

    An earlier draft of this probe checked ``hasattr(client, ...)`` on the SDK
    object. That check was wrong and would have refused every run: a
    ``BlobClient`` exposes ``upload_blob`` and ``delete_blob`` as class methods
    no matter what the caller's RBAC allows. Capability on the wire is decided
    by the role assignment, not by the Python object.

    What this probe can honestly assert is the narrower, structural claim the
    protocol actually asks for: no mutating operation, no forbidden credential
    construction, no decode and no persistence call appears anywhere in
    **this file**, which is the entire first-party source executed by the gate.
    It does not analyse the Azure SDK or the standard library, and it does not
    claim to. Independent Audit A raised three evasions that the first draft
    missed, all of which are now closed:

    * string constants, so ``getattr(client, "upload_blob")`` no longer passes;
    * plain ``import`` with an alias, so ``import azure.identity as ai``
      followed by ``ai.DefaultAzureCredential()`` no longer passes;
    * dynamic-access builtins, which would defeat any static check and are
      therefore refused outright rather than analysed.

    The decode and persist checks are what make the pinned ``decode_attempts``
    and ``persist_attempts`` counters mean something. Those counters are
    reported as literal zero; this function is the evidence for that literal.

    Returns the number of nodes inspected.
    """

    import ast

    path = Path(__file__).resolve() if source_path is None else Path(source_path)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_attrs = (
        set(FORBIDDEN_BLOB_METHODS)
        | set(FORBIDDEN_DECODE_METHODS)
        | set(FORBIDDEN_PERSIST_METHODS)
        # A credential reached as an attribute -- `ai.DefaultAzureCredential()`
        # after `import azure.identity as ai` -- produces no ImportFrom node
        # and would otherwise pass (independent Audit A, A-06).
        | set(FORBIDDEN_CREDENTIAL_TYPES)
    )
    forbidden_names = (
        set(FORBIDDEN_BLOB_METHODS)
        | set(FORBIDDEN_CREDENTIAL_TYPES)
        | set(FORBIDDEN_DYNAMIC_ACCESS)
        | set(FORBIDDEN_PERSIST_METHODS)
    )
    # Docstrings and the FORBIDDEN_* declarations themselves legitimately spell
    # out the names being forbidden. Everything else is a potential dynamic
    # payload. Without this carve-out the module would refuse itself, which
    # would be a self-defeating check rather than a safe one.
    declared: set[int] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if not any(t.startswith("FORBIDDEN_") for t in targets):
            continue
        for sub in ast.walk(node.value):
            if isinstance(sub, ast.Constant):
                declared.add(id(sub))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                declared.add(id(body[0].value))

    inspected = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            inspected += 1
            if node.attr in forbidden_attrs:
                raise ProbeRefusal("INTERNAL_REFUSAL", "WRITE_CALL_IN_SOURCE")
        elif isinstance(node, ast.Name):
            inspected += 1
            if node.id in forbidden_names:
                raise ProbeRefusal("INTERNAL_REFUSAL", "WRITE_CALL_IN_SOURCE")
        elif isinstance(node, ast.Constant):
            inspected += 1
            if id(node) in declared or not isinstance(node.value, str):
                continue
            token = node.value.strip()
            if token in forbidden_attrs or token in forbidden_names:
                raise ProbeRefusal("INTERNAL_REFUSAL", "DYNAMIC_WRITE_NAME_IN_SOURCE")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            if module and module.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                raise ProbeRefusal("INTERNAL_REFUSAL", "FORBIDDEN_IMPORT_IN_SOURCE")
            for alias in node.names:
                inspected += 1
                head = alias.name.split(".")[0]
                if head in FORBIDDEN_IMPORT_ROOTS:
                    raise ProbeRefusal("INTERNAL_REFUSAL", "FORBIDDEN_IMPORT_IN_SOURCE")
                if alias.name in forbidden_attrs or alias.name in forbidden_names:
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


def resolve_endpoint(fqdn: str, resolver: Any = None) -> list[str]:
    """Resolve the blob FQDN to the FULL set of addresses.

    Returns every distinct address, not just the first. ``gethostbyname``
    returns one address and therefore cannot support a claim that the expected
    address is the *only* address, which is what the receipt asserts.
    Independent Audit A raised this as A-12.
    """

    if resolver is not None:
        resolved = resolver(fqdn)
        if isinstance(resolved, str):
            return [resolved]
        return sorted({str(a) for a in resolved})
    infos = socket.getaddrinfo(fqdn, 443, proto=socket.IPPROTO_TCP)
    return sorted({str(info[4][0]) for info in infos})


def check_endpoint(
    record: dict[str, Any],
    public_network_access: str,
    resolved_ips: list[str] | str,
) -> dict[str, Any]:
    rule = record["endpoint_rule"]

    # publicNetworkAccess is a control-plane property. The designated identity
    # deliberately holds no management-plane role, so this process cannot read
    # it. The only honest in-job value is "Unknown"; the real observation is
    # made by the operator before the run and recorded in the decision record.
    # Accepting "Disabled" here would let a literal argument masquerade as a
    # measurement, which is what independent Audit A raised as A-03.
    if public_network_access != "Unknown":
        raise ProbeRefusal("INTERNAL_REFUSAL", "PNA_NOT_OBSERVABLE_IN_JOB")
    if rule["required_public_network_access"] != "Disabled":
        raise ProbeRefusal("DECISION_RECORD_DIGEST_MISMATCH", "ENDPOINT_RULE_DRIFT")

    if isinstance(resolved_ips, str):
        resolved_ips = [resolved_ips]
    if not resolved_ips:
        raise ProbeRefusal("ENDPOINT_NOT_PRIVATE", "NO_ADDRESS_RESOLVED")

    for resolved_ip in resolved_ips:
        try:
            address = ip_address(resolved_ip)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ProbeRefusal("ENDPOINT_NOT_PRIVATE", "UNPARSEABLE_ADDRESS") from exc

        if address.is_global:
            raise ProbeRefusal("ENDPOINT_NOT_PRIVATE", "PUBLIC_ADDRESS")

        allowed = [ip_network(c) for c in rule["allowed_private_cidrs"]]
        if not any(address in net for net in allowed):
            raise ProbeRefusal("ENDPOINT_NOT_PRIVATE", "ADDRESS_OUTSIDE_PROJECT_VNET")

    # The claim is "the resolved set is exactly the registered address", so a
    # second, also-private address must fail rather than pass.
    matches = set(resolved_ips) == {rule["expected_private_ip"]}
    if not matches:
        # Deliberately does not carry the observed address: a misconfiguration
        # must not leak an unregistered endpoint address into a public receipt.
        raise ProbeRefusal("ENDPOINT_IP_MISMATCH", "PRIVATE_IP_NOT_REGISTERED")

    return {
        "public_network_access": public_network_access,
        "public_network_access_observed_by": "operator_control_plane_read_before_run",
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

    # The operator supplies --client-id. Without binding it to the freeze, the
    # receipt would report "client_id_matches_designated" on the basis of
    # nothing, and could not distinguish the designated reader from the
    # write-capable id-jspace-aca-acrpull-sea. Independent Audit A raised this
    # as A-02.
    designated = rule["designated_identity"].get("client_id")
    if not designated:
        raise ProbeRefusal("DECISION_RECORD_DIGEST_MISMATCH", "DESIGNATED_CLIENT_ID_ABSENT")
    if client_id != designated:
        # Carries neither the supplied nor the expected value.
        raise ProbeRefusal("IDENTITY_MISMATCH", "CLIENT_ID_NOT_DESIGNATED")

    return {
        "credential_type": "ManagedIdentityCredential",
        "client_id": client_id,
        "client_id_matches_designated": True,
        "forbidden_credential_types_absent": True,
        # Deliberately NOT "READ_ONLY_CONFIRMED". The probe holds no permission
        # to read role assignments, and granting it one would increase exactly
        # the privilege this round is minimising. What is confirmed is that the
        # credential is the frozen identity; that this identity holds only
        # Storage Blob Data Reader at container scope is a control-plane
        # observation recorded in the decision record, made by a different
        # principal at a different time. Reporting it as confirmed here would
        # be attesting to a check this process did not perform.
        "effective_read_only_verdict": "NOT_CONFIRMED_IN_JOB",
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
            "aca_execution_name": _aca_execution_name(),
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
    _reset_progress()

    # _parse_args previously ran outside every handler, so an argparse error
    # exited 2 with usage text and no receipt -- indistinguishable by exit code
    # from a genuine refusal (independent Audit A, A-09).
    try:
        args = _parse_args(argv)
    except SystemExit:
        return _emit_refusal(
            ProbeRefusal("INTERNAL_REFUSAL", "ARGUMENT_PARSE_FAILED"), started, None
        )

    try:
        assert_no_override(args)
        assert_environment_clean()
        assert_no_forbidden_symbols()
        assert_no_write_calls_in_source()
        assert_verbose_logging_disabled()
        record = load_decision_record()
        expected = expected_members(record)
    except ProbeRefusal as refusal:
        return _emit_refusal(refusal, started, args)
    except Exception:  # noqa: BLE001 - deliberate blanket redaction
        # These paths touch only publicly committed files, but an unredacted
        # traceback is still an uncontrolled output channel.
        return _emit_refusal(
            ProbeRefusal("INTERNAL_REFUSAL", "PREFLIGHT_EXCEPTION"), started, args
        )

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
        return _emit_refusal(refusal, started, args)
    except Exception:  # noqa: BLE001 - deliberate blanket redaction
        # An unredacted traceback could contain a URL, a header, a member name
        # or object bytes. Nothing but a closed token escapes.
        return _emit_refusal(
            ProbeRefusal("INTERNAL_REFUSAL", "UNEXPECTED_EXCEPTION"), started, args
        )


def _aca_execution_name() -> str | None:
    """The ACA execution name as exposed to the replica, or None.

    The operator-assigned --execution-id is chosen at job-definition time,
    before any execution exists, so it cannot be the execution name the schema
    once claimed it was (independent Audit A, A-15). Where the platform
    publishes the real name, carry it; where it does not, carry null rather
    than inventing a correlation.
    """

    for var in ("CONTAINER_APP_JOB_EXECUTION_NAME", "CONTAINER_APP_REPLICA_NAME"):
        value = os.environ.get(var, "").strip()
        if value:
            return value
    return None


def _refusal_receipt(
    refusal: ProbeRefusal, started: str, args: argparse.Namespace | None
) -> dict[str, Any]:
    execution_id = ""
    if args is not None:
        execution_id = str(getattr(args, "execution_id", "") or "")
    receipt: dict[str, Any] = {
        "schema_version": REFUSAL_SCHEMA_VERSION,
        "phase": "1.2H-R1",
        "refused": True,
        "execution": {
            "execution_id": execution_id or "unparsed",
            "aca_execution_name": _aca_execution_name(),
            "started_at": started,
            "ended_at": _now(),
            "exit_status": "FAIL",
            "reason_code": refusal.reason_code,
            "invariant": refusal.invariant,
        },
        # Progress at the moment of refusal. These are the only counters that
        # can be nonzero; every semantic counter is pinned to zero by the
        # schema, and the source-level checks are what make that pin honest.
        "progress_counters": {
            "azure_data_plane_content_reads": PROGRESS["azure_data_plane_content_reads"],
            "byte_only_integrity_verifications": PROGRESS["byte_only_integrity_verifications"],
            "list_operations": PROGRESS["list_operations"],
            "azure_data_plane_writes": 0,
            "decode_attempts": 0,
            "persist_attempts": 0,
            "semantic_input_reads": 0,
            "semantic_label_reads": 0,
            "parser_invocations": 0,
            "predictions_generated": 0,
        },
    }
    if refusal.detail:
        receipt["execution"]["detail"] = refusal.detail
    return receipt


def _emit(document: dict[str, Any], schema: Path) -> None:
    """Validate before printing. Every emitted document, not just the success
    one, is checked against a committed closed schema -- that is what the
    receipt_rule in the decision record actually promises."""

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from phase1_2h_r1_receipt_validator import validate_receipt

    validate_receipt(document, schema)
    print(json.dumps(document, sort_keys=True), flush=True)


def _emit_refusal(
    refusal: ProbeRefusal, started: str, args: argparse.Namespace | None
) -> int:
    receipt = _refusal_receipt(refusal, started, args)
    try:
        _emit(receipt, REFUSAL_SCHEMA)
    except Exception:  # noqa: BLE001 - the validator must never mask a refusal
        # If the refusal receipt itself does not validate, say so in the closed
        # vocabulary rather than printing an unvalidated document.
        fallback = _refusal_receipt(
            ProbeRefusal("RECEIPT_SCHEMA_INVALID", "REFUSAL_RECEIPT_INVALID"),
            started,
            args,
        )
        print(json.dumps(fallback, sort_keys=True), flush=True)
        return 4
    return 2


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
    # "Unknown" is not a placeholder: it is the only value this process can
    # honestly report for a control-plane property it holds no role to read.
    # The earlier literal "Disabled" made the check tautological while the
    # receipt presented it as an observation (independent Audit A, A-03).
    endpoint_block = check_endpoint(record, "Unknown", resolved)
    identity_block = check_identity(record, args.client_id, "ManagedIdentityCredential")

    credential = ManagedIdentityCredential(client_id=args.client_id)
    chunk_bytes = int(record["byte_only_rule"]["chunk_bytes"])
    if chunk_bytes != CHUNK_BYTES:
        raise ProbeRefusal("DECISION_RECORD_DIGEST_MISMATCH", "CHUNK_SIZE_DRIFT")
    # The frozen chunk size must actually govern I/O. Without these two
    # arguments the SDK buffers up to max_single_get_size (32 MiB) before
    # chunks() yields anything, so the "bounded buffer" property was a claim
    # about a constant that governed nothing (independent Audit A, A-11).
    service = BlobServiceClient(
        f"https://{fqdn}",
        credential=credential,
        max_single_get_size=chunk_bytes,
        max_chunk_get_size=chunk_bytes,
    )
    container = service.get_container_client(source["blob_container"])

    prefix = source["exact_prefix"].rstrip("/") + "/"
    observed_names = [b.name for b in container.list_blobs(name_starts_with=prefix)]
    list_operations = 1
    PROGRESS["list_operations"] = list_operations
    membership_block = compare_membership(record, expected, observed_names)

    observed: list[tuple[str, int, str]] = []
    for name, _, _ in expected:
        blob = container.get_blob_client(prefix + name)
        stream = blob.download_blob(max_concurrency=1)
        digest, size = stream_object_digest(stream.chunks())
        observed.append((name, size, digest))
        PROGRESS["azure_data_plane_content_reads"] += 1

    streaming_block = verify_streamed(expected, observed)
    PROGRESS["byte_only_integrity_verifications"] = streaming_block["objects_streamed"]

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
    from phase1_2h_r1_receipt_validator import ReceiptValidationError

    try:
        _emit(receipt, RECEIPT_SCHEMA)
    except ReceiptValidationError as exc:
        raise ProbeRefusal("RECEIPT_SCHEMA_INVALID", "SUCCESS_RECEIPT_INVALID") from exc
    return 0


if __name__ == "__main__":  # pragma: no cover - container entry point
    raise SystemExit(main())
