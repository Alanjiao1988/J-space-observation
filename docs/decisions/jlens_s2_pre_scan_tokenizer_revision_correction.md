# Pre-scan correction to tokenizer revision verification

## Decision

Verify the pinned tokenizer revision from the immutable Hugging Face cache
snapshot path returned by `transformers.utils.hub.cached_file`, rather than
from the tokenizer object's optional private `_commit_hash` attribute.

The requested model/tokenizer repository and revision remain exactly:

- `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`;
- `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`.

The corrected gate requires the cache path to contain exactly one
`snapshots/<40-lowercase-hex>/` segment and requires that segment to equal the
pinned revision before the tokenizer can be used.

## Trigger and information boundary

Corrected P1 attempt
`job-jspace-s2-corpus-b77f7df6-i1qcwwm` successfully sealed the exact
WikiText source/license pack and protected prompt bank. It then constructed
the tokenizer and stopped because Transformers 5.9 returned no private
`_commit_hash` attribute on the tokenizer object.

At failure:

- one corpus tokenizer object had been constructed;
- zero WikiText rows had been scanned or tokenized;
- no eligible row, role key, role assignment, or token-ID sequence existed;
- benchmark tokenizer operations were zero;
- model, inference, logit, loss, activation, Jacobian, lens, E1/E2, and RQ2
  operations were zero.

The correction uses only a package compatibility fact and an immutable local
cache pathname established by the already pinned Hub download. It does not
change or respond to corpus content, tokenizer output, model behavior, lens
behavior, or S3 behavior.

## Retained attempt

The failed Job, execution, immutable corrected-selector image
`sha256:48efeaa40d88ac60d35f186fbb6c57b6731b28bbb5f47ba7277fbee04cc40045`,
and create-only partial prefix `jlens-s2/corpus/20260806T174244Z` are retained.
The prefix contains no final corpus manifest and is excluded from every role
and statistic.

## Validation

Correction commit `ce8cce829c11cda2a1cf78d0f06d3d74d0ceeac6`, tree
`0680f9ac92b3574ebad59394ece6cdfe7e0d581f`, adds model-free acceptance and
failure tests for immutable cache snapshot extraction. ACR run `cmau` bound
that commit/tree and passed all 29 focused S2 corpus and protocol tests.
