"""FastAPI application for ``koru wizard --gui``."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from koru.wizard.cli import _finalise_ticket, _render_next_steps
from koru.wizard.gui.session import SESSION_COOKIE, SessionStore, WizardGuiSession
from koru.wizard.ide import DetectedIDE, discover_installed_ides
from koru.wizard.project import ProjectCandidate, propose_projects
from koru.wizard.tree import TreeOption, load_tree

_GUI_ROOT = Path(__file__).resolve().parent
_STATIC_DIR = _GUI_ROOT / "static"
_TEMPLATE_PATH = _GUI_ROOT / "templates" / "wizard.html"

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:  # pragma: no cover - exercised via _require_fastapi()
    FastAPI = None  # type: ignore[misc, assignment]
    HTTPException = None  # type: ignore[misc, assignment]
    Request = None  # type: ignore[misc, assignment]
    HTMLResponse = None  # type: ignore[misc, assignment]
    JSONResponse = None  # type: ignore[misc, assignment]
    StaticFiles = None  # type: ignore[misc, assignment]


def _require_fastapi() -> None:
    if FastAPI is None:
        raise RuntimeError(
            "koru wizard --gui requires FastAPI and uvicorn. "
            "Install with: pip install 'koru[api]'"
        )


def _read_template() -> str:
    return _TEMPLATE_PATH.read_text(encoding="utf-8")


def _ide_payload(ide: DetectedIDE) -> dict[str, Any]:
    return {
        "id": ide.id,
        "label": ide.label,
        "running": ide.running,
        "pid": ide.pid,
        "path": str(ide.path),
    }


def _project_payload(cand: ProjectCandidate) -> dict[str, Any]:
    return {"path": str(cand.path), "label": cand.label(), "source": cand.source}


def _option_payload(opt: TreeOption) -> dict[str, Any]:
    return {
        "id": opt.id,
        "label": opt.label,
        "help": opt.help,
        "has_help": bool(opt.help),
    }


def _session_state(session: WizardGuiSession) -> dict[str, Any]:
    node = session.tree.node(session.current_node_id)
    payload: dict[str, Any] = {
        "step": session.step,
        "csrf": session.csrf_token,
        "strategy_path": session.strategy_path,
        "ides": [_ide_payload(i) for i in session.ides],
        "projects": [_project_payload(c) for c in session.project_candidates],
        "fallback_cwd": str(session.fallback_cwd),
        "strategy": {
            "node_id": node.id,
            "prompt": node.prompt,
            "options": [_option_payload(o) for o in node.options],
        },
    }
    if session.chosen_ide_id:
        payload["chosen_ide_id"] = session.chosen_ide_id
    if session.project_path:
        payload["project_path"] = str(session.project_path)
    if session.pending_ticket is not None:
        payload["pending"] = {
            "title": session.pending_ticket.title,
            "body": session.pending_ticket.body,
            "labels": list(session.pending_ticket.labels),
            "priority": session.pending_ticket.priority,
        }
    if session.step == "done":
        payload["result"] = {
            "ticket_id": session.ticket_id,
            "ticket_title": session.ticket_title,
            "strategy_path": session.strategy_path,
            "project_path": str(session.project_path) if session.project_path else None,
            "next_steps": list(
                _render_next_steps(session.next_steps, session.ticket_id)
            ),
            "skipped_creation": session.ticket_id is None and not session.create,
        }
    return payload


def _allowed_project_paths(session: WizardGuiSession) -> set[Path]:
    permitted_project_paths = {session.fallback_cwd.resolve()}
    permitted_project_paths.update(c.path.resolve() for c in session.project_candidates)
    if session.project_path is not None:
        permitted_project_paths.add(session.project_path.resolve())
    return permitted_project_paths


def _check_csrf(session: WizardGuiSession, token: str | None, HTTPException: Any) -> None:
    if not token or not secrets.compare_digest(session.csrf_token, token):
        raise HTTPException(status_code=403, detail="invalid CSRF token")


def _get_session(request: Any, session_store: SessionStore) -> WizardGuiSession:
    session_store.purge_expired()
    sid = request.cookies.get(SESSION_COOKIE)
    session = session_store.get(sid)
    if session is None:
        raise HTTPException(status_code=401, detail="session expired; reload /wizard")
    return session


def _cookie_response(payload: dict[str, Any], session: WizardGuiSession) -> Any:
    response = JSONResponse(payload)
    response.set_cookie(
        SESSION_COOKIE,
        session.session_id,
        httponly=True,
        samesite="lax",
        max_age=1800,
    )
    return response


def _ensure_session(request: Any, app: Any, session_store: SessionStore) -> WizardGuiSession:
    sid = request.cookies.get(SESSION_COOKIE)
    session = session_store.get(sid)
    if session is not None:
        return session
    cfg = app.state.gui_config
    session = WizardGuiSession.new(
        strategies_path=cfg["strategies_path"],
        language=cfg["language"],
        bilingual_separator=cfg["bilingual_separator"],
        create=cfg["create"],
        tree=cfg["tree"],
        ides=discover_installed_ides(),
        fallback_cwd=Path.cwd(),
        project_override=cfg["project_override"],
    )
    session_store.create(session)
    return session


def _select_ide(session: WizardGuiSession, body: dict[str, Any]) -> None:
    _check_csrf(session, body.get("csrf"), HTTPException)
    ide_id = str(body.get("ide_id") or "").strip()
    if ide_id and ide_id != "__none":
        if not any(i.id == ide_id for i in session.ides):
            raise HTTPException(status_code=400, detail=f"unknown IDE {ide_id!r}")
        session.chosen_ide_id = ide_id
        chosen = next(i for i in session.ides if i.id == ide_id)
        session.project_candidates = propose_projects([chosen])
    else:
        session.chosen_ide_id = None
        session.project_candidates = propose_projects(session.ides)
    session.step = "project"
    session.touch()


def _select_project(session: WizardGuiSession, body: dict[str, Any]) -> None:
    _check_csrf(session, body.get("csrf"), HTTPException)
    raw = str(body.get("project_path") or "").strip()
    project = session.fallback_cwd if raw == "__cwd" else Path(raw).expanduser().resolve()
    permitted_project_paths = _allowed_project_paths(session)
    if project not in permitted_project_paths:
        raise HTTPException(status_code=400, detail="project path not in allowed list")
    session.project_path = project
    session.current_node_id = session.tree.root_id
    session.strategy_path = []
    session.pending_ticket = None
    session.step = "strategy"
    session.touch()


def _select_strategy(session: WizardGuiSession, body: dict[str, Any]) -> None:
    _check_csrf(session, body.get("csrf"), HTTPException)
    if session.project_path is None:
        raise HTTPException(status_code=400, detail="project not selected")
    option_id = str(body.get("option_id") or "").strip()
    node = session.tree.node(session.current_node_id)
    matched = next((o for o in node.options if o.id == option_id), None)
    if matched is None:
        raise HTTPException(status_code=400, detail=f"unknown option {option_id!r}")
    session.strategy_path.append(option_id)
    if matched.ticket:
        session.pending_ticket = session.tree.ticket(matched.ticket)
        session.step = "confirm"
    elif matched.next_node:
        session.current_node_id = matched.next_node
    else:
        raise HTTPException(status_code=500, detail="option has no ticket or next node")
    session.touch()


def _confirm_ticket(session: WizardGuiSession, body: dict[str, Any]) -> None:
    _check_csrf(session, body.get("csrf"), HTTPException)
    if session.pending_ticket is None or session.project_path is None:
        raise HTTPException(status_code=400, detail="nothing to confirm")
    template = session.pending_ticket
    ticket_id, ticket_body = _finalise_ticket(template, session.project_path, create=session.create)
    session.ticket_id = ticket_id
    session.ticket_title = template.title
    session.ticket_body = ticket_body
    session.next_steps = session.tree.effective_next_steps(template.id)
    session.pending_ticket = None
    session.step = "done"
    session.touch()


def _register_routes(app: Any, session_store: SessionStore) -> None:
    @app.get("/wizard")
    def wizard_page(request: Request) -> HTMLResponse:
        session_store.purge_expired()
        session = _ensure_session(request, app, session_store)
        response = HTMLResponse(content=_read_template())
        response.set_cookie(
            SESSION_COOKIE,
            session.session_id,
            httponly=True,
            samesite="lax",
            max_age=1800,
        )
        return response

    @app.get("/wizard/api/state")
    def api_state(request: Request) -> JSONResponse:
        session_store.purge_expired()
        session = _ensure_session(request, app, session_store)
        return _cookie_response(_session_state(session), session)

    @app.post("/wizard/api/ide")
    async def api_select_ide(request: Request) -> JSONResponse:
        session = _get_session(request, session_store)
        _select_ide(session, await request.json())
        return JSONResponse(_session_state(session))

    @app.post("/wizard/api/project")
    async def api_select_project(request: Request) -> JSONResponse:
        session = _get_session(request, session_store)
        _select_project(session, await request.json())
        return JSONResponse(_session_state(session))

    @app.post("/wizard/api/strategy")
    async def api_strategy_choice(request: Request) -> JSONResponse:
        session = _get_session(request, session_store)
        _select_strategy(session, await request.json())
        return JSONResponse(_session_state(session))

    @app.post("/wizard/api/confirm")
    async def api_confirm(request: Request) -> JSONResponse:
        session = _get_session(request, session_store)
        _confirm_ticket(session, await request.json())
        return JSONResponse(_session_state(session))

    @app.post("/wizard/done")
    async def api_done(request: Request) -> JSONResponse:
        _get_session(request, session_store)
        app.state.shutdown = True
        server = getattr(app.state, "uvicorn_server", None)
        if server is not None:
            server.should_exit = True
        return JSONResponse({"ok": True, "message": "wizard finished; server shutting down"})


def create_app(
    *,
    strategies_path: Path,
    language: str | list[str] | None,
    project_override: Path | None = None,
    bilingual_separator: str = " · ",
    create: bool = True,
    store: SessionStore | None = None,
) -> Any:
    """Build the FastAPI app (requires ``koru[api]``)."""
    _require_fastapi()
    session_store = store or SessionStore()
    tree = load_tree(strategies_path, language=language, bilingual_separator=bilingual_separator)

    app = FastAPI(title="koru wizard", docs_url=None, redoc_url=None)
    app.state.session_store = session_store
    app.state.shutdown = False
    app.state.gui_config = {
        "strategies_path": strategies_path,
        "language": language,
        "bilingual_separator": bilingual_separator,
        "project_override": project_override,
        "create": create,
        "tree": tree,
    }

    if _STATIC_DIR.is_dir():
        app.mount("/wizard/static", StaticFiles(directory=str(_STATIC_DIR)), name="wizard-static")

    _register_routes(app, session_store)
    return app
