"""Tests for the IDE→project map exposed by the dashboard state."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from koruapi.dashboard_projects import (
    _read_workspace_folder,
    _walk_descendant_pids,
    _workspace_storage_projects,
    integrated_terminal_cwds,
    projects_by_ide,
)
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


def test_read_workspace_folder_parses_file_url(tmp_path: Path) -> None:
    project = tmp_path / "alpha"
    project.mkdir()
    storage = tmp_path / "workspaceStorage" / "deadbeef"
    storage.mkdir(parents=True)
    (storage / "workspace.json").write_text(
        '{"folder": "file://' + str(project) + '"}',
        encoding="utf-8",
    )
    found = _read_workspace_folder(storage)
    assert found is not None
    assert found == project.resolve()


def test_workspace_storage_projects_reads_cursor_dir(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "home"
    project_a = tmp_path / "proj-a"
    project_b = tmp_path / "proj-b"
    for project in (project_a, project_b):
        project.mkdir()
        (project / ".git").mkdir()

    storage = fake_home / ".config" / "Cursor" / "User" / "workspaceStorage"
    (storage / "hash-a").mkdir(parents=True)
    (storage / "hash-b").mkdir(parents=True)
    (storage / "hash-a" / "workspace.json").write_text(
        '{"folder": "file://' + str(project_a) + '"}',
        encoding="utf-8",
    )
    (storage / "hash-b" / "workspace.json").write_text(
        '{"folder": "file://' + str(project_b) + '"}',
        encoding="utf-8",
    )

    monkeypatch.setenv("HOME", str(fake_home))
    rows = _workspace_storage_projects("cursor")
    paths = sorted(row["path"] for row in rows)
    assert paths == sorted([str(project_a.resolve()), str(project_b.resolve())])
    assert all(row["source"].startswith("cursor") for row in rows)


def test_walk_descendant_pids_traverses_children(monkeypatch) -> None:
    tree = {1000: [1010, 1020], 1010: [1030], 1020: [], 1030: []}
    monkeypatch.setattr(
        "koruapi.dashboard_projects._read_proc_children",
        lambda pid: list(tree.get(pid, [])),
    )
    descendants = _walk_descendant_pids(1000)
    assert sorted(descendants) == [1010, 1020, 1030]


def test_walk_descendant_pids_handles_cycles(monkeypatch) -> None:
    tree = {1: [2], 2: [1, 3], 3: []}
    monkeypatch.setattr(
        "koruapi.dashboard_projects._read_proc_children",
        lambda pid: list(tree.get(pid, [])),
    )
    descendants = _walk_descendant_pids(1)
    assert sorted(descendants) == [2, 3]


def test_integrated_terminal_cwds_reads_shell_processes(tmp_path: Path, monkeypatch) -> None:
    project_a = tmp_path / "proj-a"
    project_a.mkdir()
    (project_a / ".git").mkdir()

    monkeypatch.setattr(
        "koruapi.dashboard_projects._walk_descendant_pids",
        lambda pid, max_pids=256: [4242, 4243, 4244],
    )

    def fake_comm(pid: int) -> str:
        return {4242: "bash", 4243: "node", 4244: "zsh"}.get(pid, "")

    def fake_cwd(pid: int):
        return {4242: project_a, 4244: project_a}.get(pid)

    monkeypatch.setattr("koruapi.dashboard_projects._read_proc_comm", fake_comm)
    monkeypatch.setattr("koruapi.dashboard_projects._read_proc_cwd_path", fake_cwd)

    cwds = integrated_terminal_cwds(9999)
    assert cwds == [project_a.resolve()]


def test_projects_by_ide_picks_up_terminal_cwd(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "proj-x"
    project.mkdir()
    (project / ".git").mkdir()

    monkeypatch.setattr(
        "koruapi.dashboard_projects._workspace_storage_projects",
        lambda ide_id: [],
    )
    monkeypatch.setattr(
        "koruapi.dashboard_projects.integrated_terminal_cwds",
        lambda pid: [project.resolve()],
    )

    ides = [RunningIDE(id="cursor", label="Cursor", pid=4242, exe="/usr/bin/cursor")]

    def fake_cmdline(pid: int) -> str:
        return "/usr/bin/cursor"

    def fake_cwd(pid: int):
        return None

    with mock.patch("koru.wizard.project._read_proc_cmdline", side_effect=fake_cmdline), \
         mock.patch("koru.wizard.project._read_proc_cwd", side_effect=fake_cwd):
        mapping = projects_by_ide(ides)

    paths = [row["path"] for row in mapping["cursor"]]
    assert str(project.resolve()) in paths
    sources = [row["source"] for row in mapping["cursor"]]
    assert any("integrated shell" in s for s in sources)


def test_projects_by_ide_skips_home_directory(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / ".git").mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    ides = [RunningIDE(id="cursor", label="Cursor", pid=4242, exe="/usr/bin/cursor")]

    def fake_cmdline(pid: int) -> str:
        return "/usr/bin/cursor"

    def fake_cwd(pid: int) -> Path | None:
        return fake_home

    with mock.patch("koru.wizard.project._read_proc_cmdline", side_effect=fake_cmdline), \
         mock.patch("koru.wizard.project._read_proc_cwd", side_effect=fake_cwd):
        mapping = projects_by_ide(ides)

    assert mapping["cursor"] == []
