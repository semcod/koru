"""In-process Gillm IDE client for keyboard/profile GUI fallback."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from gillm.adapters.koru import drive_payload_to_action_plan, koru_drive_to_payload
    from gillm.contracts.driver import ActionPlan
    from gillm.drivers.composite import CompositeGuiDriver
    from gillm.drivers.dry_run import DryRunGuiDriver
    from gillm.recovery.diagnose import diagnose_drive_reply
except ImportError:
    from koru.ide_adapters.gillm_recovery import diagnose_drive_reply

    DEFAULT_STRATEGY = (
        "plugin_bridge",
        "command_palette",
        "clipboard_paste",
        "keyboard_fallback",
    )

    @dataclass(frozen=True)
    class WindowTarget:
        hints: tuple[str, ...] = ()
        tool_id: str = "default"
        profile_id: str | None = None

    @dataclass
    class ActionPlan:  # type: ignore[no-redef]
        intent: str
        target: WindowTarget = field(default_factory=WindowTarget)
        steps: list[dict[str, Any]] = field(default_factory=list)
        validation: dict[str, Any] = field(default_factory=dict)

        @classmethod
        def chat_inject_and_submit(
            cls,
            *,
            text: str,
            tool_id: str = "default",
            submit: bool = True,
        ) -> ActionPlan:
            steps: list[dict[str, Any]] = [
                {"action": "focus", "target": tool_id},
                {"action": "type_text", "text": text},
            ]
            if submit:
                steps.append({"action": "submit", "tool_id": tool_id})
            return cls(
                intent="gui.chat.inject_and_submit",
                target=WindowTarget(hints=(tool_id,), tool_id=tool_id),
                steps=steps,
                validation={"require_empty_input": submit},
            )

    @dataclass
    class DriverStatus:
        session: str = "unknown"
        backends: dict[str, bool] = field(default_factory=dict)
        profile_loaded: bool = False
        dry_run: bool = False

        def to_dict(self) -> dict[str, Any]:
            return {
                "session": self.session,
                "backends": dict(self.backends),
                "profile_loaded": self.profile_loaded,
                "dry_run": self.dry_run,
            }

    @dataclass
    class ActionResult:
        ok: bool
        backend: str | None = None
        evidence: list[str] = field(default_factory=list)
        diagnostics: list[str] = field(default_factory=list)
        retryable: bool = False
        reason: str | None = None

    @dataclass
    class ExecutionOutcome:
        ok: bool
        intent: str
        backend: str | None = None
        evidence: list[str] = field(default_factory=list)
        diagnostics: list[str] = field(default_factory=list)
        recovery: list[str] = field(default_factory=list)
        retryable: bool = False
        reason: str | None = None
        steps: list[ActionResult] = field(default_factory=list)

    def koru_drive_to_payload(
        *,
        text: str,
        ide: str = "auto",
        submit: bool = True,
        prefer: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        tool_id = ide if ide and ide != "auto" else "default"
        return {
            "intent": "ide.chat.submit",
            "target": {"ide": tool_id, "lane": "default"},
            "input": {"text": text, "submit": submit},
            "strategy": {"prefer": list(prefer or DEFAULT_STRATEGY)},
            "validation": {
                "expect": [
                    "window_focused",
                    "text_submitted" if submit else "text_pasted",
                ],
            },
        }

    def drive_payload_to_action_plan(payload: dict[str, Any]) -> ActionPlan:
        target_raw = payload.get("target") if isinstance(payload.get("target"), dict) else {}
        input_raw = payload.get("input") if isinstance(payload.get("input"), dict) else {}
        strategy_raw = payload.get("strategy") if isinstance(payload.get("strategy"), dict) else {}
        validation = (
            payload.get("validation")
            if isinstance(payload.get("validation"), dict)
            else {}
        )
        tool_id = str(target_raw.get("ide") or target_raw.get("tool_id") or "default")
        hints = target_raw.get("window_hints") or target_raw.get("hints") or (tool_id,)
        if isinstance(hints, str):
            hints = (hints,)
        text = str(input_raw.get("text") or payload.get("text") or "")
        submit = bool(input_raw.get("submit", payload.get("submit", True)))
        prefer = strategy_raw.get("prefer") or DEFAULT_STRATEGY
        steps = _steps_from_prefer(prefer, text=text, submit=submit, tool_id=tool_id)
        return ActionPlan(
            intent=str(payload.get("intent") or "gui.chat.inject_and_submit"),
            target=WindowTarget(
                hints=tuple(str(h) for h in hints),
                tool_id=tool_id,
                profile_id=(
                    str(target_raw.get("profile") or target_raw.get("profile_id"))
                    if target_raw.get("profile") or target_raw.get("profile_id")
                    else None
                ),
            ),
            steps=steps,
            validation=validation,
        )

    def _steps_from_prefer(
        prefer: list[Any] | tuple[Any, ...],
        *,
        text: str,
        submit: bool,
        tool_id: str,
    ) -> list[dict[str, Any]]:
        normalized = [str(item).strip().lower() for item in prefer]
        steps: list[dict[str, Any]] = []
        if any(item in normalized for item in ("plugin_bridge", "command_palette")):
            steps.append({"action": "focus", "target": tool_id})
        if any(
            item in normalized
            for item in ("clipboard_paste", "keyboard_fallback", "plugin_bridge")
        ):
            steps.append({"action": "type_text", "text": text})
        if submit:
            steps.append({"action": "submit", "tool_id": tool_id})
        if steps:
            return steps
        return ActionPlan.chat_inject_and_submit(text=text, tool_id=tool_id, submit=submit).steps

    class DryRunGuiDriver:  # type: ignore[no-redef]
        def __init__(self, *, session: str = "unknown") -> None:
            self._session = session
            self._log: list[str] = []

        def probe(self) -> DriverStatus:
            return DriverStatus(
                session=self._session,
                backends={"dry_run": True},
                profile_loaded=False,
                dry_run=True,
            )

        def execute(self, plan: ActionPlan) -> ExecutionOutcome:
            steps: list[ActionResult] = []
            for step in plan.steps:
                action = str(step.get("action") or "")
                if action == "focus":
                    result = ActionResult(
                        ok=True,
                        backend="dry_run",
                        evidence=[f"would focus {plan.target.tool_id}"],
                    )
                elif action == "type_text":
                    text = str(step.get("text") or "")
                    result = ActionResult(
                        ok=True,
                        backend="dry_run",
                        evidence=[f"would type {len(text)} chars"],
                    )
                elif action == "submit":
                    result = ActionResult(ok=True, backend="dry_run", evidence=["would submit"])
                else:
                    result = ActionResult(
                        ok=False,
                        backend="dry_run",
                        reason=f"unknown action {action!r}",
                        retryable=False,
                    )
                steps.append(result)
                if not result.ok:
                    return ExecutionOutcome(
                        ok=False,
                        intent=plan.intent,
                        backend="dry_run",
                        reason=result.reason,
                        steps=steps,
                    )
            return ExecutionOutcome(
                ok=True,
                intent=plan.intent,
                backend="dry_run",
                evidence=[item for step in steps for item in step.evidence],
                steps=steps,
            )

    class CompositeGuiDriver:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs

        def probe(self) -> DriverStatus:
            return DriverStatus(
                session=os.environ.get("XDG_SESSION_TYPE", "unknown") or "unknown",
                backends={"gillm": False},
                profile_loaded=False,
                dry_run=False,
            )

        def execute(self, plan: ActionPlan) -> ExecutionOutcome:
            return ExecutionOutcome(
                ok=False,
                intent=plan.intent,
                backend="gillm",
                reason=(
                    "gillm GuiDriver unavailable; install a gillm build "
                    "with adapters and drivers"
                ),
                recovery=["Install or update gillm with adapters/drivers support"],
                retryable=False,
            )


@dataclass
class GillmIDEControlClient:
    """Expose gillm GuiDriver through koru's IDEControlClient protocol."""

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
        reply: dict[str, Any] = {
            "ok": outcome.ok,
            "backend": outcome.backend or "gillm",
            "tool_id": plan.target.tool_id,
            "message": outcome.reason or "",
            "intent": plan.intent,
            "diagnostics": {
                "recovery": outcome.recovery,
                "evidence": outcome.evidence,
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
