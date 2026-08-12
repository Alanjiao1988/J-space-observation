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

import hashlib
import json
import os
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))
sys.path.insert(0, P0_R1_DIR)

import p0_r1_execution_lock as LOCK  # noqa: E402
import p0_r1_factorization as FACT  # noqa: E402
from p0_r1_counters import P0R1Counters, SMOKE_EXACT  # noqa: E402

SCHEMA_VERSION = "study3-p0-r1-scored-row-v1"

RESTRICTED_ARGMAX_PROFILES = ("S1", "S2", "S3")

STATE_COMPLETE = "STUDY3_P0_R1_COMPLETE_MECHANICALLY_FEASIBLE"
STATE_STOPPED_ON_SMOKE = "STUDY3_P0_R1_STOPPED_ON_MODEL_SMOKE_MECHANICAL_FAILURE"

#: The frozen corpus is reused exactly; no row, member or hash is ever changed.
CORPUS_PATH = "studies/study3/pilot/p0/corpus/p0_corpus.json"

#: The K2 tuple class carries the exact smoke; the two K3 classes are extension.
SMOKE_TUPLE_CLASS = "K2-none-0"

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

def validate_execution_authorization(authorization, root=None):
    """Refuse unless a valid, unconsumed lock and a byte-valid pass receipt agree.

    A prose log line is not authorization. Section 6 requires the executor to
    receive an execution lock that is still unconsumed *and* a replay-pass
    receipt produced by the same authorized attempt, and to check that the
    receipt, lock, image digest, commit, tree, hashes and attempt ID all agree.
    """
    if not authorization or not isinstance(authorization, dict):
        raise ExecutionRefused(
            "the P0-R1 model pilot requires an execution authorization mapping "
            "carrying the execution lock and the replay-pass receipt")
    if not authorization.get("p0_r1_pilot_execution_authorized"):
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

    lock = authorization.get("execution_lock")
    receipt = authorization.get("replay_receipt")
    if not isinstance(lock, dict) or not isinstance(receipt, dict):
        raise ExecutionRefused(
            "the model pilot requires the execution lock and the replay-pass "
            "receipt as documents; a prose log line is not authorization")

    LOCK.validate_lock(lock, root=root)
    if lock["legal_status"].get("p0_r1_pilot_execution_consumed"):
        raise ExecutionRefused(
            "the execution lock is already consumed; the P0-R1 envelope is "
            "one-shot and is never re-armed")

    if receipt.get("schema_version") != "study3-p0-r1-replay-gate-receipt-v1":
        raise ExecutionRefused("the replay receipt has an unknown schema")
    if not receipt.get("passed") or not receipt.get("authorizes_model_pilot"):
        raise ExecutionRefused(
            "the replay receipt does not record a pass; a replay failure "
            "authorizes no model operation")
    if receipt.get("state") != LOCK.STATE_REPLAY_PASSED:
        raise ExecutionRefused(
            "the replay receipt records state %r, not %r"
            % (receipt.get("state"), LOCK.STATE_REPLAY_PASSED))
    for field, expected in (
            ("image_digest", lock["image"]["digest"]),
            ("executable_code_commit", lock["executable_code"]["commit"]),
            ("executable_code_tree", lock["executable_code"]["tree"])):
        if receipt.get(field) != expected:
            raise ExecutionRefused(
                "the replay receipt %s %r does not agree with the execution "
                "lock %r" % (field, receipt.get(field), expected))
    identity = LOCK.lock_identity(root=root)
    if receipt.get("execution_lock", {}).get("sha256") != identity["sha256"]:
        raise ExecutionRefused(
            "the replay receipt was produced against a different execution lock")
    if receipt.get("model_operations_performed") or receipt.get("gpu_allocated") \
            or receipt.get("tokenizer_encodes") \
            or receipt.get("tokenizer_constructions"):
        raise ExecutionRefused(
            "the replay receipt records a tokenizer, model or GPU operation; "
            "the replay gate is replay-only")
    attempt = authorization.get("attempt_id")
    if not attempt or attempt != receipt.get("attempt_id"):
        raise ExecutionRefused(
            "the model pilot attempt id %r does not match the replay attempt "
            "id %r; the receipt must come from the same authorized attempt"
            % (attempt, receipt.get("attempt_id")))
    return {"lock": lock, "receipt": receipt, "attempt_id": attempt}


def validate_infrastructure_retry(previous_attempt_counters):
    """One infrastructure retry, and only against a proven zero-operation attempt."""
    if not isinstance(previous_attempt_counters, dict):
        raise ExecutionRefused(
            "an infrastructure retry requires the signed counter snapshot of "
            "the failed attempt")
    for name in ("tokenizer_construction_events", "tokenizer_encoded_sequences",
                 "distinct_checkpoint_identities_downloaded",
                 "model_weight_loads", "non_generative_prefill_evaluations",
                 "s4_prefill_evaluations", "s4_incremental_decode_evaluations",
                 "s4_generation_calls", "total_scored_rows",
                 "gpu_jobs_performing_a_model_operation"):
        value = previous_attempt_counters.get(name)
        if value is None:
            raise ExecutionRefused(
                "the signed retry receipt does not carry %s; a missing counter "
                "is not a zero-operation proof" % name)
        if value != 0:
            raise ExecutionRefused(
                "the failed attempt recorded %s=%d; it is not a zero-operation "
                "retry and no output-conditioned retry is authorized"
                % (name, value))
    return True


class SmokeBoundary(object):
    """Enforce the 60-prefill smoke before any extension or S4 generation.

    Section 6 requires the *code* to enforce the boundary, not a post-hoc
    inspection of smoke rows after the full run. Every sequence-level operation
    is admitted through :meth:`admit`, which refuses an extension or S4
    operation until the exact smoke allocation has completed and passed.
    """

    def __init__(self, counters, smoke_prefills=None):
        self._counters = counters
        self._smoke_target = (SMOKE_EXACT["non_generative_prefill_evaluations"]
                              if smoke_prefills is None else smoke_prefills)
        self._smoke_prefills = 0
        self._smoke_closed = False
        self._smoke_passed = False

    @property
    def smoke_prefills(self):
        return self._smoke_prefills

    @property
    def smoke_closed(self):
        return self._smoke_closed

    @property
    def smoke_passed(self):
        return self._smoke_passed

    def admit(self, phase):
        """Admit one sequence-level operation in ``phase``. Fail closed."""
        if phase == "smoke":
            if self._smoke_closed:
                raise ScoringDefect(
                    "the K2 smoke allocation is exact and already closed at %d "
                    "prefills; it may not be extended after observation"
                    % self._smoke_prefills)
            if self._smoke_prefills >= self._smoke_target:
                raise ScoringDefect(
                    "the K2 smoke allocation is exactly %d non-generative "
                    "prefill evaluations" % self._smoke_target)
            self._smoke_prefills += 1
            return "smoke"
        if phase in ("extension", "s4"):
            if not self._smoke_closed:
                raise ScoringDefect(
                    "the %d-prefill mechanical smoke must complete and pass "
                    "before any extension prefill or S4 generation; observed "
                    "%d of %d smoke prefills"
                    % (self._smoke_target, self._smoke_prefills,
                       self._smoke_target))
            if not self._smoke_passed:
                raise ScoringDefect(
                    "the mechanical smoke gate did not pass; no extension "
                    "prefill or S4 generation is authorized")
            return phase
        raise ScoringDefect("unregistered execution phase %r" % phase)

    def close_smoke(self, passed):
        """Close the smoke phase with its mechanical verdict."""
        if self._smoke_closed:
            raise ScoringDefect("the smoke phase is already closed")
        if self._smoke_prefills != self._smoke_target:
            raise ScoringDefect(
                "the smoke allocation is exact: %d prefills were registered but "
                "%d were executed"
                % (self._smoke_target, self._smoke_prefills))
        self._smoke_closed = True
        self._smoke_passed = bool(passed)
        return self._smoke_passed


class GpuResidency(object):
    """At most one checkpoint on the GPU at a time, at most three weight loads.

    Section 6 permits retaining already-loaded fp16 checkpoints in CPU memory so
    that all three role-smoke slices complete before extension without a second
    load. That schedule is recorded explicitly here: a checkpoint *moves*
    between CPU and GPU, and a move is never a load.
    """

    def __init__(self, counters):
        self._counters = counters
        self._resident = None
        self._loaded = {}
        self._moves = 0

    @property
    def resident(self):
        return self._resident

    @property
    def moves(self):
        return self._moves

    def load(self, role, loader):
        """Load a checkpoint exactly once. A reload after observation is refused."""
        if role in self._loaded:
            raise ScoringDefect(
                "checkpoint %s is already loaded; reloading a checkpoint after "
                "observing smoke is forbidden and would exceed the registered "
                "three model-weight loads" % role)
        self._counters.add("model_weight_loads", 1)
        self._loaded[role] = loader()
        return self._loaded[role]

    def to_gpu(self, role, device):
        """Make ``role`` the single resident checkpoint on ``device``."""
        if role not in self._loaded:
            raise ScoringDefect("checkpoint %s was never loaded" % role)
        if self._resident == role:
            return self._loaded[role]
        if self._resident is not None:
            self._loaded[self._resident] = self._loaded[self._resident].to("cpu")
            self._moves += 1
        self._loaded[role] = self._loaded[role].to(device)
        self._resident = role
        self._moves += 1
        return self._loaded[role]

    def evict(self):
        if self._resident is not None:
            self._loaded[self._resident] = self._loaded[self._resident].to("cpu")
            self._moves += 1
            self._resident = None


def load_corpus(root=None):
    """Read the frozen, byte-verified P0 corpus. It is never edited or extended."""
    return FACT.load_immutable(CORPUS_PATH, root=root)


def build_execution_plan(corpus, roles, factorization=None, root=None):
    """Split the frozen corpus into the exact smoke, the extension and S4.

    The allocation is derived from the corpus rather than restated: the ``K2``
    tuple class carries the exact 60-prefill smoke, the two ``K3`` classes carry
    the bounded extension, and ``S4`` is diagnostic only. ``S3`` never appears
    here because it is a scoring rule over the captured ``S2`` vector, not a new
    surface.
    """
    if factorization is None:
        registry = FACT._load_registry(root=root)
        factorization = FACT.gate(registry, root=root)
    by_role = {entry["role"]: entry for entry in factorization["roles"]}
    published = FACT.load_immutable(FACT.RESULT_PATH, root=root)
    s1_published = published["candidate_token_eligibility"]

    plan = {"smoke": {}, "extension": {}, "s4": {}}
    for role in roles:
        plan["smoke"][role] = []
        plan["extension"][role] = []
        plan["s4"][role] = []
        derived = by_role[role]
        digits = [" %s" % digit for digit in FACT.REGISTERED_DIGITS]
        for row in corpus["rows"]:
            profile = row["profile"]
            if profile == "S3":
                continue
            smoke = row["tuple_class_id"] == SMOKE_TUPLE_CLASS
            for member in row["members"]:
                entry = {
                    "row_id": "%s/%s/%s" % (row["row_id"], role,
                                            member["role_in_pair"]),
                    "corpus_row_id": row["row_id"],
                    "profile": profile,
                    "role": role,
                    "contrast": row["contrast"],
                    "tuple_class_id": row["tuple_class_id"],
                    "rendering": member["rendering"],
                    "role_in_pair": member["role_in_pair"],
                    "prompt": member["prompt"],
                    "prompt_sha256": member["prompt_sha256"],
                    "ground_truth": row["ground_truth"],
                }
                if profile == "S1":
                    alphabet = member["nuisance_state"]["label_alphabet"]
                    body = s1_published[role]["s1_by_alphabet"][alphabet]
                    entry["candidate_surfaces"] = list(body["surfaces"])
                    entry["candidate_token_ids"] = [
                        list(ids) for ids in body["token_ids"]]
                    entry["tie_break_order"] = list(body["surfaces"])
                    entry["label_alphabet"] = alphabet
                elif profile == "S2":
                    entry["candidate_surfaces"] = list(digits)
                    entry["candidate_token_ids"] = [
                        [derived["common_prefix_token"], token]
                        for token in derived["discriminant_token_ids"]]
                    entry["common_prefix_token"] = derived["common_prefix_token"]
                    entry["tie_break_order"] = list(digits)
                    entry["s3_reuse"] = True
                if profile == "S4":
                    plan["s4"][role].append(entry)
                elif smoke:
                    plan["smoke"][role].append(entry)
                else:
                    plan["extension"][role].append(entry)
    return plan


def write_pilot_artifacts(out_dir, state, attempt_id, lock, scored_rows,
                          s4_completions, exceptions, counters, resources,
                          summary, smoke_passed):
    """Write every canonical P0-R1 artifact into the writable runtime namespace."""
    os.makedirs(out_dir, exist_ok=True)
    result = {
        "schema_version": "study3-p0-r1-model-pilot-result-v1",
        "document_class": "study3_p0_r1_model_pilot_result",
        "stage": "P0-R1-MODEL-PILOT",
        "state": state,
        "attempt_id": attempt_id,
        "image_digest": lock["image"]["digest"],
        "executable_code_commit": lock["executable_code"]["commit"],
        "roles": lock["roles"],
        "smoke_passed": smoke_passed,
        "scored_rows": scored_rows,
        "s4_completions": s4_completions,
        "exceptions": exceptions,
        "counters": counters,
        "resources": resources,
        "summary": summary,
        "evidence_status": (
            "a methods-feasibility continuation observation. It is not Study 3 "
            "evidence, selects no interface, sets no threshold, estimates no "
            "confirmatory effect and answers no research question."),
    }
    receipt = {
        "schema_version": "study3-p0-r1-model-pilot-receipt-v1",
        "document_class": "study3_p0_r1_model_pilot_receipt",
        "stage": "P0-R1-MODEL-PILOT",
        "state": state,
        "attempt_id": attempt_id,
        "image_digest": lock["image"]["digest"],
        "counters": counters,
        "smoke_passed": smoke_passed,
        "scored_row_count": len(scored_rows),
        "exception_count": len(exceptions),
    }
    disposition = "\n".join([
        "# Stage P0-R1 model pilot: disposition",
        "",
        "> **Emitted terminal state:** `%s`" % state,
        ">",
        "> Published exactly as emitted. Every valid row, raw S4 completion,",
        "> exception, partial result and cumulative counter is retained.",
        "",
        "| field | value |",
        "| --- | --- |",
        "| attempt id | `%s` |" % attempt_id,
        "| image digest | `%s` |" % lock["image"]["digest"],
        "| smoke passed | `%s` |" % smoke_passed,
        "| scored rows | `%d` |" % len(scored_rows),
        "| exceptions | `%d` |" % len(exceptions),
        "",
        "Correctness, accuracy, diversity and discordance are descriptive only",
        "and were not smoke criteria.",
        "",
    ])
    written = []
    for name, payload in (
            ("p0_r1_model_pilot_result.json", dumps(result).encode("utf-8")),
            ("p0_r1_model_pilot_receipt.json", dumps(receipt).encode("utf-8")),
            ("p0_r1_model_pilot_counters.json", dumps(counters).encode("utf-8")),
            ("P0_R1_MODEL_PILOT_DISPOSITION.md", disposition.encode("utf-8"))):
        path = os.path.join(out_dir, name)
        with open(path, "wb") as handle:
            handle.write(payload)
        written.append({
            "name": name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    return {
        "state": state,
        "attempt_id": attempt_id,
        "result": result,
        "receipt": receipt,
        "artifacts": written,
        "out_dir": out_dir,
    }


def run(authorization=None, counters=None, out_dir=None, root=None,
        device=None, corpus_rows=None):
    """Execute the P0-R1 bounded model pilot. Successor execution session only.

    This is a real executor, not a refusal shell and not a synthetic-logit
    harness. It refuses unless :func:`validate_execution_authorization` accepts a
    valid unconsumed execution lock together with a byte-valid replay-pass
    receipt from the same authorized attempt, and only then does it reach the
    execution shell.

    That shell lives in the separate ``execution`` subpackage. The separation is
    deliberate and is itself a registered guarantee: this module, the replay and
    registration path, never imports or names a model or tokenizer library, so it
    stays importable and testable with no such library present.
    """
    authorized = validate_execution_authorization(authorization, root=root)
    counters = counters if counters is not None else P0R1Counters()
    if not out_dir:
        raise ExecutionRefused(
            "the model pilot requires a writable runtime result directory")

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "p0_r1_model_execution",
        os.path.join(P0_R1_DIR, "execution", "p0_r1_model_execution.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute(authorized, counters, out_dir, root=root,
                          device=device, corpus_rows=corpus_rows)


def new_counters():
    return P0R1Counters()


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
