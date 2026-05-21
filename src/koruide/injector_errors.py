"""Shared exceptions for keyboard injection."""

from __future__ import annotations


class InjectorError(RuntimeError):
    """No usable backend, or the backend call failed."""


__all__ = ["InjectorError"]
