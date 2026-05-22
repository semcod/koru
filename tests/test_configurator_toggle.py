from __future__ import annotations

import json
from pathlib import Path

import pytest

from koru.configurator import (
    CONFIG_SCHEMA_V2,
    configure_main,
    configure_project,
    toggle_feature_sections,
)


def test_toggle_feature_sections_enables_and_disables(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    configure_project(project=project, workspace=tmp_path, interactive=False)

    result = toggle_feature_sections(project, enable=("vision", "mesh"))
    assert result.config["schema"] == CONFIG_SCHEMA_V2
    assert result.config["vision"]["enabled"] is True
    assert result.config["mesh"]["enabled"] is True
    saved = json.loads(result.path.read_text(encoding="utf-8"))
    assert saved["mesh"]["enabled"] is True

    result = toggle_feature_sections(project, disable=("vision",))
    assert result.config["vision"]["enabled"] is False
    assert result.config["mesh"]["enabled"] is True


def test_toggle_feature_sections_rejects_unknown_name(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    configure_project(project=project, workspace=tmp_path, interactive=False)
    with pytest.raises(ValueError, match="unknown feature"):
        toggle_feature_sections(project, enable=("bogus",))


def test_configure_cli_enable_flag(tmp_path: Path, capsys) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    configure_project(project=project, workspace=tmp_path, interactive=False)

    rc = configure_main(["--project", str(project), "--enable", "vision,mesh"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "features +vision, +mesh" in out
    saved = json.loads((project / ".koru" / "config.json").read_text(encoding="utf-8"))
    assert saved["vision"]["enabled"] is True
    assert saved["mesh"]["enabled"] is True
