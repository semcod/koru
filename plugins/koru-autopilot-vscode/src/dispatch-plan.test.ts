import { planDispatch } from "./dispatch-plan";
import { socketCandidatesFromEnv } from "./socketPath";

function assert(condition: unknown, message: string): void {
  if (!condition) {
    throw new Error(`dispatch-plan test failed: ${message}`);
  }
}

function testShutdownPlan(): void {
  const plan = planDispatch({ type: "shutdown" });
  assert(plan.kind === "ackAndDisconnect", "shutdown should map to ackAndDisconnect");
  if (plan.kind === "ackAndDisconnect") {
    assert(plan.info.shutdown === true, "shutdown info should be true");
  }
}

function testUnknownTypePlan(): void {
  const plan = planDispatch({ type: "unknown.type" });
  assert(plan.kind === "error", "unknown type should map to error");
  if (plan.kind === "error") {
    assert(plan.message.includes("unhandled unknown.type"), "error message should include type");
  }
}

function testSocketCandidatesPreferIdeInstanceBeforeSingleton(): void {
  const oldSocket = process.env.KORU_AUTOPILOT_SOCKET;
  const oldInstance = process.env.KORU_AUTOPILOT_INSTANCE;
  const oldRuntime = process.env.XDG_RUNTIME_DIR;
  try {
    delete process.env.KORU_AUTOPILOT_SOCKET;
    delete process.env.KORU_AUTOPILOT_INSTANCE;
    process.env.XDG_RUNTIME_DIR = "/run/user/1000";
    const candidates = socketCandidatesFromEnv("windsurf");
    assert(
      candidates.indexOf("/run/user/1000/koru-autopilot-windsurf.sock") <
        candidates.indexOf("/run/user/1000/koru-autopilot.sock"),
      "per-IDE socket should be tried before singleton socket",
    );
  } finally {
    if (oldSocket === undefined) delete process.env.KORU_AUTOPILOT_SOCKET;
    else process.env.KORU_AUTOPILOT_SOCKET = oldSocket;
    if (oldInstance === undefined) delete process.env.KORU_AUTOPILOT_INSTANCE;
    else process.env.KORU_AUTOPILOT_INSTANCE = oldInstance;
    if (oldRuntime === undefined) delete process.env.XDG_RUNTIME_DIR;
    else process.env.XDG_RUNTIME_DIR = oldRuntime;
  }
}

testShutdownPlan();
testUnknownTypePlan();
testSocketCandidatesPreferIdeInstanceBeforeSingleton();
