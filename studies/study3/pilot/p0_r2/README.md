# Study 3 P0-R2

P0-R2 is the preregistered infrastructure successor to the terminal P0-R1
submission stop. It is not a retry of P0-R1 and currently authorizes no replay
gate or model operation.

The first implementation boundary is the host-to-ACR source transport. P0-R1
gave Azure CLI an extracted 108 MB repository tree. On the Windows production
host, one resulting absolute path was 265 characters and the local packer
failed before an ACR run ID existed. P0-R2 instead creates a two-file context:

- `task.yaml`, read from an exact committed Git blob; and
- `context_manifest.json`, binding the commit, tree, task blob and any
  governance objects injected into the task container.

No model, corpus, result, checkpoint, or mutable-worktree byte is present in
that context. The implementation authority is
`studies/study3/prompts/study3_p0_r2_infrastructure_successor_authority.md`.

Current state:

`STUDY3_P0_R2_INFRASTRUCTURE_SUCCESSOR_IMPLEMENTATION_IN_PROGRESS`

Do not run a P0-R2 live replay or create a P0-R2 GPU job until a later
publication contains the final digest-pinned image, execution lock, production
packing canary receipts, clean exact-commit validation and `P0_R2_HANDOFF.md`.
