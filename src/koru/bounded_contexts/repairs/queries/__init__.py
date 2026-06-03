"""Queries for repair history."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoadRepairHistoryQuery:
    subject: str | None = None
    limit: int = 20


__all__ = ["LoadRepairHistoryQuery"]
