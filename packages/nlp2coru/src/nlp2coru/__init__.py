"""One-release compatibility aliases for :mod:`nlp2koru`."""

import warnings

warnings.warn(
    "nlp2coru is deprecated; import nlp2koru instead",
    DeprecationWarning,
    stacklevel=2,
)

import nlp2koru as _canonical  # noqa: E402

ApplyResult = _canonical.ApplyResult
CoruIntent = _canonical.KoruIntent
CoruPlan = _canonical.KoruPlan
LLMBackend = _canonical.LLMBackend
SubLlmBackend = _canonical.SubLlmBackend
_refactor_intent = _canonical._refactor_intent
apply_prompt = _canonical.apply_prompt
detect_setup_intent = _canonical.detect_setup_intent
get_backend = _canonical.get_backend
heuristic_plan = _canonical.heuristic_plan
llm_plan = _canonical.legacy_llm_plan
rewrite_chat_prompt = _canonical.rewrite_chat_prompt
to_dsl_lines = _canonical.to_dsl_lines

__all__ = [
    "ApplyResult",
    "CoruIntent",
    "CoruPlan",
    "LLMBackend",
    "SubLlmBackend",
    "_refactor_intent",
    "apply_prompt",
    "detect_setup_intent",
    "get_backend",
    "heuristic_plan",
    "llm_plan",
    "rewrite_chat_prompt",
    "to_dsl_lines",
]
