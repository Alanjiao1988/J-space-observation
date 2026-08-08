FROM scratch

ARG SOURCE_COMMIT
ARG SOURCE_TREE
ARG ATTEMPT_ID
LABEL org.opencontainers.image.revision="${SOURCE_COMMIT}"
LABEL org.opencontainers.image.source-tree="${SOURCE_TREE}"
LABEL org.opencontainers.image.title="Study 2 Stage T tokenizer gate pack"
LABEL org.opencontainers.image.description="Attempt ${ATTEMPT_ID}. Tokenizer mechanics only: no model weights, forward passes, generations, activations, probes, patching, or lens outputs."

COPY studies/study2/stage_t/ /stage-t-output/
COPY .study2_stage_t_binding.json /stage-t-output/acr_stage_t_binding.json
