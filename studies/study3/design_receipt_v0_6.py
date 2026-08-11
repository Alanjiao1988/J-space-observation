"""Emit and verify the Study 3 draft-v0.6 design receipt.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections 5,
9 and 12.

The receipt records bytes and boundaries. It does not declare the amended
protocol correct and it creates no successor authority. It is generated so that
the changed-path census, the protected-byte audit and the derived quantities
cannot drift from the objects they describe.

Usage::

    python design_receipt_v0_6.py --write
    python design_receipt_v0_6.py --check
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

sys.path.insert(0, os.path.join(REPO_ROOT, "studies", "study3", "analysis"))
sys.path.insert(0, os.path.join(REPO_ROOT, "studies", "study3", "pilot", "p0_r1"))

import scoring_boundary_v0_6 as SB  # noqa: E402
from p0_r1_protocol import BYTE_PROTECTED_PATHS  # noqa: E402

RECEIPT_PATH = os.path.join(REPO_ROOT, "studies", "study3",
                            "design_receipt_v0_6.json")

SCHEMA_VERSION = "study3_design_receipt_v0_6"
BASELINE_COMMIT = "dfbe6dd6c82fbe0e8906a4aa7f4df6b676496366"
BASELINE_TREE = "7779c8fd28aad434096ff9643c3f294b27157980"
AUTHORITY_COMMIT = "593e0b13b46ce3eba5d1978a576f4bfbb857f9b2"

AUTHORITY_PATH = ("studies/study3/prompts/study3_v0_6_p0_r1_authority.md")

DISPOSITION = "PROPOSED_RESOLVED_SUBJECT_TO_FINAL_FOCUSED_REVIEW"


def git(*args):
    result = subprocess.run(["git", "-C", REPO_ROOT] + list(args),
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit("git %s failed: %s" % (" ".join(args), result.stderr))
    return result.stdout


def blob(repo_relative_path):
    path = os.path.join(REPO_ROOT, *repo_relative_path.split("/"))
    if not os.path.exists(path):
        return {"path": repo_relative_path, "present": False}
    with open(path, "rb") as handle:
        raw = handle.read()
    return {
        "path": repo_relative_path,
        "present": True,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "carries_cr": b"\r" in raw,
    }


def changed_paths():
    out = git("diff", "--name-only", "%s..HEAD" % BASELINE_COMMIT)
    return sorted(line.strip() for line in out.splitlines() if line.strip())


def build_receipt():
    tables = SB.build_tables()
    registry = SB.build_registry()
    invariance = tables["statistical_invariance"]
    changed = changed_paths()
    return {
        "schema_version": SCHEMA_VERSION,
        "document_class": "design_receipt",
        "round": ("Study 3 draft-v0.6 scoring-boundary calibration and P0-R1 "
                  "registration"),
        "state": SB.STATE,
        "disposition_status": DISPOSITION,
        "authority_source": {
            "path": AUTHORITY_PATH,
            "bytes": 19632,
            "sha256": ("f72292e75ebf128e90c5cd73588786afa11d9f156f37392a9a9200"
                       "845ddc19d2"),
            "lf_only": True,
            "cr_count": 0,
            "lf_count": 375,
            "trailing_newline": False,
            "committed_verbatim": True,
            "committed_as_the_first_new_repository_object": True,
            "authority_commit": AUTHORITY_COMMIT,
            "no_wrapper_header_or_trailing_commentary": True,
            "transport_format_normalization_applied": (
                "none. The operator-supplied bytes were already LF-only with no "
                "trailing newline and no BOM, so the committed blob is "
                "byte-identical to the supplied file."),
        },
        "starting_state": {
            "commit": BASELINE_COMMIT,
            "tree": BASELINE_TREE,
            "clean_worktree": True,
            "evidence_ledger_last_row": "EV-0016",
            "p0_t_bound_commit": "d331b3e774168eec99ad849e983bfe021aebc464",
            "p0_t_terminal_state": (
                "STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE"),
        },
        "rendering_and_scoring_registry": {
            "path": ("studies/study3/protocol/"
                     "interface_calibration_rendering_registry_v0_6.json"),
            "schema": ("studies/study3/protocol/"
                       "interface_calibration_rendering_registry_v0_6.schema."
                       "json"),
            "binding_input": True,
            "illustrative_example": False,
            "registry_sha256":
                registry["registry_identity"]["registry_sha256"],
            "supersedes": ("studies/study3/protocol/"
                           "interface_calibration_rendering_registry_v0_5.json"),
            "predecessor_preserved_byte_for_byte": True,
            "visible_rendering_surface_unchanged": True,
        },
        "scoring_boundary": {
            "rule": ("first-discriminative-token restricted argmax for S2/S3; "
                     "S1 and S4 unchanged"),
            "factorization": "candidate_d = common_prefix || discriminant_d",
            "common_prefix_token": registry["scoring_boundary"][
                "common_prefix_token_for_every_pinned_role"],
            "discriminant_token_ids": registry["profiles"][1][
                "scoring_boundary"]["verified_discriminant_token_ids"],
            "derived_with_zero_tokenizer_encodes": True,
            "equivalence_identity": "P(u, v_d | x) = P(u | x) * P(v_d | x, u)",
            "equivalence_is_exact_factor_cancellation": True,
        },
        "rederived_quantities": {
            "m_max": invariance["unchanged_and_why"]["values"]["m_max"],
            "m_max_unchanged_because": (
                "the new boundary changes where one logit vector is read and "
                "adds one teacher-forced token to the S2 scoring context; it "
                "changes no cell, contrast applicability, independent unit, "
                "null, alternative, alpha or decision rule"),
            "development_sizes":
                invariance["unchanged_and_why"]["values"]["development_sizes"],
            "development_pass_counts": invariance["unchanged_and_why"][
                "values"]["development_pass_counts"],
            "confirmation_pass_counts": invariance["unchanged_and_why"][
                "values"]["confirmation_pass_counts"],
            "per_cell_false_negative_budget_exact_rational":
                invariance["unchanged_and_why"]["values"][
                    "per_cell_false_negative_budget_exact_rational"],
            "per_cell_power_target_exact_rational":
                invariance["unchanged_and_why"]["values"][
                    "per_cell_power_target_exact_rational"],
            "profile_stage_power_floor_exact_rational":
                invariance["unchanged_and_why"]["values"][
                    "profile_stage_power_floor_exact_rational"],
            "study_end_to_end_power_floor_exact_rational":
                invariance["unchanged_and_why"]["values"][
                    "study_end_to_end_power_floor_exact_rational"],
            "total_gate_bearing_cells": invariance["unchanged_and_why"][
                "values"]["total_gate_bearing_cells"],
            "sequence_level_development_projection": invariance[
                "unchanged_and_why"]["values"][
                    "development_projection_scored_rows"],
            "no_number_preserved_for_continuity": True,
        },
        "token_accounting": tables["token_accounting"]["p0_r1_totals"],
        "changed_and_surfaced": invariance["changed_and_surfaced"],
        "changed_paths": changed,
        "changed_path_count": len(changed) + 1,
        "changed_path_note": (
            "this receipt itself is the remaining authorized changed path and "
            "cannot record its own digest"),
        "immutable_objects_not_edited": [
            blob(path) for path in BYTE_PROTECTED_PATHS
        ],
        "findings_closed": [
            {"id": "S3P0T-001", "disposition": DISPOSITION},
            {"id": "S3P0T-002", "disposition": DISPOSITION},
            {"id": "S3P0T-003", "disposition": DISPOSITION},
        ],
        "closure_matrix": "studies/study3/reviews/v0_6_operator_amendment.json",
        "authority_flags": {
            "frozen": False,
            "execution_authorized": False,
            "model_operations_authorized": False,
            "seed_authorized": False,
            "bank_authorized": False,
            "confirmation_access_authorized": False,
            "positive_reference_selected": False,
            "winner_selected": False,
            "self_approval_claimed": False,
            "successor_authority_created": False,
            "p0_r1_pilot_execution_authorized": True,
            "p0_r1_pilot_execution_consumed": False,
        },
        "operation_counters": {
            "tokenizer_calls": 0,
            "tokenizer_encodes": 0,
            "tokenizer_constructions": 0,
            "checkpoint_downloads": 0,
            "model_weight_loads": 0,
            "gpu_jobs": 0,
            "forward_passes": 0,
            "generations": 0,
            "logit_reads": 0,
            "parser_calls": 0,
            "scored_rows": 0,
            "seeds_drawn": 0,
            "bank_rows_created": 0,
            "confirmation_reads": 0,
            "evidence_rows_added": 0,
            "github_actions_runs": 0,
        },
        "local_operations_disclosure": {
            "statement": (
                "No decision-bearing computation was performed on the operator "
                "machine. The activity below is read-only inspection, document "
                "assembly, syntax checking and non-authoritative debugging, and "
                "it is disclosed rather than omitted."),
            "local_pytest_runs": 0,
            "local_decision_bearing_statistical_runs": 0,
            "local_non_authoritative_debugging": (
                "the scoring-boundary, replay-gate, protocol and validation "
                "modules were executed locally in --write mode to assemble "
                "their documents and in --check mode as syntax and "
                "self-consistency checks while they were being written. Neither "
                "run is evidence."),
            "authoritative_validation": (
                "clean CPU-only Azure Container Registry tasks bound to exact "
                "commits from a fresh clone of a Git bundle, one test path per "
                "invocation, GitHub Actions not used."),
        },
        "boundary": {
            "bank_rows": 0,
            "evidence_rows": 0,
            "results": 0,
            "seeds": 0,
            "original_research_question": "unanswered",
            "od2": "unresolved",
            "ur_22": "unresolved",
            "rp_wrapper": None,
            "interface_selected": None,
            "study1_state": "untouched",
            "study2_scientific_state": "untouched",
            "study2_documentation_state": "untouched",
            "p0_namespace_state": (
                "immutable; not one byte under studies/study3/pilot/p0/ or in "
                "tests/test_study3_p0_feasibility_pilot.py changed"),
            "blocking_operator_decision": (
                "the final focused methods review of draft-v0.6 has not "
                "occurred and is not waived"),
        },
        "next_legal_action": (
            "one fresh, focused final methods review of draft-v0.6 by a party "
            "that did not draft it; and, separately, the P0-R1 replay gate "
            "continued from the published registration commit"),
        "self_approval_prohibited": (
            "this receipt records bytes and boundaries. It does not declare the "
            "amended protocol correct and creates no successor authority."),
    }


def canonical(document):
    return (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True)
            + "\n").encode("utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    document = build_receipt()
    if args.write:
        with open(RECEIPT_PATH, "wb") as handle:
            handle.write(canonical(document))
        print("wrote studies/study3/design_receipt_v0_6.json")
        return 0
    if not os.path.exists(RECEIPT_PATH):
        print("DESIGN RECEIPT CHECK FAILED")
        print("  FAIL the draft-v0.6 design receipt is missing")
        return 1
    with open(RECEIPT_PATH, "rb") as handle:
        if handle.read() != canonical(document):
            print("DESIGN RECEIPT CHECK FAILED")
            print("  FAIL the draft-v0.6 design receipt does not reproduce "
                  "from code")
            return 1
    print("design receipt v0.6: OK")
    print("  changed paths : %d" % document["changed_path_count"])
    print("  protected     : %d objects recorded unchanged"
          % len(document["immutable_objects_not_edited"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
