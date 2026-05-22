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


@dataclass(frozen=True)
class StrategyTree:
    """In-memory representation of ``strategies.json``."""

    version: int
    root_id: str
    nodes: dict[str, TreeNode]
    tickets: dict[str, TicketTemplate]
    language: str = "pl"

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


def _coerce_options(raw_options: list[dict[str, Any]], language: str) -> tuple[TreeOption, ...]:
    options: list[TreeOption] = []
    for raw in raw_options:
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        options.append(
            TreeOption(
                id=str(raw["id"]),
                label=_pick_localized(raw.get("label"), language) or str(raw["id"]),
                next_node=str(raw["next"]) if raw.get("next") else None,
                ticket=str(raw["ticket"]) if raw.get("ticket") else None,
            )
        )
    return tuple(options)


def _coerce_node(node_id: str, raw: dict[str, Any], language: str) -> TreeNode:
    prompt = _pick_localized(raw.get("prompt"), language) or node_id
    options = _coerce_options(list(raw.get("options") or []), language)
    return TreeNode(id=node_id, prompt=prompt, options=options)


def _coerce_ticket(ticket_id: str, raw: dict[str, Any]) -> TicketTemplate:
    labels_raw = raw.get("labels") or []
    return TicketTemplate(
        id=ticket_id,
        title=str(raw.get("title") or ticket_id),
        body=str(raw.get("body") or ""),
        labels=tuple(str(x) for x in labels_raw if str(x).strip()),
        priority=str(raw.get("priority") or "normal"),
    )


def load_tree(
    source: Path | str | dict[str, Any] | None = None,
    *,
    language: str | None = None,
) -> StrategyTree:
    """Load the decision tree from a path, dict, or the packaged default."""
    if isinstance(source, dict):
        data = source
    elif isinstance(source, (str, Path)):
        path = Path(source)
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        with resources.files("koru.wizard").joinpath("strategies.json").open(
            "r", encoding="utf-8"
        ) as fh:
            data = json.load(fh)

    lang = language or str(data.get("language_default") or "pl")
    raw_nodes = dict(data.get("nodes") or {})
    raw_tickets = dict(data.get("tickets") or {})
    root_id = str(data.get("root") or "root")
    if root_id not in raw_nodes:
        raise ValueError(f"strategies.json: root node {root_id!r} is missing from 'nodes'")

    nodes = {nid: _coerce_node(nid, raw, lang) for nid, raw in raw_nodes.items()}
    tickets = {tid: _coerce_ticket(tid, raw) for tid, raw in raw_tickets.items()}

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

    return StrategyTree(
        version=int(data.get("version") or 1),
        root_id=root_id,
        nodes=nodes,
        tickets=tickets,
        language=lang,
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
