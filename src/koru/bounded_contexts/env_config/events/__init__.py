"""Domain events for the environment-config bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from koru.cqrs import DomainEvent

ENV_CONFIG_CONTEXT = "env_config"

ENV_CONFIG_WRITTEN = "env_config.written"
ENV_UPDATES_APPLIED = "env_config.updates_applied"


@dataclass(frozen=True)
class EnvConfigWritten(DomainEvent):
    project: str
    path: str
    updated_keys: list[str]


@dataclass(frozen=True)
class EnvUpdatesApplied(DomainEvent):
    project: str
    updated_keys: list[str]


__all__ = [
    "ENV_CONFIG_CONTEXT",
    "ENV_CONFIG_WRITTEN",
    "ENV_UPDATES_APPLIED",
    "EnvConfigWritten",
    "EnvUpdatesApplied",
]