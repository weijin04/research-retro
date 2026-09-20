"""Deterministic context compilation; mandatory material is never dropped."""
import hashlib
import json
import re


def kind_key(kind):
    return re.sub(r"[^a-z0-9]", "", kind.lower())


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def snapshot(store):
    # Read current objects and event revision in one SQLite snapshot.
    with store._db() as db:
        db.execute("BEGIN")
        records = sorted(store._all(db).values(), key=lambda r: r["id"])
        revision = db.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]
    return records, revision


def build_context(store, task=None, budget_chars=12000):
    if not isinstance(budget_chars, int) or budget_chars <= 0:
        raise ValueError("budget_chars must be positive")
    records, revision = snapshot(store)
    mandatory_kinds = {"goal", "projectcontract", "correction", "negativeknowledge", "counterevidence", "auditcase", "auditresult", "claim", "inference", "assumption", "gap", "coverage"}
    items = []
    for record in records:
        kind = kind_key(record["kind"])
        data = record["data"]
        mandatory = kind in mandatory_kinds or bool(data.get("counterevidence") or data.get("mandatory") or data.get("opposes"))
        items.append({**record, "mandatory": mandatory, "role": kind,
                      "inclusion_reason": "mandatory goal/correction/counterevidence/current judgment" if mandatory else "supporting project state"})
    mandatory = [i for i in items if i["mandatory"]]
    optional = [i for i in items if not i["mandatory"]]
    required = sum(len(encoded(i)) for i in mandatory)
    selected = list(mandatory)
    used = required
    excluded = []
    for item in optional:
        size = len(encoded(item))
        if used + size <= budget_chars:
            selected.append(item)
            used += size
        else:
            excluded.append({"id": item["id"], "revision": item["revision"], "reason": "optional item exceeds character budget"})
    # Each chunk is independently bounded. Oversized objects are serialized into
    # exact contiguous fragments, never summarized or silently truncated.
    chunks = []
    for item in selected:
        payload = encoded(item)
        count = (len(payload) + budget_chars - 1) // budget_chars
        for index in range(count):
            chunks.append({"id": item["id"], "revision": item["revision"], "part": index + 1,
                           "parts": count, "format": "json_fragment", "content": payload[index*budget_chars:(index+1)*budget_chars]})
    packet = {"schema_version": 1, "state_revision": revision, "task": task,
              "budget_chars": budget_chars, "required_chars": required, "selected_chars": used,
              "budget_status": "requires_multiple_chunks" if used > budget_chars else "within_budget",
              "items": selected, "excluded": excluded, "chunks": chunks,
              "read_set": {i["id"]: i["revision"] for i in selected}}
    packet["content_hash"] = hashlib.sha256(encoded(packet).encode()).hexdigest()
    return packet
