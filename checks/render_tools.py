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


tool("init", "Initialize a read-only source project and independent workspace. Idempotent for identical configuration.",
     {"project": S, "workspace": S, "project_id": S, "capture_max_bytes": I, "scan_max_entries": I,
      "excludes": array(S), "capture_text": {"type": "boolean"}}, ["project"], workspace=False)
tool("scan", "Scan all in-scope assets and rehash previous captures. Retain unread, missing, unsupported and parse-failed records.", {})
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
     {"destination": S}, [])
tool("inspect", "Verify/read a self-contained frozen handoff without source project or workspace access.", {"bundle": S}, workspace=False)
state = tool("state", "Inspect status, exact record, history, events, provenance or integrity. No scientific promotion.",
             {"action": {"enum": ["status", "get", "history", "events", "verify", "provenance"]}, "id": S}, [])
state["parameters"]["allOf"] = [{"if": {"required": ["action"], "properties": {"action": {"enum": ["get", "history"]}}}, "then": {"required": ["id"]}}]

if __name__ == "__main__":
    (ROOT / "src/research_harness/resources/tools.json").write_text(json.dumps(tools, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
