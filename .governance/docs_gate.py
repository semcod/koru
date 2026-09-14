#!/usr/bin/env python3
"""Koru docs adapter. Repository source is not a protected CI trust root."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REVISION = "71c296aab28bceec709722f59078ca86ac48dca7"
ARTIFACTS = {
    "check.py": "7bdc2f5909a56ab071aefaca11e6df18ccfae9b48ffc6415c397d555d2482b45",
    "change_contract.py": "3269780542a03063fae860624e18c5f15d2d679ffbe56299acf333eabc30505e",
    "policy.json": "af5fde2d52e1c292e569cd47a4068f0e42181a8f8fb9fc21737a569bee9a206f",
    "policy-dsl.lock.json": "bbb10db0732294fb77bcf6667727071e6ebaf0dd31c4651c2ea0c1936175d209",
}


def verified_sources(root):
    """Read once and execute only these verified bytes, never adjacent pyc."""
    root = Path(root).absolute()
    payload = {}
    for name, digest in ARTIFACTS.items():
        path = root / "docs/standard" / name
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError("DOCS_RUNTIME_SYMLINK")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("DOCS_RUNTIME_DIGEST")
        payload[name] = raw
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "final"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--standard-root", type=Path, required=True)
    parser.add_argument("--policy-dsl-root", type=Path)
    parser.add_argument("--base", help="Exact trusted consumer base; mandatory for final")
    parser.add_argument("--deliverable", action="append", default=[])
    parser.add_argument("--kind")
    parser.add_argument("--id")
    args = parser.parse_args(argv)
    if args.phase == "prepare":
        if args.base or not args.kind or not args.id or len(args.deliverable) != 1:
            parser.error("prepare requires kind, id and one deliverable, without base")
    elif not args.base or not re.fullmatch(r"[0-9a-f]{40}", args.base) or args.kind or args.id:
        parser.error("final requires a full trusted base SHA and no kind/id")
    try:
        sources = verified_sources(args.standard_root)
    except (OSError, ValueError) as error:
        code = str(error) if isinstance(error, ValueError) else "DOCS_RUNTIME_UNAVAILABLE"
        print(json.dumps({"ok": False, "findings": [{"code": code}], "authority": "none"}))
        return 1
    # Temporary execution projection is not a vendored dependency or deliverable.
    # It is populated only from verified bytes; no source-side cache is imported.
    with tempfile.TemporaryDirectory(prefix="koru-docs-check-") as directory:
        runtime = Path(directory)
        for name, raw in sources.items():
            (runtime / name).write_bytes(raw)
        command = [sys.executable, "-I", "-B", str(runtime / "check.py"),
                   "--root", str(args.root.resolve()), "--standard-revision", REVISION]
        if args.policy_dsl_root:
            command += ["--policy-dsl-root", str(args.policy_dsl_root.absolute())]
        if args.phase == "prepare":
            command += ["--prepare", "--format", "v2", "--scope", "repository",
                        "--kind", args.kind, "--id", args.id]
        else:
            command += ["--base", args.base]
        for name in args.deliverable:
            command += ["--deliverable", name]
        return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
