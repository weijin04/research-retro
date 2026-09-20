"""Read-only source access, bounded immutable captures and restartable imports."""
from __future__ import annotations
import csv
import io
import json
import os
import stat
import subprocess
import zipfile
from collections import Counter
from pathlib import Path
from research_harness.common import HarnessError, canonical, digest, stable_id, now, upsert


class Ingestor:
    VERSION = "ingest-2"

    def __init__(self, store, manifest):
        self.store, self.manifest = store, manifest

    def allowed(self, path):
        path = Path(path).absolute()
        if any(path.resolve().is_relative_to(Path(p).resolve())
               for source in self.manifest["sources"] for p in source.get("excluded_paths", [])):
            raise HarnessError("permission_denied", "Workspace/output is excluded from source intake")
        # Reject historical references outside lexical scope before touching their
        # filesystem (including slow or unavailable mounts).
        candidates = []
        for source in self.manifest["sources"]:
            lexical_root = Path(source["root"]).absolute()
            if path.is_relative_to(lexical_root):
                parts = path.relative_to(lexical_root).parts
                if not any(p in source.get("excludes", []) for p in parts):
                    candidates.append((source, lexical_root))
        if candidates:
            actual = path.resolve()
            for source, lexical_root in candidates:
                root = lexical_root.resolve()
                if actual.is_relative_to(root):
                    parts = actual.relative_to(root).parts
                    if not any(p in source.get("excludes", []) for p in parts):
                        return source, actual
        raise HarnessError("permission_denied", f"Source outside allowed roots or excluded: {path}")

    @staticmethod
    def _stat(s):
        return {"size": s.st_size, "mtime_ns": s.st_mtime_ns, "ctime_ns": s.st_ctime_ns,
                "device": s.st_dev, "inode": s.st_ino}

    @staticmethod
    def _open_pinned(path):
        """Walk a resolved absolute name without following any swapped symlink."""
        directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in Path(path).parts[1:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                os.close(directory)
                directory = child
            return os.open(Path(path).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        finally:
            os.close(directory)

    def _invalidations(self, identifier, reason):
        changes = []
        for record in self.store.list():
            if record["kind"].lower() in {"evidence", "assumption"} and any(
                    loc.get("artifact_id") == identifier for loc in record["data"].get("source_locators", [])):
                changes.append({"id": record["id"], "kind": record["kind"], "data": {
                    **record["data"], "revoked": True, "reassessment_required": True, "revision_reason": reason}})
        return changes

    def _unavailable(self, artifact, reason):
        changes = [{"id": artifact["id"], "kind": artifact["kind"], "data": {
            **artifact["data"], "read_state": "unavailable", "live_unavailable_reason": reason}}]
        changes += self._invalidations(artifact["id"], "original source unavailable; historical snapshot retained")
        upsert(self.store, changes, "mark unavailable source and invalidate dependent evidence")

    def capture(self, path, *, max_bytes=None, segment=None):
        source, actual = self.allowed(path)
        cap = source.get("snapshot_max_bytes", 33554432) if max_bytes is None else max_bytes
        identifier = stable_id("artifact", [self.manifest["project_id"], str(Path(path).absolute())])
        # O_NOFOLLOW denies a symlink swapped in after resolution. fstat pins the opened inode.
        fd = self._open_pinned(actual)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise HarnessError("unsupported_format", "Only regular files may be captured")
            if not segment and before.st_size > cap:
                raise HarnessError("read_budget", "File exceeds capture budget; request a bounded segment", {"size": before.st_size, "limit": cap})
            start, end = segment or (0, before.st_size)
            if start < 0 or end < start or end > before.st_size or end - start > cap:
                raise HarnessError("invalid_locator", "Invalid or over-budget byte range")
            os.lseek(fd, start, os.SEEK_SET)
            with os.fdopen(fd, "rb", closefd=False) as f:
                fingerprint = self.store.put_stream(f, end - start)
            after = os.fstat(fd)
            # Repeat root validation to reject changed ancestors and pathname replacements.
            _, actual_after = self.allowed(path)
            named = actual_after.stat()
            if self._stat(before) != self._stat(after) or self._stat(after) != self._stat(named):
                raise HarnessError("source_changed", str(path))
        finally:
            os.close(fd)
        try:
            old = self.store.get(identifier)
        except KeyError:
            old = None
        if old and old["data"].get("sha256") == fingerprint and old["data"].get("byte_range") == [start, end] and old["data"].get("read_state") == "read":
            return old
        data = {"path": str(Path(path).absolute()), "resolved_path": str(actual), "source_id": source["id"],
                "sha256": fingerprint, "blob_refs": [fingerprint], "byte_range": [start, end],
                "identity_scope": "captured_segment" if segment else "whole_file", "read_state": "read",
                "source_before": self._stat(before), "source_after": self._stat(after), "captured_at": now(),
                "egress": source.get("egress", "denied"), "parser_version": None, "is_original": False,
                "provenance": "independent byte copy; no hardlink or symlink snapshot"}
        changes = [{"id": identifier, "kind": "artifact", "data": data}]
        # A changed original invalidates precisely the evidence that used its earlier snapshot.
        if old:
            changes += self._invalidations(identifier, "original source changed; retained evidence belongs to previous snapshot")
        upsert(self.store, changes, "capture source version and propagate source change")
        return self.store.get(identifier)

    def locator(self, artifact, start=1, end=None, kind="lines", note="source with conditions"):
        content = self.store.read_blob(artifact["data"]["sha256"])
        if end is None:
            end = len(content.decode("utf-8", errors="replace").splitlines()) if kind == "lines" else len(content)
        return {"schema_version": "0.1.0", "project_id": self.manifest["project_id"],
                "id": stable_id("locator", [artifact["id"], artifact["revision"], kind, start, end]),
                "is_example": False, "kind": "source_locator", "artifact_id": artifact["id"],
                "artifact_revision": artifact["revision"], "uri": artifact["data"]["path"],
                "content_identity": {"algorithm": "sha256", "digest": artifact["data"]["sha256"],
                                     "scope": artifact["data"]["identity_scope"]},
                "locator": {"type": kind, "start": start, "end": end, "index_base": 1 if kind in ("lines", "cells") else 0, "context_note": note},
                "availability": "captured", "extensions": {}}

    def read(self, locator, *, live=False):
        a = self.store.get(locator["artifact_id"], locator["artifact_revision"])
        if locator["content_identity"]["digest"] != a["data"]["sha256"]:
            raise HarnessError("invalid_locator", "Fingerprint does not match artifact version")
        content = self.store.read_blob(a["data"]["sha256"])
        if live:
            current = self.capture(a["data"]["path"], segment=tuple(a["data"]["byte_range"]) if a["data"]["identity_scope"] == "captured_segment" else None)
            if current["data"]["sha256"] != a["data"]["sha256"]:
                raise HarnessError("source_changed", "Live source differs; historical snapshot remains readable")
        loc = locator["locator"]
        start, end = loc["start"], loc["end"]
        if loc["type"] == "bytes":
            if not 0 <= start <= end <= len(content):
                raise HarnessError("invalid_locator", "Byte range outside snapshot")
            return content[start:end].decode("utf-8", errors="replace")
        if loc["type"] == "lines":
            lines = content.decode("utf-8", errors="replace").splitlines()
            if not 1 <= start <= end <= len(lines):
                raise HarnessError("invalid_locator", "Line range outside snapshot")
            return "\n".join(lines[start - 1:end])
        if loc["type"] == "cells":
            rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig")), delimiter="\t" if a["data"]["path"].endswith(".tsv") else ","))
            if not 1 <= start <= end <= len(rows):
                raise HarnessError("invalid_locator", "Record range outside table")
            return {"rows": rows[start-1:end], "index_semantics": "1-based logical data records, excluding header"}
        raise HarnessError("unsupported_locator", loc["type"])

    def import_table(self, path):
        artifact = self.capture(path)
        identity = stable_id("index", [self.manifest["project_id"], str(Path(path).absolute())])
        try:
            old = self.store.get(identity)
            if old["data"]["sha256"] == artifact["data"]["sha256"] and old["data"]["importer_version"] == self.VERSION:
                return {"status": "unchanged", "id": identity, "row_count": old["data"]["row_count"]}
        except KeyError:
            pass
        text = self.store.read_blob(artifact["data"]["sha256"]).decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text), delimiter="\t" if str(path).endswith(".tsv") else ",")
        counts, n, outside = Counter(), 0, 0
        for n, row in enumerate(reader, 1):
            counts[row.get("candidate_family_id", row.get("job_root_label", row.get("record_type", "records")))] += 1
            raw_path = row.get("main_output_path", row.get("absolute_path", ""))
            if raw_path:
                try:
                    self.allowed(raw_path)
                except HarnessError:
                    outside += 1
        data = {"source_artifact_id": artifact["id"], "artifact_revision": artifact["revision"],
                "path": str(Path(path).absolute()), "sha256": artifact["data"]["sha256"],
                "blob_refs": artifact["data"]["blob_refs"], "columns": reader.fieldnames, "row_count": n,
                "groups": dict(counts), "outside_reference_rows": outside, "importer_version": self.VERSION,
                "qualification": "imported_assertion", "current_scientific_validity": "unchecked",
                "time_semantics": "row fields retained; mtime is not scientific event time",
                "source_locator": self.locator(artifact, 1, n, "cells") if n else None}
        receipt = upsert(self.store, [{"id": identity, "kind": "index_table", "data": data}], "migrate historical table without promoting its judgments")
        return {"status": "imported_assertion", "id": identity, "row_count": n, "receipt": receipt}

    def query_tables(self, text, limit=30, table=None):
        matches = []
        for index in self.store.list("index_table"):
            d = index["data"]
            if table and table not in d["path"]:
                continue
            content = self.store.read_blob(d["sha256"]).decode("utf-8-sig")
            for n, row in enumerate(csv.DictReader(io.StringIO(content), delimiter="\t" if d["path"].endswith(".tsv") else ","), 1):
                if text.casefold() in canonical(row).casefold():
                    matches.append({"index_id": index["id"], "row": n, "raw": row, "qualification": "imported_assertion",
                                    "source_locator": {**d["source_locator"], "locator": {**d["source_locator"]["locator"], "start": n, "end": n}}})
                    if len(matches) >= limit:
                        return matches
        return matches

    def scan(self, source_id, *, max_entries=None):
        source = next(s for s in self.manifest["sources"] if s["id"] == source_id)
        root = Path(source["root"]).resolve()
        identity = stable_id("coverage", [self.manifest["project_id"], source_id])
        oldrows = {}
        try:
            old = self.store.get(identity)
            oldrows = {r["path"]: r for r in json.loads(self.store.read_blob(old["data"]["ledger_hash"]))}
        except KeyError:
            pass
        rows, errors, counts = [], [], Counter()
        limit = max_entries or source.get("scan_max_entries", 250000)
        snapshots = {r["data"]["path"]: r for r in self.store.list("artifact")}
        truncated = False
        def onerror(error):
            errors.append({"path": error.filename, "error": type(error).__name__})
        if not root.is_dir():
            errors.append({"path": str(root), "error": "source_root_unavailable"})
        for folder, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
            kept = []
            for directory in sorted(dirs):
                p = Path(folder) / directory
                if directory in source.get("excludes", []) or any(p.resolve().is_relative_to(Path(x).resolve()) for x in source.get("excluded_paths", [])):
                    rows.append({"path": str(p), "state": "not_in_scope", "reason": "manifest directory exclusion; descendants not enumerated"})
                elif p.is_symlink():
                    rows.append({"path": str(p), "state": "not_in_scope", "reason": "directory symlink not traversed"})
                else:
                    kept.append(directory)
            dirs[:] = kept
            for filename in sorted(files):
                p = Path(folder) / filename
                row = {"path": str(p)}
                try:
                    _, actual = self.allowed(p)
                    info = actual.stat()
                    row.update(self._stat(info))
                    row["resolved_path"] = str(actual)
                    if not stat.S_ISREG(info.st_mode):
                        row.update(state="unsupported_format", reason="not a regular file")
                    elif str(p) in snapshots:
                        a = snapshots[str(p)]["data"]
                        row.update(state="read", artifact_id=snapshots[str(p)]["id"], sha256=a["sha256"],
                                   qualification="captured version; live content not rehashed by metadata scan")
                        if any(row[k] != a["source_after"][k] for k in ("size", "mtime_ns", "ctime_ns", "inode", "device")):
                            row.update(state="source_changed", reason="metadata change; refresh snapshot required")
                    else:
                        row.update(state="pending_read", reason="metadata only; retained for audit selection",
                                   byte_ranges_not_read=[[0, info.st_size]])
                    previous = oldrows.get(str(p))
                    row["delta"] = "added" if not previous else ("metadata_unchanged_content_unverified" if all(previous.get(k) == row.get(k) for k in ("size", "mtime_ns", "ctime_ns", "inode", "device")) else "changed")
                except HarnessError as e:
                    row.update(state="not_in_scope", reason=e.code)
                except OSError as e:
                    row.update(state="read_failed", reason=type(e).__name__)
                rows.append(row)
                if len(rows) >= limit:
                    truncated = True
                    break
            if truncated:
                break
        paths = {r["path"] for r in rows}
        if not truncated and not errors:
            known_paths = set(oldrows) | {path for path in snapshots if Path(path).is_relative_to(root)}
            for path in sorted(known_paths - paths):
                rows.append({"path": path, "state": "unavailable", "reason": "absent in fresh source enumeration", "delta": "removed"})
                if path in snapshots:
                    self._unavailable(snapshots[path], "absent in complete source enumeration")
        for row in rows:
            counts[row["state"]] += 1
        blob = self.store.put_blob(canonical(rows).encode())
        data = {"source_id": source_id, "root": str(root), "ledger_hash": blob, "blob_refs": [blob],
                "denominator": len(rows), "counts": dict(counts), "enumeration_complete": not truncated and not errors,
                "scope": "files plus explicitly excluded directory roots; excluded descendants not part of denominator",
                "content_identity": "metadata scan does not prove unchanged bytes", "errors": errors,
                "scan_started_or_finished_at": now(), "dataset_role": self.manifest.get("dataset_role", "unspecified")}
        upsert(self.store, [{"id": identity, "kind": "coverage", "data": data}], "source metadata delta and complete processing ledger")
        return {"id": identity, **{k: v for k, v in data.items() if k != "blob_refs"}}

    def refresh(self):
        results = []
        for record in self.store.list("artifact"):
            d = record["data"]
            try:
                a = self.capture(d["path"], segment=tuple(d["byte_range"]) if d["identity_scope"] == "captured_segment" else None)
                results.append({"id": a["id"], "status": "unchanged" if a["revision"] == record["revision"] else "source_changed"})
            except (HarnessError, OSError) as e:
                self._unavailable(record, getattr(e, "code", type(e).__name__))
                results.append({"id": record["id"], "status": getattr(e, "code", "unavailable")})
        return results

    def git_metadata(self, source_id):
        source = next(s for s in self.manifest["sources"] if s["id"] == source_id)
        result = subprocess.run(["git", "-C", source["root"], "rev-parse", "--show-toplevel", "HEAD"], capture_output=True, text=True, timeout=15)
        return {"source_id": source_id, "exit_code": result.returncode, "observed_at": now(),
                "raw": result.stdout.strip(), "scope": "current git identity only; not proof of historical executed code"}

    def archive_directory(self, path, max_entries=1000, max_uncompressed=67108864):
        artifact = self.capture(path)
        content = io.BytesIO(self.store.read_blob(artifact["data"]["sha256"]))
        if not zipfile.is_zipfile(content):
            return {"state": "unsupported_format", "reason": "only ZIP directory inspection implemented; no extraction"}
        with zipfile.ZipFile(content) as archive:
            infos = archive.infolist()
            if len(infos) > max_entries or sum(x.file_size for x in infos) > max_uncompressed:
                raise HarnessError("read_budget", "Archive directory exceeds budget")
            entries = [{"name": i.filename, "size": i.file_size,
                        "unsafe_path": Path(i.filename).is_absolute() or ".." in Path(i.filename).parts,
                        "symlink": stat.S_ISLNK(i.external_attr >> 16)} for i in infos]
        return {"state": "directory_only", "entries": entries, "extracted": False}
