"""Static audit of process-expectation contracts (read-only).

A process envelope declares expectations such as ``expected: {ok: true}`` that a
verifier later checks against the observation of the step named in ``verified_by``.
The reference verifier (``receiptsVerifyExpectation`` in subactor/core) treats an
object ``expected`` as a *subset* of one receipt's ``observation.value``. An
expectation whose keys the verifying producer never emits can therefore never pass,
and the owning process fails on every cycle.

Rules:

* **S1** - no ``verified_by`` and no ``verified_by_control``.
* **S2** - ``expected`` is an empty object, which the verifier always rejects.
* **S3** - orphan key: no source file outside the declaration and tests contains it.
* **S4** - co-production: the producer of the verifying URI never emits all keys of
  one expectation (camelCase and snake_case are normalised).
* **S5** (informational) - control-only expectation, rejected by the completion check.
* **S4-unresolved** (informational) - the verifying URI cannot be resolved statically.

The audit only reads files. It writes a JSON report that ``koru scan
--semcod-artifacts`` turns into one ticket (signal ``expectation_contract``).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "koru.expectation-audit/v1"
DEFAULT_REPORT = ".expectation-audit/report.json"
ACTIONABLE = frozenset({"S1", "S2", "S3", "S4"})
_SKIP_DIRS = frozenset({".git", "node_modules", ".worktrees", "dist", ".venv", "__pycache__", "cache", "runs"})
_SOURCE_EXT = (".mjs", ".js", ".ts", ".py")
_KEY_RE = re.compile(r"""(?<![\w.])["']?([A-Za-z_][A-Za-z0-9_]*)["']?\s*:""")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_MIN_KEY_LEN = 4


def _walk(root: Path, exts: tuple[str, ...] = _SOURCE_EXT) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in _SKIP_DIRS]
        for name in filenames:
            if name.endswith(exts):
                yield Path(dirpath) / name


def _is_test(path: Path) -> bool:
    text = path.as_posix()
    markers = ("/test/", "/tests/", "/test_")
    return any(marker in text for marker in markers) or text.endswith((".test.mjs", ".test.js", "_test.py"))


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _norm(name: str) -> str:
    return re.sub(r"[_\-\s]", "", name).lower()


def _top_level_keys(text: str) -> list[str]:
    depth = 0
    kept: list[str] = []
    for char in text:
        if char in "{[":
            depth += 1
        elif char in "}]":
            if depth == 0:
                break
            depth -= 1
        kept.append(char if depth == 0 else " ")
    return [match.group(1) for match in _KEY_RE.finditer("".join(kept))]


_ARRAY_CONST_RE = re.compile(r"""(?:const|let|var)\s+([A-Z_][A-Z0-9_]*)\s*=\s*(?:Object\.freeze\(\s*)?\[([^\]]*)\]""")


def _constants(text: str) -> dict[str, str | list[str]]:
    """String constants and arrays of string literals (``const NAME = Object.freeze([...])``)."""
    found: dict[str, str | list[str]] = dict(
        re.findall(r"""(?:const|let|var)\s+([A-Z_][A-Z0-9_]*)\s*=\s*["']([^"']+)["']""", text)
    )
    for name, body in _ARRAY_CONST_RE.findall(text):
        items = re.findall(r"""["']([^"']+)["']""", body)
        if items:
            found[name] = items
    return found


def _lookup(value: str, constants: dict[str, str | list[str]]) -> str:
    """Resolve ``"literal"``, ``NAME`` and ``NAME[3]`` to a URI string ('' when unknown)."""
    if value[0] in "\"'":
        return value.strip("\"'")
    indexed = re.fullmatch(r"([A-Za-z_]\w*)\[(\d+)\]", value)
    if indexed:
        items = constants.get(indexed.group(1))
        position = int(indexed.group(2))
        return items[position] if isinstance(items, list) and position < len(items) else ""
    resolved = constants.get(value)
    return resolved if isinstance(resolved, str) else ""


def _resolve_uris(text: str, step_id: str, constants: dict[str, str | list[str]]) -> list[str]:
    pattern = re.compile(
        r"""\bid\s*:\s*["']"""
        + re.escape(step_id)
        + r"""["'][^{}]{0,500}?\buri\s*:\s*("[^"]+"|'[^']+'|[A-Za-z_]\w*(?:\[\d+\])?)"""
    )
    return [uri for uri in (_lookup(match.group(1), constants) for match in pattern.finditer(text)) if uri]


def _uri_tail(uri: str) -> str | None:
    match = re.match(r"^[a-z0-9+.-]+://[^/]+/(.+)$", uri)
    return match.group(1) if match else None


def source_expectations(roots: Sequence[Path]) -> list[dict[str, Any]]:
    """Find ``expected: {...}`` declarations in consumer sources."""
    pattern = re.compile(r"\b(?:expected|expect)\s*:\s*\{")
    found: list[dict[str, Any]] = []
    for root in roots:
        for path in _walk(root):
            if _is_test(path) or not path.name.endswith((".mjs", ".js", ".ts")):
                continue
            text = _read(path)
            constants = _constants(text)
            for match in pattern.finditer(text):
                tail = text[match.end() : match.end() + 900]
                verified = re.search(r"verified_by\s*:\s*\[([^\]]*)\]", tail)
                step_ids = re.findall(r"""["']([\w.-]+)["']""", verified.group(1)) if verified else []
                control = "verified_by_control" in tail[:500] and not step_ids
                context = text[max(0, match.start() - 200) : match.start()]
                ids = re.findall(r"""\bid\s*:\s*["']([\w.-]+)["']""", context)
                uris: list[str] = []
                for step_id in step_ids:
                    uris.extend(_resolve_uris(text, step_id, constants))
                found.append(
                    {
                        "path": path.as_posix(),
                        "line": text.count("\n", 0, match.start()) + 1,
                        "id": ids[-1] if ids else None,
                        "keys": _top_level_keys(text[match.end() : match.end() + 600]),
                        "verified_by": step_ids,
                        "control": control,
                        "uris": sorted(set(uris)),
                    }
                )
    return found


def _ticket_findings(tickets: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    findings: list[dict[str, Any]] = []
    declared: dict[str, list[str]] = defaultdict(list)
    for ticket in tickets:
        manifest = ((ticket.get("inputs") or {}).get("process_manifest")) or {}
        for item in (manifest.get("definitions") or {}).get("eql") or []:
            if not isinstance(item, dict):
                continue
            where = f"ticket {ticket.get('id')}"
            expected = item.get("expected", item.get("expect", True))
            steps = item.get("verified_by") or []
            if not steps and item.get("verified_by_control"):
                findings.append({"rule": "S5", "where": where, "id": item.get("id")})
            elif not steps:
                findings.append({"rule": "S1", "where": where, "id": item.get("id")})
            if expected == {}:
                findings.append({"rule": "S2", "where": where, "id": item.get("id")})
            if isinstance(expected, dict):
                for key in expected:
                    declared[str(key)].append(where)
    return findings, declared


def audit(
    tickets: Sequence[dict[str, Any]],
    consumer_roots: Sequence[Path],
    producer_roots: Sequence[Path],
) -> dict[str, Any]:
    """Return the report dict: actionable ``findings`` and ``informational`` entries."""
    findings, declared = _ticket_findings(tickets)
    sources = source_expectations(consumer_roots)
    own_declarations: Counter[str] = Counter()
    for entry in sources:
        for key in entry["keys"]:
            declared[key].append(f"{entry['path']}:{entry['line']}")
            own_declarations[_norm(key)] += 1

    wanted = {key for key in declared if len(key) >= _MIN_KEY_LEN}
    occurrences: Counter[str] = Counter()
    seen: set[Path] = set()
    for root in [*consumer_roots, *producer_roots]:
        for path in _walk(root):
            resolved = path.resolve()
            if _is_test(path) or resolved in seen:
                continue
            seen.add(resolved)
            occurrences.update(_norm(token) for token in _IDENT_RE.findall(_read(path)))
    for key in sorted(wanted):
        if occurrences[_norm(key)] - own_declarations[_norm(key)] <= 0:
            findings.append({"rule": "S3", "where": declared[key][0], "key": key})

    producers: dict[Path, tuple[str, set[str]]] = {}
    for root in producer_roots:
        for path in _walk(root, (".py", ".mjs", ".js")):
            if not _is_test(path):
                text = _read(path)
                producers[path] = (text, {_norm(token) for token in _IDENT_RE.findall(text)})
    for entry in sources:
        if entry["control"] or not entry["verified_by"]:
            continue
        keys = [key for key in entry["keys"] if len(key) >= _MIN_KEY_LEN]
        if not keys:
            continue
        where = f"{entry['path']}:{entry['line']}"
        if not entry["uris"]:
            findings.append({"rule": "S4-unresolved", "where": where, "id": entry["id"]})
            continue
        for uri in entry["uris"]:
            tail = _uri_tail(uri)
            candidates = [path for path, (text, _) in producers.items() if tail and tail in text]
            if not candidates:
                findings.append({"rule": "S4-unresolved", "where": where, "id": entry["id"], "uri": uri})
                continue
            best_path, missing = min(
                ((path, [key for key in keys if _norm(key) not in producers[path][1]]) for path in candidates),
                key=lambda pair: len(pair[1]),
            )
            if missing:
                findings.append(
                    {
                        "rule": "S4",
                        "where": where,
                        "id": entry["id"],
                        "uri": uri,
                        "missing_keys": missing,
                        "closest_producer": best_path.as_posix(),
                    }
                )

    actionable = [item for item in findings if item["rule"] in ACTIONABLE]
    informational = [item for item in findings if item["rule"] not in ACTIONABLE]
    return {
        "schema": SCHEMA,
        "summary": {
            "tickets_scanned": len(tickets),
            "expectations_in_source": len(sources),
            "by_rule": dict(Counter(item["rule"] for item in findings)),
        },
        "findings": actionable,
        "informational": informational,
    }


def _load_tickets(json_path: str | None, url: str | None) -> list[dict[str, Any]]:
    if json_path:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    elif url:
        with urllib.request.urlopen(url.rstrip("/") + "/tickets?limit=5000", timeout=60) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
    else:
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit process-expectation contracts.")
    parser.add_argument("--project", default=".", help="Directory that receives the report.")
    parser.add_argument("--consumer", action="append", default=[], help="Source root that declares expectations.")
    parser.add_argument("--producer", action="append", default=[], help="Source root of the verifying producers.")
    parser.add_argument("--planfile-json", help="Planfile tickets exported as a JSON list.")
    parser.add_argument("--planfile-url", help="Planfile REST base URL (read-only GET /tickets).")
    parser.add_argument("--out", help=f"Report path (default: <project>/{DEFAULT_REPORT}).")
    args = parser.parse_args(argv)
    report = audit(
        _load_tickets(args.planfile_json, args.planfile_url),
        [Path(item) for item in args.consumer],
        [Path(item) for item in args.producer],
    )
    out = Path(args.out) if args.out else Path(args.project) / DEFAULT_REPORT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(report["summary"], ensure_ascii=False) + "\n")
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
