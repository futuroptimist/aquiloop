"""Regression coverage for evidence boundaries and opt-in v2 assembly."""
import copy
import json
from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import shutil
import subprocess
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import binder_evidence as evidence
import build_binder as builder


class CompanionEvidenceTests(unittest.TestCase):
    def test_all_five_research_collections(self):
        for entry, _ in builder.EXPECTED_MANIFEST[:-1]:
            with self.subTest(entry=entry):
                self.assertTrue(evidence.load_companions(ROOT, entry)["claims"])

    def test_invalid_claims_are_rejected(self):
        data = evidence.load_companions(ROOT, "pothos")
        original = data["claims"]["pothos#preferred-temperature"]
        changes = [
            lambda c: c.update(description="second payload"),
            lambda c: c["quantity"].update(minimum=100),
            lambda c: c["quantity"].update(maximum=Decimal("Infinity")),
            lambda c: c["quantity"].update(minimum=True),
            lambda c: c["provenance"].update(source_refs=["MISSING"]),
            lambda c: c.update(evidence_category="proposed"),
            lambda c: c.update(evidence_category="observed"),
            lambda c: c.update(evidence_category="unknown"),
            lambda c: c.update(applicable_taxon=""),
        ]
        for mutate in changes:
            c = copy.deepcopy(original)
            mutate(c)
            with self.assertRaises(ValueError):
                evidence.validate_claim(c, data["sources"])

    def test_decimal_recipe_and_conversion(self):
        data = evidence.load_companions(ROOT, "sedum-loves-fire")
        c = copy.deepcopy(data["claims"]["sedum-loves-fire#established-substrate-recipe"])
        evidence.validate_claim(c, data["sources"])
        c["recipe"]["components"][0]["percent_by_volume"] += Decimal("0.0000000001")
        with self.assertRaises(ValueError):
            evidence.validate_claim(c, data["sources"])

    def test_unknown_cannot_have_citations_or_numbers(self):
        data = evidence.load_companions(ROOT, "pothos")
        c = copy.deepcopy(data["claims"]["pothos#lifespan"])
        c["provenance"]["source_refs"] = ["POT-WISC"]
        with self.assertRaises(ValueError):
            evidence.validate_claim(c, data["sources"])
        c["provenance"] = {}
        c["quantity"]["value"] = 0
        with self.assertRaises(ValueError):
            evidence.validate_claim(c, data["sources"])

    def test_canonical_sixteen_page_manifest(self):
        entries = builder.load_manifest(ROOT / "binder/manifest-v2.yaml")
        self.assertEqual(tuple((i["id"], i["kind"]) for i in entries), builder.EXPECTED_EXPANDED_MANIFEST)
        self.assertEqual(len(entries), 16)
        self.assertEqual(len(builder.load_manifest(ROOT / "binder/manifest.yaml")), 6)

    def test_v2_rejects_reorder_duplicate_missing_and_budget(self):
        original = json.loads((ROOT / "binder/manifest-v2.yaml").read_text())
        mutations = [lambda a: a.reverse(), lambda a: a.pop(),
                     lambda a: a.append(a[0]), lambda a: a[1].update(page_budget=2),
                     lambda a: a[1].update(kind="profile")]
        for mutate in mutations:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / "binder/manifest-v2.yaml"
                path.parent.mkdir()
                doc = copy.deepcopy(original)
                mutate(doc["entries"])
                path.write_text(json.dumps(doc))
                with mock.patch.object(builder, "ROOT", root), self.assertRaises(ValueError):
                    builder.load_manifest(path)

    def test_companions_reject_final_mode_and_path_traversal(self):
        for entry, kind, mode in [("pothos", "numbers", "final"), ("../pothos", "numbers", "draft")]:
            with self.assertRaises(ValueError):
                builder.compile_companion(entry, kind, mode, Path("unused.pdf"))

    def test_ten_authored_layouts_resolve_claims_and_keep_page_structure(self):
        import re
        for entry, kind in builder.EXPECTED_EXPANDED_MANIFEST:
            if kind not in {"numbers", "propagation"}:
                continue
            data = evidence.load_companions(ROOT, entry)
            page = (ROOT / "binder/entries" / entry / f"{kind}.tex").read_text(encoding="utf-8")
            refs = re.findall(r"^% claim-ref: (\S+)$", page, re.MULTILINE)
            self.assertTrue(refs)
            self.assertTrue(set(refs) <= data["claims"].keys())
            self.assertIn(entry + " / " + kind, page)
            if kind == "numbers":
                self.assertEqual(page.count(r"\CardRow{"), 4)
            else:
                self.assertEqual(page.count(r"\Step{"), 8)
                self.assertEqual(page.count(r"\Note{Check "), 3)


@unittest.skipUnless(all(shutil.which(t) for t in ("lualatex", "pdftotext", "pdftoppm")), "LuaLaTeX and Poppler required")
class ExpandedRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pypdf import PdfReader
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.base = Path(cls.directory.name)
        cls.pdf = cls.base / "expanded.pdf"
        builder.compile_manifest(ROOT / "binder/manifest-v2.yaml", "draft", cls.pdf)
        cls.reader = PdfReader(cls.pdf)

    def test_sixteen_pages_order_boxes_and_identity(self):
        self.assertEqual(len(self.reader.pages), 16)
        for page, (entry, kind) in zip(self.reader.pages, builder.EXPECTED_EXPANDED_MANIFEST):
            builder._validate_page(page, entry)
            content = page.extract_text()
            if kind in {"numbers", "propagation"}:
                self.assertIn(entry + " / " + kind, content)
            elif kind == "profile":
                self.assertIn("OVERVIEW / REVISION", content)
            else:
                from test_binder import _assert_watering_log_text_contract
                _assert_watering_log_text_contract(content)

    def test_all_text_and_painted_content_inside_safe_area(self):
        from test_binder import (_assert_pdf_text_inside_safe_rectangle,
                                 _assert_essential_painted_content_inside_safe_rectangle)
        self.assertEqual(len(_assert_pdf_text_inside_safe_rectangle(self.pdf, self.base / "boxes.html")), 16)
        _assert_essential_painted_content_inside_safe_rectangle(self.reader.pages)

    def test_white_margins_in_color_and_grayscale(self):
        from PIL import Image
        from test_binder import WHITE_BACKGROUND_PATCHES
        for gray in (False, True):
            prefix = self.base / ("gray" if gray else "color")
            subprocess.run(["pdftoppm", "-r", "72", "-png", *(["-gray"] if gray else []), str(self.pdf), str(prefix)], check=True, capture_output=True, timeout=120)
            paths = list(self.base.glob(prefix.name + "-*.png"))
            self.assertEqual(len(paths), 16)
            for path in paths:
                with Image.open(path) as image:
                    for box in WHITE_BACKGROUND_PATCHES:
                        self.assertEqual(image.convert("RGB").crop(box).getextrema(), ((255,255),)*3)


if __name__ == "__main__":
    unittest.main()
