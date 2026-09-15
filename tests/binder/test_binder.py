from __future__ import annotations

import json
import tempfile
import unittest
import os
import shutil
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
        cases = (
            (lambda d: d["assets"].append(d["assets"][0].copy()), "sedum-placeholder-001", "duplicate"),
            (lambda d: None, "missing-id", "unknown asset"),
        )
        for mutation, selected_id, message in cases:
            with tempfile.TemporaryDirectory(dir=ROOT / "binder" / "entries") as name:
                base = Path(name)
                (base / "assets").mkdir()
                (base / "assets" / "draft-placeholder.txt").write_text("synthetic")
                candidate = json.loads(json.dumps(data)); mutation(candidate)
                (base / "assets.json").write_text(json.dumps(candidate))
                (base / "page.tex").write_text(f"% binder-placement hero {selected_id}; test\n")
                with self.assertRaisesRegex(ValueError, message):
                    build_binder.load_entry(base.name, "draft")

    def test_source_type_and_asset_kind_are_validated(self):
        real = ROOT / "binder" / "entries" / "sedum-loves-fire"
        data = json.loads((real / "assets.json").read_text())
        for invalid_source, message in ((True, "source metadata must be an object"), (False, "unsupported kind")):
            with tempfile.TemporaryDirectory(dir=ROOT / "binder" / "entries") as name:
                base = Path(name); (base / "assets").mkdir()
                (base / "assets" / "draft-placeholder.txt").write_text("synthetic")
                candidate = json.loads(json.dumps(data))
                if invalid_source:
                    candidate["assets"][0]["source"] = "invalid"
                else:
                    candidate["assets"][0]["kind"] = "image"
                (base / "assets.json").write_text(json.dumps(candidate))
                (base / "page.tex").write_text("% binder-placement hero sedum-placeholder-001; test\n")
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

    def test_final_requires_positive_rights_review_and_matching_aspect(self):
        real = ROOT / "binder" / "entries" / "sedum-loves-fire"
        data = json.loads((real / "assets.json").read_text())
        record = data["assets"][0]
        record.update({"path": "assets/photo.jpg", "kind": "photograph"})
        record["source"]["rights"] = "permission requested"
        with tempfile.TemporaryDirectory(dir=ROOT / "binder" / "entries") as name:
            base = Path(name); (base / "assets").mkdir()
            Image.new("RGB", (1200, 800)).save(base / "assets" / "photo.jpg")
            (base / "assets.json").write_text(json.dumps(data))
            (base / "page.tex").write_text("% binder-placement hero sedum-placeholder-001; test\n")
            with self.assertRaisesRegex(ValueError, "not qualified"):
                build_binder.load_entry(base.name, "final")
            record["source"]["rights_reviewed"] = True
            (base / "assets.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "aspect ratio"):
                build_binder.load_entry(base.name, "final")


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

    def test_reports_soft_goal_but_enforces_hard_ceiling(self):
        with tempfile.TemporaryDirectory() as name:
            source = Path(name) / "source.jpg"
            output = Path(name) / "derived.jpg"
            Image.effect_noise((990, 990), 100).convert("RGB").save(source)
            original_frame = prepare_binder_photo.FRAMES["hero"]
            prepare_binder_photo.FRAMES["hero"] = (3.30, 3.30, 100)
            try:
                result = prepare_binder_photo.prepare(source, output, "hero", None, False)
                self.assertFalse(result["soft_size_goal_met"])
            finally:
                prepare_binder_photo.FRAMES["hero"] = original_frame
            self.assertTrue(output.exists())
            output.unlink()
            old_ceiling = prepare_binder_photo.HARD_CEILING
            prepare_binder_photo.HARD_CEILING = 100
            try:
                with self.assertRaisesRegex(ValueError, "1 MiB hard ceiling"):
                    prepare_binder_photo.prepare(source, output, "hero", None, False)
            finally:
                prepare_binder_photo.HARD_CEILING = old_ceiling
            self.assertFalse(output.exists())


class ComprehensiveRegressionTests(unittest.TestCase):
    def fixture(self, details=0, extra=None, page_suffix=""):
        context = tempfile.TemporaryDirectory(dir=ROOT / "binder" / "entries")
        base = Path(context.name); (base / "assets").mkdir()
        records = []
        specs = [("hero", (990, 990))] + [(f"detail{i}", (615, 405)) for i in range(1, details + 1)]
        for asset_id, size in specs:
            Image.new("RGB", size, (190, 64 + len(records) * 40, 52)).save(base / "assets" / f"{asset_id}.jpg")
            records.append({"id": asset_id, "path": f"assets/{asset_id}.jpg", "kind": "photograph", "subjects": ["visibly synthetic raster"], "alt": "Visibly synthetic raster.", "caption": "Synthetic test raster.", "source": {"photographer": "test suite", "provenance": "generated fixture", "rights": "owned test fixture", "rights_reviewed": True}})
        if extra: records.append(extra)
        (base / "assets.json").write_text(json.dumps({"schema_version": 1, "assets": records}), encoding="utf-8")
        placements = ["% binder-placement hero hero; synthetic fixture"] + [f"% binder-placement detail{i} detail{i}; synthetic fixture" for i in range(1, details + 1)]
        page = (ROOT / "binder/entries/sedum-loves-fire/page.tex").read_text(encoding="utf-8")
        page = "\n".join(placements) + "\n" + "\n".join(x for x in page.splitlines() if not x.startswith("% binder-placement")) + page_suffix
        (base / "page.tex").write_text(page, encoding="utf-8")
        return context, base

    @unittest.skipUnless(shutil.which("lualatex"), "lualatex unavailable")
    def test_actual_pdf_zero_one_two_details_and_determinism(self):
        from pypdf import PdfReader
        for count in range(3):
            context, base = self.fixture(count)
            with context:
                loaded = build_binder.load_entry(base.name, "final")
                first = base / "first.pdf"; second = base / "second.pdf"
                build_binder.compile_entry(*loaded, first); build_binder.compile_entry(*loaded, second)
                self.assertEqual(first.read_bytes(), second.read_bytes())
                reader = PdfReader(first)
                self.assertEqual(len(reader.pages), 1)
                self.assertAlmostEqual(float(reader.pages[0].mediabox.width), 612, delta=.1)
                self.assertAlmostEqual(float(reader.pages[0].mediabox.height), 792, delta=.1)
                text = reader.pages[0].extract_text()
                self.assertIn("PROPAGATION", text); self.assertIn("PLACEHOLDER", text)
                self.assertEqual(set(loaded[2]), {"hero"} | {f"detail{i}" for i in range(1, count + 1)})

    @unittest.skipUnless(shutil.which("lualatex"), "lualatex unavailable")
    def test_selected_detail_placeholders_are_visibly_labeled(self):
        from pypdf import PdfReader
        context, base = self.fixture(1)
        with context:
            data = json.loads((base / "assets.json").read_text(encoding="utf-8"))
            detail = data["assets"][1]
            detail.update(path="assets/detail.txt", kind="placeholder")
            (base / "assets/detail.txt").write_text("placeholder", encoding="utf-8")
            (base / "assets.json").write_text(json.dumps(data), encoding="utf-8")
            output = base / "placeholder.pdf"
            build_binder.compile_entry(*build_binder.load_entry(base.name, "draft"), output)
            text = PdfReader(output).pages[0].extract_text()
            self.assertIn("DRAFT PLACEHOLDER", text)
            self.assertIn("detail1", text)

    def test_template_declares_exact_outer_frame_geometry(self):
        template = (ROOT / "binder/template.tex").read_text(encoding="utf-8")
        self.assertIn("rectangle (3.30in,3.30in)", template)
        self.assertIn("rectangle (2.05in,1.35in)", template)
        self.assertNotIn("keepaspectratio=false", template)

    @unittest.skipUnless(shutil.which("lualatex"), "lualatex unavailable")
    def test_overflow_is_rejected(self):
        context, base = self.fixture(page_suffix="\\par " + ("OVERFLOW " * 5000))
        with context, self.assertRaisesRegex(RuntimeError, "rendered .* pages|overfull"):
            build_binder.compile_entry(*build_binder.load_entry(base.name, "final"), base / "bad.pdf")

    def test_valid_unselected_unknown_rights_does_not_change_output_selection(self):
        extra={"id":"unused","path":"assets/unused.txt","kind":"placeholder","subjects":["unknown specimen"],"alt":"Unknown draft.","caption":"Unknown draft.","source":{"photographer":"unknown","provenance":"unknown","rights":"unknown"}}
        context, base = self.fixture(extra=extra)
        with context:
            (base / "assets/unused.txt").write_text("unused", encoding="utf-8")
            _, records, selected = build_binder.load_entry(base.name, "final")
            self.assertIn("unused", records); self.assertNotIn("unused", selected.values())

    @unittest.skipUnless(shutil.which("lualatex"), "lualatex unavailable")
    def test_valid_unselected_record_does_not_change_pdf(self):
        context, base = self.fixture()
        with context:
            before = base / "before.pdf"
            build_binder.compile_entry(*build_binder.load_entry(base.name, "final"), before)
            data = json.loads((base / "assets.json").read_text(encoding="utf-8"))
            data["assets"].append({"id":"unused","path":"assets/unused.txt","kind":"placeholder","subjects":["unknown specimen"],"alt":"Unknown draft.","caption":"Unknown draft.","source":{"photographer":"unknown","provenance":"unknown","rights":"unknown"}})
            (base / "assets/unused.txt").write_text("unused", encoding="utf-8")
            (base / "assets.json").write_text(json.dumps(data), encoding="utf-8")
            after = base / "after.pdf"
            build_binder.compile_entry(*build_binder.load_entry(base.name, "final"), after)
            self.assertEqual(before.read_bytes(), after.read_bytes())

    def test_catalog_container_metadata_path_resolution_and_size_failures(self):
        context, base = self.fixture()
        with context:
            original = json.loads((base / "assets.json").read_text(encoding="utf-8"))
            cases=[]
            cases.append(([], "contain an object"))
            cases.append(({"schema_version":1,"assets":{}}, "array"))
            bad=json.loads(json.dumps(original)); bad["assets"][0]["alt"]=""; cases.append((bad,"nonempty"))
            bad=json.loads(json.dumps(original)); bad["assets"][0]["subjects"]="plant"; cases.append((bad,"subjects"))
            bad=json.loads(json.dumps(original)); bad["assets"][0]["id"]="bad id"; cases.append((bad,"malformed"))
            bad=json.loads(json.dumps(original)); bad["assets"][0]["path"]="../page.tex"; cases.append((bad,"within entry"))
            for candidate,message in cases:
                (base / "assets.json").write_text(json.dumps(candidate),encoding="utf-8")
                with self.assertRaisesRegex(ValueError,message): build_binder.load_entry(base.name,"draft")
            (base / "assets.json").write_text(json.dumps(original),encoding="utf-8")
            Image.new("RGB",(20,20)).save(base/"assets/hero.jpg")
            with self.assertRaisesRegex(ValueError,"below"): build_binder.load_entry(base.name,"draft")
            Image.effect_noise((990,990),100).save(base/"assets/hero.jpg",quality=100)
            with self.assertRaisesRegex(ValueError,"1 MiB"): build_binder.load_entry(base.name,"draft")

    def test_duplicate_and_malformed_placements_are_independent(self):
        for lines,message in [(["% binder-placement hero hero; ok","% binder-placement hero hero; twice"],"duplicate"),(["% binder-placement hero hero"],"malformed"),(["% binder-placement hero missing; ok"],"unknown asset")]:
            context,base=self.fixture()
            with context:
                (base/"page.tex").write_text("\n".join(lines),encoding="utf-8")
                with self.assertRaisesRegex(ValueError,message): build_binder.load_entry(base.name,"draft")

    def test_unresolved_selected_rights_values_are_rejected(self):
        for rights in ("permission requested","TBD","not reviewed","permission denied"):
            context,base=self.fixture()
            with context:
                data=json.loads((base/"assets.json").read_text()); data["assets"][0]["source"].update(rights=rights,rights_reviewed=False)
                (base/"assets.json").write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError,"not qualified"): build_binder.load_entry(base.name,"final")

    def test_hard_link_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as name:
            source=Path(name)/"source.jpg"; output=Path(name)/"alias.jpg"
            Image.new("RGB",(990,990)).save(source); os.link(source,output); before=source.read_bytes()
            with self.assertRaisesRegex(ValueError,"differ"): prepare_binder_photo.prepare(source,output,"hero",None,True)
            self.assertEqual(source.read_bytes(),before)

    def test_orientation_gps_removal_and_icc_conversion(self):
        from PIL import ImageCms
        with tempfile.TemporaryDirectory() as name:
            source=Path(name)/"source.jpg"; output=Path(name)/"out.jpg"
            exif=Image.Exif(); exif[274]=6; exif[34853]={1:"N",2:(1,1,1),3:"E",4:(1,1,1)}
            profile=ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
            Image.new("RGB",(990,990),(20,90,140)).save(source,exif=exif,icc_profile=profile)
            prepare_binder_photo.prepare(source,output,"hero",None,False)
            with Image.open(output) as image:
                self.assertFalse(image.getexif()); self.assertIn("icc_profile",image.info)


if __name__ == "__main__":
    unittest.main()
