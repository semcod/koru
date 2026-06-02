"""Transport helpers for stdio-based Koru MCP server."""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, TextIO


def write_json(payload: dict[str, Any], *, stdout: TextIO = sys.stdout) -> None:
    """Write one JSON-RPC payload line to stdout."""
    raw = json.dumps(payload, separators=(",", ":"), default=str)
    stdout.write(raw + "\n")
    stdout.flush()


def log_stderr(message: str, *, stderr: TextIO = sys.stderr) -> None:
    """Write diagnostic message to stderr only."""
    print(message, file=stderr)


def run_stdio_loop(
    *,
    handle_message: Callable[[dict[str, Any]], dict[str, Any] | None],
    jsonrpc_error: Callable[[Any, int, str, Any | None], dict[str, Any]],
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    logger: Callable[[str], None] | None = None,
    writer: Callable[[dict[str, Any]], None] | None = None,
) -> int:
    """Read JSON-RPC from stdin and write responses to stdout."""
    _logger = logger or (lambda message: log_stderr(message, stderr=stderr))
    _writer = writer or (lambda payload: write_json(payload, stdout=stdout))

    _logger("koru mcp-server: started (stdio)")
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            _writer(jsonrpc_error(None, -32700, f"Parse error: {exc}"))
            continue

        response = handle_message(msg)
        if response is not None:
            _writer(response)

    _logger("koru mcp-server: stdin closed, exiting")
    return 0
