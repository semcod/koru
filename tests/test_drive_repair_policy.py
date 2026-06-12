from __future__ import annotations

from types import SimpleNamespace

from koru.autopilot.drive_repair_policy import decide_drive_repair_reaction


def _status(**kwargs):
    defaults = {
        "ready": False,
        "plugins_connected": False,
        "plugins_compatible": False,
        "hypotheses": [
            SimpleNamespace(id="vscodium.plugin.not_connected"),
        ],
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_drive_repair_policy_falls_back_when_plugin_missing() -> None:
    decision = decide_drive_repair_reaction(_status(), require_plugin=False)

    assert decision.fallback_to_direct is True
    assert decision.action == "direct_fallback"
    assert "vscodium.plugin.not_connected" in decision.reason


def test_drive_repair_policy_honors_require_plugin() -> None:
    decision = decide_drive_repair_reaction(_status(), require_plugin=True)

    assert decision.fallback_to_direct is False
    assert decision.action == "manual_reconnect_required"
    assert "require_plugin=true" in decision.reason


def test_drive_repair_policy_counts_recent_direct_fallbacks() -> None:
    event = SimpleNamespace(
        payload={"actions": ["drive reaction: switch to local direct injection"]},
    )

    decision = decide_drive_repair_reaction(
        _status(plugins_connected=True, plugins_compatible=False),
        require_plugin=False,
        recent_events=[event, event],
    )

    assert decision.fallback_to_direct is True
    assert decision.recent_direct_fallbacks == 2
    assert "recent_direct_fallbacks=2" in decision.reason


def test_drive_repair_policy_skips_direct_when_semantic_blocked() -> None:
    reply = {
        "ok": False,
        "backend": "semantic_required",
        "message": "refusing blind keyboard/OS-injector fallback on Wayland for JetBrains",
    }
    decision = decide_drive_repair_reaction(
        _status(),
        require_plugin=False,
        drive_reply=reply,
    )

    assert decision.fallback_to_direct is False
    assert decision.action == "semantic_required"
    assert "semantic drive required" in decision.reason
