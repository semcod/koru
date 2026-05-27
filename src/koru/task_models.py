"""Shared task intake data models."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CreatedTask:
    ticket_id: str
    sprint: str
    path: Path
    name: str
    reused: bool = False
