# Study 3-P0 frozen pilot corpus - census

> Methods-feasibility input only. Not Study 3 evidence, not a
> bank, not a seed draw and never an evidence-ledger row.

Authority: `studies/study3/prompts/study3_p0_feasibility_pilot_authority.md`

Aggregate prompt SHA-256: `e2f4bc508cbb21e90b11eb46ae5e3c204ba1772f445acc07bc7e4b9a2c904d22`

Rows: **35**. Rendered pair members: **70**.

Every base-item identity lives in the permanently excluded
`study3-p0-only/` namespace and may never be relabelled,
promoted or reused by a later bank.

## Rows by profile

| profile | rows |
| --- | --- |
| S1 | 27 |
| S2 | 3 |
| S3 | 3 |
| S4 | 2 |

## Rows by tuple class

| tuple class | rows |
| --- | --- |
| `K2-none-0` | 13 |
| `K3-affine_mod10-1` | 11 |
| `K3-permutation_chain-1` | 11 |

## Rows by contrast

| contrast | rows |
| --- | --- |
| K5-A1 | 3 |
| K5-P1 | 3 |
| K5-P2 | 3 |
| K5-P3 | 3 |
| K5-S1 | 3 |
| K5-S2 | 3 |
| K5-S3 | 3 |
| K6-INSTR | 10 |
| K6-SEP | 4 |

## Complete row census

| row | base item identity | profile | contrast | rendering pair | ground truth | baseline prompt sha256 | variant prompt sha256 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `p0-000` | `study3-p0-only/K2-none-0/S1-K5-P1` | S1 | K5-P1 | R-base -> R-base | `3` | `5dc060cea9733d894abb33fcf04e234ffb536d25bf9a71e8ffe6d77840e19862` | `d549c0f9caec23308d40a23127ed9c5b78e27f050cb39f4ba8e6cbfcf9e0d20d` |
| `p0-001` | `study3-p0-only/K2-none-0/S1-K5-P2` | S1 | K5-P2 | R-base -> R-base | `3` | `492cf4edc6a36cc11c90c259b7d1443160307f21036829862da452063d0dac54` | `0d0975f7aab6703c7e91ad78ea237e32a03645e1d3dd2ea693323af29af3e4f5` |
| `p0-002` | `study3-p0-only/K2-none-0/S1-K5-P3` | S1 | K5-P3 | R-base -> R-base | `3` | `003b9a6cba4d0dee502f05faade5aa3ad14e5268f6373babbcedb48d21d94bec` | `3deae5d34cd4da14a2f3f6d1b8d62706728720dbf558828f683e6cceb1736fce` |
| `p0-003` | `study3-p0-only/K2-none-0/S1-K5-S1` | S1 | K5-S1 | R-base -> R-base | `3` | `f0380bf8e208b43b389a6f621a1e03f5fe20f2353105918f93e809a1de1935b5` | `135d1750905d1e46da45f271c4b905a400ca693321fae5b65432d7c7caa504c2` |
| `p0-004` | `study3-p0-only/K2-none-0/S1-K5-S2` | S1 | K5-S2 | R-base -> R-base | `3` | `5da4df66cc4f64427e08f53421b9e2292fab8bd5ad4d742501eb7a7cfa6d3323` | `9220e2af61c33cd032d8ed6b48d0c9a874cd48514bb7378a0c13535e88e56d22` |
| `p0-005` | `study3-p0-only/K2-none-0/S1-K5-S3` | S1 | K5-S3 | R-base -> R-base | `3` | `466cb8f12fae071fb7be2187d7bdb4041fbc7e3d4b674e1cff8e81f2ba820c35` | `076093bdf9b9b0efdc2f8c9d6f1c9e1878e015f01aa9b111d070f045f5f8dbb4` |
| `p0-006` | `study3-p0-only/K2-none-0/S1-K5-A1` | S1 | K5-A1 | R-base -> R-base | `3` | `9a1126ae194e42a6e597da2a1d0900df689542a05e25e4836c9de98046a15794` | `261ba31f386d7bc0c55016570763d4b0e5f3b1a6c4c1472d3fd9171790b7836c` |
| `p0-007` | `study3-p0-only/K2-none-0/S1-K6-SEP` | S1 | K6-SEP | R-base -> R-sep | `3` | `c9735379d0fc2ead6fd496dfa1ca94e0604c4ed50f9478a615e5f03277cb83d9` | `89c4e105097375ebfc5b74f5d2e71ca34cfefd64f5e18202e3d87c9e5f4e3172` |
| `p0-008` | `study3-p0-only/K2-none-0/S1-K6-INSTR` | S1 | K6-INSTR | R-base -> R-instr | `3` | `5eff8bf1e0a5c5b032cc8d8e2719fbaf9a643971cc148d02671c68f44d8e7894` | `c83e29f2387c7b7050b7717a78cb71a3d09e367da4006da5d570a3effa51620a` |
| `p0-009` | `study3-p0-only/K2-none-0/S2-K6-INSTR` | S2 | K6-INSTR | R-base -> R-instr | `3` | `f92bcbec624295dee9ddf1f7f7f09e4530257998ed17bee388f62a1d6c9f1487` | `bbef79f351344e945934b824c7b0550e06203a22848a8c5b439381425247c91b` |
| `p0-010` | `study3-p0-only/K2-none-0/S3-K6-INSTR` | S3 | K6-INSTR | R-base -> R-instr | `3` | `f92bcbec624295dee9ddf1f7f7f09e4530257998ed17bee388f62a1d6c9f1487` | `bbef79f351344e945934b824c7b0550e06203a22848a8c5b439381425247c91b` |
| `p0-011` | `study3-p0-only/K2-none-0/S4-K6-SEP` | S4 | K6-SEP | R-base -> R-sep | `3` | `e8cb6a1cb0edeb49c16393fdc766f549b5a43781ed2246a33fc5d1e0b581ab20` | `0f8b6a9a29a92556a9ef742db25d010047a5b4345f098837a7c773062c28b3a2` |
| `p0-012` | `study3-p0-only/K2-none-0/S4-K6-INSTR` | S4 | K6-INSTR | R-base -> R-instr | `3` | `2f9b05512fdf17692f11c94024055429213a6f3a5a113a5a891c3910113ce2b2` | `7291bceb4c5ca54ef489fae12d3e61bb6fdddf6fba56952cc8987c15412c9627` |
| `p0-013` | `study3-p0-only/K3-affine_mod10-1/S1-K5-P1` | S1 | K5-P1 | R-base -> R-base | `3` | `485905e1631b8ff5d1e18dbb0762701f497a6e26956781ef7f0d97cb2f674ab8` | `6410eebaa9b16eee03309fd1f3987f245139a916e73a726571d3f81c496f55a6` |
| `p0-014` | `study3-p0-only/K3-affine_mod10-1/S1-K5-P2` | S1 | K5-P2 | R-base -> R-base | `3` | `ccf6f6d722d3a516cbe732f2a7e55d28e50725fa1ed84aaf27d294f92090d9f9` | `a0737ea9574f05bdf520ae8d9a9ded9541a5778cde9a775e10e5ab5fc31fc8bb` |
| `p0-015` | `study3-p0-only/K3-affine_mod10-1/S1-K5-P3` | S1 | K5-P3 | R-base -> R-base | `3` | `9dd00088fa371e8da938690311a497f17805f39dc61465b32551e2c518d6c9f4` | `74db515dce12774fdeb20735b6f49d5e8f96c178ba8705f89203fb9ee8be79ba` |
| `p0-016` | `study3-p0-only/K3-affine_mod10-1/S1-K5-S1` | S1 | K5-S1 | R-base -> R-base | `3` | `238bc56979d117beb8668b4145de61f5bc2dca81cdc35cf76d91bf3343698e4b` | `1488174a1895841b934d0228cec91e423e5ceb6fb43110414280f05cc7a13171` |
| `p0-017` | `study3-p0-only/K3-affine_mod10-1/S1-K5-S2` | S1 | K5-S2 | R-base -> R-base | `3` | `005d558544484c1c933868745d766eae7553ed2d41417fffde8519b40c95541a` | `e5f8629ac8d9012463b40299ce0cf575fb4ba1dbf87058280ddcc854d26485df` |
| `p0-018` | `study3-p0-only/K3-affine_mod10-1/S1-K5-S3` | S1 | K5-S3 | R-base -> R-base | `3` | `fae4925ccf14dd2088b60913e9c85eae4ae15a45ea78982176000086f37217a5` | `fb1ea7f2f4e0ce87a65cd993ab68c15810818da4da75056637cb27fbebb92d55` |
| `p0-019` | `study3-p0-only/K3-affine_mod10-1/S1-K5-A1` | S1 | K5-A1 | R-base -> R-base | `3` | `38d5b24a82dc93b682823dddbafd7e533cc57a446ffe981287042c3433b17da0` | `a618644421333dac895aca2a1f1120cf8cddf7a91aac60b61e8ee0c4e2409d0a` |
| `p0-020` | `study3-p0-only/K3-affine_mod10-1/S1-K6-SEP` | S1 | K6-SEP | R-base -> R-sep | `3` | `51f56f95047674a8b4352566df33803970342f2cdb473ba98a1fd098664b2861` | `56b11c9fa007c432e8967ef9dd68d7b03dc6cc56811c257f1c70edcdddd47275` |
| `p0-021` | `study3-p0-only/K3-affine_mod10-1/S1-K6-INSTR` | S1 | K6-INSTR | R-base -> R-instr | `3` | `4651e57904cbd064853afedfd6cd13720c0c3816cff62c270019ff57a7dce4b5` | `eca048e87ab2d2617f518c3191809b509802c280c6ba21bbedb102fdb7c8c0e1` |
| `p0-022` | `study3-p0-only/K3-affine_mod10-1/S2-K6-INSTR` | S2 | K6-INSTR | R-base -> R-instr | `3` | `0c9eadefe471ba665ce409100e7f0d2ece8be93130824ca2c400ce6cf7f49609` | `c07f7ba6a8ea291b97a171d7bee3f22b963f88db2dedf7b5a3cd2d61a4d6f5af` |
| `p0-023` | `study3-p0-only/K3-affine_mod10-1/S3-K6-INSTR` | S3 | K6-INSTR | R-base -> R-instr | `3` | `0c9eadefe471ba665ce409100e7f0d2ece8be93130824ca2c400ce6cf7f49609` | `c07f7ba6a8ea291b97a171d7bee3f22b963f88db2dedf7b5a3cd2d61a4d6f5af` |
| `p0-024` | `study3-p0-only/K3-permutation_chain-1/S1-K5-P1` | S1 | K5-P1 | R-base -> R-base | `6` | `51d778fcc9586d2840460114f1ee6ce896d6f626229cfb976879473860a44d25` | `fa72f3b861d68505dc1b197c62ded26769d84d728608912daa9a47a9a71bf4be` |
| `p0-025` | `study3-p0-only/K3-permutation_chain-1/S1-K5-P2` | S1 | K5-P2 | R-base -> R-base | `6` | `817a7b6bddbd9a75bdfdeeff936ac746a6ab10c7bc4009d4e8addcf6ab0fff38` | `9a052c3269b522802c5707fb3c2a65121bae4b59bad578bbdd19e16f1d43d76e` |
| `p0-026` | `study3-p0-only/K3-permutation_chain-1/S1-K5-P3` | S1 | K5-P3 | R-base -> R-base | `6` | `287d372962f3c314ddf5e7e28dd47c7c28058933108b77a91076b8980d470c17` | `232102952bb48f78d79881652c24f140a0d6eab9f8924590f3cde91641e665e9` |
| `p0-027` | `study3-p0-only/K3-permutation_chain-1/S1-K5-S1` | S1 | K5-S1 | R-base -> R-base | `6` | `31b94df80b445ab14177d7a0708c7a65802aadfc176ffd82c382c2ef26d8430e` | `29d16e3d4efde2b7bc7d8ed3ed2b9b731203fd30ad54817ed33108e149d6d54f` |
| `p0-028` | `study3-p0-only/K3-permutation_chain-1/S1-K5-S2` | S1 | K5-S2 | R-base -> R-base | `6` | `37024f1c5250ea96bf8da5ce9a4e121d2cd05ef9598fa14834cc847b4cae02d8` | `f7b9b915adea8a68869becc48437bebc631d9fc5d16016a621f6a3f1490d2a0d` |
| `p0-029` | `study3-p0-only/K3-permutation_chain-1/S1-K5-S3` | S1 | K5-S3 | R-base -> R-base | `6` | `5b2e3a29bc4cb06e28d2b07f4dc470ed8eff3402839ff744c1ff3cd8b1be7d33` | `b404842c5634fb57ec8ef920a6ceba81558841873491049334959a27cce52f36` |
| `p0-030` | `study3-p0-only/K3-permutation_chain-1/S1-K5-A1` | S1 | K5-A1 | R-base -> R-base | `6` | `2b517ea47aea91a6bdf3e9ffc032cad84c136003c8f6d31e8a2a52f37b337eff` | `ac64a377f02e5aec40cb75a0506ac9490f2bd93e459e92a3302d10fbb2c140b9` |
| `p0-031` | `study3-p0-only/K3-permutation_chain-1/S1-K6-SEP` | S1 | K6-SEP | R-base -> R-sep | `6` | `29478be1297292dd0673187b88cfe6967c6f2b7e5631f6f6f8b8df102ed9ae88` | `841a11fb248ea75f317b1e007e5fe5ad56f39804e081086fcb0ce03cbb6c9423` |
| `p0-032` | `study3-p0-only/K3-permutation_chain-1/S1-K6-INSTR` | S1 | K6-INSTR | R-base -> R-instr | `6` | `7f81f013359407ee6ffc50d4ad159b14cbf81f91209062c4d3fc2b55157b852f` | `946ed6db65c41d444e7224dd94cb2fb5eec06bda8f23d110bfd412d4dd9f32f8` |
| `p0-033` | `study3-p0-only/K3-permutation_chain-1/S2-K6-INSTR` | S2 | K6-INSTR | R-base -> R-instr | `6` | `fd5d36d54983aecf13a68033d54eeefbb724143f227a19119abdcfbce4eca425` | `760ca07ff8117270ff36990f5aecca313283ccfb55e4c4573f6fe6163a98707c` |
| `p0-034` | `study3-p0-only/K3-permutation_chain-1/S3-K6-INSTR` | S3 | K6-INSTR | R-base -> R-instr | `6` | `fd5d36d54983aecf13a68033d54eeefbb724143f227a19119abdcfbce4eca425` | `760ca07ff8117270ff36990f5aecca313283ccfb55e4c4573f6fe6163a98707c` |

## Structural absence

`K6-SEP` is **not** instantiated for `S2` or `S3`: the
label-to-content separator has no referent for an option-less
profile. `not_applicable` is a third value. It is not a pass, not
a zero effect, not robustness evidence and never a denominator
member.

`S3` registers no new surface. Its prompts are byte-identical to
the matching `S2` prompts because `S3` is a CPU-only rescoring
rule over the already captured `S2` logit vector.
