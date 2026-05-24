"""Registry of available :class:`IdeStrategy` instances.

Strategies register themselves at import time. This module is intentionally
**import-light** so loading it does not pull adapter or daemon code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from koruide.ides.base import IdeStrategy

_REGISTRY: dict[str, "IdeStrategy"] = {}


def register_strategy(strategy: "IdeStrategy", *, override: bool = False) -> None:
    """Register ``strategy`` under its canonical id.

    ``override=True`` is reserved for tests.
    """
    ide_id = strategy.id
    if not ide_id:
        raise ValueError("IdeStrategy.id must be a non-empty string")
    if not override and ide_id in _REGISTRY:
        raise ValueError(
            f"IdeStrategy for {ide_id!r} already registered: "
            f"{type(_REGISTRY[ide_id]).__name__}",
        )
    _REGISTRY[ide_id] = strategy


def get_strategy(ide_id: str | None) -> "IdeStrategy | None":
    """Return the registered strategy for ``ide_id`` (or ``None``)."""
    if not ide_id:
        return None
    return _REGISTRY.get(ide_id.strip().lower())


def all_strategies() -> tuple["IdeStrategy", ...]:
    return tuple(_REGISTRY.values())


def strategy_ids() -> tuple[str, ...]:
    return tuple(_REGISTRY.keys())


def _bootstrap_default_strategies() -> None:
    """Eager-import per-IDE modules so registration happens on first use.

    Each module registers itself on import. We intentionally keep this list
    inside the function (not at module top-level) so a failure to import one
    IDE does not block the registry from serving others.
    """
    # Import order is irrelevant; modules self-register.
    import importlib

    for module_name in (
        "koruide.ides.antigravity",
        "koruide.ides.cursor",
        "koruide.ides.jetbrains",
        "koruide.ides.vscodium",
        "koruide.ides.vscode",
        "koruide.ides.windsurf",
        "koruide.ides.zed",
    ):
        try:
            importlib.import_module(module_name)
        except Exception:  # pragma: no cover - defensive
            # Never let a single IDE module break the registry.
            continue


_bootstrap_default_strategies()


__all__ = [
    "all_strategies",
    "get_strategy",
    "register_strategy",
    "strategy_ids",
]
