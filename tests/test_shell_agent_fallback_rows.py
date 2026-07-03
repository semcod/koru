"""Shell LLM lanes must stay visible when tillm is unavailable.

The dashboard's "LLM / IDE lanes" table and the IDE-lane picker previously
went blank for shell clients (claude, aider, …) whenever the serving process
could not import tillm. koru.agents now falls back to PATH detection, and the
dashboard lane rows include launchable shell clients.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import koru.agents as agents
from koruapi.dashboard_state import dashboard_ide_rows


class TestFallbackShellRows:
    def test_fallback_engages_when_tillm_rows_empty(self, monkeypatch):
        monkeypatch.setattr(agents, "detect_shell_agent_rows", lambda **_k: [])
        monkeypatch.setattr(
            agents,
            "_which",
            lambda cmd: "/usr/bin/claude" if cmd == "claude" else None,
        )

        options = {opt.id: opt for opt in agents._shell_agent_options()}

        claude = options["claude-code"]
        assert claude.available is True
        assert claude.launchable is True
        assert claude.command == "/usr/bin/claude"
        assert "fallback detection" in claude.reason
        assert options["aider"].available is False

    def test_tillm_rows_win_when_present(self, monkeypatch):
        tillm_rows = [
            {
                "id": "claude-code",
                "label": "Claude Code",
                "available": True,
                "launchable": True,
                "command": "/path/claude",
                "reason": "Claude Code CLI detected in PATH.",
                "autopilot_backend": "vendor_agent_cli",
            }
        ]
        monkeypatch.setattr(
            agents, "detect_shell_agent_rows", lambda **_k: tillm_rows
        )

        options = agents._shell_agent_options()

        assert [opt.id for opt in options] == ["claude-code"]
        assert "fallback" not in options[0].reason

    def test_detect_agent_options_lists_claude_without_tillm(
        self, tmp_path: Path, monkeypatch
    ):
        monkeypatch.setattr(agents, "detect_shell_agent_rows", lambda **_k: [])
        monkeypatch.setattr(
            agents,
            "_which",
            lambda cmd: "/usr/bin/claude" if cmd == "claude" else None,
        )

        ids = [opt.id for opt in agents.detect_agent_options(tmp_path)]

        assert "claude-code" in ids

    def test_lane_rows_only_launchable(self, monkeypatch):
        monkeypatch.setattr(agents, "detect_shell_agent_rows", lambda **_k: [])
        monkeypatch.setattr(
            agents,
            "_which",
            lambda cmd: "/usr/bin/claude" if cmd == "claude" else None,
        )

        lane_ids = [row["id"] for row in agents.shell_agent_lane_rows()]

        assert lane_ids == ["claude-code"]


class TestDashboardShellLanes:
    def test_ide_rows_include_shell_lanes(self):
        shell_lanes = [
            {
                "id": "claude-code",
                "label": "Claude Code",
                "available": True,
                "launchable": True,
                "command": "/usr/bin/claude",
            }
        ]
        with mock.patch(
            "koruapi.dashboard_state.detect_running_ides", return_value=[]
        ), mock.patch(
            "koruapi.dashboard_state.projects_by_ide", return_value={}
        ), mock.patch(
            "koruapi.dashboard_state.autopilot_ide_choices",
            return_value=("auto", "vscode"),
        ), mock.patch(
            "koruapi.dashboard_state.shell_agent_lane_rows",
            return_value=shell_lanes,
        ):
            rows, _by_ide = dashboard_ide_rows()

        shell_row = next(row for row in rows if row["id"] == "claude-code")
        assert shell_row["kind"] == "shell"
        assert shell_row["label"] == "Claude Code · CLI"
        assert shell_row["running"] is False

    def test_shell_lane_does_not_duplicate_editor_ids(self):
        with mock.patch(
            "koruapi.dashboard_state.detect_running_ides", return_value=[]
        ), mock.patch(
            "koruapi.dashboard_state.projects_by_ide", return_value={}
        ), mock.patch(
            "koruapi.dashboard_state.autopilot_ide_choices",
            return_value=("auto", "vscode"),
        ), mock.patch(
            "koruapi.dashboard_state.shell_agent_lane_rows",
            return_value=[{"id": "vscode", "label": "clash", "launchable": True}],
        ):
            rows, _by_ide = dashboard_ide_rows()

        assert [row["id"] for row in rows].count("vscode") == 1
