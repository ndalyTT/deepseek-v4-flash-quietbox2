#!/usr/bin/env bash
set -euo pipefail

HARBOR_ROOT=/home/ttuser/deepseekv4flash/terminal_bench_2_1/harbor
export OPENAI_API_KEY=local-only

cd "$HARBOR_ROOT"
exec uv run harbor run \
  --config /home/ttuser/deepseekv4flash/terminal_bench_2_1/config_smoke.yaml \
  --yes
