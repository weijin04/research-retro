"""SQLite revisions plus durable content-addressed bytes; stdlib only."""
import hashlib
import json
import os
import re
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone


class StoreError(ValueError):
    pass


class ConflictError(StoreError):
    pass


class AuthorityError(StoreError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def blob_refs(data):
    refs = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "blob_refs":
                if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
                    raise StoreError("blob_refs must be a list of sha256 strings")
                refs.extend(value)
            else:
                refs.extend(blob_refs(value))
    elif isinstance(data, list):
        for value in data:
            refs.extend(blob_refs(value))
    return refs


class Store:
    POLICY_KINDS = {"policy", "governance", "governancedecision", "projectcontract", "authorization"}

    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.blobs = self.root / "blobs"
        self.blobs.mkdir(exist_ok=True)
        self.db_path = self.root / "state.sqlite3"
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS revisions(id TEXT,revision INTEGER,kind TEXT,data TEXT,
              transaction_id TEXT,PRIMARY KEY(id,revision));
            CREATE TABLE IF NOT EXISTS current(id TEXT PRIMARY KEY,revision INTEGER);
            CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              transaction_id TEXT,id TEXT,revision INTEGER,payload TEXT);
            CREATE TABLE IF NOT EXISTS outbox(sequence INTEGER PRIMARY KEY,payload TEXT,delivered INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS transactions(transaction_id TEXT PRIMARY KEY,
              idempotency_key TEXT UNIQUE,payload_hash TEXT,receipt TEXT);
            CREATE TABLE IF NOT EXISTS views(name TEXT PRIMARY KEY,path TEXT,revision INTEGER,stale INTEGER);
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT);
            INSERT OR IGNORE INTO metadata VALUES('policy_revision','1');
            """)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def _blob_path(self, digest):
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise StoreError("invalid sha256")
        return self.blobs / digest

    def put_blob(self, content):
        digest = hashlib.sha256(content).hexdigest()
        target = self._blob_path(digest)
        if target.exists():
            self.read_blob(digest)
            return digest
        fd, tmp = tempfile.mkstemp(dir=self.blobs, prefix=".pending-")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, target)
            dirfd = os.open(self.blobs, os.O_DIRECTORY)
            try:
                os.fsync(dirfd)
            finally:
                os.close(dirfd)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return digest

    def read_blob(self, digest):
        content = self._blob_path(digest).read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise StoreError("corrupt blob: " + digest)
        return content

    @staticmethod
    def _record(row):
        return {"id": row["id"], "kind": row["kind"], "revision": row["revision"], "data": json.loads(row["data"])}

    @staticmethod
    def _all(db):
        return {r["id"]: Store._record(r) for r in db.execute(
            "SELECT r.* FROM revisions r JOIN current c ON r.id=c.id AND r.revision=c.revision")}

    def get(self, id, revision=None):
        with self._db() as db:
            if revision is None:
                row = db.execute("SELECT r.* FROM revisions r JOIN current c ON r.id=c.id AND r.revision=c.revision WHERE r.id=?", (id,)).fetchone()
            else:
                row = db.execute("SELECT * FROM revisions WHERE id=? AND revision=?", (id, revision)).fetchone()
        if row is None:
            raise KeyError(id)
        return self._record(row)

    def list(self, kind=None):
        with self._db() as db:
            records = self._all(db).values()
        return sorted((r for r in records if kind is None or r["kind"] == kind), key=lambda r: r["id"])

    def active_policy_revision(self):
        with self._db() as db:
            return int(db.execute("SELECT value FROM metadata WHERE key='policy_revision'").fetchone()[0])

    def current_revision(self):
        with self._db() as db:
            return db.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]

    def initialize_project(self, contract, authority="human_authorized_builder"):
        """Bootstrap only; authority is an audit label, not an OS credential."""
        return self._governance(contract, None, "initialize project contract", authority)

    def governance_update(self, contract, expected_policy_revision, reason,
                          authority="human_authorized_builder"):
        return self._governance(contract, expected_policy_revision, reason, authority)

    def _governance(self, contract, expected, reason, authority):
        # This builder/CLI API is observational. F1 must protect the database
        # and this endpoint with a real process/user boundary.
        if authority not in {"human_authorized_builder", "human"}:
            raise AuthorityError("governance requires human-authorized control-plane caller")
        if not isinstance(contract, dict) or not contract or not reason:
            raise StoreError("nonempty contract and reason required")
        data = json.loads(canonical(contract))
        for ref in blob_refs(data):
            self.read_blob(ref)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            policy = int(db.execute("SELECT value FROM metadata WHERE key='policy_revision'").fetchone()[0])
            row = db.execute("SELECT revision FROM current WHERE id='project:contract'").fetchone()
            if expected is None:
                if row is not None:
                    raise ConflictError("project contract already initialized")
                revision = 1
            else:
                if row is None:
                    raise ConflictError("project contract not initialized")
                if expected != policy:
                    raise ConflictError("policy revision changed")
                revision = row[0] + 1
                policy += 1
            if "policy_revision" in data and data["policy_revision"] != policy:
                raise ConflictError("contract policy_revision must match resulting policy")
            data["policy_revision"] = policy
            txid = str(uuid.uuid4())
            key = "governance:" + txid
            db.execute("INSERT INTO revisions VALUES(?,?,?,?,?)", ("project:contract", revision, "project_contract", canonical(data), txid))
            db.execute("INSERT INTO current VALUES(?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision", ("project:contract", revision))
            db.execute("UPDATE metadata SET value=? WHERE key='policy_revision'", (str(policy),))
            event = {"id": "project:contract", "revision": revision, "reason": reason,
                     "actor": authority, "event_type": "governance", "policy_revision": policy,
                     "timestamp": datetime.now(timezone.utc).isoformat(), "boundary_mode": "observational"}
            cursor = db.execute("INSERT INTO events(transaction_id,id,revision,payload) VALUES(?,?,?,?)", (txid, "project:contract", revision, canonical(event)))
            db.execute("INSERT INTO outbox(sequence,payload) VALUES(?,?)", (cursor.lastrowid, canonical(event)))
            db.execute("UPDATE views SET stale=1")
            receipt = {"transaction_id": txid, "idempotency_key": key,
                       "revisions": {"project:contract": revision}, "changed_ids": ["project:contract"],
                       "policy_revision": policy, "state_revision": cursor.lastrowid,
                       "boundary_mode": "observational"}
            db.execute("INSERT INTO transactions VALUES(?,?,?,?)", (txid, key, hashlib.sha256(canonical(data).encode()).hexdigest(), canonical(receipt)))
        return receipt

    @staticmethod
    def _support(records):
        nonaffirmative = {"refuted", "refuted_in_scope", "invalid_test", "unsupported",
                          "unresolved", "mixed", "unchecked", "imported_assertion"}
        def can_affirm(record):
            if record["kind"].lower() != "claim":
                return True
            return not any(record["data"].get(field) in nonaffirmative
                           for field in ("evidence_status", "evidence_verdict", "verdict")
                           if isinstance(record["data"].get(field), str))

        supported = set()
        for id, record in records.items():
            data = record["data"]
            if data.get("intrinsic_valid"):
                if record["kind"].lower() not in {"evidence", "assumption"}:
                    raise StoreError("intrinsic_valid is restricted to verified evidence/assumption")
                if not data.get("revoked"):
                    supported.add(id)
            sets = data.get("support_sets", [])
            if not isinstance(sets, list) or any(not isinstance(s, list) or any(not isinstance(p, str) for p in s) for s in sets):
                raise StoreError("support_sets must be a list of lists of IDs")
        while True:
            added = {id for id, record in records.items() if id not in supported
                     and not record["data"].get("revoked")
                     and can_affirm(record)
                     and any(s and all(p in supported for p in s) for s in record["data"].get("support_sets", []))}
            if not added:
                break
            supported.update(added)
        for id, record in records.items():
            data = record["data"]
            if "support_sets" in data or "intrinsic_valid" in data or record["kind"].lower() == "claim":
                data["support_status"] = "supported" if id in supported else "unsupported"
            if record["kind"].lower() == "claim":
                data["adjudication_supported"] = bool(not data.get("revoked") and any(
                    s and all(p in supported for p in s) for s in data.get("support_sets", [])))

    def commit(self, records, reason, read_set, idempotency_key, policy_revision=1, actor="integration"):
        if not reason or not idempotency_key or not isinstance(read_set, dict):
            raise StoreError("reason, read_set and idempotency_key required")
        payload = {"records": records, "reason": reason, "read_set": read_set,
                   "policy_revision": policy_revision, "actor": actor}
        digest = hashlib.sha256(canonical(payload).encode()).hexdigest()
        # JSON roundtrip detaches caller-owned mutable values.
        records = json.loads(canonical(records))
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT * FROM transactions WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if previous:
                if previous["payload_hash"] != digest:
                    raise ConflictError("idempotency payload mismatch")
                return json.loads(previous["receipt"])
            actual_policy = int(db.execute("SELECT value FROM metadata WHERE key='policy_revision'").fetchone()[0])
            if policy_revision != actual_policy:
                raise ConflictError("policy revision changed")
            old = self._all(db)
            for id, revision in read_set.items():
                if id not in old or old[id]["revision"] != revision:
                    raise ConflictError("stale read: " + id)
            new = json.loads(canonical(old))
            seen = set()
            for record in records:
                id, kind, data = record["id"], record["kind"], record["data"]
                if not isinstance(id, str) or not id or not isinstance(kind, str) or not isinstance(data, dict):
                    raise StoreError("invalid object record")
                if id in seen:
                    raise StoreError("duplicate object in patch: " + id)
                seen.add(id)
                governance_kind = re.sub(r"[^a-z0-9]", "", kind.lower())
                old_kind = re.sub(r"[^a-z0-9]", "", old[id]["kind"].lower()) if id in old else None
                if id == "project:contract" or governance_kind in self.POLICY_KINDS or old_kind in self.POLICY_KINDS:
                    raise AuthorityError("scientific commit cannot mutate governance objects")
                if id in old and id not in read_set:
                    raise ConflictError("update requires read-set: " + id)
                if id in old and kind != old[id]["kind"]:
                    raise StoreError("object kind is immutable")
                for ref in blob_refs(data):
                    self.read_blob(ref)
                new[id] = {"id": id, "kind": kind, "data": data}
            self._support(new)
            created = seen - old.keys()
            for id in seen:
                record = new[id]
                kind = re.sub(r"[^a-z0-9]", "", record["kind"].lower())
                supports = record["data"].get("support_sets", [])
                previous_supports = old.get(id, {}).get("data", {}).get("support_sets", [])
                if kind in {"claim", "inference", "evidence", "assumption"} and supports != previous_supports:
                    for premise in {p for support in supports for p in support}:
                        if premise not in new:
                            raise StoreError("missing support premise: " + premise)
                        if premise not in read_set and premise not in created:
                            raise ConflictError("support premise requires read-set: " + premise)
            changed = [id for id, r in sorted(new.items()) if id not in old or r["data"] != old[id]["data"]]
            txid = str(uuid.uuid4())
            revisions = {}
            for id in changed:
                record = new[id]
                revision = old[id]["revision"] + 1 if id in old else 1
                revisions[id] = revision
                db.execute("INSERT INTO revisions VALUES(?,?,?,?,?)", (id, revision, record["kind"], canonical(record["data"]), txid))
                db.execute("INSERT INTO current VALUES(?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision", (id, revision))
                event = {"id": id, "revision": revision, "reason": reason, "actor": actor,
                         "propagated": id not in seen, "timestamp": datetime.now(timezone.utc).isoformat()}
                cursor = db.execute("INSERT INTO events(transaction_id,id,revision,payload) VALUES(?,?,?,?)", (txid, id, revision, canonical(event)))
                db.execute("INSERT INTO outbox(sequence,payload) VALUES(?,?)", (cursor.lastrowid, canonical(event)))
            if changed:
                db.execute("UPDATE views SET stale=1")
            state_revision = db.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]
            receipt = {"transaction_id": txid, "idempotency_key": idempotency_key, "revisions": revisions,
                       "changed_ids": changed, "policy_revision": actual_policy, "state_revision": state_revision}
            db.execute("INSERT INTO transactions VALUES(?,?,?,?)", (txid, idempotency_key, digest, canonical(receipt)))
        return receipt

    def descendants(self, id):
        records = self.list()
        found = set()
        frontier = {id}
        while frontier:
            added = {r["id"] for r in records if r["id"] not in found and r["id"] != id
                     and any(frontier.intersection(s) for s in r["data"].get("support_sets", []))}
            found.update(added)
            frontier = added
        return sorted(found)

    def history(self, id):
        with self._db() as db:
            return [self._record(r) for r in db.execute("SELECT * FROM revisions WHERE id=? ORDER BY revision", (id,))]

    def diff(self, id, before, after=None):
        a, b = self.get(id, before), self.get(id, after)
        return {"id": id, "before": a, "after": b, "changed_fields": sorted(
            k for k in set(a["data"]) | set(b["data"]) if a["data"].get(k) != b["data"].get(k))}

    def events(self, after=0):
        with self._db() as db:
            return [{**json.loads(r["payload"]), "sequence": r["sequence"], "transaction_id": r["transaction_id"]}
                    for r in db.execute("SELECT * FROM events WHERE sequence>? ORDER BY sequence", (after,))]

    def mark_view(self, name, path, revision):
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]
            db.execute("INSERT OR REPLACE INTO views VALUES(?,?,?,?)", (name, str(path), revision, int(revision != current)))

    def view_status(self, name=None):
        with self._db() as db:
            rows = [dict(r) for r in db.execute("SELECT * FROM views ORDER BY name")]
        return rows if name is None else next((r for r in rows if r["name"] == name), None)

    def backup(self, dest):
        dest = Path(dest)
        if dest.exists() and any(dest.iterdir()):
            raise StoreError("backup destination must be empty")
        dest.mkdir(parents=True, exist_ok=True)
        with self._db() as source, sqlite3.connect(dest / "state.sqlite3") as target:
            source.backup(target)
        backup = Store(dest)
        with backup._db() as db:
            refs = {ref for r in db.execute("SELECT data FROM revisions") for ref in blob_refs(json.loads(r[0]))}
        for ref in sorted(refs):
            backup.put_blob(self.read_blob(ref))
        result = backup.verify()
        if not result["ok"]:
            raise StoreError("backup verification failed")
        files = {}
        for path in [dest / "state.sqlite3"] + [backup._blob_path(ref) for ref in sorted(refs)]:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            files[str(path.relative_to(dest))] = {"sha256": digest.hexdigest(), "bytes": path.stat().st_size}
        manifest = {"schema_version": 1, "files": files, "verification": result,
                    "manifest_hash": hashlib.sha256(canonical(files).encode()).hexdigest()}
        with (dest / "backup_manifest.json").open("w") as stream:
            stream.write(canonical(manifest))
            stream.flush()
            os.fsync(stream.fileno())
        return {"path": str(dest), "verification": result, "manifest_hash": manifest["manifest_hash"],
                "manifest": str(dest / "backup_manifest.json")}

    def verify(self):
        with self._db() as db:
            db.execute("BEGIN")
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            refs = {ref for r in db.execute("SELECT data FROM revisions") for ref in blob_refs(json.loads(r[0]))}
            dangling_objects = [r[0] for r in db.execute("SELECT c.id FROM current c LEFT JOIN revisions r ON c.id=r.id AND c.revision=r.revision WHERE r.id IS NULL")]
            unmatched_events = [r[0] for r in db.execute("SELECT e.sequence FROM events e LEFT JOIN outbox o ON e.sequence=o.sequence WHERE o.sequence IS NULL OR o.payload<>e.payload")]
            state_revision, event_count = db.execute("SELECT COALESCE(MAX(sequence),0),COUNT(*) FROM events").fetchone()
            revision_count = db.execute("SELECT COUNT(*) FROM revisions").fetchone()[0]
            object_count = db.execute("SELECT COUNT(*) FROM current").fetchone()[0]
            policy_revision = int(db.execute("SELECT value FROM metadata WHERE key='policy_revision'").fetchone()[0])
        missing, corrupt = [], []
        for ref in sorted(refs):
            try:
                self.read_blob(ref)
            except FileNotFoundError:
                missing.append(ref)
            except StoreError:
                corrupt.append(ref)
        orphans = sorted(p.name for p in self.blobs.iterdir() if p.is_file() and p.name not in refs)
        return {"ok": integrity == "ok" and not missing and not corrupt and not dangling_objects and not unmatched_events,
                "integrity": integrity, "missing_blobs": missing, "corrupt_blobs": corrupt,
                "dangling_objects": dangling_objects, "orphan_blobs": orphans, "unmatched_events": unmatched_events,
                "state_revision": state_revision, "policy_revision": policy_revision,
                "event_count": event_count, "revision_count": revision_count, "object_count": object_count,
                "journal_mode": "delete", "synchronous": "full", "sqlite_version": sqlite3.sqlite_version}
