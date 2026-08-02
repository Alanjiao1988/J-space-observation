"""Structural integrity of the paper registries.

These CSVs are scientific records: a row that silently loses a column can move a
hash, a limitation, or a claim onto the wrong field.  Nothing here judges the
content of a row; it only refuses a malformed one.
"""

import csv
from pathlib import Path

import pytest

PAPER = Path(__file__).resolve().parent.parent / "paper"

REGISTRIES = (
    "evidence_ledger.csv",
    "artifact_index.csv",
    "figure_registry.csv",
    "table_registry.csv",
)

IDENTIFIER_COLUMN = {
    "evidence_ledger.csv": "evidence_id",
    "artifact_index.csv": "artifact_id",
    "figure_registry.csv": "figure_or_table_id",
    "table_registry.csv": "figure_or_table_id",
}


def _rows(name: str) -> tuple[list[str], list[list[str]]]:
    with (PAPER / name).open(newline="", encoding="utf-8") as handle:
        table = list(csv.reader(handle))
    return table[0], [row for row in table[1:] if row]


@pytest.mark.parametrize("name", REGISTRIES)
def test_every_row_has_exactly_the_header_columns(name):
    header, rows = _rows(name)
    for index, row in enumerate(rows, start=2):
        assert len(row) == len(header), f"{name} line {index} has {len(row)} of {len(header)} columns"


@pytest.mark.parametrize("name", REGISTRIES)
def test_identifiers_are_unique_and_present(name):
    header, rows = _rows(name)
    column = header.index(IDENTIFIER_COLUMN[name])
    identifiers = [row[column].strip() for row in rows]
    assert all(identifiers), f"{name} has a row with an empty identifier"
    assert len(set(identifiers)) == len(identifiers), f"{name} has a duplicate identifier"


def test_every_evidence_row_states_what_it_does_not_establish():
    header, rows = _rows("evidence_ledger.csv")
    limitations = header.index("limitations")
    identifier = header.index("evidence_id")
    for row in rows:
        assert row[limitations].strip(), f"{row[identifier]} records no limitations"


@pytest.mark.parametrize("name", ("figure_registry.csv", "table_registry.csv"))
def test_every_registered_exhibit_states_what_it_does_not_establish(name):
    header, rows = _rows(name)
    limitations = header.index("limitations")
    identifier = header.index("figure_or_table_id")
    for row in rows:
        assert row[limitations].strip(), f"{row[identifier]} records no limitations"


def test_every_registered_artifact_declares_its_privacy_status():
    header, rows = _rows("artifact_index.csv")
    column = header.index("contains_private_data")
    for row in rows:
        assert row[column].strip() in {"yes", "no"}
