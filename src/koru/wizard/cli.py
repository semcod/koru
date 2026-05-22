"""``koru wizard`` CLI entrypoint.

Orchestrates IDE detection → project pick → strategy decision tree →
first planfile ticket. All interaction goes through a small Prompter
abstraction so tests can drive a scripted run without stdin.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from koru.tasks import create_nl_task
from koru.wizard.ide import DetectedIDE, discover_installed_ides, summarize_ides
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
)


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


class StdinPrompter(Prompter):
    """Default prompter: prints prompt + options, reads a single line from stdin."""

    def __init__(self, *, stream_in=sys.stdin, stream_out=sys.stdout) -> None:
        self._in = stream_in
        self._out = stream_out

    def _print(self, msg: str) -> None:
        print(msg, file=self._out, flush=True)

    def ask_choice(self, prompt: str, options: tuple[TreeOption, ...]) -> TreeOption:
        if not options:
            raise RuntimeError("no options available for prompt: " + prompt)
        self._print("")
        self._print(prompt)
        for idx, opt in enumerate(options, 1):
            self._print(f"  [{idx}] {opt.label}")
        while True:
            raw = self._in.readline()
            if not raw:
                raise EOFError("wizard cancelled (EOF on stdin)")
            answer = raw.strip()
            if not answer:
                continue
            if answer.isdigit():
                idx = int(answer)
                if 1 <= idx <= len(options):
                    return options[idx - 1]
            for opt in options:
                if opt.id == answer or opt.label.lower() == answer.lower():
                    return opt
            self._print(f"  ! unknown answer: {answer!r}, try a number 1..{len(options)}")


class ScriptedPrompter(Prompter):
    """Test prompter: answers come from a queue of (node-question -> option-id) hints."""

    def __init__(self, answers: list[str]) -> None:
        self._answers = list(answers)

    def ask_choice(self, prompt: str, options: tuple[TreeOption, ...]) -> TreeOption:
        if not self._answers:
            raise RuntimeError(f"ScriptedPrompter: no answer left for prompt {prompt!r}")
        token = self._answers.pop(0)
        if token.isdigit():
            return options[int(token) - 1]
        for opt in options:
            if opt.id == token:
                return opt
        raise KeyError(f"ScriptedPrompter: unknown option {token!r} for {prompt!r}")


def _pick_ide(prompter: Prompter, ides: list[DetectedIDE]) -> DetectedIDE | None:
    if not ides:
        return None
    running_first = sorted(ides, key=lambda i: (not i.running, i.label.lower()))
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


def _emit_human(out, result: WizardResult, ticket_id: str | None) -> None:
    print("", file=out)
    print("✓ koru wizard finished", file=out)
    if result.chosen_ide:
        print(f"  IDE      : {result.chosen_ide.label}", file=out)
    print(f"  Project  : {result.chosen_project}", file=out)
    print(f"  Strategy : {' → '.join(result.path)}", file=out)
    print(f"  Ticket   : {result.ticket_title}", file=out)
    if ticket_id:
        print(f"  Created  : {ticket_id} (sprint=current)", file=out)
    else:
        print("  Created  : (skipped — use --create to write the ticket)", file=out)


def run_wizard(
    *,
    prompter: Prompter,
    strategies_path: Path | None = None,
    language: str | None = None,
    project_override: Path | None = None,
    create: bool = True,
    use_llx: bool = False,
    ide_override: list[DetectedIDE] | None = None,
    project_candidates_override: list[ProjectCandidate] | None = None,
) -> WizardResult:
    """Programmatic entrypoint used by both the CLI and tests."""
    tree = load_tree(strategies_path, language=language)

    ides = ide_override if ide_override is not None else discover_installed_ides()
    chosen_ide = _pick_ide(prompter, ides) if ides else None

    fallback = Path.cwd().resolve()
    candidates = (
        project_candidates_override
        if project_candidates_override is not None
        else propose_projects([chosen_ide] if chosen_ide else ides)
    )
    if project_override is not None:
        project = project_override.resolve()
    else:
        project = _pick_project(prompter, candidates, fallback=fallback)

    path, template = _walk_with_llx(tree, prompter, project, use_llx=use_llx)
    body = render_ticket_body(template, {"project": project.name, "hint_modules": "<module>"})

    ticket_id: str | None = None
    if create:
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
        ticket_id = task.ticket_id

    return WizardResult(
        chosen_ide=chosen_ide,
        chosen_project=project,
        path=path,
        ticket_id=ticket_id,
        ticket_title=template.title,
        ticket_body=body,
        skipped_creation=not create,
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="koru wizard",
        description=(
            "Interactive bootstrap: detect IDE, pick project, choose strategy, "
            "create first ticket."
        ),
    )
    p.add_argument(
        "--strategies",
        type=Path,
        default=None,
        help="Custom strategies.json",
    )
    p.add_argument(
        "--language",
        default=None,
        help="UI language (pl, en, …); defaults to strategies.json setting",
    )
    p.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Skip project picker, use this path",
    )
    p.add_argument(
        "--no-create",
        action="store_true",
        help="Walk the tree but don't write a ticket",
    )
    p.add_argument(
        "--llx",
        action="store_true",
        help="Ask llx to extend tree branches dynamically",
    )
    p.add_argument(
        "--detect-only",
        action="store_true",
        help="Print IDE / project candidates and exit (no prompts)",
    )
    p.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="--detect-only output format",
    )
    return p


def wizard_main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.detect_only:
        ides = discover_installed_ides()
        candidates = propose_projects(ides)
        if args.format == "json":
            payload = {
                "ides": [ide.to_dict() for ide in ides],
                "projects": [{"path": str(c.path), "source": c.source} for c in candidates],
                "llx_available": llx_available(),
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("Detected IDEs:")
            print(summarize_ides(ides))
            print("")
            print("Project candidates:")
            if candidates:
                for cand in candidates:
                    print(f"  - {cand.label()}")
            else:
                print("  (none)")
            print("")
            print(f"llx CLI on PATH: {'yes' if llx_available() else 'no'}")
        return 0

    if args.llx and not llx_available():
        print(
            "note: --llx requested but `llx` CLI not on PATH; falling back to static tree",
            file=sys.stderr,
        )

    prompter = StdinPrompter()
    try:
        result = run_wizard(
            prompter=prompter,
            strategies_path=args.strategies,
            language=args.language,
            project_override=args.project,
            create=not args.no_create,
            use_llx=args.llx,
        )
    except (EOFError, KeyboardInterrupt):
        print("\n(cancelled)", file=sys.stderr)
        return 130

    _emit_human(sys.stdout, result, result.ticket_id)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(wizard_main())
