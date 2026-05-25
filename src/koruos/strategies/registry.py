"""Registry + resolver for :class:`OsStrategy` implementations.

Each concrete strategy module registers its singleton at import time.
``resolve_active_os_strategy`` picks the first strategy whose
:py:meth:`OsStrategy.matches_current_environment` returns True. The
order of registration therefore matters: more specific strategies
(Wayland) must register before more permissive ones (X11 fallback).
"""

from __future__ import annotations

from koruos.strategies.base import OsStrategy

_REGISTRY: list[OsStrategy] = []


def register_os_strategy(strategy: OsStrategy) -> None:
    """Register ``strategy`` (append to registry, last-write-wins by id)."""
    existing = [s for s in _REGISTRY if s.id == strategy.id]
    if existing:
        for old in existing:
            _REGISTRY.remove(old)
    _REGISTRY.append(strategy)


def get_os_strategy(strategy_id: str) -> OsStrategy | None:
    """Return the strategy with ``id == strategy_id`` if registered."""
    for strategy in _REGISTRY:
        if strategy.id == strategy_id:
            return strategy
    return None


def list_os_strategy_ids() -> tuple[str, ...]:
    """Return the ids of every registered strategy (registration order)."""
    return tuple(s.id for s in _REGISTRY)


def resolve_active_os_strategy() -> OsStrategy:
    """Return the strategy whose ``matches_current_environment`` is true.

    Falls back to the last registered strategy when nothing matches —
    that should never happen in practice because the shipped fallback
    matches everything, but keeping the contract total avoids
    propagating ``Optional`` through every caller.
    """
    for strategy in _REGISTRY:
        if strategy.matches_current_environment():
            return strategy
    if not _REGISTRY:
        raise RuntimeError(
            "koruos.strategies.registry: no OsStrategy registered; "
            "did import of koruos.strategies fail?"
        )
    return _REGISTRY[-1]


__all__ = [
    "get_os_strategy",
    "list_os_strategy_ids",
    "register_os_strategy",
    "resolve_active_os_strategy",
]
