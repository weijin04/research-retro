"""Host-led reconstruction, using the existing store, locators and signed support.

The host supplies scientific constructions. This module supplies the working
loop, selective contexts, revision consequences and the three public views.
"""
from __future__ import annotations

import copy
import json
import re
import uuid
from html import escape
from collections import Counter, defaultdict
from importlib.resources import files
from pathlib import Path

from research_harness.common import HarnessError, atomic_json, canonical, digest, now
from research_harness.config import owned
from research_harness.diagnosis.support import project
from research_harness.storage import ConflictError
from research_harness import semantic
from research_harness.ingest.service import asset_signals

SESSION = "workflow:project"
TYPES = {"question", "object", "attempt", "observation", "assumption", "claim", "route", "turn", "gap", "asset"}
STATUSES = {"observed", "conditional", "supported", "open", "untested", "paused", "rejected", "withdrawn", "superseded", "implementation_failed"}
READING_ORDER = ("turn", "question", "route", "gap", "object", "attempt", "claim", "observation", "assumption", "asset")


def node_refs(data):
    return data.get("requires", []) + [r for groups in (data.get("supports", []), data.get("counters", [])) for group in groups for r in group]


def source_index(records):
    """Resolve historical filenames without rewriting the original bytes."""
    sources = defaultdict(list)
    for r in records:
        if r["kind"] == "artifact":
            d = r["data"]
            sources[d["path"]].append({"artifact_id": r["id"], "revision": r["revision"],
                "blob": "store/blobs/" + d["sha256"], "identity_scope": d["identity_scope"],
                "byte_range": d["byte_range"], "original_size_bytes": d["source_after"]["size"], "live_state": d["read_state"]})
        for loc in r["data"].get("source_locators", []):
            entry = {"artifact_id": loc["artifact_id"], "revision": loc["artifact_revision"],
                "blob": "store/blobs/" + loc["content_identity"]["digest"], "identity_scope": loc["content_identity"]["scope"]}
            if not any(e["blob"] == entry["blob"] for e in sources[loc["uri"]]):
                sources[loc["uri"]].append(entry)
        for check in r["data"].get("review", {}).get("checks", []):
            blob = "store/blobs/" + check["sha256"]
            entry = next((e for e in sources[check["path"]] if e["blob"] == blob and "used_by" in e), None)
            if entry is None:
                entry = {"blob": blob, "identity_scope": "whole_file", "used_by": [],
                         "origin": "host-generated check; not an original scientific source"}
                sources[check["path"]].append(entry)
            entry["used_by"].append({"id": r["id"], "revision": r["revision"],
                "context": r["data"]["review"]["context"],
                "captured_at": check.get("captured_at", r["data"]["review"]["at"])})
    return {"sources": dict(sorted(sources.items())),
            "boundary": "Resolve a relative reference against its original parent path. An absent entry is not captured, not a nonexistent source. A captured byte segment is not the full file. A path may have several versions: choose the exact blob from the relevant node's source_locators/review.checks or the used_by revision/context; array order does not select a version."}


def projection(records):
    """Project declared evidence dependencies; keep model advice separate."""
    records = {r["id"]: r for r in records}
    nodes = {i: r for i, r in records.items() if r["kind"] == "research_node"}
    stale, field_reviews = {}, {}
    for i, r in nodes.items():
        d = r["data"]
        reasons = []
        for loc in d.get("source_locators", []):
            a = records.get(loc["artifact_id"])
            if not a or a["revision"] != loc["artifact_revision"] or a["data"].get("read_state") != "read":
                reasons.append("source:" + loc["artifact_id"])
        for ref in d.get("requires", []):
            if records.get(ref["id"], {}).get("revision") != ref["revision"]:
                reasons.append("dependency:" + ref["id"])
        field_reviews[i] = semantic.assessment(r, records)
        stale[i] = reasons
    while True:
        added = False
        for i, r in nodes.items():
            if not stale[i] and any(stale.get(ref["id"]) for ref in r["data"].get("requires", [])):
                stale[i] = ["stale required context"]
                added = True
        if not added:
            break
    graph = {}
    revoked = set()
    for i, r in nodes.items():
        d = r["data"]
        if stale[i] or d["status"] in {"rejected", "withdrawn", "superseded"}:
            revoked.add(i)
        graph[i] = {"positive_witness": d["type"] in {"observation", "assumption"} and d["status"] in {"observed", "conditional", "supported"}}
        for field, polarity in (("supports", "positive"), ("counters", "negative")):
            graph[i][polarity + "_supports"] = [[ref["id"] for ref in group] for group in d.get(field, [])
                if group and all(ref["id"] in nodes and nodes[ref["id"]]["revision"] == ref["revision"] for ref in group)]
    while True:
        support = project(graph, revoked)
        pending = {i for i, r in nodes.items() if stale[i] or support[i]["status"] == "conflict" or
                   (r["data"].get("supports") and not support[i]["usable_positive"] and r["data"]["status"] not in {"rejected", "withdrawn", "superseded"})}
        added = {i for i, r in nodes.items() if i not in revoked and any(ref["id"] in pending | revoked for ref in r["data"].get("requires", []))}
        if not added:
            break
        for i in added:
            stale[i].append("required interpretation lost eligibility")
        revoked |= added
    result = {}
    for i, r in nodes.items():
        d = r["data"]
        s = support[i]
        broken = bool(d.get("supports")) and not s["usable_positive"] and d["status"] not in {"rejected", "withdrawn", "superseded"}
        pending = bool(stale[i]) or broken or s["status"] == "conflict"
        context = records.get(d.get("review", {}).get("context"), {}).get("data", {})
        locids = {loc["id"] for loc in d.get("source_locators", [])}
        roles = [m["role"] for m in context.get("materials", []) if m["locator"]["id"] in locids]
        basis = "history_only" if roles and set(roles) == {"history"} else "selected_original_spans" if roles else "declared_derivation" if node_refs(d) else "host_map_without_original_spans"
        result[i] = {**r, "current": {**s, "needs_review": pending,
                    "semantic_review": field_reviews[i],
                    "source_basis": basis,
                    "reasons": stale[i] + (["no usable declared support path"] if broken else []),
                    "eligibility": "needs_review" if pending else "historical" if d["status"] in {"withdrawn", "superseded"} else "scoped_host_judgment"}}
    return result


def render(records, revision, project_id, completion=None):
    nodes = projection(records)
    session = next((r["data"] for r in records if r["id"] == SESSION), {})
    completion = completion or {"status": "draft", "reason": "Host coverage and handoff assessment not yet published"}
    state = {"format": "research-retro/3", "projection_policy": semantic.POLICY, "project": project_id, "state_revision": revision,
             "goal": session.get("goal"), "scope_history": session.get("scope_history", []),
             "spine": session.get("spine"),
             "completion": completion, "nodes": sorted(nodes.values(), key=lambda r: READING_ORDER.index(r["data"]["type"])),
             "boundary": "Named host reconstruction, qualified by the recorded scope and checks. Support is not truth probability."}
    lines = ["# " + project_id + " — Research Retro", "", f"State r{revision} · {completion['status']}", "",
             session.get("goal", ""), "", "Scientific questions may remain open in a reconstructed project. Read scope and current eligibility with each statement.", ""]
    for key in ("scientific_problem", "continuation", "blockers", "limitations"):
        if completion.get(key):
            value = completion[key]
            lines += [key.replace("_", " ").capitalize() + ": " + ("; ".join(value) if isinstance(value, list) else str(value)), ""]
    nav = ["# Original-material navigation", "", f"Frozen state r{revision}. Paths label historical sources; blob links work without the original project.", "",
           "[SOURCE_INDEX.json](SOURCE_INDEX.json) maps captured original paths to portable bytes. References inside originals are historical; uncaptured references remain unavailable in this bundle.", ""]
    for typ in READING_ORDER:
        group = [r for r in nodes.values() if r["data"]["type"] == typ]
        if not group:
            continue
        lines += ["## " + typ, ""]
        for r in group:
            d, c = r["data"], r["current"]
            lines += [f'<span id="{escape(r["id"], quote=True)}"></span>', f"### {d['title']} ({r['id']})", "", f"{d['status']} · {c['eligibility']} · {c['source_basis']} · revision {r['revision']}", "", d["statement"], "",
                      "Scope: " + canonical(d["scope"]), "", "Reasoning: " + d["rationale"], ""]
            if c["needs_review"]:
                lines += ["REASSESS BEFORE USE: " + "; ".join(c["reasons"] or ["conflicting support"]), ""]
            for key, value in semantic.actions(d).items():
                lines += ["Recorded action (" + key + "): " + (value if isinstance(value, str) else canonical(value)), ""]
            if d.get("details"):
                lines += [f"[Detailed construction and data](index.html#{r['id']}) · [Machine-readable state](SCIENTIFIC_STATE.json)", ""]
            if node_refs(d) or d.get("links"):
                lines += ["Connections: " + ", ".join(f'[{ref["id"]} v{ref["revision"]}](#{ref["id"]})' for ref in node_refs(d)) +
                          ("; navigation: " + ", ".join(f"[{i}](#{i})" for i in d["links"]) if d.get("links") else ""), ""]
            nav += [f'<span id="{escape(r["id"], quote=True)}"></span>', "## " + d["title"] + " — " + r["id"], "", d["statement"], ""]
            for index, loc in enumerate(d.get("source_locators", [])):
                span = loc["locator"]
                link = "store/blobs/" + loc["content_identity"]["digest"]
                label = f"{loc['uri']} ({span['type']} {span['start']}–{span['end']})"
                if loc["content_identity"]["scope"] == "captured_segment":
                    bounds = loc.get("extensions", {}).get("captured_byte_range")
                    label += f" [PARTIAL: lines relative to captured bytes {bounds if bounds is not None else 'listed in SOURCE_INDEX.json'}]"
                nav += [f"- [{label}]({link})"]
                if index < 3:
                    lines += [f"Source: [{label}]({link})", ""]
            if len(d.get("source_locators", [])) > 3:
                lines += [f"[All {len(d['source_locators'])} original spans](NAVIGATION.md#{r['id']})", ""]
            nav += [""]
            for check in d.get("review", {}).get("checks", []):
                nav += [f"- [Host check: {check['path']}](store/blobs/{check['sha256']})"]
    payload = json.dumps(state, ensure_ascii=False).replace("<", "\\u003c")
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Research Retro</title><style>body{margin:0;background:#f3f4ef;color:#162d2d;font:16px/1.65 system-ui}header,main{max-width:1100px;margin:auto;padding:28px}header{border-bottom:3px solid #1a726c}h1{font-size:34px;margin:8px 0}input,select{font:inherit;padding:10px;border:1px solid #b4c6bc;border-radius:6px}input{width:min(65%,650px)}article{background:#fff;padding:24px;margin:18px 0;border-left:5px solid #2b8076;border-radius:8px}article.stale{border-color:#b84429}small,.meta{color:#526861}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf2ef;padding:16px}a{color:#17675e}summary{cursor:pointer}h2{margin:0;font-size:22px}.tag{font-size:13px;background:#e7eee7;padding:4px 8px;margin:0 6px 0 0}p{white-space:pre-wrap}</style>
<header><small>RESEARCH RETRO · LOCAL SCIENTIFIC STATE</small><h1 id="title"></h1><p id="goal"></p><p id="version"></p><p id="assessment"></p><input id="query" placeholder="Find a question, route, condition or source"><select id="kind"><option value="">All objects</option></select><p><a href="MAINLINE.md">Mainline</a> · <a href="NAVIGATION.md">Originals</a> · <a href="SCIENTIFIC_STATE.json">Agent state</a></p></header><main id="cards"></main>
<script id="state" type="application/json">""" + payload + """</script><script>
const s=JSON.parse(document.getElementById('state').textContent),el=id=>document.getElementById(id),esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
el('title').textContent=s.project;el('goal').textContent=s.goal;el('version').textContent='r'+s.state_revision+' · '+s.completion.status+' · '+s.boundary;
el('assessment').textContent=['scientific_problem','continuation','blockers','limitations'].filter(k=>s.completion[k]&&s.completion[k].length).map(k=>k.replaceAll('_',' ')+': '+(Array.isArray(s.completion[k])?s.completion[k].join('; '):s.completion[k])).join(String.fromCharCode(10));
[...new Set(s.nodes.map(n=>n.data.type))].forEach(k=>{let o=document.createElement('option');o.value=k;o.textContent=k;el('kind').append(o)});
function draw(){let q=el('query').value.toLowerCase(),k=el('kind').value;el('cards').innerHTML=s.nodes.filter(n=>(!k||n.data.type===k)&&JSON.stringify(n).toLowerCase().includes(q)).map(n=>{let d=n.data,c=n.current;return '<article id="'+esc(n.id)+'" class="'+(c.needs_review?'stale':'')+'"><span class="tag">'+esc(d.type)+'</span><span class="tag">'+esc(d.status)+'</span><span class="tag">'+esc(c.eligibility)+'</span><span class="tag">'+esc(c.source_basis)+'</span><h2>'+esc(d.title)+'</h2><small>'+esc(n.id)+' · v'+n.revision+'</small><p>'+esc(d.statement)+'</p><p>'+esc(d.rationale)+'</p><details><summary>Conditions, dependencies and originals</summary><pre>'+esc(JSON.stringify({scope:d.scope,details:d.details,action:d.action,actions:d.actions,next:d.next,checks:d.review?.checks,supports:d.supports,counters:d.counters,requires:d.requires,current:c},null,2))+'</pre>'+(d.links||[]).map(i=>'<a href="#'+esc(i)+'">'+esc(i)+'</a> ').join('')+(d.source_locators||[]).map(l=>{let h=l.content_identity.digest;return '<p><a href="store/blobs/'+h+'">'+esc(l.uri)+'</a> · '+esc(l.locator.type)+' '+l.locator.start+'–'+l.locator.end+(l.content_identity.scope==='captured_segment'?' · PARTIAL bytes '+esc(JSON.stringify((l.extensions||{}).captured_byte_range||'see source index')):'')+'</p>'}).join('')+'</details></article>'}).join('')||'<p>No matching records.</p>'}el('query').oninput=draw;el('kind').onchange=draw;draw();
function followHash(){if(!location.hash)return;el('query').value='';el('kind').value='';draw();let target=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(target){target.querySelector('details').open=true;target.scrollIntoView()}}
addEventListener('hashchange',followHash);followHash();</script></html>"""
    from research_harness.views.spine import render_spine
    _, spine_html = render_spine(state)
    page = page.replace('<main id="cards"></main>', '<main>' + spine_html +
        '<details id="map"><summary>Detailed research map · all nodes, reasoning, history and originals</summary><div id="cards"></div></details></main>')
    page = page.replace("if(target){target.querySelector('details').open=true;target.scrollIntoView()}",
                        "if(target){el('map').open=true;let details=target.querySelector('details');if(details)details.open=true;target.scrollIntoView()}")
    page = page.replace("el('query').oninput=draw;el('kind').onchange=draw;", "el('query').oninput=()=>{el('map').open=true;draw()};el('kind').onchange=()=>{el('map').open=true;draw()};")
    return state, "\n".join(lines), "\n".join(nav), page


class Workflow:
    def __init__(self, unit):
        self.unit, self.store = unit, unit.store

    def _commit(self, records, reason, reads=None):
        return self.store.commit(records, reason, reads or {}, "workflow:" + uuid.uuid4().hex, self.store.active_policy_revision())

    def _get(self, identifier, kind):
        r = self.store.get(identifier)
        if r["kind"] != kind:
            raise HarnessError("invalid_contract", "Expected " + kind)
        return r

    def start(self, goal, jev=False):
        try:
            current = self._get(SESSION, "research_session")
        except KeyError:
            receipts = [self.unit.ingest.scan(s["id"]) for s in self.unit.manifest["sources"]]
            data = {"goal": goal, "started": now(), "census": [r["id"] for r in receipts], "inventory_signature": self._inventory_signature(),
                    "scope_history": [{"goal": goal, "reason": "initial discovery scope; revisable after reading", "at": now()}]}
            self._commit([{"id": SESSION, "kind": "research_session", "data": data}], "begin host-led whole-project discovery")
        else:
            if goal != current["data"]["goal"]:
                raise ConflictError("A session exists; use workflow scope with a reason to revise its goal")
        if jev:
            self._enable_jev(local=True)
        checks = {"jev_calls": 0, "mode": "explicit requests only"}
        return {"session": self.store.get(SESSION), "discovery": self.discover(), "semantic_checks": checks,
                "next": "Read the host guide. Prepare material packets for a cheap worker, use upstream local judgments to select scientific investigations, then record findings and select a short spine."}

    def _enable_jev(self, local=False):
        session = self._get(SESSION, "research_session")
        previous = session["data"].get("jev", {})
        if not previous.get("enabled") or (local and not previous.get("local_judgments")):
            session["data"]["jev"] = {"enabled": True, "authorized_at": now(),
                "local_judgments": local or previous.get("local_judgments", False),
                "scope": "explicitly supplied local judgment state and questions" if local else "node fields and linked summaries"}
            self._commit([session], "host authorized explicit Jev requests", {SESSION: session["revision"]})

    def judge(self, document):
        """Host-selected typed questions; no automatic upload, ranking or gating."""
        if document.get("authorize_egress") is True:
            self._enable_jev(local=True)
        if not self._get(SESSION, "research_session")["data"].get("jev", {}).get("local_judgments"):
            raise HarnessError("permission_denied", "Local judgments require start --jev or judge authorize_egress:true. Historical field-only authorization is not expanded automatically.")
        questions = document.get("questions")
        if not document.get("purpose") or "state" not in document or not isinstance(questions, dict) or not questions:
            raise HarnessError("invalid_contract", "judge requires purpose, state and typed questions")
        for q in questions.values():
            if not isinstance(q, dict) or q.get("type") not in {"noul", "choice", "score"} or not q.get("instructions"):
                raise HarnessError("invalid_contract", "Use a Noul, Choice or Score question with instructions")
            if q["type"] == "choice" and (not isinstance(q.get("criteria"), dict) or not q["criteria"]):
                raise HarnessError("invalid_contract", "Choice needs named criteria")
            if q["type"] == "score" and (not isinstance(q.get("criteria"), list) or not 2 <= len(q["criteria"]) <= 10):
                raise HarnessError("invalid_contract", "Score needs 2 to 10 ordered criteria")
        reads = document.get("revisions", {})
        for i, revision in reads.items():
            if self.store.get(i)["revision"] != revision:
                raise ConflictError("Judgment input changed: " + i)
        result = semantic.evaluate(document["state"], owned(self.unit.workspace, "jev"),
                                   questions=questions, purpose=document["purpose"])
        result["read_set"] = reads
        atomic_json(owned(self.unit.workspace, "jev/" + result["id"].replace(":", "-") + ".json"), result)
        self._commit([{"id": result["id"], "kind": "semantic_review", "data": result}], "retain explicit local judgment", reads)
        return result

    def semantic_review(self, document):
        """Optional batch of the historical premise/action questions."""
        if document.get("authorize_egress") is True:
            self._enable_jev()
        if not self._get(SESSION, "research_session")["data"].get("jev", {}).get("enabled"):
            raise HarnessError("permission_denied", "Enable Jev with start --jev or semantic-review authorize_egress:true")
        identifiers = document.get("nodes")
        records = {r["id"]: r for r in self.store.list()}
        if identifiers is not None and (not isinstance(identifiers, list) or any(records.get(i, {}).get("kind") != "research_node" for i in identifiers)):
            raise HarnessError("invalid_contract", "nodes must list existing research node IDs")
        receipts = []
        for r in records.values():
            if r["kind"] != "research_node" or (identifiers is not None and r["id"] not in identifiers):
                continue
            assessment = semantic.assessment(r, records)
            # Retain a failed/stale verdict until its actual fields change. A
            # manual review may explicitly request a fresh call, never a retry loop.
            if (identifiers is None and not assessment["suggested"]) or (assessment["receipt"] and not document.get("recheck", False)):
                continue
            state = semantic.state_for(r, records)
            read_set = {i: records[i]["revision"] for i in [r["id"], *[e["id"] for e in state["evidence"]]]}
            result = semantic.evaluate(state, owned(self.unit.workspace, "jev"))
            self._commit([{"id": result["id"], "kind": "semantic_review", "data": result}],
                         "record Jev premise and action judgments", read_set)
            receipts.append(result)
            if result["status"] != "ok":
                break
        self._invalidate_publication()
        return {"jev_calls": sum(r["jev_calls"] for r in receipts), "receipts": receipts,
                "state": self.status()}

    def scope(self, document):
        session = self._get(SESSION, "research_session")
        if document.get("revision") != session["revision"] or not document.get("reason") or not document.get("goal"):
            raise ConflictError("Scope revision requires the current session revision, new goal and reason")
        d = session["data"]
        d["goal"] = document["goal"]
        d["scope_history"].append({**document, "at": now()})
        receipt = self._commit([session], "revise investigation scope: " + document["reason"], {SESSION: session["revision"]})
        self._invalidate_publication()
        return receipt

    def refresh(self):
        self.unit.ingest.refresh()
        receipts = [self.unit.ingest.scan(s["id"]) for s in self.unit.manifest["sources"]]
        self._sync_inventory()
        self._invalidate_publication()
        return {"census": receipts, "state": self.status()}

    def _sync_inventory(self):
        session = self._get(SESSION, "research_session")
        signature = self._inventory_signature()
        if session["data"].get("inventory_signature") != signature:
            session["data"].update(inventory_signature=signature, inventory_changed_at=now())
            self._commit([session], "material inventory changed; reassess discovery coverage", {SESSION: session["revision"]})

    def _inventory_signature(self):
        # Reading/capturing a file is not new evidence; added, removed or changed
        # originals do reopen coverage. Ignore scan timestamps and read labels.
        inventory = []
        for r in self.store.list("coverage"):
            d = r["data"]
            rows = json.loads(self.store.read_blob(d["ledger_hash"]))
            inventory.append([d["source_id"], d["enumeration_complete"], d["errors"],
                [[row.get(k) for k in ("path", "size", "mtime_ns", "ctime_ns", "inode", "device")] for row in rows]])
        return digest(inventory)

    def _ledger(self):
        rows = []
        for r in self.store.list("coverage"):
            root = Path(r["data"]["root"])
            rows.extend({**row, "source_id": r["data"]["source_id"], "relative": str(Path(row["path"]).relative_to(root))} for row in json.loads(self.store.read_blob(r["data"]["ledger_hash"])))
        return rows

    def _unlinked_queue(self, rows, limit, offset=0):
        """No query/relevance score enters this independent candidate queue."""
        nodes = {r["id"]: r for r in self.store.list("research_node")}
        all_links = {loc["uri"] for r in nodes.values() for loc in r["data"].get("source_locators", [])}
        claimed, seen = set(), set()
        pending = [r["id"] for r in nodes.values() if r["data"]["type"] == "claim" and r["data"]["status"] not in semantic.INACTIVE]
        while pending:
            i = pending.pop()
            if i in seen or i not in nodes:
                continue
            seen.add(i)
            d = nodes[i]["data"]
            claimed.update(loc["uri"] for loc in d.get("source_locators", []))
            pending.extend(ref["id"] for ref in node_refs(d))
        exposures = Counter(c["uri"] for r in self.store.list("research_context")
                            for c in r["data"].get("unlinked_candidates", []))
        indexed = {r["data"]["path"]: r["data"].get("discovery_signals", []) for r in self.store.list("artifact")}
        captured = {r["data"]["path"]: r["data"]["sha256"] for r in self.store.list("artifact")
                    if r["data"]["identity_scope"] == "whole_file" and r["data"]["read_state"] == "read"}
        identities = {}
        groups = defaultdict(list)
        for row in rows:
            if row["path"] in claimed or row.get("size") is None or row["state"] == "not_in_scope":
                continue
            signals = sorted(set(asset_signals(row["relative"]) + row.get("discovery_signals", []) + indexed.get(row["path"], [])))
            candidate = {"path": row["relative"], "uri": row["path"], "source_id": row["source_id"],
                "state": row["state"], "size": row["size"], "claim_references": 0,
                "linked": row["path"] in all_links, "signals": signals,
                "reasons": ["unreferenced_by_claim"] + (["zero_references"] if row["path"] not in all_links else []) + signals,
                "context_exposures": exposures[row["path"]], "stratum": str(Path(row["relative"]).parent)}
            fingerprint = captured.get(row["path"])
            if fingerprint and fingerprint in identities:
                identities[fingerprint].setdefault("identical_byte_paths", []).append(candidate["uri"])
                continue
            if fingerprint:
                candidate["content_sha256"] = fingerprint
                identities[fingerprint] = candidate
            groups[(row["source_id"], candidate["stratum"])].append(candidate)
        def priority(c):
            return (c["context_exposures"], c["linked"], digest(c["uri"]))
        for group in groups.values():
            group.sort(key=priority)
        ordered = sorted(groups.values(), key=lambda g: priority(g[0]))
        candidates, depth = [], 0
        while len(candidates) < offset + limit and any(depth < len(g) for g in ordered):
            candidates.extend(g[depth] for g in ordered if depth < len(g))
            depth += 1
        count = sum(map(len, groups.values()))
        return {"candidates": candidates[offset:offset + limit], "total": count, "offset": offset,
                "next_offset": offset + limit if count > offset + limit else None,
                "query_independent": True, "policy": "unclaimed assets, interleaved parent directories; used only in discovery",
                "boundary": "Hints select material for reading; no importance or failure verdict. Only previously captured whole-file identities are deduplicated; equal bytes do not establish the same execution."}

    def discover(self, query="", limit=24, offset=0):
        from research_harness.triage import queue_from_records
        rows = self._ledger()
        linked = {loc["uri"] for r in self.store.list("research_node") for loc in r["data"].get("source_locators", [])}
        groups = defaultdict(list)
        for row in rows:
            if query and query.casefold() not in row["relative"].casefold():
                continue
            p = Path(row["relative"])
            groups[p.parts[0] if len(p.parts) > 1 else "(root)"].append(row)
        candidates = []
        # Interleave stable, hash-ordered strata: neither latest-summary order nor
        # a relevance rank can silently erase abandoned/unlinked material.
        for group in groups.values():
            group.sort(key=lambda row: (row["path"] in linked, digest(row["relative"])))
        depth = 0
        while len(candidates) < offset + limit and any(depth < len(g) for g in groups.values()):
            for key in sorted(groups):
                if depth < len(groups[key]):
                    row = groups[key][depth]
                    candidates.append({"path": row["relative"], "state": row["state"], "size": row.get("size"), "linked": row["path"] in linked,
                                       "reason": row.get("reason"), "stratum": key, "source_id": row["source_id"], "uri": row["path"]})
            depth += 1
        coverage = [{k: r["data"][k] for k in ("source_id", "denominator", "enumeration_complete", "errors")} for r in self.store.list("coverage")]
        families = defaultdict(list)
        for row in rows:
            if row.get("size") is not None and row["state"] != "not_in_scope":
                families[(row["source_id"], str(Path(row["relative"]).parent))].append(row)
        family_rows = []
        for (source_id, directory), group in sorted(families.items()):
            if query and not any(query.casefold() in r["relative"].casefold() for r in group):
                continue
            ordered = sorted(group, key=lambda r: (r["path"] in linked, r["relative"]))
            family_rows.append({"directory": directory, "source_id": source_id, "files": len(group),
                "unlinked": sum(r["path"] not in linked for r in group),
                "formats": dict(Counter(Path(r["relative"]).suffix or "(none)" for r in group)),
                "examples": [r["relative"] for r in ordered[:6]],
                "modified_ns_range": [min(r.get("mtime_ns", 0) for r in group), max(r.get("mtime_ns", 0) for r in group)]})
        findings = [r for r in self.store.list("research_node") if r["data"].get("details", {}).get("discovery")]
        return {"census": coverage, "strata": {key: {"files": len(g), "unlinked": sum(r["path"] not in linked for r in g)} for key, g in sorted(groups.items())},
                "judgment_queue": queue_from_records(self.store.list(), limit),
                "families": family_rows[offset:offset + limit], "family_count": len(family_rows),
                "next_family_offset": offset + limit if len(family_rows) > offset + limit else None,
                "scientific_candidates": [{"id": r["id"], "revision": r["revision"], "type": r["data"]["type"],
                    "title": r["data"]["title"], "statement": r["data"]["statement"], "status": r["data"]["status"],
                    "discovery": r["data"]["details"]["discovery"]} for r in findings],
                "candidates": candidates[offset:offset + limit], "unlinked_queue": self._unlinked_queue(rows, limit, offset),
                "matched": sum(map(len, groups.values())), "offset": offset,
                "next_offset": offset + limit if sum(map(len, groups.values())) > offset + limit else None,
                "scientific_reading_complete": False, "instruction": "Read related materials together, including history outside the current story. Record a missed question, route, contradiction or connection as an existing node with details.discovery describing the finding and investigation. Families and timestamps are navigation hints, not inferred attempts or scientific dates. Focused contexts contain only what you select."}

    def context(self, document):
        if not document.get("question") or not (document.get("materials") or document.get("focus")):
            raise HarnessError("invalid_contract", "Context requires a question and selected material spans")
        materials, reads = [], {"project:contract": self.store.get("project:contract")["revision"]}
        for item in document.get("materials", []):
            if item.get("role") not in {"evidence", "definition", "history"}:
                raise HarnessError("invalid_contract", "Each span needs evidence, definition or history role")
            path = Path(item["path"])
            if not path.is_absolute():
                path = Path(self.unit.manifest["sources"][0]["root"]) / path
            artifact = self.unit.ingest.capture(path, segment=tuple(item["bytes"]) if "bytes" in item else None)
            if item.get("sha256") and item["sha256"] != artifact["data"]["sha256"]:
                raise ConflictError("Selected original bytes changed: " + str(path))
            loc = self.unit.ingest.locator(artifact, item.get("start", 1), item.get("end"), note=item.get("why", document["question"]))
            loc["extensions"].update(captured_byte_range=artifact["data"]["byte_range"], original_size_bytes=artifact["data"]["source_after"]["size"])
            self.unit.ingest.read(loc)
            materials.append({"key": item.get("key", "m" + str(len(materials) + 1)), "role": item["role"], "locator": loc})
            reads[artifact["id"]] = artifact["revision"]
        if len({m["key"] for m in materials}) != len(materials):
            raise HarnessError("invalid_contract", "Material keys must be unique")
        for identifier in document.get("focus", []):
            r = self._get(identifier, "research_node")
            reads[identifier] = r["revision"]
        identifier = "context:" + uuid.uuid4().hex
        data = {"question": document["question"], "materials": materials, "read_set": reads, "focus": document.get("focus", []),
                "unlinked_candidates": [], "unlinked_total": 0,
                "phase": "working" if document.get("mode") == "working" else "initial", "policy_revision": self.store.active_policy_revision(),
                "prior_exposure": document.get("prior_exposure", "not declared; cooperative host, not a blind review"),
                "created": now(), "initial": None}
        data["checks"] = []
        for name in document.get("checks", []):
            path = owned(self.unit.workspace, name)
            content = path.read_bytes()
            fingerprint = self.store.put_blob(content)
            data["checks"].append({"path": str(path), "sha256": fingerprint, "blob_refs": [fingerprint],
                                   "captured_at": now(),
                                   "authority": "host-reported check; inspect code and output"})
        data["input_hash"] = digest(data)
        self._commit([{"id": identifier, "kind": "research_context", "data": data}], "select problem-specific original locators", reads)
        return self.packet(identifier)

    def packet(self, id):
        r = self._get(id, "research_context")
        d = r["data"]
        materials = [{**m, "text": self.unit.ingest.read(m["locator"]), "untrusted": True} for m in d["materials"] if m["role"] != "history" or d["phase"] in {"working", "revealed", "applied"}]
        partial = [{"key": m["key"], "captured_bytes": m["locator"].get("extensions", {}).get("captured_byte_range"),
                    "original_size_bytes": m["locator"].get("extensions", {}).get("original_size_bytes")}
                   for m in materials if m["locator"]["content_identity"]["scope"] == "captured_segment"]
        return {"id": id, "question": d["question"], "phase": d["phase"], "input_hash": d["input_hash"], "read_set": d["read_set"],
                "unlinked_candidates": d.get("unlinked_candidates", []), "unlinked_total": d.get("unlinked_total", 0),
                "materials": materials, "hidden_history_spans": sum(m["role"] == "history" for m in d["materials"]) if d["phase"] in {"initial", "sealed"} else 0,
                "partial_sources": partial, "capture_note": "A byte segment may truncate a dataset. Capture complete input needed for an actual handoff calculation; line numbers inside segments are relative to the captured bytes.",
                "prior_exposure": d["prior_exposure"], "initial": d["initial"],
                "focus": [self.store.get(i, d["read_set"][i]) for i in d["focus"]],
                "apply_template": {"context": id, "input_hash": d["input_hash"], "reviewer": "", "analysis": "", "alternatives": [], "nodes": []}}

    def _fresh(self, r):
        d = r["data"]
        if d["policy_revision"] != self.store.active_policy_revision():
            raise ConflictError("Context policy changed")
        for key, revision in d["read_set"].items():
            original = self.store.get(key, revision)
            if original["kind"] == "artifact":
                a = original["data"]
                self.unit.ingest.capture(a["path"], segment=tuple(a["byte_range"]) if a["identity_scope"] == "captured_segment" else None)
            if self.store.get(key)["revision"] != revision:
                raise ConflictError("Context dependency changed: " + key)

    def seal(self, id, document):
        r = self._get(id, "research_context")
        self._fresh(r)
        if r["data"]["phase"] != "initial" or not document.get("analysis") or not document.get("alternatives"):
            raise HarnessError("invalid_contract", "Record an initial construction and competing explanations before revealing history")
        r["data"].update(initial=document, phase="sealed")
        self._commit([r], "seal host initial scientific construction", {id: r["revision"], **r["data"]["read_set"]})
        return self.packet(id)

    def reveal(self, id):
        r = self._get(id, "research_context")
        self._fresh(r)
        if r["data"]["phase"] not in {"sealed", "revealed"}:
            raise HarnessError("invalid_contract", "Seal the initial interpretation first")
        r["data"]["phase"] = "revealed"
        self._commit([r], "reveal historical interpretations separately from definitions", {id: r["revision"]})
        return self.packet(id)

    def apply(self, document):
        context = self._get(document["context"], "research_context")
        self._fresh(context)
        d = context["data"]
        if d["phase"] not in {"working", "revealed"} or document.get("input_hash") != d["input_hash"]:
            raise ConflictError("Apply must bind a working/revealed context and its original input hash")
        if not document.get("reviewer") or not document.get("analysis") or not document.get("nodes"):
            raise HarnessError("scientific_test_invalid", "Provide a named host, completed scientific analysis and reconstructed nodes")
        existing = {r["id"]: r for r in self.store.list()}
        triage_receipts = document.get("triage_receipts", [])
        if any(existing.get(i, {}).get("kind") != "semantic_review" or not existing[i]["data"].get("candidate") for i in triage_receipts):
            raise HarnessError("invalid_contract", "triage_receipts must refer to retained upstream candidate judgments")
        incoming = document["nodes"]
        identifiers = [n["id"] for n in incoming]
        if len(set(identifiers)) != len(identifiers):
            raise HarnessError("invalid_contract", "Duplicate node IDs")
        versions = {i: existing[i]["revision"] + 1 if i in existing else 1 for i in identifiers}
        reads = {**d["read_set"], context["id"]: context["revision"]}
        def ref(identifier):
            if identifier in versions:
                return {"id": identifier, "revision": versions[identifier]}
            if identifier not in d["focus"]:
                raise HarnessError("invalid_contract", "Include used research nodes in context.focus: " + identifier)
            return {"id": identifier, "revision": reads[identifier]}
        materials = {m["key"]: m for m in d["materials"]}
        records, updated = [], []
        for node in incoming:
            i = node["id"]
            if i in existing:
                if existing[i]["kind"] != "research_node" or i not in d["focus"]:
                    raise ConflictError("Existing nodes must be selected in context.focus before revising: " + i)
                updated.append(i)
            if node.get("type") not in TYPES or node.get("status") not in STATUSES or any(not node.get(k) for k in ("title", "statement", "scope", "rationale")):
                raise HarnessError("invalid_contract", "Invalid research node: " + i,
                    {"type": node.get("type"), "allowed_types": sorted(TYPES), "status": node.get("status"), "allowed_statuses": sorted(STATUSES),
                     "missing": [k for k in ("title", "statement", "scope", "rationale") if not node.get(k)]})
            locators = [materials[key]["locator"] for key in node.get("sources", [])]
            if node["type"] == "observation" and not locators:
                raise HarnessError("scientific_test_invalid", "Observations need original material spans")
            if node["type"] == "claim" and node["status"] == "supported" and not node.get("supports"):
                raise HarnessError("scientific_test_invalid", "A supported claim needs declared scientific support paths")
            links = node.get("links", [])
            if any(i not in versions and existing.get(i, {}).get("kind") != "research_node" for i in links):
                raise HarnessError("invalid_contract", "Navigation link has no research node")
            data = {k: copy.deepcopy(node[k]) for k in ("type", "status", "title", "statement", "scope", "rationale", "details", "links", "action", "actions", "next") if k in node}
            data.update(source_locators=locators, source_dependencies=[loc["artifact_id"] for loc in locators],
                        requires=[ref(i) for i in node.get("requires", [])],
                        supports=[[ref(i) for i in group] for group in node.get("supports", [])],
                        counters=[[ref(i) for i in group] for group in node.get("counters", [])],
                        review={"context": context["id"], "input_hash": d["input_hash"], "reviewer": document["reviewer"], "at": now(),
                                "analysis": document["analysis"], "alternatives": document.get("alternatives", []),
                                "checks": d.get("checks", []), "triage_receipts": triage_receipts,
                                "authority": "accountable_host_judgment"})
            records.append({"id": i, "kind": "research_node", "data": data})
        context["data"].update(phase="applied", submitted_nodes=identifiers)
        receipt = self._commit([*records, context], "reconstruct or revise scientific understanding: " + document["analysis"][:200], reads)
        self._invalidate_publication()
        checks = {"jev_calls": 0, "receipts": [], "mode": "explicit requests only"}
        return {"receipt": receipt, "updated": updated, "semantic_checks": checks, "state": self.status(),
                "next": "Inspect changed-node impact, search undeclared narrative dependencies, and review residual material before publishing."}

    def record(self, document):
        """Save a completed host investigation without a mandatory staged review."""
        nodes = document.get("nodes", [])
        if not nodes or not document.get("reviewer") or not document.get("analysis"):
            raise HarnessError("invalid_contract", "record requires nodes, reviewer and completed analysis")
        used = {n["id"] for n in nodes}
        for n in nodes:
            used.update(n.get("requires", []))
            used.update(i for field in ("supports", "counters") for group in n.get(field, []) for i in group)
        existing = {r["id"]: r for r in self.store.list("research_node")}
        focus = sorted(used & existing.keys())
        for i in focus:
            if document.get("revisions", {}).get(i) != existing[i]["revision"]:
                raise ConflictError("Include the inspected revision in revisions for " + i)
        packet = self.context({**document, "mode": "working", "focus": focus})
        return self.apply({**document, "context": packet["id"], "input_hash": packet["input_hash"]})

    def spine(self, document):
        """Select the human reading order; content always comes from current nodes."""
        sections = document.get("sections")
        if not isinstance(sections, list) or not sections:
            raise HarnessError("invalid_contract", "spine needs sections with title and node IDs")
        reads = {}
        for section in sections:
            if not section.get("title") or not isinstance(section.get("nodes"), list) or not section["nodes"]:
                raise HarnessError("invalid_contract", "Each spine section needs a title and node IDs")
            for i in section["nodes"]:
                reads[i] = self._get(i, "research_node")["revision"]
        session = self._get(SESSION, "research_session")
        reads[SESSION] = session["revision"]
        session["data"]["spine"] = {"sections": [{"title": s["title"], "nodes": s["nodes"]} for s in sections]}
        receipt = self._commit([session], "arrange the scientific spine", reads)
        self._invalidate_publication()
        return {"receipt": receipt, "spine": session["data"]["spine"]}

    def impact(self, id, query="", limit=30):
        nodes = self.store.list("research_node")
        target = self._get(id, "research_node")
        affected, frontier = set(), {id}
        while frontier:
            added = {r["id"] for r in nodes if r["id"] not in affected | {id} and {ref["id"] for ref in node_refs(r["data"])} & frontier}
            affected |= added
            frontier = added
        terms = set(re.findall(r"[\w-]{3,}", (query or target["data"]["title"]).casefold()))
        candidates = [{"id": r["id"], "title": r["data"]["title"]} for r in nodes if r["id"] not in affected | {id} and
                      any(t in canonical(r["data"]).casefold() for t in terms)]
        return {"changed": id, "declared_dependents": sorted(affected), "undeclared_candidates": candidates[:limit],
                "candidate_count": len(candidates), "boundary": "Lexical discovery only. The host must search semantic aliases and independently sample excluded/unlinked originals.",
                "current": {i: r["current"] for i, r in projection(self.store.list()).items() if i in affected | {id}}}

    def show(self, id):
        node = projection(self.store.list())[id]
        return {"node": node, "originals": [{"locator": loc, "text": self.unit.ingest.read(loc)} for loc in node["data"].get("source_locators", [])],
                "history_revisions": [r["revision"] for r in self.store.history(id)]}

    def status(self):
        nodes = projection(self.store.list())
        reviews = self.store.list("semantic_review")
        return {"state_revision": self.store.current_revision(), "nodes": len(nodes),
                "jev_calls": sum(r["data"].get("jev_calls", 0) for r in reviews),
                "jev_successful_calls": sum(r["data"].get("jev_calls", 0) for r in reviews if r["data"].get("status") == "ok"),
                "types": dict(Counter(r["data"]["type"] for r in nodes.values())),
                "needs_review": [i for i, r in nodes.items() if r["current"]["needs_review"]],
                "coverage_risks": [{"id": i, "basis": r["current"]["source_basis"]} for i, r in nodes.items()
                                   if r["current"]["source_basis"] in {"history_only", "host_map_without_original_spans"}],
                "open_questions": [i for i, r in nodes.items() if r["data"]["type"] in {"question", "gap"} and r["data"]["status"] in {"open", "untested", "paused"}],
                "publication": self._completion(nodes), "next": "Review sources and unresolved issues; an empty declared queue is not proof of whole-project coverage."}

    def assess(self, document):
        required = ("reviewer", "coverage", "residual_review", "handoff", "limitations", "scientific_problem", "continuation")
        if any(k not in document for k in required) or not document["reviewer"]:
            raise HarnessError("invalid_contract", "Assessment requires reviewer, coverage, residual_review, handoff, limitations, scientific_problem and continuation")
        nodes = self.store.list("research_node")
        reads = {r["id"]: r["revision"] for r in nodes}
        reads[SESSION] = self.store.get(SESSION)["revision"]
        identifier = "assessment:" + uuid.uuid4().hex
        self._commit([{"id": identifier, "kind": "research_assessment", "data": {**document, "read_set": reads, "at": now(),
                       "authority": "host-reported acceptance; inspect actual tasks and outputs"}}], "record coverage, residual discovery and performed handoff tasks", reads)
        self._invalidate_publication()
        return {"id": identifier, "completion": self._completion(projection(self.store.list()))}

    def _completion(self, nodes):
        assessments = self.store.list("research_assessment")
        if not assessments:
            return {"status": "draft", "blockers": ["coverage, residual discovery and cold handoff not yet assessed"]}
        latest = max(assessments, key=lambda r: r["data"]["at"])
        d = latest["data"]
        current = {r["id"]: r["revision"] for r in self.store.list()}
        blockers = []
        outdated = any(current.get(i) != rev for i, rev in d["read_set"].items()) or set(nodes) != set(d["read_set"]) - {SESSION}
        if outdated:
            blockers.append("assessment predates changed scientific state or scope")
        blockers += ["needs review: " + i for i, r in nodes.items() if r["current"]["needs_review"]]
        if not d["coverage"].get("sufficient") or not d["coverage"].get("basis"):
            blockers.append("important-question/route/period/source coverage not justified")
        if not d["residual_review"].get("samples") or d["residual_review"].get("material_omissions", []):
            blockers.append("residual discovery incomplete or material omissions remain")
        if not d["handoff"].get("passed") or not d["handoff"].get("tasks") or not d["handoff"].get("receipt"):
            blockers.append("performed cold handoff tasks with a receipt not passed")
        return {"status": "draft" if blockers else "reconstructed-qualified", "blockers": blockers, "assessment": latest["id"],
                "assessment_current": not outdated,
                "scientific_problem": d["scientific_problem"] if not outdated else None,
                "continuation": d["continuation"] if not outdated else None,
                "limitations": d["limitations"] if not outdated else [],
                "authority": d["authority"]}

    def _invalidate_publication(self):
        directory = owned(self.unit.workspace, "current")
        if directory.exists():
            self._write_views(directory)

    def _write_views(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        records = self.store.list()
        from research_harness.views.spine import render_spine, handoff
        state, research_map, navigation, page = render(records, self.store.current_revision(), self.unit.manifest["project_id"], self._completion(projection(records)))
        mainline, _ = render_spine(state)
        atomic_json(directory / "SCIENTIFIC_STATE.json", state)
        atomic_json(directory / "SOURCE_INDEX.json", source_index(records))
        (directory / "MAINLINE.md").write_text(mainline, encoding="utf-8")
        (directory / "SPINE.md").write_text(mainline, encoding="utf-8")
        (directory / "RESEARCH_MAP.md").write_text(research_map, encoding="utf-8")
        (directory / "HANDOFF.md").write_text(handoff(state), encoding="utf-8")
        (directory / "NAVIGATION.md").write_text(navigation, encoding="utf-8")
        (directory / "index.html").write_text(page, encoding="utf-8")
        # Copy only selected originals for a browser-openable navigation layer.
        hashes = {entry["blob"].rsplit("/", 1)[-1] for entries in source_index(records)["sources"].values() for entry in entries}
        for h in hashes:
            dest = directory / "store/blobs" / h
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.write_bytes(self.store.read_blob(h))
        return state

    def publish(self):
        self.unit.ingest.refresh()
        directory = owned(self.unit.workspace, "publications/r" + str(self.store.current_revision()) + "-" + semantic.POLICY)
        if (directory / "SCIENTIFIC_STATE.json").is_file():
            state = json.loads((directory / "SCIENTIFIC_STATE.json").read_text())
        else:
            state = self._write_views(directory)
        self._write_views(owned(self.unit.workspace, "current"))
        return {"directory": str(directory), "current": str(owned(self.unit.workspace, "current/index.html")),
                "state_revision": state["state_revision"], "completion": state["completion"]}

    def view(self, expect=None):
        revision = self.store.current_revision()
        if expect is not None and expect != revision:
            raise ConflictError("Requested context version is stale; get the current state and inspect changes")
        records = self.store.list()
        return render(records, revision, self.unit.manifest["project_id"], self._completion(projection(records)))[0]

    def guide(self):
        return {"skill": files("research_harness.resources").joinpath("research-retro/SKILL.md").read_text(),
                "reference": files("research_harness.resources").joinpath("research-retro/references/protocol.md").read_text()}

    def run(self, action, **args):
        return getattr(self, action)(**args)
