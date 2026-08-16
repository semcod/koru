from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_MODEL = "cursor/grok-4.6"


@dataclass
class BudgetTracker:
    """Compatibility telemetry; Koru does not enforce monetary LLM budgets."""

    spent_usd: float = 0.0
    calls: int = 0

    def record(self, cost_usd: float) -> None:
        self.calls += 1
        self.spent_usd += cost_usd

    def within_budget(self) -> bool:
        """Retained for callers compiled against the old API; never blocks."""
        return True

    def reset_cycle(self) -> None:
        self.spent_usd = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_budget = BudgetTracker()


def get_budget_tracker() -> BudgetTracker:
    return _budget
