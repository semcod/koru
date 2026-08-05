"""Argparse front-end and dispatch for ``koru configure``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from koruide.ide import autopilot_ide_choices

from koru.configurator.features import migrate_project_config, toggle_feature_sections
from koru.configurator.prompting import configure_project
from koru.configurator.render import render_shell_exports, render_text_summary
from koru.configurator.schema import CONFIG_SCHEMA_V2, ConfigureResult, _ConfigureArgs


def build_configure_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru configure",
        description="Configure project-local Koru defaults from an interactive shell prompt.",
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root to configure.")
    parser.add_argument("--workspace", type=Path, default=None, help="Workspace root for project discovery.")
    parser.add_argument("--ide", choices=autopilot_ide_choices(), default=None, help="Default IDE lane.")
    parser.add_argument("--queue-name", default=None, help="Default planfile queue name.")
    parser.add_argument("--host", default=None, help="Default dashboard bind host.")
    parser.add_argument("--port", type=int, default=None, help="Default dashboard port.")
    lan_group = parser.add_mutually_exclusive_group()
    lan_group.add_argument("--lan", dest="lan", action="store_true", default=None, help="Expose dashboard on LAN.")
    lan_group.add_argument("--no-lan", dest="lan", action="store_false", help="Keep dashboard local-only.")
    port_group = parser.add_mutually_exclusive_group()
    port_group.add_argument(
        "--auto-port",
        dest="auto_port",
        action="store_true",
        default=None,
        help="Auto-pick a free dashboard port.",
    )
    port_group.add_argument(
        "--no-auto-port",
        dest="auto_port",
        action="store_false",
        help="Fail if dashboard port is busy.",
    )
    parser.add_argument("--non-interactive", action="store_true", help="Write defaults/flags without prompting.")
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Upgrade existing .koru/config.json to schema v2 (adds disabled feature sections).",
    )
    parser.add_argument(
        "--enable",
        action="append",
        default=[],
        help="Enable a v2 feature section (vision, mesh, browse, sandbox). Repeatable.",
    )
    parser.add_argument(
        "--disable",
        action="append",
        default=[],
        help="Disable a v2 feature section. Repeatable.",
    )
    parser.add_argument("--format", choices=("text", "json", "shell"), default="text")
    return parser


def _split_feature_list(values: list[str]) -> tuple[str, ...]:
    out: list[str] = []
    for raw in values:
        for item in str(raw).split(","):
            stripped = item.strip().lower()
            if stripped:
                out.append(stripped)
    return tuple(out)


def _emit_configure_output(result: ConfigureResult, fmt: str, *, text: str | None = None) -> None:
    if fmt == "json":
        print(json.dumps(result.config, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if fmt == "shell":
        print(render_shell_exports(result.config))
        return
    print(text or render_text_summary(result))


def _configure_migrate(cfg: _ConfigureArgs) -> int:
    try:
        result = migrate_project_config(cfg.project)
    except ValueError as exc:
        print(f"koru configure: {exc}", file=sys.stderr)
        return 2
    summary = f"koru configure: migrated {result.path} -> {CONFIG_SCHEMA_V2}"
    _emit_configure_output(result, cfg.format, text=summary)
    return 0


def _configure_toggle(cfg: _ConfigureArgs) -> int:
    enable = _split_feature_list(cfg.enable)
    disable = _split_feature_list(cfg.disable)
    try:
        result = toggle_feature_sections(cfg.project, enable=enable, disable=disable)
    except ValueError as exc:
        print(f"koru configure: {exc}", file=sys.stderr)
        return 2
    changed = ", ".join(
        f"+{name}" for name in enable
    ) + (", " if enable and disable else "") + ", ".join(f"-{name}" for name in disable)
    summary = f"koru configure: features {changed} in {result.path}"
    _emit_configure_output(result, cfg.format, text=summary)
    return 0


def _configure_write(cfg: _ConfigureArgs) -> int:
    try:
        result = configure_project(
            project=cfg.project,
            workspace=cfg.workspace,
            ide=cfg.ide,
            queue_name=cfg.queue_name,
            host=cfg.host,
            port=cfg.port,
            lan=cfg.lan,
            auto_port=cfg.auto_port,
            interactive=not cfg.non_interactive,
        )
    except (EOFError, ValueError) as exc:
        print(f"koru configure: {exc}", file=sys.stderr)
        return 2
    _emit_configure_output(result, cfg.format)
    return 0


def configure_main(argv: list[str] | None = None) -> int:
    args = build_configure_parser().parse_args(argv)
    cfg = _ConfigureArgs.from_namespace(args)
    if cfg.migrate:
        return _configure_migrate(cfg)
    if cfg.enable or cfg.disable:
        return _configure_toggle(cfg)
    return _configure_write(cfg)
