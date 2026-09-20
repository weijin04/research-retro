"""Upstream local judgments change reading inputs, never certify scientific state."""
import io
import json
from pathlib import Path
import shutil
import shlex
import sys
import unittest
from unittest.mock import patch

from research_harness.agent_tools import invoke
from research_harness.triage import Triage
from research_harness.unit import inspect_bundle
import test_workflow as fixtures


class TriageTests(unittest.TestCase):
    setUp = fixtures.WorkflowTest.setUp
    n = fixtures.WorkflowTest.n

    def packet(self):
        return Triage(self.unit).prepare({"materials": [{"path": "mixed.md"}]})

    def candidate(self, id="c1"):
        return {"id": id, "kind": "support", "title": "Finite observation versus universal absence",
                "evidence": [{"material": "m1", "quote": "time=4 seconds\n0 events"}],
                "target": {"text": "The physical rate is exactly zero", "material": "m1",
                           "quote": "old conclusion: rate is zero"},
                "next_check": "Check the sampling model and physical operator."}

    def provider(self, failure=False):
        def response(req, **kwargs):
            if failure:
                raise OSError("synthetic transport failure")
            body = json.loads(req.data)
            criteria = body["questions"]["relation"]["criteria"]
            choice = next((k for k in ("counters", "affected", "insufficient") if k in criteria))
            result = {"model": "jev-test", "usage": {"input_tokens": 120, "output_tokens": 20},
                      "answers": {"relation": {"type": "choice", "choice": choice, "confidence": .2,
                          "probabilities": {k: .6 if k == choice else .4/(len(criteria)-1) for k in criteria}}}}
            stream = io.BytesIO(json.dumps(result).encode()); stream.status = 200
            return stream
        mock = patch("research_harness.semantic.request.build_opener").start()
        self.addCleanup(patch.stopall)
        mock.return_value.open.side_effect = response
        patch.dict("os.environ", {"TYPESAFE_API_KEY": "synthetic-key"}).start()
        return mock.return_value.open

    def test_candidates_are_judged_before_science_and_invalid_quotes_remain_visible(self):
        packet = self.packet(); t = Triage(self.unit)
        bad = self.candidate("fabricated"); bad["evidence"][0]["quote"] = "invented original text"
        calls = self.provider()
        result = t.judge({"packet": packet["packet"], "candidates": [self.candidate(), bad], "authorize_egress": True})
        self.assertEqual((result["jev_calls"], result["successful"], len(result["invalid_candidates"])), (1, 1, 1))
        self.assertEqual(self.w.status()["nodes"], 0)
        queue = t.run("queue")
        self.assertEqual(queue["items"][0]["answer"]["choice"], "counters")
        self.assertEqual(queue["items"][0]["status"], "ok")  # confidence does not block anything
        request = json.loads(calls.call_args.args[0].data)
        self.assertIn("time=4 seconds", request["state"]["evidence"][0]["context"])
        batch = self.unit.store.get(result["batch"])["data"]
        self.assertEqual(len(json.loads(self.unit.store.read_blob(batch["proposals_blob"]))["candidates"]), 2)
        self.assertNotIn("synthetic-key", json.dumps(batch))

    def test_unchanged_inputs_reuse_receipt_but_changed_source_does_not(self):
        packet = self.packet(); t = Triage(self.unit); calls = self.provider()
        doc = {"packet": packet["packet"], "candidates": [self.candidate()], "authorize_egress": True}
        first = t.judge(doc); second = t.judge(doc)
        self.assertEqual(second["jev_calls"], 0)
        self.assertEqual(second["cached"], first["receipts"])
        self.assertEqual(calls.call_count, 1)
        (self.source / "mixed.md").write_text("The observation changed.\n")
        self.unit.ingest.capture(self.source / "mixed.md")
        self.assertTrue(t.run("queue")["items"][0]["stale_inputs"])
        failed = t.judge(doc)
        self.assertEqual(failed["jev_calls"], 0)
        self.assertTrue(failed["invalid_candidates"])

    def test_impact_checks_undeclared_relations_without_changing_nodes(self):
        self.w.record({"question": "Initial scoped understanding", "reviewer": "test host", "analysis": "Synthetic initial state.",
                       "materials": [{"key": "obs", "path": "mixed.md", "role": "evidence"}],
                       "nodes": [self.n("O"), self.n("C", "claim"), self.n("R", "route")]})
        before = self.unit.store.list("research_node")
        self.provider()
        result = Triage(self.unit).impact({"materials": [{"path": "other.txt"}, {"path": "mixed.md"}], "authorize_egress": True})
        self.assertEqual(result["candidates"], 4)
        self.assertEqual(result["successful"], 4)
        self.assertEqual(self.unit.store.list("research_node"), before)
        targets = {i["target"]["node"] for i in Triage(self.unit).run("queue")["items"]}
        self.assertEqual(targets, {"C", "R"})

    def test_local_context_marks_omissions_and_keeps_selected_action(self):
        (self.source / "long.txt").write_text("prefix " * 200 + "actual observation" + " suffix" * 200)
        self.w.record({"question": "Initial understanding", "reviewer": "test host", "analysis": "Synthetic state.",
                       "materials": [{"key": "obs", "path": "mixed.md", "role": "evidence"}],
                       "nodes": [self.n("C", "claim", details={"next": "Check the calibration"})]})
        t = Triage(self.unit)
        packet = t.prepare({"materials": [{"path": "long.txt"}]})
        calls = self.provider()
        candidate = {"id": "action", "kind": "action", "title": "Calibration still needed?",
                     "evidence": [{"material": "m1", "quote": "actual observation"}],
                     "target": {"node": "C", "text": "Check the calibration"}}
        t.judge({"packet": packet["packet"], "candidates": [candidate], "authorize_egress": True})
        state = json.loads(calls.call_args.args[0].data)["state"]
        self.assertEqual(state["target"]["text"], "Check the calibration")
        self.assertEqual(state["target"]["node"]["statement"], "C")
        evidence = state["evidence"][0]
        self.assertFalse(evidence["partial"])
        self.assertTrue(evidence["context_truncated"])
        self.assertEqual(evidence["context_chars"], [800, 2018])

    def test_record_binds_investigation_to_queue_and_exports_it(self):
        packet = self.packet(); self.provider()
        result = Triage(self.unit).judge({"packet": packet["packet"], "candidates": [self.candidate()], "authorize_egress": True})
        self.w.record({"question": "What does the count establish?", "reviewer": "test host",
                       "analysis": "Derived the finite-observation likelihood; positive rates remain compatible.",
                       "materials": [{"key": "obs", "path": "mixed.md", "role": "evidence"}],
                       "nodes": [self.n("O")], "triage_receipts": result["receipts"]})
        self.assertTrue(Triage(self.unit).run("queue")["items"][0]["investigated"])
        bundle = Path(self.unit.export()["bundle"])
        shutil.rmtree(self.source)
        self.assertTrue(inspect_bundle(bundle, full=False)["verification"]["ok"])
        q = json.loads((bundle / "DISCOVERY_QUEUE.json").read_text())
        self.assertEqual(q["items"][0]["receipt"], result["receipts"][0])
        source = q["items"][0]["sources"][0]
        self.assertIn(b"0 events", (bundle / "store/blobs" / source["sha256"]).read_bytes())

    def test_generate_is_a_real_host_neutral_stdin_stdout_process(self):
        packet = self.packet()
        code = 'import sys,json; p=json.load(sys.stdin); print(json.dumps({"packet":p["id"],"generator":{"name":"test parser"},"candidates":[]}))'
        request = {"name": "retro_triage", "arguments": {"workspace": str(self.workspace), "action": "generate",
                   "document": {"packet": packet["packet"], "command": [sys.executable, "-c", code]}}}
        result = invoke(request)
        self.assertTrue(result["ok"], result)
        self.assertEqual(json.loads(Path(result["result"]["input"]).read_text())["packet"], packet["packet"])
        self.assertEqual(self.w.status()["jev_calls"], 0)

    def test_service_failure_is_a_retained_candidate_not_false_evidence(self):
        packet = self.packet(); self.provider(failure=True)
        result = Triage(self.unit).judge({"packet": packet["packet"], "candidates": [self.candidate()], "authorize_egress": True})
        self.assertEqual(result["successful"], 0)
        self.assertEqual(len(result["failed"]), 1)
        item = Triage(self.unit).run("queue")["items"][0]
        self.assertEqual(item["status"], "error")
        self.assertEqual(item["answer"], {})
        self.assertEqual(self.w.status()["nodes"], 0)

    def discovery_worker(self):
        script = self.workspace / "candidate_worker.py"
        script.write_text('''import json,sys
p=json.load(sys.stdin); m=p["materials"][0]
print(json.dumps({"packet":p["id"],"generator":{"name":"test parser"},"candidates":[{
"id":"candidate","kind":"support","title":"Original versus proposed inference",
"evidence":[{"material":m["key"],"quote":m["text"]}],
"target":{"text":"The rate is zero"},"next_check":"Check the observation conditions"}]}))
''')
        return shlex.join([sys.executable, str(script)])

    def test_everyday_discovery_continues_and_keeps_unjudged_candidates_portable(self):
        worker = self.discovery_worker()
        started = invoke({"name": "retro_start", "arguments": {"project": str(self.source),
                          "workspace": str(self.workspace), "worker": worker}})
        self.assertTrue(started["ok"], started)
        request = {"name": "retro_discover", "arguments": {"workspace": str(self.workspace), "limit": 1}}
        with patch("research_harness.semantic.evaluate", side_effect=AssertionError("No Jev permission")):
            first = invoke(request); second = invoke(request); end = invoke(request)
        self.assertEqual((first["result"]["offset"], second["result"]["offset"]), (0, 1))
        self.assertTrue(end["result"]["material_pass_exhausted"])
        self.assertFalse(end["result"]["scientific_reconstruction_complete"])
        self.assertEqual(first["result"]["candidates"][0]["status"], "not_requested")
        self.assertIn("Original versus proposed inference", (self.workspace / "discovery/latest.md").read_text())
        bundle = Path(self.unit.export()["bundle"])
        queue = json.loads((bundle / "DISCOVERY_QUEUE.json").read_text())
        self.assertEqual(queue["total"], 2)
        self.assertEqual(self.w.status()["nodes"], 0)

    def test_everyday_discovery_uses_authorized_judgments_and_overview_is_quiet(self):
        self.provider()
        worker = self.discovery_worker()
        self.w._enable_jev(local=True)
        request = {"name": "retro_discover", "arguments": {"workspace": str(self.workspace),
                   "worker": worker, "query": "mixed.md"}}
        result = invoke(request)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["result"]["judgments"]["jev_calls"], 1)
        before = self.w.status()["jev_calls"]
        request["arguments"]["overview"] = True
        self.assertTrue(invoke(request)["ok"])
        self.assertEqual(self.w.status()["jev_calls"], before)
