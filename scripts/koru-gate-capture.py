#!/usr/bin/env python3
"""Run a gate command and create a deduplicated planfile ticket on failure.

The script is intentionally simple:
- execute one gate command,
- treat non-zero exit as failure,
- optionally treat regex match in output as failure signal,
- create one ticket per unique finding key (or skip if it already exists).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence


def _normalize_line(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return "gate command failed"


def _is_noise_line(line: str) -> bool:
    cleaned = line.strip()
    if not cleaned:
        return True
    if re.fullmatch(r"[*#=\-]{5,}", cleaned):
        return True

    lowered = cleaned.lower()
    cloud_init_markers = (
        "a new feature in cloud-init identified possible datasources",
        "the datasource used was: none",
        "in the future, cloud-init will only attempt to use datasources",
        "if you are seeing this message, please file a bug against",
        "https://bugs.launchpad.net/bugs/1669675",
        "https://github.com/canonical/cloud-init/issues",
        "disable the warnings above by:",
        "touch /home/",
        "touch /var/lib/cloud/instance/warnings/.skip",
    )
    return any(marker in lowered for marker in cloud_init_markers)


def _first_meaningful_line(text: str) -> str:
    for line in text.splitlines():
        if _is_noise_line(line):
            continue
        return line.strip()
    return _first_nonempty_line(text)


def _run_planfile(project: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["planfile", *args],
        cwd=project,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="Project root (default: current directory)")
    parser.add_argument("--gate", required=True, help="Gate identifier, e.g. regix/testql/wup/plugin")
    parser.add_argument("--command", required=True, help="Shell command to execute for this gate")
    parser.add_argument(
        "--fail-regex",
        default="",
        help="Optional regex: if matched in output, the gate is treated as failed even on exit 0",
    )
    parser.add_argument(
        "--next-step",
        default="Investigate failing gate output and apply the minimal fix.",
        help="Suggested next remediation step saved into the ticket",
    )
    parser.add_argument("--priority", default="normal", help="Ticket priority (default: normal)")
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="When finding already exists, append a note to that ticket",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not create ticket; print what would be created")
    return parser.parse_args(argv)


def _run_gate_command(project: Path, command: str) -> tuple[subprocess.CompletedProcess[str], str]:
    proc = subprocess.run(
        command,
        shell=True,
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )
    combined = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    return proc, combined


def _matched_failure_line(combined: str, fail_regex: str) -> str:
    if not fail_regex:
        return ""
    regex = re.compile(fail_regex, re.IGNORECASE)
    for line in combined.splitlines():
        if regex.search(line):
            return line.strip()
    return ""


def _extract_finding_keys_from_item(item: dict[str, object], marker_re: re.Pattern[str]) -> tuple[str | None, list[str]]:
    ticket_id = item.get("id")
    if not isinstance(ticket_id, str) or not ticket_id:
        return None, []
    found: list[str] = []
    for field in ("name", "description"):
        value = item.get(field)
        if isinstance(value, str):
            found.extend(marker_re.findall(value))
    return ticket_id, found


def _existing_finding_tickets(project: Path) -> dict[str, str]:
    proc = _run_planfile(project, ["ticket", "list", "--status", "all", "--format", "json"])
    if proc.returncode != 0:
        return {}
    try:
        payload = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, list):
        return {}

    keys: dict[str, str] = {}
    marker_re = re.compile(r"\[gate-finding:([^\]]+)\]")
    for item in payload:
        if not isinstance(item, dict):
            continue
        ticket_id, found_keys = _extract_finding_keys_from_item(item, marker_re)
        if not ticket_id:
            continue
        for key in found_keys:
            keys.setdefault(key, ticket_id)
    return keys


def _append_existing_note(
    *,
    project: Path,
    ticket_id: str,
    finding_key: str,
    gate: str,
    failing_line: str,
    command: str,
    dry_run: bool,
) -> bool:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    note = (
        f"[gate-finding:{finding_key}] still failing @ {timestamp}; "
        f"gate={gate}; line={failing_line}; cmd={command}"
    )
    if dry_run:
        print(f"[koru-gate] dry-run update ticket {ticket_id} with note:\n{note}")
        return True
    proc = _run_planfile(project, ["ticket", "update", ticket_id, "--note", note])
    if proc.returncode == 0:
        if proc.stdout:
            sys.stdout.write(proc.stdout)
        return True

    stderr_text = proc.stderr or ""
    if "No such option: --note" not in stderr_text:
        sys.stderr.write(stderr_text)
        return False

    fallback_prompt = f"{note}\n\n(autoupdate via koru-gate-capture fallback: ticket input)"
    fallback = _run_planfile(project, ["ticket", "input", ticket_id, "--prompt", fallback_prompt])
    if fallback.returncode != 0:
        sys.stderr.write(fallback.stderr)
        return False
    if fallback.stdout:
        sys.stdout.write(fallback.stdout)
    return True


def _create_ticket(
    *,
    project: Path,
    finding_key: str,
    gate: str,
    failing_line: str,
    command: str,
    next_step: str,
    priority: str,
    dry_run: bool,
) -> bool:
    title = f"[gate-finding:{finding_key}] {gate} gate failure"
    description = (
        f"Gate `{gate}` failed.\n\n"
        f"- Failing line: `{failing_line}`\n"
        f"- Command: `{command}`\n"
        f"- Next step: {next_step}\n"
    )
    if dry_run:
        print(f"[koru-gate] dry-run create ticket: {title}")
        print(description)
        return True
    cmd = [
        "ticket",
        "create",
        title,
        "--priority",
        priority,
        "--source",
        "koru-gate",
        "--label",
        "gates",
        "--label",
        f"gate-{gate}",
        "--description",
        description,
    ]
    proc = _run_planfile(project, cmd)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        return False
    sys.stdout.write(proc.stdout)
    return True


def _handle_existing_finding(
    *,
    args: argparse.Namespace,
    project: Path,
    existing: dict[str, str],
    finding_key: str,
    failing_line: str,
) -> int | None:
    if finding_key not in existing:
        return None
    ticket_id = existing[finding_key]
    if args.update_existing:
        ok = _append_existing_note(
            project=project,
            ticket_id=ticket_id,
            finding_key=finding_key,
            gate=args.gate,
            failing_line=failing_line,
            command=args.command,
            dry_run=args.dry_run,
        )
        return 0 if ok else 2
    print(f"[koru-gate] finding already tracked: {finding_key}")
    return 0


def main() -> int:
    args = _parse_args()
    project = Path(args.project).resolve()
    proc, combined = _run_gate_command(project, args.command)
    if combined:
        print(combined.rstrip())

    matched_line = _matched_failure_line(combined, args.fail_regex)

    failed = proc.returncode != 0 or bool(matched_line)
    if not failed:
        return 0

    failing_line = matched_line or _first_meaningful_line(combined)
    finding_seed = f"{args.gate}|{_normalize_line(failing_line)}"
    finding_key = hashlib.sha1(finding_seed.encode("utf-8")).hexdigest()[:12]

    existing = _existing_finding_tickets(project)
    existing_result = _handle_existing_finding(
        args=args,
        project=project,
        existing=existing,
        finding_key=finding_key,
        failing_line=failing_line,
    )
    if existing_result is not None:
        return existing_result

    ok = _create_ticket(
        project=project,
        finding_key=finding_key,
        gate=args.gate,
        failing_line=failing_line,
        command=args.command,
        next_step=args.next_step,
        priority=args.priority,
        dry_run=args.dry_run,
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
