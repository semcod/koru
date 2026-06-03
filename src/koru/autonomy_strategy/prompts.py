"""Prepared prompts for LLM-assisted strategy updates."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from koru.autonomy_strategy.config import load_autonomy_strategy
from koru.autonomy_strategy.heuristics import build_strategy_heuristics


def build_strategy_update_prompt(project: Path) -> str:
    """Return a prompt for OpenRouter or an IDE-side LLM.

    The prompt asks for a YAML patch only. Koru can show or send this prompt,
    while the actual edit remains reviewable in ``koru.yaml``.
    """
    strategy = load_autonomy_strategy(project) or {}
    heuristics = build_strategy_heuristics(project)
    strategy_yaml = yaml.safe_dump(strategy, sort_keys=False, allow_unicode=True).strip()
    heuristic_json = json.dumps(heuristics, ensure_ascii=False, indent=2)
    return (
        "You are helping tune Koru autonomy for this repository.\n"
        "Goal: improve the `autonomy.strategy` section in koru.yaml while preserving "
        "Planfile as the source of truth.\n\n"
        "Rules:\n"
        "- Return only a unified diff or a YAML replacement for `autonomy.strategy`.\n"
        "- Keep the rhythm detail-to-general: concrete tickets first, whole-project "
        "discovery only when the queue is idle.\n"
        "- Preserve idle discovery follow-up: run scan/code2llm first; if still no "
        "runnable tickets, ask IDE LLM: \"Co jeszcze zostalo do wykonania? zrob z "
        "tego nastepne tickety do planfile.\" and keep output ticket-oriented.\n"
        "- Do not invent tools as automated unless they are available and have a "
        "Mark goal/costs as advisory unless configured otherwise.\n"
        "- Use `ide_command_api` as a candidate map only: prefer low-risk public or "
        "runtime-verified commands, require live command/action verification before "
        "private IDE commands, and avoid new-chat/pane-toggle commands unless requested.\n"
        "- Prefer reviewable knobs over hidden behavior.\n\n"
        "Current autonomy.strategy:\n"
        "```yaml\n"
        f"{strategy_yaml}\n"
        "```\n\n"
        "Heuristic project report:\n"
        "```json\n"
        f"{heuristic_json}\n"
        "```\n"
    )


__all__ = ["build_strategy_update_prompt"]
