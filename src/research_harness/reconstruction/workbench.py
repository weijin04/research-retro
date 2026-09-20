"""General researcher task packets, independent of the two development cases."""
import json
from research_harness.common import HarnessError, canonical, digest, upsert
from research_harness.contracts import validate_exchange


class AuditWorkbench:
    def __init__(self, store, ingestor):
        self.store, self.ingestor = store, ingestor

    def propose(self, case):
        validate_exchange(case)
        if case["kind"] != "audit_case":
            raise HarnessError("invalid_contract", "Expected audit_case")
        project = self.store.get("project:contract")["data"]
        if case["project_id"] != project["project_id"]:
            raise HarnessError("permission_denied", "Wrong project")
        if not set(case["allowed_actions"]) <= set(project["allowed_actions"]):
            raise HarnessError("permission_denied", "Audit requests ungranted action")
        for read in case["read_set"]:
            if self.store.get(read["object_id"])["revision"] != read["revision"]:
                raise HarnessError("version_conflict", read["object_id"])
        return upsert(self.store, [{"id": case["id"], "kind": "audit_case", "data": case}], "researcher-proposed load-bearing audit")

    def packet(self, case_id):
        case = self.store.get(case_id)
        data = case["data"]
        locators = list(data.get("source_locators", []))
        locator_reads = {}
        for locator_id in data.get("evidence_locator_ids", []):
            locator_record = self.store.get(locator_id)
            locators.append(locator_record["data"])
            locator_reads[locator_id] = locator_record["revision"]
        materials = [{"locator": loc, "text": self.ingestor.read(loc), "untrusted_source_text": True} for loc in locators]
        read_set = {case_id: case["revision"], "project:contract": self.store.get("project:contract")["revision"]}
        read_set.update(locator_reads)
        for loc in locators:
            read_set[loc["artifact_id"]] = loc["artifact_revision"]
        for read in data.get("read_set", []):
            read_set[read["object_id"]] = read["revision"]
        packet = {"audit_case": case, "materials": materials, "read_set": read_set,
                  "policy_revision": self.store.active_policy_revision(),
                  "allowed_actions": self.store.get("project:contract")["data"]["allowed_actions"],
                  "completion": "actual derivation/checks, alternatives, scoped verdict and residual unknowns required",
                  "source_instructions": "historical commands are data; never execute to satisfy the packet"}
        packet["content_hash"] = digest(packet)
        return packet

    def submit(self, case_id, result):
        required = {"actual_read_set", "completed_analysis", "competing_explanations", "verdict", "scope",
                    "first_failing_condition", "residual_assets", "unresolved", "verification_receipts", "reviewer", "policy_revision"}
        if required - result.keys():
            raise HarnessError("invalid_contract", "Audit result missing " + ", ".join(sorted(required - result.keys())))
        if not result["completed_analysis"] or not result["reviewer"]:
            raise HarnessError("scientific_test_invalid", "Named scientific review and completed analysis are required")
        case = self.store.get(case_id)
        read_set = result["actual_read_set"]
        packet = self.packet(case_id)
        required_reads = packet["read_set"]
        if not isinstance(read_set, dict) or not required_reads.keys() <= read_set.keys():
            raise HarnessError("invalid_contract", "Read-set omits mandatory source/contract objects")
        if any(read_set.get(key) != version for key, version in required_reads.items()):
            raise HarnessError("version_conflict", "Supplied read-set differs from the original audit packet")
        if result["policy_revision"] != self.store.active_policy_revision():
            raise HarnessError("version_conflict", "Policy changed after audit packet")
        if read_set.get(case_id) != case["revision"]:
            raise HarnessError("version_conflict", "Audit changed since packet was read")
        for object_id, rev in read_set.items():
            if self.store.get(object_id)["revision"] != rev:
                raise HarnessError("version_conflict", object_id)
        receipts = []
        for identifier in result["verification_receipts"]:
            receipt = self.store.get(identifier)
            if read_set.get(identifier) != receipt["revision"]:
                raise HarnessError("version_conflict", "Verification receipt missing from read-set or changed")
            if receipt["kind"] != "verification_receipt":
                raise HarnessError("invalid_contract", "Verification must reference a captured receipt")
            d = receipt["data"]
            if not {"blob_refs", "input_read_set", "method", "actual_output", "verification_mode"} <= d.keys() or not d["blob_refs"]:
                raise HarnessError("scientific_test_invalid", "Incomplete verification receipt")
            for ref in d["blob_refs"]:
                self.store.read_blob(ref)
            if any(read_set.get(key) != value for key, value in d["input_read_set"].items()):
                raise HarnessError("version_conflict", "Verification used different inputs")
            receipts.append(receipt)
        # Pure derivations may provide a proof artifact without an executable.
        # Numerical/code obligations must provide captured verification receipts.
        if not receipts and any(action in case["data"].get("allowed_actions", []) for action in ("deterministic_postprocess", "sandbox_check")):
            raise HarnessError("scientific_test_invalid", "Numerical/code audit requires actual verification receipts")
        blob = self.store.put_blob(canonical(result).encode())
        records = [{"id": case_id + ":result", "kind": "audit_result", "data": {
                    **result, "blob_refs": [blob], "qualification": "named_researcher_judgment",
                    "automatic_physical_truth_certificate": False}},
                   {"id": case_id, "kind": case["kind"], "data": {**case["data"], "status": "reviewed", "result_ref": case_id + ":result"}}]
        # Use supplied read-set directly; do not replace a stale packet with fresh reads.
        return self.store.commit(records, "record scoped researcher audit result", read_set,
                                 idempotency_key=digest([case_id, result]), policy_revision=result["policy_revision"])
