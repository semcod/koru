"""Orchestrator for koru photo-VQL observe → act drive (single entrypoint)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from koru.integrations import autonomy_session as _autonomy_session
from koru.integrations.photo_vql_user_guidance import build_user_guidance


def session_prepare_is_fresh(
    session_dir: Path | None = None,
    *,
    max_age_s: float = 120.0,
) -> dict[str, Any] | None:
    """Return recent observe/prepare.json if still valid for this run."""
    root = session_dir or _autonomy_session.active_session_dir()
    if root is None:
        return None
    path = root / "observe" / "prepare.json"
    if not path.is_file():
        return None
    age = time.time() - path.stat().st_mtime
    if max_age_s > 0 and age > max_age_s:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("ok") or payload.get("map_only_fallback"):
        payload.setdefault("session_dir", str(root))
        payload["prepare_reused"] = True
        payload["prepare_age_s"] = round(age, 2)
        return payload
    return None


class PhotoVqlDrive:
    """One-shot photo-VQL drive: prepare (observe) then send_chat (decide/act/verify)."""

    def __init__(self, *, ide: str, source: str | None = None) -> None:
        self.ide = ide
        self.source = source

    def prepare(self, *, reuse_fresh: bool = True) -> dict[str, Any]:
        if reuse_fresh:
            existing = session_prepare_is_fresh()
            if existing is not None:
                return existing
        from koru.integrations.vdisplay_client import prepare_photo_vql_for_drive

        if self.source:
            import os

            os.environ["KORU_VDISPLAY_SOURCE"] = self.source
        return prepare_photo_vql_for_drive(ide=self.ide)

    def act(
        self,
        prompt: str,
        *,
        submit: bool,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        from koru.integrations.vdisplay_client import send_chat

        return send_chat(prompt, ide=self.ide, submit=submit, dry_run=dry_run)

    def run(
        self,
        prompt: str,
        *,
        submit: bool = False,
        dry_run: bool = False,
        reuse_prepare: bool = True,
    ) -> dict[str, Any]:
        observe = self.prepare(reuse_fresh=reuse_prepare)
        can_act = bool(observe.get("ok")) or bool(observe.get("map_only_fallback"))
        if not can_act:
            out = {
                "ok": False,
                "phase": "prepare",
                "backend": "vdisplay+photo-vql",
                "photo_vql_observe": observe,
                "error": observe.get("error") or "prepare failed",
                "hint": observe.get("hint"),
                "competing_ide": observe.get("competing_ide"),
            }
            out["user_next_steps"] = build_user_guidance(
                ide=self.ide,
                observe=observe,
                reply=out,
                source=self.source,
            )
            return out

        reply = self.act(prompt, submit=submit, dry_run=dry_run)
        reply = dict(reply or {"ok": False, "error": "no reply"})
        reply.setdefault("photo_vql_observe", observe)
        prov = observe.get("capture_provenance") or {}
        if prov and "capture_provenance" not in reply:
            reply["capture_provenance"] = prov
        reply["user_next_steps"] = build_user_guidance(
            ide=self.ide,
            observe=observe,
            reply=reply,
            source=self.source,
        )
        return reply


def run_photo_vql_drive(
    prompt: str,
    *,
    ide: str,
    source: str | None = None,
    submit: bool = False,
    dry_run: bool = False,
    reuse_prepare: bool = True,
) -> dict[str, Any]:
    return PhotoVqlDrive(ide=ide, source=source).run(
        prompt,
        submit=submit,
        dry_run=dry_run,
        reuse_prepare=reuse_prepare,
    )


__all__ = [
    "PhotoVqlDrive",
    "run_photo_vql_drive",
    "session_prepare_is_fresh",
]
