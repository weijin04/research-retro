import sys,json,pathlib,datetime,time
import numpy as np
from ase.io import read,Trajectory
from ase.geometry import find_mic
O=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(O/"inputs"))
import analyze_window as aw
aw.VDW_A.update({"Co":2.00,"Ni":1.63})
t0=time.time();net=json.loads((O/"inputs/coni-dab.json").read_text()); wins=net["windows"]
def winding(weights,exclude=()):
 for threshold in sorted(set(weights.values()),reverse=True):
  adj={c["id"]:[] for c in net["cavities"]}
  for w in wins:
   if w["id"] in exclude or weights[w["id"]]<threshold:continue
   u,v=w["source"],w["target"];d=np.array(w["translation"]);adj[u].append((v,d,w["id"]));adj[v].append((u,-d,w["id"]))
  seen={}
  for root in adj:
   if root in seen:continue
   seen[root]=np.zeros(3,dtype=int);stack=[root]
   while stack:
    u=stack.pop()
    for v,d,wid in adj[u]:
     q=seen[u]+d
     if v not in seen:seen[v]=q;stack.append(v)
     elif np.any(q!=seen[v]):return {"radius_A":threshold,"closing_edge":wid,"winding":(q-seen[v]).tolist()}
 return None
ref=read(O/"inputs/coni-dab.cif");offs,raw=aw.compute_calibration_offsets(wins,O/"inputs/coni-dab.cif")
def centers(at):
 p=at.positions;cell=at.cell[:];r={}; sensitivity=[]
 for w in wins:
  ids=w["defining_atom_indices"];c=aw.unwrapped_center(p,ids,cell,at.pbc);v,_=aw.free_radius_from_center(c,p,at.get_chemical_symbols(),cell,at.pbc);r[w["id"]]=v+offs[w["id"]]
  alt=aw.unwrapped_center(p,list(reversed(ids)),cell,at.pbc);dist=float(find_mic(alt-c,cell,at.pbc)[1]);ar,_=aw.free_radius_from_center(alt,p,at.get_chemical_symbols(),cell,at.pbc)
  sensitivity.append({"window":w["id"],"center_change_A":dist,"radius_change_A":float(ar-v)})
 return r,sorted(sensitivity,key=lambda z:z["center_change_A"],reverse=True)
r,s=centers(ref)
out={"started_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"definition":"maximum threshold admitting a nonzero lattice winding cycle; not a transport certificate","static":{"all_min_A":min(r.values()),"periodic":winding(r),"without_w0014":winding(r,["w0014"]),"max_calibration_offset_A":max(offs.values()),"min_calibration_offset_A":min(offs.values()),"reversed_atom_order_center_test":s},"samples":[]}
for label in ["195","298"]:
 tr=Trajectory(O/("inputs/conidab_"+label+"_final.traj"))
 for fi in sorted(set([0,20,len(tr)//2,len(tr)-1])):
  a=tr[fi];r,s=centers(a);out["samples"].append({"temperature_label":label,"frame":fi,"total_frames":len(tr),"symbols_match_reference":a.get_chemical_symbols()==ref.get_chemical_symbols(),"cell_max_delta_A":float(np.max(np.abs(a.cell[:]-ref.cell[:]))),"all_min_A":min(r.values()),"periodic":winding(r),"max_permutation_center_change":s[0],"per_window_calibrated_A":r})
out["elapsed_seconds"]=time.time()-t0
(O/"audit-result.json").write_text(json.dumps(out,indent=2));print(json.dumps({"static":{k:v for k,v in out["static"].items() if k!="reversed_atom_order_center_test"},"static_permutation_top":out["static"]["reversed_atom_order_center_test"][:3],"samples":[{k:v for k,v in z.items() if k!="per_window_calibrated_A"} for z in out["samples"]]},indent=2))
