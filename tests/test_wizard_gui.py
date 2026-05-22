"""Tests for koru wizard --gui (FastAPI app, no live network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from starlette.testclient import TestClient  # noqa: E402

from koru.wizard.gui.app import create_app
from koru.wizard.gui.session import SESSION_COOKIE, SessionStore
from koru.wizard.ide import DetectedIDE


def _tiny_tree_path(tmp_path: Path) -> Path:
    data = {
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
            "tpl_cqrs": {
                "title": "CQRS+ES",
                "body": "intro in {{project}}",
                "priority": "high",
            },
        },
    }
    path = tmp_path / "tree.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def gui_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "myproj").mkdir()
    (tmp_path / "myproj" / ".planfile").mkdir()

    monkeypatch.setattr(
        "koru.wizard.gui.app.discover_installed_ides",
        lambda: [
            DetectedIDE(
                id="vscode",
                label="VS Code",
                running=True,
                pid=99,
                path="/usr/bin/code",
            )
        ],
    )
    monkeypatch.setattr("koru.wizard.gui.app.propose_projects", lambda _ides: [])

    class _FakeTask:
        ticket_id = "PLF-GUI-001"

    monkeypatch.setattr(
        "koru.wizard.cli.create_nl_task",
        lambda *_a, **_k: _FakeTask(),
    )

    app = create_app(
        strategies_path=_tiny_tree_path(tmp_path),
        language="pl",
        project_override=None,
        create=True,
        store=SessionStore(),
    )
    return TestClient(app)


def _bootstrap(client: TestClient) -> str:
    r = client.get("/wizard/api/state")
    assert r.status_code == 200
    data = r.json()
    assert data["step"] == "ide"
    return data["csrf"]


def test_gui_app_serves_wizard_page(gui_client: TestClient) -> None:
    r = gui_client.get("/wizard")
    assert r.status_code == 200
    assert "koru wizard" in r.text
    assert SESSION_COOKIE in r.cookies


def test_gui_app_walks_tree_via_post(gui_client: TestClient) -> None:
    csrf = _bootstrap(gui_client)

    r = gui_client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "__none"})
    assert r.status_code == 200
    assert r.json()["step"] == "project"
    csrf = r.json()["csrf"]

    r = gui_client.post(
        "/wizard/api/project",
        json={"csrf": csrf, "project_path": "__cwd"},
    )
    assert r.status_code == 200
    assert r.json()["step"] == "strategy"
    csrf = r.json()["csrf"]

    r = gui_client.post(
        "/wizard/api/strategy",
        json={"csrf": csrf, "option_id": "a"},
    )
    assert r.status_code == 200
    assert r.json()["step"] == "strategy"
    csrf = r.json()["csrf"]

    r = gui_client.post(
        "/wizard/api/strategy",
        json={"csrf": csrf, "option_id": "cqrs"},
    )
    assert r.status_code == 200
    assert r.json()["step"] == "confirm"
    csrf = r.json()["csrf"]

    r = gui_client.post("/wizard/api/confirm", json={"csrf": csrf})
    assert r.status_code == 200
    body = r.json()
    assert body["step"] == "done"
    assert body["result"]["ticket_id"] == "PLF-GUI-001"
    assert body["result"]["ticket_title"] == "CQRS+ES"


def test_gui_app_creates_ticket_short_path(gui_client: TestClient) -> None:
    """Root option with direct ticket leaf (no intermediate node)."""
    csrf = _bootstrap(gui_client)
    gui_client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "__none"})
    csrf = gui_client.post(
        "/wizard/api/project",
        json={"csrf": csrf, "project_path": "__cwd"},
    ).json()["csrf"]
    r = gui_client.post(
        "/wizard/api/strategy",
        json={"csrf": csrf, "option_id": "q"},
    )
    assert r.json()["step"] == "confirm"
    csrf = r.json()["csrf"]
    r = gui_client.post("/wizard/api/confirm", json={"csrf": csrf})
    assert r.json()["result"]["ticket_title"] == "Quality"


def test_gui_csrf_rejected(gui_client: TestClient) -> None:
    _bootstrap(gui_client)
    r = gui_client.post("/wizard/api/ide", json={"csrf": "bad-token", "ide_id": "__none"})
    assert r.status_code == 403
