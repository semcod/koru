from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from koru.autopilot import daemon_cli


def test_no_handoff_daemon_keeps_project_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    class FakeDaemon:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        def start(self) -> None:
            return None

        def serve_forever(self) -> None:
            return None

    monkeypatch.setattr(daemon_cli, "AutopilotDaemon", FakeDaemon)
    monkeypatch.setattr(daemon_cli, "autopilot_local_manager_session", lambda **_kwargs: None)
    monkeypatch.setattr(daemon_cli, "start_autopilot_manager_heartbeat", lambda *_a, **_k: None)
    monkeypatch.setattr(daemon_cli, "_stop_heartbeat", lambda *_a, **_k: None)

    from koru.ide_adapters import bridge

    monkeypatch.setattr(bridge, "gc_stale_sockets_for_lane", lambda _socket: [])

    args = argparse.Namespace(
        socket=None,
        idempotent=False,
        project=tmp_path,
        handoff=False,
        handoff_cooldown=2.0,
    )

    rc = daemon_cli.run_daemon_command(
        args,
        default_socket_fn=lambda: tmp_path / "koru-autopilot.sock",
    )

    assert rc == 0
    assert captured["project"] == tmp_path.resolve()
    assert captured["enable_project_handoff"] is False

