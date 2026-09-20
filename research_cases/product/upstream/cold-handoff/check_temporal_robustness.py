#!/usr/bin/env python3
"""Read only frozen captured bytes; no external source paths are opened.
Descriptive cut sensitivity and nonoverlapping time blocks, not independent trials.
"""
import csv, io, json, hashlib, statistics
from pathlib import Path
B=Path('/home/sun07ao/retro-workspaces/retro-product-evaluation/upstream-judgment.retro/exports/reasoner-r225')
O=Path(__file__).resolve().parent
index=json.loads((B/'SOURCE_INDEX.json').read_text())['sources']
reads=[]
def read(suffix):
    matches=[(p,e) for p,es in index.items() if p.endswith(suffix) for e in es if e['identity_scope']=='whole_file']
    assert len(matches)==1, (suffix,len(matches))
    p,e=matches[0]; data=(B/e['blob']).read_bytes()
    assert len(data)==e['original_size_bytes']
    reads.append(dict(source=p,blob=e['blob'],sha256=hashlib.sha256(data).hexdigest(),scope=e['identity_scope']))
    return data.decode()
def q(xs,p):
    a=sorted(xs); z=(len(a)-1)*p;i=int(z)
    return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(z-i)
def summarize(rs):
    v=[r['r_mainwindow_A'] for r in rs]
    return dict(n=len(rs),q50=q(v,.5),q95=q(v,.95),mean=statistics.mean(v),max=max(v),above_Kr=sum(x>=1.818 for x in v),above_Xe=sum(x>=2.05 for x in v))
series={};results={};frames=[]
for species in ['gf','kr','xe']:
    rows=list(csv.DictReader(io.StringIO(read('r3/analysis-'+species+'-final.csv'))))
    rows=[{k:float(v) if k not in ['bottleneck_window_id','bottleneck_window_id_raw'] else v for k,v in r.items()} for r in rows]
    assert len(rows)==2001 and all(r['frame']==i and r['t_ps']==i*.5 for i,r in enumerate(rows))
    summary=json.loads(read('r3/analysis-'+species+'-final.json'))
    post=[r for r in rows if r['t_ps']>=10]
    reproduced=summarize(post)
    assert abs(reproduced['q50']-summary['r_mainwindow']['q50_A'])<1e-6
    assert abs(reproduced['q95']-summary['r_mainwindow']['q95_A'])<1e-6
    residual=max(abs(r['r_mainwindow_A']-min(r['r_w0025_A'],r['r_w0020_A'])) for r in rows)
    series[species]=rows
    results[species]={'baseline':reproduced,'main_min_residual_A':residual,'cuts':{},'blocks':{}}
    for cut in [10,100,250,500,750]:results[species]['cuts'][str(cut)]=summarize([r for r in rows if r['t_ps']>=cut])
    for lo,hi in [(10,200),(200,400),(400,600),(600,800),(800,1000.5)]:
        rs=[r for r in rows if lo<=r['t_ps']<hi]
        results[species]['blocks'][str(lo)+'-'+str(hi)]=summarize(rs)
    for name,p in [('median',.5),('upper95',.95),('maximum',1)]:
        target=q([r['r_mainwindow_A'] for r in post],p)
        r=min(post,key=lambda r:(abs(r['r_mainwindow_A']-target),r['frame']))
        frames.append(dict(species=species,selection=name,target_A=target,frame=int(r['frame']),t_ps=r['t_ps'],radius_A=r['r_mainwindow_A'],limiting_window='w0025' if r['r_w0025_A']<=r['r_w0020_A'] else 'w0020'))
comparisons={}
for kind in ['cuts','blocks']:
    comparisons[kind]={k:{sp:results[sp][kind][k]['q50']-results['gf'][kind][k]['q50'] for sp in ['kr','xe']} for k in results['gf'][kind]}
coordinate_sources=[p for p in index if p.lower().endswith(('.traj','.xyz','.cif','.pdb','.dump','.lammpstrj','.xtc','.dcd'))]
out=dict(method='Descriptive serial cut and time-block sensitivity; no iid confidence intervals or causal claim',results=results,loaded_minus_gf_median_A=comparisons,coordinate_sources=coordinate_sources,source_receipts=reads)
(O/'results.json').write_text(json.dumps(out,indent=2)+'\n')
with (O/'representative_frames.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(frames[0]));w.writeheader();w.writerows(frames)
print(json.dumps(comparisons,indent=2)); print('frames',frames)
