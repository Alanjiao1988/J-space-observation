"""Stage P0-T: the Study 3-P0 tokenizer and renderer gate.

Authority: ``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md``
section 7.

Stage P0-T is CPU-only. It must run in the registered Azure container route
rather than on the workstation, and it may begin only from the exact published
pre-execution commit. It performs **no** model download, weight load, GPU
allocation, forward evaluation, scoring or generation.

The gate is fail-closed. A registry/schema/renderer mismatch, a
non-deterministic render, an unexplained tokenizer identity, a missing census
branch or a counter mismatch stops P0 *before* any model operation as
``STUDY3_P0_STOPPED_ON_TOKENIZER_OR_RENDERER_DEFECT``.

A genuine token-ID collision is never repaired after observation. The specific
role/profile/contrast is marked ``INELIGIBLE_TOKEN_IDS`` and its model rows are
excluded. Ineligibility is never turned into a pass or a robustness observation.

Usage::

    python p0_tokenizer_gate.py --out-dir <dir>
    python p0_tokenizer_gate.py --out-dir <dir> --dry-run   # census only, no tokenizer
"""

import argparse
import datetime
import hashlib
import itertools
import json
import os
import platform
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p0_corpus import (  # noqa: E402
    K5_CONTRASTS,
    K6_CONTRASTS,
    TUPLE_CLASSES,
    build_rows,
    canonical_bytes,
    contents_for_state,
    distractor_triple,
    ground_truth,
    _values_for,
)
from p0_counters import CAPS, P0Counters  # noqa: E402
from p0_protocol import ROLES  # noqa: E402
from p0_renderer import (  # noqa: E402
    P0Renderer,
    UnregisteredSurface,
    labels_for_state,
    load_protocol,
    load_registry,
)

RESULT_SCHEMA_VERSION = "study3-p0-tokenizer-gate-result-v1"
RECEIPT_SCHEMA_VERSION = "study3-p0-tokenizer-gate-receipt-v1"

STOP_DEFECT = "STUDY3_P0_STOPPED_ON_TOKENIZER_OR_RENDERER_DEFECT"
STOP_NO_CONTRAST = (
    "STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE")
PASSED = "STUDY3_P0_TOKENIZER_GATE_PASSED_AWAITING_MODEL_PILOT"

INELIGIBLE = "INELIGIBLE_TOKEN_IDS"


class TokenizerGateDefect(Exception):
    """A fail-closed stop before any model operation."""


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------------------
# The deterministic rendering-fixture census.
# ---------------------------------------------------------------------------

def nuisance_states():
    """The registered 32-state nuisance support: 4 positions x 4 symbols x 2 alphabets."""
    return list(itertools.product(range(4), range(4), range(2)))


def fixture_census(registry, protocol):
    """Enumerate every applicable profile/rendering/contrast/nuisance branch.

    This is the complete existing deterministic rendering-fixture census that
    section 7.1 requires, including all 32 registered nuisance-support states and
    every applicable profile, rendering, contrast and stem branch the binding
    registry exposes. Rows carry an explicit ``applicability`` value, so a
    structurally absent branch is recorded as absence rather than omitted.
    """
    renderer = P0Renderer(registry)
    rows = []
    branches = [b["branch_id"] for b in registry["question_stem_templates"]["branches"]]
    branch_values = _fixture_branch_values(registry)
    for profile in ("S1", "S2", "S3", "S4"):
        for contrast in K6_CONTRASTS:
            applicability = _k6_applicability(registry, profile, contrast)
            baseline_rendering = "R-base"
            variant_rendering = "R-sep" if contrast == "K6-SEP" else "R-instr"
            for branch_id in branches:
                if profile not in renderer.stems[branch_id]["applicable_profiles"]:
                    continue
                for state in nuisance_states():
                    if profile in ("S2", "S3") and state != (0, 0, 0):
                        # An option-less profile renders no label and no option,
                        # so the nuisance state has no referent. One canonical
                        # state is recorded rather than 32 duplicate rows.
                        continue
                    row = {
                        "profile": profile,
                        "contrast": contrast,
                        "branch_id": branch_id,
                        "nuisance_state": list(state),
                        "applicability": applicability,
                    }
                    if applicability != "applicable":
                        row["members"] = []
                        row["structural_absence"] = True
                        rows.append(row)
                        continue
                    members = []
                    for role_in_pair, rendering in (
                            ("baseline", baseline_rendering),
                            ("variant", variant_rendering)):
                        labels = contents = None
                        if profile in ("S1", "S4"):
                            labels = labels_for_state(registry, *state)
                            contents = branch_values[branch_id]["contents"](state)
                        prompt = renderer.render(
                            profile, rendering, branch_id,
                            branch_values[branch_id]["values"], labels, contents)
                        members.append({
                            "role_in_pair": role_in_pair,
                            "rendering": rendering,
                            "prompt": prompt,
                        })
                    row["members"] = members
                    row["structural_absence"] = False
                    rows.append(row)
    return rows


def _k6_applicability(registry, profile, contrast):
    for row in registry["applicability_table"]["rows"]:
        if row["profile"] == profile and row["contrast"] == contrast:
            return row["applicability"]
    raise TokenizerGateDefect(
        "missing census branch: no applicability row for %s/%s"
        % (profile, contrast))


def _fixture_branch_values(registry):
    """One registered substitution per stem branch, with a valid option layout."""
    domain = registry["answer_domain"]["surface_forms"]
    perm = "[1 2 3 4 5 6 7 8 9 0]"
    spec = {
        "K1/none/0": ({"value": "7"}, "7"),
        "K2/none/0": ({"x": "3"}, "3"),
        "K3/affine_mod10/1": ({"x": "4", "a1": "3", "b1": "1"}, "3"),
        "K3/permutation_chain/1": ({"p1": perm, "x": "5"}, "6"),
        "K4/affine_mod10/2": (
            {"x": "2", "a1": "3", "b1": "1", "a2": "7", "b2": "4"}, "3"),
        "K4/affine_mod10/3": (
            {"x": "2", "a1": "3", "b1": "1", "a2": "7", "b2": "4",
             "a3": "9", "b3": "6"}, "3"),
        "K4/permutation_chain/2": ({"p1": perm, "p2": perm, "x": "6"}, "8"),
        "K4/permutation_chain/3": (
            {"p1": perm, "p2": perm, "p3": perm, "x": "8"}, "1"),
    }
    out = {}
    for branch_id, (values, correct) in spec.items():
        if correct not in domain:
            raise TokenizerGateDefect("fixture ground truth outside the domain")
        pool = [v for v in domain if v != correct]

        def make(correct=correct, pool=pool):
            def contents(state):
                triple = [pool[(state[0] + j) % 9] for j in range(3)]
                return contents_for_state(state, correct, triple)
            return contents
        out[branch_id] = {"values": values, "correct": correct,
                          "contents": make()}
    return out


# ---------------------------------------------------------------------------
# Tokenizer loading, pinned by exact immutable revision.
# ---------------------------------------------------------------------------

def load_tokenizers(counters, offline=False):
    """Construct the three pinned role tokenizers. No model weights are loaded."""
    from transformers import AutoTokenizer  # imported late: CPU-only stage

    tokenizers = {}
    for role in ROLES:
        started = time.time()
        tokenizer = AutoTokenizer.from_pretrained(
            role["repository_identity"],
            revision=role["immutable_revision"],
            trust_remote_code=False,
            local_files_only=offline,
        )
        counters.add("distinct_tokenizer_identities_constructed", 1)
        tokenizers[role["role"]] = {
            "tokenizer": tokenizer,
            "identity": tokenizer_identity(role, tokenizer),
            "load_seconds": round(time.time() - started, 6),
        }
    return tokenizers


def tokenizer_identity(role, tokenizer):
    """Record the exact tokenizer identity, never a branch, tag or floating cache."""
    import transformers

    special = {}
    for name in sorted(getattr(tokenizer, "special_tokens_map", {}) or {}):
        special[name] = getattr(tokenizer, "special_tokens_map")[name]
    return {
        "role": role["role"],
        "repository_identity": role["repository_identity"],
        "resolved_revision": role["immutable_revision"],
        "tokenizer_class": type(tokenizer).__name__,
        "vocabulary_size": int(getattr(tokenizer, "vocab_size", 0) or 0),
        "len_tokenizer": len(tokenizer),
        "special_token_map": special,
        "is_fast": bool(getattr(tokenizer, "is_fast", False)),
        "transformers_version": transformers.__version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }


def encode(counters, tokenizer, text):
    """Encode exactly one sequence with no unregistered normalization."""
    counters.add("tokenizer_encoded_sequences", 1)
    ids = tokenizer.encode(text, add_special_tokens=False)
    return [int(i) for i in ids]


def assert_no_unregistered_normalization(tokenizer, ids, text):
    """Reject an encode that did not round-trip the registered bytes exactly."""
    decoded = tokenizer.decode(ids, skip_special_tokens=False)
    if decoded != text:
        raise TokenizerGateDefect(
            "the tokenizer did not round-trip the registered bytes: an "
            "unregistered normalization, whitespace repair, truncation or "
            "special-token insertion policy is in effect")
    return True


# ---------------------------------------------------------------------------
# The required assertions of section 7.1.
# ---------------------------------------------------------------------------

def candidate_surfaces(registry):
    """Return the registered S1 label surfaces and S2 content surfaces."""
    profiles = {entry["profile"]: entry for entry in registry["profiles"]}
    s1 = profiles["S1"]["candidate_surfaces"]["by_label_alphabet"]
    s2 = profiles["S2"]["candidate_surfaces"]["answer_domain"]
    return s1, s2


def check_candidate_eligibility(counters, tokenizers, registry):
    """S1 label and S2 content surfaces must be single-token and distinct."""
    s1_surfaces, s2_surfaces = candidate_surfaces(registry)
    report = {}
    for role, entry in tokenizers.items():
        tokenizer = entry["tokenizer"]
        role_report = {"s1_by_alphabet": {}, "s2": {}, "eligible": True,
                       "reasons": []}
        for alphabet, surfaces in sorted(s1_surfaces.items()):
            ids = []
            for surface in surfaces:
                encoded = encode(counters, tokenizer, surface)
                ids.append(encoded)
            single = all(len(i) == 1 for i in ids)
            flat = [i[0] for i in ids if len(i) == 1]
            distinct = len(set(flat)) == len(flat) and single
            role_report["s1_by_alphabet"][alphabet] = {
                "surfaces": list(surfaces),
                "token_ids": ids,
                "all_single_token": single,
                "pairwise_distinct": distinct,
            }
            if not (single and distinct):
                role_report["eligible"] = False
                role_report["reasons"].append(
                    "S1 %s label surfaces are not four distinct single tokens"
                    % alphabet)
        ids = [encode(counters, tokenizer, s) for s in s2_surfaces]
        single = all(len(i) == 1 for i in ids)
        flat = [i[0] for i in ids if len(i) == 1]
        distinct = len(set(flat)) == len(flat) and single
        role_report["s2"] = {
            "surfaces": list(s2_surfaces),
            "token_ids": ids,
            "all_single_token": single,
            "pairwise_distinct": distinct,
        }
        if not (single and distinct):
            role_report["eligible"] = False
            role_report["reasons"].append(
                "S2 answer surfaces are not ten distinct single tokens")
        report[role] = role_report
    return report


def tokenize_rows(counters, tokenizers, rows, source):
    """Tokenize every rendered member of every applicable row, for every role."""
    records = []
    for row in rows:
        if row.get("structural_absence"):
            records.append({
                "source": source,
                "profile": row["profile"],
                "contrast": row["contrast"],
                "branch_id": row.get("branch_id"),
                "applicability": row["applicability"],
                "structural_absence": True,
                "members": [],
            })
            continue
        for role, entry in sorted(tokenizers.items()):
            tokenizer = entry["tokenizer"]
            members = []
            for member in row["members"]:
                prompt = member["prompt"]
                ids = encode(counters, tokenizer, prompt)
                assert_no_unregistered_normalization(tokenizer, ids, prompt)
                members.append({
                    "role_in_pair": member["role_in_pair"],
                    "rendering": member["rendering"],
                    "prompt_bytes": len(prompt.encode("utf-8")),
                    "prompt_sha256": hashlib.sha256(
                        prompt.encode("utf-8")).hexdigest(),
                    "token_ids": ids,
                    "token_count": len(ids),
                })
            records.append({
                "source": source,
                "role": role,
                "row_id": row.get("row_id"),
                "base_item_id": row.get("base_item_id"),
                "tuple_class_id": row.get("tuple_class_id"),
                "branch_id": row.get("branch_id"),
                "profile": row["profile"],
                "contrast": row["contrast"],
                "nuisance_state": row.get("nuisance_state"),
                "applicability": row.get("applicability", "applicable"),
                "structural_absence": False,
                "members": members,
                "pair_token_ids_distinct": (
                    members[0]["token_ids"] != members[1]["token_ids"]),
                "pair_bytes_distinct": (
                    members[0]["prompt_sha256"] != members[1]["prompt_sha256"]),
            })
    return records


def evaluate_eligibility(records, candidate_report):
    """Mark each role/profile/contrast eligible or INELIGIBLE_TOKEN_IDS."""
    matrix = {}
    for record in records:
        if record.get("structural_absence"):
            continue
        key = (record["role"], record["profile"], record["contrast"])
        cell = matrix.setdefault(key, {
            "role": record["role"],
            "profile": record["profile"],
            "contrast": record["contrast"],
            "status": "eligible",
            "reasons": [],
            "collision_rows": [],
        })
        if record["pair_bytes_distinct"] and not record["pair_token_ids_distinct"]:
            cell["status"] = INELIGIBLE
            reason = ("a byte-distinct applicable pair produced identical full "
                      "token-ID sequences")
            if reason not in cell["reasons"]:
                cell["reasons"].append(reason)
            cell["collision_rows"].append(
                record.get("row_id") or record.get("branch_id"))
    for key, cell in matrix.items():
        role, profile = key[0], key[1]
        report = candidate_report.get(role, {})
        if profile == "S1" and not report.get("eligible", True):
            cell["status"] = INELIGIBLE
            for reason in report.get("reasons", []):
                if reason.startswith("S1") and reason not in cell["reasons"]:
                    cell["reasons"].append(reason)
        if profile in ("S2", "S3") and not report.get("s2", {}).get(
                "pairwise_distinct", True):
            cell["status"] = INELIGIBLE
            reason = "S2 answer surfaces are not ten distinct single tokens"
            if reason not in cell["reasons"]:
                cell["reasons"].append(reason)
    return sorted(matrix.values(),
                  key=lambda c: (c["role"], c["profile"], c["contrast"]))


def executable_contrast_per_role(matrix):
    """Every target role needs at least one executable genuine I3 contrast."""
    executable = {}
    for cell in matrix:
        if cell["profile"] == "S4":
            # S4 is the never-selectable diagnostic; it is not a genuine I3 contrast.
            continue
        if cell["status"] == "eligible":
            executable.setdefault(cell["role"], []).append(
                "%s/%s" % (cell["profile"], cell["contrast"]))
    return executable


def check_s2_s3_parity(records):
    """S3 must reuse S2's prompt bytes and token IDs exactly."""
    index = {}
    for record in records:
        if record.get("structural_absence"):
            continue
        key = (record["role"], record.get("tuple_class_id"),
               record.get("branch_id"), record["contrast"], record["profile"])
        index[key] = record
    mismatches = []
    for key, record in index.items():
        if key[4] != "S3":
            continue
        source = index.get((key[0], key[1], key[2], key[3], "S2"))
        if source is None:
            mismatches.append({"row": record.get("row_id"),
                               "reason": "no matching S2 row"})
            continue
        for s3_member, s2_member in zip(record["members"], source["members"]):
            if s3_member["prompt_sha256"] != s2_member["prompt_sha256"] \
                    or s3_member["token_ids"] != s2_member["token_ids"]:
                mismatches.append({
                    "row": record.get("row_id"),
                    "reason": ("S3 differs from S2; S3 is a scoring rule, not a "
                               "new surface"),
                })
    return mismatches


def check_structural_absence(records):
    """S2/S3 K6-SEP rows must be absent, never duplicated onto R-base."""
    offending = []
    for record in records:
        if record["profile"] in ("S2", "S3") and record["contrast"] == "K6-SEP":
            if not record.get("structural_absence"):
                offending.append(record.get("row_id") or record.get("branch_id"))
    return offending


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------

def run(out_dir, dry_run=False, offline=False):
    started = time.time()
    run_id = utc_now()
    counters = P0Counters()
    registry = load_registry()
    protocol = load_protocol()

    corpus_rows = build_rows(registry, protocol)
    census_rows = fixture_census(registry, protocol)

    # Determinism: rendering the corpus twice must produce identical bytes.
    repeat = build_rows(registry, protocol)
    for first, second in zip(corpus_rows, repeat):
        for a, b in zip(first["members"], second["members"]):
            if a["prompt"] != b["prompt"]:
                raise TokenizerGateDefect(
                    "non-deterministic render at %s" % first["base_item_id"])

    planned = 0
    for row in corpus_rows + census_rows:
        planned += len(row.get("members", [])) * len(ROLES)
    planned += len(ROLES) * (8 + 10)
    if planned > CAPS["tokenizer_encoded_sequences"]:
        raise TokenizerGateDefect(
            "the planned census would encode %d sequences, exceeding the "
            "registered cap of %d; P0 stops before the first encode"
            % (planned, CAPS["tokenizer_encoded_sequences"]))

    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "document_class": "study3_p0_tokenizer_gate_result",
        "run_id": run_id,
        "stage": "P0-T",
        "dry_run": bool(dry_run),
        "planned_encoded_sequences": planned,
        "evidence_status": (
            "methods-feasibility observation only; not Study 3 evidence"),
        "formal_execution_authorized": False,
        "model_operations_performed": 0,
    }

    if dry_run:
        result["state"] = "P0_T_DRY_RUN_CENSUS_ONLY_NO_TOKENIZER_CONSTRUCTED"
        result["corpus_rows"] = len(corpus_rows)
        result["census_rows"] = len(census_rows)
        result["counters"] = counters.snapshot()
        _emit(out_dir, run_id, result, None)
        return 0

    tokenizers = load_tokenizers(counters, offline=offline)
    candidate_report = check_candidate_eligibility(counters, tokenizers, registry)
    corpus_records = tokenize_rows(counters, tokenizers, corpus_rows, "frozen_corpus")
    census_records = tokenize_rows(
        counters, tokenizers, census_rows, "rendering_fixture_census")
    records = corpus_records + census_records

    absence_defects = check_structural_absence(records)
    parity_defects = check_s2_s3_parity(records)
    matrix = evaluate_eligibility(records, candidate_report)
    executable = executable_contrast_per_role(matrix)

    result["tokenizer_identities"] = {
        role: entry["identity"] for role, entry in sorted(tokenizers.items())
    }
    result["candidate_token_eligibility"] = candidate_report
    result["eligibility_matrix"] = matrix
    result["executable_genuine_i3_contrasts"] = executable
    result["structural_absence_violations"] = absence_defects
    result["s2_s3_parity_mismatches"] = parity_defects
    result["records"] = records
    result["counters"] = counters.snapshot()
    result["wall_seconds"] = round(time.time() - started, 6)

    if absence_defects:
        result["state"] = STOP_DEFECT
        result["stop_reason"] = (
            "an S2 or S3 K6-SEP row was instantiated; not_applicable is "
            "structural absence, never a duplicate row")
        _emit(out_dir, run_id, result, matrix)
        return 2
    if parity_defects:
        result["state"] = STOP_DEFECT
        result["stop_reason"] = "S3 did not reuse S2's prompt bytes and token IDs"
        _emit(out_dir, run_id, result, matrix)
        return 2

    missing = [role["role"] for role in ROLES if not executable.get(role["role"])]
    if missing:
        result["state"] = STOP_NO_CONTRAST
        result["stop_reason"] = (
            "no executable genuine I3 contrast remains for %s" % ", ".join(missing))
        _emit(out_dir, run_id, result, matrix)
        return 3

    result["state"] = PASSED
    _emit(out_dir, run_id, result, matrix)
    return 0


def _emit(out_dir, run_id, result, matrix):
    os.makedirs(out_dir, exist_ok=True)
    payload = canonical_bytes(result)
    result_path = os.path.join(out_dir, "p0_tokenizer_gate_result.json")
    with open(result_path, "wb") as handle:
        handle.write(payload)
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "document_class": "study3_p0_tokenizer_gate_receipt",
        "run_id": run_id,
        "stage": "P0-T",
        "state": result.get("state"),
        "stop_reason": result.get("stop_reason"),
        "result_document": {
            "path": "p0_tokenizer_gate_result.json",
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
        "counters": result.get("counters"),
        "model_operations_performed": 0,
        "gpu_allocated": False,
        "weights_loaded": 0,
        "hosted_provider_calls": 0,
        "seeds_drawn": 0,
        "eligibility_matrix": matrix or [],
        "claim_boundary": (
            "a tokenizer and renderer feasibility observation. It selects no "
            "interface, passes no formal gate, answers no research question and "
            "is not Study 3 evidence."),
    }
    receipt_path = os.path.join(out_dir, "p0_tokenizer_gate_receipt.json")
    with open(receipt_path, "wb") as handle:
        handle.write(canonical_bytes(receipt))
    print("state: %s" % result.get("state"))
    print("wrote %s" % result_path)
    print("wrote %s" % receipt_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.out_dir, dry_run=args.dry_run, offline=args.offline)
    except (TokenizerGateDefect, UnregisteredSurface) as exc:
        print("%s: %s" % (STOP_DEFECT, exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
