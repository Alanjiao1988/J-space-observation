FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

WORKDIR /workspace

RUN apt-get update && apt-get install -y git curl vim && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /workspace/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /workspace

CMD ["bash", "-lc", "python --version && python -c 'import torch; print(torch.cuda.is_available())'"]
