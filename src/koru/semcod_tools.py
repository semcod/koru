"""Detect installed semcod-ecosystem tools available to a koru project.

The brief embeds this so an LLM agent immediately knows which
semcod CLIs / libraries it may call without guessing or trial-and-error.

Detection sources, in order of confidence:

1. **Binary in PATH** (``shutil.which``) — strongest signal; the tool can
   be invoked directly from a shell ticket.
2. **Importable Python module** (``importlib.util.find_spec``) — the
   tool is available as a library (e.g. ``import goal``); useful for
   ``executor.kind=llm`` or ``api`` tickets that call the API directly.
3. **Project config marker** — presence of ``[tool.<id>]`` in the
   project's ``pyproject.toml`` is treated as "configured for this
   project" and surfaced separately.

Tools that are neither in PATH, nor importable, nor configured are
reported with ``available=False`` so the agent knows to fall back or
ask for a bootstrap ticket.
"""

from __future__ import annotations

import shutil
import tomllib
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SemcodTool:
    """One detected (or absent) semcod tool."""

    id: str
    role: str
    command_hint: str
    available: bool
    via: str  # "PATH" | "module" | "config" | "missing"
    command: str | None = None
    config_present: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "command_hint": self.command_hint,
            "available": self.available,
            "via": self.via,
            "command": self.command,
            "config_present": self.config_present,
        }


# Tool registry — (id, role, command_hint, module_name).
#
# ``module_name`` is the importable Python package; some tools are
# Python libraries shipped under a different name than their CLI, but
# in the semcod ecosystem they match.
_TOOLS: tuple[tuple[str, str, str, str | None], ...] = (
    ("planfile", "ticket lifecycle (source of truth)", "planfile ticket <verb>", "planfile"),
    ("koru", "this gate — closed-loop automation", "koru / koru scan / koru --queue", "koru"),
    ("wup", "real-time file/service watcher", "wup watch / wup status", "wup"),
    ("testql", "behavioural HTTP probes", "testql suite / testql run <scenario>", "testql"),
    ("regix", "regression metrics gate", "regix gates / regix compare", "regix"),
    ("redup", "duplicate-code detector", "redup scan . / redup check", "redup"),
    ("sumr", "debounced project summary", "sumr generate / scripts/sumr-refresh.sh", "sumr"),
    ("sumd", "LLM-friendly project snapshot", "sumd . / code2llm ./ -f toon", "sumd"),
    ("code2llm", "whole-project LLM analysis and ticket discovery", "code2llm . -f all", None),
    ("prefact", "pre-refactor checks", "prefact check", "prefact"),
    ("pfix", "self-healing Python auto-fix", "pfix run", "pfix"),
    ("vallm", "syntax / semantic validation", "vallm validate -f <file>", "vallm"),
    ("redsl", "quality gate + LLM-backed improve lane", "redsl gate check .", "redsl"),
    ("llx", "LLM model router", "llx run / llx chat", "llx"),
    ("doql", "declarative infrastructure/app sync", "doql build / doql sync", "doql"),
    ("redeploy", "deployment planning and rollout", "redeploy plan / redeploy apply", "redeploy"),
    ("goal", "strategic goal alignment", "goal status / goal sync", "goal"),
    ("costs", "AI cost tracking + badge", "costs analyze", "costs"),
    ("op3", "multi-layer infra observation", "op3 observe / op3 report", "op3"),
    ("toonic", "TOON format conversion", "toonic convert", "toonic"),
    (
        "protogate",
        "bounded legacy migration gates",
        "protogate plan / protogate check",
        "protogate",
    ),
    ("rebuild", "git history walker / quality replay", "rebuild walk / rebuild serve", "rebuild"),
    ("mdflow", "markdown dependency analyzer", "mdflow graph / mdflow check", "mdflow"),
    ("metrun", "execution intelligence and bottlenecks", "metrun run / metrun report", "metrun"),
    ("sllm", "shell LLM client control plane", "sllm drive --client <id>", "sllm"),
)


def _read_pyproject(project: Path) -> dict[str, Any] | None:
    pyproject = project / "pyproject.toml"
    if not pyproject.is_file():
        return None
    try:
        with pyproject.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _config_present(pyproject: dict[str, Any] | None, tool_id: str) -> bool:
    """True when ``[tool.<id>]`` is declared in pyproject.toml."""
    if not pyproject:
        return False
    tool_section = pyproject.get("tool")
    if not isinstance(tool_section, dict):
        return False
    return tool_id in tool_section


def detect_semcod_tools(project: Path) -> list[SemcodTool]:
    """Return the registry of known semcod tools and their availability.

    The list is stable and ordered by koru's preference (most-impactful
    first). Tools are returned even when missing so the brief can
    surface them as bootstrap suggestions.
    """
    project = project.resolve()
    pyproject = _read_pyproject(project)
    result: list[SemcodTool] = []
    for tool_id, role, command_hint, module_name in _TOOLS:
        bin_path = shutil.which(tool_id)
        has_module = bool(module_name) and find_spec(module_name) is not None
        cfg = _config_present(pyproject, tool_id)
        if bin_path:
            via = "PATH"
        elif has_module:
            via = "module"
        elif cfg:
            via = "config"
        else:
            via = "missing"
        result.append(
            SemcodTool(
                id=tool_id,
                role=role,
                command_hint=command_hint,
                available=bool(bin_path or has_module),
                via=via,
                command=bin_path,
                config_present=cfg,
            ),
        )
    return result
