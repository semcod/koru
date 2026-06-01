"""Wizard orchestration logic for ``koru wizard``.

Core wizard flow: IDE detection → project pick → strategy tree walk → ticket creation.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from koru.tasks import create_nl_task
from koru.wizard.ide import DetectedIDE, discover_installed_ides
from koru.wizard.ide_install import offer_ide_install
from koru.wizard.llx import expand_node, llx_available
from koru.wizard.project import ProjectCandidate, propose_projects
from koru.wizard.tree import (
    Prompter,
    StrategyTree,
    TicketTemplate,
    TreeNode,
    TreeOption,
    load_tree,
    render_ticket_body,
    walk_path,
)
from koruide.ide import detect_terminal_host_ide_id, normalize_ide_id


@dataclass
class WizardResult:
    """Final summary printed at the end of a wizard run."""

    chosen_ide: DetectedIDE | None
    chosen_project: Path
    path: list[str]
    ticket_id: str | None
    ticket_title: str
    ticket_body: str
    skipped_creation: bool
    next_steps: tuple[str, ...] = ()
    quick_mode: bool = False


def _pick_ide(
    prompter: Prompter,
    ides: list[DetectedIDE],
    *,
    auto_pick: bool = True,
) -> DetectedIDE | None:
    if not ides:
        return None
    running_first = sorted(ides, key=lambda i: (not i.running, i.label.lower()))
    if auto_pick:
        auto_picked = _auto_pick_ide(running_first)
        if auto_picked is not None:
            return auto_picked
    options = tuple(
        TreeOption(
            id=ide.id,
            label=(
                f"{ide.label}  "
                f"[{'running pid=' + str(ide.pid) if ide.running else 'installed'}]  "
                f"{ide.path}"
            ),
        )
        for ide in running_first
    ) + (TreeOption(id="__none", label="(skip — pick project manually)"),)
    chosen = prompter.ask_choice("Wybierz IDE / Pick an IDE:", options)
    if chosen.id == "__none":
        return None
    return next(ide for ide in running_first if ide.id == chosen.id)


def _find_ide_by_id(
    ides: list[DetectedIDE],
    ide_id: str | None,
    *,
    running_only: bool = False,
) -> DetectedIDE | None:
    normalized = normalize_ide_id(ide_id)
    if not normalized or normalized == "auto":
        return None
    matches = [ide for ide in ides if ide.id == normalized]
    if running_only:
        matches = [ide for ide in matches if ide.running]
    if not matches:
        return None
    return next((ide for ide in matches if ide.running), matches[0])


def _auto_pick_ide(ides: list[DetectedIDE]) -> DetectedIDE | None:
    """Choose an IDE without prompting only when the runtime context is clear."""
    for env_key in ("KORU_AUTOPILOT_INSTANCE", "KORU_AUTOPILOT_IDE"):
        selected = _find_ide_by_id(ides, os.environ.get(env_key), running_only=True)
        if selected is not None:
            return selected

    running = [ide for ide in ides if ide.running]
    if len(running) == 1:
        return running[0]

    selected = _find_ide_by_id(ides, detect_terminal_host_ide_id())
    if selected is not None:
        return selected
    return None


def _pick_project(
    prompter: Prompter,
    candidates: list[ProjectCandidate],
    *,
    fallback: Path,
) -> Path:
    if not candidates:
        return fallback
    options = tuple(
        TreeOption(id=str(idx), label=cand.label())
        for idx, cand in enumerate(candidates)
    ) + (TreeOption(id="__cwd", label=f"(use shell cwd: {fallback})"),)
    chosen = prompter.ask_choice("Wybierz projekt / Pick a project:", options)
    if chosen.id == "__cwd":
        return fallback
    return candidates[int(chosen.id)].path


def _maybe_extend_node_with_llx(
    tree: StrategyTree,
    project: Path,
    node: TreeNode,
    *,
    use_llx: bool,
) -> TreeNode:
    if not use_llx or not llx_available():
        return node
    expansion = expand_node(project, node, ticket_ids=list(tree.tickets.keys()))
    if expansion is None:
        return node
    return TreeNode(
        id=node.id,
        prompt=node.prompt,
        options=node.options + expansion.extra_options,
    )


def _walk_with_llx(
    tree: StrategyTree,
    prompter: Prompter,
    project: Path,
    *,
    use_llx: bool,
) -> tuple[list[str], TicketTemplate]:
    path: list[str] = []
    current = tree.root()
    while True:
        current = _maybe_extend_node_with_llx(tree, project, current, use_llx=use_llx)
        choice = prompter.ask_choice(current.prompt, current.options)
        path.append(choice.id)
        if choice.ticket:
            return path, tree.ticket(choice.ticket)
        if choice.next_node:
            current = tree.node(choice.next_node)
            continue
        raise RuntimeError(f"option {choice.id!r} on node {current.id!r} has no next/ticket")


def _render_next_steps(steps: tuple[str, ...], ticket_id: str | None) -> list[str]:
    """Render the post-creation guidance lines with ``{{ticket_id}}`` substitution."""
    placeholder = ticket_id or "PLF-XXX"
    return [step.replace("{{ticket_id}}", placeholder) for step in steps]


def emit_human(out, result: WizardResult, ticket_id: str | None) -> None:
    print("", file=out)
    suffix = " --quick" if result.quick_mode else ""
    print(f"✓ koru wizard finished{suffix}", file=out)
    if result.chosen_ide:
        print(f"  IDE      : {result.chosen_ide.label}", file=out)
    print(f"  Project  : {result.chosen_project}", file=out)
    print(f"  Strategy : {' → '.join(result.path)}", file=out)
    print(f"  Ticket   : {result.ticket_title}", file=out)
    if ticket_id:
        print(f"  Created  : {ticket_id} (sprint=current)", file=out)
    else:
        print("  Created  : (skipped — use --create to write the ticket)", file=out)
    if result.next_steps:
        print("", file=out)
        print("Co teraz / What's next:", file=out)
        for idx, step in enumerate(_render_next_steps(result.next_steps, ticket_id), 1):
            print(f"  {idx}. {step}", file=out)


def _resolve_quick_path(
    tree: StrategyTree,
    explicit_strategy: str | None,
) -> tuple[str, ...]:
    """Pick the option-id path used in ``--quick`` mode."""
    if explicit_strategy:
        parts = tuple(p.strip() for p in explicit_strategy.split(".") if p.strip())
        if not parts:
            raise ValueError("--strategy is empty after parsing")
        return parts
    if tree.quick_default_path:
        return tree.quick_default_path
    raise ValueError(
        "strategies.json has no 'quick_default.path'; pass --strategy a.b.c "
        "to choose a path explicitly"
    )


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


def _wizard_result(
    *,
    chosen_ide: DetectedIDE | None,
    project: Path,
    path: list[str],
    template: TicketTemplate,
    tree: StrategyTree,
    ticket_id: str | None,
    body: str,
    create: bool,
    quick: bool,
) -> WizardResult:
    return WizardResult(
        chosen_ide=chosen_ide,
        chosen_project=project,
        path=path,
        ticket_id=ticket_id,
        ticket_title=template.title,
        ticket_body=body,
        skipped_creation=not create,
        next_steps=tree.effective_next_steps(template.id),
        quick_mode=quick,
    )


def _run_quick_wizard(
    tree: StrategyTree,
    *,
    project_override: Path | None,
    create: bool,
    quick_strategy: str | None,
) -> WizardResult:
    path = list(_resolve_quick_path(tree, quick_strategy))
    consumed, template = walk_path(tree, path)
    project = (project_override or Path.cwd()).resolve()
    ticket_id, body = _finalise_ticket(template, project, create=create)
    return _wizard_result(
        chosen_ide=None,
        project=project,
        path=consumed,
        template=template,
        tree=tree,
        ticket_id=ticket_id,
        body=body,
        create=create,
        quick=True,
    )


def _resolve_wizard_ide(
    prompter: Prompter,
    ide_override: list[DetectedIDE] | None,
) -> tuple[list[DetectedIDE], DetectedIDE | None]:
    ides = ide_override if ide_override is not None else discover_installed_ides()
    if not ides and ide_override is None:
        ides = offer_ide_install(prompter, sys.stdout)
        chosen_ide = _pick_ide(prompter, ides, auto_pick=False) if ides else None
        return ides, chosen_ide
    chosen_ide = _pick_ide(prompter, ides) if ides else None
    return ides, chosen_ide


def _resolve_wizard_project(
    prompter: Prompter,
    *,
    project_override: Path | None,
    project_candidates_override: list[ProjectCandidate] | None,
    ides: list[DetectedIDE],
    chosen_ide: DetectedIDE | None,
) -> Path:
    if project_override is not None:
        return project_override.resolve()
    fallback = Path.cwd().resolve()
    candidates = (
        project_candidates_override
        if project_candidates_override is not None
        else propose_projects([chosen_ide] if chosen_ide else ides)
    )
    return _pick_project(prompter, candidates, fallback=fallback)


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
    """Programmatic entrypoint used by both the CLI and tests."""
    tree = load_tree(
        strategies_path, language=language, bilingual_separator=bilingual_separator
    )

    if quick:
        return _run_quick_wizard(
            tree,
            project_override=project_override,
            create=create,
            quick_strategy=quick_strategy,
        )

    ides, chosen_ide = _resolve_wizard_ide(prompter, ide_override)
    project = _resolve_wizard_project(
        prompter,
        project_override=project_override,
        project_candidates_override=project_candidates_override,
        ides=ides,
        chosen_ide=chosen_ide,
    )
    path, template = _walk_with_llx(tree, prompter, project, use_llx=use_llx)
    ticket_id, body = _finalise_ticket(template, project, create=create)
    return _wizard_result(
        chosen_ide=chosen_ide,
        project=project,
        path=path,
        template=template,
        tree=tree,
        ticket_id=ticket_id,
        body=body,
        create=create,
        quick=False,
    )
