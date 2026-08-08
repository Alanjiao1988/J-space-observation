# Study 2 Stage B-D development execution image.
#
# The image is built from a git bundle of one exact commit, not from a working
# tree, and it deletes the six confirmation objects from its own filesystem
# before it is sealed.  The deletion is then asserted, so an image that could
# address a confirmation bank cannot be produced at all.  That is a stronger
# guarantee than a policy: the runtime check inside the job reports zero because
# the files are genuinely absent, not because the code declined to open them.
#
# Built by infra/azure/acr_tasks/study2_stage_bd_build.sh, which pins one
# immutable tag per commit and locks the tag and manifest afterwards.

FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime@sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126

ARG SOURCE_COMMIT
ARG SOURCE_TREE

ENV DEBIAN_FRONTEND=noninteractive \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    PYTHONUNBUFFERED=1 \
    STAGE_BD_SOURCE_COMMIT=${SOURCE_COMMIT} \
    STAGE_BD_SOURCE_TREE=${SOURCE_TREE}

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
COPY repo.bundle /opt/repo.bundle
RUN git clone -q /opt/repo.bundle /opt/study2-src \
    && cd /opt/study2-src \
    && git checkout -q "${SOURCE_COMMIT}" \
    && test "$(git rev-parse HEAD)" = "${SOURCE_COMMIT}" \
    && test "$(git rev-parse HEAD^{tree})" = "${SOURCE_TREE}" \
    && test -z "$(git status --porcelain)" \
    && rm -rf /opt/study2-src/.git /opt/repo.bundle

WORKDIR /opt/study2-src

# Confirmation isolation.  The objects are removed and their absence asserted in
# the same layer, so no later layer can reintroduce them without failing here.
RUN set -eu; \
    for path in \
        studies/study2/data/behavioral_confirmation.jsonl \
        studies/study2/data/mechanistic_candidate_pairs.jsonl \
        studies/study2/stage_t/stage_t_selected_mechanistic_confirmation.jsonl \
        studies/study2/stage_t/stage_t_mechanistic_eligibility_instruction_control.jsonl \
        studies/study2/stage_t/stage_t_mechanistic_eligibility_lineage_base.jsonl \
        studies/study2/stage_t/stage_t_mechanistic_eligibility_target.jsonl \
    ; do rm -f "$path"; test ! -e "$path"; done; \
    echo "CONFIRMATION_OBJECTS_REMOVED=6"

RUN pip install --no-cache-dir \
        "transformers==4.46.3" \
        "tokenizers==0.20.3" \
        "safetensors==0.4.5" \
        "huggingface-hub==0.26.2" \
    && python -c "import torch, transformers; print('torch', torch.__version__); print('transformers', transformers.__version__)"

# The frozen inputs and the closed core must import and verify inside the image,
# so a drifted artifact fails at build time rather than after a GPU allocation.
RUN python - <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, "src/jspace_observation")
import study2_stage_bd as bd

root = Path(".")
frozen = bd.verify_frozen_inputs(root)
receipt = bd.assert_confirmation_unaddressable(root)
items = bd.load_development_bank(root)
manifest = bd.build_shard_manifest(items)
assert len(items) == bd.ITEM_COUNT, len(items)
assert len(manifest["shards"]) == bd.SHARD_COUNT, len(manifest["shards"])
print("FROZEN_INPUTS_VERIFIED=%d" % len(frozen))
print("CONFIRMATION_PATHS_PRESENT=%d" % sum(
    1 for p in bd.CONFIRMATION_PATHS if (root / p).exists()
))
print("SHARD_MANIFEST_SHA256=%s" % manifest["shard_manifest_sha256"])
print("DEVELOPMENT_ONLY_RECEIPT=%s" % receipt["schema_version"])
PY

ENTRYPOINT ["bash", "/opt/study2-src/infra/azure/acr_tasks/study2_stage_bd_job.sh"]
