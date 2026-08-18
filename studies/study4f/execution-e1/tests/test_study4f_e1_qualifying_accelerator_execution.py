"""Study 4F-E1 resource and execution tests.

Authority: ``studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md``

These tests police a successor whose whole job is to change *nothing* about the
instrument it executes. They therefore concentrate on four things:

1. the E1 authority is byte-exact and was published alone, first, on top of the
   registered predecessor;
2. the predecessor instrument binds byte-exactly and every registered semantic
   invariant still holds;
3. the Azure selection rules -- registered SKU order, eligibility, lexicographic
   region ordering, quota versus capacity -- are enforced by code rather than by
   narration, including on adversarial inputs;
4. the registered terminal state is exactly one of the nine, and nothing
   downstream of the stop was reached.

Nothing here constructs a model, acquires a weight, realizes a bank, draws an
execution seed, reads a logit or contacts Azure.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()
E1 = HERE.parents[1]
STUDY4F = E1.parent
ROOT = STUDY4F.parents[1]
ANALYSIS = E1 / "analysis"

PREDECESSOR_COMMIT = "5fd9602df207e95789263d0f8d52428540f48fb8"
E1_AUTHORITY_COMMIT = "58cdcda0ec3848ba2bd3a6c525b3c28ac8955d69"
ORIGINAL_STUDY4F_AUTHORITY_COMMIT = "7d5ff0837d77af9e6df9f49d580ec0e42bdc2729"
STUDY3R_CLOSURE_COMMIT = "ee8a852111d27cb39bf21743e18857485cff1efe"

AUTHORITY = (STUDY4F / "prompts" /
             "study4f_e1_qualifying_accelerator_execution_authority.md")
STATUS_JSON = E1 / "STATUS.json"
STATUS_SCHEMA = E1 / "STATUS.schema.json"
MANIFEST_JSON = E1 / "manifest" / "predecessor_instrument_manifest.json"
INVARIANTS_JSON = E1 / "manifest" / "predecessor_semantic_invariants.json"
DISCOVERY_JSON = E1 / "azure" / "azure_discovery.json"
QUOTA_JSON = E1 / "azure" / "quota_disposition.json"
OPERATOR_PACKET = E1 / "azure" / "operator_quota_request_packet.md"
DISCLOSURE = E1 / "STUDY4F_E1_TERMINAL_DISCLOSURE.md"
README = E1 / "README.md"

#: The nine failure node IDs of the registered repository baseline.
REGISTERED_BASELINE_FAILURES = (
    "tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last",
    "tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix",
    "tests/test_phase1_0d_build_provenance.py::test_the_bundle_digest_ignores_the_checkout_line_endings",
    "tests/test_phase1_0d_generation_launcher_rp_compat.py::test_shim_has_valid_bash_syntax_and_frozen_launcher_remains_in_baseline",
    "tests/test_phase1_0d_protected_bytes.py::test_line_endings_do_not_change_the_rollup",
    "tests/test_phase1_0d_review_image.py::test_v2_refuses_a_rehashed_record_with_moved_metadata",
    "tests/test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only",
    "tests/test_study3_v0_7_focused_review.py::test_the_review_changed_no_reviewed_or_historical_path",
    "tests/test_study3r_protocol_v1.py::test_the_authoring_session_wrote_nothing_outside_the_study3r_namespace",
)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        "study4f_e1_test_" + name, ANALYSIS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


binding = _load("study4f_e1_instrument_binding")
selection = _load("study4f_e1_resource_selection")
preflight = _load("study4f_e1_runtime_preflight")
plan = _load("study4f_e1_deployment_plan")
lifecycle = _load("study4f_e1_lifecycle")


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True,
                          check=True).stdout


def _json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def status():
    return _json(STATUS_JSON)


@pytest.fixture(scope="module")
def manifest():
    return _json(MANIFEST_JSON)


@pytest.fixture(scope="module")
def invariants():
    return _json(INVARIANTS_JSON)


@pytest.fixture(scope="module")
def discovery():
    return _json(DISCOVERY_JSON)


@pytest.fixture(scope="module")
def quota():
    return _json(QUOTA_JSON)


@pytest.fixture(scope="module")
def protocol():
    return _json(STUDY4F / "protocol" / "study4f_protocol_v1.json")


# ---------------------------------------------------------------------------
# 1. Authority identity and alone-first ordering
# ---------------------------------------------------------------------------


def test_the_e1_authority_bytes_match_the_recorded_identity(status):
    payload = AUTHORITY.read_bytes()
    import hashlib
    recorded = status["authority"]
    assert len(payload) == recorded["bytes"]
    assert hashlib.sha256(payload).hexdigest() == recorded["sha256"]
    assert _git("hash-object", str(AUTHORITY)).strip() == recorded["git_blob"]


def test_the_e1_authority_was_published_alone_as_the_first_successor_commit(status):
    commit = status["authority"]["commit"]
    assert commit == E1_AUTHORITY_COMMIT
    listed = [line.strip() for line
              in _git("show", "--name-only", "--format=", commit).splitlines()
              if line.strip()]
    assert listed == [
        "studies/study4f/prompts/"
        "study4f_e1_qualifying_accelerator_execution_authority.md"]
    parents = _git("show", "-s", "--format=%P", commit).split()
    assert parents == [PREDECESSOR_COMMIT]
    assert status["authority"]["parent_commit"] == PREDECESSOR_COMMIT
    assert status["authority"]["published_alone_as_the_first_commit_after_the_predecessor"] \
        is True


def test_no_e1_artifact_predates_the_authority_commit():
    """Section 1: nothing existed under the successor namespace before it."""
    listed = [line.strip() for line
              in _git("ls-tree", "-r", "--name-only", E1_AUTHORITY_COMMIT,
                      "studies/study4f/execution-e1").splitlines()
              if line.strip()]
    assert listed == []


def test_the_history_is_strictly_linear_and_merge_free():
    merges = [line for line
              in _git("rev-list", "--merges",
                      "%s..HEAD" % PREDECESSOR_COMMIT).splitlines()
              if line.strip()]
    assert merges == []
    assert _git("merge-base", E1_AUTHORITY_COMMIT, "HEAD").strip() == \
        E1_AUTHORITY_COMMIT


def test_the_authority_file_is_the_one_this_successor_executed():
    text = AUTHORITY.read_text(encoding="utf-8")
    assert "Study 4F-E1 — Qualifying Accelerator Execution" in text
    assert PREDECESSOR_COMMIT in text
    assert "STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE" in text
    for state in lifecycle.REGISTERED_TERMINAL_STATES:
        assert state in text, state


# ---------------------------------------------------------------------------
# 2. Byte-exact instrument binding
# ---------------------------------------------------------------------------


def test_every_decision_bearing_file_binds_byte_exactly(manifest):
    assert manifest["predecessor_commit"] == PREDECESSOR_COMMIT
    assert manifest["file_count"] == len(binding.DECISION_BEARING_FILES) == 15
    assert manifest["all_files_agree"] is True
    assert binding.mismatched_paths(manifest) == []


def test_the_manifest_recomputes_from_the_repository_now(manifest):
    rebuilt = binding.build_manifest(ROOT)
    assert rebuilt["all_files_agree"] is True
    recorded = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
    fresh = {entry["path"]: entry["sha256"] for entry in rebuilt["files"]}
    assert recorded == fresh


def test_the_manifest_covers_every_named_decision_bearing_surface(manifest):
    paths = {entry["path"] for entry in manifest["files"]}
    for required in (
        "studies/study4f/protocol/study4f_protocol_v1.json",
        "studies/study4f/protocol/study4f_protocol_v1.schema.json",
        "studies/study4f/analysis/study4f_task_banks.py",
        "studies/study4f/analysis/study4f_interfaces.py",
        "studies/study4f/analysis/study4f_design_statistics.py",
        "studies/study4f/analysis/study4f_state_machine.py",
        "studies/study4f/analysis/study4f_validation.py",
        "studies/study4f/analysis/study4f_resource_route.py",
        "studies/study4f/shakedown/study4f_shakedown_disposition.json",
        "studies/study4f/tests/test_study4f_behavioral_feasibility.py",
    ):
        assert required in paths, required


def test_a_single_changed_byte_refutes_the_binding(manifest):
    corrupted = json.loads(json.dumps(manifest))
    corrupted["files"][0]["recompute_agrees"] = False
    verdict = binding.verify_manifest(corrupted)
    assert verdict["bound"] is False
    assert verdict["state"] == binding.BINDING_FAILED_STATE
    with pytest.raises(binding.Study4FE1InstrumentBindingError):
        binding.require_binding(corrupted)


def test_a_failing_semantic_invariant_refutes_the_binding(manifest, invariants):
    broken = json.loads(json.dumps(invariants["checks"]))
    broken[0]["holds"] = False
    verdict = binding.verify_manifest(manifest, broken)
    assert verdict["bound"] is False
    assert verdict["failing_invariants"] == [broken[0]["invariant"]]


def test_every_registered_semantic_invariant_was_reconfirmed(invariants):
    observed = {record["invariant"]: record["holds"]
                for record in invariants["checks"]}
    assert set(binding.REQUIRED_SEMANTIC_INVARIANTS) <= set(observed)
    assert all(observed.values()), [k for k, v in observed.items() if not v]
    assert invariants["reconfirmed_without_modification"] is True


def test_the_bound_instrument_still_carries_the_registered_design(protocol):
    assert protocol["statistics"]["m_max"] == 16
    assert protocol["statistics"]["alpha_per_cell"] == "1/320"
    assert protocol["statistics"]["cells"]["COT"]["n"] == 104
    assert protocol["statistics"]["cells"]["COT"]["pass_boundary"] == 90
    assert protocol["statistics"]["cells"]["E0"]["n"] == 60
    assert protocol["statistics"]["cells"]["E0"]["pass_boundary"] == 41
    assert protocol["statistics"]["depths_may_be_pooled"] is False
    assert protocol["ladder_order"] == ["RP_B1", "RP_B2", "RP_B3"]
    assert [entry["size"] for entry in protocol["banks"]["registered"]] == [104, 104]
    assert protocol["banks"]["seed_derivation"]["authority_commit"] == \
        ORIGINAL_STUDY4F_AUTHORITY_COMMIT


def test_the_bank_seed_never_derives_from_the_e1_authority(manifest):
    """Section 8.6: banks use the *original* authority hash, not E1's."""
    spec = importlib.util.spec_from_file_location(
        "study4f_e1_test_banks",
        STUDY4F / "analysis" / "study4f_task_banks.py")
    banks = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = banks
    spec.loader.exec_module(banks)
    original = banks.bank_seed_material(ORIGINAL_STUDY4F_AUTHORITY_COMMIT,
                                        "D2_DEVELOPMENT_BANK")
    e1 = banks.bank_seed_material(E1_AUTHORITY_COMMIT, "D2_DEVELOPMENT_BANK")
    assert original != e1
    assert ORIGINAL_STUDY4F_AUTHORITY_COMMIT in original
    assert E1_AUTHORITY_COMMIT not in original


# ---------------------------------------------------------------------------
# 3. Registered accelerator selection
# ---------------------------------------------------------------------------


def test_exactly_two_skus_are_registered_and_h100_is_first():
    assert len(selection.REGISTERED_SKUS) == 2
    first, second = selection.REGISTERED_SKUS
    assert first["sku"] == "Standard_NC40ads_H100_v5"
    assert first["gpu_count"] == 1 and first["vcpus"] == 40
    assert first["nominal_gpu_memory_gb"] == 94
    assert second["sku"] == "Standard_NC24ads_A100_v4"
    assert second["gpu_count"] == 1 and second["vcpus"] == 24
    assert second["nominal_gpu_memory_gb"] == 80
    assert first["order"] < second["order"]


@pytest.mark.parametrize("sku", [
    "Standard_NC4as_T4_v3", "Standard_NV6ads_A10_v5", "Standard_NC6s_v3",
    "Standard_ND96asr_v4", "Standard_NCC40ads_H100_v5",
])
def test_no_ineligible_accelerator_can_be_selected(sku):
    with pytest.raises(selection.Study4FE1SelectionError):
        selection.sku_record(sku)


def test_the_prohibited_substitutions_are_registered():
    for prohibited in ("T4", "A10", "V100", "multi_gpu_nd_series", "spot_vm",
                       "confidential_gpu"):
        assert prohibited in selection.PROHIBITED_SUBSTITUTIONS


def _offer(sku, region, *, family_limit=0, family_used=0, total_limit=100,
           total_used=0, restrictions=(), permitted=True, returned=True):
    return {
        "sku": sku, "region": region,
        "returned_for_sku": returned,
        "permitted_by_subscription_and_policy": permitted,
        "restrictions": list(restrictions),
        "family_vcpu_limit": family_limit, "family_vcpu_used": family_used,
        "total_regional_vcpu_limit": total_limit,
        "total_regional_vcpu_used": total_used,
    }


def test_regions_are_ordered_lexicographically_before_any_deployment_result():
    offers = [
        _offer("Standard_NC40ads_H100_v5", "WestUS3", family_limit=40),
        _offer("Standard_NC40ads_H100_v5", "eastus2", family_limit=40),
        _offer("Standard_NC40ads_H100_v5", "CanadaCentral", family_limit=40),
        _offer("Standard_NC40ads_H100_v5", "australiaeast", family_limit=40),
    ]
    assert selection.eligible_regions(offers, "Standard_NC40ads_H100_v5") == \
        ["australiaeast", "CanadaCentral", "eastus2", "WestUS3"]


def test_a_not_available_for_subscription_region_is_never_eligible():
    offers = [_offer("Standard_NC40ads_H100_v5", "eastus2", family_limit=40,
                     restrictions=["NotAvailableForSubscription"])]
    assert selection.eligible_regions(offers, "Standard_NC40ads_H100_v5") == []


def test_a_region_the_subscription_cannot_use_is_never_eligible():
    offers = [_offer("Standard_NC40ads_H100_v5", "CentralUSEUAP",
                     family_limit=40, permitted=False)]
    assert selection.eligible_regions(offers, "Standard_NC40ads_H100_v5") == []
    assert selection.eligible_regions(offers, "Standard_NC40ads_H100_v5",
                                      require_quota=False) == []


def test_family_and_total_regional_quota_must_both_admit_one_instance():
    enough = _offer("Standard_NC40ads_H100_v5", "eastus2", family_limit=40)
    assert selection.has_sufficient_quota(enough, 40) is True
    short_family = _offer("Standard_NC40ads_H100_v5", "eastus2", family_limit=24)
    assert selection.has_sufficient_quota(short_family, 40) is False
    short_total = _offer("Standard_NC40ads_H100_v5", "eastus2",
                         family_limit=40, total_limit=40, total_used=8)
    assert selection.has_sufficient_quota(short_total, 40) is False
    consumed = _offer("Standard_NC40ads_H100_v5", "eastus2",
                      family_limit=40, family_used=8)
    assert selection.has_sufficient_quota(consumed, 40) is False


def test_h100_is_attempted_before_a100_across_the_whole_order():
    offers = [
        _offer("Standard_NC24ads_A100_v4", "australiaeast", family_limit=24),
        _offer("Standard_NC40ads_H100_v5", "westus3", family_limit=40),
    ]
    order = selection.registered_attempt_order(offers)
    assert [entry["sku"] for entry in order] == [
        "Standard_NC40ads_H100_v5", "Standard_NC24ads_A100_v4"]


def test_at_most_four_on_demand_attempts_are_permitted():
    offers = [_offer("Standard_NC40ads_H100_v5", "region%d" % index,
                     family_limit=40) for index in range(9)]
    verdict = selection.select(offers)
    assert verdict["branch"] == "quota_exists"
    assert len(verdict["attempt_order"]) == selection.MAX_DEPLOYMENT_ATTEMPTS == 4
    assert len(verdict["full_registered_order"]) == 9


def test_no_quota_anywhere_routes_to_the_quota_branch_without_provisioning():
    offers = [_offer("Standard_NC40ads_H100_v5", "eastus2"),
              _offer("Standard_NC24ads_A100_v4", "eastus2")]
    verdict = selection.select(offers)
    assert verdict["branch"] == "no_sufficient_quota"
    assert verdict["attempt_order"] == []
    assert verdict["capacity_observed"] is False
    assert verdict["state"] == "STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL"


def test_the_quota_request_is_minimal_and_never_larger():
    offers = [_offer("Standard_NC40ads_H100_v5", "eastus2"),
              _offer("Standard_NC40ads_H100_v5", "australiaeast")]
    verdict = selection.select(offers)
    request = selection.quota_request(verdict["quota_request_target"])
    assert request["sku"] == "Standard_NC40ads_H100_v5"
    assert request["region"] == "australiaeast"
    assert request["requested_family_vcpus"] == 40
    assert request["instances_requested"] == 1
    assert request["larger_request_prohibited"] is True


def test_the_a100_quota_request_is_twenty_four_vcpus():
    offers = [_offer("Standard_NC24ads_A100_v4", "brazilsouth")]
    verdict = selection.select(offers)
    request = selection.quota_request(verdict["quota_request_target"])
    assert request["requested_family_vcpus"] == 24


def test_a_failed_attempt_records_its_kind_and_proves_no_model_ran():
    record = selection.record_failed_attempt(
        "Standard_NC40ads_H100_v5", "eastus2", "1", "ZonalAllocationFailed",
        "capacity")
    assert record["failure_kind"] == "capacity"
    assert record["spot_used"] is False
    assert record["model_operation_occurred"] is False
    assert record["weights_acquired"] == 0 and record["model_calls"] == 0
    with pytest.raises(selection.Study4FE1SelectionError):
        selection.record_failed_attempt("Standard_NC40ads_H100_v5", "eastus2",
                                        None, "Whatever", "inconvenient")


def test_freezing_forbids_a_later_sku_or_region_switch():
    frozen = selection.freeze("Standard_NC40ads_H100_v5", "eastus2", "1")
    assert frozen["frozen_before_any_model_output"] is True
    assert frozen["sku_switch_permitted_after_first_study_bank_call"] is False
    assert frozen["region_switch_permitted_after_first_study_bank_call"] is False


# ---------------------------------------------------------------------------
# 4. Runtime preflight on a measured device
# ---------------------------------------------------------------------------


def test_the_memory_requirement_is_the_predecessors_own_number():
    assert preflight.registered_requirement(ROOT) == \
        preflight.REQUIRED_FREE_DEVICE_MEMORY_BYTES == 69_502_926_848


def test_the_runtime_contract_is_the_original_contract(protocol):
    verdict = preflight.contract_matches_protocol(protocol)
    assert verdict["identical"] is True, verdict["differences"]
    for field in ("cpu_offload", "disk_offload", "device_map_auto",
                  "model_sharding", "trust_remote_code"):
        assert preflight.RUNTIME_CONTRACT[field] is False
    assert preflight.RUNTIME_CONTRACT["torch_dtype"] == "bfloat16"
    assert preflight.RUNTIME_CONTRACT["unquantized_weights"] is True
    assert preflight.RUNTIME_CONTRACT["batch_size"] == 1


def _observation(free_bytes, *, name="NVIDIA H100 NVL", devices=1,
                 processes=(), bf16=True, compatibility=None):
    return {
        "devices": [{"name": name,
                     "free_device_memory_bytes": free_bytes,
                     "memory_is_measured": True,
                     "bf16_supported": bf16}] * devices,
        "processes": list(processes),
        "compatibility": compatibility if compatibility is not None
        else {"driver": True, "cuda": True, "framework": True},
    }


def test_a_qualifying_measured_device_passes():
    verdict = preflight.evaluate(
        _observation(85_000_000_000), "Standard_NC40ads_H100_v5")
    assert verdict["passed"] is True
    assert verdict["failed_checks"] == []
    assert verdict["state"] is None


def test_measured_memory_below_the_requirement_stops_without_quantizing():
    verdict = preflight.evaluate(
        _observation(69_502_926_848), "Standard_NC40ads_H100_v5")
    assert verdict["passed"] is False
    assert verdict["state"] == \
        "STUDY4F_E1_VISIBLE_GPU_MEMORY_BELOW_REGISTERED_REQUIREMENT"
    assert verdict["quantization_attempted"] is False
    assert verdict["sharding_attempted"] is False
    assert verdict["cpu_or_disk_offload_attempted"] is False
    assert verdict["device_map_auto_used"] is False


def test_a_paper_specification_is_not_accepted_as_evidence():
    observation = _observation(85_000_000_000)
    observation["devices"][0]["memory_is_measured"] = False
    verdict = preflight.evaluate(observation, "Standard_NC40ads_H100_v5")
    assert verdict["passed"] is False
    assert "free_device_memory_is_a_measurement_not_a_specification" in \
        verdict["failed_checks"]
    assert verdict["paper_specification_accepted_as_evidence"] is False


def test_more_than_one_visible_accelerator_fails():
    verdict = preflight.evaluate(
        _observation(85_000_000_000, devices=2), "Standard_NC40ads_H100_v5")
    assert verdict["passed"] is False
    assert "exactly_one_eligible_accelerator_visible" in verdict["failed_checks"]


def test_a_mismatched_gpu_model_fails():
    verdict = preflight.evaluate(
        _observation(85_000_000_000, name="NVIDIA A100 80GB PCIe"),
        "Standard_NC40ads_H100_v5")
    assert verdict["passed"] is False
    assert "gpu_model_matches_the_frozen_sku" in verdict["failed_checks"]


def test_a_material_foreign_process_fails():
    verdict = preflight.evaluate(
        _observation(85_000_000_000,
                     processes=[{"pid": 4242,
                                 "used_memory_bytes": 2 * 1024 ** 3}]),
        "Standard_NC40ads_H100_v5")
    assert verdict["passed"] is False
    assert "no_unrelated_process_occupies_material_gpu_memory" in \
        verdict["failed_checks"]


def test_absent_bf16_or_broken_compatibility_fails():
    assert preflight.evaluate(_observation(85_000_000_000, bf16=False),
                              "Standard_NC40ads_H100_v5")["passed"] is False
    assert preflight.evaluate(
        _observation(85_000_000_000,
                     compatibility={"driver": True, "cuda": False,
                                    "framework": True}),
        "Standard_NC40ads_H100_v5")["passed"] is False
    assert preflight.evaluate(
        _observation(85_000_000_000, compatibility={"driver": True}),
        "Standard_NC40ads_H100_v5")["passed"] is False


# ---------------------------------------------------------------------------
# 5. Dedicated, tagged and explicitly deletable deployment
# ---------------------------------------------------------------------------


def test_the_resource_group_name_is_derived_from_the_authority_commit():
    name = plan.resource_group_name(E1_AUTHORITY_COMMIT)
    assert name.startswith("rg-study4f-e1-")
    assert name == plan.resource_group_name(E1_AUTHORITY_COMMIT)
    other = plan.resource_group_name(PREDECESSOR_COMMIT)
    assert other != name
    with pytest.raises(plan.Study4FE1DeploymentPlanError):
        plan.resource_group_name("not-a-commit")


def test_every_created_resource_carries_the_registered_tags():
    built = plan.build_plan(E1_AUTHORITY_COMMIT, "Standard_NC40ads_H100_v5",
                            "eastus2", "1", "2026-08-18T00:00:00Z",
                            "2026-08-19T00:00:00Z")
    tags = built["tags"]
    assert tags["project"] == "J-space-observation"
    assert tags["study"] == "study4f-e1"
    assert tags["authority_commit"] == E1_AUTHORITY_COMMIT
    assert tags["created_at"] and tags["expires_at"]
    with pytest.raises(plan.Study4FE1DeploymentPlanError):
        plan.tags(E1_AUTHORITY_COMMIT, "2026-08-19T00:00:00Z",
                  "2026-08-18T00:00:00Z")


def test_the_plan_is_on_demand_dedicated_and_secret_free():
    built = plan.build_plan(E1_AUTHORITY_COMMIT, "Standard_NC40ads_H100_v5",
                            "eastus2", "1", "2026-08-18T00:00:00Z",
                            "2026-08-19T00:00:00Z")
    assert built["vm"]["spot"] is False
    assert built["vm"]["priority"] == "Regular"
    assert built["vm"]["gpu_count"] == 1
    assert built["resource_group_is_new_and_dedicated"] is True
    assert built["reuses_an_existing_resource_group"] is False
    assert built["deletes_an_existing_resource_group"] is False
    assert built["network"]["public_service_endpoint"] is False
    assert all(value is False for value in built["secrets"].values())
    assert built["creates_nothing_when_emitted"] is True


def test_cleanup_refuses_globs_and_unresolved_variables():
    group = plan.resource_group_name(E1_AUTHORITY_COMMIT)
    subscription = "00000000-0000-0000-0000-000000000000"
    good = ("/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Compute"
            "/virtualMachines/vm-study4f-e1" % (subscription, group))
    assert plan.cleanup_targets([good], group) == [good]
    for bad in (
        good.replace("vm-study4f-e1", "*"),
        good.replace("vm-study4f-e1", "$VM_NAME"),
        good.replace("vm-study4f-e1", "{name}"),
        "/subscriptions/%s/resourceGroups/other-group/providers/"
        "Microsoft.Compute/virtualMachines/vm" % (subscription,),
        "Microsoft.Compute/virtualMachines/vm",
    ):
        with pytest.raises(plan.Study4FE1DeploymentPlanError):
            plan.cleanup_targets([bad], group)


def test_a_failed_artifact_publication_retains_the_group_for_recovery():
    built = plan.build_plan(E1_AUTHORITY_COMMIT, "Standard_NC40ads_H100_v5",
                            "eastus2", "1", "2026-08-18T00:00:00Z",
                            "2026-08-19T00:00:00Z")
    retained = plan.cleanup_verdict(built, [], artifacts_published=False)
    assert retained["vm_deallocated"] is True
    assert retained["resource_group_deleted"] is False
    assert retained["resource_group_retained_for_recovery"] is True
    deleted = plan.cleanup_verdict(built, [], artifacts_published=True)
    assert deleted["resource_group_deleted"] is True
    assert deleted["no_billable_accelerator_remains"] is True


# ---------------------------------------------------------------------------
# 6. Shakedown allowance and the post-first-call freeze
# ---------------------------------------------------------------------------


def test_e1_inherits_the_remaining_allowance_not_a_fresh_one():
    shakedown = _json(STUDY4F / "shakedown" /
                      "study4f_shakedown_disposition.json")
    assert shakedown["attempts_used"] == lifecycle.ORIGINAL_SHAKEDOWN_ATTEMPTS_USED
    assert shakedown["attempts_permitted"] == \
        lifecycle.ORIGINAL_SHAKEDOWN_ATTEMPTS_PERMITTED
    assert shakedown["accelerator_hours_used"] == \
        lifecycle.ORIGINAL_ACCELERATOR_HOURS_USED
    assert lifecycle.E1_MAX_ADDITIONAL_SHAKEDOWN_ATTEMPTS == 2
    assert lifecycle.E1_MAX_TOTAL_ACCELERATOR_HOURS == 6
    allowance = lifecycle.remaining_allowance(0, 0)
    assert allowance["e1_attempts_remaining"] == 2
    assert allowance["accelerator_hours_remaining"] == 6
    assert allowance["exhausted"] is False


def test_an_exhausted_allowance_stops_before_any_study_bank_execution():
    assert lifecycle.remaining_allowance(2, 0)["exhausted"] is True
    assert lifecycle.remaining_allowance(0, 6)["exhausted"] is True
    assert lifecycle.remaining_allowance(2, 6)["state_when_exhausted_without_a_pass"] \
        == "STUDY4F_E1_SHAKEDOWN_FAILED_NO_STUDY_BANK_EXECUTION"


@pytest.mark.parametrize("fix", [
    "driver_or_container_compatibility", "dependency_installation",
    "paths_and_permissions", "networking_for_public_checkpoint_acquisition",
    "serialization", "logging", "crash_recovery", "azure_deployment_mechanics",
])
def test_white_listed_fixes_are_exactly_the_registered_eight(fix):
    assert lifecycle.fix_is_white_listed(fix)
    assert len(lifecycle.WHITE_LISTED_FIXES) == 8


@pytest.mark.parametrize("fix", [
    "checkpoint", "revision", "dtype", "hardware_selection_rule", "task",
    "bank", "prompt", "parser", "decoding_configuration", "threshold", "alpha",
    "pass_boundary", "state_transition", "claim_language",
])
def test_no_decision_bearing_value_can_be_changed_by_a_fix(fix):
    assert fix in lifecycle.IMMUTABLE_DECISION_BEARING_VALUES
    assert not lifecycle.fix_is_white_listed(fix)
    verdict = lifecycle.classify_fixes([fix])
    assert verdict["non_white_listed_defect_found"] is True
    assert verdict["state_if_refused"] == \
        "STUDY4F_E1_SHAKEDOWN_FAILED_NO_STUDY_BANK_EXECUTION"


def test_after_the_first_study_bank_call_nothing_may_be_repaired():
    frozen = lifecycle.post_first_call_freeze(True)
    assert frozen["engineering_fix_permitted"] is False
    assert frozen["hardware_switch_permitted"] is False
    assert frozen["reseal_permitted"] is False
    assert frozen["parser_or_output_reinterpretation_permitted"] is False
    assert frozen["cell_repetition_because_unfavorable_permitted"] is False
    assert frozen["resume_only_through_the_sealed_create_only_journal"] is True


def test_a_resume_never_duplicates_or_replaces_a_completed_item():
    journal = {"completed_item_ids": ["item-1", "item-2"]}
    assert lifecycle.resume_is_legal(journal, "item-3") is True
    assert lifecycle.resume_is_legal(journal, "item-1") is False


# ---------------------------------------------------------------------------
# 7. The registered ladder is executed, never reimplemented
# ---------------------------------------------------------------------------


def test_execution_is_refused_until_the_seal_is_published():
    with pytest.raises(lifecycle.Study4FE1LifecycleError):
        lifecycle.execute_registered_ladder(ROOT, {}, execution_authorized=False)


def test_the_successor_delegates_to_the_published_state_machine():
    machine = lifecycle.load_registered_state_machine(ROOT)
    assert machine.LADDER == ("RP_B1", "RP_B2", "RP_B3")
    assert machine.CANDIDATE_QUALIFIED == \
        "RP_B_DEVELOPMENTAL_CANDIDATE_PENDING_CONFIRMATION"
    results = {(role, depth, cell): False
               for role in ("RP_B1", "RP_B2", "RP_B3", "RT")
               for depth in ("D2", "D3") for cell in ("COT", "E0")}
    outcome = lifecycle.execute_registered_ladder(ROOT, results,
                                                  execution_authorized=True)
    assert outcome["rt_authorized"] is False
    assert outcome["registered_transitions_altered"] is False
    assert outcome["study4f_state"] == \
        "STUDY4F_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER"
    assert outcome["state"] == \
        "STUDY4F_E1_NO_NATURAL_POSITIVE_REFERENCE_QUALIFIED_WITHIN_REGISTERED_LADDER"


def test_a_qualified_candidate_stops_the_ladder_and_authorizes_rt_only_then():
    results = {(role, depth, cell): False
               for role in ("RP_B1", "RP_B2", "RP_B3", "RT")
               for depth in ("D2", "D3") for cell in ("COT", "E0")}
    for depth in ("D2", "D3"):
        for cell in ("COT", "E0"):
            results[("RP_B1", depth, cell)] = True
            results[("RT", depth, cell)] = True
    outcome = lifecycle.execute_registered_ladder(ROOT, results,
                                                  execution_authorized=True)
    assert outcome["qualified_candidate"] == "RP_B1"
    assert outcome["candidates_evaluated"] == 1
    assert outcome["state"] == \
        "STUDY4F_E1_BEHAVIORAL_FEASIBILITY_SUPPORTED_AWAITING_SEPARATE_CONFIRMATION"


def test_a_candidate_failure_never_blocks_a_later_candidate():
    results = {(role, depth, cell): False
               for role in ("RP_B1", "RP_B2", "RP_B3", "RT")
               for depth in ("D2", "D3") for cell in ("COT", "E0")}
    for depth in ("D2", "D3"):
        for cell in ("COT", "E0"):
            results[("RP_B2", depth, cell)] = True
    outcome = lifecycle.execute_registered_ladder(ROOT, results,
                                                  execution_authorized=True)
    assert outcome["qualified_candidate"] == "RP_B2"
    assert outcome["candidates"][0]["role"] == "RP_B1"
    assert outcome["candidates"][0]["qualified"] is False


def test_an_interruption_is_never_a_licence_to_reinterpret():
    record = lifecycle.interrupted("host lost")
    assert record["state"] == "STUDY4F_E1_EXECUTION_INTERRUPTED_NO_REINTERPRETATION"
    assert record["reinterpretation_permitted"] is False
    assert record["reseal_permitted"] is False
    assert record["completed_items_replaced"] == 0
    assert record["completed_items_duplicated"] == 0


# ---------------------------------------------------------------------------
# 8. The registered terminal state
# ---------------------------------------------------------------------------


def test_exactly_nine_terminal_states_are_registered():
    assert len(lifecycle.REGISTERED_TERMINAL_STATES) == 9
    assert len(set(lifecycle.REGISTERED_TERMINAL_STATES)) == 9


def test_status_validates_against_its_restrictive_schema(status):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(status, _json(STATUS_SCHEMA))


def test_the_final_state_is_exactly_one_registered_state(status, quota):
    state = status["lifecycle_state"]
    assert lifecycle.state_is_registered(state)
    assert state == "STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL"
    assert quota["state"] == state
    assert status["terminal"] is True


def test_the_terminal_state_follows_from_the_registered_routing(status):
    assert lifecycle.final_state(quota_sufficient=False) == \
        status["lifecycle_state"]


def test_no_state_authorizes_a_prohibited_operation():
    for state in lifecycle.REGISTERED_TERMINAL_STATES:
        flags = lifecycle.authorization_flags(state)
        assert not any(flags.values()), (state, flags)
    with pytest.raises(lifecycle.Study4FE1LifecycleError):
        lifecycle.authorization_flags("STUDY4F_E1_SOMETHING_CONVENIENT")


def test_every_authorization_flag_and_counter_is_false_or_zero(status):
    assert not any(status["authorization_flags"].values())
    assert not any(status["claim_boundary"].values())
    counters = dict(status["zero_operation_counters"])
    assert counters.pop("cells_skipped") == 16
    assert all(value == 0 for value in counters.values()), counters


def test_nothing_downstream_of_the_stop_was_reached(status):
    assert not any(status["not_reached"].values())
    assert status["azure"]["resources_created"] == 0
    assert status["azure"]["deployment_attempts"] == 0
    assert status["azure"]["capacity_observed"] is False
    assert status["shakedown_allowance"]["e1_attempts_used"] == 0
    assert status["shakedown_allowance"]["accelerator_hours_used"] == 0


# ---------------------------------------------------------------------------
# 9. Azure evidence hygiene
# ---------------------------------------------------------------------------


def test_quota_and_capacity_are_reported_separately(quota):
    assert quota["quota"]["reported_separately_from_capacity"] is True
    assert quota["quota"]["eligible_sku_region_pairs_with_sufficient_quota"] == 0
    assert quota["quota"]["blocking_dimension"] == "VM-family vCPU quota"
    assert quota["capacity"]["observed"] is False
    assert quota["capacity"]["deployment_attempts"] == 0
    assert quota["capacity"]["spot_capacity_used"] is False
    assert "unavailable" not in quota["capacity"]["reason_not_observed"].lower() \
        or "not reported as" in quota["capacity"]["reason_not_observed"]


def test_exactly_one_minimal_quota_request_was_submitted(quota):
    request = quota["submitted_request"]
    assert request["count"] == 1
    assert request["larger_request_submitted"] is False
    assert request["instances_requested"] == 1
    assert request["sku"] == "Standard_NC40ads_H100_v5"
    assert request["requested_family_vcpus"] == 40
    assert request["quota_granted"] is False
    assert request["family_vcpu_limit_after_the_request"] == 0
    assert request["request_id"]


def test_the_request_targets_the_lexicographic_head_of_the_registered_order(
        discovery, quota):
    verdict = selection.select(discovery["offers"])
    assert verdict["branch"] == "no_sufficient_quota"
    target = verdict["quota_request_target"]
    assert target["sku"] == quota["submitted_request"]["sku"]
    assert target["region"] == quota["submitted_request"]["region"]
    assert target["sku"] == "Standard_NC40ads_H100_v5"


def test_the_discovery_evidence_reproduces_the_recorded_disposition(
        discovery, status):
    offers = discovery["offers"]
    h100 = [offer for offer in offers
            if offer["sku"] == "Standard_NC40ads_H100_v5"]
    a100 = [offer for offer in offers
            if offer["sku"] == "Standard_NC24ads_A100_v4"]
    assert len(h100) == status["azure"]["regions_returned_for_h100"]
    assert len(a100) == status["azure"]["regions_returned_for_a100"]
    assert all(offer["family_vcpu_limit"] == 0 for offer in offers)
    assert selection.eligible_regions(offers, "Standard_NC40ads_H100_v5") == []
    assert selection.eligible_regions(offers, "Standard_NC24ads_A100_v4") == []


def test_no_committed_e1_artifact_leaks_a_secret_or_a_full_identifier():
    """No credential, and no bare GUID except the recorded quota request ID.

    Subscription and tenant identifiers are GUIDs, so requiring every GUID in
    the namespace to be explicitly allow-listed catches a leak without this
    module having to carry the very identifiers it is protecting.

    This module is exempt from the *literal marker* scan and only from that
    scan, because it is the scanner: the markers below are its patterns, not
    leaked material. The GUID check, which is the part that could actually
    catch a leaked subscription or tenant ID, still applies to it.
    """
    import re
    guid = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
                      r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
    allowed = {
        "a6817961-e0f7-4cbe-a1ef-7ac4104e1089",          # the quota request ID
        "00000000-0000-0000-0000-000000000000",          # test placeholder
    }
    forbidden = ("BEGIN OPENSSH PRIVATE KEY", "BEGIN RSA PRIVATE KEY",
                 "BEGIN PRIVATE KEY", "?sv=", "&sig=", "access_token=",
                 "client_secret")
    scanner = str(HERE.relative_to(ROOT)).replace("\\", "/")
    tracked = [line.strip() for line
               in _git("ls-files", "studies/study4f/execution-e1").splitlines()
               if line.strip()]
    assert tracked, "the successor namespace has no committed file"
    assert scanner in tracked
    for relative in tracked:
        text = (ROOT / relative).read_text(encoding="utf-8", errors="replace")
        if relative != scanner:
            for marker in forbidden:
                assert marker not in text, (relative, marker)
        leaked = sorted(set(guid.findall(text)) - allowed)
        assert leaked == [], (relative, leaked)


def test_the_subscription_is_represented_only_by_a_salted_hash(status,
                                                               discovery):
    identity = discovery["identity"]
    assert identity["subscription_id_committed"] is False
    assert identity["tenant_id_committed"] is False
    assert identity["credentials_committed"] is False
    assert len(identity["subscription_salted_sha256"]) == 64
    assert len(identity["subscription_last_four"]) == 4
    assert status["azure"]["subscription_salted_sha256"] == \
        identity["subscription_salted_sha256"]


def test_the_operator_packet_names_the_exact_registered_request():
    text = OPERATOR_PACKET.read_text(encoding="utf-8")
    assert "Standard_NC40ads_H100_v5" in text
    assert "standardNCadsH100v5Family" in text
    assert "australiaeast" in text
    assert "40" in text
    assert "QuotaNotAvailableForResource" in text
    lowered = text.lower()
    assert "quantization" in lowered and "prohibited" in lowered


# ---------------------------------------------------------------------------
# 10. The predecessor and the wider repository are untouched
# ---------------------------------------------------------------------------


def test_the_successor_added_paths_only_inside_its_own_namespace():
    statuses = {}
    for line in _git("diff", "--name-status", PREDECESSOR_COMMIT,
                     "HEAD").splitlines():
        if not line.strip():
            continue
        code, path = line.split("\t", 1)
        statuses[path.strip()] = code.strip()
    added = {path for path, code in statuses.items() if code == "A"}
    other = {path for path, code in statuses.items() if code != "A"}
    assert other == set(), sorted(other)
    outside = sorted(path for path in added
                     if not path.startswith("studies/study4f/execution-e1/")
                     and path != "studies/study4f/prompts/"
                                 "study4f_e1_qualifying_accelerator_execution_authority.md")
    assert outside == [], outside


def test_no_study4f_or_study3r_byte_moved():
    changed = {line.strip() for line
               in _git("diff", "--name-only", PREDECESSOR_COMMIT,
                       "HEAD").splitlines() if line.strip()}
    for path in sorted(changed):
        assert not path.startswith("studies/study3r/"), path
    protected = (
        "studies/study4f/STATUS.json",
        "studies/study4f/STATUS.schema.json",
        "studies/study4f/protocol/study4f_protocol_v1.json",
        "studies/study4f/protocol/study4f_protocol_v1.schema.json",
        "studies/study4f/analysis/study4f_task_banks.py",
        "studies/study4f/analysis/study4f_interfaces.py",
        "studies/study4f/analysis/study4f_design_statistics.py",
        "studies/study4f/analysis/study4f_state_machine.py",
        "studies/study4f/analysis/study4f_validation.py",
        "studies/study4f/analysis/study4f_resource_route.py",
        "studies/study4f/shakedown/study4f_shakedown_disposition.json",
        "studies/study4f/tests/test_study4f_behavioral_feasibility.py",
        "studies/study4f/prompts/"
        "study4f_minimal_behavioral_feasibility_authority.md",
        "paper/evidence_ledger.csv",
        ".gitattributes",
        "tests/test_study3r_protocol_v1.py",
        "tests/test_study3r_operator_governance.py",
    )
    for path in protected:
        assert path not in changed, path
        assert _git("rev-parse", "%s:%s" % (PREDECESSOR_COMMIT, path)).strip() \
            == _git("rev-parse", "HEAD:%s" % path).strip(), path


def test_every_study3r_byte_is_identical_to_the_closure_head():
    listed = [line.strip() for line
              in _git("ls-tree", "-r", "--name-only", STUDY3R_CLOSURE_COMMIT,
                      "studies/study3r").splitlines() if line.strip()]
    assert len(listed) >= 50
    moved = [path for path in listed
             if _git("rev-parse", "%s:%s" % (STUDY3R_CLOSURE_COMMIT, path)).strip()
             != _git("rev-parse", "HEAD:%s" % path).strip()]
    assert moved == []


def test_the_evidence_ledger_is_untouched_and_ends_at_ev_0016(status):
    import hashlib
    ledger = ROOT / "paper" / "evidence_ledger.csv"
    payload = ledger.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == \
        status["evidence_ledger"]["sha256"]
    rows = payload.decode("utf-8").splitlines()
    assert rows[-1].startswith("EV-0016,")
    assert status["evidence_ledger"]["rows_added_by_study4f_e1"] == 0


def test_no_study_bank_or_seal_is_committed():
    committed = _git("ls-files", "studies/study4f").split()
    assert not any("bank" in path and path.endswith(".json")
                   for path in committed), committed
    assert not any("execution_seal" in path for path in committed), committed


def test_the_registered_baseline_failure_node_ids_are_the_recorded_nine(status):
    assert len(REGISTERED_BASELINE_FAILURES) == 9
    assert len(set(REGISTERED_BASELINE_FAILURES)) == 9
    differential = status["test_differential"]
    assert differential["registered_starting_baseline"] == \
        "9 failed, 5,119 passed, 16 skipped"
    assert differential["baseline_reproduced_at_the_starting_commit"] is True
    assert differential["new_non_scope_failures"] == 0
    assert differential["historical_failures_edited_or_suppressed"] == 0


def test_no_prohibited_scientific_operation_is_reachable_from_this_namespace():
    """No module in this namespace imports a model runtime.

    The check is over the parsed import graph rather than over source text, so
    it cannot be satisfied or defeated by how a name happens to be spelled in a
    string literal, and this module can police itself.
    """
    import ast
    banned_modules = {"torch", "transformers", "bitsandbytes", "accelerate",
                      "safetensors", "vllm"}
    modules = sorted((E1 / "analysis").glob("*.py"))
    assert len(modules) == 5, [path.name for path in modules]
    for path in modules + [HERE]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0]
                                for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not (imported & banned_modules), \
            (path.name, sorted(imported & banned_modules))
    for path in modules:
        source = path.read_text(encoding="utf-8")
        for forbidden in ("AutoModelForCausalLM", "load_in_4bit",
                          "load_in_8bit", 'device_map="auto"',
                          "device_map='auto'"):
            assert forbidden not in source, (path.name, forbidden)


# ---------------------------------------------------------------------------
# 11. Disclosure and byte hygiene
# ---------------------------------------------------------------------------


def test_the_disclosure_asserts_no_prohibited_conclusion():
    text = DISCLOSURE.read_text(encoding="utf-8").lower()
    for prohibited in (
        "j-space exists", "j-space does not exist", "j-space is observable",
        "j-space is unobservable", "rp-b was confirmed",
        "the model cannot reason internally",
        "single-forward reasoning was demonstrated",
    ):
        assert prohibited not in text, prohibited


def test_the_disclosure_reports_the_registered_disclosure_items():
    text = DISCLOSURE.read_text(encoding="utf-8")
    for required in (
        E1_AUTHORITY_COMMIT, PREDECESSOR_COMMIT,
        "STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL",
        "Standard_NC40ads_H100_v5", "Standard_NC24ads_A100_v4",
        "a6817961-e0f7-4cbe-a1ef-7ac4104e1089",
        "EV-0016", "69,502,926,848",
        "9 failed, 5,119 passed, 16 skipped",
    ):
        assert required in text, required
    lowered = text.lower()
    assert "no scientific result" in lowered
    assert "capacity" in lowered


def test_the_readme_routes_to_the_status_router_first():
    text = README.read_text(encoding="utf-8")
    assert text.index("STATUS.json") < text.index("azure_discovery.json")
    assert "STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL" in text


@pytest.mark.parametrize("relative", sorted(
    str(path.relative_to(ROOT)).replace("\\", "/")
    for path in (E1.rglob("*.py"))) + sorted(
    str(path.relative_to(ROOT)).replace("\\", "/")
    for path in list(E1.rglob("*.json")) + list(E1.rglob("*.md"))) + [
    "studies/study4f/prompts/"
    "study4f_e1_qualifying_accelerator_execution_authority.md"])
def test_every_e1_artifact_is_lf_only(relative):
    payload = (ROOT / relative).read_bytes()
    assert payload
    assert b"\r" not in payload, relative
    assert payload.endswith(b"\n"), relative
    assert not payload.startswith(b"\xef\xbb\xbf"), relative
