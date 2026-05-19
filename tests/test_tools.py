"""Tests for tools registry loading and detection."""

from __future__ import annotations

import textwrap
from pathlib import Path

from koru.tools import (
    build_tool_task_scaffold,
    detect_tools,
    infer_adapter_kind,
    load_tool_registry,
)


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
            """,
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
        },
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
            "detect": {
                "commands": ["not-a-real-command-koru"],
                "markers": [".windsurf/rules.md"],
                "env": [],
            },
        },
    ]

    out = detect_tools(tmp_path, registry)
    assert out[0]["available"] is True
    assert ".windsurf/rules.md" in out[0]["detected_via"]["markers"]


def test_infer_adapter_kind_defaults() -> None:
    assert infer_adapter_kind({"lane": "manual", "category": "plugin"}) == "human"
    assert infer_adapter_kind({"lane": "adapter", "category": "specialist"}) == "api"
    assert infer_adapter_kind({"lane": "adapter", "category": "cli_agent"}) == "shell"


def test_build_tool_task_scaffold_contains_expected_fields() -> None:
    scaffold = build_tool_task_scaffold(
        {
            "id": "gemini-cli",
            "lane": "adapter",
            "category": "cli_agent",
            "stability": "beta",
            "invoke": "planfile shell ticket",
            "notes": "Adapter lane pending native integration.",
        },
    )
    assert scaffold["source_tool"] == "koru-cli-tool-adapter"
    assert "tool-gemini-cli" in scaffold["labels"]
    assert scaffold["inputs"]["tool_id"] == "gemini-cli"
    assert "TOOL ADAPTER SCAFFOLD" in scaffold["prompt_suffix"]


def test_build_tool_task_scaffold_plugin_bridge_shape() -> None:
    scaffold = build_tool_task_scaffold(
        {
            "id": "github-copilot",
            "lane": "manual",
            "category": "plugin",
            "stability": "stable",
            "invoke": "manual plugin workflow",
            "notes": "No stable external control surface in koru.",
        },
    )
    assert scaffold["source_tool"] == "koru-cli-plugin-bridge"
    assert "plugin-bridge-scaffold" in scaffold["labels"]
    assert scaffold["source_context"]["plugin_bridge"] is True
    assert scaffold["inputs"]["plugin_bridge"] is True
    assert "PLUGIN BRIDGE SCAFFOLD" in scaffold["prompt_suffix"]
