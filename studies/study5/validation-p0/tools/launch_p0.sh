#!/bin/bash
# P-0 measurement launcher. Four shards, one physical GPU each.
# --network none: the measurement reaches nothing outside the container.
# /eq2 mounted read-only: EQ2's artifacts cannot be modified by this phase.
set -u
mkdir -p /scratch/study5/p0/logs /scratch/study5/p0/out
chmod 777 /scratch/study5/p0/logs /scratch/study5/p0/out

launch () {
  GPU=$1
  nohup sudo docker run --rm --name p0_shard${GPU} \
    --gpus device=${GPU} -e CUDA_VISIBLE_DEVICES=0 -e CUDA_DEVICE_ORDER=PCI_BUS_ID \
    -v /scratch/study5/p0:/p0:rw -v /scratch/study5/eq2:/eq2:ro \
    --network none \
    study5-eq1:qualification \
    python /p0/tools/patch_effect.py \
      --units /p0/out/units.json \
      --model-dir /eq2/controls/Qwen2.5-7B-Instruct \
      --shard ${GPU} --shards 4 --batch 48 \
      --out /p0/out/patch_shard${GPU}.json \
    > /scratch/study5/p0/logs/shard${GPU}.log 2>&1 &
  echo "launched shard ${GPU} on physical GPU ${GPU}"
}

for g in 0 1 2 3; do launch $g; done
sleep 10
sudo docker ps --format '{{.Names}}'
