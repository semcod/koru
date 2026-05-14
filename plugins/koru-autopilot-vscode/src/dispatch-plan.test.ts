import { planDispatch } from "./dispatch-plan";

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

testShutdownPlan();
testUnknownTypePlan();
