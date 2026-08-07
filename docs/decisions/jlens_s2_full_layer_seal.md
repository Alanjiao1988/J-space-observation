# Full-layer S2 artifact seal

## Decision

Accept the verified A600, B600, and M1200 byte identities as the exact S2
prerequisites for the already frozen S3 Stage E0. The state is:

`NONTERMINAL_CHECKPOINT_JLENS_S2_SEALED_AWAITING_S3_E0`

The create-only S2 verification prefix is
`jlens-s2/production/20260806T194226Z/verification-3`. The canonical S2
manifest is 1,978 bytes with SHA-256
`9d10a4b07a8133b7241ce9067649ebf1de48429cf7c04e0495b4c3fe90e58e47`.
The closed artifact pack is 4,599,734 bytes with SHA-256
`2dfc9bee037673f7bf33dddd863a3ce77cbe64482c72f06fd689c519a4041ddc`.

## Canonical lenses

All nine cumulative objects contain finite float32 1536 by 1536 matrices for
source layers 0 through 26, target layer 27. Every official merge equals its
independent `n_prompts`-weighted float32 recomputation exactly, and every
lossless save/load maximum absolute difference is zero.

| Lens | Prompts | Bytes | Lens SHA-256 | Manifest SHA-256 |
|---|---:|---:|---|---|
| A64 | 64 | 254,812,475 | `64a94a9d13f32a1f6679e2dea5a84a9de4541ba50def8ea9738e21cb312e0e05` | `f528f910d7cd0439ae8ebb45158278f934d9c454280453bc133db2daab0d5bb3` |
| A128 | 128 | 254,812,508 | `d52d816622fea58833476439ec823deabf350c5006ae0b659d5fade78ecedd3f` | `8582b888cb6f08fd3c14eae8584e2e4a07d9024a2949265733076ee80464d8ca` |
| A256 | 256 | 254,812,508 | `54a54ca2255ee23f6a317802cba4abf6a1f542a7f0f4fbb39ac40597f0bbebe9` | `32d59857ba888ee4f673131655d94f7d495a095b9728d6e875250ffbf529bb21` |
| A600 | 600 | 254,812,508 | `28e066960f03f51eaefb0e29aeb9cfe266e353746660f3283caaed85d0bc7689` | `302112cb3cea6c10f4531b897e5d75484e9489cd044bc8e555e5bcf6acb0fa77` |
| B64 | 64 | 254,812,475 | `508dfb52c3863b725c9dc784b891062ce4099ac2a3d290c9ace2abbf81e46dd5` | `ba81542358f8516c7f343711d2b07d17ba6bf6c115fcaca028a6251b8f1d7253` |
| B128 | 128 | 254,812,508 | `5423b887dcd09683264d8b3cc9261b596cc2be1c93171cb48590b51a31b3ab00` | `4e9683fd59579f0f46db03c8a9ea386a08eb1c90f22bb9b9336d73d5f3a3ff28` |
| B256 | 256 | 254,812,508 | `7c499260e2053b126a6be66bd7112a567c6c2ff475a5c61cf179d055442d40ee` | `4ac5b1083d96de4a95d94e31303843cad02d6e985bad5be61c80710d80e22695` |
| B600 | 600 | 254,812,508 | `f39a656a018f99b0b0bacff97fe0eb7fe18285aa0049f1ca0f477232400272d3` | `0881047112f8f8d6d105cd3e7a09c49d83cf2c2617730537e77e1604582c1aaa` |
| M1200 | 1,200 | 254,812,541 | `9938aa66e07ca8bc2f63463dc2dfe60cb512271fa7b19955b402cb581bb0e682` | `cc96d4c07aa2a5eaf35ef0aeb57391265dcfa79d3745dded1e84ece5827b943a` |

The independent A600/B600/M1200 seal hashes are respectively
`4032c8f30ec6aec2f12cbf0a303466a0fe66745617266dcc0fa3d2289e731dd7`,
`b62cd7f69aaa4a662144d8a8b75e3165330c9369990a52dbee85bb1b06b33ad4`,
and
`9716c3802625176060b3c2a479f7860cf4045807a45c6de346833a3b66e00138`.

## Non-gating diagnostics

The maximum across-layer A/B relative Frobenius distances at 64, 128, 256,
and 600 prompts are 0.217365, 0.157403, 0.112630, and 0.073860. The fitted
scaling exponent is 0.482675 with coefficient 1.627891 and residuals
`[-0.001324, 0.000898, 0.000627, -0.000387]`. These are engineering
diagnostics, not an S3 gate.

All 200 registered heldout sequences were applied to A600, B600, and M1200.
The aggregate contains exactly 16,200 finite metric rows: 200 sequences times
three lens pairs times 27 source layers. The diagnostics did not select,
alter, or block any lens.

## Execution and integrity

Production retained 33 attempts: 18 successes and 15 infrastructure failures,
including six checkpoint-bearing partial failures. The exact number of
recomputed sequence evaluations is unknowable because checkpoints were written
every eight prompts; the registered bound is zero through 42. The corrected
attempt manifest is 30,965 bytes with SHA-256
`5cad8ec9a57d73c69d9177be562a89b7233b12aa18c2cdba6db81bd10d209bbc`.

Independent verification used immutable image
`sha256:e0fec8e76a98be692d0f1f8631ca14c3978897fe765edc07db96ee97a5eae757`
at source commit `6c7acea471594c8bbb1e4dba8eb34cc50e8ae4ff`. Its receipt SHA-256 is
`b1a909cd04c991fd69932af5bfbf6427343851f87a1a00c537ac42c7d9d02a5f`.
All operational gates passed. Before this seal there were zero official S3
benchmark tokenizer operations and zero official S3 benchmark model
operations.

This is engineering artifact evidence only. WikiText is a public
Wikipedia-derived proxy rather than a known sample of the target model's
training distribution; two arms provide one difference trajectory rather than
a sampling distribution; and neither matrix convergence nor heldout apply
stability supports hidden reasoning, an internal workspace, or a J-space.
Phase 1.0D independently remains
`BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT_CAPACITY`.
