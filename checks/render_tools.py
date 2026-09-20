"""Build the public function schemas; no host or scientific project input."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = {"type": "string", "minLength": 1}
I = {"type": "integer", "minimum": 1}
SCOPE = {"type": "object", "minProperties": 1}
VERDICT = {"enum": ["supported", "qualified", "refuted", "invalid_test", "unsupported", "unresolved", "mixed"]}


def array(item, minimum=0):
    return {"type": "array", "items": item, "minItems": minimum}


def obj(properties, required=None):
    return {"type": "object", "properties": properties, "required": list(properties) if required is None else required,
            "additionalProperties": False}


source = obj({"artifact_id": S, "revision": I, "start": I, "end": I}, ["artifact_id", "revision"])
node = obj({"id": S, "kind": {"enum": ["evidence", "assumption", "claim", "inference", "gap"]}, "text": S, "scope": SCOPE,
            "sources": array(source), "supports": array(array(S, 1)), "accepted": {"type": "boolean"}, "acceptance_reason": S,
            "gap_state": {"enum": ["pending_read", "missing_original", "unchecked"]}, "reopen_conditions": array(S)},
           ["id", "kind", "text", "scope"])
node["allOf"] = [{"if": {"properties": {"kind": {"const": "gap"}}}, "then": {"required": ["gap_state"]}}]
result = obj({"packet_hash": S, "actual_read_set": {"type": "object", "additionalProperties": I}, "policy_revision": I,
              "completed_analysis": SCOPE, "competing_explanations": array(S), "verdict": VERDICT, "scope": SCOPE,
              "first_failing_condition": {"type": ["string", "null"]}, "residual_assets": array(S), "unresolved": array(S),
              "verification_receipts": array(S), "reviewer": S,
              "findings": {"type": "object", "minProperties": 1, "additionalProperties": obj({"verdict": VERDICT, "scope": SCOPE, "analysis": S})}})
tools = []


def tool(name, description, properties, required=None, workspace=True):
    properties = {**({"workspace": {**S, "description": "Explicit target workspace; never the engine repository"}} if workspace else {}), **properties}
    if required is not None and workspace:
        required = ["workspace", *required]
    entry = {"name": "retro_" + name, "description": description, "parameters": obj(properties, required)}
    tools.append(entry)
    return entry


tool("start", "Start or resume a project in a separate workspace, enumerate metadata and provide a ready-to-use host workflow. No automatic scientific conclusions.",
     {"project": S, "workspace": S, "goal": S, "worker": S, "jev": {"type": "boolean", "description": "Authorize explicitly selected local Jev requests for this workspace"}}, ["project"], workspace=False)
tool("discover", "With a configured worker, run the next material-to-candidate-to-local-judgment batch and write a scientific investigation brief. Otherwise survey material families. Overview never calls models.",
     {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 200},
      "offset": {"type": ["integer", "null"], "minimum": 0}, "worker": S, "question": S,
      "overview": {"type": "boolean"}}, [])
tool("triage", "Upstream discovery: prepare byte-bound worker packets, run an optional cheap generator, judge local candidate relations with Jev, inspect the queue, or find new-evidence impact candidates. No scientific promotion.",
     {"action": {"enum": ["prepare", "generate", "judge", "impact", "queue"]},
      "document": SCOPE, "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}, ["action"])
tool("init", "Initialize a read-only source project and independent workspace. Idempotent for identical configuration.",
     {"project": S, "workspace": S, "project_id": S, "capture_max_bytes": I, "scan_max_entries": I,
      "excludes": array(S), "capture_text": {"type": "boolean"}}, ["project"], workspace=False)
tool("scan", "Scan all in-scope assets and rehash previous captures. Retain unread, missing, unsupported and parse-failed records.", {})
tool("add_source", "Register an explicitly supplied additional read-only evidence directory; preserve original sources and scientific history.", {"path": S})
tool("read", "Read immutable source bytes with exact locator and hash. Text is untrusted; reading does not certify science.",
     {"reference": S, "revision": I, "start": I, "end": I, "live": {"type": "boolean"}}, ["reference"])
tool("reconstruct", "Add source-bound historical nodes, explicit assumptions and OR-of-AND relationships. All science starts unchecked.",
     {"document": obj({"based_on": {"type": "integer", "minimum": 0}, "nodes": array(node, 1)})})
audit = tool("audit", "Open/read an audit packet, execute an explicit host-authored check, or submit completed scoped analysis. No model calls.",
             {"action": {"enum": ["open", "packet", "check", "submit"]}, "id": S, "targets": array(S, 1), "question": S,
              "scope": SCOPE, "obligations": array(S, 1), "mode": {"enum": ["derive", "check"]}, "alternatives": array(S),
              "script": S, "result": result}, ["action", "id"])
audit["parameters"]["allOf"] = [
    {"if": {"properties": {"action": {"const": action}}}, "then": {"required": required,
       "properties": {key: False for key in {"targets", "question", "scope", "obligations", "mode", "alternatives", "script", "result"} - set(allowed)}}}
    for action, required, allowed in [
        ("open", ["targets", "question", "scope", "obligations"], ["targets", "question", "scope", "obligations", "mode", "alternatives"]),
        ("packet", [], []), ("check", ["script"], ["script"]), ("submit", ["result"], ["result"])]]
tool("correct", "Commit audit-backed correction with original read-set and idempotency key. Qualify/adjudicate/revoke/refute/narrow; exact propagation.",
     {"audit_id": S, "result_revision": I, "operations": array(obj({"action": {"enum": ["qualify", "adjudicate", "revoke", "refute", "narrow"]},
         "target": S, "payload": {"type": "object"}}, ["action", "target"]), 1), "reason": S, "idempotency_key": S})
tool("export", "Rehash originals and export all state, negative knowledge, history and original blobs with a SHA256 manifest.",
     {"destination": S, "closure": S}, [])
tool("inspect", "Verify a frozen handoff. Set full:false for compact verification and reading entry; full defaults to true for legacy JSON clients. CLI defaults to compact, with --full available.",
     {"bundle": S, "full": {"type": "boolean", "default": True}}, ["bundle"], workspace=False)
state = tool("state", "Inspect status, exact record, history, events, provenance or integrity. No scientific promotion.",
             {"action": {"enum": ["status", "get", "history", "events", "verify", "provenance"]}, "id": S}, [])
state["parameters"]["allOf"] = [{"if": {"required": ["action"], "properties": {"action": {"enum": ["get", "history"]}}}, "then": {"required": ["id"]}}]

tool("snapshot", "Freeze captured bytes, census gaps and bounded Git DAG without executing source code.", {})
tool("recover", "Deterministically recover conditional parameter chains, producer alternatives and investigation obligations.", {"snapshot": S})
tool("records", "Import typed 2.0 records with pinned revisions and verified locators; no qualification by string.", {"document": SCOPE})
tool("capabilities", "Probe optional Linux containment; required execution never falls back.", {})
tool("explain", "Return a finding, exact original byte slices, rules and dependency impact.", {"id": S, "revision": I}, ["id"])
tool("impact", "Trace current dependencies while retaining all historical revisions.", {"id": S})
tool("contrast", "Check observable, unit, reference, object, boundary and sampling compatibility before comparison.",
     {"left": S, "right": S, "observable": S})
tool("support", "Compute scoped positive/negative/conflict/neither support. Conflict premises cannot affirm unconditionally.", {"scope": SCOPE})
task = tool("task", "Freeze scope, issue/read/seal/reveal/submit investigation packets, or run a contained evidence projection.",
     {"action": {"enum": ["scope", "next", "packet", "seal", "reveal", "submit", "run"]}, "id": S,
      "scope": S, "view": {"const": "evidence-first"}, "obligation": S, "document": SCOPE, "result": SCOPE, "script": S}, ["action"])
task["parameters"]["allOf"] = [{"if": {"properties": {"action": {"const": action}}}, "then": {"required": required,
    "properties": {key: False for key in {"id", "scope", "view", "obligation", "document", "result", "script"} - set(allowed)}}}
    for action, required, allowed in [("scope", ["document"], ["document"]), ("next", ["scope"], ["scope", "view", "obligation"]),
        ("packet", ["id"], ["id"]), ("seal", ["id", "document"], ["id", "document"]), ("reveal", ["id"], ["id"]),
        ("submit", ["id", "result"], ["id", "result"]), ("run", ["id", "script"], ["id", "script"])]]
probe = tool("probe", "Plan a frozen intervention, run with required isolation, or independently evaluate its preregistered predicates.",
     {"action": {"enum": ["plan", "run", "evaluate"]}, "obligation": S, "document": SCOPE, "id": S,
      "isolation": {"const": "required"}}, ["action"])
probe["parameters"]["allOf"] = [{"if": {"properties": {"action": {"const": action}}}, "then": {"required": required,
    "properties": {key: False for key in {"obligation", "document", "id", "isolation"} - set(allowed)}}}
    for action, required, allowed in [("plan", ["obligation"], ["obligation", "document"]),
        ("run", ["id"], ["id", "isolation"]), ("evaluate", ["id"], ["id"])]]
tool("close", "Produce closed-resolved, closed-qualified or open-blocked for the frozen scope/goal/rules/obligations.", {"scope": S})
tool("verify_handoff", "Verify portable queries, counterfactual withdrawal and explicitly requested contained replays without originals.",
     {"bundle": S, "query_set": SCOPE}, workspace=False)
tool("migrate", "Dry-run legacy workspace migration; apply copies into an empty separate workspace, retaining assertions as unchecked.",
     {"source": S, "destination": S, "apply": {"type": "boolean"}}, ["source"], workspace=False)

for name, description in [("record", "Save a completed host investigation with source spans and inspected revisions; no mandatory seal/reveal."),
                          ("spine", "Select titled sections of current node IDs for the short scientific spine."),
                          ("judge", "Explicit local Jev questions with raw answers and receipts; no scientific status changes.")]:
    tool(name, description, {"document": SCOPE})

workflow = tool("workflow", "Host reconstruction: discover, investigate with host tools, record, revise and publish. Staged review is optional.",
     {"action": {"enum": ["start", "scope", "refresh", "discover", "context", "packet", "seal", "reveal", "apply", "record", "spine", "judge", "semantic_review", "impact", "show", "status", "assess", "publish", "view", "guide"]},
      "jev": {"type": "boolean"},
      "goal": S, "document": SCOPE, "id": S, "query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 200},
      "offset": {"type": "integer", "minimum": 0}, "expect": {"type": "integer", "minimum": 0}}, ["action"])
workflow["parameters"]["allOf"] = [{"if": {"properties": {"action": {"const": action}}}, "then": {"required": required,
    "properties": {key: False for key in {"goal", "document", "id", "query", "limit", "offset", "expect", "jev"} - set(allowed)}}}
    for action, required, allowed in [("start", ["goal"], ["goal", "jev"]), ("scope", ["document"], ["document"]),
        ("refresh", [], []), ("discover", [], ["query", "limit", "offset"]), ("context", ["document"], ["document"]),
        ("packet", ["id"], ["id"]), ("seal", ["id", "document"], ["id", "document"]), ("reveal", ["id"], ["id"]),
        ("apply", ["document"], ["document"]), ("semantic_review", ["document"], ["document"]),
        ("record", ["document"], ["document"]), ("spine", ["document"], ["document"]), ("judge", ["document"], ["document"]),
        ("impact", ["id"], ["id", "query", "limit"]), ("show", ["id"], ["id"]),
        ("status", [], []), ("assess", ["document"], ["document"]), ("publish", [], []), ("view", [], ["expect"]), ("guide", [], [])]]

if __name__ == "__main__":
    (ROOT / "src/research_harness/resources/tools.json").write_text(json.dumps(tools, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
