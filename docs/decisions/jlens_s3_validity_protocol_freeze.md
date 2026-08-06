# J-lens S3 validity protocol freeze

## Decision

The J-lens S3 validity protocol is frozen as a prospective, design-only
scientific gate. The successful nonterminal state is:

`NONTERMINAL_CHECKPOINT_JLENS_S3_VALIDITY_PROTOCOL_FROZEN_AWAITING_S2_LENSES_AND_EXECUTION`

This freeze does not validate a lens, authorize S3 execution, or change the
independent Phase 1.0D state
`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`.

## Authority and reviewed target

| Field | Value |
|---|---|
| Authority commit | `a98928817ce738d4e2af3365c099ed8fa6ab09e8` |
| Authority SHA-256 | `5d39859bc3d75143f3fdcb469de1d199ad7f831d474509b605569cdc9c1814b8` |
| Required starting commit | `31e8fc87cb560d141bada0aeb7d3b60c45f30081` |
| Required starting tree | `6132b43523c97c98722c094216c914f96b9dcd50` |
| Initial reviewed candidate commit | `36b54824a6c916e8d7738c6a9f65c54c314a4e20` |
| Initial reviewed candidate tree | `632b99f91daa4b071a1f1ebaee19b03c17796fc3` |
| Initial reviewed protocol SHA-256 | `eed211b11020851651bdcc4142e0e0c0d402e9814e9c7ede510667d425f897d4` |
| Consolidated correction commit | `3954e6e0089271e835de152e4c7e3e9591bb8491` |
| Corrected candidate tree | `dbb275b3ae7e0cd41af365dbac14b103c18ee0a7` |

The single bounded methods review found 0 FATAL, 2 MATERIAL, and 0 MINOR
findings. The one allowed consolidated correction resolved both MATERIAL
findings. Same-checklist verification found no correction-created
contradiction and closed at 0 FATAL / 0 MATERIAL / 0 MINOR.
`BLOCKED_ON_PREREGISTRATION_INTEGRITY` is not required.

The S3 methods-review allowance is **spent**. It cannot be repeated after this
freeze or after any target-model, tokenizer, lens, development, or confirmation
output exists.

## Frozen artifacts

Hashes are over exact committed Git blob bytes, not a CRLF-converted checkout.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `docs/jlens_s3_validity_protocol.json` | 45,138 | `bb07dc3be90539e88ff8ada8adee879da747ec5b0b0409499b9809f259df4625` |
| `docs/jlens_s3_validity_protocol.schema.json` | 50,831 | `5d6e2fc33771b427130bd1dbe94c79cdf6d5827288b96929352c0caa793acbf1` |
| `docs/jlens_s3_validity_protocol.md` | 21,150 | `d2e851013037a5efa96d7ae06c3d7c9d63466b299d255c75b6c665debf862bff` |
| validator source bundle v1 | 103,809 | `7e837b0cfdb0c9a12eb1b6c9067751c7cd4262cc18c5a6f17f4a6505f25b7410` |
| `docs/jlens_s3_validity_protocol_review.md` | 5,247 | `3ea426e74006098ebedf28e6f71f45e0bc38cc040df652ab1632eb288b07cb6a` |
| `third_party/jacobian-lens/581d398613e5602a5af361e1c34d3a92ea82ba8e/PROVENANCE.json` | 2,353 | `9af58768b200488ba28e3522c08624d8273487f6662f0dce5177a04a5f66fffc` |
| `docs/prompts/phase_s3_jlens_validity_protocol_design_prompt.md` | 31,626 | `5d39859bc3d75143f3fdcb469de1d199ad7f831d474509b605569cdc9c1814b8` |

The validator source bundle is bound to correction commit
`3954e6e0089271e835de152e4c7e3e9591bb8491`. Its byte format is:

1. ASCII `jlens-s3-validator-source-bundle-v1` followed by LF.
2. For each path in UTF-8 lexicographic order: UTF-8 path, NUL, ASCII decimal
   blob length, NUL, then the exact raw Git blob bytes.

| Bundle component | Bytes | SHA-256 |
|---|---:|---|
| `scripts/validate_jlens_s3_protocol.py` | 2,257 | `9682677258f3de060a50cffd7a590734b9a25b48ac4416a2948a5eae3f3af844` |
| `src/jspace_observation/jlens_s3_protocol.py` | 77,135 | `75979a9f7b5a596c209fe10ec4e4fda1291a99b59bb6b0f6fc63c69eb87fb0c5` |
| `tests/test_jlens_s3_protocol.py` | 24,250 | `aead1f7ef032be2b8332f80ca53d16a5215e1f1e72b8b0fd123346565f5c6d00` |

Any byte change to a frozen artifact or source-bundle component invalidates
this freeze and does not inherit the spent review.

## Frozen upstream bytes

Upstream repository:
`https://github.com/anthropics/jacobian-lens.git` at detached commit
`581d398613e5602a5af361e1c34d3a92ea82ba8e`, Apache-2.0.

| Upstream file | Bytes | SHA-256 | Registered count |
|---|---:|---|---:|
| `LICENSE` | 11,358 | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` | n/a |
| `data/evaluations/README.md` | 3,815 | `e061d9cce02a1cc651d58a81927833b760d3cef65bf4995126ecbe372a0ebe07` | n/a |
| `data/experiments/README.md` | 8,570 | `1d78c702fa22ba610990d545b4c9c96839cc75cd4e451f2badb1cab23e04ad0f` | n/a |
| `data/evaluations/lens-eval-multihop.json` | 21,869 | `50b7e4c9255291c0ca2a8e94615be9f44531fa57bb1a844e4f9616056d987416` | 93 |
| `data/evaluations/lens-eval-order-ops.json` | 9,589 | `b203206d16ff628152cc86f3838604e06cb54776f3e14fa1c34f150db8bc7560` | 55 |
| `data/experiments/probe-swap.json` | 26,567 | `a0edd27ca23f7b4d0fbe90448c2ddcc7457a3d812121bf024ed12a032ff86796` | 90 |

The frozen model-free counterpart rule yields 29 oriented matches and 24
unique unordered pairs.

## Execution and claim boundary

This round performed zero target-model loads, tokenizer loads, lens loads,
lens fits, lens applications, target-model inference calls, activation
operations, coordinate swaps, ablations, activation patches, GPU Jobs,
semantic-review provider calls, scientific rows, and RQ2 runs.

The freeze establishes only that a complete, machine-checkable, prospectively
falsifiable S3 validity protocol survived its one authorized bounded methods
review. It does not establish J-lens validity, model behavior, Phase 1.0D
headroom, human ground truth, hidden reasoning, an internal workspace, or a
J-space. A later S3 execution requires separate authority, the frozen S2 lens
artifacts, the exact identities above, and the protocol's E0/E1/E2 boundaries.
Even a future successful S3 classification would not license RQ2 while the
independent Phase 1.0D capacity block remains.
