export function isVscodiumHost(appName: string): boolean {
  const lowered = appName.toLowerCase();
  return (
    lowered === "" ||
    lowered.includes("vscodium") ||
    lowered.includes("codium") ||
    lowered.includes("code - oss") ||
    lowered.includes("code-oss")
  );
}
