"""Deterministic, model-free Study 2 task-bank construction.

The generator uses SHA-256 counter-mode streams only.  It has no tokenizer,
model, lens, provider, GPU, or Study 1 outcome path.  Ground truth is generated
here and is recomputed independently by :mod:`study2_protocol` before a
manifest can be written.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import study2_protocol as protocol


class CounterStream:
    """A deterministic SHA-256 counter stream with unbiased ``randbelow``."""

    def __init__(self, seed: str, *domain: object) -> None:
        self._prefix = (seed + "\x1f" + "\x1f".join(str(item) for item in domain)).encode("utf-8")
        self._counter = 0
        self._buffer = b""

    def _fill(self) -> None:
        digest = hashlib.sha256(self._prefix + b"\x00" + self._counter.to_bytes(16, "big")).digest()
        self._counter += 1
        self._buffer += digest

    def bytes(self, count: int) -> bytes:
        while len(self._buffer) < count:
            self._fill()
        result, self._buffer = self._buffer[:count], self._buffer[count:]
        return result

    def randbelow(self, upper: int) -> int:
        if upper <= 0:
            raise ValueError("upper must be positive")
        width = max(1, (upper.bit_length() + 7) // 8)
        ceiling = 1 << (8 * width)
        limit = ceiling - ceiling % upper
        while True:
            value = int.from_bytes(self.bytes(width), "big")
            if value < limit:
                return value % upper

    def shuffle(self, values: Sequence[int]) -> list[int]:
        result = list(values)
        for index in range(len(result) - 1, 0, -1):
            other = self.randbelow(index + 1)
            result[index], result[other] = result[other], result[index]
        return result


def _hash_order(values: Iterable[int], *domain: object) -> list[int]:
    return sorted(
        values,
        key=lambda value: hashlib.sha256(
            ("\x1f".join(str(item) for item in (*domain, value))).encode("utf-8")
        ).digest(),
    )


def _balanced_value(index: int, size: int, salt: int) -> int:
    label_index = index % 4
    within_label = index // 4
    return (within_label + 2 * label_index + salt) % size


def _template(index: int) -> str:
    label_index = index % 4
    within_label = index // 4
    return protocol.TEMPLATES[(within_label + label_index) % 2]


def _sequence(index: int, depth: int, salt: int) -> list[str]:
    label_index = index % 4
    within_label = index // 4
    return [
        protocol.OPERATOR_NAMES[(within_label + label_index + salt + position) % 3]
        for position in range(depth)
    ]


def _sample_operators(seed: str, family: str, *domain: object) -> list[dict[str, Any]]:
    stream = CounterStream(seed, *domain)
    operators: list[dict[str, Any]] = []
    if family == "permutation_chain":
        for name in protocol.OPERATOR_NAMES:
            operators.append(
                {
                    "name": name,
                    "kind": "permutation",
                    "mapping": stream.shuffle(tuple(range(8))),
                }
            )
    elif family == "affine_mod10":
        for name in protocol.OPERATOR_NAMES:
            operators.append(
                {
                    "name": name,
                    "kind": "affine",
                    "a": protocol.AFFINE_MULTIPLIERS[stream.randbelow(len(protocol.AFFINE_MULTIPLIERS))],
                    "b": stream.randbelow(10),
                    "modulus": 10,
                }
            )
    else:  # pragma: no cover - callers validate registered family first
        raise ValueError(f"unknown family {family}")
    return operators


def _apply(operator: Mapping[str, Any], value: int, family: str) -> int:
    if family == "permutation_chain":
        return operator["mapping"][value]
    return (operator["a"] * value + operator["b"]) % 10


def _evaluate(operators: Sequence[Mapping[str, Any]], start: int, sequence: Sequence[str], family: str) -> tuple[list[int], int, int]:
    by_name = {operator["name"]: operator for operator in operators}
    value = start
    states: list[int] = []
    for name in sequence:
        value = _apply(by_name[name], value, family)
        states.append(value)
    pre_answer = start if len(sequence) == 1 else states[-2]
    return states, pre_answer, states[-1]


def _primitive(
    *,
    seed: str,
    family: str,
    depth: int,
    start: int,
    sequence: Sequence[str],
    desired_pre_answer: int,
    desired_final: int,
    domain: Sequence[object],
    require_distinct_trace_states: bool = False,
) -> dict[str, Any]:
    for attempt in range(1_000_000):
        operators = _sample_operators(seed, family, *domain, attempt)
        states, pre_answer, final = _evaluate(operators, start, sequence, family)
        if require_distinct_trace_states and len(set(states[:-1])) != len(states[:-1]):
            continue
        if pre_answer == desired_pre_answer and final == desired_final:
            return {
                "family": family,
                "depth": depth,
                "state_space": list(range(8 if family == "permutation_chain" else 10)),
                "operators": operators,
                "start_state": start,
                "operation_sequence": list(sequence),
                "ground_truth": {
                    "intermediate_states": states,
                    "pre_answer_intermediate": pre_answer,
                    "final_state": final,
                },
                "attempt": attempt,
            }
    raise RuntimeError("deterministic primitive search exhausted")


def _random_primitive(
    *,
    seed: str,
    family: str,
    depth: int,
    option_values: Sequence[int],
    forbidden_intermediate: int,
    forbidden_answer: int,
    domain: Sequence[object],
) -> dict[str, Any]:
    size = 8 if family == "permutation_chain" else 10
    stream = CounterStream(seed, *domain, "outer")
    for attempt in range(1_000_000):
        start = stream.randbelow(size)
        sequence = [protocol.OPERATOR_NAMES[stream.randbelow(3)] for _ in range(depth)]
        operators = _sample_operators(seed, family, *domain, "operators", attempt)
        states, pre_answer, final = _evaluate(operators, start, sequence, family)
        if pre_answer != forbidden_intermediate and final != forbidden_answer and final in option_values:
            return {
                "family": family,
                "depth": depth,
                "state_space": list(range(size)),
                "operators": operators,
                "start_state": start,
                "operation_sequence": sequence,
                "ground_truth": {
                    "intermediate_states": states,
                    "pre_answer_intermediate": pre_answer,
                    "final_state": final,
                },
                "attempt": attempt,
            }
    raise RuntimeError("deterministic random-control search exhausted")


def _definitions(task: Mapping[str, Any], order: Sequence[str]) -> list[str]:
    by_name = {operator["name"]: operator for operator in task["operators"]}
    rows: list[str] = []
    for name in order:
        operator = by_name[name]
        if task["family"] == "permutation_chain":
            rows.append(f"{name}: " + " ".join(f"{source}->{target}" for source, target in enumerate(operator["mapping"])))
        else:
            rows.append(f"{name}(x)=({operator['a']}*x+{operator['b']}) mod 10")
    return rows


def _trace(task: Mapping[str, Any], arm: str) -> str:
    values = list(task["ground_truth"]["intermediate_states"][:-1])
    if arm == "WT":
        values[-1] = task["counterfactual"]["wrong_pre_answer_intermediate"]
    elif arm == "ST":
        values.reverse()
    return "Trace: " + "; ".join(f"s{index + 1}={value}" for index, value in enumerate(values))


def _render(task: Mapping[str, Any], arm: str) -> str:
    options = [f"{label}: {task['option_mapping'][label]}" for label in protocol.LABELS]
    sequence = " then ".join(task["operation_sequence"])
    state_legend = " ".join(str(value) for value in task["state_space"])
    trace = [] if arm == "NT" else [_trace(task, arm)]
    if task["template_id"] == "T-A":
        lines = [
            f"Task family: {task['family']}",
            f"States: {state_legend}",
            "Definitions:",
            *_definitions(task, protocol.OPERATOR_NAMES),
            f"Start: {task['start_state']}",
            f"Apply: {sequence}",
            "Options:",
            *options,
            *trace,
            "Answer:",
        ]
    else:
        lines = [
            f"Query: Start: {task['start_state']}; apply {sequence}.",
            "Options:",
            *options,
            f"State legend: {state_legend}",
            "Operator definitions:",
            *_definitions(task, tuple(reversed(protocol.OPERATOR_NAMES))),
            *trace,
            "Answer:",
        ]
    return "\n".join(lines)


def _anchor(prompt: str, start_state: int) -> dict[str, Any]:
    marker = f"Start: {start_state}"
    character_start = prompt.index(marker) + len("Start: ")
    byte_start = len(prompt[:character_start].encode("utf-8"))
    surface = str(start_state)
    return {
        "field": "Start:",
        "surface": surface,
        "byte_start": byte_start,
        "byte_end": byte_start + len(surface.encode("utf-8")),
    }


def _semantic_id(task: Mapping[str, Any]) -> str:
    payload = {
        "family": task["family"],
        "state_space": task["state_space"],
        "operators": task["operators"],
        "start_state": task["start_state"],
        "operation_sequence": task["operation_sequence"],
        "option_value_set": sorted(task["option_values"]),
        "ground_truth": task["ground_truth"],
    }
    return protocol.sha256_bytes(protocol.canonical_json_bytes(payload))


def _option_mapping(option_values: Sequence[int], correct: int, correct_label: str, *domain: object) -> dict[str, int]:
    remaining_values = _hash_order((value for value in option_values if value != correct), *domain, "value")
    remaining_labels = [label for label in protocol.LABELS if label != correct_label]
    mapping: dict[str, int] = {}
    cursor = 0
    for label in protocol.LABELS:
        if label == correct_label:
            mapping[label] = correct
        else:
            mapping[label] = remaining_values[cursor]
            cursor += 1
    return mapping


def _counterfactual(primitive: Mapping[str, Any], *domain: object) -> tuple[dict[str, int | str], int]:
    size = len(primitive["state_space"])
    pre_answer = primitive["ground_truth"]["pre_answer_intermediate"]
    wrong_candidates = [value for value in primitive["state_space"] if value != pre_answer]
    wrong = _hash_order(wrong_candidates, *domain, "wrong-intermediate")[0]
    by_name = {operator["name"]: operator for operator in primitive["operators"]}
    final_operator = by_name[primitive["operation_sequence"][-1]]
    implied = _apply(final_operator, wrong, primitive["family"])
    return {
        "wrong_pre_answer_intermediate": wrong,
        "implied_final_state": implied,
        "implied_label": "",
    }, implied


def _behavioral_row(role: str, family: str, depth: int, index: int) -> dict[str, Any]:
    seed = protocol.SEEDS[role]
    size = 8 if family == "permutation_chain" else 10
    label = protocol.LABELS[index % 4]
    template_id = _template(index)
    start = _balanced_value(index, size, 0)
    desired_pre = start if depth == 1 else _balanced_value(index, size, 2)
    desired_final = _balanced_value(index, size, 4)
    sequence = _sequence(index, depth, 0)
    primitive = _primitive(
        seed=seed,
        family=family,
        depth=depth,
        start=start,
        sequence=sequence,
        desired_pre_answer=desired_pre,
        desired_final=desired_final,
        domain=(role, family, depth, index, "primary"),
        require_distinct_trace_states=depth == 3,
    )
    counterfactual, implied = _counterfactual(primitive, seed, role, family, depth, index)
    other_states = [value for value in primitive["state_space"] if value not in {desired_final, implied}]
    extras = _hash_order(other_states, seed, role, family, depth, index, "distractors")[:2]
    option_values = sorted([desired_final, implied, *extras])
    mapping = _option_mapping(
        option_values,
        desired_final,
        label,
        protocol.SEEDS["option_permutation"],
        seed,
        role,
        family,
        depth,
        index,
    )
    counterfactual["implied_label"] = next(key for key, value in mapping.items() if value == implied)
    task: dict[str, Any] = {
        **{key: value for key, value in primitive.items() if key != "attempt"},
        "template_id": template_id,
        "option_values": option_values,
        "option_mapping": mapping,
        "correct_label": label,
        "counterfactual": counterfactual,
    }
    semantic_id = _semantic_id(task)
    item_id = f"s2-{role}-{family}-d{depth}-{index + 1:04d}"
    arms = ["NT"] + (["PT", "WT"] if depth >= 2 else []) + (["ST"] if depth == 3 else [])
    prompts = {arm: _render(task, arm) for arm in arms}
    nt_anchor = _anchor(prompts["NT"], start)
    return {
        "schema_version": protocol.TASK_ROW_VERSION,
        "role": role,
        "item_id": item_id,
        "semantic_id": semantic_id,
        "family": family,
        "depth": depth,
        "template_id": template_id,
        "seed": seed,
        "counter": index,
        "state_space": task["state_space"],
        "operators": task["operators"],
        "start_state": start,
        "operation_sequence": sequence,
        "ground_truth": task["ground_truth"],
        "option_values": option_values,
        "option_mapping": mapping,
        "correct_label": label,
        "counterfactual": counterfactual,
        "prompts": prompts,
        "prompt_hashes": {arm: protocol.sha256_bytes(prompt.encode("utf-8")) for arm, prompt in prompts.items()},
        "start_anchor": nt_anchor,
        "balance": {
            "correct_label": label,
            "template_id": template_id,
            "start_state": start,
            "pre_answer_intermediate": desired_pre,
            "final_state": desired_final,
            "final_operator": sequence[-1],
        },
    }


def _pair_task(
    primitive: Mapping[str, Any],
    *,
    task_id: str,
    template_id: str,
    option_values: Sequence[int],
    mapping: Mapping[str, int],
) -> dict[str, Any]:
    correct = primitive["ground_truth"]["final_state"]
    label = next(label for label in protocol.LABELS if mapping[label] == correct)
    task: dict[str, Any] = {
        **{key: value for key, value in primitive.items() if key != "attempt"},
        "template_id": template_id,
        "option_values": list(option_values),
        "option_mapping": dict(mapping),
        "correct_label": label,
        "counterfactual": None,
    }
    semantic_id = _semantic_id(task)
    prompt = _render(task, "NT")
    return {
        "task_id": task_id,
        "semantic_id": semantic_id,
        "family": task["family"],
        "depth": task["depth"],
        "template_id": template_id,
        "state_space": task["state_space"],
        "operators": task["operators"],
        "start_state": task["start_state"],
        "operation_sequence": task["operation_sequence"],
        "ground_truth": task["ground_truth"],
        "option_values": list(option_values),
        "option_mapping": dict(mapping),
        "correct_label": label,
        "nt_prompt": prompt,
        "prompt_sha256": protocol.sha256_bytes(prompt.encode("utf-8")),
        "start_anchor": _anchor(prompt, task["start_state"]),
    }


def _pair_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "family": row["family"],
        "depth": row["depth"],
        "option_value_set": sorted(row["option_values"]),
        "donor_semantic_id": row["primary"]["donor"]["semantic_id"],
        "recipient_semantic_id": row["primary"]["recipient"]["semantic_id"],
        "same_intermediate_semantic_id": row["controls"]["same_intermediate_donor"]["semantic_id"],
        "same_answer_semantic_id": row["controls"]["same_answer_donor"]["semantic_id"],
        "random_semantic_id": row["controls"]["random_donor"]["semantic_id"],
        "m_d": row["primary"]["donor_intermediate"],
        "m_r": row["primary"]["recipient_intermediate"],
        "a_d": row["primary"]["donor_answer"],
        "a_r": row["primary"]["recipient_answer"],
        "a_x": row["primary"]["recombinant_answer"],
    }


def _candidate_pair(role: str, family: str, depth: int, local_index: int, partition: str) -> dict[str, Any]:
    seed = protocol.SEEDS[role]
    size = 8 if family == "permutation_chain" else 10
    balance_index = local_index + (0 if partition == "front" else 128)
    label = protocol.LABELS[balance_index % 4]
    template_id = _template(balance_index)
    m_r = _balanced_value(balance_index, size, 2)
    a_r = _balanced_value(balance_index, size, 4)
    start_r = _balanced_value(balance_index, size, 0)
    seq_r = _sequence(balance_index, depth, 0)
    m_d = (m_r + 1 + ((balance_index // size) % (size - 1))) % size
    if m_d == m_r:  # pragma: no cover - construction makes this impossible
        raise AssertionError("donor and recipient intermediate collided")

    for pair_attempt in range(1_000_000):
        prefix = (role, family, depth, partition, balance_index, pair_attempt)
        recipient_primitive = _primitive(
            seed=seed,
            family=family,
            depth=depth,
            start=start_r,
            sequence=seq_r,
            desired_pre_answer=m_r,
            desired_final=a_r,
            domain=(*prefix, "recipient"),
        )
        final_operator = {op["name"]: op for op in recipient_primitive["operators"]}[seq_r[-1]]
        a_x = _apply(final_operator, m_d, family)
        if a_x == a_r:
            continue
        remaining_answers = [value for value in range(size) if value not in {a_r, a_x}]
        ordered_answers = _hash_order(remaining_answers, seed, *prefix, "donor-answer")
        a_d, distractor = ordered_answers[:2]

        donor_primitive = _primitive(
            seed=seed,
            family=family,
            depth=depth,
            start=_balanced_value(balance_index, size, 1),
            sequence=_sequence(balance_index, depth, 1),
            desired_pre_answer=m_d,
            desired_final=a_d,
            domain=(*prefix, "donor"),
        )
        same_intermediate_primitive = _primitive(
            seed=seed,
            family=family,
            depth=depth,
            start=_balanced_value(balance_index, size, 3),
            sequence=_sequence(balance_index, depth, 2),
            desired_pre_answer=m_r,
            desired_final=distractor,
            domain=(*prefix, "same-intermediate"),
        )
        same_answer_m = (m_r + 2 + ((balance_index // 3) % (size - 1))) % size
        if same_answer_m == m_r:
            same_answer_m = (same_answer_m + 1) % size
        same_answer_primitive = _primitive(
            seed=seed,
            family=family,
            depth=depth,
            start=_balanced_value(balance_index, size, 5),
            sequence=_sequence(balance_index, depth, 3),
            desired_pre_answer=same_answer_m,
            desired_final=a_r,
            domain=(*prefix, "same-answer"),
        )
        option_values = sorted([a_d, a_r, a_x, distractor])
        random_primitive = _random_primitive(
            seed=protocol.SEEDS["random_controls"],
            family=family,
            depth=depth,
            option_values=option_values,
            forbidden_intermediate=m_r,
            forbidden_answer=a_r,
            domain=(*prefix, "random"),
        )
        mapping = _option_mapping(
            option_values,
            a_r,
            label,
            protocol.SEEDS["option_permutation"],
            seed,
            *prefix,
            "pair-options",
        )
        base_id = f"s2-{role}-{family}-d{depth}-{partition}-{balance_index + 1:04d}"
        recipient = _pair_task(recipient_primitive, task_id=f"{base_id}:recipient", template_id=template_id, option_values=option_values, mapping=mapping)
        donor = _pair_task(donor_primitive, task_id=f"{base_id}:donor", template_id=template_id, option_values=option_values, mapping=mapping)
        same_intermediate = _pair_task(same_intermediate_primitive, task_id=f"{base_id}:same-intermediate", template_id=template_id, option_values=option_values, mapping=mapping)
        same_answer = _pair_task(same_answer_primitive, task_id=f"{base_id}:same-answer", template_id=template_id, option_values=option_values, mapping=mapping)
        random_donor = _pair_task(random_primitive, task_id=f"{base_id}:random", template_id=template_id, option_values=option_values, mapping=mapping)
        if len({donor["semantic_id"], recipient["semantic_id"], same_intermediate["semantic_id"], same_answer["semantic_id"], random_donor["semantic_id"]}) != 5:
            continue
        recombinant_label = next(option_label for option_label, value in mapping.items() if value == a_x)
        row: dict[str, Any] = {
            "schema_version": protocol.PAIR_ROW_VERSION,
            "role": role,
            "pair_id": "",
            "pair_semantic_id": "",
            "family": family,
            "depth": depth,
            "template_id": template_id,
            "seed": seed,
            "counter": balance_index,
            "hash_partition": partition,
            "state_space": list(range(size)),
            "option_values": option_values,
            "option_mapping": mapping,
            "primary": {
                "donor": donor,
                "recipient": recipient,
                "donor_intermediate": m_d,
                "recipient_intermediate": m_r,
                "donor_answer": a_d,
                "recipient_answer": a_r,
                "recombinant_answer": a_x,
                "donor_label": donor["correct_label"],
                "recipient_label": label,
                "recombinant_label": recombinant_label,
            },
            "controls": {
                "no_op_donor": deepcopy(recipient),
                "same_intermediate_donor": same_intermediate,
                "same_answer_donor": same_answer,
                "random_donor": random_donor,
            },
            "wrong_position_anchor": deepcopy(recipient["start_anchor"]),
            "stage_t_selector": {},
            "balance": {
                "recipient_correct_label": label,
                "template_id": template_id,
                "recipient_start_state": start_r,
                "recipient_pre_answer_intermediate": m_r,
                "recipient_final_state": a_r,
                "recipient_final_operator": seq_r[-1],
                "hash_partition": partition,
            },
        }
        pair_semantic_id = protocol.sha256_bytes(protocol.canonical_json_bytes(_pair_payload(row)))
        observed_partition = "front" if int(pair_semantic_id[:2], 16) < 128 else "back"
        if observed_partition != partition:
            continue
        row["pair_semantic_id"] = pair_semantic_id
        row["pair_id"] = f"{role}:{family}:d{depth}:{pair_semantic_id[:16]}"
        row["stage_t_selector"] = {
            "sort_key": pair_semantic_id,
            "filter": "all_three_models_exact_pair_length_and_answer_position_alignment",
            "selection": "first_128_per_role_family_depth_by_sort_key",
            "outcome_fields_allowed": [],
        }
        return row
    raise RuntimeError("deterministic candidate-pair search exhausted")


def build_role_rows(role: str) -> list[dict[str, Any]]:
    if role in {"development", "behavioral_confirmation"}:
        rows: list[dict[str, Any]] = []
        per_cell = protocol.EXPECTED_CELL_COUNTS[role]
        for family in protocol.FAMILIES:
            for depth in protocol.DEPTHS:
                rows.extend(_behavioral_row(role, family, depth, index) for index in range(per_cell))
        return rows
    if role in {"mechanistic_development", "mechanistic_candidate_confirmation"}:
        rows = []
        for family in protocol.FAMILIES:
            for depth in protocol.COMPOSITIONAL_DEPTHS:
                for partition in ("front", "back"):
                    rows.extend(_candidate_pair(role, family, depth, index, partition) for index in range(128))
        return rows
    raise ValueError(f"unregistered role {role}")


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    raw = b"".join(protocol.canonical_json_bytes(row) for row in rows)
    path.write_bytes(raw)


def generate_all(root: Path, output_root: Path | None = None) -> dict[str, Any]:
    output = output_root or root / "studies/study2/data"
    protocol_document = protocol.load_and_validate_protocol(root)
    output.mkdir(parents=True, exist_ok=True)
    for role, filename in protocol.BANK_FILES.items():
        _write_jsonl(output / filename, build_role_rows(role))

    # The manifest can only be emitted after the separately coded verifier has
    # reconstructed every just-written row.  Verification expects the canonical
    # repository path, so noncanonical outputs are for deterministic comparisons
    # only and intentionally receive no manifest.
    if output.resolve() != (root / "studies/study2/data").resolve():
        return {
            role: {
                "path": str(output / filename),
                "bytes": (output / filename).stat().st_size,
                "sha256": protocol.sha256_file(output / filename),
            }
            for role, filename in protocol.BANK_FILES.items()
        }

    report = protocol.verify_task_banks(root, require_manifest=False)
    files = {
        role: {
            "path": f"studies/study2/data/{filename}",
            "rows": protocol.EXPECTED_ROLE_COUNTS[role],
            "bytes": (output / filename).stat().st_size,
            "sha256": protocol.sha256_file(output / filename),
        }
        for role, filename in protocol.BANK_FILES.items()
    }
    protocol_path = root / "studies/study2/protocol/reasoning_internalization_protocol.json"
    manifest = {
        "schema_version": protocol.MANIFEST_VERSION,
        "status": (
            "CANDIDATE_MODEL_FREE_BANKS"
            if protocol_document["status"] == "CANDIDATE_AWAITING_REVIEW"
            else "FROZEN_MODEL_FREE_BANKS"
        ),
        "generated_by": "src/jspace_observation/study2_task_bank.py",
        "protocol_sha256": protocol.sha256_file(protocol_path),
        "files": files,
        "role_counts": report["role_counts"],
        "semantic_overlap_counts": report["semantic_overlap_counts"],
        "protected_prompt_count": report["protected_prompt_count"],
        "protected_prompt_overlap": report["protected_prompt_overlap"],
        "ground_truth_rows_verified": sum(protocol.EXPECTED_ROLE_COUNTS.values()),
        "balance": report["balance"],
        "seeds": protocol.SEEDS,
        "determinism": {
            "algorithm": "sha256_counter_mode_with_rejection_randbelow",
            "python_hash_used": False,
            "rng_state_used": False,
            "manifest_written_last": True,
        },
    }
    (output / "task_bank_manifest.json").write_bytes(protocol.canonical_json_bytes(manifest))
    protocol.verify_task_banks(root, require_manifest=True)
    return manifest
