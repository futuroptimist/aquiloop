"""Synthetic scoring fixtures; no real habitat or approval data."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import binder_audit as audit

class AuditTests(unittest.TestCase):
    def outcomes(self,state='pass'):
        return {key:dict(state=state,reason='Synthetic evidence case',evidence=['synthetic/source.json'],next_step='Inspect missing evidence') for key in audit.rubric_checks()}
    def test_weights_and_zero_partial_full(self):
        self.assertEqual(len(audit.rubric_checks()),40)
        self.assertEqual(audit.score(self.outcomes(),'pass')['raw'],100)
        self.assertEqual(audit.score(self.outcomes('fail'),'pass')['raw'],0)
        results=self.outcomes();results['V1b']['state']='fail'
        self.assertEqual(audit.score(results,'pass'),dict(earned=97.5,applicable=100.0,normalized=97.5,raw=98,effective=98))
    def test_caps(self):
        self.assertEqual(audit.score(self.outcomes(),'fail')['effective'],49)
        self.assertEqual(audit.score(self.outcomes(),'pending')['effective'],69)
    def test_na_needs_biological_reason_and_signoff(self):
        outcomes=self.outcomes();outcomes['R1a']['state']='na'
        with self.assertRaises(ValueError):audit.score(outcomes,'pass')
        outcomes['R1a'].update(biological_reason='Synthetic irrelevant subcheck',reviewer='Synthetic reviewer')
        self.assertEqual(audit.score(outcomes,'pass')['applicable'],97.5)
        self.assertEqual(audit.score(outcomes,'pass')['raw'],100)
        for key in ['I1a','S1a','E1a','Q1a']:
            altered=copy.deepcopy(outcomes);altered[key]=outcomes['R1a']
            with self.assertRaises(ValueError):audit.score(altered,'pass')
    def test_missing_evidence_unknown_and_duplicates_rejected(self):
        for mutate in [lambda d:d.pop('I1a'),lambda d:d['I1a'].update(state='unknown'),lambda d:d['I1a'].update(evidence=[]),lambda d:d['I1a'].update(state='fail',next_step='')]:
            d=self.outcomes();mutate(d)
            with self.assertRaises(ValueError):audit.score(d,'pass')

    def report(self):
        import hashlib
        from binder_logs import tracked_species
        from build_binder import load_manifest
        root=audit.ROOT
        ids=tracked_species(load_manifest(root/'binder/manifest-v8.yaml'))
        outcomes=self.outcomes('fail')
        for item in outcomes.values():item.pop('evidence')
        return dict(schema_version=1,rubric='aquiloop-entry-quality-v1',commit='a'*40,pdf_sha256='b'*64,audited='2026-10-11',manifest='binder/manifest-v8.yaml',source_snapshots={'binder/audit/rubric-v1.json':hashlib.sha256(audit.RUBRIC_PATH.read_bytes()).hexdigest()},entries=[dict(id=id,working_name='Synthetic working name',status='Synthetic fixture only',gate='pending',gate_reason='Synthetic unverified case',document_status='Synthetic draft',pages=list(range(i*3+1,i*3+4)),sections=['Care','Conditions','Reproduction'],unknowns=['Synthetic unknown'],improvements=['Inspect evidence'],outcomes=copy.deepcopy(outcomes),totals=audit.score(outcomes,'pending')) for i,id in enumerate(ids)])
    def test_exact_inventory_and_snapshot_links(self):
        report=self.report();self.assertEqual(len(audit.validate(report)),13)
        for mutate in [lambda d:d['entries'].pop(),lambda d:d['entries'].append(d['entries'][0]),lambda d:d['source_snapshots'].update({'binder/audit/rubric-v1.json':'0'*64}),lambda d:d['entries'][0]['totals'].update(raw=100),lambda d:d['entries'][0].update(pages=[4,5,6])]:
            changed=copy.deepcopy(report);mutate(changed)
            with self.assertRaises(ValueError):audit.validate(changed)
    def test_pass_requires_resolvable_versioned_evidence(self):
        report=self.report();record=report['entries'][0]
        record['outcomes']['I1a'].update(state='pass',evidence=['missing/source.json#claim'])
        record['totals']=audit.score(record['outcomes'],'pending')
        with self.assertRaises(ValueError):audit.validate(report)
        record['outcomes']['I1a']['evidence']=['pdf:46']
        with self.assertRaises(ValueError):audit.validate(report)

    def test_json_duplicate_keys_and_nonfinite_values_rejected(self):
        for raw in ['{"outcomes":{"I1a":{"state":"pass"},"I1a":{"state":"fail"}}}', '{"commit":"a","commit":"b"}', '{"raw":NaN}', '{"raw":Infinity}']:
            with self.assertRaises(ValueError):audit.parse_report(raw)
        self.assertEqual(audit.parse_report('{"value":2.5}'),{'value':2.5})

    def test_lossless_numbers_and_total_comparison(self):
        from decimal import Decimal
        import json
        parsed=audit.parse_report('{"small":1e-999,"large":1e999,"precise":97.5000000000000001}')
        self.assertEqual(parsed['small'],Decimal('1e-999'))
        self.assertTrue(parsed['large'].is_finite())
        self.assertEqual(parsed['precise'],Decimal('97.5000000000000001'))
        report=self.report()
        for value in [Decimal('1e-999'),Decimal('1e999'),False]:
            changed=copy.deepcopy(report)
            changed['entries'][0]['totals']['earned']=value
            with self.assertRaises(ValueError):audit.validate(changed)
        changed=copy.deepcopy(report)
        changed['entries'][0]['totals']['applicable']=Decimal('100.0000000000000001')
        with self.assertRaises(ValueError):audit.validate(changed)
        audit.validate(audit.parse_report(json.dumps(report)))
