"""Chat prompt rewrite helper (via LLMBackend Protocol)."""

from __future__ import annotations

from .llm_backend import LLMBackend, get_backend


def rewrite_chat_prompt(
    text: str,
    *,
    ide: str,
    instance: str,
    model: str | None = None,
    backend: LLMBackend | None = None,
) -> str:
    try:
        llm = get_backend(backend)
    except Exception:
        return text

    instruction = (
        "Rewrite the user message into a concise IDE chat prompt for coding assistant. "
        "Preserve intent and language. Return only plain text."
    )
    payload = f"ide={ide} instance={instance}\nmessage={text}"
    try:
        rewritten = llm.complete(
            model=model or "",
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": payload},
            ],
        )
    except Exception:
        return text
    return rewritten or text
