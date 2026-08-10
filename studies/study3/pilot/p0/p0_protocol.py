"""Emit and verify the machine-readable Study 3-P0 protocol and state machine.

Authority: ``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md``.

The protocol document is generated rather than hand-maintained so that the caps,
the state machine, the fixed checkpoint identities and the counter ontology
cannot drift apart from the code that enforces them. The P0 test module and the
ACR validation both run ``--check``.

Usage::

    python p0_protocol.py --write
    python p0_protocol.py --check
"""

import argparse
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p0_corpus import (  # noqa: E402
    K5_CONTRASTS,
    K6_CONTRASTS,
    NAMESPACE,
    PROFILE_ALLOCATION,
    TUPLE_CLASSES,
    canonical_bytes,
)
from p0_counters import CAPS, SMOKE_EXACT, ontology_document  # noqa: E402
from p0_renderer import REPO_ROOT  # noqa: E402

P0_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOCOL_PATH = os.path.join(P0_DIR, "p0_protocol.json")

SCHEMA_VERSION = "study3-p0-feasibility-pilot-protocol-v1"

AUTHORITY_PATH = os.path.join(
    REPO_ROOT, "studies", "study3", "prompts",
    "study3_p0_feasibility_pilot_authority.md")

# Section 4. The tokenizer of each role is loaded from the same repository
# identity and the same immutable revision as its model.
ROLES = (
    {
        "role": "RT",
        "repository_identity": "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        "immutable_revision": "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562",
    },
    {
        "role": "RL",
        "repository_identity": "Qwen/Qwen2.5-Math-1.5B",
        "immutable_revision": "4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2",
    },
    {
        "role": "RI",
        "repository_identity": "Qwen/Qwen2.5-Math-1.5B-Instruct",
        "immutable_revision": "aafeb0fc6f22cbf0eaeed126eff8be45b0360a35",
    },
)

STATES = (
    {
        "state": "STUDY3_P0_REGISTERED_AWAITING_TOKENIZER_GATE",
        "kind": "waypoint",
        "entered_when": (
            "the pre-execution commit is published by non-force fast-forward and "
            "HEAD equals origin/main with the recorded tree and a clean worktree"),
        "permits": ["stage P0-T, CPU only, in the registered Azure container route"],
        "forbids": ["every model operation", "every GPU job"],
    },
    {
        "state": "STUDY3_P0_TOKENIZER_GATE_PASSED_AWAITING_MODEL_PILOT",
        "kind": "waypoint",
        "entered_when": (
            "stage P0-T passes and its result and receipt are published by "
            "non-force fast-forward"),
        "permits": ["stage P0-M, bound to that exact commit and tree"],
        "forbids": ["merging or rebasing during an active measurement round"],
    },
    {
        "state": "STUDY3_P0_COMPLETE_MECHANICALLY_FEASIBLE",
        "kind": "terminal",
        "entered_when": (
            "tokenizer and renderer integrity pass, every executed row is complete "
            "and mechanically valid, S1/S2/S3 scoring and S3 reuse reconcile, the "
            "S4 wrapper/parser/accounting path executes, and the resource and "
            "counter records are complete"),
    },
    {
        "state": (
            "STUDY3_P0_COMPLETE_MECHANICALLY_FEASIBLE_EMPIRICALLY_LOW_INFORMATION"),
        "kind": "terminal",
        "entered_when": (
            "every mechanical condition passes but the tiny corpus shows a "
            "globally degenerate prediction pattern, no observed discordance "
            "anywhere, or another explicitly descriptive low-information pattern"),
    },
    {
        "state": "STUDY3_P0_STOPPED_ON_TOKENIZER_OR_RENDERER_DEFECT",
        "kind": "terminal",
        "entered_when": (
            "a registry/schema/renderer mismatch, a non-deterministic render, an "
            "unexplained tokenizer identity, a missing census branch or a counter "
            "mismatch is observed before any model operation"),
    },
    {
        "state": "STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE",
        "kind": "terminal",
        "entered_when": (
            "after the token-ID collision rule, one or more target roles has no "
            "executable genuine I3 contrast"),
    },
    {
        "state": "STUDY3_P0_STOPPED_ON_MODEL_SMOKE_MECHANICAL_FAILURE",
        "kind": "terminal",
        "entered_when": "the smoke mechanical gate fails after any model operation",
    },
    {
        "state": "STUDY3_P0_INCONCLUSIVE_INFRASTRUCTURE_OR_TRANSPORT_FAILURE",
        "kind": "terminal",
        "entered_when": (
            "an infrastructural or transport failure prevents the round from "
            "reaching a mechanical determination"),
    },
    {
        "state": "STUDY3_P0_BLOCKED_ON_AUTHORITY_OR_REPOSITORY_INTEGRITY",
        "kind": "terminal",
        "entered_when": (
            "the starting state, the protected bytes, the authority identity or "
            "the publication path cannot be established exactly"),
    },
)

TRANSITIONS = (
    {
        "from": "BLOCKED_ON_STUDY3_P0_STARTING_STATE_INTEGRITY",
        "to": "STUDY3_P0_REGISTERED_AWAITING_TOKENIZER_GATE",
        "guard": (
            "origin/main equals the required baseline commit and tree, the "
            "worktree is clean, the authority copy is byte-identical, the frozen "
            "corpus reproduces, every protected byte is unchanged, all P0 "
            "counters are zero, and the pre-execution commit publishes by "
            "non-force fast-forward"),
        "fail_closed_to": "STUDY3_P0_BLOCKED_ON_AUTHORITY_OR_REPOSITORY_INTEGRITY",
    },
    {
        "from": "STUDY3_P0_REGISTERED_AWAITING_TOKENIZER_GATE",
        "to": "STUDY3_P0_TOKENIZER_GATE_PASSED_AWAITING_MODEL_PILOT",
        "guard": (
            "the complete tokenizer and renderer census passes for RT, RL and RI "
            "within the 10,000 encoded-sequence cap, every applicable "
            "byte-distinct pair yields distinct full token-ID sequences, the S1 "
            "label surfaces and S2 answer surfaces are single-token and pairwise "
            "distinct, S2 and S3 share prompt bytes and token IDs, and the S2/S3 "
            "K6-SEP rows are structurally absent"),
        "fail_closed_to": "STUDY3_P0_STOPPED_ON_TOKENIZER_OR_RENDERER_DEFECT",
        "also_fail_closed_to": (
            "STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE"),
    },
    {
        "from": "STUDY3_P0_TOKENIZER_GATE_PASSED_AWAITING_MODEL_PILOT",
        "to": "STUDY3_P0_COMPLETE_MECHANICALLY_FEASIBLE",
        "guard": (
            "the K2 smoke mechanical gate passes, the bounded extension runs the "
            "two remaining tuple classes and the S4 K2 diagnostic without "
            "crossing a cap, and every mechanical, accounting and resource record "
            "is complete"),
        "fail_closed_to": "STUDY3_P0_STOPPED_ON_MODEL_SMOKE_MECHANICAL_FAILURE",
    },
)

PROHIBITIONS = (
    "any development, confirmation or P3-Q seed or bank",
    "any access to existing or future confirmation material",
    "any formal Gate I0-I5 pass/fail, Family A/B/C analysis, selection-map run, "
    "winner, interface preference or confirmation release",
    "any use of draft-v0.5's 413/214/448 sample sizes as pilot allocations",
    "any change to alpha, power, floors, claims, estimands, m_max or the formal "
    "operation projection",
    "any choice or inspection of RP, any resolution of OD2 or UR-22, or any "
    "RP/P3-Q/I4 execution",
    "any reuse of Study 1/2 item identities, banks, seeds, confirmation data or "
    "empirical results as P0 inputs",
    "any prompt, parser, scoring, tokenizer, item, allocation, checkpoint or "
    "dependency change after the pre-execution publication in response to an "
    "observed P0 result",
    "any reroll, output-conditioned retry, cherry-picking, row replacement, "
    "exclusion of a valid but inconvenient row, or reset of a cumulative counter",
    "any quantization, hosted-provider inference, unpinned revision or local "
    "workstation model execution",
    "any activation extraction, hook, lens, probe, patch, intervention, ablation "
    "or mechanistic operation",
    "any entry in paper/evidence_ledger.csv",
    "any claim that P0 answers the original research question or validates "
    "draft-v0.5",
    "any direct transition from P0 to formal development or confirmation",
)

AUTHORIZED_WRITE_PATHS = (
    "studies/study3/prompts/study3_p0_feasibility_pilot_authority.md",
    "studies/study3/pilot/p0/",
    "tests/test_study3_p0_feasibility_pilot.py",
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
    "studies/study3/protocol/interface_calibration_protocol_draft.json",
    "studies/study3/protocol/interface_calibration_protocol_draft.md",
    "studies/study3/protocol/interface_calibration_protocol.schema.json",
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
    "tests/test_study3_design.py",
    "tests/test_study3_rendering_registry_v0_5.py",
    "tests/test_study3_methods_review.py",
    "tests/test_study3_methods_review_v0_3.py",
    "tests/test_study3_methods_review_v0_4.py",
    "paper/evidence_ledger.csv",
)


def authority_identity():
    with open(AUTHORITY_PATH, "rb") as handle:
        raw = handle.read()
    return {
        "path": "studies/study3/prompts/study3_p0_feasibility_pilot_authority.md",
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "carries_cr": b"\r" in raw,
        "line_feed_count": raw.count(b"\n"),
        "ends_with_newline": raw.endswith(b"\n"),
    }


def build_document():
    return {
        "schema_version": SCHEMA_VERSION,
        "document_class": "study3_p0_feasibility_pilot_protocol",
        "authority": authority_identity(),
        "state": "STUDY3_P0_REGISTERED_AWAITING_TOKENIZER_GATE",
        "legal_status": {
            "formal_execution_authorized": False,
            "p0_pilot_execution_authorized": True,
            "draft_v0_5_frozen": False,
            "draft_v0_5_reviewed": False,
            "draft_v0_5_status": (
                "candidate protocol that has not received a fourth independent "
                "methods review; P0 does not declare it correct and does not "
                "waive that review"),
            "od2_status": "unresolved",
            "ur22_status": "unresolved",
            "rp_status": "excluded; no positive-reference object is selected or touched",
            "interface_selected": None,
            "evidence_ledger_last_row": "EV-0016",
            "evidence_ledger_policy": "byte-identical; P0 writes no evidence row",
        },
        "scientific_purpose": [
            "can an independent implementation instantiate the binding v0.5 "
            "rendering registry without an unregistered choice",
            "do applicable gate-bearing presentation pairs tokenize distinctly "
            "under the exact pinned tokenizers, and do the S1/S2 candidate-token "
            "eligibility rules hold",
            "can S1, S2 and CPU-only S3 be executed and reconciled without missing "
            "rows, non-finite values, scorer disagreement or hidden evaluations",
            "can the S4 diagnostic path render, wrap, generate, parse, retain "
            "unparseable and account for prefill and incremental decode cost",
            "what wall time, peak device memory, prompt-token length, "
            "generated-token count, failure rate and runtime batching occur",
            "does this deliberately tiny corpus show any output variation or "
            "pairwise discordance worth considering when calibrating the protocol",
        ],
        "non_purpose": [
            "no confirmatory effect size, power validation or null test",
            "no formal gate pass or fail",
            "no selection or ranking of S1, S2 or S3 and no qualification of S4",
            "no scientific checkpoint comparison",
            "no answer to the original research question",
            "no reasoning-capability claim",
            "pilot effect sizes may never justify a threshold, sample size, alpha, "
            "seed, bank, profile or confirmation rule",
        ],
        "roles": list(ROLES),
        "rp_excluded": True,
        "execution_route": {
            "workstation_permitted": [
                "code inspection", "editing", "git", "hashes", "upload",
                "submission", "result reading",
            ],
            "authoritative_cpu_validation": (
                "the registered Azure Container Registry/container route on a "
                "clean exact-commit checkout"),
            "model_operations": (
                "an Azure containerized GPU job only; never on the workstation and "
                "never in GitHub Actions"),
            "gpu_class": "one T4-class 16 GiB GPU or a larger compatible Azure GPU",
            "precision": "fp16, one checkpoint at a time",
            "prohibited": [
                "quantization", "mixed checkpoint revisions", "model conversion",
                "adapter insertion", "remote hosted inference APIs",
            ],
            "image_pinning": (
                "the container image is frozen by immutable digest and Python, "
                "PyTorch, Transformers, tokenizer, CUDA and supporting package "
                "versions are pinned before the first tokenizer call"),
            "trust_remote_code": False,
            "trust_remote_code_policy": (
                "must remain false; if a baseline model cannot load without it, "
                "stop and report. This authority permits no silent trust-policy "
                "expansion."),
        },
        "corpus": {
            "namespace": NAMESPACE,
            "seed_policy": "no random seed; no development, confirmation or P3-Q bank",
            "tuple_classes": [t["tuple_class_id"] for t in TUPLE_CLASSES],
            "profile_allocation": [
                {
                    "profile": profile,
                    "contrasts": list(contrasts),
                    "restricted_to_tuple_class": restricted,
                }
                for profile, contrasts, restricted in PROFILE_ALLOCATION
            ],
            "k5_contrasts": list(K5_CONTRASTS),
            "k6_contrasts": list(K6_CONTRASTS),
            "k6_sep_not_instantiated_for": ["S2", "S3"],
            "s3_is_a_scoring_rule_not_a_new_surface": True,
            "permanent_exclusion": (
                "the complete study3-p0-only/ namespace and every semantic tuple "
                "used by P0 are permanently excluded from every later development, "
                "confirmation, P3-Q and external-validity bank"),
        },
        "inference_behaviour": {
            "evaluation_mode": True,
            "inference_mode": "torch.inference_mode() or its exact equivalent",
            "sampling": False,
            "s1_reads": "next-token logits for the four registered label token IDs",
            "s2_reads": (
                "the same next-token logit vector, for the ten registered content "
                "token IDs"),
            "s3": (
                "CPU-only scoring from the already captured S2 vector; exactly zero "
                "prefill, decode, model-load or forward operations"),
            "s4": {
                "wrapper": "each role's registered native-wrapper policy",
                "decoding": "greedy",
                "do_sample": False,
                "max_new_tokens": 4,
                "temperature": "not passed",
                "unparseable": (
                    "an explicit retained outcome; never dropped and never imputed"),
            },
            "never_collect": [
                "hidden states", "activations", "attentions", "gradients", "hooks",
                "lens outputs", "probes", "patches", "ablations",
            ],
        },
        "counter_ontology": ontology_document(),
        "caps": dict(CAPS),
        "smoke_exact_allocation": dict(SMOKE_EXACT),
        "state_machine": {
            "states": list(STATES),
            "transitions": list(TRANSITIONS),
            "terminal_dispositions": [
                state["state"] for state in STATES if state["kind"] == "terminal"
            ],
            "disposition_1_vs_2": (
                "descriptive only; it creates no formal eligibility difference. A "
                "small pilot cannot establish that a contrast has or lacks a "
                "substantive effect."),
        },
        "token_id_collision_rule": {
            "on_genuine_collision": (
                "mark the specific role/profile/contrast INELIGIBLE_TOKEN_IDS, "
                "exclude its model rows, and continue only if at least one genuine "
                "I3 contrast remains executable for each of RT, RL and RI"),
            "never": (
                "repaired after observation, turned into a pass, or reported as a "
                "robustness observation"),
        },
        "retry_rule": {
            "output_conditioned_retry": False,
            "zero_operation_infrastructure_retry": (
                "permitted once only when a signed job receipt proves that zero "
                "tokenizer, model-load, prefill, decode, scoring and generation "
                "operations occurred"),
        },
        "prohibitions": list(PROHIBITIONS),
        "authorized_write_paths": list(AUTHORIZED_WRITE_PATHS),
        "byte_protected_paths": list(BYTE_PROTECTED_PATHS),
        "publication_rule": (
            "non-force fast-forward only, with the explicit refspec "
            "git push origin HEAD:refs/heads/main, then re-fetch and require "
            "HEAD == origin/main, the exact tree and a clean worktree"),
        "legal_successor": (
            "a fresh-session operator calibration round that reads the P0 "
            "feasibility record. It is not another pilot and not immediate formal "
            "execution. Any surviving candidate must then receive one focused, "
            "fresh-session independent methods review before freeze, seed draw, "
            "bank construction, formal model execution or confirmation."),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = canonical_bytes(build_document())
    if args.write:
        with open(PROTOCOL_PATH, "wb") as handle:
            handle.write(payload)
        print("WROTE studies/study3/pilot/p0/p0_protocol.json (%d bytes, sha256 %s)"
              % (len(payload), hashlib.sha256(payload).hexdigest()))
        return 0
    if not os.path.exists(PROTOCOL_PATH):
        print("FAIL studies/study3/pilot/p0/p0_protocol.json is missing")
        return 1
    with open(PROTOCOL_PATH, "rb") as handle:
        committed = handle.read()
    if committed != payload:
        print("FAIL the committed P0 protocol does not reproduce byte-exactly")
        return 1
    print("OK the committed P0 protocol reproduces byte-exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
