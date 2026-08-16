# Study 4F terminal disclosure

> **Registered final state:** `STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE`
>
> The authoritative router is [`STATUS.json`](STATUS.json). Study 4F published a complete,
> mechanically validated instrument and then stopped at the section 4 resource-route proof. **No bank
> was realized, no seal was created, no weight was acquired and no model was called.** No cell was
> executed, so Study 4F produced **no scientific result of any kind**.

## 1. Predecessor-execution audit

The session began by auditing what the previous prompt actually executed.

| check | finding |
| --- | --- |
| fetched `origin/main` | `f3935293d29dac6df0277179ebcdf9f5778d304b` |
| Study 3R focused-review terminal commit | `08c01ff4753b98ad0f43843fc49c93fac68c89da` (tree `0dbf9ab3…`, verified) |
| change from `08c01ff…` to `origin/main` | exactly one path: `studies/study3r/prompts/study3r_terminal_closure_authority.md` |
| authority bytes / SHA-256 / blob | `9236` / `5daf943c…5f3a99` / `4ffb7289…` — all three verified |
| commits between | 1, linear, zero merges |

**Classification: `AUTHORITY_ONLY_PARTIALLY_EXECUTED` (State A).** The predecessor committed the
terminal-closure authority alone and executed none of its sections 4–9.

### Step matrix

| step | before | after |
| --- | --- | --- |
| terminal-closure authority published | ✅ | ✅ |
| authority committed alone first | ✅ | ✅ |
| terminal closure Markdown created | ❌ | ✅ |
| terminal closure JSON + schema created | ❌ | ✅ |
| authoritative `STATUS.json` + schema created | ❌ | ✅ |
| closure tests created and passed | ❌ | ✅ (98 passed) |
| Study 3R README terminal routing updated | ❌ | ✅ |
| full-suite differential completed | ❌ | ✅ (`8 failed, 5,120 passed, 16 skipped`) |
| final closure disclosure published | ❌ | ✅ |
| final lifecycle state reached | ❌ | ✅ |
| model / scientific operation counters | all zero | all zero |

The Study 3R closure was completed under the **existing** authority, resuming sections 4–9. The
authority was not recreated, edited or recommitted.

## 2. Study 3R final closure

| item | value |
| --- | --- |
| final closure commit | `ee8a852111d27cb39bf21743e18857485cff1efe` |
| final closure tree | `8b4127139e1cbbd4ffb2ccc1cb1af075c511d6a1` |
| final lifecycle state | `STUDY3R_TERMINAL_CLOSURE_COMPLETE_RESEARCH_QUESTION_UNANSWERED` |
| `active_protocol` | `null` |
| every execution / repair / amendment flag | `false` |
| successor authorized by Study 3R | `false` |
| evidence ledger | still ends at `EV-0016` |
| scientific result | none |
| claim about the presence or absence of J-space | none |

No rejected Study 3R candidate byte and no review byte was changed.

## 3. Study 4F commits and paths

| commit | contents |
| --- | --- |
| `7d5ff0837d77af9e6df9f49d580ec0e42bdc2729` | the Study 4F authority, **alone** |
| `0dbd135…` | protocol, schemas, generators, parsers, state machine, statistics, tests |
| this commit | shakedown disposition, `STATUS.json` + schema, README, this disclosure |

Authority identity: `17822` bytes, SHA-256
`bafba585ba4fe0030f2bae14e7be8d2f060732e56b3696422102605668de0773`, Git blob
`2f120b05893ed2f09b07c3ebd2a99f23c536c752`, parent `ee8a852…`, parent tree `8b412713…`, resulting
tree `be74ae0e…`.

The only path modified outside `studies/study4f/` is `tests/test_study3r_operator_governance.py`,
which admits exactly one new namespace, `studies/study4f/`, bound to the Study 4F authority commit.
Study 3R finding F-10 recorded that this module had previously widened its own scope predicates, so
the admission is deliberately narrow and is itself asserted by a Study 4F test.

## 4. What was mechanically validated

All of the following passed on **synthetic non-study fixtures**, before any resource commitment:

* separate D2 and D3 single-family banks, 104 unique eligible items each, exact allocation;
* answer labels A/B/C/D exactly 26 each per bank, and exactly 15 each in the deterministic first 60;
* zero cross-bank and zero cross-depth duplicate content hashes across all 208 items;
* no answer or answer-derived field reaches either rendered prompt;
* the copied `W1_RAW_DIRECT` surface reproduces the byte hash the Study 3R review verified;
* the full decoding contract on both routes, with no inherited or unspecified field;
* `alpha_global = 1/20`, `m_max = 16`, `alpha_per_cell = 1/320`, recomputed independently of the
  production module;
* CoT cell `n = 104`, boundary `90`, exact size `0.0029878 ≤ 1/320`, exact power `0.9055 ≥ 9/10`,
  and both `n` and boundary shown minimal;
* E0 cell `n = 60`, boundary `41`, exact size `0.0031088 ≤ 1/320`, exact power `0.9075 ≥ 9/10`,
  and both `n` and boundary shown minimal;
* E0 and CoT parser mutation tests, including every rejected surface variant;
* the candidate-local ladder simulated over **every** pass/fail pattern, confirming a failure by
  `RP_B1` never blocks `RP_B2` or `RP_B3`;
* the seven coordinated mutations reported by the Study 3R review, each killed or rendered
  structurally inapplicable and tested as such;
* Study 3R closure, candidate and review bytes byte-identical to `ee8a852…`;
* the eight standing repository failure node IDs unchanged;
* `paper/evidence_ledger.csv` unchanged, still ending at `EV-0016`.

### The seven Study 3R survivors

| mutation | Study 4F disposition |
| --- | --- |
| `adv_cot_parser_regex_unanchored` | structurally inapplicable — the CoT parser uses exact string equality, with no regex to unanchor |
| `adv_d2_d3_ceiling_mix_drops_depth_three` | structurally inapplicable — there is no ceiling bank and no mixed bank |
| `adv_d2_d3_family_mix_drops_depth_three` | killed — a D2 item inserted into the D3 bank fails the validator |
| `adv_d3_family_depth_relabelled` | killed — depth is recomputed from the item's own arity, never read from the label |
| `adv_forced_reasoning_closure_changed` | killed — setting a closure on either route fails preflight |
| `adv_forced_reasoning_closure_removed` | structurally inapplicable — both routes register the closure as explicitly absent |
| `adv_surfaces_closure_emptied_while_rendered_bytes_unchanged` | structurally inapplicable — there is no declared closure, and the surface bytes themselves are hashed |

## 5. Shakedown and its disposition

One shakedown attempt of the three permitted; **zero** of the six permitted accelerator-hours used.

| check | result |
| --- | --- |
| environment and dependency availability | pass — `torch 2.12.0+cpu`, `transformers 5.13.0`, `tokenizers 0.22.2`, `safetensors 0.8.0` |
| renderer/parser I/O | pass |
| deterministic seed plumbing | pass |
| stub-result state-machine routing | pass |
| logging and artifact recovery | pass |
| **memory fit / unquantized resource route** | **fail** |
| checkpoint download and checksum | not reached |
| unquantized load/unload | not reached |

### The resource-route proof

Section 4 requires proving, **before weight acquisition**, that one accelerator can hold the 32B
checkpoint, the maximum registered KV cache and a fixed safety reserve without offloading.

| quantity | value |
| --- | --- |
| RP_B3 weights, bfloat16, unquantized | `64,000,000,000` bytes |
| maximum registered KV cache (4096 + 512 tokens, batch 1) | `1,207,959,552` bytes |
| fixed safety reserve | `4,294,967,296` bytes |
| **total required on one accelerator** | `69,502,926,848` bytes = **64.73 GiB** |
| accelerators visible | **0** |
| qualifying accelerators | **0** |
| torch build | `2.12.0+cpu` |
| `nvidia-smi` present | no |

No white-listed fix can supply an accelerator, and section 4 forbids the alternatives outright.
**No quantization, no sharding, no CPU offload, no disk offload, no `device_map="auto"` and no
unregistered model substitution was attempted.** The registered state is therefore:

`STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE`

Because the shakedown did not pass, the banks were **not** realized, no execution seal was created,
and developmental execution authorization remains `false`.

## 6. Scope expiries, recorded not repaired

Four assertions expired during this work. All four are **scope predicates over
`git diff <old commit> HEAD`**, so they hold only while HEAD is the commit they were written at and
expire the moment any authorized commit is added after it — the same expiry that already retired
`tests/test_study3_v0_7_focused_review.py::test_the_review_changed_no_reviewed_or_historical_path`.

Every one of the affected modules is **byte-identical** to the Study 3R closure head, so none was
repaired, edited or suppressed.

| expired assertion | in the baseline? | introduced by | guarantee carried forward by |
| --- | --- | --- | --- |
| `…single_focused_review.py::test_every_review_path_is_additive_and_inside_the_reviews_directory` | no | the inherited authority commit `f393529…`, before this session began | `…::test_every_study3r_byte_is_identical_to_the_closure_head` |
| `…test_study3r_terminal_closure.py::test_the_closure_only_added_its_own_paths_and_touched_one_readme` | no | publishing the Study 4F authority alone | `…::test_study4f_added_paths_live_only_in_its_own_namespace` |
| `…single_focused_review.py::test_the_review_changed_no_candidate_or_protected_path` | no | the governance scope admission | `…::test_the_governance_change_is_a_scope_predicate_only_change` |
| **`tests/test_study3r_protocol_v1.py::test_the_authoring_session_wrote_nothing_outside_the_study3r_namespace`** | **yes** | publishing the Study 4F authority alone | `…::test_no_expiry_hides_a_moved_study3r_byte` |

### The repository suite

| head | result |
| --- | --- |
| Study 3R closure head `ee8a852…` | `8 failed, 5,120 passed, 16 skipped` — the registered baseline, exactly |
| this Study 4F head | `9 failed, 5,119 passed, 16 skipped` |

The **eight standing failure node IDs are unchanged**. The ninth is the fourth expiry above, and it
is **structurally unavoidable**: that assertion permits only the Study 3R authored path set plus
anything inside `studies/study3r/`, while the Study 4F authority requires publishing an instrument
outside that namespace — and the module is a candidate test that section 11 of this authority and
section 3 of the Study 3R terminal-closure authority both forbid editing. There is therefore no
publication of Study 4F that leaves it passing, and no repair that does not change a protected byte.
It is recorded here rather than repaired or suppressed.

### The governance scope admission

`tests/test_study3r_operator_governance.py` carries two predicates enumerating the namespaces an
authorized session may add paths inside. They reject every path outside `studies/study3r/`, so
admitting the Study 4F namespace **strictly reduced** the damage: without it, two further tests
inside the registered baseline would also have failed, giving eleven rather than nine.

The module lists itself in `AUTHORING_MODIFIED`, so it is the designated place to carry these scope
guarantees forward. The change adds one namespace constant and rewrites two predicate expressions. A
Study 4F test proves mechanically, by comparing the parsed syntax trees before and after, that it:

* adds **0** tests and removes **0** tests;
* changes **0** assertions;
* leaves `REJECTED_CANDIDATE_PATHS`, `REVIEW_ARTIFACTS`, `PROTECTED_HISTORICAL`, `GOVERNANCE_ADDED`,
  `GOVERNANCE_MODIFIED`, `AUTHORING_ADDED` and `AUTHORING_MODIFIED` **byte-for-byte identical**;
* admits exactly one namespace, `studies/study4f/`, and **no** individual path.

The Study 3R focused-review module classifies that governance module as a candidate path, which is
why the admission expires the review module's third assertion. It is disclosed here rather than left
implicit because Study 3R finding **F-10** recorded a previous *silent* self-widening of these same
predicates.

Substantively, nothing moved: `git diff ee8a852…HEAD` touches **no** path under `studies/study3r/`,
and leaves `paper/evidence_ledger.csv`, `.gitattributes` and `tests/test_study3r_protocol_v1.py`
untouched.

## 7. Executed cells and skipped cells

**Zero of the sixteen registered cells were executed.** All sixteen are skipped for one registered
reason: `STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE`, reached before weight acquisition.

| checkpoint | depth | route | status |
| --- | --- | --- | --- |
| `RP_B1`, `RP_B2`, `RP_B3`, `RT` | `D2`, `D3` | `C1_LONG_GENERATED_COT_HEADROOM` | skipped — resource route unavailable |
| `RP_B1`, `RP_B2`, `RP_B3`, `RT` | `D2`, `D3` | `W1_RAW_DIRECT` | skipped — resource route unavailable |

Per-cell reporting (correct, incorrect and unparseable counts, exact binomial tail, pass/fail,
parser-validity rate, output-label distribution, generated-token count, accelerator time, container
and seal hashes) is **not applicable**: no cell ran and no seal exists.

## 8. Counters

| counter | value |
| --- | --- |
| checkpoint downloads | 0 |
| weight files acquired | 0 |
| model constructions | 0 |
| forward passes | 0 |
| prefill operations | 0 |
| generations | 0 |
| generated tokens | 0 |
| GPU seconds / accelerator hours | 0 / 0 |
| **D0 runs** | **0** |
| **logit readouts** | **0** |
| **activation captures** | **0** |
| **activation patches** | **0** |
| execution seeds drawn | 0 |
| study banks realized | 0 |
| RP-B selections | 0 |
| evidence-ledger rows written | 0 |
| GitHub Actions runs | 0 |
| cells executed | 0 |

`paper/evidence_ledger.csv` is unchanged, SHA-256
`3821730c45b7a58d3c582b38ba354eae77558fa4d419a51e9ff4fdf120411ff1`, tail `EV-0016`.

## 9. What this state does and does not establish

### It establishes

1. A complete, published and mechanically validated Study 4F instrument exists — separate
   single-family D2 and D3 banks with an exact answer-label allocation, two fully frozen decoding
   contracts, exactly sixteen Bonferroni cells at `alpha_per_cell = 1/320`, and a candidate-local
   ladder.
2. The registered unquantized single-accelerator route for the 32B checkpoint could not be proven on
   this host.
3. No prohibited fallback was taken to proceed anyway.

### It does not establish

1. **Nothing** about whether any registered checkpoint has generated-CoT task headroom on D2 or D3.
2. **Nothing** about whether any registered checkpoint shows zero-generated-reasoning-token expressed
   competence.
3. **Nothing** about whether a natural positive-reference candidate exists in the registered ladder.
4. **Nothing** about whether J-space exists, is observable or is unobservable.
5. **Nothing** about whether the raw direct-answer interface is valid or invalid.
6. **Nothing** about whether any model can or cannot reason internally.
7. **Nothing** that generalizes beyond the registered checkpoints, depths and interface.

No `RP_B_DEVELOPMENTAL_CANDIDATE_PENDING_CONFIRMATION` was identified, and no RP-B was confirmed —
Study 4F could not have confirmed one in any case.

## 10. Next action

Study 4F stops here, in exactly one registered state. Resuming requires one accelerator able to hold
the 32B checkpoint, the maximum registered KV cache and the fixed safety reserve without offloading.
The published instrument may then be reused unchanged from the shakedown step. Quantizing, sharding
or offloading to proceed is prohibited and would not be the registered study.

`STUDY4F_UNQUANTIZED_RESOURCE_ROUTE_UNAVAILABLE`
