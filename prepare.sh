pip install -e . --no-deps

hf download Qwen/Qwen3-4B --local-dir /mnt/xujiawang/swe/data/Qwen3-4B

# train data
hf download --repo-type dataset zhuzilin/dapo-math-17k \
  --local-dir /mnt/xujiawang/swe/data/dapo-math-17k

# eval data
hf download --repo-type dataset zhuzilin/aime-2024 \
  --local-dir /mnt/xujiawang/swe/data/aime-2024

source scripts/models/qwen3-4B.sh
MEGATRON_LM_PATH=$(pip list | grep megatron-core | awk '{print $NF}')
PYTHONPATH=${MEGATRON_LM_PATH} python tools/convert_hf_to_torch_dist.py \
    ${MODEL_ARGS[@]} \
    --no-gradient-accumulation-fusion \
    --hf-checkpoint /mnt/xujiawang/swe/data/Qwen3-4B \
    --save /mnt/xujiawang/swe/data/Qwen3-4B_torch_dist
