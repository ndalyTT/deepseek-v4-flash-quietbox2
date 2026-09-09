# Pinned revisions and versions

Everything below was measured on the QuietBox2 host `tt-quietbox` between
2026-08-21 and 2026-08-31. Reproduce against these exact pins first; upgrade
only after the pinned stack reproduces.

## Source repositories

| Component | Repository | Revision | Notes |
|---|---|---|---|
| tt-metal (model implementation) | https://github.com/ndalyTT/tt-metal | branch `deepseek-v4-flash-0731-quietbox2`, HEAD `d788873210` | 12 commits on top of upstream `tenstorrent/tt-metal` main `faed88c379101717ce16b9f0ca3acbcf1597b285`. The qualified deployment commit is `5114991f9f`; `d788873210` adds the previously uncommitted evidence and working sources. Two raw Tracy capture dirs (14.3 GB) are host-only. |
| vllm-tt-plugin | https://github.com/tenstorrent/vllm-tt-plugin | `e3fc84941bf7a1d0df32aae2c50d539259c925f0` | Installed editable into the tt-metal `python_env`. Unmodified. |
| DeepSeek Harness (`dsh`) | https://github.com/deepseek-ai/deepseek-harness | `cd5ef8148158c3a752a658978873241fdf8e2bbc` | Source reference only. The runtime used is the npm package `@deepseek-ai/dsh@0.1.0-rc.6`. Unmodified. |
| Apache Maka | https://github.com/apache/maka | `ff226aff2f3082e54300dea0ee9e410898ae2c0f` | Provenance for `terminal_bench_2_1/deepseek_harness_profile` (request-identical DeepSeek Harness arm). Unmodified. |
| Harbor (Terminal-Bench runner) | https://github.com/harbor-framework/harbor | `6ecebe4ae9910ee0b28a2e6e8fa30934c0b41dfa` | **Locally modified.** Apply `patches/harbor-6ecebe4-deepseek-terminus.patch` (7 tracked files changed, 4 new Terminus templates). Harbor CLI reports 0.22.0. |
| Terminal-Bench 2.1 dataset | https://github.com/harbor-framework/terminal-bench-2-1 | `7131e4375048a0e408a8fb404b5f499d726b695b` | Unmodified. 91 tasks. |

## Model

| Item | Value |
|---|---|
| Model | `deepseek-ai/DeepSeek-V4-Flash-0731` on Hugging Face |
| Pinned revision | `7872f01b1d1fe23eabc4c98b48bffcef5a386062` |
| On-disk size | 156 GB (48 safetensors shards, 166,878,536,440 bytes indexed) |
| Local path assumed by scripts | `/home/ttuser/deepseekv4flash/model_assets/DeepSeek-V4-Flash-0731` |
| Weights modified? | **No.** The BFP2/BFP4 block-float quantization is applied on the fly while loading the stock safetensors, inside the tt-metal model code. No derived checkpoint is written or uploaded. |

Two other checkpoints were downloaded, evaluated, and **rejected**; they are not
required: `0xSero/DeepSeek-V4-Flash-0731-REAP` (K160 expert-pruned) and
`mlx-community/DeepSeek-V4-Flash-0731-2.4bit-mixed`. See
`artifacts/quantization/README.md` and `PAUSE_HANDOFF.md` for why.

## Hardware and system software

| Item | Value |
|---|---|
| System | QuietBox 2, ASRock B850M-C, Ubuntu 24.04.4 LTS, kernel 7.0.0-30-generic, 249 GB RAM |
| Accelerators | 4x Blackhole P300C (two dual-chip boards), PCIe Gen4 x4 each |
| Mesh used | `MeshShape(4,1)`, tensor parallel 4, `FABRIC_1D_RING`, `RELAXED_INIT`, `TT_METAL_DISABLE_FABRIC_TWO_ERISC=1` |
| Firmware bundle | 19.11.0.0 (Blackhole Ethernet firmware 1.11.0) |
| TT-KMD | 2.9.0 |
| tt-smi / tt-flash / tt-umd / pyluwen | 5.3.0 / 3.10.0 / 0.9.5 / 0.8.5 (management venv, Python 3.12.3) |
| Hugepages | none configured (`HugePages_Total: 0`); the stack ran without them |

## Runtime toolchains

| Item | Value |
|---|---|
| tt-metal `python_env` | Python 3.12.13, vLLM 0.25.1, tt-metal built as `build_Release` (`v0.78.0-dev20260821-49-g5114991f9f`) |
| Harbor venv | Python 3.13.15, Harbor 0.22.0, managed by `uv` inside `terminal_bench_2_1/harbor` |
| Node | v22.23.2 (`local_tools/node22/node`, not in this repo; install any Node 22.x) |
| DeepSeek Harness toolchain | `@deepseek-ai/dsh@0.1.0-rc.6`, fingerprint `sha256:9a7c0851d0a4f1f985971bbd2f0eb0455ca22ed6b9d2081b2eba9b9574d49833`; see `terminal_bench_2_1/deepseek_harness_toolchain/manifest.json` and `checksums.sha256` |

## Evidence checksums

| Artifact | SHA-256 |
|---|---|
| Final OSL-512 performance sweep JSON (in tt-metal branch, `doc/vllm/vllm_server_benchmark_selective_bfp4_salience8_validtail_bounded_cache_required_sweep_osl512_20260827.json`) | `599915a3ef7cd9ee19b21e34c391455112470769a3b1af3f48d36163f958f249` |
| Post-reboot ERISC failure log (`terminal_bench_2_1/logs/vllm_server_deepseek_harness_max_v27_20260827_post_reboot.log`) | `0687321da09edb320876bf07843216cf9d35217adf52a7cc7c6a0272b600e804` |
| Session-log archive (GitHub Release asset `session-logs-final-post-reboot-20260827T2337Z.tar.gz`) | `4d6cd5ca2e2f7ea2b7df633210dd2df8580380930ed9db82d4b6cd3bf3a9523c` |

Full manifests: `artifacts/FINAL_POST_REBOOT_CHECKSUMS_20260827.txt`,
`artifacts/RESUME_AFTER_HOST_REBOOT_20260827_CHECKSUMS.txt`,
`artifacts/tenstorrent_support_20260828/MANIFEST.sha256`,
`artifacts/tenstorrent_support_fabric_test_20260831/MANIFEST.sha256`.
