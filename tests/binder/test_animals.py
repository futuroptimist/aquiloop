"""Animal evidence and opt-in extension; plant baselines remain independent."""
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


class AnimalEvidenceTests(unittest.TestCase):
    def test_animal_claims_and_canonical_append_only_manifest(self):
        data = evidence.load_animal(ROOT, "kuhli-loach")
        self.assertEqual(len(data["claims"]), 26)
        entries = builder.load_manifest(ROOT / "binder/manifest-v3.yaml")
        self.assertEqual(len(entries), 19)
        self.assertEqual(entries[:16], builder.load_manifest(ROOT / "binder/manifest-v2.yaml"))
        self.assertEqual(tuple((i["id"], i["kind"]) for i in entries), builder.EXPECTED_ANIMAL_MANIFEST)

    def test_animal_evidence_rejects_plant_stages_and_invalid_ranges(self):
        data = evidence.load_animal(ROOT, "kuhli-loach")
        original = data["claims"]["kuhli-loach#trade-temperature"]
        for mutate in (lambda c: c.update(life_stage="cutting"),
                       lambda c: c["provenance"].update(source_refs=["missing"]),
                       lambda c: c["quantity"].update(minimum=81),
                       lambda c: c.pop("care_method")):
            claim = copy.deepcopy(original)
            mutate(claim)
            with self.assertRaises(ValueError):
                evidence.validate_claim(claim, data["sources"], animal=True)

    def test_manifest_rejects_reorder_or_plant_propagation_for_animal(self):
        original = json.loads((ROOT / "binder/manifest-v3.yaml").read_text())
        for mutate in (lambda d: d["entries"].reverse(),
                       lambda d: d["entries"][-1].update(kind="propagation"),
                       lambda d: d["entries"][-1].update(page_budget=2)):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / "binder/manifest-v3.yaml"
                path.parent.mkdir()
                document = copy.deepcopy(original)
                mutate(document)
                path.write_text(json.dumps(document))
                with mock.patch.object(builder, "ROOT", root), self.assertRaises(ValueError):
                    builder.load_manifest(path)

    def test_animal_layout_gate_and_no_final_or_traversal(self):
        for kind in evidence.ANIMAL_PAGE_KINDS:
            with mock.patch.object(builder, "compile_entry") as compile_page:
                builder.compile_animal("kuhli-loach", kind, "draft", Path("unused.pdf"))
                compile_page.assert_called_once()
        for entry, kind, mode in (("kuhli-loach", "animal-care", "final"),
                                  ("../kuhli-loach", "animal-care", "draft"),
                                  ("kuhli-loach", "propagation", "draft")):
            with self.assertRaises(ValueError):
                builder.compile_animal(entry, kind, mode, Path("unused.pdf"))

    def test_layout_rejects_unresolved_claim_link_and_unreviewed_image(self):
        original = Path.read_text
        path = ROOT / "binder/entries/kuhli-loach/animal-care.tex"
        text = path.read_text(encoding="utf-8")
        for extra in ("\n% claim-ref: kuhli-loach#missing\n",
                      r"\href{https://example.com/unreviewed}{unknown}",
                      r"\includegraphics{unreviewed.png}"):
            def altered(p, *args, **kwargs):
                return text + extra if p == path else original(p, *args, **kwargs)
            with mock.patch.object(Path, "read_text", altered), self.assertRaises(ValueError):
                builder.compile_animal("kuhli-loach", "animal-care", "draft", Path("unused.pdf"))


@unittest.skipUnless(all(shutil.which(t) for t in ("lualatex", "pdftotext", "pdftoppm")), "LuaLaTeX and Poppler required")
class AnimalRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pypdf import PdfReader
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.base = Path(cls.directory.name)
        cls.pdf = cls.base / "animals.pdf"
        builder.compile_manifest(ROOT / "binder/manifest-v3.yaml", "draft", cls.pdf)
        cls.reader = PdfReader(cls.pdf)

    def test_nineteen_pages_identity_geometry_and_live_source_links(self):
        self.assertEqual(len(self.reader.pages), 19)
        sources = evidence.load_animal(ROOT, "kuhli-loach")["sources"]
        urls = {s["url"] for s in sources.values()}
        for page, kind in zip(self.reader.pages[16:], evidence.ANIMAL_PAGE_KINDS):
            builder._validate_page(page, kind)
            self.assertIn("kuhli-loach / " + kind, page.extract_text())
            links = [a.get_object()["/A"]["/URI"] for a in page.get("/Annots", [])]
            self.assertTrue(links)
            self.assertTrue(set(links) <= urls)

    def test_all_text_and_paint_stay_inside_safe_rectangle(self):
        from test_binder import (_assert_pdf_text_inside_safe_rectangle,
                                 _assert_essential_painted_content_inside_safe_rectangle)
        self.assertEqual(len(_assert_pdf_text_inside_safe_rectangle(self.pdf, self.base / "bounds.html")), 19)
        _assert_essential_painted_content_inside_safe_rectangle(self.reader.pages[16:])

    def test_first_sixteen_pages_are_pixel_identical_in_both_modes(self):
        from PIL import Image, ImageChops
        original = self.base / "original.pdf"
        builder.compile_manifest(ROOT / "binder/manifest-v2.yaml", "draft", original)
        for gray in (False, True):
            for label, pdf in (("old", original), ("new", self.pdf)):
                prefix = self.base / (label + str(gray))
                subprocess.run(["pdftoppm", "-r", "72", "-f", "1", "-l", "16", "-png",
                                *(["-gray"] if gray else []), str(pdf), str(prefix)],
                               check=True, capture_output=True, timeout=120)
            for i in range(1, 17):
                with Image.open(self.base / f"old{gray}-{i:02d}.png") as a, Image.open(self.base / f"new{gray}-{i:02d}.png") as b:
                    self.assertIsNone(ImageChops.difference(a, b).getbbox(), (gray, i))

    def test_animal_overflow_fails_its_own_page_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "binder", root / "binder")
            page = root / "binder/entries/kuhli-loach/animal-care.tex"
            page.write_text(page.read_text(encoding="utf-8") + r"\newpage Extra page must be rejected.", encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root), self.assertRaisesRegex(RuntimeError, "rendered 2 pages"):
                builder.compile_animal("kuhli-loach", "animal-care", "draft", root / "overflow.pdf")
