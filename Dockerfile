FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y git curl vim \
    && groupadd --system --gid 10001 jspace \
    && useradd --system --uid 10001 --gid jspace --no-create-home \
        --home-dir /nonexistent --shell /usr/sbin/nologin jspace \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /workspace/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY --chown=0:0 . /workspace
COPY --chown=0:0 .semantic_audit_build_provenance.json /opt/jspace/semantic-audit-build-provenance.json
RUN env -u PYTHONPATH python -I -S \
        scripts/prepare_semantic_audit_build_context.py \
        --project-root /workspace \
        --validate-attestation /opt/jspace/semantic-audit-build-provenance.json \
    && chown -R 0:0 /workspace /opt/jspace \
    && chmod -R a-w /workspace /opt/jspace \
    && chmod 0444 /opt/jspace/semantic-audit-build-provenance.json \
    && install -d -o jspace -g jspace -m 0700 \
        /tmp/models/huggingface \
        /tmp/results \
        /tmp/jspace-cache \
        /tmp/jspace-pycache \
        /tmp/jspace-pytest \
        /tmp/jspace-tmp \
    && chmod 0755 /tmp

ENV HF_HOME=/tmp/models/huggingface \
    TRANSFORMERS_CACHE=/tmp/models/huggingface \
    RESULTS_DIR=/tmp/results \
    XDG_CACHE_HOME=/tmp/jspace-cache \
    PYTHONPYCACHEPREFIX=/tmp/jspace-pycache \
    JSPACE_TEST_TMP=/tmp/jspace-pytest \
    TMPDIR=/tmp/jspace-tmp

USER jspace

CMD ["bash", "-lc", "python --version && python -c 'import torch; print(torch.cuda.is_available())'"]
