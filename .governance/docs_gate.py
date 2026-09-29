#!/usr/bin/env python3
"""Koru docs adapter. Repository source is not a protected CI trust root."""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REVISION = "9fb5fc4d99afb70ca577b84b0bf115e52e43a1c6"
ARTIFACTS = {
    "check.py": "69217f1fa83bff0d2796ec22d662986dc178e2c8a6fa72fa169669f827a4a4f5",
    "change_contract.py": "3269780542a03063fae860624e18c5f15d2d679ffbe56299acf333eabc30505e",
    "policy.json": "fac05e720ec49370ba393e817a4a03b895d7ed33828e09b3420f9fcfb09264b0",
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


def managed_copy_inventory(root):
    """Adoption-lock digests are the independent trust anchor for external
    standard copies under .governance/docs; the candidate report never is."""
    try:
        files = json.loads((Path(root) / ".governance/manifest.lock.json")
                           .read_text())["managedFiles"]
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    return {name: digest for name, digest in files.items()
            if isinstance(name, str) and isinstance(digest, str)
            and name.startswith(".governance/docs/") and name.endswith(".md")
            and re.fullmatch(r"[0-9a-f]{64}", digest)}


def checker(runtime, root, *tail):
    command = [sys.executable, "-I", "-B", str(runtime / "check.py"),
               "--root", str(root), "--standard-revision", REVISION, *tail]
    return subprocess.run(command, check=False)


def skeleton(plan, policy, title, priority, today, source_revision):
    """Minimal compact document; authors replace inert prose with content."""
    meta = {
        "schema": policy["compact"]["document_schema"],
        "id": plan["id"], "kind": plan["kind"], "version": 1,
        "title": title, "status": "draft",
        "owner": plan["repository"], "scope": plan["scope"],
        "updated": today, "source_revision": source_revision,
        "priority": priority,
        "evidence": ["repo://" + plan["repository"]],
    }
    lines = ["---", json.dumps(meta, indent=2), "---", "", f"# {title}", ""]
    for section in policy["compact"]["sections"]:
        lines += [f"<!-- docs:section {section} -->",
                  f"## {section.replace('_', ' ').title()}", "",
                  "Not applicable: generated skeleton; replace with the "
                  "documented finding before proposing the document.", ""]
    return "\n".join(lines)


def generate(runtime, root, prepared, policy, extra, args):
    """Write only after a successful plan; verify the staged result and roll
    back completely when completion validation rejects it."""
    plan = prepared["plan"]
    document = root / plan["path"]
    index = root / plan["index"]
    base = args.base or subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    index_bytes = index.read_bytes()
    document.parent.mkdir(parents=True, exist_ok=True)
    document.write_text(skeleton(plan, policy, args.title, args.priority,
                                 datetime.date.today().isoformat(), base))
    relative = Path(plan["path"]).relative_to(Path(plan["index"]).parent).as_posix()
    index.write_bytes(index_bytes + f"\n- [{args.title}]({relative})\n".encode())
    subprocess.run(["git", "-C", str(root), "add", "--", plan["path"],
                    plan["index"]], check=True)
    receipt = runtime / "prepared-plan.json"
    receipt.write_text(json.dumps(prepared))
    result = checker(runtime, root, "--complete", "--prepared-plan", str(receipt),
                     "--base", base, "--deliverable", plan["path"], *extra)
    if result.returncode:
        subprocess.run(["git", "-C", str(root), "rm", "-qf", "--cached",
                        plan["path"]], check=False)
        document.unlink(missing_ok=True)
        index.write_bytes(index_bytes)
        subprocess.run(["git", "-C", str(root), "add", "--",
                        plan["index"]], check=False)
    return result.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "final", "generate"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--standard-root", type=Path, required=True)
    parser.add_argument("--policy-dsl-root", type=Path)
    parser.add_argument("--base", help="Exact trusted consumer base; mandatory for final")
    parser.add_argument("--deliverable", action="append", default=[])
    parser.add_argument("--kind")
    parser.add_argument("--id")
    parser.add_argument("--title", help="Document title; mandatory for generate")
    parser.add_argument("--priority", default="P2")
    args = parser.parse_args(argv)
    full_sha = bool(args.base) and re.fullmatch(r"[0-9a-f]{40}", args.base)
    if args.phase == "prepare":
        if args.base or not args.kind or not args.id or len(args.deliverable) != 1:
            parser.error("prepare requires kind, id and one deliverable, without base")
    elif args.phase == "final":
        if not full_sha or args.kind or args.id or args.title:
            parser.error("final requires a full trusted base SHA and no kind/id/title")
    elif not args.kind or not args.id or not args.title \
            or len(args.deliverable) != 1 or (args.base and not full_sha):
        parser.error("generate requires kind, id, title and one deliverable; "
                     "base must be a full SHA")
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
        root = args.root.resolve()
        extra = []
        inventory = managed_copy_inventory(root)
        if inventory:
            trusted = runtime / "managed-copies.json"
            trusted.write_text(json.dumps(inventory))
            extra += ["--managed-copies", str(trusted)]
        if args.policy_dsl_root:
            extra += ["--policy-dsl-root", str(args.policy_dsl_root.absolute())]
        if args.phase == "final":
            tail = ["--base", args.base]
            for name in args.deliverable:
                tail += ["--deliverable", name]
            return checker(runtime, root, *tail, *extra).returncode
        tail = ["--prepare", "--format", "v2", "--scope", "repository",
                "--kind", args.kind, "--id", args.id,
                "--deliverable", args.deliverable[0]]
        if args.phase == "prepare":
            return checker(runtime, root, *tail, *extra).returncode
        plan_run = subprocess.run(
            [sys.executable, "-I", "-B", str(runtime / "check.py"),
             "--root", str(root), "--standard-revision", REVISION,
             *tail, *extra], check=False, capture_output=True, text=True)
        try:
            prepared = json.loads(plan_run.stdout)
        except ValueError:
            prepared = {"ok": False,
                        "findings": [{"code": "DOCS_PREPARE_OUTPUT",
                                      "message": plan_run.stderr.strip() or
                                                 "checker produced no plan"}]}
        if plan_run.returncode or not prepared.get("ok"):
            print(plan_run.stdout or json.dumps(prepared))
            return 1
        policy = json.loads(sources["policy.json"])
        return generate(runtime, root, prepared, policy, extra, args)


if __name__ == "__main__":
    raise SystemExit(main())
