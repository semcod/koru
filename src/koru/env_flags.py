"""Central helpers for reading boolean/integer environment variables.

Replaces the repeated ``_env_truthy``, ``_env_disabled``, ``_env_bool`` and
``_env_int`` helpers that were scattered across runtime and daemon modules.
All helpers read the environment variable live on every call (never cached)
so that tests using ``monkeypatch.setenv`` / ``monkeypatch.delenv`` observe
up-to-date values without extra setup.

Typical usage::

    from koru.env_flags import env_truthy, env_disabled, env_int

    if env_truthy("KORU_SOME_FEATURE"):
        ...
    if env_disabled("KORU_SOME_GATE"):
        ...
    port = env_int("KORU_PORT", default=8765)
"""

from __future__ import annotations

import os

_TRUTHY: frozenset[str] = frozenset({"1", "true", "yes", "on", "auto", "y"})
_FALSY: frozenset[str] = frozenset({"0", "false", "no", "off"})


def env_truthy(name: str, *, default: bool = False) -> bool:
    """Return ``True`` when *name* is set to a truthy value.

    Truthy values (case-insensitive): ``1``, ``true``, ``yes``, ``on``,
    ``auto``, ``y``.  If the variable is unset *default* is returned.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY


def env_disabled(name: str) -> bool:
    """Return ``True`` when *name* is set to a falsy/disabled value.

    Falsy values (case-insensitive): ``0``, ``false``, ``no``, ``off``.
    Returns ``False`` for an unset or empty variable.
    """
    return os.environ.get(name, "").strip().lower() in _FALSY


def env_int(name: str, default: int) -> int:
    """Return the integer value of *name*, or *default* when missing or invalid."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


__all__ = ["env_truthy", "env_disabled", "env_int"]
