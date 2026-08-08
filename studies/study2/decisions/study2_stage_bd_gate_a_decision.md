# Study 2 Stage B-D — Gate A feasibility decision

Terminal state: `STUDY2_PROTOCOL_V1_CLOSED_ON_DEVELOPMENT_FEASIBILITY`

Run id `s2-bd-development-v1`. Protocol version
`jspace-study2-reasoning-internalization/v1`. Decision date: the commit that
introduces this document.

## 1. What was decided

The pre-registered Gate A rule was applied to a complete, integrity-valid
development pack and returned `overall_gate_pass = false`. Under the terminal
precedence registered in the Stage B-D operator authority, a complete valid pack
in which either target family has fewer than 43 restricted-option-correct rows
closes protocol v1 on development feasibility.

Gate A is a non-scientific feasibility gate. Its failure is **not** evidence
that the target model does not reason, did not internalize a chain of thought,
lacks a distilled causal mechanism, or that J-space is invalid. It records only
that the frozen interface did not clear the accuracy floor that the protocol
required before spending confirmation and mechanistic budget.

## 2. The rule, exactly as frozen

The rule was frozen before any Stage B-D measurement existed and was not
modified by this round:

- decision model: `target` only;
- decision arm: `NT` (no-tool) only;
- depths 2 and 3 pooled within family, 64 rows per depth, so n = 128 per family;
- X = restricted-option-correct rows;
- exact one-sided binomial upper tail under p₀ = 0.25, α = 0.025;
- a family passes only when X ≥ 43, equivalently p_exact ≤ 0.025;
- Gate A passes only when **both** `permutation_chain` and `affine_mod10` pass.

Registered boundary values: X = 43 has upper tail 0.018218515933 and passes;
X = 42 has upper tail 0.028760674518 and does not. There is no cross-family
pooling, depth fallback, favorable subgroup, template selection, multiplicity
rescue, control-model rescue, or prior-result rescue.

## 3. The two decisive counts

| family | X | n | exact upper tail | ≥ 43 | family_gate_pass |
| --- | --- | --- | --- | --- | --- |
| `permutation_chain` | 25 | 128 | 0.9403523926144965 | no | false |
| `affine_mod10` | 33 | 128 | 0.4526854444021635 | no | false |

`overall_gate_pass = false`.

Chance under the restricted four-option surface is 32/128. The target model
scored below chance on `permutation_chain` and one row above chance on
`affine_mod10`. Neither family is close to the threshold: reaching X = 43 would
require 18 and 10 additional correct rows respectively. The decision does not
depend on any judgment call at the margin.

Integrity booleans for both decisive rows: `balance_ok = true`,
`finite_complete = true`, `confirmation_opened_before_decision = false`.

Per-family Gate input digests: `permutation_chain`
`439d00c4ba82d56c4418b43d5ce32cf192f2064cf5d3cbf46aac26240236125c`;
`affine_mod10`
`34ce185d4439e78bd712ac239b69212c143a8dba00c4fe8a5355c8a3c41720bc`.
Combined decision digest `gate_inputs_sha256`
`1433f8119b2d8e377be7ede2735430ab55006c3737ebd2bf9e0c85c486b93cf7`.

## 4. Control results, which have zero authority

The controls were run and retained in full because the protocol requires the
complete six-row table, not because they can move the decision. They are
descriptive only.

| model_role | family | X | n | exact upper tail | family_gate_pass |
| --- | --- | --- | --- | --- | --- |
| `target` | `permutation_chain` | 25 | 128 | 0.9403523926144965 | false |
| `target` | `affine_mod10` | 33 | 128 | 0.4526854444021635 | false |
| `lineage_base` | `permutation_chain` | 33 | 128 | 0.4526854444021635 | false |
| `lineage_base` | `affine_mod10` | 44 | 128 | 0.011190410208704914 | true |
| `instruction_control` | `permutation_chain` | 36 | 128 | 0.23494577258837968 | false |
| `instruction_control` | `affine_mod10` | 32 | 128 | 0.5338897878610797 | false |

`lineage_base` clearing the `affine_mod10` threshold is exactly the situation the
frozen rule anticipated when it gave controls no authority. `controls_affect_decision`
is recorded as `false` in the decision object, and substituting either control
for the target is not a permitted operation. Reading a single passing control
cell as a rescue would be the multiplicity failure the pre-registration exists to
prevent: six family cells were computed, and one control cell at p = 0.011 is
unremarkable under that many comparisons.

## 5. Why this is not a measurement artifact

The failure is not localized, so it cannot be attributed to one bad cell, one
template, or one depth.

- All 24 model × family × arm aggregates lie between 0.188 and 0.318 restricted
  accuracy, against a chance rate of 0.25.
- Every one of the 96 summary cells is finite and complete
  (`finite_rows == n`, `execution_complete = true`).
- The target's NT cells span 0.156 to 0.375 across both templates and all three
  depths, with 95% Wilson intervals that all contain 0.25.
- The pattern does not improve with depth, does not favor either template, and
  is the same for the two controls, including the model that was never
  instruction-tuned.

An implementation defect that silently destroyed the answer signal would be
expected to produce exactly this picture, so the round's integrity evidence,
rather than the accuracy numbers, is what distinguishes the two explanations:

- every prompt was re-tokenized at inference time and checked against the Stage T
  sealed token identity, so the model saw the frozen bytes and no others;
- the option token IDs A=362, B=425, C=356, D=422 were verified against the seal
  before any weight was loaded;
- the full 3,072-row space, its primary-key digest, and the shard manifest digest
  were all pre-registered in `stage_bd_preinference_seal.json` and matched at
  runtime;
- the restricted surface is a four-way choice among fixed option tokens, so a
  model that produced no signal at all would land at 0.25, which is what all
  three models did.

The honest reading is that this 1.5B interface, on this frozen bank, at these
depths, under a restricted-option surface with no tool and no chain of thought,
is at chance. Whether a different interface, surface, or scale would clear the
gate is not answered here and cannot be answered by rerunning this protocol
version.

## 6. Consequences

Closed by this decision:

- Stage B-C (behavioral confirmation) is **not** opened;
- mechanistic-cell selection, M-D and M-C are **not** started;
- no scientific evidence row is created; `paper/evidence_ledger.csv` still ends
  at EV-0016 and is byte-identical;
- no internal-reasoning, distillation, or J-space classification is made;
- protocol v1 of the reasoning-internalization study is closed.

Explicitly prohibited without new authority: backfilling, replacing,
re-rendering, pooling away, reinterpreting, or rerunning the same protocol
version. Any future attempt requires a new protocol version, a new operator
authority, and new task-bank seeds.

The confirmation bank remains unopened. `stage_bd_confirmation_unopened_receipt.json`
records `behavioral_confirmation_tokenizations = 0`,
`behavioral_confirmation_forwards = 0`,
`behavioral_confirmation_output_objects = 0`,
`confirmation_prompt_identities_loaded = 0`,
`mechanistic_confirmation_operations = 0`, and
`model_free_integrity_reads = 0`, over all six registered confirmation paths.
The execution image additionally makes those six paths physically absent, and the
GPU job printed `CONFIRMATION_PATHS_PRESENT=0`.

## 7. Provenance of the decided bytes

The decision was computed by `scripts/finalize_study2_stage_bd.py` on a CPU-only
Azure image that has neither `torch` nor `transformers` installed, then certified
by `scripts/validate_study2_stage_bd.py`, which shares no writing code path with
the finalizer and returned `certified: true` over all 3,072 rows.

- behavioral rows: Azure Container Apps GPU T4, image
  `sha256:60fd31b4b396dd09565103d85b9ccf9a8d0703f4d6333e870167b95ee02ebe86`,
  source commit `2bb70de3c2bd32a67f21b674bcecb44126032ac0`, 18 shards, 0 retries;
- shard manifest digest
  `7a0f529a9868b054fed21510959c305c01861e6dbe0692f66c1294b6885317b5`, equal to the
  value sealed before any weight load;
- Gate A decision object `stage_bd_gate_a_decision.json`, 38,845 bytes, SHA-256
  `1aebc183e157f8097cdc88ab3a9dbdb53bd1ae3bf4ff6a428e3e9dfef49a3544`;
- core manifest `stage_bd_core_manifest.json`, 41,322 bytes, SHA-256
  `4a64cbf9de6d2fae476589b3a8213dd5bf2dedad19c40b9d4003dd768fa56716`.

Two finalization runs on two different image digests reproduced all eleven
artifact digests identically. Every committed byte was pulled from the registry
by manifest digest; nothing was regenerated on the workstation.
