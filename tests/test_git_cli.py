from __future__ import annotations

import subprocess
from pathlib import Path

import koru.git_cli as git_cli_module
from koru.git_attribution import KORU_AGENT_COAUTHOR_TRAILER
from koru.git_cli import git_main


def _git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(project: Path) -> None:
    _git(project, "init")
    _git(project, "config", "user.name", "Human User")
    _git(project, "config", "user.email", "human@example.com")


def test_koru_git_commit_stages_and_adds_coauthor(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")

    rc = git_main(
        ["commit", "--project", str(tmp_path), "--add", "README.md", "-m", "test: commit"],
    )

    assert rc == 0
    message = _git(tmp_path, "log", "-1", "--format=%B").stdout
    author = _git(tmp_path, "log", "-1", "--format=%an <%ae>").stdout.strip()
    assert author == "Human User <human@example.com>"
    assert KORU_AGENT_COAUTHOR_TRAILER in message


def test_koru_git_commit_allow_empty(tmp_path: Path) -> None:
    _init_repo(tmp_path)

    rc = git_main(
        [
            "commit",
            "--project",
            str(tmp_path),
            "--allow-empty",
            "-m",
            "test: empty commit",
        ],
    )

    assert rc == 0
    assert KORU_AGENT_COAUTHOR_TRAILER in _git(tmp_path, "log", "-1", "--format=%B").stdout


def test_koru_git_push_dry_run(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    _git(tmp_path, "init", "--bare", str(remote))
    work.mkdir()
    _init_repo(work)
    _git(work, "remote", "add", "origin", str(remote))

    rc = git_main(["push", "--project", str(work), "--dry-run", "origin", "main"])

    assert rc != 2


class _FakeGh2McpService:
    calls: list[tuple[str, object]] = []

    def __init__(self, env_file: str):
        self.env_file = env_file
        self.calls.append(("init", env_file))

    def sync_token(self, force_gh_cli: bool = False) -> dict:
        self.calls.append(("sync_token", force_gh_cli))
        return {"success": True, "source": "gh_cli", "user": "tester"}

    def get_status(self, include_token: bool = False) -> dict:
        self.calls.append(("get_status", include_token))
        return {"configured": True, "gh_available": True, "user": "tester"}

    def get_last_pushed_repo(self, owner: str | None = None, limit: int = 100) -> dict:
        self.calls.append(("get_last_pushed_repo", (owner, limit)))
        return {"success": True, "repo": "tester/demo", "repo_url": "https://github.com/tester/demo"}


def test_koru_git_push_can_sync_token_with_gh2mcp(tmp_path: Path, monkeypatch) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    _git(tmp_path, "init", "--bare", str(remote))
    work.mkdir()
    _init_repo(work)
    _git(work, "remote", "add", "origin", str(remote))
    _FakeGh2McpService.calls = []
    monkeypatch.setattr(
        git_cli_module,
        "_load_gh2mcp_service_class",
        lambda: (_FakeGh2McpService, ""),
    )

    rc = git_main(
        [
            "push",
            "--project",
            str(work),
            "--dry-run",
            "--gh2mcp",
            "--force-gh-cli",
            "origin",
            "main",
        ],
    )

    assert rc != 2
    assert ("sync_token", True) in _FakeGh2McpService.calls


def test_koru_git_github_status_uses_gh2mcp(monkeypatch, capsys) -> None:
    _FakeGh2McpService.calls = []
    monkeypatch.setattr(
        git_cli_module,
        "_load_gh2mcp_service_class",
        lambda: (_FakeGh2McpService, ""),
    )

    rc = git_main(["github-status", "--include-token"])

    assert rc == 0
    assert '"user": "tester"' in capsys.readouterr().out
    assert ("get_status", True) in _FakeGh2McpService.calls


def test_koru_git_last_repo_uses_gh2mcp(monkeypatch, capsys) -> None:
    _FakeGh2McpService.calls = []
    monkeypatch.setattr(
        git_cli_module,
        "_load_gh2mcp_service_class",
        lambda: (_FakeGh2McpService, ""),
    )

    rc = git_main(["last-repo", "--owner", "tester", "--limit", "7"])

    assert rc == 0
    assert "tester/demo" in capsys.readouterr().out
    assert ("get_last_pushed_repo", ("tester", 7)) in _FakeGh2McpService.calls
