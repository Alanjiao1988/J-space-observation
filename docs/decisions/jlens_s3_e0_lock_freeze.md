# S3 Stage E0 formal lock

## Decision

Accept exactly one create-only formal E0 lock for run
`20260807T081017Z`. The state is:

`NONTERMINAL_CHECKPOINT_JLENS_S3_E0_LOCK_SEALED_AWAITING_SOLE_EXECUTION`

The lock is
`jlens-s3/e0/20260807T081017Z/lock/e0_lock.json`, 2,561 bytes,
SHA-256
`8417ec21a512f51dac094facd3e7769f0d00b8b8ee896a7e11aeb4a7acb44c1b`.
Creation execution `job-js-e0-lock-081017-1kglmch` wrote it with
`overwrite=false` and read it back byte-for-byte.

Independent execution `job-js-e0-lock-read-081017-27xh0q6` then:

- downloaded and rehashed the exact lock;
- applied the closed lock validator;
- recomputed every E0 image-local source, protocol, schema, and benchmark hash;
- revalidated the sealed S2 manifest and A600/B600/M1200 seal identities;
- confirmed the common E0 prefix contained only this one lock object;
- confirmed zero complete-output and zero partial-output objects;
- confirmed zero pre-lock benchmark tokenizer and model operations;
- confirmed that zero lens operations are authorized.

The lock binds the immutable E0 image
`sha256:17d664e13d67d79d99e7bf521bce9b7aefa946d33e25ec5ebe4cc7bc0aeff6cc`,
source bundle
`95b8cede932e1ed298e5f675075530a8b1560c0aa9049abfa0c6feebf38f9085`,
the exact 93/55/90 benchmark bytes, model/tokenizer revision, frozen S3
protocol/schema, sealed S2 prerequisites, and output prefix
`jlens-s3/e0/20260807T081017Z/output`.

This lock now authorizes exactly one formal E0 execution. It authorizes 238
item tokenizer calls and 238 clean next-token model passes, but no lens load or
application and no E1, E2, intervention, ablation, patching, or RQ2 operation.
No retry is authorized after a complete model result exists.
