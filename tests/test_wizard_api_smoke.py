"""Smoke tests for koru wizard HTTP and API endpoints.

Covers endpoints identified as missing smoke coverage:
- GET  /wizard
- GET  /wizard/api/state
- POST /wizard/api/ide
- POST /wizard/api/project
- POST /wizard/api/strategy
- POST /wizard/api/confirm
- POST /wizard/done
- Static assets and CSRF security boundary.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from starlette.testclient import TestClient  # noqa: E402

from koru.wizard.gui.app import create_app  # noqa: E402
from koru.wizard.gui.session import SESSION_COOKIE, SessionStore  # noqa: E402
from koru.wizard.ide import DetectedIDE  # noqa: E402


def _tiny_tree_path(tmp_path: Path) -> Path:
    data = {
        "version": 1,
        "language_default": "pl",
        "root": "root",
        "nodes": {
            "root": {
                "prompt": {"pl": "Co robimy?", "en": "What next?"},
                "options": [
                    {"id": "opt_arch", "label": {"pl": "Architektura"}, "next": "arch_node"},
                    {"id": "opt_quick", "label": {"pl": "Szybki start"}, "ticket": "tpl_quick"},
                ],
            },
            "arch_node": {
                "prompt": {"pl": "Wybierz wzorzec"},
                "options": [
                    {"id": "opt_cqrs", "label": {"pl": "CQRS+ES"}, "ticket": "tpl_cqrs"},
                ],
            },
        },
        "tickets": {
            "tpl_quick": {"title": "Quick Start", "body": "Setup {{project}}", "labels": ["setup"]},
            "tpl_cqrs": {"title": "Implement CQRS", "body": "Add CQRS in {{project}}", "priority": "high"},
        },
    }
    path = tmp_path / "strategies_tree.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def smoke_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test_project").mkdir()
    (tmp_path / "test_project" / ".planfile").mkdir()

    monkeypatch.setattr(
        "koru.wizard.gui.app.discover_installed_ides",
        lambda: [
            DetectedIDE(
                id="vscode",
                label="VS Code",
                running=True,
                pid=1234,
                path="/usr/bin/code",
            )
        ],
    )
    monkeypatch.setattr("koru.wizard.gui.app.propose_projects", lambda _ides: [])

    class _MockTask:
        ticket_id = "PLF-SMOKE-001"

    monkeypatch.setattr(
        "koru.wizard.cli.create_nl_task",
        lambda *_a, **_k: _MockTask(),
    )

    app = create_app(
        strategies_path=_tiny_tree_path(tmp_path),
        language="pl",
        project_override=None,
        create=True,
        store=SessionStore(),
    )
    return TestClient(app)


def test_smoke_wizard_get(smoke_client: TestClient) -> None:
    """GET /wizard: serves the wizard frontend HTML with session cookie."""
    resp = smoke_client.get("/wizard")
    assert resp.status_code == 200
    assert "koru wizard" in resp.text
    assert SESSION_COOKIE in resp.cookies


def test_smoke_wizard_api_state(smoke_client: TestClient) -> None:
    """GET /wizard/api/state: bootstraps session and returns initial state JSON."""
    resp = smoke_client.get("/wizard/api/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["step"] == "ide"
    assert "csrf" in data and len(data["csrf"]) > 8
    assert "ides" in data
    assert any(ide["id"] == "vscode" for ide in data["ides"])


def test_smoke_wizard_api_ide(smoke_client: TestClient) -> None:
    """POST /wizard/api/ide: selects an IDE and advances state to 'project'."""
    state = smoke_client.get("/wizard/api/state").json()
    csrf = state["csrf"]

    resp = smoke_client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "vscode"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["step"] == "project"
    assert data.get("chosen_ide_id") == "vscode"


def test_smoke_wizard_api_project(smoke_client: TestClient) -> None:
    """POST /wizard/api/project: selects project path and advances state to 'strategy'."""
    csrf = smoke_client.get("/wizard/api/state").json()["csrf"]
    csrf = smoke_client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "vscode"}).json()["csrf"]

    resp = smoke_client.post("/wizard/api/project", json={"csrf": csrf, "project_path": "__cwd"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["step"] == "strategy"
    assert "strategy" in data and "prompt" in data["strategy"]


def test_smoke_wizard_api_strategy(smoke_client: TestClient) -> None:
    """POST /wizard/api/strategy: chooses question options and walks tree."""
    csrf = smoke_client.get("/wizard/api/state").json()["csrf"]
    csrf = smoke_client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "vscode"}).json()["csrf"]
    csrf = smoke_client.post("/wizard/api/project", json={"csrf": csrf, "project_path": "__cwd"}).json()["csrf"]

    # Choose option that leads to a leaf ticket
    resp = smoke_client.post("/wizard/api/strategy", json={"csrf": csrf, "option_id": "opt_quick"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["step"] == "confirm"
    assert "pending" in data
    assert data["pending"]["title"] == "Quick Start"


def test_smoke_wizard_api_confirm(smoke_client: TestClient) -> None:
    """POST /wizard/api/confirm: confirms ticket creation and marks state 'done'."""
    csrf = smoke_client.get("/wizard/api/state").json()["csrf"]
    csrf = smoke_client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "vscode"}).json()["csrf"]
    csrf = smoke_client.post("/wizard/api/project", json={"csrf": csrf, "project_path": "__cwd"}).json()["csrf"]
    csrf = smoke_client.post("/wizard/api/strategy", json={"csrf": csrf, "option_id": "opt_quick"}).json()["csrf"]

    resp = smoke_client.post("/wizard/api/confirm", json={"csrf": csrf})
    assert resp.status_code == 200
    data = resp.json()
    assert data["step"] == "done"
    assert "result" in data
    assert data["result"]["ticket_id"] == "PLF-SMOKE-001"


def test_smoke_wizard_done(smoke_client: TestClient) -> None:
    """POST /wizard/done: closes session after confirmation."""
    csrf = smoke_client.get("/wizard/api/state").json()["csrf"]
    csrf = smoke_client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "vscode"}).json()["csrf"]
    csrf = smoke_client.post("/wizard/api/project", json={"csrf": csrf, "project_path": "__cwd"}).json()["csrf"]
    csrf = smoke_client.post("/wizard/api/strategy", json={"csrf": csrf, "option_id": "opt_quick"}).json()["csrf"]
    csrf = smoke_client.post("/wizard/api/confirm", json={"csrf": csrf}).json()["csrf"]

    resp = smoke_client.post("/wizard/done", json={"csrf": csrf})
    assert resp.status_code == 200
    assert resp.json().get("ok") is True


def test_smoke_wizard_csrf_protection(smoke_client: TestClient) -> None:
    """All POST endpoints reject requests missing valid CSRF tokens."""
    endpoints = [
        "/wizard/api/ide",
        "/wizard/api/project",
        "/wizard/api/strategy",
        "/wizard/api/confirm",
        "/wizard/done",
    ]
    for endpoint in endpoints:
        # Without any CSRF
        resp = smoke_client.post(endpoint, json={})
        assert resp.status_code in (401, 403), f"{endpoint} allowed request without CSRF"

        # With invalid CSRF
        resp = smoke_client.post(endpoint, json={"csrf": "invalid-token-12345"})
        assert resp.status_code in (401, 403), f"{endpoint} allowed request with bad CSRF"


def test_smoke_wizard_static_assets(smoke_client: TestClient) -> None:
    """GET /wizard/static/*: verifies static UI assets are served properly."""
    css = smoke_client.get("/wizard/static/wizard.css")
    assert css.status_code == 200
    assert len(css.content) > 0

    js = smoke_client.get("/wizard/static/wizard.js")
    assert js.status_code == 200
    assert len(js.content) > 0
