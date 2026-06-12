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

        self._set_source_env()
        return prepare_photo_vql_for_drive(ide=self.ide)

    def _set_source_env(self) -> None:
        if not self.source:
            return
        import os

        os.environ["KORU_VDISPLAY_SOURCE"] = self.source

    def act(
        self,
        prompt: str,
        *,
        submit: bool,
        dry_run: bool = False,
        observe: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        observe = observe or {}
        if observe.get("map_only_fallback") and not dry_run:
            llm_reply = self._act_map_only_with_photo_vql(
                prompt,
                submit=submit,
                observe=observe,
            )
            if llm_reply is not None:
                return llm_reply
            ide_prompt = self._act_map_only_with_ide_prompt(
                prompt,
                submit=submit,
                observe=observe,
            )
            if ide_prompt is not None:
                return ide_prompt

        return self._send_chat(prompt, submit=submit, dry_run=dry_run)

    def _act_map_only_with_photo_vql(
        self,
        prompt: str,
        *,
        submit: bool,
        observe: dict[str, Any],
    ) -> dict[str, Any] | None:
        from koru.integrations.photo_vql_config import llm_vision_enabled
        from koru.integrations.vdisplay_client import (
            _normalize_photo_vql_drive_result,
            _vdisplay_source,
            perform_photo_vql_focus_and_edit,
        )

        if not llm_vision_enabled():
            return None
        photo_res = perform_photo_vql_focus_and_edit(
            prompt,
            ide=self.ide,
            source=self.source or _vdisplay_source(),
            submit=submit,
            image_path=self._observe_png(observe),
        )
        reply = _normalize_photo_vql_drive_result(
            photo_res,
            ide=self.ide,
            submit=submit,
        )
        if not self._photo_vql_attempt_succeeded(photo_res=photo_res, reply=reply):
            return None
        reply = dict(reply)
        reply.setdefault("photo_vql_observe", observe)
        self._mark_llm_backend_if_used(reply=reply, photo_res=photo_res)
        return reply

    @staticmethod
    def _observe_png(observe: dict[str, Any]) -> str | None:
        png = observe.get("png")
        if png:
            return str(png)
        paths = observe.get("observe_session_paths") or {}
        return str(paths.get("png")) if paths.get("png") else None

    @staticmethod
    def _photo_vql_attempt_succeeded(
        *,
        photo_res: dict[str, Any],
        reply: dict[str, Any],
    ) -> bool:
        edit_ok = bool((photo_res.get("edit") or {}).get("ok"))
        plan_ok = bool((photo_res.get("vql_command_plan") or {}).get("inference_ok"))
        return bool(reply.get("ok")) or (edit_ok and plan_ok)

    @staticmethod
    def _mark_llm_backend_if_used(
        *,
        reply: dict[str, Any],
        photo_res: dict[str, Any],
    ) -> None:
        target = photo_res.get("vql_target") or {}
        llm_detect = str(target.get("id") or "").startswith("llm:")
        if llm_detect or photo_res.get("llm_used"):
            reply["backend"] = "vdisplay+photo-vql+llm"

    def _act_map_only_with_ide_prompt(
        self,
        prompt: str,
        *,
        submit: bool,
        observe: dict[str, Any],
    ) -> dict[str, Any] | None:
        from koru.integrations.vdisplay_client import send_chat_via_ide_prompt

        ide_prompt = send_chat_via_ide_prompt(
            prompt,
            ide=self.ide,
            submit=submit,
            dry_run=False,
        )
        if ide_prompt is None or not ide_prompt.get("ok"):
            return None
        ide_prompt.setdefault("map_only_fallback", True)
        ide_prompt.setdefault("photo_vql_observe", observe)
        return ide_prompt

    def _send_chat(self, prompt: str, *, submit: bool, dry_run: bool) -> dict[str, Any]:
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
        if not self._observe_allows_act(observe):
            return self._prepare_failed_reply(observe)

        reply = self.act(prompt, submit=submit, dry_run=dry_run, observe=observe)
        return self._finalize_reply(reply, observe=observe)

    @staticmethod
    def _observe_allows_act(observe: dict[str, Any]) -> bool:
        return bool(observe.get("ok")) or bool(observe.get("map_only_fallback"))

    def _prepare_failed_reply(self, observe: dict[str, Any]) -> dict[str, Any]:
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

    def _finalize_reply(
        self,
        reply: dict[str, Any] | None,
        *,
        observe: dict[str, Any],
    ) -> dict[str, Any]:
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
