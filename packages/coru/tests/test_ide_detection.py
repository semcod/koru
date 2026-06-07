"""Tests for ``coru.ide_detection``."""

import pytest

from coru import ide_detection


@pytest.fixture(autouse=True)
def _clear_ide_env(monkeypatch):
    for key in (
        "CHROME_DESKTOP",
        "CURSOR_AGENT",
        "CURSOR_CLI",
        "GIO_LAUNCHED_DESKTOP_FILE",
        "IDEA_INITIAL_DIRECTORY",
        "JETBRAINS_IDE",
        "PYCHARM_HOSTED",
        "TERM_PROGRAM",
        "TERM_PROGRAM_VERSION",
        "TERMINAL_EMULATOR",
        "VSCODE_CODE_CACHE_PATH",
        "VSCODE_NLS_CONFIG",
        "VSCODE_PID",
        "WINDSURF_CASCADE_TERMINAL",
        "WINDSURF_VERSION",
    ):
        monkeypatch.delenv(key, raising=False)


class TestIdeFromVscodePid:
    def test_none_when_no_vscode_pid(self, monkeypatch):
        monkeypatch.delenv("VSCODE_PID", raising=False)
        assert ide_detection._ide_from_vscode_pid() is None

    def test_none_when_invalid_pid(self, monkeypatch):
        monkeypatch.setenv("VSCODE_PID", "abc")
        assert ide_detection._ide_from_vscode_pid() is None


class TestVscodeFamilyEnvHint:
    def test_none_when_no_env(self, monkeypatch):
        for key in ("CHROME_DESKTOP", "VSCODE_CODE_CACHE_PATH", "VSCODE_NLS_CONFIG", "GIO_LAUNCHED_DESKTOP_FILE"):
            monkeypatch.delenv(key, raising=False)
        assert ide_detection._vscode_family_env_hint() is None

    def test_detects_cursor(self, monkeypatch):
        monkeypatch.setenv("CHROME_DESKTOP", "cursor.desktop")
        assert ide_detection._vscode_family_env_hint() == "cursor"

    def test_detects_windsurf(self, monkeypatch):
        monkeypatch.setenv("CHROME_DESKTOP", "devin.desktop")
        assert ide_detection._vscode_family_env_hint() == "windsurf"


class TestWindsurfTerminalMarker:
    def test_false_when_no_env(self, monkeypatch):
        for key in ("WINDSURF_CASCADE_TERMINAL", "WINDSURF_VERSION", "TERM_PROGRAM_VERSION", "CHROME_DESKTOP", "GIO_LAUNCHED_DESKTOP_FILE"):
            monkeypatch.delenv(key, raising=False)
        assert ide_detection._windsurf_terminal_marker() is False

    def test_true_from_cascade_terminal(self, monkeypatch):
        monkeypatch.setenv("WINDSURF_CASCADE_TERMINAL", "1")
        assert ide_detection._windsurf_terminal_marker() is True

    def test_true_from_term_version(self, monkeypatch):
        monkeypatch.setenv("TERM_PROGRAM_VERSION", "1.0.0-devin-desktop")
        assert ide_detection._windsurf_terminal_marker() is True


class TestTerminalShellContextFallback:
    def test_vscode_when_term_program_is_vscode(self, monkeypatch):
        monkeypatch.setenv("TERM_PROGRAM", "vscode")
        monkeypatch.delenv("VSCODE_PID", raising=False)
        for key in ("CHROME_DESKTOP", "VSCODE_CODE_CACHE_PATH", "VSCODE_NLS_CONFIG", "GIO_LAUNCHED_DESKTOP_FILE",
                    "WINDSURF_CASCADE_TERMINAL", "WINDSURF_VERSION", "TERM_PROGRAM_VERSION"):
            monkeypatch.delenv(key, raising=False)
        result = ide_detection._terminal_shell_context_fallback()
        assert result == ("vscode", "env:TERM_PROGRAM", True)

    def test_cursor_from_chrome_desktop(self, monkeypatch):
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        monkeypatch.delenv("TERMINAL_EMULATOR", raising=False)
        monkeypatch.setenv("CHROME_DESKTOP", "cursor.desktop")
        result = ide_detection._terminal_shell_context_fallback()
        assert result == ("cursor", "env:CURSOR_*", True)

    def test_jetbrains_from_terminal_emulator(self, monkeypatch):
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        monkeypatch.setenv("TERMINAL_EMULATOR", "JetBrains-JediTerm")
        result = ide_detection._terminal_shell_context_fallback()
        assert result == ("jetbrains", "env:TERMINAL_EMULATOR", True)

    def test_none_when_no_ide(self, monkeypatch):
        for key in ("TERM_PROGRAM", "TERMINAL_EMULATOR", "CHROME_DESKTOP", "CURSOR_AGENT",
                    "IDEA_INITIAL_DIRECTORY", "GIO_LAUNCHED_DESKTOP_FILE",
                    "WINDSURF_CASCADE_TERMINAL", "WINDSURF_VERSION", "TERM_PROGRAM_VERSION"):
            monkeypatch.delenv(key, raising=False)
        result = ide_detection._terminal_shell_context_fallback()
        assert result == (None, "none", False)

    def test_monkeypatch_ide_from_vscode_pid(self, monkeypatch):
        """Verify monkeypatch compatibility for coru.cli tests."""
        monkeypatch.setenv("TERM_PROGRAM", "vscode")
        monkeypatch.setenv("VSCODE_PID", "12345")

        def fake_ide_from_pid():
            return "vscodium"

        result = ide_detection._terminal_shell_context_fallback(
            ide_from_vscode_pid=fake_ide_from_pid,
        )
        assert result == ("vscodium", "env:VSCODE_PID.exe", True)

    def test_monkeypatch_vscode_family_env_hint(self, monkeypatch):
        """Verify monkeypatch compatibility for coru.cli tests."""
        monkeypatch.setenv("TERM_PROGRAM", "vscode")
        monkeypatch.delenv("VSCODE_PID", raising=False)

        def fake_hint():
            return "cursor"

        result = ide_detection._terminal_shell_context_fallback(
            vscode_family_env_hint=fake_hint,
        )
        assert result == ("cursor", "env:VSCODE_*", True)
