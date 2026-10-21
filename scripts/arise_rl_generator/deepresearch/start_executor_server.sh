#!/bin/bash

# --- qqr platform guard ------------------------------------------------------
# This launcher needs Linux + NVIDIA GPUs (CUDA, sglang, Megatron via slime) and
# force-kills leftover sglang/ray/training processes before starting. It must
# never run on a laptop (e.g. macOS), where those kills could hit unrelated
# processes. Set QQR_FORCE_RUN=1 only on a dedicated GPU training node.
if [ "${QQR_FORCE_RUN:-0}" != "1" ]; then
  if [ "$(uname -s)" != "Linux" ] || ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "[qqr] Refusing to start: this script requires Linux with NVIDIA GPUs (nvidia-smi not found or non-Linux OS)." >&2
    echo "[qqr] See README.md -> 'Platform support'. Override with QQR_FORCE_RUN=1 on a GPU node." >&2
    exit 1
  fi
fi
# -----------------------------------------------------------------------------
# =============================================================================
# Start the DeepResearch executor (solver) inference service
# must be started before training the generator
# =============================================================================

set -ex

EXECUTOR_MODEL_PATH=${EXECUTOR_MODEL_PATH:-"Qwen/Qwen3.5-9B"}
EXECUTOR_PORT=${EXECUTOR_PORT:-30000}
EXECUTOR_GPUS=${EXECUTOR_GPUS:-"0"}
EXECUTOR_TP_SIZE=${EXECUTOR_TP_SIZE:-1}

echo "======================================"
echo "Starting the DeepResearch executor inference service"
echo "Model: Qwen3.5-9B"
echo "Port: ${EXECUTOR_PORT}"
echo "GPU: ${EXECUTOR_GPUS}"
echo "======================================"

CUDA_VISIBLE_DEVICES=${EXECUTOR_GPUS} python -m sglang.launch_server \
    --model-path ${EXECUTOR_MODEL_PATH} \
    --port ${EXECUTOR_PORT} \
    --host 0.0.0.0 \
    --tensor-parallel-size ${EXECUTOR_TP_SIZE} \
    --mem-fraction-static 0.85 \
    --chunked-prefill-size 8192 \
    --max-running-requests 32 \
    --trust-remote-code \
    --tool-call-parser qwen
