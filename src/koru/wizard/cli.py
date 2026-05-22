"""``koru wizard`` CLI entrypoint.

Orchestrates IDE detection → project pick → strategy decision tree →
first planfile ticket. All interaction goes through a small Prompter
abstraction so tests can drive a scripted run without stdin.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from koru.tasks import create_nl_task
from koru.wizard.ide import DetectedIDE, discover_installed_ides, summarize_ides
from koru.wizard.llx import expand_node, llx_available
from koru.wizard.project import ProjectCandidate, propose_projects
from koru.wizard.templates import format_templates_list, resolve_strategies_source
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


@dataclass(frozen=True)
class IDEInstallSpec:
    ide_id: str
    label: str
    homepage: str
    commands: dict[str, tuple[str, ...]]


_IDE_INSTALL_ORDER = (
    "vscode",
    "vscodium",
    "zed",
    "jetbrains",
    "cursor",
    "windsurf",
    "antigravity",
)

_IDE_INSTALL_CATALOG: dict[str, IDEInstallSpec] = {
    "vscode": IDEInstallSpec(
        ide_id="vscode",
        label="VS Code",
        homepage="https://code.visualstudio.com/download",
        commands={
            "snap": ("sudo", "snap", "install", "code", "--classic"),
            "flatpak": ("flatpak", "install", "-y", "flathub", "com.visualstudio.code"),
            "apt": ("sudo", "apt-get", "install", "-y", "code"),
            "dnf": ("sudo", "dnf", "install", "-y", "code"),
            "pacman": ("sudo", "pacman", "-S", "--noconfirm", "code"),
            "zypper": ("sudo", "zypper", "install", "-y", "code"),
        },
    ),
    "vscodium": IDEInstallSpec(
        ide_id="vscodium",
        label="VSCodium",
        homepage="https://vscodium.com/",
        commands={
            "flatpak": ("flatpak", "install", "-y", "flathub", "com.vscodium.codium"),
            "snap": ("sudo", "snap", "install", "codium", "--classic"),
            "apt": ("sudo", "apt-get", "install", "-y", "codium"),
            "dnf": ("sudo", "dnf", "install", "-y", "codium"),
            "pacman": ("sudo", "pacman", "-S", "--noconfirm", "vscodium"),
            "zypper": ("sudo", "zypper", "install", "-y", "codium"),
        },
    ),
    "zed": IDEInstallSpec(
        ide_id="zed",
        label="Zed",
        homepage="https://zed.dev/download",
        commands={
            "flatpak": ("flatpak", "install", "-y", "flathub", "dev.zed.Zed"),
        },
    ),
    "jetbrains": IDEInstallSpec(
        ide_id="jetbrains",
        label="JetBrains IDEA Community",
        homepage="https://www.jetbrains.com/idea/download/",
        commands={
            "flatpak": (
                "flatpak",
                "install",
                "-y",
                "flathub",
                "com.jetbrains.IntelliJ-IDEA-Community",
            ),
            "snap": (
                "sudo",
                "snap",
                "install",
                "intellij-idea-community",
                "--classic",
            ),
        },
    ),
    "cursor": IDEInstallSpec(
        ide_id="cursor",
        label="Cursor",
        homepage="https://cursor.com/downloads",
        commands={},
    ),
    "windsurf": IDEInstallSpec(
        ide_id="windsurf",
        label="Windsurf",
        homepage="https://windsurf.com/",
        commands={},
    ),
    "antigravity": IDEInstallSpec(
        ide_id="antigravity",
        label="Antigravity",
        homepage="https://www.antigravity.dev/",
        commands={},
    ),
}

_MANAGER_BINARIES = {
    "apt": "apt-get",
    "dnf": "dnf",
    "pacman": "pacman",
    "zypper": "zypper",
    "snap": "snap",
    "flatpak": "flatpak",
}


class StdinPrompter(Prompter):
    """Default prompter: prints prompt + options, reads a single line from stdin.

    Supports a ``?`` prefix for on-demand option help:
        ``?2`` shows the help text for option 2,
        ``?`` lists help for every option,
        regular numeric / id answers advance the wizard.
    """

    def __init__(self, *, stream_in=sys.stdin, stream_out=sys.stdout) -> None:
        self._in = stream_in
        self._out = stream_out

    def _print(self, msg: str) -> None:
        print(msg, file=self._out, flush=True)

    def _render_prompt(self, prompt: str, options: tuple[TreeOption, ...]) -> None:
        self._print("")
        self._print(prompt)
        any_help = any(opt.help for opt in options)
        for idx, opt in enumerate(options, 1):
            suffix = "  [?]" if opt.help else ""
            self._print(f"  [{idx}] {opt.label}{suffix}")
        if any_help:
            self._print("  (wpisz ?N żeby zobaczyć opis opcji / type ?N for help, ? for all)")

    def _show_help(self, target: str, options: tuple[TreeOption, ...]) -> None:
        if target == "":
            for idx, opt in enumerate(options, 1):
                self._print(f"  [{idx}] {opt.label}")
                self._print(f"      {opt.help or '(brak opisu / no description)'}")
            return
        if target.isdigit():
            idx = int(target)
            if 1 <= idx <= len(options):
                opt = options[idx - 1]
                self._print(f"  {opt.label}")
                self._print(f"  {opt.help or '(brak opisu / no description)'}")
                return
        matched = next((o for o in options if o.id == target), None)
        if matched is not None:
            self._print(f"  {matched.label}")
            self._print(f"  {matched.help or '(brak opisu / no description)'}")
            return
        self._print(f"  ! no option {target!r}")

    def ask_choice(self, prompt: str, options: tuple[TreeOption, ...]) -> TreeOption:
        if not options:
            raise RuntimeError("no options available for prompt: " + prompt)
        self._render_prompt(prompt, options)
        while True:
            raw = self._in.readline()
            if not raw:
                raise EOFError("wizard cancelled (EOF on stdin)")
            answer = raw.strip()
            if not answer:
                continue
            if answer.startswith("?"):
                self._show_help(answer[1:].strip(), options)
                continue
            if answer.isdigit():
                idx = int(answer)
                if 1 <= idx <= len(options):
                    return options[idx - 1]
            for opt in options:
                if opt.id == answer or opt.label.lower() == answer.lower():
                    return opt
            self._print(f"  ! unknown answer: {answer!r}, try a number 1..{len(options)}")

    def ask_yes_no(self, prompt: str, *, default: bool = True) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            self._print(f"{prompt} {suffix}")
            raw = self._in.readline()
            if not raw:
                raise EOFError("wizard cancelled (EOF on stdin)")
            answer = raw.strip().lower()
            if not answer:
                return default
            if answer in {"y", "yes", "t", "tak"}:
                return True
            if answer in {"n", "no", "nie"}:
                return False
            self._print("  ! answer with y/n")


class ScriptedPrompter(Prompter):
    """Test prompter: answers come from a queue of (node-question -> option-id) hints."""

    def __init__(self, answers: list[str], yes_no_answers: list[bool] | None = None) -> None:
        self._answers = list(answers)
        self._yes_no = list(yes_no_answers or [])

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

    def ask_yes_no(self, prompt: str, *, default: bool = True) -> bool:
        if not self._yes_no:
            return default
        return self._yes_no.pop(0)


def _available_install_managers() -> set[str]:
    return {
        manager
        for manager, binary in _MANAGER_BINARIES.items()
        if shutil.which(binary) is not None
    }


def _format_command(argv: tuple[str, ...]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


def _open_download_page(url: str, out) -> None:
    print(f"Open download page: {url}", file=out)
    for opener in (
        ("xdg-open", url),
        ("open", url),
    ):
        if shutil.which(opener[0]) is None:
            continue
        try:
            subprocess.Popen(opener, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Opened in browser via {opener[0]}", file=out)
            return
        except OSError:
            continue
    if os.name == "nt":
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("Opened in browser via cmd/start", file=out)
            return
        except OSError:
            pass


def _run_install_command(argv: tuple[str, ...], out) -> bool:
    effective = list(argv)
    if effective and effective[0] == "sudo" and shutil.which("sudo") is None:
        effective = effective[1:]
        print("note: sudo not found, running command without sudo", file=out)
    if not effective:
        return False
    print(f"Running installer command: {_format_command(tuple(effective))}", file=out)
    try:
        proc = subprocess.run(effective, check=False)
    except OSError as exc:
        print(f"installation command failed to start: {exc}", file=out)
        return False
    if proc.returncode != 0:
        print(f"installation command failed with exit code {proc.returncode}", file=out)
        return False
    print("installation command finished successfully", file=out)
    return True


def _build_install_method_options(
    spec: IDEInstallSpec,
    available_managers: set[str],
) -> tuple[tuple[TreeOption, ...], dict[str, tuple[str, ...]]]:
    options: list[TreeOption] = []
    commands: dict[str, tuple[str, ...]] = {}
    for manager in ("snap", "flatpak", "apt", "dnf", "pacman", "zypper"):
        if manager not in available_managers:
            continue
        command = spec.commands.get(manager)
        if not command:
            continue
        option_id = f"install_{manager}"
        options.append(
            TreeOption(
                id=option_id,
                label=f"Install via {manager}: {_format_command(command)}",
            )
        )
        commands[option_id] = command
    options.append(TreeOption(id="open_web", label=f"Open download page ({spec.homepage})"))
    options.append(TreeOption(id="cancel", label="Cancel installation"))
    return tuple(options), commands


def _offer_ide_install(prompter: Prompter, out) -> list[DetectedIDE]:
    print("No IDE detected. You can install one now.", file=out)
    ide_options = tuple(
        TreeOption(id=f"install_{ide_id}", label=f"Install {spec.label}")
        for ide_id in _IDE_INSTALL_ORDER
        if (spec := _IDE_INSTALL_CATALOG.get(ide_id)) is not None
    ) + (TreeOption(id="__none", label="Skip installation and continue"),)
    selected = prompter.ask_choice("Choose IDE installation target:", ide_options)
    if selected.id == "__none":
        return []

    ide_id = selected.id.removeprefix("install_")
    spec = _IDE_INSTALL_CATALOG.get(ide_id)
    if spec is None:
        return []

    methods, commands = _build_install_method_options(spec, _available_install_managers())
    method = prompter.ask_choice(f"Choose installation method for {spec.label}:", methods)
    if method.id == "cancel":
        return []
    if method.id == "open_web":
        _open_download_page(spec.homepage, out)
        return discover_installed_ides()

    command = commands.get(method.id)
    if command is None:
        return discover_installed_ides()
    if prompter.ask_yes_no("Run installation command now?", default=True):
        _run_install_command(command, out)
    else:
        print("You can run this command manually:", file=out)
        print(f"  {_format_command(command)}", file=out)

    return discover_installed_ides()


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


def _render_next_steps(steps: tuple[str, ...], ticket_id: str | None) -> list[str]:
    """Render the post-creation guidance lines with ``{{ticket_id}}`` substitution."""
    placeholder = ticket_id or "PLF-XXX"
    return [step.replace("{{ticket_id}}", placeholder) for step in steps]


def _emit_human(out, result: WizardResult, ticket_id: str | None) -> None:
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
        path = list(_resolve_quick_path(tree, quick_strategy))
        consumed, template = walk_path(tree, path)
        project = (project_override or Path.cwd()).resolve()
        ticket_id, body = _finalise_ticket(template, project, create=create)
        return WizardResult(
            chosen_ide=None,
            chosen_project=project,
            path=consumed,
            ticket_id=ticket_id,
            ticket_title=template.title,
            ticket_body=body,
            skipped_creation=not create,
            next_steps=tree.effective_next_steps(template.id),
            quick_mode=True,
        )

    ides = ide_override if ide_override is not None else discover_installed_ides()
    if not ides and ide_override is None:
        ides = _offer_ide_install(prompter, sys.stdout)
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
    ticket_id, body = _finalise_ticket(template, project, create=create)

    return WizardResult(
        chosen_ide=chosen_ide,
        chosen_project=project,
        path=path,
        ticket_id=ticket_id,
        ticket_title=template.title,
        ticket_body=body,
        skipped_creation=not create,
        next_steps=tree.effective_next_steps(template.id),
        quick_mode=False,
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
        default=None,
        metavar="PATH|URL",
        help=(
            "Custom strategies.json (local path or https:// URL; "
            "HTTPS requires --allow-remote)"
        ),
    )
    p.add_argument(
        "--template",
        default=None,
        metavar="NAME",
        help=(
            "Built-in strategy template (default, web-app, ml-research, "
            "cli-tool, library). Mutually exclusive with --strategies."
        ),
    )
    p.add_argument(
        "--list-templates",
        action="store_true",
        help="List built-in strategy templates and exit.",
    )
    p.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow fetching --strategies from HTTPS URLs (cached locally).",
    )
    p.add_argument(
        "--language",
        default=None,
        help=(
            "UI language (single 'pl' / 'en', or comma-separated 'pl,en' for "
            "bilingual labels). Defaults to strategies.json setting."
        ),
    )
    p.add_argument(
        "--bilingual",
        action="store_true",
        help="Shortcut for --language pl,en (side-by-side bilingual labels).",
    )
    p.add_argument(
        "--quick",
        action="store_true",
        help="Skip every prompt; follow strategies.json quick_default.path.",
    )
    p.add_argument(
        "--strategy",
        default=None,
        help=(
            "Dot-separated option-id path to follow in --quick mode "
            "(e.g. 'quality.cc_refactor'). Implies --quick."
        ),
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
    p.add_argument(
        "--gui",
        action="store_true",
        help="Open browser UI on http://127.0.0.1:<port>/wizard (requires koru[api]).",
    )
    p.add_argument(
        "--gui-port",
        type=int,
        default=0,
        metavar="PORT",
        help="Port for --gui (0 = pick a free port). Binds 127.0.0.1 only.",
    )
    p.add_argument(
        "--no-browser",
        action="store_true",
        help="With --gui, print URL but do not open a browser tab.",
    )
    return p


def wizard_main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.template and args.strategies:
        parser.error("--template and --strategies are mutually exclusive")

    if args.list_templates:
        print(format_templates_list())
        return 0

    if args.gui and (args.quick or args.strategy):
        parser.error("--gui cannot be combined with --quick or --strategy")

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

    language = args.language
    if args.bilingual and not language:
        language = "pl,en"
    elif args.bilingual and language and "," not in language:
        language = f"{language},pl,en" if language not in {"pl", "en"} else "pl,en"

    try:
        strategies_path = resolve_strategies_source(
            strategies=args.strategies,
            template=args.template,
            allow_remote=args.allow_remote,
        )
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
        print(f"koru wizard error: {exc}", file=sys.stderr)
        return 2

    if args.gui:
        from koru.wizard.gui import run_gui_server

        try:
            return run_gui_server(
                strategies_path=strategies_path,
                language=language,
                project_override=args.project,
                create=not args.no_create,
                port=args.gui_port,
                open_browser=not args.no_browser,
            )
        except RuntimeError as exc:
            print(f"koru wizard error: {exc}", file=sys.stderr)
            return 2

    quick = args.quick or bool(args.strategy)
    prompter = StdinPrompter()
    try:
        result = run_wizard(
            prompter=prompter,
            strategies_path=strategies_path,
            language=language,
            project_override=args.project,
            create=not args.no_create,
            use_llx=args.llx,
            quick=quick,
            quick_strategy=args.strategy,
        )
    except (EOFError, KeyboardInterrupt):
        print("\n(cancelled)", file=sys.stderr)
        return 130
    except (KeyError, ValueError) as exc:
        print(f"koru wizard error: {exc}", file=sys.stderr)
        return 2

    _emit_human(sys.stdout, result, result.ticket_id)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(wizard_main())
