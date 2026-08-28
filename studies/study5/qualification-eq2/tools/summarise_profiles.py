import json

rows = {}
for role in ("positive", "negative", "depth"):
    d = json.load(open(f"studies/study5/qualification-eq2/r1/rank_{role}.json", encoding="utf-8"))
    rows[role] = d

print("role      layers  pooled_n  peak@1   argmax  band")
b = json.load(open("studies/study5/qualification-eq2/r1/band_derivation.json", encoding="utf-8"))
for role in ("positive", "negative", "depth"):
    r = b["results"][role]
    print(f"{role:9} {r['layers_measured']:>6}  {r['pooled_scored_intermediates']:>8}  "
          f"{r['peak_readrate']:.4f}  {str(r['argmax_layer']):>6}  {r['band']}")

print()
print("=== pooled pass@1 readrate per layer ===")
print("layer   positive   negative      depth")
maxlen = max(len(rows[r]["layers"]) for r in rows)
for i in range(maxlen):
    line = f"{i:5d}"
    for role in ("positive", "negative", "depth"):
        prof = rows[role]["pooled_profile"]["1"]
        if i < len(prof):
            line += f"  {prof[i]['readrate']:9.4f}"
        else:
            line += f"  {'-':>9}"
    print(line)

print()
print("=== peak ratios ===")
pp = b["results"]["positive"]["peak_readrate"]
np_ = b["results"]["negative"]["peak_readrate"]
dp = b["results"]["depth"]["peak_readrate"]
print(f"positive/negative = {pp/np_:.2f}x")
print(f"depth/negative    = {dp/np_:.2f}x")
print(f"negative peak hits = {round(np_ * b['results']['negative']['pooled_scored_intermediates'])} of "
      f"{b['results']['negative']['pooled_scored_intermediates']}")

print()
print("=== pass@10 pooled peak, for context ===")
for role in ("positive", "negative", "depth"):
    prof = rows[role]["pooled_profile"]["10"]
    print(f"{role:9} peak@10={max(p['readrate'] for p in prof):.4f}")
