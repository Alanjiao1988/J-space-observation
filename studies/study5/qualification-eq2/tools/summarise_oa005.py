import json

ROOT = "studies/study5/qualification-eq2"
d = json.load(open(f"{ROOT}/r1b/oa005_band_determination.json", encoding="utf-8"))

for role in ("positive", "depth"):
    r = d["results"].get(role)
    if not r or not r.get("condition_ii"):
        print(f"=== {role}: {r['reason'] if r else 'absent'}")
        continue
    print(f"=== {role}")
    print(f"    J-lens peak readrate      : {r['j_peak_readrate']:.6f}")
    print(f"    logit-lens peak readrate  : {r['logit_lens_peak_readrate']:.6f}")
    print(f"    condition (i) band        : {r['condition_i_band']}")
    print(f"    final band                : {r['final_band']}   valid={r['band_valid']}")
    print()
    print("    layer   J_rate   logit_rate   J_lower   logit_upper   (ii) passes")
    for p in r["condition_ii"]["per_layer"]:
        print(f"    {p['layer']:5d}  {p['j_readrate']:7.4f}  {p['logit_readrate']:10.4f}  "
              f"{p['j_lower_bound']:8.5f}  {p['logit_upper_bound']:11.5f}   "
              f"{p['j_significantly_exceeds_logit_lens']}")
    print()

print("=== full per-layer comparison, positive control ===")
j = json.load(open(f"{ROOT}/r1/rank_positive.json", encoding="utf-8"))["pooled_profile"]["1"]
l = json.load(open(f"{ROOT}/r1b/logitlens_positive.json", encoding="utf-8"))["pooled_profile"]["1"]
print("layer   J-lens   logit-lens   ratio")
for a, b in zip(j, l):
    ratio = (a["readrate"] / b["readrate"]) if b["readrate"] > 0 else float("inf")
    if a["readrate"] > 0 or b["readrate"] > 0:
        rs = f"{ratio:6.2f}" if ratio != float("inf") else "   inf"
        print(f"{a['layer']:5d}  {a['readrate']:7.4f}  {b['readrate']:10.4f}  {rs}")

print()
print("=== peak comparison, all three ===")
for role in ("positive", "depth", "negative"):
    try:
        jj = json.load(open(f"{ROOT}/r1/rank_{role}.json", encoding="utf-8"))["pooled_profile"]["1"]
        ll = json.load(open(f"{ROOT}/r1b/logitlens_{role}.json", encoding="utf-8"))["pooled_profile"]["1"]
    except FileNotFoundError:
        continue
    pj = max(p["readrate"] for p in jj)
    pl = max(p["readrate"] for p in ll)
    print(f"{role:9} J-lens peak {pj:.6f}   logit-lens peak {pl:.6f}   ratio {pj/pl if pl else float('inf'):.3f}")
