# DeepSeek-V4-Flash-0731 quantization decision

Status: selected for full-model bring-up; final quality and serving validation are still pending.

## Capacity result

The official checkpoint cannot fit in QuietBox2 accelerator memory. Its 48 indexed
safetensors shards total **166,878,536,440 bytes (166.879 GB)**, while the four
Blackhole devices expose **128 GB aggregate DRAM**. The checkpoint exceeds device
capacity before KV cache, runtime buffers, traces, or allocator overhead are counted.

The selected backbone is the experimental REAP K160 checkpoint. Its indexed tensors
total **107,803,320,952 bytes (107.803 GB)**. The current TT storage estimate, using
BFP4_B for routed-expert matrices and the selected dense-weight policy, is
**106,754,287,766 bytes (106.754 GB)**. At 131,072 total tokens the compressed/local
KV estimate is 0.907 GB, leaving about 20.34 GB before runtime and scratch buffers.

See `models/autoports/deepseek_ai_deepseek_v4_flash_0731/tools/capacity_analysis.py`
in the local tt-metal checkout for the reproducible estimator.

## Candidates considered

| Candidate | Capacity | Quality/runtime evidence | Decision |
| --- | ---: | --- | --- |
| Official 256-expert checkpoint | 166.879 GB on disk | Source uses mixed FP8/MXFP4 packing | Reject: physically larger than aggregate device DRAM |
| MLX 2.44-bit mixed | 92.8 GB per model card | Card reports 0.573 MMLU-Pro on n=600, 7.3 points below its full-precision comparison; Apple MLX affine format has no TT kernel path | Reject for TT deployment |
| All 256 experts, BFP2_B | 95.969 GB estimated weights | Real expert samples show severe output error | Reject for quality |
| All 256, top-64 BFP4_B/rest BFP2_B | 113.283 GB estimated weights | Requires two expert storage/compute paths and retains BFP2_B error | Reject in favor of higher-fidelity K160 |
| REAP K160 + routed BFP4_B | 106.754 GB estimated TT weights | Preserves BFP4_B precision for every retained routed expert and has useful KV/runtime headroom | Selected for bring-up |

The REAP card says it physically retains 160 of 256 routed experts per MoE scope,
remaps router tensors, preserves top-6 routing, and removes 37.5% of routed experts.
It also says this is an experimental checkpoint whose structural/smoke validation
does not establish benchmark parity. Those are checkpoint-author claims, not results
of this QuietBox2 bring-up.

## Direct real-weight quantization evaluation

Nine routed-expert matrices were sampled across multiple layers, expert IDs, and
projection types from the downloaded K160 checkpoint. Each test compared a real
linear output against TT's emulated block-float packing:

| Format | Mean output PCC | Worst output PCC | Mean output NMSE |
| --- | ---: | ---: | ---: |
| BFP4_B | 0.9938075 | 0.9936320 | 0.0127637 |
| BFP2_B | 0.8451624 | 0.8426045 | 0.2874696 |

BFP2_B is therefore not acceptable for routed experts. BFP4_B is the lowest tested
TT-native format with tolerable per-matrix error and is used for every retained
routed expert.

For a real layer-0 dense `attn.wq_a` matrix:

| Format | Output PCC | Output NMSE |
| --- | ---: | ---: |
| BFP8_B | 0.9999939 | 0.00001218 |
| BFP4_B | 0.9926543 | 0.0146697 |

Dense projections therefore default to BFP8_B, with BF16/FP32 exceptions for
numerically sensitive routing and control tensors. Final exceptions must be justified
by end-to-end PCC/quality and capacity measurements.

The raw JSON records in this directory are the source of the table. Early evaluator
versions computed a few *weight* PCC values in insufficient precision, so weight-PCC
fields above 1.0 must not be used. The reported linear-output PCC and NMSE fields are
valid; the dense evaluator will be rerun with float64 metric accumulation before the
final report.

## Required final gates

- Load the complete 43-layer K160 backbone across the 2x2 QuietBox2 mesh without OOM.
- Measure actual device/runtime/cache allocation rather than relying only on estimates.
- Run representative full-model output and task-quality comparisons against a suitable
  reference, documenting the effect of expert pruning separately from TT quantization.
- Serve through the standalone `vllm-tt-plugin` and measure every requested ISL with
  OSL 512.
- Retain raw benchmark, profiler, environment, and clock-state logs.

No artifact in this directory has been uploaded or pushed to a remote.
