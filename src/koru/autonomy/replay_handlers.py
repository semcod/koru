"""Concrete replay action handlers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from koru.autonomy.replay_types import ReplayAction, ReplayResult


@dataclass(frozen=True)
class ReplayQueryHandlers:
    """Read-only replay handlers."""

    def show_decisions(self, action: ReplayAction, *, project: Path) -> ReplayResult:
        url = action.args.get("url", "http://127.0.0.1:8765")
        result = subprocess.run(
            ["bash", "-lc", f"curl -s {url}/api/autonomy/trace | jq .decisions"],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
        return ReplayResult(
            ok=result.returncode == 0,
            output=result.stdout,
            returncode=result.returncode,
            action=action,
        )

    def show_interfaces(self, action: ReplayAction, *, project: Path) -> ReplayResult:
        url = action.args.get("url", "http://127.0.0.1:8765")
        result = subprocess.run(
            ["bash", "-lc", f"curl -s {url}/api/interfaces | jq '.families, .blockers'"],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
        return ReplayResult(
            ok=result.returncode == 0,
            output=result.stdout,
            returncode=result.returncode,
            action=action,
        )


@dataclass(frozen=True)
class ReplayCommandHandlers:
    """Mutating replay handlers."""

    def ticket_input(self, action: ReplayAction, *, project: Path) -> ReplayResult:
        ticket_id = action.positional[0] if action.positional else ""
        if not ticket_id:
            return ReplayResult(ok=False, output="ticket_id required", action=action)
        cmd_parts = ["planfile", "ticket", "input", ticket_id]
        prompt = action.args.get("prompt", "<input needed>")
        note = action.args.get("note", "<what was verified>")
        cmd_parts.extend(["--prompt", prompt, "--note", note])
        result = subprocess.run(cmd_parts, cwd=project, capture_output=True, text=True, check=False)
        return ReplayResult(
            ok=result.returncode == 0,
            output=result.stdout,
            returncode=result.returncode,
            action=action,
        )

    def scan_force(self, action: ReplayAction, *, project: Path) -> ReplayResult:
        result = subprocess.run(
            ["bash", "-lc", "rm -rf project/ && KORU_SCAN_FORCE_RESCAN=1 koru auto --max-cycles 1"],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
        return ReplayResult(
            ok=result.returncode == 0,
            output=result.stdout,
            returncode=result.returncode,
            action=action,
        )

    def retry_drive(self, action: ReplayAction, *, project: Path) -> ReplayResult:
        ticket_id = action.positional[0] if action.positional else ""
        if not ticket_id:
            return ReplayResult(ok=False, output="ticket_id required", returncode=2, action=action)
        ide = action.args.get("ide", "auto")
        result = subprocess.run(
            [
                "koru",
                "autopilot",
                "drive",
                "--ide",
                ide,
                "--require-plugin",
                "-p",
                f"continue with {ticket_id}",
            ],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
        return ReplayResult(
            ok=result.returncode == 0,
            output=result.stdout,
            returncode=result.returncode,
            action=action,
        )


__all__ = ["ReplayCommandHandlers", "ReplayQueryHandlers"]
