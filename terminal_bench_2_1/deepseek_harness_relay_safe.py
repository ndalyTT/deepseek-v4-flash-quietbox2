"""Restricted OpenAI relay for DeepSeek Harness provider-default parity.

The relay exposes only chat completions, requires the canary's local bearer
token, accepts only loopback or Docker-private source addresses, and forwards
only to the loopback vLLM server. It logs request metadata but never content.
"""

from __future__ import annotations

import argparse
import ipaddress
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
ALLOWED_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
)


def _is_allowed_source(remote: str | None) -> bool:
    if remote is None:
        return False
    try:
        address = ipaddress.ip_address(remote)
    except ValueError:
        return False
    return any(address in network for network in ALLOWED_NETWORKS)


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
    if not _is_allowed_source(request.remote):
        raise web.HTTPForbidden(text="source network is not allowed")
    if request.method != "POST" or request.path != "/v1/chat/completions":
        raise web.HTTPNotFound()
    if request.headers.get("Authorization") != "Bearer EMPTY":
        raise web.HTTPUnauthorized(text="invalid local relay token")

    upstream = request.app["upstream"].rstrip("/") + request.path
    request_id = uuid.uuid4().hex
    started = time.perf_counter()
    payload = await request.json()
    injected: dict[str, object] = {}

    if "top_p" not in payload:
        payload["top_p"] = 0.95
        injected["top_p"] = 0.95
    if "temperature" not in payload:
        payload["temperature"] = 1.0
        injected["temperature"] = 1.0
    if payload.get("tools") and "tool_choice" not in payload:
        payload["tool_choice"] = "auto"
        injected["tool_choice"] = "auto"

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
    body = json.dumps(payload, separators=(",", ":")).encode()
    first_byte_seconds: float | None = None
    status = 599
    try:
        session: ClientSession = request.app["session"]
        async with session.post(
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
                "remote": request.remote,
                "status": status,
                "injected": injected,
                "request": summary,
                "first_byte_seconds": first_byte_seconds,
                "elapsed_seconds": time.perf_counter() - started,
            },
        )


async def open_session(app: web.Application) -> None:
    app["session"] = ClientSession(
        timeout=ClientTimeout(total=None, sock_connect=30, sock_read=None),
        connector=TCPConnector(limit=2),
    )


async def close_session(app: web.Application) -> None:
    await app["session"].close()


def create_app(upstream: str, log_path: Path) -> web.Application:
    if not upstream.startswith("http://127.0.0.1:"):
        raise ValueError("relay upstream must be a loopback HTTP endpoint")
    app = web.Application(client_max_size=16 * 1024 * 1024)
    app["upstream"] = upstream
    app["log_path"] = log_path
    app.on_startup.append(open_session)
    app.on_cleanup.append(close_session)
    app.router.add_route("*", "/{tail:.*}", relay)
    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8011)
    parser.add_argument("--upstream", default="http://127.0.0.1:8010")
    parser.add_argument("--log", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    web.run_app(
        create_app(args.upstream, args.log),
        host=args.host,
        port=args.port,
        access_log=None,
    )


if __name__ == "__main__":
    main()
