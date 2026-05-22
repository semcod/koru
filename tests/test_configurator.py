from __future__ import annotations

import io
import json
from pathlib import Path
from unittest import mock

from koru.configurator import (
    CONFIG_SCHEMA,
    CONFIG_SCHEMA_V1,
    CONFIG_SCHEMA_V2,
    configure_project,
    migrate_project_config,
    render_shell_exports,
)


def test_configure_project_non_interactive_writes_project_config(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()

    result = configure_project(
        project=project,
        workspace=tmp_path,
        ide="windsurf",
        queue_name="ops",
        lan=True,
        port=8765,
        interactive=False,
    )

    assert result.path == project / ".koru" / "config.json"
    assert result.config["schema"] == CONFIG_SCHEMA
    assert result.config["project"] == str(project.resolve())
    assert result.config["workspace"] == str(tmp_path.resolve())
    assert result.config["ide"] == "windsurf"
    assert result.config["queue_name"] == "ops"
    assert result.config["serve"]["lan"] is True
    assert result.config["serve"]["host"] == "0.0.0.0"
    saved = json.loads(result.path.read_text(encoding="utf-8"))
    assert saved["updated_at"] == result.config["updated_at"]


def test_configure_project_interactive_prompts_for_details(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    workspace = tmp_path / "workspace"
    project.mkdir()
    workspace.mkdir()
    answers = io.StringIO(
        "\n"  # workspace default
        "windsurf\n"
        "urgent\n"
        "y\n"
        "\n"  # host defaults to 0.0.0.0 when LAN is enabled
        "9001\n"
        "n\n"
    )
    out = io.StringIO()

    result = configure_project(
        project=project,
        workspace=workspace,
        interactive=True,
        stream_in=answers,
        stream_out=out,
    )

    assert "IDE lane" in out.getvalue()
    assert result.config["workspace"] == str(workspace.resolve())
    assert result.config["ide"] == "windsurf"
    assert result.config["queue_name"] == "urgent"
    assert result.config["serve"] == {
        "auto_port": False,
        "host": "0.0.0.0",
        "lan": True,
        "port": 9001,
    }


def test_render_shell_exports_includes_koru_environment(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    result = configure_project(
        project=project,
        workspace=tmp_path,
        ide="vscode",
        queue_name="default",
        lan=False,
        host="127.0.0.1",
        port=8766,
        auto_port=True,
        interactive=False,
    )

    rendered = render_shell_exports(result.config)

    assert "export KORU_PROJECT=" in rendered
    assert "export KORU_AUTOPILOT_INSTANCE=vscode" in rendered
    assert "export KORU_SERVE_PORT=8766" in rendered
    assert "koru serve" in rendered


def test_migrate_project_config_v1_to_v2_adds_disabled_sections(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    configure_project(
        project=project,
        workspace=tmp_path,
        ide="windsurf",
        interactive=False,
    )
    assert json.loads((project / ".koru" / "config.json").read_text())["schema"] == CONFIG_SCHEMA_V1

    result = migrate_project_config(project)

    assert result.config["schema"] == CONFIG_SCHEMA_V2
    assert result.config["vision"]["enabled"] is False
    assert result.config["vision"]["interval_seconds"] == 30
    assert result.config["mesh"]["enabled"] is False
    assert result.config["browse"]["enabled"] is False
    assert result.config["sandbox"]["enabled"] is False
    assert result.config["delegate"]["accept"] == []
    saved = json.loads(result.path.read_text(encoding="utf-8"))
    assert saved["schema"] == CONFIG_SCHEMA_V2


def test_migrate_project_config_is_idempotent(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    configure_project(project=project, workspace=tmp_path, interactive=False)
    first = migrate_project_config(project)
    tweaked = dict(first.config)
    tweaked["vision"]["interval_seconds"] = 120
    first.path.write_text(json.dumps(tweaked, indent=2) + "\n", encoding="utf-8")
    second = migrate_project_config(project)
    assert second.config["vision"]["interval_seconds"] == 120
    assert second.config["schema"] == CONFIG_SCHEMA_V2


def test_koru_serve_uses_configure_defaults(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    workspace = tmp_path / "workspace"
    project.mkdir()
    workspace.mkdir()
    configure_project(
        project=project,
        workspace=workspace,
        ide="windsurf",
        queue_name="ops",
        lan=True,
        port=9010,
        auto_port=True,
        interactive=False,
    )
    from koruapi import dashboard

    captured = {}

    def fake_serve(config):
        captured["config"] = config
        return 0

    with mock.patch.object(dashboard, "serve", side_effect=fake_serve):
        with mock.patch("koru.activity_log.activity"):
            assert dashboard.dashboard_main(["--project", str(project), "--no-open"]) == 0

    config = captured["config"]
    assert config.project == project.resolve()
    assert config.workspace == workspace.resolve()
    assert config.host == "0.0.0.0"
    assert config.port == 9010
    assert config.queue_name == "ops"
    assert config.auto_port is True
    assert config.lan is True
