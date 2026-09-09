#!/usr/bin/env bash
set -o pipefail

cd /home/ttuser/deepseekv4flash/tt-metal || exit 1

timeout 180 env \
  -u TT_MESH_GRAPH_DESC_PATH \
  -u TT_METAL_DISABLE_MULTI_AERISC \
  PYTHONPATH=build_Release \
  PYTHONUNBUFFERED=1 \
  TT_METAL_DISABLE_FABRIC_TWO_ERISC=1 \
  TRACE_REGION_SIZE=268435456 \
  ROUTER_PAYLOAD_BYTES=4352 \
  python_env/bin/python \
  models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/multichip_decoder/triage/canonical_quietbox_fabric_smoke.py
