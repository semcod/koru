"""Regression: verify commands must run in a sanitized env (no loop leakage)."""

from __future__ import annotations

from pathlib import Path

import pytest

from koru.autonomy.post_run_verify import run_verify_commands


def test_verify_env_strips_loop_runtime_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_TILLM_CLIENT", "claude-code")
    monkeypatch.setenv("TILLM_BACKEND", "binary")
    monkeypatch.setenv("VDISPLAY_AGENT_URL", "http://127.0.0.1:8766")
    probe = (
        "python3 -c \"import os,sys; leaked=[k for k in os.environ "
        "if k.startswith(('KORU_','TILLM_','VDISPLAY_'))]; sys.exit(1 if leaked else 0)\""
    )
    ok, detail, code = run_verify_commands(tmp_path, [probe])
    assert ok is True, f"loop env leaked into verify subprocess: {detail}"
    assert code == 0


def test_verify_env_keeps_regular_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOME_REGULAR_VAR", "keep-me")
    probe = "python3 -c \"import os,sys; sys.exit(0 if os.environ.get('SOME_REGULAR_VAR')=='keep-me' else 1)\""
    ok, _detail, _code = run_verify_commands(tmp_path, [probe])
    assert ok is True


def test_stock_shell_runner_is_swapped_for_sanitized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy call sites pass run_shell_command explicitly — it must still sanitize."""
    from koru.queue.runners import run_shell_command

    monkeypatch.setenv("KORU_TILLM_CLIENT", "claude-code")
    probe = (
        "python3 -c \"import os,sys; sys.exit(1 if os.environ.get('KORU_TILLM_CLIENT') else 0)\""
    )
    ok, detail, _code = run_verify_commands(tmp_path, [probe], shell_runner=run_shell_command)
    assert ok is True, f"stock runner leaked loop env: {detail}"


def test_injected_fake_runner_is_untouched(tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_runner(command: str, project: Path):
        calls.append(command)
        import subprocess

        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    ok, _detail, _code = run_verify_commands(tmp_path, ["anything"], shell_runner=fake_runner)
    assert ok is True
    assert calls == ["anything"]
