from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

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
