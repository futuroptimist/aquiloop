"""Aquatic plant evidence, optional category styling, and printable v5 assembly."""
import json
from pathlib import Path
import re
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


class AquaticEvidenceTests(unittest.TestCase):
    def test_entries_resolve_evidence_links_and_honest_placeholders(self):
        for entry in builder.AQUATIC_PLANT_ENTRIES:
            with self.subTest(entry=entry):
                data = evidence.load_companions(ROOT, entry)
                self.assertGreaterEqual(len(data['claims']), 15)
                base, records, selected = builder.load_entry(entry, 'draft')
                self.assertEqual(set(selected), {'hero'})
                self.assertEqual(records[selected['hero']]['kind'], 'placeholder')
                self.assertFalse(list((base / 'assets').glob('*.jpg')))
                with self.assertRaises(ValueError):
                    builder.load_entry(entry, 'final')
                content = json.loads((base / 'content.yaml').read_text())
                self.assertEqual(len(content['cards']), 8)
                self.assertIn('Watering interval is N/A', content['environmental_variability'])
                urls = {v['url'] for v in data['sources'].values()}
                for name in ('page', 'numbers', 'propagation'):
                    tex = (base / (name + '.tex')).read_text()
                    links = re.findall(r'\\href\{([^{}]+)\}', tex)
                    self.assertTrue(links)
                    self.assertLessEqual(set(links), urls)
                    if name != 'page':
                        refs = re.findall(r'^% claim-ref: (\S+)$', tex, re.M)
                        self.assertTrue(refs)
                        self.assertLessEqual(set(refs), data['valid_refs'])
                self.assertEqual(data['claims'][entry+'#household-water']['evidence_category'], 'unknown')

    def test_glue_timing_is_product_scoped_not_a_growth_deadline(self):
        for entry in ('java-moss', 'anubias-nana'):
            data = evidence.load_companions(ROOT, entry)
            hold = data['claims'][entry+'#glue-hold']
            self.assertEqual(hold['quantity'], {'kind': 'value', 'value': 20, 'unit': 'seconds'})
            self.assertEqual(hold['provenance']['source_refs'], ['GLUE'])
            self.assertIn('Seachem', data['sources']['GLUE']['authority'])
            self.assertEqual(data['claims'][entry+'#establishment-time']['evidence_category'], 'unknown')
        self.assertNotIn('GLUE', evidence.load_companions(ROOT, 'guppy-grass')['sources'])

    def test_source_support_is_scoped_to_cards_and_canonical_claims(self):
        for entry in builder.AQUATIC_PLANT_ENTRIES:
            data = evidence.load_companions(ROOT, entry)
            sources = data['sources']
            for ref, claim in data['claims'].items():
                for key in claim['provenance'].get('source_refs', []):
                    self.assertIn(ref, sources[key]['supports'], (ref, key))
            for source in sources.values():
                self.assertNotIn('care', source['supports'])
                for ref in source['supports']:
                    if '#' in ref:
                        self.assertIn(ref, data['claims'])
                        self.assertIn(source['key'], data['claims'][ref]['provenance']['source_refs'])
            self.assertEqual(set(sources['DEC']['supports']), {
                'aquarium_compatibility_troubleshooting', entry+'#contain-discard'})
            if 'GLUE' in sources:
                expected = {entry+'#'+key for key in
                            ('glue-product','glue-hold','glue-contact','glue-safety')}
                if entry == 'java-moss':
                    expected.update({'placement_anchoring_floating', entry+'#placement'})
                self.assertEqual(set(sources['GLUE']['supports']), expected)

    def test_v5_order_log_last_and_category_separation(self):
        old = builder.load_manifest(ROOT/'binder/manifest-v4.yaml')
        new = builder.load_manifest(ROOT/'binder/manifest-v5.yaml')
        self.assertEqual(len(new), 31)
        self.assertEqual(new[:21], old[:21])
        self.assertEqual(new[-1], old[-1])
        self.assertEqual([(i['id'],i['kind']) for i in new[21:30]],
                         [(e,k) for e in ('guppy-grass','java-moss','anubias-nana')
                          for k in ('profile','numbers','propagation')])
        self.assertEqual(builder.CATEGORY_BY_ENTRY['pothos'], 'TERRESTRIAL PLANT')
        self.assertEqual(builder.CATEGORY_BY_ENTRY['aquarium-hornwort'], 'AQUATIC PLANT')
        self.assertEqual(builder.CATEGORY_BY_ENTRY['kuhli-loach'], 'AQUATIC ANIMAL')
        document = json.loads((ROOT/'binder/manifest-v5.yaml').read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'binder').mkdir()
            document['entries'].reverse()
            path=root/'binder/manifest-v5.yaml';path.write_text(json.dumps(document))
            with mock.patch.object(builder,'ROOT',root), self.assertRaises(ValueError):
                builder.load_manifest(path)


@unittest.skipUnless(all(shutil.which(t) for t in ('lualatex','pdftotext','pdftoppm')), 'LuaLaTeX and Poppler required')
class AquaticRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pypdf import PdfReader
        cls.directory=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.directory.cleanup)
        cls.base=Path(cls.directory.name);cls.pdf=cls.base/'aquatic.pdf'
        builder.compile_manifest(ROOT/'binder/manifest-v5.yaml','draft',cls.pdf)
        cls.reader=PdfReader(cls.pdf)

    def test_geometry_text_bounds_links_labels_and_no_invented_photos(self):
        from test_binder import (_assert_pdf_text_inside_safe_rectangle,
                                 _assert_essential_painted_content_inside_safe_rectangle)
        self.assertEqual(len(self.reader.pages),31)
        _assert_pdf_text_inside_safe_rectangle(self.pdf,self.base/'bounds.html')
        _assert_essential_painted_content_inside_safe_rectangle(self.reader.pages)
        for i,page in enumerate(self.reader.pages):
            builder._validate_page(page,str(i))
            text=page.extract_text()
            if i<12:self.assertIn('TERRESTRIAL PLANT',text)
            elif i<15 or 21<=i<30:self.assertIn('AQUATIC PLANT',text)
            elif i<21:self.assertIn('AQUATIC ANIMAL',text)
            else:self.assertIn('watering-log / supplemental',text)
        for i in (21,24,27):
            self.assertEqual(len(self.reader.pages[i].images),0)
            self.assertIn('DRAFT PLACEHOLDER',self.reader.pages[i].extract_text())
        for page in self.reader.pages[21:30]:
            self.assertTrue(page.get('/Annots'))

    def test_grayscale_white_margins_and_log_unchanged(self):
        from PIL import Image,ImageChops
        from pypdf import PdfReader
        old=self.base/'log.pdf'
        builder.compile_entry(builder.supplemental_path('watering-log'),{},{},old,kind='supplemental',expanded=True)
        self.assertEqual(self.reader.pages[-1].get_contents().get_data(),PdfReader(old).pages[0].get_contents().get_data())
        for gray in (False,True):
            prefix=self.base/('gray' if gray else 'color')
            subprocess.run(['pdftoppm','-r','72','-png',*(['-gray'] if gray else []),str(self.pdf),str(prefix)],check=True,capture_output=True,timeout=120)
            for i in range(1,32):
                with Image.open(self.base/f'{prefix.name}-{i:02d}.png') as im:
                    rgb=im.convert('RGB')
                    for box in ((0,0,60,792),(585,0,612,792),(0,0,612,25)):
                        self.assertIsNone(ImageChops.difference(rgb.crop(box),Image.new('RGB',(box[2]-box[0],box[3]-box[1]),'white')).getbbox())
