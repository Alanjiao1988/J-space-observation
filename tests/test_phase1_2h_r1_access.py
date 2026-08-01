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
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DECISION_RECORD = ROOT / "docs" / "phase1_2h_r1_access_decision_record.json"
RECEIPT_SCHEMA = ROOT / "docs" / "phase1_2h_r1_access_receipt.schema.json"
PROBE_PATH = SCRIPTS / "phase1_2h_r1_private_source_probe.py"
VALIDATOR_PATH = SCRIPTS / "phase1_2h_r1_receipt_validator.py"


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
    block = probe.check_identity(record, "a-client-id", "ManagedIdentityCredential")
    assert block["effective_read_only_verdict"] == "READ_ONLY_CONFIRMED"
    assert block["forbidden_credential_types_absent"] is True


@pytest.mark.parametrize("bad", ["DefaultAzureCredential", "AzureCliCredential", "ClientSecretCredential"])
def test_a_forbidden_credential_type_is_refused(record, bad):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_identity(record, "a-client-id", bad)
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
    block = probe.check_endpoint(record, "Disabled", "10.80.2.4")
    assert block["resolved_matches_expected_private_ip"] is True
    assert block["privatelink_path_confirmed"] is True


def test_a_public_storage_endpoint_is_refused(record):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Enabled", "10.80.2.4")
    assert exc.value.reason_code == "PUBLIC_NETWORK_ACCESS_NOT_DISABLED"


def test_a_public_ip_is_refused(record):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Disabled", "20.43.121.10")
    assert exc.value.reason_code == "ENDPOINT_NOT_PRIVATE"
    assert exc.value.invariant == "PUBLIC_ADDRESS"


def test_a_private_ip_outside_the_project_vnet_is_refused(record):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Disabled", "192.168.4.4")
    assert exc.value.invariant == "ADDRESS_OUTSIDE_PROJECT_VNET"


def test_an_unregistered_address_inside_the_vnet_is_still_refused(record):
    # Being inside 10.80.0.0/16 is not enough. A different private endpoint in
    # the same VNet is a different endpoint.
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Disabled", "10.80.2.5")
    assert exc.value.reason_code == "ENDPOINT_IP_MISMATCH"


def test_an_endpoint_refusal_does_not_carry_the_observed_address(record):
    with pytest.raises(probe.ProbeRefusal) as exc:
        probe.check_endpoint(record, "Disabled", "10.80.9.99")
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
    source = PROBE_PATH.read_text(encoding="utf-8")
    assert "jspace_observation" not in source
    assert "import jspace_observation" not in source


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
            record, "11111111-2222-3333-4444-555555555555", "ManagedIdentityCredential"
        ),
        endpoint_block=probe.check_endpoint(record, "Disabled", "10.80.2.4"),
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
