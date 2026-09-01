"""Dedupe policy helpers for ``koru.scan --apply``."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import yaml

from koru.scan_types import Suggestion

SCAN_DEDUP_SKIP_STATUSES: frozenset[str] = frozenset(
    {"done", "canceled", "cancelled", "closed"},
)
_HISTORY_LOCATION_SCHEMA = "planfile.history-locations/v1"
_EVIDENCE_SCHEMA = "koru.ticket_evidence.v1"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_HISTORY_ID_RE = re.compile(r"^history-[A-Za-z0-9][A-Za-z0-9._-]*$")


def _source_context(entry: dict[str, Any], *, source: str) -> dict[str, Any] | None:
    entry_source = entry.get("source")
    if isinstance(entry_source, dict):
        if entry_source.get("tool") != source:
            return None
        context = entry_source.get("context")
        return context if isinstance(context, dict) else None
    if entry_source != source:
        return None
    return None


def _dedupe_key(context: dict[str, Any] | None) -> str | None:
    if context is None:
        return None
    value = context.get("dedupe_key")
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > 1024 or any(ord(char) < 32 for char in value):
        return None
    return value


def evidence_fingerprint(evidence: object) -> str | None:
    """Return a stable fingerprint for closed, artifact-bound scan evidence."""
    if not isinstance(evidence, dict) or evidence.get("schema") != _EVIDENCE_SCHEMA:
        return None
    kind = evidence.get("kind")
    artifact = evidence.get("artifact")
    if not isinstance(kind, str) or not kind.strip() or not isinstance(artifact, dict):
        return None
    path = artifact.get("path")
    sha256 = artifact.get("sha256")
    if not isinstance(path, str) or not isinstance(sha256, str):
        return None
    normalized_path = path.replace("\\", "/").strip()
    path_parts = normalized_path.split("/")
    if (
        not normalized_path
        or normalized_path.startswith("/")
        or ":" in path_parts[0]
        or any(part in {"", ".", ".."} for part in path_parts)
        or not _SHA256_RE.fullmatch(sha256)
    ):
        return None
    canonical = json.dumps(
        {
            "schema": _EVIDENCE_SCHEMA,
            "kind": kind.strip(),
            "artifact": {"path": normalized_path, "sha256": sha256.lower()},
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _active_dedupe_key(source: str, context: dict[str, Any] | None) -> str | None:
    key = _dedupe_key(context)
    return f"dedupe:{source}:{key}" if key is not None else None


def _history_dedupe_key(source: str, context: dict[str, Any] | None) -> str | None:
    key = _dedupe_key(context)
    fingerprint = evidence_fingerprint(context.get("evidence") if context else None)
    if key is None or fingerprint is None:
        return None
    return f"history:{source}:{key}:{fingerprint}"


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
        raw_context = entry_source.get("context")
        entry_context = raw_context if isinstance(raw_context, dict) else None
    elif entry_source == source:
        entry_context = None
    else:
        return
    status = str(entry.get("status") or "").lower()
    if status in skip_statuses:
        return
    active_key = _active_dedupe_key(source, entry_context)
    if active_key is not None:
        titles.add(active_key)
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
    entry_source = entry.get("source")
    entry_context = entry_source.get("context") if isinstance(entry_source, dict) else None
    if isinstance(entry_source, dict) and isinstance(entry_source.get("tool"), str):
        active_key = _active_dedupe_key(entry_source["tool"], entry_context)
        if active_key is not None:
            titles.add(active_key)
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
        entries = list(tickets.values())
    elif isinstance(tickets, list):
        entries = tickets
    else:
        return set()
    titles: set[str] = set()
    for entry in entries:
        add_existing_scan_title_keys(titles, entry, source=source)
    return titles


def _ticket_entries(path: Path) -> list[object]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    sprint = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint.get("tickets") if isinstance(sprint, dict) else None
    if isinstance(tickets, dict):
        return list(tickets.values())
    if isinstance(tickets, list):
        return list(tickets)
    return []


def _indexed_history_ids(project: Path) -> set[str]:
    index_path = project / ".planfile" / "index" / "history-locations.yaml"
    try:
        payload = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return set()
    if not isinstance(payload, dict) or payload.get("schema") != _HISTORY_LOCATION_SCHEMA:
        return set()
    locations = payload.get("tickets")
    if not isinstance(locations, dict):
        return set()
    return {
        value
        for value in locations.values()
        if isinstance(value, str) and _HISTORY_ID_RE.fullmatch(value)
    }


def _trusted_child_file(parent: Path, candidate: Path) -> bool:
    try:
        parent_resolved = parent.resolve(strict=True)
        candidate_resolved = candidate.resolve(strict=True)
        candidate_resolved.relative_to(parent_resolved)
    except (OSError, ValueError):
        return False
    return candidate_resolved.is_file()


def existing_scan_history_keys(project: Path, *, source: str) -> set[str]:
    """Load evidence-bound terminal dedupe keys from trusted Planfile history."""
    sprints_dir = project / ".planfile" / "sprints"
    history_paths = {sprints_dir / f"{history_id}.yaml" for history_id in _indexed_history_ids(project)}
    try:
        history_paths.update(sprints_dir.glob("history-*.yaml"))
    except OSError:
        pass

    keys: set[str] = set()
    for history_path in sorted(history_paths):
        if (
            history_path.parent != sprints_dir
            or not _HISTORY_ID_RE.fullmatch(history_path.stem)
            or not _trusted_child_file(sprints_dir, history_path)
        ):
            continue
        for entry in _ticket_entries(history_path):
            if not isinstance(entry, dict):
                continue
            status = str(entry.get("status") or "").lower()
            if status not in SCAN_DEDUP_SKIP_STATUSES:
                continue
            context = _source_context(entry, source=source)
            history_key = _history_dedupe_key(source, context)
            if history_key is not None:
                keys.add(history_key)
    return keys


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
    """Resolve active legacy keys plus evidence-bound Planfile history keys."""
    history_keys = existing_scan_history_keys(project, source=source)
    if runner is None:
        titles = sprint_loader(project, source)
        if titles or history_keys:
            return titles | history_keys

    use_runner = runner or default_runner
    titles = load_existing_scan_titles(
        project,
        ["planfile", "ticket", "list", "--source", source, "--format", "json"],
        source=source,
        runner=use_runner,
    )
    if titles:
        return titles | history_keys
    titles = load_existing_scan_titles(
        project,
        ["planfile", "ticket", "list", "--format", "json"],
        source=source,
        runner=use_runner,
        filter_source=True,
    )
    return titles | history_keys


def scan_duplicate_skip(
    suggestion: Suggestion,
    existing: set[str],
    *,
    source: str | None = None,
    suggestion_dedupe_key: Callable[[str, Suggestion], str] | None = None,
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
    if source is None or suggestion_dedupe_key is None:
        return None
    context_key = _dedupe_key(suggestion.source_context)
    dedupe_key = context_key or suggestion_dedupe_key(source, suggestion)
    if f"dedupe:{source}:{dedupe_key}" in existing:
        return (
            "duplicate_dedupe_key",
            f"pomijam ze skanu (aktywny dedupe_key): {suggestion.title} "
            f"(signal={suggestion.signal})",
        )
    fingerprint = evidence_fingerprint(suggestion.source_context.get("evidence"))
    if fingerprint and f"history:{source}:{dedupe_key}:{fingerprint}" in existing:
        return (
            "duplicate_history_evidence",
            f"pomijam ze skanu (identyczny dowód w historii): {suggestion.title} "
            f"(signal={suggestion.signal})",
        )
    return None
