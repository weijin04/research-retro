#!/usr/bin/env python3
"""Real clone-only recovery/qualification acceptance; scientific sources are read-only."""
import hashlib
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from research_harness.storage import Store
from research_harness.common import atomic_json, digest
from research_cases.legacy.audit import revoke
from research_harness.context import build_context
from research_harness.views import export_report
from research_harness.ingest import Ingestor

CASE = "grephene-lmct-coordinate-and-energy-001"
CLAIMS = ["gph-c-gradient-normalized", "gph-c-gap-corrected", "gph-c-monotonic-refuted", CASE + ":negative:2"]


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def states(store):
    return {id: {"revision": (r := store.get(id))["revision"],
                 "support_status": r["data"].get("support_status"),
                 "adjudication_supported": r["data"].get("adjudication_supported"),
                 "evidence_status": r["data"].get("evidence_status")}
            for id in CLAIMS}


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    work = ROOT / "var/validation" / ("r2-" + stamp)
    work.mkdir(parents=True)
    receipt = {"schema_version": 1, "status": "running", "is_synthetic": False,
               "activity": "real cloned scientific-state qualification corrections; no source edits or scientific jobs",
               "command": [sys.executable, str(Path(__file__).resolve())], "script_sha256": file_hash(__file__),
               "started_at": datetime.now(timezone.utc).isoformat(), "work_root": str(work), "checks": []}
    def check(name, condition, details=None):
        receipt["checks"].append({"name": name, "passed": bool(condition), "details": details})
        if not condition:
            raise AssertionError(name)
    try:
        source = Store(ROOT / "var/projects/grephene")
        receipt["production_before"] = {"state_revision": source.current_revision(), "policy_revision": source.active_policy_revision(), "db_sha256": file_hash(source.db_path)}
        receipt["production_verify"] = source.verify()
        check("production_integrity", receipt["production_verify"]["ok"])
        baseline = work / "baseline"
        receipt["baseline_backup"] = source.backup(baseline)
        manifest = json.loads((baseline / "backup_manifest.json").read_text())
        manifest_matches = all(file_hash(baseline / path) == entry["sha256"] and (baseline / path).stat().st_size == entry["bytes"] for path, entry in manifest["files"].items())
        check("baseline_manifest_all_files_match", manifest_matches, {"files": len(manifest["files"]), "manifest_hash": manifest["manifest_hash"]})
        frozen = Store(baseline)
        receipt["clone_backup"] = frozen.backup(work / "clone")
        clone = Store(work / "clone")
        receipt["before_states"] = states(clone)
        check("baseline_gradient_and_gap_supported", all(receipt["before_states"][id]["support_status"] == "supported" for id in CLAIMS[:2]))
        check("baseline_monotonic_refutation_has_support", receipt["before_states"][CLAIMS[2]]["adjudication_supported"] is True and receipt["before_states"][CLAIMS[3]]["support_status"] == "supported")
        context_before = build_context(clone)
        atomic_json(work / "context_before.json", context_before)
        report_before = export_report(clone, work / "reports")
        receipt["report_before"] = report_before
        source_evidence = [r for r in clone.list("evidence") if r["data"].get("qualification") == "source_identity_verified_only"]
        def evidence_for(suffix):
            matches = [r for r in source_evidence if any(loc.get("uri", "").endswith(suffix) for loc in r["data"].get("source_locators", []))]
            if len(matches) != 1:
                raise AssertionError("expected one source evidence: " + suffix)
            return matches[0]
        gradient = evidence_for("fc_engrad_rootK/root1/orca.engrad")
        historical_locator = gradient["data"]["source_locators"][0]
        receipt["gradient_revocation"] = revoke(clone, gradient["id"], "R2 clone acceptance: temporarily withdraw root1 gradient qualification")
        receipt["after_gradient_states"] = states(clone)
        check("gradient_withdrawn", receipt["after_gradient_states"][CLAIMS[0]]["support_status"] == "unsupported")
        check("independent_endpoint_retained", receipt["after_gradient_states"][CLAIMS[1]]["support_status"] == "supported")
        check("independent_monotonic_adjudication_retained", receipt["after_gradient_states"][CLAIMS[2]]["adjudication_supported"] is True and receipt["after_gradient_states"][CLAIMS[3]]["support_status"] == "supported")
        check("old_view_stale_after_correction", clone.view_status("report")["stale"] == 1)
        context_after = build_context(clone)
        atomic_json(work / "context_after_gradient.json", context_after)
        item = next(i for i in context_after["items"] if i["id"] == CLAIMS[0])
        check("context_retains_withdrawn_claim_with_nonusable_status", item["mandatory"] and item["data"]["support_status"] == "unsupported")
        check("context_revision_and_hash_changed", context_before["content_hash"] != context_after["content_hash"] and context_before["state_revision"] != context_after["state_revision"])
        report_after = export_report(clone, work / "reports")
        receipt["report_after_gradient"] = report_after
        check("new_report_real_distinct_and_current", Path(report_after["html"]).is_file() and report_after["content_hash"] != report_before["content_hash"] and not clone.view_status("report")["stale"])
        receipt["p5_revocation"] = revoke(clone, evidence_for("tda_points/point005/orca.out")["id"], "R2 clone acceptance: withdraw p5-only witness source")
        receipt["after_p5_states"] = states(clone)
        check("first_witness_withdrawn", clone.get(CASE + ":check:monotonic_witness_5_6")["data"]["support_status"] == "unsupported")
        check("second_witness_preserved", clone.get(CASE + ":check:monotonic_witness_6_7")["data"]["support_status"] == "supported")
        check("OR_negative_knowledge_preserved", receipt["after_p5_states"][CLAIMS[3]]["support_status"] == "supported")
        receipt["p7_revocation"] = revoke(clone, evidence_for("tda_points/point007/orca.out")["id"], "R2 clone acceptance: withdraw remaining p7 witness source")
        receipt["after_p7_states"] = states(clone)
        check("both_witnesses_lost_negative_knowledge_withdrawn", receipt["after_p7_states"][CLAIMS[3]]["support_status"] == "unsupported")
        atomic_json(work / "context_after_p7.json", build_context(clone))
        receipt["report_after_p7"] = export_report(clone, work / "reports")
        receipt["clone_final_verify"] = clone.verify()
        check("corrected_clone_integrity", receipt["clone_final_verify"]["ok"])
        receipt["restore_backup"] = frozen.backup(work / "restored")
        restored = Store(work / "restored")
        receipt["restored_verify"] = restored.verify()
        receipt["restored_states"] = states(restored)
        check("restored_original_qualifications", receipt["restored_states"] == receipt["before_states"])
        check("restored_integrity", receipt["restored_verify"]["ok"])
        locator_content = Ingestor(restored, restored.get("project:contract")["data"]).read(historical_locator)
        blob_hash = historical_locator["content_identity"]["digest"]
        historical_bytes = restored.read_blob(blob_hash)
        receipt["historical_read"] = {"locator": historical_locator, "blob_sha256": digest(historical_bytes), "bytes": len(historical_bytes), "read_text_sha256": digest(locator_content.encode()), "read_chars": len(locator_content)}
        check("historical_blob_hash_verified", digest(historical_bytes) == blob_hash)
        receipt["production_after"] = {"state_revision": source.current_revision(), "policy_revision": source.active_policy_revision(), "db_sha256": file_hash(source.db_path)}
        check("production_unchanged", receipt["production_before"] == receipt["production_after"])
        receipt["status"] = "passed"
    except Exception as error:
        receipt.update(status="failed", error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        atomic_json(work / "recovery_receipt.json", receipt)
        atomic_json(ROOT / "var/receipts/r2_recovery.json", receipt)
    print(json.dumps({"status": receipt["status"], "receipt": str(work / "recovery_receipt.json"), "checks": len(receipt["checks"]), "error": receipt.get("error")}, ensure_ascii=False))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
