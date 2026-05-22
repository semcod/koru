"""Packaged strategy templates and optional remote strategies fetch."""

from __future__ import annotations

import hashlib
import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_MAX_REMOTE_BYTES = 1_048_576  # 1 MiB
_REMOTE_TIMEOUT_SEC = 5
_CACHE_DIR = Path.home() / ".cache" / "koru" / "wizard"


@dataclass(frozen=True)
class TemplateInfo:
    """One entry from ``templates/registry.json``."""

    name: str
    description: str
    path: Path


def _wizard_package_root() -> Path:
    return Path(str(resources.files("koru.wizard")))


def _templates_dir() -> Path:
    return _wizard_package_root() / "templates"


def _load_registry() -> dict[str, Any]:
    with resources.files("koru.wizard").joinpath("templates/registry.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def _pick_description(raw: dict[str, Any], language: str = "pl") -> str:
    desc = raw.get("description")
    if isinstance(desc, dict):
        return str(desc.get(language) or desc.get("en") or desc.get("pl") or "")
    return str(desc or "")


def list_templates(*, language: str = "pl") -> list[TemplateInfo]:
    """Return built-in template names with human-readable descriptions."""
    registry = _load_registry()
    entries = registry.get("templates") or {}
    result: list[TemplateInfo] = []
    for name in sorted(entries.keys()):
        raw = entries[name]
        if not isinstance(raw, dict):
            continue
        rel_file = str(raw.get("file") or "")
        path = _resolve_packaged_file(rel_file)
        result.append(
            TemplateInfo(
                name=name,
                description=_pick_description(raw, language),
                path=path,
            )
        )
    return result


def _resolve_packaged_file(rel_file: str) -> Path:
    """Resolve a registry ``file`` path relative to the wizard package root."""
    if not rel_file:
        raise ValueError("template registry entry missing 'file'")
    root = _wizard_package_root().resolve()
    candidate = (root / rel_file).resolve()
    if not str(candidate).startswith(str(root)):
        raise ValueError(f"template path escapes package root: {rel_file!r}")
    if not candidate.is_file():
        raise FileNotFoundError(f"template file not found: {candidate}")
    return candidate


def resolve_template_name(name: str) -> Path:
    """Load a packaged template by registry name (e.g. ``web-app``)."""
    registry = _load_registry()
    entries = registry.get("templates") or {}
    raw = entries.get(name)
    if not isinstance(raw, dict):
        known = ", ".join(sorted(entries.keys()))
        raise KeyError(f"unknown template {name!r}; known: {known}")
    return _resolve_packaged_file(str(raw["file"]))


def is_https_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def fetch_remote_strategies(url: str, *, allow_remote: bool) -> Path:
    """Download ``url`` (HTTPS only), cache under ``~/.cache/koru/wizard/``."""
    if not allow_remote:
        raise ValueError(
            "HTTPS strategies URL requires --allow-remote "
            "(refuses fetching arbitrary remote JSON otherwise)"
        )
    if not is_https_url(url):
        raise ValueError(f"only https:// URLs are supported, got: {url!r}")

    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _CACHE_DIR / f"{digest}.json"

    if cache_path.is_file():
        return cache_path

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "koru-wizard/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=_REMOTE_TIMEOUT_SEC, context=ssl.create_default_context()
        ) as response:
            raw = response.read(_MAX_REMOTE_BYTES + 1)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to fetch strategies from {url!r}: {exc}") from exc

    if len(raw) > _MAX_REMOTE_BYTES:
        raise ValueError(
            f"remote strategies exceed {_MAX_REMOTE_BYTES} bytes (limit 1 MiB): {url!r}"
        )

    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"remote strategies are not valid JSON: {url!r}") from exc

    if not isinstance(payload, dict) or "nodes" not in payload:
        raise ValueError(f"remote strategies missing 'nodes' object: {url!r}")

    cache_path.write_bytes(raw)
    return cache_path


def resolve_strategies_source(
    *,
    strategies: str | Path | None,
    template: str | None,
    allow_remote: bool,
) -> Path:
    """Resolve CLI ``--strategies`` / ``--template`` to a local JSON path.

    Raises ``ValueError`` when ``--template`` and ``--strategies`` are both set,
    or when a HTTPS URL is passed without ``--allow-remote``.
    """
    if template and strategies is not None:
        raise ValueError("--template and --strategies are mutually exclusive")

    if template:
        return resolve_template_name(template)

    if strategies is None:
        return _wizard_package_root() / "strategies.json"

    spec = str(strategies).strip()
    if _looks_like_url(spec):
        if not is_https_url(spec):
            raise ValueError(f"only https:// URLs are supported, got: {spec!r}")
        return fetch_remote_strategies(spec, allow_remote=allow_remote)

    path = Path(spec).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"strategies file not found: {path}")
    return path.resolve()


def format_templates_list(*, language: str = "pl") -> str:
    """Human-readable listing for ``koru wizard --list-templates``."""
    lines = ["Built-in templates:"]
    for info in list_templates(language=language):
        lines.append(f"  {info.name:<14} — {info.description}")
    lines.append("")
    lines.append("Use: koru wizard --template <name>")
    lines.append("Remote: koru wizard --strategies https://... --allow-remote")
    return "\n".join(lines)
