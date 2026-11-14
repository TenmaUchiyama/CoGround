"""Unity の代わりにサーバーを叩く確認用クライアント。

  python scripts/ws_client.py call system.ping
  python scripts/ws_client.py call debug.count '{"count": 5}'
  python scripts/ws_client.py call scene.update @tests/fixtures/tabletop_scene.json
  python scripts/ws_client.py listen                      # event を表示し続ける

  --url ws://<host>:8000/ws で接続先を変える（既定 ws://127.0.0.1:8000/ws）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import websockets


def load_params(arg: str | None) -> dict:
    if not arg:
        return {}
    if arg.startswith("@"):
        return json.loads(Path(arg[1:]).read_text(encoding="utf-8"))
    return json.loads(arg)


def show(msg: dict) -> None:
    print(json.dumps(msg, ensure_ascii=False), flush=True)


async def call(url: str, method: str, params: dict, show_events: bool) -> int:
    async with websockets.connect(url, max_size=None) as ws:
        await ws.send(json.dumps({"type": "request", "id": "cli-1", "method": method, "params": params}))
        while True:
            msg = json.loads(await ws.recv())
            if msg["type"] == "event":
                if show_events:
                    show(msg)
                continue
            show(msg)
            if msg["type"] == "response" and msg["id"] == "cli-1":
                return 0 if msg["ok"] else 1


async def listen(url: str) -> int:
    async with websockets.connect(url, max_size=None) as ws:
        async for raw in ws:
            show(json.loads(raw))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="ws://127.0.0.1:8000/ws")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_call = sub.add_parser("call")
    p_call.add_argument("method")
    p_call.add_argument("params", nargs="?", help="JSON 文字列、または @ファイル")
    p_call.add_argument("--events", action="store_true", help="途中に届いた event も表示する")
    sub.add_parser("listen")
    args = parser.parse_args()

    try:
        if args.cmd == "call":
            return asyncio.run(call(args.url, args.method, load_params(args.params), args.events))
        return asyncio.run(listen(args.url))
    except KeyboardInterrupt:
        return 0
    except OSError as e:
        print(f"接続できない: {args.url} ({e})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
