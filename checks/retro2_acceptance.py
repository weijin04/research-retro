#!/usr/bin/env python3
"""Installed public lifecycle with four actual interventions and portable replay.

Outer process creates the declared synthetic fixture. Inner process receives only
the case, the installed wheel and this host-side acceptance program, no oracle.
This is an executable product acceptance, not a blinded LLM science evaluation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Host:
    def __init__(self):
        self.base = Path("/sandbox")
        self.log = self.base / "retro2-execution.jsonl"
        self.workspace = "/sandbox/retro2-state"
        self.checks = []

    def command(self, argv, expected=0, document=None):
        started = time.monotonic()
        proc = subprocess.run(argv, input=json.dumps(document) if document is not None else None,
                              capture_output=True, text=True, timeout=90)
        with self.log.open("a") as log:
            log.write(json.dumps({"command": argv, "input": document, "returncode": proc.returncode,
                "stdout": proc.stdout, "stderr": proc.stderr, "elapsed": time.monotonic()-started}) + "\n")
        if proc.returncode != expected:
            raise AssertionError(proc.stdout[-5000:] + proc.stderr[-2000:])
        return json.loads(proc.stdout)

    def cli(self, *args, expected=0):
        envelope = self.command(["/sandbox/venv/bin/retro", "-w", self.workspace, *args], expected)
        return envelope["result"] if expected == 0 else envelope

    def call(self, name, expected=0, **args):
        if name not in {"verify_handoff", "inspect", "migrate"}:
            args = {"workspace": self.workspace, **args}
        return self.command(["/sandbox/venv/bin/retro", "call"], expected,
                            {"name": "retro_" + name, "arguments": args})["result"]

    def check(self, name, passed, details=None):
        self.checks.append({"name": name, "passed": bool(passed), "details": details})
        if not passed:
            raise AssertionError(name + ": " + str(details))

    def state(self):
        return self.cli("state")


def workflow():
    h = Host()
    project = Path("/sandbox/case")
    original = {str(p.relative_to(project)): fingerprint(p) for p in project.rglob("*") if p.is_file()}
    h.cli("init", str(project), "--workspace", h.workspace)
    snapshot = h.cli("snapshot")["result"]["id"]
    recovery = h.cli("recover", "--snapshot", snapshot)
    state = h.state()
    records = {r["id"]: r for r in state["records"]}
    bindings = [r["data"] for r in records.values() if r["kind"] == "parameter_binding"]
    h.check("historical_effective_steps", {b["effective"]["value"] for b in bindings if b["symbol"] == "steps"} == {500, 200000})
    h.check("requested_effective_separated", all(b["requested"]["value"] == 200000 for b in bindings if b["symbol"] == "steps"))
    attempts = [r["data"]["payload"] for r in records.values() if r["kind"] == "run_attempt"]
    h.check("two_historical_attempts_with_unbound_alternatives", len(attempts) == 2 and all(a["association"] == "conditional_reconstruction" and a["unbound_alternatives"] for a in attempts))
    h.check("untrusted_receipts_not_self_authenticated", all(a["origin_assurance"] == "project_asserted" for a in attempts))
    findings = [r for r in records.values() if r["kind"] == "finding"]
    codes = {r["data"]["payload"]["code"] for r in findings}
    h.check("all_structural_diagnostics", {"operator_value_changed", "effective_parameter_bound", "shared_bytes", "cache_dependency_omission", "live_withdrawn_premise", "execution_dependency_difference"} <= codes)
    for finding in findings:
        explanation = h.cli("explain", finding["id"])["result"]
        h.check("explain_" + finding["id"], all(o["text"] for o in explanation["originals"]))
    h.check("containment_available_in_clean_install", h.cli("capabilities")["result"]["contained"])
    obligation_ids = [r["id"] for r in records.values() if r["kind"] == "obligation"]
    o = obligation_ids[0]
    selected = ["driver.py", "protocol.json", "kernels/__init__.py", "kernels/gate.py", "kernels/plain.py"]
    cfg = json.loads(h.cli("read", "protocol.json")["text"])
    matrix, executions = [], []
    for name, kernel, steps in (("neither", "gate", 500), ("cap_only", "gate", 200000),
                                ("gate_only", "plain", 500), ("both", "plain", 200000)):
        # This explicitly authorized host program sets the intervention; original
        # project code executes only inside the required contained runner.
        script = f'''import json, os, runpy, shutil, sys
from pathlib import Path
for p in Path('/input').rglob('*'):
    if p.is_file() and not p.name.startswith('_retro_'):
        q=Path('/work')/p.relative_to('/input');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
os.environ['RR_MAX_STEPS']={str(steps)!r}
os.environ['RR_KERNEL']={kernel!r}
sys.argv=['driver.py','result']
sys.path.insert(0,'/work')
runpy.run_path('/work/driver.py',run_name='__main__')
'''
        k = 0.0 if kernel == "gate" else cfg["k_AB_per_s"]
        total = k + cfg["k_BA_per_s"]
        discrete = 0 if total == 0 else k / total * -math.expm1(steps * math.log1p(-total * cfg["dt_s"]))
        predicates = [
            {"op": "eq", "args": [{"field": "last_step"}, steps], "rule_id": "builtin:eq:1"},
            {"op": "approx_eq", "args": [{"field": "p_B"}, discrete, 1e-11], "rule_id": "builtin:approx_eq:1"}]
        plan = h.call("probe", action="plan", obligation=o, document={"script": script, "files": selected, "expected_predicates": predicates})["result"]
        receipt = h.cli("probe", "run", plan["id"], "--isolation", "required")["result"]
        h.check(name + "_ran_with_no_implicit_scientific_promotion", receipt["data"]["execution_completed"] and receipt["data"]["scientific_adequacy"] == "unchecked")
        evaluation = h.cli("probe", "evaluate", receipt["id"])["result"]
        h.check(name + "_independent_discrete_formula", evaluation["all_passed"])
        observed = receipt["data"]["extensions"]["observations"]
        matrix.append({"intervention": name, "steps": steps, "population": observed["p_B"], "discrete": discrete,
                       "duration_s": observed["last_time_s"], "receipt": receipt["id"]})
        executions.append({"id": receipt["id"], "revision": 2})
    h.check("minimal_repair_depends_on_question", matrix[1]["population"] == 0 and 0.019 < matrix[2]["population"] < 0.021 and matrix[2]["duration_s"] == .5 and matrix[3]["population"] > .79 and matrix[3]["duration_s"] == 200)
    scientific_scope = {"model_id": "declared-two-state-population", "object_ids": [],
        "domain": {"initial_population": 0, "dt_s": cfg["dt_s"], "k_AB_per_s": cfg["k_AB_per_s"],
                   "k_BA_per_s": cfg["k_BA_per_s"], "requested_duration_s": 200},
        "quantifier": "this_execution", "conditions": []}
    def typed(kind, identifier, payload):
        return {"schema_version": "2.0", "id": identifier, "revision": 1, "record_type": kind,
                "snapshot_id": snapshot, "scope": scientific_scope, "payload": payload, "extensions": {}}
    def put(items):
        return h.call("records", document={"based_on": h.state()["state_revision"], "records": items})
    hypotheses = {}
    updated = []
    for r in records.values():
        if r["kind"] == "hypothesis":
            row = r["data"]
            label = row["payload"]["historical_assertion"]["id"]
            row.update(scope=scientific_scope, revision=r["revision"]+1)
            hypotheses[label] = {"id": row["id"], "revision": row["revision"]}
            updated.append(row)
    assumption = typed("finding", "premise:historical-H0", {"text": "Historical H0, represented explicitly as a conditional premise, not as scientific fact",
        "conditional_assumption": {"accepted": True, "reason": "Reconstruct the historical conditional argument before applying the inspected counterevidence"}})
    gate_evidence = typed("finding", "evidence:controlled-gate", {"text": "The actual contained gate probe emitted zero under the captured conditions"})
    gate_o = json.loads(json.dumps(records[o]["data"]))
    gate_o.update(id="obligation:controlled-gate", revision=1, scope=scientific_scope,
                  target_question="Does the controlled gated implementation emit zero in the tested conditions?", extensions={}, acceptance_predicates=[])
    rate_o = json.loads(json.dumps(gate_o))
    rate_o.update(id="obligation:declared-rate", target_question="Is H0 compatible with the declared positive forward rate and controlled plain implementation?")
    put(updated + [assumption, gate_evidence, gate_o, rate_o])
    obligation_ids += [gate_o["id"], rate_o["id"]]
    records = {r["id"]: r for r in h.state()["records"]}
    graph_targets = [*hypotheses.values(), {"id": gate_evidence["id"], "revision": 1}]
    graph_before_revision = None
    def relation(identifier, source, target, negative=False, premises=None):
        payload = {"relation_type": "scientific_counter_support" if negative else "scientific_support",
                   "source": source, "target": target}
        if premises:
            payload["premises"] = premises
        return typed("relation", identifier, payload)
    # A separate declared question over the complete synthetic material set; all
    # automatically raised obligations are inspected and explicitly reviewed.
    scope = h.call("task", action="scope", document={"snapshot_id": snapshot, "goal": "Recover the declared finite two-state study, distinguish historical claims from controlled interventions, and retain non-identifiable historical execution provenance", "obligations": obligation_ids,
                    "roles": {"MODEL.md": "definition", "README.md": "narrative", "AGENTS.md": "narrative", "argument.json": "narrative", "notes/retraction.txt": "narrative"},
                    "targets": graph_targets})["result"]
    h.check("closure_blocks_before_investigation", h.cli("close", "--scope", scope["id"])["status"] == "open-blocked")
    for index, identifier in enumerate(obligation_ids):
        if identifier == rate_o["id"]:
            gate_ref = {"id": gate_evidence["id"], "revision": 1}
            put([relation("support:gate-witness", {"id": gate_o["id"], "revision": 2}, gate_ref),
                 relation("support:historical-H0", {"id": assumption["id"], "revision": 1}, hypotheses["H0"]),
                 relation("support:C1", hypotheses["H0"], hypotheses["C1"], premises=[hypotheses["H0"], gate_ref]),
                 relation("support:C2", gate_ref, hypotheses["C2"])])
            before = h.call("support", scope=scientific_scope)["result"]
            h.check("historical_argument_has_explicit_conditional_support", before["nodes"][hypotheses["C1"]["id"]]["usable_positive"] and before["conditional_assumptions"] == [assumption["id"]])
            graph_before_revision = h.state()["state_revision"]
            assumption["revision"] = 2
            assumption["payload"]["conditional_assumption"] = {"accepted": False,
                "reason": "Inspected positive declared rate and controlled plain probe invalidate the zero-rate premise in this model"}
            put([assumption])
        task = h.call("task", action="next", scope=scope["id"], obligation=identifier)["result"]
        packet = h.cli("task", "packet", task["id"])["result"]
        h.check("evidence_view_hides_narrative_" + str(index), all(m["role"] == "evidence" for m in packet["materials"]))
        if index == 0:
            h.cli("task", "reveal", task["id"], expected=3)
        h.call("task", action="seal", id=task["id"], document={"hypotheses": ["Parameter limit changes sampled time", "Rate truncation changes the operator", "Narrative overstates identifiable execution provenance"], "analysis": {"basis": "frozen source bindings and separately executed intervention matrix", "matrix": matrix}})
        h.cli("task", "reveal", task["id"])
        result = packet["result_template"]
        current_o = records[identifier]["data"]
        finding_id = current_o["extensions"].get("finding_ref", {}).get("id")
        finding = records[finding_id]["data"]["payload"] if finding_id else {"question": current_o["target_question"], "scope": scientific_scope}
        result.update(outcome="qualified", reviewer="deterministic acceptance host; explicit synthetic model analysis",
            analysis={"question": current_o["target_question"], "inspected_finding": finding,
                "derivation": "For the declared deterministic model, p_N=k/(k+r)*(1-(1-(k+r)*dt)^N). The gated k=.04<.05 becomes zero, so p_N=0 regardless of cap. Plain k=.04 gives p_500 about .019753; N=200000 gives about .799964. The 0.5-second run cannot test the 200-second population. Equal output hashes do not prove execution or statistical independence; project receipts remain assertions. The withdrawn H0 is a premise of C1, but C2 only asserts the gated output was zero.",
                "matrix": matrix, "qualification": "Numerical/scientific statements restricted to this declared synthetic model; historical association is conditional"},
            witness_refs=executions, remaining=["Project-created historical receipts are not authenticated external execution observations"],
            reopen_conditions=["New authenticated historical records", "Different declared model, observable, initial state or sampling domain"])
        if identifier == gate_o["id"]:
            result.update(outcome="confirmed", remaining=[], judgments=[{"target": {"id": gate_evidence["id"], "revision": 1},
                "polarity": "positive", "analysis": "Two independently executed contained gated probes returned p_B=0, matching the exact discrete formula."}])
        elif identifier == rate_o["id"]:
            result.update(outcome="refuted", remaining=[], judgments=[{"target": hypotheses["H0"], "polarity": "negative",
                "analysis": "The declared k_AB is positive and the controlled ungated recurrence gives a positive population, contradicting H0 within this explicit model."}])
        h.call("task", action="submit", id=task["id"], result=result)
    put([relation("counter-support:H0", {"id": rate_o["id"], "revision": 2}, hypotheses["H0"], negative=True)])
    support = h.call("support", scope=scientific_scope)["result"]
    h.check("withdrawal_propagates_and_independent_conclusion_survives", not support["nodes"][hypotheses["C1"]["id"]]["usable_positive"] and support["nodes"][hypotheses["C2"]["id"]]["usable_positive"] and support["nodes"][hypotheses["H0"]["id"]]["status"] == "negative")
    graph_index = typed("finding", "finding:scientific-argument", {"hypotheses": hypotheses, "withdrawn_premise": assumption["id"],
        "before_state_revision": graph_before_revision, "current_support": support,
        "replay_query": {"op": "withdraw", "ids": [assumption["id"]], "scope": scientific_scope, "at_state_revision": graph_before_revision}})
    put([graph_index])
    closure = h.cli("close", "--scope", scope["id"])["result"]
    h.check("qualified_complete_retains_historical_uncertainty", closure["status"] == "closed-qualified" and not closure["unresolved_obligations"])
    bundle = h.cli("export", "--closure", closure["id"], "--destination", "exports/reconstruction")["bundle"]
    source_after = {str(p.relative_to(project)): fingerprint(p) for p in project.rglob("*") if p.is_file()}
    h.check("source_and_git_byte_identical", source_after == original)
    project.rename("/sandbox/hidden-original")
    queries = {"queries": [{"op": "get", "id": closure["id"], "field": ["data", "payload", "status"], "expected": "closed-qualified"},
                           *[{"op": "replay", "id": r["id"]} for r in executions], graph_index["payload"]["replay_query"]]}
    verified = h.call("verify_handoff", bundle=bundle, query_set=queries)
    h.check("portable_queries_and_four_replays_without_sources", verified["all_passed"])
    withdrawn = verified["receipts"][-1]["answer"]["nodes"]
    h.check("portable_historical_withdrawal_is_nonempty_and_discriminating", not withdrawn[hypotheses["C1"]["id"]]["usable_positive"] and withdrawn[hypotheses["C2"]["id"]]["usable_positive"])
    dump(h.base / "retro2-query-set.json", queries)
    dump(h.base / "retro2-result.json", {"passed": True, "assertions": h.checks, "intervention_matrix": matrix,
        "closure": closure, "bundle": bundle, "queries": queries,
        "evaluation_boundary": "Installed deterministic synthetic acceptance; no LLM or real-project blind scientific accuracy claim"})


def outer(args):
    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    sandbox = Path(tempfile.mkdtemp(prefix="retro2-installed-"))
    shutil.copytree(args.wheelhouse, sandbox / "wheels")
    shutil.copy2(__file__, sandbox / "acceptance.py")
    spec = importlib.util.spec_from_file_location("fixture", root / "research_retro_architecture/benchmark.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="retro2-generate-") as generation:
        module.build(Path(generation) / "fixture")
        shutil.copytree(Path(generation) / "fixture/case", sandbox / "case")
    base = ["bwrap", "--unshare-all", "--die-with-parent", "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64", "--symlink", "usr/bin", "/bin", "--proc", "/proc", "--dev", "/dev",
            "--tmpfs", "/tmp", "--dir", "/home", "--bind", str(sandbox), "/sandbox", "--clearenv", "--setenv", "HOME", "/nonexistent",
            "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "LANG", "C.UTF-8", "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--chdir", "/sandbox"]
    pip = "/sandbox/wheels/" + next((sandbox / "wheels").glob("pip-*.whl")).name
    bootstrap = "import runpy,sys;sys.path.insert(0," + repr(pip) + ");sys.argv=['pip','--isolated','install','--no-index','--find-links','/sandbox/wheels','research-retro'];runpy.run_module('pip',run_name='__main__')"
    commands = [base + ["/usr/bin/python3", "-m", "venv", "--without-pip", "/sandbox/venv"],
                base + ["/sandbox/venv/bin/python", "-I", "-c", bootstrap],
                base + ["--ro-bind", str(sandbox / "venv"), "/sandbox/venv", "/sandbox/venv/bin/python", "-I", "/sandbox/acceptance.py", "--inner"]]
    runs = []
    try:
        for command in commands:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=300)
            runs.append({"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
            if proc.returncode:
                raise RuntimeError(proc.stderr[-4000:] + proc.stdout[-2000:])
    finally:
        dump(output / "isolation.json", {"sandbox": str(sandbox), "commands": runs, "network": False, "developer_home": False, "source_checkout": False})
        for path in sandbox.glob("retro2-*.json*"):
            shutil.copy2(path, output / path.name)
    shutil.copytree(sandbox / "retro2-state/exports/reconstruction", output / "handoff")
    result = json.loads((output / "retro2-result.json").read_text())
    print(json.dumps({"passed": result["passed"], "assertions": len(result["assertions"]), "output": str(output), "sandbox": str(sandbox)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--inner", action="store_true")
    args = parser.parse_args()
    if args.inner:
        workflow()
    else:
        outer(args)
