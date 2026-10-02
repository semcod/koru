"""Consume an operator-pinned HTTPS admission; never mint editing authority.

Execution adapters must call check immediately before their effects, enforce
the accepted intent's path scope, and retain separate publication controls.
The module CLI exposes acquire/check for supervised consumers such as Willman.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import stat
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BINDINGS = {
    "repositoryRef", "ticketId", "branchRef", "worktreeId", "ownerSession",
    "planHash", "scopeHash", "baseSha",
}
MAX_BYTES = 65_536
DIGEST = re.compile(r"[a-f0-9]{64}")


class AdmissionUnavailable(RuntimeError):
    """A bounded failure without credentials, remote body or private paths."""


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise AdmissionUnavailable("duplicate admission document field")
        value[key] = item
    return value


def _document(raw: bytes) -> dict:
    if len(raw) > MAX_BYTES:
        raise AdmissionUnavailable("admission document exceeds limit")
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
    except (ValueError, UnicodeError) as exc:
        raise AdmissionUnavailable("invalid admission document") from exc
    if not isinstance(value, dict):
        raise AdmissionUnavailable("invalid admission document")
    return value


def _external(value: str, primary: Path) -> Path:
    path = Path(value)
    if (not path.is_absolute() or str(path) != value or ".." in path.parts
            or path.is_relative_to(primary) or any(p.is_symlink() for p in (path, *path.parents))):
        raise AdmissionUnavailable("admission trust material must be external and canonical")
    return path


def _expires(value, now):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None and parsed.astimezone(UTC) > now:
            return
    except (TypeError, ValueError):
        pass
    raise AdmissionUnavailable("admission expired or invalid")


class AdmissionClient:
    """Pinned transport and exact authenticated response binding."""

    def __init__(self, config: Path, sha256: str, primary: Path, *, clock=None):
        self.primary = Path(primary)
        if not self.primary.is_absolute() or any(p.is_symlink() for p in (self.primary, *self.primary.parents)):
            raise AdmissionUnavailable("invalid admission target")
        self.config_path = _external(str(config), self.primary)
        self.sha256 = sha256
        self.clock = clock or (lambda: datetime.now(UTC))
        self._config()

    def _config(self):
        path = _external(str(self.config_path), self.primary)
        raw = path.read_bytes()
        if not DIGEST.fullmatch(self.sha256) or hashlib.sha256(raw).hexdigest() != self.sha256:
            raise AdmissionUnavailable("admission configuration pin mismatch")
        config = _document(raw)
        if (set(config) != {"schema", "endpoint", "ca_file", "ca_sha256", "credential_file",
                           "policy_sha256", "authority_ref", "owner_actor"}
                or config["schema"] != "koru.repository-admission-client/v1"
                or any(not isinstance(v, str) or not v or v != v.strip() for v in config.values())):
            raise AdmissionUnavailable("invalid admission configuration")
        endpoint = urllib.parse.urlsplit(config["endpoint"])
        if (endpoint.scheme != "https" or not endpoint.hostname or endpoint.username or endpoint.password
                or endpoint.path or endpoint.query or endpoint.fragment):
            raise AdmissionUnavailable("verified HTTPS admission endpoint required")
        if (not DIGEST.fullmatch(config["policy_sha256"])
                or not re.fullmatch(r"(?:policy|receipt):\S+", config["authority_ref"])
                or not re.fullmatch(r"agent:\S+", config["owner_actor"])):
            raise AdmissionUnavailable("invalid admission authority binding")
        ca = _external(config["ca_file"], self.primary)
        if hashlib.sha256(ca.read_bytes()).hexdigest() != config["ca_sha256"]:
            raise AdmissionUnavailable("admission certificate pin mismatch")
        credential = _external(config["credential_file"], self.primary)
        info = credential.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid()
                or info.st_size > 4096):
            raise AdmissionUnavailable("private admission credential required")
        bearer = credential.read_text().strip()
        if len(bearer) < 32 or re.search(r"\s", bearer):
            raise AdmissionUnavailable("invalid admission credential")
        context = ssl.create_default_context(cafile=str(ca))
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        return config, bearer, context

    def _call(self, request: dict, *, check: bool) -> dict:
        extras = {"leaseId", "leaseRevision", "fencingToken"} if check else set()
        if (not isinstance(request, dict) or set(request) != BINDINGS | {"schema", "requestId"} | extras
                or request.get("schema") != "subactor.repository-admission-request/v1"):
            raise AdmissionUnavailable("invalid admission request")
        self._target(request)
        config, bearer, context = self._config()
        raw = json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
        if len(raw) > MAX_BYTES:
            raise AdmissionUnavailable("admission request exceeds limit")
        query = urllib.request.Request(
            config["endpoint"] + "/v1/repository-admissions/" + ("check" if check else "acquire"),
            data=raw, headers={"Content-Type": "application/json", "Authorization": "Bearer " + bearer},
        )
        # Disable environment proxies and redirects: credentials stay at this
        # exact protected origin. A certificate is verified, never bypassed.
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context), _NoRedirect(),
        )
        try:
            with opener.open(query, timeout=5) as response:
                if response.status != 200 or response.headers.get_content_type() != "application/json":
                    raise AdmissionUnavailable("admission refused or unavailable")
                result = _document(response.read(MAX_BYTES + 1))
        except (OSError, urllib.error.URLError, ValueError) as exc:
            raise AdmissionUnavailable("admission refused or unavailable") from exc
        self._validate(result, request, config, check=check)
        # Detect trust material changes during the HTTP exchange.
        self._config()
        self._target(request)
        return result

    def _target(self, request):
        """Bind the trusted configuration's placement to the real target Git."""
        def git(*args):
            try:
                result = subprocess.run(
                    ["git", "--no-optional-locks", *args], cwd=self.primary,
                    env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
                    capture_output=True, text=True, timeout=5, check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise AdmissionUnavailable("admission target binding unavailable") from exc
            if result.returncode:
                raise AdmissionUnavailable("admission target binding unavailable")
            return result.stdout.strip()

        repository = request.get("repositoryRef")
        if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise AdmissionUnavailable("invalid admission repository")
        if (git("worktree", "list", "--porcelain").splitlines()[0] != "worktree " + str(self.primary)
                or git("symbolic-ref", "HEAD") != "refs/heads/main"
                or git("rev-parse", "HEAD") != request.get("baseSha")
                or git("remote", "get-url", "origin") not in {
                    f"git@github.com:{repository}.git", f"https://github.com/{repository}.git"}):
            raise AdmissionUnavailable("admission target binding mismatch")

    def _validate(self, result, request, config, *, check):
        expected = {key: request[key] for key in BINDINGS}
        lease = result.get("lease")
        if (result.get("schema") != "subactor.repository-admission/v1"
                or result.get("authorizationGranted") is not True
                or result.get("requestId") != request["requestId"]
                or result.get("capabilities") != ["workspace_write"]
                or result.get("policySha256") != config["policy_sha256"]
                or result.get("authorityRef") != config["authority_ref"]
                or result.get("bindings") != expected or not isinstance(lease, dict)):
            raise AdmissionUnavailable("admission response binding mismatch")
        if (lease.get("schema") != "wellmanifest.change-lease/v1" or lease.get("phase") != "editing"
                or lease.get("ownerActor") != config["owner_actor"] or lease.get("targetBranch") != "main"
                or any(lease.get(k) != expected[k] for k in BINDINGS - {"baseSha"})
                or not isinstance(lease.get("leaseId"), str) or not lease["leaseId"]
                or any(type(lease.get(k)) is not int or lease[k] < 1 for k in ("leaseRevision", "fencingToken"))):
            raise AdmissionUnavailable("authoritative editing lease required")
        if check and any(lease[k] != request[k] for k in ("leaseId", "leaseRevision", "fencingToken")):
            raise AdmissionUnavailable("stale admission fencing")
        _expires(result.get("admissionExpiresAt"), self.clock())
        _expires(lease.get("expiresAt"), self.clock())

    def acquire(self, request: dict) -> dict:
        return self._call(request, check=False)

    def check(self, request: dict, receipt: dict) -> dict:
        # Validate a cached receipt before using it as a check cursor. Cached
        # data never authorizes an effect: the authenticated server must reply.
        config, _, _ = self._config()
        self._validate(receipt, request, config, check=False)
        cursor = {**request, **{k: receipt["lease"][k] for k in ("leaseId", "leaseRevision", "fencingToken")}}
        return self._call(cursor, check=True)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--check-receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        client = AdmissionClient(args.config, args.config_sha256, args.primary)
        request = _document(args.request.read_bytes())
        result = (client.check(request, _document(args.check_receipt.read_bytes()))
                  if args.check_receipt else client.acquire(request))
    except (AdmissionUnavailable, OSError, ValueError):
        print(json.dumps({"authorizationGranted": False, "code": "admission_unavailable"}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
