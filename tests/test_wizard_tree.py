"""Unit tests for the wizard decision tree loader/walker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from koru.wizard.tree import (
    Prompter,
    load_tree,
    render_ticket_body,
    walk,
)


class _Scripted(Prompter):
    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.seen_prompts: list[str] = []

    def ask_choice(self, prompt: str, options):
        self.seen_prompts.append(prompt)
        token = self.answers.pop(0)
        if token.isdigit():
            return options[int(token) - 1]
        for opt in options:
            if opt.id == token:
                return opt
        raise KeyError(token)


def _tiny_tree() -> dict:
    return {
        "version": 1,
        "language_default": "pl",
        "root": "root",
        "nodes": {
            "root": {
                "prompt": {"pl": "Co?", "en": "What?"},
                "options": [
                    {"id": "a", "label": {"pl": "Architektura"}, "next": "arch"},
                    {"id": "q", "label": {"pl": "Jakość"}, "ticket": "tpl_q"},
                ],
            },
            "arch": {
                "prompt": {"pl": "Aspekt?"},
                "options": [
                    {"id": "cqrs", "label": {"pl": "CQRS+ES"}, "ticket": "tpl_cqrs"},
                ],
            },
        },
        "tickets": {
            "tpl_q": {"title": "Quality", "body": "fix {{project}}", "labels": ["quality"]},
            "tpl_cqrs": {"title": "CQRS+ES", "body": "intro in {{project}}", "priority": "high"},
        },
    }


def test_load_tree_resolves_localised_labels() -> None:
    tree = load_tree(_tiny_tree(), language="pl")
    root = tree.root()
    assert root.prompt == "Co?"
    labels = [opt.label for opt in root.options]
    assert "Architektura" in labels and "Jakość" in labels


def test_load_tree_falls_back_to_english_when_language_missing() -> None:
    tree = load_tree(_tiny_tree(), language="de")
    assert tree.root().options[0].label == "Architektura"


def test_load_tree_validates_dangling_next_reference() -> None:
    bad = _tiny_tree()
    bad["nodes"]["root"]["options"][0]["next"] = "missing"
    with pytest.raises(ValueError, match="next='missing'"):
        load_tree(bad)


def test_load_tree_validates_dangling_ticket_reference() -> None:
    bad = _tiny_tree()
    bad["nodes"]["root"]["options"][1]["ticket"] = "missing"
    with pytest.raises(ValueError, match="ticket='missing'"):
        load_tree(bad)


def test_walk_returns_path_and_ticket() -> None:
    tree = load_tree(_tiny_tree())
    prompter = _Scripted(["a", "cqrs"])
    path, ticket = walk(tree, prompter=prompter)
    assert path == ["a", "cqrs"]
    assert ticket.title == "CQRS+ES"
    assert ticket.priority == "high"


def test_render_ticket_body_substitutes_variables() -> None:
    tree = load_tree(_tiny_tree())
    body = render_ticket_body(tree.ticket("tpl_q"), {"project": "demo-svc"})
    assert body == "fix demo-svc"


def test_load_tree_from_path(tmp_path: Path) -> None:
    p = tmp_path / "s.json"
    p.write_text(json.dumps(_tiny_tree()), encoding="utf-8")
    tree = load_tree(p)
    assert tree.version == 1
    assert "tpl_cqrs" in tree.tickets


def test_packaged_strategies_loads_and_has_root() -> None:
    """Default strategies.json must load cleanly and expose the root node."""
    tree = load_tree()
    assert tree.root_id == "root"
    assert tree.root().options, "root must have options"
    for ticket_id in tree.tickets:
        assert tree.tickets[ticket_id].title
