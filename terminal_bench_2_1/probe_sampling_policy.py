#!/usr/bin/env python3
"""Probe DeepSeek V4 terminal-action behavior under several sampling policies."""

from __future__ import annotations

import argparse
import json
import runpy
import time
import urllib.request
from pathlib import Path


MODEL = "deepseek-ai/DeepSeek-V4-Flash-0731"
ACTION_PREFIX = '{"commands":[{"keystrokes":"'


def request_completion(api_base: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer EMPTY"},
        method="POST",
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=1200) as response:
        body = json.load(response)
    choice = body["choices"][0]
    return {
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "finish_reason": choice.get("finish_reason"),
        "text": choice.get("text", ""),
        "token_ids": choice.get("token_ids"),
        "usage": body.get("usage"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8010/v1")
    parser.add_argument(
        "--encoding-file",
        type=Path,
        default=Path(
            "/home/ttuser/deepseekv4flash/model_assets/"
            "DeepSeek-V4-Flash-0731/encoding/encoding_dsv4.py"
        ),
    )
    parser.add_argument(
        "--probe",
        choices=("sampling", "native", "command"),
        default="sampling",
    )
    parser.add_argument("--task-file", type=Path)
    parser.add_argument("--first-only", action="store_true")
    parser.add_argument(
        "--action-token",
        action="store_true",
        help="Mark the final prompt message with DeepSeek V4's official action task.",
    )
    parser.add_argument(
        "--thinking-mode",
        choices=("chat", "thinking"),
        default="chat",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("low", "high", "max"),
        default="low",
    )
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--brief-thinking", action="store_true")
    parser.add_argument("--native-prefill", action="store_true")
    parser.add_argument("--planning-only", action="store_true")
    parser.add_argument(
        "--policy",
        choices=("greedy", "low_sample", "sample", "recommended"),
        help="Run only one sampling policy.",
    )
    args = parser.parse_args()
    encoding_namespace = runpy.run_path(str(args.encoding_file))
    encode_messages = encoding_namespace["encode_messages"]
    if args.action_token:
        original_merge_tool_messages = encoding_namespace["merge_tool_messages"]

        def merge_tool_messages_with_task(messages):
            task = messages[-1].get("task") if messages else None
            merged = original_merge_tool_messages(messages)
            if task is not None and merged:
                merged[-1] = {**merged[-1], "task": task}
            return merged

        encode_messages.__globals__["merge_tool_messages"] = (
            merge_tool_messages_with_task
        )

    task = (
        "Control a Linux terminal. Output only compact JSON beginning "
        "{\"commands\":. Task: build POV-Ray 2.2 from source and install it at "
        "/usr/local/bin/povray. The current directory is /app and contains only "
        "a deps directory. Issue one concrete next command."
    )
    if args.task_file is not None:
        task = (
            "Use the terminal tools to solve this task:\n\n"
            + args.task_file.read_text()
            + "\n\nCurrent terminal screen:\nroot@container:/app#"
        )
    if args.brief_thinking:
        task = (
            "Reason for at most 64 tokens, then call exactly one tool. Do not "
            "plan the full task before acting.\n\n"
            + task
        )
    if args.planning_only:
        task = (
            "Do not call tools or pretend that commands ran. Produce a concise, "
            "concrete plan for solving the task after inspecting real tool "
            "results later.\n\n"
            + task
        )
    first_messages = [{"role": "user", "content": task}]
    next_messages = [
        {"role": "user", "content": task},
        {"role": "assistant", "content": '{"commands":[{"keystrokes":"ls -la\\n"}]}'},
        {
            "role": "user",
            "content": (
                "New Terminal Output:\n"
                "total 12\n"
                "drwxr-xr-x 2 root root 4096 deps\n"
                "root@container:/app#\n"
                "Do not repeat the previous command. Issue the next concrete command."
            ),
        },
    ]

    policies = [
        {"name": "greedy", "temperature": 0.0, "top_p": 1.0, "top_k": 1},
        {"name": "low_sample", "temperature": 0.2, "top_p": 0.95, "top_k": 8},
        {"name": "sample", "temperature": 0.6, "top_p": 0.95, "top_k": 20},
        {"name": "recommended", "temperature": 1.0, "top_p": 0.95},
    ]
    if args.probe == "native":
        tool = {
            "type": "function",
            "function": {
                "name": "bash_command",
                "description": "Send exact keystrokes to the Linux terminal.",
                "parameters": {
                    "type": "object",
                    "properties": {"keystrokes": {"type": "string"}},
                    "required": ["keystrokes"],
                },
            },
        }
        system = {
            "role": "system",
            "content": (
                "Solve the task in the Linux terminal. Use bash_command for one "
                "concrete action at a time. Do not repeat a successful command."
            ),
            "tools": [tool],
        }
        first_messages = [system, {"role": "user", "content": task}]
        next_messages = [
            system,
            {"role": "user", "content": task},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "bash_command",
                            "arguments": json.dumps({"keystrokes": "ls -la\n"}),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "content": "total 12\ndrwxr-xr-x 2 root root 4096 deps\nroot@container:/app#",
            },
        ]
        policies = [policies[0], policies[2], policies[3]]
        action_prefix = ""
        max_tokens = 256
        stop = ["<｜end▁of▁sentence｜>"]
        if args.native_prefill:
            action_prefix = (
                '<｜DSML｜tool_calls>\n<｜DSML｜invoke name="bash_command">\n'
                '<｜DSML｜parameter name="keystrokes" string="true">'
            )
            max_tokens = 96
            stop = ["</｜DSML｜parameter>"]
    elif args.probe == "command":
        if args.task_file is not None:
            command_task = (
                "Control a Linux terminal. Reply with exactly one shell command "
                "and a newline, with no prose or formatting. Task:\n"
                + args.task_file.read_text()
                + "\nCurrent terminal: root@container:/app#"
            )
        else:
            command_task = (
                "Control a Linux terminal to build POV-Ray 2.2 from source and "
                "install it at /usr/local/bin/povray. Reply with exactly one shell "
                "command and a newline, with no prose or formatting. Current "
                "directory: /app. Current entries: deps."
            )
        first_messages = [{"role": "user", "content": command_task}]
        next_messages = [
            {"role": "user", "content": command_task},
            {"role": "assistant", "content": "ls -la"},
            {
                "role": "user",
                "content": (
                    "Command output:\n"
                    "total 12\n"
                    "drwxr-xr-x 2 root root 4096 deps\n"
                    "Reply with a different next shell command only."
                ),
            },
        ]
        action_prefix = ""
        max_tokens = 64
        stop = ["\n", "<｜end▁of▁sentence｜>"]
    else:
        action_prefix = ACTION_PREFIX
        max_tokens = 96
        stop = ['","duration', '"}]}']

    if args.max_tokens is not None:
        max_tokens = args.max_tokens

    if args.policy:
        policies = [policy for policy in policies if policy["name"] == args.policy]

    results = []
    for policy in policies:
        turns = (("first", first_messages),)
        if not args.first_only:
            turns += (("after_ls", next_messages),)
        for turn, messages in turns:
            encoded_messages = [dict(message) for message in messages]
            if args.action_token:
                encoded_messages[-1]["task"] = "action"
            prompt = (
                encode_messages(
                    encoded_messages,
                    thinking_mode=args.thinking_mode,
                    reasoning_effort=args.reasoning_effort,
                )
                + action_prefix
            )
            payload = {
                "model": MODEL,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": policy["temperature"],
                "top_p": policy["top_p"],
                "stop": stop,
                "return_token_ids": True,
            }
            if "top_k" in policy:
                payload["top_k"] = policy["top_k"]
            try:
                outcome = request_completion(args.api_base, payload)
            except Exception as error:  # Keep the remaining probes useful.
                outcome = {"error": f"{type(error).__name__}: {error}"}
            results.append({"policy": policy, "turn": turn, **outcome})
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
