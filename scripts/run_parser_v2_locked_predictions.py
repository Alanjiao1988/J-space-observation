#!/usr/bin/env python3
"""Run the one allowed label-blind Stage-P parser evaluation."""

from __future__ import annotations

import argparse
import ast
import dataclasses
import hashlib
import importlib.util
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Any, Callable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = (
    PROJECT_ROOT
    / "src"
    / "jspace_observation"
    / "parser_v2_locked_evaluation.py"
)
PARSER_V2_WORKER_PATH = PROJECT_ROOT / "scripts" / "parser_v2_process_worker.py"
LEGACY_PARSER_PATH = (
    PROJECT_ROOT / "src" / "jspace_observation" / "eval_parsing.py"
)
_EXECUTION_ID_PATTERN = re.compile(r"stage-p-[0-9a-f]{32}\Z", re.ASCII)
_PARSER_REQUEST_FIELDS = {"schema_version", "answer_type", "output_text"}
_PARSER_REQUEST_SCHEMA = "phase1-parser-v2-request/v1"
_PARSER_RESULT_SCHEMA = "phase1-parser-v2-result/v1"
_PARSER_V2_VERSION = (
    "6cfaec62db37562930a4cb7d3a252bcbf80e1eaf748de98213863ff2566a7f86"
)
_PARSER_RESULT_FIELDS = {
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
_MAX_PARSER_WORKER_RESPONSE_BYTES = 1 << 20


class _RedactedArgumentError(Exception):
    pass


class _RedactedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        raise _RedactedArgumentError("arguments rejected")

    def parse_args(
        self,
        args: Sequence[str] | None = None,
        namespace: argparse.Namespace | None = None,
    ) -> argparse.Namespace:
        raw = list(sys.argv[1:] if args is None else args)
        actions = {
            option: action
            for action in self._actions
            for option in action.option_strings
        }
        seen: set[str] = set()
        index = 0
        while index < len(raw):
            option = raw[index]
            action = actions.get(option)
            if (
                action is None
                or not option.startswith("--")
                or "=" in option
                or option in seen
            ):
                self.error("invalid argument shape")
            seen.add(option)
            index += 1
            if action.nargs != 0:
                if index >= len(raw) or raw[index].startswith("--"):
                    self.error("missing argument value")
                index += 1
        return super().parse_args(raw, namespace)


def _execution_id(value: str) -> str:
    if _EXECUTION_ID_PATTERN.fullmatch(value) is None:
        raise argparse.ArgumentTypeError("execution ID is not exact")
    return value


def _load_file_module(name: str, path: Path) -> ModuleType:
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_core() -> ModuleType:
    return _load_file_module("_jspace_parser_v2_locked_eval_stage_p", CORE_PATH)


def _git_blob_oid(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def _load_frozen_legacy_numeric_parser() -> Callable[[str], Any]:
    core = _load_core()
    source = LEGACY_PARSER_PATH.read_bytes().replace(b"\r\n", b"\n").replace(
        b"\r", b"\n"
    )
    if (
        core.FROZEN_LEGACY_PARSER_COMMIT != core.FROZEN_STARTING_COMMIT
        or hashlib.sha256(source).hexdigest()
        != core.FROZEN_LEGACY_PARSER_SOURCE_SHA256
        or _git_blob_oid(source) != core.FROZEN_LEGACY_PARSER_GIT_BLOB_OID
    ):
        raise RuntimeError("frozen legacy parser provenance mismatch")
    try:
        tree = ast.parse(source.decode("utf-8"), filename="<frozen-legacy-parser>")
    except (UnicodeDecodeError, SyntaxError):
        raise RuntimeError("frozen legacy parser source is invalid") from None
    result_nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ParseResult"
    ]
    parser_nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "parse_numeric_answer"
    ]
    if (
        len(result_nodes) != 1
        or len(parser_nodes) != 1
        or isinstance(parser_nodes[0], ast.AsyncFunctionDef)
    ):
        raise RuntimeError("frozen legacy numeric parser extraction is not exact")
    extracted = ast.Module(
        body=[
            ast.Import(names=[ast.alias(name="re")]),
            ast.ImportFrom(
                module="dataclasses",
                names=[ast.alias(name="dataclass")],
                level=0,
            ),
            ast.ImportFrom(
                module="typing",
                names=[ast.alias(name="Optional")],
                level=0,
            ),
            result_nodes[0],
            parser_nodes[0],
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(extracted)
    namespace: dict[str, Any] = {
        "__name__": "_jspace_stage_p_legacy_numeric_only"
    }
    try:
        exec(
            compile(
                extracted,
                filename="<frozen-legacy-parse-numeric-answer>",
                mode="exec",
                dont_inherit=True,
            ),
            namespace,
        )
    except Exception:
        raise RuntimeError("frozen legacy numeric parser extraction failed") from None
    extracted_parser = namespace.get("parse_numeric_answer")
    result_type = namespace.get("ParseResult")
    if not callable(extracted_parser) or not isinstance(result_type, type):
        raise RuntimeError("frozen legacy numeric parser is unavailable")
    safe_namespace: dict[str, Any] = {
        "__builtins__": {"bool": bool, "len": len},
        "__name__": "_jspace_stage_p_legacy_numeric_only",
        "ParseResult": result_type,
        "re": namespace["re"],
    }
    parser = FunctionType(
        extracted_parser.__code__,
        safe_namespace,
        name="parse_numeric_answer",
        argdefs=extracted_parser.__defaults__,
        closure=extracted_parser.__closure__,
    )
    parser.__annotations__ = dict(extracted_parser.__annotations__)
    parser.__doc__ = extracted_parser.__doc__
    parser.__kwdefaults__ = extracted_parser.__kwdefaults__
    parser.__module__ = safe_namespace["__name__"]
    parser.__qualname__ = "parse_numeric_answer"
    safe_namespace["parse_numeric_answer"] = parser
    namespace.clear()
    if any(
        name in safe_namespace
        for name in (
            "create_eval_record",
            "evaluate_answer",
            "parse_answer",
            "parse_and_score",
        )
    ):
        raise RuntimeError("legacy correctness API was retained")
    return parser


def _parser_worker_environment() -> dict[str, str]:
    return {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}


def _invoke_parser_v2_worker(request: Mapping[str, Any]) -> dict[str, Any]:
    if (
        type(request) is not dict
        or set(request) != _PARSER_REQUEST_FIELDS
        or any(type(request[name]) is not str for name in _PARSER_REQUEST_FIELDS)
        or request["schema_version"] != _PARSER_REQUEST_SCHEMA
        or request["answer_type"] != "numeric"
    ):
        raise RuntimeError("isolated parser-v2 request rejected")
    worker = PARSER_V2_WORKER_PATH.resolve(strict=True)
    interpreter = Path(sys.executable).resolve(strict=True)
    if (
        not worker.is_file()
        or not interpreter.is_file()
        or not worker.is_relative_to(PROJECT_ROOT.resolve(strict=True))
    ):
        raise RuntimeError("isolated parser-v2 runtime rejected")
    request_bytes = (
        json.dumps(
            request,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    try:
        completed = subprocess.run(
            [
                str(interpreter),
                "-I",
                "-S",
                "-X",
                "utf8",
                str(worker),
            ],
            input=request_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_parser_worker_environment(),
            cwd=worker.parent,
            check=False,
            close_fds=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        raise RuntimeError("isolated parser-v2 worker unavailable") from None
    stdout = completed.stdout
    if (
        completed.returncode != 0
        or completed.stderr
        or not stdout.endswith(b"\n")
        or len(stdout) > _MAX_PARSER_WORKER_RESPONSE_BYTES
        or b"\n" in stdout[:-1]
    ):
        raise RuntimeError("isolated parser-v2 worker rejected request")
    try:
        result = json.loads(
            stdout[:-1].decode("utf-8"),
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
        canonical = (
            json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
    except (UnicodeDecodeError, ValueError, TypeError):
        raise RuntimeError("isolated parser-v2 worker returned invalid data") from None
    if (
        type(result) is not dict
        or canonical != stdout
        or set(result) != _PARSER_RESULT_FIELDS
        or result.get("schema_version") != _PARSER_RESULT_SCHEMA
        or result.get("parser_version") != _PARSER_V2_VERSION
        or result.get("answer_type") != "numeric"
        or result.get("input_sha256")
        != hashlib.sha256(request["output_text"].encode("utf-8")).hexdigest()
    ):
        raise RuntimeError("isolated parser-v2 worker returned noncanonical data")
    return result


class _ParserV2ProcessFacade:
    __slots__ = ()

    def __getattribute__(self, name: str) -> Any:
        del name
        raise AttributeError("isolated parser-v2 facade exposes no attributes")

    def __dir__(self) -> list[str]:
        return []

    def __call__(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        return _invoke_parser_v2_worker(request)


def _load_stage_p_parsers() -> tuple[Callable[..., Any], Callable[..., Any]]:
    return _ParserV2ProcessFacade(), _load_frozen_legacy_numeric_parser()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_prediction_rows(
    locked_inputs: Sequence[Mapping[str, Any]],
    *,
    parse_v2: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    parse_legacy: Callable[[str], Any],
    core: ModuleType,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Invoke each frozen parser exactly once for every ordered input."""
    predictions: list[dict[str, Any]] = []
    legacy_predictions: list[dict[str, Any]] = []
    v2_calls = 0
    legacy_calls = 0
    for locked_input in locked_inputs:
        request = core.project_parser_request(locked_input)
        if set(request) != {"schema_version", "answer_type", "output_text"}:
            raise core.LockedEvaluationError(
                "parser-v2 request is not the exact frozen three-field interface"
            )
        parser_result = dict(parse_v2(request))
        v2_calls += 1
        legacy_result_object = parse_legacy(request["output_text"])
        legacy_calls += 1
        if not dataclasses.is_dataclass(legacy_result_object):
            raise core.LockedEvaluationError(
                "legacy parser did not return its frozen dataclass result"
            )
        legacy_result = dataclasses.asdict(legacy_result_object)
        predictions.append(
            core.build_prediction_envelope(locked_input, parser_result)
        )
        legacy_predictions.append(
            core.build_legacy_prediction(locked_input, legacy_result)
        )
    if v2_calls != len(locked_inputs) or legacy_calls != len(locked_inputs):
        raise core.LockedEvaluationError("parser invocation count is not exact")
    return predictions, legacy_predictions


def _assert_exact_source_names(
    core: ModuleType,
    *,
    parent_prefix: str,
    locked_input_blob: str,
    locked_input_manifest_blob: str,
) -> None:
    parent = core.validate_registered_parent_prefix(parent_prefix)
    if locked_input_blob != f"{parent}/locked-inputs/locked_inputs.jsonl":
        raise core.LockedEvaluationError("locked-input Blob name is not exact")
    if (
        locked_input_manifest_blob
        != f"{parent}/locked-inputs/locked_inputs_manifest.json"
    ):
        raise core.LockedEvaluationError(
            "locked-input manifest Blob name is not exact"
        )


def _is_definite_create_conflict(error: BaseException) -> bool:
    pending: list[BaseException] = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        status_code = getattr(current, "status_code", None)
        error_code = getattr(current, "error_code", None)
        normalized_code = (
            re.sub(r"[^a-z0-9]", "", error_code.casefold())
            if isinstance(error_code, str)
            else ""
        )
        if (
            status_code in {409, 412}
            or current.__class__.__name__ == "ResourceExistsError"
            or normalized_code
            in {
                "blobalreadyexists",
                "conditionnotmet",
                "resourcealreadyexists",
            }
        ):
            return True
        for nested in (current.__cause__, current.__context__):
            if isinstance(nested, BaseException):
                pending.append(nested)
    return False


def _authenticate_durable_input_receipt(
    core: ModuleType,
    service: Any,
    *,
    container: str,
    state_prefix: str,
    input_receipt: Mapping[str, Any],
    expected_etag: str | None = None,
) -> dict[str, Any]:
    checked = core.validate_state_receipt(
        input_receipt, name="expected INPUTS_READ receipt"
    )
    if checked["state"] != "INPUTS_READ" or input_receipt["retry_kind"] != "none":
        raise core.LockedEvaluationError(
            "durable input evidence is not the primary INPUTS_READ receipt"
        )
    expected_bytes = core.canonical_json_bytes(dict(input_receipt))
    blob_name = core.state_receipt_blob_name(state_prefix, input_receipt)
    persisted_bytes, persisted_etag = core.download_stable_blob(
        service, container, blob_name
    )
    persisted_receipt = core.parse_json_strict(
        persisted_bytes, "persisted INPUTS_READ receipt"
    )
    if (
        persisted_bytes != expected_bytes
        or not core.exact_json_equal(persisted_receipt, dict(input_receipt))
        or (
            expected_etag is not None
            and persisted_etag != expected_etag
        )
    ):
        raise core.LockedEvaluationError(
            "persisted INPUTS_READ receipt bytes/ETag differ"
        )
    core.validate_state_receipt(
        persisted_receipt, name="persisted INPUTS_READ receipt"
    )
    return {
        "blob_name": blob_name,
        "size": len(persisted_bytes),
        "sha256": core.sha256_bytes(persisted_bytes),
        "etag": persisted_etag,
        "receipt": persisted_receipt,
    }


def persist_input_receipt_then_read_inputs(
    core: ModuleType,
    service: Any,
    *,
    container: str,
    state_prefix: str,
    input_receipt: Mapping[str, Any],
    locked_input_blob: str,
    locked_input_sha256: str,
    locked_input_size: int,
    parent_prefix: str | None = None,
    registered_parent_members_after_receipt: Sequence[str] | None = None,
) -> tuple[dict[str, Any], bytes, str]:
    """Spend the holdout durably before constructing the input payload client."""
    try:
        created = core.persist_state_receipt(
            service, container, state_prefix, input_receipt
        )
    except Exception as error:
        if _is_definite_create_conflict(error):
            raise core.LockedEvaluationError(
                "overwrite-false INPUTS_READ create conflict; "
                "input reread is prohibited"
            ) from error
        try:
            authenticated = _authenticate_durable_input_receipt(
                core,
                service,
                container=container,
                state_prefix=state_prefix,
                input_receipt=input_receipt,
            )
        except Exception as authentication_error:
            raise core.LockedEvaluationError(
                "INPUTS_READ receipt was not proven durable"
            ) from authentication_error
    else:
        if not isinstance(created, Mapping):
            raise core.LockedEvaluationError(
                "INPUTS_READ persistence metadata is invalid"
            )
        authenticated = _authenticate_durable_input_receipt(
            core,
            service,
            container=container,
            state_prefix=state_prefix,
            input_receipt=input_receipt,
            expected_etag=created.get("etag"),
        )
        if any(
            not core.exact_json_equal(created.get(field), authenticated[field])
            for field in ("blob_name", "size", "sha256", "etag")
        ):
            raise core.LockedEvaluationError(
                "INPUTS_READ persistence metadata differs from durable bytes"
            )
    receipt_persistence = {
        field: authenticated[field]
        for field in ("blob_name", "size", "sha256", "etag")
    }
    if (
        parent_prefix is not None
        or registered_parent_members_after_receipt is not None
    ):
        if (
            parent_prefix is None
            or registered_parent_members_after_receipt is None
        ):
            raise core.LockedEvaluationError(
                "input exposure parent verification is incomplete"
            )
        core.validate_registered_parent_membership(
            service,
            container,
            parent_prefix,
            registered_parent_members_after_receipt,
        )
    locked_input_bytes, locked_input_etag = core.download_verified_blob(
        service,
        container,
        locked_input_blob,
        expected_sha256=locked_input_sha256,
        expected_size=locked_input_size,
    )
    return receipt_persistence, locked_input_bytes, locked_input_etag


def _prediction_member_blobs(core: ModuleType, prediction_prefix: str) -> set[str]:
    return {
        f"{prediction_prefix}/{name}" for name in core.PREDICTION_MEMBER_NAMES
    }


def _stable_attempt_members(
    core: ModuleType,
    service: Any,
    container: str,
    members: Sequence[str] | set[str],
) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    metadata: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {}
    for blob_name in sorted(members):
        data, etag = core.download_stable_blob(
            service, container, blob_name
        )
        metadata.append(
            {
                "blob_name": blob_name,
                "size": len(data),
                "sha256": core.sha256_bytes(data),
                "etag": etag,
            }
        )
        payloads[blob_name] = data
    core.attempt_membership_sha256(metadata)
    return metadata, payloads


def _direct_leaf_members(root: str, members: set[str]) -> set[str]:
    attempt_root = f"{root}/attempts/"
    return {member for member in members if not member.startswith(attempt_root)}


def _validate_prediction_reservation(
    core: ModuleType,
    data: bytes,
    args: argparse.Namespace,
    *,
    prefix: str,
    retry_kind: str,
    execution_id: str,
) -> dict[str, Any]:
    reservation = core.parse_json_strict(data, "prediction reservation")
    core._require_exact_fields(
        reservation,
        {
            "schema_version",
            "leaf",
            "prefix",
            "authorization_id",
            "created_utc",
            "nonce",
            "overwrite",
        },
        "prediction reservation",
    )
    rebuilt = core.build_reservation(
        leaf=reservation["leaf"],
        prefix=reservation["prefix"],
        authorization_id=reservation["authorization_id"],
        created_utc=reservation["created_utc"],
        nonce=reservation["nonce"],
        parent_prefix=args.parent_prefix,
        stage="P",
        retry_kind=retry_kind,
        execution_id=execution_id,
    )
    if (
        not core.exact_json_equal(reservation, rebuilt)
        or reservation["leaf"] != "predictions"
        or reservation["prefix"] != prefix
        or reservation["authorization_id"] != args.authorization_id
        or data != core.canonical_json_bytes(reservation)
    ):
        raise core.LockedEvaluationError(
            "prediction reservation attempt binding is not exact"
        )
    return reservation


def _load_primary_abandoned_attempt(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    *,
    roots: Mapping[str, str],
) -> dict[str, Any]:
    all_predictions = core.list_exact_prefix(
        service, args.container, roots["predictions"]
    )
    all_visibility = core.list_exact_prefix(
        service, args.container, roots["visibility"]
    )
    primary_predictions = _direct_leaf_members(
        roots["predictions"], all_predictions
    )
    primary_visibility = _direct_leaf_members(
        roots["visibility"], all_visibility
    )
    foreign_predictions = all_predictions - primary_predictions
    foreign_visibility = all_visibility - primary_visibility
    if any(
        not member.startswith(f"{args.predictions_prefix}/")
        for member in foreign_predictions
    ) or any(
        not member.startswith(f"{args.visibility_prefix}/")
        for member in foreign_visibility
    ):
        raise core.LockedEvaluationError(
            "Stage-P retry contains an unbound nested attempt"
        )

    expected_primary_visibility = {
        f"{roots['visibility']}/stage_p_visibility.json"
    }
    if primary_visibility != expected_primary_visibility:
        raise core.LockedEvaluationError(
            "Stage-P retry requires exactly one primary visibility record"
        )
    primary_names = tuple(core.PREDICTION_MEMBER_NAMES)
    expected_initials = [
        {
            f"{roots['predictions']}/{name}"
            for name in primary_names[:index]
        }
        for index in range(len(primary_names))
    ]
    if primary_predictions not in expected_initials:
        raise core.LockedEvaluationError(
            "primary prediction root is not an immutable allowed partial set"
        )

    prediction_metadata, prediction_payloads = _stable_attempt_members(
        core, service, args.container, primary_predictions
    )
    visibility_metadata, visibility_payloads = _stable_attempt_members(
        core, service, args.container, primary_visibility
    )
    visibility_blob = next(iter(primary_visibility))
    visibility_bytes = visibility_payloads[visibility_blob]
    primary_record = core.parse_json_strict(
        visibility_bytes, "primary Stage-P visibility record"
    )
    core.validate_visibility_record(
        primary_record,
        expected_stage="P",
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_retry_kind="none",
    )
    if (
        visibility_bytes != core.canonical_json_bytes(primary_record)
        or primary_record["execution_id"] == args.execution_id
    ):
        raise core.LockedEvaluationError(
            "Stage-P retry does not identify a distinct primary attempt"
        )

    if primary_predictions:
        reservation_blob = (
            f"{roots['predictions']}/{core.PREDICTION_MEMBER_NAMES[0]}"
        )
        _validate_prediction_reservation(
            core,
            prediction_payloads[reservation_blob],
            args,
            prefix=roots["predictions"],
            retry_kind="none",
            execution_id=primary_record["execution_id"],
        )
    request_blob = (
        f"{roots['predictions']}/prediction_request_manifest.json"
    )
    if request_blob in prediction_payloads:
        request = core.parse_json_strict(
            prediction_payloads[request_blob],
            "primary prediction request manifest",
        )
        core.validate_prediction_request_manifest(
            request,
            expected_authorization_id=args.authorization_id,
            expected_parent_prefix=args.parent_prefix,
            expected_retry_kind="none",
            expected_execution_id=primary_record["execution_id"],
        )
        primary_visibility_binding = visibility_metadata[0]
        if (
            request["visibility_blob"] != visibility_blob
            or request["visibility_sha256"]
            != primary_visibility_binding["sha256"]
            or request["visibility_etag"] != primary_visibility_binding["etag"]
        ):
            raise core.LockedEvaluationError(
                "primary partial request does not bind primary visibility"
            )

    return {
        "prediction_members": primary_predictions,
        "visibility_members": primary_visibility,
        "metadata": sorted(
            [*prediction_metadata, *visibility_metadata],
            key=lambda item: item["blob_name"],
        ),
        "visibility": primary_record,
    }


def _retry_receipt_for_attempt(
    core: ModuleType,
    authorization: Mapping[str, Any],
    args: argparse.Namespace,
) -> Mapping[str, Any] | None:
    matching = [
        receipt
        for receipt in authorization["receipts"]
        if receipt["retry_kind"] == args.retry_kind
    ]
    if len(matching) > 1:
        raise core.LockedEvaluationError(
            "Stage-P retry receipt membership is not exact"
        )
    return None if not matching else matching[0]


def _validate_stage_p_attempt_membership(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    *,
    state_members: set[str],
    context: Mapping[str, Any] | None,
    prediction_metadata: Sequence[Mapping[str, Any]],
    visibility_metadata: Sequence[Mapping[str, Any]],
) -> dict[str, set[str]]:
    if context is None:
        primary_membership = {
            "predictions": {
                item["blob_name"] for item in prediction_metadata
            },
            "scores": set(),
            "state": set(state_members),
            "visibility": {
                item["blob_name"] for item in visibility_metadata
            },
        }
        expected = core.expected_authorization_attempt_membership(
            args.parent_prefix,
            args.authorization_id,
            [],
            primary_membership=primary_membership,
        )
    else:
        current_descriptor = core.build_attempt_membership_descriptor(
            parent_prefix=args.parent_prefix,
            authorization_id=args.authorization_id,
            stage="P",
            retry_kind=args.retry_kind,
            execution_id=args.execution_id,
            members=sorted(
                [*prediction_metadata, *visibility_metadata],
                key=lambda item: item["blob_name"],
            ),
        )
        expected = core.expected_authorization_attempt_membership(
            args.parent_prefix,
            args.authorization_id,
            [context["abandoned_record"], current_descriptor],
            primary_membership={
                "predictions": set(context["primary_prediction_members"]),
                "scores": set(),
                "state": set(state_members),
                "visibility": set(context["primary_visibility_members"]),
            },
        )
    core.validate_authorization_membership(
        service,
        args.container,
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        expected=expected,
    )
    core.validate_registered_parent_membership(
        service,
        args.container,
        args.parent_prefix,
        core.expected_registered_parent_membership(
            args.parent_prefix,
            set().union(*expected.values()),
        ),
    )
    return expected


def _load_current_retry_predictions(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    *,
    before_input: bool,
) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    members = core.list_exact_prefix(
        service, args.container, args.predictions_prefix
    )
    ordered = tuple(core.PREDICTION_MEMBER_NAMES)
    maximum = 1 if before_input else len(ordered)
    allowed = [
        {
            f"{args.predictions_prefix}/{name}"
            for name in ordered[:index]
        }
        for index in range(maximum + 1)
    ]
    if members not in allowed:
        raise core.LockedEvaluationError(
            "current retry prediction membership is not an exact initial set"
        )
    metadata, payloads = _stable_attempt_members(
        core, service, args.container, members
    )
    if members:
        reservation_blob = (
            f"{args.predictions_prefix}/{core.PREDICTION_MEMBER_NAMES[0]}"
        )
        _validate_prediction_reservation(
            core,
            payloads[reservation_blob],
            args,
            prefix=args.predictions_prefix,
            retry_kind=args.retry_kind,
            execution_id=args.execution_id,
        )
    return metadata, payloads


def _prepare_retry_attempt(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    authorization: dict[str, Any],
    *,
    now: Callable[[], str],
    allow_create: bool,
) -> dict[str, Any]:
    roots = core.evaluation_prefixes(
        args.parent_prefix, args.authorization_id
    )
    primary = _load_primary_abandoned_attempt(
        core, service, args, roots=roots
    )
    unseal_receipt = next(
        receipt
        for receipt in authorization["receipts"]
        if receipt["state"] == "UNSEAL_AUTHORIZED"
        and receipt["retry_kind"] == "none"
    )
    retry_receipt = _retry_receipt_for_attempt(core, authorization, args)
    abandoned_blob = core.derive_abandoned_attempt_blob_name(
        args.parent_prefix,
        args.authorization_id,
        "P",
        args.retry_kind,
        args.execution_id,
    )
    visibility_blob = f"{args.visibility_prefix}/stage_p_visibility.json"
    existing_visibility_members = core.list_exact_prefix(
        service, args.container, args.visibility_prefix
    )
    if existing_visibility_members not in (
        set(),
        {abandoned_blob},
        {abandoned_blob, visibility_blob},
    ):
        raise core.LockedEvaluationError(
            "current Stage-P retry visibility membership is not exact"
        )
    current_prediction_members = core.list_exact_prefix(
        service, args.container, args.predictions_prefix
    )
    actual_state_members = core.list_exact_prefix(
        service, args.container, args.state_prefix
    )
    initial_expected = {
        "predictions": {
            *primary["prediction_members"],
            *current_prediction_members,
        },
        "scores": set(),
        "state": actual_state_members,
        "visibility": {
            *primary["visibility_members"],
            *existing_visibility_members,
        },
    }
    core.validate_authorization_membership(
        service,
        args.container,
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        expected=initial_expected,
    )
    core.validate_registered_parent_membership(
        service,
        args.container,
        args.parent_prefix,
        core.expected_registered_parent_membership(
            args.parent_prefix,
            set().union(*initial_expected.values()),
        ),
    )
    if retry_receipt is not None and abandoned_blob not in existing_visibility_members:
        raise core.LockedEvaluationError(
            "retry receipt exists without its abandoned-attempt provenance"
        )

    abandoned_data: bytes
    if abandoned_blob in existing_visibility_members:
        abandoned_data, abandoned_etag = core.download_stable_blob(
            service, args.container, abandoned_blob
        )
        abandoned = core.parse_json_strict(
            abandoned_data, "abandoned Stage-P attempt"
        )
        core.validate_abandoned_attempt_record(abandoned)
        expected_abandoned = core.build_abandoned_attempt_record(
            parent_prefix=args.parent_prefix,
            authorization_id=args.authorization_id,
            prior_stage="P",
            prior_retry_kind="none",
            prior_execution_id=primary["visibility"]["execution_id"],
            prior_actor=primary["visibility"]["actor"],
            abandoned_members=primary["metadata"],
            current_retry_kind=args.retry_kind,
            current_execution_id=args.execution_id,
            current_actor=args.actor,
            prior_state_receipt_sha256=core.state_receipt_sha256(
                unseal_receipt
            ),
            created_utc=abandoned["created_utc"],
        )
        if (
            abandoned_data != core.canonical_json_bytes(abandoned)
            or not core.exact_json_equal(abandoned, expected_abandoned)
        ):
            raise core.LockedEvaluationError(
                "abandoned Stage-P attempt provenance differs"
            )
        abandoned_persistence = {
            "blob_name": abandoned_blob,
            "size": len(abandoned_data),
            "sha256": core.sha256_bytes(abandoned_data),
            "etag": abandoned_etag,
        }
    else:
        if not allow_create:
            raise core.LockedEvaluationError(
                "authorized retry omits abandoned-attempt provenance"
            )
        abandoned = core.build_abandoned_attempt_record(
            parent_prefix=args.parent_prefix,
            authorization_id=args.authorization_id,
            prior_stage="P",
            prior_retry_kind="none",
            prior_execution_id=primary["visibility"]["execution_id"],
            prior_actor=primary["visibility"]["actor"],
            abandoned_members=primary["metadata"],
            current_retry_kind=args.retry_kind,
            current_execution_id=args.execution_id,
            current_actor=args.actor,
            prior_state_receipt_sha256=core.state_receipt_sha256(
                unseal_receipt
            ),
            created_utc=now(),
        )
        if core.abandoned_attempt_blob_name(abandoned) != abandoned_blob:
            raise core.LockedEvaluationError(
                "abandoned Stage-P attempt Blob binding differs"
            )
        abandoned_data = core.canonical_json_bytes(abandoned)
        abandoned_persistence = core.persist_singleton(
            service,
            args.container,
            abandoned_blob,
            abandoned_data,
        )

    if retry_receipt is None:
        if not allow_create:
            raise core.LockedEvaluationError(
                "Stage-P retry receipt is missing"
            )
        retry_receipt = core.build_provenance_bound_retry_state_receipt(
            unseal_receipt,
            retry_kind=args.retry_kind,
            timestamp_utc=now(),
            execution_id=args.execution_id,
            actor=args.actor,
            history=authorization["receipts"],
            authorization_lock=authorization["authorization_lock"],
            implementation_manifest_bytes=authorization[
                "implementation_manifest_bytes"
            ],
            abandoned_attempt_record=abandoned,
            abandoned_attempt_blob_name=abandoned_blob,
            abandoned_attempt_record_sha256=abandoned_persistence["sha256"],
        )
        retry_persistence = core.persist_state_receipt(
            service,
            args.container,
            args.state_prefix,
            retry_receipt,
        )
        authorization["receipts"].append(retry_receipt)
        authorization["prior_receipt"] = retry_receipt
        authorization["retry_kinds"].append(args.retry_kind)
    else:
        retry_blob = core.state_receipt_blob_name(
            args.state_prefix, retry_receipt
        )
        retry_data, retry_etag = core.download_stable_blob(
            service, args.container, retry_blob
        )
        persisted_retry = core.parse_json_strict(
            retry_data, "Stage-P retry receipt"
        )
        if (
            retry_data != core.canonical_json_bytes(persisted_retry)
            or not core.exact_json_equal(persisted_retry, retry_receipt)
        ):
            raise core.LockedEvaluationError(
                "persisted Stage-P retry receipt differs"
            )
        core.validate_retry_state_receipt_provenance(
            persisted_retry,
            previous=unseal_receipt,
            abandoned_attempt_record=abandoned,
            abandoned_attempt_blob_name=abandoned_blob,
            abandoned_attempt_record_sha256=abandoned_persistence["sha256"],
        )
        if (
            persisted_retry["execution_id"] != args.execution_id
            or persisted_retry["actor"] != args.actor
        ):
            raise core.LockedEvaluationError(
                "pre-input retry was already consumed by another execution"
            )
        retry_persistence = {
            "blob_name": retry_blob,
            "size": len(retry_data),
            "sha256": core.sha256_bytes(retry_data),
            "etag": retry_etag,
        }

    if visibility_blob in existing_visibility_members:
        visibility_data, visibility_etag = core.download_stable_blob(
            service, args.container, visibility_blob
        )
        visibility = core.parse_json_strict(
            visibility_data, "current Stage-P retry visibility"
        )
        core.validate_visibility_record(
            visibility,
            expected_stage="P",
            expected_authorization_id=args.authorization_id,
            expected_parent_prefix=args.parent_prefix,
            expected_retry_kind=args.retry_kind,
            expected_execution_id=args.execution_id,
        )
        if (
            visibility_data != core.canonical_json_bytes(visibility)
            or visibility["actor"] != args.actor
        ):
            raise core.LockedEvaluationError(
                "current Stage-P retry visibility identity differs"
            )
        visibility_persistence = {
            "blob_name": visibility_blob,
            "size": len(visibility_data),
            "sha256": core.sha256_bytes(visibility_data),
            "etag": visibility_etag,
        }
    else:
        if not allow_create:
            raise core.LockedEvaluationError(
                "current Stage-P retry visibility is missing"
            )
        visibility = core.build_visibility_record(
            stage="P",
            authorization_id=args.authorization_id,
            parent_prefix=args.parent_prefix,
            visibility_prefix=args.visibility_prefix,
            execution_id=args.execution_id,
            actor=args.actor,
            created_utc=now(),
            retry_kind=args.retry_kind,
        )
        visibility_persistence = core.persist_singleton(
            service,
            args.container,
            visibility_blob,
            core.canonical_json_bytes(visibility),
        )

    if core.list_exact_prefix(
        service, args.container, args.visibility_prefix
    ) != {abandoned_blob, visibility_blob}:
        raise core.LockedEvaluationError(
            "current Stage-P retry visibility leaf membership is not exact"
        )
    return {
        "roots": roots,
        "primary_prediction_members": primary["prediction_members"],
        "primary_visibility_members": primary["visibility_members"],
        "primary_metadata": primary["metadata"],
        "abandoned_record": abandoned,
        "abandoned_persistence": abandoned_persistence,
        "retry_receipt": retry_receipt,
        "retry_persistence": retry_persistence,
        "visibility": visibility,
        "visibility_persistence": visibility_persistence,
        "visibility_metadata": [visibility_persistence],
    }


def _verify_persisted_prediction_leaf(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    authorization: Mapping[str, Any],
    input_receipt: Mapping[str, Any],
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    durable_input = _authenticate_durable_input_receipt(
        core,
        service,
        container=args.container,
        state_prefix=args.state_prefix,
        input_receipt=input_receipt,
    )
    input_receipt = durable_input["receipt"]
    producer_execution_id = input_receipt["execution_id"]
    producer_actor = input_receipt["actor"]
    expected_members = _prediction_member_blobs(core, args.predictions_prefix)
    if core.list_exact_prefix(
        service, args.container, args.predictions_prefix
    ) != expected_members:
        raise core.LockedEvaluationError(
            "persisted prediction leaf membership is not exact"
        )
    manifest_blob = (
        f"{args.predictions_prefix}/{core.PREDICTION_MEMBER_NAMES[-1]}"
    )
    manifest_bytes, manifest_etag = core.download_stable_blob(
        service, args.container, manifest_blob
    )
    manifest_sha256 = core.sha256_bytes(manifest_bytes)
    manifest = core.validate_prediction_artifact_manifest(
        manifest_bytes,
        expected_sha256=manifest_sha256,
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        expected_retry_kind=args.retry_kind,
        expected_execution_id=producer_execution_id,
    )
    if manifest_bytes != core.canonical_json_bytes(manifest):
        raise core.LockedEvaluationError(
            "prediction artifact manifest bytes are not canonical"
        )
    artifacts = core.download_prediction_artifacts(
        service,
        args.container,
        args.predictions_prefix,
        manifest_bytes,
        manifest,
        manifest_etag,
    )
    seal = core.parse_json_strict(
        artifacts["prediction_seal.json"], "prediction seal"
    )
    seal_binding = core.validate_locked_prediction_seal(
        seal,
        request_manifest_bytes=artifacts["prediction_request_manifest.json"],
        predictions_bytes=artifacts["parser_v2_locked_predictions.jsonl"],
        legacy_predictions_bytes=artifacts["legacy_locked_predictions.jsonl"],
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_retry_kind=args.retry_kind,
        expected_execution_id=producer_execution_id,
    )
    request_manifest = core.parse_json_strict(
        artifacts["prediction_request_manifest.json"],
        "prediction request manifest",
    )
    expected_input_manifest_hash = input_receipt[
        "artifact_manifest_hashes"
    ]["inputs_manifest"]
    authenticated_source = core.authenticate_locked_input_source(
        service,
        args.container,
        parent_prefix=args.parent_prefix,
        expected_locked_manifest_sha256=authorization[
            "locked_manifest_sha256"
        ],
        expected_manifest_sha256=expected_input_manifest_hash,
        expected_payload_sha256=args.locked_input_sha256,
        gates=gates,
    )
    source_artifact_binding = authenticated_source["binding"]
    if (
        args.locked_input_manifest_sha256 != expected_input_manifest_hash
        or expected_input_manifest_hash
        != input_receipt["artifact_manifest_hashes"]["locked_inputs_manifest"]
        or request_manifest.get("locked_input_blob") != args.locked_input_blob
        or request_manifest.get("locked_input_sha256")
        != args.locked_input_sha256
        or request_manifest.get("locked_input_manifest_blob")
        != args.locked_input_manifest_blob
        or request_manifest.get("locked_input_manifest_sha256")
        != args.locked_input_manifest_sha256
        or any(
            not core.exact_json_equal(
                request_manifest.get(field), source_artifact_binding[field]
            )
            for field in (
                "locked_input_reservation_blob",
                "locked_input_reservation_sha256",
                "locked_input_reservation_etag",
                "locked_input_manifest_blob",
                "locked_input_manifest_sha256",
                "locked_input_manifest_etag",
                "locked_manifest_sha256",
            )
        )
        or any(
            not core.exact_json_equal(
                authorization["authorization_manifest"].get(field),
                source_artifact_binding[field],
            )
            for field in core._LOCKED_INPUT_SOURCE_BINDING_FIELDS
        )
    ):
        raise core.LockedEvaluationError(
            "persisted request does not identify the authorized locked source"
        )
    source_manifest_bytes = authenticated_source["manifest_bytes"]
    source_manifest_etag = source_artifact_binding[
        "locked_input_manifest_etag"
    ]
    core.validate_locked_source_manifest(
        source_manifest_bytes,
        expected_manifest_sha256=expected_input_manifest_hash,
        expected_payload_sha256=args.locked_input_sha256,
        parent_prefix=args.parent_prefix,
        manifest_kind="locked-inputs",
        payload_relative_path="locked-inputs/locked_inputs.jsonl",
        gates=gates,
    )
    graph = core.validate_prediction_artifact_graph(
        manifest_bytes,
        manifest,
        artifacts,
        gates=gates,
        source_manifest_bytes=source_manifest_bytes,
        source_manifest_etag=source_manifest_etag,
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_prediction_manifest_sha256=manifest_sha256,
        expected_input_manifest_sha256=expected_input_manifest_hash,
        expected_input_receipt_sha256=core.state_receipt_sha256(input_receipt),
        expected_authorization_lock_sha256=authorization[
            "authorization_lock_sha256"
        ],
        expected_authorization_manifest_sha256=authorization[
            "authorization_manifest_sha256"
        ],
        expected_implementation_manifest_sha256=authorization[
            "implementation_manifest_sha256"
        ],
        expected_locked_manifest_sha256=authorization["locked_manifest_sha256"],
        expected_implementation_commit=args.implementation_commit,
        expected_image_digest=args.image_digest,
        expected_config_sha256=args.config_sha256,
        expected_locked_input_source_binding=source_artifact_binding,
        expected_retry_kind=args.retry_kind,
        expected_execution_id=producer_execution_id,
    )
    visibility_bytes, visibility_etag = core.download_verified_blob(
        service,
        args.container,
        seal["visibility_blob"],
        expected_sha256=seal["visibility_sha256"],
        expected_etag=seal["visibility_etag"],
    )
    visibility = core.parse_json_strict(
        visibility_bytes, "Stage-P visibility record"
    )
    core.validate_visibility_record(
        visibility,
        expected_stage="P",
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_retry_kind=args.retry_kind,
        expected_execution_id=producer_execution_id,
    )
    expected_receipt_visibility = sorted(
        {
            *visibility["artifact_classes"],
            f"record_sha256:{seal['visibility_sha256']}",
        }
    )
    launcher = authorization["runtime_config"]["launcher"]
    if (
        manifest["prediction_seal_sha256"]
        != core.sha256_bytes(artifacts["prediction_seal.json"])
        or manifest["implementation_commit"] != args.implementation_commit
        or manifest["image_digest"] != args.image_digest
        or manifest["config_sha256"] != args.config_sha256
        or manifest["locked_input_manifest_sha256"]
        != input_receipt["artifact_manifest_hashes"]["inputs_manifest"]
        or seal_binding["locked_input_manifest_sha256"]
        != input_receipt["artifact_manifest_hashes"]["inputs_manifest"]
        or seal_binding["visibility_sha256"]
        != manifest["stage_p_visibility_sha256"]
        or visibility["execution_id"] != producer_execution_id
        or visibility["actor"] != producer_actor
        or input_receipt["visibility"] != expected_receipt_visibility
        or authorization["runtime_config_sha256"] != args.config_sha256
        or authorization["image_binding_sha256"] != args.image_binding_sha256
        or authorization["helper_snapshot_set_sha256"]
        != args.helper_snapshot_set_sha256
        or launcher["sha256"] != args.launcher_sha256
        or launcher["git_blob_oid"] != args.launcher_git_blob_oid
        or not core.exact_json_equal(
            graph["ordered_case_ids"], manifest["ordered_case_ids"]
        )
    ):
        raise core.LockedEvaluationError(
            "persisted predictions differ from the spent input state"
        )
    _validate_prediction_reservation(
        core,
        artifacts[".prediction_reservation.json"],
        args,
        prefix=args.predictions_prefix,
        retry_kind=args.retry_kind,
        execution_id=producer_execution_id,
    )
    for name in (
        "prediction_request_manifest.json",
        "prediction_seal.json",
    ):
        parsed = core.parse_json_strict(artifacts[name], name)
        if artifacts[name] != core.canonical_json_bytes(parsed):
            raise core.LockedEvaluationError(
                "persisted prediction JSON bytes are not canonical"
            )
    for name in (
        "parser_v2_locked_predictions.jsonl",
        "legacy_locked_predictions.jsonl",
    ):
        rows = core.parse_jsonl_strict(artifacts[name], name)
        if artifacts[name] != core.canonical_jsonl_bytes(rows):
            raise core.LockedEvaluationError(
                "persisted prediction JSONL bytes are not canonical"
            )
    prediction_metadata = [
        {
            "blob_name": f"{args.predictions_prefix}/{item['name']}",
            "size": item["size"],
            "sha256": item["sha256"],
            "etag": item["etag"],
        }
        for item in manifest["payload_members"]
    ]
    prediction_metadata.append(
        {
            "blob_name": manifest_blob,
            "size": len(manifest_bytes),
            "sha256": manifest_sha256,
            "etag": manifest_etag,
        }
    )
    return {
        "manifest": manifest,
        "manifest_bytes": manifest_bytes,
        "manifest_sha256": manifest_sha256,
        "manifest_etag": manifest_etag,
        "artifacts": artifacts,
        "visibility": visibility,
        "prediction_metadata": sorted(
            prediction_metadata, key=lambda item: item["blob_name"]
        ),
        "visibility_metadata": [
            {
                "blob_name": seal["visibility_blob"],
                "size": len(visibility_bytes),
                "sha256": seal["visibility_sha256"],
                "etag": visibility_etag,
            }
        ],
        "members": expected_members,
    }


def _persist_spent_incomplete(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    authorization: Mapping[str, Any],
    input_receipt: Mapping[str, Any],
    *,
    now: Callable[[], str],
    final_state: str = "INPUTS_READ",
    attempt_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    durable_input = _authenticate_durable_input_receipt(
        core,
        service,
        container=args.container,
        state_prefix=args.state_prefix,
        input_receipt=input_receipt,
    )
    input_receipt = durable_input["receipt"]
    observed = sorted(
        core.list_exact_prefix(service, args.container, args.predictions_prefix)
    )
    retry_receipt_sha256 = (
        None
        if attempt_context is None
        else core.state_receipt_sha256(attempt_context["retry_receipt"])
    )
    record = core.build_spent_incomplete_record(
        input_receipt,
        state_prefix=args.state_prefix,
        authorization_manifest_sha256=authorization[
            "authorization_manifest_sha256"
        ],
        observed_prediction_members=observed,
        actor=input_receipt["actor"],
        execution_id=input_receipt["execution_id"],
        created_utc=now(),
        prediction_prefix=args.predictions_prefix,
        visibility_prefix=args.visibility_prefix,
        retry_kind=args.retry_kind,
        retry_receipt_sha256=retry_receipt_sha256,
    )
    persistence = core.persist_spent_incomplete_record(
        service,
        args.container,
        args.state_prefix,
        record,
        input_receipt=input_receipt,
        authorization_manifest_sha256=authorization[
            "authorization_manifest_sha256"
        ],
    )
    if attempt_context is None:
        allowed_initials = [
            {
                f"{args.predictions_prefix}/{name}"
                for name in core.PREDICTION_MEMBER_NAMES[:index]
            }
            for index in range(len(core.PREDICTION_MEMBER_NAMES) + 1)
        ]
        if set(observed) not in allowed_initials:
            raise core.LockedEvaluationError(
                "spent primary prediction membership is not registered"
            )
        prediction_metadata, _ = _stable_attempt_members(
            core, service, args.container, set(observed)
        )
    else:
        prediction_metadata, _ = _load_current_retry_predictions(
            core, service, args, before_input=False
        )
    visibility_blob = f"{args.visibility_prefix}/stage_p_visibility.json"
    visibility_metadata, _ = _stable_attempt_members(
        core, service, args.container, {visibility_blob}
    )
    _validate_stage_p_attempt_membership(
        core,
        service,
        args,
        state_members=core._authorization_state_members(
            args.state_prefix,
            final_state=final_state,
            retry_kinds=authorization["retry_kinds"],
            spent_incomplete=True,
        ),
        context=attempt_context,
        prediction_metadata=prediction_metadata,
        visibility_metadata=visibility_metadata,
    )
    return persistence


def _adopt_persisted_predictions(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    authorization: Mapping[str, Any],
    input_receipt: Mapping[str, Any],
    gates: Mapping[str, Any],
    *,
    receipt_exists: bool,
    spent_incomplete: bool = False,
    attempt_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if type(receipt_exists) is not bool or type(spent_incomplete) is not bool:
        raise core.LockedEvaluationError(
            "prediction adoption controls must be booleans"
        )
    persisted = _verify_persisted_prediction_leaf(
        core, service, args, authorization, input_receipt, gates
    )
    prediction_metadata, _ = _stable_attempt_members(
        core, service, args.container, persisted["members"]
    )
    visibility_member = f"{args.visibility_prefix}/stage_p_visibility.json"
    visibility_metadata, _ = _stable_attempt_members(
        core, service, args.container, {visibility_member}
    )
    if (
        not core.exact_json_equal(
            prediction_metadata, persisted["prediction_metadata"]
        )
        or not core.exact_json_equal(
            visibility_metadata, persisted["visibility_metadata"]
        )
    ):
        raise core.LockedEvaluationError(
            "prediction adoption bytes/ETags changed after authentication"
        )
    state_before = core._authorization_state_members(
        args.state_prefix,
        final_state=(
            "PREDICTIONS_VERIFIED" if receipt_exists else "INPUTS_READ"
        ),
        retry_kinds=authorization["retry_kinds"],
        spent_incomplete=spent_incomplete,
    )
    _validate_stage_p_attempt_membership(
        core,
        service,
        args,
        state_members=state_before,
        context=attempt_context,
        prediction_metadata=prediction_metadata,
        visibility_metadata=visibility_metadata,
    )
    receipt_persistence: dict[str, Any] | None = None
    if not receipt_exists:
        visibility = persisted["visibility"]
        receipt = core.build_next_state_receipt(
            input_receipt,
            state="PREDICTIONS_VERIFIED",
            artifact_manifest_sha256=persisted["manifest_sha256"],
            timestamp_utc=persisted["manifest"]["created_utc"],
            execution_id=visibility["execution_id"],
            actor=visibility["actor"],
            visibility=[
                *visibility["artifact_classes"],
                f"record_sha256:{persisted['manifest']['stage_p_visibility_sha256']}",
            ],
            authorization_lock=authorization["authorization_lock"],
            implementation_manifest_bytes=authorization[
                "implementation_manifest_bytes"
            ],
        )
        receipt_persistence = core.persist_or_adopt_state_receipt(
            service, args.container, args.state_prefix, receipt
        )
        _validate_stage_p_attempt_membership(
            core,
            service,
            args,
            state_members=core._authorization_state_members(
                args.state_prefix,
                final_state="PREDICTIONS_VERIFIED",
                retry_kinds=authorization["retry_kinds"],
                spent_incomplete=spent_incomplete,
            ),
            context=attempt_context,
            prediction_metadata=prediction_metadata,
            visibility_metadata=visibility_metadata,
        )
    else:
        receipt = authorization["prior_receipt"]
        if (
            receipt["artifact_manifest_hashes"]["predictions_manifest"]
            != persisted["manifest_sha256"]
            or receipt["previous_receipt_sha256"]
            != core.state_receipt_sha256(input_receipt)
            or receipt["execution_id"] != input_receipt["execution_id"]
            or receipt["actor"] != input_receipt["actor"]
        ):
            raise core.LockedEvaluationError(
                "prediction receipt differs from persisted prediction bytes"
            )
    return {
        "stage": "P",
        "status": "PREDICTIONS_VERIFIED",
        "authorization_id": args.authorization_id,
        "input_count": persisted["manifest"]["row_count"],
        "parser_v2_prediction_count": persisted["manifest"]["row_count"],
        "legacy_prediction_count": persisted["manifest"]["row_count"],
        "labels_accessed": False,
        "prediction_manifest_sha256": persisted["manifest_sha256"],
        "input_receipt_sha256": core.state_receipt_sha256(input_receipt),
        "predictions_receipt_sha256": (
            core.state_receipt_sha256(receipt)
            if receipt_persistence is None
            else receipt_persistence["sha256"]
        ),
        "visibility_sha256": persisted["manifest"][
            "stage_p_visibility_sha256"
        ],
        "retry_kind": args.retry_kind,
        "predictions_prefix": args.predictions_prefix,
        "visibility_prefix": args.visibility_prefix,
        "retry_receipt_sha256": (
            None
            if attempt_context is None
            else core.state_receipt_sha256(
                attempt_context["retry_receipt"]
            )
        ),
        "crash_adopted": not receipt_exists,
        "parsers_invoked": False,
        "overwrite": False,
        "manifest_uploaded_last": True,
        "target_model_loaded": False,
        "target_model_downloaded": False,
        "target_model_inference": False,
        "gpu_used": False,
    }


def _validate_stage_p_attempt_prefixes(
    core: ModuleType, args: argparse.Namespace
) -> None:
    for leaf in ("predictions", "visibility"):
        core.validate_exact_attempt_prefix(
            getattr(args, f"{leaf}_prefix"),
            args.parent_prefix,
            args.authorization_id,
            leaf,
            "P",
            args.retry_kind,
            args.execution_id,
        )


def _bind_recovery_to_prediction_producer(
    core: ModuleType,
    args: argparse.Namespace,
    authorization: Mapping[str, Any],
    input_receipt: Mapping[str, Any],
) -> argparse.Namespace:
    checked = core.validate_state_receipt(
        input_receipt, name="recovery INPUTS_READ receipt"
    )
    if checked["state"] != "INPUTS_READ" or input_receipt["retry_kind"] != "none":
        raise core.LockedEvaluationError(
            "prediction recovery lacks exact INPUTS_READ provenance"
        )
    predecessors = [
        receipt
        for receipt in authorization["receipts"]
        if core.state_receipt_sha256(receipt)
        == input_receipt["previous_receipt_sha256"]
    ]
    if len(predecessors) != 1:
        raise core.LockedEvaluationError(
            "prediction recovery predecessor provenance is not exact"
        )
    predecessor = predecessors[0]
    producer_retry_kind = predecessor["retry_kind"]
    if (
        predecessor["state"] != "UNSEAL_AUTHORIZED"
        or producer_retry_kind not in {"none", "infrastructure_pre_input"}
        or args.retry_kind != producer_retry_kind
        or args.actor != input_receipt["actor"]
        or (
            producer_retry_kind == "infrastructure_pre_input"
            and (
                predecessor["execution_id"] != input_receipt["execution_id"]
                or predecessor["actor"] != input_receipt["actor"]
            )
        )
    ):
        raise core.LockedEvaluationError(
            "prediction recovery differs from authorized launch provenance"
        )
    producer_args = argparse.Namespace(**vars(args))
    producer_args.execution_id = input_receipt["execution_id"]
    producer_args.actor = input_receipt["actor"]
    _validate_stage_p_attempt_prefixes(core, producer_args)
    return producer_args


def _run_stage_p(
    args: argparse.Namespace,
    *,
    service: Any | None = None,
    core: ModuleType | None = None,
    parser_functions: tuple[Callable[..., Any], Callable[..., Any]] | None = None,
    now: Callable[[], str] = _utc_now,
    _failure_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_core = core or _load_core()
    if service is None:
        active_core.validate_stage_p_environment(os.environ)
        active_core.validate_no_model_gpu_configuration(os.environ)
    active_core.compute_protocol_bundle_sha256(PROJECT_ROOT)
    gate_bytes = active_core.load_frozen_gate_bytes(PROJECT_ROOT)
    gates = active_core.load_acceptance_gates(gate_bytes)
    active_core.validate_exact_evaluation_prefix(
        args.state_prefix,
        args.parent_prefix,
        args.authorization_id,
        "state",
    )
    _assert_exact_source_names(
        active_core,
        parent_prefix=args.parent_prefix,
        locked_input_blob=args.locked_input_blob,
        locked_input_manifest_blob=args.locked_input_manifest_blob,
    )
    if service is None:
        active_core.validate_private_endpoint_resolution(
            args.account_url, args.expected_private_endpoint_ip
        )
    active_service = service or active_core.create_blob_service(args.account_url)
    locked_input_leaf = f"{args.parent_prefix}/locked-inputs"
    expected_locked_input_members = {
        f"{locked_input_leaf}/.locked_inputs_reservation.json",
        f"{locked_input_leaf}/locked_inputs.jsonl",
        f"{locked_input_leaf}/locked_inputs_manifest.json",
    }
    if active_core.list_exact_prefix(
        active_service, args.container, locked_input_leaf
    ) != expected_locked_input_members:
        raise active_core.LockedEvaluationError(
            "locked-input source leaf membership is not exact"
        )
    actual_state_members = active_core.list_exact_prefix(
        active_service, args.container, args.state_prefix
    )
    input_receipt_blob = (
        f"{args.state_prefix}/"
        f"{active_core.STATE_RECEIPT_FILENAMES['INPUTS_READ']}"
    )
    predictions_receipt_blob = (
        f"{args.state_prefix}/"
        f"{active_core.STATE_RECEIPT_FILENAMES['PREDICTIONS_VERIFIED']}"
    )
    spent_blob = (
        f"{args.state_prefix}/{active_core.SPENT_INCOMPLETE_FILENAME}"
    )
    pre_input_retry_blob = (
        f"{args.state_prefix}/"
        f"{active_core.STATE_RETRY_RECEIPT_FILENAMES['infrastructure_pre_input']}"
    )
    if predictions_receipt_blob in actual_state_members:
        authorization_target = "PREDICTIONS_VERIFIED"
        spent_incomplete = spent_blob in actual_state_members
    elif spent_blob in actual_state_members:
        authorization_target = "INPUTS_READ"
        spent_incomplete = True
    elif input_receipt_blob in actual_state_members:
        authorization_target = "INPUTS_READ"
        spent_incomplete = False
    else:
        authorization_target = "UNSEAL_AUTHORIZED"
        spent_incomplete = False
    authorization = active_core.authenticate_authorization_bundle(
        active_service,
        args.container,
        project_root=PROJECT_ROOT,
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        state_prefix=args.state_prefix,
        implementation_commit=args.implementation_commit,
        image_digest=args.image_digest,
        config_sha256=args.config_sha256,
        launcher_sha256=args.launcher_sha256,
        launcher_git_blob_oid=args.launcher_git_blob_oid,
        expected_prior_receipt_sha256=(
            args.prior_state_receipt_sha256
            if (
                authorization_target == "UNSEAL_AUTHORIZED"
                and pre_input_retry_blob not in actual_state_members
            )
            else None
        ),
        expected_authorization_lock_sha256=args.authorization_lock_sha256,
        expected_authorization_manifest_sha256=(
            args.authorization_manifest_sha256
        ),
        expected_image_binding_sha256=args.image_binding_sha256,
        expected_helper_snapshot_set_sha256=args.helper_snapshot_set_sha256,
        final_state=authorization_target,
        spent_incomplete=spent_incomplete,
    )
    active_core.validate_runtime_private_read_destination(
        authorization["runtime_config"],
        account_url=args.account_url,
        container=args.container,
        expected_private_endpoint_ips=getattr(
            args,
            "expected_private_endpoint_ip",
            authorization["runtime_config"]["azure_destination"]["network"][
                "private_endpoint_nic_private_ips"
            ],
        ),
    )
    unseal_receipt = next(
        receipt
        for receipt in authorization["receipts"]
        if receipt["state"] == "UNSEAL_AUTHORIZED"
        and receipt["retry_kind"] == "none"
    )
    if (
        args.prior_state_receipt_blob
        != active_core.state_receipt_blob_name(
            args.state_prefix, unseal_receipt
        )
        or args.prior_state_receipt_sha256
        != active_core.state_receipt_sha256(unseal_receipt)
    ):
        raise active_core.LockedEvaluationError(
            "Stage P predecessor Blob binding mismatch"
        )
    input_receipt: Mapping[str, Any] | None = None
    if authorization_target in {"INPUTS_READ", "PREDICTIONS_VERIFIED"}:
        input_receipt = next(
            receipt
            for receipt in authorization["receipts"]
            if receipt["state"] == "INPUTS_READ"
            and receipt["retry_kind"] == "none"
        )
        args = _bind_recovery_to_prediction_producer(
            active_core, args, authorization, input_receipt
        )
    else:
        _validate_stage_p_attempt_prefixes(active_core, args)
    if _failure_context is not None:
        _failure_context.update(
            {
                "service": active_service,
                "post_input": False,
                "attempt_args": args,
            }
        )
    attempt_context: dict[str, Any] | None = None
    retry_persistence: Mapping[str, Any] | None = None
    if args.retry_kind == "infrastructure_pre_input":
        if (
            authorization_target != "UNSEAL_AUTHORIZED"
            and args.retry_kind not in authorization["retry_kinds"]
        ):
            raise active_core.LockedEvaluationError(
                "INPUTS_READ evidence permanently forbids a new Stage-P retry"
            )
        _load_current_retry_predictions(
            active_core,
            active_service,
            args,
            before_input=authorization_target == "UNSEAL_AUTHORIZED",
        )
        attempt_context = _prepare_retry_attempt(
            active_core,
            active_service,
            args,
            authorization,
            now=now,
            allow_create=authorization_target == "UNSEAL_AUTHORIZED",
        )
        retry_persistence = attempt_context["retry_persistence"]
        prior_receipt = attempt_context["retry_receipt"]
    elif args.retry_kind != "none":
        raise active_core.LockedEvaluationError("Stage P retry kind is invalid")
    else:
        prior_receipt = unseal_receipt

    visibility_blob = f"{args.visibility_prefix}/stage_p_visibility.json"
    existing_visibility = None
    existing_visibility_persistence = None
    adopted_reservation_bytes = None
    adopted_reservation = None
    prediction_metadata: list[dict[str, Any]]
    prediction_payloads: dict[str, bytes]
    visibility_metadata: list[dict[str, Any]] = []

    if authorization_target in {"INPUTS_READ", "PREDICTIONS_VERIFIED"}:
        assert input_receipt is not None
        expected_input_predecessor = active_core.state_receipt_sha256(
            prior_receipt
        )
        if (
            input_receipt["previous_receipt_sha256"]
            != expected_input_predecessor
            or input_receipt["execution_id"] != args.execution_id
            or input_receipt["actor"] != args.actor
        ):
            raise active_core.LockedEvaluationError(
                "INPUTS_READ belongs to a different Stage-P attempt"
            )
        if attempt_context is None:
            actual_prediction_members = active_core.list_exact_prefix(
                active_service, args.container, args.predictions_prefix
            )
            if any(
                member.startswith(f"{args.predictions_prefix}/attempts/")
                for member in actual_prediction_members
            ):
                raise active_core.LockedEvaluationError(
                    "primary Stage-P attempt contains an unbound nested retry"
                )
            allowed_primary = [
                {
                    f"{args.predictions_prefix}/{name}"
                    for name in active_core.PREDICTION_MEMBER_NAMES[:index]
                }
                for index in range(
                    len(active_core.PREDICTION_MEMBER_NAMES) + 1
                )
            ]
            if actual_prediction_members not in allowed_primary:
                raise active_core.LockedEvaluationError(
                    "primary prediction membership is not an exact initial set"
                )
            prediction_metadata, prediction_payloads = (
                _stable_attempt_members(
                    active_core,
                    active_service,
                    args.container,
                    actual_prediction_members,
                )
            )
            if actual_prediction_members:
                reservation_blob = (
                    f"{args.predictions_prefix}/"
                    f"{active_core.PREDICTION_MEMBER_NAMES[0]}"
                )
                _validate_prediction_reservation(
                    active_core,
                    prediction_payloads[reservation_blob],
                    args,
                    prefix=args.predictions_prefix,
                    retry_kind="none",
                    execution_id=args.execution_id,
                )
            primary_visibility_members = active_core.list_exact_prefix(
                active_service, args.container, args.visibility_prefix
            )
            if primary_visibility_members != {visibility_blob}:
                raise active_core.LockedEvaluationError(
                    "primary Stage-P visibility membership is not exact"
                )
            visibility_metadata, visibility_payloads = (
                _stable_attempt_members(
                    active_core,
                    active_service,
                    args.container,
                    primary_visibility_members,
                )
            )
            persisted_visibility = active_core.parse_json_strict(
                visibility_payloads[visibility_blob],
                "primary Stage-P visibility",
            )
            active_core.validate_visibility_record(
                persisted_visibility,
                expected_stage="P",
                expected_authorization_id=args.authorization_id,
                expected_parent_prefix=args.parent_prefix,
                expected_retry_kind="none",
                expected_execution_id=args.execution_id,
            )
            if persisted_visibility["actor"] != args.actor:
                raise active_core.LockedEvaluationError(
                    "primary Stage-P visibility actor differs"
                )
        else:
            prediction_metadata, prediction_payloads = (
                _load_current_retry_predictions(
                    active_core,
                    active_service,
                    args,
                    before_input=False,
                )
            )
            visibility_metadata = list(
                attempt_context["visibility_metadata"]
            )

        state_at_input = active_core._authorization_state_members(
            args.state_prefix,
            final_state=authorization_target,
            retry_kinds=authorization["retry_kinds"],
            spent_incomplete=spent_incomplete,
        )
        _validate_stage_p_attempt_membership(
            active_core,
            active_service,
            args,
            state_members=state_at_input,
            context=attempt_context,
            prediction_metadata=prediction_metadata,
            visibility_metadata=visibility_metadata,
        )
        if _failure_context is not None:
            _failure_context.update(
                {
                    "service": active_service,
                    "post_input": True,
                    "attempt_context": attempt_context,
                }
            )
        prediction_members = _prediction_member_blobs(
            active_core, args.predictions_prefix
        )
        actual_prediction_members = {
            item["blob_name"] for item in prediction_metadata
        }
        if spent_incomplete:
            spent_bytes, _ = active_core.download_stable_blob(
                active_service, args.container, spent_blob
            )
            spent = active_core.parse_json_strict(
                spent_bytes, "spent-incomplete record"
            )
            active_core.validate_spent_incomplete_record(
                spent,
                input_receipt=input_receipt,
                state_prefix=args.state_prefix,
                authorization_manifest_sha256=authorization[
                    "authorization_manifest_sha256"
                ],
            )
            if (
                spent["prediction_prefix"] != args.predictions_prefix
                or spent["visibility_prefix"] != args.visibility_prefix
                or spent["retry_kind"] != args.retry_kind
                or not active_core.exact_json_equal(
                    spent["observed_prediction_members"],
                    sorted(actual_prediction_members),
                )
            ):
                raise active_core.LockedEvaluationError(
                    "spent-incomplete attempt membership changed"
                )
            if actual_prediction_members == prediction_members:
                return _adopt_persisted_predictions(
                    active_core,
                    active_service,
                    args,
                    authorization,
                    input_receipt,
                    gates,
                    receipt_exists=(
                        authorization_target == "PREDICTIONS_VERIFIED"
                    ),
                    spent_incomplete=True,
                    attempt_context=attempt_context,
                )
            raise active_core.LockedEvaluationError(
                "holdout is spent incomplete, not retired; parser rerun is prohibited"
            )
        if actual_prediction_members == prediction_members:
            try:
                return _adopt_persisted_predictions(
                    active_core,
                    active_service,
                    args,
                    authorization,
                    input_receipt,
                    gates,
                    receipt_exists=authorization_target
                    == "PREDICTIONS_VERIFIED",
                    spent_incomplete=False,
                    attempt_context=attempt_context,
                )
            except Exception:
                _persist_spent_incomplete(
                    active_core,
                    active_service,
                    args,
                    authorization,
                    input_receipt,
                    now=now,
                    final_state=authorization_target,
                    attempt_context=attempt_context,
                )
                raise
        if authorization_target == "PREDICTIONS_VERIFIED":
            raise active_core.LockedEvaluationError(
                "prediction receipt exists without its exact persisted leaf"
            )
        _persist_spent_incomplete(
            active_core,
            active_service,
            args,
            authorization,
            input_receipt,
            now=now,
            attempt_context=attempt_context,
        )
        raise active_core.LockedEvaluationError(
            "holdout is spent incomplete, not retired; parser rerun is prohibited"
        )

    if attempt_context is None:
        prediction_members_before = active_core.list_exact_prefix(
            active_service, args.container, args.predictions_prefix
        )
        if prediction_members_before:
            raise active_core.LockedEvaluationError(
                "primary prediction destination is not empty"
            )
        if active_core.list_exact_prefix(
            active_service, args.container, args.visibility_prefix
        ):
            raise active_core.LockedEvaluationError(
                "primary Stage-P visibility destination is not empty"
            )
        prediction_metadata = []
        prediction_payloads = {}
    else:
        prediction_metadata, prediction_payloads = (
            _load_current_retry_predictions(
                active_core,
                active_service,
                args,
                before_input=True,
            )
        )
        prediction_members_before = {
            item["blob_name"] for item in prediction_metadata
        }
        if prediction_payloads:
            adopted_reservation_bytes = prediction_payloads[
                f"{args.predictions_prefix}/"
                f"{active_core.PREDICTION_MEMBER_NAMES[0]}"
            ]
            adopted_reservation = active_core.parse_json_strict(
                adopted_reservation_bytes, "prediction reservation"
            )
        existing_visibility = attempt_context["visibility"]
        existing_visibility_persistence = attempt_context[
            "visibility_persistence"
        ]
        visibility_metadata = list(attempt_context["visibility_metadata"])

    state_before = active_core._authorization_state_members(
        args.state_prefix,
        final_state="UNSEAL_AUTHORIZED",
        retry_kinds=authorization["retry_kinds"],
    )
    _validate_stage_p_attempt_membership(
        active_core,
        active_service,
        args,
        state_members=state_before,
        context=attempt_context,
        prediction_metadata=prediction_metadata,
        visibility_metadata=visibility_metadata,
    )

    authenticated_source = active_core.authenticate_locked_input_source(
        active_service,
        args.container,
        parent_prefix=args.parent_prefix,
        expected_locked_manifest_sha256=authorization[
            "locked_manifest_sha256"
        ],
        expected_manifest_sha256=args.locked_input_manifest_sha256,
        expected_payload_sha256=args.locked_input_sha256,
        gates=gates,
    )
    source_binding = authenticated_source["source"]
    source_artifact_binding = authenticated_source["binding"]
    if any(
        not active_core.exact_json_equal(
            authorization["authorization_manifest"].get(field),
            source_artifact_binding[field],
        )
        for field in active_core._LOCKED_INPUT_SOURCE_BINDING_FIELDS
    ):
        raise active_core.LockedEvaluationError(
            "locked-input reservation/manifest differs from authorization"
        )
    manifest_etag = source_artifact_binding["locked_input_manifest_etag"]
    if source_binding["manifest_sha256"] != prior_receipt[
        "artifact_manifest_hashes"
    ]["locked_inputs_manifest"]:
        raise active_core.LockedEvaluationError(
            "locked-input manifest is not the authorized frozen artifact"
        )
    del authenticated_source
    prior_checked = active_core.validate_state_receipt(
        prior_receipt, name="UNSEAL_AUTHORIZED receipt"
    )
    if (
        prior_checked["state"] != "UNSEAL_AUTHORIZED"
        or prior_receipt["authorization_id"] != args.authorization_id
        or prior_receipt["registered_parent_prefix"] != args.parent_prefix
        or prior_receipt["implementation_commit"] != args.implementation_commit
        or prior_receipt["image_digest"] != args.image_digest
        or prior_receipt["config_sha256"] != args.config_sha256
        or prior_receipt["authorization_lock_sha256"]
        != authorization["authorization_lock_sha256"]
    ):
        raise active_core.LockedEvaluationError(
            "Stage P immutable authorization binding mismatch"
        )
    loaded_parsers = (
        _load_stage_p_parsers()
        if parser_functions is None
        else parser_functions
    )
    if type(loaded_parsers) is not tuple or len(loaded_parsers) != 2:
        raise active_core.LockedEvaluationError(
            "Stage P parser function membership is not exact"
        )
    parse_v2, parse_legacy = loaded_parsers

    if existing_visibility is None:
        timestamp = now()
        visibility = active_core.build_visibility_record(
            stage="P",
            authorization_id=args.authorization_id,
            parent_prefix=args.parent_prefix,
            visibility_prefix=args.visibility_prefix,
            execution_id=args.execution_id,
            actor=args.actor,
            created_utc=timestamp,
            retry_kind=args.retry_kind,
        )
        visibility_persistence = active_core.persist_singleton(
            active_service,
            args.container,
            visibility_blob,
            active_core.canonical_json_bytes(visibility),
        )
    else:
        visibility = existing_visibility
        visibility_persistence = existing_visibility_persistence
        timestamp = now()
    visibility_metadata = [visibility_persistence]
    _validate_stage_p_attempt_membership(
        active_core,
        active_service,
        args,
        state_members=state_before,
        context=attempt_context,
        prediction_metadata=prediction_metadata,
        visibility_metadata=visibility_metadata,
    )
    visibility_members = {
        visibility_persistence["blob_name"]
    }
    input_receipt = active_core.build_next_state_receipt(
        prior_receipt,
        state="INPUTS_READ",
        artifact_manifest_sha256=source_binding["manifest_sha256"],
        timestamp_utc=timestamp,
        execution_id=args.execution_id,
        actor=args.actor,
        visibility=[
            *visibility["artifact_classes"],
            f"record_sha256:{visibility_persistence['sha256']}",
        ],
        authorization_lock=authorization["authorization_lock"],
        implementation_manifest_bytes=authorization[
            "implementation_manifest_bytes"
        ],
    )
    if _failure_context is not None:
        _failure_context.update(
            {
                "service": active_service,
                "post_input": False,
                "attempt_context": attempt_context,
            }
        )
    state_after_input = active_core._authorization_state_members(
        args.state_prefix,
        final_state="INPUTS_READ",
        retry_kinds=authorization["retry_kinds"],
    )
    expected_after_input = (
        active_core.expected_authorization_attempt_membership(
            args.parent_prefix,
            args.authorization_id,
            (
                []
                if attempt_context is None
                else [
                    attempt_context["abandoned_record"],
                    active_core.build_attempt_membership_descriptor(
                        parent_prefix=args.parent_prefix,
                        authorization_id=args.authorization_id,
                        stage="P",
                        retry_kind=args.retry_kind,
                        execution_id=args.execution_id,
                        members=sorted(
                            [*prediction_metadata, *visibility_metadata],
                            key=lambda item: item["blob_name"],
                        ),
                    ),
                ]
            ),
            primary_membership=(
                {
                    "predictions": {
                        item["blob_name"] for item in prediction_metadata
                    },
                    "scores": set(),
                    "state": state_after_input,
                    "visibility": {
                        item["blob_name"] for item in visibility_metadata
                    },
                }
                if attempt_context is None
                else {
                    "predictions": set(
                        attempt_context["primary_prediction_members"]
                    ),
                    "scores": set(),
                    "state": state_after_input,
                    "visibility": set(
                        attempt_context["primary_visibility_members"]
                    ),
                }
            ),
        )
    )
    parent_after_input = active_core.expected_registered_parent_membership(
        args.parent_prefix,
        set().union(*expected_after_input.values()),
    )
    try:
        (
            input_receipt_persistence,
            locked_input_bytes,
            locked_input_etag,
        ) = persist_input_receipt_then_read_inputs(
            active_core,
            active_service,
            container=args.container,
            state_prefix=args.state_prefix,
            input_receipt=input_receipt,
            locked_input_blob=args.locked_input_blob,
            locked_input_sha256=args.locked_input_sha256,
            locked_input_size=source_binding["payload_size"],
            parent_prefix=args.parent_prefix,
            registered_parent_members_after_receipt=parent_after_input,
        )
    except Exception as input_error:
        try:
            _authenticate_durable_input_receipt(
                active_core,
                active_service,
                container=args.container,
                state_prefix=args.state_prefix,
                input_receipt=input_receipt,
            )
        except Exception:
            raise input_error
        if _failure_context is not None:
            _failure_context["post_input"] = True
        _persist_spent_incomplete(
            active_core,
            active_service,
            args,
            authorization,
            input_receipt,
            now=now,
            attempt_context=attempt_context,
        )
        raise
    if _failure_context is not None:
        _failure_context["post_input"] = True
    try:
        _validate_stage_p_attempt_membership(
            active_core,
            active_service,
            args,
            state_members=state_after_input,
            context=attempt_context,
            prediction_metadata=prediction_metadata,
            visibility_metadata=visibility_metadata,
        )
    except Exception:
        _persist_spent_incomplete(
            active_core,
            active_service,
            args,
            authorization,
            input_receipt,
            now=now,
            attempt_context=attempt_context,
        )
        raise
    try:
        locked_inputs = active_core.validate_locked_inputs_bytes(
            locked_input_bytes, gates
        )
        ordered_ids = [item["case_id"] for item in locked_inputs]
        if not active_core.exact_json_equal(
            ordered_ids, source_binding["ordered_case_ids"]
        ):
            raise active_core.LockedEvaluationError(
                "locked-input payload membership differs from its manifest"
            )
        request_manifest = active_core.build_prediction_request_manifest(
            authorization_id=args.authorization_id,
            parent_prefix=args.parent_prefix,
            prediction_prefix=args.predictions_prefix,
            implementation_commit=args.implementation_commit,
            image_digest=args.image_digest,
            config_sha256=args.config_sha256,
            authorization_lock_sha256=authorization[
                "authorization_lock_sha256"
            ],
            authorization_manifest_sha256=authorization[
                "authorization_manifest_sha256"
            ],
            implementation_manifest_sha256=authorization[
                "implementation_manifest_sha256"
            ],
            locked_manifest_sha256=authorization["locked_manifest_sha256"],
            input_receipt_sha256=active_core.state_receipt_sha256(
                input_receipt
            ),
            locked_input_reservation_blob=source_artifact_binding[
                "locked_input_reservation_blob"
            ],
            locked_input_reservation_sha256=source_artifact_binding[
                "locked_input_reservation_sha256"
            ],
            locked_input_private_nonce_sha256=source_artifact_binding[
                "locked_input_private_nonce_sha256"
            ],
            locked_input_reservation_etag=source_artifact_binding[
                "locked_input_reservation_etag"
            ],
            locked_input_blob=args.locked_input_blob,
            locked_input_sha256=args.locked_input_sha256,
            locked_input_etag=locked_input_etag,
            locked_input_manifest_blob=args.locked_input_manifest_blob,
            locked_input_manifest_sha256=args.locked_input_manifest_sha256,
            locked_input_manifest_etag=manifest_etag,
            visibility_blob=visibility_persistence["blob_name"],
            visibility_sha256=visibility_persistence["sha256"],
            visibility_etag=visibility_persistence["etag"],
            ordered_case_ids=ordered_ids,
            created_utc=timestamp,
            retry_kind=args.retry_kind,
            execution_id=args.execution_id,
        )
        predictions, legacy_predictions = generate_prediction_rows(
            locked_inputs,
            parse_v2=parse_v2,
            parse_legacy=parse_legacy,
            core=active_core,
        )
        active_core.validate_prediction_rows(
            predictions, legacy_predictions, locked_inputs, gates
        )
        seal = active_core.build_locked_prediction_seal(
            request_manifest=request_manifest,
            predictions=predictions,
            legacy_predictions=legacy_predictions,
            locked_inputs=locked_inputs,
            sealed_utc=timestamp,
            retry_kind=args.retry_kind,
            execution_id=args.execution_id,
        )
    except Exception:
        _persist_spent_incomplete(
            active_core,
            active_service,
            args,
            authorization,
            input_receipt,
            now=now,
            attempt_context=attempt_context,
        )
        raise
    try:
        if adopted_reservation_bytes is None:
            reservation = active_core.build_reservation(
                leaf="predictions",
                prefix=args.predictions_prefix,
                authorization_id=args.authorization_id,
                created_utc=timestamp,
                nonce=secrets.token_hex(16),
                parent_prefix=args.parent_prefix,
                stage="P",
                retry_kind=args.retry_kind,
                execution_id=args.execution_id,
            )
            reservation_bytes = active_core.canonical_json_bytes(
                reservation
            )
        else:
            reservation = adopted_reservation
            reservation_bytes = adopted_reservation_bytes
        payloads = {
            ".prediction_reservation.json": reservation_bytes,
            "prediction_request_manifest.json": active_core.canonical_json_bytes(
                request_manifest
            ),
            "parser_v2_locked_predictions.jsonl": (
                active_core.canonical_jsonl_bytes(predictions)
            ),
            "legacy_locked_predictions.jsonl": (
                active_core.canonical_jsonl_bytes(legacy_predictions)
            ),
            "prediction_seal.json": active_core.canonical_json_bytes(seal),
        }
        seal_sha256 = active_core.sha256_bytes(
            payloads["prediction_seal.json"]
        )
    except Exception:
        _persist_spent_incomplete(
            active_core,
            active_service,
            args,
            authorization,
            input_receipt,
            now=now,
            attempt_context=attempt_context,
        )
        raise

    def manifest_builder(metadata: list[dict[str, Any]]) -> Mapping[str, Any]:
        return active_core.build_prediction_artifact_manifest(
            metadata=metadata,
            seal_sha256=seal_sha256,
            prediction_seal=seal,
            request_manifest=request_manifest,
            created_utc=timestamp,
            retry_kind=args.retry_kind,
            execution_id=args.execution_id,
        )

    try:
        persistence = active_core.persist_manifest_last_prefix(
            active_service,
            args.container,
            args.predictions_prefix,
            member_names=active_core.PREDICTION_MEMBER_NAMES,
            payloads=payloads,
            manifest_builder=manifest_builder,
            registered_member_names=active_core.PREDICTION_MEMBER_NAMES,
            parent_prefix=args.parent_prefix,
            registered_parent_members_before=parent_after_input,
            adopted_reservation=adopted_reservation_bytes,
        )
        predictions_receipt = active_core.build_next_state_receipt(
            input_receipt,
            state="PREDICTIONS_VERIFIED",
            artifact_manifest_sha256=persistence["manifest_sha256"],
            timestamp_utc=timestamp,
            execution_id=args.execution_id,
            actor=args.actor,
            visibility=[
                *visibility["artifact_classes"],
                f"record_sha256:{visibility_persistence['sha256']}",
            ],
            authorization_lock=authorization["authorization_lock"],
            implementation_manifest_bytes=authorization[
                "implementation_manifest_bytes"
            ],
        )
        predictions_receipt_persistence = active_core.persist_state_receipt(
            active_service,
            args.container,
            args.state_prefix,
            predictions_receipt,
        )
    except Exception:
        _persist_spent_incomplete(
            active_core,
            active_service,
            args,
            authorization,
            input_receipt,
            now=now,
            attempt_context=attempt_context,
        )
        raise
    prediction_members = {
        f"{args.predictions_prefix}/{name}"
        for name in active_core.PREDICTION_MEMBER_NAMES
    }
    state_after_predictions = active_core._authorization_state_members(
        args.state_prefix,
        final_state="PREDICTIONS_VERIFIED",
        retry_kinds=authorization["retry_kinds"],
    )
    try:
        final_prediction_metadata, _ = _stable_attempt_members(
            active_core,
            active_service,
            args.container,
            prediction_members,
        )
        _validate_stage_p_attempt_membership(
            active_core,
            active_service,
            args,
            state_members=state_after_predictions,
            context=attempt_context,
            prediction_metadata=final_prediction_metadata,
            visibility_metadata=visibility_metadata,
        )
    except Exception:
        _persist_spent_incomplete(
            active_core,
            active_service,
            args,
            authorization,
            input_receipt,
            now=now,
            final_state="PREDICTIONS_VERIFIED",
            attempt_context=attempt_context,
        )
        raise
    return {
        "stage": "P",
        "status": "PREDICTIONS_VERIFIED",
        "authorization_id": args.authorization_id,
        "input_count": len(locked_inputs),
        "parser_v2_prediction_count": len(predictions),
        "legacy_prediction_count": len(legacy_predictions),
        "labels_accessed": False,
        "prediction_manifest_sha256": persistence["manifest_sha256"],
        "input_receipt_sha256": input_receipt_persistence["sha256"],
        "predictions_receipt_sha256": predictions_receipt_persistence["sha256"],
        "visibility_sha256": visibility_persistence["sha256"],
        "retry_kind": args.retry_kind,
        "predictions_prefix": args.predictions_prefix,
        "visibility_prefix": args.visibility_prefix,
        "retry_receipt_sha256": (
            None if retry_persistence is None else retry_persistence["sha256"]
        ),
        "parsers_invoked": True,
        "overwrite": False,
        "manifest_uploaded_last": True,
        "target_model_loaded": False,
        "target_model_downloaded": False,
        "target_model_inference": False,
        "gpu_used": False,
    }


def _ensure_post_input_failure_is_persisted(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    *,
    now: Callable[[], str],
    attempt_context: Mapping[str, Any] | None = None,
) -> None:
    state_members = core.list_exact_prefix(
        service, args.container, args.state_prefix
    )
    input_blob = (
        f"{args.state_prefix}/"
        f"{core.STATE_RECEIPT_FILENAMES['INPUTS_READ']}"
    )
    if input_blob not in state_members:
        return
    spent_blob = f"{args.state_prefix}/{core.SPENT_INCOMPLETE_FILENAME}"
    if spent_blob in state_members:
        return
    predictions_blob = (
        f"{args.state_prefix}/"
        f"{core.STATE_RECEIPT_FILENAMES['PREDICTIONS_VERIFIED']}"
    )
    final_state = (
        "PREDICTIONS_VERIFIED"
        if predictions_blob in state_members
        else "INPUTS_READ"
    )
    authorization = core.authenticate_authorization_bundle(
        service,
        args.container,
        project_root=PROJECT_ROOT,
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        state_prefix=args.state_prefix,
        implementation_commit=args.implementation_commit,
        image_digest=args.image_digest,
        config_sha256=args.config_sha256,
        launcher_sha256=args.launcher_sha256,
        launcher_git_blob_oid=args.launcher_git_blob_oid,
        expected_authorization_lock_sha256=args.authorization_lock_sha256,
        expected_authorization_manifest_sha256=(
            args.authorization_manifest_sha256
        ),
        expected_image_binding_sha256=args.image_binding_sha256,
        expected_helper_snapshot_set_sha256=args.helper_snapshot_set_sha256,
        final_state=final_state,
    )
    input_receipt = next(
        receipt
        for receipt in authorization["receipts"]
        if receipt["state"] == "INPUTS_READ"
        and receipt["retry_kind"] == "none"
    )
    if args.retry_kind == "infrastructure_pre_input" and attempt_context is None:
        attempt_context = _prepare_retry_attempt(
            core,
            service,
            args,
            authorization,
            now=now,
            allow_create=False,
        )
    _persist_spent_incomplete(
        core,
        service,
        args,
        authorization,
        input_receipt,
        now=now,
        final_state=final_state,
        attempt_context=attempt_context,
    )


def run_stage_p(
    args: argparse.Namespace,
    *,
    service: Any | None = None,
    core: ModuleType | None = None,
    parser_functions: tuple[Callable[..., Any], Callable[..., Any]] | None = None,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    active_core = core or _load_core()
    failure_context: dict[str, Any] = {}
    try:
        return _run_stage_p(
            args,
            service=service,
            core=active_core,
            parser_functions=parser_functions,
            now=now,
            _failure_context=failure_context,
        )
    except Exception as error:
        if not failure_context.get("post_input"):
            raise
        try:
            _ensure_post_input_failure_is_persisted(
                active_core,
                failure_context["service"],
                failure_context.get("attempt_args", args),
                now=now,
                attempt_context=failure_context.get("attempt_context"),
            )
        except Exception as persistence_error:
            raise active_core.LockedEvaluationError(
                "post-INPUTS_READ failure could not persist spent-incomplete"
            ) from persistence_error
        raise


def run_stage_p_adoption(
    args: argparse.Namespace,
    *,
    service: Any | None = None,
    core: ModuleType | None = None,
) -> dict[str, Any]:
    active_core = core or _load_core()
    if args.retry_kind != "prediction_adoption":
        raise active_core.LockedEvaluationError(
            "adopt-only execution requires its distinct retry kind"
        )
    if service is None:
        active_core.validate_stage_p_environment(os.environ)
        active_core.validate_no_model_gpu_configuration(os.environ)
        active_core.validate_private_endpoint_resolution(
            args.account_url, args.expected_private_endpoint_ip
        )
    active_service = service or active_core.create_blob_service(
        args.account_url
    )
    active_core.compute_protocol_bundle_sha256(PROJECT_ROOT)
    gates = active_core.load_acceptance_gates(
        active_core.load_frozen_gate_bytes(PROJECT_ROOT)
    )
    active_core.validate_exact_evaluation_prefix(
        args.state_prefix,
        args.parent_prefix,
        args.authorization_id,
        "state",
    )
    for leaf in ("predictions", "visibility"):
        active_core.validate_exact_attempt_prefix(
            getattr(args, f"{leaf}_prefix"),
            args.parent_prefix,
            args.authorization_id,
            leaf,
            "P",
            args.producer_retry_kind,
            args.producer_execution_id,
        )
    state_members = active_core.list_exact_prefix(
        active_service, args.container, args.state_prefix
    )
    spent_incomplete = (
        f"{args.state_prefix}/{active_core.SPENT_INCOMPLETE_FILENAME}"
        in state_members
    )
    authorization = active_core.authenticate_authorization_bundle(
        active_service,
        args.container,
        project_root=PROJECT_ROOT,
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        state_prefix=args.state_prefix,
        implementation_commit=args.implementation_commit,
        image_digest=args.image_digest,
        config_sha256=args.config_sha256,
        launcher_sha256=args.launcher_sha256,
        launcher_git_blob_oid=args.launcher_git_blob_oid,
        expected_prior_receipt_sha256=args.prior_state_receipt_sha256,
        expected_authorization_lock_sha256=args.authorization_lock_sha256,
        expected_authorization_manifest_sha256=(
            args.authorization_manifest_sha256
        ),
        expected_image_binding_sha256=args.image_binding_sha256,
        expected_helper_snapshot_set_sha256=(
            args.helper_snapshot_set_sha256
        ),
        final_state="INPUTS_READ",
        spent_incomplete=spent_incomplete,
    )
    input_receipt = authorization["prior_receipt"]
    if (
        args.prior_state_receipt_blob
        != active_core.state_receipt_blob_name(
            args.state_prefix, input_receipt
        )
        or input_receipt["execution_id"] != args.producer_execution_id
    ):
        raise active_core.LockedEvaluationError(
            "adopt-only producer does not own INPUTS_READ"
        )
    producer_predecessors = [
        receipt
        for receipt in authorization["receipts"]
        if active_core.state_receipt_sha256(receipt)
        == input_receipt["previous_receipt_sha256"]
    ]
    if len(producer_predecessors) != 1:
        raise active_core.LockedEvaluationError(
            "adopt-only producer predecessor is not unique"
        )
    producer_predecessor = producer_predecessors[0]
    if (
        producer_predecessor["state"] != "UNSEAL_AUTHORIZED"
        or producer_predecessor["retry_kind"] != args.producer_retry_kind
        or (
            args.producer_retry_kind == "infrastructure_pre_input"
            and (
                producer_predecessor["execution_id"]
                != input_receipt["execution_id"]
                or producer_predecessor["actor"] != input_receipt["actor"]
            )
        )
    ):
        raise active_core.LockedEvaluationError(
            "adopt-only producer differs from the authenticated receipt lineage"
        )
    manifest_blob = (
        f"{args.predictions_prefix}/"
        f"{active_core.PREDICTION_MEMBER_NAMES[-1]}"
    )
    manifest_bytes, manifest_etag = active_core.download_stable_blob(
        active_service, args.container, manifest_blob
    )
    manifest = active_core.validate_prediction_artifact_manifest(
        manifest_bytes,
        expected_sha256=args.prediction_manifest_sha256,
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        expected_retry_kind=args.producer_retry_kind,
        expected_execution_id=args.producer_execution_id,
    )
    artifacts = active_core.download_prediction_artifacts(
        active_service,
        args.container,
        args.predictions_prefix,
        manifest_bytes,
        manifest,
        manifest_etag,
    )
    request = active_core.parse_json_strict(
        artifacts["prediction_request_manifest.json"],
        "adopt-only prediction request",
    )
    internal = argparse.Namespace(
        **{
            **vars(args),
            "retry_kind": args.producer_retry_kind,
            "execution_id": args.producer_execution_id,
            "actor": input_receipt["actor"],
            "locked_input_blob": request["locked_input_blob"],
            "locked_input_sha256": request["locked_input_sha256"],
            "locked_input_manifest_blob": request[
                "locked_input_manifest_blob"
            ],
            "locked_input_manifest_sha256": request[
                "locked_input_manifest_sha256"
            ],
        }
    )
    attempt_context = None
    if args.producer_retry_kind == "infrastructure_pre_input":
        attempt_context = _prepare_retry_attempt(
            active_core,
            active_service,
            internal,
            authorization,
            now=lambda: input_receipt["timestamp_utc"],
            allow_create=False,
        )
    result = _adopt_persisted_predictions(
        active_core,
        active_service,
        internal,
        authorization,
        input_receipt,
        gates,
        receipt_exists=False,
        spent_incomplete=spent_incomplete,
        attempt_context=attempt_context,
    )
    if (
        result["prediction_manifest_sha256"]
        != args.prediction_manifest_sha256
        or result["predictions_receipt_sha256"]
        != args.expected_predictions_receipt_sha256
    ):
        raise active_core.LockedEvaluationError(
            "adopt-only receipt differs from authenticated producer projection"
        )
    result["mode"] = "prediction_adoption"
    result["adoption_execution_id"] = args.execution_id
    return result


def _parser() -> argparse.ArgumentParser:
    parser = _RedactedArgumentParser(
        description="Run label-blind one-shot parser-v2 locked predictions",
        allow_abbrev=False,
    )
    parser.add_argument("--account-url", required=True)
    parser.add_argument(
        "--expected-private-endpoint-ip", action="append", required=True
    )
    parser.add_argument("--container", required=True)
    parser.add_argument("--parent-prefix", required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--locked-input-blob", required=True)
    parser.add_argument("--locked-input-sha256", required=True)
    parser.add_argument("--locked-input-manifest-blob", required=True)
    parser.add_argument("--locked-input-manifest-sha256", required=True)
    parser.add_argument("--predictions-prefix", required=True)
    parser.add_argument("--state-prefix", required=True)
    parser.add_argument("--visibility-prefix", required=True)
    parser.add_argument("--prior-state-receipt-blob", required=True)
    parser.add_argument("--prior-state-receipt-sha256", required=True)
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--image-binding-sha256", required=True)
    parser.add_argument("--helper-snapshot-set-sha256", required=True)
    parser.add_argument("--authorization-lock-sha256", required=True)
    parser.add_argument("--authorization-manifest-sha256", required=True)
    parser.add_argument("--launcher-sha256", required=True)
    parser.add_argument("--launcher-git-blob-oid", required=True)
    parser.add_argument(
        "--retry-kind",
        choices=("none", "infrastructure_pre_input"),
        default="none",
    )
    parser.add_argument("--execution-id", type=_execution_id, required=True)
    parser.add_argument(
        "--actor",
        choices=("stage-p-managed-runtime",),
        required=True,
    )
    return parser


def _adopt_parser() -> argparse.ArgumentParser:
    parser = _RedactedArgumentParser(
        description="Adopt one complete immutable Stage-P producer",
        allow_abbrev=False,
    )
    parser.add_argument("--adopt-only", action="store_true", required=True)
    parser.add_argument("--account-url", required=True)
    parser.add_argument(
        "--expected-private-endpoint-ip", action="append", required=True
    )
    parser.add_argument("--container", required=True)
    parser.add_argument("--parent-prefix", required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--predictions-prefix", required=True)
    parser.add_argument("--state-prefix", required=True)
    parser.add_argument("--visibility-prefix", required=True)
    parser.add_argument("--prior-state-receipt-blob", required=True)
    parser.add_argument("--prior-state-receipt-sha256", required=True)
    parser.add_argument("--prediction-manifest-sha256", required=True)
    parser.add_argument(
        "--expected-predictions-receipt-sha256", required=True
    )
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--image-binding-sha256", required=True)
    parser.add_argument("--helper-snapshot-set-sha256", required=True)
    parser.add_argument("--authorization-lock-sha256", required=True)
    parser.add_argument("--authorization-manifest-sha256", required=True)
    parser.add_argument("--launcher-sha256", required=True)
    parser.add_argument("--launcher-git-blob-oid", required=True)
    parser.add_argument(
        "--retry-kind", choices=("prediction_adoption",), required=True
    )
    parser.add_argument(
        "--producer-retry-kind",
        choices=("none", "infrastructure_pre_input"),
        required=True,
    )
    parser.add_argument(
        "--producer-execution-id", type=_execution_id, required=True
    )
    parser.add_argument("--execution-id", type=_execution_id, required=True)
    parser.add_argument(
        "--actor",
        choices=("stage-p-adoption-runtime",),
        required=True,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        raw = list(sys.argv[1:] if argv is None else argv)
        core = _load_core()
        adopt_only = "--adopt-only" in raw
        for token in raw:
            lowered = token.casefold()
            if (
                any(
                    item in lowered
                    for item in ("label", "reference", "correctness")
                )
                or (
                    adopt_only
                    and token.startswith("--")
                    and any(
                        item in lowered for item in ("locked-input", "parser")
                    )
                )
            ):
                raise core.LockedEvaluationError(
                    "Stage P command contains a prohibited channel"
                )
        args = (
            _adopt_parser().parse_args(raw)
            if adopt_only
            else _parser().parse_args(raw)
        )
        result = (
            run_stage_p_adoption(args, core=core)
            if adopt_only
            else run_stage_p(args, core=core)
        )
        public = {
            "stage": "P",
            "status": result["status"],
            "input_count": result["input_count"],
            "parser_v2_prediction_count": result[
                "parser_v2_prediction_count"
            ],
            "legacy_prediction_count": result["legacy_prediction_count"],
            "labels_accessed": False,
        }
        print(json.dumps(public, sort_keys=True, separators=(",", ":")))
        return 0
    except SystemExit as exc:
        if exc.code in {None, 0}:
            return 0
        print(
            "STAGE_P_ERROR:ARGUMENTS_REJECTED:ArgumentError",
            file=sys.stderr,
        )
        return 2
    except _RedactedArgumentError:
        print(
            "STAGE_P_ERROR:ARGUMENTS_REJECTED:ArgumentError",
            file=sys.stderr,
        )
        return 2
    except Exception as exc:
        stable_class = (
            "LockedEvaluationError"
            if exc.__class__.__name__ == "LockedEvaluationError"
            else "RuntimeError"
        )
        print(
            f"STAGE_P_ERROR:EXECUTION_REJECTED:{stable_class}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
