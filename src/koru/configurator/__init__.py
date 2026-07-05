"""Interactive shell configurator for project-local Koru details.

This package is the public surface — import names from ``koru.configurator``.
The implementation lives in focused submodules:

* :mod:`koru.configurator.schema`   — schema constants + value dataclasses
* :mod:`koru.configurator.store`    — ``.koru/config.json`` load/save
* :mod:`koru.configurator.features` — schema v2 feature sections (migrate/toggle)
* :mod:`koru.configurator.render`   — text summary + shell export rendering
* :mod:`koru.configurator.prompting`— ``ShellPrompter`` + ``configure_project``
* :mod:`koru.configurator.cli`      — argparse front-end + ``configure_main``

The names below are re-exported so existing ``from koru.configurator import ...``
imports keep working unchanged.
"""

from __future__ import annotations

from koru.configurator.cli import build_configure_parser, configure_main
from koru.configurator.features import (
    default_v2_feature_sections,
    merge_v2_feature_sections,
    migrate_project_config,
    toggle_feature_sections,
)
from koru.configurator.prompting import ShellPrompter, configure_project
from koru.configurator.render import render_shell_exports, render_text_summary
from koru.configurator.schema import (
    CONFIG_REL_PATH,
    CONFIG_SCHEMA,
    CONFIG_SCHEMA_V1,
    CONFIG_SCHEMA_V2,
    ConfigureResult,
)
from koru.configurator.store import load_project_config, save_project_config

__all__ = [
    "CONFIG_REL_PATH",
    "CONFIG_SCHEMA",
    "CONFIG_SCHEMA_V1",
    "CONFIG_SCHEMA_V2",
    "ConfigureResult",
    "ShellPrompter",
    "build_configure_parser",
    "configure_main",
    "configure_project",
    "default_v2_feature_sections",
    "load_project_config",
    "merge_v2_feature_sections",
    "migrate_project_config",
    "render_shell_exports",
    "render_text_summary",
    "save_project_config",
    "toggle_feature_sections",
]
