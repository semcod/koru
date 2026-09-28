#!/usr/bin/env python3
"""Installer for daily verified benchmark routing timer (systemd user or crontab)."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def install_systemd_timer(dry_run: bool = False) -> int:
    systemd_user_dir = Path.home() / ".config" / "systemd" / "user"
    service_file = systemd_user_dir / "koru-benchmark.service"
    timer_file = systemd_user_dir / "koru-benchmark.timer"

    service_content = f"""[Unit]
Description=Daily verified benchmark routing campaign
After=network.target

[Service]
Type=oneshot
WorkingDirectory={Path.cwd()}
ExecStart={sys.executable} -m koru.cli benchmark run
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""

    timer_content = """[Unit]
Description=Trigger daily verified benchmark campaign at 04:00

[Timer]
OnCalendar=*-*-* 04:00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
"""

    if dry_run:
        print("Dry run: would write:")
        print(f"--- {service_file} ---\n{service_content}")
        print(f"--- {timer_file} ---\n{timer_content}")
        return 0

    systemd_user_dir.mkdir(parents=True, exist_ok=True)
    service_file.write_text(service_content, encoding="utf-8")
    timer_file.write_text(timer_content, encoding="utf-8")

    if shutil.which("systemctl"):
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "--user", "enable", "--now", "koru-benchmark.timer"], check=False)
        print("✓ Successfully installed and activated systemd user timer: koru-benchmark.timer")
    else:
        print("Wrote systemd unit files, but systemctl is not available.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install daily Koru benchmark timer.")
    parser.add_argument("--dry-run", action="store_true", help="Print unit contents without installing.")
    args = parser.parse_args()
    return install_systemd_timer(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
