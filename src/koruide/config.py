"""User-tunable autopilot config (R7).

The whole file is optional. When missing or malformed, autopilot prints
one line on ``stderr`` and falls back to built-in defaults — never a
crash, never a silent surprise.

Default location (XDG): ``$XDG_CONFIG_HOME/koru/autopilot.toml``,
which on Linux resolves to ``~/.config/koru/autopilot.toml``.

Schema (every section is optional):

    # ~/.config/koru/autopilot.toml

    [submit_keys]
    # Per-IDE submit shortcut. IDE id matches the one shown by
    # `koru autopilot ide-list`. Unknown id falls back to "Return".
    windsurf  = "Return"
    antigravity = "Return"
    vscode    = "Return"
    vscodium  = "Return"
    cursor    = "Return"
    jetbrains = "ctrl+Return"
    zed       = "Return"

Adding a new IDE only requires bumping this file; no code change. Keys
with more than one modifier (``ctrl+shift+Return``) are rejected at
injection time by :mod:`koruide.injector` with a clear error.
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from koruide.utils import resolve_xdg_path

# Single source of truth for built-in submit keys. ``default`` is the
# fallback used when an IDE id has no explicit mapping.
_BUILTIN_SUBMIT_KEYS: dict[str, str] = {
    "default": "Return",
    "antigravity": "Return",
    "windsurf": "Return",
    "vscode": "Return",
    "vscodium": "Return",
    "cursor": "Return",
    "jetbrains": "ctrl+Return",
    "zed": "Return",
}


@dataclass(frozen=True)
class AutopilotConfig:
    """In-memory view of ``autopilot.toml`` (or defaults)."""

    submit_keys: dict[str, str] = field(default_factory=lambda: dict(_BUILTIN_SUBMIT_KEYS))
    source: Path | None = None

    def submit_key_for(self, ide: str) -> str:
        """Return the configured submit key for ``ide`` (or the default)."""
        return self.submit_keys.get(ide) or self.submit_keys.get("default", "Return")


def default_config_path() -> Path:
    """Resolve the XDG-style config path for autopilot."""
    return resolve_xdg_path("koru/autopilot.toml")


def _merge_submit_keys(raw: object) -> dict[str, str]:
    """Validate and merge user-provided ``[submit_keys]`` over defaults."""
    merged = dict(_BUILTIN_SUBMIT_KEYS)
    if not isinstance(raw, dict):
        return merged
    for ide, key in raw.items():
        if not isinstance(ide, str) or not ide:
            continue
        if not isinstance(key, str) or not key:
            continue
        merged[ide] = key
    return merged


def load_config(path: Path | None = None) -> AutopilotConfig:
    """Read the TOML config from ``path`` (or the default location).

    Missing file → defaults silently. Malformed file → defaults + one
    ``stderr`` warning. Read errors → same fallback.
    """
    config_path = path or default_config_path()
    if not config_path.is_file():
        return AutopilotConfig()
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        print(
            f"koru autopilot: ignoring malformed config {config_path}: {exc}",
            file=sys.stderr,
        )
        return AutopilotConfig()
    submit_keys = _merge_submit_keys(data.get("submit_keys"))
    return AutopilotConfig(submit_keys=submit_keys, source=config_path)


@lru_cache(maxsize=1)
def cached_config() -> AutopilotConfig:
    """Process-lifetime memoised :func:`load_config`."""
    return load_config()


def clear_config_cache() -> None:
    """Drop the cached config — used by tests and after config edits."""
    cached_config.cache_clear()


__all__ = [
    "AutopilotConfig",
    "default_config_path",
    "load_config",
    "cached_config",
    "clear_config_cache",
]
