# CUST-901 intermittency check — 2026-09-17 19:25 UTC

Requested by Tenstorrent FW support on 2026-09-15: run the standalone
tt-metal fabric smoke several times, then the full vLLM launch. Run by
`terminal_bench_2_1/run_cust901_intermittency_check.sh` (SMOKE_RUNS=3).

## Outcome: the ERISC failure reproduced in the standalone smoke, on 19.13.1.0

| Step | Time (UTC) | Result |
|---|---|---|
| Preflight | 19:25:47 | No TT workload, four P300C visible, firmware bundle 19.13.1.0, tt-metal `d788873210`, worktree clean except two untracked Tracy dirs |
| Smoke 1 | 19:25:48 - 19:25:52 | **PASS**: fabric initialized on 4 devices, 4x1 mesh, exact all-reduce, `MESH_CLOSE_OK`, `FABRIC_DISABLED` |
| Smoke 2 | 19:25:52 - 19:26:37 | **FAIL** (exit 134, abort). Device 0 virtual core 29-25 never returned to base firmware |
| vLLM launch | not run | The script stops at the first non-pass, as designed |

Smoke 2 failed inside `ttnn.open_mesh_device`, in
`RiscFirmwareInitializer::run_launch_phase -> reset_cores ->
assert_active_ethernet_cores_to_reset ->
return_to_base_firmware_and_wait_for_heartbeat` after 20 s:

```text
Device 0: Virtual core 29-25, Port status: 0x1, Retrain count: 0x0, Rx link up: 0x1,
Train status: 0x2, PCS status: 0x1, SerDes reset status: 0x1, Postcode: 0xc0dea000, ERISC0 ...
TT_THROW: Device 0: Timed out while waiting for active ethernet core 29-25 to become
active again. Try resetting the board. Minimum tt-firmware version is 18.10.0
```

`MetalContext::teardown` then hit the same 20 s wait on the same core and the
process aborted. Full log: `logs/fabric_smoke_2.txt`.

## Why this matters

- Same device and same core (29-25) as every Aug 27/28 vLLM failure, but now
  on firmware bundle 19.13.1.0 and with no vLLM, no model code, and no weights.
- Smoke 1 passed four seconds earlier and closed cleanly. Smoke 2 could not
  return ERISC0 on 29-25 to base firmware. That is the same shape as Aug 27:
  a clean server exit at 20:55 UTC, then the next fabric init failed on 29-25.
- This answers the support question directly: the tt-metal smoke does **not**
  pass every time. The failure is intermittent or state dependent and is not
  specific to the vLLM integration layer.
- Both runs used `TT_METAL_DISABLE_FABRIC_TWO_ERISC=1` (single-ERISC mode,
  RELAXED_INIT). The Nemotron container that ran 2026-09-16/17 on this host
  used two-ERISC mode and STRICT_INIT and initialized fabric without error.

## Board state after the failure (no reset performed)

`logs/post_smoke_failure_tt_smi_list.txt`: all four boards visible and
resettable. `logs/post_smoke_failure_tt_smi_status.json`: fw 19.13.1.0 on
all four, DRAM healthy, ARC heartbeat counters advancing, 41-44 C, 22-25 W,
AICLK 1350 MHz. `ETH_LIVE_STATUS` read 0xc140000 on devices 0 and 2 and
0x5c0000 on devices 1 and 3, versus 0xc143edf idle before any fabric run.

No board reset, firmware action, or vLLM launch was performed after the
failure. The one bounded logical reset from the recovery contract was
attempted and blocked by the session's permission policy; it is left for
the owner.

## Files

- `RUN.log` — timeline. `FIRMWARE_BUNDLE.txt`, `TT_METAL_COMMIT.txt`,
  `TT_METAL_WORKTREE_STATUS.txt`, `SMOKE_SOURCE_SHA256.txt`, `UNAME.txt`,
  `HOST_BOOT_TIME.txt` — provenance.
- `logs/preflight_*` — processes, containers, device list, telemetry.
- `logs/fabric_smoke_1.txt` (pass), `logs/fabric_smoke_2.txt` (fail),
  `logs/fabric_smoke_{1,2}_exit.txt`.
- `logs/post_smoke_failure_tt_smi_list.txt`,
  `logs/post_smoke_failure_tt_smi_status.json`.
- `MANIFEST.sha256` — checksums of every other file.
