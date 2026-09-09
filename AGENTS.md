# Instructions for agents working on this project

You are picking up a DeepSeek-V4-Flash-0731 bring-up on a Tenstorrent
QuietBox2 (4x Blackhole P300C). The model implementation lives in the
`ndalyTT/tt-metal` fork, branch `deepseek-v4-flash-0731-quietbox2`. This
repository holds everything else: the handoff history, evidence, benchmark
harness, support escalations, and the pins needed to rebuild the environment.

## Read in this order

1. `README.md` for the summary of what was done and the current blocker.
2. `PINS.md` for every repository revision, model revision, and firmware version.
3. `artifacts/RESUME_AFTER_HOST_REBOOT_20260827.md`. This is the self-declared
   authoritative anchor written by the previous agent. Its "Post-reboot
   execution checklist" is the exact procedure for serving the model and
   running the official-Harness canary.
4. `BOARD_RECOVERY_HANDOFF.md` and `artifacts/board_recovery_20260828/README.md`
   for the hardware recovery contract and what happened when it was followed.
5. `artifacts/tenstorrent_support_20260828/TENSTORRENT_SUPPORT.md` and
   `artifacts/tenstorrent_support_fabric_test_20260831/README.md` for the open
   Tenstorrent support case.
6. `REPRODUCE.md` for environment setup and commands.
7. Only if you need history: `PAUSE_HANDOFF.md` (Aug 22), then
   `artifacts/PAUSED_RESUME_20260823.md`, `artifacts/PAUSED_RESUME_20260824.md`,
   `artifacts/FINAL_HANDOFF_20260824.md`, `artifacts/LIVE_HANDOFF_20260825.md`.
   Later documents supersede earlier ones where they disagree.

In the tt-metal branch, start at
`models/autoports/deepseek_ai_deepseek_v4_flash_0731/README.md`, then `tt/`,
`vllm_models/`, `tools/`, and the evidence under `doc/`.

## Hard rules inherited from the owner

- **Serialize all Tenstorrent hardware commands.** Never run two of
  `tt-smi`, a mesh open, a vLLM launch, a pytest that touches devices, or a
  Tracy capture at the same time. Never reset cards while a server owns them.
- **Bounded recovery only.** The recovery contract is list, reset, list, then a
  4x1 mesh smoke. Run it once, at most twice. If the same device-0 ERISC cores
  (`29-25`, `28-25`, `24-25`, `22-25`) freeze again, preserve the log and stop.
  Do not loop resets or relaunches.
- **No firmware flash** without separate explicit owner confirmation after
  Tenstorrent has reviewed the evidence. `tt-flash verify` 3.10.0 crashes on
  argument parsing on this host; that is not a verdict on the firmware image.
- **Do not redo completed work.** Decoder bring-up, quantization policy
  selection, the eight-row OSL-512 performance sweep, and the official-Harness
  protocol path are finished and evidenced. Do not re-derive them.
- **Do not clean, reset, stash, rebase, or check out over the tt-metal
  worktree on the QuietBox2 host.** It holds two 7 GB Tracy capture
  directories that are not in git.
- **Publishing is permission-gated.** Pushing to these two `ndalyTT` repos was
  explicitly authorized on 2026-09-09. Nothing else may be pushed, and nothing
  may be uploaded to Hugging Face, without new explicit permission.
- **Report status every 15 minutes** while long jobs run, and immediately on
  any meaningful event.
- The 512-token output length applies **only** to the deployment performance
  sweep. It must not cap Terminal-Bench agent reasoning.

## Current state and next action

- The model serves and is benchmarked. The quantized policy fits with about
  0.5 GB per device to spare.
- The official DeepSeek Harness Terminal-Bench 2.1 score is **not measured**.
  The prepared v27 `fix-git` canary has never started because, since
  2026-08-27 22:44 UTC, every fabric-enabled vLLM launch freezes four device-0
  ERISC cores before weights load. A host reboot, a logical reset, and a true
  AC power cycle did not change that. A fabric-only standalone smoke passed on
  2026-08-31, so raw fabric bring-up works; the fault is state or workload
  dependent.
- The 0.000 Terminal-Bench score in older documents belongs to the superseded
  Terminus/native-DSML path. Do not report it as the capability of the new path.
- **Next action:** obtain a Tenstorrent support answer or an operator-level
  recovery, re-run the bounded recovery contract, launch the server once, and
  if it initializes, run only the v27 canary. Score and inspect it before any
  broad evaluation. The exact steps are in
  `artifacts/RESUME_AFTER_HOST_REBOOT_20260827.md`.

## Where things are on the QuietBox2 host

Scripts in this repository hardcode `/home/ttuser/deepseekv4flash` as the
workspace root. On that host the layout is:

| Path | Contents |
|---|---|
| `tt-metal/` | the fork branch checkout, built as `build_Release`, with `python_env/` |
| `vllm-tt-plugin/` | editable-installed plugin checkout |
| `model_assets/DeepSeek-V4-Flash-0731/` | stock HF checkpoint at the pinned revision |
| `terminal_bench_2_1/harbor/` | Harbor checkout with the local patch applied and a `uv` venv |
| `terminal_bench_2_1/dataset/` | Terminal-Bench 2.1 tasks |
| `terminal_bench_2_1/deepseek_harness_toolchain/` | Node 22 plus `dsh` rc.6 |
| `local_tools/node22/node` | standalone Node 22.23.2 binary |
| `artifacts/session_logs/` | 1.1 GB of Codex thread exports; packaged in the release asset |
| `publish/deepseek-v4-flash-quietbox2/` | this repository's working copy |

If you are on a different host, edit the three `TT_METAL_ROOT`, `DEEPSEEK_MODEL`,
and `TB_ROOT` assignments in `terminal_bench_2_1/run_*.sh` rather than
rewriting the scripts, and say so in your handoff.

## When you finish a session

Write a dated handoff markdown next to the existing ones, refresh the
checksum manifest for anything you changed, and state explicitly whether
anything was pushed or uploaded.
