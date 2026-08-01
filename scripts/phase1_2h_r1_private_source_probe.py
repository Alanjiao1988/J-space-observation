#!/usr/bin/env python3
"""Phase 1.2H-R1 authoritative-source byte-only access probe.

This program runs inside the in-VNet Azure Container Apps job. It is the only
code in this round authorized to touch the authoritative retired ``parser-v3-v1``
sealed source, and it is authorized to do exactly one thing with it: prove, by
streaming raw bytes into SHA-256 accumulators, that what is in the sealed prefix
is byte-for-byte what the committed public record says was sealed there.

It never decodes those bytes. A byte-only integrity verification is not a
semantic read, and this probe is built so that the distinction is enforced
structurally in its own source rather than merely promised:

* the only function that holds object bytes binds each chunk to a loop
  variable, passes it to a SHA-256 digest, and uses that name nowhere else ---
  no assignment, no return, no further iteration, no non-digest call. This is a
  statement about the reference graph in this source. It is NOT a statement
  that the bytes are erased from process memory: CPython drops the reference
  when the loop rebinds, and the allocator reuses the storage on its own
  schedule, which this program neither controls nor observes;
* no syntactic construct in that function can turn a chunk into text;
* the receipt schema has no field that could carry one; and
* the module refuses to run if a decode-capable or write-capable Blob symbol is
  reachable from its own module namespace.

These are properties of first-party source, checked by AST analysis of that
source. They say nothing about the Azure SDK that yields the chunks, the
standard library, or the base image.

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
import functools
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
# step of a semantic read. These six are refused *module-wide* because this
# module has no legitimate use for any of them anywhere.
#
# Independent Audit C (C-06) found this list covered only 5 of the 9 frozen
# forbidden_operations. The four it missed --- `str()` on object bytes, json
# parsing, line splitting or text iteration, and regular expression matching
# over object bytes --- are deliberately NOT added here, because they are not
# module-wide defects: this probe legitimately reads and parses the *public*
# committed evidence file, which is what `read_expected_members` does, and a
# module-wide ban on `splitlines` and `json.loads` would refuse that.
#
# The frozen rule forbids those operations on *object bytes*, which is a
# narrower claim and a different check. It is enforced positively by
# `assert_byte_handling_is_digest_only`, which whitelists every call inside the
# one function that ever holds a chunk. See that function for why a whitelist
# is the right instrument and a wider denylist is not.
FORBIDDEN_DECODE_METHODS = (
    "decode",
    "decodebytes",
    "b64decode",
    "b64encode",
    "hexlify",
    "unhexlify",
)

# Builtins and module functions that would turn object bytes into text, a
# structure, or a match. `str` and `repr` are the direct route; the `json` and
# `re` entry points are the frozen rule's "json or jsonl parsing" and "regular
# expression matching over object bytes".
#
# These are NOT applied as a module-wide denylist: this module legitimately
# calls `str` and `split` on identifiers and configuration, and a rule that
# refused those would either refuse the module or need carve-outs that
# reintroduce the gap. The frozen rule forbids these operations *on object
# bytes*, and that is enforced positively by
# `assert_byte_handling_is_digest_only`. This tuple is retained as the frozen
# rule's vocabulary, and the boundary tests assert that every entry is refused
# inside the byte-handling function.
FORBIDDEN_INTERPRETATION_NAMES = (
    "str",
    "repr",
    "chr",
    "format",
    "hex",
    "fromhex",
    "from_bytes",
    "splitlines",
    "loads",
    "load",
    "JSONDecoder",
    "search",
    "match",
    "fullmatch",
    "findall",
    "finditer",
    "split",
    "sub",
    "subn",
)

#: The only function that ever holds a chunk of an authoritative object.
BYTE_HANDLING_FUNCTION = "stream_object_digest"

#: Every call permitted inside :data:`BYTE_HANDLING_FUNCTION`. A whitelist,
#: because the set of ways to interpret bytes is open and the set of ways to
#: digest them is not: construct the hash, feed it, measure the chunk, render
#: the result. Nothing else is needed and nothing else is allowed.
_DIGEST_ONLY_CALLS = frozenset({"sha256", "update", "len", "hexdigest"})

#: Every frozen invariant this execution actually evaluated, recorded as it is
#: evaluated rather than counted in advance.
#:
#: Independent Audit C (C-12) found ``invariants_checked`` emitted as the
#: literal ``12`` and then restated in six documents as though the probe had
#: measured it. It had not: the number was written by hand, so adding or
#: removing a check would not have changed it, and a receipt reporting 12 could
#: have come from a run that evaluated three. A field that cannot disagree with
#: reality is not a measurement.
#:
#: A set rather than a list, because the public test suite calls several of
#: these functions repeatedly and an invariant evaluated twice is still one
#: invariant.
INVARIANTS_EVALUATED: set[str] = set()


def _record_invariant(name: str) -> None:
    """Note that a named frozen invariant was actually evaluated."""

    INVARIANTS_EVALUATED.add(name)


def _invariant(name: str) -> Any:
    """Mark a function as evaluating a named frozen invariant.

    Records only on successful return, so a refusal is not counted as an
    invariant that held. Binding the record to the function definition rather
    than to a call site is deliberate: deleting the check deletes the count,
    which is the property Audit C (C-12) found missing when the number was a
    literal.
    """

    def decorate(func: Any) -> Any:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            _record_invariant(name)
            return result

        wrapper.invariant_name = name  # type: ignore[attr-defined]
        return wrapper

    return decorate

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

#: Audit E (E-20). Forms that bind a module global without an assignment
#: statement, so that no scan of assignment targets can see them. Audit E used
#: ``globals()['stream_object_digest'] = _tap(...)`` and
#: ``setattr(sys.modules[__name__], 'stream_object_digest', _tap)`` to replace
#: the analysed handler with a wrapper that retained every chunk; both passed.
#: A syntactic binding scan only means something if the source cannot bind
#: names non-syntactically, so these are refused in first-party in-job source.
FORBIDDEN_REFLECTIVE_MUTATION = ("setattr", "delattr")

#: Namespace mappings that must not be used as assignment targets. Reading
#: ``globals()`` stays permitted --- the reachability check in this module
#: needs it --- but ``globals()[name] = value`` is a store.
FORBIDDEN_NAMESPACE_STORES = ("globals", "vars", "locals")

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
    "codecs",
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


@_invariant("DECISION_RECORD_DIGEST")
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


@_invariant("EXPECTED_EVIDENCE_DIGEST")
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


@_invariant("NO_ARGUMENT_OVERRIDE")
def assert_no_override(argv_namespace: argparse.Namespace) -> None:
    """The frozen source binding may not be redirected from outside."""

    if getattr(argv_namespace, "account", None) is not None:
        raise ProbeRefusal("SOURCE_BINDING_OVERRIDE_ATTEMPTED", "ACCOUNT_OVERRIDE")
    if getattr(argv_namespace, "container", None) is not None:
        raise ProbeRefusal("SOURCE_BINDING_OVERRIDE_ATTEMPTED", "CONTAINER_OVERRIDE")
    if getattr(argv_namespace, "prefix", None) is not None:
        raise ProbeRefusal("SOURCE_BINDING_OVERRIDE_ATTEMPTED", "PREFIX_OVERRIDE")


@_invariant("ENVIRONMENT_CLEAN")
def assert_environment_clean(environ: dict[str, str] | None = None) -> None:
    env = os.environ if environ is None else environ
    for name in FORBIDDEN_ENV_VARS:
        if env.get(name):
            # The variable's name, never its value.
            raise ProbeRefusal("CREDENTIAL_TYPE_FORBIDDEN", "FORBIDDEN_ENV_VAR", name)


@_invariant("NO_FORBIDDEN_SDK_SYMBOL")
def assert_no_forbidden_symbols(namespace: dict[str, Any] | None = None) -> None:
    """Refuse if a forbidden credential or write-capable symbol is reachable."""

    ns = globals() if namespace is None else namespace
    for name in FORBIDDEN_CREDENTIAL_TYPES:
        if name in ns:
            raise ProbeRefusal("CREDENTIAL_TYPE_FORBIDDEN", "FORBIDDEN_CREDENTIAL_SYMBOL")
    for name in FORBIDDEN_BLOB_METHODS:
        if name in ns:
            raise ProbeRefusal("INTERNAL_REFUSAL", "FORBIDDEN_BLOB_SYMBOL")


@_invariant("NO_WRITE_CALL_IN_SOURCE")
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
    construction, no decode and no persistence call appears anywhere in the
    first-party source the gate executes. It does not analyse the Azure SDK or
    the standard library, and it does not claim to. Independent Audit A raised
    three evasions that the first draft missed, all of which are now closed:

    * string constants, so ``getattr(client, "upload_blob")`` no longer passes;
    * plain ``import`` with an alias, so ``import azure.identity as ai``
      followed by ``ai.DefaultAzureCredential()`` no longer passes;
    * dynamic-access builtins, which would defeat any static check and are
      therefore refused outright rather than analysed.

    Independent Audit C (C-14) found the scope claim wrong rather than the check
    wrong. The docstring said "this file, which is the entire first-party source
    executed by the gate", but ``phase1_2h_r1_receipt_validator.py`` also runs
    inside the job --- the probe imports it to validate the receipt before
    emitting it --- and was never analysed. It is clean, so nothing unsafe
    followed; the defect was that the sentence claimed a coverage the code did
    not have. :func:`assert_no_write_calls_in_first_party_source` now covers
    both files, and :data:`IN_JOB_FIRST_PARTY_SOURCES` is the list, so the claim
    and the check move together.

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


@_invariant("BYTE_HANDLING_DIGEST_ONLY")
def assert_byte_handling_is_digest_only(source_path: Path | None = None) -> int:
    """Constrain every operation performed on authoritative bytes.

    :func:`stream_object_digest` is the only function in the round that holds a
    chunk of an authoritative object. The frozen ``byte_only_rule`` forbids nine
    operations on those bytes, and independent Audit C (C-06) found the
    name-denylist check covered five of them. Four --- ``str()`` on object
    bytes, json parsing, line splitting or text iteration, and regular
    expression matching --- had no enforcement at all.

    Extending the denylist would not have fixed that honestly. ``str``,
    ``split`` and ``loads`` are ordinary operations that this module performs
    legitimately on identifiers and configuration, so banning the *names*
    everywhere would either refuse the module or require carve-outs that
    reintroduce the gap. The frozen rule is not "never call ``str``"; it is
    "never call ``str`` **on object bytes**", and that distinction is a property
    of one function.

    So this check inverts the polarity. Inside the byte-handling function, every
    call must appear in :data:`_DIGEST_ONLY_CALLS`; anything else is refused
    whether or not anyone anticipated it.

    Independent Audit E (E-02) then found the docstring calling that whitelist
    "complete", which it was not: a call whitelist constrains calls, and
    ``global SINK; SINK = chunk``, ``return chunk`` and ``for b in chunk`` are
    not calls. It also matched attribute calls by name only, so
    ``some_sink.update(chunk)`` read exactly like ``digest.update(chunk)``.
    Those three gaps are now closed by tracking the chunk name itself:

    * every appearance of the bound chunk name must be a direct argument to a
      whitelisted call, and nothing else --- not a return value, not an
      assignment source, not an iteration subject;
    * ``global`` and ``nonlocal`` are refused outright, since either would let
      the name escape;
    * the receiver of an ``update`` call must be a local name assigned from
      ``hashlib.sha256()`` in this same function.

    This is a syntactic analysis of one small function, not a proof about the
    running process. Audit E (E-20) was right that the previous version of this
    sentence --- "no path in *this source* moves object bytes anywhere but into
    a digest" --- was false while eight module-scope shapes could redirect the
    handler or the whitelisted names. What it establishes now, stated at its
    actual strength: within this source file, the handler name is bound exactly
    once by a plain ``def``, the whitelisted call names are not rebound by any
    syntactic binding construct at either scope, no reflective rebinding form
    appears, and in the resulting body every appearance of the chunk name is a
    direct argument to a whitelisted call whose ``update`` receiver came from
    ``hashlib.sha256()``.

    It does not establish anything about the Azure SDK that produces the chunks,
    the standard library, or the base image, none of which is parsed; and it
    cannot see a rebinding performed by a module that imports this one.

    Returns the number of calls inspected.
    """

    import ast

    path = Path(__file__).resolve() if source_path is None else Path(source_path)
    tree = ast.parse(path.read_text(encoding="utf-8"))

    # Audits E (E-19) and F both found, independently, that nothing bound the
    # name `stream_object_digest` to the function this check analyses. Three
    # shapes passed while shipping every chunk to a module global: a decorator;
    # `stream_object_digest = _tap(stream_object_digest)` after the def, with no
    # decorator syntax at all; and two definitions of the name, because the scan
    # below takes the *first* and Python binds the *last*.
    #
    # Audit E (E-20) then defeated the fix for that: the module scan was written
    # by hand with four node types and no recursion, while `_bindings_in` --- a
    # complete recursive enumerator --- sat one function away, used only on the
    # handler. Tuple targets, `for` targets, `with` targets, `globals()[...]`
    # and `setattr(sys.modules[__name__], ...)` all rebound the name and passed.
    #
    # There is now one enumerator and both scopes use it, and the reflective
    # forms it cannot see are refused outright first.
    _assert_no_reflective_rebinding(tree)

    module_bindings = _bindings_in(tree, include_definitions=True)

    definitions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == BYTE_HANDLING_FUNCTION
    ]
    if not definitions:
        # The function this check exists to constrain has been renamed or
        # removed. Passing silently would be the worst outcome: the check would
        # report success while guarding nothing. This is deliberately reported
        # before the binding rules below, so that "the handler is gone" is never
        # misreported as "a name was shadowed".
        raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_HANDLER_NOT_FOUND")

    if len(definitions) > 1 or len(module_bindings.get(BYTE_HANDLING_FUNCTION, ())) > 1:
        raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_HANDLER_NAME_NOT_UNIQUE")

    # Audit E (E-20), F10/F11/F12. The shadowing rule inspected only bindings
    # *inside* the handler, so a module-level `len = _tap_len` or `hashlib = _H`
    # left the body byte-identical to the live one while every whitelisted call
    # resolved to an attacker's. The whitelist matches names, so every scope
    # that can bind those names has to be checked, not just the innermost.
    #
    # `import hashlib` is the one permitted module-level binding: it is how the
    # digest constructor is meant to arrive. Anything else --- `import hashlib
    # as h`, `from x import hashlib`, an assignment, a def --- is refused.
    for name in sorted(_DIGEST_ONLY_CALLS | {"hashlib"}):
        bound = module_bindings.get(name, ())
        if name == "hashlib":
            # The digest receiver rule requires the constructor to be reached as
            # `hashlib.sha256()`, so the module must actually bind `hashlib`,
            # and by the one form that cannot be pointed elsewhere. `import
            # hashlib as h` would leave the handler's `hashlib` unbound, and
            # `import evil as hashlib` would bind it to anything at all; both
            # mean the analysed body is not the code that runs.
            if len(bound) == 1:
                alias = bound[0]
                if (
                    isinstance(alias, ast.alias)
                    and alias.asname is None
                    and alias.name == "hashlib"
                ):
                    continue
            raise ProbeRefusal("INTERNAL_REFUSAL", "WHITELISTED_NAME_SHADOWED")
        if bound:
            raise ProbeRefusal("INTERNAL_REFUSAL", "WHITELISTED_NAME_SHADOWED")

    target = definitions[0]

    # Audit F: a decorator wraps the handler, so what executes is not the body
    # this check reads. Audit F's counterexample passed every check below while
    # the decorator retained every chunk in a module global. The body cannot be
    # analysed in isolation unless it is what runs.
    if target.decorator_list:
        raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_HANDLER_IS_DECORATED")

    for node in ast.walk(target):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_NAME_ESCAPES_HANDLER")
        # A nested function or lambda has its own scope, which this analysis
        # does not follow, and can close over the chunk.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and (
            node is not target
        ):
            raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_HANDLER_NESTS_A_SCOPE")

    bindings = _handler_bindings(target)

    # Audit F: `len = leak_and_count` inside the handler makes the whitelisted
    # `len(chunk)` exfiltrate every chunk, because the whitelist matches the
    # *name* and never establishes that it resolves to the builtin. Rebinding
    # `hashlib` does the same for the digest constructor. None of these names
    # may be bound in the handler at all.
    for name in sorted(_DIGEST_ONLY_CALLS | {"hashlib"}):
        if name in bindings:
            raise ProbeRefusal("INTERNAL_REFUSAL", "WHITELISTED_NAME_SHADOWED")

    # Names bound to a fresh hashlib digest here. Only these may receive an
    # `update` call, so a same-named sink cannot impersonate the digest.
    #
    # Audit E (E-12): matching on the attribute name alone accepted
    # `sink = exfil.sha256()`, while the docstring said the receiver must come
    # from `hashlib.sha256()`. The module is now checked, so an arbitrary object
    # offering a `sha256` method no longer qualifies. `from hashlib import
    # sha256` is deliberately still refused: it is a bare `ast.Name` call whose
    # binding this function does not follow, and refusing it is the safe
    # direction.
    digest_names: set[str] = set()
    for node in ast.walk(target):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "sha256"
            and isinstance(func.value, ast.Name)
            and func.value.id == "hashlib"
        ):
            for bound in node.targets:
                if isinstance(bound, ast.Name):
                    digest_names.add(bound.id)

    # A digest name that is later rebound is no longer the digest that was
    # constructed here. Audit F raised `digest = hashlib.sha256(); digest = sink`
    # as a bypass, and then, on closure review, showed that checking only
    # Assign/AugAssign/AnnAssign left `(digest := sink)`, `for digest in (sink,)`
    # and `digest, other = sink, 1` all passing. Every binding form is counted
    # now, so a digest name bound more than once is refused whatever the shape.
    for name in sorted(digest_names):
        if len(bindings.get(name, ())) > 1:
            raise ProbeRefusal("INTERNAL_REFUSAL", "DIGEST_NAME_REASSIGNED")

    inspected = 0
    whitelisted_argument_nodes: set[int] = set()
    for statement in target.body:
        for node in ast.walk(statement):
            if not isinstance(node, ast.Call):
                continue
            inspected += 1
            func = node.func
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
                if name == "update" and not (
                    isinstance(func.value, ast.Name)
                    and func.value.id in digest_names
                ):
                    raise ProbeRefusal("INTERNAL_REFUSAL", "UPDATE_ON_NON_DIGEST")
            else:
                raise ProbeRefusal("INTERNAL_REFUSAL", "COMPUTED_CALL_ON_BYTES")
            if name not in _DIGEST_ONLY_CALLS:
                raise ProbeRefusal("INTERNAL_REFUSAL", "NON_DIGEST_CALL_ON_BYTES")
            for argument in node.args:
                whitelisted_argument_nodes.add(id(argument))

    # A comprehension, an f-string or a subscript over the chunk would move
    # bytes somewhere this function does not return them from. Only the body is
    # scanned: `tuple[str, int]` in the signature is a type annotation, not an
    # operation on bytes.
    for statement in target.body:
        for node in ast.walk(statement):
            if isinstance(
                node,
                (
                    ast.JoinedStr,
                    ast.ListComp,
                    ast.SetComp,
                    ast.DictComp,
                    ast.GeneratorExp,
                    ast.Subscript,
                    ast.Await,
                    ast.Yield,
                    ast.YieldFrom,
                ),
            ):
                raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_DERIVATIVE_IN_HANDLER")

    _assert_chunk_name_never_escapes(target, whitelisted_argument_nodes)
    return inspected


#: The attribute call that produces the byte stream inside the job, and the
#: attribute call that produces the object it is read from. Declared as module
#: constants because :func:`assert_no_write_calls_in_source` refuses source
#: files containing bare string literals that name analysed symbols unless they
#: appear in a module-level declaration.
BYTE_SOURCE_CHUNK_CALL = "chunks"
BYTE_SOURCE_OPEN_CALL = "download_blob"


@_invariant("BYTE_SOURCE_REACHES_ONLY_THE_HANDLER")
def assert_byte_source_reaches_only_the_handler(
    source_path: Path | None = None,
) -> int:
    """Require the streamed bytes to reach the analysed handler and nothing else.

    Audit F (F-08) defeated :func:`assert_byte_handling_is_digest_only` without
    touching it. A pristine ``stream_object_digest`` was left in place, passing
    every rule; the live entrypoint was then changed to call
    ``evil_stream_object_digest`` instead. The analysed function was clean, was
    unique, was undecorated --- and was dead code. Byte handling was proved safe
    for a function that never saw a byte.

    The gap is that the earlier check reasons about a *definition* and never
    about a *call site*. So this one reasons only about call sites, and asks two
    questions of the whole module:

    1. Every ``.chunks()`` call --- the expression that yields object bytes ---
       must appear directly as an argument to a call of
       :data:`BYTE_HANDLING_FUNCTION` by that exact name. A chunk iterator
       handed to anything else, stored in a variable, or wrapped in a
       comprehension is refused, because from that point the bytes are outside
       the analysed body.

    2. Every name bound to a ``.download_blob()`` call may be used only as the
       receiver of ``.chunks()``. Otherwise ``evil(stream)`` reaches the same
       bytes one step earlier.

    And at least one such call site must exist: a module where the byte source
    has been renamed away would otherwise pass by having nothing to check, which
    is the failure mode this function was written to close.

    Returns the number of call sites verified.
    """

    import ast

    path = Path(__file__).resolve() if source_path is None else Path(source_path)
    tree = ast.parse(path.read_text(encoding="utf-8"))

    handed_to_handler: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == BYTE_HANDLING_FUNCTION):
            continue
        for argument in node.args:
            handed_to_handler.add(id(argument))

    verified = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == BYTE_SOURCE_CHUNK_CALL):
            continue
        if id(node) not in handed_to_handler:
            raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_SOURCE_BYPASSES_HANDLER")
        verified += 1

    if not verified:
        raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_SOURCE_NOT_FOUND")

    stream_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        called = node.value.func
        if not (
            isinstance(called, ast.Attribute) and called.attr == BYTE_SOURCE_OPEN_CALL
        ):
            continue
        for bound in node.targets:
            if isinstance(bound, ast.Name):
                stream_names.add(bound.id)
            else:
                raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_SOURCE_BINDING_UNREADABLE")

    if not stream_names:
        raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_SOURCE_NOT_FOUND")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Name) or node.id not in stream_names:
            continue
        if isinstance(node.ctx, ast.Store):
            continue
        parent = _parent_of(tree, node)
        if not (
            isinstance(parent, ast.Attribute)
            and parent.attr == BYTE_SOURCE_CHUNK_CALL
        ):
            raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_SOURCE_ESCAPES")

    return verified


def _parent_of(tree: Any, target: Any) -> Any:
    """The node directly containing ``target``, or None.

    ``ast`` does not record parents, and this check needs to know what a name is
    being used *for*. Walking once per lookup is quadratic in principle and
    irrelevant in practice: the module has a few thousand nodes and this runs
    once per stream-name reference during preflight.
    """

    import ast

    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            if child is target:
                return node
    return None


def _bindings_in(root: Any, *, include_definitions: bool = False) -> dict[str, list[Any]]:
    """Every name bound anywhere under ``root``, by every binding construct.

    Audit F's closure review defeated a rebinding rule that inspected only
    ``Assign``, ``AugAssign`` and ``AnnAssign``: ``(digest := sink)``,
    ``for digest in (sink,)`` and ``digest, other = sink, 1`` each rebound the
    digest and passed. Enumerating binding *forms* one at a time loses that
    race, so this collects them all and the callers ask questions of the result.

    Audit E (E-20) then showed the lesson had been applied in only one place.
    This enumerator was called on the handler, while the module-level scan that
    decides *which* handler to analyse was written separately by hand with four
    node types and no recursion --- so ``stream_object_digest, _spare = ...``,
    ``for stream_object_digest in ...``, ``with ... as stream_object_digest``,
    ``globals()[...] = ...`` and ``setattr(sys.modules[__name__], ...)`` all
    rebound the name and passed. Audit E also found ``match _leak: case len:``,
    a capture pattern this enumerator did not model, shadowing ``len`` inside
    the analysed body.

    So there is now one enumerator and both scopes use it. ``root`` may be a
    function or a whole module; ``include_definitions`` additionally records
    ``def``, ``async def`` and ``class`` statements, which bind their names.

    What this establishes is bounded and worth stating exactly: a name absent
    from this mapping is not bound by any *syntactic* binding construct under
    ``root``. It is not a guarantee that the name resolves to the builtin at
    runtime --- an importing module can still rebind it from outside, which no
    analysis of this source can see.
    """

    import ast

    bindings: dict[str, list[Any]] = {}

    def record(node: Any) -> None:
        if isinstance(node, ast.Name):
            bindings.setdefault(node.id, []).append(node)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for element in node.elts:
                record(element)
        elif isinstance(node, ast.Starred):
            record(node.value)

    def record_arguments(arguments: Any) -> None:
        for argument in (
            list(arguments.posonlyargs)
            + list(arguments.args)
            + list(arguments.kwonlyargs)
            + [arguments.vararg, arguments.kwarg]
        ):
            if argument is not None:
                bindings.setdefault(argument.arg, []).append(argument)

    if isinstance(root, (ast.FunctionDef, ast.AsyncFunctionDef)):
        record_arguments(root.args)

    for node in ast.walk(root):
        if isinstance(node, ast.Assign):
            for element in node.targets:
                record(element)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            record(node.target)
        elif isinstance(node, ast.NamedExpr):
            record(node.target)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            record(node.target)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    record(item.optional_vars)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                bindings.setdefault(node.name, []).append(node)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                bindings.setdefault(bound, []).append(alias)
        elif isinstance(node, ast.comprehension):
            record(node.target)
        # Audit E (E-20), M1. `case len:` is a capture pattern: it binds `len`
        # to the subject. `case [*rest]` and `case {**rest}` bind too. These are
        # binding constructs like any other and were missing.
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)):
            if node.name:
                bindings.setdefault(node.name, []).append(node)
        elif isinstance(node, ast.MatchMapping):
            if node.rest:
                bindings.setdefault(node.rest, []).append(node)
        elif include_definitions and isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            bindings.setdefault(node.name, []).append(node)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                record_arguments(node.args)
        elif include_definitions and isinstance(node, ast.Lambda):
            record_arguments(node.args)

    return bindings


def _handler_bindings(target: Any) -> dict[str, list[Any]]:
    """Every name bound inside the handler. See :func:`_bindings_in`."""

    return _bindings_in(target)


def _assert_no_reflective_rebinding(tree: Any) -> None:
    """Refuse source that can rebind a module global without an assignment.

    Audit E (E-20) rebound the byte handler two ways that no assignment-target
    scan can see, because neither is an assignment: ``globals()['name'] = ...``
    is a subscript store on a dict, and ``setattr(sys.modules[__name__], ...)``
    is an ordinary call. Both replaced the analysed function with a wrapper that
    retained every chunk, and both passed.

    A syntactic binding scan is only meaningful if the source cannot bind names
    non-syntactically, so these forms are refused outright in first-party
    in-job source. ``globals()`` remains readable --- the reachability check in
    this module uses it --- but it may not be a store target.
    """

    import ast

    reflective = set(FORBIDDEN_REFLECTIVE_MUTATION) | set(FORBIDDEN_DYNAMIC_ACCESS)
    namespace_stores = set(FORBIDDEN_NAMESPACE_STORES)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in reflective:
                raise ProbeRefusal("INTERNAL_REFUSAL", "REFLECTIVE_REBINDING")

        targets: list[Any] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]

        for target in targets:
            if isinstance(target, ast.Subscript):
                base = target.value
                if isinstance(base, ast.Call) and isinstance(base.func, ast.Name):
                    if base.func.id in namespace_stores:
                        raise ProbeRefusal(
                            "INTERNAL_REFUSAL", "REFLECTIVE_REBINDING"
                        )
            # `hashlib.sha256 = _fake` makes the whitelisted constructor return
            # an attacker object. Audit E (F11/F12).
            if isinstance(target, ast.Attribute):
                if target.attr in _DIGEST_ONLY_CALLS:
                    raise ProbeRefusal("INTERNAL_REFUSAL", "WHITELISTED_NAME_SHADOWED")


def _assert_chunk_name_never_escapes(
    target: Any, whitelisted_argument_nodes: set[int]
) -> None:
    """Every use of the chunk name must be an argument to a whitelisted call.

    Audit E (E-02). The chunk is the loop variable of the ``for`` over the
    handler's only parameter. Once that name is known, an assignment, a return,
    a further iteration or any other read of it is a path by which object bytes
    could leave the digest, and none of those is a call.

    Audit E (E-12) then showed that tracking the loop variable alone was not
    enough: ``return digest.hexdigest(), total, chunks`` passed, because
    ``chunks`` --- the *parameter* carrying the byte stream --- was never in the
    tracked set. The parameter is now tracked too, and may appear only as the
    thing being iterated. That is the one use which does not move bytes
    anywhere: it hands them to the loop that feeds the digest.
    """

    import ast

    parameters = [argument.arg for argument in target.args.args]
    chunk_names: set[str] = set()
    loop_target_nodes: set[int] = set()
    permitted_parameter_nodes: set[int] = set()
    for node in ast.walk(target):
        if not isinstance(node, ast.For):
            continue
        iterated = node.iter
        if isinstance(iterated, ast.Name) and iterated.id in parameters:
            if not isinstance(node.target, ast.Name):
                raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_LOOP_TARGET_NOT_A_NAME")
            chunk_names.add(node.target.id)
            loop_target_nodes.add(id(node.target))
            permitted_parameter_nodes.add(id(iterated))

    if not chunk_names:
        # The handler no longer iterates its input. Either it accumulates, or
        # the shape changed; both invalidate this analysis, so refuse rather
        # than report success over a function this check no longer understands.
        raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_CHUNK_BINDING_NOT_FOUND")

    tracked = chunk_names | set(parameters)
    for node in ast.walk(target):
        if not isinstance(node, ast.Name) or node.id not in tracked:
            continue
        if id(node) in loop_target_nodes or id(node) in permitted_parameter_nodes:
            continue
        if id(node) not in whitelisted_argument_nodes:
            raise ProbeRefusal("INTERNAL_REFUSAL", "BYTE_NAME_USED_OUTSIDE_DIGEST")


#: Every first-party Python source file that executes inside the access-gate
#: job. Audit C (C-14): the AST check analysed only the probe while its
#: docstring claimed to cover "the entire first-party source executed by the
#: gate". The receipt validator also runs in-job --- the probe imports it to
#: validate the receipt before printing it --- and was outside the check. It is
#: clean, so the omission was a scope-claim defect rather than a hole, but a
#: claim that outruns its evidence is exactly what this project treats as equal
#: in severity to a functional bug.
IN_JOB_FIRST_PARTY_SOURCES: tuple[str, ...] = (
    "phase1_2h_r1_private_source_probe.py",
    "phase1_2h_r1_receipt_validator.py",
)


@_invariant("NO_WRITE_CALL_IN_FIRST_PARTY_SOURCE")
def assert_no_write_calls_in_first_party_source() -> int:
    """Run the write-call analysis over every in-job first-party source file.

    Returns the total number of nodes inspected across all of them. A missing
    file is a refusal rather than a skip: the check must not report success for
    a file it could not read.
    """

    here = Path(__file__).resolve().parent
    inspected = 0
    for name in IN_JOB_FIRST_PARTY_SOURCES:
        path = here / name
        if not path.is_file():
            raise ProbeRefusal("INTERNAL_REFUSAL", "FIRST_PARTY_SOURCE_MISSING")
        inspected += assert_no_write_calls_in_source(path)
    return inspected


@_invariant("NO_VERBOSE_SDK_LOGGING")
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


@_invariant("ENDPOINT_PRIVATE_AND_RESOLVED")
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


@_invariant("IDENTITY_IS_DESIGNATED_MANAGED_IDENTITY")
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


@_invariant("MEMBERSHIP_MATCHES_PUBLIC_ANCHOR")
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


@_invariant("BYTES_MATCH_COMMITTED_DIGESTS")
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
    invariants_evaluated: list[str] | None = None,
    exit_status: str = "PASS",
    reason_code: str = "OK",
    invariants_failed: list[str] | None = None,
) -> dict[str, Any]:
    binding = record["expected_evidence_binding"]
    streamed = streaming_block["objects_streamed"]
    verdict: dict[str, Any] = {
        "access_gate_passed": exit_status == "PASS",
        "invariants_checked": invariants_checked,
        "invariants_failed": invariants_failed or [],
    }
    # Present only when the run actually recorded which invariants held. An
    # empty list would assert that zero invariants were evaluated, which is a
    # different and false claim from "this build did not track them", and it
    # would contradict a positive ``invariants_checked``.
    if invariants_evaluated:
        verdict["invariants_evaluated"] = sorted(invariants_evaluated)
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
        "verdict": verdict,
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
        assert_no_write_calls_in_first_party_source()
        assert_byte_handling_is_digest_only()
        assert_byte_source_reaches_only_the_handler()
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
        invariants_checked=len(INVARIANTS_EVALUATED),
        invariants_evaluated=sorted(INVARIANTS_EVALUATED),
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
