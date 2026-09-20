"""Host-controlled investigation broker: frozen packets, evidence views and probes."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import uuid

from research_harness.common import HarnessError, atomic_json, canonical, digest, stable_id, upsert
from research_harness.config import owned
from research_harness.realization.contracts import entity, predicate, validate, walk
from research_harness.runner import contained
from research_harness.storage import ConflictError


def save(store, record, reason):
    try:
        old = store.get(record["id"])
    except KeyError:
        record["revision"] = 1
    else:
        record["revision"] = old["revision"]
        if record == old["data"]:
            return old
        record["revision"] += 1
    upsert(store, [{"id": record["id"], "kind": record["record_type"], "data": record}], reason)
    return store.get(record["id"])


class Investigation:
    def __init__(self, unit):
        self.unit, self.store = unit, unit.store

    def scope(self, document):
        snap = self.store.get(document["snapshot_id"])
        if snap["kind"] != "source_snapshot" or not document.get("goal"):
            raise HarnessError("invalid_contract", "Scope requires a source snapshot and target question")
        refs = document.get("obligations")
        if refs is None:
            refs = [r["id"] for r in self.store.list("obligation") if r["data"]["snapshot_id"] == snap["id"]]
        if not refs:
            raise HarnessError("invalid_contract", "A completion scope needs at least one explicit obligation")
        for identifier in refs:
            r = self.store.get(identifier)
            if r["kind"] != "obligation" or r["data"]["snapshot_id"] != snap["id"]:
                raise HarnessError("invalid_contract", "Scope obligation belongs to another snapshot")
        roles = document.get("roles", {})
        if any(p not in snap["data"]["files"] or role not in {"evidence", "definition", "narrative"} for p, role in roles.items()):
            raise HarnessError("invalid_contract", "Explicit roles must name captured paths and supported content roles")
        # Undeclared prose and instruction files are revealed after sealing; the
        # broker does not equate filenames with scientific definitions.
        roles = {p: roles.get(p, "narrative" if p.endswith((".md", ".txt")) or p.endswith("argument.json") else "evidence")
                 for p in snap["data"]["files"]}
        identifier = document.get("id") or stable_id("scope", document)
        targets = document.get("targets", [])
        for ref in targets:
            if self.store.get(ref["id"])["revision"] != ref["revision"]:
                raise ConflictError("Scope target changed")
        try:
            self.store.get(identifier)
        except KeyError:
            pass
        else:
            raise ConflictError("Scope is immutable; create a new ID to change the goal/roles/obligations")
        return save(self.store, entity("scope", identifier, snap["id"], {"goal": document["goal"], "roles": roles,
                    "obligations": refs, "targets": targets, "phase": "scope_frozen", "policy_revision": self.store.active_policy_revision(),
                    "rule_version": "investigation-1", "qualification": "completion is relative to this frozen scope"}), "freeze investigation scope")

    def next(self, scope, view="evidence-first", obligation=None):
        s = self.store.get(scope)
        if s["kind"] != "scope" or view != "evidence-first":
            raise HarnessError("invalid_contract", "Expected frozen scope and evidence-first view")
        choices = [self.store.get(i) for i in s["data"]["payload"]["obligations"]]
        choices = sorted((r for r in choices if r["data"]["state"] != "discharged" and (obligation is None or r["id"] == obligation)),
                         key=lambda r: (-r["data"].get("extensions", {}).get("priority", 0), r["id"]))
        if not choices:
            return {"status": "no-open-obligations"}
        o = choices[0]
        snapshot = self.store.get(s["data"]["snapshot_id"])
        reads = {scope: s["revision"], o["id"]: o["revision"], snapshot["id"]: snapshot["revision"],
                 "project:contract": self.store.get("project:contract")["revision"]}
        reads.update({r["id"]: r["revision"] for r in snapshot["data"]["files"].values()})
        reads.update({r["id"]: r["revision"] for r in s["data"]["payload"].get("targets", [])})
        packet_id = "task:" + uuid.uuid4().hex
        payload = {"scope_ref": {"id": scope, "revision": s["revision"]}, "obligation_ref": {"id": o["id"], "revision": o["revision"]},
                   "target_question": o["data"]["target_question"], "goal": s["data"]["payload"]["goal"],
                   "phase": "evidence_view", "read_set": reads, "roles": s["data"]["payload"]["roles"],
                   "policy_revision": self.store.active_policy_revision(), "state_revision": self.store.current_revision(),
                   "rules": "investigation-1", "hypotheses": None, "result": None,
                   "assurance": "cooperative: host may see original project; use task run for a contained projection"}
        payload["packet_sha256"] = digest(payload)
        return save(self.store, entity("investigation", packet_id, snapshot["id"], payload), "issue version-bound evidence-first task")

    def packet(self, identifier, reveal=False):
        task = self.store.get(identifier)
        if task["kind"] != "investigation":
            raise HarnessError("invalid_contract", "Expected investigation ID")
        payload = task["data"]["payload"]
        snapshot = self.store.get(task["data"]["snapshot_id"])["data"]
        materials = []
        for path, ref in snapshot["files"].items():
            if reveal or payload["roles"][path] == "evidence":
                materials.append({"path": path, "role": payload["roles"][path], "ref": ref,
                                  "text": self.store.read_blob(ref["sha256"]).decode(errors="replace"), "untrusted": True})
        return {"task": task, "materials": materials, "result_template": {
            "packet_sha256": payload["packet_sha256"], "read_set": payload["read_set"], "scope": self.store.get(payload["obligation_ref"]["id"])["data"]["scope"],
            "outcome": "qualified", "analysis": "", "reviewer": "", "witness_refs": [], "remaining": [], "reopen_conditions": []}}

    def fresh(self, task):
        payload = task["data"]["payload"]
        if payload["policy_revision"] != self.store.active_policy_revision():
            raise ConflictError("Task policy changed")
        # Refresh only the pinned current sources; a stale result cannot silently
        # rebase across changed bytes. Historical snapshot still remains readable.
        self.unit.ingest.refresh()
        for identifier, revision in payload["read_set"].items():
            if self.store.get(identifier)["revision"] != revision:
                raise ConflictError("Task dependency changed: " + identifier)

    def seal(self, identifier, document):
        task = self.store.get(identifier)
        self.fresh(task)
        payload = task["data"]["payload"]
        if payload["phase"] != "evidence_view" or not document.get("hypotheses") or not document.get("analysis"):
            raise HarnessError("invalid_contract", "Seal a nonempty initial construction before narrative reveal")
        payload.update(phase="initial_hypotheses_sealed", hypotheses=copy.deepcopy(document), seal_sha256=digest(document))
        return save(self.store, task["data"], "seal initial hypotheses before revealing narratives")

    def reveal(self, identifier):
        task = self.store.get(identifier)
        self.fresh(task)
        if task["data"]["payload"]["phase"] not in {"initial_hypotheses_sealed", "narrative_reveal"}:
            raise HarnessError("permission_denied", "Seal initial hypotheses before controlled narrative/method reveal")
        task["data"]["payload"]["phase"] = "narrative_reveal"
        save(self.store, task["data"], "reveal model definitions and historical narratives")
        return self.packet(identifier, reveal=True)

    def submit(self, identifier, result):
        task = self.store.get(identifier)
        self.fresh(task)
        payload = task["data"]["payload"]
        obligation = self.store.get(payload["obligation_ref"]["id"])
        if payload["phase"] != "narrative_reveal":
            raise HarnessError("invalid_contract", "Submission requires sealed hypotheses followed by narrative reveal")
        if result.get("packet_sha256") != payload["packet_sha256"] or result.get("read_set") != payload["read_set"]:
            raise ConflictError("Result is not bound to the issued packet")
        if result.get("scope") != obligation["data"]["scope"] or not result.get("analysis") or not result.get("reviewer") or not result.get("reopen_conditions"):
            raise HarnessError("scientific_test_invalid", "Review requires exact scope, completed analysis, named reviewer and reopening conditions")
        refs = result.get("witness_refs", [])
        if not refs or result.get("outcome") not in {"confirmed", "refuted", "qualified", "non_identifiable"}:
            raise HarnessError("scientific_test_invalid", "A scoped conclusion needs versioned witnesses and a valid outcome")
        for ref in refs:
            witness = self.store.get(ref["id"], ref["revision"])
            if self.store.get(ref["id"])["revision"] != ref["revision"]:
                raise ConflictError("Witness is stale")
            if witness["kind"] == "execution_receipt" and not witness["data"]["execution_completed"]:
                if result["outcome"] == "confirmed":
                    raise HarnessError("scientific_test_invalid", "Failed execution does not confirm an obligation")
            elif witness["kind"] not in {"execution_receipt", "artifact", "source_blob", "finding", "realization_contract"}:
                raise HarnessError("scientific_test_invalid", "Unsupported witness kind")
        if result["outcome"] == "non_identifiable":
            histories = result.get("compatible_histories", [])
            if len(histories) < 2 or len({canonical(h.get("answer")) for h in histories}) < 2 or any(not h.get("construction") or not h.get("compatibility_argument") for h in histories):
                raise HarnessError("scientific_test_invalid", "Non-identifiability requires two compatible constructions with different answers")
        if result.get("remaining") and result["outcome"] == "confirmed":
            raise HarnessError("scientific_test_invalid", "Unresolved conditions cannot yield unconditional confirmation")
        for judgment in result.get("judgments", []):
            target = judgment.get("target", {})
            if payload["read_set"].get(target.get("id")) != target.get("revision") or judgment.get("polarity") not in {"positive", "negative"} or not judgment.get("analysis"):
                raise HarnessError("scientific_test_invalid", "Signed judgments must address frozen targets with completed analysis")
            if self.store.get(target["id"])["data"].get("scope") != result["scope"]:
                raise HarnessError("scientific_test_invalid", "Signed judgment scope differs from target")
        version_before = self.store.current_revision()
        obligation["data"].update(state="discharged", outcome=result["outcome"], adjudication="accountable_review", evidence_refs=refs, blockers=[])
        obligation["data"]["extensions"].update(review=result, task_ref={"id": task["id"], "revision": task["revision"] + 1},
                                               read_set=payload["read_set"], reopening_conditions=result["reopen_conditions"])
        payload.update(phase="scoped_adjudication", result=result,
                       rebase_receipt={"issued_state": payload["state_revision"], "submitted_state": version_before,
                                       "related_dependencies_unchanged": True, "policy_unchanged": True})
        # Commit both task and obligation together, checking the frozen read set.
        task["data"]["revision"] = task["revision"] + 1
        obligation["data"]["revision"] = obligation["revision"] + 1
        reads = {**payload["read_set"], task["id"]: task["revision"]}
        reads.update({r["id"]: r["revision"] for r in refs})
        return self.store.commit([task, obligation], "scoped accountable adjudication with rebase evidence", reads,
                                 "task-submit:" + digest([identifier, result]), self.store.active_policy_revision())

    def plan(self, obligation, document=None):
        o = self.store.get(obligation)
        if o["kind"] != "obligation":
            raise HarnessError("invalid_contract", "Probe must answer an obligation")
        if document is None:
            return {"obligation": o, "template": {"script": "print('{}')", "files": [], "interventions": [],
                    "expected_predicates": o["data"]["acceptance_predicates"], "resource_limits": {
                        "wall_seconds": 30, "memory_bytes": 268435456, "max_output_bytes": 1048576}},
                    "permission": "Planning does not execute. probe run explicitly authorizes isolated execution."}
        script = document.get("script")
        if not isinstance(script, str) or not script.strip() or not document.get("expected_predicates"):
            raise HarnessError("invalid_contract", "Probe needs a script and preregistered discriminating predicates")
        snapshot = self.store.get(o["data"]["snapshot_id"])
        selected = {}
        for path in document.get("files", []):
            contained.safe_relative(path)
            if path not in snapshot["data"]["files"]:
                raise HarnessError("invalid_contract", "Probe input is not in frozen snapshot: " + path)
            selected[path] = snapshot["data"]["files"][path]
        edits = document.get("interventions", [])
        for edit in edits:
            if set(edit) != {"target", "before", "after"} or edit["target"] not in selected or not isinstance(edit["after"], str):
                raise HarnessError("invalid_contract", "Intervention must replace an explicitly selected text input")
            before = self.store.read_blob(selected[edit["target"]]["sha256"]).decode()
            if edit["before"] != before:
                raise ConflictError("Intervention before bytes do not match frozen input")
        identifier = "probe:" + uuid.uuid4().hex
        code_hash = self.store.put_blob(script.encode())
        packet = {"obligation": {"id": o["id"], "revision": o["revision"]}, "files": selected, "interventions": edits,
                  "script_sha256": code_hash, "predicates": document["expected_predicates"]}
        spec = {"schema_version": "2.0", "id": identifier, "revision": 1, "snapshot_id": snapshot["id"],
                "record_type": "probe_spec", "extensions": {"files": selected, "script_sha256": code_hash,
                    "blob_refs": [code_hash], "read_set": {o["id"]: o["revision"], **{r["id"]: r["revision"] for r in selected.values()}},
                    "policy_revision": self.store.active_policy_revision()},
                "packet_sha256": digest(packet), "obligation_refs": [{"id": o["id"], "revision": o["revision"]}],
                "probe_kind": document.get("probe_kind", "intervention"), "interventions": edits,
                "held_fixed_refs": [{"id": r["id"], "revision": r["revision"]} for p, r in selected.items() if p not in {e["target"] for e in edits}],
                "expected_predicates": document["expected_predicates"], "minimum_isolation": contained.ISOLATION,
                "resource_limits": document.get("resource_limits", {"wall_seconds": 30, "memory_bytes": 268435456, "max_output_bytes": 1048576})}
        validate(self.store, spec, trusted=True)
        return save(self.store, spec, "freeze discriminating probe, inputs, intervention and predicates")

    def run(self, identifier, isolation="required"):
        if isolation != "required":
            raise HarnessError("permission_denied", "Probe runner only supports required containment; no silent fallback")
        spec_record = self.store.get(identifier)
        if spec_record["kind"] != "probe_spec":
            raise HarnessError("invalid_contract", "Expected probe_spec ID")
        spec = spec_record["data"]
        if spec["extensions"]["policy_revision"] != self.store.active_policy_revision():
            raise ConflictError("Probe policy changed")
        for key, revision in spec["extensions"]["read_set"].items():
            if self.store.get(key)["revision"] != revision:
                raise ConflictError("Probe input changed: " + key)
        projected = {p: self.store.read_blob(r["sha256"]) for p, r in spec["extensions"]["files"].items()}
        for edit in spec["interventions"]:
            projected[edit["target"]] = edit["after"].encode()
        result = contained.run(projected, self.store.read_blob(spec["extensions"]["script_sha256"]), spec["resource_limits"],
                               owned(self.unit.workspace, "probes/" + uuid.uuid4().hex))
        identifier = "execution:" + uuid.uuid4().hex
        outputs = []
        blobs = []
        for name, content in {"stdout": result["stdout"], "stderr": result["stderr"], **result["files"]}.items():
            sha = self.store.put_blob(content)
            artifact_id = stable_id("probe-output", [identifier, name])
            upsert(self.store, [{"id": artifact_id, "kind": "source_blob", "data": {"path": name, "sha256": sha,
                    "blob_refs": [sha], "byte_range": [0, len(content)], "identity_scope": "whole_file",
                    "origin_assurance": "controlled_collector"}}], "capture contained execution output")
            outputs.append({"artifact_id": artifact_id, "sha256": sha})
            blobs.append(sha)
        receipt = {"schema_version": "2.0", "id": identifier, "revision": 1, "snapshot_id": spec["snapshot_id"],
                   "record_type": "execution_receipt", "extensions": {"started": result["started"], "finished": result["finished"],
                     "origin_assurance": "controlled_collector", "blob_refs": blobs, "observations": None},
                   "probe_ref": {"id": spec["id"], "revision": spec_record["revision"]}, "packet_sha256": spec["packet_sha256"],
                   "read_set": [{"id": k, "revision": v} for k, v in spec["extensions"]["read_set"].items()],
                   "runner_sha256": result["runner_sha256"], "script_sha256": result["script_sha256"], "returncode": result["returncode"],
                   "termination": result["termination"], "isolation_observed": result["isolation_observed"], "outputs": outputs,
                   "execution_completed": result["returncode"] == 0 and result["termination"] == "exited", "scientific_adequacy": "unchecked"}
        try:
            receipt["extensions"]["observations"] = json.loads(result["stdout"])
        except (ValueError, UnicodeError):
            pass
        validate(self.store, receipt, trusted=True)
        return save(self.store, receipt, "record actual isolated execution; no scientific discharge")

    def evaluate(self, identifier):
        receipt = self.store.get(identifier)
        if receipt["kind"] != "execution_receipt" or not receipt["data"]["execution_completed"]:
            raise HarnessError("scientific_test_invalid", "Machine evaluation requires completed controlled execution")
        r = receipt["data"]
        spec = self.store.get(r["probe_ref"]["id"], r["probe_ref"]["revision"])["data"]
        observations = r["extensions"]["observations"]
        passed = [predicate(p, observations) for p in spec["expected_predicates"]]
        # Predicate pass/failure is a normal scientific result, not a runner crash.
        result = {"receipt": identifier, "predicate_results": passed, "all_passed": all(passed),
                  "scope": "preregistered probe predicates only; obligation discharge requires the corresponding obligation criteria or review"}
        r["extensions"]["evaluation"] = result
        r["scientific_adequacy"] = "machine_obligation_passed" if all(passed) else "failed"
        save(self.store, r, "independently evaluate preregistered predicates on captured stdout")
        return result
