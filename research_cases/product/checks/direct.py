"""Read-only independent reductions; never imports or executes project code."""
from pathlib import Path
import json,csv,hashlib,re,collections
import numpy as np
from ase.io.trajectory import Trajectory
from ase.units import kB
R=Path('/home/sun07ao/retro-workspaces/retro-product-evaluation/cxekr-loop-20260921-A/materials')
O=Path(__file__).parent
seen={}
def read(p):
 p=Path(p); b=p.read_bytes();seen[str(p.relative_to(R))]=hashlib.sha256(b).hexdigest();return b.decode()
def js(p):return json.loads(read(p))
def rows(p,delim=','):return list(csv.DictReader(read(p).splitlines(),delimiter=delim))
def metric(rs,key='prediction',truth='truth_label'):
 pos=[x for x in rs if x[truth]=='kr_priority']; neg=[x for x in rs if x[truth]=='xe_priority']
 return dict(n=len(rs),kr_recall=[sum(x[key] in ['kr','kr_priority'] for x in pos),len(pos)],false_kr=[sum(x[key] in ['kr','kr_priority'] for x in neg),len(neg)],abstain=sum(x[key]=='abstain' for x in rs))
def winds(edges,b):
 adj=collections.defaultdict(list)
 for e in edges:
  if e['free_radius_A']>=b:
   a,c=e['source'],e['target'];t=tuple(e['translation']);adj[a].append((c,t));adj[c].append((a,tuple(-v for v in t)))
 potential={}
 for a in adj:
  if a in potential:continue
  potential[a]=(0,0,0);queue=[a]
  for u in queue:
   for v,t in adj[u]:
    p=tuple(x+y for x,y in zip(potential[u],t))
    if v in potential:
     if potential[v]!=p:return True
    else:potential[v]=p;queue.append(v)
 return False
out={};pr=rows(R/'cxekr_loop/r4/predictions.csv');out['R4']=metric(pr)
out['R4_held_out_family_metrics']={f:metric([x for x in pr if f in x['mechanism_families'].split(';')]) for f in ['E1','E2','E3','K1','K2','K3','K4','P2','U']}
out['R4_geometry']=[]
for row in pr:
 if row['r_eff_selection']!='percolating_bottleneck_periodic_union_find':continue
 rel=row['r_eff_source_path'].removeprefix('/home/sun07ao/');data=js(R/rel); es=data['windows'];bs=sorted({e['free_radius_A'] for e in es},reverse=True)
 b=next((b for b in bs if winds(es,b)),None)
 out['R4_geometry'].append(dict(material=row['material'],computed=b,recorded=float(row['r_eff']),match=abs(b-float(row['r_eff']))<1e-10,minimum_window=min(bs),source_hash_match=seen[rel]==row['r_eff_source_sha256']))
out['R3_csv']=[]
for gas in ['gf','kr','xe']:
 rs=rows(R/f'cxekr_loop/r3/analysis-{gas}-final.csv');a=np.array([float(x['r_mainwindow_A']) for x in rs if float(x['t_ps'])>=10]);d=js(R/f'cxekr_loop/r3/analysis-{gas}-final.json')
 out['R3_csv'].append(dict(gas=gas,n=len(a),Kr_events=int(sum(a>=1.818)),Xe_events=int(sum(a>=2.05)),median=float(np.median(a)),q95=float(np.quantile(a,.95)),max=float(max(a)),q95_error=abs(float(np.quantile(a,.95))-d['r_mainwindow']['q95_A'])))
out['trajectory_temperature']=[]
for name in ['gf_final','kr_final','xe_final','conidab_195_final','conidab_298_final']:
 p=R/f'cxekr_loop/r3/md/{name}.traj';seen[str(p.relative_to(R))]=hashlib.sha256(p.read_bytes()).hexdigest(); tr=Trajectory(str(p),'r'); ts=[];elements=collections.defaultdict(list)
 for a in tr[len(tr)//10:]:
  ek=(a.get_momenta()**2).sum(axis=1)/(2*a.get_masses()); sy=np.array(a.get_chemical_symbols());ts.append(float(2*ek.sum()/(3*len(a)*kB)))
  for s in set(sy):elements[s].append(float(2*ek[sy==s].mean()/(3*kB)))
 out['trajectory_temperature'].append(dict(run=name,frames=len(tr),used=len(ts),mean_K=float(np.mean(ts)),elements={s:float(np.mean(v)) for s,v in elements.items()}))
v=R/'cxekr/artifacts/experiment/v163_low_cost_kr_opportunity_recall_head';ev=rows(v/'KR_OPPORTUNITY_EVALUATION.tsv','\t');pred=js(v/'KR_OPPORTUNITY_PREDICTIONS.json')['families'];out['V163']=dict(known_kr=len(ev),recalled=sum(x['opportunity_recalled']=='True' for x in ev),all_predictions=len(pred),certificates=dict(collections.Counter(x['certificate'] for x in pred)),xe_only_review=sum(x['strict_candidate_sign']=='Xe' and x['kr_opportunity']=='yes' for x in pred),xe_only=sum(x['strict_candidate_sign']=='Xe' for x in pred))
v159=js(R/'cxekr/artifacts/experiment/v159_finite_step_excitation_and_retardation_audit/TRUTH_FREE_INPUT.json');out['V159_raw_covariance']=[]
for record in v159['records']:
 for u in record['units']:
  log=read(R/'cxekr'/u['source_log']);blocks=np.zeros((5,2,2));hits=re.findall(r'BLOCK \[(\d+)\] COMPONENT \[\d+\] \((Kr|Xe)\) COMPONENT \[\d+\] \((Kr|Xe)\) COVARIANCE: ([-+0-9.eE]+)',log)
  for b,i,j,val in hits:blocks[int(b),['Kr','Xe'].index(i),['Kr','Xe'].index(j)]=float(val)
  chi=blocks[1:].mean(axis=0);f=np.array(u['fugacity_kpa_Kr_Xe']);q=np.array(u['loading_mean_blocks_1_to_4_molecule']);inventory=float(np.log((q[0]/f[0])/(q[1]/f[1])))
  out['V159_raw_covariance'].append(dict(id=record['opaque_id'],cell=u['cell'],seed=u['seed'],covariance_entries=len(hits),raw_chi_maxerror=float(np.max(abs(chi-np.array(u['chi_molecule2'])))),inventory_margin=inventory,slow_species=u['slow_species'],source_sha_match=hashlib.sha256(log.encode()).hexdigest()==u['source_log_sha256']))
(O/'CHECK_RESULTS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');(O/'CHECK_INPUT_HASHES.json').write_text(json.dumps(seen,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['R4_geometry','V159_raw_covariance']},ensure_ascii=False,indent=2));print('geometry',len(out['R4_geometry']),all(x['match'] and x['source_hash_match'] for x in out['R4_geometry']));print('covariance',len(out['V159_raw_covariance']),max(x['raw_chi_maxerror'] for x in out['V159_raw_covariance']))
