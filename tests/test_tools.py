"""Tests for tools registry loading and detection."""

from __future__ import annotations

import textwrap
from pathlib import Path

from koru.tools import detect_tools, load_tool_registry


def test_load_registry_from_explicit_path(tmp_path: Path) -> None:
    reg = tmp_path / "registry.yaml"
    reg.write_text(
        textwrap.dedent(
            """
            tools:
              - id: sample
                name: Sample
                category: cli_agent
                lane: adapter
                detect:
                  commands: ["python3"]
            """
        ),
        encoding="utf-8",
    )

    entries, used = load_tool_registry(reg)
    assert used == reg.resolve()
    assert len(entries) == 1
    assert entries[0]["id"] == "sample"


def test_detect_tools_marks_available_via_command(tmp_path: Path) -> None:
    registry = [
        {
            "id": "python",
            "name": "Python",
            "category": "cli_agent",
            "lane": "adapter",
            "detect": {"commands": ["python3"], "markers": [], "env": []},
        }
    ]

    out = detect_tools(tmp_path, registry)
    assert len(out) == 1
    assert out[0]["id"] == "python"
    assert out[0]["available"] is True
    assert "python3" in out[0]["detected_via"]["commands"]


def test_detect_tools_marks_available_via_marker(tmp_path: Path) -> None:
    (tmp_path / ".windsurf" / "rules.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".windsurf" / "rules.md").write_text("# rules", encoding="utf-8")

    registry = [
        {
            "id": "windsurf",
            "name": "Windsurf",
            "category": "ide",
            "lane": "native",
            "detect": {"commands": ["not-a-real-command-koru"], "markers": [".windsurf/rules.md"], "env": []},
        }
    ]

    out = detect_tools(tmp_path, registry)
    assert out[0]["available"] is True
    assert ".windsurf/rules.md" in out[0]["detected_via"]["markers"]
