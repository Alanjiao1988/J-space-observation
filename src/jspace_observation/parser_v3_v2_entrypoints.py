"""Fail-closed production entrypoints, one per role.

Section 5.2 requires small, noninteractive, fail-closed entrypoints for the
exact role matrix, and requires that the *deployed* path be the constrained
one: "Tests must mutate the configured command, module binding, role, identity,
and lane to prove that the deployed path---not merely a similarly named
function---is constrained."

That sentence is the whole design brief. Two things follow from it.

First, there is exactly one guarded prologue, :func:`_guarded`, and every
entrypoint goes through it. A per-role copy of the checks would let one role
drift, and the role that drifts is the one nobody re-reads.

Second, the container command is not a string that happens to resemble a
function name. :data:`ENTRYPOINTS` maps each registered command to the actual
callable, :func:`resolve_entrypoint` is the only way to get from one to the
other, and :func:`preflight` reaches the role's checks through the same table.
So the command the IaC configures, the function the tests exercise, and the
boundary the container enforces are bound to the same object, and a test can
prove it by substituting any of them and observing a refusal.

What an entrypoint deliberately does not do
===========================================

It does not fetch its own payload from the network. Storage and identity
plumbing belong to the Phase B boundary; an entrypoint that both authorised
itself and fetched its bytes could not be tested for the authorisation step
without also standing up the storage. Here the payload arrives as an argument,
the entrypoint refuses it unless every lane, identity, schema and isolation
check has already passed, and the boundary supplies the bytes.

That is why the registered command dispatches the registered role callable in a
preflight context. The callable executes its own guarded prologue and is stopped
at the boundary immediately after the last guard, before it can inspect an inert
payload. The command then exits :data:`PREFLIGHT_WITHOUT_PAYLOAD`. Thus the
command the freeze binds demonstrably reaches the exact callable and guard path
the private invocation uses without pretending that a payload-free canary did
scientific work.
"""

from __future__ import annotations

import importlib.util
import hashlib
import inspect
import json
import os
import re
import sys
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


def _load_sibling(name: str) -> Any:
    """Load a sibling module by path, never through the package.

    ``jspace_observation/__init__.py`` eagerly imports ``model_loader`` and
    ``eval_parsing``, so *any* ``import jspace_observation.X`` puts parser code
    into the process. An entrypoint that reached its dependencies that way
    could never pass its own isolation check on a real container, which would
    make the check decoration rather than control. Loading by path keeps the
    deployed process genuinely parser-free.

    The resolution is deliberately unconditional rather than "reuse the package
    copy if one happens to be imported": conditional resolution would make the
    identity of these modules depend on import order, and import-order
    dependence is a defect this repository has already paid for once.
    """
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {name} without the package")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lifecycle = _load_sibling("parser_v3_v2_lifecycle")
construction = _load_sibling("parser_v3_v2_construction")
schemas = _load_sibling("parser_v3_v2_schemas")
evaluation = _load_sibling("parser_v3_v2_evaluation")

__all__ = [
    "EntrypointError",
    "RoleConfig",
    "AccessLog",
    "ROLE_IDENTITY_NAMES",
    "REGISTERED_ENDPOINTS",
    "REGISTERED_CONTAINERS",
    "REGISTERED_PREFIXES",
    "ROLE_SCHEMAS",
    "READ_CONTAINERS",
    "FORBIDDEN_CREDENTIAL_MARKERS",
    "REGISTERED_ENVIRONMENT_NAMES",
    "CONFIG_DIGEST_SCHEMA_VERSION",
    "CONFIG_DIGEST_FIELDS",
    "PREFLIGHT_ENVIRONMENT_NAMES",
    "PREFLIGHT_WITHOUT_PAYLOAD",
    "ENTRYPOINTS",
    "ENTRYPOINT_NAMES",
    "CONTAINER_ENTRYPOINT_PATH",
    "resolve_entrypoint",
    "entrypoint_call_graph",
    "assert_entrypoint_is_guarded",
    "assert_container_command_is_registered",
    "compute_config_digest",
    "compute_role_config_digests",
    "export_role_matrix",
    "preflight",
    "main",
]


class EntrypointError(Exception):
    """Raised when an entrypoint refuses to run."""


_GUID = re.compile(r"\A[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z")
_IMAGE_DIGEST = re.compile(r"\Asha256:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")


# ---------------------------------------------------------------------------
# closed registries
# ---------------------------------------------------------------------------

#: The exact user-assigned managed identity name each role runs as.
#:
#: Names rather than object ids, because the identities do not exist until the
#: Phase B deployment creates them and a placeholder GUID bound here would be a
#: fabricated fact. The runtime still has to supply a GUID-shaped client id, and
#: it still has to be the one the deployment recorded for this role's name.
ROLE_IDENTITY_NAMES: Mapping[str, str] = {
    "source_custodian": "uami-jspace-source-custodian",
    "normalizer": "uami-jspace-normalizer",
    "reviewer_a": "uami-jspace-reviewer-a",
    "reviewer_b": "uami-jspace-reviewer-b",
    "broker": "uami-jspace-broker",
    "arbiter": "uami-jspace-arbiter",
    "selector": "uami-jspace-selector",
    "private_set_auditor": "uami-jspace-private-set-auditor",
    "facts_compiler": "uami-jspace-facts-compiler",
    "seal_custodian": "uami-jspace-seal-custodian",
    "preregistration_compiler": "uami-jspace-preregistration-compiler",
    "stage_p": "uami-jspace-stage-p",
    "prediction_sealer": "uami-jspace-prediction-sealer",
    "stage_e": "uami-jspace-stage-e",
    "receipt_exporter": "uami-jspace-receipt-exporter",
}

#: The only private endpoints a role may address. A public endpoint or a direct
#: IP is refused by absence.
REGISTERED_ENDPOINTS: frozenset[str] = frozenset(
    {
        "stjspacefiles0709085305.privatelink.blob.core.windows.net",
        "acrjspaceruntime.privatelink.azurecr.io",
    }
)

#: One container per role. Sharing a container between a reader and a writer of
#: the same class is how a role acquires a lane it was never granted.
REGISTERED_CONTAINERS: Mapping[str, str] = {
    "source_custodian": "v2-private-staging",
    "normalizer": "v2-private-staging",
    "reviewer_a": "v2-review",
    "reviewer_b": "v2-review",
    "broker": "v2-review",
    "arbiter": "v2-arbitration",
    "selector": "v2-selection",
    "private_set_auditor": "v2-audit",
    "facts_compiler": "v2-facts",
    "seal_custodian": "v2-sealed",
    "preregistration_compiler": "v2-preregistration",
    "stage_p": "v2-predictions",
    "prediction_sealer": "v2-predictions",
    "stage_e": "v2-formal-result",
    "receipt_exporter": "v2-public-receipts",
}

#: One write prefix per role, never shared and never reused.
REGISTERED_PREFIXES: Mapping[str, str] = {
    "source_custodian": "staging/source/",
    "normalizer": "staging/normalized/",
    "reviewer_a": "review/a/",
    "reviewer_b": "review/b/",
    "broker": "review/disagreements/",
    "arbiter": "arbitration/records/",
    "selector": "selection/final-candidate/",
    "private_set_auditor": "audit/findings/",
    "facts_compiler": "facts/set/",
    "seal_custodian": "sealed/v2/",
    "preregistration_compiler": "preregistration/lock/",
    "stage_p": "predictions/members/",
    "prediction_sealer": "predictions/manifest/",
    "stage_e": "formal-result/",
    "receipt_exporter": "public/receipts/",
}

#: The schema ids each role is permitted to read or write. A role that names a
#: schema outside this list is refused, which is what makes "schema accepted by
#: the tests but not invoked by the live entrypoint" a detectable substitution.
ROLE_SCHEMAS: Mapping[str, tuple[str, ...]] = {
    "source_custodian": ("phase1-parser-v3-v2-admission-record/v1",),
    "normalizer": ("phase1-parser-v3-v2-admission-record/v1",),
    "reviewer_a": (
        "phase1-parser-v3-v2-blinded-case-packet/v1",
        "phase1-parser-v3-v2-reviewer-decision/v1",
    ),
    "reviewer_b": (
        "phase1-parser-v3-v2-blinded-case-packet/v1",
        "phase1-parser-v3-v2-reviewer-decision/v1",
    ),
    "broker": (
        "phase1-parser-v3-v2-reviewer-decision/v1",
        "phase1-parser-v3-v2-disagreement-packet/v1",
    ),
    "arbiter": (
        "phase1-parser-v3-v2-disagreement-packet/v1",
        "phase1-parser-v3-v2-arbitration-result/v1",
    ),
    "selector": (
        "phase1-parser-v3-v2-admission-record/v1",
        "phase1-parser-v3-v2-quarantine-record/v1",
        "phase1-parser-v3-v2-replacement-record/v1",
    ),
    "private_set_auditor": ("phase1-parser-v3-v2-admission-record/v1",),
    "facts_compiler": (
        "phase1-parser-v3-v2-admission-record/v1",
        "phase1-parser-v3-v2-set-facts-projection/v1",
    ),
    "seal_custodian": (
        "phase1-parser-v3-v2-construction-plan/v1",
        "phase1-parser-v3-v2-planned-seal-members/v1",
        "phase1-parser-v3-v2-terminal-manifest/v1",
        "phase1-parser-v3-v2-authenticated-listing-projection/v1",
        "phase1-parser-v3-v2-listing-witness-receipt/v1",
        "phase1-parser-v3-v2-final-contract-receipt/v1",
    ),
    "preregistration_compiler": ("phase1-parser-v3-v2-preregistration-lock/v1",),
    "stage_p": (
        "phase1-parser-v3-v2-prediction-member/v1",
        "phase1-parser-v3-v2-prediction-manifest/v1",
    ),
    "prediction_sealer": (
        "phase1-parser-v3-v2-prediction-manifest/v1",
        "phase1-parser-v3-v2-prediction-receipt/v1",
    ),
    "stage_e": (
        "phase1-parser-v3-v2-prediction-receipt/v1",
        "phase1-parser-v3-v2-stage-e-result/v1",
    ),
    "receipt_exporter": (
        "phase1-parser-v3-v2-public-receipt/v1",
        "phase1-parser-v3-v2-terminal-state-receipt/v1",
    ),
}

#: Read class -> the container that holds it.
#:
#: Closed and exhaustive: a control asserts that every read class appearing in
#: any lane has an entry here. Without that, a class with no mapping would
#: silently grant nothing, and a role that reads nothing looks identical to a
#: role whose lane was never wired up.
READ_CONTAINERS: Mapping[str, str] = {
    "retired_v1_source": "v1-retired-source",
    "v2_private_staging": "v2-private-staging",
    "normalized_candidates": "v2-private-staging",
    "blinded_case_packets": "v2-review",
    "reviewer_a_decisions": "v2-review",
    "reviewer_b_decisions": "v2-review",
    "disagreement_packets": "v2-review",
    "arbitration_records": "v2-arbitration",
    "final_candidate": "v2-selection",
    "provenance": "v2-selection",
    "finalized_immutable_bytes": "v2-selection",
    "set_facts": "v2-facts",
    "seal_plan": "v2-facts",
    "listing_witness": "v2-sealed",
    "sealed_v2_inputs": "v2-sealed",
    "frozen_parser_assets": "v2-parser-assets",
    "prediction_members": "v2-predictions",
    "sealed_predictions": "v2-predictions",
    "scoring_labels": "v2-labels",
    "policy": "v2-policy",
    "final_contract": "v2-policy",
    "content_free_receipts": "v2-receipts",
}

#: Environment fragments that indicate a credential other than the role's own
#: managed identity. Matched case-insensitively as substrings: the fallback that
#: matters is the one nobody spelled the way the allowlist expected.
FORBIDDEN_CREDENTIAL_MARKERS: tuple[str, ...] = (
    "client_secret",
    "clientsecret",
    "account_key",
    "accountkey",
    "sas_token",
    "sastoken",
    "sas_signature",
    "connection_string",
    "connectionstring",
    "password",
    "shared_key",
    "sharedkey",
    "certificate_password",
    "federated_token_file",
    "azure_client_certificate",
    "azure_tenant_id_override",
)

#: The complete set of environment-variable names a role may hold.
#:
#: This is closure, not a larger credential denylist. The role configuration,
#: the Container Apps managed-identity endpoint, and a small set of non-secret
#: process settings are admitted; every other name is refused. The explicit
#: credential markers above remain only to produce a precise error for a known
#: mechanism before the closure check reports the generic unknown name.
REGISTERED_ENVIRONMENT_NAMES: frozenset[str] = frozenset(
    {
        # The complete role configuration.
        "AZURE_CLIENT_ID",
        "JSPACE_ROLE",
        "JSPACE_UAMI_NAME",
        "JSPACE_ENDPOINT",
        "JSPACE_CONTAINER",
        "JSPACE_PREFIX",
        "JSPACE_SCHEMA_IDS",
        "JSPACE_SCHEMA_REGISTRY_DIGEST",
        "JSPACE_IMAGE_DIGEST",
        "JSPACE_CONFIG_DIGEST",
        # The managed-identity endpoint Container Apps injects. IDENTITY_HEADER
        # is part of that one registered mechanism, not a second credential.
        "IDENTITY_ENDPOINT",
        "IDENTITY_HEADER",
        # Closed, non-secret process settings used by the hardened role images.
        "HOME",
        "HOSTNAME",
        "LANG",
        "LC_ALL",
        "PATH",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONHASHSEED",
        "PYTHONPATH",
        "PYTHONUNBUFFERED",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "TZ",
    }
)

#: Roles that must never hold parser code. Everything that touches candidate
#: material during construction, review or sealing, plus Stage E.
PARSER_FREE_ROLES: frozenset[str] = frozenset(
    {
        "source_custodian",
        "normalizer",
        "reviewer_a",
        "reviewer_b",
        "broker",
        "arbiter",
        "selector",
        "private_set_auditor",
        "facts_compiler",
        "seal_custodian",
        "preregistration_compiler",
        "prediction_sealer",
        "stage_e",
        "receipt_exporter",
    }
)


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoleConfig:
    """Everything a role is allowed to be, fixed before it runs."""

    role: str
    uami_name: str
    uami_client_id: str
    private_endpoint: str
    container: str
    prefix: str
    schema_ids: tuple[str, ...]
    schema_registry_digest: str
    image_digest: str
    config_digest: str


CONFIG_DIGEST_SCHEMA_VERSION = "phase1-parser-v3-v2-role-config/v1"

#: Fixed order for the JSON vector hashed before deployment and at runtime.
#:
#: A JSON object is unordered by definition, even if two implementations happen
#: to preserve insertion order today. An ordered vector lets the public
#: prebinding step and the runtime derive the same byte string without relying
#: on an object-ordering accident.
CONFIG_DIGEST_FIELDS: tuple[str, ...] = (
    "container",
    "image_digest",
    "prefix",
    "private_endpoint",
    "role",
    "schema_ids",
    "schema_registry_digest",
    "uami_name",
)


def _hash_config_values(values: Mapping[str, Any]) -> str:
    if set(values) != set(CONFIG_DIGEST_FIELDS):
        raise EntrypointError(
            "configuration digest values do not exactly match the registered fields"
        )
    payload = [
        CONFIG_DIGEST_SCHEMA_VERSION,
        *[[field, values[field]] for field in CONFIG_DIGEST_FIELDS],
    ]
    serialized = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_config_digest(config: RoleConfig) -> str:
    """Derive the digest that binds a configuration to its own content.

    Every field that decides what the role *is* goes in, together with the
    digest of the schema registry the role will validate against. Public audit
    finding B-02 observed that ``config_digest`` was only checked for SHA-256
    syntax; a digest nobody recomputes is decoration. Recomputing here means
    swapping the image, endpoint, container, schema set, or registered identity
    name changes the digest and stops the run.

    The UAMI client ID is deliberately not in this pre-bound digest: Azure
    creates that value during deployment, and Bicep cannot SHA-256 a
    deployment-time resource property. Finding B-03 is closed at the IaC layer
    instead: the job's assigned identity, ``uami_name`` and ``AZURE_CLIENT_ID``
    are all derived from the same managed-identity resource, and
    :func:`assert_identity` verifies that runtime value before payload access.
    """
    values: Mapping[str, Any] = {
        "container": config.container,
        "image_digest": config.image_digest,
        "prefix": config.prefix,
        "private_endpoint": config.private_endpoint,
        "role": config.role,
        "schema_ids": list(config.schema_ids),
        "schema_registry_digest": config.schema_registry_digest,
        "uami_name": config.uami_name,
    }
    return _hash_config_values(values)


def compute_role_config_digests(
    *,
    role_image_digests: Mapping[str, str],
    private_endpoint: str,
) -> Mapping[str, str]:
    """Produce the complete predeployment digest map required by Bicep."""
    expected_roles = set(ROLE_IDENTITY_NAMES)
    supplied_roles = set(role_image_digests)
    if supplied_roles != expected_roles:
        raise EntrypointError(
            "role_image_digests must name exactly every registered role; "
            f"missing={sorted(expected_roles - supplied_roles)}, "
            f"extra={sorted(supplied_roles - expected_roles)}"
        )
    if private_endpoint not in REGISTERED_ENDPOINTS:
        raise EntrypointError(
            f"private endpoint {private_endpoint!r} is not registered"
        )

    digests: dict[str, str] = {}
    for role in sorted(expected_roles):
        image_digest = role_image_digests[role]
        if not _IMAGE_DIGEST.match(image_digest or ""):
            raise EntrypointError(
                f"role {role!r} has no immutable sha256 image digest"
            )
        digests[role] = _hash_config_values(
            {
                "container": REGISTERED_CONTAINERS[role],
                "image_digest": image_digest,
                "prefix": REGISTERED_PREFIXES[role],
                "private_endpoint": private_endpoint,
                "role": role,
                "schema_ids": list(ROLE_SCHEMAS[role]),
                "schema_registry_digest": schemas.REGISTRY_DIGEST,
                "uami_name": ROLE_IDENTITY_NAMES[role],
            }
        )
    return digests


def assert_config_registered(config: RoleConfig) -> None:
    """Refuse a configuration that is not exactly the registered one.

    Every field is compared against a closed table rather than pattern-matched,
    because "looks like a private endpoint" is satisfied by an attacker-supplied
    hostname and "is the registered private endpoint" is not.
    """
    if not isinstance(config, RoleConfig):
        raise EntrypointError("configuration must be a RoleConfig")
    if config.role not in lifecycle.ROLE_LANES:
        raise EntrypointError(f"{config.role!r} is not a registered role")
    expected_identity = ROLE_IDENTITY_NAMES.get(config.role)
    if config.uami_name != expected_identity:
        raise EntrypointError(
            f"role {config.role} must run as {expected_identity!r}, not {config.uami_name!r}"
        )
    if not _GUID.match(config.uami_client_id or ""):
        raise EntrypointError("uami_client_id must be an explicit GUID client id")
    if config.private_endpoint not in REGISTERED_ENDPOINTS:
        raise EntrypointError(
            "endpoint is not one of the registered private endpoints; a public "
            "endpoint or a direct IP is refused by absence"
        )
    if config.container != REGISTERED_CONTAINERS[config.role]:
        raise EntrypointError(f"role {config.role} may not use container {config.container!r}")
    if config.prefix != REGISTERED_PREFIXES[config.role]:
        raise EntrypointError(f"role {config.role} may not use prefix {config.prefix!r}")
    if tuple(config.schema_ids) != ROLE_SCHEMAS[config.role]:
        raise EntrypointError(
            f"role {config.role} may only bind {list(ROLE_SCHEMAS[config.role])}"
        )
    schemas.assert_all_ids_reachable(config.schema_ids)
    if not _SHA256.match(config.schema_registry_digest or ""):
        raise EntrypointError("schema_registry_digest must be a SHA-256 hex digest")
    if config.schema_registry_digest != schemas.REGISTRY_DIGEST:
        raise EntrypointError(
            "schema_registry_digest does not identify the registry loaded by this role"
        )
    if not _IMAGE_DIGEST.match(config.image_digest or ""):
        raise EntrypointError("image_digest must be an explicit sha256: digest, not a tag")
    if not _SHA256.match(config.config_digest or ""):
        raise EntrypointError("config_digest must be a SHA-256 hex digest")
    lifecycle.assert_schema_binding(
        registry_digests=schemas.SCHEMA_DIGESTS,
        registry_digest=schemas.REGISTRY_DIGEST,
    )
    expected_digest = compute_config_digest(config)
    if config.config_digest != expected_digest:
        raise EntrypointError(
            "config_digest does not match the configuration it claims to bind: "
            f"expected {expected_digest}, got {config.config_digest}"
        )


def assert_identity(config: RoleConfig, environment: Mapping[str, str]) -> None:
    """Require the process to hold exactly this role's managed identity."""
    supplied = environment.get("AZURE_CLIENT_ID")
    if supplied is None:
        raise EntrypointError("AZURE_CLIENT_ID is not set; ambient identity is refused")
    if supplied != config.uami_client_id:
        raise EntrypointError("the process identity is not the role's registered identity")


def assert_no_ambient_credentials(environment: Mapping[str, str]) -> None:
    """Refuse any credential material other than the managed identity.

    A key, SAS, connection string or client secret in the environment means the
    role can reach storage without its lane being checked at all, so the lane
    matrix stops being the access control and becomes documentation.

    The named markers run first so that a recognised mechanism is reported as
    itself, then the explicit ambient-credential opt-in, and finally a complete
    allowlist over environment-variable names. Public audit finding B-04 was
    specifically a denylist failure: another denylist with broader fragments
    would only move the hole. Under closure, ``FOO_TOKEN`` is refused because it
    was never registered, but so is ``UNIMAGINED_CREDENTIAL_CARRIER`` even if its
    name contains no marker at all.
    """
    hits = sorted(
        {
            key
            for key in environment
            for marker in FORBIDDEN_CREDENTIAL_MARKERS
            if marker in key.casefold()
        }
    )
    if hits:
        raise EntrypointError(f"ambient credential material present in the environment: {hits}")
    if environment.get("AZURE_USE_AMBIENT_CREDENTIAL", "").strip().lower() in {"1", "true", "yes"}:
        raise EntrypointError("ambient credential fallback is explicitly refused")
    unregistered = sorted(set(environment) - REGISTERED_ENVIRONMENT_NAMES)
    if unregistered:
        raise EntrypointError(
            "unregistered environment variable(s) present: "
            f"{unregistered}. Role environments are closed so an unanticipated "
            "name cannot become an ambient credential channel."
        )


def assert_lanes(role: str, *, reads: Sequence[str], writes: Sequence[str]) -> None:
    """Verify the role's actual lanes before any payload is touched."""
    lanes = lifecycle.ROLE_LANES.get(role)
    if lanes is None:
        raise EntrypointError(f"{role!r} is not a registered role")
    unlisted_reads = sorted(set(reads) - set(lanes["reads"]))
    if unlisted_reads:
        raise EntrypointError(f"{role} requested read class(es) outside its lane: {unlisted_reads}")
    unlisted_writes = sorted(set(writes) - set(lanes["writes"]))
    if unlisted_writes:
        raise EntrypointError(
            f"{role} requested write class(es) outside its lane: {unlisted_writes}"
        )
    if role == "stage_p":
        lifecycle.assert_stage_p_scope(reads)
    if role == "stage_e":
        lifecycle.assert_stage_e_scope(reads)
    if role != lifecycle.LABEL_READING_ROLE and "scoring_labels" in set(reads):
        raise EntrypointError(f"{role} may never read scoring labels")


def assert_import_isolation(role: str, loaded_module_names: Iterable[str]) -> None:
    """Refuse a process holding code its role must not be able to execute."""
    loaded = list(loaded_module_names)
    if role in PARSER_FREE_ROLES:
        lifecycle.assert_stage_e_import_is_parser_free(loaded)
    if role == "stage_p":
        evaluation.assert_stage_p_import_is_scorer_free(loaded)


# ---------------------------------------------------------------------------
# content-free logging
# ---------------------------------------------------------------------------


@dataclass
class AccessLog:
    """An append-only log that can only hold closed identifiers.

    Every record is validated against the access-event schema before it is
    kept, so a caller cannot log a prompt, a response, a private object name or
    an exception message through it: those fields do not exist in the schema and
    the schema is closed.
    """

    role: str
    events: list[Mapping[str, Any]] = field(default_factory=list)
    _step: int = 0

    def record(
        self,
        event_id: str,
        *,
        status: str = "ok",
        read_class: str | None = None,
        object_count: int = 0,
    ) -> Mapping[str, Any]:
        event = {
            "schema_version": "phase1-parser-v3-v2-access-event/v1",
            "event_id": event_id,
            "role": self.role,
            "status": status,
            "read_class": read_class,
            "object_count": object_count,
            "occurred_at_step": self._step,
        }
        schemas.assert_valid("phase1-parser-v3-v2-access-event/v1", event)
        self._step += 1
        self.events.append(event)
        return event

    def event_ids(self) -> tuple[str, ...]:
        return tuple(event["event_id"] for event in self.events)


class _PreflightComplete(Exception):
    """Internal signal that the registered callable reached every guard."""

    def __init__(self, log: AccessLog):
        super().__init__("registered entrypoint preflight completed")
        self.log = log


_PREFLIGHT_ACTIVE: ContextVar[bool] = ContextVar(
    "parser_v3_v2_preflight_active", default=False
)


# ---------------------------------------------------------------------------
# the single guarded prologue
# ---------------------------------------------------------------------------


def _guarded(
    config: RoleConfig,
    *,
    reads: Sequence[str],
    writes: Sequence[str],
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    log: AccessLog,
) -> None:
    """Run every precondition, in order, before any payload is touched.

    Order matters. Identity and credentials are checked before lanes, and lanes
    before imports, so that the first refusal a misconfigured deployment hits
    is the one that describes what is actually wrong rather than a downstream
    symptom of it.
    """
    if log.role != config.role:
        raise EntrypointError("the access log is bound to a different role")
    try:
        assert_config_registered(config)
        assert_identity(config, environment)
        assert_no_ambient_credentials(environment)
    except (EntrypointError, lifecycle.LifecycleError):
        log.record("identity_assertion_refused", status="refused")
        raise
    log.record("identity_assertion_passed")
    try:
        assert_lanes(config.role, reads=reads, writes=writes)
    except (EntrypointError, lifecycle.LifecycleError):
        log.record("lane_check_refused", status="refused")
        raise
    log.record("lane_check_passed")
    try:
        assert_import_isolation(config.role, loaded_module_names)
    except (lifecycle.LifecycleError, evaluation.EvaluationError):
        log.record("import_isolation_refused", status="refused")
        raise
    log.record("import_isolation_passed")
    if _PREFLIGHT_ACTIVE.get():
        log.record("entrypoint_completed", object_count=0)
        raise _PreflightComplete(log)


def _validate_each(schema_id: str, instances: Sequence[Mapping[str, Any]], log: AccessLog) -> None:
    if schema_id not in schemas.SCHEMAS:
        raise EntrypointError(f"unregistered schema id {schema_id!r}")
    try:
        for instance in instances:
            schemas.assert_valid(schema_id, instance)
    except schemas.SchemaValidationError:
        log.record("schema_validation_refused", status="refused")
        raise
    log.record("schema_validation_passed", object_count=len(instances))


# ---------------------------------------------------------------------------
# the role entrypoints
# ---------------------------------------------------------------------------


def run_source_custodian(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    admission_records: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Admit normalised source material into private staging."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=["retired_v1_source"],
        writes=["v2_private_staging"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    _validate_each("phase1-parser-v3-v2-admission-record/v1", admission_records, log)
    construction.assert_no_parser_field(list(admission_records), path="admission_records")
    log.record("entrypoint_completed", object_count=len(admission_records))
    return {"role": config.role, "accepted": len(admission_records), "log": log}


def run_normalizer(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    admission_records: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Normalise staged material without reading the retired source directly."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=["v2_private_staging"],
        writes=["normalized_candidates"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    _validate_each("phase1-parser-v3-v2-admission-record/v1", admission_records, log)
    construction.assert_no_parser_field(list(admission_records), path="admission_records")
    log.record("entrypoint_completed", object_count=len(admission_records))
    return {"role": config.role, "normalized": len(admission_records), "log": log}


def _run_reviewer(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    packets: Sequence[Mapping[str, Any]],
    decide: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> Mapping[str, Any]:
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=["blinded_case_packets"],
        writes=[f"{config.role}_decisions"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    _validate_each("phase1-parser-v3-v2-blinded-case-packet/v1", packets, log)
    decisions = []
    for packet in packets:
        construction.assert_reviewer_packet_is_blind(packet)
        decisions.append(decide(packet))
    _validate_each("phase1-parser-v3-v2-reviewer-decision/v1", decisions, log)
    log.record("entrypoint_completed", object_count=len(decisions))
    return {"role": config.role, "decisions": decisions, "log": log}


def run_reviewer_a(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    packets: Sequence[Mapping[str, Any]],
    decide: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Reviewer A. Sees only blinded packets and never reviewer B."""
    return _run_reviewer(
        config=config,
        environment=environment,
        loaded_module_names=loaded_module_names,
        packets=packets,
        decide=decide,
    )


def run_reviewer_b(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    packets: Sequence[Mapping[str, Any]],
    decide: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Reviewer B. Sees only blinded packets and never reviewer A."""
    return _run_reviewer(
        config=config,
        environment=environment,
        loaded_module_names=loaded_module_names,
        packets=packets,
        decide=decide,
    )


def run_broker(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    pairs: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Route only genuine disagreements to the arbiter."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=["reviewer_a_decisions", "reviewer_b_decisions"],
        writes=["disagreements"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    decisions = [d for pair in pairs for d in (pair["reviewer_a"], pair["reviewer_b"])]
    _validate_each("phase1-parser-v3-v2-reviewer-decision/v1", decisions, log)
    routed: list[Mapping[str, Any]] = []
    for pair in pairs:
        a, b = pair["reviewer_a"], pair["reviewer_b"]
        if construction.routes_to_arbiter(a, b):
            routed.append(
                {
                    "schema_version": "phase1-parser-v3-v2-disagreement-packet/v1",
                    "case_ref": pair["case_ref"],
                    "case_content": pair["case_content"],
                    "public_ontology_packet": pair["public_ontology_packet"],
                    "reviewer_a": a,
                    "reviewer_b": b,
                    "disagreeing_fields": list(construction.disagreeing_fields(a, b)),
                }
            )
    _validate_each("phase1-parser-v3-v2-disagreement-packet/v1", routed, log)
    construction.assert_only_disagreements_reached_arbiter(
        arbitrated_case_ids=[packet["case_ref"] for packet in routed],
        decisions_by_case={
            pair["case_ref"]: (pair["reviewer_a"], pair["reviewer_b"]) for pair in pairs
        },
    )
    log.record("entrypoint_completed", object_count=len(routed))
    return {"role": config.role, "routed": routed, "log": log}


def run_arbiter(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    packets: Sequence[Mapping[str, Any]],
    adjudicate: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    adjudication_permanently_recorded: bool = False,
) -> Mapping[str, Any]:
    """Adjudicate disagreements without seeing the retired label first."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=["disagreement_packets"],
        writes=["arbitration_records"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    _validate_each("phase1-parser-v3-v2-disagreement-packet/v1", packets, log)
    results = []
    for packet in packets:
        construction.assert_arbiter_packet_is_scoped(
            packet, adjudication_permanently_recorded=adjudication_permanently_recorded
        )
        results.append(adjudicate(packet))
    _validate_each("phase1-parser-v3-v2-arbitration-result/v1", results, log)
    log.record("entrypoint_completed", object_count=len(results))
    return {"role": config.role, "results": results, "log": log}


def run_selector(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    admitted: Sequence[Mapping[str, Any]],
    quarantined: Sequence[Mapping[str, Any]] = (),
    replacements: Sequence[Mapping[str, Any]] = (),
    replacement_batch_limit: int = 1,
) -> Mapping[str, Any]:
    """Select the final candidate set and coordinate bounded replacement."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=[
            "normalized_candidates",
            "reviewer_a_decisions",
            "reviewer_b_decisions",
            "arbitration_records",
        ],
        writes=["final_candidate", "quarantine_records", "replacement_records"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    _validate_each("phase1-parser-v3-v2-admission-record/v1", admitted, log)
    _validate_each("phase1-parser-v3-v2-quarantine-record/v1", quarantined, log)
    _validate_each("phase1-parser-v3-v2-replacement-record/v1", replacements, log)
    for record in quarantined:
        construction.assert_quarantine_reason_is_registered(record["reason"])
    for record in replacements:
        # ``batch_index`` is zero-based, so it is exactly the number of batches
        # already consumed for this slot before the one being recorded.
        construction.assert_replacement_batch_within_limit(
            slot=record["replaced_case_id"],
            batches_used=record["batch_index"],
            preregistered_batch_limit=replacement_batch_limit,
        )
    construction.assert_final_set_invariants(list(admitted))
    log.record("entrypoint_completed", object_count=len(admitted))
    return {"role": config.role, "selected": len(admitted), "log": log}


def run_private_set_auditor(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    admitted: Sequence[Mapping[str, Any]],
    external_fingerprints: Mapping[str, Mapping[str, str]] | None = None,
) -> Mapping[str, Any]:
    """Re-derive the set invariants and the collision rules independently."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=["final_candidate", "provenance"],
        writes=["audit_findings"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    _validate_each("phase1-parser-v3-v2-admission-record/v1", admitted, log)
    construction.assert_final_set_invariants(list(admitted))
    construction.assert_no_parser_field(list(admitted), path="final_candidate")
    log.record("entrypoint_completed", object_count=len(admitted))
    return {"role": config.role, "audited": len(admitted), "log": log}


def run_facts_compiler(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    admitted: Sequence[Mapping[str, Any]],
    facts: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Compile the content-free set-facts projection."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=["final_candidate"],
        writes=["set_facts"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    _validate_each("phase1-parser-v3-v2-admission-record/v1", admitted, log)
    construction.assert_final_set_invariants(list(admitted))
    _validate_each("phase1-parser-v3-v2-set-facts-projection/v1", [facts], log)
    construction.assert_no_parser_field(facts, path="set_facts")
    log.record("entrypoint_completed", object_count=1)
    return {"role": config.role, "facts": facts, "log": log}


def run_seal_custodian(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    plan: Mapping[str, Any],
    existing_objects: Sequence[str],
) -> Mapping[str, Any]:
    """Create the sealed namespace, terminal manifest last, never resuming."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=["finalized_immutable_bytes", "seal_plan"],
        writes=["v2_sealed_namespace", "listing_witness"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    _validate_each("phase1-parser-v3-v2-construction-plan/v1", [plan], log)
    lifecycle.assert_create_only_plan(
        existing_objects=existing_objects,
        planned_objects=list(plan["planned_objects"]),
        terminal_manifest=plan["terminal_manifest"],
    )
    lifecycle.assert_terminal_manifest_last(
        write_order=list(plan["write_order"]), terminal_manifest=plan["terminal_manifest"]
    )
    log.record("payload_write_created", object_count=len(plan["planned_objects"]))
    log.record("entrypoint_completed", object_count=len(plan["planned_objects"]))
    return {"role": config.role, "created": len(plan["planned_objects"]), "log": log}


def run_preregistration_compiler(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    bindings: Mapping[str, Any],
    existing_lock_digest: str | None,
) -> Mapping[str, Any]:
    """Create the preregistration lock exactly once."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=["set_facts", "listing_witness", "final_contract", "policy"],
        writes=["preregistration_lock"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    lock, digest = evaluation.create_preregistration_lock(
        bindings=bindings, existing_lock_digest=existing_lock_digest
    )
    _validate_each("phase1-parser-v3-v2-preregistration-lock/v1", [lock], log)
    log.record("entrypoint_completed", object_count=1)
    return {"role": config.role, "lock": lock, "lock_digest": digest, "log": log}


def run_stage_p(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    lock: Mapping[str, Any],
    lock_digest: str,
    state: str,
    ordinal: int,
    locked_inputs: Sequence[Mapping[str, Any]],
    parser: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Run the single Stage P pass through the real evaluation implementation."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        # Use the registered lane before touching the caller-supplied lock.
        # Reading lock[...] in this argument used to happen before _guarded,
        # so a malformed payload could execute before identity and isolation
        # were established.
        reads=list(lifecycle.ROLE_LANES[config.role]["reads"]),
        writes=["prediction_namespace"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    stream = evaluation.run_stage_p(
        lock=lock,
        lock_digest=lock_digest,
        state=state,
        ordinal=ordinal,
        locked_inputs=locked_inputs,
        parser=parser,
        loaded_module_names=loaded_module_names,
    )
    _validate_each("phase1-parser-v3-v2-prediction-manifest/v1", [stream], log)
    log.record("entrypoint_completed", object_count=len(stream["members"]))
    return {"role": config.role, "stream": stream, "log": log}


def run_prediction_sealer(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    stream: Mapping[str, Any],
    sealed_case_ids: Sequence[str],
    write_order: Sequence[str],
    terminal_manifest: str,
    existing_objects: Sequence[str],
) -> Mapping[str, Any]:
    """Seal the prediction stream create-only and completely."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=["prediction_members"],
        writes=["prediction_manifest", "prediction_witness"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    _validate_each("phase1-parser-v3-v2-prediction-manifest/v1", [stream], log)
    receipt = evaluation.seal_prediction_stream(
        stream=stream,
        sealed_case_ids=sealed_case_ids,
        write_order=write_order,
        terminal_manifest=terminal_manifest,
        existing_objects=existing_objects,
    )
    _validate_each("phase1-parser-v3-v2-prediction-receipt/v1", [receipt], log)
    log.record("entrypoint_completed", object_count=receipt["member_count"])
    return {"role": config.role, "receipt": receipt, "log": log}


def run_stage_e(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    lock: Mapping[str, Any],
    lock_digest: str,
    prediction_receipt: Mapping[str, Any],
    sealed_members: Sequence[Mapping[str, Any]],
    labels: Mapping[str, Mapping[str, Any]],
    strata: Mapping[str, str],
    existing_result_digests: Sequence[str],
    parser_v2_comparison: str = "NOT_RUN",
) -> Mapping[str, Any]:
    """Open labels once and produce the unique formal result."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        # As in Stage P, the guard is evaluated before any payload field.
        reads=list(lifecycle.ROLE_LANES[config.role]["reads"]),
        writes=["formal_result"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    _validate_each("phase1-parser-v3-v2-prediction-receipt/v1", [prediction_receipt], log)
    result = evaluation.run_stage_e(
        lock=lock,
        lock_digest=lock_digest,
        prediction_receipt=prediction_receipt,
        sealed_members=sealed_members,
        labels=labels,
        strata=strata,
        existing_result_digests=existing_result_digests,
        parser_v2_comparison=parser_v2_comparison,
        loaded_module_names=loaded_module_names,
    )
    _validate_each("phase1-parser-v3-v2-stage-e-result/v1", [result], log)
    log.record("entrypoint_completed", object_count=1)
    return {"role": config.role, "result": result, "log": log}


def run_receipt_exporter(
    *,
    config: RoleConfig,
    environment: Mapping[str, str],
    loaded_module_names: Iterable[str],
    receipt: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Export the only artifact class permitted to leave the boundary."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=["content_free_receipts"],
        writes=["public_projection"],
        environment=environment,
        loaded_module_names=loaded_module_names,
        log=log,
    )
    _validate_each("phase1-parser-v3-v2-public-receipt/v1", [receipt], log)
    construction.assert_no_parser_field(receipt, path="public_receipt")
    log.record("entrypoint_completed", object_count=1)
    return {"role": config.role, "exported": receipt, "log": log}


# ---------------------------------------------------------------------------
# the command registry
# ---------------------------------------------------------------------------

#: The path the container actually executes.
#:
#: Deliberately a file path and not ``python -m jspace_observation....``: the
#: ``-m`` form runs the package ``__init__``, which imports ``model_loader`` and
#: ``eval_parsing``, so every parser-free role would load parser code before its
#: first line ran. The command in the IaC, the command resolved here and the
#: command the tests exercise are the same tuple.
CONTAINER_ENTRYPOINT_PATH = "/app/src/jspace_observation/parser_v3_v2_entrypoints.py"


@dataclass(frozen=True)
class EntrypointSpec:
    """One deployable entrypoint: a command, a role, and the real callable."""

    name: str
    role: str
    function: Callable[..., Any]
    command: tuple[str, ...]


def _spec(name: str, role: str, function: Callable[..., Any]) -> EntrypointSpec:
    return EntrypointSpec(
        name=name,
        role=role,
        function=function,
        command=("python", CONTAINER_ENTRYPOINT_PATH, name),
    )


ENTRYPOINTS: Mapping[str, EntrypointSpec] = {
    spec.name: spec
    for spec in (
        _spec("source-custodian", "source_custodian", run_source_custodian),
        _spec("normalizer", "normalizer", run_normalizer),
        _spec("reviewer-a", "reviewer_a", run_reviewer_a),
        _spec("reviewer-b", "reviewer_b", run_reviewer_b),
        _spec("broker", "broker", run_broker),
        _spec("arbiter", "arbiter", run_arbiter),
        _spec("selector", "selector", run_selector),
        _spec("private-set-auditor", "private_set_auditor", run_private_set_auditor),
        _spec("facts-compiler", "facts_compiler", run_facts_compiler),
        _spec("seal-custodian", "seal_custodian", run_seal_custodian),
        _spec(
            "preregistration-compiler",
            "preregistration_compiler",
            run_preregistration_compiler,
        ),
        _spec("stage-p", "stage_p", run_stage_p),
        _spec("prediction-sealer", "prediction_sealer", run_prediction_sealer),
        _spec("stage-e", "stage_e", run_stage_e),
        _spec("receipt-exporter", "receipt_exporter", run_receipt_exporter),
    )
}

ENTRYPOINT_NAMES: tuple[str, ...] = tuple(sorted(ENTRYPOINTS))


def resolve_entrypoint(command: Sequence[str]) -> EntrypointSpec:
    """Return the entrypoint a container command actually runs.

    The only supported way to get from a configured command to a callable. A
    command that is not exactly a registered one is refused rather than
    approximately matched, so "python -m ...entrypoints stage-p --extra" and
    "python -m ...other_module stage-p" both fail instead of quietly running
    something.
    """
    wanted = tuple(command)
    for spec in ENTRYPOINTS.values():
        if spec.command == wanted:
            return spec
    raise EntrypointError(f"command {list(command)} is not a registered entrypoint")


def entrypoint_call_graph(name: str) -> tuple[str, ...]:
    """Return the global names the entrypoint's bytecode actually references.

    Read from the code object rather than from a maintained list, so a function
    that stopped calling a guard stops reporting it. This is what makes the call
    graph mechanically inspectable instead of merely documented.
    """
    if name not in ENTRYPOINTS:
        raise EntrypointError(f"unregistered entrypoint {name!r}")
    function = ENTRYPOINTS[name].function
    return tuple(sorted(set(function.__code__.co_names)))


def assert_entrypoint_is_guarded(name: str) -> None:
    """Refuse an entrypoint that does not pass through the guarded prologue."""
    graph = entrypoint_call_graph(name)
    if "_guarded" not in graph and "_run_reviewer" not in graph:
        raise EntrypointError(
            f"entrypoint {name!r} does not reach the guarded prologue; every "
            "payload path must be preceded by identity, lane and isolation checks"
        )


def assert_container_command_is_registered(role: str, command: Sequence[str]) -> None:
    """Refuse an IaC container command that does not name this role's entrypoint."""
    spec = resolve_entrypoint(command)
    if spec.role != role:
        raise EntrypointError(
            f"container command runs the {spec.role!r} entrypoint but the container "
            f"is configured for role {role!r}"
        )


def export_role_matrix() -> Mapping[str, Any]:
    """Emit the deployment matrix the IaC consumes.

    Generated from the registries above rather than transcribed beside them. A
    hand-written copy of this table would be correct on the day it was written
    and unfalsifiable afterwards; generating it means the infrastructure and the
    code cannot disagree without a test noticing.
    """
    return {
        "schema_version": "phase1-parser-v3-v2-role-matrix/v1",
        "container_entrypoint_path": CONTAINER_ENTRYPOINT_PATH,
        "config_digest_schema_version": CONFIG_DIGEST_SCHEMA_VERSION,
        "config_digest_fields": list(CONFIG_DIGEST_FIELDS),
        "roles": [
            {
                "role": spec.role,
                "entrypoint": spec.name,
                "command": list(spec.command),
                "uami_name": ROLE_IDENTITY_NAMES[spec.role],
                "container": REGISTERED_CONTAINERS[spec.role],
                "prefix": REGISTERED_PREFIXES[spec.role],
                "schema_ids": list(ROLE_SCHEMAS[spec.role]),
                "reads": list(lifecycle.ROLE_LANES[spec.role]["reads"]),
                "writes": list(lifecycle.ROLE_LANES[spec.role]["writes"]),
                "read_containers": sorted(
                    {
                        READ_CONTAINERS[read_class]
                        for read_class in lifecycle.ROLE_LANES[spec.role]["reads"]
                    }
                ),
                "parser_free": spec.role in PARSER_FREE_ROLES,
            }
            for spec in sorted(ENTRYPOINTS.values(), key=lambda item: item.role)
        ],
        "registered_endpoints": sorted(REGISTERED_ENDPOINTS),
        "schema_registry_digest": schemas.REGISTRY_DIGEST,
    }


#: Exit code for a preflight that passed and then stopped.
#:
#: Distinct from 0 because a container that did no work must not report success
#: to the orchestrator, and distinct from 1 because "the boundary is correct and
#: the payload has not been supplied" is not the same event as "the boundary is
#: wrong".
PREFLIGHT_WITHOUT_PAYLOAD = 3

#: The environment a preflight reads to reconstruct the role's configuration.
PREFLIGHT_ENVIRONMENT_NAMES: tuple[str, ...] = (
    "JSPACE_ROLE",
    "JSPACE_UAMI_NAME",
    "JSPACE_ENDPOINT",
    "JSPACE_CONTAINER",
    "JSPACE_PREFIX",
    "JSPACE_SCHEMA_IDS",
    "JSPACE_SCHEMA_REGISTRY_DIGEST",
    "JSPACE_IMAGE_DIGEST",
    "JSPACE_CONFIG_DIGEST",
    "AZURE_CLIENT_ID",
)


def _preflight_callback(*args: Any, **kwargs: Any) -> Any:
    raise EntrypointError("a preflight touched a callback before completing its guards")


_PREFLIGHT_ARGUMENT_VALUES: Mapping[str, Any] = {
    "admission_records": (),
    "packets": (),
    "decide": _preflight_callback,
    "pairs": (),
    "adjudicate": _preflight_callback,
    "admitted": (),
    "facts": {},
    "plan": {},
    "existing_objects": (),
    "bindings": {},
    "existing_lock_digest": None,
    "lock": {},
    "lock_digest": "",
    "state": "",
    "ordinal": 0,
    "locked_inputs": (),
    "parser": _preflight_callback,
    "stream": {},
    "sealed_case_ids": (),
    "write_order": (),
    "terminal_manifest": "",
    "prediction_receipt": {},
    "sealed_members": (),
    "labels": {},
    "strata": {},
    "existing_result_digests": (),
    "receipt": {},
}


def _preflight_payload(function: Callable[..., Any]) -> Mapping[str, Any]:
    """Build inert arguments for one registered callable from its signature.

    The values must never be read: :func:`_guarded` raises
    :class:`_PreflightComplete` first. They exist so Python can enter the real
    callable and prove that the command-to-callable binding reaches the exact
    guard path the private invocation uses. Signature introspection keeps this
    list fail-closed: a new required argument without an inert value prevents
    the image from reporting a successful preflight.
    """
    supplied: dict[str, Any] = {}
    common = {"config", "environment", "loaded_module_names"}
    for parameter in inspect.signature(function).parameters.values():
        if parameter.name in common or parameter.default is not inspect.Parameter.empty:
            continue
        if parameter.name not in _PREFLIGHT_ARGUMENT_VALUES:
            raise EntrypointError(
                f"no inert preflight value is registered for {parameter.name!r}"
            )
        supplied[parameter.name] = _PREFLIGHT_ARGUMENT_VALUES[parameter.name]
    return supplied


def _runtime_module_names() -> tuple[str, ...]:
    """Snapshot the real process modules for the deployed command."""
    return tuple(sorted(sys.modules))


def preflight(
    name: str,
    environment: Mapping[str, str],
    *,
    loaded_module_names: Iterable[str] | None = None,
) -> AccessLog:
    """Run every boundary check the named entrypoint would run, and stop there.

    This is what the registered container command actually does. Public audit
    finding B-01 observed that the command bound by the role matrix, by the
    Bicep, and by the preregistration lock resolved to a ``main`` that
    validated the name and then refused unconditionally: the one command the
    freeze binds provably could not do the work it was bound to. Refusing to
    fetch a payload is right -- a role that could fetch its own payload could
    reach private material on its own -- but refusing to do *anything* made the
    binding untruthful.

    So the command now dispatches ``spec.function`` itself with inert arguments.
    Its real guarded prologue checks configuration, identity, environment
    closure, lanes and import isolation, then raises the internal
    :class:`_PreflightComplete` signal before any inert argument can be read. It
    exits :data:`PREFLIGHT_WITHOUT_PAYLOAD` because the payload still has to
    arrive from the private boundary and this process is still not allowed to go
    and get one.
    """
    if name not in ENTRYPOINTS:
        raise EntrypointError(f"unregistered entrypoint {name!r}")
    spec = ENTRYPOINTS[name]
    missing = sorted(set(PREFLIGHT_ENVIRONMENT_NAMES) - set(environment))
    if missing:
        raise EntrypointError(f"preflight environment is missing {missing}")
    declared_role = environment["JSPACE_ROLE"]
    if declared_role != spec.role:
        raise EntrypointError(
            f"the container is configured for role {declared_role!r} but was "
            f"started with the {spec.role!r} entrypoint"
        )
    config = RoleConfig(
        role=declared_role,
        uami_name=environment["JSPACE_UAMI_NAME"],
        uami_client_id=environment["AZURE_CLIENT_ID"],
        private_endpoint=environment["JSPACE_ENDPOINT"],
        container=environment["JSPACE_CONTAINER"],
        prefix=environment["JSPACE_PREFIX"],
        schema_ids=tuple(
            part for part in environment["JSPACE_SCHEMA_IDS"].split(",") if part
        ),
        schema_registry_digest=environment["JSPACE_SCHEMA_REGISTRY_DIGEST"],
        image_digest=environment["JSPACE_IMAGE_DIGEST"],
        config_digest=environment["JSPACE_CONFIG_DIGEST"],
    )
    assert_container_command_is_registered(role=config.role, command=spec.command)
    token = _PREFLIGHT_ACTIVE.set(True)
    try:
        spec.function(
            config=config,
            environment=environment,
            loaded_module_names=(
                _runtime_module_names()
                if loaded_module_names is None
                else tuple(loaded_module_names)
            ),
            **_preflight_payload(spec.function),
        )
    except _PreflightComplete as completed:
        return completed.log
    finally:
        _PREFLIGHT_ACTIVE.reset(token)
    raise EntrypointError(
        f"entrypoint {name!r} returned without reaching the guarded preflight"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Preflight through the same table the IaC and the tests use."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise EntrypointError("exactly one entrypoint name is required")
    name = args[0]
    log = preflight(name, dict(os.environ))
    print(
        json.dumps(
            {
                "schema_version": "phase1-parser-v3-v2-preflight/v1",
                "entrypoint": name,
                "role": ENTRYPOINTS[name].role,
                "events": list(log.event_ids()),
                "outcome": "PREFLIGHT_PASSED_PAYLOAD_NOT_SUPPLIED",
            },
            sort_keys=True,
        )
    )
    return PREFLIGHT_WITHOUT_PAYLOAD


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
