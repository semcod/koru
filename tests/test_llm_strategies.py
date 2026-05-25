"""Tests for korullm LLM strategies."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from korullm import list_llm_strategy_ids, resolve_active_llm_strategy
from korullm.strategies.ide_chat import IdeChatStrategy


class RegistryTests(unittest.TestCase):
    def test_all_shipped_strategies_registered(self) -> None:
        ids = list_llm_strategy_ids()
        for expected in ("ide_chat", "openai", "anthropic", "ollama", "codex"):
            self.assertIn(expected, ids)

    def test_default_is_ide_chat(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            for key in (
                "KORU_LLM_PROVIDER",
                "KORU_LLM_BACKEND",
                "OPENAI_MODEL",
                "ANTHROPIC_MODEL",
                "OLLAMA_MODEL",
                "CODEX_HOME",
            ):
                os.environ.pop(key, None)
            strategy = resolve_active_llm_strategy()
        self.assertEqual(strategy.id, "ide_chat")

    def test_openai_env_selects_gpt_strategy(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_MODEL": "gpt-4"}, clear=False):
            strategy = resolve_active_llm_strategy()
        self.assertEqual(strategy.id, "openai")


class IdeChatAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.strategy = IdeChatStrategy()

    def test_input_busy_skips_cooldown(self) -> None:
        assessment = self.strategy.assess_drive_failure(
            {"verification": "input_busy"},
            attempt=0,
            max_attempts=3,
        )
        self.assertEqual(assessment.kind, "skip_cooldown")

    def test_manual_focus_when_no_candidates(self) -> None:
        assessment = self.strategy.assess_drive_failure(
            {
                "message": "chat input is not focused/open",
                "diagnostics": {"focusOpenCandidates": []},
            },
            attempt=0,
            max_attempts=3,
        )
        self.assertEqual(assessment.kind, "stop_manual_focus")

    def test_submit_retry_before_focus(self) -> None:
        assessment = self.strategy.assess_drive_failure(
            {"verification": "submit_unverified", "message": "focus unrelated"},
            attempt=0,
            max_attempts=3,
        )
        self.assertEqual(assessment.kind, "retry_submit")
        self.assertEqual(assessment.warn_banner, "submit")

    def test_focus_retry(self) -> None:
        assessment = self.strategy.assess_drive_failure(
            {"message": "chat input is not focused"},
            attempt=0,
            max_attempts=3,
        )
        self.assertEqual(assessment.kind, "retry_focus")


class CodexStrategyTests(unittest.TestCase):
    def test_manual_focus_becomes_retry_for_codex(self) -> None:
        from korullm.strategies.codex import CodexStrategy

        strategy = CodexStrategy()
        assessment = strategy.assess_drive_failure(
            {
                "message": "chat input is not focused/open",
                "diagnostics": {"focusOpenCandidates": []},
            },
            attempt=0,
            max_attempts=3,
        )
        self.assertEqual(assessment.kind, "retry_focus")


if __name__ == "__main__":
    unittest.main()
