"""Route Koru delivery surfaces: IDE (Cursor / Windsurf / VS Code family) vs headless.

This module is the single place that answers: *which autopilot IDE string should
autonomous use*, and whether MCP / autopilot GUI bridges are *recommended* for
the current environment.

It does **not** start MCP or the autopilot daemon; callers (``koru autonomous``,
shell scripts, operators) still enable those explicitly.
"""


import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from koru.autonomy.env import env_truthy
from koruide.ide import normalize_ide_id, supported_autopilot_ide_ids

_VALID_AUTOPILOT_IDE = supported_autopilot_ide_ids()


def is_headless_environment(environ: Mapping[str, str] | None = None) -> bool:
    """True when we should not assume a local GUI IDE session.

    Operators can force headless with ``KORU_HEADLESS=1`` or ``KORU_IDE_MODE=headless``.
    """
    env = os.environ if environ is None else environ
    if env_truthy("KORU_HEADLESS", False, environ=env):
        return True
    mode = (env.get("KORU_IDE_MODE") or "").strip().lower()
    if mode == "headless":
        return True
    if sys.platform != "win32" and env.get("SSH_CONNECTION") and not env.get("DISPLAY"):
        return True
    return False


@dataclass(frozen=True)
class IDERoute:
    """Resolved routing decision for one Koru process."""

    autopilot_ide: str
    headless: bool
    primary_surface: Literal["headless_terminal", "ide_shell"]
    recommend_mcp: bool
    recommend_autopilot_drive: bool
    notes: str


def resolve_ide_route(
    *,
    cli_autopilot_ide: str = "auto",
    environ: Mapping[str, str] | None = None,
) -> IDERoute:
    """Merge CLI ``--autopilot-ide``, ``KORU_AUTOPILOT_IDE``, and headless probes."""
    env = os.environ if environ is None else environ
    allow_gui_bridge = env_truthy("KORU_HEADLESS_ALLOW_AUTOPILOT", False, environ=env)
    if is_headless_environment(env) and not allow_gui_bridge:
        return IDERoute(
            autopilot_ide="auto",
            headless=True,
            primary_surface="headless_terminal",
            recommend_mcp=False,
            recommend_autopilot_drive=False,
            notes=(
                "headless: prefer queue/CLI; enable MCP only in the CI/agent that owns "
                "the workspace. Set KORU_HEADLESS_ALLOW_AUTOPILOT=1 to honor "
                "KORU_AUTOPILOT_IDE for XVFB-style GUI bridges."
            ),
        )

    env_ide = normalize_ide_id(env.get("KORU_AUTOPILOT_IDE"))
    env_instance = normalize_ide_id(env.get("KORU_AUTOPILOT_INSTANCE"))
    if env_ide in _VALID_AUTOPILOT_IDE and env_ide != "auto":
        ide = env_ide
    elif (
        env_instance in _VALID_AUTOPILOT_IDE
        and env_instance != "auto"
        and normalize_ide_id(cli_autopilot_ide) in {None, "auto"}
    ):
        ide = env_instance
    else:
        cli = normalize_ide_id(cli_autopilot_ide)
        ide = cli if cli in _VALID_AUTOPILOT_IDE else "auto"

    return IDERoute(
        autopilot_ide=ide,
        headless=False,
        primary_surface="ide_shell",
        recommend_mcp=True,
        recommend_autopilot_drive=True,
        notes=(
            "IDE shell: enable Koru MCP in the editor for chat tools; use autopilot "
            "drive/handoff from autoloop when you want terminal → chat injection."
        ),
    )


__all__ = [
    "IDERoute",
    "is_headless_environment",
    "resolve_ide_route",
]
