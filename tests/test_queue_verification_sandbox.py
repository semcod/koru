"""Actual verification processes must not mutate their host or contact services."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

from koru.queue.verification_sandbox import run_verification


def shell(command, project):
    return subprocess.run(command, shell=True, cwd=project, capture_output=True, text=True)


def test_missing_backend_never_executes_command(tmp_path, monkeypatch):
    monkeypatch.setattr("koru.queue.verification_sandbox.shutil.which", lambda _: None)
    calls = []
    result = run_verification("touch escaped", tmp_path, lambda *args: calls.append(args))
    assert result.returncode != 0
    assert "verification_sandbox_unavailable" in result.stderr
    assert calls == []


def test_unsupported_platform_never_executes_command(tmp_path, monkeypatch):
    monkeypatch.setattr("koru.queue.verification_sandbox.sys.platform", "unsupported")
    calls = []
    result = run_verification("touch escaped", tmp_path, lambda *args: calls.append(args))
    assert result.returncode != 0
    assert calls == []


def test_symlinked_checkout_is_refused(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    calls = []
    result = run_verification("true", alias, lambda *args: calls.append(args))
    assert result.returncode != 0
    assert calls == []


def test_missing_seccomp_never_executes_command(tmp_path, monkeypatch):
    monkeypatch.setattr("koru.queue.verification_sandbox.ctypes.util.find_library", lambda _: None)
    calls = []
    result = run_verification("touch escaped", tmp_path, lambda *args: calls.append(args))
    assert result.returncode != 0
    assert calls == []


def test_symlinked_scratch_is_refused(tmp_path):
    target = tmp_path / "outside"
    target.mkdir()
    (tmp_path / ".subactor").symlink_to(target, target_is_directory=True)
    calls = []
    result = run_verification("true", tmp_path, lambda *args: calls.append(args))
    assert result.returncode != 0
    assert calls == []
    assert list(target.iterdir()) == []


def test_kernel_denies_writes_and_host_sockets_in_children():
    assert sys.platform == "linux" and shutil.which("bwrap"), "Kernel evidence requires Linux bubblewrap"
    cache = Path.cwd() / ".subactor/cache/ticket-449/kernel-tests"
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        fixture = Path(temporary)
        project = fixture / "project"
        project.mkdir()
        protected = project / "out-of-scope.txt"
        sibling = fixture / "other-repository.txt"
        protected.write_text("sentinel")
        sibling.write_text("sentinel")
        alias = project / "escape-link"
        alias.symlink_to(sibling)
        temporary_target = Path("/tmp") / (fixture.name + "-must-not-exist")
        assert not temporary_target.exists()
        targets = [str(protected), "../other-repository.txt", str(alias), str(temporary_target),
                   "/dev/shm/koru-must-not-exist"]
        script = '''
import json, os, pathlib, socket, subprocess, sys
targets = json.loads(sys.argv[1])
for target in targets:
    try:
        pathlib.Path(target).write_text('escaped')
    except OSError:
        pass
    else:
        raise AssertionError('write was admitted: ' + target)
for family in (socket.AF_UNIX, socket.AF_INET):
    try:
        socket.socket(family)
    except OSError:
        pass
    else:
        raise AssertionError('socket was admitted')
child = subprocess.run([sys.executable, '-c',
    "from pathlib import Path; Path(__import__('sys').argv[1]).write_text('child')", targets[0]])
assert child.returncode != 0
assert 'KORU_VERIFICATION_TEST_CREDENTIAL' not in os.environ
scratch = pathlib.Path(os.environ['TMPDIR'])
(scratch / 'fixture.txt').write_text('allowed')
assert scratch.is_relative_to(pathlib.Path.cwd())
try:
    os.link(targets[0], scratch / 'host-hardlink')
except OSError:
    pass
else:
    raise AssertionError('host hardlink was admitted')
print('kernel-boundary-passed')
'''
        old = os.environ.get("KORU_VERIFICATION_TEST_CREDENTIAL")
        os.environ["KORU_VERIFICATION_TEST_CREDENTIAL"] = "private-test-value"
        try:
            command = shlex.join([sys.executable, "-c", script, json.dumps(targets)])
            result = run_verification(command, project, shell)
        finally:
            if old is None:
                os.environ.pop("KORU_VERIFICATION_TEST_CREDENTIAL", None)
            else:
                os.environ["KORU_VERIFICATION_TEST_CREDENTIAL"] = old
        assert result.returncode == 0, result.stderr
        assert "kernel-boundary-passed" in result.stdout
        assert protected.read_text() == sibling.read_text() == "sentinel"
        assert not temporary_target.exists()


def test_real_transaction_applies_patch_but_verifier_cannot_write(monkeypatch):
    from koru.queue.transaction import execute_patch_transaction

    assert sys.platform == "linux" and shutil.which("bwrap"), "Kernel evidence requires Linux bubblewrap"
    cache = Path.cwd() / ".subactor/cache/ticket-449/transaction-tests"
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        project = Path(temporary)
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        (project / "a.txt").write_text("old\n")
        (project / "sentinel.txt").write_text("sentinel")
        subprocess.run(["git", "add", "."], cwd=project, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "-qm", "fixture"], cwd=project, check=True)
        probe = "from pathlib import Path; print('VERIFIER-STARTED', flush=True); Path('sentinel.txt').write_text('escaped')"
        command = shlex.join([sys.executable, "-c", probe])
        ticket = {"id": "sandbox-probe", "inputs": {
            "verify_command": command, "promotion_mode": "apply"}}
        reply = subprocess.CompletedProcess([], 0,
            "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n", "")
        monkeypatch.setenv("KORU_QUEUE_WORKTREE", "0")
        result = execute_patch_transaction(project, reply, ticket, shell)
        assert result.outcome is not None
        assert "rolled back" in result.outcome.message
        assert "VERIFIER-STARTED" in result.outcome.message
        assert (project / "a.txt").read_text() == "old\n"
        assert (project / "sentinel.txt").read_text() == "sentinel"


def test_pytest_verification_allows_loopback_http_while_blocking_unix_sockets():
    assert sys.platform == "linux" and shutil.which("bwrap"), "Kernel evidence requires Linux bubblewrap"
    cache = Path.cwd() / ".subactor/cache/ticket-451/loopback-tests"
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        project = Path(temporary)
        test_file = project / "test_local_http.py"
        test_file.write_text(
            "import http.server, socket, threading, urllib.request\n"
            "def test_loopback_http_and_unix_denied():\n"
            "    try:\n"
            "        socket.socket(socket.AF_UNIX)\n"
            "    except OSError:\n"
            "        pass\n"
            "    else:\n"
            "        raise AssertionError('AF_UNIX must remain blocked')\n"
            "    class Handler(http.server.BaseHTTPRequestHandler):\n"
            "        def do_GET(self):\n"
            "            self.send_response(200)\n"
            "            self.end_headers()\n"
            "            self.wfile.write(b'loopback-ok')\n"
            "        def log_message(self, *args):\n"
            "            pass\n"
            "    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)\n"
            "    t = threading.Thread(target=srv.serve_forever, daemon=True)\n"
            "    t.start()\n"
            "    try:\n"
            "        data = urllib.request.urlopen(f'http://127.0.0.1:{srv.server_port}/').read()\n"
            "        assert data == b'loopback-ok'\n"
            "    finally:\n"
            "        srv.shutdown()\n"
            "        srv.server_close()\n",
            encoding="utf-8",
        )
        command = f"{shlex.quote(sys.executable)} -m pytest -q test_local_http.py"
        result = run_verification(command, project, shell)
        assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_multi_file_context_includes_all_files_and_retry_lists_untouched_targets(tmp_path):
    from types import SimpleNamespace
    from koru.queue.context import build_project_context
    from koru.queue.patch_retry import _build_retry_action, _pin_base, verify_retry_budget
    from koru.queue.patch_mode import PatchOutcome, VERIFY_BASELINE_FAILED

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    files = []
    for idx in range(11):
        name = f"test_mod_{idx:02d}.py"
        (tmp_path / name).write_text(f"# file {idx}\n" + ("x = 1\n" * 900), encoding="utf-8")
        files.append(name)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=t@example.invalid", "commit", "-qm", "init"],
        cwd=tmp_path,
        check=True,
    )

    ctx = build_project_context(tmp_path, {"prompt": "update all 11 test files", "context_files": files})
    assert ctx is not None
    assert ctx.included_files == files

    ticket = {"id": "PLF-255-tests", "files": files[:3], "inputs": {}}
    assert verify_retry_budget(ticket) == 1

    partial_diff = (
        "diff --git a/test_mod_00.py b/test_mod_00.py\n"
        "--- a/test_mod_00.py\n"
        "+++ b/test_mod_00.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-# file 0\n"
        "+# file 0 updated\n"
        " x = 1\n"
    )
    reply = SimpleNamespace(returncode=0, stdout=partial_diff, stderr="")
    manifest = _pin_base(tmp_path, ticket, reply, budget=2, run_id="r451")
    assert tuple(manifest["touched_files"]) == tuple(files[:3])

    outcome = PatchOutcome(
        code=VERIFY_BASELINE_FAILED,
        message="verification failed on remaining untouched files",
        workspace_left_untouched=True,
    )
    retry_act = _build_retry_action(
        {"prompt": "update all files"},
        "update all files",
        tmp_path,
        manifest,
        outcome,
        None,
        previous_diff=partial_diff,
    )
    assert "Incomplete multi-file patch detected" in retry_act["prompt"]
    assert "`test_mod_01.py`" in retry_act["prompt"]
    assert "`test_mod_02.py`" in retry_act["prompt"]

