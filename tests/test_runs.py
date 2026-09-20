import tempfile
from pathlib import Path
import unittest
from research_harness.storage import Store
from research_harness.ingest.service import Ingestor
from research_cases.legacy.runs import reconstruct_captured_runs

class RunTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.source=self.root/'source';self.source.mkdir();self.store=Store(self.root/'store')
        self.ing=Ingestor(self.store,{'project_id':'fixture','sources':[{'id':'s','root':str(self.source)}]})
    def capture(self,name,text):
        p=self.source/name;p.write_text(text);return self.ing.capture(p)
    def test_executed_echo_not_current_input_and_normal_not_science(self):
        self.capture('run.inp','! NEW_METHOD\n* xyzfile 0 1 latest.xyz\n')
        self.capture('run.out','O   R   C   A\nProgram Version 5.0.4\nINPUT FILE\n| 1> ! OLD_METHOD\n| 2> * xyzfile 1 2 original.xyz\nORCA TERMINATED NORMALLY\n')
        reconstruct_captured_runs(self.store,self.ing);r=self.store.list('run')[0]['data']
        self.assertEqual(r['identity']['method'],['OLD_METHOD']);self.assertEqual(r['identity']['charge'],1)
        self.assertEqual(r['geometry_reference'],'original.xyz')
        self.assertEqual(r['input_candidates'][0]['qualification'],'candidate_not_historical_input')
        self.assertEqual(r['axes']['process_completion'],'observed_normal_marker')
        self.assertEqual(r['axes']['scientific_test_validity'],'unchecked')
        self.assertEqual(r['actual_binary_sha256'],'unknown')
    def test_distinct_outputs_and_old_revision_identity_preserved(self):
        a=self.capture('a.out','FINAL SINGLE POINT ENERGY -1.0\n');self.capture('b.out','FINAL SINGLE POINT ENERGY -1.0\n')
        reconstruct_captured_runs(self.store,self.ing);self.assertEqual(len(self.store.list('run')),2)
        old=next(r for r in self.store.list('run') if r['data']['output_artifact_id']==a['id'])
        self.assertEqual(old['data']['identity']['method'],'unknown')
        self.capture('a.out','FINAL SINGLE POINT ENERGY -2.0\n');reconstruct_captured_runs(self.store,self.ing)
        current=self.store.get(old['id'])
        self.assertNotEqual(current['data']['output_sha256'],old['data']['output_sha256'])
        self.assertEqual(self.store.get(old['id'],old['revision'])['data']['output_sha256'],old['data']['output_sha256'])
    def test_verified_text_match_inline_composition_and_scan_boundary(self):
        inp='! PBE\n* xyz 0 1\nH 0 0 0\nH 0 0 1\n*'
        self.capture('a.inp',inp)
        self.capture('a.out','O   R   C   A\nINPUT FILE\n'+'\n'.join('| '+str(i)+'> '+line for i,line in enumerate(inp.splitlines(),1))+'\nRELAXED SURFACE SCAN\n')
        reconstruct_captured_runs(self.store,self.ing);d=self.store.list('run')[0]['data']
        self.assertEqual(d['input_candidates'][0]['qualification'],'verified_echo_text_match')
        self.assertEqual(d['identity']['composition'],{'H':2})
        self.assertIn('child_candidates',d['execution_structure'])
        self.assertEqual(d['identity']['geometry'],'unknown')
    def test_lammps_planned_steps_not_completion(self):
        self.capture('md.log','LAMMPS (28 Mar 2023)\nrun 20000\nrun 199980000\n')
        reconstruct_captured_runs(self.store,self.ing);d=self.store.list('run')[0]['data']
        self.assertEqual(d['planned_run_segments_steps'],[20000,199980000])
        self.assertEqual(d['axes']['process_completion'],'observed_prefix_only')

if __name__=='__main__': unittest.main()
