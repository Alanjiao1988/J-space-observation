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
other, and :func:`main` dispatches through the same table. So the command the
IaC configures, the function the tests exercise, and the function the container
executes are the same object, and a test can prove it by substituting any of
them and observing a refusal.

What an entrypoint deliberately does not do
===========================================

It does not fetch its own payload from the network. Storage and identity
plumbing belong to the Phase B boundary; an entrypoint that both authorised
itself and fetched its bytes could not be tested for the authorisation step
without also standing up the storage. Here the payload arrives as an argument,
the entrypoint refuses it unless every lane, identity, schema and isolation
check has already passed, and the boundary supplies the bytes.
"""

from __future__ import annotations

import importlib.util
import re
import sys
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
    "FORBIDDEN_CREDENTIAL_MARKERS",
    "ENTRYPOINTS",
    "ENTRYPOINT_NAMES",
    "CONTAINER_ENTRYPOINT_PATH",
    "resolve_entrypoint",
    "entrypoint_call_graph",
    "assert_entrypoint_is_guarded",
    "assert_container_command_is_registered",
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
    image_digest: str
    config_digest: str


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
    if not _IMAGE_DIGEST.match(config.image_digest or ""):
        raise EntrypointError("image_digest must be an explicit sha256: digest, not a tag")
    if not _SHA256.match(config.config_digest or ""):
        raise EntrypointError("config_digest must be a SHA-256 hex digest")


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
    except EntrypointError:
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
    existing_objects: Sequence[str] = (),
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
    existing_lock_digest: str | None = None,
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
        reads=list(lock["stage_p_read_classes"]),
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
    existing_objects: Sequence[str] = (),
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
    parser_v2_comparison: str = "NOT_RUN",
) -> Mapping[str, Any]:
    """Open labels once and produce the unique formal result."""
    log = AccessLog(role=config.role)
    _guarded(
        config,
        reads=list(lock["stage_e_read_classes"]),
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


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch through the same table the IaC and the tests use."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise EntrypointError("exactly one entrypoint name is required")
    name = args[0]
    if name not in ENTRYPOINTS:
        raise EntrypointError(f"unregistered entrypoint {name!r}")
    raise EntrypointError(
        f"entrypoint {name!r} requires its payload from the private boundary; "
        "it must not fetch or synthesise one itself"
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
