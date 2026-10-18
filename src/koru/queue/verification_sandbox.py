"""Run patch verification with read-only host mounts and private scratch.

Verification consumes candidate code, so its shell and all children are
untrusted. This boundary grants no source, Git, controller or publication
writes. Network syscalls are denied as well as isolated: a read-only mount
alone does not prevent connecting to an existing host Unix socket.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import errno
import os
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path


class SandboxUnavailable(ValueError):
    """The verification command must not run without its boundary."""


class _ScmpArgCmp(ctypes.Structure):
    _fields_ = [
        ("arg", ctypes.c_uint),
        ("op", ctypes.c_int),
        ("datum_a", ctypes.c_uint64),
        ("datum_b", ctypes.c_uint64),
    ]


_SCMP_CMP_EQ = 4
_PYTEST_CMD_RE = re.compile(r"(?:^|[\s/\"'])pytest(?:\s|\"|'|$)")


def _should_allow_loopback(command: str) -> bool:
    override = (os.environ.get("KORU_VERIFY_ALLOW_LOOPBACK") or "").strip().lower()
    if override in {"0", "false", "no", "off"}:
        return False
    if override in {"1", "true", "yes", "on"}:
        return True
    return bool(_PYTEST_CMD_RE.search(command or ""))


def _safe_path(path: Path) -> Path:
    if ".." in Path(path).parts:
        raise SandboxUnavailable("noncanonical verification path")
    path = Path(os.path.abspath(path))
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise SandboxUnavailable("symlinked verification path")
    return path


def _export_filter(path: Path, *, allow_loopback: bool = False) -> None:
    """Export a native-architecture seccomp program, never load it in the parent."""
    name = ctypes.util.find_library("seccomp")
    if not name:
        raise SandboxUnavailable("libseccomp is required")
    library = ctypes.CDLL(name)
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    library.seccomp_rule_add.restype = ctypes.c_int
    library.seccomp_rule_add_array.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.POINTER(_ScmpArgCmp),
    ]
    library.seccomp_rule_add_array.restype = ctypes.c_int
    library.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
    library.seccomp_export_bpf.restype = ctypes.c_int
    context = library.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW; other ABIs fail closed.
    if not context:
        raise SandboxUnavailable("seccomp initialization failed")
    try:
        denied = (
            ("socketcall",)
            if allow_loopback
            else ("socket", "socketcall", "connect", "sendto", "sendmsg")
        ) + (
            "mount", "umount2", "pivot_root", "setns", "unshare",
            "fsopen", "fsconfig", "fsmount", "move_mount", "open_tree", "mount_setattr",
            "ptrace", "process_vm_writev", "bpf", "keyctl", "add_key", "request_key",
            "io_uring_setup", "io_uring_enter", "io_uring_register",
        )
        if allow_loopback:
            socket_nr = library.seccomp_syscall_resolve_name(b"socket")
            if socket_nr == -1:
                raise SandboxUnavailable("required seccomp syscall is unknown")
            unix_cmp = _ScmpArgCmp(0, _SCMP_CMP_EQ, socket.AF_UNIX, 0)
            if library.seccomp_rule_add_array(
                context, 0x00050000 | errno.EPERM, socket_nr, 1, ctypes.byref(unix_cmp)
            ):
                raise SandboxUnavailable("seccomp rule installation failed")
        for syscall_name in denied:
            number = library.seccomp_syscall_resolve_name(syscall_name.encode("ascii"))
            if number == -1:
                if syscall_name in {"socket", "connect", "io_uring_setup"}:
                    raise SandboxUnavailable("required seccomp syscall is unknown")
                continue
            if library.seccomp_rule_add(context, 0x00050000 | errno.EPERM, number, 0):
                raise SandboxUnavailable("seccomp rule installation failed")
        with path.open("xb") as output:
            if library.seccomp_export_bpf(context, output.fileno()):
                raise SandboxUnavailable("seccomp export failed")
        if not path.stat().st_size:
            raise SandboxUnavailable("empty seccomp program")
    finally:
        library.seccomp_release(context)


def _command(command: str, project: Path, scratch: Path, binary: str) -> str:
    filter_path = scratch / "filter.bpf"
    _export_filter(filter_path, allow_loopback=_should_allow_loopback(command))
    for folder in ("tmp", "home", "cache", "config", "empty"):
        (scratch / folder).mkdir(mode=0o700)
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "LANG": "C.UTF-8",
        "HOME": str(scratch / "home"),
        "TMPDIR": str(scratch / "tmp"),
        "XDG_CACHE_HOME": str(scratch / "cache"),
        "XDG_CONFIG_HOME": str(scratch / "config"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_ADDOPTS": "-o cache_dir=" + str(scratch / "cache"),
    }
    if os.environ.get("PYTHONPATH"):
        environment["PYTHONPATH"] = os.environ["PYTHONPATH"]
    argv = ["env", "-i", *(key + "=" + value for key, value in environment.items()),
            binary, "--ro-bind", "/", "/", "--bind", str(scratch), str(scratch),
            "--unshare-all", "--unshare-user", "--disable-userns", "--assert-userns-disabled",
            "--die-with-parent", "--new-session", "--cap-drop", "ALL",
            "--proc", "/proc", "--dev", "/dev",
            "--ro-bind", str(scratch / "empty"), "/dev/shm", "--seccomp", "9",
            "--chdir", str(project), "--", "/bin/sh", "-c", command]
    # The existing runner accepts a shell string. Open the filter in that
    # shell so subprocess close_fds cannot discard its descriptor before bwrap.
    return "exec 9<" + shlex.quote(str(filter_path)) + " && exec " + shlex.join(argv)


def run_verification(command: str, project: Path, runner: Callable):
    """Keep the existing runner contract while making isolation mandatory."""
    scratch = None
    try:
        if sys.platform != "linux" or not (binary := shutil.which("bwrap")):
            raise SandboxUnavailable("Linux bubblewrap is required")
        root = _safe_path(project)
        backend = Path(binary).resolve(strict=True)
        info = backend.stat()
        if (not root.is_dir() or backend.is_relative_to(root)
                or not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022):
            raise SandboxUnavailable("invalid verification root or backend")
        binary = str(backend)
        cache = _safe_path(root / ".subactor/cache/koru-verification")
        cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        _safe_path(cache)
        scratch = tempfile.TemporaryDirectory(prefix="run-", dir=cache)
        isolated = _command(command, root, Path(scratch.name), binary)
    except (SandboxUnavailable, OSError, AttributeError):
        if scratch is not None:
            scratch.cleanup()
        return subprocess.CompletedProcess(
            ["verification-sandbox"], 125, "",
            "verification_sandbox_unavailable: verified Linux bubblewrap/seccomp execution is required",
        )
    with scratch:
        return runner(isolated, root)
