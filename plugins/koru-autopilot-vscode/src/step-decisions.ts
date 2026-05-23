/**
 * Pure decision helpers for the inject pipeline (focus → busy → paste → submit).
 *
 * Each step in ``extension.ts`` should consult these functions so verification
 * policy stays consistent across IDEs instead of being duplicated inline.
 */

import { decideSubmitCleared } from "./probe-ladder";

export type InjectStep = "focus" | "busy" | "paste" | "submit";

export interface KoruAutopilotStepConfig {
  probeLadder: boolean;
  /** When true, probe chat input after submit (all IDE ladders). */
  verifySubmit: boolean;
  /** Legacy alias kept for settings migration (≤0.1.54). */
  verifySubmitOnCursor?: boolean;
  skipWhenInputBusy?: boolean;
}

/** Read ``verifySubmit`` with fallback to deprecated ``verifySubmitOnCursor``. */
export function readVerifySubmitEnabled(cfg: KoruAutopilotStepConfig): boolean {
  if (typeof cfg.verifySubmit === "boolean") {
    return cfg.verifySubmit;
  }
  return cfg.verifySubmitOnCursor !== false;
}

/**
 * Should we run the post-submit clipboard probe for this IDE + prompt?
 *
 * Skipped for Windsurf/Antigravity native atomic send paths (no separate
 * paste+submit ladder) and when verification is disabled or the prompt is
 * too short for a reliable tail match (see ``decideSubmitCleared``).
 */
export function shouldVerifyPostSubmit(
  ide: string,
  pastedText: string | undefined,
  cfg: KoruAutopilotStepConfig
): boolean {
  if (!cfg.probeLadder || !readVerifySubmitEnabled(cfg)) {
    return false;
  }
  if (!pastedText || pastedText.trim().length < 4) {
    return false;
  }
  if (ide === "windsurf" || ide === "antigravity") {
    return false;
  }
  return true;
}

/** Should the pre-paste busy probe run before injecting? */
export function shouldVerifyPrePasteBusy(cfg: KoruAutopilotStepConfig): boolean {
  return cfg.probeLadder && (cfg.skipWhenInputBusy ?? true);
}

export type PostSubmitVerifyResult = ReturnType<typeof decideSubmitCleared> & {
  observedLength: number;
};

/**
 * Interpret a post-submit clipboard probe and map to pipeline action.
 *
 * Returns ``accept`` when the submit step succeeded (or probe inconclusive),
 * ``retry`` when the pasted tail is still in the input (try next candidate).
 */
export function interpretPostSubmitProbe(
  observedAfter: string | null,
  originalText: string
): PostSubmitVerifyResult & { action: "accept" | "retry" } {
  const decision = decideSubmitCleared(observedAfter, originalText);
  const observedLength = observedAfter === null ? -1 : observedAfter.trim().length;
  return {
    ...decision,
    observedLength,
    action: decision.cleared ? "accept" : "retry",
  };
}
