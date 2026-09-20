"""Discriminating regressions for the public standalone boundary, not CLI mocks."""
import copy
import itertools
import json
from pathlib import Path
import tempfile
import unittest

from research_harness.agent_tools import invoke
from research_harness.common import HarnessError, upsert
from research_harness.config import owned
from research_harness.reconstruction.identity import compare
from research_harness.storage import Store
from research_harness.unit import Unit, init, inspect_bundle


class StandaloneTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.project = self.base / "foreign source"
        self.project.mkdir()
        self.source = self.project / "counts.csv"
        self.source.write_text("n,hit\n1,0\n2,1\n")
        self.workspace = self.base / "state"
        init(self.project, self.workspace)
        self.unit = Unit(self.workspace)

    def call(self, name, **args):
        return invoke({"name": "retro_" + name, "arguments": {"workspace": str(self.workspace), **args}})

    def graph(self):
        observed = self.unit.read("counts.csv")
        self.unit.reconstruct({"based_on": self.unit.store.current_revision(), "nodes": [
            {"id": "e", "kind": "evidence", "text": "counts", "scope": {"sample": "two"},
             "sources": [{"artifact_id": observed["artifact"]["id"], "revision": 1}]},
            {"id": "c", "kind": "claim", "text": "all hit", "scope": {"sample": "two"}, "supports": [["e"]]}]})
        return observed

    def test_default_workspace_is_in_target_and_not_source_intake(self):
        result = init(self.project)
        workspace = self.project / ".retro"
        self.assertEqual(result["workspace"], str(workspace))
        unit = Unit(workspace)
        rows = unit.scan()["sources"][0]["assets"]
        self.assertEqual([row["path"] for row in rows if row["state"] == "captured"], [str(self.source)])
        self.assertFalse(any("state.sqlite3" in row["path"] for row in rows))
        self.assertEqual(self.source.read_text(), "n,hit\n1,0\n2,1\n")

    def test_no_workspace_or_source_authority_silently_selected(self):
        result = invoke({"name": "retro_scan", "arguments": {}})
        self.assertFalse(result["ok"])
        config = self.workspace / "retro.json"
        value = json.loads(config.read_text())
        value["sources"][0]["snapshot_max_bytes"] += 1
        config.write_text(json.dumps(value))
        self.assertEqual(self.call("scan")["error"]["code"], "version_conflict")

    def test_explicit_scan_limits_and_reinitialization_conflict(self):
        workspace = self.base / "bounded"
        init(self.project, workspace, capture_max_bytes=4, scan_max_entries=10, excludes=["cache"])
        result = Unit(workspace).scan()
        self.assertEqual(result["sources"][0]["assets"][0]["state"], "pending_read")
        self.assertEqual(init(self.project, workspace)["receipt"]["status"], "already_initialized")
        with self.assertRaises(HarnessError):
            init(self.project, workspace, capture_max_bytes=100)

    def test_engine_and_output_symlink_escape_rejected(self):
        import research_harness
        package = Path(research_harness.__file__).parent
        with self.assertRaises(HarnessError):
            init(self.project, package / "illegal-state")
        (self.workspace / "escape").symlink_to(self.base)
        with self.assertRaises(HarnessError):
            owned(self.workspace, "escape/should-not-exist")

    def test_raw_evidence_cannot_gain_qualification_via_support_formula(self):
        a = self.unit.read("counts.csv")["artifact"]
        result = self.call("reconstruct", document={"based_on": self.unit.store.current_revision(), "nodes": [
            {"id": "assume", "kind": "assumption", "text": "provisional", "scope": {"x": 1}, "accepted": True, "acceptance_reason": "conditional only"},
            {"id": "raw", "kind": "evidence", "text": "raw", "scope": {"x": 1}, "supports": [["assume"]],
             "sources": [{"artifact_id": a["id"], "revision": a["revision"]}]}]})
        self.assertFalse(result["ok"])
        with self.assertRaises(KeyError):
            self.unit.store.get("assume")

    def test_refuted_inference_cannot_affirm_and_truth_table_all_16_conditions(self):
        store = self.unit.store
        for index, mask in enumerate(itertools.product([False, True], repeat=4)):
            records = [{"id": key, "kind": "evidence" if key.startswith("E") else "assumption", "data": {"intrinsic_valid": True, "revoked": not enabled}}
                       for key, enabled in zip(["E1", "A", "E2", "B"], mask)]
            records += [{"id": "H", "kind": "claim", "data": {"support_sets": [["E1", "A"], ["E2", "B"]]}},
                        {"id": "refuted-inference", "kind": "inference", "data": {"support_sets": [["H"]], "verdict": "refuted"}},
                        {"id": "next", "kind": "claim", "data": {"support_sets": [["refuted-inference"]]}}]
            upsert(store, records, "truth table " + str(index))
            expected = (mask[0] and mask[1]) or (mask[2] and mask[3])
            self.assertEqual(store.get("H")["data"]["support_status"] == "supported", expected)
            self.assertEqual(store.get("refuted-inference")["data"]["support_status"], "unsupported")
            self.assertEqual(store.get("next")["data"]["support_status"], "unsupported")

    def test_fresh_reads_cannot_relabel_analysis_of_old_original(self):
        observed = self.graph()
        packet = self.unit.audit_open("audit", ["c"], "does it follow?", {"sample": "two"}, ["construct counterexample"])
        result = copy.deepcopy(packet["result_template"])
        result.update(completed_analysis={"counterexample": "n=1 has hit=0"}, reviewer="test", verdict="refuted",
                      findings={"c": {"verdict": "refuted", "scope": {"sample": "two"}, "analysis": "observed miss"}})
        self.source.write_text("n,hit\n1,1\n2,1\n")
        self.unit.ingest.refresh()
        result["actual_read_set"][observed["artifact"]["id"]] = self.unit.store.get(observed["artifact"]["id"])["revision"]
        with self.assertRaises(HarnessError) as error:
            self.unit.audit_submit("audit", result)
        self.assertEqual(error.exception.code, "version_conflict")

    def test_missing_root_is_not_successful_empty_census(self):
        self.source.unlink()
        self.project.rmdir()
        result = self.unit.scan()["sources"][0]
        self.assertFalse(result["enumeration_complete"])
        self.assertEqual(result["errors"][0]["error"], "source_root_unavailable")

    def test_unknown_domain_requires_explicit_comparison_fields(self):
        with self.assertRaises(HarnessError):
            compare({"station": "a"}, {"station": "a"}, domain="acoustics", relation="same_object")
        result = compare({"station": "a"}, {"station": "b"}, domain="acoustics", relation="same_object", required_fields=["station", "gain"])
        self.assertEqual(result["status"], "incompatible")
        self.assertEqual(result["unknown"], ["gain"])

    def test_bundle_has_complete_originals_and_rejects_corruption(self):
        self.graph()
        result = self.unit.export()
        bundle = Path(result["bundle"])
        self.source.unlink()
        checked = inspect_bundle(bundle)
        self.assertTrue(checked["verification"]["ok"])
        self.assertFalse(checked["handoff"]["context"]["excluded"])
        (bundle / "handoff.json").write_text("{}")
        with self.assertRaises(HarnessError):
            inspect_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
