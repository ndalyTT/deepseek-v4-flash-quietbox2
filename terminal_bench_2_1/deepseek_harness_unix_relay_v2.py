"""Run the constrained DeepSeek Harness relay on a Unix-domain socket.

This runner exists because ``aiohttp.web.run_app`` returns only after shutdown,
which is too late to change the socket permissions needed by the Docker task.
It starts the site explicitly, applies the permissions immediately, prints a
machine-readable readiness line, and then waits for SIGINT/SIGTERM.
"""

from __future__ import annotations

import asyncio
import os
import signal
import stat

from aiohttp import web

from deepseek_harness_unix_relay import create_app, parse_args


async def run() -> None:
    args = parse_args()
    args.socket.parent.mkdir(parents=True, exist_ok=True)
    if args.socket.exists():
        if not stat.S_ISSOCK(args.socket.stat().st_mode):
            raise RuntimeError(f"refusing to replace non-socket path: {args.socket}")
        args.socket.unlink()

    runner = web.AppRunner(create_app(args.upstream, args.log), access_log=None)
    await runner.setup()
    site = web.UnixSite(runner, str(args.socket))
    await site.start()
    os.chmod(args.socket, 0o666)
    print(f"READY socket={args.socket} upstream={args.upstream}", flush=True)

    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stopped.set)
    try:
        await stopped.wait()
    finally:
        await runner.cleanup()
        if args.socket.exists() and stat.S_ISSOCK(args.socket.stat().st_mode):
            args.socket.unlink()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
