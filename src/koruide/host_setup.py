"""Host dependency report and best-effort installs for autopilot keyboard injectors.

``koru --init`` drops ``.planfile/.koru/setup-autopilot-host.sh`` which wraps
``koru autopilot setup-host``.  The goal is to separate:

* what koru can probe or install automatically (Debian/Ubuntu ``apt``), and
* steps that need a human (uinput permissions, ydotoold, IDE extension).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from koruide.ide import detect_focused_ide_id, detect_running_ides
from gillm.injection.injector import Injector

YDOTOOLD_UNIT_NAME = "ydotoold.service"
YDOTOOLD_UNIT_TEMPLATE = """[Unit]
Description=ydotool user-mode keystroke injection daemon
Documentation=man:ydotoold(8)
After=graphical-session.target

[Service]
Type=simple
ExecStartPre=/bin/rm -f {socket}
ExecStart={ydotoold} --socket-path={socket} --socket-perm=0600
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
"""


def _ydotoold_socket_path() -> str:
    # Match the default ydotool client lookup path (no override needed for downstream
    # tooling). /tmp is always writable and survives session restarts cleanly.
    return "/tmp/.ydotool_socket"


def install_ydotoold_user_service(*, dry_run: bool = False) -> dict[str, Any]:
    """Generate, enable and start a per-user ydotoold systemd service.

    Returns a structured report (success / skipped / error). On Wayland-native
    compositors that lack ``virtual-keyboard-v1`` (e.g. GNOME on Wayland),
    ``ydotool`` is the only injector that crosses into the compositor, and
    running it as a daemon avoids the ``ydotoold backend unavailable`` notice
    plus the per-call uinput device race that comes with daemonless mode.
    """
    log: list[str] = []
    ydotoold = shutil.which("ydotoold")
    if ydotoold is None:
        return {
            "ok": False,
            "skipped": True,
            "reason": "ydotoold binary not on PATH (install the ydotool package).",
            "log": log,
        }
    if shutil.which("systemctl") is None:
        return {
            "ok": False,
            "skipped": True,
            "reason": "systemctl not found — cannot manage user services here.",
            "log": log,
        }
    unit_dir = Path(os.path.expanduser("~/.config/systemd/user"))
    unit_path = unit_dir / YDOTOOLD_UNIT_NAME
    socket = _ydotoold_socket_path()
    desired = YDOTOOLD_UNIT_TEMPLATE.format(socket=socket, ydotoold=ydotoold)
    actions: list[str] = []
    if not unit_path.exists() or unit_path.read_text() != desired:
        actions.append(f"write {unit_path}")
        if not dry_run:
            unit_dir.mkdir(parents=True, exist_ok=True)
            unit_path.write_text(desired)
    actions.extend([
        "systemctl --user daemon-reload",
        f"systemctl --user enable --now {YDOTOOLD_UNIT_NAME}",
    ])
    log.extend(actions)
    if dry_run:
        return {"ok": True, "skipped": False, "dry_run": True, "log": log, "unit": str(unit_path)}
    for cmd in (
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", YDOTOOLD_UNIT_NAME],
    ):
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            return {
                "ok": False,
                "skipped": False,
                "reason": f"{' '.join(cmd)} exited {proc.returncode}: {proc.stderr.strip()}",
                "log": log,
                "unit": str(unit_path),
            }
    return {"ok": True, "skipped": False, "log": log, "unit": str(unit_path), "socket": socket}

_INSTRUMENT_DEB = (
    ("xdotool", "xdotool"),
    ("wtype", "wtype"),
    ("ydotool", "ydotool"),
)


def _package_manager_hint() -> str | None:
    if shutil.which("apt-get"):
        return "apt"
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("pacman"):
        return "pacman"
    if shutil.which("brew"):
        return "brew"
    return None


def _human_followups(injector: Injector, selected: str | None) -> list[str]:
    """Reasons automation cannot fully fix the host."""
    out: list[str] = []
    session = injector.session or ""
    have_w = injector.which("wtype")
    have_y = injector.which("ydotool")
    have_x = injector.which("xdotool")

    out.append(
        "Install the koru autopilot IDE extension (Cursor/VS Code/Windsurf) so "
        "`drive` can use the editor API instead of xdotool/ydotool.",
    )

    if not selected:
        out.append(
            "No keyboard injector backend selected: install packages (see "
            "“Automated apt” below) or rely on the IDE extension above.",
        )

    if session == "wayland" and have_y and not have_w:
        out.append(
            "Wayland with only ydotool: requires ydotoold and a usable "
            "/dev/uinput (input group, permissions). See docs/autopilot-quickstart.md. "
            "On Sway/Hyprland, `wtype` is often easier.",
        )

    if session == "wayland" and not have_w and not have_y and not have_x:
        out.append(
            "Wayland session but no wtype/ydotool/xdotool on PATH — without them "
            "(or the IDE plugin) `koru autonomous` cannot type into chat.",
        )

    if session == "x11" and not have_x and not have_w:
        out.append("X11 session without xdotool: install `xdotool` or use the IDE extension.")

    if shutil.which("apt-get") is None:
        out.append(
            "`--install` only automates apt (Debian/Ubuntu). On this system install "
            "xdotool/wtype/ydotool via dnf/pacman/brew manually.",
        )

    return out


def build_setup_host_report() -> dict[str, Any]:
    injector = Injector()
    statuses = [s.to_dict() for s in injector.probe()]
    selected = injector.select_backend()
    deb_missing = [deb for name, deb in _INSTRUMENT_DEB if injector.which(name) is None]
    return {
        "session": injector.session or "unknown",
        "selected_backend": selected,
        "backends": statuses,
        "ides": [i.to_dict() for i in detect_running_ides()],
        "focused_ide": detect_focused_ide_id(),
        "package_manager": _package_manager_hint(),
        "deb_packages_missing": deb_missing,
        "human_actions_required": _human_followups(injector, selected),
        "automated_apt_suggestion": (
            "sudo apt-get update -qq && sudo apt-get install -y " + " ".join(deb_missing)
            if deb_missing
            else None
        ),
    }


def _try_apt_install(
    packages: list[str],
    *,
    dry_run: bool,
) -> tuple[int, list[str]]:
    log: list[str] = []
    if not packages:
        log.append("All injector tools (xdotool, wtype, ydotool) are already on PATH.")
        return 0, log
    cmd = ["sudo", "apt-get", "install", "-y", *packages]
    log.append(" ".join(cmd))
    if dry_run:
        log.append("(dry-run: apt-get not executed)")
        return 0, log
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.stdout.strip():
        log.append(proc.stdout.strip())
    if proc.stderr.strip():
        log.append(proc.stderr.strip())
    return proc.returncode, log


def run_host_setup(
    *,
    output_format: str = "text",
    install: bool = False,
    install_dry_run: bool = False,
) -> int:
    report = build_setup_host_report()
    exit_code = 0

    if install:
        if shutil.which("apt-get") is None:
            report["install_error"] = "apt-get not found — install packages manually."
            exit_code = 1
        else:
            missing = list(report["deb_packages_missing"])
            code, ilog = _try_apt_install(missing, dry_run=install_dry_run)
            report["install_log"] = ilog
            report["install_exit_code"] = code
            if code != 0:
                exit_code = 1
            elif not install_dry_run:
                report = build_setup_host_report()

    if output_format == "json":
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        _print_text_report(report)

    return exit_code


def _print_setup_host_header(report: dict[str, Any]) -> None:
    print("=== koru autopilot setup-host ===\n")
    print(f"Desktop session: {report['session']}")
    print(f"Selected injector (first candidate): {report.get('selected_backend') or '— none'}\n")


def _print_setup_host_backends(report: dict[str, Any]) -> None:
    print("Backends (same probes as `koru autopilot doctor`):")
    for b in report["backends"]:
        mark = "✓" if b.get("available") else "✗"
        print(f"  {mark} {b.get('name', '?'):<10} {b.get('reason', '')}")
    print()


def _print_setup_host_ides(report: dict[str, Any]) -> None:
    ides = report.get("ides") or []
    print(f"Running IDEs: {len(ides)}")
    for ide in ides:
        print(f"  · {ide.get('label', ide)}")
    if report.get("focused_ide"):
        print(f"  (focus: {report['focused_ide']})")
    print()


def _print_setup_host_apt_section(report: dict[str, Any]) -> None:
    print("--- Automated (apt) ---")
    if report.get("automated_apt_suggestion"):
        print(report["automated_apt_suggestion"])
        print("Run: koru autopilot setup-host --install   (or --install --dry-run)")
    else:
        print("xdotool/wtype/ydotool are on PATH — no apt step needed.")
    print()


def _print_setup_host_human_followups(report: dict[str, Any]) -> None:
    print("--- Likely human follow-ups ---")
    for line in report.get("human_actions_required") or []:
        print(f"  • {line}")
    print()


def _print_setup_host_install_details(report: dict[str, Any]) -> None:
    if report.get("install_error"):
        print(f"Install error: {report['install_error']}\n")
    if report.get("install_log"):
        print("Install log:")
        for line in report["install_log"]:
            print(f"  {line}")
        print()
    if report.get("package_manager"):
        print(f"Detected package manager hint: {report['package_manager']}")
    if report.get("install_exit_code") not in (None, 0):
        print("\napt install failed — fix sudo/repos and retry.", file=sys.stderr)


def _print_text_report(report: dict[str, Any]) -> None:
    for section in (
        _print_setup_host_header,
        _print_setup_host_backends,
        _print_setup_host_ides,
        _print_setup_host_apt_section,
        _print_setup_host_human_followups,
        _print_setup_host_install_details,
    ):
        section(report)


__all__ = ["build_setup_host_report", "run_host_setup"]
