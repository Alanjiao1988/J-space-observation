"""Model-free tooling for the frozen Phase 1.2A parser validation protocol."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence, TypedDict


FROZEN_PROTOCOL_COMMIT = "cc93ffe603ab8338ed860586a52b1911af4b3277"
FROZEN_PROTOCOL_BUNDLE_SHA256 = (
    "5d486a53b532012c3a64eb6bd962be325fb9892ebbb042807b919f9e41b23666"
)
FROZEN_ACCEPTANCE_GATE_SHA256 = (
    "a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988"
)
FROZEN_PROTOCOL_COMMIT_UTC = "2026-07-15T18:18:51Z"
PROTOCOL_FILES = (
    "docs/phase1_parser_v2_protocol.md",
    "docs/phase1_evaluator_validation_set.md",
    "docs/phase1_parser_v2_acceptance_gates.json",
)
FROZEN_PROTOCOL_PHASE = "1.2A/Path C"
FROZEN_PROTOCOL_VERSION = "parser-v2-v1.2"
FROZEN_PROTOCOL_FILE_SHA256S = {
    "docs/phase1_evaluator_validation_set.md": (
        "d019c446393bc60dc524178c2a91018ceb8f04f881dcc80018f0282b0919f3f8"
    ),
    "docs/phase1_parser_v2_acceptance_gates.json": (
        "a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988"
    ),
    "docs/phase1_parser_v2_protocol.md": (
        "417d9ff5d27b17ce588b7713a1b1072fb32ef21a03fd135e4e339719db28866b"
    ),
}
PROTOCOL_BUNDLE_HASH_DOMAIN = (
    b"jspace-parser-v2-validation/protocol-bundle/v1\0"
)
CASE_ID_HASH_DOMAIN = b"jspace-parser-v2-validation/case-id/v1\0"
HISTORICAL_SOURCE_HASHES = {
    "phase1_generations.jsonl": (
        "b45c972af6f8a2be771e308d943ff793bdafd44c486a4eae9ea8a4e7f1ec11a0"
    ),
    "phase1_eval_records.jsonl": (
        "57aee97ef98a9be14e489bf6aa4a6e09a80fd5ceedb2df8fadc8d991be98538b"
    ),
}
HISTORICAL_FINGERPRINT_ARTIFACT_HASHES = {
    "historical_output_fingerprints.jsonl": (
        "58adac43e7e825e92d1aa23e062ee6a554a5eedc59274fabdb21685a981839a2"
    ),
    "historical_output_fingerprint_summary.json": (
        "eb076251d30a803d7283d0e17dfda9074c676b3c11ac095ff7d3b586f7fbabdb"
    ),
}

SOURCE_KIND = "constructed_model_free_fixture"
REVIEWER_MODEL_ID = "gpt-5.6-sol"
REVIEWER_REASONING_EFFORT = "max"
SEALED_CURATOR_IDENTITIES = (
    "evaluator-case-curator-a",
    "evaluator-case-curator-b",
)
HISTORICAL_TARGET_MODEL_ID = (
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
)

CANDIDATE_SCHEMA_VERSION = "phase1-parser-v2-candidate/v1"
CURATOR_CANDIDATE_SCHEMA_VERSION = "phase1-parser-v2-curator-candidate/v1"
CURATOR_POOL_SEAL_SCHEMA_VERSION = "phase1-parser-v2-curator-pool-seal/v1"
DEVELOPMENT_SCHEMA_VERSION = "phase1-parser-v2-development-record/v1"
LOCKED_INPUT_SCHEMA_VERSION = "phase1-parser-v2-locked-input/v1"
PARSER_REQUEST_SCHEMA_VERSION = "phase1-parser-v2-request/v1"
PARSER_RESULT_SCHEMA_VERSION = "phase1-parser-v2-result/v1"
PREDICTION_ENVELOPE_SCHEMA_VERSION = "phase1-parser-v2-prediction/v1"
PREDICTION_SEAL_SCHEMA_VERSION = "phase1-parser-v2-prediction-seal/v1"
STAGE1_REVIEW_SCHEMA_VERSION = "phase1-parser-v2-review-stage1/v1"
STAGE1_ARBITRATION_SCHEMA_VERSION = (
    "phase1-parser-v2-arbitration-stage1/v1"
)
STAGE1_CONSENSUS_SCHEMA_VERSION = "phase1-parser-v2-consensus-stage1/v1"
STAGE2_REFERENCE_PACKET_SCHEMA_VERSION = (
    "phase1-parser-v2-stage2-reference-packet/v1"
)
STAGE2_REVIEW_SCHEMA_VERSION = "phase1-parser-v2-review-stage2/v1"
STAGE2_ARBITRATION_SCHEMA_VERSION = (
    "phase1-parser-v2-arbitration-stage2/v1"
)
FINAL_LABEL_SCHEMA_VERSION = "phase1-parser-v2-locked-reference-label/v1"
REVIEW_SEAL_SCHEMA_VERSION = "phase1-parser-v2-review-seal/v1"
SELECTION_PLAN_SCHEMA_VERSION = "phase1-parser-v2-selection-plan/v1"
CURATOR_C_SELECTION_SCHEMA_VERSION = (
    "phase1-parser-v2-curator-c-selection/v1"
)
CURATOR_C_SUMMARY_SCHEMA_VERSION = (
    "phase1-parser-v2-curator-c-summary/v1"
)
HISTORICAL_FINGERPRINT_SCHEMA_VERSION = (
    "phase1-parser-v2-historical-fingerprint/v1"
)
HISTORICAL_FINGERPRINT_SUMMARY_SCHEMA_VERSION = (
    "phase1-parser-v2-historical-fingerprint-summary/v1"
)
PRIVATE_SALTS_SCHEMA_VERSION = "phase1-parser-v2-private-salts/v1"
MAPPING_SCHEMA_VERSION = "phase1-parser-v2-case-mapping/v1"
MANIFEST_SCHEMA_VERSION = "phase1-parser-v2-manifest/v1"
RESERVATION_SCHEMA_VERSION = "phase1-parser-v2-reservation/v1"
VISIBILITY_LEDGER_SCHEMA_VERSION = "phase1-parser-v2-visibility-ledger/v1"
VALIDATION_REPORT_SCHEMA_VERSION = "phase1-parser-v2-validation-set-report/v1"
STATE_RECEIPT_SCHEMA_VERSION = "phase1-parser-v2-state-receipt/v1"
AUTHORIZATION_LOCK_SCHEMA_VERSION = "phase1-parser-v2-authorization-lock/v1"
IMPLEMENTATION_MANIFEST_SCHEMA_VERSION = (
    "phase1-parser-v2-implementation-manifest/v1"
)

REGISTERED_CURATOR_C_ID = "evaluator-case-curator-c"
REGISTERED_CUSTODIAN_ID = "phase1-parser-v2-custodian"
AUTHORIZATION_LOCK_BLOB_PREFIX = (
    "phase1-evaluator-validation/parser-v2-v1/authorization-locks"
)

ELIGIBLE_PRODUCTION_ARTIFACT_SHA256 = {
    "curator_a_candidate_jsonl": (
        "7c0900d1c51d20684faf4cb7fb641c37346768ace177bd60774dcd9faacb65a4"
    ),
    "curator_a_pool_seal": (
        "4b3c247240e10b6de60bca6262fc943fda7a086b3b39cde532daf335fe0b6bc1"
    ),
    "curator_b_candidate_jsonl": (
        "28ccdb24bcb935386664fdb6c292961a0c570f9927b76b7ef73e8706c5fed41c"
    ),
    "curator_b_pool_seal": (
        "454b0ef088b9a10988566544a7db823adeafce714389f7c94da147b53f64bc83"
    ),
    "curator_c_selection": (
        "0555c094735d76b280ef36434d60a1c58f01515a690fcefdb473463e3035a46b"
    ),
    "curator_c_summary": (
        "59385351114068c8260f508d8cc6035fe0358c1062769f2a895770e132402788"
    ),
}
ELIGIBLE_PRODUCTION_CURATOR_C_SUMMARY_COUNTS = {
    "candidate_pool_total": 288,
    "development": 60,
    "duplicate_groups_observed": 3,
    "excluded_duplicate_ids": 3,
    "locked": 120,
    "near_duplicate_flags": 37,
    "near_duplicate_non_s12_flags": 3,
    "selected_exact_duplicates": 0,
    "selected_frozen_normalized_duplicates": 0,
    "selected_total": 180,
    "template_family_overlaps": 0,
    "unselected": 108,
}

STRATA = tuple(f"S{number:02d}" for number in range(1, 13))
ANSWER_BEARING_STRATA = (
    "S01",
    "S02",
    "S03",
    "S04",
    "S05",
    "S06",
    "S09",
    "S12",
)
CLEAN_STRATA = ("S01", "S02", "S03", "S12")
CRITICAL_STRATA = ("S04", "S05", "S06", "S07", "S08", "S09", "S10", "S11")
NO_ANSWER_STRATA = ("S07", "S08", "S10")
AMBIGUOUS_STRATUM = "S11"

SUBTYPE_SLOTS = {
    "S01": (
        "inline_box",
        "display_math_box",
        "spaced_box",
        "math_delimited_box",
        "trailing_punctuation",
    ),
    "S02": (
        "answer_marker",
        "final_answer_marker",
        "the_answer_is",
        "final_marker",
        "case_colon_newline_variant",
    ),
    "S03": (
        "plain_infix",
        "parenthesized",
        "chained_equivalent",
        "latex",
        "prose_then_terminal_equation",
    ),
    "S04": (
        "numbered_steps",
        "multiline_equations",
        "prose_sequence",
        "mixed_prose_math",
        "balanced_think_working",
    ),
    "S05": (
        "verbal_verification",
        "equation_check",
        "reconsideration",
        "rejected_alternative",
        "tagged_continuation",
    ),
    "S06": (
        "trailing_step_number",
        "rating_or_confidence",
        "check_operand",
        "count_or_metadata",
        "explicitly_rejected_alternative",
    ),
    "S07": (
        "cut_before_marker",
        "empty_marker",
        "missing_equation_rhs",
        "incomplete_box",
        "unclosed_reasoning_tag",
    ),
    "S08": (
        "empty_or_empty_wrapper",
        "ellipsis_or_na",
        "refusal_without_numbers",
        "refusal_with_incidental_number",
        "task_echo",
    ),
    "S09": (
        "extra_delimiter",
        "doubled_marker_punctuation",
        "broken_latex_wrapper",
        "stray_tag",
        "encoding_or_markup_noise",
    ),
    "S10": (
        "corrupted_box",
        "broken_marker",
        "corrupted_equation",
        "tag_mixed_fragments",
        "invalid_numeric_form",
    ),
    "S11": (
        "two_markers",
        "two_boxes",
        "marker_box_conflict",
        "incompatible_terminal_equations",
        "two_unranked_final_claims",
    ),
    "S12": (
        "positive_signed_integer",
        "negative_integer",
        "positive_decimal",
        "negative_decimal",
        "fraction",
    ),
}

PROTOCOL_SUBTYPE_LABELS = {
    "S01": (
        "inline box",
        "display-math box",
        "spaced box",
        "math-delimited box",
        "trailing punctuation",
    ),
    "S02": (
        "Answer:",
        "Final answer:",
        "The answer is",
        "Final:",
        "case/colon/newline variant",
    ),
    "S03": (
        "plain infix",
        "parenthesized",
        "chained equivalent",
        "LaTeX",
        "prose lead-in then terminal equation",
    ),
    "S04": (
        "numbered steps",
        "multiline equations",
        "prose sequence",
        "mixed prose/math",
        "balanced think working with final outside",
    ),
    "S05": (
        "verbal verification",
        "equation check",
        "reconsideration",
        "rejected alternative",
        "tagged continuation",
    ),
    "S06": (
        "trailing step number",
        "rating/confidence",
        "check operand",
        "count/metadata",
        "explicitly rejected alternative",
    ),
    "S07": (
        "cut before marker",
        "empty marker",
        "missing equation RHS",
        "incomplete box",
        "unclosed reasoning tag",
    ),
    "S08": (
        "empty/empty-wrapper",
        "ellipsis/N/A",
        "refusal without numbers",
        "refusal with incidental number",
        "task echo",
    ),
    "S09": (
        "extra delimiter",
        "doubled marker punctuation",
        "broken LaTeX wrapper",
        "stray tag",
        "encoding/markup noise",
    ),
    "S10": (
        "corrupted box",
        "broken marker",
        "corrupted equation",
        "tag-mixed fragments",
        "invalid numeric form",
    ),
    "S11": (
        "two markers",
        "two boxes",
        "marker-box conflict",
        "incompatible terminal equations",
        "two unranked final claims",
    ),
    "S12": (
        "positive signed integer",
        "negative integer",
        "positive decimal",
        "negative decimal",
        "fraction",
    ),
}
CURATOR_A_SUBTYPE_ALIASES = {
    "S02": {
        "answer_colon": "answer_marker",
        "final_answer": "final_answer_marker",
        "the_answer_is": "the_answer_is",
        "final_marker": "final_marker",
        "case_colon_newline_variant": "case_colon_newline_variant",
    },
    "S03": {
        "prose_lead_in_terminal_equation": "prose_then_terminal_equation",
    },
    "S04": {
        "balanced_think_working_final_outside": "balanced_think_working",
    },
    "S06": {
        "rating_confidence": "rating_or_confidence",
        "count_metadata": "count_or_metadata",
    },
    "S08": {
        "empty_wrapper": "empty_or_empty_wrapper",
        "ellipsis_na": "ellipsis_or_na",
    },
    "S09": {
        "encoding_markup_noise": "encoding_or_markup_noise",
    },
}
SUBTYPE_SLOT_ALIASES = {
    stratum: {
        **{slot: slot for slot in SUBTYPE_SLOTS[stratum]},
        **dict(
            zip(
                PROTOCOL_SUBTYPE_LABELS[stratum],
                SUBTYPE_SLOTS[stratum],
                strict=True,
            )
        ),
        **CURATOR_A_SUBTYPE_ALIASES.get(stratum, {}),
    }
    for stratum in STRATA
}

SECONDARY_TAGS = (
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
)
EXTERNAL_SECONDARY_TAG_ALIASES = {
    "balanced_think_tag": "balanced_think_tags",
    "balanced_think_tags": "balanced_think_tags",
    "decimal_surface": "decimal_surface",
    "fraction_surface": "fraction_surface",
    "incidental_numeric_distractor": "incidental_numeric_distractor",
    "malformed_think_tag": "malformed_think_tags",
    "malformed_think_tags": "malformed_think_tags",
    "multiple_numeric_mentions": "multiple_numeric_mentions",
    "negative_answer": "negative_answer",
    "noncanonical_numeric_surface": "noncanonical_numeric_surface",
    "reasoning_continues_after_answer": "continued_reasoning",
    "rightmost_numeric_distractor": "last_number_distractor",
    "signed_surface": "signed_numeric_surface",
}
EXTERNAL_SECONDARY_TAGS = tuple(EXTERNAL_SECONDARY_TAG_ALIASES)
QUOTA_DIAGNOSTIC_TAGS = frozenset(
    {
        "signed_numeric_surface",
        "negative_answer",
        "decimal_surface",
        "fraction_surface",
        "balanced_think_tags",
        "malformed_think_tags",
        "incidental_numeric_distractor",
    }
)

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
EXPECTED_PRESENCE = ("present", "ambiguous", "no_answer")
PARSER_PRESENCE = ("present", "absent", "uncertain")
REVIEW_PRESENCE = (*PARSER_PRESENCE, "inconclusive")
STAGE2_CORRECTNESS = ("correct", "incorrect", "inconclusive")
TYPED_DECISION_CLASSES = ("present", "ambiguous", "no_answer")
MAX_NUMERIC_LITERAL_CHARACTERS = 100
MAX_CANONICAL_NUMERIC_CHARACTERS = 4096

PROHIBITED_OUTPUT_PREFIXES = (
    "phase1-limited-n3-gates/20260710T152820Z",
    "phase1-semantic-audits/all45-parser-underflag-20260715T094500Z",
)

REGISTERED_LEAF_MEMBERS = {
    "development": (
        ".development_reservation.json",
        "development_cases.jsonl",
        "development_manifest.json",
    ),
    "locked-inputs": (
        ".locked_inputs_reservation.json",
        "locked_inputs.jsonl",
        "locked_inputs_manifest.json",
    ),
    "locked-labels": (
        ".locked_labels_reservation.json",
        "reviewer_a_stage1.jsonl",
        "reviewer_b_stage1.jsonl",
        "arbitration_stage1.jsonl",
        "stage1_consensus.jsonl",
        "stage2_reference_packet.jsonl",
        "reviewer_a_stage2.jsonl",
        "reviewer_b_stage2.jsonl",
        "arbitration_stage2.jsonl",
        "locked_reference_labels.jsonl",
        "locked_labels_manifest.json",
    ),
    "reports": (
        ".reports_reservation.json",
        "validation_set_report.json",
        "validation_set_report.md",
        "reports_manifest.json",
    ),
    "manifests": (
        ".locked_manifest_reservation.json",
        "locked_case_mapping.json",
        "visibility_ledger.jsonl",
        "overlap_report.json",
        "locked_manifest.json",
    ),
}

CONSTRUCTION_STATES = (
    "DRAFT_PROTOCOL",
    "PROTOCOL_FROZEN",
    "PRIVATE_CONSTRUCTION",
    "RESERVED",
    "PAYLOAD_COMPLETE",
    "SEALED",
)
EVALUATION_STATES = (
    "IMPLEMENTATION_FROZEN",
    "UNSEAL_AUTHORIZED",
    "INPUTS_READ",
    "PREDICTIONS_VERIFIED",
    "LABELS_READ",
    "SCORES_VERIFIED",
    "CLOSED",
)
HOLDOUT_STATES = (*CONSTRUCTION_STATES, *EVALUATION_STATES)

_DECIMAL_PATTERN = re.compile(
    r"[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))(?:[eE][+-]?[0-9]+)?\Z",
    re.ASCII,
)
_FRACTION_PATTERN = re.compile(r"[+-]?[0-9]+/[0-9]+\Z", re.ASCII)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z", re.ASCII)
_OCI_IMAGE_DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)
_CASE_ID_PATTERN = re.compile(r"PV2-[0-9a-f]{20}\Z", re.ASCII)
_REGISTERED_PARENT_PATTERN = re.compile(
    r"phase1-evaluator-validation/parser-v2-v1/"
    r"([0-9]{8}T[0-9]{6}Z)\Z",
    re.ASCII,
)
_CANDIDATE_ID_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z", re.ASCII
)
_UTC_PATTERN = re.compile(
    r"[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])"
    r"T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z\Z",
    re.ASCII,
)
_NUMERIC_MASK_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:[+-]?[0-9]+/[0-9]+|"
    r"[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))"
    r"(?:[eE][+-]?[0-9]+)?)"
    r"(?![A-Za-z0-9_])",
    re.ASCII,
)
class ValidationSetError(ValueError):
    """Raised when an artifact violates the frozen validation-set protocol."""


class EvidenceSpan(TypedDict):
    start: int
    end: int
    text: str
    kind: str
    normalized_answer: str
    disposition: str


class AcceptableSpan(TypedDict):
    start: int
    end: int
    text: str


class LockedInput(TypedDict):
    schema_version: str
    case_id: str
    source_kind: str
    output_text: str
    parse_type: str


class ParserRequest(TypedDict):
    schema_version: str
    answer_type: str
    output_text: str


class DevelopmentRecord(TypedDict):
    schema_version: str
    case_id: str
    source_kind: str
    stratum: str
    secondary_tags: list[str]
    output_text: str
    parse_type: str
    expected_answer_presence: str
    expected_parse_valid: bool
    expected_parse_ambiguous: bool
    expected_parsed_answer: str | None
    expected_candidate_answers: list[str]
    expected_evidence_spans: list[EvidenceSpan]
    expected_extraction_strategy: str
    expected_output_quality: str
    expected_failure_reasons: list[str]
    expected_format_warnings: list[str]
    registered_reference_answer: str
    expected_correctness: bool
    critical_case: bool
    material_error_if_missed: bool
    curation_notes: str


class CandidateFixture(TypedDict):
    schema_version: str
    candidate_id: str
    curator_id: str
    source_kind: str
    stratum: str
    subtype_slot: str
    secondary_tags: list[str]
    output_text: str
    parse_type: str
    expected_answer_presence: str
    expected_parse_valid: bool
    expected_parse_ambiguous: bool
    expected_parsed_answer: str | None
    expected_candidate_answers: list[str]
    expected_evidence_spans: list[EvidenceSpan]
    expected_extraction_strategy: str
    expected_output_quality: str
    expected_failure_reasons: list[str]
    expected_format_warnings: list[str]
    registered_reference_answer: str
    expected_correctness: bool
    critical_case: bool
    material_error_if_missed: bool
    curation_notes: str
    acceptable_selected_spans: list[AcceptableSpan]
    last_number_distractor_span: AcceptableSpan | None
    template_family_id: str
    construction_provenance: str


class CuratorCandidateProposal(TypedDict):
    candidate_id: str
    candidate_schema_version: str
    construction_notes: str
    critical_case: bool
    curator_id: str
    material_error_if_missed: bool
    output_text: str
    parse_type: str
    proposed_expected_answer_presence: str
    proposed_expected_candidate_answers: list[str]
    proposed_expected_correctness: bool
    proposed_expected_evidence_spans: list[EvidenceSpan]
    proposed_expected_extraction_strategy: str
    proposed_expected_failure_reasons: list[str]
    proposed_expected_format_warnings: list[str]
    proposed_expected_output_quality: str
    proposed_expected_parse_ambiguous: bool
    proposed_expected_parse_valid: bool
    proposed_expected_parsed_answer: str | None
    registered_reference_answer: str
    secondary_tags: list[str]
    source_kind: str
    stratum: str
    subtype_slot: str
    template_family_id: str


class CuratorPoolNoModelAttestationA(TypedDict):
    fixtures_constructed_model_free: bool
    network_access_used: bool
    target_model_downloaded_or_loaded: bool
    target_model_inference_performed: bool


class CuratorPoolNoModelAttestationB(TypedDict):
    target_model_downloaded: bool
    target_model_id: str
    target_model_inference_run: bool
    target_model_loaded: bool


class CuratorCNoModelAttestation(TypedDict):
    fixtures_constructed_model_free: bool
    new_cases_generated_by_curator_c: bool
    target_model_downloaded: bool
    target_model_id: str
    target_model_inference_run: bool
    target_model_loaded: bool


ExternalCuratorPoolNoModelAttestation = (
    CuratorPoolNoModelAttestationA | CuratorPoolNoModelAttestationB
)


class CuratorPoolSeal(TypedDict):
    schema_version: str
    curator_id: str
    curator_model_id: str
    curator_reasoning_effort: str
    protocol_commit: str
    protocol_bundle_sha256: str
    acceptance_gate_sha256: str
    candidate_schema_version: str
    candidate_count: int
    ordered_candidate_ids_sha256: str
    candidate_jsonl_sha256: str
    constructed_after_protocol_utc: str
    no_model_run_attestation: ExternalCuratorPoolNoModelAttestation


class CuratorCDispositions(TypedDict):
    selected_development_candidate_ids: list[str]
    selected_locked_candidate_ids: list[str]
    not_selected_duplicate_exclusion_candidate_ids: list[str]
    not_selected_alternative_candidate_ids: list[str]


class CuratorCSelectedCandidateIds(TypedDict):
    development: list[str]
    locked: list[str]


class CuratorCSelectionArtifact(TypedDict):
    actual_derived_feature_counts: dict[str, Any]
    candidate_dispositions: CuratorCDispositions
    candidate_jsonl_sha256s: dict[str, str]
    constructed_after_protocol_utc: str
    construction_intent_warning: str
    count_tables: dict[str, Any]
    curator_id: str
    curator_model_id: str
    curator_reasoning_effort: str
    excluded_duplicate_groups: list[Any]
    excluded_duplicate_ids: list[str]
    feature_derivation: dict[str, Any] | str
    final_protocol_bindings: dict[str, Any]
    locked_label_status: str
    near_duplicate_screening: dict[str, Any]
    no_model_run_attestation: CuratorCNoModelAttestation
    overlap_validation: dict[str, Any]
    pool_seal_sha256s: dict[str, str]
    pool_summary_sha256s: dict[str, str]
    pool_validation: dict[str, Any]
    quota_validation: dict[str, Any]
    schema_version: str
    selected_temp_candidate_ids: CuratorCSelectedCandidateIds
    status: str


class CuratorCSummaryCounts(TypedDict):
    candidate_pool_total: int
    development: int
    duplicate_groups_observed: int
    excluded_duplicate_ids: int
    locked: int
    near_duplicate_flags: int
    near_duplicate_non_s12_flags: int
    selected_exact_duplicates: int
    selected_frozen_normalized_duplicates: int
    selected_total: int
    template_family_overlaps: int
    unselected: int


class CuratorCSummaryHashes(TypedDict):
    candidate_jsonl_sha256s: dict[str, str]
    pool_seal_sha256s: dict[str, str]
    selection_sha256: str


class CuratorCSummaryArtifact(TypedDict):
    constructed_after_protocol_utc: str
    counts: CuratorCSummaryCounts
    curator_id: str
    curator_model_id: str
    curator_reasoning_effort: str
    hashes: CuratorCSummaryHashes
    protocol_bindings: dict[str, str]
    schema_version: str
    status: str


class HistoricalFingerprintRow(TypedDict):
    source: str
    exact_sha256: str
    normalized_sha256: str


class HistoricalFingerprintSummary(TypedDict):
    schema_version: str
    fingerprint_schema_version: str
    status: str
    protocol_commit: str
    source_artifact_sha256s: dict[str, str]
    fingerprint_jsonl_sha256: str
    fingerprint_count: int
    contains_historical_text: bool


_EXTERNAL_NO_MODEL_ATTESTATION_VARIANTS: dict[
    str, dict[str, bool | str]
] = {
    "curator_pool_a": {
        "fixtures_constructed_model_free": True,
        "network_access_used": False,
        "target_model_downloaded_or_loaded": False,
        "target_model_inference_performed": False,
    },
    "curator_pool_b": {
        "target_model_downloaded": False,
        "target_model_id": HISTORICAL_TARGET_MODEL_ID,
        "target_model_inference_run": False,
        "target_model_loaded": False,
    },
    "curator_c_selection": {
        "fixtures_constructed_model_free": True,
        "new_cases_generated_by_curator_c": False,
        "target_model_downloaded": False,
        "target_model_id": HISTORICAL_TARGET_MODEL_ID,
        "target_model_inference_run": False,
        "target_model_loaded": False,
    },
}
_EXTERNAL_ATTESTATION_CONTEXT_VARIANTS = {
    "curator_pool": ("curator_pool_a", "curator_pool_b"),
    "curator_c_selection": ("curator_c_selection",),
}


class Stage1ReviewRow(TypedDict):
    schema_version: str
    review_stage: str
    case_id: str
    reviewer_id: str
    reviewer_model_id: str
    reviewer_reasoning_effort: str
    packet_sha256: str
    answer_presence: str
    parse_valid: bool | None
    parse_ambiguous: bool | None
    parsed_answer: str | None
    candidate_answers: list[str]
    evidence_spans: list[EvidenceSpan]
    extraction_strategy: str | None
    output_quality: str | None
    failure_reasons: list[str]
    format_warnings: list[str]
    notes: str


class Stage2ReviewRow(TypedDict):
    schema_version: str
    review_stage: str
    case_id: str
    reviewer_id: str
    reviewer_model_id: str
    reviewer_reasoning_effort: str
    packet_sha256: str
    stage1_consensus_sha256: str
    stage2_reference_packet_sha256: str
    correctness: str
    critical_case: bool | None
    material_error_if_missed: bool | None
    notes: str


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 digest of exact bytes."""
    if not isinstance(data, bytes):
        raise ValidationSetError("SHA-256 input must be bytes")
    return hashlib.sha256(data).hexdigest()


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ValidationSetError(f"non-Unicode-scalar string at {path}")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationSetError(f"non-finite JSON number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationSetError(f"non-string JSON key at {path}")
            if any(0xD800 <= ord(character) <= 0xDFFF for character in key):
                raise ValidationSetError(f"non-Unicode-scalar JSON key at {path}")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise ValidationSetError(
        f"unsupported JSON value type at {path}: {type(value).__name__}"
    )


def canonical_json_text(value: Any) -> str:
    """Serialize a value as compact, sorted-key ASCII JSON."""
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
        raise ValidationSetError(
            f"value is not canonical-JSON serializable: {exc}"
        ) from exc


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize one canonical JSON value with a terminal LF."""
    return (canonical_json_text(value) + "\n").encode("ascii")


def canonical_jsonl_bytes(records: Sequence[Mapping[str, Any]]) -> bytes:
    """Serialize canonical JSON objects one per physical line with terminal LF."""
    if not isinstance(records, Sequence) or isinstance(
        records, (str, bytes, bytearray)
    ):
        raise ValidationSetError("JSONL records must be a sequence")
    if not records:
        return b""
    rendered: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValidationSetError(f"JSONL record {index} must be an object")
        rendered.append(canonical_json_text(dict(record)))
    return ("\n".join(rendered) + "\n").encode("ascii")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationSetError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValidationSetError(f"non-finite JSON value: {value}")


def parse_json_strict(
    data: bytes, artifact_name: str, *, require_canonical: bool = True
) -> dict[str, Any]:
    """Parse one strict UTF-8 JSON object and optionally require canonical bytes."""
    if not isinstance(data, bytes):
        raise ValidationSetError(f"{artifact_name} input must be bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationSetError(f"{artifact_name} is not UTF-8: {exc}") from exc
    if not data.endswith(b"\n"):
        raise ValidationSetError(f"{artifact_name} must end with LF")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (ValueError, ValidationSetError) as exc:
        raise ValidationSetError(f"{artifact_name} has invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationSetError(f"{artifact_name} must contain one JSON object")
    _validate_json_value(value)
    if require_canonical and data != canonical_json_bytes(value):
        raise ValidationSetError(f"{artifact_name} is not canonical ASCII JSON")
    return value


def parse_jsonl_strict(
    data: bytes,
    artifact_name: str,
    *,
    require_canonical: bool = True,
    allow_empty: bool = False,
) -> list[dict[str, Any]]:
    """Parse strict UTF-8 JSONL with duplicate-key and non-finite rejection."""
    if not isinstance(data, bytes):
        raise ValidationSetError(f"{artifact_name} input must be bytes")
    if not data:
        if allow_empty:
            return []
        raise ValidationSetError(f"{artifact_name} must not be empty")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationSetError(f"{artifact_name} is not UTF-8: {exc}") from exc
    if not data.endswith(b"\n"):
        raise ValidationSetError(f"{artifact_name} must end with LF")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            raise ValidationSetError(
                f"{artifact_name} contains a blank physical line at {line_number}"
            )
        try:
            value = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite,
            )
        except (ValueError, ValidationSetError) as exc:
            raise ValidationSetError(
                f"{artifact_name} has invalid JSON on line {line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise ValidationSetError(
                f"{artifact_name} line {line_number} must be a JSON object"
            )
        _validate_json_value(value)
        records.append(value)
    if require_canonical and data != canonical_jsonl_bytes(records):
        raise ValidationSetError(f"{artifact_name} is not canonical ASCII JSONL")
    return records


def _require_exact_fields(
    value: Mapping[str, Any], fields: Iterable[str], name: str
) -> None:
    if not isinstance(value, Mapping):
        raise ValidationSetError(f"{name} must be an object")
    expected = frozenset(fields)
    actual = frozenset(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise ValidationSetError(
            f"{name} fields differ; missing={missing}, extra={extra}"
        )


def _require_string(
    value: Any, name: str, *, nonempty: bool = True, maximum: int | None = None
) -> str:
    if not isinstance(value, str):
        raise ValidationSetError(f"{name} must be a string")
    if nonempty and not value:
        raise ValidationSetError(f"{name} must not be empty")
    if maximum is not None and len(value) > maximum:
        raise ValidationSetError(f"{name} exceeds {maximum} characters")
    return value


def _require_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValidationSetError(f"{name} must be a boolean")
    return value


def _require_optional_bool(value: Any, name: str) -> bool | None:
    if value is None:
        return None
    return _require_bool(value, name)


def _require_int(value: Any, name: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise ValidationSetError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValidationSetError(f"{name} must be at least {minimum}")
    return value


def _require_enum(value: Any, allowed: Sequence[str], name: str) -> str:
    checked = _require_string(value, name)
    if checked not in allowed:
        raise ValidationSetError(f"{name} has invalid value: {checked}")
    return checked


def _require_sha256(value: Any, name: str, *, allow_zero: bool = False) -> str:
    checked = _require_string(value, name)
    if not _SHA256_PATTERN.fullmatch(checked) or (
        not allow_zero and checked == "0" * 64
    ):
        raise ValidationSetError(f"{name} must be a lowercase SHA-256 digest")
    return checked


def _require_commit(value: Any, name: str) -> str:
    checked = _require_string(value, name)
    if not _COMMIT_PATTERN.fullmatch(checked) or checked == "0" * 40:
        raise ValidationSetError(
            f"{name} must be a nonzero lowercase 40-character Git commit"
        )
    return checked


def _require_image_digest(value: Any, name: str) -> str:
    checked = _require_string(value, name)
    if not _OCI_IMAGE_DIGEST_PATTERN.fullmatch(checked) or checked == (
        "sha256:" + "0" * 64
    ):
        raise ValidationSetError(
            f"{name} must be a nonzero immutable OCI sha256 digest"
        )
    return checked


def _require_case_id(value: Any, name: str = "case_id") -> str:
    checked = _require_string(value, name)
    if not _CASE_ID_PATTERN.fullmatch(checked):
        raise ValidationSetError(f"{name} must match PV2-<20 lowercase hex>")
    return checked


def _require_utc_timestamp(value: Any, name: str) -> str:
    checked = _require_string(value, name)
    if not _UTC_PATTERN.fullmatch(checked):
        raise ValidationSetError(f"{name} must be whole-second UTC")
    try:
        datetime.strptime(checked, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValidationSetError(f"{name} is not a valid UTC date/time") from exc
    return checked


def validate_external_no_model_run_attestation(
    value: Any,
    *,
    context: Literal["curator_pool", "curator_c_selection"],
    name: str = "external no-model-run attestation",
) -> dict[str, Any]:
    """Validate one exact registered production-ingress attestation object."""
    if context not in _EXTERNAL_ATTESTATION_CONTEXT_VARIANTS:
        raise ValidationSetError(f"{name} context is not registered")
    if not isinstance(value, Mapping):
        raise ValidationSetError(f"{name} must be a structured object")
    actual_fields = frozenset(value)
    matching_variants = [
        variant
        for variant in _EXTERNAL_ATTESTATION_CONTEXT_VARIANTS[context]
        if actual_fields
        == frozenset(_EXTERNAL_NO_MODEL_ATTESTATION_VARIANTS[variant])
    ]
    if len(matching_variants) != 1:
        raise ValidationSetError(
            f"{name} fields do not match one exact registered {context} variant"
        )
    expected = _EXTERNAL_NO_MODEL_ATTESTATION_VARIANTS[
        matching_variants[0]
    ]
    checked: dict[str, Any] = {}
    for field, expected_value in expected.items():
        actual = value[field]
        field_name = f"{name}.{field}"
        if type(expected_value) is bool:
            if type(actual) is not bool or actual is not expected_value:
                raise ValidationSetError(
                    f"{field_name} does not prove model-free construction"
                )
            checked[field] = actual
            continue
        checked_value = _require_string(actual, field_name)
        if checked_value != HISTORICAL_TARGET_MODEL_ID:
            raise ValidationSetError(
                f"{field_name} must equal the full registered target model ID"
            )
        checked[field] = checked_value
    return checked


def _require_unique_ordered_enum_list(
    value: Any, allowed: Sequence[str], name: str
) -> list[str]:
    if not isinstance(value, list):
        raise ValidationSetError(f"{name} must be a list")
    result: list[str] = []
    previous = -1
    for index, item in enumerate(value):
        checked = _require_enum(item, allowed, f"{name}[{index}]")
        order = allowed.index(checked)
        if checked in result:
            raise ValidationSetError(f"{name} contains duplicate value: {checked}")
        if order <= previous:
            raise ValidationSetError(f"{name} is not in registered order")
        previous = order
        result.append(checked)
    return result


def _divide_decimal_string_small(value: str, divisor: int) -> tuple[str, int]:
    quotient: list[str] = []
    remainder = 0
    for character in value:
        remainder = remainder * 10 + (ord(character) - ord("0"))
        digit, remainder = divmod(remainder, divisor)
        if quotient or digit:
            quotient.append(chr(ord("0") + digit))
    return "".join(quotient) or "0", remainder


def _multiply_decimal_string_small(value: str, multiplier: int) -> str:
    carry = 0
    rendered: list[str] = []
    for character in reversed(value):
        product = (ord(character) - ord("0")) * multiplier + carry
        carry, digit = divmod(product, 10)
        rendered.append(chr(ord("0") + digit))
    while carry:
        carry, digit = divmod(carry, 10)
        rendered.append(chr(ord("0") + digit))
    return "".join(reversed(rendered))


def _negative_power_canonical_length(
    core_digits: str, denominator_power: int, negative: bool
) -> int:
    """Compute reduced-rational rendering length using bounded decimal strings."""
    divisor = 2 if core_digits[-1] in "02468" else 5 if core_digits[-1] == "5" else 0
    quotient = core_digits
    cancelled = 0
    if divisor:
        while cancelled < denominator_power:
            next_quotient, remainder = _divide_decimal_string_small(
                quotient, divisor
            )
            if remainder:
                break
            quotient = next_quotient
            cancelled += 1
    opposite_factor = 5 if divisor == 2 else 2 if divisor == 5 else 1
    denominator_leading = "1"
    for _ in range(cancelled):
        denominator_leading = _multiply_decimal_string_small(
            denominator_leading, opposite_factor
        )
    denominator_length = len(denominator_leading) + (
        denominator_power - cancelled
    )
    numerator_length = len(quotient) + (1 if negative else 0)
    return numerator_length + 1 + denominator_length


def normalize_rational_literal(value: str) -> str:
    """Normalize one registered decimal/scientific or integer fraction exactly."""
    if not isinstance(value, str):
        raise ValidationSetError("numeric literal must be a string")
    if not value:
        raise ValidationSetError("numeric literal must not be empty")
    if len(value) > MAX_NUMERIC_LITERAL_CHARACTERS:
        raise ValidationSetError(
            f"numeric literal exceeds {MAX_NUMERIC_LITERAL_CHARACTERS} ASCII characters"
        )
    if any(ord(character) > 127 for character in value):
        raise ValidationSetError("numeric literal must use ASCII")

    if _FRACTION_PATTERN.fullmatch(value):
        numerator_text, denominator_text = value.split("/", 1)
        try:
            numerator = int(numerator_text, 10)
            denominator = int(denominator_text, 10)
        except ValueError as exc:
            raise ValidationSetError("fraction components are unsupported") from exc
        if denominator == 0:
            raise ValidationSetError("fraction denominator must not be zero")
        rational = Fraction(numerator, denominator)
    elif _DECIMAL_PATTERN.fullmatch(value):
        mantissa, exponent_text = (
            re.split(r"[eE]", value, maxsplit=1) + [None]
        )[:2]
        exponent = _parse_bounded_exponent(
            exponent_text,
            MAX_CANONICAL_NUMERIC_CHARACTERS
            + MAX_NUMERIC_LITERAL_CHARACTERS,
        )
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
        trailing_zero_count = len(significant) - len(significant.rstrip("0"))
        core_digits = significant.rstrip("0")
        power = exponent - len(fractional) + trailing_zero_count
        try:
            if power >= 0:
                rendered = ("-" if sign < 0 else "") + core_digits
                canonical_length = len(rendered) + power
                if canonical_length > MAX_CANONICAL_NUMERIC_CHARACTERS:
                    raise ValidationSetError(
                        "canonical numeric representation exceeds "
                        f"{MAX_CANONICAL_NUMERIC_CHARACTERS} characters"
                    )
                return rendered + ("0" * power)
            else:
                denominator_power = -power
                if denominator_power > (
                    MAX_CANONICAL_NUMERIC_CHARACTERS
                    + MAX_NUMERIC_LITERAL_CHARACTERS
                ):
                    raise ValidationSetError(
                        "canonical numeric representation exceeds "
                        f"{MAX_CANONICAL_NUMERIC_CHARACTERS} characters"
                    )
                canonical_length = _negative_power_canonical_length(
                    core_digits, denominator_power, sign < 0
                )
                if canonical_length > MAX_CANONICAL_NUMERIC_CHARACTERS:
                    raise ValidationSetError(
                        "canonical numeric representation exceeds "
                        f"{MAX_CANONICAL_NUMERIC_CHARACTERS} characters"
                    )
                core = int(core_digits, 10)
                rational = Fraction(sign * core, 10**denominator_power)
        except ValidationSetError:
            raise
        except (MemoryError, OverflowError, ValueError) as exc:
            raise ValidationSetError(
                "numeric literal cannot be normalized within registered bounds"
            ) from exc
    else:
        raise ValidationSetError(
            "value does not match the registered decimal/scientific or fraction grammar"
        )

    if rational.numerator == 0:
        rendered = "0"
    elif rational.denominator == 1:
        rendered = str(rational.numerator)
    else:
        rendered = f"{rational.numerator}/{rational.denominator}"
    if len(rendered) > MAX_CANONICAL_NUMERIC_CHARACTERS:
        raise ValidationSetError(
            "canonical numeric representation exceeds "
            f"{MAX_CANONICAL_NUMERIC_CHARACTERS} characters"
        )
    return rendered


def _parse_bounded_exponent(value: str | None, maximum_absolute: int) -> int:
    """Parse a signed exponent only after a length/lexical bound preflight."""
    if value is None:
        return 0
    sign = -1 if value.startswith("-") else 1
    digits = value.lstrip("+-").lstrip("0") or "0"
    limit = str(maximum_absolute)
    if len(digits) > len(limit) or (
        len(digits) == len(limit) and digits > limit
    ):
        raise ValidationSetError(
            "canonical numeric representation exceeds "
            f"{MAX_CANONICAL_NUMERIC_CHARACTERS} characters"
        )
    return sign * int(digits, 10)


normalize_numeric_answer = normalize_rational_literal


def _require_canonical_numeric(value: Any, name: str) -> str:
    checked = _require_string(value, name)
    normalized = normalize_rational_literal(checked)
    if checked != normalized:
        raise ValidationSetError(f"{name} must already be canonical: {normalized}")
    return checked


def git_blob_bytes(
    project_root: str | Path, commit: str, relative_path: str
) -> bytes:
    """Read exact Git-blob bytes, independent of checkout line endings."""
    root = Path(project_root).resolve()
    commit = _require_commit(commit, "protocol commit")
    relative = _require_string(relative_path, "relative_path")
    normalized = relative.replace("\\", "/")
    if (
        normalized.startswith("/")
        or normalized != relative
        or any(part in {"", ".", ".."} for part in normalized.split("/"))
    ):
        raise ValidationSetError("relative_path must be a normalized repository path")
    completed = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{normalized}"],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise ValidationSetError(
            f"Git blob is unavailable at {commit}:{normalized}"
        )
    return completed.stdout


def protocol_bundle_sha256(
    project_root: str | Path, commit: str = FROZEN_PROTOCOL_COMMIT
) -> str:
    """Hash the registered ordered frozen Git-blob bundle."""
    digest = hashlib.sha256()
    digest.update(PROTOCOL_BUNDLE_HASH_DOMAIN)
    for relative in PROTOCOL_FILES:
        content = git_blob_bytes(project_root, commit, relative)
        path_bytes = relative.encode("ascii")
        digest.update(len(path_bytes).to_bytes(4, "big"))
        digest.update(path_bytes)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    result = digest.hexdigest()
    if commit == FROZEN_PROTOCOL_COMMIT and result != FROZEN_PROTOCOL_BUNDLE_SHA256:
        raise ValidationSetError("frozen protocol bundle hash is not the final binding")
    return result


def acceptance_gates_sha256(
    project_root: str | Path, commit: str = FROZEN_PROTOCOL_COMMIT
) -> str:
    """Hash the exact frozen acceptance-gate Git blob."""
    result = sha256_bytes(
        git_blob_bytes(
            project_root,
            commit,
            "docs/phase1_parser_v2_acceptance_gates.json",
        )
    )
    if commit == FROZEN_PROTOCOL_COMMIT and result != FROZEN_ACCEPTANCE_GATE_SHA256:
        raise ValidationSetError("frozen acceptance-gate hash is not the final binding")
    return result


def derive_case_id(private_salt: str | bytes, parse_type: str, output_text: str) -> str:
    """Derive the registered opaque case ID from private salt and exact text."""
    if isinstance(private_salt, str):
        salt_bytes = private_salt.encode("utf-8")
    elif isinstance(private_salt, bytes):
        salt_bytes = private_salt
    else:
        raise ValidationSetError("private ID salt must be a string or bytes")
    if len(salt_bytes) < 16:
        raise ValidationSetError("private ID salt must contain at least 16 bytes")
    if parse_type != "numeric":
        raise ValidationSetError("parse_type must equal numeric")
    output = _require_string(output_text, "output_text", nonempty=False).encode(
        "utf-8"
    )
    digest = hashlib.sha256()
    digest.update(CASE_ID_HASH_DOMAIN)
    digest.update(len(salt_bytes).to_bytes(4, "big"))
    digest.update(salt_bytes)
    parse_bytes = parse_type.encode("ascii")
    digest.update(len(parse_bytes).to_bytes(4, "big"))
    digest.update(parse_bytes)
    digest.update(len(output).to_bytes(8, "big"))
    digest.update(output)
    return f"PV2-{digest.hexdigest()[:20]}"


def normalize_fixture_text(value: str) -> str:
    """Apply the frozen NFKC/newline/whitespace/casefold normalization."""
    text = _require_string(value, "fixture text", nonempty=False)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\s+", " ", text, flags=re.UNICODE)
    return text.casefold()


def numeric_masked_text(value: str) -> str:
    """Normalize fixture text and mask every registered numeric literal."""
    return _NUMERIC_MASK_PATTERN.sub("<NUM>", normalize_fixture_text(value))


def character_ngrams(value: str, size: int = 5) -> frozenset[str]:
    if type(size) is not int or size <= 0:
        raise ValidationSetError("n-gram size must be a positive integer")
    if len(value) < size:
        return frozenset({value})
    return frozenset(value[index : index + size] for index in range(len(value) - size + 1))


def char_ngram_jaccard(left: str, right: str, size: int = 5) -> Fraction:
    """Return exact Jaccard similarity for numeric-masked character n-grams."""
    left_grams = character_ngrams(numeric_masked_text(left), size)
    right_grams = character_ngrams(numeric_masked_text(right), size)
    union = left_grams | right_grams
    if not union:
        return Fraction(1, 1)
    return Fraction(len(left_grams & right_grams), len(union))


def _span_fields(acceptable: bool) -> frozenset[str]:
    if acceptable:
        return frozenset({"start", "end", "text"})
    return frozenset(
        {
            "start",
            "end",
            "text",
            "kind",
            "normalized_answer",
            "disposition",
        }
    )


def _validate_numeric_token_context(
    output_text: str, start: int, end: int, name: str
) -> None:
    """Reject numeric spans embedded in identifiers, versions, dates, or units."""
    previous = output_text[start - 1] if start else ""
    following = output_text[end] if end < len(output_text) else ""
    if previous and (previous.isalnum() or previous == "_"):
        raise ValidationSetError(f"{name} is embedded in an identifier or unit")
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
        raise ValidationSetError(
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
        raise ValidationSetError(
            f"{name} omits numeric-token syntax or is unit-bearing"
        )
    if (
        previous in {":", ",", "：", "，"}
        and start >= 2
        and output_text[start - 2].isdigit()
    ):
        raise ValidationSetError(f"{name} is embedded in a version or date")
    if (
        following in {".", "/", "-", ":", ",", "：", "，"}
        and end + 1 < len(output_text)
        and output_text[end + 1].isdigit()
    ):
        raise ValidationSetError(f"{name} is embedded in a version or date")


def validate_evidence_span(
    span: Mapping[str, Any],
    output_text: str,
    *,
    acceptable: bool = False,
    name: str = "evidence_span",
) -> dict[str, Any]:
    """Validate one exact half-open Unicode-code-point span."""
    _require_exact_fields(span, _span_fields(acceptable), name)
    start = _require_int(span["start"], f"{name}.start", minimum=0)
    end = _require_int(span["end"], f"{name}.end", minimum=0)
    text = _require_string(span["text"], f"{name}.text", nonempty=False)
    if start >= end or end > len(output_text):
        raise ValidationSetError(f"{name} has invalid half-open offsets")
    if output_text[start:end] != text:
        raise ValidationSetError(f"{name} text does not match output_text offsets")
    result = {"start": start, "end": end, "text": text}
    if not acceptable:
        _validate_numeric_token_context(output_text, start, end, name)
        normalized_text = normalize_rational_literal(text)
        normalized_answer = _require_canonical_numeric(
            span["normalized_answer"], f"{name}.normalized_answer"
        )
        if normalized_answer != normalized_text:
            raise ValidationSetError(
                f"{name}.normalized_answer does not match exact span text"
            )
        result.update(
            {
                "kind": _require_enum(
                    span["kind"], EVIDENCE_KINDS, f"{name}.kind"
                ),
                "normalized_answer": normalized_answer,
                "disposition": _require_enum(
                    span["disposition"],
                    EVIDENCE_DISPOSITIONS,
                    f"{name}.disposition",
                ),
            }
        )
    return result


def _validate_spans(
    value: Any,
    output_text: str,
    name: str,
    *,
    acceptable: bool = False,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValidationSetError(f"{name} must be a list")
    result: list[dict[str, Any]] = []
    keys: set[tuple[Any, ...]] = set()
    for index, span in enumerate(value):
        checked = validate_evidence_span(
            span,
            output_text,
            acceptable=acceptable,
            name=f"{name}[{index}]",
        )
        key = (checked["start"], checked["end"], checked["text"])
        if key in keys:
            raise ValidationSetError(f"{name} contains a duplicate span")
        keys.add(key)
        result.append(checked)
    if result != sorted(result, key=lambda item: (item["start"], item["end"])):
        raise ValidationSetError(f"{name} must be ordered by source offset")
    return result


def _validate_candidate_answers(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValidationSetError(f"{name} must be a list")
    result: list[str] = []
    for index, item in enumerate(value):
        checked = _require_canonical_numeric(item, f"{name}[{index}]")
        if checked in result:
            raise ValidationSetError(f"{name} contains duplicate value: {checked}")
        result.append(checked)
    return result


def _validate_extraction_fields(
    record: Mapping[str, Any],
    output_text: str,
    *,
    prefix: str = "",
    expected: bool = False,
    allow_inconclusive: bool = False,
) -> dict[str, Any]:
    key = lambda field: f"{prefix}{field}"  # noqa: E731
    if expected:
        presence = _require_enum(
            record[key("answer_presence")],
            EXPECTED_PRESENCE,
            key("answer_presence"),
        )
        parser_presence = {
            "present": "present",
            "ambiguous": "uncertain",
            "no_answer": "absent",
        }[presence]
    else:
        allowed = REVIEW_PRESENCE if allow_inconclusive else PARSER_PRESENCE
        parser_presence = _require_enum(
            record[key("answer_presence")], allowed, key("answer_presence")
        )

    parse_valid = _require_optional_bool(
        record[key("parse_valid")], key("parse_valid")
    )
    parse_ambiguous = _require_optional_bool(
        record[key("parse_ambiguous")], key("parse_ambiguous")
    )
    parsed_value = record[key("parsed_answer")]
    parsed_answer = (
        None
        if parsed_value is None
        else _require_canonical_numeric(parsed_value, key("parsed_answer"))
    )
    candidates = _validate_candidate_answers(
        record[key("candidate_answers")], key("candidate_answers")
    )
    spans = _validate_spans(
        record[key("evidence_spans")], output_text, key("evidence_spans")
    )
    strategy_value = record[key("extraction_strategy")]
    quality_value = record[key("output_quality")]
    if strategy_value is None:
        strategy = None
    else:
        strategy = _require_enum(
            strategy_value, EXTRACTION_STRATEGIES, key("extraction_strategy")
        )
    if quality_value is None:
        quality = None
    else:
        quality = _require_enum(
            quality_value, OUTPUT_QUALITIES, key("output_quality")
        )
    failures = _require_unique_ordered_enum_list(
        record[key("failure_reasons")], FAILURE_REASONS, key("failure_reasons")
    )
    warnings = _require_unique_ordered_enum_list(
        record[key("format_warnings")], FORMAT_WARNINGS, key("format_warnings")
    )

    if parser_presence == "inconclusive":
        if any(
            item is not None
            for item in (parse_valid, parse_ambiguous, parsed_answer, strategy, quality)
        ) or candidates or spans or failures or warnings:
            raise ValidationSetError(
                "an inconclusive Stage-1 row must leave extraction fields unresolved"
            )
        return {
            "answer_presence": parser_presence,
            "parse_valid": None,
            "parse_ambiguous": None,
            "parsed_answer": None,
            "candidate_answers": [],
            "evidence_spans": [],
            "extraction_strategy": None,
            "output_quality": None,
            "failure_reasons": [],
            "format_warnings": [],
        }

    if parse_valid is None or parse_ambiguous is None or strategy is None or quality is None:
        raise ValidationSetError("conclusive extraction fields must not be null")
    selected = [span for span in spans if span["disposition"] == "selected"]
    ambiguous_spans = [
        span for span in spans if span["disposition"] == "ambiguous_candidate"
    ]
    evidence_candidate_order: list[str] = []
    for span in spans:
        answer = span["normalized_answer"]
        if answer not in evidence_candidate_order:
            evidence_candidate_order.append(answer)
    if candidates != evidence_candidate_order:
        raise ValidationSetError(
            "candidate answers must equal evidence values in first-source order"
        )

    if parser_presence == "present":
        if (
            not parse_valid
            or parse_ambiguous
            or parsed_answer is None
            or len(selected) != 1
            or candidates != [parsed_answer]
            or selected[0]["normalized_answer"] != parsed_answer
            or ambiguous_spans
            or any(
                span["normalized_answer"] != parsed_answer for span in spans
            )
            or strategy in {"none", "ambiguous_candidates"}
        ):
            raise ValidationSetError("present extraction invariants are violated")
    elif parser_presence == "uncertain":
        if (
            not parse_valid
            or not parse_ambiguous
            or parsed_answer is not None
            or len(candidates) < 2
            or selected
            or len(ambiguous_spans) < 2
            or len(ambiguous_spans) != len(spans)
            or strategy != "ambiguous_candidates"
        ):
            raise ValidationSetError("ambiguous extraction invariants are violated")
    elif parser_presence == "absent":
        if (
            parse_valid
            or parse_ambiguous
            or parsed_answer is not None
            or candidates
            or selected
            or spans
            or strategy != "none"
        ):
            raise ValidationSetError("no-answer extraction invariants are violated")

    if parse_valid and failures:
        raise ValidationSetError("failure_reasons must be empty for a valid parse")
    if not parse_valid and not failures:
        raise ValidationSetError("an invalid parse must state a failure reason")
    if not output_text.strip() and quality != "empty":
        raise ValidationSetError("empty output_text must have output_quality=empty")
    if quality == "empty" and output_text.strip():
        raise ValidationSetError("output_quality=empty requires empty output_text")
    return {
        "answer_presence": parser_presence,
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


_DEVELOPMENT_FIELDS = frozenset(DevelopmentRecord.__required_keys__)
_CANDIDATE_FIELDS = frozenset(CandidateFixture.__required_keys__)
_CURATOR_PROPOSAL_FIELDS = frozenset(
    CuratorCandidateProposal.__required_keys__
)
_LOCKED_INPUT_FIELDS = frozenset(LockedInput.__required_keys__)
_PARSER_REQUEST_FIELDS = frozenset(ParserRequest.__required_keys__)
_STAGE1_FIELDS = frozenset(Stage1ReviewRow.__required_keys__)
_STAGE2_FIELDS = frozenset(Stage2ReviewRow.__required_keys__)

_PARSER_RESULT_FIELDS = frozenset(
    {
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
)
_PREDICTION_ENVELOPE_FIELDS = frozenset(
    {
        "schema_version",
        "case_id",
        "input_record_sha256",
        "parser_request_sha256",
        "parser_result",
    }
)
_LOCKED_LABEL_EXTRA_FIELDS = frozenset(
    {
        "acceptable_selected_spans",
        "last_number_distractor_span",
        "template_family_id",
        "construction_provenance",
    }
)
_LOCKED_LABEL_FIELDS = _DEVELOPMENT_FIELDS | _LOCKED_LABEL_EXTRA_FIELDS
_STAGE1_ARBITRATION_FIELDS = frozenset(
    {
        "schema_version",
        "review_stage",
        "case_id",
        "arbiter_id",
        "arbiter_model_id",
        "arbiter_reasoning_effort",
        "packet_sha256",
        "reviewer_a_submission_sha256",
        "reviewer_b_submission_sha256",
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
        "resolution_notes",
    }
)
_STAGE1_CONSENSUS_FIELDS = frozenset(
    {
        "schema_version",
        "case_id",
        "source",
        "source_row_sha256",
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
)
_STAGE2_ARBITRATION_FIELDS = frozenset(
    {
        "schema_version",
        "review_stage",
        "case_id",
        "arbiter_id",
        "arbiter_model_id",
        "arbiter_reasoning_effort",
        "packet_sha256",
        "stage1_consensus_sha256",
        "stage2_reference_packet_sha256",
        "reviewer_a_submission_sha256",
        "reviewer_b_submission_sha256",
        "correctness",
        "critical_case",
        "material_error_if_missed",
        "resolution_notes",
    }
)


def _validate_common_expected_record(
    record: Mapping[str, Any],
    *,
    expected_schema: str,
    name: str,
    require_case_id: bool,
) -> dict[str, Any]:
    if record["schema_version"] != expected_schema:
        raise ValidationSetError(f"{name}.schema_version is invalid")
    if require_case_id:
        _require_case_id(record["case_id"], f"{name}.case_id")
    if record["source_kind"] != SOURCE_KIND:
        raise ValidationSetError(f"{name}.source_kind is invalid")
    stratum = _require_enum(record["stratum"], STRATA, f"{name}.stratum")
    tags = _require_unique_ordered_enum_list(
        record["secondary_tags"], SECONDARY_TAGS, f"{name}.secondary_tags"
    )
    output_text = _require_string(
        record["output_text"], f"{name}.output_text", nonempty=False
    )
    if record["parse_type"] != "numeric":
        raise ValidationSetError(f"{name}.parse_type must equal numeric")
    extraction = _validate_extraction_fields(
        record,
        output_text,
        prefix="expected_",
        expected=True,
    )
    reference = _require_canonical_numeric(
        record["registered_reference_answer"],
        f"{name}.registered_reference_answer",
    )
    correctness = _require_bool(
        record["expected_correctness"], f"{name}.expected_correctness"
    )
    expected_correctness = (
        extraction["answer_presence"] == "present"
        and extraction["parsed_answer"] == reference
    )
    if correctness != expected_correctness:
        raise ValidationSetError(
            f"{name}.expected_correctness does not follow exact reference equality"
        )
    critical = _require_bool(record["critical_case"], f"{name}.critical_case")
    if critical != (stratum in CRITICAL_STRATA):
        raise ValidationSetError(f"{name}.critical_case disagrees with stratum")
    material = _require_bool(
        record["material_error_if_missed"],
        f"{name}.material_error_if_missed",
    )
    notes = _require_string(
        record["curation_notes"], f"{name}.curation_notes", nonempty=False
    )
    derived_features = _surface_features(record)
    diagnostic_tags = set(tags) & QUOTA_DIAGNOSTIC_TAGS
    if diagnostic_tags != derived_features & QUOTA_DIAGNOSTIC_TAGS:
        raise ValidationSetError(
            f"{name}.secondary_tags disagree with content-derived quota features"
        )
    return {
        "stratum": stratum,
        "secondary_tags": tags,
        "output_text": output_text,
        "extraction": extraction,
        "registered_reference_answer": reference,
        "expected_correctness": correctness,
        "critical_case": critical,
        "material_error_if_missed": material,
        "curation_notes": notes,
    }


def _validate_private_label_spans(
    record: Mapping[str, Any],
    output_text: str,
    extraction: Mapping[str, Any],
    stratum: str,
    *,
    name: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    acceptable = _validate_spans(
        record["acceptable_selected_spans"],
        output_text,
        f"{name}.acceptable_selected_spans",
        acceptable=True,
    )
    presence = extraction["answer_presence"]
    if presence == "present" and not acceptable:
        raise ValidationSetError(
            f"{name} present case needs an acceptable selected span"
        )
    if presence != "present" and acceptable:
        raise ValidationSetError(
            f"{name} non-present case cannot have acceptable selected spans"
        )
    if presence == "present":
        evidence_keys = {
            (span["start"], span["end"], span["text"])
            for span in extraction["evidence_spans"]
            if span["normalized_answer"] == extraction["parsed_answer"]
        }
        for span in acceptable:
            if (span["start"], span["end"], span["text"]) not in evidence_keys:
                raise ValidationSetError(
                    f"{name} acceptable span is not registered extraction evidence"
                )

    distractor_value = record["last_number_distractor_span"]
    if stratum == "S06":
        if not isinstance(distractor_value, Mapping):
            raise ValidationSetError(f"{name} S06 case needs one distractor span")
        distractor = validate_evidence_span(
            distractor_value,
            output_text,
            acceptable=True,
            name=f"{name}.last_number_distractor_span",
        )
        try:
            normalized_distractor = normalize_rational_literal(distractor["text"])
        except ValidationSetError as exc:
            raise ValidationSetError(
                f"{name} S06 distractor must be one registered numeric literal"
            ) from exc
        if normalized_distractor == extraction["parsed_answer"]:
            raise ValidationSetError(
                f"{name} S06 rightmost distractor must differ canonically"
            )
        numeric_matches = _registered_numeric_matches(output_text)
        if not numeric_matches or (
            numeric_matches[-1].start(),
            numeric_matches[-1].end(),
        ) != (distractor["start"], distractor["end"]):
            raise ValidationSetError(
                f"{name} S06 distractor must be the rightmost numeric literal"
            )
    else:
        if distractor_value is not None:
            raise ValidationSetError(
                f"{name} only S06 may register a last-number distractor"
            )
        distractor = None

    if stratum == "S11" and len(extraction["candidate_answers"]) < 2:
        raise ValidationSetError(
            f"{name} S11 case needs at least two canonical candidates"
        )
    return acceptable, distractor


def _think_tag_features(output_text: str) -> tuple[bool, bool]:
    complete_matches = list(
        re.finditer(r"</?think\s*>", output_text, flags=re.IGNORECASE)
    )
    complete_starts = {match.start() for match in complete_matches}
    malformed = any(
        fragment.start() not in complete_starts
        for fragment in re.finditer(
            r"</?think", output_text, flags=re.IGNORECASE
        )
    )
    tags = [
        match.group(0).casefold()
        for match in complete_matches
    ]
    depth = 0
    balanced_pair = False
    for tag in tags:
        if tag.startswith("</"):
            if depth == 0:
                malformed = True
            else:
                depth -= 1
                balanced_pair = True
        else:
            if depth:
                malformed = True
            depth += 1
    if depth:
        malformed = True
    return balanced_pair and not malformed, malformed


def validate_candidate_fixture(
    record: Mapping[str, Any],
    *,
    expected_curator_id: str | None = None,
    name: str = "candidate",
) -> dict[str, Any]:
    """Validate one complete, private curator candidate fixture."""
    _require_exact_fields(record, _CANDIDATE_FIELDS, name)
    common = _validate_common_expected_record(
        record,
        expected_schema=CANDIDATE_SCHEMA_VERSION,
        name=name,
        require_case_id=False,
    )
    candidate_id = _require_string(record["candidate_id"], f"{name}.candidate_id")
    if not _CANDIDATE_ID_PATTERN.fullmatch(candidate_id):
        raise ValidationSetError(f"{name}.candidate_id is invalid")
    curator_id = _require_string(record["curator_id"], f"{name}.curator_id")
    if expected_curator_id is not None and curator_id != expected_curator_id:
        raise ValidationSetError(f"{name}.curator_id is not the sealed pool owner")
    subtype = _require_enum(
        record["subtype_slot"],
        SUBTYPE_SLOTS[common["stratum"]],
        f"{name}.subtype_slot",
    )
    acceptable, distractor = _validate_private_label_spans(
        record,
        common["output_text"],
        common["extraction"],
        common["stratum"],
        name=name,
    )
    template = _require_string(
        record["template_family_id"], f"{name}.template_family_id", maximum=128
    )
    provenance = _require_string(
        record["construction_provenance"],
        f"{name}.construction_provenance",
        maximum=1000,
    )
    balanced, malformed = _think_tag_features(common["output_text"])
    tags = set(common["secondary_tags"])
    if "balanced_think_tags" in tags and not balanced:
        raise ValidationSetError(
            f"{name} claims balanced_think_tags without balanced tags"
        )
    if "malformed_think_tags" in tags and not malformed:
        raise ValidationSetError(
            f"{name} claims malformed_think_tags without malformed tags"
        )
    if (
        "incidental_numeric_distractor" in tags
        and _NUMERIC_MASK_PATTERN.search(common["output_text"]) is None
    ):
        raise ValidationSetError(
            f"{name} claims an incidental distractor without a numeric literal"
        )
    return {
        **common,
        "candidate_id": candidate_id,
        "curator_id": curator_id,
        "subtype_slot": subtype,
        "acceptable_selected_spans": acceptable,
        "last_number_distractor_span": distractor,
        "template_family_id": template,
        "construction_provenance": provenance,
    }


def normalize_external_secondary_tags(
    value: Any, *, name: str = "proposal secondary_tags"
) -> list[str]:
    """Validate sealed external tags and return canonical internal ordering."""
    if not isinstance(value, list):
        raise ValidationSetError(f"{name} must be a list")
    raw_tags: list[str] = []
    for index, item in enumerate(value):
        tag = _require_enum(
            item,
            EXTERNAL_SECONDARY_TAGS,
            f"{name}[{index}]",
        )
        if tag in raw_tags:
            raise ValidationSetError(
                f"{name} contains duplicate external tag: {tag}"
            )
        raw_tags.append(tag)
    normalized = {
        EXTERNAL_SECONDARY_TAG_ALIASES[tag] for tag in raw_tags
    }
    return [tag for tag in SECONDARY_TAGS if tag in normalized]


def normalize_subtype_slot(stratum: str, value: Any) -> str:
    """Map one exact snake-case or protocol-label subtype to its internal slot."""
    checked_stratum = _require_enum(stratum, STRATA, "proposal stratum")
    checked = _require_string(value, "proposal subtype_slot")
    normalized = SUBTYPE_SLOT_ALIASES[checked_stratum].get(checked)
    if normalized is None:
        raise ValidationSetError(
            f"proposal subtype_slot is not a registered alias for {checked_stratum}"
        )
    return normalized


def _derive_s06_distractor_span(
    output_text: str,
    extraction: Mapping[str, Any],
    *,
    name: str,
) -> dict[str, Any]:
    selected = [
        span
        for span in extraction["evidence_spans"]
        if span["disposition"] == "selected"
        and span["normalized_answer"] == extraction["parsed_answer"]
    ]
    if len(selected) != 1:
        raise ValidationSetError(
            f"{name} S06 proposal must have one selected answer span"
        )
    matches = _registered_numeric_matches(output_text)
    if not matches:
        raise ValidationSetError(
            f"{name} S06 proposal has no registered rightmost numeric literal"
        )
    rightmost = matches[-1]
    text = rightmost.group(0)
    normalized = normalize_rational_literal(text)
    if (
        rightmost.start() < selected[0]["end"]
        or normalized == extraction["parsed_answer"]
    ):
        raise ValidationSetError(
            f"{name} S06 rightmost literal must follow and differ from the selected answer"
        )
    return {
        "start": rightmost.start(),
        "end": rightmost.end(),
        "text": text,
    }


def _derive_private_label_spans(
    output_text: str,
    extraction: Mapping[str, Any],
    stratum: str,
    *,
    name: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    acceptable_by_identity: dict[
        tuple[int, int, str], dict[str, Any]
    ] = {}
    if extraction["answer_presence"] == "present":
        parsed_answer = extraction["parsed_answer"]
        for span in extraction["evidence_spans"]:
            if (
                span["disposition"] in {"selected", "equivalent"}
                and span["normalized_answer"] == parsed_answer
            ):
                identity = (span["start"], span["end"], span["text"])
                acceptable_by_identity[identity] = {
                    "start": span["start"],
                    "end": span["end"],
                    "text": span["text"],
                }
    acceptable = [
        acceptable_by_identity[identity]
        for identity in sorted(acceptable_by_identity)
    ]
    distractor = (
        _derive_s06_distractor_span(
            output_text, extraction, name=name
        )
        if stratum == "S06"
        else None
    )
    return acceptable, distractor


def validate_curator_candidate_proposal(
    record: Mapping[str, Any],
    *,
    expected_curator_id: str | None = None,
    name: str = "curator candidate proposal",
) -> CandidateFixture:
    """Validate one sealed external proposal and normalize it for internal use."""
    _require_exact_fields(record, _CURATOR_PROPOSAL_FIELDS, name)
    if record["candidate_schema_version"] != CURATOR_CANDIDATE_SCHEMA_VERSION:
        raise ValidationSetError(f"{name}.candidate_schema_version is invalid")
    candidate_id = _require_string(
        record["candidate_id"], f"{name}.candidate_id"
    )
    if not _CANDIDATE_ID_PATTERN.fullmatch(candidate_id):
        raise ValidationSetError(f"{name}.candidate_id has invalid syntax")
    curator_id = _require_string(record["curator_id"], f"{name}.curator_id")
    if expected_curator_id is not None and curator_id != expected_curator_id:
        raise ValidationSetError(f"{name}.curator_id differs from its pool seal")
    stratum = _require_enum(record["stratum"], STRATA, f"{name}.stratum")
    subtype = normalize_subtype_slot(stratum, record["subtype_slot"])
    presence = _require_enum(
        record["proposed_expected_answer_presence"],
        ("present", "absent", "uncertain"),
        f"{name}.proposed_expected_answer_presence",
    )
    presence_map = {
        "present": "present",
        "absent": "no_answer",
        "uncertain": "ambiguous",
    }
    construction_notes = _require_string(
        record["construction_notes"],
        f"{name}.construction_notes",
        nonempty=False,
    )
    secondary_tags = normalize_external_secondary_tags(
        record["secondary_tags"], name=f"{name}.secondary_tags"
    )
    reference_surface = _require_string(
        record["registered_reference_answer"],
        f"{name}.registered_reference_answer",
    )
    try:
        canonical_reference = normalize_rational_literal(reference_surface)
    except ValidationSetError as exc:
        raise ValidationSetError(
            f"{name}.registered_reference_answer is not a supported numeric surface: {exc}"
        ) from exc
    internal: CandidateFixture = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "curator_id": curator_id,
        "source_kind": record["source_kind"],
        "stratum": stratum,
        "subtype_slot": subtype,
        "secondary_tags": secondary_tags,
        "output_text": record["output_text"],
        "parse_type": record["parse_type"],
        "expected_answer_presence": presence_map[presence],
        "expected_parse_valid": record["proposed_expected_parse_valid"],
        "expected_parse_ambiguous": record[
            "proposed_expected_parse_ambiguous"
        ],
        "expected_parsed_answer": record["proposed_expected_parsed_answer"],
        "expected_candidate_answers": (
            list(record["proposed_expected_candidate_answers"])
            if isinstance(record["proposed_expected_candidate_answers"], list)
            else record["proposed_expected_candidate_answers"]
        ),
        "expected_evidence_spans": (
            [
                dict(span) if isinstance(span, Mapping) else span
                for span in record["proposed_expected_evidence_spans"]
            ]
            if isinstance(record["proposed_expected_evidence_spans"], list)
            else record["proposed_expected_evidence_spans"]
        ),
        "expected_extraction_strategy": record[
            "proposed_expected_extraction_strategy"
        ],
        "expected_output_quality": record[
            "proposed_expected_output_quality"
        ],
        "expected_failure_reasons": (
            list(record["proposed_expected_failure_reasons"])
            if isinstance(record["proposed_expected_failure_reasons"], list)
            else record["proposed_expected_failure_reasons"]
        ),
        "expected_format_warnings": (
            list(record["proposed_expected_format_warnings"])
            if isinstance(record["proposed_expected_format_warnings"], list)
            else record["proposed_expected_format_warnings"]
        ),
        "registered_reference_answer": canonical_reference,
        "expected_correctness": record["proposed_expected_correctness"],
        "critical_case": record["critical_case"],
        "material_error_if_missed": record["material_error_if_missed"],
        "curation_notes": construction_notes,
        "acceptable_selected_spans": [],
        "last_number_distractor_span": None,
        "template_family_id": record["template_family_id"],
        "construction_provenance": (
            f"sealed-curator-proposal:{curator_id}:{candidate_id}"
        ),
    }
    output_text = _require_string(
        internal["output_text"], f"{name}.output_text", nonempty=False
    )
    extraction = _validate_extraction_fields(
        internal, output_text, prefix="expected_", expected=True
    )
    derived_quota_tags = (
        _surface_features(
            {
                "output_text": output_text,
                "expected_parsed_answer": extraction["parsed_answer"],
                "expected_evidence_spans": extraction["evidence_spans"],
            }
        )
        & QUOTA_DIAGNOSTIC_TAGS
    )
    normalized_nonquota_tags = (
        set(secondary_tags) - QUOTA_DIAGNOSTIC_TAGS
    )
    internal["secondary_tags"] = [
        tag
        for tag in SECONDARY_TAGS
        if tag in normalized_nonquota_tags or tag in derived_quota_tags
    ]
    (
        internal["acceptable_selected_spans"],
        internal["last_number_distractor_span"],
    ) = _derive_private_label_spans(
        output_text, extraction, stratum, name=name
    )
    validate_candidate_fixture(
        internal, expected_curator_id=expected_curator_id, name=name
    )
    return internal


def validate_development_record(
    record: Mapping[str, Any], *, name: str = "development_record"
) -> dict[str, Any]:
    """Validate one exact open development record."""
    _require_exact_fields(record, _DEVELOPMENT_FIELDS, name)
    return _validate_common_expected_record(
        record,
        expected_schema=DEVELOPMENT_SCHEMA_VERSION,
        name=name,
        require_case_id=True,
    )


def validate_locked_input(
    record: Mapping[str, Any], *, name: str = "locked_input"
) -> dict[str, Any]:
    """Validate the intentionally label-free parser-facing locked input."""
    _require_exact_fields(record, _LOCKED_INPUT_FIELDS, name)
    if record["schema_version"] != LOCKED_INPUT_SCHEMA_VERSION:
        raise ValidationSetError(f"{name}.schema_version is invalid")
    case_id = _require_case_id(record["case_id"], f"{name}.case_id")
    if record["source_kind"] != SOURCE_KIND:
        raise ValidationSetError(f"{name}.source_kind is invalid")
    output_text = _require_string(
        record["output_text"], f"{name}.output_text", nonempty=False
    )
    if record["parse_type"] != "numeric":
        raise ValidationSetError(f"{name}.parse_type must equal numeric")
    return {"case_id": case_id, "output_text": output_text}


def validate_final_label(
    record: Mapping[str, Any], *, name: str = "final_label"
) -> dict[str, Any]:
    """Validate one complete private locked operational reference label."""
    _require_exact_fields(record, _LOCKED_LABEL_FIELDS, name)
    common = _validate_common_expected_record(
        record,
        expected_schema=FINAL_LABEL_SCHEMA_VERSION,
        name=name,
        require_case_id=True,
    )
    acceptable, distractor = _validate_private_label_spans(
        record,
        common["output_text"],
        common["extraction"],
        common["stratum"],
        name=name,
    )
    template = _require_string(
        record["template_family_id"], f"{name}.template_family_id", maximum=128
    )
    provenance = _require_string(
        record["construction_provenance"],
        f"{name}.construction_provenance",
        maximum=1000,
    )
    return {
        **common,
        "case_id": record["case_id"],
        "acceptable_selected_spans": acceptable,
        "last_number_distractor_span": distractor,
        "template_family_id": template,
        "construction_provenance": provenance,
    }


def project_parser_request(outer_record: Mapping[str, Any]) -> ParserRequest:
    """Project one validated outer record to the exact three-field request."""
    validate_locked_input(outer_record)
    request: ParserRequest = {
        "schema_version": PARSER_REQUEST_SCHEMA_VERSION,
        "answer_type": "numeric",
        "output_text": outer_record["output_text"],
    }
    _require_exact_fields(request, _PARSER_REQUEST_FIELDS, "parser request")
    return request


outer_record_to_parser_request = project_parser_request


def validate_parser_request(record: Mapping[str, Any]) -> dict[str, Any]:
    _require_exact_fields(record, _PARSER_REQUEST_FIELDS, "parser request")
    if record["schema_version"] != PARSER_REQUEST_SCHEMA_VERSION:
        raise ValidationSetError("parser request schema_version is invalid")
    if record["answer_type"] != "numeric":
        raise ValidationSetError("parser request answer_type must equal numeric")
    return {
        "output_text": _require_string(
            record["output_text"], "parser request output_text", nonempty=False
        )
    }


def validate_parser_result(
    record: Mapping[str, Any],
    output_text: str,
    *,
    name: str = "parser_result",
) -> dict[str, Any]:
    """Validate one prospective parser-v2 result without implementing parsing."""
    _require_exact_fields(record, _PARSER_RESULT_FIELDS, name)
    if record["schema_version"] != PARSER_RESULT_SCHEMA_VERSION:
        raise ValidationSetError(f"{name}.schema_version is invalid")
    _require_sha256(record["parser_version"], f"{name}.parser_version")
    if record["answer_type"] != "numeric":
        raise ValidationSetError(f"{name}.answer_type must equal numeric")
    input_sha = _require_sha256(record["input_sha256"], f"{name}.input_sha256")
    expected_sha = sha256_bytes(output_text.encode("utf-8"))
    if input_sha != expected_sha:
        raise ValidationSetError(f"{name}.input_sha256 does not bind output_text")
    extraction = _validate_extraction_fields(record, output_text)
    return {"input_sha256": input_sha, **extraction}


def derive_typed_decision(record: Mapping[str, Any]) -> str:
    """Derive a typed decision from already validated extraction fields."""
    if "expected_answer_presence" in record:
        presence = record["expected_answer_presence"]
        parse_valid = record.get("expected_parse_valid")
        parse_ambiguous = record.get("expected_parse_ambiguous")
        parsed_answer = record.get("expected_parsed_answer")
        candidates = record.get("expected_candidate_answers")
        spans = record.get("expected_evidence_spans")
        prefix = "expected_"
    else:
        presence = record.get("answer_presence")
        parse_valid = record.get("parse_valid")
        parse_ambiguous = record.get("parse_ambiguous")
        parsed_answer = record.get("parsed_answer")
        candidates = record.get("candidate_answers")
        spans = record.get("evidence_spans")
        prefix = ""
    if not isinstance(candidates, list) or not isinstance(spans, list):
        raise ValidationSetError(f"{prefix}candidate and span fields must be lists")
    if any(not isinstance(span, Mapping) for span in spans):
        raise ValidationSetError(f"{prefix}evidence spans must be objects")
    if presence == "present":
        selected = [
            span for span in spans if span.get("disposition") == "selected"
        ]
        if (
            parse_valid is True
            and parse_ambiguous is False
            and isinstance(parsed_answer, str)
            and normalize_rational_literal(parsed_answer) == parsed_answer
            and candidates == [parsed_answer]
            and len(selected) == 1
            and selected[0].get("normalized_answer") == parsed_answer
            and all(
                span.get("normalized_answer") == parsed_answer
                and span.get("disposition") in {"selected", "equivalent"}
                for span in spans
            )
        ):
            return f"present:{parsed_answer}"
    elif presence in {"uncertain", "ambiguous"}:
        if (
            parse_valid is True
            and parse_ambiguous is True
            and parsed_answer is None
            and len(candidates) >= 2
            and len(set(candidates)) == len(candidates)
            and len(spans) >= 2
            and all(
                span.get("disposition") == "ambiguous_candidate"
                and span.get("normalized_answer") in candidates
                for span in spans
            )
            and {span.get("normalized_answer") for span in spans}
            == set(candidates)
        ):
            return "ambiguous"
    elif presence in {"absent", "no_answer"}:
        if (
            parse_valid is False
            and parse_ambiguous is False
            and parsed_answer is None
            and not candidates
            and not spans
        ):
            return "no_answer"
    raise ValidationSetError(f"{prefix}extraction fields do not derive a typed decision")


def typed_decision_class(decision: str) -> str:
    if isinstance(decision, str) and decision.startswith("present:"):
        literal = decision[len("present:") :]
        if normalize_rational_literal(literal) != literal:
            raise ValidationSetError(
                "present typed decision must contain a canonical numeric value"
            )
        return "present"
    if decision in {"ambiguous", "no_answer"}:
        return decision
    raise ValidationSetError("invalid typed decision")


def adapt_legacy_result(record: Mapping[str, Any]) -> dict[str, Any]:
    """Apply the frozen reference-blind legacy precedence without mutation."""
    if not isinstance(record, Mapping):
        raise ValidationSetError("legacy result must be an object")
    ambiguous = record.get("parse_ambiguous")
    valid = record.get("parse_valid")
    if type(ambiguous) is not bool or type(valid) is not bool:
        raise ValidationSetError("legacy parse flags must be booleans")
    if ambiguous:
        return {"typed_decision": "ambiguous", "adapter_failure": None}
    parsed_answer = record.get("parsed_answer")
    if valid and parsed_answer is not None:
        if not isinstance(parsed_answer, str):
            return {
                "typed_decision": "no_answer",
                "adapter_failure": "nonnormalizable_legacy_answer",
            }
        try:
            normalized = normalize_rational_literal(parsed_answer)
        except ValidationSetError:
            return {
                "typed_decision": "no_answer",
                "adapter_failure": "nonnormalizable_legacy_answer",
            }
        return {
            "typed_decision": f"present:{normalized}",
            "adapter_failure": None,
        }
    return {"typed_decision": "no_answer", "adapter_failure": None}


legacy_adapter = adapt_legacy_result


def validate_prediction_envelope(
    envelope: Mapping[str, Any], locked_input: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate hashes and the parser result in one prediction envelope."""
    _require_exact_fields(
        envelope, _PREDICTION_ENVELOPE_FIELDS, "prediction envelope"
    )
    if envelope["schema_version"] != PREDICTION_ENVELOPE_SCHEMA_VERSION:
        raise ValidationSetError("prediction envelope schema_version is invalid")
    locked = validate_locked_input(locked_input)
    case_id = _require_case_id(envelope["case_id"])
    if case_id != locked["case_id"]:
        raise ValidationSetError("prediction envelope case_id mismatch")
    input_hash = _require_sha256(
        envelope["input_record_sha256"], "prediction input_record_sha256"
    )
    if input_hash != sha256_bytes(canonical_json_bytes(dict(locked_input))):
        raise ValidationSetError("prediction input_record_sha256 mismatch")
    request = project_parser_request(locked_input)
    request_hash = _require_sha256(
        envelope["parser_request_sha256"], "prediction parser_request_sha256"
    )
    if request_hash != sha256_bytes(canonical_json_bytes(request)):
        raise ValidationSetError("prediction parser_request_sha256 mismatch")
    result = validate_parser_result(
        envelope["parser_result"], locked["output_text"]
    )
    return {"case_id": case_id, "request": request, "result": result}


_PREDICTION_SEAL_FIELDS = frozenset(
    {
        "schema_version",
        "implementation_commit",
        "parser_version",
        "locked_inputs_sha256",
        "predictions_sha256",
        "row_count",
        "ordered_case_ids",
        "sealed_utc",
    }
)


def build_prediction_seal(
    predictions: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
    *,
    implementation_commit: str,
    sealed_utc: str,
) -> dict[str, Any]:
    """Build a seal only after validating every exact prediction envelope."""
    locked = _locked_input_index(locked_inputs)
    parser_versions: set[str] = set()
    ids: list[str] = []
    for index, envelope in enumerate(predictions):
        _require_exact_fields(
            envelope, _PREDICTION_ENVELOPE_FIELDS, f"predictions[{index}]"
        )
        case_id = envelope["case_id"]
        if case_id not in locked:
            raise ValidationSetError("prediction envelope has an unknown case_id")
        validate_prediction_envelope(envelope, locked[case_id])
        parser_versions.add(envelope["parser_result"]["parser_version"])
        ids.append(case_id)
    if len(predictions) != 120 or ids != sorted(locked) or len(set(ids)) != 120:
        raise ValidationSetError(
            "prediction envelopes must exactly cover 120 ordered locked inputs"
        )
    if len(parser_versions) != 1:
        raise ValidationSetError("all predictions must use one frozen parser_version")
    seal = {
        "schema_version": PREDICTION_SEAL_SCHEMA_VERSION,
        "implementation_commit": _require_commit(
            implementation_commit, "prediction implementation_commit"
        ),
        "parser_version": next(iter(parser_versions)),
        "locked_inputs_sha256": sha256_bytes(
            canonical_jsonl_bytes(list(locked_inputs))
        ),
        "predictions_sha256": sha256_bytes(
            canonical_jsonl_bytes(list(predictions))
        ),
        "row_count": 120,
        "ordered_case_ids": ids,
        "sealed_utc": _require_utc_timestamp(sealed_utc, "prediction sealed_utc"),
    }
    validate_prediction_seal(
        seal,
        predictions,
        locked_inputs,
        expected_implementation_commit=implementation_commit,
    )
    return seal


def validate_prediction_seal(
    seal: Mapping[str, Any],
    predictions: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
    *,
    expected_implementation_commit: str,
) -> dict[str, Any]:
    """Cross-check one immutable implementation and exact prediction bytes."""
    _require_exact_fields(seal, _PREDICTION_SEAL_FIELDS, "prediction seal")
    if seal["schema_version"] != PREDICTION_SEAL_SCHEMA_VERSION:
        raise ValidationSetError("prediction seal schema_version is invalid")
    implementation = _require_commit(
        seal["implementation_commit"], "prediction seal implementation_commit"
    )
    if implementation != _require_commit(
        expected_implementation_commit, "expected implementation_commit"
    ):
        raise ValidationSetError("prediction implementation binding mismatch")
    parser_version = _require_sha256(
        seal["parser_version"], "prediction seal parser_version"
    )
    locked_hash = _require_sha256(
        seal["locked_inputs_sha256"], "prediction seal locked_inputs_sha256"
    )
    if locked_hash != sha256_bytes(canonical_jsonl_bytes(list(locked_inputs))):
        raise ValidationSetError("prediction seal locked-input hash mismatch")
    prediction_hash = _require_sha256(
        seal["predictions_sha256"], "prediction seal predictions_sha256"
    )
    if prediction_hash != sha256_bytes(canonical_jsonl_bytes(list(predictions))):
        raise ValidationSetError("prediction seal prediction hash mismatch")
    if _require_int(seal["row_count"], "prediction seal row_count") != 120:
        raise ValidationSetError("prediction seal row_count must equal 120")
    if not isinstance(seal["ordered_case_ids"], list):
        raise ValidationSetError("prediction seal ordered_case_ids must be a list")
    ids = [_require_case_id(item) for item in seal["ordered_case_ids"]]
    actual_ids = [envelope.get("case_id") for envelope in predictions]
    if ids != actual_ids or ids != sorted(ids) or len(set(ids)) != 120:
        raise ValidationSetError("prediction seal ordered membership mismatch")
    _require_utc_timestamp(seal["sealed_utc"], "prediction seal sealed_utc")
    versions = {
        envelope.get("parser_result", {}).get("parser_version")
        for envelope in predictions
        if isinstance(envelope.get("parser_result"), Mapping)
    }
    if versions != {parser_version}:
        raise ValidationSetError("mixed or unfrozen parser versions are prohibited")
    return {
        "implementation_commit": implementation,
        "parser_version": parser_version,
        "prediction_sha256": prediction_hash,
        "row_count": 120,
    }


def _record_identifier(record: Mapping[str, Any], fallback: str) -> str:
    for field in ("case_id", "candidate_id"):
        value = record.get(field)
        if isinstance(value, str) and value:
            return value
    return fallback


_HISTORICAL_OUTPUT_FIELDS = (
    "output",
    "eval_output",
    "raw_output",
    "selected_output",
    "stopped_output",
    "postprocessed_output",
    "raw_output_before_stop_cleanup",
    "raw_output_before_postprocess",
)


def validate_authoritative_historical_corpus(
    source_bytes: Mapping[str, bytes],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate the exact hash-bound all-45 historical source corpus."""
    if set(source_bytes) != set(HISTORICAL_SOURCE_HASHES) or any(
        type(value) is not bytes for value in source_bytes.values()
    ):
        raise ValidationSetError(
            "both exact named historical JSONL byte strings are required"
        )
    actual_hashes = {
        name: sha256_bytes(source_bytes[name]) for name in HISTORICAL_SOURCE_HASHES
    }
    if actual_hashes != HISTORICAL_SOURCE_HASHES:
        raise ValidationSetError(
            "historical corpus failed the two hard-coded SHA-256 checks"
        )
    generations = parse_jsonl_strict(
        source_bytes["phase1_generations.jsonl"],
        "phase1_generations.jsonl",
        require_canonical=False,
    )
    evaluations = parse_jsonl_strict(
        source_bytes["phase1_eval_records.jsonl"],
        "phase1_eval_records.jsonl",
        require_canonical=False,
    )
    if len(generations) != 45 or len(evaluations) != 45:
        raise ValidationSetError("authoritative historical corpus must be exactly 45/45")

    generation_fields = {
        "output": str,
        "raw_output": str,
        "eval_output": str,
        "stopped_output": (str, type(None)),
        "postprocessed_output": (str, type(None)),
        "raw_output_before_stop_cleanup": str,
        "raw_output_before_postprocess": str,
    }
    evaluation_fields = {
        "output": str,
        "raw_output": str,
        "stopped_output": (str, type(None)),
        "postprocessed_output": (str, type(None)),
        "raw_output_before_stop_cleanup": str,
        "raw_output_before_postprocess": str,
        "eval_output_used": str,
    }
    for artifact_name, rows, requirements in (
        ("generation", generations, generation_fields),
        ("evaluation", evaluations, evaluation_fields),
    ):
        for row_index, row in enumerate(rows):
            for field, expected_type in requirements.items():
                if field not in row or not isinstance(row[field], expected_type):
                    raise ValidationSetError(
                        f"historical {artifact_name} row {row_index}.{field} "
                        "has a missing or invalid type"
                    )
    for row_index, row in enumerate(evaluations):
        selector = row["eval_output_used"]
        if selector not in {"raw", "stopped", "postprocessed"}:
            raise ValidationSetError(
                f"historical evaluation row {row_index}.eval_output_used is invalid"
            )
        selected_field = {
            "raw": "raw_output",
            "stopped": "stopped_output",
            "postprocessed": "postprocessed_output",
        }[selector]
        selected = row[selected_field]
        if not isinstance(selected, str) or row["output"] != selected:
            raise ValidationSetError(
                f"historical evaluation row {row_index} selected output is inconsistent"
            )
    return generations, evaluations


def historical_output_fingerprints(
    generation_records: Sequence[Mapping[str, Any]],
    evaluation_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Extract only redacted text fingerprints from supplied historical rows."""
    fingerprints: list[dict[str, str]] = []
    for artifact, records in (
        ("generation", generation_records),
        ("evaluation", evaluation_records),
    ):
        if not isinstance(records, Sequence):
            raise ValidationSetError(f"historical {artifact} rows must be a sequence")
        for row_index, record in enumerate(records):
            if not isinstance(record, Mapping):
                raise ValidationSetError(
                    f"historical {artifact} row {row_index} must be an object"
                )
            for field in _HISTORICAL_OUTPUT_FIELDS:
                value = record.get(field)
                if value is None:
                    continue
                if not isinstance(value, str):
                    raise ValidationSetError(
                        f"historical {artifact} row {row_index}.{field} must be text or null"
                    )
                exact_bytes = value.encode("utf-8")
                normalized = normalize_fixture_text(value).encode("utf-8")
                fingerprints.append(
                    {
                        "source": (
                            f"{artifact}:{row_index}:{field}:"
                            f"{sha256_bytes(exact_bytes)[:16]}"
                        ),
                        "exact_sha256": sha256_bytes(exact_bytes),
                        "normalized_sha256": sha256_bytes(normalized),
                    }
                )
    return fingerprints


_HISTORICAL_FINGERPRINT_FIELDS = frozenset(
    HistoricalFingerprintRow.__required_keys__
)
_HISTORICAL_FINGERPRINT_SUMMARY_FIELDS = frozenset(
    HistoricalFingerprintSummary.__required_keys__
)
_HISTORICAL_FINGERPRINT_SOURCE_PATTERN = re.compile(
    r"(generation|evaluation):([0-9]+):([a-z_]+):([0-9a-f]{16})\Z",
    re.ASCII,
)


def _validate_historical_fingerprint_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if not rows:
        raise ValidationSetError("historical fingerprint rows must not be empty")
    validated: list[dict[str, str]] = []
    seen_sources: set[str] = set()
    for index, row in enumerate(rows):
        name = f"historical fingerprint[{index}]"
        _require_exact_fields(row, _HISTORICAL_FINGERPRINT_FIELDS, name)
        source = _require_string(row["source"], f"{name}.source")
        match = _HISTORICAL_FINGERPRINT_SOURCE_PATTERN.fullmatch(source)
        if match is None:
            raise ValidationSetError(f"{name}.source is invalid")
        artifact, row_index_text, field, prefix = match.groups()
        if (
            int(row_index_text) >= 45
            or field not in _HISTORICAL_OUTPUT_FIELDS
            or source in seen_sources
        ):
            raise ValidationSetError(
                f"{name}.source is unknown, duplicate, or out of range"
            )
        exact = _require_sha256(row["exact_sha256"], f"{name}.exact_sha256")
        normalized = _require_sha256(
            row["normalized_sha256"], f"{name}.normalized_sha256"
        )
        if prefix != exact[:16]:
            raise ValidationSetError(
                f"{name}.source does not bind its exact fingerprint"
            )
        if artifact not in {"generation", "evaluation"}:
            raise ValidationSetError(f"{name}.source artifact is invalid")
        seen_sources.add(source)
        validated.append(
            {
                "source": source,
                "exact_sha256": exact,
                "normalized_sha256": normalized,
            }
        )
    return validated


def validate_historical_fingerprint_bundle(
    fingerprint_jsonl: bytes,
    summary_json: bytes,
) -> list[dict[str, str]]:
    """Validate hash-pinned, non-content historical contamination inputs."""
    sources = {
        "historical_output_fingerprints.jsonl": fingerprint_jsonl,
        "historical_output_fingerprint_summary.json": summary_json,
    }
    if any(type(value) is not bytes for value in sources.values()):
        raise ValidationSetError(
            "historical fingerprint artifacts must be exact bytes"
        )
    if {
        name: sha256_bytes(value) for name, value in sources.items()
    } != HISTORICAL_FINGERPRINT_ARTIFACT_HASHES:
        raise ValidationSetError(
            "historical fingerprint artifacts failed registered hash checks"
        )
    rows = parse_jsonl_strict(
        fingerprint_jsonl, "historical_output_fingerprints.jsonl"
    )
    summary = parse_json_strict(
        summary_json, "historical_output_fingerprint_summary.json"
    )
    _require_exact_fields(
        summary,
        _HISTORICAL_FINGERPRINT_SUMMARY_FIELDS,
        "historical fingerprint summary",
    )
    if (
        summary["schema_version"]
        != HISTORICAL_FINGERPRINT_SUMMARY_SCHEMA_VERSION
        or summary["fingerprint_schema_version"]
        != HISTORICAL_FINGERPRINT_SCHEMA_VERSION
        or summary["status"] != "PASS"
        or summary["protocol_commit"] != FROZEN_PROTOCOL_COMMIT
    ):
        raise ValidationSetError(
            "historical fingerprint summary schema/status/protocol is invalid"
        )
    source_hashes = summary["source_artifact_sha256s"]
    _require_exact_fields(
        source_hashes,
        HISTORICAL_SOURCE_HASHES,
        "historical fingerprint summary source hashes",
    )
    if source_hashes != HISTORICAL_SOURCE_HASHES:
        raise ValidationSetError(
            "historical fingerprint summary source hashes mismatch"
        )
    if (
        _require_sha256(
            summary["fingerprint_jsonl_sha256"],
            "historical fingerprint summary JSONL hash",
        )
        != sha256_bytes(fingerprint_jsonl)
        or _require_int(
            summary["fingerprint_count"],
            "historical fingerprint summary count",
            minimum=1,
        )
        != len(rows)
        or summary["contains_historical_text"] is not False
    ):
        raise ValidationSetError(
            "historical fingerprint summary payload binding is invalid"
        )
    return _validate_historical_fingerprint_rows(rows)


def _pair_report(
    left: tuple[str, str, str, str | None],
    right: tuple[str, str, str, str | None],
    match_kind: str,
) -> dict[str, Any]:
    return {
        "left_id": left[0],
        "left_set": left[1],
        "right_id": right[0],
        "right_set": right[1],
        "match_kind": match_kind,
        "fingerprint_sha256": (
            sha256_bytes(left[2].encode("utf-8"))
            if match_kind == "exact"
            else sha256_bytes(normalize_fixture_text(left[2]).encode("utf-8"))
        ),
    }


def detect_fixture_overlaps(
    development: Sequence[Mapping[str, Any]],
    locked: Sequence[Mapping[str, Any]],
    *,
    historical_fingerprints: Sequence[Mapping[str, str]] = (),
) -> dict[str, Any]:
    """Report hard duplicate/contamination failures without exposing source text."""
    indexed: list[tuple[str, str, str, str | None]] = []
    for set_name, records in (("development", development), ("locked", locked)):
        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                raise ValidationSetError(f"{set_name}[{index}] must be an object")
            text = _require_string(
                record.get("output_text"),
                f"{set_name}[{index}].output_text",
                nonempty=False,
            )
            indexed.append(
                (
                    _record_identifier(record, f"{set_name}:{index}"),
                    set_name,
                    text,
                    (
                        record.get("template_family_id")
                        if isinstance(record.get("template_family_id"), str)
                        else None
                    ),
                )
            )

    exact_pairs: list[dict[str, Any]] = []
    normalized_pairs: list[dict[str, Any]] = []
    template_pairs: list[dict[str, Any]] = []
    for left_index, left in enumerate(indexed):
        for right in indexed[left_index + 1 :]:
            if left[2] == right[2]:
                exact_pairs.append(_pair_report(left, right, "exact"))
            if normalize_fixture_text(left[2]) == normalize_fixture_text(right[2]):
                normalized_pairs.append(_pair_report(left, right, "normalized"))
            if (
                left[1] != right[1]
                and left[3] is not None
                and left[3] == right[3]
            ):
                template_pairs.append(
                    {
                        "left_id": left[0],
                        "right_id": right[0],
                        "template_family_sha256": sha256_bytes(
                            left[3].encode("utf-8")
                        ),
                    }
                )

    historical_exact = {
        _require_sha256(item.get("exact_sha256"), "historical exact fingerprint")
        for item in historical_fingerprints
    }
    historical_normalized = {
        _require_sha256(
            item.get("normalized_sha256"), "historical normalized fingerprint"
        )
        for item in historical_fingerprints
    }
    exact_history_overlaps: list[dict[str, Any]] = []
    normalized_history_overlaps: list[dict[str, Any]] = []
    for identifier, set_name, text, _ in indexed:
        exact_hash = sha256_bytes(text.encode("utf-8"))
        normalized_hash = sha256_bytes(
            normalize_fixture_text(text).encode("utf-8")
        )
        if exact_hash in historical_exact:
            exact_history_overlaps.append(
                {
                    "case_id": identifier,
                    "set": set_name,
                    "fingerprint_sha256": exact_hash,
                }
            )
        if normalized_hash in historical_normalized:
            normalized_history_overlaps.append(
                {
                    "case_id": identifier,
                    "set": set_name,
                    "fingerprint_sha256": normalized_hash,
                }
            )

    report = {
        "schema_version": "phase1-parser-v2-overlap-report/v1",
        "exact_duplicates": exact_pairs,
        "normalized_duplicates": normalized_pairs,
        "historical_exact_overlaps": exact_history_overlaps,
        "historical_normalized_overlaps": normalized_history_overlaps,
        "cross_set_template_family_overlaps": template_pairs,
    }
    report["hard_failure_count"] = sum(
        len(report[field])
        for field in (
            "exact_duplicates",
            "normalized_duplicates",
            "historical_exact_overlaps",
            "historical_normalized_overlaps",
            "cross_set_template_family_overlaps",
        )
    )
    return report


def require_no_hard_overlaps(report: Mapping[str, Any]) -> None:
    if type(report.get("hard_failure_count")) is not int:
        raise ValidationSetError("overlap report hard_failure_count is invalid")
    if report["hard_failure_count"] != 0:
        raise ValidationSetError(
            f"fixture duplicate/contamination controls failed "
            f"({report['hard_failure_count']} redacted findings)"
        )


def near_duplicate_report(
    development: Sequence[Mapping[str, Any]],
    locked: Sequence[Mapping[str, Any]],
    *,
    threshold: Fraction = Fraction(17, 20),
) -> list[dict[str, Any]]:
    """Report all numeric-masked character-5-gram pairs at the frozen threshold."""
    if not isinstance(threshold, Fraction) or not (0 <= threshold <= 1):
        raise ValidationSetError("near-duplicate threshold must be a Fraction in [0,1]")
    indexed: list[tuple[str, str, str]] = []
    for set_name, records in (("development", development), ("locked", locked)):
        for index, record in enumerate(records):
            identifier = _record_identifier(record, f"{set_name}:{index}")
            text = _require_string(
                record.get("output_text"),
                f"{set_name}[{index}].output_text",
                nonempty=False,
            )
            indexed.append((identifier, set_name, text))
    findings: list[dict[str, Any]] = []
    for left_index, left in enumerate(indexed):
        for right in indexed[left_index + 1 :]:
            similarity = char_ngram_jaccard(left[2], right[2])
            if similarity >= threshold:
                first, second = sorted((left[0], right[0]))
                findings.append(
                    {
                        "left_id": first,
                        "right_id": second,
                        "left_set": left[1] if first == left[0] else right[1],
                        "right_set": right[1] if second == right[0] else left[1],
                        "similarity_numerator": similarity.numerator,
                        "similarity_denominator": similarity.denominator,
                        "similarity": f"{float(similarity):.6f}",
                    }
                )
    return sorted(findings, key=lambda item: (item["left_id"], item["right_id"]))


_NEAR_DISPOSITION_FIELDS = frozenset(
    {"left_candidate_id", "right_candidate_id", "decision", "reason"}
)


def validate_near_duplicate_dispositions(
    findings: Sequence[Mapping[str, Any]],
    dispositions: Sequence[Mapping[str, Any]],
) -> None:
    """Require one documented keep/reject disposition for every near pair."""
    expected = {
        tuple(sorted((item["left_id"], item["right_id"]))) for item in findings
    }
    actual: set[tuple[str, str]] = set()
    ordered: list[tuple[str, str]] = []
    for index, item in enumerate(dispositions):
        _require_exact_fields(
            item, _NEAR_DISPOSITION_FIELDS, f"near_duplicate_dispositions[{index}]"
        )
        left = _require_string(
            item["left_candidate_id"],
            f"near_duplicate_dispositions[{index}].left_candidate_id",
        )
        right = _require_string(
            item["right_candidate_id"],
            f"near_duplicate_dispositions[{index}].right_candidate_id",
        )
        pair = tuple(sorted((left, right)))
        if left != pair[0] or right != pair[1] or left == right:
            raise ValidationSetError(
                "near-duplicate disposition IDs must be distinct and sorted"
            )
        if pair in actual:
            raise ValidationSetError("duplicate near-duplicate disposition")
        _require_enum(
            item["decision"],
            ("keep", "reject"),
            f"near_duplicate_dispositions[{index}].decision",
        )
        _require_string(
            item["reason"],
            f"near_duplicate_dispositions[{index}].reason",
        )
        actual.add(pair)
        ordered.append(pair)
    if ordered != sorted(ordered):
        raise ValidationSetError(
            "near_duplicate_dispositions must be ordered by candidate pair"
        )
    if actual != expected:
        raise ValidationSetError(
            "near-duplicate dispositions do not exactly cover reported pairs"
        )


def _validate_set_record(
    record: Mapping[str, Any], set_name: str, index: int
) -> dict[str, Any]:
    schema = record.get("schema_version")
    name = f"{set_name}[{index}]"
    if schema == DEVELOPMENT_SCHEMA_VERSION:
        return validate_development_record(record, name=name)
    if schema == FINAL_LABEL_SCHEMA_VERSION:
        return validate_final_label(record, name=name)
    if schema == CANDIDATE_SCHEMA_VERSION:
        return validate_candidate_fixture(record, name=name)
    raise ValidationSetError(f"{name}.schema_version is not a set record schema")


def _registered_numeric_matches(output_text: str) -> list[re.Match[str]]:
    matches: list[re.Match[str]] = []
    for match in _NUMERIC_MASK_PATTERN.finditer(output_text):
        try:
            _validate_numeric_token_context(
                output_text, match.start(), match.end(), "numeric surface"
            )
            normalize_rational_literal(match.group(0))
        except ValidationSetError:
            continue
        matches.append(match)
    return matches


def _surface_features(record: Mapping[str, Any]) -> set[str]:
    features: set[str] = set()
    parsed = record.get("expected_parsed_answer")
    if isinstance(parsed, str) and parsed.startswith("-") and parsed != "0":
        features.add("negative_answer")
    spans = record.get("expected_evidence_spans", [])
    for span in spans:
        text = span.get("text")
        if not isinstance(text, str):
            continue
        if _FRACTION_PATTERN.fullmatch(text):
            features.add("fraction_surface")
        if _DECIMAL_PATTERN.fullmatch(text) and (
            "." in text or "e" in text.casefold()
        ):
            features.add("decimal_surface")
        if text.startswith(("+", "-")):
            features.add("signed_numeric_surface")
    balanced, malformed = _think_tag_features(record["output_text"])
    if balanced:
        features.add("balanced_think_tags")
    if malformed:
        features.add("malformed_think_tags")
    evidence_offsets = {
        (span.get("start"), span.get("end"))
        for span in spans
        if isinstance(span, Mapping)
    }
    if any(
        (match.start(), match.end()) not in evidence_offsets
        for match in _registered_numeric_matches(record["output_text"])
    ):
        features.add("incidental_numeric_distractor")
    return features


def validate_dataset_composition(
    development: Sequence[Mapping[str, Any]],
    locked: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate exact 60/120 membership, strata, support, and cross-cutting quotas."""
    if len(development) != 60 or len(locked) != 120:
        raise ValidationSetError(
            f"dataset counts must be exactly 60/120, got "
            f"{len(development)}/{len(locked)}"
        )
    validated: dict[str, list[dict[str, Any]]] = {}
    for set_name, records in (("development", development), ("locked", locked)):
        validated[set_name] = [
            _validate_set_record(record, set_name, index)
            for index, record in enumerate(records)
        ]
        identifiers = [
            _record_identifier(record, f"{set_name}:{index}")
            for index, record in enumerate(records)
        ]
        if len(identifiers) != len(set(identifiers)):
            raise ValidationSetError(f"{set_name} has duplicate identifiers")
        if all(_CASE_ID_PATTERN.fullmatch(identifier) for identifier in identifiers):
            if identifiers != sorted(identifiers):
                raise ValidationSetError(f"{set_name} must be ordered by case_id")

    expected_per_stratum = {"development": 5, "locked": 10}
    expected_support = {
        "development": {"present": 40, "ambiguous": 5, "no_answer": 15},
        "locked": {"present": 80, "ambiguous": 10, "no_answer": 30},
    }
    feature_counts: dict[str, Counter[str]] = {}
    for set_name, records in (("development", development), ("locked", locked)):
        strata = Counter(record["stratum"] for record in records)
        if strata != Counter(
            {stratum: expected_per_stratum[set_name] for stratum in STRATA}
        ):
            raise ValidationSetError(f"{set_name} stratum quotas are invalid")
        support = Counter(
            record["expected_answer_presence"] for record in records
        )
        if dict(support) != expected_support[set_name]:
            raise ValidationSetError(f"{set_name} typed-decision support is invalid")
        for record in records:
            stratum = record["stratum"]
            presence = record["expected_answer_presence"]
            if stratum == AMBIGUOUS_STRATUM and presence != "ambiguous":
                raise ValidationSetError("only S11 may and must be ambiguity-positive")
            if stratum in NO_ANSWER_STRATA and presence != "no_answer":
                raise ValidationSetError("S07/S08/S10 must be no-answer-positive")
            if stratum in ANSWER_BEARING_STRATA and presence != "present":
                raise ValidationSetError(
                    "answer-bearing strata must have present typed decisions"
                )
        feature_counts[set_name] = Counter(
            feature
            for record in records
            for feature in _surface_features(record)
        )

    locked_correctness = defaultdict(Counter)
    for record in locked:
        if record["stratum"] in ANSWER_BEARING_STRATA:
            locked_correctness[record["stratum"]][
                bool(record["expected_correctness"])
            ] += 1
    for stratum in ANSWER_BEARING_STRATA:
        if locked_correctness[stratum] != Counter({True: 5, False: 5}):
            raise ValidationSetError(
                f"locked {stratum} must contain exactly 5 correct and 5 incorrect"
            )
    development_correctness = Counter(
        bool(record["expected_correctness"])
        for record in development
        if record["stratum"] in ANSWER_BEARING_STRATA
    )
    if development_correctness != Counter({True: 20, False: 20}):
        raise ValidationSetError(
            "development answer-bearing cases must be exactly 20 correct/20 incorrect"
        )

    for set_name, minima in (
        (
            "development",
            {
                "negative_answer": 5,
                "decimal_surface": 5,
                "fraction_surface": 5,
                "balanced_think_tags": 5,
                "malformed_think_tags": 5,
            },
        ),
        (
            "locked",
            {
                "negative_answer": 10,
                "decimal_surface": 10,
                "fraction_surface": 10,
                "balanced_think_tags": 10,
                "malformed_think_tags": 10,
            },
        ),
    ):
        for feature, minimum in minima.items():
            if feature_counts[set_name][feature] < minimum:
                raise ValidationSetError(
                    f"{set_name} {feature} quota is below {minimum}"
                )

    for set_name, records, minimum in (
        ("development", development, 1),
        ("locked", locked, 2),
    ):
        for stratum in tuple(item for item in ANSWER_BEARING_STRATA if item != "S12"):
            count = sum(
                bool(
                    _surface_features(record)
                    & {
                        "signed_numeric_surface",
                        "decimal_surface",
                        "fraction_surface",
                    }
                )
                for record in records
                if record["stratum"] == stratum
            )
            if count < minimum:
                raise ValidationSetError(
                    f"{set_name} {stratum} numeric-surface quota is below {minimum}"
                )

    for set_name, records, minimum in (
        ("development", development, 2),
        ("locked", locked, 5),
    ):
        for stratum in NO_ANSWER_STRATA:
            count = sum(
                "incidental_numeric_distractor" in _surface_features(record)
                for record in records
                if record["stratum"] == stratum
            )
            if count < minimum:
                raise ValidationSetError(
                    f"{set_name} {stratum} incidental-distractor quota is below {minimum}"
                )

    empty_development = sum(not record["output_text"].strip() for record in development)
    empty_locked = sum(not record["output_text"].strip() for record in locked)
    if empty_locked != 0 or empty_development > 1 or (
        empty_development + empty_locked
    ) > 1:
        raise ValidationSetError(
            "at most one empty/whitespace fixture is allowed, only in development"
        )
    templates_development = {
        record["template_family_id"]
        for record in development
        if isinstance(record.get("template_family_id"), str)
    }
    templates_locked = {
        record["template_family_id"]
        for record in locked
        if isinstance(record.get("template_family_id"), str)
    }
    if templates_development & templates_locked:
        raise ValidationSetError(
            "template_family_id must not cross development and locked sets"
        )
    return {
        "development_count": 60,
        "locked_count": 120,
        "development_support": expected_support["development"],
        "locked_support": expected_support["locked"],
        "feature_counts": {
            set_name: dict(sorted(counts.items()))
            for set_name, counts in feature_counts.items()
        },
    }


def validate_curator_pool(
    records: Sequence[Mapping[str, Any]], curator_id: str
) -> dict[str, Any]:
    """Validate one independently authored and sealed curator pool."""
    curator = _require_string(curator_id, "curator_id")
    seen: set[str] = set()
    strata = Counter()
    for index, record in enumerate(records):
        checked = validate_candidate_fixture(
            record,
            expected_curator_id=curator,
            name=f"{curator} pool[{index}]",
        )
        identifier = checked["candidate_id"]
        if identifier in seen:
            raise ValidationSetError(f"{curator} pool has duplicate candidate_id")
        seen.add(identifier)
        strata[checked["stratum"]] += 1
    if len(records) != 144 or strata != Counter(
        {stratum: 12 for stratum in STRATA}
    ):
        raise ValidationSetError(
            f"{curator} sealed pool must contain exactly 144 candidates "
            "and 12 per stratum"
        )
    ordered_ids = [record["candidate_id"] for record in records]
    if ordered_ids != sorted(ordered_ids):
        raise ValidationSetError(f"{curator} pool must be ordered by candidate_id")
    return {
        "curator_id": curator,
        "candidate_count": len(records),
        "stratum_counts": dict(sorted(strata.items())),
        "pool_sha256": sha256_bytes(canonical_jsonl_bytes(list(records))),
    }


_CURATOR_POOL_SEAL_FIELDS = frozenset(CuratorPoolSeal.__required_keys__)


def curator_pool_seal_sha256(seal: Mapping[str, Any]) -> str:
    _require_exact_fields(seal, _CURATOR_POOL_SEAL_FIELDS, "curator pool seal")
    validate_external_no_model_run_attestation(
        seal["no_model_run_attestation"],
        context="curator_pool",
        name="curator pool seal no_model_run_attestation",
    )
    return sha256_bytes(canonical_json_bytes(dict(seal)))


def validate_curator_pool_seal(
    seal: Mapping[str, Any],
    candidate_source: Sequence[Mapping[str, Any]] | bytes,
    *,
    expected_curator_id: str | None = None,
) -> dict[str, Any]:
    """Validate one canonical v1.2 curator pool seal against exact candidate bytes."""
    _require_exact_fields(seal, _CURATOR_POOL_SEAL_FIELDS, "curator pool seal")
    if seal["schema_version"] != CURATOR_POOL_SEAL_SCHEMA_VERSION:
        raise ValidationSetError("curator pool seal schema_version is invalid")
    if isinstance(candidate_source, bytes):
        candidate_bytes = candidate_source
        records = parse_jsonl_strict(
            candidate_bytes, "sealed curator candidate JSONL"
        )
    else:
        if not isinstance(candidate_source, Sequence) or isinstance(
            candidate_source, (str, bytearray)
        ):
            raise ValidationSetError("curator candidate source must be JSONL bytes or rows")
        records = list(candidate_source)
        candidate_bytes = canonical_jsonl_bytes(records)
    curator_id = _require_string(seal["curator_id"], "curator pool seal curator_id")
    if expected_curator_id is not None and curator_id != expected_curator_id:
        raise ValidationSetError("curator pool seal identity mismatch")
    if seal["curator_model_id"] != REVIEWER_MODEL_ID:
        raise ValidationSetError("curator pool seal model is invalid")
    if seal["curator_reasoning_effort"] != REVIEWER_REASONING_EFFORT:
        raise ValidationSetError("curator pool seal reasoning effort is invalid")
    if seal["protocol_commit"] != FROZEN_PROTOCOL_COMMIT:
        raise ValidationSetError("curator pool seal protocol commit is superseded")
    if seal["protocol_bundle_sha256"] != FROZEN_PROTOCOL_BUNDLE_SHA256:
        raise ValidationSetError("curator pool seal protocol bundle is superseded")
    if seal["acceptance_gate_sha256"] != FROZEN_ACCEPTANCE_GATE_SHA256:
        raise ValidationSetError("curator pool seal acceptance gate is superseded")
    if (
        seal["candidate_schema_version"]
        != CURATOR_CANDIDATE_SCHEMA_VERSION
    ):
        raise ValidationSetError("curator pool seal candidate schema is invalid")
    if _require_int(seal["candidate_count"], "curator pool candidate_count") != 144:
        raise ValidationSetError("curator pool seal candidate_count must equal 144")
    ids: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValidationSetError(
                f"sealed curator candidate JSONL row {index} must be an object"
            )
        identifier = _require_string(
            record.get("candidate_id"),
            f"sealed curator candidate JSONL[{index}].candidate_id",
        )
        if not _CANDIDATE_ID_PATTERN.fullmatch(identifier):
            raise ValidationSetError(
                f"sealed curator candidate JSONL[{index}].candidate_id has invalid syntax"
            )
        ids.append(identifier)
    ids_hash = sha256_bytes(canonical_json_bytes(ids))
    if seal["ordered_candidate_ids_sha256"] != ids_hash:
        raise ValidationSetError("curator pool seal ordered candidate IDs mismatch")
    jsonl_hash = sha256_bytes(candidate_bytes)
    if seal["candidate_jsonl_sha256"] != jsonl_hash:
        raise ValidationSetError("curator pool seal candidate JSONL hash mismatch")
    constructed = _require_utc_timestamp(
        seal["constructed_after_protocol_utc"],
        "curator pool seal constructed_after_protocol_utc",
    )
    if constructed <= FROZEN_PROTOCOL_COMMIT_UTC:
        raise ValidationSetError(
            "curator pool was not constructed after the final protocol commit"
        )
    validate_external_no_model_run_attestation(
        seal["no_model_run_attestation"],
        context="curator_pool",
        name="curator pool seal no_model_run_attestation",
    )
    normalized_records = [
        validate_curator_candidate_proposal(
            record,
            expected_curator_id=curator_id,
            name=f"{curator_id} sealed proposal[{index}]",
        )
        for index, record in enumerate(records)
    ]
    validate_curator_pool(normalized_records, curator_id)
    return {
        "curator_id": curator_id,
        "candidate_count": 144,
        "ordered_candidate_ids_sha256": ids_hash,
        "candidate_jsonl_sha256": jsonl_hash,
        "seal_sha256": curator_pool_seal_sha256(seal),
        "raw_records": records,
        "records": normalized_records,
    }


def build_curator_pool_seal(
    records: Sequence[Mapping[str, Any]],
    *,
    curator_id: str,
    constructed_after_protocol_utc: str,
) -> CuratorPoolSeal:
    candidate_bytes = canonical_jsonl_bytes(list(records))
    ids = [record.get("candidate_id") for record in records]
    attestation: CuratorPoolNoModelAttestationA = {
        "fixtures_constructed_model_free": True,
        "network_access_used": False,
        "target_model_downloaded_or_loaded": False,
        "target_model_inference_performed": False,
    }
    seal: CuratorPoolSeal = {
        "schema_version": CURATOR_POOL_SEAL_SCHEMA_VERSION,
        "curator_id": curator_id,
        "curator_model_id": REVIEWER_MODEL_ID,
        "curator_reasoning_effort": REVIEWER_REASONING_EFFORT,
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": FROZEN_PROTOCOL_BUNDLE_SHA256,
        "acceptance_gate_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
        "candidate_schema_version": CURATOR_CANDIDATE_SCHEMA_VERSION,
        "candidate_count": len(records),
        "ordered_candidate_ids_sha256": sha256_bytes(canonical_json_bytes(ids)),
        "candidate_jsonl_sha256": sha256_bytes(candidate_bytes),
        "constructed_after_protocol_utc": constructed_after_protocol_utc,
        "no_model_run_attestation": attestation,
    }
    validate_curator_pool_seal(
        seal, candidate_bytes, expected_curator_id=curator_id
    )
    return seal


_SELECTION_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "custodian_id",
        "curator_a_pool_seal_sha256",
        "curator_a_candidate_jsonl_sha256",
        "curator_b_pool_seal_sha256",
        "curator_b_candidate_jsonl_sha256",
        "entries",
        "near_duplicate_dispositions",
    }
)
_SELECTION_ENTRY_FIELDS = frozenset(
    {"candidate_id", "disposition", "reason"}
)
_CURATOR_C_SELECTION_FIELDS = frozenset(
    CuratorCSelectionArtifact.__required_keys__
)
_CURATOR_C_DISPOSITION_FIELDS = frozenset(
    CuratorCDispositions.__required_keys__
)
_CURATOR_C_SELECTED_FIELDS = frozenset(
    CuratorCSelectedCandidateIds.__required_keys__
)
_CURATOR_C_SUMMARY_FIELDS = frozenset(
    CuratorCSummaryArtifact.__required_keys__
)
_CURATOR_C_SUMMARY_COUNT_FIELDS = frozenset(
    CuratorCSummaryCounts.__required_keys__
)
_CURATOR_C_SUMMARY_HASH_FIELDS = frozenset(
    CuratorCSummaryHashes.__required_keys__
)
_SUMMARY_PROTOCOL_BINDING_FIELDS = frozenset(
    {
        "protocol_commit",
        "protocol_bundle_sha256",
        "acceptance_gate_sha256",
    }
)
_CURATOR_C_SELECTION_PROTOCOL_BINDING_FIELDS = frozenset(
    {
        *_SUMMARY_PROTOCOL_BINDING_FIELDS,
        "phase",
        "protocol_commit_utc",
        "protocol_file_sha256s",
        "protocol_version",
    }
)
_PRIVATE_SALT_FIELDS = frozenset(
    {"schema_version", "development_id_salt", "locked_id_salt"}
)


def validate_private_salts(record: Mapping[str, Any]) -> dict[str, str]:
    _require_exact_fields(record, _PRIVATE_SALT_FIELDS, "private salts")
    if record["schema_version"] != PRIVATE_SALTS_SCHEMA_VERSION:
        raise ValidationSetError("private salts schema_version is invalid")
    development = _require_string(
        record["development_id_salt"], "development_id_salt"
    )
    locked = _require_string(record["locked_id_salt"], "locked_id_salt")
    if len(development.encode("utf-8")) < 16 or len(locked.encode("utf-8")) < 16:
        raise ValidationSetError("each private ID salt must contain at least 16 bytes")
    if development == locked:
        raise ValidationSetError("development and locked ID salts must be distinct")
    return {"development": development, "locked": locked}


def _require_candidate_id_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValidationSetError(f"{name} must be a list")
    result: list[str] = []
    for index, item in enumerate(value):
        candidate_id = _require_string(item, f"{name}[{index}]")
        if not _CANDIDATE_ID_PATTERN.fullmatch(candidate_id):
            raise ValidationSetError(f"{name}[{index}] has invalid candidate ID syntax")
        result.append(candidate_id)
    if len(result) != len(set(result)):
        raise ValidationSetError(f"{name} contains duplicate candidate IDs")
    return result


def _validate_named_curator_hashes(
    value: Any,
    expected: Mapping[str, str] | None,
    name: str,
) -> dict[str, str]:
    _require_exact_fields(value, SEALED_CURATOR_IDENTITIES, name)
    result = {
        curator_id: _require_sha256(
            value[curator_id], f"{name}.{curator_id}"
        )
        for curator_id in SEALED_CURATOR_IDENTITIES
    }
    if expected is not None:
        _require_exact_fields(expected, SEALED_CURATOR_IDENTITIES, f"{name} expected")
        checked_expected = {
            curator_id: _require_sha256(
                expected[curator_id], f"{name} expected.{curator_id}"
            )
            for curator_id in SEALED_CURATOR_IDENTITIES
        }
        if result != checked_expected:
            raise ValidationSetError(f"{name} named hash bindings mismatch")
    return result


def _validate_curator_c_selection_protocol_bindings(
    value: Any,
) -> dict[str, Any]:
    _require_exact_fields(
        value,
        _CURATOR_C_SELECTION_PROTOCOL_BINDING_FIELDS,
        "Curator-C selection final_protocol_bindings",
    )
    file_hashes = value["protocol_file_sha256s"]
    _require_exact_fields(
        file_hashes,
        FROZEN_PROTOCOL_FILE_SHA256S,
        "Curator-C selection protocol_file_sha256s",
    )
    checked_file_hashes = {
        path: _require_sha256(
            file_hashes[path],
            f"Curator-C selection protocol_file_sha256s.{path}",
        )
        for path in FROZEN_PROTOCOL_FILE_SHA256S
    }
    checked = {
        "acceptance_gate_sha256": _require_sha256(
            value["acceptance_gate_sha256"],
            "Curator-C selection acceptance_gate_sha256",
        ),
        "phase": _require_string(
            value["phase"], "Curator-C selection protocol phase"
        ),
        "protocol_bundle_sha256": _require_sha256(
            value["protocol_bundle_sha256"],
            "Curator-C selection protocol_bundle_sha256",
        ),
        "protocol_commit": _require_string(
            value["protocol_commit"], "Curator-C selection protocol_commit"
        ),
        "protocol_commit_utc": _require_utc_timestamp(
            value["protocol_commit_utc"],
            "Curator-C selection protocol_commit_utc",
        ),
        "protocol_file_sha256s": checked_file_hashes,
        "protocol_version": _require_string(
            value["protocol_version"],
            "Curator-C selection protocol_version",
        ),
    }
    expected = {
        "acceptance_gate_sha256": FROZEN_ACCEPTANCE_GATE_SHA256,
        "phase": FROZEN_PROTOCOL_PHASE,
        "protocol_bundle_sha256": FROZEN_PROTOCOL_BUNDLE_SHA256,
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "protocol_commit_utc": FROZEN_PROTOCOL_COMMIT_UTC,
        "protocol_file_sha256s": FROZEN_PROTOCOL_FILE_SHA256S,
        "protocol_version": FROZEN_PROTOCOL_VERSION,
    }
    if checked != expected:
        raise ValidationSetError("Curator-C final protocol bindings mismatch")
    return checked


def _report_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _validate_pass_report(value: Any, name: str) -> None:
    if not isinstance(value, Mapping) or not value:
        raise ValidationSetError(f"{name} must be a nonempty report object")
    for key, item in value.items():
        checked_key = _require_string(key, f"{name} key")
        normalized = _report_key(checked_key)
        child_name = f"{name}.{checked_key}"
        if isinstance(item, bool):
            negative_fact = (
                any(
                    token in normalized
                    for token in (
                        "has_",
                        "found",
                        "present",
                        "detected",
                        "performed",
                        "occurred",
                        "used",
                    )
                )
                and any(
                    token in normalized
                    for token in (
                        "overlap",
                        "duplicate",
                        "failure",
                        "error",
                        "invalid",
                        "missing",
                        "mismatch",
                        "violation",
                        "model_run",
                        "model_inference",
                        "legacy_parser",
                    )
                )
            )
            if normalized.startswith(("no_", "none_")) or any(
                marker in normalized for marker in ("_no_", "_none_")
            ):
                negative_fact = False
            if (negative_fact and item is not False) or (
                not negative_fact and item is not True
            ):
                raise ValidationSetError(f"{child_name} reports a failed condition")
        elif (
            isinstance(item, str)
            and (normalized == "status" or normalized.endswith("_status"))
            and item != "PASS"
        ):
            raise ValidationSetError(f"{child_name} must equal PASS")
        elif isinstance(item, Mapping):
            _validate_pass_report(item, child_name)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                if isinstance(child, Mapping):
                    _validate_pass_report(child, f"{child_name}[{index}]")


def _selection_record_context(
    tokens: Sequence[str],
    selected: Mapping[str, Sequence[Mapping[str, Any]]],
    pools: Sequence[Mapping[str, Any]],
    curator_ids: Sequence[str],
) -> tuple[list[Mapping[str, Any]], bool]:
    token_set = set(tokens)
    recognized = False
    if any(
        "not_selected" in token
        or token in {"rejected", "excluded", "alternatives"}
        for token in tokens
    ):
        selected_ids = {
            record["candidate_id"]
            for record in (
                *selected["development"],
                *selected["locked"],
            )
        }
        records = [
            record
            for record in pools
            if record["candidate_id"] not in selected_ids
        ]
        recognized = True
    elif any("development" in token for token in tokens):
        records = list(selected["development"])
        recognized = True
    elif any("locked" in token for token in tokens):
        records = list(selected["locked"])
        recognized = True
    elif any("selected" in token for token in tokens):
        records = [*selected["development"], *selected["locked"]]
        recognized = True
    else:
        records = list(pools)
    for index, curator_id in enumerate(curator_ids):
        aliases = {
            _report_key(curator_id),
            f"curator_{'a' if index == 0 else 'b'}",
            f"pool_{'a' if index == 0 else 'b'}",
        }
        if token_set & aliases:
            records = [
                record for record in records if record["curator_id"] == curator_id
            ]
            recognized = True
    stratum = next(
        (item.upper() for item in tokens if re.fullmatch(r"s[0-9]{2}", item)),
        None,
    )
    if stratum is not None:
        records = [record for record in records if record["stratum"] == stratum]
        recognized = True
    for registered_stratum in STRATA:
        aliases = {
            _report_key(alias): slot
            for alias, slot in SUBTYPE_SLOT_ALIASES[registered_stratum].items()
        }
        for token in tokens:
            if token in aliases:
                slot = aliases[token]
                records = [
                    record
                    for record in records
                    if record["stratum"] == registered_stratum
                    and record["subtype_slot"] == slot
                ]
                recognized = True
                break
    feature_aliases = {
        "signed_numeric_surface": {
            "signed",
            "signed_numeric",
            "signed_numeric_surface",
            "signed_numeric_surfaces",
        },
        "negative_answer": {
            "negative",
            "negative_answer",
            "negative_answers",
        },
        "decimal_surface": {
            "decimal",
            "decimals",
            "decimal_surface",
            "decimal_surfaces",
        },
        "fraction_surface": {
            "fraction",
            "fractions",
            "fraction_surface",
            "fraction_surfaces",
        },
        "balanced_think_tags": {
            "balanced_think",
            "balanced_think_tag",
            "balanced_think_tags",
        },
        "malformed_think_tags": {
            "malformed_think",
            "malformed_think_tag",
            "malformed_think_tags",
        },
        "incidental_numeric_distractor": {
            "incidental_numeric",
            "incidental_numeric_distractor",
            "incidental_numeric_distractors",
        },
    }
    for feature, aliases in feature_aliases.items():
        if token_set & aliases:
            records = [
                record
                for record in records
                if feature in _surface_features(record)
            ]
            recognized = True
    if any(
        token in {"reference_incorrect", "incorrect", "incorrect_outputs"}
        for token in token_set
    ):
        records = [
            record for record in records if not record["expected_correctness"]
        ]
        recognized = True
    elif any(
        token in {"reference_correct", "correct", "correct_outputs"}
        for token in token_set
    ):
        records = [
            record for record in records if record["expected_correctness"]
        ]
        recognized = True
    if any(
        token in {"empty", "empty_output", "empty_outputs"}
        for token in token_set
    ):
        records = [
            record for record in records if not record["output_text"].strip()
        ]
        recognized = True
    if any("answer_bearing" in token for token in tokens):
        records = [
            record for record in records if record["stratum"] in ANSWER_BEARING_STRATA
        ]
        recognized = True
    if any(token in {"critical", "critical_cases"} for token in token_set):
        records = [record for record in records if record["critical_case"]]
        recognized = True
    if any(
        token in {"material", "material_cases", "material_error_if_missed"}
        for token in token_set
    ):
        records = [
            record for record in records if record["material_error_if_missed"]
        ]
        recognized = True
    presence_aliases = {
        "present": "present",
        "absent": "no_answer",
        "no_answer": "no_answer",
        "uncertain": "ambiguous",
        "ambiguous": "ambiguous",
    }
    for token, presence in presence_aliases.items():
        if token in token_set:
            records = [
                record
                for record in records
                if record["expected_answer_presence"] == presence
            ]
            recognized = True
            break
    return records, recognized


def _validate_reported_count_tables(
    value: Any,
    *,
    selected: Mapping[str, Sequence[Mapping[str, Any]]],
    pools: Sequence[Mapping[str, Any]],
    curator_ids: Sequence[str],
    disposition_counts: Mapping[str, int],
    near_count: int,
    name: str,
) -> None:
    if not isinstance(value, (Mapping, list)) or not value:
        raise ValidationSetError(f"{name} must contain reported counts")
    observed = 0

    def visit(item: Any, path: tuple[str, ...], context: tuple[str, ...]) -> None:
        nonlocal observed
        if isinstance(item, Mapping):
            sibling_tokens = tuple(
                _report_key(child)
                for child in item.values()
                if isinstance(child, str)
            )
            for key, child in item.items():
                visit(
                    child,
                    (*path, _report_key(_require_string(key, f"{name} key"))),
                    (*context, *sibling_tokens),
                )
            return
        if isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, (*path, str(index)), context)
            return
        if type(item) is not int:
            return
        observed += 1
        tokens = tuple(token for token in (*path, *context) if token)
        text = "_".join(tokens)
        for category, expected in disposition_counts.items():
            normalized_category = _report_key(category)
            aliases = {
                normalized_category,
                normalized_category.removesuffix("_candidate_ids"),
                normalized_category.removesuffix("_ids"),
            }
            if any(alias and alias in text for alias in aliases):
                if item != expected:
                    raise ValidationSetError(f"{name} disposition count mismatch")
                return
        if "near" in text and ("flag" in text or "duplicate" in text):
            if item != near_count:
                raise ValidationSetError(f"{name} near-duplicate count mismatch")
            return
        if (
            any(
                token in {"empty", "empty_output", "empty_outputs"}
                for token in tokens
            )
            and any(
                token in {"max", "maximum", "limit", "maximum_allowed"}
                or token.endswith(("_max", "_maximum"))
                for token in tokens
            )
        ):
            expected_maximum = 0 if "locked" in tokens else 1
            if item != expected_maximum:
                raise ValidationSetError(
                    f"{name} empty-output maximum mismatch"
                )
            return
        records, recognized = _selection_record_context(
            tokens, selected, pools, curator_ids
        )
        if recognized:
            if item != len(records):
                raise ValidationSetError(f"{name} reported count mismatch at {text}")
            return
        if "selected" in text and ("total" in text or "count" in text):
            if item != 180:
                raise ValidationSetError(f"{name} selected total mismatch")
            return
        if any(
            token in text
            for token in (
                "all_candidate",
                "total_candidate",
                "candidate_count",
                "combined_candidate",
                "combined_pool",
            )
        ):
            if item != 288:
                raise ValidationSetError(f"{name} candidate total mismatch")
            return
        raise ValidationSetError(f"{name} contains an unsupported count claim at {text}")

    visit(value, (), ())
    if observed == 0:
        raise ValidationSetError(f"{name} must contain at least one integer count")


_DERIVED_FEATURE_COUNT_FIELDS = frozenset(
    {
        "balanced_think_tags",
        "decimal_surface",
        "fraction_surface",
        "incidental_numeric_distractor",
        "malformed_think_tags",
        "negative_answer",
        "signed_decimal_or_fraction_surface",
        "signed_surface",
        "truly_empty_output",
    }
)
_DERIVED_FEATURE_TOP_FIELDS = frozenset(
    {
        "development",
        "locked",
        "incidental_numeric_distractor_by_stratum",
        "answer_bearing_surface_union_by_stratum",
        "s06_rightmost_distractor_canonical_difference",
        "s11_at_least_two_distinct_canonical_candidates",
    }
)
_DERIVED_VALIDITY_FIELDS = frozenset(
    {
        "development_valid_case_count",
        "locked_valid_case_count",
        "invalid_selected_candidate_ids",
    }
)
_INCIDENTAL_QUOTA_STRATA = ("S07", "S08", "S10")
_ANSWER_SURFACE_QUOTA_STRATA = (
    "S01",
    "S02",
    "S03",
    "S04",
    "S05",
    "S06",
    "S09",
)
_NUMERIC_SURFACE_FEATURES = frozenset(
    {"signed_numeric_surface", "decimal_surface", "fraction_surface"}
)


def _validate_exact_count_object(
    value: Any,
    expected: Mapping[str, int],
    name: str,
) -> None:
    _require_exact_fields(value, expected, name)
    checked = {
        key: _require_int(value[key], f"{name}.{key}", minimum=0)
        for key in expected
    }
    if checked != dict(expected):
        raise ValidationSetError(f"{name} differs from validated output content")


def _derived_validity_report(
    records_by_set: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    stratum: str,
) -> dict[str, Any]:
    valid_counts: dict[str, int] = {}
    invalid_ids: list[str] = []
    for set_name, records in records_by_set.items():
        valid = 0
        for record in records:
            if record["stratum"] != stratum:
                continue
            is_valid = False
            if stratum == "S06":
                try:
                    _derive_s06_distractor_span(
                        record["output_text"],
                        {
                            "evidence_spans": record[
                                "expected_evidence_spans"
                            ],
                            "parsed_answer": record["expected_parsed_answer"],
                        },
                        name=f"derived feature {record['candidate_id']}",
                    )
                    is_valid = True
                except ValidationSetError:
                    is_valid = False
            else:
                canonical_candidates = {
                    normalize_rational_literal(candidate)
                    for candidate in record["expected_candidate_answers"]
                }
                is_valid = len(canonical_candidates) >= 2
            if is_valid:
                valid += 1
            else:
                invalid_ids.append(record["candidate_id"])
        valid_counts[set_name] = valid
    return {
        "development_valid_case_count": valid_counts["development"],
        "locked_valid_case_count": valid_counts["locked"],
        "invalid_selected_candidate_ids": sorted(invalid_ids),
    }


def _validate_derived_validity_claim(
    value: Any,
    expected: Mapping[str, Any],
    name: str,
) -> None:
    _require_exact_fields(value, _DERIVED_VALIDITY_FIELDS, name)
    checked = {
        "development_valid_case_count": _require_int(
            value["development_valid_case_count"],
            f"{name}.development_valid_case_count",
            minimum=0,
        ),
        "locked_valid_case_count": _require_int(
            value["locked_valid_case_count"],
            f"{name}.locked_valid_case_count",
            minimum=0,
        ),
        "invalid_selected_candidate_ids": _require_candidate_id_list(
            value["invalid_selected_candidate_ids"],
            f"{name}.invalid_selected_candidate_ids",
        ),
    }
    if checked != dict(expected):
        raise ValidationSetError(f"{name} differs from validated output content")


def _validate_actual_derived_feature_counts(
    value: Any,
    development: Sequence[Mapping[str, Any]],
    locked: Sequence[Mapping[str, Any]],
) -> None:
    _require_exact_fields(
        value, _DERIVED_FEATURE_TOP_FIELDS, "actual_derived_feature_counts"
    )
    records_by_set = {"development": development, "locked": locked}
    features_by_set = {
        set_name: [(record, _surface_features(record)) for record in records]
        for set_name, records in records_by_set.items()
    }
    aggregate_expected: dict[str, dict[str, int]] = {}
    for set_name, rows in features_by_set.items():
        aggregate_expected[set_name] = {
            "balanced_think_tags": sum(
                "balanced_think_tags" in features for _, features in rows
            ),
            "decimal_surface": sum(
                "decimal_surface" in features for _, features in rows
            ),
            "fraction_surface": sum(
                "fraction_surface" in features for _, features in rows
            ),
            "incidental_numeric_distractor": sum(
                record["stratum"] in _INCIDENTAL_QUOTA_STRATA
                and "incidental_numeric_distractor" in features
                for record, features in rows
            ),
            "malformed_think_tags": sum(
                "malformed_think_tags" in features for _, features in rows
            ),
            "negative_answer": sum(
                "negative_answer" in features for _, features in rows
            ),
            "signed_decimal_or_fraction_surface": sum(
                bool(features & _NUMERIC_SURFACE_FEATURES)
                for _, features in rows
            ),
            "signed_surface": sum(
                "signed_numeric_surface" in features for _, features in rows
            ),
            "truly_empty_output": sum(
                not record["output_text"].strip() for record, _ in rows
            ),
        }
        _validate_exact_count_object(
            value[set_name],
            aggregate_expected[set_name],
            f"actual_derived_feature_counts.{set_name}",
        )

    incidental_expected = {
        set_name: {
            stratum: sum(
                record["stratum"] == stratum
                and "incidental_numeric_distractor" in features
                for record, features in rows
            )
            for stratum in _INCIDENTAL_QUOTA_STRATA
        }
        for set_name, rows in features_by_set.items()
    }
    incidental_claim = value["incidental_numeric_distractor_by_stratum"]
    _require_exact_fields(
        incidental_claim,
        {"development", "locked"},
        "actual_derived_feature_counts.incidental_numeric_distractor_by_stratum",
    )
    for set_name in ("development", "locked"):
        _validate_exact_count_object(
            incidental_claim[set_name],
            incidental_expected[set_name],
            "actual_derived_feature_counts."
            f"incidental_numeric_distractor_by_stratum.{set_name}",
        )

    surface_union_expected = {
        set_name: {
            stratum: sum(
                record["stratum"] == stratum
                and bool(features & _NUMERIC_SURFACE_FEATURES)
                for record, features in rows
            )
            for stratum in _ANSWER_SURFACE_QUOTA_STRATA
        }
        for set_name, rows in features_by_set.items()
    }
    surface_union_claim = value["answer_bearing_surface_union_by_stratum"]
    _require_exact_fields(
        surface_union_claim,
        {"development", "locked"},
        "actual_derived_feature_counts.answer_bearing_surface_union_by_stratum",
    )
    for set_name in ("development", "locked"):
        _validate_exact_count_object(
            surface_union_claim[set_name],
            surface_union_expected[set_name],
            "actual_derived_feature_counts."
            f"answer_bearing_surface_union_by_stratum.{set_name}",
        )

    _validate_derived_validity_claim(
        value["s06_rightmost_distractor_canonical_difference"],
        _derived_validity_report(records_by_set, stratum="S06"),
        "actual_derived_feature_counts."
        "s06_rightmost_distractor_canonical_difference",
    )
    _validate_derived_validity_claim(
        value["s11_at_least_two_distinct_canonical_candidates"],
        _derived_validity_report(records_by_set, stratum="S11"),
        "actual_derived_feature_counts."
        "s11_at_least_two_distinct_canonical_candidates",
    )


_CURATOR_C_COUNT_TABLE_FIELDS = frozenset(
    {
        "answer_bearing_correctness_by_stratum",
        "by_critical_case",
        "by_curator",
        "by_material_error_if_missed",
        "by_proposed_parse_ambiguous",
        "by_proposed_parse_valid",
        "by_stratum",
        "by_stratum_and_subtype_slot",
        "dataset",
        "locked_slot_curator_counts",
        "typed_decision_support",
    }
)
_COUNT_TABLE_SET_FIELDS = frozenset({"development", "locked"})
_COUNT_TABLE_BOOLEAN_FIELDS = frozenset({"false", "true"})
_COUNT_TABLE_CORRECTNESS_FIELDS = frozenset({"correct", "incorrect"})
_COUNT_TABLE_SUPPORT_FIELDS = frozenset(
    {"present", "ambiguous", "no_answer"}
)
_COUNT_TABLE_DATASET_FIELDS = frozenset(
    {
        "candidate_pool_total",
        "development",
        "locked",
        "selected_total",
        "unselected",
    }
)


def _validate_two_set_count_section(
    value: Any,
    expected: Mapping[str, Mapping[str, int]],
    name: str,
) -> None:
    _require_exact_fields(value, _COUNT_TABLE_SET_FIELDS, name)
    for set_name in ("development", "locked"):
        _validate_exact_count_object(
            value[set_name], expected[set_name], f"{name}.{set_name}"
        )


def _validate_curator_c_count_tables(
    value: Any,
    *,
    selected: Mapping[str, Sequence[Mapping[str, Any]]],
    pools: Sequence[Mapping[str, Any]],
) -> None:
    _require_exact_fields(value, _CURATOR_C_COUNT_TABLE_FIELDS, "count_tables")
    records_by_set = {
        "development": list(selected["development"]),
        "locked": list(selected["locked"]),
    }

    correctness_expected = {
        set_name: {
            stratum: {
                "correct": sum(
                    record["stratum"] == stratum
                    and record["expected_correctness"] is True
                    for record in records
                ),
                "incorrect": sum(
                    record["stratum"] == stratum
                    and record["expected_correctness"] is False
                    for record in records
                ),
            }
            for stratum in ANSWER_BEARING_STRATA
        }
        for set_name, records in records_by_set.items()
    }
    correctness_claim = value["answer_bearing_correctness_by_stratum"]
    _require_exact_fields(
        correctness_claim,
        _COUNT_TABLE_SET_FIELDS,
        "count_tables.answer_bearing_correctness_by_stratum",
    )
    for set_name in ("development", "locked"):
        _require_exact_fields(
            correctness_claim[set_name],
            ANSWER_BEARING_STRATA,
            f"count_tables.answer_bearing_correctness_by_stratum.{set_name}",
        )
        for stratum in ANSWER_BEARING_STRATA:
            _validate_exact_count_object(
                correctness_claim[set_name][stratum],
                correctness_expected[set_name][stratum],
                "count_tables.answer_bearing_correctness_by_stratum."
                f"{set_name}.{stratum}",
            )

    boolean_sections = {
        "by_critical_case": "critical_case",
        "by_material_error_if_missed": "material_error_if_missed",
        "by_proposed_parse_ambiguous": "expected_parse_ambiguous",
        "by_proposed_parse_valid": "expected_parse_valid",
    }
    for section_name, record_field in boolean_sections.items():
        expected = {
            set_name: {
                "false": sum(
                    record[record_field] is False for record in records
                ),
                "true": sum(
                    record[record_field] is True for record in records
                ),
            }
            for set_name, records in records_by_set.items()
        }
        _validate_two_set_count_section(
            value[section_name], expected, f"count_tables.{section_name}"
        )

    curator_expected = {
        set_name: {
            curator_id: sum(
                record["curator_id"] == curator_id for record in records
            )
            for curator_id in SEALED_CURATOR_IDENTITIES
        }
        for set_name, records in records_by_set.items()
    }
    _validate_two_set_count_section(
        value["by_curator"], curator_expected, "count_tables.by_curator"
    )

    stratum_expected = {
        set_name: {
            stratum: sum(record["stratum"] == stratum for record in records)
            for stratum in STRATA
        }
        for set_name, records in records_by_set.items()
    }
    _validate_two_set_count_section(
        value["by_stratum"], stratum_expected, "count_tables.by_stratum"
    )

    subtype_expected: dict[str, dict[str, dict[str, int]]] = {}
    for set_name, records in records_by_set.items():
        subtype_expected[set_name] = {}
        for stratum in STRATA:
            subtype_expected[set_name][stratum] = {
                label: sum(
                    record["stratum"] == stratum
                    and record["subtype_slot"] == canonical_slot
                    for record in records
                )
                for label, canonical_slot in zip(
                    PROTOCOL_SUBTYPE_LABELS[stratum],
                    SUBTYPE_SLOTS[stratum],
                    strict=True,
                )
            }
    subtype_claim = value["by_stratum_and_subtype_slot"]
    _require_exact_fields(
        subtype_claim,
        _COUNT_TABLE_SET_FIELDS,
        "count_tables.by_stratum_and_subtype_slot",
    )
    for set_name in ("development", "locked"):
        _require_exact_fields(
            subtype_claim[set_name],
            STRATA,
            f"count_tables.by_stratum_and_subtype_slot.{set_name}",
        )
        for stratum in STRATA:
            _validate_exact_count_object(
                subtype_claim[set_name][stratum],
                subtype_expected[set_name][stratum],
                f"count_tables.by_stratum_and_subtype_slot.{set_name}.{stratum}",
            )

    dataset_expected = {
        "candidate_pool_total": len(pools),
        "development": len(records_by_set["development"]),
        "locked": len(records_by_set["locked"]),
        "selected_total": len(records_by_set["development"])
        + len(records_by_set["locked"]),
        "unselected": len(pools)
        - len(records_by_set["development"])
        - len(records_by_set["locked"]),
    }
    _validate_exact_count_object(
        value["dataset"], dataset_expected, "count_tables.dataset"
    )

    locked_slot_expected: dict[str, dict[str, dict[str, int]]] = {}
    for stratum in STRATA:
        locked_slot_expected[stratum] = {
            label: {
                curator_id: sum(
                    record["stratum"] == stratum
                    and record["subtype_slot"] == canonical_slot
                    and record["curator_id"] == curator_id
                    for record in records_by_set["locked"]
                )
                for curator_id in SEALED_CURATOR_IDENTITIES
            }
            for label, canonical_slot in zip(
                PROTOCOL_SUBTYPE_LABELS[stratum],
                SUBTYPE_SLOTS[stratum],
                strict=True,
            )
        }
    locked_slot_claim = value["locked_slot_curator_counts"]
    _require_exact_fields(
        locked_slot_claim, STRATA, "count_tables.locked_slot_curator_counts"
    )
    for stratum in STRATA:
        _require_exact_fields(
            locked_slot_claim[stratum],
            PROTOCOL_SUBTYPE_LABELS[stratum],
            f"count_tables.locked_slot_curator_counts.{stratum}",
        )
        for label in PROTOCOL_SUBTYPE_LABELS[stratum]:
            _validate_exact_count_object(
                locked_slot_claim[stratum][label],
                locked_slot_expected[stratum][label],
                f"count_tables.locked_slot_curator_counts.{stratum}.{label}",
            )

    support_expected = {
        set_name: {
            presence: sum(
                record["expected_answer_presence"] == presence
                for record in records
            )
            for presence in ("present", "ambiguous", "no_answer")
        }
        for set_name, records in records_by_set.items()
    }
    _validate_two_set_count_section(
        value["typed_decision_support"],
        support_expected,
        "count_tables.typed_decision_support",
    )


def _duplicate_groups(
    records: Sequence[Mapping[str, Any]],
) -> list[frozenset[str]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for record in records:
        grouped[normalize_fixture_text(record["output_text"])].add(
            record["candidate_id"]
        )
    return sorted(
        (frozenset(ids) for ids in grouped.values() if len(ids) > 1),
        key=lambda ids: sorted(ids),
    )


def _extract_reported_duplicate_groups(
    value: Any, known_ids: set[str]
) -> list[frozenset[str]]:
    if not isinstance(value, list):
        raise ValidationSetError("excluded_duplicate_groups must be a list")
    groups: list[frozenset[str]] = []
    for index, item in enumerate(value):
        if isinstance(item, list):
            ids = _require_candidate_id_list(
                item, f"excluded_duplicate_groups[{index}]"
            )
        elif isinstance(item, Mapping):
            if "candidate_ids" not in item:
                raise ValidationSetError(
                    "excluded duplicate group must contain candidate_ids"
                )
            ids = _require_candidate_id_list(
                item["candidate_ids"],
                f"excluded_duplicate_groups[{index}].candidate_ids",
            )
        else:
            raise ValidationSetError("excluded duplicate group is invalid")
        group = frozenset(ids)
        if len(group) < 2 or not group.issubset(known_ids):
            raise ValidationSetError(
                "excluded duplicate group must contain known distinct candidates"
            )
        groups.append(group)
    if len(groups) != len(set(groups)):
        raise ValidationSetError("excluded_duplicate_groups contains duplicates")
    return groups


def _near_pair_evidence(
    records: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    indexed = [
        (
            record["candidate_id"],
            character_ngrams(numeric_masked_text(record["output_text"]), 5),
        )
        for record in records
    ]
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for left_index, (left_id, left_grams) in enumerate(indexed):
        for right_id, right_grams in indexed[left_index + 1 :]:
            intersection = len(left_grams & right_grams)
            union = len(left_grams | right_grams)
            similarity = Fraction(intersection, union) if union else Fraction(1)
            if similarity >= Fraction(17, 20):
                pair = tuple(sorted((left_id, right_id)))
                result[pair] = {
                    "intersection_count": intersection,
                    "union_count": union,
                    "similarity": similarity,
                }
    return result


def _flatten_named_values(value: Mapping[str, Any]) -> dict[str, list[Any]]:
    flattened: dict[str, list[Any]] = defaultdict(list)

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                flattened[_report_key(str(key))].append(child)
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return flattened


CURATOR_C_NEAR_DUPLICATE_DISPOSITIONS = (
    "keep_global_minimum_under_frozen_constraints",
    "keep_required_three_per_slot_at_global_minimum",
    "keep_required_s12_slot_coverage_at_global_minimum",
)
_CURATOR_C_NEAR_DUPLICATE_FLAG_FIELDS = frozenset(
    {
        "candidate_ids",
        "disposition",
        "jaccard",
        "masked_5gram_intersection_count",
        "masked_5gram_union_count",
    }
)
_CURATOR_C_NEAR_SCREENING_FIELDS = frozenset(
    {
        "algorithm",
        "dispositions_complete",
        "flag_count",
        "flags",
        "global_minimum_flag_count",
        "non_s12_flag_count",
        "optimization",
        "scope_counts",
        "selected_pair_count_screened",
    }
)
_CURATOR_C_NEAR_ALGORITHM_FIELDS = frozenset(
    {
        "character_ngram_n",
        "jaccard_threshold",
        "numeric_mask",
        "text_preprocessing",
    }
)
_CURATOR_C_NEAR_OPTIMIZATION_FIELDS = frozenset(
    {
        "mip_gap",
        "primary_objective",
        "primary_status",
        "secondary_objective",
        "secondary_status",
    }
)


def _validate_near_duplicate_screening(
    value: Any,
    evidence: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    development: Sequence[Mapping[str, Any]],
    locked: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    _require_exact_fields(
        value,
        _CURATOR_C_NEAR_SCREENING_FIELDS,
        "near_duplicate_screening",
    )
    algorithm = value["algorithm"]
    _require_exact_fields(
        algorithm,
        _CURATOR_C_NEAR_ALGORITHM_FIELDS,
        "near_duplicate_screening.algorithm",
    )
    if (
        _require_int(
            algorithm["character_ngram_n"],
            "near_duplicate_screening.algorithm.character_ngram_n",
            minimum=1,
        )
        != 5
        or algorithm["jaccard_threshold"] != "0.85"
        or algorithm["numeric_mask"] != "<NUM>"
        or algorithm["text_preprocessing"]
        != "frozen_normalized_text_then_registered_ascii_numeric_mask"
    ):
        raise ValidationSetError(
            "near_duplicate_screening.algorithm is not registered"
        )
    if (
        _require_bool(
            value["dispositions_complete"],
            "near_duplicate_screening.dispositions_complete",
        )
        is not True
    ):
        raise ValidationSetError(
            "near_duplicate_screening.dispositions_complete must be true"
        )
    optimization = value["optimization"]
    _require_exact_fields(
        optimization,
        _CURATOR_C_NEAR_OPTIMIZATION_FIELDS,
        "near_duplicate_screening.optimization",
    )
    expected_optimization = {
        "mip_gap": "0",
        "primary_objective": "minimum_selected_flag_count",
        "primary_status": "optimal",
        "secondary_objective": "minimum_non_s12_flags",
        "secondary_status": "optimal",
    }
    checked_optimization = {
        key: _require_string(
            optimization[key], f"near_duplicate_screening.optimization.{key}"
        )
        for key in _CURATOR_C_NEAR_OPTIMIZATION_FIELDS
    }
    if checked_optimization != expected_optimization:
        raise ValidationSetError(
            "near_duplicate_screening.optimization is not registered"
        )
    development_ids = [
        _require_string(
            record.get("candidate_id"),
            f"near_duplicate_screening development[{index}].candidate_id",
        )
        for index, record in enumerate(development)
    ]
    locked_ids = [
        _require_string(
            record.get("candidate_id"),
            f"near_duplicate_screening locked[{index}].candidate_id",
        )
        for index, record in enumerate(locked)
    ]
    selected_ids = set(development_ids) | set(locked_ids)
    if (
        len(development_ids) != len(set(development_ids))
        or len(locked_ids) != len(set(locked_ids))
        or set(development_ids) & set(locked_ids)
    ):
        raise ValidationSetError(
            "near_duplicate_screening selected membership is invalid"
        )
    strata_by_id: dict[str, str] = {}
    for set_name, records in (("development", development), ("locked", locked)):
        for index, record in enumerate(records):
            candidate_id = _require_string(
                record.get("candidate_id"),
                f"near_duplicate_screening {set_name}[{index}].candidate_id",
            )
            strata_by_id[candidate_id] = _require_enum(
                record.get("stratum"),
                STRATA,
                f"near_duplicate_screening {set_name}[{index}].stratum",
            )
    flags = value["flags"]
    if not isinstance(flags, list):
        raise ValidationSetError("near_duplicate_screening.flags must be a list")
    flag_by_pair: dict[tuple[str, str], tuple[str, str]] = {}
    for index, flag in enumerate(flags):
        name = f"near_duplicate_screening.flags[{index}]"
        if not isinstance(flag, Mapping):
            raise ValidationSetError(f"{name} must be an object")
        _require_exact_fields(
            flag, _CURATOR_C_NEAR_DUPLICATE_FLAG_FIELDS, name
        )
        ids = _require_candidate_id_list(
            flag["candidate_ids"], f"{name}.candidate_ids"
        )
        if len(ids) != 2 or ids != sorted(ids):
            raise ValidationSetError(
                f"{name}.candidate_ids must be one exact sorted two-ID pair"
            )
        pair = (ids[0], ids[1])
        if any(candidate_id not in selected_ids for candidate_id in pair):
            raise ValidationSetError(
                f"{name} references an unselected candidate pair"
            )
        if pair in flag_by_pair:
            raise ValidationSetError(f"{name} repeats a selected candidate pair")
        if pair not in evidence:
            raise ValidationSetError(f"{name} is duplicate or below the exact threshold")
        reason = _require_enum(
            flag["disposition"],
            CURATOR_C_NEAR_DUPLICATE_DISPOSITIONS,
            f"{name}.disposition",
        )
        expected = evidence[pair]
        if (
            _require_int(
                flag["masked_5gram_intersection_count"],
                f"{name}.masked_5gram_intersection_count",
                minimum=0,
            )
            != expected["intersection_count"]
            or _require_int(
                flag["masked_5gram_union_count"],
                f"{name}.masked_5gram_union_count",
                minimum=0,
            )
            != expected["union_count"]
        ):
            raise ValidationSetError(f"{name} character-5-gram counts mismatch")
        rendered_similarity = _require_string(
            flag["jaccard"], f"{name}.jaccard"
        )
        try:
            claimed_similarity = Fraction(
                normalize_rational_literal(rendered_similarity)
            )
        except (ValueError, ZeroDivisionError, ValidationSetError) as exc:
            raise ValidationSetError(f"{name}.jaccard is invalid") from exc
        if claimed_similarity != expected["similarity"]:
            raise ValidationSetError(f"{name} exact Jaccard value mismatch")
        flag_by_pair[pair] = ("keep", reason)
    if set(flag_by_pair) != set(evidence):
        raise ValidationSetError(
            "near_duplicate_screening.flags do not exactly cover selected findings"
        )
    development_id_set = set(development_ids)
    locked_id_set = set(locked_ids)
    scope_expected = {
        "development_development": 0,
        "development_locked": 0,
        "locked_locked": 0,
    }
    for pair in evidence:
        pair_set = set(pair)
        if pair_set <= development_id_set:
            scope_expected["development_development"] += 1
        elif pair_set <= locked_id_set:
            scope_expected["locked_locked"] += 1
        elif pair_set & development_id_set and pair_set & locked_id_set:
            scope_expected["development_locked"] += 1
        else:
            raise ValidationSetError(
                "near_duplicate_screening evidence is outside selected scope"
            )
    selected_count = len(development_ids) + len(locked_ids)
    selected_pair_count = selected_count * (selected_count - 1) // 2
    if (
        _require_int(
            value.get("selected_pair_count_screened"),
            "near_duplicate_screening.selected_pair_count_screened",
            minimum=0,
        )
        != selected_pair_count
    ):
        raise ValidationSetError(
            "near_duplicate_screening selected pair count mismatch"
        )
    scope_counts = value.get("scope_counts")
    if not isinstance(scope_counts, Mapping) or len(scope_counts) != 3:
        raise ValidationSetError(
            "near_duplicate_screening.scope_counts must have three exact scopes"
        )
    scope_aliases = {
        "development_development": {
            "development_development",
            "development_development_pairs",
            "dev_dev",
            "dev_dev_pairs",
        },
        "development_locked": {
            "development_locked",
            "development_locked_pairs",
            "dev_locked",
            "dev_locked_pairs",
        },
        "locked_locked": {"locked_locked", "locked_locked_pairs"},
    }
    checked_scope_counts: dict[str, int] = {}
    for key, count in scope_counts.items():
        normalized_key = _report_key(
            _require_string(key, "near_duplicate_screening.scope_counts key")
        )
        category = next(
            (
                name
                for name, aliases in scope_aliases.items()
                if normalized_key in aliases
            ),
            None,
        )
        if category is None or category in checked_scope_counts:
            raise ValidationSetError(
                "near_duplicate_screening.scope_counts has an unknown or repeated scope"
            )
        checked_scope_counts[category] = _require_int(
            count,
            f"near_duplicate_screening.scope_counts.{key}",
            minimum=0,
        )
    if checked_scope_counts != scope_expected:
        raise ValidationSetError(
            "near_duplicate_screening.scope_counts mismatch"
        )
    finding_count = len(evidence)
    if sum(checked_scope_counts.values()) != finding_count:
        raise ValidationSetError(
            "near_duplicate_screening.scope_counts do not partition flags"
        )
    for field in ("flag_count", "global_minimum_flag_count"):
        if (
            _require_int(
                value.get(field),
                f"near_duplicate_screening.{field}",
                minimum=0,
            )
            != finding_count
        ):
            raise ValidationSetError(
                f"near_duplicate_screening.{field} mismatch"
            )
    non_s12_count = sum(
        any(strata_by_id[candidate_id] != "S12" for candidate_id in pair)
        for pair in evidence
    )
    if (
        _require_int(
            value.get("non_s12_flag_count"),
            "near_duplicate_screening.non_s12_flag_count",
            minimum=0,
        )
        != non_s12_count
    ):
        raise ValidationSetError(
            "near_duplicate_screening.non_s12_flag_count mismatch"
        )

    dispositions: list[dict[str, Any]] = []
    for pair in sorted(evidence):
        disposition, reason = flag_by_pair[pair]
        if disposition != "keep":
            raise ValidationSetError(
                "selected near-duplicate pair has a reject disposition"
            )
        dispositions.append(
            {
                "left_candidate_id": pair[0],
                "right_candidate_id": pair[1],
                "decision": "keep",
                "reason": reason,
            }
        )
    return dispositions


def _validate_selected_overlap_claims(
    value: Any, selected_overlap: Mapping[str, Any]
) -> None:
    if not isinstance(value, Mapping):
        raise ValidationSetError("overlap_validation must be an object")
    expected = {
        "exact": len(selected_overlap["exact_duplicates"]),
        "normalized": len(selected_overlap["normalized_duplicates"]),
        "template": len(
            selected_overlap["cross_set_template_family_overlaps"]
        ),
        "hard": selected_overlap["hard_failure_count"],
    }
    for key, values in _flatten_named_values(value).items():
        if "count" not in key:
            continue
        if "pool" in key or "all_candidate" in key:
            continue
        kind = next(
            (
                candidate
                for candidate in ("hard", "normalized", "exact", "template")
                if candidate in key
            ),
            None,
        )
        if kind is None:
            continue
        for item in values:
            if isinstance(item, (Mapping, list)):
                continue
            if (
                _require_int(
                    item, f"overlap_validation.{key}", minimum=0
                )
                != expected[kind]
            ):
                raise ValidationSetError(
                    "overlap_validation count differs from recomputation"
                )


def _validate_internal_selection(
    *,
    entries: Sequence[Mapping[str, Any]],
    near_duplicate_dispositions: Sequence[Mapping[str, Any]],
    pools: Sequence[Mapping[str, Any]],
    curator_c_id: str,
    selection_plan_sha256: str,
    curator_pool_seals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_id: dict[str, Mapping[str, Any]] = {}
    for index, candidate in enumerate(pools):
        identifier = _require_string(
            candidate.get("candidate_id"), f"pool candidate[{index}].candidate_id"
        )
        if identifier in by_id:
            raise ValidationSetError("candidate IDs must be distinct across pools")
        by_id[identifier] = candidate

    disposition_by_id: dict[str, str] = {}
    ordered_ids: list[str] = []
    for index, entry in enumerate(entries):
        _require_exact_fields(
            entry, _SELECTION_ENTRY_FIELDS, f"selection plan entries[{index}]"
        )
        identifier = _require_string(
            entry["candidate_id"], f"selection plan entries[{index}].candidate_id"
        )
        if identifier not in by_id:
            raise ValidationSetError("selection plan references an unknown candidate")
        if identifier in disposition_by_id:
            raise ValidationSetError("selection plan repeats a candidate")
        disposition = _require_enum(
            entry["disposition"],
            ("development", "locked", "rejected"),
            f"selection plan entries[{index}].disposition",
        )
        _require_string(entry["reason"], f"selection plan entries[{index}].reason")
        disposition_by_id[identifier] = disposition
        ordered_ids.append(identifier)
    if ordered_ids != sorted(ordered_ids):
        raise ValidationSetError("selection plan entries must be ordered by candidate_id")
    if set(disposition_by_id) != set(by_id):
        raise ValidationSetError(
            "selection plan must record a disposition for every candidate"
        )

    selected = {
        set_name: [
            by_id[identifier]
            for identifier in ordered_ids
            if disposition_by_id[identifier] == set_name
        ]
        for set_name in ("development", "locked")
    }
    if len(selected["development"]) != 60 or len(selected["locked"]) != 120:
        raise ValidationSetError("selection plan must select exactly 60/120 cases")
    development_curators = Counter(
        record["curator_id"] for record in selected["development"]
    )
    if sorted(development_curators.values()) != [30, 30]:
        raise ValidationSetError(
            "development selection must contain 30 cases from each curator"
        )
    curator_ids = set(development_curators)
    if len(curator_ids) != 2 or curator_c_id in curator_ids:
        raise ValidationSetError(
            "Curator-C and the two pool-curator identities must be distinct"
        )
    for stratum in STRATA:
        development_slots = Counter(
            record["subtype_slot"]
            for record in selected["development"]
            if record["stratum"] == stratum
        )
        if development_slots != Counter(
            {subtype: 1 for subtype in SUBTYPE_SLOTS[stratum]}
        ):
            raise ValidationSetError(
                f"development {stratum} needs exactly one case per subtype slot"
            )
    for stratum in STRATA:
        for subtype in SUBTYPE_SLOTS[stratum]:
            authors = Counter(
                record["curator_id"]
                for record in selected["locked"]
                if record["stratum"] == stratum
                and record["subtype_slot"] == subtype
            )
            if set(authors) != curator_ids or any(count != 1 for count in authors.values()):
                raise ValidationSetError(
                    f"locked {stratum}/{subtype} needs one case from each curator"
                )
    fraction_cases = [
        record
        for record in selected["locked"]
        if record["stratum"] == "S12"
        and record["subtype_slot"] == "fraction"
    ]
    fraction_surfaces: list[str] = []
    fraction_traits: list[tuple[bool, bool]] = []
    for record in fraction_cases:
        selected_spans = [
            span
            for span in record["expected_evidence_spans"]
            if span["disposition"] == "selected"
        ]
        if len(selected_spans) != 1 or not _FRACTION_PATTERN.fullmatch(
            selected_spans[0]["text"]
        ):
            raise ValidationSetError(
                "locked S12 fraction slot must use a simple fraction surface"
            )
        surface = selected_spans[0]["text"]
        numerator_text, denominator_text = surface.split("/", 1)
        numerator = abs(int(numerator_text, 10))
        denominator = int(denominator_text, 10)
        fraction_surfaces.append(surface)
        fraction_traits.append(
            (
                numerator < denominator,
                math.gcd(numerator, denominator) == 1,
            )
        )
    if len(set(fraction_surfaces)) != 2 or (
        fraction_traits[0][0] == fraction_traits[1][0]
        and fraction_traits[0][1] == fraction_traits[1][1]
    ):
        raise ValidationSetError(
            "locked S12 fraction surfaces must differ as proper/improper "
            "or reduced/unreduced forms"
        )
    return {
        "curator_c_id": curator_c_id,
        "development": selected["development"],
        "locked": selected["locked"],
        "near_duplicate_dispositions": list(near_duplicate_dispositions),
        "selection_plan_sha256": _require_sha256(
            selection_plan_sha256, "selection_plan_sha256"
        ),
        "curator_pool_seals": [dict(seal) for seal in curator_pool_seals],
    }


def validate_curator_c_selection(
    plan: Mapping[str, Any] | bytes,
    curator_a: Sequence[Mapping[str, Any]],
    curator_b: Sequence[Mapping[str, Any]],
    curator_a_seal: Mapping[str, Any],
    curator_b_seal: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and adapt the canonical production Curator-C selection artifact."""
    if isinstance(plan, bytes):
        source_bytes = plan
        source = parse_json_strict(source_bytes, "Curator-C selection")
    else:
        if not isinstance(plan, Mapping):
            raise ValidationSetError("Curator-C selection must be an object or bytes")
        source = dict(plan)
        source_bytes = canonical_json_bytes(source)
    _require_exact_fields(source, _CURATOR_C_SELECTION_FIELDS, "Curator-C selection")
    if source["schema_version"] != CURATOR_C_SELECTION_SCHEMA_VERSION:
        raise ValidationSetError("Curator-C selection schema_version is invalid")
    if source["status"] != "PASS":
        raise ValidationSetError("Curator-C selection status must equal PASS")
    if source["locked_label_status"] != "construction_intent_only":
        raise ValidationSetError(
            "Curator-C selection locked_label_status is invalid"
        )
    curator_c_id = _require_string(source["curator_id"], "Curator-C curator_id")
    if curator_c_id != REGISTERED_CURATOR_C_ID:
        raise ValidationSetError("Curator-C selection curator_id is invalid")
    if source["curator_model_id"] != REVIEWER_MODEL_ID:
        raise ValidationSetError("Curator-C selection model is invalid")
    if source["curator_reasoning_effort"] != REVIEWER_REASONING_EFFORT:
        raise ValidationSetError("Curator-C selection reasoning effort is invalid")
    constructed = _require_utc_timestamp(
        source["constructed_after_protocol_utc"],
        "Curator-C constructed_after_protocol_utc",
    )
    if constructed <= FROZEN_PROTOCOL_COMMIT_UTC:
        raise ValidationSetError(
            "Curator-C selection was not constructed after the final protocol"
        )
    validate_external_no_model_run_attestation(
        source["no_model_run_attestation"],
        context="curator_c_selection",
        name="Curator-C selection no_model_run_attestation",
    )
    _require_string(
        source["construction_intent_warning"],
        "Curator-C construction_intent_warning",
    )
    _validate_curator_c_selection_protocol_bindings(
        source["final_protocol_bindings"]
    )

    a_binding = validate_curator_pool_seal(curator_a_seal, curator_a)
    b_binding = validate_curator_pool_seal(curator_b_seal, curator_b)
    pool_bindings = {
        binding["curator_id"]: binding for binding in (a_binding, b_binding)
    }
    if set(pool_bindings) != set(SEALED_CURATOR_IDENTITIES):
        raise ValidationSetError(
            "curator pool seals must use the exact registered identities"
        )
    candidate_hashes = _validate_named_curator_hashes(
        source["candidate_jsonl_sha256s"],
        {
            curator_id: binding["candidate_jsonl_sha256"]
            for curator_id, binding in pool_bindings.items()
        },
        "candidate_jsonl_sha256s",
    )
    seal_hashes = _validate_named_curator_hashes(
        source["pool_seal_sha256s"],
        {
            curator_id: binding["seal_sha256"]
            for curator_id, binding in pool_bindings.items()
        },
        "pool_seal_sha256s",
    )
    summary_hashes = _validate_named_curator_hashes(
        source["pool_summary_sha256s"], None, "pool_summary_sha256s"
    )
    pools = [*a_binding["records"], *b_binding["records"]]
    by_id = {record["candidate_id"]: record for record in pools}
    if len(by_id) != 288:
        raise ValidationSetError("candidate IDs must be distinct across sealed pools")

    dispositions = source["candidate_dispositions"]
    _require_exact_fields(
        dispositions,
        _CURATOR_C_DISPOSITION_FIELDS,
        "candidate_dispositions",
    )
    disposition_lists = {
        field: _require_candidate_id_list(
            dispositions[field], f"candidate_dispositions.{field}"
        )
        for field in _CURATOR_C_DISPOSITION_FIELDS
    }
    partition = [
        candidate_id
        for field in _CURATOR_C_DISPOSITION_FIELDS
        for candidate_id in disposition_lists[field]
    ]
    if len(partition) != len(set(partition)) or set(partition) != set(by_id):
        raise ValidationSetError(
            "candidate_dispositions must partition all 288 sealed candidates"
        )
    selected_ids = source["selected_temp_candidate_ids"]
    _require_exact_fields(
        selected_ids,
        _CURATOR_C_SELECTED_FIELDS,
        "selected_temp_candidate_ids",
    )
    development_ids = _require_candidate_id_list(
        selected_ids["development"], "selected_temp_candidate_ids.development"
    )
    locked_ids = _require_candidate_id_list(
        selected_ids["locked"], "selected_temp_candidate_ids.locked"
    )
    if (
        development_ids
        != disposition_lists["selected_development_candidate_ids"]
        or locked_ids
        != disposition_lists["selected_locked_candidate_ids"]
        or len(development_ids) != 60
        or len(locked_ids) != 120
    ):
        raise ValidationSetError(
            "selected_temp_candidate_ids disagree with exact 60/120 dispositions"
        )
    entries: list[dict[str, str]] = []
    categories = (
        ("selected_development_candidate_ids", "development"),
        ("selected_locked_candidate_ids", "locked"),
        ("not_selected_duplicate_exclusion_candidate_ids", "rejected"),
        ("not_selected_alternative_candidate_ids", "rejected"),
    )
    for field, disposition in categories:
        for candidate_id in disposition_lists[field]:
            entries.append(
                {
                    "candidate_id": candidate_id,
                    "disposition": disposition,
                    "reason": f"Curator-C canonical disposition: {field}",
                }
            )
    entries.sort(key=lambda item: item["candidate_id"])

    selected = {
        "development": [by_id[item] for item in development_ids],
        "locked": [by_id[item] for item in locked_ids],
    }
    validate_dataset_composition(
        selected["development"], selected["locked"]
    )
    excluded_ids = _require_candidate_id_list(
        source["excluded_duplicate_ids"], "excluded_duplicate_ids"
    )
    if excluded_ids != disposition_lists[
        "not_selected_duplicate_exclusion_candidate_ids"
    ]:
        raise ValidationSetError(
            "excluded_duplicate_ids disagree with candidate dispositions"
        )
    reported_groups = _extract_reported_duplicate_groups(
        source["excluded_duplicate_groups"], set(by_id)
    )
    recomputed_groups = _duplicate_groups(pools)
    if set(reported_groups) != set(recomputed_groups):
        raise ValidationSetError(
            "excluded_duplicate_groups differ from normalized pool duplicates"
        )
    if any(
        not any(candidate_id in group for group in reported_groups)
        for candidate_id in excluded_ids
    ):
        raise ValidationSetError(
            "excluded duplicate candidate is absent from duplicate groups"
        )
    selected_overlap = detect_fixture_overlaps(
        selected["development"], selected["locked"]
    )
    require_no_hard_overlaps(selected_overlap)
    _validate_selected_overlap_claims(
        source["overlap_validation"], selected_overlap
    )
    near_evidence = _near_pair_evidence(
        [*selected["development"], *selected["locked"]]
    )
    near_dispositions = _validate_near_duplicate_screening(
        source["near_duplicate_screening"],
        near_evidence,
        development=selected["development"],
        locked=selected["locked"],
    )
    expected_selected_near = near_duplicate_report(
        selected["development"], selected["locked"]
    )
    validate_near_duplicate_dispositions(
        expected_selected_near, near_dispositions
    )
    _validate_actual_derived_feature_counts(
        source["actual_derived_feature_counts"],
        selected["development"],
        selected["locked"],
    )
    _validate_curator_c_count_tables(
        source["count_tables"],
        selected=selected,
        pools=pools,
    )
    if not isinstance(source["feature_derivation"], (Mapping, str)):
        raise ValidationSetError("feature_derivation must be an object or string")
    if isinstance(source["feature_derivation"], Mapping):
        _validate_pass_report(source["feature_derivation"], "feature_derivation")
    else:
        _require_string(source["feature_derivation"], "feature_derivation")
    _validate_pass_report(source["pool_validation"], "pool_validation")
    _validate_pass_report(source["quota_validation"], "quota_validation")
    _validate_pass_report(source["overlap_validation"], "overlap_validation")

    return _validate_internal_selection(
        entries=entries,
        near_duplicate_dispositions=near_dispositions,
        pools=pools,
        curator_c_id=curator_c_id,
        selection_plan_sha256=sha256_bytes(source_bytes),
        curator_pool_seals=(curator_a_seal, curator_b_seal),
    )


def validate_curator_c_summary(
    summary: Mapping[str, Any],
    selection: Mapping[str, Any],
    *,
    selection_sha256: str,
    candidate_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate the canonical Curator-C summary against its selection source."""
    _require_exact_fields(
        summary, _CURATOR_C_SUMMARY_FIELDS, "Curator-C summary"
    )
    _require_exact_fields(
        selection, _CURATOR_C_SELECTION_FIELDS, "Curator-C selection"
    )
    if summary["schema_version"] != CURATOR_C_SUMMARY_SCHEMA_VERSION:
        raise ValidationSetError("Curator-C summary schema_version is invalid")
    if (
        selection["schema_version"] != CURATOR_C_SELECTION_SCHEMA_VERSION
        or summary["status"] != "PASS"
        or selection["status"] != "PASS"
    ):
        raise ValidationSetError("Curator-C summary/selection status must be PASS")
    if not (
        summary["curator_id"]
        == selection["curator_id"]
        == REGISTERED_CURATOR_C_ID
    ):
        raise ValidationSetError("Curator-C summary curator binding mismatch")
    if (
        not (
            summary["curator_model_id"]
            == selection["curator_model_id"]
            == REVIEWER_MODEL_ID
        )
        or not (
            summary["curator_reasoning_effort"]
            == selection["curator_reasoning_effort"]
            == REVIEWER_REASONING_EFFORT
        )
    ):
        raise ValidationSetError("Curator-C summary model/effort binding mismatch")
    summary_timestamp = _require_utc_timestamp(
        summary["constructed_after_protocol_utc"],
        "Curator-C summary constructed_after_protocol_utc",
    )
    selection_timestamp = _require_utc_timestamp(
        selection["constructed_after_protocol_utc"],
        "Curator-C selection constructed_after_protocol_utc",
    )
    if (
        summary_timestamp != selection_timestamp
        or summary_timestamp <= FROZEN_PROTOCOL_COMMIT_UTC
    ):
        raise ValidationSetError("Curator-C summary timestamp binding is invalid")

    bindings = summary["protocol_bindings"]
    _require_exact_fields(
        bindings,
        _SUMMARY_PROTOCOL_BINDING_FIELDS,
        "Curator-C summary protocol_bindings",
    )
    selection_bindings = _validate_curator_c_selection_protocol_bindings(
        selection["final_protocol_bindings"]
    )
    selected_summary_bindings = {
        field: selection_bindings[field]
        for field in _SUMMARY_PROTOCOL_BINDING_FIELDS
    }
    if (
        bindings["protocol_commit"] != FROZEN_PROTOCOL_COMMIT
        or bindings["protocol_bundle_sha256"]
        != FROZEN_PROTOCOL_BUNDLE_SHA256
        or bindings["acceptance_gate_sha256"]
        != FROZEN_ACCEPTANCE_GATE_SHA256
        or bindings != selected_summary_bindings
    ):
        raise ValidationSetError("Curator-C summary protocol bindings mismatch")

    hashes = summary["hashes"]
    _require_exact_fields(
        hashes, _CURATOR_C_SUMMARY_HASH_FIELDS, "Curator-C summary hashes"
    )
    for field in ("candidate_jsonl_sha256s", "pool_seal_sha256s"):
        summary_hashes = hashes[field]
        selection_hashes = selection[field]
        checked_summary_hashes = _validate_named_curator_hashes(
            summary_hashes, None, f"Curator-C summary hashes.{field}"
        )
        checked_selection_hashes = _validate_named_curator_hashes(
            selection_hashes, None, f"Curator-C selection {field}"
        )
        if checked_summary_hashes != checked_selection_hashes:
            raise ValidationSetError(
                "Curator-C summary named pool bindings mismatch"
            )
    if _require_sha256(
        hashes["selection_sha256"],
        "Curator-C summary hashes.selection_sha256",
    ) != _require_sha256(selection_sha256, "Curator-C selection SHA-256"):
        raise ValidationSetError("Curator-C summary selection hash mismatch")

    dispositions = selection["candidate_dispositions"]
    _require_exact_fields(
        dispositions,
        _CURATOR_C_DISPOSITION_FIELDS,
        "Curator-C selection candidate_dispositions",
    )
    disposition_lists = {
        field: _require_candidate_id_list(
            dispositions[field], f"candidate_dispositions.{field}"
        )
        for field in _CURATOR_C_DISPOSITION_FIELDS
    }
    disposition_ids = [
        candidate_id
        for field in _CURATOR_C_DISPOSITION_FIELDS
        for candidate_id in disposition_lists[field]
    ]
    if len(disposition_ids) != len(set(disposition_ids)):
        raise ValidationSetError(
            "Curator-C summary disposition partition overlaps"
        )
    selected_temp_ids = selection["selected_temp_candidate_ids"]
    _require_exact_fields(
        selected_temp_ids,
        _CURATOR_C_SELECTED_FIELDS,
        "Curator-C selection selected_temp_candidate_ids",
    )
    if (
        _require_candidate_id_list(
            selected_temp_ids["development"],
            "selected_temp_candidate_ids.development",
        )
        != disposition_lists["selected_development_candidate_ids"]
        or _require_candidate_id_list(
            selected_temp_ids["locked"],
            "selected_temp_candidate_ids.locked",
        )
        != disposition_lists["selected_locked_candidate_ids"]
    ):
        raise ValidationSetError(
            "Curator-C summary selected IDs disagree with dispositions"
        )

    candidate_index: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(candidate_records):
        if not isinstance(record, Mapping):
            raise ValidationSetError(
                f"Curator-C summary candidate_records[{index}] must be an object"
            )
        candidate_id = _require_string(
            record.get("candidate_id"),
            f"Curator-C summary candidate_records[{index}].candidate_id",
        )
        if (
            not _CANDIDATE_ID_PATTERN.fullmatch(candidate_id)
            or candidate_id in candidate_index
        ):
            raise ValidationSetError(
                "Curator-C summary candidate membership is invalid"
            )
        _require_enum(
            record.get("stratum"),
            STRATA,
            f"Curator-C summary candidate_records[{index}].stratum",
        )
        _require_string(
            record.get("output_text"),
            f"Curator-C summary candidate_records[{index}].output_text",
            nonempty=False,
        )
        _require_string(
            record.get("template_family_id"),
            f"Curator-C summary candidate_records[{index}].template_family_id",
        )
        candidate_index[candidate_id] = record
    if set(disposition_ids) != set(candidate_index):
        raise ValidationSetError(
            "Curator-C summary dispositions do not partition the candidate pools"
        )

    development_ids = disposition_lists[
        "selected_development_candidate_ids"
    ]
    locked_ids = disposition_lists["selected_locked_candidate_ids"]
    development = [candidate_index[candidate_id] for candidate_id in development_ids]
    locked = [candidate_index[candidate_id] for candidate_id in locked_ids]
    overlap = detect_fixture_overlaps(development, locked)

    excluded_groups = selection["excluded_duplicate_groups"]
    if not isinstance(excluded_groups, list):
        raise ValidationSetError(
            "Curator-C selection excluded_duplicate_groups must be a list"
        )
    excluded_ids = _require_candidate_id_list(
        selection["excluded_duplicate_ids"],
        "Curator-C selection excluded_duplicate_ids",
    )
    if (
        excluded_ids
        != disposition_lists[
            "not_selected_duplicate_exclusion_candidate_ids"
        ]
    ):
        raise ValidationSetError(
            "Curator-C summary excluded IDs disagree with dispositions"
        )
    near_screening = selection["near_duplicate_screening"]
    if not isinstance(near_screening, Mapping):
        raise ValidationSetError(
            "Curator-C selection near_duplicate_screening must be an object"
        )
    near_flags = near_screening.get("flags")
    if not isinstance(near_flags, list):
        raise ValidationSetError(
            "Curator-C selection near_duplicate_screening.flags must be a list"
        )
    non_s12_flags = 0
    seen_near_pairs: set[tuple[str, str]] = set()
    for index, flag in enumerate(near_flags):
        if not isinstance(flag, Mapping):
            raise ValidationSetError(
                f"near_duplicate_screening.flags[{index}] must be an object"
            )
        pair_ids = _require_candidate_id_list(
            flag.get("candidate_ids"),
            f"near_duplicate_screening.flags[{index}].candidate_ids",
        )
        if len(pair_ids) != 2 or any(
            candidate_id not in candidate_index for candidate_id in pair_ids
        ):
            raise ValidationSetError(
                f"near_duplicate_screening.flags[{index}] has invalid membership"
            )
        pair = tuple(sorted(pair_ids))
        if pair in seen_near_pairs:
            raise ValidationSetError(
                "Curator-C summary near-duplicate flags repeat a pair"
            )
        seen_near_pairs.add(pair)
        if any(candidate_index[item]["stratum"] != "S12" for item in pair):
            non_s12_flags += 1

    def validate_near_counts(value: Any, name: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                normalized_key = _report_key(
                    _require_string(key, f"{name} key")
                )
                expected: int | None = None
                if (
                    "non_s12" in normalized_key
                    and "flag" in normalized_key
                    and type(child) is int
                ):
                    expected = non_s12_flags
                elif (
                    "flag" in normalized_key
                    and "non_s12" not in normalized_key
                    and type(child) is int
                ):
                    expected = len(near_flags)
                if expected is not None and type(child) is int and child != expected:
                    raise ValidationSetError(
                        f"{name}.{key} differs from its exact flags"
                    )
                validate_near_counts(child, f"{name}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                validate_near_counts(child, f"{name}[{index}]")

    validate_near_counts(
        near_screening, "Curator-C near_duplicate_screening"
    )

    overlap_expected = {
        "exact": len(overlap["exact_duplicates"]),
        "normalized": len(overlap["normalized_duplicates"]),
        "template": len(overlap["cross_set_template_family_overlaps"]),
    }
    overlap_expected["hard"] = sum(overlap_expected.values())
    overlap_bindings = 0

    def validate_overlap_bindings(value: Any, name: str) -> None:
        nonlocal overlap_bindings
        if isinstance(value, Mapping):
            for key, child in value.items():
                normalized_key = _report_key(
                    _require_string(key, f"{name} key")
                )
                expected: int | None = None
                if "hard_failure" in normalized_key and "count" in normalized_key:
                    expected = overlap_expected["hard"]
                elif (
                    "normalized" in normalized_key
                    and "duplicate" in normalized_key
                ):
                    expected = overlap_expected["normalized"]
                elif (
                    "exact" in normalized_key
                    and "duplicate" in normalized_key
                ):
                    expected = overlap_expected["exact"]
                elif (
                    "template_family" in normalized_key
                    and "overlap" in normalized_key
                ):
                    expected = overlap_expected["template"]
                if expected is not None and (
                    type(child) is int or isinstance(child, list)
                ):
                    actual = child if type(child) is int else len(child)
                    if actual != expected:
                        raise ValidationSetError(
                            f"{name}.{key} differs from selected candidates"
                        )
                    overlap_bindings += 1
                validate_overlap_bindings(child, f"{name}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                validate_overlap_bindings(child, f"{name}[{index}]")

    overlap_validation = selection["overlap_validation"]
    _validate_pass_report(overlap_validation, "Curator-C overlap_validation")
    validate_overlap_bindings(
        overlap_validation, "Curator-C overlap_validation"
    )
    if overlap_bindings == 0:
        raise ValidationSetError(
            "Curator-C overlap_validation lacks recomputable counts"
        )

    unselected = (
        len(
            disposition_lists[
                "not_selected_duplicate_exclusion_candidate_ids"
            ]
        )
        + len(disposition_lists["not_selected_alternative_candidate_ids"])
    )
    expected_counts = {
        "candidate_pool_total": len(candidate_index),
        "development": len(development_ids),
        "duplicate_groups_observed": len(excluded_groups),
        "excluded_duplicate_ids": len(excluded_ids),
        "locked": len(locked_ids),
        "near_duplicate_flags": len(near_flags),
        "near_duplicate_non_s12_flags": non_s12_flags,
        "selected_exact_duplicates": len(overlap["exact_duplicates"]),
        "selected_frozen_normalized_duplicates": len(
            overlap["normalized_duplicates"]
        ),
        "selected_total": len(development_ids) + len(locked_ids),
        "template_family_overlaps": len(
            overlap["cross_set_template_family_overlaps"]
        ),
        "unselected": unselected,
    }
    counts = summary["counts"]
    _require_exact_fields(
        counts, _CURATOR_C_SUMMARY_COUNT_FIELDS, "Curator-C summary counts"
    )
    checked_counts = {
        field: _require_int(
            counts[field], f"Curator-C summary counts.{field}", minimum=0
        )
        for field in _CURATOR_C_SUMMARY_COUNT_FIELDS
    }
    if (
        checked_counts != expected_counts
        or checked_counts["candidate_pool_total"] != 288
        or checked_counts["development"] != 60
        or checked_counts["locked"] != 120
        or checked_counts["selected_total"] != 180
        or checked_counts["unselected"] != 108
    ):
        raise ValidationSetError("Curator-C summary selection counts mismatch")
    return {"counts": checked_counts, "status": "PASS"}


def validate_eligible_production_bundle(
    artifact_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    """Hash-gate the exact registered production bundle before normalization."""
    expected_keys = frozenset(ELIGIBLE_PRODUCTION_ARTIFACT_SHA256)
    _require_exact_fields(
        artifact_bytes, expected_keys, "eligible production artifact bundle"
    )
    for name in ELIGIBLE_PRODUCTION_ARTIFACT_SHA256:
        data = artifact_bytes[name]
        if type(data) is not bytes:
            raise ValidationSetError(
                f"eligible production artifact {name} must be exact bytes"
            )
        if sha256_bytes(data) != ELIGIBLE_PRODUCTION_ARTIFACT_SHA256[name]:
            raise ValidationSetError(
                f"eligible production artifact hash mismatch: {name}"
            )

    curator_a = parse_jsonl_strict(
        artifact_bytes["curator_a_candidate_jsonl"],
        "registered Curator-A candidate JSONL",
    )
    curator_b = parse_jsonl_strict(
        artifact_bytes["curator_b_candidate_jsonl"],
        "registered Curator-B candidate JSONL",
    )
    curator_a_seal = parse_json_strict(
        artifact_bytes["curator_a_pool_seal"],
        "registered Curator-A pool seal",
    )
    curator_b_seal = parse_json_strict(
        artifact_bytes["curator_b_pool_seal"],
        "registered Curator-B pool seal",
    )
    selection = parse_json_strict(
        artifact_bytes["curator_c_selection"],
        "registered Curator-C selection",
    )
    summary = parse_json_strict(
        artifact_bytes["curator_c_summary"],
        "registered Curator-C summary",
    )
    _require_exact_fields(
        selection, _CURATOR_C_SELECTION_FIELDS, "Curator-C selection"
    )
    sealed_sources = (
        (
            curator_a_seal,
            artifact_bytes["curator_a_candidate_jsonl"],
            artifact_bytes["curator_a_pool_seal"],
        ),
        (
            curator_b_seal,
            artifact_bytes["curator_b_candidate_jsonl"],
            artifact_bytes["curator_b_pool_seal"],
        ),
    )
    raw_candidate_hashes: dict[str, str] = {}
    raw_seal_hashes: dict[str, str] = {}
    for index, (seal, candidate_bytes, seal_bytes) in enumerate(sealed_sources):
        if not isinstance(seal, Mapping):
            raise ValidationSetError(
                f"registered curator pool seal[{index}] must be an object"
            )
        curator_id = _require_string(
            seal.get("curator_id"),
            f"registered curator pool seal[{index}].curator_id",
        )
        if curator_id in raw_candidate_hashes:
            raise ValidationSetError(
                "registered curator pool seals repeat an identity"
            )
        raw_candidate_hashes[curator_id] = sha256_bytes(candidate_bytes)
        raw_seal_hashes[curator_id] = sha256_bytes(seal_bytes)
    _validate_named_curator_hashes(
        selection["candidate_jsonl_sha256s"],
        raw_candidate_hashes,
        "Curator-C candidate_jsonl_sha256s",
    )
    _validate_named_curator_hashes(
        selection["pool_seal_sha256s"],
        raw_seal_hashes,
        "Curator-C pool_seal_sha256s",
    )
    _validate_named_curator_hashes(
        selection["pool_summary_sha256s"],
        None,
        "Curator-C pool_summary_sha256s",
    )
    summary_validation = validate_curator_c_summary(
        summary,
        selection,
        selection_sha256=sha256_bytes(
            artifact_bytes["curator_c_selection"]
        ),
        candidate_records=[*curator_a, *curator_b],
    )
    if (
        summary_validation["counts"]
        != ELIGIBLE_PRODUCTION_CURATOR_C_SUMMARY_COUNTS
    ):
        raise ValidationSetError(
            "Curator-C summary does not contain the registered corrected counts"
        )
    return {
        "curator_a": curator_a,
        "curator_b": curator_b,
        "curator_a_seal": curator_a_seal,
        "curator_b_seal": curator_b_seal,
        "selection": selection,
        "summary": summary,
    }


def validate_selection_plan(
    plan: Mapping[str, Any] | bytes,
    curator_a: Sequence[Mapping[str, Any]],
    curator_b: Sequence[Mapping[str, Any]],
    curator_a_seal: Mapping[str, Any],
    curator_b_seal: Mapping[str, Any],
) -> dict[str, Any]:
    """Production ingress accepts only the sealed Curator-C selection schema."""
    return validate_curator_c_selection(
        plan, curator_a, curator_b, curator_a_seal, curator_b_seal
    )


def _copy_expected_fields(
    candidate: Mapping[str, Any], schema_version: str, case_id: str
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "case_id": case_id,
        **{
            field: candidate[field]
            for field in _DEVELOPMENT_FIELDS
            if field not in {"schema_version", "case_id"}
        },
    }


def candidate_to_development(
    candidate: Mapping[str, Any], case_id: str
) -> DevelopmentRecord:
    validate_candidate_fixture(candidate)
    _require_case_id(case_id)
    record = _copy_expected_fields(
        candidate, DEVELOPMENT_SCHEMA_VERSION, case_id
    )
    validate_development_record(record)
    return record  # type: ignore[return-value]


def candidate_to_locked_input(
    candidate: Mapping[str, Any], case_id: str
) -> LockedInput:
    validate_candidate_fixture(candidate)
    _require_case_id(case_id)
    record: LockedInput = {
        "schema_version": LOCKED_INPUT_SCHEMA_VERSION,
        "case_id": case_id,
        "source_kind": SOURCE_KIND,
        "output_text": candidate["output_text"],
        "parse_type": "numeric",
    }
    validate_locked_input(record)
    return record


def candidate_to_final_label(
    candidate: Mapping[str, Any], case_id: str
) -> dict[str, Any]:
    """Create a private draft label; reviewer consensus must supersede it."""
    validate_candidate_fixture(candidate)
    record = {
        **_copy_expected_fields(candidate, FINAL_LABEL_SCHEMA_VERSION, case_id),
        **{
            field: candidate[field]
            for field in _LOCKED_LABEL_EXTRA_FIELDS
        },
    }
    validate_final_label(record)
    return record


def materialize_selection(
    selection: Mapping[str, Any], private_salts: Mapping[str, Any]
) -> dict[str, Any]:
    """Assign deterministic opaque IDs and return ordered draft artifacts."""
    salts = validate_private_salts(private_salts)
    development_pairs = [
        (
            derive_case_id(
                salts["development"], candidate["parse_type"], candidate["output_text"]
            ),
            candidate,
        )
        for candidate in selection["development"]
    ]
    locked_pairs = [
        (
            derive_case_id(
                salts["locked"], candidate["parse_type"], candidate["output_text"]
            ),
            candidate,
        )
        for candidate in selection["locked"]
    ]
    all_ids = [identifier for identifier, _ in development_pairs + locked_pairs]
    if len(all_ids) != len(set(all_ids)):
        raise ValidationSetError("derived opaque case IDs collide")
    development_pairs.sort(key=lambda item: item[0])
    locked_pairs.sort(key=lambda item: item[0])
    development = [
        candidate_to_development(candidate, identifier)
        for identifier, candidate in development_pairs
    ]
    locked_inputs = [
        candidate_to_locked_input(candidate, identifier)
        for identifier, candidate in locked_pairs
    ]
    locked_draft_labels = [
        candidate_to_final_label(candidate, identifier)
        for identifier, candidate in locked_pairs
    ]
    return {
        "development": development,
        "locked_inputs": locked_inputs,
        "locked_draft_labels": locked_draft_labels,
        "development_pairs": development_pairs,
        "locked_pairs": locked_pairs,
    }


_MAPPING_FIELDS = frozenset(
    {
        "schema_version",
        "protocol_commit",
        "selection_plan_sha256",
        "curator_c_id",
        "custodian_id",
        "curator_pool_seals",
        "id_salts",
        "entries",
    }
)
_MAPPING_ENTRY_FIELDS = frozenset(
    {
        "case_id",
        "set",
        "candidate_id",
        "curator_id",
        "stratum",
        "subtype_slot",
        "template_family_id",
        "output_sha256",
    }
)


def build_case_mapping(
    materialized: Mapping[str, Any],
    private_salts: Mapping[str, Any],
    selection_plan_sha256: str,
    *,
    curator_c_id: str,
    custodian_id: str,
    curator_pool_seals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    salts = validate_private_salts(private_salts)
    _require_sha256(selection_plan_sha256, "selection_plan_sha256")
    entries: list[dict[str, Any]] = []
    for set_name, pairs in (
        ("development", materialized["development_pairs"]),
        ("locked", materialized["locked_pairs"]),
    ):
        for case_id, candidate in pairs:
            entries.append(
                {
                    "case_id": case_id,
                    "set": set_name,
                    "candidate_id": candidate["candidate_id"],
                    "curator_id": candidate["curator_id"],
                    "stratum": candidate["stratum"],
                    "subtype_slot": candidate["subtype_slot"],
                    "template_family_id": candidate["template_family_id"],
                    "output_sha256": sha256_bytes(
                        candidate["output_text"].encode("utf-8")
                    ),
                }
            )
    entries.sort(key=lambda item: item["case_id"])
    mapping = {
        "schema_version": MAPPING_SCHEMA_VERSION,
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "selection_plan_sha256": selection_plan_sha256,
        "curator_c_id": curator_c_id,
        "custodian_id": custodian_id,
        "curator_pool_seals": [dict(seal) for seal in curator_pool_seals],
        "id_salts": salts,
        "entries": entries,
    }
    validate_case_mapping(mapping)
    return mapping


def validate_case_mapping(record: Mapping[str, Any]) -> dict[str, Any]:
    _require_exact_fields(record, _MAPPING_FIELDS, "case mapping")
    if record["schema_version"] != MAPPING_SCHEMA_VERSION:
        raise ValidationSetError("case mapping schema_version is invalid")
    if _require_commit(record["protocol_commit"], "mapping protocol_commit") != FROZEN_PROTOCOL_COMMIT:
        raise ValidationSetError("case mapping protocol_commit is not frozen")
    _require_sha256(record["selection_plan_sha256"], "selection_plan_sha256")
    curator_c_id = _require_string(record["curator_c_id"], "mapping curator_c_id")
    custodian_id = _require_string(record["custodian_id"], "mapping custodian_id")
    if curator_c_id != REGISTERED_CURATOR_C_ID:
        raise ValidationSetError("mapping Curator-C identity is not registered")
    if custodian_id != REGISTERED_CUSTODIAN_ID:
        raise ValidationSetError("mapping custodian identity is not registered")
    if not isinstance(record["curator_pool_seals"], list) or len(
        record["curator_pool_seals"]
    ) != 2:
        raise ValidationSetError("mapping must bind exactly two curator pool seals")
    sealed_curators: list[str] = []
    for index, seal in enumerate(record["curator_pool_seals"]):
        name = f"mapping curator_pool_seals[{index}]"
        _require_exact_fields(seal, _CURATOR_POOL_SEAL_FIELDS, name)
        if (
            seal["schema_version"] != CURATOR_POOL_SEAL_SCHEMA_VERSION
            or seal["curator_model_id"] != REVIEWER_MODEL_ID
            or seal["curator_reasoning_effort"] != REVIEWER_REASONING_EFFORT
            or seal["protocol_commit"] != FROZEN_PROTOCOL_COMMIT
            or seal["protocol_bundle_sha256"] != FROZEN_PROTOCOL_BUNDLE_SHA256
            or seal["acceptance_gate_sha256"] != FROZEN_ACCEPTANCE_GATE_SHA256
            or seal["candidate_schema_version"]
            != CURATOR_CANDIDATE_SCHEMA_VERSION
            or seal["candidate_count"] != 144
        ):
            raise ValidationSetError(f"{name} has invalid final-protocol bindings")
        validate_external_no_model_run_attestation(
            seal["no_model_run_attestation"],
            context="curator_pool",
            name=f"{name}.no_model_run_attestation",
        )
        sealed_curators.append(
            _require_string(seal["curator_id"], f"{name}.curator_id")
        )
        _require_sha256(
            seal["ordered_candidate_ids_sha256"],
            f"{name}.ordered_candidate_ids_sha256",
        )
        _require_sha256(
            seal["candidate_jsonl_sha256"], f"{name}.candidate_jsonl_sha256"
        )
        constructed = _require_utc_timestamp(
            seal["constructed_after_protocol_utc"],
            f"{name}.constructed_after_protocol_utc",
        )
        if constructed <= FROZEN_PROTOCOL_COMMIT_UTC:
            raise ValidationSetError(f"{name} predates the final protocol")
    construction_actors = {*sealed_curators, curator_c_id, custodian_id}
    if len(set(sealed_curators)) != 2 or len(construction_actors) != 4:
        raise ValidationSetError(
            "mapping curator, Curator-C, and custodian identities are not distinct"
        )
    if not isinstance(record["id_salts"], Mapping):
        raise ValidationSetError("mapping id_salts must be an object")
    salts = record["id_salts"]
    _require_exact_fields(salts, {"development", "locked"}, "mapping id_salts")
    for name in ("development", "locked"):
        if len(_require_string(salts[name], f"id_salts.{name}").encode("utf-8")) < 16:
            raise ValidationSetError("mapping ID salts must contain at least 16 bytes")
    if salts["development"] == salts["locked"]:
        raise ValidationSetError("mapping ID salts must be distinct")
    if not isinstance(record["entries"], list):
        raise ValidationSetError("mapping entries must be a list")
    ids: list[str] = []
    candidate_ids: list[str] = []
    counts = Counter()
    curator_counts: dict[str, Counter[str]] = defaultdict(Counter)
    stratum_counts: dict[str, Counter[str]] = defaultdict(Counter)
    subtype_counts: Counter[tuple[str, str, str]] = Counter()
    locked_subtype_authors: dict[tuple[str, str], Counter[str]] = defaultdict(
        Counter
    )
    template_sets: dict[str, set[str]] = defaultdict(set)
    for index, entry in enumerate(record["entries"]):
        _require_exact_fields(
            entry, _MAPPING_ENTRY_FIELDS, f"mapping entries[{index}]"
        )
        case_id = _require_case_id(entry["case_id"], f"mapping entries[{index}].case_id")
        ids.append(case_id)
        set_name = _require_enum(
            entry["set"], ("development", "locked"), f"mapping entries[{index}].set"
        )
        counts[set_name] += 1
        candidate_id = _require_string(
            entry["candidate_id"], f"mapping entries[{index}].candidate_id"
        )
        if not _CANDIDATE_ID_PATTERN.fullmatch(candidate_id):
            raise ValidationSetError(
                f"mapping entries[{index}].candidate_id has invalid syntax"
            )
        candidate_ids.append(candidate_id)
        curator_id = _require_string(
            entry["curator_id"], f"mapping entries[{index}].curator_id"
        )
        curator_counts[set_name][curator_id] += 1
        stratum = _require_enum(
            entry["stratum"], STRATA, f"mapping entries[{index}].stratum"
        )
        stratum_counts[set_name][stratum] += 1
        subtype = _require_enum(
            entry["subtype_slot"],
            SUBTYPE_SLOTS[stratum],
            f"mapping entries[{index}].subtype_slot",
        )
        subtype_counts[(set_name, stratum, subtype)] += 1
        if set_name == "locked":
            locked_subtype_authors[(stratum, subtype)][curator_id] += 1
        template = _require_string(
            entry["template_family_id"],
            f"mapping entries[{index}].template_family_id",
            maximum=128,
        )
        template_sets[set_name].add(template)
        _require_sha256(
            entry["output_sha256"], f"mapping entries[{index}].output_sha256"
        )
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValidationSetError("mapping entries must have unique sorted case IDs")
    if counts != Counter({"development": 60, "locked": 120}):
        raise ValidationSetError("mapping must contain exactly 60/120 entries")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValidationSetError("mapping candidate IDs must be unique")
    curator_ids = set(curator_counts["development"]) | set(
        curator_counts["locked"]
    )
    if (
        len(curator_ids) != 2
        or curator_counts["development"]
        != Counter({curator: 30 for curator in curator_ids})
        or curator_counts["locked"]
        != Counter({curator: 60 for curator in curator_ids})
    ):
        raise ValidationSetError("mapping curator composition is invalid")
    if curator_ids != set(sealed_curators):
        raise ValidationSetError("mapping entries disagree with sealed curator identities")
    if stratum_counts["development"] != Counter(
        {stratum: 5 for stratum in STRATA}
    ) or stratum_counts["locked"] != Counter(
        {stratum: 10 for stratum in STRATA}
    ):
        raise ValidationSetError("mapping stratum composition is invalid")
    for stratum in STRATA:
        for subtype in SUBTYPE_SLOTS[stratum]:
            if subtype_counts[("development", stratum, subtype)] != 1:
                raise ValidationSetError(
                    "mapping development subtype composition is invalid"
                )
            if locked_subtype_authors[(stratum, subtype)] != Counter(
                {curator: 1 for curator in curator_ids}
            ):
                raise ValidationSetError(
                    "mapping locked subtype authorship is invalid"
                )
    if template_sets["development"] & template_sets["locked"]:
        raise ValidationSetError(
            "mapping template families overlap development and locked sets"
        )
    return {"counts": dict(counts)}


def validate_release_against_eligible_production(
    files: Mapping[str, bytes],
    production_artifact_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    """Bind a staged release to the exact registered six-artifact source bundle."""
    production = validate_eligible_production_bundle(production_artifact_bytes)
    selected = validate_selection_plan(
        production["selection"],
        production["curator_a"],
        production["curator_b"],
        production["curator_a_seal"],
        production["curator_b_seal"],
    )
    mapping_path = "manifests/locked_case_mapping.json"
    development_path = "development/development_cases.jsonl"
    locked_inputs_path = "locked-inputs/locked_inputs.jsonl"
    for path in (mapping_path, development_path, locked_inputs_path):
        if path not in files or type(files[path]) is not bytes:
            raise ValidationSetError(
                "production binding requires exact staged release members"
            )
    mapping = parse_json_strict(files[mapping_path], mapping_path)
    validate_case_mapping(mapping)
    private_salts = {
        "schema_version": PRIVATE_SALTS_SCHEMA_VERSION,
        "development_id_salt": mapping["id_salts"]["development"],
        "locked_id_salt": mapping["id_salts"]["locked"],
    }
    materialized = materialize_selection(selected, private_salts)
    expected_mapping = build_case_mapping(
        materialized,
        private_salts,
        selected["selection_plan_sha256"],
        curator_c_id=selected["curator_c_id"],
        custodian_id=REGISTERED_CUSTODIAN_ID,
        curator_pool_seals=selected["curator_pool_seals"],
    )
    if mapping != expected_mapping:
        raise ValidationSetError(
            "staged case mapping differs from the registered production selection"
        )
    if files[development_path] != canonical_jsonl_bytes(
        materialized["development"]
    ):
        raise ValidationSetError(
            "staged development cases differ from the registered production selection"
        )
    if files[locked_inputs_path] != canonical_jsonl_bytes(
        materialized["locked_inputs"]
    ):
        raise ValidationSetError(
            "staged locked inputs differ from the registered production selection"
        )
    return {
        "selection_plan_sha256": selected["selection_plan_sha256"],
        "development_count": len(materialized["development"]),
        "locked_count": len(materialized["locked_inputs"]),
        "registered_draft_labels": materialized["locked_draft_labels"],
    }


_EXTRACTION_FIELD_NAMES = (
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


def _locked_input_index(
    locked_inputs: Sequence[Mapping[str, Any]], *, require_120: bool = True
) -> dict[str, Mapping[str, Any]]:
    if require_120 and len(locked_inputs) != 120:
        raise ValidationSetError("locked input packet must contain exactly 120 rows")
    index: dict[str, Mapping[str, Any]] = {}
    ids: list[str] = []
    for row_number, record in enumerate(locked_inputs):
        checked = validate_locked_input(record, name=f"locked_inputs[{row_number}]")
        case_id = checked["case_id"]
        if case_id in index:
            raise ValidationSetError("locked input packet has duplicate case_id")
        index[case_id] = record
        ids.append(case_id)
    if ids != sorted(ids):
        raise ValidationSetError("locked input packet must be ordered by case_id")
    return index


def validate_stage1_row(
    record: Mapping[str, Any],
    locked_input: Mapping[str, Any],
    *,
    expected_packet_sha256: str | None = None,
    name: str = "stage1 row",
) -> dict[str, Any]:
    """Validate one reviewer extraction row with no reference-bearing fields."""
    _require_exact_fields(record, _STAGE1_FIELDS, name)
    if record["schema_version"] != STAGE1_REVIEW_SCHEMA_VERSION:
        raise ValidationSetError(f"{name}.schema_version is invalid")
    if record["review_stage"] != "stage1":
        raise ValidationSetError(f"{name}.review_stage must equal stage1")
    locked = validate_locked_input(locked_input)
    case_id = _require_case_id(record["case_id"], f"{name}.case_id")
    if case_id != locked["case_id"]:
        raise ValidationSetError(f"{name}.case_id does not match locked input")
    reviewer_id = _require_string(record["reviewer_id"], f"{name}.reviewer_id")
    if record["reviewer_model_id"] != REVIEWER_MODEL_ID:
        raise ValidationSetError(f"{name}.reviewer_model_id is invalid")
    if record["reviewer_reasoning_effort"] != REVIEWER_REASONING_EFFORT:
        raise ValidationSetError(f"{name}.reviewer_reasoning_effort is invalid")
    packet_hash = _require_sha256(record["packet_sha256"], f"{name}.packet_sha256")
    if expected_packet_sha256 is not None and packet_hash != expected_packet_sha256:
        raise ValidationSetError(f"{name}.packet_sha256 mismatch")
    extraction = _validate_extraction_fields(
        record, locked["output_text"], allow_inconclusive=True
    )
    notes = _require_string(record["notes"], f"{name}.notes", nonempty=False)
    return {
        "case_id": case_id,
        "reviewer_id": reviewer_id,
        "packet_sha256": packet_hash,
        "extraction": extraction,
        "notes": notes,
    }


def validate_stage1_submission(
    rows: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
    *,
    packet_sha256: str | None = None,
) -> dict[str, Any]:
    """Require one complete 120/120 Stage-1 reviewer submission."""
    locked = _locked_input_index(locked_inputs)
    expected_hash = packet_sha256 or sha256_bytes(
        canonical_jsonl_bytes(list(locked_inputs))
    )
    _require_sha256(expected_hash, "Stage-1 packet SHA-256")
    if len(rows) != 120:
        raise ValidationSetError("Stage-1 reviewer submission must contain 120 rows")
    reviewer_ids: set[str] = set()
    seen: set[str] = set()
    ordered_ids: list[str] = []
    unresolved: list[str] = []
    for index, row in enumerate(rows):
        case_id = row.get("case_id")
        if case_id not in locked:
            raise ValidationSetError("Stage-1 row has an unknown case_id")
        checked = validate_stage1_row(
            row,
            locked[case_id],
            expected_packet_sha256=expected_hash,
            name=f"Stage-1 rows[{index}]",
        )
        if checked["case_id"] in seen:
            raise ValidationSetError("Stage-1 submission has duplicate case_id")
        seen.add(checked["case_id"])
        ordered_ids.append(checked["case_id"])
        reviewer_ids.add(checked["reviewer_id"])
        if checked["extraction"]["answer_presence"] == "inconclusive":
            unresolved.append(checked["case_id"])
    if seen != set(locked) or ordered_ids != sorted(ordered_ids):
        raise ValidationSetError(
            "Stage-1 submission must exactly cover ordered locked case IDs"
        )
    if len(reviewer_ids) != 1:
        raise ValidationSetError("Stage-1 submission must have one reviewer identity")
    return {
        "reviewer_id": next(iter(reviewer_ids)),
        "packet_sha256": expected_hash,
        "submission_sha256": sha256_bytes(canonical_jsonl_bytes(list(rows))),
        "row_count": 120,
        "unresolved_ids": unresolved,
    }


def _extraction_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {field: row[field] for field in _EXTRACTION_FIELD_NAMES}


def stage1_disagreement_ids(
    reviewer_a: Sequence[Mapping[str, Any]],
    reviewer_b: Sequence[Mapping[str, Any]],
) -> list[str]:
    if len(reviewer_a) != len(reviewer_b):
        raise ValidationSetError("Stage-1 submissions have different lengths")
    by_b = {row.get("case_id"): row for row in reviewer_b}
    disagreements: list[str] = []
    for row in reviewer_a:
        case_id = row.get("case_id")
        other = by_b.get(case_id)
        if other is None or _extraction_payload(row) != _extraction_payload(other):
            disagreements.append(case_id)
    return sorted(_require_case_id(item) for item in disagreements)


def validate_stage1_arbitration(
    rows: Sequence[Mapping[str, Any]],
    reviewer_a: Sequence[Mapping[str, Any]],
    reviewer_b: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate reference-blind extraction arbitration and build full consensus."""
    a = validate_stage1_submission(reviewer_a, locked_inputs)
    b = validate_stage1_submission(
        reviewer_b, locked_inputs, packet_sha256=a["packet_sha256"]
    )
    if a["reviewer_id"] == b["reviewer_id"]:
        raise ValidationSetError("Stage-1 reviewer identities must be distinct")
    triggered = stage1_disagreement_ids(reviewer_a, reviewer_b)
    if len(rows) != len(triggered):
        raise ValidationSetError(
            "Stage-1 arbitration must exactly cover extraction disagreements"
        )
    locked = _locked_input_index(locked_inputs)
    arbitration_by_id: dict[str, Mapping[str, Any]] = {}
    arbiter_ids: set[str] = set()
    ordered_ids: list[str] = []
    for index, row in enumerate(rows):
        name = f"Stage-1 arbitration[{index}]"
        _require_exact_fields(row, _STAGE1_ARBITRATION_FIELDS, name)
        if row["schema_version"] != STAGE1_ARBITRATION_SCHEMA_VERSION:
            raise ValidationSetError(f"{name}.schema_version is invalid")
        if row["review_stage"] != "stage1_arbitration":
            raise ValidationSetError(f"{name}.review_stage is invalid")
        case_id = _require_case_id(row["case_id"], f"{name}.case_id")
        if case_id not in locked or case_id in arbitration_by_id:
            raise ValidationSetError(f"{name}.case_id is unknown or duplicate")
        arbiter_id = _require_string(row["arbiter_id"], f"{name}.arbiter_id")
        if arbiter_id in {a["reviewer_id"], b["reviewer_id"]}:
            raise ValidationSetError("Stage-1 arbiter must be a third identity")
        arbiter_ids.add(arbiter_id)
        if row["arbiter_model_id"] != REVIEWER_MODEL_ID:
            raise ValidationSetError(f"{name}.arbiter_model_id is invalid")
        if row["arbiter_reasoning_effort"] != REVIEWER_REASONING_EFFORT:
            raise ValidationSetError(f"{name}.arbiter_reasoning_effort is invalid")
        if row["packet_sha256"] != a["packet_sha256"]:
            raise ValidationSetError(f"{name}.packet_sha256 mismatch")
        if row["reviewer_a_submission_sha256"] != a["submission_sha256"]:
            raise ValidationSetError(f"{name} reviewer-A hash mismatch")
        if row["reviewer_b_submission_sha256"] != b["submission_sha256"]:
            raise ValidationSetError(f"{name} reviewer-B hash mismatch")
        _validate_extraction_fields(row, locked[case_id]["output_text"])
        _require_string(
            row["resolution_notes"], f"{name}.resolution_notes", nonempty=False
        )
        arbitration_by_id[case_id] = row
        ordered_ids.append(case_id)
    if ordered_ids != triggered:
        raise ValidationSetError(
            "Stage-1 arbitration IDs must equal ordered disagreement IDs"
        )
    if rows and len(arbiter_ids) != 1:
        raise ValidationSetError("Stage-1 arbitration must use one arbiter identity")

    by_a = {row["case_id"]: row for row in reviewer_a}
    by_b = {row["case_id"]: row for row in reviewer_b}
    consensus: list[dict[str, Any]] = []
    for case_id in sorted(locked):
        if case_id in arbitration_by_id:
            source_row = arbitration_by_id[case_id]
            source = "stage1_arbitration"
        else:
            if _extraction_payload(by_a[case_id]) != _extraction_payload(by_b[case_id]):
                raise ValidationSetError("unresolved Stage-1 extraction disagreement")
            source_row = by_a[case_id]
            source = "reviewer_agreement"
        consensus.append(
            {
                "schema_version": STAGE1_CONSENSUS_SCHEMA_VERSION,
                "case_id": case_id,
                "source": source,
                "source_row_sha256": sha256_bytes(canonical_json_bytes(source_row)),
                **_extraction_payload(source_row),
            }
        )
    validate_stage1_consensus(consensus, locked_inputs)
    return {
        "triggered_ids": triggered,
        "arbitration_count": len(triggered),
        "arbiter_id": next(iter(arbiter_ids)) if arbiter_ids else None,
        "consensus": consensus,
        "consensus_sha256": sha256_bytes(canonical_jsonl_bytes(consensus)),
        "unresolved_count": 0,
    }


def validate_stage1_consensus(
    rows: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Require a conclusive, immutable extraction consensus for all 120 cases."""
    locked = _locked_input_index(locked_inputs)
    if len(rows) != 120:
        raise ValidationSetError("Stage-1 consensus must contain 120 rows")
    ids: list[str] = []
    for index, row in enumerate(rows):
        name = f"Stage-1 consensus[{index}]"
        _require_exact_fields(row, _STAGE1_CONSENSUS_FIELDS, name)
        if row["schema_version"] != STAGE1_CONSENSUS_SCHEMA_VERSION:
            raise ValidationSetError(f"{name}.schema_version is invalid")
        case_id = _require_case_id(row["case_id"], f"{name}.case_id")
        if case_id not in locked:
            raise ValidationSetError(f"{name}.case_id is unknown")
        _require_enum(
            row["source"],
            ("reviewer_agreement", "stage1_arbitration"),
            f"{name}.source",
        )
        _require_sha256(row["source_row_sha256"], f"{name}.source_row_sha256")
        _validate_extraction_fields(row, locked[case_id]["output_text"])
        ids.append(case_id)
    if ids != sorted(locked) or len(ids) != len(set(ids)):
        raise ValidationSetError("Stage-1 consensus must exactly cover ordered IDs")
    return {
        "row_count": 120,
        "unresolved_count": 0,
        "consensus_sha256": sha256_bytes(canonical_jsonl_bytes(list(rows))),
    }


_STAGE2_REFERENCE_PACKET_FIELDS = frozenset(
    {"case_id", "registered_reference_answer"}
)


def build_stage2_reference_packet(
    reference_labels: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    labels = _final_label_index(reference_labels)
    return [
        {
            "case_id": case_id,
            "registered_reference_answer": labels[case_id][
                "registered_reference_answer"
            ],
        }
        for case_id in sorted(labels)
    ]


def validate_stage2_reference_packet(
    rows: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    locked = _locked_input_index(locked_inputs)
    if len(rows) != 120:
        raise ValidationSetError("Stage-2 reference packet must contain 120 rows")
    ids: list[str] = []
    references: dict[str, str] = {}
    for index, row in enumerate(rows):
        name = f"Stage-2 reference packet[{index}]"
        _require_exact_fields(row, _STAGE2_REFERENCE_PACKET_FIELDS, name)
        case_id = _require_case_id(row["case_id"], f"{name}.case_id")
        if case_id not in locked or case_id in references:
            raise ValidationSetError(f"{name}.case_id is unknown or duplicate")
        references[case_id] = _require_canonical_numeric(
            row["registered_reference_answer"],
            f"{name}.registered_reference_answer",
        )
        ids.append(case_id)
    if ids != sorted(locked):
        raise ValidationSetError(
            "Stage-2 reference packet must exactly cover ordered locked IDs"
        )
    return {
        "row_count": 120,
        "references": references,
        "packet_sha256": sha256_bytes(canonical_jsonl_bytes(list(rows))),
    }


def _stage2_review_packet_sha256(
    stage1_consensus_sha256: str, stage2_reference_packet_sha256: str
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": "phase1-parser-v2-stage2-review-packet/v1",
                "stage1_consensus_sha256": stage1_consensus_sha256,
                "stage2_reference_packet_sha256": (
                    stage2_reference_packet_sha256
                ),
            }
        )
    )


def validate_stage2_row(
    record: Mapping[str, Any],
    *,
    case_ids: set[str],
    packet_sha256: str,
    stage1_consensus_sha256: str,
    stage2_reference_packet_sha256: str,
    name: str = "Stage-2 row",
) -> dict[str, Any]:
    """Validate one correctness-only row; extraction fields are not permitted."""
    _require_exact_fields(record, _STAGE2_FIELDS, name)
    if record["schema_version"] != STAGE2_REVIEW_SCHEMA_VERSION:
        raise ValidationSetError(f"{name}.schema_version is invalid")
    if record["review_stage"] != "stage2":
        raise ValidationSetError(f"{name}.review_stage must equal stage2")
    case_id = _require_case_id(record["case_id"], f"{name}.case_id")
    if case_id not in case_ids:
        raise ValidationSetError(f"{name}.case_id is unknown")
    reviewer_id = _require_string(record["reviewer_id"], f"{name}.reviewer_id")
    if record["reviewer_model_id"] != REVIEWER_MODEL_ID:
        raise ValidationSetError(f"{name}.reviewer_model_id is invalid")
    if record["reviewer_reasoning_effort"] != REVIEWER_REASONING_EFFORT:
        raise ValidationSetError(f"{name}.reviewer_reasoning_effort is invalid")
    for field, expected in (
        ("packet_sha256", packet_sha256),
        ("stage1_consensus_sha256", stage1_consensus_sha256),
        (
            "stage2_reference_packet_sha256",
            stage2_reference_packet_sha256,
        ),
    ):
        digest = _require_sha256(record[field], f"{name}.{field}")
        if digest != expected:
            raise ValidationSetError(f"{name}.{field} mismatch")
    correctness = _require_enum(
        record["correctness"], STAGE2_CORRECTNESS, f"{name}.correctness"
    )
    critical = _require_optional_bool(record["critical_case"], f"{name}.critical_case")
    material = _require_optional_bool(
        record["material_error_if_missed"],
        f"{name}.material_error_if_missed",
    )
    if correctness == "inconclusive":
        if critical is not None or material is not None:
            raise ValidationSetError(
                f"{name} inconclusive judgment must leave rubric fields null"
            )
    elif critical is None or material is None:
        raise ValidationSetError(f"{name} conclusive rubric fields must be booleans")
    _require_string(record["notes"], f"{name}.notes", nonempty=False)
    return {
        "case_id": case_id,
        "reviewer_id": reviewer_id,
        "correctness": correctness,
        "critical_case": critical,
        "material_error_if_missed": material,
    }


def validate_stage2_submission(
    rows: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
    stage1_consensus: Sequence[Mapping[str, Any]],
    stage2_reference_packet: Sequence[Mapping[str, Any]],
    *,
    packet_sha256: str | None = None,
    expected_reviewer_id: str | None = None,
) -> dict[str, Any]:
    """Require one complete 120/120 Stage-2 reviewer submission."""
    locked = _locked_input_index(locked_inputs)
    consensus = validate_stage1_consensus(stage1_consensus, locked_inputs)
    references = validate_stage2_reference_packet(
        stage2_reference_packet, locked_inputs
    )
    expected_packet_hash = packet_sha256 or _stage2_review_packet_sha256(
        consensus["consensus_sha256"], references["packet_sha256"]
    )
    if len(rows) != 120:
        raise ValidationSetError("Stage-2 reviewer submission must contain 120 rows")
    reviewer_ids: set[str] = set()
    ids: list[str] = []
    unresolved: list[str] = []
    for index, row in enumerate(rows):
        checked = validate_stage2_row(
            row,
            case_ids=set(locked),
            packet_sha256=expected_packet_hash,
            stage1_consensus_sha256=consensus["consensus_sha256"],
            stage2_reference_packet_sha256=references["packet_sha256"],
            name=f"Stage-2 rows[{index}]",
        )
        ids.append(checked["case_id"])
        reviewer_ids.add(checked["reviewer_id"])
        if checked["correctness"] == "inconclusive":
            unresolved.append(checked["case_id"])
    if ids != sorted(locked) or len(ids) != len(set(ids)):
        raise ValidationSetError(
            "Stage-2 submission must exactly cover ordered locked case IDs"
        )
    if len(reviewer_ids) != 1:
        raise ValidationSetError("Stage-2 submission must have one reviewer identity")
    reviewer_id = next(iter(reviewer_ids))
    if expected_reviewer_id is not None and reviewer_id != expected_reviewer_id:
        raise ValidationSetError(
            "Stage-2 reviewer identity must equal the corresponding Stage-1 identity"
        )
    return {
        "reviewer_id": reviewer_id,
        "packet_sha256": expected_packet_hash,
        "stage1_consensus_sha256": consensus["consensus_sha256"],
        "stage2_reference_packet_sha256": references["packet_sha256"],
        "submission_sha256": sha256_bytes(canonical_jsonl_bytes(list(rows))),
        "row_count": 120,
        "unresolved_ids": unresolved,
    }


def stage2_disagreement_ids(
    reviewer_a: Sequence[Mapping[str, Any]],
    reviewer_b: Sequence[Mapping[str, Any]],
) -> list[str]:
    fields = ("correctness", "critical_case", "material_error_if_missed")
    by_b = {row.get("case_id"): row for row in reviewer_b}
    result = []
    for row in reviewer_a:
        case_id = row.get("case_id")
        other = by_b.get(case_id)
        if other is None or any(row.get(field) != other.get(field) for field in fields):
            result.append(_require_case_id(case_id))
    return sorted(result)


def validate_stage2_arbitration(
    rows: Sequence[Mapping[str, Any]],
    reviewer_a: Sequence[Mapping[str, Any]],
    reviewer_b: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
    stage1_consensus: Sequence[Mapping[str, Any]],
    stage2_reference_packet: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate separate correctness/material arbitration without extraction edits."""
    a = validate_stage2_submission(
        reviewer_a, locked_inputs, stage1_consensus, stage2_reference_packet
    )
    b = validate_stage2_submission(
        reviewer_b,
        locked_inputs,
        stage1_consensus,
        stage2_reference_packet,
        packet_sha256=a["packet_sha256"],
    )
    if a["reviewer_id"] == b["reviewer_id"]:
        raise ValidationSetError("Stage-2 reviewer identities must be distinct")
    triggered = stage2_disagreement_ids(reviewer_a, reviewer_b)
    if len(rows) != len(triggered):
        raise ValidationSetError(
            "Stage-2 arbitration must exactly cover rubric disagreements"
        )
    arbiter_ids: set[str] = set()
    resolutions: dict[str, dict[str, Any]] = {}
    ordered_ids: list[str] = []
    case_ids = set(_locked_input_index(locked_inputs))
    for index, row in enumerate(rows):
        name = f"Stage-2 arbitration[{index}]"
        _require_exact_fields(row, _STAGE2_ARBITRATION_FIELDS, name)
        if row["schema_version"] != STAGE2_ARBITRATION_SCHEMA_VERSION:
            raise ValidationSetError(f"{name}.schema_version is invalid")
        if row["review_stage"] != "stage2_arbitration":
            raise ValidationSetError(f"{name}.review_stage is invalid")
        case_id = _require_case_id(row["case_id"], f"{name}.case_id")
        if case_id not in case_ids or case_id in resolutions:
            raise ValidationSetError(f"{name}.case_id is unknown or duplicate")
        arbiter_id = _require_string(row["arbiter_id"], f"{name}.arbiter_id")
        if arbiter_id in {a["reviewer_id"], b["reviewer_id"]}:
            raise ValidationSetError("Stage-2 arbiter must be a third identity")
        arbiter_ids.add(arbiter_id)
        if row["arbiter_model_id"] != REVIEWER_MODEL_ID:
            raise ValidationSetError(f"{name}.arbiter_model_id is invalid")
        if row["arbiter_reasoning_effort"] != REVIEWER_REASONING_EFFORT:
            raise ValidationSetError(f"{name}.arbiter_reasoning_effort is invalid")
        for field, expected in (
            ("packet_sha256", a["packet_sha256"]),
            ("stage1_consensus_sha256", a["stage1_consensus_sha256"]),
            (
                "stage2_reference_packet_sha256",
                a["stage2_reference_packet_sha256"],
            ),
            ("reviewer_a_submission_sha256", a["submission_sha256"]),
            ("reviewer_b_submission_sha256", b["submission_sha256"]),
        ):
            if _require_sha256(row[field], f"{name}.{field}") != expected:
                raise ValidationSetError(f"{name}.{field} mismatch")
        correctness = _require_enum(
            row["correctness"], ("correct", "incorrect"), f"{name}.correctness"
        )
        critical = _require_bool(row["critical_case"], f"{name}.critical_case")
        material = _require_bool(
            row["material_error_if_missed"],
            f"{name}.material_error_if_missed",
        )
        _require_string(
            row["resolution_notes"], f"{name}.resolution_notes", nonempty=False
        )
        resolutions[case_id] = {
            "correctness": correctness,
            "critical_case": critical,
            "material_error_if_missed": material,
        }
        ordered_ids.append(case_id)
    if ordered_ids != triggered:
        raise ValidationSetError(
            "Stage-2 arbitration IDs must equal ordered disagreement IDs"
        )
    if rows and len(arbiter_ids) != 1:
        raise ValidationSetError("Stage-2 arbitration must use one arbiter identity")

    by_a = {row["case_id"]: row for row in reviewer_a}
    by_b = {row["case_id"]: row for row in reviewer_b}
    final: list[dict[str, Any]] = []
    for case_id in sorted(case_ids):
        if case_id in resolutions:
            decision = resolutions[case_id]
            source = "stage2_arbitration"
        else:
            fields = ("correctness", "critical_case", "material_error_if_missed")
            if any(by_a[case_id][field] != by_b[case_id][field] for field in fields):
                raise ValidationSetError("unresolved Stage-2 rubric disagreement")
            if by_a[case_id]["correctness"] == "inconclusive":
                raise ValidationSetError("agreed inconclusive Stage-2 judgment")
            decision = {field: by_a[case_id][field] for field in fields}
            source = "reviewer_agreement"
        final.append({"case_id": case_id, "source": source, **decision})
    return {
        "triggered_ids": triggered,
        "arbitration_count": len(triggered),
        "arbiter_id": next(iter(arbiter_ids)) if arbiter_ids else None,
        "final_stage2": final,
        "unresolved_count": 0,
    }


def _final_label_index(
    labels: Sequence[Mapping[str, Any]], *, require_120: bool = True
) -> dict[str, Mapping[str, Any]]:
    if require_120 and len(labels) != 120:
        raise ValidationSetError("locked reference labels must contain 120 rows")
    result: dict[str, Mapping[str, Any]] = {}
    ids: list[str] = []
    for index, label in enumerate(labels):
        validate_final_label(label, name=f"locked labels[{index}]")
        case_id = label["case_id"]
        if case_id in result:
            raise ValidationSetError("locked reference labels have duplicate case_id")
        result[case_id] = label
        ids.append(case_id)
    if ids != sorted(ids):
        raise ValidationSetError("locked reference labels must be ordered by case_id")
    return result


_FINAL_STAGE2_FIELDS = frozenset(
    {
        "case_id",
        "source",
        "correctness",
        "critical_case",
        "material_error_if_missed",
    }
)


def _final_stage2_index(
    rows: Sequence[Mapping[str, Any]], case_ids: set[str]
) -> dict[str, Mapping[str, Any]]:
    if len(rows) != len(case_ids):
        raise ValidationSetError("final Stage-2 consensus membership is incomplete")
    result: dict[str, Mapping[str, Any]] = {}
    ordered: list[str] = []
    for index, row in enumerate(rows):
        name = f"final Stage-2 consensus[{index}]"
        _require_exact_fields(row, _FINAL_STAGE2_FIELDS, name)
        case_id = _require_case_id(row["case_id"], f"{name}.case_id")
        if case_id not in case_ids or case_id in result:
            raise ValidationSetError(f"{name}.case_id is unknown or duplicate")
        _require_enum(
            row["source"],
            ("reviewer_agreement", "stage2_arbitration"),
            f"{name}.source",
        )
        _require_enum(
            row["correctness"],
            ("correct", "incorrect"),
            f"{name}.correctness",
        )
        _require_bool(row["critical_case"], f"{name}.critical_case")
        _require_bool(
            row["material_error_if_missed"],
            f"{name}.material_error_if_missed",
        )
        result[case_id] = row
        ordered.append(case_id)
    if ordered != sorted(case_ids):
        raise ValidationSetError(
            "final Stage-2 consensus must exactly cover ordered case IDs"
        )
    return result


def _final_label_draft_index_without_private_oracles(
    draft_labels: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for index, row in enumerate(draft_labels):
        if not isinstance(row, Mapping):
            raise ValidationSetError(f"draft label[{index}] must be an object")
        copy = dict(row)
        output_text = _require_string(
            copy.get("output_text"),
            f"draft label[{index}].output_text",
            nonempty=False,
        )
        stratum = _require_enum(
            copy.get("stratum"), STRATA, f"draft label[{index}].stratum"
        )
        extraction = _validate_extraction_fields(
            copy, output_text, prefix="expected_", expected=True
        )
        (
            copy["acceptable_selected_spans"],
            copy["last_number_distractor_span"],
        ) = _derive_private_label_spans(
            output_text,
            extraction,
            stratum,
            name=f"draft label[{index}]",
        )
        sanitized.append(copy)
    return _final_label_index(sanitized)


def build_final_labels(
    draft_labels: Sequence[Mapping[str, Any]],
    stage1_consensus: Sequence[Mapping[str, Any]],
    stage2_reference_packet: Sequence[Mapping[str, Any]],
    final_stage2: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Merge extraction consensus and separate Stage-2 consensus into final labels."""
    drafts = _final_label_draft_index_without_private_oracles(draft_labels)
    locked_inputs = [
        {
            "schema_version": LOCKED_INPUT_SCHEMA_VERSION,
            "case_id": label["case_id"],
            "source_kind": SOURCE_KIND,
            "output_text": label["output_text"],
            "parse_type": "numeric",
        }
        for label in draft_labels
    ]
    reference_packet = validate_stage2_reference_packet(
        stage2_reference_packet, locked_inputs
    )["references"]
    validate_stage1_consensus(stage1_consensus, locked_inputs)
    consensus = {row["case_id"]: row for row in stage1_consensus}
    stage2 = _final_stage2_index(final_stage2, set(drafts))
    if (
        set(drafts) != set(consensus)
        or set(drafts) != set(stage2)
        or set(drafts) != set(reference_packet)
    ):
        raise ValidationSetError("final label inputs do not have exact common membership")
    final: list[dict[str, Any]] = []
    presence_map = {
        "present": "present",
        "uncertain": "ambiguous",
        "absent": "no_answer",
    }
    for case_id in sorted(drafts):
        base = dict(drafts[case_id])
        if (
            base["registered_reference_answer"]
            != reference_packet[case_id]
        ):
            raise ValidationSetError(
                "draft label reference differs from immutable Stage-2 packet"
            )
        extraction = consensus[case_id]
        rubric = stage2[case_id]
        if extraction["answer_presence"] not in presence_map:
            raise ValidationSetError("Stage-1 consensus remains inconclusive")
        for field in _EXTRACTION_FIELD_NAMES:
            target = f"expected_{field}"
            value = extraction[field]
            if field == "answer_presence":
                value = presence_map[value]
            base[target] = value
        (
            base["acceptable_selected_spans"],
            base["last_number_distractor_span"],
        ) = _derive_private_label_spans(
            base["output_text"],
            extraction,
            base["stratum"],
            name=f"Stage-1 consensus {case_id}",
        )
        correctness = rubric["correctness"]
        if correctness not in {"correct", "incorrect"}:
            raise ValidationSetError("Stage-2 consensus remains inconclusive")
        base["expected_correctness"] = correctness == "correct"
        base["critical_case"] = rubric["critical_case"]
        base["material_error_if_missed"] = rubric["material_error_if_missed"]
        validate_final_label(base)
        final.append(base)
    _validate_locked_label_support(final)
    return final


def validate_final_labels_against_consensus(
    final_labels: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
    stage1_consensus: Sequence[Mapping[str, Any]],
    stage2_reference_packet: Sequence[Mapping[str, Any]],
    final_stage2: Sequence[Mapping[str, Any]],
) -> None:
    labels = _validate_locked_label_support(final_labels)
    locked = _locked_input_index(locked_inputs)
    validate_stage1_consensus(stage1_consensus, locked_inputs)
    references = validate_stage2_reference_packet(
        stage2_reference_packet, locked_inputs
    )["references"]
    consensus = {row["case_id"]: row for row in stage1_consensus}
    stage2 = _final_stage2_index(final_stage2, set(labels))
    if not (
        set(labels)
        == set(locked)
        == set(references)
        == set(consensus)
        == set(stage2)
    ):
        raise ValidationSetError("final-label derivation membership mismatch")
    presence_map = {
        "present": "present",
        "uncertain": "ambiguous",
        "absent": "no_answer",
    }
    for case_id, label in labels.items():
        if label["output_text"] != locked[case_id]["output_text"]:
            raise ValidationSetError("final label output differs from locked input")
        if label["registered_reference_answer"] != references[case_id]:
            raise ValidationSetError(
                "final label reference differs from immutable Stage-2 packet"
            )
        extraction = consensus[case_id]
        for field in _EXTRACTION_FIELD_NAMES:
            expected = extraction[field]
            if field == "answer_presence":
                expected = presence_map.get(expected)
            if label[f"expected_{field}"] != expected:
                raise ValidationSetError(
                    "final label extraction differs from sealed Stage-1 consensus"
                )
        acceptable, distractor = _derive_private_label_spans(
            label["output_text"],
            extraction,
            label["stratum"],
            name=f"sealed Stage-1 consensus {case_id}",
        )
        if (
            label["acceptable_selected_spans"] != acceptable
            or label["last_number_distractor_span"] != distractor
        ):
            raise ValidationSetError(
                "final label private spans differ from sealed Stage-1 consensus"
            )
        rubric = stage2[case_id]
        if (
            label["expected_correctness"]
            != (rubric["correctness"] == "correct")
            or label["critical_case"] != rubric["critical_case"]
            or label["material_error_if_missed"]
            != rubric["material_error_if_missed"]
        ):
            raise ValidationSetError(
                "final label rubric differs from sealed Stage-2 consensus"
            )


_REVIEW_SEAL_FIELDS = frozenset(
    {
        "schema_version",
        "review_stage",
        "actor_id",
        "reviewer_model_id",
        "reviewer_reasoning_effort",
        "packet_sha256",
        "submission_sha256",
        "row_sha256",
        "row_count",
        "ordered_case_ids",
        "stage1_consensus_sha256",
        "stage2_reference_packet_sha256",
        "predecessor_seal_sha256",
        "sealed_utc",
    }
)


_REVIEW_STAGE_PREDECESSOR_COUNTS = {
    "stage1": 0,
    "stage1_arbitration": 2,
    "stage1_consensus": 3,
    "stage2": 1,
    "stage2_arbitration": 3,
}


def review_seal_sha256(seal: Mapping[str, Any]) -> str:
    _require_exact_fields(seal, _REVIEW_SEAL_FIELDS, "review seal")
    return sha256_bytes(canonical_json_bytes(dict(seal)))


def _derive_review_row_bindings(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, str] | None:
    if not isinstance(rows, Sequence) or isinstance(
        rows, (str, bytes, bytearray)
    ):
        raise ValidationSetError("review rows must be a sequence of objects")
    if not rows:
        return None
    stages: set[str] = set()
    actors: set[str] = set()
    models: set[str] = set()
    efforts: set[str] = set()
    packets: set[str] = set()
    consensus_hashes: set[str] = set()
    reference_packet_hashes: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValidationSetError(f"review rows[{index}] must be an object")
        schema = row.get("schema_version")
        if schema == STAGE1_CONSENSUS_SCHEMA_VERSION:
            stages.add("stage1_consensus")
        else:
            stage = row.get("review_stage")
            if isinstance(stage, str):
                stages.add(stage)
        actor = row.get("reviewer_id", row.get("arbiter_id"))
        if isinstance(actor, str):
            actors.add(actor)
        model = row.get("reviewer_model_id", row.get("arbiter_model_id"))
        if isinstance(model, str):
            models.add(model)
        effort = row.get(
            "reviewer_reasoning_effort", row.get("arbiter_reasoning_effort")
        )
        if isinstance(effort, str):
            efforts.add(effort)
        packet = row.get("packet_sha256")
        if isinstance(packet, str):
            packets.add(packet)
        consensus = row.get("stage1_consensus_sha256")
        if isinstance(consensus, str):
            consensus_hashes.add(consensus)
        reference = row.get("stage2_reference_packet_sha256")
        if isinstance(reference, str):
            reference_packet_hashes.add(reference)
    if len(stages) != 1:
        raise ValidationSetError("review rows do not derive one stage")
    for values, name in (
        (actors, "actor"),
        (models, "model"),
        (efforts, "reasoning effort"),
        (packets, "packet hash"),
        (consensus_hashes, "Stage-1 consensus hash"),
        (reference_packet_hashes, "Stage-2 reference-packet hash"),
    ):
        if len(values) > 1:
            raise ValidationSetError(f"review rows do not derive one {name}")
    return {
        "review_stage": next(iter(stages)),
        "actor_id": next(iter(actors)) if actors else "",
        "reviewer_model_id": next(iter(models)) if models else "",
        "reviewer_reasoning_effort": next(iter(efforts)) if efforts else "",
        "packet_sha256": next(iter(packets)) if packets else "",
        "stage1_consensus_sha256": (
            next(iter(consensus_hashes)) if consensus_hashes else ""
        ),
        "stage2_reference_packet_sha256": (
            next(iter(reference_packet_hashes))
            if reference_packet_hashes
            else ""
        ),
    }


def build_review_seal(
    rows: Sequence[Mapping[str, Any]],
    *,
    review_stage: str,
    actor_id: str,
    packet_sha256: str,
    sealed_utc: str,
    stage1_consensus_sha256: str | None = None,
    stage2_reference_packet_sha256: str | None = None,
    predecessor_seals: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Derive and seal exact reviewer/arbitration row and predecessor bindings."""
    derived = _derive_review_row_bindings(rows)
    if derived is not None:
        if review_stage != derived["review_stage"]:
            raise ValidationSetError("review seal stage does not match its rows")
        if derived["actor_id"] and actor_id != derived["actor_id"]:
            raise ValidationSetError("review seal actor does not match its rows")
        if derived["packet_sha256"] and packet_sha256 != derived["packet_sha256"]:
            raise ValidationSetError("review seal packet hash does not match its rows")
        if (
            derived["stage1_consensus_sha256"]
            and stage1_consensus_sha256 != derived["stage1_consensus_sha256"]
        ):
            raise ValidationSetError(
                "review seal consensus hash does not match its rows"
            )
        if (
            derived["stage2_reference_packet_sha256"]
            and stage2_reference_packet_sha256
            != derived["stage2_reference_packet_sha256"]
        ):
            raise ValidationSetError(
                "review seal reference hash does not match its rows"
            )
    seal = {
        "schema_version": REVIEW_SEAL_SCHEMA_VERSION,
        "review_stage": review_stage,
        "actor_id": actor_id,
        "reviewer_model_id": REVIEWER_MODEL_ID,
        "reviewer_reasoning_effort": REVIEWER_REASONING_EFFORT,
        "packet_sha256": packet_sha256,
        "submission_sha256": sha256_bytes(canonical_jsonl_bytes(list(rows))),
        "row_sha256": [
            sha256_bytes(canonical_json_bytes(dict(row))) for row in rows
        ],
        "row_count": len(rows),
        "ordered_case_ids": [row.get("case_id") for row in rows],
        "stage1_consensus_sha256": stage1_consensus_sha256,
        "stage2_reference_packet_sha256": stage2_reference_packet_sha256,
        "predecessor_seal_sha256": [
            review_seal_sha256(item) for item in predecessor_seals
        ],
        "sealed_utc": sealed_utc,
    }
    validate_review_seal(
        seal, rows, predecessor_seals=predecessor_seals
    )
    return seal


def validate_review_seal(
    seal: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    *,
    expected_case_ids: Sequence[str] | None = None,
    predecessor_seals: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Validate exact row membership and hash bindings in one review seal."""
    _require_exact_fields(seal, _REVIEW_SEAL_FIELDS, "review seal")
    if seal["schema_version"] != REVIEW_SEAL_SCHEMA_VERSION:
        raise ValidationSetError("review seal schema_version is invalid")
    stage = _require_enum(
        seal["review_stage"],
        ("stage1", "stage1_arbitration", "stage1_consensus", "stage2", "stage2_arbitration"),
        "review seal review_stage",
    )
    actor = _require_string(seal["actor_id"], "review seal actor_id")
    if seal["reviewer_model_id"] != REVIEWER_MODEL_ID:
        raise ValidationSetError("review seal model ID is invalid")
    if seal["reviewer_reasoning_effort"] != REVIEWER_REASONING_EFFORT:
        raise ValidationSetError("review seal reasoning effort is invalid")
    packet_hash = _require_sha256(
        seal["packet_sha256"], "review seal packet_sha256"
    )
    submission_hash = _require_sha256(
        seal["submission_sha256"], "review seal submission_sha256"
    )
    if submission_hash != sha256_bytes(canonical_jsonl_bytes(list(rows))):
        raise ValidationSetError("review seal submission hash mismatch")
    if not isinstance(seal["row_sha256"], list):
        raise ValidationSetError("review seal row_sha256 must be a list")
    row_hashes = [
        _require_sha256(item, f"review seal row_sha256[{index}]")
        for index, item in enumerate(seal["row_sha256"])
    ]
    expected_row_hashes = [
        sha256_bytes(canonical_json_bytes(dict(row))) for row in rows
    ]
    if row_hashes != expected_row_hashes:
        raise ValidationSetError("review seal row hashes mismatch")
    row_count = _require_int(seal["row_count"], "review seal row_count", minimum=0)
    if row_count != len(rows):
        raise ValidationSetError("review seal row_count mismatch")
    if not isinstance(seal["ordered_case_ids"], list):
        raise ValidationSetError("review seal ordered_case_ids must be a list")
    ids = [_require_case_id(item) for item in seal["ordered_case_ids"]]
    actual_ids = [_require_case_id(row.get("case_id")) for row in rows]
    if ids != actual_ids or ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValidationSetError("review seal ordered case membership mismatch")
    if expected_case_ids is not None and ids != list(expected_case_ids):
        raise ValidationSetError("review seal does not cover expected case IDs")
    derived = _derive_review_row_bindings(rows)
    if derived is not None:
        if stage != derived["review_stage"]:
            raise ValidationSetError("review seal stage does not match row stage")
        if derived["actor_id"] and actor != derived["actor_id"]:
            raise ValidationSetError("review seal actor does not match row actor")
        if derived["reviewer_model_id"] and (
            derived["reviewer_model_id"] != seal["reviewer_model_id"]
        ):
            raise ValidationSetError("review seal model does not match rows")
        if derived["reviewer_reasoning_effort"] and (
            derived["reviewer_reasoning_effort"]
            != seal["reviewer_reasoning_effort"]
        ):
            raise ValidationSetError("review seal effort does not match rows")
        if derived["packet_sha256"] and packet_hash != derived["packet_sha256"]:
            raise ValidationSetError("review seal packet does not match rows")
    consensus_hash = seal["stage1_consensus_sha256"]
    reference_hash = seal["stage2_reference_packet_sha256"]
    if stage in {"stage2", "stage2_arbitration"}:
        _require_sha256(consensus_hash, "review seal stage1_consensus_sha256")
        _require_sha256(
            reference_hash, "review seal stage2_reference_packet_sha256"
        )
        if derived is not None and (
            consensus_hash != derived["stage1_consensus_sha256"]
            or reference_hash != derived["stage2_reference_packet_sha256"]
        ):
            raise ValidationSetError(
                "review seal Stage-2 bindings do not match rows"
            )
    elif consensus_hash is not None or reference_hash is not None:
        raise ValidationSetError(
            "reference-bearing hashes are prohibited from Stage-1 seals"
        )
    if not isinstance(seal["predecessor_seal_sha256"], list):
        raise ValidationSetError(
            "review seal predecessor_seal_sha256 must be a list"
        )
    predecessor_hashes = [
        _require_sha256(item, f"review seal predecessor[{index}]")
        for index, item in enumerate(seal["predecessor_seal_sha256"])
    ]
    expected_predecessors = [
        review_seal_sha256(item) for item in predecessor_seals
    ]
    if predecessor_hashes != expected_predecessors:
        raise ValidationSetError("review seal predecessor chain mismatch")
    if len(predecessor_hashes) != _REVIEW_STAGE_PREDECESSOR_COUNTS[stage]:
        raise ValidationSetError(
            f"{stage} seal has an invalid predecessor count"
        )
    if stage == "stage1_arbitration":
        predecessor_actors = [item.get("actor_id") for item in predecessor_seals]
        if len(set(predecessor_actors)) != 2 or actor in predecessor_actors:
            raise ValidationSetError(
                "Stage-1 arbitration seal must follow two distinct reviewers"
            )
        if any(
            item.get("packet_sha256") != packet_hash
            for item in predecessor_seals
        ):
            raise ValidationSetError(
                "Stage-1 arbitration packet must match both reviewer seals"
            )
    if stage == "stage1_consensus":
        if predecessor_seals and actor != predecessor_seals[-1].get("actor_id"):
            raise ValidationSetError(
                "Stage-1 consensus seal actor must equal the Stage-1 arbiter"
            )
        if any(
            item.get("packet_sha256") != packet_hash
            for item in predecessor_seals
        ):
            raise ValidationSetError(
                "Stage-1 consensus packet must match predecessor seals"
            )
    if stage == "stage2" and predecessor_seals:
        if consensus_hash != predecessor_seals[0].get("submission_sha256"):
            raise ValidationSetError(
                "Stage-2 seal must bind the predecessor consensus bytes"
            )
    if stage == "stage2_arbitration":
        if predecessor_seals:
            consensus_actor = predecessor_seals[0].get("actor_id")
            reviewer_actors = {
                predecessor_seals[1].get("actor_id"),
                predecessor_seals[2].get("actor_id"),
            }
            if actor != consensus_actor or actor in reviewer_actors:
                raise ValidationSetError(
                    "Stage-2 arbitration seal must retain the third arbiter"
                )
            if consensus_hash != predecessor_seals[0].get("submission_sha256"):
                raise ValidationSetError(
                    "Stage-2 arbitration must bind the sealed consensus"
                )
            for predecessor in predecessor_seals[1:]:
                if (
                    predecessor.get("packet_sha256") != packet_hash
                    or predecessor.get("stage1_consensus_sha256")
                    != consensus_hash
                    or predecessor.get("stage2_reference_packet_sha256")
                    != reference_hash
                ):
                    raise ValidationSetError(
                        "Stage-2 arbitration predecessor bindings mismatch"
                    )
    _require_utc_timestamp(seal["sealed_utc"], "review seal sealed_utc")
    return {
        "review_stage": stage,
        "actor_id": actor,
        "row_count": row_count,
        "submission_sha256": submission_hash,
        "seal_sha256": review_seal_sha256(seal),
    }


def validate_two_stage_reviewer_continuity(
    stage1_rows: Sequence[Mapping[str, Any]],
    stage2_rows: Sequence[Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
    stage1_consensus: Sequence[Mapping[str, Any]],
    stage2_reference_packet: Sequence[Mapping[str, Any]],
) -> None:
    """Require the same reviewer identity in corresponding Stage-1/Stage-2 work."""
    stage1 = validate_stage1_submission(stage1_rows, locked_inputs)
    validate_stage2_submission(
        stage2_rows,
        locked_inputs,
        stage1_consensus,
        stage2_reference_packet,
        expected_reviewer_id=stage1["reviewer_id"],
    )


def validate_two_stage_arbiter_continuity(
    stage1_arbitration: Mapping[str, Any],
    stage2_arbitration: Mapping[str, Any],
) -> None:
    """Require one third identity to perform both separately blinded passes."""
    first = stage1_arbitration.get("arbiter_id")
    second = stage2_arbitration.get("arbiter_id")
    if first is not None and second is not None and first != second:
        raise ValidationSetError(
            "the same third arbiter identity must perform both passes"
        )


def validate_complete_review_workflow(
    *,
    locked_inputs: Sequence[Mapping[str, Any]],
    draft_labels: Sequence[Mapping[str, Any]],
    stage2_reference_packet: Sequence[Mapping[str, Any]],
    reviewer_a_stage1: Sequence[Mapping[str, Any]],
    reviewer_a_stage1_seal: Mapping[str, Any],
    reviewer_b_stage1: Sequence[Mapping[str, Any]],
    reviewer_b_stage1_seal: Mapping[str, Any],
    arbitration_stage1: Sequence[Mapping[str, Any]],
    arbitration_stage1_seal: Mapping[str, Any],
    stage1_consensus_seal: Mapping[str, Any],
    reviewer_a_stage2: Sequence[Mapping[str, Any]],
    reviewer_a_stage2_seal: Mapping[str, Any],
    reviewer_b_stage2: Sequence[Mapping[str, Any]],
    reviewer_b_stage2_seal: Mapping[str, Any],
    arbitration_stage2: Sequence[Mapping[str, Any]],
    arbitration_stage2_seal: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the complete two-stage workflow at the private integration gate."""
    stage1_a = validate_stage1_submission(reviewer_a_stage1, locked_inputs)
    stage1_b = validate_stage1_submission(
        reviewer_b_stage1,
        locked_inputs,
        packet_sha256=stage1_a["packet_sha256"],
    )
    case_ids = [row["case_id"] for row in locked_inputs]
    validate_review_seal(
        reviewer_a_stage1_seal,
        reviewer_a_stage1,
        expected_case_ids=case_ids,
    )
    validate_review_seal(
        reviewer_b_stage1_seal,
        reviewer_b_stage1,
        expected_case_ids=case_ids,
    )
    stage1 = validate_stage1_arbitration(
        arbitration_stage1,
        reviewer_a_stage1,
        reviewer_b_stage1,
        locked_inputs,
    )
    validate_review_seal(
        arbitration_stage1_seal,
        arbitration_stage1,
        expected_case_ids=stage1["triggered_ids"],
        predecessor_seals=(
            reviewer_a_stage1_seal,
            reviewer_b_stage1_seal,
        ),
    )
    validate_review_seal(
        stage1_consensus_seal,
        stage1["consensus"],
        expected_case_ids=case_ids,
        predecessor_seals=(
            reviewer_a_stage1_seal,
            reviewer_b_stage1_seal,
            arbitration_stage1_seal,
        ),
    )
    validate_stage2_submission(
        reviewer_a_stage2,
        locked_inputs,
        stage1["consensus"],
        stage2_reference_packet,
        expected_reviewer_id=stage1_a["reviewer_id"],
    )
    validate_review_seal(
        reviewer_a_stage2_seal,
        reviewer_a_stage2,
        expected_case_ids=case_ids,
        predecessor_seals=(stage1_consensus_seal,),
    )
    validate_stage2_submission(
        reviewer_b_stage2,
        locked_inputs,
        stage1["consensus"],
        stage2_reference_packet,
        expected_reviewer_id=stage1_b["reviewer_id"],
    )
    validate_review_seal(
        reviewer_b_stage2_seal,
        reviewer_b_stage2,
        expected_case_ids=case_ids,
        predecessor_seals=(stage1_consensus_seal,),
    )
    stage2 = validate_stage2_arbitration(
        arbitration_stage2,
        reviewer_a_stage2,
        reviewer_b_stage2,
        locked_inputs,
        stage1["consensus"],
        stage2_reference_packet,
    )
    validate_review_seal(
        arbitration_stage2_seal,
        arbitration_stage2,
        expected_case_ids=stage2["triggered_ids"],
        predecessor_seals=(
            stage1_consensus_seal,
            reviewer_a_stage2_seal,
            reviewer_b_stage2_seal,
        ),
    )
    if (
        arbitration_stage1_seal["actor_id"]
        != arbitration_stage2_seal["actor_id"]
    ):
        raise ValidationSetError("the same third arbiter must seal both passes")
    final_labels = build_final_labels(
        draft_labels,
        stage1["consensus"],
        stage2_reference_packet,
        stage2["final_stage2"],
    )
    return {
        "stage1_arbitration_count": stage1["arbitration_count"],
        "stage2_arbitration_count": stage2["arbitration_count"],
        "unresolved_count": 0,
        "final_labels": final_labels,
        "final_labels_sha256": sha256_bytes(canonical_jsonl_bytes(final_labels)),
    }


def _fraction_record(value: Fraction | None) -> dict[str, Any]:
    if value is None:
        return {
            "numerator": None,
            "denominator": None,
            "canonical": None,
            "display": "NA",
        }
    canonical = (
        str(value.numerator)
        if value.denominator == 1
        else f"{value.numerator}/{value.denominator}"
    )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "canonical": canonical,
        "display": canonical,
    }


def nominal_cohen_kappa(
    left: Sequence[Any], right: Sequence[Any]
) -> Fraction | None:
    """Return exact nominal kappa, or NA for N=0/constant/zero denominator."""
    if len(left) != len(right):
        raise ValidationSetError("kappa inputs have different lengths")
    count = len(left)
    if count == 0:
        return None
    labels = set(left) | set(right)
    if len(set(left)) <= 1 or len(set(right)) <= 1:
        return None
    observed = Fraction(sum(a == b for a, b in zip(left, right)), count)
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum(
        Fraction(left_counts[label], count) * Fraction(right_counts[label], count)
        for label in labels
    )
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def _set_jaccard(left: Sequence[Any], right: Sequence[Any]) -> Fraction:
    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    return Fraction(len(left_set & right_set), len(union)) if union else Fraction(1)


def compute_reviewer_agreement(
    stage1_a: Sequence[Mapping[str, Any]],
    stage1_b: Sequence[Mapping[str, Any]],
    *,
    stage2_a: Sequence[Mapping[str, Any]] | None = None,
    stage2_b: Sequence[Mapping[str, Any]] | None = None,
    arbitration_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Compute exact Stage-1/Stage-2 agreement without dropping rows."""
    by_b = {row["case_id"]: row for row in stage1_b}
    if {row["case_id"] for row in stage1_a} != set(by_b):
        raise ValidationSetError("Stage-1 agreement membership mismatch")
    paired = [(row, by_b[row["case_id"]]) for row in stage1_a]
    nominal_fields = (
        "answer_presence",
        "parse_valid",
        "parse_ambiguous",
        "extraction_strategy",
        "output_quality",
    )
    field_reports: dict[str, Any] = {}
    for field in nominal_fields:
        left = [a[field] for a, _ in paired]
        right = [b[field] for _, b in paired]
        exact = sum(a == b for a, b in zip(left, right))
        field_reports[field] = {
            "exact_agreement_count": exact,
            "denominator": len(paired),
            "rate": _fraction_record(
                Fraction(exact, len(paired)) if paired else None
            ),
            "nominal_kappa": _fraction_record(nominal_cohen_kappa(left, right)),
        }

    parsed_exact = sum(a["parsed_answer"] == b["parsed_answer"] for a, b in paired)
    candidate_exact = sum(
        a["candidate_answers"] == b["candidate_answers"] for a, b in paired
    )
    selected_exact = sum(
        [
            span
            for span in a["evidence_spans"]
            if span["disposition"] == "selected"
        ]
        == [
            span
            for span in b["evidence_spans"]
            if span["disposition"] == "selected"
        ]
        for a, b in paired
    )
    selected_span_jaccard = sum(
        (
            _set_jaccard(
                [
                    canonical_json_bytes(span).decode("ascii")
                    for span in a["evidence_spans"]
                    if span["disposition"] == "selected"
                ],
                [
                    canonical_json_bytes(span).decode("ascii")
                    for span in b["evidence_spans"]
                    if span["disposition"] == "selected"
                ],
            )
            for a, b in paired
        ),
        Fraction(0),
    )
    candidate_jaccard = sum(
        (_set_jaccard(a["candidate_answers"], b["candidate_answers"]) for a, b in paired),
        Fraction(0),
    )
    set_reports = {}
    for field in ("failure_reasons", "format_warnings"):
        exact = sum(set(a[field]) == set(b[field]) for a, b in paired)
        jaccard = sum(
            (_set_jaccard(a[field], b[field]) for a, b in paired), Fraction(0)
        )
        set_reports[field] = {
            "exact_agreement_count": exact,
            "mean_jaccard": _fraction_record(
                jaccard / len(paired) if paired else None
            ),
        }
    report: dict[str, Any] = {
        "row_count": len(paired),
        "fields": field_reports,
        "normalized_parsed_answer_exact_count": parsed_exact,
        "candidate_list_exact_count": candidate_exact,
        "candidate_list_mean_jaccard": _fraction_record(
            candidate_jaccard / len(paired) if paired else None
        ),
        "selected_span_exact_count": selected_exact,
        "selected_span_mean_jaccard": _fraction_record(
            selected_span_jaccard / len(paired) if paired else None
        ),
        "sets": set_reports,
        "arbitration_count": len(arbitration_ids),
        "arbitration_ids": sorted(arbitration_ids),
        "unresolved_count": sum(
            a["answer_presence"] == "inconclusive"
            or b["answer_presence"] == "inconclusive"
            for a, b in paired
        ),
    }
    if (stage2_a is None) != (stage2_b is None):
        raise ValidationSetError("both Stage-2 submissions are required for agreement")
    if stage2_a is not None and stage2_b is not None:
        by_stage2_b = {row["case_id"]: row for row in stage2_b}
        if {row["case_id"] for row in stage2_a} != set(by_stage2_b):
            raise ValidationSetError("Stage-2 agreement membership mismatch")
        left = [row["correctness"] for row in stage2_a]
        right = [by_stage2_b[row["case_id"]]["correctness"] for row in stage2_a]
        exact = sum(a == b for a, b in zip(left, right))
        report["correctness"] = {
            "exact_agreement_count": exact,
            "denominator": len(left),
            "rate": _fraction_record(Fraction(exact, len(left)) if left else None),
            "nominal_kappa": _fraction_record(nominal_cohen_kappa(left, right)),
        }
        report["unresolved_count"] += sum(
            a == "inconclusive" or b == "inconclusive"
            for a, b in zip(left, right)
        )
    return report


def _validate_locked_label_support(
    labels: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    index = _final_label_index(labels)
    strata = Counter(label["stratum"] for label in labels)
    if strata != Counter({stratum: 10 for stratum in STRATA}):
        raise ValidationSetError("locked labels must contain ten cases per stratum")
    support = Counter(label["expected_answer_presence"] for label in labels)
    if support != Counter({"present": 80, "ambiguous": 10, "no_answer": 30}):
        raise ValidationSetError("locked labels have invalid typed-decision support")
    for label in labels:
        presence = label["expected_answer_presence"]
        stratum = label["stratum"]
        if (stratum == "S11") != (presence == "ambiguous"):
            raise ValidationSetError("locked ambiguity support is not confined to S11")
        if (stratum in NO_ANSWER_STRATA) != (presence == "no_answer"):
            raise ValidationSetError("locked no-answer support is invalid")
    correctness = {
        stratum: Counter(
            bool(label["expected_correctness"])
            for label in labels
            if label["stratum"] == stratum
        )
        for stratum in ANSWER_BEARING_STRATA
    }
    for stratum, counts in correctness.items():
        if counts != Counter({True: 5, False: 5}):
            raise ValidationSetError(
                f"final locked {stratum} must remain exactly 5 correct/5 incorrect"
            )
    if sum(label["critical_case"] for label in labels) != 80:
        raise ValidationSetError("final locked critical-case support must remain 80")
    return index


def _prediction_index(
    predictions: Sequence[Mapping[str, Any]],
    labels: Mapping[str, Mapping[str, Any]],
    locked_inputs: Sequence[Mapping[str, Any]],
    prediction_seal: Mapping[str, Any],
    implementation_commit: str,
) -> dict[str, Mapping[str, Any]]:
    if len(predictions) != 120:
        raise ValidationSetError("predictions must contain exactly 120 rows")
    locked = _locked_input_index(locked_inputs)
    validate_prediction_seal(
        prediction_seal,
        predictions,
        locked_inputs,
        expected_implementation_commit=implementation_commit,
    )
    if set(locked) != set(labels):
        raise ValidationSetError("prediction input membership differs from labels")
    result: dict[str, Mapping[str, Any]] = {}
    ids: list[str] = []
    for index, prediction in enumerate(predictions):
        _require_exact_fields(
            prediction, _PREDICTION_ENVELOPE_FIELDS, f"predictions[{index}]"
        )
        case_id = prediction["case_id"]
        if case_id not in locked:
            raise ValidationSetError("prediction has unknown case_id")
        validate_prediction_envelope(prediction, locked[case_id])
        parser_result = prediction["parser_result"]
        if case_id in result:
            raise ValidationSetError("predictions have duplicate case_id")
        result[case_id] = parser_result
        ids.append(case_id)
    if ids != sorted(labels) or set(result) != set(labels):
        raise ValidationSetError(
            "predictions must exactly cover labels in canonical case order"
        )
    return result


def _legacy_index(
    legacy_predictions: Sequence[Mapping[str, Any]],
    case_ids: set[str],
) -> dict[str, Mapping[str, Any]]:
    if len(legacy_predictions) != len(case_ids):
        raise ValidationSetError("legacy predictions have incomplete membership")
    result: dict[str, Mapping[str, Any]] = {}
    ids: list[str] = []
    for index, row in enumerate(legacy_predictions):
        if not isinstance(row, Mapping) or "case_id" not in row:
            raise ValidationSetError(f"legacy_predictions[{index}] is invalid")
        case_id = _require_case_id(
            row["case_id"], f"legacy_predictions[{index}].case_id"
        )
        if case_id not in case_ids or case_id in result:
            raise ValidationSetError("legacy prediction case_id is unknown or duplicate")
        if "legacy_result" in row:
            _require_exact_fields(
                row, {"case_id", "legacy_result"}, f"legacy_predictions[{index}]"
            )
            legacy_result = row["legacy_result"]
        else:
            _require_exact_fields(
                row,
                {"case_id", "parse_valid", "parse_ambiguous", "parsed_answer"},
                f"legacy_predictions[{index}]",
            )
            legacy_result = {
                "parse_valid": row["parse_valid"],
                "parse_ambiguous": row["parse_ambiguous"],
                "parsed_answer": row["parsed_answer"],
            }
        result[case_id] = legacy_result
        ids.append(case_id)
    if ids != sorted(case_ids):
        raise ValidationSetError("legacy predictions must be ordered by case_id")
    return result


def _safe_ratio(numerator: int, denominator: int) -> Fraction | None:
    if type(numerator) is not int or type(denominator) is not int:
        raise ValidationSetError("ratio counts must be integers")
    return None if denominator == 0 else Fraction(numerator, denominator)


def _gate_minimum(
    value: Fraction | None, threshold: Fraction
) -> Literal["PASS", "FAIL", "INVALID"]:
    if value is None:
        return "INVALID"
    return "PASS" if value >= threshold else "FAIL"


def _gate_maximum_count(
    count: int, maximum: int
) -> Literal["PASS", "FAIL"]:
    return "PASS" if count <= maximum else "FAIL"


def _classification_metrics(
    confusion: Mapping[str, Mapping[str, int]], label: str
) -> dict[str, Any]:
    tp = confusion[label][label]
    fp = sum(confusion[actual][label] for actual in TYPED_DECISION_CLASSES if actual != label)
    fn = sum(confusion[label][predicted] for predicted in TYPED_DECISION_CLASSES if predicted != label)
    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    f1 = _safe_ratio(2 * tp, 2 * tp + fp + fn)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": _fraction_record(precision),
        "recall": _fraction_record(recall),
        "f1": _fraction_record(f1),
        "_precision": precision,
        "_recall": recall,
        "_f1": f1,
    }


def _span_identity(span: Mapping[str, Any]) -> tuple[int, int, str]:
    return (span["start"], span["end"], span["text"])


def _selected_parser_span(
    parser_result: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    selected = [
        span
        for span in parser_result["evidence_spans"]
        if span["disposition"] == "selected"
    ]
    if len(selected) > 1:
        raise ValidationSetError("parser result has multiple selected spans")
    return selected[0] if selected else None


def _score_validation_set(
    final_labels: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    legacy_predictions: Sequence[Mapping[str, Any]],
    *,
    locked_inputs: Sequence[Mapping[str, Any]],
    prediction_seal: Mapping[str, Any],
    implementation_commit: str,
) -> dict[str, Any]:
    labels = _validate_locked_label_support(final_labels)
    parser = _prediction_index(
        predictions,
        labels,
        locked_inputs,
        prediction_seal,
        implementation_commit,
    )
    legacy = _legacy_index(legacy_predictions, set(labels))

    confusion = {
        actual: {predicted: 0 for predicted in TYPED_DECISION_CLASSES}
        for actual in TYPED_DECISION_CLASSES
    }
    per_stratum = {
        stratum: {
            "denominator": 0,
            "parser_v2_correct": 0,
            "legacy_correct": 0,
            "material_errors": 0,
            "wrong_span_errors": 0,
        }
        for stratum in STRATA
    }
    expected_decisions: dict[str, str] = {}
    parser_decisions: dict[str, str] = {}
    legacy_decisions: dict[str, str] = {}
    parser_correct_count = 0
    legacy_correct_count = 0
    boxed_final_misses = 0
    last_number_trap_errors = 0
    wrong_span_errors = 0
    material_errors = 0
    material_by_stratum = Counter()
    adapter_failures: list[str] = []

    for case_id in sorted(labels):
        label = labels[case_id]
        parser_result = parser[case_id]
        expected_decision = derive_typed_decision(label)
        parser_decision = derive_typed_decision(parser_result)
        legacy_adapted = adapt_legacy_result(legacy[case_id])
        legacy_decision = legacy_adapted["typed_decision"]
        if legacy_adapted["adapter_failure"] is not None:
            adapter_failures.append(case_id)
        expected_decisions[case_id] = expected_decision
        parser_decisions[case_id] = parser_decision
        legacy_decisions[case_id] = legacy_decision
        actual_class = typed_decision_class(expected_decision)
        predicted_class = typed_decision_class(parser_decision)
        confusion[actual_class][predicted_class] += 1
        stratum = label["stratum"]
        per_stratum[stratum]["denominator"] += 1
        parser_exact = parser_decision == expected_decision
        legacy_exact = legacy_decision == expected_decision
        parser_correct_count += parser_exact
        legacy_correct_count += legacy_exact
        per_stratum[stratum]["parser_v2_correct"] += parser_exact
        per_stratum[stratum]["legacy_correct"] += legacy_exact

        selected = _selected_parser_span(parser_result)
        acceptable = {
            _span_identity(span) for span in label["acceptable_selected_spans"]
        }
        if label["expected_answer_presence"] == "present":
            wrong_span = selected is None or _span_identity(selected) not in acceptable
            wrong_span_errors += wrong_span
            per_stratum[stratum]["wrong_span_errors"] += wrong_span
            if stratum in {"S01", "S02"} and (
                not parser_exact or wrong_span
            ):
                boxed_final_misses += 1
        if stratum == "S06":
            distractor = label["last_number_distractor_span"]
            if selected is not None and distractor is not None:
                last_number_trap_errors += (
                    _span_identity(selected) == _span_identity(distractor)
                )

        reference = label["registered_reference_answer"]
        parser_task_correct = (
            parser_decision.startswith("present:")
            and parser_decision[len("present:") :] == reference
        )
        expected_task_correct = bool(label["expected_correctness"])
        material = bool(parser_task_correct) ^ expected_task_correct
        material_errors += material
        material_by_stratum[stratum] += material
        per_stratum[stratum]["material_errors"] += material

    class_metrics = {
        label: _classification_metrics(confusion, label)
        for label in TYPED_DECISION_CLASSES
    }
    class_f1_values = [class_metrics[label]["_f1"] for label in TYPED_DECISION_CLASSES]
    macro_f1 = (
        sum(class_f1_values, Fraction(0)) / len(class_f1_values)
        if all(value is not None for value in class_f1_values)
        else None
    )
    overall_ratio = Fraction(parser_correct_count, 120)
    clean_v2 = sum(per_stratum[stratum]["parser_v2_correct"] for stratum in CLEAN_STRATA)
    clean_legacy = sum(per_stratum[stratum]["legacy_correct"] for stratum in CLEAN_STRATA)
    paired_regressions = sum(
        legacy_decisions[case_id] == expected_decisions[case_id]
        and parser_decisions[case_id] != expected_decisions[case_id]
        for case_id, label in labels.items()
        if label["stratum"] in CLEAN_STRATA
    )
    critical_gains = {
        stratum: (
            per_stratum[stratum]["parser_v2_correct"]
            - per_stratum[stratum]["legacy_correct"]
        )
        for stratum in CRITICAL_STRATA
    }

    gates: dict[str, str] = {
        "overall_exact_typed_decision": _gate_minimum(
            overall_ratio, Fraction(19, 20)
        ),
        "answer_presence_macro_f1": _gate_minimum(macro_f1, Fraction(19, 20)),
        "ambiguity_precision": _gate_minimum(
            class_metrics["ambiguous"]["_precision"], Fraction(9, 10)
        ),
        "ambiguity_recall": _gate_minimum(
            class_metrics["ambiguous"]["_recall"], Fraction(9, 10)
        ),
        "no_answer_precision": _gate_minimum(
            class_metrics["no_answer"]["_precision"], Fraction(9, 10)
        ),
        "no_answer_recall": _gate_minimum(
            class_metrics["no_answer"]["_recall"], Fraction(9, 10)
        ),
        "boxed_final_miss": _gate_maximum_count(boxed_final_misses, 0),
        "last_number_trap": _gate_maximum_count(last_number_trap_errors, 0),
        "wrong_span": _gate_maximum_count(wrong_span_errors, 1),
        "material_correctness": _gate_maximum_count(material_errors, 1),
        "material_correctness_S01": _gate_maximum_count(
            material_by_stratum["S01"], 0
        ),
        "material_correctness_S02": _gate_maximum_count(
            material_by_stratum["S02"], 0
        ),
        "clean_pooled_non_regression": (
            "PASS" if clean_v2 >= clean_legacy else "FAIL"
        ),
        "critical_strict_improvement": (
            "PASS" if any(gain >= 1 for gain in critical_gains.values()) else "FAIL"
        ),
    }
    for stratum in STRATA:
        correct = per_stratum[stratum]["parser_v2_correct"]
        gates[f"stratum_floor_{stratum}"] = _gate_minimum(
            Fraction(correct, 10), Fraction(4, 5)
        )
        if stratum in ANSWER_BEARING_STRATA:
            gates[f"answer_bearing_{stratum}"] = _gate_minimum(
                Fraction(correct, 10), Fraction(17, 20)
            )
    status: Literal["PASS", "FAIL", "INVALID"]
    if any(value == "INVALID" for value in gates.values()):
        status = "INVALID"
    elif any(value == "FAIL" for value in gates.values()):
        status = "FAIL"
    else:
        status = "PASS"

    public_class_metrics = {
        label: {
            key: value
            for key, value in metrics.items()
            if not key.startswith("_")
        }
        for label, metrics in class_metrics.items()
    }
    for stratum, values in per_stratum.items():
        values["exact_rate"] = _fraction_record(
            Fraction(values["parser_v2_correct"], values["denominator"])
        )
        values["critical"] = stratum in CRITICAL_STRATA
    return {
        "schema_version": "phase1-parser-v2-validation-metrics/v1",
        "status": status,
        "overall_exact_typed_decision": {
            "correct": parser_correct_count,
            "denominator": 120,
            "rate": _fraction_record(overall_ratio),
        },
        "confusion_matrix": confusion,
        "class_metrics": public_class_metrics,
        "answer_presence_macro_f1": _fraction_record(macro_f1),
        "per_stratum": per_stratum,
        "critical": {
            "denominator": 80,
            "parser_v2_correct": sum(
                per_stratum[stratum]["parser_v2_correct"]
                for stratum in CRITICAL_STRATA
            ),
            "legacy_correct": sum(
                per_stratum[stratum]["legacy_correct"]
                for stratum in CRITICAL_STRATA
            ),
            "net_gain_by_stratum": critical_gains,
        },
        "span_errors": {
            "boxed_final_miss": boxed_final_misses,
            "boxed_final_miss_denominator": 20,
            "boxed_final_miss_rate": _fraction_record(
                Fraction(boxed_final_misses, 20)
            ),
            "last_number_trap": last_number_trap_errors,
            "last_number_trap_denominator": 10,
            "last_number_trap_rate": _fraction_record(
                Fraction(last_number_trap_errors, 10)
            ),
            "wrong_span": wrong_span_errors,
            "wrong_span_denominator": 80,
            "wrong_span_rate": _fraction_record(
                Fraction(wrong_span_errors, 80)
            ),
        },
        "material_correctness": {
            "errors": material_errors,
            "denominator": 120,
            "rate": _fraction_record(Fraction(material_errors, 120)),
            "by_stratum": dict(
                sorted((stratum, material_by_stratum[stratum]) for stratum in STRATA)
            ),
        },
        "legacy_comparison": {
            "legacy_correct": legacy_correct_count,
            "parser_v2_correct": parser_correct_count,
            "clean_parser_v2_correct": clean_v2,
            "clean_legacy_correct": clean_legacy,
            "clean_denominator": 40,
            "clean_paired_regressions": paired_regressions,
            "critical_net_gain_by_stratum": critical_gains,
            "adapter_failure_count": len(adapter_failures),
            "adapter_failure_ids": adapter_failures,
        },
        "gates": dict(sorted(gates.items())),
    }


def score_validation_set(
    final_labels: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    legacy_predictions: Sequence[Mapping[str, Any]],
    *,
    locked_inputs: Sequence[Mapping[str, Any]] | None = None,
    prediction_seal: Mapping[str, Any] | None = None,
    implementation_commit: str | None = None,
    raise_on_invalid: bool = False,
) -> dict[str, Any]:
    """Score fail-closed; integrity/scorer failures return INVALID by default."""
    try:
        if (
            locked_inputs is None
            or prediction_seal is None
            or implementation_commit is None
        ):
            raise ValidationSetError(
                "scoring requires locked inputs, a prediction seal, "
                "and the frozen implementation commit"
            )
        return _score_validation_set(
            final_labels,
            predictions,
            legacy_predictions,
            locked_inputs=locked_inputs,
            prediction_seal=prediction_seal,
            implementation_commit=implementation_commit,
        )
    except (ValidationSetError, ArithmeticError, KeyError, TypeError, ValueError) as exc:
        if raise_on_invalid:
            raise
        return {
            "schema_version": "phase1-parser-v2-validation-metrics/v1",
            "status": "INVALID",
            "invalid_reason": type(exc).__name__,
            "gates": {"integrity_and_scorer": "INVALID"},
        }


compute_validation_metrics = score_validation_set


def normalize_blob_prefix(prefix: str) -> str:
    """Return a normalized relative Blob prefix or fail closed."""
    checked = _require_string(prefix, "Blob prefix")
    if "\\" in checked or "\x00" in checked:
        raise ValidationSetError("Blob prefix must use forward-slash segments")
    normalized = checked.strip("/")
    if checked != normalized or not normalized or "//" in normalized:
        raise ValidationSetError("Blob prefix is empty or non-normalized")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValidationSetError("Blob prefix contains a non-normalized segment")
    if any(any(ord(character) < 32 for character in part) for part in parts):
        raise ValidationSetError("Blob prefix contains a control character")
    return normalized


def validate_registered_parent_prefix(prefix: str) -> str:
    """Validate the exact v1 parent namespace and a real UTC timestamp."""
    normalized = normalize_blob_prefix(prefix)
    match = _REGISTERED_PARENT_PATTERN.fullmatch(normalized)
    if match is None:
        raise ValidationSetError(
            "parent prefix must equal "
            "phase1-evaluator-validation/parser-v2-v1/YYYYMMDDTHHMMSSZ"
        )
    try:
        datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ")
    except ValueError as exc:
        raise ValidationSetError(
            "parent prefix timestamp is not a real UTC calendar timestamp"
        ) from exc
    return normalized


def _prefixes_overlap(left: str, right: str) -> bool:
    return (
        left == right
        or left.startswith(f"{right}/")
        or right.startswith(f"{left}/")
    )


def validate_prefix_isolation(
    source_prefixes: Sequence[str], output_prefixes: Sequence[str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Reject equal, ancestor, descendant, prohibited, or malformed prefixes."""
    if isinstance(source_prefixes, (str, bytes)) or isinstance(
        output_prefixes, (str, bytes)
    ):
        raise ValidationSetError("prefix collections must be sequences of strings")
    sources = tuple(normalize_blob_prefix(item) for item in source_prefixes)
    outputs = tuple(normalize_blob_prefix(item) for item in output_prefixes)
    if not sources:
        raise ValidationSetError("at least one source prefix is required")
    if not outputs:
        raise ValidationSetError("at least one output prefix is required")
    if len(set(sources)) != len(sources) or len(set(outputs)) != len(outputs):
        raise ValidationSetError("prefix collections contain duplicates")
    for left_index, left in enumerate(sources):
        for right in sources[left_index + 1 :]:
            if _prefixes_overlap(left, right):
                raise ValidationSetError("source prefixes must be pairwise isolated")
    for left_index, left in enumerate(outputs):
        for right in outputs[left_index + 1 :]:
            if _prefixes_overlap(left, right):
                raise ValidationSetError("output prefixes must be pairwise isolated")
        for prohibited in PROHIBITED_OUTPUT_PREFIXES:
            if _prefixes_overlap(left, prohibited):
                raise ValidationSetError("output prefix overlaps a prohibited source")
        for source in sources:
            if _prefixes_overlap(left, source):
                raise ValidationSetError("source and output prefixes must be isolated")
    return sources, outputs


def validate_source_output_prefixes(
    source_prefix: str, output_prefix: str
) -> tuple[str, str]:
    sources, outputs = validate_prefix_isolation([source_prefix], [output_prefix])
    return sources[0], outputs[0]


def build_upload_plan(parent_prefix: str) -> list[str]:
    """Return the exact protocol order, reservation-first and manifest-last."""
    parent = validate_registered_parent_prefix(parent_prefix)
    plan = [
        f"{parent}/{leaf}/{filename}"
        for leaf, filenames in REGISTERED_LEAF_MEMBERS.items()
        for filename in filenames
    ]
    if Path(plan[-1]).name != "locked_manifest.json":
        raise AssertionError("registered upload plan must end with overall manifest")
    return plan


def expected_parent_membership(parent_prefix: str) -> frozenset[str]:
    return frozenset(build_upload_plan(parent_prefix))


def validate_registered_local_membership(
    local_root: str | Path,
) -> dict[str, bytes]:
    """Read only the exact five registered leaf layouts from a supplied root."""
    root = Path(local_root)
    if not root.is_dir() or root.is_symlink():
        raise ValidationSetError("registered local root must be a directory")
    actual_root = {path.name for path in root.iterdir()}
    if actual_root != set(REGISTERED_LEAF_MEMBERS):
        raise ValidationSetError(
            "local root membership must equal the five registered leaf directories"
        )
    files: dict[str, bytes] = {}
    for leaf, expected_names in REGISTERED_LEAF_MEMBERS.items():
        directory = root / leaf
        if not directory.is_dir() or directory.is_symlink():
            raise ValidationSetError(f"registered leaf is invalid: {leaf}")
        actual_names = {path.name for path in directory.iterdir()}
        if actual_names != set(expected_names):
            raise ValidationSetError(
                f"local leaf membership differs for {leaf}"
            )
        for filename in expected_names:
            path = directory / filename
            if not path.is_file() or path.is_symlink():
                raise ValidationSetError(f"registered member is not a regular file: {leaf}/{filename}")
            data = path.read_bytes()
            artifact_name = f"{leaf}/{filename}"
            if filename.endswith(".jsonl"):
                parse_jsonl_strict(
                    data,
                    artifact_name,
                    require_canonical=True,
                    allow_empty=True,
                )
            elif filename.endswith(".json"):
                parse_json_strict(data, artifact_name, require_canonical=True)
            elif filename.endswith(".md"):
                try:
                    data.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ValidationSetError(
                        f"{artifact_name} is not UTF-8"
                    ) from exc
                if data and not data.endswith(b"\n"):
                    raise ValidationSetError(
                        f"{artifact_name} must end with LF"
                    )
            files[artifact_name] = data
    expected_order = [
        f"{leaf}/{filename}"
        for leaf, names in REGISTERED_LEAF_MEMBERS.items()
        for filename in names
    ]
    return {name: files[name] for name in expected_order}


_FILE_METADATA_FIELDS = frozenset({"path", "size", "sha256"})
_MANIFEST_FIELDS = frozenset(
    {
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
)


def _validate_count_tree(value: Any, name: str) -> None:
    if type(value) is int:
        if value < 0:
            raise ValidationSetError(f"{name} count must be nonnegative")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _require_string(key, f"{name} key")
            _validate_count_tree(item, f"{name}.{key}")
        return
    raise ValidationSetError(f"{name} must contain only nested integer counts")


def build_manifest(
    *,
    manifest_kind: str,
    project_root: str | Path,
    created_utc: str,
    parent_prefix: str,
    ordered_case_ids: Sequence[str],
    counts: Mapping[str, int],
    schemas: Mapping[str, str],
    files: Mapping[str, bytes],
    reservation_sha256: str,
    review_seals: Sequence[Mapping[str, Any]],
    arbitration: Mapping[str, int],
    feature_counts: Mapping[str, Any],
    visibility_ledger_sha256: str,
    source_prefixes: Sequence[str],
    private_nonce: str,
) -> dict[str, Any]:
    """Build one strict manifest using exact local bytes and frozen Git blobs."""
    metadata = [
        {
            "path": path,
            "size": len(data),
            "sha256": sha256_bytes(data),
        }
        for path, data in files.items()
    ]
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_kind": manifest_kind,
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": protocol_bundle_sha256(project_root),
        "acceptance_gates_sha256": acceptance_gates_sha256(project_root),
        "created_utc": created_utc,
        "parent_prefix": validate_registered_parent_prefix(parent_prefix),
        "ordered_case_ids": list(ordered_case_ids),
        "counts": dict(counts),
        "schemas": dict(schemas),
        "files": metadata,
        "reservation_sha256": reservation_sha256,
        "review_seals": [dict(item) for item in review_seals],
        "arbitration": dict(arbitration),
        "feature_counts": dict(feature_counts),
        "visibility_ledger_sha256": visibility_ledger_sha256,
        "source_prefixes": list(source_prefixes),
        "private_nonce": private_nonce,
        "model_inference_performed": False,
        "no_model_run_attestation": True,
        "manifest_uploaded_last": True,
    }
    validate_manifest(manifest)
    return manifest


def validate_manifest(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate common manifest bindings without accepting optional extra fields."""
    _require_exact_fields(record, _MANIFEST_FIELDS, "manifest")
    if record["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ValidationSetError("manifest schema_version is invalid")
    _require_enum(
        record["manifest_kind"],
        tuple(REGISTERED_LEAF_MEMBERS),
        "manifest_kind",
    )
    if _require_commit(record["protocol_commit"], "protocol_commit") != FROZEN_PROTOCOL_COMMIT:
        raise ValidationSetError("manifest protocol_commit is not frozen")
    if (
        _require_sha256(
            record["protocol_bundle_sha256"], "protocol_bundle_sha256"
        )
        != FROZEN_PROTOCOL_BUNDLE_SHA256
    ):
        raise ValidationSetError("manifest protocol bundle is not the final binding")
    if (
        _require_sha256(
            record["acceptance_gates_sha256"], "acceptance_gates_sha256"
        )
        != FROZEN_ACCEPTANCE_GATE_SHA256
    ):
        raise ValidationSetError("manifest acceptance gate is not the final binding")
    _require_utc_timestamp(record["created_utc"], "created_utc")
    validate_registered_parent_prefix(record["parent_prefix"])
    if not isinstance(record["ordered_case_ids"], list):
        raise ValidationSetError("ordered_case_ids must be a list")
    ids = [_require_case_id(item) for item in record["ordered_case_ids"]]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValidationSetError("ordered_case_ids must be unique and sorted")
    for field in ("counts", "arbitration"):
        value = record[field]
        if not isinstance(value, Mapping) or any(
            not isinstance(key, str) or type(item) is not int or item < 0
            for key, item in value.items()
        ):
            raise ValidationSetError(f"manifest {field} must map strings to integers")
    if not isinstance(record["schemas"], Mapping) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in record["schemas"].items()
    ):
        raise ValidationSetError("manifest schemas must map strings to strings")
    if not isinstance(record["files"], list):
        raise ValidationSetError("manifest files must be a list")
    paths: list[str] = []
    for index, item in enumerate(record["files"]):
        _require_exact_fields(item, _FILE_METADATA_FIELDS, f"manifest files[{index}]")
        path = _require_string(item["path"], f"manifest files[{index}].path")
        path_parts = path.split("/")
        if (
            "\\" in path
            or path.startswith("/")
            or any(part in {"", ".", ".."} for part in path_parts)
            or any(
                ord(character) < 32
                for part in path_parts
                for character in part
            )
        ):
            raise ValidationSetError("manifest file path is not normalized")
        _require_int(item["size"], f"manifest files[{index}].size", minimum=0)
        _require_sha256(item["sha256"], f"manifest files[{index}].sha256", allow_zero=True)
        paths.append(path)
    if len(paths) != len(set(paths)):
        raise ValidationSetError("manifest contains duplicate file paths")
    _require_sha256(record["reservation_sha256"], "reservation_sha256")
    if not isinstance(record["review_seals"], list):
        raise ValidationSetError("review_seals must be a list")
    seal_hashes: list[str] = []
    for index, seal in enumerate(record["review_seals"]):
        _require_exact_fields(
            seal, _REVIEW_SEAL_FIELDS, f"review_seals[{index}]"
        )
        if seal["schema_version"] != REVIEW_SEAL_SCHEMA_VERSION:
            raise ValidationSetError("manifest contains an invalid review seal")
        seal_hashes.append(review_seal_sha256(seal))
    if len(seal_hashes) != len(set(seal_hashes)):
        raise ValidationSetError("review_seals must be unique")
    if not isinstance(record["feature_counts"], Mapping):
        raise ValidationSetError("feature_counts must be an object")
    _validate_count_tree(record["feature_counts"], "feature_counts")
    _require_sha256(
        record["visibility_ledger_sha256"], "visibility_ledger_sha256"
    )
    if not isinstance(record["source_prefixes"], list):
        raise ValidationSetError("source_prefixes must be a list")
    sources = [normalize_blob_prefix(item) for item in record["source_prefixes"]]
    if sources != record["source_prefixes"]:
        raise ValidationSetError("source_prefixes must already be normalized")
    validate_prefix_isolation(sources, [record["parent_prefix"]])
    _require_string(record["private_nonce"], "private_nonce")
    if len(record["private_nonce"].encode("utf-8")) < 16:
        raise ValidationSetError("private_nonce must contain at least 16 bytes")
    if record["model_inference_performed"] is not False:
        raise ValidationSetError("manifest must attest no model inference")
    if record["no_model_run_attestation"] is not True:
        raise ValidationSetError("manifest no-model-run attestation is required")
    if record["manifest_uploaded_last"] is not True:
        raise ValidationSetError("manifest_uploaded_last must be true")
    return {"file_count": len(paths), "case_count": len(ids)}


_RESERVATION_FIELDS = frozenset(
    {"schema_version", "leaf", "parent_prefix", "created_utc", "private_nonce"}
)
_VISIBILITY_FIELDS = frozenset(
    {
        "schema_version",
        "actor_id",
        "role",
        "artifact_classes",
        "purpose",
        "authorization",
        "execution_id",
        "model_id",
        "reasoning_effort",
        "first_access_utc",
        "last_access_utc",
    }
)
VISIBILITY_ROLE_ARTIFACT_CLASSES = {
    "curator": tuple(
        sorted(
            {
                "construction-schema",
                "frozen-protocol",
                "own-candidate-pool",
                "own-curator-pool-seal",
            }
        )
    ),
    "curator_c": tuple(
        sorted(
            {
                "curator-candidate-pools",
                "curator-pool-seals",
                "frozen-protocol",
                "selection-plan",
            }
        )
    ),
    "custodian": tuple(
        sorted(
            {
                "curator-candidate-pools",
                "curator-pool-seals",
                "curator-label-drafts",
                "frozen-protocol",
                "historical-corpus",
                "locked-inputs",
                "locked-reference-labels",
                "overlap-report",
                "review-seals",
                "selection-plan",
                "stage1-consensus",
                "stage2-reference-packet",
            }
        )
    ),
    "stage1_reviewer": tuple(
        sorted({"frozen-protocol", "locked-inputs", "stage1-rubric"})
    ),
    "stage1_arbiter": tuple(
        sorted(
            {
                "frozen-protocol",
                "locked-inputs",
                "stage1-review-submissions",
                "stage1-rubric",
            }
        )
    ),
    "stage2_reviewer": tuple(
        sorted(
            {
                "frozen-protocol",
                "stage1-consensus",
                "stage2-reference-packet",
                "stage2-rubric",
            }
        )
    ),
    "stage2_arbiter": tuple(
        sorted(
            {
                "frozen-protocol",
                "stage1-consensus",
                "stage2-reference-packet",
                "stage2-review-submissions",
                "stage2-rubric",
            }
        )
    ),
}
STAGE1_PROHIBITED_ARTIFACT_CLASSES = frozenset(
    {
        "future-parser-predictions",
        "locked-reference-labels",
        "stage1-consensus",
        "stage2-reference-packet",
        "stage2-review-submissions",
    }
)
_VALIDATION_REPORT_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "development_count",
        "locked_count",
        "agreement",
        "arbitration",
        "unresolved_count",
        "model_inference_performed",
    }
)
_AGREEMENT_FIELDS = frozenset(
    {
        "row_count",
        "fields",
        "normalized_parsed_answer_exact_count",
        "candidate_list_exact_count",
        "candidate_list_mean_jaccard",
        "selected_span_exact_count",
        "selected_span_mean_jaccard",
        "sets",
        "arbitration_count",
        "arbitration_ids",
        "unresolved_count",
        "correctness",
    }
)
_AGREEMENT_NOMINAL_FIELDS = (
    "answer_presence",
    "parse_valid",
    "parse_ambiguous",
    "extraction_strategy",
    "output_quality",
)
_FRACTION_RECORD_FIELDS = frozenset(
    {"numerator", "denominator", "canonical", "display"}
)
_OVERLAP_REPORT_FIELDS = frozenset(
    {
        "schema_version",
        "exact_duplicates",
        "normalized_duplicates",
        "historical_exact_overlaps",
        "historical_normalized_overlaps",
        "cross_set_template_family_overlaps",
        "hard_failure_count",
        "near_duplicates",
        "near_duplicate_dispositions",
        "near_duplicate_dispositions_complete",
    }
)
_NEAR_DUPLICATE_FINDING_FIELDS = frozenset(
    {
        "left_id",
        "right_id",
        "left_set",
        "right_set",
        "similarity_numerator",
        "similarity_denominator",
        "similarity",
    }
)


def validate_reservation(
    record: Mapping[str, Any], *, leaf: str, parent_prefix: str
) -> dict[str, Any]:
    _require_exact_fields(record, _RESERVATION_FIELDS, f"{leaf} reservation")
    if record["schema_version"] != RESERVATION_SCHEMA_VERSION:
        raise ValidationSetError(f"{leaf} reservation schema_version is invalid")
    if record["leaf"] != leaf:
        raise ValidationSetError(f"{leaf} reservation leaf mismatch")
    if validate_registered_parent_prefix(
        record["parent_prefix"]
    ) != validate_registered_parent_prefix(
        parent_prefix
    ):
        raise ValidationSetError(f"{leaf} reservation parent mismatch")
    _require_utc_timestamp(record["created_utc"], f"{leaf} reservation created_utc")
    nonce = _require_string(
        record["private_nonce"], f"{leaf} reservation private_nonce"
    )
    if len(nonce.encode("utf-8")) < 16:
        raise ValidationSetError(f"{leaf} reservation nonce is too short")
    return {"private_nonce": nonce}


def validate_visibility_ledger(
    rows: Sequence[Mapping[str, Any]],
    *,
    curator_pool_seals: Sequence[Mapping[str, Any]] | None = None,
    curator_c_id: str | None = None,
    custodian_id: str | None = None,
    review_seals: Sequence[Mapping[str, Any]] | None = None,
) -> None:
    if not rows:
        raise ValidationSetError("visibility ledger must not be empty")
    keys: list[tuple[str, str]] = []
    for index, row in enumerate(rows):
        name = f"visibility ledger[{index}]"
        _require_exact_fields(row, _VISIBILITY_FIELDS, name)
        if row["schema_version"] != VISIBILITY_LEDGER_SCHEMA_VERSION:
            raise ValidationSetError(f"{name}.schema_version is invalid")
        for field in (
            "actor_id",
            "purpose",
            "authorization",
            "execution_id",
        ):
            _require_string(row[field], f"{name}.{field}")
        role = _require_enum(
            row["role"],
            tuple(VISIBILITY_ROLE_ARTIFACT_CLASSES),
            f"{name}.role",
        )
        if not isinstance(row["artifact_classes"], list):
            raise ValidationSetError(f"{name}.artifact_classes must be a list")
        classes = [
            _require_string(item, f"{name}.artifact_classes[{item_index}]")
            for item_index, item in enumerate(row["artifact_classes"])
        ]
        if classes != sorted(set(classes)) or not classes:
            raise ValidationSetError(
                f"{name}.artifact_classes must be nonempty, unique, and sorted"
            )
        if tuple(classes) != VISIBILITY_ROLE_ARTIFACT_CLASSES[role]:
            raise ValidationSetError(
                f"{name}.artifact_classes do not equal the registered role visibility"
            )
        if role.startswith("stage1") and (
            set(classes) & STAGE1_PROHIBITED_ARTIFACT_CLASSES
        ):
            raise ValidationSetError(
                f"{name} exposes a prohibited reference or future artifact"
            )
        expected_model = None if role == "custodian" else REVIEWER_MODEL_ID
        expected_effort = (
            None if role == "custodian" else REVIEWER_REASONING_EFFORT
        )
        if row["model_id"] != expected_model:
            raise ValidationSetError(f"{name}.model_id is not registered")
        if row["reasoning_effort"] != expected_effort:
            raise ValidationSetError(f"{name}.reasoning_effort is not registered")
        first = _require_utc_timestamp(
            row["first_access_utc"], f"{name}.first_access_utc"
        )
        last = _require_utc_timestamp(
            row["last_access_utc"], f"{name}.last_access_utc"
        )
        if first > last:
            raise ValidationSetError(f"{name} access interval is reversed")
        keys.append((row["actor_id"], role))
    if len(keys) != len(set(keys)):
        raise ValidationSetError("visibility ledger repeats an actor/role row")

    supplied = (
        curator_pool_seals,
        curator_c_id,
        custodian_id,
        review_seals,
    )
    if any(item is not None for item in supplied) and any(
        item is None for item in supplied
    ):
        raise ValidationSetError(
            "visibility cross-check requires curator, Curator-C, custodian, "
            "and review bindings"
        )
    if curator_pool_seals is not None:
        if (
            len(curator_pool_seals) != 2
            or review_seals is None
            or len(review_seals) != 7
        ):
            raise ValidationSetError("visibility actor bindings are incomplete")
        curator_ids = [
            _require_string(
                seal["curator_id"],
                f"curator_pool_seals[{index}].curator_id",
            )
            for index, seal in enumerate(curator_pool_seals)
        ]
        checked_curator_c = _require_string(curator_c_id, "curator_c_id")
        checked_custodian = _require_string(custodian_id, "custodian_id")
        if checked_curator_c != REGISTERED_CURATOR_C_ID:
            raise ValidationSetError("visibility Curator-C identity is not registered")
        if checked_custodian != REGISTERED_CUSTODIAN_ID:
            raise ValidationSetError("visibility custodian identity is not registered")
        construction_actors = {
            *curator_ids,
            checked_curator_c,
            checked_custodian,
        }
        if len(set(curator_ids)) != 2 or len(construction_actors) != 4:
            raise ValidationSetError(
                "visibility curator, Curator-C, and custodian actors must be distinct"
            )
        seal_actors = [
            _require_string(
                seal["actor_id"], f"review_seals[{index}].actor_id"
            )
            for index, seal in enumerate(review_seals)
        ]
        stage1_reviewers = seal_actors[0:2]
        stage1_arbiter = seal_actors[2]
        stage1_consensus_actor = seal_actors[3]
        stage2_reviewers = seal_actors[4:6]
        stage2_arbiter = seal_actors[6]
        review_actors = {
            *stage1_reviewers,
            stage1_arbiter,
            stage1_consensus_actor,
            *stage2_reviewers,
            stage2_arbiter,
        }
        if (
            stage1_reviewers[0] == stage1_reviewers[1]
            or stage1_arbiter in stage1_reviewers
            or stage2_reviewers != stage1_reviewers
            or stage1_consensus_actor != stage1_arbiter
            or stage2_arbiter != stage1_arbiter
            or construction_actors & review_actors
        ):
            raise ValidationSetError(
                "visibility actor separation or Stage-1/Stage-2 continuity failed"
            )
        expected = {
            (seal["curator_id"], "curator") for seal in curator_pool_seals
        }
        expected.add((checked_curator_c, "curator_c"))
        expected.add((checked_custodian, "custodian"))
        expected.update(
            {
                (review_seals[0]["actor_id"], "stage1_reviewer"),
                (review_seals[1]["actor_id"], "stage1_reviewer"),
                (review_seals[2]["actor_id"], "stage1_arbiter"),
                (review_seals[4]["actor_id"], "stage2_reviewer"),
                (review_seals[5]["actor_id"], "stage2_reviewer"),
                (review_seals[6]["actor_id"], "stage2_arbiter"),
            }
        )
        if set(keys) != expected:
            raise ValidationSetError(
                "visibility ledger actor/role membership does not match seals"
            )


def _validate_fraction_report(record: Mapping[str, Any], name: str) -> None:
    _require_exact_fields(record, _FRACTION_RECORD_FIELDS, name)
    numerator = record["numerator"]
    denominator = record["denominator"]
    canonical = record["canonical"]
    display = record["display"]
    if numerator is None:
        if denominator is not None or canonical is not None or display != "NA":
            raise ValidationSetError(f"{name} has an invalid NA representation")
        return
    numerator = _require_int(numerator, f"{name}.numerator")
    denominator = _require_int(
        denominator, f"{name}.denominator", minimum=1
    )
    value = Fraction(numerator, denominator)
    if value.numerator != numerator or value.denominator != denominator:
        raise ValidationSetError(f"{name} is not reduced")
    expected = (
        str(numerator)
        if denominator == 1
        else f"{numerator}/{denominator}"
    )
    if canonical != expected or display != expected:
        raise ValidationSetError(f"{name} canonical/display value is inconsistent")


def _validate_agreement_report(record: Mapping[str, Any]) -> None:
    _require_exact_fields(record, _AGREEMENT_FIELDS, "agreement report")
    row_count = _require_int(
        record["row_count"], "agreement report row_count", minimum=0
    )
    if row_count != 120:
        raise ValidationSetError("agreement report must cover 120 rows")
    if not isinstance(record["fields"], Mapping) or set(
        record["fields"]
    ) != set(_AGREEMENT_NOMINAL_FIELDS):
        raise ValidationSetError("agreement report nominal fields are incomplete")
    for field in _AGREEMENT_NOMINAL_FIELDS:
        item = record["fields"][field]
        _require_exact_fields(
            item,
            {
                "exact_agreement_count",
                "denominator",
                "rate",
                "nominal_kappa",
            },
            f"agreement report fields.{field}",
        )
        exact = _require_int(
            item["exact_agreement_count"],
            f"agreement report fields.{field}.exact_agreement_count",
            minimum=0,
        )
        denominator = _require_int(
            item["denominator"],
            f"agreement report fields.{field}.denominator",
            minimum=0,
        )
        if denominator != row_count or exact > denominator:
            raise ValidationSetError("agreement field counts are inconsistent")
        _validate_fraction_report(
            item["rate"], f"agreement report fields.{field}.rate"
        )
        _validate_fraction_report(
            item["nominal_kappa"],
            f"agreement report fields.{field}.nominal_kappa",
        )
    for field in (
        "normalized_parsed_answer_exact_count",
        "candidate_list_exact_count",
        "selected_span_exact_count",
    ):
        value = _require_int(record[field], f"agreement report {field}", minimum=0)
        if value > row_count:
            raise ValidationSetError(f"agreement report {field} exceeds row count")
    for field in (
        "candidate_list_mean_jaccard",
        "selected_span_mean_jaccard",
    ):
        _validate_fraction_report(record[field], f"agreement report {field}")
    if not isinstance(record["sets"], Mapping) or set(record["sets"]) != {
        "failure_reasons",
        "format_warnings",
    }:
        raise ValidationSetError("agreement report set metrics are incomplete")
    for field in ("failure_reasons", "format_warnings"):
        item = record["sets"][field]
        _require_exact_fields(
            item,
            {"exact_agreement_count", "mean_jaccard"},
            f"agreement report sets.{field}",
        )
        exact = _require_int(
            item["exact_agreement_count"],
            f"agreement report sets.{field}.exact_agreement_count",
            minimum=0,
        )
        if exact > row_count:
            raise ValidationSetError("agreement set exact count exceeds row count")
        _validate_fraction_report(
            item["mean_jaccard"],
            f"agreement report sets.{field}.mean_jaccard",
        )
    correctness = record["correctness"]
    _require_exact_fields(
        correctness,
        {"exact_agreement_count", "denominator", "rate", "nominal_kappa"},
        "agreement report correctness",
    )
    exact = _require_int(
        correctness["exact_agreement_count"],
        "agreement report correctness exact_agreement_count",
        minimum=0,
    )
    denominator = _require_int(
        correctness["denominator"],
        "agreement report correctness denominator",
        minimum=0,
    )
    if denominator != row_count or exact > denominator:
        raise ValidationSetError("agreement correctness counts are inconsistent")
    _validate_fraction_report(
        correctness["rate"], "agreement report correctness rate"
    )
    _validate_fraction_report(
        correctness["nominal_kappa"],
        "agreement report correctness nominal_kappa",
    )
    if not isinstance(record["arbitration_ids"], list):
        raise ValidationSetError("agreement arbitration_ids must be a list")
    arbitration_ids = [
        _require_case_id(item)
        for item in record["arbitration_ids"]
    ]
    if arbitration_ids != sorted(set(arbitration_ids)):
        raise ValidationSetError("agreement arbitration IDs are not exact and ordered")
    if _require_int(
        record["arbitration_count"],
        "agreement arbitration_count",
        minimum=0,
    ) != len(arbitration_ids):
        raise ValidationSetError("agreement arbitration count mismatch")
    _require_int(
        record["unresolved_count"],
        "agreement unresolved_count",
        minimum=0,
    )


def _validate_validation_report(
    record: Mapping[str, Any],
    *,
    expected_agreement: Mapping[str, Any] | None = None,
    expected_stage1_ids: Sequence[str] | None = None,
    expected_stage2_ids: Sequence[str] | None = None,
) -> None:
    _require_exact_fields(record, _VALIDATION_REPORT_FIELDS, "validation report")
    if record["schema_version"] != VALIDATION_REPORT_SCHEMA_VERSION:
        raise ValidationSetError("validation report schema_version is invalid")
    if record["status"] != "SEALED":
        raise ValidationSetError("validation report status must equal SEALED")
    if (
        _require_int(record["development_count"], "development_count") != 60
        or _require_int(record["locked_count"], "locked_count") != 120
        or _require_int(record["unresolved_count"], "unresolved_count") != 0
    ):
        raise ValidationSetError("validation report counts are invalid")
    if record["model_inference_performed"] is not False:
        raise ValidationSetError("validation report must attest no model inference")
    if not isinstance(record["agreement"], Mapping):
        raise ValidationSetError("validation report agreement must be an object")
    _validate_agreement_report(record["agreement"])
    if expected_agreement is not None and record["agreement"] != expected_agreement:
        raise ValidationSetError("validation report agreement metrics are not derived")
    if not isinstance(record["arbitration"], Mapping) or set(
        record["arbitration"]
    ) != {"stage1", "stage2"}:
        raise ValidationSetError("validation report arbitration is incomplete")
    expected_by_stage = {
        "stage1": expected_stage1_ids,
        "stage2": expected_stage2_ids,
    }
    for stage, expected_ids in expected_by_stage.items():
        item = record["arbitration"][stage]
        _require_exact_fields(
            item, {"count", "case_ids"}, f"validation report arbitration.{stage}"
        )
        if not isinstance(item["case_ids"], list):
            raise ValidationSetError(
                f"validation report arbitration.{stage}.case_ids must be a list"
            )
        ids = [_require_case_id(case_id) for case_id in item["case_ids"]]
        if ids != sorted(set(ids)):
            raise ValidationSetError(
                f"validation report arbitration.{stage} IDs are not exact"
            )
        if _require_int(
            item["count"],
            f"validation report arbitration.{stage}.count",
            minimum=0,
        ) != len(ids):
            raise ValidationSetError(
                f"validation report arbitration.{stage} count mismatch"
            )
        if expected_ids is not None and ids != list(expected_ids):
            raise ValidationSetError(
                f"validation report arbitration.{stage} IDs are not derived"
            )


def render_validation_report_markdown(record: Mapping[str, Any]) -> bytes:
    """Render the one registered Markdown representation of the JSON report."""
    _validate_validation_report(record)
    body = canonical_json_bytes(dict(record)).decode("ascii")
    return (
        "# Phase 1 Parser V2 Validation-Set Report\n\n"
        "This report is a deterministic rendering of the sealed JSON record.\n\n"
        "```json\n"
        f"{body}"
        "```\n"
    ).encode("ascii")


def _validate_overlap_release_report(record: Mapping[str, Any]) -> None:
    _require_exact_fields(record, _OVERLAP_REPORT_FIELDS, "overlap report")
    if record["schema_version"] != "phase1-parser-v2-overlap-report/v1":
        raise ValidationSetError("overlap report schema_version is invalid")
    for field in (
        "exact_duplicates",
        "normalized_duplicates",
        "historical_exact_overlaps",
        "historical_normalized_overlaps",
        "cross_set_template_family_overlaps",
        "near_duplicates",
        "near_duplicate_dispositions",
    ):
        if not isinstance(record[field], list):
            raise ValidationSetError(f"overlap report {field} must be a list")
    if (
        _require_int(record["hard_failure_count"], "overlap hard_failure_count")
        != 0
        or record["near_duplicate_dispositions_complete"] is not True
    ):
        raise ValidationSetError("overlap report is not sealable")
    hard_fields = (
        "exact_duplicates",
        "normalized_duplicates",
        "historical_exact_overlaps",
        "historical_normalized_overlaps",
        "cross_set_template_family_overlaps",
    )
    if any(record[field] for field in hard_fields):
        raise ValidationSetError(
            "overlap report contains a hard duplicate despite a zero count"
        )
    near_pairs: list[tuple[str, str]] = []
    for index, finding in enumerate(record["near_duplicates"]):
        name = f"overlap report near_duplicates[{index}]"
        _require_exact_fields(finding, _NEAR_DUPLICATE_FINDING_FIELDS, name)
        left = _require_string(finding["left_id"], f"{name}.left_id")
        right = _require_string(finding["right_id"], f"{name}.right_id")
        if left >= right:
            raise ValidationSetError(f"{name} IDs must be distinct and sorted")
        _require_enum(
            finding["left_set"], ("development", "locked"), f"{name}.left_set"
        )
        _require_enum(
            finding["right_set"], ("development", "locked"), f"{name}.right_set"
        )
        numerator = _require_int(
            finding["similarity_numerator"],
            f"{name}.similarity_numerator",
            minimum=0,
        )
        denominator = _require_int(
            finding["similarity_denominator"],
            f"{name}.similarity_denominator",
            minimum=1,
        )
        if numerator > denominator:
            raise ValidationSetError(f"{name} similarity exceeds one")
        similarity = Fraction(numerator, denominator)
        if similarity < Fraction(17, 20):
            raise ValidationSetError(f"{name} is below the registered threshold")
        if finding["similarity"] != f"{float(similarity):.6f}":
            raise ValidationSetError(f"{name}.similarity display is inconsistent")
        near_pairs.append((left, right))
    if near_pairs != sorted(set(near_pairs)):
        raise ValidationSetError(
            "overlap report near-duplicate pairs must be unique and sorted"
        )
    validate_near_duplicate_dispositions(
        record["near_duplicates"], record["near_duplicate_dispositions"]
    )
    if any(
        item["decision"] != "keep"
        for item in record["near_duplicate_dispositions"]
    ):
        raise ValidationSetError(
            "released near-duplicate dispositions must all be keep decisions"
        )


def _manifest_metadata(
    relative_paths: Sequence[str], files: Mapping[str, bytes]
) -> list[dict[str, Any]]:
    return [
        {
            "path": path,
            "size": len(files[path]),
            "sha256": sha256_bytes(files[path]),
        }
        for path in relative_paths
    ]


def validate_release_artifacts(
    files: Mapping[str, bytes],
    parent_prefix: str,
    *,
    project_root: str | Path,
    historical_fingerprints: Sequence[Mapping[str, Any]],
    registered_draft_labels: Sequence[Mapping[str, Any]],
    source_prefixes: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Semantically validate the complete local release before any Blob write."""
    parent = validate_registered_parent_prefix(parent_prefix)
    checked_historical_fingerprints = _validate_historical_fingerprint_rows(
        historical_fingerprints
    )
    expected_relative = [
        f"{leaf}/{filename}"
        for leaf, names in REGISTERED_LEAF_MEMBERS.items()
        for filename in names
    ]
    if set(files) != set(expected_relative) or any(
        type(data) is not bytes for data in files.values()
    ):
        raise ValidationSetError("release artifact membership is not exact")
    for relative, data in files.items():
        if relative.endswith(".json"):
            parsed = parse_json_strict(data, relative)
            if canonical_json_bytes(parsed) != data:
                raise ValidationSetError(
                    f"release JSON is not canonical ASCII: {relative}"
                )
        elif relative.endswith(".jsonl"):
            parsed_rows = parse_jsonl_strict(data, relative, allow_empty=True)
            if canonical_jsonl_bytes(parsed_rows) != data:
                raise ValidationSetError(
                    f"release JSONL is not canonical ASCII: {relative}"
                )

    reservations: dict[str, Mapping[str, Any]] = {}
    manifests: dict[str, Mapping[str, Any]] = {}
    for leaf, names in REGISTERED_LEAF_MEMBERS.items():
        reservation_path = f"{leaf}/{names[0]}"
        reservation = parse_json_strict(
            files[reservation_path], reservation_path
        )
        validate_reservation(reservation, leaf=leaf, parent_prefix=parent)
        reservations[leaf] = reservation
        manifest_path = f"{leaf}/{names[-1]}"
        manifest = parse_json_strict(files[manifest_path], manifest_path)
        validate_manifest(manifest)
        manifests[leaf] = manifest
    if len({item["private_nonce"] for item in reservations.values()}) != len(
        reservations
    ):
        raise ValidationSetError("reservation private nonces must be unique")

    development = parse_jsonl_strict(
        files["development/development_cases.jsonl"],
        "development/development_cases.jsonl",
    )
    if len(development) != 60:
        raise ValidationSetError("development release must contain exactly 60 rows")
    development_ids: list[str] = []
    for index, row in enumerate(development):
        validate_development_record(row, name=f"development[{index}]")
        development_ids.append(row["case_id"])
    if development_ids != sorted(development_ids) or len(set(development_ids)) != 60:
        raise ValidationSetError("development release IDs are not exact and ordered")

    locked_inputs = parse_jsonl_strict(
        files["locked-inputs/locked_inputs.jsonl"],
        "locked-inputs/locked_inputs.jsonl",
    )
    locked_index = _locked_input_index(locked_inputs)
    locked_ids = sorted(locked_index)
    reviewer_a_stage1 = parse_jsonl_strict(
        files["locked-labels/reviewer_a_stage1.jsonl"],
        "locked-labels/reviewer_a_stage1.jsonl",
    )
    reviewer_b_stage1 = parse_jsonl_strict(
        files["locked-labels/reviewer_b_stage1.jsonl"],
        "locked-labels/reviewer_b_stage1.jsonl",
    )
    arbitration_stage1 = parse_jsonl_strict(
        files["locked-labels/arbitration_stage1.jsonl"],
        "locked-labels/arbitration_stage1.jsonl",
        allow_empty=True,
    )
    stage1_consensus = parse_jsonl_strict(
        files["locked-labels/stage1_consensus.jsonl"],
        "locked-labels/stage1_consensus.jsonl",
    )
    stage2_reference_packet = parse_jsonl_strict(
        files["locked-labels/stage2_reference_packet.jsonl"],
        "locked-labels/stage2_reference_packet.jsonl",
    )
    validate_stage2_reference_packet(stage2_reference_packet, locked_inputs)
    reviewer_a_stage2 = parse_jsonl_strict(
        files["locked-labels/reviewer_a_stage2.jsonl"],
        "locked-labels/reviewer_a_stage2.jsonl",
    )
    reviewer_b_stage2 = parse_jsonl_strict(
        files["locked-labels/reviewer_b_stage2.jsonl"],
        "locked-labels/reviewer_b_stage2.jsonl",
    )
    arbitration_stage2 = parse_jsonl_strict(
        files["locked-labels/arbitration_stage2.jsonl"],
        "locked-labels/arbitration_stage2.jsonl",
        allow_empty=True,
    )
    final_labels = parse_jsonl_strict(
        files["locked-labels/locked_reference_labels.jsonl"],
        "locked-labels/locked_reference_labels.jsonl",
    )
    _validate_locked_label_support(final_labels)
    label_index = {row["case_id"]: row for row in final_labels}
    if set(label_index) != set(locked_index) or any(
        label_index[case_id]["output_text"]
        != locked_index[case_id]["output_text"]
        for case_id in locked_ids
    ):
        raise ValidationSetError("locked input and final-label membership/text mismatch")

    locked_manifest = manifests["locked-labels"]
    review_seals = locked_manifest["review_seals"]
    expected_stages = (
        "stage1",
        "stage1",
        "stage1_arbitration",
        "stage1_consensus",
        "stage2",
        "stage2",
        "stage2_arbitration",
    )
    if (
        len(review_seals) != len(expected_stages)
        or tuple(item.get("review_stage") for item in review_seals)
        != expected_stages
    ):
        raise ValidationSetError("locked-label manifest review seals are incomplete")
    workflow = validate_complete_review_workflow(
        locked_inputs=locked_inputs,
        draft_labels=registered_draft_labels,
        stage2_reference_packet=stage2_reference_packet,
        reviewer_a_stage1=reviewer_a_stage1,
        reviewer_a_stage1_seal=review_seals[0],
        reviewer_b_stage1=reviewer_b_stage1,
        reviewer_b_stage1_seal=review_seals[1],
        arbitration_stage1=arbitration_stage1,
        arbitration_stage1_seal=review_seals[2],
        stage1_consensus_seal=review_seals[3],
        reviewer_a_stage2=reviewer_a_stage2,
        reviewer_a_stage2_seal=review_seals[4],
        reviewer_b_stage2=reviewer_b_stage2,
        reviewer_b_stage2_seal=review_seals[5],
        arbitration_stage2=arbitration_stage2,
        arbitration_stage2_seal=review_seals[6],
    )
    if stage1_consensus != validate_stage1_arbitration(
        arbitration_stage1,
        reviewer_a_stage1,
        reviewer_b_stage1,
        locked_inputs,
    )["consensus"]:
        raise ValidationSetError("persisted Stage-1 consensus is not derived")
    if workflow["final_labels"] != final_labels:
        raise ValidationSetError("persisted final labels are not derived")
    validate_final_labels_against_consensus(
        final_labels,
        locked_inputs,
        stage1_consensus,
        stage2_reference_packet,
        validate_stage2_arbitration(
            arbitration_stage2,
            reviewer_a_stage2,
            reviewer_b_stage2,
            locked_inputs,
            stage1_consensus,
            stage2_reference_packet,
        )["final_stage2"],
    )

    mapping = parse_json_strict(
        files["manifests/locked_case_mapping.json"],
        "manifests/locked_case_mapping.json",
    )
    validate_case_mapping(mapping)
    mapping_ids = {
        entry["set"]: {
            item["case_id"]
            for item in mapping["entries"]
            if item["set"] == entry["set"]
        }
        for entry in ({"set": "development"}, {"set": "locked"})
    }
    if mapping_ids["development"] != set(development_ids) or mapping_ids[
        "locked"
    ] != set(locked_ids):
        raise ValidationSetError("case mapping membership differs from released cases")
    outputs = {
        **{row["case_id"]: row["output_text"] for row in development},
        **{row["case_id"]: row["output_text"] for row in final_labels},
    }
    records = {
        **{row["case_id"]: row for row in development},
        **{row["case_id"]: row for row in final_labels},
    }
    for entry in mapping["entries"]:
        case_id = entry["case_id"]
        output_text = outputs[case_id]
        if entry["output_sha256"] != sha256_bytes(output_text.encode("utf-8")):
            raise ValidationSetError("case mapping output hash mismatch")
        if entry["stratum"] != records[case_id]["stratum"]:
            raise ValidationSetError("case mapping stratum mismatch")
        if entry["set"] == "locked" and entry["template_family_id"] != records[
            case_id
        ]["template_family_id"]:
            raise ValidationSetError("case mapping template-family mismatch")
        expected_id = derive_case_id(
            mapping["id_salts"][entry["set"]], "numeric", output_text
        )
        if case_id != expected_id:
            raise ValidationSetError("case mapping opaque ID derivation mismatch")
    candidates = {
        entry["candidate_id"]: entry for entry in mapping["entries"]
    }
    if len(candidates) != len(mapping["entries"]):
        raise ValidationSetError("case mapping candidate IDs must be unique")

    visibility = parse_jsonl_strict(
        files["manifests/visibility_ledger.jsonl"],
        "manifests/visibility_ledger.jsonl",
    )
    validate_visibility_ledger(
        visibility,
        curator_pool_seals=mapping["curator_pool_seals"],
        curator_c_id=mapping["curator_c_id"],
        custodian_id=mapping["custodian_id"],
        review_seals=review_seals,
    )
    overlap = parse_json_strict(
        files["manifests/overlap_report.json"], "manifests/overlap_report.json"
    )
    _validate_overlap_release_report(overlap)
    for finding in overlap["near_duplicates"]:
        for side in ("left", "right"):
            candidate = candidates.get(finding[f"{side}_id"])
            if candidate is None or candidate["set"] != finding[f"{side}_set"]:
                raise ValidationSetError(
                    "overlap near-duplicate membership differs from case mapping"
                )
    mapping_by_case = {
        entry["case_id"]: entry for entry in mapping["entries"]
    }

    def overlap_projection(record: Mapping[str, Any]) -> dict[str, Any]:
        projected = dict(record)
        case_id = projected.pop("case_id")
        entry = mapping_by_case[case_id]
        projected["candidate_id"] = entry["candidate_id"]
        projected["template_family_id"] = entry["template_family_id"]
        return projected

    overlap_development = [
        overlap_projection(record) for record in development
    ]
    overlap_locked = [overlap_projection(record) for record in final_labels]
    recomputed_hard = detect_fixture_overlaps(
        overlap_development,
        overlap_locked,
        historical_fingerprints=checked_historical_fingerprints,
    )
    for field in (
        "exact_duplicates",
        "normalized_duplicates",
        "historical_exact_overlaps",
        "historical_normalized_overlaps",
        "cross_set_template_family_overlaps",
        "hard_failure_count",
    ):
        if overlap[field] != recomputed_hard[field]:
            raise ValidationSetError(
                f"overlap report {field} differs from released records"
            )
    recomputed_near = near_duplicate_report(
        overlap_development, overlap_locked
    )
    if overlap["near_duplicates"] != recomputed_near:
        raise ValidationSetError(
            "overlap report near_duplicates differs from released records"
        )
    validate_near_duplicate_dispositions(
        recomputed_near, overlap["near_duplicate_dispositions"]
    )
    report = parse_json_strict(
        files["reports/validation_set_report.json"],
        "reports/validation_set_report.json",
    )
    stage1_ids = stage1_disagreement_ids(
        reviewer_a_stage1, reviewer_b_stage1
    )
    stage2_ids = stage2_disagreement_ids(
        reviewer_a_stage2, reviewer_b_stage2
    )
    agreement = compute_reviewer_agreement(
        reviewer_a_stage1,
        reviewer_b_stage1,
        stage2_a=reviewer_a_stage2,
        stage2_b=reviewer_b_stage2,
        arbitration_ids=stage1_ids,
    )
    _validate_validation_report(
        report,
        expected_agreement=agreement,
        expected_stage1_ids=stage1_ids,
        expected_stage2_ids=stage2_ids,
    )
    markdown = files["reports/validation_set_report.md"]
    if markdown != render_validation_report_markdown(report):
        raise ValidationSetError(
            "validation Markdown report is not the deterministic JSON rendering"
        )

    composition = validate_dataset_composition(development, final_labels)
    visibility_hash = sha256_bytes(files["manifests/visibility_ledger.jsonl"])
    protocol_hash = protocol_bundle_sha256(project_root)
    gates_hash = acceptance_gates_sha256(project_root)
    all_ids = sorted([*development_ids, *locked_ids])
    expected_counts = {
        "development": {"cases": 60},
        "locked-inputs": {"cases": 120},
        "locked-labels": {
            "cases": 120,
            "reviewer_a_stage1": 120,
            "reviewer_b_stage1": 120,
            "arbitration_stage1": len(arbitration_stage1),
            "stage1_consensus": 120,
            "stage2_reference_packet": 120,
            "reviewer_a_stage2": 120,
            "reviewer_b_stage2": 120,
            "arbitration_stage2": len(arbitration_stage2),
            "unresolved": 0,
        },
        "reports": {"json_reports": 1, "markdown_reports": 1},
        "manifests": {
            "development_cases": 60,
            "locked_cases": 120,
            "registered_artifacts": len(expected_relative),
        },
    }
    expected_schemas = {
        "development": {"development_cases": DEVELOPMENT_SCHEMA_VERSION},
        "locked-inputs": {"locked_inputs": LOCKED_INPUT_SCHEMA_VERSION},
        "locked-labels": {
            "reviewer_stage1": STAGE1_REVIEW_SCHEMA_VERSION,
            "arbitration_stage1": STAGE1_ARBITRATION_SCHEMA_VERSION,
            "stage1_consensus": STAGE1_CONSENSUS_SCHEMA_VERSION,
            "stage2_reference_packet": STAGE2_REFERENCE_PACKET_SCHEMA_VERSION,
            "reviewer_stage2": STAGE2_REVIEW_SCHEMA_VERSION,
            "arbitration_stage2": STAGE2_ARBITRATION_SCHEMA_VERSION,
            "final_labels": FINAL_LABEL_SCHEMA_VERSION,
            "review_seal": REVIEW_SEAL_SCHEMA_VERSION,
        },
        "reports": {"validation_set_report": VALIDATION_REPORT_SCHEMA_VERSION},
        "manifests": {
            "case_mapping": MAPPING_SCHEMA_VERSION,
            "visibility_ledger": VISIBILITY_LEDGER_SCHEMA_VERSION,
            "overlap_report": "phase1-parser-v2-overlap-report/v1",
        },
    }
    expected_ids = {
        "development": development_ids,
        "locked-inputs": locked_ids,
        "locked-labels": locked_ids,
        "reports": [],
        "manifests": all_ids,
    }
    expected_features = {
        "development": composition["feature_counts"]["development"],
        "locked-inputs": composition["feature_counts"]["locked"],
        "locked-labels": composition["feature_counts"]["locked"],
        "reports": {},
        "manifests": composition["feature_counts"],
    }
    expected_arbitration = {
        leaf: (
            {
                "stage1": len(arbitration_stage1),
                "stage2": len(arbitration_stage2),
                "unresolved": 0,
            }
            if leaf in {"locked-labels", "manifests"}
            else {"stage1": 0, "stage2": 0, "unresolved": 0}
        )
        for leaf in REGISTERED_LEAF_MEMBERS
    }
    manifest_sources = {
        tuple(manifest["source_prefixes"]) for manifest in manifests.values()
    }
    if len(manifest_sources) != 1:
        raise ValidationSetError("release manifests disagree on source prefixes")
    if source_prefixes is not None:
        registered_sources, _ = validate_prefix_isolation(source_prefixes, [parent])
        if next(iter(manifest_sources)) != registered_sources:
            raise ValidationSetError(
                "release manifest source prefixes do not match persistence inputs"
            )
    for leaf, names in REGISTERED_LEAF_MEMBERS.items():
        manifest = manifests[leaf]
        if (
            manifest["manifest_kind"] != leaf
            or manifest["parent_prefix"] != parent
            or manifest["protocol_bundle_sha256"] != protocol_hash
            or manifest["acceptance_gates_sha256"] != gates_hash
            or manifest["ordered_case_ids"] != expected_ids[leaf]
            or manifest["counts"] != expected_counts[leaf]
            or manifest["schemas"] != expected_schemas[leaf]
            or manifest["arbitration"] != expected_arbitration[leaf]
            or manifest["feature_counts"] != expected_features[leaf]
            or manifest["visibility_ledger_sha256"] != visibility_hash
            or manifest["private_nonce"] != reservations[leaf]["private_nonce"]
            or manifest["reservation_sha256"]
            != sha256_bytes(files[f"{leaf}/{names[0]}"])
        ):
            raise ValidationSetError(f"{leaf} manifest binding mismatch")
        if leaf == "manifests":
            paths = expected_relative[:-1]
        else:
            paths = [f"{leaf}/{name}" for name in names[:-1]]
        if manifest["files"] != _manifest_metadata(paths, files):
            raise ValidationSetError(f"{leaf} manifest payload membership/hash mismatch")
        expected_seals = review_seals if leaf in {"locked-labels", "manifests"} else []
        if manifest["review_seals"] != expected_seals:
            raise ValidationSetError(f"{leaf} manifest review-seal binding mismatch")
    return {
        "artifact_count": len(expected_relative),
        "development_count": 60,
        "locked_count": 120,
        "unresolved_count": 0,
        "review_seal_count": len(review_seals),
    }


_AUTHORIZATION_LOCK_FIELDS = frozenset(
    {
        "schema_version",
        "holdout_id",
        "registered_parent_prefix",
        "locked_manifest_sha256",
        "authorization_id",
        "sealed_receipt_sha256",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "implementation_manifest_sha256",
        "execution_id",
        "actor",
        "visibility_sha256",
        "created_utc",
    }
)
_IMPLEMENTATION_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "implementation_commit",
        "image_digest",
        "config_sha256",
    }
)


def derive_holdout_id(
    registered_parent_prefix: str,
    locked_manifest_sha256: str,
) -> str:
    """Derive one stable holdout identity independent of receipt metadata."""
    parent = validate_registered_parent_prefix(registered_parent_prefix)
    locked_hash = _require_sha256(
        locked_manifest_sha256, "locked_manifest_sha256"
    )
    return sha256_bytes(
        canonical_json_bytes(
            {
                "domain": "phase1-parser-v2-holdout-id/v1",
                "locked_manifest_sha256": locked_hash,
                "registered_parent_prefix": parent,
            }
        )
    )


def validate_implementation_manifest(data: bytes) -> dict[str, str]:
    """Validate the canonical immutable implementation binding."""
    record = parse_json_strict(data, "implementation manifest")
    _require_exact_fields(
        record, _IMPLEMENTATION_MANIFEST_FIELDS, "implementation manifest"
    )
    if record["schema_version"] != IMPLEMENTATION_MANIFEST_SCHEMA_VERSION:
        raise ValidationSetError("implementation manifest schema_version is invalid")
    return {
        "implementation_commit": _require_commit(
            record["implementation_commit"],
            "implementation manifest implementation_commit",
        ),
        "image_digest": _require_image_digest(
            record["image_digest"], "implementation manifest image_digest"
        ),
        "config_sha256": _require_sha256(
            record["config_sha256"], "implementation manifest config_sha256"
        ),
    }


def validate_authorization_lock(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the fixed, overwrite-false authorization-lock payload."""
    _require_exact_fields(record, _AUTHORIZATION_LOCK_FIELDS, "authorization lock")
    if record["schema_version"] != AUTHORIZATION_LOCK_SCHEMA_VERSION:
        raise ValidationSetError("authorization lock schema_version is invalid")
    holdout_id = _require_sha256(record["holdout_id"], "authorization lock holdout_id")
    parent = validate_registered_parent_prefix(
        record["registered_parent_prefix"]
    )
    locked_manifest_sha256 = _require_sha256(
        record["locked_manifest_sha256"],
        "authorization lock locked_manifest_sha256",
    )
    sealed_hash = _require_sha256(
        record["sealed_receipt_sha256"],
        "authorization lock sealed_receipt_sha256",
    )
    if holdout_id != derive_holdout_id(parent, locked_manifest_sha256):
        raise ValidationSetError(
            "authorization lock holdout_id differs from the registered holdout"
        )
    authorization_id = _require_string(
        record["authorization_id"], "authorization lock authorization_id"
    )
    implementation_commit = _require_commit(
        record["implementation_commit"],
        "authorization lock implementation_commit",
    )
    image_digest = _require_image_digest(
        record["image_digest"], "authorization lock image_digest"
    )
    config_sha256 = _require_sha256(
        record["config_sha256"], "authorization lock config_sha256"
    )
    implementation_manifest_sha256 = _require_sha256(
        record["implementation_manifest_sha256"],
        "authorization lock implementation_manifest_sha256",
    )
    execution_id = _require_string(
        record["execution_id"], "authorization lock execution_id"
    )
    actor = _require_string(record["actor"], "authorization lock actor")
    visibility_sha256 = _require_sha256(
        record["visibility_sha256"], "authorization lock visibility_sha256"
    )
    created_utc = _require_utc_timestamp(
        record["created_utc"], "authorization lock created_utc"
    )
    return {
        "holdout_id": holdout_id,
        "registered_parent_prefix": parent,
        "locked_manifest_sha256": locked_manifest_sha256,
        "authorization_id": authorization_id,
        "implementation_commit": implementation_commit,
        "image_digest": image_digest,
        "config_sha256": config_sha256,
        "implementation_manifest_sha256": implementation_manifest_sha256,
        "execution_id": execution_id,
        "actor": actor,
        "visibility_sha256": visibility_sha256,
        "created_utc": created_utc,
    }


def build_authorization_lock(
    sealed_receipt: Mapping[str, Any],
    implementation_receipt: Mapping[str, Any],
    implementation_manifest_bytes: bytes,
) -> dict[str, Any]:
    """Build the single authorization payload for one sealed holdout."""
    sealed = validate_state_receipt(sealed_receipt, name="sealed receipt")
    implementation = validate_state_receipt(
        implementation_receipt, name="implementation receipt"
    )
    sealed_hash = state_receipt_sha256(sealed_receipt)
    if sealed["state"] != "SEALED" or implementation["state"] != "IMPLEMENTATION_FROZEN":
        raise ValidationSetError(
            "authorization lock requires SEALED -> IMPLEMENTATION_FROZEN receipts"
        )
    if (
        implementation_receipt["previous_state"] != "SEALED"
        or implementation_receipt["previous_receipt_sha256"] != sealed_hash
        or implementation["authorization_id"] != sealed["authorization_id"]
    ):
        raise ValidationSetError(
            "authorization lock receipts do not form the registered transition"
        )
    manifest = validate_implementation_manifest(implementation_manifest_bytes)
    manifest_sha256 = sha256_bytes(implementation_manifest_bytes)
    if (
        manifest_sha256
        != implementation_receipt["artifact_manifest_hashes"][
            "implementation_manifest"
        ]
        or manifest["implementation_commit"]
        != implementation_receipt["implementation_commit"]
        or manifest["image_digest"] != implementation_receipt["image_digest"]
        or manifest["config_sha256"] != implementation_receipt["config_sha256"]
    ):
        raise ValidationSetError(
            "implementation receipt differs from the canonical implementation manifest"
        )
    parent = sealed_receipt["registered_parent_prefix"]
    locked_manifest_sha256 = sealed_receipt["artifact_manifest_hashes"][
        "locked_manifest"
    ]
    lock = {
        "schema_version": AUTHORIZATION_LOCK_SCHEMA_VERSION,
        "holdout_id": derive_holdout_id(parent, locked_manifest_sha256),
        "registered_parent_prefix": parent,
        "locked_manifest_sha256": locked_manifest_sha256,
        "authorization_id": implementation["authorization_id"],
        "sealed_receipt_sha256": sealed_hash,
        "implementation_commit": implementation_receipt["implementation_commit"],
        "image_digest": implementation_receipt["image_digest"],
        "config_sha256": implementation_receipt["config_sha256"],
        "implementation_manifest_sha256": manifest_sha256,
        "execution_id": implementation["execution_id"],
        "actor": implementation["actor"],
        "visibility_sha256": sha256_bytes(
            canonical_json_bytes(implementation_receipt["visibility"])
        ),
        "created_utc": implementation_receipt["timestamp_utc"],
    }
    validate_authorization_lock(lock)
    return lock


def authorization_lock_sha256(record: Mapping[str, Any]) -> str:
    validate_authorization_lock(record)
    return sha256_bytes(canonical_json_bytes(dict(record)))


def authorization_lock_blob_name(record: Mapping[str, Any]) -> str:
    checked = validate_authorization_lock(record)
    return f"{AUTHORIZATION_LOCK_BLOB_PREFIX}/{checked['holdout_id']}.json"


_STATE_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "state",
        "previous_state",
        "previous_receipt_sha256",
        "timestamp_utc",
        "execution_id",
        "actor",
        "visibility",
        "registered_parent_prefix",
        "protocol_commit",
        "protocol_bundle_sha256",
        "acceptance_gates_sha256",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "authorization_lock_sha256",
        "artifact_manifest_hashes",
        "retry_kind",
        "outcome",
        "holdout_spent",
        "holdout_retired",
    }
)

STATE_AUTHORIZED_ARTIFACT_BINDINGS = {
    "DRAFT_PROTOCOL": frozenset(),
    "PROTOCOL_FROZEN": frozenset(
        {"protocol_manifest", "acceptance_gates"}
    ),
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


def validate_state_receipt(
    receipt: Mapping[str, Any], *, name: str = "state receipt"
) -> dict[str, Any]:
    """Validate one canonical hash-chain state receipt."""
    _require_exact_fields(receipt, _STATE_RECEIPT_FIELDS, name)
    if receipt["schema_version"] != STATE_RECEIPT_SCHEMA_VERSION:
        raise ValidationSetError(f"{name}.schema_version is invalid")
    authorization_id = _require_string(
        receipt["authorization_id"], f"{name}.authorization_id"
    )
    state = _require_enum(receipt["state"], HOLDOUT_STATES, f"{name}.state")
    previous_state = receipt["previous_state"]
    previous_hash = receipt["previous_receipt_sha256"]
    if state == "DRAFT_PROTOCOL":
        if previous_state is not None or previous_hash is not None:
            raise ValidationSetError("initial state receipt cannot have a predecessor")
    else:
        _require_enum(previous_state, HOLDOUT_STATES, f"{name}.previous_state")
        _require_sha256(previous_hash, f"{name}.previous_receipt_sha256")
    timestamp = _require_utc_timestamp(
        receipt["timestamp_utc"], f"{name}.timestamp_utc"
    )
    execution_id = _require_string(receipt["execution_id"], f"{name}.execution_id")
    actor = _require_string(receipt["actor"], f"{name}.actor")
    if not isinstance(receipt["visibility"], list):
        raise ValidationSetError(f"{name}.visibility must be a list")
    visibility = [
        _require_string(item, f"{name}.visibility[{index}]")
        for index, item in enumerate(receipt["visibility"])
    ]
    if visibility != sorted(set(visibility)):
        raise ValidationSetError(f"{name}.visibility must be unique and sorted")
    registered_parent_prefix = validate_registered_parent_prefix(
        receipt["registered_parent_prefix"]
    )
    if _require_commit(receipt["protocol_commit"], f"{name}.protocol_commit") != FROZEN_PROTOCOL_COMMIT:
        raise ValidationSetError(f"{name}.protocol_commit is not frozen")
    if (
        _require_sha256(
            receipt["protocol_bundle_sha256"], f"{name}.protocol_bundle_sha256"
        )
        != FROZEN_PROTOCOL_BUNDLE_SHA256
    ):
        raise ValidationSetError(f"{name}.protocol_bundle_sha256 is not final")
    if (
        _require_sha256(
            receipt["acceptance_gates_sha256"],
            f"{name}.acceptance_gates_sha256",
        )
        != FROZEN_ACCEPTANCE_GATE_SHA256
    ):
        raise ValidationSetError(f"{name}.acceptance_gates_sha256 is not final")
    implementation = receipt["implementation_commit"]
    image = receipt["image_digest"]
    config = receipt["config_sha256"]
    authorization_lock = receipt["authorization_lock_sha256"]
    state_index = HOLDOUT_STATES.index(state)
    implementation_index = HOLDOUT_STATES.index("IMPLEMENTATION_FROZEN")
    if state_index >= implementation_index:
        _require_commit(implementation, f"{name}.implementation_commit")
        _require_image_digest(image, f"{name}.image_digest")
        _require_sha256(config, f"{name}.config_sha256")
        _require_sha256(
            authorization_lock, f"{name}.authorization_lock_sha256"
        )
    elif any(
        item is not None
        for item in (implementation, image, config, authorization_lock)
    ):
        raise ValidationSetError(
            f"{name} cannot bind implementation or authorization lock "
            "before IMPLEMENTATION_FROZEN"
        )
    manifests = receipt["artifact_manifest_hashes"]
    if not isinstance(manifests, Mapping):
        raise ValidationSetError(f"{name}.artifact_manifest_hashes must be an object")
    for key, digest in manifests.items():
        _require_string(key, f"{name}.artifact manifest key")
        _require_sha256(digest, f"{name}.artifact_manifest_hashes.{key}")
    allowed_keys: set[str] = set()
    for registered_state in HOLDOUT_STATES[: state_index + 1]:
        allowed_keys.update(STATE_AUTHORIZED_ARTIFACT_BINDINGS[registered_state])
    if set(manifests) != allowed_keys:
        raise ValidationSetError(
            f"{name} does not contain the exact cumulative bindings for {state}"
        )
    retry = _require_enum(
        receipt["retry_kind"],
        (
            "none",
            "infrastructure_pre_input",
            "scorer_infrastructure",
            "verification_only",
        ),
        f"{name}.retry_kind",
    )
    outcome = receipt["outcome"]
    if state == "CLOSED":
        _require_enum(outcome, ("PASS", "FAIL", "INVALID"), f"{name}.outcome")
    elif outcome is not None:
        raise ValidationSetError(f"{name}.outcome is allowed only at CLOSED")
    spent = _require_bool(receipt["holdout_spent"], f"{name}.holdout_spent")
    retired = _require_bool(receipt["holdout_retired"], f"{name}.holdout_retired")
    should_be_spent = state_index >= HOLDOUT_STATES.index("INPUTS_READ")
    if spent != should_be_spent:
        raise ValidationSetError(f"{name}.holdout_spent disagrees with state")
    if retired != (state == "CLOSED"):
        raise ValidationSetError(f"{name}.holdout_retired disagrees with state")
    return {
        "authorization_id": authorization_id,
        "state": state,
        "previous_state": previous_state,
        "timestamp_utc": timestamp,
        "execution_id": execution_id,
        "actor": actor,
        "registered_parent_prefix": registered_parent_prefix,
        "retry_kind": retry,
        "authorization_lock_sha256": authorization_lock,
        "holdout_spent": spent,
        "holdout_retired": retired,
    }


def state_receipt_sha256(receipt: Mapping[str, Any]) -> str:
    validate_state_receipt(receipt)
    return sha256_bytes(canonical_json_bytes(dict(receipt)))


def validate_state_transition(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    history: Sequence[Mapping[str, Any]] = (),
    authorization_lock: Mapping[str, Any] | None = None,
    implementation_manifest_bytes: bytes | None = None,
) -> None:
    """Enforce the one-shot transition and narrowly registered retry rules."""
    before = validate_state_receipt(previous, name="previous state receipt")
    after = validate_state_receipt(current, name="current state receipt")
    if before["holdout_retired"]:
        raise ValidationSetError("retired holdout cannot transition or be reused")
    if current["previous_state"] != before["state"]:
        raise ValidationSetError("state receipt previous_state mismatch")
    if current["previous_receipt_sha256"] != state_receipt_sha256(previous):
        raise ValidationSetError("state receipt hash-chain mismatch")
    if current["authorization_id"] != previous["authorization_id"]:
        raise ValidationSetError("authorization_id cannot change in a state chain")
    for field in (
        "registered_parent_prefix",
        "protocol_commit",
        "protocol_bundle_sha256",
        "acceptance_gates_sha256",
    ):
        if current[field] != previous[field]:
            raise ValidationSetError(f"state binding changed: {field}")
    if before["state"] in EVALUATION_STATES:
        for field in ("implementation_commit", "image_digest", "config_sha256"):
            if current[field] != previous[field]:
                raise ValidationSetError(f"frozen implementation binding changed: {field}")
    previous_manifests = previous["artifact_manifest_hashes"]
    current_manifests = current["artifact_manifest_hashes"]
    for key, digest in previous_manifests.items():
        if current_manifests.get(key) != digest:
            raise ValidationSetError(
                "artifact_manifest_hashes are append-only and immutable"
            )
    before_index = HOLDOUT_STATES.index(before["state"])
    after_index = HOLDOUT_STATES.index(after["state"])
    implementation_index = HOLDOUT_STATES.index("IMPLEMENTATION_FROZEN")
    if before_index >= implementation_index and (
        current["authorization_lock_sha256"]
        != previous["authorization_lock_sha256"]
    ):
        raise ValidationSetError("authorization lock binding changed")
    if after_index >= implementation_index:
        if authorization_lock is None or implementation_manifest_bytes is None:
            raise ValidationSetError(
                "implementation/evaluation transition requires the authorization "
                "lock and implementation manifest"
            )
        checked_lock = validate_authorization_lock(authorization_lock)
        checked_manifest = validate_implementation_manifest(
            implementation_manifest_bytes
        )
        if (
            current["authorization_lock_sha256"]
            != authorization_lock_sha256(authorization_lock)
            or checked_lock["registered_parent_prefix"]
            != current["registered_parent_prefix"]
            or checked_lock["locked_manifest_sha256"]
            != current_manifests["locked_manifest"]
            or checked_lock["authorization_id"] != after["authorization_id"]
            or checked_lock["implementation_commit"]
            != current["implementation_commit"]
            or checked_lock["image_digest"] != current["image_digest"]
            or checked_lock["config_sha256"] != current["config_sha256"]
            or checked_lock["implementation_manifest_sha256"]
            != sha256_bytes(implementation_manifest_bytes)
            or current_manifests["implementation_manifest"]
            != sha256_bytes(implementation_manifest_bytes)
            or checked_manifest["implementation_commit"]
            != current["implementation_commit"]
            or checked_manifest["image_digest"] != current["image_digest"]
            or checked_manifest["config_sha256"] != current["config_sha256"]
        ):
            raise ValidationSetError(
                "state receipt differs from the fixed authorization lock"
            )
        if before["state"] == "SEALED" and after["state"] == "IMPLEMENTATION_FROZEN":
            if dict(authorization_lock) != build_authorization_lock(
                previous, current, implementation_manifest_bytes
            ):
                raise ValidationSetError(
                    "IMPLEMENTATION_FROZEN receipt differs from its authorization lock"
                )
    retry_kind = after["retry_kind"]
    if retry_kind == "none":
        if after_index != before_index + 1:
            raise ValidationSetError("normal state transitions must advance exactly once")
        additions = set(current_manifests) - set(previous_manifests)
        if additions != set(
            STATE_AUTHORIZED_ARTIFACT_BINDINGS[after["state"]]
        ):
            raise ValidationSetError(
                f"artifact additions are not exact for {after['state']}"
            )
    else:
        if after_index != before_index:
            raise ValidationSetError("retry receipts must remain in the same state")
        if current["execution_id"] == previous["execution_id"]:
            raise ValidationSetError(
                "infrastructure retry must use a new execution ID"
            )
        same_kind_count = sum(
            item.get("retry_kind") == retry_kind for item in history
        )
        if same_kind_count:
            raise ValidationSetError("registered infrastructure retry already consumed")
        if retry_kind == "infrastructure_pre_input":
            if before_index >= HOLDOUT_STATES.index("INPUTS_READ"):
                raise ValidationSetError("pre-input retry is no longer allowed")
            if current_manifests != previous_manifests:
                raise ValidationSetError(
                    "pre-input retry must reuse byte-identical artifact bindings"
                )
        elif retry_kind == "scorer_infrastructure":
            if before["state"] != "PREDICTIONS_VERIFIED":
                raise ValidationSetError(
                    "scorer retry is allowed only before labels are read"
                )
            if current_manifests != previous_manifests:
                raise ValidationSetError(
                    "scorer retry must reuse byte-identical predictions"
                )
        elif retry_kind == "verification_only":
            if before_index < HOLDOUT_STATES.index("LABELS_READ"):
                raise ValidationSetError(
                    "verification-only retry requires labels already read"
                )
            if current_manifests != previous_manifests:
                raise ValidationSetError(
                    "verification-only retry cannot change written bytes"
                )


def validate_state_receipt_chain(
    receipts: Sequence[Mapping[str, Any]],
    *,
    authorization_lock: Mapping[str, Any] | None = None,
    implementation_manifest_bytes: bytes | None = None,
) -> dict[str, Any]:
    if not receipts:
        raise ValidationSetError("state receipt chain must not be empty")
    validate_state_receipt(receipts[0], name="state receipts[0]")
    if receipts[0]["state"] != "DRAFT_PROTOCOL":
        raise ValidationSetError("state receipt chain must start at DRAFT_PROTOCOL")
    seen_hashes: set[str] = set()
    for index, receipt in enumerate(receipts):
        digest = state_receipt_sha256(receipt)
        if digest in seen_hashes:
            raise ValidationSetError("state receipt chain repeats exact bytes")
        seen_hashes.add(digest)
        if index:
            validate_state_transition(
                receipts[index - 1],
                receipt,
                history=receipts[:index],
                authorization_lock=authorization_lock,
                implementation_manifest_bytes=implementation_manifest_bytes,
            )
    final = validate_state_receipt(receipts[-1])
    return {
        "receipt_count": len(receipts),
        "state": final["state"],
        "holdout_spent": final["holdout_spent"],
        "holdout_retired": final["holdout_retired"],
        "chain_sha256": state_receipt_sha256(receipts[-1]),
    }


def validate_state_receipt_graph(
    receipts: Sequence[Mapping[str, Any]],
    *,
    authorization_lock: Mapping[str, Any] | None = None,
    implementation_manifest_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Reject missing parents, disconnected receipts, and divergent child branches."""
    if not receipts:
        raise ValidationSetError("state receipt graph must not be empty")
    by_hash: dict[str, Mapping[str, Any]] = {}
    children: dict[str, list[str]] = defaultdict(list)
    roots: list[str] = []
    for index, receipt in enumerate(receipts):
        validate_state_receipt(receipt, name=f"state receipt graph[{index}]")
        digest = state_receipt_sha256(receipt)
        if digest in by_hash:
            raise ValidationSetError("state receipt graph repeats exact bytes")
        by_hash[digest] = receipt
        predecessor = receipt["previous_receipt_sha256"]
        if predecessor is None:
            roots.append(digest)
        else:
            children[predecessor].append(digest)
    if len(roots) != 1:
        raise ValidationSetError("state receipt graph must have exactly one root")
    if any(parent not in by_hash for parent in children):
        raise ValidationSetError("state receipt graph has a missing predecessor")
    if any(len(items) != 1 for items in children.values()):
        raise ValidationSetError("state receipt graph contains a divergent branch")
    ordered: list[Mapping[str, Any]] = []
    current = roots[0]
    while True:
        ordered.append(by_hash[current])
        next_items = children.get(current, [])
        if not next_items:
            break
        current = next_items[0]
    if len(ordered) != len(receipts):
        raise ValidationSetError("state receipt graph is disconnected or cyclic")
    return validate_state_receipt_chain(
        ordered,
        authorization_lock=authorization_lock,
        implementation_manifest_bytes=implementation_manifest_bytes,
    )


def assert_holdout_available(
    receipts: Sequence[Mapping[str, Any]],
    *,
    for_new_evaluation: bool = True,
    authorization_lock: Mapping[str, Any] | None = None,
    implementation_manifest_bytes: bytes | None = None,
) -> None:
    state = validate_state_receipt_chain(
        receipts,
        authorization_lock=authorization_lock,
        implementation_manifest_bytes=implementation_manifest_bytes,
    )
    if state["holdout_retired"]:
        raise ValidationSetError("retired holdout cannot be reused")
    if for_new_evaluation and state["holdout_spent"]:
        raise ValidationSetError("holdout was spent by an authorized input exposure")
