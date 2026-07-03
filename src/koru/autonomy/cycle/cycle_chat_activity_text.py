"""Pure text-processing helpers for autopilot chat-activity logic.

Extracted from ``autonomous_cycle_chat_activity`` (R-CA2) to isolate the
deterministic text utilities (prompt normalization, intake detection,
question extraction) from the operational module that wires them into
the autopilot loop. These functions have **no Koru dependencies** beyond
``re`` and ``typing``, which makes them trivially testable.

The legacy ``_underscored`` names remain importable from
``autonomous_cycle_chat_activity`` via ``import as`` re-exports so existing
tests/callers keep working without changes.
"""

from __future__ import annotations

import re
from typing import Any


def normalize_prompt_text(text: str) -> str:
  """Collapse whitespace and lowercase ``text`` for fuzzy comparison."""
  return " ".join(str(text or "").split()).strip().lower()


def looks_like_autopilot_generated_prompt(text: str) -> bool:
  """Detect strings that match autopilot's own generated prompts.

  Used to filter out IDE chat events that are echoes of autopilot drives
  rather than fresh user/LLM input. The patterns mirror the prompt
  templates emitted by ``koru.autonomy.prompts``.
  """
  normalized = normalize_prompt_text(text)
  if not normalized:
    return False
  if normalized.startswith("ticket ") and " has been stuck in status " in normalized:
    return True
  if normalized.startswith("work on planfile ticket "):
    return True
  if "planfile ticket done " in normalized:
    return True
  if normalized.startswith("the queue is blocked on waiting_input"):
    return True
  return False


def looks_like_explicit_intake_text(text: str) -> bool:
  """Heuristic: does ``text`` look like a deliberate operator intake message?

  Recognizes:
    - paths starting with ``/``, ``./``, ``../``, ``~/``
    - explicit intake prefixes: ``bug:``, ``task:``, ``todo:``, ``ticket:``,
      ``fix:``, ``feature:``
    - inline references to project paths (``src/...``, ``tests/...`` etc.)
  """
  raw = " ".join(str(text or "").split()).strip()
  if not raw:
    return False
  lowered = raw.lower()
  if lowered.startswith(("/", "./", "../", "~/")):
    return True
  if lowered.startswith(("bug:", "task:", "todo:", "ticket:", "fix:", "feature:")):
    return True
  if re.search(r"\b(?:src|tests|docs|plugins|services|project)/[\w./-]+", raw):
    return True
  return False


def compact_question_text(text: str, *, limit: int = 240) -> str:
  """Collapse whitespace in ``text`` and truncate to ``limit`` chars."""
  collapsed = " ".join(str(text or "").split()).strip()
  if not collapsed:
    return ""
  return collapsed[:limit]


def extract_needs_input_question(
  reflection_events: list[Any],
  reflection_summary: str,
) -> str:
  """Best-effort extraction of the concrete question asked by IDE LLM.

  Scans ``reflection_events`` newest-first for ``message.received`` entries
  and returns the most recent question (text ending with ``?`` or matching
  one of the known clarification markers). Falls back to the
  ``reflection_summary`` when no event qualifies.
  """
  for event in reversed(reflection_events):
    ev_type = str(getattr(event, "type", "") or "")
    if ev_type != "message.received":
      continue
    text = str(getattr(event, "text", "") or getattr(event, "summary", "") or "")
    if not text.strip():
      continue
    collapsed = compact_question_text(text, limit=600)
    if not collapsed:
      continue
    matches = re.findall(r"([^?]{8,260}\?)", collapsed)
    if matches:
      return compact_question_text(matches[-1], limit=240)
    for marker in (
      "please provide",
      "can you provide",
      "could you provide",
      "what is",
      "which",
      "need ",
      "missing ",
    ):
      if marker in collapsed.lower():
        return compact_question_text(collapsed, limit=240)

  summary = compact_question_text(reflection_summary, limit=240)
  if "?" in summary:
    return summary
  return ""


def latest_received_text(reflection_events: list[Any]) -> str:
  """Return the most recent non-empty ``message.received`` text (truncated)."""
  for event in reversed(reflection_events):
    ev_type = str(getattr(event, "type", "") or "")
    if ev_type != "message.received":
      continue
    text = str(getattr(event, "text", "") or getattr(event, "summary", "") or "")
    if not text.strip():
      continue
    return compact_question_text(text, limit=320)
  return ""


__all__ = [
  "normalize_prompt_text",
  "looks_like_autopilot_generated_prompt",
  "looks_like_explicit_intake_text",
  "compact_question_text",
  "extract_needs_input_question",
  "latest_received_text",
]
