"""Counter ontology and cap enforcement for the Study 3-P0 feasibility pilot.

Authority: ``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md``
sections 6, 7.1, 8.2 and 8.3.

Two rules shape this module.

*Separate namespace.* All pre-existing formal Study 3 counters remain historical
facts. P0 counts into its own namespace and never touches them. A P0 count is
never a formal Study 3 operation count.

*Cumulative and non-resettable.* Counters accumulate across every attempt,
including failed and retried attempts, and are never reset. The pilot must stop
*before* exceeding any cap rather than recording an overrun.

A runtime batched forward call is counted separately and may never be
substituted for a sequence-level quantity. Batch tokenizer APIs must still count
the number of encoded sequences as well as the runtime batch call.
"""

import json

NAMESPACE = "study3-p0-pilot-counters"

# Registered cumulative maxima. Section 7.1 fixes the tokenizer cap; section 8.3
# fixes every model-operation cap.
CAPS = {
    "tokenizer_encoded_sequences": 10000,
    "non_generative_prefill_evaluations": 180,
    "s4_generation_calls": 12,
    "s4_prefill_evaluations": 12,
    "s4_incremental_decode_evaluations": 36,
    "total_sequence_level_model_evaluation_equivalents": 228,
    "s1_scored_rows": 162,
    "s2_scored_rows": 18,
    "s3_cpu_only_reuse_scored_rows": 18,
    "s4_scored_generation_rows": 12,
    "total_scored_rows": 210,
    "distinct_checkpoint_identities_downloaded": 3,
    "distinct_tokenizer_identities_constructed": 3,
    "model_weight_loads": 3,
    "gpu_jobs_performing_a_model_operation": 1,
    "additional_gpu_attempt_with_signed_zero_operation_receipt": 1,
    "hosted_provider_inference_calls": 0,
    "seeds_drawn": 0,
    "bank_rows_written": 0,
    "positive_reference_operations": 0,
}

# The smoke allocation of section 8.2, which is exact rather than a maximum.
SMOKE_EXACT = {
    "non_generative_prefill_evaluations": 60,
    "s4_generation_calls": 0,
    "s3_cpu_only_reuse_scored_rows": 6,
    "total_scored_rows": 66,
}

# Counters that are recorded but deliberately uncapped, because they describe
# runtime behaviour rather than authorized scientific operations.
UNCAPPED_OBSERVATIONS = (
    "runtime_batched_forward_calls",
    "runtime_batched_tokenizer_calls",
    "parser_calls",
    "restricted_logit_reads",
    "generated_tokens",
    "exceptions_observed",
)

ZERO_BEFORE_EXECUTION = tuple(sorted(set(CAPS) | set(UNCAPPED_OBSERVATIONS)))


class CapExceeded(Exception):
    """Raised before an operation that would exceed a registered cumulative cap."""


class CounterDefect(Exception):
    """Raised when a counter is missing, negative, reset or unregistered."""


class P0Counters(object):
    """A cumulative, non-resettable P0 counter set."""

    def __init__(self, initial=None):
        self._counts = {name: 0 for name in ZERO_BEFORE_EXECUTION}
        if initial:
            for name, value in initial.items():
                if name not in self._counts:
                    raise CounterDefect("unregistered counter %r" % name)
                if not isinstance(value, int) or value < 0:
                    raise CounterDefect("counter %r is not a natural number" % name)
                self._counts[name] = value

    def __getitem__(self, name):
        if name not in self._counts:
            raise CounterDefect("unregistered counter %r" % name)
        return self._counts[name]

    def snapshot(self):
        return dict(self._counts)

    def all_zero(self):
        return all(value == 0 for value in self._counts.values())

    def add(self, name, amount=1):
        """Increment a counter, refusing in advance to cross a registered cap."""
        if name not in self._counts:
            raise CounterDefect("unregistered counter %r" % name)
        if not isinstance(amount, int) or amount < 0:
            raise CounterDefect("a counter may only advance by a natural number")
        proposed = self._counts[name] + amount
        cap = CAPS.get(name)
        if cap is not None and proposed > cap:
            raise CapExceeded(
                "%s would reach %d, exceeding the registered cap of %d; P0 stops "
                "before the operation" % (name, proposed, cap))
        self._counts[name] = proposed
        return proposed

    def reconcile_totals(self):
        """Check the registered arithmetic between derived and primitive counters."""
        counts = self._counts
        expected_equivalents = (
            counts["non_generative_prefill_evaluations"]
            + counts["s4_prefill_evaluations"]
            + counts["s4_incremental_decode_evaluations"])
        if counts["total_sequence_level_model_evaluation_equivalents"] \
                != expected_equivalents:
            raise CounterDefect(
                "total_sequence_level_model_evaluation_equivalents is %d but the "
                "registered sum of its parts is %d"
                % (counts["total_sequence_level_model_evaluation_equivalents"],
                   expected_equivalents))
        expected_rows = (
            counts["s1_scored_rows"] + counts["s2_scored_rows"]
            + counts["s3_cpu_only_reuse_scored_rows"]
            + counts["s4_scored_generation_rows"])
        if counts["total_scored_rows"] != expected_rows:
            raise CounterDefect(
                "total_scored_rows is %d but the registered sum of its parts is %d"
                % (counts["total_scored_rows"], expected_rows))
        for name in ("hosted_provider_inference_calls", "seeds_drawn",
                     "bank_rows_written", "positive_reference_operations"):
            if counts[name] != 0:
                raise CounterDefect(
                    "%s must remain exactly zero under this authority" % name)
        return True

    def merge_cumulative(self, previous):
        """Fold a previous attempt's counters in; a counter may never decrease."""
        for name, value in previous.items():
            if name not in self._counts:
                raise CounterDefect("unregistered counter %r" % name)
            if self._counts[name] < value:
                raise CounterDefect(
                    "counter %r would decrease from %d to %d; P0 counters are "
                    "cumulative and non-resettable"
                    % (name, value, self._counts[name]))
        return True


def ontology_document():
    """Return the machine-readable counter ontology."""
    return {
        "namespace": NAMESPACE,
        "separate_from": (
            "every pre-existing formal Study 3 counter, which remains a "
            "historical fact and is never touched by P0"),
        "cumulative": True,
        "resettable": False,
        "unit_semantics": {
            "non_generative_prefill_evaluations": (
                "one sequence-level prefill evaluation of one prompt by one role "
                "for S1 or S2; it is never a runtime batch call"),
            "s4_prefill_evaluations": (
                "the sequence-level prefill of one S4 generation call"),
            "s4_incremental_decode_evaluations": (
                "one incremental decode step of one S4 generation call; at "
                "max_new_tokens=4 a completed call contributes at most three"),
            "s4_generation_calls": "one bounded greedy generation call",
            "s3_cpu_only_reuse_scored_rows": (
                "one scored row produced on CPU from an already captured S2 logit "
                "vector; it adds exactly zero model evaluations"),
            "tokenizer_encoded_sequences": (
                "one encoded sequence; a batch API must count every sequence it "
                "encodes as well as the runtime batch call"),
            "runtime_batched_forward_calls": (
                "one runtime batched forward call, recorded separately and never "
                "substituted for a sequence-level quantity"),
        },
        "caps": dict(CAPS),
        "smoke_exact_allocation": dict(SMOKE_EXACT),
        "uncapped_recorded_observations": list(UNCAPPED_OBSERVATIONS),
        "zero_before_execution": list(ZERO_BEFORE_EXECUTION),
        "on_cap": (
            "the pilot stops before the operation that would cross a cap; an "
            "overrun is never recorded as a completed operation"),
        "on_failure": (
            "a failed, partial, retried or aborted attempt keeps its counters; "
            "they are never erased, overwritten or relabelled as a successful run"),
        "zero_operation_retry": (
            "one additional GPU attempt is authorized only when a signed job "
            "receipt proves that zero tokenizer, model-load, prefill, decode, "
            "scoring and generation operations occurred"),
    }


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
