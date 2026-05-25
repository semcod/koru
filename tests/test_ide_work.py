"""Tests for IDE work prompts in autonomous mode."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml

from koru.autonomy.ide_work import (
    build_ide_work_prompt,
    extract_ticket_id_from_text,
    fetch_next_open_ticket,
    release_stale_in_progress_tickets,
    resolve_idle_drive_prompt,
    sprint_ticket_status_summary,
)


def _ok(stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


class TestIdeWork(unittest.TestCase):
    def test_fetch_next_open_ticket_sorts_by_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            def runner(cmd, _proj) -> SimpleNamespace:
                self.assertEqual(cmd[:5], ["planfile", "ticket", "list", "--status", "open"])
                return _ok(
                    json.dumps(
                        [
                            {"id": "PLF-2", "status": "open", "priority": "normal", "name": "b"},
                            {"id": "PLF-1", "status": "open", "priority": "critical", "name": "a"},
                        ],
                    ),
                )

            ticket = fetch_next_open_ticket(project, runner=runner)
            assert ticket is not None
            self.assertEqual(ticket["id"], "PLF-1")

    def test_resolve_idle_drive_prompt_uses_ticket_when_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            def runner(cmd, _proj) -> SimpleNamespace:
                return _ok(
                    json.dumps(
                        [
                            {
                                "id": "PLF-99",
                                "status": "open",
                                "priority": "high",
                                "name": "Fix service health",
                                "description": "Repair failing probe",
                            },
                        ],
                    ),
                )

            prompt, kind = resolve_idle_drive_prompt(
                project,
                drive_prompt="continue",
                runner=runner,
            )
            self.assertEqual(kind, "idle_ticket_prompt")
            self.assertIn("PLF-99", prompt)
            self.assertIn("koru_run_ticket", prompt)

    def test_resolve_idle_drive_prompt_skips_drive_when_no_open_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            def runner(_cmd, _proj) -> SimpleNamespace:
                return _ok("[]")

            prompt, kind = resolve_idle_drive_prompt(
                project,
                drive_prompt="continue with the next ticket",
                runner=runner,
            )
            self.assertEqual(kind, "idle_no_ticket")
            self.assertEqual(prompt, "continue with the next ticket")
            self.assertFalse((project / ".planfile" / "sprints" / "current.yaml").exists())

    def test_release_stale_in_progress_reopens_old_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            old = "2020-01-01T00:00:00+00:00"
            updates: list[list[str]] = []

            def runner(cmd, _proj) -> SimpleNamespace:
                if cmd[:5] == ["planfile", "ticket", "list", "--status", "in_progress"]:
                    return _ok(
                        json.dumps(
                            [
                                {
                                    "id": "PLF-7",
                                    "status": "in_progress",
                                    "execution": {"started_at": old},
                                },
                            ],
                        ),
                    )
                updates.append(list(cmd))
                return _ok()

            count = release_stale_in_progress_tickets(
                project,
                stale_minutes=60,
                runner=runner,
            )
            self.assertEqual(count, 1)
            self.assertTrue(
                any(
                    c[:4] == ["planfile", "ticket", "update", "PLF-7"] and "open" in c
                    for c in updates
                ),
            )

    def test_extract_ticket_id_from_text(self) -> None:
        prompt = build_ide_work_prompt(
            {"id": "PLF-42", "name": "X", "description": ""},
            fallback="",
        )
        self.assertEqual(extract_ticket_id_from_text(prompt), "PLF-42")

    def test_build_ide_work_prompt_includes_description(self) -> None:
        prompt = build_ide_work_prompt(
            {"id": "PLF-1", "name": "Test", "description": "Do the thing"},
            fallback="x",
        )
        self.assertIn("PLF-1", prompt)
        self.assertIn("Do the thing", prompt)
        self.assertIn("planfile ticket done PLF-1", prompt)
        self.assertIn("planfile ticket input PLF-1", prompt)
        self.assertIn("planfile ticket fail PLF-1", prompt)

    def test_build_ide_work_prompt_includes_planfile_commands_without_mcp(self) -> None:
        prompt = build_ide_work_prompt(
            {"id": "STARTER-206", "name": "Refactor autonomous"},
            fallback="x",
            include_mcp_hint=False,
        )
        self.assertNotIn("koru_run_ticket", prompt)
        self.assertIn("planfile ticket done STARTER-206", prompt)
        self.assertIn("planfile ticket input STARTER-206", prompt)
        self.assertIn("Do not leave completed IDE work in waiting_input", prompt)

    def test_sprint_ticket_status_summary_counts_by_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".planfile" / "sprints").mkdir(parents=True)
            sprint = {
                "sprint": {
                    "tickets": {
                        "A": {"status": "done"},
                        "B": {"status": "done"},
                        "C": {"status": "open"},
                    },
                },
            }
            (project / ".planfile" / "sprints" / "current.yaml").write_text(
                yaml.dump(sprint),
                encoding="utf-8",
            )
            summary = sprint_ticket_status_summary(project)
            self.assertIn("done=2", summary)
            self.assertIn("open=1", summary)


if __name__ == "__main__":
    unittest.main()
