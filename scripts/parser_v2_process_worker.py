#!/usr/local/bin/python3.11 -I
"""One-request isolated process for the exact frozen parser-v2 extraction."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


_MAX_REQUEST_BYTES = 1 << 20
_REQUEST_FIELDS = {"schema_version", "answer_type", "output_text"}
_REQUEST_SCHEMA = "phase1-parser-v2-request/v1"
_RESULT_SCHEMA = "phase1-parser-v2-result/v1"
_RESULT_FIELDS = {
    "schema_version",
    "parser_version",
    "answer_type",
    "input_sha256",
    "answer_presence",
    "parse_valid",
    "parse_ambiguous",
    "parsed_answer",
    "candidate_answers",
    "evidence_spans",
    "extraction_strategy",
    "output_quality",
    "failure_reasons",
    "format_warnings",
}
_EXPECTED_EVALUATOR_SHA256 = (
    "63eb1c7d8b229dddafdd3d54a0d62bb415d76ae8dd5aab220bd91ff054f08344"
)
_EXPECTED_PARSER_SOURCE_SHA256 = (
    "f538add0bdd6e5a3281d0298b374a99fecea962a91a4cbaa5b4a20795d9a6918"
)
_EXPECTED_PARSER_VERSION = (
    "6cfaec62db37562930a4cb7d3a252bcbf80e1eaf748de98213863ff2566a7f86"
)
_EXPECTED_ENVIRONMENT = {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}


class _DuplicateField(ValueError):
    pass


def _pairs_to_exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateField
        result[key] = value
    return result


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_frozen_parser() -> Any:
    source_root = Path(__file__).resolve().parents[1] / "src" / "jspace_observation"
    evaluator_path = source_root / "evaluator_validation.py"
    parser_path = source_root / "eval_parsing_v2.py"
    evaluator_source = evaluator_path.read_bytes().replace(b"\r\n", b"\n").replace(
        b"\r", b"\n"
    )
    if hashlib.sha256(evaluator_source).hexdigest() != _EXPECTED_EVALUATOR_SHA256:
        raise RuntimeError
    package_name = "_jspace_isolated_frozen_parser"
    package = ModuleType(package_name)
    package.__path__ = [str(source_root)]  # type: ignore[attr-defined]
    package.__package__ = package_name
    sys.modules[package_name] = package
    _load_module(f"{package_name}.evaluator_validation", evaluator_path)
    parser = _load_module(f"{package_name}.eval_parsing_v2", parser_path)
    source = parser_path.read_bytes()
    if (
        parser.PARSER_SOURCE_SHA256 != _EXPECTED_PARSER_SOURCE_SHA256
        or parser.PARSER_VERSION != _EXPECTED_PARSER_VERSION
        or parser.compute_parser_source_sha256(source)
        != _EXPECTED_PARSER_SOURCE_SHA256
        or parser.compute_parser_version(_EXPECTED_PARSER_SOURCE_SHA256)
        != _EXPECTED_PARSER_VERSION
    ):
        raise RuntimeError
    return parser.parse_v2


def _read_request() -> dict[str, str]:
    data = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
    if (
        not data
        or len(data) > _MAX_REQUEST_BYTES
        or not data.endswith(b"\n")
        or b"\n" in data[:-1]
    ):
        raise ValueError
    request = json.loads(
        data[:-1].decode("utf-8"),
        object_pairs_hook=_pairs_to_exact_object,
        parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
    )
    if (
        type(request) is not dict
        or set(request) != _REQUEST_FIELDS
        or any(type(request[name]) is not str for name in _REQUEST_FIELDS)
        or request["schema_version"] != _REQUEST_SCHEMA
        or request["answer_type"] != "numeric"
        or _canonical_json_bytes(request) != data
    ):
        raise ValueError
    return request


def main() -> int:
    try:
        if dict(os.environ) != _EXPECTED_ENVIRONMENT:
            raise RuntimeError
        request = _read_request()
        result = dict(_load_frozen_parser()(request))
        if (
            set(result) != _RESULT_FIELDS
            or result.get("schema_version") != _RESULT_SCHEMA
            or result.get("parser_version") != _EXPECTED_PARSER_VERSION
            or result.get("answer_type") != "numeric"
            or result.get("input_sha256")
            != hashlib.sha256(request["output_text"].encode("utf-8")).hexdigest()
        ):
            raise RuntimeError
        response = _canonical_json_bytes(result)
        sys.stdout.buffer.write(response)
        sys.stdout.buffer.flush()
        return 0
    except Exception:
        sys.stderr.write("parser worker rejected request\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
