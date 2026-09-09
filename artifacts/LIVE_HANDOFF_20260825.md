# DeepSeek V4 Flash QuietBox2 live handoff

Updated: 2026-08-27 17:14 UTC during the required eight-point OSL-512
performance sweep.

## Latest continuation checkpoint (2026-08-27 15:55 UTC)

- The prior server session `91281` completed the Terminal-Bench diagnostics
  summarized below, then was reused to begin the performance sweep.
- A new resident-server benchmark client was added at
  `models/autoports/deepseek_ai_deepseek_v4_flash_0731/tools/run_vllm_server_benchmark.py`.
  It sends exact token-ID prompts, measures streamed TTFT/TPOT/E2EL, and
  atomically checkpoints every completed ISL.
- Its first OSL-2 smoke incorrectly set `min_tokens`. vllm-tt-plugin explicitly
  classifies that option as host-sampling-only, so the adapter's fail-closed
  device-sampling guard raised inside EngineCore. This was a benchmark-client
  contract defect, not a TT kernel or model-quality failure. Session `91281`
  exited; devices 0-3 were immediately reset and `tt-smi -ls --local` verified
  all four p300c devices.
- The benchmark no longer sends `min_tokens`; exact OSL is enforced with
  `max_tokens` plus `ignore_eos`. It uses deterministic `temperature=0,
  top_p=1, top_k=1, seed=0` on the qualified device-sampling path. The adapter
  remains fail-closed for structured output, `min_tokens`, and host-only logits
  processors. Focused adapter/benchmark tests are 18/18 passed and Ruff is
  clean.
- The same eight-layer qualified deployment is resident in exec session
  `10115`; load started at 2026-08-27 15:51:58 UTC and the API became ready at
  16:17:14 UTC. Log:
  `terminal_bench_2_1/logs/vllm_server_validtail_salience8_performance_sweep_20260827.log`.
  Do not reset cards or launch another TT workload while it is active.
- The corrected OSL-2 server benchmark smoke passed. The sequential required
  sweep is active in exec session `27217` with one excluded OSL-2 warmup per
  row. Artifact:
  `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/vllm/vllm_server_benchmark_selective_bfp4_salience8_validtail_required_sweep_osl512_20260827.json`.
  Log:
  `terminal_bench_2_1/logs/vllm_server_benchmark_selective_bfp4_salience8_validtail_required_sweep_osl512_20260827.log`.
  Completed rows are:
  - ISL 128: TTFT 2,590.36 ms, TPOT 150.384 ms, E2EL 79,436.60 ms,
    6.6496 t/s/u, TTFT/E2EL 3.2609%.
  - ISL 1,024: TTFT 22,301.18 ms, TPOT 150.363 ms, E2EL 99,136.88 ms,
    6.6506 t/s/u, TTFT/E2EL 22.4953%.
  - ISL 4,096: TTFT 90,193.70 ms, TPOT 150.314 ms, E2EL 167,004.04 ms,
    6.6528 t/s/u, TTFT/E2EL 54.0069%.
  - ISL 8,192: TTFT 180,921.14 ms, TPOT 150.322 ms, E2EL 257,735.78 ms,
    6.6524 t/s/u, TTFT/E2EL 70.1964%.
  - ISL 16,384: TTFT 364,159.40 ms, TPOT 150.360 ms, E2EL 440,993.59 ms,
    6.6507 t/s/u, TTFT/E2EL 82.5770%.
  - ISL 32,768: TTFT 727,058.97 ms, TPOT 150.324 ms, E2EL 803,874.47 ms,
    6.6523 t/s/u, TTFT/E2EL 90.4443%.
  Session `27217` is currently running ISL 65,536. Do not send another model
  request concurrently. If the client is interrupted while server `10115`
  remains healthy, restart the same command with `--resume` and the same JSON.
- Nothing has been pushed or uploaded to GitHub or Hugging Face.

## Machine state

- The qualified eight-layer vLLM server is loading in exec session `10115`.
  It started at 2026-08-27 15:51:58 UTC and normally takes 23-24 minutes.
  Log:
  `terminal_bench_2_1/logs/vllm_server_validtail_salience8_performance_sweep_20260827.log`.
- Do not reset cards or launch another TT process while session `10115` runs.
- No Harbor, Terminal-Bench, or CPU-reference process is running.
- TT devices 0-3 were reset cleanly immediately before this vLLM load and
  verified with `tt-smi -ls --local`.
- Nothing has been pushed or uploaded to GitHub or Hugging Face.
- Continue only in `/home/ttuser/deepseekv4flash/tt-metal`, branch
  `deepseek-v4-flash-0731-quietbox2`. This is the fresh-main checkout, not the
  Nemotron checkout.
- Keep all TT device work serialized. Reset cards 0-3 before a new TT process
  and immediately after a fatal TT failure.

## Quantized deployment that fits

The selected production policy remains `QUIETBOX2_SELECTIVE_BFP4_POLICY`:

- All 43 transformer layers and all 256 routed experts are resident.
- Routed gate/up uses BFP4 in layers `{2,27,29,32,34,36,41,42}` and BFP2 in
  the other 35 layers.
- Routed down and shared experts use BFP4.
- Maximum context is 131,072 tokens, batch size 1, vLLM block size 128.

Measured per-device residency after a full build:

- allocated: 33,389,479,936 bytes (31.096376 GiB)
- free: 520,815,616 bytes (0.485047 GiB)
- largest contiguous free block: 439,356,416 bytes

The unquantized model does not fit. The deployed mixed-BFP2/BFP4 policy does.

One additional gate/up layer fits in the measured headroom, but two additional
layers cannot fit at context 131,072: each upgrade costs 268,435,456 bytes per
device, while the selected policy has 520,815,616 bytes free.

The real nine-layer, all-43-layer context-131072 residency build passed in
1,464.512 seconds. Measured per-device residency is:

- allocated: 33,657,915,392 bytes (31.346376 GiB)
- free: 252,380,160 bytes (0.235047 GiB)
- largest contiguous free block: 170,920,960 bytes

Artifact:
`tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/full_model/selective_bfp4_salience9_layer38_all43_residency_ctx131072_20260827.json`.

That fit result does not qualify layer 38 for production. Matched 20-token AIME
teacher-forced top-1/top-5 results were:

- selected eight-layer policy: 85% / 100%
- add layer 38: 70% / 100%
- add layer 35: 70% / 100%
- add layer 37: 80% / 100%
- add layer 31: 75% / 100%

Every shortlisted whole-layer upgrade regressed, so all were rejected and the
source policy/tests remain on the eight-layer set; 46 focused host tests and
Ruff pass. Parallel layer-35/37/31 comparisons saturated host memory bandwidth,
so the final layer-37/31 comparisons were rerun serially.

## Cause of the old Terminal-Bench zero-score behavior

The old 415-token native prompt was padded to 512 tokens and executed as four
fixed 128-token prefill blocks. The five-page local KV ring incorrectly
persisted the 97 synthetic padding tokens in the final block. Those entries
evicted 96 real prompt-token rows, so decode attended to corrupted context and
fell into semantic/token loops.

The first attempted repair executed only the 31 valid tail tokens. That made
the KV contents exact but introduced a new 31-token collective shape and
exhausted the 2 KiB `L1_SMALL` allocation on decode. It was not retained.

The final repair preserves the fixed 128-token compute/collective shape and
passes `valid_seq_len` through streaming prefill. Only page-rounded prefixes
containing real tokens are persisted into the local cache, bounded raw
compressor state, and CSA boundary state. Padding still participates in fixed
shape compute but cannot overwrite live KV entries.

Primary implementation files:

- `models/autoports/deepseek_ai_deepseek_v4_flash_0731/tt/model.py`
- `models/autoports/deepseek_ai_deepseek_v4_flash_0731/tt/multichip_decoder.py`
- `models/autoports/deepseek_ai_deepseek_v4_flash_0731/tests/test_full_model.py`
- `models/autoports/deepseek_ai_deepseek_v4_flash_0731/tests/test_multichip_decoder.py`

## Validation completed after the repair

- Focused host suite: 62 passed, 2 warnings.
- Layer-0 post-prefill cache versus source cache: bit exact.
- Layer-0 local KV bank CPU versus TT PCC: 0.99972856.
- Layer-0 attention-head PCC improved from about 0.239996 to 0.99948394.
- Layer-0 attention output PCC: 0.9992879.
- Layer-0 final output PCC: 0.9982314.
- Full 43-layer eager discriminator passed:
  - prompt length: 415
  - prefill token: 43
  - teacher inputs: `[43,1309,304]`
  - decode outputs: `[1309,304,9487]`
- Full CPU-versus-TT layer-state comparison: minimum PCC 0.937118 and no
  layer below 0.90.

Key artifacts:

- `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/full_model/terminal_native_complete_hostpack_layer0_fixedshape_validtail_ctx131072_20260826.json`
- `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/full_model/terminal_native_complete_hostpack_fixedshape_validtail_eager_teacher_step3_layer_states_ctx131072_20260826.json`
- `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/datatype_sweep/terminal_native_complete_hostpack_fixedshape_validtail_eager_teacher_step3_cpu_vs_tt_20260826.json`
- `terminal_bench_2_1/logs/terminal_native_complete_hostpack_fixedshape_validtail_eager_teacher_step3_layer_states_ctx131072_20260826.log`

## Real vLLM qualification

The 32-token `vllm-tt-plugin` smoke passed through the actual `LLM(...)` path
with `trace_mode=all`, `sample_on_device_mode=all`, context 131,072, and block
size 128.

- output token prefix: `[43,1309,304,9487]`
- output text: `I need to solve the task. I have a decompressor in
  /app/decomp.c. It reads compressed data from stdin and writes the
  decompressed data to`
- TTFT: 12,842.96 ms
- TPOT: 201.10 ms
- throughput: 4.97275 tokens/s/user
- E2EL: 19,077.22 ms
- TTFT/E2EL: 67.3209%
- startup/build time: 1,413.24 seconds

Artifact and log:

- `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/vllm/terminal_native_write_compressor_fixedshape_validtail_vllm_32_20260826.json`
- `terminal_bench_2_1/logs/terminal_native_write_compressor_fixedshape_validtail_vllm_32_20260826.log`

The shutdown-only PyTorch `torch.accelerator.empty_cache()` exception printed
by the smoke child does not invalidate the request: the request artifact was
written with status `passed` and the wrapper exited zero.

## Latest Terminal-Bench diagnostics and current blocker

Harbor now has two opt-in DeepSeek-specific controls:

- `deepseek_v4_action_task` appends the official encoder's `task: "action"`
  marker to every final interaction. A local wrapper preserves the marker
  across the official `merge_tool_messages()` conversion, which otherwise
  dropped it on tool-result turns.
- `reject_repeated_commands` records every executed command signature, refuses
  any command already executed in the trial, and reports the forbidden set in
  subsequent observations.

The official action task immediately elicited valid DSML terminal calls in
direct probes. The focused Harbor suite is 68 passed and Ruff is clean.

Canary evidence:

- JSON/action-first no-repeat v10: the repeat guard worked, but the model kept
  requesting a forbidden file-read command; verifier reward 0, no
  infrastructure exception.
- Native-action write-compressor v13: valid actions read the source/data and
  inspected input size, but no compressor was produced before the 15-minute
  agent timeout; reward 0 with `AgentTimeoutError`.
- Native-action OpenSSL v15: the model created the directory and a valid
  RSA-2048 private key, then repeatedly failed to repair a shell-quoting and
  missing-`-x509` error after reading `openssl req -help`; reward 0 with
  `AgentTimeoutError`.

The terminal, API, DSML parser, Docker execution, and action dispatch are
therefore working. The remaining zero-score blocker is model
reasoning/instruction-following under the current compressed deployment,
amplified by slow long generations. The full 89 x 5 benchmark has not been
restarted because these gates do not justify its multi-day cost.

### Subsequent Terminal-Bench v18-v24 evidence

- v18, OpenSSL with vendor-recommended `temperature=1`, `top_p=.95`, and
  max output 1024: no agent timeout and 4/6 verifier checks passed (directory,
  key, certificate, PEM), but verification/script checks were missing; score 0.
- v19, the same canary capped at the required OSL 512: 2/6 checks passed
  (directory and key); score 0.
- v20, `temperature=.6`, `top_p=.95`, `top_k=20`, OSL 512: 2/6 checks passed;
  score 0.
- v21 used the official encoder's thinking mode with `reasoning_effort=max`.
  Its first 512-token turn exhausted the cap in reasoning before a tool call.
- v22 used the easier `fix-git` task in native chat mode. It issued valid
  status/list/branch/stash actions, then spent consecutive capped turns
  reasoning without inspecting reflog; the diagnostic was stopped.
- v23 used the JSON action prefix on `fix-git`. It ended normally after 15
  fast but wandering commands in 8m46s, with score 0 and no infrastructure
  exception. Job:
  `terminal_bench_2_1/jobs/tb21-dsv4-quietbox2-canary-fix-git-prefilled-chat-minimal-v23`.
- v24 used the official native DSML keystrokes prefix. Native action parsing
  was stable, but the model wandered through `ls-files` and never used reflog
  after 11 actions; the diagnostic was stopped at 12 minutes. Job:
  `terminal_bench_2_1/jobs/tb21-dsv4-quietbox2-canary-fix-git-native-dsml-prefill-v24`.
- Direct thinking-low and planning-only `fix-git` probes likewise failed to
  identify reflog and sometimes hallucinated tool results. A two-pass planner
  is therefore not trustworthy on this deployment.
- The local HF model card confirms DeepSeek's Code Agent harness uses thinking
  mode with max reasoning and `temperature=1`, `top_p=.95`, but recommends up
  to 384K output tokens for high/max reasoning. That policy cannot fit the
  required OSL 512 or a 900-second Terminal-Bench trial at this deployment's
  decode rate.

The current measured Terminal-Bench score remains **0.000**. The zero is no
longer attributable to API, DSML parsing, Docker, verifier, or command
dispatch; it is the honest canary result for the local compressed model under
the required output/time envelope. Do not start the full 89 x 5 evaluation
unless a task canary first earns nonzero reward.

## Exact continuation sequence

1. Poll vLLM server exec session `91281` until
   `http://127.0.0.1:8010/health` returns 200. Do not reset cards while it runs.

2. Run a direct native-action probe with the vendor-recommended agent sampling:
   `temperature=1.0`, `top_p=0.95`, with no `top_k=1`. Confirm a complete DSML
   tool call parses.

3. Run
   `terminal_bench_2_1/config_canary_openssl_native_action_recommended_sampling.yaml`.
   This also uses the generic one-shot/error-recovery prompt. Compare action
   latency and task progress against v15, whose six API calls took 38-205
   seconds and timed out after creating only the directory/private key.

4. Only if the OpenSSL/action gate shows materially improved repair behavior,
   run a five-task smoke under a new job name. Require useful task completion
   before starting the full 89 x 5 evaluation.

5. If recommended sampling does not improve the canary, document the valid
   one-task zero and timeout evidence. Do not silently reduce the required
   131,072-token context to gain more precision headroom.

## Documents and log artifacts still to finalize

- Quickstart:
  `artifacts/DeepSeek-V4-Flash-0731 QuietBox2 Quickstart.html`
- Autoport report:
  `artifacts/DeepSeek-V4-Flash-0731 QuietBox2 Autoport Report.html`
- This handoff: `artifacts/LIVE_HANDOFF_20260825.md`
- Existing full session archive through the prior run:
  `artifacts/session-logs-live-full-start-20260825T2319Z.tar.gz`
- Incremental archive containing the current Codex session, all current
  Terminal-Bench logs, the paused canary, and this handoff:
  `artifacts/session-logs-pause-20260826T2341Z-incremental.tar.gz`

Update the quickstart, report, and shareable log archive only after the final
agent configuration and benchmark outcome are known.

## Local worktree state

The tt-metal branch is `deepseek-v4-flash-0731-quietbox2`. It has 12 modified
tracked files and numerous untracked diagnostic artifacts. Preserve all of
them; do not reset or clean the worktree. Harbor also has local tracked changes
for DeepSeek parsing/tool support plus the untracked native prompt template.

## Constraints still in force

- No GitHub or Hugging Face push/upload without explicit user permission.
- Local commands are authorized without asking the user, subject to sandbox
  enforcement.
- Send a concise update every 15 minutes or when a meaningful event occurs.
- No full Terminal-Bench evaluation until direct and smoke tool-use gates pass.

## 2026-08-27 long-context qualification (authoritative latest state)

The resident OpenAI-compatible vLLM server benchmark completed the first six
required ISLs at OSL 512 under the selected eight-layer BFP4 policy:

| ISL | TTFT ms | TPOT ms | E2EL ms | t/s/u | TTFT % E2EL |
|---:|---:|---:|---:|---:|---:|
| 128 | 2,590.36 | 150.3839 | 79,436.60 | 6.64965 | 3.2609 |
| 1,024 | 22,301.18 | 150.3633 | 99,136.88 | 6.65056 | 22.4953 |
| 4,096 | 90,193.70 | 150.3137 | 167,004.04 | 6.65276 | 54.0069 |
| 8,192 | 180,921.14 | 150.3221 | 257,735.78 | 6.65238 | 70.1964 |
| 16,384 | 364,159.40 | 150.3603 | 440,993.59 | 6.65069 | 82.5770 |
| 32,768 | 727,058.97 | 150.3237 | 803,874.47 | 6.65231 | 90.4443 |

The excluded 65,536-token warmup then crossed the previously exercised 32K
shapes and failed around 36K with a 32 MiB DRAM allocation OOM. The selected
weights fit (31.096376 GiB allocated/device, 0.485047 GiB free), but that
weight-residency result alone was not sufficient to claim full required-context
runtime fit. The server and client exited, cards 0-3 were immediately reset,
and all four cards were verified present.

The failure pattern points to context-shape-specific TTNN program residency:
32K warmup and measurement both passed, while new shapes beyond 32K consumed
the remaining margin. `tt/model.py` now clears the program cache only after
each nonterminal 64-block epoch (8,192 prompt tokens), after explicitly
releasing the block's input/position tensors and synchronizing the mesh. It
logs entry counts and DRAM free bytes before and after each clear. This retains
all eight sensitivity-selected BFP4 gate/up layers unless hardware evidence
shows the bounded cache is insufficient.

The mechanism was confirmed in tt-metal source, not inferred only from timing:
`tt_metal/distributed/mesh_workload.cpp` allocates a replicated DRAM
`MeshBuffer` for every cached workload's kernel binaries, and
`ProgramCache::clear()` destroys those cached workloads. The bounded clear can
therefore reclaim the exact DRAM class exhausted by the fatal allocator error.

Host validation after this change: 39 focused full-model/vLLM adapter tests
passed in 9.86 seconds. Ruff is not installed in the current environment; the
two touched files still need a Ruff check when an executable is available.

Current hardware run:

- server exec session: `64331`
- server launch: 2026-08-27 17:36:10 UTC
- log: `terminal_bench_2_1/logs/vllm_server_selective_bfp4_salience8_bounded_program_cache_20260827.log`
- expected readiness: about 24-26 minutes after launch
- cards were reset and verified clean immediately before launch

Server became ready at 18:00:34 UTC (24m24s startup). The resumed client is
exec session `51042` and writes
`terminal_bench_2_1/logs/vllm_server_benchmark_selective_bfp4_salience8_validtail_bounded_cache_required_sweep_osl512_20260827.log` plus the matching
`...bounded_cache_required_sweep_osl512_20260827.json` artifact. Hardware
telemetry through 32,768 was stable: each 8,192-token epoch cleared roughly
2,395-2,462 entries, free DRAM rose from about 0.600-0.601 GiB to 0.645 GiB,
and execution continued beyond the old approximately 36K-token fatal point.
The complete 65,536-token excluded warmup returned HTTP 200 at 18:26:48 UTC;
the measured 65,536/512 request then started immediately and remained active
at the time of this checkpoint.

When ready, resume the checkpointed resident-server benchmark artifact with
the same ISL/OSL configuration. The client should skip the six completed rows
and execute 65,536 and 130,560. Preserve the failed six-row artifact as
historical evidence if the resume tool would overwrite its error context;
prefer copying it to a bounded-cache filename first. If this run still OOMs,
reset cards immediately and reduce the BFP4 upgrade count based on measured
runtime headroom rather than claiming the eight-layer policy fits.

## 2026-08-27 final qualification and Terminal-Bench checkpoint

This section supersedes the active-run wording above. The bounded-cache
resident-server sweep completed successfully with `status: passed` and all
eight required ISLs at OSL 512. Final artifact:

`tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/vllm/vllm_server_benchmark_selective_bfp4_salience8_validtail_bounded_cache_required_sweep_osl512_20260827.json`

SHA256:
`599915a3ef7cd9ee19b21e34c391455112470769a3b1af3f48d36163f958f249`

| ISL | TTFT ms | TPOT ms | E2EL ms | t/s/u | TTFT % E2EL |
|---:|---:|---:|---:|---:|---:|
| 128 | 2,590.36 | 150.3839 | 79,436.60 | 6.64965 | 3.2609 |
| 1,024 | 22,301.18 | 150.3633 | 99,136.88 | 6.65056 | 22.4953 |
| 4,096 | 90,193.70 | 150.3137 | 167,004.04 | 6.65276 | 54.0069 |
| 8,192 | 180,921.14 | 150.3221 | 257,735.78 | 6.65238 | 70.1964 |
| 16,384 | 364,159.40 | 150.3603 | 440,993.59 | 6.65069 | 82.5770 |
| 32,768 | 727,058.97 | 150.3237 | 803,874.47 | 6.65231 | 90.4443 |
| 65,536 | 1,543,989.33 | 150.6665 | 1,620,979.99 | 6.63717 | 95.2504 |
| 130,560 | 3,160,809.93 | 150.8978 | 3,237,918.75 | 6.62700 | 97.6186 |

Both excluded warmups and measured requests passed at 65,536 and 130,560.
At every 8,192-token boundary the cache clear returned DRAM to a stable
post-clear level (about 0.395 GiB in the final warmup and measured request),
so there was no progressive program-residency leak.

Terminal-Bench v25 then ran against the same healthy resident server using
`terminal_bench_2_1/config_canary_fix_git_native_dsml_bounded_cache_v25.yaml`.
The one-task `fix-git` canary found the lost `c499730` commit via reflog, but
checked out the already-current `d7d3e4b` commit, retried rejected commands,
and ended with `AgentTimeoutError` after 15 actions. Reward and mean were both
0.000. Result:

`terminal_bench_2_1/jobs/tb21-dsv4-quietbox2-canary-fix-git-native-dsml-bounded-cache-v25/result.json`

The server stayed healthy and no API/parser/Docker/verifier exception occurred.
The full 89 x 5 evaluation remains intentionally not restarted because the
required nonzero task-canary gate still fails.

The vLLM server and benchmark/canary clients are no longer active. The server
was stopped with Ctrl-C at 20:55:29 UTC, then TT devices 0-3 were reset and all
four p300c cards were verified present. No GitHub or Hugging Face write was
performed. Remaining work is host-only document/test validation and creation
of the final shareable session/log archive.
