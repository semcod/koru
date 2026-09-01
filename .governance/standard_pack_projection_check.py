#!/usr/bin/env python3
"""Verify content-addressed HOME standard projection evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

LEVELS = {f"S{number}": number for number in range(5)}
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "semcod.standard-pack-projection/v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def load(path: Path) -> Any:
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError(f"missing or oversized JSON document: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} has invalid fields")
    return value


def source_artifact(value: Any, repository: str, revision: str, label: str) -> dict[str, Any]:
    item = exact(value, {"path", "uri", "sha256"}, label)
    path = item["path"]
    if not isinstance(path, str) or not path or path.startswith("/") or ".." in Path(path).parts:
        raise ValueError(f"{label}.path is unsafe")
    expected_uri = f"https://github.com/{repository}/blob/{revision}/{path}"
    if item["uri"] != expected_uri or SHA256.fullmatch(str(item["sha256"])) is None:
        raise ValueError(f"{label} is not revision- and digest-bound")
    return item


def receipt(value: Any, label: str) -> tuple[dict[str, Any], str]:
    wrapper = exact(value, {"sha256", "snapshot"}, label)
    observed = digest_bytes(canonical(wrapper["snapshot"]))
    if wrapper["sha256"] != observed:
        raise ValueError(f"{label} canonical digest drift")
    return wrapper["snapshot"], observed


def validate_ci(value: Any, source: dict[str, Any]) -> str:
    snapshot, observed = receipt(value, "ciReceipt")
    schema = snapshot.get("schema") if isinstance(snapshot, dict) else None
    common = {
        "repository",
        "subjectSha",
        "checkName",
        "conclusion",
        "completedAt",
        "sourceUri",
    }
    if schema == "semcod.ci-check-receipt/v1":
        exact(
            snapshot,
            common
            | {
                "schema",
                "workflowPath",
                "workflowSha256",
                "runId",
                "runAttempt",
                "event",
                "jobId",
            },
            "ciReceipt.snapshot",
        )
        if snapshot["repository"] != source["repository"] or snapshot["subjectSha"] != source["revision"]:
            raise ValueError("upstream CI receipt does not bind the source revision")
        if snapshot["event"] not in {"push", "pull_request"}:
            raise ValueError("upstream CI receipt has an unsupported event")
        if SHA256.fullmatch(str(snapshot["workflowSha256"])) is None:
            raise ValueError("upstream CI workflow is not digest-bound")
    elif schema == "semcod.projection-ci-receipt/v1":
        exact(
            snapshot,
            common
            | {
                "schema",
                "statusId",
                "sourceRevision",
                "sourceProjectionSha256",
            },
            "ciReceipt.snapshot",
        )
        if snapshot["repository"] != "semcod/koru":
            raise ValueError("projection CI receipt belongs to another adopter")
        if snapshot["sourceRevision"] != source["revision"]:
            raise ValueError("projection CI receipt does not bind the HOME revision")
        if snapshot["sourceProjectionSha256"] != digest_bytes(canonical(source)):
            raise ValueError("projection CI receipt does not bind the projected source")
    else:
        raise ValueError("unsupported CI receipt schema")
    if (
        snapshot["conclusion"] != "success"
        or SHA1.fullmatch(str(snapshot["subjectSha"])) is None
        or not str(snapshot["sourceUri"]).startswith("https://api.github.com/")
    ):
        raise ValueError("CI receipt is not a successful immutable-subject receipt")
    return observed


def validate_protection(value: Any, ci_snapshot: dict[str, Any]) -> str:
    snapshot, observed = receipt(value, "protectionReceipt")
    exact(
        snapshot,
        {
            "schema",
            "repository",
            "rulesetId",
            "rulesetName",
            "enforcement",
            "target",
            "branchSelector",
            "requiredCheck",
            "strict",
            "sourceUri",
        },
        "protectionReceipt.snapshot",
    )
    if (
        snapshot["schema"] != "semcod.ruleset-receipt/v1"
        or snapshot["repository"] != ci_snapshot["repository"]
        or snapshot["requiredCheck"] != ci_snapshot["checkName"]
        or snapshot["enforcement"] != "active"
        or snapshot["target"] != "branch"
        or snapshot["strict"] is not True
        or not str(snapshot["sourceUri"]).startswith("https://api.github.com/")
    ):
        raise ValueError("S4 ruleset does not require the exact successful S3 check")
    return observed


def validate_projection(root: Path, record: dict[str, Any]) -> None:
    pack_id = record.get("id")
    slug = str(pack_id).removeprefix("wellmanifest/")
    projection_path = root / ".governance" / "standard-pack-evidence" / f"{slug}.json"
    projection = exact(
        load(projection_path),
        {
            "schema",
            "packId",
            "version",
            "claimedLevel",
            "source",
            "localBindings",
            "ciReceipt",
            "protectionReceipt",
        },
        f"projection {pack_id}",
    )
    if projection["schema"] != SCHEMA or projection["packId"] != pack_id:
        raise ValueError(f"projection identity mismatch for {pack_id}")
    if projection["version"] != record.get("version") or projection["claimedLevel"] != record.get("level"):
        raise ValueError(f"projection version or level mismatch for {pack_id}")
    source = exact(
        projection["source"],
        {"repository", "revision", "contract", "conformance"},
        f"{pack_id}.source",
    )
    if source["repository"] != pack_id or source["revision"] != record.get("revision"):
        raise ValueError(f"source identity mismatch for {pack_id}")
    if SHA1.fullmatch(str(source["revision"])) is None:
        raise ValueError(f"source revision is not immutable for {pack_id}")
    contract = source_artifact(source["contract"], pack_id, source["revision"], f"{pack_id}.contract")
    conformance = source_artifact(source["conformance"], pack_id, source["revision"], f"{pack_id}.conformance")

    expected_artifacts = {projection_path.relative_to(root).as_posix(): digest_file(projection_path)}
    bindings = projection["localBindings"]
    if not isinstance(bindings, list):
        raise ValueError(f"localBindings must be an array for {pack_id}")
    roles = {"contract": contract, "conformance": conformance}
    for index, raw in enumerate(bindings):
        binding = exact(raw, {"target", "sourceRole", "sha256"}, f"{pack_id}.localBindings[{index}]")
        target = binding["target"]
        if not isinstance(target, str) or target.startswith("/") or ".." in Path(target).parts:
            raise ValueError(f"unsafe local projection target for {pack_id}")
        target_path = root / target
        observed = digest_file(target_path)
        role = roles.get(binding["sourceRole"])
        if role is None or binding["sha256"] != observed or observed != role["sha256"]:
            raise ValueError(f"local projection bytes drifted for {pack_id}: {target}")
        expected_artifacts[target] = observed

    artifacts = record.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError(f"empty artifact claim for {pack_id}")
    actual_artifacts = {item.get("target"): item.get("sha256") for item in artifacts if isinstance(item, dict)}
    if actual_artifacts != expected_artifacts or len(actual_artifacts) != len(artifacts):
        raise ValueError(f"adoption artifacts do not match the generated projection for {pack_id}")

    level = record.get("level")
    if level not in LEVELS:
        raise ValueError(f"unsupported level for {pack_id}")
    ci_digest = None
    ci_snapshot = None
    if LEVELS[level] >= LEVELS["S3"]:
        ci_digest = validate_ci(projection["ciReceipt"], source)
        ci_snapshot = projection["ciReceipt"]["snapshot"]
    elif projection["ciReceipt"] is not None:
        raise ValueError(f"unclaimed CI receipt on S2 projection for {pack_id}")
    protection_digest = None
    if LEVELS[level] >= LEVELS["S4"]:
        protection_digest = validate_protection(projection["protectionReceipt"], ci_snapshot)
    elif projection["protectionReceipt"] is not None:
        raise ValueError(f"unclaimed protection receipt below S4 for {pack_id}")

    evidence = record.get("evidence")
    if not isinstance(evidence, list) or len(evidence) != LEVELS[level] + 1:
        raise ValueError(f"evidence chain is incomplete for {pack_id}")
    by_level = {item.get("level"): item for item in evidence if isinstance(item, dict)}
    expected = {
        "S0": (contract["uri"], contract["sha256"]),
        "S1": (conformance["uri"], conformance["sha256"]),
        "S2": (
            f"urn:sha256:{expected_artifacts[projection_path.relative_to(root).as_posix()]}",
            expected_artifacts[projection_path.relative_to(root).as_posix()],
        ),
    }
    if ci_digest is not None:
        expected["S3"] = (f"urn:sha256:{ci_digest}", ci_digest)
    if protection_digest is not None:
        expected["S4"] = (f"urn:sha256:{protection_digest}", protection_digest)
    for evidence_level, (uri, sha256) in expected.items():
        if by_level.get(evidence_level) != {"level": evidence_level, "uri": uri, "sha256": sha256}:
            raise ValueError(f"{pack_id} has invalid {evidence_level} evidence")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    root = args.root.resolve()
    findings: list[str] = []
    try:
        adoption = load(root / ".governance" / "standard-adoption.json")
        records = adoption.get("adoptions") if isinstance(adoption, dict) else None
        if not isinstance(records, list) or not records:
            raise ValueError("standard adoption has no records")
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("standard adoption record is not an object")
            validate_projection(root, record)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        findings.append(str(error))
    result = {
        "schema": "semcod.standard-pack-projection-report/v1",
        "ok": not findings,
        "findings": findings,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"standard-pack-projection-check: ok={result['ok']} findings={len(findings)}")
        for finding in findings:
            print(f"STD-PROJECTION: {finding}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
