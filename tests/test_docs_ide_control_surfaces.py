"""Regression: ide-control-surfaces roadmap doc stays present and non-empty."""

from __future__ import annotations

from pathlib import Path


def test_ide_control_surfaces_doc_exists_with_key_sections() -> None:
    root = Path(__file__).resolve().parent.parent
    path = root / "docs" / "ide-control-surfaces.md"
    text = path.read_text(encoding="utf-8")
    assert "MCP" in text
    assert "DAP" in text or "Debug Adapter" in text
    assert "Neovim" in text
    assert "ide-router.md" in text
