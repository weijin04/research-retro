#!/usr/bin/env python3
"""Reconstruct the T13b scan topology and energy from existing local originals."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

ROOT=Path('/home/sun07ao/grephene')
PROJECT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args()
output=args.output.resolve()
if not output.is_relative_to(PROJECT) or output.exists():
    ap.error('choose a fresh output path inside the framework project')
sources=[]

def read(path):
    path=path.resolve()
    assert path.is_relative_to(ROOT)
    before=path.stat(); blob=path.read_bytes(); after=path.stat()
    assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    sha=hashlib.sha256(blob).hexdigest(); snap=PROJECT/'var/audit_work/grephene/snapshots'/sha
    snap.parent.mkdir(parents=True,exist_ok=True)
    if not snap.exists():snap.write_bytes(blob)
    assert snap.read_bytes()==blob
    s=blob.decode(); sources.append({'path':str(path),'sha256':sha,'snapshot':str(snap),'size':len(blob),'line_ranges':[{'start':1,'end':len(s.splitlines())}],'read_mode':'full_bytes'})
    return s

started=datetime.now(timezone.utc).isoformat()
base=ROOT/'MECHANISM_FIELD_AUDIT_20260907/01_INVENTORY/RAW_CACHE/xj/s5_followups/T13b_cn_scan'
outpath=ROOT/'MECHANISM_FIELD_AUDIT_20260907/02_CALCULATIONS/CALC-1432_mech_loop_s5_followups_T13b_cn_scan/output/xj_8b9d1315e6_orca.out'
inp=read(base/'orca.inp'); dat=read(base/'orca.relaxscanact.dat'); raw=read(outpath)
assert 'Scan B 31 72 = 1.45, 2.65, 7' in inp and 'Scan B 31 72 = 1.45, 2.65, 7' in raw
assert '* xyzfile 0 6' in inp and '* xyzfile 0 6' in raw
assert 'ORCA TERMINATED NORMALLY' in raw
values=[list(map(float,line.split())) for line in dat.splitlines()]
table=raw.split("The Calculated Surface using the 'Actual Energy'")[-1].split('The Calculated Surface using the SCF energy')[0]
assert [list(map(float,line.split())) for line in table.strip().splitlines()]==values
steps=re.split(r'\*\s+RELAXED SURFACE SCAN STEP\s+(\d+)\s+\*',raw)
assert len(steps)==15
rows=[]; composition=None
for k,(target,energy) in enumerate(values,1):
    text=read(base/f'orca.{k:03d}.xyz'); lines=text.splitlines(); n=int(lines[0]); atoms=[x.split() for x in lines[2:2+n]]
    labels=[a[0] for a in atoms]; coords=[list(map(float,a[1:4])) for a in atoms]
    if composition is None:composition=Counter(labels); first_labels=labels
    assert labels==first_labels and n==88 and labels[72]=='N' and labels[31]=='C'
    scanned=math.dist(coords[31],coords[72]); assert abs(scanned-target)<1e-5
    segment=steps[2*k]
    # Check geometry association against the last complete Cartesian block of this step.
    blocks=segment.split('CARTESIAN COORDINATES (ANGSTROEM)')[1:]
    final=[]
    for block in blocks:
        trial=[]
        for line in block.splitlines()[2:]:
            p=line.split()
            if len(p)==4 and re.fullmatch(r'[A-Z][a-z]?',p[0]):
                try: trial.append((p[0],list(map(float,p[1:]))))
                except ValueError:break
            elif trial:break
        if len(trial)==n:final=trial
    assert len(final)==n and [x[0] for x in final]==labels
    discrepancy=max(abs(a-b) for (_,xyz),xyz2 in zip(final,coords) for a,b in zip(xyz,xyz2))
    assert discrepancy<1e-5
    carbon_distances=sorted([{'index':j,'distance_angstrom':math.dist(coords[72],xyz)} for j,xyz in enumerate(coords) if labels[j]=='C'],key=lambda x:x['distance_angstrom'])
    rows.append({'point':k,'scanned_c31_n72_angstrom':scanned,'energy_eh':energy,'delta_from_first_sample_kcal_mol':(energy-values[0][1])*627.5094740631,'nearest_carbons':carbon_distances[:5],'distance_contacts_by_cutoff':{str(c):[x['index'] for x in carbon_distances if x['distance_angstrom']<c] for c in [1.6,1.8,2.0]},'geometry_vs_output_max_abs_angstrom':discrepancy})
peak=max(rows,key=lambda x:x['energy_eh'])
assert rows[0]['distance_contacts_by_cutoff']['1.6']==[31,32]
assert set(rows[5]['distance_contacts_by_cutoff']['1.6'])=={32,33}
assert all(any(x['distance_angstrom']<1.6 for x in row['nearest_carbons']) for row in rows)
control=read(ROOT/'RESEARCH_CONTROL.md')
assert '200 °C 回迁垒区间' in control
source_control=sources[-1]
claimline=next(i for i,x in enumerate(control.splitlines(),1) if '**T13b/T15 回收**' in x)
receipt={'audit_id':'grephene-t13b-contact-migration-002','status':'completed_scoped_real_postprocessing','evidence_verdict':'mixed','started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'source_files':sources,'conditions':{'composition':dict(composition),'charge':0,'multiplicity':6,'method':'r2SCAN-3c LooseOpt TightSCF ground-state relaxed scan','frozen_atoms':len(re.findall(r'\{C\s+\d+\s+C\}',inp)),'coordinate':'C31-N72 distance, 1.45..2.65 Angstrom, seven samples','reference':'first constrained scan sample; not assumed a fully optimized unconstrained minimum'},'original_claim':{'text_verbatim':control.splitlines()[claimline-1],'locator':{'path':source_control['path'],'sha256':source_control['sha256'],'line_start':claimline,'line_end':claimline},'role':'historical plan/anticipated interpretation; source line1 already supersedes it'},'actual_question':'Does stretching C31-N72 detach N72 from the carbon surface, or does the same indexed atom retain/change short carbon contacts? Is maximum sampled electronic energy an annealing free-energy barrier?','results':{'scan_rows':rows,'peak_point':peak['point'],'peak_relative_kcal_mol':peak['delta_from_first_sample_kcal_mol'],'all_samples_retain_short_carbon_contact':True,'first_to_sixth_contacts':'C31/C32 to C32/C33 at <1.6 Angstrom'},'derivation':'A scanned bond coordinate is not equivalent to total surface detachment. Reconstruct N72-to-all-carbon distances with conserved atom labels; new short contacts survive cutoff changes 1.6/1.8/2.0. A sampled constrained electronic-energy maximum relative to the first sample is not DeltaG activation or a certified transition state.','competitive_explanations':[{'hypothesis':'N72 is fully detached after C31-N72 reaches 2.45 Angstrom','result':'refuted_in_scope','reason':'Two other carbon contacts remain 1.45515/1.45517 Angstrom.'},{'hypothesis':'Rebonding inference arises from atom renumbering or mismatched cached geometry','result':'refuted_in_scope','reason':'Atom-label arrays identical and each saved geometry matches its actual scan-output block within 1e-5 Angstrom.'},{'hypothesis':'The sample peak is still a useful energetic observation','result':'supported_with_scope','reason':'Peak is reproducible from primary output and dat; retain as sampled constrained electronic energy relative to first sample.'},{'hypothesis':'These data exclude a different annealing or recovery pathway','result':'unsupported','reason':'Single coordinate and fixed multiplicity do not cover competing pathways or the experimental recovery observable.'}],'first_failing_condition':'Single C31-N72 stretch ceases to represent total detachment; N72-C32 remains <1.6 Angstrom throughout and C33 becomes another short neighbor at point6.','retained_assets':['Seven matched geometries and energies','Distance-defined contact migration within this model','Peak electronic energy under explicit reference'], 'residual_unknowns':['Formal electronic bond order not computed by distance check','Stationary saddle and continuous reaction path between samples','Entropy/free-energy effects and actual 200 Celsius experimental recovery channel'],'new_authorization_needed':'None to correct this claim. New quantum/MD/kinetic calculations require separate authorization if the scientific question later demands them.','execution':{'script':str(Path(__file__).resolve()),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_scripts_executed':False,'new_scientific_jobs':0,'external_calls':0,'exit_status':0,'checks':['input/output protocol','7 point energy table identity','atom identity across all frames','actual output vs saved geometry','scanned distance consistency','all-carbon distance reconstruction','cutoff robustness']}}
output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(output),'peak_kcal_mol':peak['delta_from_first_sample_kcal_mol'],'point6':rows[5],'sources':len(sources)},ensure_ascii=False,indent=2))
