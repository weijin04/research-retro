import json, pathlib, hashlib
B=pathlib.Path('/home/sun07ao/retro-workspaces/retro-product-evaluation/upstream-judgment.retro/exports/reasoner-B-final')
W=pathlib.Path(__file__).resolve().parent
sources=json.loads((B/'SOURCE_INDEX.json').read_text())['sources']
used=[]
def get(suffix):
 matches=[(p,e[0]) for p,e in sources.items() if p.endswith(suffix)]
 assert len(matches)==1
 p,e=matches[0]; raw=(B/e['blob']).read_bytes()
 used.append(dict(original_path=p, captured_path=str(B/e['blob']), sha256=hashlib.sha256(raw).hexdigest(), identity_scope=e['identity_scope'], byte_range=e['byte_range'], original_size_bytes=e['original_size_bytes']))
 return raw.decode()
r=json.loads(get('v13_finite_t_smoke/result.json'))
get('v13_finite_t_smoke/RESULTS.md')
report=get('v13_s_only_validation/RESULTS.md')
code=get('v13_s_only_validation/analyze.py')
get('v13_reus_cross_initialization/PLAN.md')
get('cxekr_loop/r5/feasibility-note.md')
rows=[]
for x in r['runs']:
 temp_error=abs(x['mean_temperature_K']/r['settings']['temperature_K']-1)
 rows.append(dict(gas=x['gas'],seed=x['velocity_seed'], observation_ps=x['production_steps']*r['settings']['timestep_fs']/1000, frame_stride_duration_ps=x['production_frame_count']*x['observed_colvar_stride_fs']/1000,temperature_relative_error_recomputed=temp_error,reported_summary_gates_pass=temp_error<.1 and x['maximum_path_s_deviation_A']<.5 and x['maximum_mobile_host_displacement_A']<3 and x['maximum_path_z2_A2']<r['settings']['tube_wall_at_A2'], target=x['target_path_s_A']))
result={'smoke_summary_recheck':rows,'limitation':'Summary-level recomputation, not raw COLVAR verification. Four 1ps records do not establish independent samples or stationarity.', 'later_validation_original_report':{'runs':20,'gases':2,'windows_per_gas':5,'replicas':2,'adjacent_edges_expected':2*(5-1),'overlap_min_Kr':.339,'overlap_min_Xe':.322,'overlap_threshold':.10,'minimum_overlap_margin':.322-.10,'Xe_ESS_failed_windows':4,'Xe_ESS_shortfall_range':[200-184.5,200-152.0],'failed_stationarity_runs':4,'reported_umbrella_tail_duration_fs':43*2.5,'strict_validation':False},'raw_validation_recomputed':False, 'long_repair_named_sources_in_index':[p for p in sources if 'v13_s_only_validation_long/' in p], 'candidate_continuation':'Recover named v13_s_only_validation_long result, frozen protocol and full trajectories first; assess unchanged ESS/stationarity gates before considering any new overlap pilot.'}
(W/'sources_used.json').write_text(json.dumps(used,ensure_ascii=False,indent=2)+'\n')
(W/'check_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
