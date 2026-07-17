"""CLI command handlers (package migration scaffold).

Canonical subcommand dispatch currently lives in the legacy module
``src/koru/cli.py`` and is exposed through the :mod:`koru.cli` package
bridge (:func:`koru.cli.main`, ``_SUBCOMMANDS``).

This module is intentionally a documented placeholder until handlers are
moved out of the legacy module. Keeping a non-empty module avoids the
zero-byte "dead scaffold" smell reported by static analysis.
"""

from __future__ import annotations

__all__: list[str] = []
