import json

R1 = "studies/study5/qualification-eq2/r1"

print("=== registered OD-015 requirement (carried forward by OA-004) ===")
od015 = json.load(open(f"{R1}/OD-015.json", encoding="utf-8"))
print(" ", od015["band_rule"]["interior_requirement"])

print()
print("=== what band_vs_null.py actually implements ===")
print("  is_mid_depth(band, layers) -> band[0] > layers[0] and band[-1] < layers[-1]")
print("  i.e. the band's EXTENT must not touch either endpoint (stricter, unregistered)")

print()
for role in ("positive", "negative", "depth"):
    d = json.load(open(f"{R1}/band_vs_null_{role}.json", encoding="utf-8"))
    real = json.load(open(f"{R1}/rank_{role}.json", encoding="utf-8"))
    prof = real["pooled_profile"]["1"]
    layers = [p["layer"] for p in prof]
    rates = [p["readrate"] for p in prof]
    peak = max(rates)
    argmax = layers[rates.index(peak)]
    sig = d["significant_layers"]
    run = d["raw_longest_significant_run"]
    argmax_interior = layers[0] < argmax < layers[-1]
    print(f"--- {role} (layers {layers[0]}..{layers[-1]}, trials={d['trials']})")
    print(f"    significant layers      : {sig}")
    print(f"    longest contiguous run  : {run}")
    print(f"    peak readrate           : {peak:.4f} at layer {argmax}")
    print(f"    argmax interior?        : {argmax_interior}   <- REGISTERED rule")
    print(f"    band extent interior?   : {d['mid_depth']}   <- my stricter implementation")
    print(f"    null ceiling (max)      : {max(p['null_ceiling'] for p in d['per_layer']):.6f}")
    print(f"    verdict as implemented  : band_exists={d['band_exists']}")

print()
print("=== per-layer detail, positive control ===")
d = json.load(open(f"{R1}/band_vs_null_positive.json", encoding="utf-8"))
print("layer  readrate  real_lower  null_ceil  significant")
for p in d["per_layer"]:
    if p["layer"] >= 18:
        print(f"{p['layer']:5d}  {p['readrate']:8.4f}  {p['real_lower_bound']:10.6f}  "
              f"{p['null_ceiling']:9.6f}  {p['significant']}")

print()
print("=== negative control: is it clean under BOTH readings? ===")
dn = json.load(open(f"{R1}/band_vs_null_negative.json", encoding="utf-8"))
print(f"  significant layers: {dn['significant_layers']}  -> no band under either reading")
print(f"  max real lower bound: {max(p['real_lower_bound'] for p in dn['per_layer']):.6f}")
print(f"  null ceiling:         {max(p['null_ceiling'] for p in dn['per_layer']):.6f}")
