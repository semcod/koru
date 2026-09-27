#!/usr/bin/env python3
"""Readback and canary gate for the protected publication ruleset.

Compares the live GitHub ruleset against the tracked desired profile in
``ruleset.desired.json`` and validates canary evidence records captured while
exercising a ruleset deployment. Read-only against GitHub: ``readback`` and
``verify`` never mutate a ruleset; deployment itself is owned by the live
deployment acceptance ticket.

Subcommands:
  readback  Print the live ruleset JSON (or save it with --output).
  verify    Diff the observed ruleset (live or --from-file) against the
            desired profile; exit 0 only when conformant.
  canary    Validate canary evidence records; exit 0 only when every record
            is structurally bound and matches its expected outcome.

``--self-test`` runs the offline unit suite over the tracked baseline fixture
and synthetic canary records.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

SCHEMA = "new-project.publication-ruleset/v1"
CANARY_SCHEMA = "new-project.ruleset-canary/v1"
REVIEW_REQUIRED_PATTERN = re.compile(
    r"approving review|review is required|reviewed by|approval", re.IGNORECASE
)
BINDING_FIELDS = ("repository", "ticket", "actor", "observedAt")
POSITIVE_BINDINGS = ("repository", "pullRequest", "headSha", "ticket", "actor")


def policy_dir() -> Path:
    return Path(__file__).resolve().parent


def load_desired(path: Path | None = None) -> dict:
    source = path or policy_dir() / "ruleset.desired.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise SystemExit(f"unknown schema in {source}: {data.get('schema')!r}")
    return data


def fetch_ruleset(repository: str, ruleset_id: int) -> dict:
    proc = subprocess.run(
        ["gh", "api", f"repos/{repository}/rulesets/{ruleset_id}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"ruleset readback failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def rule_of_type(ruleset: dict, rule_type: str) -> dict | None:
    for rule in ruleset.get("rules", []):
        if rule.get("type") == rule_type:
            return rule
    return None


def check_contexts(rule: dict) -> list[str]:
    checks = rule.get("parameters", {}).get("required_status_checks", []) or []
    return sorted(entry.get("context", "") for entry in checks)


def bypass_signature(bypass_actors: list[dict]) -> list[list]:
    return sorted(
        [entry.get("actor_id"), entry.get("actor_type"), entry.get("bypass_mode")]
        for entry in bypass_actors
    )


def compare_rulesets(observed: dict, desired_body: dict) -> list[dict]:
    """Return one comparison record per enforced expectation."""

    records: list[dict] = []

    def add(name: str, expected, actual) -> None:
        records.append(
            {
                "check": name,
                "expected": expected,
                "actual": actual,
                "ok": expected == actual,
            }
        )

    add("enforcement", desired_body["enforcement"], observed.get("enforcement"))
    add(
        "conditions.ref_name.include",
        desired_body["conditions"]["ref_name"]["include"],
        observed.get("conditions", {}).get("ref_name", {}).get("include"),
    )
    add("rule.deletion", True, rule_of_type(observed, "deletion") is not None)
    add(
        "rule.non_fast_forward",
        True,
        rule_of_type(observed, "non_fast_forward") is not None,
    )

    desired_pull_rule = next(
        rule for rule in desired_body["rules"] if rule["type"] == "pull_request"
    )
    params = desired_pull_rule["parameters"]
    observed_pull = rule_of_type(observed, "pull_request")
    observed_params = (observed_pull or {}).get("parameters", {})
    for field in (
        "required_approving_review_count",
        "dismiss_stale_reviews_on_push",
        "require_last_push_approval",
        "required_review_thread_resolution",
        "require_extra_approval_for_unattributed_changes",
        "allowed_merge_methods",
    ):
        add(f"pull_request.{field}", params[field], observed_params.get(field))

    desired_checks_rule = next(
        (
            rule
            for rule in desired_body["rules"]
            if rule["type"] == "required_status_checks"
        ),
        None,
    )
    observed_checks = rule_of_type(observed, "required_status_checks") or {}
    if desired_checks_rule is None:
        # Fork-sandbox variant: the sandbox cannot produce the protected check
        # contexts, so the profile drops the rule and the readback must confirm
        # the deployed sandbox ruleset drops it with it.
        add(
            "required_status_checks.absent",
            True,
            rule_of_type(observed, "required_status_checks") is None,
        )
    else:
        add(
            "required_status_checks.strict",
            desired_checks_rule["parameters"]["strict_required_status_checks_policy"],
            observed_checks.get("parameters", {}).get("strict_required_status_checks_policy"),
        )
        add(
            "required_status_checks.contexts",
            sorted(
                entry["context"]
                for entry in desired_checks_rule["parameters"]["required_status_checks"]
            ),
            check_contexts(observed_checks),
        )
    add(
        "bypass_actors",
        bypass_signature(desired_body["bypass_actors"]),
        bypass_signature(observed.get("bypass_actors", [])),
    )
    return records


def render_report(records: list[dict]) -> int:
    failures = [record for record in records if not record["ok"]]
    for record in records:
        marker = "PASS" if record["ok"] else "GAP "
        print(
            f"{marker} {record['check']}: expected={record['expected']!r} "
            f"actual={record['actual']!r}"
        )
    state = "conformant" if not failures else f"{len(failures)} gap(s)"
    print(f"ruleset verification: {state}")
    return 0 if not failures else 1


def validate_canary(record: dict, trusted_app_login: str | None) -> list[str]:
    """Return the list of validation errors for one canary record."""

    errors: list[str] = []
    kind = record.get("kind")
    if record.get("schema") != CANARY_SCHEMA:
        errors.append(f"schema must be {CANARY_SCHEMA}")
    for field in BINDING_FIELDS:
        if not record.get(field):
            errors.append(f"missing binding field {field}")
    if errors:
        return errors

    outcome = record.get("outcome")
    evidence = record.get("evidence")
    if not isinstance(evidence, dict):
        return errors + ["evidence must be an object"]

    if kind == "negative_author_merge_rejected":
        for field in ("pullRequest", "headSha"):
            if record.get(field) in (None, ""):
                errors.append(f"missing binding field {field}")
        if outcome != "rejected":
            errors.append("outcome must be rejected")
        status = evidence.get("httpStatus")
        if status not in (403, 405, 422):
            errors.append("httpStatus must be 403, 405 or 422")
        message = evidence.get("message")
        if not isinstance(message, str) or not REVIEW_REQUIRED_PATTERN.search(message):
            errors.append("message must state a required approving review")
        if evidence.get("merged") is not False:
            errors.append("merged must be false")
    elif kind == "positive_app_reviewed_merge":
        for field in POSITIVE_BINDINGS:
            if record.get(field) in (None, ""):
                errors.append(f"missing binding field {field}")
        if outcome != "merged":
            errors.append("outcome must be merged")
        review = evidence.get("review")
        if not isinstance(review, dict):
            errors.append("evidence.review must be an object")
        else:
            if review.get("state") != "APPROVED":
                errors.append("review.state must be APPROVED")
            if review.get("commitId") != record.get("headSha"):
                errors.append("review.commitId must equal the record headSha")
            if review.get("author") != trusted_app_login or not trusted_app_login:
                errors.append(
                    "review.author must equal the trusted validator app login"
                )
        if evidence.get("merged") is not True:
            errors.append("merged must be true")
        if evidence.get("mergedBy") != trusted_app_login or not trusted_app_login:
            errors.append("evidence.mergedBy must be the trusted validator app login")
        submitted = review.get("submittedAt") if isinstance(review, dict) else None
        merged_at = evidence.get("mergedAt")
        if isinstance(submitted, str) and isinstance(merged_at, str):
            if submitted > merged_at:
                errors.append("review must be submitted before the merge")
        else:
            errors.append("review.submittedAt and evidence.mergedAt are required")
    elif kind == "ruleset_roundtrip":
        if outcome != "conformant":
            errors.append("outcome must be conformant")
        observed = evidence.get("observedRuleset")
        if not isinstance(observed, dict):
            errors.append("evidence.observedRuleset must embed the live readback")
    elif kind == "recovery_ruleset_removed":
        if outcome != "absent":
            errors.append("outcome must be absent")
        if evidence.get("rulesetId") in (None, ""):
            errors.append("evidence.rulesetId is required")
        remaining = evidence.get("remainingRulesetIds")
        if not isinstance(remaining, list) or evidence.get("rulesetId") in remaining:
            errors.append("evidence must show the ruleset absent from remaining ids")
    elif kind == "recovery_ruleset_restored":
        if outcome != "restored":
            errors.append("outcome must be restored")
        if evidence.get("restoredVersionId") in (None, ""):
            errors.append("evidence.restoredVersionId is required")
    else:
        errors.append(f"unknown canary kind {kind!r}")
    return errors


def run_self_test() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SelfTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


class SelfTest(unittest.TestCase):
    """Offline suite over the tracked baseline fixture and synthetic records."""

    @classmethod
    def setUpClass(cls):
        cls.desired = load_desired()
        cls.baseline = json.loads(
            (
                policy_dir() / "fixtures" / "ruleset-observed-2026-09-27.json"
            ).read_text(encoding="utf-8")
        )

    def observed_from_desired(self) -> dict:
        body = json.loads(json.dumps(self.desired["desired"]))
        body.update(
            {
                "id": self.desired["rulesetId"],
                "source_type": "Repository",
                "source": self.desired["repository"],
                "node_id": "RRS_test",
                "created_at": "2026-09-01T17:47:59Z",
                "updated_at": "2026-09-27T00:00:00Z",
            }
        )
        return body

    def gaps(self, observed) -> list[dict]:
        return [r for r in compare_rulesets(observed, self.desired["desired"]) if not r["ok"]]

    def test_baseline_reports_exactly_the_migration_gaps(self):
        gaps = self.gaps(self.baseline)
        names = sorted(gap["check"] for gap in gaps)
        self.assertEqual(
            names,
            [
                "bypass_actors",
                "pull_request.require_last_push_approval",
                "pull_request.required_approving_review_count",
            ],
        )

    def test_baseline_preserves_checks_and_strictness(self):
        records = {
            r["check"]: r for r in compare_rulesets(self.baseline, self.desired["desired"])
        }
        for name in (
            "required_status_checks.strict",
            "required_status_checks.contexts",
            "rule.deletion",
            "rule.non_fast_forward",
            "pull_request.dismiss_stale_reviews_on_push",
            "pull_request.required_review_thread_resolution",
        ):
            self.assertTrue(records[name]["ok"], name)

    def test_desired_body_is_conformant_roundtrip(self):
        self.assertEqual(self.gaps(self.observed_from_desired()), [])

    def test_fork_variant_roundtrip_without_checks_rule(self):
        observed = self.observed_from_desired()
        observed["rules"] = [
            rule
            for rule in observed["rules"]
            if rule["type"] != "required_status_checks"
        ]
        variant = json.loads(json.dumps(self.desired["desired"]))
        variant["rules"] = [
            rule
            for rule in variant["rules"]
            if rule["type"] != "required_status_checks"
        ]
        self.assertEqual([r for r in compare_rulesets(observed, variant) if not r["ok"]], [])

    def test_missing_required_check_is_a_gap(self):
        observed = self.observed_from_desired()
        checks = next(
            rule
            for rule in observed["rules"]
            if rule["type"] == "required_status_checks"
        )
        checks["parameters"]["required_status_checks"] = checks["parameters"][
            "required_status_checks"
        ][:1]
        gaps = self.gaps(observed)
        self.assertEqual([gap["check"] for gap in gaps], ["required_status_checks.contexts"])

    def negative_record(self) -> dict:
        return {
            "schema": CANARY_SCHEMA,
            "kind": "negative_author_merge_rejected",
            "repository": "example/koru",
            "pullRequest": 7,
            "headSha": "a" * 40,
            "ticket": "ticket-325",
            "actor": "example-operator",
            "observedAt": "2026-09-27T20:00:00Z",
            "outcome": "rejected",
            "evidence": {
                "httpStatus": 403,
                "message": "At least 1 approving review is required by someone other than the last pusher.",
                "merged": False,
            },
        }

    def test_negative_canary_passes(self):
        self.assertEqual(validate_canary(self.negative_record(), None), [])
        observed = self.negative_record()
        observed["evidence"]["httpStatus"] = 405
        observed["evidence"]["message"] = (
            "Repository rule violations found: New changes require approval "
            "from someone other than the last pusher."
        )
        self.assertEqual(validate_canary(observed, None), [])

    def test_negative_canary_rejects_merge_success(self):
        record = self.negative_record()
        record["outcome"] = "merged"
        self.assertTrue(validate_canary(record, None))

    def test_negative_canary_requires_head_binding(self):
        record = self.negative_record()
        del record["headSha"]
        self.assertTrue(validate_canary(record, None))

    def test_negative_canary_requires_review_reason(self):
        record = self.negative_record()
        record["evidence"]["message"] = "Server error"
        self.assertTrue(validate_canary(record, None))

    def positive_record(self) -> dict:
        return {
            "schema": CANARY_SCHEMA,
            "kind": "positive_app_reviewed_merge",
            "repository": "semcod/koru",
            "pullRequest": 9,
            "headSha": "b" * 40,
            "ticket": "ticket-325",
            "actor": "koru-validator",
            "observedAt": "2026-09-27T21:00:00Z",
            "outcome": "merged",
            "evidence": {
                "merged": True,
                "mergedBy": "koru-validator",
                "mergedAt": "2026-09-27T20:59:00Z",
                "review": {
                    "author": "koru-validator",
                    "state": "APPROVED",
                    "commitId": "b" * 40,
                    "submittedAt": "2026-09-27T20:58:00Z",
                },
            },
        }

    def test_positive_canary_fails_closed_without_trusted_login(self):
        self.assertTrue(validate_canary(self.positive_record(), None))

    def test_positive_canary_passes_with_trusted_login(self):
        self.assertEqual(validate_canary(self.positive_record(), "koru-validator"), [])

    def test_positive_canary_rejects_stale_head_review(self):
        record = self.positive_record()
        record["evidence"]["review"]["commitId"] = "c" * 40
        self.assertTrue(validate_canary(record, "koru-validator"))

    def test_roundtrip_canary_reembeds_observed_ruleset(self):
        record = {
            "schema": CANARY_SCHEMA,
            "kind": "ruleset_roundtrip",
            "repository": "example/koru",
            "ticket": "ticket-325",
            "actor": "example-operator",
            "observedAt": "2026-09-27T20:30:00Z",
            "outcome": "conformant",
            "evidence": {"observedRuleset": self.observed_from_desired()},
        }
        errors = validate_canary(record, None)
        self.assertEqual(errors, [])
        self.assertEqual(self.gaps(record["evidence"]["observedRuleset"]), [])

    def test_recovery_removed_canary(self):
        record = {
            "schema": CANARY_SCHEMA,
            "kind": "recovery_ruleset_removed",
            "repository": "example/koru",
            "ticket": "ticket-325",
            "actor": "example-operator",
            "observedAt": "2026-09-27T20:45:00Z",
            "outcome": "absent",
            "evidence": {"rulesetId": 555001, "remainingRulesetIds": []},
        }
        self.assertEqual(validate_canary(record, None), [])
        record["evidence"]["remainingRulesetIds"] = [555001]
        self.assertTrue(validate_canary(record, None))

    def test_unknown_kind_is_rejected(self):
        record = self.negative_record()
        record["kind"] = "mystery"
        self.assertTrue(validate_canary(record, None))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true", help="run the offline suite")
    sub = parser.add_subparsers(dest="command")

    readback = sub.add_parser("readback", help="print the live ruleset JSON")
    readback.add_argument("--repository", default=None)
    readback.add_argument("--ruleset-id", type=int, default=None)
    readback.add_argument("--output", type=Path, default=None)

    verify = sub.add_parser("verify", help="diff observed vs desired profile")
    verify.add_argument("--repository", default=None)
    verify.add_argument("--ruleset-id", type=int, default=None)
    verify.add_argument("--from-file", type=Path, default=None)
    verify.add_argument("--desired", type=Path, default=None)

    canary = sub.add_parser("canary", help="validate canary evidence records")
    canary.add_argument("evidence", type=Path)
    canary.add_argument("--trusted-app-login", default=None)

    args = parser.parse_args(argv)
    if args.self_test:
        return run_self_test()
    if args.command == "readback":
        desired = load_desired()
        repository = args.repository or desired["repository"]
        ruleset_id = args.ruleset_id or desired["rulesetId"]
        observed = fetch_ruleset(repository, ruleset_id)
        if args.output:
            args.output.write_text(
                json.dumps(observed, indent=2, sort_keys=False) + "\n", encoding="utf-8"
            )
            print(f"readback saved to {args.output}")
        else:
            print(json.dumps(observed, indent=2))
        return 0
    if args.command == "verify":
        desired = load_desired(args.desired)
        repository = args.repository or desired["repository"]
        ruleset_id = args.ruleset_id or desired["rulesetId"]
        if args.from_file:
            observed = json.loads(args.from_file.read_text(encoding="utf-8"))
        else:
            observed = fetch_ruleset(repository, ruleset_id)
        return render_report(compare_rulesets(observed, desired["desired"]))
    if args.command == "canary":
        payload = json.loads(args.evidence.read_text(encoding="utf-8"))
        records = payload if isinstance(payload, list) else payload.get("records")
        if not isinstance(records, list) or not records:
            print("canary evidence must be a list of records (or wrap them in records)")
            return 2
        exit_code = 0
        for index, record in enumerate(records):
            errors = validate_canary(record, args.trusted_app_login)
            label = record.get("kind") or f"record {index}"
            if errors:
                exit_code = 1
                print(f"FAIL {label}: " + "; ".join(errors))
            else:
                print(f"PASS {label}: {record.get('repository')} outcome={record.get('outcome')}")
        print(f"canary evidence: {'valid' if exit_code == 0 else 'invalid'}")
        return exit_code
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
