# Study 3 draft-v0.6: final focused methods-review packet

> **This packet is a request for review, not a claim of correctness.**
>
> Every repair it describes is labelled
> `PROPOSED_RESOLVED_SUBJECT_TO_FINAL_FOCUSED_REVIEW`. draft-v0.6 is not
> reviewed, not frozen, not selected and not formally executable. The
> determination belongs to a party that did not draft it.

Authority: [`../prompts/study3_v0_6_p0_r1_authority.md`](../prompts/study3_v0_6_p0_r1_authority.md)
§11.

State: `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_6_COMPLETE_AWAITING_FINAL_FOCUSED_METHODS_REVIEW`

## 0. The scope of this review, stated first

§11 limits the final review to four things:

1. the **first-discriminative-token factorization**;
2. the **eligibility-classifier repair**;
3. the **affected accounting**; and
4. the **consistency of the resulting candidate**.

It is **not** another general review of every historical artifact, and it must
**not** reopen unrelated resolved findings without a concrete contradiction in
live v0.6 bytes. If the review accepts v0.6 and P0-R1 discloses no
design-changing mechanical defect, no further general methods-review cycle is
required before an operator freeze decision.

## 1. What to read, in order

| # | object | why |
| --- | --- | --- |
| 1 | [`../prompts/study3_v0_6_p0_r1_authority.md`](../prompts/study3_v0_6_p0_r1_authority.md) | the operative authority, 19,632 bytes, sha256 `f72292e7…c19d2` |
| 2 | [`../pilot/p0/results/p0-t/P0_T_DISPOSITION.md`](../pilot/p0/results/p0-t/P0_T_DISPOSITION.md) | the immutable evidence that motivates both repairs |
| 3 | [`../reviews/v0_6_operator_amendment.md`](../reviews/v0_6_operator_amendment.md) | the operator decision in prose |
| 4 | [`../protocol/interface_calibration_rendering_registry_v0_6.json`](../protocol/interface_calibration_rendering_registry_v0_6.json) | the binding normative surface |
| 5 | [`../pilot/p0_r1/p0_r1_factorization.py`](../pilot/p0_r1/p0_r1_factorization.py) | the derivation, with zero tokenizer encodes |
| 6 | [`../pilot/p0_r1/p0_r1_eligibility.py`](../pilot/p0_r1/p0_r1_eligibility.py) | the repaired classifier |
| 7 | [`../pilot/p0_r1/p0_r1_model_runner.py`](../pilot/p0_r1/p0_r1_model_runner.py) | the scoring contract that would execute |
| 8 | [`scoring_boundary_v0_6_tables.json`](scoring_boundary_v0_6_tables.json) | every derived number |
| 9 | [`p0_r1_corrected_eligibility_tables.json`](p0_r1_corrected_eligibility_tables.json) | the corrected matrix, and the two repairs separated |

## 2. Claim 1 — the factorization

**Claim.** For each pinned role tokenizer, every complete `S2`/`S3` candidate
factors as `candidate_d = common_prefix || discriminant_d`, with common prefix
token `220` carrying exactly one U+0020 and discriminants `15`–`24` carrying
`0`–`9`.

**How it is established.** Not by transcription. The verifier reads two immutable
sources, verified by byte length and SHA-256 before use:

| source | bytes | sha256 |
| --- | --- | --- |
| `p0_tokenizer_gate_result.json` | 5,820,022 | `9603b611…3a85f` |
| `p0_corpus.json` | 69,781 | `5343019a…1e1c6c` |

It binds 70 published `(prompt, token-ID)` pairs per role to the exact frozen
prompt bytes by SHA-256, then solves for the byte string each token contributes
by intersecting, over every bound sequence, the set of substrings that token
could occupy. The common-prefix token and each discriminant token are required to
be **uniquely** determined. They are.

**What a reviewer should attack.**

* Is the uniqueness argument sound? The solver returns *candidate sets*; 20 of
  49 corpus tokens remain ambiguous (word-boundary shift ambiguities such as
  `"Let"` versus `"Let "`). The claim is made only for tokens whose set has
  cardinality exactly 1. Is that the right bar?
* The verifier assumes decoding is concatenative over the observed corpus. Is
  that assumption adequately supported by the byte-exact round-trip the P0-T gate
  enforced fail-closed on all 4,902 member encodes?
* Condition `SB-5` (no BOS/EOS/template/normalization/padding/truncation) is
  established structurally: no constant sequence-initial token across distinct
  prompts, no final token absent from every interior position, no registered
  prompt ending in the common-prefix token, and every published sequence
  reconciling with its recorded prompt byte length. Is that sufficient, or does a
  residual normalization remain conceivable?

## 3. Claim 2 — the equivalence is exact

**Claim.** `argmax_d P(u, v_d | x) = argmax_d P(v_d | x, u)`, exactly, because
`P(u | x)` is a strictly positive common factor.

**What a reviewer should attack.**

* The cancellation requires `P(u | x) > 0`. The runner asserts it. Is asserting
  it the right behaviour, or should a non-positive prefix probability be a
  recorded outcome rather than a stop?
* The claim is explicitly restricted to equal-length two-token candidates with a
  common prefix under a deterministic argmax. Is the registered
  `does_not_extend_to` list complete?
* The scoring context is built by **concatenating** the registered prompt token
  IDs with the verified prefix token, never by re-encoding a concatenated string.
  Is that the right choice? It avoids a new encode and avoids re-tokenization
  drift, but it is not identical to `encode(prompt + " 0")` by construction.
  **This is the sharpest open question in the packet.**

## 4. Claim 3 — the classifier repair

**Claim.** Eligibility now computes at the narrowest applicable key, no failure
crosses a profile, role or contrast, and no ineligible row can carry an empty
reason list.

**Evidence.** Replaying the immutable P0-T records:

| view | cells | eligible | ineligible | empty-reason | executable per role |
| --- | --- | --- | --- | --- | --- |
| historical, as emitted | 39 | 6 | 33 | **27** | 0 |
| classifier repair only, v0.5 rule | 39 | 33 | 6 | **0** | **9** |
| classifier repair + v0.6 boundary | 39 | 39 | 0 | **0** | **11** |

The middle row is the point: with propagation removed but the scoring rule
untouched, every target role retains nine executable genuine `I3` contrasts. The
emitted historical terminal state was over-severe. That is confirmed
mechanically, and the historical result is still not edited.

**What a reviewer should attack.**

* Reasons are structured with a `scope`, and the validator requires a reason's
  scope to be a *prefix* of the cell it decorates. Is prefix-containment the
  right non-propagation criterion?
* `S4` is excluded from target-role executability both by the classifier and by
  the validator. Is the double guard redundant or appropriate?
* `not_applicable` is never instantiated as a cell. Confirm that the two
  structurally absent pairs (`S2`/`K6-SEP`, `S3`/`K6-SEP`) are absent from the
  matrix rather than present-and-skipped.

## 5. Claim 4 — the accounting

**Nothing moves except two things, and both are surfaced.**

Unchanged, recomputed from `design_statistics.py` at derivation time:
`m_max` 43; budgets `19/17200`, `17181/17200`, `381/400`, `9/10`; sizes
`413`/`214`/`448`; development pass counts `389`/`129`/`383`; confirmation pass
counts `388`/`127`/`381`; gate-bearing cells `S1` 43, `S2` 16, `S3` 16, `S4` 39;
sequence-level development projection `31,065`.

Changed:

1. **`S2`/`S3` scoring-context token count**: `registered_prompt_token_count + 1`.
   P0-R1: +18 tokens, +0 evaluations. Development projection: +5,001 tokens,
   **+0 evaluations**.
2. **The `S3` zero-incremental-cost condition**, restated from "a jointly
   single-token registered answer domain" to a common-prefix/discriminant
   formulation. Numeric effect: none.

**What a reviewer should attack.**

* Is it right that the extra teacher-forced token changes token processing but
  not the number of sequence-level prefill evaluations?
* `S3`'s recorded `scoring_context_token_count` equals `S2`'s, because `S3`
  rescores the identical context, while its `tokens_processed` is `0`. Is that
  the clearest way to record a zero-cost rescoring?

## 6. Claim 5 — consistency of the resulting candidate

* The visible rendering surface is byte-identical to draft-v0.5: all 22 normative
  template assets, the answer cue, the candidate surfaces, the label alphabets,
  the separators, the instructions, the applicability table and the tie breaks.
* draft-v0.5 and its schema remain byte-identical on disk, so the P0-T
  observations are never restated against a surface that did not exist when they
  were made.
* `K6-SEP` remains structurally absent for `S2` and `S3`.
* `OD2`, `UR-22` and the `RP` wrapper remain unresolved; the wrapper is **null**,
  not empty.

## 6a. A structural constraint the reviewer should weigh

The normative scoring boundary is registered **entirely in the v0.6 registry and
its schema**. The draft-v0.5 protocol JSON, its Markdown companion and the
protocol schema are byte-identical to the baseline.

That placement is forced. The immutable P0 corpus manifest byte-binds
`interface_calibration_protocol_draft.json` at 418,733 bytes, sha256
`1197e087…3c7ca7`, as a generator identity. Editing that file makes the manifest
stop reproducing and fails
`tests/test_study3_p0_feasibility_pilot.py::test_frozen_corpus_re_derives_byte_exactly`,
one of the 122 historical P0 tests §10 requires. §9 forbids editing the P0
namespace and that test module, so neither may be adjusted.

This was observed, not assumed: an additive block was drafted into the protocol
JSON, published to a working commit and validated in the registered CPU route.
Run `cmf4` recorded 4,262 historical passes plus 77 net-new with exactly that one
extra failure, and the protocol files were then reverted to baseline bytes.

**The question for the reviewer.** Is the v0.6 rendering and scoring registry a
sufficient normative home for the scoring boundary, given that it carries
`BINDING_NORMATIVE_INPUT_NOT_AN_ILLUSTRATIVE_EXAMPLE` status and its own
committed schema? And is it acceptable that the draft protocol JSON is now
effectively frozen for as long as the published P0 artifacts must reproduce
byte-exactly?

## 7. What this packet does not ask for

It does not ask for a freeze, a seed, a bank, an interface selection, a positive
reference, a confirmation access, an `OD2` or `UR-22` resolution, or an
evidence-ledger row. It does not ask the reviewer to approve the P0-R1 model
pilot, which is registered under a separate one-shot authorization and gated on
its own replay gate.

## 8. If the review rejects

Then draft-v0.6 is not frozen and the successor must choose a narrowly
demonstrated repair or stop this Study 3 route. It may not silently widen the
pilot, and it may not convert a rejection into an acceptance.
