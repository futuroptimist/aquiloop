"""V9 terrestrial animal coverage and preservation of the merged v8 edition."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_binder as builder
import binder_evidence as evidence
import binder_logs as logs
import binder_audit as audit
from test_audit import AuditTests

class WormTests(unittest.TestCase):
    def test_versioned_assembly_and_log_identity(self):
        old = builder.load_manifest(ROOT / 'binder/manifest-v8.yaml')
        new = builder.load_manifest(ROOT / 'binder/manifest-v9.yaml')
        self.assertEqual(new[:39], old[:39])
        self.assertEqual(new[-2:], old[-2:])
        self.assertEqual(sum(x['page_budget'] for x in new), 48)
        species = logs.tracked_species(new)
        self.assertEqual(len(species), 14)
        self.assertEqual(species[-1], 'eisenia-fetida')
        self.assertEqual(logs.scientific_name(species[-1]), 'Eisenia fetida')
        last = logs.log_page_tex(logs.paginate_species(species)[-1], 5, 5)
        self.assertIn('Red wiggler', last)
        self.assertIn('condition-based moisture', last)
        self.assertIn('animal care event', last)

    def test_claims_no_observations_and_draft_photo_boundary(self):
        data = evidence.load_animal(ROOT, 'eisenia-fetida')
        self.assertTrue(all(c['evidence_category'] in {'proposed','published'} for c in data['claims'].values()))
        text = ' '.join(c['description'] for c in data['claims'].values())
        for phrase in ['not aquarium stocking', 'unmeasured', 'per week', 'not a daily ration', 'leachate', 'live-feed safety', 'self-fertilization', 'hybrids', 'No fixed doubling', 'origin/destination', 'not a California']:
            self.assertIn(phrase.lower(), text.lower())
        for kind in evidence.ANIMAL_PAGE_KINDS:
            with mock.patch.object(builder,'compile_entry') as call:
                builder.compile_animal('eisenia-fetida',kind,'draft',Path('unused.pdf'))
                call.assert_called_once()
            with self.assertRaises(ValueError):
                builder.compile_animal('eisenia-fetida',kind,'final',Path('unused.pdf'))
        _, catalog, selected = builder.load_entry('eisenia-fetida','draft',layout_name='animal-care.tex')
        self.assertEqual(catalog[selected['hero']]['kind'], 'placeholder')

    def test_v9_audit_uses_same_scoring_and_exact_inventory(self):
        report = AuditTests().report()
        report['manifest'] = 'binder/manifest-v9.yaml'
        report['source_snapshots'][report['manifest']] = hashlib.sha256((ROOT/report['manifest']).read_bytes()).hexdigest()
        extra = copy.deepcopy(report['entries'][-1])
        extra.update(id='eisenia-fetida',pages=[40,41,42])
        report['entries'].append(extra)
        for e in report['entries']:
            e['manifest'] = report['manifest']
        self.assertEqual(len(audit.validate(report)),14)
        report['entries'].pop()
        with self.assertRaises(ValueError):
            audit.validate(report)

@unittest.skipUnless(all(shutil.which(t) for t in ('lualatex','pdftotext','pdftoppm')), 'LuaLaTeX and Poppler required')
class WormRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pypdf import PdfReader
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.base = Path(cls.directory.name)
        cls.pdf = cls.base/'v9.pdf'
        builder.compile_manifest(ROOT/'binder/manifest-v9.yaml','draft',cls.pdf)
        cls.reader = PdfReader(cls.pdf)

    def test_actual_pdf_geometry_warnings_links_and_records(self):
        from test_binder import _assert_pdf_text_inside_safe_rectangle, _assert_essential_painted_content_inside_safe_rectangle
        self.assertEqual(len(self.reader.pages),48)
        self.assertEqual(len(_assert_pdf_text_inside_safe_rectangle(self.pdf,self.base/'bounds.html')),48)
        _assert_essential_painted_content_inside_safe_rectangle(self.reader.pages)
        urls={s['url'] for s in evidence.load_animal(ROOT,'eisenia-fetida')['sources'].values()}
        for p,k in zip(self.reader.pages[39:42], evidence.ANIMAL_PAGE_KINDS):
            builder._validate_page(p,'v9')
            self.assertIn('eisenia-fetida / '+k,p.extract_text())
            self.assertTrue({a.get_object()['/A']['/URI'] for a in p.get('/Annots',[])} <= urls)
        self.assertEqual(len(self.reader.pages[39].images),0)
        self.assertIn('live-feed safety',self.reader.pages[39].extract_text())
        self.assertIn('not California law',self.reader.pages[41].extract_text())
        self.assertIn('Red wiggler',self.reader.pages[46].extract_text())
        self.assertIn('Eisenia fetida',self.reader.pages[46].extract_text())
        self.assertIn('BLANK EDITION',self.reader.pages[47].extract_text())

    def test_preserves_all_previous_species_and_unaffected_logs(self):
        from PIL import Image,ImageChops
        old=self.base/'v8.pdf'
        builder.compile_manifest(ROOT/'binder/manifest-v8.yaml','draft',old)
        for gray in (False,True):
            for label,pdf in [('old',old),('new',self.pdf)]:
                subprocess.run(['pdftoppm','-r','72','-png',*(['-gray'] if gray else []),str(pdf),str(self.base/(label+str(gray)))],check=True,capture_output=True,timeout=180)
            for before,after in [*((i,i) for i in range(1,40)),*((i,i+3) for i in range(40,44)),(45,48)]:
                with Image.open(self.base/f'old{gray}-{before:02d}.png') as a, Image.open(self.base/f'new{gray}-{after:02d}.png') as b:
                    self.assertIsNone(ImageChops.difference(a,b).getbbox(),(gray,before,after))
