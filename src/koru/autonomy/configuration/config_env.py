"""Environment-driven defaults for ``koru autonomous up``.

Re-exports :mod:`koru.autonomy.env` so existing imports keep working.
"""


import argparse

from koru.autonomy.env import (
    apply_autoloop_env_to_args,
    autonomous_environ_doctor_probe,
    effective_ticket_source_flags,
)


def apply_autonomous_env_overrides(args: argparse.Namespace) -> None:
    """Mutate ``args`` with environment defaults (shell-autoloop parity)."""
    apply_autoloop_env_to_args(args)


__all__ = [
    "apply_autonomous_env_overrides",
    "autonomous_environ_doctor_probe",
    "effective_ticket_source_flags",
]
