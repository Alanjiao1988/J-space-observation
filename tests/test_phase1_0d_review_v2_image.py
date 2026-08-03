"""Tests for the Phase 1.0D semantic-review v2 runner, provenance and image.

Everything here is prospective.  It runs before any v2 provider call and its
job is to make the round's stated guarantees mechanical rather than aspirational:

* the gate batch completes and is persisted *before* its verdict is applied,
  because L-51 records what happens when it is not;
* the qualification probe does not consume one of the 60 registered pairs;
* qualification and smoke hold no capability to read target storage;
* the build refuses unless every section 8 obligation holds inside the image;
* the three build-provenance bundles stay disjoint, so adding v2 cannot move a
  locked record.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _load(module_name: str, relative: str):
    spec = importlib.util.spec_from_file_location(module_name, REPO_ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


runner = _load(
    "run_phase1_0d_semantic_review_v2", "scripts/run_phase1_0d_semantic_review_v2.py"
)
prov2 = _load(
    "phase1_0d_review_v2_build_provenance",
    "scripts/phase1_0d_review_v2_build_provenance.py",
)
prov1 = _load(
    "phase1_0d_review_build_provenance", "scripts/phase1_0d_review_build_provenance.py"
)
prov0 = _load("phase1_0d_build_provenance", "scripts/phase1_0d_build_provenance.py")

from jspace_observation.semantic_review import addendum as contract  # noqa: E402
from jspace_observation.semantic_review_v2 import addendum_v2  # noqa: E402

DOCKERFILE = REPO_ROOT / "Dockerfile.phase1-0d-review-v2"
RECORD = REPO_ROOT / prov2.RECORD_PATH
BUILD_SCRIPT = REPO_ROOT / "infra/azure/scripts/22_build_phase1_0d_review_v2.sh"
RUN_SCRIPT = REPO_ROOT / "infra/azure/scripts/23_run_phase1_0d_semantic_review_v2.sh"


@pytest.fixture(scope="module")
def book():
    return addendum_v2.load_addendum_v2(REPO_ROOT)


# --------------------------------------------------------------------------
# the gate batch
# --------------------------------------------------------------------------


def _ok_call(
    fixture_id: str,
    role: str,
    expected: str,
    observed: str,
    tokens: int = 12,
    profile=None,
):
    provider = profile.provider if profile else "azure_ai_foundry"
    deployment = profile.deployment if profile else f"{role}-deployment"
    model = profile.model if profile else "m"
    model_version = profile.model_version if profile else "v"
    return {
        "fixture_id": fixture_id,
        "expected_label": expected,
        "role": role,
        "provider": provider,
        "deployment": deployment,
        "model": model,
        "model_version": model_version,
        "request_body_sha256": "a" * 64,
        "response_body_sha256": "b" * 64,
        "observed_label": observed,
        "match": observed == expected,
        "request_id": "chatcmpl-1",
        "provider_model_fingerprint": "m",
        "finish_reason": "stop",
        "visible_completion_tokens": tokens,
        "total_tokens": 400,
        "latency_seconds": 1.5,
        "retry_count": 0,
        "terminal_transport_status": "ok",
    }


def _full_batch(book, observed_override=None):
    calls = []
    for fixture in book.smoke_fixtures:
        for role in contract.ROLES:
            expected = str(fixture["expected_label"])
            observed = expected
            if observed_override and observed_override[0] == (
                fixture["fixture_id"],
                role,
            ):
                observed = observed_override[1]
            calls.append(
                _ok_call(
                    str(fixture["fixture_id"]),
                    role,
                    expected,
                    observed,
                    profile=book.roles[role],
                )
            )
    return calls


def test_a_complete_matching_batch_passes(book):
    result = runner.summarise_smoke(book, _full_batch(book))
    assert result["passed"] is True
    assert result["verdict"] == "QUALIFIED"
    assert result["counts"]["completed_calls"] == 60
    assert result["counts"]["exact_expected_label_matches"] == 60
    assert result["mismatches"] == []


def test_a_single_mismatch_closes_the_route(book):
    """There is no 59/60 and no majority rule."""

    first = book.smoke_fixtures[0]["fixture_id"]
    calls = _full_batch(book, observed_override=((first, "primary"), "invalid"))
    result = runner.summarise_smoke(book, calls)
    assert result["passed"] is False
    assert result["counts"]["exact_expected_label_matches"] == 59
    assert result["verdict"] == runner.TERMINAL_UNQUALIFIED
    assert len(result["mismatches"]) == 1


def test_an_incomplete_batch_cannot_pass(book):
    result = runner.summarise_smoke(book, _full_batch(book)[:59])
    assert result["passed"] is False
    assert result["counts"]["completed_calls"] == 59


def test_a_malformed_response_is_never_relabelled(book):
    calls = _full_batch(book)
    calls[7]["observed_label"] = None
    calls[7]["match"] = False
    calls[7]["terminal_transport_status"] = "malformed_label: two keys"
    result = runner.summarise_smoke(book, calls)
    assert result["passed"] is False
    assert result["counts"]["malformed_responses"] == 1
    assert result["counts"]["valid_responses"] == 59


def test_an_exhausted_transport_is_recorded_not_retried(book):
    calls = _full_batch(book)
    calls[3]["terminal_transport_status"] = "transport_exhausted: 8 attempts"
    calls[3]["observed_label"] = None
    calls[3]["match"] = False
    result = runner.summarise_smoke(book, calls)
    assert result["passed"] is False
    assert result["counts"]["transport_failures_after_registered_retry"] == 1


def test_exceeding_the_visible_cap_is_a_failure_not_a_label(book):
    calls = _full_batch(book)
    calls[11]["visible_completion_tokens"] = 65
    result = runner.summarise_smoke(book, calls)
    assert result["passed"] is False
    assert result["counts"]["visible_completions_within_cap"] == 59
    assert result["counts"]["exact_expected_label_matches"] == 60


def test_a_negative_visible_count_is_malformed_not_within_cap(book):
    calls = _full_batch(book)
    calls[4]["visible_completion_tokens"] = -3
    result = runner.summarise_smoke(book, calls)
    assert result["passed"] is False
    assert result["counts"]["visible_completions_within_cap"] == 59


def test_the_registered_caps_are_the_frozen_sixty_four(book):
    result = runner.summarise_smoke(book, _full_batch(book))
    assert set(result["visible_token_caps"].values()) == {64}


def test_semantic_retries_are_reported_as_zero(book):
    result = runner.summarise_smoke(book, _full_batch(book))
    assert result["counts"]["semantic_retries"] == 0


# --------------------------------------------------------------------------
# the batch completes even when an early call fails
# --------------------------------------------------------------------------


class _FailingCaller:
    """Answers correctly except for one pair, which it fails hard."""

    def __init__(self, book, failing_index: int, error: Exception) -> None:
        self._book = book
        self._index = failing_index
        self._error = error
        self._call_lock = threading.Lock()
        self.calls = 0

    def __call__(self, profile, body):
        with self._call_lock:
            index = self.calls
            self.calls += 1
        if index == self._index:
            raise self._error
        label = self._expected_for(body)
        payload = {
            "id": f"chatcmpl-{index}",
            "model": "m",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": json.dumps({"label": label})},
                }
            ],
            "usage": {"completion_tokens": 9, "total_tokens": 300},
        }

        class _Response:
            response_sha256 = "c" * 64
            latency_seconds = 0.5
            retries = 0

        response = _Response()
        response.payload = payload
        response.request_sha256 = contract.sha256_text(
            contract.request_bytes(body).decode("utf-8")
        )
        return response

    def _expected_for(self, body):
        text = json.dumps(body)
        for fixture in self._book.smoke_fixtures:
            if fixture["row"]["record_id"] in text:
                return str(fixture["expected_label"])
        raise AssertionError("a call was made with an unregistered row")


class _QualificationCaller:
    def __init__(self) -> None:
        self.calls = 0
        self.resolved = {}

    def call_route(self, profile, body, path, api_version):
        self.calls += 1
        payload = {
            "id": f"qualification-{profile.role}",
            "model": profile.model,
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": json.dumps({"label": "correct"})},
                }
            ],
            "usage": {"completion_tokens": 9, "total_tokens": 200},
        }

        class _Response:
            response_sha256 = "d" * 64
            latency_seconds = 0.25
            retries = 0

        response = _Response()
        response.payload = payload
        response.request_sha256 = contract.sha256_text(
            contract.request_bytes(body).decode("utf-8")
        )
        return response


def test_qualification_is_exactly_three_calls_with_the_full_receipt(book):
    caller = _QualificationCaller()
    result = runner._qualify(book, caller)
    assert caller.calls == 3
    assert result["passed"] is True
    assert result["counts"]["valid_expected_label_matches"] == 3
    required = set(book.document["evidence_persistence"]["per_call_receipt_fields"])
    for call in result["calls"]:
        assert required <= set(call)
        assert call["fixture_id"] == runner.QUALIFICATION_PROBE["record_id"]
        assert call["expected_label"] == "correct"


def test_every_registered_call_still_runs_after_an_early_failure(book):
    caller = _FailingCaller(book, 0, contract.TransportError("exhausted"))
    result = runner._smoke(book, caller)
    assert caller.calls == 60
    assert result["counts"]["completed_calls"] == 60
    assert result["counts"]["transport_failures_after_registered_retry"] == 1
    assert result["passed"] is False


def test_a_clean_run_reaches_sixty_of_sixty(book):
    caller = _FailingCaller(book, -1, RuntimeError("unused"))
    result = runner._smoke(book, caller)
    assert result["passed"] is True
    assert result["counts"]["completed_calls"] == 60
    for call in result["calls"]:
        for field in book.document["evidence_persistence"]["per_call_receipt_fields"]:
            assert field in call


class _ConcurrencyCaller(_FailingCaller):
    def __init__(self, book) -> None:
        super().__init__(book, -1, RuntimeError("unused"))
        self._activity_lock = threading.Lock()
        self._active = {role: 0 for role in contract.ROLES}
        self.max_active = {role: 0 for role in contract.ROLES}

    def __call__(self, profile, body):
        with self._activity_lock:
            self._active[profile.role] += 1
            self.max_active[profile.role] = max(
                self.max_active[profile.role], self._active[profile.role]
            )
        try:
            time.sleep(0.02)
            return super().__call__(profile, body)
        finally:
            with self._activity_lock:
                self._active[profile.role] -= 1


def test_smoke_uses_at_most_eight_workers_per_deployment(book):
    caller = _ConcurrencyCaller(book)
    result = runner._smoke(book, caller)
    assert result["passed"] is True
    assert caller.calls == 60
    for role in contract.ROLES:
        assert 1 < caller.max_active[role] <= 8


def test_smoke_worst_case_fits_the_launcher_deadline(book):
    assert runner.smoke_worst_case_seconds(book) == 5409
    assert (
        runner.smoke_worst_case_seconds(book)
        + runner.GATE_PERSISTENCE_MARGIN_SECONDS
        < 10500
    )
    text = RUN_SCRIPT.read_text(encoding="utf-8")
    assert "--execution-timeout-seconds $REVIEW_TIMEOUT_SECONDS" in text


def test_smoke_token_acquisition_has_no_global_serial_lock():
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "SerializedTokenProvider" not in source
    assert "threading.Lock" not in source
    assert "tokens = transport.TokenProvider(args.client_id or None)" in source


def test_a_non_object_envelope_is_recorded_and_the_batch_continues(book):
    caller = _FailingCaller(book, -1, RuntimeError("unused"))
    original = caller.__call__

    class _MalformedThenClean:
        def __init__(self):
            self.calls = 0
            self.lock = threading.Lock()

        def __call__(self, profile, body):
            with self.lock:
                self.calls += 1
                call_number = self.calls
            response = original(profile, body)
            if call_number == 1:
                response.payload = []
            return response

    wrapped = _MalformedThenClean()
    result = runner._smoke(book, wrapped)
    assert wrapped.calls == 60
    assert result["counts"]["completed_calls"] == 60
    assert result["counts"]["malformed_responses"] == 1
    assert result["passed"] is False


# --------------------------------------------------------------------------
# isolation
# --------------------------------------------------------------------------


def test_the_qualification_probe_is_outside_the_registered_bank(book):
    runner.assert_probe_is_not_a_fixture(book)
    registered = {str(f["row"]["record_id"]) for f in book.smoke_fixtures}
    assert runner.QUALIFICATION_PROBE["record_id"] not in registered
    assert set(runner.QUALIFICATION_PROBE) == set(contract.PRESENTED_FIELDS)


def test_the_gate_publisher_exposes_no_read_or_list_capability():
    exposed = {name for name in dir(runner.GatePublisher) if not name.startswith("_")}
    assert exposed == {"publish", "prefix"}
    assert not hasattr(runner.GatePublisher, "get")
    assert not hasattr(runner.GatePublisher, "list_prefix")


def test_the_gate_reader_refuses_paths_outside_its_registered_prefix():
    reader = object.__new__(runner.GateReader)
    reader._prefix = "registered/qualification"
    reader._client = _FakeBlob({})
    with pytest.raises(runner.GateEvidenceError):
        reader.get("target-generation/02_records.jsonl")


def test_gate_prefixes_are_confined_to_the_frozen_roots():
    assert (
        runner._validate_gate_prefix(
            "phase1-0d-semantic-review-v2/qualification/20260803T000000Z",
            runner.QUALIFICATION_PREFIX_ROOT,
        )
        == "phase1-0d-semantic-review-v2/qualification/20260803T000000Z"
    )
    with pytest.raises(runner.GateEvidenceError):
        runner._validate_gate_prefix(
            "phase1-headroom-confirmation/20260803T000000Z",
            runner.QUALIFICATION_PREFIX_ROOT,
        )


def test_qualify_and_smoke_refuse_a_generation_pack():
    for mode in ("qualify", "smoke"):
        with pytest.raises(SystemExit) as error:
            runner.main([mode, "--pack-blob-prefix", "phase1-0d/whatever"])
        assert "take no generation pack" in str(error.value)


def test_every_mode_requires_an_explicit_commit_and_image_binding():
    with pytest.raises(SystemExit) as error:
        runner.main(["qualify"])
    assert "requires --code-commit" in str(error.value)


def test_the_download_helper_is_not_imported_at_module_scope():
    assert not hasattr(runner, "download_pack")
    source = (
        REPO_ROOT / "scripts/run_phase1_0d_semantic_review_v2.py"
    ).read_text(encoding="utf-8")
    import_line = "import run_phase1_0d_semantic_review as v1runner"
    assert source.index(import_line) > source.index(
        "# ---- review: target storage is reachable only from here"
    )


# --------------------------------------------------------------------------
# the gate receipt licenses review
# --------------------------------------------------------------------------


class _FakeBlob:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self._objects = objects

    def get(self, name: str) -> bytes:
        return self._objects[name]


def _gate_objects(book, *, passed=True, matches=60, addendum_sha=None):
    roles = {
        role: {
            "reviewer_id": book.roles[role].reviewer_id,
            "request_profile_sha256": book.roles[role].request_profile_sha256(),
            "proven_path": book.roles[role].path_candidates[0],
            "proven_api_version": book.roles[role].api_version_candidates[0],
        }
        for role in contract.ROLES
    }
    result = runner.summarise_smoke(book, _full_batch(book))
    result["passed"] = passed
    result["counts"]["exact_expected_label_matches"] = matches
    receipt = {
        "artifact": "phase1_0d_rv2_provider_smoke_receipt",
        "run_id": "20260803T000000Z",
        **runner._instrument_header(book),
        "addendum_sha256": addendum_sha or book.sha256,
        "review_code_commit": "1" * 40,
        "review_image_digest": "sha256:" + "2" * 64,
        "roles": roles,
        "qualification_parent": {
            "prefix": (
                "phase1-0d-semantic-review-v2/qualification/"
                "20260803T000001Z"
            ),
            "run_id": "20260803T000001Z",
            "receipt_sha256": "3" * 64,
        },
        **result,
    }
    raw = contract.canonical_json(receipt).encode("utf-8")
    import hashlib

    manifest = {
        "file_count": 1,
        "manifest_written_last": True,
        "files": [
            {"name": "00_gate_receipt.json", "sha256": hashlib.sha256(raw).hexdigest()}
        ]
    }
    return {
        "p/00_gate_receipt.json": raw,
        "p/artifact_manifest.json": contract.canonical_json(manifest).encode("utf-8"),
    }


def _rewrite_receipt(objects, prefix, mutate):
    import hashlib

    key = f"{prefix}/00_gate_receipt.json"
    document = json.loads(objects[key])
    mutate(document)
    raw = contract.canonical_json(document).encode("utf-8")
    objects[key] = raw
    manifest_key = f"{prefix}/artifact_manifest.json"
    manifest = json.loads(objects[manifest_key])
    manifest["files"][0]["sha256"] = hashlib.sha256(raw).hexdigest()
    objects[manifest_key] = contract.canonical_json(manifest).encode("utf-8")


def test_review_accepts_a_persisted_sixty_of_sixty(book):
    client = _FakeBlob(_gate_objects(book))
    receipt = runner._load_gate_receipt(client, "p", book)
    assert receipt["passed"] is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"passed": False},
        {"matches": 59},
        {"addendum_sha": "f" * 64},
    ],
)
def test_review_refuses_anything_less(book, kwargs):
    client = _FakeBlob(_gate_objects(book, **kwargs))
    with pytest.raises(addendum_v2.AddendumError):
        runner._load_gate_receipt(client, "p", book)


def test_review_refuses_a_receipt_that_does_not_match_its_manifest(book):
    objects = _gate_objects(book)
    objects["p/00_gate_receipt.json"] = objects["p/00_gate_receipt.json"] + b" "
    with pytest.raises(addendum_v2.AddendumError):
        runner._load_gate_receipt(_FakeBlob(objects), "p", book)


def test_review_refuses_an_incomplete_receipt_even_if_it_claims_sixty(book):
    objects = _gate_objects(book)
    _rewrite_receipt(objects, "p", lambda receipt: receipt["calls"].pop())
    with pytest.raises(addendum_v2.AddendumError):
        runner._load_gate_receipt(_FakeBlob(objects), "p", book)


def test_smoke_accepts_only_a_persisted_three_of_three_qualification(book):
    roles = {
        role: {
            "reviewer_id": book.roles[role].reviewer_id,
            "request_profile_sha256": book.roles[role].request_profile_sha256(),
            "proven_path": book.roles[role].path_candidates[0],
            "proven_api_version": book.roles[role].api_version_candidates[0],
        }
        for role in contract.ROLES
    }
    qualification = runner._qualify(book, _QualificationCaller())
    receipt = {
        "artifact": "phase1_0d_rv2_provider_qualification_receipt",
        "run_id": "20260803T000000Z",
        **runner._instrument_header(book),
        "review_code_commit": "1" * 40,
        "review_image_digest": "sha256:" + "2" * 64,
        **qualification,
    }
    raw = contract.canonical_json(receipt).encode("utf-8")
    import hashlib

    objects = {
        "q/00_gate_receipt.json": raw,
        "q/artifact_manifest.json": contract.canonical_json(
            {
                "file_count": 1,
                "manifest_written_last": True,
                "files": [
                    {
                        "name": "00_gate_receipt.json",
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                ]
            }
        ).encode("utf-8"),
    }
    observed = runner._load_qualification_receipt(_FakeBlob(objects), "q", book)
    assert observed["passed"] is True
    assert observed["counts"]["valid_expected_label_matches"] == 3


# --------------------------------------------------------------------------
# build provenance
# --------------------------------------------------------------------------


def test_the_three_bundles_are_disjoint():
    v2 = set(prov2.BUNDLE_GLOBS)
    assert not v2 & set(prov1.BUNDLE_GLOBS)
    assert not v2 & set(prov0.BUNDLE_GLOBS)
    assert prov2.BUNDLE_HASH_DOMAIN not in {
        prov1.BUNDLE_HASH_DOMAIN,
        prov0.BUNDLE_HASH_DOMAIN,
    }


def test_the_v2_record_matches_the_committed_bundle():
    assert RECORD.exists()
    result = prov2.verify_image_context(REPO_ROOT, RECORD)
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert result["bundle_sha256"] == record["bundle_sha256"]
    assert record["file_count"] == len(record["files"])


def test_the_instrument_check_binds_every_section_eight_hash():
    observed = prov2.verify_instrument(REPO_ROOT, RECORD)
    assert observed["addendum_sha256"] == prov2.ADDENDUM_SHA256
    assert observed["rubric_sha256"] == prov2.RUBRIC_SHA256
    assert observed["fixture_bank_sha256"] == prov2.FIXTURE_BANK_SHA256
    assert observed["base_protocol_sha256"] == prov2.PROTOCOL_SHA256
    assert observed["task_ids_sha256"] == prov2.TASK_IDS_SHA256
    assert observed["generation_image_digest"] == prov2.GENERATION_IMAGE_DIGEST
    assert set(observed["reviewer_ids"]) == {"primary", "secondary", "third"}
    assert len(set(observed["request_profile_sha256"].values())) == 3


def test_the_instrument_check_refuses_a_moved_hash(monkeypatch):
    monkeypatch.setattr(prov2, "RUBRIC_SHA256", "0" * 64)
    with pytest.raises(prov2.ReviewV2ProvenanceError):
        prov2.verify_instrument(REPO_ROOT, RECORD)


def test_every_v1_gate_manifest_entry_is_verified(tmp_path):
    source = (
        REPO_ROOT
        / "artifacts/phase1-0d-semantic-review-gate/20260803T031343Z"
    )
    copied = tmp_path / "gate"
    shutil.copytree(source, copied)
    result = prov2.verify_manifest_tree(copied, copied / "artifact_manifest.json")
    assert result["file_count"] == 3

    transcript = copied / "01_qualification_console_transcript.txt"
    transcript.write_bytes(transcript.read_bytes() + b"tampered\n")
    with pytest.raises(prov2.ReviewV2ProvenanceError):
        prov2.verify_manifest_tree(copied, copied / "artifact_manifest.json")


def test_no_target_output_is_present_in_the_build_context():
    assert prov2.verify_no_target_output(REPO_ROOT)["found"] == 0


def test_a_planted_target_pack_is_refused(tmp_path):
    (tmp_path / "artifacts/phase1-0d-confirmation/run").mkdir(parents=True)
    (tmp_path / "artifacts/phase1-0d-confirmation/run/02_records.jsonl").write_text("{}")
    with pytest.raises(prov2.ReviewV2ProvenanceError):
        prov2.verify_no_target_output(tmp_path)


def test_emit_refuses_a_short_commit():
    with pytest.raises(prov2.ReviewV2ProvenanceError):
        prov2.build_record(REPO_ROOT, "abc123")


# --------------------------------------------------------------------------
# the image
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def test_the_base_image_is_digest_pinned(dockerfile):
    assert f"FROM {prov2.BASE_IMAGE}@{prov2.BASE_IMAGE_DIGEST}" in dockerfile


def test_the_build_chains_every_required_verification(dockerfile):
    for command in (
        "verify-runtime",
        "verify-image-context",
        "verify-protocol",
        "verify-instrument",
        "verify-no-target-output",
    ):
        assert command in dockerfile
    assert "COPY .dockerignore" in dockerfile
    assert dockerfile.count("/workspace/.dockerignore") == 2


def test_the_build_verifies_but_never_rewrites_the_v1_review_surface(dockerfile):
    assert "phase1_0d_review_build_provenance.json /workspace/" in dockerfile
    assert "phase1_0d_review_build_provenance.py" in dockerfile
    assert "--provenance /workspace/phase1_0d_review_build_provenance.json" in dockerfile
    assert "phase1-0d-review-v2-build-provenance.json" in dockerfile
    assert "j-space-observation-phase1-0d-review:" not in dockerfile


def test_the_image_runs_unprivileged_and_defaults_to_qualify(dockerfile):
    assert "USER 10001:10001" in dockerfile
    assert "run_phase1_0d_semantic_review_v2.py" in dockerfile
    assert '"qualify"' in dockerfile
    assert '"smoke"' not in dockerfile
    assert '"review"' not in dockerfile


def test_the_image_declares_its_claim_boundary(dockerfile):
    assert "not human ground truth" in dockerfile
    assert "L-52" in dockerfile
    assert "hidden reasoning" in dockerfile


# --------------------------------------------------------------------------
# the Azure launchers
# --------------------------------------------------------------------------


def test_the_build_uses_a_separate_repository_and_locks_both_objects():
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert 'IMAGE_REPOSITORY="j-space-observation-phase1-0d-review-v2"' in text
    assert 'V1_REVIEW_REPOSITORY="j-space-observation-phase1-0d-review"' in text
    assert 'GENERATION_REPOSITORY="j-space-observation-phase1-0d"' in text
    assert "--write-enabled false --delete-enabled false" in text
    assert "is still enabled after locking" in text
    assert "already exists; use a new commit" in text
    assert "az acr build" in text
    assert "--overwrite false" in text
    assert 'BUILD_LOCK_PREFIX="phase1-0d-semantic-review-v2/build-locks"' in text
    assert 'git -C "$PROJECT_ROOT" archive --format=tar "$PROJECT_SHA"' in text
    assert '"$BUILD_CONTEXT"' in text
    assert 'LOCKED_TAG_DIGEST' in text


def test_the_build_requires_a_clean_committed_provenance_record():
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert prov2.RECORD_PATH in text
    assert "build-provenance record is missing" in text
    assert "Refusing to build a dirty worktree" in text


def test_the_runner_uses_the_registered_gate_prefixes():
    text = RUN_SCRIPT.read_text(encoding="utf-8")
    assert (
        'QUALIFICATION_PREFIX="phase1-0d-semantic-review-v2/qualification"'
        in text
    )
    assert 'SMOKE_PREFIX="phase1-0d-semantic-review-v2/smoke"' in text
    assert "--qualification-receipt-prefix" in text
    assert "--gate-receipt-prefix" in text
    assert "--gate-blob-prefix" in text


def test_the_runner_enforces_the_one_round_smoke_ceiling():
    text = RUN_SCRIPT.read_text(encoding="utf-8")
    assert '[[ "$REVIEW_MODE" == "smoke" && "$JOB_EXISTS" != "0" ]]' in text
    assert "one-round ceiling is already spent; no RV3 is authorised" in text
    assert 'SMOKE_LOCK_BLOB="phase1-0d-semantic-review-v2/smoke-round-lock.json"' in text
    assert "--overwrite false" in text
    assert "Atomic service-side one-round lock" in text


def test_the_runner_uses_a_locked_digest_and_no_platform_retry():
    text = RUN_SCRIPT.read_text(encoding="utf-8")
    assert (
        'IMAGE_DIGEST_REF="${LOGIN_SERVER}/${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"'
        in text
    )
    assert '"replicaRetryLimit": 0' in text
    assert '"parallelism": 1' in text
    assert '"replicaCompletionCount": 1' in text
    assert "V2 review image is not locked; refusing to launch" in text


def test_the_runner_carries_no_storage_secret_or_volume():
    text = RUN_SCRIPT.read_text(encoding="utf-8")
    assert "ACCOUNT_KEY" not in "\n".join(
        line for line in text.splitlines() if '{"name":' in line
    )
    assert '"volumes":' not in text
    assert "AZURE_CLIENT_ID" in text
    assert "credential-bearing variables present" in text


def test_only_review_receives_a_generation_prefix():
    text = RUN_SCRIPT.read_text(encoding="utf-8")
    case = text.rsplit('case "$REVIEW_MODE" in', 1)[1].split("esac", 1)[0]
    qualify = case.split("qualify)", 1)[1].split(";;", 1)[0]
    smoke = case.split("smoke)", 1)[1].split(";;", 1)[0]
    review = case.split("review)", 1)[1].split(";;", 1)[0]
    assert "--pack-blob-prefix" not in qualify
    assert "--pack-blob-prefix" not in smoke
    assert "--pack-blob-prefix" in review


def test_the_new_shell_scripts_are_lf_normalised():
    for path in (BUILD_SCRIPT, RUN_SCRIPT):
        assert b"\r\n" not in path.read_bytes()


def test_the_new_shell_scripts_parse_as_bash():
    for path in (BUILD_SCRIPT, RUN_SCRIPT):
        result = subprocess.run(
            ["bash", "-n", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


def test_docker_context_reincludes_only_the_required_historical_evidence():
    text = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "artifacts/*" in text
    root = "artifacts/phase1-0d-semantic-review-gate/20260803T031343Z/"
    for name in (
        "00_gate_receipt.json",
        "01_qualification_console_transcript.txt",
        "02_smoke_console_transcript.txt",
        "artifact_manifest.json",
    ):
        assert f"!{root}{name}" in text
