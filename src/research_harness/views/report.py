import hashlib
import html
import json
import os
import tempfile
import shutil
from collections import Counter
from pathlib import Path
from research_harness.context import kind_key, encoded, snapshot
from research_harness.storage.store import blob_refs


def query(store, text, kind=None, limit=20):
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    needle = text.casefold()
    matches = [r for r in store.list() if (kind is None or kind_key(r["kind"]) == kind_key(kind))
               and needle in encoded(r).casefold()]
    # Rank exact IDs before references buried inside larger case records.
    matches.sort(key=lambda r: (r['id'] != text, r['id'].casefold() != needle))
    return matches[:limit]


def brief(record):
    data = record['data']
    provenance = data.get('provenance')
    inherited_qualification = provenance.get('qualification', 'unknown') if isinstance(provenance, dict) else 'unknown'
    return {'id': record['id'], 'kind': record['kind'], 'revision': record['revision'],
            'title': title_of(record), 'summary': summary_of(record)[:900],
            'detail_entry': 'rh state get ' + record['id'],
            'source_count': len(data.get('source_locators', [])),
            'qualification': data.get('qualification') or inherited_qualification or 'unknown'}


def source_hashes(value):
    # Named hashes in structured locators are eligible; arbitrary text never is.
    found = set(blob_refs(value))
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"sha256", "content_hash", "blob_hash", "blob", "digest", "blob_sha256"} and isinstance(item, str):
                if len(item) == 64 and all(c in "0123456789abcdef" for c in item):
                    found.add(item)
            if isinstance(item, (dict, list)):
                found.update(source_hashes(item))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                found.update(source_hashes(item))
    return found


VIEW_VERSION = 'reader-3'
SECTIONS = [
    ('coverage','范围与覆盖',{'projectcontract','goal','sourcemanifest','coverage','scientificmap'}),
    ('audit','科学审计',{'auditcase','auditresult'}),
    ('work','对象与实际运行',{'scientificobject','objectidentity','run','executionreceipt'}),
    ('claims','命题与推断',{'claim','inference','assumption','evidence'}),
    ('branches','分支与负知识',{'branch','negativeknowledge'}),
    ('history','历史与纠正',{'historicalassertion','correction','patch','identityrelation'}),
    ('assets','可复用资产',{'artifact','reusableasset'}),
    ('queue','待审计候选',{'auditcandidate'}),
    ('unknown','未知与未完成',{'unknown','gap'}),
    ('other','其他导入记录',set()),
]


def title_of(record):
    data=record['data']
    for field in ('title','name','goal','research_question','actual_question','text','proposition','question','path'):
        value=data.get(field)
        if isinstance(value,str) and value.strip(): return value[:200]
    return record['id']


def summary_of(record):
    data=record['data']; result=[]
    for key in ('verdict','evidence_status','evidence_verdict','qualification','status','support_status','adjudication_supported','supported_scope','support_scope','failure_boundary','residual_unknowns','unresolved','reopen_conditions'):
        value=data.get(key)
        if value not in (None,[],{},''):
            value=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
            result.append(f'{key}: {value[:600]}')
    return '\n'.join(result)[:2000] or '原始字段可按 ID 查证；此条记录未形成独立科学判定。'


def locator_links(value, copied):
    """Labels contain version and locator; href uses verified blob hash only."""
    found=[]
    def walk(node):
        if isinstance(node,dict):
            identity=node.get('content_identity',{})
            digest=identity.get('digest') if isinstance(identity,dict) else None
            digest=digest or node.get('sha256')
            if digest in copied:
                loc=node.get('locator',{})
                label=node.get('uri',node.get('path',node.get('artifact_id','原件快照')))
                revision=node.get('artifact_revision')
                if revision is not None: label += f' · revision {revision}'
                if loc: label += f" · {loc.get('type','位置')} {loc.get('start','?')}–{loc.get('end','?')}"
                elif node.get('start_line') or node.get('line_start'):
                    label += f" · lines {node.get('start_line',node.get('line_start'))}–{node.get('end_line',node.get('line_end','?'))}"
                found.append((digest,str(label)))
            for child in node.values():
                if isinstance(child,(dict,list)): walk(child)
        elif isinstance(node,list):
            for child in node: walk(child)
    walk(value)
    represented={h for h,l in found}
    found.extend((h,'原件快照 '+h[:16]) for h in sorted(source_hashes(value)&set(copied)-represented))
    return list(dict.fromkeys(found))


def history_tracks(records):
    tracks={k:[] for k in ('actual_work','then_believed','then_reported','later_remembered','currently_warranted')}
    adjudications=[]
    rejected={'refuted','unsupported','unknown','unresolved','mixed','unchecked','imported_assertion','invalid','invalid_inference','pending','incomplete','blocked'}
    for record in records:
        data=record['data']; kind=kind_key(record['kind'])
        if kind=='run': tracks['actual_work'].append(record['id'])
        if kind=='historicalassertion':
            role=data.get('track',data.get('history_role'))
            if role in ('then_believed','then_reported','later_remembered'): tracks[role].append(record['id'])
        qualifiers=[data.get(k) for k in ('qualification','evidence_status','evidence_verdict','verdict','status')]
        blocked=any(isinstance(v,str) and (v in rejected or v.startswith(('unresolved','pending','incomplete'))) for v in qualifiers)
        if kind=='claim' and data.get('support_status')=='supported' and not blocked and not data.get('revoked'):
            tracks['currently_warranted'].append(record['id'])
        if ((kind=='claim' and data.get('adjudication_supported')) or
            (kind in ('auditcase','auditresult') and data.get('support_status')=='supported' and str(data.get('status','')).startswith('completed'))):
            adjudications.append(record['id'])
    return {k:{'status':'recorded' if ids else 'unknown','record_ids':ids} for k,ids in tracks.items()},adjudications


APP_JS = r'''"use strict";
const state=JSON.parse(document.getElementById('snapshot-data').textContent);
const records=new Map(state.records.map(r=>[r.id,r]));
const search=document.getElementById('search');
const cards=Array.from(document.querySelectorAll('article[data-record]'));
const corpus=new Map(state.records.map(r=>[r.id,JSON.stringify(r).toLocaleLowerCase()]));
function filter(){const q=search.value.toLocaleLowerCase();let count=0;
for(const card of cards){const visible=corpus.get(card.dataset.record).includes(q);card.hidden=!visible;if(visible)count++;}
document.getElementById('match-count').textContent=String(count)+' 条匹配';}
search.addEventListener('input',filter);
for(const detail of document.querySelectorAll('details[data-record]')){
 detail.addEventListener('toggle',()=>{if(!detail.open||detail.dataset.loaded)return;
 const pre=document.createElement('pre');pre.textContent=JSON.stringify(records.get(detail.dataset.record),null,2);
 detail.appendChild(pre);detail.dataset.loaded='true';});}
document.getElementById('lookup').addEventListener('submit',event=>{
 event.preventDefault();const id=document.getElementById('record-id').value;
 const card=cards.find(c=>c.dataset.record===id);const status=document.getElementById('lookup-status');
 if(!card){status.textContent='未找到这个 ID；支持精确 ID 查证。';return;}
 search.value='';filter();card.scrollIntoView({block:'start'});card.querySelector('details[data-record]').open=true;
 status.textContent=id;});
filter();
'''


def export_report(store, dest):
    records, revision = snapshot(store)
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
    fingerprint=hashlib.sha256(encoded(records).encode()).hexdigest()
    version_name=f'state-{revision}-{fingerprint[:12]}-{VIEW_VERSION}'
    final=dest/version_name; staging=Path(tempfile.mkdtemp(prefix='.render-',dir=dest))
    try:
        source_dir=staging/'sources';source_dir.mkdir()
        refs=sorted({ref for r in records for ref in source_hashes(r['data'])})
        copied=[];unavailable=[]
        for ref in refs:
            try: content=store.read_blob(ref)
            except FileNotFoundError: unavailable.append(ref);continue
            (source_dir/ref).write_bytes(content);copied.append(ref)
        state={'schema_version':1,'state_revision':revision,'content_hash':fingerprint,'records':records}
        (staging/'state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2))
        counts=Counter(kind_key(r['kind']) for r in records)
        unresolved=[r['id'] for r in records if kind_key(r['kind']) in {'unknown','gap'} or
                    str(r['data'].get('status','')).startswith(('unresolved','unknown','blocked','incomplete','pending')) or
                    r['data'].get('unresolved') or r['data'].get('missing')]
        histories,adjudications=history_tracks(records)
        handoff={'schema_version':1,'state_revision':revision,'content_hash':fingerprint,'view_version':VIEW_VERSION,
            'entry':'index.html','structured_state':'state.json','sources':'sources/',
            'read_set':{r['id']:r['revision'] for r in records},'unknown_or_unfinished':unresolved,
            'history_tracks':histories,'supported_adjudications':adjudications,
            'history_boundary':'Supported adjudication of a refuted claim does not warrant that original proposition.',
            'source_snapshots':copied,'unavailable_snapshots':unavailable,
            'reconstruction_status':'inspect scoped audit and coverage records; export does not certify R2 completion',
            'resume':'Use record ID lookup and version-bound source locators; complete original fields are retained in state.json.'}
        (staging/'handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2))
        classified={}; remaining=set(r['id'] for r in records)
        for slug,title,kinds in SECTIONS:
            classified[slug]=[r for r in records if r['id'] in remaining and (kind_key(r['kind']) in kinds or slug=='other')]
            remaining-=set(r['id'] for r in classified[slug])
        audit_records=classified['audit']; coverage_records=classified['coverage']
        contracts = [r for r in records if kind_key(r['kind']) == 'projectcontract']
        goal = contracts[0]['data'].get('goal', '目标未记录') if contracts else '目标未记录'
        scopes = contracts[0]['data'].get('scope_notes', []) if contracts else []
        md=['# 项目复盘状态','',f'状态版本 {revision} · 阅读器 {VIEW_VERSION} · {len(records)} 条记录','',
            '指定版本的只读观察快照，不宣称完成 R2。审计结论派生自结构化记录，导入条目不自动成为科学支持。','',
            '[交互阅读与按 ID 查证](index.html) · [全部结构化状态](state.json) · [交接](handoff.json)','',
            '## 目标与范围','',goal,'',*['- '+x for x in scopes],'',
            '## 当前命题与裁决','']
        for r in records:
            if kind_key(r['kind']) == 'claim':
                md += [f"- {r['data'].get('evidence_status', 'unknown')}：{title_of(r)} · `{r['id']}` · {r['data'].get('support_status','unchecked')}"]
        md += ['', '## 科学结果与边界', '']
        for r in audit_records:
            md += [f"### {html.escape(title_of(r))}",'',f"ID `{r['id']}` · revision {r['revision']}",'']
            md += ['    '+line for line in summary_of(r).splitlines()]+['']
        if not audit_records: md+=['尚无正式科学审计记录。','']
        md+=['## 历史与当前依据','',
             f"当前得到支持的命题：{len(histories['currently_warranted']['record_ids'])}；得到支持的裁决记录：{len(adjudications)}。二者不等同。",'',
             '完整五条历史轨迹与 ID 集合见 handoff.json；未记录轨迹保留 unknown。','',
             f'未知或未完成入口 {len(unresolved)} 条；缺失原件快照 {len(unavailable)} 个。','']
        for slug,title,kinds in SECTIONS:
            md += ['## '+title,'',f'{len(classified[slug])} 条记录；下列为目录，完整字段与精确来源在 HTML 的按 ID 查证及 state.json。','']
            for r in classified[slug]:
                anchor='record-'+hashlib.sha256(r['id'].encode()).hexdigest()[:20]
                md.append(f"- [{html.escape(title_of(r)).replace('[','&#91;').replace(']','&#93;')}](index.html#{anchor}) · `{r['id']}` · r{r['revision']}")
            md.append('')
        (staging/'report.md').write_text('\n'.join(md))
        e=lambda value:html.escape(str(value),quote=True)
        page=['<!doctype html><html lang="zh"><head><meta charset="utf-8">',
              '<meta name="viewport" content="width=device-width,initial-scale=1">',
              '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'self\'; style-src \'unsafe-inline\'; object-src \'none\'; base-uri \'none\';">',
              '<title>项目复盘状态</title><style>body{margin:0;background:#f6f7f9;color:#18202a;font:15px/1.6 system-ui}main,header{max-width:1160px;margin:auto;padding:24px}header{padding-bottom:8px}h1,h2,h3{line-height:1.3}nav{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}a{color:#175ca4;overflow-wrap:anywhere}article,.panel{background:white;border:1px solid #dce2e8;border-radius:8px;padding:16px;margin:12px 0}article h3{margin:0 0 8px}.meta{color:#576574;font-size:13px;overflow-wrap:anywhere}.summary{white-space:pre-wrap;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}input{padding:10px;min-width:260px;max-width:90%}button{padding:10px}summary{cursor:pointer;color:#175ca4}.stats{display:flex;gap:20px;flex-wrap:wrap}.sources{display:flex;flex-direction:column;gap:5px}[hidden]{display:none!important}section{scroll-margin-top:20px}article{scroll-margin-top:15px}</style></head><body>',
              '<header><h1>项目复盘状态</h1>',f'<p>状态版本 {revision} · {VIEW_VERSION} · {len(records)} 条记录</p>',
              f'<p><strong>目标：</strong>{e(goal)}</p><p>{e("；".join(scopes))}</p>',
              '<p>只读观察快照，不宣称完成 R2。科学结论与未知边界由版本化记录派生；历史导入不自动成为已核验证据。</p>',
              '<p><a href="state.json">全部结构化状态</a> · <a href="handoff.json">交接包</a> · <a href="report.md">Markdown</a></p>',
              f'<div class="stats"><span>来源快照 {len(copied)}</span><span>科学审计 {len(audit_records)}</span><span>未知/未完成 {len(unresolved)}</span><span>缺失快照 {len(unavailable)}</span></div>',
              '<nav>'+''.join(f'<a href="#{slug}">{e(title)} ({len(classified[slug])})</a>' for slug,title,kinds in SECTIONS)+'</nav>',
              '<label>搜索记录与原始字段 <input id="search" type="search" placeholder="条件、对象、命题或 ID"></label> <span id="match-count"></span>',
              '<form id="lookup"><label>精确 ID <input id="record-id" placeholder="粘贴记录 ID"></label> <button type="submit">查证原字段</button> <span id="lookup-status"></span></form>',
              '<noscript>JavaScript 未启用：目录与来源链接仍可使用；完整记录请打开 state.json。</noscript></header><main>',
              '<section class="panel"><h2>当前科学裁决</h2>']
        for r in audit_records:
            page += [f'<h3>{e(title_of(r))}</h3><p class="summary">{e(summary_of(r))}</p>']
        if not audit_records: page+=['<p>尚无正式科学审计结果。</p>']
        page += [f'<p>当前支持的命题 {len(histories["currently_warranted"]["record_ids"])} 条；有依据的裁决 {len(adjudications)} 条。裁决可能是否定原命题，不能将两者混同。</p></section>']
        for slug,title,kinds in SECTIONS:
            page.append(f'<section id="{slug}"><h2>{e(title)} · {len(classified[slug])}</h2>')
            if not classified[slug]: page.append('<p>未知：当前没有此类正式记录。</p>')
            for r in classified[slug]:
                anchor='record-'+hashlib.sha256(r['id'].encode()).hexdigest()[:20]
                page += [f'<article id="{anchor}" data-record="{e(r["id"])}"><h3>{e(title_of(r))}</h3>',
                         f'<p class="meta">{e(r["id"])} · {e(r["kind"])} · revision {r["revision"]}</p>',
                         f'<p class="summary">{e(summary_of(r))}</p>']
                links=locator_links(r['data'],copied)
                if links:
                    page.append('<details><summary>精确来源与版本定位</summary><div class="sources">')
                    page += [f'<a href="sources/{h}" download>{e(label)}</a>' for h,label in links]
                    page.append('</div></details>')
                page.append(f'<details data-record="{e(r["id"])}"><summary>按 ID 查证全部原字段</summary></details></article>')
            page.append('</section>')
        # Escaping '<' blocks </script> and HTML parser breakout. JS only uses textContent.
        payload=json.dumps(state,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
        page += ['</main><script id="snapshot-data" type="application/json">'+payload+'</script>',
                 '<script src="app.js" defer></script></body></html>']
        (staging/'index.html').write_text(''.join(page));(staging/'app.js').write_text(APP_JS)
        if final.exists(): shutil.rmtree(staging)
        else: os.replace(staging,final)
        store.mark_view('report',final/'index.html',revision)
        pointer=dest/'.latest.tmp';pointer.write_text(json.dumps({'state_revision':revision,'version_dir':version_name},ensure_ascii=False));os.replace(pointer,dest/'latest.json')
        return {'state_revision':revision,'content_hash':fingerprint,'version_dir':str(final),
                'report':str(final/'report.md'),'html':str(final/'index.html'),'state':str(final/'state.json'),
                'handoff':str(final/'handoff.json'),'source_count':len(copied),'unavailable_snapshots':unavailable,
                'view_status':store.view_status('report')}
    finally:
        if staging.exists(): shutil.rmtree(staging)
