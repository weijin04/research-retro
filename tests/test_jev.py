import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from research_harness.decisions import JevAdapter

Q={'q':{'type':'noul','instructions':'Does the synthetic example report completion?'}}

def response(body):
    return {'model':'jev-1.13.0','answers':{'q':{'type':'noul','noul':.9}},'usage':{'input_tokens':10,'output_tokens':2}}

class JevTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def evaluate(self, adapter, **kwargs):
        values=dict(task_family='test',state='synthetic complete',questions=Q,questions_version='q1',policy_version='p1',requested_model='jev-1.13.0',egress_scope='synthetic')
        values.update(kwargs)
        return adapter.evaluate(**values)
    def test_private_never_transmitted_or_persisted(self):
        def forbidden(body): raise AssertionError('network called')
        result=self.evaluate(JevAdapter(self.path,transport=forbidden),state='PRIVATE_SECRET',egress_scope='research')
        self.assertEqual(result['error_category'],'privacy_denied')
        self.assertNotIn('PRIVATE_SECRET',Path(result['record_path']).read_text())
    def test_alias_never_cached(self):
        calls=[]
        def send(body): calls.append(body); return response(body)
        adapter=JevAdapter(self.path,transport=send)
        self.evaluate(adapter,requested_model='jev-latest')
        self.assertFalse(self.evaluate(adapter,requested_model='jev-latest')['cache_hit'])
        self.assertEqual(len(calls),2)
    def test_pinned_cache_versions_and_conditions(self):
        calls=[]
        def send(body): calls.append(body); return response(body)
        adapter=JevAdapter(self.path,transport=send)
        self.evaluate(adapter)
        cached=self.evaluate(adapter)
        self.assertTrue(cached['cache_hit'])
        self.assertEqual(cached['usage']['input_tokens'],0)
        for change in ({'policy_version':'p2'},{'questions_version':'q2'},{'candidate_version':'c2'},{'content_version':'v2'},{'state':'different condition'},{'questions':{'q':{'type':'noul','instructions':'A different question?'}}}):
            self.assertFalse(self.evaluate(adapter,**change)['cache_hit'])
        self.assertEqual(len(calls),7)
    def test_retry_budget_and_error(self):
        calls=[]
        def failed(body): calls.append(body); raise HTTPError('https://api.typesafe.ai',429,'limit',{},None)
        result=self.evaluate(JevAdapter(self.path,transport=failed,max_attempts=3),attempt_budget=2)
        self.assertEqual(len(calls),2)
        self.assertEqual(result['retries'],1)
        self.assertEqual(result['error_category'],'rate_limit')
        self.assertEqual(result['action'],'advisory')
    def test_zero_budget_and_bad_contract(self):
        adapter=JevAdapter(self.path,transport=lambda body: {})
        self.assertEqual(self.evaluate(adapter,attempt_budget=0)['error_category'],'attempt_budget_exhausted')
        self.assertEqual(self.evaluate(adapter)['error_category'],'response_contract')
    def test_auth_not_retried(self):
        def failed(body): raise HTTPError('https://api.typesafe.ai',401,'invalid',{},None)
        result=self.evaluate(JevAdapter(self.path,transport=failed))
        self.assertEqual(len(result['attempts']),1)
        self.assertEqual(result['error_category'],'authentication')
    def test_unsafe_endpoint(self):
        for endpoint in ('http://host/x','https://user:password@host/x','https://host/x?key=secret'):
            with self.assertRaises(ValueError): JevAdapter(self.path,endpoint=endpoint)

if __name__=='__main__': unittest.main()
