# DeepSeek-V4-Flash QuietBox2 pause/resume handoff

Paused at **2026-08-23T11:47:02Z** at the user's request. This is a local-only
handoff. No Hugging Face or GitHub upload/push has been performed or authorized.

## Pause state

- The Stage 6 `multigoal`, app server, and nested rereview processes were stopped.
  A process-table check after interruption found none of the task PIDs or commands
  still running. Only the parent terminal Codex process and its code-mode host remain.
- No model/device work, download, test, commit, or remote operation was started after
  the pause request.
- The fourth Stage Review rereview was interrupted before it wrote
  `STAGE_REVIEW_REREVIEW4.md`. Its last durable output is in
  `artifacts/session_logs/full-model-to-release/06-06-full-model.jsonl`.
- The existing session-log tree was 958 MiB at pause time. A shareable archive is
  created beside this handoff; its exact filename and checksum are appended below
  after packaging.

## User constraints to preserve

1. Run local commands without asking for interactive confirmation where the runtime
   permits it.
2. Do not push or upload anything to Hugging Face or GitHub without explicit user
   permission. Local copies and local edits only.
3. Use a fresh checkout based on current `tt-metal` main, not the Nemotron fork.
4. Use the standalone `tenstorrent/vllm-tt-plugin` for eventual vLLM serving.
5. When active, report terminal status every 15 minutes: current work and changes
   since the previous check-in.

## Checkout and repository state

- Workspace: `/home/ttuser/deepseekv4flash`
- Fresh tt-metal checkout: `/home/ttuser/deepseekv4flash/tt-metal`
- Branch: `deepseek-v4-flash-0731-quietbox2`
- Main base recorded at checkout: `faed88...`
- Current HEAD: `2b1c7715301c57a555bf6ec5d080a515dae18b9c`
- Completed Stage 5 commits:
  - `9550d0cdd56fc432f8d3b2a3fae9f86ca746ef70` — Optimize DeepSeek V4 multichip decoder
  - `2b1c7715301c57a555bf6ec5d080a515dae18b9c` — Record optimized multichip review provenance
- Stage 6 is intentionally uncommitted because its review has not produced a clean
  pass. Tracked changes are in `doc/context_contract.json` and `tt/__init__.py`; the
  new full-model wrapper, generator, tests, reports, and quantization tools are
  untracked. Preserve all of them.
- Standalone plugin: `/home/ttuser/deepseekv4flash/vllm-tt-plugin`, clean on
  `main...origin/main`, recorded commit `e3fc849...`.
- No upstream was added for the tt-metal working branch and nothing was pushed.

## Decisions already made

1. Treat the official checkpoint and architecture as the source of truth; do not
   substitute Nemotron or silently change model semantics.
2. Keep production full-model eligibility separate from reduced-layer probes. Reduced
   probes require explicit opt-in and must never be described as a deployable model.
3. Use BFP4/LoFi for routed weights, BFP8 for KV cache, BF16 for activations/router/CCL,
   and FP32 for mHC in the currently selected decoder policy. This policy is functional
   through the optimized multichip decoder stages, but is not resident for the complete
   43-layer model.
4. Record the stock-policy Stage 6 outcome as a hard physical capacity block, then use
   the user's explicit quantization authorization to investigate a separately qualified
   lower-bit deployment path. Do not mislabel an expert-pruned derivative as the exact
   official model.
5. Prefer the quantization that fits all four QuietBox2 devices with the smallest
   measured quality loss; compare existing HF variants with a direct local
   quantization. Do not upload any derived weights.
6. Do not advance the standard release stages as though the full stock-policy model
   passed. Resume with a custom quantized-residency stage after closing or explicitly
   recording the remaining Stage 6 wrapper/review items.

## Capacity result: official model does not fit

QuietBox2 has four Blackhole ASICs, 32 GiB per chip (128 GiB aggregate). The measured
usable device DRAM budget is **33,910,295,552 bytes per device**.

At the selected policy and 1M-token context, the per-device lower bound is:

| Component | Bytes/device |
|---|---:|
| Decoder weights | 53,167,682,048 |
| KV cache | 4,252,943,904 |
| Decode constants | 45,545,632 |
| Terminal layers | 531,898,368 |
| **Total** | **57,998,069,952** |

The deficit is **24,087,774,400 bytes/device**. Even at minimum cache the lower
bound is 53,749,321,312 bytes/device, a 19,839,025,760-byte deficit. Routed-expert
BFP4 weights alone require 38,956,695,552 bytes/device and exceed usable DRAM.
The largest arithmetic-only prefix with all 43 caches is 23 layers; layer 24 exceeds
the budget. That prefix is evidence only and is not a supported model.

The complete official checkpoint is approximately 166.879 GB (about 156 GiB) on
disk. `doc/context_contract.json` schema v3 records:

- `full_model_status: "blocked-hard-physical-limit"`
- `full_model_runnable: false`
- no claimed full-model supported or largest-tested context

The inherited 8K-prefill/1M-decode result is decoder-only evidence.

## Stage 6 implementation and evidence

The local wrapper contains the official embedding-to-logits flow, representative
decoder, hyper-head, final norm, vocab-sharded LM head, common on-device sampler,
model/sampler traces, and persistent token/position/page-table state. It includes a
production capacity preflight that rejects an impossible configuration before
checkpoint or device initialization.

Static state at pause:

- 32 combined host contracts passed.
- Expanded CPU kernel self-test passed.
- Formatting, JSON validation, compilation, and diff hygiene passed.
- The CPU reference runner and artifact are recurrence-aware and current.

Reduced TT device evidence:

- Layer 0, prompt/position 5: prefill plus two decode/model-sampler trace replays;
  TT greedy token 126264; positions `[5, 6, 7]`; stable addresses; no host logits or
  host token feedback.
- Layer 0, prompt/position 31: crossed the semantic page boundary; logical page 1 was
  remapped from physical row 32 to 128; the old row stayed unchanged and the new row
  changed; TT greedy token 13736; positions `[31, 32, 33]`; stable trace addresses.
- Primary boundary artifact:
  `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/full_model/probe_layer0_seq31_semantic_page_retry_20260823.json`

Fresh official HF CPU reference:

- Checkpoint revision: `7872f01b1d1fe23eabc4c98b48bffcef5a386062`
- Runner SHA-256: `c5de87023f0368907d1b12bf5d39d058b755e971be3813279c3db35b7bb35b29`
- Artifact SHA-256: `259757fa8eb3f7409b7653609ac2847a36c5b08252fb7c497f805fc65dd7e5b8`
- Status SHA-256: `50aac58c843d5d8f52fb692a2eb391bfac058c1727735252be1070039bbb06e8`
- Loaded all 43 layers and all 67,569 expected parameters
  (159,117,270,492 loaded bytes).
- Official AIME prompt: 569 characters / 135 tokens; 100 greedy completion tokens;
  each step stores 100 distinct top logits and the greedy token is top-1.
- Prefill 56.4274810369825 s; decode-99 558.0765505756717 s;
  0.17739501847529465 token/s on CPU.
- Linkage evidence ranks TT token 126264 at HF rank 5 for seq5 and TT token 13736 at
  HF rank 1 for seq31.

The CPU kernel oracle fixes now cover FP4 round-to-nearest-even and signed zero,
sparse BF16 probability boundaries, and the official 64-entry online sparse recurrence
including padding and `-1` KV entries. A source-level audit refuted suspected GEMM and
Sinkhorn semantic bugs. A true official CUDA-kernel differential is not possible on
this CPU-only, non-NVIDIA host and remains an explicitly external validation gap.

## Exact open boundary when paused

The fourth rereviewer found two new code-level gaps before interruption:

1. Stochastic serving never initializes or advances the common sampler RNG state and
   does not initialize prompt/output penalty state.
2. The full-model boundary does not lock the selected decoder policy against
   experimental `DSV4_*` environment overrides.

Greedy reduced-probe evidence is unaffected, but these gaps prevent acceptance of the
advertised serving and exact-policy contracts. There is no durable
`STAGE_REVIEW_REREVIEW4.md`; use the Stage 6 JSONL as the source for this finding.
Earlier `STAGE_REVIEW*.md` documents still have a `more-work-needed` outcome due to
the capacity block, missing full-TT execution, and unavailable official CUDA
differential.

## Resume sequence

When the user says **start again**:

1. Reconfirm no stale `multigoal`/nested Codex process and inspect the last Stage 6
   JSONL boundary. Do not expect `STAGE_REVIEW_REREVIEW4.md` unless a later user edit
   created it.
2. Use the repository's AutoDebug/AutoFix prompts for only the two focused wrapper
   gaps: sampler RNG/penalty lifecycle and deployment-policy locking. Add direct host
   contracts and rerun the static Stage 6 suite. The HF CPU reference need not be
   regenerated for wrapper-only changes.
3. Rerun the bounded Stage 6 review. Preserve an honest blocked/nonresident verdict;
   do not commit Stage 6 unless the repository clean-pass rule actually permits it.
4. Close the stock-policy Stage 6 attempt as `blocked-hard-physical-limit`, then begin
   a custom, user-authorized quantized residency workstream using the local capacity
   and quantization tools. Do not blindly enter a stock stage that assumes a resident
   full model.
5. Revalidate current HF candidate revisions and license/architecture compatibility,
   then evaluate local candidates such as the 2.4-bit mixed checkpoint and direct
   low-bit expert quantization. Treat REAP/K160 as an expert-pruned derivative rather
   than the exact model. Require all 43 layers plus terminal weights and the requested
   KV-cache contexts to fit.
6. Once a quality-qualified resident model runs, integrate the standalone vLLM TT
   plugin and benchmark OSL 512 for ISLs 128, 1,024, 4,096, 8,192, 16,384, 32,768,
   65,536, and 130,560. Report TTFT, TPOT, E2EL, tokens/s/user, and TTFT as a percent
   of E2EL. Never invent results for contexts that fail or cannot allocate.
7. Finish the Ornith-modeled quickstart HTML, bring-up report HTML, and refreshed
   shareable session-log archive. Ask permission before any GitHub fork creation or
   push; no HF upload is needed.

## Device lifecycle on resume

Before every new MeshDevice lifecycle, use a fresh reset and do not insert a mesh
smoke test between the reset and the target job:

```text
tt-smi -ls
tt-smi -r 0 1 2 3
tt-smi -ls
```

Use production auto-discovery with `TT_MESH_GRAPH_DESC_PATH` unset and
`TT_METAL_DISABLE_FABRIC_TWO_ERISC=1` for the 4x1 ring. No-reset retries previously
hit the known active-Ethernet firmware startup failure; reset-backed probes established
that the mesh itself is healthy.

## Important local paths

- Stage 6 log: `artifacts/session_logs/full-model-to-release/06-06-full-model.jsonl`
- Stage 6 docs: `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/full_model/`
- Context contract: `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/context_contract.json`
- Full-model wrapper: `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/tt/model.py`
- Generator: `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/tt/generator.py`
- Host contracts: `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/tests/test_full_model.py`
- Capacity and quantization tools: `tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/tools/`

## Pause log archive

- File: `/home/ttuser/deepseekv4flash/artifacts/session-logs-pause-20260823T114702Z.tar.gz`
- Size: 241,838,056 bytes
- SHA-256: `3c6ba83d96a38ed4db7825a174a4306ca7e85c135930207d96394fe4a674b7b3`
- Integrity: `gzip -t` passed
- Contents: the workspace `artifacts/session_logs` tree, a copy of this handoff at
  packaging time, and raw local Codex rollout logs dated 2026-08-21 through
  2026-08-23. The archive is local only and has not been uploaded.
