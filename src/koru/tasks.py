from pathlib import Path
from typing import Any

from koru.task_intake import _create_nl_task_impl
from koru.task_io import _read_config, _read_sprint
from koru.task_models import CreatedTask


def create_nl_task(
    project: Path,
    text: str,
    *,
    sprint: str = "current",
    queue_name: str | None = None,
    priority: str = "normal",
    scaffold: dict[str, Any] | None = None,
) -> CreatedTask:
    """Create a planfile ticket from a normal-language sentence."""
    from koru.bounded_contexts.tasks.application import TaskCommandService
    from koru.bounded_contexts.tasks.commands import CreateNlTaskCommand
    from koru.cqrs import runtime_for_project

    return TaskCommandService(runtime=runtime_for_project(project)).create_nl_task(
        CreateNlTaskCommand(
            project=project,
            text=text,
            sprint=sprint,
            queue_name=queue_name,
            priority=priority,
            scaffold=scaffold,
        )
    )
