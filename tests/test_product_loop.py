"""Product boundaries: direct investigation, revision, usable views and handoff."""
import json
from pathlib import Path
import shutil
from unittest.mock import patch
import unittest

from research_harness.agent_tools import invoke
from research_harness.storage import ConflictError
from research_harness.unit import inspect_bundle
from research_harness.unit import Unit, start
import test_workflow as fixtures
import test_semantic_workflow as semantic_fixtures


class ProductLoopTests(unittest.TestCase):
    setUp = fixtures.WorkflowTest.setUp
    n = fixtures.WorkflowTest.n

    def record(self, nodes, revisions=None, **kw):
        return self.w.record({"question": "What did the attempt establish?", "reviewer": "test host",
            "analysis": "Checked original observations; scoped conclusions and actual next work.",
            "materials": [{"key": "obs", "path": "mixed.md", "role": "evidence"}],
            "nodes": nodes, "revisions": revisions or {}, **kw})

    def test_direct_reconstruction_and_revision_reach_new_reader(self):
        self.record([self.n("O", statement="The measurement is available."),
            self.n("C", "claim", statement="Initial bounded interpretation.", supports=[["O"]]),
            self.n("R", "route", statement="Current route.", requires=["C"], action="Old proposed test."),
            self.n("U", statement="Independent result.")])
        self.w.spine({"sections": [{"title": "Understanding and next work", "nodes": ["C", "R"]}]})
        frozen = self.w.publish()
        old = (Path(frozen["directory"]) / "SPINE.md").read_text()
        independent = self.unit.store.get("U")
        self.record([self.n("C", "claim", statement="Corrected interpretation after actual recheck.", supports=[["O"]])], {"C": 1, "O": 1})
        current = (self.workspace / "current/SPINE.md").read_text()
        self.assertIn("Corrected interpretation", current)
        self.assertNotIn("Old proposed test.", current)
        self.assertIn("Reassessment needed", current)
        self.record([self.n("R", "route", statement="Only the narrowed route remains open.", requires=["C"], action="Perform the newly justified test.")], {"R": 1, "C": 2})
        current = (self.workspace / "current/SPINE.md").read_text()
        self.assertIn("newly justified test", current)
        self.assertNotIn("Reassessment needed", current)
        self.assertEqual(self.unit.store.get("U"), independent)
        self.assertEqual((Path(frozen["directory"]) / "SPINE.md").read_text(), old)
        self.assertEqual(len(self.unit.store.history("C")), 2)

    def test_direct_record_checks_inspected_revisions_and_actual_bytes(self):
        self.record([self.n("O")])
        with self.assertRaises(ConflictError):
            self.record([self.n("O", statement="A changed interpretation")])
        original = self.unit.read("mixed.md")["artifact"]["data"]["sha256"]
        (self.source / "mixed.md").write_text("Different input\n")
        with self.assertRaises(ConflictError):
            self.record([self.n("O")], {"O": 1}, materials=[{"key": "obs", "path": "mixed.md", "role": "evidence", "sha256": original}])

    def test_additional_real_evidence_source_preserves_science_and_resumes(self):
        self.record([self.n("O")])
        old = self.unit.store.get("O")
        extra = self.root / "later-evidence"; extra.mkdir()
        (extra / "mixed.md").write_text("A later observation in a distinct source.\n")
        response = invoke({"name": "retro_add_source", "arguments": {"workspace": str(self.workspace), "path": str(extra)}})
        self.assertTrue(response["ok"], response)
        unit = Unit(self.workspace)
        self.assertEqual(unit.store.get("O"), old)
        self.assertEqual(len(unit.manifest["sources"]), 2)
        self.assertTrue(unit.add_source(extra)["already_in_scope"])
        self.assertTrue(start(self.source, self.workspace)["resumed"])
        self.assertIn("later observation", unit.read(str(extra / "mixed.md"))["text"])
        from research_harness.recovery.snapshot import freeze
        snapshot = freeze(unit)
        self.assertEqual(len(snapshot["data"]["coverage"]), 2)
        self.assertEqual(unit.store.get("O"), old)

    def test_discovery_keeps_findings_and_deduplicates_only_captured_bytes(self):
        shutil.copyfile(self.source / "other.txt", self.source / "copy.txt")
        self.unit.read("other.txt"); self.unit.read("copy.txt"); self.w.refresh()
        queue = self.w.discover()["unlinked_queue"]["candidates"]
        duplicates = [c for c in queue if c.get("identical_byte_paths")]
        self.assertEqual(len(duplicates), 1)
        self.record([self.n("missing", "gap", statement="A previously omitted comparison matters.", status="open",
                           details={"discovery": {"finding": "An old result is outside the latest story.", "next_check": "Compare the original conditions."}})])
        self.assertEqual(self.w.discover()["scientific_candidates"][0]["id"], "missing")
        self.assertTrue(self.w.discover()["families"])

    def test_portable_host_checks_are_distinct_from_originals(self):
        checks = self.workspace / "checks"; checks.mkdir()
        (checks / "recompute.py").write_text("print(2 + 2)\n")
        (checks / "result.txt").write_text("4\n")
        self.record([self.n("O")], checks=["checks/recompute.py", "checks/result.txt"])
        self.w.spine({"sections": [{"title": "Result", "nodes": ["O"]}]})
        bundle = Path(self.unit.export()["bundle"])
        shutil.rmtree(self.source); shutil.rmtree(checks)
        self.assertTrue(inspect_bundle(bundle)["verification"]["ok"])
        state = json.loads((bundle / "SCIENTIFIC_STATE.json").read_text())
        attachments = state["nodes"][0]["data"]["review"]["checks"]
        self.assertEqual((bundle / "store/blobs" / attachments[1]["sha256"]).read_text(), "4\n")
        self.assertIn("SPINE.md", (bundle / "START_HERE.md").read_text())
        self.assertIn("host-reported", attachments[0]["authority"])

    def test_same_path_check_versions_have_unambiguous_scientific_bindings(self):
        check = self.workspace / "check.txt"; check.write_text("old result\n")
        self.record([self.n("old")], checks=["check.txt"])
        check.write_text("revised result\n")
        self.record([self.n("new")], checks=["check.txt"])
        bundle = Path(self.unit.export()["bundle"])
        index = json.loads((bundle / "SOURCE_INDEX.json").read_text())
        entries = index["sources"][str(check)]
        self.assertEqual(len(entries), 2)
        for identifier, expected in [("old", "old result\n"), ("new", "revised result\n")]:
            entry = next(e for e in entries if e["used_by"][0]["id"] == identifier)
            self.assertEqual(entry["used_by"][0]["revision"], 1)
            self.assertTrue(entry["used_by"][0]["captured_at"])
            self.assertEqual((bundle / entry["blob"]).read_text(), expected)
        compact = invoke({"name": "retro_inspect", "arguments": {"bundle": str(bundle), "full": False}})
        self.assertTrue(compact["ok"], compact)
        self.assertNotIn("handoff", compact["result"])
        self.assertLess(len(json.dumps(compact)), 1500)
        self.assertIn("handoff", invoke({"name": "retro_inspect", "arguments": {"bundle": str(bundle)}})["result"])

    def test_generic_judgment_uses_public_dispatch_and_is_never_automatic(self):
        self.record([self.n("O")])
        before = self.unit.store.get("O")
        request = {"name": "retro_judge", "arguments": {"workspace": str(self.workspace), "document": {
            "purpose": "Local relevance of two source-backed candidates", "state": {"a": "candidate", "b": "candidate"},
            "questions": {"a": {"type": "noul", "instructions": "Is a relevant?"}, "b": {"type": "noul", "instructions": "Is b relevant?"}}}}}
        self.assertEqual(invoke(request)["error"]["code"], "permission_denied")
        result = {"model": "jev-test", "usage": {"input_tokens": 15, "output_tokens": 5},
                  "answers": {"a": {"type": "noul", "noul": .8}, "b": {"type": "noul", "noul": .2}}}
        opener = semantic_fixtures.SemanticWorkflowTests.live_boundary(self, result)
        request["arguments"]["document"]["authorize_egress"] = True
        response = invoke(request)
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["result"]["response"], result)
        self.w.refresh(); self.w.publish()
        self.assertEqual(opener.return_value.open.call_count, 1)
        self.assertEqual(self.unit.store.get("O"), before)

    def test_known_rationale_and_action_correction_requires_actual_downstream_update(self):
        # The two historical 3.5 defects remain a regression, not the core model.
        self.record([self.n("O", statement="The local result has arrived and been checked."),
            self.n("C", "claim", statement="The local result was checked; global connection is unknown.",
                   rationale="The local result is still unavailable.", requires=["O"], supports=[["O"]]),
            self.n("R", "route", requires=["C"], action="Wait for the local result.")])
        self.w.spine({"sections": [{"title": "Current knowledge", "nodes": ["C", "R"]}]})
        self.w.publish()
        self.record([self.n("C", "claim", statement="Local result is established; global connection remains unknown.",
                           rationale="The local result is available and verified, but does not establish the global connection.",
                           requires=["O"], supports=[["O"]])], {"C": 1, "O": 1})
        self.assertTrue(self.w.show("R")["node"]["current"]["needs_review"])
        self.assertNotIn("Wait for the local result", (self.workspace / "current/SPINE.md").read_text())
        semantic_fixtures.SemanticWorkflowTests.live_boundary(self, semantic_fixtures.response())
        self.w.semantic_review({"authorize_egress": True, "nodes": ["R"]})
        self.assertTrue(self.w.show("R")["node"]["current"]["needs_review"])
        self.record([self.n("R", "route", requires=["C"], statement="Investigate the missing global connection.",
                           action="Test the global connection using the retained local result.")], {"R": 1, "C": 2})
        self.assertFalse(self.w.show("R")["node"]["current"]["needs_review"])
        self.assertIn("Test the global connection", (self.workspace / "current/SPINE.md").read_text())
