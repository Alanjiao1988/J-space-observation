"""Model-free tests for the frozen Phase 1.2A validation-set tooling."""

from __future__ import annotations

import hashlib
import math
import os
import shutil
import sys
import uuid
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts import build_parser_v2_validation_set as builder
from scripts import persist_parser_v2_validation_set as persister

v = builder.validation


@pytest.fixture
def workdir():
    root = ROOT / ".pytest-work" / uuid.uuid4().hex
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root)
        parent = root.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()


def _ordered_tags(*tags: str) -> list[str]:
    selected = set(tags)
    return [tag for tag in v.SECONDARY_TAGS if tag in selected]


def _surface(number: int, slot: int) -> tuple[str, list[str]]:
    if slot == 0:
        return f"-{number}", ["signed_numeric_surface", "negative_answer"]
    if slot == 1:
        return f"{number}.5", ["decimal_surface"]
    if slot == 2:
        return f"{number}/2", ["fraction_surface"]
    if slot == 3:
        return str(number), []
    return f"+{number}", ["signed_numeric_surface"]


def _candidate(curator: str, stratum: str, index: int) -> dict:
    curator_letter = "A" if curator == "curator_a" else "B"
    sealed_curator_id = v.SEALED_CURATOR_IDENTITIES[
        0 if curator == "curator_a" else 1
    ]
    candidate_id = f"{curator_letter}-{stratum}-{index:02d}"
    slot_index = index % 5
    subtype = v.SUBTYPE_SLOTS[stratum][slot_index]
    digest_word = hashlib.sha256(candidate_id.encode()).hexdigest()
    tags: list[str] = []
    if slot_index == 0:
        tags.append("balanced_think_tags")
        prefix = f"<think>{digest_word}</think> "
    elif slot_index == 1:
        tags.append("malformed_think_tags")
        prefix = f"<think>{digest_word} "
    else:
        prefix = f"{digest_word} "
    reference = str(900000 + int(stratum[1:]) * 100 + index)
    critical = stratum in v.CRITICAL_STRATA

    if stratum in v.ANSWER_BEARING_STRATA:
        number = (
            1000
            + int(stratum[1:]) * 100
            + index
            + (51 if curator == "curator_b" else 0)
        )
        if stratum == "S12":
            surfaces = (
                (f"+{number}", ["signed_numeric_surface"]),
                (f"-{number}", ["signed_numeric_surface", "negative_answer"]),
                (f"{number}.5", ["decimal_surface"]),
                (f"-{number}.5", ["signed_numeric_surface", "negative_answer", "decimal_surface"]),
                (f"{number}/2", ["fraction_surface"]),
            )
            surface, surface_tags = surfaces[slot_index]
        else:
            surface, surface_tags = _surface(number, slot_index)
        tags.extend(surface_tags)
        output = f"{prefix}Final answer: {surface}; fixture {digest_word}"
        start = output.index(surface)
        canonical = v.normalize_rational_literal(surface)
        evidence = [
            {
                "start": start,
                "end": start + len(surface),
                "text": surface,
                "kind": "explicit_final_marker",
                "normalized_answer": canonical,
                "disposition": "selected",
            }
        ]
        acceptable = [{"start": start, "end": start + len(surface), "text": surface}]
        answer_rank = v.ANSWER_BEARING_STRATA.index(stratum)
        if index < 5:
            correct = curator == "curator_a"
        elif index < 10:
            correct = (index - 5) < (3 if answer_rank < 4 else 2)
        else:
            correct = False
        if correct:
            reference = canonical
        distractor = None
        if stratum == "S06":
            distractor_text = str(number + 77)
            output += f" metadata {distractor_text}"
            distractor_start = output.rindex(distractor_text)
            distractor = {
                "start": distractor_start,
                "end": distractor_start + len(distractor_text),
                "text": distractor_text,
            }
            tags.append("last_number_distractor")
            tags.append("incidental_numeric_distractor")
        presence = "present"
        parse_valid = True
        parse_ambiguous = False
        parsed_answer = canonical
        candidates = [canonical]
        strategy = "explicit_final_marker"
        quality = "malformed_recoverable" if stratum == "S09" else "complete"
        failures: list[str] = []
    elif stratum == "S11":
        first = str(7100 + index)
        second = str(8100 + index)
        output = (
            f"{prefix}Final answer: {first}; Alternative final answer: {second}; "
            f"fixture {digest_word}"
        )
        first_start = output.index(first)
        second_start = output.index(second, first_start + len(first))
        evidence = [
            {
                "start": first_start,
                "end": first_start + len(first),
                "text": first,
                "kind": "explicit_final_marker",
                "normalized_answer": first,
                "disposition": "ambiguous_candidate",
            },
            {
                "start": second_start,
                "end": second_start + len(second),
                "text": second,
                "kind": "explicit_final_marker",
                "normalized_answer": second,
                "disposition": "ambiguous_candidate",
            },
        ]
        acceptable = []
        distractor = None
        presence = "ambiguous"
        parse_valid = True
        parse_ambiguous = True
        parsed_answer = None
        candidates = [first, second]
        strategy = "ambiguous_candidates"
        quality = "complete"
        failures = []
        correct = False
        tags.append("multiple_distinct_candidates")
    else:
        is_empty = stratum == "S08" and curator == "curator_b" and index == 5
        if is_empty:
            output = ""
            tags = []
            quality = "empty"
            failures = ["empty_output"]
        elif stratum == "S07":
            output = f"{prefix}incomplete fixture {digest_word} value {4200 + index}"
            quality = "truncated"
            failures = ["truncated_before_final_answer"]
            tags.append("truncated_construct")
        elif stratum == "S08":
            output = f"{prefix}[no answer wrapper {digest_word} {4300 + index}]"
            quality = "placeholder"
            failures = ["placeholder_without_answer"]
            tags.append("placeholder_output")
        else:
            output = f"{prefix}broken fragment {digest_word} {4400 + index} ???"
            quality = "malformed_unrecoverable"
            failures = ["malformed_without_reliable_answer"]
            tags.append("malformed_output")
        if output:
            tags.append("incidental_numeric_distractor")
        evidence = []
        acceptable = []
        distractor = None
        presence = "no_answer"
        parse_valid = False
        parse_ambiguous = False
        parsed_answer = None
        candidates = []
        strategy = "none"
        correct = False

    return {
        "schema_version": v.CANDIDATE_SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "curator_id": sealed_curator_id,
        "source_kind": v.SOURCE_KIND,
        "stratum": stratum,
        "subtype_slot": subtype,
        "secondary_tags": _ordered_tags(*tags),
        "output_text": output,
        "parse_type": "numeric",
        "expected_answer_presence": presence,
        "expected_parse_valid": parse_valid,
        "expected_parse_ambiguous": parse_ambiguous,
        "expected_parsed_answer": parsed_answer,
        "expected_candidate_answers": candidates,
        "expected_evidence_spans": evidence,
        "expected_extraction_strategy": strategy,
        "expected_output_quality": quality,
        "expected_failure_reasons": failures,
        "expected_format_warnings": [],
        "registered_reference_answer": reference,
        "expected_correctness": correct,
        "critical_case": critical,
        "material_error_if_missed": correct,
        "curation_notes": f"synthetic test fixture {candidate_id}",
        "acceptable_selected_spans": acceptable,
        "last_number_distractor_span": distractor,
        "template_family_id": f"family-{candidate_id}",
        "construction_provenance": f"independent synthetic curator {curator}",
    }


def _external_proposal(candidate: dict, *, human_subtype: bool) -> dict:
    presence = {
        "present": "present",
        "no_answer": "absent",
        "ambiguous": "uncertain",
    }[candidate["expected_answer_presence"]]
    stratum = candidate["stratum"]
    subtype_index = v.SUBTYPE_SLOTS[stratum].index(candidate["subtype_slot"])
    if human_subtype:
        subtype = v.PROTOCOL_SUBTYPE_LABELS[stratum][subtype_index]
    else:
        subtype = next(
            (
                alias
                for alias, internal in v.CURATOR_A_SUBTYPE_ALIASES.get(
                    stratum, {}
                ).items()
                if internal == candidate["subtype_slot"]
            ),
            candidate["subtype_slot"],
        )
    external_tag_aliases = {
        "balanced_think_tags": (
            "balanced_think_tag"
            if human_subtype
            else "balanced_think_tags"
        ),
        "continued_reasoning": "reasoning_continues_after_answer",
        "decimal_surface": "decimal_surface",
        "fraction_surface": "fraction_surface",
        "incidental_numeric_distractor": "incidental_numeric_distractor",
        "last_number_distractor": "rightmost_numeric_distractor",
        "malformed_think_tags": (
            "malformed_think_tag"
            if human_subtype
            else "malformed_think_tags"
        ),
        "multiple_numeric_mentions": "multiple_numeric_mentions",
        "negative_answer": "negative_answer",
        "noncanonical_numeric_surface": "noncanonical_numeric_surface",
        "signed_numeric_surface": "signed_surface",
    }
    external_tags = [
        external_tag_aliases[tag]
        for tag in candidate["secondary_tags"]
        if tag in external_tag_aliases
    ]
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_schema_version": v.CURATOR_CANDIDATE_SCHEMA_VERSION,
        "construction_notes": candidate["curation_notes"],
        "critical_case": candidate["critical_case"],
        "curator_id": candidate["curator_id"],
        "material_error_if_missed": candidate["material_error_if_missed"],
        "output_text": candidate["output_text"],
        "parse_type": candidate["parse_type"],
        "proposed_expected_answer_presence": presence,
        "proposed_expected_candidate_answers": deepcopy(
            candidate["expected_candidate_answers"]
        ),
        "proposed_expected_correctness": candidate["expected_correctness"],
        "proposed_expected_evidence_spans": deepcopy(
            candidate["expected_evidence_spans"]
        ),
        "proposed_expected_extraction_strategy": candidate[
            "expected_extraction_strategy"
        ],
        "proposed_expected_failure_reasons": deepcopy(
            candidate["expected_failure_reasons"]
        ),
        "proposed_expected_format_warnings": deepcopy(
            candidate["expected_format_warnings"]
        ),
        "proposed_expected_output_quality": candidate[
            "expected_output_quality"
        ],
        "proposed_expected_parse_ambiguous": candidate[
            "expected_parse_ambiguous"
        ],
        "proposed_expected_parse_valid": candidate["expected_parse_valid"],
        "proposed_expected_parsed_answer": candidate[
            "expected_parsed_answer"
        ],
        "registered_reference_answer": candidate[
            "registered_reference_answer"
        ],
        "secondary_tags": external_tags,
        "source_kind": candidate["source_kind"],
        "stratum": stratum,
        "subtype_slot": subtype,
        "template_family_id": candidate["template_family_id"],
    }


def _pool_attestation_a() -> dict:
    return {
        "fixtures_constructed_model_free": True,
        "network_access_used": False,
        "target_model_downloaded_or_loaded": False,
        "target_model_inference_performed": False,
    }


def _pool_attestation_b() -> dict:
    return {
        "target_model_downloaded": False,
        "target_model_id": v.HISTORICAL_TARGET_MODEL_ID,
        "target_model_inference_run": False,
        "target_model_loaded": False,
    }


def _curator_c_attestation() -> dict:
    return {
        "fixtures_constructed_model_free": True,
        "new_cases_generated_by_curator_c": False,
        "target_model_downloaded": False,
        "target_model_id": v.HISTORICAL_TARGET_MODEL_ID,
        "target_model_inference_run": False,
        "target_model_loaded": False,
    }


def _actual_feature_report(development, locked):
    records_by_set = {"development": development, "locked": locked}
    aggregate = {}
    incidental_by_stratum = {}
    surface_union_by_stratum = {}
    surface_features = {
        set_name: [(record, v._surface_features(record)) for record in records]
        for set_name, records in records_by_set.items()
    }
    numeric_surfaces = {
        "signed_numeric_surface",
        "decimal_surface",
        "fraction_surface",
    }
    for set_name, rows in surface_features.items():
        aggregate[set_name] = {
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
                record["stratum"] in ("S07", "S08", "S10")
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
                bool(features & numeric_surfaces) for _, features in rows
            ),
            "signed_surface": sum(
                "signed_numeric_surface" in features for _, features in rows
            ),
            "truly_empty_output": sum(
                not record["output_text"].strip() for record, _ in rows
            ),
        }
        incidental_by_stratum[set_name] = {
            stratum: sum(
                record["stratum"] == stratum
                and "incidental_numeric_distractor" in features
                for record, features in rows
            )
            for stratum in ("S07", "S08", "S10")
        }
        surface_union_by_stratum[set_name] = {
            stratum: sum(
                record["stratum"] == stratum
                and bool(features & numeric_surfaces)
                for record, features in rows
            )
            for stratum in ("S01", "S02", "S03", "S04", "S05", "S06", "S09")
        }
    return {
        "development": aggregate["development"],
        "locked": aggregate["locked"],
        "incidental_numeric_distractor_by_stratum": incidental_by_stratum,
        "answer_bearing_surface_union_by_stratum": surface_union_by_stratum,
        "s06_rightmost_distractor_canonical_difference": (
            v._derived_validity_report(records_by_set, stratum="S06")
        ),
        "s11_at_least_two_distinct_canonical_candidates": (
            v._derived_validity_report(records_by_set, stratum="S11")
        ),
    }


def _exact_count_tables(development, locked, pools):
    records_by_set = {"development": development, "locked": locked}
    correctness = {
        set_name: {
            stratum: {
                "correct": sum(
                    row["stratum"] == stratum
                    and row["expected_correctness"] is True
                    for row in records
                ),
                "incorrect": sum(
                    row["stratum"] == stratum
                    and row["expected_correctness"] is False
                    for row in records
                ),
            }
            for stratum in v.ANSWER_BEARING_STRATA
        }
        for set_name, records in records_by_set.items()
    }

    def boolean_counts(field):
        return {
            set_name: {
                "false": sum(row[field] is False for row in records),
                "true": sum(row[field] is True for row in records),
            }
            for set_name, records in records_by_set.items()
        }

    by_curator = {
        set_name: {
            curator_id: sum(
                row["curator_id"] == curator_id for row in records
            )
            for curator_id in v.SEALED_CURATOR_IDENTITIES
        }
        for set_name, records in records_by_set.items()
    }
    by_stratum = {
        set_name: {
            stratum: sum(row["stratum"] == stratum for row in records)
            for stratum in v.STRATA
        }
        for set_name, records in records_by_set.items()
    }
    by_slot = {
        set_name: {
            stratum: {
                label: sum(
                    row["stratum"] == stratum
                    and row["subtype_slot"] == slot
                    for row in records
                )
                for label, slot in zip(
                    v.PROTOCOL_SUBTYPE_LABELS[stratum],
                    v.SUBTYPE_SLOTS[stratum],
                    strict=True,
                )
            }
            for stratum in v.STRATA
        }
        for set_name, records in records_by_set.items()
    }
    locked_slot_curators = {
        stratum: {
            label: {
                curator_id: sum(
                    row["stratum"] == stratum
                    and row["subtype_slot"] == slot
                    and row["curator_id"] == curator_id
                    for row in locked
                )
                for curator_id in v.SEALED_CURATOR_IDENTITIES
            }
            for label, slot in zip(
                v.PROTOCOL_SUBTYPE_LABELS[stratum],
                v.SUBTYPE_SLOTS[stratum],
                strict=True,
            )
        }
        for stratum in v.STRATA
    }
    return {
        "answer_bearing_correctness_by_stratum": correctness,
        "by_critical_case": boolean_counts("critical_case"),
        "by_curator": by_curator,
        "by_material_error_if_missed": boolean_counts(
            "material_error_if_missed"
        ),
        "by_proposed_parse_ambiguous": boolean_counts(
            "expected_parse_ambiguous"
        ),
        "by_proposed_parse_valid": boolean_counts("expected_parse_valid"),
        "by_stratum": by_stratum,
        "by_stratum_and_subtype_slot": by_slot,
        "dataset": {
            "candidate_pool_total": len(pools),
            "development": len(development),
            "locked": len(locked),
            "selected_total": len(development) + len(locked),
            "unselected": len(pools) - len(development) - len(locked),
        },
        "locked_slot_curator_counts": locked_slot_curators,
        "typed_decision_support": {
            set_name: {
                presence: sum(
                    row["expected_answer_presence"] == presence
                    for row in records
                )
                for presence in ("present", "ambiguous", "no_answer")
            }
            for set_name, records in records_by_set.items()
        },
    }


def _dataset():
    internal_pools = {
        curator: [
            _candidate(curator, stratum, index)
            for stratum in v.STRATA
            for index in range(12)
        ]
        for curator in ("curator_a", "curator_b")
    }
    pools = {
        curator: [
            _external_proposal(
                candidate, human_subtype=curator == "curator_b"
            )
            for candidate in internal_pools[curator]
        ]
        for curator in ("curator_a", "curator_b")
    }
    seals = {
        curator: v.build_curator_pool_seal(
            pools[curator],
            curator_id=v.SEALED_CURATOR_IDENTITIES[
                0 if curator == "curator_a" else 1
            ],
            constructed_after_protocol_utc="2026-07-15T18:18:52Z",
        )
        for curator in ("curator_a", "curator_b")
    }
    seals["curator_b"]["no_model_run_attestation"] = _pool_attestation_b()
    selected_development = []
    selected_locked = []
    not_selected_alternative = []
    for candidate in sorted(
        [*pools["curator_a"], *pools["curator_b"]],
        key=lambda item: item["candidate_id"],
    ):
        index = int(candidate["candidate_id"].rsplit("-", 1)[1])
        if index < 5:
            disposition = "locked"
        elif index < 10 and (
            (
                candidate["stratum"] in v.STRATA[:6]
                and candidate["curator_id"] == v.SEALED_CURATOR_IDENTITIES[0]
            )
            or (
                candidate["stratum"] in v.STRATA[6:]
                and candidate["curator_id"] == v.SEALED_CURATOR_IDENTITIES[1]
            )
        ):
            disposition = "development"
        else:
            disposition = "rejected"
        target = {
            "development": selected_development,
            "locked": selected_locked,
            "rejected": not_selected_alternative,
        }[disposition]
        target.append(candidate["candidate_id"])
    normalized_pools = {
        curator: v.validate_curator_pool_seal(
            seals[curator],
            pools[curator],
            expected_curator_id=v.SEALED_CURATOR_IDENTITIES[
                0 if curator == "curator_a" else 1
            ],
        )["records"]
        for curator in ("curator_a", "curator_b")
    }
    normalized_by_id = {
        candidate["candidate_id"]: candidate
        for candidate in [
            *normalized_pools["curator_a"],
            *normalized_pools["curator_b"],
        ]
    }
    selected_records = {
        "development": [
            normalized_by_id[candidate_id]
            for candidate_id in selected_development
        ],
        "locked": [
            normalized_by_id[candidate_id] for candidate_id in selected_locked
        ],
    }
    composition = v.validate_dataset_composition(
        selected_records["development"], selected_records["locked"]
    )
    near_evidence = v._near_pair_evidence(
        [
            *selected_records["development"],
            *selected_records["locked"],
        ]
    )
    flags = [
        {
            "candidate_ids": list(pair),
            "disposition": (
                "keep_global_minimum_under_frozen_constraints"
            ),
            "jaccard": (
                str(evidence["similarity"].numerator)
                if evidence["similarity"].denominator == 1
                else (
                    f"{evidence['similarity'].numerator}/"
                    f"{evidence['similarity'].denominator}"
                )
            ),
            "masked_5gram_intersection_count": evidence[
                "intersection_count"
            ],
            "masked_5gram_union_count": evidence["union_count"],
        }
        for pair, evidence in sorted(near_evidence.items())
    ]
    development_id_set = set(selected_development)
    locked_id_set = set(selected_locked)
    near_scope_counts = {
        "development_development": sum(
            set(pair) <= development_id_set for pair in near_evidence
        ),
        "development_locked": sum(
            bool(set(pair) & development_id_set)
            and bool(set(pair) & locked_id_set)
            for pair in near_evidence
        ),
        "locked_locked": sum(
            set(pair) <= locked_id_set for pair in near_evidence
        ),
    }
    plan = {
        "actual_derived_feature_counts": _actual_feature_report(
            selected_records["development"], selected_records["locked"]
        ),
        "candidate_dispositions": {
            "selected_development_candidate_ids": list(selected_development),
            "selected_locked_candidate_ids": list(selected_locked),
            "not_selected_duplicate_exclusion_candidate_ids": [],
            "not_selected_alternative_candidate_ids": list(
                not_selected_alternative
            ),
        },
        "candidate_jsonl_sha256s": {
            v.SEALED_CURATOR_IDENTITIES[0]: seals["curator_a"][
                "candidate_jsonl_sha256"
            ],
            v.SEALED_CURATOR_IDENTITIES[1]: seals["curator_b"][
                "candidate_jsonl_sha256"
            ],
        },
        "constructed_after_protocol_utc": "2026-07-15T19:00:00Z",
        "construction_intent_warning": (
            "Construction intent only; independent review remains required."
        ),
        "count_tables": _exact_count_tables(
            selected_records["development"],
            selected_records["locked"],
            list(normalized_by_id.values()),
        ),
        "curator_id": "evaluator-case-curator-c",
        "curator_model_id": v.REVIEWER_MODEL_ID,
        "curator_reasoning_effort": v.REVIEWER_REASONING_EFFORT,
        "excluded_duplicate_groups": [],
        "excluded_duplicate_ids": [],
        "feature_derivation": {
            "derived_from_validated_content": True,
            "status": "PASS",
        },
        "final_protocol_bindings": {
            "acceptance_gate_sha256": v.FROZEN_ACCEPTANCE_GATE_SHA256,
            "phase": v.FROZEN_PROTOCOL_PHASE,
            "protocol_bundle_sha256": v.FROZEN_PROTOCOL_BUNDLE_SHA256,
            "protocol_commit": v.FROZEN_PROTOCOL_COMMIT,
            "protocol_commit_utc": v.FROZEN_PROTOCOL_COMMIT_UTC,
            "protocol_file_sha256s": deepcopy(
                v.FROZEN_PROTOCOL_FILE_SHA256S
            ),
            "protocol_version": v.FROZEN_PROTOCOL_VERSION,
        },
        "locked_label_status": "construction_intent_only",
        "near_duplicate_screening": {
            "algorithm": {
                "character_ngram_n": 5,
                "jaccard_threshold": "0.85",
                "numeric_mask": "<NUM>",
                "text_preprocessing": (
                    "frozen_normalized_text_then_registered_ascii_numeric_mask"
                ),
            },
            "dispositions_complete": True,
            "flag_count": len(flags),
            "flags": flags,
            "global_minimum_flag_count": len(flags),
            "non_s12_flag_count": sum(
                any(normalized_by_id[item]["stratum"] != "S12" for item in pair)
                for pair in near_evidence
            ),
            "scope_counts": near_scope_counts,
            "selected_pair_count_screened": 180 * 179 // 2,
            "optimization": {
                "mip_gap": "0",
                "primary_objective": "minimum_selected_flag_count",
                "primary_status": "optimal",
                "secondary_objective": "minimum_non_s12_flags",
                "secondary_status": "optimal",
            },
        },
        "no_model_run_attestation": _curator_c_attestation(),
        "overlap_validation": {
            "selected_hard_failure_count": 0,
            "selected_overlap_free": True,
            "status": "PASS",
        },
        "pool_seal_sha256s": {
            v.SEALED_CURATOR_IDENTITIES[0]: v.curator_pool_seal_sha256(
                seals["curator_a"]
            ),
            v.SEALED_CURATOR_IDENTITIES[1]: v.curator_pool_seal_sha256(
                seals["curator_b"]
            ),
        },
        "pool_summary_sha256s": {
            v.SEALED_CURATOR_IDENTITIES[0]: "c" * 64,
            v.SEALED_CURATOR_IDENTITIES[1]: "d" * 64,
        },
        "pool_validation": {
            "both_pools_valid": True,
            "status": "PASS",
        },
        "quota_validation": {
            "all_quotas_met": True,
            "status": "PASS",
        },
        "schema_version": v.CURATOR_C_SELECTION_SCHEMA_VERSION,
        "selected_temp_candidate_ids": {
            "development": list(selected_development),
            "locked": list(selected_locked),
        },
        "status": "PASS",
    }
    candidate_by_id = {
        record["candidate_id"]: record
        for record in (*pools["curator_a"], *pools["curator_b"])
    }
    selected_overlap = v.detect_fixture_overlaps(
        [candidate_by_id[item] for item in selected_development],
        [candidate_by_id[item] for item in selected_locked],
    )
    near_non_s12 = sum(
        any(
            candidate_by_id[item]["stratum"] != "S12"
            for item in flag["candidate_ids"]
        )
        for flag in flags
    )
    summary = {
        "constructed_after_protocol_utc": plan[
            "constructed_after_protocol_utc"
        ],
        "counts": {
            "candidate_pool_total": 288,
            "development": len(selected_development),
            "duplicate_groups_observed": len(
                plan["excluded_duplicate_groups"]
            ),
            "excluded_duplicate_ids": len(plan["excluded_duplicate_ids"]),
            "locked": len(selected_locked),
            "near_duplicate_flags": len(flags),
            "near_duplicate_non_s12_flags": near_non_s12,
            "selected_exact_duplicates": len(
                selected_overlap["exact_duplicates"]
            ),
            "selected_frozen_normalized_duplicates": len(
                selected_overlap["normalized_duplicates"]
            ),
            "selected_total": len(selected_development) + len(selected_locked),
            "template_family_overlaps": len(
                selected_overlap["cross_set_template_family_overlaps"]
            ),
            "unselected": len(not_selected_alternative)
            + len(plan["excluded_duplicate_ids"]),
        },
        "curator_id": plan["curator_id"],
        "curator_model_id": plan["curator_model_id"],
        "curator_reasoning_effort": plan["curator_reasoning_effort"],
        "hashes": {
            "candidate_jsonl_sha256s": deepcopy(
                plan["candidate_jsonl_sha256s"]
            ),
            "pool_seal_sha256s": deepcopy(plan["pool_seal_sha256s"]),
            "selection_sha256": v.sha256_bytes(v.canonical_json_bytes(plan)),
        },
        "protocol_bindings": {
            key: deepcopy(plan["final_protocol_bindings"][key])
            for key in (
                "acceptance_gate_sha256",
                "protocol_bundle_sha256",
                "protocol_commit",
            )
        },
        "schema_version": v.CURATOR_C_SUMMARY_SCHEMA_VERSION,
        "status": "PASS",
    }
    v.validate_curator_c_summary(
        summary,
        plan,
        selection_sha256=summary["hashes"]["selection_sha256"],
        candidate_records=[*pools["curator_a"], *pools["curator_b"]],
    )
    selected = v.validate_selection_plan(
        plan,
        pools["curator_a"],
        pools["curator_b"],
        seals["curator_a"],
        seals["curator_b"],
    )
    salts = {
        "schema_version": v.PRIVATE_SALTS_SCHEMA_VERSION,
        "development_id_salt": "development-private-salt-0001",
        "locked_id_salt": "locked-private-salt-0000000002",
    }
    materialized = v.materialize_selection(selected, salts)
    mapping = v.build_case_mapping(
        materialized,
        salts,
        selected["selection_plan_sha256"],
        curator_c_id=selected["curator_c_id"],
        custodian_id=v.REGISTERED_CUSTODIAN_ID,
        curator_pool_seals=selected["curator_pool_seals"],
    )
    return {
        "pools": pools,
        "normalized_pools": normalized_pools,
        "seals": seals,
        "plan": plan,
        "summary": summary,
        "salts": salts,
        "selected": selected,
        "materialized": materialized,
        "mapping": mapping,
    }


@pytest.fixture(scope="module")
def dataset():
    return _dataset()


def _parser_result(label: dict, *, decision: str | None = None) -> dict:
    if decision is None:
        presence = {
            "present": "present",
            "ambiguous": "uncertain",
            "no_answer": "absent",
        }[label["expected_answer_presence"]]
        fields = {
            field: deepcopy(label[f"expected_{field}"])
            for field in (
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
    elif decision == "no_answer":
        presence = "absent"
        fields = {
            "parse_valid": False,
            "parse_ambiguous": False,
            "parsed_answer": None,
            "candidate_answers": [],
            "evidence_spans": [],
            "extraction_strategy": "none",
            "output_quality": "complete",
            "failure_reasons": ["no_reliable_answer"],
            "format_warnings": [],
        }
    else:
        raise AssertionError(decision)
    return {
        "schema_version": v.PARSER_RESULT_SCHEMA_VERSION,
        "parser_version": "a" * 64,
        "answer_type": "numeric",
        "input_sha256": v.sha256_bytes(label["output_text"].encode()),
        "answer_presence": presence,
        **fields,
    }


def _prediction_envelopes(
    labels: list[dict], locked_inputs: list[dict]
) -> list[dict]:
    labels_by_id = {label["case_id"]: label for label in labels}
    envelopes = []
    for outer in locked_inputs:
        request = v.project_parser_request(outer)
        envelopes.append(
            {
                "schema_version": v.PREDICTION_ENVELOPE_SCHEMA_VERSION,
                "case_id": outer["case_id"],
                "input_record_sha256": v.sha256_bytes(
                    v.canonical_json_bytes(outer)
                ),
                "parser_request_sha256": v.sha256_bytes(
                    v.canonical_json_bytes(request)
                ),
                "parser_result": _parser_result(labels_by_id[outer["case_id"]]),
            }
        )
    return envelopes


def _sealed_predictions(dataset, labels: list[dict] | None = None):
    active_labels = (
        dataset["materialized"]["locked_draft_labels"]
        if labels is None
        else labels
    )
    locked = dataset["materialized"]["locked_inputs"]
    predictions = _prediction_envelopes(active_labels, locked)
    implementation_commit = "c" * 40
    seal = v.build_prediction_seal(
        predictions,
        locked,
        implementation_commit=implementation_commit,
        sealed_utc="2026-07-15T12:00:00Z",
    )
    return predictions, seal, implementation_commit


def _legacy_predictions(labels: list[dict]) -> list[dict]:
    result = []
    degraded = False
    for label in labels:
        presence = label["expected_answer_presence"]
        if (
            label["stratum"] in v.CRITICAL_STRATA
            and presence == "present"
            and not degraded
        ):
            legacy = {
                "parse_valid": False,
                "parse_ambiguous": False,
                "parsed_answer": None,
            }
            degraded = True
        elif presence == "present":
            legacy = {
                "parse_valid": True,
                "parse_ambiguous": False,
                "parsed_answer": label["expected_parsed_answer"],
            }
        elif presence == "ambiguous":
            legacy = {
                "parse_valid": True,
                "parse_ambiguous": True,
                "parsed_answer": label["expected_candidate_answers"][0],
            }
        else:
            legacy = {
                "parse_valid": False,
                "parse_ambiguous": False,
                "parsed_answer": None,
            }
        result.append({"case_id": label["case_id"], **legacy})
    return result


def test_canonical_ascii_json_and_jsonl_round_trip():
    value = {"z": "雪", "a": 1}
    data = v.canonical_json_bytes(value)
    assert data == b'{"a":1,"z":"\\u96ea"}\n'
    assert v.parse_json_strict(data, "value.json") == value
    rows = [{"z": 2, "a": "line\nvalue"}]
    jsonl = v.canonical_jsonl_bytes(rows)
    assert len(jsonl.splitlines()) == 1
    assert v.parse_jsonl_strict(jsonl, "rows.jsonl") == rows


def test_duplicate_json_keys_and_noncanonical_bytes_are_rejected():
    with pytest.raises(v.ValidationSetError, match="duplicate JSON key"):
        v.parse_json_strict(b'{"a":1,"a":2}\n', "duplicate.json")
    with pytest.raises(v.ValidationSetError, match="canonical"):
        v.parse_json_strict(b'{"z":1, "a":2}\n', "unsorted.json")


def test_nonfinite_json_is_rejected_on_read_and_write():
    with pytest.raises(v.ValidationSetError, match="non-finite"):
        v.parse_json_strict(b'{"value":NaN}\n', "nan.json")
    with pytest.raises(v.ValidationSetError, match="non-finite"):
        v.canonical_json_bytes({"value": math.inf})


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("+0012", "12"),
        ("-0.000", "0"),
        (".5", "1/2"),
        ("1.25", "5/4"),
        ("5e-1", "1/2"),
        ("-6/8", "-3/4"),
        ("10/5", "2"),
    ],
)
def test_exact_rational_normalization(surface, expected):
    assert v.normalize_rational_literal(surface) == expected


@pytest.mark.parametrize(
    "surface",
    (
        "1 /2",
        "1/-2",
        "1.0/2",
        "1/0",
        "1,000",
        "NaN",
        "Infinity",
        "1+2",
        "",
        "1" * 101,
    ),
)
def test_rational_grammar_rejects_unregistered_forms(surface):
    with pytest.raises(v.ValidationSetError):
        v.normalize_rational_literal(surface)


def test_evidence_spans_use_unicode_code_point_offsets():
    output = "雪 Answer: -6/8."
    start = output.index("-6/8")
    span = {
        "start": start,
        "end": start + 4,
        "text": "-6/8",
        "kind": "explicit_answer_marker",
        "normalized_answer": "-3/4",
        "disposition": "selected",
    }
    assert v.validate_evidence_span(span, output)["start"] == start
    broken = dict(span, end=span["end"] + 1)
    with pytest.raises(v.ValidationSetError, match="offsets"):
        v.validate_evidence_span(broken, output)


def test_evidence_normalized_answer_must_equal_exact_span_normalization():
    output = "Answer: -6/8."
    start = output.index("-6/8")
    span = {
        "start": start,
        "end": start + 4,
        "text": "-6/8",
        "kind": "explicit_answer_marker",
        "normalized_answer": "3/4",
        "disposition": "selected",
    }
    with pytest.raises(v.ValidationSetError, match="does not match exact span"):
        v.validate_evidence_span(span, output)
    span["normalized_answer"] = "-3/4"
    v.validate_evidence_span(span, output)


def test_extreme_exponents_fail_quickly_with_controlled_validation():
    with pytest.raises(v.ValidationSetError, match="4096"):
        v.normalize_rational_literal("1e5000")
    with pytest.raises(v.ValidationSetError, match="4096"):
        v.normalize_rational_literal("0e" + "9" * 97)
    with pytest.raises(v.ValidationSetError):
        v.normalize_rational_literal("1e" + "9" * 99)
    with pytest.raises(v.ValidationSetError, match="4096"):
        v.normalize_rational_literal(("9" * 90) + "e-4090")


def test_numeric_token_context_rejects_version_percentage_and_identifier():
    for output, text in (
        ("version 1.2.3", "1.2"),
        ("score 50%", "50"),
        ("value 12kg", "12"),
        ("Answer: +5", "5"),
        ("Answer: .5", "5"),
        ("cost $5", "5"),
        ("temperature 5°C", "5"),
    ):
        start = output.index(text)
        span = {
            "start": start,
            "end": start + len(text),
            "text": text,
            "kind": "single_candidate",
            "normalized_answer": v.normalize_rational_literal(text),
            "disposition": "selected",
        }
        with pytest.raises(v.ValidationSetError):
            v.validate_evidence_span(span, output)


def test_typed_decision_class_requires_canonical_present_value():
    assert v.typed_decision_class("present:1/2") == "present"
    with pytest.raises(v.ValidationSetError, match="canonical"):
        v.typed_decision_class("present:0.5")


def test_invalid_closed_enum_fails_candidate_validation(dataset):
    candidate = deepcopy(dataset["normalized_pools"]["curator_a"][0])
    candidate["expected_output_quality"] = "almost_complete"
    with pytest.raises(v.ValidationSetError, match="invalid value"):
        v.validate_candidate_fixture(candidate)


def test_locked_input_omits_labels_and_projection_has_exact_three_fields(dataset):
    locked = dataset["materialized"]["locked_inputs"][0]
    assert set(locked) == {
        "schema_version",
        "case_id",
        "source_kind",
        "output_text",
        "parse_type",
    }
    request = v.project_parser_request(locked)
    assert request == {
        "schema_version": v.PARSER_REQUEST_SCHEMA_VERSION,
        "answer_type": "numeric",
        "output_text": locked["output_text"],
    }
    assert "case_id" not in request
    assert "registered_reference_answer" not in request


def test_locked_input_rejects_label_leak_and_final_label_requires_all_fields(dataset):
    locked = dict(dataset["materialized"]["locked_inputs"][0])
    locked["registered_reference_answer"] = "1"
    with pytest.raises(v.ValidationSetError, match="extra"):
        v.validate_locked_input(locked)
    label = dict(dataset["materialized"]["locked_draft_labels"][0])
    del label["expected_correctness"]
    with pytest.raises(v.ValidationSetError, match="missing"):
        v.validate_final_label(label)


def test_typed_decision_derivation_for_all_three_classes(dataset):
    labels = dataset["materialized"]["locked_draft_labels"]
    decisions = {v.derive_typed_decision(label) for label in labels}
    assert "ambiguous" in decisions
    assert "no_answer" in decisions
    assert any(decision.startswith("present:") for decision in decisions)


def test_legacy_ambiguous_adapter_precedence_and_failure_diagnostic():
    ambiguous = v.adapt_legacy_result(
        {
            "parse_ambiguous": True,
            "parse_valid": True,
            "parsed_answer": "2",
            "correctness": True,
        }
    )
    assert ambiguous["typed_decision"] == "ambiguous"
    assert v.adapt_legacy_result(
        {
            "parse_ambiguous": False,
            "parse_valid": True,
            "parsed_answer": "-6/8",
        }
    )["typed_decision"] == "present:-3/4"
    failed = v.adapt_legacy_result(
        {
            "parse_ambiguous": False,
            "parse_valid": True,
            "parsed_answer": "1,000",
        }
    )
    assert failed == {
        "typed_decision": "no_answer",
        "adapter_failure": "nonnormalizable_legacy_answer",
    }


def test_frozen_protocol_hash_uses_git_blobs_not_checkout_line_endings():
    expected = hashlib.sha256()
    expected.update(v.PROTOCOL_BUNDLE_HASH_DOMAIN)
    for relative in v.PROTOCOL_FILES:
        blob = v.git_blob_bytes(ROOT, v.FROZEN_PROTOCOL_COMMIT, relative)
        path = relative.encode("ascii")
        expected.update(len(path).to_bytes(4, "big"))
        expected.update(path)
        expected.update(len(blob).to_bytes(8, "big"))
        expected.update(blob)
    digest = v.protocol_bundle_sha256(ROOT)
    assert digest == expected.hexdigest()
    protocol_blob = v.git_blob_bytes(
        ROOT, v.FROZEN_PROTOCOL_COMMIT, v.PROTOCOL_FILES[0]
    )
    crlf_copy = protocol_blob.replace(b"\n", b"\r\n")
    assert hashlib.sha256(crlf_copy).hexdigest() != hashlib.sha256(
        protocol_blob
    ).hexdigest()
    assert v.protocol_bundle_sha256(ROOT) == digest


def test_final_v12_protocol_bindings_are_exact():
    assert (
        v.FROZEN_PROTOCOL_COMMIT
        == "cc93ffe603ab8338ed860586a52b1911af4b3277"
    )
    assert (
        v.FROZEN_PROTOCOL_BUNDLE_SHA256
        == "5d486a53b532012c3a64eb6bd962be325fb9892ebbb042807b919f9e41b23666"
    )
    assert (
        v.FROZEN_ACCEPTANCE_GATE_SHA256
        == "a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988"
    )
    assert v.FROZEN_PROTOCOL_PHASE == "1.2A/Path C"
    assert v.FROZEN_PROTOCOL_COMMIT_UTC == "2026-07-15T18:18:51Z"
    assert v.FROZEN_PROTOCOL_VERSION == "parser-v2-v1.2"
    assert v.SEALED_CURATOR_IDENTITIES == (
        "evaluator-case-curator-a",
        "evaluator-case-curator-b",
    )
    assert v.FROZEN_PROTOCOL_FILE_SHA256S == {
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
    assert v.protocol_bundle_sha256(ROOT) == v.FROZEN_PROTOCOL_BUNDLE_SHA256
    assert v.acceptance_gates_sha256(ROOT) == v.FROZEN_ACCEPTANCE_GATE_SHA256


def test_curator_pools_have_exactly_twelve_per_stratum(dataset):
    for index, curator in enumerate(("curator_a", "curator_b")):
        report = v.validate_curator_pool(
            dataset["normalized_pools"][curator],
            v.SEALED_CURATOR_IDENTITIES[index],
        )
        assert report["candidate_count"] == 144
        assert set(report["stratum_counts"].values()) == {12}


def test_curator_pool_seals_are_exact_and_selection_binds_both(dataset):
    for index, curator in enumerate(("curator_a", "curator_b")):
        seal = dataset["seals"][curator]
        assert set(seal) == v._CURATOR_POOL_SEAL_FIELDS
        result = v.validate_curator_pool_seal(
            seal,
            v.canonical_jsonl_bytes(dataset["pools"][curator]),
            expected_curator_id=v.SEALED_CURATOR_IDENTITIES[index],
        )
        assert result["candidate_count"] == 144
        assert result["candidate_jsonl_sha256"] == seal[
            "candidate_jsonl_sha256"
        ]
    tampered = deepcopy(dataset["seals"]["curator_a"])
    tampered["candidate_jsonl_sha256"] = "1" * 64
    with pytest.raises(v.ValidationSetError, match="candidate JSONL hash"):
        v.validate_curator_pool_seal(
            tampered, dataset["pools"]["curator_a"]
        )
    plan = deepcopy(dataset["plan"])
    plan["pool_seal_sha256s"][v.SEALED_CURATOR_IDENTITIES[0]] = "2" * 64
    with pytest.raises(v.ValidationSetError, match="hash bindings mismatch"):
        v.validate_selection_plan(
            plan,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )


def test_external_attestation_variants_are_structured_and_exact(dataset):
    assert (
        dataset["seals"]["curator_a"]["no_model_run_attestation"]
        == _pool_attestation_a()
    )
    assert (
        dataset["seals"]["curator_b"]["no_model_run_attestation"]
        == _pool_attestation_b()
    )
    assert dataset["plan"]["no_model_run_attestation"] == (
        _curator_c_attestation()
    )
    assert set(_pool_attestation_a()) == set(
        v.CuratorPoolNoModelAttestationA.__required_keys__
    )
    assert set(_pool_attestation_b()) == set(
        v.CuratorPoolNoModelAttestationB.__required_keys__
    )
    assert set(_curator_c_attestation()) == set(
        v.CuratorCNoModelAttestation.__required_keys__
    )
    assert v.validate_external_no_model_run_attestation(
        _pool_attestation_a(), context="curator_pool"
    ) == _pool_attestation_a()
    assert v.validate_external_no_model_run_attestation(
        _pool_attestation_b(), context="curator_pool"
    ) == _pool_attestation_b()
    assert v.validate_external_no_model_run_attestation(
        _curator_c_attestation(), context="curator_c_selection"
    ) == _curator_c_attestation()


@pytest.mark.parametrize(
    ("context", "value"),
    [
        ("curator_pool", True),
        (
            "curator_pool",
            {
                **_pool_attestation_a(),
                "unregistered_attestation_field": False,
            },
        ),
        (
            "curator_pool",
            {
                key: value
                for key, value in _pool_attestation_a().items()
                if key != "network_access_used"
            },
        ),
        (
            "curator_pool",
            {**_pool_attestation_a(), "network_access_used": True},
        ),
        (
            "curator_pool",
            {
                **_pool_attestation_a(),
                "fixtures_constructed_model_free": False,
            },
        ),
        (
            "curator_pool",
            {
                **_pool_attestation_a(),
                "target_model_downloaded_or_loaded": True,
            },
        ),
        (
            "curator_pool",
            {
                **_pool_attestation_a(),
                "target_model_inference_performed": True,
            },
        ),
        (
            "curator_pool",
            {**_pool_attestation_b(), "target_model_downloaded": True},
        ),
        (
            "curator_pool",
            {**_pool_attestation_b(), "target_model_inference_run": True},
        ),
        (
            "curator_pool",
            {
                **_pool_attestation_b(),
                "target_model_id": "DeepSeek-R1-Distill-Qwen-1.5B",
            },
        ),
        (
            "curator_pool",
            {**_pool_attestation_b(), "target_model_loaded": True},
        ),
        ("curator_c_selection", True),
        (
            "curator_c_selection",
            {
                **_curator_c_attestation(),
                "fixtures_constructed_model_free": False,
            },
        ),
        (
            "curator_c_selection",
            {
                **_curator_c_attestation(),
                "new_cases_generated_by_curator_c": True,
            },
        ),
        (
            "curator_c_selection",
            {
                **_curator_c_attestation(),
                "target_model_downloaded": True,
            },
        ),
        (
            "curator_c_selection",
            {
                **_curator_c_attestation(),
                "target_model_inference_run": True,
            },
        ),
        (
            "curator_c_selection",
            {
                **_curator_c_attestation(),
                "target_model_loaded": True,
            },
        ),
        (
            "curator_c_selection",
            {
                **_curator_c_attestation(),
                "target_model_id": "deepseek-ai/wrong-model",
            },
        ),
    ],
)
def test_external_attestation_rejects_non_proof_variants(context, value):
    with pytest.raises(v.ValidationSetError):
        v.validate_external_no_model_run_attestation(
            value,
            context=context,
        )


def test_external_attestation_is_enforced_on_every_ingress_path(dataset):
    bad_seal = deepcopy(dataset["seals"]["curator_a"])
    bad_seal["no_model_run_attestation"] = True
    with pytest.raises(v.ValidationSetError, match="structured object"):
        v.validate_curator_pool_seal(
            bad_seal, dataset["pools"]["curator_a"]
        )
    with pytest.raises(v.ValidationSetError, match="structured object"):
        v.curator_pool_seal_sha256(bad_seal)

    bad_selection = deepcopy(dataset["plan"])
    bad_selection["no_model_run_attestation"] = True
    with pytest.raises(v.ValidationSetError, match="structured object"):
        v.validate_selection_plan(
            bad_selection,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )

    bad_mapping = deepcopy(dataset["mapping"])
    bad_mapping["curator_pool_seals"][0][
        "no_model_run_attestation"
    ] = True
    with pytest.raises(v.ValidationSetError, match="structured object"):
        v.validate_case_mapping(bad_mapping)


def test_production_hash_constants_are_frozen():
    assert v.ELIGIBLE_PRODUCTION_ARTIFACT_SHA256 == {
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
    superseded = {
        "7b43f0fefc4d94546ce44422d66766496c92548caebc381540cd75556bd8a120",
        "2b76ac5112819c8c667cafd052474ede455e918bcde62d332ea6648679a229b7",
    }
    assert not superseded & set(v.ELIGIBLE_PRODUCTION_ARTIFACT_SHA256.values())
    assert v.ELIGIBLE_PRODUCTION_CURATOR_C_SUMMARY_COUNTS == {
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
    assert v.HISTORICAL_FINGERPRINT_ARTIFACT_HASHES == {
        "historical_output_fingerprints.jsonl": (
            "58adac43e7e825e92d1aa23e062ee6a554a5eedc59274fabdb21685a981839a2"
        ),
        "historical_output_fingerprint_summary.json": (
            "eb076251d30a803d7283d0e17dfda9074c676b3c11ac095ff7d3b586f7fbabdb"
        ),
    }


@pytest.mark.parametrize(
    ("artifact_name", "superseded_sha256"),
    (
        (
            "curator_c_selection",
            "7b43f0fefc4d94546ce44422d66766496c92548caebc381540cd75556bd8a120",
        ),
        (
            "curator_c_summary",
            "2b76ac5112819c8c667cafd052474ede455e918bcde62d332ea6648679a229b7",
        ),
    ),
)
def test_production_hash_gate_rejects_superseded_curator_c_artifacts(
    artifact_name, superseded_sha256, monkeypatch
):
    artifact_bytes = {
        name: name.encode("ascii")
        for name in v.ELIGIBLE_PRODUCTION_ARTIFACT_SHA256
    }
    reported_hashes = dict(v.ELIGIBLE_PRODUCTION_ARTIFACT_SHA256)
    reported_hashes[artifact_name] = superseded_sha256
    monkeypatch.setattr(
        v,
        "sha256_bytes",
        lambda data: reported_hashes[data.decode("ascii")],
    )
    with pytest.raises(v.ValidationSetError, match="hash mismatch"):
        v.validate_eligible_production_bundle(artifact_bytes)


def _synthetic_production_bundle(dataset) -> dict[str, bytes]:
    return {
        "curator_a_candidate_jsonl": v.canonical_jsonl_bytes(
            dataset["pools"]["curator_a"]
        ),
        "curator_a_pool_seal": v.canonical_json_bytes(
            dataset["seals"]["curator_a"]
        ),
        "curator_b_candidate_jsonl": v.canonical_jsonl_bytes(
            dataset["pools"]["curator_b"]
        ),
        "curator_b_pool_seal": v.canonical_json_bytes(
            dataset["seals"]["curator_b"]
        ),
        "curator_c_selection": v.canonical_json_bytes(dataset["plan"]),
        "curator_c_summary": v.canonical_json_bytes(dataset["summary"]),
    }


def _register_synthetic_production_hashes(
    monkeypatch, bundle, module=v
) -> None:
    monkeypatch.setattr(
        module,
        "ELIGIBLE_PRODUCTION_ARTIFACT_SHA256",
        {
            name: v.sha256_bytes(data)
            for name, data in bundle.items()
        },
    )
    monkeypatch.setattr(
        module,
        "ELIGIBLE_PRODUCTION_CURATOR_C_SUMMARY_COUNTS",
        deepcopy(
            v.parse_json_strict(
                bundle["curator_c_summary"], "synthetic Curator-C summary"
            )["counts"]
        ),
    )


def test_production_bundle_hash_gate_and_summary_bindings(dataset, monkeypatch):
    bundle = _synthetic_production_bundle(dataset)
    with pytest.raises(v.ValidationSetError, match="hash mismatch"):
        v.validate_eligible_production_bundle(bundle)

    _register_synthetic_production_hashes(monkeypatch, bundle)
    validated = v.validate_eligible_production_bundle(bundle)
    assert len(validated["curator_a"]) == 144
    assert len(validated["curator_b"]) == 144
    assert validated["summary"]["counts"] == dataset["summary"]["counts"]

    wrong_summary = deepcopy(dataset["summary"])
    wrong_summary["counts"]["locked"] = 119
    tampered_bundle = {
        **bundle,
        "curator_c_summary": v.canonical_json_bytes(wrong_summary),
    }
    _register_synthetic_production_hashes(monkeypatch, tampered_bundle)
    with pytest.raises(v.ValidationSetError, match="counts mismatch"):
        v.validate_eligible_production_bundle(tampered_bundle)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("nested_count", "counts mismatch"),
        ("nested_hash", "named pool bindings"),
        ("timestamp", "timestamp binding"),
        ("model", "model/effort binding"),
    ),
)
def test_curator_c_summary_rejects_wrong_nested_bindings(
    dataset, mutation, message
):
    summary = deepcopy(dataset["summary"])
    if mutation == "nested_count":
        summary["counts"]["near_duplicate_flags"] += 1
    elif mutation == "nested_hash":
        summary["hashes"]["candidate_jsonl_sha256s"][
            v.SEALED_CURATOR_IDENTITIES[0]
        ] = "f" * 64
    elif mutation == "timestamp":
        summary["constructed_after_protocol_utc"] = "2026-07-15T19:00:01Z"
    else:
        summary["curator_model_id"] = "gpt-5.5"
    with pytest.raises(v.ValidationSetError, match=message):
        v.validate_curator_c_summary(
            summary,
            dataset["plan"],
            selection_sha256=dataset["summary"]["hashes"]["selection_sha256"],
            candidate_records=[
                *dataset["pools"]["curator_a"],
                *dataset["pools"]["curator_b"],
            ],
        )


def test_production_bundle_rejects_self_consistent_unregistered_replacement(
    dataset,
):
    replacement = _synthetic_production_bundle(dataset)
    replacement_plan = deepcopy(dataset["plan"])
    replacement_plan["construction_intent_warning"] += " replacement"
    replacement_summary = deepcopy(dataset["summary"])
    replacement_summary["hashes"]["selection_sha256"] = v.sha256_bytes(
        v.canonical_json_bytes(replacement_plan)
    )
    replacement["curator_c_selection"] = v.canonical_json_bytes(
        replacement_plan
    )
    replacement["curator_c_summary"] = v.canonical_json_bytes(
        replacement_summary
    )
    with pytest.raises(v.ValidationSetError, match="hash mismatch"):
        v.validate_eligible_production_bundle(replacement)


def test_builder_cli_hash_gates_bundle_before_build(
    dataset, monkeypatch, capsys
):
    bundle = _synthetic_production_bundle(dataset)
    path_to_key = {
        "a-pool": "curator_a_candidate_jsonl",
        "a-seal": "curator_a_pool_seal",
        "b-pool": "curator_b_candidate_jsonl",
        "b-seal": "curator_b_pool_seal",
        "selection": "curator_c_selection",
        "summary": "curator_c_summary",
    }
    monkeypatch.setattr(
        builder, "validate_external_staging_root", lambda value: Path(value)
    )
    monkeypatch.setattr(
        builder,
        "validate_external_private_path",
        lambda value, **_kwargs: Path(value),
    )
    monkeypatch.setattr(
        builder,
        "_read_regular_bytes",
        lambda path, _name: bundle[path_to_key[str(path)]],
    )
    build_called = False

    def should_not_build(*_args, **_kwargs):
        nonlocal build_called
        build_called = True
        raise AssertionError("unregistered bundle reached build")

    monkeypatch.setattr(builder, "build_validation_drafts", should_not_build)
    result = builder.main(
        [
            "--curator-a-pool",
            "a-pool",
            "--curator-a-seal",
            "a-seal",
            "--curator-b-pool",
            "b-pool",
            "--curator-b-seal",
            "b-seal",
            "--selection-plan",
            "selection",
            "--curator-c-summary",
            "summary",
            "--private-salts",
            "salts",
            "--historical-generations",
            "generations",
            "--historical-evaluations",
            "evaluations",
            "--output-root",
            "output",
        ]
    )
    assert result == 2
    assert build_called is False
    assert capsys.readouterr().err == (
        "validation-set build failed; no artifact data emitted\n"
    )


def test_external_candidate_rows_are_exact_hash_source_and_normalize(dataset):
    raw = dataset["pools"]["curator_b"]
    assert set(raw[0]) == set(v.CuratorCandidateProposal.__required_keys__)
    raw_bytes = v.canonical_jsonl_bytes(raw)
    bound = v.validate_curator_pool_seal(
        dataset["seals"]["curator_b"], raw_bytes
    )
    assert bound["raw_records"] == raw
    assert bound["candidate_jsonl_sha256"] == v.sha256_bytes(raw_bytes)
    assert v.sha256_bytes(v.canonical_jsonl_bytes(bound["records"])) != bound[
        "candidate_jsonl_sha256"
    ]
    assert {
        row["subtype_slot"]
        for row in bound["records"]
        if row["stratum"] == "S02"
    } == set(v.SUBTYPE_SLOTS["S02"])
    assert any(
        row["subtype_slot"] == "Final answer:"
        for row in raw
        if row["stratum"] == "S02"
    )

    changed = deepcopy(raw)
    changed[0]["construction_notes"] += " changed after sealing"
    with pytest.raises(v.ValidationSetError, match="candidate JSONL hash"):
        v.validate_curator_pool_seal(
            dataset["seals"]["curator_b"],
            v.canonical_jsonl_bytes(changed),
        )


def test_external_reference_surface_normalizes_before_correctness(dataset):
    pool = deepcopy(dataset["pools"]["curator_a"])
    proposal = next(
        row for row in pool if row["candidate_id"] == "A-S01-00"
    )
    canonical = proposal["registered_reference_answer"]
    assert canonical == proposal["proposed_expected_parsed_answer"]
    proposal["registered_reference_answer"] = f"{canonical}.0"
    raw_bytes = v.canonical_jsonl_bytes(pool)
    seal = v.build_curator_pool_seal(
        pool,
        curator_id=v.SEALED_CURATOR_IDENTITIES[0],
        constructed_after_protocol_utc="2026-07-15T18:18:52Z",
    )
    bound = v.validate_curator_pool_seal(
        seal,
        raw_bytes,
        expected_curator_id=v.SEALED_CURATOR_IDENTITIES[0],
    )
    normalized = next(
        row for row in bound["records"] if row["candidate_id"] == "A-S01-00"
    )

    assert bound["raw_records"] == pool
    assert bound["candidate_jsonl_sha256"] == v.sha256_bytes(raw_bytes)
    assert normalized["registered_reference_answer"] == canonical
    assert normalized["expected_correctness"] is True
    v.validate_candidate_fixture(normalized)


@pytest.mark.parametrize(
    "reference_surface",
    (
        "not-a-number",
        "1e5000",
        "1" * (v.MAX_NUMERIC_LITERAL_CHARACTERS + 1),
    ),
)
def test_external_reference_surface_rejects_invalid_or_oversized_values(
    dataset, reference_surface
):
    proposal = deepcopy(dataset["pools"]["curator_a"][0])
    proposal["registered_reference_answer"] = reference_surface
    with pytest.raises(
        v.ValidationSetError, match="not a supported numeric surface"
    ):
        v.validate_curator_candidate_proposal(
            proposal,
            expected_curator_id=v.SEALED_CURATOR_IDENTITIES[0],
        )


def test_external_presence_mapping_and_unknown_alias_rejection(dataset):
    normalized = {
        row["candidate_id"]: row
        for row in v.validate_curator_pool_seal(
            dataset["seals"]["curator_a"], dataset["pools"]["curator_a"]
        )["records"]
    }
    assert normalized["A-S01-00"]["expected_answer_presence"] == "present"
    assert normalized["A-S07-00"]["expected_answer_presence"] == "no_answer"
    assert normalized["A-S11-00"]["expected_answer_presence"] == "ambiguous"

    unknown = deepcopy(
        next(
            row
            for row in dataset["pools"]["curator_b"]
            if row["stratum"] == "S02"
        )
    )
    unknown["subtype_slot"] = "answer marker, approximately"
    with pytest.raises(v.ValidationSetError, match="registered alias"):
        v.validate_curator_candidate_proposal(unknown)


@pytest.mark.parametrize(
    ("stratum", "external_alias", "internal_slot"),
    [
        ("S02", "answer_colon", "answer_marker"),
        ("S02", "final_answer", "final_answer_marker"),
        ("S02", "the_answer_is", "the_answer_is"),
        ("S02", "final_marker", "final_marker"),
        (
            "S02",
            "case_colon_newline_variant",
            "case_colon_newline_variant",
        ),
        (
            "S03",
            "prose_lead_in_terminal_equation",
            "prose_then_terminal_equation",
        ),
        (
            "S04",
            "balanced_think_working_final_outside",
            "balanced_think_working",
        ),
        ("S06", "rating_confidence", "rating_or_confidence"),
        ("S06", "count_metadata", "count_or_metadata"),
        ("S08", "empty_wrapper", "empty_or_empty_wrapper"),
        ("S08", "ellipsis_na", "ellipsis_or_na"),
        (
            "S09",
            "encoding_markup_noise",
            "encoding_or_markup_noise",
        ),
    ],
)
def test_curator_a_external_subtype_aliases_normalize(
    dataset, stratum, external_alias, internal_slot
):
    proposal = next(
        row
        for row in dataset["pools"]["curator_a"]
        if row["stratum"] == stratum
        and row["subtype_slot"] == external_alias
    )
    assert v.validate_curator_candidate_proposal(proposal)[
        "subtype_slot"
    ] == internal_slot


def test_curator_a_external_subtype_alias_rejects_unknown(dataset):
    proposal = deepcopy(
        next(
            row
            for row in dataset["pools"]["curator_a"]
            if row["stratum"] == "S02"
        )
    )
    proposal["subtype_slot"] = "answer-colon"
    with pytest.raises(v.ValidationSetError, match="registered alias"):
        v.validate_curator_candidate_proposal(proposal)


def test_external_secondary_tag_vocabularies_normalize_strictly(dataset):
    a_by_id = {
        row["candidate_id"]: row for row in dataset["pools"]["curator_a"]
    }
    b_by_id = {
        row["candidate_id"]: row for row in dataset["pools"]["curator_b"]
    }
    assert "balanced_think_tags" in a_by_id["A-S01-00"][
        "secondary_tags"
    ]
    assert "malformed_think_tags" in a_by_id["A-S01-01"][
        "secondary_tags"
    ]
    assert "balanced_think_tag" in b_by_id["B-S01-00"][
        "secondary_tags"
    ]
    assert "malformed_think_tag" in b_by_id["B-S01-01"][
        "secondary_tags"
    ]
    assert "signed_surface" in a_by_id["A-S01-00"]["secondary_tags"]
    assert "rightmost_numeric_distractor" in a_by_id["A-S06-00"][
        "secondary_tags"
    ]

    expected = [
        tag
        for tag in v.SECONDARY_TAGS
        if tag in set(v.EXTERNAL_SECONDARY_TAG_ALIASES.values())
    ]
    assert v.normalize_external_secondary_tags(
        list(v.EXTERNAL_SECONDARY_TAGS)
    ) == expected

    proposal = deepcopy(a_by_id["A-S01-00"])
    proposal["secondary_tags"].extend(
        ["balanced_think_tag", "noncanonical_numeric_surface"]
    )
    raw_tags = deepcopy(proposal["secondary_tags"])
    normalized = v.validate_curator_candidate_proposal(proposal)
    assert proposal["secondary_tags"] == raw_tags
    assert normalized["secondary_tags"].count("balanced_think_tags") == 1
    assert "signed_numeric_surface" in normalized["secondary_tags"]
    assert "noncanonical_numeric_surface" in normalized["secondary_tags"]
    assert normalized["secondary_tags"] == sorted(
        normalized["secondary_tags"], key=v.SECONDARY_TAGS.index
    )


def test_external_secondary_tags_reject_unknown_and_duplicate(dataset):
    base = deepcopy(dataset["pools"]["curator_a"][0])

    unknown = deepcopy(base)
    unknown["secondary_tags"].append("unregistered_external_tag")
    with pytest.raises(v.ValidationSetError, match="invalid value"):
        v.validate_curator_candidate_proposal(unknown)

    duplicate = deepcopy(base)
    duplicate["secondary_tags"].append(duplicate["secondary_tags"][0])
    with pytest.raises(v.ValidationSetError, match="duplicate external tag"):
        v.validate_curator_candidate_proposal(duplicate)


def test_external_advisory_quota_tags_are_derived_not_trusted(dataset):
    raw_by_id = {
        row["candidate_id"]: row for row in dataset["pools"]["curator_a"]
    }
    missing = deepcopy(raw_by_id["A-S01-05"])
    missing["secondary_tags"] = [
        tag
        for tag in missing["secondary_tags"]
        if v.EXTERNAL_SECONDARY_TAG_ALIASES[tag]
        not in v.QUOTA_DIAGNOSTIC_TAGS
    ]
    derived = v.validate_curator_candidate_proposal(missing)
    assert {
        "signed_numeric_surface",
        "negative_answer",
        "balanced_think_tags",
    }.issubset(derived["secondary_tags"])

    false_advisory = deepcopy(raw_by_id["A-S01-08"])
    false_advisory["secondary_tags"].append("decimal_surface")
    discarded = v.validate_curator_candidate_proposal(false_advisory)
    assert "decimal_surface" not in discarded["secondary_tags"]

    development = deepcopy(dataset["selected"]["development"])
    baseline = v.validate_dataset_composition(
        development, dataset["selected"]["locked"]
    )
    replacements = {
        derived["candidate_id"]: derived,
        discarded["candidate_id"]: discarded,
    }
    development = [
        replacements.get(row["candidate_id"], row) for row in development
    ]
    recomputed = v.validate_dataset_composition(
        development, dataset["selected"]["locked"]
    )
    assert recomputed["feature_counts"] == baseline["feature_counts"]


@pytest.mark.parametrize(
    ("output_text", "expected"),
    [
        ("plain output", (False, False)),
        ("<think>working</think> answer", (True, False)),
        ("<think>working", (False, True)),
        ("<think working without close bracket", (False, True)),
        ("</ThInK trailing fragment", (False, True)),
        ("<thinking>not a registered tag</thinking>", (False, True)),
        (
            "<think>working</think> trailing <THINK",
            (False, True),
        ),
        (
            "<think><think>nested</think></think>",
            (False, True),
        ),
    ],
)
def test_think_tag_features_detect_complete_and_fragmented_lexemes(
    output_text, expected
):
    assert v._think_tag_features(output_text) == expected


@pytest.mark.parametrize(
    "section",
    (
        "aggregate",
        "incidental_by_stratum",
        "surface_union_by_stratum",
        "s06_validity",
        "s11_validity",
        "top_extra",
        "nested_missing",
    ),
)
def test_actual_derived_feature_counts_are_exactly_recomputed(dataset, section):
    claims = deepcopy(dataset["plan"]["actual_derived_feature_counts"])
    if section == "aggregate":
        claims["development"]["balanced_think_tags"] += 1
    elif section == "incidental_by_stratum":
        claims["incidental_numeric_distractor_by_stratum"]["development"][
            "S07"
        ] += 1
    elif section == "surface_union_by_stratum":
        claims["answer_bearing_surface_union_by_stratum"]["locked"]["S01"] += 1
    elif section == "s06_validity":
        claims["s06_rightmost_distractor_canonical_difference"][
            "invalid_selected_candidate_ids"
        ] = ["A-S06-05"]
    elif section == "s11_validity":
        claims["s11_at_least_two_distinct_canonical_candidates"][
            "locked_valid_case_count"
        ] -= 1
    elif section == "top_extra":
        claims["unregistered"] = {}
    else:
        claims["locked"].pop("truly_empty_output")
    with pytest.raises(v.ValidationSetError):
        v._validate_actual_derived_feature_counts(
            claims,
            dataset["selected"]["development"],
            dataset["selected"]["locked"],
        )


@pytest.mark.parametrize(
    "section",
    (
        "correctness",
        "critical_false_true",
        "curator",
        "material",
        "parse_ambiguous",
        "parse_valid",
        "stratum",
        "slot_label",
        "dataset",
        "locked_slot_curator",
        "support",
    ),
)
def test_curator_c_count_tables_are_exactly_recomputed(dataset, section):
    claims = deepcopy(dataset["plan"]["count_tables"])
    if section == "correctness":
        claims["answer_bearing_correctness_by_stratum"]["development"]["S01"][
            "correct"
        ] += 1
    elif section == "critical_false_true":
        counts = claims["by_critical_case"]["development"]
        counts["false"] += 1
        counts["true"] -= 1
    elif section == "curator":
        claims["by_curator"]["locked"][v.SEALED_CURATOR_IDENTITIES[0]] += 1
    elif section == "material":
        claims["by_material_error_if_missed"]["development"]["false"] += 1
    elif section == "parse_ambiguous":
        claims["by_proposed_parse_ambiguous"]["locked"]["true"] += 1
    elif section == "parse_valid":
        claims["by_proposed_parse_valid"]["development"]["false"] += 1
    elif section == "stratum":
        claims["by_stratum"]["locked"]["S12"] += 1
    elif section == "slot_label":
        slots = claims["by_stratum_and_subtype_slot"]["development"]["S01"]
        value = slots.pop(v.PROTOCOL_SUBTYPE_LABELS["S01"][0])
        slots["unregistered slot label"] = value
    elif section == "dataset":
        claims["dataset"]["selected_total"] += 1
    elif section == "locked_slot_curator":
        label = v.PROTOCOL_SUBTYPE_LABELS["S01"][0]
        claims["locked_slot_curator_counts"]["S01"][label][
            v.SEALED_CURATOR_IDENTITIES[0]
        ] += 1
    else:
        claims["typed_decision_support"]["development"]["present"] += 1
    with pytest.raises(v.ValidationSetError):
        v._validate_curator_c_count_tables(
            claims,
            selected=dataset["selected"],
            pools=[
                *dataset["normalized_pools"]["curator_a"],
                *dataset["normalized_pools"]["curator_b"],
            ],
        )


def test_curator_c_artifact_bytes_are_accepted_and_bound(dataset):
    source = v.canonical_json_bytes(dataset["plan"])
    selected = v.validate_curator_c_selection(
        source,
        dataset["pools"]["curator_a"],
        dataset["pools"]["curator_b"],
        dataset["seals"]["curator_a"],
        dataset["seals"]["curator_b"],
    )
    assert len(selected["development"]) == 60
    assert len(selected["locked"]) == 120
    assert selected["selection_plan_sha256"] == v.sha256_bytes(source)
    assert v.validate_dataset_composition(
        selected["development"], selected["locked"]
    )["locked_count"] == 120


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("phase", "protocol bindings mismatch"),
        ("protocol_version", "protocol bindings mismatch"),
        ("protocol_commit_utc", "protocol bindings mismatch"),
        ("protocol_file_sha256s", "protocol bindings mismatch"),
        ("extra", "fields differ"),
    ),
)
def test_curator_c_selection_rejects_wrong_extended_protocol_binding(
    dataset, mutation, message
):
    plan = deepcopy(dataset["plan"])
    bindings = plan["final_protocol_bindings"]
    if mutation == "phase":
        bindings["phase"] = "1.2A/Path B"
    elif mutation == "protocol_version":
        bindings["protocol_version"] = "parser-v2-v1.1"
    elif mutation == "protocol_commit_utc":
        bindings["protocol_commit_utc"] = "2026-07-15T18:18:52Z"
    elif mutation == "protocol_file_sha256s":
        bindings["protocol_file_sha256s"][
            "docs/phase1_parser_v2_protocol.md"
        ] = "f" * 64
    else:
        bindings["unexpected_binding"] = "forbidden"
    with pytest.raises(v.ValidationSetError, match=message):
        v.validate_selection_plan(
            plan,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )


def test_curator_c_false_report_and_hash_binding_fail(dataset):
    false_report = deepcopy(dataset["plan"])
    false_report["quota_validation"]["all_quotas_met"] = False
    with pytest.raises(v.ValidationSetError, match="failed condition"):
        v.validate_selection_plan(
            false_report,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )

    wrong_overlap = deepcopy(dataset["plan"])
    wrong_overlap["overlap_validation"]["selected_hard_failure_count"] = 1
    with pytest.raises(v.ValidationSetError, match="differs from recomputation"):
        v.validate_selection_plan(
            wrong_overlap,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )

    wrong_hash = deepcopy(dataset["plan"])
    wrong_hash["candidate_jsonl_sha256s"][
        v.SEALED_CURATOR_IDENTITIES[1]
    ] = "f" * 64
    with pytest.raises(v.ValidationSetError, match="hash bindings mismatch"):
        v.validate_selection_plan(
            wrong_hash,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )

    for field in ("candidate_jsonl_sha256s", "pool_seal_sha256s"):
        crossed = deepcopy(dataset["plan"])
        hashes = crossed[field]
        curator_a, curator_b = v.SEALED_CURATOR_IDENTITIES
        hashes[curator_a], hashes[curator_b] = (
            hashes[curator_b],
            hashes[curator_a],
        )
        with pytest.raises(
            v.ValidationSetError, match="named hash bindings mismatch"
        ):
            v.validate_selection_plan(
                crossed,
                dataset["pools"]["curator_a"],
                dataset["pools"]["curator_b"],
                dataset["seals"]["curator_a"],
                dataset["seals"]["curator_b"],
            )


@pytest.mark.parametrize(
    "field",
    (
        "candidate_jsonl_sha256s",
        "pool_seal_sha256s",
        "pool_summary_sha256s",
    ),
)
def test_curator_c_selection_rejects_synthetic_pool_hash_aliases(dataset, field):
    plan = deepcopy(dataset["plan"])
    hashes = plan[field]
    plan[field] = {
        "curator_a": hashes[v.SEALED_CURATOR_IDENTITIES[0]],
        "curator_b": hashes[v.SEALED_CURATOR_IDENTITIES[1]],
    }
    with pytest.raises(v.ValidationSetError, match="fields differ"):
        v.validate_selection_plan(
            plan,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )


@pytest.mark.parametrize(
    "field", ("candidate_jsonl_sha256s", "pool_seal_sha256s")
)
def test_curator_c_summary_rejects_synthetic_pool_hash_aliases(dataset, field):
    summary = deepcopy(dataset["summary"])
    hashes = summary["hashes"][field]
    summary["hashes"][field] = {
        "curator_a": hashes[v.SEALED_CURATOR_IDENTITIES[0]],
        "curator_b": hashes[v.SEALED_CURATOR_IDENTITIES[1]],
    }
    with pytest.raises(v.ValidationSetError, match="fields differ"):
        v.validate_curator_c_summary(
            summary,
            dataset["plan"],
            selection_sha256=dataset["summary"]["hashes"]["selection_sha256"],
            candidate_records=[
                *dataset["pools"]["curator_a"],
                *dataset["pools"]["curator_b"],
            ],
        )


def _near_screening_record(
    flags,
    *,
    non_s12_flag_count=0,
    scope_counts=None,
    selected_pair_count_screened=1,
):
    if scope_counts is None:
        scope_counts = {
            "development_development": 0,
            "development_locked": len(flags),
            "locked_locked": 0,
        }
    return {
        "algorithm": {
            "character_ngram_n": 5,
            "jaccard_threshold": "0.85",
            "numeric_mask": "<NUM>",
            "text_preprocessing": (
                "frozen_normalized_text_then_registered_ascii_numeric_mask"
            ),
        },
        "dispositions_complete": True,
        "flag_count": len(flags),
        "flags": flags,
        "global_minimum_flag_count": len(flags),
        "non_s12_flag_count": non_s12_flag_count,
        "optimization": {
            "mip_gap": "0",
            "primary_objective": "minimum_selected_flag_count",
            "primary_status": "optimal",
            "secondary_objective": "minimum_non_s12_flags",
            "secondary_status": "optimal",
        },
        "scope_counts": scope_counts,
        "selected_pair_count_screened": selected_pair_count_screened,
    }


def test_near_duplicate_exact_empty_ngram_evidence_is_supported():
    evidence = {
        ("A-short", "B-short"): {
            "intersection_count": 0,
            "union_count": 0,
            "similarity": Fraction(1, 1),
        }
    }
    report = _near_screening_record(
        [
            {
                "candidate_ids": ["A-short", "B-short"],
                "disposition": "keep_global_minimum_under_frozen_constraints",
                "jaccard": "1",
                "masked_5gram_intersection_count": 0,
                "masked_5gram_union_count": 0,
            }
        ]
    )
    assert v._validate_near_duplicate_screening(
        report,
        evidence,
        development=[{"candidate_id": "A-short", "stratum": "S12"}],
        locked=[{"candidate_id": "B-short", "stratum": "S12"}],
    ) == [
        {
            "left_candidate_id": "A-short",
            "right_candidate_id": "B-short",
            "decision": "keep",
            "reason": "keep_global_minimum_under_frozen_constraints",
        }
    ]


@pytest.mark.parametrize(
    "disposition", v.CURATOR_C_NEAR_DUPLICATE_DISPOSITIONS
)
def test_near_duplicate_registered_dispositions_become_keep_reasons(disposition):
    result = v._validate_near_duplicate_screening(
        _near_screening_record(
            [
                {
                    "candidate_ids": ["A-near", "B-near"],
                    "disposition": disposition,
                    "jaccard": "17/20",
                    "masked_5gram_intersection_count": 17,
                    "masked_5gram_union_count": 20,
                }
            ]
        ),
        {
            ("A-near", "B-near"): {
                "intersection_count": 17,
                "union_count": 20,
                "similarity": Fraction(17, 20),
            }
        },
        development=[{"candidate_id": "A-near", "stratum": "S12"}],
        locked=[{"candidate_id": "B-near", "stratum": "S12"}],
    )
    assert result[0]["decision"] == "keep"
    assert result[0]["reason"] == disposition


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("missing", "fields differ"),
        ("extra", "fields differ"),
        ("unknown_disposition", "invalid value"),
        ("unsorted_ids", "sorted two-ID pair"),
        ("wrong_jaccard", "Jaccard value mismatch"),
        ("wrong_counts", "5-gram counts mismatch"),
    ),
)
def test_near_duplicate_flag_rejects_noncanonical_schema_or_evidence(
    mutation, message
):
    flag = {
        "candidate_ids": ["A-near", "B-near"],
        "disposition": "keep_global_minimum_under_frozen_constraints",
        "jaccard": "17/20",
        "masked_5gram_intersection_count": 17,
        "masked_5gram_union_count": 20,
    }
    if mutation == "missing":
        flag.pop("jaccard")
    elif mutation == "extra":
        flag["reason"] = "unregistered duplicate reason field"
    elif mutation == "unknown_disposition":
        flag["disposition"] = "keep_arbitrary_unregistered_reason"
    elif mutation == "unsorted_ids":
        flag["candidate_ids"] = ["B-near", "A-near"]
    elif mutation == "wrong_jaccard":
        flag["jaccard"] = "9/10"
    else:
        flag["masked_5gram_intersection_count"] = 18
    with pytest.raises(v.ValidationSetError, match=message):
        v._validate_near_duplicate_screening(
            _near_screening_record([flag]),
            {
                ("A-near", "B-near"): {
                    "intersection_count": 17,
                    "union_count": 20,
                    "similarity": Fraction(17, 20),
                }
            },
            development=[{"candidate_id": "A-near", "stratum": "S12"}],
            locked=[{"candidate_id": "B-near", "stratum": "S12"}],
        )


def test_curator_c_near_screening_is_selected_only_and_complete(dataset):
    screening = dataset["plan"]["near_duplicate_screening"]
    selected_ids = {
        *dataset["plan"]["selected_temp_candidate_ids"]["development"],
        *dataset["plan"]["selected_temp_candidate_ids"]["locked"],
    }
    assert screening["selected_pair_count_screened"] == 16110
    assert sum(screening["scope_counts"].values()) == screening["flag_count"]
    assert sum(screening["scope_counts"].values()) != screening[
        "selected_pair_count_screened"
    ]
    assert all(
        set(flag["candidate_ids"]).issubset(selected_ids)
        for flag in screening["flags"]
    )
    selected = v.validate_selection_plan(
        dataset["plan"],
        dataset["pools"]["curator_a"],
        dataset["pools"]["curator_b"],
        dataset["seals"]["curator_a"],
        dataset["seals"]["curator_b"],
    )
    assert len(selected["near_duplicate_dispositions"]) == len(
        screening["flags"]
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("primary_status", "optimization is not registered"),
        ("secondary_status", "optimization is not registered"),
        ("primary_objective", "optimization is not registered"),
        ("secondary_objective", "optimization is not registered"),
        ("mip_gap", "optimization is not registered"),
        ("algorithm", "algorithm is not registered"),
        ("top_extra", "fields differ"),
        ("optimization_extra", "fields differ"),
    ),
)
def test_curator_c_near_screening_rejects_wrong_optimization_schema(
    dataset, mutation, message
):
    plan = deepcopy(dataset["plan"])
    screening = plan["near_duplicate_screening"]
    if mutation == "algorithm":
        screening["algorithm"]["character_ngram_n"] = 4
    elif mutation == "top_extra":
        screening["unregistered"] = True
    elif mutation == "optimization_extra":
        screening["optimization"]["unregistered"] = "forbidden"
    elif mutation == "mip_gap":
        screening["optimization"]["mip_gap"] = "0.01"
    elif mutation == "primary_status":
        screening["optimization"]["primary_status"] = "PASS"
    elif mutation == "secondary_status":
        screening["optimization"]["secondary_status"] = "PASS"
    elif mutation == "primary_objective":
        screening["optimization"]["primary_objective"] = "arbitrary"
    else:
        screening["optimization"]["secondary_objective"] = "arbitrary"
    with pytest.raises(v.ValidationSetError, match=message):
        v.validate_selection_plan(
            plan,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )


def test_curator_c_near_screening_rejects_unselected_flag(dataset):
    plan = deepcopy(dataset["plan"])
    unselected_id = plan["candidate_dispositions"][
        "not_selected_alternative_candidate_ids"
    ][0]
    selected_id = plan["selected_temp_candidate_ids"]["development"][0]
    plan["near_duplicate_screening"]["flags"].append(
        {
            "candidate_ids": sorted([unselected_id, selected_id]),
            "disposition": "keep_global_minimum_under_frozen_constraints",
            "jaccard": "1",
            "masked_5gram_intersection_count": 0,
            "masked_5gram_union_count": 0,
        }
    )
    with pytest.raises(v.ValidationSetError, match="unselected candidate pair"):
        v.validate_selection_plan(
            plan,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )


def test_curator_c_near_screening_rejects_missing_selected_flag():
    with pytest.raises(v.ValidationSetError, match="exactly cover selected findings"):
        v._validate_near_duplicate_screening(
            _near_screening_record([]),
            {
                ("A-selected", "B-selected"): {
                    "intersection_count": 17,
                    "union_count": 20,
                    "similarity": Fraction(17, 20),
                }
            },
            development=[
                {"candidate_id": "A-selected", "stratum": "S01"}
            ],
            locked=[{"candidate_id": "B-selected", "stratum": "S01"}],
        )


def test_curator_c_near_screening_rejects_wrong_flag_scope_partition():
    flag = {
        "candidate_ids": ["A-selected", "B-selected"],
        "disposition": "keep_global_minimum_under_frozen_constraints",
        "jaccard": "17/20",
        "masked_5gram_intersection_count": 17,
        "masked_5gram_union_count": 20,
    }
    with pytest.raises(v.ValidationSetError, match="scope_counts mismatch"):
        v._validate_near_duplicate_screening(
            _near_screening_record(
                [flag],
                non_s12_flag_count=1,
                scope_counts={
                    "development_development": 1,
                    "development_locked": 0,
                    "locked_locked": 0,
                },
            ),
            {
                ("A-selected", "B-selected"): {
                    "intersection_count": 17,
                    "union_count": 20,
                    "similarity": Fraction(17, 20),
                }
            },
            development=[
                {"candidate_id": "A-selected", "stratum": "S01"}
            ],
            locked=[{"candidate_id": "B-selected", "stratum": "S01"}],
        )


def test_internal_selection_plan_cannot_replace_curator_c_artifact(dataset):
    internal = {
        "schema_version": v.SELECTION_PLAN_SCHEMA_VERSION,
        "custodian_id": "evaluator-case-curator-c",
        "curator_a_pool_seal_sha256": "1" * 64,
        "curator_a_candidate_jsonl_sha256": "2" * 64,
        "curator_b_pool_seal_sha256": "3" * 64,
        "curator_b_candidate_jsonl_sha256": "4" * 64,
        "entries": [],
        "near_duplicate_dispositions": [],
    }
    with pytest.raises(v.ValidationSetError, match="fields differ"):
        v.validate_selection_plan(
            internal,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )


def test_curator_pool_seal_must_postdate_final_protocol(dataset):
    with pytest.raises(v.ValidationSetError, match="after the final protocol"):
        v.build_curator_pool_seal(
            dataset["pools"]["curator_a"],
            curator_id=v.SEALED_CURATOR_IDENTITIES[0],
            constructed_after_protocol_utc=v.FROZEN_PROTOCOL_COMMIT_UTC,
        )


def test_quota_tags_must_equal_content_derived_features(dataset):
    signed = deepcopy(dataset["normalized_pools"]["curator_a"][0])
    signed["secondary_tags"].remove("signed_numeric_surface")
    with pytest.raises(v.ValidationSetError, match="content-derived"):
        v.validate_candidate_fixture(signed)
    integer = deepcopy(dataset["normalized_pools"]["curator_a"][3])
    integer["secondary_tags"] = _ordered_tags(
        *integer["secondary_tags"], "fraction_surface"
    )
    with pytest.raises(v.ValidationSetError, match="content-derived"):
        v.validate_candidate_fixture(integer)


def test_selection_plan_enforces_60_120_and_authorship(dataset):
    selected = v.validate_selection_plan(
        dataset["plan"],
        dataset["pools"]["curator_a"],
        dataset["pools"]["curator_b"],
        dataset["seals"]["curator_a"],
        dataset["seals"]["curator_b"],
    )
    assert len(selected["development"]) == 60
    assert len(selected["locked"]) == 120
    assert {item["curator_id"] for item in selected["locked"]} == {
        *v.SEALED_CURATOR_IDENTITIES,
    }


def test_selection_plan_rejects_wrong_development_authorship(dataset):
    plan = deepcopy(dataset["plan"])
    selected_id = "A-S01-08"
    replacement_id = "B-S01-08"
    for path in (
        ("selected_temp_candidate_ids", "development"),
        ("candidate_dispositions", "selected_development_candidate_ids"),
    ):
        values = plan[path[0]][path[1]]
        values[values.index(selected_id)] = replacement_id
    alternatives = plan["candidate_dispositions"][
        "not_selected_alternative_candidate_ids"
    ]
    alternatives[alternatives.index(replacement_id)] = selected_id
    with pytest.raises(v.ValidationSetError):
        v.validate_selection_plan(
            plan,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )


def test_deterministic_ids_order_bytes_hashes_and_mapping(dataset):
    first = dataset["materialized"]
    second = v.materialize_selection(dataset["selected"], dataset["salts"])
    first_development = v.canonical_jsonl_bytes(first["development"])
    second_development = v.canonical_jsonl_bytes(second["development"])
    assert first_development == second_development
    assert v.sha256_bytes(first_development) == v.sha256_bytes(second_development)
    development_ids = [row["case_id"] for row in first["development"]]
    locked_ids = [row["case_id"] for row in first["locked_inputs"]]
    assert development_ids == sorted(development_ids)
    assert locked_ids == sorted(locked_ids)
    assert all(v._CASE_ID_PATTERN.fullmatch(case_id) for case_id in development_ids)
    assert set(development_ids).isdisjoint(locked_ids)
    assert v.validate_case_mapping(dataset["mapping"])["counts"] == {
        "development": 60,
        "locked": 120,
    }


def test_exact_60_120_strata_support_and_cross_cutting_quotas(dataset):
    report = v.validate_dataset_composition(
        dataset["materialized"]["development"],
        dataset["materialized"]["locked_draft_labels"],
    )
    assert report["development_support"] == {
        "present": 40,
        "ambiguous": 5,
        "no_answer": 15,
    }
    assert report["locked_support"] == {
        "present": 80,
        "ambiguous": 10,
        "no_answer": 30,
    }


def test_composition_rejects_wrong_count(dataset):
    with pytest.raises(v.ValidationSetError, match="60/120"):
        v.validate_dataset_composition(
            dataset["materialized"]["development"][:-1],
            dataset["materialized"]["locked_draft_labels"],
        )


def _make_s08_empty(record):
    record["output_text"] = ""
    record["expected_output_quality"] = "empty"
    record["expected_failure_reasons"] = ["empty_output"]
    record["secondary_tags"] = []


def _make_s08_nonempty_wrapper(record):
    record["output_text"] = "[no answer wrapper]"
    record["expected_output_quality"] = "placeholder"
    record["expected_failure_reasons"] = ["placeholder_without_answer"]
    record["secondary_tags"] = _ordered_tags("placeholder_output")


def test_composition_allows_zero_development_empty_outputs(dataset):
    development = deepcopy(dataset["selected"]["development"])
    empty = next(record for record in development if not record["output_text"].strip())
    assert empty["stratum"] == "S08"
    assert empty["subtype_slot"] == "empty_or_empty_wrapper"
    _make_s08_nonempty_wrapper(empty)

    report = v.validate_dataset_composition(
        development, dataset["selected"]["locked"]
    )

    assert report["development_count"] == 60
    assert not any(not record["output_text"].strip() for record in development)


def test_composition_allows_one_development_empty_output(dataset):
    report = v.validate_dataset_composition(
        dataset["selected"]["development"], dataset["selected"]["locked"]
    )
    assert report["development_count"] == 60
    assert (
        sum(
            not record["output_text"].strip()
            for record in dataset["selected"]["development"]
        )
        == 1
    )


def test_composition_rejects_two_development_empty_outputs(dataset):
    development = deepcopy(dataset["selected"]["development"])
    second = next(
        record
        for record in development
        if record["stratum"] == "S08" and record["output_text"].strip()
    )
    _make_s08_empty(second)
    with pytest.raises(v.ValidationSetError, match="at most one"):
        v.validate_dataset_composition(
            development, dataset["selected"]["locked"]
        )


def test_composition_rejects_locked_empty_output(dataset):
    development = deepcopy(dataset["selected"]["development"])
    existing = next(
        record for record in development if not record["output_text"].strip()
    )
    _make_s08_nonempty_wrapper(existing)
    locked = deepcopy(dataset["selected"]["locked"])
    locked_s08 = next(
        record
        for record in locked
        if record["stratum"] == "S08" and record["output_text"].strip()
    )
    _make_s08_empty(locked_s08)
    with pytest.raises(v.ValidationSetError, match="only in development"):
        v.validate_dataset_composition(development, locked)


def test_selection_requires_one_development_case_per_subtype_slot(dataset):
    plan = deepcopy(dataset["plan"])
    selected_id = "A-S01-08"
    replacement_id = "A-S01-10"
    for path in (
        ("selected_temp_candidate_ids", "development"),
        ("candidate_dispositions", "selected_development_candidate_ids"),
    ):
        values = plan[path[0]][path[1]]
        values[values.index(selected_id)] = replacement_id
    alternatives = plan["candidate_dispositions"][
        "not_selected_alternative_candidate_ids"
    ]
    alternatives[alternatives.index(replacement_id)] = selected_id
    normalized_by_id = {
        row["candidate_id"]: row
        for rows in dataset["normalized_pools"].values()
        for row in rows
    }
    development = [
        normalized_by_id[candidate_id]
        for candidate_id in plan["selected_temp_candidate_ids"]["development"]
    ]
    locked = [
        normalized_by_id[candidate_id]
        for candidate_id in plan["selected_temp_candidate_ids"]["locked"]
    ]
    plan["actual_derived_feature_counts"] = _actual_feature_report(
        development,
        locked,
    )
    plan["count_tables"] = _exact_count_tables(
        development,
        locked,
        list(normalized_by_id.values()),
    )
    with pytest.raises(v.ValidationSetError, match="one case per subtype slot"):
        v.validate_selection_plan(
            plan,
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
        )


def test_final_locked_labels_must_preserve_five_five_correctness(dataset):
    labels = deepcopy(dataset["materialized"]["locked_draft_labels"])
    target = next(
        label
        for label in labels
        if label["stratum"] == "S01" and label["expected_correctness"]
    )
    target["registered_reference_answer"] = "999999"
    target["expected_correctness"] = False
    with pytest.raises(v.ValidationSetError, match="5 correct/5 incorrect"):
        v._validate_locked_label_support(labels)


def test_exact_and_normalized_duplicate_detection():
    development = [
        {"case_id": "d1", "output_text": "Answer: 5", "template_family_id": "a"},
        {"case_id": "d2", "output_text": "unique", "template_family_id": "b"},
    ]
    locked = [
        {"case_id": "l1", "output_text": "Answer: 5", "template_family_id": "c"},
        {"case_id": "l2", "output_text": "  ANSWER:\t5 ", "template_family_id": "d"},
    ]
    report = v.detect_fixture_overlaps(development, locked)
    assert report["exact_duplicates"]
    assert report["normalized_duplicates"]
    with pytest.raises(v.ValidationSetError, match="redacted"):
        v.require_no_hard_overlaps(report)


def test_historical_overlap_is_hashed_without_disclosing_text():
    secret_text = "historical confidential output 42"
    fingerprints = v.historical_output_fingerprints(
        [{"output": secret_text}], [{"output": "other history"}]
    )
    report = v.detect_fixture_overlaps(
        [{"case_id": "d", "output_text": secret_text}],
        [{"case_id": "l", "output_text": "new"}],
        historical_fingerprints=fingerprints,
    )
    rendered = v.canonical_json_text(report)
    assert report["historical_exact_overlaps"]
    assert report["historical_normalized_overlaps"]
    assert secret_text not in rendered


def test_development_locked_template_family_overlap_is_hard_failure():
    report = v.detect_fixture_overlaps(
        [{"case_id": "d", "output_text": "one", "template_family_id": "shared"}],
        [{"case_id": "l", "output_text": "two", "template_family_id": "shared"}],
    )
    assert report["cross_set_template_family_overlaps"]


def test_numeric_masked_char_five_gram_near_duplicate_and_disposition():
    development = [
        {"case_id": "a", "output_text": "Alpha operation gives 123 and closes."}
    ]
    locked = [
        {"case_id": "b", "output_text": "Alpha operation gives 456 and closes."}
    ]
    findings = v.near_duplicate_report(development, locked)
    assert findings[0]["similarity_numerator"] == 1
    assert findings[0]["similarity_denominator"] == 1
    with pytest.raises(v.ValidationSetError):
        v.validate_near_duplicate_dispositions(findings, [])
    v.validate_near_duplicate_dispositions(
        findings,
        [
            {
                "left_candidate_id": "a",
                "right_candidate_id": "b",
                "decision": "keep",
                "reason": "different registered semantics",
            }
        ],
    )


def _synthetic_historical_bytes(secret_text: str = "synthetic history") -> dict[str, bytes]:
    generations = []
    evaluations = []
    for index in range(45):
        text = f"{secret_text} generation {index}"
        generations.append(
            {
                "output": text,
                "raw_output": text,
                "eval_output": text,
                "stopped_output": text,
                "postprocessed_output": text,
                "raw_output_before_stop_cleanup": text,
                "raw_output_before_postprocess": text,
            }
        )
        evaluated = f"{secret_text} evaluation {index}"
        evaluations.append(
            {
                "output": evaluated,
                "raw_output": evaluated,
                "stopped_output": evaluated,
                "postprocessed_output": evaluated,
                "raw_output_before_stop_cleanup": evaluated,
                "raw_output_before_postprocess": evaluated,
                "eval_output_used": "raw",
            }
        )
    return {
        "phase1_generations.jsonl": v.canonical_jsonl_bytes(generations),
        "phase1_eval_records.jsonl": v.canonical_jsonl_bytes(evaluations),
    }


def _register_synthetic_historical_hashes(
    monkeypatch: pytest.MonkeyPatch, source_bytes: dict[str, bytes]
) -> None:
    monkeypatch.setattr(
        v,
        "HISTORICAL_SOURCE_HASHES",
        {name: v.sha256_bytes(data) for name, data in source_bytes.items()},
    )


def test_builder_emits_open_and_private_drafts_without_historical_text(
    dataset, monkeypatch
):
    secret_text = "historical do not disclose 314159"
    history = _synthetic_historical_bytes(secret_text)
    _register_synthetic_historical_hashes(monkeypatch, history)
    files = builder.build_validation_drafts(
        dataset["pools"]["curator_a"],
        dataset["pools"]["curator_b"],
        dataset["seals"]["curator_a"],
        dataset["seals"]["curator_b"],
        dataset["plan"],
        dataset["salts"],
        history,
    )
    assert set(files) == {
        "development_cases.jsonl",
        "build_receipt.json",
        "private/locked_inputs.jsonl",
        "private/locked_case_mapping.json",
        "private/curator_label_drafts.jsonl",
        "private/overlap_report.json",
    }
    assert secret_text.encode() not in b"".join(files.values())
    receipt = v.parse_json_strict(
        files["build_receipt.json"], "build_receipt.json"
    )
    assert receipt["selection_plan_sha256"] == v.sha256_bytes(
        v.canonical_json_bytes(dataset["plan"])
    )
    mapping = v.parse_json_strict(
        files["private/locked_case_mapping.json"], "locked_case_mapping.json"
    )
    assert mapping["selection_plan_sha256"] == receipt["selection_plan_sha256"]
    locked = v.parse_jsonl_strict(
        files["private/locked_inputs.jsonl"], "locked_inputs.jsonl"
    )
    assert all("registered_reference_answer" not in row for row in locked)


def test_builder_production_path_rejects_internal_selection_schema(
    dataset, monkeypatch
):
    history = _synthetic_historical_bytes("synthetic historical ingress")
    _register_synthetic_historical_hashes(monkeypatch, history)
    internal = {
        "schema_version": v.SELECTION_PLAN_SCHEMA_VERSION,
        "custodian_id": "evaluator-case-curator-c",
        "curator_a_pool_seal_sha256": "1" * 64,
        "curator_a_candidate_jsonl_sha256": "2" * 64,
        "curator_b_pool_seal_sha256": "3" * 64,
        "curator_b_candidate_jsonl_sha256": "4" * 64,
        "entries": [],
        "near_duplicate_dispositions": [],
    }
    with pytest.raises(v.ValidationSetError, match="fields differ"):
        builder.build_validation_drafts(
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
            internal,
            dataset["salts"],
            history,
        )


def test_builder_rejects_non_authoritative_or_incomplete_history(
    dataset, monkeypatch
):
    with pytest.raises(v.ValidationSetError, match="hard-coded SHA-256"):
        builder.build_validation_drafts(
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
            dataset["plan"],
            dataset["salts"],
            {
                "phase1_generations.jsonl": b"{}\n",
                "phase1_eval_records.jsonl": b"{}\n",
            },
        )
    malformed = {
        "phase1_generations.jsonl": b"{}\n",
        "phase1_eval_records.jsonl": b"{}\n",
    }
    _register_synthetic_historical_hashes(monkeypatch, malformed)
    with pytest.raises(v.ValidationSetError, match="exactly 45/45"):
        builder.build_validation_drafts(
            dataset["pools"]["curator_a"],
            dataset["pools"]["curator_b"],
            dataset["seals"]["curator_a"],
            dataset["seals"]["curator_b"],
            dataset["plan"],
            dataset["salts"],
            malformed,
        )
    with pytest.raises(v.ValidationSetError, match="exact named"):
        v.validate_authoritative_historical_corpus(
            {"wrong.jsonl": b"{}\n", "phase1_eval_records.jsonl": b"{}\n"}
        )


def test_builder_rejects_repository_staging_root_before_creation():
    target = builder.PROJECT_ROOT / "ignored-private-staging-test"
    assert not target.exists()
    files = {
        "development_cases.jsonl": b"",
        "build_receipt.json": b"{}\n",
        "private/locked_inputs.jsonl": b"",
        "private/locked_case_mapping.json": b"{}\n",
        "private/curator_label_drafts.jsonl": b"",
        "private/overlap_report.json": b"{}\n",
    }
    with pytest.raises(v.ValidationSetError, match="outside the repository"):
        builder.write_new_output_root(target, files)
    assert not target.exists()


def test_builder_cli_redacts_private_validation_errors(monkeypatch, capsys):
    secret = "SECRET-SENTINEL-BUILDER-ERROR"

    def fail_without_echo(_value):
        raise builder.ValidationSetError(secret)

    monkeypatch.setattr(
        builder, "validate_external_staging_root", fail_without_echo
    )
    result = builder.main(
        [
            "--curator-a-pool",
            "a-pool",
            "--curator-a-seal",
            "a-seal",
            "--curator-b-pool",
            "b-pool",
            "--curator-b-seal",
            "b-seal",
            "--selection-plan",
            "selection",
            "--curator-c-summary",
            "summary",
            "--private-salts",
            "salts",
            "--historical-generations",
            "generations",
            "--historical-evaluations",
            "evaluations",
            "--output-root",
            "output",
        ]
    )
    captured = capsys.readouterr()
    assert result == 2
    assert secret not in captured.err
    assert captured.err == (
        "validation-set build failed; no artifact data emitted\n"
    )


def test_strict_json_rejects_escaped_lone_surrogate():
    with pytest.raises(v.ValidationSetError, match="non-Unicode-scalar"):
        v.parse_json_strict(
            b'{"development_id_salt":"\\ud800-private-salt",'
            b'"locked_id_salt":"locked-private-salt-0002",'
            b'"schema_version":"phase1-parser-v2-private-salts/v1"}\n',
            "private salts",
        )


def test_builder_cli_redacts_unexpected_exceptions(monkeypatch, capsys):
    secret = "UNEXPECTED-PRIVATE-ERROR"

    def fail_unexpectedly(_value):
        raise RuntimeError(secret)

    monkeypatch.setattr(
        builder, "validate_external_staging_root", fail_unexpectedly
    )
    result = builder.main(
        [
            "--curator-a-pool",
            "a-pool",
            "--curator-a-seal",
            "a-seal",
            "--curator-b-pool",
            "b-pool",
            "--curator-b-seal",
            "b-seal",
            "--selection-plan",
            "selection",
            "--curator-c-summary",
            "summary",
            "--private-salts",
            "salts",
            "--historical-generations",
            "generations",
            "--historical-evaluations",
            "evaluations",
            "--output-root",
            "output",
        ]
    )
    captured = capsys.readouterr()
    assert result == 2
    assert secret not in captured.err
    assert captured.err == (
        "validation-set build failed; no artifact data emitted\n"
    )


def _stage1_rows(dataset, reviewer_id: str) -> list[dict]:
    locked = dataset["materialized"]["locked_inputs"]
    labels = {
        row["case_id"]: row
        for row in dataset["materialized"]["locked_draft_labels"]
    }
    packet_hash = v.sha256_bytes(v.canonical_jsonl_bytes(locked))
    presence_map = {
        "present": "present",
        "ambiguous": "uncertain",
        "no_answer": "absent",
    }
    rows = []
    for outer in locked:
        label = labels[outer["case_id"]]
        rows.append(
            {
                "schema_version": v.STAGE1_REVIEW_SCHEMA_VERSION,
                "review_stage": "stage1",
                "case_id": outer["case_id"],
                "reviewer_id": reviewer_id,
                "reviewer_model_id": v.REVIEWER_MODEL_ID,
                "reviewer_reasoning_effort": v.REVIEWER_REASONING_EFFORT,
                "packet_sha256": packet_hash,
                "answer_presence": presence_map[
                    label["expected_answer_presence"]
                ],
                **{
                    field: deepcopy(label[f"expected_{field}"])
                    for field in (
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
                },
                "notes": "",
            }
        )
    return rows


def _stage1_consensus_bundle(dataset):
    reviewer_a = _stage1_rows(dataset, "reviewer_a")
    reviewer_b = _stage1_rows(dataset, "reviewer_b")
    result = v.validate_stage1_arbitration(
        [],
        reviewer_a,
        reviewer_b,
        dataset["materialized"]["locked_inputs"],
    )
    return reviewer_a, reviewer_b, result


def test_stage1_reviewers_are_complete_120_of_120(dataset):
    rows = _stage1_rows(dataset, "reviewer_a")
    report = v.validate_stage1_submission(
        rows, dataset["materialized"]["locked_inputs"]
    )
    assert report["row_count"] == 120
    assert report["unresolved_ids"] == []
    with pytest.raises(v.ValidationSetError, match="120"):
        v.validate_stage1_submission(
            rows[:-1], dataset["materialized"]["locked_inputs"]
        )


def test_stage1_requires_two_distinct_reviewer_identities(dataset):
    rows = _stage1_rows(dataset, "reviewer_a")
    with pytest.raises(v.ValidationSetError, match="distinct"):
        v.validate_stage1_arbitration(
            [], rows, deepcopy(rows), dataset["materialized"]["locked_inputs"]
        )


def test_stage1_arbitration_is_reference_blind_and_separate(dataset):
    reviewer_a = _stage1_rows(dataset, "reviewer_a")
    reviewer_b = _stage1_rows(dataset, "reviewer_b")
    target = reviewer_b[0]
    target.update(
        {
            "answer_presence": "inconclusive",
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
    )
    locked = dataset["materialized"]["locked_inputs"]
    a = v.validate_stage1_submission(reviewer_a, locked)
    b = v.validate_stage1_submission(
        reviewer_b, locked, packet_sha256=a["packet_sha256"]
    )
    source = reviewer_a[0]
    arbitration = {
        "schema_version": v.STAGE1_ARBITRATION_SCHEMA_VERSION,
        "review_stage": "stage1_arbitration",
        "case_id": source["case_id"],
        "arbiter_id": "arbiter_c",
        "arbiter_model_id": v.REVIEWER_MODEL_ID,
        "arbiter_reasoning_effort": v.REVIEWER_REASONING_EFFORT,
        "packet_sha256": a["packet_sha256"],
        "reviewer_a_submission_sha256": a["submission_sha256"],
        "reviewer_b_submission_sha256": b["submission_sha256"],
        **{
            field: deepcopy(source[field]) for field in v._EXTRACTION_FIELD_NAMES
        },
        "resolution_notes": "reference-blind extraction resolution",
    }
    leaked = dict(arbitration, registered_reference_answer="999")
    with pytest.raises(v.ValidationSetError, match="extra"):
        v.validate_stage1_arbitration(
            [leaked], reviewer_a, reviewer_b, locked
        )
    report = v.validate_stage1_arbitration(
        [arbitration], reviewer_a, reviewer_b, locked
    )
    assert report["arbitration_count"] == 1
    assert report["unresolved_count"] == 0
    assert len(report["consensus"]) == 120


def test_stage1_consensus_requires_zero_unresolved(dataset):
    reviewer_a = _stage1_rows(dataset, "reviewer_a")
    reviewer_b = _stage1_rows(dataset, "reviewer_b")
    for rows in (reviewer_a, reviewer_b):
        rows[0].update(
            {
                "answer_presence": "inconclusive",
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
        )
    with pytest.raises(v.ValidationSetError):
        v.validate_stage1_arbitration(
            [],
            reviewer_a,
            reviewer_b,
            dataset["materialized"]["locked_inputs"],
        )


def _stage2_reference_packet(dataset) -> list[dict]:
    return v.build_stage2_reference_packet(
        dataset["materialized"]["locked_draft_labels"]
    )


def _stage2_rows(dataset, consensus: list[dict], reviewer_id: str) -> list[dict]:
    locked = dataset["materialized"]["locked_inputs"]
    labels = dataset["materialized"]["locked_draft_labels"]
    labels_by_id = {row["case_id"]: row for row in labels}
    consensus_hash = v.sha256_bytes(v.canonical_jsonl_bytes(consensus))
    reference_packet = _stage2_reference_packet(dataset)
    reference_hash = v.sha256_bytes(
        v.canonical_jsonl_bytes(reference_packet)
    )
    packet_hash = v._stage2_review_packet_sha256(
        consensus_hash, reference_hash
    )
    return [
        {
            "schema_version": v.STAGE2_REVIEW_SCHEMA_VERSION,
            "review_stage": "stage2",
            "case_id": outer["case_id"],
            "reviewer_id": reviewer_id,
            "reviewer_model_id": v.REVIEWER_MODEL_ID,
            "reviewer_reasoning_effort": v.REVIEWER_REASONING_EFFORT,
            "packet_sha256": packet_hash,
            "stage1_consensus_sha256": consensus_hash,
            "stage2_reference_packet_sha256": reference_hash,
            "correctness": (
                "correct"
                if labels_by_id[outer["case_id"]]["expected_correctness"]
                else "incorrect"
            ),
            "critical_case": labels_by_id[outer["case_id"]]["critical_case"],
            "material_error_if_missed": labels_by_id[outer["case_id"]][
                "material_error_if_missed"
            ],
            "notes": "",
        }
        for outer in locked
    ]


def test_stage2_reviewers_are_complete_120_of_120(dataset):
    _, _, stage1 = _stage1_consensus_bundle(dataset)
    rows = _stage2_rows(dataset, stage1["consensus"], "reviewer_a")
    report = v.validate_stage2_submission(
        rows,
        dataset["materialized"]["locked_inputs"],
        stage1["consensus"],
        _stage2_reference_packet(dataset),
    )
    assert report["row_count"] == 120
    assert report["unresolved_ids"] == []


def test_stage2_reference_packet_is_immutable_minimal_and_hash_bound(dataset):
    _, _, stage1 = _stage1_consensus_bundle(dataset)
    packet = _stage2_reference_packet(dataset)
    assert len(packet) == 120
    assert all(
        set(row) == {"case_id", "registered_reference_answer"}
        for row in packet
    )
    rows = _stage2_rows(dataset, stage1["consensus"], "reviewer_a")
    tampered = deepcopy(packet)
    tampered[0]["registered_reference_answer"] = (
        "1"
        if tampered[0]["registered_reference_answer"] != "1"
        else "2"
    )
    with pytest.raises(v.ValidationSetError, match="packet_sha256"):
        v.validate_stage2_submission(
            rows,
            dataset["materialized"]["locked_inputs"],
            stage1["consensus"],
            tampered,
        )


def test_review_submission_seal_binds_all_ordered_rows(dataset):
    rows = _stage1_rows(dataset, "reviewer_a")
    seal = v.build_review_seal(
        rows,
        review_stage="stage1",
        actor_id="reviewer_a",
        packet_sha256=rows[0]["packet_sha256"],
        sealed_utc="2026-07-15T12:00:00Z",
    )
    assert v.validate_review_seal(
        seal, rows, expected_case_ids=[row["case_id"] for row in rows]
    )["row_count"] == 120
    tampered = deepcopy(rows)
    tampered[0]["notes"] = "changed after seal"
    with pytest.raises(v.ValidationSetError, match="hash mismatch"):
        v.validate_review_seal(seal, tampered)


def _complete_review_bundle(dataset) -> dict:
    locked = dataset["materialized"]["locked_inputs"]
    labels = dataset["materialized"]["locked_draft_labels"]
    reference_packet = _stage2_reference_packet(dataset)
    stage1_a, stage1_b, stage1 = _stage1_consensus_bundle(dataset)
    packet_hash = stage1_a[0]["packet_sha256"]
    timestamp = "2026-07-15T12:00:00Z"
    seal_1a = v.build_review_seal(
        stage1_a,
        review_stage="stage1",
        actor_id="reviewer_a",
        packet_sha256=packet_hash,
        sealed_utc=timestamp,
    )
    seal_1b = v.build_review_seal(
        stage1_b,
        review_stage="stage1",
        actor_id="reviewer_b",
        packet_sha256=packet_hash,
        sealed_utc=timestamp,
    )
    seal_1arb = v.build_review_seal(
        [],
        review_stage="stage1_arbitration",
        actor_id="arbiter_c",
        packet_sha256=packet_hash,
        predecessor_seals=(seal_1a, seal_1b),
        sealed_utc=timestamp,
    )
    seal_consensus = v.build_review_seal(
        stage1["consensus"],
        review_stage="stage1_consensus",
        actor_id="arbiter_c",
        packet_sha256=packet_hash,
        predecessor_seals=(seal_1a, seal_1b, seal_1arb),
        sealed_utc=timestamp,
    )
    stage2_a = _stage2_rows(dataset, stage1["consensus"], "reviewer_a")
    stage2_b = _stage2_rows(dataset, stage1["consensus"], "reviewer_b")
    stage2_packet_hash = stage2_a[0]["packet_sha256"]
    consensus_hash = stage2_a[0]["stage1_consensus_sha256"]
    reference_hash = stage2_a[0]["stage2_reference_packet_sha256"]
    seal_2a = v.build_review_seal(
        stage2_a,
        review_stage="stage2",
        actor_id="reviewer_a",
        packet_sha256=stage2_packet_hash,
        stage1_consensus_sha256=consensus_hash,
        stage2_reference_packet_sha256=reference_hash,
        predecessor_seals=(seal_consensus,),
        sealed_utc=timestamp,
    )
    seal_2b = v.build_review_seal(
        stage2_b,
        review_stage="stage2",
        actor_id="reviewer_b",
        packet_sha256=stage2_packet_hash,
        stage1_consensus_sha256=consensus_hash,
        stage2_reference_packet_sha256=reference_hash,
        predecessor_seals=(seal_consensus,),
        sealed_utc=timestamp,
    )
    seal_2arb = v.build_review_seal(
        [],
        review_stage="stage2_arbitration",
        actor_id="arbiter_c",
        packet_sha256=stage2_packet_hash,
        stage1_consensus_sha256=consensus_hash,
        stage2_reference_packet_sha256=reference_hash,
        predecessor_seals=(seal_consensus, seal_2a, seal_2b),
        sealed_utc=timestamp,
    )
    return {
        "locked_inputs": locked,
        "draft_labels": labels,
        "stage2_reference_packet": reference_packet,
        "reviewer_a_stage1": stage1_a,
        "reviewer_a_stage1_seal": seal_1a,
        "reviewer_b_stage1": stage1_b,
        "reviewer_b_stage1_seal": seal_1b,
        "arbitration_stage1": [],
        "arbitration_stage1_seal": seal_1arb,
        "stage1_consensus": stage1["consensus"],
        "stage1_consensus_seal": seal_consensus,
        "reviewer_a_stage2": stage2_a,
        "reviewer_a_stage2_seal": seal_2a,
        "reviewer_b_stage2": stage2_b,
        "reviewer_b_stage2_seal": seal_2b,
        "arbitration_stage2": [],
        "arbitration_stage2_seal": seal_2arb,
    }


def _workflow_arguments(bundle: dict) -> dict:
    return {
        key: value
        for key, value in bundle.items()
        if key != "stage1_consensus"
    }


def test_complete_review_workflow_binds_seven_seals_and_predecessors(dataset):
    bundle = _complete_review_bundle(dataset)
    report = v.validate_complete_review_workflow(**_workflow_arguments(bundle))
    assert report["unresolved_count"] == 0
    assert len(report["final_labels"]) == 120

    tampered = deepcopy(bundle)
    tampered["reviewer_a_stage1_seal"]["row_sha256"][0] = "f" * 64
    with pytest.raises(v.ValidationSetError, match="row hashes mismatch"):
        v.validate_complete_review_workflow(**_workflow_arguments(tampered))

    leaked = deepcopy(bundle["reviewer_a_stage1_seal"])
    leaked["stage1_consensus_sha256"] = "1" * 64
    with pytest.raises(v.ValidationSetError, match="prohibited"):
        v.validate_review_seal(leaked, bundle["reviewer_a_stage1"])

    wrong_predecessor = deepcopy(bundle["stage1_consensus_seal"])
    wrong_predecessor["predecessor_seal_sha256"][0] = "2" * 64
    with pytest.raises(v.ValidationSetError, match="predecessor chain mismatch"):
        v.validate_review_seal(
            wrong_predecessor,
            bundle["stage1_consensus"],
            predecessor_seals=(
                bundle["reviewer_a_stage1_seal"],
                bundle["reviewer_b_stage1_seal"],
                bundle["arbitration_stage1_seal"],
            ),
        )

    mixed_stage2 = deepcopy(bundle["reviewer_a_stage2"])
    mixed_stage2[0]["stage1_consensus_sha256"] = "e" * 64
    with pytest.raises(v.ValidationSetError, match="one Stage-1 consensus hash"):
        v.build_review_seal(
            mixed_stage2,
            review_stage="stage2",
            actor_id="reviewer_a",
            packet_sha256=mixed_stage2[0]["packet_sha256"],
            stage1_consensus_sha256=mixed_stage2[1][
                "stage1_consensus_sha256"
            ],
            stage2_reference_packet_sha256=mixed_stage2[0][
                "stage2_reference_packet_sha256"
            ],
            predecessor_seals=(bundle["stage1_consensus_seal"],),
            sealed_utc="2026-07-15T12:00:00Z",
        )


def test_stage2_reviewer_identity_must_continue_from_stage1(dataset):
    reviewer_a, _, stage1 = _stage1_consensus_bundle(dataset)
    stage2 = _stage2_rows(dataset, stage1["consensus"], "different_reviewer")
    with pytest.raises(v.ValidationSetError, match="corresponding Stage-1"):
        v.validate_two_stage_reviewer_continuity(
            reviewer_a,
            stage2,
            dataset["materialized"]["locked_inputs"],
            stage1["consensus"],
            _stage2_reference_packet(dataset),
        )


def test_stage2_rows_cannot_revise_extraction_fields(dataset):
    _, _, stage1 = _stage1_consensus_bundle(dataset)
    row = _stage2_rows(dataset, stage1["consensus"], "reviewer_a")[0]
    row["parsed_answer"] = "1"
    with pytest.raises(v.ValidationSetError, match="extra"):
        v.validate_stage2_submission(
            [row] * 120,
            dataset["materialized"]["locked_inputs"],
            stage1["consensus"],
            _stage2_reference_packet(dataset),
        )


def test_separate_stage2_arbitration_and_final_labels(dataset):
    _, _, stage1 = _stage1_consensus_bundle(dataset)
    consensus = stage1["consensus"]
    reviewer_a = _stage2_rows(dataset, consensus, "reviewer_a")
    reviewer_b = _stage2_rows(dataset, consensus, "reviewer_b")
    reviewer_b[0]["correctness"] = (
        "incorrect" if reviewer_a[0]["correctness"] == "correct" else "correct"
    )
    locked = dataset["materialized"]["locked_inputs"]
    labels = dataset["materialized"]["locked_draft_labels"]
    reference_packet = _stage2_reference_packet(dataset)
    a = v.validate_stage2_submission(
        reviewer_a, locked, consensus, reference_packet
    )
    b = v.validate_stage2_submission(
        reviewer_b,
        locked,
        consensus,
        reference_packet,
        packet_sha256=a["packet_sha256"],
    )
    arbitration = {
        "schema_version": v.STAGE2_ARBITRATION_SCHEMA_VERSION,
        "review_stage": "stage2_arbitration",
        "case_id": reviewer_a[0]["case_id"],
        "arbiter_id": "arbiter_c",
        "arbiter_model_id": v.REVIEWER_MODEL_ID,
        "arbiter_reasoning_effort": v.REVIEWER_REASONING_EFFORT,
        "packet_sha256": a["packet_sha256"],
        "stage1_consensus_sha256": a["stage1_consensus_sha256"],
        "stage2_reference_packet_sha256": a[
            "stage2_reference_packet_sha256"
        ],
        "reviewer_a_submission_sha256": a["submission_sha256"],
        "reviewer_b_submission_sha256": b["submission_sha256"],
        "correctness": reviewer_a[0]["correctness"],
        "critical_case": reviewer_a[0]["critical_case"],
        "material_error_if_missed": reviewer_a[0][
            "material_error_if_missed"
        ],
        "resolution_notes": "correctness-only resolution",
    }
    report = v.validate_stage2_arbitration(
        [arbitration],
        reviewer_a,
        reviewer_b,
        locked,
        consensus,
        reference_packet,
    )
    assert report["arbitration_count"] == 1
    assert report["unresolved_count"] == 0
    final = v.build_final_labels(
        labels, consensus, reference_packet, report["final_stage2"]
    )
    assert len(final) == 120
    tampered_packet = deepcopy(reference_packet)
    tampered_packet[0]["registered_reference_answer"] = (
        "1"
        if tampered_packet[0]["registered_reference_answer"] != "1"
        else "2"
    )
    with pytest.raises(v.ValidationSetError, match="immutable Stage-2 packet"):
        v.build_final_labels(
            labels, consensus, tampered_packet, report["final_stage2"]
        )


def test_final_label_private_spans_are_derived_only_from_stage1_consensus(
    dataset,
):
    _, _, stage1 = _stage1_consensus_bundle(dataset)
    consensus = deepcopy(stage1["consensus"])
    labels = deepcopy(dataset["materialized"]["locked_draft_labels"])
    target = next(label for label in labels if label["stratum"] == "S01")
    target_consensus = next(
        row for row in consensus if row["case_id"] == target["case_id"]
    )
    selected_span = next(
        span
        for span in target["expected_evidence_spans"]
        if span["disposition"] == "selected"
    )
    suffix = f" Equivalent answer: {selected_span['text']}"
    equivalent_start = len(target["output_text"]) + suffix.rindex(
        selected_span["text"]
    )
    target["output_text"] += suffix
    equivalent = {
        "start": equivalent_start,
        "end": equivalent_start + len(selected_span["text"]),
        "text": selected_span["text"],
        "kind": selected_span["kind"],
        "normalized_answer": selected_span["normalized_answer"],
        "disposition": "equivalent",
    }
    target["expected_evidence_spans"].append(equivalent)
    target["acceptable_selected_spans"].append(
        {
            "start": equivalent["start"],
            "end": equivalent["end"],
            "text": equivalent["text"],
        }
    )
    target_consensus["evidence_spans"].append(deepcopy(equivalent))

    final_stage2 = [
        {
            "case_id": label["case_id"],
            "source": "reviewer_agreement",
            "correctness": (
                "correct" if label["expected_correctness"] else "incorrect"
            ),
            "critical_case": label["critical_case"],
            "material_error_if_missed": label[
                "material_error_if_missed"
            ],
        }
        for label in labels
    ]
    reference_packet = _stage2_reference_packet(dataset)
    derived = v.build_final_labels(
        labels, consensus, reference_packet, final_stage2
    )
    derived_by_id = {row["case_id"]: row for row in derived}
    expected_acceptable = derived_by_id[target["case_id"]][
        "acceptable_selected_spans"
    ]
    assert len(expected_acceptable) == 2

    removed = deepcopy(labels)
    removed_target = next(
        row for row in removed if row["case_id"] == target["case_id"]
    )
    removed_target["acceptable_selected_spans"] = [
        removed_target["acceptable_selected_spans"][0]
    ]
    assert (
        v.build_final_labels(
            removed, consensus, reference_packet, final_stage2
        )
        == derived
    )

    added = deepcopy(labels)
    added_target = next(
        row for row in added if row["case_id"] == target["case_id"]
    )
    added_target["acceptable_selected_spans"].append(
        deepcopy(added_target["acceptable_selected_spans"][-1])
    )
    assert (
        v.build_final_labels(
            added, consensus, reference_packet, final_stage2
        )
        == derived
    )

    changed_distractor = deepcopy(labels)
    s06 = next(
        row for row in changed_distractor if row["stratum"] == "S06"
    )
    s06_selected = next(
        span
        for span in s06["expected_evidence_spans"]
        if span["disposition"] == "selected"
    )
    s06["last_number_distractor_span"] = {
        "start": s06_selected["start"],
        "end": s06_selected["end"],
        "text": s06_selected["text"],
    }
    assert (
        v.build_final_labels(
            changed_distractor,
            consensus,
            reference_packet,
            final_stage2,
        )
        == derived
    )


def test_final_label_quota_tags_are_rederived_from_stage1_consensus(dataset):
    _, _, stage1 = _stage1_consensus_bundle(dataset)
    consensus = deepcopy(stage1["consensus"])
    labels = deepcopy(dataset["materialized"]["locked_draft_labels"])
    target = next(
        label
        for label in labels
        if label["stratum"] == "S01"
        and "incidental_numeric_distractor" not in label["secondary_tags"]
    )
    selected = next(
        span
        for span in target["expected_evidence_spans"]
        if span["disposition"] == "selected"
    )
    suffix = f" Equivalent answer: {selected['text']}"
    target["output_text"] += suffix
    equivalent_start = len(target["output_text"]) - len(selected["text"])
    equivalent = {
        "start": equivalent_start,
        "end": len(target["output_text"]),
        "text": selected["text"],
        "kind": selected["kind"],
        "normalized_answer": selected["normalized_answer"],
        "disposition": "equivalent",
    }
    target["expected_evidence_spans"].append(equivalent)
    target["acceptable_selected_spans"].append(
        {
            "start": equivalent["start"],
            "end": equivalent["end"],
            "text": equivalent["text"],
        }
    )
    final_stage2 = [
        {
            "case_id": label["case_id"],
            "source": "reviewer_agreement",
            "correctness": (
                "correct" if label["expected_correctness"] else "incorrect"
            ),
            "critical_case": label["critical_case"],
            "material_error_if_missed": label["material_error_if_missed"],
        }
        for label in labels
    ]

    final = v.build_final_labels(
        labels,
        consensus,
        v.build_stage2_reference_packet(labels),
        final_stage2,
    )
    derived = next(row for row in final if row["case_id"] == target["case_id"])
    assert "incidental_numeric_distractor" in derived["secondary_tags"]


def test_stage2_agreed_inconclusive_is_unresolved(dataset):
    _, _, stage1 = _stage1_consensus_bundle(dataset)
    reviewer_a = _stage2_rows(dataset, stage1["consensus"], "reviewer_a")
    reviewer_b = _stage2_rows(dataset, stage1["consensus"], "reviewer_b")
    for rows in (reviewer_a, reviewer_b):
        rows[0].update(
            {
                "correctness": "inconclusive",
                "critical_case": None,
                "material_error_if_missed": None,
            }
        )
    with pytest.raises(v.ValidationSetError, match="inconclusive"):
        v.validate_stage2_arbitration(
            [],
            reviewer_a,
            reviewer_b,
            dataset["materialized"]["locked_inputs"],
            stage1["consensus"],
            _stage2_reference_packet(dataset),
        )


def test_reviewer_agreement_uses_na_for_constant_marginals(dataset):
    row_a = _stage1_rows(dataset, "reviewer_a")[0]
    row_b = deepcopy(row_a)
    row_b["reviewer_id"] = "reviewer_b"
    report = v.compute_reviewer_agreement([row_a], [row_b])
    for field in (
        "answer_presence",
        "parse_valid",
        "parse_ambiguous",
        "extraction_strategy",
        "output_quality",
    ):
        assert report["fields"][field]["nominal_kappa"]["display"] == "NA"


def test_confusion_macro_f1_and_exact_gate_decisions(dataset):
    labels = dataset["materialized"]["locked_draft_labels"]
    predictions, seal, implementation = _sealed_predictions(dataset, labels)
    report = v.score_validation_set(
        labels,
        predictions,
        _legacy_predictions(labels),
        locked_inputs=dataset["materialized"]["locked_inputs"],
        prediction_seal=seal,
        implementation_commit=implementation,
        raise_on_invalid=True,
    )
    assert report["status"] == "PASS"
    assert report["confusion_matrix"]["present"]["present"] == 80
    assert report["confusion_matrix"]["ambiguous"]["ambiguous"] == 10
    assert report["confusion_matrix"]["no_answer"]["no_answer"] == 30
    assert report["answer_presence_macro_f1"]["canonical"] == "1"
    assert report["overall_exact_typed_decision"]["rate"]["canonical"] == "1"
    assert report["gates"]["overall_exact_typed_decision"] == "PASS"


def test_per_stratum_critical_material_and_legacy_comparison(dataset):
    labels = dataset["materialized"]["locked_draft_labels"]
    predictions, _, implementation = _sealed_predictions(dataset, labels)
    target_index = next(
        index
        for index, label in enumerate(labels)
        if label["stratum"] in v.CRITICAL_STRATA
        and label["expected_correctness"]
    )
    target = labels[target_index]
    predictions[target_index]["parser_result"] = _parser_result(
        target, decision="no_answer"
    )
    seal = v.build_prediction_seal(
        predictions,
        dataset["materialized"]["locked_inputs"],
        implementation_commit=implementation,
        sealed_utc="2026-07-15T12:00:00Z",
    )
    report = v.score_validation_set(
        labels,
        predictions,
        _legacy_predictions(labels),
        locked_inputs=dataset["materialized"]["locked_inputs"],
        prediction_seal=seal,
        implementation_commit=implementation,
        raise_on_invalid=True,
    )
    assert report["critical"]["denominator"] == 80
    assert report["per_stratum"][target["stratum"]]["parser_v2_correct"] == 9
    assert report["material_correctness"]["errors"] == 1
    assert (
        report["material_correctness"]["by_stratum"][target["stratum"]] == 1
    )
    assert report["legacy_comparison"]["clean_parser_v2_correct"] == 40


def test_zero_denominator_metric_is_na_and_invalid_fail_closed(dataset):
    labels = dataset["materialized"]["locked_draft_labels"]
    predictions, _, implementation = _sealed_predictions(dataset, labels)
    for prediction, label in zip(predictions, labels):
        prediction["parser_result"] = _parser_result(label, decision="no_answer")
    seal = v.build_prediction_seal(
        predictions,
        dataset["materialized"]["locked_inputs"],
        implementation_commit=implementation,
        sealed_utc="2026-07-15T12:00:00Z",
    )
    report = v.score_validation_set(
        labels,
        predictions,
        _legacy_predictions(labels),
        locked_inputs=dataset["materialized"]["locked_inputs"],
        prediction_seal=seal,
        implementation_commit=implementation,
        raise_on_invalid=True,
    )
    assert report["class_metrics"]["ambiguous"]["precision"]["display"] == "NA"
    assert report["gates"]["ambiguity_precision"] == "INVALID"
    assert report["status"] == "INVALID"


def test_missing_prediction_returns_invalid_without_dropping_case(dataset):
    labels = dataset["materialized"]["locked_draft_labels"]
    predictions, seal, implementation = _sealed_predictions(dataset, labels)
    report = v.score_validation_set(
        labels,
        predictions[:-1],
        _legacy_predictions(labels),
        locked_inputs=dataset["materialized"]["locked_inputs"],
        prediction_seal=seal,
        implementation_commit=implementation,
    )
    assert report["status"] == "INVALID"
    assert report["gates"] == {"integrity_and_scorer": "INVALID"}


def test_scorer_rejects_unsealed_direct_or_mixed_predictions(dataset):
    labels = dataset["materialized"]["locked_draft_labels"]
    predictions, seal, implementation = _sealed_predictions(dataset, labels)
    direct = [
        {"case_id": row["case_id"], "parser_result": row["parser_result"]}
        for row in predictions
    ]
    assert v.score_validation_set(
        labels,
        direct,
        _legacy_predictions(labels),
        locked_inputs=dataset["materialized"]["locked_inputs"],
        prediction_seal=seal,
        implementation_commit=implementation,
    )["status"] == "INVALID"
    mixed = deepcopy(predictions)
    mixed[0]["parser_result"]["parser_version"] = "b" * 64
    assert v.score_validation_set(
        labels,
        mixed,
        _legacy_predictions(labels),
        locked_inputs=dataset["materialized"]["locked_inputs"],
        prediction_seal=seal,
        implementation_commit=implementation,
    )["status"] == "INVALID"


@pytest.mark.parametrize(
    ("source", "output"),
    [
        ("source/run", "source/run"),
        ("source/run", "source/run/child"),
        ("source/run/child", "source/run"),
        ("source/run", r"other\bad"),
        ("source/run", "other//bad"),
        ("/source/run", "other/run"),
        (
            "independent/source",
            "phase1-limited-n3-gates/20260710T152820Z",
        ),
    ],
)
def test_source_output_prefix_isolation_and_prohibited_prefixes(source, output):
    with pytest.raises(v.ValidationSetError):
        v.validate_prefix_isolation([source], [output])


def test_exact_upload_plan_is_reservation_first_and_manifest_last():
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T000000Z"
    plan = v.build_upload_plan(parent)
    assert len(plan) == sum(
        len(names) for names in v.REGISTERED_LEAF_MEMBERS.values()
    )
    cursor = 0
    for leaf, names in v.REGISTERED_LEAF_MEMBERS.items():
        leaf_plan = plan[cursor : cursor + len(names)]
        assert Path(leaf_plan[0]).name.startswith(".")
        assert "manifest" in Path(leaf_plan[-1]).name
        assert all(f"/{leaf}/" in name for name in leaf_plan)
        cursor += len(names)
    assert plan[-1].endswith("/manifests/locked_manifest.json")
    packet_index = plan.index(
        f"{parent}/locked-labels/stage2_reference_packet.jsonl"
    )
    assert packet_index < plan.index(
        f"{parent}/locked-labels/reviewer_a_stage2.jsonl"
    )


@pytest.mark.parametrize(
    "parent",
    (
        "phase1-evaluator-validation/parser-v2-v1/run",
        "phase1-evaluator-validation/parser-v2-v2/20260715T000000Z",
        "phase1-evaluator-validation/parser-v2-v1/20261315T000000Z",
        "phase1-evaluator-validation/parser-v2-v1/20260230T000000Z",
        "other/parser-v2-v1/20260715T000000Z",
    ),
)
def test_parent_namespace_and_utc_calendar_timestamp_are_exact(parent):
    with pytest.raises(v.ValidationSetError):
        v.validate_registered_parent_prefix(parent)


def test_visibility_ledger_rejects_stage1_reference_access():
    timestamp = "2026-07-15T19:00:00Z"
    row = {
        "schema_version": v.VISIBILITY_LEDGER_SCHEMA_VERSION,
        "actor_id": "reviewer_a",
        "role": "stage1_reviewer",
        "artifact_classes": sorted(
            {
                *v.VISIBILITY_ROLE_ARTIFACT_CLASSES["stage1_reviewer"],
                "stage2-reference-packet",
            }
        ),
        "purpose": "test reference blinding",
        "authorization": "test-authorization",
        "execution_id": "test-execution",
        "model_id": v.REVIEWER_MODEL_ID,
        "reasoning_effort": v.REVIEWER_REASONING_EFFORT,
        "first_access_utc": timestamp,
        "last_access_utc": timestamp,
    }
    with pytest.raises(v.ValidationSetError, match="registered role visibility"):
        v.validate_visibility_ledger([row])


def _invalid_registered_file_bytes() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for leaf, names in v.REGISTERED_LEAF_MEMBERS.items():
        for name in names:
            relative = f"{leaf}/{name}"
            if name.endswith(".jsonl"):
                files[relative] = b""
            elif name.endswith(".md"):
                files[relative] = b"# validation report\n"
            else:
                files[relative] = v.canonical_json_bytes({})
    return files


def _valid_registered_file_bytes(dataset, parent: str) -> dict[str, bytes]:
    review = _complete_review_bundle(dataset)
    workflow = v.validate_complete_review_workflow(**_workflow_arguments(review))
    final_labels = workflow["final_labels"]
    development = dataset["materialized"]["development"]
    locked_inputs = dataset["materialized"]["locked_inputs"]
    mapping = dataset["mapping"]
    files: dict[str, bytes] = {}
    timestamp = "2026-07-15T12:00:00Z"
    source_prefixes = ["independent/source"]

    for index, (leaf, names) in enumerate(v.REGISTERED_LEAF_MEMBERS.items()):
        reservation = {
            "schema_version": v.RESERVATION_SCHEMA_VERSION,
            "leaf": leaf,
            "parent_prefix": parent,
            "created_utc": timestamp,
            "private_nonce": f"private-nonce-{index:04d}",
        }
        files[f"{leaf}/{names[0]}"] = v.canonical_json_bytes(reservation)

    files["development/development_cases.jsonl"] = v.canonical_jsonl_bytes(
        development
    )
    files["locked-inputs/locked_inputs.jsonl"] = v.canonical_jsonl_bytes(
        locked_inputs
    )
    files["locked-labels/reviewer_a_stage1.jsonl"] = v.canonical_jsonl_bytes(
        review["reviewer_a_stage1"]
    )
    files["locked-labels/reviewer_b_stage1.jsonl"] = v.canonical_jsonl_bytes(
        review["reviewer_b_stage1"]
    )
    files["locked-labels/arbitration_stage1.jsonl"] = b""
    files["locked-labels/stage1_consensus.jsonl"] = v.canonical_jsonl_bytes(
        review["stage1_consensus"]
    )
    files["locked-labels/stage2_reference_packet.jsonl"] = (
        v.canonical_jsonl_bytes(review["stage2_reference_packet"])
    )
    files["locked-labels/reviewer_a_stage2.jsonl"] = v.canonical_jsonl_bytes(
        review["reviewer_a_stage2"]
    )
    files["locked-labels/reviewer_b_stage2.jsonl"] = v.canonical_jsonl_bytes(
        review["reviewer_b_stage2"]
    )
    files["locked-labels/arbitration_stage2.jsonl"] = b""
    files["locked-labels/locked_reference_labels.jsonl"] = v.canonical_jsonl_bytes(
        final_labels
    )
    report = {
        "schema_version": v.VALIDATION_REPORT_SCHEMA_VERSION,
        "status": "SEALED",
        "development_count": 60,
        "locked_count": 120,
        "agreement": v.compute_reviewer_agreement(
            review["reviewer_a_stage1"],
            review["reviewer_b_stage1"],
            stage2_a=review["reviewer_a_stage2"],
            stage2_b=review["reviewer_b_stage2"],
            arbitration_ids=[],
        ),
        "arbitration": {
            "stage1": {"count": 0, "case_ids": []},
            "stage2": {"count": 0, "case_ids": []},
        },
        "unresolved_count": 0,
        "model_inference_performed": False,
    }
    files["reports/validation_set_report.json"] = v.canonical_json_bytes(report)
    files["reports/validation_set_report.md"] = (
        v.render_validation_report_markdown(report)
    )
    files["manifests/locked_case_mapping.json"] = v.canonical_json_bytes(mapping)
    actors_and_roles = [
        (v.SEALED_CURATOR_IDENTITIES[0], "curator"),
        (v.SEALED_CURATOR_IDENTITIES[1], "curator"),
        (v.REGISTERED_CURATOR_C_ID, "curator_c"),
        (v.REGISTERED_CUSTODIAN_ID, "custodian"),
        ("reviewer_a", "stage1_reviewer"),
        ("reviewer_b", "stage1_reviewer"),
        ("arbiter_c", "stage1_arbiter"),
        ("reviewer_a", "stage2_reviewer"),
        ("reviewer_b", "stage2_reviewer"),
        ("arbiter_c", "stage2_arbiter"),
    ]
    visibility = []
    for actor_id, role in actors_and_roles:
        visibility.append(
            {
            "schema_version": v.VISIBILITY_LEDGER_SCHEMA_VERSION,
            "actor_id": actor_id,
            "role": role,
            "artifact_classes": list(
                v.VISIBILITY_ROLE_ARTIFACT_CLASSES[role]
            ),
            "purpose": "synthetic validation release test",
            "authorization": "test-authorization",
            "execution_id": "test-execution",
            "model_id": None if role == "custodian" else v.REVIEWER_MODEL_ID,
            "reasoning_effort": (
                None if role == "custodian" else v.REVIEWER_REASONING_EFFORT
            ),
            "first_access_utc": timestamp,
            "last_access_utc": timestamp,
            }
        )
    files["manifests/visibility_ledger.jsonl"] = v.canonical_jsonl_bytes(visibility)
    mapping_by_case = {
        entry["case_id"]: entry for entry in mapping["entries"]
    }

    def overlap_projection(row):
        projected = dict(row)
        case_id = projected.pop("case_id")
        entry = mapping_by_case[case_id]
        projected["candidate_id"] = entry["candidate_id"]
        projected["template_family_id"] = entry["template_family_id"]
        return projected

    projected_development = [
        overlap_projection(row) for row in development
    ]
    projected_locked = [overlap_projection(row) for row in final_labels]
    overlap = v.detect_fixture_overlaps(
        projected_development, projected_locked
    )
    near = v.near_duplicate_report(
        projected_development, projected_locked
    )
    overlap["near_duplicates"] = near
    overlap["near_duplicate_dispositions"] = [
        {
            "left_candidate_id": finding["left_id"],
            "right_candidate_id": finding["right_id"],
            "decision": "keep",
            "reason": "synthetic fixtures remain intentionally distinct",
        }
        for finding in near
    ]
    overlap["near_duplicate_dispositions_complete"] = True
    files["manifests/overlap_report.json"] = v.canonical_json_bytes(overlap)

    composition = v.validate_dataset_composition(development, final_labels)
    development_ids = [row["case_id"] for row in development]
    locked_ids = [row["case_id"] for row in locked_inputs]
    all_ids = sorted([*development_ids, *locked_ids])
    visibility_hash = v.sha256_bytes(files["manifests/visibility_ledger.jsonl"])
    seals = [
        review["reviewer_a_stage1_seal"],
        review["reviewer_b_stage1_seal"],
        review["arbitration_stage1_seal"],
        review["stage1_consensus_seal"],
        review["reviewer_a_stage2_seal"],
        review["reviewer_b_stage2_seal"],
        review["arbitration_stage2_seal"],
    ]
    counts = {
        "development": {"cases": 60},
        "locked-inputs": {"cases": 120},
        "locked-labels": {
            "cases": 120,
            "reviewer_a_stage1": 120,
            "reviewer_b_stage1": 120,
            "arbitration_stage1": 0,
            "stage1_consensus": 120,
            "stage2_reference_packet": 120,
            "reviewer_a_stage2": 120,
            "reviewer_b_stage2": 120,
            "arbitration_stage2": 0,
            "unresolved": 0,
        },
        "reports": {"json_reports": 1, "markdown_reports": 1},
        "manifests": {
            "development_cases": 60,
            "locked_cases": 120,
            "registered_artifacts": sum(
                len(names) for names in v.REGISTERED_LEAF_MEMBERS.values()
            ),
        },
    }
    schemas = {
        "development": {"development_cases": v.DEVELOPMENT_SCHEMA_VERSION},
        "locked-inputs": {"locked_inputs": v.LOCKED_INPUT_SCHEMA_VERSION},
        "locked-labels": {
            "reviewer_stage1": v.STAGE1_REVIEW_SCHEMA_VERSION,
            "arbitration_stage1": v.STAGE1_ARBITRATION_SCHEMA_VERSION,
            "stage1_consensus": v.STAGE1_CONSENSUS_SCHEMA_VERSION,
            "stage2_reference_packet": v.STAGE2_REFERENCE_PACKET_SCHEMA_VERSION,
            "reviewer_stage2": v.STAGE2_REVIEW_SCHEMA_VERSION,
            "arbitration_stage2": v.STAGE2_ARBITRATION_SCHEMA_VERSION,
            "final_labels": v.FINAL_LABEL_SCHEMA_VERSION,
            "review_seal": v.REVIEW_SEAL_SCHEMA_VERSION,
        },
        "reports": {"validation_set_report": v.VALIDATION_REPORT_SCHEMA_VERSION},
        "manifests": {
            "case_mapping": v.MAPPING_SCHEMA_VERSION,
            "visibility_ledger": v.VISIBILITY_LEDGER_SCHEMA_VERSION,
            "overlap_report": "phase1-parser-v2-overlap-report/v1",
        },
    }
    ids = {
        "development": development_ids,
        "locked-inputs": locked_ids,
        "locked-labels": locked_ids,
        "reports": [],
        "manifests": all_ids,
    }
    features = {
        "development": composition["feature_counts"]["development"],
        "locked-inputs": composition["feature_counts"]["locked"],
        "locked-labels": composition["feature_counts"]["locked"],
        "reports": {},
        "manifests": composition["feature_counts"],
    }
    arbitration = {
        leaf: (
            {"stage1": 0, "stage2": 0, "unresolved": 0}
            if leaf in {"locked-labels", "manifests"}
            else {"stage1": 0, "stage2": 0, "unresolved": 0}
        )
        for leaf in v.REGISTERED_LEAF_MEMBERS
    }
    expected_relative = [
        f"{leaf}/{name}"
        for leaf, names in v.REGISTERED_LEAF_MEMBERS.items()
        for name in names
    ]
    for leaf, names in v.REGISTERED_LEAF_MEMBERS.items():
        paths = (
            expected_relative[:-1]
            if leaf == "manifests"
            else [f"{leaf}/{name}" for name in names[:-1]]
        )
        manifest = v.build_manifest(
            manifest_kind=leaf,
            project_root=ROOT,
            created_utc=timestamp,
            parent_prefix=parent,
            ordered_case_ids=ids[leaf],
            counts=counts[leaf],
            schemas=schemas[leaf],
            files={path: files[path] for path in paths},
            reservation_sha256=v.sha256_bytes(files[f"{leaf}/{names[0]}"]),
            review_seals=seals if leaf in {"locked-labels", "manifests"} else [],
            arbitration=arbitration[leaf],
            feature_counts=features[leaf],
            visibility_ledger_sha256=visibility_hash,
            source_prefixes=source_prefixes,
            private_nonce=f"private-nonce-{list(v.REGISTERED_LEAF_MEMBERS).index(leaf):04d}",
        )
        files[f"{leaf}/{names[-1]}"] = v.canonical_json_bytes(manifest)
    return {name: files[name] for name in expected_relative}


def _synthetic_historical_fingerprint_artifacts(
    text: str = "synthetic non-overlapping historical fingerprint",
) -> dict[str, object]:
    exact = v.sha256_bytes(text.encode("utf-8"))
    normalized = v.sha256_bytes(
        v.normalize_fixture_text(text).encode("utf-8")
    )
    rows = [
        {
            "source": f"generation:0:output:{exact[:16]}",
            "exact_sha256": exact,
            "normalized_sha256": normalized,
        }
    ]
    fingerprint_bytes = v.canonical_jsonl_bytes(rows)
    summary = {
        "schema_version": v.HISTORICAL_FINGERPRINT_SUMMARY_SCHEMA_VERSION,
        "fingerprint_schema_version": v.HISTORICAL_FINGERPRINT_SCHEMA_VERSION,
        "status": "PASS",
        "protocol_commit": v.FROZEN_PROTOCOL_COMMIT,
        "source_artifact_sha256s": deepcopy(v.HISTORICAL_SOURCE_HASHES),
        "fingerprint_jsonl_sha256": v.sha256_bytes(fingerprint_bytes),
        "fingerprint_count": len(rows),
        "contains_historical_text": False,
    }
    return {
        "rows": rows,
        "fingerprint_bytes": fingerprint_bytes,
        "summary_bytes": v.canonical_json_bytes(summary),
    }


@pytest.fixture
def historical_fingerprint_bundle(monkeypatch):
    bundle = _synthetic_historical_fingerprint_artifacts()
    hashes = {
        "historical_output_fingerprints.jsonl": v.sha256_bytes(
            bundle["fingerprint_bytes"]
        ),
        "historical_output_fingerprint_summary.json": v.sha256_bytes(
            bundle["summary_bytes"]
        ),
    }
    monkeypatch.setattr(
        v, "HISTORICAL_FINGERPRINT_ARTIFACT_HASHES", hashes
    )
    monkeypatch.setattr(
        persister.validation,
        "HISTORICAL_FINGERPRINT_ARTIFACT_HASHES",
        hashes,
    )
    return bundle


@pytest.fixture
def eligible_production_bundle(dataset, monkeypatch):
    bundle = _synthetic_production_bundle(dataset)
    _register_synthetic_production_hashes(
        monkeypatch, bundle, module=persister.validation
    )
    return bundle


def test_historical_fingerprint_bundle_is_canonical_bound_and_non_content(
    historical_fingerprint_bundle,
):
    secret = "synthetic non-overlapping historical fingerprint"
    assert secret.encode() not in historical_fingerprint_bundle[
        "fingerprint_bytes"
    ]
    assert secret.encode() not in historical_fingerprint_bundle[
        "summary_bytes"
    ]
    assert v.validate_historical_fingerprint_bundle(
        historical_fingerprint_bundle["fingerprint_bytes"],
        historical_fingerprint_bundle["summary_bytes"],
    ) == historical_fingerprint_bundle["rows"]


def test_registered_historical_summary_schema_is_strictly_normalized(monkeypatch):
    exact_a = "a" * 64
    exact_b = "b" * 64
    normalized = "c" * 64
    rows = [
        {
            "source": f"generation:0:output:{exact_a[:16]}",
            "exact_sha256": exact_a,
            "normalized_sha256": normalized,
        },
        {
            "source": f"evaluation:0:output:{exact_a[:16]}",
            "exact_sha256": exact_a,
            "normalized_sha256": normalized,
        },
        {
            "source": f"generation:1:output:{exact_b[:16]}",
            "exact_sha256": exact_b,
            "normalized_sha256": normalized,
        },
    ]
    fingerprint_bytes = v.canonical_jsonl_bytes(rows)
    summary = {
        "schema_version": "phase1-parser-v2-history-fingerprints/v1",
        "fingerprint_records": len(rows),
        "fingerprint_sha256": v.sha256_bytes(fingerprint_bytes),
        "historical_text_in_artifact": False,
        "protocol_commit": v.FROZEN_PROTOCOL_COMMIT,
        "source_hashes": deepcopy(v.HISTORICAL_SOURCE_HASHES),
        "unique_exact_hashes": len({row["exact_sha256"] for row in rows}),
        "unique_normalized_hashes": len(
            {row["normalized_sha256"] for row in rows}
        ),
    }
    summary_bytes = v.canonical_json_bytes(summary)
    monkeypatch.setattr(
        v,
        "HISTORICAL_FINGERPRINT_ARTIFACT_HASHES",
        {
            "historical_output_fingerprints.jsonl": v.sha256_bytes(
                fingerprint_bytes
            ),
            "historical_output_fingerprint_summary.json": v.sha256_bytes(
                summary_bytes
            ),
        },
    )
    assert v.validate_historical_fingerprint_bundle(
        fingerprint_bytes, summary_bytes
    ) == rows

    for field in ("unique_exact_hashes", "unique_normalized_hashes"):
        invalid = deepcopy(summary)
        invalid[field] += 1
        invalid_bytes = v.canonical_json_bytes(invalid)
        monkeypatch.setitem(
            v.HISTORICAL_FINGERPRINT_ARTIFACT_HASHES,
            "historical_output_fingerprint_summary.json",
            v.sha256_bytes(invalid_bytes),
        )
        with pytest.raises(v.ValidationSetError, match="binding is invalid"):
            v.validate_historical_fingerprint_bundle(
                fingerprint_bytes, invalid_bytes
            )


def test_registered_historical_row_schema_is_strictly_normalized(monkeypatch):
    first_exact = "a" * 64
    second_exact = "b" * 64
    normalized = "c" * 64
    external = [
        {
            "source_file": "phase1_generations.jsonl",
            "record_index": 1,
            "field": "output",
            "exact_sha256": first_exact,
            "normalized_sha256": normalized,
            "masked_5gram_sha256": ["d" * 64],
        },
        {
            "source_file": "phase1_eval_records.jsonl",
            "record_index": 45,
            "field": "eval_output",
            "exact_sha256": second_exact,
            "normalized_sha256": normalized,
            "masked_5gram_sha256": ["e" * 64, "f" * 64],
        },
    ]
    internal = [
        {
            "source": f"generation:0:output:{first_exact[:16]}",
            "exact_sha256": first_exact,
            "normalized_sha256": normalized,
        },
        {
            "source": f"evaluation:44:eval_output:{second_exact[:16]}",
            "exact_sha256": second_exact,
            "normalized_sha256": normalized,
        },
    ]
    fingerprint_bytes = v.canonical_jsonl_bytes(external)
    summary = {
        "schema_version": "phase1-parser-v2-history-fingerprints/v1",
        "fingerprint_records": 2,
        "fingerprint_sha256": v.sha256_bytes(fingerprint_bytes),
        "historical_text_in_artifact": False,
        "protocol_commit": v.FROZEN_PROTOCOL_COMMIT,
        "source_hashes": deepcopy(v.HISTORICAL_SOURCE_HASHES),
        "unique_exact_hashes": 2,
        "unique_normalized_hashes": 1,
    }
    summary_bytes = v.canonical_json_bytes(summary)
    hashes = {
        "historical_output_fingerprints.jsonl": v.sha256_bytes(
            fingerprint_bytes
        ),
        "historical_output_fingerprint_summary.json": v.sha256_bytes(
            summary_bytes
        ),
    }
    monkeypatch.setattr(v, "HISTORICAL_FINGERPRINT_ARTIFACT_HASHES", hashes)
    assert v.validate_historical_fingerprint_bundle(
        fingerprint_bytes, summary_bytes
    ) == internal

    invalid_rows = []
    mixed = deepcopy(external)
    mixed.append(internal[0])
    invalid_rows.append((mixed, "mixed or invalid schemas"))
    for record_index in (0, 46):
        invalid = deepcopy(external)
        invalid[0]["record_index"] = record_index
        invalid_rows.append((invalid, "record_index"))
    empty = deepcopy(external)
    empty[0]["masked_5gram_sha256"] = []
    invalid_rows.append((empty, "nonempty list"))
    duplicate = deepcopy(external)
    duplicate[0]["masked_5gram_sha256"] = ["d" * 64, "d" * 64]
    invalid_rows.append((duplicate, "sorted and unique"))
    unsorted = deepcopy(external)
    unsorted[0]["masked_5gram_sha256"] = ["e" * 64, "d" * 64]
    invalid_rows.append((unsorted, "sorted and unique"))
    for rows, message in invalid_rows:
        with pytest.raises(v.ValidationSetError, match=message):
            v._normalize_historical_fingerprint_rows(rows)


class _FakeBlobService:
    def __init__(self, *, corrupt_download: str | None = None, add_extra=False):
        self.store: dict[str, bytes] = {}
        self.etags: dict[str, str] = {}
        self.uploads: list[tuple[str, bool]] = []
        self.corrupt_download = corrupt_download
        self.add_extra = add_extra

    def get_blob_client(self, *, container, blob):
        service = self

        class Download:
            def readall(self):
                data = service.store[blob]
                if service.corrupt_download == blob:
                    return data + b"x"
                return data

        class Blob:
            def upload_blob(self, data, overwrite):
                if blob in service.store:
                    raise FileExistsError(blob)
                service.uploads.append((blob, overwrite))
                service.store[blob] = bytes(data)
                service.etags[blob] = f'"{hashlib.sha256(data).hexdigest()}"'
                if service.add_extra and blob.endswith("development_cases.jsonl"):
                    service.store[
                        blob.rsplit("/", 1)[0] + "/unexpected.json"
                    ] = b"{}\n"
                    service.etags[
                        blob.rsplit("/", 1)[0] + "/unexpected.json"
                    ] = '"extra"'

            def get_blob_properties(self):
                return SimpleNamespace(
                    size=len(service.store[blob]), etag=service.etags[blob]
                )

            def download_blob(self):
                return Download()

        return Blob()

    def get_container_client(self, container):
        service = self
        return SimpleNamespace(
            list_blobs=lambda **kwargs: iter(
                {"name": name}
                for name in sorted(service.store)
                if name.startswith(kwargs["name_starts_with"])
            )
        )


def test_persistence_uses_overwrite_false_reservation_first_manifest_last_and_hashes(
    dataset, historical_fingerprint_bundle, eligible_production_bundle
):
    service = _FakeBlobService()
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T010000Z"
    files = _valid_registered_file_bytes(dataset, parent)
    report = persister.persist_registered_artifacts(
        service,
        "private-data",
        parent,
        files,
        source_prefixes=["independent/source"],
        production_artifact_bytes=eligible_production_bundle,
        historical_fingerprint_jsonl=historical_fingerprint_bundle[
            "fingerprint_bytes"
        ],
        historical_fingerprint_summary=historical_fingerprint_bundle[
            "summary_bytes"
        ],
    )
    assert report["verified_count"] == len(files)
    assert all(overwrite is False for _, overwrite in service.uploads)
    assert service.uploads[0][0].endswith(
        "/development/.development_reservation.json"
    )
    assert service.uploads[-1][0].endswith(
        "/manifests/locked_manifest.json"
    )


def test_persistence_recomputes_historical_overlap_before_any_write(
    dataset, monkeypatch, eligible_production_bundle
):
    service = _FakeBlobService()
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T010009Z"
    files = _valid_registered_file_bytes(dataset, parent)
    development = v.parse_jsonl_strict(
        files["development/development_cases.jsonl"], "development"
    )
    bundle = _synthetic_historical_fingerprint_artifacts(
        development[0]["output_text"]
    )
    hashes = {
        "historical_output_fingerprints.jsonl": v.sha256_bytes(
            bundle["fingerprint_bytes"]
        ),
        "historical_output_fingerprint_summary.json": v.sha256_bytes(
            bundle["summary_bytes"]
        ),
    }
    monkeypatch.setattr(
        persister.validation,
        "HISTORICAL_FINGERPRINT_ARTIFACT_HASHES",
        hashes,
    )
    with pytest.raises(
        persister.ValidationSetError,
        match="historical_exact_overlaps differs",
    ):
        persister.persist_registered_artifacts(
            service,
            "private-data",
            parent,
            files,
            source_prefixes=["independent/source"],
            production_artifact_bytes=eligible_production_bundle,
            historical_fingerprint_jsonl=bundle["fingerprint_bytes"],
            historical_fingerprint_summary=bundle["summary_bytes"],
        )
    assert service.uploads == []
    assert service.store == {}


def test_persistence_rejects_release_not_bound_to_registered_production_before_write(
    dataset, historical_fingerprint_bundle, eligible_production_bundle
):
    service = _FakeBlobService()
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T010010Z"
    files = _valid_registered_file_bytes(dataset, parent)
    mapping = v.parse_json_strict(
        files["manifests/locked_case_mapping.json"], "mapping"
    )
    mapping["selection_plan_sha256"] = "9" * 64
    files["manifests/locked_case_mapping.json"] = v.canonical_json_bytes(mapping)
    with pytest.raises(
        persister.ValidationSetError,
        match="registered production selection",
    ):
        persister.persist_registered_artifacts(
            service,
            "private-data",
            parent,
            files,
            source_prefixes=["independent/source"],
            production_artifact_bytes=eligible_production_bundle,
            historical_fingerprint_jsonl=historical_fingerprint_bundle[
                "fingerprint_bytes"
            ],
            historical_fingerprint_summary=historical_fingerprint_bundle[
                "summary_bytes"
            ],
        )
    assert service.uploads == []
    assert service.store == {}


def test_release_preflight_uses_immutable_stage2_packet(
    dataset, historical_fingerprint_bundle
):
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T011000Z"
    files = _valid_registered_file_bytes(dataset, parent)
    packet = v.parse_jsonl_strict(
        files["locked-labels/stage2_reference_packet.jsonl"], "packet"
    )
    packet[0]["registered_reference_answer"] = (
        "1" if packet[0]["registered_reference_answer"] != "1" else "2"
    )
    files["locked-labels/stage2_reference_packet.jsonl"] = (
        v.canonical_jsonl_bytes(packet)
    )
    with pytest.raises(v.ValidationSetError, match="mismatch"):
        v.validate_release_artifacts(
            files,
            parent,
            project_root=ROOT,
            historical_fingerprints=historical_fingerprint_bundle["rows"],
            registered_draft_labels=dataset["materialized"][
                "locked_draft_labels"
            ],
            source_prefixes=["independent/source"],
        )


def test_release_preflight_recomputes_near_duplicates(
    dataset, monkeypatch, historical_fingerprint_bundle
):
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T011001Z"
    files = _valid_registered_file_bytes(dataset, parent)
    mapping = dataset["mapping"]["entries"]
    left = next(item for item in mapping if item["set"] == "development")
    right = next(item for item in mapping if item["set"] == "locked")
    finding = {
        "left_id": min(left["candidate_id"], right["candidate_id"]),
        "right_id": max(left["candidate_id"], right["candidate_id"]),
        "left_set": (
            left["set"]
            if left["candidate_id"] < right["candidate_id"]
            else right["set"]
        ),
        "right_set": (
            right["set"]
            if left["candidate_id"] < right["candidate_id"]
            else left["set"]
        ),
        "similarity_numerator": 17,
        "similarity_denominator": 20,
        "similarity": "0.850000",
    }
    monkeypatch.setattr(
        v, "near_duplicate_report", lambda *_args, **_kwargs: [finding]
    )
    with pytest.raises(v.ValidationSetError, match="near_duplicates differs"):
        v.validate_release_artifacts(
            files,
            parent,
            project_root=ROOT,
            historical_fingerprints=historical_fingerprint_bundle["rows"],
            registered_draft_labels=dataset["materialized"][
                "locked_draft_labels"
            ],
            source_prefixes=["independent/source"],
        )


def test_release_report_metrics_and_markdown_must_be_derived(
    dataset, historical_fingerprint_bundle
):
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T011002Z"
    files = _valid_registered_file_bytes(dataset, parent)
    report = v.parse_json_strict(
        files["reports/validation_set_report.json"], "report"
    )
    report["agreement"]["selected_span_exact_count"] -= 1
    files["reports/validation_set_report.json"] = v.canonical_json_bytes(report)
    files["reports/validation_set_report.md"] = (
        v.render_validation_report_markdown(report)
    )
    with pytest.raises(v.ValidationSetError, match="metrics are not derived"):
        v.validate_release_artifacts(
            files,
            parent,
            project_root=ROOT,
            historical_fingerprints=historical_fingerprint_bundle["rows"],
            registered_draft_labels=dataset["materialized"][
                "locked_draft_labels"
            ],
            source_prefixes=["independent/source"],
        )


def test_release_visibility_must_cover_every_sealed_actor(
    dataset, historical_fingerprint_bundle
):
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T011003Z"
    files = _valid_registered_file_bytes(dataset, parent)
    rows = v.parse_jsonl_strict(
        files["manifests/visibility_ledger.jsonl"], "visibility"
    )
    rows.pop()
    files["manifests/visibility_ledger.jsonl"] = v.canonical_jsonl_bytes(rows)
    with pytest.raises(v.ValidationSetError, match="actor/role membership"):
        v.validate_release_artifacts(
            files,
            parent,
            project_root=ROOT,
            historical_fingerprints=historical_fingerprint_bundle["rows"],
            registered_draft_labels=dataset["materialized"][
                "locked_draft_labels"
            ],
            source_prefixes=["independent/source"],
        )


def test_visibility_rejects_cross_role_and_continuity_aliasing(dataset):
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T011004Z"
    files = _valid_registered_file_bytes(dataset, parent)
    rows = v.parse_jsonl_strict(
        files["manifests/visibility_ledger.jsonl"], "visibility"
    )
    locked_manifest = v.parse_json_strict(
        files["locked-labels/locked_labels_manifest.json"],
        "locked-labels manifest",
    )
    review_seals = locked_manifest["review_seals"]
    mapping = dataset["mapping"]

    def rejected(
        changed_rows,
        changed_seals,
        *,
        custodian_id=mapping["custodian_id"],
    ):
        with pytest.raises(
            v.ValidationSetError,
            match="separation|continuity|distinct|not registered",
        ):
            v.validate_visibility_ledger(
                changed_rows,
                curator_pool_seals=mapping["curator_pool_seals"],
                curator_c_id=mapping["curator_c_id"],
                custodian_id=custodian_id,
                review_seals=changed_seals,
            )

    curator_id = mapping["curator_pool_seals"][0]["curator_id"]
    aliased_rows = deepcopy(rows)
    aliased_seals = deepcopy(review_seals)
    reviewer_id = aliased_seals[0]["actor_id"]
    aliased_seals[0]["actor_id"] = curator_id
    aliased_seals[4]["actor_id"] = curator_id
    for row in aliased_rows:
        if row["actor_id"] == reviewer_id and row["role"] in {
            "stage1_reviewer",
            "stage2_reviewer",
        }:
            row["actor_id"] = curator_id
    rejected(aliased_rows, aliased_seals)

    continuation_rows = deepcopy(rows)
    continuation_seals = deepcopy(review_seals)
    stage2_only = "different-stage2-reviewer"
    stage1_reviewer = continuation_seals[0]["actor_id"]
    continuation_seals[4]["actor_id"] = stage2_only
    for row in continuation_rows:
        if (
            row["actor_id"] == stage1_reviewer
            and row["role"] == "stage2_reviewer"
        ):
            row["actor_id"] = stage2_only
    rejected(continuation_rows, continuation_seals)

    consensus_seals = deepcopy(review_seals)
    consensus_seals[3]["actor_id"] = "different-consensus-actor"
    rejected(deepcopy(rows), consensus_seals)

    arbiter_rows = deepcopy(rows)
    arbiter_seals = deepcopy(review_seals)
    arbiter_id = arbiter_seals[2]["actor_id"]
    reviewer_id = arbiter_seals[0]["actor_id"]
    for seal_index in (2, 3, 6):
        arbiter_seals[seal_index]["actor_id"] = reviewer_id
    for row in arbiter_rows:
        if row["actor_id"] == arbiter_id and row["role"] in {
            "stage1_arbiter",
            "stage2_arbiter",
        }:
            row["actor_id"] = reviewer_id
    rejected(arbiter_rows, arbiter_seals)

    custodian_rows = deepcopy(rows)
    for row in custodian_rows:
        if row["role"] == "custodian":
            row["actor_id"] = curator_id
    rejected(custodian_rows, deepcopy(review_seals), custodian_id=curator_id)


def test_curator_c_and_historical_custodian_have_distinct_visibility(dataset):
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T011005Z"
    files = _valid_registered_file_bytes(dataset, parent)
    rows = v.parse_jsonl_strict(
        files["manifests/visibility_ledger.jsonl"], "visibility"
    )
    curator_c = next(row for row in rows if row["role"] == "curator_c")
    custodian = next(row for row in rows if row["role"] == "custodian")
    assert curator_c["actor_id"] == v.REGISTERED_CURATOR_C_ID
    assert custodian["actor_id"] == v.REGISTERED_CUSTODIAN_ID
    assert curator_c["actor_id"] != custodian["actor_id"]
    assert "historical-corpus" not in curator_c["artifact_classes"]
    assert "historical-corpus" in custodian["artifact_classes"]


def test_persistence_rejects_extra_member_before_manifest(
    dataset, historical_fingerprint_bundle, eligible_production_bundle
):
    service = _FakeBlobService(add_extra=True)
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T010001Z"
    with pytest.raises(persister.ValidationSetError, match="before manifest"):
        persister.persist_registered_artifacts(
            service,
            "private-data",
            parent,
            _valid_registered_file_bytes(dataset, parent),
            source_prefixes=["independent/source"],
            production_artifact_bytes=eligible_production_bundle,
            historical_fingerprint_jsonl=historical_fingerprint_bundle[
                "fingerprint_bytes"
            ],
            historical_fingerprint_summary=historical_fingerprint_bundle[
                "summary_bytes"
            ],
        )
    assert f"{parent}/development/development_manifest.json" not in service.store


def test_persistence_redownload_hash_or_size_mismatch_fails(
    dataset, historical_fingerprint_bundle, eligible_production_bundle
):
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T010002Z"
    corrupt = f"{parent}/development/development_cases.jsonl"
    service = _FakeBlobService(corrupt_download=corrupt)
    with pytest.raises(persister.ValidationSetError, match="size mismatch"):
        persister.persist_registered_artifacts(
            service,
            "private-data",
            parent,
            _valid_registered_file_bytes(dataset, parent),
            source_prefixes=["independent/source"],
            production_artifact_bytes=eligible_production_bundle,
            historical_fingerprint_jsonl=historical_fingerprint_bundle[
                "fingerprint_bytes"
            ],
            historical_fingerprint_summary=historical_fingerprint_bundle[
                "summary_bytes"
            ],
        )


def test_semantic_persistence_preflight_rejects_placeholders_before_write(
    historical_fingerprint_bundle, eligible_production_bundle,
):
    service = _FakeBlobService()
    with pytest.raises(persister.ValidationSetError):
        persister.persist_registered_artifacts(
            service,
            "private-data",
            "phase1-evaluator-validation/parser-v2-v1/20260715T010003Z",
            _invalid_registered_file_bytes(),
            source_prefixes=["independent/source"],
            production_artifact_bytes=eligible_production_bundle,
            historical_fingerprint_jsonl=historical_fingerprint_bundle[
                "fingerprint_bytes"
            ],
            historical_fingerprint_summary=historical_fingerprint_bundle[
                "summary_bytes"
            ],
        )
    assert service.uploads == []
    assert service.store == {}


def test_registered_local_membership_rejects_extra_files(workdir, dataset):
    parent = "phase1-evaluator-validation/parser-v2-v1/20260715T010004Z"
    expected = _valid_registered_file_bytes(dataset, parent)
    for leaf, names in v.REGISTERED_LEAF_MEMBERS.items():
        directory = workdir / leaf
        directory.mkdir()
        for name in names:
            data = expected[f"{leaf}/{name}"]
            (directory / name).write_bytes(data)
    files = v.validate_registered_local_membership(workdir)
    assert list(files) == list(expected)
    (workdir / "reports" / "extra.json").write_bytes(b"{}\n")
    with pytest.raises(v.ValidationSetError, match="membership"):
        v.validate_registered_local_membership(workdir)


def test_private_paths_must_be_external_to_repository():
    with pytest.raises(v.ValidationSetError, match="outside the repository"):
        builder.validate_external_private_path(
            ROOT / "ignored-private-input.json",
            name="private salts",
        )
    with pytest.raises(
        persister.ValidationSetError, match="outside the repository"
    ):
        persister.validate_external_local_root(ROOT / "ignored-private-root")


@pytest.mark.parametrize(
    ("url", "environment"),
    [
        (
            "http://accountname.blob.core.windows.net",
            {"AZURE_CLIENT_ID": "client"},
        ),
        (
            "https://accountname.blob.core.windows.net/container",
            {"AZURE_CLIENT_ID": "client"},
        ),
        (
            "https://accountname.blob.core.windows.net/?sig=secret",
            {"AZURE_CLIENT_ID": "client"},
        ),
        (
            "https://accountname.blob.core.windows.net",
            {"AZURE_CLIENT_ID": "client", "AZURE_STORAGE_KEY": "secret"},
        ),
        (
            "https://accountname.blob.core.windows.net",
            {"AZURE_CLIENT_ID": "client", "azure_storage_key": "secret"},
        ),
    ],
)
def test_managed_identity_configuration_rejects_key_sas_and_public_paths(
    url, environment
):
    with pytest.raises(persister.ValidationSetError):
        persister.validate_managed_identity_configuration(url, environment)


def test_azure_imports_are_lazy_and_managed_identity_uses_client_id(monkeypatch):
    calls = []

    class Credential:
        def __init__(self, *, client_id):
            calls.append(("credential", client_id))

    class Service:
        def __init__(self, *, account_url, credential):
            calls.append(("service", account_url, type(credential).__name__))

    modules = {
        "azure.identity": SimpleNamespace(ManagedIdentityCredential=Credential),
        "azure.storage.blob": SimpleNamespace(BlobServiceClient=Service),
    }
    monkeypatch.setattr(
        persister.importlib, "import_module", lambda name: modules[name]
    )
    service = persister.create_blob_service(
        "https://accountname.blob.core.windows.net",
        {"AZURE_CLIENT_ID": "registered-client-id"},
    )
    assert isinstance(service, Service)
    assert calls[0] == ("credential", "registered-client-id")


def test_persistence_cli_never_prints_data_bearing_exception_text(
    monkeypatch, capsys
):
    secret = "PRIVATE-LOCKED-BYTES"
    monkeypatch.setattr(
        persister,
        "validate_managed_identity_configuration",
        lambda account_url, environment: (account_url, "client"),
    )

    def fail_without_reading(_):
        raise persister.ValidationSetError(secret)

    monkeypatch.setattr(
        persister.validation,
        "validate_registered_local_membership",
        fail_without_reading,
    )
    result = persister.main(
        [
            "--account-url",
            "https://accountname.blob.core.windows.net",
            "--container",
            "private-data",
            "--parent-prefix",
            "phase1-evaluator-validation/parser-v2-v1/20260715T010005Z",
            "--source-prefix",
            "independent/source",
            "--local-root",
            "not-read",
            "--historical-fingerprints",
            "not-read-fingerprints",
            "--historical-fingerprint-summary",
            "not-read-fingerprint-summary",
            "--curator-a-pool",
            "not-read-a-pool",
            "--curator-a-seal",
            "not-read-a-seal",
            "--curator-b-pool",
            "not-read-b-pool",
            "--curator-b-seal",
            "not-read-b-seal",
            "--selection-plan",
            "not-read-selection",
            "--curator-c-summary",
            "not-read-summary",
        ]
    )
    captured = capsys.readouterr()
    assert result == 2
    assert secret not in captured.err


def test_manifest_schema_binds_hashes_counts_and_no_model_run(dataset):
    case_ids = [
        row["case_id"] for row in dataset["materialized"]["development"]
    ]
    manifest = v.build_manifest(
        manifest_kind="development",
        project_root=ROOT,
        created_utc="2026-07-15T12:00:00Z",
        parent_prefix="phase1-evaluator-validation/parser-v2-v1/20260715T010006Z",
        ordered_case_ids=case_ids,
        counts={"development": 60},
        schemas={"development": v.DEVELOPMENT_SCHEMA_VERSION},
        files={"development/development_cases.jsonl": b"{}\n"},
        reservation_sha256="a" * 64,
        review_seals=[],
        arbitration={"stage1": 0, "stage2": 0},
        feature_counts={"balanced_think_tags": 5},
        visibility_ledger_sha256="b" * 64,
        source_prefixes=["independent/source"],
        private_nonce="private-nonce-0000001",
    )
    assert manifest["model_inference_performed"] is False
    assert manifest["no_model_run_attestation"] is True
    assert manifest["manifest_uploaded_last"] is True
    assert v.validate_manifest(manifest)["case_count"] == 60


_STATE_PARENT_PREFIX = (
    "phase1-evaluator-validation/parser-v2-v1/20260715T010006Z"
)


def _implementation_manifest_bytes(
    *,
    implementation_commit: str = "d" * 40,
    image_digest: str = "sha256:" + "e" * 64,
    config_sha256: str = "f" * 64,
) -> bytes:
    return v.canonical_json_bytes(
        {
            "schema_version": v.IMPLEMENTATION_MANIFEST_SCHEMA_VERSION,
            "implementation_commit": implementation_commit,
            "image_digest": image_digest,
            "config_sha256": config_sha256,
        }
    )


def _state_receipt(
    state: str,
    index: int,
    previous: dict | None,
    *,
    authorization_id: str = "authorization-one",
    implementation_commit: str = "d" * 40,
    image_digest: str = "sha256:" + "e" * 64,
    config_sha256: str = "f" * 64,
) -> dict:
    state_index = v.HOLDOUT_STATES.index(state)
    implementation_bound = state_index >= v.HOLDOUT_STATES.index(
        "IMPLEMENTATION_FROZEN"
    )
    manifests = (
        {} if previous is None else deepcopy(previous["artifact_manifest_hashes"])
    )
    for key in v.STATE_AUTHORIZED_ARTIFACT_BINDINGS[state]:
        manifests[key] = (
            v.sha256_bytes(
                _implementation_manifest_bytes(
                    implementation_commit=implementation_commit,
                    image_digest=image_digest,
                    config_sha256=config_sha256,
                )
            )
            if key == "implementation_manifest"
            else hashlib.sha256(key.encode("ascii")).hexdigest()
        )
    authorization_lock_hash = None
    if implementation_bound:
        authorization_lock_hash = (
            previous["authorization_lock_sha256"]
            if previous is not None
            and previous["authorization_lock_sha256"] is not None
            else "1" * 64
        )
    return {
        "schema_version": v.STATE_RECEIPT_SCHEMA_VERSION,
        "authorization_id": authorization_id,
        "state": state,
        "previous_state": None if previous is None else previous["state"],
        "previous_receipt_sha256": (
            None if previous is None else v.state_receipt_sha256(previous)
        ),
        "timestamp_utc": f"2026-07-15T12:00:{index:02d}Z",
        "execution_id": "execution-one",
        "actor": "custodian",
        "visibility": ["aggregate", "state"],
        "registered_parent_prefix": _STATE_PARENT_PREFIX,
        "protocol_commit": v.FROZEN_PROTOCOL_COMMIT,
        "protocol_bundle_sha256": v.protocol_bundle_sha256(ROOT),
        "acceptance_gates_sha256": v.acceptance_gates_sha256(ROOT),
        "implementation_commit": (
            implementation_commit if implementation_bound else None
        ),
        "image_digest": image_digest if implementation_bound else None,
        "config_sha256": config_sha256 if implementation_bound else None,
        "authorization_lock_sha256": authorization_lock_hash,
        "artifact_manifest_hashes": manifests,
        "retry_kind": "none",
        "outcome": "PASS" if state == "CLOSED" else None,
        "holdout_spent": state_index
        >= v.HOLDOUT_STATES.index("INPUTS_READ"),
        "holdout_retired": state == "CLOSED",
    }


def _state_chain() -> list[dict]:
    receipts = []
    previous = None
    for index, state in enumerate(v.HOLDOUT_STATES):
        receipt = _state_receipt(state, index, previous)
        if state == "IMPLEMENTATION_FROZEN":
            lock = v.build_authorization_lock(
                previous, receipt, _implementation_manifest_bytes()
            )
            receipt["authorization_lock_sha256"] = (
                v.authorization_lock_sha256(lock)
            )
        receipts.append(receipt)
        previous = receipt
    return receipts


def _state_authorization_lock(chain: list[dict]) -> dict:
    sealed = chain[v.HOLDOUT_STATES.index("SEALED")]
    implementation = chain[v.HOLDOUT_STATES.index("IMPLEMENTATION_FROZEN")]
    return v.build_authorization_lock(
        sealed, implementation, _implementation_manifest_bytes()
    )


def test_one_shot_state_transitions_form_exact_hash_chain():
    chain = _state_chain()
    lock = _state_authorization_lock(chain)
    report = v.validate_state_receipt_chain(
        chain,
        authorization_lock=lock,
        implementation_manifest_bytes=_implementation_manifest_bytes(),
    )
    assert report["state"] == "CLOSED"
    assert report["holdout_spent"] is True
    assert report["holdout_retired"] is True
    assert len({v.state_receipt_sha256(item) for item in chain}) == len(chain)


def test_inputs_read_cannot_be_reentered_as_scientific_retry():
    chain = _state_chain()
    lock = _state_authorization_lock(chain)
    inputs_index = v.HOLDOUT_STATES.index("INPUTS_READ")
    previous = chain[inputs_index]
    rerun = deepcopy(previous)
    rerun["previous_state"] = previous["state"]
    rerun["previous_receipt_sha256"] = v.state_receipt_sha256(previous)
    rerun["timestamp_utc"] = "2026-07-15T12:01:00Z"
    with pytest.raises(v.ValidationSetError, match="advance"):
        v.validate_state_transition(
            previous,
            rerun,
            history=chain[: inputs_index + 1],
            authorization_lock=lock,
            implementation_manifest_bytes=_implementation_manifest_bytes(),
        )


def test_retired_holdout_is_rejected_for_reuse():
    chain = _state_chain()
    lock = _state_authorization_lock(chain)
    with pytest.raises(v.ValidationSetError, match="retired"):
        v.assert_holdout_available(
            chain,
            authorization_lock=lock,
            implementation_manifest_bytes=_implementation_manifest_bytes(),
        )
    attempted = deepcopy(chain[-1])
    attempted["previous_state"] = "CLOSED"
    attempted["previous_receipt_sha256"] = v.state_receipt_sha256(chain[-1])
    attempted["timestamp_utc"] = "2026-07-15T12:01:01Z"
    with pytest.raises(v.ValidationSetError, match="retired"):
        v.validate_state_transition(
            chain[-1], attempted, authorization_lock=lock
        )


def test_spent_holdout_is_unavailable_for_a_new_evaluation():
    chain = _state_chain()
    lock = _state_authorization_lock(chain)
    inputs_index = v.HOLDOUT_STATES.index("INPUTS_READ")
    with pytest.raises(v.ValidationSetError, match="spent"):
        v.assert_holdout_available(
            chain[: inputs_index + 1],
            authorization_lock=lock,
            implementation_manifest_bytes=_implementation_manifest_bytes(),
        )


def test_state_receipt_rejects_modified_implementation_binding():
    chain = _state_chain()
    lock = _state_authorization_lock(chain)
    prediction_index = v.HOLDOUT_STATES.index("PREDICTIONS_VERIFIED")
    previous = chain[prediction_index]
    current = deepcopy(chain[prediction_index + 1])
    current["implementation_commit"] = "c" * 40
    current["previous_receipt_sha256"] = v.state_receipt_sha256(previous)
    with pytest.raises(v.ValidationSetError, match="binding changed"):
        v.validate_state_transition(
            previous, current, authorization_lock=lock
        )


def test_pre_input_retry_requires_identical_artifact_bindings():
    chain = _state_chain()
    previous = deepcopy(chain[v.HOLDOUT_STATES.index("PROTOCOL_FROZEN")])
    current = deepcopy(previous)
    current["previous_state"] = previous["state"]
    current["previous_receipt_sha256"] = v.state_receipt_sha256(previous)
    current["timestamp_utc"] = "2026-07-15T12:01:00Z"
    current["execution_id"] = "execution-retry"
    current["retry_kind"] = "infrastructure_pre_input"
    current["artifact_manifest_hashes"]["acceptance_gates"] = "8" * 64
    with pytest.raises(v.ValidationSetError, match="append-only and immutable"):
        v.validate_state_transition(previous, current)


def test_labels_read_cannot_replace_an_existing_artifact_binding():
    chain = _state_chain()
    lock = _state_authorization_lock(chain)
    labels_index = v.HOLDOUT_STATES.index("LABELS_READ")
    previous = chain[labels_index - 1]
    current = deepcopy(chain[labels_index])
    current["artifact_manifest_hashes"]["locked_manifest"] = "9" * 64
    current["previous_receipt_sha256"] = v.state_receipt_sha256(previous)
    with pytest.raises(v.ValidationSetError, match="append-only and immutable"):
        v.validate_state_transition(
            previous, current, authorization_lock=lock
        )


def test_authorization_lock_and_graph_reject_holdout_forks():
    chain = _state_chain()
    sealed_index = v.HOLDOUT_STATES.index("SEALED")
    sealed = chain[sealed_index]
    first = chain[sealed_index + 1]
    first_lock = _state_authorization_lock(chain)

    second_manifest = _implementation_manifest_bytes(
        implementation_commit="c" * 40
    )
    second = _state_receipt(
        "IMPLEMENTATION_FROZEN",
        30,
        sealed,
        implementation_commit="c" * 40,
    )
    second["execution_id"] = "execution-two"
    second_lock = v.build_authorization_lock(
        sealed, second, second_manifest
    )
    second["authorization_lock_sha256"] = v.authorization_lock_sha256(
        second_lock
    )

    v.validate_state_transition(
        sealed,
        first,
        authorization_lock=first_lock,
        implementation_manifest_bytes=_implementation_manifest_bytes(),
    )
    v.validate_state_transition(
        sealed,
        second,
        authorization_lock=second_lock,
        implementation_manifest_bytes=second_manifest,
    )
    with pytest.raises(v.ValidationSetError, match="divergent branch"):
        v.validate_state_receipt_graph(
            [*chain[: sealed_index + 1], first, second],
            authorization_lock=first_lock,
            implementation_manifest_bytes=_implementation_manifest_bytes(),
        )

    alternate_sealed = deepcopy(sealed)
    alternate_sealed["authorization_id"] = "authorization-two"
    alternate_sealed["timestamp_utc"] = "2026-07-15T12:02:00Z"
    alternate_implementation = _state_receipt(
        "IMPLEMENTATION_FROZEN",
        31,
        alternate_sealed,
        authorization_id="authorization-two",
    )
    alternate_lock = v.build_authorization_lock(
        alternate_sealed,
        alternate_implementation,
        _implementation_manifest_bytes(),
    )
    alternate_implementation["authorization_lock_sha256"] = (
        v.authorization_lock_sha256(alternate_lock)
    )
    assert v.authorization_lock_blob_name(
        first_lock
    ) == v.authorization_lock_blob_name(alternate_lock)

    service = _FakeBlobService()
    first_result = persister.persist_authorization_lock_once(
        service,
        "private-data",
        first_lock,
        _implementation_manifest_bytes(),
    )
    assert first_result["blob_name"] == v.authorization_lock_blob_name(
        first_lock
    )
    with pytest.raises(persister.ValidationSetError, match="overwrite-false"):
        persister.persist_authorization_lock_once(
            service,
            "private-data",
            alternate_lock,
            _implementation_manifest_bytes(),
        )


def test_implementation_transition_requires_persisted_authorization_lock():
    chain = _state_chain()
    sealed_index = v.HOLDOUT_STATES.index("SEALED")
    with pytest.raises(v.ValidationSetError, match="requires the authorization lock"):
        v.validate_state_transition(
            chain[sealed_index], chain[sealed_index + 1]
        )


def test_later_transition_rechecks_cumulative_implementation_manifest_hash():
    chain = _state_chain()
    lock = _state_authorization_lock(chain)
    implementation_index = v.HOLDOUT_STATES.index("IMPLEMENTATION_FROZEN")
    previous = deepcopy(chain[implementation_index])
    current = deepcopy(chain[implementation_index + 1])
    previous["artifact_manifest_hashes"]["implementation_manifest"] = "9" * 64
    current["artifact_manifest_hashes"]["implementation_manifest"] = "9" * 64
    current["previous_receipt_sha256"] = v.state_receipt_sha256(previous)
    with pytest.raises(v.ValidationSetError, match="fixed authorization lock"):
        v.validate_state_transition(
            previous,
            current,
            authorization_lock=lock,
            implementation_manifest_bytes=_implementation_manifest_bytes(),
        )


def test_state_and_manifest_reject_mutable_image_tags():
    chain = _state_chain()
    implementation = deepcopy(
        chain[v.HOLDOUT_STATES.index("IMPLEMENTATION_FROZEN")]
    )
    implementation["image_digest"] = "mutable-tag-latest"
    with pytest.raises(v.ValidationSetError, match="immutable OCI"):
        v.validate_state_receipt(implementation)
    with pytest.raises(v.ValidationSetError, match="immutable OCI"):
        v.validate_implementation_manifest(
            _implementation_manifest_bytes(image_digest="mutable-tag-latest")
        )


def test_closed_state_requires_every_cumulative_artifact_binding():
    closed = deepcopy(_state_chain()[-1])
    closed["artifact_manifest_hashes"] = {}
    with pytest.raises(v.ValidationSetError, match="exact cumulative bindings"):
        v.validate_state_receipt(closed)
