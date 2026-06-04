"""koru autopilot — compatibility façade re-exporting :mod:`koruide` symbols.

See ``docs/autopilot-design.md`` for the architecture overview.

Public surface (all delegated to native ``koruide`` implementations):
    - :func:`default_socket_path`   from :mod:`koruide.socket`.
    - :class:`Message` and helpers  from :mod:`koru.autopilot.protocol` (shim).
    - :class:`Injector`             from :mod:`gillm.injection.injector`
      (legacy: :mod:`koru.autopilot.injector` shim, deprecated).
    - :func:`detect_running_ides`   from :mod:`koru.autopilot.ide` (shim).
    - :class:`AutopilotDaemon`      from :mod:`koru.autopilot.daemon` (shim).
    - :class:`AutopilotClient`      from :mod:`koru.autopilot.client` (shim).
"""

from __future__ import annotations

from koruide.socket import default_socket_path

__all__ = ["default_socket_path"]
