"""Koru loop automation package."""

from __future__ import annotations

from importlib import import_module

_EXPORTS: dict[str, tuple[str, str]] = {
    "Check": ("koru.doctor", "Check"),
    "DoctorReport": ("koru.doctor", "DoctorReport"),
    "ImportReport": ("koru.bootstrap", "ImportReport"),
    "InitReport": ("koru.init", "InitReport"),
    "LlmRunResult": ("koru.planfile_queue", "LlmRunResult"),
    "LoopReport": ("koru.loop", "LoopReport"),
    "Policy": ("koru.policy", "Policy"),
    "QueueLoopResult": ("koru.planfile_queue", "QueueLoopResult"),
    "QueueRunResult": ("koru.planfile_queue", "QueueRunResult"),
    "RunLogWriter": ("koru.run_log", "RunLogWriter"),
    "RunRecord": ("koru.loop", "RunRecord"),
    "ValidationError": ("koru.bootstrap", "ValidationError"),
    "build_context": ("koru.context", "build_context"),
    "discover_repositories": ("koru.loop", "discover_repositories"),
    "ensure_runs_dir": ("koru.runtime", "ensure_runs_dir"),
    "import_flat_pipeline": ("koru.bootstrap", "import_flat_pipeline"),
    "init_project": ("koru.init", "init_project"),
    "refresh_init_agent_lane": ("koru.init", "refresh_init_agent_lane"),
    "resolve_project_agent_lane": ("koru.init", "resolve_project_agent_lane"),
    "load_flat_pipeline": ("koru.bootstrap", "load_flat_pipeline"),
    "load_policy": ("koru.policy", "load_policy"),
    "materialize_to_planfile": ("koru.bootstrap", "materialize_to_planfile"),
    "new_run_id": ("koru.runtime", "new_run_id"),
    "open_run_log": ("koru.run_log", "open_run_log"),
    "open_run_log_eagerly": ("koru.run_log", "open_run_log_eagerly"),
    "planfile_dir": ("koru.runtime", "planfile_dir"),
    "policy_path": ("koru.policy", "policy_path"),
    "policy_violations": ("koru.policy", "policy_violations"),
    "render_markdown_handoff": ("koru.context", "render_markdown_handoff"),
    "run_diagnostics": ("koru.doctor", "run_diagnostics"),
    "run_closed_loop": ("koru.loop", "run_closed_loop"),
    "run_next_planfile_task": ("koru.planfile_queue", "run_next_planfile_task"),
    "run_planfile_queue_loop": ("koru.planfile_queue", "run_planfile_queue_loop"),
    "runs_dir": ("koru.runtime", "runs_dir"),
    "runtime_dir": ("koru.runtime", "runtime_dir"),
    "validate_flat_pipeline": ("koru.bootstrap", "validate_flat_pipeline"),
}


def __getattr__(name: str):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'koru' has no attribute {name!r}")
    module_name, attr_name = target
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS))

__all__ = [
    "Check",
    "DoctorReport",
    "ImportReport",
    "InitReport",
    "LlmRunResult",
    "LoopReport",
    "Policy",
    "QueueLoopResult",
    "QueueRunResult",
    "RunLogWriter",
    "RunRecord",
    "ValidationError",
    "build_context",
    "discover_repositories",
    "ensure_runs_dir",
    "import_flat_pipeline",
    "init_project",
    "refresh_init_agent_lane",
    "resolve_project_agent_lane",
    "load_flat_pipeline",
    "load_policy",
    "materialize_to_planfile",
    "new_run_id",
    "open_run_log",
    "open_run_log_eagerly",
    "planfile_dir",
    "policy_path",
    "policy_violations",
    "render_markdown_handoff",
    "run_diagnostics",
    "run_closed_loop",
    "run_next_planfile_task",
    "run_planfile_queue_loop",
    "runs_dir",
    "runtime_dir",
    "validate_flat_pipeline",
]
