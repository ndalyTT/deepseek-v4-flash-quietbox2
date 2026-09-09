# DeepSeek-V4-Flash QuietBox2 pause/resume handoff

Paused at **2026-08-24T02:29:07Z** at the user's request. This handoff is
local-only. No Hugging Face or GitHub push/upload has been performed or
authorized.

## Exact pause boundary

- No model, vLLM, EngineCore, nested agent, or benchmark process is running.
- All four Blackhole p300c boards are visible to `tt-smi -ls`.
- The last hardware job completed successfully before the pause.
- An `apply_patch` session opened for the next optimization was closed before
  receiving any patch. There is no partial batched-attention edit to recover.
- `git diff --check` passes.
- The current changes are intentionally uncommitted and remain in the local
  `tt-metal` checkout.

## User constraints that remain binding

1. Run local commands without asking where the execution environment permits.
2. Do not push or upload anything to Hugging Face or GitHub without explicit
   user permission. Local copies, edits, tests, commits, and artifacts only.
3. Use this fresh checkout based on current `tt-metal` main, never the old
   Nemotron fork.
4. Use the standalone `tenstorrent/vllm-tt-plugin` checkout.
5. While work is active, report status in the terminal every 15 minutes,
   including current work and changes since the previous check-in.

## Repositories

- Workspace: `/home/ttuser/deepseekv4flash`
- tt-metal: `/home/ttuser/deepseekv4flash/tt-metal`
- Branch: `deepseek-v4-flash-0731-quietbox2`
- Current HEAD: `2b1c7715301c57a555bf6ec5d080a515dae18b9c`
- Fresh-main base: `faed88c379101717ce16b9f0ca3acbcf1597b285`
- Standalone plugin: `/home/ttuser/deepseekv4flash/vllm-tt-plugin`
- Plugin HEAD: `e3fc84941bf7a1d0df32aae2c50d539259c925f0`
- The plugin checkout is unchanged; all bridge work is in tt-metal's dynamic
  `EXTRA_MODELS_DIR` bundle.
- Nothing has been pushed and no remote fork has been created.

Local tt-metal history already contains the reviewed stages through:

- `9550d0cdd5` — optimized multichip decoder
- `2b1c771530` — optimized multichip review provenance

The complete full-model/datatype/core/vLLM work after that point is still
uncommitted. Preserve every tracked and untracked file reported by
`git status --short`.

## Capacity and selected deployment

The stock checkpoint cannot fit this QuietBox2:

- usable DRAM/device: **33,910,295,552 bytes**
- stock 1M lower bound/device: **57,998,069,952 bytes**
- stock deficit/device: **24,087,774,400 bytes**
- minimum-cache stock lower bound/device: **53,749,321,312 bytes**
- minimum-cache stock deficit/device: **19,839,025,760 bytes**
- routed experts alone in BFP4: **38,956,695,552 bytes/device**

The selected exact-architecture policy keeps all 43 layers and all 256 experts:

- routed expert gate/up: TT `BFP2_B`
- routed expert down and shared experts: TT `BFP4_B`
- dense/control tensors unchanged
- paged caches: BFP8
- batch one, 4x1 TP, exact context 131,072
- two shared RoPE variants

Selected lower bound/device:

| Component | Bytes/device |
|---|---:|
| decoder weights excluding RoPE | 30,082,144,768 |
| shared RoPE | 67,110,912 |
| cache | 541,220,896 |
| constants | 45,545,632 |
| terminal | 531,898,368 |
| **required** | **31,267,920,576** |
| **headroom** | **2,642,374,976** |

The official local checkpoint revision is
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`; checkpoint size is
166,878,536,440 bytes.

Quality evidence for the selected routed gate/up BFP2 policy is the exact
43-layer, 100-token teacher-forced CPU run:

- top-1 agreement: 0.91
- top-5 agreement: 1.0
- top-100 agreement: 1.0
- artifact:
  `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/datatype_sweep/aime24_gate_up_bfp2_teacher_forced_cpu.json`

## Core and full-model evidence already passed

- Public `DataType::BFLOAT2_B=10` / `ttnn.bfloat2_b` support is implemented.
- Full `ttnn` built successfully; the local `_ttnn.so` was copied into the
  Python package.
- Host BFP2 32x32 roundtrip is exact at 320 bytes.
- Hardware sparse indexed matmul passed at 16 experts, 256 experts, and the
  production TP4 4x1 layout.
- Full 43-layer residency passed:
  `doc/full_model/quantized_full_residency_20260823.json`
  - SHA-256:
    `357339fe8041e9098e73f1448c4c0ac8bdf7b796f0752d95adc3f79f87389c20`
  - actual allocated/device: 31,040,899,072 bytes
  - free/device: 2,869,396,480 bytes
- Native full-model generation passed:
  `doc/full_model/quantized_full_generation_5p2d_20260823.json`
  - SHA-256:
    `e3f58d4c355b72a7534ed87f35c857af7b6dfb2d6f4bfac1329240c841269c6d`
  - 5-token prefill, split sampling, traced decode tokens
    `[67, 20366, 260]`
  - zero host logit reads and zero host token-feedback writes

## vLLM status

The local environment contains:

- `vllm 0.25.1+empty`
- editable `vllm-tt-plugin 0.1.0`
- dynamic bundle:
  `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/vllm_models/deepseek_v4_flash_0731/`

Qualified adapter constraints are exact 4x1, context 131,072, batch one, DP one,
device sampling, no prefix caching, and no async scheduling.

The first passing vLLM request is:

- artifact: `doc/vllm/vllm_smoke_hello_2_retry3_20260824.json`
- artifact SHA-256:
  `b87029001d727b1dada1d95c5b1884f2cb4df089ffe93745e9bb6e6d750d313d`
- prompt token `[19923]`
- output tokens `[21133, 438]`, text `World =`

The exact OSL-512 sweep first produced a valid ISL-128 row:

- TTFT: 2,629.4877529144287 ms
- TPOT: 140.4353142112271 ms
- E2EL: 74,392.13649905287 ms
- tokens/s/user: 7.120716079261316
- TTFT/E2EL: 3.534631315431983%
- output-token SHA-256:
  `155741293a9799088806d529c1b0d1e30001e97cf72d706dc1cb2ae80e4d3882`
- preserved in
  `doc/vllm/vllm_benchmark_isl_sweep_osl512_20260824.json`

That first sweep then failed at ISL 1,024 because the original prefill retained
sequence-wide mHC/attention activations and because trace endpoints were not
explicitly reclaimed.

## New bounded-prefill and cleanup work

The following local changes are complete and saved:

- `tt/model.py`
  - adds `STREAMING_PREFILL_BLOCK_SIZE = 128`
  - prompts longer than 128 tokens do not create full per-layer
    `PrefillPlan` device tensors
  - streams one 128-token block through all 43 layers
  - keeps only the last block for terminal logits
  - explicitly deallocates prior layer/block activation endpoints
- `tt/optimized_decoder.py`
  - adds `prefill_forward_block`
  - batches mHC and MoE over 128 tokens
  - currently advances attention positions through the already-qualified
    exact decode cache/compressor path one position at a time
- `tt/generator.py`
  - `release_decode_trace` now drops public state, releases model and sampler
    traces, synchronizes, and force-deallocates trace logits, current position,
    and token buffer exactly once
- `tests/test_full_model.py`
  - covers the 128-token streaming boundary and explicit trace endpoint
    reclamation

Focused validation after these edits:

- Python compile checks passed
- full-model plus vLLM adapter suite: **32/32 passed**
- `git diff --check`: passed

The two-request vLLM ISL-1,024/OSL-2 probe passed:

- artifact:
  `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/vllm/vllm_benchmark_isl1024_osl2_streaming_probe_20260824.json`
- artifact SHA-256:
  `d6e6e2e1f1f0d60dd09b4ddc45dc0e9c3d44e3eae489b1dfc10f8c2eae6dd7d4`
- log SHA-256:
  `02096c57266c6726a3bd9cb996b8001617e6b90c763042e6d7ff358e52d3b41a`
- startup: 1,452.7083398090908 s
- excluded warmup wall: 193.68332632200327 s
- measured TTFT: 189,002.55227088928 ms
- measured TPOT: 1,561.1526099964976 ms (OSL 2 probe only)
- measured E2EL: 190,563.92724101897 ms
- status: `passed`

Most importantly, request one released its traces and request two completed all
eight blocks. The former cross-request OOM is resolved. The known shutdown-only
`torch.accelerator.empty_cache()` traceback occurred after success and the
wrapper process exited zero.

## Exact next implementation step

The sequential attention fallback proves correctness and bounded residency but
runs prompt prefill at only about 5.4 tokens/s. Do not start the full benchmark
with this version: the exact matrix would take roughly 13 hours for one request
per ISL, or about 26 hours with the current per-ISL warmups.

Resume by replacing only the per-token attention loop with a production
`MultichipDecoder.prefill_forward_block` override:

1. Keep the outer 128-token model streaming and explicit deallocation unchanged.
2. Project Q/KV and packed compressor inputs once for the full block.
3. Fill the 128 page-aligned local KV and packed raw-history cache rows with the
   block's page-table slice.
4. HCA blocks align exactly to the ratio-128 compressor boundary; pool one
   compressed entry per block.
5. CSA produces 32 ratio-4 entries per block. For blocks after zero, repair the
   first entry using the previous four packed raw-history rows plus the current
   four rows, matching `FusedDecoder._update_compressor_decode` exactly.
6. Run attention in four 32-query groups:
   - gather absolute 128-row local windows from the paged cache;
   - HCA: append valid compressed rows with per-query count masks;
   - CSA: score the logical index bank, select top 512, gather only selected
     compressed KV rows, and concatenate them with local gathered values.
7. Add an attention helper that accepts already-gathered
   `[query, 1, key, head_dim]` values, avoiding a second embedding lookup.
8. Preserve the existing rank-local 16-head multichip attention and the
   row-parallel output reduction.
9. Keep the current sequential method as a fail-closed fallback for non-128 or
   non-aligned blocks until separately qualified.

No code for this optimization was applied before the pause.

After host checks, reset all four boards and run another two-request
ISL-1,024/OSL-2 probe. Require:

- both requests pass;
- output tokens match the current bounded probe
  `[305, 103764]`;
- TTFT improves materially from 189 seconds;
- no allocator growth on the second request.

Only then rerun the exact OSL-512 sweep for ISLs:
`128, 1024, 4096, 8192, 16384, 32768, 65536, 130560`.

## Hardware launch contract

Before a new MeshDevice lifecycle:

```text
tt-smi -ls
tt-smi -r 0 1 2 3
tt-smi -ls
```

Use:

- `MESH_DEVICE='(4,1)'`
- `TT_METAL_DISABLE_FABRIC_TWO_ERISC=1`
- `PYTHONPATH=build_Release`
- `EXTRA_MODELS_DIR=.../vllm_models`
- `VLLM_PLUGINS=tt,tt_model_registry`
- `DEEPSEEK_V4_FLASH_HF_MODEL=/home/ttuser/deepseekv4flash/model_assets/DeepSeek-V4-Flash-0731`
- `TT_MESH_GRAPH_DESC_PATH` unset

Do not run concurrent hardware lifecycle commands.

## Required final artifacts

These exist but remain pending final benchmark values and final local commit
identity:

1. `artifacts/DeepSeek-V4-Flash-0731 QuietBox2 Quickstart.html`
2. `artifacts/DeepSeek-V4-Flash-0731 QuietBox2 Autoport Report.html`
3. `artifacts/session_logs/` plus the final shareable archive

Before final handoff:

- update the README/work logs with the bounded-prefill probe and final sweep;
- update `doc/context_contract.json` only after full benchmark qualification;
- rerun the complete relevant test suites and `git diff --check`;
- make local reproducibility commits if appropriate;
- refresh the Codex thread-tree export;
- package and hash all session logs;
- do not push or create a GitHub fork until the user explicitly grants
  permission.

