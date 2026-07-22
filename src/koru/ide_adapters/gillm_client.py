"""In-process Gillm IDE client for keyboard/profile GUI fallback."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gillm.adapters.koru import drive_payload_to_action_plan, koru_drive_to_payload
from gillm.drivers.composite import CompositeGuiDriver
from gillm.drivers.dry_run import DryRunGuiDriver
from gillm.recovery import diagnose_drive_reply


@dataclass
class GillmIDEControlClient:
    """Expose Gillm's typed driver through Koru's IDEControlClient protocol."""

    driver: CompositeGuiDriver | DryRunGuiDriver

    def is_running(self) -> bool:
        return True

    def drive(
        self,
        text: str,
        *,
        submit: bool = True,
        ide: str = "auto",
        require_plugin: bool = False,
        strategy_hint: str | None = None,
    ) -> dict[str, Any]:
        del require_plugin, strategy_hint
        payload = koru_drive_to_payload(text=text, ide=ide, submit=submit)
        plan = drive_payload_to_action_plan(payload)
        outcome = self.driver.execute(plan)
        action_result = outcome.to_dict()
        reply: dict[str, Any] = {
            "ok": action_result["ok"],
            "backend": action_result["backend"] or "gillm",
            "tool_id": plan.target.tool_id,
            "message": action_result["reason"] or "",
            "reason": action_result["reason"] or "",
            "intent": action_result["intent"],
            "result_schema": action_result["schema"],
            "result_hash": action_result["result_hash"],
            "action_result": action_result,
            "diagnostics": {
                "recovery": action_result["recovery"],
                "evidence": action_result["evidence"],
                "environment": outcome.steps[-1].backend if outcome.steps else None,
            },
        }
        if not outcome.ok:
            ctx = diagnose_drive_reply(reply)
            reply["recovery"] = ctx.recovery
            reply["failure_kind"] = ctx.kind
            reply["retryable"] = ctx.retryable
        return reply

    def status(self) -> dict[str, Any]:
        status = self.driver.probe()
        return {"ok": True, "backend": "gillm", "driver": status.to_dict()}

    def shutdown(self) -> dict[str, Any]:
        return {"ok": True, "backend": "gillm"}


def build_gillm_ide_client(
    *,
    project: Path | None = None,
    dry_run: bool = False,
) -> GillmIDEControlClient:
    raw_dry_run = os.environ.get("KORU_OS_INJECTOR_DRY_RUN", "").strip().lower()
    effective_dry_run = dry_run or raw_dry_run in {
        "1",
        "true",
        "yes",
        "on",
    }
    if effective_dry_run:
        return GillmIDEControlClient(driver=DryRunGuiDriver())
    return GillmIDEControlClient(driver=CompositeGuiDriver(project=project))
