from __future__ import annotations

import json
import tempfile
import unittest
import os
import shutil
from unittest import mock
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
        record["source"].update(rights="owned test fixture", rights_reviewed=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "binder" / "entries") as name:
            base = Path(name); (base / "assets").mkdir()
            Image.new("RGB", (1200, 800)).save(base / "assets" / "photo.jpg")
            (base / "assets.json").write_text(json.dumps(data))
            (base / "page.tex").write_text("% binder-placement hero sedum-placeholder-001; test\n")
            with self.assertRaisesRegex(ValueError, "aspect ratio"):
                build_binder.load_entry(base.name, "final")

    def test_catalog_rejects_missing_files_metadata_schema_and_format(self):
        real = ROOT / "binder" / "entries" / "sedum-loves-fire"
        original = json.loads((real / "assets.json").read_text())
        cases = []
        bad = json.loads(json.dumps(original)); bad["schema_version"] = 2
        cases.append((bad, "supported schema_version"))
        bad = json.loads(json.dumps(original)); del bad["assets"][0]["caption"]
        cases.append((bad, "missing required metadata"))
        bad = json.loads(json.dumps(original)); bad["assets"][0]["source"].pop("provenance")
        cases.append((bad, "missing source metadata"))
        bad = json.loads(json.dumps(original)); bad["assets"][0]["path"] = "assets/missing.txt"
        cases.append((bad, "resolve within entry"))
        for candidate, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory(dir=ROOT / "binder" / "entries") as name:
                base = Path(name); (base / "assets").mkdir()
                (base / "assets/draft-placeholder.txt").write_text("fixture")
                (base / "assets.json").write_text(json.dumps(candidate))
                (base / "page.tex").write_text("% binder-placement hero sedum-placeholder-001; fixture\n")
                with self.assertRaisesRegex(ValueError, message):
                    build_binder.load_entry(base.name, "draft")


class AssemblyTests(unittest.TestCase):
    def test_manifest_is_the_ordered_single_page_assembly_authority(self):
        manifest = build_binder.load_manifest(ROOT / "binder" / "manifest.yaml")
        self.assertEqual(
            [item["id"] for item in manifest],
            [
                "sedum-loves-fire", "kalanchoe-desert", "pothos",
                "bird-of-paradise", "aquarium-hornwort", "watering-log",
            ],
        )
        self.assertEqual(
            [item["kind"] for item in manifest],
            ["profile"] * 5 + ["supplemental"],
        )
        self.assertTrue(all(item["page_budget"] == 1 for item in manifest))

    def test_manifest_rejects_noncanonical_entries_kinds_order_and_budgets(self):
        original = json.loads((ROOT / "binder" / "manifest.yaml").read_text())
        mutations = (
            lambda entries: entries.pop(),
            lambda entries: entries.append(entries[-1].copy()),
            lambda entries: entries.__setitem__(1, entries[0].copy()),
            lambda entries: entries.reverse(),
            lambda entries: entries[0].__setitem__("kind", "supplemental"),
            lambda entries: entries[0].__setitem__("page_budget", 2),
            lambda entries: entries[0].__setitem__("page_budget", True),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                path = root / "binder" / "manifest.yaml"
                path.parent.mkdir()
                manifest = json.loads(json.dumps(original))
                mutation(manifest["entries"])
                path.write_text(json.dumps(manifest))
                with mock.patch.object(build_binder, "ROOT", root):
                    with self.assertRaises(ValueError):
                        build_binder.load_manifest(path)

    def test_page_validation_rejects_shifted_crop_near_blank_and_rotation(self):
        class Box:
            def __init__(self, coordinates):
                self.lower_left = coordinates[:2]
                self.upper_right = coordinates[2:]

        class Page:
            mediabox = Box((0, 0, 612, 792))
            cropbox = Box((0, 0, 612, 792))

            def __init__(self, text="meaningful binder page content", rotation=0, crop=None):
                self.text = text
                self.rotation = rotation
                if crop:
                    self.cropbox = Box(crop)

            def get(self, key):
                return self.rotation if key == "/Rotate" else None

            def extract_text(self):
                return self.text

        build_binder._validate_page(Page(), "valid")
        for page, message in (
            (Page(crop=(20, 20, 632, 812)), "geometry"),
            (Page(text=" \n\t"), "near-blank"),
            (Page(text="page 1"), "near-blank"),
            (Page(rotation=90), "rotation"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(RuntimeError, message):
                build_binder._validate_page(page, "invalid")

    def test_supplemental_rejects_final_mode(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "watering-log.pdf"
            with self.assertRaisesRegex(ValueError, "only in draft mode"):
                build_binder.compile_supplemental("watering-log", "final", output)
            self.assertFalse(output.exists())

    def test_combined_expected_count_is_not_derived_from_manifest_length(self):
        self.assertEqual(build_binder.EXPECTED_BINDER_PAGES, 6)
        self.assertEqual(len(build_binder.EXPECTED_MANIFEST), 6)
        shortened = list(build_binder.EXPECTED_MANIFEST[:-1])
        self.assertNotEqual(len(shortened), build_binder.EXPECTED_BINDER_PAGES)

    @unittest.skipUnless(shutil.which("lualatex"), "lualatex unavailable")
    def test_all_profiles_build_independently_with_content_and_geometry(self):
        from pypdf import PdfReader

        required_cards = {
            "sedum-loves-fire": ("LIGHT / EXPOSURE", "SOIL / SUBSTRATE", "WATER", "TEMPERATURE / SEASON", "FEEDING / MAINTENANCE", "PROPAGATION", "TROUBLESHOOTING", "NATURAL HISTORY / TRIVIA"),
            "kalanchoe-desert": ("LIGHT / EXPOSURE", "SOIL / SUBSTRATE", "WATER", "TEMPERATURE / SEASON", "FEEDING / MAINTENANCE", "PROPAGATION", "TROUBLESHOOTING", "NATURAL HISTORY / TRIVIA"),
            "pothos": ("LIGHT / EXPOSURE", "SOIL / SUBSTRATE", "WATER", "TEMPERATURE / SEASON", "FEEDING / MAINTENANCE", "PROPAGATION", "TROUBLESHOOTING", "NATURAL HISTORY / TRIVIA"),
            "bird-of-paradise": ("LIGHT / EXPOSURE", "SOIL / SUBSTRATE", "WATER", "TEMPERATURE / SEASON", "FEEDING / MAINTENANCE", "PROPAGATION", "TROUBLESHOOTING", "NATURAL HISTORY / TRIVIA"),
            "aquarium-hornwort": ("LIGHT", "WATER PARAMETERS / TEMPERATURE", "PLACEMENT / FLOATING", "NUTRIENT CONTEXT", "GROWTH / TRIMMING", "PROPAGATION", "COMPATIBILITY / TROUBLESHOOTING", "NATURAL HISTORY / TRIVIA"),
        }
        with tempfile.TemporaryDirectory() as name:
            for slug, cards in required_cards.items():
                with self.subTest(entry=slug):
                    output = Path(name) / f"{slug}.pdf"
                    build_binder.compile_entry(*build_binder.load_entry(slug, "draft"), output)
                    reader = PdfReader(output)
                    self.assertEqual(len(reader.pages), 1)
                    page = reader.pages[0]
                    build_binder._validate_page(page, slug)
                    text = page.extract_text()
                    self.assertIn("EVIDENCE", text)
                    self.assertIn("DRAFT PLACEHOLDER", text)
                    for card in cards:
                        self.assertIn(card, text)

    @unittest.skipUnless(shutil.which("lualatex"), "lualatex unavailable")
    def test_watering_log_and_manifest_build_with_required_text_and_order(self):
        from pypdf import PdfReader

        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            log = base / "watering-log.pdf"
            first = base / "binder-first.pdf"
            second = base / "binder-second.pdf"
            build_binder.compile_supplemental("watering-log", "draft", log)
            log_reader = PdfReader(log)
            self.assertEqual(len(log_reader.pages), 1)
            log_text = log_reader.pages[0].extract_text()
            for text in (
                "Sedum", "Kalanchoe", "Pothos", "Bird of paradise",
                "Hornwort", "Planning estimate only", "Rain/amount",
                "Watering interval:", "N/A", "Aquarium maintenance", "not watering",
                "Event:", "Amount/result:",
            ):
                self.assertIn(text, log_text)
            labels = {"Date:", "Time:", "Amount/method:", "Observation:",
                      "Rain/amount:", "Event:", "Amount/result:"}
            sizes = []
            date_positions = []
            aquarium_observation_positions = []

            def inspect_text(text, _cm, tm, _font, font_size):
                stripped = text.strip()
                if any(label in stripped for label in labels):
                    sizes.append(font_size)
                if "Date:" in stripped:
                    date_positions.append(tm[5])
                if "Observation:" in stripped and tm[4] > 430:
                    aquarium_observation_positions.append(tm[5])

            log_reader.pages[0].extract_text(visitor_text=inspect_text)
            self.assertTrue(sizes)
            self.assertGreaterEqual(min(sizes), 7.9)
            # LuaLaTeX exposes requested 8 pt labels as about 7.97011 PDF
            # points. 7.9 is an extraction tolerance, not a smaller print size.
            row_tops = sorted(set(round(position, 1) for position in date_positions), reverse=True)
            self.assertEqual(len(row_tops), 14)
            self.assertGreaterEqual(min(a - b for a, b in zip(row_tops, row_tops[1:])), 34.56)
            self.assertEqual(len(aquarium_observation_positions), 14)
            for label, expected_count in (
                ("Date:", 14), ("Time:", 14), ("Event:", 14),
                ("Amount/result:", 14), ("Observation:", 70),
                ("Amount/method:", 56), ("Rain/amount:", 28),
            ):
                self.assertEqual(log_text.count(label), expected_count, label)

            manifest = ROOT / "binder" / "manifest.yaml"
            build_binder.compile_manifest(manifest, "draft", first)
            build_binder.compile_manifest(manifest, "draft", second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            reader = PdfReader(first)
            self.assertEqual(len(reader.pages), 6)
            expected = (
                "Sedum", "Kalanchoe", "Pothos", "Bird of paradise",
                "Aquarium hornwort", "Watering & aquarium log",
            )
            for page, title in zip(reader.pages, expected):
                text = page.extract_text()
                self.assertIn(title, text)
                if title != "Watering & aquarium log":
                    self.assertIn("PROPAGATION", text)
                build_binder._validate_page(page, title)


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
    def fixture(self, details=0, extra=None, page_suffix="", prefix="tmp"):
        context = tempfile.TemporaryDirectory(prefix=prefix, dir=ROOT / "binder" / "entries")
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
                self.assertIn("PROPAGATION", text); self.assertIn("SED-MSU", text)
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

    def test_selected_raster_rejects_unsupported_format(self):
        context, base = self.fixture()
        with context:
            data = json.loads((base / "assets.json").read_text())
            image = base / data["assets"][0]["path"]
            unsupported = image.with_suffix(".bmp")
            Image.open(image).save(unsupported, format="BMP")
            image.unlink()
            data["assets"][0]["path"] = "assets/hero.bmp"
            (base / "assets.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "unsupported raster format"):
                build_binder.load_entry(base.name, "draft")

    def test_duplicate_and_malformed_placements_are_independent(self):
        for lines,message in [(["% binder-placement hero hero; ok","% binder-placement hero hero; twice"],"duplicate"),(["% binder-placement hero hero"],"malformed"),(["% binder-placement hero missing; ok"],"unknown asset")]:
            context,base=self.fixture()
            with context:
                (base/"page.tex").write_text("\n".join(lines),encoding="utf-8")
                with self.assertRaisesRegex(ValueError,message): build_binder.load_entry(base.name,"draft")

    def test_unresolved_selected_rights_values_are_rejected(self):
        for rights in ("unknown", "pending", "unresolved", " Pending ", "UNRESOLVED", "permission requested", "TBD", "not reviewed", "permission denied"):
            for review in (True, False, None):
                with self.subTest(rights=rights, rights_reviewed=review):
                    context,base=self.fixture()
                    with context:
                        data=json.loads((base/"assets.json").read_text())
                        source=data["assets"][0]["source"]
                        source["rights"] = rights
                        if review is None:
                            source.pop("rights_reviewed")
                        else:
                            source["rights_reviewed"] = review
                        (base/"assets.json").write_text(json.dumps(data))
                        with self.assertRaisesRegex(ValueError,"not qualified"):
                            build_binder.load_entry(base.name,"final")

        context, base = self.fixture()
        with context:
            build_binder.load_entry(base.name, "final")

    def test_tex_special_asset_paths(self):
        for filename, rejected in (("ordinary.jpg", False), ("photo#1.jpg", True), ("photo%crop.jpg", True)):
            with self.subTest(filename=filename):
                context, base = self.fixture()
                with context:
                    data = json.loads((base / "assets.json").read_text(encoding="utf-8"))
                    old_path = base / data["assets"][0]["path"]
                    new_path = base / "assets" / filename
                    old_path.rename(new_path)
                    data["assets"][0]["path"] = f"assets/{filename}"
                    (base / "assets.json").write_text(json.dumps(data), encoding="utf-8")
                    if rejected:
                        with self.assertRaisesRegex(ValueError, "unsupported TeX characters"):
                            build_binder.load_entry(base.name, "final")
                    else:
                        build_binder.load_entry(base.name, "final")

        for prefix in ("entry#", "entry%"):
            with self.subTest(entry_directory=prefix):
                context, base = self.fixture(prefix=prefix)
                with context, self.assertRaisesRegex(ValueError, "unsupported TeX characters"):
                    build_binder.load_entry(base.name, "final")

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
