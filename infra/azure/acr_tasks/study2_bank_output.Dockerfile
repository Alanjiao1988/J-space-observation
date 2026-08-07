FROM scratch

ARG SOURCE_COMMIT
ARG SOURCE_TREE
LABEL org.opencontainers.image.revision="${SOURCE_COMMIT}"
LABEL org.opencontainers.image.source-tree="${SOURCE_TREE}"
LABEL org.opencontainers.image.title="Study 2 Stage P model-free task banks"

COPY studies/study2/data/development.jsonl /stage-p-output/development.jsonl
COPY studies/study2/data/behavioral_confirmation.jsonl /stage-p-output/behavioral_confirmation.jsonl
COPY studies/study2/data/mechanistic_development_candidate_pairs.jsonl /stage-p-output/mechanistic_development_candidate_pairs.jsonl
COPY studies/study2/data/mechanistic_candidate_pairs.jsonl /stage-p-output/mechanistic_candidate_pairs.jsonl
COPY studies/study2/data/task_bank_manifest.json /stage-p-output/task_bank_manifest.json
COPY .study2_acr_generation_binding.json /stage-p-output/acr_generation_binding.json
