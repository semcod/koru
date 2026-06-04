import {
  VERSION_MISMATCH_RECONNECT_RETRY_MS,
  extractExpectedReloadTarget,
  isReloadablePluginMismatch,
} from "./_shared/version-reconnect";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(`version-reconnect test failed: ${message}`);
}

function testDetectsReloadableMismatch(): void {
  assert(
    isReloadablePluginMismatch(
      "connected autopilot plugin version mismatch: connected=0.2.14 expected=0.2.24",
    ),
    "detects plugin version mismatch",
  );
  assert(
    isReloadablePluginMismatch(
      "connected autopilot plugin build mismatch: connected=old expected=f852997839ddbb99 version=0.2.24",
    ),
    "detects plugin build mismatch",
  );
  assert(!isReloadablePluginMismatch("daemon unavailable"), "ignores unrelated daemon errors");
}

function testExtractsExpectedReloadTarget(): void {
  assert(
    extractExpectedReloadTarget(
      "connected autopilot plugin build mismatch: connected=old expected=f852997839ddbb99 version=0.2.24",
    ) === "f852997839ddbb99@0.2.24",
    "prefers build and includes version when present",
  );
  assert(
    extractExpectedReloadTarget(
      "connected autopilot plugin version mismatch: connected=0.2.14 expected=0.2.24",
    ) === "0.2.24",
    "uses expected version when build is absent",
  );
}

function testBlockedRetryWaitsPastReloadCooldown(): void {
  assert(
    VERSION_MISMATCH_RECONNECT_RETRY_MS > 60_000,
    "blocked reconnect retry must wait past reload cooldown",
  );
}

testDetectsReloadableMismatch();
testExtractsExpectedReloadTarget();
testBlockedRetryWaitsPastReloadCooldown();
console.log("version-reconnect tests: ok");
