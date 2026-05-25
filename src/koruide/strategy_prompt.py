"""Build LLM-ready strategy prompts for Koru IDE control.

The strategy prompt is the canonical "how to plan an IDE scenario" briefing
that Koru hands to an external LLM (OpenRouter, an IDE-side model, etc.).
It bundles three artefacts the LLM needs to make a safe decision:

1. The compact command catalog (capability buckets per IDE).
2. The JSON Schema for ``koru.ide_command_scenario.v1`` (so the LLM knows the
   only output shape Koru will accept).
3. The static risk/safety policy (so the LLM understands what Koru will
   ultimately gate at execution time).

The same payload is exposed via:

* MCP tool ``koru_strategy_prompt``
* REST endpoint ``GET /api/ide/strategy-prompt?ide=cursor[&for_llm=1]``
* Python helper for in-process callers (e.g. ``OpenRouterPicker``).
"""

from __future__ import annotations

import json
from typing import Any

from koruide.command_catalog import (
    POLICY,
    build_ide_command_catalog,
    command_catalog_for_llm,
    supported_catalog_ides,
)
from koruide.command_scenario import SCENARIO_SCHEMA

STRATEGY_PROMPT_VERSION = "1.0.0"
STRATEGY_PROMPT_SCHEMA = "koru.ide_strategy_prompt.v1"

_HEADER = (
    "You are planning an IDE control scenario for Koru.\n"
    "Koru is the executor: you propose, Koru verifies and runs.\n"
    "Treat every command as a candidate; the live plugin re-checks availability\n"
    "via vscode.commands.getCommands(false) (or ActionManager.getAction for "
    "JetBrains) before anything runs."
)

_RULES = (
    "Rules:\n"
    "1. Output MUST be a single JSON object matching schema "
    "'koru.ide_command_scenario.v1'.\n"
    "2. Only reference commands present in the catalog below. Do NOT invent IDs.\n"
    "3. Pick the lowest-risk command that achieves the step's intent.\n"
    "4. Avoid focus_open_avoid unless the intent is explicitly 'new chat / "
    "toggle pane'.\n"
    "5. Prefer Koru-owned protocol over clipboard; clipboard is fallback only.\n"
    "6. Set `requires_runtime_verification: true` unless you have a justified "
    "reason to bypass.\n"
    "7. Each step has an `action` in: focus_open, focus_input, paste_text, "
    "submit, atomic_send, reload_reconnect, diagnostics, wait."
)


def _selected_ides(ide: str | None) -> list[str]:
    if ide is None or str(ide).strip().lower() in {"", "all"}:
        return list(supported_catalog_ides())
    ide_id = str(ide).strip().lower()
    if ide_id not in supported_catalog_ides():
        raise ValueError(
            f"unknown IDE {ide!r}; supported: {', '.join(supported_catalog_ides())}",
        )
    return [ide_id]


def build_strategy_prompt(
    ide: str | None = None,
    *,
    for_llm: bool = True,
    include_text: bool = True,
) -> dict[str, Any]:
    """Return the LLM strategy prompt as a structured payload.

    ``for_llm=True`` returns the compact category-only catalog (recommended
    for LLM context windows). ``for_llm=False`` returns the full catalog
    with notes and confidence per command.

    When ``include_text=True`` the payload includes a ready-to-paste
    ``text`` field – a deterministic Markdown briefing the LLM can be
    handed verbatim as a system prompt.
    """
    ides = _selected_ides(ide)
    catalog = (
        command_catalog_for_llm(ides[0] if len(ides) == 1 else None)
        if for_llm
        else build_ide_command_catalog(ides[0] if len(ides) == 1 else None)
    )
    payload: dict[str, Any] = {
        "schema": STRATEGY_PROMPT_SCHEMA,
        "version": STRATEGY_PROMPT_VERSION,
        "ide": ides[0] if len(ides) == 1 else "all",
        "supported_ides": list(supported_catalog_ides()),
        "policy": POLICY,
        "scenario_schema": SCENARIO_SCHEMA,
        "command_catalog": catalog,
    }
    if include_text:
        payload["text"] = format_strategy_prompt_text(payload)
    return payload


def format_strategy_prompt_text(payload: dict[str, Any]) -> str:
    """Render the strategy prompt as deterministic Markdown."""
    ide = payload.get("ide", "all")
    parts: list[str] = [
        f"# Koru IDE strategy prompt ({ide})",
        "",
        _HEADER,
        "",
        _RULES,
        "",
        "## Policy",
        f"- runtime_verification: {payload['policy']['runtime_verification']}",
        f"- llm_contract: {payload['policy']['llm_contract']}",
        f"- safety: {payload['policy']['safety']}",
        "",
        "## Command catalog",
        "```json",
        json.dumps(payload["command_catalog"], indent=2, sort_keys=True),
        "```",
        "",
        "## Output JSON Schema (koru.ide_command_scenario.v1)",
        "```json",
        json.dumps(payload["scenario_schema"], indent=2, sort_keys=True),
        "```",
        "",
        "Reply with the scenario JSON only — no prose, no markdown fence.",
    ]
    return "\n".join(parts)


__all__ = [
    "STRATEGY_PROMPT_SCHEMA",
    "STRATEGY_PROMPT_VERSION",
    "build_strategy_prompt",
    "format_strategy_prompt_text",
]
