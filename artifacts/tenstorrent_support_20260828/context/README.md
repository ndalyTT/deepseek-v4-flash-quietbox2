# Post-power-cycle board recovery result

Date: 2026-08-28 UTC

## Outcome

The true cold power cycle did not clear the vLLM firmware-initialization failure. Basic board discovery, logical reset, a standalone 4x1 TTNN mesh open/close, persistent status, focused Ethernet triage, and focused ARC triage all succeeded. The one permitted vLLM initialization then reproduced frozen ERISC heartbeats on the same four device-0 virtual cores as before the power cycle. The server failed before model weights loaded, and teardown again timed out on active Ethernet core `29-25`.

Per `BOARD_RECOVERY_HANDOFF.md`, no further reset, vLLM launch, firmware flash, relay launch, or official Harness canary was attempted. The official canary remains unscored. No matching TT, vLLM, relay, or Harness workload remained active at the final process check.

## Serialized recovery checks

1. `pgrep -af 'vllm|EngineCore|pytest|tracy|profiler|run_deepseek'`
   - Exit 1 with no output: no matching workload was active.
2. `timeout 60 tt-smi -ls --local`
   - Exit 0.
   - UMD chips 0, 1, 2, and 3 were all visible as Blackhole P300C devices and all four were listed as resettable.
3. `timeout 180 tt-smi -r`
   - Completed with no console output.
4. `timeout 60 tt-smi -ls --local`
   - Exit 0.
   - All four P300C devices returned in both the available and resettable lists. A second reset was not needed.
5. `env PYTHONPATH=build_Release TT_METAL_DISABLE_FABRIC_TWO_ERISC=1 python_env/bin/python -c 'import ttnn; mesh=ttnn.open_mesh_device(ttnn.MeshShape(4,1), trace_region_size=0); ttnn.close_mesh_device(mesh); print("MESH_SMOKE_OK")'`
   - Exit 0 with `MESH_SMOKE_OK`.
   - Topology discovery reported firmware bundle 19.11.0 and KMD 2.9.0.
6. `tt-smi -s`
   - Exit 0.
   - All four devices reported firmware bundle 19.11.0.0, healthy DRAM, and zero corrected or uncorrected GDDR errors.
7. `tt-flash verify`
   - Exit 1 before verification began.
   - Exact terminal error:

     ```text
     Traceback (most recent call last):
       File "/home/ttuser/.tenstorrent-venv/bin/tt-flash", line 10, in <module>
         sys.exit(main())
                  ^^^^^^
       File "/home/ttuser/.tenstorrent-venv/lib/python3.12/site-packages/tt_flash/main.py", line 230, in main
         parser, args = parse_args()
                        ^^^^^^^^^^^^
       File "/home/ttuser/.tenstorrent-venv/lib/python3.12/site-packages/tt_flash/main.py", line 195, in parse_args
         if args.fwbundle is None and args.fw_tar is None and args.download is None:
                                                              ^^^^^^^^^^^^^
     AttributeError: 'Namespace' object has no attribute 'download'
     ```

   - This is a `tt-flash` CLI argument-parsing failure, not a successful or failed image-verification verdict. No flash command was run.

## One permitted vLLM initialization

The unchanged established launcher was run exactly once:

```text
/home/ttuser/deepseekv4flash/terminal_bench_2_1/run_deepseek_v4_harness_server.sh
```

The server used the established 4x1 configuration, `TT_METAL_DISABLE_FABRIC_TWO_ERISC=1`, firmware 19.11.0, max model length 131072, and the v27 TT additional configuration. It started at 15:32:54 UTC. At 15:33:15 UTC, device 0 reported unchanged heartbeats on these virtual cores:

| Virtual core | Heartbeat start/end | Changed |
|---|---|---|
| `29-25` | `0xabcd1626` | false |
| `28-25` | `0xabcd3508` | false |
| `24-25` | `0xabcde63c` | false |
| `22-25` | `0xabcda8af` | false |

The initializer raised:

```text
Device 0: Timeout (10000 ms) waiting for physical cores to finish: 29-25, 28-25, 24-25, 22-25.
Device 0 init: failed to initialize FW! Try resetting the board.
```

At 15:33:36 UTC teardown raised:

```text
Device 0: Timed out while waiting for active ethernet core 29-25 to become active again.
```

The script exited 1 at 15:33:38 UTC. The full log is:

```text
/home/ttuser/deepseekv4flash/terminal_bench_2_1/logs/vllm_server_deepseek_harness_max_v27_20260828_post_power_cycle.log
```

## Bounded triage

The default triage report had no live Inspector data and therefore skipped device-specific checks. A focused all-device capture then completed successfully:

- Devices 0 through 3 were visible as Blackhole P300 devices.
- ARC firmware: 19.11.0 on every device.
- Flash bundle: 19.11.0.0 on every device.
- Ethernet firmware: 1.11.0 on every device.
- `check_eth_status`: pass.
- ARC heartbeats: live on all four devices at approximately 10 heartbeats/s.

The triage requirements temporarily needed `tt-umd` 0.9.9. After evidence collection, `tt-umd` was restored to 0.9.5 for `tt-smi` 5.3.0 and the newly added triage packages were removed. A final `pip check` still reported the already-installed `tt-flash` 3.10.0 requirement mismatch (`PyYAML==6.0.2` required, PyYAML 6.0.3 installed); this was not changed during recovery.

## Escalation recommendation

Request Tenstorrent hardware/firmware support. Provide this report, the full vLLM log, and the focused triage report. The fixed device-0 ERISC-core set survives a true AC power removal even though standalone mesh open/close and post-failure ARC/Ethernet checks pass. Do not repeat resets or server launches, and do not reflash without a separate explicit user authorization after Tenstorrent reviews the evidence and the broken `tt-flash verify` environment.
