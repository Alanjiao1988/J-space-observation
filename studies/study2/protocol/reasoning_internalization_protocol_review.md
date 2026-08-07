# Study 2 reasoning-internalization protocol methods review

## Review identity and allowance

- Review type: the single bounded Stage P methods review.
- Candidate commit: `97ea5b291aec1bcfc6e5ab9a0de42a6c901afae4`.
- Candidate tree: `966a31aec9bb4f1aa057e90ef95a6a4134b155ea`.
- Original authority SHA-256:
  `1408c5ae4d09a097c70b0e984150c4947e527ca12b5614905a98b65685ed0b37`.
- Additive Gate A authority SHA-256:
  `e7f015a71e0491aa26f66780e94ad7fd8201b3d1b9411298d92848781310c3c1`.
- Candidate reviews consumed: 1 of 1.
- Consolidated corrections consumed: 0 of 1.
- Same-checklist verification: `NOT_REQUIRED_NO_FATAL_OR_MATERIAL_CORRECTION`.
- Formal disposition: `PASS_WITH_DISCLOSED_MINOR_LIMITATIONS`.

This review is distinct from the earlier operator-directed pre-review gap
record. That record did not consume this allowance.

## Fixed candidate bytes

| Path | Bytes | SHA-256 |
|---|---:|---|
| `studies/study2/prompts/stage_p_protocol_design_prompt.md` | 53,018 | `1408c5ae4d09a097c70b0e984150c4947e527ca12b5614905a98b65685ed0b37` |
| `studies/study2/prompts/stage_p_gate_a_operator_amendment.md` | 5,836 | `e7f015a71e0491aa26f66780e94ad7fd8201b3d1b9411298d92848781310c3c1` |
| `studies/study2/protocol/reasoning_internalization_protocol.json` | 39,352 | `a1ae4d18fc88410c00dbe9c211b0ebac723ed67d56732cb73a8bd5080a1d767f` |
| `studies/study2/protocol/reasoning_internalization_protocol.schema.json` | 54,497 | `f063328d9fc38288e0b657f4d74c0b9b082d09c55f0ca4a29591fdda26accb38` |
| `studies/study2/protocol/reasoning_internalization_protocol.md` | 21,151 | `4d58d8c569728d96999135c2bc5c547980a3c0d86b5c5b2c8ca0b87e57edf054` |
| `studies/study2/protocol/stage_p_power_sensitivity.json` | 9,291 | `f2514ffe9bc5cff80ef164f5b05a3cd90bbdfb9550af49b755accd3cbc3589ff` |
| `scripts/build_study2_task_bank.py` | 1,583 | `d3bd127126158fdcef1c194bace3c42045188760bf34f91ef0c0302a36729b82` |
| `scripts/validate_study2_protocol.py` | 8,717 | `ba6b55e3cd5845c5ff4e9d8a2233b1f1d6cccb96a8988847c64db7c0d296dd8b` |
| `scripts/analyze_study2_stage_p_sensitivity.py` | 8,768 | `9e17ad590c0cf79bd68c198c4d46ee090f948ee972116161679fbc418d756a02` |
| `src/jspace_observation/study2_protocol.py` | 72,263 | `852073bd125aaf119ba7897666d49075c93a660ad7701d387e5bdbbfe71dbeaa` |
| `src/jspace_observation/study2_task_bank.py` | 29,847 | `e0053afec6a1c6abb712f292605f038263f921e34414d545876bdafe11a22d7e` |
| `tests/test_study2_protocol.py` | 17,673 | `97b1aa58598b39360005c9fec80fecbad5ae555818d688274c776833fd4ddefc` |
| `tests/test_study2_task_bank.py` | 9,569 | `ad5a5de1bf5ccc994bdbce254e54609b4ea62659d03c387c80f89c4a9fa4aff2` |
| `studies/study2/data/development.jsonl` | 752,708 | `7dd19884cc2cb4685863cc9df768347f7cfd52c348e5117ec574b52d3b0cf1d6` |
| `studies/study2/data/behavioral_confirmation.jsonl` | 3,068,780 | `cbd20d061ee5bdc8f8484b79005ad7faa018add9ef028da16cd885f2c89ea3a9` |
| `studies/study2/data/mechanistic_development_candidate_pairs.jsonl` | 8,008,776 | `397c752162e41ff1bc83ecf4cf58b768baa6400c9e6d20dc092f317238c1ef66` |
| `studies/study2/data/mechanistic_candidate_pairs.jsonl` | 8,102,984 | `61dfaed3b8a56be4d27083bdca5307ea326ecfaeaa26f2d43dd3c8deafd77df6` |
| `studies/study2/data/task_bank_manifest.json` | 32,340 | `7fa20875b11052f000b3694c76a1f53e4782b987317c94b7f93bff89293d36e7` |

ACR evidence over these bytes:

- generation: `cmc3` and `cmc4`, both `Succeeded`, identical bank hashes;
- focused tests: `cmc9`, 41 passed;
- full suite: `cmca`, 3,537 passed / 15 skipped / 2 accepted historical failures;
- candidate validator: `cmcb`, `Succeeded`;
- sensitivity calculation: `cmc2`, `Succeeded`.

## Fifteen-item checklist

### 1. NT has no generated or supplied reasoning and measures preference

`PASS`. NT ends at `Answer:`, supplies no trace, generates zero tokens, and
reads the four registered continuation logits. Full-vocabulary top-1 is
diagnostic only.

### 2. Four-option token support is prospective and non-substitutable

`PASS`. Stage T must prove the literal ` A`, ` B`, ` C`, and ` D`
continuations separately for all three pinned tokenizers. Failure closes on the
registered tokenizer blocker; no outcome-dependent alphabet replacement is
allowed.

### 3. Ground truth, traces, distractors, and counterfactuals are unique

`PASS`. The independent verifier reconstructs every operator application,
intermediate, answer, distractor, trace arm, pair recombinant, and control from
primitive fields. Depth-3 PT and ST states are distinct. All 3,968 registered
task or pair units were verified.

### 4. All four roles are semantically disjoint

`PASS`. The manifest reports zero semantic overlap for every role pair and
zero exact or normalized protected-prompt overlap across 1,106 protected
prompts.

### 5. Selection is prospectively closed

`PASS`. Task generation, templates, models, pair candidates, option mapping,
and exclusions are fixed before model output. Stage T selection uses only
common tokenizer mechanics and frozen hashes. Gate A is a fixed development
open/close decision and cannot revise a task or threshold. The only later cell
and layer choices are the explicitly registered target-only behavioral and
development algorithms.

### 6. Balance and direct controls separate composition from shortcuts

`PASS`. A/B/C/D and T-A/T-B are exact within cells; state and operator spreads
are at most one; single-field conditional label tables are balanced. Depth 1
is retained as the direct control while depths 2 and 3 require composition.

### 7. Recombinant transfer is distinct from answer copying

`PASS`. Every pair enforces pairwise-distinct `a_d`, `a_r`, and `a_x`, with one
shared value-to-label map and pairwise-distinct labels. `G_x` and `G_d`
separate recipient-side recomputation from donor-answer copying.

### 8. Matched causal controls cover the stated alternatives

`PASS`. No-op, same-intermediate, same-answer/different-intermediate,
deterministic random donor, wrong position, early band, and motor band are
closed. Every control retains the primary recipient contrast toward `a_x`.

### 9. Localization is development-only and target-defined

`PASS`. The target development pack alone selects one three-layer window by the
registered score and lowest-layer tie-break. Confirmation cannot move it, and
both controls use the same target-defined window or its frozen normalized-depth
mapping.

### 10. The probe is cross-template and answer-leakage controlled

`PASS`. The probe trains on T-A mechanistic development and tests on disjoint
T-B mechanistic confirmation, at one fixed center layer. Intermediate class,
final option, label permutations, and the answer-label probe are retained.

### 11. M1200 is secondary and non-rescuing

`PASS`. M1200 cannot select a task, pair, cell, layer, or primary result.
A600/B600 remain replicate diagnostics. The J-lens axis cannot promote or
demote the lens-independent axis.

### 12. The controls support only checkpoint-level association

`PASS`. Both fixed controls are required. The strongest comparison concerns the
total checkpoint-level post-training/distillation-associated difference and
cannot identify a training example, trace, objective, or loss component.

### 13. Historical authorities and protected bytes are preserved

`PASS`. DR-01 remains binding; Study 1 and Phase 1.0D states remain unchanged;
EV-0016 remains the evidence tail. ACR validation reproduced the 152-file and
36-file protected rollups exactly. No old terminal state or lens tensor was
opened or rewritten.

### 14. Metrics, nulls, thresholds, branches, and outputs are computable

`PASS_WITH_MINOR_LIMITATIONS`. Restricted probabilities, Wilson intervals,
deterministic bootstrap sampling, trace effects, patch contrasts, probes,
J-lens metrics, composite precedence, blockers, Gate A, and output rows are
fully specified. Gate A's exact boundary is 43 of 128; 42 does not pass. The
power pack explicitly declines to infer unidentified joint conjunctive power.

### 15. Positive and negative states are reconstructible without semantics

`PASS`. Every future table has a closed field contract and primary key. Unknown,
missing, duplicate, out-of-shard, non-finite, or incomplete rows fail closed.
Gate A, behavioral, mechanistic, probe, J-lens, and classification decisions
bind their exact inputs and manifest-last packs.

## Initial findings

| ID | Severity | Location | Finding | Disposition |
|---|---|---|---|---|
| S2P-R-01 | MINOR | `reasoning_internalization_protocol.json#/feasibility_gate`; `#/limitations/13` | Gate A conditions confirmation opening on favorable target development, creating protocol-selection and winner's-curse risk even though confirmation remains unopened. | Accepted and explicitly disclosed. Gate A can only open or close the version; it cannot revise it. |
| S2P-R-02 | MINOR | `reasoning_internalization_protocol.json#/design_sensitivity/joint_conjunctive_power_identified`; `#/limitations/14` | Component power and sensitivity do not identify joint power across the many conjunctive gates. | Accepted and explicitly disclosed. No sample size, threshold, or claim is changed. |

There are no `FATAL` or `MATERIAL` findings.

## Consolidated correction and verification

No consolidated correction was permitted or needed because the formal review
found no FATAL or MATERIAL issue. The candidate byte set above was not changed
between checklist review and disposition. Same-checklist correction
verification is therefore `NOT_REQUIRED_NO_FATAL_OR_MATERIAL_CORRECTION`; no
second redesign or review occurred.

The Stage P methods-review allowance is now spent. Freeze may proceed by
mechanically changing lifecycle fields, binding the reviewed candidate and
final hashes, and rerunning final ACR validation.
