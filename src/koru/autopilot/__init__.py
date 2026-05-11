"""koru autopilot — drive an IDE's LLM chat from the terminal.

See ``docs/autopilot-design.md`` for the architecture overview.

Public surface:
    - :func:`default_socket_path` — where the unix socket lives.
    - :class:`Message` and helpers from :mod:`koru.autopilot.protocol`.
    - :class:`Injector`             from :mod:`koru.autopilot.injector`.
    - :func:`detect_running_ides`   from :mod:`koru.autopilot.ide`.
    - :class:`AutopilotDaemon`      from :mod:`koru.autopilot.daemon`.
    - :class:`AutopilotClient`      from :mod:`koru.autopilot.client`.
"""

from __future__ import annotations

import os
from pathlib import Path


def default_socket_path() -> Path:
    """Return the canonical unix-socket location for the autopilot daemon.

    Uses ``$XDG_RUNTIME_DIR/koru-autopilot.sock`` when available
    (it is per-user and auto-cleaned by systemd-logind); otherwise
    falls back to ``/tmp/koru-autopilot-<uid>.sock``.
    """
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        path = Path(runtime) / "koru-autopilot.sock"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return path
    return Path(f"/tmp/koru-autopilot-{os.getuid()}.sock")


__all__ = ["default_socket_path"]
