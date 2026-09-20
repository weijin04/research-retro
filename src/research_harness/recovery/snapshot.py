"""Freeze a source census and bounded Git DAG without checkout or project execution."""
import json
import os
from pathlib import Path
import subprocess

from research_harness.common import HarnessError, digest, stable_id, upsert


def git_capture(unit, limit=128):
    root = Path(unit.manifest["sources"][0]["root"])
    metadata = root / ".git"
    if not metadata.exists():
        return {"commits": [], "refs": {}, "gaps": ["No local Git object database"], "complete": False}
    if metadata.is_symlink() or not metadata.is_dir() or (metadata / "objects/info/alternates").exists():
        return {"commits": [], "refs": {}, "gaps": ["External Git directories/alternates require a separately frozen source"], "complete": False}
    # Reject symlinks anywhere Git may open, including objects/config/refs.
    if any(p.is_symlink() for p in metadata.rglob("*")):
        return {"commits": [], "refs": {}, "gaps": ["Git metadata contains symlinks"], "complete": False}
    env = {"PATH": os.defpath, "HOME": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
    def git(*args):
        result = subprocess.run(["git", "--no-replace-objects", "-c", "core.hooksPath=/dev/null",
                                 "-c", "core.fsmonitor=false", "-c", "core.pager=cat", "-C", str(root), *args],
                                env=env, capture_output=True, timeout=30)
        if result.returncode:
            raise HarnessError("git_unavailable", result.stderr.decode(errors="replace")[:500])
        return result.stdout
    commits, gaps, refs = [], [], {}
    try:
        refs = dict(line.split(" ", 1) for line in git("for-each-ref", "--format=%(refname) %(objectname)").decode().splitlines())
        rows = git("rev-list", "--all", "--parents", "--max-count=" + str(limit + 1)).decode().splitlines()
        if len(rows) > limit:
            gaps.append("Git commit limit reached; unvisited branches/ancestors remain")
        for row in rows[:limit]:
            oid, *parents = row.split()
            files = {}
            entries = git("ls-tree", "-r", "-z", oid).split(b"\0")
            for entry in entries[:10000]:
                if not entry:
                    continue
                info, name = entry.split(b"\t", 1)
                mode, kind, blob = info.decode().split()
                path = name.decode("utf-8", errors="replace")
                if kind != "blob" or mode not in {"100644", "100755"}:
                    gaps.append(f"Unsupported Git member {oid}:{path}")
                    continue
                if any(p in unit.manifest["sources"][0]["excludes"] for p in Path(path).parts):
                    continue
                size = int(git("cat-file", "-s", blob))
                if size > unit.manifest["sources"][0]["snapshot_max_bytes"]:
                    gaps.append(f"Uncaptured Git blob {oid}:{path} ({size} bytes)")
                    continue
                content = git("cat-file", "blob", blob)
                sha = unit.store.put_blob(content)
                identifier = stable_id("git-blob", [path, sha])
                upsert(unit.store, [{"id": identifier, "kind": "source_blob", "data": {
                    "path": path, "sha256": sha, "blob_refs": [sha], "size": len(content),
                    "byte_range": [0, len(content)], "identity_scope": "whole_file", "origin_assurance": "bytes_only"}}], "capture Git blob without executing it")
                files[path] = {"id": identifier, "revision": 1, "sha256": sha, "git_oid": blob}
            if len(entries) > 10000:
                gaps.append(f"Git tree entry limit reached: {oid}")
            commits.append({"id": oid, "parents": parents, "files": files})
    except (HarnessError, OSError, subprocess.SubprocessError) as error:
        gaps.append(str(error))
    return {"commits": commits, "refs": refs, "gaps": gaps, "complete": not gaps,
            "qualification": "captured content/version DAG; Git ancestry does not establish execution"}


def freeze(unit):
    scan = unit.scan()
    files, gaps = {}, []
    root = Path(unit.manifest["sources"][0]["root"])
    for source in scan["sources"]:
        for row in source["assets"]:
            path = str(Path(row["path"]).relative_to(root))
            if row["state"] == "captured":
                files[path] = {"id": row["artifact_id"], "revision": row["artifact_revision"], "sha256": row["sha256"]}
            elif row["state"] != "not_in_scope":
                gaps.append({"path": path, "state": row["state"], "reason": row.get("reason")})
    data = {"files": files, "gaps": gaps, "coverage": scan["sources"], "git": git_capture(unit),
            "consistency": "per-file pinned capture; no claim of whole-tree atomicity", "rule_version": "snapshot-1",
            "policy_revision": unit.store.active_policy_revision()}
    identifier = stable_id("snapshot", data)
    upsert(unit.store, [{"id": identifier, "kind": "source_snapshot", "data": data}], "freeze read-only source census and Git history")
    return unit.store.get(identifier)


def materialize(store, refs):
    return {path: {**ref, "content": store.read_blob(ref["sha256"])} for path, ref in refs.items()}
