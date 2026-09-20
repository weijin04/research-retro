"""Adversarial temporary-data checks; no scientific source originals touched."""
import contextlib
import io
import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from research_harness.storage import Store
from research_harness.common import HarnessError, digest, upsert
from research_harness.ingest import Ingestor
from research_cases.legacy import audit
from research_cases.legacy.audit import integrate_case, revoke
from research_harness.reconstruction.workbench import AuditWorkbench
from research_harness.context import build_context
from research_cases.legacy import cli


class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.source_root = self.root / "sources"
        self.source_root.mkdir()
        self.source = self.source_root / "output.txt"
        self.source.write_text("energy 1.0\ncondition A\n")
        self.store = Store(self.project / "state")
        self.manifest = {"project_id": "test", "policy_revision": 1, "output_root": str(self.store.root),
                         "allowed_actions": ["read", "derive", "propose_revision"],
                         "sources": [{"id": "src", "root": str(self.source_root), "egress": "denied"}]}
        self.store.initialize_project(self.manifest)
        self.ingestor = Ingestor(self.store, self.manifest)
        self.case = {"id": "audit:test", "source_files": [{"path": str(self.source), "sha256": digest(self.source.read_bytes()), "role": "output"}],
                     "verdict": "endpoint is not barrier", "analysis": {"arithmetic": "2-1=1"}, "conditions": {"model": "synthetic"},
                     "suggested_state_records": [{"id": "claim:test", "kind": "claim", "text": "endpoint is insufficient to identify barrier", "evidence_status": "qualified"}],
                     "residual_unknowns": ["barrier unknown"]}
        self.case_path = self.project / "case.json"
        self.case_path.write_text(json.dumps(self.case))
        self.audit_root_patch = patch.object(audit, "ROOT", self.project)
        self.audit_root_patch.start()
        self.addCleanup(self.audit_root_patch.stop)
        self.execute_fixture()

    def execute_fixture(self):
        self.case["is_example"] = True
        self.case_path.write_text(json.dumps(self.case))
        script = self.project / "research_cases/test/check.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("import sys,json,hashlib\nfrom pathlib import Path\nb=Path(sys.argv[1]).read_bytes()\nx=float(b.decode().split()[1])\nPath(sys.argv[2]).write_text(json.dumps({'difference':2-x,'input_hash':hashlib.sha256(b).hexdigest()}))\n")
        output = self.project / "var/result.json"
        output.parent.mkdir(exist_ok=True)
        command = [sys.executable, str(script), str(self.source), str(output)]
        run = subprocess.run(command, capture_output=True, text=True, check=True)
        actual = json.loads(output.read_text())
        self.receipt = {"command": command, "script_sha256": digest(script.read_bytes()), "returncode": run.returncode,
                        "result_path": str(output), "result_sha256": digest(output.read_bytes()),
                        "result_identity_matches_case": actual["difference"] == 1.0,
                        "actual_input_hashes": {str(self.source): actual["input_hash"]},
                        "execution_record_path": str(output.parent / "execution.json"),
                        "case_sha256": digest(self.case_path.read_bytes()), "is_synthetic": True,
                        "stdout": run.stdout, "stderr": run.stderr}
        Path(self.receipt["execution_record_path"]).write_text(json.dumps(self.receipt))

    def integrate(self):
        return integrate_case(self.store, self.ingestor, self.case_path, self.receipt)

    def workbench(self):
        artifact = self.ingestor.capture(self.source)
        locator = self.ingestor.locator(artifact)
        upsert(self.store, [{"id": locator["id"], "kind": "source_locator", "data": locator}], "locator")
        case = {"schema_version": "0.1.0", "project_id": "test", "id": "generic", "is_example": True,
                "kind": "audit_case", "status": "ready", "historical_assertion": "barrier=endpoint", "research_question": "identifiable?",
                "scientific_scope": {}, "evidence_locator_ids": [locator["id"]], "competing_explanations": ["unknown transition state"],
                "analysis_obligations": ["derive non-identifiability"], "allowed_actions": ["read", "derive"],
                "read_set": [], "result_ref": None, "extensions": {}}
        bench = AuditWorkbench(self.store, self.ingestor)
        bench.propose(case)
        packet = bench.packet("generic")
        result = {"actual_read_set": packet["read_set"], "completed_analysis": "Two curves with equal endpoints can have different maxima.",
                  "competing_explanations": ["arbitrary intervening maximum"], "verdict": "unsupported", "scope": {},
                  "first_failing_condition": "no path", "residual_assets": ["endpoint"], "unresolved": ["barrier"],
                  "verification_receipts": [], "reviewer": "test reviewer", "policy_revision": packet["policy_revision"]}
        return bench, packet, result

    def test_change_and_delete_propagate_preserve_history(self):
        self.integrate()
        old = self.store.get("claim:test")
        self.assertEqual(old["data"]["support_status"], "supported")
        self.source.write_text("energy 2.0\ncondition B\n")
        self.ingestor.refresh()
        for identifier in ["audit:test:recomputation", "claim:test", "audit:test:inference", "audit:test"]:
            self.assertEqual(self.store.get(identifier)["data"]["support_status"], "unsupported")
        self.assertEqual(self.store.get("claim:test", old["revision"])["data"]["support_status"], "supported")
        self.assertEqual(self.ingestor.read(old["data"]["source_locators"][0]), "energy 1.0\ncondition A")
        self.source.unlink()
        self.ingestor.refresh()
        self.assertEqual(self.store.get("claim:test")["data"]["support_status"], "unsupported")

    def test_repeat_integration_preserves_revocation(self):
        self.integrate()
        revoke(self.store, "audit:test:recomputation", "do not rely")
        self.assertEqual(self.integrate()["status"], "already_integrated")
        self.assertTrue(self.store.get("audit:test:recomputation")["data"]["revoked"])
        self.assertEqual(self.store.get("claim:test")["data"]["support_status"], "unsupported")

    def test_case_change_during_capture_never_relabels_old_content(self):
        old_bytes = self.case_path.read_bytes()
        original_capture = self.ingestor.capture
        def change_case_after_initial_read(*args, **kwargs):
            self.case["conditions"]["model"] = "new synthetic condition"
            self.case_path.write_text(json.dumps(self.case))
            return original_capture(*args, **kwargs)
        with patch.object(self.ingestor, "capture", side_effect=change_case_after_initial_read):
            self.integrate()
        record = self.store.get("audit:test")
        self.assertEqual(record["data"]["conditions"]["model"], "synthetic")
        self.assertEqual(record["data"]["case_sha256"], digest(old_bytes))
        self.assertEqual(self.store.read_blob(record["data"]["case_sha256"]), old_bytes)
        self.execute_fixture()
        self.assertEqual(self.integrate()["status"], "integrated")
        self.assertEqual(self.store.get("audit:test")["data"]["conditions"]["model"], "new synthetic condition")

    def test_claim_and_negative_preserve_narrower_scopes(self):
        self.case["suggested_state_records"][0]["scope"] = {"coordinate": "sample one"}
        self.case["negative_knowledge"] = [{"proposition": "endpoint is barrier", "scope": "fixed endpoint only", "reopen_condition": "actual path"}]
        self.execute_fixture()
        self.integrate()
        self.assertEqual(self.store.get("claim:test")["data"]["scope"], {"coordinate": "sample one"})
        self.assertEqual(self.store.get("audit:test:negative:0")["data"]["scope"], "fixed endpoint only")

    def test_delete_without_prior_change_propagates(self):
        self.integrate()
        self.source.unlink()
        self.ingestor.refresh()
        for identifier in ["audit:test:recomputation", "claim:test", "audit:test:inference", "audit:test"]:
            self.assertEqual(self.store.get(identifier)["data"]["support_status"], "unsupported")

    def test_integrator_rejects_fabricated_receipt(self):
        with self.assertRaises(HarnessError):
            integrate_case(self.store, self.ingestor, self.case_path, {"result_identity_matches_case": True})

    def test_refuted_proposition_cannot_support_affirmative_inference(self):
        self.case["suggested_state_records"][0].update(text="endpoint proves barrier", evidence_status="refuted")
        self.execute_fixture()
        self.integrate()
        upsert(self.store, [{"id": "downstream", "kind": "claim", "data": {"text": "Barrier is known, so rate is known", "support_sets": [["claim:test"]]}}], "test downstream")
        self.assertEqual(self.store.get("downstream")["data"]["support_status"], "unsupported")

    def test_workbench_accepts_completed_pure_derivation(self):
        bench, packet, result = self.workbench()
        result["completed_analysis"] = {
            "domain": "continuous energy profiles on [0,1] with endpoints E(0)=0,E(1)=1",
            "construction": "E_a(t)=t+a*sin(pi*t), a>=0",
            "endpoint_check": "sin(0)=sin(pi)=0 so endpoints equal 0 and 1 for every a",
            "different_maxima": "a=0 has max 1; a=2 has E(1/2)=2.5, hence max at least 2.5",
            "conclusion": "Same endpoint energy difference 1 admits distinct activation maxima. Endpoint data do not identify a barrier.",
            "scope": "This counterexample is mathematical non-identifiability, not a computed physical pathway."}
        receipt = bench.submit("generic", result)
        self.assertIn("generic:result", receipt["changed_ids"])
        self.assertEqual(self.store.get("generic:result")["data"]["completed_analysis"], result["completed_analysis"])

    def test_workbench_rejects_omitted_material_read_set(self):
        bench, packet, result = self.workbench()
        result["actual_read_set"] = {"generic": packet["read_set"]["generic"]}
        with self.assertRaises((HarnessError, ValueError)):
            bench.submit("generic", result)

    def test_workbench_rejects_stale_policy_even_if_contract_omitted(self):
        bench, packet, result = self.workbench()
        result["actual_read_set"].pop("project:contract")
        contract = dict(self.manifest)
        contract.pop("policy_revision")
        self.store.governance_update(contract, 1, "restrict scope")
        with self.assertRaises((HarnessError, ValueError)):
            bench.submit("generic", result)

    def test_workbench_rejects_fabricated_receipt_record(self):
        bench, packet, result = self.workbench()
        upsert(self.store, [{"id": "fake:receipt", "kind": "verification_receipt", "data": {"returncode": 0}}], "fabricated test input")
        result["verification_receipts"] = ["fake:receipt"]
        with self.assertRaises((HarnessError, ValueError)):
            bench.submit("generic", result)

    def test_workbench_rejects_stale_material(self):
        bench, packet, result = self.workbench()
        self.source.write_text("changed\n")
        self.ingestor.refresh()
        with self.assertRaises((HarnessError, ValueError)):
            bench.submit("generic", result)

    def test_workbench_rejects_changed_locator_record(self):
        bench, packet, result = self.workbench()
        locator_id = packet["audit_case"]["data"]["evidence_locator_ids"][0]
        record = self.store.get(locator_id)
        record["data"]["locator"]["start"] = 2
        upsert(self.store, [record], "change source condition locator after researcher read")
        with self.assertRaises((HarnessError, ValueError)):
            bench.submit("generic", result)

    def test_cli_report_destination_must_stay_in_project(self):
        config = self.project / "config.json"
        config.write_text(json.dumps(self.manifest))
        outside = self.root / "outside-report"
        with patch.object(cli, "ROOT", self.project), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(["--project", str(config), "report", "--dest", str(outside)])
        self.assertEqual(code, 3)
        self.assertFalse(outside.exists())

    def test_cli_backup_destination_must_stay_in_project(self):
        config = self.project / "config.json"
        config.write_text(json.dumps(self.manifest))
        outside = self.root / "outside-backup"
        with patch.object(cli, "ROOT", self.project), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(["--project", str(config), "backup", str(outside)])
        self.assertEqual(code, 3)
        self.assertFalse(outside.exists())


if __name__ == "__main__":
    unittest.main()
