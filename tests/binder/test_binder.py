from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from build_binder import BinderError, load_entry  # noqa: E402
from prepare_binder_photo import prepare  # noqa: E402


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.entry = Path(self.temp.name) / "entry"
        shutil.copytree(ROOT / "binder/entries/sedum-loves-fire", self.entry)

    def tearDown(self):
        self.temp.cleanup()

    def catalog(self):
        return json.loads((self.entry / "assets.json").read_text())

    def write_catalog(self, value):
        (self.entry / "assets.json").write_text(json.dumps(value))

    def test_draft_allows_selected_placeholder(self):
        assets, selections = load_entry(self.entry, "draft")
        self.assertEqual(selections["HeroAsset"], "sedum-draft-placeholder")
        self.assertEqual(assets["sedum-draft-placeholder"]["kind"], "placeholder")

    def test_final_rejects_selected_placeholder(self):
        with self.assertRaisesRegex(BinderError, "rejects selected placeholder"):
            load_entry(self.entry, "final")

    def test_duplicate_ids_are_rejected(self):
        catalog = self.catalog()
        catalog["assets"].append(catalog["assets"][0].copy())
        self.write_catalog(catalog)
        with self.assertRaisesRegex(BinderError, "duplicate asset ID"):
            load_entry(self.entry, "draft")

    def test_unselected_unknown_rights_do_not_block_final(self):
        from PIL import Image
        Image.new("RGB", (1000, 1000), "green").save(self.entry / "assets/hero.jpg")
        catalog = self.catalog()
        catalog["assets"].append({
            "id": "qualified-hero", "path": "assets/hero.jpg", "kind": "photograph",
            "subjects": ["synthetic square"], "alt": "Synthetic green test square.",
            "caption": "Synthetic test fixture.", "source": {
                "photographer": "test suite", "provenance": "generated synthetic fixture",
                "rights": "CC0 test fixture"}})
        self.write_catalog(catalog)
        page = (self.entry / "page.tex").read_text().replace(
            r"\def\HeroAsset{sedum-draft-placeholder}", r"\def\HeroAsset{qualified-hero}")
        (self.entry / "page.tex").write_text(page)
        _, selections = load_entry(self.entry, "final")
        self.assertEqual(selections["HeroAsset"], "qualified-hero")

    def test_selected_unresolved_rights_are_rejected(self):
        from PIL import Image
        Image.new("RGB", (1000, 1000), "blue").save(self.entry / "assets/hero.jpg")
        catalog = self.catalog()
        record = catalog["assets"][0].copy()
        record.update({"id": "unknown-rights-photo", "path": "assets/hero.jpg",
                       "kind": "photograph"})
        catalog["assets"].append(record)
        self.write_catalog(catalog)
        page = (self.entry / "page.tex").read_text().replace(
            r"\def\HeroAsset{sedum-draft-placeholder}", r"\def\HeroAsset{unknown-rights-photo}")
        (self.entry / "page.tex").write_text(page)
        with self.assertRaisesRegex(BinderError, "unresolved rights"):
            load_entry(self.entry, "final")

    def test_no_details_and_unselected_catalog_record_are_inert(self):
        _, selections_before = load_entry(self.entry, "draft")
        catalog = self.catalog()
        extra = catalog["assets"][1].copy()
        extra["id"] = "unselected-extra"
        catalog["assets"].append(extra)
        self.write_catalog(catalog)
        _, selections_after = load_entry(self.entry, "draft")
        self.assertEqual(selections_before, selections_after)
        self.assertEqual(selections_after["DetailOneAsset"], "")
        self.assertEqual(selections_after["DetailTwoAsset"], "")


@unittest.skipUnless(__import__("importlib").util.find_spec("PIL"), "Pillow is required")
class PhotoPreparationTests(unittest.TestCase):
    def test_original_unchanged_and_insufficient_crop_rejected(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as raw:
            source, output = Path(raw) / "synthetic.png", Path(raw) / "derived.jpg"
            Image.new("RGB", (800, 800), "magenta").save(source)
            before = source.read_bytes()
            result = prepare(source, output, "hero", None)
            self.assertEqual(source.read_bytes(), before)
            self.assertGreaterEqual(result["effective_ppi"], 240)
            with self.assertRaisesRegex(ValueError, "insufficient resolution"):
                prepare(source, Path(raw) / "small.jpg", "hero", (0, 0, 700, 700))

    def test_same_file_and_implicit_overwrite_are_rejected(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as raw:
            source, output = Path(raw) / "synthetic.png", Path(raw) / "derived.jpg"
            Image.new("RGB", (1000, 1000), "cyan").save(source)
            with self.assertRaisesRegex(ValueError, "must differ"):
                prepare(source, source, "hero", None)
            prepare(source, output, "hero", None)
            with self.assertRaises(FileExistsError):
                prepare(source, output, "hero", None)


if __name__ == "__main__":
    unittest.main()
