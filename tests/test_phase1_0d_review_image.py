"""Tests for the Phase 1.0D semantic-review image, its provenance and launchers.

Three obligations are under test here, all of them about *bytes*, none of them
about reviewer accuracy:

1. the review image's provenance record is its own artifact, disjoint from the
   frozen generation record it must never touch;
2. the orchestrator moves a pack in and a bundle out without merging runs,
   overwriting anything, or publishing a manifest before the bytes it names;
3. the wrapper hands the completed review to the *frozen* finalizer and then
   only recomputes it.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from jspace_observation.phase1_0d_generation import (  # noqa: E402
    RunConfig,
    run_phase1_0d,
)
from jspace_observation.phase1_0d_execution import SelfTestBackend  # noqa: E402
from jspace_observation.headroom_calibration import canonical_jsonl  # noqa: E402
from jspace_observation.semantic_review import addendum as contract  # noqa: E402
from jspace_observation.semantic_review import stages  # noqa: E402
from jspace_observation.semantic_review import transport  # noqa: E402
from jspace_observation.semantic_review_v2 import verifier as v2_verifier  # noqa: E402


def _load(name: str, relative: str):
    path = REPO_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


review_provenance = _load(
    "phase1_0d_review_build_provenance", "scripts/phase1_0d_review_build_provenance.py"
)
frozen_provenance = _load(
    "phase1_0d_build_provenance_frozen", "scripts/phase1_0d_build_provenance.py"
)
entrypoint = _load(
    "run_phase1_0d_semantic_review", "scripts/run_phase1_0d_semantic_review.py"
)

COMMIT = "9cde1d95ffda36698a0ddf558a9358f3337dd711"


# ---------------------------------------------------------------------------
# The review bundle is a sibling, never an extension
# ---------------------------------------------------------------------------


def _relative(paths: list[Path]) -> set[str]:
    return {path.relative_to(REPO_ROOT).as_posix() for path in paths}


def test_the_review_bundle_is_disjoint_from_the_frozen_generation_bundle():
    """The frozen record is a protected byte; sharing a file would freeze both."""

    review = _relative(review_provenance.resolve_bundle_files(REPO_ROOT))
    frozen = _relative(frozen_provenance.resolve_bundle_files(REPO_ROOT))
    assert review & frozen == set()


def test_the_review_bundle_covers_the_whole_review_surface():
    review = _relative(review_provenance.resolve_bundle_files(REPO_ROOT))
    for required in (
        "Dockerfile.phase1-0d-review",
        "scripts/run_phase1_0d_semantic_review.py",
        "scripts/phase1_0d_review_build_provenance.py",
        "docs/phase1_0d_semantic_review_addendum.json",
        "docs/phase1_0d_semantic_review_rubric.md",
        "src/jspace_observation/semantic_review/addendum.py",
        "src/jspace_observation/semantic_review/stages.py",
        "src/jspace_observation/semantic_review/transport.py",
    ):
        assert required in review


def test_the_review_record_is_not_inside_its_own_bundle():
    """A self-referential record could never be emitted; the tool can be."""

    review = _relative(review_provenance.resolve_bundle_files(REPO_ROOT))
    assert review_provenance.RECORD_PATH not in review
    assert "scripts/phase1_0d_review_build_provenance.py" in review


def test_the_review_image_is_not_the_locked_generation_image():
    assert review_provenance.DOCKERFILE != frozen_provenance.DOCKERFILE
    assert review_provenance.BUNDLE_HASH_DOMAIN != frozen_provenance.BUNDLE_HASH_DOMAIN
    assert review_provenance.BASE_IMAGE_DIGEST == frozen_provenance.BASE_IMAGE_DIGEST


# ---------------------------------------------------------------------------
# Emit, verify, and refuse drift
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def record(tmp_path_factory) -> Path:
    built = review_provenance.build_record(REPO_ROOT, COMMIT)
    path = tmp_path_factory.mktemp("provenance") / review_provenance.RECORD_PATH
    path.write_bytes(review_provenance.canonical_json(built).encode("utf-8"))
    return path


def test_an_emitted_record_verifies_against_the_tree_it_was_emitted_from(record):
    context = review_provenance.verify_image_context(REPO_ROOT, record)
    assert len(context["bundle_sha256"]) == 64
    assert context["file_count"] == len(
        review_provenance.resolve_bundle_files(REPO_ROOT)
    )
    observed = review_provenance.verify_addendum(REPO_ROOT, record)
    assert observed["base_protocol_sha256"] == review_provenance.PROTOCOL_SHA256


def test_the_record_binds_the_authority_the_protocol_and_the_locked_image(record):
    document = json.loads(record.read_text(encoding="utf-8"))
    assert document["authority_prompt_sha256"] == review_provenance.AUTHORITY_PROMPT_SHA256
    assert document["base_protocol_sha256"] == stages.FROZEN_PROTOCOL_SHA256
    assert document["generation_image_digest"] == stages.GENERATION_IMAGE_DIGEST
    assert document["code_commit"] == COMMIT


def test_the_record_states_what_it_does_not_establish(record):
    document = json.loads(record.read_text(encoding="utf-8"))
    boundary = document["claim_boundary"]
    assert "reviewer accuracy" in boundary
    assert "J-space" in boundary


def test_a_tampered_bundle_hash_is_refused(record, tmp_path):
    document = json.loads(record.read_text(encoding="utf-8"))
    document["bundle_sha256"] = "0" * 64
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(review_provenance.ReviewProvenanceError) as error:
        review_provenance.verify_image_context(REPO_ROOT, path)
    assert "baked review bytes hash to" in str(error.value)


def test_a_dropped_file_entry_is_named_in_the_refusal(record, tmp_path):
    document = json.loads(record.read_text(encoding="utf-8"))
    dropped = document["files"].pop()["path"]
    document["bundle_sha256"] = "1" * 64
    path = tmp_path / "dropped.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(review_provenance.ReviewProvenanceError) as error:
        review_provenance.verify_image_context(REPO_ROOT, path)
    assert dropped in str(error.value)


def test_a_record_naming_a_different_addendum_is_refused(record, tmp_path):
    document = json.loads(record.read_text(encoding="utf-8"))
    document["addendum_sha256"] = "2" * 64
    path = tmp_path / "swapped.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(review_provenance.ReviewProvenanceError) as error:
        review_provenance.verify_addendum(REPO_ROOT, path)
    assert "addendum_sha256" in str(error.value)


def test_a_short_commit_is_refused():
    with pytest.raises(review_provenance.ReviewProvenanceError) as error:
        review_provenance.build_record(REPO_ROOT, "9cde1d9")
    assert "40-character" in str(error.value)


# ---------------------------------------------------------------------------
# The Dockerfile verifies both records and rebuilds neither image
# ---------------------------------------------------------------------------


def _text(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_the_review_dockerfile_pins_the_same_base_digest_as_the_locked_image():
    text = _text("Dockerfile.phase1-0d-review")
    assert review_provenance.BASE_IMAGE_DIGEST in text


def test_the_review_dockerfile_verifies_the_frozen_and_the_review_record():
    text = _text("Dockerfile.phase1-0d-review")
    assert "phase1_0d_build_provenance.py" in text
    assert "verify-protocol" in text
    assert "phase1_0d_review_build_provenance.py" in text
    assert "verify-addendum" in text
    assert text.count("verify-image-context") >= 2


def test_the_review_dockerfile_defaults_to_the_synthetic_stage():
    text = _text("Dockerfile.phase1-0d-review")
    assert "qualify" in text.split("CMD", 1)[1]


# ---------------------------------------------------------------------------
# The two launchers
# ---------------------------------------------------------------------------


BUILD_SCRIPT = "infra/azure/scripts/20_build_phase1_0d_review.sh"
RUN_SCRIPT = "infra/azure/scripts/21_run_phase1_0d_semantic_review.sh"


def test_the_review_build_script_locks_the_image_and_verifies_the_lock():
    text = _text(BUILD_SCRIPT)
    assert "--write-enabled false --delete-enabled false" in text
    assert "is still enabled after locking" in text
    assert "Refusing to build a dirty worktree" in text
    assert "already exists; use a new commit" in text


def test_the_review_build_script_never_reuses_the_locked_generation_repository():
    text = _text(BUILD_SCRIPT)
    assert 'GENERATION_REPOSITORY="j-space-observation-phase1-0d"' in text
    assert 'IMAGE_REPOSITORY="j-space-observation-phase1-0d-review"' in text
    assert "may not share the locked generation repository" in text
    assert "neither rebuilt nor retagged" in text


def test_the_review_build_script_requires_the_committed_record():
    text = _text(BUILD_SCRIPT)
    assert review_provenance.RECORD_PATH in text
    assert "build-provenance record is missing" in text


def test_the_review_run_launcher_refuses_a_platform_retry_or_a_second_replica():
    text = _text(RUN_SCRIPT)
    assert '"replicaRetryLimit": 0' in text
    assert '"parallelism": 1' in text
    assert '"replicaCompletionCount": 1' in text


def test_the_review_run_launcher_refuses_an_unlocked_or_tag_only_image():
    text = _text(RUN_SCRIPT)
    assert "Review image is not locked; refusing to launch" in text
    assert "IMAGE_DIGEST_REF=\"${LOGIN_SERVER}/${IMAGE_REPOSITORY}@${IMAGE_DIGEST}\"" in text
    for attribute in (
        "TAG_WRITE_ENABLED",
        "TAG_DELETE_ENABLED",
        "MANIFEST_WRITE_ENABLED",
        "MANIFEST_DELETE_ENABLED",
    ):
        assert attribute in text


def test_the_review_run_launcher_carries_no_storage_credential():
    text = _text(RUN_SCRIPT)
    assert "AZURE_CLIENT_ID" in text
    assert "credential-bearing variables present" in text
    environment_block = text.split("environment = [", 1)[1].split("]", 1)[0]
    for forbidden in ("ACCOUNT_KEY", "SAS", "CONNECTION_STRING"):
        assert forbidden not in environment_block.upper()


def test_the_review_run_launcher_binds_review_mode_to_a_generation_run():
    text = _text(RUN_SCRIPT)
    assert "REVIEW_MODE must be qualify, smoke or review" in text
    assert "review mode requires GENERATION_RUN_ID" in text
    assert "--pack-blob-prefix" in text
    assert "--out-blob-prefix" in text


def test_the_review_run_launcher_states_what_the_synthetic_stages_are_not():
    text = _text(RUN_SCRIPT)
    assert "count towards no scientific total" in text


def test_neither_review_launcher_touches_the_phase_1_0c_namespace():
    for relative in (BUILD_SCRIPT, RUN_SCRIPT):
        text = _text(relative)
        assert "j-space-observation-calibration" not in text
        assert "phase1-headroom-calibration" not in text


def test_both_run_launchers_resolve_an_interpreter_that_actually_answers():
    """A name on PATH can be an alias that exits without running Python.

    The interpreter only builds a control-plane request body, but a launcher
    that dies on a Windows App Execution Alias cannot submit the run at all.
    """

    for relative in ("infra/azure/scripts/19_run_phase1_0d_confirmation.sh", RUN_SCRIPT):
        text = _text(relative)
        assert "type -aP python3 python" in text
        assert "sys.version_info[0] == 3" in text
        assert "/usr/bin/python3" in text


# ---------------------------------------------------------------------------
# Moving bytes: download, publish, and the outer bundle
# ---------------------------------------------------------------------------


class _FakeBlob:
    """Records order and refuses an overwrite, like the real create-only PUT."""

    def __init__(self, existing: dict[str, bytes] | None = None) -> None:
        self.store: dict[str, bytes] = dict(existing or {})
        self.written: list[str] = []

    def list_prefix(self, prefix: str) -> list[str]:
        return [name for name in sorted(self.store) if name.startswith(prefix)]

    def get(self, name: str) -> bytes:
        return self.store[name]

    def put_create_only(self, name: str, payload: bytes) -> None:
        if name in self.store:
            raise transport.TransportError(
                f"{name} already exists; this run refuses to overwrite"
            )
        self.store[name] = payload
        self.written.append(name)


def test_download_refuses_a_non_empty_destination(tmp_path):
    client = _FakeBlob({"packs/run/02_records.jsonl": b"{}\n"})
    destination = tmp_path / "pack"
    destination.mkdir()
    (destination / "stray.json").write_bytes(b"{}")
    with pytest.raises(stages.StageError) as error:
        entrypoint.download_pack(client, "packs/run", destination)
    assert "refusing to merge packs" in str(error.value)


def test_download_refuses_an_empty_prefix(tmp_path):
    client = _FakeBlob({"other/run/02_records.jsonl": b"{}\n"})
    with pytest.raises(stages.StageError) as error:
        entrypoint.download_pack(client, "packs/run", tmp_path / "pack")
    assert "no generation pack" in str(error.value)


def test_download_copies_every_file_and_strips_the_prefix(tmp_path):
    client = _FakeBlob(
        {
            "packs/run/02_records.jsonl": b'{"record_id": "a"}\n',
            "packs/run/nested/03_review_form.jsonl": b'{"record_id": "a"}\n',
            "packs/run/": b"",
        }
    )
    destination = tmp_path / "pack"
    result = entrypoint.download_pack(client, "packs/run", destination)
    assert result["file_count"] == 2
    assert (destination / "02_records.jsonl").exists()
    assert (destination / "nested" / "03_review_form.jsonl").exists()
    assert [entry["name"] for entry in result["files"]] == [
        "02_records.jsonl",
        "nested/03_review_form.jsonl",
    ]


def test_publish_writes_every_file_before_the_manifest():
    client = _FakeBlob()
    files = {"final/05_decision.json": b"{}", "review/all_judgments.json": b"[]"}
    result = entrypoint.publish_bundle(client, "out/run", files, "20260101T000000Z")
    assert client.written[-1] == "out/run/artifact_manifest.json"
    assert result["uploaded_count"] == 2
    assert result["manifest_written_last"] is True
    manifest = json.loads(client.store["out/run/artifact_manifest.json"])
    assert [entry["name"] for entry in manifest["files"]] == sorted(files)


def test_publish_refuses_to_overwrite_an_existing_prefix():
    client = _FakeBlob({"out/run/final/05_decision.json": b"{}"})
    with pytest.raises(transport.TransportError) as error:
        entrypoint.publish_bundle(
            client, "out/run", {"final/05_decision.json": b"{}"}, "20260101T000000Z"
        )
    assert "refuses to overwrite" in str(error.value)


def test_read_tree_uses_posix_relative_names(tmp_path):
    (tmp_path / "review" / "primary").mkdir(parents=True)
    (tmp_path / "review" / "primary" / "judgments.json").write_bytes(b"[]")
    (tmp_path / "00_execution_receipt.json").write_bytes(b"{}")
    tree = entrypoint._read_tree(tmp_path)
    assert set(tree) == {
        "00_execution_receipt.json",
        "review/primary/judgments.json",
    }


# ---------------------------------------------------------------------------
# The wrapper hands the result to the frozen finalizer and only recomputes it
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pack(tmp_path_factory) -> Path:
    summary = run_phase1_0d(
        RunConfig(
            mode="self-test",
            output_root=tmp_path_factory.mktemp("packs"),
            repo_root=REPO_ROOT,
            run_id="20260101T000000Z",
            code_commit=COMMIT,
            image_digest=stages.GENERATION_IMAGE_DIGEST,
            hardware="cpu-test",
        )
    )
    assert summary["records"] == 900
    return Path(summary["output_dir"])


class _RegisteredFakeBackend(SelfTestBackend):
    is_real_model = True
    name = "phase1_0d_transformers_causal_lm_v1"

    def generate(self, unit):
        self._last_prompt_token_count = 100
        return super().generate(unit)

    def describe(self) -> dict[str, Any]:
        return {
            "backend": self.name,
            "is_real_model": True,
            "model_id": stages.MODEL_ID,
            "model_revision": stages.MODEL_REVISION,
            "device": "cuda",
        }


@pytest.fixture(scope="module")
def generation_pack(tmp_path_factory) -> Path:
    summary = run_phase1_0d(
        RunConfig(
            mode="generate",
            output_root=tmp_path_factory.mktemp("generation-packs"),
            repo_root=REPO_ROOT,
            run_id="20260101T000000Z",
            code_commit=v2_verifier.GENERATION_CODE_COMMIT,
            image_digest=stages.GENERATION_IMAGE_DIGEST,
            hardware=v2_verifier.GENERATION_HARDWARE,
            backend=_RegisteredFakeBackend(),
            runtime_environment={
                "cuda_available": True,
                "cuda_device_name": "NVIDIA Tesla T4",
            },
        )
    )
    return Path(summary["output_dir"])


def _rehash_pack_file(pack_dir: Path, name: str) -> None:
    import hashlib

    manifest_path = pack_dir / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(
        (pack_dir / name).read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    for entry in manifest["files"]:
        if entry["name"] == name:
            entry["sha256"] = digest
            break
    else:
        raise AssertionError(f"manifest has no {name}")
    manifest_path.write_bytes(contract.canonical_json(manifest).encode("utf-8"))


def _source_manifest_sha256(pack_dir: Path) -> str:
    import hashlib

    return hashlib.sha256((pack_dir / "artifact_manifest.json").read_bytes()).hexdigest()


def test_v2_rebuilds_the_exact_source_pack_before_any_review(generation_pack):
    result = v2_verifier.verify_source_pack(
        pack_dir=generation_pack,
        project_root=REPO_ROOT,
        expected_manifest_sha256=_source_manifest_sha256(generation_pack),
    )
    assert result["records_rebuilt"] == 900
    assert result["selection_recomputed"] is True
    assert result["raw_member_hashes_verified"] is True
    assert result["exact_manifest_file_set"] is True


def test_v2_refuses_line_ending_substitution_under_the_committed_manifest(
    generation_pack, tmp_path
):
    expected_manifest_sha256 = _source_manifest_sha256(generation_pack)
    copied = tmp_path / "crlf-substitution"
    shutil.copytree(generation_pack, copied)
    path = copied / "01_selection.json"
    raw = path.read_bytes()
    assert b"\r\n" not in raw
    path.write_bytes(raw.replace(b"\n", b"\r\n"))
    with pytest.raises(
        v2_verifier.IndependentVerificationError,
        match="raw source bytes differ from the committed manifest",
    ):
        v2_verifier.verify_source_pack(
            pack_dir=copied,
            project_root=REPO_ROOT,
            expected_manifest_sha256=expected_manifest_sha256,
        )


def test_v2_refuses_a_rehashed_but_substituted_selection(
    generation_pack, tmp_path
):
    copied = tmp_path / "substituted-selection"
    shutil.copytree(generation_pack, copied)
    path = copied / "01_selection.json"
    selection = json.loads(path.read_text(encoding="utf-8"))
    selection["items"][0]["question"] = "substituted after generation"
    path.write_bytes(contract.canonical_json(selection).encode("utf-8"))
    _rehash_pack_file(copied, "01_selection.json")
    with pytest.raises(
        v2_verifier.IndependentVerificationError,
        match="selected items differ",
    ):
        v2_verifier.verify_source_pack(
            pack_dir=copied,
            project_root=REPO_ROOT,
            expected_manifest_sha256=_source_manifest_sha256(copied),
        )


def test_v2_refuses_a_rehashed_record_with_moved_metadata(
    generation_pack, tmp_path
):
    copied = tmp_path / "substituted-record"
    shutil.copytree(generation_pack, copied)
    path = copied / "02_records.jsonl"
    records = stages.load_records(path)
    records[0]["condition"] = "substituted condition"
    path.write_text(canonical_jsonl(records), encoding="utf-8")
    _rehash_pack_file(copied, "02_records.jsonl")
    with pytest.raises(
        v2_verifier.IndependentVerificationError,
        match="record metadata",
    ):
        v2_verifier.verify_source_pack(
            pack_dir=copied,
            project_root=REPO_ROOT,
            expected_manifest_sha256=_source_manifest_sha256(copied),
        )


def test_v2_refuses_rehashed_output_substitution_without_committed_license(
    generation_pack, tmp_path
):
    expected_manifest_sha256 = _source_manifest_sha256(generation_pack)
    copied = tmp_path / "substituted-output"
    shutil.copytree(generation_pack, copied)
    path = copied / "02_records.jsonl"
    records = stages.load_records(path)
    records[0]["output_text"] = "attacker-controlled replacement"
    path.write_text(canonical_jsonl(records), encoding="utf-8")
    _rehash_pack_file(copied, "02_records.jsonl")

    with pytest.raises(
        v2_verifier.IndependentVerificationError,
        match="committed generation license",
    ):
        v2_verifier.verify_source_pack(
            pack_dir=copied,
            project_root=REPO_ROOT,
            expected_manifest_sha256=expected_manifest_sha256,
        )


def _parser_agreeing_labels(pack: Path) -> dict[str, str]:
    """Labels that follow the frozen parser route on every row.

    This is a fixture, not a claim: agreeing with the parser makes the forced
    component of the secondary set empty, so the arithmetic downstream is
    observable rather than accidental.
    """

    labels: dict[str, str] = {}
    for row in stages.load_records(pack / "02_records.jsonl"):
        triage = row["triage"]
        if triage["surface_matches_registered_answer"]:
            label = "correct"
        elif triage["final_answer_surface_present"]:
            label = "incorrect"
        else:
            label = "no_answer"
        labels[str(row["record_id"])] = label
    return labels


@pytest.fixture(scope="module")
def finalized(tmp_path_factory, pack: Path) -> dict[str, Any]:
    book = contract.load_addendum(REPO_ROOT)
    records = stages.load_records(pack / "02_records.jsonl")
    labels = _parser_agreeing_labels(pack)

    primary = [
        contract.judgment(
            record_id, "primary", label, book.roles["primary"].reviewer_id
        )
        for record_id, label in sorted(labels.items())
    ]
    secondary_selection = stages.select_secondary(records, primary, book)
    secondary = [
        contract.judgment(
            record_id, "secondary", labels[record_id], book.roles["secondary"].reviewer_id
        )
        for record_id in secondary_selection["required_ids"]
    ]
    third_selection = stages.select_third(primary, secondary)
    combined = stages.combine_judgments(primary, secondary, [])

    work = tmp_path_factory.mktemp("finalize")
    judgments_path = work / "all_judgments.json"
    judgments_path.write_bytes(contract.canonical_json(combined).encode("utf-8"))

    result = entrypoint.finalize_pack(
        project_root=REPO_ROOT,
        pack_dir=pack,
        judgments_path=judgments_path,
        out_root=work / "final",
        run_id="20260101T000000Z",
        code_commit=COMMIT,
        image_digest="sha256:" + "3" * 64,
    )
    return {
        "result": result,
        "combined": combined,
        "secondary_selection": secondary_selection,
        "third_selection": third_selection,
    }


def test_the_frozen_finalizer_produces_the_decision_not_the_wrapper(finalized):
    """No arbitration lives in the review package; it calls the registered one."""

    final_dir = Path(finalized["result"]["output_dir"])
    decision = json.loads((final_dir / "05_decision.json").read_text(encoding="utf-8"))
    assert decision["result"] == finalized["result"]["result"]
    assert decision["result"] != "AWAITING_SEMANTIC_REVIEW"
    assert finalized["result"]["records"] == 900


def test_the_third_reviewer_is_unused_when_the_first_two_agree(finalized):
    assert finalized["third_selection"]["required_count"] == 0
    assert finalized["secondary_selection"]["forced_count"] == 0
    assert finalized["secondary_selection"]["required_count"] == 180


def test_the_independent_check_recomputes_the_finalized_pack(finalized):
    final_dir = Path(finalized["result"]["output_dir"])
    check = stages.independent_check(
        records=stages.load_records(final_dir / "02_records.jsonl"),
        decision=json.loads((final_dir / "05_decision.json").read_text(encoding="utf-8")),
        combined=finalized["combined"],
        required_secondary=finalized["secondary_selection"]["required_ids"],
        required_third=finalized["third_selection"]["required_ids"],
    )
    assert check["records"] == 900
    assert check["recomputed_only"] is True
    assert check["changed_nothing"] is True
    assert sum(check["final_label_counts"].values()) == 900


def test_the_independent_check_refuses_a_pack_whose_judgments_moved(finalized):
    final_dir = Path(finalized["result"]["output_dir"])
    short = [item for item in finalized["combined"] if item["role"] != "secondary"]
    with pytest.raises(stages.IntegrityError) as error:
        stages.independent_check(
            records=stages.load_records(final_dir / "02_records.jsonl"),
            decision=json.loads(
                (final_dir / "05_decision.json").read_text(encoding="utf-8")
            ),
            combined=short,
            required_secondary=finalized["secondary_selection"]["required_ids"],
            required_third=finalized["third_selection"]["required_ids"],
        )
    assert "secondary judgments are not exactly the required set" in str(error.value)


def test_v2_independently_recomputes_records_metrics_gates_and_decision(
    finalized, pack
):
    final_dir = Path(finalized["result"]["output_dir"])
    check = v2_verifier.verify_final_result(
        source_records=stages.load_records(pack / "02_records.jsonl"),
        finalized_records=stages.load_records(final_dir / "02_records.jsonl"),
        decision=json.loads((final_dir / "05_decision.json").read_text("utf-8")),
        combined=finalized["combined"],
        required_secondary=finalized["secondary_selection"]["required_ids"],
        required_third=finalized["third_selection"]["required_ids"],
        expected_code_commit=COMMIT,
        expected_image_digest="sha256:" + "3" * 64,
    )
    assert check["records"] == 900
    assert check["cell_count"] == 30
    assert check["decision_result"] == finalized["result"]["result"]
    assert sum(check["final_label_counts"].values()) == 900
    assert check["decision_sha256"]
    assert check["recomputed_decision_sha256"]


def test_v2_independent_recomputation_rejects_an_arbitrary_decision(
    finalized, pack
):
    final_dir = Path(finalized["result"]["output_dir"])
    decision = json.loads((final_dir / "05_decision.json").read_text("utf-8"))
    decision["result"] = "ARBITRARY_WRONG_RESULT"
    decision["rq2_pilot_candidates"] = ["fabricated|candidate"]
    with pytest.raises(
        v2_verifier.IndependentVerificationError,
        match="decision differs from independent metric and gate recomputation",
    ):
        v2_verifier.verify_final_result(
            source_records=stages.load_records(pack / "02_records.jsonl"),
            finalized_records=stages.load_records(final_dir / "02_records.jsonl"),
            decision=decision,
            combined=finalized["combined"],
            required_secondary=finalized["secondary_selection"]["required_ids"],
            required_third=finalized["third_selection"]["required_ids"],
            expected_code_commit=COMMIT,
            expected_image_digest="sha256:" + "3" * 64,
        )


def test_v2_independent_recomputation_rejects_moved_provenance(
    finalized, pack
):
    final_dir = Path(finalized["result"]["output_dir"])
    decision = json.loads((final_dir / "05_decision.json").read_text("utf-8"))
    decision["provenance"]["code_commit"] = "0" * 40
    with pytest.raises(
        v2_verifier.IndependentVerificationError,
        match="provenance differs",
    ):
        v2_verifier.verify_final_result(
            source_records=stages.load_records(pack / "02_records.jsonl"),
            finalized_records=stages.load_records(final_dir / "02_records.jsonl"),
            decision=decision,
            combined=finalized["combined"],
            required_secondary=finalized["secondary_selection"]["required_ids"],
            required_third=finalized["third_selection"]["required_ids"],
            expected_code_commit=COMMIT,
            expected_image_digest="sha256:" + "3" * 64,
        )


def test_the_execution_receipt_binds_generation_review_and_image():
    receipt = stages.outer_receipt(
        artifact="phase1_0d_semantic_review_execution_receipt",
        run_id="20260101T000000Z",
        generation_pack_manifest_sha256="a" * 64,
        all_judgments_sha256="b" * 64,
        review_image_digest="sha256:" + "c" * 64,
    )
    assert receipt["generation_pack_manifest_sha256"] == "a" * 64
    assert "nothing about reviewer accuracy" in receipt["claim_boundary"]
