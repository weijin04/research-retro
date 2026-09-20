#!/usr/bin/env python3
"""Real offline installation and foreign-project lifecycle through public interfaces.

The synthetic sources are generated here, never read from the developer's research
projects. The inner process sees only system runtime files and its disposable sandbox.
"""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class Run:
    def __init__(self, root):
        self.root = root
        self.log = root / "execution.jsonl"
        self.assertions = []
        self.retro = "/sandbox/venv/bin/retro"
        self.workspace = "/sandbox/state"

    def command(self, argv, stdin=None, expected=0):
        started = time.time()
        proc = subprocess.run(argv, input=None if stdin is None else json.dumps(stdin), text=True, capture_output=True, timeout=90)
        with self.log.open("a") as out:
            out.write(json.dumps({"argv": argv, "stdin": stdin, "returncode": proc.returncode,
                                  "stdout": proc.stdout, "stderr": proc.stderr, "elapsed_s": time.time() - started}) + "\n")
        if proc.returncode != expected:
            raise AssertionError(f"{argv}: expected {expected}, got {proc.returncode}: {proc.stdout[-5000:]} {proc.stderr[-1000:]}")
        return proc.stdout

    def cli(self, args, expected=0):
        return json.loads(self.command([self.retro, "-w", self.workspace, *args], expected=expected))

    def call(self, name, expected=0, **args):
        if name not in ("init", "inspect"):
            args = {"workspace": self.workspace, **args}
        return json.loads(self.command([self.retro, "call"], {"name": "retro_" + name, "arguments": args}, expected))

    def check(self, name, condition, detail=None):
        self.assertions.append({"name": name, "passed": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(name + ": " + str(detail))

    def file_input(self, name, data):
        path = Path(self.workspace) / name
        dump(path, data)
        return str(path)


def install(root):
    run = Run(root)
    run.command(["/usr/bin/python3", "-m", "venv", "--without-pip", "/sandbox/venv"])
    pip = str(next((root / "wheels").glob("pip-*.whl")))
    bootstrap = f"import sys,runpy; sys.path.insert(0,{pip!r}); sys.argv=['pip','--isolated','install','--no-index','--find-links','/sandbox/wheels','research-retro']; runpy.run_module('pip',run_name='__main__')"
    run.command(["/sandbox/venv/bin/python", "-I", "-c", bootstrap])
    run.command([run.retro, "--version"])
    tools = json.loads(run.command([run.retro, "tools"]))
    run.check("installed_package_contains_all_tool_definitions", {t["name"] for t in tools["result"]} >= {"retro_init", "retro_scan", "retro_recover", "retro_probe", "retro_verify_handoff"})
    run.check("installed_package_contains_agent_manual", "Research Retro" in run.command([run.retro, "agent"]))
    run.check("developer_home_and_repo_absent", not Path("/home/sun07ao").exists())
    run.check("personal_wrappers_absent", shutil.which("rtk") is None and shutil.which("codex") is None)
    run.command(["/sandbox/venv/bin/python", "-I", "-c",
                 "import research_harness, jsonschema, sqlite3; print(research_harness.__file__); print(sqlite3.sqlite_version)"])
    dump(root / "install-result.json", {"passed": True, "assertions": run.assertions,
                                        "wheels": {p.name: sha(p) for p in (root / "wheels").glob("*.whl")}})


def workflow(root):
    run = Run(root)
    project = root / "foreign-project"
    (project / "instrument/day-17").mkdir(parents=True)
    (project / "misc/2024.odd").mkdir(parents=True)
    (project / "notes").mkdir()
    (project / "abandoned/src").mkdir(parents=True)
    (project / "instrument/day-17/events.csv").write_text("sample,hit\na1,1\na2,1\na3,0\na4,1\na5,1\n")
    (project / "misc/2024.odd/review.tsv").write_text("sample\thit\nb1\t1\nb2\t0\nb3\t1\nb4\t1\n")
    (project / "notes/summary.md").write_text("# Acoustic event detector\nEvery batch has 100% recall.\nBoth evaluation batches are independent and blinded.\nMissing calibration original: archive/clock-calibration.pdf\n")
    (project / "notes/contradiction.txt").write_text("Scope: recorded toy acoustic trials only.\nBatch A has a miss. Clock correction is unavailable.\nBatch B has a miss; label blinding is untested.\nPopulation recall and field deployment remain unknown.\n")
    (project / "abandoned/src/unfinished.py").write_text("def evaluate(samples):\n    return sum(\n")
    (project / "abandoned/src/do_not_run.py").write_text("from pathlib import Path\nPath('/sandbox/ORIGINAL_EXECUTED').write_text('bad')\n")
    (project / "instrument/waveform.bin").write_bytes(b"\x00\xff\x00\x01")
    (project / "notes/long-unread.txt").write_text("unread historical stream\n" * 50000)
    originals = {str(p.relative_to(project)): sha(p) for p in project.rglob("*") if p.is_file()}
    run.command([run.retro, "init", str(project), "--workspace", run.workspace, "--project-id", "foreign-acoustics"])
    first = run.cli(["scan"])["result"]
    rows = first["sources"][0]["assets"]
    run.check("complete_foreign_enumeration", first["sources"][0]["enumeration_complete"])
    run.check("unread_large_original_retained", any(r["state"] == "pending_read" for r in rows))
    run.check("unsupported_binary_retained", any(r["state"] == "unsupported_format" for r in rows))
    run.check("broken_code_retained_as_parse_failure", any(r.get("parse_state") == "parse_failed" for r in rows))
    run.check("original_code_never_executed", not (root / "ORIGINAL_EXECUTED").exists())
    observed = {}
    for key, relative in [("E1", "instrument/day-17/events.csv"), ("E2", "misc/2024.odd/review.tsv"),
                          ("summary", "notes/summary.md"), ("contradiction", "notes/contradiction.txt")]:
        observed[key] = run.cli(["read", relative])["result"]
    scope = {"domain": "synthetic_acoustics", "population": "two recorded toy batches"}
    def node(id, kind, text, source=None, **extra):
        value = {"id": id, "kind": kind, "text": text, "scope": scope, **extra}
        if source:
            a = observed[source]["artifact"]
            value["sources"] = [{"artifact_id": a["id"], "revision": a["revision"]}]
        return value
    nodes = [node("E1", "evidence", "Batch A recorded hits", "E1"), node("E2", "evidence", "Batch B recorded hits", "E2"),
             node("A", "assumption", "Batch A clock calibration licenses evaluation", accepted=True, acceptance_reason="Provisional historical protocol assumption; calibration to be audited"),
             node("B", "assumption", "Batch B label blinding licenses evaluation", accepted=True, acceptance_reason="Provisional historical protocol assumption; blinding to be audited"),
             node("H", "claim", "At least one qualified batch has recall at least 75%", supports=[["E1", "A"], ["E2", "B"]]),
             node("downstream", "inference", "Qualified threshold observation can inform the next experiment", supports=[["H"]]),
             node("S", "claim", "Every batch has 100% recall", "summary", supports=[["E1"], ["E2"]]),
             node("independent", "claim", "Batch B recorded exactly one miss", supports=[["E2"]]),
             node("batch_independence", "claim", "The two evaluation batches are independent", "summary", supports=[]),
             node("independence_gap", "gap", "Cross-batch independence has not been tested; the ID independent denotes a miss-count observation only", gap_state="unchecked"),
             node("missing", "gap", "Calibration certificate archive/clock-calibration.pdf was not supplied", gap_state="missing_original", reopen_conditions=["Locate calibration certificate"]),
             node("untested", "gap", "Population recall and field validity untested", gap_state="unchecked"),
             node("unread", "gap", "Long historical stream has not been read", gap_state="pending_read")]
    status = run.cli(["state"])["result"]
    doc = {"based_on": status["state_revision"], "nodes": nodes}
    run.cli(["reconstruct", "--input", run.file_input("graph.json", doc)])
    run.check("historical_claim_not_promoted", run.call("state", action="get", id="S")["result"]["data"]["support_status"] == "unsupported")
    packet = run.cli(["audit", "open", "--id", "audit:arithmetic", "--targets", "H", "downstream", "S", "independent",
                      "--question", "Check counts, conditional threshold and universal perfect-recall assertion",
                      "--scope", json.dumps(scope), "--obligation", "Recompute both batch counts from captured originals", "--mode", "check"])["result"]
    script = Path(run.workspace) / "verify_counts.py"
    script.write_text('''import csv, io, json, sys
p=json.load(open(sys.argv[1]))
tables={}
for material in p["materials"]:
    text=material["text"]
    if text.startswith("sample,") or text.startswith("sample\\t"):
        rows=list(csv.DictReader(io.StringIO(text),delimiter="\\t" if text.startswith("sample\\t") else ","))
        hits=sum(int(row["hit"]) for row in rows)
        tables["A" if rows[0]["sample"].startswith("a") else "B"]={"hits":hits,"n":len(rows),"recall":hits/len(rows),"misses":len(rows)-hits}
assert tables["A"]=={"hits":4,"n":5,"recall":0.8,"misses":1}
assert tables["B"]=={"hits":3,"n":4,"recall":0.75,"misses":1}
print(json.dumps({"packet_hash":p["content_hash"],"results":{"tables":tables,"universal_perfect_recall":False,"threshold_conditional":"(E1 AND A) OR (E2 AND B)"}}))
''')
    check = run.call("audit", action="check", id="audit:arithmetic", script=str(script))["result"]
    result = packet["result_template"]
    result.update(actual_read_set=check["result_read_set"], completed_analysis={"arithmetic": "A=4/5=0.8, B=3/4=0.75; each has a miss.",
                  "conditional_logic": "Both meet >=0.75 numerically. Evaluative H additionally needs A or B; counts alone do not establish those protocols.",
                  "counterexample": "a3 and b2 each independently refute universal perfect recall."},
                  verdict="qualified", reviewer="synthetic acceptance researcher", residual_assets=["E1", "E2"],
                  unresolved=["Clock calibration", "Label blinding", "Population generalization"],
                  competing_explanations=["Observed rates may depend on protocol failures or selection bias"],
                  first_failing_condition="At least one observed miss contradicts the universal quantifier",
                  verification_receipts=[check["verification"]["id"]],
                  findings={key: {"verdict": "refuted" if key == "S" else "qualified", "scope": scope,
                                  "analysis": "Checked actual counts; threshold conditional on explicitly retained protocol assumptions; perfect recall has two counterexamples."}
                            for key in ["E1", "E2", "H", "downstream", "S", "independent"]})
    run.cli(["audit", "submit", "audit:arithmetic", "--input", run.file_input("arithmetic-result.json", result)])
    correction = {"audit_id": "audit:arithmetic", "result_revision": 1, "reason": "Actual recomputation qualifies counts and refutes perfect recall",
                  "idempotency_key": "initial-qualification", "operations": [
                      *[{"action": "qualify", "target": e} for e in ["E1", "E2"]],
                      *[{"action": "adjudicate", "target": e} for e in ["H", "downstream", "independent"]],
                      {"action": "refute", "target": "S", "payload": {"scope": scope, "residual_assets": ["E1", "E2"],
                       "reopen_conditions": ["New explicitly separated dataset or proven invalidity of both observed counterexamples"]}}]}
    committed = run.call("correct", **correction)["result"]
    run.check("correction_retry_idempotent", run.call("correct", **correction)["result"] == committed)
    changed = {**correction, "reason": "different payload under same key"}
    run.check("idempotency_collision_rejected", not run.call("correct", expected=5, **changed)["ok"])
    def record(id):
        return run.call("state", action="get", id=id)["result"]
    run.check("conditional_two_branch_support", record("H")["data"]["support_status"] == "supported")
    run.check("qualified_evidence_has_consistent_scientific_status", all(record(key)["data"]["evidence_status"] == "qualified" for key in ["E1", "E2"]))
    run.check("audited_claims_no_longer_labeled_unchecked_reconstruction", all(record(key)["data"]["qualification"] == "scoped_audited_judgment" for key in ["H", "S", "downstream", "independent"]))
    run.check("refuted_proposition_not_affirmative", record("S")["data"]["support_status"] == "unsupported" and record("S")["data"]["adjudication_supported"])

    for assumption in ["A", "B"]:
        audit_id = "audit:retract-" + assumption
        p = run.call("audit", action="open", id=audit_id, targets=["H", assumption],
                     question="Does current evidence establish this protocol prerequisite?", scope=scope,
                     obligations=["Separate missing protocol validation from refutation of raw observations"], mode="derive")["result"]
        r = p["result_template"]
        r.update(completed_analysis={"construction": "The same hit tables are compatible with both a calibrated/blinded and a compromised procedure.",
                    "check": "Neither raw hit table records clock calibration or label blinding. Holding all observed counts fixed cannot distinguish those two protocol states.",
                    "conclusion": ("Remove A; E2 AND B still supports H and the numerical observations remain." if assumption == "A" else
                                   "Remove B after A was already withdrawn; neither branch now supports H. Preserve E1/E2 and the independently scoped miss-count observation.")},
                 competing_explanations=["Valid protocol", "Compromised protocol"], verdict="unsupported", reviewer="synthetic protocol audit",
                 residual_assets=["E1", "E2"], unresolved=["Actual protocol state"], first_failing_condition="Missing discriminating protocol record",
                 findings={assumption: {"verdict": "unsupported", "scope": scope, "analysis": "Protocol prerequisite is not established by the observed hit counts."}})
        run.call("audit", action="submit", id=audit_id, result=r)
        run.cli(["correct", "--input", run.file_input("retract-" + assumption + ".json", {
            "audit_id": audit_id, "result_revision": 1, "reason": "Retract unsupported protocol assumption " + assumption,
            "idempotency_key": "retract-" + assumption, "operations": [{"action": "revoke", "target": assumption}]})])
        expected = "supported" if assumption == "A" else "unsupported"
        run.check("AND_OR_after_retract_" + assumption, record("H")["data"]["support_status"] == expected)
        run.check("downstream_after_retract_" + assumption, record("downstream")["data"]["support_status"] == expected)
        run.check("independent_observation_preserved_" + assumption, record("independent")["data"]["support_status"] == "supported")

    run.check("CLI_tool_same_state_contract", run.cli(["state"]) == run.call("state", action="status"))
    run.check("CLI_tool_same_history_contract", run.cli(["state", "history", "H"]) == run.call("state", action="history", id="H"))
    run.check("CLI_tool_same_source_read", run.cli(["read", "instrument/day-17/events.csv"]) == run.call("read", reference="instrument/day-17/events.csv", start=1, live=False))
    bad_cli = run.cli(["export", "--destination", "/sandbox/escaped"], expected=3)
    bad_tool = run.call("export", destination="/sandbox/escaped", expected=3)
    run.check("CLI_tool_same_boundary_error", bad_cli["error"]["code"] == bad_tool["error"]["code"] and not (root / "escaped").exists())
    run.check("package_mount_is_read_only", not os.access("/sandbox/venv", os.W_OK))
    run.check("scientific_sources_unchanged", originals == {str(p.relative_to(project)): sha(p) for p in project.rglob("*") if p.is_file()})
    run.check("database_integrity", run.cli(["state", "verify"])["result"]["ok"])
    exported = run.cli(["export", "--destination", "exports/handoff"])["result"]
    bundle = exported["bundle"]
    inspected = run.call("inspect", bundle=bundle)["result"]
    handoff = inspected["handoff"]
    frozen = {r["id"]: r for r in handoff["records"]}
    run.check("handoff_retains_exact_dependency_formula", frozen["H"]["data"]["support_sets"] == [["E1", "A"], ["E2", "B"]])
    run.check("handoff_retains_all_three_gap_types", {frozen[key]["data"]["gap_state"] for key in ["missing", "untested", "unread"]} == {"missing_original", "unchecked", "pending_read"})
    run.check("handoff_negative_knowledge_present", any(r["kind"] == "negative_knowledge" and r["data"]["reopen_conditions"] for r in handoff["records"]))
    run.check("unverified_batch_independence_explicit", frozen["batch_independence"]["data"]["evidence_status"] == "unchecked")
    run.check("full_context_has_no_silent_exclusions", not handoff["context"]["excluded"])

    # Source perturbation is a separate destructive test on this disposable toy
    # project, after the intentionally frozen handoff. Original real projects are absent.
    old = observed["E1"]["artifact"]
    source = project / "instrument/day-17/events.csv"
    stamp = source.stat()
    source.write_text(source.read_text().replace("a1,1", "a1,0"))
    os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    run.cli(["scan"])
    run.check("same_size_mtime_rewrite_detected_by_hash", record("E1")["data"].get("revoked") is True)
    retained = run.cli(["read", old["id"], "--revision", str(old["revision"])])["result"]
    run.check("old_original_bytes_preserved", retained["text"] == observed["E1"]["text"])
    run.check("refutation_survives_one_counterexample_loss", record("S")["data"]["adjudication_supported"])
    (project / "misc/2024.odd/review.tsv").unlink()
    run.cli(["scan"])
    run.check("missing_original_invalidates_other_branch", record("E2")["data"].get("revoked") is True)
    run.check("refutation_support_expires_after_both_counterexamples_lost", not record("S")["data"]["adjudication_supported"])
    run.call("correct", expected=5, **{**correction, "idempotency_key": "cannot-wash-stale-audit"})
    run.check("fresh_correction_key_cannot_wash_stale_audit", True)
    # The exported packet is independently verified with original source directory hidden.
    project.rename(root / "hidden-originals")
    run.check("handoff_reads_without_sources", run.cli(["inspect", bundle])["result"]["verification"]["ok"])
    dump(root / "workflow-result.json", {"passed": True, "assertions": run.assertions, "frozen_bundle": bundle,
                                         "frozen_revision": handoff["state_revision"], "current_sources": "perturbed only after handoff freeze for robustness testing",
                                         "fixture_role": "constructed synthetic acceptance, not blind scientific evaluation"})


def outer(args):
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix="research-retro-isolated-"))
    shutil.copytree(Path(args.wheelhouse).resolve(), sandbox / "wheels")
    shutil.copy2(getattr(args, "driver", None) or __file__, sandbox / "acceptance.py")
    if getattr(args, "driver", None):
        shutil.copy2(__file__, sandbox / "standalone_acceptance.py")
    wheel = next((sandbox / "wheels").glob("research_retro-*.whl"))
    with zipfile.ZipFile(wheel) as package:
        names = package.namelist()
        assert not any("research_cases/" in n or "/decisions/" in n for n in names)
        assert any(n.endswith("resources/tools.json") for n in names)
        assert any(n.endswith("resources/contract.schema.json") for n in names)
    base = ["bwrap", "--unshare-all", "--die-with-parent", "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64", "--symlink", "usr/bin", "/bin", "--proc", "/proc", "--dev", "/dev",
            "--tmpfs", "/tmp", "--dir", "/home", "--dir", "/home/blank", "--bind", str(sandbox), "/sandbox", "--clearenv",
            "--setenv", "HOME", "/home/blank", "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "LANG", "C.UTF-8",
            "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--chdir", "/sandbox"]
    results = []
    try:
        for phase in ["install", "workflow"]:
            cmd = [*base, *(["--ro-bind", str(sandbox / "venv"), "/sandbox/venv"] if phase == "workflow" else []),
                   "/usr/bin/python3", "/sandbox/acceptance.py", "--inner", phase]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            results.append({"phase": phase, "command": cmd, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
            if proc.returncode:
                raise RuntimeError("Isolation phase failed: " + phase)
    finally:
        for filename in ["execution.jsonl", "install-result.json", "workflow-result.json"]:
            if (sandbox / filename).exists():
                shutil.copy2(sandbox / filename, output / filename)
        dump(output / "isolation.json", {"sandbox": str(sandbox), "phases": results,
                                         "developer_home_mounted": False, "repository_mounted": False, "network_namespace": "unshared",
                                         "installed_package": "read-only during workflow", "sandbox_retained": True})
    shutil.copytree(sandbox / "state/exports/handoff", output / "handoff", dirs_exist_ok=False)
    print(json.dumps({"passed": True, "output": str(output), "sandbox": str(sandbox)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse")
    parser.add_argument("--output")
    parser.add_argument("--inner", choices=["install", "workflow"])
    args = parser.parse_args()
    if args.inner:
        (install if args.inner == "install" else workflow)(Path("/sandbox"))
    else:
        if not args.wheelhouse or not args.output:
            parser.error("--wheelhouse and --output are required")
        outer(args)
