"""Compatibility aliases for canonical DSL text parsing."""

from dsl2koru import grammar as _canonical
from dsl2koru.grammar import normalize_verb, parse_line


def __getattr__(name: str):
    return getattr(_canonical, name)


__all__ = ["normalize_verb", "parse_line"]
