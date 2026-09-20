"""Offline behavioral regressions. HTTP here is mocked; real r655 runs separately."""
import copy
import io
import json
import unittest
from unittest.mock import patch

from research_harness import semantic
from research_harness.workflow import projection
from research_harness.agent_tools import invoke
from research_harness.config import load
from research_harness.common import atomic_json
from research_harness.unit import Unit
import test_workflow as fixtures


def response(premise="consistent", action="consistent"):
    return {"model": "jev-test", "usage": {"input_tokens": 10, "output_tokens": 5},
            "answers": {key: {"type": "choice", "choice": choice, "confidence": 1,
                "probabilities": {c: int(c == choice) for c in ("stale", "consistent", "uncertain")}}
                for key, choice in (("premise_validity", premise), ("action_cleanup", action))}}


class SemanticWorkflowTests(unittest.TestCase):
    # Reuse setup helpers, without rerunning the inherited test methods.
    setUp = fixtures.WorkflowTest.setUp
    packet = fixtures.WorkflowTest.packet
    submit = fixtures.WorkflowTest.submit
    n = fixtures.WorkflowTest.n

    def test_explicit_governance_revision_loads_without_rewriting_history(self):
        before = self.unit.store.get("project:contract")
        config_path = self.workspace / "retro.json"
        config = json.loads(config_path.read_text())
        config["policy_revision"] = 2
        atomic_json(config_path, config)
        self.unit.store.governance_update(load(self.workspace), 1, "explicit test governance revision")
        reopened = Unit(self.workspace)
        self.assertEqual(reopened.store.active_policy_revision(), 2)
        self.assertEqual(reopened.store.get("project:contract", 1), before)

    def live_boundary(self, result):
        stream = io.BytesIO(json.dumps(result).encode())
        stream.status = 200
        mocked = patch("research_harness.semantic.request.build_opener")
        opener = mocked.start()
        self.addCleanup(mocked.stop)
        opener.return_value.open.return_value = stream
        key = patch.dict("os.environ", {"TYPESAFE_API_KEY": "synthetic-test-key"})
        key.start()
        self.addCleanup(key.stop)
        return opener

    def pair(self):
        self.submit([self.n("obs", statement="The local vibration calculation has completed and been read."),
                     self.n("claim", "claim", statement="The local vibration calculation was reviewed.",
                            rationale="The local vibration output is still unavailable.", requires=["obs"], supports=[["obs"]]),
                     self.n("route", "route", requires=["claim"], details={"next": "Wait for the running local frequency calculation."})])

    def test_no_model_verdict_does_not_revoke_host_scientific_support(self):
        self.pair()
        nodes = projection(self.unit.store.list())
        self.assertFalse(nodes["claim"]["current"]["needs_review"])
        self.assertTrue(nodes["claim"]["current"]["usable_positive"])
        self.assertFalse(nodes["route"]["current"]["needs_review"])
        self.assertEqual(nodes["claim"]["data"]["requires"][0]["revision"], nodes["obs"]["revision"])
        self.assertEqual(self.w.status()["jev_calls"], 0)

    def test_real_response_path_records_both_field_verdicts(self):
        self.pair()
        opener = self.live_boundary(response("stale", "consistent"))
        result = self.w.semantic_review({"authorize_egress": True, "nodes": ["claim"]})
        self.assertEqual(opener.return_value.open.call_count, 1)
        receipt = result["receipts"][0]
        self.assertEqual(set(receipt["request"]["questions"]), {"premise_validity", "action_cleanup"})
        self.assertEqual(receipt["response"]["model"], "jev-test")
        self.assertIn("semantic:rationale:stale", self.w.show("claim")["node"]["current"]["semantic_review"]["reasons"])
        self.assertEqual(self.unit.store.get(receipt["id"])["data"], receipt)
        self.assertEqual(len(list((self.workspace / "jev").glob("*.json"))), 1)
        self.assertNotIn("synthetic-test-key", (next((self.workspace / "jev").glob("*.json"))).read_text())

    def test_apply_does_not_call_jev_until_explicitly_requested(self):
        self.submit([self.n("A")])
        self.w._enable_jev(local=True)
        opener = self.live_boundary(response(action="stale"))
        result = self.submit([self.n("A", statement="Result is now available and read.", action="Wait for this result.")], focus=["A"])
        self.assertEqual(opener.return_value.open.call_count, 0)
        self.w.semantic_review({"nodes": ["A"]})
        self.assertEqual(result["semantic_checks"]["jev_calls"], 0)
        node = self.w.show("A")["node"]
        self.assertEqual(node["data"]["action"], "Wait for this result.")
        self.assertIn("semantic:actions:stale", node["current"]["semantic_review"]["reasons"])

    def test_field_or_required_evidence_change_invalidates_consistent_receipt(self):
        self.pair()
        self.live_boundary(response())
        self.w.semantic_review({"authorize_egress": True, "nodes": ["claim"]})
        records = self.unit.store.list()
        self.assertFalse(projection(records)["claim"]["current"]["needs_review"])
        for target, field in (("claim", "rationale"), ("obs", "statement")):
            changed = copy.deepcopy(records)
            next(r for r in changed if r["id"] == target)["data"][field] = "Changed actual content at the same revision"
            self.assertIsNone(projection(changed)["claim"]["current"]["semantic_review"]["receipt"])
            self.assertTrue(projection(changed)["claim"]["current"]["usable_positive"])

    def test_narrow_jev_input_preserves_scope_without_sending_numeric_matrices(self):
        self.pair()
        records = {r["id"]: r for r in self.unit.store.list()}
        records["obs"]["data"]["details"] = {"matrix": list(range(100000)), "constraints": "local active space", "remaining": "full-space connection unknown"}
        state = semantic.state_for(records["claim"], records)
        self.assertLess(len(json.dumps(state)), 10000)
        self.assertEqual(state["evidence"][0]["details"]["constraints"], "local active space")
        fingerprint = semantic.input_hash(state)
        records["obs"]["data"]["details"]["matrix"][0] = 123
        self.assertNotEqual(fingerprint, semantic.input_hash(semantic.state_for(records["claim"], records)))

    def test_uncertain_judgment_and_service_failure_are_advisory(self):
        self.pair()
        self.live_boundary(response("uncertain"))
        self.w.semantic_review({"authorize_egress": True, "nodes": ["claim"]})
        self.assertFalse(self.w.show("claim")["node"]["current"]["needs_review"])
        with patch.dict("os.environ", {"TYPESAFE_API_KEY": ""}):
            result = self.w.semantic_review({"nodes": ["route"]})
        self.assertEqual(result["jev_calls"], 0)
        self.assertEqual(result["receipts"][0]["status"], "error")
        self.assertFalse(self.w.show("route")["node"]["current"]["needs_review"])

    def test_unvalidated_probability_threshold_is_not_a_product_gate(self):
        result = response()
        result["answers"]["premise_validity"]["probabilities"] = {"consistent": .79, "stale": .21, "uncertain": 0}
        self.assertEqual(semantic.findings({"status": "ok", "response": result}), [])
        self.assertEqual(result["answers"]["premise_validity"]["probabilities"]["consistent"], .79)

    def test_discovery_is_independent_and_never_injected_into_focused_context(self):
        self.submit([self.n("O"), self.n("C", "claim", sources=[], supports=[["O"]])])
        for n in range(9):
            directory = self.source / ("branch-" + str(n))
            directory.mkdir()
            (directory / "result.hess").write_text("unclaimed higher order result\n")
        failed = self.source / "failed.log"
        failed.write_text("MPI_Abort was invoked\n")
        self.unit.ingest.capture(failed)
        self.w.refresh()
        result = invoke({"name": "retro_discover", "arguments": {"workspace": str(self.workspace), "query": "no-matches"}})
        self.assertTrue(result["ok"])
        discovery = result["result"]
        self.assertEqual(discovery["candidates"], [])
        queue = discovery["unlinked_queue"]["candidates"]
        self.assertNotIn("mixed.md", [c["path"] for c in queue])
        self.assertIn("abnormal_exit_hint", next(c for c in queue if c["path"] == "failed.log")["signals"])
        first = self.packet()
        second = self.packet()
        self.assertEqual(first["unlinked_candidates"], [])
        self.assertFalse(any(m.get("mandatory_unlinked") for m in first["materials"]))
        self.assertEqual(first["read_set"], second["read_set"])

    def test_binary_candidate_remains_visible_without_decoding(self):
        (self.source / "isolated.npz").write_bytes(b"\x00\xff\x00")
        self.w.refresh()
        p = self.packet()
        candidate = next(c for c in self.w.discover()["unlinked_queue"]["candidates"] if c["path"] == "isolated.npz")
        self.assertEqual(candidate["size"], 3)
        self.assertEqual(p["unlinked_candidates"], [])
