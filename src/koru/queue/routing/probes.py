"""Default candidates and isolated benchmark probe runners."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import time
from pathlib import Path

from .contracts import Candidate, ProbeResult, ToolClass


def get_default_candidates() -> list[Candidate]:
    """Return standard candidate executors across deterministic, API and CLI classes."""
    return [
        Candidate(
            id="deterministic-ruff",
            tool_class=ToolClass.DETERMINISTIC,
            client="ruff",
            transport="local",
            fingerprint="tool:ruff:v1",
            capabilities=frozenset({"simple:ruff"}),
            available=shutil.which("ruff") is not None,
            unavailable_reason="ruff binary not found on PATH" if not shutil.which("ruff") else "",
        ),
        Candidate(
            id="subllm-gemini",
            tool_class=ToolClass.API,
            client="subllm",
            model="google/gemini-2.5-flash",
            transport="api",
            fingerprint="api:subllm:gemini",
            capabilities=frozenset({"simple:coding", "simple:ruff", "other:docs"}),
            available=True,
        ),
        Candidate(
            id="subllm-glm",
            tool_class=ToolClass.API,
            client="subllm",
            model="z-ai/glm-5.3",
            transport="api",
            fingerprint="api:subllm:glm",
            capabilities=frozenset({"simple:coding", "complex:coding", "other:docs"}),
            available=True,
        ),
        Candidate(
            id="cli-aider",
            tool_class=ToolClass.CLI,
            client="aider",
            model="openai/gemini-3.8-flash",
            transport="subprocess",
            fingerprint="cli:aider:gemini",
            capabilities=frozenset({"simple:coding", "complex:coding"}),
            available=shutil.which("aider") is not None,
            unavailable_reason="aider binary not found" if not shutil.which("aider") else "",
        ),
        Candidate(
            id="cli-opencode",
            tool_class=ToolClass.CLI,
            client="opencode",
            model="z-ai/glm-5.3",
            transport="subprocess",
            fingerprint="cli:opencode:glm",
            capabilities=frozenset({"simple:coding", "complex:coding"}),
            available=shutil.which("opencode") is not None,
            unavailable_reason="opencode binary not found" if not shutil.which("opencode") else "",
        ),
    ]


def run_deterministic_ruff_probe(tmp_dir: Path) -> ProbeResult:
    """Run an isolated deterministic ruff benchmark probe."""
    ruff_bin = shutil.which("ruff")
    if not ruff_bin:
        return ProbeResult(status="unavailable", duration_ms=0, detail="ruff not installed")

    test_file = tmp_dir / "probe_sample.py"
    test_file.write_text("import os\n\ndef hello():\n    return 'world'\n", encoding="utf-8")

    start = time.perf_counter()
    try:
        proc = subprocess.run(
            [ruff_bin, "check", "--select", "F401", "--fix", str(test_file)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
        content = test_file.read_text(encoding="utf-8")
        if proc.returncode == 0 and "import os" not in content:
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            return ProbeResult(
                status="ok",
                duration_ms=duration_ms,
                validator_digest=f"sha256:{digest}",
                tokens=0,
                cost=0.0,
                detail="ruff successfully fixed unused import",
            )
        return ProbeResult(
            status="failed",
            duration_ms=duration_ms,
            detail=f"ruff exit {proc.returncode}: {proc.stderr}",
        )
    except Exception as e:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return ProbeResult(status="error", duration_ms=duration_ms, detail=str(e))
