#!/usr/bin/env python3
"""Finalize Stage E once, without importing or executing either parser."""

from __future__ import annotations

import argparse
import ast
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import CodeType, ModuleType
from typing import Any, Callable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = (
    PROJECT_ROOT
    / "src"
    / "jspace_observation"
    / "parser_v2_locked_evaluation.py"
)
FORBIDDEN_MODULE_PARTS = (
    "eval_parsing",
    "eval_parsing_v2",
    "eval_parsing_v3",
    "parser_v2_process_worker",
    "parser_v3_process_worker",
    "run_parser_v2_locked_predictions",
    "run_parser_v3_locked_predictions",
)
# Parser modules live in the package; the workers and Stage P launchers live in
# scripts/ and reach a parser transitively, so both routes are denied by name
# and by resolved path.
_FORBIDDEN_PARSER_MODULE_FILENAMES = frozenset(
    {"eval_parsing.py", "eval_parsing_v2.py", "eval_parsing_v3.py"}
)
_FORBIDDEN_PARSER_SCRIPT_FILENAMES = frozenset(
    {
        "parser_v2_process_worker.py",
        "parser_v3_process_worker.py",
        "run_parser_v2_locked_predictions.py",
        "run_parser_v3_locked_predictions.py",
    }
)
FORBIDDEN_FILENAMES = (
    _FORBIDDEN_PARSER_MODULE_FILENAMES | _FORBIDDEN_PARSER_SCRIPT_FILENAMES
)
_FORBIDDEN_PYC_STEMS = frozenset(
    name.removesuffix(".py") for name in FORBIDDEN_FILENAMES
)
_ORIGINAL_SPEC_FROM_FILE_LOCATION = importlib.util.spec_from_file_location
_ORIGINAL_SOURCE_FILE_LOADER = importlib.machinery.SourceFileLoader
_ORIGINAL_SOURCELESS_FILE_LOADER = importlib.machinery.SourcelessFileLoader
_ORIGINAL_SOURCE_FILE_LOADER_INIT = _ORIGINAL_SOURCE_FILE_LOADER.__init__
_ORIGINAL_SOURCELESS_FILE_LOADER_INIT = _ORIGINAL_SOURCELESS_FILE_LOADER.__init__
_ORIGINAL_SOURCE_FILE_LOADER_EXEC = _ORIGINAL_SOURCE_FILE_LOADER.exec_module
_ORIGINAL_SOURCELESS_FILE_LOADER_EXEC = _ORIGINAL_SOURCELESS_FILE_LOADER.exec_module
_STAGE_E_GUARD_DEPTH = 0
_STAGE_E_AUDIT_INSTALLED = False
_DYNAMIC_GUARDS_INSTALLED = False
_FORBIDDEN_CODE_NAMES = frozenset(
    {
        "compare_parsed_answer_to_reference",
        "create_eval_record",
        "evaluate_answer",
        "parse_and_score",
        "parse_numeric_answer",
        "parse_v2",
        "parse_v3",
    }
)
_EXECUTION_ID_PATTERN = re.compile(r"stage-e-[0-9a-f]{32}\Z", re.ASCII)

# Fixed when this module is imported, before any sealed artifact or label byte
# is read, from a name seeded by a hardcoded launcher. It selects a *scoring*
# profile only: Stage E never loads a parser under any profile.
STAGE_E_PROFILE_ID = globals().pop("_PRESEEDED_PARSER_PROFILE_ID", "parser-v2-v1")
STAGE_E_PROFILE_RESOLVED_UTC = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ"
)
# Stage E restates the stream member names independently of the core and then
# cross-checks them once the core is loaded, so a rename on either side is a
# hard failure rather than a silent re-attribution.
_STAGE_E_STREAM_MEMBERS = {
    "parser-v2-v1": {
        "candidate": "parser_v2_locked_predictions.jsonl",
        "parser_v2_comparator": None,
        "legacy": "legacy_locked_predictions.jsonl",
    },
    "parser-v3-v1": {
        "candidate": "parser_v3_candidate_predictions.jsonl",
        "parser_v2_comparator": "parser_v2_comparator_predictions.jsonl",
        "legacy": "legacy_comparator_predictions.jsonl",
    },
}[STAGE_E_PROFILE_ID]
_CANDIDATE_PREDICTIONS_MEMBER = _STAGE_E_STREAM_MEMBERS["candidate"]
_V2_COMPARATOR_PREDICTIONS_MEMBER = _STAGE_E_STREAM_MEMBERS["parser_v2_comparator"]
_LEGACY_PREDICTIONS_MEMBER = _STAGE_E_STREAM_MEMBERS["legacy"]
# The stream the acceptance contract's comparison gates score against. Under
# parser v2 that is the legacy parser; under parser v3 the contract names
# parser v2, and the legacy stream becomes reporting-only.
_GATING_COMPARATOR_PREDICTIONS_MEMBER = (
    _LEGACY_PREDICTIONS_MEMBER
    if _V2_COMPARATOR_PREDICTIONS_MEMBER is None
    else _V2_COMPARATOR_PREDICTIONS_MEMBER
)


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


def _guard_active() -> bool:
    return _STAGE_E_GUARD_DEPTH > 0


def _forbidden_parser_path(location: object) -> bool:
    try:
        path = Path(os.fspath(location)).resolve()
    except (TypeError, ValueError, OSError):
        return False
    if path.name in FORBIDDEN_FILENAMES:
        return True
    if path.suffix == ".pyc" and path.stem.split(".", 1)[0] in _FORBIDDEN_PYC_STEMS:
        return True
    return path in (
        {
            (PROJECT_ROOT / "src" / "jspace_observation" / name).resolve()
            for name in _FORBIDDEN_PARSER_MODULE_FILENAMES
        }
        | {
            (PROJECT_ROOT / "scripts" / name).resolve()
            for name in _FORBIDDEN_PARSER_SCRIPT_FILENAMES
        }
    )


def _guarded_spec_from_file_location(
    name: str, location: object, *args: object, **kwargs: object
) -> object:
    if _guard_active() and _forbidden_parser_path(location):
        raise ImportError("Stage E blocks parser path loading")
    return _ORIGINAL_SPEC_FROM_FILE_LOCATION(name, location, *args, **kwargs)


def _guarded_source_file_loader_init(
    self: object, name: str, path: str
) -> None:
    if _guard_active() and _forbidden_parser_path(path):
        raise ImportError("Stage E blocks parser source loading")
    _ORIGINAL_SOURCE_FILE_LOADER_INIT(self, name, path)


def _guarded_sourceless_file_loader_init(
    self: object, name: str, path: str
) -> None:
    if _guard_active() and _forbidden_parser_path(path):
        raise ImportError("Stage E blocks parser bytecode loading")
    _ORIGINAL_SOURCELESS_FILE_LOADER_INIT(self, name, path)


def _guarded_source_file_loader_exec(self: object, module: ModuleType) -> None:
    if _guard_active() and _forbidden_parser_path(getattr(self, "path", None)):
        raise ImportError("Stage E blocks parser source execution")
    _ORIGINAL_SOURCE_FILE_LOADER_EXEC(self, module)


def _guarded_sourceless_file_loader_exec(
    self: object, module: ModuleType
) -> None:
    if _guard_active() and _forbidden_parser_path(getattr(self, "path", None)):
        raise ImportError("Stage E blocks parser bytecode execution")
    _ORIGINAL_SOURCELESS_FILE_LOADER_EXEC(self, module)


def _install_dynamic_loader_guards() -> None:
    global _DYNAMIC_GUARDS_INSTALLED
    if _DYNAMIC_GUARDS_INSTALLED:
        return
    importlib.util.spec_from_file_location = _guarded_spec_from_file_location
    _ORIGINAL_SOURCE_FILE_LOADER.__init__ = _guarded_source_file_loader_init
    _ORIGINAL_SOURCE_FILE_LOADER.exec_module = _guarded_source_file_loader_exec
    _ORIGINAL_SOURCELESS_FILE_LOADER.__init__ = (
        _guarded_sourceless_file_loader_init
    )
    _ORIGINAL_SOURCELESS_FILE_LOADER.exec_module = (
        _guarded_sourceless_file_loader_exec
    )
    importlib.machinery.SourceFileLoader = _ORIGINAL_SOURCE_FILE_LOADER
    importlib.machinery.SourcelessFileLoader = _ORIGINAL_SOURCELESS_FILE_LOADER
    _DYNAMIC_GUARDS_INSTALLED = True


def _source_defines_parser(source: object) -> bool:
    if isinstance(source, memoryview):
        source = source.tobytes()
    if isinstance(source, bytes):
        try:
            source = source.decode("utf-8")
        except UnicodeDecodeError:
            return False
    if not isinstance(source, str):
        return False
    return bool(
        re.search(
            r"(?m)^\s*(?:async\s+)?def\s+"
            r"(?:parse_numeric_answer|parse_v2|parse_v3|evaluate_answer|"
            r"create_eval_record|compare_parsed_answer_to_reference)\s*\(",
            source,
        )
    )


def _code_executes_parser(code: object) -> bool:
    if not isinstance(code, CodeType):
        return False
    if code.co_name in _FORBIDDEN_CODE_NAMES:
        return True
    return any(
        _code_executes_parser(value)
        for value in code.co_consts
        if isinstance(value, CodeType)
    )


def _allowed_protocol_git_command(executable: object, arguments: object) -> bool:
    if executable is None and isinstance(arguments, str):
        match = re.fullmatch(
            r'git -C (?P<root>"[^"]+"|[^"]+?) show '
            r"(?P<object>[0-9a-f]{40}:docs/[A-Za-z0-9_.-]+)",
            arguments,
            re.ASCII,
        )
        if match is None:
            return False
        executable = "git"
        arguments = [
            "git",
            "-C",
            match.group("root").strip('"'),
            "show",
            match.group("object"),
        ]
    if isinstance(executable, os.PathLike):
        executable = os.fspath(executable)
    if not isinstance(executable, (str, bytes)):
        return False
    executable_text = os.fsdecode(executable)
    executable_path = Path(executable_text)
    executable_name = Path(
        executable_text.replace("\\", "/")
    ).name.casefold()
    if executable_name not in {"git", "git.exe"}:
        return False
    if ("/" in executable_text or "\\" in executable_text) and (
        executable_path
        not in {Path("/bin/git"), Path("/usr/bin/git"), Path("/usr/local/bin/git")}
        and not (
            os.name == "nt"
            and "program files" in executable_text.casefold()
            and "\\git\\" in executable_text.casefold()
        )
    ):
        return False
    if not isinstance(arguments, (list, tuple)) or len(arguments) != 5:
        return False
    try:
        values = [os.fsdecode(os.fspath(item)) for item in arguments]
    except (TypeError, ValueError):
        return False
    if (
        Path(values[2]).resolve() != PROJECT_ROOT
        or Path(values[0].replace("\\", "/")).name.casefold()
        not in {"git", "git.exe"}
        or values[1] != "-C"
        or values[3] != "show"
        or ":" not in values[4]
    ):
        return False
    commit, relative_path = values[4].split(":", 1)
    return bool(
        re.fullmatch(r"[0-9a-f]{40}", commit, re.ASCII)
        and relative_path
        in {
            "docs/phase1_evaluator_validation_set.md",
            "docs/phase1_parser_v2_acceptance_gates.json",
            "docs/phase1_parser_v2_protocol.md",
        }
    )


def _stage_e_audit_hook(event: str, arguments: tuple[object, ...]) -> None:
    if not _guard_active():
        return
    if event == "import":
        name = arguments[0] if arguments else ""
        if isinstance(name, str) and (
            name == "jspace_observation"
            or any(item in name for item in FORBIDDEN_MODULE_PARTS)
        ):
            raise ImportError("Stage E blocks parser import")
    elif event == "open":
        if arguments and _forbidden_parser_path(arguments[0]):
            raise ImportError("Stage E blocks parser file access")
    elif event == "compile":
        source = arguments[0] if arguments else None
        filename = arguments[1] if len(arguments) > 1 else None
        if _forbidden_parser_path(filename) or _source_defines_parser(source):
            raise ImportError("Stage E blocks parser source compilation")
    elif event == "exec":
        if arguments and _code_executes_parser(arguments[0]):
            raise ImportError("Stage E blocks parser code execution")
    elif event == "subprocess.Popen":
        executable = arguments[0] if arguments else None
        command = arguments[1] if len(arguments) > 1 else None
        if not _allowed_protocol_git_command(executable, command):
            raise ImportError("Stage E blocks unregistered subprocesses")
    elif event in {
        "os.exec",
        "os.posix_spawn",
        "os.posix_spawnp",
        "os.spawn",
        "os.system",
        "os.startfile",
        "os.startfile/2",
    }:
        if event in {"os.system", "os.startfile", "os.startfile/2"}:
            raise ImportError("Stage E blocks unregistered subprocesses")
        executable = arguments[0] if arguments else None
        command = arguments[1] if len(arguments) > 1 else None
        if not _allowed_protocol_git_command(executable, command):
            raise ImportError("Stage E blocks unregistered subprocesses")
    elif event in {"os.link", "os.rename", "os.symlink"}:
        if any(_forbidden_parser_path(item) for item in arguments[:2]):
            raise ImportError("Stage E blocks parser path aliases")


def _activate_runtime_guards() -> None:
    global _STAGE_E_AUDIT_INSTALLED, _STAGE_E_GUARD_DEPTH
    if not _STAGE_E_AUDIT_INSTALLED:
        sys.addaudithook(_stage_e_audit_hook)
        _STAGE_E_AUDIT_INSTALLED = True
    _install_dynamic_loader_guards()
    _STAGE_E_GUARD_DEPTH += 1


def _restore_guard_depth(depth: int) -> None:
    global _STAGE_E_GUARD_DEPTH
    _STAGE_E_GUARD_DEPTH = depth


def _source_import_guard(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
        for name in names:
            if name == "jspace_observation" or any(
                item in name for item in FORBIDDEN_MODULE_PARTS
            ):
                raise RuntimeError(f"Stage E has a forbidden import: {name}")


class _ParserImportBlocker(importlib.abc.MetaPathFinder):
    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: object = None,
    ) -> None:
        if (
            fullname == "jspace_observation"
            or any(item in fullname for item in FORBIDDEN_MODULE_PARTS)
        ):
            raise ImportError(f"Stage E blocks parser import: {fullname}")
        return None


def _assert_runtime_isolation() -> None:
    forbidden_loaded = [
        name
        for name in sys.modules
        if name == "jspace_observation"
        or any(item in name for item in FORBIDDEN_MODULE_PARTS)
    ]
    if forbidden_loaded:
        raise RuntimeError(
            "Stage E started with a forbidden parser/package module loaded"
        )
    if not any(isinstance(item, _ParserImportBlocker) for item in sys.meta_path):
        sys.meta_path.insert(0, _ParserImportBlocker())
    if not _guard_active():
        _activate_runtime_guards()
    else:
        _install_dynamic_loader_guards()


def _score_reporting_only_comparator(
    core: ModuleType,
    *,
    labels_bytes: bytes,
    candidate_bytes: bytes,
    gate_bytes: bytes,
    prediction_artifacts: Mapping[str, bytes],
) -> dict[str, Any] | None:
    """Score the reporting-only comparator, for the record and nothing else.

    Under parser v2 the legacy stream already gates, so there is nothing extra
    to report. Under parser v3 the contract makes legacy reporting-only, so it
    is scored here in a separate pass whose gate verdict is discarded: only the
    legacy aggregates are kept, and they cannot move the formal decision.
    """
    if _V2_COMPARATOR_PREDICTIONS_MEMBER is None:
        return None
    return core.score_reporting_only_legacy_comparator(
        labels_bytes,
        candidate_bytes,
        prediction_artifacts[_LEGACY_PREDICTIONS_MEMBER],
        gate_bytes,
    )


def _assert_stream_member_agreement(core: ModuleType) -> None:
    """Fail unless the scorer and the core name the same streams, in order.

    Stage E holds its own copy of the member names. Agreement here is what makes
    the scorer's attribution independent of the artifact it is scoring.
    """
    profile = core.ACTIVE_PARSER_PROFILE
    identities = core.FROZEN_COMPARATOR_PARSER_IDENTITIES
    expected_v2 = (
        identities["parser_v2"]["predictions_filename"]
        if "parser_v2" in identities
        else None
    )
    if (
        profile["candidate_predictions_filename"] != _CANDIDATE_PREDICTIONS_MEMBER
        or identities["legacy"]["predictions_filename"]
        != _LEGACY_PREDICTIONS_MEMBER
        or expected_v2 != _V2_COMPARATOR_PREDICTIONS_MEMBER
    ):
        raise RuntimeError("Stage E and the core disagree on prediction streams")
    members = tuple(core.PREDICTION_MEMBER_NAMES)
    expected_streams = tuple(
        name
        for name in (
            _CANDIDATE_PREDICTIONS_MEMBER,
            _V2_COMPARATOR_PREDICTIONS_MEMBER,
            _LEGACY_PREDICTIONS_MEMBER,
        )
        if name is not None
    )
    if tuple(name for name in members if name.endswith(".jsonl")) != expected_streams:
        raise RuntimeError("Stage E prediction stream order is not exact")
    if len(set(expected_streams)) != len(expected_streams):
        raise RuntimeError("Stage E prediction streams are not distinct")


def _load_core() -> ModuleType:
    _source_import_guard(Path(__file__).resolve())
    _source_import_guard(CORE_PATH)
    _assert_runtime_isolation()
    name = "_jspace_parser_v2_locked_eval_stage_e"
    spec = _ORIGINAL_SPEC_FROM_FILE_LOCATION(name, CORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot direct-load parser-free scorer core")
    module = importlib.util.module_from_spec(spec)
    module.__dict__["_PRESEEDED_PARSER_PROFILE_ID"] = STAGE_E_PROFILE_ID
    sys.modules[name] = module
    spec.loader.exec_module(module)
    if module.ACTIVE_PARSER_PROFILE_ID != STAGE_E_PROFILE_ID:
        raise RuntimeError("Stage E core ignored the requested scoring profile")
    if "_PRESEEDED_PARSER_PROFILE_ID" in module.__dict__:
        raise RuntimeError("Stage E core leaked its profile seed")
    _assert_stream_member_agreement(module)
    module.assert_parser_free_source(
        Path(__file__).read_bytes(), str(Path(__file__).resolve())
    )
    module.assert_parser_free_source(CORE_PATH.read_bytes(), str(CORE_PATH))
    _assert_runtime_isolation()
    return module


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _assert_exact_source_names(
    core: ModuleType,
    *,
    parent_prefix: str,
    labels_blob: str,
    labels_manifest_blob: str,
) -> None:
    parent = core.validate_registered_parent_prefix(parent_prefix)
    if labels_blob != f"{parent}/locked-labels/locked_reference_labels.jsonl":
        raise core.LockedEvaluationError("locked-label Blob name is not exact")
    if (
        labels_manifest_blob
        != f"{parent}/locked-labels/locked_labels_manifest.json"
    ):
        raise core.LockedEvaluationError("locked-label manifest name is not exact")


def _stable_attempt_members(
    core: ModuleType,
    service: Any,
    container: str,
    members: Sequence[str] | set[str],
) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    metadata: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {}
    for blob_name in sorted(members):
        data, etag = core.download_stable_blob(service, container, blob_name)
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


def _list_member_metadata(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    prefix: str,
) -> list[dict[str, Any]]:
    metadata, _ = _stable_attempt_members(
        core,
        service,
        args.container,
        core.list_exact_prefix(service, args.container, prefix),
    )
    return metadata


def _direct_leaf_members(root: str, members: set[str]) -> set[str]:
    attempt_root = f"{root}/attempts/"
    return {member for member in members if not member.startswith(attempt_root)}


def _validate_score_reservation(
    core: ModuleType,
    data: bytes,
    args: argparse.Namespace,
    *,
    prefix: str,
    retry_kind: str,
    execution_id: str,
) -> dict[str, Any]:
    reservation = core.parse_json_strict(data, "scores reservation")
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
        "scores reservation",
    )
    rebuilt = core.build_reservation(
        leaf=reservation["leaf"],
        prefix=reservation["prefix"],
        authorization_id=reservation["authorization_id"],
        created_utc=reservation["created_utc"],
        nonce=reservation["nonce"],
        parent_prefix=args.parent_prefix,
        stage="E",
        retry_kind=retry_kind,
        execution_id=execution_id,
    )
    if (
        not core.exact_json_equal(reservation, rebuilt)
        or reservation["leaf"] != "scores"
        or reservation["prefix"] != prefix
        or reservation["authorization_id"] != args.authorization_id
        or data != core.canonical_json_bytes(reservation)
    ):
        raise core.LockedEvaluationError(
            "score reservation attempt binding is not exact"
        )
    return reservation


def _load_primary_stage_e_attempt(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    *,
    roots: Mapping[str, str],
) -> dict[str, Any]:
    all_scores = core.list_exact_prefix(
        service, args.container, roots["scores"]
    )
    all_visibility = core.list_exact_prefix(
        service, args.container, roots["visibility"]
    )
    primary_scores = _direct_leaf_members(roots["scores"], all_scores)
    primary_visibility = _direct_leaf_members(
        roots["visibility"], all_visibility
    )
    foreign_scores = all_scores - primary_scores
    foreign_visibility = all_visibility - primary_visibility
    if any(
        not member.startswith(f"{args.scores_prefix}/")
        for member in foreign_scores
    ) or any(
        not member.startswith(f"{args.visibility_prefix}/")
        for member in foreign_visibility
    ):
        raise core.LockedEvaluationError(
            "Stage-E retry contains an unbound nested attempt"
        )
    stage_p_visibility_blob = (
        f"{roots['visibility']}/stage_p_visibility.json"
    )
    primary_stage_e_visibility_blob = (
        f"{roots['visibility']}/stage_e_visibility.json"
    )
    if primary_visibility != {
        stage_p_visibility_blob,
        primary_stage_e_visibility_blob,
    }:
        raise core.LockedEvaluationError(
            "scorer retry requires exactly one primary Stage-E visibility record"
        )
    reservation_blob = f"{roots['scores']}/{core.SCORE_MEMBER_NAMES[0]}"
    if primary_scores not in (set(), {reservation_blob}):
        raise core.LockedEvaluationError(
            "primary score root is not an immutable pre-label partial set"
        )
    score_metadata, score_payloads = _stable_attempt_members(
        core, service, args.container, primary_scores
    )
    visibility_metadata, visibility_payloads = _stable_attempt_members(
        core,
        service,
        args.container,
        primary_visibility,
    )
    visibility_bytes = visibility_payloads[primary_stage_e_visibility_blob]
    visibility = core.parse_json_strict(
        visibility_bytes, "primary Stage-E visibility"
    )
    core.validate_visibility_record(
        visibility,
        expected_stage="E",
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_retry_kind="none",
    )
    if (
        visibility_bytes != core.canonical_json_bytes(visibility)
        or visibility["execution_id"] == args.execution_id
    ):
        raise core.LockedEvaluationError(
            "scorer retry does not identify a distinct primary attempt"
        )
    if primary_scores:
        _validate_score_reservation(
            core,
            score_payloads[reservation_blob],
            args,
            prefix=roots["scores"],
            retry_kind="none",
            execution_id=visibility["execution_id"],
        )
    return {
        "score_members": primary_scores,
        "stage_p_visibility_members": {stage_p_visibility_blob},
        "stage_e_visibility_members": {primary_stage_e_visibility_blob},
        "metadata": sorted(
            [*score_metadata, *visibility_metadata],
            key=lambda item: item["blob_name"],
        ),
        "visibility": visibility,
    }


def _retry_receipt_for_attempt(
    core: ModuleType,
    authorization: Mapping[str, Any],
    retry_kind: str,
) -> Mapping[str, Any] | None:
    matching = [
        receipt
        for receipt in authorization["receipts"]
        if receipt["retry_kind"] == retry_kind
    ]
    if len(matching) > 1:
        raise core.LockedEvaluationError(
            "Stage-E retry receipt membership is not exact"
        )
    return None if not matching else matching[0]


def _load_prediction_attempt_context(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    authorization: Mapping[str, Any],
    prediction_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    retries = [
        receipt
        for receipt in authorization["receipts"]
        if receipt["retry_kind"] == "infrastructure_pre_input"
    ]
    if len(retries) > 1:
        raise core.LockedEvaluationError(
            "prediction retry receipt membership is not exact"
        )
    retry_receipt = retries[0] if retries else None
    retry_kind = "none" if retry_receipt is None else retry_receipt["retry_kind"]
    execution_id = prediction_receipt["execution_id"]
    if retry_receipt is not None:
        input_receipt = next(
            receipt
            for receipt in authorization["receipts"]
            if receipt["state"] == "INPUTS_READ"
            and receipt["retry_kind"] == "none"
        )
        if (
            retry_receipt["execution_id"] != execution_id
            or input_receipt["execution_id"] != execution_id
            or input_receipt["previous_receipt_sha256"]
            != core.state_receipt_sha256(retry_receipt)
        ):
            raise core.LockedEvaluationError(
                "successful prediction state does not descend from its retry"
            )
    core.validate_exact_attempt_prefix(
        args.predictions_prefix,
        args.parent_prefix,
        args.authorization_id,
        "predictions",
        "P",
        retry_kind,
        execution_id,
    )
    visibility_prefix = core.derive_attempt_prefix(
        args.parent_prefix,
        args.authorization_id,
        "visibility",
        "P",
        retry_kind,
        execution_id,
    )
    prediction_members = {
        f"{args.predictions_prefix}/{name}"
        for name in core.PREDICTION_MEMBER_NAMES
    }
    if core.list_exact_prefix(
        service, args.container, args.predictions_prefix
    ) != prediction_members:
        raise core.LockedEvaluationError(
            "successful prediction attempt membership is not exact"
        )
    visibility_blob = f"{visibility_prefix}/stage_p_visibility.json"
    if retry_receipt is None:
        if visibility_blob not in core.list_exact_prefix(
            service, args.container, visibility_prefix
        ):
            raise core.LockedEvaluationError(
                "primary Stage-P visibility is missing"
            )
        return {
            "retry_kind": retry_kind,
            "execution_id": execution_id,
            "prediction_members": prediction_members,
            "primary_prediction_members": prediction_members,
            "primary_visibility_members": {visibility_blob},
            "all_visibility_members": {visibility_blob},
            "attempt_descriptors": [],
        }

    abandoned_blob = core.derive_abandoned_attempt_blob_name(
        args.parent_prefix,
        args.authorization_id,
        "P",
        retry_kind,
        execution_id,
    )
    if core.list_exact_prefix(
        service, args.container, visibility_prefix
    ) != {abandoned_blob, visibility_blob}:
        raise core.LockedEvaluationError(
            "prediction retry visibility membership is not exact"
        )
    prediction_metadata, _ = _stable_attempt_members(
        core, service, args.container, prediction_members
    )
    visibility_metadata, _ = _stable_attempt_members(
        core, service, args.container, {visibility_blob}
    )
    descriptor = core.build_attempt_membership_descriptor(
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        stage="P",
        retry_kind=retry_kind,
        execution_id=execution_id,
        members=[*prediction_metadata, *visibility_metadata],
    )
    abandoned_bytes, _ = core.download_stable_blob(
        service, args.container, abandoned_blob
    )
    abandoned = core.parse_json_strict(
        abandoned_bytes, "abandoned Stage-P attempt"
    )
    core.validate_abandoned_attempt_record(abandoned)
    previous = next(
        receipt
        for receipt in authorization["receipts"]
        if core.state_receipt_sha256(receipt)
        == retry_receipt["previous_receipt_sha256"]
    )
    core.validate_retry_state_receipt_provenance(
        retry_receipt,
        previous=previous,
        abandoned_attempt_record=abandoned,
        abandoned_attempt_blob_name=abandoned_blob,
        abandoned_attempt_record_sha256=core.sha256_bytes(abandoned_bytes),
    )
    if abandoned_bytes != core.canonical_json_bytes(abandoned):
        raise core.LockedEvaluationError(
            "abandoned Stage-P attempt bytes are not canonical"
        )
    roots = core.evaluation_prefixes(
        args.parent_prefix, args.authorization_id
    )
    return {
        "retry_kind": retry_kind,
        "execution_id": execution_id,
        "prediction_members": prediction_members,
        "primary_prediction_members": {
            item["blob_name"]
            for item in abandoned["abandoned_members"]
            if item["blob_name"].startswith(f"{roots['predictions']}/")
        },
        "primary_visibility_members": {
            item["blob_name"]
            for item in abandoned["abandoned_members"]
            if item["blob_name"].startswith(f"{roots['visibility']}/")
        },
        "all_visibility_members": {
            *{
                item["blob_name"]
                for item in abandoned["abandoned_members"]
                if item["blob_name"].startswith(f"{roots['visibility']}/")
            },
            abandoned_blob,
            visibility_blob,
        },
        "attempt_descriptors": [abandoned, descriptor],
    }


def _prepare_scorer_retry_attempt(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    authorization: dict[str, Any],
    prediction_receipt: Mapping[str, Any],
    *,
    now: Callable[[], str],
) -> dict[str, Any]:
    roots = core.evaluation_prefixes(args.parent_prefix, args.authorization_id)
    primary = _load_primary_stage_e_attempt(
        core, service, args, roots=roots
    )
    retry_receipt = _retry_receipt_for_attempt(
        core, authorization, "scorer_infrastructure"
    )
    abandoned_blob = core.derive_abandoned_attempt_blob_name(
        args.parent_prefix,
        args.authorization_id,
        "E",
        args.retry_kind,
        args.execution_id,
    )
    visibility_blob = f"{args.visibility_prefix}/stage_e_visibility.json"
    visibility_members = core.list_exact_prefix(
        service, args.container, args.visibility_prefix
    )
    if visibility_members not in (
        set(),
        {abandoned_blob},
        {abandoned_blob, visibility_blob},
    ):
        raise core.LockedEvaluationError(
            "current scorer-retry visibility membership is not exact"
        )
    score_members = core.list_exact_prefix(
        service, args.container, args.scores_prefix
    )
    reservation_blob = f"{args.scores_prefix}/{core.SCORE_MEMBER_NAMES[0]}"
    if score_members not in (set(), {reservation_blob}):
        raise core.LockedEvaluationError(
            "current scorer-retry scores are not an exact safe initial set"
        )
    score_metadata, score_payloads = _stable_attempt_members(
        core, service, args.container, score_members
    )
    if score_members:
        _validate_score_reservation(
            core,
            score_payloads[reservation_blob],
            args,
            prefix=args.scores_prefix,
            retry_kind=args.retry_kind,
            execution_id=args.execution_id,
        )
    if retry_receipt is not None and abandoned_blob not in visibility_members:
        raise core.LockedEvaluationError(
            "scorer retry receipt exists without abandoned-attempt provenance"
        )
    if retry_receipt is None and visibility_blob in visibility_members:
        raise core.LockedEvaluationError(
            "scorer retry visibility exists without its singleton retry claim"
        )

    if abandoned_blob in visibility_members:
        abandoned_bytes, abandoned_etag = core.download_stable_blob(
            service, args.container, abandoned_blob
        )
        abandoned = core.parse_json_strict(
            abandoned_bytes, "abandoned Stage-E attempt"
        )
        expected_abandoned = core.build_abandoned_attempt_record(
            parent_prefix=args.parent_prefix,
            authorization_id=args.authorization_id,
            prior_stage="E",
            prior_retry_kind="none",
            prior_execution_id=primary["visibility"]["execution_id"],
            prior_actor=primary["visibility"]["actor"],
            abandoned_members=primary["metadata"],
            current_retry_kind=args.retry_kind,
            current_execution_id=args.execution_id,
            current_actor=args.actor,
            prior_state_receipt_sha256=core.state_receipt_sha256(
                prediction_receipt
            ),
            created_utc=abandoned["created_utc"],
        )
        if (
            abandoned_bytes != core.canonical_json_bytes(abandoned)
            or not core.exact_json_equal(abandoned, expected_abandoned)
        ):
            raise core.LockedEvaluationError(
                "abandoned Stage-E attempt provenance differs"
            )
        abandoned_persistence = {
            "blob_name": abandoned_blob,
            "size": len(abandoned_bytes),
            "sha256": core.sha256_bytes(abandoned_bytes),
            "etag": abandoned_etag,
        }
    else:
        abandoned = core.build_abandoned_attempt_record(
            parent_prefix=args.parent_prefix,
            authorization_id=args.authorization_id,
            prior_stage="E",
            prior_retry_kind="none",
            prior_execution_id=primary["visibility"]["execution_id"],
            prior_actor=primary["visibility"]["actor"],
            abandoned_members=primary["metadata"],
            current_retry_kind=args.retry_kind,
            current_execution_id=args.execution_id,
            current_actor=args.actor,
            prior_state_receipt_sha256=core.state_receipt_sha256(
                prediction_receipt
            ),
            created_utc=core.max_canonical_utc(
                now(),
                prediction_receipt["timestamp_utc"],
                primary["visibility"]["created_utc"],
            ),
        )
        abandoned_persistence = core.persist_singleton(
            service,
            args.container,
            abandoned_blob,
            core.canonical_json_bytes(abandoned),
        )

    if retry_receipt is None:
        retry_receipt = core.build_provenance_bound_retry_state_receipt(
            prediction_receipt,
            retry_kind=args.retry_kind,
            timestamp_utc=core.max_canonical_utc(
                now(),
                prediction_receipt["timestamp_utc"],
                abandoned["created_utc"],
            ),
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
        retry_bytes, retry_etag = core.download_stable_blob(
            service, args.container, retry_blob
        )
        persisted_retry = core.parse_json_strict(
            retry_bytes, "scorer retry receipt"
        )
        if (
            retry_bytes != core.canonical_json_bytes(persisted_retry)
            or not core.exact_json_equal(persisted_retry, retry_receipt)
        ):
            raise core.LockedEvaluationError(
                "persisted scorer retry receipt differs"
            )
        core.validate_retry_state_receipt_provenance(
            persisted_retry,
            previous=prediction_receipt,
            abandoned_attempt_record=abandoned,
            abandoned_attempt_blob_name=abandoned_blob,
            abandoned_attempt_record_sha256=abandoned_persistence["sha256"],
        )
        if (
            persisted_retry["execution_id"] != args.execution_id
            or persisted_retry["actor"] != args.actor
        ):
            raise core.LockedEvaluationError(
                "scorer retry was already consumed by another execution"
            )
        retry_persistence = {
            "blob_name": retry_blob,
            "size": len(retry_bytes),
            "sha256": core.sha256_bytes(retry_bytes),
            "etag": retry_etag,
        }

    if visibility_blob in visibility_members:
        visibility_bytes, visibility_etag = core.download_stable_blob(
            service, args.container, visibility_blob
        )
        visibility = core.parse_json_strict(
            visibility_bytes, "current scorer-retry visibility"
        )
        core.validate_visibility_record(
            visibility,
            expected_stage="E",
            expected_authorization_id=args.authorization_id,
            expected_parent_prefix=args.parent_prefix,
            expected_retry_kind=args.retry_kind,
            expected_execution_id=args.execution_id,
        )
        if (
            visibility_bytes != core.canonical_json_bytes(visibility)
            or visibility["actor"] != args.actor
        ):
            raise core.LockedEvaluationError(
                "current scorer-retry visibility identity differs"
            )
        visibility_persistence = {
            "blob_name": visibility_blob,
            "size": len(visibility_bytes),
            "sha256": core.sha256_bytes(visibility_bytes),
            "etag": visibility_etag,
        }
    else:
        visibility = core.build_visibility_record(
            stage="E",
            authorization_id=args.authorization_id,
            parent_prefix=args.parent_prefix,
            visibility_prefix=args.visibility_prefix,
            execution_id=args.execution_id,
            actor=args.actor,
            created_utc=core.max_canonical_utc(
                now(),
                prediction_receipt["timestamp_utc"],
                retry_receipt["timestamp_utc"],
            ),
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
            "current scorer-retry visibility leaf membership is not exact"
        )
    if score_members:
        reservation_bytes = score_payloads[reservation_blob]
        reservation = _validate_score_reservation(
            core,
            reservation_bytes,
            args,
            prefix=args.scores_prefix,
            retry_kind=args.retry_kind,
            execution_id=args.execution_id,
        )
    else:
        reservation = core.build_reservation(
            leaf="scores",
            prefix=args.scores_prefix,
            authorization_id=args.authorization_id,
            created_utc=core.max_canonical_utc(
                now(),
                prediction_receipt["timestamp_utc"],
                retry_receipt["timestamp_utc"],
                visibility["created_utc"],
            ),
            nonce=secrets.token_hex(16),
            parent_prefix=args.parent_prefix,
            stage="E",
            retry_kind=args.retry_kind,
            execution_id=args.execution_id,
        )
        reservation_bytes = core.canonical_json_bytes(reservation)
        core.persist_singleton(
            service,
            args.container,
            reservation_blob,
            reservation_bytes,
        )
        score_metadata, score_payloads = _stable_attempt_members(
            core, service, args.container, {reservation_blob}
        )
    return {
        "roots": roots,
        "primary": primary,
        "abandoned_record": abandoned,
        "abandoned_persistence": abandoned_persistence,
        "retry_receipt": retry_receipt,
        "retry_persistence": retry_persistence,
        "score_metadata": score_metadata,
        "score_reservation_bytes": reservation_bytes,
        "score_nonce": reservation["nonce"],
        "visibility": visibility,
        "visibility_persistence": visibility_persistence,
        "visibility_metadata": [visibility_persistence],
    }


def _prepare_primary_stage_e_attempt(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    prediction_receipt: Mapping[str, Any],
    prediction_context: Mapping[str, Any],
    *,
    now: Callable[[], str],
) -> dict[str, Any]:
    roots = core.evaluation_prefixes(args.parent_prefix, args.authorization_id)
    score_members = core.list_exact_prefix(
        service, args.container, roots["scores"]
    )
    reservation_blob = f"{args.scores_prefix}/{core.SCORE_MEMBER_NAMES[0]}"
    if (
        any(member.startswith(f"{roots['scores']}/attempts/") for member in score_members)
        or score_members not in (set(), {reservation_blob})
    ):
        raise core.LockedEvaluationError(
            "primary score destination is not an exact safe initial set"
        )
    visibility_members = core.list_exact_prefix(
        service, args.container, roots["visibility"]
    )
    visibility_blob = f"{args.visibility_prefix}/stage_e_visibility.json"
    prediction_visibility_members = set(
        prediction_context["all_visibility_members"]
    )
    if (
        any(
            member not in prediction_visibility_members
            and member != visibility_blob
            for member in visibility_members
        )
        or visibility_members
        not in (
            prediction_visibility_members,
            {*prediction_visibility_members, visibility_blob},
        )
    ):
        raise core.LockedEvaluationError(
            "primary Stage-E visibility membership is not exact"
        )
    timestamp = core.max_canonical_utc(
        now(), prediction_receipt["timestamp_utc"]
    )
    if visibility_blob in visibility_members:
        visibility_bytes, visibility_etag = core.download_stable_blob(
            service, args.container, visibility_blob
        )
        visibility = core.parse_json_strict(
            visibility_bytes, "primary Stage-E visibility"
        )
        core.validate_visibility_record(
            visibility,
            expected_stage="E",
            expected_authorization_id=args.authorization_id,
            expected_parent_prefix=args.parent_prefix,
            expected_retry_kind="none",
            expected_execution_id=args.execution_id,
        )
        if (
            visibility_bytes != core.canonical_json_bytes(visibility)
            or visibility["actor"] != args.actor
        ):
            raise core.LockedEvaluationError(
                "primary Stage-E visibility identity differs"
            )
        visibility_persistence = {
            "blob_name": visibility_blob,
            "size": len(visibility_bytes),
            "sha256": core.sha256_bytes(visibility_bytes),
            "etag": visibility_etag,
        }
        timestamp = core.max_canonical_utc(
            timestamp, visibility["created_utc"]
        )
    else:
        visibility = core.build_visibility_record(
            stage="E",
            authorization_id=args.authorization_id,
            parent_prefix=args.parent_prefix,
            visibility_prefix=args.visibility_prefix,
            execution_id=args.execution_id,
            actor=args.actor,
            created_utc=timestamp,
            retry_kind="none",
        )
        visibility_persistence = core.persist_singleton(
            service,
            args.container,
            visibility_blob,
            core.canonical_json_bytes(visibility),
        )
    if score_members:
        reservation_bytes, _ = core.download_stable_blob(
            service, args.container, reservation_blob
        )
        reservation = _validate_score_reservation(
            core,
            reservation_bytes,
            args,
            prefix=args.scores_prefix,
            retry_kind="none",
            execution_id=args.execution_id,
        )
        score_nonce = reservation["nonce"]
        timestamp = core.max_canonical_utc(
            timestamp, reservation["created_utc"]
        )
    else:
        reservation = core.build_reservation(
            leaf="scores",
            prefix=args.scores_prefix,
            authorization_id=args.authorization_id,
            created_utc=timestamp,
            nonce=secrets.token_hex(16),
            parent_prefix=args.parent_prefix,
            stage="E",
            retry_kind="none",
            execution_id=args.execution_id,
        )
        reservation_bytes = core.canonical_json_bytes(reservation)
        core.persist_singleton(
            service,
            args.container,
            reservation_blob,
            reservation_bytes,
        )
        score_nonce = reservation["nonce"]
    score_metadata, score_payloads = _stable_attempt_members(
        core, service, args.container, {reservation_blob}
    )
    if score_payloads[reservation_blob] != reservation_bytes:
        raise core.LockedEvaluationError(
            "primary score reservation changed during adoption"
        )
    return {
        "score_metadata": score_metadata,
        "score_reservation_bytes": reservation_bytes,
        "score_nonce": score_nonce,
        "visibility": visibility,
        "visibility_persistence": visibility_persistence,
        "visibility_metadata": [
            {
                **visibility_persistence,
                "size": len(core.canonical_json_bytes(visibility)),
            }
        ],
        "timestamp": timestamp,
    }


def _validate_stage_e_attempt_membership(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    *,
    prediction_members: set[str],
    state_members: set[str],
    score_metadata: Sequence[Mapping[str, Any]],
    visibility_metadata: Sequence[Mapping[str, Any]],
    scorer_context: Mapping[str, Any] | None,
    prediction_context: Mapping[str, Any],
    extra_attempt_descriptors: Sequence[Mapping[str, Any]] = (),
) -> dict[str, set[str]]:
    if prediction_members != prediction_context["prediction_members"]:
        raise core.LockedEvaluationError(
            "Stage-E prediction membership differs from its attempt"
        )
    primary = {
        "predictions": set(
            prediction_context["primary_prediction_members"]
        ),
        "scores": set(),
        "state": state_members,
        "visibility": set(
            prediction_context["primary_visibility_members"]
        ),
    }
    attempts = [
        *prediction_context["attempt_descriptors"],
        *extra_attempt_descriptors,
    ]
    if scorer_context is None:
        primary["scores"] = {
            item["blob_name"] for item in score_metadata
        }
        primary["visibility"].update(
            item["blob_name"] for item in visibility_metadata
        )
    else:
        scorer_descriptor = core.build_attempt_membership_descriptor(
            parent_prefix=args.parent_prefix,
            authorization_id=args.authorization_id,
            stage="E",
            retry_kind="scorer_infrastructure",
            execution_id=scorer_context["retry_receipt"]["execution_id"],
            members=sorted(
                [*score_metadata, *visibility_metadata],
                key=lambda item: item["blob_name"],
            ),
        )
        primary["scores"] = set(
            scorer_context["primary"]["score_members"]
        )
        primary["visibility"].update(
            scorer_context["primary"]["stage_e_visibility_members"]
        )
        attempts.extend([
            scorer_context["abandoned_record"],
            scorer_descriptor,
        ])
    expected = core.expected_authorization_attempt_membership(
        args.parent_prefix,
        args.authorization_id,
        attempts,
        primary_membership=primary,
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
            args.parent_prefix, set().union(*expected.values())
        ),
    )
    return expected


def _persist_or_adopt_scoring_incomplete(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    *,
    state_members: set[str],
    now: Callable[[], str],
) -> dict[str, Any]:
    transaction_blob = (
        f"{args.state_prefix}/{core.LABELS_OPEN_TRANSACTION_FILENAME}"
    )
    transaction_bytes, _ = core.download_stable_blob(
        service, args.container, transaction_blob
    )
    transaction = core.parse_json_strict(
        transaction_bytes, "incomplete labels-open transaction"
    )
    core.validate_labels_open_transaction(
        transaction,
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
    )
    score_members = core.list_exact_prefix(
        service, args.container, transaction["scores_prefix"]
    )
    score_metadata, _ = _stable_attempt_members(
        core, service, args.container, score_members
    )
    evidence_blob = (
        f"{args.state_prefix}/{core.SCORING_INCOMPLETE_FILENAME}"
    )
    if evidence_blob in state_members:
        evidence_bytes, evidence_etag = core.download_stable_blob(
            service, args.container, evidence_blob
        )
        evidence = core.parse_json_strict(
            evidence_bytes, "scoring-incomplete evidence"
        )
        core.validate_scoring_incomplete_record(
            evidence, labels_open_transaction=transaction
        )
        if (
            evidence_bytes != core.canonical_json_bytes(evidence)
            or evidence["observed_state_members"]
            != sorted(state_members - {evidence_blob})
            or evidence["observed_score_members"] != score_metadata
        ):
            raise core.LockedEvaluationError(
                "scoring-incomplete evidence differs from persisted bytes"
            )
        return {
            "blob_name": evidence_blob,
            "size": len(evidence_bytes),
            "sha256": core.sha256_bytes(evidence_bytes),
            "etag": evidence_etag,
        }
    evidence = core.build_scoring_incomplete_record(
        transaction,
        observed_score_members=score_metadata,
        observed_state_members=sorted(state_members),
        evidence_execution_id=args.execution_id,
        evidence_actor=args.actor,
        created_utc=core.max_canonical_utc(
            now(), transaction["created_utc"]
        ),
    )
    return core.persist_scoring_incomplete_record(
        service,
        args.container,
        args.state_prefix,
        evidence,
        labels_open_transaction=transaction,
    )


def _authenticate_invalid_closure_provenance(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    *,
    authorization: Mapping[str, Any],
    prediction_receipt: Mapping[str, Any],
    transaction: Mapping[str, Any],
    score_payloads: Mapping[str, bytes],
    visibility_metadata: Sequence[Mapping[str, Any]],
    visibility_payloads: Mapping[str, bytes],
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    checked_transaction = core.validate_labels_open_transaction(
        transaction,
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
    )
    prediction_context = _load_prediction_attempt_context(
        core,
        service,
        args,
        authorization,
        prediction_receipt,
    )
    prediction_manifest_blob = (
        f"{args.predictions_prefix}/{core.PREDICTION_MEMBER_NAMES[-1]}"
    )
    prediction_manifest_bytes, prediction_manifest_etag = (
        core.download_stable_blob(
            service,
            args.container,
            prediction_manifest_blob,
        )
    )
    prediction_manifest = core.validate_prediction_artifact_manifest(
        prediction_manifest_bytes,
        expected_sha256=checked_transaction["prediction_manifest_sha256"],
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        expected_retry_kind=prediction_context["retry_kind"],
        expected_execution_id=prediction_context["execution_id"],
    )
    prediction_artifacts = core.download_prediction_artifacts(
        service,
        args.container,
        args.predictions_prefix,
        prediction_manifest_bytes,
        prediction_manifest,
        prediction_manifest_etag,
    )
    prediction_seal = core.parse_json_strict(
        prediction_artifacts["prediction_seal.json"],
        "prediction seal",
    )
    core.validate_locked_prediction_seal(
        prediction_seal,
        request_manifest_bytes=prediction_artifacts[
            "prediction_request_manifest.json"
        ],
        predictions_bytes=prediction_artifacts[_CANDIDATE_PREDICTIONS_MEMBER],
        legacy_predictions_bytes=prediction_artifacts[_LEGACY_PREDICTIONS_MEMBER],
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_retry_kind=prediction_context["retry_kind"],
        expected_execution_id=prediction_context["execution_id"],
    )
    input_receipts = [
        receipt
        for receipt in authorization["receipts"]
        if receipt["state"] == "INPUTS_READ"
        and receipt["retry_kind"] == "none"
    ]
    if len(input_receipts) != 1:
        raise core.LockedEvaluationError(
            "INVALID closure input receipt is not unique"
        )
    input_receipt = input_receipts[0]
    request_manifest = core.parse_json_strict(
        prediction_artifacts["prediction_request_manifest.json"],
        "prediction request manifest",
    )
    expected_input_manifest_sha256 = input_receipt[
        "artifact_manifest_hashes"
    ]["inputs_manifest"]
    prediction_graph = core.validate_prediction_artifact_graph(
        prediction_manifest_bytes,
        prediction_manifest,
        prediction_artifacts,
        gates=gates,
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_prediction_manifest_sha256=core.sha256_bytes(
            prediction_manifest_bytes
        ),
        expected_input_manifest_sha256=expected_input_manifest_sha256,
        expected_input_receipt_sha256=core.state_receipt_sha256(
            input_receipt
        ),
        expected_authorization_lock_sha256=authorization[
            "authorization_lock_sha256"
        ],
        expected_authorization_manifest_sha256=authorization[
            "authorization_manifest_sha256"
        ],
        expected_implementation_manifest_sha256=authorization[
            "implementation_manifest_sha256"
        ],
        expected_locked_manifest_sha256=authorization[
            "locked_manifest_sha256"
        ],
        expected_implementation_commit=args.implementation_commit,
        expected_image_digest=args.image_digest,
        expected_config_sha256=args.config_sha256,
        expected_locked_input_source_binding=authorization[
            "authorization_manifest"
        ],
        expected_retry_kind=prediction_context["retry_kind"],
        expected_execution_id=prediction_context["execution_id"],
    )
    _validate_prior_prediction_state(
        core,
        prediction_receipt,
        args,
        core.sha256_bytes(prediction_manifest_bytes),
    )
    if (
        request_manifest.get("locked_input_manifest_sha256")
        != expected_input_manifest_sha256
    ):
        raise core.LockedEvaluationError(
            "INVALID closure prediction source binding differs"
        )

    labels_manifest_blob = (
        f"{args.parent_prefix}/locked-labels/locked_labels_manifest.json"
    )
    labels_blob = (
        f"{args.parent_prefix}/locked-labels/locked_reference_labels.jsonl"
    )
    labels_manifest_bytes, labels_manifest_etag = (
        core.download_verified_blob(
            service,
            args.container,
            labels_manifest_blob,
            expected_sha256=checked_transaction["labels_manifest_sha256"],
            expected_etag=checked_transaction["labels_manifest_etag"],
        )
    )
    labels_binding = core.validate_locked_labels_manifest(
        labels_manifest_bytes,
        expected_manifest_sha256=checked_transaction[
            "labels_manifest_sha256"
        ],
        expected_payload_sha256=checked_transaction["labels_sha256"],
        parent_prefix=args.parent_prefix,
        payload_relative_path=(
            "locked-labels/locked_reference_labels.jsonl"
        ),
        gates=gates,
    )
    if (
        labels_binding["ordered_case_ids"]
        != prediction_graph["ordered_case_ids"]
        or labels_binding["manifest_sha256"]
        != prediction_receipt["artifact_manifest_hashes"][
            "locked_labels_manifest"
        ]
    ):
        raise core.LockedEvaluationError(
            "INVALID closure label universe differs from predictions"
        )

    scoring_retry_kind = checked_transaction["scoring_retry_kind"]
    scoring_execution_id = checked_transaction["execution_id"]
    scores_prefix = core.validate_exact_attempt_prefix(
        checked_transaction["scores_prefix"],
        args.parent_prefix,
        args.authorization_id,
        "scores",
        "E",
        scoring_retry_kind,
        scoring_execution_id,
    )
    retry_receipts = [
        receipt
        for receipt in authorization["receipts"]
        if receipt["retry_kind"] == "scorer_infrastructure"
    ]
    scoring_predecessor = prediction_receipt
    if scoring_retry_kind == "none":
        if retry_receipts:
            raise core.LockedEvaluationError(
                "INVALID closure has an unmatched scorer retry"
            )
        retry_receipt_sha256 = None
    else:
        if (
            scoring_retry_kind != "scorer_infrastructure"
            or len(retry_receipts) != 1
        ):
            raise core.LockedEvaluationError(
                "INVALID closure scorer retry is not unique"
            )
        retry_receipt = retry_receipts[0]
        retry_receipt_sha256 = core.state_receipt_sha256(retry_receipt)
        if (
            retry_receipt["execution_id"] != scoring_execution_id
            or retry_receipt["actor"] != checked_transaction["actor"]
            or checked_transaction["retry_receipt_sha256"]
            != retry_receipt_sha256
        ):
            raise core.LockedEvaluationError(
                "INVALID closure scorer retry provenance differs"
            )
        scoring_predecessor = retry_receipt

    visibility_prefix = core.derive_attempt_prefix(
        args.parent_prefix,
        args.authorization_id,
        "visibility",
        "E",
        scoring_retry_kind,
        scoring_execution_id,
    )
    visibility_blob = f"{visibility_prefix}/stage_e_visibility.json"
    visibility_metadata_by_blob = {
        item["blob_name"]: item for item in visibility_metadata
    }
    expected_visibility_members = {visibility_blob}
    if scoring_retry_kind == "none":
        expected_visibility_members.update(
            prediction_context["all_visibility_members"]
        )
    else:
        roots = core.evaluation_prefixes(
            args.parent_prefix,
            args.authorization_id,
        )
        primary = _load_primary_stage_e_attempt(
            core,
            service,
            args,
            roots=roots,
        )
        abandoned_blob = core.derive_abandoned_attempt_blob_name(
            args.parent_prefix,
            args.authorization_id,
            "E",
            scoring_retry_kind,
            scoring_execution_id,
        )
        expected_visibility_members.add(abandoned_blob)
        if abandoned_blob not in visibility_payloads:
            raise core.LockedEvaluationError(
                "INVALID closure abandoned scorer provenance is missing"
            )
        abandoned = core.parse_json_strict(
            visibility_payloads[abandoned_blob],
            "INVALID closure abandoned Stage-E attempt",
        )
        expected_abandoned = core.build_abandoned_attempt_record(
            parent_prefix=args.parent_prefix,
            authorization_id=args.authorization_id,
            prior_stage="E",
            prior_retry_kind="none",
            prior_execution_id=primary["visibility"]["execution_id"],
            prior_actor=primary["visibility"]["actor"],
            abandoned_members=primary["metadata"],
            current_retry_kind=scoring_retry_kind,
            current_execution_id=scoring_execution_id,
            current_actor=checked_transaction["actor"],
            prior_state_receipt_sha256=core.state_receipt_sha256(
                prediction_receipt
            ),
            created_utc=abandoned["created_utc"],
        )
        if (
            visibility_payloads[abandoned_blob]
            != core.canonical_json_bytes(abandoned)
            or not core.exact_json_equal(
                abandoned,
                expected_abandoned,
            )
        ):
            raise core.LockedEvaluationError(
                "INVALID closure abandoned scorer provenance differs"
            )
        core.validate_retry_state_receipt_provenance(
            retry_receipt,
            previous=prediction_receipt,
            abandoned_attempt_record=abandoned,
            abandoned_attempt_blob_name=abandoned_blob,
            abandoned_attempt_record_sha256=core.sha256_bytes(
                visibility_payloads[abandoned_blob]
            ),
        )
    if (
        set(visibility_payloads) != expected_visibility_members
        or set(visibility_metadata_by_blob) != expected_visibility_members
    ):
        raise core.LockedEvaluationError(
            "INVALID closure Stage-E visibility is not exact"
        )
    visibility_data = visibility_payloads[visibility_blob]
    visibility = core.parse_json_strict(
        visibility_data,
        "INVALID closure Stage-E visibility",
    )
    core.validate_visibility_record(
        visibility,
        expected_stage="E",
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_retry_kind=scoring_retry_kind,
        expected_execution_id=scoring_execution_id,
    )
    if visibility_data != core.canonical_json_bytes(visibility):
        raise core.LockedEvaluationError(
            "INVALID closure Stage-E visibility is not canonical"
        )
    if visibility["actor"] != checked_transaction["actor"]:
        raise core.LockedEvaluationError(
            "INVALID closure Stage-E visibility actor differs"
        )
    if (
        core.sha256_bytes(visibility_data)
        != checked_transaction["visibility_sha256"]
    ):
        raise core.LockedEvaluationError(
            "INVALID closure Stage-E visibility hash differs"
        )

    reservation_blob = f"{scores_prefix}/{core.SCORE_MEMBER_NAMES[0]}"
    if reservation_blob not in score_payloads:
        raise core.LockedEvaluationError(
            "INVALID closure score reservation is missing"
        )
    reservation = _validate_score_reservation(
        core,
        score_payloads[reservation_blob],
        args,
        prefix=scores_prefix,
        retry_kind=scoring_retry_kind,
        execution_id=scoring_execution_id,
    )
    expected_created_utc = core.max_canonical_utc(
        reservation["created_utc"],
        prediction_receipt["timestamp_utc"],
        visibility["created_utc"],
    )
    expected_transaction = core.build_labels_open_transaction(
        authorization_id=args.authorization_id,
        parent_prefix=args.parent_prefix,
        state_prefix=args.state_prefix,
        scores_prefix=scores_prefix,
        scoring_retry_kind=scoring_retry_kind,
        retry_receipt_sha256=retry_receipt_sha256,
        authorization_lock_sha256=authorization[
            "authorization_lock_sha256"
        ],
        authorization_manifest_sha256=authorization[
            "authorization_manifest_sha256"
        ],
        implementation_manifest_sha256=authorization[
            "implementation_manifest_sha256"
        ],
        prediction_manifest_sha256=core.sha256_bytes(
            prediction_manifest_bytes
        ),
        prediction_seal_sha256=core.sha256_bytes(
            prediction_artifacts["prediction_seal.json"]
        ),
        prediction_request_manifest_sha256=core.sha256_bytes(
            prediction_artifacts["prediction_request_manifest.json"]
        ),
        input_manifest_sha256=expected_input_manifest_sha256,
        locked_manifest_sha256=authorization["locked_manifest_sha256"],
        labels_manifest_sha256=core.sha256_bytes(labels_manifest_bytes),
        labels_manifest_blob_name=labels_manifest_blob,
        labels_manifest_etag=labels_manifest_etag,
        labels_blob_name=labels_blob,
        labels_sha256=labels_binding["payload_sha256"],
        ordered_case_ids=prediction_graph["ordered_case_ids"],
        prior_receipt_sha256=core.state_receipt_sha256(
            scoring_predecessor
        ),
        visibility_blob_name=visibility_blob,
        visibility_sha256=core.sha256_bytes(visibility_data),
        visibility_etag=visibility_metadata_by_blob[visibility_blob][
            "etag"
        ],
        implementation_commit=args.implementation_commit,
        image_digest=args.image_digest,
        config_sha256=args.config_sha256,
        execution_id=scoring_execution_id,
        actor=visibility["actor"],
        created_utc=expected_created_utc,
    )
    if not core.exact_json_equal(
        checked_transaction,
        expected_transaction,
    ):
        raise core.LockedEvaluationError(
            "labels-open transaction differs from authenticated provenance"
        )
    return {
        "transaction": expected_transaction,
        "prediction_context": prediction_context,
        "scoring_predecessor": scoring_predecessor,
    }


def _close_invalid_open_attempt(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
) -> dict[str, Any]:
    transaction_blob = (
        f"{args.state_prefix}/{core.LABELS_OPEN_TRANSACTION_FILENAME}"
    )
    transaction_bytes, _ = core.download_stable_blob(
        service, args.container, transaction_blob
    )
    transaction = core.parse_json_strict(
        transaction_bytes, "INVALID labels-open transaction"
    )
    core.validate_labels_open_transaction(
        transaction,
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
    )
    if transaction_bytes != core.canonical_json_bytes(transaction):
        raise core.LockedEvaluationError(
            "INVALID labels-open transaction is not canonical"
        )
    expected_producer_retry = getattr(
        args,
        "producer_retry_kind",
        None,
    )
    expected_producer_execution = getattr(
        args,
        "producer_execution_id",
        None,
    )
    if expected_producer_retry is not None and (
        transaction["scoring_retry_kind"] != expected_producer_retry
        or transaction["execution_id"] != expected_producer_execution
    ):
        raise core.LockedEvaluationError(
            "INVALID closure producer differs from authenticated launch"
        )
    state_members = core.list_exact_prefix(
        service, args.container, args.state_prefix
    )
    labels_receipt_blob = (
        f"{args.state_prefix}/"
        f"{core.STATE_RECEIPT_FILENAMES['LABELS_READ']}"
    )
    closed_receipt_blob = (
        f"{args.state_prefix}/{core.STATE_RECEIPT_FILENAMES['CLOSED']}"
    )
    invalid_blob = (
        f"{args.state_prefix}/{core.INVALID_CLOSURE_FILENAME}"
    )
    scoring_transaction_present = (
        f"{args.state_prefix}/{core.SCORING_TRANSACTION_FILENAME}"
        in state_members
    )
    scoring_attestation_present = (
        f"{args.state_prefix}/{core.SCORING_ATTESTATION_FILENAME}"
        in state_members
    )
    labels_receipt_present = labels_receipt_blob in state_members
    invalid_present = invalid_blob in state_members
    closed_present = closed_receipt_blob in state_members
    if closed_present and not invalid_present:
        raise core.LockedEvaluationError(
            "CLOSED exists without INVALID closure evidence"
        )
    authorization_target = (
        "CLOSED"
        if closed_present
        else "LABELS_READ"
        if labels_receipt_present
        else "PREDICTIONS_VERIFIED"
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
        expected_helper_snapshot_set_sha256=(
            args.helper_snapshot_set_sha256
        ),
        final_state=authorization_target,
        labels_transaction=True,
        scoring_transaction=scoring_transaction_present,
        scoring_attestation=scoring_attestation_present,
        spent_incomplete=(
            f"{args.state_prefix}/{core.SPENT_INCOMPLETE_FILENAME}"
            in state_members
        ),
        invalid_closure=invalid_present,
    )
    prediction_receipts = [
        receipt
        for receipt in authorization["receipts"]
        if receipt["state"] == "PREDICTIONS_VERIFIED"
        and receipt["retry_kind"] == "none"
    ]
    if len(prediction_receipts) != 1:
        raise core.LockedEvaluationError(
            "INVALID closure prediction receipt is not unique"
        )
    prediction_receipt = prediction_receipts[0]
    score_members = core.list_exact_prefix(
        service, args.container, transaction["scores_prefix"]
    )
    score_metadata, score_payloads = _stable_attempt_members(
        core, service, args.container, score_members
    )
    visibility_prefix = transaction["visibility_blob_name"].rsplit("/", 1)[0]
    visibility_members = core.list_exact_prefix(
        service, args.container, visibility_prefix
    )
    visibility_metadata, visibility_payloads = _stable_attempt_members(
        core, service, args.container, visibility_members
    )
    state_artifact_names = {
        name
        for name, present in (
            (
                f"{args.state_prefix}/{core.SCORING_TRANSACTION_FILENAME}",
                scoring_transaction_present,
            ),
            (
                f"{args.state_prefix}/{core.SCORING_ATTESTATION_FILENAME}",
                scoring_attestation_present,
            ),
        )
        if present
    }
    state_artifact_metadata, _ = _stable_attempt_members(
        core, service, args.container, state_artifact_names
    )
    gates = core.load_acceptance_gates(
        core.load_frozen_gate_bytes(PROJECT_ROOT)
    )
    provenance = _authenticate_invalid_closure_provenance(
        core,
        service,
        args,
        authorization=authorization,
        prediction_receipt=prediction_receipt,
        transaction=transaction,
        score_payloads=score_payloads,
        visibility_metadata=visibility_metadata,
        visibility_payloads=visibility_payloads,
        gates=gates,
    )
    transaction = provenance["transaction"]
    prediction_context = provenance["prediction_context"]
    prior_receipt = provenance["scoring_predecessor"]
    if closed_present:
        return {
            "stage": "E",
            "mode": "invalid_closure_recovery",
            "status": "INVALID",
            "result_status": "INVALID",
            "authorization_id": args.authorization_id,
            "holdout_spent": True,
            "holdout_retired": True,
            "formal_evaluation_count": 1,
            "labels_reread": False,
            "metrics_recomputed": False,
            "metric_retry_allowed": False,
            "writes_performed": False,
            "closed_receipt_sha256": core.state_receipt_sha256(
                authorization["prior_receipt"]
            ),
        }
    visibility_bytes, _ = core.download_verified_blob(
        service,
        args.container,
        transaction["visibility_blob_name"],
        expected_sha256=transaction["visibility_sha256"],
        expected_etag=transaction["visibility_etag"],
    )
    visibility = core.parse_json_strict(
        visibility_bytes, "INVALID Stage-E visibility"
    )
    core.validate_visibility_record(
        visibility,
        expected_stage="E",
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_retry_kind=transaction["scoring_retry_kind"],
        expected_execution_id=transaction["execution_id"],
    )
    expected_labels_receipt = core.build_next_state_receipt(
        prior_receipt,
        state="LABELS_READ",
        artifact_manifest_sha256=transaction["labels_manifest_sha256"],
        timestamp_utc=transaction["created_utc"],
        execution_id=transaction["execution_id"],
        actor=transaction["actor"],
        visibility=[
            *visibility["artifact_classes"],
            f"record_sha256:{transaction['visibility_sha256']}",
        ],
        authorization_lock=authorization["authorization_lock"],
        implementation_manifest_bytes=authorization[
            "implementation_manifest_bytes"
        ],
    )
    expected_labels_bytes = core.canonical_json_bytes(
        expected_labels_receipt
    )
    if labels_receipt_present:
        persisted_labels, labels_etag = core.download_stable_blob(
            service, args.container, labels_receipt_blob
        )
        if persisted_labels != expected_labels_bytes:
            raise core.LockedEvaluationError(
                "persisted LABELS_READ receipt differs"
            )
        labels_persistence = {
            "blob_name": labels_receipt_blob,
            "size": len(persisted_labels),
            "sha256": core.sha256_bytes(persisted_labels),
            "etag": labels_etag,
            "adopted": True,
        }
    else:
        labels_persistence = core.persist_or_adopt_state_receipt(
            service,
            args.container,
            args.state_prefix,
            expected_labels_receipt,
        )
    prediction_retry_kind = prediction_context["retry_kind"]
    predictions_prefix = args.predictions_prefix
    invalid = core.build_invalid_closure_manifest(
        transaction,
        expected_labels_receipt,
        prediction_retry_kind=prediction_retry_kind,
        prediction_execution_id=prediction_receipt["execution_id"],
        prediction_actor=prediction_receipt["actor"],
        predictions_prefix=predictions_prefix,
        observed_score_members=score_metadata,
        observed_visibility_members=visibility_metadata,
        observed_state_artifacts=state_artifact_metadata,
    )
    invalid_bytes = core.canonical_json_bytes(invalid)
    if invalid_present:
        persisted_invalid, invalid_etag = core.download_stable_blob(
            service, args.container, invalid_blob
        )
        if persisted_invalid != invalid_bytes:
            raise core.LockedEvaluationError(
                "persisted INVALID closure differs"
            )
        invalid_persistence = {
            "blob_name": invalid_blob,
            "size": len(persisted_invalid),
            "sha256": core.sha256_bytes(persisted_invalid),
            "etag": invalid_etag,
            "adopted": True,
        }
    else:
        invalid_persistence = core.persist_or_adopt_invalid_closure(
            service,
            args.container,
            args.state_prefix,
            invalid,
            labels_open_transaction=transaction,
            labels_read_receipt=expected_labels_receipt,
        )
    closed_receipt = core.build_invalid_closed_state_receipt(
        expected_labels_receipt,
        invalid,
        labels_open_transaction=transaction,
    )
    closed_persistence = core.persist_or_adopt_state_receipt(
        service,
        args.container,
        args.state_prefix,
        closed_receipt,
    )
    core.validate_invalid_closed_outcome(
        closed_receipt,
        invalid,
        labels_open_transaction=transaction,
        labels_read_receipt=expected_labels_receipt,
    )
    core.authenticate_authorization_bundle(
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
        expected_prior_receipt_sha256=closed_persistence["sha256"],
        expected_authorization_lock_sha256=args.authorization_lock_sha256,
        expected_authorization_manifest_sha256=(
            args.authorization_manifest_sha256
        ),
        expected_image_binding_sha256=args.image_binding_sha256,
        expected_helper_snapshot_set_sha256=(
            args.helper_snapshot_set_sha256
        ),
        final_state="CLOSED",
        labels_transaction=True,
        scoring_transaction=scoring_transaction_present,
        scoring_attestation=scoring_attestation_present,
        spent_incomplete=authorization["spent_incomplete"],
        invalid_closure=True,
    )
    return {
        "stage": "E",
        "mode": "invalid_closure_recovery",
        "status": "INVALID",
        "result_status": "INVALID",
        "authorization_id": args.authorization_id,
        "holdout_spent": True,
        "holdout_retired": True,
        "formal_evaluation_count": 1,
        "labels_reread": False,
        "metrics_recomputed": False,
        "metric_retry_allowed": False,
        "labels_receipt_sha256": labels_persistence["sha256"],
        "invalid_closure_sha256": invalid_persistence["sha256"],
        "closed_receipt_sha256": closed_persistence["sha256"],
        "writes_performed": not (
            labels_persistence["adopted"]
            and invalid_persistence["adopted"]
            and closed_persistence["adopted"]
        ),
    }


def _validate_prior_prediction_state(
    core: ModuleType,
    receipt: Mapping[str, Any],
    args: argparse.Namespace,
    prediction_manifest_sha256: str,
) -> None:
    checked = core.validate_state_receipt(
        receipt, name="PREDICTIONS_VERIFIED receipt"
    )
    if (
        checked["state"] != "PREDICTIONS_VERIFIED"
        or receipt["authorization_id"] != args.authorization_id
        or receipt["registered_parent_prefix"] != args.parent_prefix
        or receipt["implementation_commit"] != args.implementation_commit
        or receipt["image_digest"] != args.image_digest
        or receipt["config_sha256"] != args.config_sha256
        or receipt["authorization_lock_sha256"]
        != args.authorization_lock_sha256
        or receipt["artifact_manifest_hashes"]["predictions_manifest"]
        != prediction_manifest_sha256
    ):
        raise core.LockedEvaluationError(
            "Stage E immutable prediction/state binding mismatch"
        )


def _scoring_ledger_context(
    core: ModuleType,
    args: argparse.Namespace,
    *,
    authorization: Mapping[str, Any],
    prediction_manifest: Mapping[str, Any],
    labels_binding: Mapping[str, Any],
    labels_manifest_etag: str,
    labels_etag: str,
    labels_open_transaction_sha256: str,
    scoring_execution_id: str,
    scoring_actor: str,
    scoring_retry_kind: str,
    scores_prefix: str,
    stage_e_visibility_sha256: str,
    retry_receipt_sha256: str | None,
    created_utc: str,
) -> dict[str, Any]:
    return {
        "authorization_id": args.authorization_id,
        "registered_parent_prefix": args.parent_prefix,
        "authorization_lock_sha256": authorization[
            "authorization_lock_sha256"
        ],
        "authorization_manifest_sha256": authorization[
            "authorization_manifest_sha256"
        ],
        "implementation_manifest_sha256": authorization[
            "implementation_manifest_sha256"
        ],
        "prediction_manifest_sha256": args.prediction_manifest_sha256,
        "prediction_seal_sha256": prediction_manifest[
            "prediction_seal_sha256"
        ],
        "prediction_request_manifest_sha256": prediction_manifest[
            "prediction_request_manifest_sha256"
        ],
        "locked_manifest_sha256": authorization["locked_manifest_sha256"],
        "input_manifest_sha256": prediction_manifest[
            "locked_input_manifest_sha256"
        ],
        "locked_input_sha256": prediction_manifest["locked_input_sha256"],
        "labels_manifest_sha256": labels_binding["manifest_sha256"],
        "labels_manifest_etag": labels_manifest_etag,
        "labels_sha256": labels_binding["payload_sha256"],
        "labels_size": labels_binding["payload_size"],
        "labels_etag": labels_etag,
        "labels_open_transaction_sha256": labels_open_transaction_sha256,
        "scores_prefix": scores_prefix,
        "scoring_retry_kind": scoring_retry_kind,
        "stage_e_visibility_sha256": stage_e_visibility_sha256,
        "retry_receipt_sha256": retry_receipt_sha256,
        "case_universe_sha256": prediction_manifest[
            "case_universe_sha256"
        ],
        "row_count": prediction_manifest["row_count"],
        "acceptance_gates_sha256": core.FROZEN_ACCEPTANCE_GATE_SHA256,
        "implementation_commit": args.implementation_commit,
        "image_digest": args.image_digest,
        "config_sha256": args.config_sha256,
        "scoring_execution_id": scoring_execution_id,
        "scoring_actor": scoring_actor,
        "created_utc": created_utc,
    }


def _authenticate_persisted_labels_transaction(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    *,
    score_manifest: Mapping[str, Any],
    metrics: Mapping[str, Any],
    decision: Mapping[str, Any],
    prediction_manifest: Mapping[str, Any],
    prior_receipt: Mapping[str, Any],
    authorization: Mapping[str, Any],
    labels_binding: Mapping[str, Any],
) -> dict[str, Any]:
    transaction_blob = (
        f"{args.state_prefix}/{core.LABELS_OPEN_TRANSACTION_FILENAME}"
    )
    transaction_bytes, _ = core.download_verified_blob(
        service,
        args.container,
        transaction_blob,
        expected_sha256=score_manifest["labels_open_transaction_sha256"],
    )
    transaction = core.parse_json_strict(
        transaction_bytes, "labels-open transaction"
    )
    core.validate_labels_open_transaction(
        transaction,
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
    )
    transaction_sha256 = core.sha256_bytes(transaction_bytes)
    visibility_bytes, _ = core.download_verified_blob(
        service,
        args.container,
        transaction["visibility_blob_name"],
        expected_sha256=transaction["visibility_sha256"],
        expected_etag=transaction["visibility_etag"],
    )
    visibility = core.parse_json_strict(
        visibility_bytes, "Stage-E visibility record"
    )
    core.validate_visibility_record(
        visibility,
        expected_stage="E",
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
    )
    expected_metrics = {
        "authorization_id": args.authorization_id,
        "registered_parent_prefix": args.parent_prefix,
        "authorization_lock_sha256": authorization[
            "authorization_lock_sha256"
        ],
        "authorization_manifest_sha256": authorization[
            "authorization_manifest_sha256"
        ],
        "implementation_manifest_sha256": authorization[
            "implementation_manifest_sha256"
        ],
        "prediction_seal_sha256": prediction_manifest[
            "prediction_seal_sha256"
        ],
        "prediction_manifest_sha256": args.prediction_manifest_sha256,
        "prediction_request_manifest_sha256": prediction_manifest[
            "prediction_request_manifest_sha256"
        ],
        "locked_manifest_sha256": authorization["locked_manifest_sha256"],
        "input_manifest_sha256": prediction_manifest[
            "locked_input_manifest_sha256"
        ],
        "locked_input_sha256": prediction_manifest["locked_input_sha256"],
        "labels_manifest_sha256": labels_binding["manifest_sha256"],
        "labels_sha256": labels_binding["payload_sha256"],
        "labels_open_transaction_sha256": transaction_sha256,
        "scores_prefix": score_manifest["scores_prefix"],
        "scoring_retry_kind": score_manifest["scoring_retry_kind"],
        "scoring_execution_id": score_manifest["scoring_execution_id"],
        "scoring_actor": score_manifest["scoring_actor"],
        "stage_e_visibility_sha256": score_manifest[
            "stage_e_visibility_sha256"
        ],
        "retry_receipt_sha256": score_manifest[
            "retry_receipt_sha256"
        ],
        "scoring_ledger_sha256": score_manifest[
            "scoring_ledger_sha256"
        ],
        "scoring_ledger_size": score_manifest["scoring_ledger_size"],
        "scoring_ledger_etag": score_manifest["scoring_ledger_etag"],
        "case_universe_sha256": prediction_manifest[
            "case_universe_sha256"
        ],
        "row_count": prediction_manifest["row_count"],
        "implementation_commit": args.implementation_commit,
        "image_digest": args.image_digest,
        "config_sha256": args.config_sha256,
    }
    core.validate_metrics_artifact_bindings(metrics, expected_metrics)
    authorized_prediction_receipts = {
        core.state_receipt_sha256(receipt)
        for receipt in authorization["receipts"]
        if receipt["state"] == "PREDICTIONS_VERIFIED"
    }
    if (
        transaction_sha256 != decision["labels_open_transaction_sha256"]
        or transaction_sha256
        != score_manifest["labels_open_transaction_sha256"]
        or transaction["authorization_lock_sha256"]
        != authorization["authorization_lock_sha256"]
        or transaction["authorization_manifest_sha256"]
        != authorization["authorization_manifest_sha256"]
        or transaction["prediction_manifest_sha256"]
        != args.prediction_manifest_sha256
        or transaction["prediction_seal_sha256"]
        != prediction_manifest["prediction_seal_sha256"]
        or transaction["prediction_request_manifest_sha256"]
        != prediction_manifest["prediction_request_manifest_sha256"]
        or transaction["input_manifest_sha256"]
        != prediction_manifest["locked_input_manifest_sha256"]
        or transaction["locked_manifest_sha256"]
        != authorization["locked_manifest_sha256"]
        or transaction["labels_manifest_sha256"]
        != labels_binding["manifest_sha256"]
        or transaction["labels_manifest_blob_name"]
        != args.labels_manifest_blob
        or transaction["labels_manifest_etag"]
        != score_manifest["labels_manifest_etag"]
        or transaction["labels_sha256"] != labels_binding["payload_sha256"]
        or transaction["labels_blob_name"] != args.labels_blob
        or transaction["prior_receipt_sha256"]
        not in authorized_prediction_receipts
        or transaction["visibility_sha256"]
        != score_manifest["stage_e_visibility_sha256"]
        or transaction["visibility_etag"]
        != score_manifest["stage_e_visibility_etag"]
        or transaction["scores_prefix"] != score_manifest["scores_prefix"]
        or transaction["scoring_retry_kind"]
        != score_manifest["scoring_retry_kind"]
        or transaction["retry_receipt_sha256"]
        != score_manifest["retry_receipt_sha256"]
        or transaction["execution_id"]
        != score_manifest["scoring_execution_id"]
        or transaction["actor"] != score_manifest["scoring_actor"]
        or transaction["implementation_commit"] != args.implementation_commit
        or transaction["image_digest"] != args.image_digest
        or transaction["config_sha256"] != args.config_sha256
        or not core.exact_json_equal(
            transaction["ordered_case_ids"],
            prediction_manifest["ordered_case_ids"],
        )
        or transaction["case_universe_sha256"]
        != prediction_manifest["case_universe_sha256"]
        or not core.exact_json_equal(
            transaction["row_count"], prediction_manifest["row_count"]
        )
        or score_manifest["labels_sha256"] != metrics["labels_sha256"]
        or score_manifest["labels_sha256"] != decision["labels_sha256"]
        or score_manifest["labels_manifest_sha256"]
        != decision["labels_manifest_sha256"]
        or score_manifest["scoring_ledger_sha256"]
        != decision["scoring_ledger_sha256"]
        or not core.exact_json_equal(
            score_manifest["scoring_ledger_size"],
            decision["scoring_ledger_size"],
        )
        or score_manifest["scoring_ledger_etag"]
        != decision["scoring_ledger_etag"]
        or score_manifest["authorization_lock_sha256"]
        != decision["authorization_lock_sha256"]
        or score_manifest["authorization_manifest_sha256"]
        != decision["authorization_manifest_sha256"]
    ):
        raise core.LockedEvaluationError(
            "labels-open transaction differs from authenticated score bindings"
        )
    return transaction


def _load_sealed_scoring_attempt(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    *,
    scoring_transaction: Mapping[str, Any],
    labels_transaction: Mapping[str, Any],
    score_manifest: Mapping[str, Any],
    prediction_receipt: Mapping[str, Any],
    authorization: Mapping[str, Any],
) -> dict[str, Any]:
    roots = core.evaluation_prefixes(args.parent_prefix, args.authorization_id)
    retry_kind = scoring_transaction["scoring_retry_kind"]
    execution_id = scoring_transaction["execution_id"]
    score_prefix = scoring_transaction["scores_prefix"]
    core.validate_exact_attempt_prefix(
        score_prefix,
        args.parent_prefix,
        args.authorization_id,
        "scores",
        "E",
        retry_kind,
        execution_id,
    )
    expected_score_members = {
        f"{score_prefix}/{name}" for name in core.SCORE_MEMBER_NAMES
    }
    if core.list_exact_prefix(
        service, args.container, score_prefix
    ) != expected_score_members:
        raise core.LockedEvaluationError(
            "sealed scoring attempt membership is not exact"
        )
    score_metadata, score_payloads_by_blob = _stable_attempt_members(
        core, service, args.container, expected_score_members
    )
    score_payloads = {
        name: score_payloads_by_blob[f"{score_prefix}/{name}"]
        for name in core.SCORE_MEMBER_NAMES[:-1]
    }
    metadata_by_name = {
        item["blob_name"].removeprefix(f"{score_prefix}/"): item
        for item in score_metadata
    }
    for item in score_manifest["payload_members"]:
        observed = metadata_by_name.get(item["name"])
        if observed is None or not core.exact_json_equal(
            {
                "name": item["name"],
                "size": observed["size"],
                "sha256": observed["sha256"],
                "etag": observed["etag"],
            },
            item,
        ):
            raise core.LockedEvaluationError(
                "sealed score member metadata differs from its manifest"
            )

    visibility_blob = labels_transaction["visibility_blob_name"]
    visibility_metadata, visibility_payloads = _stable_attempt_members(
        core, service, args.container, {visibility_blob}
    )
    visibility_bytes = visibility_payloads[visibility_blob]
    visibility = core.parse_json_strict(
        visibility_bytes, "sealed Stage-E visibility"
    )
    core.validate_visibility_record(
        visibility,
        expected_stage="E",
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_retry_kind=retry_kind,
        expected_execution_id=execution_id,
    )
    if (
        visibility_bytes != core.canonical_json_bytes(visibility)
        or visibility["actor"] != scoring_transaction["actor"]
        or core.sha256_bytes(visibility_bytes)
        != scoring_transaction["stage_e_visibility_sha256"]
        or labels_transaction["visibility_sha256"]
        != scoring_transaction["stage_e_visibility_sha256"]
        or labels_transaction["visibility_etag"]
        != score_manifest["stage_e_visibility_etag"]
        or score_manifest["stage_e_visibility_sha256"]
        != scoring_transaction["stage_e_visibility_sha256"]
    ):
        raise core.LockedEvaluationError(
            "sealed Stage-E visibility provenance differs"
        )

    scorer_context = None
    if retry_kind == "none":
        direct_scores = _direct_leaf_members(
            roots["scores"],
            core.list_exact_prefix(service, args.container, roots["scores"]),
        )
        direct_visibility = _direct_leaf_members(
            roots["visibility"],
            core.list_exact_prefix(
                service, args.container, roots["visibility"]
            ),
        )
        expected_visibility = {
            f"{roots['visibility']}/stage_p_visibility.json",
            f"{roots['visibility']}/stage_e_visibility.json",
        }
        if (
            score_prefix != roots["scores"]
            or direct_scores != expected_score_members
            or direct_visibility != expected_visibility
            or visibility_blob
            != f"{roots['visibility']}/stage_e_visibility.json"
        ):
            raise core.LockedEvaluationError(
                "sealed primary scoring attempt is not exact"
            )
        scoring_visibility_metadata, _ = _stable_attempt_members(
            core,
            service,
            args.container,
            expected_visibility,
        )
    elif retry_kind == "scorer_infrastructure":
        scorer_retry = _retry_receipt_for_attempt(
            core, authorization, "scorer_infrastructure"
        )
        if (
            scorer_retry is None
            or core.state_receipt_sha256(scorer_retry)
            != scoring_transaction["retry_receipt_sha256"]
            or scorer_retry["execution_id"] != execution_id
            or scorer_retry["actor"] != scoring_transaction["actor"]
            or labels_transaction["prior_receipt_sha256"]
            != scoring_transaction["retry_receipt_sha256"]
        ):
            raise core.LockedEvaluationError(
                "sealed scorer retry receipt binding differs"
            )
        primary_scores = _direct_leaf_members(
            roots["scores"],
            core.list_exact_prefix(service, args.container, roots["scores"]),
        )
        primary_visibility = _direct_leaf_members(
            roots["visibility"],
            core.list_exact_prefix(
                service, args.container, roots["visibility"]
            ),
        )
        reservation_blob = (
            f"{roots['scores']}/{core.SCORE_MEMBER_NAMES[0]}"
        )
        expected_primary_visibility = {
            f"{roots['visibility']}/stage_p_visibility.json",
            f"{roots['visibility']}/stage_e_visibility.json",
        }
        if (
            primary_scores not in (set(), {reservation_blob})
            or primary_visibility != expected_primary_visibility
        ):
            raise core.LockedEvaluationError(
                "sealed scorer retry primary attempt is not an immutable partial"
            )
        primary_metadata, primary_payloads = _stable_attempt_members(
            core,
            service,
            args.container,
            primary_scores | primary_visibility,
        )
        primary_visibility_blob = (
            f"{roots['visibility']}/stage_e_visibility.json"
        )
        primary_stage_e = core.parse_json_strict(
            primary_payloads[primary_visibility_blob],
            "primary Stage-E visibility",
        )
        core.validate_visibility_record(
            primary_stage_e,
            expected_stage="E",
            expected_authorization_id=args.authorization_id,
            expected_parent_prefix=args.parent_prefix,
            expected_retry_kind="none",
        )
        if primary_stage_e["execution_id"] == execution_id:
            raise core.LockedEvaluationError(
                "scorer retry does not identify another primary execution"
            )
        if primary_scores:
            _validate_score_reservation(
                core,
                primary_payloads[reservation_blob],
                args,
                prefix=roots["scores"],
                retry_kind="none",
                execution_id=primary_stage_e["execution_id"],
            )
        scorer_visibility_prefix = core.derive_attempt_prefix(
            args.parent_prefix,
            args.authorization_id,
            "visibility",
            "E",
            "scorer_infrastructure",
            execution_id,
        )
        abandoned_blob = core.derive_abandoned_attempt_blob_name(
            args.parent_prefix,
            args.authorization_id,
            "E",
            "scorer_infrastructure",
            execution_id,
        )
        if (
            visibility_blob
            != f"{scorer_visibility_prefix}/stage_e_visibility.json"
            or core.list_exact_prefix(
                service, args.container, scorer_visibility_prefix
            )
            != {abandoned_blob, visibility_blob}
        ):
            raise core.LockedEvaluationError(
                "sealed scorer visibility attempt membership is not exact"
            )
        abandoned_bytes, abandoned_etag = core.download_stable_blob(
            service, args.container, abandoned_blob
        )
        abandoned = core.parse_json_strict(
            abandoned_bytes, "sealed abandoned Stage-E attempt"
        )
        expected_abandoned = core.build_abandoned_attempt_record(
            parent_prefix=args.parent_prefix,
            authorization_id=args.authorization_id,
            prior_stage="E",
            prior_retry_kind="none",
            prior_execution_id=primary_stage_e["execution_id"],
            prior_actor=primary_stage_e["actor"],
            abandoned_members=primary_metadata,
            current_retry_kind="scorer_infrastructure",
            current_execution_id=execution_id,
            current_actor=scoring_transaction["actor"],
            prior_state_receipt_sha256=core.state_receipt_sha256(
                prediction_receipt
            ),
            created_utc=abandoned["created_utc"],
        )
        if (
            abandoned_bytes != core.canonical_json_bytes(abandoned)
            or not core.exact_json_equal(abandoned, expected_abandoned)
        ):
            raise core.LockedEvaluationError(
                "sealed abandoned Stage-E provenance differs"
            )
        core.validate_retry_state_receipt_provenance(
            scorer_retry,
            previous=prediction_receipt,
            abandoned_attempt_record=abandoned,
            abandoned_attempt_blob_name=abandoned_blob,
            abandoned_attempt_record_sha256=core.sha256_bytes(
                abandoned_bytes
            ),
        )
        scorer_context = {
            "primary": {
                "score_members": primary_scores,
                "stage_p_visibility_members": {
                    f"{roots['visibility']}/stage_p_visibility.json"
                },
                "stage_e_visibility_members": {primary_visibility_blob},
            },
            "abandoned_record": abandoned,
            "abandoned_persistence": {
                "blob_name": abandoned_blob,
                "size": len(abandoned_bytes),
                "sha256": core.sha256_bytes(abandoned_bytes),
                "etag": abandoned_etag,
            },
            "retry_receipt": scorer_retry,
        }
        scoring_visibility_metadata = visibility_metadata
    else:
        raise core.LockedEvaluationError(
            "sealed score artifacts use an invalid scoring retry kind"
        )
    return {
        "score_metadata": score_metadata,
        "score_payloads": score_payloads,
        "scoring_visibility_metadata": scoring_visibility_metadata,
        "scoring_visibility": visibility,
        "scorer_context": scorer_context,
    }


def _validate_verification_membership(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    *,
    prediction_members: set[str],
    prediction_context: Mapping[str, Any],
    state_members: set[str],
    sealed_attempt: Mapping[str, Any],
    verification_visibility_metadata: Sequence[Mapping[str, Any]],
) -> dict[str, set[str]]:
    verification_descriptor = core.build_attempt_membership_descriptor(
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        stage="E",
        retry_kind="verification_only",
        execution_id=args.execution_id,
        members=verification_visibility_metadata,
    )
    return _validate_stage_e_attempt_membership(
        core,
        service,
        args,
        prediction_members=prediction_members,
        prediction_context=prediction_context,
        state_members=state_members,
        score_metadata=sealed_attempt["score_metadata"],
        visibility_metadata=sealed_attempt[
            "scoring_visibility_metadata"
        ],
        scorer_context=sealed_attempt["scorer_context"],
        extra_attempt_descriptors=[verification_descriptor],
    )


def _legacy_verify_score_prefix(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    prediction_manifest: Mapping[str, Any],
    prediction_artifacts: Mapping[str, bytes],
    prior_receipt: Mapping[str, Any],
    authorization: Mapping[str, Any],
    labels_binding: Mapping[str, Any],
    labels_manifest_etag: str,
    gates: Mapping[str, Any],
    gate_bytes: bytes,
    now: Callable[[], str],
) -> dict[str, Any]:
    if not args.scores_manifest_sha256:
        raise core.LockedEvaluationError(
            "verification-only mode requires the persisted score-manifest hash"
        )
    manifest_name = core.SCORE_MEMBER_NAMES[-1]
    manifest_blob = f"{args.scores_prefix}/{manifest_name}"
    manifest_bytes, manifest_etag = core.download_verified_blob(
        service,
        args.container,
        manifest_blob,
        expected_sha256=args.scores_manifest_sha256,
    )
    manifest = core.validate_score_manifest(
        manifest_bytes,
        expected_sha256=args.scores_manifest_sha256,
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
    )
    if (
        manifest["prediction_manifest_sha256"]
        != args.prediction_manifest_sha256
        or manifest["prediction_seal_sha256"]
        != prediction_manifest["prediction_seal_sha256"]
        or manifest["locked_manifest_sha256"]
        != prior_receipt["artifact_manifest_hashes"]["locked_manifest"]
        or manifest["authorization_lock_sha256"]
        != authorization["authorization_lock_sha256"]
        or manifest["authorization_manifest_sha256"]
        != authorization["authorization_manifest_sha256"]
        or manifest["labels_manifest_etag"] != labels_manifest_etag
        or manifest["implementation_commit"] != args.implementation_commit
        or manifest["image_digest"] != args.image_digest
        or manifest["config_sha256"] != args.config_sha256
    ):
        raise core.LockedEvaluationError(
            "score manifest differs from prediction/authorization bindings"
        )
    metadata = manifest.get("payload_members")
    if (
        not isinstance(metadata, list)
        or [item.get("name") for item in metadata if isinstance(item, Mapping)]
        != list(core.SCORE_MEMBER_NAMES[:-1])
    ):
        raise core.LockedEvaluationError("score manifest payload membership is invalid")
    expected_members = {
        f"{args.scores_prefix}/{name}" for name in core.SCORE_MEMBER_NAMES
    }
    if core.list_exact_prefix(
        service, args.container, args.scores_prefix
    ) != expected_members:
        raise core.LockedEvaluationError("score prefix exact membership mismatch")
    payloads: dict[str, bytes] = {}
    for item in metadata:
        data, _ = core.download_verified_blob(
            service,
            args.container,
            f"{args.scores_prefix}/{item['name']}",
            expected_sha256=item["sha256"],
            expected_size=item["size"],
            expected_etag=item["etag"],
        )
        payloads[item["name"]] = data
    scoring_transaction_blob = (
        f"{args.state_prefix}/{core.SCORING_TRANSACTION_FILENAME}"
    )
    transaction_bytes, _ = core.download_verified_blob(
        service,
        args.container,
        scoring_transaction_blob,
        expected_sha256=manifest["scoring_transaction_sha256"],
    )
    scoring_transaction = core.parse_json_strict(
        transaction_bytes, "scoring transaction"
    )
    core.validate_scoring_transaction(
        scoring_transaction, score_payloads=payloads
    )
    if (
        scoring_transaction["authorization_id"] != args.authorization_id
        or scoring_transaction["registered_parent_prefix"]
        != args.parent_prefix
        or scoring_transaction["scores_prefix"] != args.scores_prefix
        or scoring_transaction["labels_open_transaction_sha256"]
        != manifest["labels_open_transaction_sha256"]
        or scoring_transaction["labels_manifest_sha256"]
        != manifest["labels_manifest_sha256"]
        or scoring_transaction["labels_sha256"] != manifest["labels_sha256"]
        or scoring_transaction["scoring_ledger_sha256"]
        != manifest["scoring_ledger_sha256"]
        or not core.exact_json_equal(
            scoring_transaction["scoring_ledger_size"],
            manifest["scoring_ledger_size"],
        )
        or scoring_transaction["scoring_ledger_etag"]
        != manifest["scoring_ledger_etag"]
        or scoring_transaction["prediction_manifest_sha256"]
        != manifest["prediction_manifest_sha256"]
        or scoring_transaction["prediction_seal_sha256"]
        != manifest["prediction_seal_sha256"]
        or scoring_transaction["authorization_lock_sha256"]
        != authorization["authorization_lock_sha256"]
        or scoring_transaction["authorization_manifest_sha256"]
        != authorization["authorization_manifest_sha256"]
        or scoring_transaction["implementation_manifest_sha256"]
        != authorization["implementation_manifest_sha256"]
        or scoring_transaction["implementation_commit"]
        != args.implementation_commit
        or scoring_transaction["image_digest"] != args.image_digest
        or scoring_transaction["config_sha256"] != args.config_sha256
        or scoring_transaction["execution_id"]
        != manifest["scoring_execution_id"]
        or scoring_transaction["actor"] != manifest["scoring_actor"]
        or scoring_transaction["outcome"] != manifest["outcome"]
    ):
        raise core.LockedEvaluationError(
            "scoring transaction differs from authenticated score provenance"
        )
    core.verify_uploaded_blob(
        service,
        args.container,
        manifest_blob,
        manifest_bytes,
        manifest_etag,
    )
    decision = core.parse_json_strict(
        payloads["locked_evaluation_decision.json"], "decision"
    )
    metrics = core.parse_json_strict(
        payloads["locked_evaluation_metrics.json"], "metrics"
    )
    retirement = core.parse_json_strict(
        payloads["retirement_record.json"], "retirement"
    )
    core.validate_metrics_artifact(metrics, gates, require_bindings=True)
    core.validate_decision(metrics, decision)
    core.validate_retirement_record(decision, retirement)
    if payloads["locked_evaluation_metrics.csv"] != core.render_metrics_csv(
        metrics
    ):
        raise core.LockedEvaluationError(
            "persisted metrics CSV is not the deterministic renderer output"
        )
    expected_report = core.render_public_report(metrics, decision, retirement)
    if payloads["locked_evaluation_report.md"] != expected_report:
        raise core.LockedEvaluationError(
            "persisted public report is not the deterministic aggregate renderer"
        )
    failures = core.parse_jsonl_strict(
        payloads["locked_evaluation_failures.jsonl"],
        "locked evaluation failures",
        allow_empty=True,
    )
    failure_ids = [item.get("case_id") for item in failures]
    material_ids = [
        item.get("case_id") for item in failures if item.get("material_error")
    ]
    if (
        not core.exact_json_equal(failure_ids, metrics["mismatch_case_ids"])
        or not core.exact_json_equal(
            material_ids, metrics["material_error_case_ids"]
        )
    ):
        raise core.LockedEvaluationError(
            "persisted failure rows differ from aggregate metrics"
        )
    reservation = core.parse_json_strict(
        payloads[".scores_reservation.json"], "scores reservation"
    )
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
        "scores reservation",
    )
    if (
        not core.exact_json_equal(
            reservation,
            core.build_reservation(
                leaf=reservation["leaf"],
                prefix=reservation["prefix"],
                authorization_id=reservation["authorization_id"],
                created_utc=reservation["created_utc"],
                nonce=reservation["nonce"],
            ),
        )
        or reservation["leaf"] != "scores"
        or reservation["prefix"] != args.scores_prefix
        or reservation["authorization_id"] != args.authorization_id
    ):
        raise core.LockedEvaluationError("scores reservation is not exact")
    labels_transaction = _authenticate_persisted_labels_transaction(
        core,
        service,
        args,
        score_manifest=manifest,
        metrics=metrics,
        decision=decision,
        prediction_manifest=prediction_manifest,
        prior_receipt=prior_receipt,
        authorization=authorization,
        labels_binding=labels_binding,
    )
    ledger_context = _scoring_ledger_context(
        core,
        args,
        authorization=authorization,
        prediction_manifest=prediction_manifest,
        labels_binding=labels_binding,
        labels_manifest_etag=labels_manifest_etag,
        labels_etag=manifest["labels_etag"],
        labels_open_transaction_sha256=core.sha256_bytes(
            core.canonical_json_bytes(labels_transaction)
        ),
        scoring_execution_id=scoring_transaction["execution_id"],
        scoring_actor=scoring_transaction["actor"],
        created_utc=scoring_transaction["created_utc"],
    )
    ledger_validation = core.validate_scoring_ledger_bytes(
        payloads[core.SCORING_LEDGER_FILENAME],
        prediction_artifacts[_CANDIDATE_PREDICTIONS_MEMBER],
        prediction_artifacts[_GATING_COMPARATOR_PREDICTIONS_MEMBER],
        gate_bytes,
        context=ledger_context,
        expected_ordered_case_ids=prediction_manifest["ordered_case_ids"],
    )
    if (
        not core.exact_json_equal(
            ledger_validation["ledger_sha256"],
            manifest["scoring_ledger_sha256"],
        )
        or not core.exact_json_equal(
            ledger_validation["ledger_size"],
            manifest["scoring_ledger_size"],
        )
    ):
        raise core.LockedEvaluationError(
            "persisted scoring ledger differs from the score manifest"
        )
    recomputed_metrics = core.bind_metrics_artifacts(
        ledger_validation["metrics"],
        authorization_id=args.authorization_id,
        registered_parent_prefix=args.parent_prefix,
        authorization_lock_sha256=authorization[
            "authorization_lock_sha256"
        ],
        authorization_manifest_sha256=authorization[
            "authorization_manifest_sha256"
        ],
        implementation_manifest_sha256=authorization[
            "implementation_manifest_sha256"
        ],
        prediction_seal_sha256=prediction_manifest[
            "prediction_seal_sha256"
        ],
        prediction_manifest_sha256=args.prediction_manifest_sha256,
        prediction_request_manifest_sha256=prediction_manifest[
            "prediction_request_manifest_sha256"
        ],
        locked_manifest_sha256=authorization["locked_manifest_sha256"],
        input_manifest_sha256=prediction_manifest[
            "locked_input_manifest_sha256"
        ],
        locked_input_sha256=prediction_manifest["locked_input_sha256"],
        labels_manifest_sha256=labels_binding["manifest_sha256"],
        labels_sha256=labels_binding["payload_sha256"],
        labels_open_transaction_sha256=ledger_context[
            "labels_open_transaction_sha256"
        ],
        scoring_ledger_sha256=ledger_validation["ledger_sha256"],
        scoring_ledger_size=ledger_validation["ledger_size"],
        scoring_ledger_etag=manifest["scoring_ledger_etag"],
        case_universe_sha256=prediction_manifest[
            "case_universe_sha256"
        ],
        row_count=prediction_manifest["row_count"],
        implementation_commit=args.implementation_commit,
        image_digest=args.image_digest,
        config_sha256=args.config_sha256,
    )
    recomputed_payloads, recomputed_decision, recomputed_retirement = (
        core.build_score_payloads(
            recomputed_metrics,
            ledger_validation["failures"],
            authorization_id=args.authorization_id,
            registered_parent_prefix=args.parent_prefix,
            authorization_lock_sha256=authorization[
                "authorization_lock_sha256"
            ],
            authorization_manifest_sha256=authorization[
                "authorization_manifest_sha256"
            ],
            implementation_manifest_sha256=authorization[
                "implementation_manifest_sha256"
            ],
            scores_prefix=args.scores_prefix,
            prediction_seal_sha256=prediction_manifest[
                "prediction_seal_sha256"
            ],
            prediction_manifest_sha256=args.prediction_manifest_sha256,
            prediction_request_manifest_sha256=prediction_manifest[
                "prediction_request_manifest_sha256"
            ],
            locked_manifest_sha256=authorization[
                "locked_manifest_sha256"
            ],
            input_manifest_sha256=prediction_manifest[
                "locked_input_manifest_sha256"
            ],
            locked_input_sha256=prediction_manifest[
                "locked_input_sha256"
            ],
            labels_manifest_sha256=labels_binding["manifest_sha256"],
            labels_sha256=labels_binding["payload_sha256"],
            labels_open_transaction_sha256=ledger_context[
                "labels_open_transaction_sha256"
            ],
            scoring_ledger_bytes=payloads[
                core.SCORING_LEDGER_FILENAME
            ],
            scoring_ledger_sha256=ledger_validation["ledger_sha256"],
            scoring_ledger_size=ledger_validation["ledger_size"],
            scoring_ledger_etag=manifest["scoring_ledger_etag"],
            case_universe_sha256=prediction_manifest[
                "case_universe_sha256"
            ],
            row_count=prediction_manifest["row_count"],
            implementation_commit=args.implementation_commit,
            image_digest=args.image_digest,
            config_sha256=args.config_sha256,
            created_utc=manifest["created_utc"],
            nonce=reservation["nonce"],
        )
    )
    recomputed_payloads[core.SCORE_MEMBER_NAMES[0]] = payloads[
        core.SCORE_MEMBER_NAMES[0]
    ]
    if (
        not core.exact_json_equal(recomputed_metrics, metrics)
        or not core.exact_json_equal(recomputed_decision, decision)
        or not core.exact_json_equal(recomputed_retirement, retirement)
        or any(
            recomputed_payloads[name] != payloads[name]
            for name in core.SCORE_MEMBER_NAMES[:-1]
        )
    ):
        raise core.LockedEvaluationError(
            "persisted score bytes differ from ledger recomputation"
        )
    attestation_blob = (
        f"{args.state_prefix}/{core.SCORING_ATTESTATION_FILENAME}"
    )
    state_members = core.list_exact_prefix(
        service, args.container, args.state_prefix
    )
    attestation_adopted = attestation_blob not in state_members
    if attestation_adopted:
        attestation = core.build_scoring_attestation(
            scoring_transaction,
            score_manifest_bytes=manifest_bytes,
            score_manifest_etag=manifest_etag,
        )
        attestation_persistence = core.persist_singleton(
            service,
            args.container,
            attestation_blob,
            core.canonical_json_bytes(attestation),
        )
    else:
        attestation_bytes, _ = core.download_stable_blob(
            service, args.container, attestation_blob
        )
        attestation = core.parse_json_strict(
            attestation_bytes, "scoring attestation"
        )
        core.validate_scoring_attestation(
            attestation,
            transaction=scoring_transaction,
            score_manifest_bytes=manifest_bytes,
            score_manifest_etag=manifest_etag,
        )
        attestation_persistence = {
            "sha256": core.sha256_bytes(attestation_bytes)
        }
    expected_state_after_attestation = core._authorization_state_members(
        args.state_prefix,
        final_state=authorization["prior_receipt"]["state"],
        retry_kinds=authorization["retry_kinds"],
        labels_transaction=True,
        scoring_transaction=True,
        scoring_attestation=True,
        spent_incomplete=authorization["spent_incomplete"],
        closure_manifest=(
            f"{args.state_prefix}/{core.CLOSURE_MANIFEST_FILENAME}"
            in core.list_exact_prefix(
                service, args.container, args.state_prefix
            )
        ),
    )
    core.validate_registered_parent_membership(
        service,
        args.container,
        args.parent_prefix,
        core.expected_registered_parent_membership(
            args.parent_prefix,
            {
                *{
                    f"{args.predictions_prefix}/{name}"
                    for name in core.PREDICTION_MEMBER_NAMES
                },
                *{
                    f"{args.scores_prefix}/{name}"
                    for name in core.SCORE_MEMBER_NAMES
                },
                *expected_state_after_attestation,
                f"{args.visibility_prefix}/stage_p_visibility.json",
                f"{args.visibility_prefix}/stage_e_visibility.json",
            },
        ),
    )
    if (
        core.sha256_bytes(payloads["locked_evaluation_metrics.json"])
        != manifest["metrics_sha256"]
        or core.sha256_bytes(payloads["locked_evaluation_decision.json"])
        != manifest["decision_sha256"]
        or core.sha256_bytes(payloads["retirement_record.json"])
        != manifest["retirement_sha256"]
        or manifest["outcome"] != decision.get("formal_decision")
        or manifest["metrics_sha256"] != decision.get("metrics_sha256")
        or manifest["prediction_seal_sha256"]
        != decision.get("prediction_seal_sha256")
        or manifest["prediction_manifest_sha256"]
        != decision.get("prediction_manifest_sha256")
        or manifest["locked_manifest_sha256"]
        != decision.get("locked_manifest_sha256")
        or manifest["labels_manifest_sha256"]
        != decision.get("labels_manifest_sha256")
        or manifest["labels_sha256"] != decision.get("labels_sha256")
        or manifest["labels_open_transaction_sha256"]
        != decision.get("labels_open_transaction_sha256")
        or manifest["scoring_ledger_sha256"]
        != decision.get("scoring_ledger_sha256")
        or not core.exact_json_equal(
            manifest["scoring_ledger_size"],
            decision.get("scoring_ledger_size"),
        )
        or manifest["scoring_ledger_etag"]
        != decision.get("scoring_ledger_etag")
        or manifest["authorization_lock_sha256"]
        != decision.get("authorization_lock_sha256")
        or manifest["authorization_manifest_sha256"]
        != decision.get("authorization_manifest_sha256")
        or manifest["implementation_commit"]
        != decision.get("implementation_commit")
        or manifest["image_digest"] != decision.get("image_digest")
        or manifest["config_sha256"] != decision.get("config_sha256")
        or b"PV2-" in payloads["locked_evaluation_report.md"]
    ):
        raise core.LockedEvaluationError(
            "persisted score artifacts do not match the score manifest"
        )
    closed_bytes = None
    recovery_state_bytes_written = False
    closure_adopted = False
    if authorization["prior_receipt"]["state"] == "CLOSED":
        if not args.closed_receipt_sha256:
            raise core.LockedEvaluationError(
                "CLOSED verification requires the CLOSED receipt hash"
            )
        closed_blob = (
            f"{args.state_prefix}/"
            f"{core.STATE_RECEIPT_FILENAMES['CLOSED']}"
        )
        closed_bytes, _ = core.download_verified_blob(
            service,
            args.container,
            closed_blob,
            expected_sha256=args.closed_receipt_sha256,
        )
        closed = core.parse_json_strict(closed_bytes, "CLOSED receipt")
        closure_blob = (
            f"{args.state_prefix}/{core.CLOSURE_MANIFEST_FILENAME}"
        )
        closure_bytes, _ = core.download_verified_blob(
            service,
            args.container,
            closure_blob,
            expected_sha256=closed["artifact_manifest_hashes"][
                "closure_manifest"
            ],
        )
        closure = core.parse_json_strict(closure_bytes, "closure manifest")
        core.validate_closed_outcome(
            closed, metrics, decision, retirement, closure
        )
    else:
        # Recovery may recompute score bytes from the sealed ledger and
        # predictions, but it only persists missing state/attestation objects.
        current = authorization["receipts"][-1]
        closure_blob = (
            f"{args.state_prefix}/{core.CLOSURE_MANIFEST_FILENAME}"
        )
        closure_exists = closure_blob in core.list_exact_prefix(
            service, args.container, args.state_prefix
        )
        if closure_exists and current["state"] != "SCORES_VERIFIED":
            raise core.LockedEvaluationError(
                "persisted closure exists before SCORES_VERIFIED"
            )
        recovery_timestamp = core.max_canonical_utc(
            now(),
            current["timestamp_utc"],
            manifest["created_utc"],
            scoring_transaction["created_utc"],
            attestation["created_utc"],
        )
        if current["state"] == "LABELS_READ":
            scores_receipt = core.build_next_state_receipt(
                current,
                state="SCORES_VERIFIED",
                artifact_manifest_sha256=core.sha256_bytes(manifest_bytes),
                timestamp_utc=recovery_timestamp,
                execution_id=args.execution_id,
                actor=args.actor,
                visibility=["verification-only-recovery"],
                authorization_lock=authorization["authorization_lock"],
                implementation_manifest_bytes=authorization[
                    "implementation_manifest_bytes"
                ],
            )
            core.persist_state_receipt(
                service, args.container, args.state_prefix, scores_receipt
            )
            current = scores_receipt
            core.validate_registered_parent_membership(
                service,
                args.container,
                args.parent_prefix,
                core.expected_registered_parent_membership(
                    args.parent_prefix,
                    {
                        *{
                            f"{args.predictions_prefix}/{name}"
                            for name in core.PREDICTION_MEMBER_NAMES
                        },
                        *{
                            f"{args.scores_prefix}/{name}"
                            for name in core.SCORE_MEMBER_NAMES
                        },
                        *core._authorization_state_members(
                            args.state_prefix,
                            final_state="SCORES_VERIFIED",
                            retry_kinds=authorization["retry_kinds"],
                            labels_transaction=True,
                            scoring_transaction=True,
                            scoring_attestation=True,
                            spent_incomplete=authorization[
                                "spent_incomplete"
                            ],
                        ),
                        f"{args.visibility_prefix}/stage_p_visibility.json",
                        f"{args.visibility_prefix}/stage_e_visibility.json",
                    },
                ),
            )
            recovery_state_bytes_written = True
        if current["state"] != "SCORES_VERIFIED":
            raise core.LockedEvaluationError(
                "verification recovery is not at a closable frozen state"
            )
        closure = core.build_closure_manifest(
            metrics,
            decision,
            retirement,
            scores_manifest_sha256=core.sha256_bytes(manifest_bytes),
            created_utc=manifest["created_utc"],
        )
        closure_bytes = core.canonical_json_bytes(closure)
        if closure_exists:
            persisted_closure_bytes, _ = core.download_stable_blob(
                service, args.container, closure_blob
            )
            if persisted_closure_bytes != closure_bytes:
                raise core.LockedEvaluationError(
                    "persisted closure differs from score transaction"
                )
            closure_persistence = {
                "sha256": core.sha256_bytes(persisted_closure_bytes)
            }
            closure_adopted = True
        else:
            closure_persistence = core.persist_singleton(
                service,
                args.container,
                closure_blob,
                closure_bytes,
            )
            core.validate_registered_parent_membership(
                service,
                args.container,
                args.parent_prefix,
                core.expected_registered_parent_membership(
                    args.parent_prefix,
                    {
                        *{
                            f"{args.predictions_prefix}/{name}"
                            for name in core.PREDICTION_MEMBER_NAMES
                        },
                        *{
                            f"{args.scores_prefix}/{name}"
                            for name in core.SCORE_MEMBER_NAMES
                        },
                        *core._authorization_state_members(
                            args.state_prefix,
                            final_state="SCORES_VERIFIED",
                            retry_kinds=authorization["retry_kinds"],
                            labels_transaction=True,
                            scoring_transaction=True,
                            scoring_attestation=True,
                            spent_incomplete=authorization[
                                "spent_incomplete"
                            ],
                            closure_manifest=True,
                        ),
                        f"{args.visibility_prefix}/stage_p_visibility.json",
                        f"{args.visibility_prefix}/stage_e_visibility.json",
                    },
                ),
            )
        closed = core.build_next_state_receipt(
            current,
            state="CLOSED",
            artifact_manifest_sha256=closure_persistence["sha256"],
            timestamp_utc=recovery_timestamp,
            execution_id=args.execution_id,
            actor=args.actor,
            visibility=["verification-only-recovery"],
            outcome=decision["formal_decision"],
            authorization_lock=authorization["authorization_lock"],
            implementation_manifest_bytes=authorization[
                "implementation_manifest_bytes"
            ],
        )
        closed_persistence = core.persist_state_receipt(
            service, args.container, args.state_prefix, closed
        )
        closed_bytes = core.canonical_json_bytes(closed)
        if closed_persistence["sha256"] != core.sha256_bytes(closed_bytes):
            raise core.LockedEvaluationError(
                "verification recovery CLOSED receipt mismatch"
            )
        core.validate_closed_outcome(
            closed, metrics, decision, retirement, closure
        )
        core.validate_authorization_membership(
            service,
            args.container,
            parent_prefix=args.parent_prefix,
            authorization_id=args.authorization_id,
            expected={
                "predictions": {
                    f"{args.predictions_prefix}/{name}"
                    for name in core.PREDICTION_MEMBER_NAMES
                },
                "scores": {
                    f"{args.scores_prefix}/{name}"
                    for name in core.SCORE_MEMBER_NAMES
                },
                "state": core._authorization_state_members(
                    args.state_prefix,
                    final_state="CLOSED",
                    retry_kinds=authorization["retry_kinds"],
                    labels_transaction=True,
                    scoring_transaction=True,
                    scoring_attestation=True,
                    spent_incomplete=authorization["spent_incomplete"],
                    closure_manifest=True,
                ),
                "visibility": {
                    f"{args.visibility_prefix}/stage_p_visibility.json",
                    f"{args.visibility_prefix}/stage_e_visibility.json",
                },
            },
        )
        recovery_final_members = {
            *{
                f"{args.predictions_prefix}/{name}"
                for name in core.PREDICTION_MEMBER_NAMES
            },
            *{
                f"{args.scores_prefix}/{name}"
                for name in core.SCORE_MEMBER_NAMES
            },
            *core._authorization_state_members(
                args.state_prefix,
                final_state="CLOSED",
                retry_kinds=authorization["retry_kinds"],
                labels_transaction=True,
                scoring_transaction=True,
                scoring_attestation=True,
                spent_incomplete=authorization["spent_incomplete"],
                closure_manifest=True,
            ),
            f"{args.visibility_prefix}/stage_p_visibility.json",
            f"{args.visibility_prefix}/stage_e_visibility.json",
        }
        core.validate_registered_parent_membership(
            service,
            args.container,
            args.parent_prefix,
            core.expected_registered_parent_membership(
                args.parent_prefix, recovery_final_members
            ),
        )
        recovery_state_bytes_written = True
    return {
        "stage": "E",
        "mode": "verification_only",
        "verification_state": args.verification_state,
        "authenticated_predecessor_state": authorization[
            "prior_receipt"
        ]["state"],
        "status": decision["formal_decision"],
        "scores_manifest_sha256": core.sha256_bytes(manifest_bytes),
        "scoring_ledger_sha256": ledger_validation["ledger_sha256"],
        "scoring_ledger_size": ledger_validation["ledger_size"],
        "scoring_ledger_etag": manifest["scoring_ledger_etag"],
        "closed_receipt_sha256": (
            None if closed_bytes is None else core.sha256_bytes(closed_bytes)
        ),
        "label_payload_downloaded": False,
        "metrics_recomputed": True,
        "bytes_modified": (
            attestation_adopted or recovery_state_bytes_written
        ),
        "evaluation_artifact_bytes_modified": False,
        "recovery_receipt_present": args.verification_state != "CLOSED",
        "recovery_state_bytes_written": recovery_state_bytes_written,
        "closure_adopted": closure_adopted,
        "scoring_attestation_adopted": attestation_adopted,
        "scoring_attestation_sha256": attestation_persistence["sha256"],
    }


def _verify_score_prefix(
    core: ModuleType,
    service: Any,
    args: argparse.Namespace,
    prediction_manifest: Mapping[str, Any],
    prediction_receipt: Mapping[str, Any],
    prediction_context: Mapping[str, Any],
    authorization: dict[str, Any],
    gates: Mapping[str, Any],
    now: Callable[[], str],
) -> dict[str, Any]:
    if not args.scores_manifest_sha256:
        raise core.LockedEvaluationError(
            "verification-only mode requires the persisted score-manifest hash"
        )
    transaction_blob = (
        f"{args.state_prefix}/{core.SCORING_TRANSACTION_FILENAME}"
    )
    transaction_bytes, _ = core.download_stable_blob(
        service, args.container, transaction_blob
    )
    scoring_transaction = core.parse_json_strict(
        transaction_bytes, "scoring transaction"
    )
    core.validate_scoring_transaction(scoring_transaction)
    prior_scores_prefix = scoring_transaction["scores_prefix"]
    if (
        args.scores_prefix != prior_scores_prefix
        or scoring_transaction["authorization_id"]
        != args.authorization_id
        or scoring_transaction["registered_parent_prefix"]
        != args.parent_prefix
        or scoring_transaction["state_prefix"] != args.state_prefix
    ):
        raise core.LockedEvaluationError(
            "verification scores prefix differs from the sealed scoring attempt"
        )

    manifest_blob = (
        f"{prior_scores_prefix}/{core.SCORE_MEMBER_NAMES[-1]}"
    )
    manifest_bytes, manifest_etag = core.download_verified_blob(
        service,
        args.container,
        manifest_blob,
        expected_sha256=args.scores_manifest_sha256,
    )
    manifest = core.validate_score_manifest(
        manifest_bytes,
        expected_sha256=args.scores_manifest_sha256,
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
    )
    if (
        manifest["scores_prefix"] != prior_scores_prefix
        or manifest["scoring_transaction_sha256"]
        != core.sha256_bytes(transaction_bytes)
        or manifest["prediction_manifest_sha256"]
        != args.prediction_manifest_sha256
        or manifest["prediction_seal_sha256"]
        != prediction_manifest["prediction_seal_sha256"]
        or manifest["locked_manifest_sha256"]
        != prediction_receipt["artifact_manifest_hashes"][
            "locked_manifest"
        ]
        or manifest["authorization_lock_sha256"]
        != authorization["authorization_lock_sha256"]
        or manifest["authorization_manifest_sha256"]
        != authorization["authorization_manifest_sha256"]
        or manifest["implementation_manifest_sha256"]
        != authorization["implementation_manifest_sha256"]
        or manifest["implementation_commit"] != args.implementation_commit
        or manifest["image_digest"] != args.image_digest
        or manifest["config_sha256"] != args.config_sha256
    ):
        raise core.LockedEvaluationError(
            "score manifest differs from authenticated scoring provenance"
        )

    score_members = {
        f"{prior_scores_prefix}/{name}" for name in core.SCORE_MEMBER_NAMES
    }
    if core.list_exact_prefix(
        service, args.container, prior_scores_prefix
    ) != score_members:
        raise core.LockedEvaluationError(
            "verification score-prefix membership is not exact"
        )
    _, all_score_payloads = _stable_attempt_members(
        core, service, args.container, score_members
    )
    payloads = {
        name: all_score_payloads[f"{prior_scores_prefix}/{name}"]
        for name in core.SCORE_MEMBER_NAMES[:-1]
    }
    core.validate_scoring_transaction(
        scoring_transaction, score_payloads=payloads
    )

    labels_transaction_blob = (
        f"{args.state_prefix}/{core.LABELS_OPEN_TRANSACTION_FILENAME}"
    )
    labels_transaction_bytes, _ = core.download_verified_blob(
        service,
        args.container,
        labels_transaction_blob,
        expected_sha256=scoring_transaction[
            "labels_open_transaction_sha256"
        ],
    )
    labels_transaction = core.parse_json_strict(
        labels_transaction_bytes, "labels-open transaction"
    )
    core.validate_labels_open_transaction(
        labels_transaction,
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
    )
    common_transaction_fields = (
        "authorization_id",
        "registered_parent_prefix",
        "state_prefix",
        "scores_prefix",
        "scoring_retry_kind",
        "retry_receipt_sha256",
        "authorization_lock_sha256",
        "authorization_manifest_sha256",
        "implementation_manifest_sha256",
        "prediction_manifest_sha256",
        "prediction_seal_sha256",
        "prediction_request_manifest_sha256",
        "input_manifest_sha256",
        "locked_manifest_sha256",
        "labels_manifest_sha256",
        "labels_sha256",
        "case_universe_sha256",
        "row_count",
        "acceptance_gates_sha256",
        "implementation_commit",
        "image_digest",
        "config_sha256",
        "execution_id",
        "actor",
        "created_utc",
    )
    if (
        any(
            not core.exact_json_equal(
                labels_transaction[field],
                scoring_transaction[field],
            )
            for field in common_transaction_fields
        )
        or
        labels_transaction["scores_prefix"] != prior_scores_prefix
        or labels_transaction["scoring_retry_kind"]
        != scoring_transaction["scoring_retry_kind"]
        or labels_transaction["retry_receipt_sha256"]
        != scoring_transaction["retry_receipt_sha256"]
        or labels_transaction["execution_id"]
        != scoring_transaction["execution_id"]
        or labels_transaction["actor"] != scoring_transaction["actor"]
        or labels_transaction["visibility_sha256"]
        != scoring_transaction["stage_e_visibility_sha256"]
        or labels_transaction["labels_manifest_sha256"]
        != scoring_transaction["labels_manifest_sha256"]
        or labels_transaction["labels_sha256"]
        != scoring_transaction["labels_sha256"]
        or labels_transaction["labels_manifest_blob_name"]
        != args.labels_manifest_blob
        or labels_transaction["labels_blob_name"] != args.labels_blob
        or labels_transaction["labels_manifest_sha256"]
        != args.labels_manifest_sha256
        or labels_transaction["labels_sha256"] != args.labels_sha256
        or labels_transaction["prediction_manifest_sha256"]
        != args.prediction_manifest_sha256
        or labels_transaction["labels_manifest_etag"]
        != manifest["labels_manifest_etag"]
        or labels_transaction["labels_manifest_blob_name"]
        != manifest["labels_manifest_blob_name"]
        or labels_transaction["labels_blob_name"]
        != manifest["labels_blob_name"]
        or labels_transaction["visibility_etag"]
        != manifest["stage_e_visibility_etag"]
        or core.sha256_bytes(labels_transaction_bytes)
        != manifest["labels_open_transaction_sha256"]
    ):
        raise core.LockedEvaluationError(
            "labels-open transaction differs from its scoring attempt"
        )
    if (
        scoring_transaction["scoring_retry_kind"] == "none"
        and labels_transaction["prior_receipt_sha256"]
        != core.state_receipt_sha256(prediction_receipt)
    ):
        raise core.LockedEvaluationError(
            "primary labels-open transaction predecessor differs"
        )

    attestation_blob = (
        f"{args.state_prefix}/{core.SCORING_ATTESTATION_FILENAME}"
    )
    attestation_bytes, _ = core.download_stable_blob(
        service, args.container, attestation_blob
    )
    attestation = core.parse_json_strict(
        attestation_bytes, "scoring attestation"
    )
    core.validate_scoring_attestation(
        attestation,
        transaction=scoring_transaction,
        score_manifest_bytes=manifest_bytes,
        score_manifest_etag=manifest_etag,
    )
    if (
        attestation["score_manifest_sha256"]
        != args.scores_manifest_sha256
        or attestation["score_manifest_blob_name"] != manifest_blob
        or attestation["scores_prefix"] != prior_scores_prefix
    ):
        raise core.LockedEvaluationError(
            "scoring attestation does not identify the sealed score attempt"
        )

    sealed_attempt = _load_sealed_scoring_attempt(
        core,
        service,
        args,
        scoring_transaction=scoring_transaction,
        labels_transaction=labels_transaction,
        score_manifest=manifest,
        prediction_receipt=prediction_receipt,
        authorization=authorization,
    )
    payloads = sealed_attempt["score_payloads"]
    metrics = core.parse_json_strict(
        payloads["locked_evaluation_metrics.json"], "metrics"
    )
    decision = core.parse_json_strict(
        payloads["locked_evaluation_decision.json"], "decision"
    )
    retirement = core.parse_json_strict(
        payloads["retirement_record.json"], "retirement"
    )
    core.validate_metrics_artifact(metrics, gates, require_bindings=True)
    core.validate_decision(metrics, decision)
    core.validate_retirement_record(decision, retirement)
    if (
        payloads["locked_evaluation_metrics.csv"]
        != core.render_metrics_csv(metrics)
        or payloads["locked_evaluation_report.md"]
        != core.render_public_report(metrics, decision, retirement)
        or core.sha256_bytes(payloads["locked_evaluation_metrics.json"])
        != manifest["metrics_sha256"]
        or core.sha256_bytes(payloads["locked_evaluation_decision.json"])
        != manifest["decision_sha256"]
        or core.sha256_bytes(payloads["retirement_record.json"])
        != manifest["retirement_sha256"]
        or core.sha256_bytes(payloads[core.SCORING_LEDGER_FILENAME])
        != manifest["scoring_ledger_sha256"]
        or len(payloads[core.SCORING_LEDGER_FILENAME])
        != manifest["scoring_ledger_size"]
        or any(
            not core.exact_json_equal(
                manifest[field],
                scoring_transaction[
                    "execution_id"
                    if field == "scoring_execution_id"
                    else "actor"
                    if field == "scoring_actor"
                    else field
                ],
            )
            for field in (
                "scores_prefix",
                "scoring_retry_kind",
                "retry_receipt_sha256",
                "stage_e_visibility_sha256",
                "scoring_execution_id",
                "scoring_actor",
                "scoring_ledger_sha256",
                "scoring_ledger_size",
                "scoring_ledger_etag",
                "labels_open_transaction_sha256",
                "outcome",
            )
        )
    ):
        raise core.LockedEvaluationError(
            "persisted score artifacts differ from sealed provenance"
        )
    reservation = _validate_score_reservation(
        core,
        payloads[core.SCORE_MEMBER_NAMES[0]],
        args,
        prefix=prior_scores_prefix,
        retry_kind=scoring_transaction["scoring_retry_kind"],
        execution_id=scoring_transaction["execution_id"],
    )
    del reservation
    failures = core.parse_jsonl_strict(
        payloads["locked_evaluation_failures.jsonl"],
        "locked evaluation failures",
        allow_empty=True,
    )
    if (
        [item.get("case_id") for item in failures]
        != metrics["mismatch_case_ids"]
        or [
            item.get("case_id")
            for item in failures
            if item.get("material_error")
        ]
        != metrics["material_error_case_ids"]
    ):
        raise core.LockedEvaluationError(
            "persisted failure rows differ from aggregate metrics"
        )

    prior_manifest_sha256 = core.sha256_bytes(manifest_bytes)
    prior_labels_open_sha256 = core.sha256_bytes(
        labels_transaction_bytes
    )
    prior_attestation_sha256 = core.sha256_bytes(attestation_bytes)
    existing_retry = _retry_receipt_for_attempt(
        core, authorization, "verification_only"
    )
    visibility_blob = (
        f"{args.visibility_prefix}/stage_e_visibility.json"
    )
    preclaim_visibility_members = core.list_exact_prefix(
        service, args.container, args.visibility_prefix
    )
    if preclaim_visibility_members not in (set(), {visibility_blob}):
        raise core.LockedEvaluationError(
            "verification visibility attempt membership is not exact"
        )
    if existing_retry is None and preclaim_visibility_members:
        raise core.LockedEvaluationError(
            "verification visibility exists without its singleton retry claim"
        )
    if existing_retry is None:
        retry_created = True
        retry_predecessor = authorization["prior_receipt"]
        retry_receipt = core.build_provenance_bound_retry_state_receipt(
            retry_predecessor,
            retry_kind="verification_only",
            timestamp_utc=core.max_canonical_utc(
                now(),
                retry_predecessor["timestamp_utc"],
                manifest["created_utc"],
                scoring_transaction["created_utc"],
                attestation["created_utc"],
            ),
            execution_id=args.execution_id,
            actor=args.actor,
            history=authorization["receipts"],
            authorization_lock=authorization["authorization_lock"],
            implementation_manifest_bytes=authorization[
                "implementation_manifest_bytes"
            ],
            prior_score_manifest_sha256=prior_manifest_sha256,
            prior_labels_open_transaction_sha256=(
                prior_labels_open_sha256
            ),
            prior_scoring_attestation_sha256=prior_attestation_sha256,
        )
        retry_persistence = core.persist_state_receipt(
            service,
            args.container,
            args.state_prefix,
            retry_receipt,
        )
        authorization["receipts"].append(retry_receipt)
        authorization["retry_kinds"].append("verification_only")
        current = retry_receipt
    else:
        retry_created = False
        predecessor = next(
            (
                receipt
                for receipt in authorization["receipts"]
                if core.state_receipt_sha256(receipt)
                == existing_retry["previous_receipt_sha256"]
            ),
            None,
        )
        if (
            predecessor is None
            or existing_retry["execution_id"] != args.execution_id
            or existing_retry["actor"] != args.actor
        ):
            raise core.LockedEvaluationError(
                "verification-only retry was claimed by another execution"
            )
        core.validate_retry_state_receipt_provenance(
            existing_retry,
            previous=predecessor,
            prior_score_manifest_sha256=prior_manifest_sha256,
            prior_labels_open_transaction_sha256=(
                prior_labels_open_sha256
            ),
            prior_scoring_attestation_sha256=prior_attestation_sha256,
        )
        retry_blob = core.state_receipt_blob_name(
            args.state_prefix, existing_retry
        )
        retry_bytes, retry_etag = core.download_stable_blob(
            service, args.container, retry_blob
        )
        if retry_bytes != core.canonical_json_bytes(existing_retry):
            raise core.LockedEvaluationError(
                "persisted verification retry receipt differs"
            )
        retry_receipt = existing_retry
        retry_persistence = {
            "blob_name": retry_blob,
            "size": len(retry_bytes),
            "sha256": core.sha256_bytes(retry_bytes),
            "etag": retry_etag,
        }
        current = authorization["prior_receipt"]
        current_state_index = core.HOLDOUT_STATE_SEQUENCE.index(
            current["state"]
        )
        retry_state_index = core.HOLDOUT_STATE_SEQUENCE.index(
            retry_receipt["state"]
        )
        if (
            current_state_index < retry_state_index
            or (
                current_state_index == retry_state_index
                and current["retry_kind"] == "none"
            )
        ):
            current = retry_receipt

    visibility_members = core.list_exact_prefix(
        service, args.container, args.visibility_prefix
    )
    if visibility_members not in (set(), {visibility_blob}):
        raise core.LockedEvaluationError(
            "verification visibility attempt membership is not exact"
        )
    if visibility_blob in visibility_members:
        visibility_created = False
        visibility_bytes, visibility_etag = core.download_stable_blob(
            service, args.container, visibility_blob
        )
        verification_visibility = core.parse_json_strict(
            visibility_bytes, "verification-only Stage-E visibility"
        )
        core.validate_visibility_record(
            verification_visibility,
            expected_stage="E",
            expected_authorization_id=args.authorization_id,
            expected_parent_prefix=args.parent_prefix,
            expected_retry_kind="verification_only",
            expected_execution_id=args.execution_id,
        )
        if (
            visibility_bytes
            != core.canonical_json_bytes(verification_visibility)
            or verification_visibility["actor"] != args.actor
        ):
            raise core.LockedEvaluationError(
                "verification visibility identity differs"
            )
        visibility_persistence = {
            "blob_name": visibility_blob,
            "size": len(visibility_bytes),
            "sha256": core.sha256_bytes(visibility_bytes),
            "etag": visibility_etag,
        }
    else:
        visibility_created = True
        verification_visibility = core.build_visibility_record(
            stage="E",
            authorization_id=args.authorization_id,
            parent_prefix=args.parent_prefix,
            visibility_prefix=args.visibility_prefix,
            execution_id=args.execution_id,
            actor=args.actor,
            created_utc=core.max_canonical_utc(
                now(),
                retry_receipt["timestamp_utc"],
                manifest["created_utc"],
                scoring_transaction["created_utc"],
                attestation["created_utc"],
            ),
            retry_kind="verification_only",
        )
        visibility_bytes = core.canonical_json_bytes(
            verification_visibility
        )
        visibility_persistence = core.persist_singleton(
            service,
            args.container,
            visibility_blob,
            visibility_bytes,
        )
    verification_visibility_metadata = [visibility_persistence]
    prediction_members = {
        f"{args.predictions_prefix}/{name}"
        for name in core.PREDICTION_MEMBER_NAMES
    }

    def validate_membership(
        state: str, *, closure_manifest: bool
    ) -> dict[str, set[str]]:
        state_members = core._authorization_state_members(
            args.state_prefix,
            final_state=state,
            retry_kinds=authorization["retry_kinds"],
            labels_transaction=True,
            scoring_transaction=True,
            scoring_attestation=True,
            spent_incomplete=authorization["spent_incomplete"],
            closure_manifest=closure_manifest,
        )
        return _validate_verification_membership(
            core,
            service,
            args,
            prediction_members=prediction_members,
            prediction_context=prediction_context,
            state_members=state_members,
            sealed_attempt=sealed_attempt,
            verification_visibility_metadata=(
                verification_visibility_metadata
            ),
        )

    closure_blob = (
        f"{args.state_prefix}/{core.CLOSURE_MANIFEST_FILENAME}"
    )
    closure_exists = closure_blob in core.list_exact_prefix(
        service, args.container, args.state_prefix
    )
    if closure_exists and current["state"] == "LABELS_READ":
        raise core.LockedEvaluationError(
            "persisted closure exists before SCORES_VERIFIED"
        )
    validate_membership(
        current["state"],
        closure_manifest=closure_exists,
    )
    recovery_state_bytes_written = False
    recovery_timestamp = core.max_canonical_utc(
        now(),
        current["timestamp_utc"],
        retry_receipt["timestamp_utc"],
        verification_visibility["created_utc"],
        manifest["created_utc"],
        scoring_transaction["created_utc"],
        attestation["created_utc"],
    )
    if current["state"] == "LABELS_READ":
        scores_receipt = core.build_next_state_receipt(
            current,
            state="SCORES_VERIFIED",
            artifact_manifest_sha256=prior_manifest_sha256,
            timestamp_utc=recovery_timestamp,
            execution_id=args.execution_id,
            actor=args.actor,
            visibility=[
                *verification_visibility["artifact_classes"],
                f"record_sha256:{visibility_persistence['sha256']}",
            ],
            authorization_lock=authorization["authorization_lock"],
            implementation_manifest_bytes=authorization[
                "implementation_manifest_bytes"
            ],
        )
        core.persist_state_receipt(
            service, args.container, args.state_prefix, scores_receipt
        )
        current = scores_receipt
        recovery_state_bytes_written = True
        validate_membership("SCORES_VERIFIED", closure_manifest=False)
    if current["state"] not in {"SCORES_VERIFIED", "CLOSED"}:
        raise core.LockedEvaluationError(
            "verification recovery is not at a closable state"
        )

    closure_adopted = False
    if closure_exists:
        closure_bytes, _ = core.download_stable_blob(
            service, args.container, closure_blob
        )
        closure = core.parse_json_strict(
            closure_bytes, "closure manifest"
        )
        expected_closure = core.build_closure_manifest(
            metrics,
            decision,
            retirement,
            scores_manifest_sha256=prior_manifest_sha256,
            created_utc=closure["created_utc"],
        )
        if (
            closure_bytes != core.canonical_json_bytes(closure)
            or not core.exact_json_equal(closure, expected_closure)
        ):
            raise core.LockedEvaluationError(
                "persisted closure differs from sealed scores"
            )
        closure_persistence = {
            "sha256": core.sha256_bytes(closure_bytes)
        }
        closure_adopted = True
    else:
        if current["state"] == "CLOSED":
            raise core.LockedEvaluationError(
                "CLOSED state omits its closure manifest"
            )
        closure = core.build_closure_manifest(
            metrics,
            decision,
            retirement,
            scores_manifest_sha256=prior_manifest_sha256,
            created_utc=recovery_timestamp,
        )
        closure_bytes = core.canonical_json_bytes(closure)
        closure_persistence = core.persist_singleton(
            service,
            args.container,
            closure_blob,
            closure_bytes,
        )
        recovery_state_bytes_written = True
        closure_exists = True
        validate_membership("SCORES_VERIFIED", closure_manifest=True)

    if current["state"] == "SCORES_VERIFIED":
        closed_timestamp = core.max_canonical_utc(
            now(),
            current["timestamp_utc"],
            recovery_timestamp,
            closure["created_utc"],
        )
        closed = core.build_next_state_receipt(
            current,
            state="CLOSED",
            artifact_manifest_sha256=closure_persistence["sha256"],
            timestamp_utc=closed_timestamp,
            execution_id=args.execution_id,
            actor=args.actor,
            visibility=[
                *verification_visibility["artifact_classes"],
                f"record_sha256:{visibility_persistence['sha256']}",
            ],
            outcome=decision["formal_decision"],
            authorization_lock=authorization["authorization_lock"],
            implementation_manifest_bytes=authorization[
                "implementation_manifest_bytes"
            ],
        )
        closed_persistence = core.persist_state_receipt(
            service, args.container, args.state_prefix, closed
        )
        current = closed
        recovery_state_bytes_written = True
    else:
        closed = next(
            (
                receipt
                for receipt in authorization["receipts"]
                if receipt["state"] == "CLOSED"
                and receipt["retry_kind"] == "none"
            ),
            None,
        )
        if closed is None:
            raise core.LockedEvaluationError(
                "verification retry does not retain the sealed CLOSED receipt"
            )
        closed_persistence = {
            "sha256": core.state_receipt_sha256(closed)
        }
    if args.closed_receipt_sha256 is not None and (
        closed_persistence["sha256"] != args.closed_receipt_sha256
    ):
        raise core.LockedEvaluationError(
            "CLOSED receipt hash differs from the verification argument"
        )
    core.validate_closed_outcome(
        closed, metrics, decision, retirement, closure
    )
    validate_membership("CLOSED", closure_manifest=True)
    return {
        "stage": "E",
        "mode": "verification_only",
        "verification_state": args.verification_state,
        "authenticated_predecessor_state": retry_receipt["state"],
        "status": decision["formal_decision"],
        "scores_prefix": prior_scores_prefix,
        "scores_manifest_sha256": prior_manifest_sha256,
        "scoring_ledger_sha256": manifest["scoring_ledger_sha256"],
        "scoring_ledger_size": manifest["scoring_ledger_size"],
        "scoring_ledger_etag": manifest["scoring_ledger_etag"],
        "closed_receipt_sha256": closed_persistence["sha256"],
        "verification_retry_receipt_sha256": retry_persistence["sha256"],
        "verification_visibility_sha256": visibility_persistence["sha256"],
        "label_payload_downloaded": False,
        "parsers_invoked": False,
        "metrics_recomputed": False,
        "bytes_modified": (
            retry_created
            or visibility_created
            or recovery_state_bytes_written
        ),
        "evaluation_artifact_bytes_modified": False,
        "recovery_receipt_present": True,
        "recovery_state_bytes_written": recovery_state_bytes_written,
        "closure_adopted": closure_adopted,
        "scoring_attestation_adopted": False,
        "scoring_attestation_sha256": prior_attestation_sha256,
    }


def persist_transaction_then_read_labels(
    core: ModuleType,
    service: Any,
    *,
    container: str,
    state_prefix: str,
    transaction: Mapping[str, Any],
    labels_blob: str,
    labels_sha256: str,
    labels_size: int,
    parent_prefix: str | None = None,
    registered_parent_members_after_transaction: set[str] | None = None,
) -> tuple[dict[str, Any], bytes, str]:
    """Persist/re-verify the singleton transaction before creating the label client."""
    transaction_persistence = core.persist_labels_open_transaction(
        service,
        container,
        state_prefix,
        transaction,
    )
    if (
        parent_prefix is not None
        or registered_parent_members_after_transaction is not None
    ):
        if (
            parent_prefix is None
            or registered_parent_members_after_transaction is None
        ):
            raise core.LockedEvaluationError(
                "labels-open parent verification is incomplete"
            )
        core.validate_registered_parent_membership(
            service,
            container,
            parent_prefix,
            registered_parent_members_after_transaction,
        )
    labels_bytes, labels_etag = core.download_verified_blob(
        service,
        container,
        labels_blob,
        expected_sha256=labels_sha256,
        expected_size=labels_size,
    )
    return transaction_persistence, labels_bytes, labels_etag


def _run_stage_e(
    args: argparse.Namespace,
    *,
    service: Any | None = None,
    core: ModuleType | None = None,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    active_core = core or _load_core()
    if service is None:
        active_core.validate_stage_e_environment(os.environ)
        active_core.validate_no_model_gpu_configuration(os.environ)
    if args.verify_only:
        if (
            args.retry_kind != "verification_only"
            or args.scores_manifest_sha256 is None
            or (
                args.verification_state != "CLOSED"
                and args.closed_receipt_sha256 is not None
            )
        ):
            raise active_core.LockedEvaluationError(
                "Stage E verification arguments are not exact"
            )
    elif (
        args.retry_kind not in {"none", "scorer_infrastructure"}
        or args.verification_state != "CLOSED"
        or args.scores_manifest_sha256 is not None
        or args.closed_receipt_sha256 is not None
    ):
        raise active_core.LockedEvaluationError(
            "Stage E finalization arguments are not exact"
        )
    active_core.compute_protocol_bundle_sha256(PROJECT_ROOT)
    gate_bytes = active_core.load_frozen_gate_bytes(PROJECT_ROOT)
    gates = active_core.load_acceptance_gates(gate_bytes)
    prefixes = active_core.evaluation_prefixes(
        args.parent_prefix, args.authorization_id
    )
    active_core.validate_exact_evaluation_prefix(
        args.state_prefix,
        args.parent_prefix,
        args.authorization_id,
        "state",
    )
    if args.retry_kind == "none":
        for leaf in ("scores", "visibility"):
            active_core.validate_exact_attempt_prefix(
                getattr(args, f"{leaf}_prefix"),
                args.parent_prefix,
                args.authorization_id,
                leaf,
                "E",
                "none",
                args.execution_id,
            )
    elif args.retry_kind == "scorer_infrastructure":
        for leaf in ("scores", "visibility"):
            active_core.validate_exact_attempt_prefix(
                getattr(args, f"{leaf}_prefix"),
                args.parent_prefix,
                args.authorization_id,
                leaf,
                "E",
                args.retry_kind,
                args.execution_id,
            )
    else:
        active_core.normalize_blob_prefix(args.scores_prefix)
        active_core.validate_exact_attempt_prefix(
            args.visibility_prefix,
            args.parent_prefix,
            args.authorization_id,
            "visibility",
            "E",
            "verification_only",
            args.execution_id,
        )
    _assert_exact_source_names(
        active_core,
        parent_prefix=args.parent_prefix,
        labels_blob=args.labels_blob,
        labels_manifest_blob=args.labels_manifest_blob,
    )
    if service is None:
        active_core.validate_private_endpoint_resolution(
            args.account_url, args.expected_private_endpoint_ip
        )
    active_service = service or active_core.create_blob_service(args.account_url)
    actual_state_members = active_core.list_exact_prefix(
        active_service, args.container, args.state_prefix
    )
    authorization_target = (
        args.verification_state
        if args.verify_only
        else "PREDICTIONS_VERIFIED"
    )
    if args.verify_only and args.verification_state == "CLOSED":
        for candidate in ("CLOSED", "SCORES_VERIFIED", "LABELS_READ"):
            candidate_blob = (
                f"{args.state_prefix}/"
                f"{active_core.STATE_RECEIPT_FILENAMES[candidate]}"
            )
            if candidate_blob in actual_state_members:
                authorization_target = candidate
                break
    closure_blob = (
        f"{args.state_prefix}/{active_core.CLOSURE_MANIFEST_FILENAME}"
    )
    closure_present = closure_blob in actual_state_members
    spent_incomplete_present = (
        f"{args.state_prefix}/{active_core.SPENT_INCOMPLETE_FILENAME}"
        in actual_state_members
    )
    scoring_incomplete_present = (
        f"{args.state_prefix}/{active_core.SCORING_INCOMPLETE_FILENAME}"
        in actual_state_members
    )
    invalid_closure_present = (
        f"{args.state_prefix}/{active_core.INVALID_CLOSURE_FILENAME}"
        in actual_state_members
    )
    labels_transaction_present = (
        f"{args.state_prefix}/{active_core.LABELS_OPEN_TRANSACTION_FILENAME}"
        in actual_state_members
    )
    scoring_transaction_blob = (
        f"{args.state_prefix}/{active_core.SCORING_TRANSACTION_FILENAME}"
    )
    scoring_attestation_blob = (
        f"{args.state_prefix}/{active_core.SCORING_ATTESTATION_FILENAME}"
    )
    scoring_transaction_present = (
        scoring_transaction_blob in actual_state_members
    )
    scoring_attestation_present = (
        scoring_attestation_blob in actual_state_members
    )
    scorer_retry_present = (
        f"{args.state_prefix}/"
        f"{active_core.STATE_RETRY_RECEIPT_FILENAMES['scorer_infrastructure']}"
        in actual_state_members
    )
    if invalid_closure_present:
        return _close_invalid_open_attempt(
            active_core, active_service, args
        )
    if scoring_incomplete_present:
        raise active_core.LockedEvaluationError(
            "legacy scoring-incomplete evidence cannot replace CLOSED"
        )
    if labels_transaction_present:
        labels_transaction_bytes, _ = active_core.download_stable_blob(
            active_service,
            args.container,
            (
                f"{args.state_prefix}/"
                f"{active_core.LABELS_OPEN_TRANSACTION_FILENAME}"
            ),
        )
        existing_labels_transaction = active_core.parse_json_strict(
            labels_transaction_bytes, "existing labels-open transaction"
        )
        active_core.validate_labels_open_transaction(
            existing_labels_transaction,
            expected_authorization_id=args.authorization_id,
            expected_parent_prefix=args.parent_prefix,
        )
        existing_score_members = active_core.list_exact_prefix(
            active_service,
            args.container,
            existing_labels_transaction["scores_prefix"],
        )
        sealed_score_members = {
            (
                f"{existing_labels_transaction['scores_prefix']}/"
                f"{name}"
            )
            for name in active_core.SCORE_MEMBER_NAMES
        }
        if (
            not scoring_transaction_present
            or not scoring_attestation_present
            or existing_score_members != sealed_score_members
        ):
            return _close_invalid_open_attempt(
                active_core, active_service, args
            )
    if args.verify_only and (
        not labels_transaction_present
        or not scoring_transaction_present
        or not scoring_attestation_present
    ):
        raise active_core.LockedEvaluationError(
            "verification-only recovery requires sealed scoring provenance"
        )
    if not args.verify_only:
        forbidden_state = {
            f"{args.state_prefix}/{active_core.STATE_RECEIPT_FILENAMES[state]}"
            for state in ("LABELS_READ", "SCORES_VERIFIED", "CLOSED")
        } | {
            f"{args.state_prefix}/{active_core.LABELS_OPEN_TRANSACTION_FILENAME}",
            scoring_transaction_blob,
            scoring_attestation_blob,
            closure_blob,
        }
        if actual_state_members & forbidden_state:
            raise active_core.LockedEvaluationError(
                "existing labels-open or scoring provenance requires verification-only"
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
        expected_prior_receipt_sha256=(
            None
            if args.verify_only or scorer_retry_present
            else args.prior_state_receipt_sha256
        ),
        expected_authorization_lock_sha256=args.authorization_lock_sha256,
        expected_authorization_manifest_sha256=(
            args.authorization_manifest_sha256
        ),
        expected_image_binding_sha256=args.image_binding_sha256,
        expected_helper_snapshot_set_sha256=args.helper_snapshot_set_sha256,
        final_state=authorization_target,
        labels_transaction=args.verify_only,
        scoring_transaction=args.verify_only,
        scoring_attestation=args.verify_only,
        spent_incomplete=spent_incomplete_present,
        closure_manifest=args.verify_only
        and (authorization_target == "CLOSED" or closure_present),
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
    prediction_receipt = next(
        receipt
        for receipt in authorization["receipts"]
        if receipt["state"] == "PREDICTIONS_VERIFIED"
        and receipt["retry_kind"] == "none"
    )
    if (
        active_core.state_receipt_sha256(prediction_receipt)
        != args.prior_state_receipt_sha256
        or args.prior_state_receipt_blob
        != active_core.state_receipt_blob_name(
            args.state_prefix, prediction_receipt
        )
    ):
        raise active_core.LockedEvaluationError(
            "Stage E prediction predecessor hash mismatch"
        )
    prediction_context = _load_prediction_attempt_context(
        active_core,
        active_service,
        args,
        authorization,
        prediction_receipt,
    )
    retry_persistence = None
    scorer_context = None
    prior_receipt = prediction_receipt
    if args.retry_kind == "scorer_infrastructure":
        scorer_context = _prepare_scorer_retry_attempt(
            active_core,
            active_service,
            args,
            authorization,
            prediction_receipt,
            now=now,
        )
        prior_receipt = scorer_context["retry_receipt"]
        retry_persistence = scorer_context["retry_persistence"]
    elif args.retry_kind == "verification_only":
        prior_receipt = authorization["prior_receipt"]
    elif args.retry_kind != "none":
        raise active_core.LockedEvaluationError("Stage E retry kind is invalid")
    state_before = active_core._authorization_state_members(
        args.state_prefix,
        final_state=authorization_target,
        retry_kinds=authorization["retry_kinds"],
        labels_transaction=args.verify_only or labels_transaction_present,
        scoring_transaction=args.verify_only,
        scoring_attestation=args.verify_only and scoring_attestation_present,
        spent_incomplete=authorization["spent_incomplete"],
        closure_manifest=args.verify_only
        and (authorization_target == "CLOSED" or closure_present),
    )
    prediction_members = {
        f"{args.predictions_prefix}/{name}"
        for name in active_core.PREDICTION_MEMBER_NAMES
    }
    score_reservation_blob = (
        f"{args.scores_prefix}/{active_core.SCORE_MEMBER_NAMES[0]}"
    )
    stage_e_visibility_blob = (
        f"{args.visibility_prefix}/stage_e_visibility.json"
    )
    attempt_timestamp = None
    adopted_score_reservation_bytes = None
    score_nonce = None
    visibility = None
    visibility_persistence = None
    score_metadata: list[dict[str, Any]] = []
    visibility_metadata: list[dict[str, Any]] = []
    if args.retry_kind == "none":
        primary_context = _prepare_primary_stage_e_attempt(
            active_core,
            active_service,
            args,
            prediction_receipt,
            prediction_context,
            now=now,
        )
        score_metadata = primary_context["score_metadata"]
        visibility_metadata = primary_context["visibility_metadata"]
        adopted_score_reservation_bytes = primary_context[
            "score_reservation_bytes"
        ]
        score_nonce = primary_context["score_nonce"]
        visibility = primary_context["visibility"]
        visibility_persistence = primary_context[
            "visibility_persistence"
        ]
        attempt_timestamp = primary_context["timestamp"]
        _validate_stage_e_attempt_membership(
            active_core,
            active_service,
            args,
            prediction_members=prediction_members,
            prediction_context=prediction_context,
            state_members=state_before,
            score_metadata=score_metadata,
            visibility_metadata=visibility_metadata,
            scorer_context=None,
        )
    elif args.retry_kind == "scorer_infrastructure":
        if scorer_context is None:
            raise active_core.LockedEvaluationError(
                "scorer attempt provenance is missing"
            )
        score_metadata = list(scorer_context["score_metadata"])
        visibility_metadata = list(scorer_context["visibility_metadata"])
        adopted_score_reservation_bytes = scorer_context[
            "score_reservation_bytes"
        ]
        score_nonce = scorer_context["score_nonce"]
        visibility = scorer_context["visibility"]
        visibility_persistence = scorer_context[
            "visibility_persistence"
        ]
        attempt_timestamp = active_core.max_canonical_utc(
            now(),
            prediction_receipt["timestamp_utc"],
            prior_receipt["timestamp_utc"],
            visibility["created_utc"],
        )
        _validate_stage_e_attempt_membership(
            active_core,
            active_service,
            args,
            prediction_members=prediction_members,
            prediction_context=prediction_context,
            state_members=state_before,
            score_metadata=score_metadata,
            visibility_metadata=visibility_metadata,
            scorer_context=scorer_context,
        )

    prediction_manifest_blob = (
        f"{args.predictions_prefix}/"
        f"{active_core.PREDICTION_MEMBER_NAMES[-1]}"
    )
    prediction_manifest_bytes, prediction_manifest_etag = (
        active_core.download_verified_blob(
            active_service,
            args.container,
            prediction_manifest_blob,
            expected_sha256=args.prediction_manifest_sha256,
        )
    )
    prediction_manifest = active_core.validate_prediction_artifact_manifest(
        prediction_manifest_bytes,
        expected_sha256=args.prediction_manifest_sha256,
        parent_prefix=args.parent_prefix,
        authorization_id=args.authorization_id,
        expected_retry_kind=prediction_context["retry_kind"],
        expected_execution_id=prediction_context["execution_id"],
    )
    if args.verify_only:
        _validate_prior_prediction_state(
            active_core,
            prediction_receipt,
            args,
            active_core.sha256_bytes(prediction_manifest_bytes),
        )
        return _verify_score_prefix(
            active_core,
            active_service,
            args,
            prediction_manifest,
            prediction_receipt,
            prediction_context,
            authorization,
            gates,
            now,
        )
    prediction_artifacts = active_core.download_prediction_artifacts(
        active_service,
        args.container,
        args.predictions_prefix,
        prediction_manifest_bytes,
        prediction_manifest,
        prediction_manifest_etag,
    )
    prediction_seal = active_core.parse_json_strict(
        prediction_artifacts["prediction_seal.json"], "prediction seal"
    )
    seal_binding = active_core.validate_locked_prediction_seal(
        prediction_seal,
        request_manifest_bytes=prediction_artifacts[
            "prediction_request_manifest.json"
        ],
        predictions_bytes=prediction_artifacts[_CANDIDATE_PREDICTIONS_MEMBER],
        legacy_predictions_bytes=prediction_artifacts[_LEGACY_PREDICTIONS_MEMBER],
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_retry_kind=prediction_context["retry_kind"],
        expected_execution_id=prediction_context["execution_id"],
    )
    if (
        seal_binding["implementation_commit"] != args.implementation_commit
        or seal_binding["image_digest"] != args.image_digest
        or seal_binding["config_sha256"] != args.config_sha256
        or seal_binding["visibility_sha256"]
        != prediction_manifest["stage_p_visibility_sha256"]
    ):
        raise active_core.LockedEvaluationError(
            "prediction seal implementation/image/config mismatch"
        )
    input_receipt = next(
        receipt
        for receipt in authorization["receipts"]
        if receipt["state"] == "INPUTS_READ"
        and receipt["retry_kind"] == "none"
    )
    request_manifest = active_core.parse_json_strict(
        prediction_artifacts["prediction_request_manifest.json"],
        "prediction request manifest",
    )
    expected_input_manifest_sha256 = input_receipt[
        "artifact_manifest_hashes"
    ]["inputs_manifest"]
    if (
        expected_input_manifest_sha256
        != input_receipt["artifact_manifest_hashes"]["locked_inputs_manifest"]
        or request_manifest.get("locked_input_manifest_sha256")
        != expected_input_manifest_sha256
    ):
        raise active_core.LockedEvaluationError(
            "sealed prediction source is not the authorized locked-input manifest"
        )
    prediction_graph = active_core.validate_prediction_artifact_graph(
        prediction_manifest_bytes,
        prediction_manifest,
        prediction_artifacts,
        gates=gates,
        expected_authorization_id=args.authorization_id,
        expected_parent_prefix=args.parent_prefix,
        expected_prediction_manifest_sha256=args.prediction_manifest_sha256,
        expected_input_manifest_sha256=expected_input_manifest_sha256,
        expected_input_receipt_sha256=active_core.state_receipt_sha256(
            input_receipt
        ),
        expected_authorization_lock_sha256=authorization[
            "authorization_lock_sha256"
        ],
        expected_authorization_manifest_sha256=authorization[
            "authorization_manifest_sha256"
        ],
        expected_implementation_manifest_sha256=authorization[
            "implementation_manifest_sha256"
        ],
        expected_locked_manifest_sha256=authorization[
            "locked_manifest_sha256"
        ],
        expected_implementation_commit=args.implementation_commit,
        expected_image_digest=args.image_digest,
        expected_config_sha256=args.config_sha256,
        expected_locked_input_source_binding=authorization[
            "authorization_manifest"
        ],
        expected_retry_kind=prediction_context["retry_kind"],
        expected_execution_id=prediction_context["execution_id"],
    )
    _validate_prior_prediction_state(
        active_core,
        prediction_receipt,
        args,
        active_core.sha256_bytes(prediction_manifest_bytes),
    )

    # A label manifest is a predeclared binding, not the label payload.  The
    # payload client itself is deliberately constructed only after the
    # overwrite-false labels-open transaction below.
    labels_manifest_bytes, labels_manifest_etag = (
        active_core.download_verified_blob(
            active_service,
            args.container,
            args.labels_manifest_blob,
            expected_sha256=args.labels_manifest_sha256,
        )
    )
    labels_binding = active_core.validate_locked_labels_manifest(
        labels_manifest_bytes,
        expected_manifest_sha256=args.labels_manifest_sha256,
        expected_payload_sha256=args.labels_sha256,
        parent_prefix=args.parent_prefix,
        payload_relative_path="locked-labels/locked_reference_labels.jsonl",
        gates=gates,
    )
    if (
        not active_core.exact_json_equal(
            labels_binding["ordered_case_ids"],
            prediction_manifest["ordered_case_ids"],
        )
        or not active_core.exact_json_equal(
            labels_binding["ordered_case_ids"],
            prediction_graph["ordered_case_ids"],
        )
        or labels_binding["manifest_sha256"]
        != prediction_receipt["artifact_manifest_hashes"][
            "locked_labels_manifest"
        ]
    ):
        raise active_core.LockedEvaluationError(
            "label-manifest membership differs from sealed predictions"
        )
    score_members_before = {
        item["blob_name"] for item in score_metadata
    }
    if active_core.list_exact_prefix(
        active_service, args.container, args.scores_prefix
    ) != score_members_before:
        raise active_core.LockedEvaluationError(
            "score destination changed before one-shot scoring"
        )
    if (
        visibility is None
        or visibility_persistence is None
        or attempt_timestamp is None
        or score_nonce is None
        or adopted_score_reservation_bytes is None
    ):
        raise active_core.LockedEvaluationError(
            "current scoring attempt preparation is incomplete"
        )
    stage_e_retry_kind = args.retry_kind
    stage_e_retry_receipt_sha256 = (
        None if retry_persistence is None else retry_persistence["sha256"]
    )
    stage_e_visibility_sha256 = visibility_persistence["sha256"]
    timestamp = active_core.max_canonical_utc(
        attempt_timestamp,
        prior_receipt["timestamp_utc"],
        visibility["created_utc"],
    )

    def build_transaction(
        *,
        prior_receipt_sha256: str,
        execution_id: str,
        actor: str,
        created_utc: str,
    ) -> Mapping[str, Any]:
        return active_core.build_labels_open_transaction(
            authorization_id=args.authorization_id,
            parent_prefix=args.parent_prefix,
            state_prefix=args.state_prefix,
            scores_prefix=args.scores_prefix,
            scoring_retry_kind=args.retry_kind,
            retry_receipt_sha256=(
                None
                if retry_persistence is None
                else retry_persistence["sha256"]
            ),
            authorization_lock_sha256=authorization[
                "authorization_lock_sha256"
            ],
            authorization_manifest_sha256=authorization[
                "authorization_manifest_sha256"
            ],
            implementation_manifest_sha256=authorization[
                "implementation_manifest_sha256"
            ],
            prediction_manifest_sha256=active_core.sha256_bytes(
                prediction_manifest_bytes
            ),
            prediction_seal_sha256=active_core.sha256_bytes(
                prediction_artifacts["prediction_seal.json"]
            ),
            prediction_request_manifest_sha256=active_core.sha256_bytes(
                prediction_artifacts["prediction_request_manifest.json"]
            ),
            input_manifest_sha256=expected_input_manifest_sha256,
            locked_manifest_sha256=prior_receipt[
                "artifact_manifest_hashes"
            ]["locked_manifest"],
            labels_manifest_sha256=active_core.sha256_bytes(
                labels_manifest_bytes
            ),
            labels_manifest_blob_name=args.labels_manifest_blob,
            labels_manifest_etag=labels_manifest_etag,
            labels_blob_name=args.labels_blob,
            labels_sha256=args.labels_sha256,
            ordered_case_ids=prediction_graph["ordered_case_ids"],
            prior_receipt_sha256=prior_receipt_sha256,
            visibility_blob_name=visibility_persistence["blob_name"],
            visibility_sha256=visibility_persistence["sha256"],
            visibility_etag=visibility_persistence["etag"],
            implementation_commit=args.implementation_commit,
            image_digest=args.image_digest,
            config_sha256=args.config_sha256,
            execution_id=execution_id,
            actor=actor,
            created_utc=created_utc,
        )

    transaction = build_transaction(
        prior_receipt_sha256=active_core.state_receipt_sha256(prior_receipt),
        execution_id=args.execution_id,
        actor=args.actor,
        created_utc=timestamp,
    )
    transaction_persistence = active_core.persist_labels_open_transaction(
        active_service,
        args.container,
        args.state_prefix,
        transaction,
    )
    state_after_transaction = active_core._authorization_state_members(
        args.state_prefix,
        final_state="PREDICTIONS_VERIFIED",
        retry_kinds=authorization["retry_kinds"],
        labels_transaction=True,
        spent_incomplete=authorization["spent_incomplete"],
    )
    _validate_stage_e_attempt_membership(
        active_core,
        active_service,
        args,
        prediction_members=prediction_members,
        prediction_context=prediction_context,
        state_members=state_after_transaction,
        score_metadata=score_metadata,
        visibility_metadata=visibility_metadata,
        scorer_context=scorer_context,
    )
    labels_bytes, labels_etag = active_core.download_verified_blob(
        active_service,
        args.container,
        args.labels_blob,
        expected_sha256=args.labels_sha256,
        expected_size=labels_binding["payload_size"],
    )
    labels_receipt = active_core.build_next_state_receipt(
        prior_receipt,
        state="LABELS_READ",
        artifact_manifest_sha256=active_core.sha256_bytes(labels_manifest_bytes),
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
    labels_receipt_persistence = (
        active_core.persist_or_adopt_state_receipt(
        active_service, args.container, args.state_prefix, labels_receipt
        )
    )
    state_after_labels_receipt = active_core._authorization_state_members(
        args.state_prefix,
        final_state="LABELS_READ",
        retry_kinds=authorization["retry_kinds"],
        labels_transaction=True,
        spent_incomplete=authorization["spent_incomplete"],
    )
    _validate_stage_e_attempt_membership(
        active_core,
        active_service,
        args,
        prediction_members=prediction_members,
        prediction_context=prediction_context,
        state_members=state_after_labels_receipt,
        score_metadata=score_metadata,
        visibility_metadata=visibility_metadata,
        scorer_context=scorer_context,
    )
    ledger_context = _scoring_ledger_context(
        active_core,
        args,
        authorization=authorization,
        prediction_manifest=prediction_manifest,
        labels_binding=labels_binding,
        labels_manifest_etag=labels_manifest_etag,
        labels_etag=labels_etag,
        labels_open_transaction_sha256=transaction_persistence["sha256"],
        scores_prefix=args.scores_prefix,
        scoring_retry_kind=stage_e_retry_kind,
        scoring_execution_id=args.execution_id,
        scoring_actor=args.actor,
        stage_e_visibility_sha256=stage_e_visibility_sha256,
        retry_receipt_sha256=stage_e_retry_receipt_sha256,
        created_utc=timestamp,
    )
    scoring_ledger_bytes, _, _ = active_core.build_scoring_ledger_bytes(
        labels_bytes,
        prediction_artifacts[_CANDIDATE_PREDICTIONS_MEMBER],
        prediction_artifacts[_GATING_COMPARATOR_PREDICTIONS_MEMBER],
        gate_bytes,
        context=ledger_context,
        expected_ordered_case_ids=prediction_graph["ordered_case_ids"],
    )
    ledger_validation = active_core.validate_scoring_ledger_bytes(
        scoring_ledger_bytes,
        prediction_artifacts[_CANDIDATE_PREDICTIONS_MEMBER],
        prediction_artifacts[_GATING_COMPARATOR_PREDICTIONS_MEMBER],
        gate_bytes,
        context=ledger_context,
        expected_ordered_case_ids=prediction_graph["ordered_case_ids"],
    )
    metrics = ledger_validation["metrics"]
    failures = ledger_validation["failures"]
    diagnostic_metrics = _score_reporting_only_comparator(
        active_core,
        labels_bytes=labels_bytes,
        candidate_bytes=prediction_artifacts[_CANDIDATE_PREDICTIONS_MEMBER],
        gate_bytes=gate_bytes,
        prediction_artifacts=prediction_artifacts,
    )
    if adopted_score_reservation_bytes is None:
        score_nonce = secrets.token_hex(16)
        score_reservation_bytes = active_core.canonical_json_bytes(
            active_core.build_reservation(
                leaf="scores",
                prefix=args.scores_prefix,
                authorization_id=args.authorization_id,
                created_utc=timestamp,
                nonce=score_nonce,
                parent_prefix=args.parent_prefix,
                stage=active_core.STAGE_E,
                retry_kind=stage_e_retry_kind,
                execution_id=args.execution_id,
            )
        )
        score_reservation_etag = active_core.upload_blob_once(
            active_service,
            args.container,
            score_reservation_blob,
            score_reservation_bytes,
        )
        active_core.verify_uploaded_blob(
            active_service,
            args.container,
            score_reservation_blob,
            score_reservation_bytes,
            score_reservation_etag,
        )
    else:
        score_reservation_bytes = adopted_score_reservation_bytes
        score_reservation = active_core.parse_json_strict(
            score_reservation_bytes, "scores reservation"
        )
        score_nonce = score_reservation["nonce"]
    if active_core.list_exact_prefix(
        active_service, args.container, args.scores_prefix
    ) != {score_reservation_blob}:
        raise active_core.LockedEvaluationError(
            "score reservation is not the sole persisted score member"
        )
    scoring_ledger_blob = (
        f"{args.scores_prefix}/{active_core.SCORING_LEDGER_FILENAME}"
    )
    scoring_ledger_etag = active_core.upload_blob_once(
        active_service,
        args.container,
        scoring_ledger_blob,
        scoring_ledger_bytes,
    )
    active_core.verify_uploaded_blob(
        active_service,
        args.container,
        scoring_ledger_blob,
        scoring_ledger_bytes,
        scoring_ledger_etag,
    )
    score_members_before = {
        score_reservation_blob,
        scoring_ledger_blob,
    }
    if active_core.list_exact_prefix(
        active_service, args.container, args.scores_prefix
    ) != score_members_before:
        raise active_core.LockedEvaluationError(
            "score ledger prologue membership is not exact"
        )
    score_metadata = _list_member_metadata(
        active_core,
        active_service,
        args,
        args.scores_prefix,
    )
    _validate_stage_e_attempt_membership(
        active_core,
        active_service,
        args,
        prediction_members=prediction_members,
        prediction_context=prediction_context,
        state_members=state_after_labels_receipt,
        score_metadata=score_metadata,
        visibility_metadata=visibility_metadata,
        scorer_context=scorer_context,
    )
    metrics = active_core.bind_metrics_artifacts(
        metrics,
        authorization_id=args.authorization_id,
        registered_parent_prefix=args.parent_prefix,
        authorization_lock_sha256=authorization[
            "authorization_lock_sha256"
        ],
        authorization_manifest_sha256=authorization[
            "authorization_manifest_sha256"
        ],
        implementation_manifest_sha256=authorization[
            "implementation_manifest_sha256"
        ],
        prediction_seal_sha256=active_core.sha256_bytes(
            prediction_artifacts["prediction_seal.json"]
        ),
        prediction_manifest_sha256=active_core.sha256_bytes(
            prediction_manifest_bytes
        ),
        prediction_request_manifest_sha256=active_core.sha256_bytes(
            prediction_artifacts["prediction_request_manifest.json"]
        ),
        locked_manifest_sha256=authorization["locked_manifest_sha256"],
        input_manifest_sha256=expected_input_manifest_sha256,
        locked_input_sha256=prediction_graph["request"][
            "locked_input_sha256"
        ],
        labels_manifest_sha256=active_core.sha256_bytes(
            labels_manifest_bytes
        ),
        labels_sha256=active_core.sha256_bytes(labels_bytes),
        labels_open_transaction_sha256=transaction_persistence["sha256"],
        scores_prefix=args.scores_prefix,
        scoring_retry_kind=stage_e_retry_kind,
        scoring_execution_id=args.execution_id,
        scoring_actor=args.actor,
        stage_e_visibility_sha256=stage_e_visibility_sha256,
        retry_receipt_sha256=stage_e_retry_receipt_sha256,
        scoring_ledger_sha256=ledger_validation["ledger_sha256"],
        scoring_ledger_size=ledger_validation["ledger_size"],
        scoring_ledger_etag=scoring_ledger_etag,
        case_universe_sha256=prediction_graph["case_universe_sha256"],
        row_count=len(prediction_graph["ordered_case_ids"]),
        implementation_commit=args.implementation_commit,
        image_digest=args.image_digest,
        config_sha256=args.config_sha256,
    )
    active_core.validate_metrics_artifact(
        metrics, gates, require_bindings=True
    )
    score_payloads, decision, retirement = active_core.build_score_payloads(
        metrics,
        failures,
        authorization_id=args.authorization_id,
        registered_parent_prefix=args.parent_prefix,
        authorization_lock_sha256=authorization[
            "authorization_lock_sha256"
        ],
        authorization_manifest_sha256=authorization[
            "authorization_manifest_sha256"
        ],
        implementation_manifest_sha256=authorization[
            "implementation_manifest_sha256"
        ],
        scores_prefix=args.scores_prefix,
        prediction_seal_sha256=active_core.sha256_bytes(
            prediction_artifacts["prediction_seal.json"]
        ),
        prediction_manifest_sha256=active_core.sha256_bytes(
            prediction_manifest_bytes
        ),
        prediction_request_manifest_sha256=active_core.sha256_bytes(
            prediction_artifacts["prediction_request_manifest.json"]
        ),
        locked_manifest_sha256=authorization["locked_manifest_sha256"],
        input_manifest_sha256=expected_input_manifest_sha256,
        locked_input_sha256=prediction_graph["request"][
            "locked_input_sha256"
        ],
        labels_manifest_sha256=active_core.sha256_bytes(
            labels_manifest_bytes
        ),
        labels_sha256=active_core.sha256_bytes(labels_bytes),
        labels_open_transaction_sha256=transaction_persistence["sha256"],
        scoring_retry_kind=stage_e_retry_kind,
        scoring_execution_id=args.execution_id,
        scoring_actor=args.actor,
        stage_e_visibility_sha256=stage_e_visibility_sha256,
        retry_receipt_sha256=stage_e_retry_receipt_sha256,
        scoring_ledger_bytes=scoring_ledger_bytes,
        scoring_ledger_sha256=ledger_validation["ledger_sha256"],
        scoring_ledger_size=ledger_validation["ledger_size"],
        scoring_ledger_etag=scoring_ledger_etag,
        case_universe_sha256=prediction_graph["case_universe_sha256"],
        row_count=len(prediction_graph["ordered_case_ids"]),
        implementation_commit=args.implementation_commit,
        image_digest=args.image_digest,
        config_sha256=args.config_sha256,
        created_utc=timestamp,
        nonce=score_nonce,
    )
    score_payloads[active_core.SCORE_MEMBER_NAMES[0]] = (
        score_reservation_bytes
    )
    decision_sha256 = active_core.sha256_bytes(
        score_payloads["locked_evaluation_decision.json"]
    )
    retirement_sha256 = active_core.sha256_bytes(
        score_payloads["retirement_record.json"]
    )
    scoring_transaction = active_core.build_scoring_transaction(
        authorization_id=args.authorization_id,
        parent_prefix=args.parent_prefix,
        state_prefix=args.state_prefix,
        scores_prefix=args.scores_prefix,
        scoring_retry_kind=stage_e_retry_kind,
        retry_receipt_sha256=stage_e_retry_receipt_sha256,
        stage_e_visibility_sha256=stage_e_visibility_sha256,
        authorization_lock_sha256=authorization["authorization_lock_sha256"],
        authorization_manifest_sha256=authorization[
            "authorization_manifest_sha256"
        ],
        implementation_manifest_sha256=authorization[
            "implementation_manifest_sha256"
        ],
        prediction_manifest_sha256=active_core.sha256_bytes(
            prediction_manifest_bytes
        ),
        prediction_seal_sha256=active_core.sha256_bytes(
            prediction_artifacts["prediction_seal.json"]
        ),
        prediction_request_manifest_sha256=active_core.sha256_bytes(
            prediction_artifacts["prediction_request_manifest.json"]
        ),
        locked_manifest_sha256=authorization["locked_manifest_sha256"],
        input_manifest_sha256=expected_input_manifest_sha256,
        locked_input_sha256=prediction_graph["request"]["locked_input_sha256"],
        labels_manifest_sha256=active_core.sha256_bytes(labels_manifest_bytes),
        labels_sha256=active_core.sha256_bytes(labels_bytes),
        labels_open_transaction_sha256=transaction_persistence["sha256"],
        scoring_ledger_sha256=ledger_validation["ledger_sha256"],
        scoring_ledger_size=ledger_validation["ledger_size"],
        scoring_ledger_etag=scoring_ledger_etag,
        case_universe_sha256=prediction_graph["case_universe_sha256"],
        row_count=len(prediction_graph["ordered_case_ids"]),
        implementation_commit=args.implementation_commit,
        image_digest=args.image_digest,
        config_sha256=args.config_sha256,
        score_payloads=score_payloads,
        outcome=decision["formal_decision"],
        execution_id=args.execution_id,
        actor=args.actor,
        created_utc=timestamp,
    )
    scoring_transaction_bytes = active_core.canonical_json_bytes(
        scoring_transaction
    )
    scoring_transaction_persistence = active_core.persist_singleton(
        active_service,
        args.container,
        (
            f"{args.state_prefix}/"
            f"{active_core.SCORING_TRANSACTION_FILENAME}"
        ),
        scoring_transaction_bytes,
    )
    scoring_transaction_sha256 = scoring_transaction_persistence["sha256"]
    state_after_scoring_transaction = active_core._authorization_state_members(
        args.state_prefix,
        final_state="LABELS_READ",
        retry_kinds=authorization["retry_kinds"],
        labels_transaction=True,
        scoring_transaction=True,
        spent_incomplete=authorization["spent_incomplete"],
    )
    expected_score_baseline = _validate_stage_e_attempt_membership(
        active_core,
        active_service,
        args,
        prediction_members=prediction_members,
        prediction_context=prediction_context,
        state_members=state_after_scoring_transaction,
        score_metadata=score_metadata,
        visibility_metadata=visibility_metadata,
        scorer_context=scorer_context,
    )
    score_parent_baseline = active_core.expected_registered_parent_membership(
        args.parent_prefix,
        set().union(*expected_score_baseline.values()),
    )

    def score_manifest_builder(
        metadata: list[dict[str, Any]],
    ) -> Mapping[str, Any]:
        return active_core.build_score_manifest(
            metadata=metadata,
            authorization_id=args.authorization_id,
            authorization_lock_sha256=authorization[
                "authorization_lock_sha256"
            ],
            authorization_manifest_sha256=authorization[
                "authorization_manifest_sha256"
            ],
            implementation_manifest_sha256=authorization[
                "implementation_manifest_sha256"
            ],
            parent_prefix=args.parent_prefix,
            scores_prefix=args.scores_prefix,
            scoring_retry_kind=stage_e_retry_kind,
            retry_receipt_sha256=stage_e_retry_receipt_sha256,
            prediction_seal_sha256=active_core.sha256_bytes(
                prediction_artifacts["prediction_seal.json"]
            ),
            prediction_manifest_sha256=active_core.sha256_bytes(
                prediction_manifest_bytes
            ),
            prediction_request_manifest_sha256=active_core.sha256_bytes(
                prediction_artifacts["prediction_request_manifest.json"]
            ),
            locked_manifest_sha256=authorization["locked_manifest_sha256"],
            input_manifest_sha256=expected_input_manifest_sha256,
            locked_input_sha256=prediction_graph["request"][
                "locked_input_sha256"
            ],
            labels_manifest_sha256=active_core.sha256_bytes(
                labels_manifest_bytes
            ),
            labels_manifest_blob_name=args.labels_manifest_blob,
            labels_manifest_etag=labels_manifest_etag,
            labels_blob_name=args.labels_blob,
            labels_sha256=active_core.sha256_bytes(labels_bytes),
            labels_open_transaction_sha256=transaction_persistence["sha256"],
            labels_etag=labels_etag,
            scoring_ledger_sha256=ledger_validation["ledger_sha256"],
            scoring_ledger_size=ledger_validation["ledger_size"],
            scoring_ledger_etag=scoring_ledger_etag,
            case_universe_sha256=prediction_graph["case_universe_sha256"],
            row_count=len(prediction_graph["ordered_case_ids"]),
            scoring_transaction_sha256=scoring_transaction_sha256,
            scoring_execution_id=args.execution_id,
            scoring_actor=args.actor,
            stage_e_visibility_sha256=stage_e_visibility_sha256,
            stage_e_visibility_etag=visibility_persistence["etag"],
            gate_sha256=active_core.sha256_bytes(gate_bytes),
            metrics_sha256=active_core.sha256_bytes(
                score_payloads["locked_evaluation_metrics.json"]
            ),
            decision_sha256=decision_sha256,
            retirement_sha256=retirement_sha256,
            implementation_commit=args.implementation_commit,
            image_digest=args.image_digest,
            config_sha256=args.config_sha256,
            outcome=decision["formal_decision"],
            created_utc=timestamp,
        )

    score_persistence = active_core.persist_manifest_last_prefix(
        active_service,
        args.container,
        args.scores_prefix,
        member_names=active_core.SCORE_MEMBER_NAMES,
        payloads=score_payloads,
        manifest_builder=score_manifest_builder,
        registered_member_names=active_core.SCORE_MEMBER_NAMES,
        parent_prefix=args.parent_prefix,
        registered_parent_members_before=score_parent_baseline,
        adopted_payloads={
            active_core.SCORE_MEMBER_NAMES[0]: score_payloads[
                active_core.SCORE_MEMBER_NAMES[0]
            ],
            active_core.SCORING_LEDGER_FILENAME: scoring_ledger_bytes,
        },
    )
    scoring_attestation = active_core.build_scoring_attestation(
        scoring_transaction,
        score_manifest_bytes=score_persistence["manifest_bytes"],
        score_manifest_etag=score_persistence["manifest_etag"],
    )
    scoring_attestation_persistence = active_core.persist_singleton(
        active_service,
        args.container,
        f"{args.state_prefix}/{active_core.SCORING_ATTESTATION_FILENAME}",
        active_core.canonical_json_bytes(scoring_attestation),
    )
    score_metadata = _list_member_metadata(
        active_core,
        active_service,
        args,
        args.scores_prefix,
    )
    state_after_attestation = active_core._authorization_state_members(
        args.state_prefix,
        final_state="LABELS_READ",
        retry_kinds=authorization["retry_kinds"],
        labels_transaction=True,
        scoring_transaction=True,
        scoring_attestation=True,
        spent_incomplete=authorization["spent_incomplete"],
    )
    _validate_stage_e_attempt_membership(
        active_core,
        active_service,
        args,
        prediction_members=prediction_members,
        prediction_context=prediction_context,
        state_members=state_after_attestation,
        score_metadata=score_metadata,
        visibility_metadata=visibility_metadata,
        scorer_context=scorer_context,
    )
    scores_receipt = active_core.build_next_state_receipt(
        labels_receipt,
        state="SCORES_VERIFIED",
        artifact_manifest_sha256=score_persistence["manifest_sha256"],
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
    scores_receipt_persistence = active_core.persist_state_receipt(
        active_service, args.container, args.state_prefix, scores_receipt
    )
    scores_verified_state_members = active_core._authorization_state_members(
        args.state_prefix,
        final_state="SCORES_VERIFIED",
        retry_kinds=authorization["retry_kinds"],
        labels_transaction=True,
        scoring_transaction=True,
        scoring_attestation=True,
        spent_incomplete=authorization["spent_incomplete"],
    )
    expected_scores_verified = _validate_stage_e_attempt_membership(
        active_core,
        active_service,
        args,
        prediction_members=prediction_members,
        prediction_context=prediction_context,
        state_members=scores_verified_state_members,
        score_metadata=score_metadata,
        visibility_metadata=visibility_metadata,
        scorer_context=scorer_context,
    )
    scores_verified_parent = active_core.expected_registered_parent_membership(
        args.parent_prefix,
        set().union(*expected_scores_verified.values()),
    )
    closure_manifest = active_core.build_closure_manifest(
        metrics,
        decision,
        retirement,
        scores_manifest_sha256=score_persistence["manifest_sha256"],
        created_utc=timestamp,
    )
    closure_persistence = active_core.persist_singleton(
        active_service,
        args.container,
        f"{args.state_prefix}/{active_core.CLOSURE_MANIFEST_FILENAME}",
        active_core.canonical_json_bytes(closure_manifest),
    )
    state_with_closure = active_core._authorization_state_members(
        args.state_prefix,
        final_state="SCORES_VERIFIED",
        retry_kinds=authorization["retry_kinds"],
        labels_transaction=True,
        scoring_transaction=True,
        scoring_attestation=True,
        spent_incomplete=authorization["spent_incomplete"],
        closure_manifest=True,
    )
    _validate_stage_e_attempt_membership(
        active_core,
        active_service,
        args,
        prediction_members=prediction_members,
        prediction_context=prediction_context,
        state_members=state_with_closure,
        score_metadata=score_metadata,
        visibility_metadata=visibility_metadata,
        scorer_context=scorer_context,
    )
    closed_receipt = active_core.build_next_state_receipt(
        scores_receipt,
        state="CLOSED",
        artifact_manifest_sha256=closure_persistence["sha256"],
        timestamp_utc=timestamp,
        execution_id=args.execution_id,
        actor=args.actor,
        visibility=[
            *visibility["artifact_classes"],
            f"record_sha256:{visibility_persistence['sha256']}",
        ],
        outcome=decision["formal_decision"],
        authorization_lock=authorization["authorization_lock"],
        implementation_manifest_bytes=authorization[
            "implementation_manifest_bytes"
        ],
    )
    closed_receipt_persistence = active_core.persist_state_receipt(
        active_service, args.container, args.state_prefix, closed_receipt
    )
    active_core.validate_closed_outcome(
        closed_receipt, metrics, decision, retirement, closure_manifest
    )
    final_state_members = active_core._authorization_state_members(
        args.state_prefix,
        final_state="CLOSED",
        retry_kinds=authorization["retry_kinds"],
        labels_transaction=True,
        scoring_transaction=True,
        scoring_attestation=True,
        spent_incomplete=authorization["spent_incomplete"],
        closure_manifest=True,
    )
    _validate_stage_e_attempt_membership(
        active_core,
        active_service,
        args,
        prediction_members=prediction_members,
        prediction_context=prediction_context,
        state_members=final_state_members,
        score_metadata=score_metadata,
        visibility_metadata=visibility_metadata,
        scorer_context=scorer_context,
    )
    return {
        "stage": "E",
        "mode": "one_shot_finalization",
        "status": decision["formal_decision"],
        "authorization_id": args.authorization_id,
        "scores_prefix": args.scores_prefix,
        "visibility_prefix": args.visibility_prefix,
        "prediction_manifest_sha256": active_core.sha256_bytes(
            prediction_manifest_bytes
        ),
        "labels_manifest_sha256": active_core.sha256_bytes(
            labels_manifest_bytes
        ),
        "labels_manifest_etag": labels_manifest_etag,
        "labels_open_transaction_sha256": transaction_persistence["sha256"],
        "scoring_ledger_sha256": ledger_validation["ledger_sha256"],
        "scoring_ledger_size": ledger_validation["ledger_size"],
        "scoring_ledger_etag": scoring_ledger_etag,
        "scoring_transaction_sha256": scoring_transaction_sha256,
        "scoring_attestation_sha256": scoring_attestation_persistence["sha256"],
        "scores_manifest_sha256": score_persistence["manifest_sha256"],
        "labels_receipt_sha256": labels_receipt_persistence["sha256"],
        "scores_receipt_sha256": scores_receipt_persistence["sha256"],
        "closed_receipt_sha256": closed_receipt_persistence["sha256"],
        "visibility_sha256": visibility_persistence["sha256"],
        "holdout_spent": True,
        "holdout_retired": True,
        "formal_evaluation_count": 1,
        "parser_rerun": False,
        "metric_retry_allowed": False,
        "target_model_loaded": False,
        "target_model_downloaded": False,
        "target_model_inference": False,
        "gpu_used": False,
        "retry_kind": args.retry_kind,
        "retry_receipt_sha256": (
            None if retry_persistence is None else retry_persistence["sha256"]
        ),
    }


def run_stage_e(
    args: argparse.Namespace,
    *,
    service: Any | None = None,
    core: ModuleType | None = None,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    previous_depth = _STAGE_E_GUARD_DEPTH
    active_core = core or _load_core()
    try:
        _assert_runtime_isolation()
        if getattr(args, "close_invalid_only", False):
            if (
                not args.verify_only
                or args.retry_kind != "verification_only"
                or args.scores_manifest_sha256 is not None
                or args.closed_receipt_sha256 is not None
                or args.producer_retry_kind
                not in {"none", "scorer_infrastructure"}
                or not args.producer_execution_id
            ):
                raise active_core.LockedEvaluationError(
                    "INVALID closure-only controls are inconsistent"
                )
            active_service = service
            if active_service is None:
                active_core.validate_private_endpoint_resolution(
                    args.account_url,
                    args.expected_private_endpoint_ip,
                )
                active_service = active_core.create_blob_service(
                    args.account_url
                )
            return _close_invalid_open_attempt(
                active_core,
                active_service,
                args,
            )
        try:
            return _run_stage_e(
                args,
                service=service,
                core=active_core,
                now=now,
            )
        except Exception:
            if args.verify_only:
                raise
            active_service = service
            if active_service is None:
                active_core.validate_private_endpoint_resolution(
                    args.account_url, args.expected_private_endpoint_ip
                )
                active_service = active_core.create_blob_service(
                    args.account_url
                )
            transaction_blob = (
                f"{args.state_prefix}/"
                f"{active_core.LABELS_OPEN_TRANSACTION_FILENAME}"
            )
            if transaction_blob not in active_core.list_exact_prefix(
                active_service, args.container, args.state_prefix
            ):
                raise
            try:
                return _close_invalid_open_attempt(
                    active_core, active_service, args
                )
            except Exception as closure_error:
                raise active_core.LockedEvaluationError(
                    "post-label failure could not reach authenticated CLOSED"
                ) from closure_error
    finally:
        _restore_guard_depth(previous_depth)


def _parser() -> argparse.ArgumentParser:
    parser = _RedactedArgumentParser(
        description="Finalize the parser-free one-shot locked evaluation",
        allow_abbrev=False,
    )
    parser.add_argument("--account-url", required=True)
    parser.add_argument(
        "--expected-private-endpoint-ip", action="append", required=True
    )
    parser.add_argument("--container", required=True)
    parser.add_argument("--parent-prefix", required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--predictions-prefix", required=True)
    parser.add_argument("--prediction-manifest-sha256", required=True)
    parser.add_argument("--scores-prefix", required=True)
    parser.add_argument("--state-prefix", required=True)
    parser.add_argument("--visibility-prefix", required=True)
    parser.add_argument("--labels-blob", required=True)
    parser.add_argument("--labels-sha256", required=True)
    parser.add_argument("--labels-manifest-blob", required=True)
    parser.add_argument("--labels-manifest-sha256", required=True)
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
        choices=("none", "scorer_infrastructure", "verification_only"),
        default="none",
    )
    parser.add_argument("--execution-id", type=_execution_id, required=True)
    parser.add_argument(
        "--actor",
        choices=("stage-e-managed-runtime",),
        required=True,
    )
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--close-invalid-only", action="store_true")
    parser.add_argument(
        "--producer-retry-kind",
        choices=("none", "scorer_infrastructure"),
    )
    parser.add_argument("--producer-execution-id")
    parser.add_argument(
        "--verification-state",
        choices=(
            "PREDICTIONS_VERIFIED",
            "LABELS_READ",
            "SCORES_VERIFIED",
            "CLOSED",
        ),
        default="CLOSED",
    )
    parser.add_argument("--scores-manifest-sha256")
    parser.add_argument("--closed-receipt-sha256")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        core = _load_core()
        args = _parser().parse_args(argv)
        result = run_stage_e(args, core=core)
        public = {
            "stage": "E",
            "status": result["status"],
            "formal_evaluation_count": result.get(
                "formal_evaluation_count", 1
            ),
            "holdout_retired": result.get("holdout_retired", True),
            "parser_rerun": False,
        }
        print(json.dumps(public, sort_keys=True, separators=(",", ":")))
        return 0
    except SystemExit as exc:
        if exc.code in {None, 0}:
            return 0
        print(
            "STAGE_E_ERROR:ARGUMENTS_REJECTED:ArgumentError",
            file=sys.stderr,
        )
        return 2
    except _RedactedArgumentError:
        print(
            "STAGE_E_ERROR:ARGUMENTS_REJECTED:ArgumentError",
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
            f"STAGE_E_ERROR:EXECUTION_REJECTED:{stable_class}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
