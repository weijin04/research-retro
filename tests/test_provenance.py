import tempfile
from pathlib import Path
import unittest
from research_harness.common import HarnessError,upsert
from research_harness.storage import Store
from research_harness.reconstruction.provenance import source_families,propose_alias,revoke_alias

class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.store=Store(Path(t.name)/'state')
    def put(self,id,kind='object',**data): upsert(self.store,[{'id':id,'kind':kind,'data':data}],'fixture')
    def test_duplicate_bytes_retains_paths_not_independent_samples(self):
        sha=self.store.put_blob(b'one experiment')
        self.put('a','artifact',sha256=sha,path='/source/a'); self.put('b','artifact',sha256=sha,path='/copy/b')
        family=source_families(self.store)['byte_duplicate_families'][0]
        self.assertEqual(len(family['members']),2); self.assertEqual(family['byte_identity_count'],1)
        self.assertIsNone(family['independent_sample_count'])
        self.assertEqual({r['path'] for r in family['members']},{'/source/a','/copy/b'})
    def test_same_name_different_objects_rejected_and_unknown_only_candidate(self):
        self.put('a',name='X',composition='Fe',charge=0); self.put('b',name='X',composition='Co',charge=0)
        with self.assertRaises(HarnessError): propose_alias(self.store,'a','b','same_object',{'domain':'chemistry'},'review','tester')
        self.assertEqual(len(source_families(self.store)['semantic_equivalence_candidates']),1)
        self.put('c',name='X',composition='Fe',charge=0)
        result=propose_alias(self.store,'a','c','same_object',{'domain':'chemistry'},'unknown geometry','tester')
        self.assertEqual(result['record']['data']['status'],'candidate')
        self.assertFalse(result['record']['data']['merge_performed'])
        self.assertIn('geometry',result['record']['data']['comparison']['unknown'])
    def test_four_relation_conditions_separate(self):
        for id in ('a','b'): self.put(id,composition='Fe',charge=0,multiplicity=1,geometry='sha-geometry',environment='vacuum')
        same=propose_alias(self.store,'a','b','same_object',{'domain':'chemistry'},'same explicit conditions','tester')
        self.assertEqual(same['record']['data']['status'],'reviewed_compatible')
        for relation in ('same_run','numerical_comparison','same_proposition'):
            r=propose_alias(self.store,'a','b',relation,{'domain':'chemistry'},'separate identity question','tester')
            self.assertEqual(r['record']['data']['status'],'candidate')
        self.assertEqual(len(self.store.list('identity_relation')),4)
    def test_alias_revocation_preserves_objects_and_history(self):
        self.put('a',actual_input_sha256='in',execution_id='job',output_sha256='out')
        self.put('b',actual_input_sha256='in',execution_id='job',output_sha256='out')
        alias=propose_alias(self.store,'a','b','same_run',{'domain':'chemistry'},'matching receipts','reviewer')['record']
        revoked=revoke_alias(self.store,alias['id'],'recheck identity','reviewer')['record']
        self.assertEqual(revoked['revision'],alias['revision']+1)
        self.assertTrue(revoked['data']['revoked'])
        self.assertFalse(self.store.get(alias['id'],alias['revision'])['data']['revoked'])
        self.assertEqual(self.store.get('a')['revision'],1); self.assertEqual(self.store.get('b')['revision'],1)
    def test_cycles_do_not_create_support_and_external_support_remains_distinct(self):
        upsert(self.store,[{'id':'x','kind':'Claim','data':{'support_sets':[['y']]}},
                           {'id':'y','kind':'Claim','data':{'support_sets':[['x']]}}],'cyclic fixture')
        cycles=source_families(self.store)['cycles']
        self.assertEqual(cycles[0]['members'],['x','y'])
        self.assertEqual(cycles[0]['external_dependencies'],[])
        self.assertEqual(set(cycles[0]['support_status_by_member'].values()),{'unsupported'})
        self.put('external','Evidence',intrinsic_valid=True)
        self.put('x','Claim',support_sets=[['y'],['external']])
        report=source_families(self.store)
        self.assertEqual(report['cycles'][0]['external_dependencies'],['external'])
        self.assertEqual(report['cycles'][0]['external_supported_records'],['external'])
        self.assertEqual(set(report['cycles'][0]['support_status_by_member'].values()),{'supported'})
        self.put('external','Evidence',intrinsic_valid=True,revoked=True)
        self.assertEqual(set(source_families(self.store)['cycles'][0]['support_status_by_member'].values()),{'unsupported'})
    def test_common_ancestor_and_no_invented_edges(self):
        self.put('raw'); self.put('a',derived_from=['raw']); self.put('b',source_dependencies=['raw'])
        result=source_families(self.store)
        self.assertIn({'ancestor':'raw','descendants':['a','b']},result['common_ancestors'])
        self.assertEqual(len(result['derivation_edges']),2)
    def test_missing_domain_fails_closed(self):
        self.put('a'); self.put('b')
        with self.assertRaises(HarnessError): propose_alias(self.store,'a','b','same_object',{},'reason','reviewer')

if __name__=='__main__': unittest.main()
