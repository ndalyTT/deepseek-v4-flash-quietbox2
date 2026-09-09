# Support request: persistent P300C ERISC initialization failure after AC power removal

## Requested assistance

Please help determine whether this is a known Blackhole ERISC/firmware defect, a board or link fault, or a software-stack compatibility problem, and provide a safe recovery or upgrade path. We have stopped further device operations to avoid obscuring evidence or repeatedly wedging the Ethernet cores.

Suggested subject:

> QuietBox2: four-chip P300C fabric initialization repeatedly freezes fixed device-0 ERISC cores after true AC power cycle (FW 19.11.0, KMD 2.9.0)

## Executive summary

- System: QuietBox2 with four visible Blackhole P300C ASICs across two dual-chip P300C boards.
- Firmware bundle: 19.11.0.0; Blackhole Ethernet firmware: 1.11.0.
- KMD: 2.9.0.
- `tt-smi`: 5.3.0; management-environment `tt-umd`: 0.9.5; `pyluwen`: 0.8.5.
- tt-metal commit: `5114991f9f7c59d21a1c9420ca9b6ee910678dc6`.
- vLLM TT plugin commit: `e3fc84941bf7a1d0df32aae2c50d539259c925f0`.
- vLLM: 0.25.1.
- The same 4x1 `FABRIC_1D_RING` plus `RELAXED_INIT` configuration successfully initialized at 17:36 UTC on 2026-08-27 and served until 20:55 UTC.
- Starting at 22:44 UTC, every subsequent fabric-enabled vLLM initialization failed before model weights loaded on the same device-0 virtual cores: `29-25`, `28-25`, `24-25`, and `22-25`.
- An ordinary host reboot, bounded logical reset, and true cold power cycle with QuietBox mains power removed for at least 60 seconds did not change the failed core set.
- Basic device listing, reset/list, a 4x1 TTNN mesh open/close without fabric enabled, `tt-smi -s`, and focused post-failure ARC/Ethernet triage all pass.
- No PCIe AER, PCIe, or IOMMU error appears in the current-boot filtered kernel log.
- The official evaluation canary was never run and remains unscored.
- No firmware flash was attempted.

## Hardware identity

| UMD device | PCI BDF | Board identity | ASIC location | Triage unique ID |
|---:|---|---|---:|---|
| 0 | `0000:01:00.0` | `000004613193402c` | 1 | `0x8c2632680581` |
| 1 | `0000:02:00.0` | `000004613193402c` | 0 | `0x8c2632680580` |
| 2 | `0000:03:00.0` | `0000046131935060` | 1 | `0x8c26326a0c01` |
| 3 | `0000:04:00.0` | `0000046131935060` | 0 | `0x8c26326a0c00` |

All endpoints enumerated at PCIe Gen4 x4 after the cold boot. The recurring failure is on UMD device 0, the ASIC-location-1 chip of board `000004613193402c`.

## Exact failure signature

During fabric-enabled mesh initialization, all four cores report a live link but an unchanged ERISC heartbeat. The post-power-cycle values were:

| Device | Virtual core | Port status | RX link | Train status | Heartbeat start/end | Changed |
|---:|---|---|---|---|---|---|
| 0 | `29-25` | `0x1` | up | `0x2` | `0xabcd1626` | false |
| 0 | `28-25` | `0x1` | up | `0x2` | `0xabcd3508` | false |
| 0 | `24-25` | `0x1` | up | `0x2` | `0xabcde63c` | false |
| 0 | `22-25` | `0x1` | up | `0x2` | `0xabcda8af` | false |

The initializer then raises:

```text
Device 0: Timeout (10000 ms) waiting for physical cores to finish: 29-25, 28-25, 24-25, 22-25.
Device 0 init: failed to initialize FW! Try resetting the board.
```

Teardown subsequently raises:

```text
Device 0: Timed out while waiting for active ethernet core 29-25 to become active again.
```

The four-core set is identical in all four included failure logs.

## Timeline

| UTC time | Action and result |
|---|---|
| 2026-08-27 17:36:20 | Same 4x1 ring fabric and relaxed initialization enabled. |
| 2026-08-27 17:36:23 | Four-device mesh created successfully. |
| 2026-08-27 17:36 onward | vLLM initialized, model loaded, API became ready, and the server ran until 20:55. |
| 2026-08-27 22:44 | First fixed-core ERISC initialization failure. |
| 2026-08-27 22:46 | One retry reproduced the identical fixed-core failure. |
| 2026-08-27 23:28 | After host reboot and logical recovery, identical failure. |
| 2026-08-28 before 15:26 | Host powered off; QuietBox mains/auxiliary power removed for at least 60 seconds; power restored and host booted. |
| 2026-08-28 15:30-15:31 | No TT workload active; list/reset/list passed with all four devices; standalone 4x1 mesh open/close passed with `MESH_SMOKE_OK`. |
| 2026-08-28 15:31 | `tt-smi -s` showed all four devices, firmware 19.11.0.0, healthy DRAM, and zero GDDR corrected/uncorrected errors. |
| 2026-08-28 15:32:53 | One permitted post-power-cycle vLLM launch began. |
| 2026-08-28 15:33:15 | Same four device-0 ERISC cores timed out before weights loaded. |
| 2026-08-28 15:33:36 | Teardown timed out returning core `29-25` to base firmware. |
| 2026-08-28 15:35 | Focused all-device triage passed Ethernet status and observed live ARC heartbeats on all devices at approximately 10/s. |

## Reproduction

The exact failed launcher is included as `config/run_deepseek_v4_harness_server.sh`. Its hardware-relevant configuration is:

```text
MESH_DEVICE=(4,1)
TT_METAL_DISABLE_FABRIC_TWO_ERISC=1
FabricConfig.FABRIC_1D_RING
FabricReliabilityMode.RELAXED_INIT
trace_region_size=268435456
l1_small_size=2048
```

It calls `ttnn.set_fabric_config(...)` before `ttnn.open_mesh_device(...)`, then fails in `RiscFirmwareInitializer::initialize_and_launch_firmware` before model weights load.

The latest known-good launcher is included as `config/run_deepseek_v4_server.sh`. A diff is included at `context/launcher_diff.patch`; the only launcher differences are `--enable-auto-tool-choice` and `--tool-call-parser deepseek_v4`. The mesh, fabric, reliability, model, memory, and trace settings are identical.

The standalone recovery smoke used the same 4x1 mesh and `TT_METAL_DISABLE_FABRIC_TWO_ERISC=1`, but did not call `ttnn.set_fabric_config`. It therefore proves basic mesh/device open and close, not fabric ERISC initialization.

## Recovery and health evidence

1. No `vllm`, `EngineCore`, pytest, Tracy, profiler, relay, or Harness process was active before recovery or after failure.
2. `timeout 60 tt-smi -ls --local`: all four devices visible and resettable.
3. `timeout 180 tt-smi -r`: completed.
4. Second bounded list: all four devices visible and resettable; no second reset needed.
5. Standalone 4x1 mesh open/close: exit 0 with `MESH_SMOKE_OK`.
6. `tt-smi -s`: firmware 19.11.0.0 on all devices, healthy DRAM, zero GDDR corrected/uncorrected errors.
7. Focused `tt-triage --dev=all`: all four devices visible; firmware versions consistent; `check_eth_status` passed; ARC heartbeats live on all devices.
8. Current-boot kernel log: four Tenstorrent endpoints enumerated at Gen4 x4; KMD 2.9.0 loaded; no matching AER/PCIe/IOMMU fault after enumeration.
9. No reset, vLLM relaunch, canary, or flash was attempted after the post-power-cycle recurrence.

## Firmware verification issue

`tt-flash verify` did not reach the hardware verification stage. Installed `tt-flash` 3.10.0 crashed during argument parsing:

```text
AttributeError: 'Namespace' object has no attribute 'download'
```

The traceback is included in `context/tt_flash_verify_failure.txt`. The official v3.10.0 source appears to define `download` only for the `flash` subparser and then access `args.download` in shared validation, which matches this failure. The environment also has PyYAML 6.0.3 while the installed `tt-flash` metadata requires exactly 6.0.2. We did not patch the tool, run a different build, or attempt a flash.

## Potentially related public Tenstorrent information

- `tenstorrent/tt-metal#25553` reports a Blackhole Ethernet mailbox/active-core timeout and explicitly notes an earlier `Device 0 init: failed to initialize FW!` error. It was closed as a duplicate of #25427.
- `tenstorrent/tt-metal#25427` describes nondeterministic ERISC0 instability on Blackhole multi-chip systems, with higher failure rates as more systems are connected. It notes that slow dispatch made tests more likely to succeed.
- System firmware 19.11.0 uses Blackhole ERISC firmware 1.11.0.
- System firmware 19.12.0 uses Blackhole ERISC firmware 1.12.0 and its release notes describe reworked runtime link-check and recovery logic.

Links and notes are collected in `context/public_references.md`. These are possible matches, not a claim that the same root cause has been proven.

## Questions for Tenstorrent

Please answer these in priority order if possible:

1. Does this fixed-core signature match the known Blackhole multi-chip ERISC instability tracked in tt-metal issues #25427/#25553 or an internal successor issue?
2. Is firmware 19.11.0/ERISC 1.11.0 validated for this P300C QuietBox2 topology and tt-metal commit `5114991f9f7c59d21a1c9420ca9b6ee910678dc6`?
3. Do the ERISC 1.12 link-recovery changes in firmware 19.12.0 address this specific failure? If an upgrade is recommended, which exact stable firmware version, bundle checksum, KMD, UMD, tt-smi, and tt-flash versions form a validated set for this checkout?
4. Before any firmware change, which supported `tt-flash verify` version and exact command should be used? Is the 3.10.0 `args.download` crash a known defect?
5. Is `TT_METAL_DISABLE_FABRIC_TWO_ERISC=1` the correct and sufficient workaround for #25427 on this tt-metal revision, or is an additional patch/configuration required?
6. Do fixed virtual cores `29-25`, `28-25`, `24-25`, and `22-25` on device 0 identify a specific physical link, cable group, SerDes block, or P300C ASIC fault? If so, what is the safe board/cable isolation procedure?
7. Should we run a minimal fabric-only reproducer that calls `set_fabric_config(FABRIC_1D_RING, RELAXED_INIT)` and opens/closes the 4x1 mesh without vLLM? Please provide the preferred command and triage environment if you want this test, because it may wedge the same cores and require another cold cycle.
8. Would a slow-dispatch comparison provide useful evidence, or would it only mask the known timing-sensitive ERISC issue?
9. Should `RELAXED_INIT` be retained for this topology, or do you want a bounded `STRICT_INIT` diagnostic to expose a link mismatch?
10. Which additional low-level capture should be collected on the next reproduction: Inspector RPC logs, fabric telemetry, ERISC callstacks, watcher ringbuffer, `tt-exalens`, or a support-specific diagnostic build?
11. Given that generic `check_eth_status` and ARC heartbeats pass after the failure, which targeted health check can detect this fabric-firmware state without launching a model?
12. Do you recommend any physical action before a software/firmware change—cable reseat, board swap, or slot isolation—or should the current physical state be preserved for diagnosis?

## Actions intentionally not taken

- No firmware flash or ROM update.
- No `--force`, `--allow-major-downgrades`, or `--no-reset` option.
- No repeated reset loop.
- No additional vLLM launch after the post-power-cycle recurrence.
- No minimal fabric-only, slow-dispatch, strict-init, cable-swap, or board-swap experiment.
- No official Harness canary.
- No deletion or reset of the development worktrees.

## Artifact map

### Primary evidence

- `logs/failures/vllm_server_deepseek_harness_max_v27_20260828_post_power_cycle.log` — definitive post-AC-cycle recurrence.
- `logs/failures/vllm_server_deepseek_harness_max_v27_20260827_post_reboot.log` — recurrence after ordinary host reboot.
- `logs/failures/vllm_server_deepseek_harness_max_v27_20260827.log` — first recorded fixed-core failure.
- `logs/failures/vllm_server_deepseek_harness_max_v27_20260827_retry1.log` — one bounded retry, identical signature.
- `logs/known_good/vllm_server_selective_bfp4_salience8_bounded_program_cache_20260827.log` — latest full known-good same-fabric run.
- `context/log_signature_comparison.txt` — decisive timestamps and signatures extracted from those logs.

### Recovery and triage

- `context/README.md` — completed recovery report.
- `context/BOARD_RECOVERY_HANDOFF.md` — pre-power-cycle state and bounded procedure.
- `triage/tt-triage-all-devices.txt` — focused machine-readable device, firmware, Ethernet, and ARC results.
- `triage/triage-summary-all-devices.txt` — focused summary.
- `triage/tt-triage.txt` and `triage/triage-summary.txt` — initial no-live-Inspector capture.

### Configuration and reproducibility

- `config/run_deepseek_v4_harness_server.sh` — exact failed launcher.
- `config/run_deepseek_v4_server.sh` — exact latest known-good launcher.
- `config/config_canary_fix_git_deepseek_harness_max_v27.yaml` — planned but unrun canary configuration.
- `context/launcher_diff.patch` — exact launcher difference.
- `environment/software_versions.txt` — host and vLLM Python package versions.
- `environment/repository_revisions.txt` — repository commits.
- `environment/tt-metal-worktree-status.txt` — uncommitted tt-metal state, preserved for reproducibility.
- `environment/other-worktree-status.txt` — plugin/Harness/Harbor worktree state.
- `environment/runtime_hashes.txt` — runtime library and launcher hashes.
- `environment/umd_source_revision.txt` — UMD source revision embedded in tt-metal.

### Host and PCIe

- `environment/host.txt` — OS/host/CPU information.
- `environment/kernel_boot_filtered.log` — current-boot Tenstorrent/PCIe/AER/IOMMU kernel messages.
- `environment/lspci_tenstorrent.txt` — four Tenstorrent PCI functions and driver binding.
- `environment/lspci_tree.txt` — PCI topology.
- `environment/hugepages.txt` — hugepage allocation.

### Integrity and sanitization

- `MANIFEST.sha256` — SHA-256 for every file except the manifest itself.
- `SANITIZATION.txt` — credential-pattern scan result and excluded data classes.

## Contact note

The operator can perform another physical power cycle or support-directed test, but requests an exact serialized procedure. Please specify whether any test can leave ERISC or flash state unsafe and whether a full AC removal is required afterward.
