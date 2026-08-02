# Phase A public audit — scope B

**Audit B: repository, entrypoints, schemas, infrastructure-as-code, runtime
binding, security.**

You are auditing whether the *mechanical* material of this round is closed,
bound, and fail-closed. You are not auditing the scientific methodology — whether
the statistical design is sound, whether blinding is the right blinding, whether
the gates are the right gates. A second auditor covers that and you should not
spend effort there. Your question is narrower and harder: **can the thing that
actually runs in Azure differ from the thing that was audited, and would anyone
notice?**

## What the material is supposed to do

- Fifteen per-role container entrypoints are the only way any protocol step is
  reached. They are noninteractive and fail-closed: before doing any work each
  one asserts its registered configuration, its managed identity, the absence of
  ambient credentials, its permitted storage lanes, and its import isolation.
- A **closed** JSON Schema registry validates every cross-role artifact.
  `additionalProperties: false` at every object boundary, explicit schema
  versions, required fields, enums, cardinalities, and range constraints. Unknown
  fields, wrong versions, duplicate IDs and partial sets are rejected.
- Production entrypoints call **the same validators the tests exercise** — not a
  parallel simplified copy.
- Bicep defines a private review boundary: no public network access, private
  endpoints, no ambient credentials, egress control, and a role matrix that
  cannot grant delete.
- The runtime is bound by **content**, not by name: image digests, config
  digests, schema digests, and a dependency lock.

## Areas

Use one of these strings for `area`:
`repository`, `entrypoints`, `schemas`, `iac`, `runtime-binding`, `security`,
`role-matrix`, `dependency-lock`, `packaging`.

## What to look for, in order of value

1. **Substitution.** The central risk. Can a container be started with a command
   that resolves to a *different* role than the one whose identity and lanes were
   checked? Can a schema be swapped for a looser one? Can an image be referenced
   by a mutable tag anywhere that a digest is claimed? Can `roleImageDigests` be
   defaulted, empty, or partially populated and still deploy? Trace each of these
   to the exact line that refuses it, or report a `BLOCKER`.
2. **Openness in a "closed" schema.** Walk the schema registry for any object
   that omits `additionalProperties: false`, any enum that is actually a free
   string, any array without `minItems`/`maxItems` where a cardinality is
   claimed, any `"type": "string"` where a digest, an identity, or a version is
   claimed, and any schema whose `$id`/version is not bound to a digest.
3. **Fail-open behaviour behind a fail-closed claim.** A guard that returns
   instead of raising; a `try`/`except` that swallows; a check that is skipped
   when an optional argument is absent; a default that makes a missing
   environment variable mean "allowed"; a validator that is only called on one of
   several code paths.
4. **Ambient credentials and lanes.** The entrypoints claim to refuse ambient
   credentials and to permit only registered storage prefixes. Check the actual
   predicate: does it reject the credential *names* it knows about only, and
   would a differently named ambient credential pass? Is the lane check on the
   prefix a `startswith` that a crafted prefix could satisfy?
5. **Import isolation.** Fourteen of the fifteen roles must be parser-free and
   one must additionally be scorer-free. Check how "parser-free" is decided — is
   it a substring test on module names that a rename would defeat?
6. **IaC.** In the Bicep: hardcoded environment URLs, public network access left
   enabled, an overlap check that does not actually refuse, a role assignment
   that includes delete or write where create-only is claimed, a parameter whose
   `@allowed` narrowing is bypassed by `any()`, and any resource declared but not
   wired.
7. **Repository hygiene that could change what runs.** `.dockerignore` and
   `.gitattributes` interactions: does anything the audit relies on get stripped
   from a build context? Are line endings normalised such that a digest computed
   locally and a digest computed in Azure could differ?
8. **Tests that assert about source text.** Several controls assert on the bytes
   of source files. A substring assertion cannot distinguish a real declaration
   from a comment that quotes the thing being rejected. Find any such control
   that a comment could satisfy or defeat.

## Properties to check

Return one `properties_checked` entry for each of the following, verbatim, in
this order.

1. Every protocol step is reachable only through a registered container entrypoint.
2. A container command naming a different role than the role being run is refused.
3. An unregistered entrypoint name, a module-form command, or an extra argument is refused rather than ignored.
4. Each entrypoint asserts configuration, identity, absence of ambient credentials, storage lanes, and import isolation before doing work.
5. A role holding no managed identity is refused.
6. Every object boundary in the schema registry sets additionalProperties to false.
7. Every registered schema carries an explicit version and a bound digest.
8. Schema validation rejects unknown fields, wrong versions, duplicate IDs, and partial sets.
9. Production entrypoints call the same validators the tests exercise, not a simplified replica.
10. The runtime is bound by image digest, config digest, and schema digest rather than by mutable name or tag.
11. roleImageDigests has no default and an incomplete map cannot deploy.
12. The Bicep template refuses an overlapping address prefix rather than warning.
13. Public network access is disabled on every resource that holds or transits private material.
14. The role matrix grants no delete permission where create-only is claimed.
15. The Bicep template contains no hardcoded environment URLs.
16. The dependency closure is pinned and the pinned closure is what Azure installs.
17. Text-substring controls over source files cannot be satisfied or defeated by a comment.
18. No existing test is weakened, removed, skipped, or xfailed by the material under audit.
