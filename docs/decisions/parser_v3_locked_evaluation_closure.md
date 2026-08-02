# Decision — the parser-v3 locked-evaluation program is closed

**Decision ID:** `DEC-PARSER-V3-CLOSURE`
**Recorded:** 2026-08-02
**Authority:** `docs/prompts/phase_science_restart_after_parser_closure_prompt.md`
(SHA-256 `5bc137c42c68e1b85b4cad1d45e1b4bf54fb68e2899f27bc6338dae61e9ef162`),
executed at commit `ea2bce81defe9063bde2be58ada0e747d2a34c03`.

**Parser subproject state:** `CLOSED_NONAUTHORITATIVE_TRIAGE_ONLY`
**Global project state:** `SCIENTIFIC_MAINLINE_RESTART_AUTHORIZED`

---

## 1. The old bound was honored and its record is immutable

The parser-v3-v2 round operated under
`docs/prompts/phase_a3_b_to_d_cloud_execution_prompt.md`, whose section 5.4
permitted at most two independent audit/remediation cycles. Both cycles ran.
The second cycle, against exact commit
`423d16a7b486b8c22fa58a733ffa6a03b389f0fe` and tree
`3080241e68dc007e91f49967beebbd80ff1d4ec6`, returned four BLOCKER findings and
one MAJOR finding. No third cycle was attempted, and the round terminated at
`BLOCKED_ON_PUBLIC_PROTOCOL_FREEZE`.

That terminal state was correct under that authority and is **not** revised,
softened, or reinterpreted here. This decision changes what the project does
next; it does not change what the parser round concluded.

The following bytes are preserved unchanged by this decision. Any future
divergence in these digests is a defect, not an update:

| Artifact | SHA-256 | Bytes |
| --- | --- | --- |
| `docs/phase1_2h_r2_phase_a_public_audit_terminal_receipt.json` | `ef4273e102543ccbdec870a016c43461583687d77b0b0b3e3e6cc74f2c85f76d` | 4999 |
| `docs/audits/phase_a_public_audit_a_report.json` | `bc9ec0e3db9640fd200cc786adb787e8c5c3657c763b7299c139c4f109a5871d` | 18834 |
| `docs/audits/phase_a_public_audit_b_report.json` | `2b55670c7c59ee74ab1351246f0450b64fa68becd5c0ad59c7e1c638bba4f3ef` | 20112 |
| `docs/audits/phase_a_public_audit_a_round2_report.json` | `f5a40d3a88f1977de6afb098b9c7109832e2b32679ef3d513018cedddec2d0f5` | 16473 |
| `docs/audits/phase_a_public_audit_b_round2_report.json` | `4be4cf1ee04976ff69b9fc666287fd5304cd13520ae742e1acb3a9dca8b6d364` | 15243 |
| `docs/phase1_2h_r2_acr_baseline_receipt.json` | `3a28598fc9820d7188a6bb7634717fed0651eaba788d3c77927930416e240468` | 13292 |
| `docs/phase1_2h_r2_phase_a_lifecycle_receipt.json` | `30a936571cda0fc40a62aa43564d12bafa4c819698be5c88961aec81532d01d3` | 18635 |
| `docs/phase1_2h_r2_phase_a_construction_evaluation_receipt.json` | `24a3cbec462b6e37d63c187cfe5593db55cf373f1500d3512c37a29a771d4322` | 17005 |

The failed candidate commit `423d16a7…`, the terminal record commit
`ea2bce81…`, the sealed parser-v3-v1 objects under
`phase1-evaluator-validation/parser-v3-v1/20260725T160340Z/`, and the retired
parser-v2 holdout are all retained. Nothing is deleted, rescored, reopened, or
rewritten.

## 2. Parser v3 was never validated, and no parser-v3 scientific result exists

Parser v3 has development-gate evidence (`EV-0006`) and a sealed but unspent
holdout (`EV-0007`). It has no locked evaluation, no prediction, no score, and
no formal ordinal. `parser-v3-v1` remains
`SEALED / UNSPENT / UNSCORABLE / RETIRED_AS_INELIGIBLE`; `parser-v3-v2` never
reached a freeze. Every parser-v3 scientific counter in the project ledgers is
zero and stays zero.

Consequently there is no parser-v3 result to defend, withdraw, or promote. The
closure removes an *unfinished instrument*, not a finding.

## 3. Why closure is the correct move, not an evasion

`paper/limitations_ledger.md` `L-01` already held that no automatic parser
output may be treated as a final label anywhere in this project, and that every
downstream label that matters must be semantically adjudicated. Under this
decision `L-01` is **elevated from a temporary limitation to a binding project
design rule** (`DR-01`).

That elevation dissolves the premise of the whole locked-evaluation program.
The program existed to license automatic parsing as an authoritative final
label. If semantic adjudication is authoritative *by design*, then:

- a validated parser is no longer a prerequisite for any scientific label;
- a validated parser is no longer a prerequisite for any downstream experiment;
- continuing to build private holdouts, private review boundaries and audit
  cycles would purchase an authority the project has decided never to use.

The honest reading of the second audit cycle is not "the protocol was nearly
right." It is that four BLOCKER-class properties — Stage E member-ID
uniqueness, genuinely atomic create-only state, a structurally closed
construction target, and keyed schema-array uniqueness — cannot be established
by pure functions over caller-supplied evidence. Closing the program states
that plainly rather than spending further rounds approaching it.

## 4. What this decision does not do

This decision opens nothing. It creates no private holdout, reads no private
label, generates no prediction, produces no Stage P or Stage E result, consumes
no formal ordinal, and deploys no private boundary. All scientific counters
attached to the parser program remain at zero.

It also does not claim the parser work is publishable. The parser-v3 code,
tests, schemas, entrypoints, boundary IaC and audit tooling are retained as
historical and methodological artifacts. They are not deleted; they are also
not improved, extended, or re-audited under this authority. Whether any of it
ever becomes a methods paper is a separate decision that this record does not
make (`DR-05`).

## 5. What replaces it on the critical path

The scientific mainline resumes:

1. **S1 / Phase 1.0D** — repair the Phase 1.0C headroom run under a new
   protocol and artifact namespace, with the literal `<answer>` placeholder and
   the 512-token cap treated as two separate preregistered generation-profile
   defects, and with authoritative semantic adjudication.
2. **S2** — fit a materially larger, full-layer J-lens on a deterministic public
   pretraining-like corpus.
3. **S3** — execute a preregistered J-lens validity benchmark against known
   intermediates and causal controls. Matrix convergence is diagnostic and is
   never a substitute for functional validity.
4. **S4** — conditional on S1 and S3, run the first bounded RQ2 strict-no-CoT
   mechanistic pilot.

A negative headroom result, a non-converged lens, or a failed validity gate is
a scientific result under this authority, and is never a reason to start
another evaluator or audit-infrastructure project (`DR-06`).

## 6. Superseded planning material

The previously drafted `phase1_2h_rd1_public_protocol_refoundation_prompt.md`
public-protocol-v2 refoundation is superseded and must not be executed. It is
not present in this repository at the time of this record; if it is added later
as a planning artifact, it must carry a pointer to this decision and must
remain unexecuted.

`docs/prompts/phase_a3_b_to_d_cloud_execution_prompt.md` and
`docs/prompts/phase1_2h_r2_to_1_2j_cloud_execution_prompt.md` are retained as
the historical authorities of the closed rounds. Neither is the active
execution authority any longer.
