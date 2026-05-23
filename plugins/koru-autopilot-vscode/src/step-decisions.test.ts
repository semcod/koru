import {
  interpretPostSubmitProbe,
  readVerifySubmitEnabled,
  shouldVerifyPostSubmit,
  shouldVerifyPrePasteBusy,
} from "./step-decisions";

function assert(condition: unknown, message: string): void {
  if (!condition) {
    throw new Error(`step-decisions test failed: ${message}`);
  }
}

function testReadVerifySubmitPrefersNewSetting(): void {
  assert(
    !readVerifySubmitEnabled({ probeLadder: true, verifySubmit: false }),
    "verifySubmit=false disables verification",
  );
  assert(
    readVerifySubmitEnabled({ probeLadder: true, verifySubmit: true, verifySubmitOnCursor: false }),
    "verifySubmit=true beats legacy false",
  );
}

function testShouldVerifyPostSubmitAllPluginIdes(): void {
  const base = { probeLadder: true, verifySubmit: true, skipWhenInputBusy: true };
  for (const ide of ["cursor", "vscode", "vscodium"]) {
    assert(
      shouldVerifyPostSubmit(ide, "long enough prompt", base),
      `${ide} must verify post-submit`,
    );
  }
  assert(
    !shouldVerifyPostSubmit("windsurf", "long enough prompt", base),
    "windsurf native path skips verify",
  );
  assert(
    !shouldVerifyPostSubmit("cursor", "hi", base),
    "short prompt skips verify",
  );
}

function testShouldVerifyPrePasteBusy(): void {
  assert(
    shouldVerifyPrePasteBusy({ probeLadder: true, verifySubmit: true, skipWhenInputBusy: true }),
    "busy probe when ladder+skipWhenInputBusy",
  );
  assert(
    !shouldVerifyPrePasteBusy({ probeLadder: true, verifySubmit: true, skipWhenInputBusy: false }),
    "no busy probe when setting off",
  );
}

function testInterpretPostSubmitProbeRetry(): void {
  const original = "Architektura: wprowadź CQRS — test";
  const result = interpretPostSubmitProbe(original, original);
  assert(result.action === "retry", "residue must request retry");
  assert(!result.cleared, "not cleared");
}

testReadVerifySubmitPrefersNewSetting();
testShouldVerifyPostSubmitAllPluginIdes();
testShouldVerifyPrePasteBusy();
testInterpretPostSubmitProbeRetry();
console.log("step-decisions tests: ok");
