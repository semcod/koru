"""``koru wizard`` CLI entrypoint.

This module now serves as a compatibility shim, re-exporting symbols from
the refactored wizard submodules.

The actual implementation has been split into:
- koru.wizard.prompters: StdinPrompter, ScriptedPrompter
- koru.wizard.ide_install: IDE installation logic
- koru.wizard.orchestrator: WizardResult, run_wizard, emit_human
- koru.wizard.cli_main: CLI argument parsing and wizard_main
"""

from __future__ import annotations

from pathlib import Path

from koru import tasks as _tasks
from koru.wizard import ide as _ide
from koru.wizard import orchestrator as _orchestrator
from koru.wizard import project as _project

# Re-export main entrypoint
from koru.wizard.cli_main import wizard_main

# Re-export data classes for backward compatibility
from koru.wizard.ide import DetectedIDE

# Re-export functions for backward compatibility
from koru.wizard.ide_install import (
    _IDE_INSTALL_CATALOG,
    _IDE_INSTALL_ORDER,
    _MANAGER_BINARIES,
    IDEInstallSpec,
    offer_ide_install,
)
from koru.wizard.orchestrator import (
    WizardResult,
    _render_next_steps,
    emit_human,
)
from koru.wizard.project import ProjectCandidate
from koru.wizard.prompters import ScriptedPrompter, StdinPrompter
from koru.wizard.tree import Prompter, TicketTemplate, render_ticket_body


def discover_installed_ides() -> list[DetectedIDE]:
    """Return installed IDEs, preserving the old monkeypatch target in this module."""
    return _ide.discover_installed_ides()


def propose_projects(ides: list[DetectedIDE]) -> list[ProjectCandidate]:
    """Return project candidates, preserving the old monkeypatch target in this module."""
    return _project.propose_projects(ides)


def create_nl_task(*args, **kwargs):
    """Create a Planfile task via the legacy ``koru.wizard.cli`` symbol."""
    return _tasks.create_nl_task(*args, **kwargs)


_DEFAULT_DISCOVER_INSTALLED_IDES = discover_installed_ides
_DEFAULT_PROPOSE_PROJECTS = propose_projects
_DEFAULT_CREATE_NL_TASK = create_nl_task


def _finalise_ticket(
    template: TicketTemplate,
    project: Path,
    *,
    create: bool,
) -> tuple[str | None, str]:
    """Render the ticket body, optionally write it to the planfile."""
    body = render_ticket_body(
        template, {"project": project.name, "hint_modules": "<module>"}
    )
    if not create:
        return None, body
    scaffold = {
        "title": template.title,
        "labels": list(template.labels) + ["koru-wizard"],
        "executor_kind": "human",
        "executor_mode": "interactive",
    }
    task = create_nl_task(
        project,
        f"{template.title}\n\n{body}",
        priority=template.priority,
        scaffold=scaffold,
    )
    return task.ticket_id, body


def run_wizard(
    *,
    prompter: Prompter,
    strategies_path: Path | None = None,
    language: str | list[str] | None = None,
    project_override: Path | None = None,
    create: bool = True,
    use_llx: bool = False,
    ide_override: list[DetectedIDE] | None = None,
    project_candidates_override: list[ProjectCandidate] | None = None,
    quick: bool = False,
    quick_strategy: str | None = None,
    bilingual_separator: str = " · ",
) -> WizardResult:
    """Programmatic entrypoint kept compatible with pre-refactor patch points."""
    use_legacy_patch_points = any(
        (
            discover_installed_ides is not _DEFAULT_DISCOVER_INSTALLED_IDES,
            propose_projects is not _DEFAULT_PROPOSE_PROJECTS,
            create_nl_task is not _DEFAULT_CREATE_NL_TASK,
        )
    )
    if not use_legacy_patch_points:
        return _orchestrator.run_wizard(
            prompter=prompter,
            strategies_path=strategies_path,
            language=language,
            project_override=project_override,
            create=create,
            use_llx=use_llx,
            ide_override=ide_override,
            project_candidates_override=project_candidates_override,
            quick=quick,
            quick_strategy=quick_strategy,
            bilingual_separator=bilingual_separator,
        )

    previous_discover = _orchestrator.discover_installed_ides
    previous_propose = _orchestrator.propose_projects
    previous_create = _orchestrator.create_nl_task
    _orchestrator.discover_installed_ides = discover_installed_ides
    _orchestrator.propose_projects = propose_projects
    _orchestrator.create_nl_task = create_nl_task
    try:
        return _orchestrator.run_wizard(
            prompter=prompter,
            strategies_path=strategies_path,
            language=language,
            project_override=project_override,
            create=create,
            use_llx=use_llx,
            ide_override=ide_override,
            project_candidates_override=project_candidates_override,
            quick=quick,
            quick_strategy=quick_strategy,
            bilingual_separator=bilingual_separator,
        )
    finally:
        _orchestrator.discover_installed_ides = previous_discover
        _orchestrator.propose_projects = previous_propose
        _orchestrator.create_nl_task = previous_create


__all__ = [
    "StdinPrompter",
    "ScriptedPrompter",
    "WizardResult",
    "IDEInstallSpec",
    "wizard_main",
    "run_wizard",
    "emit_human",
    "offer_ide_install",
    "discover_installed_ides",
    "propose_projects",
    "create_nl_task",
    "_finalise_ticket",
    "_render_next_steps",
    "_IDE_INSTALL_CATALOG",
    "_IDE_INSTALL_ORDER",
    "_MANAGER_BINARIES",
]
