"""Unit tests for the optional llx bridge."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from koru.wizard.llx import _parse_llx_response, expand_node
from koru.wizard.tree import TreeNode, TreeOption


def _node() -> TreeNode:
    return TreeNode(
        id="quality",
        prompt="Which quality dimension?",
        options=(TreeOption(id="tests", label="Tests"),),
    )


def test_parse_llx_response_accepts_valid_options() -> None:
    raw = '{"options": [{"id": "mut", "label": "Mutation tests", "ticket": "tpl_tests"}]}'
    extras = _parse_llx_response(raw, {"tpl_tests"})
    assert len(extras) == 1
    assert extras[0].id == "llx_mut"
    assert extras[0].label.startswith("[LLX]")
    assert extras[0].ticket == "tpl_tests"


def test_parse_llx_response_strips_unknown_ticket() -> None:
    raw = '{"options": [{"id": "x", "label": "Y", "ticket": "tpl_unknown"}]}'
    extras = _parse_llx_response(raw, {"tpl_tests"})
    assert extras[0].ticket is None


def test_parse_llx_response_ignores_garbage() -> None:
    assert _parse_llx_response("not json", set()) == ()
    assert _parse_llx_response('{"options": "wat"}', set()) == ()


def test_expand_node_returns_none_when_runner_fails(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("koru.wizard.llx.llx_available", lambda: True)

    def boom(_argv, _t):
        raise subprocess.TimeoutExpired(cmd="llx", timeout=1)

    result = expand_node(tmp_path, _node(), ticket_ids=["tpl_tests"], runner=boom)
    assert result is None


def test_expand_node_parses_runner_output(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("koru.wizard.llx.llx_available", lambda: True)

    def fake_runner(_argv, _t):
        return SimpleNamespace(
            returncode=0,
            stdout='{"options": [{"id": "fuzz", "label": "Fuzz tests", "ticket": "tpl_tests"}]}',
            stderr="",
        )

    expansion = expand_node(tmp_path, _node(), ticket_ids=["tpl_tests"], runner=fake_runner)
    assert expansion is not None
    assert expansion.extra_options[0].id == "llx_fuzz"


def test_expand_node_returns_none_when_llx_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("koru.wizard.llx.llx_available", lambda: False)
    assert expand_node(tmp_path, _node(), ticket_ids=["tpl_tests"]) is None
