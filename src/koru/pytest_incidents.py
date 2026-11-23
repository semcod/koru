"""Track missing Python modules until pytest verifies collection in the same project."""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time

from koru.runtime import runtime_dir
from koru.scan_types import Suggestion

# A pytest error line, not arbitrary prose about a previous missing module.
MISSING = re.compile(r"^(?:E\s+|(?:ERROR|FAILED)\s+\S+\s+-\s+|\s*)ModuleNotFoundError: No module named ['\"]([a-zA-Z_]\w*(?:\.\w+)*)['\"]", re.MULTILINE)
LOG = logging.getLogger(__name__)
SCHEMA = """
CREATE TABLE IF NOT EXISTS probe (id INTEGER PRIMARY KEY CHECK(id=1), started INTEGER, generation TEXT);
CREATE TABLE IF NOT EXISTS open_modules (module TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS outbox (seq INTEGER PRIMARY KEY, body TEXT NOT NULL);
"""


def _source_key(source, module, generation):
    return f"{source}:pytest_collect:missing:{module}:{generation}"


def ticket_key(source, context):
    fact = (context or {}).get("pytest_incident")
    if isinstance(fact, dict) and isinstance(fact.get("module"), str) and isinstance(fact.get("generation"), str):
        return _source_key(source, fact["module"], fact["generation"])
    return None


def history_keys(source, context):
    key = ticket_key(source, context)
    if key:
        return {key}
    if not isinstance(context, dict) or context.get("signal") != "pytest_collect":
        return set()
    text = context.get("input")
    return {_source_key(source, module, "initial") for module in MISSING.findall(text)} if isinstance(text, str) else set()


def suggestion(module, generation):
    return Suggestion(
        signal="pytest_collect", title=f"Diagnose missing pytest collection dependency {module}",
        description=(f"Pytest collection reported ModuleNotFoundError for `{module}`. "
                     "Identify the interpreter used by the probe, check the declared project dependencies, extras "
                     "and lockfile, and give the owner the matching environment or packaging fix. Cite the observed "
                     "exception and the collection command. Only a later successful collection verifies recovery."),
        priority="high", labels=("ci", "diagnosis", "scan"),
        source_context={"pytest_incident": {"module": module, "generation": generation}},
    )


def _repository(project):
    top = subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel"],
                         capture_output=True, check=False, text=True)
    if top.returncode or Path(top.stdout.strip()).resolve() != project.resolve():
        return None
    from koru.work.llm_provenance import _git_remote_url
    slug = re.fullmatch(r"https://github\.com/([\w.-]+/[\w.-]+)", _git_remote_url(project))
    return slug.group(1) if slug else None


def _deliver(conn, project, state):
    # Limit optional model time in the scan path. Unsent transitions survive restart.
    deadline = time.monotonic() + 35
    repository = _repository(project)
    if not repository:
        return
    try:
        from urtlog.facts import observe_check
        from urtlog.store import UrtLogStore
        with UrtLogStore(state) as store:
            for seq, body in conn.execute("SELECT seq,body FROM outbox ORDER BY seq LIMIT 24").fetchall():
                event = json.loads(body)
                if time.monotonic() >= deadline:
                    break
                if event["repository"] != repository:
                    LOG.warning("Pytest fact retained for its original repository")
                    continue
                result = observe_check(store, event, principal="koru")
                if result.get("advice") != "pending":
                    with conn:
                        conn.execute("DELETE FROM outbox WHERE seq=?", (seq,))
    except (ImportError, ValueError, OSError, sqlite3.Error) as exc:
        LOG.warning("Pytest fact delivery pending (%s)", type(exc).__name__)


def record_probe(project: Path, modules: set[str], *, success: bool, started_ns: int, output: str):
    """Fence concurrent probes by start time, then deliver transitions outside the transaction."""
    root = runtime_dir(project)
    root.mkdir(exist_ok=True, parents=True)
    state = os.environ.get("URTLOG_STATE_DIR")
    with closing(sqlite3.connect(root / "pytest-incidents.sqlite3", timeout=10)) as conn:
        conn.executescript(SCHEMA)
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute("SELECT started,generation FROM probe WHERE id=1").fetchone()
            if previous and started_ns <= previous[0]:
                return None
            generation = previous[1] if previous else "initial"
            active = {row[0] for row in conn.execute("SELECT module FROM open_modules")}
            changed = active if success else modules - active
            if success:
                if active or not previous:
                    generation = str(started_ns)
                conn.execute("DELETE FROM open_modules")
            else:
                conn.executemany("INSERT OR IGNORE INTO open_modules VALUES (?)", [(name,) for name in modules])
            conn.execute("INSERT OR REPLACE INTO probe VALUES (1,?,?)", (started_ns, generation))
            repository = _repository(project) if changed else None
            if repository and changed:
                digest = hashlib.sha256(output.encode()).hexdigest()
                for module in sorted(changed):
                    cause = f"missing-dependency.{module}"
                    if len(cause) > 64:  # Reflex failure codes have a 64-character wire limit.
                        cause = "missing-dependency.sha256-" + hashlib.sha256(module.encode()).hexdigest()[:32]
                    body = {"repository": repository, "schema": "reflex.observation/v1", "event_type": "check.fact",
                            "operation": "dev.pytest-collect", "failure_code": cause,
                            "source_event_id": f"pytest-{started_ns}-{cause}", "evidence_digest": digest,
                            "occurred_at": datetime.fromtimestamp(started_ns / 1e9, timezone.utc).isoformat(),
                            "outcome": "success" if success else "failure"}
                    conn.execute("INSERT INTO outbox(body) VALUES (?)", (json.dumps(body),))
        if state and conn.execute("SELECT 1 FROM outbox LIMIT 1").fetchone():
            _deliver(conn, project, state)
    return generation
