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
    QueueLoopResult,
    QueueRunResult,
    run_next_planfile_task,
    run_planfile_queue_loop,
)

__all__ = [
    "ImportReport",
    "LoopReport",
    "QueueLoopResult",
    "QueueRunResult",
    "RunRecord",
    "ValidationError",
    "discover_repositories",
    "import_flat_pipeline",
    "load_flat_pipeline",
    "materialize_to_planfile",
    "run_closed_loop",
    "run_next_planfile_task",
    "run_planfile_queue_loop",
    "validate_flat_pipeline",
]
