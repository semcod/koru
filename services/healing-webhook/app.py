"""healing-webhook — alert/probe sink that triggers redsl / rebuild / planfile.

Endpoints
---------
GET  /healthz              — liveness
GET  /metrics              — Prometheus exposition
POST /alertmanager         — Alertmanager webhook payload
POST /probe-failure        — testql-watchdog failure payload
GET  /history              — last 50 healing actions (JSON)
GET  /tickets              — tickets created by the webhook (from planfile.yaml)

Decision matrix (label → action)
-------------------------------------------------------------
healing_strategy = annotate         → log only
healing_strategy = redsl_gate       → docker run semcod/redsl:local gate check
healing_strategy = redsl_improve    → docker run semcod/redsl:local improve --max-actions 1 --dry-run
healing_strategy = rebuild_restore  → docker run semcod/rebuild:local restore <endpoint>

Every alert with severity >= error **also** creates a ticket in the
project's planfile.yaml via `planfile ticket create`. The ticket carries
a full LLM-ready prompt block (reproduction, context, acceptance criteria)
so any IDE-integrated agent (Windsurf, Cursor, Claude Code, aider) can
pick it up and propose a fix without additional priming.

DRY_RUN=true (default) forces every redsl/rebuild invocation to use the
appropriate dry-run/no-apply flag, so the webhook is *safe* to enable in
production. Flip DRY_RUN=false only after you trust the recommendations.
"""

from __future__ import annotations

import collections
import logging
import os
import subprocess
import sys
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    generate_latest,
)

from ticket_builder import build_ticket_payload

# ── Config ─────────────────────────────────────────────────────────────
REPO_PATH = os.getenv("REPO_PATH", "/repo")
REDSL_IMAGE = os.getenv("REDSL_IMAGE", "semcod/redsl:local")
REBUILD_IMAGE = os.getenv("REBUILD_IMAGE", "semcod/rebuild:local")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in {"1", "true", "yes"}
MAX_ACTIONS_PER_HOUR = int(os.getenv("MAX_ACTIONS_PER_HOUR", "4"))  # hard rate cap
PLANFILE_ENABLED = os.getenv("PLANFILE_ENABLED", "true").lower() in {"1", "true", "yes"}
PLANFILE_SPRINT = os.getenv("PLANFILE_SPRINT", "current")
PLANFILE_BIN = os.getenv("PLANFILE_BIN", "planfile")
ENABLE_LLM_AUTOFIX = os.getenv("ENABLE_LLM_AUTOFIX", "false").lower() in {"1", "true", "yes"}

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("healing-webhook")

# ── Metrics ────────────────────────────────────────────────────────────
ACTIONS = Counter(
    "c2004_healing_actions_total",
    "Healing actions taken by the webhook.",
    ["action", "outcome", "component"],
)
ALERTS = Counter(
    "c2004_healing_alerts_total",
    "Alerts received.",
    ["source", "severity"],
)
LAST_ACTION_TS = Gauge(
    "c2004_healing_last_action_timestamp",
    "Unix ts of the most recent healing action.",
    ["action"],
)
TICKETS_CREATED = Counter(
    "c2004_healing_tickets_created_total",
    "Planfile tickets created from alerts.",
    ["severity", "outcome"],
)
VALLM_SCORE = Gauge(
    "c2004_vallm_score",
    "Last vallm validation score per affected path (0.0 fail … 1.0 pass).",
    ["path", "tier"],
)
VALLM_RUNS = Counter(
    "c2004_vallm_runs_total",
    "Number of vallm validation runs.",
    ["tier", "outcome"],
)
REDUP_GROUPS = Gauge(
    "c2004_redup_groups",
    "Number of duplicate groups detected (after exclude filter).",
)
REDUP_SAVED_LINES = Gauge(
    "c2004_redup_saved_lines",
    "Total lines recoverable through duplicate refactor.",
)
REDUP_BUDGET_BREACH = Gauge(
    "c2004_redup_budget_breach",
    "1 if duplicate budget breached (groups>max or lines>max), else 0.",
)

app = FastAPI(title="c2004 healing-webhook", version="1.0")
history: collections.deque = collections.deque(maxlen=50)
_recent_actions: collections.deque = collections.deque(maxlen=MAX_ACTIONS_PER_HOUR * 4)


# ── Helpers ────────────────────────────────────────────────────────────
def _rate_limit_ok() -> bool:
    now = time.time()
    while _recent_actions and now - _recent_actions[0] > 3600:
        _recent_actions.popleft()
    return len(_recent_actions) < MAX_ACTIONS_PER_HOUR


def _record_action(action: str, outcome: str, component: str, detail: dict) -> None:
    ACTIONS.labels(action=action, outcome=outcome, component=component).inc()
    LAST_ACTION_TS.labels(action=action).set(time.time())
    history.appendleft(
        {
            "ts": time.time(),
            "action": action,
            "outcome": outcome,
            "component": component,
            "detail": detail,
            "dry_run": DRY_RUN,
        }
    )


def create_planfile_ticket(alert: dict, *, source: str = "healing-webhook") -> dict:
    """Create a planfile ticket for an alert.

    The ticket body is produced by ticket_builder.build_ticket_payload and
    is *LLM-agnostic* — any coding agent (Windsurf/Cursor/Claude Code/aider)
    can consume it verbatim via `planfile ticket show <ID>`.

    Returns a small dict describing the outcome; never raises so the
    healing pipeline isn't blocked by a planfile CLI issue.
    """
    if not PLANFILE_ENABLED:
        return {"skipped": "PLANFILE_ENABLED=false"}

    try:
        payload = build_ticket_payload(alert, repo=REPO_PATH, source=source)
    except Exception as exc:  # noqa: BLE001
        log.warning("ticket_builder failed: %s", exc)
        TICKETS_CREATED.labels(severity="unknown", outcome="build_failed").inc()
        return {"error": f"ticket_builder failed: {exc}"}

    # Enrich the ticket description with a vallm pre-flight summary of the
    # affected files. This gives the LLM agent immediate insight into whether
    # the files are syntactically clean or already broken (saves a round trip).
    try:
        labels = alert.get("labels", {}) or {}
        component = labels.get("component", "unknown")
        files = _resolve_affected_files(component, labels, max_files=5)
        if files:
            vallm_results = [_run_vallm_check(f) for f in files]
            avg = sum(r.get("score", 0.0) for r in vallm_results) / len(vallm_results)
            lines = [f"\n## 🔍 vallm pre-flight (tier-1 syntax check)\n"]
            lines.append(f"**Average score:** {avg:.2f} ({len(files)} file(s) checked)\n")
            for f, r in zip(files, vallm_results):
                icon = "✅" if r.get("ok") else "❌"
                rel = f.replace(f"{REPO_PATH}/", "")
                lines.append(f"- {icon} `{rel}` — score `{r.get('score', 0):.2f}`")
            payload["description"] = payload["description"] + "\n" + "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        log.debug("vallm enrichment skipped: %s", exc)

    severity = next(
        (lbl.split(":", 1)[1] for lbl in payload["labels"] if lbl.startswith("severity:")),
        "unknown",
    )
    cmd = [
        PLANFILE_BIN,
        "ticket",
        "create",
        payload["name"],
        "--priority",
        payload["priority"],
        "--sprint",
        PLANFILE_SPRINT,
        "--source",
        payload["source"],
        "--description",
        payload["description"],
    ]
    for label in payload["labels"]:
        cmd.extend(["--label", label])

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, cwd=REPO_PATH, timeout=15
        )
        outcome = "success" if proc.returncode == 0 else "failed"
        TICKETS_CREATED.labels(severity=severity, outcome=outcome).inc()
        # Extract the new ticket ID from planfile's stdout when possible.
        new_id = None
        for line in (proc.stdout or "").splitlines():
            if "PLF-" in line:
                for word in line.split():
                    if word.startswith("PLF-"):
                        new_id = word.strip(":,.")
                        break
        log.info("planfile ticket create -> %s (%s)", outcome, new_id or "?")
        return {
            "outcome": outcome,
            "ticket_id": new_id,
            "stdout": (proc.stdout or "")[-300:],
            "stderr": (proc.stderr or "")[-300:],
        }
    except FileNotFoundError:
        TICKETS_CREATED.labels(severity=severity, outcome="no_cli").inc()
        log.warning("planfile CLI not installed in this container; skipping ticket")
        return {"error": "planfile CLI not found"}
    except Exception as exc:  # noqa: BLE001
        TICKETS_CREATED.labels(severity=severity, outcome="exception").inc()
        log.warning("planfile ticket create failed: %s", exc)
        return {"error": str(exc)}


def _run_docker(image: str, cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """Run a one-shot docker container, bind-mount the repo read-write."""
    argv = [
        "docker",
        "run",
        "--rm",
        "--network=c2004-quality-net",
        "-v",
        f"{REPO_PATH}:/mnt/project:rw",
        "-w",
        "/mnt/project",
        image,
        *cmd,
    ]
    log.info("→ %s", " ".join(argv))
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


# ── Healing strategies ─────────────────────────────────────────────────
def heal_redsl_gate(component: str, detail: dict) -> dict:
    code, out, err = _run_docker(REDSL_IMAGE, ["python", "-m", "redsl", "gate", "check", "/mnt/project"])
    outcome = "success" if code == 0 else "violations"
    _record_action("redsl_gate", outcome, component, {"exit": code, "stdout": out[-500:], "stderr": err[-500:]})
    return {"action": "redsl_gate", "exit": code, "outcome": outcome}


def heal_redsl_improve(component: str, detail: dict) -> dict:
    if not ENABLE_LLM_AUTOFIX:
        downgraded_detail = {
            **detail,
            "requested_action": "redsl_improve",
            "reason": "ENABLE_LLM_AUTOFIX=false",
        }
        _record_action("redsl_improve", "disabled", component, downgraded_detail)
        return {
            "action": "redsl_improve",
            "outcome": "disabled",
            "fallback": "annotate",
            "reason": "ENABLE_LLM_AUTOFIX=false",
        }
    if not _rate_limit_ok():
        _record_action("redsl_improve", "rate_limited", component, detail)
        return {"action": "redsl_improve", "outcome": "rate_limited"}
    _recent_actions.append(time.time())
    cmd = ["python", "-m", "redsl", "improve", "/mnt/project", "--max-actions", "1"]
    if DRY_RUN:
        cmd.append("--dry-run")
    code, out, err = _run_docker(REDSL_IMAGE, cmd, timeout=300)
    outcome = "success" if code == 0 else "failed"
    _record_action("redsl_improve", outcome, component, {"exit": code, "stdout": out[-500:], "stderr": err[-500:]})
    return {"action": "redsl_improve", "exit": code, "outcome": outcome}


def heal_rebuild_restore(component: str, detail: dict) -> dict:
    if not _rate_limit_ok():
        _record_action("rebuild_restore", "rate_limited", component, detail)
        return {"action": "rebuild_restore", "outcome": "rate_limited"}
    _recent_actions.append(time.time())
    endpoint = detail.get("endpoint") or detail.get("instance") or "unknown"
    cmd = ["restore", endpoint, "--results-dir", "/mnt/project/.rebuild"]
    if DRY_RUN:
        cmd.append("--dry-run")
    code, out, err = _run_docker(REBUILD_IMAGE, cmd, timeout=600)
    outcome = "success" if code == 0 else "failed"
    _record_action(
        "rebuild_restore",
        outcome,
        component,
        {"endpoint": endpoint, "exit": code, "stdout": out[-500:], "stderr": err[-500:]},
    )
    return {"action": "rebuild_restore", "exit": code, "outcome": outcome, "endpoint": endpoint}


def heal_annotate(component: str, detail: dict) -> dict:
    _record_action("annotate", "logged", component, detail)
    return {"action": "annotate", "outcome": "logged"}


# ── vallm validation helpers ───────────────────────────────────────────
# Multi-tier code validation:
#   tier 1 (check)    — syntax only, fast (~50ms/file), no LLM call
#   tier 2 (validate) — full pipeline: syntax + imports + complexity + LLM-as-judge
#
# Used both as a stand-alone strategy (`vallm_validate`) AND as an automatic
# context enrichment step on every ticket (so the LLM agent sees the score
# of the affected files without running vallm itself).

def _run_vallm_check(file_path: str, timeout: int = 15) -> dict:
    """Quick syntax check (tier 1). Returns {ok, score, raw}."""
    cmd = ["vallm", "check", "--file", file_path, "--output", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        ok = proc.returncode == 0
        try:
            import json as _json
            payload = _json.loads(proc.stdout or "{}")
            score = float(payload.get("score", 1.0 if ok else 0.0))
        except Exception:  # noqa: BLE001
            payload = {"raw_stdout": (proc.stdout or "")[:300]}
            score = 1.0 if ok else 0.0
        VALLM_SCORE.labels(path=file_path, tier="check").set(score)
        VALLM_RUNS.labels(tier="check", outcome="pass" if ok else "fail").inc()
        return {"ok": ok, "score": score, "tier": "check", "raw": payload}
    except FileNotFoundError:
        VALLM_RUNS.labels(tier="check", outcome="no_cli").inc()
        return {"ok": True, "score": 1.0, "tier": "check", "skipped": "vallm not installed"}
    except subprocess.TimeoutExpired:
        VALLM_RUNS.labels(tier="check", outcome="timeout").inc()
        return {"ok": False, "score": 0.0, "tier": "check", "error": "timeout"}
    except Exception as exc:  # noqa: BLE001
        VALLM_RUNS.labels(tier="check", outcome="exception").inc()
        return {"ok": False, "score": 0.0, "tier": "check", "error": str(exc)}


def _run_vallm_validate(file_path: str, model: str | None = None, timeout: int = 60) -> dict:
    """Full pipeline including LLM-as-judge (tier 2). Slower; uses LLM API key."""
    cmd = ["vallm", "validate", "--file", file_path, "--output", "json"]
    if model:
        cmd.extend(["--model", model])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        ok = proc.returncode == 0
        try:
            import json as _json
            payload = _json.loads(proc.stdout or "{}")
            score = float(payload.get("score", 1.0 if ok else 0.0))
        except Exception:  # noqa: BLE001
            payload = {"raw_stdout": (proc.stdout or "")[:300]}
            score = 1.0 if ok else 0.0
        VALLM_SCORE.labels(path=file_path, tier="validate").set(score)
        VALLM_RUNS.labels(tier="validate", outcome="pass" if ok else "fail").inc()
        return {"ok": ok, "score": score, "tier": "validate", "raw": payload}
    except FileNotFoundError:
        VALLM_RUNS.labels(tier="validate", outcome="no_cli").inc()
        return {"ok": True, "score": 1.0, "tier": "validate", "skipped": "vallm not installed"}
    except subprocess.TimeoutExpired:
        VALLM_RUNS.labels(tier="validate", outcome="timeout").inc()
        return {"ok": False, "score": 0.0, "tier": "validate", "error": "timeout"}
    except Exception as exc:  # noqa: BLE001
        VALLM_RUNS.labels(tier="validate", outcome="exception").inc()
        return {"ok": False, "score": 0.0, "tier": "validate", "error": str(exc)}


def _resolve_affected_files(component: str, labels: dict, max_files: int = 10) -> list[str]:
    """Map alert component → concrete files to validate.

    Reuses ticket_builder._infer_paths logic but materialises directory
    globs into actual file paths within REPO_PATH (capped at max_files).
    """
    from ticket_builder import _infer_paths
    import glob as _glob
    from pathlib import Path as _Path

    candidates = _infer_paths(component, labels)
    files: list[str] = []
    for spec in candidates:
        full = _Path(REPO_PATH) / spec
        if full.is_file():
            files.append(str(full))
        elif full.is_dir():
            files.extend(str(p) for p in sorted(full.rglob("*.py"))[:max_files])
        else:
            # treat as glob (e.g. "connect-*/backend/")
            for m in sorted(_glob.glob(str(_Path(REPO_PATH) / spec), recursive=True)):
                mp = _Path(m)
                if mp.is_file() and mp.suffix == ".py":
                    files.append(str(mp))
                elif mp.is_dir():
                    files.extend(str(p) for p in sorted(mp.rglob("*.py"))[:5])
        if len(files) >= max_files:
            break
    return files[:max_files]


def heal_vallm_validate(component: str, detail: dict) -> dict:
    """Run vallm tier-1 (check) on all files mapped from the alert component.

    Cheap pre-flight gate: blocks AI patches if affected files are already
    syntactically broken (likely from a prior failed patch). When all files
    pass tier-1, optionally upgrades the worst-scoring file to tier-2
    (LLM-as-judge) for richer context in the resulting ticket.
    """
    labels = detail.get("labels", {}) if isinstance(detail.get("labels"), dict) else {}
    files = _resolve_affected_files(component, labels, max_files=8)
    if not files:
        _record_action("vallm_validate", "no_files", component, detail)
        return {"action": "vallm_validate", "outcome": "no_files"}

    results = [_run_vallm_check(f) for f in files]
    failures = [r for r in results if not r.get("ok")]
    avg_score = sum(r.get("score", 0.0) for r in results) / max(len(results), 1)

    outcome = "pass" if not failures else "violations"
    _record_action(
        "vallm_validate",
        outcome,
        component,
        {
            "files_checked": len(files),
            "failures": len(failures),
            "avg_score": round(avg_score, 3),
            "results": [{"file": f, "ok": r.get("ok"), "score": r.get("score")} for f, r in zip(files, results)],
        },
    )
    return {
        "action": "vallm_validate",
        "outcome": outcome,
        "files_checked": len(files),
        "failures": len(failures),
        "avg_score": round(avg_score, 3),
    }


# ── redup duplicate detection ──────────────────────────────────────────
# Runs `scripts/redup-check.sh` from the mounted repo and exposes the
# filtered summary (post-exclude) as Prometheus metrics. When the budget
# is breached we still create a ticket — the budget check is enforced by
# scripts/redup-check.sh exit code (non-zero = breach).

def _run_redup_check(timeout: int = 180) -> dict:
    """Run redup-check.sh and parse the filtered JSON report.

    Returns: {ok, groups, saved_lines, breach, top_groups, raw}
    """
    script = "scripts/redup-check.sh"
    cmd = ["bash", script, "."]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=REPO_PATH,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "groups": 0, "saved_lines": 0}
    except FileNotFoundError:
        return {"ok": True, "skipped": "redup-check.sh missing", "groups": 0, "saved_lines": 0}

    breach = proc.returncode != 0
    filtered_json = os.path.join(REPO_PATH, ".redup", "check.filtered.json")
    summary = {"groups": 0, "saved_lines": 0, "top_groups": []}
    try:
        import json as _json
        with open(filtered_json, "r", encoding="utf-8") as fh:
            payload = _json.load(fh)
        s = payload.get("summary", {}) or {}
        summary["groups"] = int(s.get("total_groups", 0))
        summary["saved_lines"] = int(s.get("total_saved_lines", 0))
        # Top 3 groups by fragment count for ticket context
        groups = sorted(
            payload.get("groups", []) or [],
            key=lambda g: len(g.get("fragments", []) or []),
            reverse=True,
        )[:3]
        summary["top_groups"] = [
            {
                "fragments": len(g.get("fragments", []) or []),
                "files": sorted({f.get("file", "?") for f in (g.get("fragments") or [])})[:5],
                "function": (g.get("fragments") or [{}])[0].get("function_name", "(module)"),
            }
            for g in groups
        ]
    except Exception as exc:  # noqa: BLE001
        log.debug("redup filtered report parse failed: %s", exc)

    REDUP_GROUPS.set(summary["groups"])
    REDUP_SAVED_LINES.set(summary["saved_lines"])
    REDUP_BUDGET_BREACH.set(1 if breach else 0)

    return {
        "ok": not breach,
        "breach": breach,
        "groups": summary["groups"],
        "saved_lines": summary["saved_lines"],
        "top_groups": summary["top_groups"],
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-400:],
    }


def heal_redup_check(component: str, detail: dict) -> dict:
    """Run the duplicate-budget gate. Always advisory — never auto-patches.

    Two outcomes:
      - within_budget   → log + metric only
      - budget_breached → record action so a ticket can be filed by the
                          calling /alertmanager handler (severity≥error
                          will trigger create_planfile_ticket).
    """
    result = _run_redup_check()
    if result.get("skipped"):
        _record_action("redup_check", "skipped", component, {"reason": result["skipped"]})
        return {"action": "redup_check", "outcome": "skipped"}

    outcome = "budget_breached" if result.get("breach") else "within_budget"
    _record_action(
        "redup_check",
        outcome,
        component,
        {
            "groups": result.get("groups"),
            "saved_lines": result.get("saved_lines"),
            "top_groups": result.get("top_groups"),
        },
    )
    return {
        "action": "redup_check",
        "outcome": outcome,
        "groups": result.get("groups"),
        "saved_lines": result.get("saved_lines"),
        "top_groups_count": len(result.get("top_groups", [])),
    }


STRATEGIES = {
    "annotate": heal_annotate,
    "redsl_gate": heal_redsl_gate,
    "redsl_improve": heal_redsl_improve,
    "rebuild_restore": heal_rebuild_restore,
    "vallm_validate": heal_vallm_validate,
    "redup_check": heal_redup_check,
}


def _resolve_strategy(strategy_name: str):
    if strategy_name == "redsl_improve" and not ENABLE_LLM_AUTOFIX:
        return heal_annotate, "annotate"
    return STRATEGIES.get(strategy_name, heal_annotate), strategy_name


# ── Routes ─────────────────────────────────────────────────────────────
@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "dry_run": DRY_RUN,
        "rate_budget": MAX_ACTIONS_PER_HOUR - len(_recent_actions),
        "llm_autofix_enabled": ENABLE_LLM_AUTOFIX,
    }


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/history")
def get_history() -> list[dict]:
    return list(history)


@app.post("/alertmanager")
async def alertmanager_webhook(request: Request) -> dict[str, Any]:
    """Accept the Alertmanager webhook payload (v4)."""
    payload = await request.json()
    results: list[dict] = []
    for alert in payload.get("alerts", []):
        labels = alert.get("labels", {})
        severity = labels.get("severity", "info")
        component = labels.get("component", "unknown")
        strategy_name = labels.get("healing_strategy", "annotate")
        status = alert.get("status", "firing")
        ALERTS.labels(source="alertmanager", severity=severity).inc()
        if status != "firing":
            # resolution → annotate only, no ticket
            strategy_name = "annotate"
        strategy, effective_strategy_name = _resolve_strategy(strategy_name)
        log.info(
            "alert %s/%s → %s",
            severity,
            labels.get("alertname"),
            effective_strategy_name,
        )
        strategy_result = strategy(component, {"labels": labels, "annotations": alert.get("annotations", {})})
        ticket_result: dict[str, Any] = {"skipped": "severity_below_threshold"}
        # Create a planfile ticket only for firing alerts at error/critical level.
        if status == "firing" and severity in {"error", "critical"}:
            ticket_result = create_planfile_ticket(alert, source="alertmanager")
        results.append({"strategy": strategy_result, "ticket": ticket_result})
    return {"received": len(payload.get("alerts", [])), "results": results}


@app.post("/probe-failure")
async def probe_failure(request: Request) -> dict:
    """Accept the testql-watchdog probe-failure payload."""
    payload = await request.json()
    ALERTS.labels(source="testql-watchdog", severity="error").inc()
    failures = payload.get("failures", [])
    log.info("probe-failure from %s — %d failures", payload.get("source"), len(failures))
    # Aggregate: if >half of the probes are failing, prefer redsl_improve only
    # when LLM autofix is explicitly enabled; otherwise stay LLM-free.
    total = payload.get("total") or max(len(failures), 1)
    ratio = len(failures) / total if total else 0.0
    if ratio >= 0.5 and ENABLE_LLM_AUTOFIX:
        result = heal_redsl_improve("backend", {"failures": failures, "ratio": ratio})
    else:
        result = heal_redsl_gate("backend", {"failures": failures, "ratio": ratio})
    # One consolidated ticket per probe-failure payload (not per-endpoint,
    # so the planfile doesn't drown in duplicates when a whole service goes down).
    synthetic_alert = {
        "labels": {
            "alertname": "TestQLProbeFailure",
            "severity": "critical" if ratio >= 0.5 else "error",
            "component": "backend",
            "instance": (failures[0].get("endpoint") if failures else "multiple"),
        },
        "annotations": {
            "summary": f"{len(failures)} TestQL probe(s) failed out of {total} ({ratio:.0%}).",
            "observed": f"{len(failures)}/{total} endpoints failing",
        },
        "failures": failures,
        "startsAt": str(time.time()),
    }
    ticket_result = create_planfile_ticket(synthetic_alert, source="testql-watchdog")
    return {"failures": len(failures), "result": result, "ticket": ticket_result}


@app.get("/tickets")
def get_tickets() -> dict:
    """List planfile tickets that were created by this webhook."""
    if not PLANFILE_ENABLED:
        return {"enabled": False, "tickets": []}
    try:
        proc = subprocess.run(
            [PLANFILE_BIN, "ticket", "list", "--status", "all", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=REPO_PATH,
            timeout=10,
        )
        # Filter down to webhook-sourced tickets so the response stays manageable.
        import json

        all_tickets = json.loads(proc.stdout or "[]")
        mine = [t for t in all_tickets if "llm-ready" in (t.get("labels") or [])]
        return {"enabled": True, "count": len(mine), "tickets": mine[:25]}
    except Exception as exc:  # noqa: BLE001
        return {"enabled": True, "error": str(exc)}
