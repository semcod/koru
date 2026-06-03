"""Issue-detection helpers for ``install_manager``.

Extracted from ``install_manager.py`` (R-IM1) so that the issue-check
chain (``ManagerIssue`` producers) lives in a focused module separate from
report assembly and repair orchestration.

Each ``check_*`` function is a pure function that returns
``list[ManagerIssue]``. They are composed by ``install_manager._issue_list``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ManagerIssue:
  """Single issue surfaced by the install manager.

  Re-exported from the legacy ``install_manager`` symbol; tests and CLI
  serialization rely on this class staying source-of-truth here.
  """

  code: str
  severity: str
  message: str
  fix: str | None = None

  def to_dict(self) -> dict[str, Any]:
    out: dict[str, Any] = {
      "code": self.code,
      "severity": self.severity,
      "message": self.message,
    }
    if self.fix:
      out["fix"] = self.fix
    return out


# ---------------------------------------------------------------------------
# Path / environment checks
# ---------------------------------------------------------------------------


def is_pyenv_shim(path: Path | None) -> bool:
  return bool(path and ".pyenv" in path.parts and "shims" in path.parts)


def check_koru_path_issues(
  path_koru: Path | None,
  repo_koru: Path | None,
  *,
  source_root: Path,
  editable_source_root: Path | None = None,
) -> list[ManagerIssue]:
  issues: list[ManagerIssue] = []
  if path_koru is None:
    issues.append(
      ManagerIssue(
        "koru_not_in_path",
        "error",
        "`koru` is not available in PATH.",
        "Install the package or use the repo-local .venv/bin/koru explicitly.",
      ),
    )
  elif repo_koru is not None and path_koru != repo_koru:
    if editable_source_root is not None and editable_source_root == source_root.resolve():
      return issues
    issues.append(
      ManagerIssue(
        "koru_path_mismatch",
        "warning",
        f"PATH resolves koru to {path_koru}, but repo-local koru is {repo_koru}.",
        (
          f"Use `{repo_koru}` or put `{repo_koru.parent}` before other "
          "koru installs in PATH."
        ),
      ),
    )
  return issues


def check_pyenv_shim_issue(path_koru: Path | None) -> list[ManagerIssue]:
  if is_pyenv_shim(path_koru):
    return [
      ManagerIssue(
        "koru_pyenv_shim",
        "warning",
        f"PATH resolves koru through a pyenv shim ({path_koru}).",
        (
          "Run `pyenv which koru` and `pyenv rehash`, or call the intended "
          "virtualenv binary explicitly while debugging autopilot installs."
        ),
      ),
    ]
  return []


def check_version_mismatch_issue(
  source_version: str | None, package_version: str | None
) -> list[ManagerIssue]:
  if source_version and package_version and source_version != package_version:
    return [
      ManagerIssue(
        "koru_version_mismatch",
        "warning",
        (
          f"Imported package version is {package_version}, "
          f"source pyproject is {source_version}."
        ),
        "Reinstall editable from the source checkout or use the matching virtualenv.",
      ),
    ]
  return []


# ---------------------------------------------------------------------------
# Daemon / plugin checks
# ---------------------------------------------------------------------------


def check_daemon_issues(daemon: dict[str, Any]) -> list[ManagerIssue]:
  if not daemon.get("running"):
    return [
      ManagerIssue(
        "daemon_not_running",
        "warning",
        "Autopilot daemon is not running for this socket.",
        "Start it with `koru autopilot daemon` or let `koru autonomous up` start it.",
      ),
    ]
  return []


def check_plugin_version_missing_issue(
  daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
  if daemon.get("running") and plugin.get("connected") and not plugin.get("connected_version"):
    return [
      ManagerIssue(
        "plugin_version_missing",
        "warning",
        f"Connected {ide} plugin did not report a version.",
        (
          "Reload the IDE window after installing the current VSIX, "
          "then reconnect autopilot."
        ),
      ),
    ]
  return []


def check_plugin_build_missing_issue(
  daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
  if (
    daemon.get("running")
    and plugin.get("connected")
    and plugin.get("expected_build_sha")
    and not plugin.get("connected_build_sha")
  ):
    return [
      ManagerIssue(
        "plugin_build_missing",
        "warning",
        f"Connected {ide} plugin did not report a VSIX build hash.",
        (
          "Rebuild/reinstall the current VSIX, reload the IDE window, "
          "then reconnect autopilot."
        ),
      ),
    ]
  return []


def check_plugin_installed_version_mismatch_issue(
  plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
  installed_version = plugin.get("installed_version")
  expected_version = plugin.get("expected_version")
  if installed_version and expected_version and installed_version != expected_version:
    return [
      ManagerIssue(
        "plugin_installed_version_mismatch",
        "error",
        (
          f"Installed {ide} extension is {installed_version}, "
          f"but the source VSIX/package is {expected_version}."
        ),
        f"Run `koru autopilot manage --ide {ide} --fix`.",
      ),
    ]
  return []


def check_plugin_installed_ok_but_not_connected_issue(
  daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
  if plugin.get("connected"):
    return []
  installed_version = plugin.get("installed_version")
  expected_version = plugin.get("expected_version")
  installed_matches_expected = (
    bool(installed_version) and bool(expected_version) and installed_version == expected_version
  )
  if not installed_matches_expected:
    return []
  fix = (
    f"Start the daemon with `KORU_AUTOPILOT_INSTANCE={ide} koru autopilot daemon`, "
    "reload the IDE window, then run `koru: Connect autopilot daemon`."
  )
  if not daemon.get("running"):
    fix = (
      "Let `koru autonomous up` start the daemon, or start it manually with "
      f"`KORU_AUTOPILOT_INSTANCE={ide} koru autopilot daemon`; then reload the IDE "
      "window and run `koru: Connect autopilot daemon`."
    )
  return [
    ManagerIssue(
      "plugin_installed_ok_but_not_connected",
      "info",
      (
        f"{ide} extension is installed at the expected version "
        f"({installed_version}), but no live plugin is connected to this daemon."
      ),
      fix,
    ),
  ]


def check_plugin_live_host_stale_issue(
  daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
  installed_version = plugin.get("installed_version")
  expected_version = plugin.get("expected_version")
  if not _plugin_install_matches_expected(daemon, installed_version, expected_version):
    return []
  if _plugin_live_connection_matches_expected(plugin):
    return []
  rejected = _stale_rejected_plugins(daemon, ide, expected_version)
  if not rejected:
    return []
  return [_plugin_live_host_stale_issue(ide, str(installed_version), rejected)]


def _plugin_install_matches_expected(
  daemon: dict[str, Any],
  installed_version: Any,
  expected_version: Any,
) -> bool:
  return bool(daemon.get("running") and installed_version and installed_version == expected_version)


def _plugin_live_connection_matches_expected(plugin: dict[str, Any]) -> bool:
  connected_version = str(plugin.get("connected_version") or "").strip()
  expected_version = str(plugin.get("expected_version") or "").strip()
  if not connected_version or not expected_version or connected_version != expected_version:
    return False
  expected_build = str(plugin.get("expected_build_sha") or "").strip()
  if not expected_build:
    return True
  connected_build = str(plugin.get("connected_build_sha") or "").strip()
  return bool(connected_build and connected_build == expected_build)


def _stale_rejected_plugins(
  daemon: dict[str, Any],
  ide: str,
  expected_version: Any,
) -> list[dict[str, Any]]:
  return [
    row
    for row in daemon.get("rejected_plugins", [])
    if isinstance(row, dict)
    and row.get("ide") == ide
    and _is_stale_rejected_plugin(row, expected_version)
  ]


def _is_stale_rejected_plugin(row: dict[str, Any], expected_version: Any) -> bool:
  version = row.get("version")
  return bool(
    (version and version != expected_version)
    or (
      version == expected_version
      and row.get("expected_build_sha")
      and row.get("build_sha") != row.get("expected_build_sha")
    )
  )


def _plugin_live_host_stale_issue(
  ide: str,
  installed_version: str,
  rejected: list[dict[str, Any]],
) -> ManagerIssue:
  versions = ", ".join(sorted({str(row.get("version")) for row in rejected if row.get("version")}))
  builds = ", ".join(sorted({str(row.get("build_sha") or "-") for row in rejected}))
  return ManagerIssue(
    "plugin_live_host_stale",
    "error",
    (
      f"{ide} extension is installed at {installed_version}, but the live IDE "
      f"extension host is still reconnecting with stale version/build(s): "
      f"versions={versions or '-'} builds={builds or '-'}."
    ),
    (
      "Reload the IDE window with `Developer: Reload Window`, then run "
      "`koru: Connect autopilot daemon`. If stale reconnects continue, fully "
      "close that IDE window and open the project again."
    ),
  )


# ---------------------------------------------------------------------------
# Plugin debug-log scanning
# ---------------------------------------------------------------------------


def plugin_debug_log_path() -> Path:
  return Path(os.environ.get("KORU_PLUGIN_DEBUG_LOG", "/tmp/koru-plugin-debug.log"))


def recent_socket_candidate_mismatch(
  ide: str,
  expected_socket: Path,
) -> dict[str, Any] | None:
  try:
    lines = plugin_debug_log_path().read_text(encoding="utf-8").splitlines()[-200:]
  except OSError:
    return None

  expected = str(expected_socket)
  for line in reversed(lines):
    if "CONNECT_CANDIDATES" not in line:
      continue
    _, _, payload = line.partition("CONNECT_CANDIDATES")
    try:
      data = json.loads(payload.strip())
    except json.JSONDecodeError:
      continue
    if data.get("ide") != ide:
      continue
    candidates = [str(item) for item in data.get("candidates", []) if isinstance(item, str)]
    override = str(data.get("override") or "")
    if expected not in candidates:
      return {"override": override, "candidates": candidates}
  return None


def check_plugin_socket_candidate_mismatch_issue(
  daemon: dict[str, Any], plugin: dict[str, Any], ide: str, socket_path: Path
) -> list[ManagerIssue]:
  if not daemon.get("running") or plugin.get("connected"):
    return []
  installed_version = plugin.get("installed_version")
  expected_version = plugin.get("expected_version")
  if not installed_version or installed_version != expected_version:
    return []

  mismatch = recent_socket_candidate_mismatch(ide, socket_path)
  if not mismatch:
    return []

  candidates = ", ".join(mismatch["candidates"]) or "<empty>"
  override = mismatch["override"] or "<unset>"
  return [
    ManagerIssue(
      "plugin_socket_candidate_mismatch",
      "error",
      (
        f"{ide} extension is installed at {installed_version}, but the live "
        f"extension host is probing socket candidate(s) {candidates} instead "
        f"of {socket_path} (override={override})."
      ),
      (
        "Reload the IDE window with `Developer: Reload Window` or run "
        "`Developer: Restart Extension Host`, then run "
        "`koru: Connect autopilot daemon`."
      ),
    ),
  ]


def check_plugin_version_mismatch_issue(
  daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
  connected_version = plugin.get("connected_version")
  expected_version = plugin.get("expected_version")
  if (
    daemon.get("running")
    and plugin.get("connected")
    and connected_version
    and expected_version
    and connected_version != expected_version
  ):
    return [
      ManagerIssue(
        "plugin_version_mismatch",
        "error",
        (
          f"Connected {ide} plugin is {connected_version}, "
          f"but the source VSIX/package is {expected_version}."
        ),
        (
          f"Run `koru autopilot manage --ide {ide} --fix`, fully reload the IDE "
          "window, then run `koru: Connect autopilot daemon`."
        ),
      ),
    ]
  return []


def check_plugin_build_mismatch_issue(
  daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
  connected_build = plugin.get("connected_build_sha")
  expected_build = plugin.get("expected_build_sha")
  if (
    daemon.get("running")
    and plugin.get("connected")
    and connected_build
    and expected_build
    and connected_build != expected_build
  ):
    return [
      ManagerIssue(
        "plugin_build_mismatch",
        "error",
        (
          f"Connected {ide} plugin build is {connected_build}, "
          f"but the source VSIX/package build is {expected_build}."
        ),
        (
          f"Run `koru autopilot manage --ide {ide} --fix`, fully reload the IDE "
          "window, then run `koru: Connect autopilot daemon`."
        ),
      ),
    ]
  return []


def check_plugin_not_connected_issue(
  daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
  if daemon.get("running") and not plugin.get("connected"):
    fix = (
      "Reload the IDE window with `Developer: Reload Window`, then run "
      "`koru: Connect autopilot daemon`."
    )
    return [
      ManagerIssue(
        "plugin_not_connected",
        "error",
        f"Autopilot daemon is running, but no plugin is connected for ide={ide}.",
        fix,
      ),
    ]
  return []


__all__ = [
  "ManagerIssue",
  "is_pyenv_shim",
  "plugin_debug_log_path",
  "recent_socket_candidate_mismatch",
  "check_koru_path_issues",
  "check_pyenv_shim_issue",
  "check_version_mismatch_issue",
  "check_daemon_issues",
  "check_plugin_version_missing_issue",
  "check_plugin_build_missing_issue",
  "check_plugin_installed_version_mismatch_issue",
  "check_plugin_installed_ok_but_not_connected_issue",
  "check_plugin_live_host_stale_issue",
  "check_plugin_socket_candidate_mismatch_issue",
  "check_plugin_version_mismatch_issue",
  "check_plugin_build_mismatch_issue",
  "check_plugin_not_connected_issue",
]
