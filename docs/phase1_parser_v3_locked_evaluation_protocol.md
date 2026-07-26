# Phase 1.2D — Parser v3 prospective one-shot locked evaluation protocol

This document is preregistered. It is committed and pushed **before** any
parser-v3 prediction is generated and **before** any parser-v3 locked label is
read. After the preregistration commit, the parser and the gate contract are
frozen for this evaluation.

## 1. Scope and terminal outcome

This round runs exactly one formal evaluation of parser v3 against the sealed
`parser-v3-v1` holdout. The round terminates in `PASS`, `FAIL`, or `INVALID`.
There is no "near pass", no "conditional pass", no "manual pass", and no
"mostly passed". A manual override is prohibited.

`INVALID` is reserved for integrity faults only: provenance mismatch, broken
prediction seal, label/prediction membership mismatch, scoring-code mismatch,
unauthorised overwrite, or state-chain corruption. A poor result is never
`INVALID`; a poor result is `FAIL`.

## 2. What this evaluation can and cannot establish

The holdout is 120 synthetic evaluator fixtures. Its labels are a two-reviewer
plus arbiter **LLM operational consensus**, not human ground truth. Isolation
between holdout construction and parser development is **procedural and
hash-audited, not security-enforced**.

A `PASS` would therefore support only a bounded claim: that on this fixed
120-case instrument, under this frozen contract, parser v3 met every
preregistered gate. It would not support natural model-output prevalence,
human-ground-truth reliability, or all-domain evaluator validity.

Nothing in this round is a model result. No model is run. No GPU is used. No
J-lens is fitted. Nothing here bears on hidden reasoning, an internal
workspace, or J-space.

## 3. Frozen parser identity

Parser v3 uses a non-self-referential digest scheme. The registered
`source_sha256` is **not** the raw file digest: it is SHA-256 over a domain
separator plus the UTF-8 source after newline canonicalization and after the
two provenance assignment values are replaced by 64 zeroes. Both digests are
recorded below so the two are never confused again.

| Field | Value |
| --- | --- |
| algorithm ID | `jspace-parser-v3-reference-blind-extraction/v1` |
| canonical source SHA-256 | `76dc58684f4e3818a3f557a1828571674e799f65a9f0a97d07706839ff859ea9` |
| parser version | `0ce0f3cd5e0a1d4c5b4c9eff9a2968deecd04c594f435a2fa2bfec332fd3cace` |
| raw blob SHA-256 | `dd729c3c23771fb112811e382bf7e55f531ce534cbbd1cfec4f0527056c8908e` |
| implementation commit | `310277bcadd67ca9e77986fc292fae47dc5ceda2` |
| module | `src/jspace_observation/eval_parsing_v3.py` |

`src/jspace_observation/eval_parsing_v3.py` is byte-identical at `HEAD` and at
its implementation commit; the file has not been touched by any commit in
between. The comparators are frozen the same way:

| Parser | Role | Canonical source SHA-256 | Raw blob SHA-256 |
| --- | --- | --- | --- |
| parser v2 | gating non-regression comparator | `f538add0bdd6e5a3281d0298b374a99fecea962a91a4cbaa5b4a20795d9a6918` | `fe02781545e26c2f97d1731e985d081a2f1468950bec4d88700647849243d182` |
| legacy | secondary reporting only | not applicable | `4b07b91859aca33b51af9c15b08f07026f11b0141f1300fd3f942138b731177e` |

The legacy parser predates the provenance-digest scheme and carries no
canonical identity constants, so it is pinned by raw blob digest alone.

Frozen for the whole round: `eval_parsing_v3.py`, `eval_parsing_v2.py`,
`eval_parsing.py`, the parser-v3 development fixtures, and the parser-v3
development protocol. Any parser-v3 change discovered in the working tree must
be set aside as a separate v3.1 patch and excluded from this round.

## 4. Gate contract derivation

`docs/phase1_parser_v2_acceptance_gates.json` is the sole numeric source. The
v3 contract is produced by `scripts/derive_parser_v3_gate_contract.py`, which
refuses to run unless that source file hashes to
`a51c7faa4ff6345eb3ffa78b3f1ed49e18db0ff24e4a746bf91938dc3af3f988`. No
threshold is ever re-entered by hand.

The v2 contract file itself is **not** modified. It is a member of the frozen
protocol bundle whose hash is bound into `parser_version`; editing it would
change parser v3's own identity. The v3 contract is a new, separate file and is
not added to that bundle.

Only three leaves change, and each is registered:

| Path | From | To | Category |
| --- | --- | --- | --- |
| `/schema_version` | `phase1-parser-v2-acceptance-gates/v1` | `phase1-parser-v3-acceptance-gates/v1` | candidate |
| `/status` | `preregistered_before_case_construction` | `preregistered_before_prediction_generation_and_label_access` | provenance |
| `/legacy_comparison_gates/clean_pooled_non_regression/rule` | `parser_v2_correct_count>=legacy_correct_count` | `parser_v3_correct_count>=parser_v2_correct_count` | comparator |

No container is renamed and no structural path changes. An earlier draft
renamed `/legacy_comparison_gates` to `/comparator_comparison_gates` and
rewrote `/status_logic/PASS` to match. Both were reverted after checking the
code that actually consumes the contract: `load_acceptance_gates` requires the
literal key `legacy_comparison_gates`, and the status verifier asserts the
literal string `all_absolute_and_legacy_comparison_gates_pass` **only when the
result is PASS**. The rename would have broken the loader outright and the
string rewrite would have planted a landmine that detonates on a passing run
and stays silent on a failing one. The v2-era container name is therefore
retained, and the authoritative comparator is declared by an added
`comparator` field inside each sub-gate. Four top-level provenance blocks are
added — `candidate_parser`, `comparators`, `holdout`, `derivation` — which the
loader tolerates because it checks for required keys rather than an exact
top-level key set.

The derivation script does not merely assert compatibility, it demonstrates it:
before writing anything, it loads the derived contract through the production
`load_acceptance_gates` under its own computed digest, and records
`frozen_loader_accepts_derived_contract: true`.

`docs/parser_v2_to_v3_gate_contract_diff.json` records the machine-checked
result: **numeric threshold changes 0, metric semantic changes 0, population
definition changes 0, unregistered changes 0, removed paths 0, unexpectedly
introduced paths 0**, across 52 inherited numeric leaves. Verdict
`DERIVATION_FAITHFUL`. The derivation is idempotent; `--check` re-derives and
compares byte for byte.

### 4.1 Honest statement about preregistration strength

The v2 contract was preregistered before any case existed. The v3 contract
inherits every threshold from it verbatim, but this v3 instantiation is written
after the parser-v3 holdout was constructed and sealed. The thresholds are
therefore not chosen with knowledge of parser-v3 results — no parser-v3 result
exists — but the contract is not prior to case construction in the way the v2
contract was. This is recorded as a limitation rather than smoothed over.

### 4.2 Mandatory gates

Inherited unchanged from the v2 contract: overall exact typed-decision
agreement ≥ 114/120; answer-bearing strata ≥ 9/10 each; every-stratum floor
≥ 8/10; answer-presence macro-F1 ≥ 19/20; ambiguity precision and recall
≥ 9/10; no-answer precision and recall ≥ 9/10; boxed/final misses 0 over S01
and S02; last-number-trap errors 0 over S06; wrong-span errors ≤ 1 over the
expected-present population of 80; material correctness errors ≤ 1/120 with
S01 and S02 each at 0.

Under the registered comparator substitution, the two comparison gates become:
clean-strata pooled non-regression `parser_v3 >= parser_v2` over S01, S02, S03,
S12; and critical strict improvement, requiring a net gain of at least 1 in at
least one of S04–S11 against parser v2. The second gate is retained because the
v2 contract made it mandatory against its own comparator, and the derivation
rule substitutes the comparator rather than deleting the gate. Parser v3 exists
only because parser v2 failed on critical strata, so a parser v3 that improves
on parser v2 nowhere critical is not certifiable. This is the single most
consequential derivation decision in this document and it is recorded here, in
advance, precisely because it can turn a PASS into a FAIL.

Zero-denominator metrics report `NA` and are not silently treated as passes.

## 4.3 Sealed holdout verification

The sealed prefix is
`phase1-evaluator-validation/parser-v3-v1/20260725T160340Z` in container
`jspace-results`. Twelve objects were written in registered order with
`overwrite=false`, `manifests/set_manifest.json` last.

Before any prediction, a read-only in-VNet job re-measures the prefix and must
establish: object count exactly 12; exact membership against the registered
list; `set_manifest.json` carrying both the latest `last_modified` and the
largest ETag; and a streamed SHA-256 round trip matching each recorded digest
and byte count. Label blobs are hashed chunk-wise and discarded; nothing is
decoded, parsed, printed, or retained. Listing must use a trailing slash,
because a sibling runlog prefix shares the timestamp as a string prefix and an
unslashed listing returns fourteen objects rather than twelve.

Any failure stops the round before labels are opened.

### 4.3.1 What "not overwritten" can and cannot mean here

The storage account has **no** blob versioning, **no** blob or container soft
delete, **no** change feed, **no** point-in-time restore, **no** immutability
policy, **no** legal hold, and **no** version-level WORM. There is therefore no
history object to enumerate, and this round does not claim one.

The claim "no overwrite history" is not certifiable and is not made. The sound
claim is **"no modification since seal"**, established by ETag equality: Azure
mints a new ETag on every successful write and no write path preserves one, so
an ETag equal to the value the seal job received at write time proves the blob
has not been written since. Creation time is recorded but not relied upon,
because overwriting a block blob resets creation time to equal last-modified —
the same pattern a never-overwritten blob shows — so it cannot distinguish the
two cases.

Absence of overwrite *during* sealing is established separately, by the
`overwrite=false` conditional write used on every object; that guard is not
theoretical, having already aborted one sealing attempt.

An ETag mismatch means the object was written after sealing. Because no history
is retained, the original bytes would be unrecoverable and the discrepancy
unresolvable: the instrument would be compromised, and the round would stop
without producing a PASS or a FAIL. An ETag mismatch with a matching SHA-256
would mean a rewrite with identical bytes, which is still a seal violation and
still stops the round.

## 4.4 Gate contract binding

The v2 contract is bound by its **git blob** digest at a frozen commit, not by
a working-tree file hash. The v3 contract is bound the same way. Its digest is
`2fcc323481221fbc5c1f56b5beccd238fd835303c46df61087e1483dfc28dda7`, taken over
LF bytes; `.gitattributes` registers the file as `text eol=lf` so the checked
out bytes, the blob bytes, and the digest agree on every platform. Pinning a
raw hash of an uncommitted file would be a weaker binding than the v2 analogue
and is not done: the preregistration commit lands first, and the binding refers
to the blob at that commit.


## 5. Two-stage execution

### Stage P — label-blind predictions

Stage P may read only `locked-inputs/locked_inputs.jsonl`, the frozen parser
bytes, and public manifests. It must not **read** any locked label, reviewer
judgment, arbitration record, expected typed decision, expected parsed answer,
or expected correctness.

Stage P does perform one name-only, recursive listing of the registered parent
prefix, as part of `validate_registered_parent_membership`, and that listing
necessarily enumerates the `locked-labels/*` blob **names**. This is
preregistered here rather than patched, for three reasons: the orchestrator may
not be rewritten this round; the eleven member names are hard-coded public
constants already published in this repository; and the listing result is only
ever compared for set equality, so it carries zero per-case signal. The correct
statement of the isolation property is therefore:

- `labels_content_accessed = false` — enforced by construction and, once the
  narrow identities are in place, by a storage-side 403 on any label read;
- `labels_prefix_listed = true` — a name-only integrity listing that yields no
  label value and no per-case information.

A bare `labels_accessed = false` must not be published, because the emitted
flag is a hardcoded literal rather than a derived access counter. The
substantive claim that is published is `labels_content_accessed = false`,
supported by: zero label symbols anywhere in the Stage P source; an exact-set
environment allowlist rather than a denylist; an exact blob-name assertion
restricting input reads to `locked-inputs/locked_inputs.jsonl` and its
manifest; a command-line channel scan rejecting any argument token containing
`label`, `reference`, or `correctness`; a recursive label-blindness scan of
every emitted payload; and the storage-side read condition pinned to the
`locked-inputs/` prefix.

For each of the 120 locked inputs, only `output_text` is passed to the parser.
The locked input schema is itself label-free: it carries exactly
`schema_version`, `case_id`, `source_kind`, `output_text`, `parse_type`, with
extra fields rejected, and no reference answer exists in it to leak. The parser
request is narrowed further to exactly `schema_version`, `answer_type`,
`output_text`, re-asserted in-process and again across a subprocess boundary.
Correctness is not computed in Stage P.

Three prediction sets are produced: parser v3 (120), parser v2 comparator
(120), legacy comparator (120). Each v3 prediction carries `case_id`,
`parser_algorithm_id`, `parser_version`, `parser_source_sha256`,
`answer_presence`, `parse_valid`, `parse_ambiguous`, `parsed_answer`,
`candidate_answers`, `evidence_spans`, `extraction_strategy`,
`output_quality`, `failure_reasons`, `format_warnings`, `typed_decision`, and
carries no expected label, no expected correctness, no gate outcome, and no
reference-guided candidate selection.

Completion gates: locked inputs 120; v3, v2 and legacy predictions 120 each;
unique IDs 120; duplicates 0; missing 0; extra 0; schema errors 0; prediction
errors 0; `labels_content_accessed` false.

Two registered prediction fields are satisfied by binding rather than by
storage, and this is recorded now rather than discovered later.
`parser_algorithm_id` and `parser_source_sha256` are not per-row columns; each
row carries `parser_version`, which is a SHA-256 over a canonical manifest that
already binds the algorithm ID, the normalizer ID, the protocol bundle digest,
the protocol version, both schema versions, and the source digest. The binding
is cryptographic, so adding the two columns would add no information.
`typed_decision` is likewise derived, not stored, for the candidate rows: it is
computed by the single shared `derive_typed_decision` function, which is pure
and deterministic. No field is dropped; both are equivalent by construction.

Predictions are then sealed with `overwrite=false`, manifest last, round-trip
SHA-256 and exact membership verified. After the seal, predictions are never
regenerated — not on `PASS`, not on `FAIL`, not on a persistence error.

### Stage E — one-shot label open and scoring

Stage E starts only once a valid prediction seal exists.
`labels_open_transaction.json` is written and durably persisted **before** any
label is read. From the first label read onward, `holdout_spent` is true.

The Stage E finalizer must not import `eval_parsing_v3`, `eval_parsing_v2`, or
`eval_parsing`; must not call any parser; must not modify predictions; must not
drop cases; must not change normalisation; and must not change gates. It uses
only the sealed predictions, the sealed locked labels, the frozen correctness
comparison, and the frozen gate contract.

## 6. Retry rules

Before any label is read, infrastructure faults may be repaired and Stage P may
be re-executed in full, provided no valid prediction seal exists. Every failed
attempt is retained.

Once predictions are sealed and labels are still unread, predictions are
reused exactly; only the Stage E launcher may be repaired.

Once labels are read, no parser may be invoked. The only permitted replay is a
deterministic report or persistence replay over the same predictions, the same
labels, and the same frozen finalizer, and only for an upload, serialization,
or log-retrieval fault. A metric failure is never retried.

## 7. Identity separation

Three separated identities are used. The prediction identity may read only the
parser-v3 locked-inputs prefix and write only the new prediction prefix; it may
not read locked labels, label-bearing reports, or prior scores. The scoring
identity may read the sealed prediction prefix, the parser-v3 locked-labels
prefix, and the frozen manifests, and may write only the new scoring prefix.
The control identity holds management-plane rights only and no blob data-plane
role.

Azure RBAC and ABAC are evaluated server-side per presented principal, so a
container-scope role with a prefix condition is genuinely enforced for the
identity it is attached to. The weakness is not the condition but identity
attachment: a Container Apps job can request a token for **any** identity
attached to it, so attaching a broadly privileged identity alongside a narrow
one destroys the boundary.

A standing, unconditioned, account-scope `Storage Blob Data Contributor`
assignment exists on `id-jspace-aca-acrpull-sea` and predates this project
phase. That identity is disqualified from this round. Rather than delete a
grant that dozens of unrelated existing jobs depend on, this round removes the
reachability instead: `id-jspace-aca-acrpull-sea` is **not attached to any
Phase 1.2D job**. Each task identity is granted its own `AcrPull` and serves as
both the registry-pull identity and the data-plane identity for its own job, so
no broadly privileged token is obtainable from inside an evaluation container.

Because Stage P must list the registered parent prefix for its membership
integrity check, the prediction identity's list permission is conditioned on
the parent prefix while its read permission is conditioned on
`locked-inputs/`. The result is a technically enforced content boundary: label
names are listable, label bytes are not readable. Delete is not granted, which
reinforces the `overwrite=false` discipline.

`allowSharedKeyAccess` is currently false and shared-key access is therefore
closed. Because the control identity holds resource-group Contributor and could
in principle re-enable it, `allowSharedKeyAccess` and `publicNetworkAccess` are
measured and recorded immediately before Stage P and immediately after Stage E.

Two exposures cannot be removed and are recorded as standing limitations rather
than resolved: a Microsoft Defender platform service principal holds
subscription-scope `Storage Blob Data Reader`, and the human operator holds
subscription Owner plus account-scope `Storage Blob Data Reader`. Isolation is
enforced against the job identities; it is not enforced against the
subscription operator or the platform scanner.

All temporary grants are deleted after the result and the teardown is verified
by measurement, not by assertion.

## 8. Post-result independent recomputation

After formal scoring, an independent reviewer recomputes every mandatory metric
from the sealed scoring ledger and the frozen gate contract alone. It does not
run the parser, does not re-read the raw label blobs, does not modify state,
and does not write to the formal evaluation prefix. A primary/reviewer mismatch
blocks formal publication; the holdout nevertheless remains spent.

## 9. Minimal parameterisation of the frozen v2 tooling

The v2 one-shot machinery is reused, not rebuilt. It is single-identity by
construction, so it is parameterised along exactly the axes the round permits:
candidate parser, sealed prefix, candidate/comparator mapping, evaluation ID,
and gate-contract hash.

The measurement that makes this tractable is that the candidate identity enters
the core through only **five module-level constants** —
`FROZEN_PARSER_SOURCE_SHA256`, `FROZEN_PARSER_GIT_BLOB_OID`,
`FROZEN_PARSER_VERSION`, `FROZEN_PARSER_IMPLEMENTATION_COMMIT`, and
`FROZEN_ACCEPTANCE_GATE_SHA256` — referenced from 49 sites that all read them by
name. Parameterisation therefore rebinds five definitions; it does not edit 49
call sites, and it does not touch control flow. `FROZEN_PROTOCOL_COMMIT` and
`FROZEN_PROTOCOL_BUNDLE_SHA256` are deliberately **not** parameterised: parser
v3 binds the v2 protocol bundle inside its own `parser_version`, so changing
them would contradict the candidate's own identity.

The core is not self-pinned. `RUNTIME_SOURCE_BINDING_PATHS` and
`IMAGE_BINDING_SOURCE_PATHS` list paths and hash them at runtime, so amending
the core changes a recorded binding rather than violating a frozen one. Those
two tuples are themselves profile-scoped, because a v3 run must additionally
bind `eval_parsing_v3.py`, the v3 worker, and the v3 gate contract, while a v2
run must keep binding exactly what it bound before.

Selection is explicit and provenance-bound rather than ambient. The profile
identifier is a field of the runtime config, so it is covered by
`config_sha256`, which is bound into the authorization lock and from there into
every state receipt. It is not read from the environment and not inferred, and
the v2 profile remains the default, so every existing v2 path behaves as before
unless a run explicitly selects otherwise.

Stage P runs **three** parsers rather than two, because the derived contract
scores the candidate against two comparators: parser v2 for
`clean_pooled_non_regression` and `critical_strict_improvement`, and the legacy
parser for `legacy_adapter`. Parser v2 has never been run against this holdout,
so its comparator stream must be generated here; doing so is label-blind and
leaks nothing, because v2 is frozen and its outputs depend only on inputs. The
exact-arity check that currently demands two parser callables becomes an exact
check against the arity the selected profile declares — still exact, never
relaxed.

Parser v3 executes in its own single-request isolated worker, a sibling of the
v2 worker pinning the v3 module, entry symbol, source digest, and version. The
worker is deliberately **not** argv-parameterised. Its hardcoded identity is
the security property: a worker that self-attests which parser it loaded cannot
be redirected by its caller, whereas one told what to load can. It also holds a
total environment lock, so parameterisation by environment is impossible by
design. `parse_v3` has a signature and result shape identical to `parse_v2`,
so the sibling differs only in those pinned constants.

Stage E gains `eval_parsing_v3` in its forbidden-import set. The omission is a
live hazard rather than a formality: Stage E currently blocks the candidate
parser only through the `"eval_parsing"` substring and the coincidence that v3
happens to define `compare_parsed_answer_to_reference`. The filename, its
bytecode stem, the code-name list, and the source-defines probe are all
extended, and a regression test asserts the parser-free property directly.

### 9.1 The evaluator-validation instrument is not parameterised

`evaluator_validation.py` is the immutable evaluator-validation instrument. It
is hash-pinned, it fails hard on any digest mismatch, and it is never edited. It
also hardcodes the parser-v2 sealed-family namespace — the `PV2` case-ID family
and the `parser-v2-v1` parent-prefix family — inside its own bytes.

Forking it for parser v3 would give the two evaluations two different measuring
devices, and any v2-versus-v3 difference could then be an artifact of that
difference. Instead the editable core rewrites records onto the instrument's
namespace on the way in and back on the way out. The mapping moves only the
family label; the 20-hex case suffix, and therefore case identity, is preserved
exactly. Under the parser-v2 profile the rewrite short-circuits to the identity
function before doing any work, so v2 behaviour is unchanged by construction.
Nothing translated is ever persisted: every stored artifact carries the true
parser-v3 namespace.

Receipt links need one extra step. `previous_receipt_sha256` hashes the
predecessor's exact bytes, so translation necessarily changes it; inside a
validation call the links are recomputed over translated predecessors in
dependency order, and `chain_sha256` is reported in the persisted namespace. An
independent auditor recomputing `sha256(canonical_json(receipt))` over the
stored bytes therefore reproduces every stored link.

### 9.2 Protocol binding versus candidate binding

A state receipt's `acceptance_gates_sha256` belongs to the protocol triple
alongside `protocol_commit` and `protocol_bundle_sha256`, and is **not**
profile-scoped, for the same reason those two are not: parser v3 binds the
parser-v2 protocol bundle inside its own `parser_version`, and a candidate does
not restate the protocol it is measured under. The parser-v3 gate contract is
bound in the receipt's `artifact_manifest_hashes.acceptance_gates`, and again in
the authorization manifest, the prediction request manifest, the prediction
seal, the scoring ledger, and the reported metrics. No threshold, metric
definition, population, or gate depends on the protocol-triple value. The full
statement, including the reporting obligation, is in
`docs/phase1_parser_v3_orchestrator_schema_compatibility.md` §9.

## 10. Prohibited in this round

Developing parser v4; rebuilding the locked set; re-reviewing the 120 labels;
re-running headroom calibration; running DeepSeek; running J-lens; using a GPU;
committing locked inputs, locked labels, or the full scoring ledger to GitHub;
rewriting the one-shot orchestrator; and any claim about hidden reasoning, an
internal workspace, or J-space.


## 11. Three prediction streams and their roles

Stage P produces three independent, separately bound prediction streams over
the same 120 locked inputs:

```text
candidate      parser v3     parser_v3_candidate_predictions.jsonl
comparator_1   parser v2     parser_v2_comparator_predictions.jsonl
comparator_2   legacy        legacy_comparator_predictions.jsonl
```

All three are sealed together. Their ordered case membership must be identical;
any divergence is an integrity fault.

The **gating** comparator for this contract is **parser v2**. The derived
contract's `clean_pooled_non_regression` and `critical_strict_improvement`
gates compare parser v3 against parser v2, not against the legacy parser. The
legacy stream is **reporting-only** in this round: it is carried for
non-regression narrative and paper tables, it is scored only after the holdout
has been retired, and a defect in that pass cannot alter `PASS` or `FAIL`. Its
aggregates are published in the Stage E result and report rather than in the
sealed score members.

Legacy output is never re-interpreted through a parser-v2 or parser-v3 adapter
and then presented as legacy output. Where the parser-v2 comparator has to be
expressed in the frozen comparator schema, a total, deterministic adapter is
applied to the parser envelope only, and its identity is recorded:

```text
adapter_id  jspace-parser-envelope-to-comparator-decision/v1
applies_to  parser envelopes only
```

## 12. Orchestrator schema compatibility

Historical `parser_v2_*` field names are retained for orchestration-schema
compatibility.

> Fields whose historical names begin with `parser_v2_` are retained for
> orchestration-schema compatibility. They do not identify the candidate parser
> used by the current evaluation. Candidate identity is controlled exclusively
> by the import-time profile, hardcoded worker identity, algorithm ID, parser
> version, source SHA-256 and prediction-seal bindings.

Under `evaluation_profile = parser_v3` the scoring ledger's
`parser_v2_prediction_row_*` fields hold **candidate parser-v3** rows and its
`legacy_prediction_row_*` fields hold **parser-v2 comparator** rows. Every
metrics record carries a `parser_attribution` block that names the parser behind
each field prefix; that block is authoritative, not the field name. No report
and no paper table may describe these compatibility fields as parser-v2
candidate output.

The full record is `docs/phase1_parser_v3_orchestrator_schema_compatibility.md`.

## 13. Runtime profile lock

The evaluation profile is resolved at import time, before any locked input is
read, by a loader that seeds the profile identifier into the module namespace
prior to execution. After import it cannot be changed by `argv` or by the
environment. Parser v2 remains the default profile, so every pre-existing
caller observes byte-identical behaviour.

Stage P and Stage E run from the same image and the same source digest but
through different hardcoded entrypoints and therefore different identities. The
Stage E profile denotes a **scoring** profile only: Stage E cannot load,
import, or call any parser, and the candidate parser's filename, module name,
bytecode stem, code-object names, and dynamic-import strings are all in its
deny lists.

The machine-readable record is `docs/phase1_parser_v3_runtime_profile.json`;
the derivation evidence is `docs/phase1_parser_v3_gate_derivation.json`.

## 14. Defect found and fixed before preregistration

Stage E's parser-import prohibition initially omitted parser v3 from several
exact-match deny lists and probes, and the three-stream wiring contained four
further defects that would have surfaced only after prediction generation or
after the first label read.

```text
Found and fixed before:
  preregistration
  prediction generation
  holdout access
  label access

Impact on formal evaluation:
  none
```

The defects are recorded here and in the paper's limitations and methods
ledgers rather than hidden, because they are reproducibility and
safety-boundary evidence.
### 14.1 Full defect register

Every defect below was found by pre-launch review, is fixed, and is covered by a
regression test. All of them were found **before** preregistration, prediction
generation, holdout access, and label access, so the impact on the formal
evaluation is `none` in every case.

| # | Defect | Class | Would have surfaced |
| --- | --- | --- | --- |
| D1 | Stage E's parser-import prohibition omitted parser v3 from `FORBIDDEN_FILENAMES`, the `.pyc` stem set, `_FORBIDDEN_CODE_NAMES`, and the source probe | Safety boundary | Never — it would have silently failed open |
| D2 | `scripts/parser_v3_azure_contract.py` loaded the core without seeding the profile | Profile binding | Contract generation, before launch |
| D3 | `scripts/create_parser_v2_runtime_config.py` loaded the core without seeding the profile, and hardcoded the `PV2-` / `parser-v2-v1` namespace | Profile binding | Runtime-config generation, before launch |
| D4 | `scripts/bootstrap_parser_v2_locked_evaluation.py` loaded the core without seeding the profile and hardcoded the parser source path | Profile binding | State-chain bootstrap, before launch |
| D5 | The hash-pinned evaluator-validation instrument rejected every parser-v3 case ID and parent prefix | Namespace | First validated record, before launch |
| D6 | The same instrument pinned the parser-v2 gate hash into the state receipt's protocol triple, so no parser-v3 receipt could validate | Protocol binding | State-chain bootstrap, before launch |
| D7 | Namespace translation changed receipt bytes, so `previous_receipt_sha256` links no longer matched under translation | Chain integrity | Chain validation, before launch |
| D8 | No parser-v3 state chain existed; only the v2 chain had ever been bootstrapped | Missing artifact | Launch, before any claim |

D1 is the most serious: it is the only one that would have failed **open** —
Stage E would have run and produced a formal result while the property it claims
to enforce was unenforced. Every other defect fails closed and loudly.

### 14.2 The pattern, stated plainly

D2, D3, and D4 are three instances of one defect family: a helper script loads
the profile-aware core without seeding the profile, silently gets the parser-v2
default, and then writes parser-v2 identity into a parser-v3 artifact. D3 and D4
additionally hardcoded v2 namespace literals.

That the same defect recurred three times across three independently written
scripts is itself a finding, and is reported as one. It indicates that
import-time profile seeding was, until this round, a convention enforced by
attention rather than by construction. The mitigation now applied is that every
core load asserts twice — that the resolved profile ID is the requested one, and
that a v3 load did not silently return v2 constants — so a future omission
fails at load rather than at write. That is a mitigation, not a proof: the
seeding call itself is still hand-written in each script, and a fifth script
written without it would still default to v2. It is disclosed on that basis.

### 14.3 Provenance note, not a defect

The launcher derives its Azure Container Apps job name with a hardcoded `pv2-`
prefix on both profiles, so a parser-v3 Stage P job carries a name that does not
distinguish it from the retired parser-v2 round. No identity, hash, or gate
depends on the job name; the launch-domain digest binds the parser-v3 image
digest and config. It is recorded because a reader inspecting Azure resource
names alone could otherwise misattribute the execution.
