import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research_harness.storage import Store
from research_harness.context import build_context
from research_harness.views import export_report, query


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / "state")
        self.source = self.root / "original.txt"
        self.source.write_text("original scientific observation")
        self.digest = self.store.put_blob(self.source.read_bytes())
        self.store.commit([
            {"id": "claim", "kind": "Claim", "data": {"text": "<script>alert(1)</script>", "support_sets": [["ev"]]}},
            {"id": "ev", "kind": "evidence", "data": {"intrinsic_valid": True, "blob_refs": [self.digest]}},
            {"id": "audit", "kind": "audit_case", "data": {"status": "unresolved", "source_locators": [{"path": str(self.source), "sha256": self.digest, "line_start": 1}]}},
            {"id": "negative", "kind": "negative_knowledge", "data": {"text": "do not infer kinetics from endpoints"}},
            {"id": "index", "kind": "imported_assertion", "data": {"rows": "historical text " * 10000}},
        ], "seed", {}, "seed")

    def test_export_source_escape_repeat_staleness(self):
        report = export_report(self.store, self.root / "reports")
        html = Path(report["html"]).read_text()
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("sources/" + self.digest, html)
        self.assertEqual((Path(report["version_dir"]) / "sources" / self.digest).read_bytes(), self.source.read_bytes())
        self.assertLess(Path(report["report"]).stat().st_size, 20000)
        self.assertEqual(export_report(self.store, self.root / "reports")["version_dir"], report["version_dir"])
        self.store.commit([{"id": "new", "kind": "correction", "data": {"text": "correction"}}], "correction", {}, "update")
        self.assertTrue(self.store.view_status("report")["stale"])
        with patch.object(self.store, "read_blob", side_effect=OSError("render failed")):
            with self.assertRaises(OSError):
                export_report(self.store, self.root / "reports")
        self.assertTrue(self.store.view_status("report")["stale"])
        self.assertTrue(Path(report["html"]).exists())
        self.assertEqual(self.source.read_text(), "original scientific observation")
        handoff = json.loads(Path(report["handoff"]).read_text())
        self.assertEqual(handoff["history_tracks"]["then_believed"]["status"], "unknown")
        self.assertIn("audit", handoff["unknown_or_unfinished"])

    def test_static_reader_safe_payload_roundtrip_and_locator_versions(self):
        hostile='</script><img src=x onerror=alert(1)>\nconditions < 300 K'
        self.store.commit([
            {'id':'case-reader','kind':'audit_case','data':{'title':hostile,'status':'pending','source_locators':[{
                'artifact_id':'original','artifact_revision':7,'uri':'/original/log.out',
                'content_identity':{'digest':self.digest},'locator':{'type':'lines','start':3,'end':9}}]}},
            {'id':'map','kind':'scientific_map','data':{'title':'Map overview'}},
            {'id':'asset','kind':'reusable_asset','data':{'title':'Reusable result'}},
            {'id':'queue','kind':'audit_candidate','data':{'title':'Candidate awaiting audit'}}
        ],'reader test',{},'reader-test')
        exported=export_report(self.store,self.root/'reader')
        page=Path(exported['html']).read_text()
        payload=page.split('<script id="snapshot-data" type="application/json">',1)[1].split('</script>',1)[0]
        decoded=json.loads(payload)
        self.assertEqual(next(r for r in decoded['records'] if r['id']=='case-reader')['data']['title'],hostile)
        self.assertNotIn('<img src=x',page)
        self.assertIn('revision 7 · lines 3–9',page)
        self.assertIn('script-src',page);self.assertIn("'self'",page)
        app=(Path(exported['version_dir'])/'app.js').read_text()
        self.assertNotIn('innerHTML',app);self.assertNotIn('fetch(',app)
        self.assertIn('textContent',app);self.assertIn('details[data-record]',app)
        for section in ('coverage','assets','queue','history','branches'):
            self.assertIn('id="'+section+'"',page)
        self.assertEqual(decoded,json.loads(Path(exported['state']).read_text()))

    def test_history_separates_refuted_adjudication_from_warranted_proposition(self):
        self.store.commit([
            {'id':'refuted','kind':'claim','data':{'text':'Original wrong claim','evidence_status':'refuted','support_sets':[['ev']]}},
            {'id':'unknown-claim','kind':'claim','data':{'text':'Not established','qualification':'unchecked','support_sets':[['ev']]}},
            {'id':'pending-case','kind':'audit_case','data':{'status':'pending','support_sets':[['ev']]}},
            {'id':'accepted','kind':'claim','data':{'text':'Bounded accepted result','evidence_status':'qualified','support_sets':[['ev']]}},
        ],'history fixture',{'ev':self.store.get('ev')['revision']},'history-fixture')
        report=export_report(self.store,self.root/'history')
        handoff=json.loads(Path(report['handoff']).read_text())
        current=handoff['history_tracks']['currently_warranted']['record_ids']
        self.assertIn('accepted',current)
        for identifier in ('refuted','unknown-claim','pending-case','audit'):
            self.assertNotIn(identifier,current)
        self.assertIn('refuted',handoff['supported_adjudications'])
        self.assertNotIn('pending-case',handoff['supported_adjudications'])

    def test_exact_id_query_precedes_case_mentions_and_brief_accepts_provenance_shapes(self):
        from research_harness.views.report import brief
        target='t13b-c-complete-detachment'
        self.store.commit([
            {'id':'aaa-large-case','kind':'audit_case','data':{'text':'Large case mentions '+target,'provenance':'researcher adjudication plus verified reproduction'}},
            {'id':target,'kind':'branch','data':{'title':'Complete detachment','provenance':{'qualification':'scoped'}}},
            {'id':'unknown-provenance','kind':'branch','data':{'provenance':None}},
        ],'query regression',{},'query-regression')
        first=query(self.store,target,limit=1)[0]
        self.assertEqual(first['id'],target)
        self.assertEqual(brief(first)['qualification'],'scoped')
        self.assertEqual(brief(self.store.get('aaa-large-case'))['qualification'],'unknown')
        self.assertEqual(brief(self.store.get('unknown-provenance'))['qualification'],'unknown')
        self.assertTrue(brief(self.store.get('aaa-large-case'))['summary'])
        self.assertEqual(query(self.store,target,kind='audit_case')[0]['id'],'aaa-large-case')

    def test_context_mandatory_budget_and_hash(self):
        packet = build_context(self.store, task="check", budget_chars=50)
        self.assertEqual(packet["budget_status"], "requires_multiple_chunks")
        self.assertGreater(packet["required_chars"], 50)
        self.assertEqual(set(packet["read_set"]), {"audit", "claim", "negative"})
        self.assertTrue(all(len(c["content"]) <= 50 for c in packet["chunks"]))
        for item in packet["items"]:
            text = "".join(c["content"] for c in packet["chunks"] if c["id"] == item["id"])
            self.assertEqual(json.loads(text), item)
        self.assertEqual(packet["content_hash"], build_context(self.store, task="check", budget_chars=50)["content_hash"])
        self.assertEqual(query(self.store, "SCRIPT", "claim")[0]["id"], "claim")
        self.assertEqual(query(self.store, "", limit=0), [])


if __name__ == "__main__":
    unittest.main()
