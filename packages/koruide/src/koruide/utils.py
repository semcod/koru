"""Small koruide-internal helpers that have no external dependency."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

# Boolean-ish environment parsing, kept in sync with ``koru.env_flags``.
# Duplicated here (rather than imported) so ``koruide`` stays importable on
# hosts that do not have the ``koru`` distribution installed.
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
    Reads the environment live on every call (never cached) so tests using
    ``monkeypatch.setenv`` observe up-to-date values.
    """
    env = os.environ if environ is None else environ
    raw = env.get(name)
    return parse_boolish(raw, default=default)


def resolve_xdg_path(relative_path: str) -> Path:
    """Resolve an XDG-style config path.

    Args:
        relative_path: Relative path from the XDG config base
            (e.g. ``"koru/autopilot.toml"``).

    Returns:
        Absolute path to the XDG config location.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / relative_path
