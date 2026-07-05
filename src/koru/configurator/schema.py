"""Schema constants and value dataclasses for project-local Koru config."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_SCHEMA_V1 = "koru.config/v1"
CONFIG_SCHEMA_V2 = "koru.config/v2"
CONFIG_SCHEMA = CONFIG_SCHEMA_V1
CONFIG_REL_PATH = Path(".koru") / "config.json"


@dataclass(frozen=True)
class ConfigureResult:
    project: Path
    path: Path
    config: dict[str, Any]


@dataclass(frozen=True)
class _ConfigureValues:
    workspace: str
    ide: str
    queue_name: str
    host: str
    port: int
    lan: bool
    auto_port: bool


@dataclass(frozen=True)
class _ConfigureArgs:
    """Extracted configuration from argparse.Namespace to avoid Shotgun Surgery."""

    project: Path
    format: str
    migrate: bool
    enable: str
    disable: str
    workspace: str
    ide: str
    queue_name: str
    host: str
    port: int
    lan: bool
    auto_port: bool
    non_interactive: bool

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> _ConfigureArgs:
        """Create config from parsed arguments."""
        return cls(
            project=args.project,
            format=args.format,
            migrate=args.migrate,
            enable=args.enable,
            disable=args.disable,
            workspace=args.workspace,
            ide=args.ide,
            queue_name=args.queue_name,
            host=args.host,
            port=args.port,
            lan=args.lan,
            auto_port=args.auto_port,
            non_interactive=args.non_interactive,
        )
