"""Local, model-free tests for the preregistered all-45 semantic audit."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import os
import shutil
import stat
import subprocess
import sys
import uuid
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts import export_phase1_semantic_review_pack as exporter
from scripts import finalize_phase1_semantic_audit as finalizer
from scripts import prepare_semantic_audit_build_context as build_preparation
from jspace_observation.eval_parsing import create_eval_record
from jspace_observation.no_cot import (
    STRICT_ANSWER_ONLY_STOP_STRINGS,
    apply_stop_control_cleanup,
    create_generation_record,
    get_generation_config_for_condition,
    validate_no_cot_output,
)
from jspace_observation.phase1_branches import get_phase1_branch_metadata
from jspace_observation.postprocess import postprocess_answer_only
from jspace_observation.prompt_sets import ArithmeticPromptSet
from jspace_observation.record_audit import expected_record_keys
import jspace_observation.semantic_audit as semantic_audit_module
from jspace_observation.semantic_audit import (
    ANSWER_STATUS_LABELS,
    ARBITRATION_JUDGMENT_SCHEMA_VERSION,
    EXPERIMENTAL_TARGET_MODEL_ID,
    FROZEN_SHUFFLE_SEED,
    ISSUE_TAGS,
    MANDATORY_BOUNDARY_TEXT,
    PROTOCOL_BUNDLE_HASH_DOMAIN,
    PROTOCOL_RUNTIME_FILES,
    RELEASE_MANIFEST_FILENAMES,
    RELEASE_RESERVATION_FILENAME,
    REVIEWER_MODEL_ID,
    REVIEWER_REASONING_EFFORT,
    STAGE1_JUDGMENT_SCHEMA_VERSION,
    STAGE1_PACKET_FILENAME,
    STAGE2_JUDGMENT_SCHEMA_VERSION,
    STAGE2_PACKET_FILENAME,
    SemanticAuditError,
    SYNTHETIC_TEST_SOURCE_MODE,
    VERIFIED_SOURCE_EVIDENCE_MODE,
    _build_synthetic_review_pack_for_tests,
    _build_restricted_records,
    build_ambiguity_confusion_report,
    build_blinded_arbitration_packet,
    build_correctness_confusion_table,
    build_final_machine_outputs,
    build_material_impact_report,
    build_release_files,
    build_review_pack,
    build_submission_seal,
    canonical_json_bytes,
    canonical_jsonl_bytes,
    combine_staged_submission,
    compute_ambiguity_confusion_matrix,
    compute_reviewer_agreement,
    derive_parser_label,
    deterministic_review_mapping,
    determine_arbitration_triggers,
    enrich_final_adjudications,
    ensure_distinct_reviewer_identities,
    material_evaluator_error,
    merge_final_judgments,
    nominal_cohen_kappa,
    normalize_numeric_answer,
    parse_jsonl_strict,
    protocol_bundle_sha256,
    reconstruct_generation_prompt,
    render_semantic_audit_metrics_csv,
    scan_blinded_forbidden_fields,
    sha256_bytes,
    validate_arbiter_submission,
    validate_review_pack,
    validate_reviewer_submission,
    validate_sealed_submission,
    validate_semantic_audit_prefixes,
    validate_stage1_submission,
    validate_stage2_submission,
    validate_stage_release,
    validate_stage_release_files,
    validate_submission_artifact,
    verify_protocol_provenance,
)

exporter._load_runtime_for_tests()
finalizer._load_runtime_for_tests()


@pytest.fixture
def workdir():
    base = Path(os.environ.get("JSPACE_TEST_TMP", ROOT / ".pytest-work"))
    root = base / uuid.uuid4().hex
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        def remove_readonly(function, path, _error):
            os.chmod(path, stat.S_IWRITE)
            function(path)

        shutil.rmtree(root, onerror=remove_readonly)
        parent = root.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()


_SOURCE_RECORD_CACHE: tuple[list[dict], list[dict]] | None = None


def _remove_tree(path: Path) -> None:
    def remove_readonly(function, target, _error):
        os.chmod(target, stat.S_IWRITE)
        function(target)

    shutil.rmtree(path, onerror=remove_readonly)


def _source_records() -> tuple[list[dict], list[dict]]:
    global _SOURCE_RECORD_CACHE
    if _SOURCE_RECORD_CACHE is not None:
        return deepcopy(_SOURCE_RECORD_CACHE)
    items = {item.id: item for item in ArithmeticPromptSet.generate_pilot_set()}
    generations: list[dict] = []
    evaluations: list[dict] = []
    for model, task_family, depth, condition, task_id in expected_record_keys():
        item = items[task_id]
        answer = item.expected_answer
        raw_output = answer
        branch = get_phase1_branch_metadata(condition)
        config = get_generation_config_for_condition(condition, 64)
        raw_eval = create_eval_record(
            output=raw_output,
            parse_type=item.parse_type,
            expected_answer=answer,
            task_id=task_id,
            model_name=model,
            task_family=task_family,
            depth=depth,
            condition=condition,
            **branch,
        )
        stop_record = {
            "stop_control_enabled": config.stop_control_enabled,
            "stop_triggered": False,
            "stop_reason": None,
            "stop_string": None,
            "stop_mode": config.stop_mode,
            "stop_warning": None,
            "raw_output_before_stop_cleanup": raw_output,
            "raw_output": raw_output,
            "stopped_output": None,
            "stopped_no_cot_valid": None,
        }
        postprocess_record = {
            "raw_output_before_postprocess": raw_output,
            "postprocessed_output": None,
            "postprocessing_applied": False,
            "postprocessing_strategy": None,
            "postprocessing_reason": None,
            "postprocessing_warning": None,
            "raw_no_cot_valid": validate_no_cot_output(
                raw_output, method="answer_prefill"
            ).is_valid,
            "postprocessed_no_cot_valid": None,
            "postprocessed_answer_like": None,
        }
        selected_output = raw_output
        selected = "raw"
        if condition == "strict_answer_only_stopped":
            stopped = apply_stop_control_cleanup(
                raw_output,
                stop_strings=STRICT_ANSWER_ONLY_STOP_STRINGS,
                stop_control_enabled=True,
                stop_mode=config.stop_mode,
            )
            selected_output = stopped.stopped_output
            selected = "stopped"
            stop_record = {
                "stop_control_enabled": stopped.stop_control_enabled,
                "stop_triggered": stopped.stop_triggered,
                "stop_reason": stopped.stop_reason,
                "stop_string": stopped.stop_string,
                "stop_mode": stopped.stop_mode,
                "stop_warning": stopped.stop_warning,
                "raw_output_before_stop_cleanup": (
                    stopped.raw_output_before_stop_cleanup
                ),
                "raw_output": stopped.raw_output,
                "stopped_output": stopped.stopped_output,
                "stopped_no_cot_valid": validate_no_cot_output(
                    stopped.stopped_output, method="answer_prefill"
                ).is_valid,
            }
        elif condition == "strict_answer_only_postprocessed":
            processed = postprocess_answer_only(
                raw_output, task_type=item.parse_type
            )
            selected_output = processed.postprocessed_output
            selected = "postprocessed"
            postprocess_record = {
                "raw_output_before_postprocess": processed.raw_output,
                "postprocessed_output": processed.postprocessed_output,
                "postprocessing_applied": processed.postprocessing_applied,
                "postprocessing_strategy": processed.postprocessing_strategy,
                "postprocessing_reason": processed.postprocessing_reason,
                "postprocessing_warning": processed.postprocessing_warning,
                "raw_no_cot_valid": processed.raw_no_cot_valid,
                "postprocessed_no_cot_valid": processed.postprocessed_no_cot_valid,
                "postprocessed_answer_like": processed.postprocessed_answer_like,
            }
        evaluation = create_eval_record(
            output=selected_output,
            parse_type=item.parse_type,
            expected_answer=answer,
            task_id=task_id,
            model_name=model,
            task_family=task_family,
            depth=depth,
            condition=condition,
            raw_correctness=raw_eval["correctness"],
            raw_parsed_answer=raw_eval["parsed_answer"],
            raw_parse_valid=raw_eval["parse_valid"],
            eval_output_used=selected,
            **branch,
            **stop_record,
            **postprocess_record,
        )
        evaluation.update(
            {
                "eval_correctness": evaluation["correctness"],
                "stopped_correctness": (
                    evaluation["correctness"] if selected == "stopped" else None
                ),
                "postprocessed_correctness": (
                    evaluation["correctness"]
                    if selected == "postprocessed"
                    else None
                ),
            }
        )
        generation = create_generation_record(
            prompt=reconstruct_generation_prompt(condition, item.prompt_base),
            output=raw_output,
            no_cot_method=(
                "visible_cot"
                if condition == "visible_cot"
                else "r1_style_thinking"
                if condition == "r1_style_thinking"
                else "answer_prefill"
            ),
            model_name=model,
            task_id=task_id,
            ground_truth=answer,
            task_family=task_family,
            depth=depth,
            condition=condition,
            generation_time_s=1.0,
            condition_max_new_tokens=config.max_new_tokens,
            condition_temperature=config.temperature,
            condition_do_sample=config.do_sample,
            condition_top_p=config.top_p,
            decoding_profile=config.decoding_profile,
            stop_strings=list(config.stop_strings),
            **branch,
        )
        generation.update(
            {
                "raw_output": raw_output,
                "eval_output": selected_output,
                "parsed_answer": evaluation["parsed_answer"],
                "correct": evaluation["correctness"],
                "parse_valid": evaluation["parse_valid"],
                "parse_ambiguous": evaluation["parse_ambiguous"],
                "parse_strategy": evaluation["parse_strategy"],
                "answer_format_warning": evaluation["answer_format_warning"],
                "raw_correct": raw_eval["correctness"],
                "raw_correctness": raw_eval["correctness"],
                "raw_parsed_answer": raw_eval["parsed_answer"],
                "eval_output_used": selected,
                "eval_correct": evaluation["correctness"],
                "eval_correctness": evaluation["correctness"],
                "stopped_correct": (
                    evaluation["correctness"] if selected == "stopped" else None
                ),
                "stopped_correctness": (
                    evaluation["correctness"] if selected == "stopped" else None
                ),
                "postprocessed_correct": (
                    evaluation["correctness"]
                    if selected == "postprocessed"
                    else None
                ),
                "postprocessed_correctness": (
                    evaluation["correctness"]
                    if selected == "postprocessed"
                    else None
                ),
                **stop_record,
                **postprocess_record,
            }
        )
        generations.append(generation)
        evaluations.append(evaluation)
    _SOURCE_RECORD_CACHE = (generations, evaluations)
    return deepcopy(_SOURCE_RECORD_CACHE)


def _test_provenance() -> dict:
    file_sha256 = {
        relative: hashlib.sha256(
            ROOT.joinpath(*relative.split("/")).read_bytes()
        ).hexdigest()
        for relative in PROTOCOL_RUNTIME_FILES
    }
    return {
        "protocol_commit": "1" * 40,
        "protocol_bundle_sha256": protocol_bundle_sha256(ROOT),
        "bundle_hash_domain": PROTOCOL_BUNDLE_HASH_DOMAIN.decode("ascii").rstrip(
            "\0"
        ),
        "runtime_files": list(PROTOCOL_RUNTIME_FILES),
        "file_sha256": dict(sorted(file_sha256.items())),
        "attestation_schema_version": (
            semantic_audit_module.BUILD_ATTESTATION_SCHEMA_VERSION
        ),
        "generated_from_clean_git": True,
        "verification_mode": "local_git_and_bundle",
        "git_checks_performed": True,
        "verified": True,
    }


def _blob_source_service_for_tests(source_bytes: dict[str, bytes]):
    callbacks = {
        name: (lambda data=data: data) for name, data in source_bytes.items()
    }

    class Download:
        def __init__(self, callback):
            self.callback = callback

        def readall(self):
            return self.callback()

    class Blob:
        def __init__(self, name: str, index: int):
            self.name = name
            self.index = index

        def get_blob_properties(self):
            return SimpleNamespace(
                size=len(source_bytes[self.name]),
                etag=f'"test-etag-{self.index}"',
                last_modified="2026-07-15T00:00:00+00:00",
                version_id=f"test-version-{self.index}",
            )

        def download_blob(self, **kwargs):
            return Download(callbacks[self.name])

    names = list(source_bytes)

    class Service:
        def get_blob_client(self, *, container, blob):
            name = Path(blob).name
            return Blob(name, names.index(name))

    return Service()


_REVIEW_PACK_CACHE: dict | None = None
_REVIEW_SOURCE_HASHES: dict[str, str] | None = None


@pytest.fixture
def review_pack(monkeypatch) -> dict:
    global _REVIEW_PACK_CACHE, _REVIEW_SOURCE_HASHES
    if _REVIEW_PACK_CACHE is not None:
        monkeypatch.setattr(
            semantic_audit_module,
            "SOURCE_ARTIFACT_HASHES",
            _REVIEW_SOURCE_HASHES,
        )
        monkeypatch.setattr(
            exporter, "SOURCE_ARTIFACT_HASHES", _REVIEW_SOURCE_HASHES
        )
        return deepcopy(_REVIEW_PACK_CACHE)
    generations, evaluations = _source_records()
    source_bytes = {
        "phase1_generations.jsonl": canonical_jsonl_bytes(generations),
        "phase1_eval_records.jsonl": canonical_jsonl_bytes(evaluations),
    }
    source_hashes = {
        name: hashlib.sha256(data).hexdigest()
        for name, data in source_bytes.items()
    }
    monkeypatch.setattr(
        semantic_audit_module, "SOURCE_ARTIFACT_HASHES", source_hashes
    )
    monkeypatch.setattr(exporter, "SOURCE_ARTIFACT_HASHES", source_hashes)
    downloaded, source_evidence = (
        exporter._download_exact_sources_with_verified_evidence(
            _blob_source_service_for_tests(source_bytes),
            "container",
            "source/run",
        )
    )
    assert downloaded == source_bytes
    _REVIEW_SOURCE_HASHES = source_hashes
    _REVIEW_PACK_CACHE = build_review_pack(
        source_bytes["phase1_generations.jsonl"],
        source_bytes["phase1_eval_records.jsonl"],
        source_prefix="source/run",
        output_prefix="semantic/stage",
        protocol_provenance=_test_provenance(),
        source_evidence=source_evidence,
    )
    return deepcopy(_REVIEW_PACK_CACHE)


def _stage1_rows(pack: dict, reviewer_id: str) -> list[dict]:
    packet_hash = pack["manifest"]["packet_files"][STAGE1_PACKET_FILENAME]["sha256"]
    references = {
        row["review_id"]: row["registered_reference_answer"]
        for row in pack["packet_records"][STAGE2_PACKET_FILENAME]
    }
    return [
        {
            "schema_version": STAGE1_JUDGMENT_SCHEMA_VERSION,
            "review_id": review_id,
            "reviewer_id": reviewer_id,
            "reviewer_model_id": REVIEWER_MODEL_ID,
            "reviewer_reasoning_effort": REVIEWER_REASONING_EFFORT,
            "review_stage": "stage1",
            "packet_sha256": packet_hash,
            "stage1_answer_presence": "answer_present",
            "semantic_ambiguity_category": "unambiguous_single_answer",
            "best_answer_if_any": references[review_id],
            "issue_tags": [],
            "confidence": "high",
            "notes": None,
        }
        for review_id in (f"R{index:03d}" for index in range(1, 46))
    ]


def _sealed_stage1(pack: dict, reviewer_id: str):
    packet_hash = pack["manifest"]["packet_files"][STAGE1_PACKET_FILENAME]["sha256"]
    rows = validate_stage1_submission(
        _stage1_rows(pack, reviewer_id), packet_sha256=packet_hash
    )
    data = canonical_jsonl_bytes(rows)
    seal = build_submission_seal(rows, "stage1")
    return validate_sealed_submission(
        data,
        seal,
        expected_stage="stage1",
        expected_packet_sha256=packet_hash,
    )


def _stage2_rows(pack: dict, stage1, reviewer_id: str) -> list[dict]:
    packet_hash = pack["manifest"]["packet_files"][STAGE2_PACKET_FILENAME]["sha256"]
    return [
        {
            "schema_version": STAGE2_JUDGMENT_SCHEMA_VERSION,
            "review_id": row["review_id"],
            "reviewer_id": reviewer_id,
            "reviewer_model_id": REVIEWER_MODEL_ID,
            "reviewer_reasoning_effort": REVIEWER_REASONING_EFFORT,
            "review_stage": "stage2",
            "packet_sha256": packet_hash,
            "answer_status": "correct",
            "notes": None,
        }
        for row in stage1.rows
    ]


def _sealed_stage2(pack: dict, stage1, reviewer_id: str):
    packet_hash = pack["manifest"]["packet_files"][STAGE2_PACKET_FILENAME]["sha256"]
    rows = validate_stage2_submission(
        _stage2_rows(pack, stage1, reviewer_id),
        packet_sha256=packet_hash,
        stage1_rows=stage1.rows,
        stage2_records=pack["packet_records"][STAGE2_PACKET_FILENAME],
    )
    data = canonical_jsonl_bytes(rows)
    seal = build_submission_seal(rows, "stage2")
    return validate_sealed_submission(
        data,
        seal,
        expected_stage="stage2",
        expected_packet_sha256=packet_hash,
        stage1_submission=stage1,
        stage2_records=pack["packet_records"][STAGE2_PACKET_FILENAME],
    )


def _submission_artifact(sealed) -> tuple[bytes, bytes]:
    return canonical_jsonl_bytes(sealed.rows), canonical_json_bytes(sealed.seal)


def _release_validation_bytes(release: dict) -> dict[str, bytes]:
    return {
        RELEASE_RESERVATION_FILENAME: release["files"][
            RELEASE_RESERVATION_FILENAME
        ],
        release["packet_name"]: release["files"][release["packet_name"]],
    }


def _review_pack_for_output(pack: dict, output_prefix: str) -> dict:
    source_bytes = pack["source_bytes"]
    return build_review_pack(
        source_bytes["phase1_generations.jsonl"],
        source_bytes["phase1_eval_records.jsonl"],
        source_prefix=pack["manifest"]["source_prefix"],
        output_prefix=output_prefix,
        protocol_provenance=pack["manifest"]["protocol_provenance"],
        source_evidence=pack["_verified_source_evidence"],
    )


@pytest.fixture
def staged(review_pack):
    stage1_a = _sealed_stage1(review_pack, "reviewer-a")
    stage1_b = _sealed_stage1(review_pack, "reviewer-b")
    stage2_a = _sealed_stage2(review_pack, stage1_a, "reviewer-a")
    stage2_b = _sealed_stage2(review_pack, stage1_b, "reviewer-b")
    return stage1_a, stage1_b, stage2_a, stage2_b


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _provenance_repo(root: Path) -> tuple[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Semantic Audit Test")
    _git(root, "config", "core.autocrlf", "false")
    for relative in PROTOCOL_RUNTIME_FILES:
        path = root.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"frozen:{relative}\n".encode("ascii"))
    (root / ".gitignore").write_text(
        "artifacts/\n.semantic_audit_build_provenance.json\n",
        encoding="ascii",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "freeze protocol")
    return _git(root, "rev-parse", "HEAD"), protocol_bundle_sha256(root)


def test_protocol_provenance_valid_pin_and_ignored_artifacts(workdir):
    commit, bundle = _provenance_repo(workdir / "repo")
    ignored = workdir / "repo" / "artifacts" / "ignored"
    ignored.mkdir(parents=True)
    (ignored / "ignored.txt").write_text("ignored", encoding="ascii")
    result = verify_protocol_provenance(workdir / "repo", commit, bundle)
    assert result["verification_mode"] == "local_git_and_bundle"
    assert result["protocol_commit"] == commit
    assert result["protocol_bundle_sha256"] == bundle
    assert "src/jspace_observation/eval_parsing.py" in result["runtime_files"]
    assert "src/jspace_observation/record_audit.py" in result["runtime_files"]
    assert "src/jspace_observation/__init__.py" in result["runtime_files"]


@pytest.mark.parametrize("commit", ["0" * 40, "abc", "g" * 40, "A" * 40])
def test_protocol_provenance_rejects_zero_or_malformed_commit(workdir, commit):
    with pytest.raises(SemanticAuditError):
        verify_protocol_provenance(workdir, commit, "a" * 64)


def test_protocol_provenance_rejects_nonexistent_local_commit(workdir):
    _, bundle = _provenance_repo(workdir / "repo")
    with pytest.raises(SemanticAuditError, match="does not exist|differs"):
        verify_protocol_provenance(workdir / "repo", "f" * 40, bundle)


def test_protocol_provenance_rejects_wrong_bundle(workdir):
    commit, _ = _provenance_repo(workdir / "repo")
    with pytest.raises(SemanticAuditError, match="bundle SHA-256"):
        verify_protocol_provenance(workdir / "repo", commit, "a" * 64)


def test_protocol_provenance_rejects_uppercase_bundle(workdir):
    commit, _ = _provenance_repo(workdir / "repo")
    with pytest.raises(SemanticAuditError, match="lowercase"):
        verify_protocol_provenance(workdir / "repo", commit, "A" * 64)


def test_protocol_provenance_rejects_dirty_tracked_runtime(workdir):
    commit, _ = _provenance_repo(workdir / "repo")
    target = workdir / "repo" / PROTOCOL_RUNTIME_FILES[-1]
    target.write_bytes(target.read_bytes() + b"dirty\n")
    dirty_bundle = protocol_bundle_sha256(workdir / "repo")
    with pytest.raises(SemanticAuditError, match="must be clean"):
        verify_protocol_provenance(workdir / "repo", commit, dirty_bundle)


def test_exporter_requires_explicit_provenance_env(workdir):
    with pytest.raises(
        (SemanticAuditError, exporter.SemanticAuditBootstrapError),
        match="attestation",
    ):
        exporter.resolve_protocol_provenance(
            {},
            project_root=workdir,
            baked_attestation_path=workdir / "missing-attestation.json",
        )


def _baked_provenance_repo(root: Path) -> tuple[str, Path]:
    commit, _ = _provenance_repo(root)
    attestation = build_preparation.prepare_build_context(root, commit)
    _remove_tree(root / ".git")
    return commit, attestation


def test_build_preparation_and_valid_baked_attestation(workdir):
    root = workdir / "repo"
    commit, attestation = _baked_provenance_repo(root)
    value = build_preparation.validate_attestation(root, attestation)
    assert value["protocol_commit"] == commit
    provenance = verify_protocol_provenance(
        root, commit, baked_attestation_path=attestation
    )
    assert provenance["verification_mode"] == "baked_image_attestation"
    assert provenance["generated_from_clean_git"] is True


def test_build_preparation_rejects_arbitrary_commit(workdir):
    root = workdir / "repo"
    _provenance_repo(root)
    with pytest.raises(
        build_preparation.PreparationError, match="HEAD|commit lookup"
    ):
        build_preparation.prepare_build_context(root, "f" * 40)


def test_build_preparation_rejects_untracked_import_shadow(workdir):
    root = workdir / "repo"
    commit, _ = _provenance_repo(root)
    shadow = root / "src" / "azure"
    shadow.mkdir()
    (shadow / "__init__.py").write_text("shadow = True\n", encoding="ascii")
    with pytest.raises(build_preparation.PreparationError, match="untracked"):
        build_preparation.prepare_build_context(root, commit)


def test_baked_provenance_rejects_missing_wrong_list_and_bundle(workdir):
    missing_root = workdir / "missing"
    _provenance_repo(missing_root)
    _remove_tree(missing_root / ".git")
    with pytest.raises(SemanticAuditError, match="missing"):
        verify_protocol_provenance(
            missing_root,
            baked_attestation_path=missing_root / "missing.json",
        )

    for mutation in ("file_list", "bundle"):
        root = workdir / mutation
        _, attestation = _baked_provenance_repo(root)
        value = semantic_audit_module.parse_json_object_strict(
            attestation.read_bytes(), "attestation"
        )
        if mutation == "file_list":
            value["runtime_files"] = value["runtime_files"][:-1]
        else:
            value["protocol_bundle_sha256"] = "a" * 64
        attestation.write_bytes(canonical_json_bytes(value))
        with pytest.raises(SemanticAuditError, match="attestation|bundle"):
            verify_protocol_provenance(
                root, baked_attestation_path=attestation
            )


def test_baked_attestation_rejects_runtime_commit_override(workdir):
    root = workdir / "repo"
    commit, attestation = _baked_provenance_repo(root)
    assert commit != "f" * 40
    with pytest.raises(SemanticAuditError, match="requested"):
        verify_protocol_provenance(
            root,
            "f" * 40,
            baked_attestation_path=attestation,
        )


def test_shadow_package_origins_are_rejected(workdir):
    fake_path = (
        workdir
        / "site-packages"
        / "azure"
        / "identity.py"
    )
    fake_path.parent.mkdir(parents=True)
    fake_path.write_text("shadow = True\n", encoding="ascii")
    fake_azure = SimpleNamespace(__file__=str(fake_path))
    with pytest.raises(
        exporter.SemanticAuditBootstrapError, match="exact interpreter package root"
    ):
        exporter._require_interpreter_package_origin(fake_azure, "azure.identity")

    shadow_name = "jspace_observation.shadow"
    sys.modules[shadow_name] = SimpleNamespace(
        __file__=str(workdir / "shadow.py")
    )
    try:
        with pytest.raises(
            exporter.SemanticAuditBootstrapError, match="unexpected frozen-module"
        ):
            exporter._verify_frozen_module_origins()
    finally:
        sys.modules.pop(shadow_name, None)


def test_semantic_clis_reject_external_pythonpath_and_nonisolated_flags():
    secure_flags = SimpleNamespace(isolated=1, safe_path=True, no_site=1)
    insecure_flags = SimpleNamespace(isolated=0, safe_path=False, no_site=0)
    for module in (exporter, finalizer):
        with pytest.raises(
            module.SemanticAuditBootstrapError, match="PYTHONPATH"
        ):
            module._require_secure_interpreter(
                {"PYTHONPATH": "C:\\external\\src"}, secure_flags
            )
        with pytest.raises(
            module.SemanticAuditBootstrapError, match="python -I -S"
        ):
            module._require_secure_interpreter({}, insecure_flags)


def test_pack_has_exact_two_packets_45_ids_and_target(review_pack):
    assert set(review_pack["packet_records"]) == {
        STAGE1_PACKET_FILENAME,
        STAGE2_PACKET_FILENAME,
    }
    assert "all45_review_packet_unblinded.jsonl" not in review_pack["packet_records"]
    for records in review_pack["packet_records"].values():
        assert [row["review_id"] for row in records] == [
            f"R{index:03d}" for index in range(1, 46)
        ]
        assert {row["experimental_target_model_id"] for row in records} == {
            EXPERIMENTAL_TARGET_MODEL_ID
        }
    validate_review_pack(review_pack["manifest"], review_pack["packet_bytes"])


def test_preregistered_source_hashes_are_exact():
    assert semantic_audit_module.SOURCE_ARTIFACT_HASHES == {
        "phase1_generations.jsonl": (
            "b45c972af6f8a2be771e308d943ff793bdafd44c486a4eae9ea8a4e7f1ec11a0"
        ),
        "phase1_eval_records.jsonl": (
            "57aee97ef98a9be14e489bf6aa4a6e09a80fd5ceedb2df8fadc8d991be98538b"
        ),
    }


@pytest.mark.parametrize(
    "mode", [None, "caller_attested", SYNTHETIC_TEST_SOURCE_MODE]
)
def test_nonverified_source_modes_cannot_produce_release(review_pack, mode):
    invalid = deepcopy(review_pack)
    if mode is None:
        invalid["manifest"].pop("source_evidence_mode")
    else:
        invalid["manifest"]["source_evidence_mode"] = mode
    with pytest.raises(SemanticAuditError, match="verified_source_bytes"):
        build_release_files(invalid, "stage1")


def test_structurally_consistent_source_mapping_is_not_a_capability(review_pack):
    source_bytes = review_pack["source_bytes"]
    arbitrary_mapping = {
        "source_artifacts": deepcopy(
            review_pack["manifest"]["source_artifacts"]
        ),
        "source_immutability": deepcopy(
            review_pack["manifest"]["source_immutability"]
        ),
    }
    with pytest.raises(SemanticAuditError, match="exporter-minted"):
        build_review_pack(
            source_bytes["phase1_generations.jsonl"],
            source_bytes["phase1_eval_records.jsonl"],
            source_prefix="source/run",
            output_prefix="semantic/stage",
            protocol_provenance=_test_provenance(),
            source_evidence=arbitrary_mapping,
        )


def test_private_synthetic_pack_is_always_release_ineligible():
    generations, evaluations = _source_records()
    synthetic = _build_synthetic_review_pack_for_tests(
        generations,
        evaluations,
        source_prefix="source/run",
        output_prefix="semantic/stage",
        protocol_provenance=_test_provenance(),
    )
    assert (
        synthetic["manifest"]["source_evidence_mode"]
        == SYNTHETIC_TEST_SOURCE_MODE
    )
    with pytest.raises(SemanticAuditError, match="verified_source_bytes"):
        build_release_files(synthetic, "stage1")
    with pytest.raises(SemanticAuditError, match="verified_source_bytes"):
        validate_review_pack(synthetic["manifest"], synthetic["packet_bytes"])


def test_shuffle_is_frozen_deterministic_and_permutation_invariant():
    keys = expected_record_keys()
    first, first_hash = deterministic_review_mapping(keys, FROZEN_SHUFFLE_SEED)
    same, same_hash = deterministic_review_mapping(
        reversed(keys), FROZEN_SHUFFLE_SEED
    )
    assert first == same
    assert first_hash == same_hash
    with pytest.raises(SemanticAuditError, match="frozen value|integer"):
        deterministic_review_mapping(keys, 42)


def test_cli_and_pack_reject_seed_42(review_pack):
    with pytest.raises(SystemExit):
        exporter.parse_args(
            [
                "--release-stage",
                "stage1",
                "--storage-account",
                "a",
                "--container",
                "c",
                "--source-prefix",
                "source/run",
                "--output-prefix",
                "out/stage1",
                "--shuffle-seed",
                "42",
            ]
        )
    generations, evaluations = _source_records()
    with pytest.raises(SemanticAuditError, match="frozen value|integer"):
        _build_synthetic_review_pack_for_tests(
            generations,
            evaluations,
            source_prefix="source/run",
            output_prefix="out/stage1",
            protocol_provenance=_test_provenance(),
            shuffle_seed=42,
        )


def test_stage1_release_contains_only_blinded_packet_and_manifest(review_pack):
    release = build_release_files(review_pack, "stage1")
    assert list(release["files"]) == [
        RELEASE_RESERVATION_FILENAME,
        STAGE1_PACKET_FILENAME,
        RELEASE_MANIFEST_FILENAMES["stage1"],
    ]
    rendered = b"".join(release["files"].values())
    assert STAGE2_PACKET_FILENAME.encode() not in rendered
    assert b"all45_review_packet_unblinded" not in rendered
    records = validate_stage_release(
        release["manifest"],
        _release_validation_bytes(release),
        expected_stage="stage1",
    )
    assert len(records) == 45
    args = exporter.parse_args(
        [
            "--release-stage",
            "stage1",
            "--storage-account",
            "a",
            "--container",
            "c",
            "--source-prefix",
            "source/run",
            "--output-prefix",
            "review/stage1",
            "--output-dir",
            "stage1-output",
        ]
    )
    assert args.print_blinded_packet is False


def test_release_cli_requires_sink_and_completed_stage1():
    common = [
        "--storage-account",
        "a",
        "--container",
        "c",
        "--source-prefix",
        "source/run",
        "--output-prefix",
        "review/stage",
    ]
    with pytest.raises(SystemExit):
        exporter.parse_args(["--release-stage", "stage1", *common])
    with pytest.raises(SystemExit):
        exporter.parse_args(
            [
                "--release-stage",
                "stage2",
                *common,
                "--output-dir",
                "stage2-output",
                "--stage1-reviewer-a",
                "a.jsonl",
                "--stage1-reviewer-a-seal",
                "a.json",
                "--stage1-reviewer-b",
                "b.jsonl",
                "--stage1-reviewer-b-seal",
                "b.json",
            ]
        )


def test_stage2_release_requires_two_distinct_stage1_seals(review_pack, staged):
    stage1_a, stage1_b, _, _ = staged
    stage1_artifacts = (
        _submission_artifact(stage1_a),
        _submission_artifact(stage1_b),
    )
    stage1_release = build_release_files(
        _review_pack_for_output(review_pack, "semantic/release-stage1"),
        "stage1",
    )
    with pytest.raises(SemanticAuditError, match="two sealed"):
        build_release_files(
            review_pack,
            "stage2",
            stage1_release_files=stage1_release["files"],
        )
    with pytest.raises(SemanticAuditError, match="distinct"):
        build_release_files(
            review_pack,
            "stage2",
            stage1_submission_artifacts=(
                _submission_artifact(stage1_a),
                _submission_artifact(stage1_a),
            ),
            stage1_release_files=stage1_release["files"],
        )
    release = build_release_files(
        review_pack,
        "stage2",
        stage1_submission_artifacts=stage1_artifacts,
        stage1_release_files=stage1_release["files"],
    )
    assert list(release["files"]) == [
        RELEASE_RESERVATION_FILENAME,
        STAGE2_PACKET_FILENAME,
        RELEASE_MANIFEST_FILENAMES["stage2"],
    ]
    assert b"all45_review_packet_unblinded" not in b"".join(
        release["files"].values()
    )
    validate_stage_release(
        release["manifest"],
        _release_validation_bytes(release),
        expected_stage="stage2",
        stage1_release_files=stage1_release["files"],
        stage1_submission_artifacts=stage1_artifacts,
    )


def test_fabricated_45_row_submission_cannot_release_stage2(review_pack, staged):
    stage1_a, stage1_b, _, _ = staged
    stage1_release = build_release_files(
        _review_pack_for_output(review_pack, "semantic/release-stage1"),
        "stage1",
    )
    bare_bytes = canonical_jsonl_bytes(
        [{"review_id": f"R{index:03d}"} for index in range(1, 46)]
    )
    fabricated_seal = deepcopy(stage1_a.seal)
    fabricated_seal["submission_sha256"] = sha256_bytes(bare_bytes)
    with pytest.raises(SemanticAuditError):
        build_release_files(
            review_pack,
            "stage2",
            stage1_submission_artifacts=(
                (bare_bytes, canonical_json_bytes(fabricated_seal)),
                _submission_artifact(stage1_b),
            ),
            stage1_release_files=stage1_release["files"],
        )


def test_stage2_requires_validated_stage1_release_bytes(review_pack, staged):
    stage1_a, stage1_b, _, _ = staged
    artifacts = (
        _submission_artifact(stage1_a),
        _submission_artifact(stage1_b),
    )
    with pytest.raises(TypeError):
        build_release_files(
            review_pack,
            "stage2",
            stage1_submission_artifacts=artifacts,
            stage1_release_manifest_sha256="a" * 64,
        )

    stage1_release = build_release_files(
        _review_pack_for_output(review_pack, "semantic/release-stage1"),
        "stage1",
    )
    tampered = dict(stage1_release["files"])
    tampered[STAGE1_PACKET_FILENAME] += b"\n"
    with pytest.raises(SemanticAuditError):
        build_release_files(
            review_pack,
            "stage2",
            stage1_submission_artifacts=artifacts,
            stage1_release_files=tampered,
        )


def test_strict_integer_bindings_reject_float_and_bool(review_pack, staged):
    keys = expected_record_keys()
    for value in (float(FROZEN_SHUFFLE_SEED), True):
        with pytest.raises(SemanticAuditError, match="integer"):
            deterministic_review_mapping(keys, value)

    generations, evaluations = _source_records()
    with pytest.raises(SemanticAuditError, match="integer"):
        _build_synthetic_review_pack_for_tests(
            generations,
            evaluations,
            source_prefix="source/run",
            output_prefix="semantic/stage",
            protocol_provenance=_test_provenance(),
            expected_records=45.0,
        )

    release = build_release_files(review_pack, "stage1")
    for field in ("expected_record_count", "shuffle_seed", "record_count"):
        manifest = deepcopy(release["manifest"])
        if field == "expected_record_count":
            manifest["expected_record_count"] = 45.0
        elif field == "shuffle_seed":
            manifest["shuffle"]["seed"] = float(FROZEN_SHUFFLE_SEED)
        else:
            manifest["packet_files"][STAGE1_PACKET_FILENAME][
                "record_count"
            ] = 45.0
        with pytest.raises(SemanticAuditError, match="integer"):
            validate_stage_release(
                manifest,
                _release_validation_bytes(release),
                expected_stage="stage1",
            )

    stage1_a, _, _, _ = staged
    submission_bytes, seal_bytes = _submission_artifact(stage1_a)
    seal = semantic_audit_module.parse_json_object_strict(seal_bytes, "seal")
    seal["record_count"] = 45.0
    with pytest.raises(SemanticAuditError, match="integer"):
        validate_submission_artifact(
            submission_bytes,
            canonical_json_bytes(seal),
            expected_stage="stage1",
            expected_packet_sha256=stage1_a.packet_sha256,
        )


def test_release_manifest_rejects_concealed_extra_fields(review_pack):
    release = build_release_files(review_pack, "stage1")
    leaked = deepcopy(release["manifest"])
    leaked["registered_reference_answer"] = "12"
    with pytest.raises(SemanticAuditError, match="exact schema"):
        validate_stage_release(
            leaked,
            _release_validation_bytes(release),
            expected_stage="stage1",
        )


@pytest.mark.parametrize("mutation", ["schema", "nested_output"])
def test_stage1_release_rejects_invalid_value_schema(review_pack, mutation):
    release = build_release_files(review_pack, "stage1")
    records = deepcopy(release["packet_records"])
    if mutation == "schema":
        records[0]["schema_version"] = "wrong"
    else:
        records[0]["outputs"]["raw_output"] = {"storedCorrectness": True}
    packet = canonical_jsonl_bytes(records)
    manifest = deepcopy(release["manifest"])
    manifest["packet_files"][STAGE1_PACKET_FILENAME]["sha256"] = sha256_bytes(
        packet
    )
    with pytest.raises(SemanticAuditError):
        validate_stage_release(
            manifest,
            {
                RELEASE_RESERVATION_FILENAME: release["files"][
                    RELEASE_RESERVATION_FILENAME
                ],
                STAGE1_PACKET_FILENAME: packet,
            },
            expected_stage="stage1",
        )


def test_release_upload_plans_exclude_forbidden_files():
    stage1 = exporter.planned_release_uploads("review/stage1", "stage1")
    stage2 = exporter.planned_release_uploads("review/stage2", "stage2")
    assert [Path(name).name for name in stage1] == [
        RELEASE_RESERVATION_FILENAME,
        STAGE1_PACKET_FILENAME,
        RELEASE_MANIFEST_FILENAMES["stage1"],
    ]
    assert [Path(name).name for name in stage2] == [
        RELEASE_RESERVATION_FILENAME,
        STAGE2_PACKET_FILENAME,
        RELEASE_MANIFEST_FILENAMES["stage2"],
    ]
    assert all("unblinded" not in name for name in [*stage1, *stage2])


def test_blob_stage1_gate_rejects_extra_prefix_members(review_pack):
    release = build_release_files(review_pack, "stage1")
    prefix = "review/stage1"

    class Container:
        def list_blobs(self, **kwargs):
            return iter(
                [
                    {"name": f"{prefix}/{RELEASE_RESERVATION_FILENAME}"},
                    {"name": f"{prefix}/{STAGE1_PACKET_FILENAME}"},
                    {
                        "name": (
                            f"{prefix}/"
                            f"{RELEASE_MANIFEST_FILENAMES['stage1']}"
                        )
                    },
                    {"name": f"{prefix}/{STAGE2_PACKET_FILENAME}"},
                ]
            )

    class Service:
        def get_container_client(self, container):
            return Container()

        def get_blob_client(self, **kwargs):
            raise AssertionError("contaminated prefix must fail before download")

    args = SimpleNamespace(
        stage1_release_dir=None,
        stage1_release_prefix=prefix,
        container="container",
    )
    with pytest.raises(SemanticAuditError, match="exactly"):
        exporter._read_completed_stage1_release(args, Service())


def test_private_integration_requires_both_stage2_seals(review_pack, staged):
    generations, evaluations = _source_records()
    stage1_a, stage1_b, stage2_a, stage2_b = staged
    stage1_artifacts = (
        _submission_artifact(stage1_a),
        _submission_artifact(stage1_b),
    )
    stage2_artifacts = (
        _submission_artifact(stage2_a),
        _submission_artifact(stage2_b),
    )
    stage1_release = build_release_files(
        _review_pack_for_output(review_pack, "semantic/release-stage1"),
        "stage1",
    )
    stage2_release = build_release_files(
        review_pack,
        "stage2",
        stage1_release_files=stage1_release["files"],
        stage1_submission_artifacts=stage1_artifacts,
    )
    with pytest.raises(SemanticAuditError, match="requires"):
        finalizer._construct_private_records(
            generations,
            evaluations,
            stage1_release_files=stage1_release["files"],
            stage2_release_files=stage2_release["files"],
            stage1_submission_artifacts=stage1_artifacts,
            stage2_submission_artifacts=stage2_artifacts[:1],
        )
    tampered_stage2 = (
        (
            stage2_artifacts[0][0].replace(
                b'"answer_status":"correct"',
                b'"answer_status":"incorrect"',
                1,
            ),
            stage2_artifacts[0][1],
        ),
        stage2_artifacts[1],
    )
    with pytest.raises(SemanticAuditError):
        finalizer._construct_private_records(
            generations,
            evaluations,
            stage1_release_files=stage1_release["files"],
            stage2_release_files=stage2_release["files"],
            stage1_submission_artifacts=stage1_artifacts,
            stage2_submission_artifacts=tampered_stage2,
        )
    tampered_release = dict(stage2_release["files"])
    tampered_release[STAGE2_PACKET_FILENAME] += b"\n"
    with pytest.raises(SemanticAuditError):
        finalizer._construct_private_records(
            generations,
            evaluations,
            stage1_release_files=stage1_release["files"],
            stage2_release_files=tampered_release,
            stage1_submission_artifacts=stage1_artifacts,
            stage2_submission_artifacts=stage2_artifacts,
        )
    records, *_ = finalizer._construct_private_records(
        generations,
        evaluations,
        stage1_release_files=stage1_release["files"],
        stage2_release_files=stage2_release["files"],
        stage1_submission_artifacts=stage1_artifacts,
        stage2_submission_artifacts=stage2_artifacts,
    )
    assert len(records) == 45


def test_bare_rows_and_missing_bindings_are_rejected(review_pack):
    bare = [{"review_id": f"R{index:03d}"} for index in range(1, 46)]
    with pytest.raises(SemanticAuditError, match="bare combined"):
        validate_reviewer_submission(bare)
    rows = _stage1_rows(review_pack, "reviewer-a")
    rows[0].pop("packet_sha256")
    with pytest.raises(SemanticAuditError, match="exact schema"):
        validate_stage1_submission(
            rows,
            packet_sha256=review_pack["manifest"]["packet_files"][
                STAGE1_PACKET_FILENAME
            ]["sha256"],
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reviewer_model_id", "other"),
        ("reviewer_reasoning_effort", "high"),
        ("review_stage", "stage2"),
        ("schema_version", "wrong"),
        ("packet_sha256", "a" * 64),
    ],
)
def test_stage1_rejects_wrong_binding(review_pack, field, value):
    rows = _stage1_rows(review_pack, "reviewer-a")
    rows[0][field] = value
    with pytest.raises(SemanticAuditError):
        validate_stage1_submission(
            rows,
            packet_sha256=review_pack["manifest"]["packet_files"][
                STAGE1_PACKET_FILENAME
            ]["sha256"],
        )


def test_stage2_identity_continuity_and_no_stage1_revision(review_pack):
    stage1 = _sealed_stage1(review_pack, "reviewer-a")
    packet_hash = review_pack["manifest"]["packet_files"][STAGE2_PACKET_FILENAME][
        "sha256"
    ]
    rows = _stage2_rows(review_pack, stage1, "other-reviewer")
    with pytest.raises(SemanticAuditError, match="differs from Stage 1"):
        validate_stage2_submission(
            rows,
            packet_sha256=packet_hash,
            stage1_rows=stage1.rows,
            stage2_records=review_pack["packet_records"][STAGE2_PACKET_FILENAME],
        )
    rows = _stage2_rows(review_pack, stage1, "reviewer-a")
    rows[0]["stage1_answer_presence"] = "no_answer"
    with pytest.raises(SemanticAuditError, match="exact schema"):
        validate_stage2_submission(
            rows,
            packet_sha256=packet_hash,
            stage1_rows=stage1.rows,
            stage2_records=review_pack["packet_records"][STAGE2_PACKET_FILENAME],
        )


def test_submission_seal_hash_mismatch_fails(review_pack):
    stage1 = _sealed_stage1(review_pack, "reviewer-a")
    data = canonical_jsonl_bytes(stage1.rows)
    seal = deepcopy(stage1.seal)
    seal["submission_sha256"] = "a" * 64
    with pytest.raises(SemanticAuditError, match="seal"):
        validate_sealed_submission(
            data,
            seal,
            expected_stage="stage1",
            expected_packet_sha256=stage1.packet_sha256,
        )


def test_arbiter_must_be_distinct_and_bound(review_pack, staged):
    stage1_a, stage1_b, stage2_a, stage2_b = staged
    reviewer_a = combine_staged_submission(stage1_a, stage2_a)
    reviewer_b = combine_staged_submission(stage1_b, stage2_b)
    reviewer_b[0]["issue_tags"] = ["other"]
    generations, evaluations = _source_records()
    restricted = _build_restricted_records(
        generations,
        evaluations,
        review_pack,
        stage1_a=stage1_a,
        stage1_b=stage1_b,
        stage2_a=stage2_a,
        stage2_b=stage2_b,
    )
    triggers = determine_arbitration_triggers(reviewer_a, reviewer_b, restricted)
    packet = build_blinded_arbitration_packet(
        review_pack["packet_records"][STAGE1_PACKET_FILENAME],
        review_pack["packet_records"][STAGE2_PACKET_FILENAME],
        reviewer_a,
        reviewer_b,
        triggers,
    )
    packet_hash = sha256_bytes(canonical_jsonl_bytes(packet))
    reference = review_pack["packet_records"][STAGE2_PACKET_FILENAME][0][
        "registered_reference_answer"
    ]
    row = {
        "schema_version": ARBITRATION_JUDGMENT_SCHEMA_VERSION,
        "review_id": "R001",
        "reviewer_id": "reviewer-a",
        "reviewer_model_id": REVIEWER_MODEL_ID,
        "reviewer_reasoning_effort": REVIEWER_REASONING_EFFORT,
        "review_stage": "arbitration",
        "packet_sha256": packet_hash,
        "semantic_category": "unambiguous_single_answer",
        "answer_presence": "answer_present",
        "answer_status": "correct",
        "best_answer": reference,
        "issue_tags": [],
        "confidence": "high",
        "notes": None,
    }
    with pytest.raises(SemanticAuditError, match="differ"):
        validate_arbiter_submission(
            [row],
            packet_sha256=packet_hash,
            expected_ids=["R001"],
            reviewer_ids=["reviewer-a", "reviewer-b"],
            stage2_records=review_pack["packet_records"][STAGE2_PACKET_FILENAME],
        )
    row["reviewer_id"] = "arbiter"
    validated = validate_arbiter_submission(
        [row],
        packet_sha256=packet_hash,
        expected_ids=["R001"],
        reviewer_ids=["reviewer-a", "reviewer-b"],
        stage2_records=review_pack["packet_records"][STAGE2_PACKET_FILENAME],
    )
    assert validated[0]["packet_sha256"] == packet_hash


def _confusion_row(
    *,
    category: str,
    presence: str,
    status: str,
    stored: bool,
    condition: str = "visible_cot",
    branch: str = "visible_reasoning_control",
    depth: int = 1,
) -> dict:
    return {
        "semantic_category": category,
        "answer_presence": presence,
        "answer_status": status,
        "best_answer": "1" if presence == "answer_present" else None,
        "issue_tags": [],
        "confidence": "high",
        "stored_parse_ambiguous": stored,
        "condition": condition,
        "branch": branch,
        "depth": depth,
    }


def test_truncated_inconclusive_is_unresolved_not_tn_or_fp():
    row = _confusion_row(
        category="incomplete_or_truncated",
        presence="inconclusive",
        status="inconclusive",
        stored=True,
    )
    result = compute_ambiguity_confusion_matrix([row])
    assert result["counts"]["unresolved"] == 1
    assert result["counts"]["fp"] == 0
    assert result["counts"]["tn"] == 0
    assert result["rates_available"] is False


def test_one_unresolved_suppresses_every_overall_and_group_rate():
    rows = [
        _confusion_row(
            category="unambiguous_single_answer",
            presence="answer_present",
            status="correct",
            stored=False,
            condition="visible_cot",
            branch="visible_reasoning_control",
            depth=1,
        ),
        _confusion_row(
            category="review_inconclusive",
            presence="inconclusive",
            status="inconclusive",
            stored=False,
            condition="r1_style_thinking",
            branch="visible_reasoning_control",
            depth=2,
        ),
    ]
    report = build_ambiguity_confusion_report(rows)
    matrices = [
        report["overall"],
        *report["by_condition"].values(),
        *report["by_branch"].values(),
        *report["by_depth"].values(),
    ]
    assert all(matrix["rates_available"] is False for matrix in matrices)
    assert all(
        metric["value"] is None
        for matrix in matrices
        for metric in matrix["rates"].values()
    )


def test_invalid_stored_ambiguity_uses_same_global_unresolved_gate():
    rows = [
        _confusion_row(
            category="unambiguous_single_answer",
            presence="answer_present",
            status="correct",
            stored=False,
            condition="visible_cot",
        ),
        _confusion_row(
            category="unambiguous_single_answer",
            presence="answer_present",
            status="correct",
            stored=False,
            condition="r1_style_thinking",
        ),
    ]
    rows[1]["stored_parse_ambiguous"] = None
    report = build_ambiguity_confusion_report(rows)
    assert report["overall"]["counts"]["unresolved"] == 1
    assert all(
        matrix["rates_available"] is False
        for matrix in report["by_condition"].values()
    )


def test_only_true_multiple_candidate_is_ambiguity_positive():
    assert derive_parser_label(True, "no_answer") == "parser_overflag"
    assert (
        derive_parser_label(True, "incomplete_or_truncated")
        == "parser_overflag"
    )
    assert (
        derive_parser_label(True, "true_multiple_candidate_ambiguity")
        == "correct_flag"
    )


def test_missing_or_invalid_final_field_is_unresolved():
    row = _confusion_row(
        category="unambiguous_single_answer",
        presence="answer_present",
        status="correct",
        stored=False,
    )
    row.pop("confidence")
    result = compute_ambiguity_confusion_matrix([row])
    assert result["counts"]["unresolved"] == 1


def test_stale_final_output_directory_fails(workdir):
    output = workdir / "final"
    output.mkdir()
    (output / "all45_semantic_audit_metrics.csv").write_text(
        "stale\n", encoding="ascii"
    )
    with pytest.raises(SemanticAuditError, match="new or empty"):
        finalizer._require_new_output_dir(output)


def test_missing_required_arbitration_is_explicit_nonzero():
    exit_code, status = finalizer.incomplete_arbitration_status(
        [{"review_id": "R001", "reasons": ["issue_set_difference"]}], "a" * 64
    )
    assert exit_code != 0
    assert status["status"] == "incomplete_awaiting_arbitration"
    assert status["final_metrics_emitted"] is False


def test_material_breakdowns_keep_four_measures_separate():
    rows = [
        {
            "review_id": "R001",
            "issue_tags": ["last_number_selection_risk"],
            "parsed_answer_consistency": "stored_matches_semantic_best",
            "material_correctness_error": False,
            "material_evaluator_error": False,
            "condition": "visible_cot",
            "branch": "visible_reasoning_control",
            "depth": 1,
            "answer_status": "correct",
            "answer_presence": "answer_present",
            "best_answer": "1",
            "confidence": "high",
            "semantic_category": "unambiguous_single_answer",
        },
        {
            "review_id": "R002",
            "issue_tags": [],
            "parsed_answer_consistency": "stored_differs_from_semantic_best",
            "material_correctness_error": True,
            "material_evaluator_error": True,
            "condition": "r1_style_thinking",
            "branch": "visible_reasoning_control",
            "depth": 2,
            "answer_status": "incorrect",
            "answer_presence": "answer_present",
            "best_answer": "2",
            "confidence": "high",
            "semantic_category": "unambiguous_single_answer",
        },
    ]
    report = build_material_impact_report(rows, None)
    assert report["distinctions"]["last_number_risk_tag"]["count"] == 1
    assert report["distinctions"]["observed_extraction_error"]["count"] == 1
    assert report["distinctions"]["material_correctness_error"]["count"] == 1
    breakdowns = report["material_breakdowns"]
    assert (
        breakdowns["last_number_selection_risk"]["by_condition"]["visible_cot"]
        == 1
    )
    assert (
        breakdowns["observed_extraction_error"]["by_condition"]["visible_cot"]
        == 0
    )
    assert (
        breakdowns["material_evaluator_error"]["by_depth"]["2"] == 1
    )


def test_parser_metric_disagreement_is_material_in_every_condition(
    review_pack, staged
):
    generations, evaluations = _source_records()
    stage1_a, stage1_b, stage2_a, stage2_b = staged
    restricted = _build_restricted_records(
        generations,
        evaluations,
        review_pack,
        stage1_a=stage1_a,
        stage1_b=stage1_b,
        stage2_a=stage2_a,
        stage2_b=stage2_b,
    )
    target = next(
        row
        for row in restricted
        if row["stage1_record"]["task"]["condition"] == "r1_style_thinking"
    )
    target["stored_evaluation_fields"]["parse_ambiguous"] = True
    reviewer_a = combine_staged_submission(stage1_a, stage2_a)
    reviewer_b = combine_staged_submission(stage1_b, stage2_b)
    final = enrich_final_adjudications(
        merge_final_judgments(reviewer_a, reviewer_b, [], []), restricted
    )
    enriched = next(row for row in final if row["review_id"] == target["review_id"])
    assert enriched["material_correctness_error"] is False
    assert enriched["material_parser_metric_error"] is True
    assert enriched["material_evaluator_error"] is True


def test_recursive_stage1_leakage_scan(review_pack):
    blinded = deepcopy(
        review_pack["packet_records"][STAGE1_PACKET_FILENAME][0]
    )
    blinded["outputs"]["nested"] = {"stored_correctness": True}
    findings = scan_blinded_forbidden_fields(blinded)
    assert any("stored_correctness" in finding for finding in findings)
    assert scan_blinded_forbidden_fields({"storedCorrectness": True})


def test_canonical_jsonl_and_nonfinite_rejection():
    data = canonical_jsonl_bytes([{"review_id": "R001", "output": "a\nb"}])
    assert len(data.splitlines()) == 1
    assert parse_jsonl_strict(data, "test.jsonl")[0]["output"] == "a\nb"
    with pytest.raises(SemanticAuditError):
        canonical_jsonl_bytes([{"value": math.nan}])


@pytest.mark.parametrize(
    ("source", "output"),
    [
        ("source/run", "source/run/audit"),
        ("source/run/audit", "source/run"),
        ("source/run", "source/run"),
        ("source/run", r"audit\source"),
        ("source/run", "audit//source"),
    ],
)
def test_prefix_overlap_and_normalization_fail_closed(source, output):
    with pytest.raises(SemanticAuditError):
        validate_semantic_audit_prefixes(source, output)


def test_numeric_canonicalization_and_comma_policy():
    assert normalize_numeric_answer("+001.2300") == "1.23"
    assert normalize_numeric_answer("-0.000") == "0"
    assert normalize_numeric_answer("1e3") == "1000"
    for invalid in ("1,000", "1+2", "NaN", "Infinity", ""):
        with pytest.raises(SemanticAuditError):
            normalize_numeric_answer(invalid)


def test_question_and_full_prompt_registry_verification(review_pack):
    generations, evaluations = _source_records()
    generations[0]["prompt"] += " changed"
    with pytest.raises(SemanticAuditError, match="prompt/reference"):
        _build_synthetic_review_pack_for_tests(
            generations,
            evaluations,
            source_prefix="source/run",
            output_prefix="semantic/stage",
            protocol_provenance=_test_provenance(),
        )


def test_agreement_kappa_jaccard_and_na(review_pack, staged):
    stage1_a, stage1_b, stage2_a, stage2_b = staged
    reviewer_a = combine_staged_submission(stage1_a, stage2_a)
    reviewer_b = combine_staged_submission(stage1_b, stage2_b)
    reviewer_b[0]["issue_tags"] = ["other"]
    reviewer_b[0]["confidence"] = "medium"
    agreement = compute_reviewer_agreement(reviewer_a, reviewer_b)
    assert agreement["best_answer"]["overall_exact"]["matches"] == 45
    assert agreement["issue_tags"]["exact"]["matches"] == 44
    assert agreement["issue_tags"]["mean_jaccard"]["value"] == pytest.approx(
        44 / 45
    )
    assert nominal_cohen_kappa(["x", "x"], ["x", "x"])["display"] == "NA"


def test_correctness_table_keeps_full_states():
    statuses = ANSWER_STATUS_LABELS
    stored_states = ("true", "false", "null", "missing", "invalid")
    rows = []
    for index, (status, stored) in enumerate(zip(statuses, stored_states)):
        presence = (
            "answer_present"
            if status in {"correct", "incorrect"}
            else "ambiguous"
            if status == "ambiguous"
            else status
        )
        category = (
            "unambiguous_single_answer"
            if presence == "answer_present"
            else "true_multiple_candidate_ambiguity"
            if presence == "ambiguous"
            else "no_answer"
            if presence == "no_answer"
            else "review_inconclusive"
        )
        rows.append(
            {
                "review_id": f"R{index + 1:03d}",
                "answer_status": status,
                "answer_presence": presence,
                "semantic_category": category,
                "best_answer": "1" if presence == "answer_present" else None,
                "issue_tags": [],
                "confidence": "high",
                "stored_correctness_state": stored,
            }
        )
    table = build_correctness_confusion_table(rows)
    assert table["counts"]["ambiguous"]["null"] == 1
    assert table["counts"]["no_answer"]["missing"] == 1
    assert table["counts"]["inconclusive"]["invalid"] == 1


def test_zero_accuracy_is_not_rendered_as_na():
    final = [
        {
            "depth": 1,
            "condition": "visible_cot",
            "branch": "visible_reasoning_control",
            "answer_status": "incorrect",
            "answer_presence": "answer_present",
            "semantic_category": "unambiguous_single_answer",
            "best_answer": "1",
            "issue_tags": [],
            "confidence": "high",
        }
    ]
    metric = {
        "model": EXPERIMENTAL_TARGET_MODEL_ID,
        "task_family": "arithmetic",
        "depth": 1,
        "condition": "visible_cot",
        "accuracy": 0.0,
        "parse_valid_rate": 0.0,
        "parse_ambiguous_rate": 0.0,
        "accuracy_raw": 0.0,
        "accuracy_stopped": "NA",
        "accuracy_postprocessed": "NA",
    }
    alternatives = {
        "stored_recomputed_metric_rows": [metric],
        "audit_only_semantic_alternative_metric_rows": [deepcopy(metric)],
    }
    rows = list(
        csv.DictReader(
            io.StringIO(
                render_semantic_audit_metrics_csv(final, alternatives).decode()
            )
        )
    )
    assert rows[0]["stored_recomputed_accuracy"] == "0.0"
    assert rows[0]["audit_only_semantic_alternative_accuracy"] == "0.0"


def test_final_machine_outputs_are_complete_and_audit_only(review_pack, staged):
    generations, evaluations = _source_records()
    stage1_a, stage1_b, stage2_a, stage2_b = staged
    reviewer_a = combine_staged_submission(stage1_a, stage2_a)
    reviewer_b = combine_staged_submission(stage1_b, stage2_b)
    restricted = _build_restricted_records(
        generations,
        evaluations,
        review_pack,
        stage1_a=stage1_a,
        stage1_b=stage1_b,
        stage2_a=stage2_a,
        stage2_b=stage2_b,
    )
    triggers = determine_arbitration_triggers(reviewer_a, reviewer_b, restricted)
    assert triggers == []
    final = enrich_final_adjudications(
        merge_final_judgments(reviewer_a, reviewer_b, [], []), restricted
    )
    outputs = build_final_machine_outputs(
        manifest_bytes=review_pack["manifest_bytes"],
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        arbiter=[],
        final_records=final,
        agreement=compute_reviewer_agreement(reviewer_a, reviewer_b),
        triggers=[],
        unblinded_records=restricted,
    )
    assert set(outputs) == {
        "all45_review_manifest.json",
        "all45_reviewer_a.jsonl",
        "all45_reviewer_b.jsonl",
        "all45_arbitration.jsonl",
        "all45_final_semantic_adjudication.jsonl",
        "all45_ambiguity_confusion_matrix.json",
        "all45_correctness_confusion_matrix.json",
        "all45_semantic_audit_metrics.csv",
        "all45_material_impact.json",
    }
    assert b"audit-only semantic alternative estimate" in outputs[
        "all45_semantic_audit_metrics.csv"
    ]
    assert b'"official_stored_metrics_or_classifications_modified":false' in outputs[
        "all45_material_impact.json"
    ]


def test_source_hash_mismatch_fails_before_release():
    class Download:
        def readall(self):
            return b"wrong"

    class Blob:
        def get_blob_properties(self):
            return SimpleNamespace(
                size=5, etag='"etag"', last_modified=None, version_id=None
            )

        def download_blob(self, **kwargs):
            return Download()

    class Service:
        def get_blob_client(self, **kwargs):
            return Blob()

    with pytest.raises(SemanticAuditError, match="SHA-256"):
        exporter._download_exact_sources_with_verified_evidence(
            Service(), "container", "source/run"
        )


def test_upload_checks_all_destinations_manifest_last_and_overwrite_false(review_pack):
    release = build_release_files(review_pack, "stage1")
    uploads: list[tuple[str, bool]] = []
    lease_events: list[str] = []
    store: dict[str, bytes] = {}

    class Download:
        def __init__(self, data):
            self.data = data

        def readall(self):
            return self.data

    class Blob:
        def __init__(self, name):
            self.name = name

        def upload_blob(self, data, overwrite):
            if self.name in store:
                raise FileExistsError(self.name)
            uploads.append((self.name, overwrite))
            store[self.name] = data

        def download_blob(self, **kwargs):
            return Download(store[self.name])

        def acquire_lease(self):
            lease_events.append("acquired")

            class Lease:
                def release(self):
                    lease_events.append("released")

            return Lease()

    blobs: dict[str, Blob] = {}

    class Service:
        def get_blob_client(self, *, container, blob):
            blobs.setdefault(blob, Blob(blob))
            return blobs[blob]

        def get_container_client(self, container):
            return SimpleNamespace(
                list_blobs=lambda **kwargs: iter(
                    {"name": name}
                    for name in sorted(store)
                    if name.startswith(kwargs["name_starts_with"])
                )
            )

    exporter.upload_release(
        Service(), "container", "new/stage1", "stage1", release["files"]
    )
    assert [Path(name).name for name, _ in uploads] == [
        RELEASE_RESERVATION_FILENAME,
        STAGE1_PACKET_FILENAME,
        RELEASE_MANIFEST_FILENAMES["stage1"],
    ]
    assert all(overwrite is False for _, overwrite in uploads)
    assert lease_events == ["acquired", "released"]


def test_upload_rejects_nonempty_blob_prefix_before_any_destination_write(review_pack):
    release = build_release_files(review_pack, "stage1")
    uploads: list[str] = []

    class Blob:
        def exists(self):
            return False

        def upload_blob(self, data, overwrite):
            uploads.append("unexpected")

    class Service:
        def get_container_client(self, container):
            return SimpleNamespace(
                list_blobs=lambda **kwargs: iter([{"name": "existing"}])
            )

        def get_blob_client(self, *, container, blob):
            return Blob()

    with pytest.raises(SemanticAuditError, match="entirely new"):
        exporter.upload_release(
            Service(), "container", "existing/stage1", "stage1", release["files"]
        )
    assert uploads == []


def test_concurrent_exporter_cannot_win_reserved_prefix(review_pack):
    release = build_release_files(review_pack, "stage1")
    prefix = "race/stage1"
    store: dict[str, bytes] = {}

    class Download:
        def __init__(self, data):
            self.data = data

        def readall(self):
            return self.data

    class Blob:
        def __init__(self, name):
            self.name = name

        def upload_blob(self, data, overwrite):
            if self.name in store:
                raise FileExistsError(self.name)
            store[self.name] = data

        def download_blob(self, **kwargs):
            return Download(store[self.name])

    class Container:
        stale_once = False

        def list_blobs(self, **kwargs):
            if self.stale_once:
                self.stale_once = False
                return iter(())
            return iter(
                {"name": name}
                for name in sorted(store)
                if name.startswith(kwargs["name_starts_with"])
            )

    container_client = Container()

    class Service:
        def get_container_client(self, container):
            return container_client

        def get_blob_client(self, *, container, blob):
            return Blob(blob)

    service = Service()
    exporter.upload_release(
        service, "container", prefix, "stage1", release["files"]
    )
    container_client.stale_once = True
    with pytest.raises(SemanticAuditError, match="reservation"):
        exporter.upload_release(
            service, "container", prefix, "stage1", release["files"]
        )


def test_extra_blob_prevents_manifest_completion(review_pack):
    release = build_release_files(review_pack, "stage1")
    prefix = "extra/stage1"
    store: dict[str, bytes] = {}
    packet_blob = f"{prefix}/{STAGE1_PACKET_FILENAME}"
    manifest_blob = f"{prefix}/{RELEASE_MANIFEST_FILENAMES['stage1']}"

    class Download:
        def __init__(self, data):
            self.data = data

        def readall(self):
            return self.data

    class Blob:
        def __init__(self, name):
            self.name = name

        def upload_blob(self, data, overwrite):
            if self.name in store:
                raise FileExistsError(self.name)
            store[self.name] = data
            if self.name == packet_blob:
                store[f"{prefix}/unexpected.json"] = b"{}\n"

        def download_blob(self, **kwargs):
            return Download(store[self.name])

    class Service:
        def get_container_client(self, container):
            return SimpleNamespace(
                list_blobs=lambda **kwargs: iter(
                    {"name": name}
                    for name in sorted(store)
                    if name.startswith(kwargs["name_starts_with"])
                )
            )

        def get_blob_client(self, *, container, blob):
            return Blob(blob)

    with pytest.raises(SemanticAuditError, match="before manifest"):
        exporter.upload_release(
            Service(), "container", prefix, "stage1", release["files"]
        )
    assert manifest_blob not in store
    assert f"{prefix}/{RELEASE_RESERVATION_FILENAME}" in store


def test_local_release_and_final_writers_use_exclusive_destinations(
    review_pack, workdir
):
    release = build_release_files(review_pack, "stage1")
    release_dir = workdir / "release"
    exporter._write_release(str(release_dir), release["files"])
    with pytest.raises(SemanticAuditError, match="new or empty"):
        exporter._write_release(str(release_dir), release["files"])

    final_dir = workdir / "final"
    files = {"payload.json": b"{}\n", "marker.json": b"{}\n"}
    finalizer._write_verified_new(
        final_dir, files, manifest_last="marker.json"
    )
    with pytest.raises(SemanticAuditError, match="new or empty"):
        finalizer._write_verified_new(
            final_dir, files, manifest_last="marker.json"
        )


def test_manifest_contains_verbatim_boundary_and_provenance(review_pack):
    assert review_pack["manifest"]["mandatory_boundary"] == MANDATORY_BOUNDARY_TEXT
    assert review_pack["manifest"]["source_evidence_sha256"] == sha256_bytes(
        canonical_json_bytes(
            {
                "source_artifacts": review_pack["manifest"]["source_artifacts"],
                "source_immutability": review_pack["manifest"][
                    "source_immutability"
                ],
            }
        )
    )
    protocol = (ROOT / "docs" / "phase1_semantic_review_protocol.md").read_text(
        encoding="utf-8"
    )
    assert MANDATORY_BOUNDARY_TEXT in protocol
    assert review_pack["manifest"]["protocol_bundle_sha256"] == protocol_bundle_sha256(
        ROOT
    )


def test_docker_and_acr_use_baked_attestation_not_bundle_env():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    helper = (
        ROOT / "infra" / "azure" / "scripts" / "06_run_job_acr_mi.sh"
    ).read_text(encoding="utf-8")
    build_helper = (
        ROOT / "infra" / "azure" / "scripts" / "01_build_and_push_image.sh"
    ).read_text(encoding="utf-8")
    assert "ARG JSPACE_SEMANTIC_PROTOCOL" not in dockerfile
    assert "JSPACE_SEMANTIC_PROTOCOL_BUNDLE_SHA256" not in dockerfile
    assert "JSPACE_SEMANTIC_PROTOCOL_BUNDLE_SHA256" not in helper
    assert "JSPACE_SEMANTIC_PROTOCOL_COMMIT" in helper
    assert ".semantic_audit_build_provenance.json" in dockerfile
    assert "--validate-attestation" in dockerfile
    assert "useradd --system --uid 10001" in dockerfile
    assert "COPY --chown=0:0 . /workspace" in dockerfile
    assert "chown -R 0:0 /workspace /opt/jspace" in dockerfile
    assert "chmod -R a-w /workspace /opt/jspace" in dockerfile
    assert dockerfile.index("--validate-attestation") < dockerfile.index(
        "chmod -R a-w /workspace /opt/jspace"
    )
    assert dockerfile.index("chmod -R a-w /workspace /opt/jspace") < (
        dockerfile.index("USER jspace")
    )
    assert "HF_HOME=/tmp/models/huggingface" in dockerfile
    assert "RESULTS_DIR=/tmp/results" in dockerfile
    assert "TMPDIR=/tmp/jspace-tmp" in dockerfile
    assert "chmod 0755 /tmp" in dockerfile
    assert "USER jspace" in dockerfile
    assert "python -I -S" in helper
    assert "env -u PYTHONPATH" in helper
    assert 'semantic_audit_mode.lower() != "true"' in helper
    assert "prepare_semantic_audit_build_context.py" in build_helper
    assert "env -u PYTHONPATH python -I -S" in build_helper
    assert "trap cleanup_attestation EXIT" in build_helper
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "**/all45_*" in dockerignore
    assert "!.semantic_audit_build_provenance.json" in dockerignore
    assert "python -I -S" in dockerfile
    assert Path(exporter._semantic_audit_module.__file__).resolve() == (
        ROOT / "src" / "jspace_observation" / "semantic_audit.py"
    ).resolve()


def test_closed_vocab_constants_are_exact():
    assert ANSWER_STATUS_LABELS == (
        "correct",
        "incorrect",
        "ambiguous",
        "no_answer",
        "inconclusive",
    )
    assert len(ISSUE_TAGS) == 14
    assert material_evaluator_error(True, "incorrect") is True
    assert material_evaluator_error(False, "incorrect") is False
