"""Optional ``llx`` bridge for reflecting on IDE chat state.

The IDE plugin streams ``message.sent`` and ``message.received`` events into
the shared NDJSON file consumed by :mod:`koruide.chat_history`. When ``llx``
is on ``PATH`` (unless disabled with ``KORU_LLM_REFLECT=0``), the
autonomous loop can ask an OpenRouter-backed model to interpret those events
*before* deciding whether to redrive the same ticket prompt.

The bridge is intentionally lightweight and side-effect free:

* No event is sent if ``llx`` is missing → returns ``None`` (caller falls back
  to the simple cooldown heuristic).
* Outputs MUST be JSON ``{"done": bool, "needs_input": bool, "summary": str}``;
  anything else is treated as ``None``.
* Honors a hard timeout to keep the autonomous tick fast.

This is *exactly* the OpenRouter-backed reactive layer the operator asked
for: rather than blindly redriving a ticket every cycle, koru can briefly
"read" what the IDE-side LLM wrote back and decide accordingly.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Callable

from koruide.chat_history import ChatEvent, read_events

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReflectionResult:
    """Structured opinion from llx about the IDE conversation state."""

    done: bool
    needs_input: bool
    summary: str
    raw: str

    @classmethod
    def from_json(cls, raw: str) -> "ReflectionResult | None":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return cls(
            done=bool(payload.get("done", False)),
            needs_input=bool(payload.get("needs_input", False)),
            summary=str(payload.get("summary") or "").strip(),
            raw=raw,
        )


def llm_reflect_enabled() -> bool:
    """``True`` iff llx reflection is enabled and ``llx`` is on PATH.

    Behavior:
    - default (unset): disabled,
    - explicit falsey value (0/false/no/off): disabled,
    - explicit truthy value (1/true/yes/on/auto): enabled when ``llx`` exists.
    """
    flag = os.environ.get("KORU_LLM_REFLECT", "").strip().lower()
    if not flag or flag in {"0", "false", "no", "off"}:
        return False
    if flag not in {"1", "true", "yes", "on", "auto"}:
        return False
    return shutil.which("llx") is not None


def _format_events_for_prompt(events: list[ChatEvent]) -> str:
    if not events:
        return "(no recent chat events)"
    lines: list[str] = []
    now = time.time()
    for ev in events:
        ago = max(0.0, now - ev.ts)
        text = ev.text or ev.summary or ""
        snippet = text[:240].replace("\n", " ")
        lines.append(f"[t-{ago:.0f}s] {ev.type} ide={ev.ide} chat={ev.chat}: «{snippet}»")
    return "\n".join(lines)


def build_reflect_prompt(
    *,
    ticket_id: str,
    ticket_title: str,
    driven_prompt: str,
    events: list[ChatEvent],
) -> str:
    schema_example = '{"done": bool, "needs_input": bool, "summary": "<1 short sentence>"}'
    preview = (driven_prompt or "")[:300].replace("\n", " ")
    return (
        "You are a reflection assistant for the koru autonomous loop. The koru\n"
        "loop just drove the prompt below into the IDE chat. Based ONLY on the\n"
        "recent IDE chat events, decide whether the IDE-side LLM is:\n"
        "  - done = true: it produced a final answer or completed the task;\n"
        "  - needs_input = true: it is asking the user / koru a question and is\n"
        "    blocked until someone answers;\n"
        "  - otherwise (still working) leave both false.\n\n"
        "Respond STRICTLY as JSON, no prose:\n"
        f"  {schema_example}\n\n"
        f"Ticket: {ticket_id or '-'} — {ticket_title or '-'}\n"
        f"Driven prompt (last):\n  «{preview}»\n\n"
        f"Recent IDE chat events (newest last):\n{_format_events_for_prompt(events)}"
    )


def reflect_on_chat(
    *,
    ticket_id: str,
    ticket_title: str,
    driven_prompt: str,
    ide: str,
    chat: str = "default",
    within_seconds: float = 600.0,
    timeout: float = 20.0,
    runner: Callable[[list[str], float], subprocess.CompletedProcess[str]] | None = None,
    events: list[ChatEvent] | None = None,
) -> ReflectionResult | None:
    """Ask llx to interpret recent chat events; ``None`` if disabled/unavailable."""
    if not llm_reflect_enabled():
        return None
    recent = (
        events
        if events is not None
        else read_events(
            ide=ide,
            chat=chat,
            max_age_seconds=within_seconds,
            limit=20,
        )
    )
    if not recent:
        return None
    prompt = build_reflect_prompt(
        ticket_id=ticket_id,
        ticket_title=ticket_title,
        driven_prompt=driven_prompt,
        events=recent,
    )
    argv = ["llx", "chat", "--prompt", prompt, "--free"]
    invoke = runner or (
        lambda cmd, t: subprocess.run(
            cmd, capture_output=True, text=True, timeout=t, check=False
        )
    )
    try:
        result = invoke(argv, timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.info("llx reflect failed: %s", exc)
        return None
    if getattr(result, "returncode", 1) != 0:
        logger.info("llx reflect non-zero exit: %s", getattr(result, "stderr", ""))
        return None
    raw = (getattr(result, "stdout", "") or "").strip()
    return ReflectionResult.from_json(raw)


__all__ = [
    "ReflectionResult",
    "build_reflect_prompt",
    "llm_reflect_enabled",
    "reflect_on_chat",
]
