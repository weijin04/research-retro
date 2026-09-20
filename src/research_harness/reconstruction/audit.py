"""Audits are proposed by researchers, verified against captures, then committed.

This integration endpoint does not invent a scientific verdict. It preserves the
named researcher's adjudication and independent deterministic receipts separately.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path
from research_harness.common import HarnessError, now, digest, canonical, atomic_json, upsert

ROOT = Path(__file__).resolve().parents[3]
INTEGRATION_VERSION = "audit-integration-4"

CHECKS = {
    "grephene": {"script": "grephene/audit_check.py", "case": "grephene/audit_case.json", "output": "check_receipt.json"},
    "diffusion": {"script": "diffusion/audit_check.py", "case": "diffusion/audit_case.json", "output": None},
    "grephene-t13b": {"script": "grephene/audit_t13b.py", "case": "grephene/t13b_audit_normalized.json", "output": "check_receipt.json"},
    "grephene-entry": {"script": "grephene/entry_audit.py", "case": "grephene/entry_audit_normalized.json", "output": "check_receipt.json"},
}


def case_path(name):
    if name not in CHECKS:
        raise HarnessError("permission_denied", "Only reviewed harness-owned postprocessors are registered")
    return ROOT / "research_cases" / CHECKS[name]["case"]


def execute_check(name, output_root):
    case_file = case_path(name)
    expected_bytes = case_file.read_bytes()
    expected = json.loads(expected_bytes)
    spec = CHECKS[name]
    script = ROOT / "research_cases" / spec["script"]
    output_root = Path(output_root).resolve()
    if not output_root.is_relative_to(ROOT / "var"):
        raise HarnessError("permission_denied", "Postprocessing output must be in project var/")
    output_root.mkdir(parents=True, exist_ok=True)
    # Some reviewed checkers require a new output rather than overwriting history.
    output_root = output_root / now().replace(":", "").replace("+", "_")
    output_root.mkdir(parents=True, exist_ok=False)
    destination = output_root / spec["output"] if spec["output"] else output_root
    command = [sys.executable, str(script), "--output", str(destination)]
    started = now()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
    receipt = {"command": command, "script_sha256": digest(script.read_bytes()), "started_at": started,
               "finished_at": now(), "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
               "execution_mode": "real_local_postprocess", "is_synthetic": False,
               "new_scientific_job": False, "worker_boundary": "authorized_builder_not_runtime_worker"}
    atomic_json(output_root / "execution.json", receipt)
    if result.returncode:
        raise HarnessError("scientific_test_invalid", "Postprocessor failed", receipt)
    actual_file = destination if spec["output"] else destination / "audit_case.json"
    actual = json.loads(actual_file.read_text())
    if name == "grephene":
        exp = expected["analysis"]["actual_results"]
        fields = {"projections": "projections", "scan": "scan", "upward_scan_steps": "upward_scan_steps", "fc_gaps_ev": "vertical_fc_gaps_ev"}
        equal = all(exp[k] == actual[v] for k, v in fields.items())
    elif name == "diffusion":
        equal = expected["analyses"] == actual["analyses"] and expected["scientific_scope"] == actual["scientific_scope"]
    else:
        actual_results = actual["results"] if name == "grephene-t13b" else actual["actual_results"]
        equal = expected["analysis"]["actual_results"] == actual_results
    receipt["result_identity_matches_case"] = equal
    receipt["result_path"] = str(actual_file)
    receipt["result_sha256"] = digest(actual_file.read_bytes())
    receipt["case_sha256"] = digest(expected_bytes)
    receipt["actual_input_hashes"] = {s["path"]: s["sha256"] for s in actual["source_files"]}
    receipt["execution_record_path"] = str(output_root / "execution.json")
    atomic_json(output_root / "execution.json", receipt)
    if not equal:
        raise HarnessError("source_changed", "Recomputed result differs; scientific re-review required", receipt)
    return receipt


def validate_execution_receipt(receipt, case_path, case):
    """Accept only persisted, source-bound output from reviewed project code.

    This is the authorized-builder boundary. File possession is not a claim of
    OS isolation; an F1 worker must not write these control-plane receipts.
    """
    required = {"command", "script_sha256", "returncode", "result_path", "result_sha256",
                "result_identity_matches_case", "actual_input_hashes", "execution_record_path", "case_sha256"}
    if not isinstance(receipt, dict) or required - receipt.keys():
        raise HarnessError("scientific_test_invalid", "Incomplete execution receipt; a success boolean is insufficient")
    if receipt["returncode"] != 0 or receipt["result_identity_matches_case"] is not True:
        raise HarnessError("scientific_test_invalid", "Check did not complete with matching results")
    for key in ("result_path", "execution_record_path"):
        path = Path(receipt[key]).resolve()
        if not path.is_relative_to(ROOT / "var") or not path.is_file():
            raise HarnessError("scientific_test_invalid", "Missing control-plane receipt/output")
    persisted = json.loads(Path(receipt["execution_record_path"]).read_text())
    if persisted != receipt or digest(Path(receipt["result_path"]).read_bytes()) != receipt["result_sha256"]:
        raise HarnessError("scientific_test_invalid", "Receipt or output fingerprint mismatch")
    if receipt["case_sha256"] != digest(Path(case_path).read_bytes()):
        raise HarnessError("source_changed", "Audit case changed after execution")
    command = receipt["command"]
    if not isinstance(command, list) or len(command) < 2:
        raise HarnessError("scientific_test_invalid", "Missing actual command")
    script = Path(command[1]).resolve()
    if not script.is_relative_to(ROOT / "research_cases") or not script.is_file() or digest(script.read_bytes()) != receipt["script_sha256"]:
        raise HarnessError("scientific_test_invalid", "Unregistered or changed check script")
    expected = {s["path"]: s["sha256"] for s in case["source_files"]}
    if expected != receipt["actual_input_hashes"]:
        raise HarnessError("scientific_test_invalid", "Check read-set does not match case sources")
    return receipt


def integrate_case(store, ingestor, case_path, execution_receipt=None):
    case_path = Path(case_path)
    # Pin the parsed content and its identity to the same read. A source case can
    # change while many raw artifacts are captured; never label old JSON with a
    # later file hash, otherwise a retry could wrongly skip the new version.
    case_bytes = case_path.read_bytes()
    case = json.loads(case_bytes)
    case_id = case["id"]
    validate_execution_receipt(execution_receipt, case_path, case)
    if digest(case_bytes) != execution_receipt["case_sha256"]:
        raise HarnessError("source_changed", "Case changed between its read and receipt verification")
    locators, source_evidence, captures = [], [], []
    source_ids = {}
    for source in case["source_files"]:
        artifact = ingestor.capture(source["path"])
        if artifact["data"]["sha256"] != source["sha256"]:
            raise HarnessError("source_changed", "Case refers to different source bytes: " + source["path"])
        ranges = source.get("line_ranges", [{"start": source.get("start_line", 1), "end": source.get("end_line")}])
        source_locs = [ingestor.locator(artifact, r["start"], r["end"], note=source.get("role", "audit source")) for r in ranges]
        for loc in source_locs:
            ingestor.read(loc)
        locators.extend(source_locs)
        evidence_id = "source-evidence:" + digest([case_id, artifact["id"]])[:24]
        source_ids[source["path"]] = evidence_id
        captures.append(artifact)
        source_evidence.append({"id": evidence_id, "kind": "evidence", "data": {
            "intrinsic_valid": True, "qualification": "source_identity_verified_only",
            "scientific_validity": "not_implied_by_existence", "source_locators": source_locs,
            "blob_refs": [source["sha256"]], "role": source.get("role", "unknown"),
            "artifact_id": artifact["id"], "artifact_revision": artifact["revision"],
            "verification": "full content hash, immutable capture and exact locator checked by integration"}})
    receipt_hash = store.put_blob(canonical(execution_receipt).encode())
    case_hash = store.put_blob(case_bytes)
    result_evidence_id = case_id + ":recomputation"
    conditions = case.get("conditions", case.get("scientific_scope", {}))
    analysis = case.get("analysis", case.get("analyses", {}))
    unresolved = case.get("residual_unknowns", case.get("unresolved", []))
    existing_cases = {r["id"]: r for r in store.list("audit_case")}
    if (case_id in existing_cases and existing_cases[case_id]["data"].get("case_sha256") == case_hash
            and existing_cases[case_id]["data"].get("integration_version") == INTEGRATION_VERSION):
        # Replays do not reset a revoked premise or duplicate researcher judgments.
        return {"status": "already_integrated", "case_id": case_id, "new_execution_receipt": execution_receipt}
    originals = case.get("original_claims", [])
    if not originals:
        originals = [{"id": case_id + ":historical", "text_verbatim": case.get("historical_assertion", {}), "status": "imported_assertion"}]
    history = []
    for index, original in enumerate(originals):
        original = {**original, "id": original.get("id", f"{case_id}:historical:{index}")}
        history.append({"id": original["id"], "kind": "historical_assertion", "data": {
            **original, "track": "then_reported", "qualification": "imported_assertion", "source_locators": locators,
            "historical_belief": "unknown unless explicit record", "event_time": {"status": "unknown", "value": None},
            "collected_at": now(), "current_qualification": "awaiting_current_audit"}})
    initial = upsert(store, history, "preserve historical report before current scientific adjudication")
    records = source_evidence + [{"id": result_evidence_id, "kind": "evidence", "data": {
        "intrinsic_valid": True, "qualification": "deterministic_check_completed", "analysis": analysis,
        "blob_refs": [receipt_hash], "receipt_ref": receipt_hash, "source_locators": locators,
        "source_dependencies": [e["id"] for e in source_evidence],
        "support_sets": [[e["id"] for e in source_evidence]],
        "method_applicability": "scope-limited researcher judgment; not certified by process exit"}}]
    # Make derivation explicitly depend on sources, so source withdrawal propagates.
    records[-1]["data"].pop("intrinsic_valid")
    groups = case.get("source_groups", {})
    group_ids = {group: case_id + ":check:" + group for group in groups}
    for group, spec in groups.items():
        if not spec.get("sources") or any(path not in source_ids for path in spec["sources"]):
            raise HarnessError("invalid_contract", "Unknown/empty inference source group: " + group)
        records.append({"id": group_ids[group], "kind": "evidence", "data": {
            "qualification": "scoped_completed_check", "scope": spec.get("scope", conditions),
            "rationale": spec.get("rationale"), "checked_relations": spec.get("checked_relations"),
            "limitations": spec.get("limitations"), "blob_refs": [receipt_hash], "receipt_ref": receipt_hash,
            "source_locators": [loc for loc in locators if loc["uri"] in spec["sources"]],
            "support_sets": [[source_ids[path] for path in spec["sources"]]]}})
    if group_ids:
        # Aggregate completion is a view; each physical inference uses its own group.
        next(r for r in records if r["id"] == result_evidence_id)["data"]["support_sets"] = [list(group_ids.values())]
    object_id = case_id + ":object"
    records.append({"id": object_id, "kind": "scientific_object", "data": {
        "conditions": conditions, "source_locators": locators, "representation_version": 1,
        "aliases": [], "unknown_fields": case.get("residual_unknowns", case.get("unresolved", []))}})
    records.append({"id": case_id + ":actual-work", "kind": "run", "data": {
        "track": "actual_work", "object_id": object_id, "source_locators": locators, "conditions": conditions,
        "actual_outputs": [s for s in case["source_files"] if "output" in s.get("role", "") or s.get("role") in {"log", "early"}],
        "actual_input_identity": "verified by audit where echoed; see analysis", "historical_executable": "unknown byte version",
        "process_completed": case.get("run_summary", "per-output completion and convergence are separate; inspect source-bound run records and analysis"),
        "protocol_consistency": "checked scoped inputs and output values; see executed checks",
        "numerical_convergence": "see scoped markers; not general certification", "method_applicability": "unchecked beyond scoped analysis",
        "scientific_test_validity": "qualified_for_listed_observables_only", "postprocess_receipt": receipt_hash}})
    claims = case.get("suggested_state_records", [])
    if not claims:
        claims = [{"id": case_id + ":claim", "kind": "claim", "evidence_status": "qualified", "text": case["verdict"]},
                  {"id": case_id + ":branch", "kind": "branch", "evidence_status": "unresolved", "work_disposition": "waiting_input", "text": "Equilibrium/kernel/diffusion conclusions require their own tests"}]
    claim_ids = []
    for item in claims:
        item = copy.deepcopy(item)
        ident, kind = item.pop("id"), item.pop("kind")
        data = {**item, "scope": item.get("scope", conditions), "source_locators": locators, "audit_case_id": case_id,
                "support_sets": [[result_evidence_id]], "researcher": "authorized construction agent",
                "support_semantics": "support for the recorded adjudication; refuted proposition is not made true"}
        if kind == "claim":
            claim_ids.append(ident)
        else:
            data["evidence_verdict"] = item.get("evidence_status", "unresolved")
            data["stop_reason"] = "insufficient connecting evidence" if data.get("work_disposition") == "waiting_input" else None
            data["reopen_conditions"] = unresolved
        records.append({"id": ident, "kind": kind, "data": data})
    for i, n in enumerate(case.get("negative_knowledge", [{"proposition": case.get("verdict"), "verdict": "invalid_inference", "scope": conditions, "failure_type": "finite_DOF_and_sampling", "reopen_condition": "stationary high-frequency windows and independent numerical validation"}])):
        records.append({"id": f"{case_id}:negative:{i}", "kind": "negative_knowledge", "data": {
            **n, "scope": n.get("scope", conditions), "source_locators": locators, "audit_case_id": case_id,
            "reopen_condition": n.get("reopen_condition", unresolved),
            "residual_valid_assets": case.get("retained_assets", case.get("residual_assets", [])), "support_sets": [[result_evidence_id]]}})
    for i, unknown in enumerate(unresolved):
        records.append({"id": f"{case_id}:unknown:{i}", "kind": "unknown", "data": {
            "question": unknown, "audit_case_id": case_id, "status": "unresolved_after_scoped_audit",
            "authorization": "look for already-existing authorized evidence first; new simulation requires separate authority"}})
    for original in history:
        records.append({**original, "data": {**original["data"], "current_qualification": "reviewed_see_audit", "audit_case_id": case_id}})
    records.append({"id": case_id + ":inference", "kind": "inference", "data": {
        "analysis": analysis, "scope": conditions, "conclusions": claim_ids, "support_sets": [[result_evidence_id]],
        "competing_explanations": case.get("competitive_explanations", case.get("competing_explanations")),
        "first_failing_conditions": case.get("first_failing_conditions", case.get("failure_boundary")), "unresolved": unresolved}})
    records.append({"id": case_id, "kind": "audit_case", "data": {
        **case, "case_sha256": case_hash, "integration_version": INTEGRATION_VERSION,
        "blob_refs": [case_hash, receipt_hash], "source_locators": locators,
        "status": "completed_scoped_real_postprocessing", "provenance": "researcher adjudication plus verified deterministic reproduction",
        "independent_physical_evidence_count": "not increased by reports or reviewers", "claim_ids": claim_ids,
        "support_sets": [[result_evidence_id]]}})
    records.append({"id": case_id + ":correction", "kind": "correction", "data": {
        "reason": "Original targets/conditions reconstructed and current inferences qualified from raw data",
        "original_assertion_ids": [r["id"] for r in history], "revised_claim_ids": claim_ids,
        "audit_case_id": case_id, "source_locators": locators, "support_sets": [[result_evidence_id]],
        "history_preserved": True, "new_quantum_or_MD_job": False}})
    for record in records:
        dependencies = case.get("inference_dependencies", {}).get(record["id"])
        if dependencies is not None:
            try:
                record["data"]["support_sets"] = [[group_ids[group] for group in support] for support in dependencies]
                paths = {path for support in dependencies for group in support for path in groups[group]["sources"]}
                record["data"]["source_locators"] = [loc for loc in locators if loc["uri"] in paths]
            except KeyError as e:
                raise HarnessError("invalid_contract", "Unknown inference group " + str(e)) from e
        try:
            old = store.get(record["id"])
        except KeyError:
            continue
        if old["data"].get("revoked"):
            record["data"]["revoked"] = True
            record["data"]["revocation_reason"] = old["data"].get("revocation_reason", "prior retraction retained; reinstatement needs explicit review")
    receipt = upsert(store, records, "scientific adjudication after raw-source reconstruction and deterministic checks")
    return {"case_id": case_id, "status": "integrated", "historical_import": initial, "scientific_patch": receipt}


def revoke(store, object_id, reason):
    record = store.get(object_id)
    correction = {"id": "correction:" + digest([object_id, record["revision"], reason])[:24], "kind": "correction",
                  "data": {"original_text": reason, "target_id": object_id, "before_revision": record["revision"],
                           "reason_type": "assumption_retraction", "physical_falsehood_implied": False, "impact_scan_pending": True}}
    return upsert(store, [{"id": object_id, "kind": record["kind"], "data": {**record["data"], "revoked": True, "revocation_reason": reason}}, correction], reason)
