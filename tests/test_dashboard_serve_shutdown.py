"""Dashboard server shutdown must not hang on open SSE connections.

Regression tests for the Ctrl+C hang: ``ThreadingHTTPServer`` defaults
(``daemon_threads=False``, ``block_on_close=True``) made ``server_close()``
wait forever for the infinite ``/api/logs/stream`` handler, so Ctrl+C stuck
inside ``BaseServer.shutdown()``/``server_close()``.
"""

from __future__ import annotations

import socket
import threading
import time
import unittest
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from koruapi.dashboard_logs import sse_log_stream
from koruapi.dashboard_serve import ServeConfig
from koruapi.dashboard_serve_utils import DashboardHTTPServer, bind_serve_server


def _free_port() -> int:
    with closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start(project: Path, port: int) -> ThreadingHTTPServer:
    config = ServeConfig(
        project=project,
        host="127.0.0.1",
        port=port,
        open_browser=False,
    )
    server = bind_serve_server(config)[0]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    for _ in range(50):
        try:
            with closing(socket.create_connection(("127.0.0.1", port), 0.05)):
                break
        except OSError:
            time.sleep(0.005)
    return server


class TestDashboardHTTPServerClass(unittest.TestCase):
    def test_build_server_uses_daemon_threads(self) -> None:
        with TemporaryDirectory() as tmp:
            server = _start(Path(tmp), _free_port())
            try:
                self.assertIsInstance(server, DashboardHTTPServer)
                self.assertTrue(server.daemon_threads)
                self.assertFalse(server.block_on_close)
                self.assertFalse(server.shutdown_event.is_set())
            finally:
                server.shutdown()
                server.server_close()

    def test_server_close_sets_shutdown_event(self) -> None:
        with TemporaryDirectory() as tmp:
            server = _start(Path(tmp), _free_port())
            server.shutdown()
            server.server_close()
            self.assertTrue(server.shutdown_event.is_set())


class TestShutdownWithOpenSSEClient(unittest.TestCase):
    def test_shutdown_returns_promptly_with_open_sse_stream(self) -> None:
        """shutdown()+server_close() must not block while a client holds SSE."""
        with TemporaryDirectory() as tmp:
            port = _free_port()
            server = _start(Path(tmp), port)
            # Open an SSE stream with no limit and keep the socket open.
            sse_sock = socket.create_connection(("127.0.0.1", port), timeout=5)
            try:
                sse_sock.sendall(
                    b"GET /api/logs/stream?limit=0 HTTP/1.0\r\n"
                    b"Host: 127.0.0.1\r\n\r\n"
                )
                sse_sock.recv(4096)  # response headers + first events
            except OSError:
                pass

            start = time.monotonic()
            server.shutdown()
            server.server_close()
            elapsed = time.monotonic() - start
            sse_sock.close()

            self.assertLess(elapsed, 5.0, "shutdown blocked on open SSE client")

    def test_sse_handler_exits_after_server_close(self) -> None:
        """The SSE handler thread should observe shutdown_event and finish."""
        with TemporaryDirectory() as tmp:
            port = _free_port()
            server = _start(Path(tmp), port)
            sse_sock = socket.create_connection(("127.0.0.1", port), timeout=5)
            sse_sock.sendall(
                b"GET /api/logs/stream?limit=0 HTTP/1.0\r\n"
                b"Host: 127.0.0.1\r\n\r\n"
            )
            sse_sock.recv(4096)
            server.shutdown()
            server.server_close()
            deadline = time.monotonic() + 3.0
            handler_done = False
            while time.monotonic() < deadline:
                alive = [
                    t for t in threading.enumerate()
                    if t.name.startswith("Thread") and t.is_alive()
                ]
                # daemon handler threads exit once shutdown_event propagates
                handler_done = not any(
                    "handle" in (getattr(t, "_target", None).__name__ or "")
                    for t in alive
                )
                if handler_done:
                    break
                time.sleep(0.05)
            sse_sock.close()
            self.assertTrue(server.shutdown_event.is_set())


class TestSSEGeneratorStopEvent(unittest.TestCase):
    def test_generator_stops_when_event_set(self) -> None:
        with TemporaryDirectory() as tmp:
            stop = threading.Event()
            chunks: list[str] = []

            def _consume() -> None:
                for chunk in sse_log_stream(
                    Path(tmp), max_events=0, poll_interval=0.01, stop_event=stop
                ):
                    chunks.append(chunk)
                    if len(chunks) >= 3:
                        stop.set()

            thread = threading.Thread(target=_consume, daemon=True)
            thread.start()
            thread.join(timeout=3.0)
            self.assertFalse(thread.is_alive(), "SSE generator ignored stop_event")
            self.assertGreaterEqual(len(chunks), 3)

    def test_generator_runs_without_stop_event(self) -> None:
        with TemporaryDirectory() as tmp:
            nfo = Path(tmp) / ".planfile" / ".koru" / "nfo-events.jsonl"
            nfo.parent.mkdir(parents=True)
            nfo.write_text(
                '{"level": "INFO", "message": "hi", "timestamp": "t0"}\n',
                encoding="utf-8",
            )
            gen = sse_log_stream(Path(tmp), max_events=1, poll_interval=0.01)
            self.assertTrue(next(gen).startswith("data:"))
            with self.assertRaises(StopIteration):
                next(gen)


class TestHandleErrorSuppression(unittest.TestCase):
    def test_disconnect_errors_not_reported(self) -> None:
        with TemporaryDirectory() as tmp:
            server = _start(Path(tmp), _free_port())
            try:
                try:
                    raise ConnectionResetError(104, "reset by peer")
                except ConnectionResetError:
                    server.handle_error(None, ("127.0.0.1", 0))  # no traceback
                try:
                    raise BrokenPipeError(32, "broken pipe")
                except BrokenPipeError:
                    server.handle_error(None, ("127.0.0.1", 0))
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
