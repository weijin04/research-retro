import json,hashlib,datetime,ast
from pathlib import Path
import numpy as np
from ase.io import read,Trajectory
from ase.geometry import find_mic
ROOT=Path('/home/sun07ao/retro-workspaces/retro-product-evaluation/reconstruction.retro/exports/product-repacked-A')
OUT=Path(__file__).parent
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
index=json.loads((ROOT/'SOURCE_INDEX.json').read_text())['sources'];sources=[]
def src(suffix):
 matches=[(k,v) for k,v in index.items() if k.endswith(suffix)]
 assert len(matches)==1
 label,versions=matches[0];assert len(versions)==1
 ent=versions[0];p=ROOT/ent['blob'];b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==p.name
 assert ent.get('identity_scope')=='whole_file'
 sources.append(dict(label=label,blob=ent['blob'],sha256=p.name,bytes=len(b)))
 return p
net=json.loads(src('validation/networks/coni-dab.json').read_text());ref=read(src('benchmarks/structures/coni-dab.cif'),format='cif')
# Parse only the two captured pure geometry functions, never run the historical module or its CLI.
script=src('r3/analyze_window.py');tree=ast.parse(script.read_text());selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['unwrapped_center','free_radius_from_center']]
assert len(selected)==2
ns=dict(np=np,find_mic=find_mic,GUEST_SYMBOLS={'Kr','Xe'},VDW_A={'H':1.09,'C':1.7,'N':1.55,'O':1.52,'Zn':1.39,'Co':2.,'Ni':1.63})
# Assert actual table is the same for elements used here.
for n in tree.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VDW_A' for t in n.targets):
  table=ast.literal_eval(n.value)
  for sym in ['H','C','N']:assert table[sym]==ns['VDW_A'][sym],(sym,table)
exec(compile(ast.Module(body=selected,type_ignores=[]),str(script),'exec'),ns)
def calc(a,inds):
 c=ns['unwrapped_center'](a.positions,inds,a.cell.array,a.pbc)
 r,_=ns['free_radius_from_center'](c,a.positions,a.get_chemical_symbols(),a.cell.array,a.pbc)
 return c,r
rows=[];identity=[]
for label,suffix in [('195K','r3/md/conidab_195_final.traj'),('298K','r3/md/conidab_298_final.traj')]:
 traj=Trajectory(src(suffix));frames=sorted(set([0,len(traj)//4,len(traj)//2,3*len(traj)//4,len(traj)-1]))
 for fi in frames:
  a=traj[fi];assert a.get_chemical_symbols()==ref.get_chemical_symbols();assert np.allclose(a.cell.array,ref.cell.array)
  identity.append(dict(temperature_label=label,frame=fi,n_frames=len(traj),symbols_match=True,cell_match=True))
  for w in net['windows']:
   inds=w['defining_atom_indices'];c0,r0=calc(ref,inds);c,r=calc(a,inds);base=r+w['free_radius_A']-r0
   for shift in range(1,len(inds)):
    perm=inds[shift:]+inds[:shift];cp0,rp0=calc(ref,perm);cp,rp=calc(a,perm)
    rawcenter=float(find_mic((cp0-c0)[None,:],ref.cell.array,ref.pbc)[1][0])
    permcal=rp+w['free_radius_A']-rp0
    rows.append(dict(temperature_label=label,frame=fi,window=w['id'],shift=shift,static_center_difference_A=rawcenter,static_raw_radius_difference_A=rp0-r0,base_calibrated_A=base,permuted_recalibrated_A=permcal,calibrated_difference_A=permcal-base))
import csv
with (OUT/'permutation_checks.csv').open('w') as f:
 wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
res=dict(start_utc=start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),question='Does unchanged unordered defining-atom membership preserve the historical window observable after per-order static recalibration?',source_hashes=sources,identity_checks=identity,n_comparisons=len(rows),n_dynamic_differences_over_1e_6=sum(abs(r['calibrated_difference_A'])>1e-6 for r in rows),max_dynamic_difference=max(rows,key=lambda r:abs(r['calibrated_difference_A'])),max_static_center_difference=max(rows,key=lambda r:r['static_center_difference_A']),affected_windows=sorted(set(r['window'] for r in rows if abs(r['calibrated_difference_A'])>1e-6)))
(OUT/'results.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
