"""Study 4F-M1 execution scheduler.

This module is an ORCHESTRATION layer only. Every scientific decision -- item
construction, bank realization, prompt rendering, parsing, scoring, cell
boundaries and state transitions -- is delegated to the already published
Study 4F instrument. Nothing here reimplements, reinterprets or relaxes it.

What this module adds, and all it adds:

* binding a cell deterministically to exactly one GPU worker;
* a create-only item journal so an interrupted run resumes without duplicating
  or replacing a completed item;
* recording GPU identity, container digest and checkpoint digest per item;
* enforcing the dependency rules that make parallelism legal.

The parallelism rule is deliberately narrow. Two cells may run concurrently
only when the published state machine treats them as simultaneously eligible
and independent. Concretely:

* the ladder is sequential: RP_B1 must resolve before RP_B2 is scheduled, and
  RP_B2 before RP_B3, because a later candidate is only reached when the
  earlier one fails;
* within one candidate, CoT D2 and CoT D3 are independent and may run
  concurrently on different GPUs;
* E0 is never scheduled for a candidate until BOTH of its CoT cells have passed,
  because E0 is gated on CoT headroom;
* RT is never scheduled until a candidate has qualified.

Item remains the statistical unit. GPU workers are an execution detail and are
never treated as independent samples, and a repeated response is never treated
as a new sample.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_ANALYSIS = Path(__file__).resolve().parents[2] / "analysis"
if str(_ANALYSIS) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS))

import study4f_design_statistics as stats  # noqa: E402
import study4f_state_machine as machine  # noqa: E402
import study4f_task_banks as banks  # noqa: E402

ORIGINAL_STUDY4F_AUTHORITY_COMMIT = "7d5ff0837d77af9e6df9f49d580ec0e42bdc2729"
LADDER: Tuple[str, ...] = ("RP_B1", "RP_B2", "RP_B3")
TARGET = machine.TARGET
DEPTHS: Tuple[str, ...] = ("D2", "D3")
BANK_FOR_DEPTH = {"D2": "D2_DEVELOPMENT_BANK", "D3": "D3_DEVELOPMENT_BANK"}


class SchedulerError(RuntimeError):
    """Raised when a scheduling rule would be violated."""


@dataclass(frozen=True)
class Worker:
    """One isolated single-GPU worker."""

    index: int
    gpu_uuid: str

    def env(self) -> Dict[str, str]:
        return {
            "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
            "CUDA_VISIBLE_DEVICES": str(self.index),
        }


@dataclass(frozen=True)
class Cell:
    """One registered (checkpoint, depth, route) cell."""

    role: str
    depth: str
    route: str

    @property
    def cell_id(self) -> str:
        return stats.cell_id(self.role, self.depth, self.route)

    @property
    def n(self) -> int:
        return 104 if self.route == "COT" else 60

    @property
    def pass_boundary(self) -> int:
        return 90 if self.route == "COT" else 41


class ItemJournal:
    """Create-only journal. A completed item is never rewritten or replaced."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._seen: Dict[str, Dict[str, object]] = {}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists():
            with self._path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    self._seen[record["journal_key"]] = record

    @staticmethod
    def key(cell: "Cell", item_key: str) -> str:
        return f"{cell.cell_id}|{item_key}"

    def completed(self, cell: "Cell", item_key: str) -> Optional[Dict[str, object]]:
        return self._seen.get(self.key(cell, item_key))

    def append(self, record: Mapping[str, object]) -> None:
        journal_key = str(record["journal_key"])
        with self._lock:
            if journal_key in self._seen:
                raise SchedulerError(
                    f"refusing to rewrite a completed journal entry: {journal_key}"
                )
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._seen[journal_key] = dict(record)

    def cell_records(self, cell: "Cell") -> List[Dict[str, object]]:
        prefix = cell.cell_id + "|"
        return [v for k, v in self._seen.items() if k.startswith(prefix)]


def realize_bank(depth: str) -> List[Dict[str, object]]:
    """Realize a registered bank using the ORIGINAL Study 4F authority hash."""
    if depth not in BANK_FOR_DEPTH:
        raise SchedulerError(f"unregistered depth: {depth}")
    return banks.realize_bank(
        BANK_FOR_DEPTH[depth], ORIGINAL_STUDY4F_AUTHORITY_COMMIT
    )


def cell_correct_count(journal: ItemJournal, cell: Cell) -> int:
    """Correct count for a cell. Unparseable is incorrect, never dropped."""
    records = journal.cell_records(cell)
    return sum(1 for record in records if record.get("outcome") == "correct")


def cell_is_complete(journal: ItemJournal, cell: Cell) -> bool:
    return len(journal.cell_records(cell)) >= cell.n


def cell_passes(journal: ItemJournal, cell: Cell) -> bool:
    """Delegate the pass decision to the registered exact binomial boundary."""
    if not cell_is_complete(journal, cell):
        raise SchedulerError(
            f"cell {cell.cell_id} is incomplete; a pass decision is not defined"
        )
    return stats.passes(cell.route, cell_correct_count(journal, cell))


def plan_next_batch(
    results: Mapping[Tuple[str, str, str], bool],
    completed_cells: Sequence[Cell],
) -> List[Cell]:
    """Return the cells that may legally run concurrently right now.

    The ladder, the CoT-gates-E0 precondition and the RT gate are all honoured.
    An empty list means the study is finished or blocked on a running cell.
    """
    done = {(c.role, c.depth, c.route) for c in completed_cells}

    def both_cot_done(role: str) -> bool:
        return all((role, d, "COT") in done for d in DEPTHS)

    def both_cot_passed(role: str) -> bool:
        return both_cot_done(role) and all(
            results[(role, d, "COT")] for d in DEPTHS
        )

    def both_e0_done(role: str) -> bool:
        return all((role, d, "E0") in done for d in DEPTHS)

    for role in LADDER:
        if not both_cot_done(role):
            # CoT D2 and CoT D3 are independent: they may run together.
            return [
                Cell(role, d, "COT") for d in DEPTHS if (role, d, "COT") not in done
            ]
        if not both_cot_passed(role):
            # This candidate failed CoT. Move to the next candidate.
            continue
        if not both_e0_done(role):
            # E0 is unlocked only because both CoT cells passed.
            return [
                Cell(role, d, "E0") for d in DEPTHS if (role, d, "E0") not in done
            ]
        if not all(results[(role, d, "E0")] for d in DEPTHS):
            # Candidate did not qualify on E0. Try the next candidate.
            continue
        # Candidate qualified. RT is now gated in.
        if not both_cot_done(TARGET):
            return [
                Cell(TARGET, d, "COT")
                for d in DEPTHS
                if (TARGET, d, "COT") not in done
            ]
        if not both_cot_passed(TARGET):
            return []
        if not both_e0_done(TARGET):
            return [
                Cell(TARGET, d, "E0")
                for d in DEPTHS
                if (TARGET, d, "E0") not in done
            ]
        return []
    return []


def bind_worker(cell: Cell, workers: Sequence[Worker]) -> Worker:
    """Deterministically bind a cell to exactly one worker."""
    if not workers:
        raise SchedulerError("no workers available")
    ordered = sorted(workers, key=lambda w: w.index)
    slot = (LADDER + (TARGET,)).index(cell.role) * len(DEPTHS)
    slot += DEPTHS.index(cell.depth)
    return ordered[slot % len(ordered)]


def final_state(results: Mapping[Tuple[str, str, str], bool]) -> Dict[str, object]:
    """Delegate the terminal decision entirely to the published state machine."""
    return machine.run_study(results)


__all__ = [
    "ORIGINAL_STUDY4F_AUTHORITY_COMMIT",
    "Cell",
    "ItemJournal",
    "SchedulerError",
    "Worker",
    "bind_worker",
    "cell_correct_count",
    "cell_is_complete",
    "cell_passes",
    "final_state",
    "plan_next_batch",
    "realize_bank",
]
