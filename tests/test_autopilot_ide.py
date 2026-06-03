"""Tests for IDE process detection."""

from __future__ import annotations

from pathlib import Path

import pytest

@pytest.fixture(autouse=True)
def _clear_antigravity_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "GIO_LAUNCHED_DESKTOP_FILE",
        "VSCODE_CODE_CACHE_PATH",
        "VSCODE_IPC_HOOK",
        "VSCODE_NLS_CONFIG",
        "VSCODE_CWD",
        "CHROME_DESKTOP",
        "TERM_PROGRAM",
        "TERM_PROGRAM_VERSION",
        "CURSOR_CLI",
        "CURSOR_AGENT",
        "WINDSURF_VERSION",
        "WINDSURF_CSRF_TOKEN",
        "WINDSURF_CASCADE_TERMINAL",
        "TERMINAL_EMULATOR",
        "IDEA_INITIAL_DIRECTORY",
        "PYCHARM_HOSTED",
        "JETBRAINS_IDE",
    ):
        monkeypatch.delenv(key, raising=False)

from koru.autopilot import ide as ide_mod


@pytest.fixture
def fake_proc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a tiny ``/proc``-like tree under ``tmp_path`` with two PIDs."""

    def write_pid(pid: int, comm: str, cmdline: list[str]) -> None:
        d = tmp_path / str(pid)
        d.mkdir()
        (d / "comm").write_text(comm + "\n")
        (d / "cmdline").write_bytes(b"\x00".join(c.encode() for c in cmdline) + b"\x00")

    write_pid(1234, "windsurf", ["/opt/windsurf/windsurf", "--type=renderer"])
    write_pid(5678, "java", ["/usr/lib/jvm/java/bin/java", "-jar", "/opt/idea/lib/idea.jar"])
    write_pid(9999, "bash", ["bash"])  # noise — must not match any IDE

    def fake_read_comm(pid: int) -> str:
        path = tmp_path / str(pid) / "comm"
        if not path.is_file():
            return ""
        return path.read_text().strip()

    def fake_read_cmdline(pid: int) -> str:
        path = tmp_path / str(pid) / "cmdline"
        if not path.is_file():
            return ""
        raw = path.read_bytes()
        return raw.replace(b"\x00", b" ").decode().strip()

    monkeypatch.setattr(ide_mod, "_read_comm", fake_read_comm)
    monkeypatch.setattr(ide_mod, "_read_cmdline", fake_read_cmdline)
    monkeypatch.setattr(ide_mod, "_active_window_pid_x11", lambda: None)
    monkeypatch.setattr(ide_mod, "detect_terminal_host_ide_id", lambda: None)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    return tmp_path


def test_detect_running_ides_finds_windsurf_and_jetbrains(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678, 9999])
    ids = [d.id for d in detected]
    assert "windsurf" in ids
    assert "jetbrains" in ids
    assert "vscode" not in ids


def test_detect_running_ides_deduplicates_same_ide(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 1234])
    assert sum(1 for d in detected if d.id == "windsurf") == 1


def test_detect_running_ides_prefers_primary_windsurf_over_devin_helper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for pid, comm, cmd in [
        (1111, "devin", ["/usr/share/windsurf/resources/app/extensions/windsurf/devin/bin/devin"]),
        (2222, "windsurf", ["/usr/share/windsurf/windsurf", "--type=browser"]),
    ]:
        d = tmp_path / str(pid)
        d.mkdir()
        (d / "comm").write_text(comm + "\n")
        (d / "cmdline").write_bytes(b"\x00".join(c.encode() for c in cmd) + b"\x00")

    monkeypatch.setattr(
        ide_mod,
        "_read_comm",
        lambda pid: (tmp_path / str(pid) / "comm").read_text().strip(),
    )
    monkeypatch.setattr(
        ide_mod,
        "_read_cmdline",
        lambda pid: (
            (tmp_path / str(pid) / "cmdline").read_bytes().replace(b"\x00", b" ").decode().strip()
        ),
    )
    monkeypatch.setattr(
        ide_mod,
        "_read_exe",
        lambda pid: (
            "/usr/share/windsurf/resources/app/extensions/windsurf/devin/bin/devin"
            if pid == 1111
            else "/usr/share/windsurf/windsurf"
        ),
    )
    detected = ide_mod.detect_running_ides(_pids=[1111, 2222])
    ws = next(d for d in detected if d.id == "windsurf")
    assert ws.pid == 2222
    assert ws.exe.endswith("/windsurf")


def test_detect_running_ides_skips_unknown_processes(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[9999])
    assert detected == []


def test_detect_running_ides_separates_vscode_and_vscodium(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = {
        111: ("code", ["/snap/code/current/usr/share/code/code", "--type=browser"]),
        222: ("codium", ["/snap/codium/current/usr/share/codium/codium", "--type=browser"]),
    }
    for pid, (comm, cmd) in rows.items():
        d = tmp_path / str(pid)
        d.mkdir()
        (d / "comm").write_text(comm + "\n")
        (d / "cmdline").write_bytes(b"\x00".join(c.encode() for c in cmd) + b"\x00")

    monkeypatch.setattr(
        ide_mod,
        "_read_comm",
        lambda pid: (tmp_path / str(pid) / "comm").read_text().strip(),
    )
    monkeypatch.setattr(
        ide_mod,
        "_read_cmdline",
        lambda pid: (
            (tmp_path / str(pid) / "cmdline").read_bytes().replace(b"\x00", b" ").decode().strip()
        ),
    )
    monkeypatch.setattr(ide_mod, "_read_exe", lambda pid: rows[pid][1][0])

    detected = ide_mod.detect_running_ides(_pids=[111, 222])
    assert [row.id for row in detected if row.id in {"vscode", "vscodium"}] == [
        "vscode",
        "vscodium",
    ]


def test_detect_running_ides_finds_antigravity_as_separate_ide(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = {
        111: ("antigravity", ["/usr/share/antigravity/antigravity", "--type=browser"]),
        222: ("code", ["/snap/code/current/usr/share/code/code", "--type=browser"]),
    }
    for pid, (comm, cmd) in rows.items():
        d = tmp_path / str(pid)
        d.mkdir()
        (d / "comm").write_text(comm + "\n")
        (d / "cmdline").write_bytes(b"\x00".join(c.encode() for c in cmd) + b"\x00")

    monkeypatch.setattr(
        ide_mod,
        "_read_comm",
        lambda pid: (tmp_path / str(pid) / "comm").read_text().strip(),
    )
    monkeypatch.setattr(
        ide_mod,
        "_read_cmdline",
        lambda pid: (
            (tmp_path / str(pid) / "cmdline").read_bytes().replace(b"\x00", b" ").decode().strip()
        ),
    )
    monkeypatch.setattr(ide_mod, "_read_exe", lambda pid: rows[pid][1][0])

    detected = ide_mod.detect_running_ides(_pids=[111, 222])
    assert [row.id for row in detected if row.id in {"antigravity", "vscode"}] == [
        "antigravity",
        "vscode",
    ]


def test_pick_target_prefers_user_choice(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678])
    chosen = ide_mod.pick_target(detected, prefer="jetbrains")
    assert chosen is not None
    assert chosen.id == "jetbrains"


def test_pick_target_returns_none_when_pref_not_running(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234])
    chosen = ide_mod.pick_target(detected, prefer="vscode")
    assert chosen is None


def test_pick_target_defaults_to_first(
    fake_proc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setattr(ide_mod, "detect_terminal_host_ide_id", lambda **_k: None)
    monkeypatch.setattr(ide_mod, "detect_focused_ide_id", lambda **_k: None)
    detected = ide_mod.detect_running_ides(_pids=[5678, 1234])
    chosen = ide_mod.pick_target(detected)
    # windsurf comes first in declared order, regardless of pid order.
    assert chosen is not None
    assert chosen.id == "windsurf"


def test_pick_target_prefers_koru_autopilot_ide_env(
    fake_proc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "jetbrains")
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678])
    chosen = ide_mod.pick_target(detected)
    assert chosen is not None
    assert chosen.id == "jetbrains"


def test_pick_target_ignores_koru_autopilot_ide_env_when_not_running(
    fake_proc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "cursor")
    monkeypatch.setattr(ide_mod, "detect_terminal_host_ide_id", lambda **_k: None)
    monkeypatch.setattr(ide_mod, "detect_focused_ide_id", lambda **_k: None)
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678])
    chosen = ide_mod.pick_target(detected)
    assert chosen is not None
    assert chosen.id == "windsurf"


def test_pick_target_empty_list_returns_none() -> None:
    assert ide_mod.pick_target([]) is None


# ---- R13: focused-window arbitration ----


def test_detect_focused_ide_id_from_active_pid(fake_proc: Path) -> None:
    # PID 5678 is our fake JetBrains java process in the fixture.
    assert ide_mod.detect_focused_ide_id(_active_pid=5678) == "jetbrains"


def test_detect_focused_ide_id_returns_none_for_unknown_pid(fake_proc: Path) -> None:
    assert ide_mod.detect_focused_ide_id(_active_pid=9999) is None


def test_focused_ide_returns_matching_instance(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678])
    focused = ide_mod.focused_ide(detected, focused_id="jetbrains")
    assert focused is not None
    assert focused.id == "jetbrains"


def test_pick_target_prefers_focused_when_no_explicit_prefer(
    fake_proc: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678])
    chosen = ide_mod.pick_target(detected, focused_id="jetbrains")
    assert chosen is not None
    assert chosen.id == "jetbrains"


def test_pick_target_explicit_prefer_beats_focus(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678])
    chosen = ide_mod.pick_target(detected, prefer="windsurf", focused_id="jetbrains")
    assert chosen is not None
    assert chosen.id == "windsurf"


def test_resolve_drive_target_auto_picks_first_ide_with_profile(
    fake_proc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678, 9999])
    monkeypatch.setattr(ide_mod, "detect_running_ides", lambda: detected)
    profiles = {"windsurf"}

    def has_profile(tool_id: str, project) -> bool:
        return tool_id in profiles

    kb, profile, reason = ide_mod.resolve_drive_target(
        "auto",
        None,
        has_profile=has_profile,
    )
    assert kb == "windsurf"
    assert profile == "windsurf"
    assert reason in ("auto:profile", "auto:running-profile")


def test_detect_terminal_host_ide_id_cursor_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WINDSURF_CSRF_TOKEN", raising=False)
    monkeypatch.setenv("CHROME_DESKTOP", "cursor.desktop")
    monkeypatch.setenv("VSCODE_PID", "201464")
    monkeypatch.setenv("VSCODE_CODE_CACHE_PATH", "/home/tom/.config/Cursor/CachedData/x")
    assert ide_mod.detect_terminal_host_ide_id() == "cursor"


def test_detect_terminal_host_ide_id_cursor_beats_windsurf_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHROME_DESKTOP", "cursor.desktop")
    monkeypatch.setenv("WINDSURF_CSRF_TOKEN", "deadbeef")
    monkeypatch.setenv("VSCODE_PID", "1")
    assert ide_mod.detect_terminal_host_ide_id() == "cursor"


def test_detect_terminal_host_ide_id_vscode_nls_without_pid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "CURSOR_AGENT",
        "CURSOR_CLI",
        "CHROME_DESKTOP",
        "VSCODE_PID",
        "VSCODE_CODE_CACHE_PATH",
        "VSCODE_IPC_HOOK",
        "WINDSURF_VERSION",
        "WINDSURF_CSRF_TOKEN",
        "TERM_PROGRAM_VERSION",
        "WINDSURF_CASCADE_TERMINAL",
        "GIO_LAUNCHED_DESKTOP_FILE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("VSCODE_NLS_CONFIG", "{}")
    assert ide_mod.detect_terminal_host_ide_id() == "vscode"


def test_detect_terminal_host_ide_id_vscodium_from_vscode_family_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "CURSOR_AGENT",
        "CURSOR_CLI",
        "CHROME_DESKTOP",
        "WINDSURF_VERSION",
        "WINDSURF_CSRF_TOKEN",
        "TERM_PROGRAM_VERSION",
        "WINDSURF_CASCADE_TERMINAL",
        "GIO_LAUNCHED_DESKTOP_FILE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("VSCODE_PID", "123")
    monkeypatch.setenv("VSCODE_NLS_CONFIG", "/snap/codium/current/resources/app")

    assert ide_mod.detect_terminal_host_ide_id() == "vscodium"


def test_detect_terminal_host_ide_id_antigravity_from_vscode_family_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "CURSOR_AGENT",
        "CURSOR_CLI",
        "CHROME_DESKTOP",
        "WINDSURF_VERSION",
        "WINDSURF_CSRF_TOKEN",
        "TERM_PROGRAM_VERSION",
        "WINDSURF_CASCADE_TERMINAL",
        "GIO_LAUNCHED_DESKTOP_FILE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("VSCODE_PID", "123")
    monkeypatch.setenv("VSCODE_NLS_CONFIG", "/usr/share/antigravity/resources/app")

    assert ide_mod.detect_terminal_host_ide_id() == "antigravity"


def test_detect_terminal_host_ide_id_zed_term_program(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "CURSOR_AGENT",
        "CURSOR_CLI",
        "CHROME_DESKTOP",
        "VSCODE_PID",
        "VSCODE_CODE_CACHE_PATH",
        "VSCODE_IPC_HOOK",
        "WINDSURF_VERSION",
        "WINDSURF_CSRF_TOKEN",
        "TERM_PROGRAM_VERSION",
        "WINDSURF_CASCADE_TERMINAL",
        "GIO_LAUNCHED_DESKTOP_FILE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TERM_PROGRAM", "zed")

    assert ide_mod.detect_terminal_host_ide_id() == "zed"


def test_detect_terminal_host_context_vscode_pid_beats_cursor_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("VSCODE_PID", "123")
    monkeypatch.setenv("CURSOR_AGENT", "1")
    monkeypatch.setenv("CHROME_DESKTOP", "cursor.desktop")
    monkeypatch.setattr(ide_mod, "_ide_from_vscode_pid", lambda: "vscode")

    ctx = ide_mod.detect_terminal_host_context()
    assert ctx.ide == "vscode"
    assert ctx.source == "env:VSCODE_PID.exe"
    assert ctx.kind == "integrated"
    assert ctx.integrated is True


def test_detect_terminal_host_context_system_shell_when_no_markers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "CURSOR_AGENT",
        "CURSOR_CLI",
        "CHROME_DESKTOP",
        "TERM_PROGRAM",
        "TERM_PROGRAM_VERSION",
        "VSCODE_PID",
        "VSCODE_NLS_CONFIG",
        "VSCODE_IPC_HOOK",
        "VSCODE_CODE_CACHE_PATH",
        "VSCODE_CWD",
        "WINDSURF_CASCADE_TERMINAL",
        "WINDSURF_VERSION",
        "WINDSURF_CSRF_TOKEN",
        "GIO_LAUNCHED_DESKTOP_FILE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(ide_mod, "_terminal_ide_from_parent_chain", lambda _pid: None)

    ctx = ide_mod.detect_terminal_host_context(_start_pid=999)
    assert ctx.ide is None
    assert ctx.source == "none"
    assert ctx.kind == "system"
    assert ctx.integrated is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("codium", "vscodium"),
        ("antigravity", "antigravity"),
        ("google-antigravity.desktop", "antigravity"),
        ("code-oss.desktop", "vscodium"),
        ("pycharm", "jetbrains"),
        ("zed-editor", "zed"),
    ],
)
def test_normalize_ide_id_aliases(raw: str, expected: str) -> None:
    assert ide_mod.normalize_ide_id(raw) == expected


def test_detect_terminal_host_context_parent_chain_is_ide_adjacent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "CURSOR_AGENT",
        "CURSOR_CLI",
        "CHROME_DESKTOP",
        "TERM_PROGRAM",
        "VSCODE_PID",
        "VSCODE_NLS_CONFIG",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(ide_mod, "_terminal_ide_from_parent_chain", lambda _pid: "vscodium")

    ctx = ide_mod.detect_terminal_host_context(_start_pid=999)

    assert ctx.ide == "vscodium"
    assert ctx.kind == "ide_adjacent"
    assert ctx.integrated is False
    assert "parent_chain" in ctx.source


def test_terminal_host_prefers_vscodium_flavor_over_generic_vscode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv(
        "VSCODE_NLS_CONFIG",
        '{"defaultMessagesFile":"/snap/codium/current/usr/share/codium/resources/app/out/nls.messages.json"}',
    )
    monkeypatch.delenv("VSCODE_PID", raising=False)
    monkeypatch.delenv("CHROME_DESKTOP", raising=False)
    monkeypatch.setattr(ide_mod, "_terminal_ide_from_parent_chain", lambda _pid: None)

    ctx = ide_mod.detect_terminal_host_context(_start_pid=999)

    assert ctx.ide == "vscodium"
    assert ctx.source == "env:VSCODE_*"
    assert ctx.kind == "integrated"
    assert ctx.integrated is True


def test_pick_target_prefers_terminal_host_over_signature_order(
    fake_proc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678])
    monkeypatch.setattr(ide_mod, "detect_terminal_host_ide_id", lambda **_k: "jetbrains")
    chosen = ide_mod.pick_target(detected)
    assert chosen is not None
    assert chosen.id == "jetbrains"


def test_resolve_drive_target_terminal_without_profile_skips_other_profiles(
    fake_proc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678, 9999])
    detected = [
        *detected,
        ide_mod.RunningIDE(id="cursor", label="Cursor", pid=42, exe="/opt/cursor"),
    ]
    monkeypatch.setattr(ide_mod, "detect_running_ides", lambda: detected)
    monkeypatch.setattr(ide_mod, "detect_terminal_host_ide_id", lambda **_k: "cursor")
    profiles = {"windsurf"}

    def has_profile(tool_id: str, project) -> bool:
        return tool_id in profiles

    kb, profile, reason = ide_mod.resolve_drive_target(
        "auto",
        None,
        has_profile=has_profile,
    )
    assert kb == "cursor"
    assert profile == "cursor"
    assert reason == "auto:terminal-no-profile"


def test_resolve_drive_target_auto_prefers_focused_when_it_has_profile(
    fake_proc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678, 9999])
    monkeypatch.setattr(ide_mod, "detect_running_ides", lambda: detected)
    profiles = {"jetbrains"}

    def has_profile(tool_id: str, project) -> bool:
        return tool_id in profiles

    monkeypatch.setattr(ide_mod, "detect_focused_ide_id", lambda: "jetbrains")
    kb, profile, reason = ide_mod.resolve_drive_target(
        "auto",
        None,
        has_profile=has_profile,
    )
    assert profile == "jetbrains"
    assert reason == "auto:focused-profile"


def test_resolve_drive_target_explicit_zed_without_running_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ide_mod, "detect_running_ides", lambda: [])

    kb, profile, reason = ide_mod.resolve_drive_target("zed", None)

    assert kb == "zed"
    assert profile == "zed"
    assert reason == "explicit-missing:zed"


# ---- R5: detect_running_ides_cached ----


def test_detect_cached_uses_cache_within_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Second call within ``ttl`` must NOT trigger a fresh ``/proc`` scan."""
    ide_mod.clear_detect_cache()
    calls: list[None] = []

    def fake_detect(*, _pids: list[int] | None = None) -> list:
        calls.append(None)
        return []

    monkeypatch.setattr(ide_mod, "detect_running_ides", fake_detect)
    ide_mod.detect_running_ides_cached(ttl=10.0)
    ide_mod.detect_running_ides_cached(ttl=10.0)
    ide_mod.detect_running_ides_cached(ttl=10.0)
    assert len(calls) == 1


def test_detect_cached_ttl_zero_always_refreshes(monkeypatch: pytest.MonkeyPatch) -> None:
    ide_mod.clear_detect_cache()
    calls: list[None] = []
    monkeypatch.setattr(
        ide_mod,
        "detect_running_ides",
        lambda **_: calls.append(None) or [],
    )
    ide_mod.detect_running_ides_cached(ttl=0)
    ide_mod.detect_running_ides_cached(ttl=0)
    assert len(calls) == 2


def test_clear_detect_cache_forces_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    ide_mod.clear_detect_cache()
    calls: list[None] = []
    monkeypatch.setattr(
        ide_mod,
        "detect_running_ides",
        lambda **_: calls.append(None) or [],
    )
    ide_mod.detect_running_ides_cached(ttl=10.0)
    ide_mod.clear_detect_cache()
    ide_mod.detect_running_ides_cached(ttl=10.0)
    assert len(calls) == 2
