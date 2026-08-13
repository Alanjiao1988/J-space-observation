#!/usr/bin/env python3
"""Generation-3 model execution: the observation itself is what gets stored.

This is the only generation-3 module that may ever touch a model library, and
like its predecessors it lives under ``execution/`` so that every other
generation-3 module stays importable and testable with no model library
present.

It changes **no** scientific rule. The allocation, the caps, the exact 60-prefill
smoke criterion, the scoring rules, the parser and every statistic are the
registered generation-2 implementations, imported and called unmodified. What
changes is what reaches durable storage.

Generation 2 recorded, for a completed scored row::

    journal.complete(row_admission, outcome={"row_id": row_id})

If the replica died one row later, an operator recovering the journal learned
that a row called ``S1-014`` had once existed. The score, the raw completion,
the parse and the logits were gone. That is an index of lost evidence, not
evidence.

The adapter below sits between the registered executor and the durable journal.
Every time the executor closes an admission, the adapter reads what the
executor actually appended to the shared ``PartialResults`` object and writes
the **complete payload** durably before returning. The executor is unmodified
and unaware; the record becomes sufficient.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

P0_R1_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if P0_R1_DIR not in sys.path:
    sys.path.insert(0, P0_R1_DIR)

import p0_r1_journal_v3 as JOURNAL_V3  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-model-execution-v3"

# Registered generation-2 operation names mapped onto the payload-bearing kind
# whose complete contents must be stored when the operation closes.
PAYLOAD_FOR_OPERATION = {
    "s1_scored_row": "scored_row",
    "s2_scored_row": "scored_row",
    "s3_scored_row": "scored_row",
    "s4_scored_row": "scored_row",
    "scored_row": "scored_row",
    "s2_vector_reuse": "s2_vector_reuse",
    "s4_generation": "s4_raw_completion",
    "parser_call": "parser_call",
    "smoke_transition": "smoke_transition",
}

IRREVERSIBLE_ALIASES = {
    "checkpoint_download_or_load": "checkpoint_download",
    "tokenizer_construction": "tokenizer_construction",
    "tokenizer_encode": "tokenizer_encode",
    "encode": "tokenizer_encode",
    "prompt_encode": "tokenizer_encode",
    "model_weight_load": "model_weight_load",
    "cuda_initialization": "cuda_initialization",
    "prefill": "prefill_evaluation",
    "prefill_evaluation": "prefill_evaluation",
    "s4_generation": "generation_call",
    "generation": "generation_call",
    "generation_or_decode": "generation_call",
}


class ExecutionDefect(Exception):
    """The generation-3 execution boundary refused."""


class CompletePayloadJournal(object):
    """Adapt the registered executor's journal calls onto a durable record.

    Presents the exact ``admit`` / ``complete`` / ``failed`` / ``record``
    surface the generation-2 executor calls, and additionally stores the full
    observation. Nothing is summarized on the way in.
    """

    def __init__(self, journal, partial):
        self.journal = journal
        self.partial = partial
        self._open = {}
        self._rows_seen = 0
        self._completions_seen = 0

    @property
    def sequence(self):
        return self.journal.index

    def _kind_for(self, operation):
        return IRREVERSIBLE_ALIASES.get(operation)

    def admit(self, operation, detail=None, counter_updates=None,
              identity_updates=None):
        kind = self._kind_for(operation)
        if kind is None:
            # Not an irreversible external call: still recorded, but as a
            # payload entry so nothing silently disappears.
            record = self.journal.record("counter_snapshot", {
                "operation": operation, "state": "admitted",
                "detail": detail or {}})
            token = ("soft", record["sequence"])
        else:
            token = ("hard", self.journal.admit(kind, detail=detail))
        self._open[id(token)] = (operation, token)
        return token

    def _drain_new_payloads(self, operation):
        """Store every observation the executor appended since the last close."""
        stored = []
        rows = list(getattr(self.partial, "scored_rows", ()) or ())
        while self._rows_seen < len(rows):
            row = rows[self._rows_seen]
            self._rows_seen += 1
            stored.append(self.journal.record("scored_row", row))
        completions = list(getattr(self.partial, "s4_completions", ()) or ())
        while self._completions_seen < len(completions):
            completion = completions[self._completions_seen]
            self._completions_seen += 1
            stored.append(self.journal.record("s4_raw_completion", completion))
        return stored

    def complete(self, token, outcome=None):
        operation, _ = self._open.pop(id(token), (None, None))
        stored = self._drain_new_payloads(operation)
        kind, value = token if isinstance(token, tuple) else ("soft", None)
        if kind == "hard":
            self.journal.complete(value, payload={
                "operation": operation,
                "outcome": outcome,
                "stored_payload_entries": [entry["name"] for entry in stored],
            })
        else:
            self.journal.record("counter_snapshot", {
                "operation": operation, "state": "completed",
                "outcome": outcome,
                "stored_payload_entries": [entry["name"] for entry in stored]})
        return stored

    def failed(self, token, error, outcome=None):
        operation, _ = self._open.pop(id(token), (None, None))
        self._drain_new_payloads(operation)
        kind, value = token if isinstance(token, tuple) else ("soft", None)
        if kind == "hard":
            return self.journal.fail(value, error, payload={
                "operation": operation, "outcome": outcome})
        return self.journal.record("exception", {
            "operation": operation, "error": str(error), "outcome": outcome})

    def record(self, event, payload=None, counters=None):
        kind = PAYLOAD_FOR_OPERATION.get(event, "counter_snapshot")
        if kind not in JOURNAL_V3.PAYLOAD_BEARING_KINDS:
            kind = "counter_snapshot"
        return self.journal.record(kind, {
            "event": event, "payload": payload, "counters": counters})

    def open_attempt(self, detail=None):
        return self.journal.record("counter_snapshot", {
            "event": "open_attempt", "detail": detail or {}})

    def interruption(self):
        self._drain_new_payloads("interruption")
        return self.journal.interruption()


def execute(authorized, counters, partial, journal, out_dir=None, root=None,
            device=None, corpus_rows=None, identities=None,
            executor_module=None):
    """Run the registered bounded pilot with a complete-payload journal.

    ``journal`` is the generation-3 :class:`DurableJournal`. It is wrapped so
    the unmodified registered executor writes complete observations.
    """
    if journal is None:
        raise ExecutionDefect(
            "the generation-3 execution boundary requires a durable journal; "
            "an unjournaled model operation is unrecoverable by construction")

    adapter = CompletePayloadJournal(journal, partial)
    module = executor_module
    if module is None:
        import p0_r1_model_execution_v2 as EXEC_V2
        module = EXEC_V2
    try:
        state = module.execute(
            authorized, counters, partial, adapter, out_dir=out_dir,
            root=root, device=device, corpus_rows=corpus_rows,
            identities=identities)
    finally:
        # Whatever happened, every observation the executor produced is stored
        # before this frame unwinds.
        adapter._drain_new_payloads("finalization")
        adapter.interruption()
    journal.record("counter_snapshot", {
        "event": "execution_complete",
        "counters": counters.snapshot() if hasattr(counters, "snapshot")
        else None,
        "state": state,
    })
    return state


def implementation_identity(root=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "execution/p0_r1_model_execution_v3.py",
        "delegates_science_to": "execution/p0_r1_model_execution_v2.execute",
        "changes_any_scientific_rule": False,
        "stores_complete_payloads": True,
        "payload_for_operation": dict(PAYLOAD_FOR_OPERATION),
        "irreversible_aliases": dict(IRREVERSIBLE_ALIASES),
        "closes": "G2-07",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", action="store_true")
    args = parser.parse_args(argv)
    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
