#!/usr/bin/env python3
"""Scaffold a per-IDE koru autopilot VSIX from the umbrella vscode plugin.

Usage:
    python3 scripts/scaffold-ide-plugin.py vscodium
    python3 scripts/scaffold-ide-plugin.py windsurf
    python3 scripts/scaffold-ide-plugin.py antigravity
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC_PLUGIN = REPO / "plugins" / "koru-autopilot-vscode"

# IDE id → (appName guard substring(s), strategy module, optional test modules)
IDE_CONFIG: dict[str, dict[str, object]] = {
    "vscodium": {
        "dir": "koru-autopilot-vscodium",
        "display": "koru autopilot (VSCodium)",
        "keywords": ["koru", "autopilot", "vscodium", "codium", "automation"],
        "strategy": "vscodium",
        "tests": ["vscodium.test.ts"],
        "guard": 'appName.toLowerCase().includes("vscodium") || appName.toLowerCase().includes("code - oss") || appName.toLowerCase().includes("code-oss")',
        "guard_label": "VSCodium / Code - OSS",
    },
    "windsurf": {
        "dir": "koru-autopilot-windsurf",
        "display": "koru autopilot (Windsurf)",
        "keywords": ["koru", "autopilot", "windsurf", "cascade", "automation"],
        "strategy": "windsurf",
        "tests": [],
        "guard": 'appName.toLowerCase().includes("windsurf")',
        "guard_label": "Windsurf",
    },
    "antigravity": {
        "dir": "koru-autopilot-antigravity",
        "display": "koru autopilot (Antigravity)",
        "keywords": ["koru", "autopilot", "antigravity", "automation"],
        "strategy": "antigravity",
        "tests": [],
        "guard": 'appName.toLowerCase().includes("antigravity")',
        "guard_label": "Antigravity",
    },
}

KEEP_IDE_FILES = {"ide-strategy.ts", "index.ts", "registry.ts"}


def _write_registry(dest: Path, strategy: str) -> None:
    text = f'''/**
 * Per-IDE strategy registry — ``{strategy}`` only.
 */

import type {{ IdeStrategy }} from "./ide-strategy";

const REGISTRY = new Map<string, IdeStrategy>();

export function registerStrategy(strategy: IdeStrategy, opts: {{ override?: boolean }} = {{}}): void {{
  const id = strategy.id;
  if (!id) throw new Error("IdeStrategy.id must be a non-empty string");
  if (!opts.override && REGISTRY.has(id)) {{
    throw new Error(`IdeStrategy for ${{id}} already registered`);
  }}
  REGISTRY.set(id, strategy);
}}

export function getStrategy(id: string | undefined): IdeStrategy | undefined {{
  if (!id) return undefined;
  return REGISTRY.get(id.toLowerCase());
}}

export function allStrategies(): IdeStrategy[] {{
  return [...REGISTRY.values()];
}}

export function detectIdeViaStrategies(appName: string): string | undefined {{
  for (const strat of REGISTRY.values()) {{
    const id = strat.detectIde(appName);
    if (id) return id;
  }}
  return undefined;
}}

export function bootstrapStrategies(): void {{
  for (const mod of ["./{strategy}"]) {{
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require(mod);
  }}
}}

bootstrapStrategies();
'''
    (dest / "src" / "ides" / "registry.ts").write_text(text, encoding="utf-8")


def _write_chat_history_adapters(dest: Path, ide: str) -> None:
    class_name = {
        "vscodium": "VSCodeChatSessionAdapter",
        "windsurf": "UnsupportedAdapter",
        "antigravity": "UnsupportedAdapter",
    }[ide]
    import_line = {
        "vscodium": 'import { VSCodeChatSessionAdapter } from "./vscode-chat-session-adapter";',
        "windsurf": 'import { UnsupportedAdapter } from "./unsupported-chat-adapter";',
        "antigravity": 'import { UnsupportedAdapter } from "./unsupported-chat-adapter";',
    }[ide]
    if ide == "vscodium":
        body = f'''/**
 * VSCodium-only chat-history adapter factory.
 */

{import_line}
import type {{ IdeAdapter, SupportedIde }} from "./chat-history-types";

export {{ VSCodeChatSessionAdapter, parseVSCodeChatIndex }} from "./vscode-chat-session-adapter";

export function buildAdapterForIde(ide: SupportedIde): IdeAdapter {{
  if (ide !== "vscodium" && ide !== "vscode") {{
    throw new Error(
      `koru-autopilot-vscodium: unexpected IDE ${{ide}} — this VSIX only ships VSCodium support.`
    );
  }}
  return new VSCodeChatSessionAdapter({{ ide: "vscodium" }});
}}
'''
    else:
        reason = (
            "Cascade conversations are stored encrypted; no readable text."
            if ide == "windsurf"
            else "Antigravity conversations are stored encrypted; no readable text."
        )
        body = f'''/**
 * {ide.title()}-only chat-history adapter factory.
 */

{import_line}
import type {{ IdeAdapter, SupportedIde }} from "./chat-history-types";

export {{ UnsupportedAdapter }} from "./unsupported-chat-adapter";

export function buildAdapterForIde(ide: SupportedIde): IdeAdapter {{
  if (ide !== "{ide}") {{
    throw new Error(
      `koru-autopilot-{ide}: unexpected IDE ${{ide}} — this VSIX only ships {ide.title()} support.`
    );
  }}
  return new UnsupportedAdapter("{ide}", "{reason}");
}}
'''
    (dest / "src" / "chat-history-adapters.ts").write_text(body, encoding="utf-8")


def _patch_extension_activate(dest: Path, cfg: dict[str, object]) -> None:
    ide = cfg["strategy"]
    guard = cfg["guard"]
    label = cfg["guard_label"]
    path = dest / "src" / "extension.ts"
    text = path.read_text(encoding="utf-8")
    # Remove cursor-only guard if present from copy
    text = re.sub(
        r"  // Cursor now has its own dedicated VSIX.*?\n    return;\n  \}\n",
        "",
        text,
        flags=re.DOTALL,
    )
    insert = f'''  // ``koru-autopilot-{ide}`` is a {label}-only VSIX.
  if (!({guard})) {{
    console.warn(
      `koru-autopilot-{ide}: not activating (appName="${{appName}}"; ` +
      "install the matching koru-autopilot-<ide> VSIX for this IDE)."
    );
    return;
  }}
'''
    text = text.replace(
        "  const bridge = new AutopilotBridge(context);",
        insert + "  const bridge = new AutopilotBridge(context);",
        1,
    )
    # The hello payload looks up the plugin's own version via the extension API.
    # The vscode template hard-codes the umbrella ID; switch each per-IDE
    # plugin to its dedicated ID so the daemon never sees ``version=unknown``.
    text = text.replace(
        'vscode.extensions.getExtension("semcod.koru-autopilot-vscode")',
        f'vscode.extensions.getExtension("semcod.koru-autopilot-{ide}")',
    )
    path.write_text(text, encoding="utf-8")


def _write_package_json(dest: Path, cfg: dict[str, object], version: str) -> None:
    ide = cfg["strategy"]
    dir_name = cfg["dir"]
    pkg = json.loads((SRC_PLUGIN / "package.json").read_text(encoding="utf-8"))
    pkg["name"] = dir_name
    pkg["displayName"] = cfg["display"]
    pkg["description"] = (
        f"Bridge between {cfg['guard_label']} and the koru autopilot daemon. "
        f"Standalone VSIX for {cfg['guard_label']} only — sibling packages "
        "cover other IDEs so regressions cannot leak across runtimes."
    )
    pkg["version"] = version
    pkg["repository"]["directory"] = f"plugins/{dir_name}"
    pkg["homepage"] = f"https://github.com/semcod/koru/tree/main/plugins/{dir_name}#readme"
    pkg["keywords"] = cfg["keywords"]
    pkg["contributes"]["title"] = cfg["display"]
    pkg["scripts"] = {
        "prebuild": f"python3 ../../scripts/sync-plugin-shared.py --plugin {dir_name}",
        "precompile": f"python3 ../../scripts/sync-plugin-shared.py --plugin {dir_name}",
        "compile": "tsc -p ./",
        "pretest": f"python3 ../../scripts/sync-plugin-shared.py --plugin {dir_name}",
        "test": _test_script(cfg),
        "watch": "tsc -watch -p ./",
        "vscode:prepublish": "npm run compile",
        "prepackage": (
            f"python3 ../../scripts/sync-plugin-version.py --plugin {dir_name} && "
            f"python3 ../../scripts/sync-plugin-shared.py --plugin {dir_name} && "
            f"python3 ../../scripts/sync-plugin-build.py --plugin {dir_name}"
        ),
        "package": f"vsce package --no-dependencies --out {dir_name}-${{npm_package_version}}.vsix",
        "prepublish": (
            f"python3 ../../scripts/sync-plugin-version.py --plugin {dir_name} && "
            f"python3 ../../scripts/sync-plugin-build.py --plugin {dir_name}"
        ),
        "publish": "vsce publish --no-dependencies",
        "clean": "rm -rf out node_modules src/_shared *.vsix",
    }
    (dest / "package.json").write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")


def _test_script(cfg: dict[str, object]) -> str:
    base = (
        "npm run compile && node out/dispatch-plan.test.js && "
        "node out/probe-ladder.test.js && node out/step-decisions.test.js && "
        "node out/host-click-submit.test.js && node out/chat-history-watcher.test.js && "
        "node out/ack-payload.test.js"
    )
    extra: list[str] = []
    for t in cfg.get("tests", []):
        extra.append(f"node out/ides/{t.replace('.ts', '.js')}")
    if cfg["strategy"] == "antigravity":
        extra.append("node out/antigravity-fastpath.test.js")
    if extra:
        return base + " && " + " && ".join(extra)
    return base


def scaffold(ide: str) -> None:
    if ide not in IDE_CONFIG:
        print(f"unknown ide: {ide}", file=sys.stderr)
        sys.exit(1)
    cfg = IDE_CONFIG[ide]
    dest = REPO / "plugins" / cfg["dir"]
    if dest.exists():
        print(f"already exists: {dest}", file=sys.stderr)
        sys.exit(1)

    shutil.copytree(
        SRC_PLUGIN,
        dest,
        ignore=shutil.ignore_patterns("node_modules", "out", "*.vsix", "package-lock.json", "src/_shared"),
    )

    # Drop unrelated IDE strategies
    ides_dir = dest / "src" / "ides"
    keep = {f"{cfg['strategy']}.ts"} | {f"{cfg['strategy']}.test.ts" for _ in [0]} | KEEP_IDE_FILES
    for f in ides_dir.glob("*.ts"):
        if f.name not in keep:
            f.unlink()

    version = json.loads((SRC_PLUGIN / "package.json").read_text())["version"]
    _write_registry(dest, str(cfg["strategy"]))
    _write_chat_history_adapters(dest, ide)
    _patch_extension_activate(dest, cfg)
    _write_package_json(dest, cfg, version)

    gitignore = dest / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "node_modules/\nout/\n*.vsix\nsrc/_shared/\n",
            encoding="utf-8",
        )

    print(f"scaffolded plugins/{cfg['dir']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ide", choices=sorted(IDE_CONFIG))
    args = parser.parse_args()
    scaffold(args.ide)
    return 0


if __name__ == "__main__":
    sys.exit(main())
