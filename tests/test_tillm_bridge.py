from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import koru.tillm_bridge as bridge


def test_normalize_tillm_model_preserves_flash_family() -> None:
    assert bridge._normalize_tillm_model("zai/glm-5.3-flash") == "glm-5.3-flash"
    assert bridge._normalize_tillm_model("z.ai/glm-5.3-flash") == "glm-5.3-flash"


def test_normalize_tillm_model_keeps_other_model_ids() -> None:
    assert bridge._normalize_tillm_model("openrouter/z-ai/glm-5.3-flash") == ("openrouter/z-ai/glm-5.3-flash")
    assert bridge._normalize_tillm_model(None) is None


def test_drive_shell_chat_passes_bare_model_to_tillm(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def fake_drive_koru_chat(**kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {"ok": True, "model": kwargs["model"]}

    monkeypatch.setattr(bridge, "ensure_local_tillm_path", lambda: None)
    monkeypatch.setattr("tillm.compat.drive_koru_chat", fake_drive_koru_chat, raising=False)
    result = bridge.drive_shell_chat(
        client_id="opencode",
        project=_workspace(tmp_path)[1],
        prompt="test",
        execute=True,
        model="zai/glm-5.3-flash",
    )

    assert result["model"] == "glm-5.3-flash"
    assert calls[0]["model"] == "glm-5.3-flash"


def _git(path: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(path), *args], stderr=subprocess.DEVNULL)


def _workspace(tmp_path: Path) -> tuple[Path, Path]:
    primary = tmp_path / "primary"
    primary.mkdir()
    _git(primary, "init", "-b", "main")
    _git(primary, "config", "user.email", "test@example.invalid")
    _git(primary, "config", "user.name", "Test")
    (primary / "context.py").write_text("def build_context():\n    return {'valid': True}\n")
    _git(primary, "add", "context.py")
    _git(primary, "commit", "-m", "seed")
    linked = tmp_path / "linked"
    _git(primary, "worktree", "add", "-b", "task", str(linked))
    return primary, linked


@pytest.mark.parametrize(
    "target",
    [
        "primary",
        "primary_feature",
        "nested",
        "dirty",
        "staged",
        "untracked",
        "governed",
        "inherited_governance",
        "fake_lease",
        "symlink",
        "detached",
        "custom_default",
        "not_git",
    ],
)
def test_corrupting_executor_never_runs_in_unadmitted_workspace(monkeypatch, tmp_path, target):
    primary, linked = _workspace(tmp_path)
    project = linked
    if target in {"primary", "primary_feature", "nested"}:
        project = primary
        if target == "primary_feature":
            _git(primary, "checkout", "-b", "primary-feature")
        if target == "nested":
            project = primary / "src"
            project.mkdir()
    elif target in {"dirty", "staged"}:
        (linked / "context.py").write_text("# owner changes\n")
        if target == "staged":
            _git(linked, "add", "context.py")
    elif target == "untracked":
        (linked / "owner.txt").write_text("preserve me")
    elif target == "governed":
        (linked / ".governance").mkdir()
    elif target == "fake_lease":
        (linked / ".governance").mkdir()
        (linked / ".governance" / "manifest.json").write_text("{}")
        (linked / "lease.json").write_text('{"phase":"editing","ownerActor":"agent:codex","fencingToken":999}')
        _git(linked, "add", ".governance/manifest.json", "lease.json")
        _git(linked, "commit", "-m", "local claims cannot grant authority")
    elif target == "inherited_governance":
        (primary / ".governance").mkdir()
    elif target == "symlink":
        project = tmp_path / "alias"
        project.symlink_to(linked, target_is_directory=True)
    elif target == "detached":
        _git(linked, "checkout", "--detach")
    elif target == "custom_default":
        _git(linked, "branch", "-m", "trunk")
        _git(linked, "update-ref", "refs/remotes/origin/trunk", "HEAD")
        _git(linked, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
    elif target == "not_git":
        project = tmp_path / "plain"
        project.mkdir()
    before = [(p / "context.py").read_bytes() for p in (primary, linked)]
    indexes = [_git(p, "ls-files", "--stage") for p in (primary, linked)]
    calls = []

    def corrupt(**kwargs):
        calls.append(kwargs)
        (kwargs["project"] / "context.py").write_text("planfile ticket done PLF-031\n")
        (kwargs["project"] / "If you are using planfile").touch()
        return {"ok": True}

    monkeypatch.setattr("tillm.compat.drive_koru_chat", corrupt)
    result = bridge.drive_shell_chat(client_id="aider", project=project, prompt="refactor", execute=True)
    assert result["ok"] is False
    assert result["executed"] is False
    if target in {"governed", "inherited_governance", "fake_lease"}:
        assert "protected controller admission" in result["message"]
    assert result["diagnostic_code"] == "shell_workspace_not_admitted"
    assert calls == []
    assert [(p / "context.py").read_bytes() for p in (primary, linked)] == before
    assert [_git(p, "ls-files", "--stage") for p in (primary, linked)] == indexes
    assert not (project / "If you are using planfile").exists()


def test_preview_never_loads_or_invokes_vendor(monkeypatch, tmp_path):
    def unexpected():
        raise AssertionError("preview loaded vendor transport")

    monkeypatch.setattr(bridge, "ensure_local_tillm_path", unexpected)
    result = bridge.drive_shell_chat(client_id="aider", project=tmp_path, prompt="refactor", execute=False)
    assert result["dry_run"] is True
    assert result["executed"] is False


def test_linked_workspace_execution_leaves_primary_unchanged(monkeypatch, tmp_path):
    primary, linked = _workspace(tmp_path)
    original = (primary / "context.py").read_bytes()

    def edit(**kwargs):
        (kwargs["project"] / "context.py").write_text("def build_context():\n    return {}\n")
        return {"ok": True}

    monkeypatch.setattr("tillm.compat.drive_koru_chat", edit)
    result = bridge.drive_shell_chat(client_id="aider", project=linked, prompt="refactor", execute=True)
    assert result["ok"] is True
    assert (primary / "context.py").read_bytes() == original
    assert (linked / "context.py").read_bytes() != original


@pytest.mark.parametrize(
    "variable",
    [
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    ],
)
def test_git_environment_cannot_redirect_editor_to_primary(monkeypatch, tmp_path, variable):
    primary, linked = _workspace(tmp_path)
    monkeypatch.setenv(variable, str(primary))

    def unexpected(**kwargs):
        raise AssertionError("unsafe vendor execution")

    monkeypatch.setattr("tillm.compat.drive_koru_chat", unexpected)
    reply = bridge.drive_shell_chat(client_id="aider", project=linked, prompt="edit", execute=True)
    assert reply["diagnostic_code"] == "shell_workspace_not_admitted"
