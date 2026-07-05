/**
 * Umbrella-plugin strategy registry.
 *
 * Cursor / VSCodium / Windsurf / Antigravity each have their own
 * standalone VSIX; this umbrella plugin serves Microsoft VS Code and
 * forks without a dedicated VSIX (Qoder).
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
  // Forks first: the detect probe may contain both the fork's install
  // path and a masqueraded "Visual Studio Code" appName, so the more
  // specific strategy must win before vscode's broad match.
  for (const mod of ["./qoder", "./vscode"]) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require(mod);
  }
}

bootstrapStrategies();
