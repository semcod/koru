"""Prompter implementations for ``koru wizard``.

Provides stdin-based and test-scripted prompters for interactive wizard walks.
"""

from __future__ import annotations

import sys

from koru.wizard.tree import Prompter, TreeOption


class StdinPrompter(Prompter):
    """Default prompter: prints prompt + options, reads a single line from stdin.

    Supports a ``?`` prefix for on-demand option help:
        ``?2`` shows the help text for option 2,
        ``?`` lists help for every option,
        regular numeric / id answers advance the wizard.
    """

    def __init__(self, *, stream_in=sys.stdin, stream_out=sys.stdout) -> None:
        self._in = stream_in
        self._out = stream_out

    def _print(self, msg: str) -> None:
        print(msg, file=self._out, flush=True)

    def _render_prompt(self, prompt: str, options: tuple[TreeOption, ...]) -> None:
        self._print("")
        self._print(prompt)
        any_help = any(opt.help for opt in options)
        for idx, opt in enumerate(options, 1):
            suffix = "  [?]" if opt.help else ""
            self._print(f"  [{idx}] {opt.label}{suffix}")
        if any_help:
            self._print("  (wpisz ?N żeby zobaczyć opis opcji / type ?N for help, ? for all)")

    def _show_help(self, target: str, options: tuple[TreeOption, ...]) -> None:
        if target == "":
            for idx, opt in enumerate(options, 1):
                self._print(f"  [{idx}] {opt.label}")
                self._print(f"      {opt.help or '(brak opisu / no description)'}")
            return
        if target.isdigit():
            idx = int(target)
            if 1 <= idx <= len(options):
                opt = options[idx - 1]
                self._print(f"  {opt.label}")
                self._print(f"  {opt.help or '(brak opisu / no description)'}")
                return
        matched = next((o for o in options if o.id == target), None)
        if matched is not None:
            self._print(f"  {matched.label}")
            self._print(f"  {matched.help or '(brak opisu / no description)'}")
            return
        self._print(f"  ! no option {target!r}")

    def ask_choice(self, prompt: str, options: tuple[TreeOption, ...]) -> TreeOption:
        if not options:
            raise RuntimeError("no options available for prompt: " + prompt)
        self._render_prompt(prompt, options)
        while True:
            raw = self._in.readline()
            if not raw:
                raise EOFError("wizard cancelled (EOF on stdin)")
            answer = raw.strip()
            if not answer:
                continue
            if answer.startswith("?"):
                self._show_help(answer[1:].strip(), options)
                continue
            if answer.isdigit():
                idx = int(answer)
                if 1 <= idx <= len(options):
                    return options[idx - 1]
            for opt in options:
                if opt.id == answer or opt.label.lower() == answer.lower():
                    return opt
            self._print(f"  ! unknown answer: {answer!r}, try a number 1..{len(options)}")

    def ask_yes_no(self, prompt: str, *, default: bool = True) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            self._print(f"{prompt} {suffix}")
            raw = self._in.readline()
            if not raw:
                raise EOFError("wizard cancelled (EOF on stdin)")
            answer = raw.strip().lower()
            if not answer:
                return default
            if answer in {"y", "yes", "t", "tak"}:
                return True
            if answer in {"n", "no", "nie"}:
                return False
            self._print("  ! answer with y/n")


class ScriptedPrompter(Prompter):
    """Test prompter: answers come from a queue of (node-question -> option-id) hints."""

    def __init__(self, answers: list[str], yes_no_answers: list[bool] | None = None) -> None:
        self._answers = list(answers)
        self._yes_no = list(yes_no_answers or [])

    def ask_choice(self, prompt: str, options: tuple[TreeOption, ...]) -> TreeOption:
        if not self._answers:
            raise RuntimeError(f"ScriptedPrompter: no answer left for prompt {prompt!r}")
        token = self._answers.pop(0)
        if token.isdigit():
            return options[int(token) - 1]
        for opt in options:
            if opt.id == token:
                return opt
        raise KeyError(f"ScriptedPrompter: unknown option {token!r} for {prompt!r}")

    def ask_yes_no(self, prompt: str, *, default: bool = True) -> bool:
        if not self._yes_no:
            return default
        return self._yes_no.pop(0)
