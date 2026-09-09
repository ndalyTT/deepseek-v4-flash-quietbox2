#!/usr/bin/env bash
# Refresh this repository's working copy from the QuietBox2 workspace.
#
# Copies the shareable subset of /home/ttuser/deepseekv4flash into this repo:
# handoff docs, artifacts (minus session logs), the Terminal-Bench harness
# code/configs/logs, job metadata (no terminal recordings), the dsh toolchain
# manifest, and a regenerated Harbor patch. It never copies weights,
# virtualenvs, node binaries, or the raw Tracy captures.
set -euo pipefail

SRC=${SRC:-/home/ttuser/deepseekv4flash}
DST=${DST:-$(cd "$(dirname "$0")/.." && pwd)}

cp "$SRC/PAUSE_HANDOFF.md" "$SRC/BOARD_RECOVERY_HANDOFF.md" "$DST/"

rsync -a --delete \
  --exclude 'session_logs/' --exclude 'session-logs-*' \
  "$SRC/artifacts/" "$DST/artifacts/"

mkdir -p "$DST/terminal_bench_2_1"
rsync -a --delete \
  --exclude 'harbor/' --exclude 'dataset/' --exclude 'deepseek_harness_toolchain/' \
  --exclude 'jobs/' --exclude '__pycache__/' --exclude 'deepseek_harness_runtime/*.sock' \
  "$SRC/terminal_bench_2_1/" "$DST/terminal_bench_2_1/"

# Job metadata only: result/config/trajectory JSON, text, and logs.
rsync -a --delete --prune-empty-dirs \
  --include '*/' --include '*.json' --include '*.txt' --include '*.log' --exclude '*' \
  "$SRC/terminal_bench_2_1/jobs/" "$DST/terminal_bench_2_1/jobs/"

mkdir -p "$DST/terminal_bench_2_1/deepseek_harness_toolchain"
cp "$SRC/terminal_bench_2_1/deepseek_harness_toolchain/manifest.json" \
   "$SRC/terminal_bench_2_1/deepseek_harness_toolchain/checksums.sha256" \
   "$DST/terminal_bench_2_1/deepseek_harness_toolchain/"

# Harbor local modifications as one patch (tracked diff + untracked new files).
mkdir -p "$DST/patches"
HARBOR="$SRC/terminal_bench_2_1/harbor"
HEAD=$(git -C "$HARBOR" rev-parse --short HEAD)
PATCH="$DST/patches/harbor-${HEAD}-deepseek-terminus.patch"
git -C "$HARBOR" diff > "$PATCH"
for f in $(git -C "$HARBOR" ls-files -o --exclude-standard); do
  git -C "$HARBOR" diff --no-index -- /dev/null "$f" >> "$PATCH" || true
done

echo "synced to $DST"
find "$DST" -type f -size +50M -not -path '*/.git/*' | sed 's/^/WARNING >50MB: /'
