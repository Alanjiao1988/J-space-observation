# Stage P0-T — tokenizer and renderer gate: disposition

> **Emitted terminal disposition:** `STUDY3_P0_STOPPED_NO_EXECUTABLE_CONTRAST_FOR_EVERY_TARGET_ROLE`
>
> Published exactly as emitted. No fix-and-rerun is authorized, and no observed
> value in `p0_tokenizer_gate_result.json` or `p0_tokenizer_gate_receipt.json`
> has been edited, relabelled or replaced.

Authority: [`../../../prompts/study3_p0_feasibility_pilot_authority.md`](../../../prompts/study3_p0_feasibility_pilot_authority.md) §7.

| field | value |
| --- | --- |
| run id | `20260810T053804Z` |
| ACR run | `cmej` |
| bound commit | `d331b3e774168eec99ad849e983bfe021aebc464` |
| bound tree | `395a5676c1fd481ee20885eedce8b83024555ece` |
| worktree dirty | `0` |
| image | `j-space-observation-study3-p0@sha256:81f55870787d76bb556b071451676ee57a9fea9dc1de545463af30e830271dcf` |
| device | CPU only; `cuda_available=false`, `cuda_device_count=0` |
| wall seconds (census) | `10.05` |

## Counters (cumulative, non-resettable)

| counter | value | cap |
| --- | --- | --- |
| `tokenizer_encoded_sequences` | 4,956 | 10,000 |
| `distinct_tokenizer_identities_constructed` | 3 | 3 |
| model downloads, weight loads, prefill, decode, generation, scored rows | 0 | — |
| GPU jobs, provider calls, seeds, bank rows, positive-reference operations | 0 | — |

4,902 member encodes + 54 candidate-surface encodes = 4,956, exactly the planned
count. 1,634 encodes per role, identical across `RT`, `RL` and `RI`.

## Tokenizer identities

| role | repository | revision | class | vocab | len |
| --- | --- | --- | --- | --- | --- |
| `RT` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` | `LlamaTokenizerFast` | 151,643 | 151,665 |
| `RL` | `Qwen/Qwen2.5-Math-1.5B` | `4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2` | `Qwen2TokenizerFast` | 151,643 | 151,665 |
| `RI` | `Qwen/Qwen2.5-Math-1.5B-Instruct` | `aafeb0fc6f22cbf0eaeed126eff8be45b0360a35` | `Qwen2TokenizerFast` | 151,643 | 151,665 |

Every tokenizer was loaded from the same repository identity and the same
immutable revision as its model, with `trust_remote_code=false`. No branch, tag,
floating cache entry or substituted tokenizer was used.

## What passed

* **Independent implementation (authority §2, question 1).** The P0 renderer,
  written from the binding registry alone, instantiated every applicable
  surface. All 4,902 member encodes round-tripped through `decode(encode(x))`
  byte-exactly, so no unregistered normalization, whitespace repair, truncation,
  BOS/EOS insertion or chat template was in effect for any role.
* **Pair token-ID distinctness (authority §7.1).** **Zero** byte-distinct
  applicable pairs produced identical full token-ID sequences, anywhere in the
  census, for any role. 2,451 tokenized rows across the frozen corpus and the
  complete deterministic rendering-fixture census, including all 32 registered
  nuisance-support states.
* **S1 candidate eligibility.** The four registered label surfaces map to four
  distinct single token IDs under **every** role, for **both** alphabets:
  `ALPHA-1` → `362, 425, 356, 422`; `ALPHA-2` → `467, 1599, 809, 1863`.
* **Structural absence.** 14 `S2`/`S3` × `K6-SEP` rows were recorded as
  structural absence with no members. None was instantiated, duplicated onto
  `R-base`, or counted.
* **`S3` is a scoring rule, not a surface.** Zero `S2`/`S3` parity mismatches:
  identical prompt bytes and identical token IDs for every matched row.
* **Prompt-length census.** Token counts ranged 18–139, mean 67.4.

## What failed, and why the stage stopped

**`S2` and `S3` are `INELIGIBLE_TOKEN_IDS` for all three target roles.**

The registered `S2`/`S3` candidate surfaces carry exactly one leading space and
are scored at the single next-token position after the answer cue. Under all
three pinned tokenizers each surface is **two** tokens, not one:

```
" 0" -> [220, 15]   " 1" -> [220, 16]   " 2" -> [220, 17]   " 3" -> [220, 18]
" 4" -> [220, 19]   " 5" -> [220, 20]   " 6" -> [220, 21]   " 7" -> [220, 22]
" 8" -> [220, 23]   " 9" -> [220, 24]
```

Token `220` is the shared leading-space token; the residue is carried by the
*second* token. The ten sequences are pairwise distinct, but they are not
single tokens, so the registered rule — read one next-token logit vector and
restrict it to ten registered content token IDs — is **not implementable as
written** for these roles. This is a genuine registered eligibility outcome. It
is not repaired, replaced or rerun, and it is never reported as a pass or as
robustness evidence.

By contrast `S1` is unaffected, because a label surface such as `" A"` is a
single token under every role.

## A defect in the gate itself, disclosed rather than repaired

The emitted terminal state is **more severe than this run's own evidence
supports**, and the cause is a defect in the P0 harness, not in the measurement.

`evaluate_eligibility` in `p0_tokenizer_gate.py` consults a **role-level**
eligibility flag that is set to false when *either* the `S1` or the `S2`
candidate check fails. It then marks every `S1` cell of that role
`INELIGIBLE_TOKEN_IDS` as well. Because only the `S2` check failed, the 27 `S1`
cells were marked ineligible **with an empty reason list** — visible in
`p0_tokenizer_gate_result.json`, where each such cell carries
`"reasons": []` and `"collision_rows": []`, while the `S2`/`S3` cells carry an
explicit reason.

With that propagation removed, the recorded evidence shows every target role
retains nine executable genuine `I3` contrasts under `S1`, so §7.2's continue
rule — "continue only if at least one genuine `I3` contrast remains executable
for each of `RT`, `RL` and `RI`" — would have been satisfied.

The defect is **not fixed in this round**. Stage P0-T is single-shot: every
encode increments a cumulative, non-resettable counter, and no fix-and-rerun is
authorized. Repairing the classifier and re-deriving a different terminal state
from the same authority would be exactly the output-conditioned change the
authority forbids. The defect is therefore recorded here as demonstrated
mechanical evidence for the successor calibration round, which §12 explicitly
empowers to "repair a demonstrated mechanical or surface defect in a new
candidate protocol".

## What this does and does not establish

This is a **methods-feasibility observation, not Study 3 evidence**. It selects
no interface, sets no threshold, passes no formal gate, ranks nothing, estimates
no effect, resolves neither `OD2` nor `UR-22`, freezes nothing, and answers no
research question. No model operation of any kind occurred: no checkpoint was
downloaded, no weight loaded, no GPU allocated, no forward pass performed and no
text generated.

## What the successor calibration round must weigh

1. **The `S2`/`S3` single-token registration is a demonstrated surface defect.**
   The candidate surfaces cannot be scored at one position as registered. A new
   candidate protocol must choose deliberately between, for example, registering
   the content surfaces without the leading space, scoring at the second
   position, or accepting multi-token candidates with an explicit scoring rule —
   and must say why. The pilot supplies the mechanical fact, not the choice.
2. **The eligibility-propagation defect above must be repaired** before any
   further round can trust a terminal disposition from this harness.
3. **`S1` and the renderer are mechanically sound** on this evidence: complete
   rendering, exact round-trip, and zero token-ID collisions across the entire
   32-state census for all three roles.
4. Nothing here licenses a claim about `S2`'s or `S3`'s scientific merit. A
   surface that cannot be scored has not been shown to be a worse interface; it
   has been shown to be unimplementable **as registered**.
