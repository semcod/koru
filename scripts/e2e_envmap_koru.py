#!/usr/bin/env python3
"""Compare Koru resolution with vs without env2llm+nlp2uri stack on the koru repo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

KORU_ROOT = Path(__file__).resolve().parents[1]


def _section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    from koruapi import desktop_uri, env2llm_registry

    _section("Dependencies")
    print(f"nlp2uri available: {desktop_uri.nlp2uri_available()}")
    print(f"env2llm available: {env2llm_registry.env2llm_available()}")
    if not desktop_uri.nlp2uri_available():
        print("SKIP: install koru[desktop]")
        return 1

    _section("1. env2llm refresh registry for koru")
    if not env2llm_registry.env2llm_available():
        print("env2llm missing — desktop-only mode")
        registry_path = None
    else:
        refresh = env2llm_registry.env2llm_refresh_registry(
            project_root=str(KORU_ROOT),
            probe_desktop=True,
            publish_mqtt=False,
        )
        print(json.dumps({k: refresh[k] for k in ("ok", "path", "command_count", "example_id")}, indent=2))
        registry_path = refresh.get("path")

    _section("2. URI index (nlp2uri over SystemMapIR)")
    if env2llm_registry.env2llm_available():
        uris = env2llm_registry.env2llm_list_uris(project_root=str(KORU_ROOT))
        if uris.get("ok"):
            entries = uris.get("entries") or {}
            kinds: dict[str, int] = {}
            for entry in entries.values():
                kind = entry.get("kind", "unknown")
                kinds[kind] = kinds.get(kind, 0) + 1
            print(f"URI entries: {len(entries)}")
            print(f"By kind: {json.dumps(kinds, indent=2)}")
            desktop = [e for e in entries.values() if e.get("kind", "").startswith("desktop")]
            if desktop:
                sample = desktop[0]
                print(f"Sample desktop URI: {sample.get('uri')} ({sample.get('name')})")
        else:
            print(json.dumps(uris, indent=2))

    _section("3. NL resolve — WITHOUT system map (desktop fallback only)")
    prompts = [
        "run quality gates",
        "list tickets",
        "run ticket",
        "focus firefox window",
        "capture screen",
    ]
    for prompt in prompts:
        out = desktop_uri.desktop_uri_resolve_system_map(
            prompt,
            fallback_desktop=True,
        )
        print(
            f"  [{prompt!r}] -> source={out.get('source')} "
            f"uri={out.get('uri', out.get('error', 'none'))}"
        )

    _section("4. NL resolve — WITH env2llm registry (command:// aware)")
    if registry_path:
        for prompt in prompts:
            out = desktop_uri.desktop_uri_resolve_system_map(
                prompt,
                doql_path=registry_path,
                fallback_desktop=True,
            )
            print(
                f"  [{prompt!r}] -> source={out.get('source')} "
                f"uri={out.get('uri', out.get('error', 'none'))}"
            )
    else:
        print("  (skipped — no registry)")

    _section("5. Desktop-only baseline (nlp2uri plan)")
    for prompt in ["focus firefox window", "capture screen", "open settings"]:
        plan = desktop_uri.desktop_uri_plan(prompt, platform="linux")
        uri = (plan.get("plan") or {}).get("uri") if plan.get("ok") else plan.get("error")
        print(f"  [{prompt!r}] -> {uri}")

    _section("6. MCP tool smoke (koru_env2llm_get_registry)")
    try:
        from koruapi.mcp_server_env2llm import tool_env2llm_get_registry

        mcp_out = tool_env2llm_get_registry({"project_root": str(KORU_ROOT)})
        reg = (mcp_out.get("registry") or {}) if mcp_out.get("ok") else {}
        print(
            json.dumps(
                {
                    "ok": mcp_out.get("ok"),
                    "project_id": mcp_out.get("project_id"),
                    "commands": len(reg.get("commands") or []),
                    "runtimes": len(reg.get("runtimes") or []),
                    "has_desktop": reg.get("desktop") is not None,
                },
                indent=2,
            )
        )
    except Exception as exc:
        print(f"  MCP smoke failed: {exc}")

    _section("Summary")
    print(
        "Stack improves Koru when agents need command:// workflow URIs from the live\n"
        "registry instead of guessing desktop URIs. Desktop NL still uses nlp2uri.\n"
        "See section 3 vs 4 for resolution differences on the same prompts."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
