from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_BUDGET_PER_CYCLE_USD = 0.02
DEFAULT_BUDGET_PER_HOUR_USD = 0.50
DEFAULT_MODEL = "qwen/qwen3-coder-next"


@dataclass
class BudgetTracker:
    """In-memory spend tracker. Resets on process restart."""

    spent_usd: float = 0.0
    calls: int = 0
    first_call_ts: float = 0.0
    last_call_ts: float = 0.0
    budget_per_cycle_usd: float = DEFAULT_BUDGET_PER_CYCLE_USD
    budget_per_hour_usd: float = DEFAULT_BUDGET_PER_HOUR_USD

    def record(self, cost_usd: float) -> None:
        now = time.time()
        if self.first_call_ts == 0.0:
            self.first_call_ts = now
        self.last_call_ts = now
        self.calls += 1
        self.spent_usd += cost_usd

    def over_cycle_budget(self) -> bool:
        return self.spent_usd >= self.budget_per_cycle_usd

    def over_hour_budget(self) -> bool:
        if self.first_call_ts == 0.0:
            return False
        elapsed = time.time() - self.first_call_ts
        if elapsed >= 3600:
            self.spent_usd = 0.0
            self.calls = 0
            self.first_call_ts = time.time()
            return False
        return self.spent_usd >= self.budget_per_hour_usd

    def within_budget(self) -> bool:
        return not self.over_cycle_budget() and not self.over_hour_budget()

    def reset_cycle(self) -> None:
        self.spent_usd = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_budget = BudgetTracker()


def get_budget_tracker() -> BudgetTracker:
    return _budget
