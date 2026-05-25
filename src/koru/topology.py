"""Project-level topology & pipelines — what runs, in what role, and whether it is enabled.

This module is the single source of truth for the on/off state of the
semcod components (regix, testql, wup, redup, sumr, vallm, planfile,
koru, …) and the higher-level *pipelines* that compose them
(idle-diagnostics, gate:regix, gate:testql, autoloop:queue, scan:on-change, …).

State is persisted to ``.koru/topology.yaml`` inside the project. The
file is optional: when absent, :func:`load_topology` returns the
built-in defaults merged with live detection from :mod:`koru.semcod_tools`.

Public API
----------
- :func:`load_topology` — return merged topology (defaults + saved overrides + detection).
- :func:`save_topology` — write a topology dict back to ``.koru/topology.yaml``.
- :func:`set_component_enabled` / :func:`set_pipeline_enabled` — convenience mutators.
- :func:`is_component_enabled` / :func:`is_pipeline_enabled` — read-only predicates.
- :func:`enabled_components_for_pipeline` — list of enabled component ids in a pipeline.
"""


from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from koru.semcod_tools import detect_semcod_tools

SCHEMA_VERSION = "1"
TOPOLOGY_FILENAME = "topology.yaml"


# ---------------------------------------------------------------------------
# Built-in defaults
# ---------------------------------------------------------------------------

# Each component maps to a semcod_tools id when applicable. ``kind`` is a
# free-form label rendered in the dashboard ("cli" / "library" / "service").
_DEFAULT_COMPONENTS: dict[str, dict[str, Any]] = {
    "regix": {"enabled": True, "kind": "cli", "role": "regression metrics gate"},
    "testql": {
        "enabled": True,
        "kind": "cli",
        "role": "behavioural HTTP probes / autonomy loop",
    },
    "wup": {
        "enabled": True,
        "kind": "cli",
        "role": "intelligent file watcher / on-change router",
    },
    "redup": {
        "enabled": True,
        "kind": "cli",
        "role": "duplicate / redundancy detection",
    },
    "redsl": {
        "enabled": False,
        "kind": "cli",
        "role": "redundancy slicer (semantic dedup)",
    },
    "sumr": {"enabled": False, "kind": "cli", "role": "weekly project summary refresh"},
    "vallm": {
        "enabled": False,
        "kind": "cli",
        "role": "LLM-as-judge semantic validation",
    },
    "goal": {"enabled": False, "kind": "cli", "role": "strategic goal alignment"},
    "pfix": {"enabled": False, "kind": "cli", "role": "self-healing Python auto-fix"},
    "costs": {"enabled": False, "kind": "cli", "role": "AI cost tracking + badge"},
    "rebuild": {
        "enabled": False,
        "kind": "cli",
        "role": "git history walker / quality replay",
    },
    "planfile": {
        "enabled": True,
        "kind": "cli",
        "role": "ticket lifecycle (source of truth)",
    },
    "koru": {
        "enabled": True,
        "kind": "cli",
        "role": "closed-loop automation orchestrator",
    },
}

# Pipelines are constellations of components triggered together. ``trigger``
# is informational ("manual", "autoloop-cycle", "on-commit", "on-merge", ...).
_DEFAULT_PIPELINES: dict[str, dict[str, Any]] = {
    "idle-diagnostics": {
        "enabled": True,
        "description": "Run quality gates when the queue drains to idle",
        "components": ["regix", "wup", "redup", "testql", "redsl", "sumr"],
        "trigger": "autoloop-cycle",
    },
    "autoloop:queue": {
        "enabled": True,
        "description": "Continuous intake + execution loop (scripts/koru-autoloop.sh)",
        "components": ["koru", "planfile"],
        "trigger": "manual",
    },
    "scan:on-change": {
        "enabled": True,
        "description": "Per-cycle `koru scan --apply` (auto-creates tickets from repo signals)",
        "components": ["koru"],
        "trigger": "autoloop-cycle",
    },
    "gate:regix": {
        "enabled": True,
        "description": "Regression metrics gate (`task quality:regix`)",
        "components": ["regix"],
        "trigger": "on-change",
    },
    "gate:testql": {
        "enabled": True,
        "description": "TestQL probe gate",
        "components": ["testql"],
        "trigger": "on-change",
    },
    "gate:wup": {
        "enabled": True,
        "description": "wup watcher status gate",
        "components": ["wup"],
        "trigger": "on-change",
    },
    "gate:redup": {
        "enabled": True,
        "description": "Duplicate-detection gate (`task quality:redup:check`)",
        "components": ["redup"],
        "trigger": "on-change",
    },
    "gate:sumr": {
        "enabled": False,
        "description": "SUMR.md staleness gate (`task quality:sumr:status`)",
        "components": ["sumr"],
        "trigger": "scheduled",
    },
    "autopilot:drive": {
        "enabled": True,
        "description": "Per-cycle autopilot drive ping to IDE/agent",
        "components": ["koru"],
        "trigger": "autoloop-cycle",
    },
}


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def topology_path(project: Path) -> Path:
    """Path to ``.koru/topology.yaml`` inside *project* (not guaranteed to exist)."""
    return project.resolve() / ".koru" / TOPOLOGY_FILENAME


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return data if isinstance(data, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def _saved_component_ids(saved_components: object) -> list[str]:
    ids = list(_DEFAULT_COMPONENTS.keys())
    if isinstance(saved_components, dict):
        for extra_id in saved_components:
            if extra_id not in ids:
                ids.append(extra_id)
    return ids


def _component_defaults(cid: str, override: object) -> dict[str, Any]:
    defaults = dict(_DEFAULT_COMPONENTS.get(cid, {"enabled": True, "kind": "cli", "role": ""}))
    if isinstance(override, dict):
        defaults.update({k: v for k, v in override.items() if k in {"enabled", "kind", "role"}})
    defaults["id"] = cid
    return defaults


def _apply_detected_tool(component: dict[str, Any], detected_tool: Any | None) -> None:
    if detected_tool is not None:
        component["available"] = bool(detected_tool.available)
        component["via"] = detected_tool.via
        component["command"] = detected_tool.command
        component["config_present"] = bool(detected_tool.config_present)
        component["command_hint"] = detected_tool.command_hint
        return
    component.setdefault("available", False)
    component.setdefault("via", "missing")
    component.setdefault("command", None)
    component.setdefault("config_present", False)
    component.setdefault("command_hint", "")


def _merge_components(saved: dict[str, Any], detected: list[Any]) -> dict[str, dict[str, Any]]:
    """Return components dict with `enabled` merged from saved overrides and
    `available` / `via` / `command` / `config_present` filled from live
    detection. Components present in `saved` but not in defaults are kept
    (forward-compat for future tools).
    """
    detected_by_id = {tool.id: tool for tool in detected}
    merged: dict[str, dict[str, Any]] = {}
    saved_components = saved.get("components") or {}
    for cid in _saved_component_ids(saved_components):
        override = saved_components.get(cid) if isinstance(saved_components, dict) else None
        component = _component_defaults(cid, override)
        _apply_detected_tool(component, detected_by_id.get(cid))
        merged[cid] = component
    return merged


def _merge_pipelines(saved: dict[str, Any]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    saved_pipelines = saved.get("pipelines") or {}
    if not isinstance(saved_pipelines, dict):
        saved_pipelines = {}
    ids = list(_DEFAULT_PIPELINES.keys())
    for extra_id in saved_pipelines:
        if extra_id not in ids:
            ids.append(extra_id)
    for pid in ids:
        defaults = dict(
            _DEFAULT_PIPELINES.get(
                pid,
                {
                    "enabled": True,
                    "description": "",
                    "components": [],
                    "trigger": "manual",
                },
            ),
        )
        override = saved_pipelines.get(pid)
        if isinstance(override, dict):
            for key in ("enabled", "description", "components", "trigger"):
                if key in override:
                    defaults[key] = override[key]
        defaults["id"] = pid
        merged[pid] = defaults
    return merged


def load_topology(project: Path) -> dict[str, Any]:
    """Return merged topology: defaults + ``.koru/topology.yaml`` overrides + detection.

    The returned dict has shape::

        {
          "schema_version": "1",
          "project": "<absolute path>",
          "components": {id: {enabled, kind, role, available, via, ...}, ...},
          "pipelines":  {id: {enabled, description, components, trigger}, ...},
          "path": "<absolute path to topology.yaml>",
          "exists": bool,
        }
    """
    project = project.resolve()
    path = topology_path(project)
    saved = _read_yaml(path)
    detected = detect_semcod_tools(project)
    return {
        "schema_version": SCHEMA_VERSION,
        "project": str(project),
        "components": _merge_components(saved, detected),
        "pipelines": _merge_pipelines(saved),
        "path": str(path),
        "exists": path.is_file(),
    }


def _strip_to_persisted(topology: dict[str, Any]) -> dict[str, Any]:
    """Return only the user-controllable bits (no detection cache)."""
    components_out: dict[str, dict[str, Any]] = {}
    for cid, comp in (topology.get("components") or {}).items():
        if not isinstance(comp, dict):
            continue
        components_out[cid] = {
            "enabled": bool(comp.get("enabled", True)),
            "kind": comp.get("kind", "cli"),
            "role": comp.get("role", ""),
        }
    pipelines_out: dict[str, dict[str, Any]] = {}
    for pid, pipe in (topology.get("pipelines") or {}).items():
        if not isinstance(pipe, dict):
            continue
        pipelines_out[pid] = {
            "enabled": bool(pipe.get("enabled", True)),
            "description": pipe.get("description", ""),
            "components": list(pipe.get("components") or []),
            "trigger": pipe.get("trigger", "manual"),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "components": components_out,
        "pipelines": pipelines_out,
    }


def save_topology(project: Path, topology: dict[str, Any]) -> Path:
    """Persist *topology* to ``.koru/topology.yaml`` and return the path."""
    project = project.resolve()
    path = topology_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _strip_to_persisted(topology)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=True, default_flow_style=False, allow_unicode=True)
    return path


# ---------------------------------------------------------------------------
# Predicates / mutators
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToggleResult:
    """Outcome of a single enable/disable mutation."""

    id: str
    kind: str  # "component" | "pipeline"
    previous: bool | None
    current: bool
    found: bool


def _toggle(
    topology: dict[str, Any],
    section: str,
    target_id: str,
    enabled: bool,
) -> ToggleResult:
    bucket = topology.setdefault(section, {})
    entry = bucket.get(target_id)
    if not isinstance(entry, dict):
        return ToggleResult(
            id=target_id,
            kind=section.rstrip("s"),
            previous=None,
            current=enabled,
            found=False,
        )
    previous = bool(entry.get("enabled", True))
    entry["enabled"] = bool(enabled)
    return ToggleResult(
        id=target_id,
        kind=section.rstrip("s"),
        previous=previous,
        current=bool(enabled),
        found=True,
    )


def set_component_enabled(
    topology: dict[str, Any],
    component_id: str,
    enabled: bool,
) -> ToggleResult:
    return _toggle(topology, "components", component_id, enabled)


def set_pipeline_enabled(
    topology: dict[str, Any],
    pipeline_id: str,
    enabled: bool,
) -> ToggleResult:
    return _toggle(topology, "pipelines", pipeline_id, enabled)


def is_component_enabled(project: Path, component_id: str) -> bool:
    """True when *component_id* is enabled in the project's topology (defaults if unset)."""
    topo = load_topology(project)
    comp = (topo.get("components") or {}).get(component_id)
    if not isinstance(comp, dict):
        return False
    return bool(comp.get("enabled", True))


def is_pipeline_enabled(project: Path, pipeline_id: str) -> bool:
    topo = load_topology(project)
    pipe = (topo.get("pipelines") or {}).get(pipeline_id)
    if not isinstance(pipe, dict):
        return False
    return bool(pipe.get("enabled", True))


def enabled_components_for_pipeline(project: Path, pipeline_id: str) -> list[str]:
    """Return component ids that are enabled AND belong to *pipeline_id*.

    Returns an empty list when the pipeline itself is disabled or absent.
    """
    topo = load_topology(project)
    pipe = (topo.get("pipelines") or {}).get(pipeline_id)
    if not isinstance(pipe, dict) or not pipe.get("enabled", True):
        return []
    components = topo.get("components") or {}
    result: list[str] = []
    for cid in pipe.get("components") or []:
        comp = components.get(cid)
        if isinstance(comp, dict) and comp.get("enabled", True):
            result.append(cid)
    return result


# ---------------------------------------------------------------------------
# Public defaults (for tests / introspection)
# ---------------------------------------------------------------------------


def default_component_ids() -> list[str]:
    return list(_DEFAULT_COMPONENTS.keys())


def default_pipeline_ids() -> list[str]:
    return list(_DEFAULT_PIPELINES.keys())
