from pathlib import Path
import csv,json,hashlib,time,collections,math,sys
P=Path(sys.argv[1]); W=Path(sys.argv[2])
reads=[]
def read(rel):
 b=(P/rel).read_bytes(); reads.append({"path":rel,"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b)});return b.decode()
def rows(rel,delim=','):return list(csv.DictReader(read(rel).splitlines(),delimiter=delim))
def metrics(rs):
 kr=[r for r in rs if r['truth_label']=='kr_priority'];xe=[r for r in rs if r['truth_label']=='xe_priority']
 return {"rows":len(rs),"kr":len(kr),"xe":len(xe),"tp":sum(r['prediction']=='kr_priority' for r in kr),"fp":sum(r['prediction']=='kr_priority' for r in xe),"abstain":sum(r['prediction']=='abstain' for r in rs)}
r=rows('cxekr_loop/r4/predictions.csv'); saved=json.loads(read('cxekr_loop/r4/metrics.json'))
res={"started_utc":time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),"r4_overall":metrics(r),"r4_saved_overall":saved.get('metrics',saved).get('overall'),"folds":{}}
for family,fold in saved['lomfo']['folds'].items():
 ids=fold['held_out_row_ids'];h=[x for x in r if int(x['row_id']) in ids];other=[x for x in r if int(x['row_id']) not in ids]
 res['folds'][family]={"held_out":metrics(h),"complement":metrics(other),"saved_scoring_population":"complement" if fold.get('retained_row_count')==len(other) else 'not_executable'}
# Independent threshold-connectivity via quotient graph displacement consistency; no imported historical code.
def cycle(edges):
 adj=collections.defaultdict(list)
 for e in edges:
  a,b,t=e['source'],e['target'],tuple(e['translation']);adj[a].append((b,t,e['id']));adj[b].append((a,tuple(-v for v in t),e['id']))
 seen={}
 for root in adj:
  if root in seen:continue
  seen[root]=(0,0,0);q=[root]
  for a in q:
   for b,t,eid in adj[a]:
    v=tuple(x+y for x,y in zip(seen[a],t))
    if b in seen:
     if v!=seen[b]:return {"edge":eid,"net_translation":tuple(x-y for x,y in zip(v,seen[b]))}
    else:seen[b]=v;q.append(b)
 return None
res['networks']=[]
for rel in ['cxekr/validation/networks/coni-dab.json','cxekr/validation/networks/hkust-1.json','cxekr/validation/networks/sbmof-2.json']:
 n=json.loads(read(rel)); es=n['windows']; thresholds=sorted(set(e['free_radius_A'] for e in es),reverse=True)
 for b in thresholds:
  active=[e for e in es if e['free_radius_A']>=b]; witness=cycle(active)
  if witness:break
 res['networks'].append({"path":rel,"all_window_min":min(e['free_radius_A'] for e in es),"periodic_widest_bottleneck":b,"witness":witness,"above_threshold_has_cycle":bool(cycle([e for e in es if e['free_radius_A']>b])),"min_window_removed_same_path":bool(cycle([e for e in active if e['id']!='w0014']))})
res['md_derived_csv_checks']=[]
for rel,field in [('cxekr_loop/r3/analysis-gf-final.csv','r_mainwindow_A'),('cxekr_loop/r3/analysis-kr-final.csv','r_mainwindow_A'),('cxekr_loop/r3/analysis-xe-final.csv','r_mainwindow_A'),('cxekr_loop/r3/analysis-conidab-final/195K_window.csv','r_bottleneck_A'),('cxekr_loop/r3/analysis-conidab-final/298K_window.csv','r_bottleneck_A')]:
 data=rows(rel);vs=[float(x[field]) for x in data if float(x['t_ps'])>=10]
 res['md_derived_csv_checks'].append({"path":rel,"field":field,"n":len(vs),"max":max(vs),"mean":sum(vs)/len(vs),"kr_events":sum(v>=1.818 for v in vs),"xe_events":sum(v>=2.05 for v in vs),"independent_binomial_zero_event_upper95_not_time_correlated_MD_CI":1-0.05**(1/len(vs))})
evalrows=rows('cxekr/artifacts/experiment/v163_low_cost_kr_opportunity_recall_head/KR_OPPORTUNITY_EVALUATION.tsv','\t')
res['v163']={"known_Kr_families":len(evalrows),"recalled":sum(x['opportunity_recalled']=='True' for x in evalrows),"strict_Kr":sum(x['strict_candidate_sign']=='Kr' for x in evalrows),"certificate_no_clear":sum(x['certificate']=='no-clear' for x in evalrows)}
res['logic_counterexample']={"all_edge_min":0.01,"edges":[{"source":"a","target":"a","translation":[1,0,0],"id":"open","free_radius_A":2.1},{"source":"a","target":"b","translation":[0,0,0],"id":"dead","free_radius_A":0.01}],"claim":"A closed dead end does not block the open periodic self-loop."}
res['logic_counterexample']['witness']=cycle([res['logic_counterexample']['edges'][0]])
v12=json.loads(read('cxekr/validation/v12/benchmark_summary.json'))
res['v12']={k:v12[k] for k in ['active_total','complete_total','directionally_recovered_kr_priority_materials','false_kr_orderings_on_xe_controls','recovered_kr_priority_materials']}
manifest=rows('cxekr/artifacts/experiment/v162_final_closed_performance_audit/COMPLETE_SAMPLE_MANIFEST.tsv','\t')
res['v162_records']=[{k:x[k] for k in ['material_group','exposure','estimand','final_prediction','certificate_status','primary_metric_eligible']} for x in manifest]
fm=rows('cxekr/artifacts/experiment/v156_fmof_background_occupant_state_envelope/FMOF_STATE_ENVELOPE_RESULTS.tsv','\t')
res['fmof']={'rows':len(fm),'technical_valid':sum(x['technical_validity']=='True' for x in fm),'all_temperature_Kr':sum(all(y.endswith(':Kr') for y in x['state_sign_by_temperature_K'].split(';')) for x in fm)}
res['r2_outputs']=[]
for slug in ['utsa-74a','mil-160','cu-ain','mfm-520','calf-20m-w-195k']:
 j=json.loads(read('cxekr_loop/funnel_runs/'+slug+'/result.json'))
 res['r2_outputs'].append({'slug':slug,'policy':j['policy'],'decision':j['decision']['output'],'input':j['request']['cif']})
res['reads']=reads
(W/'checks/result.json').write_text(json.dumps(res,indent=2,ensure_ascii=False))
print(json.dumps({k:v for k,v in res.items() if k!='reads'},indent=2))
