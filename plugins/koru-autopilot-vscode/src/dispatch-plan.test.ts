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

function testSocketCandidatesDoNotCrossIdeFallback(): void {
  const oldSocket = process.env.KORU_AUTOPILOT_SOCKET;
  const oldInstance = process.env.KORU_AUTOPILOT_INSTANCE;
  const oldRuntime = process.env.XDG_RUNTIME_DIR;
  try {
    delete process.env.KORU_AUTOPILOT_SOCKET;
    process.env.KORU_AUTOPILOT_INSTANCE = "windsurf";
    process.env.XDG_RUNTIME_DIR = "/run/user/1000";
    const candidates = socketCandidatesFromEnv("vscode");
    assert(
      candidates.includes("/run/user/1000/koru-autopilot-vscode.sock"),
      "vscode socket should be considered",
    );
    assert(
      !candidates.includes("/run/user/1000/koru-autopilot-windsurf.sock"),
      "vscode plugin must not fall back to Windsurf socket",
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

function testSocketCandidatesSeparateVscodeAndVscodium(): void {
  const oldSocket = process.env.KORU_AUTOPILOT_SOCKET;
  const oldInstance = process.env.KORU_AUTOPILOT_INSTANCE;
  const oldRuntime = process.env.XDG_RUNTIME_DIR;
  try {
    delete process.env.KORU_AUTOPILOT_SOCKET;
    process.env.KORU_AUTOPILOT_INSTANCE = "vscode";
    process.env.XDG_RUNTIME_DIR = "/run/user/1000";
    const candidates = socketCandidatesFromEnv("vscodium");
    assert(
      candidates.includes("/run/user/1000/koru-autopilot-vscodium.sock"),
      "vscodium socket should be considered",
    );
    assert(
      !candidates.includes("/run/user/1000/koru-autopilot-vscode.sock"),
      "VSCodium plugin must not fall back to VS Code socket",
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

function testSocketCandidatesPreferOverrideThenDefaults(): void {
  const candidates = socketCandidatesFromEnv("cursor", "/run/user/1000/koru-autopilot-cursor.sock");
  assert(candidates.length >= 2, "override should be tried first, then default lane candidates");
  assert(
    candidates[0] === "/run/user/1000/koru-autopilot-cursor.sock",
    "explicit override path should be first",
  );
  assert(
    candidates.includes("/run/user/1000/koru-autopilot.sock"),
    "singleton socket should remain a fallback when override is set",
  );
}

testShutdownPlan();
testUnknownTypePlan();
testSocketCandidatesPreferIdeInstanceBeforeSingleton();
testSocketCandidatesDoNotCrossIdeFallback();
testSocketCandidatesSeparateVscodeAndVscodium();
testSocketCandidatesPreferOverrideThenDefaults();
