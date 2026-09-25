"""Focused regression tests for ``koru.autonomous.argv_config``.

The submodule owns the argv-configuration responsibility (maintenance
normalization, auto-mode option collection, pipeline/replace-existing flags
and ``--web`` consumption) extracted from the historical ``koru.autonomous``
facade in ticket-185. These tests pin its behavior and the facade re-export
contract.
"""

from __future__ import annotations

import argparse

import koru.autonomous as autonomous_facade
from koru.autonomous.argv_config import (
    _apply_auto_pipeline_flags,
    _apply_replace_existing_flags,
    _configure_auto_mode_args,
    _consume_web_flag,
    _normalize_autonomous_argv,
)


class TestConsumeWebFlag:
    def test_strips_web_flag(self) -> None:
        assert _consume_web_flag(["up", "--web"]) == (["up"], True)

    def test_no_web_resets_and_strips_both(self) -> None:
        assert _consume_web_flag(["up", "--web", "--no-web"]) == (["up"], False)

    def test_no_flags_leaves_argv_untouched(self) -> None:
        assert _consume_web_flag(["up"]) == (["up"], False)

    def test_last_flag_wins(self) -> None:
        assert _consume_web_flag(["--no-web", "up", "--web", "--cycle", "2"]) == (
            ["up", "--cycle", "2"],
            True,
        )


class TestNormalizeAutonomousArgv:
    def test_empty_argv_defaults_to_up(self) -> None:
        assert _normalize_autonomous_argv([]) == ["up"]

    def test_maintenance_actions_pass_through(self) -> None:
        argv = ["doctor", "--project", "/tmp/p"]
        assert _normalize_autonomous_argv(argv) == argv

    def test_bare_action_gets_up_prefix(self) -> None:
        assert _normalize_autonomous_argv(["--max-cycles", "1"]) == [
            "up",
            "--max-cycles",
            "1",
        ]

    def test_safe_up_expands_compat_profile(self) -> None:
        normalized = _normalize_autonomous_argv(["safe-up", "--project", "/tmp/p"])
        assert normalized[0] == "up"
        assert "--no-autopilot" in normalized
        assert "--max-cycles" in normalized
        assert normalized[-1] == "/tmp/p"


class TestConfigureAutoModeArgs:
    def test_collects_user_options_for_up(self) -> None:
        options, argv = _configure_auto_mode_args(
            ["up", "--max-cycles", "2"],
            None,
            True,
        )
        assert "--max-cycles" in options
        assert argv[0] == "up"
        assert "--max-cycles" in argv
        assert "2" in argv

    def test_non_up_argv_returned_unchanged(self) -> None:
        options, argv = _configure_auto_mode_args(["doctor"], None, True)
        assert options == set()
        assert argv == ["doctor"]


class TestApplyAutoPipelineFlags:
    def test_enabled_when_auto_up_and_env_set(self, monkeypatch) -> None:
        monkeypatch.setenv("KORU_AUTO_PIPELINE", "1")
        args = argparse.Namespace(action="up")
        _apply_auto_pipeline_flags(args, invoked_as_auto=True)
        assert args._auto_pipeline_enabled is True

    def test_disabled_without_auto_invocation(self, monkeypatch) -> None:
        monkeypatch.setenv("KORU_AUTO_PIPELINE", "1")
        args = argparse.Namespace(action="up")
        _apply_auto_pipeline_flags(args, invoked_as_auto=False)
        assert args._auto_pipeline_enabled is False

    def test_disabled_for_non_up_action(self, monkeypatch) -> None:
        monkeypatch.setenv("KORU_AUTO_PIPELINE", "true")
        args = argparse.Namespace(action="doctor")
        _apply_auto_pipeline_flags(args, invoked_as_auto=True)
        assert args._auto_pipeline_enabled is False


class TestApplyReplaceExistingFlags:
    def test_auto_invocation_defaults_replace_existing(self) -> None:
        args = argparse.Namespace(
            action="up",
            allow_duplicate=False,
            replace_existing=False,
        )
        _apply_replace_existing_flags(args, invoked_as_auto=True)
        assert args.replace_existing is True
        assert args.replace_existing_global is True

    def test_auto_invocation_respects_explicit_choice(self) -> None:
        args = argparse.Namespace(
            action="up",
            allow_duplicate=False,
            replace_existing=False,
        )
        args.replace_existing = False
        _apply_replace_existing_flags(args, invoked_as_auto=True)
        # allow_duplicate=False and replace_existing explicitly False still
        # defaults to True under auto; only allow_duplicate opts out.
        args2 = argparse.Namespace(
            action="up",
            allow_duplicate=True,
            replace_existing=False,
        )
        _apply_replace_existing_flags(args2, invoked_as_auto=True)
        assert args2.replace_existing is False

    def test_non_auto_marks_global_false(self) -> None:
        args = argparse.Namespace(
            action="up",
            allow_duplicate=False,
            replace_existing=False,
        )
        _apply_replace_existing_flags(args, invoked_as_auto=False)
        assert args.replace_existing is False
        assert args.replace_existing_global is False


class TestFacadeReExports:
    def test_facade_reexports_argv_config_api(self) -> None:
        assert autonomous_facade._normalize_autonomous_argv is _normalize_autonomous_argv
        assert autonomous_facade._configure_auto_mode_args is _configure_auto_mode_args
        assert autonomous_facade._apply_auto_pipeline_flags is _apply_auto_pipeline_flags
        assert autonomous_facade._apply_replace_existing_flags is _apply_replace_existing_flags
        assert autonomous_facade._consume_web_flag is _consume_web_flag
