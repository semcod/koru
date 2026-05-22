"""Strategy decision-tree loader + walker for ``koru wizard``.

Decision trees are plain JSON (``strategies.json``) so users can fork them
without touching Python. The walker is pure (no IO beyond load) so tests can
drive arbitrary trees.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TreeOption:
    """Single answer option presented to the user."""

    id: str
    label: str
    next_node: str | None = None
    ticket: str | None = None
    help: str = ""


@dataclass(frozen=True)
class TreeNode:
    """Decision node: a prompt and a list of options."""

    id: str
    prompt: str
    options: tuple[TreeOption, ...]


@dataclass(frozen=True)
class TicketTemplate:
    """Leaf ticket template referenced by an option."""

    id: str
    title: str
    body: str
    labels: tuple[str, ...] = field(default_factory=tuple)
    priority: str = "normal"
    next_steps: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StrategyTree:
    """In-memory representation of ``strategies.json``."""

    version: int
    root_id: str
    nodes: dict[str, TreeNode]
    tickets: dict[str, TicketTemplate]
    language: str = "pl"
    quick_default_path: tuple[str, ...] = field(default_factory=tuple)
    default_next_steps: tuple[str, ...] = field(default_factory=tuple)

    def root(self) -> TreeNode:
        return self.nodes[self.root_id]

    def node(self, node_id: str) -> TreeNode:
        if node_id not in self.nodes:
            raise KeyError(f"unknown wizard node: {node_id!r}")
        return self.nodes[node_id]

    def ticket(self, ticket_id: str) -> TicketTemplate:
        if ticket_id not in self.tickets:
            raise KeyError(f"unknown wizard ticket: {ticket_id!r}")
        return self.tickets[ticket_id]

    def effective_next_steps(self, ticket_id: str) -> tuple[str, ...]:
        """Per-ticket steps when defined, otherwise the tree-wide default."""
        steps = self.ticket(ticket_id).next_steps
        return steps if steps else self.default_next_steps


def _pick_localized(value: Any, language: str) -> str:
    """Return ``value[language]`` when it's a localisation dict, else stringify."""
    if isinstance(value, dict):
        return str(
            value.get(language)
            or value.get("pl")
            or value.get("en")
            or next(iter(value.values()), "")
        )
    return str(value)


def _pick_localized_multi(value: Any, languages: tuple[str, ...], separator: str) -> str:
    """Return localised strings for *all* requested languages joined by ``separator``.

    Used to render side-by-side bilingual labels like ``"Architektura · Architecture"``.
    Falls back to single-language render when ``value`` is not a dict.
    """
    if not isinstance(value, dict):
        return str(value)
    if len(languages) <= 1:
        return _pick_localized(value, languages[0] if languages else "pl")
    rendered: list[str] = []
    seen: set[str] = set()
    for lang in languages:
        text = _pick_localized(value, lang)
        if text and text not in seen:
            rendered.append(text)
            seen.add(text)
    return separator.join(rendered)


def _coerce_languages(
    language: str | list[str] | tuple[str, ...] | None,
    fallback: str,
) -> tuple[str, ...]:
    """Normalise a language spec into a non-empty tuple."""
    if language is None:
        return (fallback,)
    if isinstance(language, str):
        parts = [p.strip() for p in language.split(",") if p.strip()]
        return tuple(parts) or (fallback,)
    parts = [str(p).strip() for p in language if str(p).strip()]
    return tuple(parts) or (fallback,)


def _coerce_options(
    raw_options: list[dict[str, Any]],
    languages: tuple[str, ...],
    separator: str,
) -> tuple[TreeOption, ...]:
    options: list[TreeOption] = []
    primary_lang = languages[0]
    for raw in raw_options:
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        label = _pick_localized_multi(raw.get("label"), languages, separator) or str(raw["id"])
        raw_help = raw.get("help")
        help_text = _pick_localized(raw_help, primary_lang) if raw_help is not None else ""
        options.append(
            TreeOption(
                id=str(raw["id"]),
                label=label,
                next_node=str(raw["next"]) if raw.get("next") else None,
                ticket=str(raw["ticket"]) if raw.get("ticket") else None,
                help=help_text,
            )
        )
    return tuple(options)


def _coerce_node(
    node_id: str,
    raw: dict[str, Any],
    languages: tuple[str, ...],
    separator: str,
) -> TreeNode:
    prompt = _pick_localized_multi(raw.get("prompt"), languages, separator) or node_id
    options = _coerce_options(list(raw.get("options") or []), languages, separator)
    return TreeNode(id=node_id, prompt=prompt, options=options)


def _coerce_ticket(ticket_id: str, raw: dict[str, Any], primary_lang: str) -> TicketTemplate:
    labels_raw = raw.get("labels") or []
    next_steps_raw = raw.get("next_steps") or []
    next_steps: list[str] = []
    for item in next_steps_raw:
        rendered = _pick_localized(item, primary_lang)
        if rendered:
            next_steps.append(rendered)
    return TicketTemplate(
        id=ticket_id,
        title=str(raw.get("title") or ticket_id),
        body=str(raw.get("body") or ""),
        labels=tuple(str(x) for x in labels_raw if str(x).strip()),
        priority=str(raw.get("priority") or "normal"),
        next_steps=tuple(next_steps),
    )


def _load_tree_data(source: Path | str | dict[str, Any] | None) -> dict[str, Any]:
    """Load tree data from various sources."""
    if isinstance(source, dict):
        return source
    if isinstance(source, (str, Path)):
        path = Path(source)
        return json.loads(path.read_text(encoding="utf-8"))
    with resources.files("koru.wizard").joinpath("strategies.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def _validate_tree_references(
    nodes: dict[str, TreeNode], tickets: dict[str, TicketTemplate]
) -> None:
    """Validate that all node/ticket references in options exist."""
    for nid, node in nodes.items():
        for opt in node.options:
            if opt.next_node is not None and opt.next_node not in nodes:
                raise ValueError(
                    f"node {nid!r} option {opt.id!r}: next={opt.next_node!r} not in 'nodes'"
                )
            if opt.ticket is not None and opt.ticket not in tickets:
                raise ValueError(
                    f"node {nid!r} option {opt.id!r}: ticket={opt.ticket!r} not in 'tickets'"
                )


def _load_quick_defaults(
    data: dict[str, Any], primary_lang: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Load quick_default path and default next_steps from data."""
    quick = data.get("quick_default") or {}
    quick_path = tuple(str(x) for x in (quick.get("path") or []))
    default_steps_raw = (data.get("defaults") or {}).get("next_steps") or []
    default_steps = tuple(
        rendered for rendered in (
            _pick_localized(item, primary_lang) for item in default_steps_raw
        ) if rendered
    )
    return quick_path, default_steps


def load_tree(
    source: Path | str | dict[str, Any] | None = None,
    *,
    language: str | list[str] | tuple[str, ...] | None = None,
    bilingual_separator: str = " · ",
) -> StrategyTree:
    """Load the decision tree from a path, dict, or the packaged default."""
    data = _load_tree_data(source)

    default_lang = str(data.get("language_default") or "pl")
    languages = _coerce_languages(language, default_lang)
    primary_lang = languages[0]
    raw_nodes = dict(data.get("nodes") or {})
    raw_tickets = dict(data.get("tickets") or {})
    root_id = str(data.get("root") or "root")
    if root_id not in raw_nodes:
        raise ValueError(f"strategies.json: root node {root_id!r} is missing from 'nodes'")

    nodes = {
        nid: _coerce_node(nid, raw, languages, bilingual_separator)
        for nid, raw in raw_nodes.items()
    }
    tickets = {
        tid: _coerce_ticket(tid, raw, primary_lang) for tid, raw in raw_tickets.items()
    }

    _validate_tree_references(nodes, tickets)

    quick_path, default_steps = _load_quick_defaults(data, primary_lang)

    return StrategyTree(
        version=int(data.get("version") or 1),
        root_id=root_id,
        nodes=nodes,
        tickets=tickets,
        language=primary_lang,
        quick_default_path=quick_path,
        default_next_steps=default_steps,
    )


def render_ticket_body(template: TicketTemplate, variables: dict[str, str]) -> str:
    """Substitute ``{{var}}`` placeholders in the template body."""
    rendered = template.body
    for key, value in variables.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def walk(
    tree: StrategyTree,
    *,
    prompter: Prompter,
) -> tuple[list[str], TicketTemplate]:
    """Walk ``tree`` interactively, returning the path of option ids and the leaf ticket."""
    path: list[str] = []
    current = tree.root()
    while True:
        choice = prompter.ask_choice(current.prompt, current.options)
        path.append(choice.id)
        if choice.ticket:
            return path, tree.ticket(choice.ticket)
        if choice.next_node:
            current = tree.node(choice.next_node)
            continue
        raise RuntimeError(f"option {choice.id!r} on node {current.id!r} has no next/ticket")


def walk_path(
    tree: StrategyTree, path: tuple[str, ...] | list[str]
) -> tuple[list[str], TicketTemplate]:
    """Follow a pre-resolved sequence of option ids through the tree.

    Used by ``--quick`` and ``--strategy`` to skip interactive prompts.
    Raises ``KeyError`` when an option id is missing from the current node,
    ``RuntimeError`` when the path doesn't end at a ticket leaf.
    """
    if not path:
        raise ValueError("walk_path requires at least one option id")
    current = tree.root()
    consumed: list[str] = []
    for option_id in path:
        matched = next((opt for opt in current.options if opt.id == option_id), None)
        if matched is None:
            raise KeyError(
                f"node {current.id!r}: no option {option_id!r} "
                f"(have: {[o.id for o in current.options]})"
            )
        consumed.append(option_id)
        if matched.ticket:
            return consumed, tree.ticket(matched.ticket)
        if matched.next_node:
            current = tree.node(matched.next_node)
            continue
        raise RuntimeError(
            f"option {option_id!r} on node {current.id!r} has no next/ticket"
        )
    raise RuntimeError(
        f"path {list(path)} ended at node {current.id!r} without reaching a ticket"
    )


class Prompter:
    """Minimal interface used by :func:`walk`; subclass for non-stdin UIs."""

    def ask_choice(  # pragma: no cover - interface
        self,
        prompt: str,
        options: tuple[TreeOption, ...],
    ) -> TreeOption:
        raise NotImplementedError

    def ask_yes_no(  # pragma: no cover - interface
        self,
        prompt: str,
        *,
        default: bool = True,
    ) -> bool:
        raise NotImplementedError
