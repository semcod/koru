import { isVscodiumHost } from "./ides/vscodium-host";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(`vscodium-extension test failed: ${message}`);
}

function testHostVariants() {
  assert(isVscodiumHost("VSCodium"), "detects VSCodium host");
  assert(isVscodiumHost("Codium"), "detects Codium host");
  assert(isVscodiumHost("Code - OSS"), "detects Code - OSS host");
  assert(isVscodiumHost("code-oss"), "detects code-oss host");
  assert(isVscodiumHost(""), "accepts empty appName fallback");
  assert(!isVscodiumHost("Visual Studio Code"), "rejects upstream VS Code host");
  assert(!isVscodiumHost("Cursor"), "rejects Cursor host");
}

testHostVariants();
console.log("vscodium-extension tests: ok");
