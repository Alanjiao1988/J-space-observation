import json
from collections import Counter

d = json.load(open("studies/study5/qualification-eq2/r0/control_weights.json", encoding="utf-8"))
print("files            :", d["file_count"])
print("total bytes      :", d["total_bytes"], "=", round(d["total_bytes"] / 1e9, 2), "GB")
print("failures         :", d["failures"])
print("workstation bytes:", d["bytes_fetched_by_operator_workstation"])
print("anchors          :", dict(Counter(f["method"] for f in d["files"])))
for role, m in d["models"].items():
    fs = [f for f in d["files"] if f["role"] == role]
    print(f"  {role:18} {m['repo']:32} rev={m['revision'][:12]}  files={len(fs)}  bytes={sum(x['bytes'] for x in fs)}")
print("all verified     :", all(f["verified"] for f in d["files"]))
