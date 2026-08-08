# Study 2 Stage B-D model-free finalization image.
#
# Deliberately CPU-only and deliberately without torch or transformers, so the
# stage that computes Gate A physically cannot load a model.  The image is built
# from a bundle of one exact commit and asserts commit, tree and cleanliness
# during the build.
#
# The confirmation objects are not deleted here: this stage reads only shard
# artifacts and frozen development inputs, and its own runtime receipt records
# zero confirmation reads.  Deleting them would break the frozen-input
# verification that proves the checkout is the registered one.

FROM python:3.11.15-bookworm@sha256:a8f8fbe1a0edc9e4dddafa64ba73f7e04be7be5ebc23f332362e779e0a2e4e52

ARG SOURCE_COMMIT
ARG SOURCE_TREE

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    PYTHONUNBUFFERED=1 \
    STAGE_BD_SOURCE_COMMIT=${SOURCE_COMMIT} \
    STAGE_BD_SOURCE_TREE=${SOURCE_TREE}

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

# The finalizer and validator use the standard library only.  Installing nothing
# is what makes the model-free claim checkable rather than merely asserted.
RUN python infra/azure/acr_tasks/study2_stage_bd_image_verify.py --require-model-free

ENTRYPOINT ["bash", "/opt/study2-src/infra/azure/acr_tasks/study2_stage_bd_finalize_job.sh"]
