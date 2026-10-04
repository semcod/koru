from __future__ import annotations

import copy
import hashlib
import json
import secrets
import ssl
import subprocess
import threading
import unittest
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from koru.repository_admission import BINDINGS, AdmissionClient, AdmissionUnavailable, main


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class AdmissionClientTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.primary = self.root / "target"
        self.primary.mkdir()
        def git(*args):
            return subprocess.run(["git", *args], cwd=self.primary, capture_output=True,
                                  text=True, check=True, timeout=10).stdout.strip()
        git("init", "-b", "main")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "--allow-empty", "-m", "fixture baseline")
        git("remote", "add", "origin", "https://github.com/example/target.git")
        base = git("rev-parse", "HEAD")
        self.now = datetime.now(UTC)
        self.bearer = secrets.token_urlsafe(32)
        self.credential = self.root / "credential"
        self.credential.write_text(self.bearer + "\n")
        self.credential.chmod(0o600)
        self.cert = self.root / "cert.pem"
        self.key = self.root / "key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                        "-keyout", str(self.key), "-out", str(self.cert), "-days", "1",
                        "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost"],
                       check=True, capture_output=True, timeout=10)
        self.request = {
            "schema": "subactor.repository-admission-request/v1", "requestId": "request-a",
            "repositoryRef": "example/target", "ticketId": "ticket-001",
            "branchRef": "refs/heads/ticket/001-admission", "worktreeId": "ticket-001--admission",
            "ownerSession": "session-a", "planHash": "1" * 64, "scopeHash": "2" * 64, "baseSha": base,
        }
        self.result = {
            "schema": "subactor.repository-admission/v1", "requestId": self.request["requestId"],
            "authorizationGranted": True, "capabilities": ["workspace_write"],
            "policySha256": "4" * 64, "authorityRef": "policy:independent-admission",
            "admissionExpiresAt": (self.now + timedelta(hours=1)).isoformat(),
            "bindings": {k: self.request[k] for k in BINDINGS},
            "lease": {"schema": "wellmanifest.change-lease/v1", "phase": "editing", "leaseId": "lease-a",
                      "ownerActor": "agent:koru", "targetBranch": "main", "leaseRevision": 2,
                      "fencingToken": 1, "expiresAt": (self.now + timedelta(seconds=600)).isoformat(),
                      **{k: self.request[k] for k in BINDINGS - {"baseSha"}}},
        }
        self.calls = []
        self.status = 200
        self.mutate = None
        test = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                test.calls.append({"path": self.path, "request": payload,
                                   "authenticated": self.headers["Authorization"] == "Bearer " + test.bearer})
                if test.mutate:
                    test.mutate()
                self.send_response(test.status)
                self.send_header("Content-Type", "application/json")
                if test.status == 302:
                    self.send_header("Location", f"https://localhost:{test.port}/redirected")
                self.end_headers()
                self.wfile.write(json.dumps(test.result).encode())

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(self.cert, self.key)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.config = {
            "schema": "koru.repository-admission-client/v1", "endpoint": f"https://localhost:{self.port}",
            "ca_file": str(self.cert), "ca_sha256": digest(self.cert.read_bytes()),
            "credential_file": str(self.credential), "policy_sha256": self.result["policySha256"],
            "authority_ref": self.result["authorityRef"], "owner_actor": "agent:koru",
        }
        self.config_path = self.root / "client.json"
        self.client = self.load()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def load(self):
        self.config_path.write_text(json.dumps(self.config))
        self.pin = digest(self.config_path.read_bytes())
        return AdmissionClient(self.config_path, self.pin, self.primary, clock=lambda: self.now)

    def test_verified_acquisition_and_current_check_use_exact_endpoint(self):
        result = self.client.acquire(self.request)
        self.assertEqual(result, self.result)
        self.assertEqual(self.client.check(self.request, result), result)
        self.assertEqual([c["path"] for c in self.calls],
                         ["/v1/repository-admissions/acquire", "/v1/repository-admissions/check"])
        self.assertTrue(all(c["authenticated"] for c in self.calls))
        self.assertEqual(self.calls[-1]["request"]["leaseRevision"], 2)
        self.assertEqual(self.calls[-1]["request"]["fencingToken"], 1)

    def test_inherited_proxy_cannot_receive_the_credential(self):
        with patch.dict("os.environ", {"HTTPS_PROXY": "http://127.0.0.1:1", "https_proxy": "http://127.0.0.1:1"}):
            self.assertEqual(self.client.acquire(self.request), self.result)

    def test_changed_config_or_ca_pin_denies_before_request(self):
        self.config_path.write_text(self.config_path.read_text() + "\n")
        with self.assertRaisesRegex(AdmissionUnavailable, "configuration pin mismatch"):
            self.client.acquire(self.request)
        self.client = self.load()
        self.cert.write_bytes(self.cert.read_bytes() + b"\n")
        with self.assertRaisesRegex(AdmissionUnavailable, "certificate pin mismatch"):
            self.client.acquire(self.request)
        self.assertFalse(self.calls)

    def test_local_or_symlinked_configuration_is_not_authority(self):
        local = self.primary / "client.json"
        local.write_bytes(self.config_path.read_bytes())
        with self.assertRaises(AdmissionUnavailable):
            AdmissionClient(local, digest(local.read_bytes()), self.primary)
        self.config_path.unlink()
        self.config_path.symlink_to(local)
        with self.assertRaises(AdmissionUnavailable):
            AdmissionClient(self.config_path, digest(local.read_bytes()), self.primary)

    def test_plain_http_and_url_credentials_are_refused(self):
        for endpoint in (f"http://localhost:{self.port}", f"https://user:password@localhost:{self.port}",
                         f"https://localhost:{self.port}/other", f"https://localhost:{self.port}?credential=x"):
            with self.subTest(endpoint=endpoint), self.assertRaises(AdmissionUnavailable):
                self.config["endpoint"] = endpoint
                self.load()
        self.assertFalse(self.calls)

    def test_world_readable_credential_is_refused(self):
        self.credential.chmod(0o644)
        with self.assertRaisesRegex(AdmissionUnavailable, "private admission credential"):
            self.client.acquire(self.request)
        self.assertFalse(self.calls)

    def test_requested_repository_or_base_mismatch_denies_before_http(self):
        for key, value in (("repositoryRef", "other/target"), ("baseSha", "0" * 40)):
            with self.subTest(key=key), self.assertRaisesRegex(AdmissionUnavailable, "target binding mismatch"):
                self.client.acquire({**self.request, key: value})
        self.assertFalse(self.calls)

    def test_redirects_do_not_reissue_credentials(self):
        self.status = 302
        with self.assertRaisesRegex(AdmissionUnavailable, "refused or unavailable"):
            self.client.acquire(self.request)
        self.assertEqual(len(self.calls), 1)

    def test_all_response_bindings_are_checked(self):
        baseline = copy.deepcopy(self.result)
        changes = [("authorizationGranted", False), ("requestId", "other"), ("policySha256", "5" * 64),
                   ("authorityRef", "policy:other"), ("capabilities", ["workspace_write", "merge"])]
        for key, value in changes:
            with self.subTest(key=key), self.assertRaises(AdmissionUnavailable):
                self.result = copy.deepcopy(baseline)
                self.result[key] = value
                self.client.acquire(self.request)
        for key in BINDINGS:
            with self.subTest(binding=key), self.assertRaises(AdmissionUnavailable):
                self.result = copy.deepcopy(baseline)
                self.result["bindings"][key] = "forged"
                self.client.acquire(self.request)

    def test_invalid_lease_owner_phase_revision_and_fence_are_refused(self):
        baseline = copy.deepcopy(self.result)
        for key, value in (("ownerActor", "agent:other"), ("phase", "released"), ("leaseRevision", True),
                           ("fencingToken", 0), ("scopeHash", "5" * 64), ("targetBranch", "other")):
            with self.subTest(key=key), self.assertRaises(AdmissionUnavailable):
                self.result = copy.deepcopy(baseline)
                self.result["lease"][key] = value
                self.client.acquire(self.request)

    def test_stale_check_cursor_or_cached_expiry_never_authorizes(self):
        receipt = copy.deepcopy(self.result)
        self.result["lease"]["leaseRevision"] += 1
        with self.assertRaisesRegex(AdmissionUnavailable, "stale admission fencing"):
            self.client.check(self.request, receipt)
        self.now += timedelta(seconds=601)
        self.calls.clear()
        with self.assertRaisesRegex(AdmissionUnavailable, "expired"):
            self.client.check(self.request, receipt)
        self.assertFalse(self.calls)

    def renewal(self, *, outcome="accepted"):
        cached = copy.deepcopy(self.result)
        request = {**self.request, "requestId": "renew-one"}
        self.result["requestId"] = request["requestId"]
        self.result["lease"]["leaseRevision"] += 1
        self.result["lease"]["expiresAt"] = (self.now + timedelta(seconds=900)).isoformat()
        receipt = {
            "schema": "wellmanifest.change-lease-receipt/v1", "requestId": request["requestId"],
            "leaseId": "lease-a", "previousRevision": 2, "leaseRevision": 3,
            "previousFencingToken": 1, "fencingToken": 1, "action": "heartbeat",
            "outcome": "accepted", "code": None, "phaseBefore": "editing", "phaseAfter": "editing",
            "headSha": None, "pullRequest": None, "occurredAt": self.now.isoformat(),
        }
        receipt["receiptRef"] = "receipt://change-lease/" + digest(
            json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())
        receipt["outcome"] = outcome
        self.result["renewalReceipt"] = receipt
        return request, cached

    def test_renewal_sends_original_cursor_and_checks_new_current_lease(self):
        request, cached = self.renewal()
        result = self.client.renew(request, cached)
        self.assertEqual(result, self.result)
        self.assertEqual(self.calls[-1]["path"], "/v1/repository-admissions/renew")
        self.assertTrue(self.calls[-1]["authenticated"])
        self.assertEqual(self.calls[-1]["request"],
                         {**request, "leaseId": "lease-a", "leaseRevision": 2, "fencingToken": 1})
        self.assertEqual(self.client.check(request, result), result)
        self.assertEqual(self.calls[-1]["request"]["leaseRevision"], 3)
        self.result["requestId"] = self.request["requestId"]
        with self.assertRaisesRegex(AdmissionUnavailable, "stale admission fencing"):
            self.client.check(self.request, cached)

    def test_lost_response_retry_uses_expired_cache_only_as_cursor(self):
        request, cached = self.renewal(outcome="idempotent")
        self.now += timedelta(seconds=601)
        self.result["lease"]["leaseRevision"] = 4  # A subsequent heartbeat may already exist.
        with self.assertRaisesRegex(AdmissionUnavailable, "expired"):
            self.client.check(self.request, cached)
        self.assertFalse(self.calls)
        self.assertEqual(self.client.renew(request, cached), self.result)
        self.assertEqual(self.calls[-1]["request"]["leaseRevision"], 2)
        self.assertEqual(self.client.renew(request, cached), self.result)
        self.assertEqual(self.calls[-1]["request"], self.calls[-2]["request"])

    def test_renewal_refuses_expired_policy_and_malformed_cached_lease_before_http(self):
        request, cached = self.renewal()
        for key, value in (("expiresAt", "invalid"), ("expiresAt", "2026-01-01T00:00:00"),
                           ("fencingToken", True), ("phase", "released"), ("ownerSession", "foreign")):
            bad = copy.deepcopy(cached)
            bad["lease"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(AdmissionUnavailable):
                self.client.renew(request, bad)
        self.now += timedelta(hours=2)
        with self.assertRaisesRegex(AdmissionUnavailable, "expired"):
            self.client.renew(request, cached)
        self.assertFalse(self.calls)

    def test_renewal_refuses_replacement_fence_stale_revision_and_expired_server_lease(self):
        request, cached = self.renewal()
        baseline = copy.deepcopy(self.result)
        for key, value in (("leaseId", "replacement"), ("fencingToken", 2), ("leaseRevision", 2),
                           ("expiresAt", self.now.isoformat()), ("phase", "released")):
            self.result = copy.deepcopy(baseline)
            self.result["lease"][key] = value
            with self.subTest(key=key), self.assertRaises(AdmissionUnavailable):
                self.client.renew(request, cached)

    def test_renewal_requires_bound_durable_heartbeat_receipt(self):
        request, cached = self.renewal()
        baseline = copy.deepcopy(self.result)
        mutations = (("schema", "other"), ("requestId", "foreign"), ("leaseId", "replacement"),
                     ("previousRevision", True), ("previousRevision", 1), ("leaseRevision", 4),
                     ("previousFencingToken", 2), ("fencingToken", True), ("action", "release"),
                     ("outcome", "rejected"), ("outcome", []), ("code", "denied"), ("phaseBefore", "released"),
                     ("phaseAfter", "frozen"), ("headSha", "a" * 40), ("pullRequest", 1),
                     ("occurredAt", "invalid"), ("receiptRef", "receipt://change-lease/" + "0" * 64))
        for key, value in mutations:
            self.result = copy.deepcopy(baseline)
            self.result["renewalReceipt"][key] = value
            if key != "receiptRef":
                original = {k: v for k, v in self.result["renewalReceipt"].items() if k != "receiptRef"}
                original["outcome"] = "accepted"
                self.result["renewalReceipt"]["receiptRef"] = "receipt://change-lease/" + digest(
                    json.dumps(original, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())
            with self.subTest(key=key), self.assertRaises(AdmissionUnavailable):
                self.client.renew(request, cached)
        for invalid in (None, {}, "receipt"):
            self.result = {**baseline, "renewalReceipt": invalid}
            with self.subTest(invalid=invalid), self.assertRaises(AdmissionUnavailable):
                self.client.renew(request, cached)
        self.result = copy.deepcopy(baseline)
        self.result["admissionExpiresAt"] = (self.now + timedelta(hours=2)).isoformat()
        with self.assertRaises(AdmissionUnavailable):
            self.client.renew(request, cached)

    def test_renewal_never_uses_cache_when_endpoint_refuses_or_trust_changes(self):
        request, cached = self.renewal()
        self.status = 403
        with self.assertRaises(AdmissionUnavailable):
            self.client.renew(request, cached)
        self.status = 302
        with self.assertRaises(AdmissionUnavailable):
            self.client.renew(request, cached)
        self.assertEqual(len(self.calls), 2)
        self.status = 200
        self.mutate = lambda: self.config_path.write_text(self.config_path.read_text() + "\n")
        with self.assertRaisesRegex(AdmissionUnavailable, "configuration pin mismatch"):
            self.client.renew(request, cached)

    def test_cli_renewal_and_exclusive_check_mode(self):
        request, cached = self.renewal()
        payload = self.root / "request.json"
        payload.write_text(json.dumps(request))
        receipt = self.root / "receipt.json"
        receipt.write_text(json.dumps(cached))
        args = ["--config", str(self.config_path), "--config-sha256", self.pin,
                "--primary", str(self.primary), "--request", str(payload), "--renew-receipt", str(receipt)]
        with patch("builtins.print") as printed:
            self.assertEqual(main(args), 0)
        self.assertEqual(json.loads(printed.call_args.args[0]), self.result)
        with self.assertRaises(SystemExit) as rejected, patch("sys.stderr"):
            main([*args, "--check-receipt", str(receipt)])
        self.assertEqual(rejected.exception.code, 2)

    def test_policy_expiry_without_timezone_is_refused(self):
        self.result["admissionExpiresAt"] = "2026-10-02T18:00:00"
        with self.assertRaisesRegex(AdmissionUnavailable, "expired or invalid"):
            self.client.acquire(self.request)

    def test_configuration_changed_during_response_is_refused(self):
        self.mutate = lambda: self.config_path.write_text(self.config_path.read_text() + "\n")
        with self.assertRaisesRegex(AdmissionUnavailable, "configuration pin mismatch"):
            self.client.acquire(self.request)

    def test_unverified_certificate_is_refused(self):
        client = self.client
        config, bearer, _ = client._config()
        with patch.object(client, "_config", return_value=(config, bearer, ssl.create_default_context())):
            with self.assertRaisesRegex(AdmissionUnavailable, "refused or unavailable"):
                client.acquire(self.request)
        self.assertFalse(self.calls)

    def test_cli_reports_bounded_unavailable_without_secret(self):
        payload = self.root / "request.json"
        payload.write_text(json.dumps(self.request))
        self.status = 403
        with patch("builtins.print") as printed:
            status = main(["--config", str(self.config_path), "--config-sha256", self.pin,
                           "--primary", str(self.primary), "--request", str(payload)])
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(printed.call_args.args[0]),
                         {"authorizationGranted": False, "code": "admission_unavailable"})
        self.assertNotIn(self.bearer, str(printed.call_args))


if __name__ == "__main__":
    unittest.main()
