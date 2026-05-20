"""Shared autonomy / autoloop configuration (CLI, shell, MCP).

See :mod:`koru.autonomy.env` for environment variable names and defaults
that mirror ``scripts/koru-autoloop.sh``.
"""


from koru.autonomy.config import AutonomyConfig
from koru.autonomy.env import (
    AUTOLOOP_ENV_DEFAULTS,
    apply_autoloop_env_to_args,
    autonomous_environ_doctor_probe,
    effective_ticket_source_flags,
    env_truthy,
)

__all__ = [
    "AutonomyConfig",
    "AUTOLOOP_ENV_DEFAULTS",
    "apply_autoloop_env_to_args",
    "autonomous_environ_doctor_probe",
    "effective_ticket_source_flags",
    "env_truthy",
]
