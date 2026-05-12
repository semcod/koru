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


def _autopilot_socket_basename() -> str:
    """File name (with ``.sock``) under ``$XDG_RUNTIME_DIR`` or ``/tmp``."""
    instance = os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip()
    if not instance:
        return "koru-autopilot.sock"
    slug_chars: list[str] = []
    for ch in instance[:64]:
        if ch.isalnum() or ch in "-_":
            slug_chars.append(ch)
        else:
            slug_chars.append("-")
    slug = "".join(slug_chars).strip("-") or "instance"
    return f"koru-autopilot-{slug}.sock"


def default_socket_path() -> Path:
    """Return the canonical unix-socket location for the autopilot daemon.

    Resolution order:

    1. ``KORU_AUTOPILOT_SOCKET`` — absolute path (each IDE/plugin should set a
       distinct path when several instances share one login session).
    2. Otherwise ``$XDG_RUNTIME_DIR/<name>`` where ``<name>`` is
       ``koru-autopilot.sock`` (legacy) or ``koru-autopilot-<slug>.sock`` when
       ``KORU_AUTOPILOT_INSTANCE`` is set (e.g. ``cursor-main``, ``windsurf-2``).
    3. Fallback under ``/tmp`` — distinct file per uid; instance sockets
       include the slug in the file name.
    """
    explicit = os.environ.get("KORU_AUTOPILOT_SOCKET", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    name = _autopilot_socket_basename()
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        path = Path(runtime) / name
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return path
    if name == "koru-autopilot.sock":
        return Path(f"/tmp/koru-autopilot-{os.getuid()}.sock")
    stem = name.removesuffix(".sock")
    return Path(f"/tmp/{stem}-{os.getuid()}.sock")


__all__ = ["default_socket_path"]
