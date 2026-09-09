#!/usr/bin/env bash
set -euo pipefail

TB_ROOT=/home/ttuser/deepseekv4flash/terminal_bench_2_1
SOCKET_PATH="$TB_ROOT/deepseek_harness_runtime/vllm_relay.sock"
CONFIG_PATH="$TB_ROOT/config_canary_fix_git_deepseek_harness_max_v27.yaml"

curl -fsS http://127.0.0.1:8010/health >/dev/null
if [[ ! -S "$SOCKET_PATH" ]]; then
  printf 'DeepSeek Harness relay socket is not ready: %s\n' "$SOCKET_PATH" >&2
  exit 1
fi

export PYTHONPATH="$TB_ROOT:$TB_ROOT/harbor/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$TB_ROOT"
exec "$TB_ROOT/harbor/.venv/bin/harbor" jobs start \
  --config "$CONFIG_PATH" \
  --yes
