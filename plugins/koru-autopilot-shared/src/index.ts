/**
 * Barrel entrypoint for the shared autopilot-plugin utilities.
 *
 * Each per-IDE plugin (cursor, vscode, vscodium, windsurf, antigravity)
 * receives a copy of this directory at ``src/_shared/`` via
 * ``scripts/sync-plugin-shared.py`` and re-exports from
 * ``./_shared/index``. Keeping the surface narrow makes regressions
 * impossible to leak across plugins — touching one plugin's
 * ``extension.ts`` cannot affect another.
 *
 * Only put truly stable, IDE-agnostic helpers here. Anything that
 * branches on ``vscode.env.appName`` belongs in the per-IDE plugin.
 */

export {
  MAX_ACK_WIRE_BYTES,
  measureEnvelopeBytes,
  sanitizeOutboundEnvelope,
} from "./ack-payload";
export type { DispatchPlan, EnvelopeLike } from "./dispatch-plan";
export { planDispatch } from "./dispatch-plan";
export {
  bottomRightSubmitPoint,
  parseXdotoolGeometryShell,
} from "./host-click-submit";
export type { ScreenPoint, WindowGeometry } from "./host-click-submit";
export {
  defaultSocketPathFromEnv,
  socketCandidatesFromEnv,
} from "./socketPath";
export { defaultGlobalStateDbPath } from "./chat-history-paths";
export type {
  AdapterRunner,
  ChatHistoryRow,
  IdeAdapter,
  SupportedIde,
} from "./chat-history-types";
