from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from koru.agents import detect_agent_environment, detect_agent_options, select_agent


class TestAgentDetection(unittest.TestCase):
    def test_detects_project_hints_without_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".windsurf").mkdir()
            (project / ".windsurf" / "rules.md").write_text("rules", encoding="utf-8")
            with patch("shutil.which", return_value=None), patch.dict(os.environ, {}, clear=True):
                agents = detect_agent_options(project)

            windsurf = next(agent for agent in agents if agent.id == "windsurf")
            self.assertTrue(windsurf.available)
            self.assertFalse(windsurf.launchable)
            self.assertTrue(windsurf.project_hint)

    def test_detects_openrouter_lane_from_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("shutil.which", return_value=None), patch.dict(
                os.environ, {"OPENROUTER_API_KEY": "test"}, clear=True
            ):
                env = detect_agent_environment(Path(tmp))

            openrouter = next(
                agent for agent in env["llm_agents"] if agent["id"] == "openrouter"
            )
            self.assertTrue(openrouter["available"])
            self.assertFalse(openrouter["launchable"])

    def test_select_agent_prefers_launchable_when_noninteractive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            def fake_which(command: str) -> str | None:
                return f"/usr/bin/{command}" if command == "claude" else None

            with patch("shutil.which", side_effect=fake_which):
                agents = detect_agent_options(Path(tmp))

            selected = select_agent(agents, interactive=False)
            self.assertIsNotNone(selected)
            self.assertEqual(selected.id, "claude-code")
