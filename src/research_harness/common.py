from __future__ import annotations
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class HarnessError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code, self.details = code, details or {}


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value).encode()).hexdigest()


def stable_id(kind, value):
    return f"{kind}:{digest(value)[:24]}"


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def upsert(store, records, reason, key=None):
    changed, read_set = [], {}
    for r in records:
        try:
            old = store.get(r["id"])
        except KeyError:
            old = None
        if old and old["data"] == r["data"] and old["kind"] == r["kind"]:
            continue
        if old:
            read_set[r["id"]] = old["revision"]
        changed.append(r)
    if not changed:
        return {"status": "unchanged", "changed_ids": []}
    new_ids = {r["id"] for r in changed}
    for record in changed:
        for support in record["data"].get("support_sets", []):
            for premise in support:
                if premise not in new_ids and premise not in read_set:
                    read_set[premise] = store.get(premise)["revision"]
    return store.commit(changed, reason=reason, read_set=read_set,
                        idempotency_key=key or digest({"records": changed, "reads": read_set}),
                        policy_revision=store.active_policy_revision() if hasattr(store, "active_policy_revision") else 1)
