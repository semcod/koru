from __future__ import annotations

from pathlib import Path

from koru.bounded_contexts.repairs.application import RepairCommandService, RepairQueryService
from koru.bounded_contexts.repairs.commands import (
    RecordRepairAttemptCommand,
    RecordRepairDiagnosticCommand,
)
from koru.bounded_contexts.repairs.events import (
    REPAIR_ATTEMPT_RECORDED,
    REPAIR_CONTEXT,
    REPAIR_DIAGNOSTIC_RECORDED,
)
from koru.bounded_contexts.repairs.queries import LoadRepairHistoryQuery
from koru.bounded_contexts.repairs.read_model import format_repair_history_for_llm
from koru.cqrs import runtime_for_project


def test_repair_history_persists_diagnostics_and_attempts(tmp_path: Path) -> None:
    runtime = runtime_for_project(tmp_path)
    commands = RepairCommandService(runtime)
    subject = f"ide-bridge:vscodium:{tmp_path}"

    commands.record_diagnostic(
        RecordRepairDiagnosticCommand(
            subject=subject,
            repair_kind="ide_bridge",
            project=str(tmp_path),
            summary="ide=vscodium ready=False primary=vscodium.plugin.build_mismatch",
            status={"ready": False, "plugins_compatible": False},
            hypotheses=[
                {
                    "id": "vscodium.plugin.build_mismatch",
                    "confidence": 95,
                    "evidence": "old-build != new-build",
                    "remediation": "Developer: Reload Window",
                },
            ],
        )
    )
    commands.record_attempt(
        RecordRepairAttemptCommand(
            subject=subject,
            repair_kind="ide_bridge",
            project=str(tmp_path),
            attempted=True,
            ok=False,
            actions=["safe autofix requested; no safe automatic changes were available"],
            summary="ide=vscodium autofix ok=False",
        )
    )

    persisted = runtime_for_project(tmp_path)
    history = RepairQueryService(persisted).history(
        LoadRepairHistoryQuery(subject=subject, limit=10)
    )

    assert [entry.event_type for entry in history] == [
        REPAIR_DIAGNOSTIC_RECORDED,
        REPAIR_ATTEMPT_RECORDED,
    ]
    assert persisted.store.all_events(context=REPAIR_CONTEXT)
    rendered = format_repair_history_for_llm(history)
    assert "vscodium.plugin.build_mismatch" in rendered
    assert "old-build != new-build" in rendered
    assert "safe autofix requested" in rendered
