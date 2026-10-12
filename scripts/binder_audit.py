"""Validate human-authored entry audits; never infer factual or visual passes."""
from __future__ import annotations
import argparse
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import subprocess
from build_binder import ROOT, load_manifest
from binder_logs import tracked_species

RUBRIC_PATH = ROOT / 'binder/audit/rubric-v1.json'

def require(condition, message):
    if not condition:
        raise ValueError(message)

def nonempty(value):
    return isinstance(value, str) and bool(value.strip())

def parse_report(text):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON member: ' + key)
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError('non-finite JSON number: ' + value)
    return json.loads(text, object_pairs_hook=unique_pairs, parse_constant=reject_constant, parse_float=Decimal)


def load_rubric():
    rubric = json.loads(RUBRIC_PATH.read_text(encoding='utf-8'))
    caps = rubric.get('gate_caps')
    require(isinstance(caps, dict) and set(caps) == {'pass', 'pending', 'fail'}, 'invalid gate cap states')
    require(all(type(value) is int and 0 <= value <= 100 for value in caps.values()), 'invalid gate cap values')
    require(caps['fail'] <= caps['pending'] <= caps['pass'] == 100, 'invalid gate cap order')
    return rubric


def rubric_checks(rubric=None):
    rubric = load_rubric() if rubric is None else rubric
    checks = {s['id']: s['text'] for c in rubric['checks'] for s in c['subchecks']}
    require(len(checks) == 40 and rubric['subcheck_points'] == 2.5, 'invalid rubric weight')
    require(sum(rubric['categories'].values()) == 100, 'invalid category total')
    for category, weight in rubric['categories'].items():
        require(sum(k.startswith(category) for k in checks) * 2.5 == weight, 'category weight mismatch')
    return checks

def score(outcomes, gate):
    require(gate in {'pass', 'pending', 'fail'}, 'invalid gate')
    rubric = load_rubric()
    require(isinstance(outcomes, dict) and set(outcomes) == set(rubric_checks(rubric)), 'forty exact outcomes required')
    earned = Decimal(0)
    applicable = Decimal(100)
    for key, result in outcomes.items():
        require(isinstance(result, dict), 'outcome must be object')
        state = result.get('state')
        require(state in {'pass', 'fail', 'na'}, 'unknown is not a scoring state or N/A')
        require(nonempty(result.get('reason')), 'outcome reason required')
        if state == 'na':
            require(key[0] not in 'ISEQV', 'identity, safety, evidence, imagery and proof cannot be N/A')
            require(nonempty(result.get('reviewer')) and nonempty(result.get('biological_reason')), 'N/A needs biological reason and reviewer sign-off')
            applicable -= Decimal('2.5')
        elif state == 'pass':
            require(isinstance(result.get('evidence'), list) and result['evidence'] and all(nonempty(x) for x in result['evidence']), 'pass needs evidence')
            earned += Decimal('2.5')
        else:
            require(nonempty(result.get('next_step')), 'failure needs next step')
    require(applicable > 0, 'no applicable points')
    raw = int((100 * earned / applicable).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return dict(earned=float(earned), applicable=float(applicable),
                normalized=float((100 * earned / applicable).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)), raw=raw,
                effective=min(raw, rubric['gate_caps'][gate]))

def validate(report, root=ROOT):
    require(isinstance(report, dict) and report.get('schema_version') == 1, 'unsupported audit schema')
    require(report.get('rubric') == 'aquiloop-entry-quality-v1', 'rubric mismatch')
    for name, length in [('commit',40), ('pdf_sha256',64)]:
        require(isinstance(report.get(name), str) and re.fullmatch('[0-9a-f]{'+str(length)+'}', report[name]), 'invalid '+name)
    require(date.fromisoformat(report['audited']).isoformat() == report['audited'], 'invalid audit date')
    require(report.get('manifest') == 'binder/manifest-v8.yaml', 'audit requires v8 manifest')
    entries = load_manifest(root / report['manifest'])
    records = report.get('entries')
    require(isinstance(records, list) and [e.get('id') for e in records] == tracked_species(entries), 'exact manifest coverage and order required')
    pages = sum(e['page_budget'] for e in entries)
    snapshots = report.get('source_snapshots')
    require(isinstance(snapshots, dict) and snapshots, 'source-version linkage required')
    for path, digest in snapshots.items():
        target = (root / path).resolve()
        require(root.resolve() in target.parents and target.is_file(), 'invalid snapshot path')
        require(hashlib.sha256(target.read_bytes()).hexdigest() == digest, 'source snapshot mismatch: '+path)
    for index, record in enumerate(records):
        require(all(nonempty(record.get(k)) for k in ('working_name','status','gate_reason','document_status')), 'missing identity/status/gate evidence')
        require(record.get('pages') == list(range(3*index+1,3*index+4)), 'entry pages mismatch')
        require(isinstance(record.get('sections'), list) and len(record['sections']) == 3 and all(nonempty(s) for s in record['sections']), 'three section names required')
        for key in ('unknowns','improvements'):
            require(isinstance(record.get(key), list) and all(nonempty(x) for x in record[key]), 'missing '+key)
        expected = score(record.get('outcomes'),record.get('gate'))
        totals = record.get('totals')
        require(isinstance(totals, dict) and set(totals) == set(expected), 'score fields mismatch')
        for key, value in totals.items():
            require(isinstance(value, (int, float, Decimal)) and not isinstance(value, bool), 'score must be numeric')
            exact = Decimal(str(value))
            require(exact.is_finite() and exact == Decimal(str(expected[key])), 'score arithmetic mismatch: '+key)
        for outcome in record['outcomes'].values():
            for ref in outcome.get('evidence', []):
                if ref.startswith('pdf:'):
                    require(ref[4:].isdigit() and 1 <= int(ref[4:]) <= pages, 'invalid PDF page evidence')
                else:
                    path = ref.split('#',1)[0]
                    require(path in snapshots, 'evidence needs linked source snapshot')
                    if '#' in ref:
                        require(ref.split('#',1)[1] in (root/path).read_text(encoding='utf-8'), 'claim or passage evidence missing')
    return records

def verify_checkout(commit, root=ROOT, source_paths=()):
    """Bind an audit to committed inputs, including otherwise untracked files."""
    status = subprocess.check_output(
        ['git', 'status', '--porcelain', '--untracked-files=all'],
        cwd=root, text=True,
    )
    require(not status.strip(), 'audit requires a clean checkout (tracked and untracked files)')
    head = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=root, text=True,
    ).strip()
    require(commit == head, 'audit commit is not checkout HEAD')
    tracked = set(subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=root, text=True,
    ).split('\0'))
    require(all(path in tracked for path in source_paths), 'audit source snapshots must be tracked inputs')
    for path in source_paths:
        recorded = subprocess.check_output(
            ['git', 'rev-parse', f'{commit}:{path}'], cwd=root, text=True,
        ).strip()
        actual = subprocess.check_output(
            ['git', 'hash-object', f'--path={path}', '--', path], cwd=root, text=True,
        ).strip()
        # Git's clean conversion preserves legitimate Windows CRLF checkouts.
        require(actual == recorded, 'snapshot content differs from recorded commit: ' + path)



def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--pdf',type=Path,required=True,help='Exact inspected PDF')
    args=parser.parse_args()
    report=parse_report(args.report.read_text(encoding='utf-8'))
    records=validate(report)
    verify_checkout(report['commit'], source_paths=report['source_snapshots'])
    require(hashlib.sha256(args.pdf.read_bytes()).hexdigest() == report['pdf_sha256'], 'PDF digest mismatch')
    print(f'Validated {len(records)} entry records; arithmetic and references only, not factual or visual certification.')

if __name__ == '__main__':
    main()
