"""Configuration helpers for the koru dashboard HTTP API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koru.configurator import CONFIG_REL_PATH, configure_project, load_project_config
from koruide.ide import autopilot_ide_choices


@dataclass(frozen=True)
class DashboardConfigDefaults:
  """Serve-time defaults used by the dashboard Settings API."""

  workspace: Path
  host: str
  port: int
  lan: bool
  auto_port: bool
  queue_name: str | None


def bool_from_dashboard(value: object, *, default: bool = False) -> bool:
  if value is None:
    return default
  if isinstance(value, bool):
    return value
  return str(value).strip().lower() in {"1", "true", "yes", "on", "y", "tak"}


def int_from_dashboard(value: object, *, default: int) -> int:
  if value is None or str(value).strip() == "":
    return default
  return int(str(value).strip())


def dashboard_config_payload(
  project: Path,
  defaults: DashboardConfigDefaults,
) -> dict[str, Any]:
  saved = load_project_config(project)
  raw_serve = saved.get("serve")
  serve: dict[str, Any] = raw_serve if isinstance(raw_serve, dict) else {}
  effective = {
    "project": str(project.resolve()),
    "workspace": str(saved.get("workspace") or defaults.workspace),
    "ide": str(saved.get("ide") or "auto"),
    "queue_name": str(saved.get("queue_name") or defaults.queue_name or "default"),
    "serve": {
      "host": str(serve.get("host") or defaults.host),
      "port": int(serve.get("port") or defaults.port),
      "lan": bool_from_dashboard(
        serve.get("lan"),
        default=bool(defaults.lan or defaults.host in {"0.0.0.0", "::"}),
      ),
      "auto_port": bool_from_dashboard(
        serve.get("auto_port"),
        default=bool(defaults.auto_port),
      ),
    },
  }
  return {
    "ok": True,
    "path": str(project.resolve() / CONFIG_REL_PATH),
    "exists": bool((project.resolve() / CONFIG_REL_PATH).is_file()),
    "config": {
      **effective,
      **{k: v for k, v in saved.items() if k in {"schema", "created_at", "updated_at"}},
    },
    "ide_choices": list(autopilot_ide_choices()),
  }


def save_dashboard_config(
  project: Path,
  body: dict[str, Any],
  defaults: DashboardConfigDefaults,
) -> Any:
  raw_serve = body.get("serve")
  serve: dict[str, Any] = raw_serve if isinstance(raw_serve, dict) else {}
  workspace_raw = str(body.get("workspace") or "").strip()
  return configure_project(
    project=project,
    workspace=Path(workspace_raw) if workspace_raw else None,
    ide=str(body.get("ide") or "auto").strip() or "auto",
    queue_name=str(body.get("queue_name") or "default").strip() or "default",
    host=str(serve.get("host") or defaults.host).strip() or defaults.host,
    port=int_from_dashboard(serve.get("port"), default=defaults.port),
    lan=bool_from_dashboard(serve.get("lan"), default=bool(defaults.lan)),
    auto_port=bool_from_dashboard(serve.get("auto_port"), default=bool(defaults.auto_port)),
    interactive=False,
  )