from __future__ import annotations

from koru.autonomous_plugin import plugin_status_decision
from koruide.ide import canonical_autopilot_ide_id
from koruide.plugin_router import PluginRouter


def test_canonical_autopilot_ide_id_maps_lane_suffix() -> None:
    assert canonical_autopilot_ide_id("cursor-main") == "cursor"
    assert canonical_autopilot_ide_id("windsurf-main") == "windsurf"


def test_plugin_status_decision_accepts_cursor_plugin_for_cursor_main_lane() -> None:
    status = {
        "plugins": [
            {
                "ide": "cursor",
                "version": "0.2.1",
                "buildSha": "abc",
                "protocolVersion": 2,
                "capabilities": ["chat.send"],
            }
        ],
        "expected_plugin_version": "0.2.1",
        "expected_plugin_build_sha": "abc",
    }
    ok, reason = plugin_status_decision(status, "cursor-main")
    assert ok is True
    assert "accepted" in reason


def test_plugin_router_matches_cursor_main_lane_to_cursor_plugin() -> None:
    from dataclasses import dataclass, field

    @dataclass
    class _Sock:
        fd: int

        def fileno(self) -> int:
            return self.fd

    @dataclass
    class _Client:
        fd: int
        role: str = "plugin"
        ide: str | None = "cursor"
        workspace_folders: list[str] = field(default_factory=list)
        sock: _Sock = field(init=False)

        def __post_init__(self) -> None:
            self.sock = _Sock(self.fd)

    client = _Client(1)
    router = PluginRouter({1: client}, drop_client=lambda _c: None)
    assert router.plugin_for("cursor-main") is client
