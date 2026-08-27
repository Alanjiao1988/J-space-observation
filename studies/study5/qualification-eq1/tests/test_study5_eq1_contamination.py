"""Tests for the Study 5-EQ1 contamination check.

The check decides whether the adapter's training sample overlaps the benchmark
items, and that number may end up next to an accuracy figure in a paper. So the
properties tested here are the ones that would make such a number wrong or
unreportable: reproducibility, threshold discipline, and confirmation isolation.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location(
    "study5_eq1_contamination", _TOOLS / "contamination_check.py"
)
assert _SPEC is not None and _SPEC.loader is not None
contamination = importlib.util.module_from_spec(_SPEC)
sys.modules["study5_eq1_contamination"] = contamination
_SPEC.loader.exec_module(contamination)


def test_the_hash_is_stable_across_processes() -> None:
    """A randomised hash would make the cosine channel irreproducible.

    Authority 9.4 forbids reporting a number with no committed provenance, and a
    number that changes between runs has none. This is checked in a *separate
    interpreter*, because within one process even a randomised hash looks stable.
    """

    code = (
        "import importlib.util,sys;"
        f"s=importlib.util.spec_from_file_location('c',r'{_TOOLS / 'contamination_check.py'}');"
        "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        "print(m.stable_hash('a benchmark problem'))"
    )
    first = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    second = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env={"PYTHONHASHSEED": "1", "PATH": ""},
    ).stdout.strip()
    assert first == second
    assert first == str(contamination.stable_hash("a benchmark problem"))


def test_normalisation_folds_case_whitespace_and_latex_spacing() -> None:
    a = contamination.normalise("Let $x \\ge 2$.   Find  X!")
    b = contamination.normalise("let $x \\ge 2$. find x!")
    assert a == b


def test_identical_text_is_maximally_similar() -> None:
    text = contamination.normalise("compute the sum of the first ten primes")
    vector = contamination.hashed_char_vector(text)
    assert contamination.cosine(vector, vector) == pytest.approx(1.0)


def test_unrelated_text_is_not_similar() -> None:
    a = contamination.hashed_char_vector(
        contamination.normalise("compute the sum of the first ten primes")
    )
    b = contamination.hashed_char_vector(
        contamination.normalise("a train leaves the station heading north")
    )
    assert contamination.cosine(a, b) < contamination.COSINE_FLAG_THRESHOLD


def test_short_text_still_produces_an_ngram() -> None:
    """A problem shorter than the window must not silently vanish."""

    grams = contamination.word_ngrams(contamination.normalise("find x"))
    assert grams == {"find x"}


def test_reference_text_ignores_assistant_turns() -> None:
    """Contamination is about the problem, not the model's own reasoning."""

    row = {
        "conversations": [
            {"from": "human", "value": "PROBLEM TEXT"},
            {"from": "gpt", "value": "ASSISTANT REASONING"},
        ]
    }
    text = contamination.reference_text(row)
    assert "PROBLEM TEXT" in text
    assert "ASSISTANT REASONING" not in text


def test_reference_text_reads_role_content_messages() -> None:
    row = {
        "messages": [
            {"role": "user", "content": "USER TEXT"},
            {"role": "assistant", "content": "REPLY"},
        ]
    }
    text = contamination.reference_text(row)
    assert "USER TEXT" in text
    assert "REPLY" not in text


def _fixture(tmp_path: Path, contaminated: bool) -> tuple[Path, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    # Deliberately unrelated problems. An earlier version of this fixture gave
    # the items a shared 13-word prefix, so a reference matching one item
    # matched them all -- the tool was right and the fixture was wrong.
    problems = {
        "i0": "prove that the sum of two odd integers is always an even integer",
        "i1": "a cyclist travels forty kilometres uphill then returns downhill twice as fast",
        "i2": "determine how many distinct arrangements exist for the letters in banana",
    }
    benchmark = tmp_path / "bench.jsonl"
    benchmark.write_text(
        "\n".join(
            json.dumps({"unique_id": k, "problem": v}) for k, v in problems.items()
        )
        + "\n",
        encoding="utf-8",
    )
    split = tmp_path / "split.json"
    split.write_text(
        json.dumps({"development_ids": ["i0", "i1"], "confirmation_ids": ["i2"]}),
        encoding="utf-8",
    )
    reference = tmp_path / "ref.jsonl"
    body = (
        {"conversations": [{"from": "human", "value": problems["i0"]}]}
        if contaminated
        else {"conversations": [{"from": "human", "value": "an unrelated question"}]}
    )
    reference.write_text(json.dumps(body) + "\n", encoding="utf-8")
    return split, benchmark, reference


def _run(tmp_path: Path, contaminated: bool) -> dict:
    split, benchmark, reference = _fixture(tmp_path, contaminated)
    out = tmp_path / "report.json"
    assert (
        contamination.main(
            [
                "--split",
                str(split),
                "--benchmark",
                str(benchmark),
                "--reference",
                str(reference),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    return json.loads(out.read_text(encoding="utf-8"))


def test_a_verbatim_reused_problem_is_flagged(tmp_path: Path) -> None:
    report = _run(tmp_path, contaminated=True)
    assert report["flagged_item_count"] == 1
    assert report["flagged_items"][0]["item_id"] == "i0"
    assert report["flagged_items"][0]["flagged_by_ngram"] is True


def test_clean_data_is_not_flagged(tmp_path: Path) -> None:
    report = _run(tmp_path, contaminated=False)
    assert report["flagged_item_count"] == 0
    assert report["overlap_rate"] == 0.0


def test_only_development_items_are_checked(tmp_path: Path) -> None:
    """Authority 10.2: no confirmation item is loaded or inspected."""

    report = _run(tmp_path, contaminated=True)
    assert report["items_checked"] == 2
    assert report["other_split_items_checked"] == 0
    assert report["other_split_items_loaded"] == 0
    assert report["screened_split"] == "development"
    assert all(f["item_id"] != "i2" for f in report["flagged_items"])


def test_a_partial_load_is_refused_rather_than_reported(tmp_path: Path) -> None:
    """Reporting an overlap rate over a subset would understate contamination."""

    split, benchmark, reference = _fixture(tmp_path, contaminated=False)
    broken = json.loads(split.read_text(encoding="utf-8"))
    broken["development_ids"].append("missing-item")
    split.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(SystemExit):
        contamination.main(
            [
                "--split",
                str(split),
                "--benchmark",
                str(benchmark),
                "--reference",
                str(reference),
                "--out",
                str(tmp_path / "r.json"),
            ]
        )


def test_thresholds_are_recorded_in_the_report(tmp_path: Path) -> None:
    """A decision rule that is not in the artifact can be changed after the fact."""

    report = _run(tmp_path, contaminated=False)
    assert report["thresholds_fixed_before_measurement"] is True
    assert report["ngram_n"] == contamination.NGRAM_N
    assert report["ngram_flag_threshold"] == contamination.NGRAM_FLAG_THRESHOLD
    assert report["cosine_flag_threshold"] == contamination.COSINE_FLAG_THRESHOLD
    assert report["flag_rule"]


def test_the_report_carries_its_claim_ceiling(tmp_path: Path) -> None:
    report = _run(tmp_path, contaminated=False)
    ceiling = report["interpretation_ceiling"].lower()
    assert "not evidence about j-space" in ceiling


def test_the_result_is_reproducible(tmp_path: Path) -> None:
    first = _run(tmp_path / "a", contaminated=True)
    second = _run(tmp_path / "b", contaminated=True)
    assert first["flagged_items"] == second["flagged_items"]
    assert first["max_cosine_observed"] == second["max_cosine_observed"]


def test_matched_ngrams_are_recorded_verbatim(tmp_path: Path) -> None:
    """OD-002: a reader must be able to judge boilerplate for themselves."""

    report = _run(tmp_path, contaminated=True)
    flagged = report["flagged_items"][0]
    assert flagged["matched_ngram_count"] >= 1
    assert flagged["matched_ngrams_verbatim"]
    assert all(isinstance(g, str) and g for g in flagged["matched_ngrams_verbatim"])


def test_the_confirmation_split_can_be_screened(tmp_path: Path) -> None:
    """OD-002 authorises screening confirmation items, and only that."""

    split, benchmark, reference = _fixture(tmp_path, contaminated=False)
    out = tmp_path / "conf.json"
    assert (
        contamination.main(
            [
                "--split", str(split),
                "--benchmark", str(benchmark),
                "--reference", str(reference),
                "--screen", "confirmation",
                "--out", str(out),
            ]
        )
        == 0
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["screened_split"] == "confirmation"
    assert report["items_checked"] == 1
    assert report["other_split_items_loaded"] == 0
    assert report["model_calls"] == 0
    assert report["items_tokenized"] == 0
    assert report["items_generated_from"] == 0
    assert report["items_scored"] == 0


def test_screening_defaults_to_development(tmp_path: Path) -> None:
    assert _run(tmp_path, contaminated=False)["screened_split"] == "development"


def test_the_primary_analysis_set_excludes_flagged_items(tmp_path: Path) -> None:
    report = _run(tmp_path, contaminated=True)
    assert report["primary_analysis_set_size"] == (
        report["items_checked"] - report["flagged_item_count"]
    )
    assert report["excluded_items_retained_as_registered_sensitivity_set"] is True


def test_the_limitation_is_worded_as_a_ceiling_risk(tmp_path: Path) -> None:
    """OD-002 forbids calling this a threat to validity."""

    wording = _run(tmp_path, contaminated=False)["limitation_wording"].lower()
    assert "ceiling" in wording
    assert "compresses the difference" in wording
    assert "threatens validity" not in wording


def test_thresholds_are_recorded_as_unchanged_from_p0(tmp_path: Path) -> None:
    assert _run(tmp_path, contaminated=False)["thresholds_unchanged_from_p0"] is True
