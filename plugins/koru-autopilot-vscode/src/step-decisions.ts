/**
 * Pure decision helpers for the inject pipeline (focus → busy → paste → submit).
 *
 * Each step in ``extension.ts`` should consult these functions so verification
 * policy stays consistent across IDEs instead of being duplicated inline.
 */

import { decideSubmitCleared } from "./probe-ladder";
import { ideControlStrategy } from "./ide-control-strategy";

export type InjectStep = "focus" | "busy" | "paste" | "submit";

export interface KoruAutopilotStepConfig {
  probeLadder: boolean;
  /** When true, probe chat input after submit (all IDE ladders). */
  verifySubmit: boolean;
  /** Legacy alias kept for settings migration (≤0.1.54). */
  verifySubmitOnCursor?: boolean;
  skipWhenInputBusy?: boolean;
}

export type BusyInputAction = "empty" | "submit_existing" | "replace_known_koru_draft" | "block";

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
  if (!ideControlStrategy(ide).verifyPostSubmit) {
    return false;
  }
  return true;
}

/** Should the pre-paste busy probe run before injecting? */
export function shouldVerifyPrePasteBusy(cfg: KoruAutopilotStepConfig): boolean {
  return cfg.probeLadder && (cfg.skipWhenInputBusy ?? true);
}

function normalizeDraft(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

function isKnownStaleKoruCommandDraft(text: string): boolean {
  if (text.length > 120) {
    return false;
  }
  const withoutEnv = text.replace(/^(?:[A-Z_][A-Z0-9_]*=\S+\s+)*/, "");
  return /^(?:\.\/)?(?:\.venv\/bin\/)?koru\s+auto(?:\s+--[A-Za-z0-9][A-Za-z0-9_.-]*(?:=\S+)?)?$/i.test(withoutEnv);
}

export function decideBusyInputAction(
  observedInput: string | null,
  requestedText: string
): BusyInputAction {
  const observed = normalizeDraft(observedInput || "");
  if (observed.length < 4) {
    return "empty";
  }
  const requested = normalizeDraft(requestedText);
  if (requested && observed === requested) {
    return "submit_existing";
  }
  if (isKnownStaleKoruCommandDraft(observed)) {
    return "replace_known_koru_draft";
  }
  return "block";
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
