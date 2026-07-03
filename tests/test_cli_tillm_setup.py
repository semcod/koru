"""Tests for the `koru tillm` provider setup picker."""

from __future__ import annotations

from koru.cli_tillm_setup import tillm_setup_main


def test_non_interactive_lists_and_exits_cleanly(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    rc = tillm_setup_main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "z.ai" in out
    assert "claude-code" in out
    assert "provider set" in out  # non-interactive hint


def test_missing_tillm_reports_actionable_error(capsys, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("tillm"):
            raise ImportError("no tillm")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    rc = tillm_setup_main([])
    err = capsys.readouterr().err
    assert rc == 2
    assert "pip install tillm" in err
