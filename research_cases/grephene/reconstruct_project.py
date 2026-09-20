#!/usr/bin/env python3
"""Build scoped historical reconstruction with read-only primary spot checks."""
import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re

ROOT = Path('/home/sun07ao/grephene')
PROJECT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True, help='New JSON output path inside this framework project.')
args = parser.parse_args()
OUTPUT = args.output.resolve()
if not OUTPUT.is_relative_to(PROJECT):
    parser.error('--output must stay inside the framework project')
if OUTPUT.exists():
    parser.error('--output already exists; choose a fresh path to preserve the previous package')
WORK = Path('/home/sun07ao/框架/var/audit_work/grephene')
MAP = ROOT/'research/scientific_evidence_map_20260915'
records, sources, cache = [], {}, {}


def read(path):
    path = Path(path).resolve()
    assert path.is_relative_to(ROOT), 'out_of_scope'
    if str(path) in cache:
        return cache[str(path)]
    before = path.stat()
    blob = path.read_bytes()
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'source_changed'
    sha = hashlib.sha256(blob).hexdigest()
    snapshot = WORK/'snapshots'/sha
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if not snapshot.exists():
        snapshot.write_bytes(blob)
    assert snapshot.read_bytes() == blob
    text = blob.decode()
    sources[str(path)] = {'path': str(path), 'sha256': sha, 'size': len(blob), 'line_count': len(text.splitlines()), 'line_ranges': [{'start': 1, 'end': len(text.splitlines())}], 'snapshot': str(snapshot), 'read_mode': 'full_bytes', 'mtime_ns': after.st_mtime_ns}
    cache[str(path)] = text
    return text


def loc(path, start=1, end=None):
    path = Path(path).resolve()
    text = read(path)
    return {'path': str(path), 'sha256': sources[str(path)]['sha256'], 'line_start': start, 'line_end': end or start}


def tracks(current='imported_assertion_unchecked'):
    return {'actual_work': {'status': 'unknown', 'value': None}, 'then_believed': {'status': 'unknown', 'value': None}, 'then_reported': {'status': 'recorded_in_source', 'value': 'verbatim source text'}, 'later_memory': {'status': 'unknown', 'value': None}, 'current_qualification': {'status': current, 'value': None}, 'note': 'Historical review/control documents do not expose private internal beliefs or prove actual execution.'}


def add(rid, kind, data, locations, verified=False):
    for l in locations:
        assert l['line_end'] <= sources[l['path']]['line_count']
    data.setdefault('scope', {'project': 'grephene', 'material': 'development_trial', 'source_scope': 'specified local project indexes and selected primary originals', 'not_blind': True})
    data.setdefault('provenance', {'locators': locations, 'qualification': 'current_primary_check' if verified else 'imported_assertion', 'proposer': 'local_reconstruction_agent', 'activity': 'scoped reconstruction 2026-09-20'})
    data.setdefault('source_files', [{'path': l['path'], 'sha256': l['sha256']} for l in locations])
    data.setdefault('five_tracks', tracks('current_primary_check' if verified else 'imported_assertion_unchecked'))
    if verified:
        data['five_tracks']['actual_work']={'status':'observed_primary_inputs_outputs','value':'See actual_results or identity fields and locators; historical executable byte-version not established.'}
        data['five_tracks']['then_reported']={'status':'unknown','value':None}
    records.append({'id': rid, 'kind': kind, 'data': data})


doc_names = ['SCIENTIFIC_FAMILIES.md', 'EVIDENCE_LEDGER.md', 'CONTRADICTIONS_AND_ANOMALIES.md', 'FORGOTTEN_ASSETS.md', 'MODEL_PROVENANCE_AUDIT.md']
for name in doc_names:
    read(MAP/name)
read(ROOT/'RESEARCH_CONTROL.md')

# Every SF historical family is retained as a branch with a separate audit task.
sfpath = MAP/'SCIENTIFIC_FAMILIES.md'
sflines = read(sfpath).splitlines()
starts = [(i, re.search(r'\*\*(SF-\d+)\b', x).group(1)) for i, x in enumerate(sflines) if re.search(r'^\*\*SF-\d+\b', x)]
family_titles = []
for n, (i, fid) in enumerate(starts):
    j = starts[n+1][0] if n+1 < len(starts) else next(k for k in range(i+1, len(sflines)) if sflines[k].startswith('## 5.'))
    while j > i+1 and (not sflines[j-1].strip() or sflines[j-1].startswith('###')):
        j -= 1
    text = '\n'.join(sflines[i:j])
    title = sflines[i].replace('**','')
    family_titles.append((fid, title))
    rid = 'gph-branch-'+fid.lower()
    add(rid, 'branch', {'title': title, 'original_text': text, 'evidence_verdict': 'unresolved', 'work_disposition': 'unknown', 'historical_qualification': 'reported in 2026-09-16 family map; not adopted as present evidence', 'object_codes': sorted(set(re.findall(r'\bO\d+[bcn]?\b', text))), 'destination': 'gph-audit-'+fid.lower(), 'current_audits': ['grephene-lmct-coordinate-and-energy-001'] if fid == 'SF-10' else []}, [loc(sfpath,i+1,j)])
    add('gph-audit-'+fid.lower(), 'audit_candidate', {'title': title, 'branch_id': rid, 'status': 'partially_audited' if fid == 'SF-10' else 'queued', 'required_work': 'Return each load-bearing value and inference to primary inputs/outputs; reconcile object, reference, path, convergence and interpretation. Existing originals first.', 'new_computation_required': {'status': 'unknown', 'value': None}, 'authorization': 'local read and postprocessing allowed; new scientific submissions prohibited', 'priority': 'load_bearing' if fid in {'SF-03','SF-06','SF-09','SF-10','SF-13','SF-14','SF-18','SF-19','SF-21','SF-24','SF-25'} else 'coverage'}, [loc(sfpath,i+1,j)])

# Preserve every explicit object and question row; these are schemas, not aliases.
section = ''
for i, line in enumerate(sflines, 1):
    if line.startswith('## '): section = line
    if not line.startswith('|'): continue
    cells = [x.strip() for x in line.strip('|').split('|')]
    code = cells[0].replace('**','')
    if section.startswith('## 1.') and re.fullmatch(r'O\d+[bcn]?', code):
        add('gph-object-historical-'+code.lower(), 'scientific_object', {'original_code':code, 'original_fields':cells,'identity_status':'candidate_only','merge_policy':'No unconditional equality or numeric comparison from family code alone.'}, [loc(sfpath,i)])
    elif section.startswith('## 2.') and re.fullmatch(r'Q\d+(?:/Q?\d+)?', code):
        add('gph-question-'+code.lower().replace('/','-'), 'scientific_map', {'question_code':code,'original_fields':cells,'status':'open_reconstruction_question'}, [loc(sfpath,i)])

# Every data row / residual bullet in the remaining documents has a destination.
coverage = {}
for name in doc_names[1:]:
    path=MAP/name; lines=read(path).splitlines(); section=''; count=0
    for i, line in enumerate(lines,1):
        if line.startswith('#'): section=line.lstrip('# ')
        table_data = line.startswith('|') and not re.match(r'^\|\s*[-:#]',line)
        cells = [x.strip() for x in line.strip('|').split('|')] if table_data else []
        if cells and cells[0] in {'#','资产','数字','文档','事项','目录（逻辑路径）','现象','族','名称','血统根','代'}: table_data=False
        # Chinese/English headers are excluded explicitly; no physical claim inferred.
        if cells and cells[0] in {'数字 (kcal/mol)','代码','对象','现象','目录','量'}: table_data=False
        prose = bool(line.strip()) and not line.startswith(('#','|','---'))
        if not table_data and not prose: continue
        if table_data and all(re.fullmatch(r'[-: ]*',x) for x in cells): continue
        count += 1
        tag={'EVIDENCE_LEDGER.md':'ledger','CONTRADICTIONS_AND_ANOMALIES.md':'anomaly','FORGOTTEN_ASSETS.md':'forgotten','MODEL_PROVENANCE_AUDIT.md':'provenance'}[name]
        rid=f'gph-{tag}-line-{i}'
        kind='historical_assertion' if tag=='ledger' else ('reusable_asset' if tag=='forgotten' else 'audit_candidate')
        add(rid,kind,{'title':cells[0] if cells else line[:110],'original_text':line,'source_section':section,'original_fields':cells,'status':'imported_unchecked','destination':rid+'-review','required_work':'Verify primary artifact availability and actual protocol, then resolve inference; preserve unknown if external evidence needed.','external_paths_policy':'Referenced external roots are not opened.','new_computation_required':{'status':'unknown','value':None}},[loc(path,i)])
        if tag in {'ledger','forgotten'}:
            add(rid+'-review','audit_candidate',{'title':'Review '+(cells[0] if cells else line[:80]),'subject_id':rid,'status':'queued','required_work':'Locate from existing index first, check local primary original and archived variants; do not classify missing local file as never run.','new_computation_required':{'status':'unknown','value':None}},[loc(path,i)])
        else:
            records[-1]['data']['destination']=rid
    coverage[name]={'addressed_source_items':count,'qualification':'historical intake complete for listed rows/bullets; scientific audit remains selective'}

# Current control is historical reporting, not authorization to resume old jobs.
control=ROOT/'RESEARCH_CONTROL.md'
section=''
for i,line in enumerate(read(control).splitlines(),1):
    if line.startswith('##'):section=line
    if not (line.startswith('- ') or line.startswith('> **')):continue
    rid=f'gph-control-line-{i}'
    add(rid,'historical_assertion',{'original_text':line,'source_section':section,'authorization_effect':'none; current user read-only scientific boundary dominates','destination':'gph-control-context-review','time_status':'embedded historical text only; mtime is not scientific event time'},[loc(control,i)])
    if section.startswith('## REJECTED'):
        add(rid+'-negative','negative_knowledge',{'proposition_original':line,'evidence_verdict':'unresolved','work_disposition':'unknown','historical_work_disposition':'withdrawn/deferred/stopped as source states','failure_type':'historical_classification_requires_recheck','reopen_condition':'Retain exact source reopening condition; verify evidence before changing current scientific qualification.','residual_valid_assets':'Do not discard underlying inputs/outputs merely because interpretation was withdrawn.'},[loc(control,i)])

# Existing mapping and census coverage: group metadata only, no recensus or external access.
index=MAP/'JOB_TO_SCIENTIFIC_FAMILY.tsv'
rows=list(csv.DictReader(io.StringIO(read(index)),delimiter='\t'))
by_campaign=defaultdict(list)
for i,row in enumerate(rows,2):by_campaign[row['campaign']].append((i,row))
for campaign, entries in by_campaign.items():
    orphan=[row for _,row in entries if row.get('mention_depth')=='0']
    add('gph-campaign-'+hashlib.sha256(campaign.encode()).hexdigest()[:12],'scientific_map',{'campaign':campaign,'indexed_row_count':len(entries),'orphaned_by_legacy_mention_matching':len(orphan),'object_labels':dict(Counter(x['object'] for _,x in entries)),'question_labels':dict(Counter(x['question'] for _,x in entries)),'directory_family_ids':sorted(set(x['candidate_family_id'] for _,x in entries)),'row_semantics':'indexed storage-site/output rows, not independent experiments','destination':'Reconcile primary runs and unmentioned outputs within this campaign.','scientific_review_status':'not_complete'},[loc(index,i) for i,_ in entries])
familypath=ROOT/'research/raw_asset_census_20260915/job_families_20260916/JOB_FAMILIES.csv'
familyrows=list(csv.DictReader(io.StringIO(read(familypath))))
groups=defaultdict(list)
for i,row in enumerate(familyrows,2):groups[row['candidate_family_id']].append((i,row))
for fid,entries in groups.items():
    refs=sorted(set(r['main_output_path'] for _,r in entries if r['main_output_path']))
    add('gph-directory-'+fid.lower(),'reusable_asset',{'directory_family_id':fid,'directory_roots':sorted(set(r['family_root_dir'] for _,r in entries)),'campaigns':sorted(set(r['campaign'] for _,r in entries)),'indexed_storage_rows':len(entries),'raw_path_references':refs,'reference_policy':'Paths only; referenced files not read by this grouping operation.','current_qualification':'indexed_not_audited','destination':'incremental per-artifact ingestion and branch mapping; avoid duplicate whole-project census','legacy_status_counts':dict(Counter(r['status_class'] for _,r in entries))},[loc(familypath,i) for i,_ in entries])

# Primary identity checks: count coordinates from the actual output, compare input.
def output_geometry(text):
    lines=text.splitlines(); start=next(i for i,x in enumerate(lines) if x.strip()=='CARTESIAN COORDINATES (ANGSTROEM)')
    atoms=[]
    for line in lines[start+2:]:
        parts=line.split()
        if len(parts)==4 and re.fullmatch(r'[A-Z][a-z]?',parts[0]):
            try: xyz=list(map(float,parts[1:]))
            except ValueError: break
            atoms.append((parts[0],xyz))
        elif atoms:break
    assert atoms
    return atoms,start+1,start+2+len(atoms)

identity_results=[]
identity_dirs={'O2':'stage3_photoresponse_5x3/encounter_m6_tddft_dz','O3':'expert_system_contrast_20260422/stage2_adsorption_5x3/p1_n1_neutral_adsorption/a1b_n1_encounter_stab','O4':'mech_loop/entry_competition_20260911/fe_arm/F0_pcontact_m6'}
for code,directory in identity_dirs.items():
    d=ROOT/directory; inp=read(d/'orca.inp'); out=read(d/'orca.out'); atoms,start,end=output_geometry(out)
    charge,mult=map(int,re.search(r'\*\s+xyz(?:file)?\s+(-?\d+)\s+(\d+)',inp).groups())
    echo=re.search(r'\*\s+xyz(?:file)?\s+(-?\d+)\s+(\d+)',out)
    assert echo and tuple(map(int,echo.groups()))==(charge,mult)
    assert 'ORCA TERMINATED NORMALLY' in out
    composition=dict(sorted(Counter(x[0] for x in atoms).items()))
    xyzref=re.search(r'\*\s+xyzfile\s+-?\d+\s+\d+\s+(\S+)',inp)
    locations=[loc(d/'orca.inp',1,len(inp.splitlines())),loc(d/'orca.out',start,end)]
    if xyzref:
        xyzpath=d/xyzref.group(1); xyz=read(xyzpath).splitlines(); inp_atoms=[(x.split()[0],list(map(float,x.split()[1:4]))) for x in xyz[2:2+int(xyz[0])]]
        locations.append(loc(xyzpath,1,len(xyz)))
    else:
        block=inp.split(re.search(r'\*\s+xyz\s+-?\d+\s+\d+',inp).group(0),1)[1].split('*',1)[0]
        inp_atoms=[(x.split()[0],list(map(float,x.split()[1:4]))) for x in block.splitlines() if len(x.split())==4]
    assert [x[0] for x in inp_atoms]==[x[0] for x in atoms]
    maxdiff=max(abs(a-b) for (_,a3),(_,b3) in zip(inp_atoms,atoms) for a,b in zip(a3,b3))
    assert maxdiff<1e-5
    result={'object_code':code,'composition':composition,'charge':charge,'multiplicity':mult,'atom_count':len(atoms),'input_vs_output_initial_geometry_max_abs_angstrom':maxdiff,'input_method_line':inp.splitlines()[0],'output_normal_termination':True,'claim_scope':'actual modeled object in this run, not experimental precursor identity'}
    identity_results.append(result)
    add('gph-primary-identity-'+code.lower(),'scientific_object',result,locations,True)

o2,o3,o4=identity_results
delta={k:o3['composition'].get(k,0)-o2['composition'].get(k,0) for k in set(o2['composition'])|set(o3['composition'])}
delta={k:v for k,v in delta.items() if v}
add('gph-identity-comparability','scientific_map',{'title':'O2/O3/O4 comparability is operation-specific','evidence_verdict':'supported','actual_primary_results':identity_results,'o3_minus_o2_atom_balance':delta,'charge_difference':o3['charge']-o2['charge'],'conclusion':'O2 and O3 are different composition and charge models, not merely one redox pair or interchangeable encounter label. O3/O4 differ flake composition.','comparison_rules':[{'operation':'same_object','rule':'Require composition/charge/state/geometry identity appropriate to operation; family label alone insufficient.'},{'operation':'energy_difference','rule':'Same-model path energies need compatible method, reference, constraints and electronic state. Different composition can only enter an explicit balanced reaction/thermochemical cycle with all missing species and charge accounting.'},{'operation':'cross_model_comparison','rule':'Compare separately defined observables as model sensitivity, not subtract raw Hartree totals as one barrier.'},{'operation':'same_proposition_support','rule':'Local fragment slope, full contact path and observed experimental identity are distinct support obligations.'}],'current_unknown':'Experimental precursor and film identity remain unestablished by these model inputs.'},[loc(ROOT/v/'orca.inp',1,len(read(ROOT/v/'orca.inp').splitlines())) for v in identity_dirs.values()],True)

# F5 m2 actual OptTS/Freq distinction: finite evidence cannot certify stationarity.
tsroot=ROOT/'research/pro_evidence_rebuild_20260915/raw_live_xj/entry_remaining/fe_arm/F5_n2ts_m2'
a=read(tsroot/'step_a/orca.out'); b=read(tsroot/'step_b/orca.out')
ainp=read(tsroot/'step_a/orca.inp'); binp=read(tsroot/'step_b/orca.inp')
assert 'OptTS' in ainp and 'Freq' in binp
assert 'OPTIMIZATION HAS CONVERGED' not in a and 'HURRAY' not in a
assert 'ORCA TERMINATED NORMALLY' not in a and 'ORCA TERMINATED NORMALLY' in b
last=a.rsplit('|Geometry convergence|',1)[1].split('The optimization has not yet converged',1)[0]
steps=re.findall(r'(RMS step|MAX step)\s+([\d.]+)\s+([\d.]+)\s+(NO|YES)',last)
assert len(steps)==2 and all(x[-1]=='NO' for x in steps)
imag=re.findall(r'\d+:\s+(-[\d.]+) cm\*\*-1\s+\*\*\*imaginary mode',b)
assert len(imag)==1
alines=a.splitlines(); blines=b.splitlines(); aloc=max(i for i,x in enumerate(alines,1) if '|Geometry convergence|' in x); bloc=next(i for i,x in enumerate(blines,1) if '***imaginary mode***' in x)
add('gph-ts-frequency-not-stationarity','negative_knowledge',{'title':'F5 m2 frequency completion does not certify converged TS','evidence_verdict':'invalid_test','work_disposition':'parked','original_claim_ref':'SF-14 describes single-imaginary TS certification, while ledger A10 retains unconverged candidate status.','failed_proposition':'F5 m2 has completed converged OptTS plus stationary first-order saddle certification.','failure_type':'stationarity_and_protocol_obligation','actual_results':{'step_a_normal_termination':False,'step_a_optimization_converged_marker':False,'last_geometry_step_checks':[{'quantity':x[0],'value':float(x[1]),'tolerance':float(x[2]),'passed':False} for x in steps],'step_b_normal_termination':True,'step_b_imaginary_frequencies_cm_1':list(map(float,imag))},'derivation':'A first-order saddle requires stationarity plus exactly one negative curvature on the specified allowed subspace. One imaginary frequency alone supplies curvature information and cannot fill the missing stationarity/protocol check.','competing_explanation':'Last RMS/MAX gradient pass, so the point may be a useful approximate TS candidate; final RMS/MAX displacement criteria still fail. No claim that the TS or mechanism is impossible.','retained_assets':'Frequency, geometry and energy at this candidate; approximate candidate qualification.','reopen_condition':'First inspect available final geometry/gradient and constrained-subspace consistency; only if missing numerical refinement is scientifically needed request a specifically authorized new optimization.','new_computation_required':{'status':'conditional','value':'not needed to reject completed-converged certification; may be needed to establish a refined TS.'}},[loc(tsroot/'step_a/orca.out',aloc,aloc+15),loc(tsroot/'step_b/orca.out',bloc-2,bloc+2),loc(tsroot/'step_a/orca.inp',1,len(ainp.splitlines())),loc(tsroot/'step_b/orca.inp',1,len(binp.splitlines()))],True)

# Non-generic task boundaries: existing assets first; not every unknown needs compute.
tasks=[
('precursor','Experimental precursor/film identity versus modeled neutral candidate','RESEARCH_CONTROL.md','Read authorized experiment records/IR/XPS and stated sample conditions; model input identity cannot decide film composition.','Existing experimental originals may be missing; ask for exact record if absent, not new DFT by default.'),
('thermochemistry','MeCN desorption +5..8 versus electronic +19.7','research/scientific_evidence_map_20260915/FORGOTTEN_ASSETS.md','Locate A0/A1/MeCN output and .hess in existing RAW_CACHE; reconstruct ZPE/thermal entropy/standard-state/solvent consistency.','Existing-output postprocessing; only missing thermo data could require new computation.'),
('tslinks','F5 candidate geometry, allowed subspace and path linkage','research/scientific_evidence_map_20260915/EVIDENCE_LEDGER.md','Compare final OptTS geometry to Freq input, retained constrained gradients/modes and any IRC/nearby downhill endpoints.','Convergence/path refinement if no existing adequate evidence; do not launch here.'),
('etcycle','r4t four-point lambda and neutral injection target','research/scientific_evidence_map_20260915/FORGOTTEN_ASSETS.md','Read six archived CP2K outputs, check charge/population and geometry matching; write exact energy cycle and see whether it estimates claimed process.','Local audit may invalidate target without computation; new states only after defining missing cycle.'),
('tmscurve','Unconsumed TMS/PFPA EA(Q) ladder','research/scientific_evidence_map_20260915/FORGOTTEN_ASSETS.md','Read existing matched neutral/anion same-geometry SPs and build coordinate-resolved vertical EA with method-specific references and failures retained.','Existing original postprocessing first; failed PFPA DLPNO cells remain explicit missing observations.'),
('t13b','Opening/rebonding versus annealing barrier','research/scientific_evidence_map_20260915/EVIDENCE_LEDGER.md','Read RAW_CACHE seven geometries and energies, reconstruct all N-C bonds rather than single scanned bond, check path endpoint identity.','Existing coordinate audit; real annealing kinetics needs more than this scan.'),
('hab','H_ab alleged coordinate gating','research/scientific_evidence_map_20260915/CONTRADICTIONS_AND_ANOMALIES.md','Inspect resting and failed-other-geometry raw outputs plus duplicate input hashes; separate unavailable coupling from zero coupling.','Existing files suffice to bound gating claim; measuring additional geometries would require new computation.'),
('periodic','EV-056 periodic assertion versus six local inputs','research/scientific_evidence_map_20260915/MODEL_PROVENANCE_AUDIT.md','Use already imported index to locate other local raw copies; do not equate lack of local output with never executed.','If only remote originals exist, ask for bounded read/access or provided copy; do not resubmit.')]
for tid,title,path,work,boundary in tasks:
    p=ROOT/path
    add('gph-directed-audit-'+tid,'audit_candidate',{'title':title,'status':'queued','required_work':work,'external_boundary':boundary,'new_computation_required':{'status':'unknown_until_existing_asset_audit','value':None}},[loc(p,1,len(read(p).splitlines()))])

add('gph-world-model','scientific_map',{'title':'Evidence-bounded project reconstruction baseline','goal':'Explain observed light-associated nitrogen chemistry and graphene/Si comparison without assuming precursor, active intermediate or final bonding identity.','relationships_needed':['modeled/experimental precursor identity','population of a reactive local state','productive N2-loss connectivity','capture versus recombination','product identity and annealing observable','representation/spin/method validity for each load-bearing relation'],'current_primary_audits':['grephene-lmct-coordinate-and-energy-001','gph-identity-comparability','gph-ts-frequency-not-stationarity'],'scientific_status':'No global mechanism certified by this reconstruction. Historical branches preserved; unresolved tasks not counted as audited.','missing_records':'Private internal beliefs and conversation history not accessed; experimental raw records not in this scoped packet.','independence':'Repeated reports/indexes/reviews sharing a source do not add independent physical support.'},[loc(control,1,25)])
add('gph-control-context-review','audit_candidate',{'title':'Reconcile control-document historical assertions with accepted corrections','status':'queued','required_work':'Keep top-of-file corrections distinct from stale historical NEXT/OPEN; link each load-bearing historical assertion to its raw audit and do not revive expired job authorization.','new_computation_required':{'status':'not_required_for_control_reconciliation','value':False}},[loc(control,1,len(read(control).splitlines()))])
for record in records:
    if record['id']=='gph-branch-sf-14': record['data']['current_audits']=['gph-ts-frequency-not-stationarity']
    if record['id'] in {'gph-branch-sf-05','gph-branch-sf-06','gph-branch-sf-08'}: record['data']['current_audits']=['gph-identity-comparability']

ids=[r['id'] for r in records]
assert len(ids)==len(set(ids))
payload={'schema_version':'project-reconstruction-local-1','project_id':'grephene-development','created_at':datetime.now(timezone.utc).isoformat(),'scope':{'read_roots':[str(ROOT)],'source_index_files':[str(MAP/n) for n in doc_names],'source_is_read_only':True,'external_reference_policy':'register only; no external roots accessed','role':'development_trial','claims':'historical inventory plus three scoped current audits, not completed full project science'},'records':records,'source_files':list(sources.values()),'coverage':{'scientific_families':len(starts),'directory_families':len(groups),'directory_index_rows':len(familyrows),'scientific_mapping_rows':len(rows),'campaigns':len(by_campaign),'records_by_kind':dict(Counter(r['kind'] for r in records)),'documents':coverage,'completeness':'Every indexed directory family, SF family, question/object row, selected-doc data row/residual bullet has a retained record/destination. Scientific adjudication is selective and explicitly incomplete.'},'primary_check_receipt':{'mode':'real_read_only_stdlib_checks','identity_results':identity_results,'ts_last_displacement_checks':steps,'ts_imaginary_frequencies_cm_1':imag,'source_scripts_executed':False,'new_scientific_jobs':0,'external_calls':0,'builder':str(Path(__file__).resolve()),'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},'checks':{'unique_ids':True,'all_record_locators_present':True,'snapshots_sha256_checked':True},'declarations':{'reconstruction_intake':'completed_for_declared_index_and_document_rows','full_project_deep_audit':'not_completed','R2_product_release':'not_claimed_by_this_packet'}}
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'records':len(records),'source_count':len(sources),'coverage':payload['coverage'],'identity_results':identity_results,'ts_step_checks':steps},ensure_ascii=False,indent=2))
