"""Unit tests for project candidate proposal."""

from __future__ import annotations

from pathlib import Path

from koru.wizard.ide import DetectedIDE
from koru.wizard.project import (
    _extract_workspace_from_cmdline,
    propose_projects,
)


def test_extract_workspace_from_cursor_cmdline(tmp_path: Path) -> None:
    workspace = tmp_path / "myproj"
    workspace.mkdir()
    cmdline = f"/opt/Cursor/cursor --user-data-dir=/home/x {workspace}"
    assert _extract_workspace_from_cmdline(cmdline) == workspace


def test_extract_workspace_ignores_nonexistent_paths() -> None:
    assert _extract_workspace_from_cmdline("/opt/Cursor/cursor /does/not/exist/x") is None


def test_extract_workspace_returns_none_for_empty_cmdline() -> None:
    assert _extract_workspace_from_cmdline("") is None


def test_propose_projects_includes_shell_cwd(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "svc"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    monkeypatch.chdir(project_root)

    candidates = propose_projects([])

    assert any(c.path == project_root.resolve() for c in candidates)
    assert any("shell cwd" in c.source for c in candidates)


def test_propose_projects_deduplicates(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "svc"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    monkeypatch.chdir(project_root)

    candidates = propose_projects([], max_results=5)

    paths = [c.path for c in candidates]
    assert len(paths) == len(set(paths))


def test_propose_projects_skips_non_running_ides(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "demo"
    project_root.mkdir()
    monkeypatch.chdir(project_root)
    not_running = DetectedIDE(
        id="cursor", label="Cursor", running=False, pid=None, path="/opt/cursor"
    )

    candidates = propose_projects([not_running])

    assert all("Cursor workspace" not in c.source for c in candidates)
