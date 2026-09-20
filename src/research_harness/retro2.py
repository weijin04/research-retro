"""Research Retro 2 public services layered over the compatible revision store."""
from __future__ import annotations

import json
from pathlib import Path

from research_harness.common import HarnessError, digest, stable_id, upsert
from research_harness.diagnosis.support import project
from research_harness.investigation import Investigation, save
from research_harness.realization.contracts import entity, import_records, walk
from research_harness.recovery import RULE_VERSION
from research_harness.recovery.engine import recover
from research_harness.recovery.snapshot import freeze
from research_harness.runner.contained import capabilities
from research_harness.storage import ConflictError


class Service:
    def __init__(self, unit):
        self.unit, self.store = unit, unit.store
        self.investigation = Investigation(unit)

    def response(self, result, snapshot_id=None):
        return {"schema_version": "2.0", "snapshot_id": snapshot_id or result.get("snapshot_id") or result.get("data", {}).get("snapshot_id"),
                "read_set": result.get("read_set", {}), "findings": result.get("findings", []), "gaps": result.get("gaps", []),
                "receipts": result.get("receipts", []), "capabilities": {"model_calls": False, "network": False,
                    "recovery_rules": RULE_VERSION, "contained_runner": "probe with retro capabilities"},
                "status": result.get("status", "ok"), "result": result}

    def snapshot(self):
        result = freeze(self.unit)
        return self.response(result, result["id"])

    def recover(self, snapshot):
        if snapshot == "latest":
            snaps = self.store.list("source_snapshot")
            snapshot = max(snaps, key=lambda r: next((e["sequence"] for e in reversed(self.store.events()) if e["id"] == r["id"]), 0))["id"] if snaps else freeze(self.unit)["id"]
        return self.response(recover(self.unit, snapshot), snapshot)

    def records(self, document):
        return self.response(import_records(self.unit, document))

    def capabilities(self):
        return self.response(capabilities())

    def explain(self, id, revision=None):
        record = self.store.get(id, revision)
        originals = []
        for value in walk(record["data"]):
            if "artifact_id" in value and "start_byte" in value:
                artifact = self.store.get(value["artifact_id"], value["artifact_revision"])
                content = self.store.read_blob(artifact["data"]["sha256"])
                if value["sha256"] != digest(content) or not 0 <= value["start_byte"] <= value["end_byte_exclusive"] <= len(content):
                    raise HarnessError("invalid_locator", "Invalid stored explanation locator")
                originals.append({"locator": value, "text": content[value["start_byte"]:value["end_byte_exclusive"]].decode(errors="replace")})
        return self.response({"record": record, "originals": originals, "impact": self._impact(id)})

    def _impact(self, identifier):
        records = self.store.list()
        found, frontier = set(), {identifier}
        while frontier:
            added = set()
            for record in records:
                if record["id"] in found or record["id"] == identifier:
                    continue
                deps = set(record["data"].get("source_dependencies", []))
                for item in walk(record["data"]):
                    if set(item) == {"id", "revision"}:
                        deps.add(item["id"])
                    if "artifact_id" in item:
                        deps.add(item["artifact_id"])
                    if isinstance(item.get("read_set"), dict):
                        deps.update(item["read_set"])
                    for group in item.get("support_sets", []):
                        deps.update(group)
                if deps & frontier:
                    added.add(record["id"])
            found |= added
            frontier = added
        return sorted(found)

    def impact(self, id):
        self.store.get(id)
        return self.response({"id": id, "affected": self._impact(id), "history_retained": True})

    def contrast(self, left, right, observable):
        a, b, o = self.store.get(left), self.store.get(right), self.store.get(observable)
        if o["kind"] != "observable_definition":
            raise HarnessError("invalid_contract", "Comparison requires an explicit observable_definition")
        definition = o["data"]["payload"]
        required = ["observable", "unit", "reference_state", "object", "boundary_conditions", "sampling"]
        x, y = a["data"].get("payload", {}), b["data"].get("payload", {})
        reasons = []
        for field in required:
            if field not in definition or field not in x.get("comparison_context", {}) or field not in y.get("comparison_context", {}):
                reasons.append({"field": field, "reason": "missing explicit definition or comparison context"})
            elif x["comparison_context"][field] != y["comparison_context"][field] or x["comparison_context"][field] != definition[field]:
                reasons.append({"field": field, "reason": "incompatible"})
        hashes_a, hashes_b = x.get("source_hashes", {}), y.get("source_hashes", {})
        payload = {"left": {"id": left, "revision": a["revision"]}, "right": {"id": right, "revision": b["revision"]},
                   "observable": {"id": observable, "revision": o["revision"]}, "comparable": not reasons, "reasons": reasons,
                   "changed_dependencies": sorted(k for k in set(hashes_a) | set(hashes_b) if hashes_a.get(k) != hashes_b.get(k)),
                   "observations": [x.get("reported", x.get("value")), y.get("reported", y.get("value"))],
                   "equivalence": "not established; numeric tolerance never merges identities"}
        record = entity("comparison", stable_id("comparison", payload), o["data"]["snapshot_id"], payload, o["data"]["scope"])
        return self.response(save(self.store, record, "check comparability before contrasting frozen observations"))

    def task(self, action, **args):
        if action == "run":
            identifier, script = args["id"], args["script"]
            task = self.investigation.packet(identifier, reveal=False)
            record = task["task"]
            if record["data"]["payload"]["phase"] != "evidence_view":
                raise HarnessError("invalid_contract", "Contained initial investigation requires evidence_view phase")
            from research_harness.runner.contained import run
            from research_harness.config import owned
            import uuid
            code = owned(self.unit.workspace, script).read_bytes()
            projection = {m["path"]: self.store.read_blob(m["ref"]["sha256"]) for m in task["materials"]}
            result = run(projection, code, {"wall_seconds": 30, "memory_bytes": 268435456, "max_output_bytes": 1048576},
                         owned(self.unit.workspace, "tasks/" + uuid.uuid4().hex))
            logs = {name: self.store.put_blob(result[name]) for name in ("stdout", "stderr")}
            record["data"]["payload"]["contained_execution"] = {"logs": logs, "blob_refs": list(logs.values()),
                "script_sha256": result["script_sha256"], "isolation": result["isolation_observed"],
                "returncode": result["returncode"], "termination": result["termination"],
                "materials": [m["ref"] for m in task["materials"]], "assurance": "contained projection; access does not prove understanding"}
            return self.response(save(self.store, record["data"], "capture contained evidence-view investigation"))
        method = {"scope": "scope", "next": "next", "packet": "packet", "seal": "seal", "reveal": "reveal", "submit": "submit"}[action]
        if "id" in args:
            args["identifier"] = args.pop("id")
        return self.response(getattr(self.investigation, method)(**args))

    def probe(self, action, **args):
        if "id" in args:
            args["identifier"] = args.pop("id")
        return self.response(getattr(self.investigation, action)(**args))

    def support(self, scope):
        from research_harness.diagnosis.scoped import projection
        return self.response(projection(self.store.list(), scope))

    def stale_obligation(self, obligation):
        for identifier, revision in obligation["data"].get("extensions", {}).get("read_set", {}).items():
            if identifier == obligation["id"]:
                continue
            if self.store.get(identifier)["revision"] != revision:
                return True
        return False

    def close(self, scope):
        self.unit.ingest.refresh()
        s = self.store.get(scope)
        if s["kind"] != "scope":
            raise HarnessError("invalid_contract", "Completion requires a frozen scope")
        snap = self.store.get(s["data"]["snapshot_id"])
        obligations = [self.store.get(i) for i in s["data"]["payload"]["obligations"]]
        open_items = [o["id"] for o in obligations if o["data"]["state"] != "discharged" or self.stale_obligation(o)]
        coverage = snap["data"]["coverage"]
        gaps = snap["data"]["gaps"]
        coverage_blocked = bool(gaps) or any(not c["enumeration_complete"] for c in coverage)
        status = "open-blocked" if open_items or coverage_blocked else "closed-qualified" if any(o["data"]["outcome"] in {"qualified", "non_identifiable"} for o in obligations) else "closed-resolved"
        payload = {"scope_ref": {"id": scope, "revision": s["revision"]}, "goal": s["data"]["payload"]["goal"],
                   "rule_version": RULE_VERSION, "obligation_refs": [{"id": o["id"], "revision": o["revision"]} for o in obligations],
                   "status": status, "unresolved_obligations": open_items, "gaps": gaps, "coverage": coverage,
                   "conclusions": [{"id": o["id"], "question": o["data"]["target_question"], "outcome": o["data"]["outcome"],
                       "review": o["data"]["extensions"].get("review")} for o in obligations if o["id"] not in open_items],
                   "completion_boundary": "Only frozen scope, goal, rules and required obligations; no universal scientific truth certificate"}
        identifier = stable_id("closure", payload)
        record = entity("reconstruction_package", identifier, snap["id"], payload)
        save(self.store, record, "freeze scope-relative completion certificate and explicit residuals")
        return self.response({"id": identifier, "snapshot_id": snap["id"], **payload})
