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
