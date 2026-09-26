"""Task profile matching, ticket ordering, and completion heuristics for execution planning."""

from __future__ import annotations

import fnmatch
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from koru.autonomy.ide_work import _current_sprint_tickets

_PRIORITY_RANK = {"critical": 0, "high": 1, "normal": 2, "low": 3}
_SKIP_TICKET_IDS = frozenset({"STARTER-001", "STARTER-002"})
_OPEN_STATUSES = frozenset({"open", "ready", "todo"})


@lru_cache(maxsize=1)
def load_task_profiles() -> dict[str, Any]:
    raw = resources.files("koru.autonomy").joinpath("task_profiles.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    return data if isinstance(data, dict) else {}


def ticket_labels(ticket: dict[str, Any]) -> set[str]:
    labels = ticket.get("labels")
    if isinstance(labels, list):
        return {str(label).lower() for label in labels}
    return set()


def ticket_signal(ticket: dict[str, Any]) -> str | None:
    source = ticket.get("source")
    if not isinstance(source, dict):
        return None
    context = source.get("context")
    if isinstance(context, dict) and context.get("signal"):
        return str(context["signal"])
    return None


def ticket_name(ticket: dict[str, Any]) -> str:
    return str(ticket.get("name") or ticket.get("id") or "").strip()


def profile_labels_match(labels: set[str], wanted: Any) -> bool:
    if not wanted:
        return True
    return bool(labels.intersection({str(value).lower() for value in wanted}))


def ticket_matches_profile(match: dict[str, Any], ticket: dict[str, Any]) -> bool:
    labels = ticket_labels(ticket)
    labels_any = match.get("labels_any") or []
    if not profile_labels_match(labels, labels_any):
        return False
    signal = ticket_signal(ticket)
    signals_any = match.get("signals_any") or []
    if signals_any and (signal is None or signal not in signals_any):
        return False
    patterns = match.get("name_patterns") or []
    name = ticket_name(ticket)
    if patterns and not any(fnmatch.fnmatch(name, str(pat)) for pat in patterns):
        return False
    return bool(labels_any or signals_any or patterns)


def profile_matches(profile: dict[str, Any], *, ticket: dict[str, Any] | None, phase: str) -> bool:
    match = profile.get("match")
    if not isinstance(match, dict):
        return False
    if match.get("phase"):
        return str(match["phase"]) == phase
    if ticket is None:
        return False
    return ticket_matches_profile(match, ticket)


def profile_order(profiles_doc: dict[str, Any]) -> tuple[str, ...]:
    defaults = profiles_doc.get("defaults")
    if isinstance(defaults, dict):
        order = defaults.get("profile_order")
        if isinstance(order, list):
            return tuple(str(item).strip() for item in order if str(item).strip())
    return ("cc_hotspot_refactor", "god_module_split")


def fallback_profile_id(profiles_doc: dict[str, Any]) -> str:
    defaults = profiles_doc.get("defaults")
    if isinstance(defaults, dict):
        token = str(defaults.get("fallback_profile") or "").strip()
        if token:
            return token
    return "god_module_split"


def select_profile(
    ticket: dict[str, Any] | None,
    phase: str,
    profiles_doc: dict[str, Any] | None = None,
) -> tuple[str | None, dict[str, Any] | None]:
    doc = profiles_doc if profiles_doc is not None else load_task_profiles()
    profiles = doc.get("profiles") or {}
    if not isinstance(profiles, dict):
        return None, None
    order = profile_order(doc)
    ordered_ids = [pid for pid in order if pid in profiles]
    ordered_ids.extend(pid for pid in profiles if pid not in ordered_ids)
    for profile_id in ordered_ids:
        profile = profiles.get(profile_id)
        if isinstance(profile, dict) and profile_matches(profile, ticket=ticket, phase=phase):
            return str(profile_id), profile
    return None, None


def target_source_lines(project: Path, ticket: dict[str, Any]) -> int | None:
    files = ticket.get("files")
    if not isinstance(files, list):
        return None
    for entry in files:
        rel = str(entry).strip()
        if not rel or rel.startswith("project/") or rel.endswith(".toon.yaml"):
            continue
        path = project / rel
        if not path.is_file():
            continue
        try:
            return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            return None
    return None


def first_code_file(project: Path, ticket: dict[str, Any]) -> Path | None:
    files = ticket.get("files")
    if not isinstance(files, list):
        return None
    for entry in files:
        rel = str(entry).strip()
        if not rel or rel.endswith(".toon.yaml") or rel.startswith("project/"):
            continue
        candidate = project / rel
        if candidate.is_file():
            return candidate
    return None


def count_lines(path: Path) -> int | None:
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))
    except OSError:
        return None


def evidence_artifact_sha(ticket: dict[str, Any]) -> str | None:
    source = ticket.get("source")
    if not isinstance(source, dict):
        return None
    context = source.get("context")
    if not isinstance(context, dict):
        return None
    evidence = context.get("evidence")
    if not isinstance(evidence, dict):
        return None
    files = evidence.get("files")
    if isinstance(files, list) and files:
        first = files[0]
        if isinstance(first, dict) and first.get("sha256"):
            return str(first["sha256"])
    artifact = evidence.get("artifact")
    if isinstance(artifact, dict) and artifact.get("sha256"):
        return str(artifact["sha256"])
    return None


def file_sha256(path: Path) -> str | None:
    import hashlib

    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def ticket_likely_complete(project: Path, ticket: dict[str, Any]) -> bool:
    labels = ticket_labels(ticket)
    lines = target_source_lines(project, ticket)
    if lines is not None:
        if "god-module" in labels and lines < 250:
            return True
        if "cyclomatic" in labels and lines < 80:
            return True
    evidence_sha = evidence_artifact_sha(ticket)
    if evidence_sha:
        code_file = first_code_file(project, ticket)
        if code_file is not None:
            current_sha = file_sha256(code_file)
            if current_sha and current_sha != evidence_sha:
                if lines is not None and lines < 250:
                    return True
    return False


def ticket_sort_key(project: Path, ticket: dict[str, Any]) -> tuple[int, int, str]:
    priority_label = str(ticket.get("priority") or "normal").lower()
    priority = _PRIORITY_RANK.get(priority_label, 99)
    labels = ticket_labels(ticket)
    deprioritize = 0
    lines = target_source_lines(project, ticket)
    if lines is not None:
        if "god-module" in labels and lines < 250:
            deprioritize = 1
        if "cyclomatic" in labels and lines < 120:
            deprioritize = 1
    return (priority + deprioritize, lines or 99999, str(ticket.get("id") or ""))


def count_skipped_complete(project: Path) -> int:
    count = 0
    for ticket in _current_sprint_tickets(project):
        ticket_id = str(ticket.get("id") or "").strip().upper()
        status = str(ticket.get("status") or "").lower()
        if ticket_id in _SKIP_TICKET_IDS:
            continue
        if status not in _OPEN_STATUSES:
            continue
        if ticket_likely_complete(project, ticket):
            count += 1
    return count


def open_refactor_tickets(project: Path) -> list[dict[str, Any]]:
    tickets: list[dict[str, Any]] = []
    for ticket in _current_sprint_tickets(project):
        ticket_id = str(ticket.get("id") or "").strip().upper()
        status = str(ticket.get("status") or "").lower()
        if ticket_id in _SKIP_TICKET_IDS:
            continue
        if status not in _OPEN_STATUSES:
            continue
        if ticket_likely_complete(project, ticket):
            continue
        tickets.append(ticket)
    tickets.sort(key=lambda t: ticket_sort_key(project, t))
    return tickets
