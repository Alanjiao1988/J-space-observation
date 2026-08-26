"""Restrictive tests for the Study 4F-M1 Mooncake execution substrate.

These tests enforce the operator decisions and governance rules mechanically:
no VM creation, no VM resize or redeployment, exactly one Storage Account, no
unauthorized paid service, protected-byte preservation, manifest integrity,
scheduler dependency rules, no confirmation leakage, no unauthorized scientific
operation, no resource deletion, price-source completeness, secret redaction and
a complete final paid-resource inventory.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

M1 = Path(__file__).resolve().parents[1]
REPO = M1.parents[2]
ANALYSIS = M1 / "analysis"
if str(ANALYSIS) not in sys.path:
    sys.path.insert(0, str(ANALYSIS))

import study4f_m1_scheduler as sched  # noqa: E402

AUTHORITY = (
    REPO
    / "studies/study4f/prompts/"
    "study4f_m1_mooncake_four_a100_execution_authority.md"
)
STATUS = M1 / "STATUS.json"
SCHEMA = M1 / "STATUS.schema.json"
COST = M1 / "cost_inventory.json"
DIFF = M1 / "test_differential.json"
RESULTS = M1 / "cell_results.json"

ORIGINAL_STUDY4F_AUTHORITY_COMMIT = "7d5ff0837d77af9e6df9f49d580ec0e42bdc2729"
PREDECESSOR_COMMIT = "ddf592010cd8788b637a90a998724f7ccdce4383"
M1_AUTHORITY_COMMIT = "1ca457e105b29b73027ad21c6adce9a9e8904682"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# resource decisions
# --------------------------------------------------------------------------


def test_no_vm_was_created_resized_or_redeployed_by_the_execution_phase():
    azure = _load(STATUS)["azure"]
    assert azure["vms_created_by_this_invocation"] == 0
    assert azure["vms_resized"] == 0
    cost = _load(COST)["preservation_confirmation"]
    assert cost["vms_created_by_this_invocation"] == 0
    assert cost["vms_resized_or_redeployed"] == 0


def test_exactly_one_storage_account_was_created():
    assert _load(STATUS)["azure"]["storage_accounts_created"] == 1
    assert _load(COST)["preservation_confirmation"]["storage_accounts_created"] == 1


def test_no_resource_was_deleted_or_deallocated():
    cost = _load(COST)["preservation_confirmation"]
    assert cost["resources_deleted"] == 0
    assert cost["vms_deleted"] == 0
    assert cost["vms_deallocated"] == 0
    assert cost["disks_deleted_or_detached"] == 0
    assert cost["public_ips_released"] == 0
    assert cost["storage_accounts_deleted"] == 0


def test_no_unauthorized_paid_service_was_created():
    forbidden = {
        "Microsoft.ContainerRegistry",
        "Microsoft.KeyVault",
        "Microsoft.Network/bastionHosts",
        "Microsoft.Network/natGateways",
        "Microsoft.Network/vpnGateways",
        "Microsoft.Network/privateEndpoints",
        "Microsoft.Network/azureFirewalls",
        "Microsoft.Network/loadBalancers",
        "Microsoft.OperationalInsights",
        "Microsoft.MachineLearningServices",
    }
    types = {r["type"] for r in _load(COST)["resources"]}
    for banned in forbidden:
        assert not any(t.startswith(banned) for t in types), banned
    assert _load(COST)["preservation_confirmation"][
        "unauthorized_paid_services_created"
    ] == 0


def test_no_lifecycle_or_auto_delete_policy_was_configured():
    assert _load(COST)["preservation_confirmation"][
        "lifecycle_or_auto_delete_policies_configured"
    ] == 0


# --------------------------------------------------------------------------
# governance and protected bytes
# --------------------------------------------------------------------------


def test_the_authority_was_published_alone_as_the_sole_path_in_its_commit():
    paths = [
        line
        for line in _git(
            "show", "--pretty=format:", "--name-only", M1_AUTHORITY_COMMIT
        ).splitlines()
        if line.strip()
    ]
    assert paths == [
        "studies/study4f/prompts/"
        "study4f_m1_mooncake_four_a100_execution_authority.md"
    ]


def test_m1_added_paths_only_inside_its_own_namespace_and_the_authority():
    statuses = {}
    for line in _git(
        "diff", "--name-status", PREDECESSOR_COMMIT, "HEAD"
    ).splitlines():
        if not line.strip():
            continue
        code, path = line.split("\t", 1)
        statuses[path.strip()] = code.strip()
    assert all(code == "A" for code in statuses.values()), statuses
    authority = (
        "studies/study4f/prompts/"
        "study4f_m1_mooncake_four_a100_execution_authority.md"
    )
    allowed_prefix = "studies/study4f/execution-m1/"
    assert all(
        path.startswith(allowed_prefix) or path == authority for path in statuses
    ), sorted(statuses)


def test_the_evidence_ledger_is_untouched_at_ev_0016():
    status = _load(STATUS)["evidence_ledger"]
    assert status["last_row"] == "EV-0016"
    assert status["rows_added_by_study4f_m1"] == 0
    ledger = REPO / "paper/evidence_ledger.csv"
    committed = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{PREDECESSOR_COMMIT}:paper/evidence_ledger.csv"],
        capture_output=True,
        check=True,
    ).stdout
    assert ledger.read_bytes() == committed


def test_no_study3r_study4f_e1_or_q1_byte_was_modified():
    protected = (
        "studies/study3r/",
        "studies/study4f/STATUS.json",
        "studies/study4f/protocol/",
        "studies/study4f/analysis/",
        "studies/study4f/tests/",
        "studies/study4f/execution-e1/",
        "paper/",
    )
    changed = [
        line.split("\t", 1)[1].strip()
        for line in _git("diff", "--name-status", PREDECESSOR_COMMIT, "HEAD").splitlines()
        if line.strip()
    ]
    for path in changed:
        for prefix in protected:
            assert not path.startswith(prefix), f"{path} touches protected {prefix}"


def test_the_history_is_linear_and_merge_free():
    merges = _git("rev-list", "--merges", f"{PREDECESSOR_COMMIT}..HEAD").strip()
    assert merges == ""


# --------------------------------------------------------------------------
# secret redaction
# --------------------------------------------------------------------------


def test_no_secret_or_raw_identifier_is_committed():
    import re

    guid = re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    )
    gpu_uuid = re.compile(r"GPU-[0-9a-f]{8}-[0-9a-f]{4}")
    key_like = re.compile(r"(AccountKey=|sv=20\d\d-\d\d-\d\d&|sig=)")
    for path in sorted(M1.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.resolve() == Path(__file__).resolve():
            # This module necessarily contains the detector patterns themselves.
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not guid.search(text), f"raw GUID in {path.name}"
        assert not gpu_uuid.search(text), f"raw GPU UUID in {path.name}"
        assert not key_like.search(text), f"credential-like string in {path.name}"


def test_identity_is_recorded_only_as_salted_hashes_and_safe_names():
    azure = _load(STATUS)["azure"]
    assert len(azure["subscription_salted_sha256"]) == 64
    assert azure["subscription_last_four"] == "8845"
    assert azure.get("subscription_id_committed", False) is False
    assert azure.get("tenant_id_committed", False) is False


# --------------------------------------------------------------------------
# price-source completeness
# --------------------------------------------------------------------------


def test_every_paid_resource_has_a_price_source_or_a_registered_unavailability():
    for resource in _load(COST)["resources"]:
        price = resource.get("unit_price")
        assert price is not None, resource["safe_name"]
        if price == "CONTRACT_UNIT_PRICE_UNAVAILABLE":
            assert resource.get("billing_meter"), resource["safe_name"]
            assert resource.get("price_source_note"), resource["safe_name"]
        elif price == 0:
            # A free resource class still has to say why it is free.
            assert resource.get("note") or resource.get("price_source"), resource[
                "safe_name"
            ]
        else:
            assert resource.get("price_source"), resource["safe_name"]


def test_global_azure_retail_was_never_used_as_a_mooncake_price():
    resolution = _load(COST)["price_resolution"]
    assert resolution["global_azure_retail_used_as_a_mooncake_price"] is False
    assert resolution["invented_numbers"] == 0


def test_the_price_resolution_order_required_by_the_authority_was_followed():
    resolution = _load(COST)["price_resolution"]
    assert resolution["attempt_order_required_by_authority"][0].startswith(
        "subscription_specific_price_sheet"
    )
    assert "attempt_1_price_sheet" in resolution
    assert "attempt_2_consumption_meter" in resolution
    assert "attempt_3_official_azure_cn_page" in resolution


def test_the_cost_inventory_covers_every_required_category():
    resources = _load(COST)["resources"]
    types = " ".join(r["type"] for r in resources)
    assert "virtualMachines" in types
    assert "disks" in types
    assert "publicIPAddresses" in types
    assert "storageAccounts" in types
    cost = _load(COST)
    assert "egress" in cost
    assert "marketplace_charges" in cost
    assert "totals" in cost


def test_operator_created_resources_are_included_not_just_session_created():
    provenances = {r.get("provenance") for r in _load(COST)["resources"]}
    assert "operator_created" in provenances
    assert "session_created" in provenances


# --------------------------------------------------------------------------
# no unauthorized scientific operation
# --------------------------------------------------------------------------


def test_only_developmental_execution_is_authorized_by_the_seal():
    """The seal unlocks developmental execution and nothing else.

    Before the seal every flag is false. Publishing the seal flips exactly two
    flags -- developmental and model execution -- and every other flag, above
    all confirmation, D0, activation capture, patching and Study 3M, must stay
    false forever.
    """
    flags = _load(STATUS)["authorization_flags"]
    assert flags, "authorization_flags must not be empty"
    unlocked_by_the_seal = {
        "developmental_execution_authorized",
        "model_execution_authorized",
    }
    seal_published = _load(STATUS).get("seal", {}).get("created") is True
    for name, value in flags.items():
        if name in unlocked_by_the_seal:
            assert value is seal_published, name
        else:
            assert value is False, name


def test_the_seal_was_published_before_the_first_study_bank_model_call():
    seal = _load(STATUS)["seal"]
    assert seal["created"] is True
    assert seal["published_before_the_first_study_bank_model_call"] is True
    assert len(seal["seal_sha256"]) == 64


def test_confirmation_d0_activation_and_patching_stay_unauthorized():
    flags = _load(STATUS)["authorization_flags"]
    for name in (
        "confirmation_authorized",
        "d0_authorized",
        "activation_capture_or_patching_authorized",
        "study3m_authorized",
        "quantization_authorized",
        "sharding_authorized",
        "offload_authorized",
        "device_map_auto_authorized",
        "unregistered_model_authorized",
        "threshold_or_estimand_change_authorized",
        "reinterpretation_authorized",
        "evidence_ledger_row_authorized",
        "github_actions_run_authorized",
    ):
        assert flags[name] is False, name


def test_every_j_space_and_generalization_claim_stays_false():
    """A registered terminal state IS a scientific result, so that one flag may
    be true. Every claim about J-space, about the interface, about mechanism and
    about generalization must stay false forever."""
    claims = _load(STATUS)["claim_boundary"]
    assert claims, "claim_boundary must not be empty"
    for name, value in claims.items():
        if name == "is_a_scientific_result":
            continue
        assert value is False, name
    for name in (
        "claims_j_space_exists",
        "claims_j_space_does_not_exist",
        "claims_j_space_is_observable",
        "claims_j_space_is_unobservable",
        "claims_the_interface_is_valid",
        "claims_the_interface_is_invalid",
        "claims_any_result_generalizes",
        "rp_b_confirmed",
    ):
        assert claims.get(name) is False, name


def test_the_result_is_developmental_and_not_confirmatory():
    status = _load(STATUS)
    assert status["claim_boundary"]["rp_b_confirmed"] is False
    assert status["authorization_flags"]["confirmation_authorized"] is False
    assert status["banks"]["confirmation_bank_realized"] is False
    assert status["next_action_rule"]["confirmation_authorized"] is False
    assert status["next_action_rule"]["a_successor_study_is_drafted_here"] is False


def test_the_disclosure_never_claims_evidence_about_j_space():
    results = _load(RESULTS)
    joined = " ".join(results["what_this_does_not_establish"]).lower()
    assert "j-space" in joined
    established = " ".join(results["what_this_establishes"]).lower()
    assert "j-space" not in established


def test_no_d0_activation_or_patching_operation_was_run():
    """Bank realization and checkpoint acquisition are authorized after the
    seal; D0, activation capture, patching and ledger writes never are."""
    counters = _load(STATUS)["zero_operation_counters"]
    for key in (
        "d0_runs",
        "activation_collections",
        "activation_patches",
        "logit_reads",
        "rp_b_selections",
        "evidence_ledger_rows_written",
        "github_actions_runs",
    ):
        assert counters[key] == 0, key


def test_exactly_the_two_registered_development_banks_were_realized():
    counters = _load(STATUS)["zero_operation_counters"]
    assert counters["study_banks_realized"] == 2
    banks = _load(STATUS)["banks"]
    assert banks["confirmation_bank_realized"] is False
    assert banks["cross_bank_disjoint"] is True
    assert banks["all_invariants_pass"] is True
    assert (
        banks["authority_commit_used_for_seeds"]
        == ORIGINAL_STUDY4F_AUTHORITY_COMMIT
    )
    assert banks["uses_the_m1_authority_hash_for_seeds"] is False


def test_the_status_validates_against_its_own_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(_load(STATUS)))
    assert errors == [], [e.message for e in errors[:5]]


# --------------------------------------------------------------------------
# scheduler dependency rules
# --------------------------------------------------------------------------


def test_the_bank_seed_uses_the_original_study4f_authority_hash():
    assert sched.ORIGINAL_STUDY4F_AUTHORITY_COMMIT == ORIGINAL_STUDY4F_AUTHORITY_COMMIT
    assert M1_AUTHORITY_COMMIT != ORIGINAL_STUDY4F_AUTHORITY_COMMIT


def test_the_scheduler_starts_with_only_the_first_candidate_cot_cells():
    batch = sched.plan_next_batch({}, [])
    assert {(c.role, c.depth, c.route) for c in batch} == {
        ("RP_B1", "D2", "COT"),
        ("RP_B1", "D3", "COT"),
    }


def test_e0_is_never_scheduled_before_both_cot_cells_pass():
    done = [sched.Cell("RP_B1", "D2", "COT"), sched.Cell("RP_B1", "D3", "COT")]
    results = {("RP_B1", "D2", "COT"): True, ("RP_B1", "D3", "COT"): False}
    batch = sched.plan_next_batch(results, done)
    assert all(c.route != "E0" for c in batch), batch
    assert {c.role for c in batch} == {"RP_B2"}


def test_e0_is_scheduled_only_after_both_cot_cells_pass():
    done = [sched.Cell("RP_B1", "D2", "COT"), sched.Cell("RP_B1", "D3", "COT")]
    results = {("RP_B1", "D2", "COT"): True, ("RP_B1", "D3", "COT"): True}
    batch = sched.plan_next_batch(results, done)
    assert {(c.role, c.depth, c.route) for c in batch} == {
        ("RP_B1", "D2", "E0"),
        ("RP_B1", "D3", "E0"),
    }


def test_the_ladder_is_never_parallelised_across_candidates():
    batch = sched.plan_next_batch({}, [])
    assert len({c.role for c in batch}) == 1


def test_rt_is_never_scheduled_before_a_candidate_qualifies():
    done = []
    results = {}
    for role in ("RP_B1", "RP_B2", "RP_B3"):
        for depth in ("D2", "D3"):
            done.append(sched.Cell(role, depth, "COT"))
            results[(role, depth, "COT")] = False
    batch = sched.plan_next_batch(results, done)
    assert batch == [], batch


def test_rt_is_scheduled_only_after_a_candidate_qualifies():
    done = []
    results = {}
    for depth in ("D2", "D3"):
        done.append(sched.Cell("RP_B1", depth, "COT"))
        results[("RP_B1", depth, "COT")] = True
        done.append(sched.Cell("RP_B1", depth, "E0"))
        results[("RP_B1", depth, "E0")] = True
    batch = sched.plan_next_batch(results, done)
    assert {(c.role, c.depth, c.route) for c in batch} == {
        ("RT", "D2", "COT"),
        ("RT", "D3", "COT"),
    }


def test_each_cell_binds_to_exactly_one_gpu_worker():
    workers = [sched.Worker(i, f"uuid-{i}") for i in range(4)]
    cell = sched.Cell("RP_B1", "D2", "COT")
    worker = sched.bind_worker(cell, workers)
    assert worker.env()["CUDA_VISIBLE_DEVICES"] == str(worker.index)
    assert worker.env()["CUDA_DEVICE_ORDER"] == "PCI_BUS_ID"
    assert "," not in worker.env()["CUDA_VISIBLE_DEVICES"]


def test_worker_binding_is_deterministic():
    workers = [sched.Worker(i, f"uuid-{i}") for i in range(4)]
    cell = sched.Cell("RP_B2", "D3", "E0")
    assert sched.bind_worker(cell, workers) == sched.bind_worker(cell, workers)


def test_the_journal_is_create_only(tmp_path):
    journal = sched.ItemJournal(tmp_path / "journal.jsonl")
    cell = sched.Cell("RP_B1", "D2", "COT")
    record = {
        "journal_key": sched.ItemJournal.key(cell, "item-1"),
        "outcome": "correct",
    }
    journal.append(record)
    with pytest.raises(sched.SchedulerError):
        journal.append(dict(record, outcome="incorrect"))


def test_the_journal_resumes_without_duplicating_a_completed_item(tmp_path):
    path = tmp_path / "journal.jsonl"
    cell = sched.Cell("RP_B1", "D2", "COT")
    first = sched.ItemJournal(path)
    first.append(
        {"journal_key": sched.ItemJournal.key(cell, "item-1"), "outcome": "correct"}
    )
    resumed = sched.ItemJournal(path)
    assert resumed.completed(cell, "item-1") is not None
    assert len(resumed.cell_records(cell)) == 1


def test_a_cell_pass_decision_requires_a_complete_cell(tmp_path):
    journal = sched.ItemJournal(tmp_path / "journal.jsonl")
    cell = sched.Cell("RP_B1", "D2", "COT")
    journal.append(
        {"journal_key": sched.ItemJournal.key(cell, "item-1"), "outcome": "correct"}
    )
    with pytest.raises(sched.SchedulerError):
        sched.cell_passes(journal, cell)


def test_unparseable_is_counted_as_incorrect_never_dropped(tmp_path):
    journal = sched.ItemJournal(tmp_path / "journal.jsonl")
    cell = sched.Cell("RP_B1", "D2", "COT")
    for index in range(cell.n):
        outcome = "unparseable" if index == 0 else "correct"
        journal.append(
            {
                "journal_key": sched.ItemJournal.key(cell, f"item-{index}"),
                "outcome": outcome,
            }
        )
    assert len(journal.cell_records(cell)) == cell.n
    assert sched.cell_correct_count(journal, cell) == cell.n - 1


def test_the_registered_cell_geometry_is_unchanged():
    assert sched.Cell("RP_B1", "D2", "COT").n == 104
    assert sched.Cell("RP_B1", "D2", "COT").pass_boundary == 90
    assert sched.Cell("RP_B1", "D2", "E0").n == 60
    assert sched.Cell("RP_B1", "D2", "E0").pass_boundary == 41


def test_the_final_state_is_delegated_to_the_published_state_machine():
    results = {}
    for role in ("RP_B1", "RP_B2", "RP_B3"):
        for depth in ("D2", "D3"):
            results[(role, depth, "COT")] = False
    outcome = sched.final_state(results)
    assert isinstance(outcome, dict)


# --------------------------------------------------------------------------
# no confirmation leakage
# --------------------------------------------------------------------------


def test_no_confirmation_bank_is_realized_or_referenced():
    assert set(sched.BANK_FOR_DEPTH.values()) == {
        "D2_DEVELOPMENT_BANK",
        "D3_DEVELOPMENT_BANK",
    }
    assert all("CONFIRMATION" not in v for v in sched.BANK_FOR_DEPTH.values())


def test_confirmation_remains_unauthorized():
    assert _load(STATUS)["authorization_flags"]["confirmation_authorized"] is False


# --------------------------------------------------------------------------
# final inventory completeness
# --------------------------------------------------------------------------


def test_the_final_paid_resource_inventory_reports_continuing_cost():
    totals = _load(COST)["totals"]
    assert "continuing_cost_per_hour_resolved_portion_cny" in totals
    assert "continuing_cost_per_day_resolved_portion_cny" in totals
    assert totals["continuing_cost_warning"]


def test_each_continuing_charge_has_a_stopping_action():
    actions = _load(COST)[
        "actions_that_stop_each_continuing_charge_without_deleting_anything"
    ]
    assert actions
    for action in actions:
        assert action["resource"]
        assert action["action"]
        assert action["authorized_by_this_invocation"] is False


def test_the_test_differential_records_the_baseline_reproduction():
    diff = _load(DIFF)
    assert diff["baseline_reproduction"]["reproduced_exactly"] is True
    assert diff["extra_failure_adjudication"]["is_a_regression_introduced_by_m1"] is False
    assert diff["conclusion"]["hard_blocker_9_triggered"] is False
    assert diff["study4f_namespace_suites"]["repaired"] == 0
    assert diff["study4f_namespace_suites"]["suppressed"] == 0


def test_the_terminal_state_is_a_registered_m1_state():
    status = _load(STATUS)
    registered = {
        "STUDY4F_M1_RESOURCE_ROUTE_QUALIFIED_ACQUISITION_IN_PROGRESS",
        "STUDY4F_M1_SEALED_DEVELOPMENTAL_EXECUTION_IN_PROGRESS",
        "STUDY4F_M1_RESOURCE_ROUTE_UNAVAILABLE",
        "STUDY4F_M1_VISIBLE_GPU_MEMORY_BELOW_REGISTERED_REQUIREMENT",
        "STUDY4F_M1_IMMUTABLE_ACQUISITION_FAILED",
        "STUDY4F_M1_SHAKEDOWN_FAILED_NO_STUDY_BANK_EXECUTION",
        "STUDY4F_M1_EXECUTION_INTERRUPTED_NO_REINTERPRETATION",
        "STUDY4F_M1_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER",
        "STUDY4F_M1_RP_DEV_IDENTIFIED_TARGET_NO_COT_HEADROOM",
        "STUDY4F_M1_RP_DEV_IDENTIFIED_TARGET_E0_NOT_OBSERVED",
        "STUDY4F_M1_BEHAVIORAL_FEASIBILITY_SUPPORTED_AWAITING_SEPARATE_CONFIRMATION",
    }
    assert status["lifecycle_state"] in registered, status["lifecycle_state"]


def test_the_terminal_state_was_produced_by_the_published_state_machine():
    """The verdict must come from the instrument, not from a hand-written value."""
    import study4f_state_machine as machine

    results = {}
    for cell in _load(RESULTS)["cells"]:
        role, depth, route = cell["cell_id"].split("|")
        results[(role, depth, route)] = cell["passes"]
    recomputed = machine.run_study(results)
    recorded = _load(RESULTS)["state_machine_verdict"]
    assert recomputed["state"] == recorded["state"], (
        recomputed["state"],
        recorded["state"],
    )
    assert recomputed["qualified_candidate"] == recorded["qualified_candidate"]
    assert recomputed["rt_authorized"] == recorded["rt_authorized"] is False
    assert _load(STATUS)["lifecycle_state"].replace("STUDY4F_M1_", "") == recorded[
        "state"
    ].replace("STUDY4F_", "")


def test_rt_was_never_run_because_no_candidate_qualified():
    results = _load(RESULTS)
    assert results["state_machine_verdict"]["rt_cells_run"] == 0
    assert results["state_machine_verdict"]["qualified_candidate"] is None
    assert all(not c["cell_id"].startswith("RT|") for c in results["cells"])


def test_every_pass_decision_matches_the_registered_binomial_boundary():
    import study4f_design_statistics as stats

    for cell in _load(RESULTS)["cells"]:
        route = cell["cell_id"].split("|")[2]
        assert cell["passes"] is stats.passes(route, cell["correct"]), cell["cell_id"]
        assert cell["n"] == (104 if route == "COT" else 60), cell["cell_id"]
        assert cell["pass_boundary"] == (90 if route == "COT" else 41)


def test_no_cell_was_repeated_or_reinterpreted_after_its_result_was_seen():
    results = _load(RESULTS)
    contract = results["execution_contract_in_force"]
    assert contract["cells_repeated_because_a_result_was_unfavorable"] == 0
    assert contract["engineering_fixes_after_the_first_study_bank_call"] == 0
    assert contract["hardware_switches_after_the_first_study_bank_call"] == 0
    assert contract["reseals"] == 0
    forensics = results["e0_unparseable_forensics"]
    assert forensics["parser_was_modified"] is False
    assert forensics["answer_surface_was_added"] is False
    assert forensics["prefix_matching_enabled"] is False
    assert forensics["cell_rerun_after_seeing_the_result"] is False


def test_the_item_journal_had_no_duplicate_or_rewritten_entry():
    integrity = _load(RESULTS)["journal_integrity"]
    assert integrity["duplicate_keys"] == 0
    assert integrity["create_only_violations"] == 0
    assert integrity["unique_journal_keys"] == integrity["total_items"]
    assert integrity["distinct_seals"] == 1
    assert integrity["distinct_container_images"] == 1


def test_execution_counters_moved_but_the_prohibited_ones_stayed_at_zero():
    """Sealed execution legitimately moves generation counters. It must never
    move the counters this authority permanently forbids."""
    counters = _load(STATUS)["zero_operation_counters"]
    assert counters["cells_executed"] > 0
    assert counters["forward_passes"] > 0
    for key in (
        "logit_reads",
        "activation_collections",
        "activation_patches",
        "d0_runs",
        "rp_b_selections",
        "evidence_ledger_rows_written",
        "github_actions_runs",
    ):
        assert counters[key] == 0, key


def test_the_oci_archive_is_frozen_and_round_trip_verified():
    oci = _load(M1 / "oci_manifest.json")
    assert oci["base_image_digest"].startswith("pytorch/pytorch@sha256:")
    assert oci["image_id"].startswith("sha256:")
    assert len(oci["archive"]["sha256"]) == 64
    assert len(oci["compressed"]["sha256"]) == 64
    assert oci["compressed"]["embedded_image_altered_by_compression"] is False
    assert oci["round_trip_verification"]["byte_identical"] is True
    assert (
        oci["round_trip_verification"]["downloaded_sha256"]
        == oci["compressed"]["sha256"]
    )
    assert oci["no_acr_was_created"] is True
    assert oci["blob"]["sas_or_key_used"] is False
    assert oci["is_the_image_used_for_every_executed_cell"] is True
    assert oci["distinct_container_images_across_all_864_journalled_items"] == 1


def test_the_oci_manifest_binds_the_same_image_as_the_seal():
    oci = _load(M1 / "oci_manifest.json")
    seal = _load(M1 / "execution_seal.json")
    assert oci["image_id"] == seal["container"]["execution_image_id"]
    assert oci["base_image_digest"] == seal["container"]["base_digest"]
    assert oci["seal_sha256"] == seal["seal_sha256"]
    for key, value in oci["pinned_versions"].items():
        assert seal["container"][key] == value, key


def test_every_checkpoint_byte_is_content_addressed_in_blob():
    index = _load(M1 / "model_blob_index.json")
    manifest = _load(M1 / "acquisition_manifest.json")
    assert index["total_files"] == manifest["total_files"] == 34
    assert index["total_bytes"] == manifest["total_bytes"] == 113881744368
    for name, cp in index["checkpoints"].items():
        assert cp["revision"] == manifest["checkpoints"][name]["revision"]
        for entry in cp["files"]:
            digest = entry["digest"]
            assert len(digest) == 64, entry["path"]
            # the blob name IS the proof of what the blob contains
            assert entry["blob"] == f"models/sha256/{digest[:2]}/{digest}"


def test_the_model_blob_index_covers_every_acquired_file():
    index = _load(M1 / "model_blob_index.json")
    manifest = _load(M1 / "acquisition_manifest.json")
    for name, cp in manifest["checkpoints"].items():
        indexed = {e["path"] for e in index["checkpoints"][name]["files"]}
        acquired = {f["path"] for f in cp["files"]}
        assert indexed == acquired, (name, acquired - indexed)


def test_storage_makes_gpu_deallocation_non_destructive():
    storage = _load(STATUS)["storage"]
    assert storage["models_container_populated"] is True
    assert storage["oci_container_populated"] is True
    assert storage["content_address_round_trip_verified"] is True
    assert storage["oci_archive_round_trip_verified"] is True
    assert storage["deallocating_the_gpu_vm_no_longer_destroys_verified_bytes"] is True
    assert storage["sas_tokens_issued"] == 0
    assert storage["keys_committed"] is False


def test_the_authority_exists_and_forbids_vm_creation():
    text = AUTHORITY.read_text(encoding="utf-8")
    assert "Do not create any virtual machine." in text
    assert "exactly one** new Storage Account" in text or (
        "exactly one" in text and "Storage Account" in text
    )
    assert "STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL" in text
    assert "STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION" in text
