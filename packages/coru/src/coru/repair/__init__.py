"""Coru bridge repair — CQRS commands, event-sourced history, registry-backed fixes."""

from coru.repair.commands import ExecuteRepairActionCommand, RecordDiagnosisCommand, RunRepairSessionCommand
from coru.repair.diagnostics import (
    collect_problems_from_console_logs,
    collect_problems_from_drive_result,
    collect_problems_from_manage_report,
    collect_problems_from_status,
    dedupe_problems,
)
from coru.repair.domain import RepairAttempt, RepairCaseSummary, RepairPlan, RepairProblem, RepairStepDef
from coru.repair.events import RepairEvent, aggregate_id_for
from coru.repair.pipeline import format_repair_lines, manual_vsix_unpack, plugin_build_aligned, run_repair_pipeline
from coru.repair.projector import format_case_llm, format_history_llm, project_repair_cases
from coru.repair.query import RepairHistoryQuery, problems_to_payload
from coru.repair.registry import REPAIR_REGISTRY, playbook_for_codes, registry_step, registry_steps_for_code
from coru.repair.service import RepairService, run_repair_with_events
from coru.repair.store import RepairEventStore

__all__ = [
    "ExecuteRepairActionCommand",
    "REPAIR_REGISTRY",
    "RecordDiagnosisCommand",
    "RepairAttempt",
    "RepairCaseSummary",
    "RepairEvent",
    "RepairEventStore",
    "RepairHistoryQuery",
    "RepairPlan",
    "RepairProblem",
    "RepairService",
    "RepairStepDef",
    "RunRepairSessionCommand",
    "aggregate_id_for",
    "collect_problems_from_console_logs",
    "collect_problems_from_drive_result",
    "collect_problems_from_manage_report",
    "collect_problems_from_status",
    "dedupe_problems",
    "format_case_llm",
    "format_history_llm",
    "format_repair_lines",
    "manual_vsix_unpack",
    "playbook_for_codes",
    "plugin_build_aligned",
    "problems_to_payload",
    "project_repair_cases",
    "registry_step",
    "registry_steps_for_code",
    "run_repair_pipeline",
    "run_repair_with_events",
]
