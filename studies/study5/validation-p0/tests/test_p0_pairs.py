"""OD-011 failing cases for the P-0 frame construction.

Every admissibility rule gets a case built to violate it, so that each rule is
shown to reject something. A rule with no demonstrated rejection is a rule that
has not been shown to do anything.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pairs = load("p0_pairs", "build_pairs.py")


def item(index, name, target, intermediates, target_ids, inter_ids, ids):
    return {
        "index": index,
        "name": name,
        "prompt": name,
        "target": target,
        "intermediates": intermediates,
        "ids": ids,
        "target_token_ids": target_ids,
        "intermediate_token_ids": inter_ids,
    }


A = item(0, "a", "Atlantic", ["Brazil"], [10], [20], [1, 2, 3, 4, 5])
B = item(1, "b", "Portuguese", ["Peru"], [11], [21], [1, 2, 9, 4, 5])


# ----------------------------------------------------------------- sites_for


def test_unequal_length_is_rejected():
    assert pairs.sites_for([1, 2, 3], [1, 2, 3, 4]) is None


def test_identical_sequences_are_rejected():
    assert pairs.sites_for([1, 2, 3, 4], [1, 2, 3, 4]) is None


def test_difference_at_the_readout_position_is_rejected():
    # last position differs, so there is no room for a BRIDGE at all
    assert pairs.sites_for([1, 2, 3, 9], [1, 2, 3, 4]) is None


def test_empty_bridge_is_rejected():
    # the only difference is immediately before the readout position
    assert pairs.sites_for([1, 2, 9, 4], [1, 2, 3, 4]) is None


def test_empty_prefix_is_rejected():
    # position 0 differs, so nothing is causally upstream of the cue
    assert pairs.sites_for([9, 2, 3, 4, 5], [1, 2, 3, 4, 5]) is None


def test_admissible_pair_yields_all_four_sites():
    sites = pairs.sites_for([1, 2, 9, 4, 5], [1, 2, 3, 4, 5])
    assert sites == {
        "PREFIX": [0, 1],
        "CUE": [2],
        "BRIDGE": [3],
        "READOUT": [4],
    }


def test_bridge_positions_carry_identical_tokens():
    donor = [1, 2, 9, 4, 5, 6]
    recipient = [1, 2, 3, 4, 5, 6]
    sites = pairs.sites_for(donor, recipient)
    assert sites is not None
    for position in sites["BRIDGE"]:
        assert donor[position] == recipient[position]


def test_prefix_positions_carry_identical_tokens():
    donor = [1, 2, 9, 4, 5, 6]
    recipient = [1, 2, 3, 4, 5, 6]
    sites = pairs.sites_for(donor, recipient)
    assert sites is not None
    for position in sites["PREFIX"]:
        assert donor[position] == recipient[position]


# ---------------------------------------------------------------- compatible


def test_same_item_is_rejected():
    assert not pairs.compatible(A, A)


def test_equal_targets_are_rejected():
    other = dict(B, target="atlantic ")
    assert not pairs.compatible(A, other)


def test_overlapping_intermediates_are_rejected():
    other = dict(B, intermediates=["brazil"])
    assert not pairs.compatible(A, other)


def test_shared_single_token_target_form_is_rejected():
    other = dict(B, target_token_ids=[10, 12])
    assert not pairs.compatible(A, other)


def test_admissible_content_is_accepted():
    assert pairs.compatible(A, B)


# ------------------------------------------------------------ readout / rule


def test_readout_position_is_the_final_token():
    assert pairs.readout_position(7) == 6


def test_an_unregistered_readout_rule_raises(monkeypatch):
    monkeypatch.setattr(pairs, "READOUT_RULE", "something_else")
    with pytest.raises(pairs.PairBuildError):
        pairs.readout_position(7)


def test_decisive_site_is_bridge():
    assert pairs.DECISIVE_SITE == "BRIDGE"


def test_null_replicates_is_five():
    assert pairs.NULL_REPLICATES == 5


# ------------------------------------------------------------- null assignment


def test_null_donor_is_admissible_against_both_members():
    C = item(2, "c", "Spanish", ["Chile"], [12], [22], [1, 2, 7, 4, 5])
    D = item(3, "d", "Atlantic", ["Brazil"], [10], [20], [1, 2, 8, 4, 5])
    units = [
        {
            "unit_id": "a->b",
            "cluster_id": "a|b",
            "donor": "a",
            "recipient": "b",
            "sites": pairs.sites_for(A["ids"], B["ids"]),
        }
    ]
    assignment = pairs.assign_null_donors(units, [A, B, C, D], 1, 5)
    chosen = assignment["assignment"]["a->b"]
    assert len(chosen) == 5
    # d shares a's target and intermediate, so it can never be a null donor
    assert set(chosen) == {"c"}


def test_no_admissible_third_item_is_recorded_not_papered_over():
    units = [
        {
            "unit_id": "a->b",
            "cluster_id": "a|b",
            "donor": "a",
            "recipient": "b",
            "sites": pairs.sites_for(A["ids"], B["ids"]),
        }
    ]
    assignment = pairs.assign_null_donors(units, [A, B], 1, 5)
    assert assignment["assignment"]["a->b"] == []
    assert assignment["units_with_no_admissible_third_item"] == ["a->b"]


def test_null_assignment_is_reproducible_from_the_seed():
    C = item(2, "c", "Spanish", ["Chile"], [12], [22], [1, 2, 7, 4, 5])
    E = item(4, "e", "German", ["Peru2"], [13], [23], [1, 2, 6, 4, 5])
    units = [
        {
            "unit_id": "a->b",
            "cluster_id": "a|b",
            "donor": "a",
            "recipient": "b",
            "sites": pairs.sites_for(A["ids"], B["ids"]),
        }
    ]
    first = pairs.assign_null_donors(units, [A, B, C, E], 7, 5)
    second = pairs.assign_null_donors(units, [A, B, C, E], 7, 5)
    assert first["assignment"] == second["assignment"]
    different = pairs.assign_null_donors(units, [A, B, C, E], 8, 5)
    assert different["assignment"] != first["assignment"]


def test_jlens_is_not_imported_by_the_frame_builder():
    assert "jlens" not in sys.modules
    source = (TOOLS / "build_pairs.py").read_text(encoding="utf-8")
    assert "import jlens" not in source
