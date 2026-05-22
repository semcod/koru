"""CLI action for installing the autopilot systemd user unit."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from koru.autopilot.utils.client_helpers import resolve_xdg_path


def systemd_user_dir() -> Path:
    """Resolve the XDG ``systemd/user`` directory."""
    return resolve_xdg_path("systemd/user")


def resolve_koru_bin() -> str:
    """Best-effort absolute path to the ``koru`` executable.

    Priority:
    1) ``koru`` on ``PATH``;
    2) sibling of ``sys.executable`` (common for virtualenvs);
    3) user-local default used in docs.
    """
    on_path = shutil.which("koru")
    if on_path:
        return on_path
    sibling = Path(sys.executable).with_name("koru")
    if sibling.is_file() and os.access(sibling, os.X_OK):
        return str(sibling)
    prefixed = Path(sys.prefix) / "bin" / "koru"
    if prefixed.is_file() and os.access(prefixed, os.X_OK):
        return str(prefixed)
    return "%h/.local/bin/koru"


def render_unit(koru_bin: str) -> str:
    """Build the systemd unit text with the resolved koru binary path."""
    template_path = Path(__file__).resolve().parents[3] / "systemd" / "koru-autopilot.service"
    try:
        template = template_path.read_text(encoding="utf-8")
    except OSError:
        template = (
            "[Unit]\n"
            "Description=koru autopilot daemon\n"
            "After=graphical-session.target\n"
            "PartOf=graphical-session.target\n\n"
            "[Service]\n"
            "Type=simple\n"
            "ExecStart=__KORU_BIN__ autopilot daemon --idempotent --no-handoff\n"
            "Restart=on-failure\n"
            "RestartSec=2\n\n"
            "[Install]\n"
            "WantedBy=default.target\n"
        )
    lines = []
    for line in template.splitlines():
        if line.startswith("ExecStart=") and "autopilot daemon" in line:
            lines.append(f"ExecStart={koru_bin} autopilot daemon --idempotent --no-handoff")
        else:
            lines.append(line)
    return f"{'\n'.join(lines)}\n"


def action_install_unit(
    args: argparse.Namespace,
    *,
    resolve_bin: Callable[[], str] = resolve_koru_bin,
    render: Callable[[str], str] = render_unit,
    resolve_unit_dir: Callable[[], Path] = systemd_user_dir,
) -> int:
    """Install the systemd --user service unit."""
    koru_bin = resolve_bin()
    rendered = render(koru_bin)
    if args.print_only:
        sys.stdout.write(rendered)
        return 0
    dest = args.dest or resolve_unit_dir() / "koru-autopilot.service"
    if dest.exists() and not args.force:
        print(
            f"koru autopilot install-unit: {dest} already exists (pass --force to overwrite).",
            file=sys.stderr,
        )
        return 1
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        print(f"koru autopilot install-unit: {exc}", file=sys.stderr)
        return 1
    print(f"koru autopilot: installed {dest}")
    print()
    print("Next steps:")
    print("  systemctl --user daemon-reload")
    print("  systemctl --user enable --now koru-autopilot.service")
    print("  journalctl --user -u koru-autopilot -f      # follow logs")
    print()
    print("To enable auto-handoff for a project, override ExecStart with:")
    print("  systemctl --user edit koru-autopilot.service")
    return 0
