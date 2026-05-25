"""Project and environment discovery checks for ``koru --doctor``."""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

from koru.doctor_constants import FAIL, PASS, WARN
from koru.policy import policy_path
from koru.project_pipeline import project_pipeline_path
from koru.runtime import planfile_dir


def _check_detected_environment(project: Path) -> tuple[str, str]:
    del project
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    bits = [
        f"os={platform.system().lower()} {platform.release()} ({platform.machine()})",
        f"python={py}",
        f"executable={sys.executable}",
    ]
    virtual_env = os.environ.get("VIRTUAL_ENV", "").strip()
    if not virtual_env and getattr(sys, "base_prefix", sys.prefix) != sys.prefix:
        virtual_env = sys.prefix
    bits.append(f"virtual_env={virtual_env or 'none'}")
    lane = os.environ.get("KORU_AGENT_LANE", "").strip()
    if lane:
        bits.append(f"agent_lane={lane}")
    return PASS, "; ".join(bits)


def _detected_configuration_presence_bits(
    *,
    planfile_cfg: Path,
    policy_cfg: Path,
    pipeline_cfg: Path,
) -> list[str]:
    return [
        f"planfile_config={'present' if planfile_cfg.is_file() else 'missing'}",
        f"policy_yaml={'present' if policy_cfg.is_file() else 'missing'}",
        f"koru_yaml={'present' if pipeline_cfg.is_file() else 'missing'}",
    ]


def _detected_configuration_json_bits(
    *,
    project: Path,
    payload: dict[str, object],
) -> tuple[str, list[str]]:
    """Return (status, detail_bits) derived from .koru/project.json payload."""
    status = PASS
    bits: list[str] = []

    schema = str(payload.get("schema", "")).strip()
    declared_project = str(payload.get("project", "")).strip()
    bits.append(f"koru_project_json=present(schema={schema or 'unknown'})")

    if declared_project:
        try:
            if Path(declared_project).expanduser().resolve() != project.resolve():
                status = WARN
                bits.append("project_path_mismatch=true")
        except OSError:
            status = WARN
            bits.append("project_path_mismatch=unknown")

    if schema and schema != "koru.project/v1":
        status = WARN
        bits.append("schema_mismatch=true")

    return status, bits


def _check_detected_configuration(project: Path) -> tuple[str, str]:
    koru_project = project / ".koru" / "project.json"
    planfile_cfg = planfile_dir(project) / "config.yaml"
    policy_cfg = policy_path(project)
    pipeline_cfg = project_pipeline_path(project)

    status = PASS
    detail_bits = _detected_configuration_presence_bits(
        planfile_cfg=planfile_cfg,
        policy_cfg=policy_cfg,
        pipeline_cfg=pipeline_cfg,
    )

    if koru_project.is_file():
        try:
            payload = json.loads(koru_project.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return FAIL, f".koru/project.json malformed JSON: {exc}"

        payload_status, payload_bits = _detected_configuration_json_bits(
            project=project,
            payload=payload,
        )
        detail_bits.extend(payload_bits)
        if payload_status != PASS:
            status = payload_status
    else:
        detail_bits.append("koru_project_json=missing")
        if planfile_cfg.is_file():
            status = WARN

    return status, "; ".join(detail_bits)