# DeepSeek V4 Flash QuietBox2 pause handoff

Paused at: 2026-08-22 04:25 UTC

## User constraints that remain in force

- Work locally and run local commands without conversational confirmation.
- Do not push or upload anything to GitHub or Hugging Face without explicit permission.
- Use the fresh current-main checkout at `/home/ttuser/deepseekv4flash/tt-metal`; do not use the Nemotron checkout.
- The final deliverables remain the runnable vLLM deployment, requested ISL/OSL benchmarks, quickstart HTML, bring-up report HTML, and exported session logs.
- Final deployment/performance runs must use the QuietBox2 `p300_x2_mesh_graph_descriptor.textproto` descriptor. The single-chip decoder-stage evidence currently uses the repo workflow's `p150_x4` parent descriptor and a carved 1x1 device.

## Safe paused state

- The autonomous multigoal runner was interrupted with SIGINT while Stage 2 was reasoning; exit code was 130.
- No `multigoal`, Codex app-server, model gate, Tracy, vLLM, or EngineCore process remains active.
- `tt-smi -ls --local` enumerates all four Blackhole p300c chips.
- Nothing has been pushed or uploaded.
- Nothing from the in-progress Stage 2 is staged in Git.

## Repository state

- Checkout: `/home/ttuser/deepseekv4flash/tt-metal`
- Branch: `deepseek-v4-flash-0731-quietbox2`
- Base current-main commit: `faed88c379101717ce16b9f0ca3acbcf1597b285`
- Local functional-stage commits:
  - `91ff2840c7` — `Add DeepSeek V4 Flash functional decoder`
  - `7f01175b81` — `Record DeepSeek V4 Flash decoder evidence`
- HEAD: `7f01175b81`
- Stage 1 review: `clean-pass`
- Stage 2 files are intentionally untracked and uncommitted:
  - `models/autoports/deepseek_ai_deepseek_v4_flash_0731/tt/fused_decoder.py`
  - `models/autoports/deepseek_ai_deepseek_v4_flash_0731/tests/run_fused_decoder_gate.py`
  - `models/autoports/deepseek_ai_deepseek_v4_flash_0731/tests/test_fused_decoder.py`
  - `models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/fused_decoder/`
- Separate pre-existing quantization/capacity tools are also untracked and must be preserved:
  - `tools/capacity_analysis.py`
  - `tools/evaluate_dense_quantization.py`
  - `tools/evaluate_expert_quantization.py`
  - `tools/test_capacity_analysis.py`
- `.agents/` is the locally copied research workflow and remains untracked.

## Completed functional stage

- Representative real-weight layer kinds all passed PCC >= 0.995.
- Populated full-context cache/addressing oracles passed at position 1,048,575 for layers 0/2/3/4.
- Reverse page tables, advancing trace inputs/positions, exact 32/128 boundaries, and a nonzero non-divisible long-context oracle passed.
- Functional single-chip full-prefill limit is 6,592 tokens; 6,593 fails at the documented allocation boundary.
- Host tests: 24/24 passed. Device primitive tests: 3/3 passed.
- Watcher and no-fallback audits are clean.
- Per-kind Tracy/`tt-perf-report` evidence is committed.
- Important HCA fixes retained in Stage 1:
  - chunk wide row-major cache gathers at 1,024 rows;
  - use the explicit high-accuracy compute config for wide softmax.

## Quantization/capacity decision already made

- Official checkpoint size: 166,878,536,440 bytes, so it cannot fit in 128 GB aggregate device DRAM before KV cache/runtime allocations.
- Selected checkpoint backbone: local REAP K160 at `/home/ttuser/deepseekv4flash/model_assets/DeepSeek-V4-Flash-0731-REAP`.
- Selected policy: K160 REAP backbone, omit three MTP layers initially, TT BFP4_B routed experts, dense weights BFP8/BF16 with FP32 exceptions.
- Estimated selected TT weights: 106,754,287,766 bytes.
- Estimated KV at 131,072 tokens: 0.907 GB, leaving about 20.338 GB before runtime; at 1,048,576 tokens: 7.220 GB, leaving about 14.026 GB before runtime.
- Measured nine-expert BFP4 mean output PCC: 0.9938075; BFP2 mean output PCC: 0.8451624, so BFP2 was rejected.
- Dense `wq_a` BFP8 output PCC: 0.9999939; BFP4 output PCC: 0.992654.
- Quantization evidence: `/home/ttuser/deepseekv4flash/artifacts/quantization/README.md`.

## Exact paused multigoal state

- Log directory: `/home/ttuser/deepseekv4flash/artifacts/session_logs/multigoal-decoder`
- Manifest: `manifest.txt`
- Stage 1 thread: `01a02605-0a29-7d70-be8e-21cbdb1bf683` (complete)
- Stage 2 thread: `01a02791-92ba-7ed3-b40c-698af07044ca` (interrupted, not complete)
- Stage 2 log: `02-02-fused-decoder.jsonl`
- Stages configured in this run: functional, fused, optimized, multichip, optimized-multichip (1 through 5).
- On resume, the runner will create `02-02-fused-decoder.resume-1.jsonl`, resume the recorded Stage 2 thread, and then continue Stages 3 through 5 after Stage 2 passes.

Resume command (do not run until the user says to start again):

```bash
cd /home/ttuser/deepseekv4flash/tt-metal
python_env/bin/python .agents/scripts/multigoal \
  --repo /home/ttuser/deepseekv4flash/tt-metal \
  --log-dir /home/ttuser/deepseekv4flash/artifacts/session_logs/multigoal-decoder \
  --resume-stage 2 \
  --replace HF_MODEL=deepseek-ai/DeepSeek-V4-Flash-0731 \
  .agents/prompts/model_bringup_multigoal/01-functional-decoder.txt \
  .agents/prompts/model_bringup_multigoal/02-fused-decoder.txt \
  .agents/prompts/model_bringup_multigoal/03-optimized-decoder.txt \
  .agents/prompts/model_bringup_multigoal/04-multichip-decoder.txt \
  .agents/prompts/model_bringup_multigoal/05-optimized-multichip-decoder.txt
```

## Stage 2 state and measured candidates

Current fused source SHA-256:

`a0a0cfa05776e85c393ad977e5a777dc19089cd895c17d31d164825aaeeb7c93`

Current retained graph changes include:

- lossless int32 logical-row LUT gather replacing page division/remainder/multiply/add;
- sink-aware decode SDPA;
- dedicated fused RoPE;
- shared prefill compressor projection reuse;
- packed shared-input attention/compressor projections with unused individual weights deallocated;
- CSA-specific packed `q_b`/index-query and index-weight projections.

Most recent real-device candidate is `candidate_csa_packed_qr_layer2_seq33.json`:

- status: passed
- layer kind: CSA/hash
- prefill PCC: 0.9995370302
- decode PCC: 0.9999057985
- warmed prefill: 143.488 ms
- traced decode: 14.0096 ms over 100 replays
- deterministic: true
- allocated DRAM after build: 7,144,243,200 bytes

Candidate progression:

| Candidate | Layer | Warmed prefill | Traced decode | Decision/state |
|---|---:|---:|---:|---|
| row-LUT | 0 | 140.012 ms | 12.2605 ms | retained |
| decode SDPA | 0 | 140.026 ms | 12.2235 ms | retained |
| fused RoPE | 0 | 139.379 ms | 11.8587 ms | retained/current layer-0 best |
| dedicated concatenate-heads | 0 | 140.279 ms | 12.0083 ms | rejected/removed |
| rank-5 grouped permutation | 0 | 140.653 ms | 11.8644 ms | rejected/removed; fractionally slower |
| dedicated query-head op | 0 | 139.543 ms | 12.4423 ms | rejected/removed |
| compressor projection reuse | 2 | 145.554 ms | 14.4370 ms | retained |
| packed shared LHS, deallocated | 2 | 144.903 ms | 14.0522 ms | retained |
| CSA packed QR/index projections | 2 | 143.488 ms | 14.0096 ms | retained/current layer-2 best |

The earlier `candidate_shared_lhs_layer2_seq33.json` reports a 720 ms prefill because that command omitted `--prefill-warmup-replays 1`; the corrected deallocated run above is the comparable warmed result.

## Exact next action

At interruption, Stage 2 had just finished the passing CSA packed-QR candidate and was auditing remaining graph-fusion patterns. Its last source searches examined:

- fused activation opportunities in sparse MoE;
- `softplus`/`sqrt` router expressions;
- residual/hyperconnection add/multiply combinations;
- availability of `ttnn.addcmul`.

Resume the existing Stage 2 thread. Do not start a fresh fused stage and do not discard the untracked source/artifacts. The resumed agent should continue the MoE/router/hyperconnection fusion audit, validate every retained path across all four layer kinds, then produce watcher/stress/Tracy evidence, documentation, Stage Review, and local commits. After Stages 1–5 complete, launch Stages 6–10 for the selected REAP checkpoint, full model, datatype sweep, standalone vLLM plugin, and optimized vLLM. Never run the publishing stage and never push without explicit user permission.

## Remaining top-level work after decoder stages

1. Complete fused, optimized, multichip, and optimized-multichip decoder stages.
2. Bring up the selected REAP K160 full model with the chosen dtype policy and streaming weight conversion.
3. Integrate the standalone `/home/ttuser/deepseekv4flash/vllm-tt-plugin` checkout.
4. Benchmark OSL 512 at ISL 128, 1,024, 4,096, 8,192, 16,384, 32,768, 65,536, and 130,560, recording TTFT ms, TPOT ms, E2EL ms, t/s/u, and TTFT percent of E2EL.
5. Sample telemetry during final serving using the correct p300 x2 descriptor.
6. Create the Quickstart HTML and Autoport Report HTML from the Ornith reference documents.
7. Refresh/export all primary and autonomous session logs, create SHA-256 manifests, and package them locally.
8. Present local commits and results; ask explicit permission before any GitHub push. Never upload to HF.
