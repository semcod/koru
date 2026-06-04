"""Registry-loading checks for ``koru doctor``."""

from __future__ import annotations

from pathlib import Path

from koru.doctor_constants import PASS, WARN


def check_agent_backends_registry(_project: Path) -> tuple[str, str]:
    del _project
    from koru.agent_backends import list_agent_backend_ids

    ids = list_agent_backend_ids()
    return PASS, f"{len(ids)} profiles: {', '.join(ids)}"


def check_interface_registry(_project: Path) -> tuple[str, str]:
    del _project
    from koru.interface_registry import list_interface_ids, summarize_interfaces_by_family

    ids = list_interface_ids()
    if not ids:
        return WARN, "0 interfaces loaded"
    families = summarize_interfaces_by_family()
    family_summary = ", ".join(f"{name}={count}" for name, count in sorted(families.items()))
    preview = f"{', '.join(ids[:5])}{' ...' if len(ids) > 5 else ''}"
    return PASS, f"{len(ids)} interfaces: {preview}; families: {family_summary}"
