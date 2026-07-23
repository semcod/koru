"""koru's binding to vdisplay.monitors: the KORU_VDISPLAY_SOURCE contract.

The monitor-topology logic moved to vdisplay.monitors on 2026-07-23 (and its
surface-preference tests moved with it, to
vdisplay/tests/test_monitor_surface_preference.py). What stays koru's is the
environment override: koru reads KORU_VDISPLAY_SOURCE and forwards it to
vdisplay as ``explicit_source``. That forwarding is what this file guards.
"""

from __future__ import annotations

from koru.integrations import photo_vql_monitor as m


def _canon(ide: str) -> str:
    return {"pycharm": "jetbrains", "idea": "jetbrains"}.get(ide, ide)


def _probe(names):
    return {
        "monitor_names": list(names),
        "monitors": [{"name": n, "primary": n == names[0]} for n in names],
    }


def test_env_override_is_read_and_forwarded(monkeypatch):
    monkeypatch.setenv("KORU_VDISPLAY_SOURCE", "DP-2")
    probe = _probe(["DP-1", "DP-2"])
    chosen, out = m.resolve_vdisplay_source_for_ide(
        "vscode", canonical_ide=_canon, desktop_probe=lambda **k: probe, probe=probe
    )
    assert chosen == "DP-2"
    assert out["ok"] is True


def test_without_env_the_ide_default_applies(monkeypatch):
    monkeypatch.delenv("KORU_VDISPLAY_SOURCE", raising=False)
    probe = _probe(["DP-1", "DP-2"])
    chosen, _ = m.resolve_vdisplay_source_for_ide(
        "vscode", canonical_ide=_canon, desktop_probe=lambda **k: probe, probe=probe
    )
    assert chosen == "DP-1"


def test_env_override_for_a_disconnected_monitor_fails_closed(monkeypatch):
    monkeypatch.setenv("KORU_VDISPLAY_SOURCE", "HDMI-9")
    probe = _probe(["DP-1"])
    chosen, out = m.resolve_vdisplay_source_for_ide(
        "vscode", canonical_ide=_canon, desktop_probe=lambda **k: probe, probe=probe
    )
    assert chosen == "HDMI-9"
    assert out["ok"] is False


def test_mismatch_and_format_hint_are_re_exported():
    assert callable(m.map_capture_monitor_mismatch)
    assert callable(m.format_wayland_vdisplay_operator_hint)
