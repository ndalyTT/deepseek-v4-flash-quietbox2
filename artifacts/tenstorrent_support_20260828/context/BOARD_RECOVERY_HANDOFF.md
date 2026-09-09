# Tenstorrent Board Recovery Handoff

## Request for the next Codex session

Read this entire file, then continue the recovery procedure below. Treat hardware
commands as serialized operations: never run two Tenstorrent commands at the
same time. Do not start the official Harness canary until the recovery checks
and one vLLM initialization have succeeded.

The user can resume with:

> Read `BOARD_RECOVERY_HANDOFF.md` and perform the post-power-cycle recovery.

## State before the cold power cycle

- Four P300C devices were visible.
- `tt-smi -r` succeeded.
- A standalone 4x1 TTNN mesh open/close succeeded with `MESH_SMOKE_OK`.
- The first subsequent vLLM server initialization failed before model weights
  loaded, with frozen ERISC heartbeats on device 0 virtual cores `29-25`,
  `28-25`, `24-25`, and `22-25`.
- Teardown also timed out returning active Ethernet core `29-25` to base
  firmware.
- No official Harness canary was run, so it remains unscored.
- Failure log:
  `terminal_bench_2_1/logs/vllm_server_deepseek_harness_max_v27_20260827_post_reboot.log`
- Failure log SHA-256:
  `0687321da09edb320876bf07843216cf9d35217adf52a7cc7c6a0272b600e804`
- Known software/firmware versions:
  - system firmware bundle: `19.11.0`
  - KMD: `2.9.0`
  - `tt-smi`: `5.3.0`
  - `tt-flash`: `3.10.0`

An ordinary host reboot and a logical board reset did not resolve the ERISC
failure. The next recovery action is a true cold power cycle that removes
auxiliary board power.

## Physical step the user must perform

1. Stop all Tenstorrent workloads.
2. Shut down the host completely with `sudo poweroff`.
3. Once it is off, disconnect or switch off the QuietBox power at the mains for
   at least 60 seconds. An OS reboot alone is not sufficient.
4. Restore power and boot the host.

If the user confirms that this full AC power removal has already happened,
continue with the post-power-cycle procedure. Do not ask them to repeat it.

## Post-power-cycle recovery procedure

First read the local TT device-usage skill at:

`tt-metal/.agents/skills/tt-device-usage/SKILL.md`

Then check that no TT workload is active. Do not indiscriminately kill unrelated
or system processes:

```bash
pgrep -af 'vllm|EngineCore|pytest|tracy|profiler|run_deepseek'
```

From `tt-metal`, run these commands one at a time and capture their output:

```bash
cd /home/ttuser/deepseekv4flash/tt-metal
timeout 60 tt-smi -ls --local
timeout 180 tt-smi -r
timeout 60 tt-smi -ls --local
```

If the reset is incomplete, the local skill permits one more bounded reset.
Do not loop resets indefinitely.

Run the 4x1 mesh smoke test:

```bash
env PYTHONPATH=build_Release TT_METAL_DISABLE_FABRIC_TWO_ERISC=1 \
  python_env/bin/python -c \
  'import ttnn; mesh=ttnn.open_mesh_device(ttnn.MeshShape(4,1), trace_region_size=0); ttnn.close_mesh_device(mesh); print("MESH_SMOKE_OK")'
```

If device listing, reset, or mesh open fails, stop and collect bounded triage
evidence. Do not launch vLLM or the Harness.

If the mesh test succeeds, verify the persistent firmware without changing it:

```bash
tt-smi -s
tt-flash verify
```

`tt-smi -r` is only a logical board reset; it does not reinstall firmware.
Failure of `tt-flash verify` because no local flash record exists is not by
itself proof of corrupt firmware. Preserve the exact output.

Next, launch the established vLLM server configuration exactly once. Use the
commands and environment from the prior handoff/logs; do not improvise a new
model configuration. Observe initialization before starting the official
Harness canary.

- If initialization succeeds, proceed with the planned bounded canary and
  record the result.
- If the same ERISC heartbeat/core failure recurs, stop. Do not loop resets,
  server launches, or firmware flashes. Collect triage and escalate to
  Tenstorrent support.

## Firmware reflash boundary

Do **not** reflash firmware merely because the runtime ERISC initializer failed.
The failure can have causes other than a corrupt persistent SPI image.

Reflashing is destructive and requires a separate explicit confirmation from
the user after reviewing `tt-flash verify` output. The version matching this
stack is `19.11.0`. If a reflash is explicitly authorized, the initial command
is:

```bash
tt-flash flash -d 19.11.0
tt-flash verify
```

Use stable power and no active TT workloads, and never interrupt the flash. Do
not add `--force`, `--allow-major-downgrades`, or `--no-reset` without direct
Tenstorrent support guidance. In particular, installed `tt-flash` describes
`--force` as forcing a ROM update.

If the same fixed ERISC cores fail after a true AC power cycle, or after a
verified image, preserve the logs and request Tenstorrent hardware/firmware
support rather than repeating recovery operations.
