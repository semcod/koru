"""Compatibility aliases for canonical NLP result and plan models."""

from nlp2koru.apply import ApplyResult
from nlp2koru.to_dsl import KoruIntent as CoruIntent
from nlp2koru.to_dsl import KoruPlan as CoruPlan

__all__ = ["ApplyResult", "CoruIntent", "CoruPlan"]
