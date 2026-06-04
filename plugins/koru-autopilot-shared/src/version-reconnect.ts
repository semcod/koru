export const VERSION_MISMATCH_RECONNECT_RETRY_MS = 65_000;

export function isReloadablePluginMismatch(message: string): boolean {
  const lowered = message.toLowerCase();
  return lowered.includes("plugin version mismatch") || lowered.includes("plugin build mismatch");
}

/**
 * Pull the daemon's expected build/version token out of a rejection message so
 * the reload cooldown can be keyed to the target the daemon actually wants
 * loaded. The daemon emits both `expected=<build sha> version=<x>` (build
 * mismatch) and `expected=<version>` (version mismatch); the build sha is the
 * most specific identity, so prefer it and fall back to the version.
 */
export function extractExpectedReloadTarget(message: string): string {
  const build = /expected=([^\s;]+)/i.exec(message);
  const version = /version=([^\s;]+)/i.exec(message);
  const parts: string[] = [];
  if (build?.[1] && build[1] !== "-") parts.push(build[1]);
  if (version?.[1] && version[1] !== "-") parts.push(version[1]);
  return parts.join("@");
}
