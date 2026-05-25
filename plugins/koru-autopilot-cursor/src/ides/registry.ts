/**
 * Lightweight per-IDE strategy registry.
 *
 * Strategies self-register at import time. Callers must use `getStrategy`
 * (returns `undefined` for IDEs without a dedicated module) so the legacy
 * fall-through code in `probe-ladder.ts` / `extension.ts` keeps working
 * for IDEs that have not been extracted yet.
 */

import type { IdeStrategy } from "./ide-strategy";

const REGISTRY = new Map<string, IdeStrategy>();

export function registerStrategy(strategy: IdeStrategy, opts: { override?: boolean } = {}): void {
  const id = strategy.id;
  if (!id) {
    throw new Error("IdeStrategy.id must be a non-empty string");
  }
  if (!opts.override && REGISTRY.has(id)) {
    throw new Error(`IdeStrategy for ${id} already registered`);
  }
  REGISTRY.set(id, strategy);
}

export function getStrategy(id: string | undefined): IdeStrategy | undefined {
  if (!id) return undefined;
  return REGISTRY.get(id.toLowerCase());
}

export function allStrategies(): IdeStrategy[] {
  return [...REGISTRY.values()];
}

export function detectIdeViaStrategies(appName: string): string | undefined {
  for (const strat of REGISTRY.values()) {
    const id = strat.detectIde(appName);
    if (id) return id;
  }
  return undefined;
}

/**
 * Eager-load per-IDE strategy modules so they self-register before any
 * caller asks for them.
 *
 * This plugin ships only the Cursor strategy by design. Each other
 * IDE has its own standalone VSIX (``koru-autopilot-vscode``,
 * ``koru-autopilot-vscodium``, ``koru-autopilot-windsurf``,
 * ``koru-autopilot-antigravity``) so a regression here cannot leak
 * into another IDE's runtime.
 */
export function bootstrapStrategies(): void {
  // The require() form means TypeScript compiles to commonjs and each
  // strategy's top-level `registerStrategy(...)` call runs once.
  for (const mod of [
    "./cursor",
  ]) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require(mod);
  }
}

bootstrapStrategies();
