# Thread handoff - J-space observation project

Date: 2026-07-25

Repository: `Alanjiao1988/J-space-observation`

Current Phase 0.5 runtime launcher commit:
`be997eefbaec410107045dac7c50423f7297c633`

Parser-v2 frozen implementation commit:
`654f3bb463fedc33b0638b77fefdd9b2b9d1c9c2`

## 1. Authoritative identities

Historical experimental target:

```text
Display name:
DeepSeek-R1-Distill-Qwen-1.5B

Hugging Face model ID:
deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B

Role:
historical target of the bounded n=3 behavioral records and target of the
bounded Phase 0.5A technical Jacobian run
```

Engineering, curation, labeling, arbitration, and audit agents:

```text
gpt-5.6-sol
reasoning=max
```

Do not confuse the engineering agent with the experimental target.

## 2. Current phase

Path C remains preserved:

```text
status: CLOSED / FAIL / RETIRED
development cases: 60
locked cases: 120
parser v2 implemented from public development cases: yes
locked evaluation performed: yes (one shot, 2026-07-25)
formal outcome: FAIL (32/34 mandatory gates passed)
holdout: spent and retired
higher-n performed: no
new target-model behavioral run: no
```

The sealing phase constructed, independently labeled, validated, and privately
sealed a prospective parser-v2 evaluator set. Parser v2 was later implemented
using only the public development set. The single authorized one-shot locked
evaluation was executed on 2026-07-25 and closed with formal outcome **FAIL**:
`boxed_final_miss` 1/20 against a limit of 0, and `wrong_span` 2/80 against a
limit of 1. Report-only typed agreement was 116/120. The holdout is now spent
and retired; formal reuse and formal rescoring are strictly prohibited, and
post-retirement reads are permitted only for diagnosis and parser-v3
development.

Phase 0.5A is also complete:

```text
run ID: 20260718T184445Z
official source: anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e
primary: job-jspace-p05-jlens-l7tipil / Failed at F4
sole operational retry: job-jspace-p05-jlens-m1sazlr / Succeeded
F2/F3 recomputed on retry: no
F4: passed with unchanged tolerance after exact fp32 serialization
F5: not run
final decision: GREEN / COMPLETE for bounded technical feasibility only
Plan B: not triggered
```

Detailed report:

- `reports/phase1_parser_v2_validation_set.md`
- `reports/phase1_parser_v2_development.md`
- `reports/phase05_jlens_feasibility.md`

## 3. Frozen protocol

```text
starting commit:
58d299bb66c5536a0f1b7d0617204472fbb8c212

final protocol commit:
cc93ffe603ab8338ed860586a52b1911af4b3277

tooling/development commit:
e7a95a458d05d4ef211bb6902c2a20cb5f16bf60

production-ingress hardening:
297420abfebb65c9f3702c56f28fe5a193913cd0

sealed no-Git validation:
9b4262a9d35e6342935b8d2f72887a56c5f98486

protocol bundle SHA-256:
5d486a53b532012c3a64eb6bd962be325fb9892ebbb042807b919f9e41b23666

acceptance-gate SHA-256:
a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988
```

Frozen files:

- `docs/phase1_parser_v2_protocol.md`
- `docs/phase1_evaluator_validation_set.md`
- `docs/phase1_parser_v2_acceptance_gates.json`

The final protocol was pushed before eligible construction. Do not amend these
v1 gates after seeing a locked result.

## 4. Evaluator set

Composition:

| Property | Development | Locked |
|---|---:|---:|
| Total | 60 | 120 |
| Per S01-S12 stratum | 5 | 10 |
| Present | 40 | 80 |
| Ambiguous | 5 | 10 |
| No answer | 15 | 30 |

Locked critical cases: 80.

Locked material cases: 68.

Public development path:

```text
evaluator_sets/parser_v2_v1/development_cases.jsonl
SHA-256: bfaeca837ecfe8673df834c5b8a4fc1626f0835c6ae35c0821acf59bd6e4ac27
```

Hard exact, normalized, cross-set template, and historical overlaps are zero.
Thirty-seven near-duplicate findings were reviewed and dispositioned.

## 5. Labeling result

- Curator A/B independently produced 144 candidates each.
- Curator C selected the exact 60/120 set.
- Stage-1 Reviewer A/B completed 120/120 each, reference-blind.
- Stage-1 disagreements and arbitration rows: 57.
- Stage-2 Reviewer A/B completed 120/120 each.
- Stage-2 disagreements and arbitration rows: 0.
- Final labels: 120.
- Unresolved: 0.
- Review seals: 7.

Key agreement:

```text
presence/validity/ambiguity/strategy: 120/120
output quality: 112/120; rate 14/15; kappa 491/571
parsed answer: 120/120
candidate lists: 120/120; mean Jaccard 1
selected spans: 119/120; mean Jaccard 119/120
failure reasons: 111/120; mean Jaccard 229/240
format warnings: 73/120; mean Jaccard 199/240
Stage-2 correctness: 120/120; kappa 1
```

These are LLM operational consensus references, not human ground truth.

Visibility:

- Curators saw frozen construction protocols, not legacy/future parser
  predictions.
- The historical custodian produced non-content fingerprints; historical text
  was not supplied to curators or reviewers.
- Stage 1 was reference-blind for both reviewers and the extraction arbiter.
- Stage 2 saw sealed consensus plus immutable references and could not revise
  extraction.
- Validation/sealing agents handled private artifacts only for workflow,
  integrity, and persistence checks.
- No prospective parser-v2 implementation agent exists or has seen locked
  inputs/labels.
- The private visibility ledger records the full role transitions.

This is procedural, hash-audited isolation, not a security-enforced boundary.

## 6. Private release and Azure state

Sealed parent:

```text
phase1-evaluator-validation/parser-v2-v1/20260716T024856Z
```

Registered leaves:

- `development`
- `locked-inputs`
- `locked-labels`
- `reports`
- `manifests`

Key bindings:

```text
artifact count:
26

locked inputs:
2d60483e7f7a2ce1883acca2dcf9a6771f84b54d596ab2e02ed4a39d937c4e3e

final labels:
44d3830c5ce3f9fdd5ba3059f63ba5d8a89f76152c0fe2eb128080b40af448af

locked-label manifest:
aa53cb8a808a213423f8deb7370d880c5b1c934073301356aabb593db17fd5b6

overall manifest:
f73bc80b2d5a2c0ba720b021385fb3343dedfbe4867351376ca52b086a824260

validation report:
5b3daf44553a7c99d57c8d5a117ef82de113c4b5cde74ef13dd218c11c56b641
```

Azure:

```text
environment:
cae-jspace-observation-sea-vnet2

profile/resources:
Consumption / 2 CPU / 4Gi / no GPU

job:
job-jspace-parser-v2-set

sole execution:
job-jspace-parser-v2-set-ib7uc0e

status:
Succeeded

authentication:
ManagedIdentityCredential

identity:
id-jspace-aca-acrpull-sea
```

The upload used `overwrite=false`, reservation-first/manifest-last ordering,
exact 26-object membership, and per-object re-download size/SHA-256/ETag
verification.

After persistence:

- the job was reset to the immutable base image and `/bin/true`;
- job secrets and secret references are zero;
- exactly one terminal execution exists;
- the temporary ACR transport tag and digest were deleted;
- the local encrypted build context was deleted.

Do not restart this job for Phase 1.2A and do not write to the sealed parent.

## 7. One-shot holdout rule

The holdout has completed the full one-shot workflow and is at `CLOSED`.
The recorded state chain ran `00_draft_protocol` → `12_closed` with
`outcome = FAIL`, `holdout_retired = true`, and `holdout_spent = true`.

The workflow that was executed:

1. Implement parser v2 using only the public development set.
2. Freeze and push its implementation commit.
3. Obtain separate authorization for one locked evaluation.
4. Produce and seal predictions before labels are read.
5. Score once against the frozen gates.
6. Retain PASS or FAIL and retire the holdout.

A parser, schema, assertion, threshold, or scientific failure is not retryable.
A modified parser requires a new independent holdout. Because parser v2 failed,
any parser v3 must be validated against a newly constructed locked set; the
retired parser-v2 holdout must not be reused for a formal result and must not
be rescored.

## 8. Frozen acceptance gates

- overall typed decision: at least 114/120;
- each answer-bearing stratum: at least 9/10;
- every stratum: at least 8/10;
- answer-presence macro-F1: at least 0.95;
- ambiguity precision/recall: each at least 0.90;
- no-answer precision/recall: each at least 0.90;
- boxed/final misses: zero;
- last-number trap errors: zero;
- wrong-span errors: at most 1/80;
- material correctness errors: at most 1/120 and zero in S01/S02;
- clean pooled parser-v2 count cannot regress versus legacy;
- at least one critical stratum must strictly improve.

These gates were evaluated exactly once, on 2026-07-25. Thirty-two of the 34
mandatory gates passed; `boxed_final_miss` (1/20, limit 0) and `wrong_span`
(2/80, limit 1) failed, so the formal parser-v2 outcome is FAIL. The gates must
not be amended retrospectively.

## 9. Validation status

```text
python -m pytest tests\ -q
460 passed, 2 warnings
```

Five post-sealing `gpt-5.6-sol/max` reviews passed:

- `postseal-integrity`
- `postseal-strata`
- `postseal-agreement`
- `postseal-one-shot`
- `postseal-boundaries`

The secure transport separately passed `secure-persistence-review`.

## 10. Historical behavioral boundary

The last target-model run remains the bounded arithmetic n=3 run:

```text
source writer commit:
359643b7b5eb8f95c13cca2e60fa753df8701282

source prefix:
phase1-limited-n3-gates/20260710T152820Z

observations:
45

cells:
15

observations per cell:
3
```

The all-45 post hoc audit found 18 parser overflags, zero underflags, 14
observed extraction errors, two material correctness errors, and 19 material
evaluator issues. It selected Path C but did not change historical records,
metrics, classifications, or parser behavior.

Raw strict, stopped intervention, and postprocessed utility remain separate.
Stopped validity is intervention-controlled. Postprocessed validity is
answer-recovery utility, not raw no-CoT.

## 11. Scientific boundaries

- No target-model download, load, or inference occurred in Phase 1.2A.
- No parser v2 was implemented or evaluated during Phase 1.2A sealing. It was
  subsequently implemented against only the public development set; the
  locked evaluation remains unperformed.
- No locked labels are in the repository.
- No higher-n or GPU run occurred.
- Fixtures and consensus labels are not target-model evidence.
- LLM consensus is not human ground truth.
- Isolation is procedural and hash-audited, not security-enforced.
- Historical cells remain n=3 and are not stability evidence.
- No hidden-reasoning, internal-workspace, invisible-CoT, genuine-no-CoT, or
  J-space claim is supported.

## 12. Next authorized action

Request explicit authorization for the one-shot parser-v2 locked evaluation
against the already frozen implementation and gates. Predictions must be
sealed before labels are read, and PASS or FAIL retires the holdout.

Do not run that evaluation automatically. Higher-n, every new target-model
behavioral run, and any larger J-lens fit remain paused.

## 13. Prompt for the next thread

```text
Continue Alanjiao1988/J-space-observation after the critical-path reset and
Phase 0.5A technical feasibility result.

Read:
- reports/phase1_parser_v2_validation_set.md
- reports/phase1_parser_v2_development.md
- reports/phase05_jlens_feasibility.md
- docs/phase1_parser_v2_protocol.md
- docs/phase1_evaluator_validation_set.md
- docs/phase1_parser_v2_acceptance_gates.json
- docs/phase05_jlens_feasibility_protocol.md
- docs/thread_handoff.md

Authoritative historical target:
deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B

Current state:
- Phase 1.2A is SEALED.
- Public development set: 60 cases.
- Private locked set: 120 cases.
- Parser v2 is implemented and frozen from public development material only.
- Locked evaluation and higher-n are not authorized.
- Phase 0.5A is GREEN for bounded real-Jacobian technical feasibility only.
- F5 and actual 10-/25-prompt fits were not run.
- No new formal behavioral observation was generated.

Task:
If separately authorized, execute the registered one-shot parser-v2 locked
evaluation exactly once against the frozen implementation. Seal predictions
before labels are read, retain PASS or FAIL, and retire the holdout. Otherwise
stop. Do not start higher-n, a new target-model behavioral run, or a larger
J-lens fit.
```


## Phase 1.2D handoff - parser-v3 preregistration complete, execution pending

Preregistration commit (source freeze):

```text
e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea
```

State at that commit:

```text
holdout touched         no
predictions generated   no
locked labels accessed  no
holdout state           SEALED (unspent)
formal result           none
full test suite         1320 passed
working tree            clean, HEAD == origin/main
```

Frozen after this commit - do not modify: parser v3, the candidate worker,
Stage P prediction semantics, Stage E scoring semantics, the gate contract, the
profile binding, and the membership rules.

### What remains

```text
1. build the immutable image once from e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea
   tag j-space-observation-parser-v3-eval:e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea
2. validate image digest and provenance
3. Stage P            120 candidate + 120 parser-v2 + 120 legacy predictions
4. seal three prediction streams
5. Stage E            labels-open transaction, then first label read
6. formal PASS or FAIL, holdout RETIRED
7. independent claude-opus-5 reasoning=max recomputation
8. paper ledgers, commit and push
```

### Blocker

`infra/azure/scripts/09_build_parser_v3_eval.sh` and
`10_run_parser_v3_locked_eval.sh` are hardened POSIX shell scripts. They
re-exec under `env -i` with `PATH=/usr/local/bin:/usr/bin:/bin` and resolve
`/usr/bin/python3`. The current Windows machine has only MSYS/MINGW64 bash, no
`/usr/bin/python3`, no `/usr/local/bin`, no container runtime, and WSL with no
distribution installed. Earlier Azure phases used Python drivers and were
unaffected.

A POSIX host with Python 3.11 and the Azure CLI, signed in to subscription
`943bacdf-8b6e-4e3a-8126-a149f623d32e`, is required. The coordination zone
`parser-v2-coordination.jspace.internal`
(`rg-jspace-parser-v2-coord-sea`, 0 VNet links) and the registry
`acrjspaceobssea0708231738` both already exist.

Nothing needs re-deriving. Execution resumes from `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea` exactly as frozen.


### Post-freeze commits and the build source SHA

The preregistration freeze is commit `e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea`.
Commits made after it in this round touch **documentation only** and never touch
any path in `RUNTIME_SOURCE_BINDING_PATHS` (24 paths) or
`IMAGE_BINDING_SOURCE_PATHS` (31 paths). Verified: the intersection of the
edited set and both binding sets is empty.

The build script derives its source SHA from `HEAD` at build time, so the
image tag may name a later commit than the preregistration commit. That is
audit-visible and intended. The invariant that matters is that every bound
source path is byte-identical to its state at the freeze, which the image
binding hashes prove independently of the commit name. No parser, gate
contract, orchestrator semantic, profile binding or membership rule may change
after the freeze, and none has.


## Parser-v3 execution state after the image build

`	ext
preregistration freeze   e3f86ae39ecefe5e6b4b68a1e9266708cd1607ea
image source commit      ec3801d39677f1568e6940c5593a7af07999a8f3
image digest             sha256:2d85fc9be656d5af992d2ec28e4749583c6c4873ce0c0c38b0e6e811d3fb1ad8
image binding sha256     c9f82d9253650f57bbe0e945027cb4c74c1ce6d29369b453d02871c022203cfb
holdout state            SEALED (unspent)
predictions              none
labels accessed          none
formal result            none
full test suite          1323 passed
`

Build host, already provisioned and ready:

`	ext
vm-pv2-orchestrator-sea   rg-jspace-observation-sea, Debian 12, running
repo clone                /home/jspaceadmin/J-space-observation (root-owned)
operator                  root, PATH=/usr/local/bin:/usr/bin:/bin
identity                  id-jspace-parser-v2-control-sea
                          clientId 3a34885b-f76c-493a-965a-6ac13c7c2530
driven from Windows by    az vm run-command invoke (output truncates at ~4 KB)
`

**The launcher must be run as root.** It writes `acr_task_run_body.json`,
`chmod 400` s it, then rewrites the same path; a non-root operator fails with
`EACCES` after the durable claim already exists, which strands the claim
permanently. Two parser-v3 build claims were stranded this way before the cause
was found.

### Remaining steps

`	ext
1. Stage P    infra/azure/scripts/10_run_parser_v3_locked_eval.sh
              PARSER_EVAL_STAGE=P
              PARSER_EVAL_RUNTIME_CONFIG_FILE=<generated>
              PARSER_EVAL_IMPLEMENTATION_MANIFEST_FILE=<generated>
              PARSER_EVAL_IMAGE_BINDING_FILE=<build record image_binding.json>
              plus the same coordination-zone variables used for the build
2. seal three prediction streams
3. labels-open transaction, then Stage E
4. formal PASS or FAIL, holdout RETIRED
5. independent claude-opus-5 reasoning=max recomputation
6. paper ledgers, commit and push
`

The runtime configuration is produced by
`scripts/create_parser_v2_runtime_config.py`, which resolves the launcher path
through `core.EVAL_RUNTIME_LAUNCHER_PATH` and therefore selects
`10_run_parser_v3_locked_eval.sh` under the parser-v3 profile.

### Warning carried into the next round

Every launch attempt takes a durable one-shot claim in the coordination zone.
A launch that dies after claiming and before dispatching strands the claim, and
a stranded launch claim cannot be recovered by any later process. Stage P must
therefore not be started without enough capacity to carry it to a sealed
prediction set in one pass. The launcher requires clean
`HEAD == origin/main`; it does **not** require `HEAD` to equal the image's
source commit, so documentation-only commits made after the build are safe as
long as no bound source path changes.

---

# HANDOFF — Phase 1.2D halted (supersedes the "Remaining steps" above)

**The remaining steps listed above must not be executed.** Phase 1.2D was
halted in preflight. The one-shot holdout is `SEALED` and unspent, no
preregistration commit was created this round, and nothing in the repository is
frozen by this round.

Read first: `reports/phase1_parser_v3_locked_evaluation.md`, then protocol §15,
then the `docs/decision_log.md` entry "Phase 1.2D — halt the parser-v3 locked
evaluation before preregistration".

## State

```
Holdout                    SEALED, unspent, 15 objects
                           phase1-evaluator-validation/parser-v3-v1/20260725T160340Z
Locked labels read         0
Predictions generated      0
Authorization lock         not created
State chain                not bootstrapped
ACA job                    job-jspace-parser-v3-locked-eval  does not exist
Formal evaluation ordinal  0
Preregistration commit     none this round
Superseded prereg commits  bdd5e10d, a38d7daa, 9e98467e
Parser v3 source sha256    76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9
Parser v3 impl commit      310277bcadd67ca9e77986fc292fae47dc5ceda2
```

Any previously built image and any generated runtime config are **stale** and
must not be reused: the protocol document changed, so the Dockerfile digest pin
changed.

## Why it stopped

The sealed parser-v3 set, the frozen scoring instrument and the parser-v3 gate
contract are three artifacts that do not describe the same thing. Nine findings
`H1`-`H9` in protocol §15.3.

The fatal one, `H9`, involves no instrument: the gate contract admits three
typed-decision labels with `null_collapse_prohibited: true` and declares
`typed_decision_support = {ambiguous: 10, no_answer: 30, present: 80}`, while
the sealed set contains a fourth class `present_unextractable` (4 cases) and a
real support of `{present: 91, no_answer: 23, ambiguous: 6}`. Strata are
correct at 12 × 10 = 120. Gates calibrated against the declared support cannot
score the real set.

Root cause: the contract was derived from the v2 contract by substitution
rather than re-derived from the v3 set — the `last_number_trap` blocks in the
two contracts are byte-identical, naming a distractor span the v3 set does not
contain.

## Do not repeat these dead ends

- Do **not** try to resolve this by namespace adaptation. `H1` (12-object v3
  layout versus the frozen 26-object registered-set layout) is not a naming
  problem.
- Do **not** drop the 15 non-projectable records. The contract fixes 120 cases,
  10 per stratum, and every gate denominator.
- Do **not** map `present_unextractable` onto `no_answer`. That is precisely
  the collapse `null_collapse_prohibited: true` forbids.
- Do **not** author a fresh scoring instrument immediately before a one-shot
  run. The frozen instrument's hash pinning is the protocol's trust anchor.

## Reusable work, already validated

Protocol §15.4 records six normalisations `N1`-`N6` that lift the frozen-valid
projection from 22 to 105 of 120, preserve all 105 typed decisions, and make
the mandatory `last_number_trap` gate non-vacuous on all 10 S06 cases. `N4` and
`N5` are the frozen instrument's own definitions, not inventions. Reuse them
once the set and contract are reconciled.

The two preflight instruments are documented in `paper/methods_ledger.md` and
must be kept: the **write-blocked dry run** and the **projection probe**.
Between them they found all five §14 findings and all nine §15 findings, every
one before any irreversible action.

## Next round, in order

```
1. Re-derive docs/phase1_parser_v3_acceptance_gates.json from the sealed
   parser-v3 set. Every support count, gate denominator and enum vocabulary
   recomputed from sealed bytes. Never inherited from v2.
2. Resolve present_unextractable explicitly: admit it with its own gate
   treatment, or rebuild those 4 cases. Never collapse it silently.
3. Reconcile the label ontology with the scoring instrument: S11
   minimum-candidate rule, ambiguous/parse_valid semantics, output_quality=empty.
4. Freeze one span convention across the set and all three parsers, with an
   artifact-level agreement test. Parsers currently emit literal-only spans;
   the set registers marker-inclusive spans.
5. Implement the artifact agreement check described in paper/methods_ledger.md,
   including the mandatory-gate non-vacuity clause. Run it before any image is
   built. It is a pure function of two sealed artifacts.
6. Only then preregister, build once, and run Stage P.
```

## Warning that still applies

Every launch attempt takes a durable one-shot claim in the coordination zone.
A launch that dies after claiming and before dispatching strands the claim
permanently. Stage P must not be started without enough capacity to carry it to
a sealed prediction set in one pass. Two stale build-claim strandings from
earlier rounds (`c2ab05c9`, `1c5ace45`) exist and must never be deleted or
concealed.

---

# HANDOFF — Phase 1.2E complete, BLOCKED (supersedes the "Next round, in order" above)

Items 1-5 of the previous list are **done in public form**, with one exception
noted below. Item 6 remains gated.

## State

```
Round type                        public tooling only
Terminal status                   BLOCKED
Blocking item                     acceptance thresholds REVIEW_REQUIRED
parser-v3-v1                      SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE
sealed_object_count               12
total_case_count                  120
residual_semantic_case_count      15
Sealed inputs read                0
Sealed labels read                0
Local private curator files read  0
Predictions generated             0
Parser invocations on locked data 0
Azure writes or resource changes  0
Formal evaluation ordinal         0
Parser v3                         unchanged, unvalidated
```

## What changed relative to the previous handoff

Item 1 changed shape. The v3 gate contract is **not** re-derived and **not**
amended. `parser-v3-v1` is retired permanently, so there is nothing to re-derive
it against. The historical contract is preserved byte-for-byte as the artifact
found defective. A future contract is a different artifact, compiled by
`parser_v3_repair_contract.compile_contract` from a prospective policy plus a
set-derived facts manifest.

Item 2 is resolved by exclusion. `present_unextractable` is not admitted to the
formal set, is never collapsed, and is permitted only in a separate research-only
corpus that is never scored.

Items 3, 4 and 5 are delivered: the three-class truth table with the `S11`
minimum-candidate rule, the `ambiguous`/`parse_valid` semantics and the
`output_quality = empty` biconditional; the literal-only span convention binding
labels, parsers, comparators, validation and scoring; and the artifact-agreement
check including the mandatory-gate non-vacuity clause.

Item 6 is unchanged and still gated.

## Where things are

```
docs/phase1_2e_parser_v3_ontology_repair_protocol.md   the protocol
docs/phase1_parser_v3_v2_evaluation_policy.json        prospective policy (REVIEW_REQUIRED)
src/jspace_observation/parser_v3_repair_ontology.py    truth table + validator
src/jspace_observation/parser_v3_repair_normalization.py  N1-N6
src/jspace_observation/parser_v3_repair_contract.py    facts, agreement, compiler
scripts/parser_v3_repair_cli.py                        facts / check / normalize / compile / verify
tests/test_parser_v3_repair.py                         122 synthetic tests
reports/phase1_2e_parser_v3_repair.md                  round report
```

## The one blocker

Numeric acceptance thresholds. There is no calibration basis: Phase 1.0C
headroom calibration is `BLOCKED` with no model run, parser-v2 constants would
import an unjustified number of the kind that produced `H9`, and any
parser-v3-derived threshold would be selected against the measurement it bounds.
They are `REVIEW_REQUIRED` in the policy and the compiler refuses to compile
while any is open.

## Next round, in order

```
1. Resolve the acceptance thresholds. Either run Phase 1.0C headroom
   calibration and derive them, or register an explicit reviewed scientific
   rationale for a threshold family that does not depend on it. Nothing below
   may start first.
2. Register the parser-v3-v2 replacement selection rules, before any private
   review. They must not condition on any parser prediction.
3. Construct parser-v3-v2 independently: 120 unique cases, 10 per stratum,
   80/30/10 supports, literal-only spans, every case passing the ontology
   validator. The 15 quarantined cases get fresh parser-blind review or
   replacement; no old semantic label may be coerced.
4. Build the set-derived facts manifest and run the agreement check. It must be
   empty before sealing.
5. Seal, then compile the contract, then verify byte-for-byte with --check.
6. Only then preregister, build the image once, and run Stage P.
```

## Traps specific to this tooling

* The tooling has **synthetic-test evidence only** (`L-29`). The first real run
  is itself untested; treat a first-run failure as a possible tooling defect
  before treating it as a set defect.
* `jspace_observation/__init__.py` eagerly imports the whole package, so
  `eval_parsing` lands in `sys.modules` for *any* repo import. The parser-free
  proof is therefore differential — importing the repair modules must add no
  module the frozen validator alone would not already have loaded. Do not
  "fix" this by asserting `eval_parsing` is absent; that assertion cannot hold.
* `scripts/parser_v3_repair_cli.py` refuses every path inside the
  `parser_v3_v1` namespace and has no override flag. That is deliberate.
* `PROTECTED_DIGESTS` in `tests/test_parser_v3_repair.py` pins eleven artifacts
  by LF-normalised SHA-256. If a legitimate future change touches one of them,
  update the pin in the same commit and say why in the decision log.

## Warning that still applies

Every launch attempt takes a durable one-shot claim in the coordination zone. A
launch that dies after claiming and before dispatching strands the claim
permanently. Stage P must not be started without enough capacity to carry it to
a sealed prediction set in one pass. Two stale build-claim strandings from
earlier rounds (`c2ab05c9`, `1c5ace45`) exist and must never be deleted or
concealed.
