"""In-memory wizard GUI sessions (localhost single-user)."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

from koru.wizard.ide import DetectedIDE
from koru.wizard.project import ProjectCandidate
from koru.wizard.tree import StrategyTree, TicketTemplate

SESSION_COOKIE = "koru_wizard_session"
SESSION_TTL_SEC = 30 * 60


@dataclass
class WizardGuiSession:
    """Server-side state for one browser wizard run."""

    session_id: str
    csrf_token: str
    strategies_path: Path
    language: str | list[str] | None
    bilingual_separator: str
    create: bool
    tree: StrategyTree
    created_at: float = field(default_factory=time.time)
    last_touch: float = field(default_factory=time.time)

    ides: list[DetectedIDE] = field(default_factory=list)
    project_candidates: list[ProjectCandidate] = field(default_factory=list)
    fallback_cwd: Path = field(default_factory=Path.cwd)

    step: str = "ide"
    chosen_ide_id: str | None = None
    project_path: Path | None = None
    strategy_path: list[str] = field(default_factory=list)
    current_node_id: str = ""
    pending_ticket: TicketTemplate | None = None

    ticket_id: str | None = None
    ticket_title: str = ""
    ticket_body: str = ""
    next_steps: tuple[str, ...] = ()

    def touch(self) -> None:
        self.last_touch = time.time()

    def expired(self, *, ttl: int = SESSION_TTL_SEC) -> bool:
        return (time.time() - self.last_touch) > ttl

    @staticmethod
    def new(
        *,
        strategies_path: Path,
        language: str | list[str] | None,
        bilingual_separator: str,
        create: bool,
        tree: StrategyTree,
        ides: list[DetectedIDE],
        fallback_cwd: Path,
        project_override: Path | None = None,
    ) -> WizardGuiSession:
        session = WizardGuiSession(
            session_id=secrets.token_urlsafe(16),
            csrf_token=secrets.token_urlsafe(32),
            strategies_path=strategies_path,
            language=language,
            bilingual_separator=bilingual_separator,
            create=create,
            tree=tree,
            ides=ides,
            fallback_cwd=fallback_cwd.resolve(),
            current_node_id=tree.root_id,
        )
        if project_override is not None:
            session.project_path = project_override.resolve()
            session.step = "strategy"
        return session


class SessionStore:
    """Thread-unsafe in-memory store (single localhost user)."""

    def __init__(self) -> None:
        self._sessions: dict[str, WizardGuiSession] = {}

    def create(self, session: WizardGuiSession) -> WizardGuiSession:
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str | None) -> WizardGuiSession | None:
        if not session_id:
            return None
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.expired():
            self.delete(session_id)
            return None
        session.touch()
        return session

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def purge_expired(self) -> None:
        expired = [sid for sid, s in self._sessions.items() if s.expired()]
        for sid in expired:
            self.delete(sid)
