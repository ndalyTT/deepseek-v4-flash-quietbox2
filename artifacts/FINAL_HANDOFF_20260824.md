# DeepSeek-V4-Flash QuietBox2 final handoff

Finalized locally on **2026-08-24 UTC**. No GitHub fork, branch push, Hugging
Face upload, or other remote write was performed. Remote publication remains
permission-gated by the user's explicit instruction.

## Outcome

- The stock full model cannot fit: 57,998,069,952 required bytes/device versus
  33,910,295,552 usable, a 24,087,774,400-byte deficit/device.
- The selected exact-architecture policy retains all 43 layers and 256 routed
  experts. Routed gate/up weights use TT BFP2_B; routed down and shared experts
  use TT BFP4_B; dense/control paths keep their selected higher precision.
- The complete model is resident and runs through the Tenstorrent vLLM plugin
  at batch/concurrency one, TP4 on a `(4,1)` mesh, context 131,072, TT on-device
  sampling, prefix caching off, and chunked prefill off.
- Real allocation is 31,040,899,072 bytes/device with 2,869,396,480 bytes/device
  free.
- The selected policy also cannot retain the HF-advertised 1,048,576-token
  context: its lower bound is 35,449,405,632 bytes/device, 1,539,110,080 over
  usable DRAM. Its 710,784-token arithmetic boundary has only 196 KB before
  excluded runtime overhead; the largest end-to-end qualified context is
  131,072.

## Local source state

- tt-metal checkout: `/home/ttuser/deepseekv4flash/tt-metal`
- branch: `deepseek-v4-flash-0731-quietbox2`
- qualified local code commit: `5114991f9f`
- fresh-main ancestor: `faed88c379101717ce16b9f0ca3acbcf1597b285`
- standalone plugin checkout:
  `/home/ttuser/deepseekv4flash/vllm-tt-plugin`
- plugin commit: `e3fc84941bf7a1d0df32aae2c50d539259c925f0`
- plugin worktree: clean
- model revision: `7872f01b1d1fe23eabc4c98b48bffcef5a386062`

Only two untracked 14.3-GB Tracy capture directories remain in tt-metal. They
are retained locally and intentionally excluded from the reproducibility
commit because they are transient profiler scratch data, not required source
or compact qualification evidence.

## Final performance

Every row uses exact ISL, OSL 512, batch/concurrency one, one excluded
same-shape two-token warmup, and one measured request. Model construction
(1,421.65 seconds) is excluded.

| ISL | TTFT ms | TPOT ms | E2EL ms | tokens/s/user | TTFT % E2EL |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 128 | 2,627.74 | 140.449 | 74,397.09 | 7.1200 | 3.5321% |
| 1,024 | 22,869.62 | 140.342 | 94,584.28 | 7.1255 | 24.1791% |
| 4,096 | 91,112.85 | 140.341 | 162,827.50 | 7.1255 | 55.9567% |
| 8,192 | 182,894.94 | 140.334 | 254,606.02 | 7.1258 | 71.8345% |
| 16,384 | 367,505.20 | 140.450 | 439,275.21 | 7.1200 | 83.6617% |
| 32,768 | 739,387.37 | 140.423 | 811,143.60 | 7.1213 | 91.1537% |
| 65,536 | 1,499,561.52 | 140.613 | 1,571,400.60 | 7.1117 | 95.4283% |
| 130,560 | 3,016,893.27 | 140.551 | 3,088,715.46 | 7.1149 | 97.6747% |

Benchmark artifact:
`tt-metal/models/autoports/deepseek_ai_deepseek_v4_flash_0731/doc/vllm/vllm_benchmark_required_sweep_osl512_20260824.json`

SHA256:
`72d69145bf0b8d9b6c14720cdab4336df629c16d68d54bb07dd8d901189f6be7`

## Requested shareable artifacts

1. Quickstart:
   `artifacts/DeepSeek-V4-Flash-0731 QuietBox2 Quickstart.html`
   - SHA256:
     `84d6adde1c3d2567908d2770a23a01f080cc19f2a345ba50dbe59bd06b9e3cb4`
2. Autoport report:
   `artifacts/DeepSeek-V4-Flash-0731 QuietBox2 Autoport Report.html`
   - SHA256:
     `b15a9af1cb149a6e1de3ab29d4ad64eee9ea53ff551fa64e9403fc09f1e1a4f6`
3. Complete shareable session-log archive:
   `artifacts/session-logs-final-20260824T210545Z.tar.gz`
   - size: 182 MB
   - SHA256:
     `6ebfb93c618a7f7682de03938c9a44d66918bfba262d4e739ba7a019ba141f77`
   - `gzip -t`: passed

The refreshed root-thread manifest contains 12,521 primary-session items and
all three historical child review threads. Manifest SHA256:
`1485bfdd5550937535760be08362a289499c9a628a7d0fbb708c47a1f40bdc83`.

## Verification

- Exact vLLM sweep: status `passed`, 8/8 ISLs, wrapper exit code 0.
- Host regression: 59/59 passed.
- Repository pre-commit hooks: all passed.
- Context checker: target 1,048,576, supported 131,072, DRAM-limited; passed.
- Python compile checks, HTML parse checks, JSON assertions, artifact hashes,
  and `git diff --check`: passed.
- vLLM 0.25.1 prints a known non-CUDA
  `torch.accelerator.empty_cache()` traceback during successful teardown. The
  request and atomic artifact complete first and the wrapper exits zero.

## Permission-gated next action

Only after explicit user authorization: create or select the `ndalyTT/tt-metal`
GitHub fork and push local branch `deepseek-v4-flash-0731-quietbox2`. Do not
upload model weights or any artifact to Hugging Face without separate explicit
permission.
