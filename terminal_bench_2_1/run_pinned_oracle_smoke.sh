#!/usr/bin/env bash
set -euo pipefail

HARBOR_ROOT=/home/ttuser/deepseekv4flash/terminal_bench_2_1/harbor

cd "$HARBOR_ROOT"
exec uv run harbor run \
  --config /home/ttuser/deepseekv4flash/terminal_bench_2_1/config_oracle_pinned_smoke.yaml \
  --yes
