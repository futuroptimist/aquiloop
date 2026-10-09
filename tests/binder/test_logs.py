"""Coverage, ordering and physical print geometry for the reusable log edition."""
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
import binder_logs as logs


class LogTests(unittest.TestCase):
    def test_every_tracked_entry_once_in_manifest_order(self):
        entries = builder.load_manifest(ROOT / "binder/manifest-v6.yaml")
        expected = ["sedum-loves-fire", "kalanchoe-desert", "pothos",
                    "bird-of-paradise", "aquarium-hornwort", "kuhli-loach",
                    "cherry-shrimp", "guppy-grass", "java-moss", "anubias-nana"]
        self.assertEqual(logs.tracked_species(entries), expected)
        batches = logs.paginate_species(logs.tracked_species(entries))
        self.assertEqual([len(page) for page in batches], [3, 3, 3, 1])
        self.assertEqual([entry for page in batches for entry in page], expected)
        self.assertEqual(set(expected), set(logs.LABELS))

    def test_pagination_never_truncates_or_duplicates(self):
        for count in (0, 1, 3, 4, 10, 11, 30, 31):
            with self.subTest(count=count):
                entries = [f"species-{i}" for i in range(count)]
                batches = logs.paginate_species(entries)
                self.assertEqual([item for batch in batches for item in batch], entries)
                self.assertTrue(all(1 <= len(batch) <= 3 for batch in batches))
                self.assertEqual(len(batches), (count + 2) // 3)

    def test_blank_names_and_unselected_preferences(self):
        tex = logs.log_page_tex([], 1, 1, blank=True)
        self.assertEqual(tex.count(r"\NameCell{}"), 3)
        for label in logs.LABELS.values():
            self.assertNotIn(label, tex)
        for field in ("Watering frequency", "Check / trigger", "Amount / method",
                      "Propagation / breeding", "Light / location"):
            self.assertIn(field, tex)
        self.assertIn("not universal care instructions", tex)
        self.assertNotIn(r"\checkmark", tex)
        with self.assertRaises(ValueError):
            logs.log_page_tex(["pothos"], 1, 1, blank=True)

    def test_blank_is_after_all_named_logs_and_unrelated_pages_unchanged(self):
        old = builder.load_manifest(ROOT / "binder/manifest-v5.yaml")
        new = builder.load_manifest(ROOT / "binder/manifest-v6.yaml")
        self.assertEqual(new[:-2], old[:-1])
        self.assertEqual(new[-2:], [
            {"id": "watering-log-tracked", "kind": "supplemental", "page_budget": 4},
            {"id": "watering-log-blank", "kind": "supplemental", "page_budget": 1}])
        self.assertEqual(sum(item["page_budget"] for item in new), 35)
        document = {"schema_version": 6, "entries": new}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "binder").mkdir()
            path = root / "binder/manifest-v6.yaml"
            for change in ("swap", "budget"):
                altered = json.loads(json.dumps(document))
                if change == "swap":
                    altered["entries"][-2:] = reversed(altered["entries"][-2:])
                else:
                    altered["entries"][-2]["page_budget"] = 1
                path.write_text(json.dumps(altered))
                with mock.patch.object(builder, "ROOT", root), self.assertRaises(ValueError):
                    builder.load_manifest(path)


@unittest.skipUnless(all(shutil.which(t) for t in ("lualatex", "pdftotext", "pdftoppm")),
                     "LuaLaTeX and Poppler required")
class LogRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pypdf import PdfReader
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.base = Path(cls.directory.name)
        cls.pdf = cls.base / "binder.pdf"
        builder.compile_manifest(ROOT / "binder/manifest-v6.yaml", "draft", cls.pdf)
        cls.reader = PdfReader(cls.pdf)

    def test_coverage_order_and_blank_names_in_actual_pdf(self):
        self.assertEqual(len(self.reader.pages), 35)
        for number, batch in enumerate(logs.paginate_species(list(logs.LABELS)), 30):
            text = self.reader.pages[number].extract_text()
            self.assertIn("TRACKED SPECIES", text)
            for label in logs.LABELS.values():
                self.assertEqual(text.count(label), int(label in [logs.LABELS[e] for e in batch]))
        blank = self.reader.pages[-1].extract_text()
        self.assertIn("BLANK EDITION", blank)
        for label in logs.LABELS.values():
            self.assertNotIn(label, blank)

    def test_species_pages_preserve_v5_painted_content(self):
        from pypdf import PdfReader
        original = self.base / "v5.pdf"
        builder.compile_manifest(ROOT / "binder/manifest-v5.yaml", "draft", original)
        old = PdfReader(original)
        for number in range(30):
            self.assertEqual(self.reader.pages[number].get_contents().get_data(),
                             old.pages[number].get_contents().get_data(), number)

    def test_readable_text_rules_margins_and_writing_space(self):
        from test_binder import (_assert_pdf_text_inside_safe_rectangle,
                                 _assert_essential_painted_content_inside_safe_rectangle,
                                 _painted_pdf_geometry)
        _assert_pdf_text_inside_safe_rectangle(self.pdf, self.base / "bounds.html")
        _assert_essential_painted_content_inside_safe_rectangle(self.reader.pages)
        for page in self.reader.pages[-5:]:
            builder._validate_page(page, "care log")
            sizes = []
            page.extract_text(visitor_text=lambda text, cm, tm, font, size:
                              sizes.append(size) if text.strip() else None)
            self.assertGreaterEqual(min(sizes), 8.9)
            text = page.extract_text()
            self.assertEqual(text.count("A/M or Evt"),
                             logs.LOG_ROWS * (1 if "4 of 4" in text else 3))
            # Physical geometry is checked using actual painted horizontal rules.
            _, strokes, fills = _painted_pdf_geometry(page)
            bounds = strokes + fills
            horizontal = [(x0, y0, x1, y1) for x0, y0, x1, y1 in bounds
                          if y1-y0 < 1 and x1-x0 > 130]
            self.assertGreater(len(horizontal), 10)
            # Eight writable rows, each at least .43 inch high in the PDF.
            table_width = 200 if "4 of 4" in text else 490
            edges = sorted({round(y0, 2) for x0, y0, x1, y1 in horizontal
                            if x1-x0 > table_width})
            row_heights = [b-a for a, b in zip(edges, edges[1:]) if 30 <= b-a <= 40]
            self.assertEqual(len(row_heights), logs.LOG_ROWS)
            # Name and preference writing rules are at least 1.9 inches long.
            self.assertGreaterEqual(sum(136 <= x1-x0 <= 142
                                        for x0, y0, x1, y1 in horizontal),
                                    6 * (1 if "4 of 4" in text else 3))

    def test_white_paper_color_and_grayscale(self):
        from PIL import Image, ImageChops
        for gray in (False, True):
            prefix = self.base / ("gray" if gray else "color")
            subprocess.run(["pdftoppm", "-f", "31", "-l", "35", "-r", "72",
                            "-png", *(["-gray"] if gray else []), str(self.pdf), str(prefix)],
                           check=True, capture_output=True, timeout=60)
            for path in self.base.glob(prefix.name + "-*.png"):
                with Image.open(path) as source:
                    image = source.convert("RGB")
                    for box in ((0, 0, 60, 792), (585, 0, 612, 792), (0, 0, 612, 25)):
                        self.assertIsNone(ImageChops.difference(image.crop(box),
                            Image.new("RGB", (box[2]-box[0], box[3]-box[1]), "white")).getbbox())
                    white = sum(count for count, color in image.getcolors(612*792)
                                if color == (255, 255, 255))
                    self.assertGreater(white / (612*792), .85)


if __name__ == "__main__":
    unittest.main()
