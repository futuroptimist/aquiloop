"""Two photographed terrestrial entries: evidence, privacy, assembly and print proof."""
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_binder as builder
import binder_evidence as evidence
import binder_logs as logs

NEW = ("pachyveria-powder-puff", "crassula-rupestris")


class SucculentTests(unittest.TestCase):
    def test_complete_entries_and_scoped_evidence(self):
        from test_content import TERRESTRIAL, PROPAGATION_FIELDS
        for entry in NEW:
            with self.subTest(entry=entry):
                base = ROOT / "binder/entries" / entry
                data = evidence.load_companions(ROOT, entry)
                content = json.loads((base / "content.yaml").read_text())
                self.assertEqual(content["entry"], entry)
                self.assertEqual(content["identity"]["status"], "provisional")
                self.assertEqual(set(content["cards"]), TERRESTRIAL)
                self.assertTrue(content["unresolved_fields"])
                for cards in content["cards"].values():
                    for card in cards:
                        self.assertTrue(card["claim"])
                        self.assertTrue(set(card["sources"]) <= data["sources"].keys())
                self.assertTrue(PROPAGATION_FIELDS <= content["cards"]["propagation"][0].keys())
                for kind in ("numbers", "propagation"):
                    page = (base / f"{kind}.tex").read_text()
                    refs = re.findall(r"^% claim-ref: (\S+)$", page, re.M)
                    self.assertTrue(refs)
                    self.assertTrue(set(refs) <= data["valid_refs"])
                    self.assertIn(entry + " / " + kind, page)
                    self.assertEqual(page.count(r"\CardRow{") if kind == "numbers" else page.count(r"\Step{"),
                                     4 if kind == "numbers" else 8)
                self.assertEqual(data["claims"][entry + "#root-initiation"]["evidence_category"], "unknown")
                self.assertEqual(data["claims"][entry + "#established-recipe"]["evidence_category"], "proposed")
                self.assertIn("UK minimum", data["claims"][entry + "#cold-category"]["quantity"]["unit"])

    def test_square_images_under_decimal_ceiling_and_metadata_free(self):
        for entry in NEW:
            base, records, selected = builder.load_entry(entry, "draft")
            self.assertEqual(set(selected), {"hero"})
            record = records[selected["hero"]]
            path = base / record["path"]
            self.assertLess(path.stat().st_size, 100000)
            self.assertEqual(path.stat().st_size, record["preparation"]["bytes"])
            self.assertTrue(record["source"]["rights_reviewed"])
            with Image.open(path) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.size, (954, 954))
                self.assertGreaterEqual(image.width, 792)
                self.assertEqual(len(image.getexif()), 0)
                self.assertEqual([marker for marker, _ in image.applist], ["APP0"])
                self.assertFalse(set(image.info) & {"exif", "xmp", "photoshop", "comment", "icc_profile", "mp"})
            with self.assertRaisesRegex(ValueError, "provisional"):
                builder.load_entry(entry, "final")

    def test_builder_rejects_exact_ceiling_nonsquare_and_private_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = NEW[0]
            base = root / "binder/entries" / entry
            shutil.copytree(ROOT / "binder/entries" / entry, base)
            photo = base / "assets/overview.jpg"
            original = photo.read_bytes()
            with mock.patch.object(builder, "ROOT", root):
                photo.write_bytes(original + b"\0" * (100000-len(original)))
                with self.assertRaisesRegex(ValueError, "strictly under"):
                    builder.load_entry(entry, "draft")
                Image.new("RGB", (954, 953), "white").save(photo, "JPEG")
                with self.assertRaisesRegex(ValueError, "square"):
                    builder.load_entry(entry, "draft")
                for marker in (b"\xff\xfe", b"\xff\xe1", b"\xff\xed"):
                    # JPEG COM, APP1 (EXIF/XMP), APP13 (IPTC/Photoshop).
                    photo.write_bytes(original[:2] + marker + b"\x00\x06test" + original[2:])
                    with self.assertRaisesRegex(ValueError, "metadata"):
                        builder.load_entry(entry, "draft")

    def test_canonical_order_all_twelve_species_and_final_blank(self):
        entries = builder.load_manifest(ROOT / "binder/manifest-v7.yaml")
        old = builder.load_manifest(ROOT / "binder/manifest-v6.yaml")
        self.assertEqual(entries[:30], old[:30])
        self.assertEqual([(x["id"], x["kind"]) for x in entries[30:36]],
                         [(e, k) for e in NEW for k in ("profile", "numbers", "propagation")])
        self.assertEqual(entries[-2:], old[-2:])
        self.assertEqual(sum(x["page_budget"] for x in entries), 41)
        species = logs.tracked_species(entries)
        self.assertEqual(species, logs.tracked_species(old) + list(NEW))
        self.assertEqual(len(species), 12)
        self.assertEqual(set(species), set(logs.LABELS))
        batches = logs.paginate_species(species)
        self.assertEqual([len(x) for x in batches], [3, 3, 3, 3])
        rendered = "".join(logs.log_page_tex(batch, i, 4) for i, batch in enumerate(batches, 1))
        for entry in species:
            self.assertEqual(rendered.count(r"\NameCell{" + logs.LABELS[entry] + "}"), 1)

    def test_bad_page_order_missing_species_and_wrong_log_budget_fail(self):
        original = json.loads((ROOT / "binder/manifest-v7.yaml").read_text())
        for mutate in (lambda e: e.reverse(), lambda e: e.pop(31),
                       lambda e: e.insert(32, e[31]), lambda e: e[-2].update(page_budget=3)):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / "binder/manifest-v7.yaml"
                path.parent.mkdir()
                doc = copy.deepcopy(original)
                mutate(doc["entries"])
                path.write_text(json.dumps(doc))
                with mock.patch.object(builder, "ROOT", root), self.assertRaises(ValueError):
                    builder.load_manifest(path)


@unittest.skipUnless(all(shutil.which(t) for t in ("lualatex", "pdftotext", "pdftoppm")),
                     "LuaLaTeX and Poppler required")
class SucculentRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pypdf import PdfReader
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.base = Path(cls.directory.name)
        cls.pdf = cls.base / "succulents.pdf"
        builder.compile_manifest(ROOT / "binder/manifest-v7.yaml", "draft", cls.pdf)
        cls.reader = PdfReader(cls.pdf)

    def test_pages_images_coverage_and_print_bounds(self):
        from test_binder import (_assert_pdf_text_inside_safe_rectangle,
                                 _assert_essential_painted_content_inside_safe_rectangle)
        self.assertEqual(len(self.reader.pages), 41)
        _assert_pdf_text_inside_safe_rectangle(self.pdf, self.base / "bounds.html")
        _assert_essential_painted_content_inside_safe_rectangle(self.reader.pages)
        for i, entry in enumerate(NEW):
            pages = self.reader.pages[30+i*3:33+i*3]
            self.assertEqual(len(pages[0].images), 1)
            self.assertEqual(pages[0].images[0].image.size, (954, 954))
            for page, kind in zip(pages, ("OVERVIEW", "NUMBERS & PACIFICA", "PROPAGATION")):
                builder._validate_page(page, entry)
                self.assertIn(kind, page.extract_text())
                self.assertIn("TERRESTRIAL PLANT", page.extract_text())
                sizes = []
                page.extract_text(visitor_text=lambda text, cm, tm, font, size:
                                  sizes.append(size) if text.strip() else None)
                self.assertGreaterEqual(min(sizes), 7.9)
        text = "".join(p.extract_text() for p in self.reader.pages[36:40]).replace("\u2019", "'")
        for label in logs.LABELS.values():
            self.assertEqual(text.count(label), 1)
        self.assertIn("BLANK EDITION", self.reader.pages[-1].extract_text())

    def test_white_margins_in_color_and_grayscale(self):
        from PIL import ImageChops
        for gray in (False, True):
            prefix = self.base / ("gray" if gray else "color")
            subprocess.run(["pdftoppm", "-f", "31", "-l", "41", "-r", "72", "-png",
                            *(["-gray"] if gray else []), str(self.pdf), str(prefix)],
                           check=True, capture_output=True, timeout=120)
            for path in self.base.glob(prefix.name + "-*.png"):
                with Image.open(path) as source:
                    image = source.convert("RGB")
                    for box in ((0, 0, 60, 792), (585, 0, 612, 792), (0, 0, 612, 25)):
                        self.assertIsNone(ImageChops.difference(image.crop(box),
                            Image.new("RGB", (box[2]-box[0], box[3]-box[1]), "white")).getbbox())


if __name__ == "__main__":
    unittest.main()
