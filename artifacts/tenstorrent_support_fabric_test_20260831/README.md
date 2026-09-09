# Standalone TT-Metal fabric test for Tenstorrent support

## Outcome

**PASS** on 2026-08-31. The standalone TT-Metal/TTNN fabric test exited 0.
It initialized `FABRIC_1D_RING` on all four P300C devices, opened the 4x1
mesh, completed an exact four-rank BF16 all-reduce, closed the mesh, and
disabled fabric cleanly.

This test did not launch vLLM, load model weights, or execute DeepSeek model
code.

## Why this test was run

Tenstorrent support suggested running a TT-Metal test that enables fabric
outside the vLLM workload. This test isolates fabric initialization and a
minimal collective from vLLM and the model while retaining the important
hardware/runtime settings from the failing vLLM initialization.

## System and source provenance

- System: QuietBox 2, four Blackhole P300C ASICs.
- Host boot time: `2026-08-28 15:25:42`.
- The host was not rebooted, logically reset, power-cycled, or flashed as part
  of this 2026-08-31 test procedure.
- Firmware detected by the test: `19.11.0`.
- Post-test firmware bundle: `19.11.0.0`; Ethernet firmware: `1.11.0`.
- KMD: `2.9.0`.
- TT-Metal commit: `5114991f9f7c59d21a1c9420ca9b6ee910678dc6`.
- TT-Metal description: `v0.78.0-dev20260821-49-g5114991f9f-dirty`.
- The individual reproducer file was clean in the worktree even though other,
  unrelated files make the overall checkout dirty.
- Reproducer SHA-256:
  `3f2a218f11a25019475525afeeb131876953cb7fe1ac2fe85dc2e66a58bde497`.

The tracked reproducer is copied into
`source/canonical_quietbox_fabric_smoke.py`. The exact invocation is preserved
in `EXACT_COMMAND.sh`.

## Preconditions and sequence

1. A self-excluding process search found no active vLLM, EngineCore, pytest,
   Tracy, profiler, or DeepSeek launcher process. The corresponding log is
   empty because there were no matches.
2. `timeout 60 tt-smi -ls --local` exited 0. All four P300C devices were
   visible and listed as resettable.
3. The standalone test was run exactly once under `timeout 180`.
4. No watcher, profiler, vLLM launch, reset, firmware verify, or firmware flash
   was run as part of the test.
5. Because the test passed and closed cleanly, no failure triage or recovery
   reset was necessary.
6. Post-test `tt-smi -ls --local` again showed all four devices visible and
   resettable. Post-test `tt-smi -s` exited 0.

For completeness, earlier on 2026-08-31 at approximately 14:27 UTC, pytest
collection-only was used to resolve the name of an existing QuietBox test. It
opened and closed the UMD during collection, but ran no test, did not enable
fabric, and did not open a mesh. There was no board reset between that
collection step and this fabric smoke.

## Exact fabric configuration

- `TT_MESH_GRAPH_DESC_PATH`: absent; runtime auto-discovery was used.
- `TT_METAL_DISABLE_MULTI_AERISC`: absent.
- `TT_METAL_DISABLE_FABRIC_TWO_ERISC=1`: single-ERISC fabric workaround.
- Fabric config: `FABRIC_1D_RING`.
- Reliability mode: `RELAXED_INIT`.
- Fabric Tensix config: disabled.
- Fabric UDM mode: disabled.
- Fabric manager: default.
- Router payload: `4352` bytes. This matches the effective default when the
  vLLM plugin calls `set_fabric_config` without a router override in this
  checkout.
- Mesh: `MeshShape(4, 1)`.
- `l1_small_size=2048`.
- `trace_region_size=268435456`.

## Decisive result

The complete output is in `logs/tt_metal_fabric_smoke.txt`. Its decisive lines
are:

```text
Fabric initialized on 4 devices
MESH_OPEN_OK shape=(4, 1) devices=4
RANK_0_EXACT=True ... unique=[4.0]
RANK_1_EXACT=True ... unique=[4.0]
RANK_2_EXACT=True ... unique=[4.0]
RANK_3_EXACT=True ... unique=[4.0]
COLLECTIVE_EXACT_OK ranks=4 expected_value=4.0
SMOKE_PASS
MESH_CLOSE_OK
FABRIC_DISABLED=FabricConfig.DISABLED
```

The process exit code, recorded in `TEST_EXIT_CODE.txt`, is `0`.

The only notable warning was:

```text
Unknown motherboard 'B850M-C' for chip_id=2 (bus_id=0x3) — falling back to bus_id as tray_id.
```

This warning was non-fatal in this run: auto-discovery produced a four-node
ring, fabric initialized, and the collective passed exactly.

## Post-test health

- All four devices remained visible and resettable.
- All four reported healthy DRAM at 16G.
- All four remained at PCIe Gen4 x4.
- All corrected GDDR counters were zero.
- All uncorrected GDDR counters were zero.
- No workload process from the test remained active.

See `logs/postflight_tt_smi_status.txt` for the full board telemetry and
firmware details.

## Interpretation and questions for support

This result proves that, at the time of this test, the same TT-Metal checkout
could initialize single-ERISC ring fabric and execute real fabric-backed data
movement on all four devices without vLLM. It means the previously reported
vLLM failure is not a continuously reproducible inability of this host to
initialize fabric.

It does **not** rule out an intermittent or state-dependent TT-Metal,
ERISC/firmware, link, or initialization-order problem. In particular, the
earlier vLLM failures occurred before model weights loaded and repeatedly froze
the same device-0 ERISC cores, including after a true AC power cycle.

Please advise:

1. Does this clean standalone pass, on the same host boot that previously
   produced the fixed-core failure, suggest a known intermittent ERISC or
   runtime-state issue?
2. Which additional vLLM initialization steps should be added incrementally to
   this passing reproducer to expose the relevant difference?
3. Would you prefer an official `fabric_unit_tests` gtest or a bounded repeated
   version of this exact smoke? We intentionally ran only once to avoid
   obscuring an intermittent board state.
4. Should the non-fatal `B850M-C` topology-discovery fallback be corrected or
   supplied with a supported motherboard mapping for this QuietBox 2?
5. Which fabric/ERISC telemetry should be enabled on the next vLLM reproduction
   without materially changing initialization timing?

## Artifact map

- `README.md` — this support-ready description and interpretation.
- `EXACT_COMMAND.sh` — exact standalone test command.
- `source/canonical_quietbox_fabric_smoke.py` — copied test source.
- `logs/preflight_active_processes.txt` — empty; no matching processes.
- `logs/preflight_tt_smi_list.txt` — four devices visible/resettable before.
- `logs/tt_metal_fabric_smoke.txt` — complete test output.
- `logs/postflight_tt_smi_list.txt` — four devices visible/resettable after.
- `logs/postflight_tt_smi_status.txt` — full post-test health and versions.
- `logs/postflight_active_processes.txt` — empty; no matching processes.
- `TEST_EXIT_CODE.txt` — standalone test exit code.
- `TT_METAL_COMMIT.txt`, `TT_METAL_DESCRIBE.txt` — source revision.
- `SOURCE_SHA256.txt`, `SOURCE_WORKTREE_STATUS.txt` — reproducer integrity and
  worktree state.
- `HOST_BOOT_TIME.txt`, `RUN_STARTED_UTC.txt`, `UNAME.txt` — time and host
  provenance.
- `MANIFEST.sha256` — integrity checksum for each artifact other than the
  manifest itself.
