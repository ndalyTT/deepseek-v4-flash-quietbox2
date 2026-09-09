# DeepSeek-V4-Flash-0731 on Tenstorrent QuietBox2

Bring-up, quantization, vLLM serving, performance qualification, and
Terminal-Bench 2.1 evaluation work for `deepseek-ai/DeepSeek-V4-Flash-0731` on a
QuietBox2 with four Blackhole P300C chips. Work ran 2026-08-21 to 2026-08-31,
mostly in autonomous Codex sessions, and is snapshotted here as of 2026-09-09.

- **Model code:** https://github.com/ndalyTT/tt-metal, branch
  `deepseek-v4-flash-0731-quietbox2` (HEAD `d788873210`). This is a fork
  branch, not a pull request to `tenstorrent/tt-metal`.
- **Weights:** the stock Hugging Face checkpoint
  `deepseek-ai/DeepSeek-V4-Flash-0731` at revision
  `7872f01b1d1fe23eabc4c98b48bffcef5a386062`. **The weights were not modified.**
  Quantization to Tenstorrent block-float formats happens at load time inside
  the tt-metal model code, so no derived checkpoint exists or was uploaded.
- **This repository:** everything around the model code. Handoff documents,
  evidence, the Terminal-Bench harness integration, Tenstorrent support
  bundles, and the pins needed to rebuild the environment.

If you are an agent, read `AGENTS.md` first.

## Status in one paragraph

The full 43-layer, 256-expert model is resident and serves through the
Tenstorrent vLLM plugin at tensor parallel 4, batch 1, context 131,072. The
stock checkpoint cannot fit (about 58 GB needed per device against 33.9 GB
usable), so routed-expert gate/up weights use TT BFP4_B in eight layers and
BFP2_B in the other 35, routed down and shared experts use BFP4_B, and dense
paths keep higher precision. The required eight-row ISL sweep at 512 output
tokens passed on 2026-08-27. The official DeepSeek Harness Terminal-Bench 2.1
canary is **unscored**: since 2026-08-27 22:44 UTC every fabric-enabled vLLM
launch freezes four device-0 ERISC cores before weights load. A host reboot, a
logical reset, and a true AC power cycle did not clear it. The case is open with
Tenstorrent support. A fabric-only standalone smoke passed on 2026-08-31.

## What was done

| Phase | Dates | Outcome | Evidence |
|---|---|---|---|
| Decoder bring-up: functional, fused, optimized, multichip, optimized-multichip | Aug 21-23 | All five stages complete; layer PCC at or above 0.995 | tt-metal branch `doc/*_decoder/`; session logs (release asset) |
| Capacity and quantization | Aug 22-27 | Stock model rejected for capacity; REAP K160 and MLX 2.4-bit rejected; exact-architecture mixed BFP2/BFP4 policy selected and quality-screened (85% top-1, 100% top-5 in the matched 20-token AIME check) | `artifacts/quantization/`, tt-metal `doc/datatype_sweep/`, `doc/full_model/` |
| Full-model serving | Aug 24-27 | Resident at 33.39 GB allocated per device, 0.52 GB free; padding bug that evicted real KV rows found and fixed | tt-metal `doc/full_model/`, `doc/vllm/` |
| Performance sweep, OSL 512 | Aug 27 | 8/8 rows passed, see table below | tt-metal `doc/vllm/...bounded_cache_required_sweep_osl512_20260827.json` |
| Terminal-Bench 2.1, local Terminus/DSML path | Aug 25-27 | Oracle smoke 1.0; every DeepSeek run 0.0 (20 canaries, two aborted full runs). Path judged non-representative of DeepSeek's official conditions | `terminal_bench_2_1/jobs/*/result.json`, `terminal_bench_2_1/logs/` |
| Terminal-Bench 2.1, official DeepSeek Harness path (v27) | Aug 27 | Built and preflighted end to end with a mock response; never scored | `terminal_bench_2_1/*_unix*`, `config_canary_fix_git_deepseek_harness_max_v27.yaml` |
| Hardware failure and escalation | Aug 27-31 | Device-0 ERISC freeze survives reboot and AC cycle; support bundles sent; fabric-only smoke passes | `artifacts/tenstorrent_support_20260828/`, `artifacts/tenstorrent_support_fabric_test_20260831/` |

### Final performance (OSL 512, batch 1, TP4, 4x1 mesh)

| ISL | TTFT ms | TPOT ms | E2EL ms | tokens/s/user | TTFT % of E2EL |
|---:|---:|---:|---:|---:|---:|
| 128 | 2,590.36 | 150.38 | 79,436.60 | 6.650 | 3.26 |
| 1,024 | 22,301.18 | 150.36 | 99,136.88 | 6.651 | 22.50 |
| 4,096 | 90,193.70 | 150.31 | 167,004.04 | 6.653 | 54.01 |
| 8,192 | 180,921.14 | 150.32 | 257,735.78 | 6.652 | 70.20 |
| 16,384 | 364,159.40 | 150.36 | 440,993.59 | 6.651 | 82.58 |
| 32,768 | 727,058.97 | 150.32 | 803,874.47 | 6.652 | 90.44 |
| 65,536 | 1,543,989.33 | 150.67 | 1,620,979.99 | 6.637 | 95.25 |
| 130,560 | 3,160,809.93 | 150.90 | 3,237,918.75 | 6.627 | 97.62 |

Model construction (about 24 minutes) is excluded from every row.

### Terminal-Bench 2.1

No score exists for the official DeepSeek Harness path. The `0.000` recorded in
`terminal_bench_2_1/jobs/` belongs to the superseded local Terminus/DSML path,
which differed from DeepSeek's published conditions (custom DSML actions,
reasoning disabled, 512-token output cap). The model card reports 82.7 under
DeepSeek's own harness. The v27 path reproduces those conditions: pinned
`@deepseek-ai/dsh@0.1.0-rc.6`, max reasoning, 49,152-token per-call cap,
exactly the `bash` and `str_replace_editor` tools, and a constrained
Unix-socket relay to loopback vLLM.

## Repository layout

| Path | What it is |
|---|---|
| `AGENTS.md` | Operating instructions and hard rules for agents |
| `PINS.md` | Every repository SHA, model revision, firmware and tool version |
| `REPRODUCE.md` | Environment setup and the exact serve, benchmark, and canary commands |
| `PAUSE_HANDOFF.md`, `BOARD_RECOVERY_HANDOFF.md` | Top-level handoffs (Aug 22, Aug 28) |
| `artifacts/*.md` | The rest of the handoff chain; `RESUME_AFTER_HOST_REBOOT_20260827.md` is authoritative |
| `artifacts/*.html` | Quickstart and Autoport Report deliverables (`.orig` are the pre-Aug-27 versions) |
| `artifacts/quantization/` | Raw PCC/NMSE records behind the quantization decision |
| `artifacts/tenstorrent_support_20260828/`, `artifacts/board_recovery_20260828/`, `artifacts/tenstorrent_support_fabric_test_20260831/` | Support escalation bundles with checksum manifests |
| `artifacts/hardware/` | tt-smi telemetry snapshot |
| `artifacts/*CHECKSUMS*.txt` | SHA-256 manifests for deliverables and evidence |
| `artifacts/export_codex_task_logs.py` | Exporter that produced the session logs |
| `terminal_bench_2_1/` | Harbor configs (v1 to v27), launchers, DeepSeek Harness adapters and relays, DSH profile, 147 logs, and per-job result/config/trajectory JSON |
| `terminal_bench_2_1/deepseek_harness_toolchain/` | Manifest and checksums for the Node 22 plus `dsh` rc.6 toolchain (binaries excluded) |
| `patches/harbor-6ecebe4-deepseek-terminus.patch` | Local Harbor modifications: Terminus 2 DeepSeek templates, parser, temperature handling, LiteLLM changes |
| `tools/sync_from_workspace.sh` | Refreshes this repo from the QuietBox2 workspace |

## What is deliberately not here

- **Weights.** Fetch `deepseek-ai/DeepSeek-V4-Flash-0731` at the pinned revision.
- **Session logs (1.1 GB JSONL).** Attached to the GitHub Release as
  `session-logs-final-post-reboot-20260827T2337Z.tar.gz`, SHA-256
  `4d6cd5ca2e2f7ea2b7df633210dd2df8580380930ed9db82d4b6cd3bf3a9523c`.
- **Raw Tracy captures (14.3 GB)** under the tt-metal branch's
  `doc/multichip_decoder/tracy/20260823/*/capture`. Host-only. The derived perf
  reports next to them are in the branch.
- **Terminal recordings** (`recording.cast`, `*.pane`, 6 GB) from Harbor jobs.
  Result, config, trajectory JSON, and logs are included.
- **Virtualenvs and binaries:** Harbor `.venv`, tt-metal `python_env` and
  `build_Release`, the Node binary, `dsh` `node_modules`.
- **Upstream checkouts** of vllm-tt-plugin, deepseek-harness, maka, Harbor, and
  the Terminal-Bench dataset. Clone them at the SHAs in `PINS.md`.

## Path assumptions

Scripts and YAML configs hardcode `/home/ttuser/deepseekv4flash` as the
workspace root. They are kept verbatim because checksums in the handoffs refer
to them. See `REPRODUCE.md` for how to relocate.

## Constraints that still apply

Nothing has been pushed anywhere other than these two `ndalyTT` repositories,
and nothing has been uploaded to Hugging Face. Any further publication needs
explicit permission from the owner.
