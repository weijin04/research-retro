"""The everyday discovery command composes existing packet/worker/judgment tools."""
from __future__ import annotations

import json
import shlex

from research_harness.common import atomic_json, digest, now
from research_harness.config import owned
from research_harness.triage import Triage


def run(unit, query="", limit=12, offset=None, worker=None, question=None, overview=False):
    triage = Triage(unit)
    session = unit.store.get("workflow:project")["data"]
    worker = worker or session.get("worker")
    if overview or not worker:
        survey = triage.workflow.discover(query, limit, offset or 0)
        survey["next"] = "Use discover --worker dsh, a configured JSON worker command, or give triage prepare's packet to your host worker."
        return survey

    # The cursor belongs to material navigation, not scientific completion.
    progress_path = owned(unit.workspace, "discovery/progress.json")
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
    key = digest({"query": query, "question": question or session["goal"], "inventory": session.get("inventory_signature")})
    previous = progress.get(key, {})
    if offset is None and previous.get("exhausted"):
        return {"material_pass_exhausted": True, "scientific_reconstruction_complete": False,
                "brief": previous["brief"], "queue": triage.run("queue", limit=limit),
                "next": "Investigate remaining candidates; change the question/query or use --offset 0 to revisit this pass."}
    offset = previous.get("next_offset", 0) if offset is None else offset
    survey = triage.workflow.discover(query, limit, offset)
    prepared = triage.prepare({"materials": [{"path": c["uri"]} for c in survey["candidates"]],
                               "bytes_per_file": 4000, "question": question or session["goal"]})
    packet = triage._packet(prepared["packet"])
    result = {"packet": prepared, "worker": worker, "offset": offset,
              "next_offset": survey["next_offset"], "material_pass_exhausted": survey["next_offset"] is None,
              "scientific_reconstruction_complete": False, "at": now()}
    items = []
    if packet["materials"]:
        command = worker_command(worker, packet, prepared["path"])
        generated = triage.generate({"packet": prepared["packet"], "command": command, "timeout_s": 900})
        proposals = json.loads(owned(unit.workspace, generated["input"]).read_text())
        # Enabling a worker does not expand the workspace's Jev permission.
        proposals["use_jev"] = bool(session.get("jev", {}).get("local_judgments"))
        judged = triage.judge(proposals)
        ids = set(judged["receipts"] + judged["cached"])
        items = [i for i in triage.run("queue", limit=None)["items"] if i["receipt"] in ids]
        result.update(candidates=items, judgments=judged, generated=generated)
    else:
        result.update(candidates=[], note="This batch has no readable text. Unread materials remain available for host/domain tools.")
    directory = owned(unit.workspace, "discovery/" + prepared["packet"])
    directory.mkdir(parents=True)
    brief = render_brief(result, items)
    (directory / "brief.md").write_text(brief, encoding="utf-8")
    result["brief"] = str(directory / "brief.md")
    atomic_json(directory / "result.json", result)
    owned(unit.workspace, "discovery/latest.md").write_text(brief, encoding="utf-8")
    atomic_json(owned(unit.workspace, "discovery/latest.json"), result)
    progress[key] = {"next_offset": survey["next_offset"], "exhausted": survey["next_offset"] is None,
                     "brief": result["brief"]}
    atomic_json(progress_path, progress)
    result["next"] = "Read the brief, investigate consequential candidates against originals, and record the resulting understanding. Run discover again for the next material batch."
    return result


def worker_command(worker, packet, packet_path):
    """dsh is an optional adapter; every other worker uses JSON stdin/stdout."""
    if worker != "dsh":
        return shlex.split(worker)
    encoded = json.dumps(packet, ensure_ascii=False)
    prompt = ("Act only as a candidate generator. Follow the packet's instructions. "
              "Return ONLY its candidate JSON, without markdown fences. Do not perform scientific synthesis. ")
    if len(encoded.encode()) < 100000:
        # Pass the ready text directly: no repeated file-reading agent loop needed.
        prompt += "All input is supplied below; do not use tools or read files.\n" + encoded
    else:
        prompt += "Read only this packet, then return the JSON: " + packet_path
    return ["dsh", "--profile", "headless", prompt]


def render_brief(result, items):
    lines = ["# Scientific discovery brief", "", "Candidate questions and relations for investigation; these are not scientific conclusions.", "",
             f"Material batch: {result['packet']['materials']} readable files; {result['packet']['partial']} partial captures.", ""]
    for item in items:
        lines.extend(["## " + item["title"], "", "Target: " + item["target"]["text"], "",
                      "Local signal: " + item["answer"].get("choice", item["status"]) + " (" + item["kind"] + ")", ""])
        if item["why_proposed"]:
            lines.extend(["Worker's proposed connection: " + item["why_proposed"], ""])
        if item["next_check"]:
            lines.extend(["Suggested original check: " + item["next_check"], ""])
        lines.extend(["Sources: " + "; ".join(dict.fromkeys(s["path"] for s in item["sources"])), "",
                      "Receipt for record.triage_receipts: `" + item["receipt"] + "`", ""])
    if not items:
        lines.extend(["No scientific candidate proposed in this batch. This does not establish absence in the project.", ""])
    if result["packet"]["unread"]:
        lines.extend(["Unread material for host/domain tools:", ""])
        lines.extend("- " + i["path"] + ": " + i["reason"] for i in result["packet"]["unread"])
    lines.extend(["", "Investigate the useful candidates, revise the scientific map when warranted, and record findings. Continue discovery separately from focused reasoning.", ""])
    return "\n".join(lines)
