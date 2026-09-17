# CUST-901 check, run 3 — DeepSeek vLLM as the first fabric init after reset

2026-09-17 20:40 UTC, `SMOKE_RUNS=0`, immediately after one `tt-smi -r`.

| Time (UTC) | Event |
|---|---|
| 20:40:21 | `run_deepseek_v4_harness_server.sh` launched (unchanged launcher: 4x1 mesh, `FABRIC_1D_RING`, `RELAXED_INIT`, `TT_METAL_DISABLE_FABRIC_TWO_ERISC=1`) |
| 20:40:31 | UMD: firmware bundle 19.13.1 |
| 20:40:32 | `Fabric initialized on 4 devices` |
| 21:04:37 | `/health` 200 after 1456 s; `/v1/models` lists `deepseek-ai/DeepSeek-V4-Flash-0731`, max_model_len 131072 |

First successful fabric-enabled DeepSeek vLLM launch since 2026-08-27
20:55 UTC. The server was left running for the Terminal-Bench v27 canary.
Logs: `logs/vllm_server_deepseek_harness_max_v27_20260917T204020Z_cust901.log`,
`logs/vllm_models.json`. No `tt-smi` was run while the server owned the devices.
