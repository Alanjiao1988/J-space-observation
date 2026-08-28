import json

ROOT = "studies/study5/qualification-eq2"
d = json.load(open(f"{ROOT}/d1/d1_degeneracy.json", encoding="utf-8"))

print("=== decision rule, frozen before measurement ===")
r = d["decision_rule_frozen_before_measurement"]
print(f"  negative-B if median < {r['negative_B_if_median_below']}")
print(f"  negative-A if median >= {r['negative_A_if_median_at_or_above']}")
print(f"  uncorrelated matched-norm reference: {r['uncorrelated_matched_norm_reference']:.4f}")
print()

for role in ("positive", "depth", "negative"):
    res = d["results"][role]
    print(f"=== {role}  d_model={res['d_model']}  layers={res['layers']}")
    print(f"    ||J-I||/||I||  median {res['median_relative_distance_from_identity']:.4f}"
          f"  min {res['min_relative_distance_from_identity']:.4f}"
          f"  max {res['max_relative_distance_from_identity']:.4f}")
    print(f"    identity energy share, median: {res['median_identity_attributable_share']:.6f}")
    print(f"    effective rank, median       : {res['median_effective_rank']:.1f}"
          f" ({100*res['median_effective_rank']/res['d_model']:.1f}% of d_model)")
    print()
    print("    layer  ||J-I||/||I||   alpha    id_share  resid_share  eff_rank  smax/smin")
    for p in res["per_layer"]:
        ratio = p["singular_value_max"] / p["singular_value_min"] if p["singular_value_min"] > 0 else float("inf")
        rs = f"{ratio:9.1f}" if ratio != float("inf") else "      inf"
        print(f"    {p['layer']:5d}  {p['relative_distance_from_identity']:12.4f}"
              f"  {p['best_scaled_identity_alpha']:7.4f}"
              f"  {p['identity_attributable_share_of_energy']:9.5f}"
              f"  {p['residual_share_of_energy']:11.5f}"
              f"  {p['effective_rank_participation']:8.1f}"
              f"  {rs}")
    print()

print("=== OD-016 retrospective ===")
o = d["od016_retrospective"]
print(f"  what it was written to catch: {o['what_od016_was_written_to_catch']}")
print(f"  registered interval: [{o['od016_registered_lower_gate']}, {o['od016_registered_upper_fence']}]")
for k, v in o["external_published_final_identity_distance"].items():
    fired = o["would_od016_have_fired_on_these_lenses"][k]
    print(f"    {k:18} value {v:.6f}   would OD-016 fire? {fired}")

print()
print(f"CATEGORY: {d['category']}")
