"""Tests for ``koru.serve`` — the local dashboard HTTP server.

These tests start the server on an ephemeral port (port=0), hit the
endpoints with ``urllib.request``, and assert the shape of responses.
The handler is bound to a tempdir project so ``build_context`` runs
without touching the real workspace.
"""

from __future__ import annotations

import errno
import json
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import yaml

from koru.serve import (
    ServeConfig,
    _cmdline_suggests_koru_serve_from_bytes,
    bind_serve_server,
    build_server,
    read_serve_endpoint,
    start_serve_background,
    write_serve_endpoint_file,
)
from koruapi.dashboard_tickets import bulk_waiting_input_action


def _minimal_planfile_project() -> tuple[tempfile.TemporaryDirectory, Path]:
    tmp = tempfile.TemporaryDirectory()
    project = Path(tmp.name)
    (project / ".planfile" / "sprints").mkdir(parents=True)
    (project / ".planfile" / "config.yaml").write_text("project: test\n", encoding="utf-8")
    (project / ".planfile" / "sprints" / "current.yaml").write_text(
        "sprint:\n  id: current\n  tickets: {}\n",
        encoding="utf-8",
    )
    return tmp, project


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start(project: Path, port: int) -> ThreadingHTTPServer:
    config = ServeConfig(
        project=project,
        host="127.0.0.1",
        port=port,
        open_browser=False,
    )
    server = build_server(config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Wait briefly so the listener is accepting.
    for _ in range(50):
        try:
            with closing(socket.create_connection(("127.0.0.1", port), 0.1)):
                break
        except OSError:
            time.sleep(0.02)
    return server


def _get(port: int, path: str) -> tuple[int, str, str]:
    url = f"http://127.0.0.1:{port}{path}"
    with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310
        body = resp.read().decode("utf-8")
        content_type = resp.headers.get("Content-Type", "")
        return resp.status, content_type, body


def _post_json(port: int, path: str, payload: dict[str, object]) -> tuple[int, str, str]:
    url = f"http://127.0.0.1:{port}{path}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
        text = resp.read().decode("utf-8")
        content_type = resp.headers.get("Content-Type", "")
        return resp.status, content_type, text


class TestServe(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        # Minimal markers so build_context returns a non-error brief.
        (self.project / ".planfile" / "sprints").mkdir(parents=True)
        (self.project / ".planfile" / "config.yaml").write_text(
            "project: test\n",
            encoding="utf-8",
        )
        (self.project / ".planfile" / "sprints" / "current.yaml").write_text(
            "sprint:\n  id: current\n  tickets: {}\n",
            encoding="utf-8",
        )
        self.port = _free_port()
        self.server = _start(self.project, self.port)

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._tmp.cleanup()

    def test_health_endpoint(self) -> None:
        status, ctype, body = _get(self.port, "/health")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        self.assertEqual(json.loads(body), {"ok": True})

    def test_mesh_grid_and_frames_endpoints(self) -> None:
        from korumesh.envelope import sign_envelope
        from korumesh.store import clear_vision_frames, remember_envelope

        clear_vision_frames()
        key = b"serve-mesh-grid-key-32-bytes!!!"
        remember_envelope(
            sign_envelope(
                peer_from="host-a",
                peer_to="*",
                topic="vision/frame",
                mime="image/png; monitor=2; w=432; h=768; nw=2160; nh=3840; output=DP-3",
                payload=b"\x89PNG",
                key=key,
                envelope_id="host-a:vision:2",
            )
        )
        status, ctype, body = _get(self.port, "/api/mesh/frames")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        self.assertEqual(len(payload["frames"]), 1)
        frame = payload["frames"][0]
        self.assertEqual(frame["peer_from"], "host-a")
        self.assertEqual(frame["mime"], "image/png")
        self.assertEqual(frame["monitor"], 2)
        self.assertEqual(frame["width"], 432)
        self.assertEqual(frame["native_width"], 2160)
        self.assertEqual(frame["native_height"], 3840)
        self.assertEqual(frame["output"], "DP-3")

        status, ctype, body = _get(self.port, "/grid")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn("/api/mesh/frames", body)
        clear_vision_frames()

    def test_dashboard_html_served_on_root(self) -> None:
        status, ctype, body = _get(self.port, "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn("koru dashboard", body)
        # The HTML must reference the JSON endpoint it polls.
        self.assertIn("/api/context", body)
        self.assertIn("view-tabs", body)
        self.assertIn('href="/grid"', body)
        self.assertIn("searchParams", body)
        self.assertIn("tab", body)
        self.assertIn("project", body)
        self.assertIn("change", body)

    def test_dashboard_endpoint_lists_lan_state_projects_and_ides(self) -> None:
        status, ctype, body = _get(self.port, "/api/dashboard")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        self.assertEqual(payload["default_project"], str(self.project.resolve()))
        self.assertIn(f"http://127.0.0.1:{self.port}/", payload["urls"])
        self.assertTrue(any(row["path"] == str(self.project.resolve()) for row in payload["projects"]))
        self.assertTrue(any(row["id"] == "auto" for row in payload["ides"]))

    def test_api_config_get_and_post_persist_dashboard_settings(self) -> None:
        status, ctype, body = _get(self.port, "/api/config")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        self.assertEqual(payload["config"]["project"], str(self.project.resolve()))
        self.assertFalse(payload["exists"])

        status, _, body = _post_json(
            self.port,
            "/api/config",
            {
                "workspace": str(self.project.parent),
                "ide": "windsurf",
                "queue_name": "ops",
                "serve": {
                    "host": "0.0.0.0",
                    "port": 9013,
                    "lan": True,
                    "auto_port": True,
                },
            },
        )
        self.assertEqual(status, 200)
        saved_payload = json.loads(body)
        self.assertTrue(saved_payload["saved"])
        self.assertTrue(saved_payload["exists"])
        saved = json.loads((self.project / ".koru" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["ide"], "windsurf")
        self.assertEqual(saved["queue_name"], "ops")
        self.assertEqual(saved["serve"]["port"], 9013)
        self.assertTrue(saved["serve"]["lan"])

    def test_api_context_returns_brief(self) -> None:
        status, ctype, body = _get(self.port, "/api/context")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        # The brief always carries these top-level keys regardless of
        # ticket state — they are the contract the dashboard relies on.
        self.assertIn("project", payload)
        self.assertIn("policy", payload)
        self.assertIn("environment", payload)

    def test_api_handoff_returns_markdown(self) -> None:
        status, ctype, body = _get(self.port, "/api/handoff")
        self.assertEqual(status, 200)
        self.assertIn("text/markdown", ctype)
        self.assertIn("# koru handoff", body)
        # Dashboard section must remain in the brief.
        self.assertIn("Dashboard", body)

    def test_api_topology_returns_components_and_pipelines(self) -> None:
        status, ctype, body = _get(self.port, "/api/topology")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        self.assertIn("components", payload)
        self.assertIn("pipelines", payload)
        self.assertIn("regix", payload["components"])
        self.assertIn("idle-diagnostics", payload["pipelines"])

    def test_api_topology_post_persists_toggle(self) -> None:
        status, ctype, body = _post_json(
            self.port,
            "/api/topology",
            {
                "components": {"redsl": True},
                "pipelines": {"gate:wup": False},
            },
        )
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        self.assertTrue(payload["components"]["redsl"]["enabled"])
        self.assertFalse(payload["pipelines"]["gate:wup"]["enabled"])

        status2, _, body2 = _get(self.port, "/api/topology")
        self.assertEqual(status2, 200)
        payload2 = json.loads(body2)
        self.assertTrue(payload2["components"]["redsl"]["enabled"])
        self.assertFalse(payload2["pipelines"]["gate:wup"]["enabled"])

    def test_api_topology_post_rejects_empty_update(self) -> None:
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/topology",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as exc_ctx:
            urllib.request.urlopen(req, timeout=5)  # noqa: S310
        self.assertEqual(exc_ctx.exception.code, 400)

    def test_unknown_path_returns_404(self) -> None:
        url = f"http://127.0.0.1:{self.port}/does-not-exist"
        try:
            urllib.request.urlopen(url, timeout=5)  # noqa: S310
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 404)
        else:
            self.fail("expected HTTPError 404")

    def test_api_create_ticket_accepts_selected_ide(self) -> None:
        status, ctype, body = _post_json(
            self.port,
            "/api/tickets/create",
            {
                "description": "ship LAN dashboard controls",
                "title": "LAN dashboard controls",
                "priority": "high",
                "ide": "windsurf",
                "queue_name": "ops",
            },
        )
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        self.assertEqual(payload["project"], str(self.project.resolve()))
        self.assertEqual(payload["ide"], "windsurf")

        data = yaml.safe_load((self.project / ".planfile" / "sprints" / "current.yaml").read_text())
        ticket = data["sprint"]["tickets"][payload["ticket_id"]]
        self.assertEqual(ticket["priority"], "high")
        self.assertEqual(ticket["execution"]["queue"], "ops")
        self.assertEqual(ticket["source"]["context"]["ide"], "windsurf")

    def test_api_ticket_update_and_reorder_mutate_current_sprint(self) -> None:
        sprint_path = self.project / ".planfile" / "sprints" / "current.yaml"
        sprint_path.write_text(
            """
sprint:
  id: current
  tickets:
    PLF-001:
      id: PLF-001
      name: First
      priority: normal
      execution:
        queue: default
      history: []
    PLF-002:
      id: PLF-002
      name: Second
      priority: low
      execution:
        queue: default
      history: []
""".lstrip(),
            encoding="utf-8",
        )

        status, _, body = _post_json(
            self.port,
            "/api/tickets/update",
            {"ticket_id": "PLF-001", "priority": "critical", "queue_name": "lane-a"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["changed"])

        status, _, body = _post_json(
            self.port,
            "/api/tickets/reorder",
            {"ticket_id": "PLF-002", "direction": "up"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["changed"])

        data = yaml.safe_load(sprint_path.read_text(encoding="utf-8"))
        tickets = data["sprint"]["tickets"]
        self.assertEqual(list(tickets), ["PLF-002", "PLF-001"])
        self.assertEqual(tickets["PLF-001"]["priority"], "critical")
        self.assertEqual(tickets["PLF-001"]["execution"]["queue"], "lane-a")
        self.assertTrue(tickets["PLF-001"]["history"])


class TestServeAutoPort(unittest.TestCase):
    def test_endpoint_file_includes_lan_urls(self) -> None:
        tmp, project = _minimal_planfile_project()
        try:
            cfg = ServeConfig(
                project=project,
                host="0.0.0.0",
                port=8765,
                open_browser=False,
                lan=True,
            )
            with mock.patch("koruapi.dashboard_state.local_lan_addresses", return_value=["192.168.1.50"]):
                write_serve_endpoint_file(cfg)
            data = read_serve_endpoint(project)
            self.assertIsNotNone(data)
            assert data is not None
            self.assertTrue(data["lan"])
            self.assertIn("http://localhost:8765/", data["urls"])
            self.assertIn("http://192.168.1.50:8765/", data["urls"])
        finally:
            tmp.cleanup()

    def test_auto_port_skips_busy_port(self) -> None:
        tmp, project = _minimal_planfile_project()
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            blocker.bind(("127.0.0.1", 0))
            busy = blocker.getsockname()[1]
            blocker.listen(1)
            cfg = ServeConfig(
                project=project,
                host="127.0.0.1",
                port=busy,
                open_browser=False,
                auto_port=True,
            )
            server, actual, requested = bind_serve_server(cfg)
            self.assertEqual(requested, busy)
            self.assertNotEqual(actual, busy)
            write_serve_endpoint_file(cfg)
            data = read_serve_endpoint(project)
            self.assertIsNotNone(data)
            assert data is not None
            self.assertEqual(data["port"], actual)
            self.assertEqual(data["http_base"], f"http://127.0.0.1:{actual}")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            time.sleep(0.05)
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)
        finally:
            blocker.close()
            tmp.cleanup()

    def test_without_auto_port_busy_raises(self) -> None:
        tmp, project = _minimal_planfile_project()
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            blocker.bind(("127.0.0.1", 0))
            busy = blocker.getsockname()[1]
            blocker.listen(1)
            cfg = ServeConfig(
                project=project,
                host="127.0.0.1",
                port=busy,
                open_browser=False,
                auto_port=False,
            )
            with self.assertRaises(OSError):
                bind_serve_server(cfg)
        finally:
            blocker.close()
            tmp.cleanup()

    def test_port_zero_updates_config_and_endpoint(self) -> None:
        tmp, project = _minimal_planfile_project()
        try:
            cfg = ServeConfig(
                project=project,
                host="127.0.0.1",
                port=0,
                open_browser=False,
                auto_port=False,
            )
            server, actual, requested = bind_serve_server(cfg)
            self.assertEqual(requested, 0)
            self.assertGreater(actual, 0)
            self.assertEqual(cfg.port, actual)
            write_serve_endpoint_file(cfg)
            data = read_serve_endpoint(project)
            self.assertIsNotNone(data)
            assert data is not None
            self.assertEqual(data["port"], actual)
            self.assertEqual(data["http_base"], f"http://127.0.0.1:{actual}")
            server.server_close()
        finally:
            tmp.cleanup()


def test_cmdline_suggests_koru_serve_from_bytes() -> None:
    assert _cmdline_suggests_koru_serve_from_bytes(
        b"/usr/bin/python\x00-m\x00koru.cli\x00serve\x00",
    )
    assert _cmdline_suggests_koru_serve_from_bytes(b"/opt/koru\x00serve\x00")
    assert not _cmdline_suggests_koru_serve_from_bytes(b"/usr/bin/koru\x00mcp-serve\x00")


def test_bulk_waiting_input_action_approve() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        tickets = [{"id": "A-1", "status": "waiting_input"}]
        ok = subprocess.CompletedProcess(args=["planfile"], returncode=0, stdout="", stderr="")
        with mock.patch("koruapi.dashboard_tickets.list_tickets", return_value=tickets):
            with mock.patch("koruapi.dashboard_tickets.planfile_command", return_value=ok) as cmd:
                out = bulk_waiting_input_action(
                    project,
                    ticket_ids=["A-1"],
                    action="approve",
                    reason="",
                )
        assert out["ok"] is True
        assert out["applied"][0]["ok"] is True
        assert cmd.call_count == 3


def test_bulk_waiting_input_action_reject() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        tickets = [{"id": "A-2", "status": "waiting_input"}]
        ok = subprocess.CompletedProcess(args=["planfile"], returncode=0, stdout="", stderr="")
        with mock.patch("koruapi.dashboard_tickets.list_tickets", return_value=tickets):
            with mock.patch("koruapi.dashboard_tickets.planfile_command", return_value=ok) as cmd:
                out = bulk_waiting_input_action(
                    project,
                    ticket_ids=["A-2"],
                    action="reject",
                    reason="manual reject",
                )
        assert out["ok"] is True
        assert out["applied"][0]["action"] == "reject"
        assert out["applied"][0]["ok"] is True
        assert cmd.call_count == 1
    assert not _cmdline_suggests_koru_serve_from_bytes(b"/usr/bin/python\x00-m\x00http.server\x00")


class TestServeReplacePrior(unittest.TestCase):
    def test_bind_retries_after_prior_listener_stopped(self) -> None:
        tmp, project = _minimal_planfile_project()
        try:
            port = _free_port()
            cfg = ServeConfig(
                project=project,
                host="127.0.0.1",
                port=port,
                open_browser=False,
                auto_port=False,
            )
            built = {"n": 0}
            real_build = build_server

            def fake_build(c: ServeConfig) -> ThreadingHTTPServer:
                built["n"] += 1
                if built["n"] == 1:
                    raise OSError(errno.EADDRINUSE, "Address already in use")
                return real_build(c)

            from koru import serve as serve_mod

            with (
                mock.patch.object(serve_mod, "build_server", side_effect=fake_build),
                mock.patch.object(
                    serve_mod,
                    "_try_stop_prior_koru_serve_listener",
                    return_value=True,
                ),
            ):
                srv, actual, req = serve_mod.bind_serve_server(cfg)
            self.assertEqual(built["n"], 2)
            self.assertEqual(actual, port)
            self.assertEqual(req, port)
            srv.server_close()
        finally:
            tmp.cleanup()


def test_start_serve_background_shutdown() -> None:
    tmp, project = _minimal_planfile_project()
    try:
        cfg = ServeConfig(
            project=project,
            host="127.0.0.1",
            port=0,
            open_browser=False,
            auto_port=True,
        )
        srv, th = start_serve_background(cfg, log=lambda _msg: None)
        port = int(srv.server_address[1])
        status, _, _ = _get(port, "/health")
        assert status == 200
        srv.shutdown()
        srv.server_close()
        th.join(timeout=3.0)
        assert not th.is_alive()
    finally:
        tmp.cleanup()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
