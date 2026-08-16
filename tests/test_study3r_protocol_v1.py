"""Study 3R protocol candidate v1: semantic and coordinated-mutation tests.

Authority: ``studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md``

This module is the independent validator of the Study 3R bundle. It is written
from scratch for Study 3R and shares no structure with any earlier Study 3 test.

It does three things that byte-reproduction alone cannot:

1. it validates every decision-bearing artifact against a restrictive schema;
2. it re-states every registered identity, revision, surface, threshold,
   sample size, boundary and transition **independently of the generators**,
   so a generator edit that changes any of them is rejected here; and
3. it runs coordinated generator-mutation tests: each mutation edits a staged
   copy of a generator, rebuilds the whole bundle, and requires
   :func:`validate_bundle` to reject the rebuilt bundle. Required survivors
   are zero.

Nothing in this module loads a model, runs a forward pass, scores a logit,
generates a token, reaches the network, realizes a scientific bank or draws a
seed.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STUDY3R = ROOT / "studies" / "study3r"
PROTOCOL_DIR = STUDY3R / "protocol"
ANALYSIS_DIR = STUDY3R / "analysis"
ACQUISITION_DIR = STUDY3R / "acquisition"
TASKS_DIR = STUDY3R / "tasks"

AUTHORITY_RELATIVE = \
    "studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md"

# ---------------------------------------------------------------------------
# The complete authored path set. Nothing outside it may be written by the
# Study 3R protocol-authoring session.
# ---------------------------------------------------------------------------

AUTHORED_PATHS = (
    ".gitattributes",
    "studies/study3r/AUTHORING_DISCLOSURE.md",
    "studies/study3r/README.md",
    "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.json",
    "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.schema.json",
    "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.json",
    "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.schema.json",
    "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.json",
    "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.schema.json",
    "studies/study3r/analysis/study3r_atomic_cell_census_v1.json",
    "studies/study3r/analysis/study3r_design_statistics.py",
    "studies/study3r/analysis/study3r_design_statistics_tables.json",
    "studies/study3r/analysis/study3r_independent_recalculation.py",
    "studies/study3r/analysis/study3r_independent_recalculation_tables.json",
    "studies/study3r/analysis/study3r_manifest.py",
    "studies/study3r/analysis/study3r_protocol_build.py",
    "studies/study3r/analysis/study3r_tokenizer_probe.py",
    "studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md",
    "studies/study3r/protocol/study3r_protocol_current.json",
    "studies/study3r/protocol/study3r_protocol_current.schema.json",
    "studies/study3r/protocol/study3r_protocol_v1.json",
    "studies/study3r/protocol/study3r_protocol_v1.md",
    "studies/study3r/protocol/study3r_protocol_v1.schema.json",
    "studies/study3r/protocol/study3r_rendering_registry_v1.json",
    "studies/study3r/protocol/study3r_rendering_registry_v1.schema.json",
    "studies/study3r/protocol/study3r_state_machine_v1.json",
    "studies/study3r/protocol/study3r_state_machine_v1.schema.json",
    "studies/study3r/study3r_authoring_disclosure_v1.json",
    "studies/study3r/study3r_authoring_disclosure_v1.schema.json",
    "studies/study3r/study3r_candidate_manifest_v1.json",
    "studies/study3r/study3r_candidate_manifest_v1.schema.json",
    "studies/study3r/tasks/study3r_task_generators_v1.py",
    "tests/test_study3r_operator_governance.py",
    "tests/test_study3r_protocol_v1.py",
)

#: The governance head this authoring session started from.
STARTING_COMMIT = "cd9c0af3118ca2f254bd0bbaa8eb2ee4dad6d1ed"
STARTING_TREE = "fc303a001bbfea60149e9f425f64230c022b6d91"

# ---------------------------------------------------------------------------
# Independently re-stated registered identities
# ---------------------------------------------------------------------------

EXPECTED_TARGET = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
EXPECTED_LADDER = (
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
)
EXPECTED_LADDER_LENGTH = 3
EXPECTED_ROLES = ("RT", "RP_B1", "RP_B2", "RP_B3")
EXPECTED_REVISIONS = {
    "RT": "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562",
    "RP_B1": "916b56a44061fd5cd7d6a8fb632557ed4f724f60",
    "RP_B2": "1df8507178afcc1bef68cd8c393f61a886323761",
    "RP_B3": "711ad2ea6aa40cfca18895e8aca02ab92df1a746",
}
EXPECTED_LABELS = ("A", "B", "C", "D")
EXPECTED_ARMS = ("W1_RAW_DIRECT", "W2_ROLE_CANONICAL")
EXPECTED_ROLE_CANONICAL_MESSAGE_ROLE = "user"
EXPECTED_COT_ROUTE = "C1_CANONICAL_GENERATED_COT"
EXPECTED_E0_ID = "E0_zero_generated_reasoning_token_expressed_competence"
EXPECTED_D0_ID = "D0_single_forward_decodability"
EXPECTED_COT_ID = "COT_generated_reasoning_ceiling"
EXPECTED_COT_K = 1
EXPECTED_COT_PARSER = "P1_FINAL_ANSWER_LAST_LINE"
EXPECTED_COT_MAX_NEW_TOKENS = 4096
EXPECTED_TERMINATION_MARGIN = 1
EXPECTED_D0_POSITION_OFFSET = 0
EXPECTED_ANSWER_CUE = "Answer:\n"
EXPECTED_AUTHORED_STATE = \
    "STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW"
EXPECTED_AUTHORITATIVE_PROTOCOL = \
    "studies/study3r/protocol/study3r_protocol_v1.json"
EXPECTED_CURRENT_POINTER = \
    "studies/study3r/protocol/study3r_protocol_current.json"
EXPECTED_MANIFEST_GENERATOR = "studies/study3r/analysis/study3r_manifest.py"

EXPECTED_M_MAX = 58
EXPECTED_ALPHA_GLOBAL = "1/20"
EXPECTED_ALPHA_PER_CELL = "1/1160"
EXPECTED_POWER_TARGET = "9/10"
EXPECTED_CHANCE_LEVEL = "1/4"
EXPECTED_MULTIPLICITY_FAMILY = "F_GLOBAL_STUDY3R"
EXPECTED_RPB_DECISION_ID = "Q0_RPB_QUALIFICATION_DECISION"

#: gate_id -> (cells, direction, floor, alternative, n, pass boundary)
EXPECTED_GATES = {
    "G01_COT_CEILING": (4, "greater_than_floor", "3/4", "9/10", 128, 111),
    "G02_CONTROL_RECOVERY": (8, "greater_than_floor", "9/10", "99/100", 110, 108),
    "G03_CONTROL_BINDING": (8, "greater_than_floor", "9/10", "99/100", 110, 108),
    "G04_CONTROL_PRIMITIVE": (8, "greater_than_floor", "9/10", "99/100", 110, 108),
    "G05_NEGATIVE_CONTROL": (8, "less_than_upper_margin", "35/100", "1/4", 416, 115),
    "G06_WRAPPER_JOINT_ADEQUACY": (8, "greater_than_floor", "1/2", "3/4", 74, 51),
    "G07_RPB_DEVELOPMENT": (6, "greater_than_floor", "1/2", "3/4", 74, 51),
    "G08_RPB_CONFIRMATION": (6, "greater_than_floor", "1/2", "3/4", 74, 51),
    "G09_RT_E0_QUALIFICATION": (2, "greater_than_floor", "1/2", "3/4", 74, 51),
}

EXPECTED_TRANSITIONS = {
    "S00_AUTHORED": {
        "execution_authorization_granted": "S01_SEALED_ENGINEERING_SHAKEDOWN",
        "execution_authorization_absent": "T00_NOT_EXECUTED",
    },
    "S01_SEALED_ENGINEERING_SHAKEDOWN": {
        "shakedown_reproduced_every_sealed_surface":
            "S02_CHECKPOINT_TOKENIZER_FUNCTIONAL_EQUIVALENCE",
        "shakedown_failed_to_reproduce_a_sealed_surface": "T01_SHAKEDOWN_FAILED",
    },
    "S02_CHECKPOINT_TOKENIZER_FUNCTIONAL_EQUIVALENCE": {
        "every_registered_tuple_verified_and_stratified":
            "S03_GENERATED_COT_CEILING",
        "a_registered_tuple_could_not_be_verified":
            "T02_TOKENIZER_EQUIVALENCE_FAILED",
    },
    "S03_GENERATED_COT_CEILING": {
        "every_checkpoint_cell_passed": "S04_COMPETENCE_CONTROLS",
        "at_least_one_checkpoint_cell_failed": "T03_COT_CEILING_FAILED",
    },
    "S04_COMPETENCE_CONTROLS": {
        "every_control_cell_passed": "S05_NEGATIVE_CONTROL",
        "at_least_one_control_cell_failed": "T04_COMPETENCE_CONTROL_FAILED",
    },
    "S05_NEGATIVE_CONTROL": {
        "every_negative_control_cell_passed": "S06_TWO_WRAPPER_JOINT_ADEQUACY",
        "at_least_one_negative_control_cell_failed":
            "T05_NEGATIVE_CONTROL_FAILED",
    },
    "S06_TWO_WRAPPER_JOINT_ADEQUACY": {
        "both_arms_cleared_the_floor_for_every_checkpoint":
            "S07_RPB_LADDER_DEVELOPMENT_AND_CONFIRMATION",
        "at_least_one_arm_failed_for_at_least_one_checkpoint":
            "T06_WRAPPER_ADEQUACY_FAILED",
    },
    "S07_RPB_LADDER_DEVELOPMENT_AND_CONFIRMATION": {
        "a_candidate_passed_development_and_confirmation_on_both_arms":
            "S08_RPB_FIRST_CONFIRMED_PASS_FREEZE",
        "the_full_registered_ladder_was_scanned_without_a_confirmed_pass":
            "T07_NO_QUALIFIED_REFERENCE",
    },
    "S08_RPB_FIRST_CONFIRMED_PASS_FREEZE": {
        "freeze_record_written": "S09_RT_E0_BEHAVIORAL_QUALIFICATION",
        "freeze_record_could_not_be_written": "T08_RPB_FREEZE_RECORD_FAILED",
    },
    "S09_RT_E0_BEHAVIORAL_QUALIFICATION": {
        "rt_cleared_the_floor_on_both_arms": "S10_D0_DIAGNOSTIC_REPORT",
        "rt_failed_at_least_one_arm": "S10_D0_DIAGNOSTIC_REPORT",
    },
    "S10_D0_DIAGNOSTIC_REPORT": {
        "diagnostic_readout_reported": "S11_TERMINAL_DISPOSITION",
        "diagnostic_readout_unavailable_and_recorded_as_such":
            "S11_TERMINAL_DISPOSITION",
    },
    "S11_TERMINAL_DISPOSITION": {
        "carried_outcome_is_rt_cleared_the_floor_on_both_arms":
            "T10_STUDY3R_COMPLETE_RT_QUALIFIED",
        "carried_outcome_is_rt_failed_at_least_one_arm": "T09_RT_NOT_QUALIFIED",
    },
}

EXPECTED_MANIFEST_CATEGORIES = {
    "atomic_cell_census", "authoring_authority", "current_pointer",
    "current_pointer_schema", "independent_recalculation_code",
    "independent_recalculation_tables", "manifest_generator",
    "manifest_schema", "protocol", "protocol_builder", "protocol_markdown",
    "protocol_schema", "rendering_registry", "rendering_registry_schema",
    "semantic_and_mutation_tests", "state_machine", "state_machine_schema",
    "statistical_code", "statistical_tables", "task_generator_specification",
    "tokenizer_acquisition_record", "tokenizer_acquisition_schema",
    "tokenizer_equivalence_record", "tokenizer_equivalence_schema",
    "tokenizer_probe", "wrapper_bytes_and_token_surfaces",
    "wrapper_bytes_and_token_surfaces_schema",
}

ZERO_OPERATION_COUNTERS = (
    "evidence_ledger_rows_written", "execution_seeds_drawn", "forward_passes",
    "generations", "gpu_or_cloud_jobs", "interfaces_selected", "logit_reads",
    "model_constructions", "prefill_operations", "remote_code_executions",
    "scientific_items_realized", "scoring_operations", "weight_files_acquired",
)

WEIGHT_SUFFIXES = (".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".h5",
                   ".msgpack", ".gguf", ".onnx", ".npz", ".pkl")


# ---------------------------------------------------------------------------
# Tokenizer-derived expectations, restated independently of the probe.
# ---------------------------------------------------------------------------

#: E0 legal answer-surface token ids, per checkpoint revision.
EXPECTED_ANSWER_TOKEN_IDS = {
    "RT": {"A": [32], "B": [33], "C": [34], "D": [35]},
    "RP_B1": {"A": [32], "B": [33], "C": [34], "D": [35]},
    "RP_B2": {"A": [32], "B": [33], "C": [34], "D": [35]},
    "RP_B3": {"A": [32], "B": [33], "C": [34], "D": [35]},
}

#: Per-checkpoint E0 generation length: longest legal surface + margin.
EXPECTED_MAX_NEW_TOKENS = {
    "RT": 2,
    "RP_B1": 2,
    "RP_B2": 2,
    "RP_B3": 2,
}

#: Context windows used by the generated-CoT resource bound.
EXPECTED_CONTEXT_WINDOWS = {
    "RT": 131072,
    "RP_B1": 131072,
    "RP_B2": 131072,
    "RP_B3": 131072,
}

#: SHA-256 of the frozen rendered wrapper bytes, per checkpoint and arm.
EXPECTED_PROMPT_SHA256 = {
    "RT": {
        "W1_RAW_DIRECT":
            "9dab5a865967308bc43b219f5b44476cc610fb0b310dd6f528dd3fd0934a4c95",
        "W2_ROLE_CANONICAL":
            "3d8c066ae7729c1bda23033c24a3e397c9b1fe520e5004dcc18631368e97f052",
    },
    "RP_B1": {
        "W1_RAW_DIRECT":
            "9dab5a865967308bc43b219f5b44476cc610fb0b310dd6f528dd3fd0934a4c95",
        "W2_ROLE_CANONICAL":
            "3d8c066ae7729c1bda23033c24a3e397c9b1fe520e5004dcc18631368e97f052",
    },
    "RP_B2": {
        "W1_RAW_DIRECT":
            "9dab5a865967308bc43b219f5b44476cc610fb0b310dd6f528dd3fd0934a4c95",
        "W2_ROLE_CANONICAL":
            "3d8c066ae7729c1bda23033c24a3e397c9b1fe520e5004dcc18631368e97f052",
    },
    "RP_B3": {
        "W1_RAW_DIRECT":
            "9dab5a865967308bc43b219f5b44476cc610fb0b310dd6f528dd3fd0934a4c95",
        "W2_ROLE_CANONICAL":
            "3d8c066ae7729c1bda23033c24a3e397c9b1fe520e5004dcc18631368e97f052",
    },
}

#: Frozen D0 discriminant positions, per checkpoint and arm.
EXPECTED_D0_POSITIONS = {
    "RT": {"W1_RAW_DIRECT": 57, "W2_ROLE_CANONICAL": 63},
    "RP_B1": {"W1_RAW_DIRECT": 57, "W2_ROLE_CANONICAL": 63},
    "RP_B2": {"W1_RAW_DIRECT": 57, "W2_ROLE_CANONICAL": 63},
    "RP_B3": {"W1_RAW_DIRECT": 57, "W2_ROLE_CANONICAL": 63},
}

#: Isomorphic re-instantiation strata assigned by the equivalence record.
EXPECTED_STRATA = {
    "RT": "STRATUM_01",
    "RP_B1": "STRATUM_01",
    "RP_B2": "STRATUM_01",
    "RP_B3": "STRATUM_01",
}

#: SHA-256 of the frozen canonical generated-CoT wrapper bytes.
EXPECTED_COT_WRAPPER_SHA256 = {
    "RT":
        "4ea1868024141139b82f19615a57fc76b6264d7a30a2bdea8fc146ecf1c62081",
    "RP_B1":
        "4ea1868024141139b82f19615a57fc76b6264d7a30a2bdea8fc146ecf1c62081",
    "RP_B2":
        "4ea1868024141139b82f19615a57fc76b6264d7a30a2bdea8fc146ecf1c62081",
    "RP_B3":
        "4ea1868024141139b82f19615a57fc76b6264d7a30a2bdea8fc146ecf1c62081",
}


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------


def _json(path):
    with open(str(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _bundle(root):
    root = pathlib.Path(root)
    return {
        "protocol": _json(root / "studies/study3r/protocol/study3r_protocol_v1.json"),
        "protocol_schema": _json(
            root / "studies/study3r/protocol/study3r_protocol_v1.schema.json"),
        "registry": _json(
            root / "studies/study3r/protocol/study3r_rendering_registry_v1.json"),
        "registry_schema": _json(
            root
            / "studies/study3r/protocol/study3r_rendering_registry_v1.schema.json"),
        "machine": _json(
            root / "studies/study3r/protocol/study3r_state_machine_v1.json"),
        "machine_schema": _json(
            root / "studies/study3r/protocol/study3r_state_machine_v1.schema.json"),
        "pointer": _json(
            root / "studies/study3r/protocol/study3r_protocol_current.json"),
        "pointer_schema": _json(
            root / "studies/study3r/protocol/study3r_protocol_current.schema.json"),
        "statistics": _json(
            root / "studies/study3r/analysis/study3r_design_statistics_tables.json"),
        "census": _json(
            root / "studies/study3r/analysis/study3r_atomic_cell_census_v1.json"),
        "recalculation": _json(
            root
            / "studies/study3r/analysis/study3r_independent_recalculation_tables.json"),
        "acquisition": _json(
            root
            / "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.json"),
        "surfaces": _json(
            root / "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.json"),
        "equivalence": _json(
            root
            / "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.json"),
        "manifest": _json(
            root / "studies/study3r/study3r_candidate_manifest_v1.json"),
        "manifest_schema": _json(
            root / "studies/study3r/study3r_candidate_manifest_v1.schema.json"),
    }


@pytest.fixture(scope="module")
def bundle():
    return _bundle(ROOT)


def _git(*args):
    return subprocess.run(["git", "--no-pager", *args], cwd=str(ROOT),
                          capture_output=True, text=True, check=True).stdout


# ---------------------------------------------------------------------------
# The independent semantic validator
# ---------------------------------------------------------------------------


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_bundle(root):
    """Reject any bundle that departs from the registered Study 3R design.

    This validator is deliberately independent of every generator: it restates
    each registered value rather than recomputing it. It uses only the standard
    library so that it can never be skipped.
    """
    artifacts = _bundle(root)
    protocol = artifacts["protocol"]
    machine = artifacts["machine"]
    registry = artifacts["registry"]
    pointer = artifacts["pointer"]
    statistics = artifacts["statistics"]
    census = artifacts["census"]
    recalculation = artifacts["recalculation"]
    surfaces = artifacts["surfaces"]
    equivalence = artifacts["equivalence"]
    acquisition = artifacts["acquisition"]
    manifest = artifacts["manifest"]

    # -- identity and scope -------------------------------------------------
    _require(protocol["protocol_id"] == "STUDY3R_PROTOCOL_V1",
             "protocol id changed")
    _require(protocol["authority"] == AUTHORITY_RELATIVE, "authority changed")
    _require(protocol["scope"]["target_checkpoint"] == EXPECTED_TARGET,
             "target checkpoint identity changed")
    _require(tuple(protocol["scope"]["rp_b_ladder"]) == EXPECTED_LADDER,
             "RP-B ladder membership or order changed")
    _require(protocol["scope"]["rp_b_ladder_length"] == EXPECTED_LADDER_LENGTH,
             "RP-B ladder length changed")
    _require(protocol["scope"]["rp_b_fallback_candidate"] is None,
             "a RP-B fallback candidate appeared")
    _require(protocol["scope"]["rp_b_post_result_expansion_permitted"] is False,
             "post-result ladder expansion was permitted")
    _require(protocol["scope"]["activation_patching_authorized"] is False,
             "activation patching was authorized")
    _require(protocol["scope"]["rp_m_authorized"] is False,
             "RP-M was authorized")
    _require(protocol["scope"]["mechanism_claims_authorized"] is False,
             "mechanism claims were authorized")
    _require(protocol["scope"]["interface_profile_selection_performed"] is False,
             "an interface profile was selected")

    # -- execution authorization -------------------------------------------
    _require(protocol["status"]["frozen"] is False, "the candidate was frozen")
    _require(protocol["status"]["execution_authorized"] is False,
             "execution was authorized")
    _require(protocol["status"]["formal_execution_authorized"] is False,
             "formal execution was authorized")
    _require(protocol["status"]["authored_state"] == EXPECTED_AUTHORED_STATE,
             "authored state changed")
    _require(pointer["execution_authorized"] is False,
             "the pointer authorized execution")
    _require(pointer["frozen"] is False, "the pointer froze the candidate")

    # -- current authoritative path ----------------------------------------
    _require(pointer["authoritative_protocol"] == EXPECTED_AUTHORITATIVE_PROTOCOL,
             "current authoritative protocol path changed")
    _require(protocol["references"]["authoritative_protocol"]
             == EXPECTED_AUTHORITATIVE_PROTOCOL,
             "protocol self-reference to the authoritative path changed")
    _require(protocol["references"]["current_pointer"] == EXPECTED_CURRENT_POINTER,
             "current pointer path changed")
    _require(protocol["references"]["manifest_generator"]
             == EXPECTED_MANIFEST_GENERATOR, "manifest generator path changed")
    _require(pointer["supersedes"] == [], "the pointer superseded an artifact")
    _require(pointer["runtime_overlay_permitted"] is False,
             "a runtime overlay was permitted")
    _require(pointer["fallback_protocol_permitted"] is False,
             "a fallback protocol was permitted")
    _require(pointer["alternative_authoritative_artifacts"] == [],
             "an alternative authoritative artifact appeared")
    _require((pathlib.Path(root)
              / pathlib.PurePosixPath(EXPECTED_AUTHORITATIVE_PROTOCOL)).exists(),
             "the authoritative protocol path does not resolve to a file")

    # -- checkpoints, revisions and E0 surfaces -----------------------------
    rows = {row["role"]: row for row in protocol["checkpoints"]}
    _require(tuple(sorted(rows)) == tuple(sorted(EXPECTED_ROLES)),
             "checkpoint role set changed")
    expected_repositories = dict(zip(EXPECTED_ROLES,
                                     (EXPECTED_TARGET,) + EXPECTED_LADDER))
    for role in EXPECTED_ROLES:
        row = rows[role]
        _require(row["repository_id"] == expected_repositories[role],
                 "repository identity changed for %s" % role)
        _require(row["immutable_revision"] == EXPECTED_REVISIONS[role],
                 "immutable revision changed for %s" % role)
        _require(row["acquisition_immutable_revision"]
                 == EXPECTED_REVISIONS[role],
                 "acquisition revision disagrees for %s" % role)
        _require(row["revision_matches_acquisition_record"] is True,
                 "revision no longer matches the acquisition record for %s"
                 % role)
        _require(tuple(sorted(row["e0_legal_answer_surfaces"]))
                 == tuple(sorted(EXPECTED_LABELS)),
                 "E0 legal answer surface set changed for %s" % role)
        for label in EXPECTED_LABELS:
            surface = row["e0_legal_answer_surfaces"][label]
            _require(surface["text"] == label,
                     "E0 legal surface text changed for %s/%s" % (role, label))
            _require(surface["token_ids"]
                     == EXPECTED_ANSWER_TOKEN_IDS[role][label],
                     "E0 legal surface token ids changed for %s/%s"
                     % (role, label))
        _require(row["e0_termination_margin_tokens"]
                 == EXPECTED_TERMINATION_MARGIN,
                 "E0 termination margin changed for %s" % role)
        _require(row["e0_max_new_tokens"] == EXPECTED_MAX_NEW_TOKENS[role],
                 "E0 max_new_tokens changed for %s" % role)

    primary = protocol["estimands"]["primary"]
    _require(primary["estimand_id"] == EXPECTED_E0_ID, "E0 estimand id changed")
    _require(primary["decoding"]["do_sample"] is False, "E0 sampling enabled")
    _require(primary["scoring"]["rule"] == "full_sequence_exact_match",
             "E0 scoring rule changed")
    _require(primary["scoring"]["prefix_matching_permitted"] is False,
             "E0 prefix matching was permitted")
    _require(primary["scoring"][
        "rationale_or_extra_emitted_token_permitted"] is False,
        "E0 permitted a rationale or an extra emitted token")
    _require(primary["scoring"]["unparseable_output"] == "incorrect",
             "E0 unparseable treatment changed")
    _require(primary["descriptive_only_diagnostics_may_determine_a_gate"]
             is False, "a descriptive diagnostic was allowed to gate")

    # -- D0 diagnostic ------------------------------------------------------
    diagnostic = protocol["estimands"]["diagnostic"]
    _require(diagnostic["estimand_id"] == EXPECTED_D0_ID,
             "D0 estimand id changed")
    _require(diagnostic["is_ever_a_gate"] is False, "D0 became a gate")
    _require(diagnostic["is_ever_an_rp_b_gate"] is False,
             "D0 became an RP-B gate")
    _require(diagnostic["qualifies_a_candidate"] is False,
             "D0 was allowed to qualify a candidate")
    _require(list(diagnostic["candidate_set"]) == list(EXPECTED_LABELS),
             "D0 candidate set changed")
    _require(diagnostic["discriminant_position_offset"]
             == EXPECTED_D0_POSITION_OFFSET,
             "D0 discriminant position offset changed")
    _require("never demonstrates natural expression" in diagnostic["limitation"],
             "the D0 limitation statement was weakened")

    # -- generated-CoT ceiling ---------------------------------------------
    ceiling = protocol["estimands"]["generated_cot_ceiling"]
    _require(ceiling["estimand_id"] == EXPECTED_COT_ID,
             "CoT estimand id changed")
    _require(ceiling["route_id"] == EXPECTED_COT_ROUTE, "CoT route id changed")
    _require(ceiling["separate_from_e0"] is True,
             "the CoT ceiling stopped being separate from E0")
    _require(ceiling["k"] == EXPECTED_COT_K, "CoT k changed")
    _require(ceiling["parser_id"] == EXPECTED_COT_PARSER, "CoT parser changed")
    _require(ceiling["unparseable_output"] == "incorrect",
             "CoT unparseable treatment changed")
    _require(ceiling["is_an_interface_selector"] is False,
             "the CoT ceiling became an interface selector")
    for role in EXPECTED_ROLES:
        bound = ceiling["resource_bounds_per_checkpoint"][role]
        _require(bound["max_new_tokens_per_item"] == EXPECTED_COT_MAX_NEW_TOKENS,
                 "CoT per-item generation bound changed for %s" % role)
        _require(bound["fits_context_window"] is True,
                 "the CoT bound no longer fits the context window for %s" % role)
        _require(bound["context_window_tokens"]
                 == EXPECTED_CONTEXT_WINDOWS[role],
                 "CoT context window changed for %s" % role)
        wrapper = ceiling["canonical_wrapper_per_checkpoint"][role]
        _require(wrapper["utf8_sha256"] == EXPECTED_COT_WRAPPER_SHA256[role],
                 "canonical CoT wrapper bytes changed for %s" % role)

    # -- wrapper arms -------------------------------------------------------
    arms = {arm["arm_id"]: arm for arm in protocol["interfaces"]["e0_arms"]}
    _require(tuple(sorted(arms)) == tuple(sorted(EXPECTED_ARMS)),
             "the registered E0 wrapper arm set changed")
    _require(protocol["interfaces"]["arm_count"] == 2,
             "the number of E0 wrapper arms changed")
    _require(protocol["interfaces"]["arm_gate"] == "joint_adequacy",
             "the wrapper gate stopped being joint adequacy")
    _require(protocol["interfaces"]["arm_differentiating_field"] == "envelope",
             "the arm differentiating field changed")
    _require(arms["W1_RAW_DIRECT"]["message_roles"] == [],
             "the raw arm acquired a message role")
    _require(arms["W2_ROLE_CANONICAL"]["message_roles"]
             == [EXPECTED_ROLE_CANONICAL_MESSAGE_ROLE],
             "the role-canonical wrapper role changed")
    for arm_id in EXPECTED_ARMS:
        _require(arms[arm_id]["few_shot_example_count"] == 0,
                 "few-shot examples appeared in %s" % arm_id)
        for role in EXPECTED_ROLES:
            entry = arms[arm_id]["per_checkpoint"][role]
            _require(entry["prompt_utf8_sha256"]
                     == EXPECTED_PROMPT_SHA256[role][arm_id],
                     "wrapper bytes changed for %s/%s" % (role, arm_id))
            _require(entry["d0_discriminant_position"]
                     == EXPECTED_D0_POSITIONS[role][arm_id],
                     "D0 discriminant position changed for %s/%s"
                     % (role, arm_id))

    registry_entries = {entry["registry_key"]: entry
                        for entry in registry["entries"]}
    _require(registry["entry_count"] == 8,
             "the rendering registry no longer covers four checkpoints "
             "times two arms")
    for role in EXPECTED_ROLES:
        for arm_id in EXPECTED_ARMS:
            entry = registry_entries["%s|%s" % (role, arm_id)]
            _require(entry["rendered_utf8_sha256"]
                     == EXPECTED_PROMPT_SHA256[role][arm_id],
                     "registry wrapper bytes changed for %s/%s" % (role, arm_id))
            _require(entry["few_shot_examples"] == [],
                     "registry few-shot examples appeared for %s/%s"
                     % (role, arm_id))
            _require(entry["immutable_revision"] == EXPECTED_REVISIONS[role],
                     "registry revision changed for %s/%s" % (role, arm_id))
            expected_roles = ([] if arm_id == "W1_RAW_DIRECT"
                              else [EXPECTED_ROLE_CANONICAL_MESSAGE_ROLE])
            _require(entry["message_roles"] == expected_roles,
                     "registry wrapper role changed for %s/%s" % (role, arm_id))
    _require(registry["paired_discordance_reporting"]["required"] is True,
             "paired discordance reporting stopped being required")
    _require(registry["paired_discordance_reporting"]["is_a_gate"] is False,
             "paired discordance became a gate")
    _require(registry["paired_discordance_reporting"][
        "estimates_a_template_effect"] is False,
        "the registry began estimating a template effect")

    # -- wrapper bytes must never drift from the frozen surfaces ------------
    rendering = protocol["task_populations"]["rendering_rules"]
    _require(rendering["answer_cue"] == EXPECTED_ANSWER_CUE,
             "the registered answer cue changed")
    _require(rendering["answer_cue"] == surfaces["answer_cue"],
             "the answer cue drifted from the frozen tokenizer surfaces")
    _require(rendering["item_body_template"] == surfaces["item_body_template"],
             "the item body template drifted from the frozen surfaces")
    _require(rendering["raw_envelope_separator"]
             == surfaces["raw_envelope_separator"],
             "the raw envelope separator drifted from the frozen surfaces")
    _require(rendering["newline_bytes"] == "\n", "the newline bytes changed")
    _require(protocol["task_populations"]["label_alphabet"]
             == list(EXPECTED_LABELS),
             "the registered label alphabet changed")
    _require(protocol["task_populations"]["chance_level"]
             == EXPECTED_CHANCE_LEVEL,
             "the task-population chance level changed")
    _require(protocol["task_populations"]["seed_commitment_procedure"][
        "seed_drawn_in_the_authoring_session"] is False,
        "an execution seed was drawn in the authoring session")
    _require(protocol["task_populations"]["seed_commitment_procedure"][
        "banks_realized_in_the_authoring_session"] is False,
        "a scientific bank was realized in the authoring session")
    _require(protocol["task_populations"]["tokenizer_fixtures"][
        "are_scientific_items"] is False,
        "tokenizer fixtures became scientific items")

    # -- statistics ---------------------------------------------------------
    budget = protocol["statistics"]["global_error_budget"]
    _require(protocol["statistics"]["m_max"] == EXPECTED_M_MAX,
             "m_max changed")
    _require(protocol["statistics"]["atomic_cell_count"] == EXPECTED_M_MAX,
             "the atomic-cell count changed")
    _require(census["count"] == EXPECTED_M_MAX, "the census count changed")
    _require(census["m_max"] == EXPECTED_M_MAX, "the census m_max changed")
    _require(census["both_wrapper_arms_enter_the_census"] is True,
             "a wrapper arm left the census")
    _require(census["full_ladder_enters_the_census"] is True,
             "the full ladder left the census")
    _require(sorted({cell["route"] for cell in census["cells"]
                     if cell["route"].startswith("W")}) == sorted(EXPECTED_ARMS),
             "the census wrapper factor changed")
    _require(budget["alpha_global"] == EXPECTED_ALPHA_GLOBAL,
             "the global error budget changed")
    _require(budget["alpha_per_cell"] == EXPECTED_ALPHA_PER_CELL,
             "the per-cell alpha changed")
    _require(budget["family_id"] == EXPECTED_MULTIPLICITY_FAMILY,
             "the multiplicity family changed")
    _require(budget["claims_fixed_sequence_protection"] is False,
             "fixed-sequence protection was claimed")
    _require(protocol["statistics"]["rp_b_decision_id"]
             == EXPECTED_RPB_DECISION_ID, "the RP-B decision id changed")
    _require(protocol["statistics"]["diagnostic_without_a_gate"]
             == EXPECTED_D0_ID, "D0 stopped being the gate-free diagnostic")
    ladder = protocol["statistics"]["ladder_multiplicity"]
    _require(ladder["corrects_over_full_registered_l"] is True,
             "multiplicity stopped covering the full ladder")
    _require(ladder["registered_l"] == EXPECTED_LADDER_LENGTH,
             "the registered ladder length changed in the multiplicity block")
    _require(ladder["selection_rule"] == "first_confirmed_pass",
             "the ladder selection rule changed")
    _require(ladder["evaluations_per_candidate"] == {"development": 1,
                                                     "confirmation": 1},
             "the per-candidate evaluation budget changed")
    _require(protocol["statistics"]["unresolved_values"] == [],
             "an unresolved value was registered")

    gates = {gate["gate_id"]: gate for gate in protocol["statistics"]["gates"]}
    _require(sorted(gates) == sorted(EXPECTED_GATES),
             "the registered gate set changed")
    for gate_id, expected in EXPECTED_GATES.items():
        cells, direction, floor, alternative, n, boundary = expected
        gate = gates[gate_id]
        _require(gate["atomic_cell_count"] == cells,
                 "%s cell count changed" % gate_id)
        _require(len(gate["atomic_cells"]) == cells,
                 "%s cell list length changed" % gate_id)
        _require(gate["direction"] == direction, "%s direction changed" % gate_id)
        _require(gate["floor_or_upper_margin"] == floor,
                 "%s floor or upper margin changed" % gate_id)
        _require(gate["effect_or_adequacy_margin"] == alternative,
                 "%s alternative changed" % gate_id)
        _require(gate["n"] == n, "%s sample size changed" % gate_id)
        _require(gate["pass_boundary"] == boundary,
                 "%s integer pass boundary changed" % gate_id)
        _require(gate["alpha_per_cell"] == EXPECTED_ALPHA_PER_CELL,
                 "%s per-cell alpha changed" % gate_id)
        _require(gate["development_alpha"] == EXPECTED_ALPHA_PER_CELL,
                 "%s development alpha changed" % gate_id)
        _require(gate["confirmation_alpha"] == EXPECTED_ALPHA_PER_CELL,
                 "%s confirmation alpha changed" % gate_id)
        _require(gate["power_target"] == EXPECTED_POWER_TARGET,
                 "%s power target changed" % gate_id)
        _require(gate["chance_level"] == EXPECTED_CHANCE_LEVEL,
                 "%s chance level changed" % gate_id)
        _require(gate["statistical_unit"] == "item",
                 "%s statistical unit changed" % gate_id)
        _require(gate["sample_size_minimality_proof"][
            "every_smaller_n_falls_short"] is True,
            "%s lost its minimality proof" % gate_id)
        _require(gate["sample_size_minimality_proof"][
            "smaller_n_values_checked"] == n - 1,
            "%s minimality search was truncated" % gate_id)
        _require(gate["missing_or_unparseable_treatment"].strip() != "",
                 "%s lost its missing-data rule" % gate_id)
        _require(gate["stop_rule"].strip() != "", "%s lost its stop rule"
                 % gate_id)
    _require(gates["G05_NEGATIVE_CONTROL"]["direction"]
             == "less_than_upper_margin",
             "the negative control stopped being an upper-bound rule")
    _require("not significantly above chance"
             not in json.dumps(protocol).lower(),
             "an equivalence-by-non-significance argument appeared")

    # -- statistics tables and the independent recalculation ---------------
    _require(statistics["global_error_budget"]["m_max"] == EXPECTED_M_MAX,
             "the statistics tables m_max changed")
    _require(statistics["arithmetic"]["uses_normal_approximation"] is False,
             "a normal approximation was used")
    _require(statistics["arithmetic"]["uses_floating_point_comparison"] is False,
             "a floating-point gate comparison was used")
    _require(recalculation["independence"]["imports_production_calculators"]
             is False, "the recalculation stopped being independent")
    _require(recalculation["agreement"]["exact_agreement"] is True,
             "the independent recalculation disagrees")
    _require(recalculation["recomputed_census"]["m_max"] == EXPECTED_M_MAX,
             "the independently recomputed m_max changed")
    _require(recalculation["recomputed_census"]["agrees_with_protocol"] is True,
             "the independently recomputed census disagrees")
    _require(recalculation["agreement"]["gates_in_agreement"]
             == len(EXPECTED_GATES), "a gate fell out of exact agreement")

    # -- state machine ------------------------------------------------------
    states = {state["state_id"]: state for state in machine["states"]}
    _require(sorted(states) == sorted(EXPECTED_TRANSITIONS),
             "the registered state set changed")
    for state_id, expected in EXPECTED_TRANSITIONS.items():
        observed = {transition["outcome"]: transition["target"]
                    for transition in states[state_id]["transitions"]}
        _require(observed == expected,
                 "state transition changed for %s" % state_id)
        _require(len(states[state_id]["transitions"]) == len(observed),
                 "a duplicate outcome appeared in %s" % state_id)
    terminals = {entry["terminal_id"] for entry in machine["terminals"]}
    targets = {transition["target"]
               for state in machine["states"]
               for transition in state["transitions"]}
    _require(targets <= (set(states) | terminals),
             "a transition targets an unknown state")
    _require(machine["identifier_uniqueness"][
        "every_registered_gate_appears_exactly_once"] is True,
        "a gate is missing from or duplicated in the state machine")
    _require(machine["identifier_uniqueness"][
        "state_and_terminal_namespaces_are_disjoint"] is True,
        "a state id collides with a terminal id")
    _require(machine["activation_patching_states"] == [],
             "an activation-patching state appeared")
    _require(machine["rp_m_states"] == [], "an RP-M state appeared")
    _require(machine["mechanism_claim_states"] == [],
             "a mechanism-claim state appeared")
    bounded = [entry["meaning"] for entry in machine["terminals"]
               if entry["terminal_id"] == "T07_NO_QUALIFIED_REFERENCE"][0]
    _require("makes no claim about other models" in bounded,
             "the no-qualified-reference terminal lost its bound")

    # -- acquisition boundary ----------------------------------------------
    _require(acquisition["trust_remote_code"] is False,
             "remote code execution was enabled")
    proof = acquisition["no_weight_file_proof"]
    _require(proof["weight_paths_requested_total"] == 0,
             "a weight path was requested")
    _require(proof["weight_files_acquired_total"] == 0,
             "a weight file was acquired")
    _require(proof["weight_bytes_acquired_total"] == 0,
             "weight bytes were acquired")
    _require(proof["no_acquired_path_has_a_weight_suffix"] is True,
             "an acquired path has a weight suffix")
    for record in acquisition["checkpoints"]:
        _require(record["weight_paths_requested"] == [],
                 "a weight path was requested for %s" % record["role"])
        for entry in record["acquired_files"]:
            _require(not entry["path"].lower().endswith(WEIGHT_SUFFIXES),
                     "a weight file appears in the acquisition record")
    for name in ZERO_OPERATION_COUNTERS:
        _require(acquisition["counters"][name] == 0,
                 "the %s counter is no longer zero" % name)
        _require(protocol["boundaries"]["zero_operation_counters"].get(name)
                 == 0, "the protocol %s counter is no longer zero" % name)
    _require(protocol["boundaries"]["no_weight_file_acquired"] is True,
             "the protocol stopped asserting that no weight file was acquired")
    _require(protocol["boundaries"]["evidence_ledger_rows_written"] == 0,
             "an evidence-ledger row was written")
    _require(protocol["boundaries"]["study3m_artifacts"] == [],
             "a Study 3M artifact appeared")

    # -- tokenizer surfaces and strata -------------------------------------
    _require(list(surfaces["arm_ids"]) == list(EXPECTED_ARMS),
             "the surfaces arm list changed")
    _require(list(surfaces["label_alphabet"]) == list(EXPECTED_LABELS),
             "the label alphabet changed")
    _require(surfaces["canonical_fixture"]["is_scientific_item"] is False,
             "the canonical fixture became a scientific item")
    for fixture in surfaces["tokenizer_fixtures"]:
        _require(fixture["is_scientific_item"] is False,
                 "a tokenizer fixture became a scientific item")
    _require(equivalence["reference_role"] == "RT",
             "the equivalence reference role changed")
    _require(equivalence["role_to_stratum"] == EXPECTED_STRATA,
             "the isomorphic re-instantiation strata changed")
    _require(equivalence["distinct_stratum_count"]
             == len(set(EXPECTED_STRATA.values())),
             "the distinct stratum count changed")
    _require("never pooled" in equivalence["pooling_rule"],
             "the no-pooling rule was weakened")
    _require(protocol["interfaces"]["tokenizer_functional_equivalence"][
        "isomorphic_reinstantiation_strata_are_never_pooled"] is True,
        "isomorphic strata became poolable")

    # -- manifest -----------------------------------------------------------
    _require(manifest["manifest_kind"] == "candidate_reproducibility_manifest",
             "the manifest kind changed")
    _require(manifest["is_an_execution_seal"] is False,
             "the manifest claimed to be an execution seal")
    _require(manifest["sealing_design"]["acyclic"] is True,
             "the sealing design stopped being acyclic")
    _require(manifest["sealing_design"][
        "claims_to_contain_its_own_hash"] is False,
        "the manifest claimed an impossible self-hash")
    _require(set(manifest["inclusion_categories"])
             == EXPECTED_MANIFEST_CATEGORIES,
             "the manifest inclusion rule set changed")
    _require(manifest["missing_paths"] == [],
             "the manifest is missing a required path")
    _require(manifest["every_entry_is_lf_only"] is True,
             "a manifest entry is not LF-only")
    _require(manifest["no_entry_has_a_utf8_bom"] is True,
             "a manifest entry carries a UTF-8 BOM")
    _require(len(manifest["self_exclusions"]) == 1,
             "the manifest self-exclusion set changed")
    _require(manifest["self_exclusions"][0]["path"]
             == "studies/study3r/study3r_candidate_manifest_v1.json",
             "the manifest self-exclusion path changed")
    _require(len(manifest["deferred_exclusions"]) >= 1,
             "the manifest deferred-exclusion explanations disappeared")
    for entry in manifest["deferred_exclusions"]:
        _require(len(entry["reason"]) >= 40,
                 "a deferred exclusion lost its explanation")
    manifest_paths = {entry["path"] for entry in manifest["entries"]}
    _require(manifest["self_exclusions"][0]["path"] not in manifest_paths,
             "the manifest included itself")
    for entry in manifest["entries"]:
        target = pathlib.Path(root) / pathlib.PurePosixPath(entry["path"])
        payload = target.read_bytes()
        _require(len(payload) == entry["bytes"],
                 "manifest byte length drifted for %s" % entry["path"])
        _require(hashlib.sha256(payload).hexdigest() == entry["sha256"],
                 "manifest digest drifted for %s" % entry["path"])
    return artifacts


# ---------------------------------------------------------------------------
# Coordinated generator-mutation harness
# ---------------------------------------------------------------------------

STAGED_PATHS = (
    "studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md",
    "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.json",
    "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.schema.json",
    "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.json",
    "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.schema.json",
    "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.json",
    "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.schema.json",
    "studies/study3r/analysis/study3r_design_statistics.py",
    "studies/study3r/analysis/study3r_independent_recalculation.py",
    "studies/study3r/analysis/study3r_manifest.py",
    "studies/study3r/analysis/study3r_protocol_build.py",
    "studies/study3r/analysis/study3r_tokenizer_probe.py",
    "studies/study3r/tasks/study3r_task_generators_v1.py",
    "tests/test_study3r_protocol_v1.py",
)

BUILD = "studies/study3r/analysis/study3r_protocol_build.py"
RECALC = "studies/study3r/analysis/study3r_independent_recalculation.py"
MANIFEST = "studies/study3r/analysis/study3r_manifest.py"
STATS = "studies/study3r/analysis/study3r_design_statistics.py"
TASKS = "studies/study3r/tasks/study3r_task_generators_v1.py"

#: ``(mutation_id, target file, exact old text, replacement text)``.
#: Every entry must be killed by :func:`validate_bundle`.
MUTATIONS = (
    ("target_checkpoint_identity", BUILD,
     'TARGET_CHECKPOINT = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"',
     'TARGET_CHECKPOINT = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"'),
    ("rp_b_membership_and_order", BUILD,
     '    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",\n'
     '    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",\n'
     '    "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",\n',
     '    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",\n'
     '    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",\n'
     '    "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",\n'),
    ("rp_b_ladder_length_l", BUILD,
     "LADDER_LENGTH = 3", "LADDER_LENGTH = 2"),
    ("immutable_revision", BUILD,
     '"RT": "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"',
     '"RT": "0000000000000000000000000000000000000000"'),
    ("e0_legal_answer_surface", BUILD,
     'REGISTERED_LABELS = ("A", "B", "C", "D")',
     'REGISTERED_LABELS = ("A", "B", "C", "E")'),
    ("e0_max_new_tokens", BUILD,
     "E0_TERMINATION_MARGIN_TOKENS = 1", "E0_TERMINATION_MARGIN_TOKENS = 2"),
    ("d0_discriminant_position", BUILD,
     "D0_DISCRIMINANT_POSITION_OFFSET = 0",
     "D0_DISCRIMINANT_POSITION_OFFSET = 1"),
    ("wrapper_role", BUILD,
     'ROLE_CANONICAL_MESSAGE_ROLE = "user"',
     'ROLE_CANONICAL_MESSAGE_ROLE = "system"'),
    ("wrapper_bytes", TASKS,
     'ANSWER_CUE = "Answer:\\n"', 'ANSWER_CUE = "Answer: \\n"'),
    ("gate_alpha", STATS, "ALPHA_GLOBAL = (1, 20)", "ALPHA_GLOBAL = (1, 10)"),
    ("gate_sample_size", STATS, "POWER_TARGET = (9, 10)",
     "POWER_TARGET = (85, 100)"),
    ("gate_floor", STATS, '"floor": (3, 4),', '"floor": (7, 10),'),
    ("gate_pass_count", STATS, "PASS_BOUNDARY_OFFSET = 0",
     "PASS_BOUNDARY_OFFSET = 1"),
    ("multiplicity_family", STATS,
     'MULTIPLICITY_FAMILY = "F_GLOBAL_STUDY3R"',
     'MULTIPLICITY_FAMILY = "F_GLOBAL_STUDY3R_V2"'),
    ("negative_control_margin", STATS, '"floor": (35, 100),',
     '"floor": (45, 100),'),
    ("negative_control_chance_level", STATS, "CHANCE_LEVEL = (1, 4)",
     "CHANCE_LEVEL = (1, 5)"),
    ("cot_k", BUILD, "COT_K = 1", "COT_K = 2"),
    ("cot_parser", BUILD, 'COT_PARSER_ID = "P1_FINAL_ANSWER_LAST_LINE"',
     'COT_PARSER_ID = "P2_ANY_LABEL_ANYWHERE"'),
    ("cot_resource_bound", BUILD, "COT_MAX_NEW_TOKENS_PER_ITEM = 4096",
     "COT_MAX_NEW_TOKENS_PER_ITEM = 262144"),
    ("state_transition", BUILD,
     '"target": "T04_COMPETENCE_CONTROL_FAILED"},',
     '"target": "S05_NEGATIVE_CONTROL"},'),
    ("census_wrapper_factor", STATS,
     'E0_ARMS = ("W1_RAW_DIRECT", "W2_ROLE_CANONICAL")',
     'E0_ARMS = ("W1_RAW_DIRECT",)'),
    ("current_authoritative_path", BUILD,
     'AUTHORITATIVE_PROTOCOL_PATH = "studies/study3r/protocol/'
     'study3r_protocol_v1.json"',
     'AUTHORITATIVE_PROTOCOL_PATH = "studies/study3r/protocol/'
     'study3r_protocol_v0.json"'),
    ("execution_authorization", BUILD,
     "\nEXECUTION_AUTHORIZED = False", "\nEXECUTION_AUTHORIZED = True"),
    ("manifest_inclusion_rule", MANIFEST,
     '    ("semantic_and_mutation_tests", "tests/test_study3r_protocol_v1.py"),\n',
     ""),
)

#: The mutation categories the authority requires to be killed.
REQUIRED_MUTATION_CATEGORIES = (
    "target_checkpoint_identity", "rp_b_membership_and_order",
    "rp_b_ladder_length_l", "immutable_revision", "e0_legal_answer_surface",
    "e0_max_new_tokens", "d0_discriminant_position", "wrapper_role",
    "wrapper_bytes", "gate_alpha", "gate_sample_size", "gate_floor",
    "gate_pass_count", "multiplicity_family", "negative_control_margin",
    "negative_control_chance_level", "cot_k", "cot_parser",
    "cot_resource_bound", "state_transition", "census_wrapper_factor",
    "current_authoritative_path", "execution_authorization",
    "manifest_inclusion_rule",
)


def _stage(destination):
    destination = pathlib.Path(destination)
    for relative in STAGED_PATHS:
        source = ROOT / pathlib.PurePosixPath(relative)
        target = destination / pathlib.PurePosixPath(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(source), str(target))
    return destination


def _run(root, script, *args):
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(pathlib.Path(root) / pathlib.PurePosixPath(script)),
         *args],
        cwd=str(root), capture_output=True, text=True, env=environment)


def _rebuild(root):
    steps = (
        (BUILD, ("--source-root", str(root), "--out-root", str(root))),
        (RECALC, ("--root", str(root))),
        (MANIFEST, ("--root", str(root))),
    )
    for script, args in steps:
        completed = _run(root, script, *args)
        if completed.returncode != 0:
            raise RuntimeError("rebuild step %s failed: %s"
                               % (script, completed.stderr[-2000:]))
    return root


def _apply(root, relative, old, new):
    path = pathlib.Path(root) / pathlib.PurePosixPath(relative)
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise AssertionError("mutation anchor is not unique in %s (%d matches)"
                             % (relative, text.count(old)))
    with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.replace(old, new, 1))


# ---------------------------------------------------------------------------
# 1. Presence, encoding and reproduction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relative", AUTHORED_PATHS)
def test_every_authored_path_exists_and_is_lf_only_without_a_bom(relative):
    path = ROOT / pathlib.PurePosixPath(relative)
    assert path.is_file(), relative
    payload = path.read_bytes()
    assert b"\r" not in payload, relative
    assert not payload.startswith(b"\xef\xbb\xbf"), relative


def test_the_authoring_session_wrote_nothing_outside_the_study3r_namespace():
    """No path outside the declared Study 3R namespace may move.

    The permitted set is the exact authored path set plus anything inside
    ``studies/study3r/``, which is the namespace the Study 3R charter declares.
    At the authoring head the two sets coincide; keeping the namespace clause
    lets the single independent focused review add its own artifacts inside the
    namespace without expiring this invariant.
    """
    changed = {line.strip() for line
               in _git("diff", "--name-only", STARTING_COMMIT, "HEAD").splitlines()
               if line.strip()}
    outside = {path for path in changed
               if path not in AUTHORED_PATHS
               and not path.startswith("studies/study3r/")}
    assert outside == set(), sorted(outside)


def test_the_authoring_history_is_linear_and_merge_free():
    commits = [line.strip() for line
               in _git("rev-list", "%s..HEAD" % STARTING_COMMIT).splitlines()
               if line.strip()]
    assert commits, "no authoring commits found"
    merges = [line.strip() for line
              in _git("rev-list", "--merges",
                      "%s..HEAD" % STARTING_COMMIT).splitlines()
              if line.strip()]
    assert merges == []
    assert _git("merge-base", STARTING_COMMIT, "HEAD").strip() == STARTING_COMMIT


def test_the_authority_was_published_alone_as_the_first_authoring_commit():
    commits = [line.strip() for line
               in _git("rev-list", "--reverse",
                       "%s..HEAD" % STARTING_COMMIT).splitlines()
               if line.strip()]
    first = commits[0]
    listed = [line.strip() for line
              in _git("show", "--name-only", "--format=", first).splitlines()
              if line.strip()]
    assert listed == [AUTHORITY_RELATIVE], listed
    parent = _git("rev-parse", "%s^" % first).strip()
    assert parent == STARTING_COMMIT


def test_the_bundle_reproduces_byte_for_byte_from_its_generators(tmp_path):
    staged = _stage(tmp_path / "reproduce")
    _rebuild(staged)
    generated = (
        "studies/study3r/protocol/study3r_protocol_v1.json",
        "studies/study3r/protocol/study3r_protocol_v1.schema.json",
        "studies/study3r/protocol/study3r_protocol_v1.md",
        "studies/study3r/protocol/study3r_rendering_registry_v1.json",
        "studies/study3r/protocol/study3r_rendering_registry_v1.schema.json",
        "studies/study3r/protocol/study3r_state_machine_v1.json",
        "studies/study3r/protocol/study3r_state_machine_v1.schema.json",
        "studies/study3r/protocol/study3r_protocol_current.json",
        "studies/study3r/protocol/study3r_protocol_current.schema.json",
        "studies/study3r/analysis/study3r_design_statistics_tables.json",
        "studies/study3r/analysis/study3r_atomic_cell_census_v1.json",
        "studies/study3r/analysis/study3r_independent_recalculation_tables.json",
        "studies/study3r/study3r_candidate_manifest_v1.schema.json",
    )
    for relative in generated:
        committed = (ROOT / pathlib.PurePosixPath(relative)).read_bytes()
        rebuilt = (staged / pathlib.PurePosixPath(relative)).read_bytes()
        assert committed == rebuilt, relative
    committed_manifest = _json(
        ROOT / "studies/study3r/study3r_candidate_manifest_v1.json")
    rebuilt_manifest = _json(
        staged / "studies/study3r/study3r_candidate_manifest_v1.json")
    for key in ("entries", "entry_count", "aggregate_sha256",
                "inclusion_categories", "self_exclusions", "missing_paths"):
        if key == "entries":
            strip = [{name: value for name, value in entry.items()
                      if name != "git_blob"} for entry in committed_manifest[key]]
            other = [{name: value for name, value in entry.items()
                      if name != "git_blob"} for entry in rebuilt_manifest[key]]
            assert strip == other, "manifest entries did not reproduce"
        else:
            assert committed_manifest[key] == rebuilt_manifest[key], key


# ---------------------------------------------------------------------------
# 2. Schema conformance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("document,schema", [
    ("protocol", "protocol_schema"),
    ("registry", "registry_schema"),
    ("machine", "machine_schema"),
    ("pointer", "pointer_schema"),
    ("manifest", "manifest_schema"),
])
def test_each_artifact_validates_against_its_restrictive_schema(
        bundle, document, schema):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(bundle[document], bundle[schema])


@pytest.mark.parametrize("document,schema_path", [
    ("acquisition",
     "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.schema.json"),
    ("surfaces",
     "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.schema.json"),
    ("equivalence",
     "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.schema.json"),
])
def test_each_acquisition_artifact_validates_against_its_schema(
        bundle, document, schema_path):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(bundle[document],
                        _json(ROOT / pathlib.PurePosixPath(schema_path)))


@pytest.mark.parametrize("schema_path", [
    "studies/study3r/protocol/study3r_protocol_v1.schema.json",
    "studies/study3r/protocol/study3r_rendering_registry_v1.schema.json",
    "studies/study3r/protocol/study3r_state_machine_v1.schema.json",
    "studies/study3r/protocol/study3r_protocol_current.schema.json",
    "studies/study3r/study3r_candidate_manifest_v1.schema.json",
    "studies/study3r/study3r_authoring_disclosure_v1.schema.json",
    "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.schema.json",
    "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.schema.json",
    "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.schema.json",
])
def test_no_decision_bearing_property_schema_is_unconstrained(schema_path):
    """No property schema may be empty or a bare type with no constraint.

    ``null`` and ``boolean`` are exempt: their value domains are already finite
    and completely enumerated by the type alone. Every other property schema
    must carry at least one further keyword (``const``, ``enum``, ``pattern``,
    ``minimum``, ``minLength``, ``properties``, ``items`` and so on).
    """
    document = _json(ROOT / pathlib.PurePosixPath(schema_path))
    exempt = {"null", "boolean"}

    def walk(node, trail):
        if isinstance(node, dict):
            if trail and trail[-2:-1] == ["properties"]:
                assert node != {}, "empty schema at %s" % "/".join(trail)
                if set(node) <= {"type"}:
                    declared = node.get("type")
                    declared = (declared if isinstance(declared, list)
                                else [declared])
                    assert set(declared) <= exempt, (
                        "unconstrained %r property schema at %s"
                        % (declared, "/".join(trail)))
            for key, value in node.items():
                walk(value, trail + [str(key)])
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, trail + [str(index)])

    walk(document, [])
    assert document.get("additionalProperties") is False, schema_path


# ---------------------------------------------------------------------------
# 3. Semantic validation of the committed bundle
# ---------------------------------------------------------------------------


def test_the_committed_bundle_passes_independent_semantic_validation():
    validate_bundle(ROOT)


def test_the_atomic_cell_census_is_exactly_the_registered_cross_product(bundle):
    expected = []
    for gate in bundle["protocol"]["statistics"]["gates"]:
        for role in gate["checkpoint_roles"]:
            for route in gate["routes"]:
                expected.append("%s|%s|%s" % (gate["gate_id"], role, route))
    observed = [cell["cell_id"] for cell in bundle["census"]["cells"]]
    assert sorted(observed) == sorted(expected)
    assert len(set(observed)) == len(observed)
    assert len(observed) == EXPECTED_M_MAX
    assert sum(count for count in
               bundle["census"]["counts_by_gate"].values()) == EXPECTED_M_MAX


def test_the_diagnostic_contributes_no_gate_bearing_cell(bundle):
    assert bundle["census"]["diagnostic_contributes_no_cell"] is True
    assert all(not cell["gate_id"].startswith("D0")
               for cell in bundle["census"]["cells"])
    assert EXPECTED_D0_ID not in {
        gate["estimand"] for gate in bundle["protocol"]["statistics"]["gates"]}


def test_every_gate_boundary_is_exact_and_minimal(bundle):
    from fractions import Fraction
    from math import comb

    alpha = Fraction(1, 1160)
    for gate in bundle["protocol"]["statistics"]["gates"]:
        numerator, _, denominator = gate["floor_or_upper_margin"].partition("/")
        floor = Fraction(int(numerator), int(denominator))
        n = gate["n"]
        k = gate["pass_boundary"]
        if gate["direction"] == "greater_than_floor":
            def tail(bound):
                return sum(Fraction(comb(n, i)) * floor ** i
                           * (1 - floor) ** (n - i)
                           for i in range(bound, n + 1))
            assert tail(k) <= alpha, gate["gate_id"]
            assert tail(k - 1) > alpha, gate["gate_id"]
        else:
            def tail(bound):
                return sum(Fraction(comb(n, i)) * floor ** i
                           * (1 - floor) ** (n - i)
                           for i in range(0, bound + 1))
            assert tail(k) <= alpha, gate["gate_id"]
            assert tail(k + 1) > alpha, gate["gate_id"]


def test_the_markdown_and_the_json_agree_on_every_decision_bearing_value(bundle):
    text = (PROTOCOL_DIR / "study3r_protocol_v1.md").read_text(encoding="utf-8")
    assert EXPECTED_AUTHORED_STATE in text
    assert EXPECTED_TARGET in text
    for repository in EXPECTED_LADDER:
        assert repository in text
    for role in EXPECTED_ROLES:
        assert EXPECTED_REVISIONS[role] in text
    assert "`m_max = %d`" % EXPECTED_M_MAX in text
    assert EXPECTED_ALPHA_PER_CELL in text
    for gate_id, expected in EXPECTED_GATES.items():
        assert "`%s`" % gate_id in text
        assert "| %d |" % expected[4] in text
    for state_id in EXPECTED_TRANSITIONS:
        assert "`%s`" % state_id in text
    assert "`formal_execution_authorized` remains `false`." in text


def test_the_protocol_registers_exactly_one_authoritative_artifact(bundle):
    pointer = bundle["pointer"]
    assert pointer["authoritative_protocol"] == EXPECTED_AUTHORITATIVE_PROTOCOL
    assert pointer["alternative_authoritative_artifacts"] == []
    assert pointer["runtime_overlay_permitted"] is False
    assert pointer["fallback_protocol_permitted"] is False
    for legacy in pointer["legacy_pointers_not_consulted"]:
        assert legacy.startswith("studies/study3/")
    assert "v0_5" not in json.dumps(bundle["protocol"])
    assert "v0_6" not in json.dumps(bundle["protocol"])
    assert "v0_7" not in json.dumps(bundle["protocol"])


def test_the_bundle_declares_no_unresolved_value(bundle):
    payload = json.dumps(bundle["protocol"])
    assert "TBD" not in payload
    assert "to_be_determined" not in payload
    assert re.search(r'"[A-Za-z_]*_tbd"', payload) is None
    assert bundle["protocol"]["statistics"]["unresolved_values"] == []


def test_the_task_generators_refuse_to_realize_a_bank_before_authorization():
    sys.path.insert(0, str(TASKS_DIR))
    try:
        import study3r_task_generators_v1 as tasks
    finally:
        sys.path.remove(str(TASKS_DIR))
    with pytest.raises(tasks.Study3RExecutionNotAuthorizedError):
        tasks.realize_bank("D2_D3_TARGET_BANK", "D2", 4)
    with pytest.raises(tasks.Study3RExecutionNotAuthorizedError):
        tasks.realize_bank("D2_D3_TARGET_BANK", "D2", 4,
                           formal_execution_authorized=True)
    fixtures = tasks.tokenizer_fixtures()
    assert len(fixtures) == 6
    assert all(item["is_scientific_item"] is False for item in fixtures)
    assert len({item["item_key"] for item in fixtures}) == len(fixtures)


def test_the_negative_control_family_never_exposes_a_derivable_option():
    sys.path.insert(0, str(TASKS_DIR))
    try:
        import study3r_task_generators_v1 as tasks
    finally:
        sys.path.remove(str(TASKS_DIR))
    negative = [item for item in tasks.tokenizer_fixtures()
                if item["family"] == tasks.NEGATIVE_CONTROL_FAMILY]
    assert negative
    for item in negative:
        assert item["value"] not in item["options"]
    with pytest.raises(tasks.Study3RItemIneligibleError):
        tasks.check_eligibility("NEG", 7, [7, 1, 2, 3], 0)


def test_the_authoring_disclosure_validates_against_its_schema():
    jsonschema = pytest.importorskip("jsonschema")
    document = _json(STUDY3R / "study3r_authoring_disclosure_v1.json")
    schema = _json(STUDY3R / "study3r_authoring_disclosure_v1.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(document, schema)


def test_the_authoring_disclosure_reports_the_registered_design():
    document = _json(STUDY3R / "study3r_authoring_disclosure_v1.json")
    assert document["terminal_state"] == EXPECTED_AUTHORED_STATE
    assert document["target_checkpoint"] == EXPECTED_TARGET
    assert tuple(document["rp_b_ladder"]) == EXPECTED_LADDER
    assert document["rp_b_ladder_length"] == EXPECTED_LADDER_LENGTH
    assert document["census"]["m_max"] == EXPECTED_M_MAX
    assert document["mutations"]["survivor_count"] == 0
    assert document["mutations"]["registered_count"] == len(MUTATIONS)
    assert sorted(document["mutations"]["registered"]) == sorted(
        mutation[0] for mutation in MUTATIONS)
    assert document["independent_recalculation"]["exact_agreement"] is True
    assert document["protected_bytes"]["all_identical"] is True
    assert document["boundary"]["formal_execution_authorized"] is False
    assert document["boundary"]["evidence_ledger_rows_written"] == 0
    assert document["test_results"]["final_head"]["new_failure_node_ids"] == []
    assert document["test_results"]["baseline"]["failed"] == 8
    assert document["authority_identity"][
        "published_alone_as_the_first_commit_after_the_starting_state"] is True
    assert document["starting_state"]["commit"] == STARTING_COMMIT
    assert document["starting_state"]["tree"] == STARTING_TREE
    for role in EXPECTED_ROLES:
        recorded = [row for row in document["checkpoints"]
                    if row["role"] == role][0]
        assert recorded["immutable_revision"] == EXPECTED_REVISIONS[role]


def test_the_study3r_readme_routes_to_the_authored_candidate():
    text = (STUDY3R / "README.md").read_text(encoding="utf-8")
    assert EXPECTED_AUTHORED_STATE in text
    assert "protocol/study3r_protocol_current.json" in text
    assert "protocol/study3r_protocol_v1.json" in text
    assert "AUTHORING_DISCLOSURE.md" in text
    assert "one independent focused methods review" in text
    assert "formal_execution_authorized" in text
    banner = text.splitlines()[2]
    assert EXPECTED_AUTHORED_STATE in banner


def test_the_authoring_disclosure_markdown_matches_the_machine_readable_form():
    document = _json(STUDY3R / "study3r_authoring_disclosure_v1.json")
    text = (STUDY3R / "AUTHORING_DISCLOSURE.md").read_text(encoding="utf-8")
    assert document["terminal_state"] in text
    assert document["starting_state"]["commit"] in text
    assert document["starting_state"]["tree"] in text
    assert document["authority_identity"]["sha256"] in text
    assert document["manifest"]["aggregate_sha256"] in text
    for role in EXPECTED_ROLES:
        assert EXPECTED_REVISIONS[role] in text
    for node in document["test_results"]["baseline"]["failure_node_ids"]:
        assert node in text


# ---------------------------------------------------------------------------
# 4. Coordinated generator-mutation tests
# ---------------------------------------------------------------------------

def test_the_registered_mutation_set_covers_every_required_category():
    registered = [mutation[0] for mutation in MUTATIONS]
    assert len(registered) == len(set(registered))
    assert set(REQUIRED_MUTATION_CATEGORIES) <= set(registered)
    assert len(registered) >= 15


@pytest.fixture(scope="module")
def mutation_report(tmp_path_factory):
    """Apply every registered mutation once, rebuild, and record the outcome."""
    report = {}
    for index, (mutation_id, relative, old, new) in enumerate(MUTATIONS):
        staged = _stage(tmp_path_factory.mktemp("s3rm%02d" % index))
        _apply(staged, relative, old, new)
        try:
            _rebuild(staged)
        except RuntimeError as error:
            report[mutation_id] = {"killed": True,
                                   "killed_by": "rebuild_failure",
                                   "detail": str(error)[-400:]}
            continue
        try:
            validate_bundle(staged)
        except AssertionError as error:
            report[mutation_id] = {"killed": True,
                                   "killed_by": "semantic_validation",
                                   "detail": str(error)}
            continue
        report[mutation_id] = {"killed": False, "killed_by": None,
                               "detail": None}
    return report


def test_the_unmutated_staged_bundle_is_accepted(tmp_path):
    staged = _stage(tmp_path / "control")
    _rebuild(staged)
    validate_bundle(staged)


@pytest.mark.parametrize("mutation_id", [mutation[0] for mutation in MUTATIONS])
def test_every_coordinated_mutation_is_killed_by_semantic_validation(
        mutation_id, mutation_report):
    entry = mutation_report[mutation_id]
    assert entry["killed"] is True, (mutation_id, entry)
    assert entry["killed_by"] == "semantic_validation", (mutation_id, entry)


def test_the_mutation_survivor_count_is_zero(mutation_report):
    assert len(mutation_report) == len(MUTATIONS)
    survivors = sorted(mutation_id for mutation_id, entry
                       in mutation_report.items() if not entry["killed"])
    assert survivors == [], survivors
