"""Behavioral regression for the host reconstruction and correction loop."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from research_harness.unit import Unit, init, start, inspect_bundle
from research_harness.workflow import Workflow
from research_harness.storage import ConflictError


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "original"
        self.source.mkdir()
        (self.source / "mixed.md").write_text("time=4 seconds\n0 events\nold conclusion: rate is zero\n")
        (self.source / "other.txt").write_text("unrelated work\n")
        self.workspace = self.root / "separate-retro"
        init(self.source, self.workspace, capture_text=False)
        self.unit = Unit(self.workspace)
        self.w = Workflow(self.unit)
        self.w.start("Recover what the transport attempt establishes")

    def packet(self, focus=(), materials=None):
        p = self.w.context({"question": "What does the original establish?", "focus": list(focus), "materials": materials or [
            {"key": "conditions", "path": "mixed.md", "role": "definition", "start": 1, "end": 1},
            {"key": "obs", "path": "mixed.md", "role": "evidence", "start": 2, "end": 2},
            {"key": "old", "path": "mixed.md", "role": "history", "start": 3, "end": 3}]})
        return p

    def submit(self, nodes, focus=()):
        p = self.packet(focus)
        self.w.seal(p["id"], {"analysis": "Finite positive rates also permit zero counts; original operator/detection assumptions remain explicit.",
                                "alternatives": ["zero rate", "positive rate with zero realized events"]})
        self.w.reveal(p["id"])
        return self.w.apply({"context": p["id"], "input_hash": p["input_hash"], "reviewer": "test host (synthetic)",
                            "analysis": "synthetic behavioral construction, not a scientific benchmark", "nodes": nodes})

    def n(self, id, type="observation", **kw):
        return {"id": id, "type": type, "title": id, "statement": id, "status": "observed" if type == "observation" else "conditional",
                "scope": {"test": "toy"}, "rationale": "synthetic record", "sources": ["obs"], **kw}

    def test_definitions_early_history_after_seal_related_reads_only(self):
        p = self.packet()
        self.assertEqual([m["role"] for m in p["materials"] if not m.get("mandatory_unlinked")], ["definition", "evidence"])
        self.assertEqual(len(p["read_set"]), 2)  # contract and selected file only
        self.assertEqual(p["unlinked_candidates"], [])
        (self.source / "not-in-this-context.txt").write_text("new unrelated evidence\n")
        sealed = self.w.seal(p["id"], {"analysis": "derived initial reading", "alternatives": ["another interpretation"]})
        self.assertEqual(sealed["hidden_history_spans"], 1)
        self.assertEqual(len(self.w.reveal(p["id"])["materials"]), 3)
        (self.source / "mixed.md").write_text("changed selected conditions\n")
        with self.assertRaises(ConflictError):
            self.w.apply({"context": p["id"]})

    def test_single_entry_resumes_existing_scientific_state(self):
        self.submit([self.n("original-observation")])
        before = self.unit.store.current_revision()
        result = start(self.source, self.workspace)
        self.assertEqual(result["state"]["state_revision"], before)
        self.assertTrue(result["resumed"])
        self.assertTrue(Path(result["entry"]).is_file())
        self.assertTrue((self.workspace / "host/references/protocol.md").is_file())
        self.assertEqual(sorted(p.name for p in self.source.iterdir()), ["mixed.md", "other.txt"])
        with self.assertRaises(ConflictError):
            start(self.source, self.workspace, "silently replace the scope")

    def test_readable_mainline_keeps_large_detail_in_linked_state(self):
        self.submit([self.n("A", details={"large_table": list(range(3000))})])
        self.w.spine({"sections": [{"title": "Result", "nodes": ["A"]}]})
        self.w.publish()
        mainline = (self.workspace / "current/MAINLINE.md").read_text()
        state = json.loads((self.workspace / "current/SCIENTIFIC_STATE.json").read_text())
        self.assertLess(len(mainline.splitlines()), 100)
        self.assertIn("index.html#A", mainline)
        self.assertEqual(len(state["nodes"][0]["data"]["details"]["large_table"]), 3000)

    def test_independent_byte_segments_in_one_context(self):
        p = self.packet(materials=[
            {"key": "a", "path": "mixed.md", "bytes": [0, 15], "role": "definition"},
            {"key": "b", "path": "mixed.md", "bytes": [15, 24], "role": "evidence"}])
        self.assertEqual(len(p["read_set"]), 3)
        self.assertEqual(p["partial_sources"][1]["captured_bytes"], [15, 24])
        self.assertGreater(p["partial_sources"][1]["original_size_bytes"], 24)
        self.w.seal(p["id"], {"analysis": "two original ranges", "alternatives": ["full file contains more context"]})

    def test_withdrawal_preserves_or_then_propagates_to_required_interpretation(self):
        self.submit([self.n("A"), self.n("B"), self.n("D"), self.n("U"),
                     self.n("C", "claim", sources=[], supports=[["A", "B"], ["D"]]),
                     self.n("route", "route", sources=[], requires=["C"])])
        unrelated = self.unit.store.get("U")
        self.submit([self.n("A", status="withdrawn")], focus=["A"])
        view = {r["id"]: r for r in self.w.view()["nodes"]}
        self.assertTrue(view["C"]["current"]["usable_positive"])
        self.assertFalse(view["route"]["current"]["needs_review"])
        self.submit([self.n("D", status="withdrawn")], focus=["D"])
        view = {r["id"]: r for r in self.w.view()["nodes"]}
        self.assertFalse(view["C"]["current"]["usable_positive"])
        self.assertTrue(view["route"]["current"]["needs_review"])
        self.assertEqual(unrelated, self.unit.store.get("U"))

    def test_conflict_and_self_support_never_affirm(self):
        self.submit([self.n("A"), self.n("B"), self.n("C", "claim", supports=[["A"]], counters=[["B"]]),
                     self.n("cycle", "claim", supports=[["cycle"]])])
        view = {r["id"]: r for r in self.w.view()["nodes"]}
        # counters are scientific dependencies, not a textual disagreement marker.
        self.assertEqual(view["C"]["current"]["status"], "conflict")
        self.assertFalse(view["cycle"]["current"]["usable_positive"])

    def test_rejected_interpretation_cannot_retain_old_affirmative_support(self):
        self.submit([self.n("A"), self.n("C", "claim", supports=[["A"]], status="rejected"),
                     self.n("next", "claim", supports=[["C"]])])
        view = {r["id"]: r for r in self.w.view()["nodes"]}
        self.assertFalse(view["C"]["current"]["usable_positive"])
        self.assertTrue(view["next"]["current"]["needs_review"])

    def test_new_unlinked_original_reopens_coverage_but_rereading_does_not(self):
        self.submit([self.n("A")])
        self.w.assess({"reviewer": "synthetic", "coverage": {"sufficient": True, "basis": "known two-file fixture"},
                       "residual_review": {"samples": ["other.txt"]},
                       "handoff": {"passed": True, "tasks": ["synthetic"], "receipt": "synthetic"},
                       "limitations": [], "scientific_problem": "open", "continuation": "conditional"})
        self.assertEqual(self.w.refresh()["state"]["publication"]["status"], "reconstructed-qualified")
        (self.source / "omitted-counterexample.txt").write_text("A decisive original outside the old map\n")
        bundle = Path(self.unit.export()["bundle"])
        self.assertEqual(json.loads((bundle / "SCIENTIFIC_STATE.json").read_text())["completion"]["status"], "draft")
        self.assertEqual(self.w.refresh()["state"]["publication"]["status"], "draft")
        self.assertIn("omitted-counterexample.txt", [c["path"] for c in self.w.discover()["candidates"]])

    def test_correction_updates_current_views_and_stales_assessment(self):
        self.submit([self.n("A"), self.n("route", "route", requires=["A"])])
        self.w.assess({"reviewer": "synthetic test", "coverage": {"sufficient": True, "basis": "toy fixture"},
                       "residual_review": {"samples": [{"path": "other.txt", "finding": "unrelated"}]},
                       "handoff": {"passed": True, "tasks": ["synthetic task"], "receipt": "synthetic only"},
                       "limitations": ["not scientific validation"], "scientific_problem": "open", "continuation": "conditional"})
        frozen = self.w.publish()
        self.assertEqual(frozen["completion"]["status"], "reconstructed-qualified")
        self.assertNotIn("route", self.w.status()["needs_review"])
        self.submit([self.n("A", statement="revised identity")], focus=["A"])
        current = json.loads((self.workspace / "current/SCIENTIFIC_STATE.json").read_text())
        self.assertEqual(current["completion"]["status"], "draft")
        self.assertFalse(current["completion"]["assessment_current"])
        self.assertIsNone(current["completion"]["continuation"])
        self.assertTrue(next(n for n in current["nodes"] if n["id"] == "route")["current"]["needs_review"])
        old = json.loads((Path(frozen["directory"]) / "SCIENTIFIC_STATE.json").read_text())
        self.assertEqual(old["completion"]["status"], "reconstructed-qualified")
        with self.assertRaises(ConflictError):
            self.w.view(expect=old["state_revision"])

    def test_offline_export_preserves_originals_history_and_navigation(self):
        self.submit([self.n("A")])
        self.submit([self.n("A", statement="corrected")], focus=["A"])
        bundle = Path(self.unit.export()["bundle"])
        shutil.rmtree(self.source)
        self.assertTrue(inspect_bundle(bundle)["verification"]["ok"])
        state = json.loads((bundle / "SCIENTIFIC_STATE.json").read_text())
        self.assertEqual(state["nodes"][0]["revision"], 2)
        loc = state["nodes"][0]["data"]["source_locators"][0]
        self.assertIn("0 events", (bundle / "store/blobs" / loc["content_identity"]["digest"]).read_text())
        self.assertIn("store/blobs/" + loc["content_identity"]["digest"], (bundle / "NAVIGATION.md").read_text())
        self.assertFalse((self.source / ".retro").exists())
