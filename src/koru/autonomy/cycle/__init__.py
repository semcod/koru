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
    "DiagnosticResult",
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
    "apply_agent_lane_environ",
    "apply_autopilot_drive_outcome",
    "autopilot_escalation_cooldown_seconds",
    "autopilot_os_injector_cooldown_seconds",
    "autopilot_redrive_cooldown_seconds",
    "build_cycle_run_kwargs",
    "chat_intake_ticket_enabled",
    "classify_chat_event",
    "compact_question_text",
    "compute_cycle_sleep",
    "configure_loop_state",
    "decide_intake_ticket",
    "decide_redrive_cooldown",
    "effective_cycle_autopilot_enabled",
    "effective_cycle_scan_enabled",
    "effective_ide_control_submit",
    "explain_skip",
    "extract_needs_input_question",
    "imgl_fallback_enabled",
    "latest_received_text",
    "llm_needs_input_heuristic_enabled",
    "llm_needs_input_ticket_enabled",
    "llm_needs_input_ticket_priority",
    "llm_needs_input_ticket_queue_name",
    "llm_reflection_summary_max_age_seconds",
    "looks_like_autopilot_generated_prompt",
    "looks_like_explicit_intake_text",
    "nlp2uri_ide_control_enabled",
    "normalize_prompt_text",
    "resolve_agent_lane_from_environ",
    "resolve_autopilot_ide",
    "resolve_effective_cycle_flags",
    "run_cycle_with_compat",
    "scan_while_waiting_input_enabled",
    "select_and_log_cycle_profile",
    "try_gillm_gui_fallback",
    "try_imgl_gui_fallback",
    "try_nlp2uri_focus_fallback",
    "try_nlp2uri_ide_control",
    "try_os_injector_fallback",
    "try_os_injector_fallback_with_deps",
    "try_vdisplay_control_fallback",
]
