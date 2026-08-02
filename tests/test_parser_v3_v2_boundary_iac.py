"""Controls for the private review boundary infrastructure.

Infrastructure tests are usually theatre: they read a template and assert that
the words in it are the words the author meant to write. The two controls that
matter here are not that.

``TestTheMatrixIsGeneratedNotTranscribed`` compares ``role_matrix.json`` byte
for byte against what the entrypoint registry exports. That file is the only
place the deployment learns what command to run, so if it drifts from the code,
the platform runs something the tests never exercised. Section 5.2 calls that
out as the failure mode to prevent, and this is where it is prevented.

``TestTheOverlapRuleActuallyDetectsOverlap`` re-implements the arithmetic
``main.bicep`` performs and then feeds it a prefix that does overlap. A gate
that has only ever been shown a passing input is not known to be a gate.

The remaining classes check the address plan's internal consistency and assert
that the security properties the boundary depends on are actually declared.
Those are text-level checks and are honest about being so: they prove the
template says the right thing, not that Azure did it. What Azure did is proven
by the Phase B deployment and its canaries, not here.
"""

from __future__ import annotations

import ipaddress
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from jspace_observation import parser_v3_v2_entrypoints as entrypoints  # noqa: E402

BOUNDARY = ROOT / "infra" / "azure" / "parser_v3_v2_boundary"
ROLE_MATRIX_PATH = BOUNDARY / "role_matrix.json"
ADDRESS_PLAN_PATH = BOUNDARY / "address_plan.json"
MAIN_TEMPLATE = BOUNDARY / "main.bicep"
MODULES = BOUNDARY / "modules"

SUBNET_ORDER = (
    "AzureFirewallSubnet",
    "AzureFirewallManagementSubnet",
    "snet-aca-boundary",
    "snet-pe-boundary",
)

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def role_matrix() -> dict:
    return _read_json(ROLE_MATRIX_PATH)


@pytest.fixture(scope="module")
def address_plan() -> dict:
    return _read_json(ADDRESS_PLAN_PATH)


def _bicep_files() -> list[Path]:
    return sorted([MAIN_TEMPLATE] + list(MODULES.glob("*.bicep")))


def _decorators(path: Path) -> list[str]:
    """Decorator lines, with comments removed first.

    Several of these templates explain in a block comment why a particular
    decorator was *not* used, and those explanations quote the decorator they
    are rejecting. Scanning the raw file would therefore find ``@allowed`` in a
    module that deliberately does not use it. Stripping comments before looking
    is the difference between checking a declaration and checking a sentence.
    """
    text = _BLOCK_COMMENT.sub("", _read_text(path))
    return [
        line.strip() for line in text.splitlines() if line.strip().startswith("@")
    ]


# ---------------------------------------------------------------------------
# The binding between the deployed command and the tested command
# ---------------------------------------------------------------------------


class TestTheMatrixIsGeneratedNotTranscribed:
    def test_the_committed_matrix_equals_what_the_code_exports(self, role_matrix):
        assert role_matrix == entrypoints.export_role_matrix()

    def test_a_drifted_matrix_is_rejected_by_that_comparison(self, role_matrix):
        drifted = json.loads(json.dumps(role_matrix))
        drifted["roles"][0]["command"] = ["python", "-m", "jspace_observation.something"]
        assert drifted != entrypoints.export_role_matrix()

    def test_every_role_in_the_registry_is_present(self, role_matrix):
        assert {row["role"] for row in role_matrix["roles"]} == set(entrypoints.ROLE_IDENTITY_NAMES)

    def test_every_command_round_trips_through_the_registry_check(self, role_matrix):
        for row in role_matrix["roles"]:
            entrypoints.assert_container_command_is_registered(
                role=row["role"], command=tuple(row["command"])
            )

    def test_a_command_that_is_not_registered_is_refused(self, role_matrix):
        row = role_matrix["roles"][0]
        with pytest.raises(entrypoints.EntrypointError):
            entrypoints.assert_container_command_is_registered(
                role=row["role"],
                command=tuple(row["command"][:-1]) + ("stage_e",),
            )

    def test_the_entrypoint_path_matches_the_one_the_container_runs(self, role_matrix):
        assert role_matrix["container_entrypoint_path"] == entrypoints.CONTAINER_ENTRYPOINT_PATH
        for row in role_matrix["roles"]:
            assert entrypoints.CONTAINER_ENTRYPOINT_PATH in row["command"]

    def test_the_matrix_names_no_module_invocation(self, role_matrix):
        # ``python -m jspace_observation.X`` executes the package __init__, which
        # imports the parser. A role that must be parser-free cannot be launched
        # that way, so the string must not appear anywhere in the matrix.
        rendered = json.dumps(role_matrix)
        assert "-m" not in json.loads(rendered)["roles"][0]["command"]
        assert "jspace_observation." not in rendered.replace(
            entrypoints.CONTAINER_ENTRYPOINT_PATH, ""
        )


class TestTheMatrixCarriesOnlyClosedVocabulary:
    def test_containers_and_prefixes_are_registered(self, role_matrix):
        for row in role_matrix["roles"]:
            assert row["container"] == entrypoints.REGISTERED_CONTAINERS[row["role"]]
            assert row["prefix"] == entrypoints.REGISTERED_PREFIXES[row["role"]]

    def test_read_containers_are_derived_from_the_declared_lanes(self, role_matrix):
        for row in role_matrix["roles"]:
            assert tuple(row["reads"]) == tuple(
                entrypoints.lifecycle.ROLE_LANES[row["role"]]["reads"]
            )
            for read_class in row["reads"]:
                assert entrypoints.READ_CONTAINERS[read_class] in row["read_containers"]

    def test_endpoints_are_the_closed_allowlist(self, role_matrix):
        assert set(role_matrix["registered_endpoints"]) == set(
            entrypoints.REGISTERED_ENDPOINTS
        )

    def test_parser_free_roles_are_marked(self, role_matrix):
        marked = {row["role"] for row in role_matrix["roles"] if row["parser_free"]}
        assert marked == set(entrypoints.PARSER_FREE_ROLES)

    def test_the_matrix_exposes_a_closed_set_of_keys(self, role_matrix):
        # A generated record is only safe to commit if its shape is fixed. An
        # extra key appearing here would be an unreviewed channel out of the
        # code and into the deployment.
        assert set(role_matrix) == {
            "schema_version",
            "container_entrypoint_path",
            "roles",
            "registered_endpoints",
        }
        for row in role_matrix["roles"]:
            assert set(row) == {
                "role",
                "entrypoint",
                "command",
                "uami_name",
                "container",
                "prefix",
                "schema_ids",
                "reads",
                "writes",
                "read_containers",
                "parser_free",
            }


# ---------------------------------------------------------------------------
# The address plan
# ---------------------------------------------------------------------------


class TestTheAddressPlanIsInternallyConsistent:
    def test_every_subnet_sits_inside_the_boundary_vnet(self, address_plan):
        vnet = ipaddress.ip_network(address_plan["boundary_vnet_prefix"])
        for subnet in address_plan["subnets"]:
            assert ipaddress.ip_network(subnet["prefix"]).subnet_of(vnet)

    def test_the_subnets_are_pairwise_disjoint(self, address_plan):
        nets = [ipaddress.ip_network(s["prefix"]) for s in address_plan["subnets"]]
        for left_index, left in enumerate(nets):
            for right in nets[left_index + 1 :]:
                assert not left.overlaps(right)

    def test_the_subnets_appear_in_the_declared_order(self, address_plan):
        assert tuple(s["name"] for s in address_plan["subnets"]) == SUBNET_ORDER

    def test_the_platform_minimum_sizes_are_respected(self, address_plan):
        required = {
            "AzureFirewallSubnet": 26,
            "AzureFirewallManagementSubnet": 26,
            "snet-aca-boundary": 23,
            "snet-pe-boundary": 26,
        }
        for subnet in address_plan["subnets"]:
            network = ipaddress.ip_network(subnet["prefix"])
            assert network.prefixlen <= required[subnet["name"]]

    def test_the_boundary_is_disjoint_from_every_observed_network(self, address_plan):
        boundary = ipaddress.ip_network(address_plan["boundary_vnet_prefix"])
        for vnet in address_plan["observed_vnets"]:
            for prefix in vnet["address_prefixes"]:
                assert not boundary.overlaps(ipaddress.ip_network(prefix))

    def test_the_boundary_is_above_every_observed_network(self, address_plan):
        # The stated rule is "strictly above the highest allocated /16", so that
        # an existing network growing downward cannot reach the boundary.
        boundary = ipaddress.ip_network(address_plan["boundary_vnet_prefix"])
        for vnet in address_plan["observed_vnets"]:
            for prefix in vnet["address_prefixes"]:
                assert boundary.network_address > ipaddress.ip_network(prefix).network_address

    def test_the_region_hosts_the_private_storage_account(self, address_plan, role_matrix):
        account = address_plan["region_evidence"]["existing_private_storage"].split()[0]
        endpoints = [
            endpoint
            for endpoint in role_matrix["registered_endpoints"]
            if ".blob." in endpoint
        ]
        assert endpoints and endpoints[0].startswith(account + ".")

    def test_the_quota_question_is_recorded_rather_than_assumed(self, address_plan):
        unresolved = " ".join(address_plan["unresolved_at_freeze"]).lower()
        assert "quota" in unresolved
        assert "blocked_on_model_availability_or_quota" in unresolved


# ---------------------------------------------------------------------------
# The overlap gate
# ---------------------------------------------------------------------------


def _octet_span(prefix_length: int) -> int:
    table = {8: 256, 9: 128, 10: 64, 11: 32, 12: 16, 13: 8, 14: 4, 15: 2, 16: 1}
    return table.get(prefix_length, 1)


def _conflicts(boundary_prefix: str, observed: list[str]) -> list[str]:
    """The arithmetic main.bicep performs, expressed once more in Python.

    This is deliberately a re-implementation rather than a call into shared
    code: the point is to check that the Bicep expression computes what it is
    supposed to, and a shared helper would make both sides wrong together.
    """
    boundary_first, boundary_second = (
        int(part) for part in boundary_prefix.split("/")[0].split(".")[:2]
    )
    conflicting = []
    for prefix in observed:
        address, length = prefix.split("/")
        first, second = (int(part) for part in address.split(".")[:2])
        span = _octet_span(int(length))
        if first == boundary_first and second <= boundary_second <= second + span - 1:
            conflicting.append(prefix)
    return conflicting


class TestTheOverlapRuleActuallyDetectsOverlap:
    def test_the_committed_plan_yields_no_conflicts(self, address_plan):
        observed = [
            prefix
            for vnet in address_plan["observed_vnets"]
            for prefix in vnet["address_prefixes"]
        ]
        assert _conflicts(address_plan["boundary_vnet_prefix"], observed) == []

    @pytest.mark.parametrize(
        "intruder",
        ["10.81.0.0/16", "10.80.0.0/15", "10.64.0.0/10", "10.0.0.0/8", "10.81.7.0/24"],
    )
    def test_an_overlapping_prefix_is_detected(self, address_plan, intruder):
        assert _conflicts(address_plan["boundary_vnet_prefix"], [intruder]) == [intruder]

    @pytest.mark.parametrize("neighbour", ["10.80.0.0/16", "10.82.0.0/16", "10.42.0.0/16"])
    def test_a_non_overlapping_neighbour_is_not_flagged(self, address_plan, neighbour):
        assert _conflicts(address_plan["boundary_vnet_prefix"], [neighbour]) == []

    def test_the_gate_module_accepts_only_zero(self):
        decorators = _decorators(MODULES / "assert_no_overlap.bicep")
        assert "@minValue(0)" in decorators
        assert "@maxValue(0)" in decorators
        assert "param conflictingPrefixCount int" in _read_text(
            MODULES / "assert_no_overlap.bicep"
        )

    def test_the_gate_is_a_preflight_constraint_not_a_type_narrowing(self):
        # @allowed([0]) narrows the parameter's *type* to the literal 0, so
        # Bicep rejects any int-valued argument -- including the correct one.
        # The gate would then refuse every deployment, and would be removed by
        # the first person it inconvenienced. The check reads declarations
        # rather than file text because the module documents that reasoning in
        # a comment, and a substring search cannot tell the two apart.
        decorators = _decorators(MODULES / "assert_no_overlap.bicep")
        assert not any(line.startswith("@allowed") for line in decorators)
        assert "conflictingPrefixCount: any(length(conflictingPrefixes))" in _read_text(
            MAIN_TEMPLATE
        )

    def test_main_computes_the_count_and_passes_it_to_the_gate(self):
        text = _read_text(MAIN_TEMPLATE)
        assert "conflictingPrefixCount: any(length(conflictingPrefixes))" in text
        assert "modules/assert_no_overlap.bicep" in text


# ---------------------------------------------------------------------------
# What the templates declare
# ---------------------------------------------------------------------------


class TestNothingIsTranscribedIntoTheTemplates:
    def test_no_subnet_prefix_is_written_literally_in_any_template(self, address_plan):
        literals = [subnet["prefix"] for subnet in address_plan["subnets"]]
        literals.append(address_plan["boundary_vnet_prefix"])
        for path in _bicep_files():
            text = _read_text(path)
            for literal in literals:
                assert literal not in text, f"{path.name} hard-codes {literal}"

    def test_no_endpoint_host_is_written_literally_in_main(self, role_matrix):
        text = _read_text(MAIN_TEMPLATE)
        for endpoint in role_matrix["registered_endpoints"]:
            assert endpoint not in text
            assert endpoint.split(".")[0] not in text

    def test_main_loads_both_records(self):
        text = _read_text(MAIN_TEMPLATE)
        assert "loadJsonContent('address_plan.json')" in text
        assert "loadJsonContent('role_matrix.json')" in text

    def test_no_container_command_is_written_literally(self, role_matrix):
        for path in _bicep_files():
            text = _read_text(path)
            assert entrypoints.CONTAINER_ENTRYPOINT_PATH not in text


class TestTheBoundaryDeclaresItsSecurityProperties:
    def test_the_runtime_registry_is_private(self):
        text = _read_text(MODULES / "privatelink.bicep")
        assert "publicNetworkAccess: 'Disabled'" in text
        assert "networkRuleBypassOptions: 'None'" in text

    def test_both_private_dns_zones_are_created_and_linked(self):
        text = _read_text(MODULES / "privatelink.bicep")
        assert "privatelink.azurecr.io" in text
        assert "privatelink.blob." in text
        assert "virtualNetworkLinks" in text

    def test_the_environment_has_no_public_ingress(self):
        text = _read_text(MODULES / "workload.bicep")
        assert "internal: true" in text

    def test_every_job_is_manually_triggered(self, role_matrix):
        text = _read_text(MODULES / "workload.bicep")
        assert "triggerType: 'Manual'" in text
        assert "replicaRetryLimit: 0" in text

    def test_no_job_declares_a_secret(self):
        text = _read_text(MODULES / "workload.bicep")
        assert "secrets: []" in text
        assert "secretRef" not in text

    def test_images_are_pinned_by_digest_not_tag(self):
        text = _read_text(MODULES / "workload.bicep")
        assert "roleImageDigests[role.role]" in text
        assert ":latest" not in text

    def test_the_image_digest_parameter_has_no_default(self):
        text = _read_text(MODULES / "workload.bicep")
        assert "param roleImageDigests object\n" in text

    def test_the_egress_default_is_deny(self):
        text = _read_text(MODULES / "network.bicep")
        assert "deny-everything-else" in text
        assert "threatIntelMode: 'Deny'" in text

    def test_all_workload_traffic_is_routed_through_the_firewall(self):
        text = _read_text(MODULES / "network.bicep")
        assert "0.0.0.0/0" in text
        assert "VirtualAppliance" in text

    def test_the_custom_write_role_cannot_delete(self):
        text = _read_text(MAIN_TEMPLATE)
        assert "blobs/delete" not in text
        assert "blobs/add/action" in text
        assert "'*'" not in text

    def test_roles_pull_but_cannot_push_images(self):
        text = _read_text(MODULES / "workload.bicep")
        assert "7f951dda-4ed3-4680-a7ca-43fe172d538d" in text  # AcrPull
        assert "8311e382-0749-4cb8-b61a-304f252e45ec" not in text  # AcrPush

    def test_data_grants_are_scoped_to_containers_not_the_account(self):
        text = _read_text(MODULES / "storage_access.bicep")
        assert "scope: containers[" in text
        assert "scope: storageAccount" not in text

    def test_the_resource_group_carries_a_delete_lock(self):
        text = _read_text(MODULES / "observability.bicep")
        assert "level: 'CanNotDelete'" in text

    def test_egress_decisions_are_logged(self):
        text = _read_text(MODULES / "observability.bicep")
        assert "diagnosticSettings" in text
        assert "categoryGroup: 'allLogs'" in text

    def test_the_deployment_scope_allows_the_custom_role(self):
        assert "targetScope = 'subscription'" in _read_text(MAIN_TEMPLATE)

    def test_outputs_carry_no_case_material(self):
        text = _read_text(MAIN_TEMPLATE)
        outputs = [line for line in text.splitlines() if line.startswith("output ")]
        assert outputs
        for line in outputs:
            lowered = line.lower()
            for forbidden in ("case", "label", "verdict", "content", "text", "blob"):
                assert forbidden not in lowered


class TestTheGpuChoiceIsEvidenceBacked:
    def test_the_profile_name_comes_from_the_recorded_discovery(self, address_plan):
        text = _read_text(MAIN_TEMPLATE)
        assert "addressPlan.region_evidence.gpu_profile_found.name" in text
        assert address_plan["region_evidence"]["gpu_profile_found"]["name"] not in text

    def test_only_the_parser_bearing_stage_gets_a_gpu(self):
        text = _read_text(MODULES / "workload.bicep")
        assert "param gpuRoles array = [ 'stage_p' ]" in text

    def test_the_discovery_command_is_recorded(self, address_plan):
        assert "workload-profile list-supported" in (
            address_plan["region_evidence"]["gpu_discovery_command"]
        )
