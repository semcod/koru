"""Tests for the IDE→project map exposed by the dashboard state."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from koruapi.dashboard_projects import projects_by_ide
from koruapi.dashboard_state import dashboard_ide_rows, dashboard_state
from koruide.ide import RunningIDE


def _fake_running_ides(tmp_path: Path) -> list[RunningIDE]:
    return [
        RunningIDE(id="cursor", label="Cursor", pid=1001, exe="/usr/bin/cursor"),
        RunningIDE(id="vscode", label="vscode", pid=2002, exe="/usr/bin/code"),
    ]


def test_projects_by_ide_uses_cmdline_and_cwd(tmp_path: Path) -> None:
    cursor_project = tmp_path / "alpha"
    vscode_project = tmp_path / "beta"
    cursor_project.mkdir()
    vscode_project.mkdir()
    (cursor_project / ".git").mkdir()
    (vscode_project / ".git").mkdir()

    def fake_cmdline(pid: int) -> str:
        if pid == 1001:
            return f"/usr/bin/cursor --user-data-dir /tmp {cursor_project}"
        if pid == 2002:
            return f"/usr/bin/code {vscode_project}"
        return ""

    def fake_cwd(pid: int) -> Path | None:
        return None

    ides = _fake_running_ides(tmp_path)
    with mock.patch("koru.wizard.project._read_proc_cmdline", side_effect=fake_cmdline), \
         mock.patch("koru.wizard.project._read_proc_cwd", side_effect=fake_cwd):
        mapping = projects_by_ide(ides)

    assert "cursor" in mapping
    assert "vscode" in mapping
    cursor_rows = mapping["cursor"]
    vscode_rows = mapping["vscode"]
    assert cursor_rows
    assert Path(cursor_rows[0]["path"]) == cursor_project.resolve()
    assert vscode_rows
    assert Path(vscode_rows[0]["path"]) == vscode_project.resolve()


def test_dashboard_state_includes_projects_by_ide(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    with mock.patch(
        "koruapi.dashboard_state.detect_running_ides",
        return_value=_fake_running_ides(tmp_path),
    ), mock.patch(
        "koruapi.dashboard_state.projects_by_ide",
        return_value={
            "cursor": [{"path": str(tmp_path / "alpha"), "source": "Cursor cwd"}],
        },
    ):
        rows, by_ide = dashboard_ide_rows()

    assert any(row["id"] == "cursor" and row["projects"] for row in rows)
    assert "cursor" in by_ide

    with mock.patch(
        "koruapi.dashboard_state.dashboard_ide_rows",
        return_value=(
            [
                {"id": "auto", "label": "Auto", "running": False, "projects": []},
                {
                    "id": "cursor",
                    "label": "Cursor",
                    "running": True,
                    "pid": 1001,
                    "exe": "/usr/bin/cursor",
                    "projects": [{"path": str(tmp_path / "alpha"), "source": "Cursor cwd"}],
                },
            ],
            {"cursor": [{"path": str(tmp_path / "alpha"), "source": "Cursor cwd"}]},
        ),
    ):
        payload = dashboard_state(
            project=tmp_path,
            host="127.0.0.1",
            port=8765,
            lan=False,
            configured_workspace=None,
            queue_name="default",
        )

    assert "projects_by_ide" in payload
    assert payload["projects_by_ide"]["cursor"][0]["path"].endswith("alpha")
    cursor_row = next(row for row in payload["ides"] if row["id"] == "cursor")
    assert cursor_row["projects"][0]["path"].endswith("alpha")
