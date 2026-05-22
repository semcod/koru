"""Allow ``python -m koru`` (same as the ``koru`` console script)."""

from koru.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
