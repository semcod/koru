"""Focused tests for autonomous duplicate process detection."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from koru import autonomous_processes as autonomous_processes_mod


def test_find_existing_autonomous_does_not_skip_sibling_from_same_shell(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A previous loop may share our shell/tmux ancestor as PPID."""
    project = tmp_path.resolve()
    command = (
        f"/venv/bin/python /repo/.venv/bin/koru autonomous up "
        f"--project {project} --autopilot-ide windsurf"
    )

    monkeypatch.setattr(autonomous_processes_mod.os, "getpid", lambda: 2000)
    monkeypatch.setattr(autonomous_processes_mod, "_ancestor_pids", lambda _pid: {100})
    monkeypatch.setattr(autonomous_processes_mod, "_process_cwd", lambda _pid: Path("/home/tom"))
    monkeypatch.setattr(
        autonomous_processes_mod.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=f"123 100 {command}\n2000 100 /repo/.venv/bin/koru autonomous up\n",
        ),
    )

    matches = autonomous_processes_mod._find_existing_autonomous_processes(project)

    assert [match.pid for match in matches] == [123]


def _guard_args(**overrides):
    base = {
        "allow_duplicate": False,
        "replace_existing": True,
        "replace_existing_global": False,
        "emit_events": "human",
        "wup_watch": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _wup_proc(project: Path):
    return autonomous_processes_mod.ExistingManagedProcess(
        pid=123,
        kind="wup-watch",
        command=f"/usr/bin/wup watch {project}",
        cwd=project,
    )


def test_replace_existing_skips_external_wup_when_no_wup_watch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """--no-wup-watch means wup runs externally — replace must not SIGTERM it."""
    project = tmp_path.resolve()
    terminated: list[list] = []

    monkeypatch.setattr(
        autonomous_processes_mod, "_find_existing_autonomous_processes",
        lambda _project, any_project=False: [],
    )
    monkeypatch.setattr(
        autonomous_processes_mod, "_find_existing_wup_processes",
        lambda _project: [_wup_proc(project)],
    )
    monkeypatch.setattr(
        autonomous_processes_mod, "_terminate_existing_processes",
        lambda procs, stdio_format: terminated.append(list(procs)),
    )

    rc = autonomous_processes_mod.guard_existing_autonomous_processes(
        _guard_args(wup_watch=False), project,
    )

    assert rc == 0
    assert terminated == []


def test_replace_existing_still_replaces_wup_when_managed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Default (auto) wup_watch keeps the old replace semantics."""
    project = tmp_path.resolve()
    terminated: list[list] = []

    monkeypatch.setattr(
        autonomous_processes_mod, "_find_existing_autonomous_processes",
        lambda _project, any_project=False: [],
    )
    monkeypatch.setattr(
        autonomous_processes_mod, "_find_existing_wup_processes",
        lambda _project: [_wup_proc(project)],
    )
    monkeypatch.setattr(
        autonomous_processes_mod, "_terminate_existing_processes",
        lambda procs, stdio_format: terminated.append(list(procs)),
    )

    rc = autonomous_processes_mod.guard_existing_autonomous_processes(
        _guard_args(wup_watch=None), project,
    )

    assert rc == 0
    assert len(terminated) == 1
    assert [proc.pid for proc in terminated[0]] == [123]


def test_find_existing_wup_processes_filters_project_and_excluded_pid(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path.resolve()
    matching = f"/usr/bin/wup watch --project {project}"
    foreign = "/usr/bin/wup watch --project /tmp/other"

    monkeypatch.setattr(autonomous_processes_mod.os, "getpid", lambda: 2000)
    monkeypatch.setattr(autonomous_processes_mod, "_ancestor_pids", lambda _pid: {100})
    monkeypatch.setattr(
        autonomous_processes_mod,
        "_process_cwd",
        lambda pid: project if pid == 123 else Path("/tmp/other"),
    )
    monkeypatch.setattr(
        autonomous_processes_mod.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=(
                f"123 77 {matching}\n"
                f"124 88 {foreign}\n"
                f"2000 100 /usr/bin/wup watch --project {project}\n"
            ),
        ),
    )

    matches = autonomous_processes_mod._find_existing_wup_processes(project)

    assert [match.pid for match in matches] == [123]
