import {
  MAX_ACK_WIRE_BYTES,
  measureEnvelopeBytes,
  sanitizeOutboundEnvelope,
} from "./ack-payload";

function assert(cond: boolean, msg: string): void {
  if (!cond) {
    throw new Error(msg);
  }
}

function testStripsEditorSnapshotsFromDiagnosticsRejected(): void {
  const hugeText = "x".repeat(80_000);
  const env = {
    type: "ack",
    id: "drive-1",
    ok: false,
    diagnostics: {
      ide: "cursor",
      rejected: [
        {
          cmd: "workbench.panel.chat",
          reason: "probe rejected",
          before: { text: hugeText },
          after: { text: hugeText },
        },
      ],
      focusOpenCandidates: Array.from({ length: 200 }, (_, i) => `cmd.${i}`),
    },
    operation_trace: Array.from({ length: 60 }, (_, i) => ({
      op: "focus_open",
      route: `step-${i}`,
      ok: false,
      reason: "y".repeat(500),
      attempts: Array.from({ length: 20 }, () => "attempt-" + "z".repeat(200)),
      detail: { before: { text: hugeText } },
    })),
  };
  const slim = sanitizeOutboundEnvelope(env);
  const bytes = measureEnvelopeBytes(slim);
  assert(bytes < MAX_ACK_WIRE_BYTES, `expected < ${MAX_ACK_WIRE_BYTES}, got ${bytes}`);
  const diag = slim.diagnostics as Record<string, unknown>;
  const rejected = (diag?.rejected as unknown[]) || [];
  assert(rejected.length > 0 && rejected.length <= 8, "rejected capped");
  const first = rejected[0] as Record<string, unknown>;
  assert(!("before" in first), "before snapshot must not be on wire");
  assert(!("after" in first), "after snapshot must not be on wire");
  console.log("ack-payload tests: ok");
}

testStripsEditorSnapshotsFromDiagnosticsRejected();
