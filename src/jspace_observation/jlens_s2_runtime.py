"""Pinned GPU/Blob runtime primitives for full-layer S2."""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import jlens_s2_corpus as corpus
import jlens_s2_protocol as s2


CORPUS_ROOT = Path("/workspace/repo/data/jlens_s2_wikitext")
MODEL_SNAPSHOT = Path("/workspace/model")
MODEL_SNAPSHOT_MANIFEST = MODEL_SNAPSHOT / "MODEL_SNAPSHOT_MANIFEST.json"
CHECKPOINT_EVERY = 8
TOP_K = (10, 50)
HELDOUT_PAIRS = {
    "A600_vs_B600",
    "A600_vs_M1200",
    "B600_vs_M1200",
}
RUNTIME_PACK_SCHEMA_VERSION = "jlens-s2-runtime-pack/v1"
RUNTIME_PACK_STAGES = {
    "S2-T0-smoke",
    "S2-T0-selection",
    "S2-F0-fit-shard",
    "S2-F0-fit-shard-failure",
    "S2-M0-merge",
    "S2-heldout-apply",
    "S2-convergence-analysis",
    "S2-heldout-aggregate",
    "S2-V0-independent-verification",
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_IMAGE_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


class S2RuntimeError(RuntimeError):
    """Raised when an S2 runtime identity or artifact fails closed."""


def load_registered_corpus(root: Path = CORPUS_ROOT) -> dict[str, Any]:
    rows_path = root / "corpus_rows.jsonl"
    rows = [
        json.loads(line)
        for line in rows_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    manifest = s2.load_json(root / "corpus_manifest.json")
    report = s2.validate_corpus_manifest(manifest, rows)
    by_role = {
        role: sorted(
            (row for row in rows if row["role"] == role),
            key=lambda row: int(row["role_index"]),
        )
        for role in s2.ROLE_ORDER
    }
    return {
        "by_role": by_role,
        "manifest": manifest,
        "report": report,
        "rows": rows,
    }


def role_slice(
    corpus_pack: Mapping[str, Any],
    role: str,
    start_index: int,
    end_index: int,
) -> list[dict[str, Any]]:
    if role not in {"A", "B", "heldout", "smoke"}:
        raise S2RuntimeError(f"unknown corpus role: {role}")
    if start_index < 1 or end_index < start_index:
        raise S2RuntimeError("role indices must be one-based and increasing")
    rows = list(corpus_pack["by_role"][role])
    selected = rows[start_index - 1 : end_index]
    if len(selected) != end_index - start_index + 1:
        raise S2RuntimeError("requested role slice exceeds registered rows")
    if [row["role_index"] for row in selected] != list(
        range(start_index, end_index + 1)
    ):
        raise S2RuntimeError("role slice order is not contiguous")
    return selected


def package_versions() -> list[dict[str, str]]:
    import importlib.metadata

    names = (
        "azure-identity",
        "azure-storage-blob",
        "huggingface-hub",
        "jlens",
        "numpy",
        "psutil",
        "torch",
        "transformers",
    )
    return [
        {"name": name, "version": importlib.metadata.version(name)}
        for name in names
    ]


class BlobStore:
    """Create-only managed-identity Blob access for one registered prefix."""

    def __init__(
        self,
        *,
        account: str,
        container: str,
        prefix: str,
        client_id: str | None,
        container_client: Any = None,
    ) -> None:
        if not account or not container or not prefix.strip("/"):
            raise S2RuntimeError("Blob account, container, and prefix are required")
        forbidden = sorted(
            name
            for name in (
                "AZURE_STORAGE_CONNECTION_STRING",
                "AZURE_STORAGE_KEY",
                "AZURE_STORAGE_SAS_TOKEN",
                "AZURE_STORAGE_ACCOUNT_KEY",
                "JSPACE_BLOB_ACCOUNT_KEY",
                "JSPACE_BLOB_SAS",
            )
            if os.getenv(name)
        )
        if forbidden:
            raise S2RuntimeError(
                "managed identity is required; forbidden Blob secrets: "
                + ", ".join(forbidden)
            )
        self.account = account
        self.container = container
        self.prefix = prefix.strip("/")
        if container_client is None:
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import BlobServiceClient

            credential = DefaultAzureCredential(
                managed_identity_client_id=client_id or None
            )
            service = BlobServiceClient(
                account_url=f"https://{account}.blob.core.windows.net",
                credential=credential,
            )
            container_client = service.get_container_client(container)
        self.client = container_client

    def name(self, relative: str) -> str:
        clean = relative.strip("/")
        if not clean or ".." in clean.split("/"):
            raise S2RuntimeError("invalid Blob relative path")
        return f"{self.prefix}/{clean}"

    def upload_bytes(self, relative: str, payload: bytes) -> dict[str, Any]:
        name = self.name(relative)
        self.client.upload_blob(name=name, data=payload, overwrite=False)
        observed = self.client.download_blob(name).readall()
        if observed != payload:
            raise S2RuntimeError(f"Blob readback mismatch: {name}")
        return {
            "blob": name,
            "bytes": len(payload),
            "sha256": s2.sha256_bytes(payload),
        }

    def upload_file(self, relative: str, path: Path) -> dict[str, Any]:
        name = self.name(relative)
        with path.open("rb") as handle:
            self.client.upload_blob(name=name, data=handle, overwrite=False)
        digest = hashlib.sha256()
        size = 0
        for chunk in self.client.download_blob(name).chunks():
            digest.update(chunk)
            size += len(chunk)
        if size != path.stat().st_size or digest.hexdigest() != s2.sha256_file(path):
            raise S2RuntimeError(f"Blob file readback mismatch: {name}")
        return {"blob": name, "bytes": size, "sha256": digest.hexdigest()}

    def download_bytes(self, relative: str) -> bytes:
        return self.client.download_blob(self.name(relative)).readall()

    def download_absolute(self, blob_name: str) -> bytes:
        clean = blob_name.strip("/")
        if not clean or ".." in clean.split("/"):
            raise S2RuntimeError("invalid absolute Blob name")
        return self.client.download_blob(clean).readall()

    def download_absolute_to(self, blob_name: str, path: Path) -> dict[str, Any]:
        clean = blob_name.strip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        with path.open("wb") as handle:
            for chunk in self.client.download_blob(clean).chunks():
                handle.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        return {"blob": clean, "bytes": size, "sha256": digest.hexdigest()}

    def list_absolute(self, prefix: str) -> list[str]:
        return sorted(
            row.name
            for row in self.client.list_blobs(name_starts_with=prefix.strip("/"))
        )


def runtime_store_from_environment() -> BlobStore:
    return BlobStore(
        account=os.environ["JSPACE_BLOB_ACCOUNT"],
        container=os.environ["JSPACE_BLOB_CONTAINER"],
        prefix=os.environ["JSPACE_BLOB_PREFIX"],
        client_id=os.getenv("AZURE_CLIENT_ID"),
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(s2.canonical_json_bytes(value))


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(s2.canonical_jsonl_bytes(rows))


def pack_manifest(
    *,
    stage: str,
    files: Sequence[Path],
    root: Path,
    complete: bool,
) -> dict[str, Any]:
    source_commit = os.environ["JSPACE_CODE_COMMIT"]
    image_digest = os.environ["JSPACE_IMAGE_DIGEST"]
    manifest = {
        "complete": complete,
        "create_only": True,
        "files": [
            {
                "bytes": path.stat().st_size,
                "relative_path": path.relative_to(root).as_posix(),
                "sha256": s2.sha256_file(path),
                "written_order": index,
            }
            for index, path in enumerate(
                sorted(files, key=lambda item: item.relative_to(root).as_posix()),
                start=1,
            )
        ],
        "image_digest": image_digest,
        "manifest_written_last": True,
        "protocol_sha256": s2.sha256_file(
            Path("/workspace/repo/docs/jlens_s2_protocol.json")
        ),
        "schema_version": RUNTIME_PACK_SCHEMA_VERSION,
        "source_commit": source_commit,
        "stage": stage,
    }
    validate_runtime_pack_manifest(manifest)
    return manifest


def validate_runtime_pack_manifest(
    manifest: Mapping[str, Any],
    *,
    expected_source_commit: str | None = None,
    expected_image_digest: str | None = None,
) -> dict[str, Any]:
    required = {
        "complete",
        "create_only",
        "files",
        "image_digest",
        "manifest_written_last",
        "protocol_sha256",
        "schema_version",
        "source_commit",
        "stage",
    }
    if set(manifest) != required:
        raise S2RuntimeError("runtime pack manifest fields are not exact")
    if (
        not isinstance(manifest["complete"], bool)
        or manifest["create_only"] is not True
        or manifest["manifest_written_last"] is not True
        or manifest["schema_version"] != RUNTIME_PACK_SCHEMA_VERSION
        or manifest["stage"] not in RUNTIME_PACK_STAGES
        or not _COMMIT.fullmatch(str(manifest["source_commit"]))
        or not _IMAGE_DIGEST.fullmatch(str(manifest["image_digest"]))
        or manifest["protocol_sha256"]
        != "e542841890322f2407553714c65ad153e4dfbdba3cb51dad61542e122a5a29a2"
    ):
        raise S2RuntimeError("runtime pack manifest identity mismatch")
    if (
        expected_source_commit is not None
        and manifest["source_commit"] != expected_source_commit
    ):
        raise S2RuntimeError("runtime pack source commit mismatch")
    if (
        expected_image_digest is not None
        and manifest["image_digest"] != expected_image_digest
    ):
        raise S2RuntimeError("runtime pack image digest mismatch")
    files = manifest["files"]
    if not isinstance(files, list):
        raise S2RuntimeError("runtime pack files must be an array")
    names: list[str] = []
    for index, row in enumerate(files, start=1):
        if (
            not isinstance(row, Mapping)
            or set(row) != {"bytes", "relative_path", "sha256", "written_order"}
            or not isinstance(row["bytes"], int)
            or row["bytes"] < 0
            or not isinstance(row["relative_path"], str)
            or not row["relative_path"]
            or ".." in row["relative_path"].split("/")
            or not _SHA256.fullmatch(str(row["sha256"]))
            or row["written_order"] != index
        ):
            raise S2RuntimeError("runtime pack file identity is malformed")
        names.append(row["relative_path"])
    if len(names) != len(set(names)) or names != sorted(names):
        raise S2RuntimeError("runtime pack files are not unique sorted identities")
    return {
        "complete": manifest["complete"],
        "file_count": len(files),
        "image_digest": manifest["image_digest"],
        "source_commit": manifest["source_commit"],
        "stage": manifest["stage"],
    }


def receipt_artifact_manifest_blob(receipt_blob: str) -> str:
    clean = receipt_blob.strip("/")
    if "/" not in clean:
        raise S2RuntimeError("receipt Blob has no parent prefix")
    return clean.rsplit("/", 1)[0] + "/artifact_manifest.json"


def validate_receipt_transport(
    store: BlobStore,
    *,
    receipt_blob: str,
    receipt_sha256: str,
    receipt_bytes: bytes,
    related_files: Sequence[Mapping[str, Any]] = (),
    expected_source_commit: str | None = None,
    expected_image_digest: str | None = None,
) -> dict[str, Any]:
    if s2.sha256_bytes(receipt_bytes) != receipt_sha256:
        raise S2RuntimeError("receipt bytes differ from registered SHA-256")
    manifest_blob = receipt_artifact_manifest_blob(receipt_blob)
    manifest_bytes = store.download_absolute(manifest_blob)
    manifest = json.loads(manifest_bytes)
    provenance = validate_runtime_pack_manifest(
        manifest,
        expected_source_commit=expected_source_commit,
        expected_image_digest=expected_image_digest,
    )
    receipt_name = receipt_blob.rsplit("/", 1)[-1]
    matches = [
        row for row in manifest["files"] if row["relative_path"] == receipt_name
    ]
    if (
        len(matches) != 1
        or matches[0]["bytes"] != len(receipt_bytes)
        or matches[0]["sha256"] != receipt_sha256
    ):
        raise S2RuntimeError("receipt is not bound by its runtime pack manifest")
    by_name = {row["relative_path"]: row for row in manifest["files"]}
    for related in related_files:
        blob = str(related.get("blob", ""))
        name = blob.rsplit("/", 1)[-1]
        row = by_name.get(name)
        if (
            not blob
            or row is None
            or row["bytes"] != related.get("bytes")
            or row["sha256"] != related.get("sha256")
        ):
            raise S2RuntimeError(
                f"related artifact {name!r} is not bound by the runtime manifest"
            )
    return {
        **provenance,
        "manifest_blob": manifest_blob,
        "manifest_bytes": len(manifest_bytes),
        "manifest_sha256": s2.sha256_bytes(manifest_bytes),
        "receipt_blob": receipt_blob,
        "receipt_sha256": receipt_sha256,
    }


def upload_pack(
    store: BlobStore,
    *,
    root: Path,
    files: Sequence[Path],
    subprefix: str,
) -> dict[str, Any]:
    relative = [path.relative_to(root).as_posix() for path in files]
    if "artifact_manifest.json" not in relative:
        raise S2RuntimeError("runtime pack requires artifact_manifest.json")
    order = s2.manifest_last_order(relative)
    by_relative = {
        path.relative_to(root).as_posix(): path for path in files
    }
    uploaded = []
    for index, name in enumerate(order, start=1):
        row = store.upload_file(f"{subprefix.strip('/')}/{name}", by_relative[name])
        row["written_order"] = index
        uploaded.append(row)
    if not uploaded[-1]["blob"].endswith("/artifact_manifest.json"):
        raise S2RuntimeError("runtime artifact manifest was not uploaded last")
    return {"manifest_written_last": True, "uploaded": uploaded}


def model_snapshot_identity(path: Path = MODEL_SNAPSHOT_MANIFEST) -> dict[str, Any]:
    document = s2.load_json(path)
    if (
        document.get("model_id") != s2.MODEL_ID
        or document.get("revision") != s2.MODEL_REVISION
        or document.get("complete") is not True
    ):
        raise S2RuntimeError("baked model snapshot identity mismatch")
    files = document.get("files")
    if not isinstance(files, list) or not files:
        raise S2RuntimeError("baked model snapshot file manifest is empty")
    for row in files:
        target = MODEL_SNAPSHOT / row["path"]
        if (
            not target.is_file()
            or target.stat().st_size != row["bytes"]
            or s2.sha256_file(target) != row["sha256"]
        ):
            raise S2RuntimeError(f"baked model snapshot drift: {row['path']}")
    return document


class OfficialBackend:
    """Exact pinned model and official Jacobian-lens adapter."""

    def __init__(self, *, require_gpu: bool) -> None:
        import importlib

        self.torch = importlib.import_module("torch")
        self.transformers = importlib.import_module("transformers")
        self.jlens = importlib.import_module("jlens")
        self.require_gpu = require_gpu
        self.hf_model: Any = None
        self.tokenizer: Any = None
        self.lens_model: Any = None

    def prepare(self) -> dict[str, Any]:
        snapshot = model_snapshot_identity()
        if self.require_gpu and not self.torch.cuda.is_available():
            raise S2RuntimeError("registered GPU runtime is unavailable")
        config = self.transformers.AutoConfig.from_pretrained(
            str(MODEL_SNAPSHOT),
            local_files_only=True,
            trust_remote_code=False,
        )
        config.use_cache = False
        config.output_hidden_states = False
        self.tokenizer = self.transformers.AutoTokenizer.from_pretrained(
            str(MODEL_SNAPSHOT),
            local_files_only=True,
            trust_remote_code=False,
        )
        if (
            getattr(self.tokenizer, "bos_token_id", None) is not None
            and hasattr(self.tokenizer, "add_bos_token")
        ):
            self.tokenizer.add_bos_token = True
        if getattr(self.tokenizer, "add_bos_token", None) is not True:
            raise S2RuntimeError("force_bos=true could not be applied")
        self.hf_model = self.transformers.AutoModelForCausalLM.from_pretrained(
            str(MODEL_SNAPSHOT),
            config=config,
            dtype=self.torch.float16,
            local_files_only=True,
            trust_remote_code=False,
        )
        device = self.torch.device("cuda:0" if self.require_gpu else "cpu")
        self.hf_model.to(device)
        self.hf_model.eval()
        self.hf_model.config.use_cache = False
        floating = {
            str(parameter.dtype)
            for parameter in self.hf_model.parameters()
            if parameter.is_floating_point()
        }
        if floating != {"torch.float16"}:
            raise S2RuntimeError(f"model parameter dtype drift: {floating}")
        self.lens_model = self.jlens.from_hf(
            self.hf_model,
            self.tokenizer,
            compile=False,
            force_bos=True,
        )
        if (
            self.lens_model.n_layers != s2.MODEL_LAYERS
            or self.lens_model.d_model != s2.MODEL_WIDTH
        ):
            raise S2RuntimeError("official adapter architecture mismatch")
        gpu = None
        total = None
        if self.torch.cuda.is_available():
            gpu = self.torch.cuda.get_device_name(0)
            total = int(self.torch.cuda.get_device_properties(0).total_memory)
        return {
            "adapter_force_bos": True,
            "compile": False,
            "d_model": self.lens_model.d_model,
            "eval_mode": not self.hf_model.training,
            "gpu_name": gpu,
            "gpu_total_bytes": total,
            "model_id": s2.MODEL_ID,
            "model_revision": s2.MODEL_REVISION,
            "n_layers": self.lens_model.n_layers,
            "parameter_dtype": s2.MODEL_DTYPE,
            "snapshot_manifest_sha256": s2.sha256_file(
                MODEL_SNAPSHOT_MANIFEST
            ),
            "snapshot_source": snapshot["source"],
            "trust_remote_code": False,
            "use_cache": False,
        }

    def verify_tokenization(self, rows: Sequence[Mapping[str, Any]]) -> None:
        encoded = self.tokenizer(
            [row["raw_text"] for row in rows],
            add_special_tokens=True,
            return_attention_mask=False,
            truncation=False,
        )
        ids = encoded["input_ids"]
        if len(ids) != len(rows):
            raise S2RuntimeError("runtime tokenizer cardinality mismatch")
        for row, token_ids in zip(rows, ids, strict=True):
            observed = [int(token_id) for token_id in token_ids[: s2.MAX_SEQ_LEN]]
            if observed != row["token_ids"]:
                raise S2RuntimeError(
                    f"runtime token IDs differ for {row['row_id']}"
                )

    def start_memory(self) -> None:
        if not self.torch.cuda.is_available():
            return
        self.torch.cuda.synchronize()
        self.torch.cuda.empty_cache()
        self.torch.cuda.reset_peak_memory_stats()

    def finish_memory(self) -> dict[str, Any]:
        if not self.torch.cuda.is_available():
            return {
                "gpu_free_bytes": None,
                "gpu_peak_allocated_bytes": 0,
                "gpu_peak_reserved_bytes": 0,
                "gpu_total_bytes": None,
                "peak_reserved_ratio": 0.0,
            }
        self.torch.cuda.synchronize()
        free, total = self.torch.cuda.mem_get_info()
        reserved = int(self.torch.cuda.max_memory_reserved())
        return {
            "gpu_free_bytes": int(free),
            "gpu_peak_allocated_bytes": int(
                self.torch.cuda.max_memory_allocated()
            ),
            "gpu_peak_reserved_bytes": reserved,
            "gpu_total_bytes": int(total),
            "peak_reserved_ratio": reserved / int(total),
        }

    def jacobian_for_prompt(self, text: str, dim_batch: int) -> tuple[Any, int, int]:
        return self.jlens.jacobian_for_prompt(
            self.lens_model,
            text,
            list(s2.SOURCE_LAYERS),
            target_layer=s2.TARGET_LAYER,
            dim_batch=dim_batch,
            max_seq_len=s2.MAX_SEQ_LEN,
            skip_first=s2.SKIP_FIRST,
        )

    def fit(
        self,
        prompts: Sequence[str],
        *,
        dim_batch: int,
        checkpoint_path: Path,
        resume: bool,
    ) -> Any:
        return self.jlens.fit(
            self.lens_model,
            prompts=list(prompts),
            source_layers=list(s2.SOURCE_LAYERS),
            target_layer=s2.TARGET_LAYER,
            dim_batch=dim_batch,
            max_seq_len=s2.MAX_SEQ_LEN,
            skip_first=s2.SKIP_FIRST,
            checkpoint_path=str(checkpoint_path),
            checkpoint_every=CHECKPOINT_EVERY,
            resume=resume,
        )

    def merge(self, lenses: Sequence[Any]) -> Any:
        return self.jlens.JacobianLens.merge(list(lenses))

    def load_lens(self, path: Path) -> Any:
        return self.jlens.JacobianLens.load(str(path))

    def save_lossless(self, lens: Any, path: Path) -> tuple[Any, dict[str, Any]]:
        from phase05_jlens_feasibility import save_lossless_jacobian_lens

        return save_lossless_jacobian_lens(
            self.torch,
            self.jlens,
            lens,
            path,
        )

    def lens_from_jacobians(self, jacobians: Mapping[int, Any], n_prompts: int) -> Any:
        return self.jlens.JacobianLens(
            jacobians=dict(jacobians),
            n_prompts=n_prompts,
            d_model=s2.MODEL_WIDTH,
        )


def validate_jacobians(torch_module: Any, jacobians: Mapping[int, Any]) -> dict[str, Any]:
    if set(jacobians) != set(s2.SOURCE_LAYERS):
        raise S2RuntimeError("Jacobian layer set is not exactly 0 through 26")
    rows = {}
    for layer in s2.SOURCE_LAYERS:
        matrix = jacobians[layer]
        if (
            matrix.dtype != torch_module.float32
            or list(matrix.shape) != [s2.MODEL_WIDTH, s2.MODEL_WIDTH]
            or matrix.device.type != "cpu"
            or not bool(torch_module.isfinite(matrix).all().item())
        ):
            raise S2RuntimeError(f"invalid Jacobian matrix at layer {layer}")
        rows[str(layer)] = {
            "dtype": str(matrix.dtype),
            "finite": True,
            "norm": float(matrix.norm().item()),
            "shape": list(matrix.shape),
        }
    return rows


def compare_tensor_matrices(
    torch_module: Any,
    left: Mapping[int, Any],
    right: Mapping[int, Any],
) -> dict[str, Any]:
    if set(left) != set(right) or set(left) != set(s2.SOURCE_LAYERS):
        raise S2RuntimeError("matrix comparison layer sets differ")
    layers = {}
    for layer in s2.SOURCE_LAYERS:
        a = left[layer].float()
        b = right[layer].float()
        difference = a - b
        denominator = max(float(b.norm().item()), 1e-12)
        flat_a = a.reshape(-1)
        flat_b = b.reshape(-1)
        norm_product = float(flat_a.norm().item() * flat_b.norm().item())
        cosine = (
            float(torch_module.dot(flat_a, flat_b).item()) / norm_product
            if norm_product > 0
            else (1.0 if torch_module.equal(a, b) else 0.0)
        )
        layers[str(layer)] = {
            "cosine": cosine,
            "max_abs": float(difference.abs().max().item()),
            "relative_frobenius": float(difference.norm().item()) / denominator,
        }
    return {
        "layers": layers,
        "max_abs": max(row["max_abs"] for row in layers.values()),
        "max_relative_frobenius": max(
            row["relative_frobenius"] for row in layers.values()
        ),
        "min_cosine": min(row["cosine"] for row in layers.values()),
    }


def independent_weighted_mean(
    torch_module: Any,
    lenses: Sequence[Any],
) -> dict[int, Any]:
    if not lenses:
        raise S2RuntimeError("independent weighted mean requires lenses")
    total = sum(int(lens.n_prompts) for lens in lenses)
    return {
        layer: sum(
            (
                lens.jacobians[layer].float() * int(lens.n_prompts)
                for lens in lenses
            ),
            torch_module.zeros_like(
                lenses[0].jacobians[layer],
                dtype=torch_module.float32,
            ),
        )
        / total
        for layer in s2.SOURCE_LAYERS
    }


class CheckpointMirror:
    """Mirror atomic upstream checkpoints to immutable Blob snapshots."""

    def __init__(
        self,
        *,
        torch_module: Any,
        path: Path,
        store: BlobStore,
        subprefix: str,
        minimum_next_idx: int,
    ) -> None:
        self.torch = torch_module
        self.path = path
        self.store = store
        self.subprefix = subprefix.strip("/")
        self.minimum_next_idx = minimum_next_idx
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.last_identity: tuple[int, str] | None = None
        self.errors: list[BaseException] = []
        self.uploaded: list[dict[str, Any]] = []

    def start(self) -> None:
        self.thread.start()

    def _snapshot(self) -> None:
        if not self.path.is_file():
            return
        payload = self.path.read_bytes()
        digest = s2.sha256_bytes(payload)
        state = self.torch.load(
            io.BytesIO(payload),
            map_location="cpu",
            weights_only=True,
        )
        next_idx = int(state["next_idx"])
        n_done = int(state["n_done"])
        if next_idx <= self.minimum_next_idx:
            return
        if (
            state["source_layers"] != list(s2.SOURCE_LAYERS)
            or state["target_layer"] != s2.TARGET_LAYER
            or state["skip_first"] != s2.SKIP_FIRST
            or n_done != next_idx
        ):
            raise S2RuntimeError("checkpoint state identity mismatch")
        identity = (next_idx, digest)
        if self.last_identity == identity:
            return
        checkpoint = self.store.upload_bytes(
            f"{self.subprefix}/checkpoints/n{next_idx:04d}.pt",
            payload,
        )
        receipt = {
            "checkpoint": checkpoint,
            "n_done": n_done,
            "next_idx": next_idx,
            "source_layers": list(s2.SOURCE_LAYERS),
            "target_layer": s2.TARGET_LAYER,
        }
        manifest = self.store.upload_bytes(
            f"{self.subprefix}/checkpoints/n{next_idx:04d}.json",
            s2.canonical_json_bytes(receipt),
        )
        self.uploaded.append(
            {"checkpoint": checkpoint, "manifest": manifest, **receipt}
        )
        self.last_identity = identity

    def _run(self) -> None:
        try:
            while not self.stop_event.wait(1.0):
                self._snapshot()
        except BaseException as exc:
            self.errors.append(exc)

    def finish(self) -> list[dict[str, Any]]:
        self.stop_event.set()
        self.thread.join(timeout=30)
        self._snapshot()
        if self.errors:
            raise S2RuntimeError(f"checkpoint mirror failed: {self.errors[0]}")
        return self.uploaded


def load_checkpoint_state(torch_module: Any, path: Path) -> dict[str, Any]:
    state = torch_module.load(path, map_location="cpu", weights_only=True)
    required = {
        "jacobian_sum",
        "n_done",
        "next_idx",
        "skip_first",
        "source_layers",
        "target_layer",
    }
    if not isinstance(state, dict) or set(state) != required:
        raise S2RuntimeError("checkpoint fields are not exact")
    if (
        state["source_layers"] != list(s2.SOURCE_LAYERS)
        or state["target_layer"] != s2.TARGET_LAYER
        or state["skip_first"] != s2.SKIP_FIRST
        or int(state["n_done"]) != int(state["next_idx"])
    ):
        raise S2RuntimeError("checkpoint metadata mismatch")
    return state


def lens_metadata(lens: Any, *, target_layer: int = s2.TARGET_LAYER) -> dict[str, Any]:
    return {
        "d_model": int(lens.d_model),
        "n_prompts": int(lens.n_prompts),
        "source_layers": [int(layer) for layer in lens.source_layers],
        "target_layer": target_layer,
    }


def logit_pair_metrics(
    torch_module: Any,
    left: Any,
    right: Any,
) -> dict[str, float]:
    a = left.float().reshape(-1)
    b = right.float().reshape(-1)
    if not bool(torch_module.isfinite(a).all()) or not bool(
        torch_module.isfinite(b).all()
    ):
        raise S2RuntimeError("heldout logits are non-finite")
    norm_product = float(a.norm().item() * b.norm().item())
    cosine = (
        float(torch_module.dot(a, b).item()) / norm_product
        if norm_product > 0
        else (1.0 if torch_module.equal(a, b) else 0.0)
    )
    result = {"logit_cosine": cosine}
    for k in TOP_K:
        left_top = set(int(value) for value in torch_module.topk(a, k).indices.tolist())
        right_top = set(
            int(value) for value in torch_module.topk(b, k).indices.tolist()
        )
        result[f"top{k}_overlap"] = len(left_top & right_top) / k
    left_order = torch_module.argsort(a)
    right_order = torch_module.argsort(b)
    left_rank = torch_module.empty_like(left_order, dtype=torch_module.float32)
    right_rank = torch_module.empty_like(right_order, dtype=torch_module.float32)
    positions = torch_module.arange(
        a.numel(), device=a.device, dtype=torch_module.float32
    )
    left_rank[left_order] = positions
    right_rank[right_order] = positions
    left_centered = left_rank - left_rank.mean()
    right_centered = right_rank - right_rank.mean()
    denominator = float(left_centered.norm().item() * right_centered.norm().item())
    result["rank_correlation"] = (
        float(torch_module.dot(left_centered, right_centered).item()) / denominator
    )
    return result


def validate_heldout_metric_rows(
    rows: Sequence[Mapping[str, Any]],
    expected_sequence_ids: Sequence[str],
) -> dict[str, Any]:
    if (
        len(expected_sequence_ids) != len(set(expected_sequence_ids))
        or not expected_sequence_ids
    ):
        raise S2RuntimeError("heldout expected sequence IDs are not unique")
    expected_keys = {
        (sequence_id, pair, layer)
        for sequence_id in expected_sequence_ids
        for pair in HELDOUT_PAIRS
        for layer in s2.SOURCE_LAYERS
    }
    observed_keys = [
        (row.get("sequence_id"), row.get("pair"), row.get("layer"))
        for row in rows
    ]
    if (
        len(observed_keys) != len(set(observed_keys))
        or set(observed_keys) != expected_keys
        or any(row.get("finite") is not True for row in rows)
    ):
        raise S2RuntimeError(
            "heldout metric keys do not exactly cover sequence x pair x layer"
        )
    return {
        "finite_rate": 1.0,
        "metric_row_count": len(rows),
        "pair_count": len(HELDOUT_PAIRS),
        "sequence_count": len(expected_sequence_ids),
        "source_layer_count": len(s2.SOURCE_LAYERS),
    }


def validate_production_attempt_manifest(
    store: BlobStore,
    manifest: Mapping[str, Any],
    *,
    production_plan: Mapping[str, Any],
    success_receipts: Mapping[str, Mapping[str, str]],
    success_documents: Mapping[str, Mapping[str, Any]],
    expected_fit_source_commit: str,
    expected_fit_image_digest: str,
    production_plan_sha256: str,
) -> dict[str, Any]:
    required = {
        "attempts",
        "fit_image_digest",
        "fit_source_commit",
        "production_plan_sha256",
        "run_id",
        "schema_version",
        "sequence_recomputed",
        "successful_shards",
    }
    if set(manifest) != required:
        raise S2RuntimeError("production attempt manifest fields are not exact")
    if (
        manifest["schema_version"] != "jlens-s2-production-attempts/v1"
        or manifest["fit_source_commit"] != expected_fit_source_commit
        or manifest["fit_image_digest"] != expected_fit_image_digest
        or manifest["production_plan_sha256"] != production_plan_sha256
        or manifest["run_id"] != production_plan["run_id"]
        or manifest["sequence_recomputed"] is not False
    ):
        raise S2RuntimeError("production attempt manifest identity mismatch")
    expected_shards = {
        row["id"]: row for row in production_plan["shards"]
    }
    successful = manifest["successful_shards"]
    if (
        not isinstance(successful, Mapping)
        or set(successful) != set(expected_shards)
        or set(success_receipts) != set(expected_shards)
        or set(success_documents) != set(expected_shards)
    ):
        raise S2RuntimeError("successful production shard set is incomplete")
    for shard_id, reference in successful.items():
        if reference != success_receipts[shard_id]:
            raise S2RuntimeError("successful shard receipt reference mismatch")
    attempts = manifest["attempts"]
    if not isinstance(attempts, list) or not attempts:
        raise S2RuntimeError("production attempts are missing")
    attempt_keys: set[tuple[str, str]] = set()
    successes: dict[str, list[Mapping[str, Any]]] = {
        shard_id: [] for shard_id in expected_shards
    }
    failed_with_progress: list[Mapping[str, Any]] = []
    for attempt in attempts:
        fields = {
            "artifact_prefix",
            "attempt_id",
            "end_time_utc",
            "execution",
            "failure_reason",
            "job",
            "last_checkpoint",
            "processed_count",
            "resume_source",
            "shard_id",
            "start_time_utc",
            "status",
            "success_receipt",
        }
        if not isinstance(attempt, Mapping) or set(attempt) != fields:
            raise S2RuntimeError("production attempt row fields are not exact")
        shard_id = str(attempt["shard_id"])
        attempt_id = str(attempt["attempt_id"])
        key = (shard_id, attempt_id)
        shard = expected_shards.get(shard_id)
        if (
            shard is None
            or not attempt_id
            or key in attempt_keys
            or attempt["status"] not in {"success", "infrastructure_failed"}
            or not isinstance(attempt["processed_count"], int)
            or not 0 <= attempt["processed_count"] <= shard["size"]
            or not str(attempt["job"])
            or not str(attempt["execution"])
            or not str(attempt["artifact_prefix"]).startswith(
                f"{production_plan['blob_prefix']}/shards/{shard_id}/attempts/"
            )
        ):
            raise S2RuntimeError("production attempt identity is invalid")
        attempt_keys.add(key)
        if attempt["status"] == "success":
            if (
                attempt["processed_count"] != shard["size"]
                or attempt["success_receipt"] != successful[shard_id]
                or attempt["failure_reason"] is not None
            ):
                raise S2RuntimeError("successful attempt accounting is invalid")
            successes[shard_id].append(attempt)
        else:
            if (
                attempt["success_receipt"] is not None
                or not str(attempt["failure_reason"])
            ):
                raise S2RuntimeError("failed attempt accounting is invalid")
            if attempt["processed_count"] > 0:
                failed_with_progress.append(attempt)
        resume = attempt["resume_source"]
        document = success_documents.get(shard_id) if attempt["status"] == "success" else None
        if resume is None:
            if document is not None and document.get("resumed") is True:
                raise S2RuntimeError("resumed success has no checkpoint binding")
        else:
            resume_fields = {
                "checkpoint_blob",
                "checkpoint_manifest_blob",
                "checkpoint_manifest_sha256",
                "checkpoint_sha256",
                "n_done",
            }
            if (
                not isinstance(resume, Mapping)
                or set(resume) != resume_fields
                or not isinstance(resume["n_done"], int)
                or not 0 < resume["n_done"] < shard["size"]
            ):
                raise S2RuntimeError("resume source fields are invalid")
            shard_prefix = (
                f"{production_plan['blob_prefix']}/shards/{shard_id}/attempts/"
            )
            if (
                not str(resume["checkpoint_blob"]).startswith(shard_prefix)
                or not str(resume["checkpoint_manifest_blob"]).startswith(
                    shard_prefix
                )
                or not _SHA256.fullmatch(str(resume["checkpoint_sha256"]))
                or not _SHA256.fullmatch(
                    str(resume["checkpoint_manifest_sha256"])
                )
            ):
                raise S2RuntimeError("resume source is not shard-bound")
            payload = store.download_absolute(
                resume["checkpoint_manifest_blob"]
            )
            if s2.sha256_bytes(payload) != resume["checkpoint_manifest_sha256"]:
                raise S2RuntimeError("resume manifest SHA-256 mismatch")
            checkpoint_manifest = json.loads(payload)
            if (
                checkpoint_manifest.get("checkpoint", {}).get("blob")
                != resume["checkpoint_blob"]
                or checkpoint_manifest.get("checkpoint", {}).get("sha256")
                != resume["checkpoint_sha256"]
                or checkpoint_manifest.get("n_done") != resume["n_done"]
                or checkpoint_manifest.get("next_idx") != resume["n_done"]
            ):
                raise S2RuntimeError("resume manifest content mismatch")
            if document is not None and (
                document.get("resumed") is not True
                or document.get("initial_next_idx") != resume["n_done"]
            ):
                raise S2RuntimeError("success receipt resume progress mismatch")
    if any(len(rows) != 1 for rows in successes.values()):
        raise S2RuntimeError("each production shard requires one successful attempt")
    resume_sources = {
        (
            row["shard_id"],
            row["resume_source"]["checkpoint_blob"],
            row["resume_source"]["checkpoint_sha256"],
        )
        for rows in successes.values()
        for row in rows
        if row["resume_source"] is not None
    }
    for failed in failed_with_progress:
        checkpoint = failed["last_checkpoint"]
        if (
            not isinstance(checkpoint, Mapping)
            or (
                failed["shard_id"],
                checkpoint.get("checkpoint_blob"),
                checkpoint.get("checkpoint_sha256"),
            )
            not in resume_sources
        ):
            raise S2RuntimeError(
                "failed progress is not consumed by an exact later resume"
            )
    return {
        "attempt_count": len(attempts),
        "failed_attempt_count": sum(
            attempt["status"] == "infrastructure_failed" for attempt in attempts
        ),
        "partial_attempt_count": len(failed_with_progress),
        "sequence_recomputed": False,
        "successful_shard_count": len(successes),
    }


__all__ = [
    "BlobStore",
    "CHECKPOINT_EVERY",
    "CheckpointMirror",
    "CORPUS_ROOT",
    "MODEL_SNAPSHOT",
    "MODEL_SNAPSHOT_MANIFEST",
    "OfficialBackend",
    "S2RuntimeError",
    "compare_tensor_matrices",
    "independent_weighted_mean",
    "lens_metadata",
    "load_checkpoint_state",
    "load_registered_corpus",
    "logit_pair_metrics",
    "pack_manifest",
    "package_versions",
    "role_slice",
    "runtime_store_from_environment",
    "upload_pack",
    "validate_receipt_transport",
    "validate_runtime_pack_manifest",
    "validate_jacobians",
    "validate_heldout_metric_rows",
    "validate_production_attempt_manifest",
    "write_json",
    "write_jsonl",
]
