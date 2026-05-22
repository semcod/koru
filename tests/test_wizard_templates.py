"""Tests for koru.wizard.templates — packaged templates and remote fetch."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from koru.wizard import templates as wiz_templates
from koru.wizard.cli import wizard_main
from koru.wizard.tree import load_tree


def test_list_templates_returns_packaged_set() -> None:
    names = {t.name for t in wiz_templates.list_templates()}
    assert names == {"cli-tool", "default", "library", "ml-research", "web-app"}


def test_resolve_template_by_name() -> None:
    path = wiz_templates.resolve_template_name("web-app")
    assert path.name == "web-app.json"
    tree = load_tree(path)
    assert tree.root_id == "root"
    assert any(opt.id == "frontend" for opt in tree.root().options)


def test_resolve_template_unknown_raises() -> None:
    with pytest.raises(KeyError, match="unknown template"):
        wiz_templates.resolve_template_name("not-a-template")


def test_resolve_strategies_https_requires_allow_remote() -> None:
    url = "https://example.com/strategies.json"
    with pytest.raises(ValueError, match="--allow-remote"):
        wiz_templates.resolve_strategies_source(
            strategies=url,
            template=None,
            allow_remote=False,
        )


def test_resolve_strategies_rejects_non_https() -> None:
    with pytest.raises(ValueError, match="only https://"):
        wiz_templates.resolve_strategies_source(
            strategies="http://example.com/x.json",
            template=None,
            allow_remote=True,
        )


def test_fetch_remote_strategies_caches(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(wiz_templates, "_CACHE_DIR", tmp_path)
    payload = {
        "version": 1,
        "root": "root",
        "nodes": {
            "root": {
                "prompt": "Pick",
                "options": [{"id": "x", "ticket": "tpl_x"}],
            }
        },
        "tickets": {"tpl_x": {"title": "T", "body": "B"}},
    }
    body = json.dumps(payload).encode("utf-8")

    response = MagicMock()
    response.read = MagicMock(return_value=body)
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr(
        wiz_templates.urllib.request,
        "urlopen",
        MagicMock(return_value=response),
    )

    url = "https://example.com/custom-tree.json"
    path1 = wiz_templates.fetch_remote_strategies(url, allow_remote=True)
    assert path1.is_file()
    assert json.loads(path1.read_text(encoding="utf-8"))["root"] == "root"

    path2 = wiz_templates.fetch_remote_strategies(url, allow_remote=True)
    assert path1 == path2
    wiz_templates.urllib.request.urlopen.assert_called_once()


def test_resolve_strategies_template_and_path_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        wiz_templates.resolve_strategies_source(
            strategies="/tmp/x.json",
            template="web-app",
            allow_remote=False,
        )


def test_load_tree_web_app_template_quick_default() -> None:
    path = wiz_templates.resolve_template_name("web-app")
    tree = load_tree(path)
    assert tree.quick_default_path == ("frontend", "ux_perf")


def test_wizard_main_list_templates(capsys) -> None:
    rc = wizard_main(["--list-templates"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "web-app" in out
    assert "ml-research" in out


def test_wizard_main_template_and_strategies_error() -> None:
    with pytest.raises(SystemExit) as exc:
        wizard_main(["--template", "web-app", "--strategies", "/tmp/x.json"])
    assert exc.value.code != 0


def test_wizard_quick_with_template(tmp_path: Path) -> None:
    from koru.wizard.cli import ScriptedPrompter, run_wizard

    project = tmp_path / "mlproj"
    project.mkdir()
    (project / ".planfile").mkdir()

    result = run_wizard(
        prompter=ScriptedPrompter([]),
        strategies_path=wiz_templates.resolve_template_name("ml-research"),
        project_override=project,
        ide_override=[],
        project_candidates_override=[],
        create=False,
        quick=True,
    )
    assert result.path == ["reproducibility"]
    assert "ML: reprodukowalność" in result.ticket_title
