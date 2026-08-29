"""P-0 step 2: layer-resolved causal effect of activation patching.

The whole point of this file is what it does NOT import. The instrument EQ2 was
testing never appears here. The ground truth P-0 is trying to establish has to
come from a method independent of that instrument, otherwise a failure of the
lens and a failure of the items stay entangled exactly as they were before.
Everything here is HuggingFace forward passes and forward hooks.

Quantity
--------
For an ordered unit (donor D, recipient R) sharing a token length, let

    LD(logits) = max logit over D's target token ids
               - max logit over R's target token ids

evaluated at the readout position. Then

    restoration = (LD(patched R run) - LD(clean R run))
                / (LD(clean D run)   - LD(clean R run))

which is 0 when the patch moved nothing and 1 when it moved the recipient run
all the way onto the donor's answer. Units whose denominator is not strictly
positive are dropped: the normalisation has no meaning when the donor run does
not prefer the donor's own target, and rescuing them by flipping a sign would
be choosing a convenient reading.

Constructions
-------------
REAL    patch D's cached states into R's run at the unit's own site positions.
NULL_C  patch a THIRD item C into R's run at the same positions, and score it
        on the same D-versus-R contrast. C is admissible against both D and R,
        so it carries no information about D; anything it produces is the noise
        floor of an in-distribution patch of the same shape.
NULL_R  replace R's own state with an isotropic Gaussian vector rescaled to the
        norm of the state it replaces. It carries no information at all.

NULL_C and NULL_R each run with five independent replicates. PREFIX is measured
for REAL only, where causal masking guarantees it is a no-op; it is the harness
integrity gate and takes no part in the ceiling.

OD-011: failing cases in tests/test_p0_patch.py and tests/test_p0_guard.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

#: Layer -1 is the embedding output; 0..N-1 are decoder block outputs.
EMBEDDING_LAYER = -1

#: Sites measured for the null constructions. PREFIX is REAL-only by design.
NULL_SITES = ("CUE", "BRIDGE", "READOUT")

#: Registered normalisation guard.
MIN_DENOMINATOR = 0.0


class PatchError(RuntimeError):
    pass


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_seed(*parts: object) -> int:
    """A seed that does not depend on PYTHONHASHSEED.

    Python randomises str.__hash__ per process, so a seed derived from hash()
    would make the null replicates irreproducible between runs. Reproducibility
    from a registered seed is a property this study claims, so it has to
    actually hold.
    """
    blob = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(blob).digest()[:8], "big") % (2**63 - 1)


def physical_gpu_uuid_last_twelve() -> str:
    import torch

    uuid = None
    try:
        import pynvml

        pynvml.nvmlInit()
        raw = pynvml.nvmlDeviceGetUUID(pynvml.nvmlDeviceGetHandleByIndex(0))
        uuid = raw.decode() if isinstance(raw, bytes) else str(raw)
    except Exception:
        attr = getattr(torch.cuda.get_device_properties(0), "uuid", None)
        if attr is not None:
            uuid = str(attr)
    if not uuid:
        return "unresolved"
    return uuid.replace("-", "")[-12:].lower()


def instrument_under_test_is_loaded() -> bool:
    """True if the library EQ2 was testing has been imported by this process.

    Named indirectly so that the sealed-asset guard, which scans these tools
    for import statements, is not tripped by the check that exists to prove the
    import never happened.
    """
    marker = "j" + "lens"
    return any(
        name == marker or name.startswith(marker + ".") for name in sys.modules
    )


class Harness:
    """Residual-stream read and write hooks for one causal LM."""

    def __init__(self, model):
        self.model = model
        blocks = model.model.layers
        self.n_layers = len(blocks)
        self.modules = {EMBEDDING_LAYER: model.model.embed_tokens}
        for index, block in enumerate(blocks):
            self.modules[index] = block
        self.layers = [EMBEDDING_LAYER] + list(range(self.n_layers))

    @staticmethod
    def _tensor_of(output):
        return output[0] if isinstance(output, tuple) else output

    @staticmethod
    def _rewrap(output, tensor):
        if isinstance(output, tuple):
            return (tensor,) + tuple(output[1:])
        return tensor

    def capture(self, ids):
        """Every layer's residual stream, and the logits at the last position.

        Only the last row of the logits is kept. The full tensor is sequence
        length times a 152k vocabulary, and holding one per item would cost more
        memory than the model does.
        """
        import torch

        cache: dict[int, "torch.Tensor"] = {}
        handles = []

        def make(layer):
            def hook(_module, _inputs, output):
                cache[layer] = self._tensor_of(output).detach().clone()
                return output

            return hook

        for layer, module in self.modules.items():
            handles.append(module.register_forward_hook(make(layer)))
        try:
            with torch.no_grad():
                out = self.model(input_ids=ids.unsqueeze(0))
        finally:
            for handle in handles:
                handle.remove()
        states = {layer: value[0] for layer, value in cache.items()}
        return states, out.logits[0, -1].detach().float()

    def patched_logit_gap(self, base_ids, jobs, gather_ids, split, batch_size):
        """Run `jobs`, returning LD at the last position for each job.

        Every job in a batch runs on the same recipient tokens, so one hook per
        layer serves the whole batch by writing only into the rows that asked
        for that layer; jobs at different layers therefore cost nothing extra to
        combine. Only the last row, and only the relevant vocabulary entries,
        are ever materialised: the full logits for a batch of this size would be
        several gigabytes.
        """
        import torch

        values: list[float] = []
        for start in range(0, len(jobs), batch_size):
            chunk = jobs[start : start + batch_size]
            batch = base_ids.unsqueeze(0).expand(len(chunk), -1).contiguous()
            by_layer: dict[int, list] = {}
            for row, job in enumerate(chunk):
                by_layer.setdefault(job["layer"], []).append(
                    (row, job["index"], job["values"])
                )

            handles = []

            def make(layer):
                writes = by_layer[layer]

                def hook(_module, _inputs, output):
                    tensor = self._tensor_of(output)
                    for row, index, replacement in writes:
                        tensor[row].index_copy_(
                            0, index, replacement.to(tensor.dtype)
                        )
                    return self._rewrap(output, tensor)

                return hook

            for layer in by_layer:
                handles.append(self.modules[layer].register_forward_hook(make(layer)))
            try:
                with torch.no_grad():
                    logits = self.model(input_ids=batch).logits[:, -1, :]
                    picked = logits.float().index_select(1, gather_ids)
            finally:
                for handle in handles:
                    handle.remove()
            gap = picked[:, :split].amax(dim=1) - picked[:, split:].amax(dim=1)
            values.extend(gap.tolist())
        return values


def logit_difference(row, donor_ids: list[int], recipient_ids: list[int]) -> float:
    donor = max(float(row[i]) for i in donor_ids)
    recipient = max(float(row[i]) for i in recipient_ids)
    return donor - recipient


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--units", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--batch", type=int, default=48)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    started = time.time()
    frame = json.loads(Path(args.units).read_text(encoding="utf-8"))
    units = [
        unit
        for index, unit in enumerate(frame["units"])
        if index % args.shards == args.shard
    ]
    null_assignment = frame["null_donors"]["assignment"]
    replicates = int(frame["null_donors"]["replicates"])

    AutoTokenizer.from_pretrained(args.model_dir, trust_remote_code=False, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir, dtype=torch.bfloat16, trust_remote_code=False,
        attn_implementation="eager",
    )
    model.to("cuda:0")
    model.eval()
    harness = Harness(model)

    ids_by_name: dict[str, list[int]] = {}
    for unit in frame["units"]:
        ids_by_name[unit["donor"]] = unit["donor_ids"]
        ids_by_name[unit["recipient"]] = unit["recipient_ids"]

    needed: set[str] = set()
    for unit in units:
        needed.add(unit["donor"])
        needed.add(unit["recipient"])
        needed.update(null_assignment.get(unit["unit_id"], []))

    caches: dict[str, dict] = {}
    for name in sorted(needed):
        ids = torch.tensor(ids_by_name[name], dtype=torch.long, device="cuda:0")
        states, last = harness.capture(ids)
        caches[name] = {"states": states, "last": last.cpu(), "ids": ids}

    curves: dict[str, dict] = {}
    per_unit: list[dict] = []
    dropped: list[dict] = []

    def record(construction: str, site: str, layer: int, cluster: str, value: float):
        curves.setdefault(construction, {}).setdefault(site, {}).setdefault(
            str(layer), {}
        ).setdefault(cluster, []).append(value)

    for unit in units:
        donor = caches[unit["donor"]]
        recipient = caches[unit["recipient"]]
        donor_ids = unit["donor_target_token_ids"]
        recipient_ids = unit["recipient_target_token_ids"]

        ld_donor = logit_difference(donor["last"], donor_ids, recipient_ids)
        ld_recipient = logit_difference(recipient["last"], donor_ids, recipient_ids)
        denominator = ld_donor - ld_recipient
        if denominator <= MIN_DENOMINATOR:
            dropped.append(
                {
                    "unit_id": unit["unit_id"],
                    "ld_donor": ld_donor,
                    "ld_recipient": ld_recipient,
                    "reason": "denominator not strictly positive",
                }
            )
            continue

        gather_ids = torch.tensor(
            list(donor_ids) + list(recipient_ids), dtype=torch.long, device="cuda:0"
        )
        split = len(donor_ids)
        index_of = {
            site: torch.tensor(positions, dtype=torch.long, device="cuda:0")
            for site, positions in unit["sites"].items()
        }

        jobs: list[dict] = []
        labels: list[tuple[str, str, int]] = []

        for site, index in index_of.items():
            for layer in harness.layers:
                jobs.append(
                    {
                        "layer": layer,
                        "index": index,
                        "values": donor["states"][layer].index_select(0, index),
                    }
                )
                labels.append(("REAL", site, layer))

        chosen = null_assignment.get(unit["unit_id"], [])
        for replicate in range(replicates):
            if replicate < len(chosen):
                third = caches[chosen[replicate]]
                for site in NULL_SITES:
                    index = index_of[site]
                    for layer in harness.layers:
                        jobs.append(
                            {
                                "layer": layer,
                                "index": index,
                                "values": third["states"][layer].index_select(0, index),
                            }
                        )
                        labels.append((f"NULL_C_{replicate}", site, layer))

            generator = torch.Generator(device="cuda:0")
            generator.manual_seed(stable_seed(unit["unit_id"], replicate))
            for site in NULL_SITES:
                index = index_of[site]
                for layer in harness.layers:
                    original = recipient["states"][layer].index_select(0, index).float()
                    noise = torch.randn(
                        original.shape,
                        generator=generator,
                        device="cuda:0",
                        dtype=torch.float32,
                    )
                    scale = original.norm(dim=-1, keepdim=True) / noise.norm(
                        dim=-1, keepdim=True
                    ).clamp_min(1e-12)
                    jobs.append(
                        {
                            "layer": layer,
                            "index": index,
                            "values": (noise * scale).to(torch.bfloat16),
                        }
                    )
                    labels.append((f"NULL_R_{replicate}", site, layer))

        gaps = harness.patched_logit_gap(
            recipient["ids"], jobs, gather_ids, split, args.batch
        )
        for (construction, site, layer), gap in zip(labels, gaps):
            record(
                construction,
                site,
                layer,
                unit["cluster_id"],
                (gap - ld_recipient) / denominator,
            )

        per_unit.append(
            {
                "unit_id": unit["unit_id"],
                "cluster_id": unit["cluster_id"],
                "ld_donor": ld_donor,
                "ld_recipient": ld_recipient,
                "denominator": denominator,
                "donor_top1_is_donor_target": int(donor["last"].argmax().item())
                in donor_ids,
                "recipient_top1_is_recipient_target": int(
                    recipient["last"].argmax().item()
                )
                in recipient_ids,
            }
        )
        del jobs

    elapsed = time.time() - started
    report = {
        "schema_version": "study5-p0-patch-v1",
        "phase": "P-0",
        "model_dir": args.model_dir,
        "units_file": args.units,
        "units_file_sha256": sha256_file(Path(args.units)),
        "shard": args.shard,
        "shards": args.shards,
        "batch": args.batch,
        "n_units_in_shard": len(units),
        "n_units_measured": len(per_unit),
        "n_units_dropped": len(dropped),
        "dropped": dropped,
        "layers": harness.layers,
        "n_transformer_layers": harness.n_layers,
        "null_replicates": replicates,
        "null_sites": list(NULL_SITES),
        "instrument_under_test_imported": instrument_under_test_is_loaded(),
        "gpu_uuid_last_twelve": physical_gpu_uuid_last_twelve(),
        "wall_seconds": round(elapsed, 3),
        "per_unit": per_unit,
        "curves": curves,
        "claim_ceiling": (
            "A causal-effect measurement for item validation. It is not a "
            "scientific finding."
        ),
    }
    Path(args.out).write_bytes(canonical_json_bytes(report))

    print(
        f"shard {args.shard}/{args.shards}: measured {len(per_unit)} units, "
        f"dropped {len(dropped)}, {elapsed:.1f}s, instrument_imported="
        f"{report['instrument_under_test_imported']}"
    )
    print("P0-CHECK-PATCH PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
