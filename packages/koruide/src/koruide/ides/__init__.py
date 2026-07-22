"""Per-IDE strategy modules.

Each IDE Koru supports has its own module here implementing the
:class:`IdeStrategy` contract. The package is the **single place** to add or
modify behavior for a given IDE — detection signatures, settings paths,
trusted-publisher requirements, window reload tactics and so on — so that
changes for one IDE cannot accidentally break others.

Usage::

    from koruide.ides import get_strategy

    strat = get_strategy("cursor")
    if strat is not None:
        if strat.requires_trusted_publisher:
            ...

The registry is intentionally additive: when an IDE has no module yet, we
return a :class:`~koruide.ides.fallback.FallbackIdeStrategy` derived from
the legacy ``_IDE_SIGNATURES`` / ``_IDE_ALIASES`` tables so callers always get
a usable object.
"""

from __future__ import annotations

from koruide.ides.base import IdeStrategy
from koruide.ides.registry import (
    all_strategies,
    get_strategy,
    register_strategy,
    strategy_ids,
)

__all__ = [
    "IdeStrategy",
    "all_strategies",
    "get_strategy",
    "register_strategy",
    "strategy_ids",
]
