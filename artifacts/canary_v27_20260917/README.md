# Official DeepSeek Harness Terminal-Bench 2.1 canary (v27, `fix-git`) — 2026-09-17

First scored run of the official-Harness path. Everything before today was a
mock-response preflight (Aug 27) or the superseded Terminus/DSML path.

## Setup that ran

- Server: unchanged `run_deepseek_v4_harness_server.sh`, launched 20:40 UTC as
  the first fabric init after a `tt-smi -r`; ready 21:04 UTC. Firmware
  19.13.1.0, tt-metal `d788873210`, vllm 0.25.1, `--reasoning-parser
  deepseek_v4 --tool-call-parser deepseek_v4 --tokenizer-mode deepseek_v4`.
- Relay: `deepseek_harness_unix_relay.py` with the new `--upstream-model`
  rewrite (Harness asks for `deepseek-v4-flash`; vLLM serves
  `deepseek-ai/DeepSeek-V4-Flash-0731`). Injected defaults unchanged:
  temperature 1.0, top_p 0.95, tool_choice auto.
- Harness: DSH profile `quietbox2-eval`, thinking enabled, reasoning effort
  max, max_tokens 49,152, tools `bash` + one other (tool_count 2), single task
  `fix-git`, agent timeout 14,400 s.

## Attempt 1 (21:08 UTC): infrastructure error, fixed

HTTP 404 from vLLM: model id mismatch (see above). Preserved as
`terminal_bench_2_1/jobs/...-v27__attempt1_model404_20260917T2108Z/`.

## Attempt 2 (21:11 UTC): the model does not stop after tool calls

Turn 1 request: 1,179 prompt tokens, 2 messages, 2 tools. First byte after
28.3 s. Streamed for **7,254 s** (2 h 1 min) and ended with vLLM
`finished_reason=length` at exactly **49,152 output tokens**, the cap.

What the model produced in that single turn (from the DSH session ledger,
`dsh_session_turn1_snapshot_2345Z.jsonl`):

| Item | Value |
|---|---|
| Reasoning blocks | 0 (thinking was enabled and the prompt demands maximum reasoning; none was emitted or surfaced) |
| Text | 8,731 chars: one sensible opening sentence, then the word `response` repeated between tool calls |
| Tool-call blocks | **722** in one assistant message |
| Distinct tool commands | 21 |
| Most repeated command | `git ls-files -s --modified --others --cached --skipped-kopt 2>&1 \| head -30` x **702** (`--skipped-kopt` is not a git flag) |
| First five commands | `git status --short --ahead -b`, `git branch -a`, `git log --oneline --all --decorate -20`, `git diff --stat --cached`, `git diff --stat` (all reasonable) |

Interpretation: the DSML tool-call blocks were well formed (the parser
extracted every one), but after its first `</｜DSML｜tool_calls>` the model
never emitted `<｜end▁of▁sentence｜>`. Instead it improvised a tool-response
section (rendered as the bare word `response`) and issued another call, and
after about twenty varied commands it fell into a 702-repeat loop until the
token cap. The 8-token probe earlier finished with `stop`, so EOS itself
works; the failure is specific to long agentic generation. This is the same
family as the Aug 25-27 Terminus result ("repeated rejected actions, timed
out after 15 actions"), now reproduced under DeepSeek's own request format,
with reasoning enabled, and with no output cap in the way. It points at the
deployed quantization (BFP2_B routed experts in 35 of 43 layers) or at the
TT decode path, not at the harness, relay, parser, or fabric.

DSH then executed the 722 queued bash calls serially inside the task
container (23:12 to about 23:50 UTC, roughly 3-4 s each). Whatever it sends
as turn 2 cannot finish before Harbor's 14,400 s agent timeout at about
01:11 UTC on 2026-09-18.

## Final Harbor verdict

Trial `fix-git__NcnBpwE` finished 2026-09-17 23:55:26 UTC (2 h 44 min).

| Field | Value |
|---|---|
| Reward | **0.0** |
| Verifier | 2 of 2 tests failed (`test_about_file`, `test_layout_file`); the lost commit was never restored |
| Exception | `NonZeroAgentExitCodeError`: DSH exited 1 with `INVALID_REQUEST: Unterminated string starting at: line 1 column 13 (char 12)` |
| Turn 2 | 725 messages (system, user, assistant, 722 tool results); vLLM answered HTTP 400 in 0.0 s because the 722nd tool call's JSON arguments had been cut mid-string by the 49,152-token cap and were echoed back verbatim |
| Model requests | 2 (turn 1 length-capped, turn 2 rejected) |

**Reading the score.** This 0.0 is the first result on the official-Harness
path and it is *not* a protocol, parser, relay, Docker, or verifier failure:
the request reached the model in DeepSeek's own format with reasoning enabled
and no output cap in the way, the DSML tool calls parsed, and DSH executed
them. The run failed because the served model did not end its turn after a
tool call and degenerated into a 702-repeat loop of a hallucinated command.
That is a decision-quality / generation-quality failure of the deployed
mixed BFP2/BFP4 quantization on the TT decode path. It matches the Aug 25-27
Terminus-path failure and removes "harness/request parity" as the
explanation. Do not run the full Terminal-Bench 2.1 sweep on this
configuration; it would produce 0.0 per task at about 2 h 45 min per task.

Recommended next experiments, in order of cost: (1) a 20-30 request
non-agentic probe set through the same server measuring EOS emission after
DSML tool-call blocks and repetition rate; (2) the same canary with a
`--max-tokens` cap of 4,096 to 8,192 via the relay to bound damage and to
see whether turn 2 ever forms correctly; (3) re-evaluate the quantization
policy (fewer BFP2_B layers) if (1) shows the loop is generation quality.


## Files

- `dsh_session_turn1_snapshot_2345Z.jsonl` — DSH session ledger copied from
  the task container at 23:45 UTC (turn 1 complete, tool execution ongoing).
- `relay_ledger_snapshot_2345Z.jsonl` — relay records: attempt-1 404, the
  8-token probe, and the 7,254 s turn-1 request.
- Harbor trial directory:
  `terminal_bench_2_1/jobs/tb21-dsv4-quietbox2-canary-fix-git-deepseek-harness-max-v27/fix-git__NcnBpwE/`
  (Harbor copies `deepseek-harness.txt`, the bridge log, and `dsh-sessions/**`
  there on completion).
- Server log: `terminal_bench_2_1/logs/vllm_server_deepseek_harness_max_v27_20260917T204020Z_cust901.log`.
