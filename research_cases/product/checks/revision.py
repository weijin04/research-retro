from pathlib import Path
import json, statistics
base=Path('/home/sun07ao/retro-workspaces/retro-product-evaluation/cxekr-loop-20260921-A/materials/cxekr')
s=json.loads((base/'artifacts/experiment/v13_finite_t_smoke/result.json').read_text())
out={'barrier_materials':sorted(p.stem for p in (base/'validation/v13/barrier_components').glob('*.json')), 'smoke_material':s['material'],'runs':[]}
for run in s['runs']:
 p=base/Path(run['files']['colvar']).relative_to('/home/sun07ao/cxekr')
 lines=p.read_text().splitlines();fields=next(x.split()[2:] for x in lines if x.startswith('#! FIELDS'))
 rows=[list(map(float,x.split())) for x in lines if x and not x.startswith('#')]
 rows=[row for row in rows if row[0]>500]
 out['runs'].append({'gas':run['gas'],'seed':run['velocity_seed'],'fields':fields,'rows':len(rows),'reported_sd':run['path_s_standard_deviation_A'],'columns_sd':{f:statistics.stdev([row[i] for row in rows]) for i,f in enumerate(fields)}})
b=json.loads((base/'validation/v13/barrier_components/coni-dab.json').read_text())['models'][0]['components']
out['opening_fraction_kr']=b['host_opening_only']['gases']['Kr']['B_kjmol']/b['full_proxy']['gases']['Kr']['B_kjmol']
out['delta_opening_fraction']=b['host_opening_only']['delta_kin_kjmol']/b['full_proxy']['delta_kin_kjmol']
print(json.dumps(out,ensure_ascii=False,indent=2))
