"""Extra coverage for IDE detection, project proposal, and install flow."""

from __future__ import annotations

import io
from pathlib import Path

from koru.wizard import cli as wizard_cli
from koru.wizard import ide as wiz_ide
from koru.wizard import ide_install as wiz_ide_install
from koru.wizard import project as wiz_project
from koru.wizard.cli import (
    _IDE_INSTALL_CATALOG,
    _IDE_INSTALL_ORDER,
    _MANAGER_BINARIES,
    ScriptedPrompter,
    StdinPrompter,
)
from koru.wizard.ide_install import (
    _available_install_managers,
    _build_install_method_options,
    _format_command,
    _run_install_command,
    offer_ide_install as _offer_ide_install,
)
from koru.wizard.ide import DetectedIDE, _merge_running, _scan_installed, discover_installed_ides
from koru.wizard.project import (
    ProjectCandidate,
    _candidates_from_running_ide,
    _dedup,
    _extract_workspace_from_cmdline,
    _is_project_root,
    _walk_up_to_root,
    propose_projects,
)


def test_scan_installed_picks_primary_and_extras(tmp_path: Path) -> None:
    main = tmp_path / "bin" / "code"
    extra = tmp_path / "snap" / "code"
    main.parent.mkdir(parents=True)
    extra.parent.mkdir(parents=True)
    main.touch()
    extra.touch()

    hints = {"vscode": ("VS Code", (str(main), str(extra)))}
    result = _scan_installed(hint_map=hints)
    assert len(result) == 1
    only = result[0]
    assert only.id == "vscode"
    assert only.path == str(main)
    assert only.extras == (str(extra),)
    assert only.running is False


def test_scan_installed_falls_back_to_shutil_which(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(wiz_ide.shutil, "which", lambda name: str(tmp_path / name))
    hints = {"vscode": ("VS Code", ("/nope/code",))}
    fake_target = tmp_path / "vscode"
    fake_target.touch()
    result = _scan_installed(hint_map=hints)
    assert len(result) == 1
    assert result[0].path.endswith("vscode")


def test_scan_installed_returns_empty_for_unknown_paths() -> None:
    hints = {"none": ("Nothing", ("/definitely/does/not/exist",))}
    assert _scan_installed(hint_map=hints) == []


def test_merge_running_promotes_installed_entry() -> None:
    from koruide.ide import RunningIDE

    installed = [
        DetectedIDE(id="vscode", label="VS Code", running=False, pid=None, path="/usr/bin/code")
    ]
    running = [RunningIDE(id="vscode", label="VS Code", pid=42, exe="/snap/bin/code")]
    merged = _merge_running(installed, running)
    assert len(merged) == 1
    assert merged[0].running is True
    assert merged[0].pid == 42
    assert merged[0].path == "/snap/bin/code"


def test_merge_running_inserts_pure_runtime_entry() -> None:
    from koruide.ide import RunningIDE

    running = [RunningIDE(id="zed", label="Zed", pid=7, exe="/opt/zed/zed")]
    merged = _merge_running([], running)
    assert len(merged) == 1
    assert merged[0].id == "zed"
    assert merged[0].running is True


def test_discover_uses_overrides(monkeypatch) -> None:
    monkeypatch.setattr(wiz_ide, "detect_running_ides", lambda: [])
    ides = discover_installed_ides(hint_map={}, running_override=[])
    assert ides == []


def test_extract_workspace_from_cmdline_picks_last_existing_path(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    cmdline = f"/usr/bin/code --user-data-dir=/tmp/foo /not/real {workspace} --extra"
    result = _extract_workspace_from_cmdline(cmdline)
    assert result == workspace


def test_extract_workspace_returns_none_when_no_path_exists() -> None:
    assert _extract_workspace_from_cmdline("/usr/bin/code --no-folder") is None
    assert _extract_workspace_from_cmdline("") is None


def test_is_project_root_recognises_common_markers(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    assert _is_project_root(project) is False
    (project / "pyproject.toml").touch()
    assert _is_project_root(project) is True

    other = tmp_path / "other"
    other.mkdir()
    (other / ".git").mkdir()
    assert _is_project_root(other) is True


def test_walk_up_to_root_finds_parent_with_marker(tmp_path: Path) -> None:
    root = tmp_path / "root"
    deep = root / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (root / "package.json").touch()
    assert _walk_up_to_root(deep) == root


def test_walk_up_to_root_returns_start_when_no_marker(tmp_path: Path) -> None:
    deep = tmp_path / "lonely"
    deep.mkdir()
    assert _walk_up_to_root(deep) == deep


def test_dedup_preserves_order_drops_duplicates(tmp_path: Path) -> None:
    a = ProjectCandidate(path=tmp_path / "a", source="x")
    b = ProjectCandidate(path=tmp_path / "b", source="y")
    a2 = ProjectCandidate(path=tmp_path / "a", source="z")
    result = _dedup([a, b, a2])
    assert [c.path for c in result] == [a.path, b.path]


def test_candidates_from_running_ide_returns_empty_for_not_running(tmp_path: Path) -> None:
    ide = DetectedIDE(id="vscode", label="VS Code", running=False, pid=None, path="/x")
    assert _candidates_from_running_ide(ide) == []


def test_candidates_from_running_ide_combines_workspace_and_cwd(
    monkeypatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.setattr(wiz_project, "_read_proc_cmdline", lambda _pid: f"code {workspace}")
    monkeypatch.setattr(wiz_project, "_read_proc_cwd", lambda _pid: cwd)
    ide = DetectedIDE(id="vscode", label="VS Code", running=True, pid=1, path="/x")
    result = _candidates_from_running_ide(ide)
    assert [c.path for c in result] == [workspace.resolve(), cwd.resolve()]
    assert "workspace" in result[0].source
    assert "cwd" in result[1].source


def test_candidates_from_running_ide_skips_duplicate_cwd(monkeypatch, tmp_path: Path) -> None:
    same = tmp_path / "same"
    same.mkdir()
    monkeypatch.setattr(wiz_project, "_read_proc_cmdline", lambda _pid: f"code {same}")
    monkeypatch.setattr(wiz_project, "_read_proc_cwd", lambda _pid: same)
    ide = DetectedIDE(id="vscode", label="VS Code", running=True, pid=1, path="/x")
    result = _candidates_from_running_ide(ide)
    assert len(result) == 1


def test_propose_projects_combines_ides_cwd_and_jetbrains(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setattr(wiz_project, "_read_proc_cmdline", lambda _pid: f"code {workspace}")
    monkeypatch.setattr(wiz_project, "_read_proc_cwd", lambda _pid: None)
    monkeypatch.setattr(
        wiz_project,
        "_shell_cwd_candidate",
        lambda: ProjectCandidate(path=tmp_path, source="shell cwd"),
    )
    monkeypatch.setattr(wiz_project, "_recent_jetbrains_projects", lambda: [])
    ide = DetectedIDE(id="vscode", label="VS Code", running=True, pid=1, path="/x")
    result = propose_projects([ide])
    paths = [str(c.path) for c in result]
    assert str(workspace.resolve()) in paths
    assert str(tmp_path) in paths


def test_propose_projects_respects_max_results(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        wiz_project,
        "_shell_cwd_candidate",
        lambda: ProjectCandidate(path=tmp_path, source="shell cwd"),
    )
    monkeypatch.setattr(wiz_project, "_recent_jetbrains_projects", lambda: [])
    result = propose_projects([], max_results=0)
    assert result == []


def test_format_command_quotes_args_with_spaces() -> None:
    assert _format_command(("sudo", "apt-get", "install", "-y", "code")) == (
        "sudo apt-get install -y code"
    )
    assert _format_command(("echo", "with space")) == "echo 'with space'"


def test_install_catalog_has_entries_for_known_ides() -> None:
    for ide_id in ("vscode", "vscodium", "zed", "jetbrains", "cursor", "windsurf", "antigravity"):
        assert ide_id in _IDE_INSTALL_CATALOG, ide_id
    assert tuple(_IDE_INSTALL_ORDER)
    assert set(_IDE_INSTALL_ORDER) <= set(_IDE_INSTALL_CATALOG)


def test_available_install_managers_uses_path(monkeypatch) -> None:
    monkeypatch.setattr(
        wiz_ide_install.shutil,
        "which",
        lambda name: "/usr/bin/" + name if name in ("snap", "apt-get") else None,
    )
    assert _available_install_managers() == {"snap", "apt"}


def test_build_install_method_options_filters_by_manager() -> None:
    spec = _IDE_INSTALL_CATALOG["vscode"]
    options, commands = _build_install_method_options(spec, {"snap"})
    ids = [o.id for o in options]
    assert "install_snap" in ids
    assert "install_apt" not in ids
    assert "open_web" in ids
    assert "cancel" in ids
    assert commands["install_snap"][0] == "sudo"


def test_build_install_method_options_always_appends_web_and_cancel() -> None:
    spec = _IDE_INSTALL_CATALOG["cursor"]  # no manager commands at all
    options, commands = _build_install_method_options(spec, set())
    ids = [o.id for o in options]
    assert ids == ["open_web", "cancel"]
    assert commands == {}


def test_offer_ide_install_runs_command_and_rediscovers(monkeypatch) -> None:
    monkeypatch.setattr(wiz_ide_install, "_available_install_managers", lambda: {"snap"})
    executed: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        wiz_ide_install,
        "_run_install_command",
        lambda argv, _out: executed.append(argv) or True,
    )

    expected_post_install = [
        DetectedIDE(id="vscode", label="VS Code", running=False, pid=None, path="/usr/bin/code"),
    ]
    monkeypatch.setattr(wiz_ide_install, "discover_installed_ides", lambda: expected_post_install)

    prompter = ScriptedPrompter(
        ["install_vscode", "install_snap"],
        yes_no_answers=[True],
    )
    out = io.StringIO()
    result = _offer_ide_install(prompter, out)
    assert result == expected_post_install
    assert executed and "snap" in executed[0]


def test_offer_ide_install_handles_open_web_choice(monkeypatch) -> None:
    monkeypatch.setattr(wiz_ide_install, "_available_install_managers", lambda: set())
    monkeypatch.setattr(wiz_ide_install, "discover_installed_ides", lambda: [])
    opened: list[str] = []
    monkeypatch.setattr(
        wiz_ide_install, "_open_download_page", lambda url, _out: opened.append(url)
    )
    prompter = ScriptedPrompter(["install_cursor", "open_web"])
    result = _offer_ide_install(prompter, io.StringIO())
    assert result == []
    assert opened == [_IDE_INSTALL_CATALOG["cursor"].homepage]


def test_offer_ide_install_cancel_branch_returns_empty(monkeypatch) -> None:
    monkeypatch.setattr(wiz_ide_install, "_available_install_managers", lambda: set())
    monkeypatch.setattr(wiz_ide_install, "discover_installed_ides", lambda: [])
    prompter = ScriptedPrompter(["install_cursor", "cancel"])
    assert _offer_ide_install(prompter, io.StringIO()) == []


def test_offer_ide_install_user_skips_returns_empty() -> None:
    prompter = ScriptedPrompter(["__none"])
    assert _offer_ide_install(prompter, io.StringIO()) == []


def test_offer_ide_install_user_declines_to_run_command(monkeypatch) -> None:
    monkeypatch.setattr(wiz_ide_install, "_available_install_managers", lambda: {"snap"})
    monkeypatch.setattr(wiz_ide_install, "discover_installed_ides", lambda: [])
    run_called: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        wiz_ide_install,
        "_run_install_command",
        lambda argv, _out: run_called.append(argv) or True,
    )
    prompter = ScriptedPrompter(
        ["install_vscode", "install_snap"],
        yes_no_answers=[False],
    )
    out = io.StringIO()
    _offer_ide_install(prompter, out)
    assert run_called == []
    assert "can run this command manually" in out.getvalue()


def test_run_install_command_drops_sudo_when_unavailable(monkeypatch) -> None:
    captured_argv: list[list[str]] = []

    class _Proc:
        returncode = 0

    def fake_run(argv, check=False):  # noqa: ANN001
        captured_argv.append(list(argv))
        return _Proc()

    monkeypatch.setattr(wiz_ide_install.subprocess, "run", fake_run)
    monkeypatch.setattr(wiz_ide_install.shutil, "which", lambda _name: None)
    out = io.StringIO()
    ok = _run_install_command(("sudo", "apt-get", "install", "code"), out)
    assert ok is True
    assert captured_argv == [["apt-get", "install", "code"]]
    assert "sudo not found" in out.getvalue()


def test_run_install_command_returns_false_on_oserror(monkeypatch) -> None:
    def _explode(*_a, **_k):  # noqa: ANN002, ANN003
        raise OSError("boom")

    monkeypatch.setattr(wiz_ide_install.subprocess, "run", _explode)
    out = io.StringIO()
    assert _run_install_command(("apt-get", "install", "code"), out) is False
    assert "failed to start" in out.getvalue()


def test_stdin_prompter_yes_no_defaults() -> None:
    p = StdinPrompter(stream_in=io.StringIO("\n"), stream_out=io.StringIO())
    assert p.ask_yes_no("OK?", default=True) is True
    p = StdinPrompter(stream_in=io.StringIO("\n"), stream_out=io.StringIO())
    assert p.ask_yes_no("OK?", default=False) is False


def test_stdin_prompter_yes_no_accepts_localised_answers() -> None:
    for answer, expected in (("tak\n", True), ("nie\n", False), ("y\n", True), ("n\n", False)):
        p = StdinPrompter(stream_in=io.StringIO(answer), stream_out=io.StringIO())
        assert p.ask_yes_no("OK?", default=False) is expected


def test_stdin_prompter_yes_no_rejects_garbage_then_accepts() -> None:
    out = io.StringIO()
    p = StdinPrompter(stream_in=io.StringIO("maybe\ny\n"), stream_out=out)
    assert p.ask_yes_no("OK?", default=False) is True
    assert "answer with y/n" in out.getvalue()


def test_scripted_prompter_yes_no_uses_queue() -> None:
    p = ScriptedPrompter([], yes_no_answers=[True, False])
    assert p.ask_yes_no("?", default=False) is True
    assert p.ask_yes_no("?", default=True) is False
    assert p.ask_yes_no("?", default=True) is True  # falls back to default when empty


def test_manager_binaries_are_sane() -> None:
    """Ensure every manager has an associated binary name."""
    for key in ("apt", "dnf", "pacman", "zypper", "snap", "flatpak"):
        assert _MANAGER_BINARIES[key]
