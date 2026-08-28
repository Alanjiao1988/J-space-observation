import json

ROOT = "studies/study5/qualification-eq2"

# Read only already-committed artifacts. No measurement, no lens is opened.
j = json.load(open(f"{ROOT}/r1/rank_negative.json", encoding="utf-8"))
l = json.load(open(f"{ROOT}/r1b/logitlens_negative.json", encoding="utf-8"))

n = j["pooled_scored_intermediates"]
j_peak = max(p["readrate"] for p in j["pooled_profile"]["1"])
l_peak = max(p["readrate"] for p in l["pooled_profile"]["1"])
j_hits = max(p["hits"] for p in j["pooled_profile"]["1"])
l_hits = max(p["hits"] for p in l["pooled_profile"]["1"])

print("=== addendum 3 arithmetic, gpt2 ===")
print(f"  n                    : {n}")
print(f"  J-lens peak readrate : {j_peak:.6f}  -> peak hits {j_hits}")
print(f"  logit peak readrate  : {l_peak:.6f}  -> peak hits {l_hits}")
print(f"  ratio                : {j_peak / l_peak:.3f}")
print(f"  stated as            : {j_hits} hits vs {l_hits} hits at n~{n}")

print()
print("=== addendum 1, identity share by depth, positive control ===")
d1 = json.load(open(f"{ROOT}/d1/d1_degeneracy.json", encoding="utf-8"))
pos = d1["results"]["positive"]["per_layer"]
for layer in (0, 18, 21, 23, 26):
    p = next(x for x in pos if x["layer"] == layer)
    print(f"  layer {layer:2d}  identity share {p['identity_attributable_share_of_energy']:.3f}"
          f"  alpha {p['best_scaled_identity_alpha']:.4f}")

print()
print("=== addendum 2, was there ever a passing positive control? ===")
oa5 = json.load(open(f"{ROOT}/r1b/oa005_band_determination.json", encoding="utf-8"))
p = oa5["results"]["positive"]
print(f"  positive final band  : {p['final_band']}  length {p['final_band_length']}")
print(f"  usable downstream    : False (R-0 ladder floor is 3)")
print(f"  depth final band     : {oa5['results']['depth']['final_band']}")
