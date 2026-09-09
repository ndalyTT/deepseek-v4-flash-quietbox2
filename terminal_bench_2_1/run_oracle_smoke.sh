#!/usr/bin/env bash
set -euo pipefail

HARBOR_ROOT=/home/ttuser/deepseekv4flash/terminal_bench_2_1/harbor
DATASET_ROOT=/home/ttuser/deepseekv4flash/terminal_bench_2_1/dataset/tasks
JOBS_ROOT=/home/ttuser/deepseekv4flash/terminal_bench_2_1/jobs

cd "$HARBOR_ROOT"
exec uv run harbor run \
  --path "$DATASET_ROOT" \
  --agent oracle \
  --n-tasks 5 \
  --n-attempts 1 \
  --n-concurrent 1 \
  --jobs-dir "$JOBS_ROOT" \
  --job-name tb21-oracle-environment-smoke \
  --yes
