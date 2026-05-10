"""Koru loop automation package."""

from .bootstrap import (
    ImportReport,
    ValidationError,
    import_flat_pipeline,
    load_flat_pipeline,
    materialize_to_planfile,
    validate_flat_pipeline,
)
from .loop import LoopReport, RunRecord, discover_repositories, run_closed_loop
from .planfile_queue import (
    LlmRunResult,
    QueueLoopResult,
    QueueRunResult,
    run_next_planfile_task,
    run_planfile_queue_loop,
)
from .context import build_context, render_markdown_handoff
from .init import InitReport, init_project
from .policy import Policy, load_policy, policy_path, policy_violations
from .run_log import RunLogWriter, open_run_log, open_run_log_eagerly
from .runtime import (
    ensure_runs_dir,
    new_run_id,
    planfile_dir,
    runs_dir,
    runtime_dir,
)

__all__ = [
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
    "run_closed_loop",
    "run_next_planfile_task",
    "run_planfile_queue_loop",
    "runs_dir",
    "runtime_dir",
    "validate_flat_pipeline",
]
