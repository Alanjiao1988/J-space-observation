"""Tests for the Phase 1.2H-R1 cloud private-source access gate.

The gate's job is to make a narrow, honest claim -- that the bytes in the sealed
prefix are the bytes the committed public record says were sealed there -- while
making the broader claims structurally impossible. These tests exist to attack
the second half. Each one mutates a single condition and asserts the probe
refuses, because a gate that only passes when everything is correct has not been
shown to fail when something is wrong.

Nothing here touches Azure, the network, or any private material. Every fixture
is synthetic, and the two live constants that appear (the registered private IP
and the designated client-id shape) are already public in the committed decision
record.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DECISION_RECORD = ROOT / "docs" / "phase1_2h_r1_access_decision_record.json"
RECEIPT_SCHEMA = ROOT / "docs" / "phase1_2h_r1_access_receipt.schema.json"
REFUSAL_SCHEMA = ROOT / "docs" / "phase1_2h_r1_access_refusal_receipt.schema.json"
PROBE_PATH = SCRIPTS / "phase1_2h_r1_private_source_probe.py"
VALIDATOR_PATH = SCRIPTS / "phase1_2h_r1_receipt_validator.py"
COMMITTED_RECEIPT = ROOT / "docs" / "phase1_2h_r1_access_receipt_003.json"

#: The designated read-only identity, as frozen in the decision record. It is a
#: public Azure resource identifier, not a credential. Tests read it from the
#: record rather than restating it, so a record edit cannot silently diverge
#: from what the tests assert.
DESIGNATED_CLIENT_ID = json.loads(DECISION_RECORD.read_text(encoding="utf-8"))[
    "identity_rule"
]["designated_identity"]["client_id"]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = _load(PROBE_PATH, "_p12hr1_probe")
validator = _load(VALIDATOR_PATH, "_p12hr1_validator")


@pytest.fixture(scope="module")
def record() -> dict:
    return json.loads(DECISION_RECORD.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def expected(record: dict) -> list[tuple[str, int, str]]:
    return probe.expected_members(record)


@pytest.fixture()
def mutable_record(record: dict) -> dict:
    return copy.deepcopy(record)


# --- 1. The frozen bindings load, and reproduce the public anchors ----------


def test_expected_member_set_matches_the_committed_seal_record(expected):
    assert len(expected) == 12
    assert sum(size for _, size, _ in expected) == 396613
    assert len({digest for _, _, digest in expected}) == 12


def test_members_digest_is_reproducible_from_the_committed_evidence(record, expected):
    assert (
        probe.members_digest(expected)
        == record["expected_evidence_binding"]["members_digest"]
    )


def test_expected_evidence_digest_is_enforced(mutable_record):
    mutable_record["expected_evidence_binding"]["sha256"] = "0" * 64
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.expected_members(mutable_record)
    assert exc.value.reason_code == "EXPECTED_EVIDENCE_DIGEST_MISMATCH"


def test_expected_count_disagreement_is_refused(mutable_record):
    mutable_record["source_binding"]["expected_object_count"] = 11
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.expected_members(mutable_record)
    assert exc.value.invariant == "EXPECTED_COUNT_DISAGREES"


def test_expected_total_bytes_disagreement_is_refused(mutable_record):
    mutable_record["source_binding"]["expected_total_bytes"] = 396612
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.expected_members(mutable_record)
    assert exc.value.invariant == "EXPECTED_TOTAL_BYTES"


def test_a_record_missing_a_required_block_is_refused(tmp_path, record):
    broken = copy.deepcopy(record)
    del broken["byte_only_rule"]
    path = tmp_path / "rec.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.load_decision_record(path)
    assert exc.value.invariant == "RECORD_BLOCK_MISSING"


def test_a_record_with_a_foreign_schema_version_is_refused(tmp_path, record):
    broken = copy.deepcopy(record)
    broken["schema_version"] = "something-else/v9"
    path = tmp_path / "rec.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(probe.ProbeRefusal):
        probe.load_decision_record(path)


# --- 2. Source binding cannot be redirected from outside the freeze --------


@pytest.mark.parametrize(
    "field,invariant",
    [
        ("account", "ACCOUNT_OVERRIDE"),
        ("container", "CONTAINER_OVERRIDE"),
        ("prefix", "PREFIX_OVERRIDE"),
    ],
)
def test_cli_override_of_the_source_binding_is_refused(field, invariant):
    args = probe._parse_args(
        [
            "--client-id",
            "x",
            "--execution-id",
            "e",
            "--freeze-commit",
            "c",
            "--image-digest",
            "d",
            f"--{field}",
            "attacker-supplied",
        ]
    )
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_override(args)
    assert exc.value.reason_code == "SOURCE_BINDING_OVERRIDE_ATTEMPTED"
    assert exc.value.invariant == invariant


@pytest.mark.parametrize("name", probe.FORBIDDEN_ENV_VARS)
def test_an_ambient_or_secret_credential_env_var_is_refused(name):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_environment_clean({name: "set"})
    assert exc.value.reason_code == "CREDENTIAL_TYPE_FORBIDDEN"


def test_a_clean_environment_passes():
    probe.assert_environment_clean({"PATH": "/usr/bin", "HOME": "/home/probe"})


# --- 2b. Defects found by executing the gate, not by reasoning about it -----


@pytest.mark.parametrize(
    "name", ["MSI_ENDPOINT", "MSI_SECRET", "IDENTITY_ENDPOINT", "IDENTITY_HEADER"]
)
def test_the_platform_managed_identity_endpoint_is_not_forbidden(name):
    # The first live gate execution refused with FORBIDDEN_ENV_VAR because the
    # denylist included MSI_ENDPOINT and MSI_SECRET. Those are how Container
    # Apps provides the managed identity the freeze *requires*, so the rule
    # forbade the required credential. Correcting a self-contradictory rule is
    # not the same as relaxing a requirement, and this test pins the
    # distinction so the contradiction cannot come back.
    assert name not in probe.FORBIDDEN_ENV_VARS
    probe.assert_environment_clean({name: "http://localhost:42356/msi/token"})


@pytest.mark.parametrize(
    "name",
    [
        "AZURE_CLIENT_SECRET",
        "AZURE_STORAGE_KEY",
        "AZURE_STORAGE_SAS_TOKEN",
        "AZURE_STORAGE_CONNECTION_STRING",
    ],
)
def test_secret_bearing_variables_are_still_refused(name):
    with pytest.raises(probe.ProbeRefusal):
        probe.assert_environment_clean({name: "secret"})


def test_an_environment_refusal_names_the_variable_but_never_its_value():
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_environment_clean({"AZURE_CLIENT_SECRET": "hunter2-do-not-leak"})
    assert exc.value.detail == "AZURE_CLIENT_SECRET"
    assert "hunter2-do-not-leak" not in str(exc.value)


def test_a_refusal_receipt_carries_the_detail_without_the_value():
    args = probe._parse_args(
        ["--client-id", DESIGNATED_CLIENT_ID, "--execution-id", "e", "--freeze-commit", "c", "--image-digest", "d"]
    )
    refusal = probe.ProbeRefusal(
        "CREDENTIAL_TYPE_FORBIDDEN", "FORBIDDEN_ENV_VAR", "AZURE_CLIENT_SECRET"
    )
    receipt = probe._refusal_receipt(refusal, "2026-01-01T00:00:00Z", args)
    assert receipt["execution"]["detail"] == "AZURE_CLIENT_SECRET"
    assert receipt["refused"] is True
    # The refusal receipt is now a closed, schema-validated document. Its
    # first draft was an ad-hoc flat object that carried the success receipt's
    # schema_version and was never validated -- independent Audit A (A-09) and
    # independent Audit B (B-08).
    validator.validate_receipt(receipt, REFUSAL_SCHEMA)


def test_the_refusal_receipt_schema_is_closed_everywhere():
    validator.load_schema(REFUSAL_SCHEMA)


def test_a_refusal_receipt_cannot_carry_prose():
    # The invariant and detail patterns are what make this document
    # structurally incapable of being a content channel.
    receipt = probe._refusal_receipt(
        probe.ProbeRefusal("INTERNAL_REFUSAL", "X"), "2026-01-01T00:00:00Z", None
    )
    receipt["execution"]["invariant"] = "case_0007 span=Yes offset=412"
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_receipt(receipt, REFUSAL_SCHEMA)


def test_a_refusal_before_argument_parsing_still_emits_a_valid_receipt():
    receipt = probe._refusal_receipt(
        probe.ProbeRefusal("INTERNAL_REFUSAL", "ARGUMENT_PARSE_FAILED"),
        "2026-01-01T00:00:00Z",
        None,
    )
    assert receipt["execution"]["execution_id"] == "unparsed"
    validator.validate_receipt(receipt, REFUSAL_SCHEMA)


def test_a_bad_argument_produces_a_receipt_not_a_usage_message(capsys):
    # argparse exits 2 with usage text on stderr, which is indistinguishable
    # by exit code from a genuine refusal and carries no receipt at all.
    code = probe.main(["--not-a-real-flag"])
    captured = capsys.readouterr()
    emitted = json.loads(captured.out.strip().splitlines()[-1])
    assert code == 2
    assert emitted["execution"]["invariant"] == "ARGUMENT_PARSE_FAILED"
    validator.validate_receipt(emitted, REFUSAL_SCHEMA)


def test_a_refusal_after_partial_streaming_reports_the_reads_it_performed():
    # A refusal raised after objects were already streamed must still report
    # how many data-plane content reads occurred, or the append-only access
    # ledger cannot record what actually happened. Independent Audit B (B-08).
    probe._reset_progress()
    try:
        probe.PROGRESS["azure_data_plane_content_reads"] = 7
        probe.PROGRESS["list_operations"] = 1
        receipt = probe._refusal_receipt(
            probe.ProbeRefusal("DIGEST_MISMATCH", "OBJECT_DIGEST"),
            "2026-01-01T00:00:00Z",
            None,
        )
    finally:
        probe._reset_progress()
    assert receipt["progress_counters"]["azure_data_plane_content_reads"] == 7
    assert receipt["progress_counters"]["list_operations"] == 1
    assert receipt["progress_counters"]["semantic_input_reads"] == 0
    validator.validate_receipt(receipt, REFUSAL_SCHEMA)


def test_a_refusal_receipt_cannot_report_a_semantic_read():
    receipt = probe._refusal_receipt(
        probe.ProbeRefusal("INTERNAL_REFUSAL", "X"), "2026-01-01T00:00:00Z", None
    )
    receipt["progress_counters"]["semantic_input_reads"] = 1
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_receipt(receipt, REFUSAL_SCHEMA)


def test_a_refusal_without_detail_omits_the_field():
    args = probe._parse_args(
        ["--client-id", DESIGNATED_CLIENT_ID, "--execution-id", "e", "--freeze-commit", "c", "--image-digest", "d"]
    )
    receipt = probe._refusal_receipt(
        probe.ProbeRefusal("MEMBER_SET_MISMATCH", "MEMBER_SET"), "2026-01-01T00:00:00Z", args
    )
    assert "detail" not in receipt["execution"]


@pytest.mark.parametrize(
    "env",
    [
        {"AZURE_LOG_LEVEL": "debug"},
        {"AZURE_LOG_LEVEL": "TRACE"},
        {"AZURE_SDK_LOGGING_ENABLE_BODY": "true"},
    ],
)
def test_verbose_sdk_logging_is_refused(env):
    with pytest.raises(probe.ProbeRefusal):
        probe.assert_verbose_logging_disabled(env)


def test_ordinary_sdk_logging_is_allowed():
    probe.assert_verbose_logging_disabled({"AZURE_LOG_LEVEL": "warning"})


# --- 3. Identity ------------------------------------------------------------


def test_the_designated_managed_identity_is_accepted(record):
    block = probe.check_identity(record, DESIGNATED_CLIENT_ID, "ManagedIdentityCredential")
    # NOT "READ_ONLY_CONFIRMED". The probe holds no permission to read role
    # assignments, so it cannot confirm read-only from inside the job.
    # Independent Audit A (A-02) found the previous unconditional
    # READ_ONLY_CONFIRMED was asserted on the basis of no check at all.
    assert block["effective_read_only_verdict"] == "NOT_CONFIRMED_IN_JOB"
    assert block["forbidden_credential_types_absent"] is True


def test_an_undesignated_client_id_is_refused(record):
    # The concrete risk: id-jspace-aca-acrpull-sea is write-capable and exists
    # in the same subscription. A receipt must be able to tell them apart.
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_identity(
            record, "11111111-2222-3333-4444-555555555555", "ManagedIdentityCredential"
        )
    assert exc.value.reason_code == "IDENTITY_MISMATCH"
    assert exc.value.invariant == "CLIENT_ID_NOT_DESIGNATED"


def test_an_identity_refusal_carries_neither_the_supplied_nor_expected_id(record):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_identity(
            record, "11111111-2222-3333-4444-555555555555", "ManagedIdentityCredential"
        )
    rendered = str(exc.value)
    assert "11111111" not in rendered
    assert DESIGNATED_CLIENT_ID not in rendered


def test_a_record_without_a_designated_client_id_is_refused(mutable_record):
    del mutable_record["identity_rule"]["designated_identity"]["client_id"]
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_identity(
            mutable_record, DESIGNATED_CLIENT_ID, "ManagedIdentityCredential"
        )
    assert exc.value.invariant == "DESIGNATED_CLIENT_ID_ABSENT"


@pytest.mark.parametrize("bad", ["DefaultAzureCredential", "AzureCliCredential", "ClientSecretCredential"])
def test_a_forbidden_credential_type_is_refused(record, bad):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_identity(record, DESIGNATED_CLIENT_ID, bad)
    assert exc.value.reason_code == "CREDENTIAL_TYPE_FORBIDDEN"


def test_a_system_assigned_identity_is_refused_via_the_missing_client_id(record):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_identity(record, "", "ManagedIdentityCredential")
    assert exc.value.invariant == "CLIENT_ID_ABSENT"


def test_every_credential_the_freeze_forbids_is_enforced_by_the_probe(record):
    declared = set(record["identity_rule"]["forbidden_credential_types"])
    # These two are configurations rather than class names and are enforced
    # structurally instead; the probe documents the same carve-out.
    declared -= {"ConnectionString", "SystemAssignedManagedIdentity"}
    assert declared <= set(probe.FORBIDDEN_CREDENTIAL_TYPES)


def test_a_freeze_that_drifted_away_from_the_credential_rule_is_refused(mutable_record):
    mutable_record["identity_rule"]["required_credential_type"] = "AnythingGoes"
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_identity(mutable_record, "a-client-id", "ManagedIdentityCredential")
    assert exc.value.invariant == "CREDENTIAL_RULE_DRIFT"


def test_a_freeze_that_forbids_something_the_probe_ignores_is_refused(mutable_record):
    mutable_record["identity_rule"]["forbidden_credential_types"].append("NovelCredential")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_identity(mutable_record, "a-client-id", "ManagedIdentityCredential")
    assert exc.value.invariant == "FORBIDDEN_LIST_NOT_ENFORCED"


# --- 4. Endpoint ------------------------------------------------------------


def test_the_registered_private_endpoint_is_accepted(record):
    block = probe.check_endpoint(record, "Unknown", "10.80.2.4")
    assert block["resolved_matches_expected_private_ip"] is True
    assert block["privatelink_path_confirmed"] is True


def test_a_public_storage_endpoint_is_refused(record):
    # "Enabled" is not an in-job observation either; the probe refuses any
    # value other than "Unknown" because publicNetworkAccess is a control-plane
    # property it holds no role to read. Independent Audit A (A-03) found the
    # previous call site passed a literal "Disabled", making the check
    # tautological while the receipt presented it as observed.
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Enabled", "10.80.2.4")
    assert exc.value.invariant == "PNA_NOT_OBSERVABLE_IN_JOB"


def test_a_literal_disabled_is_refused_rather_than_echoed(record):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Disabled", "10.80.2.4")
    assert exc.value.invariant == "PNA_NOT_OBSERVABLE_IN_JOB"


def test_the_receipt_records_who_observed_public_network_access(record):
    block = probe.check_endpoint(record, "Unknown", "10.80.2.4")
    assert block["public_network_access"] == "Unknown"
    assert block["public_network_access_observed_by"] == (
        "operator_control_plane_read_before_run"
    )


def test_a_second_resolved_address_defeats_the_only_claim(record):
    # resolved_ip_matches_only asserts the expected address is the ONLY one.
    # gethostbyname returns a single address and cannot establish that, which
    # independent Audit A raised as A-12.
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Unknown", ["10.80.2.4", "10.80.2.9"])
    assert exc.value.reason_code == "ENDPOINT_IP_MISMATCH"


def test_an_empty_resolution_is_refused(record):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Unknown", [])
    assert exc.value.invariant == "NO_ADDRESS_RESOLVED"


def test_resolve_endpoint_returns_the_full_address_set():
    resolved = probe.resolve_endpoint(
        "example.invalid", resolver=lambda _: ["10.0.0.2", "10.0.0.1", "10.0.0.1"]
    )
    assert resolved == ["10.0.0.1", "10.0.0.2"]


def test_a_public_ip_is_refused(record):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Unknown", "20.43.121.10")
    assert exc.value.reason_code == "ENDPOINT_NOT_PRIVATE"
    assert exc.value.invariant == "PUBLIC_ADDRESS"


def test_a_private_ip_outside_the_project_vnet_is_refused(record):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Unknown", "192.168.4.4")
    assert exc.value.invariant == "ADDRESS_OUTSIDE_PROJECT_VNET"


def test_an_unregistered_address_inside_the_vnet_is_still_refused(record):
    # Being inside 10.80.0.0/16 is not enough. A different private endpoint in
    # the same VNet is a different endpoint.
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Unknown", "10.80.2.5")
    assert exc.value.reason_code == "ENDPOINT_IP_MISMATCH"


def test_an_endpoint_refusal_does_not_carry_the_observed_address(record):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Unknown", "10.80.9.99")
    assert "10.80.9.99" not in str(exc.value)


# --- 5. Membership ----------------------------------------------------------


def _names(record: dict, expected) -> list[str]:
    prefix = record["source_binding"]["exact_prefix"].rstrip("/") + "/"
    return [prefix + name for name, _, _ in expected]


def test_the_exact_expected_member_set_is_accepted(record, expected):
    block = probe.compare_membership(record, expected, _names(record, expected))
    assert block["member_sets_equal"] is True
    assert block["observed_count"] == 12
    assert block["unexpected_member_count"] == 0
    assert block["missing_member_count"] == 0


def test_an_extra_object_in_the_prefix_is_refused(record, expected):
    names = _names(record, expected)
    names.append(names[0].rsplit("/", 1)[0] + "/unexpected.bin")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.compare_membership(record, expected, names)
    assert exc.value.reason_code == "MEMBER_COUNT_MISMATCH"


def test_a_missing_object_is_refused(record, expected):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.compare_membership(record, expected, _names(record, expected)[:-1])
    assert exc.value.reason_code == "MEMBER_COUNT_MISMATCH"


def test_a_renamed_object_is_refused_even_at_the_right_count(record, expected):
    names = _names(record, expected)
    names[0] = names[0] + ".renamed"
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.compare_membership(record, expected, names)
    assert exc.value.reason_code == "MEMBER_SET_MISMATCH"


def test_enumeration_leaking_outside_the_registered_prefix_is_refused(record, expected):
    names = _names(record, expected)
    names.append("evaluator_sets/some_other_prefix/object.bin")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.compare_membership(record, expected, names)
    assert exc.value.invariant == "OBSERVED_OUTSIDE_PREFIX"


def test_membership_result_carries_no_member_name(record, expected):
    block = probe.compare_membership(record, expected, _names(record, expected))
    blob = json.dumps(block)
    for name, _, _ in expected:
        assert name not in blob


# --- 6. Streaming integrity -------------------------------------------------


def test_streaming_folds_chunks_without_accumulating_them():
    digest, size = probe.stream_object_digest([b"abc", b"def"])
    import hashlib

    assert digest == hashlib.sha256(b"abcdef").hexdigest()
    assert size == 6


def test_matching_bytes_pass(expected):
    block = probe.verify_streamed(expected, list(expected))
    assert block["all_digests_match"] is True
    assert block["all_sizes_match"] is True
    assert block["total_bytes_streamed"] == 396613
    assert block["decode_attempts"] == 0
    assert block["persist_attempts"] == 0


def test_a_size_mismatch_is_refused(expected):
    observed = list(expected)
    name, size, digest = observed[0]
    observed[0] = (name, size + 1, digest)
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.verify_streamed(expected, observed)
    assert exc.value.reason_code == "OBJECT_SIZE_MISMATCH"


def test_a_digest_mismatch_is_refused(expected):
    observed = list(expected)
    name, size, _ = observed[0]
    observed[0] = (name, size, "f" * 64)
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.verify_streamed(expected, observed)
    assert exc.value.reason_code == "OBJECT_DIGEST_MISMATCH"


def test_the_aggregate_digest_is_order_independent(expected):
    forward = probe.verify_streamed(expected, list(expected))
    backward = probe.verify_streamed(expected, list(reversed(expected)))
    assert forward["observed_aggregate_digest"] == backward["observed_aggregate_digest"]


def test_the_aggregate_digest_matches_the_independently_computed_anchor(expected):
    block = probe.verify_streamed(expected, list(expected))
    assert (
        block["observed_aggregate_digest"]
        == "e1364afcac87516813d33a4e9fb3e370769487ab2f3ca47a08a3b4059db14e71"
    )


# --- 7. Structural byte-only and read-only guarantees -----------------------


def test_the_probe_source_contains_no_mutating_blob_operation():
    assert probe.assert_no_write_calls_in_source() > 0


def test_a_source_that_calls_a_write_method_is_refused(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("def go(client):\n    client.upload_blob(b'x')\n", encoding="utf-8")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_write_calls_in_source(bad)
    assert exc.value.invariant == "WRITE_CALL_IN_SOURCE"


def test_a_source_that_imports_a_forbidden_credential_is_refused(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text(
        "from azure.identity import DefaultAzureCredential\n", encoding="utf-8"
    )
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_write_calls_in_source(bad)
    assert exc.value.invariant == "FORBIDDEN_IMPORT_IN_SOURCE"


def test_a_forbidden_credential_symbol_in_the_namespace_is_refused():
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_forbidden_symbols({"DefaultAzureCredential": object()})
    assert exc.value.reason_code == "CREDENTIAL_TYPE_FORBIDDEN"


def test_the_live_probe_namespace_is_clean():
    probe.assert_no_forbidden_symbols()


def test_the_probe_never_decodes_streamed_bytes():
    tree = ast.parse(PROBE_PATH.read_text(encoding="utf-8"))
    streamer = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "stream_object_digest"
    )
    # Body only: the return annotation legitimately names ``str``, and a type
    # annotation cannot decode anything.
    for statement in streamer.body:
        for node in ast.walk(statement):
            if isinstance(node, ast.Attribute):
                assert node.attr not in {"decode", "read", "write", "text", "content"}
            if isinstance(node, ast.Name):
                assert node.id not in {"str", "print", "open", "repr", "bytes"}


def test_the_probe_does_not_import_the_package_that_eagerly_loads_the_parser():
    # jspace_observation/__init__ imports the legacy parser eagerly. The probe
    # must not pull parser code into the one process that touches sealed bytes.
    #
    # This was previously a substring search for "jspace_observation" in the
    # source text, which independent Audit B (B-06) correctly called out: a
    # string search proves nothing about imports, cannot see a deferred import
    # inside a function, and breaks the moment the module legitimately *names*
    # the package in a denylist. The check is now structural.
    tree = ast.parse(PROBE_PATH.read_text(encoding="utf-8"))
    forbidden_roots = {"jspace_observation", "torch", "transformers"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # A relative import would resolve through the package __init__,
                # which is exactly the eager-parser path being excluded.
                imported.add("<relative>")
            imported.add((node.module or "").split(".")[0])
    assert not (imported & forbidden_roots), sorted(imported & forbidden_roots)
    assert "<relative>" not in imported


def test_the_probe_refuses_a_source_that_imports_the_eager_parser_package(tmp_path):
    # The structural check above describes the probe as it is. This one proves
    # the probe would refuse to run if a future edit added such an import,
    # which is the property that keeps the claim true over time.
    bad = tmp_path / "bad.py"
    bad.write_text("import jspace_observation\n", encoding="utf-8")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_write_calls_in_source(bad)
    assert exc.value.invariant == "FORBIDDEN_IMPORT_IN_SOURCE"


# --- Evasions closed after independent Audit A finding A-06 -----------------


def test_a_write_method_reached_through_a_string_constant_is_refused(tmp_path):
    # getattr(client, "upload_blob") has no Attribute node naming the method,
    # so an AST check that looks only at attributes and imports passes it.
    bad = tmp_path / "bad.py"
    bad.write_text(
        "def go(client):\n    return getattr(client, 'upload_blob')(b'x')\n",
        encoding="utf-8",
    )
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_write_calls_in_source(bad)
    assert exc.value.invariant == "DYNAMIC_WRITE_NAME_IN_SOURCE"


def test_an_aliased_module_import_of_a_forbidden_credential_is_refused(tmp_path):
    # import azure.identity as ai; ai.DefaultAzureCredential() has no
    # ImportFrom node, so checking only ImportFrom passes it.
    bad = tmp_path / "bad.py"
    bad.write_text(
        "import azure.identity as ai\n\n\ndef go():\n    return ai.DefaultAzureCredential()\n",
        encoding="utf-8",
    )
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_write_calls_in_source(bad)
    assert exc.value.invariant == "WRITE_CALL_IN_SOURCE"


@pytest.mark.parametrize("call", ["eval", "exec", "compile", "__import__"])
def test_a_dynamic_access_builtin_is_refused(tmp_path, call):
    bad = tmp_path / "bad.py"
    bad.write_text(f"def go(s):\n    return {call}(s)\n", encoding="utf-8")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_write_calls_in_source(bad)
    assert exc.value.invariant == "WRITE_CALL_IN_SOURCE"


@pytest.mark.parametrize("method", ["decode", "b64encode", "hexlify"])
def test_a_decode_of_object_bytes_is_refused_at_source_level(tmp_path, method):
    # This is what makes the pinned decode_attempts counter mean something.
    # Independent Audit A (A-04) observed that the counter was a hardcoded
    # literal and the schema constrained only what could be reported.
    bad = tmp_path / "bad.py"
    bad.write_text(f"def go(chunk):\n    return chunk.{method}()\n", encoding="utf-8")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_write_calls_in_source(bad)
    assert exc.value.invariant == "WRITE_CALL_IN_SOURCE"


@pytest.mark.parametrize("method", ["write_text", "write_bytes", "writelines"])
def test_a_persistence_call_is_refused_at_source_level(tmp_path, method):
    # Likewise for persist_attempts.
    bad = tmp_path / "bad.py"
    bad.write_text(f"def go(p, chunk):\n    return p.{method}(chunk)\n", encoding="utf-8")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_write_calls_in_source(bad)
    assert exc.value.invariant == "WRITE_CALL_IN_SOURCE"


@pytest.mark.parametrize("root", ["pickle", "subprocess", "shutil", "urllib", "requests"])
def test_a_persistence_or_exfiltration_import_is_refused(tmp_path, root):
    bad = tmp_path / "bad.py"
    bad.write_text(f"import {root}\n", encoding="utf-8")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_write_calls_in_source(bad)
    assert exc.value.invariant == "FORBIDDEN_IMPORT_IN_SOURCE"


def test_the_probe_does_not_refuse_itself():
    # The FORBIDDEN_* tuples necessarily contain the very names being
    # forbidden. If the declaration carve-out were wrong, the probe would
    # refuse every run -- a self-defeating check rather than a safe one.
    assert probe.assert_no_write_calls_in_source() > 1000


# --- Image payload completeness (independent Audit B, B-06) -----------------

DOCKERFILE = ROOT / "Dockerfile.phase1-2h-r1-access"
PAYLOAD_MANIFEST = ROOT / "infra" / "azure" / "phase1_2h_r1_image_payload.json"

#: Files the Dockerfile copies that are deliberately not digest-pinned payload:
#: the pip requirements closure (already hash-pinned by pip itself via
#: --require-hashes) and the manifest, which cannot contain its own digest.
NON_PAYLOAD_COPIES = {
    "requirements-parser-v2-eval.txt",
    "infra/azure/phase1_2h_r1_image_payload.json",
}


def _dockerfile_copy_sources() -> set[str]:
    """Every source path the Dockerfile copies into the image."""

    text = DOCKERFILE.read_text(encoding="utf-8")
    # Join backslash continuations so a multi-line COPY is one logical line.
    text = text.replace("\\\n", " ")
    sources: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.upper().startswith("COPY "):
            continue
        parts = stripped.split()[1:]
        # The last token is the destination.
        sources.update(parts[:-1])
    return sources


def test_the_dockerfile_copies_exactly_the_manifested_payload():
    # A Dockerfile addition could otherwise bake in a parser module, an
    # evaluator source, or private material without failing any check, because
    # the manifest verifies the files it lists rather than the files present.
    manifest = json.loads(PAYLOAD_MANIFEST.read_text(encoding="utf-8"))
    manifested = {entry["path"] for entry in manifest["payload"]}
    copied = _dockerfile_copy_sources()
    assert copied == manifested | NON_PAYLOAD_COPIES, {
        "copied_but_not_manifested": sorted(copied - manifested - NON_PAYLOAD_COPIES),
        "manifested_but_not_copied": sorted(manifested - copied),
    }


def test_no_parser_bearing_path_is_copied_into_the_image():
    parser_names = (
        "eval_parsing.py",
        "eval_parsing_v2.py",
        "eval_parsing_v3.py",
        "src/jspace_observation",
    )
    copied = " ".join(sorted(_dockerfile_copy_sources()))
    for name in parser_names:
        assert name not in copied


def test_every_runtime_schema_the_probe_reads_is_in_the_payload():
    # The probe reads both receipt schemas at runtime. A schema that is not
    # baked into the image turns a refusal path into a crash.
    manifest = json.loads(PAYLOAD_MANIFEST.read_text(encoding="utf-8"))
    manifested = {entry["path"] for entry in manifest["payload"]}
    for schema in (RECEIPT_SCHEMA, REFUSAL_SCHEMA, DECISION_RECORD):
        assert schema.relative_to(ROOT).as_posix() in manifested


def test_the_payload_manifest_is_current():
    manifest = json.loads(PAYLOAD_MANIFEST.read_text(encoding="utf-8"))
    for entry in manifest["payload"]:
        raw = (ROOT / entry["path"]).read_bytes()
        lf = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        assert hashlib.sha256(lf).hexdigest() == entry["sha256"], entry["path"]


def test_the_receipt_validator_imports_only_the_standard_library():
    tree = ast.parse(VALIDATOR_PATH.read_text(encoding="utf-8"))
    allowed = {"json", "re", "pathlib", "typing", "__future__", "argparse"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in allowed
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert (node.module or "").split(".")[0] in allowed


# --- 8. Receipt schema ------------------------------------------------------


@pytest.fixture()
def receipt(record, expected) -> dict:
    names = _names(record, expected)
    return probe.build_receipt(
        record=record,
        execution_id="ex-0001",
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:05:00Z",
        freeze_commit="a" * 40,
        image_digest="sha256:" + "b" * 64,
        decision_record_sha256="c" * 64,
        probe_source_sha256="d" * 64,
        identity_block=probe.check_identity(
            record, DESIGNATED_CLIENT_ID, "ManagedIdentityCredential"
        ),
        endpoint_block=probe.check_endpoint(record, "Unknown", "10.80.2.4"),
        membership_block=probe.compare_membership(record, expected, names),
        streaming_block=probe.verify_streamed(expected, list(expected)),
        list_operations=1,
        invariants_checked=12,
    )


def test_a_well_formed_receipt_validates(receipt):
    validator.validate_receipt(receipt, RECEIPT_SCHEMA)


def test_the_committed_schema_is_closed_everywhere():
    validator.load_schema(RECEIPT_SCHEMA)


def test_an_undeclared_receipt_field_is_rejected(receipt):
    receipt["membership"]["member_names"] = ["leaked.md"]
    with pytest.raises(validator.ReceiptValidationError) as exc:
        validator.validate_receipt(receipt, RECEIPT_SCHEMA)
    assert "undeclared" in str(exc.value)


@pytest.mark.parametrize(
    "counter",
    [
        "azure_data_plane_writes",
        "semantic_input_reads",
        "semantic_label_reads",
        "parser_invocations",
        "predictions_generated",
    ],
)
def test_a_nonzero_forbidden_counter_cannot_produce_a_valid_receipt(receipt, counter):
    receipt["counters"][counter] = 1
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_receipt(receipt, RECEIPT_SCHEMA)


@pytest.mark.parametrize("field", ["decode_attempts", "persist_attempts"])
def test_a_decode_or_persist_attempt_cannot_produce_a_valid_receipt(receipt, field):
    receipt["streaming"][field] = 1
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_receipt(receipt, RECEIPT_SCHEMA)


def test_a_free_text_reason_code_is_rejected(receipt):
    receipt["execution"]["reason_code"] = "it seemed fine to me"
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_receipt(receipt, RECEIPT_SCHEMA)


def test_an_execution_without_an_id_is_rejected(receipt):
    del receipt["execution"]["execution_id"]
    with pytest.raises(validator.ReceiptValidationError) as exc:
        validator.validate_receipt(receipt, RECEIPT_SCHEMA)
    assert "execution_id" in str(exc.value)


@pytest.mark.parametrize(
    "field",
    [
        "access_protocol_freeze_commit",
        "image_digest",
        "decision_record_sha256",
        "expected_evidence_sha256",
        "probe_source_sha256",
    ],
)
def test_a_receipt_missing_a_provenance_binding_is_rejected(receipt, field):
    del receipt["provenance"][field]
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_receipt(receipt, RECEIPT_SCHEMA)


def test_the_receipt_carries_no_member_name_and_no_object_content(receipt, expected):
    blob = json.dumps(receipt)
    for name, _, _ in expected:
        assert name not in blob
    assert "text" not in blob
    assert "content" not in blob.replace("azure_data_plane_content_reads", "")


def test_counters_are_derived_from_streaming_evidence_not_asserted(receipt):
    assert receipt["counters"]["azure_data_plane_content_reads"] == 12
    assert receipt["counters"]["byte_only_integrity_verifications"] == 12
    assert receipt["counters"]["azure_data_plane_writes"] == 0
    assert receipt["counters"]["semantic_input_reads"] == 0
    assert receipt["counters"]["semantic_label_reads"] == 0
    assert receipt["counters"]["parser_invocations"] == 0
    assert receipt["counters"]["predictions_generated"] == 0


# --- 9. The validator itself fails closed -----------------------------------


def test_an_unknown_schema_keyword_is_rejected(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(
        json.dumps({"type": "object", "additionalProperties": False, "oneOf": []}),
        encoding="utf-8",
    )
    with pytest.raises(validator.ReceiptSchemaError) as exc:
        validator.load_schema(path)
    assert "unsupported schema keyword" in str(exc.value)


def test_an_open_object_schema_is_rejected(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    with pytest.raises(validator.ReceiptSchemaError):
        validator.load_schema(path)


def test_a_required_field_without_a_property_schema_is_rejected(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(
        json.dumps(
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": ["ghost"],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(validator.ReceiptSchemaError):
        validator.load_schema(path)


def test_booleans_do_not_satisfy_integer_bounds():
    schema = {"type": "integer", "maximum": 0}
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_instance(True, schema)


def test_a_timestamp_without_an_offset_is_rejected():
    schema = {"type": "string", "format": "date-time"}
    validator.validate_instance("2026-01-01T00:00:00Z", schema)
    with pytest.raises(validator.ReceiptValidationError):
        validator.validate_instance("2026-01-01 00:00:00", schema)


# --- 10. Audit C remediations ------------------------------------------------
#
# Independent Audit C reviewed commit 393ff3e and returned BLOCKED. These tests
# pin the fixes so a later edit cannot quietly restore the defect. Each names
# the finding it belongs to.


def test_the_byte_handler_admits_only_digest_calls():
    # C-06. The frozen rule is "object bytes reach a hash and nothing else".
    # The module-wide name ban cannot express it, because reading the *public*
    # committed member list legitimately calls .splitlines() and json.loads().
    # The rule is a property of one function, so it is checked there.
    assert probe.assert_byte_handling_is_digest_only() > 0


@pytest.mark.parametrize("name", probe.FORBIDDEN_INTERPRETATION_NAMES)
def test_any_interpreting_call_inside_the_byte_handler_is_refused(name, tmp_path):
    source = (
        "import hashlib\n"
        f"def {probe.BYTE_HANDLING_FUNCTION}(client, blob):\n"
        "    digest = hashlib.sha256()\n"
        "    for chunk in client.chunks():\n"
        "        digest.update(chunk)\n"
        f"        {name}(chunk)\n"
        "    return digest.hexdigest(), 0\n"
    )
    path = tmp_path / "probe_like.py"
    path.write_text(source, encoding="utf-8")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_byte_handling_is_digest_only(path)
    assert exc.value.invariant in {
        "NON_DIGEST_CALL_ON_BYTES",
        "BYTE_DERIVATIVE_IN_HANDLER",
    }


def test_a_renamed_byte_handler_is_a_refusal_not_a_skip(tmp_path):
    # A check that silently guards nothing is worse than no check: it reads as
    # evidence. Renaming the function must fail loudly.
    path = tmp_path / "probe_like.py"
    path.write_text("def something_else():\n    return 1\n", encoding="utf-8")
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_byte_handling_is_digest_only(path)
    assert exc.value.invariant == "BYTE_HANDLER_NOT_FOUND"


def test_the_write_call_check_covers_every_in_job_first_party_source():
    # C-14. The docstring claimed to cover "the first-party source executed by
    # the gate" while the check read only the probe. The receipt validator also
    # runs in-job. It is clean, so this was a scope-claim defect rather than a
    # hole -- but an overbroad claim is the defect this project ranks equal to a
    # functional bug.
    assert probe.IN_JOB_FIRST_PARTY_SOURCES == (
        "phase1_2h_r1_private_source_probe.py",
        "phase1_2h_r1_receipt_validator.py",
    )
    combined = probe.assert_no_write_calls_in_first_party_source()
    single = probe.assert_no_write_calls_in_source()
    assert combined > single


def test_a_missing_first_party_source_is_a_refusal(monkeypatch):
    monkeypatch.setattr(
        probe, "IN_JOB_FIRST_PARTY_SOURCES", ("no_such_file_at_all.py",)
    )
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.assert_no_write_calls_in_first_party_source()
    assert exc.value.invariant == "FIRST_PARTY_SOURCE_MISSING"


def test_the_invariant_count_is_derived_from_the_checks_that_ran():
    # C-12. invariants_checked was a literal 12 typed next to the checks, so
    # deleting a check would have left the count untouched and the receipt
    # would still have claimed twelve. The count is now the size of the set the
    # decorator populates on successful return.
    probe.INVARIANTS_EVALUATED.clear()
    probe.assert_byte_handling_is_digest_only()
    assert probe.INVARIANTS_EVALUATED == {"BYTE_HANDLING_DIGEST_ONLY"}
    # The wrapper and the per-file check each record, so the count grows with
    # the checks that actually ran rather than with a number typed by hand.
    probe.assert_no_write_calls_in_first_party_source()
    assert probe.INVARIANTS_EVALUATED == {
        "BYTE_HANDLING_DIGEST_ONLY",
        "NO_WRITE_CALL_IN_SOURCE",
        "NO_WRITE_CALL_IN_FIRST_PARTY_SOURCE",
    }


def test_a_receipt_may_not_claim_more_invariants_than_it_names():
    receipt = {"verdict": {"invariants_checked": 12, "invariants_evaluated": ["A"]}}
    with pytest.raises(validator.ReceiptValidationError) as exc:
        validator._assert_invariant_count_agrees(receipt)
    assert "not an independent assertion" in str(exc.value)


def test_a_receipt_may_not_name_the_same_invariant_twice():
    receipt = {
        "verdict": {"invariants_checked": 2, "invariants_evaluated": ["A", "A"]}
    }
    with pytest.raises(validator.ReceiptValidationError):
        validator._assert_invariant_count_agrees(receipt)


def test_receipt_003_is_identifiable_as_predating_the_derived_count():
    # C-12, residual. Receipt 003 was emitted by the old code with the literal.
    # Back-filling the list would fabricate evidence about a run that already
    # happened, so the field is absent and its absence is the marker.
    #
    # Audit E (E-06) found this test taking the synthetic `receipt` fixture,
    # which is built by the *current* code. It therefore asserted a property of
    # a receipt this test constructs, not of the committed one it names, and
    # would have kept passing had receipt 003 been back-filled. It now opens the
    # committed file.
    committed = json.loads(COMMITTED_RECEIPT.read_text(encoding="utf-8"))
    assert committed["execution"]["execution_id"] == "p12h-r1-access-gate-003"
    assert "invariants_evaluated" not in committed["verdict"]
    assert committed["verdict"]["invariants_checked"] == 12
    validator._assert_invariant_count_agrees(committed)


def test_a_receipt_emitted_today_carries_the_derived_list(record, expected):
    # The other half of E-06. The absence above is only meaningful evidence of
    # age if a receipt built now would carry the field. The current code passes
    # the evaluated set through, so this builds one with two invariants recorded
    # and checks that both the list and the count follow from them.
    names = _names(record, expected)
    evaluated = ["DESIGNATED_IDENTITY", "EXPECTED_MEMBERS_DIGEST"]
    fresh = probe.build_receipt(
        record=record,
        execution_id="ex-0002",
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:05:00Z",
        freeze_commit="a" * 40,
        image_digest="sha256:" + "b" * 64,
        decision_record_sha256="c" * 64,
        probe_source_sha256="d" * 64,
        identity_block=probe.check_identity(
            record, DESIGNATED_CLIENT_ID, "ManagedIdentityCredential"
        ),
        endpoint_block=probe.check_endpoint(record, "Unknown", "10.80.2.4"),
        membership_block=probe.compare_membership(record, expected, names),
        streaming_block=probe.verify_streamed(expected, list(expected)),
        list_operations=1,
        invariants_checked=len(evaluated),
        invariants_evaluated=evaluated,
    )

    assert sorted(fresh["verdict"]["invariants_evaluated"]) == evaluated
    assert fresh["verdict"]["invariants_checked"] == 2
    validator._assert_invariant_count_agrees(fresh)


def test_public_network_access_cannot_be_recorded_as_a_reassuring_value():
    # C-11. The field was an enum including "Disabled", so an instrument that
    # could not observe the setting could still have written a value implying
    # it had. In-job observation is not available, so the only admissible value
    # is the one that admits ignorance.
    schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
    field = schema["properties"]["endpoint"]["properties"]["public_network_access"]
    assert field["const"] == "Unknown"
    assert "enum" not in field


# --- Audit E / Audit F regressions -----------------------------------------
#
# Audits E and F were independent read-only reviews of the instruments this
# suite covers. Each finding below is pinned by a test that fails if the fix is
# reverted, because a finding closed only in prose is a finding that can reopen
# silently.


def _byte_handler_variant(body: str) -> Path:
    """Write a probe-shaped module whose byte handler has the given body."""

    import tempfile

    source = (
        "import hashlib\n"
        "SINK = None\n"
        "def other(x):\n"
        "    return x\n"
        "def stream_object_digest(chunks):\n" + body
    )
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False, encoding="utf-8"
    )
    handle.write(source)
    handle.close()
    return Path(handle.name)


def _refuses(body: str) -> str:
    path = _byte_handler_variant(body)
    try:
        with pytest.raises(probe.ProbeRefusal) as exc:
            probe.assert_byte_handling_is_digest_only(path)
        return exc.value.invariant
    finally:
        path.unlink()


BASELINE_HANDLER = (
    "    digest = hashlib.sha256()\n"
    "    total = 0\n"
    "    for chunk in chunks:\n"
    "        digest.update(chunk)\n"
    "        total += len(chunk)\n"
    "    return (digest.hexdigest(), total)\n"
)


def test_the_baseline_handler_shape_is_accepted():
    # Negative control for the tests below: if this refused, they would prove
    # nothing about the specific escapes they inject.
    path = _byte_handler_variant(BASELINE_HANDLER)
    try:
        assert probe.assert_byte_handling_is_digest_only(path) == 4
    finally:
        path.unlink()


def test_a_chunk_assigned_to_a_module_global_is_refused():
    # E-02. `global SINK; SINK = chunk` is not a call, so a call whitelist
    # could not see it. The bytes would outlive the loop.
    assert (
        _refuses(
            "    global SINK\n"
            "    digest = hashlib.sha256()\n"
            "    total = 0\n"
            "    for chunk in chunks:\n"
            "        digest.update(chunk)\n"
            "        SINK = chunk\n"
            "        total += len(chunk)\n"
            "    return (digest.hexdigest(), total)\n"
        )
        == "BYTE_NAME_ESCAPES_HANDLER"
    )


def test_a_chunk_bound_to_a_local_name_is_refused():
    # E-02. A plain assignment is also not a call.
    assert (
        _refuses(
            "    digest = hashlib.sha256()\n"
            "    total = 0\n"
            "    for chunk in chunks:\n"
            "        digest.update(chunk)\n"
            "        kept = chunk\n"
            "        total += len(kept)\n"
            "    return (digest.hexdigest(), total)\n"
        )
        == "BYTE_NAME_USED_OUTSIDE_DIGEST"
    )


def test_returning_the_chunk_is_refused():
    # E-02. The declared return type would not stop it; nothing checked.
    assert (
        _refuses(
            "    digest = hashlib.sha256()\n"
            "    total = 0\n"
            "    for chunk in chunks:\n"
            "        digest.update(chunk)\n"
            "        total += len(chunk)\n"
            "        return chunk\n"
            "    return (digest.hexdigest(), total)\n"
        )
        == "BYTE_NAME_USED_OUTSIDE_DIGEST"
    )


def test_iterating_over_the_chunk_is_refused():
    # E-02. Iterating bytes yields integers, which is a content inspection.
    assert (
        _refuses(
            "    digest = hashlib.sha256()\n"
            "    total = 0\n"
            "    for chunk in chunks:\n"
            "        digest.update(chunk)\n"
            "        for b in chunk:\n"
            "            total += b\n"
            "    return (digest.hexdigest(), total)\n"
        )
        == "BYTE_NAME_USED_OUTSIDE_DIGEST"
    )


def test_update_on_something_that_is_not_a_digest_is_refused():
    # E-02. The old check matched the attribute name only, so any object with
    # an `update` method -- a dict, a file-like accumulator -- read exactly
    # like the SHA-256 digest.
    assert (
        _refuses(
            "    digest = hashlib.sha256()\n"
            "    sink = {}\n"
            "    total = 0\n"
            "    for chunk in chunks:\n"
            "        sink.update(chunk)\n"
            "        total += len(chunk)\n"
            "    return (digest.hexdigest(), total)\n"
        )
        == "UPDATE_ON_NON_DIGEST"
    )


def test_returning_the_byte_bearing_parameter_is_refused():
    # E-12. The flow analysis tracked the loop variable but not the parameter
    # carrying the stream, so `return digest.hexdigest(), total, chunks` handed
    # every chunk back to the caller and passed. Audit E demonstrated it.
    assert (
        _refuses(
            "    digest = hashlib.sha256()\n"
            "    total = 0\n"
            "    for chunk in chunks:\n"
            "        digest.update(chunk)\n"
            "        total += len(chunk)\n"
            "    return (digest.hexdigest(), total, chunks)\n"
        )
        == "BYTE_NAME_USED_OUTSIDE_DIGEST"
    )


def test_a_digest_from_a_module_other_than_hashlib_is_refused():
    # E-12. `digest_names` matched on the attribute name alone, so
    # `digest = exfil.sha256()` qualified as the digest and could then receive
    # every chunk, while the docstring said the receiver had to come from
    # hashlib.
    assert (
        _refuses(
            "    import exfil\n"
            "    digest = exfil.sha256()\n"
            "    total = 0\n"
            "    for chunk in chunks:\n"
            "        digest.update(chunk)\n"
            "        total += len(chunk)\n"
            "    return (digest.hexdigest(), total)\n"
        )
        == "UPDATE_ON_NON_DIGEST"
    )


def test_rebinding_the_digest_name_is_refused():
    # F-03. `digest = hashlib.sha256()` followed by `digest = sink` left the
    # name in `digest_names` while the object receiving the bytes was no longer
    # a digest at all.
    assert (
        _refuses(
            "    digest = hashlib.sha256()\n"
            "    total = 0\n"
            "    digest = object()\n"
            "    for chunk in chunks:\n"
            "        digest.update(chunk)\n"
            "        total += len(chunk)\n"
            "    return (digest.hexdigest(), total)\n"
        )
        == "DIGEST_NAME_REASSIGNED"
    )


def test_the_live_byte_handler_still_passes_its_own_check():
    # The negative controls above are only meaningful if the real handler is
    # accepted. A check that refuses everything proves nothing.
    assert probe.assert_byte_handling_is_digest_only() > 0


def test_a_handler_that_no_longer_iterates_its_input_is_refused():
    # E-02. If the shape changes, the analysis no longer describes the code.
    # Reporting success over a function this check cannot read would be worse
    # than refusing.
    assert (
        _refuses(
            "    digest = hashlib.sha256()\n"
            "    digest.update(chunks)\n"
            "    return (digest.hexdigest(), len(chunks))\n"
        )
        == "BYTE_CHUNK_BINDING_NOT_FOUND"
    )


def test_nonlocal_in_the_handler_is_refused():
    # Audit F round 3 added a blanket refusal of any nested scope inside the
    # handler, because a nested function is one of the shapes that lets bytes
    # leave the body the analysis reads. That refusal is strictly broader than
    # the `nonlocal` rule and now fires first on this counterexample. Both are
    # correct; the assertion records which one owns the case, so that deleting
    # the nested-scope rule would fail here rather than pass silently.
    assert (
        _refuses(
            "    nonlocal_marker = 0\n"
            "    digest = hashlib.sha256()\n"
            "    total = 0\n"
            "    for chunk in chunks:\n"
            "        digest.update(chunk)\n"
            "        total += len(chunk)\n"
            "    def inner():\n"
            "        nonlocal total\n"
            "        total = 0\n"
            "    return (digest.hexdigest(), total)\n"
        )
        == "BYTE_HANDLER_NESTS_A_SCOPE"
    )


def test_the_byte_handler_name_must_be_defined_once_and_never_rebound():
    """Audits E (E-19) and F: nothing bound the analysed body to what runs.

    ``assert_byte_handling_is_digest_only`` reads the *first* definition found
    by ``ast.walk``; Python binds the *last*. Both reviewers built handlers that
    passed every check below while shipping every chunk to a module global: one
    wrapped by a decorator, one rebound by a plain module-level assignment after
    the def, and one simply defined twice. None of those is a byte-flow property
    of the body, so none of the body checks could ever have caught them.
    """
    baseline = (
        "import hashlib\n"
        "def stream_object_digest(chunks):\n"
        "    digest = hashlib.sha256()\n"
        "    total = 0\n"
        "    for chunk in chunks:\n"
        "        digest.update(chunk)\n"
        "        total += len(chunk)\n"
        "    return (digest.hexdigest(), total)\n"
    )

    def _refuse_module(source: str) -> str:
        path = Path(tempfile.mkdtemp()) / "candidate.py"
        path.write_text(source, encoding="utf-8")
        with pytest.raises(probe.ProbeRefusal) as caught:
            probe.assert_byte_handling_is_digest_only(source_path=path)
        return caught.value.invariant

    # The control: the same module without the escape shape is accepted, so the
    # refusals below are attributable to the shape and not to the fixture.
    control = Path(tempfile.mkdtemp()) / "control.py"
    control.write_text(baseline, encoding="utf-8")
    assert probe.assert_byte_handling_is_digest_only(source_path=control) > 0

    rebound = baseline + "stream_object_digest = _tap(stream_object_digest)\n"
    assert _refuse_module(rebound) == "BYTE_HANDLER_NAME_NOT_UNIQUE"

    duplicated = baseline + (
        "\ndef stream_object_digest(chunks):\n"
        "    _SINK.extend(list(chunks))\n"
        "    return ('', 0)\n"
    )
    assert _refuse_module(duplicated) == "BYTE_HANDLER_NAME_NOT_UNIQUE"

    decorated = baseline.replace(
        "def stream_object_digest", "@_tap\ndef stream_object_digest", 1
    )
    assert _refuse_module(decorated) == "BYTE_HANDLER_IS_DECORATED"

    annotated = baseline + "stream_object_digest: object = _tap\n"
    assert _refuse_module(annotated) == "BYTE_HANDLER_NAME_NOT_UNIQUE"


def test_the_strengthened_checks_pass_on_the_source_that_actually_ran():
    """Audit F (F-02): a new check cited for an execution it did not run under.

    Execution 003 ran a frozen probe whose SHA-256 the receipt records. The
    checks added after Audit C and Audit E did not exist then, so citing them as
    though they had governed that run would be a retroactive claim.

    They can, however, be run against the frozen source now. That is a weaker
    but true statement -- post-hoc verification rather than enforcement -- and
    this test is what makes it true rather than asserted. It recovers the exact
    bytes the receipt names, confirms the digest, and runs both strengthened
    checks over them.
    """

    import subprocess
    import tempfile

    committed = json.loads(COMMITTED_RECEIPT.read_text(encoding="utf-8"))
    claimed = committed["provenance"]["probe_source_sha256"]
    freeze = committed["provenance"]["access_protocol_freeze_commit"]

    completed = subprocess.run(
        ["git", "show", f"{freeze}:scripts/phase1_2h_r1_private_source_probe.py"],
        cwd=ROOT,
        capture_output=True,
    )
    if completed.returncode != 0:  # pragma: no cover - shallow clone
        pytest.skip("the freeze commit is not present in this clone")

    frozen = completed.stdout.replace(b"\r\n", b"\n")
    assert hashlib.sha256(frozen).hexdigest() == claimed

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "frozen_probe.py"
        path.write_bytes(frozen)
        assert probe.assert_no_write_calls_in_source(path) > 0
        assert probe.assert_byte_handling_is_digest_only(path) == 4


def test_the_docstring_does_not_claim_the_call_whitelist_is_complete():
    # E-02. The word was load-bearing: it told a reader no further analysis was
    # needed, which is what stopped the four gaps being found earlier.
    doc = probe.assert_byte_handling_is_digest_only.__doc__ or ""
    assert "both enforceable and complete" not in doc
    assert "syntactic analysis of one small function" in doc
    assert "not a proof about the" in doc


def test_the_module_docstring_does_not_claim_memory_is_overwritten():
    # F-03. CPython drops a reference when the loop rebinds; it does not zero
    # the storage, and this program neither controls nor observes when the
    # allocator reuses it.
    doc = probe.__doc__ or ""
    assert "overwritten each chunk" not in doc
    assert "erased from process memory" in doc
