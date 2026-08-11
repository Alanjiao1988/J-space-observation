"""Counter ontology and cap enforcement for the Study 3 P0-R1 continuation.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections 6
and 7.

Three rules shape this module.

*Separate namespace.* Every pre-existing formal Study 3 counter and every
consumed P0-T counter remains a historical fact. P0-R1 counts into its own
namespace and never touches either. A P0-R1 count is never a formal Study 3
operation count and never rewrites the immutable P0-T snapshot.

*Cumulative and non-resettable.* Counters accumulate across every attempt,
including failed and retried attempts, and are never reset. The continuation
must stop *before* exceeding any cap rather than recording an overrun.

*Identity counts are set cardinalities, not load events.* Section 7 requires an
aggregate view in which additive counters are summed while identity counts are
the cardinality of the distinct identity set. Reloading the same three pinned
tokenizer identities is therefore recorded by the separate additive counter
``tokenizer_construction_events`` and can never be hidden inside, or confused
with, ``distinct_tokenizer_identities_constructed``.
"""

import json

NAMESPACE = "study3-p0-r1-pilot-counters"

HISTORICAL_NAMESPACE = "study3-p0-pilot-counters"

# Section 7 retains the original P0-M allocation and maxima. Nothing here is
# widened: the common-prefix token changes token processing, not the number of
# sequence-level prefill evaluations.
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

# The K2 smoke allocation of section 7, which is exact rather than a maximum.
SMOKE_EXACT = {
    "non_generative_prefill_evaluations": 60,
    "s4_generation_calls": 0,
    "s3_cpu_only_reuse_scored_rows": 6,
    "total_scored_rows": 66,
}

# Counters that are recorded but deliberately uncapped, because they describe
# runtime behaviour or token processing rather than authorized scientific
# operations. ``common_prefix_tokens_processed`` is reported explicitly so the
# extra teacher-forced token is never silent and is never mistaken for an extra
# sequence-level evaluation.
UNCAPPED_OBSERVATIONS = (
    "runtime_batched_forward_calls",
    "runtime_batched_tokenizer_calls",
    "parser_calls",
    "restricted_logit_reads",
    "generated_tokens",
    "exceptions_observed",
    "tokenizer_construction_events",
    "common_prefix_tokens_processed",
    "registered_prompt_tokens_processed",
    "scoring_context_tokens_processed",
    "replay_gate_evaluations",
)

# Counters whose value is the cardinality of a distinct identity set rather than
# a count of events. Section 7 forbids summing these across attempts.
IDENTITY_CARDINALITY_COUNTERS = (
    "distinct_checkpoint_identities_downloaded",
    "distinct_tokenizer_identities_constructed",
)

ZERO_BEFORE_EXECUTION = tuple(sorted(set(CAPS) | set(UNCAPPED_OBSERVATIONS)))


class CapExceeded(Exception):
    """Raised before an operation that would exceed a registered cumulative cap."""


class CounterDefect(Exception):
    """Raised when a counter is missing, negative, reset or unregistered."""


class P0R1Counters(object):
    """A cumulative, non-resettable P0-R1 counter set."""

    def __init__(self, initial=None):
        self._counts = {name: 0 for name in ZERO_BEFORE_EXECUTION}
        self._identities = {name: set() for name in IDENTITY_CARDINALITY_COUNTERS}
        if initial:
            for name, value in initial.items():
                if name not in self._counts:
                    raise CounterDefect("unregistered counter %r" % name)
                if not isinstance(value, int) or isinstance(value, bool) \
                        or value < 0:
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
        if name in self._identities:
            raise CounterDefect(
                "%s is an identity cardinality, not an event count; register the "
                "identity with observe_identity instead" % name)
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise CounterDefect("a counter may only advance by a natural number")
        proposed = self._counts[name] + amount
        cap = CAPS.get(name)
        if cap is not None and proposed > cap:
            raise CapExceeded(
                "%s would reach %d, exceeding the registered cap of %d; P0-R1 "
                "stops before the operation" % (name, proposed, cap))
        self._counts[name] = proposed
        return proposed

    def observe_identity(self, name, identity):
        """Record a distinct identity; reloading the same one is not a new one.

        Constructing a tokenizer always advances the additive event counter
        ``tokenizer_construction_events``. Only a *new* repository/revision pair
        advances the identity cardinality.
        """
        if name not in self._identities:
            raise CounterDefect("%r is not an identity cardinality counter" % name)
        if not isinstance(identity, str) or not identity:
            raise CounterDefect("an identity must be a non-empty string")
        proposed = set(self._identities[name]) | {identity}
        cap = CAPS.get(name)
        if cap is not None and len(proposed) > cap:
            raise CapExceeded(
                "%s would reach %d distinct identities, exceeding the registered "
                "cap of %d; P0-R1 stops before the operation"
                % (name, len(proposed), cap))
        self._identities[name] = proposed
        self._counts[name] = len(proposed)
        return self._counts[name]

    def identities(self, name):
        if name not in self._identities:
            raise CounterDefect("%r is not an identity cardinality counter" % name)
        return sorted(self._identities[name])

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
        if counts["s3_cpu_only_reuse_scored_rows"] > counts["s2_scored_rows"]:
            raise CounterDefect(
                "S3 reuses an S2 discriminant-position logit vector; it cannot "
                "produce more scored rows (%d) than S2 produced (%d)"
                % (counts["s3_cpu_only_reuse_scored_rows"],
                   counts["s2_scored_rows"]))
        if counts["common_prefix_tokens_processed"] != counts["s2_scored_rows"]:
            raise CounterDefect(
                "the teacher-forced common-prefix token is processed exactly once "
                "per S2 scoring context: %d prefix tokens against %d S2 rows"
                % (counts["common_prefix_tokens_processed"],
                   counts["s2_scored_rows"]))
        expected_context = (counts["registered_prompt_tokens_processed"]
                            + counts["common_prefix_tokens_processed"])
        if counts["scoring_context_tokens_processed"] != expected_context:
            raise CounterDefect(
                "scoring_context_tokens_processed is %d but registered prompt "
                "tokens plus common-prefix tokens is %d"
                % (counts["scoring_context_tokens_processed"], expected_context))
        if counts["distinct_tokenizer_identities_constructed"] \
                > counts["tokenizer_construction_events"]:
            raise CounterDefect(
                "distinct tokenizer identities (%d) exceed tokenizer construction "
                "events (%d); an identity cannot exist without a construction"
                % (counts["distinct_tokenizer_identities_constructed"],
                   counts["tokenizer_construction_events"]))
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
                    "counter %r would decrease from %d to %d; P0-R1 counters are "
                    "cumulative and non-resettable"
                    % (name, value, self._counts[name]))
        return True


def aggregate_view(historical_p0_t, p0_r1_attempts):
    """Combine the immutable P0-T snapshot with the P0-R1 attempt counters.

    Additive counters are summed. Identity counters are set cardinalities: the
    aggregate is the cardinality of the union of the identity sets, which for
    the three pinned roles is 3 no matter how many times a tokenizer is
    constructed. ``tokenizer_construction_events`` carries the load events.
    """
    if not isinstance(historical_p0_t, dict):
        raise CounterDefect("the historical P0-T snapshot must be a mapping")
    attempts = list(p0_r1_attempts)
    aggregate = {}
    names = set(historical_p0_t) | set(ZERO_BEFORE_EXECUTION)
    for attempt in attempts:
        names |= set(attempt)
    for name in sorted(names):
        values = [historical_p0_t.get(name, 0)]
        values += [attempt.get(name, 0) for attempt in attempts]
        for value in values:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CounterDefect(
                    "counter %r carries a non-natural value" % name)
        if name in IDENTITY_CARDINALITY_COUNTERS:
            # A set cardinality is never summed. The pinned identities are the
            # same objects in every attempt, so the union cardinality is the
            # maximum observed cardinality, never the sum of the attempts.
            aggregate[name] = max(values)
        else:
            aggregate[name] = sum(values)
    return {
        "namespace": "study3-p0-aggregate-view",
        "historical_namespace": HISTORICAL_NAMESPACE,
        "attempt_namespace": NAMESPACE,
        "additive_counters_summed": True,
        "identity_counters_are_set_cardinalities": list(
            IDENTITY_CARDINALITY_COUNTERS),
        "attempt_count": len(attempts),
        "counters": aggregate,
    }


def ontology_document():
    """Return the machine-readable P0-R1 counter ontology."""
    return {
        "namespace": NAMESPACE,
        "historical_namespace": HISTORICAL_NAMESPACE,
        "separate_from": (
            "every pre-existing formal Study 3 counter and the immutable P0-T "
            "snapshot, both of which remain historical facts that P0-R1 never "
            "touches"),
        "cumulative": True,
        "resettable": False,
        "unit_semantics": {
            "non_generative_prefill_evaluations": (
                "one sequence-level prefill evaluation of one scoring context by "
                "one role for S1 or S2; it is never a runtime batch call and it "
                "does not increase because the S2 scoring context carries one "
                "extra teacher-forced token"),
            "s4_prefill_evaluations": (
                "the sequence-level prefill of one S4 generation call"),
            "s4_incremental_decode_evaluations": (
                "one incremental decode step of one S4 generation call; at "
                "max_new_tokens=4 a completed call contributes at most three"),
            "s4_generation_calls": "one bounded greedy generation call",
            "s3_cpu_only_reuse_scored_rows": (
                "one scored row produced on CPU from an already captured S2 "
                "discriminant-position logit vector; it adds exactly zero model "
                "evaluations, prefills, decodes and generations"),
            "tokenizer_encoded_sequences": (
                "one encoded sequence; a batch API must count every sequence it "
                "encodes as well as the runtime batch call"),
            "tokenizer_construction_events": (
                "one construction of a tokenizer object. Reloading the same "
                "pinned identity is a further event and is never hidden; it does "
                "not increase the distinct-identity cardinality"),
            "distinct_tokenizer_identities_constructed": (
                "the cardinality of the set of distinct repository/revision "
                "tokenizer identities constructed; a set cardinality, never a "
                "load-event count"),
            "distinct_checkpoint_identities_downloaded": (
                "the cardinality of the set of distinct repository/revision "
                "checkpoint identities downloaded; a set cardinality"),
            "common_prefix_tokens_processed": (
                "the number of teacher-forced common-prefix tokens appended to a "
                "scoring context. It is token processing, not a generation and "
                "not a sequence-level model evaluation"),
            "registered_prompt_tokens_processed": (
                "the number of registered prompt tokens processed, excluding the "
                "teacher-forced common prefix"),
            "scoring_context_tokens_processed": (
                "registered prompt tokens plus common-prefix tokens; the two "
                "component counters must reconcile to this total"),
            "replay_gate_evaluations": (
                "one replay-only factorization gate evaluation over immutable "
                "source artifacts; it performs zero tokenizer encodes and zero "
                "model operations"),
            "runtime_batched_forward_calls": (
                "one runtime batched forward call, recorded separately and never "
                "substituted for a sequence-level quantity"),
        },
        "caps": dict(CAPS),
        "smoke_exact_allocation": dict(SMOKE_EXACT),
        "uncapped_recorded_observations": list(UNCAPPED_OBSERVATIONS),
        "identity_cardinality_counters": list(IDENTITY_CARDINALITY_COUNTERS),
        "zero_before_execution": list(ZERO_BEFORE_EXECUTION),
        "aggregate_view_rule": (
            "additive counters are summed across the immutable P0-T snapshot and "
            "every P0-R1 attempt; identity counters are the cardinality of the "
            "union of the identity sets and are never summed"),
        "on_cap": (
            "the continuation stops before the operation that would cross a cap; "
            "an overrun is never recorded as a completed operation"),
        "on_failure": (
            "a failed, partial, retried or aborted attempt keeps its counters; "
            "they are never erased, overwritten or relabelled as a successful run"),
        "zero_operation_retry": (
            "one infrastructure retry is authorized only when a signed job "
            "receipt proves that zero tokenizer, model-load, prefill, decode, "
            "scoring and generation operations occurred"),
    }


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
