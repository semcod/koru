// koru autopilot — shared types
//
// Shared type definitions for VS Code family IDE plugins.

export type CommandOutcome = { ok: boolean; command?: string; reason?: string; attempts?: string[] };
export type FocusOutcome = CommandOutcome & { diagnostics?: Record<string, unknown> };
export type PasteAttempt = { handled: boolean; result: CommandOutcome };
export type SubmitOutcome = CommandOutcome & { unverified?: boolean };
export type HostCommandResult = { ok: boolean; stdout: string };

export type OperationTraceStep = {
  op: string;
  route: string;
  ok: boolean;
  command?: string;
  reason?: string;
  attempts?: string[];
  detail?: Record<string, unknown>;
};

export interface Envelope {
  type: string;
  id?: string;
  [k: string]: unknown;
}
