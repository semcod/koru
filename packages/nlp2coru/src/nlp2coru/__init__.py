"""nlp2coru — natural-language to CORU DSL bridge."""

from .apply import ApplyResult, apply_prompt
from .heuristic import _refactor_intent, heuristic_plan, detect_setup_intent, to_dsl_lines
from .llm import llm_plan
from .llm_backend import LLMBackend, LitellmBackend, get_backend
from .models import CoruIntent, CoruPlan
from .rewrite import rewrite_chat_prompt

__all__ = [
    "ApplyResult",
    "apply_prompt",
    "CoruIntent",
    "CoruPlan",
    "LLMBackend",
    "LitellmBackend",
    "get_backend",
    "llm_plan",
    "_refactor_intent",
    "heuristic_plan",
    "detect_setup_intent",
    "to_dsl_lines",
    "rewrite_chat_prompt",
]
