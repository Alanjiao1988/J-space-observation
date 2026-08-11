"""Emit and verify the Study 3 P0-R1 protocol, state machine and receipt.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections 6,
7 and 10.

The protocol document and the pre-execution receipt are generated rather than
hand-maintained, so the caps, the state machine, the pinned identities, the
counter ontology and the bound code blobs cannot drift apart from the code that
enforces them. The registration tests and the authoritative CPU validation both
run ``--check``.

Usage::

    python p0_r1_protocol.py --write
    python p0_r1_protocol.py --check
"""

import argparse
import hashlib
import json
import os
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))

sys.path.insert(0, P0_R1_DIR)

import p0_r1_eligibility as ELIG  # noqa: E402
import p0_r1_factorization as FACT  # noqa: E402
from p0_r1_counters import CAPS, SMOKE_EXACT, ontology_document  # noqa: E402

PROTOCOL_PATH = os.path.join(P0_R1_DIR, "p0_r1_protocol.json")
RECEIPT_PATH = os.path.join(P0_R1_DIR, "p0_r1_pre_execution_receipt.json")

SCHEMA_VERSION = "study3-p0-r1-continuation-protocol-v1"
RECEIPT_SCHEMA_VERSION = "study3-p0-r1-pre-execution-receipt-v1"

AUTHORITY_REPO_PATH = (
    "studies/study3/prompts/study3_v0_6_p0_r1_authority.md")
AUTHORITY_BYTES = 19632
AUTHORITY_SHA256 = (
    "f72292e75ebf128e90c5cd73588786afa11d9f156f37392a9a9200845ddc19d2")

REGISTRY_REPO_PATH = (
    "studies/study3/protocol/interface_calibration_rendering_registry_v0_6.json")
REGISTRY_SCHEMA_REPO_PATH = (
    "studies/study3/protocol/"
    "interface_calibration_rendering_registry_v0_6.schema.json")

REGISTERED_STATE = "STUDY3_P0_R1_REGISTERED_AWAITING_REPLAY_GATE"

# Section 4. The tokenizer of each role is loaded from the same repository
# identity and the same immutable revision as its model. These are the exact
# identities P0-T recorded; they are re-read from the immutable result rather
# than restated here.
ROLE_ORDER = ("RT", "RL", "RI")

STATES = (
    {
        "state": REGISTERED_STATE,
        "kind": "waypoint",
        "entered_when": (
            "the draft-v0.6 candidate and the P0-R1 package are published by "
            "non-force fast-forward and HEAD equals origin/main with the "
            "recorded tree and a clean worktree"),
        "permits": [
            "one fresh successor session continuing from this exact published "
            "registration commit",
        ],
        "forbids": [
            "the replay gate in the calibration session",
            "constructing a tokenizer",
            "downloading a checkpoint",
            "allocating a GPU",
            "beginning the model pilot",
        ],
    },
    {
        "state": "STUDY3_P0_R1_REPLAY_GATE_PASSED_AWAITING_MODEL_PILOT",
        "kind": "waypoint",
        "entered_when": (
            "the replay-only factorization gate verifies all five conditions of "
            "section 3.2 and the corrected eligibility matrix from immutable "
            "source artifacts, performing zero new encodes"),
        "permits": [
            "one Azure containerized GPU job running the repaired model pilot, "
            "one checkpoint at a time",
        ],
        "forbids": ["merging or rebasing during an active measurement round"],
    },
    {
        "state": "STUDY3_P0_R1_STOPPED_ON_REPLAY_FACTORIZATION_DEFECT",
        "kind": "terminal",
        "entered_when": (
            "the replay-only gate cannot verify the factorization or the "
            "corrected eligibility matrix from the immutable artifacts"),
        "on_entry": (
            "publish a registered stop and perform no model operation. Do not "
            "repair and rerun."),
    },
    {
        "state": ELIG.STOP_SOME_ROLE_HAS_NO_EXECUTABLE_CONTRAST,
        "kind": "terminal",
        "entered_when": ELIG.STOP_LABEL_SEMANTICS,
        "semantics": ELIG.STOP_LABEL_SEMANTICS,
        "supersedes_label": ELIG.HISTORICAL_STOP_LABEL,
        "supersedes_label_status": ELIG.HISTORICAL_STOP_LABEL_STATUS,
    },
    {
        "state": "STUDY3_P0_R1_COMPLETE_MECHANICALLY_FEASIBLE",
        "kind": "terminal",
        "entered_when": (
            "the replay gate passes, every executed row is complete and "
            "mechanically valid, S1/S2/S3 scoring and S3 reuse reconcile, the "
            "S4 diagnostic path executes, and the resource and counter records "
            "are complete"),
    },
    {
        "state": ("STUDY3_P0_R1_COMPLETE_MECHANICALLY_FEASIBLE_"
                  "EMPIRICALLY_LOW_INFORMATION"),
        "kind": "terminal",
        "entered_when": (
            "every mechanical condition passes but the tiny corpus shows a "
            "globally degenerate prediction pattern or another explicitly "
            "descriptive low-information pattern"),
    },
    {
        "state": "STUDY3_P0_R1_STOPPED_ON_MODEL_SMOKE_MECHANICAL_FAILURE",
        "kind": "terminal",
        "entered_when": "the smoke mechanical gate fails after any model operation",
    },
    {
        "state": "STUDY3_P0_R1_INCONCLUSIVE_INFRASTRUCTURE_OR_TRANSPORT_FAILURE",
        "kind": "terminal",
        "entered_when": (
            "an infrastructural or transport failure prevents the round from "
            "reaching a mechanical determination"),
    },
    {
        "state": "STUDY3_P0_R1_BLOCKED_ON_AUTHORITY_OR_REPOSITORY_INTEGRITY",
        "kind": "terminal",
        "entered_when": (
            "the starting state, the protected bytes, the authority identity or "
            "the publication path cannot be established exactly"),
    },
)

TRANSITIONS = (
    {
        "from": "BLOCKED_ON_STUDY3_V0_6_STARTING_STATE_INTEGRITY",
        "to": REGISTERED_STATE,
        "guard": (
            "origin/main equals the required baseline commit and tree, the "
            "worktree is clean, the authority copy is byte-identical and is the "
            "first new repository object, the frozen corpus reproduces, every "
            "protected byte is unchanged, all P0-R1 counters are zero, and the "
            "registration commit publishes by non-force fast-forward"),
        "fail_closed_to": "STUDY3_P0_R1_BLOCKED_ON_AUTHORITY_OR_REPOSITORY_INTEGRITY",
    },
    {
        "from": REGISTERED_STATE,
        "to": "STUDY3_P0_R1_REPLAY_GATE_PASSED_AWAITING_MODEL_PILOT",
        "guard": (
            "in a new session continuing from the exact published registration "
            "commit, the replay-only factorization gate verifies, from immutable "
            "source artifacts and with zero new encodes, all five conditions of "
            "section 3.2 and the corrected eligibility matrix, and at least one "
            "eligible genuine gate-bearing I3 contrast remains for each of RT, "
            "RL and RI"),
        "fail_closed_to": "STUDY3_P0_R1_STOPPED_ON_REPLAY_FACTORIZATION_DEFECT",
        "also_fail_closed_to": ELIG.STOP_SOME_ROLE_HAS_NO_EXECUTABLE_CONTRAST,
    },
    {
        "from": "STUDY3_P0_R1_REPLAY_GATE_PASSED_AWAITING_MODEL_PILOT",
        "to": "STUDY3_P0_R1_COMPLETE_MECHANICALLY_FEASIBLE",
        "guard": (
            "the K2 smoke mechanical gate passes, the bounded extension runs "
            "without crossing a cap, and every mechanical, accounting and "
            "resource record is complete"),
        "fail_closed_to": "STUDY3_P0_R1_STOPPED_ON_MODEL_SMOKE_MECHANICAL_FAILURE",
    },
)

PROHIBITIONS = (
    "any development, confirmation or P3-Q seed or bank",
    "any access to existing or future confirmation material",
    "any formal Gate I0-I5 pass/fail, selection-map run, winner, interface "
    "preference or confirmation release",
    "any use of draft-v0.6's 413/214/448 sample sizes as pilot allocations",
    "any change to alpha, power, floors, claims, estimands, m_max or the formal "
    "operation projection",
    "any choice or inspection of RP, any resolution of OD2 or UR-22",
    "any reuse of Study 1/2 item identities, banks, seeds, confirmation data or "
    "empirical results as P0-R1 inputs",
    "any edit to any byte under studies/study3/pilot/p0/ or to "
    "tests/test_study3_p0_feasibility_pilot.py",
    "any prompt, parser, scoring, tokenizer, item, allocation, checkpoint or "
    "dependency change after the registration publication in response to an "
    "observed result",
    "any reroll, output-conditioned retry, cherry-picking, row replacement, "
    "exclusion of a valid but inconvenient row, or reset of a cumulative counter",
    "any quantization, hosted-provider inference, unpinned revision or local "
    "workstation model execution",
    "any activation extraction, hook, lens, probe, patch, intervention or "
    "ablation",
    "any entry in paper/evidence_ledger.csv",
    "any claim that P0-R1 answers the original research question or validates "
    "draft-v0.6",
    "any direct transition from P0-R1 to formal development or confirmation",
)

AUTHORIZED_WRITE_PATHS = (
    "studies/study3/prompts/study3_v0_6_p0_r1_authority.md",
    "studies/study3/pilot/p0_r1/",
    "studies/study3/protocol/interface_calibration_rendering_registry_v0_6.json",
    "studies/study3/protocol/"
    "interface_calibration_rendering_registry_v0_6.schema.json",
    "studies/study3/protocol/interface_calibration_protocol_draft.json",
    "studies/study3/protocol/interface_calibration_protocol_draft.md",
    "studies/study3/protocol/interface_calibration_protocol.schema.json",
    "studies/study3/reviews/v0_6_operator_amendment.json",
    "studies/study3/reviews/v0_6_operator_amendment.md",
    "studies/study3/reviews/v0_6_operator_amendment.schema.json",
    "studies/study3/design_receipt_v0_6.json",
    "studies/study3/design_receipt_v0_6.py",
    "studies/study3/analysis/scoring_boundary_v0_6.py",
    "studies/study3/analysis/scoring_boundary_v0_6_tables.json",
    "studies/study3/analysis/p0_r1_corrected_eligibility_tables.json",
    "studies/study3/analysis/final_focused_review_packet_v0_6.md",
    "tests/test_study3_rendering_registry_v0_6.py",
    "tests/test_study3_p0_r1_registration.py",
    "README.md",
    "docs/decision_log.md",
    "docs/run_log.md",
    "paper/artifact_index.csv",
    "paper/methods_ledger.md",
    "reports/current_status.md",
    "studies/study3/README.md",
    "studies/study3/NEXT_THREAD_HANDOFF.md",
    "studies/study3/RESEARCH_CHARTER_DRAFT.md",
)

BYTE_PROTECTED_PATHS = (
    "studies/study3/pilot/p0/results/p0-t/p0_tokenizer_gate_result.json",
    "studies/study3/pilot/p0/results/p0-t/p0_tokenizer_gate_receipt.json",
    "studies/study3/pilot/p0/results/p0-t/P0_T_DISPOSITION.md",
    "studies/study3/pilot/p0/corpus/p0_corpus.json",
    "studies/study3/pilot/p0/corpus/p0_corpus_manifest.json",
    "studies/study3/pilot/p0/corpus/p0_corpus_census.md",
    "studies/study3/pilot/p0/p0_corpus.py",
    "studies/study3/pilot/p0/p0_counters.py",
    "studies/study3/pilot/p0/p0_freeze_corpus.py",
    "studies/study3/pilot/p0/p0_image_verify.py",
    "studies/study3/pilot/p0/p0_model_pilot.py",
    "studies/study3/pilot/p0/p0_parser.py",
    "studies/study3/pilot/p0/p0_protocol.json",
    "studies/study3/pilot/p0/p0_protocol.py",
    "studies/study3/pilot/p0/p0_renderer.py",
    "studies/study3/pilot/p0/p0_summarize.py",
    "studies/study3/pilot/p0/p0_tokenizer_gate.py",
    "studies/study3/pilot/p0/p0_transport.py",
    "studies/study3/pilot/p0/p0_validate.py",
    "studies/study3/pilot/p0/README.md",
    "studies/study3/pilot/p0/container/Dockerfile.study3-p0",
    "studies/study3/pilot/p0/container/p0_t_acr_task.yaml",
    "studies/study3/pilot/p0/container/p0_t_checkout.sh",
    "studies/study3/pilot/p0/container/p0_t_stage.sh",
    "studies/study3/pilot/p0/container/requirements-study3-p0.txt",
    "tests/test_study3_p0_feasibility_pilot.py",
    "studies/study3/protocol/interface_calibration_rendering_registry_v0_5.json",
    "studies/study3/protocol/"
    "interface_calibration_rendering_registry_v0_5.schema.json",
    "studies/study3/reviews/v0_5_operator_amendment.json",
    "studies/study3/reviews/v0_5_operator_amendment.md",
    "studies/study3/reviews/v0_5_operator_amendment.schema.json",
    "studies/study3/design_receipt_v0_5.json",
    "studies/study3/analysis/independent_methods_review_packet_v0_5.md",
    "studies/study3/analysis/design_statistics.py",
    "studies/study3/analysis/design_statistics_tables.json",
    "studies/study3/prompts/study3_p0_feasibility_pilot_authority.md",
    "studies/study3/prompts/study3_v0_5_design_amendment_authority.md",
    "tests/test_study3_design.py",
    "tests/test_study3_rendering_registry_v0_5.py",
    "tests/test_study3_methods_review.py",
    "tests/test_study3_methods_review_v0_3.py",
    "tests/test_study3_methods_review_v0_4.py",
    "paper/evidence_ledger.csv",
)

# The code blobs the pre-execution receipt binds. Section 6 requires the receipt
# to bind the code as well as the data.
BOUND_CODE_BLOBS = (
    "studies/study3/pilot/p0_r1/p0_r1_counters.py",
    "studies/study3/pilot/p0_r1/p0_r1_eligibility.py",
    "studies/study3/pilot/p0_r1/p0_r1_factorization.py",
    "studies/study3/pilot/p0_r1/p0_r1_model_runner.py",
    "studies/study3/pilot/p0_r1/p0_r1_protocol.py",
    "studies/study3/pilot/p0_r1/p0_r1_replay_gate.py",
    "studies/study3/pilot/p0_r1/p0_r1_schemas.py",
    "studies/study3/pilot/p0_r1/p0_r1_summarize.py",
    "studies/study3/pilot/p0_r1/p0_r1_validate.py",
    "studies/study3/pilot/p0_r1/container/Dockerfile.study3-p0-r1",
    "studies/study3/pilot/p0_r1/container/requirements-study3-p0-r1.txt",
    "studies/study3/pilot/p0_r1/container/p0_r1_acr_task.yaml",
    "studies/study3/pilot/p0_r1/container/p0_r1_replay.sh",
    "studies/study3/analysis/scoring_boundary_v0_6.py",
)


def blob_identity(repo_relative_path):
    path = os.path.join(REPO_ROOT, *repo_relative_path.split("/"))
    if not os.path.exists(path):
        return {"path": repo_relative_path, "bytes": None, "sha256": None,
                "present": False}
    with open(path, "rb") as handle:
        raw = handle.read()
    return {
        "path": repo_relative_path,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "present": True,
        "carries_cr": b"\r" in raw,
    }


def authority_identity():
    identity = blob_identity(AUTHORITY_REPO_PATH)
    identity["registered_bytes"] = AUTHORITY_BYTES
    identity["registered_sha256"] = AUTHORITY_SHA256
    identity["byte_identical"] = (
        identity.get("bytes") == AUTHORITY_BYTES
        and identity.get("sha256") == AUTHORITY_SHA256)
    identity["lf_only"] = identity.get("carries_cr") is False
    return identity


def role_identities():
    result = FACT.load_immutable(FACT.RESULT_PATH)
    identities = result["tokenizer_identities"]
    out = []
    for role in ROLE_ORDER:
        entry = identities[role]
        out.append({
            "role": role,
            "repository_identity": entry["repository_identity"],
            "immutable_revision": entry["resolved_revision"],
            "tokenizer_class": entry["tokenizer_class"],
            "vocabulary_size": entry["vocabulary_size"],
            "len_tokenizer": entry["len_tokenizer"],
            "trust_remote_code": False,
            "source": (
                "read back from the immutable published P0-T result; not "
                "restated by hand"),
        })
    return out


def build_document():
    return {
        "schema_version": SCHEMA_VERSION,
        "document_class": "study3_p0_r1_continuation_protocol",
        "authority": authority_identity(),
        "state": REGISTERED_STATE,
        "legal_status": {
            "formal_execution_authorized": False,
            "p0_r1_pilot_execution_authorized": True,
            "p0_r1_pilot_execution_consumed": False,
            "draft_v0_6_frozen": False,
            "draft_v0_6_reviewed": False,
            "draft_v0_6_status": (
                "candidate protocol that has not received the final focused "
                "methods review; P0-R1 does not declare it correct and does not "
                "waive that review"),
            "od2_status": "unresolved",
            "ur22_status": "unresolved",
            "rp_status": (
                "excluded; no positive-reference object is selected or touched"),
            "interface_selected": None,
            "evidence_ledger_last_row": "EV-0016",
            "evidence_ledger_policy":
                "byte-identical; P0-R1 writes no evidence row",
        },
        "supersedes": {
            "round": "the consumed Study 3-P0 feasibility pilot",
            "namespace": "studies/study3/pilot/p0/",
            "namespace_status": (
                "immutable. Every byte of the consumed P0 namespace, including "
                "its result, receipt, disposition and counters, remains "
                "historical truth and is never edited, replaced, relabelled or "
                "rerun."),
            "historical_terminal_state": ELIG.HISTORICAL_STOP_LABEL,
            "historical_terminal_state_status": (
                "not rewritten. The published disposition already discloses "
                "that it was over-severe."),
        },
        "scientific_purpose": [
            "does the repaired first-discriminative-token factorization verify "
            "from the immutable P0-T evidence with zero new encodes",
            "does the repaired eligibility classifier compute at the narrowest "
            "applicable key without cross-profile, cross-role or cross-contrast "
            "propagation",
            "can S1, S2 and CPU-only S3 be executed and reconciled under the "
            "draft-v0.6 scoring boundary without missing rows, non-finite "
            "values, scorer disagreement or hidden evaluations",
            "can the S4 diagnostic path render, wrap, generate, parse, retain "
            "unparseable output and account for its cost",
            "what wall time, peak device memory, prompt-token length, "
            "scoring-context token length, generated-token count, failure rate "
            "and runtime batching occur",
        ],
        "non_purpose": [
            "no confirmatory effect size, power validation or null test",
            "no formal gate pass or fail",
            "no selection or ranking of S1, S2 or S3 and no qualification of S4",
            "no scientific checkpoint comparison",
            "no answer to the original research question",
            "pilot observations may never justify a threshold, sample size, "
            "alpha, seed, bank, profile or confirmation rule",
        ],
        "roles": role_identities(),
        "rp_excluded": True,
        "corpus": {
            "namespace": "study3-p0-only",
            "path": "studies/study3/pilot/p0/corpus/p0_corpus.json",
            "reuse_rule": (
                "P0-R1 reuses the exact frozen 35-cell / 70-member P0 corpus and "
                "its hashes. No row, member, tuple, prompt, rendering, answer, "
                "nuisance state, allocation or ground truth may be added, "
                "removed, replaced or edited."),
            "row_count": 35,
            "member_count": 70,
            "permanent_exclusion": (
                "the complete study3-p0-only/ namespace and every semantic tuple "
                "used by the pilot are permanently excluded from every formal "
                "development, confirmation, P3-Q and external-validity bank"),
        },
        "scoring_boundary": {
            "registry": REGISTRY_REPO_PATH,
            "registry_schema": REGISTRY_SCHEMA_REPO_PATH,
            "rule": "first-discriminative-token restricted argmax for S2/S3",
            "s1_rule_unchanged": True,
            "s4_rule_unchanged": True,
            "common_prefix_is_teacher_forced_not_generated": True,
            "common_prefix_is_not_a_separate_sequence_level_evaluation": True,
            "equivalence": FACT.equivalence_identity(),
        },
        "eligibility": {
            "classifier_version": ELIG.CLASSIFIER_VERSION,
            "keys": {
                "candidate_surface_eligibility": "role x profile",
                "presentation_pair_distinctness": "role x profile x contrast",
                "structural_absence": "profile x contrast",
                "target_role_executability": "role",
            },
            "s4_is_diagnostic_only": True,
            "not_applicable_semantics": (
                "structural absence. It can never become eligible, ineligible, "
                "a pass, a zero, a denominator row or robustness evidence."),
            "an_ineligible_row_must_carry_a_local_reason": True,
            "no_propagation": [
                "a failure in S1 never propagates to S2 or S3",
                "a failure in S2 or S3 never propagates to S1",
                "a failure in one role never propagates to another role",
                "one contrast's collision never propagates to an unrelated "
                "contrast",
            ],
            "stop_label": ELIG.STOP_SOME_ROLE_HAS_NO_EXECUTABLE_CONTRAST,
            "stop_label_semantics": ELIG.STOP_LABEL_SEMANTICS,
            "historical_stop_label": ELIG.HISTORICAL_STOP_LABEL,
            "historical_stop_label_status": ELIG.HISTORICAL_STOP_LABEL_STATUS,
        },
        "execution_route": {
            "workstation_permitted": [
                "code inspection", "editing", "git", "hashes", "upload",
                "submission", "result reading",
            ],
            "authoritative_cpu_validation": (
                "the registered Azure Container Registry/container route on a "
                "clean exact-commit checkout"),
            "model_operations": (
                "an Azure containerized GPU job only; never on the workstation "
                "and never in GitHub Actions"),
            "gpu_class": "one T4-class 16 GiB GPU or a larger compatible Azure GPU",
            "precision": "fp16, one checkpoint at a time",
            "prohibited": [
                "quantization", "mixed checkpoint revisions", "model conversion",
                "adapter insertion", "remote hosted inference APIs",
                "local workstation model execution",
            ],
            "image_pinning": (
                "the container image is frozen by immutable digest and Python, "
                "PyTorch, Transformers, tokenizer, CUDA and supporting package "
                "versions are pinned before the first tokenizer call"),
            "trust_remote_code": False,
        },
        "inference_behaviour": {
            "evaluation_mode": True,
            "inference_mode": "torch.inference_mode() or its exact equivalent",
            "sampling": False,
            "gradients": False,
            "adapters": False,
            "quantization": False,
            "s1_reads": (
                "next-token logits for the four registered label token IDs at "
                "the single position after the registered prompt"),
            "s2_reads": (
                "next-token logits for the ten verified discriminant token IDs "
                "at the single position after the teacher-forced common prefix"),
            "s3": (
                "CPU-only scoring from the already captured S2 "
                "discriminant-position vector; exactly zero prefill, decode, "
                "model-load or forward operations"),
            "s4": {
                "wrapper": "each role's registered native-wrapper policy",
                "decoding": "greedy",
                "do_sample": False,
                "max_new_tokens": 4,
                "temperature": "not passed",
                "unparseable": (
                    "an explicit retained outcome; never dropped and never "
                    "imputed"),
            },
            "never_collect": [
                "hidden states", "activations", "attentions", "gradients",
                "hooks", "lens outputs", "probes", "patches", "ablations",
            ],
        },
        "counter_ontology": ontology_document(),
        "caps": dict(CAPS),
        "smoke_exact_allocation": dict(SMOKE_EXACT),
        "allocation": {
            "non_generative_prefill_evaluations_in_the_k2_smoke": 60,
            "automatic_extension_upper_bound_prefills": 180,
            "s4_generations": 12,
            "s4_max_new_tokens_each": 4,
            "total_sequence_level_model_evaluation_equivalents_upper_bound": 228,
            "s1_scored_rows": 162,
            "s2_scored_rows": 18,
            "s3_cpu_reuse_scored_rows": 18,
            "s4_scored_rows": 12,
            "total_scored_rows": 210,
            "the_common_prefix_changes_token_processing_not_evaluations": True,
        },
        "state_machine": {
            "states": list(STATES),
            "transitions": list(TRANSITIONS),
            "terminal_dispositions": [
                state["state"] for state in STATES if state["kind"] == "terminal"
            ],
        },
        "prohibitions": list(PROHIBITIONS),
        "authorized_write_paths": list(AUTHORIZED_WRITE_PATHS),
        "byte_protected_paths": list(BYTE_PROTECTED_PATHS),
        "retry_rule": {
            "output_conditioned_retry": False,
            "zero_operation_infrastructure_retry": (
                "permitted once only when a signed job receipt proves that zero "
                "tokenizer, model-load, prefill, decode, scoring and generation "
                "operations occurred"),
        },
        "evidence_status": (
            "methods-feasibility observations only; never Study 3 evidence and "
            "never an entry in paper/evidence_ledger.csv"),
    }


def build_receipt():
    """The pre-execution receipt of section 6."""
    protocol = build_document()
    sources = FACT.verify_immutable_sources()
    registry = _load_json(REGISTRY_REPO_PATH)
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "document_class": "study3_p0_r1_pre_execution_receipt",
        "state": REGISTERED_STATE,
        "authority": authority_identity(),
        "draft_v0_6_candidate": {
            "registry": blob_identity(REGISTRY_REPO_PATH),
            "registry_schema": blob_identity(REGISTRY_SCHEMA_REPO_PATH),
            "registry_sha256_self_hash":
                registry["registry_identity"]["registry_sha256"],
            "draft_version": registry["draft_version"],
            "state": registry["state"],
            "disposition_status": registry["disposition_status"],
            "frozen": False,
            "reviewed": False,
        },
        "corpus": {
            "path": "studies/study3/pilot/p0/corpus/p0_corpus.json",
            "identity": blob_identity(
                "studies/study3/pilot/p0/corpus/p0_corpus.json"),
            "manifest": blob_identity(
                "studies/study3/pilot/p0/corpus/p0_corpus_manifest.json"),
            "row_count": 35,
            "member_count": 70,
            "reused_unchanged": True,
        },
        "p0_t_source_artifacts": sources,
        "model_and_tokenizer_revisions": protocol["roles"],
        "container": _container_identity(),
        "code_blobs": [blob_identity(path) for path in BOUND_CODE_BLOBS],
        "counters": {
            "p0_r1_before_execution": {name: 0 for name in sorted(CAPS)},
            "historical_p0_t_snapshot":
                FACT.load_immutable(FACT.RESULT_PATH)["counters"],
            "historical_snapshot_is_immutable": True,
        },
        "caps": dict(CAPS),
        "authority_flags": {
            "frozen": False,
            "formal_execution_authorized": False,
            "draft_v0_6_reviewed": False,
            "draft_v0_6_selected": False,
            "positive_reference_selected": False,
            "seed_authorized": False,
            "bank_authorized": False,
            "confirmation_access_authorized": False,
            "winner_selected": False,
            "od2_resolved": False,
            "ur22_resolved": False,
            "rp_selected": False,
            "evidence_row_written": False,
            "selection_map_run": False,
            "interface_selected": None,
            "positive_reference": None,
            "rp_wrapper": None,
            "p0_r1_pilot_execution_authorized": True,
            "p0_r1_pilot_execution_consumed": False,
            "evidence_ledger_last_row": "EV-0016",
        },
        "operations_in_the_calibration_session": {
            "tokenizer_constructions": 0,
            "tokenizer_encodes": 0,
            "checkpoint_downloads": 0,
            "model_weight_loads": 0,
            "gpu_allocations": 0,
            "forward_passes": 0,
            "generations": 0,
            "scored_rows": 0,
            "replay_gates_performed": 0,
            "seeds_drawn": 0,
            "bank_rows_written": 0,
            "evidence_rows_added": 0,
        },
        "claim_boundary": (
            "a registration receipt. It binds bytes and boundaries. It selects "
            "no interface, passes no formal gate, estimates no effect, resolves "
            "neither OD2 nor UR-22, freezes nothing and answers no research "
            "question."),
    }


def _container_identity():
    return {
        "definition": blob_identity(
            "studies/study3/pilot/p0_r1/container/Dockerfile.study3-p0-r1"),
        "requirements": blob_identity(
            "studies/study3/pilot/p0_r1/container/"
            "requirements-study3-p0-r1.txt"),
        "acr_task": blob_identity(
            "studies/study3/pilot/p0_r1/container/p0_r1_acr_task.yaml"),
        "replay_entrypoint": blob_identity(
            "studies/study3/pilot/p0_r1/container/p0_r1_replay.sh"),
        "image_digest": None,
        "image_digest_status": (
            "null until the successor session builds the image. It is not zero, "
            "not empty and not a placeholder digest."),
    }


def _load_json(repo_relative_path):
    path = os.path.join(REPO_ROOT, *repo_relative_path.split("/"))
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def canonical_bytes(document):
    return (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True)
            + "\n").encode("utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    targets = (
        (PROTOCOL_PATH, build_document(), "the P0-R1 protocol"),
        (RECEIPT_PATH, build_receipt(), "the P0-R1 pre-execution receipt"),
    )
    if args.write:
        for path, document, _ in targets:
            with open(path, "wb") as handle:
                handle.write(canonical_bytes(document))
            print("wrote %s"
                  % os.path.relpath(path, REPO_ROOT).replace(os.sep, "/"))
        return 0

    findings = []
    for path, document, label in targets:
        if not os.path.exists(path):
            findings.append("%s is missing" % label)
            continue
        with open(path, "rb") as handle:
            if handle.read() != canonical_bytes(document):
                findings.append("%s does not reproduce from code" % label)
    if findings:
        print("P0-R1 PROTOCOL CHECK FAILED")
        for finding in findings:
            print("  FAIL %s" % finding)
        return 1
    print("P0-R1 protocol: OK")
    print("  state     : %s" % REGISTERED_STATE)
    print("  authority : %d bytes, sha256 %s" % (AUTHORITY_BYTES,
                                                 AUTHORITY_SHA256))
    return 0


if __name__ == "__main__":
    sys.exit(main())
