import base64
import hashlib
import json
import math
import os
import sys
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


ROOT = Path("/workspace/repo")
sys.path.insert(0, str(ROOT / "src" / "jspace_observation"))

import jlens_s2_protocol as s2
import jlens_s3_e0_runtime as e0
import jlens_s3_protocol as s3


ACCOUNT = "stjspacefiles0709085305"
CONTAINER = "jspace-results"
RUN_PREFIX = "jlens-s3/e0/20260807T081017Z"
LOCK_NAME = f"{RUN_PREFIX}/lock/e0_lock.json"
OUTPUT_PREFIX = f"{RUN_PREFIX}/output"
PARTIAL_PREFIX = f"{RUN_PREFIX}/partial"
LOCK_SHA256 = "8417ec21a512f51dac094facd3e7769f0d00b8b8ee896a7e11aeb4a7acb44c1b"
IMAGE_DIGEST = "sha256:17d664e13d67d79d99e7bf521bce9b7aefa946d33e25ec5ebe4cc7bc0aeff6cc"
SOURCE_COMMIT = "67b72c29bd3dc6e8707198b16cfac27177664943"
EXPECTED_FILES = {
    "artifact_manifest.jsonl": {
        "bytes": 1726,
        "sha256": "6d11b09b39bbeead9b38fdb23be47a4247245fb55e6b6b665b817241519df60f",
    },
    "e0_item.jsonl": {
        "bytes": 250605,
        "sha256": "698bfaa830c5f19c41a79ed4059d848464d09d47c73dede72eba678c2e45cfd4",
    },
    "e0_surface.jsonl": {
        "bytes": 339433,
        "sha256": "0b0c6d8393c8eb5ed4495b3d555790666ccd5381cb32313a911ed1f74f5f9a86",
    },
    "eligibility_split_manifest.json": {
        "bytes": 1585,
        "sha256": "aaa8ac7526824da3ea5bfe1e07508ccfbb490d939d32ca9105d7a39847ec89c1",
    },
}
BENCHMARK_PATHS = {
    "multihop": "data/evaluations/lens-eval-multihop.json",
    "order_ops": "data/evaluations/lens-eval-order-ops.json",
    "causal_swap": "data/experiments/probe-swap.json",
}


def parse_jsonl(payload):
    if not payload.endswith(b"\n"):
        raise AssertionError("JSONL payload lacks final LF")
    rows = [json.loads(line) for line in payload.splitlines()]
    if s2.canonical_jsonl_bytes(rows) != payload:
        raise AssertionError("JSONL payload is not canonical")
    return rows


credential = DefaultAzureCredential(
    managed_identity_client_id=os.environ["AZURE_CLIENT_ID"]
)
container = BlobServiceClient(
    account_url=f"https://{ACCOUNT}.blob.core.windows.net",
    credential=credential,
).get_container_client(CONTAINER)

all_names = sorted(
    blob.name for blob in container.list_blobs(name_starts_with=f"{RUN_PREFIX}/")
)
expected_names = [LOCK_NAME] + sorted(
    f"{OUTPUT_PREFIX}/{name}" for name in EXPECTED_FILES
)
if all_names != expected_names:
    raise AssertionError(("unexpected E0 object set", all_names))
if list(container.list_blobs(name_starts_with=PARTIAL_PREFIX)):
    raise AssertionError("partial E0 objects exist")

lock_bytes = container.download_blob(LOCK_NAME).readall()
if hashlib.sha256(lock_bytes).hexdigest() != LOCK_SHA256:
    raise AssertionError("lock hash mismatch")
lock = json.loads(lock_bytes)
e0.validate_e0_lock(lock)
e0.verify_locked_local_bytes(ROOT, lock)

payloads = {}
properties = {}
for relative, expected in EXPECTED_FILES.items():
    name = f"{OUTPUT_PREFIX}/{relative}"
    payload = container.download_blob(name).readall()
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) != expected["bytes"] or digest != expected["sha256"]:
        raise AssertionError(("output identity mismatch", relative, len(payload), digest))
    payloads[relative] = payload
    prop = container.get_blob_client(name).get_blob_properties()
    properties[relative] = {
        "creation_time": prop.creation_time.isoformat(),
        "etag": str(prop.etag),
        "last_modified": prop.last_modified.isoformat(),
    }

manifest_time = properties["artifact_manifest.jsonl"]["last_modified"]
if any(
    manifest_time < row["last_modified"]
    for name, row in properties.items()
    if name != "artifact_manifest.jsonl"
):
    raise AssertionError("artifact manifest was not written last")

item_rows = parse_jsonl(payloads["e0_item.jsonl"])
surface_rows = parse_jsonl(payloads["e0_surface.jsonl"])
manifest_rows = parse_jsonl(payloads["artifact_manifest.jsonl"])
eligibility = json.loads(payloads["eligibility_split_manifest.json"])
if s2.canonical_json_bytes(eligibility) != payloads["eligibility_split_manifest.json"]:
    raise AssertionError("eligibility manifest is not canonical")

protocol = s3.load_and_validate_protocol(ROOT)
for row in item_rows:
    s3.validate_output_row(protocol, "e0_item", row)
for row in surface_rows:
    s3.validate_output_row(protocol, "e0_surface", row)
for row in manifest_rows:
    s3.validate_output_row(protocol, "artifact_manifest", row)

vendored = ROOT / "third_party" / "jacobian-lens" / s2.JLENS_COMMIT
raw_items = {}
expected_item_order = []
expected_surface_specs = []
for distribution in e0.DISTRIBUTION_ORDER:
    document = s3.load_json(vendored / BENCHMARK_PATHS[distribution])
    items = document["items"]
    if len(items) != e0.EXPECTED_ITEM_COUNTS[distribution]:
        raise AssertionError("official item count drift")
    raw_items[distribution] = items
    for item in items:
        expected_item_order.append((distribution, str(item["name"]), item))
        for spec in e0.surface_specs(distribution, item):
            expected_surface_specs.append(
                (
                    distribution,
                    str(item["name"]),
                    item,
                    spec,
                )
            )

if len(item_rows) != 238 or len(expected_item_order) != 238:
    raise AssertionError("item row count mismatch")
if len(surface_rows) != 962 or len(expected_surface_specs) != 962:
    raise AssertionError("surface row count mismatch")

surface_by_item = {}
surface_keys = set()
for row, expected in zip(surface_rows, expected_surface_specs, strict=True):
    distribution, item_id, item, spec = expected
    for key in (
        "candidate_surface",
        "intermediate_index",
        "raw_key",
        "surface_role",
    ):
        if row[key] != spec[key]:
            raise AssertionError(("surface specification mismatch", item_id, key))
    if row["distribution"] != distribution or row["item_id"] != item_id:
        raise AssertionError("surface row order or identity mismatch")
    candidate = row["candidate_surface"]
    target = str(
        item["target"] if distribution != "causal_swap" else item["answer"]
    )
    prompt_leakage = s3.token_bounded_literal(str(item["prompt"]), candidate)
    target_overlap = s3.normalize_surface(
        candidate, casefold=True
    ) == s3.normalize_surface(target, casefold=True)
    single_token = bool(row["token_ids"])
    primary_scope = (
        distribution in {"multihop", "order_ops"}
        and row["surface_role"] == "intermediate"
    )
    expected_primary = (
        primary_scope and not prompt_leakage and not target_overlap and single_token
    )
    if row["normalized_surface"] != s3.normalize_surface(candidate):
        raise AssertionError("normalized surface mismatch")
    if row["prompt_leakage"] != prompt_leakage:
        raise AssertionError("prompt leakage mismatch")
    if row["target_overlap"] != target_overlap:
        raise AssertionError("target overlap mismatch")
    if row["single_token"] != single_token:
        raise AssertionError("single-token flag mismatch")
    if row["official_inclusive_retained"] != single_token:
        raise AssertionError("official inclusive flag mismatch")
    if row["primary_retained"] != expected_primary:
        raise AssertionError("primary retained flag mismatch")
    if row["token_ids"] != sorted(set(row["token_ids"])):
        raise AssertionError("surface token IDs are not sorted unique")
    key = (
        distribution,
        item_id,
        row["surface_role"],
        row["intermediate_index"],
        candidate,
    )
    if key in surface_keys:
        raise AssertionError("duplicate surface primary key")
    surface_keys.add(key)
    surface_by_item.setdefault((distribution, item_id), []).append(row)

item_keys = set()
for row, expected in zip(item_rows, expected_item_order, strict=True):
    distribution, item_id, item = expected
    key = (distribution, item_id)
    if key in item_keys:
        raise AssertionError("duplicate item primary key")
    item_keys.add(key)
    if row["distribution"] != distribution or row["item_id"] != item_id:
        raise AssertionError("item row order or identity mismatch")
    prompt_bytes = str(item["prompt"]).encode("utf-8")
    if row["canonical_item_sha256"] != hashlib.sha256(
        s3.canonical_item_bytes(item)
    ).hexdigest():
        raise AssertionError("canonical item hash mismatch")
    prompt_sha = hashlib.sha256(prompt_bytes).hexdigest()
    if row["prompt_sha256"] != prompt_sha or row["raw_prompt_utf8_sha256"] != prompt_sha:
        raise AssertionError("prompt hash mismatch")
    if row["input_length"] != len(row["input_token_ids"]):
        raise AssertionError("input length mismatch")
    if row["model_id"] != s2.MODEL_ID:
        raise AssertionError("model identity mismatch")
    if row["model_revision"] != s2.MODEL_REVISION:
        raise AssertionError("model revision mismatch")
    if row["tokenizer_revision"] != s2.MODEL_REVISION:
        raise AssertionError("tokenizer revision mismatch")
    if row["parameter_dtype"] != s2.MODEL_DTYPE:
        raise AssertionError("dtype mismatch")
    if row["control_position_candidates"] != sorted(
        set(row["control_position_candidates"])
    ):
        raise AssertionError("control candidates are not sorted unique")
    if any(
        position < 0 or position >= max(0, row["input_length"] - 1)
        for position in row["control_position_candidates"]
    ):
        raise AssertionError("control position outside non-final token range")
    expected_controls = (
        list(
            s3.deterministic_position_controls(
                item, row["control_position_candidates"]
            )
        )
        if row["control_position_candidates"]
        else []
    )
    if row["control_positions"] != expected_controls:
        raise AssertionError("deterministic controls mismatch")

    surfaces = surface_by_item[key]
    target_token_ids = sorted(
        {
            token_id
            for surface in surfaces
            if surface["surface_role"] == "target"
            for token_id in surface["token_ids"]
        }
    )
    if row["target_token_ids"] != target_token_ids:
        raise AssertionError("target token IDs mismatch")
    reasons = []
    if row["input_length"] > e0.MAXIMUM_INPUT_TOKENS:
        reasons.append("over_length")
    if not row["control_position_candidates"]:
        reasons.append("no_control_position")
    if not target_token_ids:
        reasons.append("multi_token")
    if distribution in {"multihop", "order_ops"}:
        indexes = sorted(
            {
                int(surface["intermediate_index"])
                for surface in surfaces
                if surface["surface_role"] == "intermediate"
            }
        )
        for index in indexes:
            candidates = [
                surface
                for surface in surfaces
                if surface["surface_role"] == "intermediate"
                and surface["intermediate_index"] == index
            ]
            if not any(surface["primary_retained"] for surface in candidates):
                if any(surface["prompt_leakage"] for surface in candidates):
                    reasons.append("prompt_surface")
                if any(surface["target_overlap"] for surface in candidates):
                    reasons.append("target_overlap")
                if any(not surface["single_token"] for surface in candidates):
                    reasons.append("multi_token")
    else:
        for role in {"intermediate", "swap_to", "target", "swap_answer"}:
            if not any(
                surface["surface_role"] == role and surface["single_token"]
                for surface in surfaces
            ):
                reasons.append("multi_token")
    reasons = sorted(set(reasons))
    if row["exclusion_reasons"] != reasons:
        raise AssertionError(("exclusion reason mismatch", key, reasons))
    mechanical = not reasons
    behavioral = bool(
        mechanical
        and target_token_ids
        and s3.clean_behavior_eligible(
            row["clean_top1_token_id"], target_token_ids
        )
    )
    if row["mechanical_eligible"] != mechanical:
        raise AssertionError("mechanical eligibility mismatch")
    if row["behavioral_eligible"] != behavioral:
        raise AssertionError("behavioral eligibility mismatch")
    if row["multi_token_removed_count"] != sum(
        not surface["single_token"] for surface in surfaces
    ):
        raise AssertionError("multi-token removal count mismatch")
    if row["prompt_surface_removed_count"] != sum(
        surface["surface_role"] == "intermediate"
        and surface["prompt_leakage"]
        for surface in surfaces
    ):
        raise AssertionError("prompt removal count mismatch")
    if row["target_overlap_removed_count"] != sum(
        surface["surface_role"] == "intermediate"
        and surface["target_overlap"]
        for surface in surfaces
    ):
        raise AssertionError("target removal count mismatch")

expected_splits = {}
for distribution in e0.DISTRIBUTION_ORDER:
    eligible = [
        item
        for item in raw_items[distribution]
        if next(
            row
            for row in item_rows
            if row["distribution"] == distribution
            and row["item_id"] == str(item["name"])
        )["behavioral_eligible"]
        and next(
            row
            for row in item_rows
            if row["distribution"] == distribution
            and row["item_id"] == str(item["name"])
        )["mechanical_eligible"]
    ]
    for assignment in s3.assign_hash_split(eligible):
        expected_splits[(distribution, assignment["item_id"])] = assignment

for row in item_rows:
    assignment = expected_splits.get((row["distribution"], row["item_id"]))
    expected_role = assignment["split_role"] if assignment else "ineligible"
    expected_hash = assignment["split_hash"] if assignment else None
    if row["split_role"] != expected_role or row["split_hash"] != expected_hash:
        raise AssertionError("sealed split mismatch")

counts = e0.e0_counts(item_rows)
if counts["distribution_counts"] != eligibility["distribution_counts"]:
    raise AssertionError("distribution counts mismatch")
if counts["floor_booleans"] != eligibility["floor_booleans"]:
    raise AssertionError("floor booleans mismatch")
if counts["terminal_state"] != eligibility["terminal_state"]:
    raise AssertionError("terminal state mismatch")
if eligibility["terminal_state"] != "INSUFFICIENT_BEHAVIORAL_SUPPORT_FOR_VALIDITY":
    raise AssertionError("unexpected terminal state")

expected_exclusions = {
    "multi_token": sum(row["multi_token_removed_count"] for row in item_rows),
    "no_control_position": sum(
        "no_control_position" in row["exclusion_reasons"] for row in item_rows
    ),
    "over_length": sum(
        "over_length" in row["exclusion_reasons"] for row in item_rows
    ),
    "prompt_surface": sum(
        row["prompt_surface_removed_count"] for row in item_rows
    ),
    "target_overlap": sum(
        row["target_overlap_removed_count"] for row in item_rows
    ),
}
if eligibility["exclusion_counts"] != expected_exclusions:
    raise AssertionError("exclusion count mismatch")
if eligibility["e0_item_sha256"] != EXPECTED_FILES["e0_item.jsonl"]["sha256"]:
    raise AssertionError("eligibility item hash mismatch")
if eligibility["e0_surface_sha256"] != EXPECTED_FILES["e0_surface.jsonl"]["sha256"]:
    raise AssertionError("eligibility surface hash mismatch")
if eligibility["benchmark_item_tokenizer_calls"] != 238:
    raise AssertionError("tokenizer call count mismatch")
if eligibility["benchmark_model_forward_calls"] != 238:
    raise AssertionError("model call count mismatch")
for key in (
    "e1_outputs",
    "e2_outputs",
    "lens_imports",
    "lens_operations",
    "pre_lock_benchmark_model_operations",
    "pre_lock_benchmark_tokenizer_operations",
):
    if eligibility[key] != 0:
        raise AssertionError((key, eligibility[key]))
if eligibility["lock_sha256"] != LOCK_SHA256:
    raise AssertionError("eligibility lock mismatch")
if eligibility["artifact_manifest_destination"] != OUTPUT_PREFIX:
    raise AssertionError("output prefix mismatch")
if eligibility["manifest_written_last"] is not True:
    raise AssertionError("manifest-written-last flag mismatch")

if len(manifest_rows) != 3:
    raise AssertionError("artifact manifest row count mismatch")
for index, relative in enumerate(
    ("e0_item.jsonl", "e0_surface.jsonl", "eligibility_split_manifest.json"),
    start=1,
):
    row = manifest_rows[index - 1]
    if row != {
        "artifact_id": f"E0::{relative}",
        "bytes": len(payloads[relative]),
        "complete": True,
        "create_only": True,
        "image_digest": IMAGE_DIGEST,
        "opened_at_utc": None,
        "protocol_sha256": s2.S3_PROTOCOL_SHA256,
        "relative_path": relative,
        "schema_sha256": e0.E0_PACK_SCHEMA_SHA256,
        "sha256": hashlib.sha256(payloads[relative]).hexdigest(),
        "source_commit": SOURCE_COMMIT,
        "stage": "E0",
        "written_order": index,
    }:
        raise AssertionError(("artifact manifest row mismatch", relative))

schema = s3.load_json(ROOT / "docs" / "jlens_s3_e0_pack.schema.json")
pack = {
    "artifact_files": [
        {
            "bytes": len(payloads[relative]),
            "create_only": True,
            "relative_path": relative,
            "sha256": hashlib.sha256(payloads[relative]).hexdigest(),
            "written_order": index,
        }
        for index, relative in enumerate(
            ("e0_item.jsonl", "e0_surface.jsonl", "eligibility_split_manifest.json"),
            start=1,
        )
    ],
    "complete": True,
    "e0_items": item_rows,
    "e0_surfaces": surface_rows,
    "eligibility_split_manifest": eligibility,
    "s2_manifest_sha256": lock["s2_manifest"]["sha256"],
    "s3_protocol_sha256": s2.S3_PROTOCOL_SHA256,
    "s3_schema_sha256": s2.S3_SCHEMA_SHA256,
    "schema_version": "jlens-s3-e0-pack/v1",
}
s3.validate_json_schema(pack, schema)

receipt = {
    "artifact_manifest_sha256": EXPECTED_FILES["artifact_manifest.jsonl"]["sha256"],
    "blob_properties": properties,
    "confirmation_counts": counts["confirmation_counts"],
    "distribution_counts": counts["distribution_counts"],
    "exclusion_counts": expected_exclusions,
    "files": EXPECTED_FILES,
    "floor_booleans": counts["floor_booleans"],
    "image_digest": IMAGE_DIGEST,
    "item_count": len(item_rows),
    "lens_imports": 0,
    "lens_operations": 0,
    "lock_sha256": LOCK_SHA256,
    "manifest_written_last": True,
    "model_forward_calls": eligibility["benchmark_model_forward_calls"],
    "object_names": all_names,
    "partial_object_count": 0,
    "schema_version": "jlens-s3-e0-independent-verification/v1",
    "source_commit": SOURCE_COMMIT,
    "status": "S3-V0-VERIFIED",
    "surface_count": len(surface_rows),
    "terminal_state": counts["terminal_state"],
    "tokenizer_calls": eligibility["benchmark_item_tokenizer_calls"],
    "vocabulary_token_decodes": eligibility["vocabulary_token_decodes"],
}
print(
    json.dumps(
        {"kind": "e0_verification_receipt", "receipt": receipt},
        sort_keys=True,
        separators=(",", ":"),
    ),
    flush=True,
)

chunk_size = 3000
for relative, payload in payloads.items():
    total = max(1, (len(payload) + chunk_size - 1) // chunk_size)
    digest = hashlib.sha256(payload).hexdigest()
    for index in range(total):
        chunk = payload[index * chunk_size : (index + 1) * chunk_size]
        print(
            json.dumps(
                {
                    "b64": base64.b64encode(chunk).decode("ascii"),
                    "index": index,
                    "kind": "e0_export_chunk",
                    "path": relative,
                    "payload_bytes": len(payload),
                    "payload_sha256": digest,
                    "total": total,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )
