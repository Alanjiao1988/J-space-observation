"""Prompt set generation for depth gradient tasks."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import json


@dataclass
class PromptItem:
    """Single prompt item with metadata."""
    id: str
    task_family: str
    depth: int
    prompt_base: str
    expected_answer: str
    expected_intermediates: Optional[List[str]] = None
    floor_accuracy: Optional[float] = None
    parse_type: str = "numeric"  # numeric, entity, yes_no
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ArithmeticPromptSet:
    """Arithmetic depth gradient prompt set."""
    
    @staticmethod
    def generate_pilot_set() -> List[PromptItem]:
        """Generate small pilot arithmetic dataset (1-3 ops)."""
        items = []
        
        # 1-op: simple arithmetic
        items.extend([
            PromptItem(
                id="arith_1op_001",
                task_family="arithmetic",
                depth=1,
                prompt_base="What is 7 + 5?",
                expected_answer="12",
                parse_type="numeric",
                floor_accuracy=0.95,
            ),
            PromptItem(
                id="arith_1op_002",
                task_family="arithmetic",
                depth=1,
                prompt_base="What is 23 - 8?",
                expected_answer="15",
                parse_type="numeric",
                floor_accuracy=0.95,
            ),
            PromptItem(
                id="arith_1op_003",
                task_family="arithmetic",
                depth=1,
                prompt_base="What is 6 * 4?",
                expected_answer="24",
                parse_type="numeric",
                floor_accuracy=0.95,
            ),
        ])
        
        # 2-op: simple multi-step
        items.extend([
            PromptItem(
                id="arith_2op_001",
                task_family="arithmetic",
                depth=2,
                prompt_base="What is (5 + 3) * 2?",
                expected_answer="16",
                expected_intermediates=["8", "16"],
                parse_type="numeric",
                floor_accuracy=0.85,
            ),
            PromptItem(
                id="arith_2op_002",
                task_family="arithmetic",
                depth=2,
                prompt_base="What is 20 - 7 + 3?",
                expected_answer="16",
                expected_intermediates=["13", "16"],
                parse_type="numeric",
                floor_accuracy=0.85,
            ),
            PromptItem(
                id="arith_2op_003",
                task_family="arithmetic",
                depth=2,
                prompt_base="What is (10 + 2) / 3?",
                expected_answer="4",
                expected_intermediates=["12", "4"],
                parse_type="numeric",
                floor_accuracy=0.80,
            ),
        ])
        
        # 3-op: deeper reasoning
        items.extend([
            PromptItem(
                id="arith_3op_001",
                task_family="arithmetic",
                depth=3,
                prompt_base="What is ((8 + 4) * 2) - 6?",
                expected_answer="18",
                expected_intermediates=["12", "24", "18"],
                parse_type="numeric",
                floor_accuracy=0.70,
            ),
            PromptItem(
                id="arith_3op_002",
                task_family="arithmetic",
                depth=3,
                prompt_base="What is (10 + 5) * 2 + 4?",
                expected_answer="34",
                expected_intermediates=["15", "30", "34"],
                parse_type="numeric",
                floor_accuracy=0.70,
            ),
            PromptItem(
                id="arith_3op_003",
                task_family="arithmetic",
                depth=3,
                prompt_base="What is ((9 - 3) * 4) + 2?",
                expected_answer="26",
                expected_intermediates=["6", "24", "26"],
                parse_type="numeric",
                floor_accuracy=0.70,
            ),
        ])
        
        return items


class SyntheticRelationPromptSet:
    """Synthetic relation depth gradient with facts in prompt."""
    
    @staticmethod
    def generate_pilot_set() -> List[PromptItem]:
        """Generate small pilot synthetic relation dataset (1-3 hops)."""
        items = []
        
        # 1-hop: direct relation
        items.extend([
            PromptItem(
                id="syn_1hop_001",
                task_family="synthetic_relation",
                depth=1,
                prompt_base="Given: Alice is the mother of Bob. Who is the mother of Bob?",
                expected_answer="Alice",
                parse_type="entity",
                floor_accuracy=0.90,
            ),
            PromptItem(
                id="syn_1hop_002",
                task_family="synthetic_relation",
                depth=1,
                prompt_base="Given: The book is red. What color is the book?",
                expected_answer="red",
                parse_type="entity",
                floor_accuracy=0.90,
            ),
        ])
        
        # 2-hop: transitive relation
        items.extend([
            PromptItem(
                id="syn_2hop_001",
                task_family="synthetic_relation",
                depth=2,
                prompt_base="Given: Alice is the mother of Bob. Bob is the father of Charlie. Who is the mother of Alice's grandchild?",
                expected_answer="Alice",
                expected_intermediates=["Bob", "Alice"],
                parse_type="entity",
                floor_accuracy=0.75,
            ),
            PromptItem(
                id="syn_2hop_002",
                task_family="synthetic_relation",
                depth=2,
                prompt_base="Given: X is larger than Y. Y is larger than Z. Is X larger than Z?",
                expected_answer="yes",
                expected_intermediates=["Y", "yes"],
                parse_type="yes_no",
                floor_accuracy=0.80,
            ),
        ])
        
        # 3-hop: longer chain
        items.extend([
            PromptItem(
                id="syn_3hop_001",
                task_family="synthetic_relation",
                depth=3,
                prompt_base="Given: A leads to B. B leads to C. C leads to D. If we follow from A, do we reach D?",
                expected_answer="yes",
                expected_intermediates=["B", "C", "yes"],
                parse_type="yes_no",
                floor_accuracy=0.60,
            ),
        ])
        
        return items


class FactualCounterfactualPromptSet:
    """Factual and counterfactual depth gradient."""
    
    @staticmethod
    def generate_pilot_set() -> List[PromptItem]:
        """Generate small pilot factual/counterfactual dataset."""
        items = []
        
        # 1-hop factual
        items.extend([
            PromptItem(
                id="fact_1hop_001",
                task_family="factual",
                depth=1,
                prompt_base="What is the capital of France?",
                expected_answer="Paris",
                parse_type="entity",
                floor_accuracy=0.95,
            ),
        ])
        
        # 2-hop factual
        items.extend([
            PromptItem(
                id="fact_2hop_001",
                task_family="factual",
                depth=2,
                prompt_base="What is the capital of the country where the Eiffel Tower is located?",
                expected_answer="Paris",
                expected_intermediates=["France", "Paris"],
                parse_type="entity",
                floor_accuracy=0.80,
            ),
        ])
        
        # 2-hop counterfactual
        items.extend([
            PromptItem(
                id="fact_2hop_cf_001",
                task_family="counterfactual",
                depth=2,
                prompt_base="If the Eiffel Tower were in Germany, what would be the capital?",
                expected_answer="Berlin",
                expected_intermediates=["Germany", "Berlin"],
                parse_type="entity",
                floor_accuracy=0.60,
            ),
        ])
        
        return items


def generate_all_pilot_prompt_sets() -> Dict[str, List[PromptItem]]:
    """Generate all pilot prompt sets."""
    return {
        "arithmetic": ArithmeticPromptSet.generate_pilot_set(),
        "synthetic_relation": SyntheticRelationPromptSet.generate_pilot_set(),
        "factual_counterfactual": FactualCounterfactualPromptSet.generate_pilot_set(),
    }


def save_prompt_sets(
    prompt_sets: Dict[str, List[PromptItem]],
    output_dir: str
) -> None:
    """Save prompt sets to JSON files."""
    from pathlib import Path
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    for task_family, items in prompt_sets.items():
        file_path = output_path / f"{task_family}_prompts.jsonl"
        with open(file_path, "w") as f:
            for item in items:
                f.write(json.dumps(item.to_dict()) + "\n")


def load_prompt_sets(input_dir: str) -> Dict[str, List[PromptItem]]:
    """Load prompt sets from JSON files."""
    from pathlib import Path
    input_path = Path(input_dir)
    
    prompt_sets = {}
    for file_path in input_path.glob("*_prompts.jsonl"):
        task_family = file_path.stem.replace("_prompts", "")
        items = []
        with open(file_path, "r") as f:
            for line in f:
                item_dict = json.loads(line)
                items.append(PromptItem(**item_dict))
        prompt_sets[task_family] = items
    
    return prompt_sets
