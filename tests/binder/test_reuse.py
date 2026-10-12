"""Reuse contract; all pre-existing regression tests remain cold."""
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import binder_reuse as reuse
import build_binder as builder
import render_binder_proofs as proofs
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.environment = mock.patch.dict(os.environ, {
            'GITHUB_ACTIONS':'true', 'GITHUB_REPOSITORY':'test/repo', 'GITHUB_RUN_ID':'1',
            'GITHUB_RUN_ATTEMPT':'1', 'GITHUB_JOB':'build', 'RUNNER_TEMP':str(self.root)})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.path = reuse.initialize()
        self.session = reuse.Session(self.path)

    def test_exact_key_payload_integrity_and_external_dependencies(self):
        source = self.root / 'result'; source.write_bytes(b'validated PDF')
        dependency = self.root / 'external.tex'; dependency.write_text('one')
        key = self.session.key('compile', {'source':'one','option':'draft'})
        self.session.save('compile', key, source, [dependency])
        target = self.root / 'copy'
        self.assertTrue(self.session.restore('compile', key, target))
        self.assertEqual(target.read_bytes(), source.read_bytes())
        self.assertFalse(self.session.restore('compile', self.session.key('compile', {'source':'two'}), target))
        stat = dependency.stat(); dependency.write_text('two'); os.utime(dependency, ns=(stat.st_atime_ns,stat.st_mtime_ns))
        self.assertFalse(self.session.restore('compile', key, target))
        dependency.write_text('one')
        (self.session.root/'compile'/key/'payload').write_bytes(b'corrupt')
        self.assertFalse(self.session.restore('compile', key, target))

    def test_each_source_asset_option_generated_input_and_toolchain_invalidates(self):
        for folder in ('binder/entries/example/assets', 'scripts', 'staged'):
            (self.root/folder).mkdir(parents=True)
        names = ['binder/template.tex','binder/entries/example/assets/photo.jpg',
                 'binder/entries/example/assets.json','binder/entries/example/sources.yaml',
                 'binder/manifest-v9.yaml','scripts/build_binder.py','requirements-binder.txt',
                 'staged/template.tex','staged/page.tex','staged/resolved-assets.tex']
        for name in names:(self.root/name).write_text('one')
        options = dict(base=str(self.root/'binder/entries/example'), kind='profile',
                       expanded=True, category='TERRESTRIAL PLANT', page_text_override=None)
        with mock.patch.object(self.session,'toolchain',return_value={'binary':'one','font':'one','package':'one','environment':'one'}) as toolchain:
            def key():return reuse.compile_key(self.session,self.root,self.root/'staged',{'asset':'one'},{'hero':'one'},options)
            original=key()
            self.assertEqual(key(),original)
            for name in names:
                path=self.root/name;stat=path.stat();path.write_text('two');os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
                self.assertNotEqual(key(),original,name);path.write_text('one')
            for name in options:
                if name=='base':continue
                previous=options[name];options[name]='different'
                self.assertNotEqual(key(),original,name);options[name]=previous
            for name in toolchain.return_value:
                toolchain.return_value[name]='two';self.assertNotEqual(key(),original,name);toolchain.return_value[name]='one'
            self.assertNotEqual(reuse.compile_key(self.session,self.root,self.root/'staged',{'asset':'two'},{'hero':'one'},options),original)
            self.assertNotEqual(reuse.compile_key(self.session,self.root,self.root/'staged',{'asset':'one'},{'hero':'two'},options),original)

    def test_fresh_sessions_and_owner_changes_never_reuse_old_job(self):
        second = reuse.Session(reuse.initialize())
        self.assertNotEqual(self.session.root,second.root)
        source = self.root / 'result'; source.write_bytes(b'validated')
        key = self.session.key('compile', {'source': 'one'})
        self.session.save('compile', key, source)
        self.assertFalse(second.restore('compile', key, self.root / 'copy'))
        for name in reuse.OWNER_KEYS:
            with mock.patch.dict(os.environ,{name:'another'}),self.assertRaises(ValueError):
                reuse.Session(self.path)
        with mock.patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}),self.assertRaises(ValueError):reuse.initialize()

    def test_default_cold_and_context_cleanup(self):
        with mock.patch.dict(os.environ,{'BINDER_REUSE_SESSION':str(self.path)}):
            self.assertIsNone(reuse.ACTIVE.get())
            with reuse.activate(self.path):self.assertIsNotNone(reuse.ACTIVE.get())
            self.assertIsNone(reuse.ACTIVE.get())
            with reuse.activate(None):self.assertIsNone(reuse.ACTIVE.get())
        workflow=(ROOT/'.github/workflows/binder.yml').read_text(encoding='utf8')
        start=workflow.index('      - name: Start disposable job-local reuse after cold tests')
        self.assertGreater(start,workflow.index('      - name: Run complete binder regression suite'))
        self.assertNotIn('--reuse-session',workflow[:start])
        self.assertNotIn('actions/cache',workflow)

    def test_snapshot_new_files_and_symlinks_are_content_keys(self):
        folder=self.root/'inputs';folder.mkdir();(folder/'one').write_text('one')
        before=self.session.snapshot([folder]);(folder/'two').write_text('two')
        self.assertNotEqual(self.session.snapshot([folder]),before)

    def test_page_normalization_preserves_distinct_resources_and_geometry(self):
        writer=PdfWriter();writer.add_blank_page(612,792);writer.add_blank_page(612,792)
        buffer=io.BytesIO();writer.write(buffer);reader=PdfReader(buffer)
        self.assertEqual(proofs.page_bytes(reader.pages[0]),proofs.page_bytes(reader.pages[1]))
        reader.pages[1].cropbox.upper_right=(600,790)
        self.assertNotEqual(proofs.page_bytes(reader.pages[0]),proofs.page_bytes(reader.pages[1]))

    def test_raster_options_inputs_corruption_and_catalog_fallback(self):
        pdf=self.root/'input.pdf';writer=PdfWriter();writer.add_blank_page(612,792)
        with pdf.open('wb') as stream:writer.write(stream)
        from PIL import Image
        def render(command,**kwargs):Image.new('RGB',(10,10),'white').save(str(command[-1])+'-1.png')
        with mock.patch.object(self.session,'toolchain',return_value={'version':'one'}),mock.patch.object(proofs.subprocess,'run',side_effect=render) as run:
            proofs.render(pdf,self.root/'cold',session=self.session)
            proofs.render(pdf,self.root/'warm',session=self.session)
            self.assertEqual(run.call_count,1)
            self.assertEqual((self.root/'cold-1.png').read_bytes(),(self.root/'warm-1.png').read_bytes())
            proofs.render(pdf,self.root/'gray',gray=True,session=self.session)
            proofs.render(pdf,self.root/'dpi',dpi=72,session=self.session)
            self.assertEqual(run.call_count,3)
            writer.root_object[NameObject('/Lang')]=TextStringObject('en')
            with pdf.open('wb') as stream:writer.write(stream)
            proofs.render(pdf,self.root/'unsupported',session=self.session)
            proofs.render(pdf,self.root/'unsupported2',session=self.session)
            self.assertEqual(run.call_count,5)


@unittest.skipUnless(all(shutil.which(t) for t in ('lualatex','pdftoppm','ldd','kpsewhich')), 'Linux TeX/Poppler toolchain required')
class ActualReuseTests(unittest.TestCase):
    setUp = ReuseTests.setUp
    def test_actual_compile_and_raster_match_cold_results(self):
        cold=self.root/'cold.pdf';warm=self.root/'warm.pdf';hit=self.root/'hit.pdf'
        builder.compile_animal('eisenia-fetida','tank-setup','draft',cold)
        with reuse.activate(self.path):
            builder.compile_animal('eisenia-fetida','tank-setup','draft',warm)
            with mock.patch.object(builder.subprocess,'run', wraps=builder.subprocess.run) as calls:
                builder.compile_animal('eisenia-fetida','tank-setup','draft',hit)
                self.assertFalse(any(c.args[0][0]=='lualatex' for c in calls.call_args_list))
        self.assertEqual(cold.read_bytes(),warm.read_bytes());self.assertEqual(cold.read_bytes(),hit.read_bytes())
        proofs.render(cold,self.root/'original')
        # Standalone TeX PDFs have catalog context; use the production assembly form.
        writer=PdfWriter();writer.add_page(PdfReader(cold).pages[0])
        assembled=self.root/'assembled.pdf'
        with assembled.open('wb') as stream:writer.write(stream)
        proofs.render(assembled,self.root/'baseline')
        with mock.patch.object(self.session,'toolchain',return_value=self.session.toolchain()):
            proofs.render(assembled,self.root/'first',session=self.session)
            with mock.patch.object(proofs.subprocess,'run',side_effect=AssertionError('warm raster should not execute')):
                proofs.render(assembled,self.root/'second',session=self.session)
            # A common page at a different index in another assembly must reuse
            # exactly the same pixels as cold rendering of that assembly.
            writer = PdfWriter(); writer.add_blank_page(612,792)
            writer.add_page(PdfReader(cold).pages[0])
            later = self.root / 'later.pdf'
            with later.open('wb') as stream: writer.write(stream)
            proofs.render(later,self.root/'later-cold',first=2,last=2)
            with mock.patch.object(proofs.subprocess,'run',side_effect=AssertionError('common page should reuse')):
                proofs.render(later,self.root/'later-hit',first=2,last=2,session=self.session)
            self.assertEqual((self.root/'later-cold-2.png').read_bytes(),(self.root/'later-hit-2.png').read_bytes())
        self.assertEqual((self.root/'baseline-1.png').read_bytes(),(self.root/'first-1.png').read_bytes())
        self.assertEqual((self.root/'first-1.png').read_bytes(),(self.root/'second-1.png').read_bytes())
