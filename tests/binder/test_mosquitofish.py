"""V8 coverage, animal safety boundaries and actual PDF proof."""
import copy,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import build_binder as builder
import binder_evidence as evidence
import binder_logs as logs

class MosquitofishTests(unittest.TestCase):
    def test_manifest_and_log_coverage(self):
        entries=builder.load_manifest(ROOT/'binder/manifest-v8.yaml')
        previous=builder.load_manifest(ROOT/'binder/manifest-v7.yaml')
        self.assertEqual(entries[:36],previous[:36])
        self.assertEqual(sum(x['page_budget'] for x in entries),45)
        species=logs.tracked_species(entries)
        self.assertEqual(len(species),13);self.assertEqual(species[-1],'mosquitofish')
        batches=logs.paginate_species(species)
        self.assertEqual([len(x) for x in batches],[3,3,3,3,1])
        self.assertEqual(logs.scientific_name('mosquitofish'),'Gambusia affinis')
        self.assertIn('Mosquitofish',logs.log_page_tex(batches[-1],5,5))
    def test_standalone_logs_use_latest_inventory(self):
        expected=logs.tracked_species(builder.load_manifest(ROOT/'binder/manifest-v8.yaml'))
        for name,blank in [('watering-log-tracked',False),('watering-log-blank',True)]:
            with mock.patch.object(builder,'compile_logs') as call:
                builder.compile_supplemental(name,'draft',Path('unused.pdf'))
            actual=logs.tracked_species(call.call_args.args[0])
            self.assertEqual(actual,expected)
            self.assertEqual(len(logs.paginate_species(actual)),5)
            self.assertEqual(call.call_args.kwargs['blank'],blank)

    def test_evidence_and_compile_contract(self):
        data=evidence.load_animal(ROOT,'mosquitofish')
        for kind in evidence.ANIMAL_PAGE_KINDS:
            with mock.patch.object(builder,'compile_entry') as call:
                builder.compile_animal('mosquitofish',kind,'draft',Path('unused.pdf'))
                call.assert_called_once()
            with self.assertRaises(ValueError):builder.compile_animal('mosquitofish',kind,'final',Path('unused.pdf'))
        for c in data['claims'].values():self.assertIn(c['life_stage'],{'all','adult','egg','juvenile'})
        bad=copy.deepcopy(next(iter(data['claims'].values())));bad['life_stage']='cutting'
        with self.assertRaises(ValueError):evidence.validate_claim(bad,data['sources'],animal=True)
        text=' '.join(c['description'] for c in data['claims'].values())
        for phrase in ['G. holbrooki','unseen specimen','chloramine','fishless','overflow','No release','retain sperm','Kuhli','not an official minimum']:
            self.assertIn(phrase.lower(),text.lower())
        catalog=json.loads((ROOT/'binder/entries/mosquitofish/assets.json').read_text())
        self.assertEqual(catalog['assets'][0]['kind'],'placeholder')
    def test_shrimp_milestones_regression(self):
        c=evidence.load_animal(ROOT,'cherry-shrimp')['claims']['cherry-shrimp#maturity-uncertainty']
        for text in ['25 +/- 1 C','ovarian','36.6','49','55.18','32 C','lost eggs']:
            self.assertIn(text,c['description'])
        page=(ROOT/'binder/entries/cherry-shrimp/reproduction.tex').read_text()
        self.assertNotIn('maturity around 30 days',page)
        self.assertEqual(page.count('\\Step{'),7)
        self.assertIn('Pause expansion/transfer',page)
    def test_manifest_rejects_duplicate_or_wrong_kind(self):
        original=json.loads((ROOT/'binder/manifest-v8.yaml').read_text())
        for mutate in [lambda d:d['entries'][36].update(kind='propagation'),lambda d:d['entries'].append(d['entries'][36]),lambda d:d['entries'][-2].update(page_budget=4)]:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);p=root/'binder/manifest-v8.yaml';p.parent.mkdir()
                data=copy.deepcopy(original);mutate(data);p.write_text(json.dumps(data))
                with mock.patch.object(builder,'ROOT',root),self.assertRaises(ValueError):builder.load_manifest(p)

@unittest.skipUnless(all(shutil.which(t) for t in ('lualatex','pdftotext','pdftoppm')),'LuaLaTeX and Poppler required')
class MosquitofishRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pypdf import PdfReader
        cls.directory=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.directory.cleanup)
        cls.base=Path(cls.directory.name);cls.pdf=cls.base/'v8.pdf'
        builder.compile_manifest(ROOT/'binder/manifest-v8.yaml','draft',cls.pdf)
        cls.reader=PdfReader(cls.pdf)
    def test_geometry_safe_bounds_links_and_logs(self):
        from test_binder import _assert_pdf_text_inside_safe_rectangle,_assert_essential_painted_content_inside_safe_rectangle
        self.assertEqual(len(self.reader.pages),45)
        self.assertEqual(len(_assert_pdf_text_inside_safe_rectangle(self.pdf,self.base/'bounds.html')),45)
        _assert_essential_painted_content_inside_safe_rectangle(self.reader.pages)
        for p in self.reader.pages:builder._validate_page(p,'v8')
        self.assertEqual(len(self.reader.pages[36].images),0)
        sources=evidence.load_animal(ROOT,'mosquitofish')['sources']
        urls={s['url'] for s in sources.values()}
        for p,k in zip(self.reader.pages[36:39],evidence.ANIMAL_PAGE_KINDS):
            self.assertIn('mosquitofish / '+k,p.extract_text())
            self.assertTrue({a.get_object()['/A']['/URI'] for a in p.get('/Annots',[])} <= urls)
        text=' '.join(p.extract_text() for p in self.reader.pages[39:44])
        for id in logs.tracked_species(builder.load_manifest(ROOT/'binder/manifest-v8.yaml')):
            self.assertIn(''.join(logs.LABELS[id].split()), ''.join(text.split()), id)
            self.assertIn(''.join(logs.scientific_name(id).split()), ''.join(text.split()), id)
        self.assertIn('BLANK EDITION',self.reader.pages[44].extract_text())
    def test_v7_species_and_blank_pixels_unchanged(self):
        from PIL import Image,ImageChops
        old=self.base/'v7.pdf';builder.compile_manifest(ROOT/'binder/manifest-v7.yaml','draft',old)
        for gray in (False,True):
            for label,pdf in [('old',old),('new',self.pdf)]:
                subprocess.run(['pdftoppm','-r','72','-png',*(['-gray'] if gray else []),str(pdf),str(self.base/(label+str(gray)))],check=True,capture_output=True,timeout=180)
            for before,after in [*((i,i) for i in range(1,37)),(41,45)]:
                with Image.open(self.base/f'old{gray}-{before:02d}.png') as a,Image.open(self.base/f'new{gray}-{after:02d}.png') as b:
                    self.assertIsNone(ImageChops.difference(a,b).getbbox(),(gray,before))
