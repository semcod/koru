"""Command execution engine for parsed voice and NL intents."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from koru.global_control import (
    global_disable,
    global_enable,
    is_globally_disabled,
    read_killswitch_state,
)
from koru.task_io import _read_sprint, _write_yaml
from koru.voice.dispatcher import ParsedVoiceCommand, VoiceIntent


@dataclass(frozen=True)
class VoiceExecutionResult:
    """Outcome of executing a voice command."""

    intent: VoiceIntent
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.value,
            "success": self.success,
            "message": self.message,
            "data": self.data,
        }


class VoiceCommandExecutor:
    """Executes validated voice commands against koru runtime and planfile."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()

    def execute(self, cmd: ParsedVoiceCommand) -> VoiceExecutionResult:
        """Route and execute the parsed command."""
        match cmd.intent:
            case VoiceIntent.STOP_LOOP:
                return self._execute_stop_loop(cmd)
            case VoiceIntent.START_LOOP:
                return self._execute_start_loop(cmd)
            case VoiceIntent.STATUS_LOOP:
                return self._execute_status_loop(cmd)
            case VoiceIntent.QUEUE_STATUS:
                return self._execute_queue_status(cmd)
            case VoiceIntent.TASK_NEXT:
                return self._execute_task_next(cmd)
            case VoiceIntent.TASK_CLOSE:
                return self._execute_task_close(cmd)
            case VoiceIntent.TASK_CREATE:
                return self._execute_task_create(cmd)
            case _:
                return self._execute_unknown(cmd)

    def _execute_stop_loop(self, cmd: ParsedVoiceCommand) -> VoiceExecutionResult:
        reason = cmd.arguments.get("reason") or "voice command"
        path = global_disable(reason)
        return VoiceExecutionResult(
            intent=cmd.intent,
            success=True,
            message="Pętla Koru została zatrzymana (global killswitch aktywny).",
            data={"killswitch_path": str(path), "reason": reason, "disabled": True},
        )

    def _execute_start_loop(self, cmd: ParsedVoiceCommand) -> VoiceExecutionResult:
        res = global_enable()
        msg = (
            "Pętla Koru została wznowiona (global killswitch wyłączony)."
            if res
            else "Pętla Koru jest już aktywna (brak aktywnego killswitcha)."
        )
        return VoiceExecutionResult(
            intent=cmd.intent,
            success=True,
            message=msg,
            data={"was_disabled": res, "disabled": False},
        )

    def _execute_status_loop(self, cmd: ParsedVoiceCommand) -> VoiceExecutionResult:
        disabled = is_globally_disabled()
        state = read_killswitch_state() if disabled else {}
        status_text = "ZATRZYMANA" if disabled else "AKTYWNA"
        msg = f"Status pętli Koru: {status_text}."
        if disabled and state.get("reason"):
            msg += f" Powód: {state['reason']} (od {state.get('disabled_at', 'nieznany')})"
        return VoiceExecutionResult(
            intent=cmd.intent,
            success=True,
            message=msg,
            data={"status": status_text, "disabled": disabled, "state": state},
        )

    def _execute_queue_status(self, cmd: ParsedVoiceCommand) -> VoiceExecutionResult:
        sprint_path = self.project_root / ".planfile" / "sprints" / "current.yaml"
        if not sprint_path.exists():
            return VoiceExecutionResult(
                intent=cmd.intent,
                success=True,
                message="Kolejka zadań: brak pliku current.yaml (kolejka pusta).",
                data={"total": 0, "tickets": {}},
            )
        data = _read_sprint(sprint_path, sprint="current")
        tickets = data.get("sprint", {}).get("tickets", {})
        open_tickets = [t for t in tickets.values() if t.get("status") in ("open", "ready", "in_progress")]
        in_prog = [t for t in open_tickets if t.get("status") == "in_progress"]

        top_names = [f"[{t.get('id', '?')}] {t.get('name', 'Brak nazwy')}" for t in open_tickets[:5]]
        lines = [
            f"Kolejka zadań: łącznie {len(tickets)} zadań, {len(open_tickets)} oczekujących / w toku."
        ]
        if in_prog:
            lines.append(f"W toku: {in_prog[0].get('id')} - {in_prog[0].get('name')}")
        if top_names:
            lines.append("Najbliższe: " + ", ".join(top_names))

        return VoiceExecutionResult(
            intent=cmd.intent,
            success=True,
            message="\n".join(lines),
            data={
                "total": len(tickets),
                "open_count": len(open_tickets),
                "in_progress_count": len(in_prog),
                "top_tickets": [t.get("id") for t in open_tickets[:5]],
            },
        )

    def _execute_task_next(self, cmd: ParsedVoiceCommand) -> VoiceExecutionResult:
        sprint_path = self.project_root / ".planfile" / "sprints" / "current.yaml"
        if not sprint_path.exists():
            return VoiceExecutionResult(
                intent=cmd.intent,
                success=False,
                message="Brak zadań w kolejce planfile.",
            )
        data = _read_sprint(sprint_path, sprint="current")
        tickets = data.get("sprint", {}).get("tickets", {})
        open_tickets = [t for t in tickets.values() if t.get("status") in ("in_progress", "ready", "open")]
        if not open_tickets:
            return VoiceExecutionResult(
                intent=cmd.intent,
                success=True,
                message="Brak aktywnych zadań w kolejce.",
            )
        # Prioritize in_progress over ready over open
        open_tickets.sort(key=lambda t: (0 if t.get("status") == "in_progress" else 1, t.get("id", "")))
        next_t = open_tickets[0]
        tid = next_t.get("id", "?")
        tname = next_t.get("name", "Bez nazwy")
        tstatus = next_t.get("status", "open")
        tprio = next_t.get("priority", "normal")
        msg = f"Aktualne zadanie: [{tid}] {tname} (status: {tstatus}, priorytet: {tprio})"
        return VoiceExecutionResult(
            intent=cmd.intent,
            success=True,
            message=msg,
            data={"ticket": next_t},
        )

    def _execute_task_close(self, cmd: ParsedVoiceCommand) -> VoiceExecutionResult:
        ticket_id = cmd.arguments.get("ticket_id")
        if not ticket_id:
            return VoiceExecutionResult(
                intent=cmd.intent,
                success=False,
                message="Nie podano identyfikatora zadania do zamknięcia (np. 'zamknij zadanie PLF-001').",
            )
        sprint_path = self.project_root / ".planfile" / "sprints" / "current.yaml"
        if not sprint_path.exists():
            return VoiceExecutionResult(
                intent=cmd.intent,
                success=False,
                message=f"Nie znaleziono pliku sprintu current.yaml, nie można zamknąć zadania {ticket_id}.",
            )
        data = _read_sprint(sprint_path, sprint="current")
        tickets = data.get("sprint", {}).get("tickets", {})
        if ticket_id not in tickets:
            # Fuzzy match ID
            matched_id = next((k for k in tickets if k.lower() == ticket_id.lower() or ticket_id in k), None)
            if not matched_id:
                return VoiceExecutionResult(
                    intent=cmd.intent,
                    success=False,
                    message=f"Zadanie {ticket_id} nie zostało znalezione w kolejce.",
                )
            ticket_id = matched_id

        tickets[ticket_id]["status"] = "closed"
        _write_yaml(sprint_path, data)
        return VoiceExecutionResult(
            intent=cmd.intent,
            success=True,
            message=f"Zadanie {ticket_id} zostało pomyślnie zamknięte.",
            data={"ticket_id": ticket_id, "status": "closed"},
        )

    def _execute_task_create(self, cmd: ParsedVoiceCommand) -> VoiceExecutionResult:
        task_text = cmd.arguments.get("task_text", "").strip()
        if not task_text:
            return VoiceExecutionResult(
                intent=cmd.intent,
                success=False,
                message="Nie podano opisu zadania (np. 'dodaj zadanie zoptymalizować zapytania sql').",
            )
        from koru.tasks import create_nl_task

        created = create_nl_task(self.project_root, task_text)
        return VoiceExecutionResult(
            intent=cmd.intent,
            success=True,
            message=f"Utworzono nowe zadanie: [{created.id}] {created.name}",
            data={"id": created.id, "name": created.name, "path": created.path},
        )

    def _execute_unknown(self, cmd: ParsedVoiceCommand) -> VoiceExecutionResult:
        msg = (
            f"Nie rozpoznano polecenia głosowego: '{cmd.raw_text}'.\n"
            "Dostępne polecenia:\n"
            "  - 'zatrzymaj pętlę' / 'wyłącz' (zatrzymuje autonomiczny cykl Koru)\n"
            "  - 'wznów' / 'włącz' (wznawia cykl Koru)\n"
            "  - 'status' (sprawdza stan pętli)\n"
            "  - 'status kolejki' / 'pokaż kolejkę' (wyświetla listę zadań)\n"
            "  - 'następne zadanie' (pokazuje aktualnie realizowane zadanie)\n"
            "  - 'zamknij zadanie <id>' (zamyka zadanie w kolejce)\n"
            "  - 'dodaj zadanie <opis>' (tworzy nowe zadanie z opisu NL)"
        )
        return VoiceExecutionResult(
            intent=cmd.intent,
            success=False,
            message=msg,
            data={"raw_text": cmd.raw_text, "normalized": cmd.normalized_text},
        )
