"""Tests for ticket hygiene (auto-archive junk)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from koru.autonomy import ticket_hygiene as th


def _write_sprint(project: Path, tickets: dict) -> None:
    sprint = project / ".planfile" / "sprints"
    sprint.mkdir(parents=True)
    (sprint / "current.yaml").write_text(
        yaml.safe_dump({"sprint": {"tickets": tickets}}),
        encoding="utf-8",
    )


def test_ticket_is_junk_for_venv_paths() -> None:
    assert th.ticket_is_junk(
        {"files": [".testvenv/lib/python3.13/site-packages/x.py"], "name": "x"}
    )
    assert not th.ticket_is_junk({"files": ["src/core.py"], "name": "x"})


def test_hygiene_archives_junk(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    _write_sprint(
        tmp_path,
        {
            "PLF-JUNK": {
                "name": "[todo2code] venv",
                "status": "open",
                "files": [".testvenv/lib/site-packages/a.py"],
                "source": {"tool": "koru-todo2code-discovery"},
            },
            "PLF-OK": {
                "name": "[todo2code] real",
                "status": "open",
                "files": ["src/a.py"],
                "source": {"tool": "koru-todo2code-discovery"},
            },
        },
    )
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        from types import SimpleNamespace

        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch("koru.autonomy.ticket_hygiene.subprocess.run", side_effect=fake_run):
        outcome = th.run_ticket_hygiene(tmp_path)
    assert "PLF-JUNK" in outcome.archived
    assert "PLF-OK" in outcome.kept
    assert any("done" in c and "PLF-JUNK" in c for c in calls)


def test_hygiene_dry_run(tmp_path: Path) -> None:
    _write_sprint(
        tmp_path,
        {
            "PLF-JUNK": {
                "name": "[todo2code] venv",
                "status": "open",
                "files": ["node_modules/x/index.js"],
            }
        },
    )
    outcome = th.run_ticket_hygiene(tmp_path, dry_run=True)
    assert outcome.archived == ["PLF-JUNK (dry-run)"]


def test_ticket_has_stale_paths(tmp_path: Path) -> None:
    stale = tmp_path / "src" / "env2llm" / "doql" / "parse.py"
    assert th.ticket_has_stale_paths(
        {"files": ["src/env2llm/doql/parse.py"]},
        project=tmp_path,
    ) is True
    stale.parent.mkdir(parents=True)
    stale.write_text("# moved\n", encoding="utf-8")
    assert th.ticket_has_stale_paths(
        {"files": ["src/env2llm/doql/parse.py"]},
        project=tmp_path,
    ) is False
