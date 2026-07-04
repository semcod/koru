"""Source-monitor resolution: chat panel on a secondary monitor vs editor."""

from __future__ import annotations

from koru.integrations import photo_vql_monitor as m


def _canon(ide: str) -> str:
    return {"pycharm": "jetbrains", "idea": "jetbrains"}.get(ide, ide)


def _probe(*, surfaces, primary="HDMI-1", best=None):
    monitors = [
        {"name": "HDMI-1", "primary": primary == "HDMI-1"},
        {"name": "DP-1", "primary": primary == "DP-1"},
        {"name": "DP-2", "primary": primary == "DP-2"},
    ]
    probe = {
        "monitors": monitors,
        "monitor_names": ["HDMI-1", "DP-1", "DP-2"],
        "ide_surfaces": surfaces,
    }
    if best is not None:
        probe["ide_surface_best"] = best
    return probe


def test_editor_on_primary_chat_on_dp_prefers_dp():
    # PyCharm editor ranks best on HDMI-1 (primary); Qoder chat panel on DP-1.
    probe = _probe(
        surfaces=[
            {"ide_hint": "jetbrains", "display_name": "PyCharm", "monitor_name": "HDMI-1"},
            {"ide_hint": "jetbrains", "display_name": "PyCharm", "monitor_name": "DP-1"},
        ],
        best={"ide_hint": "jetbrains", "monitor_name": "HDMI-1"},
    )
    assert m._surface_preferred_monitor(probe, canon="jetbrains") == "DP-1"


def test_single_monitor_ide_keeps_editor_monitor():
    probe = _probe(
        surfaces=[
            {"ide_hint": "jetbrains", "display_name": "PyCharm", "monitor_name": "HDMI-1"},
        ],
        best={"ide_hint": "jetbrains", "monitor_name": "HDMI-1"},
    )
    assert m._surface_preferred_monitor(probe, canon="jetbrains") == "HDMI-1"


def test_toolbox_surface_ignored_for_multimonitor_decision():
    # A Toolbox launcher on DP-2 must not be treated as a chat panel.
    probe = _probe(
        surfaces=[
            {"ide_hint": "jetbrains", "display_name": "PyCharm", "monitor_name": "HDMI-1"},
            {"ide_hint": "jetbrains", "display_name": "JetBrains Toolbox", "monitor_name": "DP-2"},
        ],
        best={"ide_hint": "jetbrains", "monitor_name": "HDMI-1"},
    )
    assert m._surface_preferred_monitor(probe, canon="jetbrains") == "HDMI-1"


def test_chat_on_primary_dp_not_preferred_over_itself():
    # Editor already on the only DP surface → nothing else to prefer.
    probe = _probe(
        surfaces=[
            {"ide_hint": "jetbrains", "display_name": "PyCharm", "monitor_name": "DP-1"},
        ],
        primary="DP-1",
        best={"ide_hint": "jetbrains", "monitor_name": "DP-1"},
    )
    assert m._surface_preferred_monitor(probe, canon="jetbrains") == "DP-1"


def test_no_best_falls_back_to_first_surface_then_secondary_dp():
    probe = _probe(
        surfaces=[
            {"ide_hint": "jetbrains", "display_name": "PyCharm", "monitor_name": "HDMI-1"},
            {"ide_hint": "jetbrains", "display_name": "PyCharm", "monitor_name": "DP-1"},
        ],
    )
    assert m._surface_preferred_monitor(probe, canon="jetbrains") == "DP-1"


def test_ide_surface_monitors_dedupes_and_skips_toolbox():
    probe = _probe(
        surfaces=[
            {"ide_hint": "jetbrains", "display_name": "PyCharm", "monitor_name": "HDMI-1"},
            {"ide_hint": "jetbrains", "display_name": "PyCharm", "monitor_name": "HDMI-1"},
            {"ide_hint": "jetbrains", "display_name": "PyCharm", "monitor_name": "DP-1"},
            {"ide_hint": "jetbrains", "display_name": "JetBrains Toolbox", "monitor_name": "DP-2"},
        ],
    )
    assert m._ide_surface_monitors(probe, canon="jetbrains") == ["HDMI-1", "DP-1"]
