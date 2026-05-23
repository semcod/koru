from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from koru.cqrs.event_store import JsonlEventStore
from koru.tasks import create_nl_task


class TestNaturalLanguageTask(unittest.TestCase):
    def test_creates_planfile_ticket_from_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            created = create_nl_task(
                project,
                "Dodaj feature importu raportów",
                queue_name="c2004-refactor",
                priority="high",
            )

            self.assertEqual(created.ticket_id, "PLF-001")
            data = yaml.safe_load(created.path.read_text(encoding="utf-8"))
            ticket = data["sprint"]["tickets"]["PLF-001"]
            self.assertEqual(ticket["name"], "Dodaj feature importu raportów")
            self.assertEqual(ticket["priority"], "high")
            self.assertEqual(ticket["executor"]["kind"], "human")
            self.assertEqual(ticket["execution"]["queue"], "c2004-refactor")
            self.assertEqual(ticket["execution"]["state"], "ready")
            self.assertIn("llm-ready", ticket["labels"])
            self.assertEqual(ticket["inputs"]["prompt"], "Dodaj feature importu raportów")
            self.assertEqual(ticket["history"][0]["action"], "created")

    def test_increments_next_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            first = create_nl_task(project, "First task")
            second = create_nl_task(project, "Second task")

            self.assertEqual(first.ticket_id, "PLF-001")
            self.assertEqual(second.ticket_id, "PLF-002")
            config = yaml.safe_load((project / ".planfile" / "config.yaml").read_text())
            self.assertEqual(config["next_id"], 3)

    def test_rejects_empty_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                create_nl_task(Path(tmp), "   ")

    def test_scaffold_overrides_ticket_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            created = create_nl_task(
                project,
                "Integrate adapter flow",
                scaffold={
                    "source_tool": "koru-cli-tool-adapter",
                    "source_context": {"tool_id": "gemini-cli"},
                    "labels": ["adapter-scaffold", "tool-gemini-cli"],
                    "executor_kind": "shell",
                    "executor_mode": "automatic",
                    "prompt_suffix": "[TOOL ADAPTER SCAFFOLD]",
                    "inputs": {"tool_id": "gemini-cli", "adapter_executor_hint": "shell"},
                },
            )
            data = yaml.safe_load(created.path.read_text(encoding="utf-8"))
            ticket = data["sprint"]["tickets"][created.ticket_id]
            self.assertEqual(ticket["source"]["tool"], "koru-cli-tool-adapter")
            self.assertEqual(ticket["source"]["context"]["tool_id"], "gemini-cli")
            self.assertIn("adapter-scaffold", ticket["labels"])
            self.assertEqual(ticket["executor"]["kind"], "shell")
            self.assertEqual(ticket["executor"]["mode"], "automatic")
            self.assertIn("[TOOL ADAPTER SCAFFOLD]", ticket["inputs"]["prompt"])
            self.assertEqual(ticket["inputs"]["tool_id"], "gemini-cli")

    def test_reuses_existing_ticket_with_same_dedupe_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            first = create_nl_task(
                project,
                "Split autonomous module",
                scaffold={
                    "source_tool": "prefact",
                    "source_context": {"dedupe_key": "semcod:code2llm:refactor:src/koru/autonomous.py"},
                    "title": "Split god module: src/koru/autonomous.py",
                },
            )
            data = yaml.safe_load(first.path.read_text(encoding="utf-8"))
            data["sprint"]["tickets"][first.ticket_id]["status"] = "done"
            first.path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

            second = create_nl_task(
                project,
                "Same issue reported by another plugin",
                scaffold={
                    "source_tool": "prefact",
                    "source_context": {"dedupe_key": "semcod:code2llm:refactor:src/koru/autonomous.py"},
                    "title": "Split god module: src/koru/autonomous.py",
                },
            )

            self.assertTrue(second.reused)
            self.assertEqual(second.ticket_id, first.ticket_id)
            config = yaml.safe_load((project / ".planfile" / "config.yaml").read_text())
            self.assertEqual(config["next_id"], 2)


def test_create_nl_task_persists_domain_event(tmp_path: Path) -> None:
    created = create_nl_task(tmp_path, "Persist CQRS task")

    events = JsonlEventStore(tmp_path / ".koru" / "event-store.jsonl").all_events(context="tasks")

    assert created.ticket_id == "PLF-001"
    assert [event.event_type for event in events] == ["tasks.created"]
    assert events[0].aggregate_id == created.ticket_id
