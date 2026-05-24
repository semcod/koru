"""Configuration helpers for the koru dashboard HTTP API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koru.configurator import CONFIG_REL_PATH, configure_project, load_project_config
from koru.dotenv_loader import load_dotenv
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


def _dotenv_path(project: Path) -> Path:
  return project.resolve() / ".env"


def _dotenv_payload(project: Path) -> dict[str, Any]:
  path = _dotenv_path(project)
  text = ""
  exists = path.is_file()
  if exists:
    try:
      text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
      text = ""
  return {
    "path": str(path),
    "exists": exists,
    "text": text,
  }


def save_dashboard_dotenv(project: Path, text: str) -> Path:
  path = _dotenv_path(project)
  path.write_text(text, encoding="utf-8")
  load_dotenv(project, override=True)
  return path


def _saved_serve_config(saved: dict[str, Any]) -> dict[str, Any]:
  raw_serve = saved.get("serve")
  return raw_serve if isinstance(raw_serve, dict) else {}


def _dashboard_config_path_payload(project: Path) -> tuple[str, bool]:
  path = project.resolve() / CONFIG_REL_PATH
  return str(path), path.is_file()


def _effective_serve_config(
  serve: dict[str, Any],
  defaults: DashboardConfigDefaults,
) -> dict[str, Any]:
  return {
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
  }


def _effective_dashboard_config(
  project: Path,
  saved: dict[str, Any],
  defaults: DashboardConfigDefaults,
) -> dict[str, Any]:
  effective = {
    "project": str(project.resolve()),
    "workspace": str(saved.get("workspace") or defaults.workspace),
    "ide": str(saved.get("ide") or "auto"),
    "queue_name": str(saved.get("queue_name") or defaults.queue_name or "default"),
    "serve": _effective_serve_config(_saved_serve_config(saved), defaults),
  }
  return {
    **effective,
    **{k: v for k, v in saved.items() if k in {"schema", "created_at", "updated_at"}},
  }


def dashboard_config_payload(
  project: Path,
  defaults: DashboardConfigDefaults,
) -> dict[str, Any]:
  saved = load_project_config(project)
  config_path, config_exists = _dashboard_config_path_payload(project)
  return {
    "ok": True,
    "path": config_path,
    "exists": config_exists,
    "config": _effective_dashboard_config(project, saved, defaults),
    "dotenv": _dotenv_payload(project),
    "ide_choices": list(autopilot_ide_choices()),
  }


def _dashboard_config_request_kwargs(
  body: dict[str, Any],
  defaults: DashboardConfigDefaults,
) -> dict[str, Any]:
  raw_serve = body.get("serve")
  serve: dict[str, Any] = raw_serve if isinstance(raw_serve, dict) else {}
  workspace_raw = str(body.get("workspace") or "").strip()
  return {
    "workspace": Path(workspace_raw) if workspace_raw else None,
    "ide": str(body.get("ide") or "auto").strip() or "auto",
    "queue_name": str(body.get("queue_name") or "default").strip() or "default",
    "host": str(serve.get("host") or defaults.host).strip() or defaults.host,
    "port": int_from_dashboard(serve.get("port"), default=defaults.port),
    "lan": bool_from_dashboard(serve.get("lan"), default=bool(defaults.lan)),
    "auto_port": bool_from_dashboard(serve.get("auto_port"), default=bool(defaults.auto_port)),
  }


def _save_dashboard_dotenv_from_body(project: Path, body: dict[str, Any]) -> None:
  raw_dotenv = body.get("dotenv")
  if isinstance(raw_dotenv, dict) and "text" in raw_dotenv:
    save_dashboard_dotenv(project, str(raw_dotenv.get("text") or ""))


def save_dashboard_config(
  project: Path,
  body: dict[str, Any],
  defaults: DashboardConfigDefaults,
) -> Any:
  result = configure_project(
    project=project,
    interactive=False,
    **_dashboard_config_request_kwargs(body, defaults),
  )
  _save_dashboard_dotenv_from_body(project, body)
  return result
