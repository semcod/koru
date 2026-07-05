"""Autonomous cycle management for loop execution."""

from koru.autonomy.cycle.cycle import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_bridge import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_chat_activity import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_chat_activity import (  # noqa: F401
    _skip_due_to_recent_chat_activity,
)
from koru.autonomy.cycle.cycle_chat_activity_analyzer import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_chat_activity_config import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_chat_activity_config import (  # noqa: F401
    autopilot_redrive_cooldown_seconds as _autopilot_redrive_cooldown_seconds,
)
from koru.autonomy.cycle.cycle_chat_activity_text import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_chat_activity_text import (  # noqa: F401
    extract_needs_input_question as _extract_needs_input_question,
)
from koru.autonomy.cycle.cycle_chat_activity_tickets import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_common import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_config import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_drive_outcome import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_drive_retry import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_drive_retry import (  # noqa: F401
    _log_autopilot_result,
    _reply_chat_input_busy,
    _resolve_autopilot_drive_decision,
)
from koru.autonomy.cycle.cycle_gate import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_orchestrator import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_orchestrator import (  # noqa: F401
    _handle_autopilot_phase,
)
from koru.autonomy.cycle.cycle_post_drive import *  # noqa: F401, F403
from koru.autonomy.cycle.cycle_post_drive import (  # noqa: F401
    _handle_post_drive_verification,
    _take_pre_drive_snapshot,
)
from koru.autonomy.cycle.cycle_skip_conditions import *  # noqa: F401, F403
from koru.autonomy.cycle_events import (  # noqa: F401
    _drain_autopilot_events,
    _handle_autopilot_events,
)
from koru.autonomy.cycle_queue_scan import (  # noqa: F401
    _build_queue_command,
    _handle_scan_after_idle,
)
from koru.autonomy.env import plugin_required_for_ide as _plugin_required_for_ide  # noqa: F401

# Explicit imports for functions needed by tests/external code
from koruide.ide import detect_terminal_host_ide_id  # noqa: F401

__all__ = [
    "DiagnosticResult",  # noqa: F405
    "_autopilot_redrive_cooldown_seconds",
    "_build_queue_command",
    "_drain_autopilot_events",
    "_extract_needs_input_question",
    "_handle_autopilot_events",
    "_handle_autopilot_phase",
    "_handle_post_drive_verification",
    "_handle_scan_after_idle",
    "_log_autopilot_result",
    "_plugin_required_for_ide",
    "_reply_chat_input_busy",
    "_resolve_autopilot_drive_decision",
    "_skip_due_to_recent_chat_activity",
    "_take_pre_drive_snapshot",
    "detect_terminal_host_ide_id",
    "apply_agent_lane_environ",  # noqa: F405
    "apply_autopilot_drive_outcome",  # noqa: F405
    "autopilot_escalation_cooldown_seconds",  # noqa: F405
    "autopilot_os_injector_cooldown_seconds",  # noqa: F405
    "autopilot_redrive_cooldown_seconds",  # noqa: F405
    "build_cycle_run_kwargs",  # noqa: F405
    "chat_intake_ticket_enabled",  # noqa: F405
    "classify_chat_event",  # noqa: F405
    "compact_question_text",  # noqa: F405
    "compute_cycle_sleep",  # noqa: F405
    "configure_loop_state",  # noqa: F405
    "decide_intake_ticket",  # noqa: F405
    "decide_redrive_cooldown",  # noqa: F405
    "effective_cycle_autopilot_enabled",  # noqa: F405
    "effective_cycle_scan_enabled",  # noqa: F405
    "effective_ide_control_submit",  # noqa: F405
    "explain_skip",  # noqa: F405
    "extract_needs_input_question",  # noqa: F405
    "imgl_fallback_enabled",  # noqa: F405
    "latest_received_text",  # noqa: F405
    "llm_needs_input_heuristic_enabled",  # noqa: F405
    "llm_needs_input_ticket_enabled",  # noqa: F405
    "llm_needs_input_ticket_priority",  # noqa: F405
    "llm_needs_input_ticket_queue_name",  # noqa: F405
    "llm_reflection_summary_max_age_seconds",  # noqa: F405
    "looks_like_autopilot_generated_prompt",  # noqa: F405
    "looks_like_explicit_intake_text",  # noqa: F405
    "nlp2uri_ide_control_enabled",  # noqa: F405
    "normalize_prompt_text",  # noqa: F405
    "resolve_agent_lane_from_environ",  # noqa: F405
    "resolve_autopilot_ide",  # noqa: F405
    "resolve_effective_cycle_flags",  # noqa: F405
    "run_cycle_with_compat",  # noqa: F405
    "scan_while_waiting_input_enabled",  # noqa: F405
    "select_and_log_cycle_profile",  # noqa: F405
    "try_gillm_gui_fallback",  # noqa: F405
    "try_imgl_gui_fallback",  # noqa: F405
    "try_nlp2uri_focus_fallback",  # noqa: F405
    "try_nlp2uri_ide_control",  # noqa: F405
    "try_os_injector_fallback",  # noqa: F405
    "try_os_injector_fallback_with_deps",  # noqa: F405
    "try_vdisplay_control_fallback",  # noqa: F405
]
