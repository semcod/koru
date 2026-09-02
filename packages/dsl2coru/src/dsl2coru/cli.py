"""Deprecated compatibility aliases for :mod:`dsl2koru.cli`."""

from dsl2koru.cli import _build_subcommand_parser, main

__all__ = ["_build_subcommand_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
