from __future__ import annotations

import asyncio
import json
import unittest

from koru.watch import format_queue_event, watch_planfile_events


class FakeWebSocket:
    def __init__(self, messages: list[dict]) -> None:
        self.messages = [json.dumps(message) for message in messages]

    async def __aenter__(self) -> FakeWebSocket:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def recv(self) -> str:
        return self.messages.pop(0)


class TestWatch(unittest.TestCase):
    def test_format_queue_event_for_execution_change(self) -> None:
        event = {
            "type": "ticket.execution.changed",
            "action": "claim",
            "ticket_id": "PLF-001",
            "ticket": {
                "name": "Bootstrap project",
                "execution": {
                    "state": "ready",
                    "assigned_to": "koru-shell",
                },
            },
        }

        line = format_queue_event(event)

        self.assertEqual(
            line,
            "ticket.execution.changed | claim | PLF-001 | Bootstrap project | "
            "state=ready | assigned_to=koru-shell",
        )

    def test_format_management_event(self) -> None:
        event = {
            "type": "management.event",
            "source": "koru",
            "tool": "koru.queue",
            "action": "completed",
            "status": "dry_run",
            "queue": "c2004-runtime",
            "message": "PLF-074",
        }

        line = format_queue_event(event)

        self.assertEqual(
            line,
            "management.event | koru.queue | completed | dry_run | queue=c2004-runtime | PLF-074",
        )

    def test_watch_planfile_events_prints_compact_lines(self) -> None:
        messages = [
            {"ok": True, "message": "planfile DSL ready. Type 'help' for commands."},
            {
                "type": "ticket.execution.changed",
                "action": "complete",
                "ticket_id": "PLF-002",
                "ticket": {"name": "Run shell", "execution": {"state": "done"}},
            },
        ]
        printed: list[str] = []

        async def connector(_url: str) -> FakeWebSocket:
            return FakeWebSocket(messages)

        seen = asyncio.run(
            watch_planfile_events(
                "ws://example/ws",
                max_events=2,
                printer=printed.append,
                connector=connector,
            ),
        )

        self.assertEqual(seen, 2)
        self.assertEqual(
            printed,
            [
                "connected: planfile DSL ready. Type 'help' for commands.",
                "ticket.execution.changed | complete | PLF-002 | Run shell | state=done",
            ],
        )


if __name__ == "__main__":
    unittest.main()
