import csv,json,io,hashlib,math
from pathlib import Path
from collections import defaultdict,Counter
W=Path(__file__).parent
S=W.parents[1]/"cxekr-loop-20260921-A/materials"
trace=json.loads((W/"read-trace.json").read_text())
def read(rel,purpose):
 p=S/rel;b=p.read_bytes()
 trace["reads"].append({"path":str(p),"range":"whole","purpose":purpose,"mode":"programmatic_recompute","program_input_bytes":len(b),"bytes_read_by_host":0,"sha256_whole":hashlib.sha256(b).hexdigest()})
 return b.decode()
def tab(rel,purpose):return list(csv.DictReader(io.StringIO(read(rel,purpose))))
r2=tab("cxekr_loop/r4/predictions.csv","Independently count scoring numerators and denominators")
r1=tab("cxekr_loop/r4/run1/predictions.csv","Verify preserved void row count")
def metrics(rows):
 k=[r for r in rows if r["truth_label"]=="kr_priority"];x=[r for r in rows if r["truth_label"]=="xe_priority"]
 return {"n":len(rows),"recall":[sum(r["prediction"]=="kr_priority" for r in k),len(k)],"false_kr":[sum(r["prediction"]=="kr_priority" for r in x),len(x)],"abstain":sum(r["prediction"]=="abstain" for r in rows)}
out={"r1":metrics(r1),"r2":metrics(r2),"basis":{b:metrics([r for r in r2 if r["basis_branch"]==b]) for b in sorted(set(r["basis_branch"] for r in r2))},"K1_excluded":metrics([r for r in r2 if "K1" not in r["mechanism_families"].split("; ") and "K1" not in r["mechanism_families"].split(";")])}
net=json.loads(read("cxekr/validation/networks/hkust-1.json","Independent BFS integer-offset winding certificate, unlike original union-find"))
ws=net["windows"]
def winding(threshold):
 adj=defaultdict(list)
 for w in ws:
  if w["free_radius_A"]>=threshold:
   a,b,t=w["source"],w["target"],tuple(w["translation"])
   adj[a].append((b,t,w["id"]));adj[b].append((a,tuple(-v for v in t),w["id"]))
 pos={}
 for start in adj:
  if start in pos:continue
  pos[start]=(0,0,0);todo=[start]
  while todo:
   a=todo.pop()
   for b,t,edge in adj[a]:
    implied=tuple(u+v for u,v in zip(pos[a],t))
    if b in pos:
     residual=tuple(u-v for u,v in zip(implied,pos[b]))
     if any(residual):return {"edge":edge,"residual":residual}
    else:pos[b]=implied;todo.append(b)
 return None
radii=sorted({w["free_radius_A"] for w in ws},reverse=True)
for i,r in enumerate(radii):
 witness=winding(r)
 if witness:
  upper=radii[i-1] if i else None
  out["hkust_graph"]={"global_min":min(radii),"percolation_threshold":r,"cycle_witness":witness,"next_higher_threshold":upper,"winds_at_next_higher":bool(winding(upper)) if upper else None}
  break
assert out["hkust_graph"]["percolation_threshold"]==3.9208
assert out["hkust_graph"]["global_min"]==0.0333747
assert out["r2"]=={"n":23,"recall":[0,9],"false_kr":[2,13],"abstain":18}
def quantile(values,q):
 v=sorted(values);k=(len(v)-1)*q;i=int(k);f=k-i
 return v[i]*(1-f)+v[min(i+1,len(v)-1)]*f
out["r3"]={}
for e in ("gf","kr","xe"):
 rows=tab(f"cxekr_loop/r3/analysis-{e}-final.csv","Recompute post-10ps calibrated/raw medians and crossing counts from frame CSV")
 rows=[r for r in rows if float(r["t_ps"])>=10]
 v=[float(r["r_mainwindow_A"]) for r in rows];raw=[float(r["r_mainwindow_raw_A"]) for r in rows]
 source=json.loads(read(f"cxekr_loop/r3/analysis-{e}-final.json","Compare independent CSV statistics to full-precision stored outputs"))
 d={"n":len(v),"Kr_crossings":sum(x>=1.818 for x in v),"Xe_crossings":sum(x>=2.05 for x in v),"q50":quantile(v,.5),"raw_q50":quantile(raw,.5),"q95":quantile(v,.95),"max":max(v),"framewise_offset_range":[min(a-b for a,b in zip(v,raw)),max(a-b for a,b in zip(v,raw))]}
 for key,sk in (("q50","q50_A"),("q95","q95_A"),("max","max_A")):
  assert abs(d[key]-source["r_mainwindow"][sk])<=1.1e-6
 out["r3"][e]=d
out["loaded_q50_changes_A"]={e:out["r3"][e]["q50"]-out["r3"]["gf"]["q50"] for e in ("kr","xe")}
out["calf_r4_inherits_r3_q95"]={"r4":float(r2[3]["r_eff"]),"r3_csv":out["r3"]["gf"]["q95"],"static_only":r2[3]["static_only"]}
assert abs(out["calf_r4_inherits_r3_q95"]["r4"]-out["calf_r4_inherits_r3_q95"]["r3_csv"])<1.1e-6
out["limits"]=["No MD simulation or scorer rerun; independent postprocessing only.","Zero stored-frame crossings are not zero continuous-time crossing rate or independent Bernoulli trials.","Graph certificate verifies one representative failure, not all networks.","Ground-truth labels inherited from saved table, not independently verified against papers."]
(W/"verification.json").write_text(json.dumps(out,ensure_ascii=False,indent=2))
trace["scientific_original_unique_files"]=len({r["path"] for r in trace["reads"]})
trace["high_cost_original_text_bytes"]=sum(r.get("bytes_read_by_host",0) for r in trace["reads"])
trace["programmatic_input_bytes_including_rereads"]=sum(r.get("program_input_bytes",0) for r in trace["reads"])
trace["token_count"]="unknown"
(W/"read-trace.json").write_text(json.dumps(trace,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
