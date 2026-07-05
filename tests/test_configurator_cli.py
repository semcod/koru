from __future__ import annotations

import json
from pathlib import Path

from koru.configurator import CONFIG_SCHEMA, CONFIG_SCHEMA_V2, configure_main


def _seed_config(project: Path) -> None:
    """Write a minimal v1 config so migrate/toggle have something to act on."""
    config_dir = project / ".koru"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text(
        json.dumps({"schema": CONFIG_SCHEMA, "project": str(project), "vision": {"enabled": False}}) + "\n",
        encoding="utf-8",
    )


def test_cli_write_supports_json_format(tmp_path: Path, capsys) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    rc = configure_main(
        ["--project", str(project), "--workspace", str(tmp_path), "--non-interactive", "--format", "json"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    decoded = json.loads(out)
    assert decoded["schema"] == CONFIG_SCHEMA
    assert decoded["project"] == str(project.resolve())


def test_cli_write_supports_shell_format(tmp_path: Path, capsys) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    rc = configure_main(
        ["--project", str(project), "--workspace", str(tmp_path), "--non-interactive", "--format", "shell"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "export KORU_PROJECT=" in out
    assert out.startswith("export ")


def test_cli_disable_flips_feature_off(tmp_path: Path, capsys) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    _seed_config(project)
    rc = configure_main(["--project", str(project), "--disable", "vision"])
    assert rc == 0
    saved = json.loads((project / ".koru" / "config.json").read_text(encoding="utf-8"))
    assert saved["schema"] == CONFIG_SCHEMA_V2
    assert saved["vision"]["enabled"] is False
    out = capsys.readouterr().out
    assert "-vision" in out


def test_cli_migrate_upgrades_to_v2(tmp_path: Path, capsys) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    _seed_config(project)
    rc = configure_main(["--project", str(project), "--migrate"])
    assert rc == 0
    saved = json.loads((project / ".koru" / "config.json").read_text(encoding="utf-8"))
    assert saved["schema"] == CONFIG_SCHEMA_V2
    out = capsys.readouterr().out
    assert "migrated" in out
    assert CONFIG_SCHEMA_V2 in out


def test_cli_migrate_returns_2_when_no_config(tmp_path: Path, capsys) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    rc = configure_main(["--project", str(project), "--migrate"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "koru configure:" in err


def test_cli_toggle_unknown_feature_returns_2(tmp_path: Path, capsys) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    _seed_config(project)
    rc = configure_main(["--project", str(project), "--enable", "bogus"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "unknown feature" in err


def test_split_feature_list_parses_commas_and_strips() -> None:
    from koru.configurator.cli import _split_feature_list

    assert _split_feature_list(["vision,mesh", " browse ", "", "SANDBOX"]) == (
        "vision",
        "mesh",
        "browse",
        "sandbox",
    )
    assert _split_feature_list([]) == ()
    assert _split_feature_list(["", "  "]) == ()
