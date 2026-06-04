import {
  decideBusyInputAction,
  interpretPostSubmitProbe,
  readVerifySubmitEnabled,
  shouldRequireVerifiedHostSubmit,
  shouldVerifyPostSubmit,
  shouldVerifyPrePasteBusy,
} from "./step-decisions";
import { ideControlStrategy } from "./ide-control-strategy";

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

function testHostSubmitIdesRequireVerificationEvenWhenOptionalVerifyDisabled(): void {
  const cfg = { probeLadder: true, verifySubmit: false, skipWhenInputBusy: true };
  assert(
    shouldRequireVerifiedHostSubmit("vscodium", "long enough prompt", cfg),
    "VSCodium host-key submit must be verified because host keys can be no-ops",
  );
  assert(
    shouldRequireVerifiedHostSubmit("cursor", "long enough prompt", cfg),
    "Cursor host-key submit must be verified because Return can be a newline",
  );
  assert(
    !shouldRequireVerifiedHostSubmit("vscode", "long enough prompt", cfg),
    "VS Code registered-command path does not force host-submit verification",
  );
  assert(
    !shouldRequireVerifiedHostSubmit("vscodium", "hi", cfg),
    "short prompts skip mandatory host-submit verification",
  );
}

function testIdeStrategiesAreSeparated(): void {
  assert(
    ideControlStrategy("vscodium").submitStrategy === "vscodium-host-submit",
    "VSCodium has its own host-submit strategy",
  );
  assert(
    ideControlStrategy("cursor").submitStrategy === "cursor-host-submit",
    "Cursor has its own host-submit strategy",
  );
  assert(
    ideControlStrategy("windsurf").nativeAtomicSend,
    "Windsurf must stay on native atomic send",
  );
  assert(
    !ideControlStrategy("windsurf").allowGenericPaste,
    "Windsurf must not use generic paste fallback",
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

function testDecideBusyInputAction(): void {
  assert(decideBusyInputAction("", "next prompt") === "empty", "empty input is not busy");
  assert(
    decideBusyInputAction("same prompt", " same\n prompt ") === "submit_existing",
    "existing matching prompt should be submitted instead of pasted twice",
  );
  assert(
    decideBusyInputAction("koru auto", "next prompt") === "replace_known_koru_draft",
    "stale koru auto draft may be replaced",
  );
  assert(
    decideBusyInputAction("KORU_AUTOPILOT_INSTANCE=vscode .venv/bin/koru auto", "next prompt")
      === "replace_known_koru_draft",
    "command-like koru auto draft with env/path may be replaced",
  );
  assert(
    decideBusyInputAction("koru auto nie działa", "next prompt") === "block",
    "natural-language user text must not be replaced",
  );
  assert(decideBusyInputAction("please answer this", "next prompt") === "block", "user draft blocks drive");
  assert(
    decideBusyInputAction(
      "Ticket STARTER-468 waiting_input Continue the actual implementation for this ticket.",
      "next prompt",
    ) === "replace_known_koru_draft",
    "stale autonomous drive draft may be replaced",
  );
  assert(
    decideBusyInputAction(
      "Ticket STARTER-468 same autonomous prompt with extra trailing whitespace",
      "Ticket STARTER-468 same autonomous prompt with extra trailing whitespace ",
    ) === "submit_existing",
    "near-duplicate autonomous prompt should submit existing input",
  );
}

function testInterpretPostSubmitProbeRetry(): void {
  const original = "Architektura: wprowadź CQRS — test";
  const result = interpretPostSubmitProbe(original, original);
  assert(result.action === "retry", "residue must request retry");
  assert(!result.cleared, "not cleared");
}

function testInterpretPostSubmitProbeStrictEmpty(): void {
  const result = interpretPostSubmitProbe(
    "unrelated copied text from editor",
    "Ticket prompt that was pasted into chat",
    { requireEmpty: true },
  );
  assert(result.action === "retry", "strict host submit must reject non-empty probe");
  assert(!result.cleared, "strict host submit requires empty input");
  const inconclusive = interpretPostSubmitProbe(null, "Ticket prompt", { requireEmpty: true });
  assert(inconclusive.action === "retry", "strict host submit rejects inconclusive probe");
  assert(!inconclusive.cleared, "strict inconclusive probe is not cleared");
  const empty = interpretPostSubmitProbe("", "Ticket prompt", { requireEmpty: true });
  assert(empty.action === "accept", "strict host submit accepts empty input");
}

testReadVerifySubmitPrefersNewSetting();
testShouldVerifyPostSubmitAllPluginIdes();
testHostSubmitIdesRequireVerificationEvenWhenOptionalVerifyDisabled();
testIdeStrategiesAreSeparated();
testShouldVerifyPrePasteBusy();
testDecideBusyInputAction();
testInterpretPostSubmitProbeRetry();
testInterpretPostSubmitProbeStrictEmpty();
console.log("step-decisions tests: ok");
