"""Run the wizard GUI with uvicorn (127.0.0.1 only)."""

from __future__ import annotations

import socket
import sys
import webbrowser
from pathlib import Path

from koru.wizard.gui.app import create_app

_BIND_HOST = "127.0.0.1"


def _pick_port(requested: int) -> int:
    if requested != 0:
        return requested
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((_BIND_HOST, 0))
        return int(sock.getsockname()[1])


def _require_uvicorn():
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "koru wizard --gui requires uvicorn. Install with: pip install 'koru[api]'"
        ) from exc
    return uvicorn


def run_gui_server(
    *,
    strategies_path: Path,
    language: str | list[str] | None,
    bilingual_separator: str = " · ",
    project_override: Path | None = None,
    create: bool = True,
    port: int = 0,
    open_browser: bool = True,
) -> int:
    """Start the wizard GUI blocking until the user finishes or idle timeout."""
    if port < 0 or port > 65535:
        raise ValueError(f"invalid port: {port}")

    bind_port = _pick_port(port)
    app = create_app(
        strategies_path=strategies_path,
        language=language,
        bilingual_separator=bilingual_separator,
        project_override=project_override,
        create=create,
    )

    uvicorn = _require_uvicorn()
    config = uvicorn.Config(
        app,
        host=_BIND_HOST,
        port=bind_port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    runtime = getattr(app.state, "runtime", None)
    if runtime is not None:
        runtime.uvicorn_server = server
    app.state.uvicorn_server = server

    url = f"http://{_BIND_HOST}:{bind_port}/wizard"
    print(f"koru wizard GUI: {url}", file=sys.stderr)
    if open_browser:
        webbrowser.open(url)

    server.run()
    return 0
