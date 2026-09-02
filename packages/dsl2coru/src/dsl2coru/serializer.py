"""Compatibility alias for canonical DSL text serialization."""

from dsl2koru import grammar as _canonical
from dsl2koru.grammar import to_text


def __getattr__(name: str):
    return getattr(_canonical, name)


__all__ = ["to_text"]
