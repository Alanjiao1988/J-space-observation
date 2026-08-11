"""The Study 3 P0-R1 model runner: first-discriminative-token scoring.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections 3
and 7.

This module implements the registered draft-v0.6 scoring boundary. It does not
import, call, wrap, subclass or mutate the historical P0-T eligibility
classifier; the repaired classifier lives in ``p0_r1_eligibility``.

Two layers are deliberately separate.

*The scoring contract* -- ``build_scoring_plan``, ``validate_scoring_plan`` and
``score_from_logits`` -- is pure. It takes token IDs and a logit vector and
returns a scored row. It performs no model operation, so it is exercised
directly by the registration tests with synthetic logits and zero model
evaluations. Every section 8 mutation of the scoring boundary is rejected by
``validate_scoring_plan`` or ``score_from_logits`` on live input.

*The execution shell* -- ``run`` -- is the successor session's entry point. It
imports torch and transformers lazily, refuses to start without an explicit
one-shot authorization, and is never invoked by the calibration session.

The registered rule, restated exactly:

* ``S1``  one prefill on the registered prompt token IDs; read the next-token
  logits at the single position after the prompt; restrict to the four
  registered label token IDs.
* ``S2``  form the scoring context as the registered prompt token IDs followed
  by the verified common-prefix token; perform one ordinary prefill on that
  context; read the next-token logits only at the ten verified discriminant
  token IDs; map the deterministic restricted argmax back to the complete
  registered candidate surface.
* ``S3``  reuse the exact S2 discriminant-position logit vector on CPU. Zero
  model evaluations, model loads, prefills, decodes and generations.
* ``S4``  unchanged: bounded greedy generation mapped by the pinned parser,
  diagnostic-only, never selectable.
"""

import json
import os
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, P0_R1_DIR)

import p0_r1_factorization as FACT  # noqa: E402
from p0_r1_counters import P0R1Counters  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-scored-row-v1"

RESTRICTED_ARGMAX_PROFILES = ("S1", "S2", "S3")

# The registered tie break of the S2/S3 answer domain: ascending mod-10 residue
# order. It is unchanged from draft-v0.5 and may not be reordered.
REGISTERED_DIGIT_TIE_BREAK = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")


class ScoringDefect(Exception):
    """A fail-closed scoring stop. No row is emitted past one of these."""


class ExecutionRefused(Exception):
    """Raised when a model operation is attempted without live authorization."""


# ---------------------------------------------------------------------------
# The scoring contract.
# ---------------------------------------------------------------------------

def build_scoring_plan(profile, role, row_id, registered_prompt_token_ids,
                       candidate_token_ids, candidate_surfaces,
                       common_prefix_token=None, reuses_row_id=None,
                       tie_break_order=None):
    """Build the registered scoring plan for one row.

    ``candidate_token_ids`` is the complete registered candidate token sequence
    per candidate, exactly as the replay gate verified it. For S1 each sequence
    is one token; for S2/S3 each is the two-token
    ``common_prefix || discriminant``.
    """
    if profile not in RESTRICTED_ARGMAX_PROFILES:
        raise ScoringDefect(
            "%s does not use restricted-argmax scoring" % profile)
    prompt = [int(token) for token in registered_prompt_token_ids]
    if not prompt:
        raise ScoringDefect("the registered prompt token sequence is empty")
    sequences = [[int(token) for token in ids] for ids in candidate_token_ids]
    surfaces = list(candidate_surfaces)
    if len(sequences) != len(surfaces):
        raise ScoringDefect("candidate token IDs and surfaces are misaligned")

    lengths = sorted({len(ids) for ids in sequences})
    if lengths == [1]:
        if common_prefix_token is not None:
            raise ScoringDefect(
                "a single-token candidate set has no common prefix to force")
        context = list(prompt)
        discriminants = [ids[0] for ids in sequences]
        prefix_tokens = 0
    elif lengths == [2]:
        firsts = {ids[0] for ids in sequences}
        if len(firsts) != 1:
            raise ScoringDefect(
                "the two-token candidates do not share one common prefix token")
        derived_prefix = firsts.pop()
        if common_prefix_token is None:
            raise ScoringDefect(
                "the verified common-prefix token must be supplied explicitly")
        if int(common_prefix_token) != derived_prefix:
            raise ScoringDefect(
                "the supplied common-prefix token %r is not the token the "
                "candidate set actually shares (%r)"
                % (common_prefix_token, derived_prefix))
        context = list(prompt) + [derived_prefix]
        discriminants = [ids[1] for ids in sequences]
        prefix_tokens = 1
    else:
        raise ScoringDefect(
            "the registered candidate set is neither uniformly one token nor "
            "uniformly two tokens: observed lengths %s" % lengths)

    if len(set(discriminants)) != len(discriminants):
        raise ScoringDefect(
            "two discriminant token IDs collide: %s" % discriminants)

    order = list(tie_break_order) if tie_break_order is not None else list(surfaces)
    if sorted(order) != sorted(surfaces):
        raise ScoringDefect(
            "the tie-break order is not a permutation of the registered "
            "candidate surfaces")

    evaluations = 0 if profile == "S3" else 1
    if profile == "S3" and not reuses_row_id:
        raise ScoringDefect(
            "an S3 row must name the S2 row whose discriminant-position logit "
            "vector it reuses")
    if profile != "S3" and reuses_row_id:
        raise ScoringDefect(
            "only S3 reuses another row's logit vector")

    return {
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "role": role,
        "row_id": row_id,
        "registered_prompt_token_ids": prompt,
        "registered_prompt_token_count": len(prompt),
        "common_prefix_token": derived_prefix if prefix_tokens else None,
        "common_prefix_token_count": prefix_tokens,
        "teacher_forced_common_prefix": bool(prefix_tokens),
        "scoring_context_token_ids": context,
        "scoring_context_token_count": len(context),
        "logit_read_position": len(context) - 1,
        "candidate_surfaces": surfaces,
        "complete_candidate_token_ids": sequences,
        "discriminant_token_ids": discriminants,
        "restricted_logit_reads": len(discriminants),
        "sequence_level_model_evaluations": evaluations,
        "reuses_row_id": reuses_row_id,
        "tie_break_order": order,
    }


def validate_scoring_plan(plan):
    """Reject any plan that violates the registered scoring boundary.

    This is the production validator for section 3. Every section 8 mutation of
    the scoring boundary is rejected here, on the live plan the runner would
    actually execute.
    """
    if not isinstance(plan, dict):
        raise ScoringDefect("a scoring plan must be a mapping")
    for field in ("profile", "registered_prompt_token_ids",
                  "scoring_context_token_ids", "logit_read_position",
                  "discriminant_token_ids", "candidate_surfaces",
                  "complete_candidate_token_ids",
                  "sequence_level_model_evaluations", "tie_break_order"):
        if field not in plan:
            raise ScoringDefect("the scoring plan is missing %r" % field)

    prompt = plan["registered_prompt_token_ids"]
    context = plan["scoring_context_token_ids"]
    prefix = plan.get("common_prefix_token")
    sequences = plan["complete_candidate_token_ids"]
    surfaces = plan["candidate_surfaces"]
    discriminants = plan["discriminant_token_ids"]

    if context[:len(prompt)] != list(prompt):
        raise ScoringDefect(
            "the scoring context is not the registered prompt token IDs "
            "followed by the teacher-forced prefix; the registered prompt bytes "
            "may never be re-rendered or re-encoded")
    tail = context[len(prompt):]
    if plan.get("teacher_forced_common_prefix"):
        if tail != [prefix]:
            raise ScoringDefect(
                "the scoring context does not end with exactly the verified "
                "common-prefix token")
        if plan["common_prefix_token_count"] != 1:
            raise ScoringDefect(
                "exactly one teacher-forced common-prefix token is registered")
    else:
        if tail:
            raise ScoringDefect(
                "a single-token candidate set must not extend the scoring "
                "context")
        if plan.get("common_prefix_token_count"):
            raise ScoringDefect(
                "a single-token candidate set has no common-prefix token")

    if plan["scoring_context_token_count"] != len(context):
        raise ScoringDefect("the scoring-context token count is misrecorded")
    if plan["registered_prompt_token_count"] != len(prompt):
        raise ScoringDefect("the registered prompt token count is misrecorded")
    if plan["scoring_context_token_count"] != (
            plan["registered_prompt_token_count"]
            + plan["common_prefix_token_count"]):
        raise ScoringDefect(
            "the scoring-context token count does not reconcile with the "
            "registered prompt token count plus the common-prefix token count")

    if plan["logit_read_position"] != len(context) - 1:
        raise ScoringDefect(
            "the logits are read at position %d, not at the final position %d "
            "of the scoring context; reading before the teacher-forced common "
            "prefix scores the shared token instead of the discriminant"
            % (plan["logit_read_position"], len(context) - 1))

    lengths = sorted({len(ids) for ids in sequences})
    if lengths not in ([1], [2]):
        raise ScoringDefect(
            "the registered candidate set is neither uniformly one token nor "
            "uniformly two tokens: observed lengths %s" % lengths)
    if lengths == [2]:
        firsts = {ids[0] for ids in sequences}
        if len(firsts) != 1:
            raise ScoringDefect(
                "the complete candidates do not share one common prefix token")
        if firsts != {prefix}:
            raise ScoringDefect(
                "the complete candidates do not begin with the verified "
                "common-prefix token")
        if [ids[1] for ids in sequences] != list(discriminants):
            raise ScoringDefect(
                "a discriminant token does not come from its own complete "
                "candidate, so a digit token would map to the wrong complete "
                "candidate surface")
    else:
        if [ids[0] for ids in sequences] != list(discriminants):
            raise ScoringDefect(
                "a candidate token does not come from its own complete "
                "candidate surface")

    if len(set(discriminants)) != len(discriminants):
        raise ScoringDefect(
            "two discriminant token IDs collide: %s" % discriminants)
    if len(surfaces) != len(sequences):
        raise ScoringDefect("candidate surfaces and token IDs are misaligned")
    if plan["restricted_logit_reads"] != len(discriminants):
        raise ScoringDefect("the restricted logit read count is misrecorded")

    if sorted(plan["tie_break_order"]) != sorted(surfaces):
        raise ScoringDefect(
            "the tie-break order is not a permutation of the registered "
            "candidate surfaces")
    if plan["profile"] in ("S2", "S3"):
        expected = [" %s" % digit for digit in REGISTERED_DIGIT_TIE_BREAK]
        if list(plan["tie_break_order"]) != expected:
            raise ScoringDefect(
                "the registered S2/S3 tie-break order was changed from "
                "ascending mod-10 residue order to %s" % plan["tie_break_order"])

    if plan["profile"] == "S3":
        if plan["sequence_level_model_evaluations"] != 0:
            raise ScoringDefect(
                "S3 recorded %d sequence-level model evaluations; S3 reuses the "
                "S2 discriminant-position logit vector on CPU and adds exactly "
                "zero" % plan["sequence_level_model_evaluations"])
        if not plan.get("reuses_row_id"):
            raise ScoringDefect(
                "an S3 row must name the S2 row it reuses")
    else:
        if plan["sequence_level_model_evaluations"] != 1:
            raise ScoringDefect(
                "%s recorded %d sequence-level model evaluations; exactly one "
                "prefill per scored row is registered"
                % (plan["profile"], plan["sequence_level_model_evaluations"]))
    return True


def score_from_logits(plan, next_token_logits, counters=None):
    """Score one row from an already-obtained next-token logit vector.

    ``next_token_logits`` maps token ID to logit for at least the registered
    discriminant token IDs. Only those IDs are read. The deterministic restricted
    argmax is mapped back to the complete registered candidate surface, and the
    section 3.3 ranking equivalence is asserted mechanically for the two-token
    case.
    """
    validate_scoring_plan(plan)
    discriminants = plan["discriminant_token_ids"]
    surfaces = plan["candidate_surfaces"]
    order = plan["tie_break_order"]

    scores = {}
    for surface, token in zip(surfaces, discriminants):
        if token not in next_token_logits:
            raise ScoringDefect(
                "the logit vector does not carry the registered discriminant "
                "token %r" % token)
        value = next_token_logits[token]
        if value != value or value in (float("inf"), float("-inf")):
            raise ScoringDefect(
                "a non-finite logit was read at discriminant token %r" % token)
        scores[surface] = float(value)

    best = None
    for surface in order:
        if best is None or scores[surface] > scores[best]:
            best = surface

    if plan.get("teacher_forced_common_prefix"):
        # Section 3.3: the joint ranking over the complete two-token candidates
        # must agree with the ranking at the discriminant position. The common
        # factor P(u | x) cancels exactly.
        shifted = {surface: scores[surface] - max(scores.values())
                   for surface in surfaces}
        conditional = {}
        total = 0.0
        for surface in surfaces:
            weight = 2.718281828459045 ** shifted[surface]
            conditional[surface[-1]] = weight
            total += weight
        for digit in list(conditional):
            conditional[digit] /= total
        FACT.assert_ranking_equivalence(
            0.5, conditional,
            tie_break_order=[surface[-1] for surface in order])

    if counters is not None:
        counters.add("restricted_logit_reads", len(discriminants))
        if plan["profile"] == "S1":
            counters.add("s1_scored_rows", 1)
            counters.add("non_generative_prefill_evaluations", 1)
            counters.add("registered_prompt_tokens_processed",
                         plan["registered_prompt_token_count"])
            counters.add("scoring_context_tokens_processed",
                         plan["scoring_context_token_count"])
        elif plan["profile"] == "S2":
            counters.add("s2_scored_rows", 1)
            counters.add("non_generative_prefill_evaluations", 1)
            counters.add("common_prefix_tokens_processed",
                         plan["common_prefix_token_count"])
            counters.add("registered_prompt_tokens_processed",
                         plan["registered_prompt_token_count"])
            counters.add("scoring_context_tokens_processed",
                         plan["scoring_context_token_count"])
        else:
            counters.add("s3_cpu_only_reuse_scored_rows", 1)
        counters.add("total_scored_rows", 1)

    return {
        "schema_version": SCHEMA_VERSION,
        "profile": plan["profile"],
        "role": plan["role"],
        "row_id": plan["row_id"],
        "selected_complete_candidate_surface": best,
        "selected_discriminant_token": discriminants[surfaces.index(best)],
        "restricted_scores": scores,
        "registered_prompt_token_count": plan["registered_prompt_token_count"],
        "common_prefix_token_count": plan["common_prefix_token_count"],
        "scoring_context_token_count": plan["scoring_context_token_count"],
        "sequence_level_model_evaluations":
            plan["sequence_level_model_evaluations"],
        "reuses_row_id": plan.get("reuses_row_id"),
        "tie_break_order": list(order),
    }


def reuse_for_s3(s2_plan, s2_logits, counters=None):
    """Build and score the S3 row from the exact S2 discriminant-position vector."""
    plan = dict(s2_plan)
    plan["profile"] = "S3"
    plan["sequence_level_model_evaluations"] = 0
    plan["reuses_row_id"] = s2_plan["row_id"]
    plan["row_id"] = "%s#s3" % s2_plan["row_id"]
    validate_scoring_plan(plan)
    return score_from_logits(plan, s2_logits, counters=counters)


# ---------------------------------------------------------------------------
# The execution shell. Never invoked by the calibration session.
# ---------------------------------------------------------------------------

def run(authorization=None, counters=None):
    """Execute the P0-R1 model pilot. Successor session only.

    The calibration session is forbidden to construct a tokenizer, download a
    checkpoint, allocate a GPU or begin the model pilot, so this shell refuses to
    start unless it is handed a live one-shot authorization *and* the registered
    replay gate has already passed in the same session.
    """
    del counters
    if not authorization or not authorization.get(
            "p0_r1_pilot_execution_authorized"):
        raise ExecutionRefused(
            "the P0-R1 model pilot requires the narrow, not-yet-consumed "
            "p0_r1_pilot_execution_authorized flag recorded in the P0-R1 "
            "package, and it may only run in the successor session after the "
            "registered replay gate passes")
    if not authorization.get("replay_gate_passed_in_this_session"):
        raise ExecutionRefused(
            "the registered replay-only factorization gate must pass first; "
            "if replay fails, publish a registered stop and perform no model "
            "operation")
    raise ExecutionRefused(
        "the model pilot is registered but not implemented in the calibration "
        "session; the successor session supplies the container entry point "
        "recorded in studies/study3/pilot/p0_r1/container/")


def new_counters():
    return P0R1Counters()


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
