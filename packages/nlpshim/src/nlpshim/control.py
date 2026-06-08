"""Thin shim — workflow bridge delegates to nlp2koru (not direct dispatch)."""

from __future__ import annotations


def run_workflow(prompt: str, *, project: str = ".") -> dict:
    from nlpshim.conversation_test_api import run_conversation_test

    return run_conversation_test(prompt, project=project)


def to_dsl(prompt: str, *, project: str = ".") -> str:
    from nlp2koru.to_dsl import to_dsl

    return to_dsl(prompt, project=project)
