"""Pinned, opt-in admission for new fleet scan tickets; never execution authority."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

GATE_SHA256 = "07d7410be09ddd7b24f73171a5ddd2980bcd4dbffb85a49007ae762dab0450d6"


def _read(path: str) -> bytes:
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise ValueError("absolute_path_required")
    with Path(path).open("rb") as stream:
        data = stream.read(65537)
    if len(data) > 65536:
        raise ValueError("input_too_large")
    return data


def scan_admission(project: Path) -> dict[str, Any] | None:
    """Return None for standalone mode, otherwise an explicit admission result.

    Any configured fleet input activates validation, including empty variables.
    Only the operator's digest-pinned absolute project map defines identity.
    """
    names = ("KORU_FLEET_ADMISSION_ENABLED", "KORU_FLEET_ADMISSION_CONFIG",
             "KORU_FLEET_ADMISSION_CONFIG_DIGEST")
    if not any(name in os.environ for name in names):
        return None
    denied: dict[str, Any] = {"admit_new": False, "authorization_granted": False,
                              "stage": "observe"}
    try:
        if os.environ.get(names[0], "1") != "1":
            raise ValueError("invalid_enable_value")
        raw = _read(os.environ.get(names[1], ""))
        if hashlib.sha256(raw).hexdigest() != os.environ.get(names[2], ""):
            raise ValueError("configuration_digest_mismatch")
        config = json.loads(raw)
        if config.get("schema") != "koru.fleet-admission-config/v1":
            raise ValueError("unsupported_configuration")
        source = _read(config["gate_path"])
        if hashlib.sha256(source).hexdigest() != GATE_SHA256:
            raise ValueError("gate_digest_mismatch")
        policy = config["projects"][str(project.resolve())]
        repository, base = policy["repository"], policy["base_branch"]
        if (not isinstance(repository, str) or repository.count("/") != 1
                or not all(repository.split("/")) or repository.startswith("-")
                or not isinstance(base, str) or not base or base.startswith("-")):
            raise ValueError("invalid_repository_policy")
        for key in ("resume_path", "prs_path"):
            if not isinstance(config[key], str) or not Path(config[key]).is_absolute():
                raise ValueError("absolute_observation_path_required")
        pins = policy.get("runtime_pins", {})
        if not isinstance(pins, dict):
            raise ValueError("invalid_runtime_pins")
        with tempfile.TemporaryDirectory(prefix="koru-fleet-admission-") as tmp:
            pin_path = Path(tmp) / "pins.json"
            pin_path.write_text(json.dumps(pins), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-I", "-c", source.decode("utf-8"),
                 "--resume", config["resume_path"], "--prs", config["prs_path"],
                 "--repository", repository, "--base-branch", base,
                 "--runtime-pins", str(pin_path)],
                capture_output=True, text=True, timeout=30, check=False,
            )
        decision = json.loads(result.stdout)
        # The pinned CLI omits identity when observation parsing fails. Such
        # responses can report a denial reason, but can never admit work.
        if (result.returncode != 0
                and decision.get("schema") == "autonom.fleet-admission/v1"
                and decision.get("admit_new") is False
                and decision.get("authorization_granted") is False
                and isinstance(decision.get("error"), str)):
            return {**denied, "error": decision["error"][:256]}
        if (decision.get("schema") != "autonom.fleet-admission/v1"
                or decision.get("repository") != repository
                or decision.get("authorization_granted") is not False):
            raise ValueError("invalid_decision_binding")
        return {"admit_new": result.returncode == 0
                and decision.get("admit_new") is True
                and decision.get("stage") == "admit_issue",
                "authorization_granted": False, "stage": decision.get("stage"),
                "repository": repository, "reasons": decision.get("reasons", []),
                "error": decision.get("error")}
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            subprocess.TimeoutExpired) as error:
        return {**denied, "error": type(error).__name__}
