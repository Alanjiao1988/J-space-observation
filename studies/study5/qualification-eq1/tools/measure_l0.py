#!/usr/bin/env python3
"""Measure the true L0 of an acquired transcoder checkpoint (P-1 step 2).

Authority Q-3 requires the true L0 of each acquired checkpoint to be measured
empirically, because the published README's table and its prose disagree about
the direction of ``l1_weight -> sparsity``. At most one of them is right and
neither can be relied on, so this measures rather than reads.

L0 here is the registered quantity: the mean number of active transcoder
features per token, per layer. The adapter class already computes it -- the
encoder is ReLU-gated, so "active" means strictly positive -- and exposes it
through ``set_cache_features`` and ``collect_transcoder_stats``. Using the
model's own definition rather than reimplementing it means the number reported
is the same number the training objective shaped.

Two measurement decisions worth stating:

* the **val** split of the registered contamination reference is used, never
  ``train``. Measuring sparsity on data the adapter was fit to would report how
  well it memorised, not how sparsely it represents;
* padding is masked out. The class masks with the attention mask when one is
  supplied, so padding tokens cannot dilute the per-token mean -- an unmasked
  measurement would report a lower L0 simply for having batched more padding.

Runs on a single GPU with ``batch_size = 1``, as the registered execution
contract requires.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from transformers import AutoTokenizer


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


def proof(check_id: str, passed: bool, detail: str = "") -> bool:
    if passed:
        print(f"P1-CHECK-{check_id} PASSED", flush=True)
    else:
        print(f"P1-CHECK-{check_id} FAILED: {detail}", flush=True)
    return passed


def load_rows(path: Path, limit: int) -> list[str]:
    """Take the first `limit` usable rows, deterministically.

    A fixed prefix of the file is a registered slice: it does not depend on a
    seed, a shuffle or anything observed later, so the same slice is recoverable
    by anyone holding the file.
    """

    texts: list[str] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            parts: list[str] = []
            for key in ("problem", "question", "prompt", "instruction", "text"):
                value = row.get(key)
                if isinstance(value, str) and value.strip():
                    parts.append(value)
            for key in ("conversations", "messages"):
                turns = row.get(key)
                if isinstance(turns, list):
                    for turn in turns:
                        if isinstance(turn, dict):
                            content = turn.get("content") or turn.get("value")
                            if isinstance(content, str) and content.strip():
                                parts.append(content)
            text = "\n".join(parts).strip()
            if text:
                texts.append(text)
            if len(texts) >= limit:
                break
    return texts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--adapter-repo", required=True)
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--val", required=True)
    parser.add_argument("--rows", type=int, default=200)
    parser.add_argument("--max-seq-len", type=int, default=1024)
    parser.add_argument("--label", required=True)
    parser.add_argument("--check-id", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    sys.path.insert(0, args.adapter_repo)
    from models.qwen2_transcoder import (  # type: ignore[import-not-found]
        Qwen2ConfigWithTranscoder,
        Qwen2ForCausalLMWithTranscoder,
    )

    if not torch.cuda.is_available():
        raise SystemExit("no CUDA device visible; L0 measurement requires a GPU")
    if torch.cuda.device_count() != 1:
        raise SystemExit(
            f"{torch.cuda.device_count()} devices visible; the registered "
            "contract requires exactly one per worker"
        )

    log(f"loading adapter: {args.adapter}")
    config = Qwen2ConfigWithTranscoder.from_pretrained(args.adapter)
    model = Qwen2ForCausalLMWithTranscoder.from_pretrained(
        args.adapter, config=config, dtype=torch.bfloat16
    )
    layers = int(config.num_hidden_layers)
    features = int(config.transcoder_n_features)
    model = model.to("cuda").eval()

    # transformers 5.x initialises modules on the meta device and then loads
    # weights into them. `_dead_feature_counters` is a plain attribute rather
    # than a registered buffer, so it is never materialised and the class's own
    # forward pass raises "Cannot copy out of meta tensor" the first time it
    # touches it. Materialising it here to the zeros `__init__` intended is a
    # restoration of the class's designed state, not a change to it: the L0
    # figure is computed earlier in the same block and is unaffected, and no
    # weight is altered. The alternative -- editing the third-party source --
    # would mean measuring a model that differs from the registered commit.
    materialised = 0
    for layer in model.model.layers:
        counters = getattr(layer.mlp, "_dead_feature_counters", None)
        if counters is None or counters.is_meta:
            layer.mlp._dead_feature_counters = torch.zeros(features, device="cuda")
            materialised += 1
    log(f"materialised {materialised} dead-feature counters left on the meta device")

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    texts = load_rows(Path(args.val), args.rows)
    log(f"loaded {len(texts)} rows from the val split")

    per_layer_sums = [0.0] * layers
    per_layer_counts = [0] * layers
    tokens_seen = 0

    model.set_cache_features(True)
    started = time.time()
    gpu_started = time.time()

    with torch.no_grad():
        for index, text in enumerate(texts):
            batch = tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=args.max_seq_len,
            )
            batch = {k: v.to("cuda") for k, v in batch.items()}
            tokens_seen += int(batch["input_ids"].numel())
            model(**batch)

            for layer_index, layer in enumerate(model.model.layers):
                cached = layer.mlp.cached_l0
                if cached is not None:
                    per_layer_sums[layer_index] += float(cached)
                    per_layer_counts[layer_index] += 1

            if (index + 1) % 25 == 0:
                log(f"  {index + 1}/{len(texts)} rows")

    gpu_seconds = time.time() - gpu_started
    model.set_cache_features(False)

    per_layer_l0 = [
        (per_layer_sums[i] / per_layer_counts[i]) if per_layer_counts[i] else None
        for i in range(layers)
    ]
    measured = [v for v in per_layer_l0 if v is not None]
    whole_model_mean = sum(measured) / len(measured) if measured else None

    ok = len(measured) == layers and whole_model_mean is not None
    report = {
        "schema_version": "study5-eq1-l0-measurement-v1",
        "phase": "P-1",
        "step": "S2",
        "label": args.label,
        "adapter": args.adapter,
        "measured_at_utc": utc_now(),
        "l0_definition": "mean number of strictly positive transcoder features per token",
        "computed_by": "the adapter class's own cached_l0, so this is the same quantity the training objective shaped",
        "encoder_is_relu_gated": True,
        "split_used": "val",
        "why_val_not_train": "measuring sparsity on data the adapter was fit to would report memorisation, not representational sparsity",
        "padding_masked_out": True,
        "why_padding_masked": "an unmasked mean would report a lower L0 simply for having batched more padding",
        "rows_measured": len(texts),
        "tokens_seen": tokens_seen,
        "max_seq_len": args.max_seq_len,
        "batch_size": 1,
        "dtype": "bfloat16",
        "quantized": False,
        "devices_visible": torch.cuda.device_count(),
        "num_hidden_layers": layers,
        "transcoder_n_features": features,
        "per_layer_l0": per_layer_l0,
        "whole_model_mean_l0": whole_model_mean,
        "min_layer_l0": min(measured) if measured else None,
        "max_layer_l0": max(measured) if measured else None,
        "layers_measured": len(measured),
        "gpu_seconds": round(gpu_seconds, 3),
        "wall_seconds": round(time.time() - started, 3),
        "readme_is_not_trusted": True,
        "why_readme_is_not_trusted": "the published README's table and its prose disagree about the direction of l1_weight -> sparsity, so at most one is right",
        "l0_is_not_a_pass_fail_threshold": True,
        "why_not": "no L0 threshold is registered anywhere in the authority; introducing one now would be inventing a criterion after the fact",
        "passed": ok,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    log(f"{args.label}: whole-model mean L0 = {whole_model_mean}")
    log(f"  per-layer range {report['min_layer_l0']} .. {report['max_layer_l0']}")
    log(f"  gpu_seconds {report['gpu_seconds']}")
    proof(args.check_id, ok, f"layers_measured={len(measured)}/{layers}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
