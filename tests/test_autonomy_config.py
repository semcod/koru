"""Tests for unified autoloop configuration model."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from koru.autonomy import AutonomyConfig


def test_autonomy_config_defaults():
    """Test that AutonomyConfig has sensible defaults."""
    config = AutonomyConfig()

    assert config.actor == "koru-shell"
    assert config.queue_name == ""
    assert config.use_all_queues is False
    assert config.max_iterations == 50
    assert config.max_cycles == 0  # infinite
    assert config.sleep_seconds == 120
    assert config.enable_scan is True
    assert config.ticket_sources == "queue"
    assert config.enable_autopilot_drive is True
    assert config.autopilot_action == "drive"
    assert config.autopilot_ide == "auto"
    assert config.autopilot_submit is True
    assert config.enable_idle_diagnostics is False
    assert config.idle_diagnostics_profile == "off"


def test_autonomy_config_from_env():
    """Test that AutonomyConfig can be created from environment variables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_vars = {
            "PROJECT": tmpdir,
            "ACTOR": "test-actor",
            "QUEUE_NAME": "test-queue",
            "USE_ALL_QUEUES": "true",
            "MAX_ITERATIONS": "100",
            "MAX_CYCLES": "5",
            "SLEEP_SECONDS": "60",
            "ENABLE_SCAN": "false",
            "TICKET_SOURCES": "all",
            "ENABLE_AUTOPILOT_DRIVE": "false",
            "AUTOPILOT_ACTION": "handoff",
            "AUTOPILOT_IDE": "windsurf",
            "ENABLE_IDLE_DIAGNOSTICS": "true",
            "IDLE_DIAGNOSTICS_PROFILE": "full",
            "STRICT_DIAGNOSTICS": "true",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = AutonomyConfig.from_env()

            assert config.project == Path(tmpdir)
            assert config.actor == "test-actor"
            assert config.queue_name == "test-queue"
            assert config.use_all_queues is True
            assert config.max_iterations == 100
            assert config.max_cycles == 5
            assert config.sleep_seconds == 60
            assert config.enable_scan is False
            assert config.ticket_sources == "all"
            assert config.enable_autopilot_drive is False
            assert config.autopilot_action == "handoff"
            assert config.autopilot_ide == "windsurf"
            assert config.enable_idle_diagnostics is True
            assert config.idle_diagnostics_profile == "full"
            assert config.strict_diagnostics is True


def test_autonomy_config_from_env_defaults():
    """Test that from_env uses defaults when vars are missing."""
    with patch.dict(os.environ, {}, clear=True):
        config = AutonomyConfig.from_env()

        # Should match class defaults
        assert config.actor == "koru-shell"
        assert config.max_iterations == 50
        assert config.enable_scan is True


def test_autonomy_config_from_env_actor_name_fallback():
    """Test that ACTOR_NAME falls back to ACTOR."""
    with patch.dict(os.environ, {"ACTOR_NAME": "fallback-actor"}, clear=True):
        config = AutonomyConfig.from_env()
        assert config.actor == "fallback-actor"


def test_autonomy_config_ticket_sources_valid():
    """Test that valid ticket_sources values are accepted."""
    for source in ["queue", "scan", "all"]:
        config = AutonomyConfig(ticket_sources=source)  # type: ignore
        assert config.ticket_sources == source


def test_autonomy_config_autopilot_action_valid():
    """Test that valid autopilot_action values are accepted."""
    for action in ["drive", "handoff", "off"]:
        config = AutonomyConfig(autopilot_action=action)  # type: ignore
        assert config.autopilot_action == action


def test_autonomy_config_idle_diagnostics_profile_valid():
    """Test that valid idle_diagnostics_profile values are accepted."""
    for profile in ["off", "quick", "full"]:
        config = AutonomyConfig(idle_diagnostics_profile=profile)  # type: ignore
        assert config.idle_diagnostics_profile == profile


def test_autonomy_config_stagnation_control_fields():
    """Test stagnation control configuration fields."""
    config = AutonomyConfig(
        autopilot_skip_statuses="waiting_input,blocked",
        autopilot_skip_drive_idle_streak=2,
        backoff_on_stagnation=True,
        max_sleep_seconds=1800,
        scan_skip_if_clean=True,
        scan_skip_after=3,
    )

    assert config.autopilot_skip_statuses == "waiting_input,blocked"
    assert config.autopilot_skip_drive_idle_streak == 2
    assert config.backoff_on_stagnation is True
    assert config.max_sleep_seconds == 1800
    assert config.scan_skip_if_clean is True
    assert config.scan_skip_after == 3


def test_autonomy_config_from_env_idle_streak() -> None:
    """AUTOPILOT_SKIP_DRIVE_IDLE_STREAK parses as a non-negative int."""
    with patch.dict(os.environ, {"AUTOPILOT_SKIP_DRIVE_IDLE_STREAK": "4"}, clear=True):
        config = AutonomyConfig.from_env()
    assert config.autopilot_skip_drive_idle_streak == 4


def test_autonomy_config_diag_state_dir_default():
    """Test that diag_state_dir has correct default."""
    config = AutonomyConfig()
    assert config.diag_state_dir == Path(".planfile/.koru/autoloop-diag")
