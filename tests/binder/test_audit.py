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
        self.assertEqual(audit.score(results,'pass'),dict(earned=97.5,applicable=100.0,raw=98,effective=98))
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
