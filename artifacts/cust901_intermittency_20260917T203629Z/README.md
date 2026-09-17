# CUST-901 intermittency check, run 2 — 2026-09-17 20:36 UTC

Same script and settings as run 1 (`../cust901_intermittency_20260917T192547Z/`),
executed immediately after one `tt-smi -r` (logged in
`logs/recovery_tt_smi_reset.txt` of run 1's sibling command; the reset itself
completed on PCI indices 0-3).

| Step | Time (UTC) | Result |
|---|---|---|
| Smoke 1 | 20:36:30 - 20:36:34 | **PASS** |
| Smoke 2 | 20:36:34 - 20:37:18 | **FAIL** (exit 134): device 0 virtual core 29-25, `Postcode: 0xc0dea000`, `ERISC0 reset PC: 0x3560`, timed out returning to base firmware in `run_launch_phase -> reset_cores`; teardown hit the same wait and aborted |

Second reproduction of the pattern seen in run 1: after a reset the first
single-ERISC fabric initialization passes and closes cleanly; the very next
initialization cannot return ERISC0 on device 0 core 29-25 to base firmware.
Firmware 19.13.1.0, tt-metal `d788873210`, no vLLM.

Consequence acted on: after one more `tt-smi -r`, the DeepSeek vLLM server was
launched as the **first** fabric initialization (run 3, `SMOKE_RUNS=0`) and
came up normally. See `../cust901_intermittency_20260917T204020Z/`.
