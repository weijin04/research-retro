"""Portable numerical regression derived from a performed cold task, not a discovery benchmark."""
from pathlib import Path
import json,hashlib,math
import argparse
p=argparse.ArgumentParser();p.add_argument('bundle');p.add_argument('output');args=p.parse_args()
B=Path(args.bundle).resolve();O=Path(args.output).resolve();O.mkdir(parents=True,exist_ok=True)
expected=hashlib.sha256((B/'manifest.json').read_bytes()).hexdigest()
H={'flex':'2527e31e0064bad5ebc47c352d67c68b6563c4821c973b36736ca331635f6277','rigid':'0773c49f58b282d90e68572effe567dde50fcf354d34a92d51a8feb3a09ebe40'}
rows=[];sources={}
for mode,h in H.items():
 raw=(B/'store/blobs'/h).read_bytes();assert hashlib.sha256(raw).hexdigest()==h
 s=json.loads(raw);shots=s['outcomes'];assert len(shots)=={'flex':1024,'rigid':512}[mode];assert len(set(x['shot'] for x in shots))==len(shots)
 sources[mode]={'blob':h,'bytes':len(raw),'shots':len(shots)}
 for key in ['0.5ps','1ps','2ps']:
  positive=[x for x in shots if x['v_n_A_fs']>0]
  reactive=[x for x in positive if x['forward_commit'][key]==x['cage_j'] and x['backward_commit'][key]==x['cage_i']]
  denominator=sum(x['v_n_A_fs'] for x in positive);numerator=sum(x['v_n_A_fs'] for x in reactive)
  k=numerator/denominator
  assert math.isclose(k,s['kappa'][key],abs_tol=1e-12)
  rows.append({'mode':mode,'threshold':key,'shots':len(shots),'positive':len(positive),'reactive':len(reactive),'numerator_A_fs':numerator,'denominator_A_fs':denominator,'kappa':k,'stored_kappa':s['kappa'][key]})
manifest=json.loads((B/'manifest.json').read_text());audit={name:hashlib.sha256((B/name).read_bytes()).hexdigest()==h for name,h in manifest['files'].items()};assert all(audit.values())
frozen={}
(O/'repair-table.json').write_text(json.dumps({'evaluation':'targeted revealed repair recheck','author_questions':0,'sources':sources,'rows':rows},indent=2)+'\n')
(O/'repair-receipt.json').write_text(json.dumps({'bundle':str(B),'manifest_sha256':expected,'manifest_checks':audit,'initial_frozen_sha256':frozen},indent=2)+'\n')
lines=['|mode|threshold|shots|positive|reactive|weighted kappa|','|---|---|---:|---:|---:|---:|']+[f"|{r['mode']}|{r['threshold']}|{r['shots']}|{r['positive']}|{r['reactive']}|{r['kappa']:.12f}|" for r in rows]
(O/'repair-table.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
