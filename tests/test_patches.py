import copy
import tempfile
from pathlib import Path
import unittest
from research_harness.common import HarnessError,upsert
from research_harness.storage import Store,ConflictError
from research_harness.ingest.service import Ingestor
from research_harness.reconstruction.workbench import AuditWorkbench
from research_harness.governance import PatchService

class PatchTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.source=self.root/'source';self.source.mkdir();(self.source/'observation.txt').write_text('Synthetic observation: at fixed condition, measured value = 2.\n')
        self.store=Store(self.root/'state'); self.store.initialize_project({'project_id':'test','allowed_actions':['deterministic_postprocess']})
        self.ing=Ingestor(self.store,{'project_id':'test','sources':[{'id':'source','root':str(self.source)}]})
        a=self.ing.capture(self.source/'observation.txt');self.loc=self.ing.locator(a)
        self.put('case','audit_case',source_locators=[self.loc],allowed_actions=['deterministic_postprocess'])
        wb=AuditWorkbench(self.store,self.ing);packet=wb.packet('case')
        blob=self.store.put_blob(b'Actual fixture verification: lexical value captured as 2; synthetic test only.')
        self.put('check','verification_receipt',blob_refs=[blob],input_read_set=packet['read_set'],method='fixture lexical observation',actual_output='2',verification_mode='synthetic_test')
        reads={**packet['read_set'],'check':self.store.get('check')['revision']}
        wb.submit('case',{'actual_read_set':reads,'completed_analysis':'Verified fixture condition and parsed value from captured source. Synthetic test, not real science.',
                         'competing_explanations':['Unspecified condition is excluded by source text'],'verdict':'qualified','scope':{'condition':'fixed'},
                         'first_failing_condition':None,'residual_assets':[a['id']],'unresolved':[],'verification_receipts':['check'],
                         'reviewer':'fixture reviewer','policy_revision':self.store.active_policy_revision()})
        self.put('claim','claim',text='An unbounded extrapolation',scope={'condition':'all'})
        self.service=PatchService(self.store,self.ing)
    def put(self,id,kind,**data): upsert(self.store,[{'id':id,'kind':kind,'data':data}],'fixture')
    def patch(self,operation='change_claim_scope',target='claim',payload=None):
        return {'schema_version':'0.1.0','project_id':'test','id':'patch1','is_example':True,'kind':'scientific_patch','status':'proposed',
            'read_set':[{'object_id':r['id'],'revision':r['revision']} for r in self.store.list()],
            'policy_revision':self.store.active_policy_revision(),'idempotency_key':'patch-key',
            'reason':{'original_statement':'Correct fixture scope','reason_type':'scope_correction','evidence_refs':['case:result']},
            'operations':[{'operation':operation,'target_id':target,'payload':payload or {'scope':{'condition':'fixed'}}}],
            'support_recompute_required':True,'proposed_impact':{'potentially_affected_ids':['claim'],'expected_preserved_ids':[],'note':'fixture'},
            'verification_refs':['case:result'],'extensions':{}}
    def test_real_workbench_result_scope_commit_duplicate_and_conflict(self):
        p=self.patch();before=self.store.get('claim')
        result=self.service.commit(p)
        self.assertEqual(self.store.get('claim')['id'],before['id'])
        self.assertEqual(self.store.get('claim')['data']['scope'],{'condition':'fixed'})
        self.assertEqual(self.service.commit(p),result)
        altered=copy.deepcopy(p);altered['operations'][0]['payload']['scope']={'condition':'different'}
        with self.assertRaises(ConflictError): self.service.commit(altered)
    def test_changed_audit_input_requires_reassessment(self):
        p=self.patch();(self.source/'observation.txt').write_text('Different observation under different conditions.\n');self.ing.refresh()
        with self.assertRaises(ConflictError): self.service.commit(p)
        # Even fresh patch reads cannot wash away the old audit's source versions.
        with self.assertRaises(ConflictError): self.service.commit(self.patch())
    def test_changed_case_scope_cannot_reuse_its_old_result(self):
        case=self.store.get('case')
        self.put('case','audit_case',**{**case['data'],'scope':{'condition':'changed after review'}})
        with self.assertRaises(ConflictError): self.service.commit(self.patch())
    def test_raw_capture_does_not_create_intrinsic_scientific_truth(self):
        p=self.patch('add_evidence','new-evidence',{'source_locators':[self.loc,self.loc],'scope':{'condition':'fixed'}})
        self.service.commit(p);d=self.store.get('new-evidence')['data']
        self.assertFalse(d['intrinsic_valid']);self.assertEqual(len(d['source_content_identities']),1)
        self.assertNotEqual(d['support_status'],'supported')
    def test_qualification_requires_actual_matching_completed_audit(self):
        p=self.patch('add_evidence','qualified-evidence',{'source_locators':[self.loc],'scope':{'condition':'fixed'},'intrinsic_valid':True,'qualification':'audited_observation'})
        self.service.commit(p);self.assertEqual(self.store.get('qualified-evidence')['data']['support_status'],'supported')
    def test_refutation_keeps_original_and_negative_scope(self):
        self.put('e','evidence',intrinsic_valid=True);self.put('claim','claim',text='Wrong proposition',support_sets=[['e']])
        p=self.patch('record_refutation',payload={'scope':{'condition':'fixed'},'residual_assets':['e'],'reopen_conditions':['new discriminating evidence']})
        self.service.commit(p)
        self.assertEqual(self.store.get('claim')['data']['support_status'],'unsupported')
        self.assertTrue(self.store.get('claim')['data']['adjudication_supported'])
        negative=self.store.list('negative_knowledge')[0]
        self.assertEqual(negative['data']['residual_assets'],['e'])
        self.assertEqual(self.store.get('claim',1)['data']['text'],'An unbounded extrapolation')
    def test_governance_and_unverified_reference_rejected(self):
        p=self.patch();p['operations'][0]['payload']['allowed_actions']=['new_md']
        with self.assertRaises(HarnessError): self.service.commit(p)
        p=self.patch();p['verification_refs']=['claim']
        with self.assertRaises(HarnessError): self.service.commit(p)
        p=self.patch('revoke_assumption','project:contract',{'reason':'no'})
        with self.assertRaises(HarnessError): self.service.commit(p)
    def test_support_requires_original_read_set(self):
        self.put('extra','evidence',intrinsic_valid=True)
        p=self.patch();p['read_set']=[r for r in p['read_set'] if r['object_id']!='extra']
        p['operations'][0]['payload']['support_sets']=[['extra']]
        with self.assertRaises(ConflictError): self.service.commit(p)

if __name__=='__main__': unittest.main()
