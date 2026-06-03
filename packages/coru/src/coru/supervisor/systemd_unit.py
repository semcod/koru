"""CLI action for installing the coru supervisor systemd user unit."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path


def systemd_user_dir() -> Path:
    """Resolve the XDG ``systemd/user`` directory."""
    xdg_config_home = (os.environ.get("XDG_CONFIG_HOME") or "").strip()
    if xdg_config_home:
        return (Path(xdg_config_home).expanduser() / "systemd" / "user").resolve()
    return (Path.home() / ".config" / "systemd" / "user").resolve()


def resolve_coru_bin() -> str:
    """Best-effort absolute path to the ``coru`` executable."""
    on_path = shutil.which("coru")
    if on_path:
        return on_path
    sibling = Path(sys.executable).with_name("coru")
    if sibling.is_file() and os.access(sibling, os.X_OK):
        return str(sibling)
    prefixed = Path(sys.prefix) / "bin" / "coru"
    if prefixed.is_file() and os.access(prefixed, os.X_OK):
        return str(prefixed)
    return "%h/.local/bin/coru"


def render_unit(coru_bin: str) -> str:
    """Render the systemd user unit text with resolved executable path."""
    template_path = Path(__file__).resolve().parents[5] / "systemd" / "coru-supervisor.service"
    try:
        template = template_path.read_text(encoding="utf-8")
    except OSError:
        template = (
            "[Unit]\n"
            "Description=coru supervisor lane registry and health watcher\n"
            "After=graphical-session.target\n"
            "PartOf=graphical-session.target\n\n"
            "[Service]\n"
            "Type=simple\n"
            "ExecStart=__CORU_BIN__ supervisor start --foreground --refresh-interval 30\n"
            "Restart=on-failure\n"
            "RestartSec=3\n"
            "Environment=CORU_SUPERVISOR_PORT=8766\n"
            "StandardOutput=journal\n"
            "StandardError=journal\n\n"
            "[Install]\n"
            "WantedBy=default.target\n"
        )

    lines: list[str] = []
    for line in template.splitlines():
        if line.startswith("ExecStart=") and "supervisor start" in line:
            lines.append(f"ExecStart={coru_bin} supervisor start --foreground --refresh-interval 30")
        else:
            lines.append(line)
    return f"{'\n'.join(lines)}\n"


def action_install_unit(
    args: argparse.Namespace,
    *,
    resolve_bin: Callable[[], str] | None = None,
    render: Callable[[str], str] | None = None,
    resolve_unit_dir: Callable[[], Path] | None = None,
) -> int:
    """Install the ``coru-supervisor.service`` unit under systemd user dir."""
    resolve_bin_fn = resolve_bin or resolve_coru_bin
    render_fn = render or render_unit
    resolve_unit_dir_fn = resolve_unit_dir or systemd_user_dir

    coru_bin = resolve_bin_fn()
    rendered = render_fn(coru_bin)
    if args.print_only:
        sys.stdout.write(rendered)
        return 0

    dest = args.dest or resolve_unit_dir_fn() / "coru-supervisor.service"
    if dest.exists() and not args.force:
        print(
            f"coru supervisor install-unit: {dest} already exists (pass --force to overwrite).",
            file=sys.stderr,
        )
        return 1
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        print(f"coru supervisor install-unit: {exc}", file=sys.stderr)
        return 1

    print(f"coru supervisor: installed {dest}")
    print()
    print("Next steps:")
    print("  systemctl --user daemon-reload")
    print("  systemctl --user enable --now coru-supervisor.service")
    print("  journalctl --user -u coru-supervisor -f")
    return 0