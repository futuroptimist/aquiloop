from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_binder  # noqa: E402
import prepare_binder_photo  # noqa: E402


class CatalogTests(unittest.TestCase):
    def test_draft_loads_and_has_no_empty_detail_placements(self):
        _, records, selected = build_binder.load_entry("sedum-loves-fire", "draft")
        self.assertEqual(selected, {"hero": "sedum-placeholder-001"})
        self.assertGreater(len(records), 0)

    def test_final_rejects_selected_placeholder_and_unresolved_rights(self):
        with self.assertRaisesRegex(ValueError, "not qualified for final mode"):
            build_binder.load_entry("sedum-loves-fire", "final")

    def test_duplicate_ids_and_unknown_selection_are_rejected(self):
        real = ROOT / "binder" / "entries" / "sedum-loves-fire"
        data = json.loads((real / "assets.json").read_text())
        for mutation, message in ((lambda d: d["assets"].append(d["assets"][0].copy()), "duplicate"),):
            with tempfile.TemporaryDirectory(dir=ROOT / "binder" / "entries") as name:
                base = Path(name)
                (base / "assets").mkdir()
                (base / "assets" / "draft-placeholder.txt").write_text("synthetic")
                candidate = json.loads(json.dumps(data)); mutation(candidate)
                (base / "assets.json").write_text(json.dumps(candidate))
                (base / "page.tex").write_text("% binder-placement hero missing-id; test\n")
                with self.assertRaisesRegex(ValueError, message):
                    build_binder.load_entry(base.name, "draft")

    def test_selected_details_are_explicit_and_unselected_records_stay_unselected(self):
        real = ROOT / "binder" / "entries" / "sedum-loves-fire"
        with tempfile.TemporaryDirectory(dir=ROOT / "binder" / "entries") as name:
            base = Path(name); (base / "assets").mkdir()
            assets = []
            for asset_id, size in (("hero", (990, 990)), ("detail", (615, 405)), ("unused", (615, 405))):
                path = base / "assets" / f"{asset_id}.jpg"
                Image.new("RGB", size, "#9b6245").save(path)
                assets.append({"id": asset_id, "path": f"assets/{asset_id}.jpg", "kind": "photograph", "subjects": ["synthetic fixture"], "alt": "Visibly synthetic fixture.", "caption": "Synthetic fixture.", "source": {"photographer": "test suite", "provenance": "generated test fixture", "rights": "test-only owned fixture"}})
            (base / "assets.json").write_text(json.dumps({"schema_version": 1, "assets": assets}))
            (base / "page.tex").write_text("% binder-placement hero hero; test\n% binder-placement detail1 detail; test\n")
            _, _, selected = build_binder.load_entry(base.name, "draft")
            self.assertEqual(selected, {"hero": "hero", "detail1": "detail"})
            self.assertNotIn("unused", selected.values())


class PhotoPreparationTests(unittest.TestCase):
    def test_prepares_derivative_without_changing_original_or_gps(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name); source = base / "original.jpg"; output = base / "derived.jpg"
            Image.new("RGB", (1200, 1200), "#c65f45").save(source, exif=Image.Exif())
            before = source.read_bytes()
            result = prepare_binder_photo.prepare(source, output, "hero", None, False)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual((result["width"], result["height"]), (990, 990))
            with Image.open(output) as prepared:
                self.assertFalse(prepared.getexif())

    def test_rejects_insufficient_resolution_same_file_and_overwrite(self):
        with tempfile.TemporaryDirectory() as name:
            source = Path(name) / "small.jpg"; output = Path(name) / "exists.jpg"
            Image.new("RGB", (500, 500)).save(source); output.write_text("keep")
            with self.assertRaisesRegex(ValueError, "insufficient"):
                prepare_binder_photo.prepare(source, Path(name) / "new.jpg", "hero", None, False)
            with self.assertRaisesRegex(ValueError, "differ"):
                prepare_binder_photo.prepare(source, source, "hero", None, False)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                prepare_binder_photo.prepare(source, output, "hero", None, False)


if __name__ == "__main__":
    unittest.main()
