"""Clone-only real-source qualification isolation checks for entry and T13b."""
import sys,json,hashlib,traceback
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from research_harness.storage import Store
from research_cases.legacy.audit import revoke
from research_harness.common import atomic_json

def h(p):
 d=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):d.update(b)
 return d.hexdigest()

def main():
 work=ROOT/'var/validation'/('r2-entry-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));work.mkdir(parents=True)
 r={'command':[sys.executable,str(Path(__file__).resolve())],'script_sha256':h(__file__),'status':'running','work_root':str(work),'checks':[],'mode':'real cloned source qualification; no source edits or new scientific jobs'}
 def check(n,v):
  r['checks'].append({'name':n,'passed':bool(v)})
  if not v:raise AssertionError(n)
 try:
  s=Store(ROOT/'var/projects/grephene');before_prod={'sha256':h(s.db_path),'revision':s.current_revision()};r['production_before']=before_prod
  r['backup']=s.backup(work/'clone');c=Store(work/'clone')
  entry=json.loads((ROOT/'research_cases/grephene/entry_audit_normalized.json').read_text());t13=json.loads((ROOT/'research_cases/grephene/t13b_audit_normalized.json').read_text())
  entryid=entry['id'];t13id=t13['id']
  tracked=[x['id'] for x in entry['suggested_state_records']+t13['suggested_state_records']]+['gph-c-gradient-normalized','gph-c-gap-corrected']
  tracked += [entryid+':negative:'+str(i) for i in range(3)]+[t13id+':negative:'+str(i) for i in range(2)]
  def states():return {i:{'revision':(o:=c.get(i))['revision'],'support_status':o['data'].get('support_status'),'adjudication_supported':o['data'].get('adjudication_supported')} for i in tracked}
  r['before']=states()
  path=next(p for p in entry['source_groups']['tms_legacy_r2_ea']['sources'] if p.endswith('TMSN3_anion_vert/orca.out'))
  def source_id(path,caseid):
   matches=[x['id'] for x in c.list('evidence') if x['data'].get('qualification')=='source_identity_verified_only' and any(z.get('uri')==path for z in x['data'].get('source_locators',[])) and x['id'] in c.get(caseid+':check:'+('tms_legacy_r2_ea' if caseid==entryid else 'point1_to_6_contact_migration'))['data']['support_sets'][0]]
   if len(matches)!=1:raise AssertionError('expected unique source evidence')
   return matches[0]
  r['old_tms_source']=path;r['old_tms_revocation']=revoke(c,source_id(path,entryid),'Clone acceptance: withdraw one legacy r2SCAN source qualification')
  r['after_old_tms']=states()
  check('old_EA_withdrawn',r['after_old_tms']['entry-c-old-r2-ea']['support_status']=='unsupported')
  preserve=['entry-c-tms-min-dlpno-ea','entry-c-tms-dea-endpoint','entry-c-tms-neu-q6-positive','entry-c-pfpa-first-ea','entry-c-geometry-conditioning','entry-c-pfpa-dlpno-incomplete','entry-c-point9-relaxed-status']+[x['id'] for x in t13['suggested_state_records']]+['gph-c-gradient-normalized','gph-c-gap-corrected']
  check('DLPNO_other_SP_T13b_gradient_unchanged',all(r['before'][i]==r['after_old_tms'][i] for i in preserve))
  check('entry_negative0_old_arithmetic_withdrawn',r['after_old_tms'][entryid+':negative:0']['support_status']=='unsupported')
  check('entry_negative1_joint_correction_withdrawn',r['after_old_tms'][entryid+':negative:1']['support_status']=='unsupported')
  check('entry_negative2_selector_independent',r['after_old_tms'][entryid+':negative:2']==r['before'][entryid+':negative:2'])
  check('T13b_both_negative_records_independent',all(r['after_old_tms'][t13id+':negative:'+str(i)]==r['before'][t13id+':negative:'+str(i)] for i in range(2)))
  r['changed_objects_old_tms']=r['old_tms_revocation']['changed_ids']
  # An independent T13b geometry withdrawal must not alter any entry or FC claim.
  path=next(p for p in t13['source_groups']['point1_to_6_contact_migration']['sources'] if p.endswith('orca.006.xyz'))
  r['t13b_source']=path;r['t13b_revocation']=revoke(c,source_id(path,t13id),'Clone acceptance: withdraw T13b point6 geometry qualification')
  r['after_t13b']=states()
  check('T13b_contact_claim_withdrawn',r['after_t13b']['t13b-c-contact-migration']['support_status']=='unsupported')
  check('T13b_energy_peak_independent',r['after_t13b']['t13b-c-sampled-peak']==r['after_old_tms']['t13b-c-sampled-peak'])
  preserve=[x['id'] for x in entry['suggested_state_records']]+['gph-c-gradient-normalized','gph-c-gap-corrected']
  check('entry_and_FC_independent_of_T13b',all(r['after_t13b'][i]==r['after_old_tms'][i] for i in preserve))
  check('T13b_negative0_contact_withdrawn',r['after_t13b'][t13id+':negative:0']['support_status']=='unsupported')
  check('T13b_negative1_energy_qualification_preserved',r['after_t13b'][t13id+':negative:1']==r['after_old_tms'][t13id+':negative:1'])
  check('entry_all_negative_records_independent_of_T13b',all(r['after_t13b'][entryid+':negative:'+str(i)]==r['after_old_tms'][entryid+':negative:'+str(i)] for i in range(3)))
  r['clone_verify']=c.verify();check('clone_integrity',r['clone_verify']['ok'])
  r['production_after']={'sha256':h(s.db_path),'revision':s.current_revision()};check('production_unchanged',r['production_after']==before_prod)
  r['status']='passed'
 except Exception as e:r.update(status='failed',error=str(e),traceback=traceback.format_exc())
 atomic_json(work/'receipt.json',r);atomic_json(ROOT/'var/receipts/r2_entry_isolation.json',r)
 print(json.dumps({'status':r['status'],'receipt':str(work/'receipt.json'),'checks':len(r['checks']),'error':r.get('error')}));return 0 if r['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
