"""Heuristic inputs for evolving ``autonomy.strategy``."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from koru.semcod_tools import detect_semcod_tools
from koruide.command_catalog import command_catalog_for_llm


def build_strategy_heuristics(project: Path) -> dict[str, Any]:
    project = project.resolve()
    analysis = project / "project" / "analysis.toon.yaml"
    tool_rows = [tool.to_dict() for tool in detect_semcod_tools(project)]
    available_tools = [row["id"] for row in tool_rows if row.get("available")]
    missing_tools = [row["id"] for row in tool_rows if not row.get("available")]
    return {
        "project": str(project),
        "planfile_present": (project / ".planfile").is_dir(),
        "koru_yaml_present": (project / "koru.yaml").is_file(),
        "code2llm_analysis": {
            "path": "project/analysis.toon.yaml",
            "present": analysis.is_file(),
            "age_seconds": _file_age_seconds(analysis),
        },
        "semcod_tools": {
            "available": available_tools,
            "missing": missing_tools,
            "details": tool_rows,
        },
        "ide_command_api": command_catalog_for_llm(),
        "recommendations": _recommendations(available_tools, analysis.is_file()),
    }


def _file_age_seconds(path: Path) -> float | None:
    if not path.is_file():
        return None
    return max(0.0, time.time() - path.stat().st_mtime)


def _recommendations(available_tools: list[str], has_code2llm_analysis: bool) -> list[str]:
    recs = [
        "Keep planfile as source_of_truth and execute specific tickets before broad discovery.",
        "When the queue is idle, run scan/code2llm discovery and create focused tickets.",
    ]
    if "code2llm" not in available_tools:
        recs.append("Install or expose code2llm to enable automated whole-project discovery.")
    if "prefact" in available_tools:
        recs.append(
            "Use prefact as an advisory pre-refactor/check signal until a ticket adapter exists.",
        )
    if "metrun" in available_tools:
        recs.append(
            "Use metrun for performance-specific strategy proposals, not default every-cycle work.",
        )
    if not has_code2llm_analysis:
        recs.append(
            "Generate project/analysis.toon.yaml before relying on artifact-based "
            "refactor tickets.",
        )
    return recs


__all__ = ["build_strategy_heuristics"]
