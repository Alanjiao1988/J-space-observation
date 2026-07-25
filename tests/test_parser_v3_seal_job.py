"""Targeted tests for the parser-v3-v1 pre-seal cross-check and gated seal.

Model-free, offline, and deliberately built on synthetic corpora: the real
retired parser-v2 holdout is never contacted and the real locked labels are
never read.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts import build_parser_v3_validation_set as builder  # noqa: E402
from scripts import emit_track_d1_artifacts as packer  # noqa: E402
from scripts import parser_v3_seal_job as job  # noqa: E402

BUILDER_PATH = ROOT / "scripts" / "build_parser_v3_validation_set.py"
INPUTS_MANIFEST = ROOT / "evaluator_sets" / "parser_v3_v1" / "manifests" / "inputs_manifest.json"
LOCKED_INPUTS = ROOT / "evaluator_sets" / "parser_v3_v1" / "locked_inputs.jsonl"

PARSER_V3_LF_SHA256 = "dd729c3c23771fb112811e382bf7e55f531ce534cbbd1cfec4f0527056c8908e"

# ------------------------------------------------------------- fake storage


class _Download:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def readall(self) -> bytes:
        return self._payload


class _Conflict(RuntimeError):
    pass


class _Blob:
    def __init__(self, service: "FakeService", name: str) -> None:
        self._service = service
        self._name = name

    def upload_blob(self, data: bytes, overwrite: bool = True) -> None:
        if self._name in self._service.store and not overwrite:
            raise _Conflict(f"blob already exists: {self._name}")
        self._service.store[self._name] = bytes(data)
        self._service.writes.append(self._name)
        self._service.etags[self._name] = f'"etag-{len(self._service.store)}"'

    def download_blob(self) -> _Download:
        self._service.reads.append(self._name)
        if self._name not in self._service.store:
            raise KeyError(self._name)
        return _Download(self._service.store[self._name])

    def get_blob_properties(self) -> dict:
        return {
            "size": len(self._service.store[self._name]),
            "etag": self._service.etags[self._name],
        }


class _Container:
    def __init__(self, service: "FakeService") -> None:
        self._service = service

    def list_blobs(self, name_starts_with=None):
        self._service.list_calls.append(name_starts_with)
        if not name_starts_with:
            raise PermissionError(
                "AuthorizationPermissionMismatch: an unprefixed listing is denied "
                "by the prefix-conditioned grant"
            )
        return [
            type("Item", (), {"name": name})()
            for name in sorted(self._service.store)
            if name.startswith(name_starts_with)
        ]


class FakeService:
    def __init__(self, store: dict[str, bytes] | None = None) -> None:
        self.store: dict[str, bytes] = dict(store or {})
        self.etags: dict[str, str] = {
            name: f'"etag-seed-{index}"' for index, name in enumerate(self.store)
        }
        self.writes: list[str] = []
        self.reads: list[str] = []
        self.opened: list[str] = []
        self.list_calls: list[str | None] = []

    def get_container_client(self, container: str) -> _Container:
        return _Container(self)

    def get_blob_client(self, container: str, blob: str) -> _Blob:
        self.opened.append(blob)
        return _Blob(self, blob)


# ------------------------------------------------------------- synthetic set


def _synthetic_manifest(tmp_path: Path, texts: list[str]) -> Path:
    records = []
    for index, text in enumerate(texts):
        marks = builder.fingerprints(text)
        records.append({"case_id": f"PV3-synthetic-{index:03d}", **marks})
    payload = {
        "schema_version": "phase1-parser-v3-inputs-manifest/v1",
        "set_id": "parser-v3-v1",
        "record_count": len(records),
        "records": records,
    }
    path = tmp_path / "inputs_manifest.json"
    path.write_bytes(job.canonical_json_bytes(payload))
    return path


def _new_texts() -> list[str]:
    return [f"new holdout fixture {index} yields {index + 1}/7" for index in range(120)]


def _retired_payload(texts: list[str]) -> bytes:
    lines = []
    for index, text in enumerate(texts):
        lines.append(
            json.dumps(
                {
                    "schema_version": job.RETIRED_INPUT_SCHEMA_VERSION,
                    "case_id": f"PV2-synthetic-{index:03d}",
                    "source_kind": "synthetic",
                    "output_text": text,
                    "parse_type": "numeric",
                },
                sort_keys=True,
            )
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _service_with_retired(payload: bytes) -> FakeService:
    return FakeService({job.RETIRED_INPUTS_BLOB: payload})


# --------------------------------------------------- fingerprint registration


def test_registered_builder_reproduces_the_pinned_vectors():
    summary = job.verify_fingerprint_registration(builder)
    assert summary["status"] == "verified"
    assert summary["vectors"] == len(job.FINGERPRINT_KNOWN_ANSWERS)


def test_cross_check_refuses_to_run_with_a_divergent_normaliser(tmp_path):
    class Divergent:
        @staticmethod
        def normalize_text(text: str) -> str:
            return text

        @staticmethod
        def numeric_normalized_text(text: str) -> str:
            return text

        @staticmethod
        def fingerprints(text: str) -> dict[str, str]:
            digest = job.sha256_bytes(text.encode("utf-8"))
            return {field: digest for field in job._KAT_FIELDS}

    with pytest.raises(job.RegistrationError):
        job.verify_fingerprint_registration(Divergent)


def test_run_aborts_when_the_imported_functions_are_not_registered(tmp_path):
    fake_builder = tmp_path / "build_parser_v3_validation_set.py"
    fake_builder.write_text(
        "import hashlib\n"
        "def normalize_text(text):\n    return text\n"
        "def numeric_normalized_text(text):\n    return text\n"
        "def fingerprints(text):\n"
        "    d = hashlib.sha256(text.encode('utf-8')).hexdigest()\n"
        "    return {k: d for k in ('exact_sha256', 'normalized_sha256',\n"
        "        'numeric_normalized_sha256', 'masked_template_sha256')}\n",
        encoding="utf-8",
    )
    manifest = _synthetic_manifest(tmp_path, _new_texts())
    service = _service_with_retired(_retired_payload(["unrelated retired text 1"]))
    sys.modules.pop("_jspace_parser_v3_fingerprints", None)
    with pytest.raises(job.RegistrationError):
        job.run(
            mode="crosscheck",
            account="stjspacefiles0709085305",
            container="jspace-results",
            seal_timestamp=None,
            builder_path=fake_builder,
            manifest_path=manifest,
            locked_inputs=None,
            payload_dir=None,
            repo_root=None,
            environment={"AZURE_CLIENT_ID": "x"},
            service_factory=lambda: service,
            emit=lambda *_: None,
        )
    sys.modules.pop("_jspace_parser_v3_fingerprints", None)
    assert service.writes == []
    assert service.reads == []


@pytest.mark.skipif(
    not LOCKED_INPUTS.is_file(), reason="locked inputs are private holdout material"
)
def test_manifest_reproduction_matches_the_committed_manifest():
    manifest = json.loads(INPUTS_MANIFEST.read_text(encoding="utf-8"))
    result = job.verify_manifest_reproduction(builder, manifest, LOCKED_INPUTS)
    assert result == {"status": "verified", "records": 120}


# ------------------------------------------------------------------ isolation


def test_retired_source_prefix_is_a_constant_and_names_only_inputs():
    assert job.RETIRED_INPUTS_PREFIX.endswith("/locked-inputs/")
    assert job.RETIRED_INPUTS_BLOB.endswith("/locked_inputs.jsonl")
    with pytest.raises(job.JobAbort):
        job.assert_source_prefix_is_locked_inputs(
            "phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-labels/"
        )
    with pytest.raises(job.JobAbort):
        job.assert_source_prefix_is_locked_inputs("phase1-evaluator-validation/")


@pytest.mark.parametrize(
    "name",
    [
        "phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-labels/locked_reference_labels.jsonl",
        "phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/../locked-labels/x.jsonl",
        "phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/scores/ledger.jsonl",
        "phase1-evaluator-validation/parser-v2-v1/20260716T024856Z/locked-inputs/stage1_consensus.jsonl",
    ],
)
def test_label_and_score_paths_are_refused(name):
    with pytest.raises(job.JobAbort):
        job.assert_blob_name_is_readable(name)


def test_a_retired_record_with_a_label_field_aborts_before_its_values_are_read():
    label_key = "expected_" + "parsed_answer"
    payload = (
        json.dumps(
            {
                "schema_version": job.RETIRED_INPUT_SCHEMA_VERSION,
                "case_id": "PV2-x",
                "source_kind": "synthetic",
                "output_text": "some text",
                "parse_type": "numeric",
                label_key: "17",
            },
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    with pytest.raises(job.JobAbort) as error:
        job.retired_texts_from_bytes(payload)
    assert "label-free schema" in str(error.value)
    assert "17" not in str(error.value)


def test_the_report_may_not_carry_retired_text():
    text = "a retired output body that must never come back"
    with pytest.raises(job.JobAbort):
        job.assert_report_is_text_free({"note": text}, [text])
    job.assert_report_is_text_free({"note": "counts only"}, [text])


def test_listings_always_carry_a_prefix():
    service = _service_with_retired(_retired_payload(["retired text one"]))
    job.list_retired_inputs(service, "jspace-results")
    assert service.list_calls
    assert all(
        isinstance(value, str) and value.startswith("phase1-evaluator-validation/")
        for value in service.list_calls
    )


# ----------------------------------------------------------------- decisions


def _run(tmp_path, retired_texts, mode, service=None, seal_timestamp=None):
    manifest = _synthetic_manifest(tmp_path, _new_texts())
    service = service or _service_with_retired(_retired_payload(retired_texts))
    sys.modules.pop("_jspace_parser_v3_fingerprints", None)
    code, summary = job.run(
        mode=mode,
        account="stjspacefiles0709085305",
        container="jspace-results",
        seal_timestamp=seal_timestamp,
        builder_path=BUILDER_PATH,
        manifest_path=manifest,
        locked_inputs=None,
        payload_dir=None,
        repo_root=ROOT,
        environment={"AZURE_CLIENT_ID": "x"},
        service_factory=lambda: service,
        emit=lambda *_: None,
    )
    sys.modules.pop("_jspace_parser_v3_fingerprints", None)
    return code, summary, service


def test_disjoint_corpora_pass_and_read_only_the_inputs_leaf(tmp_path, monkeypatch):
    retired = [f"retired parser-v2 fixture {index} says {index}/13" for index in range(60)]
    monkeypatch.setattr(
        job,
        "RETIRED_INPUTS_REGISTERED_SHA256",
        job.sha256_bytes(_retired_payload(retired)),
    )
    code, summary, service = _run(tmp_path, retired, "crosscheck")
    report = summary["crosscheck"]
    assert code == 0
    assert report["cross_check"] == "PASS"
    assert report["decision"] == "PROCEED_TO_SEAL"
    assert report["new_count"] == 120
    assert report["retired_count"] == 60
    assert report["exact_collision_count"] == 0
    assert report["normalised_collision_count"] == 0
    assert report["numeric_normalised_collision_count"] == 0
    assert report["source"]["registered_sha256_match"] is True
    assert set(service.opened) == {job.RETIRED_INPUTS_BLOB}
    assert service.writes == []
    blob = json.dumps(report, ensure_ascii=False)
    for text in retired:
        assert text not in blob


def test_a_planted_collision_fails_and_blocks_the_seal(tmp_path, monkeypatch):
    collider = _new_texts()[7]
    retired = ["retired fixture zero says 1/13", collider]
    monkeypatch.setattr(
        job,
        "RETIRED_INPUTS_REGISTERED_SHA256",
        job.sha256_bytes(_retired_payload(retired)),
    )
    code, summary, service = _run(
        tmp_path, retired, "seal", seal_timestamp="20260725T160000Z"
    )
    report = summary["crosscheck"]
    assert code == 2
    assert summary["state"] == "BLOCKED_COLLISION"
    assert summary["seal"] is None
    assert report["cross_check"] == "FAIL"
    assert report["decision"] == "DO_NOT_SEAL"
    assert report["exact_collision_count"] == 1
    assert report["normalised_collision_count"] == 1
    assert report["numeric_normalised_collision_count"] == 1
    assert report["collisions"]["exact"][0]["new_case_id"] == "PV3-synthetic-007"
    assert report["collisions"]["exact"][0]["sha256"]
    sealed = [name for name in service.writes if "-runlog/" not in name]
    assert sealed == []


def test_a_provenance_mismatch_aborts_and_is_not_a_pass(tmp_path):
    retired = ["retired fixture zero says 1/13"]
    code, summary, service = _run(tmp_path, retired, "seal", seal_timestamp="20260725T160000Z")
    report = summary["crosscheck"]
    assert code == 3
    assert summary["state"] == "BLOCKED_INFRASTRUCTURE"
    assert report["cross_check"] == "ABORT"
    assert report["cross_check"] != "PASS"
    assert report["abort_reasons"]
    assert [name for name in service.writes if "-runlog/" not in name] == []


# --------------------------------------------------------------------- seal


def _payload_service(retired: list[str]) -> FakeService:
    return _service_with_retired(_retired_payload(retired))


def test_seal_writes_twelve_objects_with_the_set_manifest_last(tmp_path, monkeypatch):
    retired = [f"retired parser-v2 fixture {index} says {index}/13" for index in range(60)]
    monkeypatch.setattr(
        job,
        "RETIRED_INPUTS_REGISTERED_SHA256",
        job.sha256_bytes(_retired_payload(retired)),
    )
    service = _payload_service(retired)
    stamp = "20260725T161500Z"
    code, summary, _ = _run(tmp_path, retired, "seal", service=service, seal_timestamp=stamp)
    assert code == 0
    assert summary["state"] == "SEALED"
    record = summary["seal"]
    assert record["status"] == "SEALED"
    assert record["object_count"] == 12
    assert record["membership_check"]["exact_match"] is True
    parent = f"{job.SEAL_ROOT}/{stamp}"
    sealed = [name for name in service.writes if name.startswith(parent + "/")]
    assert len(sealed) == 12
    assert sealed[-1] == f"{parent}/manifests/set_manifest.json"
    assert sealed[0] == f"{parent}/locked-inputs/locked_inputs.jsonl"
    assert set(sealed) == set(job.seal_blob_names(stamp))
    assert record["written_last"] == sealed[-1]
    runlog = [name for name in service.writes if name.startswith(f"{parent}-runlog/")]
    assert runlog == [
        f"{parent}-runlog/crosscheck_report.json",
        f"{parent}-runlog/seal_record.json",
    ]
    assert record["account_key_used"] is False
    assert record["sas_used"] is False


def test_seal_refuses_a_non_empty_parent_prefix(tmp_path, monkeypatch):
    retired = [f"retired parser-v2 fixture {index} says {index}/13" for index in range(60)]
    monkeypatch.setattr(
        job,
        "RETIRED_INPUTS_REGISTERED_SHA256",
        job.sha256_bytes(_retired_payload(retired)),
    )
    stamp = "20260725T162000Z"
    service = _payload_service(retired)
    service.store[f"{job.SEAL_ROOT}/{stamp}/manifests/inputs_manifest.json"] = b"x"
    service.etags[f"{job.SEAL_ROOT}/{stamp}/manifests/inputs_manifest.json"] = '"e"'
    with pytest.raises(job.JobAbort) as error:
        _run(tmp_path, retired, "seal", service=service, seal_timestamp=stamp)
    assert "already happened" in str(error.value)


def test_seal_aborts_on_a_local_digest_mismatch(tmp_path):
    payload_dir = tmp_path / "payload"
    payload_dir.mkdir()
    for item in job.SEAL_OBJECTS:
        (payload_dir / str(item["name"])).write_bytes(b"tampered")
    with pytest.raises(job.JobAbort) as error:
        job.load_seal_payload(payload_dir, None)
    assert "mismatch" in str(error.value)


def test_upload_is_overwrite_false():
    service = FakeService()
    job.upload_one(service, "jspace-results", "a/b.json", b"one")
    with pytest.raises(job.JobAbort) as error:
        job.upload_one(service, "jspace-results", "a/b.json", b"two")
    assert "overwrite-false" in str(error.value)
    assert service.store["a/b.json"] == b"one"


def test_seal_timestamp_shape_is_enforced():
    assert job.seal_parent_prefix("20260725T161500Z").endswith("/20260725T161500Z")
    for bad in ("2026-07-25T16:15:00Z", "20260725161500Z", "", "latest"):
        with pytest.raises(job.JobAbort):
            job.seal_parent_prefix(bad)


def test_the_twelve_objects_match_the_registered_specification():
    spec = (ROOT / "docs" / "phase1_parser_v3_sealing_run.md").read_text(encoding="utf-8")
    block = spec.split("expected = {", 1)[1].split("}", 1)[0]
    registered = {
        match.group(1)
        for match in re.finditer(r'"<parent>/([^"]+)"', block)
    }
    assert len(registered) == 12
    produced = {
        name.split("/20260725T161500Z/", 1)[1]
        for name in job.seal_blob_names("20260725T161500Z")
    }
    assert produced == registered


def test_local_seal_objects_match_their_registered_digests():
    missing = [
        item["source"]
        for item in job.SEAL_OBJECTS
        if not (ROOT / str(item["source"])).is_file()
    ]
    if missing:
        pytest.skip(f"private holdout material is absent: {missing}")
    loaded = job.load_seal_payload(None, ROOT)
    assert len(loaded) == 12
    assert [item["order"] for item in loaded] == list(range(1, 13))


# ------------------------------------------------------------ secrecy in git


def _check_ignore(relative: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "check-ignore", "-v", relative],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_no_secret_path_is_stageable_in_git():
    private = [
        "evaluator_sets/parser_v3_v1/locked_inputs.jsonl",
        "evaluator_sets/parser_v3_v1/locked_labels.jsonl",
        "evaluator_sets/parser_v3_v1/reviewer_a_locked_labels.jsonl",
        "evaluator_sets/parser_v3_v1/reviewer_b_locked_labels.jsonl",
        "evaluator_sets/parser_v3_v1/arbitration_locked_labels.jsonl",
        "evaluator_sets/parser_v3_v1/private/salts.json",
    ]
    for relative in private:
        result = _check_ignore(relative)
        assert result.returncode == 0, f"{relative} is not gitignored"
        assert ".gitignore:" in result.stdout
        assert not result.stdout.strip().endswith(".gitignore:0:\t" + relative)
    public = [
        "evaluator_sets/parser_v3_v1/manifests/inputs_manifest.json",
        "evaluator_sets/parser_v3_v1/manifests/labels_manifest.json",
        "evaluator_sets/parser_v3_v1/manifests/set_manifest.json",
        "scripts/parser_v3_seal_job.py",
        "scripts/stage_parser_v3_seal_payload.py",
        "scripts/emit_track_d1_artifacts.py",
        "docs/phase1_parser_v3_seal_job_spec.md",
        "artifacts/phase1-evaluator-validation/track-d1",
    ]
    for relative in public:
        assert _check_ignore(relative).returncode == 1, f"{relative} is gitignored"
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    leaked = [
        line
        for line in status.splitlines()
        if re.search(r"locked_inputs|locked_labels|_locked_labels|parser_v3_v1/private/", line)
    ]
    assert leaked == [], leaked


def test_the_authored_artifacts_carry_no_case_text_or_label_values():
    authored = [
        ROOT / "scripts" / "parser_v3_seal_job.py",
        ROOT / "scripts" / "stage_parser_v3_seal_payload.py",
        ROOT / "scripts" / "emit_track_d1_artifacts.py",
        ROOT / "docs" / "phase1_parser_v3_seal_job_spec.md",
    ]
    texts = (
        [
            json.loads(line)["output_text"]
            for line in LOCKED_INPUTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if LOCKED_INPUTS.is_file()
        else []
    )
    for path in authored:
        blob = path.read_text(encoding="utf-8")
        for text in texts:
            assert text not in blob, path.name
        assert not re.search(r"PV3-[0-9a-f]{20}", blob), path.name


def test_parser_v3_source_is_untouched():
    payload = (ROOT / "src" / "jspace_observation" / "eval_parsing_v3.py").read_bytes()
    lf = payload.replace(b"\r\n", b"\n")
    assert job.sha256_bytes(lf) == PARSER_V3_LF_SHA256


# ------------------------------------------------------------- artifact pack


def _pack(tmp_path, summary=None, run_id="20260725T170000Z-track-d1-test"):
    root = packer.build_pack(
        run_id, generated_at="2026-07-25T17:00:00Z", job_summary=summary, out_root=tmp_path
    )
    return root, json.loads((root / "artifact_manifest.json").read_text(encoding="utf-8"))


def test_pack_uses_the_existing_schema_and_writes_the_manifest_last(tmp_path):
    run_dir, manifest = _pack(tmp_path)
    names = sorted(path.name for path in run_dir.iterdir() if path.is_file())
    assert names == sorted(list(packer.WRITE_ORDER) + ["artifact_manifest.json"])
    assert manifest["manifest_written_last"] is True
    assert manifest["write_order"] == list(packer.WRITE_ORDER) + ["artifact_manifest.json"]
    for entry in manifest["files"]:
        payload = (run_dir / entry["path"]).read_bytes()
        assert len(payload) == entry["bytes"]
        assert job.sha256_bytes(payload) == entry["sha256"]
        assert entry["status"] in {"ok", "not_applicable"}
        if entry["status"] == "not_applicable":
            assert entry["reason"]
    assert (run_dir / "03_metrics.csv").read_text(encoding="utf-8").splitlines()[
        0
    ] == packer.METRICS_HEADER


def test_pack_states_are_restricted_and_never_upgrade_not_performed(tmp_path):
    run_dir, manifest = _pack(tmp_path)
    assert manifest["status"] == "BLOCKED_INFRASTRUCTURE"
    assert manifest["status"] in packer.ALLOWED_STATES
    decision = json.loads((run_dir / "04_decision.json").read_text(encoding="utf-8"))
    assert decision["status"] == "BLOCKED_INFRASTRUCTURE"
    assert decision["cross_check"]["verdict"] == "NOT PERFORMED"
    assert decision["cross_check"]["executed"] is False
    summary_text = (run_dir / "05_summary.md").read_text(encoding="utf-8")
    assert "NOT PERFORMED" in summary_text
    assert "VACUOUS" in summary_text
    joined = " ".join(decision["prohibited_interpretations"]).lower()
    assert "no parser-v3 evaluation was run" in joined
    assert "no parser-v3 result exists" in joined
    metrics = (run_dir / "03_metrics.csv").read_text(encoding="utf-8")
    for row in metrics.splitlines()[1:]:
        if "collision_count" in row and "crosscheck_1" in row:
            assert ",true," not in row


def test_pack_reports_a_collision_as_blocked_collision(tmp_path):
    summary = {
        "state": "BLOCKED_COLLISION",
        "crosscheck": {
            "cross_check": "FAIL",
            "new_count": 120,
            "retired_count": 60,
            "exact_collision_count": 1,
            "normalised_collision_count": 1,
            "numeric_normalised_collision_count": 1,
            "abort_reasons": [],
        },
        "seal": None,
    }
    run_dir, manifest = _pack(tmp_path, summary, run_id="20260725T170500Z-track-d1-test")
    assert manifest["status"] == "BLOCKED_COLLISION"
    decision = json.loads((run_dir / "04_decision.json").read_text(encoding="utf-8"))
    assert decision["criteria_failed"]
    assert "do not swap cases" in decision["next_gate"].lower()


def test_pack_reports_a_successful_seal_as_sealed(tmp_path):
    summary = {
        "state": "SEALED",
        "crosscheck": {
            "cross_check": "PASS",
            "new_count": 120,
            "retired_count": 60,
            "exact_collision_count": 0,
            "normalised_collision_count": 0,
            "numeric_normalised_collision_count": 0,
            "abort_reasons": [],
        },
        "seal": {
            "parent_prefix": f"{job.SEAL_ROOT}/20260725T161500Z",
            "written_last": f"{job.SEAL_ROOT}/20260725T161500Z/manifests/set_manifest.json",
            "objects": [
                {
                    "blob_name": name,
                    "etag": '"etag"',
                    "roundtrip_verified": True,
                }
                for name in job.seal_blob_names("20260725T161500Z")
            ],
        },
    }
    run_dir, manifest = _pack(tmp_path, summary, run_id="20260725T171000Z-track-d1-test")
    assert manifest["status"] == "SEALED"
    rows = [
        json.loads(line)
        for line in (run_dir / "02_records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 13
    assert sum(1 for row in rows if row["status"] == "sealed") == 12
    assert rows[-1]["status"] == "pass"


def test_pack_carries_no_case_text_or_label_values(tmp_path):
    run_dir, _ = _pack(tmp_path)
    texts = (
        [
            json.loads(line)["output_text"]
            for line in LOCKED_INPUTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if LOCKED_INPUTS.is_file()
        else []
    )
    for path in sorted(run_dir.iterdir()):
        blob = path.read_text(encoding="utf-8")
        assert "expected_" + "parsed_answer" not in blob, path.name
        assert "expected_" + "answer_presence" not in blob, path.name
        for text in texts:
            assert text not in blob, path.name


def test_staging_refuses_a_target_inside_the_repository():
    from scripts import stage_parser_v3_seal_payload as staging

    with pytest.raises(staging.StagingError):
        staging.validate_external_context(ROOT / "scratch_agentd_context")
    with pytest.raises(staging.StagingError):
        staging.validate_external_context(ROOT)


# --------------------------------------------------- pack built from evidence


def _evidence(tmp_path, *, report_overrides=None, record_overrides=None):
    """The two durable runlog objects, in the shape the real job writes them."""
    stamp = "20260725T161500Z"
    report = {
        "schema_version": "phase1-parser-v3-preseal-crosscheck/v1",
        "cross_check": "PASS",
        "decision": "PROCEED_TO_SEAL",
        "new_count": 120,
        "retired_count": 120,
        "exact_collision_count": 0,
        "normalised_collision_count": 0,
        "numeric_normalised_collision_count": 0,
        "collisions": {"exact": [], "normalised": [], "numeric_normalised": []},
        "abort_reasons": [],
        "seal_timestamp": stamp,
    }
    report.update(report_overrides or {})
    report_path = tmp_path / "crosscheck_report.json"
    report_path.write_bytes(job.canonical_json_bytes(report))

    record = {
        "schema_version": "phase1-parser-v3-seal-record/v1",
        "status": "SEALED",
        "overwrite": False,
        "object_count": len(job.SEAL_OBJECTS),
        "parent_prefix": f"{job.SEAL_ROOT}/{stamp}",
        "written_last": f"{job.SEAL_ROOT}/{stamp}/manifests/set_manifest.json",
        "membership_check": {
            "expected": len(job.SEAL_OBJECTS),
            "observed": len(job.SEAL_OBJECTS),
            "exact_match": True,
        },
        "roundtrip_verification": "size, SHA-256 and ETag verified for all 12 objects",
        "crosscheck_report_sha256": job.sha256_bytes(report_path.read_bytes()),
        "crosscheck": {
            "verdict": report["cross_check"],
            "exact_collision_count": report["exact_collision_count"],
            "normalised_collision_count": report["normalised_collision_count"],
            "numeric_normalised_collision_count": report[
                "numeric_normalised_collision_count"
            ],
        },
        "objects": [
            {
                "order": int(item["order"]),
                "blob_name": f"{job.SEAL_ROOT}/{stamp}/{item['leaf']}/{item['name']}",
                "sha256": item["sha256"],
                "bytes": int(item["bytes"]),
                "etag": '"0x8DEEA66BB074CBA"',
                "roundtrip_verified": True,
            }
            for item in job.SEAL_OBJECTS
        ],
    }
    record.update(record_overrides or {})
    record_path = tmp_path / "seal_record.json"
    record_path.write_bytes(job.canonical_json_bytes(record))
    return report_path, record_path


def test_evidence_rebuilds_the_summary_without_inventing_fields(tmp_path):
    report_path, record_path = _evidence(tmp_path)
    summary = packer.summary_from_evidence(report_path, record_path)
    assert summary["state"] == "SEALED"
    assert summary["crosscheck"] == json.loads(report_path.read_text(encoding="utf-8"))
    assert summary["seal"] == json.loads(record_path.read_text(encoding="utf-8"))
    artifacts = {row["artifact"]: row for row in summary["evidence"]}
    assert set(artifacts) == {"crosscheck_report.json", "seal_record.json"}
    assert artifacts["crosscheck_report.json"]["sha256"] == job.sha256_bytes(
        report_path.read_bytes()
    )


def test_evidence_rejects_a_report_the_seal_record_does_not_pin(tmp_path):
    report_path, record_path = _evidence(
        tmp_path, record_overrides={"crosscheck_report_sha256": "00" * 32}
    )
    with pytest.raises(packer.EvidenceMismatch):
        packer.summary_from_evidence(report_path, record_path)


def test_evidence_rejects_a_verdict_that_disagrees_across_the_two_objects(tmp_path):
    report_path, record_path = _evidence(tmp_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["crosscheck"]["verdict"] = "FAIL"
    record_path.write_bytes(job.canonical_json_bytes(record))
    with pytest.raises(packer.EvidenceMismatch):
        packer.summary_from_evidence(report_path, record_path)


def test_evidence_rejects_sealed_bytes_that_differ_from_the_staged_bytes(tmp_path):
    report_path, record_path = _evidence(tmp_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["objects"][0]["sha256"] = "11" * 32
    record_path.write_bytes(job.canonical_json_bytes(record))
    with pytest.raises(packer.EvidenceMismatch):
        packer.summary_from_evidence(report_path, record_path)


def test_evidence_rejects_a_seal_that_claims_overwrite_true(tmp_path):
    report_path, record_path = _evidence(tmp_path, record_overrides={"overwrite": True})
    with pytest.raises(packer.EvidenceMismatch):
        packer.summary_from_evidence(report_path, record_path)


def test_evidence_rejects_a_closure_record_that_is_not_the_set_manifest(tmp_path):
    stamp = "20260725T161500Z"
    report_path, record_path = _evidence(
        tmp_path,
        record_overrides={
            "written_last": f"{job.SEAL_ROOT}/{stamp}/locked-inputs/locked_inputs.jsonl"
        },
    )
    with pytest.raises(packer.EvidenceMismatch):
        packer.summary_from_evidence(report_path, record_path)


def test_evidence_without_a_seal_record_never_reports_sealed(tmp_path):
    report_path, _ = _evidence(tmp_path)
    summary = packer.summary_from_evidence(report_path)
    assert summary["state"] == "CROSSCHECK_PASS"
    assert summary["seal"] is None
    state, _reason = packer.resolve_state(summary)
    assert state == "BLOCKED_INFRASTRUCTURE"


def test_evidence_driven_pack_is_sealed_and_records_the_abac_finding(tmp_path):
    report_path, record_path = _evidence(tmp_path)
    summary = packer.summary_from_evidence(report_path, record_path)
    execution = json.loads(
        (ROOT / "docs" / "phase1_parser_v3_seal_execution_record.json").read_text(
            encoding="utf-8"
        )
    )
    run_dir = packer.build_pack(
        "20260725T161500Z-track-d1-test",
        generated_at="2026-07-25T16:15:00Z",
        job_summary=summary,
        execution=execution,
        out_root=tmp_path / "pack",
    )
    manifest = json.loads((run_dir / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "SEALED"
    assert manifest["seal"]["object_count"] == 12
    assert manifest["evidence_sources"][0]["artifact"] == "crosscheck_report.json"

    deviations = json.loads((run_dir / "08_deviations.json").read_text(encoding="utf-8"))
    ids = {row["id"] for row in deviations["deviations"]}
    assert "D10-seal-timestamp-rotated-after-an-overwrite-false-abort" in ids
    assert "D11-image-retagged-not-rebuilt-for-the-second-timestamp" in ids
    assert "D12-shared-identity-instead-of-a-dedicated-one" in ids
    assert "D13-standing-unconditioned-role-meant-abac-enforced-nothing" in ids
    assert "D9-not-executed-in-this-round" not in ids

    decision = json.loads((run_dir / "04_decision.json").read_text(encoding="utf-8"))
    assert any("RBAC" in row for row in decision["criteria_failed"])
    text = (run_dir / "05_summary.md").read_text(encoding="utf-8")
    assert "enforced nothing" in text
    assert "licenses no claim about parser-v3 accuracy" in text

    texts = (
        [
            json.loads(line)["output_text"]
            for line in LOCKED_INPUTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if LOCKED_INPUTS.is_file()
        else []
    )
    for path in sorted(run_dir.iterdir()):
        blob = path.read_text(encoding="utf-8")
        assert "expected_" + "parsed_answer" not in blob, path.name
        assert "expected_" + "answer_presence" not in blob, path.name
        for case_text in texts:
            assert case_text not in blob, path.name


def test_the_teardown_expectation_is_recorded_as_measured_not_as_met():
    record = json.loads(
        (ROOT / "docs" / "phase1_parser_v3_seal_execution_record.json").read_text(
            encoding="utf-8"
        )
    )
    roles = record["teardown"]["sealing_identity_blob_roles"]
    assert roles["count"] == 1
    assert roles["expected_by_spec"] == 0
    assert roles["matches_expectation"] is False
    assert roles["standing_assignment"]["condition"] is None

    spec = (ROOT / "docs" / "phase1_parser_v3_seal_job_spec.md").read_text(
        encoding="utf-8"
    )
    assert "record the actual value" in spec.lower()


def test_the_pre_execution_pack_still_refuses_to_claim_a_result(tmp_path):
    _run_dir, manifest = _pack(tmp_path, None, run_id="20260725T172000Z-track-d1-test")
    assert manifest["status"] == "BLOCKED_INFRASTRUCTURE"
    assert manifest["cross_check"]["verdict"] == "NOT PERFORMED"
    assert manifest["seal"]["status"] == "not_applicable"
