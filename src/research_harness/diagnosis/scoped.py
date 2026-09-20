"""The same typed support projection for live state and portable handoff."""
from research_harness.diagnosis.support import project


def projection(records, scope, withdrawn=()):
    records = {r["id"]: r for r in records} if isinstance(records, list) else records
    withdrawn = set(withdrawn)
    nodes, assumptions = {}, []
    for identifier, record in records.items():
        if record["kind"] not in {"hypothesis", "finding"} or record["data"].get("scope") != scope:
            continue
        nodes[identifier] = {"positive_supports": [], "negative_supports": []}
        payload = record["data"].get("payload", {})
        if payload.get("revoked"):
            withdrawn.add(identifier)
        assumed = payload.get("conditional_assumption", {})
        if assumed.get("accepted") and assumed.get("reason"):
            nodes[identifier]["positive_witness"] = True
            assumptions.append(identifier)
    for record in records.values():
        if record["kind"] != "relation" or record["data"].get("scope") != scope:
            continue
        relation = record["data"]["payload"]
        kind = relation.get("relation_type")
        if kind not in {"scientific_support", "scientific_counter_support"}:
            continue
        source, target = relation["source"], relation["target"]
        if target["id"] not in nodes or records[target["id"]]["revision"] != target["revision"]:
            continue
        if source["id"] in withdrawn or records.get(source["id"], {}).get("revision") != source["revision"]:
            continue
        polarity = "positive" if kind == "scientific_support" else "negative"
        origin = records[source["id"]]
        if origin["kind"] == "obligation" and origin["data"]["state"] == "discharged" and origin["data"]["scope"] == scope:
            ext = origin["data"]["extensions"]
            stale = any(k != origin["id"] and records.get(k, {}).get("revision") != v for k, v in ext.get("read_set", {}).items())
            judgments = ext.get("review", {}).get("judgments", [])
            if not stale and any(j.get("target") == target and j.get("polarity") == polarity for j in judgments):
                nodes[target["id"]][polarity + "_witness"] = True
        elif source["id"] in nodes:
            premises = relation.get("premises", [source])
            if all(p["id"] in nodes and records[p["id"]]["revision"] == p["revision"] for p in premises):
                nodes[target["id"]][polarity + "_supports"].append([p["id"] for p in premises])
    return {"scope": scope, "nodes": project(nodes, withdrawn), "conditional_assumptions": sorted(set(assumptions) - withdrawn),
            "semantics": "signed least fixed points; explicit assumptions remain conditional; conflicts block unconditional use"}
