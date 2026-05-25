"""Concrete OS strategies (Wayland-Linux, X11-Linux, macOS, Windows).

Importing this package auto-registers every shipped strategy with the
registry. New strategies should call :func:`register_os_strategy` at
module import time, mirroring how :mod:`koruide.ides` registers IDE
strategies.
"""

from koruos.strategies import (
    darwin,
    wayland_linux,
    windows,
    x11_linux,
)

__all__ = ["darwin", "wayland_linux", "windows", "x11_linux"]
