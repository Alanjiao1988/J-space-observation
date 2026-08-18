"""Study 4F-E1 byte-exact binding to the published Study 4F instrument.

Authority: ``studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md``

Section 2. E1 is a *resource-only* execution successor. It supplies a qualifying
accelerator and executes the existing instrument unchanged, so before anything
else it must prove that every decision-bearing Study 4F file at the registered
predecessor commit is byte-identical to the file it is about to execute.

This module is read-only. It constructs no model, acquires no weight, realizes
no bank, draws no execution seed and reads no logit. It never repairs a
mismatch: a mismatch is refuted with
``STUDY4F_E1_INSTRUMENT_BINDING_FAILED``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

#: The registered predecessor commit: the published Study 4F terminal head.
PREDECESSOR_COMMIT = "5fd9602df207e95789263d0f8d52428540f48fb8"

#: The E1 authority commit, published alone as the first commit after the
#: predecessor.
E1_AUTHORITY_COMMIT = "58cdcda0ec3848ba2bd3a6c525b3c28ac8955d69"

#: The *original* Study 4F authority commit. Bank realization derives its seed
#: from this commit, never from the E1 authority commit.
ORIGINAL_STUDY4F_AUTHORITY_COMMIT = "7d5ff0837d77af9e6df9f49d580ec0e42bdc2729"

BINDING_FAILED_STATE = "STUDY4F_E1_INSTRUMENT_BINDING_FAILED"

#: Every decision-bearing Study 4F file, with the role section 2 names for it.
DECISION_BEARING_FILES: Sequence[Dict[str, str]] = (
    {"role": "protocol",
     "path": "studies/study4f/protocol/study4f_protocol_v1.json"},
    {"role": "protocol_schema",
     "path": "studies/study4f/protocol/study4f_protocol_v1.schema.json"},
    {"role": "task_bank_generator_and_ordering",
     "path": "studies/study4f/analysis/study4f_task_banks.py"},
    {"role": "e0_and_cot_renderers_and_parsers",
     "path": "studies/study4f/analysis/study4f_interfaces.py"},
    {"role": "statistical_calculator",
     "path": "studies/study4f/analysis/study4f_design_statistics.py"},
    {"role": "candidate_local_state_machine",
     "path": "studies/study4f/analysis/study4f_state_machine.py"},
    {"role": "semantic_and_mutation_validators",
     "path": "studies/study4f/analysis/study4f_validation.py"},
    {"role": "checkpoint_identities_and_resource_route",
     "path": "studies/study4f/analysis/study4f_resource_route.py"},
    {"role": "original_shakedown_disposition",
     "path": "studies/study4f/shakedown/study4f_shakedown_disposition.json"},
    {"role": "original_authority",
     "path": "studies/study4f/prompts/"
             "study4f_minimal_behavioral_feasibility_authority.md"},
    {"role": "original_status_router",
     "path": "studies/study4f/STATUS.json"},
    {"role": "original_status_schema",
     "path": "studies/study4f/STATUS.schema.json"},
    {"role": "study4f_tests",
     "path": "studies/study4f/tests/test_study4f_behavioral_feasibility.py"},
    {"role": "original_terminal_disclosure",
     "path": "studies/study4f/STUDY4F_TERMINAL_DISCLOSURE.md"},
    {"role": "original_readme",
     "path": "studies/study4f/README.md"},
)

#: Semantic invariants section 2 requires E1 to reconfirm without modification.
REQUIRED_SEMANTIC_INVARIANTS: Sequence[str] = (
    "d2_and_d3_are_separate",
    "each_planned_bank_has_104_items",
    "m_max_is_16",
    "alpha_per_cell_is_1_over_320",
    "cot_gate_is_n104_pass_90",
    "e0_gate_is_n60_pass_41",
    "candidate_order_is_7b_14b_32b",
    "candidate_failures_are_local",
    "rt_unreachable_without_a_qualified_candidate",
    "quantization_sharding_offload_and_substitution_prohibited",
    "only_developmental_candidate_disposition",
    "w1_raw_direct_surface_hash_reproduces",
    "bank_seed_derives_from_the_original_study4f_authority_commit",
)


class Study4FE1InstrumentBindingError(RuntimeError):
    """Raised when the predecessor instrument does not bind byte-exactly."""


def _git(repo_root: Path, *args: str) -> bytes:
    completed = subprocess.run(["git", "-C", str(repo_root), *args],
                               capture_output=True, check=False)
    if completed.returncode != 0:
        raise Study4FE1InstrumentBindingError(
            completed.stderr.decode("utf-8", "replace").strip())
    return completed.stdout


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def blob_at(repo_root: Path, commit: str, path: str) -> bytes:
    """Exact committed bytes of ``path`` at ``commit``."""
    blob = _git(repo_root, "rev-parse", "%s:%s" % (commit, path)).decode().strip()
    return _git(repo_root, "cat-file", "blob", blob)


def build_manifest(repo_root: Path,
                   commit: str = PREDECESSOR_COMMIT) -> Dict[str, object]:
    """Recompute every decision-bearing hash and compare with the worktree.

    The manifest is read-only evidence. ``recompute_agrees`` is the whole point:
    a false value means the file E1 would execute is not the file Study 4F
    published, which is refuted rather than repaired.
    """
    files: List[Dict[str, object]] = []
    for entry in DECISION_BEARING_FILES:
        path = entry["path"]
        committed = blob_at(repo_root, commit, path)
        worktree = (repo_root / path).read_bytes()
        files.append({
            "role": entry["role"],
            "path": path,
            "git_blob": _git(repo_root, "rev-parse",
                             "%s:%s" % (commit, path)).decode().strip(),
            "bytes": len(committed),
            "sha256": sha256_bytes(committed),
            "recomputed_worktree_sha256": sha256_bytes(worktree),
            "recompute_agrees": committed == worktree,
        })
    return {
        "schema_version": "study4f-e1-predecessor-instrument-manifest-v1",
        "read_only": True,
        "predecessor_commit": commit,
        "predecessor_tree": _git(repo_root, "show", "-s", "--format=%T",
                                 commit).decode().strip(),
        "e1_authority_commit": E1_AUTHORITY_COMMIT,
        "original_study4f_authority_commit": ORIGINAL_STUDY4F_AUTHORITY_COMMIT,
        "file_count": len(files),
        "files": files,
        "all_files_agree": all(entry["recompute_agrees"] for entry in files),
        "binding_failure_state": BINDING_FAILED_STATE,
    }


def mismatched_paths(manifest: Mapping[str, object]) -> List[str]:
    return [str(entry["path"])
            for entry in manifest["files"]  # type: ignore[index]
            if not entry["recompute_agrees"]]


def verify_manifest(manifest: Mapping[str, object],
                    invariants: Optional[Sequence[Mapping[str, object]]] = None
                    ) -> Dict[str, object]:
    """Return the binding verdict. ``bound`` is true only for total agreement."""
    mismatched = mismatched_paths(manifest)
    covered = {str(entry["role"]) for entry in manifest["files"]}  # type: ignore[index]
    required = {entry["role"] for entry in DECISION_BEARING_FILES}
    missing_roles = sorted(required - covered)
    failing_invariants: List[str] = []
    missing_invariants: List[str] = []
    if invariants is not None:
        observed = {str(record["invariant"]): bool(record["holds"])
                    for record in invariants}
        failing_invariants = sorted(name for name, holds in observed.items()
                                    if not holds)
        missing_invariants = sorted(set(REQUIRED_SEMANTIC_INVARIANTS) -
                                    set(observed))
    bound = (not mismatched and not missing_roles and not failing_invariants
             and not missing_invariants)
    return {
        "bound": bound,
        "mismatched_paths": mismatched,
        "missing_roles": missing_roles,
        "failing_invariants": failing_invariants,
        "missing_invariants": missing_invariants,
        "state": None if bound else BINDING_FAILED_STATE,
    }


def require_binding(manifest: Mapping[str, object],
                    invariants: Optional[Sequence[Mapping[str, object]]] = None
                    ) -> None:
    """Raise unless the instrument binds byte-exactly and semantically."""
    verdict = verify_manifest(manifest, invariants)
    if not verdict["bound"]:
        raise Study4FE1InstrumentBindingError(
            "%s: %s" % (BINDING_FAILED_STATE, json.dumps(verdict, sort_keys=True)))
