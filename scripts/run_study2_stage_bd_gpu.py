#!/usr/bin/env python
"""Execute the Study 2 Stage B-D sealed development workload on a GPU.

This entry point is the only place Stage B-D loads model weights or runs a
forward pass.  It is deliberately narrow:

* weights are loaded for exactly the three registered checkpoints, at their
  pinned immutable revisions, with ``trust_remote_code=False``;
* every prompt is re-tokenized and required to reproduce the sealed Stage T
  prompt hash, input-ids hash, input length and answer position before it may
  be forwarded;
* exactly one final-input-position logit vector is read per logical row;
* generation, sampling, KV-cache reuse, hooks, hidden-state retention, chat
  templating and lens/probe/patching imports are all disabled by interlock, so
  attempting them raises instead of quietly succeeding;
* the behavioral-confirmation objects are asserted absent from the execution
  context before a single weight is read.

Deterministic core rows never contain a run ID, image digest, timestamp or
cache path.  Those live in the separate attempt/execution receipts.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# Import the Study 2 modules as top-level modules.  Importing the
# ``jspace_observation`` package would execute its ``__init__``, which pulls in
# unrelated Phase 1 machinery.
sys.path.insert(0, str(REPO_ROOT / "src" / "jspace_observation"))

import study2_protocol as s2  # noqa: E402
import study2_stage_bd as bd  # noqa: E402

FORBIDDEN_MODULES = (
    "jlens",
    "jacobian_lens",
    "sklearn",
    "baukit",
    "transformer_lens",
    "nnsight",
)


def _refuse(operation: str):
    def _stub(*_args: object, **_kwargs: object):
        raise bd.StageBDError(
            f"Stage B-D attempted a forbidden operation: {operation}. Stage B-D "
            "reads one restricted-option logit vector per row and nothing else."
        )

    return _stub


def install_interlocks() -> list[str]:
    """Make generation, hooks and hidden-state retention impossible.

    Passive checks can only observe that a forbidden path was not taken.  These
    replacements make it abort the run instead of merely being unlikely.
    """

    import torch
    import transformers
    from transformers import modeling_utils

    patched: list[str] = []
    base = modeling_utils.PreTrainedModel
    for attribute in ("generate", "sample", "greedy_search", "beam_search", "contrastive_search"):
        if hasattr(base, attribute):
            setattr(base, attribute, _refuse(f"PreTrainedModel.{attribute}"))
            patched.append(f"transformers.modeling_utils.PreTrainedModel.{attribute}")

    for attribute in (
        "register_forward_hook",
        "register_forward_pre_hook",
        "register_full_backward_hook",
        "register_backward_hook",
    ):
        if hasattr(torch.nn.Module, attribute):
            setattr(torch.nn.Module, attribute, _refuse(f"torch.nn.Module.{attribute}"))
            patched.append(f"torch.nn.Module.{attribute}")

    for name in ("apply_chat_template",):
        target = getattr(transformers.PreTrainedTokenizerBase, name, None)
        if target is not None:
            setattr(transformers.PreTrainedTokenizerBase, name, _refuse(name))
            patched.append(f"transformers.PreTrainedTokenizerBase.{name}")

    if len(patched) < 6:
        raise bd.StageBDError(f"the Stage B-D interlock patched too little: {patched}")
    return sorted(set(patched))


def assert_clean_import_surface() -> None:
    leaked = sorted(name for name in FORBIDDEN_MODULES if name in sys.modules)
    if leaked:
        raise bd.StageBDError(f"forbidden modules are imported: {leaked}")


def load_role(role: str, model_id: str, revision: str, cache_root: Path):
    """Load one registered checkpoint at its pinned revision, weights included."""

    import torch
    from huggingface_hub import HfApi, snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer

    info = HfApi().repo_info(repo_id=model_id, revision=revision, files_metadata=False)
    if str(info.sha) != revision:
        raise bd.StageBDError(
            f"{model_id} resolved revision {info.sha} != pinned {revision}"
        )
    local_dir = snapshot_download(
        repo_id=model_id,
        revision=revision,
        local_dir=str(cache_root / model_id.replace("/", "__")),
    )

    tokenizer = AutoTokenizer.from_pretrained(
        local_dir, revision=revision, trust_remote_code=False, use_fast=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        local_dir,
        revision=revision,
        trust_remote_code=False,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    )
    model.eval()
    model.config.use_cache = False
    if torch.cuda.is_available():
        model = model.to("cuda")

    files = []
    for path in sorted(Path(local_dir).rglob("*")):
        if not path.is_file():
            continue
        name = str(path.relative_to(local_dir)).replace(os.sep, "/")
        files.append(
            {
                "bytes": path.stat().st_size,
                "name": name,
                "sha256": bd.sha256_bytes(path.read_bytes()),
            }
        )

    dtypes: dict[str, int] = {}
    for parameter in model.parameters():
        dtypes[str(parameter.dtype)] = dtypes.get(str(parameter.dtype), 0) + 1
    snapshot = {
        "dtype_inventory": dtypes,
        "files": files,
        "model_class": type(model).__name__,
        "model_id": model_id,
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "parameter_dtype": str(next(model.parameters()).dtype),
        "requested_revision": revision,
        "resolved_revision": revision,
        "tokenizer_class": type(tokenizer).__name__,
    }
    return model, tokenizer, snapshot


def verify_prompt_identity(tokenizer, prompt: str, sealed) -> list[int]:
    """Refuse to forward anything whose tokenization differs from Stage T."""

    if bd.sha256_text(prompt) != sealed["prompt_sha256"]:
        raise bd.StageBDError("raw prompt bytes differ from the sealed Stage T prompt")
    input_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    if bd.ids_sha256(input_ids) != sealed["input_ids_sha256"]:
        raise bd.StageBDError("input ids differ from the sealed Stage T identity")
    if len(input_ids) != int(sealed["input_length"]):
        raise bd.StageBDError("input length differs from the sealed Stage T identity")
    if int(sealed["answer_position"]) != len(input_ids) - 1:
        raise bd.StageBDError("answer position is not the final input position")
    return list(input_ids)


def forward_row(model, input_ids, tokens):
    """One forward pass; read exactly one final-input-position logit vector."""

    import torch

    with torch.inference_mode():
        batch = torch.tensor([input_ids], dtype=torch.long, device=model.device)
        mask = torch.ones_like(batch)
        output = model(
            input_ids=batch,
            attention_mask=mask,
            use_cache=False,
            output_hidden_states=False,
            output_attentions=False,
        )
        if getattr(output, "hidden_states", None) is not None:
            raise bd.StageBDError("the forward returned hidden states")
        logits = output.logits[0].float().cpu().tolist()
    return bd.read_option_logits(
        logits, input_length=len(input_ids), tokens=tokens, left_padded=False
    )


def verify_published_seal(
    *,
    manifest: dict,
    expected_keys: list,
    tokens: dict,
    frozen: dict,
) -> dict:
    """Bind this run to the pre-inference seal that was published before it.

    The seal is a commit that exists in the image because it was pushed to
    ``main`` before this job was ever started.  Re-deriving the row space and
    then requiring it to equal the sealed values is what makes the
    pre-registration checkable: a run that silently measured a different row
    space, a different shard partition or different option tokens cannot reach a
    forward pass.
    """

    path = REPO_ROOT / bd.OUTPUT_DIR / bd.SEAL_NAME
    if not path.exists():
        raise bd.StageBDError(
            f"the pre-inference seal is absent from this image: {path}. Stage B-D "
            "refuses to run against an unpublished row space."
        )
    seal = json.loads(path.read_text(encoding="utf-8"))

    payload = "\n".join("|".join(key) for key in expected_keys)
    recomputed = bd.sha256_text(
        f"jspace-study2-stage-bd/expected-keys/v1\n{payload}\n"
    )
    checks = {
        "expected_primary_keys_sha256": (seal["expected_primary_keys_sha256"], recomputed),
        "expected_row_count": (seal["expected_row_count"], len(expected_keys)),
        "shard_manifest_sha256": (
            seal["shard_manifest_sha256"],
            manifest["shard_manifest_sha256"],
        ),
        "schema_version": (seal["schema_version"], bd.SEAL_VERSION),
        "run_id": (seal["run_id"], bd.RUN_ID),
        "starting_commit": (seal["starting_commit"], bd.STAGE_BD_START_COMMIT),
        "starting_tree": (seal["starting_tree"], bd.STAGE_BD_START_TREE),
    }
    for field, (sealed, observed) in sorted(checks.items()):
        if sealed != observed:
            raise bd.StageBDError(
                f"the sealed {field} is {sealed!r} but this run derived {observed!r}"
            )

    sealed_tokens = {entry["label"]: int(entry["token_id"]) for entry in seal["option_token_ids"]}
    if sealed_tokens != {label: int(value) for label, value in tokens.items()}:
        raise bd.StageBDError("the sealed option token IDs are not the ones this run derived")

    sealed_frozen = {entry["path"]: entry["sha256"] for entry in seal["frozen_inputs"]}
    observed_frozen = {path: entry["sha256"] for path, entry in frozen.items()}
    if sealed_frozen != observed_frozen:
        drifted = sorted(
            name
            for name in set(sealed_frozen) | set(observed_frozen)
            if sealed_frozen.get(name) != observed_frozen.get(name)
        )
        raise bd.StageBDError(f"frozen inputs drifted from the seal: {drifted}")

    source = seal["source"]
    payload_bytes = (REPO_ROOT / source["path"]).read_bytes()
    if bd.sha256_bytes(payload_bytes) != source["sha256"]:
        raise bd.StageBDError(
            f"{source['path']} is not the sealed source this run was registered against"
        )

    print(f"SEAL_VERIFIED={bd.sha256_bytes(path.read_bytes())}")
    return seal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="directory for shard artifacts")
    parser.add_argument("--cache", required=True, help="model snapshot cache root")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--roles", nargs="*", default=list(bd.MODEL_ROLES))
    args = parser.parse_args()

    started = time.monotonic()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    frozen = bd.verify_frozen_inputs(REPO_ROOT)
    confirmation = bd.assert_confirmation_unaddressable(REPO_ROOT)
    items = bd.load_development_bank(REPO_ROOT)
    by_id = {item["item_id"]: item for item in items}
    index = bd.load_stage_t_development_index(REPO_ROOT)
    tokens = bd.option_token_ids(index)
    manifest = bd.build_shard_manifest(items)
    prompts = bd.load_development_prompts(REPO_ROOT)

    # Bind to the published pre-registration before any model library is
    # imported, so a row-space discrepancy stops the run before a weight is read.
    verify_published_seal(
        manifest=manifest,
        expected_keys=bd.expected_row_keys(items),
        tokens=tokens,
        frozen=frozen,
    )

    patched = install_interlocks()
    assert_clean_import_surface()

    import torch
    import transformers

    environment = {
        "cuda_device_name": (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else ""
        ),
        "image_digest": args.image_digest,
        "platform_machine": platform.machine(),
        "python_version": platform.python_version(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED", ""),
        "source_commit": args.source_commit,
        "source_tree": args.source_tree,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
    }

    snapshots: dict[str, dict] = {}
    attempts: list[dict] = []
    identities = {
        role: (model_id, revision) for role, model_id, revision in s2.MODEL_IDENTITIES
    }

    for role in args.roles:
        model_id, revision = identities[role]
        model, tokenizer, snapshot = load_role(role, model_id, revision, Path(args.cache))
        snapshots[role] = snapshot
        identity = {"model_id": model_id, "resolved_revision": revision}

        for shard in manifest["shards"]:
            if shard["model_role"] != role:
                continue
            target = output / f"{bd.SHARD_RECEIPT_PREFIX}{shard['shard_id'].replace('/', '_')}.json"
            rows_path = output / f"stage_bd_rows_{shard['shard_id'].replace('/', '_')}.jsonl"
            if target.exists():
                # create-only checkpoint: a completed shard is never recomputed
                attempts.append(json.loads(target.read_text(encoding="utf-8"))["attempt"])
                continue

            attempt_started = time.monotonic()
            rows = []
            for role_key, item_id, arm in bd.expected_row_keys(items):
                if role_key != role:
                    continue
                item = by_id[item_id]
                if bd.shard_id(role, item["family"], item["depth"]) != shard["shard_id"]:
                    continue
                sealed = index[(role, item_id, arm)]
                input_ids = verify_prompt_identity(
                    tokenizer, prompts[(item_id, arm)], sealed
                )
                logits, ranks, top1 = forward_row(model, input_ids, tokens)
                rows.append(
                    bd.behavioral_row(
                        item=item,
                        role=role,
                        arm=arm,
                        identity=identity,
                        prompt_identity=sealed,
                        tokens=tokens,
                        option_logits=logits,
                        option_ranks=ranks,
                        top1_token_id=top1,
                    )
                )
                bd.verify_behavioral_row(
                    rows[-1],
                    item=item,
                    identity=identity,
                    prompt_identity=sealed,
                    tokens=tokens,
                )

            if len(rows) != shard["row_count"]:
                raise bd.StageBDError(
                    f"shard {shard['shard_id']} produced {len(rows)} rows, "
                    f"expected {shard['row_count']}"
                )
            entry = bd.write_jsonl(rows_path, rows)
            attempt = {
                "attempt": 1,
                "attempt_id": bd.attempt_id(shard["shard_id"], 1),
                "elapsed_seconds_bucket": int(time.monotonic() - attempt_started),
                "outcome": "complete",
                "retry_reason": "",
                "row_count": len(rows),
                "row_keys_sha256": shard["row_keys_sha256"],
                "shard_id": shard["shard_id"],
            }
            bd.write_json(
                target,
                {
                    "attempt": attempt,
                    "environment": environment,
                    "rows_file": entry,
                    "schema_version": bd.SHARD_RECEIPT_VERSION,
                },
            )
            attempts.append(attempt)

        del model
        torch.cuda.empty_cache()

    bd.write_json(
        output / "stage_bd_execution_receipt.json",
        {
            "confirmation_unopened": confirmation,
            "environment": environment,
            "execution": {
                "attempts": sorted(attempts, key=lambda entry: entry["shard_id"]),
                "batch_size": 1,
                "retries": sum(1 for entry in attempts if entry["attempt"] > 1),
                "schema_version": bd.EXECUTION_RECEIPT_VERSION,
                "shards_complete": len(attempts),
            },
            "frozen_inputs": bd._file_entries(frozen),
            "interlocks": patched,
            "shard_manifest_sha256": manifest["shard_manifest_sha256"],
            "weight_identity": bd.weight_identity_receipt(snapshots)
            if len(snapshots) == len(bd.MODEL_ROLES)
            else None,
        },
    )
    print(f"stage B-D shards complete in {int(time.monotonic() - started)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
