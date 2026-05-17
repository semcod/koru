"""`koruide` package scaffold.

This package is the extraction target for IDE communication/control-plane
components currently hosted under `koru.autopilot`.
"""

from .client import KoruIDEClient, build_client

__all__ = ["KoruIDEClient", "build_client"]
