/**
 * Per-IDE strategy registry — ``windsurf`` only.
 */

import type { IdeStrategy } from "./ide-strategy";

const REGISTRY = new Map<string, IdeStrategy>();

export function registerStrategy(strategy: IdeStrategy, opts: { override?: boolean } = {}): void {
  const id = strategy.id;
  if (!id) throw new Error("IdeStrategy.id must be a non-empty string");
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

export function bootstrapStrategies(): void {
  for (const mod of ["./windsurf"]) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require(mod);
  }
}

bootstrapStrategies();
