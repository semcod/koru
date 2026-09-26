"""Pin tests for the ticket-236 vdisplay_client module split.

The historical monolith `koru.integrations.vdisplay_client` (272 top-level
functions) was split into responsibility modules under
`koru.integrations.vdisplay`. These tests pin the two contracts the split
must keep: the facade re-export surface, and facade-level monkeypatching of
moved code (moved modules resolve former module globals through the facade
at call time).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import koru.integrations.vdisplay_client as vdisplay_client
from koru.integrations import vdisplay


def _repo_module(relative: str) -> Path:
    return Path(__file__).resolve().parent.parent / relative


def test_facade_reexports_every_moved_name() -> None:
    moved_modules = [
        "source_policy",
        "vql_sidecar",
        "imgl_loader",
        "ide_control",
        "drive_prepare",
        "chat_send",
        "input_actuation",
        "chat_target",
        "map_pointer",
        "command_plan",
        "capture_gates",
        "focus_edit",
        "vql_metadata",
    ]
    for name in moved_modules:
        module = getattr(vdisplay, name)
        tree = ast.parse(_repo_module(f"src/koru/integrations/vdisplay/{name}.py").read_text())
        top_level: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                top_level.add(node.target.id)
            elif isinstance(node, ast.Assign):
                top_level.update(
                    t.id for t in node.targets if isinstance(t, ast.Name)
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_vdc"):
                    top_level.add(node.name)
        assert top_level, name
        for fn in top_level:
            assert getattr(module, fn, None) is not None, f"{name}.{fn} missing"
            assert hasattr(vdisplay_client, fn), f"facade lost {name}.{fn}"


def test_facade_all_importable() -> None:
    assert len(vdisplay_client.__all__) >= 20
    for name in vdisplay_client.__all__:
        assert getattr(vdisplay_client, name, None) is not None, name


def test_facade_monkeypatch_still_steers_moved_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """A patch on the facade must reach code that moved to chat_send."""
    monkeypatch.setattr(vdisplay_client, "_CHAT_INPUT_SELECTORS", ({"role": "input"},))
    assert vdisplay_client._chat_selectors_for("windsurf") == ({"role": "input"},)


def test_facade_monkeypatch_still_steers_same_module_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A patch must reach same-module siblings too (LOAD_GLOBAL semantics)."""
    monkeypatch.setattr(
        vdisplay_client,
        "_control_click",
        lambda **kwargs: {"ok": True, "local_x": 1, "local_y": 2},
    )
    assert vdisplay_client._control_click(backend="vision")["ok"] is True
    # _type_text_via_ide_map_fallback (input_actuation) calls _control_click
    # through the facade even though both moved into the same module.
    monkeypatch.setattr(vdisplay_client, "_ide_map_message_target", lambda _app: "t")
    monkeypatch.setattr(
        vdisplay_client,
        "_vdisplay_source_for_ide",
        lambda _ide: "source",
    )
    monkeypatch.setattr(
        vdisplay_client,
        "_type_text_at_vql_coords",
        lambda value, **kwargs: {"ok": True, "value": value},
    )
    out = vdisplay_client._type_text_via_ide_map_fallback(
        "hi", map_path="/m.json", app_id="pycharm", ide="jetbrains"
    )
    assert out["ok"] is True


def test_vql_shims_keep_facade_identity() -> None:
    """The vdisplay.vql shims are real functions on the facade, not aliases."""
    for name in ("_main_vql_layer_count", "_vql_from_ui_elements", "_vdisplay_vql"):
        assert callable(getattr(vdisplay_client, name)), name
        assert getattr(vdisplay.chat_target, "get_vql_chat_target_from_photo", None)
        assert vdisplay_client.get_vql_chat_target_from_photo is (
            vdisplay.chat_target.get_vql_chat_target_from_photo
        )


def test_every_module_under_god_gate() -> None:
    facade_tree = ast.parse(
        _repo_module("src/koru/integrations/vdisplay_client.py").read_text()
    )
    facade_defs = [
        node.name
        for node in facade_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert len(facade_defs) <= 40, facade_defs
    for path in sorted(_repo_module("src/koru/integrations/vdisplay").glob("*.py")):
        tree = ast.parse(path.read_text())
        defs = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert len(defs) <= 40, f"{path.name}: {len(defs)}"


def test_moved_behavior_sanity(monkeypatch: pytest.MonkeyPatch) -> None:
    # one behavior per responsibility module, at its new home
    monkeypatch.delenv("KORU_VDISPLAY_CONTROL_FALLBACK", raising=False)
    assert vdisplay_client._ide_hints("jetbrains")["app"] == "pycharm"
    assert vdisplay_client._canonical_ide("Cursor") in {"cursor"}
    assert vdisplay_client.vdisplay_fallback_enabled(
        ide="windsurf", plugin_connected=False
    ) is True
