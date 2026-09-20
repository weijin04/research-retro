"""Recover producer alternatives, conditional parameters and dependency differences."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re

from research_harness.common import HarnessError, digest, stable_id, upsert
from research_harness.realization.contracts import basis, entity, validate
from research_harness.recovery import RULE_VERSION
from research_harness.recovery.snapshot import materialize
from research_harness.recovery.static import Analyzer, launcher_environment


def recover(unit, snapshot_id):
    snapshot = unit.store.get(snapshot_id)
    if snapshot["kind"] != "source_snapshot":
        raise HarnessError("invalid_contract", "recover requires a frozen snapshot")
    data, store = snapshot["data"], unit.store
    current = materialize(store, data["files"])
    records, findings, gaps, analyses, attempts = [], [], list(data["gaps"]), [], []

    def add(record):
        records.append({"id": record["id"], "kind": record["record_type"], "data": record})
        return record["id"]

    def finding(code, question, detail, locators=None, severity="review"):
        identifier = stable_id("finding", [snapshot_id, code, detail])
        add(entity("finding", identifier, snapshot_id, {"code": code, "question": question, "detail": detail,
                    "locators": locators or [], "rule_version": RULE_VERSION, "severity": severity,
                    "qualification": "diagnostic candidate; not a scientific verdict"}))
        findings.append(identifier)
        scope = {"model_id": "unreviewed", "object_ids": [identifier], "domain": {"snapshot": snapshot_id},
                 "quantifier": "this_execution", "conditions": []}
        add({"schema_version": "2.0", "id": identifier.replace("finding:", "obligation:"), "revision": 1,
             "snapshot_id": snapshot_id, "extensions": {"finding_ref": {"id": identifier, "revision": 1}, "required": True},
             "record_type": "obligation", "target_question": question, "kind": "semantic", "scope": scope,
             "required_capabilities": [], "acceptance_predicates": [], "state": "open", "outcome": None,
             "adjudication": "none", "evidence_refs": [], "blockers": []})

    def analyze(files, label):
        shells = {p: launcher_environment(f["content"]) for p, f in files.items() if p.endswith(".sh")}
        scenarios = list(shells.items()) or [("no-launcher", {})]
        for launcher, env in scenarios:
            for path in sorted(files):
                if not path.endswith(".py"):
                    continue
                analysis = Analyzer(files, path, env).analyze()
                analysis.update(scenario=label, launcher=launcher, environment=env)
                analyses.append(analysis)
                stages = defaultdict(list)
                bindings = analysis["bindings"] + [b for c in analysis["calls"] for b in c["bindings"]]
                for b in bindings:
                    stages[(b["locator"]["artifact_id"], b["scope"], b["symbol"])].append(b)
                for (_, binding_scope, symbol), chain in stages.items():
                    # Local names are scoped by path, scenario, callsite and location.
                    identifier = stable_id("binding", [snapshot_id, label, launcher, path, symbol, chain])
                    add({"schema_version": "2.0", "id": identifier, "revision": 1, "snapshot_id": snapshot_id,
                         "extensions": {"path": path, "scenario": label, "launcher": launcher,
                                        "binding_scope": binding_scope, "assumptions": analysis["assumptions"], "dependencies": sorted({d for b in chain for d in b["dependencies"]})},
                         "record_type": "parameter_binding", "run_ref": None, "symbol": symbol,
                         "requested": chain[0].get("requested_value") or chain[0]["value"], "effective": chain[-1]["value"],
                         "stages": [{"operator_rule": b["rule"], "input_refs": b["dependencies"], "output": b["value"],
                                     "path_conditions": [], "locators": [b["locator"]]} for b in chain],
                         "basis": basis(), "unresolved_dependencies": [b["value"]["unknown_reason"] for b in chain if b["value"]["state"] == "unknown"]})
                    if len(chain) > 1 and chain[0]["value"]["state"] == chain[-1]["value"]["state"] == "known" and chain[0]["value"]["value"] != chain[-1]["value"]["value"]:
                        finding("operator_value_changed", "Does the transformed operator still realize the declared model?",
                                {"symbol": symbol, "before": chain[0]["value"], "after": chain[-1]["value"], "scenario": label,
                                 "binding": identifier}, [b["locator"] for b in chain])
                    for b in chain:
                        if b["expression"].startswith("min(") and b["value"]["state"] == "known":
                            finding("effective_parameter_bound", "Does the effective bound cover the intended domain?",
                                    {"symbol": symbol, "effective": b["value"], "expression": b["expression"], "scenario": label,
                                     "environment": env, "binding": identifier}, [b["locator"]])

    jsons = {}
    for path, entry in current.items():
        if path.endswith((".json", ".jsonl")):
            try:
                raw = json.loads(entry["content"])
                if isinstance(raw, dict):
                    jsons[path] = raw
            except (ValueError, UnicodeError):
                gaps.append({"path": path, "state": "parse_failed"})
    receipt_paths = [p for p, r in jsons.items() if isinstance(r.get("source_hashes"), dict) and "output_sha256" in r]
    analyzed = set()
    for path in receipt_paths:
        reported = jsons[path]
        candidates = []
        for commit in data["git"]["commits"]:
            if all(commit["files"].get(p, {}).get("sha256") == sha for p, sha in reported["source_hashes"].items()):
                candidates.append(commit)
        output = data["files"].get(reported.get("output", ""))
        output_matches = output is not None and output["sha256"] == reported["output_sha256"]
        qualification = "conditional_reconstruction" if candidates and output_matches else "unbound"
        attempt_id = stable_id("attempt", [snapshot_id, path])
        attempt = entity("run_attempt", attempt_id, snapshot_id, {
            "label": reported.get("attempt_id", path), "reported_receipt": path,
            "receipt_ref": {"id": current[path]["id"], "revision": current[path]["revision"]},
            "origin_assurance": "project_asserted", "association": qualification,
            "candidates": [{"commit": c["id"], "source_hashes": {p: f["sha256"] for p, f in c["files"].items()}} for c in candidates],
            "candidate_limit": 128, "candidate_search_complete": data["git"]["complete"],
            "unbound_alternatives": ["Unrecorded/different executions or fabricated project receipts cannot be excluded by these bytes"],
            "output": reported.get("output"), "output_hash_consistent": output_matches,
            "reported": reported.get("stdout", {}), "source_hashes": reported["source_hashes"],
            "status_axes": {"process_termination": "reported_success" if reported.get("returncode") == 0 else "reported_failure",
                            "output_integrity": "hash_consistent" if output_matches else "unbound", "numerical_convergence": "unknown",
                            "model_applicability": "unchecked", "scientific_test_qualification": "unchecked"}})
        add(attempt)
        attempts.append(attempt)
        if not output_matches:
            finding("receipt_output_mismatch", "Which bytes were produced by this attempt?", {"receipt": path})
        for candidate in candidates:
            signature = digest(candidate["files"])
            if signature not in analyzed:
                analyzed.add(signature)
                analyze(materialize(store, candidate["files"]), candidate["id"])
    analyze(current, "working-tree")

    # Equality of bytes is deliberately separate from execution/sample independence.
    by_hash = defaultdict(list)
    for path, ref in data["files"].items():
        by_hash[ref["sha256"]].append(path)
    for sha, paths in by_hash.items():
        if len(paths) > 1 and any(p.endswith((".csv", ".out", ".log")) for p in paths):
            finding("shared_bytes", "Are these separate executions and statistically independent observations?",
                    {"sha256": sha, "paths": paths, "execution_independence": "unknown", "statistical_independence": "unknown"})
    for i, a in enumerate(attempts):
        for b in attempts[i+1:]:
            left, right = a["payload"], b["payload"]
            changed = sorted(p for p in set(left["source_hashes"]) | set(right["source_hashes"]) if left["source_hashes"].get(p) != right["source_hashes"].get(p))
            common = sorted(p for p in left["source_hashes"] if left["source_hashes"].get(p) == right["source_hashes"].get(p))
            finding("execution_dependency_difference", "Which launch/operator differences explain the observable difference?",
                    {"left": a["id"], "right": b["id"], "changed": changed, "unchanged": common,
                     "reported_observations": [left["reported"], right["reported"]]})
    for path, raw in jsons.items():
        if "cache_key" in raw and isinstance(raw.get("key_fields"), list):
            dependencies = {p for a in attempts for p in a["payload"]["source_hashes"]}
            omitted = sorted(dependencies - set(raw["key_fields"]))
            if omitted:
                finding("cache_dependency_omission", "Is the cache valid under the actual operator and launch conditions?",
                        {"path": path, "declared_key_fields": raw["key_fields"], "omitted_dependencies": omitted,
                         "qualification": "candidate dependency set from project receipts; value influence needs review"})
        if isinstance(raw.get("claims"), list):
            for claim in raw["claims"]:
                if not isinstance(claim, dict) or not isinstance(claim.get("id"), str):
                    continue
                mentions = []
                for note, entry in current.items():
                    if note.endswith((".md", ".txt")):
                        text = entry["content"].decode(errors="replace")
                        if re.search(r"\b" + re.escape(claim["id"]) + r"\b", text) and re.search(r"withdrawn|retract|撤回", text, re.I):
                            mentions.append(note)
                add(entity("hypothesis", stable_id("hypothesis", [snapshot_id, path, claim["id"]]), snapshot_id,
                           {"historical_assertion": claim, "qualification": "imported_assertion", "counterassertion_paths": mentions}))
                if mentions and claim.get("status") == "accepted":
                    affected = [c["id"] for c in raw["claims"] if isinstance(c, dict) and any(claim["id"] in s for s in c.get("supports", []))]
                    finding("live_withdrawn_premise", "Does the current argument depend on a scoped withdrawn premise?",
                            {"premise": claim["id"], "affected_claims": affected, "notes": mentions,
                             "qualification": "conflicting project assertions; scope and adjudication still required"})
    if not attempts:
        gaps.append({"state": "unbound", "reason": "No supported receipt format; output-to-execution identities remain unknown"})
        finding("unbound_history", "Can alternative histories compatible with the surviving bytes change the answer?",
                {"outputs": sorted(p for p in current if p.endswith((".csv", ".out", ".log"))),
                 "requires": "construct two compatible histories or acquire a trusted run witness"})
    summary = {"snapshot_id": snapshot_id, "rule_version": RULE_VERSION, "analyses": analyses, "attempt_ids": [a["id"] for a in attempts],
               "findings": findings, "gaps": gaps + [{"state": "git_coverage", "reason": g} for g in data["git"]["gaps"]],
               "read_set": {r["id"]: r["revision"] for r in data["files"].values()},
               "coverage": {"current_files": len(current), "git_commits": len(data["git"]["commits"]),
                            "scientific_reading_complete": False, "unsupported_syntax": sum(len(a["gaps"]) for a in analyses)},
               "status": "recovered-with-open-obligations"}
    identifier = stable_id("recovery", [snapshot_id, RULE_VERSION])
    records.append({"id": identifier, "kind": "recovery", "data": summary})
    # Validate generated locators and every reference after accounting for this batch.
    pending = {r["id"]: r["data"] for r in records}
    for record in records[:-1]:
        validate(store, record["data"], pending, trusted=True)
    upsert(store, records, "deterministic recovery without executing source code")
    return {"id": identifier, **summary}
