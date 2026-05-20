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
    assert "mcp-ide-flow.md" in text
    assert "autopilot-design.md" in text


def test_ide_router_doc_links_to_ide_control_surfaces() -> None:
    root = Path(__file__).resolve().parent.parent
    text = (root / "docs" / "ide-router.md").read_text(encoding="utf-8")
    assert "ide-control-surfaces.md" in text


def test_ide_router_doc_links_mcp_and_autopilot() -> None:
    root = Path(__file__).resolve().parent.parent
    text = (root / "docs" / "ide-router.md").read_text(encoding="utf-8")
    assert "mcp-ide-flow.md" in text
    assert "autopilot-design.md" in text


def test_mcp_ide_flow_doc_links_to_ide_control_surfaces() -> None:
    root = Path(__file__).resolve().parent.parent
    text = (root / "docs" / "mcp-ide-flow.md").read_text(encoding="utf-8")
    assert "ide-control-surfaces.md" in text


def test_autopilot_design_doc_links_to_ide_control_surfaces() -> None:
    root = Path(__file__).resolve().parent.parent
    text = (root / "docs" / "autopilot-design.md").read_text(encoding="utf-8")
    assert "ide-control-surfaces.md" in text


def test_agent_guide_links_to_ide_control_surfaces() -> None:
    root = Path(__file__).resolve().parent.parent
    text = (root / "docs" / "agent-guide.md").read_text(encoding="utf-8")
    assert "ide-control-surfaces.md" in text


def test_readme_links_ide_control_surfaces() -> None:
    root = Path(__file__).resolve().parent.parent
    text = (root / "README.md").read_text(encoding="utf-8")
    assert "docs/ide-control-surfaces.md" in text


def test_ide_protocol_doc_exists_with_key_protocol_terms() -> None:
    root = Path(__file__).resolve().parent.parent
    text = (root / "docs" / "IDE_PROTOCOL.md").read_text(encoding="utf-8")
    assert "Control Plane" in text
    assert "NDJSON" in text
    assert "chat.send" in text
    assert "session.ended" in text
    assert "docs/specs/kide-002-koruide-api-v1.md" in text
    assert "src/koruide/protocol.py" in text


def test_ide_protocol_doc_has_no_stale_payload_placeholder() -> None:
    root = Path(__file__).resolve().parent.parent
    text = (root / "docs" / "IDE_PROTOCOL.md").read_text(encoding="utf-8")
    assert "PROPOLS_DEPENDING_ON_TYPE" not in text
    assert "postrun_verify" not in text


def test_readme_links_formal_ide_protocol() -> None:
    root = Path(__file__).resolve().parent.parent
    text = (root / "README.md").read_text(encoding="utf-8")
    assert "docs/IDE_PROTOCOL.md" in text


def test_docs_index_links_formal_ide_protocol() -> None:
    root = Path(__file__).resolve().parent.parent
    text = (root / "docs" / "README.md").read_text(encoding="utf-8")
    assert "IDE_PROTOCOL.md" in text
