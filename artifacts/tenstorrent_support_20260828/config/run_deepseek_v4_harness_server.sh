#!/usr/bin/env bash
set -euo pipefail

TT_METAL_ROOT=/home/ttuser/deepseekv4flash/tt-metal
DEEPSEEK_MODEL=/home/ttuser/deepseekv4flash/model_assets/DeepSeek-V4-Flash-0731
DEEPSEEK_L1_SMALL_SIZE=${DEEPSEEK_L1_SMALL_SIZE:-2048}

export TT_METAL_ROOT
export DEEPSEEK_MODEL
export MESH_DEVICE='(4,1)'
export TT_METAL_DISABLE_FABRIC_TWO_ERISC=1
export PYTHONPATH="$TT_METAL_ROOT/build_Release"
export EXTRA_MODELS_DIR="$TT_METAL_ROOT/models/autoports/deepseek_ai_deepseek_v4_flash_0731/vllm_models"
export VLLM_PLUGINS=tt,tt_model_registry
export DEEPSEEK_V4_FLASH_HF_MODEL="$DEEPSEEK_MODEL"
unset TT_MESH_GRAPH_DESC_PATH

printf -v TT_ADDITIONAL_CONFIG \
  '{"tt":{"sample_on_device_mode":"all","trace_mode":"all","enable_model_warmup":false,"trace_region_size":268435456,"l1_small_size":%s,"fabric_config":"FABRIC_1D_RING","fabric_reliability_mode":"RELAXED_INIT"}}' \
  "$DEEPSEEK_L1_SMALL_SIZE"

cd "$TT_METAL_ROOT"
exec python_env/bin/vllm serve "$DEEPSEEK_MODEL" \
  --host 127.0.0.1 \
  --port 8010 \
  --served-model-name deepseek-ai/DeepSeek-V4-Flash-0731 \
  --tokenizer "$DEEPSEEK_MODEL" \
  --tokenizer-mode deepseek_v4 \
  --reasoning-parser deepseek_v4 \
  --enable-auto-tool-choice \
  --tool-call-parser deepseek_v4 \
  --trust-remote-code \
  --dtype bfloat16 \
  --max-model-len 131072 \
  --max-num-seqs 1 \
  --max-num-batched-tokens 131072 \
  --block-size 128 \
  --additional-config "$TT_ADDITIONAL_CONFIG"
