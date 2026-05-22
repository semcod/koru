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
                    {
                        "id": "a",
                        "label": {"pl": "Architektura", "en": "Architecture"},
                        "next": "arch",
                    },
                    {
                        "id": "q",
                        "label": {"pl": "Jakość", "en": "Quality"},
                        "ticket": "tpl_q",
                    },
                ],
            },
            "arch": {
                "prompt": {"pl": "Aspekt?", "en": "Aspect?"},
                "options": [
                    {
                        "id": "cqrs",
                        "label": {"pl": "CQRS+ES", "en": "CQRS+ES"},
                        "ticket": "tpl_cqrs",
                    },
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


def test_load_tree_supports_bilingual_language_list() -> None:
    """Passing ``['pl', 'en']`` joins labels with the default separator."""
    tree = load_tree(_tiny_tree(), language=["pl", "en"])
    labels = [opt.label for opt in tree.root().options]
    assert "Architektura · Architecture" in labels or "Architektura" in labels[0]
    assert " · " in labels[0]


def test_load_tree_supports_comma_separated_language() -> None:
    tree = load_tree(_tiny_tree(), language="pl,en")
    labels = [opt.label for opt in tree.root().options]
    assert any("·" in lbl for lbl in labels)


def test_load_tree_bilingual_custom_separator() -> None:
    tree = load_tree(_tiny_tree(), language=["pl", "en"], bilingual_separator=" / ")
    assert " / " in tree.root().options[0].label


def test_load_tree_dedupes_identical_translations() -> None:
    """When pl and en strings are identical, render only once."""
    data = {
        "version": 1,
        "language_default": "pl",
        "root": "root",
        "nodes": {
            "root": {
                "prompt": {"pl": "Same", "en": "Same"},
                "options": [
                    {"id": "x", "label": {"pl": "Identical", "en": "Identical"}, "ticket": "tpl_x"},
                ],
            }
        },
        "tickets": {"tpl_x": {"title": "x", "body": "y"}},
    }
    tree = load_tree(data, language=["pl", "en"])
    assert tree.root().options[0].label == "Identical"


def test_tree_option_loads_help_text() -> None:
    data = _tiny_tree()
    data["nodes"]["root"]["options"][0]["help"] = {"pl": "Pomoc PL", "en": "Help EN"}
    tree = load_tree(data, language="pl")
    assert tree.root().options[0].help == "Pomoc PL"


def test_tree_quick_default_path_parsed() -> None:
    """Packaged strategies.json declares a quick default path."""
    tree = load_tree()
    assert tree.quick_default_path == ("quality", "cc_refactor")


def test_ticket_template_loads_next_steps() -> None:
    tree = load_tree()
    cc = tree.ticket("tpl_cc_refactor")
    assert cc.next_steps, "tpl_cc_refactor declares its own next_steps"
    assert any("koru scan" in step or "code2llm" in step for step in cc.next_steps)


def test_effective_next_steps_falls_back_to_defaults() -> None:
    """A ticket without explicit next_steps must use defaults.next_steps."""
    tree = load_tree()
    steps = tree.effective_next_steps("tpl_ddd")
    assert steps, "default next_steps must exist"
    assert any("koru" in s.lower() for s in steps)


def test_walk_path_follows_pre_resolved_ids() -> None:
    from koru.wizard.tree import walk_path

    tree = load_tree(_tiny_tree())
    consumed, ticket = walk_path(tree, ["a", "cqrs"])
    assert consumed == ["a", "cqrs"]
    assert ticket.id == "tpl_cqrs"


def test_walk_path_rejects_unknown_option() -> None:
    from koru.wizard.tree import walk_path

    tree = load_tree(_tiny_tree())
    with pytest.raises(KeyError, match="no option 'missing'"):
        walk_path(tree, ["a", "missing"])
