"""Consumer canaries; all destructive fixtures stay in TemporaryDirectory."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".governance/docs_gate.py"
SPEC = importlib.util.spec_from_file_location("koru_docs_gate", SCRIPT)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class ArgumentBoundary(unittest.TestCase):
    def test_final_needs_exact_base(self):
        for extra in [[], ["--base", "main"]]:
            run = subprocess.run([sys.executable, str(SCRIPT), "final", "--root", str(ROOT),
                                  "--standard-root", "/missing", *extra], capture_output=True)
            self.assertEqual(run.returncode, 2)

    def test_missing_runtime_is_json_failure(self):
        with tempfile.TemporaryDirectory() as empty:
            run = subprocess.run([sys.executable, str(SCRIPT), "final", "--root", str(ROOT),
                                  "--standard-root", empty, "--base", "a" * 40],
                                 capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stdout)["findings"][0]["code"], "DOCS_RUNTIME_UNAVAILABLE")


@unittest.skipUnless(
    os.environ.get("KORU_DOCS_STANDARD_ROOT"),
    "Set KORU_DOCS_STANDARD_ROOT to run real consumer canaries",
)
class ConsumerCanaries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "consumer"
        self.root.mkdir()
        self.runtime = Path(self.tmp.name) / "standard"
        package = self.runtime / "docs/standard"
        package.mkdir(parents=True)
        for name, raw in gate.verified_sources(os.environ["KORU_DOCS_STANDARD_ROOT"]).items():
            (package / name).write_bytes(raw)
        self.git("init", "-q")
        self.git("remote", "add", "origin", "https://github.com/semcod/koru.git")
        names = ["docs/SERVICE/COMMAND_EXECUTION.md", "docs/SERVICE/CI_COMPLETION_GATES.md",
                 "docs/SERVICE/POST_RUN_VERIFICATION.md", "docs/auto-execute-commands.md",
                 "docs/post-run-verify.md", ".governance/docs.json"]
        for name in names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        (self.root / "docs/README.md").write_text("\n".join(
            "[Topic](" + name[5:] + ")" for name in names[:3]))
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.org", "commit", "-qm", "fixture")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True, stderr=subprocess.PIPE)

    def run_gate(self, phase="final", extra=()):
        command = [sys.executable, str(SCRIPT), phase, "--root", str(self.root),
                   "--standard-root", str(self.runtime)]
        command += ["--base", self.base] if phase == "final" else [
            "--kind", "feature", "--id", "consumer-pilot", "--deliverable", "docs/FEATURE/CONSUMER_PILOT.md"]
        result = subprocess.run(command + list(extra), capture_output=True, text=True)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return result.returncode, json.loads(result.stdout)

    def codes(self, phase="final"):
        code, result = self.run_gate(phase)
        self.assertEqual(code, 1)
        return {item["code"] for item in result["findings"]}

    def test_real_corpus_passes_and_is_idempotent(self):
        first = self.run_gate()
        self.assertEqual(first[0], 0, first)
        self.assertEqual(first[1]["documents_checked"], 5)
        self.assertEqual(first, self.run_gate())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_prepare_creates_no_document(self):
        code, result = self.run_gate("prepare")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["plan"]["standard_revision"], gate.REVISION)
        self.assertFalse((self.root / "docs/FEATURE/CONSUMER_PILOT.md").exists())

    def test_missing_adoption_stops_both_phases(self):
        (self.root / ".governance/docs.json").unlink()
        for phase in ("prepare", "final"):
            self.assertIn("DOCS_ADOPTION", self.codes(phase))

    def test_wrong_adoption_pin_stops_both_phases(self):
        path = self.root / ".governance/docs.json"
        value = json.loads(path.read_text())
        value["source_revision"] = "b" * 40
        path.write_text(json.dumps(value))
        for phase in ("prepare", "final"):
            self.assertIn("DOCS_ADOPTION", self.codes(phase))

    def test_modified_runtime_never_executes(self):
        path = self.runtime / "docs/standard/check.py"
        path.write_text("raise RuntimeError('untrusted source')")
        self.assertIn("DOCS_RUNTIME_DIGEST", self.codes())

    def test_runtime_symlink_fails(self):
        path = self.runtime / "docs/standard/policy.json"
        saved = self.runtime / "saved.json"
        path.rename(saved)
        path.symlink_to(saved)
        self.assertIn("DOCS_RUNTIME_SYMLINK", self.codes())

    def test_adjacent_unverified_source_is_not_imported(self):
        (self.runtime / "docs/standard/subprocess.py").write_text("raise RuntimeError('poisoned import')")
        self.assertEqual(self.run_gate()[0], 0)

    def test_missing_index_stops_generation(self):
        (self.root / "docs/README.md").unlink()
        self.assertIn("DOCS_INDEX", self.codes("prepare"))

    def test_metadata_removal_is_discovered_from_base(self):
        (self.root / "docs/SERVICE/COMMAND_EXECUTION.md").write_text("# Missing metadata")
        self.assertIn("DOCS_METADATA", self.codes())

    def test_missing_redirect_target_fails(self):
        (self.root / "docs/SERVICE/COMMAND_EXECUTION.md").unlink()
        self.assertIn("DOCS_REDIRECT_TARGET", self.codes())

    def test_unavailable_base_fails(self):
        self.base = "f" * 40
        self.assertIn("DOCS_BASE", self.codes())


if __name__ == "__main__":
    unittest.main()
