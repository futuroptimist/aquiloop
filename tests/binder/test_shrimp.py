"""Cherry shrimp extends the accepted nineteen-page binder without altering it."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_binder as builder
import binder_evidence as evidence


class ShrimpEvidenceTests(unittest.TestCase):
    def test_claims_and_append_only_manifest(self):
        data = evidence.load_animal(ROOT, "cherry-shrimp")
        self.assertEqual(len(data["claims"]), 30)
        entries = builder.load_manifest(ROOT / "binder/manifest-v4.yaml")
        self.assertEqual(len(entries), 22)
        self.assertEqual(entries[:19], builder.load_manifest(ROOT / "binder/manifest-v3.yaml"))
        self.assertEqual(tuple((i["id"], i["kind"]) for i in entries), builder.EXPECTED_SHRIMP_MANIFEST)
        for kind in evidence.ANIMAL_PAGE_KINDS:
            with mock.patch.object(builder, "compile_entry") as compile_page:
                builder.compile_animal("cherry-shrimp", kind, "draft", Path("unused.pdf"))
                compile_page.assert_called_once()

    def test_manifest_rejects_reordering_or_wrong_page_kind(self):
        original = json.loads((ROOT / "binder/manifest-v4.yaml").read_text())
        for mutate in (lambda d: d["entries"].reverse(),
                       lambda d: d["entries"][-1].update(kind="propagation"),
                       lambda d: d["entries"][-1].update(page_budget=2)):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / "binder/manifest-v4.yaml"
                path.parent.mkdir()
                document = copy.deepcopy(original)
                mutate(document)
                path.write_text(json.dumps(document))
                with mock.patch.object(builder, "ROOT", root), self.assertRaises(ValueError):
                    builder.load_manifest(path)

    def test_overlap_is_a_derivation_and_nursery_is_unknown(self):
        claims = evidence.load_animal(ROOT, "cherry-shrimp")["claims"]
        overlap = claims["cherry-shrimp#possible-temperature-overlap"]
        self.assertEqual(overlap["evidence_category"], "proposed")
        self.assertTrue(overlap["provenance"]["derivation"])
        self.assertEqual((overlap["quantity"]["minimum"], overlap["quantity"]["maximum"]),
                         (max(72, 74), min(76, 80)))
        for id in ("current-water", "nursery-cycle-status", "transfer-size", "individual-lifespan"):
            self.assertEqual(claims["cherry-shrimp#" + id]["quantity"]["kind"], "unknown")
        self.assertEqual(claims["cherry-shrimp#incubation-disagreement"]["life_stage"], "egg")
        self.assertEqual(claims["cherry-shrimp#newborn-size"]["life_stage"], "juvenile")


@unittest.skipUnless(all(shutil.which(t) for t in ("lualatex", "pdftotext", "pdftoppm")), "LuaLaTeX and Poppler required")
class ShrimpRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pypdf import PdfReader
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.base = Path(cls.directory.name)
        cls.pdf = cls.base / "shrimp.pdf"
        builder.compile_manifest(ROOT / "binder/manifest-v4.yaml", "draft", cls.pdf)
        cls.reader = PdfReader(cls.pdf)

    def test_geometry_links_and_safe_bounds(self):
        from test_binder import (_assert_pdf_text_inside_safe_rectangle,
                                 _assert_essential_painted_content_inside_safe_rectangle)
        self.assertEqual(len(self.reader.pages), 22)
        self.assertEqual(len(_assert_pdf_text_inside_safe_rectangle(self.pdf, self.base / "bounds.html")), 22)
        _assert_essential_painted_content_inside_safe_rectangle(self.reader.pages[19:])
        sources = evidence.load_animal(ROOT, "cherry-shrimp")["sources"]
        urls = {s["url"] for s in sources.values()}
        for page, kind in zip(self.reader.pages[19:], evidence.ANIMAL_PAGE_KINDS):
            builder._validate_page(page, kind)
            self.assertIn("cherry-shrimp / " + kind, page.extract_text())
            links = [a.get_object()["/A"]["/URI"] for a in page.get("/Annots", [])]
            self.assertTrue(links)
            self.assertTrue(set(links) <= urls)

    def test_first_nineteen_pages_unchanged_in_both_modes(self):
        from PIL import Image, ImageChops
        original = self.base / "original.pdf"
        builder.compile_manifest(ROOT / "binder/manifest-v3.yaml", "draft", original)
        for gray in (False, True):
            for label, pdf in (("old", original), ("new", self.pdf)):
                prefix = self.base / (label + str(gray))
                subprocess.run(["pdftoppm", "-r", "72", "-f", "1", "-l", "19", "-png",
                                *(["-gray"] if gray else []), str(pdf), str(prefix)],
                               check=True, capture_output=True, timeout=120)
            for i in range(1, 20):
                with Image.open(self.base / f"old{gray}-{i:02d}.png") as a, Image.open(self.base / f"new{gray}-{i:02d}.png") as b:
                    self.assertIsNone(ImageChops.difference(a, b).getbbox(), (gray, i))
