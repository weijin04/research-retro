#!/usr/bin/env python3
"""Normalize already-executed audits; does not invent or rerun execution receipts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
WORK=PROJECT/'var/audit_work/grephene'

def load(name): return json.loads((HERE/name).read_text())
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

entry=load('entry_audit_case.json')
er=entry['execution_receipt'].copy()
er['receipt_origin']='copied from actual completed entry_audit_case.json execution_receipt; normalization is not a new execution'
er['source_case_sha256']=hashlib.sha256((HERE/'entry_audit_case.json').read_bytes()).hexdigest()
er['stdout_path']=str(WORK/'entry_stdout.json')
er['stdout_sha256']=hashlib.sha256((WORK/'entry_stdout.json').read_bytes()).hexdigest()
assert hashlib.sha256(Path(er['script']).read_bytes()).hexdigest()==er['script_sha256']
save(WORK/'entry_execution_receipt.json',er)

groups=entry['source_groups'].copy()
base='/home/sun07ao/grephene/research/pro_evidence_rebuild_20260915/raw_live_xj/entry_remaining/tms_arm/iso'
groups['pfpa_dlpno_incomplete']={'sources':[s for tag in ['neutral_min','vertical_anion_at_min','RN_anion','RN_triplet','anion_scan_EAvert_crossing'] for s in entry['actual_results']['dlpno']['PFPA'][tag]['sources']],'scope':'These five local higher-level outputs are incomplete and have no final single-point energies; not zero energies or a mechanistic negative.','rationale':'Each stated missing result depends on its own actual input/output; this group is only the composite five-job status claim.'}
groups['tms_point9_parent_status']={'sources':[base+'/TMS/step2_neutral_scan/orca.inp',base+'/TMS/step2_neutral_scan/orca.out',base+'/TMS/step2_neutral_scan/orca.009.xyz'],'scope':'TMS neutral parent ninth relaxed-scan step lacks convergence/normal completion; saved geometry exists.','rationale':'SP completion does not supply parent relaxed-geometry convergence.'}
def rec(i,status,text,kind='claim'):return {'id':i,'kind':kind,'evidence_status':status,'text':text}
normalized={
 'id':entry['id'],'schema_version':'audit-case-local-1','project_id':entry['project_id'],'revision':1,
 'status':entry['status'],'evidence_verdict':'mixed','source_files':entry['source_files'],'conditions':entry['conditions'],
 'original_claims':entry['original_claims'],'actual_question':entry['actual_question'],
 'analysis':{'actual_results':entry['actual_results'],'script':'research_cases/grephene/entry_audit.py','execution_receipt':'var/audit_work/grephene/entry_execution_receipt.json','execution_receipt_sha256':hashlib.sha256((WORK/'entry_execution_receipt.json').read_bytes()).hexdigest(),'script_sha256':er['script_sha256'],'derivations':entry['analysis']['derivations']+['For finite-fragment CT at matched geometries, DeltaE_CT=IP(graphene fragment)-EA(molecule)+DeltaE_interaction. Under an electron-reservoir approximation the corresponding term is -mu_e-EA; a vacuum-zero attachment threshold cannot be directly compared to hot-electron excess above the Fermi level without the reservoir reference.'],'code_path_checks':entry['analysis']['code_path_checks'],'historical_code_identity':entry['analysis']['historical_code_identity']},
 'support_scope':entry['support_scope'],'first_failing_conditions':[{'claim':'global interface DEA exclusion from initial molecular negative EA','failure':entry['first_failing_condition']},{'claim':'positive EA on anion-relaxed geometry establishes easy capture from neutral geometry','failure':'Matched Nalpha-Nbeta does not imply same geometry; TMS first neutral/anion-lineage NNN angles differ by about 41 degrees and neutral deformation is 1.72814049 eV in TZVPD.'},{'claim':'point9 sign rebound describes a converged relaxed profile','failure':'Parent ninth TMS neutral scan point is not converged; its SP is only a fixed-geometry observation.'}],
 'retained_assets':entry['retained_assets'],'negative_knowledge':[{'proposition':'The old -2.13 eV was a numerical transcription error','verdict':'refuted','scope':'The two old TMS r2SCAN jobs at the matched neutral final geometry','failure_type':'not_an_error_in_the_old_arithmetic','retained':'-2.1266416366 eV is reproduced.'},{'proposition':'Negative EA at the initial molecular geometry alone proves global interface DEA exclusion','verdict':'unsupported','scope':'Inference, not the physical impossibility of DEA','failure_type':'target_geometry_and_reservoir_transfer','retained':'Initial vertical attachment is endothermic in the stated tested methods.'},{'proposition':'First EA>0 anion-scan point is an actual located neutral-to-anion pathway crossing','verdict':'invalid_test','scope':'Archived A6 selector and its chosen point1 in both molecules','failure_type':'conditioned_geometry_selection','retained':'Actual SP at the selected geometry remains usable.'}],
 'residual_unknowns':entry['residual_unknowns'],'competitive_explanations':entry['competitive_explanations'],'r2_release_effect':entry['r2_release_effect'],'source_groups':groups,
 'suggested_state_records':[
  rec('entry-c-old-r2-ea','supported','Old isolated TMS r2SCAN neutral-geometry vertical EA is -2.126641636558386 eV.'),
  rec('entry-c-tms-neu-q6-positive','supported','At neutral-lineage Nalpha-Nbeta=1.74 Angstrom, TMS same-geometry EA is +0.1849 eV (TZVP) and +0.290847 eV (TZVPD); this is not an interface pathway claim.'),
  rec('entry-c-pfpa-first-ea','supported','PFPA-Me neutral-lineage first 1.24 Angstrom sample has positive same-geometry EA +0.4048/+0.467426 eV; PFPA is a distinct control, not TMS.'),
  rec('entry-c-geometry-conditioning','supported','TMS neutral versus anion optimized first samples have the same 1.24 Angstrom scan coordinate but NNN angles 174.751 versus 133.523 degrees. At TZVPD the latter costs 1.72814049 eV neutral deformation; positive EA does not erase this access condition.'),
  rec('entry-c-tms-min-dlpno-ea','qualified','Completed isolated TMS DLPNO-CCSD(T)/aug-cc-pVTZ vertical EA at its neutral minimum is -0.39823254578974365 eV; finite-basis method-specific result.'),
  rec('entry-c-tms-dea-endpoint','qualified','Completed same-method molecular separated endpoint TMSN3+e(vacuum zero)->TMSN(-)+N2 is +0.01760908070508041 eV electronic energy; not DeltaG or a barrier.'),
  rec('entry-c-pfpa-dlpno-incomplete','supported','Five PFPA higher-level molecular outputs read here are incomplete with no final energies; the completed N2 reference does not complete those pairs.'),
  rec('entry-c-point9-relaxed-status','qualified','TMS neutral scan point9 is not certified as a converged relaxed geometry; retain its completed SP values only as fixed-geometry observations.'),
  rec('entry-c-global-dea-exclusion','unsupported','The old initial molecular negative EA establishes global exclusion of organic/TMS interface DEA.'),
  rec('entry-b-interface-route','unresolved','Whether TMS interface electron attachment leads to productive nitrogen transfer remains unresolved by these isolated-molecule data.','branch')],
 'inference_dependencies':{
  'entry-c-old-r2-ea':[['tms_legacy_r2_ea']],
  'entry-c-tms-neu-q6-positive':[['tms_neuscan_06_tzvp','tms_neuscan_06_tzvpd']],
  'entry-c-pfpa-first-ea':[['pfpa_neuscan_01_tzvp','pfpa_neuscan_01_tzvpd']],
  'entry-c-geometry-conditioning':[['tms_neuscan_01_tzvpd','tms_anscan_01_tzvpd']],
  'entry-c-tms-min-dlpno-ea':[['tms_minimum_dlpno_ea']],
  'entry-c-tms-dea-endpoint':[['tms_separated_dlpno_dea_endpoint']],
  'entry-c-pfpa-dlpno-incomplete':[['pfpa_dlpno_incomplete']],
  'entry-c-point9-relaxed-status':[['tms_point9_parent_status']],
  'entry-c-global-dea-exclusion':[['tms_legacy_r2_ea','tms_neuscan_06_tzvpd','tms_neuscan_01_tzvpd','tms_anscan_01_tzvpd']],
  'entry-b-interface-route':[]},
 'integration_notes':['Unsupported/refuted propositions are not affirmative support for productive downstream mechanisms.','An unresolved branch has no affirmative support-set certification here.','Source groups may share files; this represents common provenance, not independent physical trials.'],
 'normalization':{'source_case':'research_cases/grephene/entry_audit_case.json','source_case_sha256':er['source_case_sha256'],'normalized_at':datetime.now(timezone.utc).isoformat(),'new_execution':False}}
groups['a6_selected_geometry_and_code']={
 'sources':sorted(set([base+'/common/azide_chain.py',base+'/TMS/run_iso.py',base+'/PFPA/run_iso.py']+
 [p for molecule in ['TMS','PFPA'] for p in entry['actual_results']['dlpno'][molecule]['anion_scan_EAvert_crossing']['sources']]+
 [p for key in ['tms_anscan_01_tzvp','pfpa_anscan_01_tzvp'] for p in groups[key]['sources']])),
 'scope':'Archived selector chooses first positive TZVP anion-lineage EA; actual selected input geometry matches point1 in each molecule.',
 'limitations':['Archived code identity is not proven to be the byte-version used historically.','No claim that the unfinished PFPA selected higher-level job completed.']}
entry_negative_groups=[
 ['tms_legacy_r2_ea'],
 ['tms_legacy_r2_ea','tms_neuscan_06_tzvpd','tms_neuscan_01_tzvpd','tms_anscan_01_tzvpd'],
 ['a6_selected_geometry_and_code']]
entry_negative_reopen=[
 'Reopen if the original charge-paired input/output identity, geometry match, final energies, or numerical conversion changes.',
 'Reopen the inference qualification if matched donor/reservoir and interface conditions plus an applicable pathway or exclusion argument are supplied; positive deformed molecular EA alone does not establish DEA.',
 'Reopen if a versioned historical selector and actual surface-intersection calculation establish a different selection procedure or a located crossing at this geometry.']
for i,(negative,dependencies,reopen) in enumerate(zip(normalized['negative_knowledge'],entry_negative_groups,entry_negative_reopen)):
 negative['applicable_conditions']=negative['scope']
 negative['reopen_condition']=reopen
 normalized['inference_dependencies'][normalized['id']+':negative:'+str(i)]=[dependencies]
save(HERE/'entry_audit_normalized.json',normalized)

t=load('t13b_audit_case.json')
tr=t['execution'].copy();tr['started_at']=t['started_at'];tr['finished_at']=t['finished_at']
tr['receipt_origin']='copied from actual t13b_audit_case.json execution and timestamps; normalization is not a new run'
tr['stdout_status']='not retained as a separate file; actual structured result and tool execution already exist'
assert hashlib.sha256(Path(tr['script']).read_bytes()).hexdigest()==tr['script_sha256']
save(WORK/'entry_t13b_execution_receipt.json',tr)
paths=[s['path'] for s in t['source_files']]
inp=next(p for p in paths if p.endswith('/orca.inp'))
rawout=next(p for p in paths if '/OBJECTS/' in p)
dat=next(p for p in paths if p.endswith('.dat'))
frames=sorted(p for p in paths if p.endswith('.xyz'))
f1=next(p for p in frames if p.endswith('.001.xyz'));f6=next(p for p in frames if p.endswith('.006.xyz'))
tg={
 'point1_to_6_contact_migration':{'sources':[inp,rawout,f1,f6],'scope':'Same indexed N72 changes short carbon neighbors from C31/C32 to C32/C33 between these two actual scan geometries.','rationale':'Only initial and point6 matched geometries are needed for this contact-change witness; full output provides identity and actual frame association.','limitations':['Distance-based contacts do not independently establish formal bond order or an intervening continuous path.']},
 'all_seven_retain_carbon_contact':{'sources':[inp,rawout]+frames,'scope':'Each of the seven actual scan geometries retains at least one N72-C distance below 1.6 Angstrom.','rationale':'The universal seven-sample claim requires all seven geometries, not just endpoint6.'},
 'sampled_energy_peak':{'sources':[inp,rawout,dat],'scope':'Maximum seven-point actual electronic energy relative to first constrained sample is +16.048818352997433 kcal/mol at point5.','rationale':'Raw scan table, its independent dat copy and coordinate protocol establish the sampled target and reference; no geometry-derived bond inference needed.'}}
tsource=[dict(s,role=('historical_assertion' if s['path'].endswith('RESEARCH_CONTROL.md') else 'primary_scan_input' if s['path'].endswith('.inp') else 'primary_scan_geometry' if s['path'].endswith('.xyz') else 'primary_scan_output')) for s in t['source_files']]
tn={'id':t['audit_id'],'schema_version':'audit-case-local-1','project_id':'grephene-development','revision':1,'status':t['status'],'evidence_verdict':'mixed','source_files':tsource,'conditions':t['conditions'],'original_claims':[t['original_claim']],'actual_question':t['actual_question'],'analysis':{'actual_results':t['results'],'script':'research_cases/grephene/audit_t13b.py','execution_receipt':'var/audit_work/grephene/entry_t13b_execution_receipt.json','execution_receipt_sha256':hashlib.sha256((WORK/'entry_t13b_execution_receipt.json').read_bytes()).hexdigest(),'script_sha256':tr['script_sha256'],'derivation':t['derivation'],'checks':tr['checks']},'support_scope':['Matched seven-frame energy and distance reconstruction of the existing constrained scan.','Limited invalidation of full-detachment/annealing-barrier inference.'],'first_failing_conditions':[{'claim':'single C31-N72 extension means complete surface detachment','failure':t['first_failing_condition']},{'claim':'sampled electronic maximum is a certified 200 Celsius recovery free-energy barrier','failure':'Different target: constrained electronic sample relative to sample1; no stationarity/path/entropy or experimental reaction assignment.'}],'retained_assets':t['retained_assets'],'negative_knowledge':[{'proposition':'N72 loses all short carbon contacts when C31-N72 is 2.45 Angstrom','verdict':'refuted','scope':'point6 geometry only','failure_type':'representation_loses_other_contacts','retained':'C32/C33 short contacts remain.'},{'proposition':'This scan certifies the annealing activation free energy','verdict':'unsupported','scope':'Inference, not actual existence of another annealing pathway','failure_type':'target_and_path_obligation','retained':'Real constrained electronic profile.'}],'residual_unknowns':t['residual_unknowns'],'competitive_explanations':t['competitive_explanations'],'suggested_state_records':[rec('t13b-c-contact-migration','supported','N72 short neighbors change from C31/C32 at point1 to C32/C33 at point6; point6 distances are 1.455153/1.455170 Angstrom.'),rec('t13b-c-retained-carbon-contact','supported','All seven checked scan geometries retain at least one N72-C contact below 1.6 Angstrom.'),rec('t13b-c-sampled-peak','supported','Seven-point sampled electronic peak is +16.048818352997433 kcal/mol relative to first constrained point.'),rec('t13b-c-complete-detachment','refuted','Point6 is complete N72 detachment from all carbon contacts.'),rec('t13b-c-annealing-barrier','unsupported','The T13b sampled peak certifies an annealing activation free energy.'),rec('t13b-b-recovery-mechanism','unresolved','The actual chemical recovery/annealing pathway remains unresolved.','branch')],'source_groups':tg,'inference_dependencies':{'t13b-c-contact-migration':[['point1_to_6_contact_migration']],'t13b-c-retained-carbon-contact':[['all_seven_retain_carbon_contact']],'t13b-c-sampled-peak':[['sampled_energy_peak']],'t13b-c-complete-detachment':[['point1_to_6_contact_migration']],'t13b-c-annealing-barrier':[['point1_to_6_contact_migration','sampled_energy_peak']],'t13b-b-recovery-mechanism':[]},'integration_notes':normalized['integration_notes'],'normalization':{'source_case':'research_cases/grephene/t13b_audit_case.json','source_case_sha256':hashlib.sha256((HERE/'t13b_audit_case.json').read_bytes()).hexdigest(),'normalized_at':datetime.now(timezone.utc).isoformat(),'new_execution':False}}
t13b_negative_groups=[['point1_to_6_contact_migration'],['sampled_energy_peak']]
t13b_negative_reopen=[
 'Reopen if atom identity or matched point6 coordinates change, or a different contact definition is justified; a later detached geometry is a separate branch rather than a correction to point6.',
 'Reopen if a reaction-assigned stationary pathway, applicable thermodynamic reference and thermal corrections establish an annealing activation free energy; the constrained electronic maximum alone is insufficient.']
for i,(negative,dependencies,reopen) in enumerate(zip(tn['negative_knowledge'],t13b_negative_groups,t13b_negative_reopen)):
 negative['applicable_conditions']=negative['scope']
 negative['reopen_condition']=reopen
 tn['inference_dependencies'][tn['id']+':negative:'+str(i)]=[dependencies]
save(HERE/'t13b_audit_normalized.json',tn)
for case in [normalized,tn]:
 available={s['path'] for s in case['source_files']}
 assert all(set(g['sources'])<=available for g in case['source_groups'].values())
 assert all(set(group)<=set(case['source_groups']) for alternatives in case['inference_dependencies'].values() for group in alternatives)
print(json.dumps({'entry':{'id':normalized['id'],'sources':len(normalized['source_files']),'source_groups':len(groups),'actual_result_keys':list(entry['actual_results'])},'t13b':{'id':tn['id'],'sources':len(tsource),'source_groups':len(tg),'actual_result_keys':list(t['results'])}},ensure_ascii=False,indent=2))
