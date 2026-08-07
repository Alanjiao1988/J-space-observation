# Frozen S3 Stage E0 image and source

## Decision

Accept the distinct lens-free E0 image and source bundle as the only executable
for run `20260807T081017Z`. The state is:

`NONTERMINAL_CHECKPOINT_JLENS_S3_E0_IMAGE_FROZEN_AWAITING_LOCK`

The image is
`acrjspaceobssea0708231738.azurecr.io/j-space-observation-jlens-s3-e0@sha256:17d664e13d67d79d99e7bf521bce9b7aefa946d33e25ec5ebe4cc7bc0aeff6cc`.
Its tag and manifest are write- and delete-disabled. It was built from exact
commit `67b72c29bd3dc6e8707198b16cfac27177664943` over the immutable S2
model image.

The E0 source bundle is 117,995 bytes with SHA-256
`95b8cede932e1ed298e5f675075530a8b1560c0aa9049abfa0c6feebf38f9085`.
A read-only Container Apps execution independently recomputed that hash, the
frozen S3 protocol/schema hashes, E0 output-schema hash, and all three vendored
benchmark hashes from the image.

The create-only namespace is fixed as:

- lock: `jlens-s3/e0/20260807T081017Z/lock`;
- complete output: `jlens-s3/e0/20260807T081017Z/output`;
- operational partials: `jlens-s3/e0/20260807T081017Z/partial`.

A private-network read-only preflight found zero existing objects under the
common prefix. At this boundary there have been zero official benchmark
tokenizer calls and zero official benchmark model passes. A600, B600, and
M1200 remain sealed prerequisites only; no lens is authorized to load or run
during E0.

ACR run `cmbh` was a path-setup failure before repository testing. Runs `cmbm`
and `cmbn` were external image-verifier harness failures caused respectively by
CRLF shell bytes and the ACR source mount hiding the image workspace. They
performed no benchmark tokenizer/model operation. The corrected read-only
Container Apps verifier
`job-js-e0-imgverify-67b72c2-5lg12he` succeeded without modifying the image or
Blob storage.

This decision authorizes creation and independent readback of one formal E0
lock. It does not yet authorize E0 execution; execution begins only after the
exact lock is durably exported and its bytes are independently verified.
