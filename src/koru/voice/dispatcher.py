"""Natural language and voice command dispatcher for koru."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class VoiceIntent(StrEnum):
    """Categorized intent of a natural language voice command."""

    STOP_LOOP = "stop_loop"
    START_LOOP = "start_loop"
    STATUS_LOOP = "status_loop"
    QUEUE_STATUS = "queue_status"
    TASK_NEXT = "task_next"
    TASK_CLOSE = "task_close"
    TASK_CREATE = "task_create"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ParsedVoiceCommand:
    """Structured representation of a parsed voice or NL command."""

    intent: VoiceIntent
    raw_text: str
    normalized_text: str
    arguments: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


_TICKET_ID_RE = re.compile(r"\b((?:PLF|ticket)-?\d+|\d+)\b", re.IGNORECASE)


def normalize_text(text: str) -> str:
    """Normalize text: strip accents, lowercase, remove punctuation, collapse whitespace."""
    text = text.strip().lower().replace("ł", "l")
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    cleaned = re.sub(r"[^\w\s-]", " ", stripped)
    return re.sub(r"\s+", " ", cleaned).strip()


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings with minimal memory."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if not s2:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def phrase_fuzzy_match(normalized_input: str, target_phrase: str, max_dist: int = 1) -> bool:
    """Return True if target_phrase appears in normalized_input or is within max_dist."""
    if target_phrase in normalized_input:
        return True
    words_in = normalized_input.split()
    target_words = target_phrase.split()
    if len(target_words) == 1 and words_in:
        tw = target_words[0]
        # Never match antonym stems like wlacz vs wylacz
        if tw == "wylacz" and any(w == "wlacz" for w in words_in):
            return False
        if tw == "wlacz" and any(w == "wylacz" for w in words_in):
            return False
        return any(levenshtein_distance(w, tw) <= max_dist for w in words_in)
    return False


class VoiceDispatcher:
    """Dispatcher translating natural language speech to koru actions."""

    _STOP_TRIGGERS = (
        "zatrzymaj petle",
        "zatrzymaj",
        "wylacz koru",
        "wylacz",
        "stop",
        "pause",
        "pauza",
        "halt",
        "przerwij",
    )

    _START_TRIGGERS = (
        "wznow",
        "uruchom",
        "wlacz koru",
        "wlacz",
        "start",
        "resume",
        "start loop",
        "kontynuuj",
        "dalej",
    )

    _STATUS_TRIGGERS = (
        "status petli",
        "stan petli",
        "status koru",
        "stan koru",
        "loop status",
        "jaki jest stan",
        "stan",
        "status",
    )

    _QUEUE_TRIGGERS = (
        "status kolejki",
        "pokaz kolejke",
        "stan kolejki",
        "co w kolejce",
        "ile zadan",
        "kolejka",
        "queue status",
        "list queue",
        "queue",
    )

    _NEXT_TASK_TRIGGERS = (
        "nastepne zadanie",
        "kolejne zadanie",
        "aktualne zadanie",
        "aktywne zadanie",
        "pokaz zadanie",
        "co robisz",
        "current task",
        "next task",
    )

    _CLOSE_TRIGGERS = (
        "zamknij zadanie",
        "zakoncz zadanie",
        "zrobione zadanie",
        "usun zadanie",
        "close task",
        "finish task",
        "complete task",
    )

    _CREATE_TRIGGERS = (
        "dodaj zadanie",
        "utworz zadanie",
        "nowe zadanie",
        "zaplanuj zadanie",
        "add task",
        "create task",
        "new task",
    )

    def parse(self, text: str) -> ParsedVoiceCommand:
        """Parse natural language command text into a ParsedVoiceCommand."""
        normalized = normalize_text(text)
        if not normalized:
            return ParsedVoiceCommand(VoiceIntent.UNKNOWN, text, normalized, confidence=0.0)

        # 1. Close Task Intent
        close_match = self._match_close_task(text, normalized)
        if close_match is not None:
            return close_match

        # 2. Create Task Intent
        create_match = self._match_create_task(text, normalized)
        if create_match is not None:
            return create_match

        # 3. Next Task Intent
        if any(phrase_fuzzy_match(normalized, trig) for trig in self._NEXT_TASK_TRIGGERS):
            return ParsedVoiceCommand(VoiceIntent.TASK_NEXT, text, normalized, confidence=0.95)

        # 4. Queue Status Intent
        if any(phrase_fuzzy_match(normalized, trig) for trig in self._QUEUE_TRIGGERS):
            return ParsedVoiceCommand(VoiceIntent.QUEUE_STATUS, text, normalized, confidence=0.95)

        # 5. Stop Loop Intent
        if any(phrase_fuzzy_match(normalized, trig) for trig in self._STOP_TRIGGERS):
            reason = self._extract_trailing_reason(normalized, self._STOP_TRIGGERS)
            args = {"reason": reason} if reason else {}
            return ParsedVoiceCommand(VoiceIntent.STOP_LOOP, text, normalized, arguments=args, confidence=0.95)

        # 6. Start Loop Intent
        if any(phrase_fuzzy_match(normalized, trig) for trig in self._START_TRIGGERS):
            return ParsedVoiceCommand(VoiceIntent.START_LOOP, text, normalized, confidence=0.95)

        # 7. Loop Status Intent
        if any(phrase_fuzzy_match(normalized, trig) for trig in self._STATUS_TRIGGERS):
            return ParsedVoiceCommand(VoiceIntent.STATUS_LOOP, text, normalized, confidence=0.9)

        return ParsedVoiceCommand(VoiceIntent.UNKNOWN, text, normalized, confidence=0.0)

    def _match_close_task(self, raw: str, normalized: str) -> ParsedVoiceCommand | None:
        matched_trigger = next((trig for trig in self._CLOSE_TRIGGERS if phrase_fuzzy_match(normalized, trig)), None)
        ticket_match = _TICKET_ID_RE.search(raw)
        if matched_trigger or (ticket_match and ("zamknij" in normalized or "zakoncz" in normalized)):
            ticket_id = self._canonical_ticket_id(ticket_match.group(1)) if ticket_match else ""
            return ParsedVoiceCommand(
                VoiceIntent.TASK_CLOSE,
                raw,
                normalized,
                arguments={"ticket_id": ticket_id},
                confidence=0.95 if ticket_id else 0.7,
            )
        return None

    def _match_create_task(self, raw: str, normalized: str) -> ParsedVoiceCommand | None:
        matched_trigger = next((trig for trig in self._CREATE_TRIGGERS if phrase_fuzzy_match(normalized, trig)), None)
        if matched_trigger:
            task_desc = self._extract_after_trigger(raw, matched_trigger)
            return ParsedVoiceCommand(
                VoiceIntent.TASK_CREATE,
                raw,
                normalized,
                arguments={"task_text": task_desc.strip()},
                confidence=0.9,
            )
        return None

    @staticmethod
    def _canonical_ticket_id(raw_id: str) -> str:
        raw_clean = raw_id.upper().replace("TICKET-", "ticket-")
        if raw_clean.isdigit():
            return f"PLF-{int(raw_clean):03d}"
        if raw_clean.startswith("PLF"):
            parts = raw_clean.split("-")
            num = parts[1] if len(parts) > 1 and parts[1].isdigit() else parts[0][3:]
            return f"PLF-{int(num):03d}" if num.isdigit() else raw_clean
        return raw_id

    @staticmethod
    def _extract_trailing_reason(normalized: str, triggers: tuple[str, ...]) -> str:
        for trig in triggers:
            if trig in normalized:
                idx = normalized.find(trig) + len(trig)
                rest = normalized[idx:].strip()
                if rest.startswith("bo ") or rest.startswith("powod ") or rest.startswith("because "):
                    return rest
        return ""

    @staticmethod
    def _extract_after_trigger(raw: str, trigger: str) -> str:
        lower = raw.lower()
        idx = lower.find(trigger)
        if idx != -1:
            return raw[idx + len(trigger):].strip()
        # Fallback to normalized split
        words = raw.split()
        trig_len = len(trigger.split())
        return " ".join(words[trig_len:]) if len(words) > trig_len else raw
