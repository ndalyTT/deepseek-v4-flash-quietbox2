#!/usr/bin/env bash
# CUST-901 intermittency check requested by Tenstorrent FW support on
# 2026-09-15: run the standalone tt-metal fabric smoke several times, then
# immediately launch the unchanged DeepSeek harness vLLM server once.
#
# Serialized and bounded. Never resets, never flashes, never loops on
# failure. Refuses to start while any other TT workload owns the devices.
#
# Usage:  terminal_bench_2_1/run_cust901_intermittency_check.sh
# Env:    SMOKE_RUNS (default 3)   VLLM_READY_TIMEOUT seconds (default 2700)
# Exit:   0 smoke(s) passed and vLLM reached /health (server left running)
#         2 preflight refused      3 a smoke run did not pass
#         4 vLLM launch failed     5 vLLM did not become ready in time
set -uo pipefail

WS=/home/ttuser/deepseekv4flash
TTM=$WS/tt-metal
SMOKE_RUNS=${SMOKE_RUNS:-3}
VLLM_READY_TIMEOUT=${VLLM_READY_TIMEOUT:-2700}
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT=$WS/artifacts/cust901_intermittency_$TS
mkdir -p "$OUT/logs"
log() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$OUT/RUN.log"; }
finish() {
  ( cd "$OUT" && find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256 )
  log "artifacts: $OUT (exit $1)"; exit "$1"
}

log "CUST-901 intermittency check start; SMOKE_RUNS=$SMOKE_RUNS"
uname -a > "$OUT/UNAME.txt"; uptime -s > "$OUT/HOST_BOOT_TIME.txt"

# ---- 0. preflight -----------------------------------------------------------
pgrep -af 'vllm|EngineCore|pytest|tracy|run_deepseek|harbor|deepseek_harness' \
  | grep -v -e "$$" -e 'run_cust901_intermittency_check' > "$OUT/logs/preflight_processes.txt" || true
if [ -s "$OUT/logs/preflight_processes.txt" ]; then
  log "REFUSE: TT workload processes present (see logs/preflight_processes.txt)"; finish 2
fi
docker ps --format '{{.Names}}\t{{.Image}}' 2>/dev/null | grep -E '^tt-model-|tt-inference' > "$OUT/logs/preflight_containers.txt" || true
if [ -s "$OUT/logs/preflight_containers.txt" ]; then
  log "REFUSE: a model-serving container holds /dev/tenstorrent; the owner must stop it first:"
  cat "$OUT/logs/preflight_containers.txt" | tee -a "$OUT/RUN.log"; finish 2
fi
if ! timeout 60 tt-smi -ls --local > "$OUT/logs/preflight_tt_smi_list.txt" 2>&1; then
  log "REFUSE: tt-smi -ls --local failed"; finish 2
fi
timeout 60 tt-smi -s > "$OUT/logs/preflight_tt_smi_status.json" 2>&1 || log "warn: tt-smi -s failed"
FW=$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(",".join(sorted({x["firmwares"]["fw_bundle_version"] for x in d["device_info"]})))' "$OUT/logs/preflight_tt_smi_status.json" 2>/dev/null || echo unknown)
echo "$FW" > "$OUT/FIRMWARE_BUNDLE.txt"
log "firmware bundle(s): $FW  (Aug 27/28 failures were on 19.11.0.0)"
git -C "$TTM" rev-parse HEAD > "$OUT/TT_METAL_COMMIT.txt"
git -C "$TTM" status --short > "$OUT/TT_METAL_WORKTREE_STATUS.txt"

# ---- 1. repeated fabric smoke (Aug 31 EXACT_COMMAND semantics) ------------
SMOKE=$TTM/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/multichip_decoder/triage/canonical_quietbox_fabric_smoke.py
sha256sum "$SMOKE" > "$OUT/SMOKE_SOURCE_SHA256.txt"
for i in $(seq 1 "$SMOKE_RUNS"); do
  L=$OUT/logs/fabric_smoke_$i.txt
  log "smoke run $i/$SMOKE_RUNS"
  ( cd "$TTM" && timeout 180 env -u TT_MESH_GRAPH_DESC_PATH -u TT_METAL_DISABLE_MULTI_AERISC \
      PYTHONPATH=build_Release PYTHONUNBUFFERED=1 TT_METAL_DISABLE_FABRIC_TWO_ERISC=1 \
      TRACE_REGION_SIZE=268435456 ROUTER_PAYLOAD_BYTES=4352 \
      python_env/bin/python "$SMOKE" ) > "$L" 2>&1
  RC=$?
  echo "$RC" > "$OUT/logs/fabric_smoke_${i}_exit.txt"
  if [ "$RC" -eq 0 ] && grep -q '^SMOKE_PASS' "$L" && grep -q 'MESH_CLOSE_OK' "$L"; then
    log "smoke run $i: PASS"
  else
    log "smoke run $i: FAIL (exit $RC). Stopping; no reset, no retry."
    grep -nE 'Timeout|failed to initialize|TT_THROW|Error' "$L" | head -20 | tee -a "$OUT/RUN.log"
    sleep 5; timeout 60 tt-smi -ls --local > "$OUT/logs/post_smoke_failure_tt_smi_list.txt" 2>&1 || true
    finish 3
  fi
done

# ---- 2. one full DeepSeek harness vLLM launch, immediately -----------------
VLOG=$WS/terminal_bench_2_1/logs/vllm_server_deepseek_harness_max_v27_${TS}_cust901.log
log "launching DeepSeek harness vLLM server; log $VLOG"
setsid script -q -f -c "$WS/terminal_bench_2_1/run_deepseek_v4_harness_server.sh" "$VLOG" </dev/null >/dev/null 2>&1 &
SPID=$!
echo "$SPID" > "$OUT/VLLM_SCRIPT_PID.txt"
T0=$(date +%s)
while :; do
  if curl -fsS -m 5 http://127.0.0.1:8010/health >/dev/null 2>&1; then
    curl -fsS -m 10 http://127.0.0.1:8010/v1/models > "$OUT/logs/vllm_models.json" 2>&1
    log "vLLM READY after $(( $(date +%s) - T0 )) s; server left running (script pid $SPID)."
    grep -nE 'firmware bundle|Setting fabric config|Fabric initialized on|Application startup' "$VLOG" | head -12 | tee -a "$OUT/RUN.log"
    cp "$VLOG" "$OUT/logs/" ; finish 0
  fi
  if grep -qE 'failed to initialize FW|waiting for physical cores to finish|Timed out while waiting for active ethernet core' "$VLOG" 2>/dev/null; then
    log "vLLM FAILED with ERISC/firmware-init signature:"
    grep -nE 'firmware bundle|Setting fabric config|Timeout|failed to initialize|Timed out' "$VLOG" | head -12 | tee -a "$OUT/RUN.log"
    timeout 180 tail --pid="$SPID" -f /dev/null; sleep 5
    timeout 60 tt-smi -ls --local > "$OUT/logs/post_vllm_failure_tt_smi_list.txt" 2>&1 || true
    cp "$VLOG" "$OUT/logs/"; finish 4
  fi
  if ! kill -0 "$SPID" 2>/dev/null; then
    log "vLLM process exited before readiness (see log)"; tail -40 "$VLOG" >> "$OUT/RUN.log"
    sleep 5; timeout 60 tt-smi -ls --local > "$OUT/logs/post_vllm_exit_tt_smi_list.txt" 2>&1 || true
    cp "$VLOG" "$OUT/logs/"; finish 4
  fi
  if [ $(( $(date +%s) - T0 )) -ge "$VLLM_READY_TIMEOUT" ]; then
    log "vLLM not ready after $VLLM_READY_TIMEOUT s; leaving it running for inspection"
    cp "$VLOG" "$OUT/logs/"; finish 5
  fi
  sleep 15
done
