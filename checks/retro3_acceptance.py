#!/usr/bin/env python3
"""Installed 3.0 workflow in the same empty offline namespace as legacy acceptance.

This constructs a known scientific example to test product behavior; real host
discovery/cold tasks are separately reported in the release evidence.
"""
import argparse
import json
import math
from pathlib import Path
import shutil

from standalone_acceptance import Run, dump, install, outer, sha


def workflow(root):
    run = Run(root)
    source = root / "unfamiliar-project"
    source.mkdir()
    mixed = source / "mixed.md"
    mixed.write_text("Time: 4 s; complete detection, Poisson model assumed.\nObserved events: 0\nOld conclusion: the physical rate is exactly zero.\n")
    (source / "operator.py").write_text("def step(state):\n    return state  # no event transition implemented\n")
    (source / "residual.txt").write_text("Independent experiment still needs its own model.\n")
    original = {p.name: sha(p) for p in source.iterdir()}
    skill = run.command([run.retro, "skill"])
    run.check("packaged_host_method_is_available_without_project", "Discover before fixing the map" in skill)
    run.command([run.retro, "skill", "--destination", str(root / "host-skill")])
    run.check("skill_installs_with_complete_protocol", (root / "host-skill/references/protocol.md").is_file())
    result = json.loads(run.command([run.retro, "start", str(source)]))["result"]
    run.check("default_workspace_is_external", result["workspace"] == str(root / "unfamiliar-project.retro") and not (source / ".retro").exists())
    run.check("single_start_provides_host_entry_and_method", Path(result["entry"]).is_file() and (Path(result["workspace"]) / "host/references/protocol.md").is_file())
    resumed = json.loads(run.command([run.retro, "start", str(source)]))["result"]
    run.check("resume_preserves_scientific_state", resumed["resumed"] and resumed["state"]["state_revision"] == result["state"]["state_revision"])
    # Exercise the explicit path too; moving an authoritative workspace is not
    # a supported migration and must not bypass its recorded project contract.
    run.command([run.retro, "init", str(source), "--workspace", run.workspace, "--metadata-only"])

    def call(action, **args):
        response = run.call("workflow", action=action, **args)
        if not response["ok"]:
            raise AssertionError(response)
        return response["result"]

    call("start", goal="What did the zero-event attempt establish, and how can research continue?")
    discovery = call("discover")
    run.check("census_is_not_claimed_scientifically_read", discovery["matched"] == 3 and not discovery["scientific_reading_complete"])

    def context(focus=()):
        return call("context", document={"question": "What is warranted by zero recorded events?", "focus": list(focus),
            "materials": [{"key": "conditions", "path": "mixed.md", "role": "definition", "start": 1, "end": 1},
                          {"key": "zero", "path": "mixed.md", "role": "evidence", "start": 2, "end": 2},
                          {"key": "old", "path": "mixed.md", "role": "history", "start": 3, "end": 3}],
            "prior_exposure": "Known synthetic acceptance; not a blind scientific evaluation"})

    def node(id, type="observation", **fields):
        return {"id": id, "type": type, "title": id, "statement": id,
                "scope": {"time_s": 4, "observable": "detected counts", "model": "Poisson conditional"},
                "status": "observed" if type == "observation" else "conditional", "rationale": "synthetic acceptance construction",
                "sources": ["zero"] if type == "observation" else [], **fields}

    def submit(p, nodes):
        call("seal", id=p["id"], document={"analysis": "Zero observed events is compatible with positive finite rates; the operator must permit events.",
                                           "alternatives": ["positive physical rate but finite sample", "operator does not permit event", "zero rate"]})
        sealed = call("packet", id=p["id"])
        run.check("seal_does_not_implicitly_reveal_history", sealed["hidden_history_spans"] == 1)
        call("reveal", id=p["id"])
        return call("apply", document={"context": p["id"], "input_hash": p["input_hash"], "reviewer": "deterministic acceptance host",
            "analysis": "Conditional Poisson inference; withdrawal requires revised downstream understanding.", "nodes": nodes})

    p = context()
    run.check("definition_before_history_with_only_selected_materials",
              [m["role"] for m in p["materials"] if not m.get("mandatory_unlinked")] == ["definition", "evidence"]
              and len(p["read_set"]) == 2 and p["unlinked_candidates"] == [])
    upper = -math.log(0.05) / 4
    submit(p, [node("obs:zero"), node("assumption:operator", "assumption", status="conditional", statement="The implementation permits the physical event"),
        node("claim:rate", "claim", supports=[["obs:zero", "assumption:operator"]], statement=f"k <= {upper:.9f} s^-1 at one-sided 95% confidence under declared assumptions", details={"formula": "-ln(0.05)/T", "upper_s_inverse": upper}),
        node("route:transport", "route", requires=["claim:rate"], statement="Use this constraint only while observation and operator assumptions remain eligible"),
        node("obs:independent", statement="independent usable observation"),
        node("claim:alternative", "claim", supports=[["obs:zero", "assumption:operator"], ["obs:independent"]])])
    view = call("view"); initial = {n["id"]: n for n in view["nodes"]}
    run.check("actual_numeric_derivation_retained", abs(initial["claim:rate"]["data"]["details"]["upper_s_inverse"] - 0.748933068388) < 1e-10)
    call("assess", document={"reviewer": "synthetic only", "coverage": {"sufficient": True, "basis": "known fixture"},
        "residual_review": {"samples": [{"path": "residual.txt", "finding": "independent context"}]},
        "handoff": {"passed": True, "tasks": ["synthetic declaration; real acceptance separate"], "receipt": "execution.jsonl"},
        "limitations": ["synthetic acceptance"], "scientific_problem": "open", "continuation": "bounded"})
    publication = call("publish")
    run.check("three_views_and_source_index_are_emitted", all((Path(run.workspace) / "current" / n).is_file() for n in ["index.html", "MAINLINE.md", "SCIENTIFIC_STATE.json", "NAVIGATION.md", "SOURCE_INDEX.json"]))
    p = context(["assumption:operator"])
    submit(p, [node("assumption:operator", "assumption", status="withdrawn", statement="Original operator has no transition; the zero-count observation cannot bound the physical rate")])
    now = call("view"); nodes = {n["id"]: n for n in now["nodes"]}
    run.check("correction_reaches_argument_route_and_current_view", nodes["claim:rate"]["current"]["needs_review"] and nodes["route:transport"]["current"]["needs_review"] and json.loads((Path(run.workspace) / "current/SCIENTIFIC_STATE.json").read_text())["completion"]["status"] == "draft")
    run.check("independent_alternative_survives", nodes["claim:alternative"]["current"]["usable_positive"] and nodes["obs:independent"] == initial["obs:independent"])
    frozen = json.loads((Path(publication["directory"]) / "SCIENTIFIC_STATE.json").read_text())
    run.check("old_publication_is_unchanged_history", frozen["completion"]["status"] == "reconstructed-qualified")
    stale = run.call("workflow", expected=5, action="view", expect=view["state_revision"])
    run.check("stale_downstream_context_is_rejected", not stale["ok"])
    # Mechanical repair deliberately remains qualified: no false rate bound.
    p = context(["claim:rate", "route:transport", "obs:zero"])
    submit(p, [node("claim:rate", "claim", status="withdrawn", statement="No physical rate bound from a transition-disabled implementation", requires=["obs:zero"]),
               node("route:transport", "route", status="implementation_failed", statement="Retain raw observation; repair event operator before testing physical rate", requires=["obs:zero"])])
    repaired = {n["id"]: n for n in call("view")["nodes"]}
    run.check("host_repair_is_usable_offline_without_model_permission",
              not repaired["route:transport"]["current"]["needs_review"] and
              call("status")["jev_calls"] == 0)
    direct = run.call("record", document={"question": "What remains usable independently?", "reviewer": "installed test host",
        "analysis": "Direct host investigation through the installed public API.",
        "materials": [{"key": "residual", "path": "residual.txt", "role": "evidence"}],
        "nodes": [node("gap:independent", "gap", status="open", statement="The independent experiment needs its own model.",
                       sources=["residual"], details={"discovery": {"finding": "Separate research question", "next_check": "Specify its model"}})]})
    run.check("installed_direct_record_needs_no_staged_review", direct["ok"])
    spine = run.call("spine", document={"sections": [{"title": "What remains", "nodes": ["route:transport", "gap:independent"]}]})
    call("publish")
    short = (Path(run.workspace) / "current/SPINE.md").read_text()
    run.check("installed_spine_and_detailed_map_are_separate", spine["ok"] and "gap:independent" in short and
              "obs:independent" not in short and (Path(run.workspace) / "current/RESEARCH_MAP.md").is_file())
    run.check("discovery_returns_scientific_finding", call("discover")["scientific_candidates"][0]["id"] == "gap:independent")
    later = root / "later-evidence"; later.mkdir()
    (later / "new.txt").write_text("New independently supplied evidence.\n")
    before_extra = {n["id"]: n for n in call("view")["nodes"]}
    addition = run.call("add_source", path=str(later))
    run.check("installed_additional_source_preserves_science", addition["ok"] and
              {n["id"]: n for n in call("view")["nodes"]} == before_extra)
    new_read = run.cli(["read", str(later / "new.txt")])["result"]
    run.check("installed_additional_source_is_readable", "independently supplied" in new_read["text"])
    prepared = run.call("triage", action="prepare", document={"materials": [{"path": "mixed.md"}]})
    packet = json.loads(Path(prepared["result"]["path"]).read_text())
    run.check("installed_upstream_packet_has_exact_originals", prepared["ok"] and
              packet["materials"][0]["sha256"] == sha(mixed) and "Observed events: 0" in packet["materials"][0]["text"])
    parser = 'import json,sys; p=json.load(sys.stdin); print(json.dumps({"packet":p["id"],"generator":{"name":"synthetic parser"},"candidates":[]}))'
    generated = run.call("triage", action="generate", document={"packet": packet["id"],
                         "command": [str(Path(run.retro).with_name("python")), "-c", parser]})
    run.check("installed_worker_runs_without_host_sdk", generated["ok"] and
              json.loads(Path(generated["result"]["input"]).read_text())["packet"] == packet["id"])
    denied = run.call("triage", expected=3, action="judge", document={"packet": packet["id"], "candidates": []})
    run.check("installed_upstream_egress_is_explicit", not denied["ok"] and denied["error"]["code"] == "permission_denied")
    run.check("candidate_generation_does_not_rewrite_science", {n["id"]: n for n in call("view")["nodes"]} == before_extra and
              call("status")["jev_calls"] == 0)
    run.check("original_project_unchanged", original == {p.name: sha(p) for p in source.iterdir()})
    bundle = run.cli(["export", "--destination", "exports/handoff"])["result"]["bundle"]
    shutil.rmtree(source)
    shutil.rmtree(later)
    inspected = run.cli(["inspect", bundle])["result"]
    index = json.loads((Path(bundle) / "SOURCE_INDEX.json").read_text())
    entry = index["sources"][str(mixed)][0]
    run.check("offline_bundle_resolves_original_bytes", inspected["verification"]["ok"] and "Observed events: 0" in (Path(bundle) / entry["blob"]).read_text())
    run.check("offline_bundle_retains_revised_state", json.loads((Path(bundle) / "SCIENTIFIC_STATE.json").read_text())["nodes"] != frozen["nodes"])
    run.check("cold_entry_starts_with_scientific_spine", "SPINE.md" in (Path(bundle) / "START_HERE.md").read_text())
    dump(root / "workflow-result.json", {"passed": True, "assertions": run.assertions, "frozen_bundle": bundle,
        "fixture_role": "known synthetic product behavior; not scientific discovery accuracy", "originals_deleted_before_handoff_check": True})


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
        args.driver = __file__
        outer(args)
