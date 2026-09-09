#!/usr/bin/env bash
set -euo pipefail

TB_ROOT=/home/ttuser/deepseekv4flash/terminal_bench_2_1
SOCKET_PATH="$TB_ROOT/deepseek_harness_runtime/vllm_relay.sock"
LOG_PATH="$TB_ROOT/logs/deepseek_harness_relay_max_v27_20260827.jsonl"

cd "$TB_ROOT"
exec "$TB_ROOT/harbor/.venv/bin/python" \
  "$TB_ROOT/deepseek_harness_unix_relay_v2.py" \
  --socket "$SOCKET_PATH" \
  --upstream http://127.0.0.1:8010 \
  --log "$LOG_PATH"
