from __future__ import annotations

from pathlib import Path

from koru.semcod_tools import detect_semcod_tools


def test_detect_semcod_tools_covers_core_semcod_extensions(tmp_path: Path) -> None:
    detected = {tool.id: tool for tool in detect_semcod_tools(tmp_path)}

    expected = {
        "planfile",
        "koru",
        "wup",
        "testql",
        "regix",
        "redup",
        "sumr",
        "sumd",
        "code2llm",
        "prefact",
        "pfix",
        "vallm",
        "redsl",
        "llx",
        "doql",
        "redeploy",
        "goal",
        "costs",
        "op3",
        "toonic",
        "protogate",
        "rebuild",
        "mdflow",
        "metrun",
        "aider",
    }

    assert expected <= set(detected)
    for tool_id in expected:
        assert detected[tool_id].role
        assert detected[tool_id].command_hint


def test_detect_semcod_tools_marks_pyproject_config_without_binary(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.redsl]\n", encoding="utf-8")

    detected = {tool.id: tool for tool in detect_semcod_tools(tmp_path)}

    assert detected["redsl"].config_present is True
    assert detected["redsl"].via in {"PATH", "module", "config", "missing"}
