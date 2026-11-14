"""python -m coground_server [--host 0.0.0.0] [--port 8000] [--reload]"""

from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(prog="coground_server")
    parser.add_argument("--host", default=os.environ.get("COGROUND_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("COGROUND_PORT", "8000")))
    parser.add_argument("--reload", action="store_true", help="コードの変更で自動再起動する")
    args = parser.parse_args()
    uvicorn.run("coground_server.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
