from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path
from unittest import mock

from koru.cli import main


def _run_main(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with mock.patch("sys.argv", ["koru", *argv]):
        with mock.patch("sys.stdout", new=buf):
            code = main()
    return code, buf.getvalue()


def test_agent_list_json_includes_ready_summary() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)

        fake_agents = [
            {
                "id": "gemini-cli",
                "label": "Gemini CLI",
                "available": True,
                "launchable": True,
                "command": "/usr/bin/gemini",
                "reason": "Gemini CLI detected in PATH.",
                "project_hint": False,
            },
            {
                "id": "openrouter",
                "label": "OpenRouter automation lane",
                "available": False,
                "launchable": False,
                "command": None,
                "reason": "OPENROUTER_API_KEY is not set.",
                "project_hint": False,
            },
        ]

        class _FakeAgent:
            def __init__(self, payload: dict):
                self._payload = payload
                self.available = bool(payload.get("available"))
                self.launchable = bool(payload.get("launchable"))
                self.id = str(payload.get("id"))
                self.reason = str(payload.get("reason"))

            def to_dict(self) -> dict:
                return dict(self._payload)

        with mock.patch(
            "koru._legacy_cli_impl.detect_agent_options",
            return_value=[_FakeAgent(p) for p in fake_agents],
        ):
            code, output = _run_main("agent", "--project", str(project), "--list", "--format", "json")

        assert code == 0
        payload = json.loads(output)
        assert payload["summary"]["total"] == 2
        assert payload["summary"]["available"] == 1
        assert payload["summary"]["launchable"] == 1
        assert payload["summary"]["ready"] is True
        assert payload["agents"][0]["id"] == "gemini-cli"
