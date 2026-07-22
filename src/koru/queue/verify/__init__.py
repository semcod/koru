"""Verify profile registry: tickets name a gate, the project defines it.

``resolver.resolve_verify`` is the entry point the transaction uses; the rest
of the package is its machinery — built-in and project-defined profiles,
command rendering with extension filtering and timeouts, and the allowlist for
raw commands.
"""

from __future__ import annotations

from koru.queue.verify.executor import render_profile_command
from koru.queue.verify.profiles import (
    BUILTIN_PROFILES,
    CHANGED_FILES,
    CUSTOM_READONLY,
    VerifyProfile,
)
from koru.queue.verify.registry import VerifyRegistry, load_registry
from koru.queue.verify.resolver import resolve_verify
from koru.queue.verify.result import VerifyResolution

__all__ = [
    "BUILTIN_PROFILES",
    "CHANGED_FILES",
    "CUSTOM_READONLY",
    "VerifyProfile",
    "VerifyRegistry",
    "VerifyResolution",
    "load_registry",
    "render_profile_command",
    "resolve_verify",
]
