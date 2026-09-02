"""Compatibility aliases for the canonical :mod:`dsl2koru.grammar`."""

from dsl2koru import grammar as _canonical
from dsl2koru.grammar import normalize_verb, parse_line, to_text


def __getattr__(name: str):
    return getattr(_canonical, name)


__all__ = ["normalize_verb", "parse_line", "to_text"]
