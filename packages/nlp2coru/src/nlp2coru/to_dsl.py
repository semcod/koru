"""NL → dsl2coru command line (no side effects)."""

from __future__ import annotations

import os
from typing import Any

from uri2coru.nlp2uri import best_uri

from nlp2coru.heuristic import to_dsl_lines


def to_dsl(
    prompt: str,
    *,
    project: str | None = None,
    default_file: str | None = None,
    use_llm: bool = False,
    llm_model: str = "openrouter/qwen/qwen3-coder-next",
) -> str:
    ctx = default_file or project
    if use_llm or os.getenv("OPENROUTER_API_KEY"):
        try:
            from nlp2coru.llm import llm_plan

            plan = llm_plan(prompt, model=llm_model)
            if plan.steps:
                lines = to_dsl_lines(prompt, use_llm=False, llm_model=llm_model)
                if lines:
                    return lines[0]
        except Exception:
            pass

    hit = best_uri(prompt, default_file=ctx, project=ctx)
    if hit and hit.dsl:
        return hit.dsl

    lines = to_dsl_lines(prompt, use_llm=False, llm_model=llm_model)
    if lines:
        return lines[0]

    normalized = prompt.strip()
    if normalized.lower().startswith(("status", "lane", "repair", "auto", "ensure", "doctor")):
        return normalized.upper().split()[0]

    raise ValueError(f"could not map NL to DSL: {prompt!r}")
