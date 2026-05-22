"""Mesh pre-shared key helpers."""

from __future__ import annotations

import os
from pathlib import Path


def load_mesh_key(path: Path) -> bytes:
    raw = path.expanduser().read_bytes()
    key = raw.strip()
    if len(key) < 16:
        msg = f"mesh key too short ({len(key)} bytes): {path}"
        raise ValueError(msg)
    return key


def write_mesh_key(path: Path, *, force: bool = False) -> Path:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return path
    path.write_bytes(os.urandom(32))
    path.chmod(0o600)
    return path
