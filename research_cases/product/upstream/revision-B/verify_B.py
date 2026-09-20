import json,hashlib,statistics
from pathlib import Path
R=Path(__file__).parent;S=R.parents[2]/"cxekr-loop-20260921-A/materials/cxekr/artifacts/experiment"
t=json.loads((R/"read-trace.json").read_text())
def read(rel,purpose):
 p=S/rel;b=p.read_bytes();t["reads"].append({"path":str(p),"range":"whole","mode":"programmatic_recompute","purpose":purpose,"program_input_bytes":len(b),"bytes_read_by_host":0,"sha256_whole":hashlib.sha256(b).hexdigest()});return json.loads(b)
x=read("v33_finite_t_path_survival_falsifier/path_survival.json","Recount tail row crossings and worst-case failed-frame rescue")
out={"v33":{}}
for e in ("ensemble_a","ensemble_b"):
 rows=[r for r in x["rows"] if r["ensemble_id"]==e and r["frame_index"]>=10];good=[r for r in rows if r["status"]=="completed"];bad=[r for r in rows if r["status"]!="completed"];v=[r["widest_periodic_free_radius_A"] for r in good]
 out["v33"][e]={"tail_rows":len(rows),"completed":len(good),"failed_indices":[r["frame_index"] for r in bad],"median":statistics.median(v),"max":max(v),"Kr_pass":sum(a>=1.868 for a in v),"Xe_pass":sum(a>=2.1 for a in v),"worst_case_if_all_failed_pass":{"pass_count":len(bad),"positive_blocks":len({(r["frame_index"]-10)//5 for r in bad}),"total_blocks":4}}
 assert out["v33"][e]["Kr_pass"]==0
assert out["v33"]["ensemble_a"]["completed"]==19
assert out["v33"]["ensemble_a"]["worst_case_if_all_failed_pass"]["positive_blocks"]==1
y=read("v13_finite_t_smoke/result.json","Verify numerical duration, stage boundary, material and breadth of saved smoke receipts")
out["smoke"]={"material":y["material"],"runs":len(y["runs"]),"all_runs_passed":all(r["smoke_passed"] for r in y["runs"]),"observation_ps":y["settings"]["production_steps"]*y["settings"]["timestep_fs"]/1000,"gas_seeds":[[r["gas"],r["velocity_seed"]] for r in y["runs"]],"pmf_eligible":y["finite_temperature_pmf_eligible"],"overlap_pilot_eligible":y["overlap_pilot_eligible"],"rate_eligible":y["rate_eligible"],"max_host_shift":max(r["maximum_mobile_host_displacement_A"] for r in y["runs"])}
out["limits"]=["Recomputed v33 stored per-frame results, not rerun Zeo++ or MD.","Smoke receipt consistency check only; raw COLVAR not reread or independently reproduced.","MIP-203-Suc historical evidence does not validate the CALF dynamic centroid calibration.","One technical failure cannot restore block-repeated support, but does not prove absence of rare physical passage."]
(R/"verification-B.json").write_text(json.dumps(out,ensure_ascii=False,indent=2));t["unique_scientific_files"]=len({r["path"] for r in t["reads"]});t["known_host_bytes"]=sum(r.get("bytes_read_by_host",0) for r in t["reads"] if isinstance(r.get("bytes_read_by_host",0),int));t["high_cost_reading_total"]="unknown_exact_due_to_truncated_path_survival_view; known_host_bytes is lower bound; token_count unknown";(R/"read-trace.json").write_text(json.dumps(t,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
