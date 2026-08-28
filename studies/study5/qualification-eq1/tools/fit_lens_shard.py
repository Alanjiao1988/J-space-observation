"""Fit a Jacobian lens shard on the target model T using the official jlens fit().

The estimator is NOT reimplemented here. This tool loads the model, wraps it
with jlens.from_hf, hands a slice of prompts to jlens.fitting.fit, and saves the
result. Everything statistical is the registered package's own code at commit
581d398613e5602a5af361e1c34d3a92ea82ba8e.

Layer convention is inherited unchanged from the 1.5B precedent in
jlens_s2_protocol.py: source_layers = 0..26, target_layer = 27, max_seq_len 128,
skip_first 16.

OD-010: a shard belongs to exactly one half, and shards are merged only within
their own half. This tool refuses to write a shard whose rows are not all from
one half.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

SOURCE_LAYERS = tuple(range(27))
TARGET_LAYER = 27
MAX_SEQ_LEN = 128
SKIP_FIRST = 16

MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
MODEL_REVISION = "916b56a44061fd5cd7d6a8fb632557ed4f724f60"

REGISTERED_GPU_UUIDS = {
    "e85524f36fdf",
    "b29579ca41a6",
    "0ec45dca0dfc",
    "5767cc3ad060",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def physical_gpu_uuid_last_twelve() -> str:
    """OD-006: the container index is meaningless, so resolve physical identity."""
    import torch

    props_uuid = None
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        raw = pynvml.nvmlDeviceGetUUID(handle)
        props_uuid = raw.decode() if isinstance(raw, bytes) else str(raw)
    except Exception:
        uuid_attr = getattr(torch.cuda.get_device_properties(0), "uuid", None)
        if uuid_attr is not None:
            props_uuid = str(uuid_attr)
    if not props_uuid:
        raise RuntimeError("could not resolve the physical GPU UUID (OD-006)")
    last12 = props_uuid.replace("-", "")[-12:].lower()
    if last12 not in REGISTERED_GPU_UUIDS:
        raise RuntimeError(
            f"physical GPU {last12} is not one of the four registered devices"
        )
    return last12


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", required=True)
    parser.add_argument("--role", required=True, choices=["A", "B", "heldout", "smoke"])
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--dim-batch", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0, help="0 means no limit")
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args()

    import torch

    if torch.cuda.device_count() != 1:
        raise RuntimeError(
            "exactly one GPU must be visible to this worker; "
            f"saw {torch.cuda.device_count()}"
        )
    gpu_uuid = physical_gpu_uuid_last_twelve()

    rows = []
    with Path(args.rows).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    role_rows = [r for r in rows if r["role"] == args.role]
    role_rows.sort(key=lambda r: r["role_index"])

    # OD-010 guard: this shard is drawn from exactly one half.
    if len({r["role"] for r in role_rows}) != 1:
        raise RuntimeError("shard rows span more than one role")

    shard_rows = role_rows[args.shard_index :: args.shard_count]
    if args.limit:
        shard_rows = shard_rows[: args.limit]
    prompts = [r["raw_text"] for r in shard_rows]
    if not prompts:
        raise RuntimeError("shard is empty")

    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_dir, trust_remote_code=False, use_fast=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir,
        dtype=torch.bfloat16,
        trust_remote_code=False,
        attn_implementation="eager",
    )
    model.to("cuda:0")
    model.eval()

    import jlens
    from jlens.fitting import fit

    lens_model = jlens.from_hf(model, tokenizer, force_bos=True)

    if lens_model.n_layers != 28 or lens_model.d_model != 3584:
        raise RuntimeError(
            f"unexpected geometry n_layers={lens_model.n_layers} "
            f"d_model={lens_model.d_model}"
        )

    # Prove force_bos actually took effect here too; from_hf's own docstring
    # warns the attribute may be ignored by some fast tokenizers, and DC-003
    # showed that failure is silent.
    probe = lens_model.encode("Hello world", max_length=MAX_SEQ_LEN)
    if int(probe[0, 0]) != int(tokenizer.bos_token_id):
        raise RuntimeError(
            "force_bos did not take effect inside the lens model; "
            f"first token was {int(probe[0, 0])}"
        )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{args.role}_shard{args.shard_index}of{args.shard_count}"
    ckpt = out_dir / f"ckpt_{tag}.pt"

    started = time.time()
    lens = fit(
        lens_model,
        prompts,
        source_layers=list(SOURCE_LAYERS),
        target_layer=TARGET_LAYER,
        dim_batch=args.dim_batch,
        max_seq_len=MAX_SEQ_LEN,
        skip_first=SKIP_FIRST,
        checkpoint_path=str(ckpt),
        checkpoint_every=args.checkpoint_every,
        resume=True,
    )
    elapsed = time.time() - started

    lens_path = out_dir / f"lens_{tag}.pt"
    torch.save(
        {
            "jacobians": lens.jacobians,
            "n_prompts": lens.n_prompts,
            "d_model": lens.d_model,
        },
        str(lens_path),
    )

    receipt = {
        "schema_version": "study5-eq1-p2-lens-shard-v1",
        "phase": "P-2",
        "role": args.role,
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "dtype": "bfloat16"},
        "jlens_commit": "581d398613e5602a5af361e1c34d3a92ea82ba8e",
        "estimator": "jlens.fitting.fit, not reimplemented",
        "layer_convention": {
            "source_layers": list(SOURCE_LAYERS),
            "target_layer": TARGET_LAYER,
            "max_seq_len": MAX_SEQ_LEN,
            "skip_first": SKIP_FIRST,
            "dim_batch": args.dim_batch,
        },
        "prompts_requested": len(prompts),
        "prompts_fitted": int(lens.n_prompts),
        "row_ids": [r["row_id"] for r in shard_rows],
        "elapsed_seconds": round(elapsed, 3),
        "seconds_per_prompt": round(elapsed / max(1, int(lens.n_prompts)), 3),
        "gpu_index_in_container": 0,
        "gpu_uuid_last_twelve": gpu_uuid,
        "outputs": {
            "lens_path": str(lens_path),
            "lens_sha256": sha256_file(lens_path),
            "lens_bytes": lens_path.stat().st_size,
        },
        "claim_ceiling": "A fitted lens is an instrument, not a result.",
    }
    (out_dir / f"receipt_{tag}.json").write_bytes(canonical_json_bytes(receipt))
    print(json.dumps(receipt, indent=1))
    print(f"P2-CHECK-FIT-{tag} PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
