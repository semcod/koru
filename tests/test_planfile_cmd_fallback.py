"""A broken ``KORU_PLANFILE_CMD`` must not kill the queue.

Field incident (c2004, 2026-07-02): ``KORU_PLANFILE_CMD=.venv/bin/python -m
planfile.cli`` with no planfile installed in that venv produced
``planfile_queue.tick_error`` on every ticket-list call. The resolver now
verifies the pinned command once and falls back to auto-resolution with a
single stderr warning; ``koru doctor`` reports the same condition.
"""

from __future__ import annotations

import shlex
import stat
from pathlib import Path

import koru.queue.ticket as ticket_mod
from koru.doctor_project_health import check_planfile_binary
from koru.queue.ticket import (
    _configured_planfile_cmd_usable,
    resolve_planfile_base_command,
)


def _script(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _module_missing_script(tmp_path: Path, name: str = "broken-planfile") -> Path:
    return _script(
        tmp_path,
        name,
        'echo "python: Error while finding module specification for \'planfile.cli\' '
        "(ModuleNotFoundError: No module named 'planfile')\" >&2\nexit 1",
    )


class TestConfiguredCmdUsable:
    def test_working_command_is_usable(self, tmp_path):
        script = _script(tmp_path, "ok-planfile", 'echo "Planfile CLI version: 0.1.104"')
        assert _configured_planfile_cmd_usable(str(script)) is True

    def test_module_missing_command_is_unusable(self, tmp_path):
        script = _module_missing_script(tmp_path)
        assert _configured_planfile_cmd_usable(str(script)) is False

    def test_unrelated_failure_stays_trusted(self, tmp_path):
        # Only the module-missing signature may bypass an operator pin.
        script = _script(tmp_path, "flaky-planfile", 'echo "boom: config error" >&2\nexit 1')
        assert _configured_planfile_cmd_usable(str(script)) is True

    def test_missing_binary_keeps_pin_authoritative(self, tmp_path):
        # A pin we cannot probe stays trusted — doctor reports it separately;
        # only the module-missing signature may bypass operator config.
        assert _configured_planfile_cmd_usable(str(tmp_path / "nope")) is True


class TestResolveFallback:
    def test_broken_pin_falls_back_and_warns_once(self, tmp_path, monkeypatch, capsys):
        script = _module_missing_script(tmp_path)
        monkeypatch.setenv("KORU_PLANFILE_CMD", str(script))
        monkeypatch.setattr(
            ticket_mod, "_local_planfile_executable", lambda _p: tmp_path / "resolved-planfile"
        )
        ticket_mod._warned_planfile_cmd_fallbacks.clear()

        first = resolve_planfile_base_command(tmp_path)
        second = resolve_planfile_base_command(tmp_path)

        assert first == [str(tmp_path / "resolved-planfile")]
        assert second == first
        err = capsys.readouterr().err
        assert err.count("falling back to auto-resolution") == 1

    def test_working_pin_is_used_verbatim(self, tmp_path, monkeypatch):
        script = _script(tmp_path, "ok-planfile2", 'echo "Planfile CLI version: 0.1.104"')
        configured = f"{script} --project ."
        monkeypatch.setenv("KORU_PLANFILE_CMD", configured)

        assert resolve_planfile_base_command(tmp_path) == shlex.split(configured)


class TestLaneDependenciesCheck:
    def test_shell_lane_without_tillm_fails(self, tmp_path, monkeypatch):
        import koru.tillm_bridge as tb
        from koru.doctor_project_health import check_lane_dependencies

        monkeypatch.setenv("KORU_TILLM_CLIENT", "claude-code")
        monkeypatch.setattr(tb, "looks_like_shell_client", lambda _t: True)
        monkeypatch.setattr(tb, "tillm_available", lambda: False)

        status, message = check_lane_dependencies(tmp_path)

        assert status.lower() in {"fail", "failed"} or "FAIL" in status
        assert "pip install tillm" in message

    def test_shell_lane_without_cli_fails(self, tmp_path, monkeypatch):
        import koru.tillm_bridge as tb
        from koru.doctor_project_health import check_lane_dependencies

        monkeypatch.setenv("KORU_TILLM_CLIENT", "claude-code")
        monkeypatch.setattr(tb, "looks_like_shell_client", lambda _t: True)
        monkeypatch.setattr(tb, "tillm_available", lambda: True)
        monkeypatch.setattr(tb, "shell_agent_available", lambda _t: False)

        status, message = check_lane_dependencies(tmp_path)

        assert "not on PATH" in message

    def test_shell_lane_healthy_passes(self, tmp_path, monkeypatch):
        import koru.tillm_bridge as tb
        from koru.doctor_project_health import check_lane_dependencies

        monkeypatch.setenv("KORU_TILLM_CLIENT", "claude-code")
        monkeypatch.setattr(tb, "looks_like_shell_client", lambda _t: True)
        monkeypatch.setattr(tb, "tillm_available", lambda: True)
        monkeypatch.setattr(tb, "shell_agent_available", lambda _t: True)

        status, message = check_lane_dependencies(tmp_path)

        assert "tillm + CLI available" in message

    def test_editor_lane_without_gillm_warns(self, tmp_path, monkeypatch):
        import sys

        import koru.tillm_bridge as tb
        from koru.doctor_project_health import check_lane_dependencies

        monkeypatch.delenv("KORU_TILLM_CLIENT", raising=False)
        monkeypatch.setenv("KORU_AUTOPILOT_IDE", "vscode")
        monkeypatch.setattr(tb, "looks_like_shell_client", lambda _t: False)
        monkeypatch.setattr(tb, "tillm_available", lambda: True)
        monkeypatch.setitem(sys.modules, "gillm", None)

        _status, message = check_lane_dependencies(tmp_path)

        assert "GUI fallbacks unavailable" in message


class TestDoctorCheck:
    def test_doctor_fails_on_module_missing_pin(self, tmp_path, monkeypatch):
        script = _module_missing_script(tmp_path, "broken-doctor-planfile")
        monkeypatch.setenv("KORU_PLANFILE_CMD", str(script))

        status, message = check_planfile_binary(tmp_path)

        assert status == "FAIL" or "fail" in status.lower()
        assert "install planfile" in message

    def test_doctor_passes_on_working_pin(self, tmp_path, monkeypatch):
        script = _script(tmp_path, "ok-doctor-planfile", 'echo "Planfile CLI version: 0.1.104"')
        monkeypatch.setenv("KORU_PLANFILE_CMD", str(script))

        status, _message = check_planfile_binary(tmp_path)

        assert "fail" not in status.lower()
