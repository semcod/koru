"""CLI fake extension for executor/lifecycle unit tests with runnable fixtures.

These older tests supply ticket-list fixtures already assumed runnable. Model
Planfile's added read-only readiness response without changing their lifecycle
call assertions. Admission policy itself is tested with real native Planfile
and explicit reports in test_queue_admission; those tests do not use this fake.
"""
import json
from functools import wraps
from types import SimpleNamespace


def runnable_fixture_report(fake):
    tickets = []

    @wraps(fake)
    def run(command, project):
        nonlocal tickets
        args = command[command.index("ticket"):] if "ticket" in command else command
        if args[:3] == ["ticket", "next", "--debug"]:
            return SimpleNamespace(returncode=0, stderr="", stdout=json.dumps({
                "servable": [row["id"] for row in tickets if isinstance(row, dict) and row.get("id")],
                "skipped": [],
            }))
        result = fake(command, project)
        if args[:2] == ["ticket", "list"] and result.returncode == 0:
            try:
                payload = json.loads(result.stdout)
                tickets = [payload] if isinstance(payload, dict) else (payload or [])
            except (ValueError, TypeError):
                tickets = []
        return result

    return run
