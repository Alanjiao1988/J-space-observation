"""Parser-free tooling for the Phase 1.2B one-shot locked evaluation.

This module intentionally has no package-relative imports.  The Stage-E
executable loads it directly from this file, without executing
``jspace_observation.__init__`` or making either parser reachable.
"""

from __future__ import annotations

import ast
import base64
import binascii
import csv
import hashlib
import importlib
import importlib.util
import ipaddress
import io
import json
import math
import os
import re
import socket
import subprocess
import sys
from collections import Counter
from datetime import datetime
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlsplit


PARSER_EVALUATION_PROFILE_SCHEMA_VERSION = "phase1-parser-evaluation-profile/v1"
DEFAULT_PARSER_EVALUATION_PROFILE_ID = "parser-v2-v1"

# The candidate parser's identity reaches the rest of this module through the
# five FROZEN_PARSER_*/FROZEN_ACCEPTANCE_GATE_SHA256 names bound below. Every
# other site reads them by name, so selecting a candidate is a matter of
# binding these once at import rather than editing any call site.
#
# FROZEN_PROTOCOL_COMMIT and FROZEN_PROTOCOL_BUNDLE_SHA256 are deliberately not
# profile-scoped: parser v3 binds the parser-v2 protocol bundle inside its own
# parser_version, so varying them would contradict the candidate's own identity.
_PARSER_EVALUATION_PROFILES = {
    "parser-v2-v1": {
        "profile_id": "parser-v2-v1",
        "candidate_parser": "parser_v2",
        "candidate_parser_algorithm_id": (
            "jspace-parser-v2-reference-blind-extraction/v1"
        ),
        "orchestrator_schema_compatibility": "parser_v2_field_names_v1",
        "comparator_parsers": ("legacy",),
        "parser_source_path": "src/jspace_observation/eval_parsing_v2.py",
        "parser_entry_symbol": "parse_v2",
        "parser_worker_path": "scripts/parser_v2_process_worker.py",
        "parser_source_sha256": (
            "f538add0bdd6e5a3281d0298b374a99fecea962a91a4cbaa5b4a20795d9a6918"
        ),
        "parser_git_blob_oid": "7428dd3fe5be621e32a6331e2d34fd62cea0fb91",
        "parser_version": (
            "6cfaec62db37562930a4cb7d3a252bcbf80e1eaf748de98213863ff2566a7f86"
        ),
        "parser_implementation_commit": (
            "ab6abec42a13d0e1c193fad7db420dbd512c2f03"
        ),
        "acceptance_gate_path": "docs/phase1_parser_v2_acceptance_gates.json",
        "acceptance_gate_sha256": (
            "a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988"
        ),
        "sealed_holdout_family": "parser-v2-v1",
        "candidate_predictions_filename": "parser_v2_locked_predictions.jsonl",
        "comparator_predictions_filenames": ("legacy_locked_predictions.jsonl",),
        "extra_source_binding_paths": (),
        "extra_image_binding_paths": (),
    },
    "parser-v3-v1": {
        "profile_id": "parser-v3-v1",
        "candidate_parser": "parser_v3",
        "candidate_parser_algorithm_id": (
            "jspace-parser-v3-reference-blind-extraction/v1"
        ),
        "orchestrator_schema_compatibility": "parser_v2_field_names_v1",
        "comparator_parsers": ("parser_v2", "legacy"),
        "parser_source_path": "src/jspace_observation/eval_parsing_v3.py",
        "parser_entry_symbol": "parse_v3",
        "parser_worker_path": "scripts/parser_v3_process_worker.py",
        "parser_source_sha256": (
            "76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9"
        ),
        "parser_git_blob_oid": "18676eefff3e4f3ed0ce4e592e41e1794365006e",
        "parser_version": (
            "0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace"
        ),
        "parser_implementation_commit": (
            "310277bcadd67ca9e77986fc292fae47dc5ceda2"
        ),
        "acceptance_gate_path": "docs/phase1_parser_v3_acceptance_gates.json",
        "acceptance_gate_sha256": (
            "2fcc323481221fbc5c1f56b5beccd238fd835303c46df61087e1483dfc28dda7"
        ),
        "sealed_holdout_family": "parser-v3-v1",
        "candidate_predictions_filename": "parser_v3_candidate_predictions.jsonl",
        "comparator_predictions_filenames": (
            "parser_v2_comparator_predictions.jsonl",
            "legacy_comparator_predictions.jsonl",
        ),
        "extra_source_binding_paths": (
            "src/jspace_observation/eval_parsing_v3.py",
            "scripts/parser_v3_process_worker.py",
        ),
        "extra_image_binding_paths": (
            "src/jspace_observation/eval_parsing_v3.py",
            "scripts/parser_v3_process_worker.py",
            "docs/phase1_parser_v3_acceptance_gates.json",
        ),
    },
}

# Selected once, at import, by a loader that seeds this name into the module
# namespace before execution. Absent a deliberate choice the profile is v2, so
# every pre-existing loader keeps the behaviour it already had.
ACTIVE_PARSER_PROFILE_ID = globals().pop(
    "_PRESEEDED_PARSER_PROFILE_ID", DEFAULT_PARSER_EVALUATION_PROFILE_ID
)
if ACTIVE_PARSER_PROFILE_ID not in _PARSER_EVALUATION_PROFILES:
    raise RuntimeError(
        f"unknown parser evaluation profile: {ACTIVE_PARSER_PROFILE_ID!r}"
    )
ACTIVE_PARSER_PROFILE = dict(_PARSER_EVALUATION_PROFILES[ACTIVE_PARSER_PROFILE_ID])

FROZEN_PROTOCOL_COMMIT = "cc93ffe603ab8338ed860586a52b1911af4b3277"
FROZEN_PROTOCOL_BUNDLE_SHA256 = (
    "5d486a53b532012c3a64eb6bd962be325fb9892ebbb042807b919f9e41b23666"
)
FROZEN_ACCEPTANCE_GATE_SHA256 = ACTIVE_PARSER_PROFILE["acceptance_gate_sha256"]
FROZEN_PARSER_SOURCE_SHA256 = ACTIVE_PARSER_PROFILE["parser_source_sha256"]
FROZEN_PARSER_GIT_BLOB_OID = ACTIVE_PARSER_PROFILE["parser_git_blob_oid"]
FROZEN_PARSER_VERSION = ACTIVE_PARSER_PROFILE["parser_version"]
FROZEN_STARTING_COMMIT = "02577a272e2f3740485fa97630f6c82450fe6017"
FROZEN_PARSER_IMPLEMENTATION_COMMIT = ACTIVE_PARSER_PROFILE[
    "parser_implementation_commit"
]
FROZEN_LEGACY_PARSER_COMMIT = FROZEN_STARTING_COMMIT
FROZEN_LEGACY_PARSER_GIT_BLOB_OID = (
    "d9b0bd56f7757af64b79f71332f45570b4b8cb6d"
)
FROZEN_LEGACY_PARSER_SOURCE_SHA256 = (
    "4b07b91859aca33b51af9c15b08f07026f11b0141f1300fd3f942138b731177e"
)

LOCKED_INPUT_SCHEMA_VERSION = "phase1-parser-v2-locked-input/v1"
FINAL_LABEL_SCHEMA_VERSION = "phase1-parser-v2-locked-reference-label/v1"
PARSER_REQUEST_SCHEMA_VERSION = "phase1-parser-v2-request/v1"
PARSER_RESULT_SCHEMA_VERSION = "phase1-parser-v2-result/v1"
PREDICTION_ENVELOPE_SCHEMA_VERSION = "phase1-parser-v2-prediction/v1"
FROZEN_PREDICTION_SEAL_SCHEMA_VERSION = "phase1-parser-v2-prediction-seal/v1"
LEGACY_PREDICTION_SCHEMA_VERSION = "phase1-parser-v2-legacy-prediction/v1"
PREDICTION_REQUEST_MANIFEST_SCHEMA_VERSION = (
    "phase1-parser-v2-locked-prediction-request-manifest/v1"
)
LOCKED_PREDICTION_SEAL_SCHEMA_VERSION = (
    "phase1-parser-v2-locked-prediction-seal/v1"
)
PREDICTION_MANIFEST_SCHEMA_VERSION = (
    "phase1-parser-v2-locked-prediction-manifest/v1"
)
SCORE_MANIFEST_SCHEMA_VERSION = "phase1-parser-v2-locked-score-manifest/v2"
METRICS_SCHEMA_VERSION = "phase1-parser-v2-locked-metrics/v2"
DECISION_SCHEMA_VERSION = "phase1-parser-v2-locked-decision/v2"
RETIREMENT_SCHEMA_VERSION = "phase1-parser-v2-locked-retirement/v2"
RUNTIME_CONFIG_SCHEMA_VERSION = "phase1-parser-v2-runtime-config/v5"
IMAGE_BINDING_SCHEMA_VERSION = "phase1-parser-v2-eval-image-binding/v6"
IMAGE_BINDING_ESSENTIAL_SCHEMA_VERSION = (
    "phase1-parser-v2-runtime-image-provenance/v3"
)
BUILD_SOURCE_BINDING_SCHEMA_VERSION = (
    "phase1-parser-v2-build-source-binding/v2"
)
BUILD_PROVENANCE_SCHEMA_VERSION = "phase1-parser-v2-build-provenance/v4"
COORDINATION_BINDING_SCHEMA_VERSION = (
    "phase1-parser-v2-dns-coordination/v1"
)
CLAIM_DOMAIN_SCHEMA_VERSION = "phase1-parser-v2-claim-domain/v1"
PRIVATE_DNS_RECORD_SET_API_VERSION = "2024-06-01"
MANAGEMENT_LOCK_API_VERSION = "2016-09-01"
OCI_VERIFICATION_SCHEMA_VERSION = "phase1-parser-v2-oci-verification/v1"
BUILD_PROVENANCE_LABEL = (
    "org.opencontainers.image.build-provenance-sha256"
)
CLOSURE_MANIFEST_SCHEMA_VERSION = "phase1-parser-v2-closure-manifest/v2"
RESERVATION_SCHEMA_VERSION = "phase1-parser-v2-locked-reservation/v1"
STATE_RECEIPT_SCHEMA_VERSION = "phase1-parser-v2-state-receipt/v1"
AUTHORIZATION_LOCK_SCHEMA_VERSION = "phase1-parser-v2-authorization-lock/v1"
IMPLEMENTATION_MANIFEST_SCHEMA_VERSION = (
    "phase1-parser-v2-implementation-manifest/v1"
)
LABELS_OPEN_TRANSACTION_SCHEMA_VERSION = (
    "phase1-parser-v2-labels-open-transaction/v2"
)
AUTHORIZATION_MANIFEST_SCHEMA_VERSION = (
    "phase1-parser-v2-authorization-manifest/v2"
)
SPENT_INCOMPLETE_SCHEMA_VERSION = (
    "phase1-parser-v2-spent-incomplete-failure/v1"
)
SCORING_INCOMPLETE_SCHEMA_VERSION = (
    "phase1-parser-v2-scoring-incomplete-failure/v1"
)
INVALID_CLOSURE_SCHEMA_VERSION = (
    "phase1-parser-v2-invalid-closure-manifest/v1"
)
VISIBILITY_SCHEMA_VERSION = "phase1-parser-v2-evaluation-visibility/v1"
SCORING_TRANSACTION_SCHEMA_VERSION = (
    "phase1-parser-v2-scoring-transaction/v2"
)
SCORING_ATTESTATION_SCHEMA_VERSION = (
    "phase1-parser-v2-scoring-attestation/v2"
)
SCORING_LEDGER_SCHEMA_VERSION = "phase1-parser-v2-scoring-ledger-row/v2"
ABANDONED_ATTEMPT_SCHEMA_VERSION = (
    "phase1-parser-v2-abandoned-attempt/v1"
)
ATTEMPT_DESCRIPTOR_SCHEMA_VERSION = (
    "phase1-parser-v2-attempt-membership-descriptor/v1"
)

SOURCE_KIND = "constructed_model_free_fixture"
TYPED_DECISION_CLASSES = ("present", "ambiguous", "no_answer")
PARSER_PRESENCE = ("present", "absent", "uncertain")
EXTRACTION_STRATEGIES = (
    "boxed_answer",
    "explicit_final_marker",
    "explicit_answer_marker",
    "terminal_equation",
    "single_candidate",
    "none",
    "ambiguous_candidates",
)
OUTPUT_QUALITIES = (
    "complete",
    "truncated",
    "malformed_recoverable",
    "malformed_unrecoverable",
    "placeholder",
    "empty",
)
FAILURE_REASONS = (
    "empty_output",
    "placeholder_without_answer",
    "truncated_before_final_answer",
    "malformed_without_reliable_answer",
    "unsupported_numeric_literal",
    "no_reliable_answer",
)
FORMAT_WARNINGS = (
    "multiple_numeric_mentions",
    "reasoning_continues_after_answer",
    "equivalent_repeated_claim",
    "lower_priority_conflict_ignored",
    "incomplete_box",
    "unbalanced_think_tag",
    "stray_think_tag",
    "redundant_answer_marker",
    "noncanonical_numeric_surface",
    "incidental_numeric_material",
)
EVIDENCE_KINDS = (
    "boxed",
    "explicit_final_marker",
    "explicit_answer_marker",
    "terminal_equation",
    "single_candidate",
)
EVIDENCE_DISPOSITIONS = (
    "selected",
    "equivalent",
    "ambiguous_candidate",
)

CONSTRUCTION_STATE_SEQUENCE = (
    "DRAFT_PROTOCOL",
    "PROTOCOL_FROZEN",
    "PRIVATE_CONSTRUCTION",
    "RESERVED",
    "PAYLOAD_COMPLETE",
    "SEALED",
)
EVALUATION_STATE_SEQUENCE = (
    "IMPLEMENTATION_FROZEN",
    "UNSEAL_AUTHORIZED",
    "INPUTS_READ",
    "PREDICTIONS_VERIFIED",
    "LABELS_READ",
    "SCORES_VERIFIED",
    "CLOSED",
)
HOLDOUT_STATE_SEQUENCE = (*CONSTRUCTION_STATE_SEQUENCE, *EVALUATION_STATE_SEQUENCE)
CONSTRUCTION_STATES = CONSTRUCTION_STATE_SEQUENCE
EVALUATION_STATES = EVALUATION_STATE_SEQUENCE
HOLDOUT_STATES = HOLDOUT_STATE_SEQUENCE
STATE_AUTHORIZED_ARTIFACT_BINDINGS = {
    "DRAFT_PROTOCOL": frozenset(),
    "PROTOCOL_FROZEN": frozenset({"protocol_manifest", "acceptance_gates"}),
    "PRIVATE_CONSTRUCTION": frozenset(
        {"selection_plan", "overlap_report", "construction_manifest"}
    ),
    "RESERVED": frozenset({"reservations_manifest"}),
    "PAYLOAD_COMPLETE": frozenset(
        {
            "development_manifest",
            "locked_inputs_manifest",
            "locked_labels_manifest",
            "reports_manifest",
        }
    ),
    "SEALED": frozenset({"locked_manifest"}),
    "IMPLEMENTATION_FROZEN": frozenset({"implementation_manifest"}),
    "UNSEAL_AUTHORIZED": frozenset({"authorization_manifest"}),
    "INPUTS_READ": frozenset({"inputs_manifest"}),
    "PREDICTIONS_VERIFIED": frozenset({"predictions_manifest"}),
    "LABELS_READ": frozenset({"labels_manifest"}),
    "SCORES_VERIFIED": frozenset({"scores_manifest"}),
    "CLOSED": frozenset({"closure_manifest"}),
}
STATE_RECEIPT_FILENAMES = {
    state: f"{index:02d}_{state.casefold()}_receipt.json"
    for index, state in enumerate(HOLDOUT_STATE_SEQUENCE)
}
STATE_RETRY_RECEIPT_FILENAMES = {
    kind: f"retry_{kind}_receipt.json"
    for kind in (
        "infrastructure_pre_input",
        "scorer_infrastructure",
        "verification_only",
    )
}
AUTHORIZATION_LOCK_BLOB_PREFIX = (
    "phase1-evaluator-validation/parser-v2-v1/authorization-locks"
)
IMPLEMENTATION_MANIFEST_FILENAME = "implementation_manifest.json"
RUNTIME_CONFIG_FILENAME = "runtime_config.json"
AUTHORIZATION_MANIFEST_FILENAME = "authorization_manifest.json"
CLOSURE_MANIFEST_FILENAME = "closure_manifest.json"
LABELS_OPEN_TRANSACTION_FILENAME = "labels_open_transaction.json"
SCORING_TRANSACTION_FILENAME = "scoring_transaction.json"
SCORING_ATTESTATION_FILENAME = "scoring_attestation.json"
SCORING_LEDGER_FILENAME = "scoring_ledger.jsonl"
SPENT_INCOMPLETE_FILENAME = "spent_incomplete_failure.json"
SCORING_INCOMPLETE_FILENAME = "scoring_incomplete_failure.json"
INVALID_CLOSURE_FILENAME = "invalid_closure_manifest.json"
ABANDONED_ATTEMPT_FILENAME = "abandoned_attempt.json"
PARSER_V2_EVAL_BASE_IMAGE = (
    "python:3.11.14-slim-bookworm@"
    "sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d"
)

CANDIDATE_PREDICTION_FILENAME = ACTIVE_PARSER_PROFILE["candidate_predictions_filename"]
COMPARATOR_PREDICTION_FILENAMES = ACTIVE_PARSER_PROFILE[
    "comparator_predictions_filenames"
]
PREDICTION_MEMBER_NAMES = (
    (
        ".prediction_reservation.json",
        "prediction_request_manifest.json",
        CANDIDATE_PREDICTION_FILENAME,
    )
    + COMPARATOR_PREDICTION_FILENAMES
    + (
        "prediction_seal.json",
        "prediction_artifact_manifest.json",
    )
)
SCORE_MEMBER_NAMES = (
    ".scores_reservation.json",
    SCORING_LEDGER_FILENAME,
    "locked_evaluation_metrics.json",
    "locked_evaluation_metrics.csv",
    "locked_evaluation_failures.jsonl",
    "locked_evaluation_decision.json",
    "retirement_record.json",
    "locked_evaluation_report.md",
    "scores_manifest.json",
)

RUNTIME_SOURCE_BINDING_PATHS = (
    "Dockerfile.parser-v2-eval",
    "requirements-parser-v2-eval.txt",
    "infra/azure/scripts/09_build_parser_v2_eval.sh",
    "infra/azure/scripts/10_run_parser_v2_locked_eval.sh",
    "scripts/create_parser_v2_runtime_config.py",
    "scripts/bootstrap_parser_v2_locked_evaluation.py",
    "scripts/parser_v2_azure_contract.py",
    "scripts/parser_v2_process_worker.py",
    "scripts/run_parser_v2_locked_predictions.py",
    "scripts/finalize_parser_v2_locked_evaluation.py",
    "scripts/stage_p_entrypoint.sh",
    "scripts/stage_p_adopt_entrypoint.sh",
    "scripts/stage_e_entrypoint.sh",
    "src/jspace_observation/evaluator_validation.py",
    "src/jspace_observation/eval_parsing.py",
    "src/jspace_observation/eval_parsing_v2.py",
    "src/jspace_observation/parser_v2_locked_evaluation.py",
) + ACTIVE_PARSER_PROFILE["extra_source_binding_paths"]
IMAGE_BINDING_SOURCE_PATHS = (
    ".dockerignore",
    ".gitattributes",
    "Dockerfile.parser-v2-eval",
    "requirements-parser-v2-eval.txt",
    "infra/azure/scripts/09_build_parser_v2_eval.sh",
    "infra/azure/scripts/10_run_parser_v2_locked_eval.sh",
    "scripts/create_parser_v2_runtime_config.py",
    "scripts/bootstrap_parser_v2_locked_evaluation.py",
    "scripts/parser_v2_azure_contract.py",
    "scripts/parser_v2_process_worker.py",
    "scripts/run_parser_v2_locked_predictions.py",
    "scripts/finalize_parser_v2_locked_evaluation.py",
    "scripts/stage_p_entrypoint.sh",
    "scripts/stage_p_adopt_entrypoint.sh",
    "scripts/stage_e_entrypoint.sh",
    "src/jspace_observation/evaluator_validation.py",
    "src/jspace_observation/eval_parsing.py",
    "src/jspace_observation/eval_parsing_v2.py",
    "src/jspace_observation/parser_v2_locked_evaluation.py",
    "docs/phase1_parser_v2_protocol.md",
    "docs/phase1_evaluator_validation_set.md",
    "docs/phase1_parser_v2_acceptance_gates.json",
) + ACTIVE_PARSER_PROFILE["extra_image_binding_paths"]

_PROTOCOL_FILES = (
    "docs/phase1_parser_v2_protocol.md",
    "docs/phase1_evaluator_validation_set.md",
    "docs/phase1_parser_v2_acceptance_gates.json",
)
_FROZEN_PROTOCOL_FILE_SHA256S = {
    "docs/phase1_parser_v2_protocol.md": (
        "417d9ff5d27b17ce588b7713a1b1072fb32ef21a03fd135e4e339719db28866b"
    ),
    "docs/phase1_evaluator_validation_set.md": (
        "d019c446393bc60dc524178c2a91018ceb8f04f881dcc80018f0282b0919f3f8"
    ),
    "docs/phase1_parser_v2_acceptance_gates.json": (
        "a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988"
    ),
}
_PROTOCOL_BUNDLE_DOMAIN = b"jspace-parser-v2-validation/protocol-bundle/v1\0"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z", re.ASCII)
_IMAGE_DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)
_GIT_OBJECT_ID_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z", re.ASCII)
_ACR_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z", re.ASCII)
_ACR_TASK_RUN_NAME_PATTERN = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{3,48}[a-z0-9])\Z", re.ASCII
)
_CASE_ID_PATTERN = re.compile(r"PV2-[0-9a-f]{20}\Z", re.ASCII)
_AUTHORIZATION_ID_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z", re.ASCII
)
_REGISTERED_PARENT_PATTERN = re.compile(
    r"phase1-evaluator-validation/parser-v2-v1/"
    r"(?P<timestamp>[0-9]{8}T[0-9]{6}Z)\Z",
    re.ASCII,
)
_UTC_PATTERN = re.compile(
    r"[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])"
    r"T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z\Z",
    re.ASCII,
)
_DECIMAL_PATTERN = re.compile(
    r"[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))"
    r"(?:[eE][+-]?[0-9]+)?\Z",
    re.ASCII,
)
_FRACTION_PATTERN = re.compile(r"[+-]?[0-9]+/[0-9]+\Z", re.ASCII)
_CONTAINER_PATTERN = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?\Z", re.ASCII
)
_ACCOUNT_HOST_PATTERN = re.compile(
    r"[a-z0-9][a-z0-9-]{1,22}[a-z0-9]\.blob\.core\.windows\.net\Z",
    re.ASCII,
)
_AZURE_CLIENT_ID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z",
    re.ASCII | re.IGNORECASE,
)
_AZURE_OPAQUE_INTERNAL_ID_PATTERN = re.compile(
    r"[A-Za-z0-9+/]{16,252}={0,2}\Z", re.ASCII
)
_AZURE_RESOURCE_ID_PATTERN = re.compile(
    r"/subscriptions/(?P<subscription>[0-9a-f-]{36})"
    r"/resourceGroups/(?P<resource_group>[A-Za-z0-9._()-]{1,90})"
    r"/providers/(?P<provider>[A-Za-z][A-Za-z0-9.]+)"
    r"/(?P<tail>[A-Za-z0-9._()/-]+)\Z",
    re.ASCII | re.IGNORECASE,
)
_AZURE_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z", re.ASCII)
_ACR_LOGIN_SERVER_PATTERN = re.compile(
    r"[a-z0-9][a-z0-9-]{3,48}[a-z0-9]\.azurecr\.io\Z", re.ASCII
)
_AZURE_LOCATION_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,62}\Z", re.ASCII)
_IMAGE_REPOSITORY_PATTERN = re.compile(
    r"[a-z0-9]+(?:[._/-][a-z0-9]+)*\Z", re.ASCII
)
_SOURCE_PREFIX_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
    r"(?:/[A-Za-z0-9][A-Za-z0-9._-]{0,127}){0,15}\Z",
    re.ASCII,
)
_STAGE_RUNTIME_ENVIRONMENT = {
    "HOME": "/nonexistent",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "TMPDIR": "/runtime/work",
}
_PROHIBITED_CREDENTIAL_ENV = (
    "AZURE_STORAGE_CONNECTION_STRING",
    "AZURE_STORAGE_KEY",
    "AZURE_STORAGE_ACCOUNT_KEY",
    "AZURE_STORAGE_SAS_TOKEN",
    "AZURE_SAS_TOKEN",
)
_FORBIDDEN_PARSER_MODULE_PARTS = (
    "eval_parsing",
    "eval_parsing_v2",
)
_STAGE_P_FEATURE_COUNT_FIELDS = frozenset(
    {
        "signed_numeric_surface",
        "negative_answer",
        "decimal_surface",
        "fraction_surface",
        "noncanonical_numeric_surface",
        "balanced_think_tags",
        "malformed_think_tags",
        "incidental_numeric_distractor",
        "multiple_numeric_mentions",
        "continued_reasoning",
        "last_number_distractor",
        "multiple_distinct_candidates",
        "truncated_construct",
        "placeholder_output",
        "malformed_output",
    }
)
_FROZEN_EVALUATOR_VALIDATION_SHA256 = (
    "63eb1c7d8b229dddafdd3d54a0d62bb415d76ae8dd5aab220bd91ff054f08344"
)
_MAX_LITERAL_CHARACTERS = 100
_MAX_CANONICAL_CHARACTERS = 4096


class LockedEvaluationError(ValueError):
    """Raised when a locked-evaluation artifact fails closed."""


def _normalized_source_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


@lru_cache(maxsize=1)
def _load_frozen_validation() -> Any:
    """Direct-load the immutable validator without importing the package graph."""
    path = Path(__file__).resolve().with_name("evaluator_validation.py")
    source = _normalized_source_bytes(path)
    if hashlib.sha256(source).hexdigest() != _FROZEN_EVALUATOR_VALIDATION_SHA256:
        raise LockedEvaluationError("frozen evaluator validation digest mismatch")
    name = "_jspace_phase1_frozen_evaluator_validation"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LockedEvaluationError("frozen evaluator validation cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise LockedEvaluationError(
            "frozen evaluator validation cannot be loaded"
        ) from None
    expected = (
        tuple(module.CONSTRUCTION_STATES),
        tuple(module.EVALUATION_STATES),
        {
            state: frozenset(bindings)
            for state, bindings in module.STATE_AUTHORIZED_ARTIFACT_BINDINGS.items()
        },
    )
    actual = (
        CONSTRUCTION_STATE_SEQUENCE,
        EVALUATION_STATE_SEQUENCE,
        STATE_AUTHORIZED_ARTIFACT_BINDINGS,
    )
    if expected != actual:
        sys.modules.pop(name, None)
        raise LockedEvaluationError("frozen state model binding mismatch")
    return module
def sha256_bytes(data: bytes) -> str:
    if type(data) is not bytes:
        raise LockedEvaluationError("SHA-256 input must be exact bytes")
    return hashlib.sha256(data).hexdigest()


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or type(value) in {bool, int}:
        return
    if type(value) is str:
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise LockedEvaluationError("JSON contains a non-Unicode-scalar string")
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise LockedEvaluationError("JSON contains a non-finite number")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise LockedEvaluationError("JSON contains a non-string key")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise LockedEvaluationError("JSON contains an unsupported value type")


def exact_json_equal(left: Any, right: Any) -> bool:
    """Compare JSON without Python's bool/int numeric coercion."""

    try:
        _validate_json_value(left, "left JSON value")
        _validate_json_value(right, "right JSON value")
    except LockedEvaluationError:
        return False
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        if left.keys() != right.keys():
            return False
        return all(exact_json_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            exact_json_equal(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    return bool(left == right)


def canonical_json_text(value: Any) -> str:
    _validate_json_value(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise LockedEvaluationError("value is not canonical-JSON serializable") from exc


def canonical_json_bytes(value: Any) -> bytes:
    return (canonical_json_text(value) + "\n").encode("ascii")


def canonical_jsonl_bytes(records: Sequence[Mapping[str, Any]]) -> bytes:
    if isinstance(records, (str, bytes, bytearray)) or not isinstance(
        records, Sequence
    ):
        raise LockedEvaluationError("JSONL records must be a sequence")
    return (
        ("\n".join(canonical_json_text(dict(record)) for record in records) + "\n")
        .encode("ascii")
        if records
        else b""
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise LockedEvaluationError("JSON contains a duplicate key")
        value[key] = item
    return value


def _reject_nonfinite(value: str) -> None:
    raise LockedEvaluationError("JSON contains a non-finite value")


def parse_json_strict(
    data: bytes, artifact_name: str, *, require_canonical: bool = True
) -> dict[str, Any]:
    if type(require_canonical) is not bool:
        raise LockedEvaluationError("canonical JSON control must be a boolean")
    if type(data) is not bytes:
        raise LockedEvaluationError(f"{artifact_name} must be exact bytes")
    if not data.endswith(b"\n"):
        raise LockedEvaluationError(f"{artifact_name} must end with LF")
    try:
        text = data.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, ValueError, LockedEvaluationError):
        raise LockedEvaluationError(f"{artifact_name} has invalid JSON") from None
    if not isinstance(value, dict):
        raise LockedEvaluationError(f"{artifact_name} must contain one JSON object")
    _validate_json_value(value)
    if require_canonical and data != canonical_json_bytes(value):
        raise LockedEvaluationError(
            f"{artifact_name} is not canonical ASCII JSON"
        )
    return value


def parse_jsonl_strict(
    data: bytes,
    artifact_name: str,
    *,
    require_canonical: bool = True,
    allow_empty: bool = False,
) -> list[dict[str, Any]]:
    if type(require_canonical) is not bool or type(allow_empty) is not bool:
        raise LockedEvaluationError("canonical JSONL controls must be booleans")
    if type(data) is not bytes:
        raise LockedEvaluationError(f"{artifact_name} must be exact bytes")
    if not data:
        if allow_empty:
            return []
        raise LockedEvaluationError(f"{artifact_name} must not be empty")
    if not data.endswith(b"\n"):
        raise LockedEvaluationError(f"{artifact_name} must end with LF")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LockedEvaluationError(f"{artifact_name} is not UTF-8") from exc
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            raise LockedEvaluationError(
                f"{artifact_name} has a blank line at {line_number}"
            )
        try:
            value = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite,
            )
        except (ValueError, LockedEvaluationError):
            raise LockedEvaluationError(
                f"{artifact_name} has invalid JSON at line {line_number}"
            ) from None
        if not isinstance(value, dict):
            raise LockedEvaluationError(
                f"{artifact_name} line {line_number} must be an object"
            )
        _validate_json_value(value)
        records.append(value)
    if require_canonical and data != canonical_jsonl_bytes(records):
        raise LockedEvaluationError(
            f"{artifact_name} is not canonical ASCII JSONL"
        )
    return records


def _require_exact_fields(
    value: Mapping[str, Any], fields: Iterable[str], name: str
) -> None:
    if not isinstance(value, Mapping):
        raise LockedEvaluationError(f"{name} must be an object")
    expected = frozenset(fields)
    actual = frozenset(value)
    if actual != expected:
        raise LockedEvaluationError(f"{name} schema fields are invalid")


def _require_string(
    value: Any, name: str, *, nonempty: bool = True, maximum: int | None = None
) -> str:
    if not isinstance(value, str):
        raise LockedEvaluationError(f"{name} must be a string")
    if nonempty and not value:
        raise LockedEvaluationError(f"{name} must not be empty")
    if maximum is not None and len(value) > maximum:
        raise LockedEvaluationError(f"{name} exceeds {maximum} characters")
    return value


def _require_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise LockedEvaluationError(f"{name} must be a boolean")
    return value


def _require_int(value: Any, name: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise LockedEvaluationError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise LockedEvaluationError(f"{name} must be at least {minimum}")
    return value


def _require_enum(value: Any, allowed: Sequence[str], name: str) -> str:
    checked = _require_string(value, name)
    if checked not in allowed:
        raise LockedEvaluationError(f"{name} has an invalid enumerated value")
    return checked


def _require_sha256(value: Any, name: str, *, allow_zero: bool = False) -> str:
    checked = _require_string(value, name)
    if not _SHA256_PATTERN.fullmatch(checked) or (
        not allow_zero and checked == "0" * 64
    ):
        raise LockedEvaluationError(f"{name} must be a lowercase SHA-256")
    return checked


def _require_commit(value: Any, name: str) -> str:
    checked = _require_string(value, name)
    if not _COMMIT_PATTERN.fullmatch(checked) or checked == "0" * 40:
        raise LockedEvaluationError(f"{name} must be a nonzero full Git commit")
    return checked


def _require_image_digest(value: Any, name: str) -> str:
    checked = _require_string(value, name)
    if not _IMAGE_DIGEST_PATTERN.fullmatch(checked) or checked == "sha256:" + "0" * 64:
        raise LockedEvaluationError(f"{name} must be an immutable OCI digest")
    return checked


def _require_case_id(value: Any, name: str = "case_id") -> str:
    checked = _require_string(value, name)
    if not _CASE_ID_PATTERN.fullmatch(checked):
        raise LockedEvaluationError(f"{name} must match PV2-<20 lowercase hex>")
    return checked


def case_universe_sha256(case_ids: Sequence[str]) -> str:
    ids = [_require_case_id(item, "case universe ID") for item in case_ids]
    if ids != sorted(set(ids)):
        raise LockedEvaluationError("case universe is not exact and ordered")
    return sha256_bytes(canonical_json_bytes(ids))


def _require_utc(value: Any, name: str) -> str:
    checked = _require_string(value, name)
    if not _UTC_PATTERN.fullmatch(checked):
        raise LockedEvaluationError(f"{name} must be whole-second UTC")
    try:
        datetime.strptime(checked, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise LockedEvaluationError(f"{name} is not a real UTC timestamp") from exc
    return checked


def max_canonical_utc(*values: Any) -> str:
    if not values:
        raise LockedEvaluationError("at least one UTC timestamp is required")
    return max(
        _require_utc(value, f"UTC timestamp[{index}]")
        for index, value in enumerate(values)
    )


def normalize_blob_prefix(prefix: str) -> str:
    checked = _require_string(prefix, "Blob prefix")
    if "\\" in checked or "\x00" in checked:
        raise LockedEvaluationError("Blob prefix must use forward slashes")
    if checked != checked.strip("/") or "//" in checked:
        raise LockedEvaluationError("Blob prefix is not normalized")
    parts = checked.split("/")
    if any(
        part in {"", ".", ".."}
        or any(ord(character) < 32 for character in part)
        for part in parts
    ):
        raise LockedEvaluationError("Blob prefix has an invalid segment")
    return checked


def validate_registered_parent_prefix(prefix: str) -> str:
    checked = normalize_blob_prefix(prefix)
    match = _REGISTERED_PARENT_PATTERN.fullmatch(checked)
    if match is None:
        raise LockedEvaluationError("sealed parent prefix is not registered")
    try:
        datetime.strptime(match.group("timestamp"), "%Y%m%dT%H%M%SZ")
    except ValueError as exc:
        raise LockedEvaluationError(
            "sealed parent prefix has an invalid timestamp"
        ) from exc
    return checked


def validate_authorization_id(value: str) -> str:
    checked = _require_string(value, "authorization_id")
    if not _AUTHORIZATION_ID_PATTERN.fullmatch(checked):
        raise LockedEvaluationError("authorization_id has invalid syntax")
    return checked


def evaluation_prefixes(parent_prefix: str, authorization_id: str) -> dict[str, str]:
    parent = validate_registered_parent_prefix(parent_prefix)
    authorization = validate_authorization_id(authorization_id)
    return {
        leaf: f"{parent}/{leaf}/{authorization}"
        for leaf in ("predictions", "scores", "state", "visibility")
    }


def validate_exact_evaluation_prefix(
    value: str, parent_prefix: str, authorization_id: str, leaf: str
) -> str:
    expected = evaluation_prefixes(parent_prefix, authorization_id)
    if leaf not in expected:
        raise LockedEvaluationError("evaluation prefix leaf is not registered")
    checked = normalize_blob_prefix(value)
    if checked != expected[leaf]:
        raise LockedEvaluationError(
            f"{leaf} prefix must equal the authorization-specific prefix"
        )
    return checked


_ATTEMPT_LEAVES = {
    ("P", "none"): ("predictions", "visibility"),
    ("P", "infrastructure_pre_input"): ("predictions", "visibility"),
    # Adoption is a parser-disabled control-plane attempt.  It owns no output
    # leaf and may only bind an already-complete producer attempt.
    ("P", "prediction_adoption"): (),
    ("E", "none"): ("scores", "visibility"),
    ("E", "scorer_infrastructure"): ("scores", "visibility"),
    ("E", "verification_only"): ("visibility",),
}
_ATTEMPT_OUTPUT_LEAVES = {
    ("P", "none"): "predictions",
    ("P", "infrastructure_pre_input"): "predictions",
    ("E", "none"): "scores",
    ("E", "scorer_infrastructure"): "scores",
}


def _validate_attempt_binding(
    stage: Any, retry_kind: Any, execution_id: Any
) -> tuple[str, str, str]:
    checked_stage = _require_enum(stage, ("P", "E"), "attempt stage")
    checked_retry = _require_enum(
        retry_kind,
        ("none", *STATE_RETRY_RECEIPT_FILENAMES, "prediction_adoption"),
        "attempt retry kind",
    )
    checked_execution = _require_string(
        execution_id, "attempt execution_id", maximum=512
    )
    _validate_json_value(checked_execution, "attempt execution_id")
    if (checked_stage, checked_retry) not in _ATTEMPT_LEAVES:
        raise LockedEvaluationError(
            "attempt stage/retry combination is not registered"
        )
    return checked_stage, checked_retry, checked_execution


def attempt_binding_sha256(
    stage: str, retry_kind: str, execution_id: str
) -> str:
    """Hash the canonical stage/retry/execution binding used by retry prefixes."""

    checked_stage, checked_retry, checked_execution = _validate_attempt_binding(
        stage, retry_kind, execution_id
    )
    return sha256_bytes(
        canonical_json_bytes(
            {
                "stage": checked_stage,
                "retry_kind": checked_retry,
                "execution_id": checked_execution,
            }
        )
    )


def attempt_prefix_sha256(value: str) -> str:
    """Hash one canonical effective attempt prefix."""

    return sha256_bytes(normalize_blob_prefix(value).encode("utf-8"))


def derive_attempt_prefix(
    parent_prefix: str,
    authorization_id: str,
    leaf: str,
    stage: str,
    retry_kind: str,
    execution_id: str,
) -> str:
    """Derive one exact primary or retry-attempt prefix."""

    roots = evaluation_prefixes(parent_prefix, authorization_id)
    checked_leaf = _require_enum(
        leaf, ("predictions", "scores", "state", "visibility"), "attempt leaf"
    )
    checked_stage, checked_retry, checked_execution = _validate_attempt_binding(
        stage, retry_kind, execution_id
    )
    if checked_leaf == "state":
        return roots["state"]
    if checked_leaf not in _ATTEMPT_LEAVES[(checked_stage, checked_retry)]:
        raise LockedEvaluationError("attempt leaf is not registered for stage/retry")
    if checked_retry == "none":
        return roots[checked_leaf]
    binding_sha256 = attempt_binding_sha256(
        checked_stage, checked_retry, checked_execution
    )
    return f"{roots[checked_leaf]}/attempts/{checked_retry}/{binding_sha256}"


def validate_exact_attempt_prefix(
    value: str,
    parent_prefix: str,
    authorization_id: str,
    leaf: str,
    stage: str,
    retry_kind: str,
    execution_id: str,
) -> str:
    """Require a prefix to equal its recomputed canonical attempt prefix."""

    checked = normalize_blob_prefix(value)
    expected = derive_attempt_prefix(
        parent_prefix,
        authorization_id,
        leaf,
        stage,
        retry_kind,
        execution_id,
    )
    if checked != expected:
        raise LockedEvaluationError("attempt prefix is not the exact derived prefix")
    return checked


def evaluation_attempt_prefixes(
    parent_prefix: str,
    authorization_id: str,
    stage: str,
    retry_kind: str,
    execution_id: str,
) -> dict[str, str]:
    """Return every registered output prefix plus the invariant state root."""

    checked_stage, checked_retry, checked_execution = _validate_attempt_binding(
        stage, retry_kind, execution_id
    )
    result = {
        leaf: derive_attempt_prefix(
            parent_prefix,
            authorization_id,
            leaf,
            checked_stage,
            checked_retry,
            checked_execution,
        )
        for leaf in _ATTEMPT_LEAVES[(checked_stage, checked_retry)]
    }
    result["state"] = evaluation_prefixes(parent_prefix, authorization_id)["state"]
    return result


def derive_effective_launcher_attempt_prefixes(
    *,
    parent_prefix: str,
    authorization_id: str,
    stage: str,
    retry_kind: str,
    execution_id: str,
    verification_only: bool,
    authenticated_prediction_attempt: Mapping[str, Any] | None,
    authenticated_scoring_attempt: Mapping[str, Any] | None,
) -> dict[str, str]:
    """Recompute every effective runner prefix from authenticated identities."""

    if type(verification_only) is not bool:
        raise LockedEvaluationError(
            "launcher verification-only control must be a boolean"
        )
    current = evaluation_attempt_prefixes(
        parent_prefix,
        authorization_id,
        stage,
        retry_kind,
        execution_id,
    )

    def checked_attempt(
        record: Mapping[str, Any] | None,
        *,
        expected_stage: str,
        allowed_retry_kinds: Sequence[str],
        output_leaf: str,
    ) -> dict[str, Any]:
        if not isinstance(record, Mapping):
            raise LockedEvaluationError(
                f"authenticated {output_leaf} attempt is missing"
            )
        kind = _require_enum(
            record.get("retry_kind"),
            allowed_retry_kinds,
            f"authenticated {output_leaf} retry kind",
        )
        identity = _require_string(
            record.get("execution_id"),
            f"authenticated {output_leaf} execution ID",
            maximum=512,
        )
        if record.get("stage") != expected_stage:
            raise LockedEvaluationError(
                f"authenticated {output_leaf} stage differs"
            )
        output_prefix = derive_attempt_prefix(
            parent_prefix,
            authorization_id,
            output_leaf,
            expected_stage,
            kind,
            identity,
        )
        visibility_prefix = derive_attempt_prefix(
            parent_prefix,
            authorization_id,
            "visibility",
            expected_stage,
            kind,
            identity,
        )
        if (
            record.get(f"{output_leaf}_prefix") != output_prefix
            or record.get(f"{output_leaf}_prefix_sha256")
            != attempt_prefix_sha256(output_prefix)
            or record.get("visibility_prefix") != visibility_prefix
            or record.get("visibility_prefix_sha256")
            != attempt_prefix_sha256(visibility_prefix)
            or record.get("attempt_binding_sha256")
            != attempt_binding_sha256(expected_stage, kind, identity)
        ):
            raise LockedEvaluationError(
                f"authenticated {output_leaf} attempt prefix differs"
            )
        return dict(record)

    if stage == "P" and retry_kind == "prediction_adoption":
        if verification_only:
            raise LockedEvaluationError(
                "prediction adoption cannot use verification-only routing"
            )
        prediction = checked_attempt(
            authenticated_prediction_attempt,
            expected_stage="P",
            allowed_retry_kinds=("none", "infrastructure_pre_input"),
            output_leaf="predictions",
        )
        predictions_prefix = prediction["predictions_prefix"]
        visibility_prefix = prediction["visibility_prefix"]
        scores_prefix = ""
        prediction_retry_kind = prediction["retry_kind"]
        prediction_execution_id = prediction["execution_id"]
        scoring_retry_kind = ""
        scoring_execution_id = ""
    elif stage == "P":
        if verification_only:
            raise LockedEvaluationError(
                "Stage P cannot use verification-only prefix routing"
            )
        predictions_prefix = current["predictions"]
        scores_prefix = ""
        prediction_retry_kind = ""
        prediction_execution_id = ""
        scoring_retry_kind = ""
        scoring_execution_id = ""
    elif stage == "E":
        prediction = checked_attempt(
            authenticated_prediction_attempt,
            expected_stage="P",
            allowed_retry_kinds=("none", "infrastructure_pre_input"),
            output_leaf="predictions",
        )
        predictions_prefix = prediction["predictions_prefix"]
        prediction_retry_kind = prediction["retry_kind"]
        prediction_execution_id = prediction["execution_id"]
        if verification_only:
            if retry_kind != "verification_only":
                raise LockedEvaluationError(
                    "verification prefix routing requires its retry kind"
                )
            scoring = checked_attempt(
                authenticated_scoring_attempt,
                expected_stage="E",
                allowed_retry_kinds=("none", "scorer_infrastructure"),
                output_leaf="scores",
            )
            scores_prefix = scoring["scores_prefix"]
            scoring_retry_kind = scoring["retry_kind"]
            scoring_execution_id = scoring["execution_id"]
        else:
            if retry_kind not in {"none", "scorer_infrastructure"}:
                raise LockedEvaluationError(
                    "Stage E prefix routing retry kind is invalid"
                )
            scores_prefix = current["scores"]
            scoring_retry_kind = ""
            scoring_execution_id = ""
    else:
        raise LockedEvaluationError("launcher attempt stage is invalid")
    if not (stage == "P" and retry_kind == "prediction_adoption"):
        visibility_prefix = current["visibility"]
    return {
        "predictions_prefix": predictions_prefix,
        "scores_prefix": scores_prefix,
        "visibility_prefix": visibility_prefix,
        "predictions_attempt_prefix_sha256": attempt_prefix_sha256(
            predictions_prefix
        ),
        "scores_attempt_prefix_sha256": (
            "" if not scores_prefix else attempt_prefix_sha256(scores_prefix)
        ),
        "visibility_attempt_prefix_sha256": attempt_prefix_sha256(
            visibility_prefix
        ),
        "current_attempt_binding_sha256": attempt_binding_sha256(
            stage, retry_kind, execution_id
        ),
        "authenticated_prediction_retry_kind": prediction_retry_kind,
        "authenticated_prediction_execution_id": prediction_execution_id,
        "authenticated_scoring_retry_kind": scoring_retry_kind,
        "authenticated_scoring_execution_id": scoring_execution_id,
    }


def validate_scoring_attempt_binding(
    *,
    parent_prefix: str,
    authorization_id: str,
    scores_prefix: str,
    scoring_retry_kind: str,
    scoring_execution_id: str,
    retry_receipt_sha256: str | None,
) -> dict[str, Any]:
    """Validate the one scoring attempt that may own score bytes."""

    checked_retry = _require_enum(
        scoring_retry_kind,
        ("none", "scorer_infrastructure"),
        "scoring retry kind",
    )
    checked_execution = _require_string(
        scoring_execution_id, "scoring execution ID", maximum=512
    )
    checked_scores = validate_exact_attempt_prefix(
        scores_prefix,
        parent_prefix,
        authorization_id,
        "scores",
        "E",
        checked_retry,
        checked_execution,
    )
    if checked_retry == "none":
        if retry_receipt_sha256 is not None:
            raise LockedEvaluationError(
                "primary scoring attempt cannot bind a retry receipt"
            )
        checked_retry_receipt = None
    else:
        checked_retry_receipt = _require_sha256(
            retry_receipt_sha256, "scoring retry receipt SHA-256"
        )
    return {
        "scores_prefix": checked_scores,
        "scoring_retry_kind": checked_retry,
        "scoring_execution_id": checked_execution,
        "retry_receipt_sha256": checked_retry_receipt,
    }


_ATTEMPT_MEMBER_FIELDS = frozenset({"blob_name", "size", "sha256", "etag"})
_ATTEMPT_DESCRIPTOR_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "stage",
        "retry_kind",
        "execution_id",
        "attempt_prefixes",
        "members",
        "membership_sha256",
    }
)
_ABANDONED_ATTEMPT_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "prior_stage",
        "prior_retry_kind",
        "prior_execution_id",
        "prior_actor",
        "abandoned_prefixes",
        "abandoned_members",
        "abandoned_membership_sha256",
        "current_retry_kind",
        "current_execution_id",
        "current_actor",
        "current_output_prefix",
        "current_visibility_prefix",
        "prior_state_receipt_sha256",
        "created_utc",
    }
)


def _attempt_data_prefixes(
    parent_prefix: str,
    authorization_id: str,
    stage: str,
    retry_kind: str,
    execution_id: str,
) -> dict[str, str]:
    prefixes = evaluation_attempt_prefixes(
        parent_prefix,
        authorization_id,
        stage,
        retry_kind,
        execution_id,
    )
    prefixes.pop("state")
    return prefixes


def _canonical_attempt_members(
    members: Sequence[Mapping[str, Any]],
    *,
    parent_prefix: str,
    authorization_id: str,
    allowed_prefixes: Mapping[str, str],
    name: str,
) -> list[dict[str, Any]]:
    if isinstance(members, (str, bytes)) or not isinstance(members, Sequence):
        raise LockedEvaluationError(f"{name} must be a sequence")
    roots = evaluation_prefixes(parent_prefix, authorization_id)
    if (
        not isinstance(allowed_prefixes, Mapping)
        or not allowed_prefixes
        or any(
            leaf not in {"predictions", "scores", "visibility"}
            for leaf in allowed_prefixes
        )
    ):
        raise LockedEvaluationError(f"{name} prefixes are invalid")
    canonical: list[dict[str, Any]] = []
    for index, member in enumerate(members):
        _require_exact_fields(
            member, _ATTEMPT_MEMBER_FIELDS, f"{name}[{index}]"
        )
        blob_name = normalize_blob_prefix(member["blob_name"])
        if blob_name.startswith(f"{roots['state']}/"):
            raise LockedEvaluationError(f"{name} contains a state-prefix member")
        matching_prefixes = [
            prefix
            for prefix in allowed_prefixes.values()
            if blob_name.startswith(f"{prefix}/")
        ]
        if len(matching_prefixes) != 1:
            raise LockedEvaluationError(f"{name} contains an out-of-prefix member")
        relative_name = blob_name[len(matching_prefixes[0]) + 1 :]
        is_primary_prefix = matching_prefixes[0] in roots.values()
        if not relative_name or (
            is_primary_prefix
            and (
                relative_name == "attempts"
                or relative_name.startswith("attempts/")
            )
        ):
            raise LockedEvaluationError(
                f"{name} member aliases the reserved attempt subtree"
            )
        etag = _require_string(
            member["etag"], f"{name}[{index}] ETag", maximum=2048
        )
        _validate_json_value(etag, f"{name}[{index}] ETag")
        canonical.append(
            {
                "blob_name": blob_name,
                "size": _require_int(
                    member["size"], f"{name}[{index}] size", minimum=0
                ),
                "sha256": _require_sha256(
                    member["sha256"], f"{name}[{index}] SHA-256"
                ),
                "etag": etag,
            }
        )
    canonical.sort(key=lambda item: item["blob_name"])
    names = [item["blob_name"] for item in canonical]
    if len(names) != len(set(names)):
        raise LockedEvaluationError(f"{name} contains duplicate Blob names")
    return canonical


def attempt_membership_sha256(members: Sequence[Mapping[str, Any]]) -> str:
    """Hash already-canonical, exactly sorted attempt member metadata."""

    if type(members) is not list:
        raise LockedEvaluationError("attempt membership must be an exact list")
    canonical: list[dict[str, Any]] = []
    for index, member in enumerate(members):
        _require_exact_fields(
            member, _ATTEMPT_MEMBER_FIELDS, f"attempt membership[{index}]"
        )
        canonical.append(
            {
                "blob_name": normalize_blob_prefix(member["blob_name"]),
                "size": _require_int(
                    member["size"],
                    f"attempt membership[{index}] size",
                    minimum=0,
                ),
                "sha256": _require_sha256(
                    member["sha256"],
                    f"attempt membership[{index}] SHA-256",
                ),
                "etag": _require_string(
                    member["etag"],
                    f"attempt membership[{index}] ETag",
                    maximum=2048,
                ),
            }
        )
    if not exact_json_equal(canonical, members):
        raise LockedEvaluationError("attempt membership metadata is not canonical")
    names = [item["blob_name"] for item in canonical]
    if names != sorted(set(names)):
        raise LockedEvaluationError("attempt membership is not exact and sorted")
    return sha256_bytes(canonical_json_bytes(canonical))


def build_attempt_membership_descriptor(
    *,
    parent_prefix: str,
    authorization_id: str,
    stage: str,
    retry_kind: str,
    execution_id: str,
    members: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build an explicit, closed membership descriptor for one attempt."""

    parent = validate_registered_parent_prefix(parent_prefix)
    authorization = validate_authorization_id(authorization_id)
    checked_stage, checked_retry, checked_execution = _validate_attempt_binding(
        stage, retry_kind, execution_id
    )
    prefixes = _attempt_data_prefixes(
        parent,
        authorization,
        checked_stage,
        checked_retry,
        checked_execution,
    )
    canonical_members = _canonical_attempt_members(
        members,
        parent_prefix=parent,
        authorization_id=authorization,
        allowed_prefixes=prefixes,
        name="attempt descriptor members",
    )
    return {
        "schema_version": ATTEMPT_DESCRIPTOR_SCHEMA_VERSION,
        "authorization_id": authorization,
        "registered_parent_prefix": parent,
        "stage": checked_stage,
        "retry_kind": checked_retry,
        "execution_id": checked_execution,
        "attempt_prefixes": prefixes,
        "members": canonical_members,
        "membership_sha256": attempt_membership_sha256(canonical_members),
    }


def validate_attempt_membership_descriptor(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate an attempt membership descriptor without trusting its paths."""

    _require_exact_fields(
        record, _ATTEMPT_DESCRIPTOR_FIELDS, "attempt membership descriptor"
    )
    if record["schema_version"] != ATTEMPT_DESCRIPTOR_SCHEMA_VERSION:
        raise LockedEvaluationError("attempt membership descriptor schema is invalid")
    if (
        type(record["members"]) is not list
        or type(record["attempt_prefixes"]) is not dict
    ):
        raise LockedEvaluationError("attempt membership descriptor types are invalid")
    try:
        rebuilt = build_attempt_membership_descriptor(
            parent_prefix=record["registered_parent_prefix"],
            authorization_id=record["authorization_id"],
            stage=record["stage"],
            retry_kind=record["retry_kind"],
            execution_id=record["execution_id"],
            members=record["members"],
        )
    except (KeyError, TypeError, LockedEvaluationError):
        raise LockedEvaluationError(
            "attempt membership descriptor bindings are invalid"
        ) from None
    if not exact_json_equal(dict(record), rebuilt):
        raise LockedEvaluationError(
            "attempt membership descriptor differs from its derived binding"
        )
    return rebuilt


def attempt_membership_descriptor_sha256(record: Mapping[str, Any]) -> str:
    checked = validate_attempt_membership_descriptor(record)
    return sha256_bytes(canonical_json_bytes(checked))


def build_abandoned_attempt_record(
    *,
    parent_prefix: str,
    authorization_id: str,
    prior_stage: str,
    prior_retry_kind: str,
    prior_execution_id: str,
    prior_actor: str,
    abandoned_members: Sequence[Mapping[str, Any]],
    current_retry_kind: str,
    current_execution_id: str,
    current_actor: str,
    prior_state_receipt_sha256: str,
    created_utc: str,
) -> dict[str, Any]:
    """Bind one immutable partial attempt to its distinct recovery attempt."""

    parent = validate_registered_parent_prefix(parent_prefix)
    authorization = validate_authorization_id(authorization_id)
    checked_stage, checked_prior_retry, checked_prior_execution = (
        _validate_attempt_binding(
            prior_stage, prior_retry_kind, prior_execution_id
        )
    )
    checked_current_stage, checked_current_retry, checked_current_execution = (
        _validate_attempt_binding(
            checked_stage, current_retry_kind, current_execution_id
        )
    )
    if (
        checked_current_retry
        not in {"infrastructure_pre_input", "scorer_infrastructure"}
        or checked_prior_retry not in {"none", checked_current_retry}
        or checked_current_stage != checked_stage
    ):
        raise LockedEvaluationError(
            "abandoned attempt retry relationship is not registered"
        )
    if checked_prior_execution == checked_current_execution:
        raise LockedEvaluationError(
            "retry execution must differ from its abandoned execution"
        )
    abandoned_prefixes = _attempt_data_prefixes(
        parent,
        authorization,
        checked_stage,
        checked_prior_retry,
        checked_prior_execution,
    )
    current_prefixes = _attempt_data_prefixes(
        parent,
        authorization,
        checked_stage,
        checked_current_retry,
        checked_current_execution,
    )
    output_leaf = _ATTEMPT_OUTPUT_LEAVES.get(
        (checked_stage, checked_current_retry)
    )
    if output_leaf is None:
        raise LockedEvaluationError("abandoned attempt has no registered output leaf")
    canonical_members = _canonical_attempt_members(
        abandoned_members,
        parent_prefix=parent,
        authorization_id=authorization,
        allowed_prefixes=abandoned_prefixes,
        name="abandoned attempt members",
    )
    return {
        "schema_version": ABANDONED_ATTEMPT_SCHEMA_VERSION,
        "authorization_id": authorization,
        "registered_parent_prefix": parent,
        "prior_stage": checked_stage,
        "prior_retry_kind": checked_prior_retry,
        "prior_execution_id": checked_prior_execution,
        "prior_actor": _require_string(
            prior_actor, "abandoned attempt prior actor", maximum=512
        ),
        "abandoned_prefixes": abandoned_prefixes,
        "abandoned_members": canonical_members,
        "abandoned_membership_sha256": attempt_membership_sha256(
            canonical_members
        ),
        "current_retry_kind": checked_current_retry,
        "current_execution_id": checked_current_execution,
        "current_actor": _require_string(
            current_actor, "abandoned attempt current actor", maximum=512
        ),
        "current_output_prefix": current_prefixes[output_leaf],
        "current_visibility_prefix": current_prefixes["visibility"],
        "prior_state_receipt_sha256": _require_sha256(
            prior_state_receipt_sha256,
            "abandoned attempt prior state receipt SHA-256",
        ),
        "created_utc": _require_utc(
            created_utc, "abandoned attempt created_utc"
        ),
    }


def validate_abandoned_attempt_record(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild and validate every abandoned-attempt identity and member binding."""

    _require_exact_fields(
        record, _ABANDONED_ATTEMPT_FIELDS, "abandoned attempt record"
    )
    if record["schema_version"] != ABANDONED_ATTEMPT_SCHEMA_VERSION:
        raise LockedEvaluationError("abandoned attempt schema is invalid")
    if (
        type(record["abandoned_members"]) is not list
        or type(record["abandoned_prefixes"]) is not dict
    ):
        raise LockedEvaluationError("abandoned attempt record types are invalid")
    try:
        rebuilt = build_abandoned_attempt_record(
            parent_prefix=record["registered_parent_prefix"],
            authorization_id=record["authorization_id"],
            prior_stage=record["prior_stage"],
            prior_retry_kind=record["prior_retry_kind"],
            prior_execution_id=record["prior_execution_id"],
            prior_actor=record["prior_actor"],
            abandoned_members=record["abandoned_members"],
            current_retry_kind=record["current_retry_kind"],
            current_execution_id=record["current_execution_id"],
            current_actor=record["current_actor"],
            prior_state_receipt_sha256=record["prior_state_receipt_sha256"],
            created_utc=record["created_utc"],
        )
    except (KeyError, TypeError, LockedEvaluationError):
        raise LockedEvaluationError(
            "abandoned attempt immutable bindings are invalid"
        ) from None
    if not exact_json_equal(dict(record), rebuilt):
        raise LockedEvaluationError(
            "abandoned attempt record differs from its derived binding"
        )
    return rebuilt


def abandoned_attempt_sha256(record: Mapping[str, Any]) -> str:
    checked = validate_abandoned_attempt_record(record)
    return sha256_bytes(canonical_json_bytes(checked))


def abandoned_attempt_blob_name(record: Mapping[str, Any]) -> str:
    checked = validate_abandoned_attempt_record(record)
    return derive_abandoned_attempt_blob_name(
        checked["registered_parent_prefix"],
        checked["authorization_id"],
        checked["prior_stage"],
        checked["current_retry_kind"],
        checked["current_execution_id"],
    )


def derive_abandoned_attempt_blob_name(
    parent_prefix: str,
    authorization_id: str,
    stage: str,
    retry_kind: str,
    execution_id: str,
) -> str:
    checked_retry = _require_enum(
        retry_kind,
        tuple(STATE_RETRY_RECEIPT_FILENAMES),
        "abandoned attempt retry kind",
    )
    if checked_retry not in {
        "infrastructure_pre_input",
        "scorer_infrastructure",
    }:
        raise LockedEvaluationError(
            "abandoned attempt Blob requires an infrastructure retry"
        )
    visibility_prefix = derive_attempt_prefix(
        parent_prefix,
        authorization_id,
        "visibility",
        stage,
        checked_retry,
        execution_id,
    )
    return f"{visibility_prefix}/{ABANDONED_ATTEMPT_FILENAME}"


def validate_exact_abandoned_attempt_blob_name(
    value: str, record: Mapping[str, Any]
) -> str:
    checked = normalize_blob_prefix(value)
    if checked != abandoned_attempt_blob_name(record):
        raise LockedEvaluationError("abandoned attempt Blob path is not exact")
    return checked


def expected_authorization_attempt_membership(
    parent_prefix: str,
    authorization_id: str,
    attempts: Sequence[Mapping[str, Any]],
    *,
    primary_membership: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, set[str]]:
    """Compute closed authorization membership only from explicit descriptors."""

    parent = validate_registered_parent_prefix(parent_prefix)
    authorization = validate_authorization_id(authorization_id)
    roots = evaluation_prefixes(parent, authorization)
    expected = {leaf: set() for leaf in roots}
    if primary_membership is not None:
        _require_exact_fields(
            primary_membership, roots, "primary authorization membership"
        )
        for leaf, members in primary_membership.items():
            if isinstance(members, (str, bytes)) or not isinstance(
                members, Iterable
            ):
                raise LockedEvaluationError(
                    "primary authorization membership leaf is invalid"
                )
            root = roots[leaf]
            for member in members:
                checked = normalize_blob_prefix(member)
                if not checked.startswith(f"{root}/"):
                    raise LockedEvaluationError(
                        "primary authorization member is outside its leaf"
                    )
                relative_name = checked[len(root) + 1 :]
                if (
                    not relative_name
                    or relative_name == "attempts"
                    or relative_name.startswith("attempts/")
                ):
                    raise LockedEvaluationError(
                        "nested attempt members require an explicit descriptor"
                    )
                expected[leaf].add(checked)
    if isinstance(attempts, (str, bytes)) or not isinstance(attempts, Sequence):
        raise LockedEvaluationError(
            "attempt descriptors must be an explicit sequence"
        )
    explicit_members: list[str] = []
    for item in attempts:
        if not isinstance(item, Mapping):
            raise LockedEvaluationError("attempt descriptor must be an object")
        schema_version = item.get("schema_version")
        if schema_version == ATTEMPT_DESCRIPTOR_SCHEMA_VERSION:
            descriptor = validate_attempt_membership_descriptor(item)
            if (
                descriptor["registered_parent_prefix"] != parent
                or descriptor["authorization_id"] != authorization
            ):
                raise LockedEvaluationError(
                    "attempt descriptor authorization binding differs"
                )
            explicit_members.extend(
                member["blob_name"] for member in descriptor["members"]
            )
        elif schema_version == ABANDONED_ATTEMPT_SCHEMA_VERSION:
            abandoned = validate_abandoned_attempt_record(item)
            if (
                abandoned["registered_parent_prefix"] != parent
                or abandoned["authorization_id"] != authorization
            ):
                raise LockedEvaluationError(
                    "abandoned attempt authorization binding differs"
                )
            explicit_members.extend(
                member["blob_name"] for member in abandoned["abandoned_members"]
            )
            explicit_members.append(abandoned_attempt_blob_name(abandoned))
        else:
            raise LockedEvaluationError("attempt descriptor schema is not registered")
    for member in explicit_members:
        matching_leaves = [
            leaf
            for leaf, root in roots.items()
            if member.startswith(f"{root}/")
        ]
        if len(matching_leaves) != 1 or matching_leaves[0] == "state":
            raise LockedEvaluationError(
                "explicit attempt member is outside an output leaf"
            )
        expected[matching_leaves[0]].add(member)
    return expected


derive_evaluation_attempt_prefix = derive_attempt_prefix
validate_evaluation_attempt_prefix = validate_exact_attempt_prefix
canonical_attempt_prefix = derive_attempt_prefix
validate_attempt_prefix = validate_exact_attempt_prefix
build_attempt_descriptor = build_attempt_membership_descriptor
validate_attempt_descriptor = validate_attempt_membership_descriptor
abandoned_attempt_membership_sha256 = attempt_membership_sha256
abandoned_attempt_record_sha256 = abandoned_attempt_sha256


def _require_azure_name(value: Any, name: str) -> str:
    checked = _require_string(value, name)
    if (
        checked != checked.strip()
        or any(ord(character) < 32 for character in checked)
        or not _AZURE_NAME_PATTERN.fullmatch(checked)
    ):
        raise LockedEvaluationError(f"{name} is not a canonical Azure name")
    return checked


def _require_azure_resource_id(
    value: Any,
    name: str,
    *,
    subscription_id: str,
    resource_group: str,
    provider: str,
    tail: str,
) -> str:
    checked = _require_string(value, name)
    if checked != checked.strip() or "\r" in checked or "\n" in checked:
        raise LockedEvaluationError(f"{name} is not a canonical resource ID")
    match = _AZURE_RESOURCE_ID_PATTERN.fullmatch(checked)
    if (
        match is None
        or match.group("subscription").casefold() != subscription_id.casefold()
        or match.group("resource_group").casefold() != resource_group.casefold()
        or match.group("provider").casefold() != provider.casefold()
        or match.group("tail").casefold() != tail.casefold()
    ):
        raise LockedEvaluationError(f"{name} does not identify the exact resource")
    return checked


def validate_runtime_source_bindings(
    value: Any,
    *,
    launcher_sha256: str | None = None,
    launcher_git_blob_oid: str | None = None,
) -> dict[str, dict[str, str]]:
    if not isinstance(value, Mapping) or set(value) != set(
        RUNTIME_SOURCE_BINDING_PATHS
    ):
        raise LockedEvaluationError("runtime source-file membership is not exact")
    checked: dict[str, dict[str, str]] = {}
    for path in RUNTIME_SOURCE_BINDING_PATHS:
        binding = value[path]
        _require_exact_fields(
            binding, {"git_blob_oid", "sha256"}, f"source binding {path}"
        )
        checked[path] = {
            "git_blob_oid": _require_commit(
                binding["git_blob_oid"], f"source binding {path} Git blob"
            ),
            "sha256": _require_sha256(
                binding["sha256"], f"source binding {path} SHA-256"
            ),
        }
    launcher = checked["infra/azure/scripts/10_run_parser_v2_locked_eval.sh"]
    if launcher_sha256 is not None and launcher["sha256"] != _require_sha256(
        launcher_sha256, "expected launcher SHA-256"
    ):
        raise LockedEvaluationError("runtime launcher content binding mismatch")
    if (
        launcher_git_blob_oid is not None
        and launcher["git_blob_oid"]
        != _require_commit(launcher_git_blob_oid, "expected launcher Git blob")
    ):
        raise LockedEvaluationError("runtime launcher Git binding mismatch")
    return checked


def _require_coordination_internal_id(value: Any) -> str:
    internal_id = _require_string(value, "coordination zone internal ID")
    if _AZURE_CLIENT_ID_PATTERN.fullmatch(internal_id):
        return internal_id.casefold()
    if not _AZURE_OPAQUE_INTERNAL_ID_PATTERN.fullmatch(internal_id):
        raise LockedEvaluationError("coordination zone internal ID is invalid")
    try:
        decoded = base64.b64decode(internal_id, validate=True)
    except (binascii.Error, ValueError):
        raise LockedEvaluationError(
            "coordination zone internal ID is invalid"
        ) from None
    if (
        len(decoded) < 16
        or base64.b64encode(decoded).decode("ascii") != internal_id
    ):
        raise LockedEvaluationError("coordination zone internal ID is invalid")
    return internal_id


def validate_coordination_binding(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        {
            "schema_version",
            "zone_name",
            "zone_resource_id",
            "zone_location",
            "zone_internal_id",
            "private_dns_api_version",
            "record_ttl",
            "expected_vnet_link_count",
            "lock_name",
            "lock_resource_id",
            "lock_level",
            "management_lock_api_version",
        },
        "Private DNS coordination binding",
    )
    zone_name = _require_string(
        value["zone_name"], "coordination zone name"
    ).casefold()
    if not re.fullmatch(
        r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
        r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?",
        zone_name,
        re.ASCII,
    ):
        raise LockedEvaluationError("coordination zone name is invalid")
    if zone_name == "privatelink.blob.core.windows.net":
        raise LockedEvaluationError(
            "coordination zone must not be the Blob private-link zone"
        )
    zone_id = _require_string(
        value["zone_resource_id"], "coordination zone resource ID"
    )
    zone_match = _AZURE_RESOURCE_ID_PATTERN.fullmatch(zone_id)
    if (
        zone_match is None
        or zone_match.group("provider").casefold() != "microsoft.network"
        or zone_match.group("tail").casefold()
        != f"privatednszones/{zone_name}"
    ):
        raise LockedEvaluationError(
            "coordination zone resource ID is not exact"
        )
    internal_id = _require_coordination_internal_id(
        value["zone_internal_id"]
    )
    ttl = value["record_ttl"]
    link_count = value["expected_vnet_link_count"]
    if (
        value["schema_version"] != COORDINATION_BINDING_SCHEMA_VERSION
        or value["zone_location"] != "global"
        or value["private_dns_api_version"]
        != PRIVATE_DNS_RECORD_SET_API_VERSION
        or value["management_lock_api_version"] != MANAGEMENT_LOCK_API_VERSION
        or type(ttl) is not int
        or not 60 <= ttl <= 3600
        or type(link_count) is not int
        or link_count != 0
        or value["lock_level"] != "CanNotDelete"
    ):
        raise LockedEvaluationError(
            "coordination zone immutable controls are invalid"
        )
    lock_name = _require_azure_name(
        value["lock_name"], "coordination management-lock name"
    )
    lock_id = _require_string(
        value["lock_resource_id"], "coordination management-lock resource ID"
    )
    suffix = f"/providers/Microsoft.Authorization/locks/{lock_name}"
    if not lock_id.casefold().endswith(suffix.casefold()):
        raise LockedEvaluationError(
            "coordination management-lock identity is invalid"
        )
    lock_scope = lock_id[: -len(suffix)].casefold()
    zone_parts = zone_id.split("/")
    if lock_scope not in {
        "/".join(zone_parts[:3]).casefold(),
        "/".join(zone_parts[:5]).casefold(),
        zone_id.casefold(),
    }:
        raise LockedEvaluationError(
            "coordination management lock is not inherited or direct"
        )
    checked = {
        "schema_version": COORDINATION_BINDING_SCHEMA_VERSION,
        "zone_name": zone_name,
        "zone_resource_id": zone_id,
        "zone_location": "global",
        "zone_internal_id": internal_id,
        "private_dns_api_version": PRIVATE_DNS_RECORD_SET_API_VERSION,
        "record_ttl": ttl,
        "expected_vnet_link_count": 0,
        "lock_name": lock_name,
        "lock_resource_id": lock_id,
        "lock_level": "CanNotDelete",
        "management_lock_api_version": MANAGEMENT_LOCK_API_VERSION,
    }
    if not exact_json_equal(dict(value), checked):
        raise LockedEvaluationError(
            "Private DNS coordination binding is not canonical"
        )
    return checked


def coordination_binding_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(validate_coordination_binding(value)))


def _claim_domain_sha256(kind: str, binding: Mapping[str, Any]) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": CLAIM_DOMAIN_SCHEMA_VERSION,
                "kind": kind,
                "binding": dict(binding),
            }
        )
    )


def _dns_txt_record_name(kind: str, domain_sha256: str) -> str:
    domain = _require_sha256(domain_sha256, "Private DNS claim domain")
    return f"{kind}-{domain[:32]}.{domain[32:]}"


_IMAGE_BINDING_FIELDS = frozenset(
    {
        "schema_version",
        "source_commit",
        "source_repository_url",
        "remote_source_location",
        "base_image",
        "image_repository",
        "files",
        "source_binding_sha256",
        "build_provenance",
        "build_provenance_sha256",
        "build_run_request_sha256",
        "oci_verification_sha256",
        "oci_verification",
        "staging_image_tag",
        "image_tag",
        "image_digest",
        "image_digest_ref",
        "acr_build_task_run_name",
        "acr_build_task_run_resource_id",
        "acr_build_run_id",
        "coordination_binding",
        "coordination_binding_sha256",
        "build_slot",
        "historical_finalization_supported",
        "changeable_attributes",
        "cpu_only",
        "gpu",
        "stage_p_and_e_same_digest",
        "mutable_latest_forbidden",
    }
)


def _validate_image_source_binding(record: Mapping[str, Any]) -> dict[str, Any]:
    _require_exact_fields(
        record,
        {
            "schema_version",
            "source_commit",
            "source_repository_url",
            "remote_source_location",
            "base_image",
            "image_repository",
            "files",
        },
        "image source binding",
    )
    if record["schema_version"] != BUILD_SOURCE_BINDING_SCHEMA_VERSION:
        raise LockedEvaluationError("image source-binding schema is invalid")
    commit = _require_commit(record["source_commit"], "image source commit")
    repository_url = _require_string(
        record["source_repository_url"], "image source repository URL"
    )
    if repository_url != "https://github.com/Alanjiao1988/J-space-observation.git":
        raise LockedEvaluationError("image source repository is not approved")
    source_location = _require_string(
        record["remote_source_location"], "image remote source location"
    )
    if source_location != f"{repository_url}#{commit}":
        raise LockedEvaluationError("image remote source does not bind the exact commit")
    if record["base_image"] != PARSER_V2_EVAL_BASE_IMAGE:
        raise LockedEvaluationError("image source base is not the approved exact pin")
    repository = _require_string(
        record["image_repository"], "image repository"
    )
    if not _IMAGE_REPOSITORY_PATTERN.fullmatch(repository):
        raise LockedEvaluationError("image repository is invalid")
    raw_files = record["files"]
    if not isinstance(raw_files, Mapping) or set(raw_files) != set(
        IMAGE_BINDING_SOURCE_PATHS
    ):
        raise LockedEvaluationError("image source-file membership is not exact")
    files: dict[str, dict[str, Any]] = {}
    for path in IMAGE_BINDING_SOURCE_PATHS:
        binding = raw_files[path]
        _require_exact_fields(
            binding,
            {"git_blob_oid", "sha256", "size"},
            f"image source binding {path}",
        )
        oid = _require_string(
            binding["git_blob_oid"], f"image source binding {path} Git blob"
        )
        size = binding["size"]
        if (
            not _GIT_OBJECT_ID_PATTERN.fullmatch(oid)
            or set(oid) == {"0"}
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
        ):
            raise LockedEvaluationError(
                f"image source binding {path} metadata is invalid"
            )
        files[path] = {
            "git_blob_oid": oid,
            "sha256": _require_sha256(
                binding["sha256"], f"image source binding {path} SHA-256"
            ),
            "size": size,
        }
    return {
        "schema_version": BUILD_SOURCE_BINDING_SCHEMA_VERSION,
        "source_commit": commit,
        "source_repository_url": repository_url,
        "remote_source_location": source_location,
        "base_image": PARSER_V2_EVAL_BASE_IMAGE,
        "image_repository": repository,
        "files": files,
    }


def _validate_image_build_provenance(
    value: Mapping[str, Any],
    *,
    source_binding: Mapping[str, Any],
    expected_sha256: str,
) -> dict[str, Any]:
    _require_exact_fields(
        value,
        {
            "schema_version",
            "source_commit",
            "remote_source",
            "pinned_base_image",
            "acr",
            "source_binding",
            "source_binding_sha256",
            "coordination",
            "build_context",
            "expected_run_request",
            "expected_images",
            "image_config_label",
        },
        "image build provenance",
    )
    if value["schema_version"] != BUILD_PROVENANCE_SCHEMA_VERSION:
        raise LockedEvaluationError("image build-provenance schema is invalid")
    source = _validate_image_source_binding(value["source_binding"])
    if not exact_json_equal(source, dict(source_binding)):
        raise LockedEvaluationError("image provenance source binding differs")
    source_hash = sha256_bytes(canonical_json_bytes(source))
    if value["source_binding_sha256"] != source_hash:
        raise LockedEvaluationError("image provenance source-binding hash differs")
    acr_for_domain = value["acr"]
    _require_exact_fields(
        acr_for_domain,
        {"resource_id", "login_server", "location", "repository"},
        "image provenance ACR",
    )
    acr_resource_id_for_domain = _require_string(
        acr_for_domain["resource_id"], "image provenance ACR ID"
    ).casefold()
    coordination = value["coordination"]
    _require_exact_fields(
        coordination,
        {"binding", "binding_sha256", "build_slot"},
        "image provenance coordination",
    )
    coordination_binding = validate_coordination_binding(
        coordination["binding"]
    )
    coordination_hash = coordination_binding_sha256(coordination_binding)
    _require_exact_fields(
        coordination["build_slot"],
        {"domain_sha256", "record_name"},
        "image provenance build slot",
    )
    build_domain = _claim_domain_sha256(
        "build",
        {
            "source_commit": source["source_commit"],
            "source_binding_sha256": source_hash,
            "acr_resource_id_sha256": sha256_bytes(
                acr_resource_id_for_domain.encode("ascii")
            ),
            "image_repository_sha256": sha256_bytes(
                source["image_repository"].encode("ascii")
            ),
            "base_image_sha256": sha256_bytes(
                source["base_image"].encode("ascii")
            ),
            "coordination_binding_sha256": coordination_hash,
        },
    )
    if not exact_json_equal(
        coordination,
        {
            "binding": coordination_binding,
            "binding_sha256": coordination_hash,
            "build_slot": {
                "domain_sha256": build_domain,
                "record_name": _dns_txt_record_name("build", build_domain),
            },
        },
    ):
        raise LockedEvaluationError(
            "image provenance coordination/build-slot binding differs"
        )
    remote = value["remote_source"]
    _require_exact_fields(
        remote, {"repository_url", "commit", "source_location"}, "image remote source"
    )
    if not exact_json_equal(
        remote,
        {
            "repository_url": source["source_repository_url"],
            "commit": source["source_commit"],
            "source_location": source["remote_source_location"],
        },
    ):
        raise LockedEvaluationError("image provenance remote source differs")
    if (
        value["source_commit"] != source["source_commit"]
        or value["pinned_base_image"] != PARSER_V2_EVAL_BASE_IMAGE
    ):
        raise LockedEvaluationError("image provenance source/base differs")
    acr = value["acr"]
    _require_exact_fields(
        acr,
        {"resource_id", "login_server", "location", "repository"},
        "image provenance ACR",
    )
    resource_id = _require_string(acr["resource_id"], "image provenance ACR ID")
    login_server = _require_string(
        acr["login_server"], "image provenance ACR login server"
    ).casefold()
    location = _require_string(
        acr["location"], "image provenance ACR location"
    ).casefold()
    repository = _require_string(
        acr["repository"], "image provenance ACR repository"
    )
    registry_name = resource_id.rsplit("/", 1)[-1].casefold()
    if (
        not resource_id.casefold().startswith("/subscriptions/")
        or "/providers/microsoft.containerregistry/registries/"
        not in resource_id.casefold()
        or login_server != f"{registry_name}.azurecr.io"
        or not _AZURE_LOCATION_PATTERN.fullmatch(location)
        or repository != source["image_repository"]
    ):
        raise LockedEvaluationError("image provenance ACR binding is invalid")
    context = value["build_context"]
    _require_exact_fields(
        context,
        {"registered_paths", "dockerfile", "dependencies"},
        "image build context",
    )
    dockerfile = context["dockerfile"]
    _require_exact_fields(
        dockerfile, {"path", "git_blob_oid", "sha256", "size"}, "image Dockerfile"
    )
    dependencies = context["dependencies"]
    if (
        not exact_json_equal(
            context["registered_paths"], sorted(IMAGE_BINDING_SOURCE_PATHS)
        )
        or not exact_json_equal(
            dockerfile,
            {
            "path": "Dockerfile.parser-v2-eval",
            **source["files"]["Dockerfile.parser-v2-eval"],
            }
        )
        or not exact_json_equal(
            dependencies,
            [
                {
                    "path": "requirements-parser-v2-eval.txt",
                    **source["files"]["requirements-parser-v2-eval.txt"],
                }
            ],
        )
    ):
        raise LockedEvaluationError("image build context is not exact")
    request = value["expected_run_request"]
    _require_exact_fields(
        request,
        {
            "fields",
            "type",
            "run_type",
            "source_location",
            "dockerfile_path",
            "platform",
            "is_push_enabled",
            "no_cache",
            "is_archive_enabled",
            "credentials",
            "agent_configuration",
            "timeout",
            "base_image_argument",
            "provenance_argument",
            "argument_count",
        },
        "image expected build request",
    )
    expected_run_fields = sorted(
        {
            "type",
            "imageNames",
            "dockerFilePath",
            "platform",
            "arguments",
            "isPushEnabled",
            "noCache",
            "sourceLocation",
            "isArchiveEnabled",
            "credentials",
            "agentConfiguration",
            "timeout",
        }
    )
    if not exact_json_equal(
        request,
        {
            "fields": expected_run_fields,
            "type": "DockerBuildRequest",
            "run_type": "QuickRun",
            "source_location": source["remote_source_location"],
            "dockerfile_path": "Dockerfile.parser-v2-eval",
            "platform": {"os": "Linux", "architecture": "amd64"},
            "is_push_enabled": True,
            "no_cache": False,
            "is_archive_enabled": True,
            "credentials": {},
            "agent_configuration": {"cpu": 2},
            "timeout": 3600,
            "base_image_argument": {
                "name": "PYTHON_BASE_IMAGE",
                "value": PARSER_V2_EVAL_BASE_IMAGE,
            },
            "provenance_argument": "BUILD_PROVENANCE_SHA256",
            "argument_count": 2,
        },
    ):
        raise LockedEvaluationError("image expected build request is not exact")
    images = value["expected_images"]
    _require_exact_fields(
        images,
        {"staging_name_template", "final_name", "digest_repository"},
        "image expected names",
    )
    commit = source["source_commit"]
    if not exact_json_equal(
        images,
        {
            "staging_name_template": (
                f"{repository}:staging-{commit}-{{invocation_id}}"
            ),
            "final_name": f"{repository}:{commit}",
            "digest_repository": f"{login_server}/{repository}",
        },
    ):
        raise LockedEvaluationError("image expected names differ")
    label = value["image_config_label"]
    _require_exact_fields(
        label, {"name", "value_from_argument"}, "image provenance label"
    )
    if not exact_json_equal(
        label,
        {
            "name": BUILD_PROVENANCE_LABEL,
            "value_from_argument": "BUILD_PROVENANCE_SHA256",
        },
    ):
        raise LockedEvaluationError("image provenance label contract differs")
    checked = {
        "schema_version": BUILD_PROVENANCE_SCHEMA_VERSION,
        "source_commit": commit,
        "remote_source": dict(remote),
        "pinned_base_image": PARSER_V2_EVAL_BASE_IMAGE,
        "acr": {
            "resource_id": resource_id.casefold(),
            "login_server": login_server,
            "location": location,
            "repository": repository,
        },
        "source_binding": source,
        "source_binding_sha256": source_hash,
        "coordination": {
            "binding": coordination_binding,
            "binding_sha256": coordination_hash,
            "build_slot": {
                "domain_sha256": build_domain,
                "record_name": _dns_txt_record_name("build", build_domain),
            },
        },
        "build_context": {
            "registered_paths": sorted(IMAGE_BINDING_SOURCE_PATHS),
            "dockerfile": dict(dockerfile),
            "dependencies": [dict(item) for item in dependencies],
        },
        "expected_run_request": dict(request),
        "expected_images": dict(images),
        "image_config_label": dict(label),
    }
    if not exact_json_equal(
        dict(value), checked
    ) or sha256_bytes(canonical_json_bytes(checked)) != (
        _require_sha256(expected_sha256, "image build provenance SHA-256")
    ):
        raise LockedEvaluationError("image build provenance is not canonical")
    return checked


def _validate_image_oci_evidence(
    value: Mapping[str, Any],
    *,
    image_digest: str,
    provenance_sha256: str,
    expected_sha256: str,
) -> dict[str, Any]:
    _require_exact_fields(
        value,
        {
            "schema_version",
            "image_digest",
            "manifest_sha256",
            "config_digest",
            "config_sha256",
            "provenance_label",
        },
        "image OCI evidence",
    )
    config_digest = _require_image_digest(
        value["config_digest"], "image OCI config digest"
    )
    label = value["provenance_label"]
    _require_exact_fields(label, {"name", "value"}, "image OCI provenance label")
    checked = {
        "schema_version": OCI_VERIFICATION_SCHEMA_VERSION,
        "image_digest": image_digest,
        "manifest_sha256": image_digest.removeprefix("sha256:"),
        "config_digest": config_digest,
        "config_sha256": config_digest.removeprefix("sha256:"),
        "provenance_label": {
            "name": BUILD_PROVENANCE_LABEL,
            "value": provenance_sha256,
        },
    }
    if (
        not exact_json_equal(dict(value), checked)
        or sha256_bytes(canonical_json_bytes(checked))
        != _require_sha256(expected_sha256, "image OCI evidence SHA-256")
    ):
        raise LockedEvaluationError("image OCI evidence is not exact")
    return checked


def validate_image_binding(
    data: bytes,
    *,
    expected_sha256: str,
    expected_source_commit: str | None = None,
    expected_acr_resource_id: str | None = None,
    expected_login_server: str | None = None,
    expected_repository: str | None = None,
) -> dict[str, Any]:
    expected_hash = _require_sha256(expected_sha256, "image binding SHA-256")
    if sha256_bytes(data) != expected_hash:
        raise LockedEvaluationError("image binding hash mismatch")
    record = parse_json_strict(data, "image binding")
    _require_exact_fields(record, _IMAGE_BINDING_FIELDS, "image binding")
    if record["schema_version"] != IMAGE_BINDING_SCHEMA_VERSION:
        raise LockedEvaluationError("image binding schema version is invalid")
    source = _validate_image_source_binding(
        {
            "schema_version": BUILD_SOURCE_BINDING_SCHEMA_VERSION,
            "source_commit": record["source_commit"],
            "source_repository_url": record["source_repository_url"],
            "remote_source_location": record["remote_source_location"],
            "base_image": record["base_image"],
            "image_repository": record["image_repository"],
            "files": record["files"],
        }
    )
    source_hash = sha256_bytes(canonical_json_bytes(source))
    if record["source_binding_sha256"] != source_hash:
        raise LockedEvaluationError("image source-binding hash mismatch")
    provenance_hash = _require_sha256(
        record["build_provenance_sha256"], "image build provenance SHA-256"
    )
    provenance = _validate_image_build_provenance(
        record["build_provenance"],
        source_binding=source,
        expected_sha256=provenance_hash,
    )
    commit = source["source_commit"]
    if expected_source_commit is not None and commit != _require_commit(
        expected_source_commit, "expected image source commit"
    ):
        raise LockedEvaluationError("image binding source commit mismatch")
    acr = provenance["acr"]
    expected_acr_values = (
        (
            acr["resource_id"],
            expected_acr_resource_id,
            "image binding ACR resource ID",
        ),
        (acr["login_server"], expected_login_server, "image binding login server"),
        (acr["repository"], expected_repository, "image binding repository"),
    )
    for actual, expected, name in expected_acr_values:
        if expected is not None and actual.casefold() != _require_string(
            expected, f"expected {name}"
        ).casefold():
            raise LockedEvaluationError(f"{name} mismatch")
    digest = _require_image_digest(record["image_digest"], "bound image digest")
    staging_tag = _require_string(
        record["staging_image_tag"], "bound staging image tag"
    )
    if not re.fullmatch(
        rf"staging-{re.escape(commit)}-[0-9a-f]{{32}}", staging_tag, re.ASCII
    ):
        raise LockedEvaluationError("image staging tag is invalid")
    if record["image_tag"] != commit:
        raise LockedEvaluationError("image final tag does not equal source commit")
    expected_ref = f"{acr['login_server']}/{acr['repository']}@{digest}"
    if record["image_digest_ref"] != expected_ref:
        raise LockedEvaluationError("image digest reference is not exact")
    task_run_name = _require_string(
        record["acr_build_task_run_name"], "ACR build TaskRun name"
    )
    if not _ACR_TASK_RUN_NAME_PATTERN.fullmatch(task_run_name):
        raise LockedEvaluationError("ACR build TaskRun name is invalid")
    task_run_resource_id = _require_string(
        record["acr_build_task_run_resource_id"],
        "ACR build TaskRun resource ID",
    )
    expected_task_run_resource_id = (
        f"{acr['resource_id']}/taskRuns/{task_run_name}"
    )
    if task_run_resource_id.casefold() != expected_task_run_resource_id.casefold():
        raise LockedEvaluationError("ACR build TaskRun resource identity differs")
    run_id = _require_string(record["acr_build_run_id"], "ACR build run ID")
    if not _ACR_RUN_ID_PATTERN.fullmatch(run_id):
        raise LockedEvaluationError("ACR build run ID is invalid")
    run_request_hash = _require_sha256(
        record["build_run_request_sha256"], "ACR build runRequest SHA-256"
    )
    oci_hash = _require_sha256(
        record["oci_verification_sha256"], "image OCI evidence SHA-256"
    )
    oci = _validate_image_oci_evidence(
        record["oci_verification"],
        image_digest=digest,
        provenance_sha256=provenance_hash,
        expected_sha256=oci_hash,
    )
    coordination = validate_coordination_binding(
        record["coordination_binding"]
    )
    coordination_hash = coordination_binding_sha256(coordination)
    if (
        record["coordination_binding_sha256"] != coordination_hash
        or not exact_json_equal(
            provenance["coordination"]["binding"], coordination
        )
        or provenance["coordination"]["binding_sha256"]
        != coordination_hash
    ):
        raise LockedEvaluationError(
            "image coordination binding differs from build provenance"
        )
    build_slot = record["build_slot"]
    _require_exact_fields(
        build_slot,
        {
            "domain_sha256",
            "record_name",
            "record_resource_id",
            "record_etag",
            "record_etag_sha256",
            "payload_sha256",
            "claim_nonce",
            "record_ttl",
        },
        "image build TXT slot",
    )
    slot_domain = _require_sha256(
        build_slot["domain_sha256"], "image build-slot domain"
    )
    slot_name = _require_string(
        build_slot["record_name"], "image build-slot record name"
    )
    slot_etag = _require_string(
        build_slot["record_etag"], "image build-slot ETag", maximum=512
    )
    slot_nonce = _require_string(
        build_slot["claim_nonce"], "image build-slot claim nonce"
    )
    if (
        not slot_etag.isascii()
        or not re.fullmatch(r"[0-9a-f]{32}", slot_nonce, re.ASCII)
        or slot_nonce != staging_tag.rsplit("-", 1)[-1]
        or slot_domain
        != provenance["coordination"]["build_slot"]["domain_sha256"]
        or slot_name != _dns_txt_record_name("build", slot_domain)
        or slot_name
        != provenance["coordination"]["build_slot"]["record_name"]
        or str(build_slot["record_resource_id"]).casefold()
        != (
            f"{coordination['zone_resource_id']}/TXT/{slot_name}"
        ).casefold()
        or build_slot["record_etag_sha256"]
        != sha256_bytes(slot_etag.encode("ascii"))
        or not _SHA256_PATTERN.fullmatch(str(build_slot["payload_sha256"]))
        or build_slot["record_ttl"] != coordination["record_ttl"]
        or type(build_slot["record_ttl"]) is not int
    ):
        raise LockedEvaluationError("image build TXT slot evidence is invalid")
    attributes = record["changeable_attributes"]
    _require_exact_fields(
        attributes,
        {
            "tag_write_enabled",
            "tag_delete_enabled",
            "manifest_write_enabled",
            "manifest_delete_enabled",
        },
        "image immutable lock attributes",
    )
    if not exact_json_equal(
        attributes,
        {
            "tag_write_enabled": False,
            "tag_delete_enabled": False,
            "manifest_write_enabled": False,
            "manifest_delete_enabled": False,
        },
    ):
        raise LockedEvaluationError("image tag/manifest locks are not immutable")
    fixed_controls = {
        "historical_finalization_supported": True,
        "cpu_only": True,
        "gpu": False,
        "stage_p_and_e_same_digest": True,
        "mutable_latest_forbidden": True,
    }
    if any(record[name] is not expected for name, expected in fixed_controls.items()):
        raise LockedEvaluationError("image binding immutable controls differ")
    return {
        **source,
        "schema_version": IMAGE_BINDING_SCHEMA_VERSION,
        "source_binding_sha256": source_hash,
        "build_provenance": provenance,
        "build_provenance_sha256": provenance_hash,
        "build_run_request_sha256": run_request_hash,
        "oci_verification_sha256": oci_hash,
        "oci_verification": oci,
        "staging_image_tag": staging_tag,
        "image_tag": commit,
        "image_digest": digest,
        "image_digest_ref": expected_ref,
        "acr_build_task_run_name": task_run_name,
        "acr_build_task_run_resource_id": expected_task_run_resource_id,
        "acr_build_run_id": run_id,
        "coordination_binding": coordination,
        "coordination_binding_sha256": coordination_hash,
        "build_slot": dict(build_slot),
        **fixed_controls,
        "changeable_attributes": dict(attributes),
    }


def image_binding_essential_record(
    image_binding: Mapping[str, Any],
) -> dict[str, Any]:
    data = canonical_json_bytes(dict(image_binding))
    binding = validate_image_binding(
        data, expected_sha256=sha256_bytes(data)
    )
    provenance = binding["build_provenance"]
    return {
        "schema_version": IMAGE_BINDING_ESSENTIAL_SCHEMA_VERSION,
        "source_commit": binding["source_commit"],
        "source_repository_url": binding["source_repository_url"],
        "source_location": binding["remote_source_location"],
        "pinned_base_image": binding["base_image"],
        "acr": dict(provenance["acr"]),
        "source_binding_sha256": binding["source_binding_sha256"],
        "build_provenance_sha256": binding["build_provenance_sha256"],
        "build_run": {
            "task_run_name": binding["acr_build_task_run_name"],
            "task_run_resource_id": binding["acr_build_task_run_resource_id"],
            "run_id": binding["acr_build_run_id"],
            "run_request_sha256": binding["build_run_request_sha256"],
            "staging_tag": binding["staging_image_tag"],
        },
        "coordination_binding": dict(binding["coordination_binding"]),
        "coordination_binding_sha256": binding[
            "coordination_binding_sha256"
        ],
        "build_slot": dict(binding["build_slot"]),
        "final_image": {
            "tag": binding["image_tag"],
            "digest": binding["image_digest"],
            "digest_ref": binding["image_digest_ref"],
        },
        "oci_verification_sha256": binding["oci_verification_sha256"],
        "oci_verification": dict(binding["oci_verification"]),
        "changeable_attributes": dict(binding["changeable_attributes"]),
    }


def validate_runtime_azure_destination(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        {
            "subscription_id",
            "resource_group",
            "location",
            "container_apps",
            "managed_identity",
            "storage",
            "network",
            "coordination",
            "registry",
            "image",
        },
        "runtime Azure destination",
    )
    subscription = _require_string(
        value["subscription_id"], "runtime subscription ID"
    ).casefold()
    if not _AZURE_CLIENT_ID_PATTERN.fullmatch(subscription):
        raise LockedEvaluationError("runtime subscription ID is not a UUID")
    resource_group = _require_azure_name(
        value["resource_group"], "runtime resource group"
    )
    location = _require_azure_name(value["location"], "runtime Azure location")

    apps = value["container_apps"]
    _require_exact_fields(
        apps,
        {
            "environment_name",
            "environment_resource_id",
            "job_name",
            "job_resource_id",
            "workload_profile",
        },
        "runtime Container Apps destination",
    )
    environment_name = _require_azure_name(
        apps["environment_name"], "Container Apps environment name"
    )
    job_name = _require_azure_name(apps["job_name"], "Container Apps job name")
    if apps["workload_profile"] != "Consumption":
        raise LockedEvaluationError("runtime workload profile must be Consumption")
    environment_id = _require_azure_resource_id(
        apps["environment_resource_id"],
        "Container Apps environment resource ID",
        subscription_id=subscription,
        resource_group=resource_group,
        provider="Microsoft.App",
        tail=f"managedEnvironments/{environment_name}",
    )
    job_id = _require_azure_resource_id(
        apps["job_resource_id"],
        "Container Apps job resource ID",
        subscription_id=subscription,
        resource_group=resource_group,
        provider="Microsoft.App",
        tail=f"jobs/{job_name}",
    )

    identity = value["managed_identity"]
    _require_exact_fields(
        identity,
        {"name", "resource_id", "client_id", "principal_id"},
        "runtime managed identity",
    )
    identity_name = _require_azure_name(identity["name"], "managed identity name")
    identity_id = _require_azure_resource_id(
        identity["resource_id"],
        "managed identity resource ID",
        subscription_id=subscription,
        resource_group=resource_group,
        provider="Microsoft.ManagedIdentity",
        tail=f"userAssignedIdentities/{identity_name}",
    )
    client_id = _require_string(identity["client_id"], "managed identity client ID")
    principal_id = _require_string(
        identity["principal_id"], "managed identity principal ID"
    )
    if not _AZURE_CLIENT_ID_PATTERN.fullmatch(client_id) or not (
        _AZURE_CLIENT_ID_PATTERN.fullmatch(principal_id)
    ):
        raise LockedEvaluationError("managed identity UUID binding is invalid")

    storage = value["storage"]
    _require_exact_fields(
        storage,
        {
            "account_name",
            "resource_id",
            "blob_endpoint",
            "container",
            "public_network_access",
            "shared_key_access",
            "allow_blob_public_access",
            "container_public_access",
        },
        "runtime storage destination",
    )
    account_name = _require_azure_name(
        storage["account_name"], "storage account name"
    ).casefold()
    if not re.fullmatch(r"[a-z0-9]{3,24}", account_name, re.ASCII):
        raise LockedEvaluationError("storage account name is invalid")
    storage_id = _require_azure_resource_id(
        storage["resource_id"],
        "storage account resource ID",
        subscription_id=subscription,
        resource_group=resource_group,
        provider="Microsoft.Storage",
        tail=f"storageAccounts/{account_name}",
    )
    account_url, _ = validate_managed_identity_configuration(
        storage["blob_endpoint"], {"AZURE_CLIENT_ID": client_id}
    )
    if account_url != f"https://{account_name}.blob.core.windows.net":
        raise LockedEvaluationError("runtime Blob endpoint is not the exact account")
    container = validate_container_name(storage["container"])
    if (
        storage["public_network_access"] != "Disabled"
        or storage["shared_key_access"] is not False
        or storage["allow_blob_public_access"] is not False
        or storage["container_public_access"] is not None
    ):
        raise LockedEvaluationError(
            "runtime storage must be private, nonpublic, and keyless"
        )

    network = value["network"]
    _require_exact_fields(
        network,
        {
            "vnet_resource_id",
            "infrastructure_subnet_resource_id",
            "private_endpoint_subnet_resource_id",
            "private_endpoint_resource_id",
            "private_endpoint_name",
            "private_endpoint_resource_group",
            "private_link_connection_name",
            "storage_private_endpoint_connection_name",
            "storage_private_endpoint_connection_resource_id",
            "private_link_group_id",
            "private_link_subresource",
            "private_endpoint_nic_private_ips",
            "private_dns_zone_name",
            "private_dns_zone_resource_id",
            "private_dns_zone_group_name",
            "private_dns_vnet_link_name",
        },
        "runtime private network destination",
    )
    private_endpoint_resource_group = _require_azure_name(
        network["private_endpoint_resource_group"],
        "private endpoint resource group",
    )
    vnet_id = _require_string(network["vnet_resource_id"], "VNet resource ID")
    vnet_match = _AZURE_RESOURCE_ID_PATTERN.fullmatch(vnet_id)
    if (
        vnet_match is None
        or vnet_match.group("subscription").casefold() != subscription
        or vnet_match.group("resource_group").casefold()
        != resource_group.casefold()
        or vnet_match.group("provider").casefold() != "microsoft.network"
        or not re.fullmatch(
            r"virtualNetworks/[A-Za-z0-9._-]+",
            vnet_match.group("tail"),
            re.ASCII | re.IGNORECASE,
        )
    ):
        raise LockedEvaluationError("runtime VNet resource ID is invalid")
    infrastructure_subnet_id = _require_string(
        network["infrastructure_subnet_resource_id"],
        "Container Apps infrastructure subnet resource ID",
    )
    private_endpoint_subnet_id = _require_string(
        network["private_endpoint_subnet_resource_id"],
        "private endpoint subnet resource ID",
    )
    for name, subnet_id in (
        ("Container Apps infrastructure subnet", infrastructure_subnet_id),
        ("private endpoint subnet", private_endpoint_subnet_id),
    ):
        if (
            not subnet_id.casefold().startswith(f"{vnet_id}/subnets/".casefold())
            or subnet_id.count("/") != vnet_id.count("/") + 2
        ):
            raise LockedEvaluationError(f"{name} is not in the exact VNet")
    endpoint_name = _require_azure_name(
        network["private_endpoint_name"], "private endpoint name"
    )
    endpoint_id = _require_azure_resource_id(
        network["private_endpoint_resource_id"],
        "private endpoint resource ID",
        subscription_id=subscription,
        resource_group=private_endpoint_resource_group,
        provider="Microsoft.Network",
        tail=f"privateEndpoints/{endpoint_name}",
    )
    connection_name = _require_azure_name(
        network["private_link_connection_name"],
        "private link connection name",
    )
    storage_connection_name = _require_azure_name(
        network["storage_private_endpoint_connection_name"],
        "storage private endpoint connection name",
    )
    storage_connection_id = _require_azure_resource_id(
        network["storage_private_endpoint_connection_resource_id"],
        "storage private endpoint connection resource ID",
        subscription_id=subscription,
        resource_group=resource_group,
        provider="Microsoft.Storage",
        tail=(
            f"storageAccounts/{account_name}/privateEndpointConnections/"
            f"{storage_connection_name}"
        ),
    )
    if (
        network["private_link_group_id"] != "blob"
        or network["private_link_subresource"] != "blob"
    ):
        raise LockedEvaluationError("private endpoint must bind only the Blob group")
    ips = network["private_endpoint_nic_private_ips"]
    if not isinstance(ips, list) or not ips:
        raise LockedEvaluationError("private endpoint NIC IP membership is empty")
    checked_ips: list[str] = []
    for value_ip in ips:
        try:
            address = ipaddress.ip_address(
                _require_string(value_ip, "private endpoint NIC IP")
            )
        except ValueError:
            raise LockedEvaluationError(
                "private endpoint NIC IP is invalid"
            ) from None
        if address.version != 4 or not any(
            address in ipaddress.ip_network(network)
            for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
        ):
            raise LockedEvaluationError(
                "private endpoint NIC IP must be private IPv4"
            )
        checked_ips.append(str(address))
    if checked_ips != sorted(set(checked_ips)):
        raise LockedEvaluationError(
            "private endpoint NIC IP membership must be sorted and unique"
        )
    zone_name = _require_string(
        network["private_dns_zone_name"], "private DNS zone name"
    ).casefold()
    if zone_name != "privatelink.blob.core.windows.net":
        raise LockedEvaluationError("runtime private DNS zone is not the Blob zone")
    zone_id = _require_azure_resource_id(
        network["private_dns_zone_resource_id"],
        "private DNS zone resource ID",
        subscription_id=subscription,
        resource_group=resource_group,
        provider="Microsoft.Network",
        tail=f"privateDnsZones/{zone_name}",
    )
    zone_group_name = _require_azure_name(
        network["private_dns_zone_group_name"], "private DNS zone-group name"
    )
    vnet_link_name = _require_azure_name(
        network["private_dns_vnet_link_name"], "private DNS VNet-link name"
    )
    coordination = validate_coordination_binding(value["coordination"])
    coordination_zone_match = _AZURE_RESOURCE_ID_PATTERN.fullmatch(
        coordination["zone_resource_id"]
    )
    if (
        coordination_zone_match is None
        or coordination_zone_match.group("subscription").casefold()
        != subscription
        or coordination["zone_resource_id"].casefold()
        == zone_id.casefold()
        or coordination["zone_name"] == zone_name
    ):
        raise LockedEvaluationError(
            "coordination zone must be distinct from the Blob private DNS zone"
        )

    registry = value["registry"]
    _require_exact_fields(
        registry,
        {"name", "resource_id", "login_server", "repository"},
        "runtime registry destination",
    )
    registry_name = _require_azure_name(
        registry["name"], "container registry name"
    ).casefold()
    registry_id = _require_azure_resource_id(
        registry["resource_id"],
        "container registry resource ID",
        subscription_id=subscription,
        resource_group=resource_group,
        provider="Microsoft.ContainerRegistry",
        tail=f"registries/{registry_name}",
    )
    login_server = _require_string(
        registry["login_server"], "container registry login server"
    ).casefold()
    if (
        not _ACR_LOGIN_SERVER_PATTERN.fullmatch(login_server)
        or login_server != f"{registry_name}.azurecr.io"
    ):
        raise LockedEvaluationError("container registry login server is invalid")
    repository = _require_string(
        registry["repository"], "container registry repository"
    )
    if not _IMAGE_REPOSITORY_PATTERN.fullmatch(repository):
        raise LockedEvaluationError("container registry repository is invalid")

    image = value["image"]
    _require_exact_fields(
        image,
        {
            "digest",
            "reference",
            "base_image",
            "binding_sha256",
            "provenance",
        },
        "runtime image binding",
    )
    digest = _require_image_digest(image["digest"], "runtime image digest")
    reference = _require_string(image["reference"], "runtime image reference")
    if reference != f"{login_server}/{repository}@{digest}":
        raise LockedEvaluationError("runtime image reference is not exact")
    base_image = _require_string(image["base_image"], "runtime base image")
    if base_image != PARSER_V2_EVAL_BASE_IMAGE:
        raise LockedEvaluationError("runtime base image is not the approved exact pin")
    binding_sha256 = _require_sha256(
        image["binding_sha256"], "runtime image binding SHA-256"
    )
    provenance = image["provenance"]
    _require_exact_fields(
        provenance,
        {
            "schema_version",
            "source_commit",
            "source_repository_url",
            "source_location",
            "pinned_base_image",
            "acr",
            "source_binding_sha256",
            "build_provenance_sha256",
            "build_run",
            "coordination_binding",
            "coordination_binding_sha256",
            "build_slot",
            "final_image",
            "oci_verification_sha256",
            "oci_verification",
            "changeable_attributes",
        },
        "runtime image provenance",
    )
    _require_exact_fields(
        provenance["acr"],
        {"resource_id", "login_server", "location", "repository"},
        "runtime image provenance ACR",
    )
    if not _AZURE_LOCATION_PATTERN.fullmatch(
        _require_string(
            provenance["acr"]["location"],
            "runtime image provenance ACR location",
        )
    ):
        raise LockedEvaluationError(
            "runtime image provenance ACR location is invalid"
        )
    _require_exact_fields(
        provenance["build_run"],
        {
            "task_run_name",
            "task_run_resource_id",
            "run_id",
            "run_request_sha256",
            "staging_tag",
        },
        "runtime image provenance build run",
    )
    if (
        not exact_json_equal(
            provenance["coordination_binding"], coordination
        )
        or provenance["coordination_binding_sha256"]
        != coordination_binding_sha256(coordination)
    ):
        raise LockedEvaluationError(
            "runtime coordination differs from image provenance"
        )
    _require_exact_fields(
        provenance["build_slot"],
        {
            "domain_sha256",
            "record_name",
            "record_resource_id",
            "record_etag",
            "record_etag_sha256",
            "payload_sha256",
            "claim_nonce",
            "record_ttl",
        },
        "runtime image provenance build TXT slot",
    )
    _require_exact_fields(
        provenance["final_image"],
        {"tag", "digest", "digest_ref"},
        "runtime image provenance final image",
    )
    _require_exact_fields(
        provenance["changeable_attributes"],
        {
            "tag_write_enabled",
            "tag_delete_enabled",
            "manifest_write_enabled",
            "manifest_delete_enabled",
        },
        "runtime image provenance locks",
    )
    _require_sha256(
        provenance["source_binding_sha256"],
        "runtime image provenance source-binding SHA-256",
    )
    _require_sha256(
        provenance["build_provenance_sha256"],
        "runtime image provenance build-provenance SHA-256",
    )
    _require_sha256(
        provenance["build_run"]["run_request_sha256"],
        "runtime image provenance runRequest SHA-256",
    )
    task_run_name = _require_string(
        provenance["build_run"]["task_run_name"],
        "runtime image provenance TaskRun name",
    )
    if (
        not _ACR_TASK_RUN_NAME_PATTERN.fullmatch(task_run_name)
        or str(provenance["build_run"]["task_run_resource_id"]).casefold()
        != f"{registry_id}/taskRuns/{task_run_name}".casefold()
    ):
        raise LockedEvaluationError(
            "runtime image provenance TaskRun resource identity differs"
        )
    _require_sha256(
        provenance["oci_verification_sha256"],
        "runtime image provenance OCI SHA-256",
    )
    if (
        provenance["schema_version"] != IMAGE_BINDING_ESSENTIAL_SCHEMA_VERSION
        or provenance["pinned_base_image"] != base_image
        or provenance["final_image"]["digest"] != digest
        or provenance["final_image"]["digest_ref"] != reference
        or not exact_json_equal(
            {
                key: provenance["acr"][key]
                for key in ("resource_id", "login_server", "repository")
            },
            {
                "resource_id": registry_id.casefold(),
                "login_server": login_server,
                "repository": repository,
            },
        )
    ):
        raise LockedEvaluationError("runtime image provenance differs from destination")

    checked = {
        "subscription_id": subscription,
        "resource_group": resource_group,
        "location": location,
        "container_apps": {
            "environment_name": environment_name,
            "environment_resource_id": environment_id,
            "job_name": job_name,
            "job_resource_id": job_id,
            "workload_profile": "Consumption",
        },
        "managed_identity": {
            "name": identity_name,
            "resource_id": identity_id,
            "client_id": client_id,
            "principal_id": principal_id,
        },
        "storage": {
            "account_name": account_name,
            "resource_id": storage_id,
            "blob_endpoint": account_url,
            "container": container,
            "public_network_access": "Disabled",
            "shared_key_access": False,
            "allow_blob_public_access": False,
            "container_public_access": None,
        },
        "network": {
            "vnet_resource_id": vnet_id,
            "infrastructure_subnet_resource_id": infrastructure_subnet_id,
            "private_endpoint_subnet_resource_id": private_endpoint_subnet_id,
            "private_endpoint_resource_id": endpoint_id,
            "private_endpoint_name": endpoint_name,
            "private_endpoint_resource_group": private_endpoint_resource_group,
            "private_link_connection_name": connection_name,
            "storage_private_endpoint_connection_name": (
                storage_connection_name
            ),
            "storage_private_endpoint_connection_resource_id": (
                storage_connection_id
            ),
            "private_link_group_id": "blob",
            "private_link_subresource": "blob",
            "private_endpoint_nic_private_ips": checked_ips,
            "private_dns_zone_name": zone_name,
            "private_dns_zone_resource_id": zone_id,
            "private_dns_zone_group_name": zone_group_name,
            "private_dns_vnet_link_name": vnet_link_name,
        },
        "coordination": coordination,
        "registry": {
            "name": registry_name,
            "resource_id": registry_id,
            "login_server": login_server,
            "repository": repository,
        },
        "image": {
            "digest": digest,
            "reference": reference,
            "base_image": base_image,
            "binding_sha256": binding_sha256,
            "provenance": dict(provenance),
        },
    }
    if not exact_json_equal(dict(value), checked):
        raise LockedEvaluationError(
            "runtime Azure destination is not exact canonical JSON"
        )
    return checked


def runtime_destination_sha256(destination: Mapping[str, Any]) -> str:
    checked = validate_runtime_azure_destination(destination)
    return sha256_bytes(canonical_json_bytes(checked))


def validate_runtime_private_read_destination(
    runtime_configuration: Mapping[str, Any],
    *,
    account_url: str,
    container: str,
    expected_private_endpoint_ips: str | Sequence[str],
) -> dict[str, Any]:
    destination = validate_runtime_azure_destination(
        runtime_configuration["azure_destination"]
    )
    supplied_ips = (
        [expected_private_endpoint_ips]
        if isinstance(expected_private_endpoint_ips, str)
        else list(expected_private_endpoint_ips)
    )
    try:
        normalized_ips = sorted(
            str(ipaddress.ip_address(_require_string(item, "private endpoint IP")))
            for item in supplied_ips
        )
    except ValueError:
        raise LockedEvaluationError(
            "runtime private-read endpoint IP is invalid"
        ) from None
    if (
        account_url.rstrip("/") != destination["storage"]["blob_endpoint"]
        or validate_container_name(container)
        != destination["storage"]["container"]
        or not exact_json_equal(
            normalized_ips,
            destination["network"]["private_endpoint_nic_private_ips"],
        )
    ):
        raise LockedEvaluationError(
            "private read differs from the immutable Azure destination"
        )
    return destination


def validate_runtime_configuration(
    data: bytes,
    *,
    expected_sha256: str,
    source_commit: str,
    parent_prefix: str,
    authorization_id: str,
    launcher_sha256: str | None = None,
    launcher_git_blob_oid: str | None = None,
    expected_azure_destination: Mapping[str, Any] | None = None,
    expected_image_digest: str | None = None,
    image_binding_bytes: bytes | None = None,
    expected_image_binding_sha256: str | None = None,
) -> dict[str, Any]:
    expected_hash = _require_sha256(expected_sha256, "runtime config SHA-256")
    if sha256_bytes(data) != expected_hash:
        raise LockedEvaluationError("runtime config hash mismatch")
    record = parse_json_strict(data, "runtime config")
    _require_exact_fields(
        record,
        {
            "schema_version",
            "source_commit",
            "source_bindings",
            "helper_snapshot_set_sha256",
            "launcher",
            "stage_commands",
            "job",
            "bindings",
            "azure_destination",
            "azure_destination_sha256",
            "image_binding",
            "image_binding_sha256",
            "retry_policy",
        },
        "runtime config",
    )
    if record["schema_version"] != RUNTIME_CONFIG_SCHEMA_VERSION:
        raise LockedEvaluationError("runtime config schema version is invalid")
    commit = _require_commit(record["source_commit"], "runtime source commit")
    if commit != _require_commit(source_commit, "expected source commit"):
        raise LockedEvaluationError("runtime config source binding mismatch")
    source_bindings = validate_runtime_source_bindings(
        record["source_bindings"],
        launcher_sha256=launcher_sha256,
        launcher_git_blob_oid=launcher_git_blob_oid,
    )
    helper_snapshot_set_sha256 = sha256_bytes(
        canonical_json_bytes(source_bindings)
    )
    if (
        _require_sha256(
            record["helper_snapshot_set_sha256"],
            "runtime helper snapshot-set SHA-256",
        )
        != helper_snapshot_set_sha256
    ):
        raise LockedEvaluationError("runtime helper snapshot-set binding mismatch")
    embedded_image_binding_bytes = canonical_json_bytes(record["image_binding"])
    image_binding_sha256 = _require_sha256(
        record["image_binding_sha256"], "runtime image binding SHA-256"
    )
    image_binding = validate_image_binding(
        embedded_image_binding_bytes,
        expected_sha256=image_binding_sha256,
        expected_source_commit=commit,
    )
    image_runtime_sources = {
        path: {
            "git_blob_oid": image_binding["files"][path]["git_blob_oid"],
            "sha256": image_binding["files"][path]["sha256"],
        }
        for path in RUNTIME_SOURCE_BINDING_PATHS
    }
    if not exact_json_equal(source_bindings, image_runtime_sources):
        raise LockedEvaluationError(
            "runtime sources differ from image source provenance"
        )
    if expected_image_binding_sha256 is not None and image_binding_sha256 != (
        _require_sha256(
            expected_image_binding_sha256, "expected runtime image binding SHA-256"
        )
    ):
        raise LockedEvaluationError("runtime image binding expected hash mismatch")
    if image_binding_bytes is not None:
        external_image_binding = validate_image_binding(
            image_binding_bytes,
            expected_sha256=image_binding_sha256,
            expected_source_commit=commit,
        )
        if not exact_json_equal(external_image_binding, image_binding):
            raise LockedEvaluationError(
                "runtime and external image binding records differ"
            )
    launcher = record["launcher"]
    _require_exact_fields(
        launcher, {"path", "git_blob_oid", "sha256"}, "runtime launcher"
    )
    launcher_path = "infra/azure/scripts/10_run_parser_v2_locked_eval.sh"
    if not exact_json_equal(
        launcher, {"path": launcher_path, **source_bindings[launcher_path]}
    ):
        raise LockedEvaluationError("runtime launcher binding is not registered")
    expected_commands = {
        "P": {"command": ["/workspace/bin/stage-p"], "args_prefix": []},
        "P_ADOPT": {
            "command": ["/workspace/bin/stage-p-adopt"],
            "args_prefix": [],
        },
        "E": {"command": ["/workspace/bin/stage-e"], "args_prefix": []},
    }
    if not exact_json_equal(record["stage_commands"], expected_commands):
        raise LockedEvaluationError("runtime stage commands are not exact")
    expected_job = {
        "trigger_type": "Manual",
        "replica_timeout_seconds": 3600,
        "replica_retry_limit": 0,
        "replica_completion_count": 1,
        "parallelism": 1,
        "cpu": "2.0",
        "memory": "4Gi",
        "workload_profile": "Consumption",
        "gpu": False,
        "azure_files": False,
        "managed_identity_only": True,
    }
    if not exact_json_equal(record["job"], expected_job):
        raise LockedEvaluationError("runtime job controls/resources are not exact")
    prefixes = evaluation_prefixes(parent_prefix, authorization_id)
    expected_bindings = {
        "registered_parent_prefix": validate_registered_parent_prefix(
            parent_prefix
        ),
        "authorization_id": validate_authorization_id(authorization_id),
        **{f"{leaf}_prefix": value for leaf, value in prefixes.items()},
    }
    if not exact_json_equal(record["bindings"], expected_bindings):
        raise LockedEvaluationError("runtime authorization/prefix bindings are not exact")
    destination = validate_runtime_azure_destination(record["azure_destination"])
    destination_hash = runtime_destination_sha256(destination)
    if not exact_json_equal(record["azure_destination"], destination) or (
        _require_sha256(
            record["azure_destination_sha256"],
            "runtime Azure destination SHA-256",
        )
        != destination_hash
    ):
        raise LockedEvaluationError("runtime Azure destination binding is not canonical")
    if (
        destination["image"]["binding_sha256"] != image_binding_sha256
        or not exact_json_equal(
            destination["image"]["provenance"],
            image_binding_essential_record(image_binding),
        )
        or destination["image"]["digest"] != image_binding["image_digest"]
        or destination["image"]["base_image"] != image_binding["base_image"]
        or destination["registry"]["resource_id"].casefold()
        != image_binding["build_provenance"]["acr"]["resource_id"].casefold()
        or destination["registry"]["login_server"]
        != image_binding["build_provenance"]["acr"]["login_server"]
        or destination["registry"]["repository"]
        != image_binding["build_provenance"]["acr"]["repository"]
    ):
        raise LockedEvaluationError(
            "runtime Azure destination differs from image provenance"
        )
    if (
        expected_azure_destination is not None
        and not exact_json_equal(
            destination,
            validate_runtime_azure_destination(expected_azure_destination),
        )
    ):
        raise LockedEvaluationError("runtime Azure destination differs from expected")
    if (
        expected_image_digest is not None
        and destination["image"]["digest"]
        != _require_image_digest(
            expected_image_digest, "expected runtime image digest"
        )
    ):
        raise LockedEvaluationError("runtime image digest binding mismatch")
    expected_retry = {
        "infrastructure_pre_input_max": 1,
        "prediction_adoption_max": 1,
        "scorer_infrastructure_max": 1,
        "verification_only_max": 1,
        "parser_rerun_after_inputs": False,
        "metric_recompute_after_labels": False,
        "verification_only_new_bytes": False,
    }
    if not exact_json_equal(record["retry_policy"], expected_retry):
        raise LockedEvaluationError("runtime retry policy is not exact")
    return record


def build_runtime_configuration(
    *,
    source_commit: str,
    parent_prefix: str,
    authorization_id: str,
    launcher_sha256: str,
    launcher_git_blob_oid: str,
    source_bindings: Mapping[str, Mapping[str, str]],
    azure_destination: Mapping[str, Any],
    image_binding: Mapping[str, Any],
    image_binding_sha256: str,
) -> dict[str, Any]:
    prefixes = evaluation_prefixes(parent_prefix, authorization_id)
    checked_sources = validate_runtime_source_bindings(
        source_bindings,
        launcher_sha256=launcher_sha256,
        launcher_git_blob_oid=launcher_git_blob_oid,
    )
    binding_bytes = canonical_json_bytes(dict(image_binding))
    checked_image_binding = validate_image_binding(
        binding_bytes,
        expected_sha256=image_binding_sha256,
        expected_source_commit=source_commit,
    )
    raw_destination = dict(azure_destination)
    raw_destination["image"] = {
        **dict(azure_destination["image"]),
        "binding_sha256": image_binding_sha256,
        "provenance": image_binding_essential_record(checked_image_binding),
    }
    destination = validate_runtime_azure_destination(raw_destination)
    launcher_path = "infra/azure/scripts/10_run_parser_v2_locked_eval.sh"
    record = {
        "schema_version": RUNTIME_CONFIG_SCHEMA_VERSION,
        "source_commit": _require_commit(source_commit, "source commit"),
        "source_bindings": checked_sources,
        "helper_snapshot_set_sha256": sha256_bytes(
            canonical_json_bytes(checked_sources)
        ),
        "launcher": {"path": launcher_path, **checked_sources[launcher_path]},
        "stage_commands": {
            "P": {"command": ["/workspace/bin/stage-p"], "args_prefix": []},
            "P_ADOPT": {
                "command": ["/workspace/bin/stage-p-adopt"],
                "args_prefix": [],
            },
            "E": {"command": ["/workspace/bin/stage-e"], "args_prefix": []},
        },
        "job": {
            "trigger_type": "Manual",
            "replica_timeout_seconds": 3600,
            "replica_retry_limit": 0,
            "replica_completion_count": 1,
            "parallelism": 1,
            "cpu": "2.0",
            "memory": "4Gi",
            "workload_profile": "Consumption",
            "gpu": False,
            "azure_files": False,
            "managed_identity_only": True,
        },
        "bindings": {
            "registered_parent_prefix": validate_registered_parent_prefix(
                parent_prefix
            ),
            "authorization_id": validate_authorization_id(authorization_id),
            **{f"{leaf}_prefix": value for leaf, value in prefixes.items()},
        },
        "azure_destination": destination,
        "azure_destination_sha256": runtime_destination_sha256(destination),
        "image_binding": checked_image_binding,
        "image_binding_sha256": _require_sha256(
            image_binding_sha256, "image binding SHA-256"
        ),
        "retry_policy": {
            "infrastructure_pre_input_max": 1,
            "prediction_adoption_max": 1,
            "scorer_infrastructure_max": 1,
            "verification_only_max": 1,
            "parser_rerun_after_inputs": False,
            "metric_recompute_after_labels": False,
            "verification_only_new_bytes": False,
        },
    }
    data = canonical_json_bytes(record)
    validate_runtime_configuration(
        data,
        expected_sha256=sha256_bytes(data),
        source_commit=source_commit,
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
        launcher_sha256=launcher_sha256,
        launcher_git_blob_oid=launcher_git_blob_oid,
        expected_azure_destination=destination,
        expected_image_digest=destination["image"]["digest"],
        image_binding_bytes=binding_bytes,
        expected_image_binding_sha256=image_binding_sha256,
    )
    return record


def read_git_blob_bytes(
    project_root: str | Path, relative_path: str, commit: str = FROZEN_PROTOCOL_COMMIT
) -> bytes:
    root = Path(project_root).resolve()
    checked_commit = _require_commit(commit, "Git blob commit")
    normalized = _require_string(relative_path, "Git blob relative path").replace(
        "\\", "/"
    )
    if (
        normalized != relative_path
        or normalized.startswith("/")
        or any(part in {"", ".", ".."} for part in normalized.split("/"))
    ):
        raise LockedEvaluationError("Git blob path must be normalized")
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "show", f"{checked_commit}:{normalized}"],
            check=False,
            capture_output=True,
        )
    except OSError:
        completed = None
    if completed is not None and completed.returncode == 0:
        return completed.stdout
    expected = _FROZEN_PROTOCOL_FILE_SHA256S.get(normalized)
    if checked_commit != FROZEN_PROTOCOL_COMMIT or expected is None:
        raise LockedEvaluationError(
            f"frozen Git blob is unavailable: {checked_commit}:{normalized}"
        )
    path = root.joinpath(*normalized.split("/"))
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise LockedEvaluationError(
            f"frozen protocol file is unavailable: {normalized}"
        ) from exc
    if sha256_bytes(data) != expected:
        raise LockedEvaluationError(
            f"frozen protocol file hash mismatch: {normalized}"
        )
    return data


def compute_protocol_bundle_sha256(project_root: str | Path) -> str:
    digest = hashlib.sha256()
    digest.update(_PROTOCOL_BUNDLE_DOMAIN)
    for relative in _PROTOCOL_FILES:
        content = read_git_blob_bytes(project_root, relative)
        path_bytes = relative.encode("ascii")
        digest.update(len(path_bytes).to_bytes(4, "big"))
        digest.update(path_bytes)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    result = digest.hexdigest()
    if result != FROZEN_PROTOCOL_BUNDLE_SHA256:
        raise LockedEvaluationError("frozen protocol bundle hash mismatch")
    return result


def load_frozen_gate_bytes(project_root: str | Path) -> bytes:
    data = read_git_blob_bytes(
        project_root, "docs/phase1_parser_v2_acceptance_gates.json"
    )
    if sha256_bytes(data) != FROZEN_ACCEPTANCE_GATE_SHA256:
        raise LockedEvaluationError("frozen acceptance-gate blob hash mismatch")
    return data


def _require_gate_fraction(
    record: Mapping[str, Any], numerator_key: str, denominator_key: str, name: str
) -> Fraction:
    numerator = _require_int(record.get(numerator_key), f"{name}.{numerator_key}")
    denominator = _require_int(
        record.get(denominator_key), f"{name}.{denominator_key}", minimum=1
    )
    return Fraction(numerator, denominator)


def load_acceptance_gates(
    data: bytes, *, expected_sha256: str = FROZEN_ACCEPTANCE_GATE_SHA256
) -> dict[str, Any]:
    expected = _require_sha256(expected_sha256, "expected acceptance-gate SHA-256")
    if sha256_bytes(data) != expected:
        raise LockedEvaluationError("acceptance-gate bytes failed SHA-256 binding")
    gates = parse_json_strict(
        data, "phase1_parser_v2_acceptance_gates.json", require_canonical=False
    )
    for field in (
        "schema_version",
        "dataset_contract",
        "typed_decision",
        "numeric_normalization",
        "absolute_gates",
        "legacy_comparison_gates",
        "correctness_mapping",
        "status_logic",
        "one_shot",
    ):
        if field not in gates:
            raise LockedEvaluationError(f"acceptance gates omit {field}")
    dataset = gates["dataset_contract"]
    absolute = gates["absolute_gates"]
    legacy = gates["legacy_comparison_gates"]
    if not isinstance(dataset, Mapping) or not isinstance(absolute, Mapping):
        raise LockedEvaluationError("gate contract sections must be objects")
    required_absolute = {
        "overall_exact_typed_decision",
        "answer_bearing_per_stratum",
        "every_stratum_floor",
        "answer_presence_macro_f1",
        "ambiguity",
        "no_answer",
        "boxed_final_miss",
        "last_number_trap",
        "wrong_span",
        "material_correctness",
    }
    if set(absolute) != required_absolute:
        raise LockedEvaluationError("absolute gate membership is not frozen")
    if not isinstance(legacy, Mapping) or set(legacy) != {
        "legacy_adapter",
        "clean_pooled_non_regression",
        "critical_strict_improvement",
    }:
        raise LockedEvaluationError("legacy-comparison gate membership is not frozen")
    total = _require_int(dataset.get("total_cases"), "dataset total_cases", minimum=1)
    strata = dataset.get("strata")
    if (
        not isinstance(strata, list)
        or not strata
        or any(not isinstance(item, str) for item in strata)
        or strata != sorted(set(strata))
    ):
        raise LockedEvaluationError("dataset strata must be unique and ordered")
    per_stratum = _require_int(
        dataset.get("cases_per_stratum"), "dataset cases_per_stratum", minimum=1
    )
    if len(strata) * per_stratum != total:
        raise LockedEvaluationError("dataset strata do not partition total_cases")
    support = dataset.get("typed_decision_support")
    if (
        not isinstance(support, Mapping)
        or set(support) != set(TYPED_DECISION_CLASSES)
        or any(type(value) is not int or value < 0 for value in support.values())
        or sum(support.values()) != total
    ):
        raise LockedEvaluationError("typed-decision support is invalid")
    for name in ("answer_bearing_strata", "clean_strata", "critical_strata"):
        values = dataset.get(name)
        if (
            not isinstance(values, list)
            or values != [stratum for stratum in strata if stratum in set(values)]
            or not set(values).issubset(strata)
        ):
            raise LockedEvaluationError(f"{name} is not an ordered stratum subset")
    status_logic = gates["status_logic"]
    if not isinstance(status_logic, Mapping) or set(status_logic) != {
        "PASS",
        "FAIL",
        "INVALID",
        "rounded_display_values_used_for_gates",
        "missing_cases_dropped",
    }:
        raise LockedEvaluationError("status logic is not frozen")
    if (
        status_logic["rounded_display_values_used_for_gates"] is not False
        or status_logic["missing_cases_dropped"] is not False
    ):
        raise LockedEvaluationError("status logic permits rounding or case dropping")
    one_shot = gates["one_shot"]
    if not isinstance(one_shot, Mapping) or any(
        one_shot.get(field) is not expected_value
        for field, expected_value in {
            "implementation_commit_before_input_read": True,
            "predictions_sealed_before_label_read": True,
            "formal_evaluations_per_holdout": 1,
            "pass_or_fail_retires_holdout": True,
            "metric_failure_retry_allowed": False,
            "modified_parser_requires_new_holdout": True,
        }.items()
    ):
        raise LockedEvaluationError("one-shot gate contract is invalid")
    return gates


def normalize_rational_literal(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise LockedEvaluationError("numeric literal must be a nonempty string")
    if len(value) > _MAX_LITERAL_CHARACTERS or any(ord(item) > 127 for item in value):
        raise LockedEvaluationError("numeric literal is outside registered bounds")
    if _FRACTION_PATTERN.fullmatch(value):
        numerator_text, denominator_text = value.split("/", 1)
        denominator = int(denominator_text, 10)
        if denominator == 0:
            raise LockedEvaluationError("fraction denominator must not be zero")
        rational = Fraction(int(numerator_text, 10), denominator)
    elif _DECIMAL_PATTERN.fullmatch(value):
        parts = re.split(r"[eE]", value, maxsplit=1)
        mantissa = parts[0]
        exponent_text = parts[1] if len(parts) == 2 else "0"
        exponent_digits = exponent_text.lstrip("+-").lstrip("0") or "0"
        bound = _MAX_CANONICAL_CHARACTERS + _MAX_LITERAL_CHARACTERS
        if len(exponent_digits) > len(str(bound)) or (
            len(exponent_digits) == len(str(bound))
            and exponent_digits > str(bound)
        ):
            raise LockedEvaluationError("numeric exponent exceeds registered bounds")
        exponent = int(exponent_text, 10)
        sign = -1 if mantissa.startswith("-") else 1
        unsigned = mantissa.lstrip("+-")
        if "." in unsigned:
            whole, fractional = unsigned.split(".", 1)
        else:
            whole, fractional = unsigned, ""
        digits = (whole or "0") + fractional
        significant = digits.lstrip("0")
        if not significant:
            return "0"
        power = exponent - len(fractional)
        if power >= 0:
            rendered = ("-" if sign < 0 else "") + significant + ("0" * power)
            if len(rendered) > _MAX_CANONICAL_CHARACTERS:
                raise LockedEvaluationError("canonical numeric value is too long")
            return rendered
        denominator_power = -power
        if denominator_power > bound:
            raise LockedEvaluationError("canonical numeric value is too long")
        rational = Fraction(sign * int(significant, 10), 10**denominator_power)
    else:
        raise LockedEvaluationError("numeric literal has unsupported grammar")
    rendered = (
        str(rational.numerator)
        if rational.denominator == 1
        else f"{rational.numerator}/{rational.denominator}"
    )
    if len(rendered) > _MAX_CANONICAL_CHARACTERS:
        raise LockedEvaluationError("canonical numeric value is too long")
    return rendered


def _require_canonical_numeric(value: Any, name: str) -> str:
    checked = _require_string(value, name)
    if normalize_rational_literal(checked) != checked:
        raise LockedEvaluationError(f"{name} must already be canonical")
    return checked


def validate_locked_input(
    record: Mapping[str, Any], *, name: str = "locked input"
) -> dict[str, Any]:
    try:
        return _load_frozen_validation().validate_locked_input(record, name=name)
    except Exception:
        raise LockedEvaluationError("locked input schema/invariants are invalid") from None


def validate_locked_inputs_bytes(
    data: bytes, gates: Mapping[str, Any]
) -> list[dict[str, Any]]:
    rows = parse_jsonl_strict(data, "locked_inputs.jsonl")
    total = _require_int(
        gates["dataset_contract"]["total_cases"], "gate total cases", minimum=1
    )
    if len(rows) != total:
        raise LockedEvaluationError("locked inputs have the wrong record count")
    ids: list[str] = []
    for index, row in enumerate(rows):
        ids.append(validate_locked_input(row, name=f"locked inputs[{index}]")["case_id"])
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise LockedEvaluationError("locked input IDs must be unique and ordered")
    return rows


def project_parser_request(locked_input: Mapping[str, Any]) -> dict[str, str]:
    checked = validate_locked_input(locked_input)
    return {
        "schema_version": PARSER_REQUEST_SCHEMA_VERSION,
        "answer_type": "numeric",
        "output_text": checked["output_text"],
    }


def _validate_numeric_token_context(
    output_text: str, start: int, end: int, name: str
) -> None:
    previous = output_text[start - 1] if start else ""
    following = output_text[end] if end < len(output_text) else ""
    if previous and (previous.isalnum() or previous == "_"):
        raise LockedEvaluationError(f"{name} is embedded in an identifier or unit")
    if following and (
        following.isalnum()
        or following
        in {
            "_",
            "%",
            "％",
            "‰",
            "‱",
            "°",
            "º",
            "℃",
            "℉",
            "$",
            "€",
            "£",
            "¥",
            "₹",
            "₽",
            "¢",
            "/",
        }
    ):
        raise LockedEvaluationError(
            f"{name} is embedded in an identifier, percentage, or unit"
        )
    if previous in {
        "+",
        "-",
        ".",
        "/",
        "$",
        "€",
        "£",
        "¥",
        "₹",
        "₽",
        "¢",
        "°",
        "º",
    }:
        raise LockedEvaluationError(
            f"{name} omits numeric syntax or is unit-bearing"
        )
    if (
        previous in {":", ",", "：", "，"}
        and start >= 2
        and output_text[start - 2].isdigit()
    ):
        raise LockedEvaluationError(f"{name} is embedded in a version or date")
    if (
        following in {".", "/", "-", ":", ",", "：", "，"}
        and end + 1 < len(output_text)
        and output_text[end + 1].isdigit()
    ):
        raise LockedEvaluationError(f"{name} is embedded in a version or date")


def _validate_evidence_span(
    span: Mapping[str, Any], output_text: str, *, acceptable: bool, name: str
) -> dict[str, Any]:
    fields = {"start", "end", "text"}
    if not acceptable:
        fields |= {"kind", "normalized_answer", "disposition"}
    _require_exact_fields(span, fields, name)
    start = _require_int(span["start"], f"{name}.start", minimum=0)
    end = _require_int(span["end"], f"{name}.end", minimum=0)
    text = _require_string(span["text"], f"{name}.text", nonempty=False)
    if start >= end or end > len(output_text) or output_text[start:end] != text:
        raise LockedEvaluationError(f"{name} offsets/text are invalid")
    result = {"start": start, "end": end, "text": text}
    if not acceptable:
        _validate_numeric_token_context(output_text, start, end, name)
        normalized = _require_canonical_numeric(
            span["normalized_answer"], f"{name}.normalized_answer"
        )
        if normalize_rational_literal(text) != normalized:
            raise LockedEvaluationError(f"{name} normalized value mismatches text")
        result.update(
            {
                "kind": _require_enum(span["kind"], EVIDENCE_KINDS, f"{name}.kind"),
                "normalized_answer": normalized,
                "disposition": _require_enum(
                    span["disposition"],
                    EVIDENCE_DISPOSITIONS,
                    f"{name}.disposition",
                ),
            }
        )
    return result


def _validate_spans(
    value: Any, output_text: str, *, acceptable: bool, name: str
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise LockedEvaluationError(f"{name} must be a list")
    spans = [
        _validate_evidence_span(
            item,
            output_text,
            acceptable=acceptable,
            name=f"{name}[{index}]",
        )
        for index, item in enumerate(value)
    ]
    identities = [(item["start"], item["end"], item["text"]) for item in spans]
    if identities != sorted(set(identities)):
        raise LockedEvaluationError(f"{name} must be unique and source ordered")
    return spans


def _validate_extraction(
    record: Mapping[str, Any],
    output_text: str,
    *,
    expected: bool,
    name: str,
) -> dict[str, Any]:
    prefix = "expected_" if expected else ""
    key = lambda field: prefix + field
    presence_allowed = TYPED_DECISION_CLASSES if expected else PARSER_PRESENCE
    presence = _require_enum(
        record[key("answer_presence")], presence_allowed, f"{name}.{key('answer_presence')}"
    )
    parse_valid = _require_bool(
        record[key("parse_valid")], f"{name}.{key('parse_valid')}"
    )
    parse_ambiguous = _require_bool(
        record[key("parse_ambiguous")], f"{name}.{key('parse_ambiguous')}"
    )
    parsed_value = record[key("parsed_answer")]
    parsed_answer = (
        None
        if parsed_value is None
        else _require_canonical_numeric(
            parsed_value, f"{name}.{key('parsed_answer')}"
        )
    )
    candidates_value = record[key("candidate_answers")]
    if not isinstance(candidates_value, list):
        raise LockedEvaluationError(f"{name}.{key('candidate_answers')} must be a list")
    candidates = [
        _require_canonical_numeric(item, f"{name}.{key('candidate_answers')}[{index}]")
        for index, item in enumerate(candidates_value)
    ]
    if len(candidates) != len(set(candidates)):
        raise LockedEvaluationError(f"{name} candidate answers are not unique")
    spans = _validate_spans(
        record[key("evidence_spans")],
        output_text,
        acceptable=False,
        name=f"{name}.{key('evidence_spans')}",
    )
    strategy = _require_enum(
        record[key("extraction_strategy")],
        EXTRACTION_STRATEGIES,
        f"{name}.{key('extraction_strategy')}",
    )
    quality = _require_enum(
        record[key("output_quality")],
        OUTPUT_QUALITIES,
        f"{name}.{key('output_quality')}",
    )
    failures_value = record[key("failure_reasons")]
    warnings_value = record[key("format_warnings")]
    if not isinstance(failures_value, list) or not isinstance(warnings_value, list):
        raise LockedEvaluationError(f"{name} failure/warning fields must be lists")
    failures = [
        _require_enum(item, FAILURE_REASONS, f"{name}.failure_reasons[{index}]")
        for index, item in enumerate(failures_value)
    ]
    warnings = [
        _require_enum(item, FORMAT_WARNINGS, f"{name}.format_warnings[{index}]")
        for index, item in enumerate(warnings_value)
    ]
    if failures != [item for item in FAILURE_REASONS if item in set(failures)]:
        raise LockedEvaluationError(f"{name} failure reasons are not closed/ordered")
    if warnings != [item for item in FORMAT_WARNINGS if item in set(warnings)]:
        raise LockedEvaluationError(f"{name} warnings are not closed/ordered")
    selected = [item for item in spans if item["disposition"] == "selected"]
    span_values: list[str] = []
    for span in spans:
        if span["normalized_answer"] not in span_values:
            span_values.append(span["normalized_answer"])
    if candidates != span_values:
        raise LockedEvaluationError(f"{name} candidates do not match evidence order")
    normalized_presence = (
        {"present": "present", "ambiguous": "uncertain", "no_answer": "absent"}[
            presence
        ]
        if expected
        else presence
    )
    if normalized_presence == "present":
        if (
            not parse_valid
            or parse_ambiguous
            or parsed_answer is None
            or candidates != [parsed_answer]
            or len(selected) != 1
            or any(item["normalized_answer"] != parsed_answer for item in spans)
            or strategy in {"none", "ambiguous_candidates"}
        ):
            raise LockedEvaluationError(f"{name} present invariants are invalid")
    elif normalized_presence == "uncertain":
        if (
            not parse_valid
            or not parse_ambiguous
            or parsed_answer is not None
            or len(candidates) < 2
            or selected
            or len(spans) < 2
            or any(item["disposition"] != "ambiguous_candidate" for item in spans)
            or strategy != "ambiguous_candidates"
        ):
            raise LockedEvaluationError(f"{name} ambiguity invariants are invalid")
    else:
        if (
            parse_valid
            or parse_ambiguous
            or parsed_answer is not None
            or candidates
            or spans
            or strategy != "none"
        ):
            raise LockedEvaluationError(f"{name} no-answer invariants are invalid")
    if parse_valid == bool(failures):
        raise LockedEvaluationError(f"{name} validity/failure reasons disagree")
    if not output_text.strip() and quality != "empty":
        raise LockedEvaluationError(f"{name} empty text must have empty quality")
    return {
        "answer_presence": normalized_presence,
        "parse_valid": parse_valid,
        "parse_ambiguous": parse_ambiguous,
        "parsed_answer": parsed_answer,
        "candidate_answers": candidates,
        "evidence_spans": spans,
        "extraction_strategy": strategy,
        "output_quality": quality,
        "failure_reasons": failures,
        "format_warnings": warnings,
    }


_PARSER_RESULT_FIELDS = {
    "schema_version",
    "parser_version",
    "answer_type",
    "input_sha256",
    "answer_presence",
    "parse_valid",
    "parse_ambiguous",
    "parsed_answer",
    "candidate_answers",
    "evidence_spans",
    "extraction_strategy",
    "output_quality",
    "failure_reasons",
    "format_warnings",
}
_EXPECTED_EXTRACTION_FIELDS = {
    f"expected_{field}"
    for field in (
        "answer_presence",
        "parse_valid",
        "parse_ambiguous",
        "parsed_answer",
        "candidate_answers",
        "evidence_spans",
        "extraction_strategy",
        "output_quality",
        "failure_reasons",
        "format_warnings",
    )
}
_FINAL_LABEL_FIELDS = {
    "schema_version",
    "case_id",
    "source_kind",
    "stratum",
    "secondary_tags",
    "output_text",
    "parse_type",
    *_EXPECTED_EXTRACTION_FIELDS,
    "registered_reference_answer",
    "expected_correctness",
    "critical_case",
    "material_error_if_missed",
    "curation_notes",
    "acceptable_selected_spans",
    "last_number_distractor_span",
    "template_family_id",
    "construction_provenance",
}


def validate_parser_result(
    record: Mapping[str, Any], output_text: str, *, name: str = "parser result"
) -> dict[str, Any]:
    try:
        checked = _load_frozen_validation().validate_parser_result(
            record, output_text, name=name
        )
    except Exception:
        raise LockedEvaluationError("parser result schema/invariants are invalid") from None
    if record.get("parser_version") != FROZEN_PARSER_VERSION:
        raise LockedEvaluationError("parser result frozen version binding is invalid")
    return checked


def derive_typed_decision(record: Mapping[str, Any], *, expected: bool = False) -> str:
    del expected
    try:
        return _load_frozen_validation().derive_typed_decision(record)
    except Exception:
        raise LockedEvaluationError("extraction does not derive a typed decision") from None


def typed_decision_class(decision: str) -> str:
    if isinstance(decision, str) and decision.startswith("present:"):
        value = decision.removeprefix("present:")
        if normalize_rational_literal(value) != value:
            raise LockedEvaluationError("present decision is not canonical")
        return "present"
    return _require_enum(decision, ("ambiguous", "no_answer"), "typed decision")


def validate_prediction_envelope(
    envelope: Mapping[str, Any], locked_input: Mapping[str, Any]
) -> dict[str, Any]:
    fields = {
        "schema_version",
        "case_id",
        "input_record_sha256",
        "parser_request_sha256",
        "parser_result",
    }
    _require_exact_fields(envelope, fields, "prediction envelope")
    if envelope["schema_version"] != PREDICTION_ENVELOPE_SCHEMA_VERSION:
        raise LockedEvaluationError("prediction envelope schema is invalid")
    locked = validate_locked_input(locked_input)
    if _require_case_id(envelope["case_id"]) != locked["case_id"]:
        raise LockedEvaluationError("prediction envelope case ID mismatch")
    if _require_sha256(
        envelope["input_record_sha256"], "prediction input record SHA-256"
    ) != sha256_bytes(canonical_json_bytes(dict(locked_input))):
        raise LockedEvaluationError("prediction input-record hash mismatch")
    request = project_parser_request(locked_input)
    if _require_sha256(
        envelope["parser_request_sha256"], "prediction request SHA-256"
    ) != sha256_bytes(canonical_json_bytes(request)):
        raise LockedEvaluationError("prediction request hash mismatch")
    validate_parser_result(envelope["parser_result"], locked["output_text"])
    return dict(envelope)


def build_prediction_envelope(
    locked_input: Mapping[str, Any], parser_result: Mapping[str, Any]
) -> dict[str, Any]:
    locked = validate_locked_input(locked_input)
    request = project_parser_request(locked_input)
    envelope = {
        "schema_version": PREDICTION_ENVELOPE_SCHEMA_VERSION,
        "case_id": locked["case_id"],
        "input_record_sha256": sha256_bytes(
            canonical_json_bytes(dict(locked_input))
        ),
        "parser_request_sha256": sha256_bytes(canonical_json_bytes(request)),
        "parser_result": dict(parser_result),
    }
    validate_prediction_envelope(envelope, locked_input)
    return envelope


_LEGACY_RESULT_FIELDS = {
    "parsed_answer",
    "parse_valid",
    "parse_error_type",
    "parse_ambiguous",
    "parse_strategy",
    "candidate_answers",
    "answer_format_warning",
}


def adapt_legacy_result(record: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return _load_frozen_validation().adapt_legacy_result(record)
    except Exception:
        raise LockedEvaluationError("legacy result schema/invariants are invalid") from None


def validate_legacy_prediction(
    record: Mapping[str, Any], locked_input: Mapping[str, Any]
) -> dict[str, Any]:
    fields = {
        "schema_version",
        "case_id",
        "input_record_sha256",
        "legacy_result",
        "adapter",
    }
    _require_exact_fields(record, fields, "legacy prediction")
    if record["schema_version"] != LEGACY_PREDICTION_SCHEMA_VERSION:
        raise LockedEvaluationError("legacy prediction schema is invalid")
    locked = validate_locked_input(locked_input)
    if _require_case_id(record["case_id"]) != locked["case_id"]:
        raise LockedEvaluationError("legacy prediction case ID mismatch")
    if _require_sha256(
        record["input_record_sha256"], "legacy input-record SHA-256"
    ) != sha256_bytes(canonical_json_bytes(dict(locked_input))):
        raise LockedEvaluationError("legacy input-record hash mismatch")
    result = record["legacy_result"]
    _require_exact_fields(result, _LEGACY_RESULT_FIELDS, "legacy result")
    _require_bool(result["parse_valid"], "legacy result parse_valid")
    _require_bool(result["parse_ambiguous"], "legacy result parse_ambiguous")
    if result["parsed_answer"] is not None and not isinstance(
        result["parsed_answer"], str
    ):
        raise LockedEvaluationError("legacy parsed_answer must be text or null")
    for field in (
        "parse_error_type",
        "parse_strategy",
        "answer_format_warning",
    ):
        if result[field] is not None and not isinstance(result[field], str):
            raise LockedEvaluationError(f"legacy result {field} must be text or null")
    candidates = result["candidate_answers"]
    if candidates is not None and (
        not isinstance(candidates, list)
        or any(not isinstance(item, str) for item in candidates)
    ):
        raise LockedEvaluationError(
            "legacy candidate_answers must be a text list or null"
        )
    adapted = adapt_legacy_result(result)
    _require_exact_fields(
        record["adapter"], {"typed_decision", "adapter_failure"}, "legacy adapter"
    )
    if not exact_json_equal(dict(record["adapter"]), adapted):
        raise LockedEvaluationError("persisted legacy adapter result is not derived")
    typed_decision_class(adapted["typed_decision"])
    return dict(record)


def build_legacy_prediction(
    locked_input: Mapping[str, Any], legacy_result: Mapping[str, Any]
) -> dict[str, Any]:
    locked = validate_locked_input(locked_input)
    record = {
        "schema_version": LEGACY_PREDICTION_SCHEMA_VERSION,
        "case_id": locked["case_id"],
        "input_record_sha256": sha256_bytes(
            canonical_json_bytes(dict(locked_input))
        ),
        "legacy_result": dict(legacy_result),
        "adapter": adapt_legacy_result(legacy_result),
    }
    validate_legacy_prediction(record, locked_input)
    return record


def validate_prediction_rows(
    predictions: Sequence[Mapping[str, Any]],
    legacy_predictions: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
    gates: Mapping[str, Any],
) -> list[str]:
    total = _require_int(
        gates["dataset_contract"]["total_cases"], "gate total cases", minimum=1
    )
    if not (
        len(predictions) == len(legacy_predictions) == len(locked_inputs) == total
    ):
        raise LockedEvaluationError("prediction bundle counts are not exact")
    ids = [validate_locked_input(item)["case_id"] for item in locked_inputs]
    if ids != sorted(set(ids)):
        raise LockedEvaluationError("locked input membership is not exact")
    prediction_ids: list[str] = []
    legacy_ids: list[str] = []
    for index, (prediction, legacy, locked) in enumerate(
        zip(predictions, legacy_predictions, locked_inputs, strict=True)
    ):
        validate_prediction_envelope(prediction, locked)
        validate_legacy_prediction(legacy, locked)
        prediction_ids.append(_require_case_id(prediction["case_id"]))
        legacy_ids.append(_require_case_id(legacy["case_id"]))
    if not exact_json_equal(prediction_ids, ids) or not exact_json_equal(
        legacy_ids, ids
    ):
        raise LockedEvaluationError("prediction ordering/membership mismatch")
    return ids


def build_frozen_v2_seal(
    predictions: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
    *,
    implementation_commit: str,
    sealed_utc: str,
) -> dict[str, Any]:
    ids = [item["case_id"] for item in predictions]
    seal = {
        "schema_version": FROZEN_PREDICTION_SEAL_SCHEMA_VERSION,
        "implementation_commit": _require_commit(
            implementation_commit, "implementation commit"
        ),
        "parser_version": FROZEN_PARSER_VERSION,
        "locked_inputs_sha256": sha256_bytes(
            canonical_jsonl_bytes(list(locked_inputs))
        ),
        "predictions_sha256": sha256_bytes(
            canonical_jsonl_bytes(list(predictions))
        ),
        "row_count": len(predictions),
        "ordered_case_ids": ids,
        "sealed_utc": _require_utc(sealed_utc, "sealed_utc"),
    }
    return seal


def _contains_prohibited_stage_p_key(key: str) -> bool:
    normalized = re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])", "_", key
    ).casefold().replace("-", "_")
    if normalized == "labels_accessed":
        return False
    segments = {item for item in normalized.split("_") if item}
    return bool(
        segments
        & {
            "label",
            "labels",
            "reference",
            "references",
            "correctness",
            "expected",
        }
    )


def _contains_prohibited_stage_p_value(value: str) -> bool:
    normalized = value.casefold().replace("\\", "/")
    segments = {
        item
        for item in re.split(r"[^a-z0-9]+", normalized)
        if item
    }
    return bool(
        segments
        & {
            "label",
            "labels",
            "reference",
            "references",
            "correctness",
            "expected",
        }
    ) or any(
        token in normalized
        for token in (
            "locked-label",
            "locked_label",
            "reference-answer",
            "reference_answer",
            "expected-answer",
            "expected_answer",
            "/labels/",
            "/references/",
            "/correctness/",
        )
    )


def assert_label_blind_payload(
    value: Any, *, path: str = "$", allow_access_attestation: bool = True
) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise LockedEvaluationError("Stage-P payload contains an invalid key")
            allowed = allow_access_attestation and key == "labels_accessed"
            if _contains_prohibited_stage_p_key(key) and not allowed:
                raise LockedEvaluationError("Stage-P payload contains a prohibited channel")
            assert_label_blind_payload(
                item,
                path=f"{path}.{key}",
                allow_access_attestation=allow_access_attestation,
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_label_blind_payload(
                item,
                path=f"{path}[{index}]",
                allow_access_attestation=allow_access_attestation,
            )
    elif isinstance(value, str) and _contains_prohibited_stage_p_value(value):
        raise LockedEvaluationError("Stage-P payload contains a prohibited value")


def validate_stage_p_environment(environment: Mapping[str, str]) -> None:
    _validate_stage_runtime_environment(environment, stage="P")


def validate_stage_e_environment(environment: Mapping[str, str]) -> None:
    _validate_stage_runtime_environment(environment, stage="E")


def _validate_stage_runtime_environment(
    environment: Mapping[str, str], *, stage: str
) -> None:
    if not isinstance(environment, Mapping):
        raise LockedEvaluationError(f"Stage-{stage} environment is not exact")
    expected = {
        *_STAGE_RUNTIME_ENVIRONMENT,
        "AZURE_CLIENT_ID",
        "IDENTITY_ENDPOINT",
        "IDENTITY_HEADER",
    }
    if set(environment) != expected or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in environment.items()
    ):
        raise LockedEvaluationError(
            f"Stage-{stage} environment exposes a prohibited channel or extra field"
        )
    if any(
        environment[name] != value
        for name, value in _STAGE_RUNTIME_ENVIRONMENT.items()
    ):
        raise LockedEvaluationError(
            f"Stage-{stage} environment runtime values are not exact"
        )
    if not _AZURE_CLIENT_ID_PATTERN.fullmatch(environment["AZURE_CLIENT_ID"]):
        raise LockedEvaluationError(
            f"Stage-{stage} managed-identity binding is malformed"
        )
    endpoint = urlsplit(environment["IDENTITY_ENDPOINT"])
    try:
        endpoint_ip = (
            None
            if endpoint.hostname == "localhost"
            else ipaddress.ip_address(endpoint.hostname or "")
        )
        endpoint.port
    except ValueError:
        raise LockedEvaluationError(
            f"Stage-{stage} managed-identity endpoint is malformed"
        ) from None
    if (
        endpoint.scheme != "http"
        or endpoint.username is not None
        or endpoint.password is not None
        or endpoint.query
        or endpoint.fragment
        or endpoint.path in {"", "/"}
        or (
            endpoint.hostname != "localhost"
            and (
                endpoint_ip is None
                or not (
                    endpoint_ip.is_loopback
                    or endpoint_ip.is_link_local
                    or endpoint_ip.is_private
                )
            )
        )
    ):
        raise LockedEvaluationError(
            f"Stage-{stage} managed-identity endpoint is malformed"
        )
    identity_header = environment["IDENTITY_HEADER"]
    if (
        not 16 <= len(identity_header) <= 4096
        or any(
            ord(character) < 0x21 or ord(character) > 0x7E
            for character in identity_header
        )
    ):
        raise LockedEvaluationError(
            f"Stage-{stage} managed-identity capability is malformed"
        )


def _validated_manifest_files(
    manifest: Mapping[str, Any], *, name: str
) -> list[dict[str, Any]]:
    files = manifest.get("files")
    if not isinstance(files, list):
        raise LockedEvaluationError(f"{name}.files must be a list")
    checked_files: list[dict[str, Any]] = []
    for index, item in enumerate(files):
        _require_exact_fields(
            item, {"path", "size", "sha256"}, f"{name}.files[{index}]"
        )
        checked_files.append(
            {
                "path": _require_string(
                    item["path"], f"{name}.files[{index}].path"
                ),
                "size": _require_int(
                    item["size"],
                    f"{name}.files[{index}].size",
                    minimum=0,
                ),
                "sha256": _require_sha256(
                    item["sha256"], f"{name}.files[{index}].sha256"
                ),
            }
        )
    return checked_files


def _metadata_by_suffix(
    manifest: Mapping[str, Any], suffix: str, *, name: str
) -> dict[str, Any]:
    files = _validated_manifest_files(manifest, name=name)
    matches = [
        item
        for item in files
        if item["path"] == suffix
    ]
    if len(matches) != 1:
        raise LockedEvaluationError(f"{name} does not bind exact member {suffix}")
    return matches[0]


def validate_locked_source_manifest(
    data: bytes,
    *,
    expected_manifest_sha256: str,
    expected_payload_sha256: str,
    parent_prefix: str,
    manifest_kind: str,
    payload_relative_path: str,
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    if sha256_bytes(data) != _require_sha256(
        expected_manifest_sha256, "expected source manifest SHA-256"
    ):
        raise LockedEvaluationError("source manifest hash mismatch")
    manifest = parse_json_strict(data, "locked source manifest")
    manifest_fields = {
        "schema_version",
        "manifest_kind",
        "protocol_commit",
        "protocol_bundle_sha256",
        "acceptance_gates_sha256",
        "created_utc",
        "parent_prefix",
        "ordered_case_ids",
        "counts",
        "schemas",
        "files",
        "reservation_sha256",
        "review_seals",
        "arbitration",
        "feature_counts",
        "visibility_ledger_sha256",
        "source_prefixes",
        "private_nonce",
        "model_inference_performed",
        "no_model_run_attestation",
        "manifest_uploaded_last",
    }
    _require_exact_fields(manifest, manifest_fields, "locked source manifest")
    if canonical_json_bytes(manifest) != data:
        raise LockedEvaluationError("locked source manifest is not canonical")
    try:
        _load_frozen_validation().validate_manifest(manifest)
    except Exception:
        raise LockedEvaluationError("locked source manifest schema is invalid") from None
    assert_label_blind_payload(
        {
            key: value
            for key, value in manifest.items()
            if key != "private_nonce"
        },
        allow_access_attestation=False,
    )
    if manifest_kind != "locked-inputs" or manifest["manifest_kind"] != "locked-inputs":
        raise LockedEvaluationError("Stage P accepts only the locked-input manifest")
    if manifest["parent_prefix"] != validate_registered_parent_prefix(parent_prefix):
        raise LockedEvaluationError("locked source manifest parent binding mismatch")
    expected_files = (
        "locked-inputs/.locked_inputs_reservation.json",
        "locked-inputs/locked_inputs.jsonl",
    )
    if payload_relative_path != expected_files[1]:
        raise LockedEvaluationError("locked source payload path is not registered")
    files = _validated_manifest_files(manifest, name="locked source manifest")
    if (
        not isinstance(files, list)
        or tuple(item["path"] for item in files) != expected_files
        or not exact_json_equal(
            manifest["counts"],
            {"cases": gates["dataset_contract"]["total_cases"]},
        )
        or not exact_json_equal(
            manifest["schemas"],
            {"locked_inputs": LOCKED_INPUT_SCHEMA_VERSION},
        )
        or not exact_json_equal(manifest["review_seals"], [])
        or not exact_json_equal(
            manifest["arbitration"],
            {"stage1": 0, "stage2": 0, "unresolved": 0},
        )
        or manifest["reservation_sha256"] != files[0]["sha256"]
        or manifest["model_inference_performed"] is not False
        or manifest["no_model_run_attestation"] is not True
        or manifest["manifest_uploaded_last"] is not True
    ):
        raise LockedEvaluationError(
            "locked source manifest member bindings are not exact"
        )
    feature_counts = manifest["feature_counts"]
    source_prefixes = manifest["source_prefixes"]
    if (
        not isinstance(feature_counts, Mapping)
        or not set(feature_counts).issubset(_STAGE_P_FEATURE_COUNT_FIELDS)
        or any(type(value) is not int or value < 0 for value in feature_counts.values())
        or not isinstance(source_prefixes, list)
        or len(source_prefixes) > 16
        or len(source_prefixes) != len(set(source_prefixes))
        or any(
            not isinstance(value, str)
            or _SOURCE_PREFIX_PATTERN.fullmatch(value) is None
            for value in source_prefixes
        )
    ):
        raise LockedEvaluationError(
            "locked source manifest contains a generic metadata extension"
        )
    ids = manifest["ordered_case_ids"]
    expected_total = gates["dataset_contract"]["total_cases"]
    if (
        not isinstance(ids, list)
        or len(ids) != expected_total
        or ids != sorted(set(ids))
        or any(_CASE_ID_PATTERN.fullmatch(item) is None for item in ids)
    ):
        raise LockedEvaluationError("source manifest case membership is invalid")
    metadata = _metadata_by_suffix(
        manifest, payload_relative_path, name="locked source manifest"
    )
    if metadata["sha256"] != _require_sha256(
        expected_payload_sha256, "expected source payload SHA-256"
    ):
        raise LockedEvaluationError("source payload hash binding mismatch")
    return {
        "manifest_sha256": sha256_bytes(data),
        "payload_sha256": metadata["sha256"],
        "payload_size": metadata["size"],
        "ordered_case_ids": list(ids),
    }


_LOCKED_INPUT_SOURCE_BINDING_FIELDS = frozenset(
    {
        "locked_input_reservation_blob",
        "locked_input_reservation_sha256",
        "locked_input_private_nonce_sha256",
        "locked_input_reservation_etag",
        "locked_input_manifest_blob",
        "locked_input_manifest_sha256",
        "locked_input_manifest_etag",
        "locked_manifest_sha256",
    }
)


def validate_locked_input_source_binding(
    *,
    reservation_bytes: bytes,
    reservation_blob: str,
    reservation_etag: str,
    manifest_bytes: bytes,
    manifest_blob: str,
    manifest_etag: str,
    locked_manifest_bytes: bytes,
    expected_locked_manifest_sha256: str,
    expected_manifest_sha256: str,
    expected_payload_sha256: str | None,
    parent_prefix: str,
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    parent = validate_registered_parent_prefix(parent_prefix)
    reservation_relative = "locked-inputs/.locked_inputs_reservation.json"
    manifest_relative = "locked-inputs/locked_inputs_manifest.json"
    payload_relative = "locked-inputs/locked_inputs.jsonl"
    if (
        reservation_blob != f"{parent}/{reservation_relative}"
        or manifest_blob != f"{parent}/{manifest_relative}"
    ):
        raise LockedEvaluationError("locked-input reservation/manifest path is not exact")
    locked_manifest_sha256 = _require_sha256(
        expected_locked_manifest_sha256, "locked overall manifest SHA-256"
    )
    if sha256_bytes(locked_manifest_bytes) != locked_manifest_sha256:
        raise LockedEvaluationError("locked overall manifest hash mismatch")
    overall = parse_json_strict(locked_manifest_bytes, "locked overall manifest")
    try:
        _load_frozen_validation().validate_manifest(overall)
    except Exception:
        raise LockedEvaluationError("locked overall manifest is invalid") from None
    if (
        overall.get("manifest_kind") != "manifests"
        or overall.get("parent_prefix") != parent
    ):
        raise LockedEvaluationError("locked overall manifest identity mismatch")
    overall_reservation = _metadata_by_suffix(
        overall, reservation_relative, name="locked overall manifest"
    )
    overall_manifest = _metadata_by_suffix(
        overall, manifest_relative, name="locked overall manifest"
    )
    reservation_sha256 = sha256_bytes(reservation_bytes)
    manifest_sha256 = sha256_bytes(manifest_bytes)
    if (
        overall_reservation["sha256"] != reservation_sha256
        or overall_reservation["size"] != len(reservation_bytes)
        or overall_manifest["sha256"] != manifest_sha256
        or overall_manifest["size"] != len(manifest_bytes)
        or manifest_sha256
        != _require_sha256(
            expected_manifest_sha256, "locked input manifest SHA-256"
        )
    ):
        raise LockedEvaluationError(
            "locked overall manifest source-member binding mismatch"
        )
    manifest = parse_json_strict(manifest_bytes, "locked input manifest")
    payload_metadata = _metadata_by_suffix(
        manifest, payload_relative, name="locked input manifest"
    )
    source = validate_locked_source_manifest(
        manifest_bytes,
        expected_manifest_sha256=manifest_sha256,
        expected_payload_sha256=(
            payload_metadata["sha256"]
            if expected_payload_sha256 is None
            else expected_payload_sha256
        ),
        parent_prefix=parent,
        manifest_kind="locked-inputs",
        payload_relative_path=payload_relative,
        gates=gates,
    )
    leaf_reservation = _metadata_by_suffix(
        manifest, reservation_relative, name="locked input manifest"
    )
    reservation = parse_json_strict(
        reservation_bytes, "locked input preregistered reservation"
    )
    try:
        checked_reservation = _load_frozen_validation().validate_reservation(
            reservation, leaf="locked-inputs", parent_prefix=parent
        )
    except Exception:
        raise LockedEvaluationError(
            "locked input preregistered reservation is invalid"
        ) from None
    if (
        canonical_json_bytes(reservation) != reservation_bytes
        or leaf_reservation["sha256"] != reservation_sha256
        or leaf_reservation["size"] != len(reservation_bytes)
        or manifest["reservation_sha256"] != reservation_sha256
        or type(manifest.get("private_nonce")) is not str
        or type(checked_reservation.get("private_nonce")) is not str
        or manifest["private_nonce"] != checked_reservation["private_nonce"]
    ):
        raise LockedEvaluationError(
            "locked input nonce is not bound to its preregistered reservation"
        )
    binding = {
        "locked_input_reservation_blob": reservation_blob,
        "locked_input_reservation_sha256": reservation_sha256,
        "locked_input_private_nonce_sha256": sha256_bytes(
            checked_reservation["private_nonce"].encode("utf-8")
        ),
        "locked_input_reservation_etag": _require_string(
            reservation_etag, "locked input reservation ETag"
        ),
        "locked_input_manifest_blob": manifest_blob,
        "locked_input_manifest_sha256": manifest_sha256,
        "locked_input_manifest_etag": _require_string(
            manifest_etag, "locked input manifest ETag"
        ),
        "locked_manifest_sha256": locked_manifest_sha256,
    }
    return {"binding": binding, "source": source}


def authenticate_locked_input_source(
    service: Any,
    container: str,
    *,
    parent_prefix: str,
    expected_locked_manifest_sha256: str,
    expected_manifest_sha256: str,
    expected_payload_sha256: str | None,
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    parent = validate_registered_parent_prefix(parent_prefix)
    reservation_blob = f"{parent}/locked-inputs/.locked_inputs_reservation.json"
    manifest_blob = f"{parent}/locked-inputs/locked_inputs_manifest.json"
    locked_manifest_blob = f"{parent}/manifests/locked_manifest.json"
    locked_manifest_bytes, _ = download_stable_blob(
        service, container, locked_manifest_blob
    )
    manifest_bytes, manifest_etag = download_stable_blob(
        service, container, manifest_blob
    )
    reservation_bytes, reservation_etag = download_stable_blob(
        service, container, reservation_blob
    )
    checked = validate_locked_input_source_binding(
        reservation_bytes=reservation_bytes,
        reservation_blob=reservation_blob,
        reservation_etag=reservation_etag,
        manifest_bytes=manifest_bytes,
        manifest_blob=manifest_blob,
        manifest_etag=manifest_etag,
        locked_manifest_bytes=locked_manifest_bytes,
        expected_locked_manifest_sha256=expected_locked_manifest_sha256,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_payload_sha256=expected_payload_sha256,
        parent_prefix=parent,
        gates=gates,
    )
    return {
        **checked,
        "reservation_bytes": reservation_bytes,
        "manifest_bytes": manifest_bytes,
        "locked_manifest_bytes": locked_manifest_bytes,
    }


def validate_locked_labels_manifest(
    data: bytes,
    *,
    expected_manifest_sha256: str,
    expected_payload_sha256: str,
    parent_prefix: str,
    payload_relative_path: str,
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    if sha256_bytes(data) != _require_sha256(
        expected_manifest_sha256, "expected label manifest SHA-256"
    ):
        raise LockedEvaluationError("label manifest hash mismatch")
    manifest = parse_json_strict(data, "locked label manifest")
    frozen = _load_frozen_validation()
    try:
        frozen.validate_manifest(manifest)
    except Exception:
        raise LockedEvaluationError("locked label manifest schema is invalid") from None
    expected_files = tuple(
        f"locked-labels/{name}"
        for name in frozen.REGISTERED_LEAF_MEMBERS["locked-labels"][:-1]
    )
    files = _validated_manifest_files(manifest, name="locked label manifest")
    if (
        manifest["manifest_kind"] != "locked-labels"
        or manifest["parent_prefix"] != validate_registered_parent_prefix(parent_prefix)
        or tuple(item["path"] for item in files) != expected_files
        or payload_relative_path
        != "locked-labels/locked_reference_labels.jsonl"
    ):
        raise LockedEvaluationError("locked label manifest bindings are not exact")
    ids = manifest["ordered_case_ids"]
    expected_total = gates["dataset_contract"]["total_cases"]
    if (
        not isinstance(ids, list)
        or len(ids) != expected_total
        or ids != sorted(set(ids))
        or any(_CASE_ID_PATTERN.fullmatch(item) is None for item in ids)
        or not exact_json_equal(
            manifest["counts"], {"cases": expected_total}
        )
        or not exact_json_equal(
            manifest["schemas"],
            {"final_labels": FINAL_LABEL_SCHEMA_VERSION},
        )
        or manifest["manifest_uploaded_last"] is not True
    ):
        raise LockedEvaluationError("locked label manifest membership is invalid")
    metadata = _metadata_by_suffix(
        manifest, payload_relative_path, name="locked label manifest"
    )
    if metadata["sha256"] != _require_sha256(
        expected_payload_sha256, "expected label payload SHA-256"
    ):
        raise LockedEvaluationError("label payload hash binding mismatch")
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_bytes(data),
        "payload_sha256": metadata["sha256"],
        "payload_size": metadata["size"],
        "ordered_case_ids": ids,
    }


def validate_locked_labels_bytes(
    data: bytes,
    gates: Mapping[str, Any],
    *,
    expected_sha256: str,
    expected_ordered_case_ids: Sequence[str],
) -> list[dict[str, Any]]:
    if sha256_bytes(data) != _require_sha256(
        expected_sha256, "expected locked-label payload SHA-256"
    ):
        raise LockedEvaluationError("locked-label payload hash mismatch")
    labels = parse_jsonl_strict(data, "locked_reference_labels.jsonl")
    label_index = _labels_index(labels, gates)
    ids = list(label_index)
    expected_ids = [
        _require_case_id(item, "expected locked-label case ID")
        for item in expected_ordered_case_ids
    ]
    if (
        expected_ids != sorted(set(expected_ids))
        or ids != expected_ids
        or [item.get("case_id") for item in labels] != expected_ids
    ):
        raise LockedEvaluationError(
            "locked-label payload differs from the sealed case universe"
        )
    return labels


def build_reservation(
    *,
    leaf: str,
    prefix: str,
    authorization_id: str,
    created_utc: str,
    nonce: str,
    parent_prefix: str | None = None,
    stage: str | None = None,
    retry_kind: str = "none",
    execution_id: str | None = None,
) -> dict[str, Any]:
    checked_nonce = _require_string(nonce, "reservation nonce")
    if len(checked_nonce.encode("utf-8")) < 16:
        raise LockedEvaluationError("reservation nonce is too short")
    checked_leaf = _require_enum(
        leaf, ("predictions", "scores"), "reservation leaf"
    )
    checked_prefix = normalize_blob_prefix(prefix)
    attempt_values = (parent_prefix, stage, execution_id)
    if any(value is not None for value in attempt_values):
        if any(value is None for value in attempt_values):
            raise LockedEvaluationError(
                "reservation attempt binding is incomplete"
            )
        checked_prefix = validate_exact_attempt_prefix(
            checked_prefix,
            parent_prefix,
            authorization_id,
            checked_leaf,
            stage,
            retry_kind,
            execution_id,
        )
    elif retry_kind != "none":
        raise LockedEvaluationError(
            "retry reservation requires its exact attempt binding"
        )
    return {
        "schema_version": RESERVATION_SCHEMA_VERSION,
        "leaf": checked_leaf,
        "prefix": checked_prefix,
        "authorization_id": validate_authorization_id(authorization_id),
        "created_utc": _require_utc(created_utc, "reservation created_utc"),
        "nonce": checked_nonce,
        "overwrite": False,
    }


def build_prediction_request_manifest(
    *,
    authorization_id: str,
    parent_prefix: str,
    prediction_prefix: str,
    implementation_commit: str,
    image_digest: str,
    config_sha256: str,
    authorization_lock_sha256: str,
    authorization_manifest_sha256: str,
    implementation_manifest_sha256: str,
    locked_manifest_sha256: str,
    input_receipt_sha256: str,
    locked_input_reservation_blob: str,
    locked_input_reservation_sha256: str,
    locked_input_private_nonce_sha256: str,
    locked_input_reservation_etag: str,
    locked_input_blob: str,
    locked_input_sha256: str,
    locked_input_etag: str,
    locked_input_manifest_blob: str,
    locked_input_manifest_sha256: str,
    locked_input_manifest_etag: str,
    visibility_blob: str,
    visibility_sha256: str,
    visibility_etag: str,
    ordered_case_ids: Sequence[str],
    created_utc: str,
    retry_kind: str = "none",
    execution_id: str | None = None,
) -> dict[str, Any]:
    parent = validate_registered_parent_prefix(parent_prefix)
    authorization = validate_authorization_id(authorization_id)
    if retry_kind == "none":
        attempt_execution_id = (
            "primary-prefix-binding"
            if execution_id is None
            else _require_string(execution_id, "prediction execution_id")
        )
    else:
        attempt_execution_id = _require_string(
            execution_id, "prediction retry execution_id"
        )
    attempt_prefixes = evaluation_attempt_prefixes(
        parent,
        authorization,
        "P",
        retry_kind,
        attempt_execution_id,
    )
    expected_input_blob = f"{parent}/locked-inputs/locked_inputs.jsonl"
    expected_input_reservation_blob = (
        f"{parent}/locked-inputs/.locked_inputs_reservation.json"
    )
    expected_input_manifest_blob = (
        f"{parent}/locked-inputs/locked_inputs_manifest.json"
    )
    expected_visibility_blob = (
        f"{attempt_prefixes['visibility']}/stage_p_visibility.json"
    )
    if (
        locked_input_reservation_blob != expected_input_reservation_blob
        or locked_input_blob != expected_input_blob
        or locked_input_manifest_blob != expected_input_manifest_blob
        or visibility_blob != expected_visibility_blob
    ):
        raise LockedEvaluationError(
            "prediction request source/visibility Blob names are not exact"
        )
    ids = [_require_case_id(item) for item in ordered_case_ids]
    if ids != sorted(set(ids)):
        raise LockedEvaluationError("request manifest membership is invalid")
    checked_config_sha256 = _require_sha256(config_sha256, "config SHA-256")
    record = {
        "schema_version": PREDICTION_REQUEST_MANIFEST_SCHEMA_VERSION,
        "authorization_id": authorization,
        "registered_parent_prefix": parent,
        "prediction_prefix": validate_exact_attempt_prefix(
            prediction_prefix,
            parent,
            authorization,
            "predictions",
            "P",
            retry_kind,
            attempt_execution_id,
        ),
        "implementation_commit": _require_commit(
            implementation_commit, "implementation commit"
        ),
        "image_digest": _require_image_digest(image_digest, "image digest"),
        "config_sha256": checked_config_sha256,
        "runtime_config_sha256": checked_config_sha256,
        "authorization_lock_sha256": _require_sha256(
            authorization_lock_sha256, "authorization lock SHA-256"
        ),
        "authorization_manifest_sha256": _require_sha256(
            authorization_manifest_sha256, "authorization manifest SHA-256"
        ),
        "implementation_manifest_sha256": _require_sha256(
            implementation_manifest_sha256, "implementation manifest SHA-256"
        ),
        "locked_manifest_sha256": _require_sha256(
            locked_manifest_sha256, "locked manifest SHA-256"
        ),
        "input_receipt_sha256": _require_sha256(
            input_receipt_sha256, "INPUTS_READ receipt SHA-256"
        ),
        "parser_source_sha256": FROZEN_PARSER_SOURCE_SHA256,
        "parser_version": FROZEN_PARSER_VERSION,
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": FROZEN_PROTOCOL_BUNDLE_SHA256,
        "acceptance_gates_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
        "locked_input_reservation_blob": normalize_blob_prefix(
            locked_input_reservation_blob
        ),
        "locked_input_reservation_sha256": _require_sha256(
            locked_input_reservation_sha256,
            "locked input reservation SHA-256",
        ),
        "locked_input_private_nonce_sha256": _require_sha256(
            locked_input_private_nonce_sha256,
            "locked input private nonce SHA-256",
        ),
        "locked_input_reservation_etag": _require_string(
            locked_input_reservation_etag, "locked input reservation ETag"
        ),
        "locked_input_blob": normalize_blob_prefix(locked_input_blob),
        "locked_input_sha256": _require_sha256(
            locked_input_sha256, "locked input SHA-256"
        ),
        "locked_input_etag": _require_string(locked_input_etag, "locked input ETag"),
        "locked_input_manifest_blob": normalize_blob_prefix(
            locked_input_manifest_blob
        ),
        "locked_input_manifest_sha256": _require_sha256(
            locked_input_manifest_sha256, "locked input manifest SHA-256"
        ),
        "source_manifest_sha256": _require_sha256(
            locked_input_manifest_sha256, "source manifest SHA-256"
        ),
        "locked_input_manifest_etag": _require_string(
            locked_input_manifest_etag, "locked input manifest ETag"
        ),
        "visibility_blob": normalize_blob_prefix(visibility_blob),
        "visibility_sha256": _require_sha256(
            visibility_sha256, "Stage-P visibility SHA-256"
        ),
        "visibility_etag": _require_string(
            visibility_etag, "Stage-P visibility ETag"
        ),
        "ordered_case_ids": ids,
        "case_universe_sha256": case_universe_sha256(ids),
        "request_schema_version": PARSER_REQUEST_SCHEMA_VERSION,
        "result_schema_version": PARSER_RESULT_SCHEMA_VERSION,
        "labels_accessed": False,
        "target_model_loaded": False,
        "target_model_downloaded": False,
        "target_model_inference": False,
        "gpu_used": False,
        "created_utc": _require_utc(created_utc, "request manifest created_utc"),
    }
    assert_label_blind_payload(record)
    return record


def validate_prediction_request_manifest(
    record: Mapping[str, Any],
    *,
    expected_authorization_id: str,
    expected_parent_prefix: str,
    expected_retry_kind: str = "none",
    expected_execution_id: str | None = None,
) -> dict[str, Any]:
    try:
        rebuilt = build_prediction_request_manifest(
            authorization_id=record["authorization_id"],
            parent_prefix=record["registered_parent_prefix"],
            prediction_prefix=record["prediction_prefix"],
            implementation_commit=record["implementation_commit"],
            image_digest=record["image_digest"],
            config_sha256=record["config_sha256"],
            authorization_lock_sha256=record["authorization_lock_sha256"],
            authorization_manifest_sha256=record[
                "authorization_manifest_sha256"
            ],
            implementation_manifest_sha256=record[
                "implementation_manifest_sha256"
            ],
            locked_manifest_sha256=record["locked_manifest_sha256"],
            input_receipt_sha256=record["input_receipt_sha256"],
            locked_input_reservation_blob=record[
                "locked_input_reservation_blob"
            ],
            locked_input_reservation_sha256=record[
                "locked_input_reservation_sha256"
            ],
            locked_input_private_nonce_sha256=record[
                "locked_input_private_nonce_sha256"
            ],
            locked_input_reservation_etag=record[
                "locked_input_reservation_etag"
            ],
            locked_input_blob=record["locked_input_blob"],
            locked_input_sha256=record["locked_input_sha256"],
            locked_input_etag=record["locked_input_etag"],
            locked_input_manifest_blob=record[
                "locked_input_manifest_blob"
            ],
            locked_input_manifest_sha256=record[
                "locked_input_manifest_sha256"
            ],
            locked_input_manifest_etag=record[
                "locked_input_manifest_etag"
            ],
            visibility_blob=record["visibility_blob"],
            visibility_sha256=record["visibility_sha256"],
            visibility_etag=record["visibility_etag"],
            ordered_case_ids=record["ordered_case_ids"],
            created_utc=record["created_utc"],
            retry_kind=expected_retry_kind,
            execution_id=expected_execution_id,
        )
    except (KeyError, TypeError, LockedEvaluationError):
        raise LockedEvaluationError(
            "prediction request manifest schema is invalid"
        ) from None
    if (
        not exact_json_equal(dict(record), rebuilt)
        or record["authorization_id"]
        != validate_authorization_id(expected_authorization_id)
        or record["registered_parent_prefix"]
        != validate_registered_parent_prefix(expected_parent_prefix)
    ):
        raise LockedEvaluationError(
            "prediction request manifest immutable bindings are invalid"
        )
    return rebuilt


def build_locked_prediction_seal(
    *,
    request_manifest: Mapping[str, Any],
    predictions: Sequence[Mapping[str, Any]],
    legacy_predictions: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
    sealed_utc: str,
    retry_kind: str = "none",
    execution_id: str | None = None,
) -> dict[str, Any]:
    validate_prediction_request_manifest(
        request_manifest,
        expected_authorization_id=request_manifest["authorization_id"],
        expected_parent_prefix=request_manifest["registered_parent_prefix"],
        expected_retry_kind=retry_kind,
        expected_execution_id=execution_id,
    )
    ids = [item["case_id"] for item in predictions]
    frozen = build_frozen_v2_seal(
        predictions,
        locked_inputs,
        implementation_commit=request_manifest["implementation_commit"],
        sealed_utc=sealed_utc,
    )
    record = {
        "schema_version": LOCKED_PREDICTION_SEAL_SCHEMA_VERSION,
        "authorization_id": request_manifest["authorization_id"],
        "registered_parent_prefix": request_manifest["registered_parent_prefix"],
        "prediction_prefix": request_manifest["prediction_prefix"],
        "implementation_commit": request_manifest["implementation_commit"],
        "image_digest": request_manifest["image_digest"],
        "config_sha256": request_manifest["config_sha256"],
        "runtime_config_sha256": request_manifest["runtime_config_sha256"],
        "authorization_lock_sha256": request_manifest[
            "authorization_lock_sha256"
        ],
        "authorization_manifest_sha256": request_manifest[
            "authorization_manifest_sha256"
        ],
        "implementation_manifest_sha256": request_manifest[
            "implementation_manifest_sha256"
        ],
        "locked_manifest_sha256": request_manifest["locked_manifest_sha256"],
        "input_receipt_sha256": request_manifest["input_receipt_sha256"],
        "parser_implementation_commit": FROZEN_PARSER_IMPLEMENTATION_COMMIT,
        "parser_source_sha256": FROZEN_PARSER_SOURCE_SHA256,
        "parser_version": FROZEN_PARSER_VERSION,
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": FROZEN_PROTOCOL_BUNDLE_SHA256,
        "acceptance_gates_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
        "locked_input_reservation_blob": request_manifest[
            "locked_input_reservation_blob"
        ],
        "locked_input_reservation_sha256": request_manifest[
            "locked_input_reservation_sha256"
        ],
        "locked_input_private_nonce_sha256": request_manifest[
            "locked_input_private_nonce_sha256"
        ],
        "locked_input_reservation_etag": request_manifest[
            "locked_input_reservation_etag"
        ],
        "locked_input_blob": request_manifest["locked_input_blob"],
        "locked_input_sha256": request_manifest["locked_input_sha256"],
        "locked_input_etag": request_manifest["locked_input_etag"],
        "locked_input_manifest_blob": request_manifest[
            "locked_input_manifest_blob"
        ],
        "locked_input_manifest_sha256": request_manifest[
            "locked_input_manifest_sha256"
        ],
        "source_manifest_sha256": request_manifest["source_manifest_sha256"],
        "locked_input_manifest_etag": request_manifest[
            "locked_input_manifest_etag"
        ],
        "visibility_blob": request_manifest["visibility_blob"],
        "visibility_sha256": request_manifest["visibility_sha256"],
        "visibility_etag": request_manifest["visibility_etag"],
        "prediction_request_manifest_sha256": sha256_bytes(
            canonical_json_bytes(dict(request_manifest))
        ),
        "parser_v2_predictions_sha256": sha256_bytes(
            canonical_jsonl_bytes(list(predictions))
        ),
        "legacy_predictions_sha256": sha256_bytes(
            canonical_jsonl_bytes(list(legacy_predictions))
        ),
        "frozen_v2_seal": frozen,
        "row_count": len(ids),
        "ordered_case_ids": ids,
        "case_universe_sha256": case_universe_sha256(ids),
        "labels_accessed": False,
        "target_model_loaded": False,
        "target_model_downloaded": False,
        "target_model_inference": False,
        "gpu_used": False,
        "sealed_utc": _require_utc(sealed_utc, "prediction sealed_utc"),
    }
    assert_label_blind_payload(record)
    return record


_LOCKED_PREDICTION_SEAL_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "prediction_prefix",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "runtime_config_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "locked_manifest_sha256",
        "input_receipt_sha256",
        "parser_implementation_commit",
        "parser_source_sha256",
        "parser_version",
        "protocol_commit",
        "protocol_bundle_sha256",
        "acceptance_gates_sha256",
        "locked_input_reservation_blob",
        "locked_input_reservation_sha256",
        "locked_input_private_nonce_sha256",
        "locked_input_reservation_etag",
        "locked_input_blob",
        "locked_input_sha256",
        "locked_input_etag",
        "locked_input_manifest_blob",
        "locked_input_manifest_sha256",
        "source_manifest_sha256",
        "locked_input_manifest_etag",
        "visibility_blob",
        "visibility_sha256",
        "visibility_etag",
        "prediction_request_manifest_sha256",
        "parser_v2_predictions_sha256",
        "legacy_predictions_sha256",
        "frozen_v2_seal",
        "row_count",
        "ordered_case_ids",
        "case_universe_sha256",
        "labels_accessed",
        "target_model_loaded",
        "target_model_downloaded",
        "target_model_inference",
        "gpu_used",
        "sealed_utc",
    }
)


def validate_locked_prediction_seal_metadata(
    record: Mapping[str, Any],
    *,
    request_manifest_bytes: bytes,
    prediction_manifest: Mapping[str, Any],
    expected_authorization_id: str,
    expected_parent_prefix: str,
    expected_retry_kind: str = "none",
    expected_execution_id: str | None = None,
) -> dict[str, Any]:
    """Authenticate a prediction seal without reading locked prediction rows."""

    _require_exact_fields(
        record, _LOCKED_PREDICTION_SEAL_FIELDS, "locked prediction seal"
    )
    if record["schema_version"] != LOCKED_PREDICTION_SEAL_SCHEMA_VERSION:
        raise LockedEvaluationError("locked prediction seal schema mismatch")
    authorization = validate_authorization_id(expected_authorization_id)
    parent = validate_registered_parent_prefix(expected_parent_prefix)
    attempt_execution_id = (
        "primary-prefix-binding"
        if expected_retry_kind == "none" and expected_execution_id is None
        else _require_string(
            expected_execution_id, "expected prediction execution_id"
        )
    )
    prefixes = evaluation_attempt_prefixes(
        parent,
        authorization,
        "P",
        expected_retry_kind,
        attempt_execution_id,
    )
    if (
        record["authorization_id"] != authorization
        or record["registered_parent_prefix"] != parent
        or record["prediction_prefix"] != prefixes["predictions"]
    ):
        raise LockedEvaluationError("locked prediction authorization binding mismatch")
    fixed = {
        "parser_implementation_commit": FROZEN_PARSER_IMPLEMENTATION_COMMIT,
        "parser_source_sha256": FROZEN_PARSER_SOURCE_SHA256,
        "parser_version": FROZEN_PARSER_VERSION,
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": FROZEN_PROTOCOL_BUNDLE_SHA256,
        "acceptance_gates_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
    }
    if any(
        not exact_json_equal(record[field], value)
        for field, value in fixed.items()
    ):
        raise LockedEvaluationError("locked prediction frozen binding mismatch")
    if any(
        record[field] is not False
        for field in (
            "labels_accessed",
            "target_model_loaded",
            "target_model_downloaded",
            "target_model_inference",
            "gpu_used",
        )
    ):
        raise LockedEvaluationError("prediction seal violates label/model/GPU boundary")
    _require_commit(record["implementation_commit"], "seal implementation commit")
    _require_image_digest(record["image_digest"], "seal image digest")
    for field in (
        "config_sha256",
        "runtime_config_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "locked_manifest_sha256",
        "input_receipt_sha256",
        "locked_input_reservation_sha256",
        "locked_input_private_nonce_sha256",
        "locked_input_sha256",
        "locked_input_manifest_sha256",
        "source_manifest_sha256",
        "visibility_sha256",
        "prediction_request_manifest_sha256",
        "parser_v2_predictions_sha256",
        "legacy_predictions_sha256",
        "case_universe_sha256",
    ):
        _require_sha256(record[field], f"seal {field}")
    for field in (
        "locked_input_reservation_blob",
        "locked_input_reservation_etag",
        "locked_input_blob",
        "locked_input_etag",
        "locked_input_manifest_blob",
        "locked_input_manifest_etag",
        "visibility_blob",
        "visibility_etag",
    ):
        _require_string(record[field], f"seal {field}")
    if (
        record["runtime_config_sha256"] != record["config_sha256"]
        or record["source_manifest_sha256"]
        != record["locked_input_manifest_sha256"]
        or record["prediction_request_manifest_sha256"]
        != sha256_bytes(request_manifest_bytes)
    ):
        raise LockedEvaluationError("locked prediction provenance aliases mismatch")
    request = parse_json_strict(
        request_manifest_bytes, "prediction request manifest"
    )
    validate_prediction_request_manifest(
        request,
        expected_authorization_id=authorization,
        expected_parent_prefix=parent,
        expected_retry_kind=expected_retry_kind,
        expected_execution_id=expected_execution_id,
    )
    if canonical_json_bytes(dict(request)) != request_manifest_bytes:
        raise LockedEvaluationError(
            "prediction request manifest bytes are not canonical"
        )
    request_bindings = (
        "authorization_id",
        "registered_parent_prefix",
        "prediction_prefix",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "runtime_config_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "locked_manifest_sha256",
        "input_receipt_sha256",
        "parser_source_sha256",
        "parser_version",
        "protocol_commit",
        "protocol_bundle_sha256",
        "acceptance_gates_sha256",
        "locked_input_reservation_blob",
        "locked_input_reservation_sha256",
        "locked_input_private_nonce_sha256",
        "locked_input_reservation_etag",
        "locked_input_blob",
        "locked_input_sha256",
        "locked_input_etag",
        "locked_input_manifest_blob",
        "locked_input_manifest_sha256",
        "source_manifest_sha256",
        "locked_input_manifest_etag",
        "visibility_blob",
        "visibility_sha256",
        "visibility_etag",
        "ordered_case_ids",
        "case_universe_sha256",
    )
    if any(
        not exact_json_equal(request.get(field), record[field])
        for field in request_bindings
    ):
        raise LockedEvaluationError(
            "prediction request manifest differs from its seal"
        )
    if (
        record["visibility_blob"]
        != f"{prefixes['visibility']}/stage_p_visibility.json"
    ):
        raise LockedEvaluationError("Stage-P visibility binding mismatch")
    metadata = prediction_manifest.get("payload_members")
    if not isinstance(metadata, list):
        raise LockedEvaluationError("prediction manifest payload metadata is invalid")
    by_name = {
        item.get("name"): item for item in metadata if isinstance(item, Mapping)
    }
    required_members = set(PREDICTION_MEMBER_NAMES[:-1])
    if set(by_name) != required_members:
        raise LockedEvaluationError("prediction manifest payload metadata is not exact")
    if (
        by_name["prediction_request_manifest.json"].get("sha256")
        != record["prediction_request_manifest_sha256"]
        or by_name["parser_v2_locked_predictions.jsonl"].get("sha256")
        != record["parser_v2_predictions_sha256"]
        or by_name["legacy_locked_predictions.jsonl"].get("sha256")
        != record["legacy_predictions_sha256"]
        or prediction_manifest.get("prediction_seal_sha256")
        != by_name["prediction_seal.json"].get("sha256")
    ):
        raise LockedEvaluationError(
            "prediction seal differs from prediction manifest metadata"
        )
    ids = [_require_case_id(item) for item in record["ordered_case_ids"]]
    frozen = record["frozen_v2_seal"]
    _require_exact_fields(
        frozen,
        {
            "schema_version",
            "implementation_commit",
            "parser_version",
            "locked_inputs_sha256",
            "predictions_sha256",
            "row_count",
            "ordered_case_ids",
            "sealed_utc",
        },
        "frozen v2 seal",
    )
    if (
        ids != sorted(set(ids))
        or ids != request["ordered_case_ids"]
        or ids != prediction_manifest.get("ordered_case_ids")
        or _require_int(record["row_count"], "seal row_count") != len(ids)
        or record["case_universe_sha256"] != case_universe_sha256(ids)
        or frozen["schema_version"] != FROZEN_PREDICTION_SEAL_SCHEMA_VERSION
        or frozen["implementation_commit"] != record["implementation_commit"]
        or frozen["parser_version"] != FROZEN_PARSER_VERSION
        or frozen["predictions_sha256"] != record["parser_v2_predictions_sha256"]
        or frozen["locked_inputs_sha256"] != record["locked_input_sha256"]
        or _require_int(frozen["row_count"], "frozen seal row_count") != len(ids)
        or not exact_json_equal(frozen["ordered_case_ids"], ids)
        or prediction_manifest.get("frozen_prediction_seal_sha256")
        != sha256_bytes(canonical_json_bytes(frozen))
    ):
        raise LockedEvaluationError("prediction seal metadata membership mismatch")
    _require_utc(record["sealed_utc"], "prediction seal sealed_utc")
    _require_utc(frozen["sealed_utc"], "frozen v2 seal sealed_utc")
    assert_label_blind_payload(record)
    return dict(record)


def validate_locked_prediction_seal(
    record: Mapping[str, Any],
    *,
    request_manifest_bytes: bytes,
    predictions_bytes: bytes,
    legacy_predictions_bytes: bytes,
    expected_authorization_id: str,
    expected_parent_prefix: str,
    expected_retry_kind: str = "none",
    expected_execution_id: str | None = None,
) -> dict[str, Any]:
    _require_exact_fields(
        record, _LOCKED_PREDICTION_SEAL_FIELDS, "locked prediction seal"
    )
    if record["schema_version"] != LOCKED_PREDICTION_SEAL_SCHEMA_VERSION:
        raise LockedEvaluationError("locked prediction seal schema mismatch")
    authorization = validate_authorization_id(expected_authorization_id)
    parent = validate_registered_parent_prefix(expected_parent_prefix)
    if expected_retry_kind == "none":
        attempt_execution_id = (
            "primary-prefix-binding"
            if expected_execution_id is None
            else _require_string(
                expected_execution_id, "expected prediction execution_id"
            )
        )
    else:
        attempt_execution_id = _require_string(
            expected_execution_id, "expected prediction retry execution_id"
        )
    attempt_prefixes = evaluation_attempt_prefixes(
        parent,
        authorization,
        "P",
        expected_retry_kind,
        attempt_execution_id,
    )
    if (
        record["authorization_id"] != authorization
        or record["registered_parent_prefix"] != parent
        or record["prediction_prefix"]
        != attempt_prefixes["predictions"]
    ):
        raise LockedEvaluationError("locked prediction authorization binding mismatch")
    fixed = {
        "parser_implementation_commit": FROZEN_PARSER_IMPLEMENTATION_COMMIT,
        "parser_source_sha256": FROZEN_PARSER_SOURCE_SHA256,
        "parser_version": FROZEN_PARSER_VERSION,
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": FROZEN_PROTOCOL_BUNDLE_SHA256,
        "acceptance_gates_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
    }
    if any(
        not exact_json_equal(record[field], value)
        for field, value in fixed.items()
    ):
        raise LockedEvaluationError("locked prediction frozen binding mismatch")
    if any(
        record[field] is not False
        for field in (
            "labels_accessed",
            "target_model_loaded",
            "target_model_downloaded",
            "target_model_inference",
            "gpu_used",
        )
    ):
        raise LockedEvaluationError("prediction seal violates label/model/GPU boundary")
    _require_commit(record["implementation_commit"], "seal implementation commit")
    _require_image_digest(record["image_digest"], "seal image digest")
    _require_sha256(record["config_sha256"], "seal config SHA-256")
    for field in (
        "runtime_config_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "locked_manifest_sha256",
        "input_receipt_sha256",
        "locked_input_reservation_sha256",
        "locked_input_private_nonce_sha256",
        "source_manifest_sha256",
        "case_universe_sha256",
    ):
        _require_sha256(record[field], f"seal {field}")
    if (
        record["runtime_config_sha256"] != record["config_sha256"]
        or record["source_manifest_sha256"]
        != record["locked_input_manifest_sha256"]
    ):
        raise LockedEvaluationError("locked prediction provenance aliases mismatch")
    byte_bindings = {
        "prediction_request_manifest_sha256": request_manifest_bytes,
        "parser_v2_predictions_sha256": predictions_bytes,
        "legacy_predictions_sha256": legacy_predictions_bytes,
    }
    for field, data in byte_bindings.items():
        if _require_sha256(record[field], field) != sha256_bytes(data):
            raise LockedEvaluationError(f"prediction seal {field} mismatch")
    request_manifest = parse_json_strict(
        request_manifest_bytes, "prediction request manifest"
    )
    validate_prediction_request_manifest(
        request_manifest,
        expected_authorization_id=authorization,
        expected_parent_prefix=parent,
        expected_retry_kind=expected_retry_kind,
        expected_execution_id=expected_execution_id,
    )
    request_bindings = (
        "authorization_id",
        "registered_parent_prefix",
        "prediction_prefix",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "runtime_config_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "locked_manifest_sha256",
        "input_receipt_sha256",
        "parser_source_sha256",
        "parser_version",
        "protocol_commit",
        "protocol_bundle_sha256",
        "acceptance_gates_sha256",
        "locked_input_reservation_blob",
        "locked_input_reservation_sha256",
        "locked_input_private_nonce_sha256",
        "locked_input_reservation_etag",
        "locked_input_blob",
        "locked_input_sha256",
        "locked_input_etag",
        "locked_input_manifest_blob",
        "locked_input_manifest_sha256",
        "source_manifest_sha256",
        "locked_input_manifest_etag",
        "visibility_blob",
        "visibility_sha256",
        "visibility_etag",
        "ordered_case_ids",
        "case_universe_sha256",
    )
    if (
        any(
            not exact_json_equal(request_manifest.get(field), record[field])
            for field in request_bindings
        )
        or request_manifest.get("labels_accessed") is not False
    ):
        raise LockedEvaluationError(
            "prediction request manifest differs from its seal"
        )
    expected_visibility_blob = (
        f"{attempt_prefixes['visibility']}/stage_p_visibility.json"
    )
    _require_sha256(record["visibility_sha256"], "Stage-P visibility SHA-256")
    _require_string(record["visibility_etag"], "Stage-P visibility ETag")
    if record["visibility_blob"] != expected_visibility_blob:
        raise LockedEvaluationError("Stage-P visibility binding mismatch")
    predictions = parse_jsonl_strict(
        predictions_bytes, "parser_v2_locked_predictions.jsonl"
    )
    legacy = parse_jsonl_strict(
        legacy_predictions_bytes, "legacy_locked_predictions.jsonl"
    )
    ids = [_require_case_id(item) for item in record["ordered_case_ids"]]
    if (
        ids != [item.get("case_id") for item in predictions]
        or ids != [item.get("case_id") for item in legacy]
        or ids != sorted(set(ids))
        or _require_int(record["row_count"], "seal row_count") != len(ids)
        or record["case_universe_sha256"] != case_universe_sha256(ids)
    ):
        raise LockedEvaluationError("prediction seal membership mismatch")
    frozen = record["frozen_v2_seal"]
    _require_exact_fields(
        frozen,
        {
            "schema_version",
            "implementation_commit",
            "parser_version",
            "locked_inputs_sha256",
            "predictions_sha256",
            "row_count",
            "ordered_case_ids",
            "sealed_utc",
        },
        "frozen v2 seal",
    )
    if (
        frozen["schema_version"] != FROZEN_PREDICTION_SEAL_SCHEMA_VERSION
        or frozen["implementation_commit"] != record["implementation_commit"]
        or frozen["parser_version"] != FROZEN_PARSER_VERSION
        or frozen["predictions_sha256"] != sha256_bytes(predictions_bytes)
        or _require_int(frozen["row_count"], "frozen seal row_count")
        != len(ids)
        or not exact_json_equal(frozen["ordered_case_ids"], ids)
        or frozen["locked_inputs_sha256"] != record["locked_input_sha256"]
    ):
        raise LockedEvaluationError("nested frozen v2 seal mismatch")
    _require_utc(record["sealed_utc"], "prediction seal sealed_utc")
    _require_utc(frozen["sealed_utc"], "frozen v2 seal sealed_utc")
    assert_label_blind_payload(record)
    return {
        "ordered_case_ids": ids,
        "implementation_commit": record["implementation_commit"],
        "image_digest": record["image_digest"],
        "config_sha256": record["config_sha256"],
        "authorization_lock_sha256": record["authorization_lock_sha256"],
        "authorization_manifest_sha256": record[
            "authorization_manifest_sha256"
        ],
        "implementation_manifest_sha256": record[
            "implementation_manifest_sha256"
        ],
        "locked_manifest_sha256": record["locked_manifest_sha256"],
        "input_receipt_sha256": record["input_receipt_sha256"],
        "locked_input_sha256": record["locked_input_sha256"],
        "locked_input_reservation_sha256": record[
            "locked_input_reservation_sha256"
        ],
        "locked_input_private_nonce_sha256": record[
            "locked_input_private_nonce_sha256"
        ],
        "locked_input_manifest_sha256": record[
            "locked_input_manifest_sha256"
        ],
        "case_universe_sha256": record["case_universe_sha256"],
        "visibility_sha256": record["visibility_sha256"],
    }


def _fraction_parts(value: Fraction | None) -> dict[str, Any]:
    if value is None:
        return {"numerator": None, "denominator": None, "rational": None}
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "rational": (
            str(value.numerator)
            if value.denominator == 1
            else f"{value.numerator}/{value.denominator}"
        ),
    }


def metric_record(
    numerator: int | None,
    denominator: int | None,
    *,
    comparison: str | None = None,
    threshold: Fraction | None = None,
    count_limit: int | None = None,
    mandatory: bool = False,
    reason: str | None = None,
) -> dict[str, Any]:
    if type(mandatory) is not bool:
        raise LockedEvaluationError("metric mandatory control must be a boolean")
    if numerator is not None and type(numerator) is not int:
        raise LockedEvaluationError("metric numerator must be an integer or null")
    if denominator is not None and (
        type(denominator) is not int or denominator < 0
    ):
        raise LockedEvaluationError("metric denominator must be nonnegative or null")
    if count_limit is not None and type(count_limit) is not int:
        raise LockedEvaluationError("metric count limit must be an integer or null")
    rate = (
        None
        if numerator is None or denominator in {None, 0}
        else Fraction(numerator, denominator)
    )
    threshold_record = None
    if comparison is not None:
        if comparison not in {">=", "<="} or threshold is None:
            raise LockedEvaluationError("gated metric threshold is incomplete")
        threshold_record = {
            "comparison": comparison,
            **_fraction_parts(threshold),
            "count_limit": count_limit,
        }
    if denominator == 0 or numerator is None or denominator is None:
        status = "NA_INVALID" if mandatory else "NA"
        passed: bool | None = None
        effective_reason = reason or "zero_or_missing_denominator"
    elif comparison is None:
        status = "REPORT_ONLY"
        passed = None
        effective_reason = reason or "not_a_hard_gate"
    else:
        rate_pass = rate >= threshold if comparison == ">=" else rate <= threshold
        count_pass = True
        if count_limit is not None:
            count_pass = (
                numerator >= count_limit
                if comparison == ">="
                else numerator <= count_limit
            )
        passed = bool(rate_pass and count_pass)
        status = "PASS" if passed else "FAIL"
        effective_reason = reason
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": _fraction_parts(rate),
        "threshold": threshold_record,
        "passed": passed,
        "status": status,
        "reason": effective_reason,
    }


def _count_metric(value: int, total: int) -> dict[str, Any]:
    return metric_record(value, total)


def _classification_metrics(
    confusion_counts: Mapping[str, Mapping[str, int]],
    label: str,
    total: int,
) -> tuple[dict[str, Any], dict[str, Fraction | None]]:
    tp = confusion_counts[label][label]
    fp = sum(
        confusion_counts[actual][label]
        for actual in TYPED_DECISION_CLASSES
        if actual != label
    )
    fn = sum(
        confusion_counts[label][predicted]
        for predicted in TYPED_DECISION_CLASSES
        if predicted != label
    )
    tn = total - tp - fp - fn
    values = {
        "precision": None if tp + fp == 0 else Fraction(tp, tp + fp),
        "recall": None if tp + fn == 0 else Fraction(tp, tp + fn),
        "specificity": None if tn + fp == 0 else Fraction(tn, tn + fp),
        "f1": None if 2 * tp + fp + fn == 0 else Fraction(2 * tp, 2 * tp + fp + fn),
    }
    report = {
        "tp": _count_metric(tp, total),
        "fp": _count_metric(fp, total),
        "fn": _count_metric(fn, total),
        "tn": _count_metric(tn, total),
        "precision": metric_record(tp, tp + fp),
        "recall": metric_record(tp, tp + fn),
        "specificity": metric_record(tn, tn + fp),
        "f1": metric_record(2 * tp, 2 * tp + fp + fn),
    }
    return report, values


def _span_identity(span: Mapping[str, Any]) -> tuple[int, int, str]:
    return (span["start"], span["end"], span["text"])


def _selected_span(result: Mapping[str, Any]) -> Mapping[str, Any] | None:
    selected = [
        item
        for item in result["evidence_spans"]
        if item["disposition"] == "selected"
    ]
    if len(selected) > 1:
        raise LockedEvaluationError("parser result has multiple selected spans")
    return selected[0] if selected else None


def validate_final_label(
    record: Mapping[str, Any], gates: Mapping[str, Any], *, name: str
) -> dict[str, Any]:
    try:
        checked = _load_frozen_validation().validate_final_label(record, name=name)
    except Exception:
        raise LockedEvaluationError("final label schema/invariants are invalid") from None
    dataset = gates["dataset_contract"]
    if (
        tuple(dataset["strata"]) != tuple(_load_frozen_validation().STRATA)
        or tuple(dataset["critical_strata"])
        != tuple(_load_frozen_validation().CRITICAL_STRATA)
        or gates["absolute_gates"]["last_number_trap"]["stratum"] != "S06"
    ):
        raise LockedEvaluationError("gate JSON diverges from frozen label semantics")
    extraction = checked["extraction"]
    return {
        "case_id": checked["case_id"],
        "stratum": checked["stratum"],
        "output_text": checked["output_text"],
        "extraction": extraction,
        "reference": checked["registered_reference_answer"],
        "expected_correctness": checked["expected_correctness"],
        "acceptable_spans": checked["acceptable_selected_spans"],
        "distractor": checked["last_number_distractor_span"],
    }


def _labels_index(
    labels: Sequence[Mapping[str, Any]], gates: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    dataset = gates["dataset_contract"]
    total = dataset["total_cases"]
    if len(labels) != total:
        raise LockedEvaluationError("locked labels do not contain total_cases")
    result: dict[str, dict[str, Any]] = {}
    ordered: list[str] = []
    strata = Counter()
    support = Counter()
    for index, label in enumerate(labels):
        checked = validate_final_label(label, gates, name=f"locked labels[{index}]")
        case_id = checked["case_id"]
        if case_id in result:
            raise LockedEvaluationError("locked labels repeat a case ID")
        result[case_id] = {"raw": label, **checked}
        ordered.append(case_id)
        strata[checked["stratum"]] += 1
        support[typed_decision_class(derive_typed_decision(label, expected=True))] += 1
    if ordered != sorted(result):
        raise LockedEvaluationError("locked labels are not in canonical order")
    if strata != Counter(
        {
            stratum: dataset["cases_per_stratum"]
            for stratum in dataset["strata"]
        }
    ):
        raise LockedEvaluationError("locked labels violate stratum quotas")
    if not exact_json_equal(
        dict(support), dict(dataset["typed_decision_support"])
    ):
        raise LockedEvaluationError("locked labels violate typed-decision support")
    try:
        _load_frozen_validation()._validate_locked_label_support(labels)
    except Exception:
        raise LockedEvaluationError(
            "locked labels violate frozen cross-record support invariants"
        ) from None
    return result


def _reconstruct_locked_input(label: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": LOCKED_INPUT_SCHEMA_VERSION,
        "case_id": label["case_id"],
        "source_kind": SOURCE_KIND,
        "output_text": label["output_text"],
        "parse_type": "numeric",
    }


def _prediction_indexes(
    predictions: Sequence[Mapping[str, Any]],
    legacy_predictions: Sequence[Mapping[str, Any]],
    labels: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if len(predictions) != len(labels) or len(legacy_predictions) != len(labels):
        raise LockedEvaluationError("prediction membership is incomplete")
    parser_index: dict[str, Mapping[str, Any]] = {}
    legacy_index: dict[str, Mapping[str, Any]] = {}
    prediction_ids: list[str] = []
    legacy_ids: list[str] = []
    for prediction in predictions:
        case_id = _require_case_id(prediction.get("case_id"))
        if case_id not in labels or case_id in parser_index:
            raise LockedEvaluationError("v2 prediction case ID is unknown or duplicate")
        locked = _reconstruct_locked_input(labels[case_id]["raw"])
        validate_prediction_envelope(prediction, locked)
        parser_index[case_id] = prediction["parser_result"]
        prediction_ids.append(case_id)
    for legacy in legacy_predictions:
        case_id = _require_case_id(legacy.get("case_id"))
        if case_id not in labels or case_id in legacy_index:
            raise LockedEvaluationError("legacy prediction case ID is unknown or duplicate")
        locked = _reconstruct_locked_input(labels[case_id]["raw"])
        validate_legacy_prediction(legacy, locked)
        legacy_index[case_id] = legacy
        legacy_ids.append(case_id)
    expected_ids = sorted(labels)
    if not exact_json_equal(
        prediction_ids, expected_ids
    ) or not exact_json_equal(legacy_ids, expected_ids):
        raise LockedEvaluationError("prediction IDs are not exact and ordered")
    return parser_index, legacy_index


def _minimum_gate(
    numerator: int,
    denominator: int,
    gate: Mapping[str, Any],
    *,
    name: str,
) -> dict[str, Any]:
    threshold = _require_gate_fraction(
        gate, "threshold_numerator", "threshold_denominator", name
    )
    minimum = _require_int(gate["minimum_correct"], f"{name}.minimum_correct")
    registered_denominator = _require_int(
        gate["denominator"], f"{name}.denominator", minimum=1
    )
    if denominator != registered_denominator:
        raise LockedEvaluationError(f"{name} denominator differs from gate JSON")
    return metric_record(
        numerator,
        denominator,
        comparison=">=",
        threshold=threshold,
        count_limit=minimum,
        mandatory=True,
    )


def _maximum_gate(
    numerator: int,
    denominator: int,
    gate: Mapping[str, Any],
    *,
    name: str,
) -> dict[str, Any]:
    registered_denominator = _require_int(
        gate["denominator"], f"{name}.denominator", minimum=1
    )
    if denominator != registered_denominator:
        raise LockedEvaluationError(f"{name} denominator differs from gate JSON")
    maximum = _require_int(gate["maximum_errors"], f"{name}.maximum_errors")
    if "maximum_rate_numerator" in gate:
        threshold = _require_gate_fraction(
            gate, "maximum_rate_numerator", "maximum_rate_denominator", name
        )
    else:
        threshold = Fraction(maximum, registered_denominator)
    return metric_record(
        numerator,
        denominator,
        comparison="<=",
        threshold=threshold,
        count_limit=maximum,
        mandatory=True,
    )


def mandatory_gate_specs(
    gates: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    dataset = gates["dataset_contract"]
    absolute = gates["absolute_gates"]
    legacy = gates["legacy_comparison_gates"]
    cases_per_stratum = dataset["cases_per_stratum"]
    specs: dict[str, dict[str, Any]] = {}

    def add(
        name: str,
        comparison: str,
        threshold: Fraction,
        count_limit: int | None,
        denominator: int | None,
    ) -> None:
        specs[name] = {
            "comparison": comparison,
            "threshold": threshold,
            "count_limit": count_limit,
            "denominator": denominator,
        }

    overall = absolute["overall_exact_typed_decision"]
    add(
        "overall_exact_typed_decision",
        ">=",
        _require_gate_fraction(
            overall,
            "threshold_numerator",
            "threshold_denominator",
            "overall_exact_typed_decision",
        ),
        overall["minimum_correct"],
        overall["denominator"],
    )
    macro = absolute["answer_presence_macro_f1"]
    add(
        "answer_presence_macro_f1",
        ">=",
        _require_gate_fraction(
            macro,
            "minimum_numerator",
            "minimum_denominator",
            "answer_presence_macro_f1",
        ),
        None,
        None,
    )
    for gate_name in ("ambiguity", "no_answer"):
        gate = absolute[gate_name]
        for metric_name in ("precision", "recall"):
            add(
                f"{gate_name}_{metric_name}",
                ">=",
                _require_gate_fraction(
                    gate,
                    f"minimum_{metric_name}_numerator",
                    f"minimum_{metric_name}_denominator",
                    f"{gate_name}.{metric_name}",
                ),
                None,
                None,
            )
    for name in ("boxed_final_miss", "last_number_trap", "wrong_span"):
        gate = absolute[name]
        add(
            name,
            "<=",
            _require_gate_fraction(
                gate,
                "maximum_rate_numerator",
                "maximum_rate_denominator",
                name,
            ),
            gate["maximum_errors"],
            gate["denominator"],
        )
    material = absolute["material_correctness"]
    add(
        "material_correctness",
        "<=",
        Fraction(material["maximum_errors"], material["denominator"]),
        material["maximum_errors"],
        material["denominator"],
    )
    for key, maximum in material.items():
        if re.fullmatch(r"S[0-9]{2}_maximum_errors", key):
            stratum = key.removesuffix("_maximum_errors")
            add(
                f"material_correctness_{stratum}",
                "<=",
                Fraction(maximum, cases_per_stratum),
                maximum,
                cases_per_stratum,
            )
    floor = absolute["every_stratum_floor"]
    answer_bearing = absolute["answer_bearing_per_stratum"]
    for stratum in dataset["strata"]:
        add(
            f"stratum_floor_{stratum}",
            ">=",
            _require_gate_fraction(
                floor,
                "threshold_numerator",
                "threshold_denominator",
                f"every_stratum_floor.{stratum}",
            ),
            floor["minimum_correct"],
            floor["denominator"],
        )
        if stratum in dataset["answer_bearing_strata"]:
            add(
                f"answer_bearing_{stratum}",
                ">=",
                _require_gate_fraction(
                    answer_bearing,
                    "threshold_numerator",
                    "threshold_denominator",
                    f"answer_bearing_per_stratum.{stratum}",
                ),
                answer_bearing["minimum_correct"],
                answer_bearing["denominator"],
            )
    clean = legacy["clean_pooled_non_regression"]
    add(
        "clean_pooled_non_regression",
        ">=",
        Fraction(0),
        0,
        clean["denominator"],
    )
    critical = legacy["critical_strict_improvement"]
    minimum_gain = critical["minimum_net_gain_in_at_least_one_stratum"]
    add(
        "critical_strict_improvement",
        ">=",
        Fraction(minimum_gain, cases_per_stratum),
        minimum_gain,
        cases_per_stratum,
    )
    return dict(sorted(specs.items()))


def _metrics_dataset_summary(gates: Mapping[str, Any]) -> dict[str, Any]:
    dataset = gates["dataset_contract"]
    return {
        "total_cases": dataset["total_cases"],
        "cases_per_stratum": dataset["cases_per_stratum"],
        "strata": list(dataset["strata"]),
        "typed_decision_support": dict(dataset["typed_decision_support"]),
        "answer_bearing_strata": list(dataset["answer_bearing_strata"]),
        "clean_strata": list(dataset["clean_strata"]),
        "critical_strata": list(dataset["critical_strata"]),
    }


def _metrics_topology_summary(gates: Mapping[str, Any]) -> dict[str, Any]:
    dataset = gates["dataset_contract"]
    gate_names = list(mandatory_gate_specs(gates))
    return {
        "registered_case_count": dataset["total_cases"],
        "registered_stratum_count": len(dataset["strata"]),
        "registered_support_count": sum(
            dataset["typed_decision_support"].values()
        ),
        "registered_present_count": dataset["typed_decision_support"]["present"],
        "registered_mandatory_gate_count": len(gate_names),
        "registered_mandatory_gate_names": gate_names,
        "per_stratum_denominators": {
            stratum: dataset["cases_per_stratum"]
            for stratum in dataset["strata"]
        },
    }


def _score_locked_evaluation(
    labels: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    legacy_predictions: Sequence[Mapping[str, Any]],
    gates: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    label_index = _labels_index(labels, gates)
    parser_index, legacy_index = _prediction_indexes(
        predictions, legacy_predictions, label_index
    )
    dataset = gates["dataset_contract"]
    absolute = gates["absolute_gates"]
    legacy_gates = gates["legacy_comparison_gates"]
    total = dataset["total_cases"]
    strata = dataset["strata"]
    confusion_counts = {
        actual: {predicted: 0 for predicted in TYPED_DECISION_CLASSES}
        for actual in TYPED_DECISION_CLASSES
    }
    stratum_counts = {
        stratum: {
            "denominator": 0,
            "v2_correct": 0,
            "legacy_correct": 0,
            "material_errors": 0,
            "wrong_span_errors": 0,
        }
        for stratum in strata
    }
    typed_correct = 0
    parsed_answer_correct = 0
    legacy_correct = 0
    boxed_final_misses = 0
    last_number_errors = 0
    wrong_span_errors = 0
    material_errors = 0
    material_by_stratum = Counter()
    expected_decisions: dict[str, str] = {}
    v2_decisions: dict[str, str] = {}
    legacy_decisions: dict[str, str] = {}
    adapter_failure_ids: list[str] = []
    failures: list[dict[str, Any]] = []

    boxed_strata = set(absolute["boxed_final_miss"]["strata"])
    trap_stratum = absolute["last_number_trap"]["stratum"]
    for case_id in sorted(label_index):
        label = label_index[case_id]
        raw_label = label["raw"]
        parser_result = parser_index[case_id]
        legacy_row = legacy_index[case_id]
        expected_decision = derive_typed_decision(raw_label, expected=True)
        v2_decision = derive_typed_decision(parser_result)
        legacy_decision = legacy_row["adapter"]["typed_decision"]
        expected_decisions[case_id] = expected_decision
        v2_decisions[case_id] = v2_decision
        legacy_decisions[case_id] = legacy_decision
        if legacy_row["adapter"]["adapter_failure"] is not None:
            adapter_failure_ids.append(case_id)
        actual_class = typed_decision_class(expected_decision)
        predicted_class = typed_decision_class(v2_decision)
        confusion_counts[actual_class][predicted_class] += 1
        stratum = label["stratum"]
        values = stratum_counts[stratum]
        values["denominator"] += 1
        v2_exact = v2_decision == expected_decision
        legacy_exact = legacy_decision == expected_decision
        typed_correct += int(v2_exact)
        legacy_correct += int(legacy_exact)
        values["v2_correct"] += int(v2_exact)
        values["legacy_correct"] += int(legacy_exact)
        parsed_exact = (
            parser_result["parsed_answer"] == raw_label["expected_parsed_answer"]
        )
        parsed_answer_correct += int(parsed_exact)
        selected = _selected_span(parser_result)
        acceptable = {_span_identity(item) for item in label["acceptable_spans"]}
        wrong_span = False
        if raw_label["expected_answer_presence"] == "present":
            wrong_span = selected is None or _span_identity(selected) not in acceptable
            wrong_span_errors += int(wrong_span)
            values["wrong_span_errors"] += int(wrong_span)
            if stratum in boxed_strata and (not v2_exact or wrong_span):
                boxed_final_misses += 1
        last_number = bool(
            stratum == trap_stratum
            and selected is not None
            and label["distractor"] is not None
            and _span_identity(selected) == _span_identity(label["distractor"])
        )
        last_number_errors += int(last_number)
        parser_correctness = (
            v2_decision.startswith("present:")
            and v2_decision.removeprefix("present:") == label["reference"]
        )
        material = bool(parser_correctness) ^ label["expected_correctness"]
        material_errors += int(material)
        material_by_stratum[stratum] += int(material)
        values["material_errors"] += int(material)
        if (
            not v2_exact
            or not parsed_exact
            or wrong_span
            or last_number
            or material
        ):
            affected: list[str] = []
            if not v2_exact:
                affected.extend(
                    [
                        "overall_exact_typed_decision",
                        f"stratum_floor_{stratum}",
                    ]
                )
                if stratum in dataset["answer_bearing_strata"]:
                    affected.append(f"answer_bearing_{stratum}")
            if wrong_span:
                affected.append("wrong_span")
            if stratum in boxed_strata and (not v2_exact or wrong_span):
                affected.append("boxed_final_miss")
            if last_number:
                affected.append("last_number_trap")
            if material:
                affected.append("material_correctness")
            failures.append(
                {
                    "case_id": case_id,
                    "stratum": stratum,
                    "output_text": label["output_text"],
                    "expected_typed_decision": expected_decision,
                    "predicted_typed_decision": v2_decision,
                    "legacy_typed_decision": legacy_decision,
                    "expected_parsed_answer": raw_label["expected_parsed_answer"],
                    "predicted_parsed_answer": parser_result["parsed_answer"],
                    "expected_acceptable_spans": raw_label[
                        "acceptable_selected_spans"
                    ],
                    "predicted_evidence_spans": parser_result["evidence_spans"],
                    "expected_extraction_strategy": raw_label[
                        "expected_extraction_strategy"
                    ],
                    "predicted_extraction_strategy": parser_result[
                        "extraction_strategy"
                    ],
                    "wrong_span": wrong_span,
                    "last_number_error": last_number,
                    "material_error": material,
                    "gates_affected": sorted(set(affected)),
                }
            )

    confusion = {
        actual: {
            predicted: _count_metric(confusion_counts[actual][predicted], total)
            for predicted in TYPED_DECISION_CLASSES
        }
        for actual in TYPED_DECISION_CLASSES
    }
    class_reports: dict[str, Any] = {}
    class_values: dict[str, dict[str, Fraction | None]] = {}
    for label in TYPED_DECISION_CLASSES:
        class_reports[label], class_values[label] = _classification_metrics(
            confusion_counts, label, total
        )
    f1_values = [class_values[label]["f1"] for label in TYPED_DECISION_CLASSES]
    macro_f1 = (
        sum((value for value in f1_values if value is not None), Fraction())
        / len(f1_values)
        if all(value is not None for value in f1_values)
        else None
    )

    gates_report: dict[str, dict[str, Any]] = {}
    gates_report["overall_exact_typed_decision"] = _minimum_gate(
        typed_correct,
        total,
        absolute["overall_exact_typed_decision"],
        name="overall_exact_typed_decision",
    )
    macro_gate = absolute["answer_presence_macro_f1"]
    macro_threshold = _require_gate_fraction(
        macro_gate,
        "minimum_numerator",
        "minimum_denominator",
        "answer_presence_macro_f1",
    )
    macro_denominator = (
        None
        if macro_f1 is None
        else macro_f1.denominator
    )
    gates_report["answer_presence_macro_f1"] = metric_record(
        None if macro_f1 is None else macro_f1.numerator,
        macro_denominator,
        comparison=">=",
        threshold=macro_threshold,
        mandatory=True,
    )
    for class_name, gate_name in (
        ("ambiguous", "ambiguity"),
        ("no_answer", "no_answer"),
    ):
        gate = absolute[gate_name]
        for metric_name in ("precision", "recall"):
            value = class_values[class_name][metric_name]
            threshold = _require_gate_fraction(
                gate,
                f"minimum_{metric_name}_numerator",
                f"minimum_{metric_name}_denominator",
                f"{gate_name}.{metric_name}",
            )
            key = (
                "ambiguity_" + metric_name
                if class_name == "ambiguous"
                else "no_answer_" + metric_name
            )
            source_record = class_reports[class_name][metric_name]
            gates_report[key] = metric_record(
                source_record["numerator"],
                source_record["denominator"],
                comparison=">=",
                threshold=threshold,
                mandatory=True,
            )
    gates_report["boxed_final_miss"] = _maximum_gate(
        boxed_final_misses,
        len(boxed_strata) * dataset["cases_per_stratum"],
        absolute["boxed_final_miss"],
        name="boxed_final_miss",
    )
    gates_report["last_number_trap"] = _maximum_gate(
        last_number_errors,
        dataset["cases_per_stratum"],
        absolute["last_number_trap"],
        name="last_number_trap",
    )
    wrong_span_population = _require_string(
        absolute["wrong_span"]["population"], "wrong_span.population"
    ).removeprefix("expected_")
    if wrong_span_population not in dataset["typed_decision_support"]:
        raise LockedEvaluationError("wrong-span population is not registered")
    expected_present = dataset["typed_decision_support"][wrong_span_population]
    gates_report["wrong_span"] = _maximum_gate(
        wrong_span_errors,
        expected_present,
        absolute["wrong_span"],
        name="wrong_span",
    )
    gates_report["material_correctness"] = _maximum_gate(
        material_errors,
        total,
        absolute["material_correctness"],
        name="material_correctness",
    )
    material_gate = absolute["material_correctness"]
    special_material_strata = sorted(
        key.removesuffix("_maximum_errors")
        for key in material_gate
        if re.fullmatch(r"S[0-9]{2}_maximum_errors", key)
    )
    for stratum in special_material_strata:
        maximum = _require_int(
            material_gate[f"{stratum}_maximum_errors"],
            f"material_correctness.{stratum}_maximum_errors",
        )
        denominator = stratum_counts[stratum]["denominator"]
        gates_report[f"material_correctness_{stratum}"] = metric_record(
            material_by_stratum[stratum],
            denominator,
            comparison="<=",
            threshold=Fraction(maximum, denominator),
            count_limit=maximum,
            mandatory=True,
        )

    per_stratum: dict[str, Any] = {}
    for stratum in strata:
        values = stratum_counts[stratum]
        denominator = values["denominator"]
        floor_gate = _minimum_gate(
            values["v2_correct"],
            denominator,
            absolute["every_stratum_floor"],
            name=f"every_stratum_floor.{stratum}",
        )
        gates_report[f"stratum_floor_{stratum}"] = floor_gate
        answer_bearing_gate = None
        if stratum in dataset["answer_bearing_strata"]:
            answer_bearing_gate = _minimum_gate(
                values["v2_correct"],
                denominator,
                absolute["answer_bearing_per_stratum"],
                name=f"answer_bearing_per_stratum.{stratum}",
            )
            gates_report[f"answer_bearing_{stratum}"] = answer_bearing_gate
        per_stratum[stratum] = {
            "typed_agreement": metric_record(
                values["v2_correct"], denominator
            ),
            "legacy_typed_agreement": metric_record(
                values["legacy_correct"], denominator
            ),
            "legacy_v2_delta": metric_record(
                values["v2_correct"] - values["legacy_correct"], denominator
            ),
            "wrong_span_errors": metric_record(
                values["wrong_span_errors"], denominator
            ),
            "material_errors": metric_record(
                values["material_errors"], denominator
            ),
            "floor_gate": floor_gate,
            "answer_bearing_gate": answer_bearing_gate,
            "critical": stratum in dataset["critical_strata"],
        }

    clean_strata = legacy_gates["clean_pooled_non_regression"]["strata"]
    clean_v2 = sum(stratum_counts[item]["v2_correct"] for item in clean_strata)
    clean_legacy = sum(
        stratum_counts[item]["legacy_correct"] for item in clean_strata
    )
    clean_denominator = _require_int(
        legacy_gates["clean_pooled_non_regression"]["denominator"],
        "clean pooled denominator",
        minimum=1,
    )
    actual_clean_denominator = sum(
        stratum_counts[item]["denominator"] for item in clean_strata
    )
    if clean_denominator != actual_clean_denominator:
        raise LockedEvaluationError("clean denominator differs from gate JSON")
    clean_gate = metric_record(
        clean_v2 - clean_legacy,
        clean_denominator,
        comparison=">=",
        threshold=Fraction(0),
        count_limit=0,
        mandatory=True,
    )
    gates_report["clean_pooled_non_regression"] = clean_gate

    critical_gate = legacy_gates["critical_strict_improvement"]
    critical_strata = critical_gate["strata"]
    minimum_gain = _require_int(
        critical_gate["minimum_net_gain_in_at_least_one_stratum"],
        "critical strict improvement minimum gain",
        minimum=1,
    )
    critical_gains = {
        stratum: (
            stratum_counts[stratum]["v2_correct"]
            - stratum_counts[stratum]["legacy_correct"]
        )
        for stratum in critical_strata
    }
    maximum_gain = max(critical_gains.values())
    critical_improvement_gate = metric_record(
        maximum_gain,
        dataset["cases_per_stratum"],
        comparison=">=",
        threshold=Fraction(minimum_gain, dataset["cases_per_stratum"]),
        count_limit=minimum_gain,
        mandatory=True,
    )
    gates_report["critical_strict_improvement"] = critical_improvement_gate

    invalid = any(item["status"] == "NA_INVALID" for item in gates_report.values())
    failed = any(item["status"] == "FAIL" for item in gates_report.values())
    status = "INVALID" if invalid else "FAIL" if failed else "PASS"
    status_logic = gates["status_logic"]
    if status == "PASS" and status_logic["PASS"] != (
        "all_absolute_and_legacy_comparison_gates_pass"
    ):
        raise LockedEvaluationError("PASS status logic is unrecognized")
    if status == "FAIL" and status_logic["FAIL"] != (
        "all_metrics_defined_and_any_hard_gate_fails"
    ):
        raise LockedEvaluationError("FAIL status logic is unrecognized")
    if status == "INVALID" and status_logic["INVALID"] != (
        "integrity_representation_schema_consensus_denominator_or_scorer_failure"
    ):
        raise LockedEvaluationError("INVALID status logic is unrecognized")

    failures.sort(key=lambda item: item["case_id"])
    metrics = {
        "schema_version": METRICS_SCHEMA_VERSION,
        "status": status,
        "gate_contract_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
        "dataset_summary": _metrics_dataset_summary(gates),
        "topology_summary": _metrics_topology_summary(gates),
        "overall_typed_agreement": metric_record(typed_correct, total),
        "overall_parsed_answer_agreement": metric_record(
            parsed_answer_correct, total
        ),
        "confusion_matrix": confusion,
        "class_metrics": class_reports,
        "answer_presence_macro_f1": metric_record(
            None if macro_f1 is None else macro_f1.numerator,
            None if macro_f1 is None else macro_f1.denominator,
        ),
        "per_stratum": per_stratum,
        "ambiguity": {
            "precision": gates_report["ambiguity_precision"],
            "recall": gates_report["ambiguity_recall"],
            "specificity": class_reports["ambiguous"]["specificity"],
            "f1": class_reports["ambiguous"]["f1"],
        },
        "no_answer": {
            "precision": gates_report["no_answer_precision"],
            "recall": gates_report["no_answer_recall"],
            "specificity": class_reports["no_answer"]["specificity"],
            "f1": class_reports["no_answer"]["f1"],
        },
        "span_errors": {
            "boxed_final_miss": gates_report["boxed_final_miss"],
            "last_number_trap": gates_report["last_number_trap"],
            "wrong_span": gates_report["wrong_span"],
        },
        "material_correctness": {
            "overall": gates_report["material_correctness"],
            "by_stratum": {
                stratum: metric_record(
                    material_by_stratum[stratum],
                    stratum_counts[stratum]["denominator"],
                )
                for stratum in strata
            },
            "special_strata_gates": {
                stratum: gates_report[f"material_correctness_{stratum}"]
                for stratum in special_material_strata
            },
        },
        "legacy_comparison": {
            "overall_legacy": metric_record(legacy_correct, total),
            "overall_v2": metric_record(typed_correct, total),
            "overall_delta": metric_record(
                typed_correct - legacy_correct, total
            ),
            "clean_v2": metric_record(clean_v2, clean_denominator),
            "clean_legacy": metric_record(clean_legacy, clean_denominator),
            "clean_delta": clean_gate,
            "critical_net_gain_by_stratum": {
                stratum: metric_record(
                    gain, stratum_counts[stratum]["denominator"]
                )
                for stratum, gain in critical_gains.items()
            },
            "critical_strict_improvement": critical_improvement_gate,
            "paired_clean_regressions": metric_record(
                sum(
                    legacy_decisions[case_id] == expected_decisions[case_id]
                    and v2_decisions[case_id] != expected_decisions[case_id]
                    for case_id, label in label_index.items()
                    if label["stratum"] in clean_strata
                ),
                clean_denominator,
            ),
            "adapter_failures": metric_record(len(adapter_failure_ids), total),
            "adapter_failure_case_ids": adapter_failure_ids,
        },
        "mismatch_case_ids": [item["case_id"] for item in failures],
        "material_error_case_ids": [
            item["case_id"] for item in failures if item["material_error"]
        ],
        "error_summary": {
            "mismatch_case_count": len(failures),
            "material_error_case_count": sum(
                item["material_error"] for item in failures
            ),
        },
        "gates": dict(sorted(gates_report.items())),
        "gate_summary": {
            "passed": sum(item["status"] == "PASS" for item in gates_report.values()),
            "failed": sum(item["status"] == "FAIL" for item in gates_report.values()),
            "na_invalid": sum(
                item["status"] == "NA_INVALID" for item in gates_report.values()
            ),
            "mandatory": len(gates_report),
        },
        "rounded_values_used_for_gates": False,
        "manual_override": False,
    }
    return metrics, failures


def _invalid_metrics(
    reason_code: str,
    detail: str = "redacted",
    *,
    gates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if gates is None:
        gate_records = {
            "integrity_and_scorer": metric_record(
                None,
                None,
                comparison=">=",
                threshold=Fraction(1),
                mandatory=True,
                reason=reason_code,
            )
        }
        dataset_summary = None
        topology_summary = None
    else:
        specs = mandatory_gate_specs(gates)
        gate_records = {
            name: metric_record(
                None,
                spec["denominator"],
                comparison=spec["comparison"],
                threshold=spec["threshold"],
                count_limit=spec["count_limit"],
                mandatory=True,
                reason=reason_code,
            )
            for name, spec in specs.items()
        }
        dataset_summary = _metrics_dataset_summary(gates)
        topology_summary = _metrics_topology_summary(gates)
    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        "status": "INVALID",
        "gate_contract_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
        "invalid_reason": reason_code,
        "invalid_detail": "redacted",
        "dataset_summary": dataset_summary,
        "topology_summary": topology_summary,
        "error_summary": {
            "mismatch_case_count": 0,
            "material_error_case_count": 0,
        },
        "mismatch_case_ids": [],
        "material_error_case_ids": [],
        "gates": gate_records,
        "gate_summary": {
            "passed": 0,
            "failed": 0,
            "na_invalid": len(gate_records),
            "mandatory": len(gate_records),
        },
        "rounded_values_used_for_gates": False,
        "manual_override": False,
    }


def score_locked_evaluation(
    labels: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    legacy_predictions: Sequence[Mapping[str, Any]],
    gate_bytes: bytes,
    *,
    raise_on_invalid: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    gates: Mapping[str, Any] | None = None
    try:
        gates = load_acceptance_gates(gate_bytes)
        return _score_locked_evaluation(
            labels, predictions, legacy_predictions, gates
        )
    except Exception as exc:
        if raise_on_invalid:
            raise
        return _invalid_metrics(type(exc).__name__, gates=gates), []


def score_locked_evaluation_bytes(
    labels_bytes: bytes,
    predictions_bytes: bytes,
    legacy_predictions_bytes: bytes,
    gate_bytes: bytes,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        labels = parse_jsonl_strict(labels_bytes, "locked_reference_labels.jsonl")
        predictions = parse_jsonl_strict(
            predictions_bytes, "parser_v2_locked_predictions.jsonl"
        )
        legacy = parse_jsonl_strict(
            legacy_predictions_bytes, "legacy_locked_predictions.jsonl"
        )
        return score_locked_evaluation(
            labels,
            predictions,
            legacy,
            gate_bytes,
            raise_on_invalid=True,
        )
    except Exception as exc:
        try:
            gates = load_acceptance_gates(gate_bytes)
        except Exception:
            gates = None
        return _invalid_metrics(type(exc).__name__, gates=gates), []


_SCORING_LEDGER_CONTEXT_FIELDS = frozenset(
    {
        "authorization_id",
        "registered_parent_prefix",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "prediction_manifest_sha256",
        "prediction_seal_sha256",
        "prediction_request_manifest_sha256",
        "locked_manifest_sha256",
        "input_manifest_sha256",
        "locked_input_sha256",
        "labels_manifest_sha256",
        "labels_manifest_etag",
        "labels_sha256",
        "labels_size",
        "labels_etag",
        "labels_open_transaction_sha256",
        "scores_prefix",
        "scoring_retry_kind",
        "stage_e_visibility_sha256",
        "retry_receipt_sha256",
        "case_universe_sha256",
        "row_count",
        "acceptance_gates_sha256",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "scoring_execution_id",
        "scoring_actor",
        "created_utc",
    }
)
_SCORING_LEDGER_ROW_FIELDS = frozenset(
    {
        "schema_version",
        "row_index",
        *_SCORING_LEDGER_CONTEXT_FIELDS,
        "case_id",
        "stratum",
        "label_record_base64",
        "label_record_size",
        "label_record_sha256",
        "parser_v2_prediction_row_size",
        "parser_v2_prediction_row_sha256",
        "legacy_prediction_row_size",
        "legacy_prediction_row_sha256",
        "expected_answer_presence",
        "expected_parsed_answer",
        "registered_reference_answer",
        "expected_typed_decision",
        "parser_v2_typed_decision",
        "legacy_typed_decision",
        "expected_typed_class",
        "parser_v2_typed_class",
        "legacy_typed_class",
        "expected_correctness",
        "parser_v2_correctness",
        "v2_typed_agreement",
        "legacy_typed_agreement",
        "parsed_answer_agreement",
        "agreement_category",
        "error_categories",
        "span_status",
        "wrong_span",
        "boxed_final_miss",
        "last_number_error",
        "material_error",
        "critical_case",
        "critical_stratum",
        "material_error_if_missed",
        "legacy_adapter_failure",
    }
)
_SCORING_LEDGER_AGREEMENT_CATEGORIES = (
    "both_correct",
    "v2_only_correct",
    "legacy_only_correct",
    "both_wrong_same",
    "both_wrong_different",
)
_SCORING_LEDGER_ERROR_CATEGORIES = (
    "v2_typed_mismatch",
    "legacy_typed_mismatch",
    "parsed_answer_mismatch",
    "wrong_span",
    "boxed_final_miss",
    "last_number_error",
    "material_error",
    "legacy_adapter_failure",
)


def validate_scoring_ledger_context(
    context: Mapping[str, Any],
) -> dict[str, Any]:
    _require_exact_fields(
        context, _SCORING_LEDGER_CONTEXT_FIELDS, "scoring ledger context"
    )
    attempt = validate_scoring_attempt_binding(
        parent_prefix=context["registered_parent_prefix"],
        authorization_id=context["authorization_id"],
        scores_prefix=context["scores_prefix"],
        scoring_retry_kind=context["scoring_retry_kind"],
        scoring_execution_id=context["scoring_execution_id"],
        retry_receipt_sha256=context["retry_receipt_sha256"],
    )
    checked = {
        "authorization_id": validate_authorization_id(context["authorization_id"]),
        "registered_parent_prefix": validate_registered_parent_prefix(
            context["registered_parent_prefix"]
        ),
        **attempt,
    }
    for field in (
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "prediction_manifest_sha256",
        "prediction_seal_sha256",
        "prediction_request_manifest_sha256",
        "locked_manifest_sha256",
        "input_manifest_sha256",
        "locked_input_sha256",
        "labels_manifest_sha256",
        "labels_sha256",
        "labels_open_transaction_sha256",
        "stage_e_visibility_sha256",
        "case_universe_sha256",
        "config_sha256",
    ):
        checked[field] = _require_sha256(
            context[field], f"scoring ledger {field}"
        )
    checked.update(
        {
            "labels_manifest_etag": _require_string(
                context["labels_manifest_etag"],
                "scoring ledger labels-manifest ETag",
            ),
            "labels_size": _require_int(
                context["labels_size"], "scoring ledger labels size", minimum=1
            ),
            "labels_etag": _require_string(
                context["labels_etag"], "scoring ledger labels ETag"
            ),
            "row_count": _require_int(
                context["row_count"], "scoring ledger row count", minimum=1
            ),
            "acceptance_gates_sha256": _require_sha256(
                context["acceptance_gates_sha256"],
                "scoring ledger acceptance-gates SHA-256",
            ),
            "implementation_commit": _require_commit(
                context["implementation_commit"],
                "scoring ledger implementation commit",
            ),
            "image_digest": _require_image_digest(
                context["image_digest"], "scoring ledger image digest"
            ),
            "scoring_actor": _require_string(
                context["scoring_actor"], "scoring ledger actor"
            ),
            "created_utc": _require_utc(
                context["created_utc"], "scoring ledger created_utc"
            ),
        }
    )
    if checked["acceptance_gates_sha256"] != FROZEN_ACCEPTANCE_GATE_SHA256:
        raise LockedEvaluationError(
            "scoring ledger acceptance-gates binding is not frozen"
        )
    return checked


def _scoring_ledger_row(
    label: Mapping[str, Any],
    prediction: Mapping[str, Any],
    legacy: Mapping[str, Any],
    *,
    label_row_bytes: bytes,
    prediction_row_bytes: bytes,
    legacy_row_bytes: bytes,
    row_index: int,
    context: Mapping[str, Any],
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    checked_label = validate_final_label(
        label, gates, name="scoring ledger label"
    )
    locked_input = _reconstruct_locked_input(label)
    validate_prediction_envelope(prediction, locked_input)
    validate_legacy_prediction(legacy, locked_input)
    if (
        prediction["case_id"] != checked_label["case_id"]
        or legacy["case_id"] != checked_label["case_id"]
    ):
        raise LockedEvaluationError(
            "scoring ledger prediction membership is not exact"
        )
    parser_result = prediction["parser_result"]
    expected_decision = derive_typed_decision(label, expected=True)
    parser_decision = derive_typed_decision(parser_result)
    legacy_decision = legacy["adapter"]["typed_decision"]
    v2_exact = parser_decision == expected_decision
    legacy_exact = legacy_decision == expected_decision
    parsed_exact = parser_result["parsed_answer"] == label[
        "expected_parsed_answer"
    ]
    selected = _selected_span(parser_result)
    acceptable = {
        _span_identity(item) for item in checked_label["acceptable_spans"]
    }
    expected_present = label["expected_answer_presence"] == "present"
    wrong_span = bool(
        expected_present
        and (selected is None or _span_identity(selected) not in acceptable)
    )
    span_status = (
        "not_applicable"
        if not expected_present
        else "wrong"
        if wrong_span
        else "acceptable"
    )
    boxed_final_miss = bool(
        checked_label["stratum"]
        in set(gates["absolute_gates"]["boxed_final_miss"]["strata"])
        and (not v2_exact or wrong_span)
    )
    last_number_error = bool(
        checked_label["stratum"]
        == gates["absolute_gates"]["last_number_trap"]["stratum"]
        and selected is not None
        and checked_label["distractor"] is not None
        and _span_identity(selected)
        == _span_identity(checked_label["distractor"])
    )
    parser_correctness = bool(
        parser_decision.startswith("present:")
        and parser_decision.removeprefix("present:")
        == checked_label["reference"]
    )
    material_error = bool(
        parser_correctness ^ checked_label["expected_correctness"]
    )
    legacy_adapter_failure = legacy["adapter"]["adapter_failure"] is not None
    if v2_exact and legacy_exact:
        agreement_category = "both_correct"
    elif v2_exact:
        agreement_category = "v2_only_correct"
    elif legacy_exact:
        agreement_category = "legacy_only_correct"
    elif parser_decision == legacy_decision:
        agreement_category = "both_wrong_same"
    else:
        agreement_category = "both_wrong_different"
    error_flags = {
        "v2_typed_mismatch": not v2_exact,
        "legacy_typed_mismatch": not legacy_exact,
        "parsed_answer_mismatch": not parsed_exact,
        "wrong_span": wrong_span,
        "boxed_final_miss": boxed_final_miss,
        "last_number_error": last_number_error,
        "material_error": material_error,
        "legacy_adapter_failure": legacy_adapter_failure,
    }
    return {
        "schema_version": SCORING_LEDGER_SCHEMA_VERSION,
        "row_index": row_index,
        **dict(context),
        "case_id": checked_label["case_id"],
        "stratum": checked_label["stratum"],
        "label_record_base64": base64.b64encode(label_row_bytes).decode(
            "ascii"
        ),
        "label_record_size": len(label_row_bytes),
        "label_record_sha256": sha256_bytes(label_row_bytes),
        "parser_v2_prediction_row_size": len(prediction_row_bytes),
        "parser_v2_prediction_row_sha256": sha256_bytes(
            prediction_row_bytes
        ),
        "legacy_prediction_row_size": len(legacy_row_bytes),
        "legacy_prediction_row_sha256": sha256_bytes(legacy_row_bytes),
        "expected_answer_presence": label["expected_answer_presence"],
        "expected_parsed_answer": label["expected_parsed_answer"],
        "registered_reference_answer": label["registered_reference_answer"],
        "expected_typed_decision": expected_decision,
        "parser_v2_typed_decision": parser_decision,
        "legacy_typed_decision": legacy_decision,
        "expected_typed_class": typed_decision_class(expected_decision),
        "parser_v2_typed_class": typed_decision_class(parser_decision),
        "legacy_typed_class": typed_decision_class(legacy_decision),
        "expected_correctness": checked_label["expected_correctness"],
        "parser_v2_correctness": parser_correctness,
        "v2_typed_agreement": v2_exact,
        "legacy_typed_agreement": legacy_exact,
        "parsed_answer_agreement": parsed_exact,
        "agreement_category": agreement_category,
        "error_categories": [
            name
            for name in _SCORING_LEDGER_ERROR_CATEGORIES
            if error_flags[name]
        ],
        "span_status": span_status,
        "wrong_span": wrong_span,
        "boxed_final_miss": boxed_final_miss,
        "last_number_error": last_number_error,
        "material_error": material_error,
        "critical_case": _require_bool(
            label["critical_case"], "scoring ledger critical_case"
        ),
        "critical_stratum": checked_label["stratum"]
        in gates["dataset_contract"]["critical_strata"],
        "material_error_if_missed": _require_bool(
            label["material_error_if_missed"],
            "scoring ledger material_error_if_missed",
        ),
        "legacy_adapter_failure": legacy_adapter_failure,
    }


def build_scoring_ledger_bytes(
    labels_bytes: bytes,
    predictions_bytes: bytes,
    legacy_predictions_bytes: bytes,
    gate_bytes: bytes,
    *,
    context: Mapping[str, Any],
    expected_ordered_case_ids: Sequence[str],
) -> tuple[bytes, dict[str, Any], list[dict[str, Any]]]:
    checked_context = validate_scoring_ledger_context(context)
    gates = load_acceptance_gates(gate_bytes)
    expected_ids = [
        _require_case_id(item, "scoring ledger expected case ID")
        for item in expected_ordered_case_ids
    ]
    if (
        expected_ids != sorted(set(expected_ids))
        or len(expected_ids) != gates["dataset_contract"]["total_cases"]
        or checked_context["row_count"] != len(expected_ids)
        or checked_context["case_universe_sha256"]
        != case_universe_sha256(expected_ids)
        or checked_context["labels_sha256"] != sha256_bytes(labels_bytes)
        or checked_context["labels_size"] != len(labels_bytes)
    ):
        raise LockedEvaluationError(
            "scoring ledger immutable context is inconsistent"
        )
    labels = validate_locked_labels_bytes(
        labels_bytes,
        gates,
        expected_sha256=checked_context["labels_sha256"],
        expected_ordered_case_ids=expected_ids,
    )
    predictions = parse_jsonl_strict(
        predictions_bytes, "scoring ledger parser-v2 predictions"
    )
    legacy = parse_jsonl_strict(
        legacy_predictions_bytes, "scoring ledger legacy predictions"
    )
    metrics, failures = score_locked_evaluation(
        labels,
        predictions,
        legacy,
        gate_bytes,
        raise_on_invalid=True,
    )
    label_rows = [
        canonical_json_bytes(record) for record in labels
    ]
    prediction_rows = [
        canonical_json_bytes(record) for record in predictions
    ]
    legacy_rows = [canonical_json_bytes(record) for record in legacy]
    rows = [
        _scoring_ledger_row(
            label,
            prediction,
            legacy_row,
            label_row_bytes=label_row,
            prediction_row_bytes=prediction_row,
            legacy_row_bytes=legacy_bytes,
            row_index=index,
            context=checked_context,
            gates=gates,
        )
        for index, (
            label,
            prediction,
            legacy_row,
            label_row,
            prediction_row,
            legacy_bytes,
        ) in enumerate(
            zip(
                labels,
                predictions,
                legacy,
                label_rows,
                prediction_rows,
                legacy_rows,
                strict=True,
            )
        )
    ]
    ledger_bytes = canonical_jsonl_bytes(rows)
    if b"".join(label_rows) != labels_bytes:
        raise LockedEvaluationError(
            "scoring ledger cannot reconstruct exact locked-label bytes"
        )
    return ledger_bytes, metrics, failures


def validate_scoring_ledger_bytes(
    ledger_bytes: bytes,
    predictions_bytes: bytes,
    legacy_predictions_bytes: bytes,
    gate_bytes: bytes,
    *,
    context: Mapping[str, Any],
    expected_ordered_case_ids: Sequence[str],
) -> dict[str, Any]:
    checked_context = validate_scoring_ledger_context(context)
    expected_ids = [
        _require_case_id(item, "scoring ledger expected case ID")
        for item in expected_ordered_case_ids
    ]
    rows = parse_jsonl_strict(ledger_bytes, SCORING_LEDGER_FILENAME)
    if (
        len(rows) != checked_context["row_count"]
        or len(rows) != len(expected_ids)
        or len(rows)
        != load_acceptance_gates(gate_bytes)["dataset_contract"]["total_cases"]
    ):
        raise LockedEvaluationError(
            "scoring ledger row membership is not exact"
        )
    label_rows: list[bytes] = []
    for index, (row, expected_case_id) in enumerate(
        zip(rows, expected_ids, strict=True)
    ):
        _require_exact_fields(
            row, _SCORING_LEDGER_ROW_FIELDS, "scoring ledger row"
        )
        if (
            row["schema_version"] != SCORING_LEDGER_SCHEMA_VERSION
            or _require_int(
                row["row_index"], "scoring ledger row index", minimum=0
            )
            != index
            or any(
                not exact_json_equal(row[field], checked_context[field])
                for field in _SCORING_LEDGER_CONTEXT_FIELDS
            )
            or row["case_id"] != expected_case_id
        ):
            raise LockedEvaluationError(
                "scoring ledger order or immutable context is invalid"
            )
        encoded = _require_string(
            row["label_record_base64"],
            "scoring ledger label record",
        )
        try:
            label_row = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise LockedEvaluationError(
                "scoring ledger label record encoding is invalid"
            ) from None
        if (
            base64.b64encode(label_row).decode("ascii") != encoded
            or len(label_row)
            != _require_int(
                row["label_record_size"],
                "scoring ledger label record size",
                minimum=1,
            )
            or sha256_bytes(label_row)
            != _require_sha256(
                row["label_record_sha256"],
                "scoring ledger label row SHA-256",
            )
        ):
            raise LockedEvaluationError(
                "scoring ledger label row bytes are invalid"
            )
        label = parse_json_strict(label_row, "scoring ledger label row")
        if (
            label.get("case_id") != expected_case_id
            or label.get("stratum") != row["stratum"]
        ):
            raise LockedEvaluationError(
                "scoring ledger label identity is invalid"
            )
        label_rows.append(label_row)
    reconstructed_labels = b"".join(label_rows)
    if (
        len(reconstructed_labels) != checked_context["labels_size"]
        or sha256_bytes(reconstructed_labels)
        != checked_context["labels_sha256"]
    ):
        raise LockedEvaluationError(
            "scoring ledger does not reconstruct registered locked labels"
        )
    rebuilt_bytes, metrics, failures = build_scoring_ledger_bytes(
        reconstructed_labels,
        predictions_bytes,
        legacy_predictions_bytes,
        gate_bytes,
        context=checked_context,
        expected_ordered_case_ids=expected_ids,
    )
    if rebuilt_bytes != ledger_bytes:
        raise LockedEvaluationError(
            "scoring ledger rows are not mechanically derived"
        )
    return {
        "ledger_bytes": ledger_bytes,
        "ledger_sha256": sha256_bytes(ledger_bytes),
        "ledger_size": len(ledger_bytes),
        "labels_bytes": reconstructed_labels,
        "labels_sha256": checked_context["labels_sha256"],
        "labels_size": checked_context["labels_size"],
        "row_count": len(rows),
        "ordered_case_ids": expected_ids,
        "metrics": metrics,
        "failures": failures,
    }


def render_metrics_csv(metrics: Mapping[str, Any]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "metric",
            "numerator",
            "denominator",
            "rate",
            "comparison",
            "threshold",
            "count_limit",
            "status",
            "passed",
            "reason",
        ]
    )

    def visit(value: Any, path: str) -> None:
        if isinstance(value, Mapping) and {
            "numerator",
            "denominator",
            "rate",
            "threshold",
            "status",
            "passed",
            "reason",
        }.issubset(value):
            threshold = value["threshold"]
            writer.writerow(
                [
                    path,
                    value["numerator"],
                    value["denominator"],
                    value["rate"]["rational"],
                    None if threshold is None else threshold["comparison"],
                    None if threshold is None else threshold["rational"],
                    None if threshold is None else threshold["count_limit"],
                    value["status"],
                    value["passed"],
                    value["reason"],
                ]
            )
            return
        if isinstance(value, Mapping):
            for key in sorted(value):
                visit(value[key], f"{path}.{key}" if path else key)

    visit(metrics, "")
    return output.getvalue().encode("utf-8")


_METRIC_RECORD_FIELDS = frozenset(
    {
        "numerator",
        "denominator",
        "rate",
        "threshold",
        "passed",
        "status",
        "reason",
    }
)
_VALID_METRICS_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "gate_contract_sha256",
        "dataset_summary",
        "topology_summary",
        "overall_typed_agreement",
        "overall_parsed_answer_agreement",
        "confusion_matrix",
        "class_metrics",
        "answer_presence_macro_f1",
        "per_stratum",
        "ambiguity",
        "no_answer",
        "span_errors",
        "material_correctness",
        "legacy_comparison",
        "mismatch_case_ids",
        "material_error_case_ids",
        "error_summary",
        "gates",
        "gate_summary",
        "rounded_values_used_for_gates",
        "manual_override",
    }
)
_INVALID_METRICS_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "gate_contract_sha256",
        "invalid_reason",
        "invalid_detail",
        "dataset_summary",
        "topology_summary",
        "error_summary",
        "mismatch_case_ids",
        "material_error_case_ids",
        "gates",
        "gate_summary",
        "rounded_values_used_for_gates",
        "manual_override",
    }
)


def _coerce_gate_contract(
    gates: Mapping[str, Any] | bytes | None,
) -> Mapping[str, Any]:
    if gates is None:
        project_root = Path(__file__).resolve().parents[2]
        return load_acceptance_gates(load_frozen_gate_bytes(project_root))
    if isinstance(gates, bytes):
        return load_acceptance_gates(gates)
    return gates


def _validate_metric_record(
    record: Mapping[str, Any],
    name: str,
    *,
    spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _require_exact_fields(record, _METRIC_RECORD_FIELDS, name)
    numerator = record["numerator"]
    denominator = record["denominator"]
    if numerator is not None and type(numerator) is not int:
        raise LockedEvaluationError(f"{name} numerator is invalid")
    if denominator is not None and (
        type(denominator) is not int or denominator < 0
    ):
        raise LockedEvaluationError(f"{name} denominator is invalid")
    threshold = record["threshold"]
    if threshold is None:
        comparison = None
        threshold_fraction = None
        count_limit = None
        mandatory = False
    else:
        _require_exact_fields(
            threshold,
            {
                "comparison",
                "numerator",
                "denominator",
                "rational",
                "count_limit",
            },
            f"{name}.threshold",
        )
        comparison = _require_enum(
            threshold["comparison"], (">=", "<="), f"{name}.comparison"
        )
        threshold_numerator = _require_int(
            threshold["numerator"], f"{name}.threshold.numerator"
        )
        threshold_denominator = _require_int(
            threshold["denominator"],
            f"{name}.threshold.denominator",
            minimum=1,
        )
        threshold_fraction = Fraction(
            threshold_numerator, threshold_denominator
        )
        if not exact_json_equal(
            threshold,
            {
                "comparison": comparison,
                **_fraction_parts(threshold_fraction),
                "count_limit": threshold["count_limit"],
            },
        ):
            raise LockedEvaluationError(f"{name} threshold rational is invalid")
        count_limit = threshold["count_limit"]
        if count_limit is not None and type(count_limit) is not int:
            raise LockedEvaluationError(f"{name} count limit is invalid")
        mandatory = record["status"] == "NA_INVALID" or record[
            "status"
        ] in {"PASS", "FAIL"}
    rebuilt = metric_record(
        numerator,
        denominator,
        comparison=comparison,
        threshold=threshold_fraction,
        count_limit=count_limit,
        mandatory=mandatory,
        reason=record["reason"],
    )
    if not exact_json_equal(dict(record), rebuilt):
        raise LockedEvaluationError(f"{name} status/rational semantics are invalid")
    if spec is not None:
        expected_threshold = {
            "comparison": spec["comparison"],
            **_fraction_parts(spec["threshold"]),
            "count_limit": spec["count_limit"],
        }
        if not exact_json_equal(threshold, expected_threshold):
            raise LockedEvaluationError(
                f"{name} threshold differs from the frozen gate"
            )
        registered_denominator = spec["denominator"]
        if (
            registered_denominator is not None
            and denominator != registered_denominator
        ):
            raise LockedEvaluationError(
                f"{name} denominator differs from the frozen gate"
            )
    return rebuilt


def validate_metrics_artifact(
    metrics: Mapping[str, Any],
    gates: Mapping[str, Any] | bytes | None = None,
    *,
    require_bindings: bool = False,
) -> dict[str, Any]:
    if type(require_bindings) is not bool:
        raise LockedEvaluationError(
            "metrics binding requirement must be a boolean"
        )
    gate_contract = _coerce_gate_contract(gates)
    specs = mandatory_gate_specs(gate_contract)
    status = _require_enum(
        metrics.get("status"), ("PASS", "FAIL", "INVALID"), "metrics status"
    )
    binding_fields = set(_METRICS_BINDING_FIELDS)
    present_bindings = binding_fields & set(metrics)
    if present_bindings and present_bindings != binding_fields:
        raise LockedEvaluationError("metrics artifact bindings are partial")
    if require_bindings and present_bindings != binding_fields:
        raise LockedEvaluationError("metrics artifact bindings are required")
    base_fields = (
        _INVALID_METRICS_FIELDS if "invalid_reason" in metrics else _VALID_METRICS_FIELDS
    )
    _require_exact_fields(
        metrics,
        set(base_fields) | present_bindings,
        "frozen metrics artifact",
    )
    if (
        metrics["schema_version"] != METRICS_SCHEMA_VERSION
        or metrics["gate_contract_sha256"] != FROZEN_ACCEPTANCE_GATE_SHA256
        or not exact_json_equal(
            metrics["dataset_summary"], _metrics_dataset_summary(gate_contract)
        )
        or not exact_json_equal(
            metrics["topology_summary"], _metrics_topology_summary(gate_contract)
        )
        or metrics["rounded_values_used_for_gates"] is not False
        or metrics["manual_override"] is not False
    ):
        raise LockedEvaluationError(
            "metrics schema/dataset/topology contract is invalid"
        )
    gate_records = metrics["gates"]
    if not isinstance(gate_records, Mapping) or set(gate_records) != set(specs):
        raise LockedEvaluationError(
            "metrics mandatory gate membership is not complete and registered"
        )
    for name, spec in specs.items():
        record = gate_records[name]
        if not isinstance(record, Mapping):
            raise LockedEvaluationError("metrics gate record is invalid")
        _validate_metric_record(record, f"metrics.gates.{name}", spec=spec)
    summary = metrics["gate_summary"]
    expected_summary = {
        "passed": sum(item["status"] == "PASS" for item in gate_records.values()),
        "failed": sum(item["status"] == "FAIL" for item in gate_records.values()),
        "na_invalid": sum(
            item["status"] in {"NA_INVALID", "INVALID"}
            for item in gate_records.values()
        ),
        "mandatory": len(specs),
    }
    if not exact_json_equal(summary, expected_summary):
        raise LockedEvaluationError("metrics gate summary is not mechanical")
    derived_status = (
        "INVALID"
        if expected_summary["na_invalid"]
        else "FAIL"
        if expected_summary["failed"]
        else "PASS"
    )
    if status != derived_status:
        raise LockedEvaluationError("metrics outcome differs from mandatory gates")

    mismatch_ids = metrics["mismatch_case_ids"]
    material_ids = metrics["material_error_case_ids"]
    for ids, name in (
        (mismatch_ids, "mismatch case IDs"),
        (material_ids, "material-error case IDs"),
    ):
        if (
            not isinstance(ids, list)
            or ids != sorted(set(ids))
            or any(_CASE_ID_PATTERN.fullmatch(item) is None for item in ids)
        ):
            raise LockedEvaluationError(f"metrics {name} are invalid")
    if not set(material_ids).issubset(mismatch_ids):
        raise LockedEvaluationError(
            "material-error cases are not a subset of mismatches"
        )
    if not exact_json_equal(
        metrics["error_summary"],
        {
            "mismatch_case_count": len(mismatch_ids),
            "material_error_case_count": len(material_ids),
        },
    ):
        raise LockedEvaluationError("metrics aggregate error summary is invalid")

    if "invalid_reason" in metrics:
        if (
            status != "INVALID"
            or not isinstance(metrics["invalid_reason"], str)
            or not metrics["invalid_reason"]
            or metrics["invalid_detail"] != "redacted"
            or mismatch_ids
            or material_ids
            or any(
                item["status"] != "NA_INVALID"
                or item["passed"] is not None
                for item in gate_records.values()
            )
        ):
            raise LockedEvaluationError("INVALID metrics artifact is inconsistent")
        if present_bindings:
            validate_metrics_artifact_bindings(
                metrics, {field: metrics[field] for field in _METRICS_BINDING_FIELDS}
            )
        return dict(metrics)

    dataset = gate_contract["dataset_contract"]
    total = dataset["total_cases"]
    confusion = metrics["confusion_matrix"]
    if not isinstance(confusion, Mapping) or set(confusion) != set(
        TYPED_DECISION_CLASSES
    ):
        raise LockedEvaluationError("metrics confusion matrix topology is invalid")
    confusion_counts: dict[str, dict[str, int]] = {}
    for actual in TYPED_DECISION_CLASSES:
        row = confusion[actual]
        if not isinstance(row, Mapping) or set(row) != set(
            TYPED_DECISION_CLASSES
        ):
            raise LockedEvaluationError(
                "metrics confusion matrix class membership is invalid"
            )
        confusion_counts[actual] = {}
        for predicted in TYPED_DECISION_CLASSES:
            checked = _validate_metric_record(
                row[predicted],
                f"metrics.confusion_matrix.{actual}.{predicted}",
            )
            if checked["denominator"] != total:
                raise LockedEvaluationError(
                    "confusion-matrix denominator is not the dataset total"
                )
            confusion_counts[actual][predicted] = checked["numerator"]
        if sum(confusion_counts[actual].values()) != dataset[
            "typed_decision_support"
        ][actual]:
            raise LockedEvaluationError(
                "confusion-matrix support differs from the frozen dataset"
            )
    if sum(sum(row.values()) for row in confusion_counts.values()) != total:
        raise LockedEvaluationError("confusion-matrix total is invalid")
    class_metrics = metrics["class_metrics"]
    if not isinstance(class_metrics, Mapping) or set(class_metrics) != set(
        TYPED_DECISION_CLASSES
    ):
        raise LockedEvaluationError("class-metric topology is invalid")
    for class_name in TYPED_DECISION_CLASSES:
        expected_class, _ = _classification_metrics(
            confusion_counts, class_name, total
        )
        if not exact_json_equal(class_metrics[class_name], expected_class):
            raise LockedEvaluationError(
                "class metrics are not derived from the confusion matrix"
            )
        for metric_name, record in expected_class.items():
            _validate_metric_record(
                record, f"metrics.class_metrics.{class_name}.{metric_name}"
            )

    for name in (
        "overall_typed_agreement",
        "overall_parsed_answer_agreement",
        "answer_presence_macro_f1",
    ):
        _validate_metric_record(metrics[name], f"metrics.{name}")
    if (
        metrics["overall_typed_agreement"]["numerator"]
        != sum(confusion_counts[item][item] for item in TYPED_DECISION_CLASSES)
        or metrics["overall_typed_agreement"]["denominator"] != total
        or gate_records["overall_exact_typed_decision"]["numerator"]
        != metrics["overall_typed_agreement"]["numerator"]
        or gate_records["answer_presence_macro_f1"]["rate"]
        != metrics["answer_presence_macro_f1"]["rate"]
    ):
        raise LockedEvaluationError(
            "overall metrics are not derived from registered aggregates"
        )
    for section_name, class_name in (
        ("ambiguity", "ambiguous"),
        ("no_answer", "no_answer"),
    ):
        section = metrics[section_name]
        if not isinstance(section, Mapping) or set(section) != {
            "precision",
            "recall",
            "specificity",
            "f1",
        }:
            raise LockedEvaluationError("presence-class metric topology is invalid")
        if (
            not exact_json_equal(
                section["precision"], gate_records[f"{section_name}_precision"]
            )
            or not exact_json_equal(
                section["recall"], gate_records[f"{section_name}_recall"]
            )
            or not exact_json_equal(
                section["specificity"], class_metrics[class_name]["specificity"]
            )
            or not exact_json_equal(
                section["f1"], class_metrics[class_name]["f1"]
            )
        ):
            raise LockedEvaluationError(
                "presence-class metrics are not mechanically linked"
            )
    if not exact_json_equal(
        metrics["span_errors"],
        {
            "boxed_final_miss": gate_records["boxed_final_miss"],
            "last_number_trap": gate_records["last_number_trap"],
            "wrong_span": gate_records["wrong_span"],
        },
    ):
        raise LockedEvaluationError("span-error gates are not mechanically linked")

    per_stratum = metrics["per_stratum"]
    if not isinstance(per_stratum, Mapping) or set(per_stratum) != set(
        dataset["strata"]
    ):
        raise LockedEvaluationError("per-stratum topology is invalid")
    checked_strata: dict[str, dict[str, dict[str, Any]]] = {}
    for stratum in dataset["strata"]:
        record = per_stratum[stratum]
        expected_fields = {
            "typed_agreement",
            "legacy_typed_agreement",
            "legacy_v2_delta",
            "wrong_span_errors",
            "material_errors",
            "floor_gate",
            "answer_bearing_gate",
            "critical",
        }
        _require_exact_fields(record, expected_fields, f"per_stratum.{stratum}")
        checked_metrics: dict[str, dict[str, Any]] = {}
        for metric_name in (
            "typed_agreement",
            "legacy_typed_agreement",
            "legacy_v2_delta",
            "wrong_span_errors",
            "material_errors",
        ):
            checked = _validate_metric_record(
                record[metric_name],
                f"per_stratum.{stratum}.{metric_name}",
            )
            if checked["denominator"] != dataset["cases_per_stratum"]:
                raise LockedEvaluationError(
                    "per-stratum denominator is not registered"
                )
            checked_metrics[metric_name] = checked
        for metric_name in (
            "typed_agreement",
            "legacy_typed_agreement",
            "wrong_span_errors",
            "material_errors",
        ):
            numerator = checked_metrics[metric_name]["numerator"]
            denominator = checked_metrics[metric_name]["denominator"]
            if (
                type(numerator) is not int
                or type(denominator) is not int
                or not 0 <= numerator <= denominator
            ):
                raise LockedEvaluationError(
                    "per-stratum count metric is outside its registered denominator"
                )
        expected_delta = metric_record(
            checked_metrics["typed_agreement"]["numerator"]
            - checked_metrics["legacy_typed_agreement"]["numerator"],
            checked_metrics["typed_agreement"]["denominator"],
        )
        if not exact_json_equal(record["legacy_v2_delta"], expected_delta):
            raise LockedEvaluationError(
                "per-stratum legacy-v2 delta is not mechanically derived"
            )
        checked_strata[stratum] = checked_metrics
        if (
            not exact_json_equal(
                record["floor_gate"], gate_records[f"stratum_floor_{stratum}"]
            )
            or not exact_json_equal(
                record["critical"], stratum in dataset["critical_strata"]
            )
        ):
            raise LockedEvaluationError("per-stratum gate topology is invalid")
        answer_gate_name = f"answer_bearing_{stratum}"
        expected_answer_gate = (
            gate_records[answer_gate_name]
            if answer_gate_name in gate_records
            else None
        )
        if not exact_json_equal(
            record["answer_bearing_gate"], expected_answer_gate
        ):
            raise LockedEvaluationError(
                "answer-bearing stratum gate topology is invalid"
            )

    material = metrics["material_correctness"]
    _require_exact_fields(
        material,
        {"overall", "by_stratum", "special_strata_gates"},
        "material_correctness",
    )
    expected_special = {
        name.removeprefix("material_correctness_"): value
        for name, value in gate_records.items()
        if name.startswith("material_correctness_")
    }
    if (
        not exact_json_equal(
            material["overall"], gate_records["material_correctness"]
        )
        or not exact_json_equal(
            material["special_strata_gates"], expected_special
        )
        or set(material["by_stratum"]) != set(dataset["strata"])
    ):
        raise LockedEvaluationError(
            "material-correctness topology is invalid"
        )
    for stratum, record in material["by_stratum"].items():
        checked = _validate_metric_record(
            record, f"material_correctness.by_stratum.{stratum}"
        )
        if (
            checked["denominator"] != dataset["cases_per_stratum"]
            or checked["numerator"]
            != per_stratum[stratum]["material_errors"]["numerator"]
        ):
            raise LockedEvaluationError(
                "material-correctness stratum aggregate is invalid"
            )

    legacy = metrics["legacy_comparison"]
    _require_exact_fields(
        legacy,
        {
            "overall_legacy",
            "overall_v2",
            "overall_delta",
            "clean_v2",
            "clean_legacy",
            "clean_delta",
            "critical_net_gain_by_stratum",
            "critical_strict_improvement",
            "paired_clean_regressions",
            "adapter_failures",
            "adapter_failure_case_ids",
        },
        "legacy_comparison",
    )
    legacy_metric_names = (
        "overall_legacy",
        "overall_v2",
        "overall_delta",
        "clean_v2",
        "clean_legacy",
        "clean_delta",
        "critical_strict_improvement",
        "paired_clean_regressions",
        "adapter_failures",
    )
    checked_legacy: dict[str, dict[str, Any]] = {}
    for name in legacy_metric_names:
        value = legacy[name]
        if not isinstance(value, Mapping):
            raise LockedEvaluationError(
                f"legacy_comparison.{name} must be an exact metric record"
            )
        checked_legacy[name] = _validate_metric_record(
            value, f"legacy_comparison.{name}"
        )

    total_v2 = sum(
        checked_strata[stratum]["typed_agreement"]["numerator"]
        for stratum in dataset["strata"]
    )
    total_legacy = sum(
        checked_strata[stratum]["legacy_typed_agreement"]["numerator"]
        for stratum in dataset["strata"]
    )
    expected_overall_v2 = metric_record(total_v2, total)
    expected_overall_legacy = metric_record(total_legacy, total)
    expected_overall_delta = metric_record(total_v2 - total_legacy, total)
    if (
        not exact_json_equal(
            metrics["overall_typed_agreement"], expected_overall_v2
        )
        or not exact_json_equal(legacy["overall_v2"], expected_overall_v2)
        or not exact_json_equal(
            legacy["overall_legacy"], expected_overall_legacy
        )
        or not exact_json_equal(
            legacy["overall_delta"], expected_overall_delta
        )
    ):
        raise LockedEvaluationError(
            "legacy overall aggregates are not mechanically derived"
        )

    legacy_gates = gate_contract["legacy_comparison_gates"]
    clean_contract = legacy_gates["clean_pooled_non_regression"]
    clean_strata = clean_contract["strata"]
    clean_denominator = clean_contract["denominator"]
    if (
        sum(
            checked_strata[stratum]["typed_agreement"]["denominator"]
            for stratum in clean_strata
        )
        != clean_denominator
    ):
        raise LockedEvaluationError(
            "clean aggregate denominator is not mechanically registered"
        )
    clean_v2 = sum(
        checked_strata[stratum]["typed_agreement"]["numerator"]
        for stratum in clean_strata
    )
    clean_legacy = sum(
        checked_strata[stratum]["legacy_typed_agreement"]["numerator"]
        for stratum in clean_strata
    )
    expected_clean_v2 = metric_record(clean_v2, clean_denominator)
    expected_clean_legacy = metric_record(clean_legacy, clean_denominator)
    expected_clean_delta = metric_record(
        clean_v2 - clean_legacy,
        clean_denominator,
        comparison=">=",
        threshold=Fraction(0),
        count_limit=0,
        mandatory=True,
    )
    if (
        not exact_json_equal(legacy["clean_v2"], expected_clean_v2)
        or not exact_json_equal(legacy["clean_legacy"], expected_clean_legacy)
        or not exact_json_equal(legacy["clean_delta"], expected_clean_delta)
        or not exact_json_equal(
            gate_records["clean_pooled_non_regression"], expected_clean_delta
        )
    ):
        raise LockedEvaluationError(
            "legacy clean aggregates are not mechanically derived"
        )

    critical_contract = legacy_gates["critical_strict_improvement"]
    critical_strata = critical_contract["strata"]
    critical_records = legacy["critical_net_gain_by_stratum"]
    if not isinstance(critical_records, Mapping) or set(critical_records) != set(
        critical_strata
    ):
        raise LockedEvaluationError(
            "critical net-gain metric membership is not registered"
        )
    critical_gains: dict[str, int] = {}
    for stratum in critical_strata:
        v2 = checked_strata[stratum]["typed_agreement"]
        legacy_typed = checked_strata[stratum]["legacy_typed_agreement"]
        gain = v2["numerator"] - legacy_typed["numerator"]
        expected_gain = metric_record(gain, v2["denominator"])
        value = critical_records[stratum]
        if not isinstance(value, Mapping):
            raise LockedEvaluationError(
                "critical net gain must be an exact metric record"
            )
        _validate_metric_record(
            value,
            f"legacy_comparison.critical_net_gain_by_stratum.{stratum}",
        )
        if not exact_json_equal(value, expected_gain):
            raise LockedEvaluationError(
                "critical net gain is not mechanically derived"
            )
        critical_gains[stratum] = gain
    minimum_gain = critical_contract[
        "minimum_net_gain_in_at_least_one_stratum"
    ]
    expected_critical_gate = metric_record(
        max(critical_gains.values()),
        dataset["cases_per_stratum"],
        comparison=">=",
        threshold=Fraction(minimum_gain, dataset["cases_per_stratum"]),
        count_limit=minimum_gain,
        mandatory=True,
    )
    if (
        not exact_json_equal(
            legacy["critical_strict_improvement"], expected_critical_gate
        )
        or not exact_json_equal(
            gate_records["critical_strict_improvement"],
            expected_critical_gate,
        )
    ):
        raise LockedEvaluationError(
            "critical strict-improvement gate is not mechanically derived"
        )

    paired_regressions = checked_legacy["paired_clean_regressions"]
    if (
        paired_regressions["denominator"] != clean_denominator
        or type(paired_regressions["numerator"]) is not int
        or not 0 <= paired_regressions["numerator"] <= clean_denominator
    ):
        raise LockedEvaluationError(
            "paired clean-regression aggregate is invalid"
        )
    adapter_ids = legacy["adapter_failure_case_ids"]
    if (
        not isinstance(adapter_ids, list)
        or adapter_ids != sorted(set(adapter_ids))
        or any(
            not isinstance(item, str)
            or _CASE_ID_PATTERN.fullmatch(item) is None
            for item in adapter_ids
        )
        or legacy["adapter_failures"]["numerator"] != len(adapter_ids)
        or legacy["adapter_failures"]["denominator"] != total
    ):
        raise LockedEvaluationError("legacy adapter diagnostics are invalid")
    if present_bindings:
        validate_metrics_artifact_bindings(
            metrics, {field: metrics[field] for field in _METRICS_BINDING_FIELDS}
        )
    return dict(metrics)


_METRICS_BINDING_FIELDS = (
    "authorization_id",
    "registered_parent_prefix",
    "authorization_lock_sha256",
    "authorization_manifest_sha256",
    "implementation_manifest_sha256",
    "prediction_seal_sha256",
    "prediction_manifest_sha256",
    "prediction_request_manifest_sha256",
    "locked_manifest_sha256",
    "input_manifest_sha256",
    "locked_input_sha256",
    "labels_manifest_sha256",
    "labels_sha256",
    "labels_open_transaction_sha256",
    "scores_prefix",
    "scoring_retry_kind",
    "scoring_execution_id",
    "scoring_actor",
    "stage_e_visibility_sha256",
    "retry_receipt_sha256",
    "scoring_ledger_sha256",
    "scoring_ledger_size",
    "scoring_ledger_etag",
    "case_universe_sha256",
    "row_count",
    "implementation_commit",
    "image_digest",
    "config_sha256",
)


def bind_metrics_artifacts(
    metrics: Mapping[str, Any],
    *,
    authorization_id: str,
    registered_parent_prefix: str,
    authorization_lock_sha256: str,
    authorization_manifest_sha256: str,
    implementation_manifest_sha256: str,
    prediction_seal_sha256: str,
    prediction_manifest_sha256: str,
    prediction_request_manifest_sha256: str,
    locked_manifest_sha256: str,
    input_manifest_sha256: str,
    locked_input_sha256: str,
    labels_manifest_sha256: str,
    labels_sha256: str,
    labels_open_transaction_sha256: str,
    scores_prefix: str,
    scoring_retry_kind: str,
    scoring_execution_id: str,
    scoring_actor: str,
    stage_e_visibility_sha256: str,
    retry_receipt_sha256: str | None,
    scoring_ledger_sha256: str,
    scoring_ledger_size: int,
    scoring_ledger_etag: str,
    case_universe_sha256: str,
    row_count: int,
    implementation_commit: str,
    image_digest: str,
    config_sha256: str,
) -> dict[str, Any]:
    if any(field in metrics for field in _METRICS_BINDING_FIELDS):
        raise LockedEvaluationError("metrics artifact bindings cannot be overwritten")
    scoring_attempt = validate_scoring_attempt_binding(
        parent_prefix=registered_parent_prefix,
        authorization_id=authorization_id,
        scores_prefix=scores_prefix,
        scoring_retry_kind=scoring_retry_kind,
        scoring_execution_id=scoring_execution_id,
        retry_receipt_sha256=retry_receipt_sha256,
    )
    bindings = {
        "authorization_id": validate_authorization_id(authorization_id),
        "registered_parent_prefix": validate_registered_parent_prefix(
            registered_parent_prefix
        ),
        "authorization_lock_sha256": _require_sha256(
            authorization_lock_sha256, "metrics authorization lock SHA-256"
        ),
        "authorization_manifest_sha256": _require_sha256(
            authorization_manifest_sha256,
            "metrics authorization manifest SHA-256",
        ),
        "implementation_manifest_sha256": _require_sha256(
            implementation_manifest_sha256,
            "metrics implementation manifest SHA-256",
        ),
        "prediction_seal_sha256": _require_sha256(
            prediction_seal_sha256, "metrics prediction seal SHA-256"
        ),
        "prediction_manifest_sha256": _require_sha256(
            prediction_manifest_sha256, "metrics prediction manifest SHA-256"
        ),
        "prediction_request_manifest_sha256": _require_sha256(
            prediction_request_manifest_sha256,
            "metrics prediction request manifest SHA-256",
        ),
        "locked_manifest_sha256": _require_sha256(
            locked_manifest_sha256, "metrics locked manifest SHA-256"
        ),
        "input_manifest_sha256": _require_sha256(
            input_manifest_sha256, "metrics locked-input manifest SHA-256"
        ),
        "locked_input_sha256": _require_sha256(
            locked_input_sha256, "metrics locked-input payload SHA-256"
        ),
        "labels_manifest_sha256": _require_sha256(
            labels_manifest_sha256, "metrics labels manifest SHA-256"
        ),
        "labels_sha256": _require_sha256(
            labels_sha256, "metrics labels SHA-256"
        ),
        "labels_open_transaction_sha256": _require_sha256(
            labels_open_transaction_sha256,
            "metrics labels-open transaction SHA-256",
        ),
        **scoring_attempt,
        "scoring_actor": _require_string(
            scoring_actor, "metrics scoring actor"
        ),
        "stage_e_visibility_sha256": _require_sha256(
            stage_e_visibility_sha256,
            "metrics Stage-E visibility SHA-256",
        ),
        "scoring_ledger_sha256": _require_sha256(
            scoring_ledger_sha256, "metrics scoring-ledger SHA-256"
        ),
        "scoring_ledger_size": _require_int(
            scoring_ledger_size, "metrics scoring-ledger size", minimum=1
        ),
        "scoring_ledger_etag": _require_string(
            scoring_ledger_etag, "metrics scoring-ledger ETag"
        ),
        "case_universe_sha256": _require_sha256(
            case_universe_sha256, "metrics case-universe SHA-256"
        ),
        "row_count": _require_int(
            row_count, "metrics row count", minimum=1
        ),
        "implementation_commit": _require_commit(
            implementation_commit, "metrics implementation commit"
        ),
        "image_digest": _require_image_digest(
            image_digest, "metrics image digest"
        ),
        "config_sha256": _require_sha256(
            config_sha256, "metrics config SHA-256"
        ),
    }
    return {**dict(metrics), **bindings}


def validate_metrics_artifact_bindings(
    metrics: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    if set(expected) != set(_METRICS_BINDING_FIELDS):
        raise LockedEvaluationError("expected metrics bindings are incomplete")
    canonical = {
        "authorization_id": validate_authorization_id(
            expected["authorization_id"]
        ),
        "registered_parent_prefix": validate_registered_parent_prefix(
            expected["registered_parent_prefix"]
        ),
        **{
            field: _require_sha256(
                expected[field], f"metrics binding {field}"
            )
            for field in (
                "authorization_lock_sha256",
                "authorization_manifest_sha256",
                "implementation_manifest_sha256",
                "prediction_seal_sha256",
                "prediction_manifest_sha256",
                "prediction_request_manifest_sha256",
                "locked_manifest_sha256",
                "input_manifest_sha256",
                "locked_input_sha256",
                "labels_manifest_sha256",
                "labels_sha256",
                "labels_open_transaction_sha256",
            )
        },
        **validate_scoring_attempt_binding(
            parent_prefix=expected["registered_parent_prefix"],
            authorization_id=expected["authorization_id"],
            scores_prefix=expected["scores_prefix"],
            scoring_retry_kind=expected["scoring_retry_kind"],
            scoring_execution_id=expected["scoring_execution_id"],
            retry_receipt_sha256=expected["retry_receipt_sha256"],
        ),
        "scoring_actor": _require_string(
            expected["scoring_actor"], "metrics binding scoring actor"
        ),
        "stage_e_visibility_sha256": _require_sha256(
            expected["stage_e_visibility_sha256"],
            "metrics binding Stage-E visibility SHA-256",
        ),
        "scoring_ledger_sha256": _require_sha256(
            expected["scoring_ledger_sha256"],
            "metrics binding scoring-ledger SHA-256",
        ),
        "scoring_ledger_size": _require_int(
            expected["scoring_ledger_size"],
            "metrics binding scoring-ledger size",
            minimum=1,
        ),
        "scoring_ledger_etag": _require_string(
            expected["scoring_ledger_etag"],
            "metrics binding scoring-ledger ETag",
        ),
        "case_universe_sha256": _require_sha256(
            expected["case_universe_sha256"],
            "metrics binding case-universe SHA-256",
        ),
        "row_count": _require_int(
            expected["row_count"], "metrics binding row count", minimum=1
        ),
        "implementation_commit": _require_commit(
            expected["implementation_commit"],
            "metrics binding implementation commit",
        ),
        "image_digest": _require_image_digest(
            expected["image_digest"], "metrics binding image digest"
        ),
        "config_sha256": _require_sha256(
            expected["config_sha256"], "metrics binding config SHA-256"
        ),
    }
    if any(
        not exact_json_equal(metrics.get(field), canonical[field])
        for field in _METRICS_BINDING_FIELDS
    ):
        raise LockedEvaluationError(
            "metrics artifact bindings differ from authenticated artifacts"
        )


def build_decision(
    metrics: Mapping[str, Any],
    *,
    authorization_id: str,
    registered_parent_prefix: str,
    authorization_lock_sha256: str,
    authorization_manifest_sha256: str,
    implementation_manifest_sha256: str,
    prediction_seal_sha256: str,
    prediction_manifest_sha256: str,
    prediction_request_manifest_sha256: str,
    locked_manifest_sha256: str,
    input_manifest_sha256: str,
    locked_input_sha256: str,
    labels_manifest_sha256: str,
    labels_sha256: str,
    labels_open_transaction_sha256: str,
    scores_prefix: str,
    scoring_retry_kind: str,
    scoring_execution_id: str,
    scoring_actor: str,
    stage_e_visibility_sha256: str,
    retry_receipt_sha256: str | None,
    scoring_ledger_sha256: str,
    scoring_ledger_size: int,
    scoring_ledger_etag: str,
    case_universe_sha256: str,
    row_count: int,
    implementation_commit: str,
    image_digest: str,
    config_sha256: str,
    decided_utc: str,
) -> dict[str, Any]:
    status = _require_enum(metrics.get("status"), ("PASS", "FAIL", "INVALID"), "status")
    gates = metrics.get("gates")
    if not isinstance(gates, Mapping) or not gates:
        raise LockedEvaluationError("metrics gates are missing")
    allowed_gate_statuses = {"PASS", "FAIL", "NA_INVALID", "INVALID"}
    if any(
        not isinstance(item, Mapping)
        or item.get("status") not in allowed_gate_statuses
        for item in gates.values()
    ):
        raise LockedEvaluationError("metrics gate statuses are invalid")
    derived = (
        "INVALID"
        if any(item.get("status") in {"NA_INVALID", "INVALID"} for item in gates.values())
        else "FAIL"
        if any(item.get("status") == "FAIL" for item in gates.values())
        else "PASS"
    )
    if status != derived:
        raise LockedEvaluationError("decision is not mechanically derived from gates")
    expected_metrics_bindings = {
        "authorization_id": validate_authorization_id(authorization_id),
        "registered_parent_prefix": validate_registered_parent_prefix(
            registered_parent_prefix
        ),
        "authorization_lock_sha256": _require_sha256(
            authorization_lock_sha256, "authorization lock SHA-256"
        ),
        "authorization_manifest_sha256": _require_sha256(
            authorization_manifest_sha256, "authorization manifest SHA-256"
        ),
        "implementation_manifest_sha256": _require_sha256(
            implementation_manifest_sha256,
            "implementation manifest SHA-256",
        ),
        "prediction_seal_sha256": _require_sha256(
            prediction_seal_sha256, "prediction seal SHA-256"
        ),
        "prediction_manifest_sha256": _require_sha256(
            prediction_manifest_sha256, "prediction manifest SHA-256"
        ),
        "prediction_request_manifest_sha256": _require_sha256(
            prediction_request_manifest_sha256,
            "prediction request manifest SHA-256",
        ),
        "locked_manifest_sha256": _require_sha256(
            locked_manifest_sha256, "locked manifest SHA-256"
        ),
        "input_manifest_sha256": _require_sha256(
            input_manifest_sha256, "locked-input manifest SHA-256"
        ),
        "locked_input_sha256": _require_sha256(
            locked_input_sha256, "locked-input payload SHA-256"
        ),
        "labels_manifest_sha256": _require_sha256(
            labels_manifest_sha256, "labels manifest SHA-256"
        ),
        "labels_sha256": _require_sha256(labels_sha256, "labels SHA-256"),
        "labels_open_transaction_sha256": _require_sha256(
            labels_open_transaction_sha256,
            "labels-open transaction SHA-256",
        ),
        **validate_scoring_attempt_binding(
            parent_prefix=registered_parent_prefix,
            authorization_id=authorization_id,
            scores_prefix=scores_prefix,
            scoring_retry_kind=scoring_retry_kind,
            scoring_execution_id=scoring_execution_id,
            retry_receipt_sha256=retry_receipt_sha256,
        ),
        "scoring_actor": _require_string(
            scoring_actor, "decision scoring actor"
        ),
        "stage_e_visibility_sha256": _require_sha256(
            stage_e_visibility_sha256,
            "decision Stage-E visibility SHA-256",
        ),
        "scoring_ledger_sha256": _require_sha256(
            scoring_ledger_sha256, "scoring-ledger SHA-256"
        ),
        "scoring_ledger_size": _require_int(
            scoring_ledger_size, "scoring-ledger size", minimum=1
        ),
        "scoring_ledger_etag": _require_string(
            scoring_ledger_etag, "scoring-ledger ETag"
        ),
        "case_universe_sha256": _require_sha256(
            case_universe_sha256, "case-universe SHA-256"
        ),
        "row_count": _require_int(row_count, "decision row count", minimum=1),
        "implementation_commit": _require_commit(
            implementation_commit, "implementation commit"
        ),
        "image_digest": _require_image_digest(image_digest, "image digest"),
        "config_sha256": _require_sha256(config_sha256, "config SHA-256"),
    }
    if any(field in metrics for field in _METRICS_BINDING_FIELDS):
        validate_metrics_artifact_bindings(metrics, expected_metrics_bindings)
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "authorization_id": expected_metrics_bindings["authorization_id"],
        "registered_parent_prefix": expected_metrics_bindings[
            "registered_parent_prefix"
        ],
        "authorization_lock_sha256": expected_metrics_bindings[
            "authorization_lock_sha256"
        ],
        "authorization_manifest_sha256": expected_metrics_bindings[
            "authorization_manifest_sha256"
        ],
        "implementation_manifest_sha256": expected_metrics_bindings[
            "implementation_manifest_sha256"
        ],
        "formal_decision": status,
        "metrics_sha256": sha256_bytes(canonical_json_bytes(dict(metrics))),
        "prediction_seal_sha256": expected_metrics_bindings[
            "prediction_seal_sha256"
        ],
        "prediction_manifest_sha256": expected_metrics_bindings[
            "prediction_manifest_sha256"
        ],
        "prediction_request_manifest_sha256": expected_metrics_bindings[
            "prediction_request_manifest_sha256"
        ],
        "locked_manifest_sha256": expected_metrics_bindings[
            "locked_manifest_sha256"
        ],
        "input_manifest_sha256": expected_metrics_bindings[
            "input_manifest_sha256"
        ],
        "locked_input_sha256": expected_metrics_bindings[
            "locked_input_sha256"
        ],
        "labels_manifest_sha256": expected_metrics_bindings[
            "labels_manifest_sha256"
        ],
        "labels_sha256": expected_metrics_bindings["labels_sha256"],
        "labels_open_transaction_sha256": expected_metrics_bindings[
            "labels_open_transaction_sha256"
        ],
        "scores_prefix": expected_metrics_bindings["scores_prefix"],
        "scoring_retry_kind": expected_metrics_bindings[
            "scoring_retry_kind"
        ],
        "scoring_execution_id": expected_metrics_bindings[
            "scoring_execution_id"
        ],
        "scoring_actor": expected_metrics_bindings["scoring_actor"],
        "stage_e_visibility_sha256": expected_metrics_bindings[
            "stage_e_visibility_sha256"
        ],
        "retry_receipt_sha256": expected_metrics_bindings[
            "retry_receipt_sha256"
        ],
        "scoring_ledger_sha256": expected_metrics_bindings[
            "scoring_ledger_sha256"
        ],
        "scoring_ledger_size": expected_metrics_bindings[
            "scoring_ledger_size"
        ],
        "scoring_ledger_etag": expected_metrics_bindings[
            "scoring_ledger_etag"
        ],
        "case_universe_sha256": expected_metrics_bindings[
            "case_universe_sha256"
        ],
        "row_count": expected_metrics_bindings["row_count"],
        "implementation_commit": expected_metrics_bindings[
            "implementation_commit"
        ],
        "image_digest": expected_metrics_bindings["image_digest"],
        "config_sha256": expected_metrics_bindings["config_sha256"],
        "mandatory_gate_count": len(gates),
        "passed_gate_count": sum(
            item.get("status") == "PASS" for item in gates.values()
        ),
        "failed_gate_count": sum(
            item.get("status") == "FAIL" for item in gates.values()
        ),
        "na_invalid_gate_count": sum(
            item.get("status") in {"NA_INVALID", "INVALID"}
            for item in gates.values()
        ),
        "manual_override": False,
        "metric_retry_allowed": False,
        "decided_utc": _require_utc(decided_utc, "decision timestamp"),
    }


_DECISION_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "formal_decision",
        "metrics_sha256",
        "prediction_seal_sha256",
        "prediction_manifest_sha256",
        "prediction_request_manifest_sha256",
        "locked_manifest_sha256",
        "input_manifest_sha256",
        "locked_input_sha256",
        "labels_manifest_sha256",
        "labels_sha256",
        "labels_open_transaction_sha256",
        "scores_prefix",
        "scoring_retry_kind",
        "scoring_execution_id",
        "scoring_actor",
        "stage_e_visibility_sha256",
        "retry_receipt_sha256",
        "scoring_ledger_sha256",
        "scoring_ledger_size",
        "scoring_ledger_etag",
        "case_universe_sha256",
        "row_count",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "mandatory_gate_count",
        "passed_gate_count",
        "failed_gate_count",
        "na_invalid_gate_count",
        "manual_override",
        "metric_retry_allowed",
        "decided_utc",
    }
)


def validate_decision(
    metrics: Mapping[str, Any], decision: Mapping[str, Any]
) -> dict[str, Any]:
    _require_exact_fields(decision, _DECISION_FIELDS, "decision")
    if decision["schema_version"] != DECISION_SCHEMA_VERSION:
        raise LockedEvaluationError("decision schema version is invalid")
    rebuilt = build_decision(
        metrics,
        authorization_id=decision["authorization_id"],
        registered_parent_prefix=decision["registered_parent_prefix"],
        authorization_lock_sha256=decision["authorization_lock_sha256"],
        authorization_manifest_sha256=decision[
            "authorization_manifest_sha256"
        ],
        implementation_manifest_sha256=decision[
            "implementation_manifest_sha256"
        ],
        prediction_seal_sha256=decision["prediction_seal_sha256"],
        prediction_manifest_sha256=decision["prediction_manifest_sha256"],
        prediction_request_manifest_sha256=decision[
            "prediction_request_manifest_sha256"
        ],
        locked_manifest_sha256=decision["locked_manifest_sha256"],
        input_manifest_sha256=decision["input_manifest_sha256"],
        locked_input_sha256=decision["locked_input_sha256"],
        labels_manifest_sha256=decision["labels_manifest_sha256"],
        labels_sha256=decision["labels_sha256"],
        labels_open_transaction_sha256=decision[
            "labels_open_transaction_sha256"
        ],
        scores_prefix=decision["scores_prefix"],
        scoring_retry_kind=decision["scoring_retry_kind"],
        scoring_execution_id=decision["scoring_execution_id"],
        scoring_actor=decision["scoring_actor"],
        stage_e_visibility_sha256=decision["stage_e_visibility_sha256"],
        retry_receipt_sha256=decision["retry_receipt_sha256"],
        scoring_ledger_sha256=decision["scoring_ledger_sha256"],
        scoring_ledger_size=decision["scoring_ledger_size"],
        scoring_ledger_etag=decision["scoring_ledger_etag"],
        case_universe_sha256=decision["case_universe_sha256"],
        row_count=decision["row_count"],
        implementation_commit=decision["implementation_commit"],
        image_digest=decision["image_digest"],
        config_sha256=decision["config_sha256"],
        decided_utc=decision["decided_utc"],
    )
    if not exact_json_equal(dict(decision), rebuilt):
        raise LockedEvaluationError("decision is not mechanically derived from metrics")
    return rebuilt


def build_retirement_record(
    decision: Mapping[str, Any],
    *,
    authorization_id: str,
    retired_utc: str,
) -> dict[str, Any]:
    _require_exact_fields(decision, _DECISION_FIELDS, "decision")
    if decision["schema_version"] != DECISION_SCHEMA_VERSION:
        raise LockedEvaluationError("decision schema version is invalid")
    authorization = validate_authorization_id(authorization_id)
    if decision["authorization_id"] != authorization:
        raise LockedEvaluationError("retirement authorization binding mismatch")
    validate_scoring_attempt_binding(
        parent_prefix=decision["registered_parent_prefix"],
        authorization_id=authorization,
        scores_prefix=decision["scores_prefix"],
        scoring_retry_kind=decision["scoring_retry_kind"],
        scoring_execution_id=decision["scoring_execution_id"],
        retry_receipt_sha256=decision["retry_receipt_sha256"],
    )
    _require_string(decision["scoring_actor"], "decision scoring actor")
    outcome = _require_enum(
        decision["formal_decision"], ("PASS", "FAIL", "INVALID"), "decision outcome"
    )
    if decision["manual_override"] is not False or decision["metric_retry_allowed"] is not False:
        raise LockedEvaluationError("decision violates one-shot retirement")
    for field in (
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "metrics_sha256",
        "prediction_seal_sha256",
        "prediction_manifest_sha256",
        "prediction_request_manifest_sha256",
        "locked_manifest_sha256",
        "input_manifest_sha256",
        "locked_input_sha256",
        "labels_manifest_sha256",
        "labels_sha256",
        "labels_open_transaction_sha256",
        "stage_e_visibility_sha256",
        "scoring_ledger_sha256",
        "case_universe_sha256",
        "config_sha256",
    ):
        _require_sha256(decision[field], f"decision {field}")
    _require_int(
        decision["scoring_ledger_size"],
        "decision scoring-ledger size",
        minimum=1,
    )
    _require_string(
        decision["scoring_ledger_etag"], "decision scoring-ledger ETag"
    )
    _require_commit(decision["implementation_commit"], "decision implementation")
    _require_image_digest(decision["image_digest"], "decision image")
    return {
        "schema_version": RETIREMENT_SCHEMA_VERSION,
        "authorization_id": authorization,
        "registered_parent_prefix": decision["registered_parent_prefix"],
        "authorization_lock_sha256": decision["authorization_lock_sha256"],
        "authorization_manifest_sha256": decision[
            "authorization_manifest_sha256"
        ],
        "implementation_manifest_sha256": decision[
            "implementation_manifest_sha256"
        ],
        "formal_decision": outcome,
        "metrics_sha256": decision["metrics_sha256"],
        "decision_sha256": sha256_bytes(canonical_json_bytes(dict(decision))),
        "prediction_seal_sha256": decision["prediction_seal_sha256"],
        "prediction_manifest_sha256": decision["prediction_manifest_sha256"],
        "prediction_request_manifest_sha256": decision[
            "prediction_request_manifest_sha256"
        ],
        "locked_manifest_sha256": decision["locked_manifest_sha256"],
        "input_manifest_sha256": decision["input_manifest_sha256"],
        "locked_input_sha256": decision["locked_input_sha256"],
        "labels_manifest_sha256": decision["labels_manifest_sha256"],
        "labels_sha256": decision["labels_sha256"],
        "labels_open_transaction_sha256": decision[
            "labels_open_transaction_sha256"
        ],
        "scores_prefix": decision["scores_prefix"],
        "scoring_retry_kind": decision["scoring_retry_kind"],
        "scoring_execution_id": decision["scoring_execution_id"],
        "scoring_actor": decision["scoring_actor"],
        "stage_e_visibility_sha256": decision[
            "stage_e_visibility_sha256"
        ],
        "retry_receipt_sha256": decision["retry_receipt_sha256"],
        "scoring_ledger_sha256": decision["scoring_ledger_sha256"],
        "scoring_ledger_size": decision["scoring_ledger_size"],
        "scoring_ledger_etag": decision["scoring_ledger_etag"],
        "case_universe_sha256": decision["case_universe_sha256"],
        "row_count": decision["row_count"],
        "implementation_commit": decision["implementation_commit"],
        "image_digest": decision["image_digest"],
        "config_sha256": decision["config_sha256"],
        "holdout_spent": True,
        "holdout_retired": True,
        "formal_evaluation_count": 1,
        "prediction_rerun_allowed": False,
        "metric_retry_allowed": False,
        "future_formal_claim_reuse_allowed": False,
        "retired_utc": _require_utc(retired_utc, "retirement timestamp"),
    }


_RETIREMENT_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "formal_decision",
        "metrics_sha256",
        "decision_sha256",
        "prediction_seal_sha256",
        "prediction_manifest_sha256",
        "prediction_request_manifest_sha256",
        "locked_manifest_sha256",
        "input_manifest_sha256",
        "locked_input_sha256",
        "labels_manifest_sha256",
        "labels_sha256",
        "labels_open_transaction_sha256",
        "scores_prefix",
        "scoring_retry_kind",
        "scoring_execution_id",
        "scoring_actor",
        "stage_e_visibility_sha256",
        "retry_receipt_sha256",
        "scoring_ledger_sha256",
        "scoring_ledger_size",
        "scoring_ledger_etag",
        "case_universe_sha256",
        "row_count",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "holdout_spent",
        "holdout_retired",
        "formal_evaluation_count",
        "prediction_rerun_allowed",
        "metric_retry_allowed",
        "future_formal_claim_reuse_allowed",
        "retired_utc",
    }
)


def validate_retirement_record(
    decision: Mapping[str, Any], retirement: Mapping[str, Any]
) -> dict[str, Any]:
    _require_exact_fields(retirement, _RETIREMENT_FIELDS, "retirement")
    rebuilt = build_retirement_record(
        decision,
        authorization_id=decision["authorization_id"],
        retired_utc=retirement["retired_utc"],
    )
    if not exact_json_equal(dict(retirement), rebuilt):
        raise LockedEvaluationError(
            "retirement is not mechanically derived from the decision"
        )
    return rebuilt


def build_closure_manifest(
    metrics: Mapping[str, Any],
    decision: Mapping[str, Any],
    retirement: Mapping[str, Any],
    *,
    scores_manifest_sha256: str,
    created_utc: str,
) -> dict[str, Any]:
    validate_decision(metrics, decision)
    validate_retirement_record(decision, retirement)
    return {
        "schema_version": CLOSURE_MANIFEST_SCHEMA_VERSION,
        "authorization_id": decision["authorization_id"],
        "registered_parent_prefix": decision["registered_parent_prefix"],
        "authorization_lock_sha256": decision["authorization_lock_sha256"],
        "authorization_manifest_sha256": decision[
            "authorization_manifest_sha256"
        ],
        "implementation_manifest_sha256": decision[
            "implementation_manifest_sha256"
        ],
        "outcome": decision["formal_decision"],
        "metrics_sha256": decision["metrics_sha256"],
        "decision_sha256": retirement["decision_sha256"],
        "retirement_sha256": sha256_bytes(
            canonical_json_bytes(dict(retirement))
        ),
        "scores_manifest_sha256": _require_sha256(
            scores_manifest_sha256, "scores manifest SHA-256"
        ),
        "prediction_seal_sha256": decision["prediction_seal_sha256"],
        "prediction_manifest_sha256": decision["prediction_manifest_sha256"],
        "prediction_request_manifest_sha256": decision[
            "prediction_request_manifest_sha256"
        ],
        "locked_manifest_sha256": decision["locked_manifest_sha256"],
        "input_manifest_sha256": decision["input_manifest_sha256"],
        "locked_input_sha256": decision["locked_input_sha256"],
        "labels_manifest_sha256": decision["labels_manifest_sha256"],
        "labels_sha256": decision["labels_sha256"],
        "labels_open_transaction_sha256": decision[
            "labels_open_transaction_sha256"
        ],
        "scores_prefix": decision["scores_prefix"],
        "scoring_retry_kind": decision["scoring_retry_kind"],
        "scoring_execution_id": decision["scoring_execution_id"],
        "scoring_actor": decision["scoring_actor"],
        "stage_e_visibility_sha256": decision[
            "stage_e_visibility_sha256"
        ],
        "retry_receipt_sha256": decision["retry_receipt_sha256"],
        "scoring_ledger_sha256": decision["scoring_ledger_sha256"],
        "scoring_ledger_size": decision["scoring_ledger_size"],
        "scoring_ledger_etag": decision["scoring_ledger_etag"],
        "case_universe_sha256": decision["case_universe_sha256"],
        "row_count": decision["row_count"],
        "implementation_commit": decision["implementation_commit"],
        "image_digest": decision["image_digest"],
        "config_sha256": decision["config_sha256"],
        "holdout_spent": True,
        "holdout_retired": True,
        "created_utc": _require_utc(created_utc, "closure timestamp"),
    }


def render_public_report(
    metrics: Mapping[str, Any],
    decision: Mapping[str, Any],
    retirement: Mapping[str, Any],
) -> bytes:
    validate_metrics_artifact(metrics)
    validate_decision(metrics, decision)
    validate_retirement_record(decision, retirement)
    status = decision["formal_decision"]
    error_summary = metrics["error_summary"]
    lines = [
        "# Phase 1.2B Parser-v2 Locked Evaluation",
        "",
        f"- Formal decision: **{status}**",
        "- Holdout retired: **yes**",
        "- Formal evaluation count: **1**",
        "- Manual override: **no**",
        f"- Mandatory gates: {decision['mandatory_gate_count']}",
        f"- Gates passed: {decision['passed_gate_count']}",
        f"- Gates failed: {decision['failed_gate_count']}",
        f"- Gates NA/invalid: {decision['na_invalid_gate_count']}",
        "",
        "## Aggregate error counts",
        "",
        f"- Mismatched cases: {error_summary['mismatch_case_count']}",
        (
            "- Material-error cases: "
            f"{error_summary['material_error_case_count']}"
        ),
        "",
        "## Scientific boundary",
        "",
        "- This is evaluator validation, not model evaluation.",
        "- The historical target model was not loaded, downloaded, or run.",
        "- Fixtures are operational evaluator cases, not behavioral samples.",
        "- Operational consensus references are not human ground truth.",
        "- No hidden-reasoning, invisible-CoT, internal-workspace, or J-space claim follows.",
        "",
    ]
    rendered = "\n".join(lines).encode("utf-8")
    prohibited = (
        "output_text",
        "registered_reference_answer",
        "expected_parsed_answer",
        "label_record_base64",
        "scoring_ledger",
        "case_id",
        "PV2-",
    )
    if any(token.encode("utf-8") in rendered for token in prohibited):
        raise AssertionError("public report leaked a private-detail field")
    return rendered


_LABELS_OPEN_TRANSACTION_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "state_prefix",
        "scores_prefix",
        "scoring_retry_kind",
        "retry_receipt_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "prediction_manifest_sha256",
        "prediction_seal_sha256",
        "prediction_request_manifest_sha256",
        "input_manifest_sha256",
        "locked_manifest_sha256",
        "labels_manifest_sha256",
        "labels_manifest_blob_name",
        "labels_manifest_etag",
        "labels_blob_name",
        "labels_sha256",
        "row_count",
        "ordered_case_ids",
        "case_universe_sha256",
        "acceptance_gates_sha256",
        "protocol_bundle_sha256",
        "parser_source_sha256",
        "parser_version",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "prior_receipt_sha256",
        "visibility_blob_name",
        "visibility_sha256",
        "visibility_etag",
        "execution_id",
        "actor",
        "labels_open_authorized",
        "intended_state",
        "formal_evaluation_ordinal",
        "overwrite",
        "created_utc",
    }
)


def build_labels_open_transaction(
    *,
    authorization_id: str,
    parent_prefix: str,
    state_prefix: str,
    scores_prefix: str,
    scoring_retry_kind: str,
    retry_receipt_sha256: str | None,
    authorization_lock_sha256: str,
    authorization_manifest_sha256: str,
    implementation_manifest_sha256: str,
    prediction_manifest_sha256: str,
    prediction_seal_sha256: str,
    prediction_request_manifest_sha256: str,
    input_manifest_sha256: str,
    locked_manifest_sha256: str,
    labels_manifest_sha256: str,
    labels_manifest_blob_name: str,
    labels_manifest_etag: str,
    labels_blob_name: str,
    labels_sha256: str,
    ordered_case_ids: Sequence[str],
    prior_receipt_sha256: str,
    visibility_blob_name: str,
    visibility_sha256: str,
    visibility_etag: str,
    implementation_commit: str,
    image_digest: str,
    config_sha256: str,
    execution_id: str,
    actor: str,
    created_utc: str,
) -> dict[str, Any]:
    ids = [_require_case_id(item) for item in ordered_case_ids]
    if ids != sorted(set(ids)):
        raise LockedEvaluationError(
            "labels-open transaction case universe is invalid"
        )
    scoring_attempt = validate_scoring_attempt_binding(
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
        scores_prefix=scores_prefix,
        scoring_retry_kind=scoring_retry_kind,
        scoring_execution_id=execution_id,
        retry_receipt_sha256=retry_receipt_sha256,
    )
    return {
        "schema_version": LABELS_OPEN_TRANSACTION_SCHEMA_VERSION,
        "authorization_id": validate_authorization_id(authorization_id),
        "registered_parent_prefix": validate_registered_parent_prefix(parent_prefix),
        "state_prefix": validate_exact_evaluation_prefix(
            state_prefix, parent_prefix, authorization_id, "state"
        ),
        "scores_prefix": scoring_attempt["scores_prefix"],
        "scoring_retry_kind": scoring_attempt["scoring_retry_kind"],
        "retry_receipt_sha256": scoring_attempt["retry_receipt_sha256"],
        "authorization_lock_sha256": _require_sha256(
            authorization_lock_sha256, "authorization lock SHA-256"
        ),
        "authorization_manifest_sha256": _require_sha256(
            authorization_manifest_sha256, "authorization manifest SHA-256"
        ),
        "implementation_manifest_sha256": _require_sha256(
            implementation_manifest_sha256,
            "implementation manifest SHA-256",
        ),
        "prediction_manifest_sha256": _require_sha256(
            prediction_manifest_sha256, "prediction manifest SHA-256"
        ),
        "prediction_seal_sha256": _require_sha256(
            prediction_seal_sha256, "prediction seal SHA-256"
        ),
        "prediction_request_manifest_sha256": _require_sha256(
            prediction_request_manifest_sha256,
            "prediction request manifest SHA-256",
        ),
        "input_manifest_sha256": _require_sha256(
            input_manifest_sha256, "locked-input manifest SHA-256"
        ),
        "locked_manifest_sha256": _require_sha256(
            locked_manifest_sha256, "locked manifest SHA-256"
        ),
        "labels_manifest_sha256": _require_sha256(
            labels_manifest_sha256, "labels manifest SHA-256"
        ),
        "labels_manifest_blob_name": normalize_blob_prefix(
            labels_manifest_blob_name
        ),
        "labels_manifest_etag": _require_string(
            labels_manifest_etag, "labels manifest ETag"
        ),
        "labels_blob_name": normalize_blob_prefix(labels_blob_name),
        "labels_sha256": _require_sha256(labels_sha256, "labels SHA-256"),
        "row_count": len(ids),
        "ordered_case_ids": ids,
        "case_universe_sha256": case_universe_sha256(ids),
        "acceptance_gates_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
        "protocol_bundle_sha256": FROZEN_PROTOCOL_BUNDLE_SHA256,
        "parser_source_sha256": FROZEN_PARSER_SOURCE_SHA256,
        "parser_version": FROZEN_PARSER_VERSION,
        "implementation_commit": _require_commit(
            implementation_commit, "implementation commit"
        ),
        "image_digest": _require_image_digest(image_digest, "image digest"),
        "config_sha256": _require_sha256(config_sha256, "config SHA-256"),
        "prior_receipt_sha256": _require_sha256(
            prior_receipt_sha256, "prior receipt SHA-256"
        ),
        "visibility_blob_name": normalize_blob_prefix(visibility_blob_name),
        "visibility_sha256": _require_sha256(
            visibility_sha256, "Stage-E visibility SHA-256"
        ),
        "visibility_etag": _require_string(
            visibility_etag, "Stage-E visibility ETag"
        ),
        "execution_id": _require_string(execution_id, "execution_id"),
        "actor": _require_string(actor, "actor"),
        "labels_open_authorized": True,
        "intended_state": "LABELS_READ",
        "formal_evaluation_ordinal": 1,
        "overwrite": False,
        "created_utc": _require_utc(created_utc, "transaction created_utc"),
    }


def validate_labels_open_transaction(
    record: Mapping[str, Any],
    *,
    expected_authorization_id: str | None = None,
    expected_parent_prefix: str | None = None,
) -> dict[str, Any]:
    _require_exact_fields(
        record, _LABELS_OPEN_TRANSACTION_FIELDS, "labels-open transaction"
    )
    if record["schema_version"] != LABELS_OPEN_TRANSACTION_SCHEMA_VERSION:
        raise LockedEvaluationError("labels-open transaction schema is invalid")
    try:
        rebuilt = build_labels_open_transaction(
            authorization_id=record["authorization_id"],
            parent_prefix=record["registered_parent_prefix"],
            state_prefix=record["state_prefix"],
            scores_prefix=record["scores_prefix"],
            scoring_retry_kind=record["scoring_retry_kind"],
            retry_receipt_sha256=record["retry_receipt_sha256"],
            authorization_lock_sha256=record["authorization_lock_sha256"],
            authorization_manifest_sha256=record[
                "authorization_manifest_sha256"
            ],
            implementation_manifest_sha256=record[
                "implementation_manifest_sha256"
            ],
            prediction_manifest_sha256=record["prediction_manifest_sha256"],
            prediction_seal_sha256=record["prediction_seal_sha256"],
            prediction_request_manifest_sha256=record[
                "prediction_request_manifest_sha256"
            ],
            input_manifest_sha256=record["input_manifest_sha256"],
            locked_manifest_sha256=record["locked_manifest_sha256"],
            labels_manifest_sha256=record["labels_manifest_sha256"],
            labels_manifest_blob_name=record["labels_manifest_blob_name"],
            labels_manifest_etag=record["labels_manifest_etag"],
            labels_blob_name=record["labels_blob_name"],
            labels_sha256=record["labels_sha256"],
            ordered_case_ids=record["ordered_case_ids"],
            prior_receipt_sha256=record["prior_receipt_sha256"],
            visibility_blob_name=record["visibility_blob_name"],
            visibility_sha256=record["visibility_sha256"],
            visibility_etag=record["visibility_etag"],
            implementation_commit=record["implementation_commit"],
            image_digest=record["image_digest"],
            config_sha256=record["config_sha256"],
            execution_id=record["execution_id"],
            actor=record["actor"],
            created_utc=record["created_utc"],
        )
    except (KeyError, TypeError, LockedEvaluationError):
        raise LockedEvaluationError(
            "labels-open transaction immutable bindings are invalid"
        ) from None
    parent = record["registered_parent_prefix"]
    authorization = record["authorization_id"]
    expected_visibility = (
        f"{derive_attempt_prefix(parent, authorization, 'visibility', 'E', record['scoring_retry_kind'], record['execution_id'])}/"
        "stage_e_visibility.json"
    )
    expected_labels = (
        f"{parent}/locked-labels/locked_reference_labels.jsonl"
    )
    expected_labels_manifest = (
        f"{parent}/locked-labels/locked_labels_manifest.json"
    )
    if (
        not exact_json_equal(dict(record), rebuilt)
        or record["labels_blob_name"] != expected_labels
        or record["labels_manifest_blob_name"] != expected_labels_manifest
        or record["visibility_blob_name"] != expected_visibility
        or (
            expected_authorization_id is not None
            and authorization
            != validate_authorization_id(expected_authorization_id)
        )
        or (
            expected_parent_prefix is not None
            and parent
            != validate_registered_parent_prefix(expected_parent_prefix)
        )
    ):
        raise LockedEvaluationError("labels-open transaction binding mismatch")
    return rebuilt


_SCORING_TRANSACTION_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "state_prefix",
        "scores_prefix",
        "scoring_retry_kind",
        "retry_receipt_sha256",
        "stage_e_visibility_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "prediction_manifest_sha256",
        "prediction_seal_sha256",
        "prediction_request_manifest_sha256",
        "locked_manifest_sha256",
        "input_manifest_sha256",
        "locked_input_sha256",
        "labels_manifest_sha256",
        "labels_sha256",
        "labels_open_transaction_sha256",
        "scoring_ledger_sha256",
        "scoring_ledger_size",
        "scoring_ledger_etag",
        "case_universe_sha256",
        "row_count",
        "acceptance_gates_sha256",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "score_payloads",
        "outcome",
        "execution_id",
        "actor",
        "formal_evaluation_ordinal",
        "metric_recompute_allowed",
        "overwrite",
        "created_utc",
    }
)


def build_scoring_transaction(
    *,
    authorization_id: str,
    parent_prefix: str,
    state_prefix: str,
    scores_prefix: str,
    scoring_retry_kind: str,
    retry_receipt_sha256: str | None,
    stage_e_visibility_sha256: str,
    authorization_lock_sha256: str,
    authorization_manifest_sha256: str,
    implementation_manifest_sha256: str,
    prediction_manifest_sha256: str,
    prediction_seal_sha256: str,
    prediction_request_manifest_sha256: str,
    locked_manifest_sha256: str,
    input_manifest_sha256: str,
    locked_input_sha256: str,
    labels_manifest_sha256: str,
    labels_sha256: str,
    labels_open_transaction_sha256: str,
    scoring_ledger_sha256: str,
    scoring_ledger_size: int,
    scoring_ledger_etag: str,
    case_universe_sha256: str,
    row_count: int,
    implementation_commit: str,
    image_digest: str,
    config_sha256: str,
    score_payloads: Mapping[str, bytes],
    outcome: str,
    execution_id: str,
    actor: str,
    created_utc: str,
) -> dict[str, Any]:
    expected_names = list(SCORE_MEMBER_NAMES[:-1])
    if list(score_payloads) != expected_names or set(score_payloads) != set(
        expected_names
    ):
        raise LockedEvaluationError(
            "scoring transaction payload membership/order is not exact"
        )
    metadata = []
    for name in expected_names:
        data = score_payloads[name]
        if type(data) is not bytes:
            raise LockedEvaluationError(
                "scoring transaction payload must contain exact bytes"
            )
        metadata.append(
            {
                "name": name,
                "size": len(data),
                "sha256": sha256_bytes(data),
            }
        )
    ledger_metadata = metadata[SCORE_MEMBER_NAMES.index(SCORING_LEDGER_FILENAME)]
    checked_ledger_sha256 = _require_sha256(
        scoring_ledger_sha256, "scoring transaction ledger SHA-256"
    )
    checked_ledger_size = _require_int(
        scoring_ledger_size, "scoring transaction ledger size", minimum=1
    )
    if (
        ledger_metadata["name"] != SCORING_LEDGER_FILENAME
        or ledger_metadata["sha256"] != checked_ledger_sha256
        or ledger_metadata["size"] != checked_ledger_size
    ):
        raise LockedEvaluationError(
            "scoring transaction ledger metadata is not exact"
        )
    scoring_attempt = validate_scoring_attempt_binding(
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
        scores_prefix=scores_prefix,
        scoring_retry_kind=scoring_retry_kind,
        scoring_execution_id=execution_id,
        retry_receipt_sha256=retry_receipt_sha256,
    )
    return {
        "schema_version": SCORING_TRANSACTION_SCHEMA_VERSION,
        "authorization_id": validate_authorization_id(authorization_id),
        "registered_parent_prefix": validate_registered_parent_prefix(
            parent_prefix
        ),
        "state_prefix": validate_exact_evaluation_prefix(
            state_prefix, parent_prefix, authorization_id, "state"
        ),
        "scores_prefix": scoring_attempt["scores_prefix"],
        "scoring_retry_kind": scoring_attempt["scoring_retry_kind"],
        "retry_receipt_sha256": scoring_attempt["retry_receipt_sha256"],
        "stage_e_visibility_sha256": _require_sha256(
            stage_e_visibility_sha256,
            "scoring transaction Stage-E visibility SHA-256",
        ),
        "authorization_lock_sha256": _require_sha256(
            authorization_lock_sha256, "authorization lock SHA-256"
        ),
        "authorization_manifest_sha256": _require_sha256(
            authorization_manifest_sha256, "authorization manifest SHA-256"
        ),
        "implementation_manifest_sha256": _require_sha256(
            implementation_manifest_sha256,
            "implementation manifest SHA-256",
        ),
        "prediction_manifest_sha256": _require_sha256(
            prediction_manifest_sha256, "prediction manifest SHA-256"
        ),
        "prediction_seal_sha256": _require_sha256(
            prediction_seal_sha256, "prediction seal SHA-256"
        ),
        "prediction_request_manifest_sha256": _require_sha256(
            prediction_request_manifest_sha256,
            "prediction request manifest SHA-256",
        ),
        "locked_manifest_sha256": _require_sha256(
            locked_manifest_sha256, "locked manifest SHA-256"
        ),
        "input_manifest_sha256": _require_sha256(
            input_manifest_sha256, "locked-input manifest SHA-256"
        ),
        "locked_input_sha256": _require_sha256(
            locked_input_sha256, "locked-input payload SHA-256"
        ),
        "labels_manifest_sha256": _require_sha256(
            labels_manifest_sha256, "labels manifest SHA-256"
        ),
        "labels_sha256": _require_sha256(labels_sha256, "labels SHA-256"),
        "labels_open_transaction_sha256": _require_sha256(
            labels_open_transaction_sha256,
            "labels-open transaction SHA-256",
        ),
        "scoring_ledger_sha256": checked_ledger_sha256,
        "scoring_ledger_size": checked_ledger_size,
        "scoring_ledger_etag": _require_string(
            scoring_ledger_etag, "scoring transaction ledger ETag"
        ),
        "case_universe_sha256": _require_sha256(
            case_universe_sha256, "case-universe SHA-256"
        ),
        "row_count": _require_int(row_count, "scoring row count", minimum=1),
        "acceptance_gates_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
        "implementation_commit": _require_commit(
            implementation_commit, "implementation commit"
        ),
        "image_digest": _require_image_digest(image_digest, "image digest"),
        "config_sha256": _require_sha256(config_sha256, "config SHA-256"),
        "score_payloads": metadata,
        "outcome": _require_enum(
            outcome, ("PASS", "FAIL", "INVALID"), "scoring outcome"
        ),
        "execution_id": _require_string(execution_id, "scoring execution ID"),
        "actor": _require_string(actor, "scoring actor"),
        "formal_evaluation_ordinal": 1,
        "metric_recompute_allowed": False,
        "overwrite": False,
        "created_utc": _require_utc(created_utc, "scoring transaction timestamp"),
    }


def validate_scoring_transaction(
    record: Mapping[str, Any],
    *,
    score_payloads: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    _require_exact_fields(
        record, _SCORING_TRANSACTION_FIELDS, "scoring transaction"
    )
    if record["schema_version"] != SCORING_TRANSACTION_SCHEMA_VERSION:
        raise LockedEvaluationError("scoring transaction schema is invalid")
    metadata = record["score_payloads"]
    if (
        not isinstance(metadata, list)
        or [item.get("name") for item in metadata if isinstance(item, Mapping)]
        != list(SCORE_MEMBER_NAMES[:-1])
    ):
        raise LockedEvaluationError(
            "scoring transaction payload metadata is invalid"
        )
    for index, item in enumerate(metadata):
        _require_exact_fields(
            item,
            {"name", "size", "sha256"},
            f"scoring transaction payload[{index}]",
        )
        _require_int(item["size"], "scoring payload size", minimum=0)
        _require_sha256(item["sha256"], "scoring payload SHA-256")
        if score_payloads is not None:
            data = score_payloads.get(item["name"])
            if (
                type(data) is not bytes
                or len(data) != item["size"]
                or sha256_bytes(data) != item["sha256"]
            ):
                raise LockedEvaluationError(
                    "score bytes differ from their original scoring transaction"
                )
    ledger_metadata = metadata[SCORE_MEMBER_NAMES.index(SCORING_LEDGER_FILENAME)]
    if (
        not exact_json_equal(
            ledger_metadata["sha256"], record["scoring_ledger_sha256"]
        )
        or not exact_json_equal(
            ledger_metadata["size"], record["scoring_ledger_size"]
        )
    ):
        raise LockedEvaluationError(
            "scoring transaction ledger metadata is inconsistent"
        )
    try:
        if score_payloads is None:
            checked = {
                "schema_version": SCORING_TRANSACTION_SCHEMA_VERSION,
                "authorization_id": validate_authorization_id(
                    record["authorization_id"]
                ),
                "registered_parent_prefix": validate_registered_parent_prefix(
                    record["registered_parent_prefix"]
                ),
                "state_prefix": validate_exact_evaluation_prefix(
                    record["state_prefix"],
                    record["registered_parent_prefix"],
                    record["authorization_id"],
                    "state",
                ),
                **validate_scoring_attempt_binding(
                    parent_prefix=record["registered_parent_prefix"],
                    authorization_id=record["authorization_id"],
                    scores_prefix=record["scores_prefix"],
                    scoring_retry_kind=record["scoring_retry_kind"],
                    scoring_execution_id=record["execution_id"],
                    retry_receipt_sha256=record["retry_receipt_sha256"],
                ),
            }
            del checked
            for field in (
                "authorization_lock_sha256",
                "authorization_manifest_sha256",
                "implementation_manifest_sha256",
                "prediction_manifest_sha256",
                "prediction_seal_sha256",
                "prediction_request_manifest_sha256",
                "locked_manifest_sha256",
                "input_manifest_sha256",
                "locked_input_sha256",
                "labels_manifest_sha256",
                "labels_sha256",
                "labels_open_transaction_sha256",
                "stage_e_visibility_sha256",
                "scoring_ledger_sha256",
                "case_universe_sha256",
                "config_sha256",
            ):
                _require_sha256(record[field], f"scoring transaction {field}")
            _require_commit(
                record["implementation_commit"],
                "scoring transaction implementation commit",
            )
            _require_image_digest(
                record["image_digest"], "scoring transaction image digest"
            )
            _require_int(record["row_count"], "scoring row count", minimum=1)
            _require_int(
                record["scoring_ledger_size"],
                "scoring transaction ledger size",
                minimum=1,
            )
            _require_string(
                record["scoring_ledger_etag"],
                "scoring transaction ledger ETag",
            )
            _require_string(record["execution_id"], "scoring execution ID")
            _require_string(record["actor"], "scoring actor")
            _require_utc(record["created_utc"], "scoring transaction timestamp")
            if (
                record["acceptance_gates_sha256"]
                != FROZEN_ACCEPTANCE_GATE_SHA256
                or _require_int(
                    record["formal_evaluation_ordinal"],
                    "formal evaluation ordinal",
                    minimum=1,
                )
                != 1
                or record["metric_recompute_allowed"] is not False
                or record["overwrite"] is not False
                or record["outcome"] not in {"PASS", "FAIL", "INVALID"}
            ):
                raise LockedEvaluationError(
                    "scoring transaction one-shot bindings are invalid"
                )
            return dict(record)
        rebuilt = build_scoring_transaction(
            authorization_id=record["authorization_id"],
            parent_prefix=record["registered_parent_prefix"],
            state_prefix=record["state_prefix"],
            scores_prefix=record["scores_prefix"],
            scoring_retry_kind=record["scoring_retry_kind"],
            retry_receipt_sha256=record["retry_receipt_sha256"],
            stage_e_visibility_sha256=record[
                "stage_e_visibility_sha256"
            ],
            authorization_lock_sha256=record["authorization_lock_sha256"],
            authorization_manifest_sha256=record[
                "authorization_manifest_sha256"
            ],
            implementation_manifest_sha256=record[
                "implementation_manifest_sha256"
            ],
            prediction_manifest_sha256=record["prediction_manifest_sha256"],
            prediction_seal_sha256=record["prediction_seal_sha256"],
            prediction_request_manifest_sha256=record[
                "prediction_request_manifest_sha256"
            ],
            locked_manifest_sha256=record["locked_manifest_sha256"],
            input_manifest_sha256=record["input_manifest_sha256"],
            locked_input_sha256=record["locked_input_sha256"],
            labels_manifest_sha256=record["labels_manifest_sha256"],
            labels_sha256=record["labels_sha256"],
            labels_open_transaction_sha256=record[
                "labels_open_transaction_sha256"
            ],
            scoring_ledger_sha256=record["scoring_ledger_sha256"],
            scoring_ledger_size=record["scoring_ledger_size"],
            scoring_ledger_etag=record["scoring_ledger_etag"],
            case_universe_sha256=record["case_universe_sha256"],
            row_count=record["row_count"],
            implementation_commit=record["implementation_commit"],
            image_digest=record["image_digest"],
            config_sha256=record["config_sha256"],
            score_payloads=score_payloads,
            outcome=record["outcome"],
            execution_id=record["execution_id"],
            actor=record["actor"],
            created_utc=record["created_utc"],
        )
    except (KeyError, TypeError, LockedEvaluationError):
        raise LockedEvaluationError(
            "scoring transaction immutable bindings are invalid"
        ) from None
    if not exact_json_equal(dict(record), rebuilt):
        raise LockedEvaluationError(
            "scoring transaction differs from its exact score bytes"
        )
    return rebuilt


_SCORING_ATTESTATION_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "state_prefix",
        "scores_prefix",
        "scoring_retry_kind",
        "retry_receipt_sha256",
        "stage_e_visibility_sha256",
        "scoring_transaction_sha256",
        "labels_open_transaction_sha256",
        "labels_manifest_sha256",
        "labels_sha256",
        "scoring_ledger_sha256",
        "scoring_ledger_size",
        "scoring_ledger_etag",
        "prediction_manifest_sha256",
        "prediction_seal_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "score_manifest_blob_name",
        "score_manifest_sha256",
        "score_manifest_etag",
        "score_members",
        "outcome",
        "execution_id",
        "actor",
        "formal_evaluation_ordinal",
        "metric_recompute_allowed",
        "overwrite",
        "created_utc",
    }
)


def build_scoring_attestation(
    transaction: Mapping[str, Any],
    *,
    score_manifest_bytes: bytes,
    score_manifest_etag: str,
) -> dict[str, Any]:
    validate_scoring_transaction(transaction)
    manifest_hash = sha256_bytes(score_manifest_bytes)
    manifest = validate_score_manifest(
        score_manifest_bytes,
        expected_sha256=manifest_hash,
        parent_prefix=transaction["registered_parent_prefix"],
        authorization_id=transaction["authorization_id"],
    )
    expected_manifest_bindings = {
        "scoring_transaction_sha256": sha256_bytes(
            canonical_json_bytes(dict(transaction))
        ),
        "scoring_execution_id": transaction["execution_id"],
        "scoring_actor": transaction["actor"],
        "outcome": transaction["outcome"],
        "created_utc": transaction["created_utc"],
        "scoring_ledger_sha256": transaction["scoring_ledger_sha256"],
        "scoring_ledger_size": transaction["scoring_ledger_size"],
        "scoring_ledger_etag": transaction["scoring_ledger_etag"],
        **{
            field: transaction[field]
            for field in (
                "authorization_id",
                "registered_parent_prefix",
                "scores_prefix",
                "scoring_retry_kind",
                "retry_receipt_sha256",
                "stage_e_visibility_sha256",
                "authorization_lock_sha256",
                "authorization_manifest_sha256",
                "implementation_manifest_sha256",
                "prediction_manifest_sha256",
                "prediction_seal_sha256",
                "prediction_request_manifest_sha256",
                "locked_manifest_sha256",
                "input_manifest_sha256",
                "locked_input_sha256",
                "labels_manifest_sha256",
                "labels_sha256",
                "labels_open_transaction_sha256",
                "case_universe_sha256",
                "row_count",
                "implementation_commit",
                "image_digest",
                "config_sha256",
            )
        },
    }
    if any(
        not exact_json_equal(manifest.get(field), expected)
        for field, expected in expected_manifest_bindings.items()
    ):
        raise LockedEvaluationError(
            "score manifest differs from its original scoring transaction"
        )
    members = [dict(item) for item in manifest["payload_members"]]
    members.append(
        {
            "name": SCORE_MEMBER_NAMES[-1],
            "size": len(score_manifest_bytes),
            "sha256": manifest_hash,
            "etag": _require_string(
                score_manifest_etag, "score manifest ETag"
            ),
        }
    )
    return {
        "schema_version": SCORING_ATTESTATION_SCHEMA_VERSION,
        "authorization_id": transaction["authorization_id"],
        "registered_parent_prefix": transaction["registered_parent_prefix"],
        "state_prefix": transaction["state_prefix"],
        "scores_prefix": transaction["scores_prefix"],
        "scoring_retry_kind": transaction["scoring_retry_kind"],
        "retry_receipt_sha256": transaction["retry_receipt_sha256"],
        "stage_e_visibility_sha256": transaction[
            "stage_e_visibility_sha256"
        ],
        "scoring_transaction_sha256": manifest[
            "scoring_transaction_sha256"
        ],
        "labels_open_transaction_sha256": transaction[
            "labels_open_transaction_sha256"
        ],
        "labels_manifest_sha256": transaction["labels_manifest_sha256"],
        "labels_sha256": transaction["labels_sha256"],
        "scoring_ledger_sha256": transaction["scoring_ledger_sha256"],
        "scoring_ledger_size": transaction["scoring_ledger_size"],
        "scoring_ledger_etag": transaction["scoring_ledger_etag"],
        "prediction_manifest_sha256": transaction[
            "prediction_manifest_sha256"
        ],
        "prediction_seal_sha256": transaction["prediction_seal_sha256"],
        "authorization_lock_sha256": transaction[
            "authorization_lock_sha256"
        ],
        "authorization_manifest_sha256": transaction[
            "authorization_manifest_sha256"
        ],
        "implementation_manifest_sha256": transaction[
            "implementation_manifest_sha256"
        ],
        "implementation_commit": transaction["implementation_commit"],
        "image_digest": transaction["image_digest"],
        "config_sha256": transaction["config_sha256"],
        "score_manifest_blob_name": (
            f"{transaction['scores_prefix']}/{SCORE_MEMBER_NAMES[-1]}"
        ),
        "score_manifest_sha256": manifest_hash,
        "score_manifest_etag": score_manifest_etag,
        "score_members": members,
        "outcome": transaction["outcome"],
        "execution_id": transaction["execution_id"],
        "actor": transaction["actor"],
        "formal_evaluation_ordinal": 1,
        "metric_recompute_allowed": False,
        "overwrite": False,
        "created_utc": transaction["created_utc"],
    }


def validate_scoring_attestation(
    record: Mapping[str, Any],
    *,
    transaction: Mapping[str, Any],
    score_manifest_bytes: bytes,
    score_manifest_etag: str,
) -> dict[str, Any]:
    _require_exact_fields(
        record, _SCORING_ATTESTATION_FIELDS, "scoring attestation"
    )
    if record["schema_version"] != SCORING_ATTESTATION_SCHEMA_VERSION:
        raise LockedEvaluationError("scoring attestation schema is invalid")
    rebuilt = build_scoring_attestation(
        transaction,
        score_manifest_bytes=score_manifest_bytes,
        score_manifest_etag=score_manifest_etag,
    )
    if not exact_json_equal(dict(record), rebuilt):
        raise LockedEvaluationError(
            "scoring attestation differs from the attested score leaf"
        )
    return rebuilt


_SCORING_INCOMPLETE_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "state_prefix",
        "scores_prefix",
        "scoring_retry_kind",
        "scoring_execution_id",
        "scoring_actor",
        "retry_receipt_sha256",
        "labels_open_transaction_blob_name",
        "labels_open_transaction_sha256",
        "observed_score_members",
        "observed_score_membership_sha256",
        "observed_state_members",
        "reason_code",
        "outcome",
        "labels_reread_allowed",
        "scoring_retry_allowed",
        "holdout_spent",
        "holdout_retired",
        "evidence_execution_id",
        "evidence_actor",
        "created_utc",
        "overwrite",
    }
)


def build_scoring_incomplete_record(
    labels_open_transaction: Mapping[str, Any],
    *,
    observed_score_members: Sequence[Mapping[str, Any]],
    observed_state_members: Sequence[str],
    evidence_execution_id: str,
    evidence_actor: str,
    created_utc: str,
) -> dict[str, Any]:
    transaction = validate_labels_open_transaction(
        labels_open_transaction
    )
    parent = transaction["registered_parent_prefix"]
    authorization = transaction["authorization_id"]
    state_prefix = transaction["state_prefix"]
    score_members = _canonical_attempt_members(
        observed_score_members,
        parent_prefix=parent,
        authorization_id=authorization,
        allowed_prefixes={"scores": transaction["scores_prefix"]},
        name="scoring-incomplete score members",
    )
    if any(
        not item["blob_name"].startswith(
            f"{transaction['scores_prefix']}/"
        )
        for item in score_members
    ):
        raise LockedEvaluationError(
            "scoring-incomplete score membership is outside its attempt"
        )
    state_members = [
        normalize_blob_prefix(item) for item in observed_state_members
    ]
    if (
        state_members != sorted(set(state_members))
        or any(
            not item.startswith(f"{state_prefix}/")
            for item in state_members
        )
        or f"{state_prefix}/{SCORING_INCOMPLETE_FILENAME}"
        in state_members
    ):
        raise LockedEvaluationError(
            "scoring-incomplete state membership is not canonical"
        )
    attempt = validate_scoring_attempt_binding(
        parent_prefix=parent,
        authorization_id=authorization,
        scores_prefix=transaction["scores_prefix"],
        scoring_retry_kind=transaction["scoring_retry_kind"],
        scoring_execution_id=transaction["execution_id"],
        retry_receipt_sha256=transaction["retry_receipt_sha256"],
    )
    return {
        "schema_version": SCORING_INCOMPLETE_SCHEMA_VERSION,
        "authorization_id": authorization,
        "registered_parent_prefix": parent,
        "state_prefix": state_prefix,
        **attempt,
        "scoring_actor": transaction["actor"],
        "labels_open_transaction_blob_name": (
            f"{state_prefix}/{LABELS_OPEN_TRANSACTION_FILENAME}"
        ),
        "labels_open_transaction_sha256": sha256_bytes(
            canonical_json_bytes(dict(transaction))
        ),
        "observed_score_members": score_members,
        "observed_score_membership_sha256": attempt_membership_sha256(
            score_members
        ),
        "observed_state_members": state_members,
        "reason_code": "labels_open_without_sealed_scores",
        "outcome": "INVALID",
        "labels_reread_allowed": False,
        "scoring_retry_allowed": False,
        "holdout_spent": True,
        "holdout_retired": True,
        "evidence_execution_id": _require_string(
            evidence_execution_id,
            "scoring-incomplete evidence execution ID",
        ),
        "evidence_actor": _require_string(
            evidence_actor, "scoring-incomplete evidence actor"
        ),
        "created_utc": _require_utc(
            created_utc, "scoring-incomplete created_utc"
        ),
        "overwrite": False,
    }


def validate_scoring_incomplete_record(
    record: Mapping[str, Any],
    *,
    labels_open_transaction: Mapping[str, Any],
) -> dict[str, Any]:
    _require_exact_fields(
        record, _SCORING_INCOMPLETE_FIELDS, "scoring-incomplete record"
    )
    if record["schema_version"] != SCORING_INCOMPLETE_SCHEMA_VERSION:
        raise LockedEvaluationError(
            "scoring-incomplete record schema is invalid"
        )
    try:
        rebuilt = build_scoring_incomplete_record(
            labels_open_transaction,
            observed_score_members=record["observed_score_members"],
            observed_state_members=record["observed_state_members"],
            evidence_execution_id=record["evidence_execution_id"],
            evidence_actor=record["evidence_actor"],
            created_utc=record["created_utc"],
        )
    except (KeyError, TypeError, LockedEvaluationError):
        raise LockedEvaluationError(
            "scoring-incomplete record bindings are invalid"
        ) from None
    if not exact_json_equal(dict(record), rebuilt):
        raise LockedEvaluationError(
            "scoring-incomplete record differs from labels-open evidence"
        )
    return rebuilt


_INVALID_CLOSURE_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "state_prefix",
        "labels_read_receipt_sha256",
        "labels_open_transaction_sha256",
        "prediction_manifest_sha256",
        "prediction_seal_sha256",
        "prediction_request_manifest_sha256",
        "prediction_retry_kind",
        "prediction_execution_id",
        "prediction_actor",
        "predictions_prefix",
        "scores_prefix",
        "visibility_prefix",
        "scoring_retry_kind",
        "scoring_execution_id",
        "scoring_actor",
        "retry_receipt_sha256",
        "failure_class",
        "observed_score_members",
        "observed_score_membership_sha256",
        "observed_visibility_members",
        "observed_visibility_membership_sha256",
        "observed_state_artifacts",
        "observed_state_artifacts_sha256",
        "score_artifact_complete",
        "score_manifest_accepted",
        "metrics_accepted",
        "decision_accepted",
        "result_status",
        "formal_evaluation_ordinal",
        "labels_reread_allowed",
        "scoring_retry_allowed",
        "holdout_spent",
        "holdout_retired",
        "created_utc",
        "overwrite",
    }
)
INVALID_CLOSURE_FAILURE_CLASSES = (
    "incomplete_score_artifacts_after_labels_read",
)


def build_invalid_closure_manifest(
    labels_open_transaction: Mapping[str, Any],
    labels_read_receipt: Mapping[str, Any],
    *,
    prediction_retry_kind: str,
    prediction_execution_id: str,
    prediction_actor: str,
    predictions_prefix: str,
    observed_score_members: Sequence[Mapping[str, Any]],
    observed_visibility_members: Sequence[Mapping[str, Any]],
    observed_state_artifacts: Sequence[Mapping[str, Any]] = (),
    failure_class: str = "incomplete_score_artifacts_after_labels_read",
) -> dict[str, Any]:
    transaction = validate_labels_open_transaction(labels_open_transaction)
    receipt = validate_state_receipt(
        labels_read_receipt, name="INVALID closure LABELS_READ receipt"
    )
    if (
        receipt["state"] != "LABELS_READ"
        or labels_read_receipt["retry_kind"] != "none"
        or labels_read_receipt["authorization_id"]
        != transaction["authorization_id"]
        or labels_read_receipt["registered_parent_prefix"]
        != transaction["registered_parent_prefix"]
        or labels_read_receipt["artifact_manifest_hashes"]["labels_manifest"]
        != transaction["labels_manifest_sha256"]
        or labels_read_receipt["execution_id"] != transaction["execution_id"]
        or labels_read_receipt["actor"] != transaction["actor"]
    ):
        raise LockedEvaluationError(
            "INVALID closure does not bind the exact LABELS_READ receipt"
        )
    parent = transaction["registered_parent_prefix"]
    authorization = transaction["authorization_id"]
    checked_prediction_retry = _require_enum(
        prediction_retry_kind,
        ("none", "infrastructure_pre_input"),
        "INVALID closure prediction retry kind",
    )
    checked_prediction_execution = _require_string(
        prediction_execution_id,
        "INVALID closure prediction execution ID",
        maximum=512,
    )
    checked_predictions_prefix = validate_exact_attempt_prefix(
        predictions_prefix,
        parent,
        authorization,
        "predictions",
        "P",
        checked_prediction_retry,
        checked_prediction_execution,
    )
    visibility_prefix = transaction["visibility_blob_name"].rsplit("/", 1)[0]
    validate_exact_attempt_prefix(
        visibility_prefix,
        parent,
        authorization,
        "visibility",
        "E",
        transaction["scoring_retry_kind"],
        transaction["execution_id"],
    )
    scores = _canonical_attempt_members(
        observed_score_members,
        parent_prefix=parent,
        authorization_id=authorization,
        allowed_prefixes={"scores": transaction["scores_prefix"]},
        name="INVALID closure score members",
    )
    visibility = _canonical_attempt_members(
        observed_visibility_members,
        parent_prefix=parent,
        authorization_id=authorization,
        allowed_prefixes={"visibility": visibility_prefix},
        name="INVALID closure visibility members",
    )
    if any(
        not item["blob_name"].startswith(f"{transaction['scores_prefix']}/")
        for item in scores
    ) or any(
        not item["blob_name"].startswith(f"{visibility_prefix}/")
        for item in visibility
    ):
        raise LockedEvaluationError(
            "INVALID closure attempt membership is outside its producer"
        )
    if isinstance(observed_state_artifacts, (str, bytes)) or not isinstance(
        observed_state_artifacts, Sequence
    ):
        raise LockedEvaluationError(
            "INVALID closure state artifacts must be a sequence"
        )
    allowed_state_artifacts = {
        f"{transaction['state_prefix']}/{SCORING_TRANSACTION_FILENAME}",
        f"{transaction['state_prefix']}/{SCORING_ATTESTATION_FILENAME}",
    }
    state_artifacts: list[dict[str, Any]] = []
    for index, item in enumerate(observed_state_artifacts):
        _require_exact_fields(
            item,
            _ATTEMPT_MEMBER_FIELDS,
            f"INVALID closure state artifacts[{index}]",
        )
        blob_name = normalize_blob_prefix(item["blob_name"])
        if blob_name not in allowed_state_artifacts:
            raise LockedEvaluationError(
                "INVALID closure contains an unregistered state artifact"
            )
        state_artifacts.append(
            {
                "blob_name": blob_name,
                "size": _require_int(
                    item["size"],
                    f"INVALID closure state artifacts[{index}] size",
                    minimum=0,
                ),
                "sha256": _require_sha256(
                    item["sha256"],
                    f"INVALID closure state artifacts[{index}] SHA-256",
                ),
                "etag": _require_string(
                    item["etag"],
                    f"INVALID closure state artifacts[{index}] ETag",
                    maximum=2048,
                ),
            }
        )
    state_artifacts.sort(key=lambda item: item["blob_name"])
    if len(state_artifacts) != len(
        {item["blob_name"] for item in state_artifacts}
    ):
        raise LockedEvaluationError(
            "INVALID closure repeats a state artifact"
        )
    _require_enum(
        failure_class,
        INVALID_CLOSURE_FAILURE_CLASSES,
        "INVALID closure failure class",
    )
    return {
        "schema_version": INVALID_CLOSURE_SCHEMA_VERSION,
        "authorization_id": authorization,
        "registered_parent_prefix": parent,
        "state_prefix": transaction["state_prefix"],
        "labels_read_receipt_sha256": state_receipt_sha256(
            labels_read_receipt
        ),
        "labels_open_transaction_sha256": sha256_bytes(
            canonical_json_bytes(dict(transaction))
        ),
        "prediction_manifest_sha256": transaction[
            "prediction_manifest_sha256"
        ],
        "prediction_seal_sha256": transaction["prediction_seal_sha256"],
        "prediction_request_manifest_sha256": transaction[
            "prediction_request_manifest_sha256"
        ],
        "prediction_retry_kind": checked_prediction_retry,
        "prediction_execution_id": checked_prediction_execution,
        "prediction_actor": _require_string(
            prediction_actor, "INVALID closure prediction actor", maximum=512
        ),
        "predictions_prefix": checked_predictions_prefix,
        "scores_prefix": transaction["scores_prefix"],
        "visibility_prefix": visibility_prefix,
        "scoring_retry_kind": transaction["scoring_retry_kind"],
        "scoring_execution_id": transaction["execution_id"],
        "scoring_actor": transaction["actor"],
        "retry_receipt_sha256": transaction["retry_receipt_sha256"],
        "failure_class": failure_class,
        "observed_score_members": scores,
        "observed_score_membership_sha256": attempt_membership_sha256(
            scores
        ),
        "observed_visibility_members": visibility,
        "observed_visibility_membership_sha256": attempt_membership_sha256(
            visibility
        ),
        "observed_state_artifacts": state_artifacts,
        "observed_state_artifacts_sha256": attempt_membership_sha256(
            state_artifacts
        ),
        "score_artifact_complete": False,
        "score_manifest_accepted": False,
        "metrics_accepted": False,
        "decision_accepted": False,
        "result_status": "INVALID",
        "formal_evaluation_ordinal": 1,
        "labels_reread_allowed": False,
        "scoring_retry_allowed": False,
        "holdout_spent": True,
        "holdout_retired": True,
        "created_utc": max_canonical_utc(
            transaction["created_utc"],
            labels_read_receipt["timestamp_utc"],
        ),
        "overwrite": False,
    }


def validate_invalid_closure_manifest(
    record: Mapping[str, Any],
    *,
    labels_open_transaction: Mapping[str, Any],
    labels_read_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    _require_exact_fields(
        record, _INVALID_CLOSURE_FIELDS, "INVALID closure manifest"
    )
    if record["schema_version"] != INVALID_CLOSURE_SCHEMA_VERSION:
        raise LockedEvaluationError("INVALID closure manifest schema is invalid")
    try:
        rebuilt = build_invalid_closure_manifest(
            labels_open_transaction,
            labels_read_receipt,
            prediction_retry_kind=record["prediction_retry_kind"],
            prediction_execution_id=record["prediction_execution_id"],
            prediction_actor=record["prediction_actor"],
            predictions_prefix=record["predictions_prefix"],
            observed_score_members=record["observed_score_members"],
            observed_visibility_members=record[
                "observed_visibility_members"
            ],
            observed_state_artifacts=record["observed_state_artifacts"],
            failure_class=record["failure_class"],
        )
    except (KeyError, TypeError, LockedEvaluationError):
        raise LockedEvaluationError(
            "INVALID closure manifest bindings are invalid"
        ) from None
    if not exact_json_equal(dict(record), rebuilt):
        raise LockedEvaluationError(
            "INVALID closure manifest differs from immutable failure evidence"
        )
    return rebuilt


_SPENT_INCOMPLETE_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "state_prefix",
        "prediction_prefix",
        "visibility_prefix",
        "retry_kind",
        "retry_receipt_blob",
        "retry_receipt_sha256",
        "current_state",
        "current_receipt_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "inputs_manifest_sha256",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "observed_prediction_members",
        "reason_code",
        "detail",
        "holdout_spent",
        "holdout_retired",
        "parser_rerun_allowed",
        "scientific_retry_allowed",
        "actor",
        "execution_id",
        "created_utc",
        "overwrite",
    }
)


def build_spent_incomplete_record(
    input_receipt: Mapping[str, Any],
    *,
    state_prefix: str,
    authorization_manifest_sha256: str,
    observed_prediction_members: Sequence[str],
    actor: str,
    execution_id: str,
    created_utc: str,
    prediction_prefix: str | None = None,
    visibility_prefix: str | None = None,
    retry_kind: str = "none",
    retry_receipt_sha256: str | None = None,
) -> dict[str, Any]:
    checked = validate_state_receipt(input_receipt, name="INPUTS_READ receipt")
    if checked["state"] != "INPUTS_READ" or input_receipt["retry_kind"] != "none":
        raise LockedEvaluationError(
            "spent-incomplete record requires the primary INPUTS_READ receipt"
        )
    parent = input_receipt["registered_parent_prefix"]
    authorization = input_receipt["authorization_id"]
    prefix = validate_exact_evaluation_prefix(
        state_prefix, parent, authorization, "state"
    )
    checked_execution_id = _require_string(
        execution_id, "spent-incomplete execution_id"
    )
    checked_actor = _require_string(actor, "spent-incomplete actor")
    if (
        input_receipt["execution_id"] != checked_execution_id
        or input_receipt["actor"] != checked_actor
    ):
        raise LockedEvaluationError(
            "spent-incomplete attempt identity differs from INPUTS_READ"
        )
    attempt_prefixes = evaluation_attempt_prefixes(
        parent,
        authorization,
        "P",
        retry_kind,
        checked_execution_id,
    )
    checked_prediction_prefix = validate_exact_attempt_prefix(
        (
            attempt_prefixes["predictions"]
            if prediction_prefix is None
            else prediction_prefix
        ),
        parent,
        authorization,
        "predictions",
        "P",
        retry_kind,
        checked_execution_id,
    )
    checked_visibility_prefix = validate_exact_attempt_prefix(
        (
            attempt_prefixes["visibility"]
            if visibility_prefix is None
            else visibility_prefix
        ),
        parent,
        authorization,
        "visibility",
        "P",
        retry_kind,
        checked_execution_id,
    )
    if retry_kind == "none":
        if retry_receipt_sha256 is not None:
            raise LockedEvaluationError(
                "primary spent-incomplete record cannot bind a retry receipt"
            )
        retry_receipt_blob = None
        checked_retry_receipt_sha256 = None
    else:
        checked_retry_receipt_sha256 = _require_sha256(
            retry_receipt_sha256, "spent-incomplete retry receipt SHA-256"
        )
        if (
            retry_kind != "infrastructure_pre_input"
            or input_receipt["previous_receipt_sha256"]
            != checked_retry_receipt_sha256
        ):
            raise LockedEvaluationError(
                "spent-incomplete retry predecessor binding is invalid"
            )
        retry_receipt_blob = (
            f"{prefix}/{STATE_RETRY_RECEIPT_FILENAMES[retry_kind]}"
        )
    observed = [normalize_blob_prefix(item) for item in observed_prediction_members]
    if (
        observed != sorted(set(observed))
        or any(
            not item.startswith(f"{checked_prediction_prefix}/")
            for item in observed
        )
    ):
        raise LockedEvaluationError(
            "spent-incomplete prediction metadata membership is invalid"
        )
    return {
        "schema_version": SPENT_INCOMPLETE_SCHEMA_VERSION,
        "authorization_id": authorization,
        "registered_parent_prefix": parent,
        "state_prefix": prefix,
        "prediction_prefix": checked_prediction_prefix,
        "visibility_prefix": checked_visibility_prefix,
        "retry_kind": retry_kind,
        "retry_receipt_blob": retry_receipt_blob,
        "retry_receipt_sha256": checked_retry_receipt_sha256,
        "current_state": "INPUTS_READ",
        "current_receipt_sha256": state_receipt_sha256(input_receipt),
        "authorization_lock_sha256": input_receipt[
            "authorization_lock_sha256"
        ],
        "authorization_manifest_sha256": _require_sha256(
            authorization_manifest_sha256, "authorization manifest SHA-256"
        ),
        "inputs_manifest_sha256": input_receipt["artifact_manifest_hashes"][
            "inputs_manifest"
        ],
        "implementation_commit": input_receipt["implementation_commit"],
        "image_digest": input_receipt["image_digest"],
        "config_sha256": input_receipt["config_sha256"],
        "observed_prediction_members": observed,
        "reason_code": "post_inputs_read_nonretryable_failure",
        "detail": "redacted",
        "holdout_spent": True,
        "holdout_retired": False,
        "parser_rerun_allowed": False,
        "scientific_retry_allowed": False,
        "actor": checked_actor,
        "execution_id": checked_execution_id,
        "created_utc": _require_utc(
            created_utc, "spent-incomplete created_utc"
        ),
        "overwrite": False,
    }


def validate_spent_incomplete_record(
    record: Mapping[str, Any],
    *,
    input_receipt: Mapping[str, Any],
    state_prefix: str,
    authorization_manifest_sha256: str,
) -> dict[str, Any]:
    _require_exact_fields(
        record, _SPENT_INCOMPLETE_FIELDS, "spent-incomplete record"
    )
    if record["schema_version"] != SPENT_INCOMPLETE_SCHEMA_VERSION:
        raise LockedEvaluationError("spent-incomplete schema is invalid")
    try:
        rebuilt = build_spent_incomplete_record(
            input_receipt,
            state_prefix=state_prefix,
            authorization_manifest_sha256=authorization_manifest_sha256,
            observed_prediction_members=record["observed_prediction_members"],
            actor=record["actor"],
            execution_id=record["execution_id"],
            created_utc=record["created_utc"],
            prediction_prefix=record["prediction_prefix"],
            visibility_prefix=record["visibility_prefix"],
            retry_kind=record["retry_kind"],
            retry_receipt_sha256=record["retry_receipt_sha256"],
        )
    except (KeyError, TypeError, LockedEvaluationError):
        raise LockedEvaluationError(
            "spent-incomplete immutable bindings are invalid"
        ) from None
    if not exact_json_equal(dict(record), rebuilt):
        raise LockedEvaluationError(
            "spent-incomplete record differs from the spent state"
        )
    assert_label_blind_payload(record)
    return rebuilt


def validate_state_receipt(
    receipt: Mapping[str, Any], *, name: str = "state receipt"
) -> dict[str, Any]:
    try:
        checked = _load_frozen_validation().validate_state_receipt(
            receipt, name=name
        )
    except Exception:
        raise LockedEvaluationError("state receipt schema/invariants are invalid") from None
    return {
        **checked,
        "state_index": HOLDOUT_STATE_SEQUENCE.index(checked["state"]),
    }


def state_receipt_sha256(receipt: Mapping[str, Any]) -> str:
    validate_state_receipt(receipt)
    return sha256_bytes(canonical_json_bytes(dict(receipt)))


def validate_implementation_manifest(data: bytes) -> dict[str, str]:
    try:
        return _load_frozen_validation().validate_implementation_manifest(data)
    except Exception:
        raise LockedEvaluationError("implementation manifest is invalid") from None


def validate_authorization_lock(record: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return _load_frozen_validation().validate_authorization_lock(record)
    except Exception:
        raise LockedEvaluationError("authorization lock is invalid") from None


def authorization_lock_sha256(record: Mapping[str, Any]) -> str:
    validate_authorization_lock(record)
    return sha256_bytes(canonical_json_bytes(dict(record)))


def authorization_lock_blob_name(record: Mapping[str, Any]) -> str:
    checked = validate_authorization_lock(record)
    return f"{AUTHORIZATION_LOCK_BLOB_PREFIX}/{checked['holdout_id']}.json"


def derive_holdout_id(parent_prefix: str, locked_manifest_sha256: str) -> str:
    try:
        return _load_frozen_validation().derive_holdout_id(
            parent_prefix, locked_manifest_sha256
        )
    except Exception:
        raise LockedEvaluationError("holdout identity binding is invalid") from None


_AUTHORIZATION_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "state_prefix",
        "intended_state",
        "prior_receipt_sha256",
        "authorization_lock_blob",
        "authorization_lock_sha256",
        "implementation_manifest_blob",
        "implementation_manifest_sha256",
        "runtime_config_blob",
        "runtime_config_sha256",
        "azure_destination_sha256",
        "source_bindings_sha256",
        "helper_snapshot_set_sha256",
        "image_binding_sha256",
        "locked_manifest_sha256",
        "locked_input_reservation_blob",
        "locked_input_reservation_sha256",
        "locked_input_private_nonce_sha256",
        "locked_input_reservation_etag",
        "locked_input_manifest_blob",
        "locked_input_manifest_sha256",
        "locked_input_manifest_etag",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "actor",
        "created_utc",
        "overwrite",
    }
)


def build_authorization_manifest(
    implementation_receipt: Mapping[str, Any],
    authorization_lock: Mapping[str, Any],
    implementation_manifest_bytes: bytes,
    runtime_config_bytes: bytes,
    *,
    locked_input_source_binding: Mapping[str, Any],
    state_prefix: str,
    actor: str,
    created_utc: str,
) -> dict[str, Any]:
    checked_receipt = validate_state_receipt(
        implementation_receipt, name="IMPLEMENTATION_FROZEN receipt"
    )
    if checked_receipt["state"] != "IMPLEMENTATION_FROZEN":
        raise LockedEvaluationError(
            "authorization manifest requires IMPLEMENTATION_FROZEN"
        )
    lock = validate_authorization_lock(authorization_lock)
    implementation = validate_implementation_manifest(implementation_manifest_bytes)
    parent = implementation_receipt["registered_parent_prefix"]
    authorization = implementation_receipt["authorization_id"]
    prefix = validate_exact_evaluation_prefix(
        state_prefix, parent, authorization, "state"
    )
    runtime = validate_runtime_configuration(
        runtime_config_bytes,
        expected_sha256=implementation_receipt["config_sha256"],
        source_commit=implementation_receipt["implementation_commit"],
        parent_prefix=parent,
        authorization_id=authorization,
    )
    implementation_sha256 = sha256_bytes(implementation_manifest_bytes)
    lock_sha256 = authorization_lock_sha256(authorization_lock)
    _require_exact_fields(
        locked_input_source_binding,
        _LOCKED_INPUT_SOURCE_BINDING_FIELDS,
        "authorization locked-input source binding",
    )
    source_binding = {
        "locked_input_reservation_blob": normalize_blob_prefix(
            locked_input_source_binding["locked_input_reservation_blob"]
        ),
        "locked_input_reservation_sha256": _require_sha256(
            locked_input_source_binding["locked_input_reservation_sha256"],
            "authorization locked-input reservation SHA-256",
        ),
        "locked_input_private_nonce_sha256": _require_sha256(
            locked_input_source_binding["locked_input_private_nonce_sha256"],
            "authorization locked-input private nonce SHA-256",
        ),
        "locked_input_reservation_etag": _require_string(
            locked_input_source_binding["locked_input_reservation_etag"],
            "authorization locked-input reservation ETag",
        ),
        "locked_input_manifest_blob": normalize_blob_prefix(
            locked_input_source_binding["locked_input_manifest_blob"]
        ),
        "locked_input_manifest_sha256": _require_sha256(
            locked_input_source_binding["locked_input_manifest_sha256"],
            "authorization locked-input manifest SHA-256",
        ),
        "locked_input_manifest_etag": _require_string(
            locked_input_source_binding["locked_input_manifest_etag"],
            "authorization locked-input manifest ETag",
        ),
        "locked_manifest_sha256": _require_sha256(
            locked_input_source_binding["locked_manifest_sha256"],
            "authorization locked overall manifest SHA-256",
        ),
    }
    if (
        lock["authorization_id"] != authorization
        or lock["registered_parent_prefix"] != parent
        or lock["locked_manifest_sha256"]
        != implementation_receipt["artifact_manifest_hashes"]["locked_manifest"]
        or lock["implementation_commit"]
        != implementation_receipt["implementation_commit"]
        or lock["image_digest"] != implementation_receipt["image_digest"]
        or lock["config_sha256"] != implementation_receipt["config_sha256"]
        or lock["implementation_manifest_sha256"] != implementation_sha256
        or implementation_receipt["authorization_lock_sha256"] != lock_sha256
        or implementation_receipt["artifact_manifest_hashes"][
            "implementation_manifest"
        ]
        != implementation_sha256
        or implementation["implementation_commit"] != runtime["source_commit"]
        or implementation["image_digest"] != implementation_receipt["image_digest"]
        or implementation["config_sha256"] != sha256_bytes(runtime_config_bytes)
        or source_binding["locked_input_reservation_blob"]
        != f"{parent}/locked-inputs/.locked_inputs_reservation.json"
        or source_binding["locked_input_manifest_blob"]
        != f"{parent}/locked-inputs/locked_inputs_manifest.json"
        or source_binding["locked_input_manifest_sha256"]
        != implementation_receipt["artifact_manifest_hashes"][
            "locked_inputs_manifest"
        ]
        or source_binding["locked_manifest_sha256"]
        != lock["locked_manifest_sha256"]
    ):
        raise LockedEvaluationError(
            "authorization manifest inputs do not match the global lock"
        )
    return {
        "schema_version": AUTHORIZATION_MANIFEST_SCHEMA_VERSION,
        "authorization_id": authorization,
        "registered_parent_prefix": parent,
        "state_prefix": prefix,
        "intended_state": "UNSEAL_AUTHORIZED",
        "prior_receipt_sha256": state_receipt_sha256(implementation_receipt),
        "authorization_lock_blob": authorization_lock_blob_name(authorization_lock),
        "authorization_lock_sha256": lock_sha256,
        "implementation_manifest_blob": (
            f"{prefix}/{IMPLEMENTATION_MANIFEST_FILENAME}"
        ),
        "implementation_manifest_sha256": implementation_sha256,
        "runtime_config_blob": f"{prefix}/{RUNTIME_CONFIG_FILENAME}",
        "runtime_config_sha256": sha256_bytes(runtime_config_bytes),
        "azure_destination_sha256": runtime["azure_destination_sha256"],
        "source_bindings_sha256": sha256_bytes(
            canonical_json_bytes(runtime["source_bindings"])
        ),
        "helper_snapshot_set_sha256": runtime[
            "helper_snapshot_set_sha256"
        ],
        "image_binding_sha256": runtime["image_binding_sha256"],
        "locked_manifest_sha256": lock["locked_manifest_sha256"],
        "locked_input_reservation_blob": source_binding[
            "locked_input_reservation_blob"
        ],
        "locked_input_reservation_sha256": source_binding[
            "locked_input_reservation_sha256"
        ],
        "locked_input_private_nonce_sha256": source_binding[
            "locked_input_private_nonce_sha256"
        ],
        "locked_input_reservation_etag": source_binding[
            "locked_input_reservation_etag"
        ],
        "locked_input_manifest_blob": source_binding["locked_input_manifest_blob"],
        "locked_input_manifest_sha256": source_binding[
            "locked_input_manifest_sha256"
        ],
        "locked_input_manifest_etag": source_binding[
            "locked_input_manifest_etag"
        ],
        "implementation_commit": implementation["implementation_commit"],
        "image_digest": implementation["image_digest"],
        "config_sha256": implementation["config_sha256"],
        "actor": _require_string(actor, "authorization manifest actor"),
        "created_utc": _require_utc(
            created_utc, "authorization manifest created_utc"
        ),
        "overwrite": False,
    }


def validate_authorization_manifest(
    data: bytes,
    *,
    implementation_receipt: Mapping[str, Any],
    authorization_lock: Mapping[str, Any],
    implementation_manifest_bytes: bytes,
    runtime_config_bytes: bytes,
    state_prefix: str,
) -> dict[str, Any]:
    record = parse_json_strict(data, AUTHORIZATION_MANIFEST_FILENAME)
    _require_exact_fields(
        record, _AUTHORIZATION_MANIFEST_FIELDS, "authorization manifest"
    )
    if record["schema_version"] != AUTHORIZATION_MANIFEST_SCHEMA_VERSION:
        raise LockedEvaluationError("authorization manifest schema is invalid")
    try:
        rebuilt = build_authorization_manifest(
            implementation_receipt,
            authorization_lock,
            implementation_manifest_bytes,
            runtime_config_bytes,
            locked_input_source_binding={
                field: record[field]
                for field in _LOCKED_INPUT_SOURCE_BINDING_FIELDS
            },
            state_prefix=state_prefix,
            actor=record["actor"],
            created_utc=record["created_utc"],
        )
    except (KeyError, TypeError, LockedEvaluationError):
        raise LockedEvaluationError(
            "authorization manifest immutable bindings are invalid"
        ) from None
    if not exact_json_equal(dict(record), rebuilt):
        raise LockedEvaluationError(
            "authorization manifest differs from the real lock/config artifacts"
        )
    return record


def build_sealed_state_receipt(
    *,
    authorization_id: str,
    parent_prefix: str,
    locked_manifest_sha256: str,
    timestamp_utc: str,
    execution_id: str,
    actor: str,
    visibility: Sequence[str],
) -> dict[str, Any]:
    del (
        authorization_id,
        parent_prefix,
        locked_manifest_sha256,
        timestamp_utc,
        execution_id,
        actor,
        visibility,
    )
    raise LockedEvaluationError(
        "SEALED must preserve the full DRAFT_PROTOCOL predecessor chain"
    )


def build_next_state_receipt(
    previous: Mapping[str, Any],
    *,
    state: str,
    artifact_manifest_sha256: str,
    timestamp_utc: str,
    execution_id: str,
    actor: str,
    visibility: Sequence[str],
    outcome: str | None = None,
    implementation_commit: str | None = None,
    image_digest: str | None = None,
    config_sha256: str | None = None,
    authorization_lock_sha256: str | None = None,
    authorization_lock: Mapping[str, Any] | None = None,
    implementation_manifest_bytes: bytes | None = None,
) -> dict[str, Any]:
    checked_previous = validate_state_receipt(previous, name="previous receipt")
    expected_index = checked_previous["state_index"] + 1
    if expected_index >= len(HOLDOUT_STATE_SEQUENCE) or state != HOLDOUT_STATE_SEQUENCE[
        expected_index
    ]:
        raise LockedEvaluationError("state transition does not advance exactly once")
    manifests = dict(previous["artifact_manifest_hashes"])
    additions = STATE_AUTHORIZED_ARTIFACT_BINDINGS[state]
    if len(additions) != 1:
        raise LockedEvaluationError(
            "state requires an explicit exact artifact-binding mapping"
        )
    manifests[next(iter(additions))] = _require_sha256(
        artifact_manifest_sha256, "state artifact manifest SHA-256"
    )
    if state == "IMPLEMENTATION_FROZEN":
        implementation_binding = {
            "implementation_commit": _require_commit(
                implementation_commit, "implementation commit"
            ),
            "image_digest": _require_image_digest(image_digest, "image digest"),
            "config_sha256": _require_sha256(config_sha256, "config SHA-256"),
            "authorization_lock_sha256": _require_sha256(
                authorization_lock_sha256, "authorization lock SHA-256"
            ),
        }
    else:
        if any(
            item is not None
            for item in (
                implementation_commit,
                image_digest,
                config_sha256,
                authorization_lock_sha256,
            )
        ):
            raise LockedEvaluationError(
                "implementation bindings may be introduced only once"
            )
        implementation_binding = {
            "implementation_commit": previous["implementation_commit"],
            "image_digest": previous["image_digest"],
            "config_sha256": previous["config_sha256"],
            "authorization_lock_sha256": previous[
                "authorization_lock_sha256"
            ],
        }
    receipt = {
        "schema_version": STATE_RECEIPT_SCHEMA_VERSION,
        "authorization_id": previous["authorization_id"],
        "state": state,
        "previous_state": previous["state"],
        "previous_receipt_sha256": state_receipt_sha256(previous),
        "timestamp_utc": _require_utc(timestamp_utc, "state timestamp"),
        "execution_id": _require_string(execution_id, "execution_id"),
        "actor": _require_string(actor, "actor"),
        "visibility": sorted(
            {
                _require_string(item, "visibility item")
                for item in visibility
            }
        ),
        "registered_parent_prefix": previous["registered_parent_prefix"],
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": FROZEN_PROTOCOL_BUNDLE_SHA256,
        "acceptance_gates_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
        **implementation_binding,
        "artifact_manifest_hashes": manifests,
        "retry_kind": "none",
        "outcome": outcome if state == "CLOSED" else None,
        "holdout_spent": expected_index
        >= HOLDOUT_STATE_SEQUENCE.index("INPUTS_READ"),
        "holdout_retired": state == "CLOSED",
    }
    validate_state_transition(
        previous,
        receipt,
        authorization_lock=authorization_lock,
        implementation_manifest_bytes=implementation_manifest_bytes,
    )
    return receipt


def build_invalid_closed_state_receipt(
    labels_read_receipt: Mapping[str, Any],
    invalid_closure_manifest: Mapping[str, Any],
    *,
    labels_open_transaction: Mapping[str, Any],
) -> dict[str, Any]:
    previous = validate_state_receipt(
        labels_read_receipt, name="INVALID closure predecessor"
    )
    invalid = validate_invalid_closure_manifest(
        invalid_closure_manifest,
        labels_open_transaction=labels_open_transaction,
        labels_read_receipt=labels_read_receipt,
    )
    if previous["state"] != "LABELS_READ":
        raise LockedEvaluationError(
            "INVALID closure requires a LABELS_READ predecessor"
        )
    invalid_sha256 = sha256_bytes(
        canonical_json_bytes(dict(invalid_closure_manifest))
    )
    manifests = dict(labels_read_receipt["artifact_manifest_hashes"])
    manifests["scores_manifest"] = invalid_sha256
    manifests["closure_manifest"] = invalid_sha256
    receipt = {
        **dict(labels_read_receipt),
        "state": "CLOSED",
        "previous_state": "LABELS_READ",
        "previous_receipt_sha256": state_receipt_sha256(
            labels_read_receipt
        ),
        "timestamp_utc": invalid["created_utc"],
        "execution_id": invalid["scoring_execution_id"],
        "actor": invalid["scoring_actor"],
        "visibility": sorted(
            {
                f"invalid_closure_sha256={invalid_sha256}",
                "result_status=INVALID",
            }
        ),
        "artifact_manifest_hashes": manifests,
        "retry_kind": "none",
        "outcome": "INVALID",
        "holdout_spent": True,
        "holdout_retired": True,
    }
    validate_state_transition(labels_read_receipt, receipt)
    return receipt


def _validate_invalid_closed_transition(
    previous: Mapping[str, Any], current: Mapping[str, Any]
) -> None:
    before = validate_state_receipt(
        previous, name="INVALID closure predecessor"
    )
    after = validate_state_receipt(current, name="INVALID CLOSED receipt")
    before_manifests = dict(previous["artifact_manifest_hashes"])
    after_manifests = dict(current["artifact_manifest_hashes"])
    scores_hash = after_manifests.pop("scores_manifest", None)
    closure_hash = after_manifests.pop("closure_manifest", None)
    expected_visibility = sorted(
        {
            f"invalid_closure_sha256={closure_hash}",
            "result_status=INVALID",
        }
    )
    immutable_fields = (
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "protocol_commit",
        "protocol_bundle_sha256",
        "acceptance_gates_sha256",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "authorization_lock_sha256",
    )
    if (
        before["state"] != "LABELS_READ"
        or after["state"] != "CLOSED"
        or current["previous_state"] != "LABELS_READ"
        or current["previous_receipt_sha256"]
        != state_receipt_sha256(previous)
        or current["retry_kind"] != "none"
        or current["outcome"] != "INVALID"
        or current["holdout_spent"] is not True
        or current["holdout_retired"] is not True
        or scores_hash is None
        or scores_hash != closure_hash
        or not exact_json_equal(after_manifests, before_manifests)
        or not exact_json_equal(current["visibility"], expected_visibility)
        or any(
            not exact_json_equal(current[field], previous[field])
            for field in immutable_fields
        )
    ):
        raise LockedEvaluationError("INVALID CLOSED transition is invalid")
    _validate_nondecreasing_state_timestamps([previous, current])


def _is_invalid_closure_receipt(receipt: Mapping[str, Any]) -> bool:
    return (
        receipt.get("state") == "CLOSED"
        and receipt.get("previous_state") == "LABELS_READ"
        and receipt.get("outcome") == "INVALID"
        and receipt.get("retry_kind") == "none"
    )


def _validate_nondecreasing_state_timestamps(
    receipts: Sequence[Mapping[str, Any]],
) -> None:
    by_hash = {
        sha256_bytes(canonical_json_bytes(dict(receipt))): receipt
        for receipt in receipts
    }
    for receipt in receipts:
        current_timestamp = _require_utc(
            receipt.get("timestamp_utc"), "state receipt timestamp"
        )
        previous_hash = receipt.get("previous_receipt_sha256")
        if previous_hash is None:
            continue
        previous = by_hash.get(previous_hash)
        if previous is None:
            continue
        previous_timestamp = _require_utc(
            previous.get("timestamp_utc"), "previous state receipt timestamp"
        )
        if current_timestamp < previous_timestamp:
            raise LockedEvaluationError(
                "state receipt timestamp regresses from its predecessor"
            )


def _validate_closed_verification_retry_transition(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    history: Sequence[Mapping[str, Any]],
) -> None:
    before = validate_state_receipt(
        previous, name="closed verification predecessor"
    )
    after = validate_state_receipt(
        current, name="closed verification retry"
    )
    immutable_fields = (
        "schema_version",
        "authorization_id",
        "state",
        "registered_parent_prefix",
        "protocol_commit",
        "protocol_bundle_sha256",
        "acceptance_gates_sha256",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "authorization_lock_sha256",
        "artifact_manifest_hashes",
        "outcome",
        "holdout_spent",
        "holdout_retired",
    )
    if (
        before["state"] != "CLOSED"
        or previous["retry_kind"] != "none"
        or _is_invalid_closure_receipt(previous)
        or after["state"] != "CLOSED"
        or current["retry_kind"] != "verification_only"
        or current["previous_state"] != "CLOSED"
        or current["previous_receipt_sha256"]
        != state_receipt_sha256(previous)
        or current["execution_id"] == previous["execution_id"]
        or any(
            not exact_json_equal(current[field], previous[field])
            for field in immutable_fields
        )
        or any(
            item.get("retry_kind") == "verification_only"
            for item in history
        )
    ):
        raise LockedEvaluationError(
            "closed verification-only retry transition is invalid"
        )
    _validate_nondecreasing_state_timestamps(
        [*history, previous, current]
    )


def validate_state_transition(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    history: Sequence[Mapping[str, Any]] = (),
    authorization_lock: Mapping[str, Any] | None = None,
    implementation_manifest_bytes: bytes | None = None,
) -> None:
    if (
        previous.get("state") == "LABELS_READ"
        and current.get("state") == "CLOSED"
        and current.get("outcome") == "INVALID"
    ):
        _validate_invalid_closed_transition(previous, current)
        return
    if (
        previous.get("state") == "CLOSED"
        and current.get("retry_kind") == "verification_only"
    ):
        _validate_closed_verification_retry_transition(
            previous, current, history=history
        )
        return
    try:
        _load_frozen_validation().validate_state_transition(
            previous,
            current,
            history=history,
            authorization_lock=authorization_lock,
            implementation_manifest_bytes=implementation_manifest_bytes,
        )
    except Exception:
        raise LockedEvaluationError("state transition is invalid") from None
    _validate_nondecreasing_state_timestamps(
        [*history, previous, current]
    )


def validate_state_receipt_chain(
    receipts: Sequence[Mapping[str, Any]],
    *,
    require_closed: bool = False,
    authorization_lock: Mapping[str, Any] | None = None,
    implementation_manifest_bytes: bytes | None = None,
) -> dict[str, Any]:
    if type(require_closed) is not bool:
        raise LockedEvaluationError("closed-state requirement must be a boolean")
    terminal_retries = [
        item
        for item in receipts
        if item.get("state") == "CLOSED"
        and item.get("retry_kind") == "verification_only"
    ]
    frozen_receipts = list(receipts)
    if terminal_retries:
        if len(terminal_retries) != 1 or receipts[-1] is not terminal_retries[0]:
            raise LockedEvaluationError(
                "closed verification retry must be the unique terminal receipt"
            )
        terminal = terminal_retries[0]
        frozen_receipts = list(receipts[:-1])
        if not frozen_receipts:
            raise LockedEvaluationError("state receipt chain is invalid")
        _validate_closed_verification_retry_transition(
            frozen_receipts[-1],
            terminal,
            history=frozen_receipts[:-1],
        )
    invalid_terminal = (
        frozen_receipts[-1]
        if frozen_receipts
        and _is_invalid_closure_receipt(frozen_receipts[-1])
        else None
    )
    frozen_prefix = (
        frozen_receipts[:-1] if invalid_terminal is not None else frozen_receipts
    )
    try:
        result = _load_frozen_validation().validate_state_receipt_chain(
            frozen_prefix,
            authorization_lock=authorization_lock,
            implementation_manifest_bytes=implementation_manifest_bytes,
        )
    except Exception:
        raise LockedEvaluationError("state receipt chain is invalid") from None
    if invalid_terminal is not None:
        if result["state"] != "LABELS_READ":
            raise LockedEvaluationError(
                "INVALID CLOSED chain does not end at LABELS_READ"
            )
        _validate_invalid_closed_transition(
            frozen_prefix[-1], invalid_terminal
        )
        result = {
            "receipt_count": len(frozen_receipts),
            "state": "CLOSED",
            "holdout_spent": True,
            "holdout_retired": True,
            "chain_sha256": state_receipt_sha256(invalid_terminal),
            "result_status": "INVALID",
        }
    _validate_nondecreasing_state_timestamps(receipts)
    if require_closed and result["state"] != "CLOSED":
        raise LockedEvaluationError("state receipt chain is not CLOSED")
    return result


def validate_state_receipt_graph(
    receipts: Sequence[Mapping[str, Any]],
    *,
    authorization_lock: Mapping[str, Any] | None = None,
    implementation_manifest_bytes: bytes | None = None,
    authorization_manifest_bytes: bytes | None = None,
    runtime_config_bytes: bytes | None = None,
    state_prefix: str | None = None,
) -> dict[str, Any]:
    terminal_retries = [
        item
        for item in receipts
        if item.get("state") == "CLOSED"
        and item.get("retry_kind") == "verification_only"
    ]
    frozen_receipts = list(receipts)
    if terminal_retries:
        if len(terminal_retries) != 1:
            raise LockedEvaluationError(
                "closed verification retry membership is not exact"
            )
        terminal = terminal_retries[0]
        predecessors = [
            item
            for item in receipts
            if state_receipt_sha256(item)
            == terminal["previous_receipt_sha256"]
        ]
        children = [
            item
            for item in receipts
            if item.get("previous_receipt_sha256")
            == state_receipt_sha256(terminal)
        ]
        if len(predecessors) != 1 or children:
            raise LockedEvaluationError(
                "closed verification retry is not terminal"
            )
        frozen_receipts = [
            item for item in receipts if item is not terminal
        ]
        _validate_closed_verification_retry_transition(
            predecessors[0],
            terminal,
            history=[
                item
                for item in frozen_receipts
                if item is not predecessors[0]
            ],
        )
    invalid_terminals = [
        item
        for item in frozen_receipts
        if _is_invalid_closure_receipt(item)
    ]
    invalid_terminal = None
    if invalid_terminals:
        if len(invalid_terminals) != 1:
            raise LockedEvaluationError(
                "INVALID CLOSED receipt membership is not exact"
            )
        invalid_terminal = invalid_terminals[0]
        predecessors = [
            item
            for item in frozen_receipts
            if state_receipt_sha256(item)
            == invalid_terminal["previous_receipt_sha256"]
        ]
        children = [
            item
            for item in frozen_receipts
            if item.get("previous_receipt_sha256")
            == state_receipt_sha256(invalid_terminal)
        ]
        if len(predecessors) != 1 or children:
            raise LockedEvaluationError(
                "INVALID CLOSED receipt is not terminal"
            )
        frozen_receipts = [
            item for item in frozen_receipts if item is not invalid_terminal
        ]
        _validate_invalid_closed_transition(
            predecessors[0], invalid_terminal
        )
    try:
        result = _load_frozen_validation().validate_state_receipt_graph(
            frozen_receipts,
            authorization_lock=authorization_lock,
            implementation_manifest_bytes=implementation_manifest_bytes,
        )
    except Exception:
        raise LockedEvaluationError(
            "state receipt graph is missing, disconnected, reused, or forked"
        ) from None
    if invalid_terminal is not None:
        if result["state"] != "LABELS_READ":
            raise LockedEvaluationError(
                "INVALID CLOSED graph does not terminate LABELS_READ"
            )
        result = {
            "receipt_count": len(receipts),
            "state": "CLOSED",
            "holdout_spent": True,
            "holdout_retired": True,
            "chain_sha256": state_receipt_sha256(invalid_terminal),
            "result_status": "INVALID",
        }
    _validate_nondecreasing_state_timestamps(receipts)
    if result["state"] in HOLDOUT_STATE_SEQUENCE[
        HOLDOUT_STATE_SEQUENCE.index("UNSEAL_AUTHORIZED") :
    ]:
        if (
            authorization_lock is None
            or implementation_manifest_bytes is None
            or authorization_manifest_bytes is None
            or runtime_config_bytes is None
            or state_prefix is None
        ):
            raise LockedEvaluationError(
                "full authorization graph requires the persisted authorization manifest"
            )
        implementation_receipt = next(
            (
                item
                for item in receipts
                if item["state"] == "IMPLEMENTATION_FROZEN"
                and item["retry_kind"] == "none"
            ),
            None,
        )
        unseal_receipt = next(
            (
                item
                for item in receipts
                if item["state"] == "UNSEAL_AUTHORIZED"
                and item["retry_kind"] == "none"
            ),
            None,
        )
        if implementation_receipt is None or unseal_receipt is None:
            raise LockedEvaluationError(
                "authorization graph omits its frozen authorization transition"
            )
        validate_authorization_manifest(
            authorization_manifest_bytes,
            implementation_receipt=implementation_receipt,
            authorization_lock=authorization_lock,
            implementation_manifest_bytes=implementation_manifest_bytes,
            runtime_config_bytes=runtime_config_bytes,
            state_prefix=state_prefix,
        )
        if unseal_receipt["artifact_manifest_hashes"]["authorization_manifest"] != (
            sha256_bytes(authorization_manifest_bytes)
        ):
            raise LockedEvaluationError(
                "UNSEAL_AUTHORIZED does not bind the persisted authorization manifest"
            )
    return result


def abandoned_attempt_retry_visibility(
    record: Mapping[str, Any],
    *,
    expected_blob_name: str | None = None,
    expected_record_sha256: str | None = None,
) -> list[str]:
    """Return the exact nonsecret receipt linkage for an abandoned attempt."""

    checked = validate_abandoned_attempt_record(record)
    blob_name = abandoned_attempt_blob_name(checked)
    record_sha256 = abandoned_attempt_sha256(checked)
    if expected_blob_name is not None:
        validate_exact_abandoned_attempt_blob_name(expected_blob_name, checked)
    if expected_record_sha256 is not None and _require_sha256(
        expected_record_sha256, "expected abandoned attempt SHA-256"
    ) != record_sha256:
        raise LockedEvaluationError("abandoned attempt SHA-256 binding differs")
    binding_sha256 = attempt_binding_sha256(
        checked["prior_stage"],
        checked["current_retry_kind"],
        checked["current_execution_id"],
    )
    return sorted(
        [
            f"abandoned_attempt_blob={blob_name}",
            f"abandoned_attempt_sha256={record_sha256}",
            f"current_attempt_prefix_sha256={binding_sha256}",
        ]
    )


def verification_retry_visibility(
    *,
    parent_prefix: str,
    authorization_id: str,
    execution_id: str,
    prior_score_manifest_sha256: str,
    prior_labels_open_transaction_sha256: str,
    prior_scoring_attestation_sha256: str,
) -> list[str]:
    """Return exact visibility-only retry bindings to already-written bytes."""

    visibility_prefix = derive_attempt_prefix(
        parent_prefix,
        authorization_id,
        "visibility",
        "E",
        "verification_only",
        execution_id,
    )
    score_manifest_sha256 = _require_sha256(
        prior_score_manifest_sha256, "prior score manifest SHA-256"
    )
    labels_open_sha256 = _require_sha256(
        prior_labels_open_transaction_sha256,
        "prior labels-open transaction SHA-256",
    )
    scoring_attestation_sha256 = _require_sha256(
        prior_scoring_attestation_sha256,
        "prior scoring attestation SHA-256",
    )
    return sorted(
        [
            f"current_visibility_attempt_prefix={visibility_prefix}",
            f"prior_labels_open_transaction_sha256={labels_open_sha256}",
            f"prior_score_manifest_sha256={score_manifest_sha256}",
            f"prior_scoring_attestation_sha256={scoring_attestation_sha256}",
        ]
    )


def _retry_provenance_visibility(
    previous: Mapping[str, Any],
    *,
    retry_kind: str,
    execution_id: str,
    actor: str,
    abandoned_attempt_record: Mapping[str, Any] | None,
    abandoned_attempt_blob_name: str | None,
    abandoned_attempt_record_sha256: str | None,
    prior_score_manifest_sha256: str | None,
    prior_labels_open_transaction_sha256: str | None,
    prior_scoring_attestation_sha256: str | None,
) -> list[str]:
    checked_previous = validate_state_receipt(
        previous, name="retry provenance predecessor"
    )
    checked_retry = _require_enum(
        retry_kind,
        tuple(STATE_RETRY_RECEIPT_FILENAMES),
        "retry provenance kind",
    )
    checked_execution = _require_string(
        execution_id, "retry provenance execution_id", maximum=512
    )
    checked_actor = _require_string(
        actor, "retry provenance actor", maximum=512
    )
    verification_values = (
        prior_score_manifest_sha256,
        prior_labels_open_transaction_sha256,
        prior_scoring_attestation_sha256,
    )
    if checked_retry in {
        "infrastructure_pre_input",
        "scorer_infrastructure",
    }:
        if abandoned_attempt_record is None or any(
            value is not None for value in verification_values
        ):
            raise LockedEvaluationError(
                "infrastructure retry requires only an abandoned-attempt binding"
            )
        abandoned = validate_abandoned_attempt_record(
            abandoned_attempt_record
        )
        if (
            abandoned["authorization_id"] != previous["authorization_id"]
            or abandoned["registered_parent_prefix"]
            != previous["registered_parent_prefix"]
            or abandoned["current_retry_kind"] != checked_retry
            or abandoned["current_execution_id"] != checked_execution
            or abandoned["current_actor"] != checked_actor
            or abandoned["prior_state_receipt_sha256"]
            != state_receipt_sha256(previous)
        ):
            raise LockedEvaluationError(
                "abandoned attempt does not bind the retry receipt identity"
            )
        return abandoned_attempt_retry_visibility(
            abandoned,
            expected_blob_name=abandoned_attempt_blob_name,
            expected_record_sha256=abandoned_attempt_record_sha256,
        )
    if (
        abandoned_attempt_record is not None
        or abandoned_attempt_blob_name is not None
        or abandoned_attempt_record_sha256 is not None
        or any(value is None for value in verification_values)
    ):
        raise LockedEvaluationError(
            "verification-only retry requires exactly its prior artifact hashes"
        )
    return verification_retry_visibility(
        parent_prefix=checked_previous["registered_parent_prefix"],
        authorization_id=checked_previous["authorization_id"],
        execution_id=checked_execution,
        prior_score_manifest_sha256=prior_score_manifest_sha256,
        prior_labels_open_transaction_sha256=(
            prior_labels_open_transaction_sha256
        ),
        prior_scoring_attestation_sha256=(
            prior_scoring_attestation_sha256
        ),
    )


def build_retry_state_receipt(
    previous: Mapping[str, Any],
    *,
    retry_kind: str,
    timestamp_utc: str,
    execution_id: str,
    actor: str,
    visibility: Sequence[str],
    history: Sequence[Mapping[str, Any]],
    authorization_lock: Mapping[str, Any] | None = None,
    implementation_manifest_bytes: bytes | None = None,
    abandoned_attempt_record: Mapping[str, Any] | None = None,
    abandoned_attempt_blob_name: str | None = None,
    abandoned_attempt_record_sha256: str | None = None,
    prior_score_manifest_sha256: str | None = None,
    prior_labels_open_transaction_sha256: str | None = None,
    prior_scoring_attestation_sha256: str | None = None,
    require_provenance_binding: bool = False,
) -> dict[str, Any]:
    validate_state_receipt(previous, name="retry predecessor")
    retry_kind = _require_enum(
        retry_kind,
        tuple(STATE_RETRY_RECEIPT_FILENAMES),
        "retry kind",
    )
    if type(require_provenance_binding) is not bool:
        raise LockedEvaluationError(
            "retry provenance requirement must be a boolean"
        )
    provenance_supplied = any(
        value is not None
        for value in (
            abandoned_attempt_record,
            abandoned_attempt_blob_name,
            abandoned_attempt_record_sha256,
            prior_score_manifest_sha256,
            prior_labels_open_transaction_sha256,
            prior_scoring_attestation_sha256,
        )
    )
    supplied_visibility = sorted(
        {_require_string(item, "retry visibility") for item in visibility}
    )
    if require_provenance_binding or provenance_supplied:
        expected_visibility = _retry_provenance_visibility(
            previous,
            retry_kind=retry_kind,
            execution_id=execution_id,
            actor=actor,
            abandoned_attempt_record=abandoned_attempt_record,
            abandoned_attempt_blob_name=abandoned_attempt_blob_name,
            abandoned_attempt_record_sha256=abandoned_attempt_record_sha256,
            prior_score_manifest_sha256=prior_score_manifest_sha256,
            prior_labels_open_transaction_sha256=(
                prior_labels_open_transaction_sha256
            ),
            prior_scoring_attestation_sha256=(
                prior_scoring_attestation_sha256
            ),
        )
        if supplied_visibility and not exact_json_equal(
            supplied_visibility, expected_visibility
        ):
            raise LockedEvaluationError(
                "retry visibility differs from canonical provenance linkage"
            )
        receipt_visibility = expected_visibility
    else:
        receipt_visibility = supplied_visibility
    receipt = {
        **dict(previous),
        "previous_state": previous["state"],
        "previous_receipt_sha256": state_receipt_sha256(previous),
        "timestamp_utc": _require_utc(timestamp_utc, "retry timestamp"),
        "execution_id": _require_string(execution_id, "retry execution_id"),
        "actor": _require_string(actor, "retry actor"),
        "visibility": receipt_visibility,
        "retry_kind": retry_kind,
    }
    validate_state_transition(
        previous,
        receipt,
        history=history,
        authorization_lock=authorization_lock,
        implementation_manifest_bytes=implementation_manifest_bytes,
    )
    if require_provenance_binding or provenance_supplied:
        validate_retry_state_receipt_provenance(
            receipt,
            previous=previous,
            abandoned_attempt_record=abandoned_attempt_record,
            abandoned_attempt_blob_name=abandoned_attempt_blob_name,
            abandoned_attempt_record_sha256=abandoned_attempt_record_sha256,
            prior_score_manifest_sha256=prior_score_manifest_sha256,
            prior_labels_open_transaction_sha256=(
                prior_labels_open_transaction_sha256
            ),
            prior_scoring_attestation_sha256=(
                prior_scoring_attestation_sha256
            ),
        )
    return receipt


def build_provenance_bound_retry_state_receipt(
    previous: Mapping[str, Any],
    *,
    retry_kind: str,
    timestamp_utc: str,
    execution_id: str,
    actor: str,
    history: Sequence[Mapping[str, Any]],
    authorization_lock: Mapping[str, Any] | None = None,
    implementation_manifest_bytes: bytes | None = None,
    abandoned_attempt_record: Mapping[str, Any] | None = None,
    abandoned_attempt_blob_name: str | None = None,
    abandoned_attempt_record_sha256: str | None = None,
    prior_score_manifest_sha256: str | None = None,
    prior_labels_open_transaction_sha256: str | None = None,
    prior_scoring_attestation_sha256: str | None = None,
) -> dict[str, Any]:
    """Build a production retry receipt with mandatory canonical provenance."""

    return build_retry_state_receipt(
        previous,
        retry_kind=retry_kind,
        timestamp_utc=timestamp_utc,
        execution_id=execution_id,
        actor=actor,
        visibility=(),
        history=history,
        authorization_lock=authorization_lock,
        implementation_manifest_bytes=implementation_manifest_bytes,
        abandoned_attempt_record=abandoned_attempt_record,
        abandoned_attempt_blob_name=abandoned_attempt_blob_name,
        abandoned_attempt_record_sha256=abandoned_attempt_record_sha256,
        prior_score_manifest_sha256=prior_score_manifest_sha256,
        prior_labels_open_transaction_sha256=(
            prior_labels_open_transaction_sha256
        ),
        prior_scoring_attestation_sha256=(
            prior_scoring_attestation_sha256
        ),
        require_provenance_binding=True,
    )


def validate_retry_state_receipt_provenance(
    receipt: Mapping[str, Any],
    *,
    previous: Mapping[str, Any],
    abandoned_attempt_record: Mapping[str, Any] | None = None,
    abandoned_attempt_blob_name: str | None = None,
    abandoned_attempt_record_sha256: str | None = None,
    prior_score_manifest_sha256: str | None = None,
    prior_labels_open_transaction_sha256: str | None = None,
    prior_scoring_attestation_sha256: str | None = None,
) -> dict[str, Any]:
    """Require production retry visibility to be the exact canonical binding."""

    checked = validate_state_receipt(receipt, name="bound retry receipt")
    checked_previous = validate_state_receipt(
        previous, name="bound retry predecessor"
    )
    if receipt["retry_kind"] not in STATE_RETRY_RECEIPT_FILENAMES:
        raise LockedEvaluationError("bound retry receipt kind is invalid")
    if (
        receipt["authorization_id"] != previous["authorization_id"]
        or receipt["registered_parent_prefix"]
        != previous["registered_parent_prefix"]
        or receipt["previous_receipt_sha256"]
        != state_receipt_sha256(previous)
        or receipt["previous_state"] != previous["state"]
        or checked["state_index"] != checked_previous["state_index"]
    ):
        raise LockedEvaluationError("bound retry receipt predecessor differs")
    expected_visibility = _retry_provenance_visibility(
        previous,
        retry_kind=receipt["retry_kind"],
        execution_id=receipt["execution_id"],
        actor=receipt["actor"],
        abandoned_attempt_record=abandoned_attempt_record,
        abandoned_attempt_blob_name=abandoned_attempt_blob_name,
        abandoned_attempt_record_sha256=abandoned_attempt_record_sha256,
        prior_score_manifest_sha256=prior_score_manifest_sha256,
        prior_labels_open_transaction_sha256=(
            prior_labels_open_transaction_sha256
        ),
        prior_scoring_attestation_sha256=prior_scoring_attestation_sha256,
    )
    if not exact_json_equal(receipt["visibility"], expected_visibility):
        raise LockedEvaluationError(
            "retry receipt visibility provenance binding is not exact"
        )
    return dict(receipt)


build_strict_retry_state_receipt = build_provenance_bound_retry_state_receipt
build_bound_retry_state_receipt = build_provenance_bound_retry_state_receipt
validate_retry_state_receipt_binding = (
    validate_retry_state_receipt_provenance
)


_CLOSURE_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "outcome",
        "metrics_sha256",
        "decision_sha256",
        "retirement_sha256",
        "scores_manifest_sha256",
        "prediction_seal_sha256",
        "prediction_manifest_sha256",
        "prediction_request_manifest_sha256",
        "locked_manifest_sha256",
        "input_manifest_sha256",
        "locked_input_sha256",
        "labels_manifest_sha256",
        "labels_sha256",
        "labels_open_transaction_sha256",
        "scores_prefix",
        "scoring_retry_kind",
        "scoring_execution_id",
        "scoring_actor",
        "stage_e_visibility_sha256",
        "retry_receipt_sha256",
        "scoring_ledger_sha256",
        "scoring_ledger_size",
        "scoring_ledger_etag",
        "case_universe_sha256",
        "row_count",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "holdout_spent",
        "holdout_retired",
        "created_utc",
    }
)


def validate_closed_outcome(
    closed_receipt: Mapping[str, Any],
    metrics: Mapping[str, Any],
    decision: Mapping[str, Any],
    retirement: Mapping[str, Any],
    closure_manifest: Mapping[str, Any],
) -> None:
    checked = validate_state_receipt(closed_receipt, name="CLOSED receipt")
    validate_decision(metrics, decision)
    validate_retirement_record(decision, retirement)
    _require_exact_fields(
        closure_manifest, _CLOSURE_MANIFEST_FIELDS, "closure manifest"
    )
    rebuilt = build_closure_manifest(
        metrics,
        decision,
        retirement,
        scores_manifest_sha256=closure_manifest["scores_manifest_sha256"],
        created_utc=closure_manifest["created_utc"],
    )
    manifests = closed_receipt["artifact_manifest_hashes"]
    if (
        not exact_json_equal(dict(closure_manifest), rebuilt)
        or checked["state"] != "CLOSED"
        or closed_receipt["authorization_id"] != decision["authorization_id"]
        or closed_receipt["outcome"] != decision["formal_decision"]
        or closed_receipt["implementation_commit"]
        != decision["implementation_commit"]
        or closed_receipt["image_digest"] != decision["image_digest"]
        or closed_receipt["config_sha256"] != decision["config_sha256"]
        or closed_receipt["authorization_lock_sha256"]
        != decision["authorization_lock_sha256"]
        or manifests["authorization_manifest"]
        != decision["authorization_manifest_sha256"]
        or manifests["locked_manifest"] != decision["locked_manifest_sha256"]
        or manifests["predictions_manifest"]
        != decision["prediction_manifest_sha256"]
        or manifests["labels_manifest"] != decision["labels_manifest_sha256"]
        or manifests["scores_manifest"]
        != closure_manifest["scores_manifest_sha256"]
        or manifests["closure_manifest"]
        != sha256_bytes(canonical_json_bytes(dict(closure_manifest)))
    ):
        raise LockedEvaluationError(
            "CLOSED outcome is not derived from persisted metrics/decision/retirement"
        )


def validate_invalid_closed_outcome(
    closed_receipt: Mapping[str, Any],
    invalid_closure_manifest: Mapping[str, Any],
    *,
    labels_open_transaction: Mapping[str, Any],
    labels_read_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    closed = validate_state_receipt(
        closed_receipt, name="INVALID CLOSED receipt"
    )
    invalid = validate_invalid_closure_manifest(
        invalid_closure_manifest,
        labels_open_transaction=labels_open_transaction,
        labels_read_receipt=labels_read_receipt,
    )
    invalid_sha256 = sha256_bytes(
        canonical_json_bytes(dict(invalid_closure_manifest))
    )
    if (
        closed["state"] != "CLOSED"
        or closed_receipt["outcome"] != "INVALID"
        or closed_receipt["previous_receipt_sha256"]
        != invalid["labels_read_receipt_sha256"]
        or closed_receipt["artifact_manifest_hashes"]["scores_manifest"]
        != invalid_sha256
        or closed_receipt["artifact_manifest_hashes"]["closure_manifest"]
        != invalid_sha256
        or closed_receipt["execution_id"]
        != invalid["scoring_execution_id"]
        or closed_receipt["actor"] != invalid["scoring_actor"]
        or any(
            invalid[field] is not False
            for field in (
                "score_artifact_complete",
                "score_manifest_accepted",
                "metrics_accepted",
                "decision_accepted",
                "labels_reread_allowed",
                "scoring_retry_allowed",
            )
        )
    ):
        raise LockedEvaluationError(
            "INVALID CLOSED outcome authorizes result acceptance"
        )
    _validate_invalid_closed_transition(
        labels_read_receipt, closed_receipt
    )
    return invalid


def build_visibility_record(
    *,
    stage: str,
    authorization_id: str,
    parent_prefix: str,
    visibility_prefix: str,
    execution_id: str,
    actor: str,
    created_utc: str,
    retry_kind: str = "none",
) -> dict[str, Any]:
    checked_stage = _require_enum(stage, ("P", "E"), "visibility stage")
    checked_execution_id = _require_string(execution_id, "execution_id")
    artifact_classes = (
        [
            "frozen-legacy-parser",
            "frozen-parser-v2",
            "locked-inputs",
            "prediction-destinations",
            "public-protocol",
            "state-destination",
        ]
        if checked_stage == "P"
        else [
            "frozen-acceptance-gates",
            "locked-reference-labels",
            "score-destination",
            "sealed-predictions",
            "state-destination",
        ]
    )
    return {
        "schema_version": VISIBILITY_SCHEMA_VERSION,
        "stage": checked_stage,
        "authorization_id": validate_authorization_id(authorization_id),
        "registered_parent_prefix": validate_registered_parent_prefix(parent_prefix),
        "visibility_prefix": validate_exact_attempt_prefix(
            visibility_prefix,
            parent_prefix,
            authorization_id,
            "visibility",
            checked_stage,
            retry_kind,
            checked_execution_id,
        ),
        "execution_id": checked_execution_id,
        "actor": _require_string(actor, "actor"),
        "artifact_classes": artifact_classes,
        "same_managed_identity_isolation": "procedural",
        "registered_parent_membership_visibility": "procedural_metadata_only",
        "unselected_payload_bytes_read": False,
        "managed_identity_only": True,
        "public_network": False,
        "storage_key_or_sas": False,
        "azure_files": False,
        "target_model_loaded": False,
        "target_model_downloaded": False,
        "target_model_inference": False,
        "gpu_used": False,
        "created_utc": _require_utc(created_utc, "visibility created_utc"),
    }


def validate_visibility_record(
    record: Mapping[str, Any],
    *,
    expected_stage: str,
    expected_authorization_id: str,
    expected_parent_prefix: str,
    expected_retry_kind: str = "none",
    expected_execution_id: str | None = None,
) -> dict[str, Any]:
    required = {
        "schema_version",
        "stage",
        "authorization_id",
        "registered_parent_prefix",
        "visibility_prefix",
        "execution_id",
        "actor",
        "artifact_classes",
        "same_managed_identity_isolation",
        "registered_parent_membership_visibility",
        "unselected_payload_bytes_read",
        "managed_identity_only",
        "public_network",
        "storage_key_or_sas",
        "azure_files",
        "target_model_loaded",
        "target_model_downloaded",
        "target_model_inference",
        "gpu_used",
        "created_utc",
    }
    _require_exact_fields(record, required, "visibility record")
    if record["schema_version"] != VISIBILITY_SCHEMA_VERSION:
        raise LockedEvaluationError("visibility record schema is invalid")
    rebuilt = build_visibility_record(
        stage=record["stage"],
        authorization_id=record["authorization_id"],
        parent_prefix=record["registered_parent_prefix"],
        visibility_prefix=record["visibility_prefix"],
        execution_id=record["execution_id"],
        actor=record["actor"],
        created_utc=record["created_utc"],
        retry_kind=expected_retry_kind,
    )
    if (
        not exact_json_equal(dict(record), rebuilt)
        or record["stage"] != expected_stage
        or record["authorization_id"]
        != validate_authorization_id(expected_authorization_id)
        or record["registered_parent_prefix"]
        != validate_registered_parent_prefix(expected_parent_prefix)
        or (
            expected_execution_id is not None
            and record["execution_id"]
            != _require_string(
                expected_execution_id, "expected visibility execution_id"
            )
        )
    ):
        raise LockedEvaluationError("visibility record binding mismatch")
    return rebuilt


def _property_value(properties: Any, *names: str) -> Any:
    for name in names:
        if isinstance(properties, Mapping) and name in properties:
            return properties[name]
        value = getattr(properties, name, None)
        if value is not None:
            return value
    return None


def validate_managed_identity_configuration(
    account_url: str, environment: Mapping[str, str]
) -> tuple[str, str]:
    normalized_environment = {
        key.upper(): value
        for key, value in environment.items()
        if isinstance(key, str)
    }
    for name in _PROHIBITED_CREDENTIAL_ENV:
        if normalized_environment.get(name):
            raise LockedEvaluationError(f"prohibited key/SAS credential is set: {name}")
    client_id = normalized_environment.get("AZURE_CLIENT_ID")
    if not client_id:
        raise LockedEvaluationError("AZURE_CLIENT_ID is required")
    parsed = urlsplit(_require_string(account_url, "account URL"))
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.port not in {None, 443}
        or not _ACCOUNT_HOST_PATTERN.fullmatch(parsed.hostname or "")
    ):
        raise LockedEvaluationError(
            "account URL must be a credential-free Azure Blob HTTPS root"
        )
    return account_url.rstrip("/"), client_id


def validate_private_endpoint_resolution(
    account_url: str, expected_private_ips: str | Sequence[str]
) -> tuple[str, ...]:
    normalized_url, _ = validate_managed_identity_configuration(
        account_url, {"AZURE_CLIENT_ID": "resolution-preflight"}
    )
    hostname = urlsplit(normalized_url).hostname
    supplied = (
        [expected_private_ips]
        if isinstance(expected_private_ips, str)
        else list(expected_private_ips)
    )
    if not supplied:
        raise LockedEvaluationError("expected private endpoint IP set is empty")
    expected: set[ipaddress.IPv4Address] = set()
    private_ranges = tuple(
        ipaddress.ip_network(value)
        for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    )
    for supplied_ip in supplied:
        try:
            address = ipaddress.ip_address(
                _require_string(supplied_ip, "expected private endpoint IP")
            )
        except ValueError:
            raise LockedEvaluationError(
                "expected private endpoint IP is invalid"
            ) from None
        if (
            address.version != 4
            or not any(address in network for network in private_ranges)
        ):
            raise LockedEvaluationError(
                "expected endpoint must be an RFC1918 private IPv4 address"
            )
        expected.add(address)
    if len(expected) != len(supplied):
        raise LockedEvaluationError("expected private endpoint IP set repeats an IP")
    try:
        answers = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(
                hostname, 443, family=socket.AF_INET, type=socket.SOCK_STREAM
            )
        }
    except (OSError, ValueError):
        raise LockedEvaluationError(
            "execution VNet cannot resolve the configured Blob endpoint"
        ) from None
    if answers != expected:
        raise LockedEvaluationError(
            "execution VNet resolution differs from the configured private endpoint"
        )
    return tuple(sorted(str(address) for address in expected))


def create_blob_service(
    account_url: str, environment: Mapping[str, str] | None = None
) -> Any:
    active = os.environ if environment is None else environment
    normalized_url, client_id = validate_managed_identity_configuration(
        account_url, active
    )
    identity = importlib.import_module("azure.identity")
    blob = importlib.import_module("azure.storage.blob")
    credential = identity.ManagedIdentityCredential(client_id=client_id)
    return blob.BlobServiceClient(
        account_url=normalized_url, credential=credential
    )


def validate_container_name(container: str) -> str:
    if (
        not isinstance(container, str)
        or not _CONTAINER_PATTERN.fullmatch(container)
        or "--" in container
    ):
        raise LockedEvaluationError("container name is invalid")
    return container


def _blob_name(item: Any) -> str:
    value = item.get("name") if isinstance(item, Mapping) else getattr(item, "name", None)
    if (
        not isinstance(value, str)
        or value != value.replace("\r", "")
        or any(ord(character) < 32 for character in value)
    ):
        raise LockedEvaluationError("Blob listing returned an invalid member")
    return value


def list_exact_prefix(service: Any, container: str, prefix: str) -> set[str]:
    checked_container = validate_container_name(container)
    checked_prefix = normalize_blob_prefix(prefix)
    try:
        client = service.get_container_client(checked_container)
        listing = client.list_blobs(name_starts_with=f"{checked_prefix}/")
        names: list[str] = []
        if not hasattr(listing, "by_page"):
            raise LockedEvaluationError("Blob listing does not expose explicit paging")
        continuation_token: str | None = None
        seen_tokens: set[str] = set()
        while True:
            pager = listing.by_page(continuation_token=continuation_token)
            try:
                page = next(iter(pager))
            except StopIteration:
                if continuation_token is not None:
                    raise LockedEvaluationError(
                        "Blob pagination ended before its continuation token"
                    )
                break
            for item in page:
                name = _blob_name(item)
                normalized_name = normalize_blob_prefix(name)
                if (
                    normalized_name != name
                    or not normalized_name.startswith(f"{checked_prefix}/")
                ):
                    raise LockedEvaluationError(
                        "Blob listing returned a member outside the exact prefix"
                    )
                names.append(normalized_name)
            next_token = getattr(pager, "continuation_token", None)
            if next_token is None:
                break
            if (
                not isinstance(next_token, str)
                or not next_token
                or "\r" in next_token
                or "\n" in next_token
                or next_token in seen_tokens
            ):
                raise LockedEvaluationError(
                    "Blob listing continuation token is invalid"
                )
            seen_tokens.add(next_token)
            continuation_token = next_token
        if len(names) != len(set(names)):
            raise LockedEvaluationError("Blob listing repeated a member")
        return set(names)
    except LockedEvaluationError:
        raise
    except Exception as exc:
        raise LockedEvaluationError("cannot verify exact Blob membership") from exc


def _blob_properties(blob: Any, blob_name: str, expected_size: int) -> str:
    try:
        properties = blob.get_blob_properties()
    except Exception as exc:
        raise LockedEvaluationError(
            f"cannot read Blob properties: {blob_name}"
        ) from exc
    size = _property_value(properties, "size", "blob_size")
    etag = _property_value(properties, "etag")
    if type(size) is not int or size != expected_size:
        raise LockedEvaluationError(f"Blob size mismatch: {blob_name}")
    if not isinstance(etag, str) or not etag:
        raise LockedEvaluationError(f"Blob ETag is unavailable: {blob_name}")
    return etag


def upload_blob_once(
    service: Any, container: str, blob_name: str, data: bytes
) -> str:
    validate_container_name(container)
    checked_name = normalize_blob_prefix(blob_name)
    if type(data) is not bytes:
        raise LockedEvaluationError("Blob upload payload must be exact bytes")
    blob = service.get_blob_client(container=container, blob=checked_name)
    try:
        blob.upload_blob(data, overwrite=False)
    except Exception as exc:
        raise LockedEvaluationError(
            f"overwrite-false upload failed: {checked_name}"
        ) from exc
    return _blob_properties(blob, checked_name, len(data))


def download_verified_blob(
    service: Any,
    container: str,
    blob_name: str,
    *,
    expected_sha256: str,
    expected_size: int | None = None,
    expected_etag: str | None = None,
) -> tuple[bytes, str]:
    validate_container_name(container)
    checked_name = normalize_blob_prefix(blob_name)
    expected_hash = _require_sha256(expected_sha256, "expected Blob SHA-256")
    blob = service.get_blob_client(container=container, blob=checked_name)
    try:
        data = blob.download_blob().readall()
    except Exception as exc:
        raise LockedEvaluationError(f"cannot download Blob: {checked_name}") from exc
    if not isinstance(data, bytes):
        data = bytes(data)
    if expected_size is not None and len(data) != expected_size:
        raise LockedEvaluationError(f"downloaded Blob size mismatch: {checked_name}")
    if sha256_bytes(data) != expected_hash:
        raise LockedEvaluationError(f"downloaded Blob hash mismatch: {checked_name}")
    etag = _blob_properties(blob, checked_name, len(data))
    if expected_etag is not None and etag != expected_etag:
        raise LockedEvaluationError(f"downloaded Blob ETag mismatch: {checked_name}")
    return data, etag


def download_stable_blob(
    service: Any, container: str, blob_name: str
) -> tuple[bytes, str]:
    """Read an object twice and bind the second read to the first SHA/ETag."""
    validate_container_name(container)
    checked_name = normalize_blob_prefix(blob_name)
    blob = service.get_blob_client(container=container, blob=checked_name)
    try:
        first = blob.download_blob().readall()
    except Exception:
        raise LockedEvaluationError("cannot download required immutable object") from None
    if not isinstance(first, bytes):
        first = bytes(first)
    etag = _blob_properties(blob, checked_name, len(first))
    second, second_etag = download_verified_blob(
        service,
        container,
        checked_name,
        expected_sha256=sha256_bytes(first),
        expected_size=len(first),
        expected_etag=etag,
    )
    if second != first or second_etag != etag:
        raise LockedEvaluationError("immutable object changed between reads")
    return first, etag


def state_receipt_blob_name(
    state_prefix: str, receipt: Mapping[str, Any]
) -> str:
    checked = validate_state_receipt(receipt)
    if receipt["retry_kind"] == "none":
        filename = STATE_RECEIPT_FILENAMES[checked["state"]]
    else:
        filename = STATE_RETRY_RECEIPT_FILENAMES[receipt["retry_kind"]]
    return f"{normalize_blob_prefix(state_prefix)}/{filename}"


def _authorization_state_members(
    state_prefix: str,
    *,
    final_state: str,
    retry_kinds: Sequence[str] = (),
    labels_transaction: bool = False,
    scoring_transaction: bool = False,
    scoring_attestation: bool = False,
    closure_manifest: bool = False,
    spent_incomplete: bool = False,
    scoring_incomplete: bool = False,
    invalid_closure: bool = False,
) -> set[str]:
    if any(
        type(value) is not bool
        for value in (
            labels_transaction,
            scoring_transaction,
            scoring_attestation,
            closure_manifest,
            spent_incomplete,
            scoring_incomplete,
            invalid_closure,
        )
    ):
        raise LockedEvaluationError(
            "authorization membership controls must be booleans"
        )
    final_index = HOLDOUT_STATE_SEQUENCE.index(final_state)
    prefix = normalize_blob_prefix(state_prefix)
    receipt_states = HOLDOUT_STATE_SEQUENCE[: final_index + 1]
    if invalid_closure:
        if (
            final_state not in {"LABELS_READ", "CLOSED"}
            or not labels_transaction
            or closure_manifest
            or scoring_incomplete
        ):
            raise LockedEvaluationError(
                "INVALID closure membership controls are inconsistent"
            )
        receipt_states = HOLDOUT_STATE_SEQUENCE[
            : HOLDOUT_STATE_SEQUENCE.index("LABELS_READ") + 1
        ]
        if final_state == "CLOSED":
            receipt_states = (*receipt_states, "CLOSED")
    members = {
        f"{prefix}/{STATE_RECEIPT_FILENAMES[state]}"
        for state in receipt_states
    }
    if final_index >= HOLDOUT_STATE_SEQUENCE.index("IMPLEMENTATION_FROZEN"):
        members |= {
            f"{prefix}/{IMPLEMENTATION_MANIFEST_FILENAME}",
            f"{prefix}/{RUNTIME_CONFIG_FILENAME}",
        }
    if final_index >= HOLDOUT_STATE_SEQUENCE.index("UNSEAL_AUTHORIZED"):
        members.add(f"{prefix}/{AUTHORIZATION_MANIFEST_FILENAME}")
    for kind in retry_kinds:
        if kind not in STATE_RETRY_RECEIPT_FILENAMES:
            raise LockedEvaluationError("state membership contains an unknown retry")
        members.add(f"{prefix}/{STATE_RETRY_RECEIPT_FILENAMES[kind]}")
    if labels_transaction:
        members.add(f"{prefix}/{LABELS_OPEN_TRANSACTION_FILENAME}")
    if scoring_transaction:
        if (
            not labels_transaction
            or final_index < HOLDOUT_STATE_SEQUENCE.index("LABELS_READ")
        ):
            raise LockedEvaluationError(
                "scoring transaction requires LABELS_READ and labels transaction"
            )
        members.add(f"{prefix}/{SCORING_TRANSACTION_FILENAME}")
    if scoring_attestation:
        if not scoring_transaction:
            raise LockedEvaluationError(
                "scoring attestation requires its scoring transaction"
            )
        members.add(f"{prefix}/{SCORING_ATTESTATION_FILENAME}")
    if closure_manifest:
        members.add(f"{prefix}/{CLOSURE_MANIFEST_FILENAME}")
    if spent_incomplete:
        if final_index < HOLDOUT_STATE_SEQUENCE.index("INPUTS_READ"):
            raise LockedEvaluationError(
                "spent-incomplete artifact requires a spent input state"
            )
        members.add(f"{prefix}/{SPENT_INCOMPLETE_FILENAME}")
    if scoring_incomplete:
        if not labels_transaction:
            raise LockedEvaluationError(
                "scoring-incomplete evidence requires a labels transaction"
            )
        members.add(f"{prefix}/{SCORING_INCOMPLETE_FILENAME}")
    if invalid_closure:
        members.add(f"{prefix}/{INVALID_CLOSURE_FILENAME}")
    return members


def validate_authorization_membership(
    service: Any,
    container: str,
    *,
    parent_prefix: str,
    authorization_id: str,
    expected: Mapping[str, set[str]],
) -> None:
    prefixes = evaluation_prefixes(parent_prefix, authorization_id)
    if set(expected) != set(prefixes):
        raise LockedEvaluationError("authorization membership leaves are not exact")
    for leaf, prefix in prefixes.items():
        if list_exact_prefix(service, container, prefix) != expected[leaf]:
            raise LockedEvaluationError(
                "authorization-scoped Blob membership is not exact"
            )


def validate_registered_parent_membership(
    service: Any,
    container: str,
    parent_prefix: str,
    expected_members: Iterable[str],
) -> None:
    parent = validate_registered_parent_prefix(parent_prefix)
    expected = {normalize_blob_prefix(item) for item in expected_members}
    if any(not item.startswith(f"{parent}/") for item in expected):
        raise LockedEvaluationError("registered parent member is outside the parent")
    if list_exact_prefix(service, container, parent) != expected:
        raise LockedEvaluationError("registered parent membership is not exact")


def expected_registered_parent_membership(
    parent_prefix: str, authorization_members: Iterable[str]
) -> set[str]:
    parent = validate_registered_parent_prefix(parent_prefix)
    try:
        frozen_members = set(
            _load_frozen_validation().expected_parent_membership(parent)
        )
    except Exception:
        raise LockedEvaluationError(
            "frozen registered parent membership is unavailable"
        ) from None
    dynamic = {normalize_blob_prefix(item) for item in authorization_members}
    if any(not item.startswith(f"{parent}/") for item in dynamic):
        raise LockedEvaluationError(
            "authorization object is outside the registered parent"
        )
    return frozen_members | dynamic


def authenticate_authorization_bundle(
    service: Any,
    container: str,
    *,
    project_root: str | Path,
    parent_prefix: str,
    authorization_id: str,
    state_prefix: str,
    implementation_commit: str,
    image_digest: str,
    config_sha256: str,
    launcher_sha256: str | None = None,
    launcher_git_blob_oid: str | None = None,
    expected_prior_receipt_sha256: str | None = None,
    expected_authorization_lock_sha256: str | None = None,
    expected_authorization_manifest_sha256: str | None = None,
    expected_azure_destination: Mapping[str, Any] | None = None,
    expected_image_binding_sha256: str | None = None,
    expected_helper_snapshot_set_sha256: str | None = None,
    final_state: str = "UNSEAL_AUTHORIZED",
    labels_transaction: bool = False,
    scoring_transaction: bool = False,
    scoring_attestation: bool = False,
    closure_manifest: bool = False,
    spent_incomplete: bool = False,
    scoring_incomplete: bool = False,
    invalid_closure: bool = False,
) -> dict[str, Any]:
    """Authenticate the complete frozen graph and its real lock/config objects."""
    compute_protocol_bundle_sha256(project_root)
    load_acceptance_gates(load_frozen_gate_bytes(project_root))
    parent = validate_registered_parent_prefix(parent_prefix)
    authorization = validate_authorization_id(authorization_id)
    prefix = validate_exact_evaluation_prefix(
        state_prefix, parent, authorization, "state"
    )
    actual_members = list_exact_prefix(service, container, prefix)
    if final_state not in HOLDOUT_STATE_SEQUENCE:
        raise LockedEvaluationError("authorization graph target state is invalid")
    required = _authorization_state_members(
        prefix,
        final_state=final_state,
        labels_transaction=labels_transaction,
        scoring_transaction=scoring_transaction,
        scoring_attestation=scoring_attestation,
        closure_manifest=closure_manifest,
        spent_incomplete=spent_incomplete,
        scoring_incomplete=scoring_incomplete,
        invalid_closure=invalid_closure,
    )
    retry_names = {
        f"{prefix}/{filename}": kind
        for kind, filename in STATE_RETRY_RECEIPT_FILENAMES.items()
    }
    extras = actual_members - required
    retry_members = extras & set(retry_names)
    allowed_retry_kinds = {"infrastructure_pre_input"}
    if HOLDOUT_STATE_SEQUENCE.index(final_state) >= HOLDOUT_STATE_SEQUENCE.index(
        "PREDICTIONS_VERIFIED"
    ):
        allowed_retry_kinds.add("scorer_infrastructure")
    if (
        not invalid_closure
        and HOLDOUT_STATE_SEQUENCE.index(final_state)
        >= HOLDOUT_STATE_SEQUENCE.index(
        "LABELS_READ"
        )
    ):
        allowed_retry_kinds.add("verification_only")
    if (
        actual_members - required - set(retry_names)
        or len({retry_names[item] for item in retry_members})
        != len(retry_members)
        or any(
            retry_names[item] not in allowed_retry_kinds
            for item in retry_members
        )
    ):
        raise LockedEvaluationError(
            "pre-input state membership contains an unexpected object"
        )
    if not required.issubset(actual_members):
        raise LockedEvaluationError("pre-input state graph is incomplete")
    receipts: list[dict[str, Any]] = []
    receipt_states = HOLDOUT_STATE_SEQUENCE[
        : HOLDOUT_STATE_SEQUENCE.index(final_state) + 1
    ]
    if invalid_closure:
        receipt_states = HOLDOUT_STATE_SEQUENCE[
            : HOLDOUT_STATE_SEQUENCE.index("LABELS_READ") + 1
        ]
        if final_state == "CLOSED":
            receipt_states = (*receipt_states, "CLOSED")
    for state in receipt_states:
        blob_name = f"{prefix}/{STATE_RECEIPT_FILENAMES[state]}"
        data, _ = download_stable_blob(service, container, blob_name)
        receipt = parse_json_strict(data, "state receipt")
        validate_state_receipt(receipt)
        if receipt["state"] != state or receipt["retry_kind"] != "none":
            raise LockedEvaluationError("registered state receipt identity mismatch")
        receipts.append(receipt)
    for blob_name in retry_members:
        data, _ = download_stable_blob(service, container, blob_name)
        retry = parse_json_strict(data, "retry receipt")
        validate_state_receipt(retry)
        if retry["retry_kind"] != retry_names[blob_name]:
            raise LockedEvaluationError("retry receipt filename binding mismatch")
        receipts.append(retry)
    implementation_bytes, implementation_etag = download_stable_blob(
        service,
        container,
        f"{prefix}/{IMPLEMENTATION_MANIFEST_FILENAME}",
    )
    implementation = validate_implementation_manifest(implementation_bytes)
    config_bytes, config_etag = download_stable_blob(
        service, container, f"{prefix}/{RUNTIME_CONFIG_FILENAME}"
    )
    config = validate_runtime_configuration(
        config_bytes,
        expected_sha256=config_sha256,
        source_commit=implementation_commit,
        parent_prefix=parent,
        authorization_id=authorization,
        launcher_sha256=launcher_sha256,
        launcher_git_blob_oid=launcher_git_blob_oid,
        expected_azure_destination=expected_azure_destination,
        expected_image_digest=image_digest,
    )
    sealed = next(item for item in receipts if item["state"] == "SEALED")
    expected_holdout_id = derive_holdout_id(
        parent, sealed["artifact_manifest_hashes"]["locked_manifest"]
    )
    lock_blob = f"{AUTHORIZATION_LOCK_BLOB_PREFIX}/{expected_holdout_id}.json"
    lock_bytes, lock_etag = download_stable_blob(
        service, container, lock_blob
    )
    lock_record = parse_json_strict(lock_bytes, "authorization lock")
    lock = validate_authorization_lock(lock_record)
    lock_hash = authorization_lock_sha256(lock_record)
    authorization_manifest_bytes, authorization_manifest_etag = (
        download_stable_blob(
            service,
            container,
            f"{prefix}/{AUTHORIZATION_MANIFEST_FILENAME}",
        )
    )
    graph = validate_state_receipt_graph(
        receipts,
        authorization_lock=lock_record,
        implementation_manifest_bytes=implementation_bytes,
        authorization_manifest_bytes=authorization_manifest_bytes,
        runtime_config_bytes=config_bytes,
        state_prefix=prefix,
    )
    if graph["state"] != final_state:
        raise LockedEvaluationError("authorization graph target state mismatch")
    by_parent = {
        item["previous_receipt_sha256"]: item
        for item in receipts
        if item["previous_receipt_sha256"] is not None
    }
    current = next(
        item for item in receipts if item["previous_receipt_sha256"] is None
    )
    chain = [current]
    while state_receipt_sha256(current) in by_parent:
        current = by_parent[state_receipt_sha256(current)]
        chain.append(current)
    final = chain[-1]
    expected_manifest_hash = sha256_bytes(implementation_bytes)
    authorization_manifest = validate_authorization_manifest(
        authorization_manifest_bytes,
        implementation_receipt=next(
            item
            for item in receipts
            if item["state"] == "IMPLEMENTATION_FROZEN"
            and item["retry_kind"] == "none"
        ),
        authorization_lock=lock_record,
        implementation_manifest_bytes=implementation_bytes,
        runtime_config_bytes=config_bytes,
        state_prefix=prefix,
    )
    authorization_manifest_hash = sha256_bytes(authorization_manifest_bytes)
    spent_record = None
    if spent_incomplete:
        input_receipt = next(
            (
                item
                for item in receipts
                if item["state"] == "INPUTS_READ"
                and item["retry_kind"] == "none"
            ),
            None,
        )
        if input_receipt is None:
            raise LockedEvaluationError(
                "spent-incomplete authorization omits INPUTS_READ"
            )
        spent_bytes, _ = download_stable_blob(
            service,
            container,
            f"{prefix}/{SPENT_INCOMPLETE_FILENAME}",
        )
        spent_record = parse_json_strict(
            spent_bytes, "spent-incomplete record"
        )
        validate_spent_incomplete_record(
            spent_record,
            input_receipt=input_receipt,
            state_prefix=prefix,
            authorization_manifest_sha256=authorization_manifest_hash,
        )
        if spent_record["retry_kind"] == "none":
            if any(
                item["retry_kind"] == "infrastructure_pre_input"
                and state_receipt_sha256(item)
                == input_receipt["previous_receipt_sha256"]
                for item in receipts
            ):
                raise LockedEvaluationError(
                    "spent-incomplete record omits its retry predecessor"
                )
        elif not any(
            item["retry_kind"] == spent_record["retry_kind"]
            and state_receipt_sha256(item)
            == spent_record["retry_receipt_sha256"]
            for item in receipts
        ):
            raise LockedEvaluationError(
                "spent-incomplete retry receipt is not authenticated"
            )
        actual_prediction_members = sorted(
            list_exact_prefix(
                service,
                container,
                spent_record["prediction_prefix"],
            )
        )
        if not exact_json_equal(
            spent_record["observed_prediction_members"],
            actual_prediction_members,
        ):
            raise LockedEvaluationError(
                "spent-incomplete prediction membership changed"
            )
    scoring_incomplete_record = None
    if scoring_incomplete:
        transaction_bytes, _ = download_stable_blob(
            service,
            container,
            f"{prefix}/{LABELS_OPEN_TRANSACTION_FILENAME}",
        )
        labels_transaction_record = parse_json_strict(
            transaction_bytes, "labels-open transaction"
        )
        evidence_bytes, _ = download_stable_blob(
            service,
            container,
            f"{prefix}/{SCORING_INCOMPLETE_FILENAME}",
        )
        scoring_incomplete_record = parse_json_strict(
            evidence_bytes, "scoring-incomplete record"
        )
        validate_scoring_incomplete_record(
            scoring_incomplete_record,
            labels_open_transaction=labels_transaction_record,
        )
        evidence_blob = f"{prefix}/{SCORING_INCOMPLETE_FILENAME}"
        if not exact_json_equal(
            scoring_incomplete_record["observed_state_members"],
            sorted(actual_members - {evidence_blob}),
        ):
            raise LockedEvaluationError(
                "scoring-incomplete state membership changed"
            )
        actual_score_members = list_exact_prefix(
            service,
            container,
            scoring_incomplete_record["scores_prefix"],
        )
        if actual_score_members != {
            item["blob_name"]
            for item in scoring_incomplete_record[
                "observed_score_members"
            ]
        }:
            raise LockedEvaluationError(
                "scoring-incomplete score membership changed"
            )
        for item in scoring_incomplete_record["observed_score_members"]:
            data, etag = download_stable_blob(
                service, container, item["blob_name"]
            )
            if (
                len(data) != item["size"]
                or sha256_bytes(data) != item["sha256"]
                or etag != item["etag"]
            ):
                raise LockedEvaluationError(
                    "scoring-incomplete score member changed"
                )
    invalid_closure_record = None
    if invalid_closure:
        labels_receipt = next(
            (
                item
                for item in receipts
                if item["state"] == "LABELS_READ"
                and item["retry_kind"] == "none"
            ),
            None,
        )
        closed_receipt = next(
            (
                item
                for item in receipts
                if item["state"] == "CLOSED"
                and item["retry_kind"] == "none"
            ),
            None,
        )
        prediction_receipt = next(
            (
                item
                for item in receipts
                if item["state"] == "PREDICTIONS_VERIFIED"
                and item["retry_kind"] == "none"
            ),
            None,
        )
        if labels_receipt is None or prediction_receipt is None or (
            final_state == "CLOSED" and closed_receipt is None
        ):
            raise LockedEvaluationError(
                "INVALID closure omits a required producer receipt"
            )
        labels_transaction_bytes, _ = download_stable_blob(
            service,
            container,
            f"{prefix}/{LABELS_OPEN_TRANSACTION_FILENAME}",
        )
        labels_transaction_record = parse_json_strict(
            labels_transaction_bytes, "INVALID labels-open transaction"
        )
        invalid_bytes, _ = download_stable_blob(
            service,
            container,
            f"{prefix}/{INVALID_CLOSURE_FILENAME}",
        )
        invalid_closure_record = parse_json_strict(
            invalid_bytes, "INVALID closure manifest"
        )
        if closed_receipt is None:
            validate_invalid_closure_manifest(
                invalid_closure_record,
                labels_open_transaction=labels_transaction_record,
                labels_read_receipt=labels_receipt,
            )
        else:
            validate_invalid_closed_outcome(
                closed_receipt,
                invalid_closure_record,
                labels_open_transaction=labels_transaction_record,
                labels_read_receipt=labels_receipt,
            )
        if (
            canonical_json_bytes(labels_transaction_record)
            != labels_transaction_bytes
            or canonical_json_bytes(invalid_closure_record) != invalid_bytes
            or prediction_receipt["execution_id"]
            != invalid_closure_record["prediction_execution_id"]
            or prediction_receipt["actor"]
            != invalid_closure_record["prediction_actor"]
            or prediction_receipt["artifact_manifest_hashes"][
                "predictions_manifest"
            ]
            != invalid_closure_record["prediction_manifest_sha256"]
        ):
            raise LockedEvaluationError(
                "INVALID closure producer binding differs"
            )
        prediction_retries = [
            item
            for item in receipts
            if item["retry_kind"] == "infrastructure_pre_input"
        ]
        expected_prediction_retry = (
            "none"
            if not prediction_retries
            else prediction_retries[0]["retry_kind"]
        )
        if (
            len(prediction_retries) > 1
            or invalid_closure_record["prediction_retry_kind"]
            != expected_prediction_retry
        ):
            raise LockedEvaluationError(
                "INVALID closure prediction retry binding differs"
            )
        for member_field, member_prefix in (
            ("observed_score_members", invalid_closure_record["scores_prefix"]),
            (
                "observed_visibility_members",
                invalid_closure_record["visibility_prefix"],
            ),
        ):
            observed = invalid_closure_record[member_field]
            if list_exact_prefix(
                service, container, member_prefix
            ) != {item["blob_name"] for item in observed}:
                raise LockedEvaluationError(
                    "INVALID closure attempt membership changed"
                )
            for item in observed:
                data, etag = download_stable_blob(
                    service, container, item["blob_name"]
                )
                if (
                    len(data) != item["size"]
                    or sha256_bytes(data) != item["sha256"]
                    or etag != item["etag"]
                ):
                    raise LockedEvaluationError(
                        "INVALID closure attempt member changed"
                    )
        expected_state_artifacts = {
            f"{prefix}/{SCORING_TRANSACTION_FILENAME}"
            if scoring_transaction
            else None,
            f"{prefix}/{SCORING_ATTESTATION_FILENAME}"
            if scoring_attestation
            else None,
        } - {None}
        if expected_state_artifacts != {
            item["blob_name"]
            for item in invalid_closure_record[
                "observed_state_artifacts"
            ]
        }:
            raise LockedEvaluationError(
                "INVALID closure state-artifact membership differs"
            )
        for item in invalid_closure_record["observed_state_artifacts"]:
            data, etag = download_stable_blob(
                service, container, item["blob_name"]
            )
            if (
                len(data) != item["size"]
                or sha256_bytes(data) != item["sha256"]
                or etag != item["etag"]
            ):
                raise LockedEvaluationError(
                    "INVALID closure state artifact changed"
                )
    supplied_authorization_manifest_hash = (
        authorization_manifest_hash
        if expected_authorization_manifest_sha256 is None
        else _require_sha256(
            expected_authorization_manifest_sha256,
            "expected authorization manifest SHA-256",
        )
    )
    supplied_lock_hash = (
        lock_hash
        if expected_authorization_lock_sha256 is None
        else _require_sha256(
            expected_authorization_lock_sha256,
            "expected authorization lock SHA-256",
        )
    )
    supplied_prior_hash = (
        state_receipt_sha256(final)
        if expected_prior_receipt_sha256 is None
        else _require_sha256(
            expected_prior_receipt_sha256, "expected prior receipt SHA-256"
        )
    )
    supplied_image_binding_hash = (
        config["image_binding_sha256"]
        if expected_image_binding_sha256 is None
        else _require_sha256(
            expected_image_binding_sha256,
            "expected image binding SHA-256",
        )
    )
    supplied_helper_snapshot_hash = (
        config["helper_snapshot_set_sha256"]
        if expected_helper_snapshot_set_sha256 is None
        else _require_sha256(
            expected_helper_snapshot_set_sha256,
            "expected helper snapshot-set SHA-256",
        )
    )
    if (
        final["state"] != final_state
        or final["authorization_id"] != authorization
        or final["registered_parent_prefix"] != parent
        or final["implementation_commit"] != implementation_commit
        or final["image_digest"] != image_digest
        or final["config_sha256"] != config_sha256
        or final["authorization_lock_sha256"] != lock_hash
        or state_receipt_sha256(final) != supplied_prior_hash
        or lock_hash != supplied_lock_hash
        or lock["holdout_id"] != expected_holdout_id
        or lock["authorization_id"] != authorization
        or lock["registered_parent_prefix"] != parent
        or lock["locked_manifest_sha256"]
        != sealed["artifact_manifest_hashes"]["locked_manifest"]
        or lock["implementation_commit"] != implementation_commit
        or lock["image_digest"] != image_digest
        or lock["config_sha256"] != config_sha256
        or lock["implementation_manifest_sha256"] != expected_manifest_hash
        or implementation["implementation_commit"] != implementation_commit
        or implementation["image_digest"] != image_digest
        or implementation["config_sha256"] != config_sha256
        or config["azure_destination"]["image"]["digest"] != image_digest
        or authorization_manifest["azure_destination_sha256"]
        != config["azure_destination_sha256"]
        or authorization_manifest["source_bindings_sha256"]
        != sha256_bytes(canonical_json_bytes(config["source_bindings"]))
        or config["image_binding_sha256"] != supplied_image_binding_hash
        or config["helper_snapshot_set_sha256"]
        != supplied_helper_snapshot_hash
        or authorization_manifest["image_binding_sha256"]
        != supplied_image_binding_hash
        or authorization_manifest["helper_snapshot_set_sha256"]
        != supplied_helper_snapshot_hash
        or final["artifact_manifest_hashes"]["authorization_manifest"]
        != authorization_manifest_hash
        or authorization_manifest["authorization_lock_sha256"] != lock_hash
        or authorization_manifest_hash
        != supplied_authorization_manifest_hash
    ):
        raise LockedEvaluationError("authorization bundle immutable bindings mismatch")
    if final_state == "UNSEAL_AUTHORIZED":
        try:
            _load_frozen_validation().assert_holdout_available(
                chain,
                authorization_lock=lock_record,
                implementation_manifest_bytes=implementation_bytes,
            )
        except Exception:
            raise LockedEvaluationError(
                "authorized holdout is unavailable or reused"
            ) from None
    return {
        "receipts": chain,
        "prior_receipt": final,
        "authorization_lock": lock_record,
        "authorization_lock_sha256": lock_hash,
        "authorization_lock_blob": lock_blob,
        "authorization_lock_etag": lock_etag,
        "implementation_manifest": implementation,
        "implementation_manifest_bytes": implementation_bytes,
        "implementation_manifest_sha256": expected_manifest_hash,
        "implementation_manifest_etag": implementation_etag,
        "runtime_config": config,
        "runtime_config_bytes": config_bytes,
        "runtime_config_sha256": sha256_bytes(config_bytes),
        "runtime_config_etag": config_etag,
        "image_binding": config["image_binding"],
        "image_binding_sha256": config["image_binding_sha256"],
        "helper_snapshot_set_sha256": config[
            "helper_snapshot_set_sha256"
        ],
        "authorization_manifest": authorization_manifest,
        "authorization_manifest_bytes": authorization_manifest_bytes,
        "authorization_manifest_sha256": authorization_manifest_hash,
        "authorization_manifest_etag": authorization_manifest_etag,
        "locked_manifest_sha256": lock["locked_manifest_sha256"],
        "holdout_id": expected_holdout_id,
        "retry_kinds": [item["retry_kind"] for item in chain if item["retry_kind"] != "none"],
        "spent_incomplete": spent_incomplete,
        "spent_incomplete_record": spent_record,
        "scoring_incomplete": scoring_incomplete,
        "scoring_incomplete_record": scoring_incomplete_record,
        "invalid_closure": invalid_closure,
        "invalid_closure_record": invalid_closure_record,
        "result_status": (
            final["outcome"] if final["state"] == "CLOSED" else "PENDING"
        ),
        "scoring_transaction": scoring_transaction,
        "scoring_attestation": scoring_attestation,
    }


def verify_uploaded_blob(
    service: Any,
    container: str,
    blob_name: str,
    data: bytes,
    etag: str,
) -> None:
    downloaded, actual_etag = download_verified_blob(
        service,
        container,
        blob_name,
        expected_sha256=sha256_bytes(data),
        expected_size=len(data),
        expected_etag=etag,
    )
    if downloaded != data or actual_etag != etag:
        raise LockedEvaluationError(f"uploaded Blob verification failed: {blob_name}")


def persist_singleton(
    service: Any,
    container: str,
    blob_name: str,
    data: bytes,
) -> dict[str, Any]:
    etag = upload_blob_once(service, container, blob_name, data)
    verify_uploaded_blob(service, container, blob_name, data, etag)
    return {
        "blob_name": normalize_blob_prefix(blob_name),
        "size": len(data),
        "sha256": sha256_bytes(data),
        "etag": etag,
    }


def persist_or_adopt_exact_singleton(
    service: Any,
    container: str,
    blob_name: str,
    data: bytes,
) -> dict[str, Any]:
    """Attempt one create, then authenticate only exact immutable bytes."""

    try:
        persisted = persist_singleton(
            service, container, blob_name, data
        )
        return {**persisted, "adopted": False}
    except LockedEvaluationError as create_error:
        try:
            existing, etag = download_stable_blob(
                service, container, blob_name
            )
        except LockedEvaluationError:
            raise create_error
        if existing != data:
            raise LockedEvaluationError(
                "persisted singleton differs after create ambiguity"
            ) from create_error
        return {
            "blob_name": normalize_blob_prefix(blob_name),
            "size": len(existing),
            "sha256": sha256_bytes(existing),
            "etag": etag,
            "adopted": True,
        }


def persist_state_receipt(
    service: Any,
    container: str,
    state_prefix: str,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    validate_state_receipt(receipt)
    blob_name = state_receipt_blob_name(state_prefix, receipt)
    return persist_singleton(
        service, container, blob_name, canonical_json_bytes(dict(receipt))
    )


def persist_or_adopt_state_receipt(
    service: Any,
    container: str,
    state_prefix: str,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    validate_state_receipt(receipt)
    return persist_or_adopt_exact_singleton(
        service,
        container,
        state_receipt_blob_name(state_prefix, receipt),
        canonical_json_bytes(dict(receipt)),
    )


def persist_or_adopt_invalid_closure(
    service: Any,
    container: str,
    state_prefix: str,
    record: Mapping[str, Any],
    *,
    labels_open_transaction: Mapping[str, Any],
    labels_read_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    validate_invalid_closure_manifest(
        record,
        labels_open_transaction=labels_open_transaction,
        labels_read_receipt=labels_read_receipt,
    )
    return persist_or_adopt_exact_singleton(
        service,
        container,
        f"{normalize_blob_prefix(state_prefix)}/{INVALID_CLOSURE_FILENAME}",
        canonical_json_bytes(dict(record)),
    )


def persist_authorization_manifest(
    service: Any,
    container: str,
    state_prefix: str,
    manifest: Mapping[str, Any],
    *,
    implementation_receipt: Mapping[str, Any],
    authorization_lock: Mapping[str, Any],
    implementation_manifest_bytes: bytes,
    runtime_config_bytes: bytes,
) -> dict[str, Any]:
    data = canonical_json_bytes(dict(manifest))
    validate_authorization_manifest(
        data,
        implementation_receipt=implementation_receipt,
        authorization_lock=authorization_lock,
        implementation_manifest_bytes=implementation_manifest_bytes,
        runtime_config_bytes=runtime_config_bytes,
        state_prefix=state_prefix,
    )
    return persist_singleton(
        service,
        container,
        f"{normalize_blob_prefix(state_prefix)}/{AUTHORIZATION_MANIFEST_FILENAME}",
        data,
    )


def persist_spent_incomplete_record(
    service: Any,
    container: str,
    state_prefix: str,
    record: Mapping[str, Any],
    *,
    input_receipt: Mapping[str, Any],
    authorization_manifest_sha256: str,
) -> dict[str, Any]:
    validate_spent_incomplete_record(
        record,
        input_receipt=input_receipt,
        state_prefix=state_prefix,
        authorization_manifest_sha256=authorization_manifest_sha256,
    )
    return persist_singleton(
        service,
        container,
        f"{normalize_blob_prefix(state_prefix)}/{SPENT_INCOMPLETE_FILENAME}",
        canonical_json_bytes(dict(record)),
    )


def persist_scoring_incomplete_record(
    service: Any,
    container: str,
    state_prefix: str,
    record: Mapping[str, Any],
    *,
    labels_open_transaction: Mapping[str, Any],
) -> dict[str, Any]:
    validate_scoring_incomplete_record(
        record, labels_open_transaction=labels_open_transaction
    )
    return persist_singleton(
        service,
        container,
        (
            f"{normalize_blob_prefix(state_prefix)}/"
            f"{SCORING_INCOMPLETE_FILENAME}"
        ),
        canonical_json_bytes(dict(record)),
    )


def persist_labels_open_transaction(
    service: Any,
    container: str,
    state_prefix: str,
    transaction: Mapping[str, Any],
) -> dict[str, Any]:
    validate_labels_open_transaction(transaction)
    blob_name = (
        f"{normalize_blob_prefix(state_prefix)}/"
        f"{LABELS_OPEN_TRANSACTION_FILENAME}"
    )
    return persist_singleton(
        service, container, blob_name, canonical_json_bytes(dict(transaction))
    )


def _member_metadata(
    name: str, data: bytes, etag: str
) -> dict[str, Any]:
    return {
        "name": name,
        "size": len(data),
        "sha256": sha256_bytes(data),
        "etag": etag,
    }


def persist_manifest_last_prefix(
    service: Any,
    container: str,
    prefix: str,
    *,
    member_names: Sequence[str],
    payloads: Mapping[str, bytes],
    manifest_builder: Callable[[list[dict[str, Any]]], Mapping[str, Any]],
    registered_member_names: Sequence[str] | None = None,
    parent_prefix: str | None = None,
    registered_parent_members_before: Iterable[str] | None = None,
    adopted_reservation: bytes | None = None,
    adopted_payloads: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    checked_prefix = normalize_blob_prefix(prefix)
    names = tuple(member_names)
    if not names or names[0][0] != "." or "manifest" not in names[-1]:
        raise LockedEvaluationError(
            "immutable prefix must be reservation-first and manifest-last"
        )
    if (
        registered_member_names is not None
        and names != tuple(registered_member_names)
    ):
        raise LockedEvaluationError("leaf member set is not the registered set")
    parent_baseline: set[str] | None = None
    if parent_prefix is not None or registered_parent_members_before is not None:
        if parent_prefix is None or registered_parent_members_before is None:
            raise LockedEvaluationError(
                "registered parent verification requires both bindings"
            )
        parent_baseline = {
            normalize_blob_prefix(item)
            for item in registered_parent_members_before
        }
        validate_registered_parent_membership(
            service, container, parent_prefix, parent_baseline
        )
    if set(payloads) != set(names[:-1]):
        raise LockedEvaluationError("payload membership is not exact")
    if list(payloads) != list(names[:-1]):
        raise LockedEvaluationError("payload order is not registered")
    uploaded: dict[str, tuple[bytes, str]] = {}
    existing_members = list_exact_prefix(service, container, checked_prefix)
    first_blob = f"{checked_prefix}/{names[0]}"
    if adopted_payloads is not None:
        if adopted_reservation is not None:
            raise LockedEvaluationError(
                "immutable prefix adoption channels are mutually exclusive"
            )
        adopted_names = tuple(adopted_payloads)
        if (
            not adopted_names
            or adopted_names != names[: len(adopted_names)]
            or len(adopted_names) >= len(names)
            or any(
                type(adopted_payloads[name]) is not bytes
                or adopted_payloads[name] != payloads[name]
                for name in adopted_names
            )
            or existing_members
            != {
                f"{checked_prefix}/{name}" for name in adopted_names
            }
        ):
            raise LockedEvaluationError(
                "existing prefix members cannot be authenticated for reuse"
            )
        for name in adopted_names:
            persisted, persisted_etag = download_stable_blob(
                service, container, f"{checked_prefix}/{name}"
            )
            if persisted != adopted_payloads[name]:
                raise LockedEvaluationError(
                    "existing prefix member bytes differ from the authorized retry"
                )
            uploaded[name] = (persisted, persisted_etag)
        remaining_names = names[len(adopted_names) : -1]
    elif adopted_reservation is None:
        if existing_members:
            raise LockedEvaluationError("immutable output prefix is not empty")
        remaining_names = names[:-1]
    else:
        if (
            type(adopted_reservation) is not bytes
            or adopted_reservation != payloads[names[0]]
            or existing_members != {first_blob}
        ):
            raise LockedEvaluationError(
                "existing reservation cannot be authenticated for reuse"
            )
        persisted, persisted_etag = download_stable_blob(
            service, container, first_blob
        )
        if persisted != adopted_reservation:
            raise LockedEvaluationError(
                "existing reservation bytes differ from the authorized retry"
            )
        uploaded[names[0]] = (persisted, persisted_etag)
        remaining_names = names[1:-1]
    for name in remaining_names:
        data = payloads[name]
        blob_name = f"{checked_prefix}/{name}"
        etag = upload_blob_once(service, container, blob_name, data)
        uploaded[name] = (data, etag)
        expected = {
            f"{checked_prefix}/{member}" for member in uploaded
        }
        if list_exact_prefix(service, container, checked_prefix) != expected:
            raise LockedEvaluationError(
                "exact membership failed during immutable upload"
            )
        if parent_baseline is not None:
            validate_registered_parent_membership(
                service,
                container,
                parent_prefix,
                parent_baseline
                | {
                    f"{checked_prefix}/{uploaded_name}"
                    for uploaded_name in uploaded
                },
            )
    metadata = [
        _member_metadata(name, *uploaded[name]) for name in names[:-1]
    ]
    for name in names[:-1]:
        data, etag = uploaded[name]
        verify_uploaded_blob(
            service, container, f"{checked_prefix}/{name}", data, etag
        )
    if parent_baseline is not None:
        validate_registered_parent_membership(
            service,
            container,
            parent_prefix,
            parent_baseline
            | {f"{checked_prefix}/{name}" for name in names[:-1]},
        )
    manifest = dict(manifest_builder(metadata))
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_name = names[-1]
    manifest_blob_name = f"{checked_prefix}/{manifest_name}"
    manifest_etag = upload_blob_once(
        service, container, manifest_blob_name, manifest_bytes
    )
    uploaded[manifest_name] = (manifest_bytes, manifest_etag)
    expected_final = {
        f"{checked_prefix}/{name}" for name in names
    }
    if list_exact_prefix(service, container, checked_prefix) != expected_final:
        raise LockedEvaluationError("final exact prefix membership failed")
    for name in names:
        data, etag = uploaded[name]
        verify_uploaded_blob(
            service, container, f"{checked_prefix}/{name}", data, etag
        )
    if parent_baseline is not None:
        validate_registered_parent_membership(
            service,
            container,
            parent_prefix,
            parent_baseline
            | {f"{checked_prefix}/{name}" for name in names},
        )
    return {
        "prefix": checked_prefix,
        "exact_members": list(names),
        "manifest": manifest,
        "manifest_bytes": manifest_bytes,
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "manifest_etag": manifest_etag,
        "verified_count": len(names),
        "overwrite": False,
        "manifest_uploaded_last": True,
        "reservation_adopted": (
            adopted_reservation is not None or adopted_payloads is not None
        ),
    }


def build_prediction_artifact_manifest(
    *,
    metadata: Sequence[Mapping[str, Any]],
    seal_sha256: str,
    prediction_seal: Mapping[str, Any],
    request_manifest: Mapping[str, Any],
    created_utc: str,
    retry_kind: str = "none",
    execution_id: str | None = None,
) -> dict[str, Any]:
    expected_payload_names = list(PREDICTION_MEMBER_NAMES[:-1])
    if (
        not isinstance(metadata, Sequence)
        or isinstance(metadata, (str, bytes, bytearray))
        or len(metadata) != len(expected_payload_names)
    ):
        raise LockedEvaluationError("prediction manifest payload order is not exact")
    checked_metadata: list[dict[str, Any]] = []
    for index, (item, expected_name) in enumerate(
        zip(metadata, expected_payload_names, strict=True)
    ):
        _require_exact_fields(
            item,
            {"name", "size", "sha256", "etag"},
            f"prediction manifest payload[{index}]",
        )
        checked_item = {
            "name": _require_string(
                item["name"], f"prediction manifest payload[{index}].name"
            ),
            "size": _require_int(
                item["size"],
                f"prediction manifest payload[{index}].size",
                minimum=0,
            ),
            "sha256": _require_sha256(
                item["sha256"],
                f"prediction manifest payload[{index}].sha256",
            ),
            "etag": _require_string(
                item["etag"], f"prediction manifest payload[{index}].etag"
            ),
        }
        if checked_item["name"] != expected_name:
            raise LockedEvaluationError(
                "prediction manifest payload order is not exact"
            )
        checked_metadata.append(checked_item)
    validate_prediction_request_manifest(
        request_manifest,
        expected_authorization_id=request_manifest["authorization_id"],
        expected_parent_prefix=request_manifest["registered_parent_prefix"],
        expected_retry_kind=retry_kind,
        expected_execution_id=execution_id,
    )
    if (
        prediction_seal.get("prediction_request_manifest_sha256")
        != sha256_bytes(canonical_json_bytes(dict(request_manifest)))
        or not exact_json_equal(
            prediction_seal.get("ordered_case_ids"),
            request_manifest["ordered_case_ids"],
        )
    ):
        raise LockedEvaluationError(
            "prediction manifest inputs do not form one sealed request"
        )
    record = {
        "schema_version": PREDICTION_MANIFEST_SCHEMA_VERSION,
        "authorization_id": request_manifest["authorization_id"],
        "registered_parent_prefix": request_manifest["registered_parent_prefix"],
        "prediction_prefix": request_manifest["prediction_prefix"],
        "implementation_commit": request_manifest["implementation_commit"],
        "image_digest": request_manifest["image_digest"],
        "config_sha256": request_manifest["config_sha256"],
        "runtime_config_sha256": request_manifest["runtime_config_sha256"],
        "authorization_lock_sha256": request_manifest[
            "authorization_lock_sha256"
        ],
        "authorization_manifest_sha256": request_manifest[
            "authorization_manifest_sha256"
        ],
        "implementation_manifest_sha256": request_manifest[
            "implementation_manifest_sha256"
        ],
        "locked_manifest_sha256": request_manifest["locked_manifest_sha256"],
        "input_receipt_sha256": request_manifest["input_receipt_sha256"],
        "parser_source_sha256": FROZEN_PARSER_SOURCE_SHA256,
        "parser_version": FROZEN_PARSER_VERSION,
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": FROZEN_PROTOCOL_BUNDLE_SHA256,
        "acceptance_gates_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
        "locked_input_reservation_blob": request_manifest[
            "locked_input_reservation_blob"
        ],
        "locked_input_reservation_sha256": request_manifest[
            "locked_input_reservation_sha256"
        ],
        "locked_input_private_nonce_sha256": request_manifest[
            "locked_input_private_nonce_sha256"
        ],
        "locked_input_reservation_etag": request_manifest[
            "locked_input_reservation_etag"
        ],
        "locked_input_blob": request_manifest["locked_input_blob"],
        "locked_input_sha256": request_manifest["locked_input_sha256"],
        "locked_input_etag": request_manifest["locked_input_etag"],
        "locked_input_manifest_blob": request_manifest[
            "locked_input_manifest_blob"
        ],
        "locked_input_manifest_sha256": request_manifest[
            "locked_input_manifest_sha256"
        ],
        "source_manifest_sha256": request_manifest["source_manifest_sha256"],
        "locked_input_manifest_etag": request_manifest[
            "locked_input_manifest_etag"
        ],
        "prediction_request_manifest_sha256": sha256_bytes(
            canonical_json_bytes(dict(request_manifest))
        ),
        "stage_p_visibility_sha256": request_manifest["visibility_sha256"],
        "stage_p_visibility_etag": request_manifest["visibility_etag"],
        "prediction_seal_sha256": _require_sha256(
            seal_sha256, "prediction seal SHA-256"
        ),
        "frozen_prediction_seal_sha256": sha256_bytes(
            canonical_json_bytes(dict(prediction_seal["frozen_v2_seal"]))
        ),
        "row_count": len(request_manifest["ordered_case_ids"]),
        "ordered_case_ids": list(request_manifest["ordered_case_ids"]),
        "case_universe_sha256": request_manifest["case_universe_sha256"],
        "exact_members": list(PREDICTION_MEMBER_NAMES),
        "payload_members": checked_metadata,
        "labels_accessed": False,
        "overwrite": False,
        "manifest_uploaded_last": True,
        "created_utc": _require_utc(created_utc, "prediction manifest created_utc"),
    }
    assert_label_blind_payload(record)
    return record


_PREDICTION_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "registered_parent_prefix",
        "prediction_prefix",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "runtime_config_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "locked_manifest_sha256",
        "input_receipt_sha256",
        "parser_source_sha256",
        "parser_version",
        "protocol_commit",
        "protocol_bundle_sha256",
        "acceptance_gates_sha256",
        "locked_input_reservation_blob",
        "locked_input_reservation_sha256",
        "locked_input_private_nonce_sha256",
        "locked_input_reservation_etag",
        "locked_input_blob",
        "locked_input_sha256",
        "locked_input_etag",
        "locked_input_manifest_blob",
        "locked_input_manifest_sha256",
        "source_manifest_sha256",
        "locked_input_manifest_etag",
        "prediction_request_manifest_sha256",
        "stage_p_visibility_sha256",
        "stage_p_visibility_etag",
        "prediction_seal_sha256",
        "frozen_prediction_seal_sha256",
        "row_count",
        "ordered_case_ids",
        "case_universe_sha256",
        "exact_members",
        "payload_members",
        "labels_accessed",
        "overwrite",
        "manifest_uploaded_last",
        "created_utc",
    }
)


def validate_prediction_artifact_manifest(
    data: bytes,
    *,
    expected_sha256: str,
    parent_prefix: str,
    authorization_id: str,
    expected_retry_kind: str = "none",
    expected_execution_id: str | None = None,
) -> dict[str, Any]:
    if sha256_bytes(data) != _require_sha256(
        expected_sha256, "expected prediction manifest SHA-256"
    ):
        raise LockedEvaluationError("prediction artifact manifest hash mismatch")
    record = parse_json_strict(data, PREDICTION_MEMBER_NAMES[-1])
    _require_exact_fields(
        record, _PREDICTION_MANIFEST_FIELDS, "prediction artifact manifest"
    )
    if expected_retry_kind == "none":
        attempt_execution_id = (
            "primary-prefix-binding"
            if expected_execution_id is None
            else _require_string(
                expected_execution_id, "expected prediction execution_id"
            )
        )
    else:
        attempt_execution_id = _require_string(
            expected_execution_id, "expected prediction retry execution_id"
        )
    expected_prediction_prefix = derive_attempt_prefix(
        parent_prefix,
        authorization_id,
        "predictions",
        "P",
        expected_retry_kind,
        attempt_execution_id,
    )
    if (
        record.get("schema_version") != PREDICTION_MANIFEST_SCHEMA_VERSION
        or record.get("authorization_id") != validate_authorization_id(authorization_id)
        or record.get("registered_parent_prefix")
        != validate_registered_parent_prefix(parent_prefix)
        or record.get("prediction_prefix")
        != expected_prediction_prefix
        or not exact_json_equal(
            record.get("exact_members"), list(PREDICTION_MEMBER_NAMES)
        )
        or record.get("labels_accessed") is not False
        or record.get("overwrite") is not False
        or record.get("manifest_uploaded_last") is not True
    ):
        raise LockedEvaluationError("prediction artifact manifest binding mismatch")
    fixed = {
        "parser_source_sha256": FROZEN_PARSER_SOURCE_SHA256,
        "parser_version": FROZEN_PARSER_VERSION,
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": FROZEN_PROTOCOL_BUNDLE_SHA256,
        "acceptance_gates_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
    }
    if any(
        not exact_json_equal(record.get(field), value)
        for field, value in fixed.items()
    ):
        raise LockedEvaluationError("prediction artifact frozen binding mismatch")
    for field in (
        "config_sha256",
        "runtime_config_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "locked_manifest_sha256",
        "input_receipt_sha256",
        "locked_input_reservation_sha256",
        "locked_input_private_nonce_sha256",
        "locked_input_sha256",
        "locked_input_manifest_sha256",
        "source_manifest_sha256",
        "prediction_request_manifest_sha256",
        "prediction_seal_sha256",
        "frozen_prediction_seal_sha256",
        "case_universe_sha256",
    ):
        _require_sha256(record[field], f"prediction manifest {field}")
    if (
        record["runtime_config_sha256"] != record["config_sha256"]
        or record["source_manifest_sha256"]
        != record["locked_input_manifest_sha256"]
        or record["locked_input_reservation_blob"]
        != (
            f"{record['registered_parent_prefix']}/locked-inputs/"
            ".locked_inputs_reservation.json"
        )
        or record["locked_input_blob"]
        != f"{record['registered_parent_prefix']}/locked-inputs/locked_inputs.jsonl"
        or record["locked_input_manifest_blob"]
        != (
            f"{record['registered_parent_prefix']}/locked-inputs/"
            "locked_inputs_manifest.json"
        )
    ):
        raise LockedEvaluationError(
            "prediction artifact source provenance is not exact"
        )
    _require_string(
        record["locked_input_etag"], "prediction manifest locked-input ETag"
    )
    _require_string(
        record["locked_input_manifest_etag"],
        "prediction manifest locked-input manifest ETag",
    )
    _require_sha256(
        record.get("stage_p_visibility_sha256"),
        "prediction manifest Stage-P visibility SHA-256",
    )
    _require_string(
        record.get("stage_p_visibility_etag"),
        "prediction manifest Stage-P visibility ETag",
    )
    metadata = record.get("payload_members")
    if (
        not isinstance(metadata, list)
        or [item.get("name") for item in metadata if isinstance(item, Mapping)]
        != list(PREDICTION_MEMBER_NAMES[:-1])
    ):
        raise LockedEvaluationError("prediction payload metadata is not exact")
    for index, item in enumerate(metadata):
        _require_exact_fields(
            item, {"name", "size", "sha256", "etag"}, f"payload member[{index}]"
        )
        _require_int(item["size"], f"payload member[{index}].size", minimum=0)
        _require_sha256(item["sha256"], f"payload member[{index}].sha256")
        _require_string(item["etag"], f"payload member[{index}].etag")
    ids = [_require_case_id(item) for item in record.get("ordered_case_ids", [])]
    if (
        ids != sorted(set(ids))
        or not exact_json_equal(record.get("row_count"), len(ids))
        or record["case_universe_sha256"] != case_universe_sha256(ids)
    ):
        raise LockedEvaluationError("prediction manifest membership is invalid")
    assert_label_blind_payload(record)
    return record


def download_prediction_artifacts(
    service: Any,
    container: str,
    prefix: str,
    manifest_bytes: bytes,
    manifest: Mapping[str, Any],
    manifest_etag: str,
) -> dict[str, bytes]:
    expected_names = set(PREDICTION_MEMBER_NAMES)
    expected_blob_names = {
        f"{normalize_blob_prefix(prefix)}/{name}" for name in expected_names
    }
    if list_exact_prefix(service, container, prefix) != expected_blob_names:
        raise LockedEvaluationError("prediction prefix exact membership mismatch")
    result = {PREDICTION_MEMBER_NAMES[-1]: manifest_bytes}
    metadata = {
        item["name"]: item for item in manifest["payload_members"]
    }
    for name in PREDICTION_MEMBER_NAMES[:-1]:
        item = metadata[name]
        data, _ = download_verified_blob(
            service,
            container,
            f"{prefix}/{name}",
            expected_sha256=item["sha256"],
            expected_size=item["size"],
            expected_etag=item["etag"],
        )
        result[name] = data
    manifest_blob = f"{prefix}/{PREDICTION_MEMBER_NAMES[-1]}"
    verify_uploaded_blob(
        service, container, manifest_blob, manifest_bytes, manifest_etag
    )
    return {name: result[name] for name in PREDICTION_MEMBER_NAMES}


def validate_prediction_artifact_graph(
    manifest_bytes: bytes,
    manifest: Mapping[str, Any],
    artifacts: Mapping[str, bytes],
    *,
    gates: Mapping[str, Any],
    source_manifest_bytes: bytes | None = None,
    source_manifest_etag: str | None = None,
    expected_authorization_id: str,
    expected_parent_prefix: str,
    expected_prediction_manifest_sha256: str,
    expected_input_manifest_sha256: str,
    expected_input_receipt_sha256: str,
    expected_authorization_lock_sha256: str,
    expected_authorization_manifest_sha256: str,
    expected_implementation_manifest_sha256: str,
    expected_locked_manifest_sha256: str,
    expected_implementation_commit: str,
    expected_image_digest: str,
    expected_config_sha256: str,
    locked_inputs_bytes: bytes | None = None,
    locked_input_etag: str | None = None,
    expected_locked_input_source_binding: Mapping[str, Any] | None = None,
    expected_retry_kind: str = "none",
    expected_execution_id: str | None = None,
) -> dict[str, Any]:
    if set(artifacts) != set(PREDICTION_MEMBER_NAMES):
        raise LockedEvaluationError("prediction artifact byte membership is not exact")
    checked_manifest = validate_prediction_artifact_manifest(
        manifest_bytes,
        expected_sha256=expected_prediction_manifest_sha256,
        parent_prefix=expected_parent_prefix,
        authorization_id=expected_authorization_id,
        expected_retry_kind=expected_retry_kind,
        expected_execution_id=expected_execution_id,
    )
    if not exact_json_equal(dict(manifest), checked_manifest):
        raise LockedEvaluationError("prediction manifest object/byte mismatch")
    metadata = {
        item["name"]: item for item in checked_manifest["payload_members"]
    }
    for name in PREDICTION_MEMBER_NAMES[:-1]:
        item = metadata[name]
        data = artifacts[name]
        if len(data) != item["size"] or sha256_bytes(data) != item["sha256"]:
            raise LockedEvaluationError(
                "prediction artifact bytes differ from manifest metadata"
            )
    if artifacts[PREDICTION_MEMBER_NAMES[-1]] != manifest_bytes:
        raise LockedEvaluationError("prediction manifest bytes are not exact")

    request_bytes = artifacts["prediction_request_manifest.json"]
    request = parse_json_strict(request_bytes, "prediction request manifest")
    validate_prediction_request_manifest(
        request,
        expected_authorization_id=expected_authorization_id,
        expected_parent_prefix=expected_parent_prefix,
        expected_retry_kind=expected_retry_kind,
        expected_execution_id=expected_execution_id,
    )
    seal_bytes = artifacts["prediction_seal.json"]
    seal = parse_json_strict(seal_bytes, "prediction seal")
    seal_binding = validate_locked_prediction_seal(
        seal,
        request_manifest_bytes=request_bytes,
        predictions_bytes=artifacts["parser_v2_locked_predictions.jsonl"],
        legacy_predictions_bytes=artifacts["legacy_locked_predictions.jsonl"],
        expected_authorization_id=expected_authorization_id,
        expected_parent_prefix=expected_parent_prefix,
        expected_retry_kind=expected_retry_kind,
        expected_execution_id=expected_execution_id,
    )
    reservation = parse_json_strict(
        artifacts[".prediction_reservation.json"], "prediction reservation"
    )
    _require_exact_fields(
        reservation,
        {
            "schema_version",
            "leaf",
            "prefix",
            "authorization_id",
            "created_utc",
            "nonce",
            "overwrite",
        },
        "prediction reservation",
    )
    rebuilt_reservation = build_reservation(
        leaf=reservation["leaf"],
        prefix=reservation["prefix"],
        authorization_id=reservation["authorization_id"],
        created_utc=reservation["created_utc"],
        nonce=reservation["nonce"],
        parent_prefix=expected_parent_prefix,
        stage="P",
        retry_kind=expected_retry_kind,
        execution_id=(
            expected_execution_id
            if expected_execution_id is not None
            else "primary-prefix-binding"
        ),
    )
    if (
        not exact_json_equal(reservation, rebuilt_reservation)
        or reservation["leaf"] != "predictions"
        or reservation["prefix"] != request["prediction_prefix"]
        or reservation["authorization_id"] != request["authorization_id"]
    ):
        raise LockedEvaluationError("prediction reservation binding is invalid")

    expected = {
        "authorization_id": validate_authorization_id(
            expected_authorization_id
        ),
        "registered_parent_prefix": validate_registered_parent_prefix(
            expected_parent_prefix
        ),
        "implementation_commit": _require_commit(
            expected_implementation_commit, "expected implementation commit"
        ),
        "image_digest": _require_image_digest(
            expected_image_digest, "expected image digest"
        ),
        "config_sha256": _require_sha256(
            expected_config_sha256, "expected config SHA-256"
        ),
        "runtime_config_sha256": _require_sha256(
            expected_config_sha256, "expected runtime-config SHA-256"
        ),
        "authorization_lock_sha256": _require_sha256(
            expected_authorization_lock_sha256,
            "expected authorization lock SHA-256",
        ),
        "authorization_manifest_sha256": _require_sha256(
            expected_authorization_manifest_sha256,
            "expected authorization manifest SHA-256",
        ),
        "implementation_manifest_sha256": _require_sha256(
            expected_implementation_manifest_sha256,
            "expected implementation manifest SHA-256",
        ),
        "locked_manifest_sha256": _require_sha256(
            expected_locked_manifest_sha256,
            "expected locked manifest SHA-256",
        ),
        "input_receipt_sha256": _require_sha256(
            expected_input_receipt_sha256,
            "expected INPUTS_READ receipt SHA-256",
        ),
        "locked_input_manifest_sha256": _require_sha256(
            expected_input_manifest_sha256,
            "expected locked-input manifest SHA-256",
        ),
        "source_manifest_sha256": _require_sha256(
            expected_input_manifest_sha256,
            "expected source manifest SHA-256",
        ),
    }
    for record_name, record in (
        ("request", request),
        ("prediction seal", seal),
        ("prediction manifest", checked_manifest),
    ):
        if any(
            not exact_json_equal(record.get(field), value)
            for field, value in expected.items()
        ):
            raise LockedEvaluationError(
                f"{record_name} differs from authenticated provenance"
            )

    if expected_locked_input_source_binding is not None:
        if not isinstance(expected_locked_input_source_binding, Mapping):
            raise LockedEvaluationError(
                "authenticated locked-input source binding is invalid"
            )
        for record_name, record in (
            ("request", request),
            ("prediction seal", seal),
            ("prediction manifest", checked_manifest),
        ):
            if any(
                field not in expected_locked_input_source_binding
                or not exact_json_equal(
                    record.get(field),
                    expected_locked_input_source_binding[field],
                )
                for field in _LOCKED_INPUT_SOURCE_BINDING_FIELDS
            ):
                raise LockedEvaluationError(
                    f"{record_name} differs from authenticated locked-input source"
                )

    if source_manifest_bytes is None:
        if source_manifest_etag is not None or locked_inputs_bytes is not None:
            raise LockedEvaluationError(
                "locked-input-free graph validation received a source channel"
            )
        ids = [_require_case_id(item) for item in request["ordered_case_ids"]]
        source = {
            "manifest_sha256": expected["locked_input_manifest_sha256"],
            "payload_sha256": request["locked_input_sha256"],
            "ordered_case_ids": ids,
        }
    else:
        if source_manifest_etag is None:
            raise LockedEvaluationError("source manifest ETag binding is incomplete")
        source = validate_locked_source_manifest(
            source_manifest_bytes,
            expected_manifest_sha256=expected_input_manifest_sha256,
            expected_payload_sha256=request["locked_input_sha256"],
            parent_prefix=expected_parent_prefix,
            manifest_kind="locked-inputs",
            payload_relative_path="locked-inputs/locked_inputs.jsonl",
            gates=gates,
        )
        ids = [_require_case_id(item) for item in source["ordered_case_ids"]]
    if (
        (
            source_manifest_etag is not None
            and (
                source_manifest_etag != request["locked_input_manifest_etag"]
                or source_manifest_etag
                != checked_manifest["locked_input_manifest_etag"]
            )
        )
        or not exact_json_equal(
            source["ordered_case_ids"], request["ordered_case_ids"]
        )
        or not exact_json_equal(
            source["ordered_case_ids"], seal_binding["ordered_case_ids"]
        )
        or not exact_json_equal(
            source["ordered_case_ids"], checked_manifest["ordered_case_ids"]
        )
        or checked_manifest["prediction_request_manifest_sha256"]
        != sha256_bytes(request_bytes)
        or checked_manifest["prediction_seal_sha256"] != sha256_bytes(seal_bytes)
        or checked_manifest["frozen_prediction_seal_sha256"]
        != sha256_bytes(canonical_json_bytes(seal["frozen_v2_seal"]))
    ):
        raise LockedEvaluationError(
            "prediction request/seals/manifest/source are not cross-bound"
        )

    predictions = parse_jsonl_strict(
        artifacts["parser_v2_locked_predictions.jsonl"],
        "parser-v2 predictions",
    )
    legacy = parse_jsonl_strict(
        artifacts["legacy_locked_predictions.jsonl"], "legacy predictions"
    )
    if (
        [item.get("case_id") for item in predictions] != ids
        or [item.get("case_id") for item in legacy] != ids
        or checked_manifest["case_universe_sha256"] != case_universe_sha256(ids)
    ):
        raise LockedEvaluationError(
            "prediction rows differ from the authorized source universe"
        )
    if locked_inputs_bytes is not None:
        if (
            sha256_bytes(locked_inputs_bytes) != source["payload_sha256"]
            or locked_input_etag is None
            or locked_input_etag != request["locked_input_etag"]
            or locked_input_etag != checked_manifest["locked_input_etag"]
        ):
            raise LockedEvaluationError(
                "locked-input payload hash/ETag provenance mismatch"
            )
        locked_inputs = validate_locked_inputs_bytes(locked_inputs_bytes, gates)
        if [item["case_id"] for item in locked_inputs] != ids:
            raise LockedEvaluationError(
                "locked-input payload differs from its source manifest"
            )
        validate_prediction_rows(predictions, legacy, locked_inputs, gates)
    assert_label_blind_payload(request)
    assert_label_blind_payload(seal)
    assert_label_blind_payload(checked_manifest)
    assert_label_blind_payload(predictions)
    assert_label_blind_payload(legacy)
    return {
        "manifest": checked_manifest,
        "request": request,
        "seal": seal,
        "ordered_case_ids": ids,
        "case_universe_sha256": case_universe_sha256(ids),
        "source": source,
    }


def build_score_manifest(
    *,
    metadata: Sequence[Mapping[str, Any]],
    authorization_id: str,
    authorization_lock_sha256: str,
    authorization_manifest_sha256: str,
    implementation_manifest_sha256: str,
    parent_prefix: str,
    scores_prefix: str,
    scoring_retry_kind: str,
    retry_receipt_sha256: str | None,
    prediction_seal_sha256: str,
    prediction_manifest_sha256: str,
    prediction_request_manifest_sha256: str,
    locked_manifest_sha256: str,
    input_manifest_sha256: str,
    locked_input_sha256: str,
    labels_manifest_sha256: str,
    labels_manifest_blob_name: str,
    labels_manifest_etag: str,
    labels_blob_name: str,
    labels_sha256: str,
    labels_open_transaction_sha256: str,
    labels_etag: str,
    scoring_ledger_sha256: str,
    scoring_ledger_size: int,
    scoring_ledger_etag: str,
    case_universe_sha256: str,
    row_count: int,
    scoring_transaction_sha256: str,
    scoring_execution_id: str,
    scoring_actor: str,
    stage_e_visibility_sha256: str,
    stage_e_visibility_etag: str,
    gate_sha256: str,
    metrics_sha256: str,
    decision_sha256: str,
    retirement_sha256: str,
    implementation_commit: str,
    image_digest: str,
    config_sha256: str,
    outcome: str,
    created_utc: str,
) -> dict[str, Any]:
    if (
        not isinstance(metadata, Sequence)
        or isinstance(metadata, (str, bytes, bytearray))
        or len(metadata) != len(SCORE_MEMBER_NAMES) - 1
    ):
        raise LockedEvaluationError("score manifest payload order is not exact")
    checked_metadata: list[dict[str, Any]] = []
    for index, (item, expected_name) in enumerate(
        zip(metadata, SCORE_MEMBER_NAMES[:-1], strict=True)
    ):
        _require_exact_fields(
            item,
            {"name", "size", "sha256", "etag"},
            f"score manifest payload[{index}]",
        )
        checked_item = {
            "name": _require_string(item["name"], "score payload name"),
            "size": _require_int(
                item["size"], "score payload size", minimum=0
            ),
            "sha256": _require_sha256(
                item["sha256"], "score payload SHA-256"
            ),
            "etag": _require_string(item["etag"], "score payload ETag"),
        }
        if checked_item["name"] != expected_name:
            raise LockedEvaluationError(
                "score manifest payload order is not exact"
            )
        checked_metadata.append(checked_item)
    if [item["name"] for item in checked_metadata] != list(
        SCORE_MEMBER_NAMES[:-1]
    ):
        raise LockedEvaluationError("score manifest payload order is not exact")
    if _require_sha256(gate_sha256, "gate SHA-256") != FROZEN_ACCEPTANCE_GATE_SHA256:
        raise LockedEvaluationError("score manifest gate binding is not frozen")
    ledger_metadata = checked_metadata[
        SCORE_MEMBER_NAMES.index(SCORING_LEDGER_FILENAME)
    ]
    _require_exact_fields(
        ledger_metadata,
        {"name", "size", "sha256", "etag"},
        "score manifest ledger member",
    )
    checked_ledger_sha256 = _require_sha256(
        scoring_ledger_sha256, "score manifest ledger SHA-256"
    )
    checked_ledger_size = _require_int(
        scoring_ledger_size, "score manifest ledger size", minimum=1
    )
    checked_ledger_etag = _require_string(
        scoring_ledger_etag, "score manifest ledger ETag"
    )
    if not exact_json_equal(
        ledger_metadata,
        {
            "name": SCORING_LEDGER_FILENAME,
            "size": checked_ledger_size,
            "sha256": checked_ledger_sha256,
            "etag": checked_ledger_etag,
        },
    ):
        raise LockedEvaluationError(
            "score manifest ledger member binding is not exact"
        )
    scoring_attempt = validate_scoring_attempt_binding(
        parent_prefix=parent_prefix,
        authorization_id=authorization_id,
        scores_prefix=scores_prefix,
        scoring_retry_kind=scoring_retry_kind,
        scoring_execution_id=scoring_execution_id,
        retry_receipt_sha256=retry_receipt_sha256,
    )
    return {
        "schema_version": SCORE_MANIFEST_SCHEMA_VERSION,
        "authorization_id": validate_authorization_id(authorization_id),
        "authorization_lock_sha256": _require_sha256(
            authorization_lock_sha256, "authorization lock SHA-256"
        ),
        "authorization_manifest_sha256": _require_sha256(
            authorization_manifest_sha256, "authorization manifest SHA-256"
        ),
        "implementation_manifest_sha256": _require_sha256(
            implementation_manifest_sha256,
            "implementation manifest SHA-256",
        ),
        "registered_parent_prefix": validate_registered_parent_prefix(parent_prefix),
        "scores_prefix": scoring_attempt["scores_prefix"],
        "scoring_retry_kind": scoring_attempt["scoring_retry_kind"],
        "retry_receipt_sha256": scoring_attempt["retry_receipt_sha256"],
        "prediction_seal_sha256": _require_sha256(
            prediction_seal_sha256, "prediction seal SHA-256"
        ),
        "prediction_manifest_sha256": _require_sha256(
            prediction_manifest_sha256, "prediction manifest SHA-256"
        ),
        "prediction_request_manifest_sha256": _require_sha256(
            prediction_request_manifest_sha256,
            "prediction request manifest SHA-256",
        ),
        "locked_manifest_sha256": _require_sha256(
            locked_manifest_sha256, "locked manifest SHA-256"
        ),
        "input_manifest_sha256": _require_sha256(
            input_manifest_sha256, "locked-input manifest SHA-256"
        ),
        "locked_input_sha256": _require_sha256(
            locked_input_sha256, "locked-input payload SHA-256"
        ),
        "labels_manifest_sha256": _require_sha256(
            labels_manifest_sha256, "labels manifest SHA-256"
        ),
        "labels_manifest_blob_name": normalize_blob_prefix(
            labels_manifest_blob_name
        ),
        "labels_manifest_etag": _require_string(
            labels_manifest_etag, "labels manifest ETag"
        ),
        "labels_blob_name": normalize_blob_prefix(labels_blob_name),
        "labels_sha256": _require_sha256(labels_sha256, "labels SHA-256"),
        "labels_open_transaction_sha256": _require_sha256(
            labels_open_transaction_sha256,
            "labels-open transaction SHA-256",
        ),
        "labels_etag": _require_string(labels_etag, "labels ETag"),
        "scoring_ledger_sha256": checked_ledger_sha256,
        "scoring_ledger_size": checked_ledger_size,
        "scoring_ledger_etag": checked_ledger_etag,
        "case_universe_sha256": _require_sha256(
            case_universe_sha256, "case-universe SHA-256"
        ),
        "row_count": _require_int(row_count, "score row count", minimum=1),
        "scoring_transaction_sha256": _require_sha256(
            scoring_transaction_sha256, "scoring transaction SHA-256"
        ),
        "scoring_execution_id": _require_string(
            scoring_execution_id, "scoring execution ID"
        ),
        "scoring_actor": _require_string(scoring_actor, "scoring actor"),
        "stage_e_visibility_sha256": _require_sha256(
            stage_e_visibility_sha256, "Stage-E visibility SHA-256"
        ),
        "stage_e_visibility_etag": _require_string(
            stage_e_visibility_etag, "Stage-E visibility ETag"
        ),
        "acceptance_gates_sha256": gate_sha256,
        "metrics_sha256": _require_sha256(metrics_sha256, "metrics SHA-256"),
        "decision_sha256": _require_sha256(decision_sha256, "decision SHA-256"),
        "retirement_sha256": _require_sha256(
            retirement_sha256, "retirement SHA-256"
        ),
        "implementation_commit": _require_commit(
            implementation_commit, "implementation commit"
        ),
        "image_digest": _require_image_digest(image_digest, "image digest"),
        "config_sha256": _require_sha256(config_sha256, "config SHA-256"),
        "outcome": _require_enum(outcome, ("PASS", "FAIL", "INVALID"), "outcome"),
        "exact_members": list(SCORE_MEMBER_NAMES),
        "payload_members": checked_metadata,
        "overwrite": False,
        "manifest_uploaded_last": True,
        "formal_evaluation_count": 1,
        "metric_retry_allowed": False,
        "created_utc": _require_utc(created_utc, "score manifest created_utc"),
    }


def validate_score_manifest(
    data: bytes,
    *,
    expected_sha256: str,
    parent_prefix: str,
    authorization_id: str,
) -> dict[str, Any]:
    if sha256_bytes(data) != _require_sha256(
        expected_sha256, "expected scores manifest SHA-256"
    ):
        raise LockedEvaluationError("scores manifest hash mismatch")
    record = parse_json_strict(data, SCORE_MEMBER_NAMES[-1])
    metadata = record.get("payload_members")
    if not isinstance(metadata, list):
        raise LockedEvaluationError("scores manifest payload metadata is invalid")
    try:
        rebuilt = build_score_manifest(
            metadata=metadata,
            authorization_id=record["authorization_id"],
            authorization_lock_sha256=record["authorization_lock_sha256"],
            authorization_manifest_sha256=record[
                "authorization_manifest_sha256"
            ],
            implementation_manifest_sha256=record[
                "implementation_manifest_sha256"
            ],
            parent_prefix=record["registered_parent_prefix"],
            scores_prefix=record["scores_prefix"],
            scoring_retry_kind=record["scoring_retry_kind"],
            retry_receipt_sha256=record["retry_receipt_sha256"],
            prediction_seal_sha256=record["prediction_seal_sha256"],
            prediction_manifest_sha256=record["prediction_manifest_sha256"],
            prediction_request_manifest_sha256=record[
                "prediction_request_manifest_sha256"
            ],
            locked_manifest_sha256=record["locked_manifest_sha256"],
            input_manifest_sha256=record["input_manifest_sha256"],
            locked_input_sha256=record["locked_input_sha256"],
            labels_manifest_sha256=record["labels_manifest_sha256"],
            labels_manifest_blob_name=record["labels_manifest_blob_name"],
            labels_manifest_etag=record["labels_manifest_etag"],
            labels_blob_name=record["labels_blob_name"],
            labels_sha256=record["labels_sha256"],
            labels_open_transaction_sha256=record[
                "labels_open_transaction_sha256"
            ],
            labels_etag=record["labels_etag"],
            scoring_ledger_sha256=record["scoring_ledger_sha256"],
            scoring_ledger_size=record["scoring_ledger_size"],
            scoring_ledger_etag=record["scoring_ledger_etag"],
            case_universe_sha256=record["case_universe_sha256"],
            row_count=record["row_count"],
            scoring_transaction_sha256=record[
                "scoring_transaction_sha256"
            ],
            scoring_execution_id=record["scoring_execution_id"],
            scoring_actor=record["scoring_actor"],
            stage_e_visibility_sha256=record[
                "stage_e_visibility_sha256"
            ],
            stage_e_visibility_etag=record["stage_e_visibility_etag"],
            gate_sha256=record["acceptance_gates_sha256"],
            metrics_sha256=record["metrics_sha256"],
            decision_sha256=record["decision_sha256"],
            retirement_sha256=record["retirement_sha256"],
            implementation_commit=record["implementation_commit"],
            image_digest=record["image_digest"],
            config_sha256=record["config_sha256"],
            outcome=record["outcome"],
            created_utc=record["created_utc"],
        )
    except (KeyError, TypeError, LockedEvaluationError):
        raise LockedEvaluationError("scores manifest schema is invalid") from None
    if (
        not exact_json_equal(dict(record), rebuilt)
        or record["registered_parent_prefix"]
        != validate_registered_parent_prefix(parent_prefix)
        or record["authorization_id"]
        != validate_authorization_id(authorization_id)
        or record["acceptance_gates_sha256"]
        != FROZEN_ACCEPTANCE_GATE_SHA256
        or record["labels_manifest_blob_name"]
        != (
            f"{record['registered_parent_prefix']}/locked-labels/"
            "locked_labels_manifest.json"
        )
        or record["labels_blob_name"]
        != (
            f"{record['registered_parent_prefix']}/locked-labels/"
            "locked_reference_labels.jsonl"
        )
    ):
        raise LockedEvaluationError("scores manifest bindings are invalid")
    return record


def build_score_payloads(
    metrics: Mapping[str, Any],
    failures: Sequence[Mapping[str, Any]],
    *,
    authorization_id: str,
    registered_parent_prefix: str,
    authorization_lock_sha256: str,
    authorization_manifest_sha256: str,
    implementation_manifest_sha256: str,
    scores_prefix: str,
    prediction_seal_sha256: str,
    prediction_manifest_sha256: str,
    prediction_request_manifest_sha256: str,
    locked_manifest_sha256: str,
    input_manifest_sha256: str,
    locked_input_sha256: str,
    labels_manifest_sha256: str,
    labels_sha256: str,
    labels_open_transaction_sha256: str,
    scoring_retry_kind: str,
    scoring_execution_id: str,
    scoring_actor: str,
    stage_e_visibility_sha256: str,
    retry_receipt_sha256: str | None,
    scoring_ledger_bytes: bytes,
    scoring_ledger_sha256: str,
    scoring_ledger_size: int,
    scoring_ledger_etag: str,
    case_universe_sha256: str,
    row_count: int,
    implementation_commit: str,
    image_digest: str,
    config_sha256: str,
    created_utc: str,
    nonce: str,
) -> tuple[dict[str, bytes], dict[str, Any], dict[str, Any]]:
    if (
        type(scoring_ledger_bytes) is not bytes
        or not scoring_ledger_bytes
        or sha256_bytes(scoring_ledger_bytes)
        != _require_sha256(
            scoring_ledger_sha256, "score payload ledger SHA-256"
        )
        or len(scoring_ledger_bytes)
        != _require_int(
            scoring_ledger_size, "score payload ledger size", minimum=1
        )
    ):
        raise LockedEvaluationError(
            "score payload ledger bytes do not match their binding"
        )
    _require_string(scoring_ledger_etag, "score payload ledger ETag")
    metrics_bytes = canonical_json_bytes(dict(metrics))
    failures_bytes = canonical_jsonl_bytes(list(failures))
    decision = build_decision(
        metrics,
        authorization_id=authorization_id,
        registered_parent_prefix=registered_parent_prefix,
        authorization_lock_sha256=authorization_lock_sha256,
        authorization_manifest_sha256=authorization_manifest_sha256,
        implementation_manifest_sha256=implementation_manifest_sha256,
        prediction_seal_sha256=prediction_seal_sha256,
        prediction_manifest_sha256=prediction_manifest_sha256,
        prediction_request_manifest_sha256=prediction_request_manifest_sha256,
        locked_manifest_sha256=locked_manifest_sha256,
        input_manifest_sha256=input_manifest_sha256,
        locked_input_sha256=locked_input_sha256,
        labels_manifest_sha256=labels_manifest_sha256,
        labels_sha256=labels_sha256,
        labels_open_transaction_sha256=labels_open_transaction_sha256,
        scores_prefix=scores_prefix,
        scoring_retry_kind=scoring_retry_kind,
        scoring_execution_id=scoring_execution_id,
        scoring_actor=scoring_actor,
        stage_e_visibility_sha256=stage_e_visibility_sha256,
        retry_receipt_sha256=retry_receipt_sha256,
        scoring_ledger_sha256=scoring_ledger_sha256,
        scoring_ledger_size=scoring_ledger_size,
        scoring_ledger_etag=scoring_ledger_etag,
        case_universe_sha256=case_universe_sha256,
        row_count=row_count,
        implementation_commit=implementation_commit,
        image_digest=image_digest,
        config_sha256=config_sha256,
        decided_utc=created_utc,
    )
    retirement = build_retirement_record(
        decision,
        authorization_id=authorization_id,
        retired_utc=created_utc,
    )
    report = render_public_report(metrics, decision, retirement)
    reservation = build_reservation(
        leaf="scores",
        prefix=scores_prefix,
        authorization_id=authorization_id,
        created_utc=created_utc,
        nonce=nonce,
        parent_prefix=registered_parent_prefix,
        stage="E",
        retry_kind=scoring_retry_kind,
        execution_id=scoring_execution_id,
    )
    payloads = {
        ".scores_reservation.json": canonical_json_bytes(reservation),
        SCORING_LEDGER_FILENAME: scoring_ledger_bytes,
        "locked_evaluation_metrics.json": metrics_bytes,
        "locked_evaluation_metrics.csv": render_metrics_csv(metrics),
        "locked_evaluation_failures.jsonl": failures_bytes,
        "locked_evaluation_decision.json": canonical_json_bytes(decision),
        "retirement_record.json": canonical_json_bytes(retirement),
        "locked_evaluation_report.md": report,
    }
    return payloads, decision, retirement


def assert_parser_free_source(source: bytes, source_name: str) -> None:
    try:
        tree = ast.parse(source.decode("utf-8"), filename=source_name)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise LockedEvaluationError(
            f"cannot AST-validate parser isolation for {source_name}"
        ) from exc
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
        elif isinstance(node, ast.Call):
            function_name = ""
            if isinstance(node.func, ast.Name):
                function_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                function_name = node.func.attr
            call_literals: list[str] = []
            for argument in (*node.args, *node.keywords):
                candidate = argument.value if isinstance(argument, ast.keyword) else argument
                literal_parts: list[str] = []
                for child in ast.walk(candidate):
                    if isinstance(child, ast.Constant) and isinstance(
                        child.value, str
                    ):
                        call_literals.append(child.value)
                        literal_parts.append(child.value)
                if literal_parts:
                    call_literals.append("".join(literal_parts))
                try:
                    folded = ast.literal_eval(candidate)
                except (ValueError, TypeError):
                    folded = None
                if isinstance(folded, str):
                    call_literals.append(folded)
            if function_name in {
                "SourceFileLoader",
                "SourcelessFileLoader",
                "__import__",
                "compile",
                "eval",
                "exec",
                "exec_module",
                "get_code",
                "import_module",
                "run_module",
                "run_path",
                "spec_from_file_location",
                "spec_from_loader",
            } and any(
                any(part in value for part in _FORBIDDEN_PARSER_MODULE_PARTS)
                for value in call_literals
            ):
                raise LockedEvaluationError(
                    f"{source_name} contains a forbidden parser execution path"
                )
            if function_name in {
                "__import__",
                "import_module",
                "spec_from_file_location",
            }:
                names.extend(
                    argument.value
                    for argument in node.args
                    if isinstance(argument, ast.Constant)
                    and isinstance(argument.value, str)
                )
            if function_name in {
                "run",
                "Popen",
                "call",
                "check_call",
                "check_output",
            }:
                for argument in node.args:
                    for child in ast.walk(argument):
                        if (
                            isinstance(child, ast.Constant)
                            and isinstance(child.value, str)
                            and any(
                                part in child.value
                                for part in _FORBIDDEN_PARSER_MODULE_PARTS
                            )
                        ):
                            raise LockedEvaluationError(
                                f"{source_name} contains a forbidden parser subprocess"
                            )
        for name in names:
            if any(part in name for part in _FORBIDDEN_PARSER_MODULE_PARTS):
                raise LockedEvaluationError(
                    f"{source_name} references a forbidden parser import: {name}"
                )
            if name == "jspace_observation":
                raise LockedEvaluationError(
                    f"{source_name} imports the normal package graph"
                )


def assert_parser_free_subprocess(paths: Sequence[str | Path]) -> None:
    checked_paths = [str(Path(path).resolve()) for path in paths]
    scanner = (
        "import ast,pathlib,sys;"
        "bad=('eval_'+'parsing','eval_'+'parsing_v2');"
        "trees=[(p,ast.parse(pathlib.Path(p).read_text(encoding='utf-8'))) "
        "for p in sys.argv[1:]];"
        "names=[(p,a.name) for p,t in trees for n in ast.walk(t) "
        "if isinstance(n,(ast.Import,ast.ImportFrom)) "
        "for a in (n.names if isinstance(n,ast.Import) else "
        "[ast.alias(name=n.module or '')])];"
        "violations=[(p,n) for p,n in names "
        "if n=='jspace_observation' or any(x in n for x in bad)];"
        "sys.exit(9 if violations else 0)"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", scanner, *checked_paths],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise LockedEvaluationError("subprocess parser-isolation guard failed")


def forbidden_parser_module_name(name: str) -> bool:
    return name == "jspace_observation" or any(
        part in name for part in _FORBIDDEN_PARSER_MODULE_PARTS
    )


def validate_no_model_gpu_configuration(environment: Mapping[str, str]) -> None:
    forbidden_keys = (
        "HF_HOME",
        "HUGGINGFACE_HUB_CACHE",
        "TRANSFORMERS_CACHE",
        "MODEL_ID",
        "MODEL_PATH",
        "CUDA_VISIBLE_DEVICES",
        "NVIDIA_VISIBLE_DEVICES",
    )
    configured = [key for key in forbidden_keys if environment.get(key)]
    if configured:
        raise LockedEvaluationError(
            "model/GPU environment is prohibited: " + ", ".join(configured)
        )


__all__ = [
    "LockedEvaluationError",
    "PARSER_EVALUATION_PROFILE_SCHEMA_VERSION",
    "DEFAULT_PARSER_EVALUATION_PROFILE_ID",
    "ACTIVE_PARSER_PROFILE_ID",
    "ACTIVE_PARSER_PROFILE",
    "FROZEN_PROTOCOL_COMMIT",
    "FROZEN_PROTOCOL_BUNDLE_SHA256",
    "FROZEN_ACCEPTANCE_GATE_SHA256",
    "FROZEN_PARSER_SOURCE_SHA256",
    "FROZEN_PARSER_GIT_BLOB_OID",
    "FROZEN_PARSER_VERSION",
    "FROZEN_STARTING_COMMIT",
    "FROZEN_PARSER_IMPLEMENTATION_COMMIT",
    "FROZEN_LEGACY_PARSER_COMMIT",
    "FROZEN_LEGACY_PARSER_GIT_BLOB_OID",
    "FROZEN_LEGACY_PARSER_SOURCE_SHA256",
    "RUNTIME_CONFIG_SCHEMA_VERSION",
    "IMAGE_BINDING_SCHEMA_VERSION",
    "IMAGE_BINDING_ESSENTIAL_SCHEMA_VERSION",
    "COORDINATION_BINDING_SCHEMA_VERSION",
    "PRIVATE_DNS_RECORD_SET_API_VERSION",
    "MANAGEMENT_LOCK_API_VERSION",
    "IMAGE_BINDING_SOURCE_PATHS",
    "RUNTIME_SOURCE_BINDING_PATHS",
    "IMPLEMENTATION_MANIFEST_SCHEMA_VERSION",
    "SCORING_TRANSACTION_SCHEMA_VERSION",
    "SCORING_ATTESTATION_SCHEMA_VERSION",
    "SCORING_LEDGER_SCHEMA_VERSION",
    "ABANDONED_ATTEMPT_SCHEMA_VERSION",
    "ATTEMPT_DESCRIPTOR_SCHEMA_VERSION",
    "CLOSURE_MANIFEST_SCHEMA_VERSION",
    "PREDICTION_MEMBER_NAMES",
    "SCORE_MEMBER_NAMES",
    "CONSTRUCTION_STATES",
    "EVALUATION_STATES",
    "HOLDOUT_STATES",
    "HOLDOUT_STATE_SEQUENCE",
    "STATE_AUTHORIZED_ARTIFACT_BINDINGS",
    "EVALUATION_STATE_SEQUENCE",
    "STATE_RECEIPT_FILENAMES",
    "STATE_RETRY_RECEIPT_FILENAMES",
    "IMPLEMENTATION_MANIFEST_FILENAME",
    "RUNTIME_CONFIG_FILENAME",
    "AUTHORIZATION_MANIFEST_FILENAME",
    "CLOSURE_MANIFEST_FILENAME",
    "LABELS_OPEN_TRANSACTION_FILENAME",
    "SCORING_TRANSACTION_FILENAME",
    "SCORING_ATTESTATION_FILENAME",
    "SCORING_LEDGER_FILENAME",
    "SPENT_INCOMPLETE_FILENAME",
    "SCORING_INCOMPLETE_FILENAME",
    "ABANDONED_ATTEMPT_FILENAME",
    "exact_json_equal",
    "max_canonical_utc",
    "canonical_json_bytes",
    "canonical_jsonl_bytes",
    "parse_json_strict",
    "parse_jsonl_strict",
    "sha256_bytes",
    "load_acceptance_gates",
    "load_frozen_gate_bytes",
    "compute_protocol_bundle_sha256",
    "validate_locked_inputs_bytes",
    "project_parser_request",
    "build_prediction_envelope",
    "build_legacy_prediction",
    "validate_prediction_rows",
    "build_prediction_request_manifest",
    "validate_prediction_request_manifest",
    "build_locked_prediction_seal",
    "validate_locked_prediction_seal",
    "build_prediction_artifact_manifest",
    "validate_prediction_artifact_manifest",
    "validate_prediction_artifact_graph",
    "download_prediction_artifacts",
    "score_locked_evaluation",
    "score_locked_evaluation_bytes",
    "build_scoring_ledger_bytes",
    "validate_scoring_ledger_bytes",
    "validate_scoring_ledger_context",
    "render_metrics_csv",
    "bind_metrics_artifacts",
    "validate_metrics_artifact_bindings",
    "validate_metrics_artifact",
    "build_decision",
    "validate_decision",
    "build_retirement_record",
    "validate_retirement_record",
    "build_closure_manifest",
    "render_public_report",
    "build_labels_open_transaction",
    "validate_labels_open_transaction",
    "build_scoring_transaction",
    "validate_scoring_transaction",
    "build_scoring_attestation",
    "validate_scoring_attestation",
    "build_scoring_incomplete_record",
    "validate_scoring_incomplete_record",
    "build_invalid_closure_manifest",
    "validate_invalid_closure_manifest",
    "build_spent_incomplete_record",
    "validate_spent_incomplete_record",
    "validate_state_receipt",
    "state_receipt_sha256",
    "build_sealed_state_receipt",
    "build_next_state_receipt",
    "build_invalid_closed_state_receipt",
    "build_retry_state_receipt",
    "build_provenance_bound_retry_state_receipt",
    "build_strict_retry_state_receipt",
    "build_bound_retry_state_receipt",
    "validate_retry_state_receipt_provenance",
    "validate_retry_state_receipt_binding",
    "abandoned_attempt_retry_visibility",
    "verification_retry_visibility",
    "validate_state_transition",
    "validate_state_receipt_chain",
    "validate_state_receipt_graph",
    "validate_closed_outcome",
    "validate_invalid_closed_outcome",
    "validate_implementation_manifest",
    "validate_authorization_lock",
    "build_authorization_manifest",
    "validate_authorization_manifest",
    "authorization_lock_sha256",
    "authorization_lock_blob_name",
    "derive_holdout_id",
    "build_runtime_configuration",
    "validate_runtime_configuration",
    "validate_coordination_binding",
    "coordination_binding_sha256",
    "validate_image_binding",
    "image_binding_essential_record",
    "authenticate_authorization_bundle",
    "build_visibility_record",
    "validate_visibility_record",
    "validate_managed_identity_configuration",
    "create_blob_service",
    "download_verified_blob",
    "download_stable_blob",
    "upload_blob_once",
    "persist_singleton",
    "persist_or_adopt_exact_singleton",
    "persist_state_receipt",
    "persist_or_adopt_state_receipt",
    "persist_or_adopt_invalid_closure",
    "persist_authorization_manifest",
    "persist_spent_incomplete_record",
    "persist_scoring_incomplete_record",
    "persist_labels_open_transaction",
    "persist_manifest_last_prefix",
    "expected_registered_parent_membership",
    "expected_authorization_attempt_membership",
    "validate_registered_parent_membership",
    "build_score_manifest",
    "validate_score_manifest",
    "build_score_payloads",
    "validate_locked_source_manifest",
    "validate_locked_input_source_binding",
    "authenticate_locked_input_source",
    "validate_locked_labels_manifest",
    "evaluation_prefixes",
    "validate_exact_evaluation_prefix",
    "attempt_binding_sha256",
    "derive_attempt_prefix",
    "derive_evaluation_attempt_prefix",
    "canonical_attempt_prefix",
    "validate_exact_attempt_prefix",
    "validate_scoring_attempt_binding",
    "validate_evaluation_attempt_prefix",
    "validate_attempt_prefix",
    "evaluation_attempt_prefixes",
    "attempt_membership_sha256",
    "abandoned_attempt_membership_sha256",
    "build_attempt_membership_descriptor",
    "build_attempt_descriptor",
    "validate_attempt_membership_descriptor",
    "validate_attempt_descriptor",
    "attempt_membership_descriptor_sha256",
    "build_abandoned_attempt_record",
    "validate_abandoned_attempt_record",
    "abandoned_attempt_sha256",
    "abandoned_attempt_record_sha256",
    "abandoned_attempt_blob_name",
    "derive_abandoned_attempt_blob_name",
    "validate_exact_abandoned_attempt_blob_name",
    "validate_stage_p_environment",
    "validate_stage_e_environment",
    "validate_no_model_gpu_configuration",
    "validate_private_endpoint_resolution",
    "assert_label_blind_payload",
    "assert_parser_free_source",
    "assert_parser_free_subprocess",
    "forbidden_parser_module_name",
]
