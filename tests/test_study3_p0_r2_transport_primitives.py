"""P0-R2 transport primitives are disjoint, lossless and model-free."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
P0_R2_DIR = ROOT / "studies" / "study3" / "pilot" / "p0_r2"
P0_R1_DIR = ROOT / "studies" / "study3" / "pilot" / "p0_r1"
for path in (P0_R2_DIR, P0_R1_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _load(name, directory=P0_R2_DIR):
    path = directory / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TRANSPORT = _load("p0_r2_transport")
TRANSPORT_V1 = _load("p0_r2_transport_v1")
BLOB = _load("p0_r2_blob_transport")
BLOB_V1 = _load("p0_r2_blob_transport_v1")
JOURNAL = _load("p0_r2_journal_v1")
P0_R1_TRANSPORT = _load("p0_r1_transport", P0_R1_DIR)


def _payloads(size=2048):
    return {
        name: ((name + "|").encode("utf-8") * size)[:size]
        for name in TRANSPORT.REPLAY_ARTIFACTS
    }


def test_p0_r2_envelope_has_only_disjoint_canonical_artifacts():
    assert TRANSPORT.ENVELOPE_VERSION == \
        "study3-p0-r2-transport-envelope-v1"
    assert TRANSPORT.CHUNK_MARKER == "P0R2TXC"
    assert TRANSPORT.MANIFEST_MARKER == "P0R2TXM"
    assert TRANSPORT.COMPLETE_MARKER == "P0R2TXE"
    assert TRANSPORT.REPLAY_ARTIFACTS == (
        "p0_r2_replay_result.json",
        "p0_r2_replay_receipt.json",
        "p0_r2_replay_counters.json",
        "P0_R2_REPLAY_DISPOSITION.md",
    )
    assert not set(TRANSPORT.REPLAY_ARTIFACTS).intersection(
        P0_R1_TRANSPORT.REPLAY_ARTIFACTS)


def test_four_artifacts_round_trip_byte_exactly():
    payloads = _payloads()
    lines = TRANSPORT.encode("p0r2-g1-unit", payloads)
    assert max(len(line.encode("utf-8")) for line in lines) <= \
        TRANSPORT.MAX_LINE_BYTES
    recovered = TRANSPORT.recover("\n".join(lines), attempt_id="p0r2-g1-unit")
    assert recovered == payloads


def test_envelope_requires_exact_artifacts_and_p0_r2_attempt_namespace():
    payloads = _payloads()
    payloads.pop(TRANSPORT.REPLAY_ARTIFACTS[-1])
    with pytest.raises(TRANSPORT.TransportDefect):
        TRANSPORT.encode("p0r2-g1-incomplete", payloads)
    with pytest.raises(TRANSPORT.TransportDefect):
        TRANSPORT.encode("gen3-historical", _payloads())


def test_p0_r1_and_p0_r2_decoders_refuse_each_others_envelopes():
    p0_r2_lines = TRANSPORT.encode("p0r2-g1-unit", _payloads())
    with pytest.raises(P0_R1_TRANSPORT.TransportDefect):
        P0_R1_TRANSPORT.recover("\n".join(p0_r2_lines))

    p0_r1_payloads = {
        name: b"historical" for name in P0_R1_TRANSPORT.REPLAY_ARTIFACTS}
    p0_r1_lines = P0_R1_TRANSPORT.encode("gen3-historical", p0_r1_payloads)
    with pytest.raises(TRANSPORT.TransportDefect):
        TRANSPORT.recover("\n".join(p0_r1_lines))


@pytest.mark.parametrize("name", [
    "../escape.json", "p0_r1_replay_result.json", "unknown.json",
    "P0_R2_REPLAY_DISPOSITION.md/child",
])
def test_unknown_or_traversing_artifact_refuses(name):
    with pytest.raises(TRANSPORT.TransportDefect):
        TRANSPORT.validate_artifact_name(name)


def test_checksum_proved_acr_fragment_repair():
    payloads = _payloads(4096)
    lines = TRANSPORT.encode("p0r2-g1-fragment", payloads)
    chunk_index = next(
        index for index, line in enumerate(lines)
        if line.startswith(TRANSPORT.CHUNK_MARKER + "|") and "|d=" in line)
    prefix, data = lines[chunk_index].split("|d=", 1)
    split = len(data) // 2
    lines[chunk_index] = prefix + "|d=" + data[:split]
    lines.insert(chunk_index + 1, data[split:])
    recovered, repairs = TRANSPORT_V1.recover_with_report(
        "\n".join(lines), attempt_id="p0r2-g1-fragment")
    assert recovered == payloads
    assert len(repairs) == 1


def test_recovery_refuses_impossible_chunk_count_before_reassembly():
    lines = TRANSPORT.encode("p0r2-g1-bounded", _payloads())
    chunk = next(index for index, line in enumerate(lines)
                 if line.startswith(TRANSPORT.CHUNK_MARKER + "|"))
    lines[chunk] = lines[chunk].replace("|c=4|", "|c=999999999|")
    with pytest.raises(TRANSPORT.TransportDefect):
        TRANSPORT.recover("\n".join(lines), attempt_id="p0r2-g1-bounded")


def test_recovered_files_are_create_only(tmp_path):
    recovered = _payloads()
    TRANSPORT.write_recovered(recovered, str(tmp_path))
    with pytest.raises(TRANSPORT.TransportDefect):
        TRANSPORT.write_recovered(recovered, str(tmp_path))


def test_blob_prefix_is_disjoint_and_recursive_manifest_is_exact():
    backend = BLOB.InMemoryBackend()
    transport = BLOB_V1.PrivateBlobTransportV1(
        "p0r2-g1-blob", backend=backend)
    assert transport.prefix == "study3/p0_r2/g1/p0r2-g1-blob/"
    assert not transport.prefix.startswith("study3/p0_r1/")
    transport.upload_and_verify("artifact.json", b"{}\n")
    recursive = transport.write_recursive_manifest({"test": True})
    verified = transport.verify_recursive_manifest()
    assert recursive["document"]["object_count"] == 1
    assert verified["verified_objects"] == 1


def test_blob_attempt_prefix_is_exact_empty_and_metadata_cannot_override():
    backend = BLOB.InMemoryBackend()
    with pytest.raises(BLOB.BlobTransportDefect):
        BLOB.PrivateBlobTransport("gen3-historical", backend=backend)
    with pytest.raises(BLOB.BlobTransportDefect):
        BLOB.PrivateBlobTransport(
            "p0r2-g1-bound", backend=backend,
            prefix="study3/p0_r2/g1/p0r2-g1-other/")

    transport = BLOB.PrivateBlobTransport("p0r2-g1-bound", backend=backend)
    backend.upload(transport.prefix + "unexpected.json", b"{}\n")
    with pytest.raises(BLOB.BlobTransportDefect):
        transport.assert_prefix_unused(("expected.json",))

    clean = BLOB.PrivateBlobTransport(
        "p0r2-g1-extra", backend=BLOB.InMemoryBackend())
    clean.upload_and_verify("artifact.json", b"{}\n")
    with pytest.raises(BLOB.BlobTransportDefect):
        clean.write_manifest(
            ("artifact.json",), extra={"attempt_id": "p0r2-g1-forged"})


def test_journal_stores_complete_payloads_create_only():
    backend = BLOB.InMemoryBackend()
    transport = BLOB_V1.PrivateBlobTransportV1(
        "p0r2-g1-journal", backend=backend)
    journal = JOURNAL.DurableJournal(
        "p0r2-g1-journal", JOURNAL.BlobJournalSink(transport),
        stream=io.StringIO())
    journal.start({"attempt_id": "p0r2-g1-journal"})
    admitted = journal.admit("prefill_evaluation", {"row": "S1-001"})
    journal.complete(admitted, {"row": "S1-001", "logits": [0.2, 0.8]})
    journal.record("scored_row", {
        "row_id": "S1-001", "raw": "Answer: 7", "score": 1})
    manifest = journal.manifest(canonical=[])
    verified = JOURNAL.verify_manifest(manifest, journal.sink)
    assert verified["verified_objects"] == journal.index
    completed = [entry for entry in journal.entries
                 if entry["kind"] == "completion"]
    assert completed
    completed_document = json.loads(
        journal.sink.read(completed[0]["name"]).decode("utf-8"))
    assert completed_document["state"] == JOURNAL.COMPLETED
    assert completed_document["payload"]["logits"] == [0.2, 0.8]


def test_journal_refuses_unbound_completion_and_manifest_override():
    backend = BLOB.InMemoryBackend()
    transport = BLOB_V1.PrivateBlobTransportV1(
        "p0r2-g1-journal-refusal", backend=backend)
    journal = JOURNAL.DurableJournal(
        "p0r2-g1-journal-refusal", JOURNAL.BlobJournalSink(transport),
        stream=io.StringIO())
    journal.start({"attempt_id": "p0r2-g1-journal-refusal"})
    with pytest.raises(JOURNAL.JournalDefect):
        journal.fail(999, RuntimeError("not admitted"))
    with pytest.raises(JOURNAL.JournalDefect):
        journal.manifest(extra={"attempt_id": "p0r2-g1-forged"})


def test_journal_verifier_requires_final_recursive_manifest():
    backend = BLOB.InMemoryBackend()
    transport = BLOB_V1.PrivateBlobTransportV1(
        "p0r2-g1-journal-manifest", backend=backend)
    journal = JOURNAL.DurableJournal(
        "p0r2-g1-journal-manifest", JOURNAL.BlobJournalSink(transport))
    journal.start({"attempt_id": "p0r2-g1-journal-manifest"})
    manifest = journal.manifest()
    manifest["written_last"] = False
    with pytest.raises(JOURNAL.JournalDefect):
        JOURNAL.verify_manifest(manifest, journal.sink)


def test_transport_modules_import_no_model_library():
    for name in (
        "p0_r2_transport.py", "p0_r2_transport_v1.py",
        "p0_r2_blob_transport.py", "p0_r2_blob_transport_v1.py",
        "p0_r2_journal_v1.py"):
        source = (P0_R2_DIR / name).read_text(encoding="utf-8")
        assert "import torch" not in source
        assert "import transformers" not in source


def test_p0_r1_terminal_tree_remains_untouched():
    changed = __import__("subprocess").run(
        ["git", "diff", "--name-only",
         "30806d793872a50e581d3252382b4a0ec2af3889", "--",
         "studies/study3/pilot/p0_r1",
         "studies/study3/pilot/p0/results/p0-r1"],
        cwd=str(ROOT), capture_output=True, text=True, check=True).stdout.strip()
    assert changed == ""
