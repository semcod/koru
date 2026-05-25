"""Operator-tunable env config readers for autopilot chat-activity logic.

Extracted from ``autonomous_cycle_chat_activity`` (R-CA1) to isolate the
pure environment-variable lookups from the (1000+ LOC) main module that
contains the operational logic. These functions are read live on every
call, never cached, so tests using ``monkeypatch.setenv`` continue to
observe up-to-date values without further changes.

Public name conventions follow the legacy private names so existing
imports/monkeypatches keep working through re-exports in
``autonomous_cycle_chat_activity``.
"""

from __future__ import annotations

import os


def autopilot_redrive_cooldown_seconds() -> float:
  """Operator-tunable cooldown (env: ``KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS``).

  Defaults to 300 s. The autopilot loop must NOT redrive the same
  ``llm-ready`` ticket prompt if a ``message.sent`` or ``message.received``
  event has been logged within this window — that means the IDE-side LLM
  is still working, or just answered, and a re-paste would clobber its
  output. Set to ``0`` (or negative) to disable the new behavior and
  restore the legacy "redrive every cycle" semantics.
  """
  raw = os.environ.get("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "").strip()
  if not raw:
    return 300.0
  try:
    return max(0.0, float(raw))
  except ValueError:
    return 300.0


def autopilot_escalation_cooldown_seconds(base_cooldown: float) -> float:
  """Cooldown applied when the LAST drive was an ``escalation_prompt``.

  Escalations ("Ticket X has been stuck in status 'waiting_input' for N
  cycles…") are explicit nudges aimed at an LLM that has likely already
  asked the user a clarifying question. Hammering the chat with another
  escalation every 30 s actively destroys the dialog: it concatenates new
  text on top of the user's pending reply or scrolls the LLM's question
  out of view. Use ``KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS`` (default
  1800 = 30 min) to give a real human / the IDE-side LLM enough time to
  converge before the next nudge. Falls back to ``base_cooldown`` when set
  to a value below it (cooldown can never shrink below the global one).
  """
  raw = os.environ.get("KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS", "").strip()
  if not raw:
    return max(base_cooldown, 1800.0)
  try:
    value = float(raw)
  except ValueError:
    return max(base_cooldown, 1800.0)
  return max(base_cooldown, max(0.0, value))


def llm_reflection_summary_max_age_seconds() -> float:
  raw = os.environ.get("KORU_LLM_REFLECTION_SUMMARY_MAX_AGE_SECONDS", "").strip()
  if not raw:
    return 1800.0
  try:
    return max(0.0, float(raw))
  except ValueError:
    return 1800.0


def llm_needs_input_ticket_enabled() -> bool:
  raw = os.environ.get("KORU_LLM_NEEDS_INPUT_TICKET", "1").strip().lower()
  return raw not in {"0", "false", "no", "off"}


def llm_needs_input_ticket_queue_name() -> str:
  raw = os.environ.get("KORU_LLM_NEEDS_INPUT_TICKET_QUEUE", "").strip()
  return raw or "operator"


def llm_needs_input_ticket_priority() -> str:
  raw = os.environ.get("KORU_LLM_NEEDS_INPUT_TICKET_PRIORITY", "").strip()
  return raw or "high"


def llm_needs_input_heuristic_enabled() -> bool:
  raw = os.environ.get("KORU_LLM_NEEDS_INPUT_HEURISTIC", "1").strip().lower()
  return raw not in {"0", "false", "no", "off"}


def chat_intake_ticket_enabled() -> bool:
  raw = os.environ.get("KORU_AUTOPILOT_CHAT_INTAKE_TICKET", "1").strip().lower()
  return raw not in {"0", "false", "no", "off"}


__all__ = [
  "autopilot_redrive_cooldown_seconds",
  "autopilot_escalation_cooldown_seconds",
  "llm_reflection_summary_max_age_seconds",
  "llm_needs_input_ticket_enabled",
  "llm_needs_input_ticket_queue_name",
  "llm_needs_input_ticket_priority",
  "llm_needs_input_heuristic_enabled",
  "chat_intake_ticket_enabled",
]
