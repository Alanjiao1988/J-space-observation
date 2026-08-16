"""Independent recalculation for the Study 3 draft-v0.7 single focused methods review.

This module is written by the independent reviewer of draft-v0.7. It deliberately
does NOT import, exec, or otherwise reuse any of the following, because those are
the artifacts whose numbers it is supposed to check:

* ``studies/study3/analysis/v0_7_protocol_build.py``
* ``studies/study3/analysis/design_statistics.py``
* ``studies/study3/analysis/scoring_boundary_v0_6.py``
* any earlier ``independent_methods_recalculation*.py``
* any production gate calculator

External packages used: NONE. Only the Python standard library
(``argparse``, ``fractions``, ``json``, ``math``, ``pathlib``, ``sys``).
``json`` is used to read committed artifacts and to write the tables file; every
decision-bearing quantity below is recomputed from first principles with exact
rational arithmetic (``fractions.Fraction`` + ``math.comb``), so no floating-point
tolerance is required and none is used in any comparison.

Run:
    python studies/study3/analysis/independent_methods_recalculation_v0_7.py --emit
    python studies/study3/analysis/independent_methods_recalculation_v0_7.py --check
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_DIR = ROOT / "studies" / "study3" / "protocol"
ANALYSIS_DIR = ROOT / "studies" / "study3" / "analysis"

PROTOCOL = PROTOCOL_DIR / "interface_calibration_protocol_draft_v0_7.json"
REGISTRY_V0_7 = PROTOCOL_DIR / "interface_calibration_rendering_registry_v0_7.json"
REGISTRY_V0_6 = PROTOCOL_DIR / "interface_calibration_rendering_registry_v0_6.json"
POINTER = PROTOCOL_DIR / "interface_calibration_protocol_current.json"
TABLES = ANALYSIS_DIR / "independent_methods_recalculation_tables_v0_7.json"

DECIMALS = 12


# ---------------------------------------------------------------------------
# 1. Exact binomial primitives, implemented here from first principles.
# ---------------------------------------------------------------------------


def exact_upper_tail(n: int, c: int, p: Fraction) -> Fraction:
    """Pr(X >= c) for X ~ Binomial(n, p), computed exactly over the rationals.

    The sum is accumulated in pure integer arithmetic over the common
    denominator ``b ** n`` (where ``p == a / b``) and reduced once at the end,
    which is exact and avoids a gcd reduction on every term.
    """
    if c <= 0:
        return Fraction(1)
    if c > n:
        return Fraction(0)
    a = p.numerator
    b = p.denominator
    r = b - a
    numerator = 0
    a_pow = a ** c
    r_pow = r ** (n - c)
    for k in range(c, n + 1):
        numerator += math.comb(n, k) * a_pow * r_pow
        a_pow *= a
        r_pow = r_pow // r if r else 0
    return Fraction(numerator, b ** n)


def minimal_pass_count(n: int, p0: Fraction, alpha: Fraction) -> int:
    """Smallest c with Pr(X >= c | p0) <= alpha.

    Pr(X >= c) is non-increasing in c and Pr(X >= n + 1) = 0 <= alpha, so a
    minimal admissible c always exists in [0, n + 1] and is found by bisection
    rather than by a linear scan.
    """
    low, high = 0, n + 1
    while low < high:
        mid = (low + high) // 2
        if exact_upper_tail(n, mid, p0) <= alpha:
            high = mid
        else:
            low = mid + 1
    return low


def _admissible(n: int, p0: Fraction, p1: Fraction, alpha: Fraction,
                power_target: Fraction):
    c = minimal_pass_count(n, p0, alpha)
    if c > n:
        return None
    power = exact_upper_tail(n, c, p1)
    if power >= power_target:
        return c, power
    return None


def minimal_n_for_power(p0: Fraction, p1: Fraction, alpha: Fraction,
                        power_target: Fraction, n_max: int = 4096) -> tuple:
    """Smallest n whose minimal-alpha critical count also attains power_target at p1.

    Admissibility is NOT monotone in n, because the minimal critical count moves
    in integer jumps, so bisection alone can return a local rather than a global
    minimum. An exponentially growing probe therefore only establishes an upper
    bound, and the reported n is the first admissible n found by an exhaustive
    upward scan below that bound.
    """
    bound = 1
    while bound <= n_max and _admissible(bound, p0, p1, alpha,
                                         power_target) is None:
        bound *= 2
    if bound > n_max:
        return None, None, None
    for n in range(1, bound + 1):
        found = _admissible(n, p0, p1, alpha, power_target)
        if found is not None:
            return n, found[0], found[1]
    return None, None, None


def dec(value: Fraction, places: int = DECIMALS) -> str:
    """Exact rational rendered as a truncation-free rounded decimal string."""
    scaled = value * (10 ** places)
    whole = scaled.numerator // scaled.denominator
    remainder = scaled - whole
    if remainder >= Fraction(1, 2):
        whole += 1
    sign = "-" if whole < 0 else ""
    whole = abs(whole)
    digits = str(whole).rjust(places + 1, "0")
    return "%s%s.%s" % (sign, digits[:-places], digits[-places:])


def rat(text: str) -> Fraction:
    return Fraction(text)


# ---------------------------------------------------------------------------
# 2. Registered inputs, transcribed from the committed protocol as INPUTS only.
#    Every OUTPUT below is recomputed; nothing is copied from the drafting
#    party's derived tables.
# ---------------------------------------------------------------------------

COMPONENT_INPUTS = {
    "I1a+I1b+I3": {"n": 413, "p0": "9/10", "p1": "97/100"},
    "I2": {"n": 214, "p0": "1/2", "p1": "7/10"},
    "I4": {"n": 448, "p0": "4/5", "p1": "9/10"},
}

DEV_ALPHA = "1/600"
CONF_ALPHA = "1/200"

# Structural constants of the registered cell layout, read off the registered
# ``evaluated_per`` factor lists rather than off any derived census.
TARGET_ROLES = 3          # RT, RL, RI
I1A_STRATA = 1            # K2
I1B_STRATA = 1            # K1
I2_OPERATION_FAMILIES = 2  # affine_mod10, permutation_chain
I4_OPERATION_FAMILIES = 2
I4_DEPTHS = 2             # depth 2, depth 3
I3_VARIANTS_PER_CLUSTER = 2


def load(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------------------
# 3. Recalculation blocks.
# ---------------------------------------------------------------------------


def recompute_components() -> dict:
    out = {}
    for name, spec in COMPONENT_INPUTS.items():
        n = spec["n"]
        p0 = rat(spec["p0"])
        p1 = rat(spec["p1"])
        row = {"n": n, "p0_exact_rational": spec["p0"],
               "p1_exact_rational": spec["p1"]}
        for stage, alpha_text in (("development", DEV_ALPHA),
                                  ("confirmation", CONF_ALPHA)):
            alpha = rat(alpha_text)
            c = minimal_pass_count(n, p0, alpha)
            tail = exact_upper_tail(n, c, p0)
            power = exact_upper_tail(n, c, p1)
            tail_one_lower = exact_upper_tail(n, c - 1, p0)
            row[stage] = {
                "alpha_exact_rational": alpha_text,
                "pass_count": c,
                "pass_count_is_minimal_at_alpha": bool(tail_one_lower > alpha),
                "exact_null_tail_at_p0": dec(tail),
                "exact_null_tail_at_p0_rational": "%d/%d" % (tail.numerator,
                                                             tail.denominator),
                "exact_power_at_p1": dec(power),
                "critical_accuracy_exact_rational": "%d/%d" % (c, n),
                "critical_accuracy_decimal": dec(Fraction(c, n)),
            }
        out[name] = row
    return out


def recompute_minimal_sizes(per_cell_power_target: Fraction) -> dict:
    out = {}
    for name, spec in COMPONENT_INPUTS.items():
        n, c, power = minimal_n_for_power(rat(spec["p0"]), rat(spec["p1"]),
                                          rat(DEV_ALPHA), per_cell_power_target)
        out[name] = {
            "minimal_n": n,
            "minimal_pass_count": c,
            "attained_power": dec(power) if power is not None else None,
            "registered_n": spec["n"],
            "registered_n_equals_minimal_n": n == spec["n"],
        }
    return out


def recompute_census(protocol: dict) -> dict:
    """Derive the gate-bearing cell census from the committed gate truth table.

    This is an independent derivation: it counts applicable contrast IDs in the
    truth table and multiplies by the registered evaluated_per factor structure.
    """
    census = {}
    for row in protocol["gate_truth_table"]["rows"]:
        profile = row["profile"]
        k5 = sorted(k for k, v in row["I3_K5"].items() if v == "applicable")
        k6 = sorted(k for k, v in row["I3_K6"].items() if v == "applicable")
        contrasts = k5 + k6
        i1a = TARGET_ROLES * I1A_STRATA if row["I1a"] == "applicable" else 0
        i1b = TARGET_ROLES * I1B_STRATA if row["I1b"] == "applicable" else 0
        i2 = TARGET_ROLES * I2_OPERATION_FAMILIES if row["I2"] == "applicable" else 0
        i3 = TARGET_ROLES * len(contrasts)
        i4 = (I4_OPERATION_FAMILIES * I4_DEPTHS
              if row["I4"] == "applicable" else 0)
        census[profile] = {
            "applicable_i3_contrast_ids": contrasts,
            "applicable_i3_contrast_count": len(contrasts),
            "I1a_cells": i1a,
            "I1b_cells": i1b,
            "I2_cells": i2,
            "I3_K5_cells": TARGET_ROLES * len(k5),
            "I3_K6_cells": TARGET_ROLES * len(k6),
            "I3_cells": i3,
            "I4_cells": i4,
            "cells_at_i1_i3_floor": i1a + i1b + i3,
            "cells_at_i2_floor": i2,
            "cells_at_i4_floor": i4,
            "total_gate_bearing_cells": i1a + i1b + i2 + i3 + i4,
            "selectable": bool(row["selectable"]),
        }
    selectable = [v["total_gate_bearing_cells"]
                  for v in census.values() if v["selectable"]]
    census["m_max_recomputed"] = max(selectable)
    census["m_max_definition"] = ("maximum total gate-bearing cell count over "
                                  "the selectable profiles")
    return census


def recompute_power_architecture(m_max: int) -> dict:
    per_stage_profile_fn = Fraction(19, 400)
    panel_false_qualification = Fraction(1, 200)
    per_cell_fn = per_stage_profile_fn / m_max
    per_cell_power = 1 - per_cell_fn
    profile_stage_power = 1 - m_max * per_cell_fn
    study_power = 1 - per_stage_profile_fn - panel_false_qualification \
        - per_stage_profile_fn
    return {
        "m_max_used": m_max,
        "per_stage_profile_false_negative_budget_exact_rational":
            str(per_stage_profile_fn),
        "panel_false_qualification_budget_exact_rational":
            str(panel_false_qualification),
        "per_cell_false_negative_budget_exact_rational": str(per_cell_fn),
        "per_cell_power_target_exact_rational": str(per_cell_power),
        "per_cell_power_target_decimal": dec(per_cell_power),
        "profile_stage_power_floor_exact_rational": str(profile_stage_power),
        "profile_stage_power_floor_decimal": dec(profile_stage_power, 6),
        "study_end_to_end_power_floor_exact_rational": str(study_power),
        "study_end_to_end_power_floor_decimal": dec(study_power, 6),
    }


def recompute_derived_gaps() -> dict:
    gap = rat("97/100") - rat("9/10")
    restricted_chance = Fraction(1, 10)
    negative_control_bound = restricted_chance + gap
    return {
        "registered_alternative_gap_exact_rational": str(gap),
        "restricted_chance_level_exact_rational": str(restricted_chance),
        "restricted_chance_level_derivation": "1 / 10 registered answer surfaces",
        "negative_control_equivalence_upper_bound_exact_rational":
            str(negative_control_bound),
        "wrapper_descriptive_bandwidth_exact_rational": str(gap),
    }


def recompute_cot_ceiling() -> dict:
    n = 214
    theta = Fraction(1, 2)
    p1 = Fraction(7, 10)
    alpha = rat("1/600")
    c = minimal_pass_count(n, theta, alpha)
    tail = exact_upper_tail(n, c, theta)
    power = exact_upper_tail(n, c, p1)
    chance_e0 = Fraction(1, 10)
    return {
        "n": n,
        "theta_exact_rational": str(theta),
        "p1_exact_rational": str(p1),
        "alpha_exact_rational": str(alpha),
        "recomputed_pass_count": c,
        "exact_null_tail_at_theta": dec(tail),
        "exact_power_at_p1": dec(power),
        "critical_accuracy_exact_rational": "%d/%d" % (c, n),
        "critical_accuracy_decimal": dec(Fraction(c, n)),
        "null_floor_is_not_the_critical_accuracy": True,
        "registered_e0_restricted_chance_level_exact_rational": str(chance_e0),
        "null_floor_equals_e0_restricted_chance_level": theta == chance_e0,
        "identical_to_i2_development_row": True,
    }


def recompute_projection(census: dict) -> dict:
    """Recompute the target-role development projection from the census."""
    n_i3 = COMPONENT_INPUTS["I1a+I1b+I3"]["n"]
    n_i1a = COMPONENT_INPUTS["I1a+I1b+I3"]["n"]
    n_i1b = COMPONENT_INPUTS["I1a+I1b+I3"]["n"]
    n_i2 = COMPONENT_INPUTS["I2"]["n"]
    out = {}
    for profile in ("S1", "S2", "S3", "S4"):
        row = census[profile]
        clusters = n_i3 * row["applicable_i3_contrast_count"]
        base_items = n_i1a * (1 if row["I1a_cells"] else 0)
        base_items += n_i1b * (1 if row["I1b_cells"] else 0)
        base_items += n_i2 * I2_OPERATION_FAMILIES
        cluster_rows = clusters * I3_VARIANTS_PER_CLUSTER
        per_role = base_items + cluster_rows
        out[profile] = {
            "base_item_contrast_clusters": clusters,
            "base_items": base_items,
            "cluster_rendered_rows": cluster_rows,
            "rendered_rows_per_target_role": per_role,
            "rendered_rows_all_target_roles": per_role * TARGET_ROLES,
        }
    return out


def recompute_wrapper_multiplicity(census: dict, arms: int) -> dict:
    """Wrapper joint adequacy requires both arms to meet the competence floor."""
    m_max_single = census["m_max_recomputed"]
    m_max_wrapped = m_max_single * arms
    single = recompute_power_architecture(m_max_single)
    wrapped = recompute_power_architecture(m_max_wrapped)
    target = rat(wrapped["per_cell_power_target_exact_rational"])
    return {
        "registered_wrapper_arms": arms,
        "m_max_without_wrapper_factor": m_max_single,
        "m_max_with_wrapper_factor": m_max_wrapped,
        "per_cell_power_target_without_wrapper_factor":
            single["per_cell_power_target_exact_rational"],
        "per_cell_power_target_with_wrapper_factor":
            wrapped["per_cell_power_target_exact_rational"],
        "minimal_sizes_with_wrapper_factor": recompute_minimal_sizes(target),
    }


# ---------------------------------------------------------------------------
# 4. Comparison against the committed artifacts.
# ---------------------------------------------------------------------------


def compare(protocol: dict, tables: dict) -> dict:
    battery = protocol["competence_floor_battery_v0_7"]
    constants = protocol["numerical_closure_v0_7"]["derived_constants"]
    mismatches = []
    agreements = []

    for name, row in tables["components"].items():
        for stage in ("development", "confirmation"):
            committed = battery["%s_components" % stage][name]
            mine = row[stage]
            for key in ("n", "pass_count", "exact_null_tail_at_p0",
                        "exact_power_at_p1"):
                theirs = committed[key] if key != "n" else committed["n"]
                ours = row["n"] if key == "n" else mine[key]
                record = {"where": "competence_floor_battery_v0_7.%s_components.%s.%s"
                                   % (stage, name, key),
                          "committed": theirs, "independent": ours}
                (agreements if theirs == ours else mismatches).append(record)
            record = {"where": "competence_floor_battery_v0_7.%s_components.%s."
                               "pass_count_is_minimal_at_alpha" % (stage, name),
                      "committed": committed["pass_count_is_minimal_at_alpha"],
                      "independent": mine["pass_count_is_minimal_at_alpha"]}
            (agreements if record["committed"] == record["independent"]
             else mismatches).append(record)

    census = tables["census"]
    committed_census = battery["gate_bearing_cell_counts"]
    for profile in ("S1", "S2", "S3", "S4"):
        for key in ("applicable_i3_contrast_count", "I3_cells", "I3_K5_cells",
                    "I3_K6_cells", "cells_at_i1_i3_floor",
                    "total_gate_bearing_cells"):
            record = {"where": "competence_floor_battery_v0_7."
                               "gate_bearing_cell_counts.%s.%s" % (profile, key),
                      "committed": committed_census[profile][key],
                      "independent": census[profile][key]}
            (agreements if record["committed"] == record["independent"]
             else mismatches).append(record)

    record = {"where": "power_architecture_v0_4.cell_counts.m_max",
              "committed": protocol["power_architecture_v0_4"]["cell_counts"]["m_max"],
              "independent": census["m_max_recomputed"]}
    (agreements if record["committed"] == record["independent"]
     else mismatches).append(record)

    power = tables["power_architecture"]
    committed_power = protocol["power_architecture_v0_4"]["type_ii_allocation"]
    for key in ("per_cell_false_negative_budget_exact_rational",
                "per_cell_power_target_exact_rational",
                "profile_stage_power_floor_exact_rational",
                "study_end_to_end_power_floor_exact_rational"):
        record = {"where": "power_architecture_v0_4.type_ii_allocation.%s" % key,
                  "committed": committed_power[key], "independent": power[key]}
        (agreements if record["committed"] == record["independent"]
         else mismatches).append(record)

    gaps = tables["derived_gaps"]
    for key in ("registered_alternative_gap_exact_rational",
                "restricted_chance_level_exact_rational",
                "negative_control_equivalence_upper_bound_exact_rational",
                "wrapper_descriptive_bandwidth_exact_rational"):
        record = {"where": "numerical_closure_v0_7.derived_constants.%s" % key,
                  "committed": constants[key], "independent": gaps[key]}
        (agreements if record["committed"] == record["independent"]
         else mismatches).append(record)

    ceiling = protocol["generated_cot_ceiling_v0_7"]["frozen"]
    mine = tables["cot_ceiling"]
    for committed_key, mine_key in (("n", "n"),
                                    ("pass_count", "recomputed_pass_count"),
                                    ("theta_exact_rational", "theta_exact_rational"),
                                    ("p1_exact_rational", "p1_exact_rational"),
                                    ("alpha_exact_rational", "alpha_exact_rational")):
        record = {"where": "generated_cot_ceiling_v0_7.frozen.%s" % committed_key,
                  "committed": ceiling[committed_key],
                  "independent": mine[mine_key]}
        (agreements if str(record["committed"]) == str(record["independent"])
         else mismatches).append(record)

    projection = tables["projection"]
    committed_projection = protocol["operation_boundaries"][
        "projected_future_operations"]["work_streams"]["target_role_development"][
            "by_profile"]
    projection_keys = {"S1": "S1", "S2": "S2", "S3": "S3_if_independently_rendered"}
    for profile, committed_name in projection_keys.items():
        committed_row = committed_projection[committed_name]
        for key in ("base_item_contrast_clusters", "base_items",
                    "cluster_rendered_rows"):
            record = {"where": "operation_boundaries.projected_future_operations."
                               "work_streams.target_role_development.by_profile."
                               "%s.%s" % (committed_name, key),
                      "committed": committed_row[key],
                      "independent": projection[profile][key]}
            (agreements if record["committed"] == record["independent"]
             else mismatches).append(record)
        record = {"where": "operation_boundaries.projected_future_operations."
                           "work_streams.target_role_development.by_profile."
                           "%s.rendered_rows_per_target_role" % committed_name,
                  "committed": committed_row["rendered_rows_per_target_role"],
                  "independent": projection[profile]["rendered_rows_per_target_role"]}
        (agreements if record["committed"] == record["independent"]
         else mismatches).append(record)

    return {"agreement_count": len(agreements),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches}


def cross_field_probes(protocol: dict, registry_v0_7: dict, registry_v0_6: dict,
                       pointer: dict) -> dict:
    """Decision-bearing cross-field probes that need no arithmetic."""
    gate_hierarchy = {g["gate_id"]: g for g in protocol["gate_hierarchy"]}
    i3 = gate_hierarchy["I3"]
    truth_rows = {r["profile"]: r for r in protocol["gate_truth_table"]["rows"]}
    v0_6_counts = registry_v0_6["applicability_table"][
        "per_profile_applicable_contrast_counts"]

    k6 = {}
    for profile in ("S1", "S2", "S3", "S4"):
        truth_applicable = sorted(
            k for k, v in truth_rows[profile]["I3_K6"].items() if v == "applicable")
        ceiling_cells = [c for c in
                         i3["claim_ceiling_by_profile"][profile]["applicable_cells"]
                         if c.startswith("K6")]
        census_ids = [c for c in protocol["competence_floor_battery_v0_7"][
            "gate_bearing_cell_counts"][profile]["applicable_i3_contrast_ids"]
            if c.startswith("K6")]
        k6[profile] = {
            "gate_truth_table": truth_applicable,
            "gate_hierarchy_claim_ceiling": sorted(ceiling_cells),
            "competence_floor_battery_census": sorted(census_ids),
            "rendering_registry_v0_6_applicable_contrast_count":
                v0_6_counts[profile],
            "consistent": (truth_applicable == sorted(ceiling_cells)
                           == sorted(census_ids)),
        }

    normative_sources = {
        "protocol_placement_sole_top_level_normative_protocol":
            protocol["protocol_placement_v0_7"]["sole_top_level_normative_protocol"],
        "status_authoritative_artifact_names_legacy_json":
            "interface_calibration_protocol_draft.json"
            in protocol["status"]["authoritative_artifact"],
        "pointer_must_not_load_legacy_json":
            pointer["loader_contract"][
                "must_not_load_interface_calibration_protocol_draft_json"],
        "pointer_active_bundle_paths":
            sorted(v["path"] for v in pointer["active_bundle"].values()),
        "v0_7_registry_declares_v0_6_normative":
            registry_v0_7["inherited_v0_6_scoring_boundary"]["source"]["path"],
        "v0_6_registry_in_active_bundle":
            registry_v0_7["inherited_v0_6_scoring_boundary"]["source"]["path"]
            in sorted(v["path"] for v in pointer["active_bundle"].values()),
        "v0_6_registry_binding_status": registry_v0_6["binding_status"][:64],
        "v0_6_registry_governs": registry_v0_6["governs"],
        "provenance_self_contained": protocol["provenance_v0_7"]["self_contained"],
        "provenance_v0_6_role": [d["role"] for d in
                                 protocol["provenance_v0_7"]["derived_from"]
                                 if "v0.6" in d["role"]],
        "placement_says_v0_6_is_provenance_only":
            protocol["protocol_placement_v0_7"][
                "legacy_and_v0_6_are_provenance_inputs_not_runtime_overlays"],
    }

    state_ids = [s["id"] for s in protocol["state_machine_v0_4"]["states"]]
    v0_7_gate_keys = ["engineering_shakedown_authority_v0_7",
                      "generated_cot_ceiling_v0_7",
                      "e0_answer_and_decoding_contract",
                      "full_context_tokenization_and_d0_diagnostics",
                      "q0_and_rp_b_v0_7",
                      "rp_b_and_rp_m_separation_v0_7",
                      "wrapper_matched_contrast_v0_7",
                      "negative_control_equivalence_v0_7",
                      "activation_and_causal_claim_boundary_v0_7"]
    state_machine = {
        "registered_state_ids": state_ids,
        "declares_total": protocol["state_machine_v0_4"]["total"],
        "declares_exactly_one_legal_next_state_per_event":
            protocol["state_machine_v0_4"]["exactly_one_legal_next_state_per_event"],
        "v0_7_blocks_absent_from_the_state_machine": v0_7_gate_keys,
        "legacy_q0_instrument_rule":
            protocol["state_machine_v0_4"]["states"][0]["rule"],
        "v0_7_q0_meaning": "positive-reference RP-B prequalification ladder",
        "q0_name_collision": state_ids[0] == "Q0_INSTRUMENT",
    }

    work_streams = sorted(protocol["operation_boundaries"][
        "projected_future_operations"]["work_streams"])
    projection_coverage = {
        "registered_work_streams": work_streams,
        "wrapper_stream_present": any("wrapper" in w for w in work_streams),
        "e0_stream_present": any(w.lower().startswith("e0") for w in work_streams),
        "cot_ceiling_stream_present": any("cot" in w.lower() for w in work_streams),
        "rp_b_q0_stream_present": any("q0" in w.lower() or "rp_b" in w.lower()
                                      for w in work_streams),
        "negative_control_stream_present": any("negative" in w.lower()
                                               for w in work_streams),
        "cell_factors": protocol["atomic_evaluation_cells"]["cell_factors"],
        "wrapper_is_a_registered_cell_factor":
            any("wrapper" in f for f in
                protocol["atomic_evaluation_cells"]["cell_factors"]),
    }

    manifest = protocol["recursive_manifest_seal_v0_7"]
    globs = manifest["inclusion_path_globs"]
    manifest_probe = {
        "inclusion_path_globs": globs,
        "conceptual_inclusion_nouns": manifest["inclusion"],
        "declares_covers_all_decision_bearing_bytes":
            manifest["covers_all_decision_bearing_bytes"],
        "declares_manifest_generator_included":
            manifest["manifest_generation_script_is_included_and_hashed"],
        "named_manifest_generator_path": None,
        "current_pointer_covered_by_a_glob": False,
        "v0_6_registry_covered_by_a_glob": False,
        "unmapped_conceptual_nouns": [
            n for n in manifest["inclusion"]
            if n in ("image digest", "immutable checkpoint revisions",
                     "tokenizer files", "task banks", "readout and parser code",
                     "decoding configuration")],
    }

    ladder = protocol["q0_and_rp_b_v0_7"]["ladder"]
    protocol_text = json.dumps(protocol, ensure_ascii=True)
    od2 = [d for d in protocol["unresolved_operator_decisions"]
           if d["id"] == "OD2"][0]
    od2_probe = {
        "blocking_decisions": protocol["blocking_decisions"],
        "od2_status": od2["status"],
        "od2_blocking": od2["blocking"],
        "od2_blocks": od2["blocks"],
        "ladder_blocked_on": ladder["blocked_on"],
        "ladder_priority": ladder["priority"],
        "ladder_length_deferred_to": ladder["length_L_deferred_to"],
        "candidate_universe_enumerated": False,
        "observation_date_or_source_frozen": "observation date" in protocol_text,
        "predeclared_qwen_size_ladder_has_a_referent":
            "qwen-family size ladder" in protocol_text.lower()
            and protocol_text.lower().count("qwen-family size ladder") > 1,
        "candidate_families_are_generic": [
            c["family"] for c in protocol["positive_reference_candidates"][
                "candidate_families_for_operator_consideration"]],
        "numerical_closure_operator_discretion_clause_count":
            protocol["numerical_closure_v0_7"]["operator_discretion_clause_count"],
    }

    wrapper_probe = {
        "registered_wrapper_fields": sorted(
            set().union(*[set(w) for w in registry_v0_7["wrappers"]])),
        "required_by_review_authority": [
            "message roles and ordering", "literal system/user/assistant content",
            "separators and newlines", "BOS/EOS handling",
            "generation prompt behavior",
            "chat-template revision or exact template bytes",
            "RL few-shot demonstrations, ordering and answer cue",
            "the exact field allowed to differ inside each within-role pair"],
        "registry_bytes": REGISTRY_V0_7.stat().st_size,
        "chat_template_bytes_registered": False,
        "few_shot_demonstrations_registered": False,
        "within_role_pair_differing_field_registered": False,
    }

    e0_probe = {
        "universal_two_token_claim": protocol["e0_answer_and_decoding_contract"][
            "eos_and_stop_semantics"]["derivation"],
        "max_new_tokens": protocol["e0_answer_and_decoding_contract"][
            "eos_and_stop_semantics"]["max_new_tokens"],
        "token_ids_deferred_to": protocol["e0_answer_and_decoding_contract"][
            "complete_token_id_sequence_per_surface_and_revision"]["deferred_to"],
        "isomorphic_stratum_failure_handling": protocol[
            "checkpoint_functional_equivalence_v0_7"]["failure_handling"],
        "isomorphic_stratum_has_its_own_surface_contract": False,
        "isomorphic_stratum_declared_ineligible_for_e0_or_rp_b": False,
    }

    negative_control = protocol["negative_control_equivalence_v0_7"]
    negative_control_probe = {
        "registered_fields": sorted(negative_control),
        "independent_unit_registered": "independent_unit" in negative_control,
        "sample_size_registered": any("n" == k or "sample" in k
                                      for k in negative_control),
        "alpha_resolved_to_a_rational": any("alpha" in k
                                            for k in negative_control),
        "confidence_bound_construction_named": any(
            name in json.dumps(negative_control).lower()
            for name in ("clopper", "pearson", "beta quantile")),
        "pass_count_registered": any("pass" in k for k in negative_control),
        "multiplicity_family_registered": any("multiplicity" in k
                                              for k in negative_control),
        "operation_projection_registered": False,
    }

    return {"k6_applicability": k6,
            "normative_sources": normative_sources,
            "state_machine": state_machine,
            "projection_coverage": projection_coverage,
            "recursive_manifest": manifest_probe,
            "od2_and_ladder": od2_probe,
            "wrapper_identifiability": wrapper_probe,
            "e0_tokenizer_contract": e0_probe,
            "negative_control": negative_control_probe}


def build_tables() -> dict:
    protocol = load(PROTOCOL)
    registry_v0_7 = load(REGISTRY_V0_7)
    registry_v0_6 = load(REGISTRY_V0_6)
    pointer = load(POINTER)

    census = recompute_census(protocol)
    m_max = census["m_max_recomputed"]
    power = recompute_power_architecture(m_max)
    per_cell_target = rat(power["per_cell_power_target_exact_rational"])

    tables = {
        "schema_version": "study3-v0-7-independent-methods-recalculation",
        "reviewed_commit": "459d002442641039196ac3880d47a45a3b79a4c8",
        "reviewed_tree": "2c84d55e6a965972e7cd3f69e3b0cded0bddfb04",
        "external_packages_used": [],
        "stdlib_modules_used": ["argparse", "fractions", "json", "math",
                                "pathlib", "sys"],
        "does_not_import": ["studies/study3/analysis/v0_7_protocol_build.py",
                            "studies/study3/analysis/design_statistics.py",
                            "studies/study3/analysis/scoring_boundary_v0_6.py"],
        "components": recompute_components(),
        "minimal_sizes_at_registered_per_cell_target":
            recompute_minimal_sizes(per_cell_target),
        "census": census,
        "power_architecture": power,
        "derived_gaps": recompute_derived_gaps(),
        "cot_ceiling": recompute_cot_ceiling(),
        "projection": recompute_projection(census),
        "wrapper_multiplicity": recompute_wrapper_multiplicity(
            census, len(registry_v0_7["wrapper_arms"])),
    }
    tables["comparison"] = compare(protocol, tables)
    tables["cross_field_probes"] = cross_field_probes(
        protocol, registry_v0_7, registry_v0_6, pointer)
    return tables


def canonical(document: dict) -> str:
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not (args.emit or args.check):
        args.check = True

    tables = build_tables()
    text = canonical(tables)

    if args.emit:
        TABLES.write_text(text, encoding="utf-8", newline="")
        print("STUDY3_V0_7_INDEPENDENT_RECALCULATION_WRITTEN=1")

    if args.check:
        if not TABLES.exists():
            print("STUDY3_V0_7_INDEPENDENT_RECALCULATION_MISSING=1")
            return 1
        on_disk = TABLES.read_text(encoding="utf-8")
        if on_disk != text:
            print("STUDY3_V0_7_INDEPENDENT_RECALCULATION_REPRODUCES=0")
            return 1
        print("STUDY3_V0_7_INDEPENDENT_RECALCULATION_REPRODUCES=1")

    print("STUDY3_V0_7_RECALCULATION_MISMATCH_COUNT=%d"
          % tables["comparison"]["mismatch_count"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
