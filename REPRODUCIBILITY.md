# Reproducibility guide

This repository supports three different levels of reproduction. They should not be conflated.

1. **Audit-level reproduction (CPU, self-contained):** recompute every number and figure newly used in `REPORT.md` from committed result files.
2. **Artifact and test validation (mostly CPU):** run study-specific validators and tests against the current tree, subject to documented historical scope expiries and optional dependencies.
3. **Original GPU experiment reproduction:** reconstruct a study's pinned environment and acquire external checkpoints or large lens assets. This is not fully self-contained in Git and may require A100/T4-class hardware, storage, and provider access.

No command in this document authorizes a new scientific study or cloud operation. The project remains discontinued.

## 1. Audit-level environment

The report derivation was verified with:

| Component | Version / requirement |
|---|---|
| OS | Linux x86_64 container |
| Python | 3.11 |
| Matplotlib | 3.10.8 |
| NumPy | 2.3.5 |
| GPU | not used |
| Model weights | not used |
| Network | not used |

The arithmetic itself uses the Python standard library. Matplotlib and NumPy are required only to regenerate figures.

### Installation

```bash
python3 -m venv .venv-report
source .venv-report/bin/activate
python -m pip install --upgrade pip
python -m pip install -r analysis/requirements-report.txt
```

### Regenerate the report metrics and figures

```bash
python analysis/reproduce_report.py
```

Expected outputs:

- `analysis/report_metrics.json`
- `figures/interface_gate_results.svg`
- `figures/interface_gate_results.png`
- `figures/batch_width_numeric_shift.svg`
- `figures/batch_width_numeric_shift.png`

### Verify the committed derived metrics without writing

```bash
python analysis/reproduce_report.py --check
```

Expected terminal line:

```text
PASS: report metrics reproduce exactly; no model execution performed
```

The `--check` path does not import Matplotlib or NumPy and writes no file.

## 2. Source-to-output map

| Derived output | Primary committed inputs | Recalculation |
|---|---|---|
| Study 1 eligibility counts | `studies/study1/terminal_manifest.json` | manifest consistency and zero-operation boundary |
| Study 2 gate tails | `stage_bd_development_summaries.jsonl`, `stage_bd_gate_a_decision.json` | aggregate target/NT/D2+D3 rows; exact one-sided binomial tail |
| Study 4F-M1 table and Figure 1 | `studies/study4f/execution-m1/cell_results.json` | exact rates; Wilson 95% descriptive intervals |
| Study 5 object metrics | P-0c and P-0c-2 `object_proof.json` | clean/ablated accuracy and drop checks |
| Study 5 Figure 2 | P-0-prime and P-0c-2 `baseline_bf16.json` / `baseline_fp32.json` | mean-shift ratios and repaired zero checks |
| C1 non-vacuity summary | `validation-p0c2/measurement/out/c1_nonvacuity.json` | committed case maxima and pass flags |

Every consumed file's SHA-256 is stored in `analysis/report_metrics.json`. The analysis does not edit or normalize its inputs.

## 3. Original experimental environments

### Study 1

- Model: `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`
- Revision: `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562`
- Model dtype: float16; evaluation mode; `use_cache=false`; `trust_remote_code=false`
- Jacobian Lens: commit `581d398613e5602a5af361e1c34d3a92ea82ba8e`
- GPU: Tesla T4
- Corpus: WikiText-103 raw train revision `b08601e04326c79dfdd32d625aee71d232d685c3`
- Assignment seed: `jlens-s2-wikitext-roles-2026-08-06`
- Authoritative environment record: `docs/jlens_s2_s3_e0_final_handoff.md`

Exact host OS and all provider-side runtime metadata are not recorded in one reconstructable lock and remain unknown.

### Study 2

- GPU: Tesla T4
- Python 3.11.9; PyTorch 2.4.1+cu121; Transformers 4.46.3
- `PYTHONHASHSEED=0`; batch size 1
- Models and revisions:
  - target `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` at `ad9f0ae...`
  - lineage base `Qwen/Qwen2.5-Math-1.5B` at `4a83ca6...`
  - instruction control `Qwen/Qwen2.5-Math-1.5B-Instruct` at `aafeb0f...`
- Runtime image: `sha256:60fd31b4b396dd09565103d85b9ccf9a8d0703f4d6333e870167b95ee02ebe86`
- Authoritative record: `studies/study2/stage_bd/stage_bd_core_manifest.json`

### Study 3 / Study 3R

No scientific model experiment ran. Reproduction concerns deterministic protocol builders, schemas, tokenizer reconstructions, review packets, and historical scope anchors. See the terminal records linked in `EXPERIMENTS.md` before running any historical test.

### Study 4F-M1

- VM: AzureChinaCloud `Standard_NC96ads_A100_v4`, ChinaEast3
- GPUs: 4 × NVIDIA A100 80GB PCIe; pairwise NVLink
- Driver / CUDA: 580.173.02 / 13.0
- Runtime: bfloat16, batch size 1, isolated single-GPU workers
- Checkpoints: immutable 7B, 14B, 32B positive-reference revisions and a 1.5B target revision; the target was never run
- Execution seeds drawn: 416
- Authoritative record: `studies/study4f/execution-m1/M1_FINAL_DISCLOSURE.md`

The original VM, mounted storage, and checkpoint blobs are not provided by this repository.

### Study 5

- Base image: `python:3.11.14-slim-bookworm` at recorded digest
- J-lens 0.1.0 at commit `581d398...`
- PyTorch 2.12.0; Transformers 5.9.0; NumPy 2.4.6; SciPy 1.17.1
- Primary GPU: NVIDIA A100 80GB PCIe; bfloat16 unless an explicit float32 check is named
- Full lock: `studies/study5/qualification-eq1/requirements.study5-eq1.lock.txt`
- Image record: `studies/study5/qualification-eq1/container_image.json`

Study 5 consumed 40.144672 active GPU-hours across its recorded phases. A future rerun must re-prove no-op integrity on the actual object, model, dtype, batch width, and attention backend rather than inheriting a previous pass.

## 4. Tests and current-tree behavior

The report audit ran source parsing and targeted CPU-compatible tests. In the audit environment, `torch`, `transformers`, and `jsonschema` were not preinstalled, so the full suite could not be collected without installing the model stack.

Observed targeted result:

```text
284 passed, 4 skipped, 1 failed
```

The one failure was a Study 4F history-relative scope test that compares a predecessor anchor with the current project head. A separate Study 3R closure/review selection produced 129 passes, 3 skips, and 4 scope-relative failures after later-study files changed. These are reproducibility defects in historical tests, not discrepancies in the committed experimental result files.

Other current limitations:

- `src/jspace_observation/__init__.py` imports the model loader eagerly, so even CPU-only imports require the PyTorch/Transformers stack.
- The top-level `requirements.txt` is unpinned; study-specific locks are more authoritative for exact historical environments.
- Several historical tests intentionally bind a predecessor-to-then-current diff and expire as the repository grows.
- A Markdown link scan found broken local links, primarily inside intentionally partial upstream snapshots. One historical Study 3 disposition also points to a moved/missing prompt path.

## 5. Missing assets and non-self-contained boundaries

The `.gitignore` intentionally excludes model weights, checkpoints, `.pt` lenses, private evaluator sets, local secrets, and raw cloud audit downloads. Consequently, cloning the repository is sufficient for report-level reproduction but not for every original GPU run.

Material external dependencies include:

- immutable model checkpoints from their original model hosts;
- large fitted Jacobian-lens objects whose hashes and receipts are committed but whose binaries are not;
- private/locked evaluator inputs excluded by policy;
- Azure resources, storage mounts, and credentials;
- exact provider images when only a digest and construction record remain.

Do not substitute a new checkpoint revision or silently regenerate a missing private input and call the result a replication.

## 6. Reproducibility metadata still missing or incomplete

- a top-level license governing reuse of original repository content;
- a single lock file covering the entire historical program;
- exact host OS metadata for every early study;
- turnkey acquisition scripts for every excluded model and lens artifact;
- independent external replication on another hardware/software stack;
- non-expiring test variants that validate terminal artifacts without assuming a historical head tree.

These gaps should be reported with any reuse. They should not be filled by inference or by copying a third-party license onto original project content.
