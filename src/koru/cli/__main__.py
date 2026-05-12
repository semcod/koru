"""Allow ``python -m koru.cli`` when the ``cli`` package shadows ``cli.py``."""

from __future__ import annotations

from . import main

if __name__ == "__main__":
    raise SystemExit(main())
