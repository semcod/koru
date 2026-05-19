"""Compatibility launcher for WUP-driven TestQL runs."""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import sys
from pathlib import Path

_TIMEOUT_PATTERN = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>ms|s)?$")


def _normalize_timeout(value: str) -> str:
    match = _TIMEOUT_PATTERN.fullmatch(value.strip())
    if match is None:
        return value
    number = float(match.group("value"))
    unit = match.group("unit") or "ms"
    milliseconds = number * 1000 if unit == "s" else number
    return str(int(milliseconds))


def _normalize_args(args: list[str]) -> list[str]:
    normalized: list[str] = []
    iterator = iter(args)
    for arg in iterator:
        if arg.startswith("--timeout "):
            normalized.extend(["--timeout", _normalize_timeout(arg.split(None, 1)[1])])
            continue
        if arg.startswith("--timeout="):
            normalized.append("--timeout=" + _normalize_timeout(arg.split("=", 1)[1]))
            continue
        if arg == "--timeout":
            normalized.append(arg)
            with contextlib.suppress(StopIteration):
                normalized.append(_normalize_timeout(next(iterator)))
            continue
        normalized.append(arg)
    return normalized


def _real_testql() -> str:
    this_file = Path(__file__).resolve()
    candidates = [
        path
        for path in os.environ.get("PATH", "").split(os.pathsep)
        if path and Path(path).resolve() != this_file.parent
    ]
    found = shutil.which("testql", path=os.pathsep.join(candidates))
    if found is None:
        raise SystemExit("koru-wup-testql: real `testql` binary not found in PATH")
    return found


def main(argv: list[str] | None = None) -> int:
    args = _normalize_args(list(sys.argv[1:] if argv is None else argv))
    os.execvp(_real_testql(), ["testql", *args])
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
