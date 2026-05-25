/**
 * Cap plugin → daemon ack envelopes so the CLI NDJSON line stays bounded.
 *
 * STARTER-242: a ~170 KB truncated ack crashed ``koru auto`` when
 * ``diagnostics.rejected`` carried full editor snapshots (``before`` /
 * ``after`` document text) plus a long ``operation_trace``. Debug logs
 * may keep the full payload; the wire format must not.
 */

/** Target max serialized ack line (UTF-8 bytes). Well under daemon 1 MiB cap. */
export const MAX_ACK_WIRE_BYTES = 48 * 1024;

const MAX_TRACE_STEPS = 20;
const MAX_TRACE_ATTEMPTS = 6;
const MAX_SHORT_FIELD = 200;
const MAX_MESSAGE_FIELD = 500;
const MAX_FOCUS_OPEN_CANDIDATES = 24;
const MAX_REJECTED_WIRE = 8;

type TraceStep = {
  op?: string;
  route?: string;
  ok?: boolean;
  command?: string;
  reason?: string;
  attempts?: string[];
  detail?: Record<string, unknown>;
};

function clipString(value: unknown, limit: number): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  if (value.length <= limit) {
    return value;
  }
  return value.slice(0, limit) + `…[+${value.length - limit}]`;
}

function slimTraceStep(raw: unknown): TraceStep | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const step = raw as TraceStep;
  const out: TraceStep = {
    op: clipString(step.op, 64),
    route: clipString(step.route, 64),
    ok: step.ok,
  };
  const command = clipString(step.command, MAX_SHORT_FIELD);
  if (command) {
    out.command = command;
  }
  const reason = clipString(step.reason, MAX_SHORT_FIELD);
  if (reason) {
    out.reason = reason;
  }
  if (Array.isArray(step.attempts)) {
    out.attempts = step.attempts
      .slice(0, MAX_TRACE_ATTEMPTS)
      .map((item) => clipString(item, 80) || String(item).slice(0, 80));
  }
  // Never forward editor snapshots or arbitrary nested blobs on the wire.
  if (step.detail && typeof step.detail === "object") {
    const detail = step.detail as Record<string, unknown>;
    const slim: Record<string, unknown> = {};
    for (const key of ["rejectedCount", "length", "observedLength", "ide", "submit"]) {
      if (key in detail) {
        slim[key] = detail[key];
      }
    }
    if (Object.keys(slim).length > 0) {
      out.detail = slim;
    }
  }
  return out;
}

function slimOperationTrace(trace: unknown): TraceStep[] | undefined {
  if (!Array.isArray(trace)) {
    return undefined;
  }
  const out: TraceStep[] = [];
  for (const raw of trace.slice(-MAX_TRACE_STEPS)) {
    const step = slimTraceStep(raw);
    if (step) {
      out.push(step);
    }
  }
  return out.length > 0 ? out : undefined;
}

function slimRejectedEntry(raw: unknown): Record<string, unknown> | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const entry = raw as Record<string, unknown>;
  const out: Record<string, unknown> = {};
  if (typeof entry.cmd === "string") {
    out.cmd = clipString(entry.cmd, 120);
  }
  if (typeof entry.reason === "string") {
    out.reason = clipString(entry.reason, MAX_SHORT_FIELD);
  }
  // Drop before/after editor snapshots — they can be 100KB+ each.
  return Object.keys(out).length > 0 ? out : null;
}

function slimDiagnostics(diagnostics: unknown): Record<string, unknown> | undefined {
  if (!diagnostics || typeof diagnostics !== "object") {
    return undefined;
  }
  const diag = diagnostics as Record<string, unknown>;
  const out: Record<string, unknown> = {};
  for (const key of [
    "ide",
    "appName",
    "logPath",
    "probeLadder",
    "cacheFocusOpen",
  ] as const) {
    if (typeof diag[key] === "string") {
      out[key] = clipString(diag[key], 120);
    } else if (typeof diag[key] === "boolean") {
      out[key] = diag[key];
    }
  }
  if (Array.isArray(diag.configuredChatOpenCommands)) {
    out.configuredChatOpenCommands = diag.configuredChatOpenCommands
      .slice(0, MAX_FOCUS_OPEN_CANDIDATES)
      .map((c) => clipString(c, 80) || String(c).slice(0, 80));
  }
  if (Array.isArray(diag.focusOpenCandidates)) {
    out.focusOpenCandidates = diag.focusOpenCandidates
      .slice(0, MAX_FOCUS_OPEN_CANDIDATES)
      .map((c) => clipString(c, 80) || String(c).slice(0, 80));
  }
  if (Array.isArray(diag.rejected)) {
    const rejected: Record<string, unknown>[] = [];
    for (const raw of diag.rejected.slice(0, MAX_REJECTED_WIRE)) {
      const entry = slimRejectedEntry(raw);
      if (entry) {
        rejected.push(entry);
      }
    }
    if (rejected.length > 0) {
      out.rejected = rejected;
      if (diag.rejected.length > MAX_REJECTED_WIRE) {
        out.rejected_truncated = diag.rejected.length - MAX_REJECTED_WIRE;
      }
    }
  }
  return Object.keys(out).length > 0 ? out : undefined;
}

function slimSubmitAttempts(attempts: unknown): string[] | undefined {
  if (!Array.isArray(attempts)) {
    return undefined;
  }
  return attempts
    .slice(0, 12)
    .map((item) => clipString(item, 120) || String(item).slice(0, 120));
}

/**
 * Return a wire-safe copy of an outbound envelope (ack / error).
 * Idempotent for non-ack types.
 */
export function sanitizeOutboundEnvelope(
  env: Record<string, unknown>
): Record<string, unknown> {
  const type = env.type;
  if (type !== "ack" && type !== "error") {
    return env;
  }

  const out: Record<string, unknown> = { ...env };

  if (typeof out.message === "string") {
    out.message = clipString(out.message, MAX_MESSAGE_FIELD);
  }

  if ("operation_trace" in out) {
    const slim = slimOperationTrace(out.operation_trace);
    if (slim) {
      out.operation_trace = slim;
    } else {
      delete out.operation_trace;
    }
  }

  if ("diagnostics" in out) {
    const slim = slimDiagnostics(out.diagnostics);
    if (slim) {
      out.diagnostics = slim;
    } else {
      delete out.diagnostics;
    }
  }

  if ("submit_attempts" in out) {
    const slim = slimSubmitAttempts(out.submit_attempts);
    if (slim) {
      out.submit_attempts = slim;
    } else {
      delete out.submit_attempts;
    }
  }

  let bytes = measureEnvelopeBytes(out);
  if (bytes <= MAX_ACK_WIRE_BYTES) {
    return out;
  }

  // Second pass: drop the heaviest optional fields until we fit.
  delete out.diagnostics;
  delete out.submit_attempts;
  bytes = measureEnvelopeBytes(out);
  if (bytes <= MAX_ACK_WIRE_BYTES) {
    out.payload_trimmed = true;
    return out;
  }

  delete out.operation_trace;
  out.operation_trace_dropped = true;
  out.payload_trimmed = true;
  return out;
}

export function measureEnvelopeBytes(env: Record<string, unknown>): number {
  try {
    return Buffer.byteLength(JSON.stringify(env), "utf8");
  } catch {
    return Number.MAX_SAFE_INTEGER;
  }
}
