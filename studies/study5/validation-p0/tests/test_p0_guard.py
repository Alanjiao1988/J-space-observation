"""OD-011 failing cases for the sealed-asset guard and the patching harness.

The guard has to fire on a genuine read and stay quiet on prose, and both are
demonstrated. The harness tests run without a model: the pieces that can be
checked arithmetically are checked arithmetically.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


guard = load("p0_guard", "guard_p0.py")
patch = load("p0_patch_static", "patch_effect.py")


# ------------------------------------------------------------------- guard


def test_a_lens_name_in_an_access_field_is_a_read():
    assert guard.reads_a_sealed_lens({"inputs_sha256": ["lens_A.pt"]})


def test_a_lens_digest_in_an_access_field_is_a_read_even_if_renamed():
    digest = guard.SEALED_LENS_SHA256["lens_B"]
    assert guard.reads_a_sealed_lens({"inputs_sha256": [digest]})


def test_a_lens_name_in_a_note_is_not_a_read():
    record = {"note": "lens_A was not read", "inputs_sha256": []}
    assert not guard.reads_a_sealed_lens(record)
    assert guard.mentions_in_prose(record)


def test_an_unrelated_record_is_neither():
    record = {"inputs_sha256": ["abc"], "note": "nothing to see"}
    assert not guard.reads_a_sealed_lens(record)
    assert not guard.mentions_in_prose(record)


def test_a_similar_but_different_name_does_not_trip_the_guard():
    assert not guard.reads_a_sealed_lens({"inputs_sha256": ["lens_AB_notes"]})


def test_the_guard_fails_on_a_journal_that_records_a_read(tmp_path):
    namespace = tmp_path / "ns"
    (namespace / "journal").mkdir(parents=True)
    (namespace / "tools").mkdir()
    (namespace / "journal" / "P-0.jsonl").write_text(
        json.dumps({"step_id": "X", "inputs_sha256": ["lens_A"]}) + "\n",
        encoding="utf-8",
    )
    result = guard.scan_journal(namespace)
    assert result["lens_reading_record_count"] == 1


def test_the_guard_fails_on_a_tool_that_names_the_target(tmp_path):
    namespace = tmp_path / "ns"
    (namespace / "tools").mkdir(parents=True)
    (namespace / "tools" / "bad.py").write_text(
        "MODEL = 'DeepSeek-R1-Distill-Qwen-7B'\n", encoding="utf-8"
    )
    result = guard.scan_tools(namespace)
    assert result["target_or_lens_references_in_tools"]


def test_the_real_p0_namespace_is_clean():
    namespace = Path(__file__).resolve().parent.parent
    result = guard.scan_tools(namespace)
    assert not result["target_or_lens_references_in_tools"]
    assert not result["tools_importing_jlens"]


def test_the_guard_is_the_only_file_excused_from_the_marker_scan():
    namespace = Path(__file__).resolve().parent.parent
    result = guard.scan_tools(namespace)
    assert result["excluded_from_the_marker_scan"] == ["guard_p0.py"]
    assert "guard_p0.py" not in result["tools_scanned"]
    every = {p.name for p in (namespace / "tools").glob("*.py")}
    assert set(result["tools_scanned"]) == every - {"guard_p0.py"}


def test_the_guard_would_report_itself_if_it_actually_imported_jlens():
    assert guard.imports_jlens("import jlens\n")
    assert guard.imports_jlens("from jlens import JacobianLens\n")
    assert guard.imports_jlens("    import jlens as jl\n")


def test_merely_naming_jlens_is_not_importing_it():
    assert not guard.imports_jlens("# jlens is never imported here\n")
    assert not guard.imports_jlens('PATTERN = "import jlens"\n')
    assert not guard.imports_jlens(
        guard.__doc__ or "the instrument under test is jlens"
    )


# ----------------------------------------------------------------- harness


def test_logit_difference_is_a_max_over_surface_forms():
    row = [0.0, 5.0, 1.0, 9.0]
    assert patch.logit_difference(row, [1, 2], [0]) == 5.0
    assert patch.logit_difference(row, [0], [1, 3]) == -9.0


def test_the_denominator_guard_is_strict():
    assert patch.MIN_DENOMINATOR == 0.0


def test_prefix_is_not_measured_for_the_null_constructions():
    assert "PREFIX" not in patch.NULL_SITES
    assert set(patch.NULL_SITES) == {"CUE", "BRIDGE", "READOUT"}


def test_the_embedding_layer_index_is_registered_as_minus_one():
    assert patch.EMBEDDING_LAYER == -1


def test_the_measurement_module_does_not_import_jlens():
    source = (TOOLS / "patch_effect.py").read_text(encoding="utf-8")
    assert not guard.imports_jlens(source)
    assert "jlens" not in sys.modules


def test_no_p0_tool_imports_jlens():
    for path in sorted(TOOLS.glob("*.py")):
        assert not guard.imports_jlens(path.read_text(encoding="utf-8")), path.name
