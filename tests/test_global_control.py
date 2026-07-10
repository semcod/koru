"""Tests for the machine-wide koru kill-switch (`koru on|off|status`)."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from koru.cli_global_control import off_main, on_main, status_main
from koru.global_control import (
    KILLSWITCH_DIR_ENV,
    KILLSWITCH_ENV,
    disabled_message,
    global_control_dir,
    global_disable,
    global_enable,
    is_globally_disabled,
    killswitch_path,
    read_killswitch_state,
)


@pytest.fixture(autouse=True)
def _isolated_control_dir(tmp_path, monkeypatch):
    """Point the kill-switch at a temp dir and never at the real user config."""
    monkeypatch.setenv(KILLSWITCH_DIR_ENV, str(tmp_path / "koru-ctl"))
    monkeypatch.delenv(KILLSWITCH_ENV, raising=False)
    # Never let a test spawn a real agent shell client.
    monkeypatch.setenv("KORU_AUTO_SHELL_CLIENT", "0")
    yield


@pytest.fixture(autouse=True)
def _no_systemctl(monkeypatch):
    """Keep tests hermetic: never call the real systemctl."""
    import koru.cli_global_control as mod

    monkeypatch.setattr(mod, "_systemctl_user", lambda *a: None)
    yield


def test_control_dir_honors_env_override(tmp_path):
    assert global_control_dir() == tmp_path / "koru-ctl"
    assert killswitch_path() == tmp_path / "koru-ctl" / "killswitch"


def test_disable_enable_roundtrip():
    assert not is_globally_disabled()
    path = global_disable("test reason")
    assert path.exists()
    assert is_globally_disabled()
    state = read_killswitch_state()
    assert state["reason"] == "test reason"
    assert state["disabled_at"]
    assert global_enable()
    assert not is_globally_disabled()
    assert not global_enable()  # second enable is a no-op


def test_env_variable_disables_without_marker(monkeypatch):
    assert not is_globally_disabled()
    monkeypatch.setenv(KILLSWITCH_ENV, "1")
    assert is_globally_disabled()
    monkeypatch.setenv(KILLSWITCH_ENV, "0")
    assert not is_globally_disabled()


def test_disabled_message_mentions_reason_and_recovery():
    global_disable("maintenance window")
    message = disabled_message("autonomous")
    assert "koru autonomous" in message
    assert "maintenance window" in message
    assert "koru on" in message


def test_off_on_status_cli_roundtrip(capsys):
    assert off_main(["--reason", "cli test"]) == 0
    assert is_globally_disabled()
    out = capsys.readouterr().out
    assert "kill-switch set" in out

    assert status_main([]) == 0
    out = capsys.readouterr().out
    assert "DISABLED" in out
    assert "cli test" in out

    assert on_main([]) == 0
    assert not is_globally_disabled()
    capsys.readouterr()

    assert status_main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["disabled"] is False


def test_on_warns_when_env_override_still_active(monkeypatch, capsys):
    global_disable("x")
    monkeypatch.setenv(KILLSWITCH_ENV, "1")
    assert on_main([]) == 1
    err = capsys.readouterr().err
    assert KILLSWITCH_ENV in err


def test_cli_dispatch_blocks_agent_subcommands(monkeypatch, capsys):
    import koru.cli as cli

    global_disable("blocked in test")
    called = {"n": 0}
    monkeypatch.setitem(cli._SUBCOMMANDS, "autonomous", lambda argv: called.__setitem__("n", 1) or 0)
    monkeypatch.setattr(sys, "argv", ["koru", "autonomous", "up"])
    rc = cli.main()
    assert rc == 3
    assert called["n"] == 0
    assert "globally disabled" in capsys.readouterr().err


def test_cli_dispatch_allows_status_and_on_when_disabled(monkeypatch, capsys):
    import koru.cli as cli

    global_disable("blocked in test")
    monkeypatch.setattr(sys, "argv", ["koru", "status"])
    assert cli.main() == 0
    assert "DISABLED" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["koru", "on"])
    assert cli.main() == 0
    assert not is_globally_disabled()


def test_loop_runner_stops_on_killswitch():
    from koru.autonomy.operator.operator_loop_runner import _cycle_stop_reason

    class _QueueResult:
        last_status = "done"

    class _Args:
        stop_on_waiting_input = False
        max_cycles = 0

    assert _cycle_stop_reason(_Args(), _QueueResult(), 1) is None
    global_disable("stop the loop")
    assert _cycle_stop_reason(_Args(), _QueueResult(), 1) == "global_killswitch"


def test_coauthor_hook_skipped_when_disabled(tmp_path):
    from koru.git_attribution import install_koru_agent_coauthor_hook

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)

    global_disable("no hooks while off")
    result = install_koru_agent_coauthor_hook(repo)
    assert result.status == "disabled_globally"
    assert not (repo / ".git" / "hooks" / "prepare-commit-msg").exists()


def test_coauthor_hook_shell_respects_killswitch(tmp_path, monkeypatch):
    """The installed shell hook itself must honor the marker file."""
    from koru.git_attribution import (
        KORU_AGENT_COAUTHOR_TRAILER,
        install_koru_agent_coauthor_hook,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)

    result = install_koru_agent_coauthor_hook(repo)
    assert result.status == "installed"
    hook = repo / ".git" / "hooks" / "prepare-commit-msg"
    assert hook.exists()

    env_dir = global_control_dir()

    def run_hook(msg: str) -> str:
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text(msg, encoding="utf-8")
        subprocess.run(
            ["sh", str(hook), str(msg_file)],
            check=True,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": str(tmp_path),
                "KORU_GLOBAL_CONTROL_DIR": str(env_dir),
            },
        )
        return msg_file.read_text(encoding="utf-8")

    # Enabled: trailer appended once, idempotent on re-run.
    text = run_hook("feat: x\n")
    assert KORU_AGENT_COAUTHOR_TRAILER in text
    assert run_hook(text).count(KORU_AGENT_COAUTHOR_TRAILER) == 1

    # Disabled: no trailer.
    global_disable("hook off")
    assert KORU_AGENT_COAUTHOR_TRAILER not in run_hook("feat: y\n")
