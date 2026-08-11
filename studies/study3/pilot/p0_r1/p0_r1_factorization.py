"""Replay-only tokenizer factorization verifier for Study 3 P0-R1.

Authority: ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md`` sections
3.2, 3.3, 6 and 7.

This module **derives** the first-discriminative-token factorization from the
immutable published P0-T artifacts. It never transcribes the common-prefix or
discriminant token IDs as an assumption, and it performs **zero** tokenizer
encodes, zero tokenizer constructions, zero checkpoint downloads, zero weight
loads and zero model operations. It deliberately imports no tokenizer library,
so a stray encode would be an ``ImportError`` rather than a silent operation.

Two immutable sources are read, both verified by byte length and SHA-256 before
use:

* ``studies/study3/pilot/p0/results/p0-t/p0_tokenizer_gate_result.json`` --
  the published P0-T result, which carries the candidate-surface encodes and
  4,902 member token-ID sequences; and
* ``studies/study3/pilot/p0/corpus/p0_corpus.json`` -- the frozen 35-cell /
  70-member P0 corpus, which carries the exact prompt bytes and their SHA-256.

The token identity of the common prefix is not asserted from a constant. It is
recovered by solving, over the published (plaintext, token-ID) pairs, for the
byte string each token contributes. The solution is required to be *unique* for
the common-prefix token and for each of the ten discriminant tokens; a token
whose byte string is not uniquely determined by the published evidence cannot
satisfy section 3.2 and is reported as an unresolved ambiguity rather than
guessed.

Usage::

    python p0_r1_factorization.py --check
    python p0_r1_factorization.py --emit <path>
"""

import argparse
import hashlib
import json
import os
import sys

P0_R1_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(P0_R1_DIR, "..", "..", "..", ".."))

SCHEMA_VERSION = "study3-p0-r1-factorization-replay-v1"

# Immutable published sources. Section 9 forbids editing any byte under
# ``studies/study3/pilot/p0/``; this module only ever reads them.
IMMUTABLE_SOURCES = {
    "studies/study3/pilot/p0/results/p0-t/p0_tokenizer_gate_result.json": {
        "bytes": 5820022,
        "sha256":
            "9603b61165bc0b405fe8eb6103a56e646ceb2e254a33e0eba2ee2d035f03a85f",
        "role": "the published P0-T tokenizer gate result",
    },
    "studies/study3/pilot/p0/results/p0-t/p0_tokenizer_gate_receipt.json": {
        "bytes": 7934,
        "sha256":
            "0b28fbe6f633cc5a6d0664588fb685065d15ab1c301a1540d1e12f7c7b69e737",
        "role": "the published P0-T receipt",
    },
    "studies/study3/pilot/p0/results/p0-t/P0_T_DISPOSITION.md": {
        "bytes": 7850,
        "sha256":
            "9d6a6508383ebd5f6e4f0bb97a5b75de282da3cf28afba837b923cd1a6ec66eb",
        "role": "the published P0-T disposition",
    },
    "studies/study3/pilot/p0/corpus/p0_corpus.json": {
        "bytes": 69781,
        "sha256":
            "5343019a334ce666bb3e7f7f57d87181550aa90fad4815ba51a7ba3f571e1c6c",
        "role": "the frozen 35-cell / 70-member P0 corpus",
    },
}

RESULT_PATH = "studies/study3/pilot/p0/results/p0-t/p0_tokenizer_gate_result.json"
CORPUS_PATH = "studies/study3/pilot/p0/corpus/p0_corpus.json"

# The registered S2/S3 answer domain, in registered order. The surfaces are read
# back from the published result and from the v0.6 registry and must agree; this
# tuple only fixes the order in which the digits are registered.
REGISTERED_DIGITS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")

# The registered leading whitespace of every S2/S3 candidate surface.
REGISTERED_LEADING_WHITESPACE = "\u0020"

# No registered prompt or candidate piece is longer than this. The bound only
# limits the search; a solution that needed a longer piece would be reported as
# infeasible rather than silently truncated.
MAX_TOKEN_PIECE = 48

ROLES = ("RI", "RL", "RT")


class FactorizationDefect(Exception):
    """A fail-closed replay stop. No model operation follows one of these."""


# ---------------------------------------------------------------------------
# Immutable source loading.
# ---------------------------------------------------------------------------

def source_identity(repo_relative_path, root=None):
    path = os.path.join(root or REPO_ROOT, *repo_relative_path.split("/"))
    if not os.path.exists(path):
        raise FactorizationDefect(
            "the immutable source %s is missing" % repo_relative_path)
    with open(path, "rb") as handle:
        raw = handle.read()
    return {
        "path": repo_relative_path,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def load_immutable(repo_relative_path, root=None):
    """Read one registered immutable source after verifying its exact bytes."""
    expected = IMMUTABLE_SOURCES.get(repo_relative_path)
    if expected is None:
        raise FactorizationDefect(
            "%s is not a registered immutable source" % repo_relative_path)
    identity = source_identity(repo_relative_path, root=root)
    if identity["bytes"] != expected["bytes"]:
        raise FactorizationDefect(
            "%s is %d bytes, not the registered %d; the immutable P0-T evidence "
            "has been altered" % (repo_relative_path, identity["bytes"],
                                  expected["bytes"]))
    if identity["sha256"] != expected["sha256"]:
        raise FactorizationDefect(
            "%s has sha256 %s, not the registered %s; the immutable P0-T "
            "evidence has been altered"
            % (repo_relative_path, identity["sha256"], expected["sha256"]))
    path = os.path.join(root or REPO_ROOT, *repo_relative_path.split("/"))
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def verify_immutable_sources(root=None):
    """Verify every registered immutable source byte-for-byte."""
    verified = []
    for repo_relative_path in sorted(IMMUTABLE_SOURCES):
        expected = IMMUTABLE_SOURCES[repo_relative_path]
        identity = source_identity(repo_relative_path, root=root)
        if identity["bytes"] != expected["bytes"] \
                or identity["sha256"] != expected["sha256"]:
            raise FactorizationDefect(
                "%s does not reproduce its registered identity"
                % repo_relative_path)
        entry = dict(identity)
        entry["role"] = expected["role"]
        verified.append(entry)
    return verified


# ---------------------------------------------------------------------------
# Binding published token-ID sequences to known plaintext.
# ---------------------------------------------------------------------------

def corpus_prompts_by_hash(corpus):
    """Map SHA-256 to the exact frozen prompt bytes."""
    by_hash = {}
    for row in corpus["rows"]:
        for member in row.get("members", []):
            prompt = member["prompt"]
            digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            if digest != member["prompt_sha256"]:
                raise FactorizationDefect(
                    "frozen corpus row %s does not reproduce its own recorded "
                    "prompt hash" % row.get("row_id"))
            by_hash[digest] = prompt
    return by_hash


def bound_sequences(result, by_hash, role):
    """Published (plaintext, token IDs) pairs for one role.

    Only the frozen-corpus records are bound, because the corpus is the sole
    immutable source of the exact prompt bytes. Every bound pair is checked
    against the published byte length as well as the published hash.
    """
    pairs = []
    for record in result["records"]:
        if record.get("structural_absence"):
            continue
        if record.get("role") != role or record.get("source") != "frozen_corpus":
            continue
        for member in record["members"]:
            text = by_hash.get(member["prompt_sha256"])
            if text is None:
                raise FactorizationDefect(
                    "published frozen-corpus record %s carries a prompt hash "
                    "absent from the frozen corpus" % record.get("row_id"))
            if len(text.encode("utf-8")) != member["prompt_bytes"]:
                raise FactorizationDefect(
                    "published record %s disagrees with the frozen corpus on the "
                    "prompt byte length" % record.get("row_id"))
            if len(member["token_ids"]) != member["token_count"]:
                raise FactorizationDefect(
                    "published record %s disagrees with its own token count"
                    % record.get("row_id"))
            pairs.append((text, list(member["token_ids"])))
    if not pairs:
        raise FactorizationDefect(
            "no published frozen-corpus sequence is bound for role %s" % role)
    return pairs


# ---------------------------------------------------------------------------
# Solving for the byte string each token contributes.
# ---------------------------------------------------------------------------

def _feasible_offsets(text, ids, candidates):
    """Forward/backward reachable character offsets for each token position."""
    n, length = len(ids), len(text)
    forward = [set() for _ in range(n + 1)]
    forward[0].add(0)
    for index in range(n):
        allowed = candidates.get(ids[index])
        for start in forward[index]:
            if allowed is None:
                upper = min(MAX_TOKEN_PIECE, length - start)
                for size in range(1, upper + 1):
                    forward[index + 1].add(start + size)
            else:
                for piece in allowed:
                    if text.startswith(piece, start):
                        forward[index + 1].add(start + len(piece))
    backward = [set() for _ in range(n + 1)]
    backward[n].add(length)
    for index in range(n - 1, -1, -1):
        allowed = candidates.get(ids[index])
        for end in backward[index + 1]:
            if allowed is None:
                upper = min(MAX_TOKEN_PIECE, end)
                for size in range(1, upper + 1):
                    backward[index].add(end - size)
            else:
                for piece in allowed:
                    start = end - len(piece)
                    if start >= 0 and text.startswith(piece, start):
                        backward[index].add(start)
    return [forward[index] & backward[index] for index in range(n + 1)]


def solve_token_pieces(pairs, max_rounds=12):
    """Recover the byte string each token contributes, from published evidence.

    Returns a mapping from token ID to the set of byte strings still consistent
    with every published sequence. A token whose set has exactly one member is
    uniquely determined by the immutable evidence.
    """
    candidates = {}
    for _ in range(max_rounds):
        narrowed = {}
        for text, ids in pairs:
            reachable = _feasible_offsets(text, ids, candidates)
            if not reachable[len(ids)] or not reachable[0]:
                raise FactorizationDefect(
                    "a published token-ID sequence admits no segmentation of its "
                    "own registered prompt bytes; the published evidence is "
                    "internally inconsistent")
            for index, token in enumerate(ids):
                allowed = candidates.get(token)
                pieces = set()
                for start in reachable[index]:
                    for end in reachable[index + 1]:
                        if end <= start or (end - start) > MAX_TOKEN_PIECE:
                            continue
                        piece = text[start:end]
                        if allowed is None or piece in allowed:
                            pieces.add(piece)
                if not pieces:
                    raise FactorizationDefect(
                        "token %d has no byte string consistent with the "
                        "published evidence" % token)
                previous = narrowed.get(token)
                narrowed[token] = pieces if previous is None else previous & pieces
        changed = False
        for token, pieces in narrowed.items():
            if not pieces:
                raise FactorizationDefect(
                    "token %d has no byte string consistent with every published "
                    "sequence" % token)
            if candidates.get(token) != pieces:
                candidates[token] = pieces
                changed = True
        if not changed:
            break
    return candidates


def resolved_piece(candidates, token):
    """The byte string of a token, only when the evidence determines it uniquely."""
    pieces = candidates.get(token)
    if pieces is None:
        raise FactorizationDefect(
            "token %d never appears in the published evidence, so its byte "
            "string cannot be derived" % token)
    if len(pieces) != 1:
        raise FactorizationDefect(
            "token %d is not uniquely determined by the published evidence; %d "
            "byte strings remain consistent" % (token, len(pieces)))
    return next(iter(pieces))


# ---------------------------------------------------------------------------
# The five conditions of section 3.2.
# ---------------------------------------------------------------------------

def published_candidate_encodes(result, role):
    entry = result.get("candidate_token_eligibility", {}).get(role)
    if entry is None:
        raise FactorizationDefect(
            "the published P0-T result carries no candidate encodes for %s" % role)
    s2 = entry.get("s2")
    if not s2 or "surfaces" not in s2 or "token_ids" not in s2:
        raise FactorizationDefect(
            "the published P0-T result carries no S2 candidate encode for %s"
            % role)
    surfaces = list(s2["surfaces"])
    token_ids = [list(ids) for ids in s2["token_ids"]]
    if len(surfaces) != len(token_ids):
        raise FactorizationDefect(
            "the published S2 candidate encode for %s is misaligned" % role)
    return surfaces, token_ids


def derive_role_factorization(result, candidates, role, registered_surfaces):
    """Derive and verify the five conditions of section 3.2 for one role."""
    surfaces, token_ids = published_candidate_encodes(result, role)
    conditions = {}
    reasons = []

    # The published candidate surfaces must be exactly the registered ones, in
    # the registered order, byte for byte.
    if surfaces != list(registered_surfaces):
        raise FactorizationDefect(
            "the published S2 candidate surfaces for %s are not the registered "
            "surfaces in registered order" % role)
    if len(surfaces) != len(REGISTERED_DIGITS):
        raise FactorizationDefect(
            "the registered S2 candidate set is not ten surfaces")
    for digit, surface in zip(REGISTERED_DIGITS, surfaces):
        if surface != REGISTERED_LEADING_WHITESPACE + digit:
            raise FactorizationDefect(
                "registered candidate surface %r is not one U+0020 followed by "
                "the registered digit %r" % (surface, digit))

    # Condition 1: every complete candidate is exactly two tokens.
    lengths = sorted({len(ids) for ids in token_ids})
    conditions["every_complete_candidate_is_exactly_two_tokens"] = (
        lengths == [2])
    if lengths != [2]:
        reasons.append(
            "a complete S2/S3 candidate is not exactly two tokens: observed "
            "token-sequence lengths %s" % lengths)

    # Condition 2: the first token is identical for all ten candidates.
    first_tokens = sorted({ids[0] for ids in token_ids if ids})
    conditions["the_first_token_is_identical_for_all_ten_candidates"] = (
        len(first_tokens) == 1)
    if len(first_tokens) != 1:
        reasons.append(
            "the ten complete candidates do not share one first token: observed "
            "%s" % first_tokens)

    if reasons:
        return {
            "role": role,
            "eligible": False,
            "reasons": reasons,
            "conditions": conditions,
        }

    common_prefix_token = first_tokens[0]
    discriminant_token_ids = [ids[1] for ids in token_ids]

    # Condition 3: the common token decodes byte-exactly to the registered
    # leading U+0020. The byte string is derived from the published evidence.
    prefix_piece = resolved_piece(candidates, common_prefix_token)
    prefix_ok = prefix_piece == REGISTERED_LEADING_WHITESPACE
    conditions[
        "the_common_token_decodes_byte_exactly_to_one_registered_u0020"] = \
        prefix_ok
    if not prefix_ok:
        reasons.append(
            "the common-prefix token %d carries %r, not exactly one registered "
            "U+0020" % (common_prefix_token, prefix_piece))

    # Condition 4: the second token IDs are pairwise distinct and map
    # byte-exactly to 0 through 9 in registered order.
    distinct = len(set(discriminant_token_ids)) == len(discriminant_token_ids)
    digit_pieces = []
    mapped = True
    for digit, token in zip(REGISTERED_DIGITS, discriminant_token_ids):
        piece = resolved_piece(candidates, token)
        digit_pieces.append(piece)
        if piece != digit:
            mapped = False
    conditions["the_second_token_ids_are_pairwise_distinct"] = distinct
    conditions[
        "the_second_token_ids_map_byte_exactly_to_0_through_9_in_order"] = mapped
    if not distinct:
        reasons.append(
            "two discriminant token IDs collide: %s" % discriminant_token_ids)
    if not mapped:
        reasons.append(
            "a discriminant token does not carry its registered digit: derived "
            "%s against registered %s"
            % (digit_pieces, list(REGISTERED_DIGITS)))

    # Condition 4b: the complete candidate surface must be reproduced exactly by
    # the derived factorization, so a digit token can never map to the wrong
    # complete candidate surface.
    reconstructed = [prefix_piece + piece for piece in digit_pieces]
    surfaces_ok = reconstructed == list(surfaces)
    conditions[
        "the_factorization_reproduces_every_complete_candidate_surface"] = \
        surfaces_ok
    if not surfaces_ok:
        reasons.append(
            "the derived factorization does not reproduce the registered "
            "candidate surfaces: %s against %s" % (reconstructed, list(surfaces)))

    # Condition 5: no BOS, EOS, chat template, normalization, padding,
    # truncation or implicit whitespace transformation participates.
    structural = _structural_purity(result, role, candidates,
                                    common_prefix_token)
    conditions.update(structural["conditions"])
    reasons.extend(structural["reasons"])

    return {
        "role": role,
        "eligible": not reasons,
        "reasons": reasons,
        "conditions": conditions,
        "common_prefix_token": common_prefix_token,
        "common_prefix_bytes": prefix_piece,
        "discriminant_token_ids": discriminant_token_ids,
        "discriminant_bytes": digit_pieces,
        "complete_candidate_token_ids": token_ids,
        "registered_candidate_surfaces": list(surfaces),
    }


def _structural_purity(result, role, candidates, common_prefix_token):
    """Derive that no special token or normalization participates, from evidence."""
    conditions = {}
    reasons = []
    sequences = []
    for record in result["records"]:
        if record.get("structural_absence") or record.get("role") != role:
            continue
        for member in record["members"]:
            sequences.append(member)
    if not sequences:
        raise FactorizationDefect(
            "the published result carries no member encode for %s" % role)

    # A BOS policy would put one constant token at position 0 of every sequence.
    first_tokens = {member["token_ids"][0] for member in sequences
                    if member["token_ids"]}
    last_tokens = {member["token_ids"][-1] for member in sequences
                   if member["token_ids"]}
    conditions["no_constant_sequence_initial_token_across_distinct_prompts"] = (
        len(first_tokens) > 1)
    if len(first_tokens) <= 1:
        reasons.append(
            "every published sequence for %s begins with the same token, which "
            "is the signature of a BOS or chat-template prefix" % role)

    # Every registered prompt ends with the registered answer cue, so a constant
    # final token is expected and is *not* evidence of EOS. An EOS policy would
    # instead show a final token that never occurs anywhere else.
    trailing = sorted(last_tokens)
    interior = set()
    for member in sequences:
        interior.update(member["token_ids"][:-1])
    eos_like = [token for token in trailing if token not in interior]
    conditions["no_sequence_final_token_absent_from_every_interior_position"] = (
        not eos_like)
    if eos_like:
        reasons.append(
            "token(s) %s appear only in final position for %s, which is the "
            "signature of an EOS policy" % (eos_like, role))

    # The common prefix must be a separate token that the registered prompt does
    # not already end with, otherwise the leading U+0020 would be duplicated.
    ends_with_prefix = [member for member in sequences
                        if member["token_ids"]
                        and member["token_ids"][-1] == common_prefix_token]
    conditions["no_registered_prompt_ends_with_the_common_prefix_token"] = (
        not ends_with_prefix)
    if ends_with_prefix:
        reasons.append(
            "a registered prompt for %s already ends with the common-prefix "
            "token, so appending it would duplicate the registered U+0020" % role)

    # Padding or truncation would break the byte accounting. Every published
    # sequence must admit a total piece length that contains its recorded prompt
    # byte length.
    unresolved = 0
    inconsistent = 0
    for member in sequences:
        low = high = 0
        for token in member["token_ids"]:
            pieces = candidates.get(token)
            if pieces is None:
                unresolved += 1
                low += 1
                high += MAX_TOKEN_PIECE
                continue
            sizes = [len(piece.encode("utf-8")) for piece in pieces]
            low += min(sizes)
            high += max(sizes)
        if not low <= member["prompt_bytes"] <= high:
            inconsistent += 1
    conditions["every_published_sequence_reconciles_with_its_prompt_bytes"] = (
        inconsistent == 0)
    if inconsistent:
        reasons.append(
            "%d published sequences for %s cannot reconcile their token "
            "segmentation with their recorded prompt byte length, which is the "
            "signature of padding, truncation or normalization"
            % (inconsistent, role))
    conditions["unresolved_token_occurrences"] = unresolved
    return {"conditions": conditions, "reasons": reasons}


# ---------------------------------------------------------------------------
# The exact ranking-equivalence identity of section 3.3.
# ---------------------------------------------------------------------------

def equivalence_identity():
    """The registered, exact factor-cancellation identity of section 3.3."""
    return {
        "identity": "P(u, v_d | x) = P(u | x) * P(v_d | x, u)",
        "consequence": "argmax_d P(u, v_d | x) = argmax_d P(v_d | x, u)",
        "why_exact": (
            "P(u | x) does not depend on d, so it is a strictly positive common "
            "factor of all ten complete-candidate probabilities and cancels from "
            "the ranking. This is an exact factor cancellation, not an "
            "approximation"),
        "valid_because": [
            "the registered decision statistic is a deterministic argmax over a "
            "closed ten-member candidate set",
            "all ten candidates have the same two-token structure",
            "all ten candidates share the identical common prefix token u",
            "the registered digit-order tie break is preserved unchanged",
        ],
        "does_not_extend_to": [
            "arbitrary multi-token candidates",
            "candidates of unequal length",
            "candidates without a common prefix",
            "summed or length-normalised log probabilities",
            "free generation",
            "any tokenizer that is not separately pinned and verified",
        ],
        "tie_break_order": (
            "ascending mod-10 residue order 0, 1, 2, ..., 9, unchanged from the "
            "registered v0.5 order"),
    }


def assert_ranking_equivalence(prefix_probability, conditional_probabilities,
                               tie_break_order=None):
    """Mechanically assert the section 3.3 identity for one prompt.

    ``prefix_probability`` is P(u | x); ``conditional_probabilities`` maps each
    registered digit to P(v_d | x, u). The joint P(u, v_d | x) is formed by the
    registered identity, and the restricted argmax over the joint must equal the
    restricted argmax over the conditional, under the same tie break.
    """
    order = list(tie_break_order or REGISTERED_DIGITS)
    if sorted(order) != sorted(REGISTERED_DIGITS):
        raise FactorizationDefect(
            "the registered tie-break order was changed: %s" % order)
    if set(conditional_probabilities) != set(REGISTERED_DIGITS):
        raise FactorizationDefect(
            "the conditional distribution does not cover the registered "
            "candidate set exactly")
    if not prefix_probability > 0:
        raise FactorizationDefect(
            "P(u | x) must be strictly positive for the common factor to cancel")

    def _argmax(scores):
        best = None
        for digit in order:
            value = scores[digit]
            if best is None or value > scores[best]:
                best = digit
        return best

    joint = {digit: prefix_probability * conditional_probabilities[digit]
             for digit in REGISTERED_DIGITS}
    joint_choice = _argmax(joint)
    conditional_choice = _argmax(conditional_probabilities)
    if joint_choice != conditional_choice:
        raise FactorizationDefect(
            "the restricted ranking over the complete two-token candidates "
            "disagrees with the ranking over the discriminant position: %r "
            "against %r" % (joint_choice, conditional_choice))
    return conditional_choice


# ---------------------------------------------------------------------------
# The replay gate.
# ---------------------------------------------------------------------------

def registered_candidate_surfaces(registry):
    """The registered S2/S3 candidate surfaces, read from the v0.6 registry."""
    for profile in registry["profiles"]:
        if profile["profile"] == "S2":
            return list(profile["candidate_surfaces"]["answer_domain"])
    raise FactorizationDefect("the registry carries no S2 profile")


def replay(registry, root=None, counters=None):
    """Run the replay-only factorization derivation. Zero tokenizer encodes."""
    sources = verify_immutable_sources(root=root)
    result = load_immutable(RESULT_PATH, root=root)
    corpus = load_immutable(CORPUS_PATH, root=root)
    surfaces = registered_candidate_surfaces(registry)
    by_hash = corpus_prompts_by_hash(corpus)

    roles = sorted({record["role"] for record in result["records"]
                    if not record.get("structural_absence")})
    if tuple(roles) != ROLES:
        raise FactorizationDefect(
            "the published result does not cover exactly the pinned roles %s"
            % (ROLES,))

    per_role = []
    bound_counts = {}
    for role in roles:
        pairs = bound_sequences(result, by_hash, role)
        bound_counts[role] = len(pairs)
        candidates = solve_token_pieces(pairs)
        per_role.append(
            derive_role_factorization(result, candidates, role, surfaces))

    if counters is not None:
        counters.add("replay_gate_evaluations", 1)

    common_tokens = sorted({entry["common_prefix_token"] for entry in per_role
                            if entry.get("common_prefix_token") is not None})
    discriminants = sorted({tuple(entry["discriminant_token_ids"])
                            for entry in per_role
                            if entry.get("discriminant_token_ids")})
    return {
        "schema_version": SCHEMA_VERSION,
        "document_class": "study3_p0_r1_factorization_replay",
        "stage": "P0-R1-REPLAY",
        "derived_not_transcribed": (
            "the common-prefix token and the ten discriminant token IDs are "
            "recovered from the immutable published P0-T result and the frozen "
            "corpus; no token identity is written into this module as a "
            "constant"),
        "tokenizer_encodes_performed": 0,
        "tokenizer_constructions_performed": 0,
        "model_operations_performed": 0,
        "immutable_sources": sources,
        "bound_frozen_corpus_sequences": bound_counts,
        "registered_candidate_surfaces": surfaces,
        "roles": per_role,
        "common_prefix_token_is_common_to_every_role": len(common_tokens) == 1,
        "discriminant_token_ids_are_common_to_every_role":
            len(discriminants) == 1,
        "all_roles_eligible": all(entry["eligible"] for entry in per_role),
        "equivalence": equivalence_identity(),
    }


def gate(registry, root=None, counters=None):
    """Replay and fail closed. Returns the replay document when every role passes."""
    document = replay(registry, root=root, counters=counters)
    failures = [entry for entry in document["roles"] if not entry["eligible"]]
    if failures:
        raise FactorizationDefect(
            "the replay factorization gate failed for %s"
            % ", ".join("%s (%s)" % (entry["role"], "; ".join(entry["reasons"]))
                        for entry in failures))
    if not document["common_prefix_token_is_common_to_every_role"]:
        raise FactorizationDefect(
            "the pinned roles do not share one common-prefix token")
    if not document["discriminant_token_ids_are_common_to_every_role"]:
        raise FactorizationDefect(
            "the pinned roles do not share one discriminant token-ID vector")
    return document


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def _load_registry(root=None):
    path = os.path.join(
        root or REPO_ROOT, "studies", "study3", "protocol",
        "interface_calibration_rendering_registry_v0_6.json")
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--emit")
    args = parser.parse_args(argv)
    try:
        document = gate(_load_registry())
    except FactorizationDefect as exc:
        print("REPLAY FACTORIZATION DEFECT: %s" % exc)
        return 2
    if args.emit:
        with open(args.emit, "wb") as handle:
            handle.write(dumps(document).encode("utf-8"))
        print("wrote %s" % args.emit)
    if args.check or not args.emit:
        first = document["roles"][0]
        print("replay factorization: PASSED")
        print("  encodes performed        : %d"
              % document["tokenizer_encodes_performed"])
        print("  common-prefix token      : %d (derived)"
              % first["common_prefix_token"])
        print("  common-prefix bytes      : %r" % first["common_prefix_bytes"])
        print("  discriminant token IDs   : %s (derived)"
              % first["discriminant_token_ids"])
        print("  bound corpus sequences   : %s"
              % document["bound_frozen_corpus_sequences"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
