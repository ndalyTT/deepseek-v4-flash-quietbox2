# Reproducing the QuietBox2 deployment

This walks from an empty host to serving the model, running the performance
sweep, and running the official-Harness Terminal-Bench canary. Versions are in
`PINS.md`. Commands below are the ones that were actually used on the
QuietBox2 host; where the original environment-build steps were not captured
verbatim, this says so and points to the upstream instructions.

All paths assume the workspace root `/home/ttuser/deepseekv4flash`. If you use
another root, set it once as `WS` and edit the `TT_METAL_ROOT`,
`DEEPSEEK_MODEL`, and `TB_ROOT` assignments at the top of
`terminal_bench_2_1/run_*.sh`, plus the absolute paths in the Harbor YAML
configs.

## 0. Host prerequisites

- Ubuntu 24.04, kernel 7.0.x, TT-KMD 2.9.0, firmware bundle 19.11.0 on all
  four P300C chips, `tt-smi` 5.3.0. Verify with `tt-smi -ls --local` and
  `tt-smi -s`.
- Docker (Harbor runs tasks in containers). The host firewall blocked Docker
  host-gateway routing, which is why the relay uses a bind-mounted Unix socket.
- `uv` for the Harbor venv, Node 22.x for the `dsh` toolchain, `git`, `curl`.
- About 200 GB free for the checkpoint plus builds.

## 1. Clone at the pins

```bash
WS=/home/ttuser/deepseekv4flash
mkdir -p "$WS" && cd "$WS"

git clone --branch deepseek-v4-flash-0731-quietbox2 https://github.com/ndalyTT/tt-metal.git tt-metal
git -C tt-metal submodule update --init --recursive

git clone https://github.com/tenstorrent/vllm-tt-plugin.git
git -C vllm-tt-plugin checkout e3fc84941bf7a1d0df32aae2c50d539259c925f0

git clone https://github.com/ndalyTT/deepseek-v4-flash-quietbox2.git publish/deepseek-v4-flash-quietbox2
# then copy artifacts/, terminal_bench_2_1/, *.md from it into $WS, or symlink
```

Reference-only checkouts (not needed to run anything):

```bash
git clone --depth 1 https://github.com/deepseek-ai/deepseek-harness.git   # cd5ef814
git clone --depth 1 https://github.com/apache/maka.git                    # ff226aff
```

## 2. Model weights

```bash
hf download deepseek-ai/DeepSeek-V4-Flash-0731 \
  --revision 7872f01b1d1fe23eabc4c98b48bffcef5a386062 \
  --local-dir "$WS/model_assets/DeepSeek-V4-Flash-0731"
```

48 safetensors shards, about 156 GB on disk. Do not convert or requantize
them; the tt-metal model quantizes at load time.

## 3. Build tt-metal and the vLLM environment

The build followed the standard tt-metal instructions in `INSTALLING.md` of
the branch. The exact command history was not captured; the resulting
environment was Python 3.12.13 in `tt-metal/python_env`, a `build_Release`
tree, vLLM 0.25.1, and vllm-tt-plugin installed editable.

```bash
cd "$WS/tt-metal"
./install_dependencies.sh
./build_metal.sh                # produces build_Release
./create_venv.sh                # produces python_env
source python_env/bin/activate
pip install -e "$WS/vllm-tt-plugin"   # brings vLLM 0.25.1 as a dependency
```

Check: `python -c "import ttnn, vllm; print(vllm.__version__)"` prints
`0.25.1` and the vLLM plugin log line `Platform plugin tt is activated`
appears.

Host-only regression that needs no devices (62 to 64 tests depending on the
checkpoint of the docs):

```bash
cd "$WS/tt-metal"
python_env/bin/pytest models/autoports/deepseek_ai_deepseek_v4_flash_0731/tests -q
```

## 4. Bounded hardware recovery contract

Run these one at a time, never in parallel with any other TT process.

```bash
cd "$WS/tt-metal"
pgrep -af 'vllm|EngineCore|harbor|deepseek_harness|terminal_bench|run_deepseek'   # expect nothing
timeout 60 tt-smi -ls --local
timeout 180 tt-smi -r
timeout 60 tt-smi -ls --local
env PYTHONPATH=build_Release TT_METAL_DISABLE_FABRIC_TWO_ERISC=1 \
  python_env/bin/python -c 'import ttnn; m=ttnn.open_mesh_device(ttnn.MeshShape(4,1), trace_region_size=0); ttnn.close_mesh_device(m); print("MESH_SMOKE_OK")'
```

Require all four devices and `MESH_SMOKE_OK`. Repeat the reset at most once.
The fabric-enabled standalone smoke that Tenstorrent support requested is in
the tt-metal branch and is invoked by
`artifacts/tenstorrent_support_fabric_test_20260831/EXACT_COMMAND.sh`.

## 5. Serve the model

```bash
script -q -f -c "$WS/terminal_bench_2_1/run_deepseek_v4_harness_server.sh" \
  "$WS/terminal_bench_2_1/logs/vllm_server_$(date -u +%Y%m%dT%H%MZ).log"
```

This runs `vllm serve` on `127.0.0.1:8010` with the 4x1 mesh,
`FABRIC_1D_RING`, `RELAXED_INIT`, on-device sampling, trace mode, context
131,072, block size 128, batch 1, and the DeepSeek V4 tokenizer, reasoning and
tool-call parsers. Load takes 24 to 26 minutes. Do not run `tt-smi` or any
other TT workload while it owns the devices. Readiness:

```bash
curl -fsS http://127.0.0.1:8010/health
curl -fsS http://127.0.0.1:8010/v1/models     # id deepseek-ai/DeepSeek-V4-Flash-0731, max_model_len 131072
```

The non-Harness variant `run_deepseek_v4_server.sh` (in
`artifacts/tenstorrent_support_20260828/config/`) differs only by omitting the
two tool-call flags; it is the last configuration known to initialize.

**Known failure:** if device 0 reports unchanged ERISC heartbeats on virtual
cores `29-25`, `28-25`, `24-25`, `22-25` and `Device 0 init: failed to
initialize FW!`, you have reproduced the open support case. Preserve the log
and stop; do not loop.

## 6. Performance sweep (OSL 512)

With the server resident:

```bash
cd "$WS/tt-metal"
python_env/bin/python models/autoports/deepseek_ai_deepseek_v4_flash_0731/tools/run_vllm_server_benchmark.py --help
```

The qualified run used exact token-ID prompts at ISL 128, 1,024, 4,096,
8,192, 16,384, 32,768, 65,536, 130,560, OSL 512 enforced with `max_tokens`
plus `ignore_eos`, deterministic top-k-one device sampling, one excluded
two-token warmup per row, and `--resume` support with atomic per-ISL
checkpoints. The reference output is
`doc/vllm/vllm_server_benchmark_selective_bfp4_salience8_validtail_bounded_cache_required_sweep_osl512_20260827.json`
in the branch. Do not send `min_tokens`; the adapter fails closed on
host-only sampling options.

## 7. Terminal-Bench 2.1 through the official DeepSeek Harness (v27)

### Harbor and dataset

```bash
cd "$WS/terminal_bench_2_1"
git clone https://github.com/harbor-framework/harbor.git
git -C harbor checkout 6ecebe4ae9910ee0b28a2e6e8fa30934c0b41dfa
git -C harbor apply "$WS/publish/deepseek-v4-flash-quietbox2/patches/harbor-6ecebe4-deepseek-terminus.patch"
(cd harbor && uv sync)          # Python 3.13 venv at harbor/.venv, Harbor 0.22.0

git clone https://github.com/harbor-framework/terminal-bench-2-1.git dataset
git -C dataset checkout 7131e4375048a0e408a8fb404b5f499d726b695b
```

Validate the environment with the oracle smoke (scored 1.0 here):

```bash
harbor/.venv/bin/harbor jobs start --config config_oracle_pinned_smoke.yaml --yes
```

### DeepSeek Harness toolchain

The toolchain directory is Node 22.23.2 plus `@deepseek-ai/dsh@0.1.0-rc.6`
installed under `lib/dsh/node_modules`, produced by Apache Maka's
`maka-eval/prepare-deepseek-harness-toolchain` in a `node:22-bookworm`
container. Rebuild it with Maka at `ff226aff`, then confirm
`checksums.sha256` and the fingerprint in `manifest.json` match. The profile
in `deepseek_harness_profile/` and its `NOTICE.md` are already in this repo.

### Run

Three persistent sessions, in order. Never send a second model request
while a canary is running.

```bash
# 1. server (section 5), wait for /health
# 2. relay
script -q -f -c "$WS/terminal_bench_2_1/run_deepseek_harness_unix_relay.sh" \
  "$WS/terminal_bench_2_1/logs/relay_console_$(date -u +%Y%m%dT%H%MZ).log"
# require a console line starting with: READY socket=
# 3. canary
script -q -f -c "$WS/terminal_bench_2_1/run_deepseek_harness_canary_v27.sh" \
  "$WS/terminal_bench_2_1/logs/canary_v27_console_$(date -u +%Y%m%dT%H%MZ).log"
```

The canary is one attempt of the `fix-git` task with a 14,400 s agent
timeout. The relay injects `temperature=1.0`, `top_p=0.95`, and
`tool_choice=auto` when `dsh` rc.6 omits them, and logs metadata only.
Results land in
`terminal_bench_2_1/jobs/tb21-dsv4-quietbox2-canary-fix-git-deepseek-harness-max-v27/`.
Inspect reward, the DSH session ledger, and relay timings before scaling to
the full 89-task run; keep concurrency at one because the server is batch one.

Do not use v26, `deepseek_harness_host_gateway.yaml`, or the non-`unix`
relay/adapter files; they are kept for history only.

## 8. Shutdown order

Stop the canary, then the relay, then vLLM. Confirm with `pgrep` that
nothing from the run remains, and only then run the bounded reset in
section 4 if another TT lifecycle is needed.
