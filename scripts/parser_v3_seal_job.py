#!/usr/bin/env python3
"""Parser-v3-v1 pre-seal overlap cross-check and gated seal.

Single-execution payload for a short-lived Azure Container Apps CPU job.  It
does exactly two things, in this order:

1. **Cross-check 1** of ``docs/phase1_parser_v3_sealing_run.md`` section 9: the
   new ``parser-v3-v1`` locked set against the **retired** ``parser-v2-v1``
   locked *inputs*.  Only one-way digests and counts leave the comparison.
2. **The seal**, and only if the cross-check passes: the twelve registered
   objects of section 1 written to the append-only parent prefix, with
   ``overwrite=false``, exact membership verification, per-object round-trip
   SHA-256 verification, and ``manifests/set_manifest.json`` written last.

Hard properties this file is built to guarantee:

* It is structurally incapable of reading retired **labels**, retired **scores**
  or the retired scoring ledger.  The retired source prefix is a module
  constant, no argument can change it, only one blob leaf inside it is ever
  downloaded, and every record read from it must match the frozen label-free
  ``phase1-parser-v2-locked-input/v1`` key set.
* No retired input body text is emitted, printed, uploaded or returned.  The
  emitted report is checked against the retired texts before it is written.
* No parser is imported, no parser-v3 prediction is produced and nothing is
  scored.  ``src/jspace_observation/eval_parsing_v3.py`` is never touched.
* The registered fingerprint functions are imported from
  ``scripts/build_parser_v3_validation_set.py``.  They are never reimplemented
  here, and the job refuses to run if they do not reproduce pinned known-answer
  vectors and the committed inputs manifest.

Exit codes:

* ``0``  cross-check PASS (and, in ``seal`` mode, seal complete)  -> ``SEALED``
* ``2``  cross-check FAIL, at least one collision                 -> ``BLOCKED_COLLISION``
* ``3``  aborted on a guard, provenance or infrastructure fault   -> ``BLOCKED_INFRASTRUCTURE``
* ``1``  usage error                                              -> ``BLOCKED_INFRASTRUCTURE``
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import hashlib
import importlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

SCHEMA_CROSSCHECK = "phase1-parser-v3-preseal-crosscheck/v1"
SCHEMA_SEAL_RECORD = "phase1-parser-v3-seal-record/v1"

# --------------------------------------------------------------- source side

#: Retired parser-v2-v1 locked **inputs** leaf.  Not configurable, by design.
RETIRED_INPUTS_PREFIX = (
    "phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/"
)
#: The only blob this job is ever allowed to download from the retired release.
RETIRED_INPUTS_BLOB = RETIRED_INPUTS_PREFIX + "locked_inputs.jsonl"
#: Digest published in ``reports/phase1_parser_v2_validation_set.md``.
RETIRED_INPUTS_REGISTERED_SHA256 = (
    "2d60483e7f7a2ce1883acca2dcf9a6771f84b54d596ab2e02ed4a39d937c4e3e"
)
RETIRED_INPUT_SCHEMA_VERSION = "phase1-parser-v2-locked-input/v1"

#: Any retired blob name containing one of these is refused before download.
FORBIDDEN_SOURCE_TOKENS = (
    "locked-labels",
    "locked_labels",
    "reference_label",
    "reviewer_",
    "arbitration",
    "consensus",
    "stage1",
    "stage2",
    "score",
    "scoring",
    "ledger",
    "prediction",
    "verdict",
    "grade",
)

#: Frozen, label-free key set of a parser-v2 locked input record.
ALLOWED_RETIRED_RECORD_KEYS = frozenset(
    {"schema_version", "case_id", "source_kind", "output_text", "parse_type"}
)
#: Output-bearing fields, in priority order.  Nothing else is ever read.
OUTPUT_BEARING_KEYS = ("output_text", "text", "model_output", "generation", "completion")

# ----------------------------------------------------------------- sink side

SEAL_ROOT = "phase1-evaluator-validation/parser-v3-v1"
SEAL_TIMESTAMP_RE = re.compile(r"\A[0-9]{8}T[0-9]{6}Z\Z")

#: The twelve registered objects of docs/phase1_parser_v3_sealing_run.md §1,
#: in the section-3 write order.  ``sha256``/``bytes`` are the Track D build
#: digests; the job aborts if a local file does not match.
SEAL_OBJECTS: tuple[dict[str, Any], ...] = (
    {
        "order": 1,
        "leaf": "locked-inputs",
        "name": "locked_inputs.jsonl",
        "source": "evaluator_sets/parser_v3_v1/locked_inputs.jsonl",
        "sha256": "946218357432d6f271e403a883559235a7b59da7832f534bdf7eb33e934c4e06",
        "bytes": 32430,
        "content_class": "private holdout inputs",
    },
    {
        "order": 2,
        "leaf": "locked-labels",
        "name": "locked_labels.jsonl",
        "source": "evaluator_sets/parser_v3_v1/locked_labels.jsonl",
        "sha256": "3e4f1b1bca3862d97a6db37854d1b046ac7a3c606f031b692b58ef1940be2743",
        "bytes": 109411,
        "content_class": "private holdout labels",
    },
    {
        "order": 3,
        "leaf": "locked-labels",
        "name": "reviewer_a_locked_labels.jsonl",
        "source": "evaluator_sets/parser_v3_v1/reviewer_a_locked_labels.jsonl",
        "sha256": "ee85baa3f1aeced9d2e5f15ef5dd8d97d5d23378a0808b8708b2bb9ea794fa6c",
        "bytes": 55407,
        "content_class": "private reviewer A rows",
    },
    {
        "order": 4,
        "leaf": "locked-labels",
        "name": "reviewer_b_locked_labels.jsonl",
        "source": "evaluator_sets/parser_v3_v1/reviewer_b_locked_labels.jsonl",
        "sha256": "41a5eef727a793b5c0e80d89d9174fd8c15b859660cba7530512105e5cb2c335",
        "bytes": 55264,
        "content_class": "private reviewer B rows",
    },
    {
        "order": 5,
        "leaf": "locked-labels",
        "name": "arbitration_locked_labels.jsonl",
        "source": "evaluator_sets/parser_v3_v1/arbitration_locked_labels.jsonl",
        "sha256": "07613a47dad94f52ea3e521a5d7585e5628c0cf7ac3ab49c69524f38351b4b37",
        "bytes": 3345,
        "content_class": "private arbiter rows",
    },
    {
        "order": 6,
        "leaf": "reports",
        "name": "strata_definitions.md",
        "source": "evaluator_sets/parser_v3_v1/strata_definitions.md",
        "sha256": "85990e195537c8cf9473d1ac0d34debf1c9f6d9728814b99d2f90f6da65ca87d",
        "bytes": 6054,
        "content_class": "public protocol copy",
    },
    {
        "order": 7,
        "leaf": "reports",
        "name": "phase1_parser_v3_locked_set.md",
        "source": "docs/phase1_parser_v3_locked_set.md",
        "sha256": "a99ec53537717989559d452a5c92e12a30cd7bc11d8b5d30f6d2452c777b4027",
        "bytes": 20895,
        "content_class": "public protocol copy",
    },
    {
        "order": 8,
        "leaf": "reports",
        "name": "phase1_parser_v3_validation_set.md",
        "source": "reports/phase1_parser_v3_validation_set.md",
        "sha256": "85648ac4aad2be92fc98f117c7380450bae6ca8fddd3e066d0114ead21eb9713",
        "bytes": 20772,
        "content_class": "public report copy",
    },
    {
        "order": 9,
        "leaf": "reports",
        "name": "phase1_parser_v3_sealing_run.md",
        "source": "docs/phase1_parser_v3_sealing_run.md",
        "sha256": "7c5d61a1cef1f84e340457e3c80a26095bccaa54c0e89c9d3afd04a3086f873c",
        "bytes": 13460,
        "content_class": "sealing specification",
    },
    {
        "order": 10,
        "leaf": "manifests",
        "name": "inputs_manifest.json",
        "source": "evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json",
        "sha256": "ec954093648cb68ce8e6a83db07639bf7de426cc14e35c0a4503b0a6d75ede9d",
        "bytes": 53703,
        "content_class": "integrity",
    },
    {
        "order": 11,
        "leaf": "manifests",
        "name": "labels_manifest.json",
        "source": "evaluator_sets/parser_v3_v1/manifests/labels_manifest.json",
        "sha256": "ab32c559cd62c72d059fc2527e17d3e806d5ddc9227f8bd8f8f6b0295d7e67a2",
        "bytes": 17786,
        "content_class": "integrity",
    },
    {
        "order": 12,
        "leaf": "manifests",
        "name": "set_manifest.json",
        "source": "evaluator_sets/parser_v3_v1/manifests/set_manifest.json",
        "sha256": "13f021abd7a052b3b7153b6a0af8ccc13f3bced4b4c280dd3abaa7ab65b949f3",
        "bytes": 8086,
        "content_class": "closure record, written last",
    },
)

SET_MANIFEST_ORDER = 12

# ------------------------------------------------- registered fingerprinting

MANIFEST_FIELDS = ("exact_sha256", "normalized_sha256", "numeric_normalized_sha256")
REPORT_FIELD_NAMES = {
    "exact_sha256": "exact",
    "normalized_sha256": "normalised",
    "numeric_normalized_sha256": "numeric_normalised",
}

#: Known-answer vectors for the registered fingerprint functions.  They pin
#: NFKC folding, CRLF folding, punctuation folding, whitespace collapsing,
#: case folding and numeric canonicalisation.  A divergent normaliser would
#: produce a meaningless "0 collisions", so the job refuses to run instead.
FINGERPRINT_KNOWN_ANSWERS: tuple[dict[str, str], ...] = (
    {
        "text": "The answer is 0.50",
        "exact_sha256": "ea7da740ef717b13e1d4e8cfcbad8cda9f05066a15ffecde05ffebc7991270fa",
        "normalized_sha256": "23b8084cd9d397607011b76841e4bb7577d52b9aa49769a7758e7a5663da7bf2",
        "numeric_normalized_sha256": "db24700225023492aef05423c870e263e1f7f510f525a8ca16204a9268a28232",
        "masked_template_sha256": "b79e6c8ff0d818cae04deadda33719cf4d755eb7733a6d05551246e1cae14bd3",
    },
    {
        "text": "The\u00a0answer  is\r\n \u201c1/2\u201d\u2014exactly",
        "exact_sha256": "34a7533ebf941275b07f1070401b51bcf2473e336702189d54d40f06ef163156",
        "normalized_sha256": "9c1bbc82d02e9bd8ceb1667584c5f10e2d12956bb7e3a16b9a721ab7b4a0b6b0",
        "numeric_normalized_sha256": "9c1bbc82d02e9bd8ceb1667584c5f10e2d12956bb7e3a16b9a721ab7b4a0b6b0",
        "masked_template_sha256": "37304f573821c2c9a3d1eef166bf629a256dbc9b5804a275acee13c1ac4bce58",
    },
    {
        "text": "ANSWER: 5.0e-1",
        "exact_sha256": "fa39cfab70beaf0f8d5acd389347449a41e735bc5cc6bedbafc141f087e4325c",
        "normalized_sha256": "33cedfcb853ad3993951d59dc60a60476bf293182301e06a6f757b498fbf5b34",
        "numeric_normalized_sha256": "87655bc0c20685761a67796eb980435115438d348ab746fd3085debcb7748fb8",
        "masked_template_sha256": "0b1cd412021c32db07cbfe40a6f3b943ec704006cd24b726c855204fbffb6c75",
    },
    {
        "text": "  mixed   CASE and 3/6 \u2018quoted\u2019  ",
        "exact_sha256": "a9ef81a7b985187ff734f875cecf45da507976ba5daacde1d75957615c748e0a",
        "normalized_sha256": "b7d5b03ecff2dafdd243ff85d0cd9939d9fcf871e86994308268d4afcb1c67f0",
        "numeric_normalized_sha256": "0f6f97d3e31892ff962e8cd32875916418f740788600a6f12f49884f96a12a89",
        "masked_template_sha256": "54950fc53664d5d51d8504c0dc5e1770d29c6ed0f5c17d725b34c558c5d6db2f",
    },
    {
        "text": "no numerals here at all",
        "exact_sha256": "95abaf054fdaf9ba62fc95b4f776bede34466863c704d7aa8c172104f27df2c1",
        "normalized_sha256": "95abaf054fdaf9ba62fc95b4f776bede34466863c704d7aa8c172104f27df2c1",
        "numeric_normalized_sha256": "95abaf054fdaf9ba62fc95b4f776bede34466863c704d7aa8c172104f27df2c1",
        "masked_template_sha256": "95abaf054fdaf9ba62fc95b4f776bede34466863c704d7aa8c172104f27df2c1",
    },
)

_KAT_FIELDS = (
    "exact_sha256",
    "normalized_sha256",
    "numeric_normalized_sha256",
    "masked_template_sha256",
)

_PROHIBITED_CREDENTIAL_ENV = (
    "AZURE_STORAGE_CONNECTION_STRING",
    "AZURE_STORAGE_KEY",
    "AZURE_STORAGE_ACCOUNT_KEY",
    "AZURE_STORAGE_SAS_TOKEN",
    "AZURE_SAS_TOKEN",
)
_ACCOUNT_HOST_PATTERN = re.compile(
    r"[a-z0-9][a-z0-9-]{1,22}[a-z0-9]\.blob\.core\.windows\.net\Z"
)
_CONTAINER_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?\Z")


class JobAbort(RuntimeError):
    """A guard, provenance or infrastructure fault.  Never a science result."""


class RegistrationError(JobAbort):
    """The imported fingerprint functions are not the registered ones."""


# --------------------------------------------------------------- primitives


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def utc_now() -> str:
    return (
        _datetime.datetime.now(_datetime.timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def load_builder_module(builder_path: Path) -> ModuleType:
    """Import the registered builder so its fingerprint functions are reused."""
    builder_path = Path(builder_path)
    if not builder_path.is_file():
        raise JobAbort(f"registered fingerprint module not found: {builder_path}")
    name = "_jspace_parser_v3_fingerprints"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, builder_path)
    if spec is None or spec.loader is None:
        raise JobAbort("cannot load the registered fingerprint module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_fingerprint_registration(module: Any) -> dict[str, Any]:
    """Refuse to run unless the imported functions are the registered ones."""
    for attribute in ("fingerprints", "normalize_text", "numeric_normalized_text"):
        if not callable(getattr(module, attribute, None)):
            raise RegistrationError(
                f"registered fingerprint function is missing: {attribute}"
            )
    for index, vector in enumerate(FINGERPRINT_KNOWN_ANSWERS):
        text = vector["text"]
        try:
            produced = module.fingerprints(text)
        except Exception as error:  # pragma: no cover - defensive
            raise RegistrationError(
                f"registered fingerprint function raised on vector {index}: "
                f"{type(error).__name__}"
            ) from None
        if not isinstance(produced, Mapping):
            raise RegistrationError("fingerprints() must return a mapping")
        for field in _KAT_FIELDS:
            if produced.get(field) != vector[field]:
                raise RegistrationError(
                    "imported fingerprint functions are not the registered ones: "
                    f"vector {index} field {field}"
                )
        normalized = module.normalize_text(text)
        if sha256_bytes(normalized.encode("utf-8")) != vector["normalized_sha256"]:
            raise RegistrationError(
                f"normalize_text diverged from the registered normaliser: vector {index}"
            )
        numeric = module.numeric_normalized_text(text)
        if sha256_bytes(numeric.encode("utf-8")) != vector["numeric_normalized_sha256"]:
            raise RegistrationError(
                "numeric_normalized_text diverged from the registered normaliser: "
                f"vector {index}"
            )
    return {
        "status": "verified",
        "method": "pinned known-answer vectors against the registered builder",
        "vectors": len(FINGERPRINT_KNOWN_ANSWERS),
        "functions": ["fingerprints", "normalize_text", "numeric_normalized_text"],
    }


def verify_manifest_reproduction(
    module: Any, manifest: Mapping[str, Any], locked_inputs: Path | None
) -> dict[str, Any]:
    """Recompute the new set's own fingerprints and require an exact match.

    This is the strongest available proof that the fingerprint functions in
    this container are the ones that produced the committed inputs manifest.
    """
    if locked_inputs is None or not Path(locked_inputs).is_file():
        return {
            "status": "not_applicable",
            "reason": "locked inputs are not present in this execution context",
        }
    records = {row["case_id"]: row for row in manifest_records(manifest)}
    reproduced = 0
    for line in Path(locked_inputs).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        case_id = row.get("case_id")
        expected = records.get(case_id)
        if expected is None:
            raise RegistrationError(
                "locked input case id is absent from the committed manifest"
            )
        produced = module.fingerprints(row["output_text"])
        for field in _KAT_FIELDS:
            if produced.get(field) != expected.get(field):
                raise RegistrationError(
                    "recomputed fingerprints do not reproduce the committed manifest"
                )
        reproduced += 1
    if reproduced != len(records):
        raise RegistrationError(
            "locked inputs and committed manifest disagree on record count"
        )
    return {"status": "verified", "records": reproduced}


def manifest_records(manifest: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    records = manifest.get("records") or manifest.get("cases") or []
    if not isinstance(records, list) or not records:
        raise JobAbort("the inputs manifest carries no records")
    return records


def new_fingerprint_index(manifest: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Map each registered field digest to the owning new-set case id."""
    index: dict[str, dict[str, str]] = {field: {} for field in MANIFEST_FIELDS}
    for row in manifest_records(manifest):
        marks = row.get("fingerprints", row)
        case_id = str(row.get("case_id", ""))
        for field in MANIFEST_FIELDS:
            digest = marks.get(field)
            if digest:
                index[field].setdefault(str(digest), case_id)
    return index


# ----------------------------------------------------------- retired source


def assert_source_prefix_is_locked_inputs(prefix: str) -> str:
    """Structural refusal to point this job at anything but retired inputs."""
    if prefix != RETIRED_INPUTS_PREFIX:
        raise JobAbort("the retired source prefix is a constant and was altered")
    if not prefix.endswith("/locked-inputs/"):
        raise JobAbort("the retired source prefix is not a locked-inputs leaf")
    lowered = prefix.lower()
    for token in FORBIDDEN_SOURCE_TOKENS:
        if token in lowered:
            raise JobAbort(f"the retired source prefix names forbidden material: {token}")
    return prefix


def assert_blob_name_is_readable(name: str) -> None:
    if not name.startswith(RETIRED_INPUTS_PREFIX):
        raise JobAbort("a listed blob escaped the retired locked-inputs prefix")
    lowered = name.lower()
    for token in FORBIDDEN_SOURCE_TOKENS:
        if token in lowered:
            raise JobAbort(f"refusing to touch forbidden retired material: {token}")


def blob_name_of(item: Any) -> str:
    name = getattr(item, "name", None)
    if name is None and isinstance(item, Mapping):
        name = item.get("name")
    if not isinstance(name, str) or not name:
        raise JobAbort("blob listing returned an invalid member")
    return name


def list_retired_inputs(service: Any, container: str) -> list[str]:
    """List the retired locked-inputs leaf, always with ``name_starts_with``.

    The ABAC condition on the read grant evaluates ``blobs:prefix`` for List
    Blobs, so an unprefixed listing is denied by design.
    """
    assert_source_prefix_is_locked_inputs(RETIRED_INPUTS_PREFIX)
    client = service.get_container_client(container)
    names = sorted(
        blob_name_of(item)
        for item in client.list_blobs(name_starts_with=RETIRED_INPUTS_PREFIX)
    )
    for name in names:
        assert_blob_name_is_readable(name)
    if RETIRED_INPUTS_BLOB not in names:
        raise JobAbort("the retired locked-inputs object is absent from its prefix")
    return names


def retired_texts_from_bytes(payload: bytes) -> tuple[list[str], list[str]]:
    """Extract output-bearing text only.  Never reads a label-shaped field."""
    texts: list[str] = []
    case_ids: list[str] = []
    for index, raw in enumerate(payload.decode("utf-8").splitlines()):
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            raise JobAbort(
                f"retired locked-inputs record {index} is not valid JSON"
            ) from None
        if not isinstance(row, Mapping):
            raise JobAbort(f"retired locked-inputs record {index} is not an object")
        keys = set(row)
        unexpected = keys - ALLOWED_RETIRED_RECORD_KEYS
        if unexpected:
            raise JobAbort(
                "retired locked-inputs record carries fields outside the frozen "
                f"label-free schema at record {index}"
            )
        if row.get("schema_version") != RETIRED_INPUT_SCHEMA_VERSION:
            raise JobAbort(
                f"retired locked-inputs record {index} is not a parser-v2 locked input"
            )
        found = False
        for key in OUTPUT_BEARING_KEYS:
            value = row.get(key)
            if isinstance(value, str) and value:
                texts.append(value)
                case_ids.append(str(row.get("case_id", f"index-{index}")))
                found = True
        if not found:
            raise JobAbort(
                f"retired locked-inputs record {index} has no output-bearing field"
            )
    if not texts:
        raise JobAbort("the retired locked-inputs object yielded no comparable text")
    return texts, case_ids


def read_retired_inputs(service: Any, container: str) -> dict[str, Any]:
    assert_blob_name_is_readable(RETIRED_INPUTS_BLOB)
    blob = service.get_blob_client(container=container, blob=RETIRED_INPUTS_BLOB)
    try:
        payload = blob.download_blob().readall()
    except Exception as error:
        raise JobAbort(
            f"cannot read the retired locked-inputs object: {type(error).__name__}"
        ) from None
    if not isinstance(payload, (bytes, bytearray)):
        raise JobAbort("the retired locked-inputs download returned a non-byte payload")
    payload = bytes(payload)
    digest = sha256_bytes(payload)
    texts, case_ids = retired_texts_from_bytes(payload)
    return {
        "sha256": digest,
        "bytes": len(payload),
        "registered_sha256": RETIRED_INPUTS_REGISTERED_SHA256,
        "registered_sha256_match": digest == RETIRED_INPUTS_REGISTERED_SHA256,
        "texts": texts,
        "case_ids": case_ids,
    }


# ------------------------------------------------------------- cross-check


def compare_fingerprints(
    module: Any,
    new_index: Mapping[str, Mapping[str, str]],
    retired_texts: Sequence[str],
    retired_case_ids: Sequence[str],
) -> dict[str, list[dict[str, Any]]]:
    collisions: dict[str, list[dict[str, Any]]] = {
        REPORT_FIELD_NAMES[field]: [] for field in MANIFEST_FIELDS
    }
    for position, text in enumerate(retired_texts):
        marks = module.fingerprints(text)
        for field in MANIFEST_FIELDS:
            digest = marks[field]
            owner = new_index[field].get(digest)
            if owner is not None:
                collisions[REPORT_FIELD_NAMES[field]].append(
                    {
                        "field": field,
                        "sha256": digest,
                        "new_case_id": owner,
                        "retired_case_id": (
                            retired_case_ids[position]
                            if position < len(retired_case_ids)
                            else f"index-{position}"
                        ),
                        "retired_record_index": position,
                    }
                )
    return collisions


def assert_report_is_text_free(report: Mapping[str, Any], texts: Iterable[str]) -> None:
    """Refuse to emit anything that could carry retired body text."""
    blob = json.dumps(report, ensure_ascii=False, sort_keys=True)
    for text in texts:
        stripped = text.strip()
        if len(stripped) < 8:
            continue
        if stripped in blob:
            raise JobAbort("the report would carry retired input text; refusing to emit")
        window = stripped[:32]
        if len(window) >= 8 and window in blob:
            raise JobAbort("the report would carry retired input text; refusing to emit")


def build_crosscheck_report(
    *,
    account: str,
    container: str,
    listed_names: Sequence[str],
    source: Mapping[str, Any],
    registration: Mapping[str, Any],
    reproduction: Mapping[str, Any],
    new_index: Mapping[str, Mapping[str, str]],
    collisions: Mapping[str, list[dict[str, Any]]],
    started_at: str,
    seal_timestamp: str | None,
    mode: str,
) -> dict[str, Any]:
    counts = {
        f"{REPORT_FIELD_NAMES[field]}_collision_count": len(
            collisions[REPORT_FIELD_NAMES[field]]
        )
        for field in MANIFEST_FIELDS
    }
    clean = all(value == 0 for value in counts.values())
    provenance_ok = bool(source.get("registered_sha256_match"))
    abort_reasons: list[str] = []
    if not provenance_ok:
        abort_reasons.append(
            "the retired locked-inputs object does not match its registered digest"
        )
    if abort_reasons:
        verdict = "ABORT"
    elif clean:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_CROSSCHECK,
        "check_id": "parser-v3-preseal-crosscheck-1",
        "check_name": (
            "new parser-v3-v1 locked set against the retired parser-v2-v1 locked inputs"
        ),
        "registered_in": "docs/phase1_parser_v3_sealing_run.md section 9 item 1",
        "mode": mode,
        "started_at_utc": started_at,
        "finished_at_utc": utc_now(),
        "seal_timestamp": seal_timestamp,
        "source": {
            "account": account,
            "container": container,
            "retired_prefix": RETIRED_INPUTS_PREFIX,
            "listed_blob_names": list(listed_names),
            "read_blob_names": [RETIRED_INPUTS_BLOB],
            "not_read_blob_names": [
                name for name in listed_names if name != RETIRED_INPUTS_BLOB
            ],
            "retired_object_sha256": source["sha256"],
            "retired_object_bytes": source["bytes"],
            "registered_sha256": source["registered_sha256"],
            "registered_sha256_match": provenance_ok,
            "label_material_touched": False,
            "score_material_touched": False,
            "rescoring_performed": False,
        },
        "fingerprint_registration": dict(registration),
        "manifest_reproduction": dict(reproduction),
        "new_count": len(new_index["exact_sha256"]),
        "retired_count": len(source["texts"]),
        "exact_collision_count": counts["exact_collision_count"],
        "normalised_collision_count": counts["normalised_collision_count"],
        "numeric_normalised_collision_count": counts[
            "numeric_normalised_collision_count"
        ],
        "collisions": {key: list(value) for key, value in collisions.items()},
        "cross_check": verdict,
        "abort_reasons": abort_reasons,
        "decision": "PROCEED_TO_SEAL" if verdict == "PASS" else "DO_NOT_SEAL",
        "content_disclosure": (
            "counts and one-way digests only; no retired input text, no label "
            "material and no score material crossed this boundary"
        ),
        "prohibited_interpretations": [
            "This is an overlap diagnostic, not a parser-v3 result.",
            "No parser-v3 evaluation was run and no parser-v3 prediction exists.",
            "A passing cross-check does not validate parser v3; it only shows the "
            "instrument does not reuse retired holdout text.",
            "Isolation is procedural, not security-enforced.",
        ],
    }
    assert_report_is_text_free(report, source["texts"])
    return report


# ------------------------------------------------------------------- seal


def seal_parent_prefix(timestamp: str) -> str:
    if not isinstance(timestamp, str) or not SEAL_TIMESTAMP_RE.fullmatch(timestamp):
        raise JobAbort("seal timestamp must have the form YYYYMMDDTHHMMSSZ")
    return f"{SEAL_ROOT}/{timestamp}"


def runlog_prefix(timestamp: str) -> str:
    return f"{SEAL_ROOT}/{timestamp}-runlog"


def seal_blob_names(timestamp: str) -> list[str]:
    parent = seal_parent_prefix(timestamp)
    return [f"{parent}/{item['leaf']}/{item['name']}" for item in SEAL_OBJECTS]


def resolve_payload_path(
    item: Mapping[str, Any], payload_dir: Path | None, repo_root: Path | None
) -> Path:
    if payload_dir is not None:
        return Path(payload_dir) / str(item["name"])
    if repo_root is not None:
        return Path(repo_root) / str(item["source"])
    raise JobAbort("no payload directory and no repository root were supplied")


def load_seal_payload(
    payload_dir: Path | None, repo_root: Path | None
) -> list[dict[str, Any]]:
    """Read the twelve objects and abort on any digest or size mismatch."""
    loaded: list[dict[str, Any]] = []
    for item in SEAL_OBJECTS:
        path = resolve_payload_path(item, payload_dir, repo_root)
        if not path.is_file():
            raise JobAbort(f"seal object is missing from the payload: {item['name']}")
        data = path.read_bytes()
        if len(data) != item["bytes"]:
            raise JobAbort(f"seal object byte count mismatch: {item['name']}")
        digest = sha256_bytes(data)
        if digest != item["sha256"]:
            raise JobAbort(f"seal object SHA-256 mismatch: {item['name']}")
        entry = dict(item)
        entry["data"] = data
        entry["local_path"] = str(path)
        loaded.append(entry)
    if len(loaded) != 12:
        raise JobAbort("the registered seal membership is exactly twelve objects")
    return loaded


def property_value(properties: Any, *names: str) -> Any:
    for name in names:
        if isinstance(properties, Mapping) and name in properties:
            return properties[name]
        value = getattr(properties, name, None)
        if value is not None:
            return value
    return None


def upload_one(service: Any, container: str, blob_name: str, data: bytes) -> str:
    blob = service.get_blob_client(container=container, blob=blob_name)
    try:
        blob.upload_blob(data, overwrite=False)
    except Exception as error:
        raise JobAbort(
            f"overwrite-false upload failed: {blob_name} ({type(error).__name__})"
        ) from None
    properties = blob.get_blob_properties()
    size = property_value(properties, "size", "blob_size")
    if size != len(data):
        raise JobAbort(f"uploaded blob size mismatch: {blob_name}")
    etag = property_value(properties, "etag")
    if not isinstance(etag, str) or not etag:
        raise JobAbort(f"uploaded blob ETag is unavailable: {blob_name}")
    return etag


def verify_one(
    service: Any, container: str, blob_name: str, expected: bytes, etag: str
) -> None:
    blob = service.get_blob_client(container=container, blob=blob_name)
    try:
        downloaded = blob.download_blob().readall()
    except Exception as error:
        raise JobAbort(
            f"cannot re-download sealed object: {blob_name} ({type(error).__name__})"
        ) from None
    downloaded = bytes(downloaded)
    if len(downloaded) != len(expected):
        raise JobAbort(f"re-downloaded blob size mismatch: {blob_name}")
    if sha256_bytes(downloaded) != sha256_bytes(expected):
        raise JobAbort(f"re-downloaded blob SHA-256 mismatch: {blob_name}")
    observed = property_value(blob.get_blob_properties(), "etag")
    if observed != etag:
        raise JobAbort(f"sealed blob ETag changed: {blob_name}")


def list_seal_prefix(service: Any, container: str, timestamp: str) -> set[str]:
    parent = seal_parent_prefix(timestamp)
    client = service.get_container_client(container)
    return {
        blob_name_of(item)
        for item in client.list_blobs(name_starts_with=f"{parent}/")
    }


def assert_prefix_is_empty(service: Any, container: str, timestamp: str) -> None:
    observed = list_seal_prefix(service, container, timestamp)
    if observed:
        raise JobAbort(
            "the seal parent prefix is not empty; the run has already happened, "
            "do not retry under this timestamp"
        )


def seal(
    service: Any,
    container: str,
    timestamp: str,
    payload: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    parent = seal_parent_prefix(timestamp)
    assert_prefix_is_empty(service, container, timestamp)
    ordered = sorted(payload, key=lambda item: int(item["order"]))
    expected_names = set(seal_blob_names(timestamp))
    records: list[dict[str, Any]] = []
    for item in ordered:
        if int(item["order"]) == SET_MANIFEST_ORDER:
            continue
        blob_name = f"{parent}/{item['leaf']}/{item['name']}"
        etag = upload_one(service, container, blob_name, item["data"])
        verify_one(service, container, blob_name, item["data"], etag)
        records.append(
            {
                "order": int(item["order"]),
                "blob_name": blob_name,
                "sha256": item["sha256"],
                "bytes": int(item["bytes"]),
                "etag": etag,
                "uploaded_at_utc": utc_now(),
                "roundtrip_verified": True,
                "content_class": item["content_class"],
            }
        )
    observed = list_seal_prefix(service, container, timestamp)
    eleven = {name for name in expected_names if not name.endswith("/set_manifest.json")}
    if observed != eleven:
        raise JobAbort(
            "eleven-object membership check failed before the closure record; "
            f"missing={len(eleven - observed)} unexpected={len(observed - eleven)}"
        )
    closure = next(
        item for item in ordered if int(item["order"]) == SET_MANIFEST_ORDER
    )
    closure_name = f"{parent}/{closure['leaf']}/{closure['name']}"
    closure_etag = upload_one(service, container, closure_name, closure["data"])
    verify_one(service, container, closure_name, closure["data"], closure_etag)
    records.append(
        {
            "order": int(closure["order"]),
            "blob_name": closure_name,
            "sha256": closure["sha256"],
            "bytes": int(closure["bytes"]),
            "etag": closure_etag,
            "uploaded_at_utc": utc_now(),
            "roundtrip_verified": True,
            "content_class": closure["content_class"],
        }
    )
    final = list_seal_prefix(service, container, timestamp)
    if final != expected_names:
        raise JobAbort(
            "exact twelve-object membership check failed after the closure record"
        )
    return {
        "schema_version": SCHEMA_SEAL_RECORD,
        "parent_prefix": parent,
        "written_last": closure_name,
        "object_count": len(records),
        "objects": records,
        "membership_check": {
            "expected": len(expected_names),
            "observed": len(final),
            "exact_match": True,
        },
        "roundtrip_verification": "size, SHA-256 and ETag verified for all 12 objects",
        "overwrite": False,
        "authentication": "ManagedIdentityCredential",
        "account_key_used": False,
        "sas_used": False,
        "public_network_access": "disabled",
        "status": "SEALED",
    }


# ------------------------------------------------------------------ wiring


def validate_managed_identity(account_url: str, environment: Mapping[str, str]) -> str:
    normalized = {
        key.upper(): value for key, value in environment.items() if isinstance(key, str)
    }
    for name in _PROHIBITED_CREDENTIAL_ENV:
        if normalized.get(name):
            raise JobAbort(f"prohibited key/SAS credential is set: {name}")
    client_id = normalized.get("AZURE_CLIENT_ID")
    if not isinstance(client_id, str) or not client_id:
        raise JobAbort("AZURE_CLIENT_ID is required; this job is managed identity only")
    parsed = urlsplit(account_url)
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.port not in {None, 443}
    ):
        raise JobAbort("account URL must be a credential-free HTTPS Blob service root")
    if not _ACCOUNT_HOST_PATTERN.fullmatch(parsed.hostname or ""):
        raise JobAbort("account URL must use the registered Azure Blob endpoint")
    return client_id


def create_blob_service(account_url: str, environment: Mapping[str, str]) -> Any:
    client_id = validate_managed_identity(account_url, environment)
    identity_module = importlib.import_module("azure.identity")
    blob_module = importlib.import_module("azure.storage.blob")
    credential = identity_module.ManagedIdentityCredential(client_id=client_id)
    return blob_module.BlobServiceClient(
        account_url=account_url.rstrip("/"), credential=credential
    )


def validate_container(container: str) -> str:
    if (
        not isinstance(container, str)
        or not _CONTAINER_PATTERN.fullmatch(container)
        or "--" in container
    ):
        raise JobAbort("container name is invalid")
    return container


def upload_sidecar(
    service: Any, container: str, timestamp: str, name: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    """Write the report or the seal record beside, never inside, the seal."""
    data = canonical_json_bytes(payload)
    blob_name = f"{runlog_prefix(timestamp)}/{name}"
    etag = upload_one(service, container, blob_name, data)
    verify_one(service, container, blob_name, data, etag)
    return {
        "blob_name": blob_name,
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "etag": etag,
    }


def run(
    *,
    mode: str,
    account: str,
    container: str,
    seal_timestamp: str | None,
    builder_path: Path,
    manifest_path: Path,
    locked_inputs: Path | None,
    payload_dir: Path | None,
    repo_root: Path | None,
    environment: Mapping[str, str],
    service_factory: Any = None,
    emit: Any = print,
) -> tuple[int, dict[str, Any]]:
    started_at = utc_now()
    container = validate_container(container)
    module = load_builder_module(builder_path)
    registration = verify_fingerprint_registration(module)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    reproduction = verify_manifest_reproduction(module, manifest, locked_inputs)
    new_index = new_fingerprint_index(manifest)
    for field in MANIFEST_FIELDS:
        if len(new_index[field]) != 120:
            raise JobAbort(
                f"expected 120 distinct {field} fingerprints in the inputs manifest"
            )
    emit(f"[gate] fingerprint registration: {registration['status']}")
    emit(f"[gate] manifest reproduction: {reproduction['status']}")

    if mode == "preflight":
        payload = load_seal_payload(payload_dir, repo_root)
        emit(f"[preflight] verified {len(payload)} seal objects against Track D digests")
        summary = {
            "mode": "preflight",
            "started_at_utc": started_at,
            "finished_at_utc": utc_now(),
            "fingerprint_registration": registration,
            "manifest_reproduction": reproduction,
            "seal_objects_verified": len(payload),
            "cross_check": "NOT PERFORMED",
            "status": "PREFLIGHT_OK",
            "state": "PREFLIGHT_OK",
        }
        emit("[preflight] cross_check=NOT PERFORMED (no Azure access in this mode)")
        return 0, summary

    account_url = f"https://{account}.blob.core.windows.net"
    factory = service_factory or (lambda: create_blob_service(account_url, environment))
    service = factory()

    listed = list_retired_inputs(service, container)
    emit(f"[source] listed {len(listed)} objects under the retired locked-inputs leaf")
    source = read_retired_inputs(service, container)
    emit(f"[source] retired records with output-bearing text: {len(source['texts'])}")
    collisions = compare_fingerprints(
        module, new_index, source["texts"], source["case_ids"]
    )
    report = build_crosscheck_report(
        account=account,
        container=container,
        listed_names=listed,
        source=source,
        registration=registration,
        reproduction=reproduction,
        new_index=new_index,
        collisions=collisions,
        started_at=started_at,
        seal_timestamp=seal_timestamp,
        mode=mode,
    )
    emit(
        "[crosscheck] new_count={new_count} retired_count={retired_count} "
        "exact={exact_collision_count} normalised={normalised_collision_count} "
        "numeric_normalised={numeric_normalised_collision_count} "
        "verdict={cross_check}".format(**report)
    )

    if seal_timestamp:
        sidecar = upload_sidecar(
            service, container, seal_timestamp, "crosscheck_report.json", report
        )
        report = dict(report)
        report["report_blob"] = sidecar
        emit(f"[crosscheck] report written to {sidecar['blob_name']}")

    if report["cross_check"] == "FAIL":
        emit("[decision] DO NOT SEAL: at least one fingerprint collision")
        return 2, {"crosscheck": report, "seal": None, "state": "BLOCKED_COLLISION"}
    if report["cross_check"] != "PASS":
        emit("[decision] DO NOT SEAL: cross-check aborted on a guard")
        return 3, {"crosscheck": report, "seal": None, "state": "BLOCKED_INFRASTRUCTURE"}

    if mode == "crosscheck":
        emit("[decision] cross-check PASS; seal not requested in this mode")
        return 0, {"crosscheck": report, "seal": None, "state": "CROSSCHECK_PASS"}

    if not seal_timestamp:
        raise JobAbort("seal mode requires an explicit --seal-timestamp")
    payload = load_seal_payload(payload_dir, repo_root)
    emit(f"[seal] verified {len(payload)} local objects against Track D digests")
    seal_record = seal(service, container, seal_timestamp, payload)
    seal_record["crosscheck_report_blob"] = report.get("report_blob", {}).get(
        "blob_name"
    )
    seal_record["crosscheck_report_sha256"] = report.get("report_blob", {}).get("sha256")
    seal_record["crosscheck"] = {
        "verdict": report["cross_check"],
        "exact_collision_count": report["exact_collision_count"],
        "normalised_collision_count": report["normalised_collision_count"],
        "numeric_normalised_collision_count": report[
            "numeric_normalised_collision_count"
        ],
    }
    seal_record["prohibited_interpretations"] = [
        "Sealing does not validate parser v3 and licenses no accuracy claim.",
        "No parser-v3 evaluation was run and no parser-v3 prediction exists.",
        "The labels are an LLM operational consensus, not human ground truth.",
        "Isolation from parser-v3 development is procedural, not security-enforced.",
    ]
    sidecar = upload_sidecar(
        service, container, seal_timestamp, "seal_record.json", seal_record
    )
    seal_record["seal_record_blob"] = sidecar
    emit(f"[seal] SEALED {seal_record['object_count']} objects at {seal_record['parent_prefix']}")
    return 0, {"crosscheck": report, "seal": seal_record, "state": "SEALED"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("preflight", "crosscheck", "seal"),
        default="crosscheck",
        help="preflight verifies locally; crosscheck reads the retired inputs; "
        "seal additionally writes the twelve registered objects on PASS",
    )
    parser.add_argument("--account", default="stjspacefiles0709085305")
    parser.add_argument("--container", default="jspace-results")
    parser.add_argument(
        "--seal-timestamp",
        default=None,
        help="UTC stamp YYYYMMDDTHHMMSSZ chosen before the run so the ABAC write "
        "condition can be pinned to it",
    )
    parser.add_argument("--builder", default=None)
    parser.add_argument("--inputs-manifest", default=None)
    parser.add_argument("--locked-inputs", default=None)
    parser.add_argument("--payload-dir", default=None)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--out", default=None, help="write the run summary JSON here")
    return parser


def _default_paths(
    args: argparse.Namespace,
) -> tuple[Path, Path, Path | None, Path | None, Path | None]:
    payload_dir = Path(args.payload_dir) if args.payload_dir else None
    repo_root = Path(args.repo_root) if args.repo_root else None
    if payload_dir is None and repo_root is None:
        here = Path(__file__).resolve().parent
        if (here.parent / "evaluator_sets").is_dir():
            repo_root = here.parent
        else:
            payload_dir = here
    builder = (
        Path(args.builder)
        if args.builder
        else (
            (payload_dir / "build_parser_v3_validation_set.py")
            if payload_dir is not None
            else (repo_root / "scripts" / "build_parser_v3_validation_set.py")
        )
    )
    manifest = (
        Path(args.inputs_manifest)
        if args.inputs_manifest
        else (
            (payload_dir / "inputs_manifest.json")
            if payload_dir is not None
            else (
                repo_root
                / "evaluator_sets"
                / "parser_v3_v1"
                / "manifests"
                / "inputs_manifest.json"
            )
        )
    )
    locked = (
        Path(args.locked_inputs)
        if args.locked_inputs
        else (
            (payload_dir / "locked_inputs.jsonl")
            if payload_dir is not None
            else (repo_root / "evaluator_sets" / "parser_v3_v1" / "locked_inputs.jsonl")
        )
    )
    return builder, manifest, locked, payload_dir, repo_root


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    builder, manifest, locked, payload_dir, repo_root = _default_paths(args)
    try:
        code, summary = run(
            mode=args.mode,
            account=args.account,
            container=args.container,
            seal_timestamp=args.seal_timestamp,
            builder_path=builder,
            manifest_path=manifest,
            locked_inputs=locked,
            payload_dir=payload_dir,
            repo_root=repo_root,
            environment=os.environ,
        )
    except JobAbort as error:
        print(f"[ABORT] {error}")
        print("state=BLOCKED_INFRASTRUCTURE")
        return 3
    if args.out:
        Path(args.out).write_bytes(canonical_json_bytes(summary))
    print(json.dumps({"state": summary.get("state", "UNKNOWN")}, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
