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


def test_gui_unknown_ide_id_returns_400(gui_client: TestClient) -> None:
    csrf = _bootstrap(gui_client)
    r = gui_client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "does-not-exist"})
    assert r.status_code == 400
    assert "unknown IDE" in r.json()["detail"]


def test_gui_unknown_strategy_option_returns_400(gui_client: TestClient) -> None:
    csrf = _bootstrap(gui_client)
    gui_client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "__none"})
    csrf = gui_client.post(
        "/wizard/api/project",
        json={"csrf": csrf, "project_path": "__cwd"},
    ).json()["csrf"]
    r = gui_client.post(
        "/wizard/api/strategy",
        json={"csrf": csrf, "option_id": "no-such"},
    )
    assert r.status_code == 400
    assert "unknown option" in r.json()["detail"]


def test_gui_project_path_must_be_in_allowed_list(gui_client: TestClient) -> None:
    csrf = _bootstrap(gui_client)
    gui_client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "__none"})
    csrf = gui_client.cookies[SESSION_COOKIE]
    state = gui_client.get("/wizard/api/state").json()
    csrf = state["csrf"]
    r = gui_client.post(
        "/wizard/api/project",
        json={"csrf": csrf, "project_path": "/etc/passwd"},
    )
    assert r.status_code == 400
    assert "not in allowed list" in r.json()["detail"]


def test_gui_expired_session_yields_401(monkeypatch, tmp_path: Path) -> None:
    """Touch a session timestamp into the past and expect 401."""
    monkeypatch.setattr("koru.wizard.gui.app.discover_installed_ides", lambda: [])
    monkeypatch.setattr("koru.wizard.gui.app.propose_projects", lambda _ides: [])

    store = SessionStore()
    app = create_app(
        strategies_path=_tiny_tree_path(tmp_path),
        language="pl",
        project_override=None,
        create=False,
        store=store,
    )
    client = TestClient(app)
    csrf = _bootstrap(client)
    sid = client.cookies[SESSION_COOKIE]
    sess = store.get(sid)
    assert sess is not None
    sess.last_touch -= 10_000  # force expiry

    r = client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "__none"})
    assert r.status_code == 401


def test_gui_done_endpoint_marks_shutdown(gui_client: TestClient) -> None:
    csrf = _bootstrap(gui_client)
    app = gui_client.app
    assert getattr(app.state, "shutdown", False) is False
    r = gui_client.post("/wizard/done", json={"csrf": csrf})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert app.state.shutdown is True


def test_gui_done_without_session_yields_401(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("koru.wizard.gui.app.discover_installed_ides", lambda: [])
    monkeypatch.setattr("koru.wizard.gui.app.propose_projects", lambda _ides: [])
    app = create_app(
        strategies_path=_tiny_tree_path(tmp_path),
        language="pl",
        project_override=None,
        store=SessionStore(),
    )
    client = TestClient(app)
    # No bootstrap → no cookie → 401
    r = client.post("/wizard/done", json={"csrf": "x"})
    assert r.status_code == 401


def test_gui_state_endpoint_lists_static_links(gui_client: TestClient) -> None:
    """Sanity: HTML references bundled CSS+JS, not a CDN."""
    r = gui_client.get("/wizard")
    assert "/wizard/static/wizard.css" in r.text
    assert "/wizard/static/wizard.js" in r.text
    # No external CDN references in the bundle.
    assert "cdn.tailwindcss" not in r.text
    assert "cdn.jsdelivr" not in r.text


def test_gui_static_assets_served(gui_client: TestClient) -> None:
    r = gui_client.get("/wizard/static/wizard.css")
    assert r.status_code == 200
    assert "koru wizard" in r.text or "--bg" in r.text
    r = gui_client.get("/wizard/static/wizard.js")
    assert r.status_code == 200
    assert "loadState" in r.text or "ScriptedPrompter" in r.text or "wizard" in r.text


def test_gui_app_factory_raises_when_fastapi_missing(monkeypatch, tmp_path: Path) -> None:
    """Cover the optional-dep gate when FastAPI is absent at runtime."""
    monkeypatch.setattr("koru.wizard.gui.app.FastAPI", None)
    with pytest.raises(RuntimeError, match="koru\\[api\\]"):
        create_app(
            strategies_path=_tiny_tree_path(tmp_path),
            language="pl",
            store=SessionStore(),
        )


def test_gui_select_running_ide_proposes_projects(monkeypatch, tmp_path: Path) -> None:
    """When user picks a running IDE, propose_projects is called with that IDE only."""
    monkeypatch.setattr(
        "koru.wizard.gui.app.discover_installed_ides",
        lambda: [
            DetectedIDE(
                id="cursor",
                label="Cursor",
                running=True,
                pid=11,
                path="/usr/bin/cursor",
            ),
            DetectedIDE(
                id="vscode",
                label="VS Code",
                running=True,
                pid=12,
                path="/usr/bin/code",
            ),
        ],
    )
    seen_args: list[list[DetectedIDE]] = []

    def fake_propose(ides):  # noqa: ANN001
        seen_args.append(list(ides))
        return []

    monkeypatch.setattr("koru.wizard.gui.app.propose_projects", fake_propose)
    app = create_app(
        strategies_path=_tiny_tree_path(tmp_path),
        language="pl",
        store=SessionStore(),
    )
    client = TestClient(app)
    csrf = _bootstrap(client)
    r = client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "vscode"})
    assert r.status_code == 200
    assert seen_args
    assert [i.id for i in seen_args[-1]] == ["vscode"]


def test_gui_walk_with_back_to_root_resets_strategy_path(gui_client: TestClient) -> None:
    """Selecting a project after partial strategy walk resets node + path."""
    csrf = _bootstrap(gui_client)
    gui_client.post("/wizard/api/ide", json={"csrf": csrf, "ide_id": "__none"})
    csrf = gui_client.post(
        "/wizard/api/project",
        json={"csrf": csrf, "project_path": "__cwd"},
    ).json()["csrf"]
    r = gui_client.post(
        "/wizard/api/strategy",
        json={"csrf": csrf, "option_id": "a"},
    )
    assert r.json()["strategy_path"] == ["a"]
    csrf = r.json()["csrf"]
    # Re-pick project → wizard rolls strategy back to root.
    r = gui_client.post(
        "/wizard/api/project",
        json={"csrf": csrf, "project_path": "__cwd"},
    )
    assert r.json()["strategy_path"] == []
    assert r.json()["strategy"]["node_id"] == "root"
