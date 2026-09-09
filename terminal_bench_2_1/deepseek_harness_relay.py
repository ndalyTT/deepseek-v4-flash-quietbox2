"""Narrow OpenAI relay for DeepSeek Harness provider-default parity.

DeepSeek Harness rc.6 omits ``top_p`` and ``tool_choice``. The official
DeepSeek evaluation uses top_p=0.95 and DeepSeek's API treats supplied tools
as automatically selectable. vLLM's neutral defaults differ, so this relay
fills only those absent fields and streams every response byte unchanged.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aiohttp import ClientSession, ClientTimeout, TCPConnector, web

HOP_BY_HOP_HEADERS = {
    "connection",
    "content-encoding",
    "content-length",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def _headers(headers: Any) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() != "host"
    }


def _append_record(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")


async def relay(request: web.Request) -> web.StreamResponse:
    upstream = request.app["upstream"].rstrip("/") + request.rel_url.path_qs
    request_id = uuid.uuid4().hex
    started = time.perf_counter()
    body = await request.read()
    injected: dict[str, object] = {}
    summary: dict[str, object] = {}

    if request.method == "POST" and request.path.endswith("/chat/completions"):
        payload = json.loads(body)
        if "top_p" not in payload:
            payload["top_p"] = 0.95
            injected["top_p"] = 0.95
        if "temperature" not in payload:
            payload["temperature"] = 1.0
            injected["temperature"] = 1.0
        if payload.get("tools") and "tool_choice" not in payload:
            payload["tool_choice"] = "auto"
            injected["tool_choice"] = "auto"
        body = json.dumps(payload, separators=(",", ":")).encode()
        summary = {
            "model": payload.get("model"),
            "message_count": len(payload.get("messages") or []),
            "tool_count": len(payload.get("tools") or []),
            "stream": payload.get("stream"),
            "max_tokens": payload.get("max_tokens"),
            "reasoning_effort": payload.get("reasoning_effort"),
            "thinking": payload.get("thinking"),
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            "tool_choice": payload.get("tool_choice"),
        }

    first_byte_seconds: float | None = None
    status = 599
    try:
        session: ClientSession = request.app["session"]
        async with session.request(
            request.method,
            upstream,
            headers=_headers(request.headers),
            data=body,
        ) as upstream_response:
            status = upstream_response.status
            response = web.StreamResponse(
                status=status,
                headers={
                    key: value
                    for key, value in upstream_response.headers.items()
                    if key.lower() not in HOP_BY_HOP_HEADERS
                },
            )
            await response.prepare(request)
            async for chunk in upstream_response.content.iter_any():
                if first_byte_seconds is None:
                    first_byte_seconds = time.perf_counter() - started
                await response.write(chunk)
            await response.write_eof()
            return response
    finally:
        _append_record(
            request.app["log_path"],
            {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status": status,
                "injected": injected,
                "request": summary,
                "first_byte_seconds": first_byte_seconds,
                "elapsed_seconds": time.perf_counter() - started,
            },
        )


async def close_session(app: web.Application) -> None:
    await app["session"].close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="172.17.0.1")
    parser.add_argument("--port", type=int, default=8011)
    parser.add_argument("--upstream", default="http://127.0.0.1:8010")
    parser.add_argument("--log", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = web.Application(client_max_size=16 * 1024 * 1024)
    app["upstream"] = args.upstream
    app["log_path"] = args.log
    app["session"] = ClientSession(
        timeout=ClientTimeout(total=None, sock_connect=30, sock_read=None),
        connector=TCPConnector(limit=2),
    )
    app.on_cleanup.append(close_session)
    app.router.add_route("*", "/{tail:.*}", relay)
    web.run_app(app, host=args.host, port=args.port, access_log=None)


if __name__ == "__main__":
    main()
