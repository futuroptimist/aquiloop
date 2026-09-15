from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from binderlib import Asset, BinderError, load_catalog, placement_tex, validate_selection  # noqa: E402
from build_binder import selection  # noqa: E402
from prepare_binder_photo import prepare  # noqa: E402


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.entry = ROOT / "binder/entries/sedum-loves-fire"

    def test_proof_has_no_detail_and_unselected_asset_is_not_resolved(self):
        hero, details = selection((self.entry / "page.tex").read_text())
        catalog = load_catalog(self.entry)
        selected = validate_selection(catalog, hero, details, "draft")
        self.assertEqual([], details)
        self.assertEqual(["sedum-draft-placeholder-001"], [item.record["id"] for item in selected])
        self.assertNotIn("sedum-unselected-placeholder-002", placement_tex(selected[0], "hero"))

    def test_final_rejects_selected_placeholder_but_ignores_unselected_unknown_rights(self):
        catalog = load_catalog(self.entry)
        with self.assertRaisesRegex(BinderError, "selected placeholder"):
            validate_selection(catalog, "sedum-draft-placeholder-001", [], "final")
        unresolved = Asset(
            {**catalog["sedum-draft-placeholder-001"].record, "id": "synthetic-photo", "kind": "photograph"},
            Path("synthetic.jpg"),
            (1000, 1000),
            "JPEG",
            100,
        )
        catalog["synthetic-photo"] = unresolved
        with self.assertRaisesRegex(BinderError, "unresolved rights"):
            validate_selection(catalog, "synthetic-photo", [], "final")

    def test_duplicate_ids_and_unknown_schema_are_rejected(self):
        original = json.loads((self.entry / "assets.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            duplicate = {**original, "assets": [original["assets"][0], original["assets"][0]]}
            (temporary / "assets.json").write_text(json.dumps(duplicate))
            with self.assertRaisesRegex(BinderError, "duplicate"):
                load_catalog(temporary)
            duplicate["schema_version"] = 2
            (temporary / "assets.json").write_text(json.dumps(duplicate))
            with self.assertRaisesRegex(BinderError, "schema_version"):
                load_catalog(temporary)

    def test_selected_detail_is_resolved_at_exact_frame_ratio(self):
        catalog = load_catalog(self.entry)
        selected = validate_selection(catalog, "sedum-draft-placeholder-001", ["sedum-unselected-placeholder-002"], "draft")
        tex = placement_tex(selected[1], "detail")
        self.assertIn("2.02in", tex)
        self.assertIn("1.32in", tex)

    def test_template_declares_letter_geometry_and_all_eight_cards(self):
        template = (ROOT / "binder/template.tex").read_text()
        self.assertIn("letterpaper,left=1in,right=.55in,top=.55in,bottom=.55in", template)
        for heading in ("LIGHT / EXPOSURE", "SOIL / SUBSTRATE", "WATER", "TEMPERATURE / SEASON", "FEEDING / MAINTENANCE", "PROPAGATION", "TROUBLESHOOTING", "NATURAL HISTORY / TRIVIA"):
            self.assertEqual(1, template.count("{" + heading + "}"))


class PreparationTests(unittest.TestCase):
    def test_preparation_preserves_original_and_strips_exif(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "synthetic-original.jpg", root / "derivative.jpg"
            image = Image.new("RGB", (1200, 1000), "#d050c0")
            exif = Image.Exif()
            exif[270] = "VISIBLY SYNTHETIC TEST IMAGE"
            image.save(source, exif=exif)
            before = source.read_bytes()
            result = prepare(source, output, "hero", (0.5, 0.5))
            self.assertEqual(before, source.read_bytes())
            self.assertEqual((990, 990), result["dimensions"])
            with Image.open(output) as derivative:
                self.assertFalse(derivative.getexif())

    def test_insufficient_crop_same_file_and_overwrite_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "small.jpg", root / "out.jpg"
            Image.new("RGB", (700, 700), "red").save(source)
            with self.assertRaisesRegex(ValueError, "requires at least"):
                prepare(source, output, "hero", (0.5, 0.5))
            with self.assertRaisesRegex(ValueError, "different"):
                prepare(source, source, "hero", (0.5, 0.5))
            Image.new("RGB", (1000, 1000), "red").save(source)
            output.write_text("do not replace")
            with self.assertRaisesRegex(ValueError, "--overwrite"):
                prepare(source, output, "hero", (0.5, 0.5))


if __name__ == "__main__":
    unittest.main()
