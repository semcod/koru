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
from .runtime import (
    ensure_runs_dir,
    new_run_id,
    planfile_dir,
    runs_dir,
    runtime_dir,
)

__all__ = [
    "ImportReport",
    "LlmRunResult",
    "LoopReport",
    "QueueLoopResult",
    "QueueRunResult",
    "RunRecord",
    "ValidationError",
    "discover_repositories",
    "ensure_runs_dir",
    "import_flat_pipeline",
    "load_flat_pipeline",
    "materialize_to_planfile",
    "new_run_id",
    "planfile_dir",
    "run_closed_loop",
    "run_next_planfile_task",
    "run_planfile_queue_loop",
    "runs_dir",
    "runtime_dir",
    "validate_flat_pipeline",
]
