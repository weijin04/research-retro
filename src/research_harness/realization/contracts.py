from __future__ import annotations

import copy
import json
import math
import operator
from importlib.resources import files

from jsonschema import Draft202012Validator

from research_harness.common import HarnessError, digest
from research_harness.storage import ConflictError

WIRE_TYPES = {"parameter_binding", "realization_contract", "obligation", "probe_spec", "execution_receipt"}
ENTITY_TYPES = {"entity_state", "representation", "run_attempt", "observable_definition", "comparison",
                "hypothesis", "finding", "reconstruction_package", "relation", "investigation", "scope"}
RULES = {"eq": operator.eq, "ne": operator.ne, "lt": operator.lt, "le": operator.le,
         "gt": operator.gt, "ge": operator.ge, "in": lambda a, b: a in b,
         "subset": lambda a, b: set(a) <= set(b), "dimension_eq": operator.eq,
         "approx_eq": lambda a, b, tolerance: math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tolerance}


def predicate(spec, observations):
    if spec["rule_id"] != "builtin:" + spec["op"] + ":1" or spec["op"] not in RULES:
        raise HarnessError("capability_blocked", "Predicate needs a registered rule or accountable review")
    args = []
    for arg in spec["args"]:
        if isinstance(arg, dict) and set(arg) == {"field"}:
            value = observations
            for key in arg["field"].split("."):
                if not isinstance(value, dict) or key not in value:
                    raise HarnessError("scientific_test_invalid", "Missing predicate observation: " + arg["field"])
                value = value[key]
            args.append(value)
        else:
            args.append(arg)
    try:
        return bool(RULES[spec["op"]](*args))
    except (TypeError, ValueError, ArithmeticError) as error:
        raise HarnessError("scientific_test_invalid", "Predicate operands invalid") from error


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def validate(store, record, pending=None, trusted=False):
    pending = pending or {}
    kind = record.get("record_type")
    schema = json.loads(files("research_harness.resources").joinpath("retro2.schema.json").read_text())
    root = {"$ref": "#/$defs/" + (kind if kind in WIRE_TYPES else "entity"), "$defs": schema["$defs"]}
    errors = list(Draft202012Validator(root).iter_errors(record))
    if errors:
        raise HarnessError("invalid_contract", "; ".join(e.message for e in errors[:5]))
    if kind not in WIRE_TYPES | ENTITY_TYPES or record.get("extensions", {}).get("is_example"):
        raise HarnessError("invalid_contract", "Unknown record type or example record")
    if store.get(record["snapshot_id"])["kind"] != "source_snapshot":
        raise HarnessError("invalid_contract", "snapshot_id must name a frozen source snapshot")
    def reference(ref):
        if ref["id"] in pending and pending[ref["id"]]["revision"] == ref["revision"]:
            return pending[ref["id"]]
        return store.get(ref["id"], ref["revision"])["data"]
    for value in walk(record):
        if set(value) == {"id", "revision"}:
            reference(value)
        if "artifact_id" in value and "start_byte" in value:
            artifact = store.get(value["artifact_id"], value["artifact_revision"])
            data = artifact["data"]
            content = store.read_blob(data["sha256"])
            if value["sha256"] != data["sha256"] or not 0 <= value["start_byte"] <= value["end_byte_exclusive"] <= len(content):
                raise HarnessError("invalid_locator", "Locator does not match captured bytes")
        if set(value) >= {"state", "value", "unit", "alternatives", "unknown_reason"}:
            if value["state"] == "known" and (value["value"] is None or value["unknown_reason"] is not None):
                raise HarnessError("invalid_contract", "Known values need an actual value")
            if value["state"] == "unknown" and (not value["unknown_reason"] or value["value"] is not None):
                raise HarnessError("invalid_contract", "Unknown values need an explicit reason and no invented value")
            if value["state"] == "alternatives" and len(value["alternatives"]) < 2:
                raise HarnessError("invalid_contract", "Alternatives need at least two admissible values")
    basis = record.get("basis", {})
    if not trusted and (basis.get("origin_assurance") in {"controlled_collector", "authenticated_collector"} or kind == "execution_receipt"):
        raise HarnessError("permission_denied", "Only the broker can issue controlled execution receipts")
    if kind == "obligation" and record["state"] == "discharged":
        if not trusted or not record["evidence_refs"] or record["outcome"] is None or record["adjudication"] == "none":
            raise HarnessError("scientific_test_invalid", "Discharge requires independently adjudicated witnesses")
    if kind == "relation":
        relation = record["payload"]
        if relation.get("relation_type") not in {"generated", "consumed", "may_read", "must_read_given_conditions", "observed_read",
                "value_depends_on", "version_parent", "scientific_support", "scientific_counter_support", "same_bytes", "same_execution", "same_object", "comparable", "correlated"}:
            raise HarnessError("invalid_contract", "Unknown relation contract")
        if not all(isinstance(relation.get(k), dict) and set(relation[k]) == {"id", "revision"} for k in ("source", "target")):
            raise HarnessError("invalid_contract", "Relations pin both endpoint revisions")
    return record


def import_records(unit, document):
    if document.get("based_on") != unit.store.current_revision():
        raise ConflictError("Entity import based_on is stale")
    records = document.get("records", [])
    if not records or len({r["id"] for r in records}) != len(records):
        raise HarnessError("invalid_contract", "Nonempty unique record IDs required")
    pending = {r["id"]: r for r in records}
    reads = {"project:contract": unit.store.get("project:contract")["revision"]}
    output = []
    for record in records:
        validate(unit.store, record, pending)
        try:
            old = unit.store.get(record["id"])
        except KeyError:
            expected = 1
        else:
            expected = old["revision"] + 1
            reads[old["id"]] = old["revision"]
        if record["revision"] != expected:
            raise ConflictError("Revision must append exactly one immutable revision")
        for ref in walk(record):
            if set(ref) == {"id", "revision"} and ref["id"] not in pending:
                current = unit.store.get(ref["id"])
                if current["revision"] != ref["revision"]:
                    raise ConflictError("Import references stale dependency: " + ref["id"])
                reads[ref["id"]] = ref["revision"]
        output.append({"id": record["id"], "kind": record["record_type"], "data": copy.deepcopy(record)})
    return unit.store.commit(output, "import typed records without scientific promotion", reads,
                             "records:" + digest(document), unit.store.active_policy_revision())


def entity(kind, identifier, snapshot, payload, scope=None):
    return {"schema_version": "2.0", "id": identifier, "revision": 1, "snapshot_id": snapshot,
            "record_type": kind, "extensions": {}, "scope": scope or {"snapshot": snapshot}, "payload": payload}


def basis(mode="static_conditional", assurance="bytes_only"):
    return {"mode": mode, "origin_assurance": assurance, "witness_refs": [], "assumption_refs": [],
            "qualification": "conditional reconstruction; not proof of historical execution or scientific adequacy"}
