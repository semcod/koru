from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from koru.agents import (
    agent_lane_environment,
    autopilot_backend_for_agent_id,
    detect_agent_environment,
    detect_agent_options,
    format_agent_lane_exports,
    normalize_agent_lane_id,
    select_agent,
)


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
            with (
                patch("shutil.which", return_value=None),
                patch.dict(
                    os.environ,
                    {"OPENROUTER_API_KEY": "test"},
                    clear=True,
                ),
            ):
                env = detect_agent_environment(Path(tmp))

            openrouter = next(agent for agent in env["llm_agents"] if agent["id"] == "openrouter")
            self.assertTrue(openrouter["available"])
            self.assertFalse(openrouter["launchable"])
            self.assertEqual(openrouter["autopilot_backend"], "headless")

    def test_select_agent_prefers_launchable_when_noninteractive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:

            def fake_which(command: str) -> str | None:
                return f"/usr/bin/{command}" if command == "claude" else None

            with patch("shutil.which", side_effect=fake_which):
                agents = detect_agent_options(Path(tmp))

            selected = select_agent(agents, interactive=False)
            self.assertIsNotNone(selected)
            self.assertEqual(selected.id, "claude-code")

    def test_detects_gemini_cli_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:

            def fake_which(command: str) -> str | None:
                return "/usr/bin/gemini" if command == "gemini" else None

            with patch("shutil.which", side_effect=fake_which):
                agents = detect_agent_options(Path(tmp))

            gemini = next(agent for agent in agents if agent.id == "gemini-cli")
            self.assertTrue(gemini.available)
            self.assertTrue(gemini.launchable)
            self.assertEqual(gemini.command, "/usr/bin/gemini")

    def test_select_agent_can_pick_gemini_when_only_launchable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:

            def fake_which(command: str) -> str | None:
                return "/usr/bin/gemini" if command == "gemini" else None

            with patch("shutil.which", side_effect=fake_which):
                agents = detect_agent_options(Path(tmp))

            selected = select_agent(agents, interactive=False)
            self.assertIsNotNone(selected)
            self.assertEqual(selected.id, "gemini-cli")

    def test_detects_cline_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:

            def fake_which(command: str) -> str | None:
                return "/usr/bin/cline" if command == "cline" else None

            with patch("shutil.which", side_effect=fake_which):
                agents = detect_agent_options(Path(tmp))

            cline = next(agent for agent in agents if agent.id == "cline")
            self.assertTrue(cline.available)
            self.assertTrue(cline.launchable)
            self.assertEqual(cline.command, "/usr/bin/cline")

    def test_select_agent_can_pick_cline_when_only_launchable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:

            def fake_which(command: str) -> str | None:
                return "/usr/bin/cline" if command == "cline" else None

            with patch("shutil.which", side_effect=fake_which):
                agents = detect_agent_options(Path(tmp))

            selected = select_agent(agents, interactive=False)
            self.assertIsNotNone(selected)
            self.assertEqual(selected.id, "cline")

    def test_agent_lane_environment_cursor(self) -> None:
        env = agent_lane_environment("cursor")
        self.assertEqual(env["KORU_AUTOPILOT_INSTANCE"], "cursor")
        self.assertEqual(env["KORU_AUTOPILOT_IDE"], "cursor")
        self.assertEqual(env["KORU_AUTOPILOT_BACKEND"], "plugin_socket")
        self.assertIn("koru-cursor", env["KORU_SUGGESTED_QUEUE_ACTOR"])

    def test_normalize_agent_lane_id_strips_garbage(self) -> None:
        self.assertEqual(normalize_agent_lane_id("Cursor : A"), "cursor---a")

    def test_format_agent_lane_exports_is_shell_safe(self) -> None:
        env = {"KORU_X": "a'b"}
        out = format_agent_lane_exports(env)
        self.assertIn("export KORU_X=", out)
        self.assertIn("a'\"'\"'b", out)

    def test_detects_qwen_code_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:

            def fake_which(command: str) -> str | None:
                return "/usr/bin/qwen-code" if command == "qwen-code" else None

            with patch("shutil.which", side_effect=fake_which):
                agents = detect_agent_options(Path(tmp))

            qwen = next(agent for agent in agents if agent.id == "qwen-code")
            self.assertTrue(qwen.available)
            self.assertTrue(qwen.launchable)
            self.assertEqual(qwen.command, "/usr/bin/qwen-code")

    def test_select_agent_can_pick_qwen_when_only_launchable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:

            def fake_which(command: str) -> str | None:
                return "/usr/bin/qwen" if command == "qwen" else None

            with patch("shutil.which", side_effect=fake_which):
                agents = detect_agent_options(Path(tmp))

            selected = select_agent(agents, interactive=False)
            self.assertIsNotNone(selected)
            self.assertEqual(selected.id, "qwen-code")

    def test_detects_opencode_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:

            def fake_which(command: str) -> str | None:
                return "/usr/bin/opencode" if command == "opencode" else None

            with patch("shutil.which", side_effect=fake_which):
                agents = detect_agent_options(Path(tmp))

            opencode = next(agent for agent in agents if agent.id == "opencode")
            self.assertTrue(opencode.available)
            self.assertTrue(opencode.launchable)
            self.assertEqual(opencode.command, "/usr/bin/opencode")

    def test_select_agent_can_pick_opencode_when_only_launchable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:

            def fake_which(command: str) -> str | None:
                return "/usr/bin/opencode" if command == "opencode" else None

            with patch("shutil.which", side_effect=fake_which):
                agents = detect_agent_options(Path(tmp))

            selected = select_agent(agents, interactive=False)
            self.assertIsNotNone(selected)
            self.assertEqual(selected.id, "opencode")


class TestAgentLaneEnv(unittest.TestCase):
    def test_qwen_lane_env_defaults(self) -> None:
        env = agent_lane_environment("qwen-code")
        self.assertEqual(env["KORU_AUTOPILOT_IDE"], "auto")
        self.assertEqual(env["KORU_AUTOPILOT_BACKEND"], "cursor_cli")
        self.assertEqual(env["KORU_SUGGESTED_QUEUE_ACTOR"], "koru-qwen-code")

    def test_opencode_lane_env_defaults(self) -> None:
        env = agent_lane_environment("opencode")
        self.assertEqual(env["KORU_AUTOPILOT_IDE"], "auto")
        self.assertEqual(env["KORU_AUTOPILOT_BACKEND"], "cursor_cli")
        self.assertEqual(env["KORU_SUGGESTED_QUEUE_ACTOR"], "koru-opencode")


class TestAutopilotBackendForLane(unittest.TestCase):
    def test_backend_matrix(self) -> None:
        self.assertEqual(autopilot_backend_for_agent_id("windsurf"), "plugin_socket")
        self.assertEqual(autopilot_backend_for_agent_id("openrouter"), "headless")
        self.assertEqual(autopilot_backend_for_agent_id("codex"), "cursor_cli")
