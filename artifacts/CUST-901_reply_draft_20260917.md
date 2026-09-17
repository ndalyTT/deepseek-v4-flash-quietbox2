# Draft comment for CUST-901 (not posted)

Hi Aaron, thanks for taking a look. Answers and an update:

**1. Provenance of the `known_good` log.** Same system (this QB2, host
`tt-quietbox`), same host boot, and the same software components as the
failing launches: tt-metal `5114991f9f`, vllm-tt-plugin `e3fc8494`, vllm
0.25.1, firmware bundle 19.11.0, KMD 2.9.0, `FABRIC_1D_RING`, `RELAXED_INIT`,
`TT_METAL_DISABLE_FABRIC_TWO_ERISC=1`, 4x1 mesh. The known-good server
started 2026-08-27 17:36 UTC, served for 3 h 19 min, and exited cleanly at
20:55 UTC (exit 0). The first failing launch was at 22:44 UTC the same day on
the same boot. The only launcher difference is two vLLM CLI flags
(`--enable-auto-tool-choice --tool-call-parser deepseek_v4`), see
`context/launcher_diff.patch` in the bundle. Every subsequent fabric-enabled
launch (bounded retry, after host reboot, after AC power cycle) reproduced the
same four device-0 cores through 2026-08-28 15:33 UTC.

**2. Repeated smoke followed by the full vLLM test.** Agreed, and I have the
sequence scripted (N standalone smokes with no reset between, then the
unchanged vLLM launcher immediately after, logs and tt-smi snapshots bundled).
Two things changed on the host since the bundle that you should know before
we run it:

- The boards were updated to firmware bundle **19.13.1.0** on 2026-09-09
  (tt-installer 3.6.0 / tt-flash 3.10.0, flash and reset succeeded on all
  four). This was not done as a deliberate recovery step for this ticket, so
  the exact 19.11.0 condition is no longer reproducible here. I do not plan
  to downgrade unless you advise it.
- Since 2026-09-16 a different model (Nemotron 30B via the tt-model vLLM
  container, tt-metal `v0.74.0-dev20260622-202-gcfd2056ecb`, plugin
  `52db6438`) has been serving on all four devices with `FABRIC_1D_RING`,
  `STRICT_INIT`, two-ERISC mode. It logged `Fabric initialized on Device 0`
  and on all four devices at first try and has been healthy for over a day.
  That points toward your first hypothesis (vLLM/tt-metal integration or
  version specific, or state dependent) rather than a board fault.

I will run the smoke x3 + DeepSeek vLLM sequence on 19.13.1.0 as soon as the
devices are free and attach the bundle either way. If you would rather see a
specific `fabric_unit_tests` gtest or a longer smoke repetition count, tell me
and I will add it to the same run.
