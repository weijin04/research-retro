import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from research_harness.common import HarnessError, upsert
from research_harness.ingest.service import Ingestor
from research_harness.parsers.basic import parse
from research_harness.storage import Store

class IngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name); self.source=self.base/'source'; self.source.mkdir()
        self.store=Store(self.base/'store')
        self.ing=Ingestor(self.store,{'project_id':'fixture','sources':[{'id':'s','root':str(self.source),'egress':'denied'}]})
    def file(self,name='sample.txt',text='T=300 K\nvalidity unknown\n'):
        p=self.source/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text); return p
    def supported(self,a):
        upsert(self.store,[{'id':'e','kind':'Evidence','data':{'intrinsic_valid':True,'source_locators':[self.ing.locator(a)]}},
                          {'id':'c','kind':'Claim','data':{'support_sets':[['e']]}}],'test source dependence')
        self.assertEqual(self.store.get('c')['data']['support_status'],'supported')
    def test_historical_snapshot_same_size_rewrite_and_dependency(self):
        p=self.file(text='old\n'); a=self.ing.capture(p); loc=self.ing.locator(a); self.supported(a)
        stamp=p.stat(); p.write_text('new\n'); os.utime(p,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        self.assertEqual(self.ing.refresh()[0]['status'],'source_changed')
        self.assertEqual(self.ing.read(loc),'old')
        self.assertEqual(self.store.get('c')['data']['support_status'],'unsupported')
        with self.assertRaises(HarnessError): self.ing.read(loc,live=True)
    def test_deleted_source_refresh_invalidates_but_retains_copy(self):
        p=self.file(); a=self.ing.capture(p); loc=self.ing.locator(a); self.supported(a); p.unlink()
        self.ing.refresh()
        self.assertEqual(self.store.get('c')['data']['support_status'],'unsupported')
        self.assertEqual(self.store.get(a['id'])['data']['read_state'],'unavailable')
        self.assertIn('300',self.ing.read(loc))
    def test_deleted_source_complete_scan_invalidates(self):
        p=self.file(); a=self.ing.capture(p); self.supported(a); self.ing.scan('s'); p.unlink(); self.ing.scan('s')
        self.assertTrue(self.store.get('e')['data']['revoked'])
    def test_first_scan_also_detects_deleted_captured_source(self):
        p=self.file(); a=self.ing.capture(p); self.supported(a); p.unlink(); self.ing.scan('s')
        self.assertTrue(self.store.get('e')['data']['revoked'])
    def test_outside_and_excluded_paths_do_not_resolve(self):
        self.ing.manifest['sources'][0]['excludes']=['excluded']
        with patch('pathlib.Path.resolve',side_effect=AssertionError('must not touch outside filesystem')):
            for path in (self.base/'unavailable-mount'/'record',self.source/'excluded'/'record'):
                with self.assertRaises(HarnessError) as raised:
                    self.ing.allowed(path)
                self.assertEqual(raised.exception.code,'permission_denied')
    def test_symlink_escape_denied(self):
        outside=self.base/'private'; outside.write_text('private'); (self.source/'link').symlink_to(outside)
        with self.assertRaises(HarnessError): self.ing.capture(self.source/'link')
    def test_intermediate_symlink_swap_never_opens_outside_file(self):
        p=self.file('dir/sample.txt','allowed'); outside=self.base/'outside'; outside.mkdir(); (outside/'sample.txt').write_text('PRIVATE')
        original_open=os.open; opened=[]; swapped=False
        def racing_open(path,flags,*args,**kwargs):
            nonlocal swapped
            if not swapped:
                swapped=True
                (self.source/'dir').rename(self.source/'held'); (self.source/'dir').symlink_to(outside,target_is_directory=True)
            fd=original_open(path,flags,*args,**kwargs)
            opened.append(os.readlink('/proc/self/fd/'+str(fd)))
            return fd
        with patch('research_harness.ingest.service.os.open',side_effect=racing_open):
            with self.assertRaises((OSError,HarnessError)): self.ing.capture(p)
        self.assertNotIn(str(outside/'sample.txt'),opened)
        self.assertEqual(self.store.list('artifact'),[])
    def test_csv_logical_locator_retains_condition_columns_and_no_promotion(self):
        p=self.file('history.csv','name,condition,decision\ncase,"300 K\nNVT",valid\n')
        result=self.ing.import_table(p); again=self.ing.import_table(p)
        self.assertEqual(again['status'],'unchanged'); self.assertEqual(result['status'],'imported_assertion')
        row=self.ing.query_tables('300')[0]
        self.assertEqual(row['raw']['condition'],'300 K\nNVT')
        self.assertEqual(self.ing.read(row['source_locator'])['rows'][0],row['raw'])
        index=self.store.get(result['id'])
        self.assertEqual(index['data']['current_scientific_validity'],'unchecked')
        self.assertEqual(self.store.list('Evidence'),[])
    def test_zip_dangerous_directory_is_never_extracted(self):
        p=self.source/'bundle.zip'
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('../escape.txt','danger'); z.writestr('/absolute.txt','danger')
            z.writestr('execute.py','raise RuntimeError("must not execute")')
        result=self.ing.archive_directory(p)
        self.assertEqual(result['state'],'directory_only'); self.assertFalse(result['extracted'])
        self.assertEqual(sum(r['unsafe_path'] for r in result['entries']),2)
        self.assertFalse((self.base/'escape.txt').exists()); self.assertFalse((self.source/'execute.py').exists())
    def test_parser_execution_and_convergence_not_promoted(self):
        r=parse(b'FINAL SINGLE POINT ENERGY -10.0\nORCA TERMINATED NORMALLY\n','a.out')
        self.assertEqual(r['axes']['process_completed'],'observed_normal_marker')
        self.assertEqual(r['axes']['scientific_test_validity'],'unchecked')
        r=parse(b'raise RuntimeError("must not execute")','a.py')
        self.assertEqual(r['records'][0]['type'],'Call')

if __name__=='__main__': unittest.main()
