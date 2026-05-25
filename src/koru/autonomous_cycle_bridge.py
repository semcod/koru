"""Compatibility bridge for the autonomous cycle module."""

from __future__ import annotations

from typing import Any


def run_cycle_with_compat(
    kwargs: dict[str, Any],
    *,
    cycle_module: Any,
    dependencies: dict[str, Any],
) -> Any:
    """Forward facade-level monkeypatch points into ``koru.autonomous_cycle``."""
    for name, value in dependencies.items():
        setattr(cycle_module, name, value)
    return cycle_module.run_cycle(**kwargs)


__all__ = ["run_cycle_with_compat"]
