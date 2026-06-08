"""REST server CLI."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rest2coru FastAPI server")
    parser.add_argument("cmd", nargs="?", default="serve")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8218)
    args = parser.parse_args(argv)
    if args.cmd in {"serve", "server"}:
        import uvicorn

        uvicorn.run("rest2coru.app:app", host=args.host, port=args.port, reload=False)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
