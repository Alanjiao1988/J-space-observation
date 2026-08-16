# Study 3 v0.7 — terminal operator decision required

> **Terminal state:** `STUDY3_V0_7_TERMINAL_OPERATOR_DECISION_REQUIRED`
>
> No v0.7 candidate is published. No estimand, threshold, sample size, registry,
> schema or protocol byte was changed. The drafting party stopped at the first
> binding requirement that cannot be satisfied without an operator-level choice,
> exactly as section 0 of the authority directs.

Authority:
[`../prompts/study3_v0_7_consolidated_amendment_authority.md`](../prompts/study3_v0_7_consolidated_amendment_authority.md)
(23,782 bytes, sha256 `3ec79dfc…c98bc`, LF only, one trailing newline).

Machine-readable form:
[`v0_7_terminal_operator_decision_required.json`](v0_7_terminal_operator_decision_required.json).

Reproducible evidence:
[`../analysis/v0_7_protocol_placement_probe.py`](../analysis/v0_7_protocol_placement_probe.py)
and its committed output
[`../analysis/v0_7_protocol_placement_probe.json`](../analysis/v0_7_protocol_placement_probe.json).

## 1. The blocking contradiction

Section 5 requires updating three active normative protocol files. One of them
cannot be changed by a single byte without breaking a historical P0 artifact
that sections 3 and 8 protect.

The probe establishes this mechanically rather than quoting the v0.6 amendment's
prose account of the same constraint. For each file it perturbs one benign
trailing space, runs the committed regeneration checks, restores the original
bytes and verifies the restoration by SHA-256.

| protocol file | bytes | amendable | check broken by one benign byte |
| --- | ---: | --- | --- |
| `interface_calibration_protocol_draft.json` | 418,733 | **no** | `p0_freeze_corpus.py --check` |
| `interface_calibration_protocol_draft.md` | 120,132 | yes | none |
| `interface_calibration_protocol.schema.json` | 137,495 | yes | none |

The binding is a single immutable artifact:
`studies/study3/pilot/p0/corpus/p0_corpus_manifest.json` records the protocol
JSON at `generator_and_renderer_identities/binding_protocol_draft`, path and
sha256 `1197e087…3c7ca7`. `p0_freeze_corpus.py` recomputes that field from the
live file, so any edit makes the committed manifest stop reproducing and fails
`tests/test_study3_p0_feasibility_pilot.py::test_frozen_corpus_re_derives_byte_exactly`.

The three requirements are therefore not jointly satisfiable:

* **section 5** — update `interface_calibration_protocol_draft.json`;
* **section 3** — do not alter historical manifests;
* **section 8** — publish no passing state with a waived decision-bearing test.

## 2. Why the update cannot be avoided inside the JSON

The protocol JSON is **draft-v0.5**, not v0.6. Its schema pins two `const`
values and forbids unregistered fields:

| constraint | value |
| --- | --- |
| `schema_version` | const `study3-interface-calibration-protocol-draft-v0.5` |
| `state` | const `STUDY3_INTERFACE_CALIBRATION_PROTOCOL_DRAFT_V0_5_COMPLETE_AWAITING_FOURTH_INDEPENDENT_METHODS_REVIEW` |
| `additionalProperties` | `false`, over 40 required top-level keys |

A v0.7 amendment must move `schema_version`, `study_identity.draft_version` and
`state`, and section 6 registers new decision-bearing objects — `E0`, `D0`, the
canonical generated-CoT ceiling, the RP-B ladder, RP-M, the wrapper-only matched
contrast and the recursive-manifest seal — none of which exist as registered
keys today. Every one of those edits changes the frozen bytes. There is no
formulation of a v0.7 protocol update that leaves the JSON byte-identical.

Draft-v0.6 met the same wall and resolved it by registering its normative
content **entirely in a versioned rendering registry**, leaving the three
protocol files byte-identical. It disclosed that placement in its section 7a and
asked the focused review to decide "whether the v0.6 registry is a sufficient
normative home … or whether a different arrangement is required." That question
was never answered, and the v0.7 authority's four recorded audit exceptions do
not carry it forward.

## 3. The choice belongs to the operator

The three ways out have different consequences for the P0 corpus provenance
chain, so none of them is a drafting decision.

**Option A — register the v0.7 registry as the normative home.**
Author `interface_calibration_rendering_registry_v0_7.json` and its schema as
the normative carrier, update the protocol Markdown and schema, and leave the
protocol JSON byte-identical. This follows the v0.6 precedent and keeps every
historical artifact reproducing. It requires the operator to relax section 5's
literal three-file list, and it leaves Study 3 with a normative surface split
across a v0.5 JSON and two versioned registries.

**Option B — authorize regenerating the P0 corpus manifest.**
Edit the protocol JSON and regenerate
`studies/study3/pilot/p0/corpus/p0_corpus_manifest.json`. Section 3 currently
forbids this. It would break the byte-identity of an immutable artifact that
several published P0 receipts and images bind, and the consequences for those
downstream bindings would have to be assessed before, not after.

**Option C — authorize re-scoping the frozen-corpus test.**
Retire or narrow `test_frozen_corpus_re_derives_byte_exactly` so the protocol
JSON is no longer byte-bound. Section 8 currently forbids publishing with a
waived decision-bearing test, and this test is the only mechanical guarantee
that the frozen P0 corpus still re-derives.

The drafting party makes no recommendation among these, and has changed nothing
that would presuppose one.

## 4. What this session did and did not do

Published, in order, as linear descendants of the starting commit:

1. the authority, alone, as required by section 1.1;
2. the deterministic placement probe;
3. this disposition and its machine-readable form.

Not done: no v0.7 amendment, registry, schema, protocol edit, design-statistics
recalculation, decision table, recursive-manifest specification, test or
mutation test. No focused review was performed or simulated. No v0.8 was
drafted.

Zero operations of every prohibited class: no Azure, ACR, ACA, GPU or cloud
operation; no tokenizer construction, encode or decode; no checkpoint
resolution, download or load; no prefill, forward pass, logit read, scoring or
generation; no model-output parsing; no seed draw, bank generation, split
realization or confirmation access; no interface qualification or selection; no
RP-B or RP-M qualification; no evidence-ledger addition; no scientific-evidence
claim.

`paper/evidence_ledger.csv` is byte-identical and still ends at `EV-0016`.
`formal_execution_authorized` remains `false`. Study 3 remains unfrozen,
unselected and unexecuted, and the research question remains unanswered.

## 5. Inherited P0-R2 disposition, recorded without repair

Generation-2 live replay mechanically passed and was independently
reconstructed; bounded pilot authorization failed; no GPU job was created or
started; model, tokenizer, scoring and GPU counters remained zero; the evidence
ledger remained at `EV-0016`; the research question remained unanswered.

The four governance audit exceptions are recorded, and no historical file was
repaired to remove them:

1. aggregate attempt-ledger and handoff counts predate the final
   live-prefix/replay operations and are not a complete final aggregate,
   although the individual terminal receipts exist;
2. committed Phase-B/preflight evidence binds an earlier head and lock; no
   committed artifact proves the entire 38-condition admission result at the
   exact replay anchor;
3. the final hard-kill job used an empty `CUDA_VISIBLE_DEVICES` value although
   the authority literally specified `-1`; the safe no-GPU intent was preserved,
   but literal byte-level compliance cannot be claimed;
4. the current Git DAG establishes linear history and no merge, but historical
   force-push count is `UNKNOWN` without an independent GitHub audit log.

The legal characterization is therefore
`P0_R2_G2_TERMINAL_VERIFIED_WITH_AUDIT_EXCEPTIONS`. This disposition does not
write "full authority compliance verified" or "zero force-pushes verified".

## 6. The only legal next action

One operator decision among options A, B and C in section 3, issued as a new
authority. This session drafts no v0.7 candidate and no v0.8, and performs no
review.
