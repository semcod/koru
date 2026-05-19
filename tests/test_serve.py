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

from koru.serve import (
    ServeConfig,
    _bulk_waiting_input_action,
    _cmdline_suggests_koru_serve_from_bytes,
    bind_serve_server,
    build_server,
    read_serve_endpoint,
    start_serve_background,
    write_serve_endpoint_file,
)


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

    def test_dashboard_html_served_on_root(self) -> None:
        status, ctype, body = _get(self.port, "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn("koru dashboard", body)
        # The HTML must reference the JSON endpoint it polls.
        self.assertIn("/api/context", body)

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


class TestServeAutoPort(unittest.TestCase):
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
        with mock.patch("koru.serve._list_tickets", return_value=tickets):
            with mock.patch("koru.serve.planfile_command", return_value=ok) as cmd:
                out = _bulk_waiting_input_action(
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
        with mock.patch("koru.serve._list_tickets", return_value=tickets):
            with mock.patch("koru.serve.planfile_command", return_value=ok) as cmd:
                out = _bulk_waiting_input_action(
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
