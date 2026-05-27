from __future__ import annotations

from koru.autonomous_operator import _plugin_blocker_line
from koru.autonomous_plugin import plugin_skip_code, plugin_status_decision


def test_plugin_skip_code_classifies_version_mismatch() -> None:
    assert (
        plugin_skip_code(
            "ide=vscodium version=0.1.63 blocked: connected autopilot "
            "plugin version mismatch: connected=0.1.63 expected=0.1.64"
        )
        == "plugin_version_mismatch"
    )


def test_plugin_skip_code_classifies_build_mismatch() -> None:
    assert (
        plugin_skip_code(
            "ide=vscodium version=0.2.7 blocked: connected autopilot "
            "plugin build mismatch: connected=old expected=new"
        )
        == "plugin_version_mismatch"
    )


def test_plugin_skip_code_classifies_empty_plugin_list_as_not_connected() -> None:
    assert plugin_skip_code("daemon status plugin list is empty") == "plugin_not_connected"


def test_plugin_blocker_line_includes_recovery_action() -> None:
    line = _plugin_blocker_line(
        "connected autopilot plugin version mismatch: connected=0.1.63 expected=0.1.64",
        "vscodium",
    )

    assert "blocked_by=plugin_version_mismatch" in line
    assert "ide=vscodium" in line
    assert "reload IDE window" in line


def test_plugin_blocker_line_for_empty_list_is_reload_first() -> None:
    line = _plugin_blocker_line("daemon status plugin list is empty", "vscodium")

    assert "blocked_by=plugin_not_connected" in line
    assert "Developer: Reload Window" in line
    assert "koru: Connect autopilot daemon" in line


def test_plugin_status_decision_uses_stale_rejection_when_plugin_list_empty() -> None:
    ready, reason = plugin_status_decision(
        {
            "plugins": [],
            "rejected_plugins": [
                {
                    "ide": "vscodium",
                    "version": "0.1.77",
                    "expected_version": "0.1.78",
                    "message": (
                        "connected autopilot plugin version mismatch: "
                        "connected=0.1.77 expected=0.1.78"
                    ),
                },
            ],
        },
        "vscodium",
    )

    assert ready is False
    assert "plugin version mismatch" in reason
    assert "connected=0.1.77 expected=0.1.78" in reason
    assert plugin_skip_code(reason) == "plugin_version_mismatch"
