"""NL → dsl2koru command line (no side effects)."""

from __future__ import annotations

import os
from typing import Any

from uri2koru.nlp2uri import best_uri

from nlp2koru.llm_backend import LLMBackend, nl_to_dsl_line


def to_dsl(
    prompt: str,
    *,
    project: str | None = None,
    use_llm: bool = False,
    llm_backend: LLMBackend | None = None,
) -> str:
    if use_llm or os.getenv("OPENROUTER_API_KEY"):
        llm_line = nl_to_dsl_line(prompt, project=project, backend=llm_backend)
        if llm_line:
            return llm_line

    hit = best_uri(prompt, project=project)
    if hit and hit.dsl:
        return hit.dsl

    normalized = prompt.strip()
    if normalized.lower().startswith(("query_repair", "repair_run", "validate_lane", "resolve")):
        return normalized

    raise ValueError(f"could not map NL to DSL: {prompt!r}")


def workflow_from_nl(prompt: str) -> dict[str, Any]:
    """Bridge to nlpshim for desktop workflow steps (separate from dsl2koru dispatch)."""
    from nlpshim.client import NLPBridgeClient, analyze_text_structure

    structure = analyze_text_structure(prompt, include_plan=True)
    steps = NLPBridgeClient().parse_intent(prompt, execute=False)
    payload: dict[str, Any] = {"steps": steps}
    if structure is not None:
        payload["structure"] = structure
    return payload
