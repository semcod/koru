"""Fast E2E coverage for the observation mesh CLI paths."""

from __future__ import annotations

import asyncio
import io
import threading
from pathlib import Path
from unittest import mock
from unittest.mock import AsyncMock

import pytest

from koru.cli import main
from korumesh.envelope import verify_envelope
from korumesh.store import clear_vision_frames, list_vision_frames, remember_envelope
from korumesh.transport import _relay_client
from koruobserve.paths import pidfile
from koruvision.capture import VisionFrame

websockets = pytest.importorskip("websockets")


def _run_main(*argv: str) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with mock.patch("sys.argv", ["koru", *argv]):
        with mock.patch("sys.stdout", new=out):
            with mock.patch("sys.stderr", new=err):
                try:
                    code = main()
                except SystemExit as exc:
                    code = exc.code if exc.code is not None else 0
    return int(code), out.getvalue(), err.getvalue()


class _RelayThread:
    def __init__(self, *, key: bytes) -> None:
        self.key = key
        self.ready = threading.Event()
        self.url = ""
        self.error: BaseException | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop: asyncio.Future[None] | None = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> str:
        self._thread.start()
        assert self.ready.wait(5), "relay did not start"
        if self.error is not None:
            raise self.error
        return self.url

    def stop(self) -> None:
        if self._loop is not None and self._stop is not None and not self._stop.done():
            self._loop.call_soon_threadsafe(self._stop.set_result, None)
        self._thread.join(5)

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._serve())
        except BaseException as exc:  # noqa: BLE001
            self.error = exc
            self.ready.set()
        finally:
            loop.close()

    async def _serve(self) -> None:
        peers: set[object] = set()
        async with websockets.serve(
            lambda ws: _relay_client(ws, key=self.key, peers=peers, on_frame=remember_envelope),
            "127.0.0.1",
            0,
        ) as server:
            port = server.sockets[0].getsockname()[1]
            self.url = f"ws://127.0.0.1:{port}"
            self._stop = asyncio.Future()
            self.ready.set()
            await self._stop


def test_mesh_cli_init_publish_reaches_relay_store(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    code, out, err = _run_main("mesh", "init", "--project", str(project))
    assert code == 0, err
    assert "key ready" in out

    key_file = project / ".koru" / "keys" / "mesh.hmac"
    key = key_file.read_bytes().strip()
    clear_vision_frames()
    relay = _RelayThread(key=key)
    try:
        url = relay.start()
        code, out, err = _run_main(
            "mesh",
            "publish",
            "--url",
            url,
            "--from-peer",
            "host-a",
            "--topic",
            "vision/frame",
            "--mime",
            "image/png",
            "--payload",
            "fake-png",
            "--key-file",
            str(key_file),
            "--listen-seconds",
            "0.1",
        )
    finally:
        relay.stop()

    assert code == 0, err
    assert "published topic=vision/frame" in out
    frames = list_vision_frames()
    assert len(frames) == 1
    assert frames[0].peer_from == "host-a"
    assert frames[0].payload == b"fake-png"
    assert verify_envelope(frames[0], key)
    clear_vision_frames()


def test_vision_agent_cli_publishes_captured_frame_to_mesh(tmp_path: Path) -> None:
    project = tmp_path / "project"
    key_file = project / ".koru" / "keys" / "mesh.hmac"
    key_file.parent.mkdir(parents=True)
    key_file.write_bytes(b"vision-agent-e2e-key-32-bytes!!")
    (project / ".koru" / "config.json").write_text(
        """
{
  "vision": {"enabled": true, "interval_seconds": 1},
  "mesh": {
    "enabled": true,
    "relay_url": "ws://127.0.0.1:9999",
    "peer_id": "host-b",
    "psk_path": ".koru/keys/mesh.hmac"
  }
}
""".strip(),
        encoding="utf-8",
    )
    frame = VisionFrame(
        frame_id="frame-1",
        monitor_id=0,
        captured_at="2026-05-22T12:00:00+00:00",
        mime="image/png",
        width=2,
        height=2,
        payload=b"\x89PNG",
    )

    with mock.patch("koruvision.agent.capture_once", return_value=frame):
        with mock.patch("koruvision.mesh.publish_envelope", new_callable=AsyncMock) as publish:
            code, out, err = _run_main(
                "vision",
                "--project",
                str(project),
                "agent",
                "--monitor",
                "0",
                "--max-frames",
                "1",
                "--interval",
                "0.01",
            )

    assert code == 0, err
    assert "frame=frame-1" in out
    publish.assert_called_once()
    mesh_url, envelope = publish.call_args.args
    assert mesh_url == "ws://127.0.0.1:9999"
    assert envelope.peer_from == "host-b"
    assert envelope.topic == "vision/frame"
    assert envelope.payload == b"\x89PNG"
    assert verify_envelope(envelope, b"vision-agent-e2e-key-32-bytes!!")


def test_observe_cli_roundtrip_through_main_dispatch(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    next_pid = iter(range(30001, 30010))
    spawned: list[tuple[str, list[str]]] = []

    def _fake_spawn(name: str, args: list[str], project_root: Path) -> int:
        pid = next(next_pid)
        spawned.append((name, args))
        pidfile(project_root, name).parent.mkdir(parents=True, exist_ok=True)
        pidfile(project_root, name).write_text(f"{pid}\n", encoding="utf-8")
        return pid

    monkeypatch.setattr("koruobserve.cli._require_observe_runtime", lambda: None)
    monkeypatch.setattr("koruobserve.lifecycle._spawn", _fake_spawn)
    monkeypatch.setattr("koruobserve.lifecycle._is_alive", lambda pid: True)
    monkeypatch.setattr("koruobserve.lifecycle.os.kill", lambda pid, sig: None)

    code, out, err = _run_main(
        "observe",
        "up",
        "--project",
        str(project),
        "--relay-port",
        "0",
        "--dashboard-port",
        "0",
    )
    assert code == 0, err
    assert "koru observe: up" in out
    assert [name for name, _ in spawned] == ["relay", "vision", "dashboard"]
    assert not out.split("relay", 1)[1].splitlines()[0].endswith(":0")

    code, out, err = _run_main("observe", "status", "--project", str(project))
    assert code == 0, err
    assert '"alive": true' in out

    code, out, err = _run_main("observe", "grid", "--project", str(project))
    assert code == 0, err
    assert out.strip().endswith("/grid")

    code, out, err = _run_main("observe", "down", "--project", str(project))
    assert code == 0, err
    assert "dashboard stopped=True" in out
    assert not pidfile(project, "relay").exists()
