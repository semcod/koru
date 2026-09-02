"""Canonical natural-language adapter for Koru control commands."""

from nlp2koru.apply import (
    ApplyResult,
    _execute_line,
    apply_nl,
    apply_prompt,
    dispatch_line,
    is_dsl2koru_line,
)
from nlp2koru.llm_backend import (
    LLMBackend,
    SubLlmBackend,
    get_backend,
    legacy_llm_plan,
    llm_plan,
    nl_to_dsl_line,
    rewrite_chat_prompt,
)
from nlp2koru.to_dsl import (
    KoruIntent,
    KoruPlan,
    _refactor_intent,
    detect_setup_intent,
    heuristic_plan,
    to_dsl,
    to_dsl_lines,
    workflow_from_nl,
)

__all__ = [
    "ApplyResult",
    "KoruIntent",
    "KoruPlan",
    "LLMBackend",
    "SubLlmBackend",
    "_execute_line",
    "_refactor_intent",
    "apply_nl",
    "apply_prompt",
    "detect_setup_intent",
    "dispatch_line",
    "get_backend",
    "heuristic_plan",
    "is_dsl2koru_line",
    "legacy_llm_plan",
    "llm_plan",
    "nl_to_dsl_line",
    "rewrite_chat_prompt",
    "to_dsl",
    "to_dsl_lines",
    "workflow_from_nl",
]
