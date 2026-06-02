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
from collections.abc import Mapping

_TRUTHY: frozenset[str] = frozenset({"1", "true", "yes", "on", "auto", "y"})
_FALSY: frozenset[str] = frozenset({"0", "false", "no", "off"})


def parse_boolish(value: object, *, default: bool = False) -> bool:
    """Parse truthy/falsy string-like values with a default fallback."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in _TRUTHY:
        return True
    if normalized in _FALSY:
        return False
    return default


def env_truthy(
    name: str,
    *,
    default: bool = False,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return ``True`` when *name* is set to a truthy value.

    Truthy values (case-insensitive): ``1``, ``true``, ``yes``, ``on``,
    ``auto``, ``y``.  If the variable is unset *default* is returned.
    """
    env = os.environ if environ is None else environ
    raw = env.get(name)
    return parse_boolish(raw, default=default)


def env_disabled(name: str, *, environ: Mapping[str, str] | None = None) -> bool:
    """Return ``True`` when *name* is set to a falsy/disabled value.

    Falsy values (case-insensitive): ``0``, ``false``, ``no``, ``off``.
    Returns ``False`` for an unset or empty variable.
    """
    env = os.environ if environ is None else environ
    return str(env.get(name, "")).strip().lower() in _FALSY


def env_int(name: str, default: int, *, environ: Mapping[str, str] | None = None) -> int:
    """Return the integer value of *name*, or *default* when missing or invalid."""
    env = os.environ if environ is None else environ
    raw = str(env.get(name, "")).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


__all__ = ["env_truthy", "env_disabled", "env_int", "parse_boolish"]
