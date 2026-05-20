"""JSON-Lines run log writer for ``koru --queue [--loop]``.

Each call to ``koru --queue`` (single or loop) gets a single JSONL
file under ``<project>/.planfile/.koru/runs/<run-id>.jsonl``. The
file is append-only and self-contained: header line, one event line
per iteration, footer line. This makes postmortems trivially
``jq``-able without depending on planfile or the koru process itself.

The writer is opt-in (callers must construct it explicitly) and never
crashes the queue runner — IO errors are swallowed after a single
``stderr`` warning. Logs are non-authoritative; planfile sprint YAML
remains the source of truth.
"""


import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koru.runtime import ensure_runs_dir, new_run_id, runs_dir


@dataclass
class RunLogWriter:
    """Append-only JSONL writer with best-effort durability.

    The constructor does not open the file — that happens lazily on the
    first ``write_*`` call so a never-used writer leaves no trace on
    disk (matches the "dry-run leaves zero trace" guarantee).
    """

    path: Path
    run_id: str
    started_at: float
    _opened: bool = False

    def _emit(self, event: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if self._opened else "w"
            with open(self.path, mode, encoding="utf-8") as fh:
                fh.write(json.dumps(event, sort_keys=True) + "\n")
            self._opened = True
        except OSError as exc:
            # Never let logging crash the queue runner.
            print(
                f"koru run_log: write failed ({self.path}): {exc}",
                file=sys.stderr,
            )

    def write_header(self, *, project: Path, mode: str, **extra: Any) -> None:
        self._emit(
            {
                "type": "run.start",
                "run_id": self.run_id,
                "started_at": _iso(self.started_at),
                "project": str(project),
                "mode": mode,
                "pid": os.getpid(),
                **extra,
            },
        )

    def write_iteration(self, *, iteration: int, result: Any) -> None:
        """Record one queue tick. ``result`` should be a QueueRunResult-like."""
        self._emit(
            {
                "type": "iteration",
                "run_id": self.run_id,
                "iteration": iteration,
                "ticket_id": getattr(result, "ticket_id", None),
                "executor_kind": getattr(result, "executor_kind", None),
                "status": getattr(result, "status", None),
                "exit_code": getattr(result, "exit_code", None),
                "message": (getattr(result, "message", "") or "")[:500],
                "stderr_tail": (getattr(result, "stderr", "") or "")[-500:],
                "at": _iso(time.time()),
            },
        )

    def write_footer(self, *, summary: Any) -> None:
        finished = time.time()
        self._emit(
            {
                "type": "run.end",
                "run_id": self.run_id,
                "finished_at": _iso(finished),
                "duration_seconds": round(finished - self.started_at, 3),
                "iterations": getattr(summary, "iterations", None),
                "completed": list(getattr(summary, "completed", []) or []),
                "failed": list(getattr(summary, "failed", []) or []),
                "waiting": list(getattr(summary, "waiting", []) or []),
                "last_status": getattr(summary, "last_status", None),
            },
        )


def open_run_log(project: Path, *, prefix: str = "queue") -> RunLogWriter:
    """Construct a writer pointing at ``<runs>/<run-id>.jsonl``.

    Does not create the directory or the file — see :class:`RunLogWriter`.
    The caller may discard the writer without leaving a trace if no
    events end up being written.
    """
    rid = new_run_id(prefix=prefix)
    path = runs_dir(project) / f"{rid}.jsonl"
    return RunLogWriter(path=path, run_id=rid, started_at=time.time())


def open_run_log_eagerly(project: Path, *, prefix: str = "queue") -> RunLogWriter:
    """Like :func:`open_run_log`, but pre-creates ``runs/`` and writes
    the README stub. Use this when you know you're about to log events
    so the directory layout is visible from the very first iteration."""
    ensure_runs_dir(project)
    return open_run_log(project, prefix=prefix)


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))
