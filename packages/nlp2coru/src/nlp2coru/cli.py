"""Compatibility alias for the canonical NLP CLI."""

from nlp2koru.cli import main

__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
