from __future__ import annotations

import json
import tempfile
import unittest
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from unittest import mock
from pathlib import Path
from PIL import Image

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_binder  # noqa: E402
import prepare_binder_photo  # noqa: E402


SAFE_TEXT_RECT = (72.0, 39.6, 572.4, 752.4)
# Poppler occasionally reports a glyph a few thousandths of a point beyond the
# right boundary.  No vertical tolerance is permitted: the bottom defect this
# check guards against was real layout overflow, not extraction noise.
RIGHT_EXTRACTION_TOLERANCE = 0.01


def _rendered_text_bounds(pdf):
    """Extract per-page top-origin word bounds with the pinned Poppler tool."""
    with tempfile.TemporaryDirectory() as name:
        bbox = Path(name) / "bbox.html"
        subprocess.run(
            ["pdftotext", "-bbox-layout", str(pdf), str(bbox)],
            check=True,
            capture_output=True,
            text=True,
        )
        root = ET.parse(bbox).getroot()
    pages = []
    for page in root.iter("{http://www.w3.org/1999/xhtml}page"):
        words = list(page.iter("{http://www.w3.org/1999/xhtml}word"))
        if not words:
            raise AssertionError("rendered page contains no extractable words")
        pages.append((
            min(float(word.attrib["xMin"]) for word in words),
            min(float(word.attrib["yMin"]) for word in words),
            max(float(word.attrib["xMax"]) for word in words),
            max(float(word.attrib["yMax"]) for word in words),
        ))
    return pages


def _assert_rendered_text_inside_safe_area(pdf):
    left, top, right, bottom = SAFE_TEXT_RECT
    bounds = _rendered_text_bounds(pdf)
    for page_number, (x_min, y_min, x_max, y_max) in enumerate(bounds, 1):
        if not (x_min >= left and y_min >= top and
                x_max <= right + RIGHT_EXTRACTION_TOLERANCE and y_max <= bottom):
            raise AssertionError(
                f"page {page_number} text bounds {(x_min, y_min, x_max, y_max)} "
                f"outside safe rectangle {SAFE_TEXT_RECT}"
            )
    return bounds


def _log_row_cells(row_anchors, column_anchors, field_positions):
    """Assign every extracted label to one non-overlapping rendered cell."""
    rows = sorted(row_anchors, reverse=True)
    # Date baselines are row starts, not row centers.  A row owns everything
    # below its Date baseline down to (but not including) the next baseline.
    boundaries = rows[1:]
    cells = [[Counter() for _ in column_anchors] for _ in rows]
    for label, x, y in field_positions:
        column = min(range(len(column_anchors)), key=lambda index: abs(x - column_anchors[index]))
        row = next((index for index, boundary in enumerate(boundaries) if y > boundary + 1), len(rows) - 1)
        cells[row][column][label] += 1
    return cells


def _assert_log_row_cells(row_anchors, column_anchors, field_positions, expected_fields):
    cells = _log_row_cells(row_anchors, column_anchors, field_positions)
    for row, row_cells in enumerate(cells):
        for column, found in enumerate(row_cells):
            expected = Counter(expected_fields[column])
            if found != expected:
                raise AssertionError(
                    f"row {row + 1}, column {column + 1}: expected {expected}, found {found}"
                )


def _painted_pdf_geometry(page):
    """Return painted image and stroked-path boxes from a PDF page."""
    resources = page["/Resources"]
    xobjects = resources.get("/XObject", {})
    ctm = (1, 0, 0, 1, 0, 0)
    stack = []
    path = []
    images = []
    strokes = []

    def transform(point):
        x, y = point
        a, b, c, d, e, f = ctm
        return (a * x + c * y + e, b * x + d * y + f)

    def bounds(points):
        xs, ys = zip(*points)
        return (min(xs), min(ys), max(xs), max(ys))

    for operands, operator in page.get_contents().operations:
        if operator == b"q":
            stack.append(ctm)
        elif operator == b"Q":
            ctm = stack.pop()
        elif operator == b"cm":
            values = [float(value) for value in operands]
            a, b, c, d, e, f = values
            ca, cb, cc, cd, ce, cf = ctm
            ctm = (
                ca * a + cc * b, cb * a + cd * b,
                ca * c + cc * d, cb * c + cd * d,
                ca * e + cc * f + ce, cb * e + cd * f + cf,
            )
        elif operator in (b"m", b"l"):
            values = [float(value) for value in operands]
            path.append(transform(values[:2]))
        elif operator == b"re":
            values = [float(value) for value in operands]
            x, y, width, height = values
            path.extend(transform(point) for point in (
                (x, y), (x + width, y), (x + width, y + height), (x, y + height)
            ))
        elif operator in (b"c", b"v", b"y"):
            values = [float(value) for value in operands]
            path.extend(transform(values[index:index + 2]) for index in range(0, len(values), 2))
        elif operator in (b"S", b"s", b"B", b"B*", b"b", b"b*"):
            if path:
                strokes.append(bounds(path))
            path = []
        elif operator in (b"f", b"f*"):
            path = []
        elif operator == b"n":
            path = []
        elif operator == b"Do":
            name = operands[0]
            xobject = xobjects.get(name)
            if xobject is not None and xobject.get_object().get("/Subtype") == "/Image":
                images.append(bounds([transform(point) for point in ((0, 0), (1, 0), (1, 1), (0, 1))]))
    return images, strokes


def _assert_watering_log_text_contract(text):
    """Check extraction-stable watering-log headings and row-key meanings."""
    compact = re.sub(r"\s+", "", text)
    expected_key = (
        "D=date;T=time;A/M=amountormethod;Obs=observation;"
        "Rain=rain/amount;Evt=aquariumevent;A/R=amountorresult."
    )
    if expected_key not in compact:
        raise AssertionError("watering-log row key does not preserve every abbreviation mapping")
    if "Date/time" not in compact:
        raise AssertionError("watering-log leftmost header must be Date / time")


def _assert_optional_detail_rendering(page, detail_count):
    images, strokes = _painted_pdf_geometry(page)
    image_sizes = [(box[2] - box[0], box[3] - box[1]) for box in images]
    if len(image_sizes) != 1 + detail_count:
        raise AssertionError(f"expected {1 + detail_count} painted images, found {len(image_sizes)}")
    if sum(width > 230 and height > 230 for width, height in image_sizes) != 1:
        raise AssertionError("expected exactly one painted hero image")
    painted_details = sum(
        145 < width < 150 and 95 < height < 100 for width, height in image_sizes
    )
    detail_images = [
        box for box in images
        if 145 < box[2] - box[0] < 150 and 95 < box[3] - box[1] < 100
    ]
    # TikZ emits the template frame as four separately stroked edges.  Fold
    # those edges into a rectangle while retaining support for a single `re`
    # stroke, as used by the unwanted-empty-frame regression below.
    frames = [
        box for box in strokes
        if 146 < box[2] - box[0] < 150 and 96 < box[3] - box[1] < 100
    ]
    horizontal = [box for box in strokes if 146 < box[2] - box[0] < 150 and box[3] - box[1] < .2]
    vertical = [box for box in strokes if box[2] - box[0] < .2 and 96 < box[3] - box[1] < 100]
    for bottom in horizontal:
        for top in horizontal:
            candidate = (bottom[0], bottom[1], bottom[2], top[1])
            if not 96 < candidate[3] - candidate[1] < 100:
                continue
            if any(
                abs(left[0] - candidate[0]) < .5
                and abs(left[1] - candidate[1]) < .5
                and abs(left[3] - candidate[3]) < .5
                for left in vertical
            ) and any(
                abs(right[0] - candidate[2]) < .5
                and abs(right[1] - candidate[1]) < .5
                and abs(right[3] - candidate[3]) < .5
                for right in vertical
            ):
                frames.append(candidate)
    frames = list({tuple(round(value, 1) for value in frame) for frame in frames})
    if (
        painted_details != detail_count
        or len(detail_images) != detail_count
        or len(frames) != detail_count
        or any(
            not any(all(abs(a - b) < 1 for a, b in zip(frame, image)) for frame in frames)
            for image in detail_images
        )
    ):
        raise AssertionError(
            f"expected {detail_count} painted details/frames, "
            f"found {painted_details}/{len(frames)}"
        )


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

    def test_synthetic_owned_reviewed_photograph_passes_final_validation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "binder" / "entries") as name:
            base = Path(name)
            (base / "assets").mkdir()
            Image.new("RGB", (990, 990), "#597267").save(base / "assets" / "hero.jpg")
            record = {
                "id": "owned-hero", "path": "assets/hero.jpg", "kind": "photograph",
                "subjects": ["synthetic plant"], "alt": "Synthetic owned plant photograph.",
                "caption": "Synthetic owned fixture.",
                "source": {"photographer": "test suite", "provenance": "generated fixture",
                           "rights": "owned test fixture", "rights_reviewed": True},
            }
            (base / "assets.json").write_text(json.dumps({"schema_version": 1, "assets": [record]}))
            (base / "page.tex").write_text("% binder-placement hero owned-hero; test\n")
            _, records, selected = build_binder.load_entry(base.name, "final")
            self.assertEqual(selected, {"hero": "owned-hero"})
            self.assertTrue(records["owned-hero"]["source"]["rights_reviewed"])


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

    def test_page_validation_rejects_shifted_crop_blank_and_rotation(self):
        class Box:
            def __init__(self, coordinates):
                self.lower_left = coordinates[:2]
                self.upper_right = coordinates[2:]

        class Page:
            mediabox = Box((0, 0, 612, 792))
            cropbox = Box((0, 0, 612, 792))

            def __init__(self, text="substantive page content " * 6, rotation=0, crop=None, media=None):
                self.text = text
                self.rotation = rotation
                if crop:
                    self.cropbox = Box(crop)
                if media:
                    self.mediabox = Box(media)

            def get(self, key):
                return self.rotation if key == "/Rotate" else None

            def extract_text(self):
                return self.text

        build_binder._validate_page(Page(), "valid")
        build_binder._validate_page(
            Page(text=("x " * build_binder.MIN_EXTRACTED_PAGE_CHARACTERS)),
            "threshold with normalized whitespace",
        )
        for page, message in (
            (Page(crop=(20, 20, 632, 812)), "geometry"),
            (Page(media=(0, 0, 600, 792)), "geometry"),
            (Page(text=" \n\t"), "blank"),
            (Page(text="page 1"), "near-blank"),
            (Page(text="Watering & aquarium log"), "near-blank"),
            (Page(text="DRAFT PLACEHOLDER\nhero-placeholder-001"), "near-blank"),
            (Page(text="x" * (build_binder.MIN_EXTRACTED_PAGE_CHARACTERS - 1)), "near-blank"),
            (Page(rotation=90), "rotation"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(RuntimeError, message):
                build_binder._validate_page(page, "invalid")

    def test_removed_entry_cannot_reduce_combined_expected_page_count(self):
        original = json.loads((ROOT / "binder" / "manifest.yaml").read_text())
        original["entries"].pop()
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            manifest = root / "binder" / "manifest.yaml"
            manifest.parent.mkdir()
            manifest.write_text(json.dumps(original))
            with mock.patch.object(build_binder, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "canonical six-entry"):
                    build_binder.compile_manifest(manifest, "draft", root / "short.pdf")

    def test_supplemental_rejects_final_mode(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "watering-log.pdf"
            with self.assertRaisesRegex(ValueError, "only in draft mode"):
                build_binder.compile_supplemental("watering-log", "final", output)
            self.assertFalse(output.exists())

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
            _assert_watering_log_text_contract(log_text)
            for original, replacement in (
                ("D = date; T = time", "D = time; T = date"),
                ("Date / time", "Session"),
            ):
                mutated = log_text.replace(original, replacement)
                self.assertNotEqual(mutated, log_text)
                with self.assertRaises(AssertionError):
                    _assert_watering_log_text_contract(mutated)
            for text in (
                "Sedum", "Kalanchoe", "Pothos", "Bird of paradise",
                "Hornwort", "Planning estimate only", "rain/amount",
                "Watering interval:", "N/A", "Aquarium maintenance", "not watering",
                "aquarium event", "amount or result", "observation", "date", "time",
                "amount or method", "outdoor", "grow bag",
                "indoors", "aquarium",
            ):
                self.assertIn(text, log_text)
            # TeX Gyre Heros kerning can make Poppler/pypdf expose this header
            # as "T ypical"; assert the words while tolerating that extractor
            # artifact rather than coupling the contract to one PDF parser.
            self.assertEqual(len(re.findall(r"T\s*ypical interval:", log_text)), 4)
            self.assertEqual(len(re.findall(r"_+\s*days", log_text)), 4)
            self.assertRegex(log_text, r"Hornwort[\s\S]*Watering interval:\s*N/A")
            labels = {"D", "T", "A/M", "Obs", "Rain", "Evt", "A/R"}
            sizes = []
            date_positions = []
            aquarium_observation_positions = []
            field_positions = []
            header_positions = {}

            def inspect_text(text, _cm, tm, _font, font_size):
                stripped = text.strip()
                if stripped in labels:
                    sizes.append(font_size)
                    field_positions.append((stripped, tm[4], tm[5]))
                if stripped == "D":
                    date_positions.append(tm[5])
                if stripped == "Obs" and tm[4] > 430:
                    aquarium_observation_positions.append(tm[5])
                if stripped in {
                    "Date / time", "Sedum", "Kalanchoe", "Pothos",
                    "Bird of paradise", "Hornwort",
                }:
                    header_positions[stripped] = tm[4]

            log_reader.pages[0].extract_text(visitor_text=inspect_text)
            counts = Counter(label for label, _, _ in field_positions)
            self.assertEqual(counts, Counter({
                "D": 14, "T": 14, "Evt": 14, "A/R": 14,
                "Rain": 28, "A/M": 56, "Obs": 70,
            }))
            self.assertEqual(
                sorted(header_positions, key=header_positions.get),
                ["Date / time", "Sedum", "Kalanchoe", "Pothos", "Bird of paradise", "Hornwort"],
            )
            self.assertEqual(min(header_positions, key=header_positions.get), "Date / time")
            self.assertTrue(sizes)
            # LuaLaTeX's PDF conversion exposes requested 8 pt labels as about
            # 7.97011 points. Keep that explicit tolerance without weakening
            # the design's physical 8 pt request.
            self.assertGreaterEqual(min(sizes), 7.9)
            self.assertAlmostEqual(min(sizes), 7.97011, delta=0.01)
            row_tops = sorted(set(round(position, 1) for position in date_positions), reverse=True)
            self.assertEqual(len(row_tops), 14)
            self.assertGreaterEqual(min(a - b for a, b in zip(row_tops, row_tops[1:])), 34.56)
            self.assertEqual(len(aquarium_observation_positions), 14)

            # On the pinned, supported LuaHBTeX 1.17.0 engine, all 210
            # handwriting rules are emitted as stroked paths. Exact quantity
            # is intentional: missing rules must fail rather than be hidden by
            # speculative handling for unsupported PDF backends.
            _, strokes = _painted_pdf_geometry(log_reader.pages[0])
            writing_rules = [
                box for box in strokes
                if box[3] - box[1] < .2 and 32.4 <= box[2] - box[0] < 100
            ]
            self.assertEqual(len(writing_rules), 14 * 15)
            self.assertGreaterEqual(min(box[2] - box[0] for box in writing_rules), 32.4)

            # Establish the six rendered columns from their label x positions,
            # then verify every one of the 14 row/column regions independently.
            x_positions = sorted({round(x, 1) for _, x, _ in field_positions})
            self.assertEqual(len(x_positions), 6)
            expected_fields = (
                {"D", "T"},
                {"A/M", "Obs", "Rain"},
                {"A/M", "Obs", "Rain"},
                {"A/M", "Obs"},
                {"A/M", "Obs"},
                {"Evt", "A/R", "Obs"},
            )
            _assert_log_row_cells(row_tops, x_positions, field_positions, expected_fields)

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

    def test_log_row_regions_reject_adjacent_field_borrowing(self):
        rows = [606.8, 567.7, 528.6, 489.5]
        columns = [10.0, 20.0]
        expected = ({"Date:"}, {"Observation:"})
        positions = []
        for y in rows:
            positions.extend((
                ("Date:", columns[0], y),
                ("Observation:", columns[1], y - 20.9),
            ))
        _assert_log_row_cells(rows, columns, positions, expected)

        # Preserve global counts while moving an aquarium Observation into an
        # adjacent row. Exercise both outer rows so neither can borrow a label.
        for source, destination in ((0, 1), (3, 2)):
            mutated = list(positions)
            occurrence = ("Observation:", columns[1], rows[source] - 20.9)
            index = mutated.index(occurrence)
            mutated[index] = ("Observation:", columns[1], rows[destination] - 20.9)
            self.assertEqual(Counter(label for label, _, _ in mutated),
                             Counter(label for label, _, _ in positions))
            cells = _log_row_cells(rows, columns, mutated)
            self.assertEqual(cells[source][1]["Observation:"], 0)
            self.assertEqual(cells[destination][1]["Observation:"], 2)
            with self.assertRaisesRegex(AssertionError, r"row [1-4], column 2"):
                _assert_log_row_cells(rows, columns, mutated, expected)

    @unittest.skipUnless(shutil.which("lualatex"), "lualatex unavailable")
    def test_every_profile_builds_independently_with_complete_visible_content(self):
        from pypdf import PdfReader

        headings = {
            "sedum-loves-fire": ("Sedum", "LIGHT / EXPOSURE", "SOIL / SUBSTRATE", "WATER", "TEMPERATURE / SEASON", "FEEDING / MAINTENANCE", "PROPAGATION", "TROUBLESHOOTING", "NATURAL HISTORY / TRIVIA"),
            "kalanchoe-desert": ("Kalanchoe", "LIGHT / EXPOSURE", "SOIL / SUBSTRATE", "WATER", "TEMPERATURE / SEASON", "FEEDING / MAINTENANCE", "PROPAGATION", "TROUBLESHOOTING", "NATURAL HISTORY / TRIVIA"),
            "pothos": ("Pothos", "LIGHT / EXPOSURE", "SOIL / SUBSTRATE", "WATER", "TEMPERATURE / SEASON", "FEEDING / MAINTENANCE", "PROPAGATION", "TROUBLESHOOTING", "NATURAL HISTORY / TRIVIA"),
            "bird-of-paradise": ("Bird of paradise", "LIGHT / EXPOSURE", "SOIL / SUBSTRATE", "WATER", "TEMPERATURE / SEASON", "FEEDING / MAINTENANCE", "PROPAGATION", "TROUBLESHOOTING", "NATURAL HISTORY / TRIVIA"),
            "aquarium-hornwort": ("Aquarium hornwort", "LIGHT", "WATER PARAMETERS / TEMPERATURE", "PLACEMENT / FLOATING", "NUTRIENT CONTEXT", "GROWTH / TRIMMING", "PROPAGATION", "COMPATIBILITY / TROUBLESHOOTING", "NATURAL HISTORY / TRIVIA"),
        }
        propagation_evidence = {
            "sedum-loves-fire": (("stem cutting", "lower leaves", "callus", "rot"), ("SED-POWO", "SED-PAT", "SED-MSU", "SED-IA")),
            "kalanchoe-desert": (("stem section", "lower leaves", "well-drained", "rot"), ("KAL-RHS", "KAL-IA", "KAL-PROP")),
            "pothos": (("stem piece", "node", "bud", "foliage above water"), ("POT-NCSU", "POT-PSU", "POT-WISC", "POT-NCSU-PROP")),
            "bird-of-paradise": (("divide", "shoot", "original depth", "soggy"), ("BOP-REG", "BOP-NIC", "BOP-UF")),
            "aquarium-hornwort": (("method", "plant fragment", "below the surface", "broken stems"), ("HOR-FWS", "HOR-WA", "HOR-TROP")),
        }

        def assert_extracted_phrase(phrase, text):
            # PDF extraction preserves discretionary line-break hyphens and
            # whitespace. Normalize those artifacts without weakening the
            # profile-specific prose evidence being checked.
            if re.fullmatch(r"[A-Z]{3}(?:-[A-Z0-9]+)+", phrase):
                # TeX may wrap only at a key's existing hyphens. Preserve the
                # key itself while accepting whitespace introduced there.
                pattern = re.escape(phrase).replace(r"\-", r"\-\s*")
                self.assertRegex(text, pattern)
                return
            normalized = re.sub(r"-\s+", "", text)
            normalized = re.sub(r"\s+", " ", normalized)
            self.assertIn(phrase, normalized)

        def assert_profile_evidence(slug, text):
            guidance, source_keys = propagation_evidence[slug]
            for marker in (*headings[slug], *guidance, *source_keys, "EVIDENCE", "REVISION"):
                assert_extracted_phrase(marker, text)

        # Pin the two observed extractor wraps and ensure normalization does
        # not allow genuinely absent guidance to satisfy the assertion.
        assert_extracted_phrase("After establishment", "After estab-\nlishment")
        assert_extracted_phrase("below the surface", "below the sur-\nface")
        with self.assertRaises(AssertionError):
            assert_extracted_phrase("After establishment", "PROPAGATION [POT-NCSU]")

        with tempfile.TemporaryDirectory() as name:
            for slug, required in headings.items():
                with self.subTest(entry=slug):
                    output = Path(name) / f"{slug}.pdf"
                    base, records, selected = build_binder.load_entry(slug, "draft")
                    build_binder.compile_entry(base, records, selected, output)
                    reader = PdfReader(output)
                    self.assertEqual(len(reader.pages), 1)
                    page = reader.pages[0]
                    build_binder._validate_page(page, slug)
                    text = page.extract_text()
                    assert_profile_evidence(slug, text)
                    if any(records[asset_id]["kind"] == "placeholder"
                           for asset_id in selected.values()):
                        self.assertIn("DRAFT PLACEHOLDER", text)
                    if slug == "aquarium-hornwort":
                        self.assertNotIn("SOIL / SUBSTRATE", text)
                        self.assertNotIn("Water thoroughly", text)

            # A heading and citation alone must not masquerade as a rendered
            # propagation contract. Work only on a temporary entry copy.
            source = ROOT / "binder" / "entries" / "pothos"
            with tempfile.TemporaryDirectory(dir=ROOT / "binder" / "entries") as temp_entry:
                mutant = Path(temp_entry)
                shutil.copytree(source / "assets", mutant / "assets")
                shutil.copy(source / "assets.json", mutant / "assets.json")
                page = (source / "page.tex").read_text(encoding="utf-8")
                page = re.sub(
                    r"(\{PROPAGATION\}\{).*?(\\textbf\{\[POT-NCSU-PROP; POT-WISC\]\}\})",
                    r"\1Citation retained only. \2",
                    page,
                    count=1,
                )
                (mutant / "page.tex").write_text(page, encoding="utf-8")
                output = Path(name) / "pothos-missing-propagation.pdf"
                build_binder.compile_entry(*build_binder.load_entry(mutant.name, "draft"), output)
                text = PdfReader(output).pages[0].extract_text()
                self.assertIn("PROPAGATION", text)
                self.assertIn("POT-NCSU-PROP", text)
                with self.assertRaises(AssertionError):
                    assert_profile_evidence("pothos", text)


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

    @unittest.skipUnless(shutil.which("lualatex") and shutil.which("pdftotext"),
                         "LuaLaTeX and Poppler unavailable")
    def test_rendered_text_stays_inside_safe_area_and_rejects_bottom_violation(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "binder.pdf"
            build_binder.compile_manifest(
                ROOT / "binder" / "manifest.yaml", "draft", output
            )
            bounds = _assert_rendered_text_inside_safe_area(output)
            self.assertEqual(len(bounds), 6)

        # Place extractable text deliberately in the protected bottom margin.
        # Overlaying it avoids pagination/overfull guards, so this specifically
        # proves the rendered safe-area check catches the violation.
        context, base = self.fixture(page_suffix=(
            r"\begin{tikzpicture}[remember picture,overlay]"
            r"\node[anchor=south] at ([yshift=12pt]current page.south)"
            r"{BOTTOM SAFE MARGIN VIOLATION};\end{tikzpicture}"
        ))
        with context:
            output = base / "bottom-violation.pdf"
            build_binder.compile_entry(
                *build_binder.load_entry(base.name, "final"), output
            )
            with self.assertRaisesRegex(AssertionError, "outside safe rectangle"):
                _assert_rendered_text_inside_safe_area(output)

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
                _assert_optional_detail_rendering(reader.pages[0], count)

        # Resource counts and placement declarations cannot detect an empty
        # vector frame. Inspect painted path geometry and reject one directly.
        context, base = self.fixture(
            0, page_suffix=r"\tikz[overlay]{\draw (0,0) rectangle (2.05in,1.35in);}"
        )
        with context:
            output = base / "empty-frame.pdf"
            build_binder.compile_entry(*build_binder.load_entry(base.name, "final"), output)
            page = PdfReader(output).pages[0]
            with self.assertRaisesRegex(AssertionError, "painted details/frames"):
                _assert_optional_detail_rendering(page, 0)

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
    def test_overfull_box_is_rejected_independently(self):
        context, base = self.fixture(page_suffix=r"\par\noindent\hbox to 1pt{WWWWW}\par")
        with context, self.assertRaisesRegex(RuntimeError, "overfull"):
            build_binder.compile_entry(*build_binder.load_entry(base.name, "final"), base / "bad.pdf")

    @unittest.skipUnless(shutil.which("lualatex"), "lualatex unavailable")
    def test_unexpected_page_count_is_rejected_independently(self):
        context, base = self.fixture(page_suffix=r"\newpage SECOND PAGE")
        with context, self.assertRaisesRegex(RuntimeError, r"rendered 2 pages, expected 1"):
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
            cases.append(({"schema_version":2,"assets":[]}, "schema_version"))
            bad=json.loads(json.dumps(original)); bad["assets"][0]["alt"]=""; cases.append((bad,"nonempty"))
            bad=json.loads(json.dumps(original)); bad["assets"][0]["subjects"]="plant"; cases.append((bad,"subjects"))
            bad=json.loads(json.dumps(original)); del bad["assets"][0]["caption"]; cases.append((bad,"missing required metadata"))
            bad=json.loads(json.dumps(original)); del bad["assets"][0]["source"]["rights"]; cases.append((bad,"missing source metadata"))
            bad=json.loads(json.dumps(original)); bad["assets"][0]["source"]["photographer"]=""; cases.append((bad,"nonempty"))
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

    def test_missing_asset_file_is_rejected_independently_of_containment(self):
        context, base = self.fixture()
        with context:
            data = json.loads((base / "assets.json").read_text())
            data["assets"][0]["path"] = "assets/does-not-exist.jpg"
            (base / "assets.json").write_text(json.dumps(data))
            self.assertFalse(base.joinpath("assets/does-not-exist.jpg").exists())
            with self.assertRaisesRegex(ValueError, "asset path must resolve within entry"):
                build_binder.load_entry(base.name, "draft")

    def test_unsupported_raster_format_and_wrong_aspect_are_rejected(self):
        for image_format, size, message in (("GIF", (990, 990), "unsupported raster format"),
                                            ("JPEG", (1000, 990), "aspect ratio")):
            with self.subTest(image_format=image_format, size=size):
                context, base = self.fixture()
                with context:
                    data = json.loads((base / "assets.json").read_text())
                    path = base / data["assets"][0]["path"]
                    Image.new("RGB", size).save(path, format=image_format)
                    with self.assertRaisesRegex(ValueError, message):
                        build_binder.load_entry(base.name, "final")

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

    def test_rights_review_guard_is_independent_of_resolved_rights(self):
        for value in ("missing", False, "true", 1, None, True):
            with self.subTest(rights_reviewed=value):
                context, base = self.fixture()
                with context:
                    data = json.loads((base / "assets.json").read_text())
                    source = data["assets"][0]["source"]
                    if value == "missing":
                        source.pop("rights_reviewed")
                    else:
                        source["rights_reviewed"] = value
                    (base / "assets.json").write_text(json.dumps(data))
                    if value is True:
                        build_binder.load_entry(base.name, "final")
                    else:
                        with self.assertRaisesRegex(ValueError, "not qualified"):
                            build_binder.load_entry(base.name, "final")

    def test_reviewed_resolved_placeholder_is_still_rejected(self):
        context, base = self.fixture()
        with context:
            data = json.loads((base / "assets.json").read_text())
            record = data["assets"][0]
            record.update(kind="placeholder", path="assets/placeholder.txt")
            (base / "assets/placeholder.txt").write_text("synthetic")
            (base / "assets.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "not qualified"):
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
