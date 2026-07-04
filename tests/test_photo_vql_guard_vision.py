"""Vision-LLM decision relaxes non-competing capture-title mismatches only."""

from __future__ import annotations

import pytest

from koru.integrations import photo_vql_guard as g
from koru.integrations import vdisplay_client as vc


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in (
        "KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH",
        "KORU_VDISPLAY_ALLOW_IDE_MISMATCH",
        "KORU_VDISPLAY_LLM_VISION_DECISION",
        "KORU_VDISPLAY_ALLOW_ACTUATION_ON_CAPTURE_MISMATCH",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(vc, "_dry_run", lambda: False)


def test_llm_vision_decision_flag(monkeypatch):
    assert g.llm_vision_decision_enabled() is False
    monkeypatch.setenv("KORU_VDISPLAY_LLM_VISION_DECISION", "1")
    assert g.llm_vision_decision_enabled() is True


def test_vision_decision_does_not_widen_map_on_mismatch(monkeypatch):
    # allow_prepare_map_on_mismatch stays explicit-flag only (safety).
    monkeypatch.setenv("KORU_VDISPLAY_LLM_VISION_DECISION", "1")
    assert g.allow_prepare_map_on_mismatch() is False


def test_non_competing_mismatch_relaxed_under_vision(monkeypatch):
    monkeypatch.setenv("KORU_VDISPLAY_LLM_VISION_DECISION", "1")
    # editor breadcrumb / Qoder panel — no competing IDE named
    mismatch = {"message": "does not look like jetbrains", "window_titles": ["mainv Current File"]}
    assert vc._mismatch_shows_competing_ide(mismatch, ide="jetbrains") is False
    assert (
        vc._photo_vql_capture_mismatch_blocks(mismatch=mismatch, ide="jetbrains", is_code_edit=False)
        is False
    )


def test_competing_ide_capture_always_blocks_even_under_vision(monkeypatch):
    monkeypatch.setenv("KORU_VDISPLAY_LLM_VISION_DECISION", "1")
    mismatch = {"message": "capture shows Cursor", "window_titles": ["Cursor"]}
    assert vc._mismatch_shows_competing_ide(mismatch, ide="jetbrains") is True
    assert (
        vc._photo_vql_capture_mismatch_blocks(mismatch=mismatch, ide="jetbrains", is_code_edit=False)
        is True
    )


def test_competing_detected_field_blocks(monkeypatch):
    monkeypatch.setenv("KORU_VDISPLAY_LLM_VISION_DECISION", "1")
    mismatch = {"message": "looks like a different IDE", "competing_detected": ["vscode"]}
    assert vc._mismatch_shows_competing_ide(mismatch, ide="jetbrains") is True


def test_non_competing_mismatch_still_blocks_without_vision(monkeypatch):
    # No vision, no override flags → the mismatch still hard-blocks.
    mismatch = {"message": "does not look like jetbrains", "window_titles": ["mainv Current File"]}
    assert (
        vc._photo_vql_capture_mismatch_blocks(mismatch=mismatch, ide="jetbrains", is_code_edit=False)
        is True
    )
