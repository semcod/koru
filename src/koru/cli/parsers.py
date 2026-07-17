"""CLI argparse builders (package migration scaffold).

Canonical parser construction lives in :mod:`koru.cli_parser` and is
wired through the :mod:`koru.cli` package bridge (``_build_parser``,
``_command_value``).

This module is intentionally a documented placeholder until argparse
builders move into the package layout. Keeping a non-empty module avoids
the zero-byte "dead scaffold" smell reported by static analysis.
"""

from __future__ import annotations

__all__: list[str] = []
