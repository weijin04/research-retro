import tempfile
import unittest
from pathlib import Path
from research_harness.storage import Store, StoreError, ConflictError, AuthorityError


def record(id, kind="Claim", **data):
    return {"id": id, "kind": kind, "data": data}


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / "state")
        self.serial = 0

    def commit(self, records, read_set=None):
        self.serial += 1
        return self.store.commit(records, "test", read_set or {}, str(self.serial))

    def test_and_or_cycle_and_independent_evidence(self):
        self.commit([record("a", "Evidence", intrinsic_valid=True), record("b", "Evidence", intrinsic_valid=True),
                     record("and", support_sets=[["a", "b"]]), record("or", support_sets=[["a"], ["b"]]),
                     record("x", support_sets=[["y"]]), record("y", support_sets=[["x"]]), record("empty")])
        for id in ["and", "or"]:
            self.assertEqual(self.store.get(id)["data"]["support_status"], "supported")
        for id in ["x", "y", "empty"]:
            self.assertEqual(self.store.get(id)["data"]["support_status"], "unsupported")
        receipt = self.commit([record("a", "Evidence", intrinsic_valid=True, revoked=True)], {"a": 1})
        self.assertIn("and", receipt["changed_ids"])
        self.assertNotIn("or", receipt["changed_ids"])
        self.assertEqual(self.store.get("and")["data"]["support_status"], "unsupported")
        self.assertEqual(self.store.get("or")["data"]["support_status"], "supported")
        self.assertEqual(self.store.descendants("a"), ["and", "or"])
        self.commit([record("x", support_sets=[["y"], ["b"]])], {"x": 1, "y": 1, "b": 1})
        self.assertEqual(self.store.get("y")["data"]["support_status"], "supported")
        self.commit([record("b", "Evidence", intrinsic_valid=True, revoked=True)], {"b": 1})
        self.assertEqual(self.store.get("x")["data"]["support_status"], "unsupported")
        self.assertEqual(self.store.get("y")["data"]["support_status"], "unsupported")

    def test_stale_related_unrelated_allowed(self):
        self.commit([record("a"), record("b")])
        self.commit([record("b", value=2)], {"b": 1})
        self.commit([record("a", value=3)], {"a": 1})
        with self.assertRaises(ConflictError):
            self.commit([record("a", value=4)], {"a": 1})
        with self.assertRaises(ConflictError):
            self.commit([record("a", value=4)])
        with self.assertRaises(ConflictError):
            self.store.commit([], "test", {}, "policy-stale", policy_revision=2)

    def test_idempotency_and_rollback(self):
        records = [record("a")]
        receipt = self.store.commit(records, "test", {}, "key")
        self.assertEqual(receipt, self.store.commit(records, "test", {}, "key"))
        with self.assertRaises(ConflictError):
            self.store.commit(records, "changed", {}, "key")
        events = self.store.events()
        with self.assertRaises(StoreError):
            self.commit([record("b"), record("bad", intrinsic_valid=True)])
        self.assertEqual(self.store.events(), events)
        with self.assertRaises(KeyError):
            self.store.get("b")
        # An injected SQL failure after revision/event insertion rolls back all tables.
        with self.store._db() as db:
            db.execute("CREATE TRIGGER fail_outbox BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT, 'injected'); END")
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            self.commit([record("c")])
        self.assertEqual(self.store.events(), events)
        with self.assertRaises(KeyError):
            self.store.get("c")

    def test_blob_history_backup_view(self):
        digest = self.store.put_blob(b"original bytes")
        self.commit([record("a", "Artifact", nested={"blob_refs": [digest]}, extensions={"raw": 1})])
        self.store.mark_view("report", "report.html", self.store.events()[-1]["sequence"])
        self.assertFalse(self.store.view_status("report")["stale"])
        self.commit([record("a", "Artifact", extensions={"raw": 2})], {"a": 1})
        self.assertTrue(self.store.view_status("report")["stale"])
        self.assertEqual(self.store.get("a", 1)["data"]["nested"]["blob_refs"], [digest])
        self.assertEqual(len(self.store.history("a")), 2)
        self.assertIn("extensions", self.store.diff("a", 1)["changed_fields"])
        self.store.put_blob(b"unreferenced")
        self.assertEqual(len(self.store.verify()["orphan_blobs"]), 1)
        dest = Path(self.tmp.name) / "backup"
        self.assertTrue(self.store.backup(dest)["verification"]["ok"])
        restored = Store(dest)
        self.assertEqual(restored.read_blob(digest), b"original bytes")
        self.assertEqual(restored.history("a"), self.store.history("a"))
        self.assertEqual(restored.events(), self.store.events())
        with self.assertRaises(FileNotFoundError):
            self.commit([record("missing", blob_refs=["0" * 64])])
        self.assertTrue(self.store.verify()["ok"])

    def test_scientific_cannot_write_policy(self):
        with self.assertRaises(AuthorityError):
            self.commit([record("project:contract", "claim")])
        for kind in ["Policy", "GovernanceDecision", "Authorization", "project_contract", "governance_decision"]:
            with self.assertRaises(AuthorityError):
                self.commit([record("policy", kind)])

    def test_governance_bootstrap_revision_boundary(self):
        receipt = self.store.initialize_project({"scope": "development only"})
        self.assertEqual(receipt["boundary_mode"], "observational")
        self.assertEqual(self.store.active_policy_revision(), 1)
        self.assertEqual(self.store.get("project:contract")["data"]["policy_revision"], 1)
        self.assertEqual(self.store.current_revision(), receipt["state_revision"])
        with self.assertRaises(ConflictError):
            self.store.initialize_project({"scope": "second"})
        with self.assertRaises(AuthorityError):
            self.store.governance_update({"scope": "expanded"}, 1, "worker attempt", authority="worker")
        self.store.mark_view("report", "old.html", self.store.current_revision())
        update = self.store.governance_update({"scope": "restricted"}, 1, "human correction")
        self.assertEqual(update["policy_revision"], 2)
        self.assertEqual(self.store.active_policy_revision(), 2)
        self.assertTrue(self.store.view_status("report")["stale"])
        with self.assertRaises(ConflictError):
            self.store.governance_update({"scope": "stale"}, 1, "stale policy")
        with self.assertRaises(ConflictError):
            self.store.commit([record("c")], "old policy", {}, "old-policy")
        self.store.commit([record("c")], "new policy", {}, "new-policy", policy_revision=2)
        with self.assertRaises(AuthorityError):
            self.store.commit([record("project:contract", "project_contract")], "illegal", {"project:contract": 2}, "illegal", policy_revision=2)
        self.assertEqual(len(self.store.history("project:contract")), 2)

    def test_changed_supports_require_read_premises(self):
        self.commit([record("e", "Evidence", intrinsic_valid=True), record("c")])
        with self.assertRaises(ConflictError):
            self.commit([record("c", support_sets=[["e"]])], {"c": 1})
        with self.assertRaises(StoreError):
            self.commit([record("c", support_sets=[["missing"]])], {"c": 1})
        self.commit([record("c", support_sets=[["e"]])], {"c": 1, "e": 1})
        # A metadata edit does not introduce a new scientific dependence.
        self.commit([record("c", support_sets=[["e"]], note="format")], {"c": 2})
        self.commit([record("e", "Evidence", intrinsic_valid=True, note="new version")], {"e": 1})
        with self.assertRaises(ConflictError):
            self.commit([record("new", support_sets=[["e"]])], {"e": 1})
        self.commit([record("new", support_sets=[["e"]])], {"e": 2})

    def test_adjudication_is_not_affirmative_proposition_support(self):
        self.commit([record("e", "evidence", intrinsic_valid=True),
                     record("c", "claim", evidence_status="refuted", support_sets=[["e"]]),
                     record("downstream", support_sets=[["c"]]),
                     record("negative", "negative_knowledge", support_sets=[["e"]])])
        self.assertTrue(self.store.get("c")["data"]["adjudication_supported"])
        self.assertEqual(self.store.get("c")["data"]["support_status"], "unsupported")
        self.assertEqual(self.store.get("downstream")["data"]["support_status"], "unsupported")
        self.assertEqual(self.store.get("negative")["data"]["support_status"], "supported")
        for field in ["evidence_status", "evidence_verdict", "verdict"]:
            for verdict in ["refuted", "refuted_in_scope", "invalid_test", "unsupported", "unresolved", "mixed", "unchecked", "imported_assertion"]:
                r = self.store.get("c")
                self.commit([record("c", "claim", **{field: verdict}, support_sets=[["e"]])], {"c": r["revision"]})
                self.assertEqual(self.store.get("c")["data"]["support_status"], "unsupported")
        self.commit([record("c", "claim", evidence_status="qualified", support_sets=[["e"]])], {"c": self.store.get("c")["revision"]})
        self.assertEqual(self.store.get("downstream")["data"]["support_status"], "supported")
        self.commit([record("e", "evidence", intrinsic_valid=True, revoked=True)], {"e": 1})
        self.assertFalse(self.store.get("c")["data"]["adjudication_supported"])
        self.assertEqual(self.store.get("negative")["data"]["support_status"], "unsupported")


if __name__ == "__main__":
    unittest.main()
