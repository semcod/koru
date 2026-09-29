import { isWindsurfLaneHost } from "./windsurf";
import { detectIdeViaStrategies } from "./index";

function assert(condition: unknown, message: string): void {
  if (!condition) {
    throw new Error(`windsurf host detection test failed: ${message}`);
  }
}

function testDevinDesktopMatchesWindsurfLane(): void {
  assert(isWindsurfLaneHost("Devin"), "Devin must match the windsurf lane");
  assert(
    isWindsurfLaneHost("Devin Desktop"),
    "Devin Desktop must match the windsurf lane",
  );
  assert(
    detectIdeViaStrategies("Devin") === "windsurf",
    "detectIdeViaStrategies(Devin) must resolve to windsurf",
  );
}

function testWindsurfStillMatches(): void {
  assert(isWindsurfLaneHost("Windsurf"), "Windsurf must match");
  assert(
    detectIdeViaStrategies("Windsurf") === "windsurf",
    "detectIdeViaStrategies(Windsurf) must resolve to windsurf",
  );
}

function testUnrelatedHostsRejected(): void {
  for (const appName of ["Visual Studio Code", "Cursor", "VSCodium", ""]) {
    assert(
      !isWindsurfLaneHost(appName),
      `${appName} must not match the windsurf lane`,
    );
  }
}

testDevinDesktopMatchesWindsurfLane();
testWindsurfStillMatches();
testUnrelatedHostsRejected();
console.log("windsurf host detection tests passed");
