"""Exercise the MCP entry point with a real JSON-RPC input stream."""

import json
import os
import subprocess
import sys
from pathlib import Path


def test_startup_activity_does_not_corrupt_jsonrpc(tmp_path: Path) -> None:
    env = {**os.environ, 'KORU_ACTIVITY_LOG': '1', 'KORU_STDIO_FORMAT': 'text'}
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}}
    result = subprocess.run(
        [sys.executable, '-c', 'from koruapi.mcp import mcp_main; mcp_main([])'],
        cwd=tmp_path, env=env, input=json.dumps(request) + '\n',
        capture_output=True, text=True, timeout=30, check=True,
    )
    messages = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(messages) == 1
    assert messages[0]['id'] == 1
    assert 'protocolVersion' in messages[0]['result']
    assert 'starting stdio MCP server' in result.stderr
