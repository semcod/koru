"""Tests for refactor planfile handoff text."""

from __future__ import annotations

from pathlib import Path

from koru.refactor_planfile_handoff import render_planfile_refactor_handoff


def test_render_handoff_mentions_analysis_paths(tmp_path: Path) -> None:
    text = render_planfile_refactor_handoff(tmp_path)
    assert "project/analysis.toon.yaml" in text
    assert "koru scan --apply" in text


def test_render_handoff_notes_when_analysis_present(tmp_path: Path) -> None:
    (tmp_path / "project").mkdir()
    (tmp_path / "project" / "analysis.toon.yaml").write_text("x: 1\n", encoding="utf-8")
    text = render_planfile_refactor_handoff(tmp_path)
    assert "tak" in text
