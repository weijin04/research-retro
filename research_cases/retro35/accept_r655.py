#!/usr/bin/env python3
"""One real r655 acceptance: archived state, live Jev, normal public workflow.

No fabricated scientific nodes, synthetic API answers, new scientific jobs or
source writes. The two known textual repairs are declared, not a blind benchmark.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

from research_harness.agent_tools import invoke
from research_harness.common import atomic_json, now
from research_harness.unit import Unit
from research_harness.config import load
from research_harness.storage import Store
from research_harness import semantic


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(original, workspace, output, resume_prepared=False):
    original, workspace, output = map(lambda p: Path(p).resolve(), (original, workspace, output))
    output.mkdir(parents=True, exist_ok=resume_prepared)
    log = output / "acceptance.jsonl"
    checks = []

    def record(event, **fields):
        with log.open("a") as stream:
            stream.write(json.dumps({"at": now(), "event": event, **fields}, ensure_ascii=False) + "\n")
        print(event, json.dumps(fields, ensure_ascii=False)[:1500], flush=True)

    def check(name, condition, **details):
        checks.append({"name": name, "passed": bool(condition), **details})
        record("check", **checks[-1])
        if not condition:
            raise AssertionError(name)

    def call(action, **arguments):
        name = "retro_workflow"
        if action == "discover":
            name = "retro_discover"
        args = {"workspace": str(workspace), **arguments}
        if name == "retro_workflow":
            args["action"] = action
        result = invoke({"name": name, "arguments": args})
        path = output / (str(len(list(output.glob("command-*.json")))).zfill(3) + ".tmp")
        path = output / ("command-" + path.stem + "-" + action + ".json")
        atomic_json(path, {"request": {"name": name, "arguments": args}, "response": result})
        record("command", action=action, ok=result["ok"], receipt=str(path),
               jev_calls=result.get("result", {}).get("jev_calls", result.get("result", {}).get("semantic_checks", {}).get("jev_calls", 0)))
        if not result["ok"]:
            raise AssertionError(result["error"])
        return result["result"]

    original_db = original / "state/state.sqlite3"
    original_hash = sha(original_db)
    frozen = json.loads((original / "publications/r655/SCIENTIFIC_STATE.json").read_text())
    frozen_nodes = {n["id"]: n for n in frozen["nodes"]}
    check("historical_r655_false_green_retained", frozen["state_revision"] == 655 and
          not frozen_nodes["claim:pair-scope"]["current"]["needs_review"] and
          not frozen_nodes["route:thermal"]["current"]["needs_review"])
    with sqlite3.connect(f"file:{original_db}?mode=ro", uri=True) as src:
        check("source_database_is_exact_r655", src.execute("SELECT max(sequence) FROM events").fetchone()[0] == 655)
        if not resume_prepared:
            workspace.mkdir(parents=True, exist_ok=False)
            (workspace / "state").mkdir()
            with sqlite3.connect(workspace / "state/state.sqlite3") as dst:
                src.backup(dst)
            shutil.copytree(original / "state/blobs", workspace / "state/blobs")
        else:
            copied = Store(workspace / "state")
            check("resume_retains_exact_r655_scientific_nodes", all(copied.get(i)["data"] == n["data"] and
                  copied.get(i)["revision"] == n["revision"] for i, n in frozen_nodes.items()))
    manifest = json.loads(((workspace if resume_prepared else original) / "retro.json").read_text())
    # Resolve source roots explicitly so a different external workspace depth
    # does not retarget the historical contract. Stored absolute roots match.
    for source in manifest["sources"]:
        source["root"] = str((original / source["root"]).resolve())
    # Use the existing append-only governance API to relocate only this copy's
    # output boundary. Keep all original contract revisions and science intact.
    store = Store(workspace / "state")
    if not resume_prepared or store.get("project:contract")["data"] != load(workspace):
        manifest["policy_revision"] = store.active_policy_revision() + 1
        atomic_json(workspace / "retro.json", manifest)
        relocation = store.governance_update(load(workspace), store.active_policy_revision(),
            "Authorized acceptance copy: relocate output boundary only; retain r655 science and original contract history")
        record("copy_relocation", receipt=relocation, original_database_sha256=original_hash)
    unit = Unit(workspace)
    check("whole_historical_module_state_preserved", len(unit.store.list("research_node")) == 87)
    hessian = unit.store.get("obs:pair-hessian")
    source_hashes = {loc["uri"]: sha(loc["uri"]) for loc in hessian["data"]["source_locators"]}
    check("hessian_originals_match_historical_evidence", all(
          source_hashes[l["uri"]] == l["content_identity"]["digest"] for l in hessian["data"]["source_locators"]))

    before = call("view")
    nodes = {n["id"]: n for n in before["nodes"]}
    check("aligned_r655_now_blocks_semantically_unchecked_claim_and_action",
          nodes["claim:pair-scope"]["current"]["needs_review"] and nodes["route:thermal"]["current"]["needs_review"]
          and not nodes["claim:pair-scope"]["current"]["usable_positive"],
          claim=nodes["claim:pair-scope"]["current"], route=nodes["route:thermal"]["current"])

    # Enable the real host integration on the entire archived state, not a
    # preselected pair. All actual receipts, including other findings, survive.
    reviewed = call("semantic_review", document={"authorize_egress": True})
    receipts = {r["data"]["node_id"]: r["data"] for r in sorted(unit.store.list("semantic_review"), key=lambda r:r["data"]["at"])}
    check("real_jev_request_and_response_receipts", sum(r["jev_calls"] for r in receipts.values()) > 0 and
          all(r["status"] == "ok" and r["http_status"] == 200 and r["response"]["usage"]["input_tokens"] > 0 for r in receipts.values()),
          jev_calls=reviewed["jev_calls"], models=sorted({r["response"]["model"] for r in receipts.values() if r.get("response")}))
    check("jev_rationale_verdict_does_not_authorize_merge", any(r.startswith("semantic:rationale:") for r in semantic.findings(receipts["claim:pair-scope"])),
          answers=receipts["claim:pair-scope"]["response"]["answers"])
    check("jev_action_verdict_does_not_authorize_merge", any(r.startswith("semantic:actions:") for r in semantic.findings(receipts["route:thermal"])),
          answers=receipts["route:thermal"]["response"]["answers"])
    check("contradictory_receipts_do_not_merge_state", {"claim:pair-scope", "route:thermal"}.issubset(reviewed["state"]["needs_review"]))

    discovery = call("discover", query="__no_mainline_matches__", limit=24)
    unlinked = discovery["unlinked_queue"]
    check("independent_queue_survives_zero_relevance_query", not discovery["candidates"] and bool(unlinked["candidates"])
          and unlinked["query_independent"] and all(c["claim_references"] == 0 for c in unlinked["candidates"]),
          total=unlinked["total"], candidates=unlinked["candidates"])
    check("unmarked_calculation_candidates_selected_without_branch_prompt", any(
          not c["linked"] and set(c["signals"]) & {"higher_order_output", "calculation_output", "abnormal_exit_hint"}
          for c in unlinked["candidates"]))

    def repair(changes, analysis):
        existing = {i: unit.store.get(i) for i in changes}
        focus = set(changes)
        materials = []
        originals = {}
        for i, node in existing.items():
            data = node["data"]
            focus.update(r["id"] for r in data.get("requires", []))
            focus.update(r["id"] for field in ("supports", "counters") for group in data.get(field, []) for r in group)
            originals[i] = []
            for loc in data.get("source_locators", []):
                key = "source" + str(len(materials))
                artifact = unit.store.get(loc["artifact_id"], loc["artifact_revision"])["data"]
                item = {"key": key, "path": loc["uri"], "role": "history" if Path(loc["uri"]).suffix == ".md" else "definition",
                        "start": loc["locator"]["start"], "end": loc["locator"]["end"]}
                if artifact["identity_scope"] == "captured_segment":
                    item["bytes"] = artifact["byte_range"]
                materials.append(item)
                originals[i].append(key)
        if not materials:
            loc = hessian["data"]["source_locators"][0]
            materials.append({"key": "hessian", "path": loc["uri"], "role": "evidence", "start": 1, "end": 8})
        packet = call("context", document={"question": "Reconcile completed observations, current rationale and next actions across this historical state",
            "materials": materials, "focus": sorted(focus),
            "prior_exposure": "Known r655 defects; targeted repair acceptance, not an unseen-project or cold scientific benchmark"})
        check("context_forces_independent_material", bool(packet["unlinked_candidates"]) and any(m.get("mandatory_unlinked") for m in packet["materials"]),
              candidates=packet["unlinked_candidates"])
        call("seal", id=packet["id"], document={"analysis": analysis,
             "alternatives": ["Same local Hessian already completed", "Distinct full-space or connection test still unresolved"]})
        call("reveal", id=packet["id"])
        incoming = []
        for i, node in existing.items():
            data = copy.deepcopy(node["data"])
            data = {k: v for k, v in data.items() if k in {"type", "status", "title", "statement", "scope", "rationale", "details", "links", "next", "action", "actions"}}
            data.update(changes[i])
            data.update(id=i, sources=originals[i])
            for field in ("requires", "supports", "counters"):
                value = node["data"].get(field, [])
                data[field] = [r["id"] for r in value] if field == "requires" else [[r["id"] for r in group] for group in value]
            incoming.append(data)
        return call("apply", document={"context": packet["id"], "input_hash": packet["input_hash"],
            "reviewer": "Codex host; user-authorized real r655 repair acceptance", "analysis": analysis, "nodes": incoming})

    partial = repair({"claim:pair-scope": {"rationale":
        "两份局域 R/TS Hessian 已取得并按14原子活动空间复算：R零虚频，TS一条−452.343 cm−1虚频；"
        "活动模态 HO/QH100-S 的 ΔG‡ 在298/473 K分别约10.1775/9.6090 kcal/mol。"
        "NEB电子垒约13.45 kcal/mol是不同量。频率stdout及执行回执、全空间驻点资格和双向路径连接"
        "仍未在此快照中证实；局域曲率不能替代真实动力学、扩散/相遇/自旋或产率证据。"}},
        "按已有Hessian观察量修平旧理由中的未出具状态，保留执行关联、全空间和连接的真实缺口。")
    check("partial_repair_keeps_downstream_action_blocked", "route:thermal" in partial["state"]["needs_review"] and
          "claim:pair-scope" not in partial["state"]["needs_review"], jev_calls=partial["semantic_checks"]["jev_calls"])
    route = unit.store.get("route:thermal")["data"]
    affected = call("impact", id="claim:pair-scope")["declared_dependents"]
    changes = {i: {} for i in affected}
    changes["route:thermal"] = {"details": {**route["details"], "next":
        "使用已复算的R/TS局域Hessian和同活动空间自由能；补查频率stdout/执行回执以确认运行身份，"
        "核验几何两侧端点与双向连接及全空间驻点资格，再构建覆盖依赖的动力学。"}}
    completed = repair(changes, "更新当前行动为尚缺的运行身份、双向连接和全空间资格验证；同步所有显式后继的前提引用，保留其他科学判断。")
    final = call("view")
    nodes = {n["id"]: n for n in final["nodes"]}
    check("semantic_repair_clears_both_target_nodes", not nodes["claim:pair-scope"]["current"]["needs_review"] and
          not nodes["route:thermal"]["current"]["needs_review"], claim=nodes["claim:pair-scope"]["current"], route=nodes["route:thermal"]["current"])
    check("normal_apply_performs_real_jev_calls", partial["semantic_checks"]["jev_calls"] > 0 and completed["semantic_checks"]["jev_calls"] > 0)
    published = call("publish")
    visible = json.loads((workspace / "current/SCIENTIFIC_STATE.json").read_text())
    check("publication_uses_same_field_gate", {n["id"]: n["current"] for n in visible["nodes"]} ==
          {n["id"]: n["current"] for n in call("view")["nodes"]})
    check("original_historical_state_and_hessians_unchanged", sha(original_db) == original_hash and
          all(sha(path) == value for path, value in source_hashes.items()))
    calls = unit.store.list("semantic_review")
    summary = {"passed": True, "case": "real grephene r655", "role": "known-defect repair acceptance; no unseen-project performance claim",
        "single_uninterrupted_run": not resume_prepared,
        "acceptance_status": "completed_after_recorded_interruptions" if resume_prepared else "completed",
        "initial_field_judgments": {i: receipts[i]["response"]["answers"] for i in ("claim:pair-scope", "route:thermal")},
        "clear_threshold": semantic.MIN_CONSISTENT_PROBABILITY,
        "prior_failed_assertions": [entry for line in log.read_text().splitlines()
            if (entry := json.loads(line)).get("event") == "check" and not entry["passed"]],
        "original_workspace": str(original), "workspace": str(workspace), "checks": checks,
        "jev_calls": sum(r["data"]["jev_calls"] for r in calls),
        "jev_successful_calls": sum(r["data"]["jev_calls"] for r in calls if r["data"]["status"] == "ok"),
        "judgment_receipts": [r["id"] for r in calls], "remaining_review": call("status")["needs_review"],
        "publication": published, "source_database_sha256": original_hash}
    atomic_json(output / "result.json", summary)
    record("complete", passed=True, jev_calls=summary["jev_calls"], remaining_review=summary["remaining_review"], result=str(output / "result.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--resume-prepared", action="store_true", help="Continue the same acceptance before scientific text repair; preserve all prior API/setup receipts")
    args = parser.parse_args()
    run(args.original, args.workspace, args.output, args.resume_prepared)
