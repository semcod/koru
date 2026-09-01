"""nlp2koru — NL → dsl2koru command lines."""

from nlp2koru.apply import ApplyResult, apply_nl
from nlp2koru.llm_backend import LLMBackend, SubLlmBackend, get_backend
from nlp2koru.to_dsl import to_dsl, workflow_from_nl

__all__ = [
    "ApplyResult",
    "apply_nl",
    "LLMBackend",
    "SubLlmBackend",
    "get_backend",
    "to_dsl",
    "workflow_from_nl",
]
