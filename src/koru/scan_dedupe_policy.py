"""Dedupe policy helpers for ``koru.scan --apply``."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import yaml

from koru.scan_types import Suggestion

SCAN_DEDUP_SKIP_STATUSES: frozenset[str] = frozenset(
    {"done", "canceled", "cancelled", "closed"},
)


def add_existing_scan_title_keys(
    titles: set[str],
    entry: object,
    *,
    source: str,
    skip_statuses: frozenset[str] = SCAN_DEDUP_SKIP_STATUSES,
) -> None:
    if not isinstance(entry, dict):
        return
    entry_source = entry.get("source")
    if isinstance(entry_source, dict):
        if entry_source.get("tool") != source:
            return
    elif entry_source != source:
        return
    status = str(entry.get("status") or "").lower()
    if status in skip_statuses:
        return
    entry_context = entry_source.get("context") if isinstance(entry_source, dict) else None
    if isinstance(entry_context, dict):
        signal = entry_context.get("signal")
        if isinstance(signal, str) and signal:
            titles.add(f"signal:{signal}")
    name = entry.get("name") or entry.get("title")
    if isinstance(name, str):
        titles.add(name)


def add_active_scan_title_keys(
    titles: set[str],
    entry: object,
    *,
    skip_statuses: frozenset[str] = SCAN_DEDUP_SKIP_STATUSES,
) -> None:
    if not isinstance(entry, dict):
        return
    status = str(entry.get("status") or "").lower()
    if status in skip_statuses:
        return
    entry_context = entry.get("source", {}).get("context")
    if isinstance(entry_context, dict):
        signal = entry_context.get("signal")
        if isinstance(signal, str) and signal:
            titles.add(f"signal:{signal}")
    name = entry.get("name") or entry.get("title")
    if isinstance(name, str):
        titles.add(name)


def existing_scan_titles_from_sprint(
    project: Path,
    *,
    source: str,
) -> set[str]:
    sprint_path = project / ".planfile" / "sprints" / "current.yaml"
    try:
        data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return set()
    sprint = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint.get("tickets") if isinstance(sprint, dict) else None
    if isinstance(tickets, dict):
        entries = tickets.values()
    elif isinstance(tickets, list):
        entries = tickets
    else:
        return set()
    titles: set[str] = set()
    for entry in entries:
        add_existing_scan_title_keys(titles, entry, source=source)
    return titles


def scan_ticket_list_payload(
    project: Path,
    cmd: list[str],
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
) -> list[Any]:
    try:
        result = runner(cmd, project)
    except (FileNotFoundError, OSError):
        return []
    if result.returncode != 0:
        return []
    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def existing_scan_titles_from_payload(
    payload: list[Any],
    *,
    source: str,
    filter_source: bool = False,
) -> set[str]:
    titles: set[str] = set()
    for entry in payload:
        if filter_source:
            add_existing_scan_title_keys(titles, entry, source=source)
            continue
        add_active_scan_title_keys(titles, entry)
    return titles


def load_existing_scan_titles(
    project: Path,
    cmd: list[str],
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
    filter_source: bool = False,
) -> set[str]:
    payload = scan_ticket_list_payload(project, cmd, runner)
    return existing_scan_titles_from_payload(
        payload,
        source=source,
        filter_source=filter_source,
    )


def existing_scan_titles(
    project: Path,
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None,
    default_runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
    sprint_loader: Callable[[Path, str], set[str]],
) -> set[str]:
    """Resolve active scan titles for dedupe across apply runs."""
    if runner is None:
        titles = sprint_loader(project, source)
        if titles:
            return titles

    use_runner = runner or default_runner
    titles = load_existing_scan_titles(
        project,
        ["planfile", "ticket", "list", "--source", source, "--format", "json"],
        source=source,
        runner=use_runner,
    )
    if titles:
        return titles
    return load_existing_scan_titles(
        project,
        ["planfile", "ticket", "list", "--format", "json"],
        source=source,
        runner=use_runner,
        filter_source=True,
    )


def scan_duplicate_skip(
    suggestion: Suggestion,
    existing: set[str],
) -> tuple[str, str] | None:
    if suggestion.title in existing:
        return (
            "duplicate_title",
            f"pomijam ze skanu (duplikat tytułu): {suggestion.title} "
            f"(signal={suggestion.signal})",
        )
    if f"signal:{suggestion.signal}" in existing:
        return (
            "duplicate_signal",
            f"pomijam ze skanu (duplikat sygnału): {suggestion.title} "
            f"(signal={suggestion.signal} — istnieje aktywny ticket dla tego sygnału)",
        )
    return None
