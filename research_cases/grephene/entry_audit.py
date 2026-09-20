#!/usr/bin/env python3
"""Read-only EA(Q) reconstruction. Never invokes scientific/source executables."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

PROJECT=Path(__file__).resolve().parents[2]
ROOT=Path('/home/sun07ao/grephene')
BASE=ROOT/'research/pro_evidence_rebuild_20260915/raw_live_xj/entry_remaining/tms_arm/iso'
EV=27.211386245988
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args(); output=args.output.resolve()
if output.exists() or not output.is_relative_to(PROJECT):ap.error('use a fresh --output inside framework project')
started=datetime.now(timezone.utc).isoformat()
source_files={}; cache={}; groups={}; warnings=[]

def read(path,role='primary',patterns=None):
    path=path.resolve(); key=str(path)
    assert path.is_relative_to(ROOT)
    if key in cache:return cache[key]
    before=path.stat(); blob=path.read_bytes(); after=path.stat()
    assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'source_changed'
    sha=hashlib.sha256(blob).hexdigest(); snap=PROJECT/'var/audit_work/grephene/entry_snapshots'/sha
    snap.parent.mkdir(parents=True,exist_ok=True)
    if not snap.exists():snap.write_bytes(blob)
    assert snap.read_bytes()==blob
    text=blob.decode(errors='replace'); lines=text.splitlines()
    ranges=[{'start':max(1,i-1),'end':min(len(lines),i+1)} for i,line in enumerate(lines,1) if patterns and any(re.search(p,line) for p in patterns)]
    source_files[key]={'path':key,'sha256':sha,'snapshot':str(snap),'size':len(blob),'role':role,'read_mode':'full_bytes','line_ranges':ranges or [{'start':1,'end':len(lines)}]}
    cache[key]=text; return text

def input_geometry(text):
    match=re.search(r'\*\s+xyz\s+(-?\d+)\s+(\d+)',text)
    assert match
    rows=text[match.end():].split('*')[0].strip().splitlines()
    labels=[r.split()[0] for r in rows]
    coords=[list(map(float,r.split()[1:4])) for r in rows]
    return int(match[1]),int(match[2]),labels,coords

def out_geometries(text):
    found=[]
    lines=text.splitlines()
    for i,line in enumerate(lines):
        if line.strip()!='CARTESIAN COORDINATES (ANGSTROEM)':continue
        rows=[]
        for l in lines[i+2:]:
            p=l.split()
            if len(p)==4 and re.fullmatch(r'[A-Z][a-z]?',p[0]):
                try:rows.append((p[0],list(map(float,p[1:]))))
                except ValueError:break
            elif rows:break
        if rows:found.append((rows,i+1,i+2+len(rows)))
    return found

def compare(labels,a,blabels,b,tol=1e-5):
    assert labels==blabels
    error=max(abs(x-y) for xa,xb in zip(a,b) for x,y in zip(xa,xb))
    assert error<tol,('geometry_mismatch',error)
    return error

def parse_job(d,expected_method=None,allow_failed=False):
    inp=read(d/'orca.inp','primary_input'); out=read(d/'orca.out','primary_output',[r'FINAL SINGLE POINT ENERGY','TERMINATED NORMALLY',r'Expectation value of <S\*\*2>',r'\* xyz',r'T1 diagnostic',r'D1 diagnostic'])
    q,m,l,c=input_geometry(inp)
    echo=re.search(r'\*\s+xyz\s+(-?\d+)\s+(\d+)',out)
    assert echo and (int(echo[1]),int(echo[2]))==(q,m)
    if expected_method:assert expected_method in inp.splitlines()[0] and expected_method in out
    normal='ORCA TERMINATED NORMALLY' in out
    energies=re.findall(r'FINAL SINGLE POINT ENERGY\s+([-\d.]+)',out)
    if not allow_failed:assert normal and energies
    geom=out_geometries(out)
    assert geom
    first,start,end=geom[0]
    compare(l,c,[x[0] for x in first],[x[1] for x in first])
    source_files[str((d/'orca.out').resolve())]['line_ranges'].append({'start':start,'end':end})
    s2=re.findall(r'Expectation value of <S\*\*2>\s*:\s*([-\d.]+)',out)
    return {'path':str(d),'charge':q,'multiplicity':m,'labels':l,'coords':c,'energy_eh':float(energies[-1]) if energies else None,'normal_termination':normal,'s2':float(s2[-1]) if s2 else None,'method_line':inp.splitlines()[0],'sources':[str((d/'orca.inp').resolve()),str((d/'orca.out').resolve())]}

brief=read(ROOT/'mech_loop/entry_competition_20260911/tms_arm/BRIEF.md','historical_design')
jobs=read(ROOT/'mech_loop/entry_competition_20260911/tms_arm/JOBS.md','historical_execution_report')
control=read(ROOT/'RESEARCH_CONTROL.md','historical_assertion')
code=read(BASE/'common/azide_chain.py','historical_source_code_not_executed',[r'def job_succeeded',r'return \("HURRAY"',r'first EA_vert',r'ea_vert_eV',r'crossing_geom',r'if ok2',r'if ok3'])
assert 'return ("HURRAY" in txt) or ("TERMINATED NORMALLY" in txt)' in code
assert 'rec["neu"].get("TZVP")' in code
all_rows=[]; provenance_checks=[]
for mol,indices in [('TMS',(2,1,0,3)),('PFPA',(17,18,19,3))]:
    wrapper=read(BASE/mol/'run_iso.py','historical_source_code_not_executed')
    alpha,beta,gamma,rsite=indices
    for route,step,q in [('neuscan','step2_neutral_scan',0),('anscan','step3_anion_scan',-1)]:
        d=BASE/mol/step
        scan_inp=read(d/'orca.inp','primary_scan_input')
        scan_out=read(d/'orca.out','primary_scan_output',[r'RELAXED SURFACE SCAN STEP',r'HURRAY',r'TERMINATED NORMALLY',r'aborting',r'error termination'])
        scan_dat=read(d/'orca.relaxscanact.dat','primary_scan_table') if (d/'orca.relaxscanact.dat').exists() else None
        if scan_dat is None:warnings.append({'molecule':mol,'route':route,'missing_original':str(d/'orca.relaxscanact.dat'),'effect':'No summary table here; SP pairs and saved geometries remain individually auditable.'})
        assert re.search(r'Scan B\s+'+str(alpha)+r'\s+'+str(beta)+r'\s*=\s*1.24,\s*2.04,\s*9',scan_inp)
        assert re.search(r'\*\s+xyz\s+'+str(q)+r'\s+'+('1' if q==0 else '2'),scan_inp)
        scan_segments=re.split(r'RELAXED SURFACE SCAN STEP\s+(\d+)',scan_out)
        point_segments={int(scan_segments[i]):scan_segments[i+1] for i in range(1,len(scan_segments),2)}
        raw_table=scan_out.split("The Calculated Surface using the 'Actual Energy'")
        table_verified=False
        if len(raw_table)>1:
            tab=raw_table[-1].split('The Calculated Surface using the SCF energy')[0]
            numbers=[list(map(float,l.split())) for l in tab.strip().splitlines() if len(l.split())==2 and re.fullmatch(r'[\d.]+',l.split()[0])]
            table_verified=scan_dat is not None and numbers==[list(map(float,l.split())) for l in scan_dat.splitlines()]
        provenance_checks.append({'molecule':mol,'route':route,'scan_output_normal': 'ORCA TERMINATED NORMALLY' in scan_out,'scan_steps_present':sorted(point_segments),'scan_table_verified_against_output':table_verified,'historical_warning':'PFPA neutral scan log reported overwritten; do not reconstruct missing convergence from current partial log.' if mol=='PFPA' and route=='neuscan' else None})
        for point in range(1,10):
            pxyz=d/f'orca.{point:03d}.xyz'; text=read(pxyz,'primary_saved_scan_geometry'); ls=text.splitlines(); n=int(ls[0]); fields=[x.split() for x in ls[2:2+n]]; syms=[x[0] for x in fields]; coords=[list(map(float,x[1:4])) for x in fields]
            nn=math.dist(coords[alpha],coords[beta]); assert abs(nn-(1.24+0.1*(point-1)))<1e-5
            segment=point_segments.get(point,''); convergence=('HURRAY' in segment or 'OPTIMIZATION RUN DONE' in segment) if segment else None
            geom_blocks=out_geometries(segment)
            if geom_blocks:
                rows,_,_=geom_blocks[-1]
                try:compare(syms,coords,[x[0] for x in rows],[x[1] for x in rows])
                except AssertionError:
                    warnings.append({'molecule':mol,'route':route,'point':point,'warning':'saved geometry differs from current scan output; current output may be overwritten or truncated; SP geometry remains checked directly'})
            for basis in ['TZVP','TZVPD']:
                pair={}
                for charge,qexp,mexp in [('neu',0,1),('an',-1,2)]:
                    job=parse_job(BASE/mol/'step5_sp'/f'{route}_pt{point:02d}_{charge}_{basis}','wB97X-D4')
                    assert (job['charge'],job['multiplicity'])==(qexp,mexp)
                    assert 'def2-'+basis in job['method_line']
                    assert len(job['labels'])==n and dict(Counter(job['labels']))==({'C':3,'H':9,'N':3,'Si':1} if mol=='TMS' else {'C':8,'F':4,'H':3,'N':3,'O':2})
                    compare(syms,coords,job['labels'],job['coords'],1e-10)
                    pair[charge]=job
                compare(pair['neu']['labels'],pair['neu']['coords'],pair['an']['labels'],pair['an']['coords'],1e-12)
                ba=[coords[alpha][i]-coords[beta][i] for i in range(3)]; bg=[coords[gamma][i]-coords[beta][i] for i in range(3)]
                angle=math.degrees(math.acos(max(-1,min(1,sum(a*b for a,b in zip(ba,bg))/(math.sqrt(sum(a*a for a in ba))*math.sqrt(sum(b*b for b in bg)))))))
                key=f'{mol.lower()}_{route}_{point:02d}_{basis.lower()}'
                groups[key]={'sources':pair['neu']['sources']+pair['an']['sources']+[str(pxyz.resolve()),str((d/'orca.inp').resolve())],'scope':f'{mol} {route} point{point} {basis}: same-geometry ground-state E(neutral)-E(anion), specified singlet/doublet, with input-frame identity.','rationale':'EA requires this matched charge pair, not any energies from another geometry or method. Parent scan input identifies nominal coordinate; separate scan convergence is not inferred from SP completion.','checked_relations':['composition and charge/multiplicity','input vs output initial geometry','neutral/anion exact input geometry equality','SP geometry vs saved parent frame','normal termination','method and basis'],'limitations':['Finite-basis method-relative energy difference, not a measured gas-phase binding certification.','No interface electron reservoir, continuum scattering, capture rate or productive path proved.']}
                all_rows.append({'group':key,'molecule':mol,'route':route,'point':point,'basis':basis,'nalpha_nbeta_angstrom':nn,'nbeta_ngamma_angstrom':math.dist(coords[beta],coords[gamma]),'r_nalpha_angstrom':math.dist(coords[rsite],coords[alpha]),'n_n_n_angle_degree':angle,'neutral_energy_eh':pair['neu']['energy_eh'],'anion_energy_eh':pair['an']['energy_eh'],'ea_vertical_ev':(pair['neu']['energy_eh']-pair['an']['energy_eh'])*EV,'anion_s2':pair['an']['s2'],'neutral_s2':pair['neu']['s2'],'parent_step_convergence_marker':convergence,'sample_status':'not_certified_relaxed_point' if convergence is not True else 'parent_convergence_marker_present','note':'At TMS neutral point9 retain a fixed-geometry SP observation only; known incomplete parent step.' if mol=='TMS' and route=='neuscan' and point==9 else ''})

# Independently reproduce old vertical EA using final optimized neutral geometry.
oldroot=ROOT/'mech_loop/s5_followups/T10'
oldneu=parse_job(oldroot/'TMSN3_isolated','r2SCAN-3c')
oldan=parse_job(oldroot/'TMSN3_anion_vert','r2SCAN-3c')
finalgeo=out_geometries(cache[str((oldroot/'TMSN3_isolated/orca.out').resolve())])[-1][0]
compare(oldan['labels'],oldan['coords'],[x[0] for x in finalgeo],[x[1] for x in finalgeo])
legacy={'ea_vertical_ev':(oldneu['energy_eh']-oldan['energy_eh'])*EV,'neutral_energy_eh':oldneu['energy_eh'],'anion_energy_eh':oldan['energy_eh'],'scope':'r2SCAN-3c fixed neutral optimized geometry; both normal; same final neutral/anion input geometry'}
groups['tms_legacy_r2_ea']={'sources':oldneu['sources']+oldan['sources'],'scope':legacy['scope'],'rationale':'Preserve old value within its actual method, not declare fabrication.'}

# Existing higher-level minimum and separated endpoint checks; failures retained.
dlpno={}
for mol in ['TMS','PFPA']:
    dlpno[mol]={}
    for tag in ['neutral_min','vertical_anion_at_min','RN_anion','RN_triplet','N2','anion_scan_EAvert_crossing']:
        job=parse_job(BASE/mol/'step6_dlpno'/tag,'DLPNO-CCSD(T)',allow_failed=True)
        dlpno[mol][tag]=job
    neu=dlpno[mol]['neutral_min']; an=dlpno[mol]['vertical_anion_at_min']
    compare(neu['labels'],neu['coords'],an['labels'],an['coords'],1e-12)
    if neu['normal_termination'] and an['normal_termination']:
        dlpno[mol]['minimum_vertical_ea_ev']=(neu['energy_eh']-an['energy_eh'])*EV
        groups[mol.lower()+'_minimum_dlpno_ea']={'sources':neu['sources']+an['sources'],'scope':'DLPNO-CCSD(T)/aug-cc-pVTZ same neutral-minimum geometry vertical EA; finite-basis method-specific estimate','rationale':'Independent actual completed charge-pair arithmetic; no hybrid/DLPNO energy subtraction.'}
    rna=dlpno[mol]['RN_anion']; n2=dlpno[mol]['N2']
    if all(x['normal_termination'] for x in [neu,rna,n2]):
        assert Counter(neu['labels'])==Counter(rna['labels'])+Counter(n2['labels'])
        assert neu['charge']==0 and rna['charge']==-1 and n2['charge']==0
        dlpno[mol]['separated_dissociative_attachment_ev']=(rna['energy_eh']+n2['energy_eh']-neu['energy_eh'])*EV
        groups[mol.lower()+'_separated_dlpno_dea_endpoint']={'sources':neu['sources']+rna['sources']+n2['sources'],'scope':'RN3 + free electron at vacuum zero -> RN(-) + N2, separated optimized endpoints, molecular electronic reaction energy only','rationale':'Element-balanced endpoint sum at one method; electron reference explicitly vacuum zero. It is not a pathway barrier or interface CT cost.'}
    cross=dlpno[mol]['anion_scan_EAvert_crossing']
    target=next(x for x in all_rows if x['molecule']==mol and x['route']=='anscan' and x['basis']=='TZVP' and x['ea_vertical_ev']>0)
    refjob=parse_job(BASE/mol/'step5_sp'/f"anscan_pt{target['point']:02d}_an_TZVP",'wB97X-D4')
    compare(cross['labels'],cross['coords'],refjob['labels'],refjob['coords'],1e-12)
    dlpno[mol]['selected_crossing_point']=target['point']
    dlpno[mol]['crossing_selection_scope']='first sampled EA>0 on separately optimized anion geometry using TZVP, not an intersection located along the neutral approach trajectory'

summaries=[]
for mol in ['TMS','PFPA']:
    for basis in ['TZVP','TZVPD']:
        q0=next(r for r in all_rows if r['molecule']==mol and r['basis']==basis and r['route']=='neuscan' and r['point']==1)['neutral_energy_eh']
        for route in ['neuscan','anscan']:
            rows=[r for r in all_rows if r['molecule']==mol and r['basis']==basis and r['route']==route]
            for row in rows:
                row['neutral_deformation_from_neuscan_first_ev']=(row['neutral_energy_eh']-q0)*EV
                row['anion_height_from_neuscan_first_plus_vacuum_electron_ev']=(row['anion_energy_eh']-q0)*EV
                assert abs(row['neutral_deformation_from_neuscan_first_ev']-row['ea_vertical_ev']-row['anion_height_from_neuscan_first_plus_vacuum_electron_ev'])<1e-8
            summaries.append({'molecule':mol,'basis':basis,'route':route,'ea_ev':[r['ea_vertical_ev'] for r in rows],'first_positive_sample':next((r['point'] for r in rows if r['ea_vertical_ev']>0),None),'anion_heights_vacuum_reference_ev':[r['anion_height_from_neuscan_first_plus_vacuum_electron_ev'] for r in rows]})

primary_claim_line=next(i for i,l in enumerate(control.splitlines(),1) if 'EA_vert 全负' in l)
control_path=str((ROOT/'RESEARCH_CONTROL.md').resolve())
claims=[{'id':'entry-historical-dea-exclusion','text_verbatim':control.splitlines()[primary_claim_line-1],'source_locator':{'path':control_path,'sha256':source_files[control_path]['sha256'],'line_start':primary_claim_line,'line_end':primary_claim_line},'qualification':'historical compound report: not all its species or scans are covered here'}]
result={'id':'grephene-entry-ea-geometry-003','audit_id':'grephene-entry-ea-geometry-003','schema_version':'audit-case-local-1','project_id':'grephene-development','status':'completed_scoped_real_postprocessing','evidence_verdict':'mixed','original_claims':claims,'conditions':{'molecules':['isolated TMSN3 C3H9N3Si','isolated PFPA-Me C8F4H3N3O2'],'electron_affinity_definition':'EA(Q)=E_neutral(Q)-E_anion(Q), positive means energy lowering for a vacuum-zero electron within the tested method','charge_spin':'neutral 0/1, anion -1/2 for all 144 hybrid SP jobs','geometry':'both separately r2SCAN optimized neutral and anion scan lineages; no cross-geometry subtraction in EA','hybrid_methods':['wB97X-D4/def2-TZVP','wB97X-D4/def2-TZVPD'],'higher_level':'existing DLPNO-CCSD(T)/aug-cc-pVTZ TightPNO checks; unsuccessful PFPA jobs retained','not_in_model':['graphene electronic reservoir','interface polarization/coupling','capture kinetics','experimental film identity']},'actual_question':'Which target did the old negative EA measure; how does same-geometry EA depend on geometry, molecule and basis; does this establish or exclude an interface DEA pathway?','source_files':list(source_files.values()),'source_groups':groups,'actual_results':{'legacy_tms_r2':legacy,'ea_rows':all_rows,'curve_summaries':summaries,'parent_scan_checks':provenance_checks,'dlpno':dlpno,'warnings':warnings},'analysis':{'script':str(Path(__file__).resolve()),'actual_results':'top-level actual_results','derivations':['EA(Q)=E0(Q)-E-(Q); never E0(Q_neutral)-E-(Q_anion) as a vertical quantity.','E-(Q)-E0(Q0)=[E0(Q)-E0(Q0)]-EA(Q); positive EA on a deformed geometry does not eliminate deformation/access cost.','RN3+e(vacuum)->RN(-)+N2 endpoint energy is element/electron balanced but gives neither a reaction barrier nor a graphene-injection energy.','A first sampled EA>0 on the anion-optimized lineage is not evidence that the neutral initial trajectory reached that geometry or crossed the surfaces.'],'code_path_checks':['job_succeeded treats any HURRAY OR normal termination as success: one successful scan window can mask a failed later window.','A5 generates charge pairs from each saved scan geometry. Exact input coordinates and current parent snapshots matched here.','A6 selects the first positive TZVP EA point along anion scan; both systems choose point1. It is not a numerically solved energy-surface intersection.'],'historical_code_identity':'current archived code read, not proven original invocation byte-version; actual input/output checks independent of this uncertainty'},'competitive_explanations':[{'hypothesis':'Old TMS EA -2.13 was arithmetically wrong','verdict':'refuted_in_scope','reason':'Recomputed old raw r2SCAN energies and matched final neutral geometry recover the old value.'},{'hypothesis':'TMS is always vertically endothermic along the tested coordinate','verdict':'refuted_in_scope','reason':'Neutral-lineage sample6 onward has positive hybrid EA; anion-lineage geometries are positive from sample1.'},{'hypothesis':'Positive anion-lineage EA proves easy injection from the initial neutral configuration','verdict':'unsupported','reason':'At same Nalpha-Nbeta 1.24 Angstrom, other coordinates differ strongly; deformation plus electronic attachment costs remain explicit.'},{'hypothesis':'PFPA can be substituted for TMS in entry verdict','verdict':'unsupported','reason':'Same-protocol first neutral-lineage EA differs in sign; PFPA is a distinct molecule/control.'},{'hypothesis':'Finite basis/method and an unbound extra electron undermine a universal quantitative threshold','verdict':'qualified','reason':'TMS initial vertical EA magnitude changes substantially from r2SCAN to diffuse hybrid and completed DLPNO. No continuum/basis-limit validation performed.'},{'hypothesis':'TMS neutral point9 negative rebound proves reentrant bound/unbound physics','verdict':'invalid_test','reason':'Parent relaxed point not converged; retain only its fixed-geometry SP result, not a certified relaxed trend.'}],'support_scope':['Old TMS fixed-geometry r2SCAN negative EA reproduced.','Matched molecular hybrid EA(Q) and their composition/geometry/basis dependence.','Completed TMS molecular DLPNO minimum and separated-endpoint electronic energetics.','Limits on historical broad exclusion without asserting interface DEA succeeds.'],'first_failing_condition':'The inference changes from one molecular vertical attachment geometry/method to a whole interface dissociative entry pathway or another precursor; geometry and electron reservoir obligations are missing.','retained_assets':['All matched SP charge pairs','scan geometries with per-point provenance/convergence qualification','valid old r2SCAN vertical EA observation','completed higher-level endpoint calculations'],'residual_unknowns':['Electron attachment resonances/continuum and basis-limit energetics','access to bent anion-lineage geometries before capture','interface CT/coupling/charge redistribution and productive N2-loss connection','experimental precursor identity and branch yield','PFPA neutral scan original full convergence log missing/overwritten; five higher-level jobs incomplete'],'needs_new_authorization':'No new calculation required to complete this bounded reconstruction. Interface mechanism resolution or missing higher-level jobs would require separate research authorization.','r2_release_effect':'LB-ENTRY-COMPETITION is resolved for the exact legacy-EA target and its overbroad transfer. A reconstruction can report TMS entry as unresolved with these retained molecular constraints. It cannot claim either global DEA exclusion or a preferred productive mechanism from this audit.','execution_receipt':{'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'exit_status':0,'mode':'real_local_stdlib_postprocessing','script':str(Path(__file__).resolve()),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_scripts_executed':False,'new_scientific_jobs':0,'external_calls':0,'completed_hybrid_sp_pairs':len(all_rows),'checks':['144 input/output method-charge-spin-geometry checks','72 exact same-geometry charge-pair EAs','36 saved parent geometries matched to SP input','r2SCAN old vertical geometry and arithmetic','DLPNO completed/failed outputs retained','atom/electron-balanced molecular endpoint sum','crossing selector actual chosen geometry','energy-reference decomposition identity']},'inference_dependencies':{'entry-c-old-r2-ea':[['tms_legacy_r2_ea']],'entry-c-tms-neu-q6-positive':[['tms_neuscan_06_tzvp'],['tms_neuscan_06_tzvpd']],'entry-c-tms-min-dlpno-ea':[['tms_minimum_dlpno_ea']],'entry-c-tms-dea-endpoint':[['tms_separated_dlpno_dea_endpoint']]}}
output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(output),'sources':len(source_files),'old_tms':legacy,'curve_summaries':summaries,'dlpno_summary':{m:{k:v for k,v in rec.items() if not isinstance(v,dict)} for m,rec in dlpno.items()},'warnings':warnings},ensure_ascii=False,indent=2))
