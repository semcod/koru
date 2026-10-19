"""koru.queue stays a lower layer (semcod/koru#731).

The helpers the queue path needs live in neutral modules; the autonomy modules
re-export them so existing imports keep working.
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "koru"
LOWER_LAYER_CALLERS = (
    "activity_log.py",
    "bounded_contexts/planfile_queue/application.py",
    "task_model_policy.py",
    "ticket_logs.py",
    "drive_budget.py",
)


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
    return found


def test_lower_layer_callers_do_not_import_the_autonomy_layer():
    for rel in LOWER_LAYER_CALLERS:
        offenders = sorted(
            m for m in imported_modules(SRC / rel) if m == "koru.autonomy" or m.startswith("koru.autonomy.")
        )
        assert not offenders, f"{rel} imports {offenders}"


def test_old_import_paths_still_resolve_to_the_moved_helpers():
    from koru import drive_budget, ticket_logs
    from koru.autonomy import cycle_trace
    from koru.autonomy.verification_engine import budget, reserve_drive_attempt

    assert cycle_trace.find_ticket_dir is ticket_logs.find_ticket_dir
    assert cycle_trace.append_queue_ticket_markdown_log is ticket_logs.append_queue_ticket_markdown_log
    assert cycle_trace.append_ticket_markdown_log is ticket_logs.append_ticket_markdown_log
    assert budget.reserve_drive_attempt is drive_budget.reserve_drive_attempt
    assert reserve_drive_attempt is drive_budget.reserve_drive_attempt


def test_drive_budget_reserves_attempts_up_to_the_limit(tmp_path):
    from koru.drive_budget import reserve_drive_attempt

    assert [reserve_drive_attempt(tmp_path, "ticket-1", limit=2) for _ in range(3)] == [True, True, False]
