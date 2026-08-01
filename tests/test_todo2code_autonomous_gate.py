"""Focused tests runnable without Koru's display-dependent global fixture."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from koru.queue.ticket_templates import hydrate_todo2code_ticket
from koru.queue.todo2code_gate import (
    infer_project_verify_command,
    infer_project_verify_commands,
    resolve_project_verify_commands,
)


class Todo2codeAutonomousGateTest(unittest.TestCase):
    def test_python_project_gets_pytest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            (project / "tests").mkdir()
            command = infer_project_verify_command(project)
            self.assertIsNotNone(command)
            self.assertEqual(command[-3:], ["-m", "pytest", "-q"])

    def test_package_prefers_verify_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "package.json").write_text(
                json.dumps({"scripts": {"test": "node --test", "verify": "npm run check"}}),
                encoding="utf-8",
            )
            self.assertEqual(infer_project_verify_command(project), ["npm", "run", "verify"])

    def test_all_declared_completion_commands_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "koru.yaml").write_text(
                "when:\n  before_complete_ticket:\n    commands:\n"
                "      - python -m ruff check src\n"
                "      - python -m pytest -q\n",
                encoding="utf-8",
            )
            self.assertEqual(
                infer_project_verify_commands(project),
                [
                    ["sh", "-lc", "python -m ruff check src"],
                    ["sh", "-lc", "python -m pytest -q"],
                ],
            )

    def test_docker_project_refuses_undeclared_host_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")
            (project / "compose.yml").write_text("services: {}\n", encoding="utf-8")
            (project / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            (project / "tests").mkdir()
            commands, error = resolve_project_verify_commands(project)
            self.assertEqual(commands, [])
            self.assertIn("host fallback is forbidden", error or "")

    def test_docker_project_wraps_every_declared_container_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")
            (project / "compose.yml").write_text(
                "services:\n  app:\n    image: python:3.12\n", encoding="utf-8"
            )
            (project / "koru.yaml").write_text(
                "when:\n  before_complete_ticket:\n    commands:\n      - host-only\n"
                "queue:\n  todo2code:\n    verification:\n      runtime: docker\n"
                "      service: app\n      commands:\n        - python -m pytest -q\n",
                encoding="utf-8",
            )
            commands, error = resolve_project_verify_commands(project)
            self.assertIsNone(error)
            self.assertEqual(
                commands,
                [[
                    "docker", "compose", "-f", "compose.yml", "run", "--rm",
                    "--entrypoint", "sh", "app", "-lc", "python -m pytest -q",
                ]],
            )

    def test_hydration_adds_gate_caps_and_retry_model(self) -> None:
        ticket = {
            "labels": ["todo2code"],
            "files": ["src/a.py"],
            "execution": {"attempt": 1},
            "inputs": {"llm_model": "openrouter/cheap/model"},
            "source": {
                "tool": "koru-todo2code-discovery",
                "context": {"diagnostic_ids": ["DIAG-deadbeef"]},
            },
        }
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {
                "KORU_TODO2CODE_BIN": str(Path(tmp) / "t2c"),
                "KORU_TODO2CODE_LLM_FALLBACK_MODEL": "openrouter/strong/model",
            },
            clear=False,
        ):
            binary = Path(tmp) / "t2c"
            binary.write_text("", encoding="utf-8")
            hydrated = hydrate_todo2code_ticket(ticket, Path(tmp))

        self.assertEqual(hydrated["inputs"]["llm_model"], "openrouter/strong/model")
        self.assertEqual(hydrated["inputs"]["llm_max_tokens"], 4000)
        self.assertEqual(hydrated["inputs"]["llm_timeout_seconds"], 300)
        self.assertTrue(hydrated["inputs"]["patch_mode"])
        self.assertIn("koru.queue.todo2code_gate", hydrated["inputs"]["verify_command"])
        self.assertIn("PYTHONPATH=", hydrated["inputs"]["verify_command"])
        self.assertNotIn("PYTHONPATH=src ", hydrated["inputs"]["verify_command"])
        self.assertIn("type:development-defect", hydrated["labels"])

    def test_hydration_downgrades_uncontracted_legacy_llm_ticket(self) -> None:
        ticket = {
            "labels": ["todo2code"],
            "files": ["src/a.py"],
            "executor": {"kind": "llm", "mode": "automatic"},
            "inputs": {},
        }
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"KORU_TODO2CODE_CONTRACT": ""},
            clear=False,
        ):
            hydrated = hydrate_todo2code_ticket(ticket, Path(tmp))
        self.assertEqual(hydrated["executor"], {"kind": "human", "mode": "interactive"})
        self.assertIn("requires", hydrated["inputs"]["governance_block_reason"])


if __name__ == "__main__":
    unittest.main()
