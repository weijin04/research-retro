from __future__ import annotations

import copy
import json
from pathlib import Path
import sqlite3
import tempfile

from research_harness.common import HarnessError, atomic_json, digest, upsert
from research_harness.realization.contracts import predicate, walk


def verify(path, query_set):
    from research_harness.unit import inspect_bundle
    from research_harness.runner.contained import run
    from research_harness.storage import Store
    checked = inspect_bundle(path)
    root = Path(path).resolve()
    records = {r["id"]: r for r in checked["handoff"]["records"]}
    questions = query_set.get("queries", [])
    if not questions:
        raise HarnessError("invalid_contract", "Handoff verification needs a nonempty query set")
    answers = []
    for question in questions:
        op = question["op"]
        if op == "get":
            answer = records[question["id"]]
            for key in question.get("field", []):
                answer = answer[key]
        elif op == "find":
            answer = [r for r in records.values() if r["kind"] == question["kind"]]
        elif op == "read":
            ref = records[question["id"]]["data"]
            sha = ref["sha256"]
            content = (root / "store/blobs" / sha).read_bytes()
            start, end = question.get("start", 0), question.get("end", len(content))
            if not 0 <= start <= end <= len(content):
                raise HarnessError("invalid_locator", "Handoff byte locator exceeds capture")
            answer = content[start:end].decode(errors="replace")
        elif op == "withdraw":
            # Counterfactual read-only projection; never rewrites frozen history.
            nodes = copy.deepcopy(records)
            if "at_state_revision" in question:
                with sqlite3.connect((root / "store/state.sqlite3").as_uri() + "?mode=ro", uri=True) as db:
                    rows = db.execute("SELECT r.id,r.kind,r.revision,r.data FROM revisions r JOIN "
                        "(SELECT id,MAX(revision) AS revision FROM events WHERE sequence<=? GROUP BY id) e "
                        "ON r.id=e.id AND r.revision=e.revision", (question["at_state_revision"],)).fetchall()
                nodes = {r[0]: {"id": r[0], "kind": r[1], "revision": r[2], "data": json.loads(r[3])} for r in rows}
            for identifier in question["ids"]:
                if identifier not in nodes:
                    raise HarnessError("invalid_contract", "Unknown withdrawal target: " + identifier)
                nodes[identifier]["data"]["revoked"] = True
            if "scope" in question:
                from research_harness.diagnosis.scoped import projection
                answer = projection(nodes, question["scope"], question["ids"])
                if not answer["nodes"]:
                    raise HarnessError("invalid_contract", "No scientific graph in the requested scope")
            else:
                Store._support(nodes)
                answer = {identifier: r["data"]["support_status"] for identifier, r in nodes.items() if "support_status" in r["data"]}
                if not answer:
                    raise HarnessError("invalid_contract", "No legacy support graph; provide the typed graph's explicit scope")
        elif op == "replay":
            receipt = records[question["id"]]["data"]
            spec = records[receipt["probe_ref"]["id"]]["data"]
            if spec["revision"] != receipt["probe_ref"]["revision"]:
                raise HarnessError("version_conflict", "Replay probe revision is not the receipt's probe")
            projected = {p: (root / "store/blobs" / r["sha256"]).read_bytes() for p, r in spec["extensions"]["files"].items()}
            for edit in spec["interventions"]:
                projected[edit["target"]] = edit["after"].encode()
            code = (root / "store/blobs" / spec["extensions"]["script_sha256"]).read_bytes()
            with tempfile.TemporaryDirectory(prefix="retro-replay-") as temporary:
                result = run(projected, code, spec["resource_limits"], Path(temporary) / "outputs")
            passed = []
            if result["returncode"] == 0:
                observation = json.loads(result["stdout"])
                passed = [predicate(p, observation) for p in spec["expected_predicates"]]
            answer = {"returncode": result["returncode"], "termination": result["termination"],
                      "predicates": passed, "all_passed": bool(passed) and all(passed),
                      "script_sha256": result["script_sha256"], "stdout_sha256": digest(result["stdout"])}
        else:
            raise HarnessError("invalid_contract", "Unknown portable query: " + str(op))
        answers.append({"query": question, "answer": answer, "passed": answer == question["expected"] if "expected" in question else
                        answer["all_passed"] if op == "replay" else True})
    return {"schema_version": "2.0", "status": "verified" if all(a["passed"] for a in answers) else "query-failed",
            "snapshot_id": checked["handoff"].get("snapshot_id"), "read_set": {}, "findings": [], "gaps": [],
            "receipts": answers, "capabilities": {"offline_query": True, "original_project_required": False},
            "verification": checked["verification"], "all_passed": all(a["passed"] for a in answers),
            "boundary": "Query/replay verification is not a blank Agent understanding assessment"}


def migrate(source, destination=None, apply=False):
    from research_harness.unit import init, Unit
    from research_harness.config import outside_engine
    source = Path(source).resolve()
    db = source / "state/state.sqlite3"
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as conn:
        rows = conn.execute("SELECT id,revision,kind,data FROM revisions ORDER BY id,revision").fetchall()
    config = json.loads((source / "retro.json").read_text())
    mapping = [{"id": identifier, "revision": revision, "target": "legacy:" + digest([identifier, revision])[:24],
                "kind": kind} for identifier, revision, kind, raw in rows]
    result = {"schema_version": "2.0", "source": str(source), "source_sha256": digest(db.read_bytes()),
              "mapping": mapping, "status": "dry-run", "qualification": "Historical judgments retained as unchecked assertions; missing execution fields stay unknown"}
    if not apply:
        return result
    if destination is None:
        raise HarnessError("invalid_contract", "Migration apply requires a new destination workspace")
    dest = outside_engine(destination)
    if dest == source or dest.is_relative_to(source) or source.is_relative_to(dest):
        raise HarnessError("permission_denied", "Migration destination must be separate from the old workspace")
    if dest.exists() and any(dest.iterdir()):
        raise HarnessError("invalid_contract", "Migration destination must be empty")
    project = (source / config["sources"][0]["root"]).resolve()
    init(project, dest, project_id=config["project_id"])
    unit = Unit(dest)
    imported = []
    for item, (identifier, revision, kind, raw) in zip(mapping, rows):
        data = json.loads(raw)
        from research_harness.storage.store import blob_refs
        for sha in blob_refs(data):
            content = (source / "state/blobs" / sha).read_bytes()
            if digest(content) != sha:
                raise HarnessError("corrupt_state", "Legacy blob hash mismatch")
            unit.store.put_blob(content)
        imported.append({"id": item["target"], "kind": "legacy_assertion", "data": {
            "source_id": identifier, "source_revision": revision, "source_kind": kind, "original": data,
            "qualification": "imported_assertion", "historical_execution": "unknown", "scientific_validity": "unchecked"}})
    upsert(unit.store, imported, "explicit copy migration; no silent scientific qualification")
    if digest(db.read_bytes()) != result["source_sha256"]:
        raise HarnessError("source_changed", "Legacy database changed during migration; target is not certified")
    result.update(status="migrated", destination=str(dest), verification=unit.store.verify())
    atomic_json(dest / "migration.json", result)
    return result
