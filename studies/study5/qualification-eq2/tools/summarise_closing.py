import json

d = json.load(open("studies/study5/qualification-eq2/d1/eq2_closing_snapshot.json", encoding="utf-8"))
print("--- VM power states at EQ2 close ---")
for vm in d["vms"]:
    name = vm["name"]
    label = name if not name.startswith("salted:") else "salted:" + name[7:19] + "..."
    scope = "registered" if vm.get("in_registered_scope") else "TRAINING/other"
    print(f"  {label:34} {vm['power_state']:12} {vm['size']:26} {scope}")
print()
print("control-plane writes :", d["control_plane_writes"])
print("data-plane writes    :", d["data_plane_writes"])
print("SAS tokens issued    :", d["sas_tokens_issued"])
print("storage keys read    :", d["storage_keys_read"])
print("vm count             :", d["vm_count"])
print("nsg count            :", d["network_security_group_count"])
