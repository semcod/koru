"""Koru loop automation package."""

from koru.bootstrap import (
    ImportReport,
    ValidationError,
    import_flat_pipeline,
    load_flat_pipeline,
    materialize_to_planfile,
    validate_flat_pipeline,
)
from koru.context import build_context, render_markdown_handoff
from koru.doctor import Check, DoctorReport, run_diagnostics
from koru.init import InitReport, init_project, refresh_init_agent_lane, resolve_project_agent_lane
from koru.loop import LoopReport, RunRecord, discover_repositories, run_closed_loop
from koru.planfile_queue import (
    LlmRunResult,
    QueueLoopResult,
    QueueRunResult,
    run_next_planfile_task,
    run_planfile_queue_loop,
)
from koru.policy import Policy, load_policy, policy_path, policy_violations
from koru.run_log import RunLogWriter, open_run_log, open_run_log_eagerly
from koru.runtime import (
    ensure_runs_dir,
    new_run_id,
    planfile_dir,
    runs_dir,
    runtime_dir,
)

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
