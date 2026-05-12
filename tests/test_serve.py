"""Tests for ``koru.serve`` — the local dashboard HTTP server.

These tests start the server on an ephemeral port (port=0), hit the
endpoints with ``urllib.request``, and assert the shape of responses.
The handler is bound to a tempdir project so ``build_context`` runs
without touching the real workspace.
"""
from __future__ import annotations

import json
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path

from koru.serve import ServeConfig, build_server


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
            "project: test\n", encoding="utf-8"
        )
        (self.project / ".planfile" / "sprints" / "current.yaml").write_text(
            "sprint:\n  id: current\n  tickets: {}\n", encoding="utf-8"
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
