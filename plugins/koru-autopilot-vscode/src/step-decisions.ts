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

/**
 * Host-level submit commands can report rc=0 even when the chat webview did
 * not consume the key. For those IDEs, a long pasted prompt must be verified
 * whenever the probe ladder is available, even if the legacy user setting
 * disabled optional post-submit verification.
 */
export function shouldRequireVerifiedHostSubmit(
  ide: string,
  pastedText: string | undefined,
  cfg: KoruAutopilotStepConfig
): boolean {
  if (!cfg.probeLadder) {
    return false;
  }
  if (!pastedText || pastedText.trim().length < 4) {
    return false;
  }
  const strategy = ideControlStrategy(ide);
  return strategy.verifyPostSubmit && strategy.submitStrategy.endsWith("host-submit");
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

/** Leftover from a failed autonomous drive (paste OK, submit no-op). */
function isStaleKoruAutonomousDriveDraft(text: string): boolean {
  if (text.length < 80) {
    return false;
  }
  return (
    /Ticket\s+[A-Z]+-\d+/.test(text)
    || (/waiting_input/i.test(text) && /Continue the actual implementation/i.test(text))
    || (/stuck in status/i.test(text) && /Ticket\s+[A-Z]+-\d+/.test(text))
    || (/redrive/i.test(text) && /Ticket\s+[A-Z]+-\d+/.test(text))
  );
}

function promptsLikelySameDraft(observed: string, requested: string): boolean {
  if (!requested || observed.length < 80 || requested.length < 80) {
    return false;
  }
  const prefixLen = Math.min(120, requested.length, observed.length);
  if (prefixLen < 40) {
    return false;
  }
  const observedPrefix = observed.slice(0, prefixLen);
  const requestedPrefix = requested.slice(0, prefixLen);
  return (
    observed.startsWith(requestedPrefix)
    || requested.startsWith(observedPrefix)
    || observed.includes(requestedPrefix)
    || requested.includes(observedPrefix)
  );
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
  if (requested && promptsLikelySameDraft(observed, requested)) {
    return "submit_existing";
  }
  if (isKnownStaleKoruCommandDraft(observed)) {
    return "replace_known_koru_draft";
  }
  if (isStaleKoruAutonomousDriveDraft(observed)) {
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
 * With ``requireEmpty`` enabled, inconclusive probes are also retried because
 * host-level submit commands often report rc=0 even when the webview ignored
 * the key/click.
 */
export function interpretPostSubmitProbe(
  observedAfter: string | null,
  originalText: string,
  opts: { requireEmpty?: boolean } = {}
): PostSubmitVerifyResult & { action: "accept" | "retry" } {
  const decision = decideSubmitCleared(observedAfter, originalText);
  const observedLength = observedAfter === null ? -1 : observedAfter.trim().length;
  if (opts.requireEmpty && (observedAfter === null || observedLength > 0)) {
    return {
      ...decision,
      cleared: false,
      observedLength,
      action: "retry",
    };
  }
  return {
    ...decision,
    observedLength,
    action: decision.cleared ? "accept" : "retry",
  };
}

export function postSubmitProbeMaxAttempts(
  ide: string,
  opts: { requireEmpty?: boolean } = {}
): number {
  if (ide === "vscodium" && opts.requireEmpty) {
    return 4;
  }
  return 1;
}
