"""Tests for pilot prompt-set capacity and identity."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jspace_observation.prompt_sets import ArithmeticPromptSet


def test_arithmetic_prompt_set_supports_three_items_per_depth():
    items = ArithmeticPromptSet.generate_pilot_set()

    assert Counter(item.depth for item in items) == {1: 3, 2: 3, 3: 3}
    assert len({item.id for item in items}) == len(items)


def test_third_depth_three_arithmetic_item_has_expected_trace():
    item = next(
        item
        for item in ArithmeticPromptSet.generate_pilot_set()
        if item.id == "arith_3op_003"
    )

    assert item.expected_answer == "26"
    assert item.expected_intermediates == ["6", "24", "26"]
