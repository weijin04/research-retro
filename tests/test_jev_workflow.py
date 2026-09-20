import json
import tempfile
from pathlib import Path
import unittest
from research_harness.storage import Store
from research_harness.decisions import JevAdapter
from research_harness.decisions.workflow import attach_advice,LOCAL_CASE_ID

class JevWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.store=Store(self.root/'state')
        self.store.commit([{'id':LOCAL_CASE_ID,'kind':'audit_case','data':{
            'text':'PRIVATE_ORIGINAL_SCIENTIFIC_TEXT','path':'/private/science/source','status':'pending'}}],'fixture',{},'fixture')
    def test_mock_is_labeled_and_private_state_never_sent(self):
        sent=[]
        def transport(body):
            sent.append(body)
            return {'model':'jev-1.13.0','usage':{'input_tokens':1,'output_tokens':1},'answers':{
                k:{'type':'choice','choice':next(iter(q['criteria'])),'confidence':1.,
                   'probabilities':{c:float(i==0) for i,c in enumerate(q['criteria'])}} for k,q in body['questions'].items()}}
        adapter=JevAdapter(self.root/'receipts',transport=transport)
        receipt=attach_advice(self.store,self.root/'receipts',adapter=adapter)
        self.assertEqual(len(sent),2)
        serialized=json.dumps(sent)
        for prohibited in (LOCAL_CASE_ID,'PRIVATE_ORIGINAL_SCIENTIFIC_TEXT','/private/science/source','grephene'):
            self.assertNotIn(prohibited,serialized)
        self.assertEqual(receipt['execution_mode'],'mock_injected')
        self.assertEqual(len(self.store.list('audit_suggestion')),2)
        self.assertEqual(self.store.get(LOCAL_CASE_ID)['revision'],1)
        self.assertEqual(self.store.get(LOCAL_CASE_ID)['data']['status'],'pending')
        attach_advice(self.store,self.root/'receipts',adapter=adapter)
        self.assertEqual(len(sent),2)
        for record in self.store.list('decision_record'):
            self.assertFalse(record['data']['private_raw_data_evaluated'])
            self.assertNotIn('support_sets',record['data'])
    def test_service_failure_is_recoverable_candidate(self):
        def failed(body): raise TimeoutError('test transport timeout')
        adapter=JevAdapter(self.root/'receipts',transport=failed,max_attempts=1)
        result=attach_advice(self.store,self.root/'receipts',adapter=adapter)
        self.assertEqual(result['status'],'attached')
        self.assertEqual(self.store.get(LOCAL_CASE_ID)['revision'],1)
        self.assertTrue(all(r['data']['status']=='recoverable_service_failure' for r in self.store.list('audit_suggestion')))
        self.assertTrue(all(r['data']['execution_mode']=='mock_injected' for r in self.store.list('decision_record')))

if __name__=='__main__': unittest.main()
