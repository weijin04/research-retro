"""Portable numerical regression derived from a performed cold task, not a discovery benchmark."""
from pathlib import Path
import json,re,math,hashlib,collections,csv,io
import argparse
p=argparse.ArgumentParser();p.add_argument('bundle');p.add_argument('output');args=p.parse_args()
B=Path(args.bundle).resolve();O=Path(args.output).resolve();O.mkdir(parents=True,exist_ok=True)
S=json.loads((B/'SOURCE_INDEX.json').read_text())['sources']
used={}
def read(path):
 r=S[path][-1]; p=B/r['blob']; raw=p.read_bytes(); used[path]={'blob':r['blob'],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};return raw.decode()
def get(suffix):
 keys=[p for p in S if p.endswith(suffix)]; assert len(keys)==1,keys;return read(keys[0])
def xyz(t):
 l=t.splitlines(); n=int(l[0]);a=[(r.split()[0],tuple(map(float,r.split()[1:4]))) for r in l[2:2+n]];assert len(a)==n;return a
rows=[]
for p in sorted(S):
 if p.endswith('/RESTART/C3_free/orca.xyz'):
  a=xyz(read(p)); stem=p[:-8]; inp=read(stem+'orca.inp');out=read(stem+'orca.out')
  assert [a[i][0] for i in [32,72,87,88]]==['C','Fe','N','N']
  ids=list(map(int,re.findall(r'\{\s*C\s+(\d+)\s+C\s*\}',inp)))
  d=lambda i,j:math.dist(a[i][1],a[j][1])
  row={'case':p.split('/')[-4],'atom_count':len(a),'charge_mult':re.search(r'xyzfile\s+(\d+)\s+(\d+)',inp).groups(),'N87_C32_A':d(87,32),'Fe72_N87_A':d(72,87),'N87_N88_A':d(87,88),'HURRAY':'HURRAY' in out,'normal_termination':'ORCA TERMINATED NORMALLY' in out,'frozen_atoms':[{'index':i,'element':a[i][0]} for i in ids],'frozen_elements':dict(collections.Counter(a[i][0] for i in ids))}
  row['C4_gate']=row['HURRAY'] and row['N87_C32_A']<1.70 and row['Fe72_N87_A']>2.10
  rows.append(row)
make=get('/cage_branch/make_c4.py')
f0=get('/fe_arm/F0_pcontact_m6/orca.inp'); fids=list(map(int,re.findall(r'\{\s*C\s+(\d+)\s+C\s*\}',f0)))
assert all([a['index'] for a in r['frozen_atoms']]==fids for r in rows)
build=json.loads(get('/G5_qexit/BUILD.json')); D=xyz(get('/D_RKS/orca.xyz'))
pairs={k:{'indices':ij,'elements':[D[i][0] for i in ij],'distance_A':math.dist(D[ij[0]][1],D[ij[1]][1])} for k,ij in build['pairs'].items()}
pair=get('/G9_ts/source/diazene_neb/orca.out');sec=pair[pair.rfind('PATH SUMMARY FOR NEB-TS'):];en={m[0]:float(m[1]) for m in re.findall(r'^\s*(\d+|TS)\s+(-\d+\.\d+)\s',sec,re.M)}
index=get('/CALC_INDEX.tsv');calc=list(csv.DictReader(io.StringIO(index),delimiter='\t'))
code={s:get(s) for s in ['/G5_qexit/collect.py','/NH_exit2/thermo_active.py','/product_fingerprint_20260919/extract_phi.py']}
manifest=json.loads((B/'manifest.json').read_text());audit={p:hashlib.sha256((B/p).read_bytes()).hexdigest()==h for p,h in manifest['files'].items()}
source_checks=[{'path':p,'blob_exists':(B/r['blob']).is_file(),'length_matches':len((B/r['blob']).read_bytes())==r['byte_range'][1]-r['byte_range'][0] if 'byte_range' in r else None} for p,rs in S.items() for r in rs]
result={'evaluation':'revealed repair recheck, not independent initial evaluation','bundle':str(B),'C3':rows,'D_BUILD_pairs':pairs,'CI_delta_kcal_mol':(en['2']-en['0'])*627.5094740631,'CALC_INDEX_rows':len(calc),'captured_sources':len(S),'source_index_checks':source_checks,'all_manifest_hashes_match':all(audit.values()),'source_hashes':used}
(O/'repair-table.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(O/'repair-sources.json').write_text(json.dumps({'manifest_checks':audit,'used_sources':used},indent=2)+'\n')
lines=['|case|q/m|N87–C32 Å|Fe72–N87 Å|N87–N88 Å|HURRAY/normal|frozen|C4 gate|','|---|---|---:|---:|---:|---|---|---|']
for r in rows:lines.append(f"|{r['case']}|{'/'.join(r['charge_mult'])}|{r['N87_C32_A']:.6f}|{r['Fe72_N87_A']:.6f}|{r['N87_N88_A']:.6f}|{r['HURRAY']}/{r['normal_termination']}|{r['frozen_elements']}|{r['C4_gate']}|")
(O/'repair-table.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines));print(json.dumps({k:result[k] for k in ['D_BUILD_pairs','CI_delta_kcal_mol','CALC_INDEX_rows','captured_sources','all_manifest_hashes_match']},indent=2))
