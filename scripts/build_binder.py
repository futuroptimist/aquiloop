#!/usr/bin/env python3
"""Build individual binder pages or an ordered draft binder manifest."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from binder_evidence import ANIMAL_PAGE_KINDS, load_animal, load_companions
from binder_logs import tracked_species, paginate_species, log_page_tex

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"id", "path", "kind", "subjects", "alt", "caption", "source"}
SOURCE_REQUIRED = {"photographer", "provenance", "rights"}
KINDS = {"photograph", "placeholder"}
ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLACEMENT = re.compile(r"^% binder-placement (hero|detail1|detail2) ([a-z0-9]+(?:-[a-z0-9]+)*);(?: .+)?$")
UNRESOLVED_RIGHTS = {"unknown", "pending", "unresolved", "permission requested", "tbd", "not reviewed", "permission denied"}
UNSAFE_TEX_PATH_CHARS = frozenset("#%{}\\\r\n")
# A title or placeholder can easily contribute a few dozen extracted characters;
# require enough text to demonstrate that the page's substantive body survived.
MIN_EXTRACTED_PAGE_CHARACTERS = 100
EXPECTED_MANIFEST = (
    ("sedum-loves-fire", "profile"),
    ("kalanchoe-desert", "profile"),
    ("pothos", "profile"),
    ("bird-of-paradise", "profile"),
    ("aquarium-hornwort", "profile"),
    ("watering-log", "supplemental"),
)
EXPECTED_EXPANDED_MANIFEST = tuple(
    (entry, kind)
    for entry, _ in EXPECTED_MANIFEST[:-1]
    for kind in ("profile", "numbers", "propagation")
) + (("watering-log", "supplemental"),)
EXPECTED_ANIMAL_MANIFEST = EXPECTED_EXPANDED_MANIFEST[:-1] + tuple(
    ("kuhli-loach", kind) for kind in ANIMAL_PAGE_KINDS
) + (EXPECTED_EXPANDED_MANIFEST[-1],)
EXPECTED_SHRIMP_MANIFEST = EXPECTED_ANIMAL_MANIFEST[:-1] + tuple(
    ("cherry-shrimp", kind) for kind in ANIMAL_PAGE_KINDS
) + (EXPECTED_ANIMAL_MANIFEST[-1],)
AQUATIC_PLANT_ENTRIES = ("guppy-grass", "java-moss", "anubias-nana")
EXPECTED_AQUATIC_MANIFEST = EXPECTED_SHRIMP_MANIFEST[:-1] + tuple(
    (entry, kind) for entry in AQUATIC_PLANT_ENTRIES
    for kind in ("profile", "numbers", "propagation")
) + (EXPECTED_SHRIMP_MANIFEST[-1],)
EXPECTED_LOG_MANIFEST = EXPECTED_AQUATIC_MANIFEST[:-1] + (
    ("watering-log-tracked", "supplemental"),
    ("watering-log-blank", "supplemental"),
)
SUCCULENT_ENTRIES = ("pachyveria-powder-puff", "crassula-rupestris")
EXPECTED_SUCCULENT_MANIFEST = EXPECTED_AQUATIC_MANIFEST[:-1] + tuple(
    (entry, kind) for entry in SUCCULENT_ENTRIES
    for kind in ("profile", "numbers", "propagation")
) + EXPECTED_LOG_MANIFEST[-2:]
CATEGORY_BY_ENTRY = {
    **{entry: "TERRESTRIAL PLANT" for entry in SUCCULENT_ENTRIES},
    **{entry: "TERRESTRIAL PLANT" for entry, _ in EXPECTED_MANIFEST[:4]},
    **{entry: "AQUATIC PLANT" for entry in ("aquarium-hornwort", *AQUATIC_PLANT_ENTRIES)},
    "kuhli-loach": "AQUATIC ANIMAL", "cherry-shrimp": "AQUATIC ANIMAL",
}
COMPANION_LABELS = {"numbers": "NUMBERS & PACIFICA", "propagation": "PROPAGATION",
                    "animal-care": "ANIMAL CARE", "tank-setup": "TANK SETUP",
                    "reproduction": "REPRODUCTION"}


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load_entry(entry: str, mode: str, *, layout_name: str = "page.tex") -> tuple[Path, dict[str, dict], dict[str, str]]:
    if layout_name not in {"page.tex", "animal-care.tex"}:
        raise ValueError("unsupported asset-bearing layout")
    entries = (ROOT / "binder" / "entries").resolve()
    base = (entries / entry).resolve()
    if entries not in base.parents or not base.is_dir():
        raise ValueError(f"unknown entry: {entry}")
    # Current production profiles remain provisional; future publication
    # qualification is intentionally deferred rather than encoded in content.
    provisional_profiles = {
        (entries / entry_id).resolve()
        for entry_id, kind in EXPECTED_SUCCULENT_MANIFEST
        if kind == "profile"
    }
    if mode == "final" and base in provisional_profiles:
        raise ValueError(f"production profile {base.name} remains provisional and cannot be built in final mode")
    catalog = json.loads((base / "assets.json").read_text(encoding="utf-8"))
    if not isinstance(catalog, dict):
        raise ValueError("assets.json must contain an object")
    if catalog.get("schema_version") != 1:
        raise ValueError("assets.json must use supported schema_version 1")
    assets = catalog.get("assets")
    if not isinstance(assets, list):
        raise ValueError("assets must be an array")
    records: dict[str, dict] = {}
    for record in assets:
        if not isinstance(record, dict):
            raise ValueError("each asset must be an object")
        missing = REQUIRED - record.keys()
        if missing:
            raise ValueError(f"asset missing required metadata: {sorted(missing)}")
        asset_id = record["id"]
        if not _nonempty(asset_id) or not ID.fullmatch(asset_id):
            raise ValueError(f"malformed asset ID: {asset_id!r}")
        if asset_id in records:
            raise ValueError(f"duplicate asset ID: {asset_id}")
        if record["kind"] not in KINDS:
            raise ValueError(f"asset {asset_id} has unsupported kind: {record['kind']}")
        for key in ("path", "alt", "caption"):
            if not _nonempty(record[key]):
                raise ValueError(f"asset {asset_id} {key} must be a nonempty string")
        if not isinstance(record["subjects"], list) or not record["subjects"] or not all(_nonempty(x) for x in record["subjects"]):
            raise ValueError(f"asset {asset_id} subjects must be a nonempty string array")
        source = record["source"]
        if not isinstance(source, dict):
            raise ValueError(f"asset {asset_id} source metadata must be an object")
        missing = SOURCE_REQUIRED - source.keys()
        if missing:
            raise ValueError(f"asset {asset_id} missing source metadata: {sorted(missing)}")
        for key in SOURCE_REQUIRED:
            if not _nonempty(source[key]):
                raise ValueError(f"asset {asset_id} source.{key} must be a nonempty string")
        path = (base / record["path"]).resolve()
        if base not in path.parents or not path.is_file():
            raise ValueError(f"asset path must resolve within entry: {record['path']}")
        records[asset_id] = record

    selected: dict[str, str] = {}
    for line in (base / layout_name).read_text(encoding="utf-8").splitlines():
        if line.startswith("% binder-placement"):
            match = PLACEMENT.fullmatch(line)
            if not match:
                raise ValueError(f"malformed placement declaration: {line}")
            role, asset_id = match.groups()
            if role in selected:
                raise ValueError(f"duplicate placement declaration: {role}")
            selected[role] = asset_id
    if "hero" not in selected:
        raise ValueError("page must select one hero")
    for role, asset_id in selected.items():
        if asset_id not in records:
            raise ValueError(f"selected {role} references unknown asset: {asset_id}")
        record = records[asset_id]
        rights = record["source"]["rights"].strip().casefold()
        if mode == "final" and (record["kind"] == "placeholder" or
                                record["source"].get("rights_reviewed") is not True or
                                rights in UNRESOLVED_RIGHTS):
            raise ValueError(f"selected asset {asset_id} is not qualified for final mode")
        if record["kind"] == "placeholder":
            continue
        path = (base / record["path"]).resolve()
        if any(char in path.as_posix() for char in UNSAFE_TEX_PATH_CHARS):
            raise ValueError(f"asset path contains unsupported TeX characters: {record['path']}")
        try:
            from PIL import Image
            with Image.open(path) as image:
                width, height, image_format = image.width, image.height, image.format
                if entry in SUCCULENT_ENTRIES:
                    if path.stat().st_size >= 100000:
                        raise ValueError("new succulent images must be strictly under 100000 bytes")
                    if image_format != "JPEG" or width != height:
                        raise ValueError("new succulent photographs must be square JPEGs")
                    if image.getexif() or any(marker != "APP0" for marker, _ in image.applist):
                        raise ValueError("new succulent photographs must have no embedded metadata except JFIF")
                image.verify()
        except (ImportError, OSError) as exc:
            raise ValueError(f"cannot measure raster asset {asset_id}: {exc}") from exc
        if image_format not in {"JPEG", "PNG"}:
            raise ValueError(f"unsupported raster format for {asset_id}: {image_format}")
        if path.stat().st_size > 1024 * 1024:
            raise ValueError(f"raster asset {asset_id} exceeds 1 MiB")
        required = (792, 792) if role == "hero" else (492, 324)
        if width < required[0] or height < required[1]:
            raise ValueError(f"selected {role} {asset_id} is below {required[0]} x {required[1]} px")
        ratio = 1 if role == "hero" else 2.05 / 1.35
        if abs(width / height - ratio) > .005:
            raise ValueError(f"selected {role} {asset_id} aspect ratio does not match its frame; prepare an exact crop")
        print(f"asset {asset_id}: {width} x {height} px, {image_format}, {path.stat().st_size} bytes")
    return base, records, selected


def compile_entry(base: Path, records: dict[str, dict], selected: dict[str, str], output: Path,
                  *, kind: str = "profile", expanded: bool = False, category: str | None = None,
                  page_text_override: str | None = None) -> None:
    if not shutil.which("lualatex"):
        raise RuntimeError("lualatex is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="binder-") as tmp_name:
        tmp = Path(tmp_name)
        template = "companion-template.tex" if kind in COMPANION_LABELS else "template.tex"
        shutil.copyfile(ROOT / "binder" / template, tmp / "template.tex")
        if page_text_override is not None:
            # Keep full-width writing rules inside the safe edge after PDF rounding.
            content = (tmp / "template.tex").read_text(encoding="utf-8")
            (tmp / "template.tex").write_text(content.replace("right=.55in", "right=.56in", 1), encoding="utf-8")
        if kind in ANIMAL_PAGE_KINDS:
            # Add source links only to animal pages; existing PDF bytes/layouts stay stable.
            content = (tmp / "template.tex").read_text(encoding="utf-8")
            # Inset animal rules from the exact safe edge; PDF transform arithmetic
            # can otherwise put a full-width writing rule fractionally outside it.
            content = content.replace("right=.55in", "right=.56in", 1)
            content = content.replace(r"\begin{document}", r"\usepackage[hidelinks]{hyperref}" + "\n" + r"\begin{document}")
            if selected:
                # Reuse the existing square hero geometry and prepared-asset path.
                profile_template = (ROOT / "binder/template.tex").read_text(encoding="utf-8")
                hero_macros = "\n".join(line for line in profile_template.splitlines()
                                        if line.startswith((r"\newcommand{\HeroImage}", r"\newcommand{\HeroPlaceholder}")))
                hero_macros = hero_macros.replace("[rust,", "[ink,")
                setup = (r"\usepackage{graphicx}\setlength{\fboxsep}{0pt}\setlength{\fboxrule}{.6pt}"
                         + "\n" + hero_macros + "\n")
                content = content.replace(r"\begin{document}", setup + r"\begin{document}\input{resolved-assets.tex}")
            (tmp / "template.tex").write_text(content, encoding="utf-8")
        if base.name in (*AQUATIC_PLANT_ENTRIES, *SUCCULENT_ENTRIES):
            # New aquatic source links use the existing catalog and evidence checks.
            load_companions(ROOT, base.name)
            content = (tmp / "template.tex").read_text(encoding="utf-8")
            content = content.replace(r"\begin{document}", r"\usepackage[hidelinks]{hyperref}" + "\n" + r"\begin{document}")
            content = content.replace("right=.55in", "right=.56in", 1)
            if base.name in SUCCULENT_ENTRIES:
                content = content.replace("v1 / 2026-10-04", "v1 / 2026-10-09")
            (tmp / "template.tex").write_text(content, encoding="utf-8")
        if category is not None:
            if category != CATEGORY_BY_ENTRY.get(base.name):
                raise ValueError("category must match the entry")
            content = (tmp / "template.tex").read_text(encoding="utf-8")
            color = "486B83" if category.startswith("AQUATIC") else "557064"
            content = content.replace(r"\definecolor{sage}{HTML}{557064}", rf"\definecolor{{sage}}{{HTML}}{{{color}}}")
            # Thin rules only; white backgrounds, dark body text and photo pixels stay intact.
            content = re.sub(r"\\rule\{\\linewidth\}\{([.0-9]+pt)\}",
                             lambda m: r"{\color{sage}\rule{\linewidth}{" + m[1] + "}}", content)
            content = content.replace(r"\textbf{#2}\quad", r"\textbf{" + category + r" / #2}\quad")
            (tmp / "template.tex").write_text(content, encoding="utf-8")
        page_name = f"{kind}.tex" if kind in COMPANION_LABELS else "page.tex"
        page_text = (base / page_name).read_text(encoding="utf-8") if page_text_override is None else page_text_override
        if expanded and kind == "profile":
            # Only the existing footer's revision label changes in v2.
            page_text = page_text.replace(r"\textbf{REVISION}", r"\textbf{OVERVIEW / REVISION}", 1)
        if expanded and kind == "supplemental":
            page_text = page_text.replace("HANDWRITTEN CARE RECORD", "HANDWRITTEN CARE RECORD / watering-log / supplemental", 1)
        if category is not None and kind == "profile":
            page_text = page_text.replace(r"\textbf{OVERVIEW / REVISION}", r"\textbf{" + category + r" / OVERVIEW / REVISION}", 1)
        (tmp / "page.tex").write_text(page_text, encoding="utf-8")
        lines, commands = [], {"hero": "AssetHero", "detail1": "AssetDetailOne", "detail2": "AssetDetailTwo"}
        for role in commands:
            command = commands[role]
            if role not in selected:
                lines.append(rf"\newcommand{{\{command}}}{{}}")
                continue
            record = records[selected[role]]
            if record["kind"] == "placeholder":
                rendered = rf"\HeroPlaceholder{{{selected[role]}}}" if role == "hero" else rf"\DetailPlaceholder{{{selected[role]}}}"
            else:
                path = (base / record["path"]).resolve().as_posix()
                if any(c in path for c in UNSAFE_TEX_PATH_CHARS):
                    raise ValueError(f"asset path contains unsupported TeX characters: {record['path']}")
                rendered = (r"\HeroImage" if role == "hero" else r"\DetailImage") + rf"{{\detokenize{{{path}}}}}"
            lines.append(rf"\newcommand{{\{command}}}{{{rendered}}}")
        details = [rf"\{commands[r]}" for r in ("detail1", "detail2") if r in selected]
        lines.append(r"\newcommand{\AssetDetails}{" + (r"\par\vspace{.08in}\hfill" + r"\hfill".join(details) if details else "") + "}")
        (tmp / "resolved-assets.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
        env = {**os.environ, "SOURCE_DATE_EPOCH": "0", "FORCE_SOURCE_DATE": "1"}
        for _ in range(2):
            result = subprocess.run(["lualatex", "-no-shell-escape", "-halt-on-error", "-interaction=nonstopmode", "template.tex"], cwd=tmp, text=True, encoding="utf-8", capture_output=True, env=env)
            if result.returncode:
                sys.stderr.write(result.stdout[-4000:]); raise RuntimeError("LuaLaTeX compilation failed")
        log = (tmp / "template.log").read_text(encoding="utf-8", errors="replace")
        if "Overfull" in log:
            if kind in COMPANION_LABELS or page_text_override is not None:
                shutil.copyfile(tmp / "template.pdf", output.with_suffix(".failed.pdf"))
            details = "\n".join(line for line in log.splitlines() if "Overfull" in line)
            raise RuntimeError(f"LuaLaTeX reported an overfull box in {base.name}/{page_name}: {details}")
        pdf = tmp / "template.pdf"
        from pypdf import PdfReader
        reader = PdfReader(pdf)
        if len(reader.pages) != 1:
            if kind in COMPANION_LABELS or page_text_override is not None:
                shutil.copyfile(pdf, output.with_suffix(".failed.pdf"))
            raise RuntimeError(f"entry rendered {len(reader.pages)} pages, expected 1 ({base.name}/{page_name})")
        _validate_page(reader.pages[0], base.name)
        if kind in COMPANION_LABELS:
            extracted = reader.pages[0].extract_text()
            label = COMPANION_LABELS[kind]
            if label not in extracted or f"{base.name} / {kind}" not in extracted:
                raise RuntimeError("companion page identity missing")
        shutil.copyfile(pdf, output)
        print(f"built {output} (1 page, 612 x 792 pt, sha256 {hashlib.sha256(output.read_bytes()).hexdigest()})")


def supplemental_path(name: str) -> Path:
    root = (ROOT / "binder" / "supplemental").resolve()
    base = (root / name).resolve()
    if root not in base.parents or not base.is_dir() or not (base / "page.tex").is_file():
        raise ValueError(f"unknown supplemental page: {name}")
    return base


def compile_supplemental(name: str, mode: str, output: Path) -> None:
    if mode != "draft":
        raise ValueError("supplemental pages are currently available only in draft mode")
    if name in {"watering-log-tracked", "watering-log-blank"}:
        entries = load_manifest(ROOT / "binder/manifest-v6.yaml")
        compile_logs(entries, output, blank=name == "watering-log-blank")
    else:
        compile_entry(supplemental_path(name), {}, {}, output)


def compile_logs(entries: list[dict], output: Path, *, blank: bool = False) -> None:
    from pypdf import PdfReader, PdfWriter
    batches = [[]] if blank else paginate_species(tracked_species(entries))
    writer = PdfWriter()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="binder-logs-") as directory:
        for number, species in enumerate(batches, 1):
            page = Path(directory) / f"log-{number}.pdf"
            compile_entry(supplemental_path("watering-log"), {}, {}, page,
                          page_text_override=log_page_tex(species, number, len(batches), blank=blank))
            writer.add_page(PdfReader(page).pages[0])
        with output.open("wb") as stream:
            writer.write(stream)


def load_manifest(path: Path) -> list[dict]:
    manifest_path = path.resolve()
    supported = {(ROOT / "binder" / "manifest.yaml").resolve(): 1,
                 (ROOT / "binder" / "manifest-v2.yaml").resolve(): 2,
                 (ROOT / "binder" / "manifest-v3.yaml").resolve(): 3,
                 (ROOT / "binder" / "manifest-v4.yaml").resolve(): 4,
                 (ROOT / "binder" / "manifest-v5.yaml").resolve(): 5,
                 (ROOT / "binder" / "manifest-v6.yaml").resolve(): 6,
                 (ROOT / "binder" / "manifest-v7.yaml").resolve(): 7}
    if manifest_path not in supported:
        raise ValueError("only the versioned binder assembly manifests are supported")
    version = supported[manifest_path]
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema_version") != version:
        raise ValueError("manifest schema version must match its versioned path")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest entries must be a nonempty array")
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"id", "kind", "page_budget"}:
            raise ValueError("each manifest entry must define only id, kind, and page_budget")
        if not _nonempty(item["id"]) or not ID.fullmatch(item["id"]):
            raise ValueError(f"malformed manifest entry ID: {item['id']!r}")
        if item["kind"] not in {"profile", "supplemental", *COMPANION_LABELS}:
            raise ValueError(f"unsupported manifest kind: {item['kind']}")
    for item in entries:
        budget = (len(paginate_species(tracked_species(entries)))
                  if version in {6, 7} and item["id"] == "watering-log-tracked" else 1)
        if type(item["page_budget"]) is not int or item["page_budget"] != budget:
            raise ValueError(f"manifest page_budget must be integer {budget}")
    actual = tuple((item["id"], item["kind"]) for item in entries)
    expected = {1: EXPECTED_MANIFEST, 2: EXPECTED_EXPANDED_MANIFEST,
                3: EXPECTED_ANIMAL_MANIFEST, 4: EXPECTED_SHRIMP_MANIFEST,
                5: EXPECTED_AQUATIC_MANIFEST, 6: EXPECTED_LOG_MANIFEST,
                7: EXPECTED_SUCCULENT_MANIFEST}[version]
    if actual != expected:
        label = {1: "six-entry", 2: "sixteen-entry", 3: "nineteen-entry", 4: "twenty-two-entry", 5: "thirty-one-entry", 6: "thirty-two-entry", 7: "thirty-eight-entry"}[version]
        raise ValueError(f"manifest entries must match the canonical {label} order and kinds")
    return entries


def compile_companion(entry: str, kind: str, mode: str, output: Path, *, category: str | None = None) -> None:
    if mode != "draft":
        raise ValueError("companion pages remain provisional and draft-only")
    if (entry, kind) not in EXPECTED_SUCCULENT_MANIFEST or kind not in {"numbers", "propagation"}:
        raise ValueError("unknown companion page")
    evidence = load_companions(ROOT, entry)
    base = ROOT / "binder" / "entries" / entry
    page = (base / f"{kind}.tex").read_text(encoding="utf-8")
    references = re.findall(r"^% claim-ref: (\S+)$", page, re.MULTILINE)
    if not references or any(ref not in evidence["valid_refs"] for ref in references):
        raise ValueError("companion layout must cite resolved entry or context claims")
    # This release uses native vector schematics. Reject unsupported photograph
    # placement rather than silently bypassing catalog/rights validation.
    if "% binder-placement" in page or r"\includegraphics" in page:
        raise ValueError("companion photograph placement is not supported; use a native vector schematic")
    compile_entry(base, {}, {}, output, kind=kind, expanded=True,
                  **({"category": category} if category is not None else {}))


def compile_animal(entry: str, kind: str, mode: str, output: Path, *, category: str | None = None) -> None:
    if mode != "draft":
        raise ValueError("animal pages remain provisional and draft-only")
    if kind not in ANIMAL_PAGE_KINDS or (entry, kind) not in EXPECTED_SHRIMP_MANIFEST:
        raise ValueError("unknown animal page")
    evidence = load_animal(ROOT, entry)
    base = ROOT / "binder/entries" / entry
    page = (base / f"{kind}.tex").read_text(encoding="utf-8")
    references = re.findall(r"^% claim-ref: (\S+)$", page, re.MULTILINE)
    if not references or not set(references) <= evidence["valid_refs"]:
        raise ValueError("animal layout must cite resolved claims")
    if r"\includegraphics" in page:
        raise ValueError("animal images must use the validated asset catalog")
    records, selected = {}, {}
    if kind == "animal-care" and "% binder-placement" not in page:
        raise ValueError("animal care must declare its hero or visible placeholder")
    if "% binder-placement" in page:
        if kind != "animal-care":
            raise ValueError("animal hero belongs on the first care page only")
        base, records, selected = load_entry(entry, mode, layout_name="animal-care.tex")
        if set(selected) != {"hero"}:
            raise ValueError("animal care supports exactly one hero")
        for record in records.values():
            if record["kind"] == "photograph":
                source = record["source"]
                if (source.get("owner_supplied") is not True or source.get("rights_reviewed") is not True
                        or source["rights"].strip().casefold() in UNRESOLVED_RIGHTS):
                    raise ValueError("animal photographs require reviewed owner-supplied provenance")
    links = re.findall(r"\\href\{([^{}]+)\}", page)
    source_urls = {s["url"] for s in evidence["sources"].values()}
    if not links or not set(links) <= source_urls:
        raise ValueError("animal source links must resolve to bibliography URLs")
    compile_entry(base, records, selected, output, kind=kind, expanded=True,
                  **({"category": category} if category is not None else {}))


def _validate_page(page: object, label: str) -> None:
    media = page.mediabox
    crop = page.cropbox
    media_coordinates = tuple(float(value) for value in (*media.lower_left, *media.upper_right))
    crop_coordinates = tuple(float(value) for value in (*crop.lower_left, *crop.upper_right))
    expected = (0, 0, 612, 792)
    if (any(abs(actual - wanted) > .1 for actual, wanted in zip(media_coordinates, expected)) or
            any(abs(actual - wanted) > .1 for actual, wanted in zip(crop_coordinates, expected)) or
            any(abs(actual - wanted) > .1 for actual, wanted in zip(crop_coordinates, media_coordinates))):
        raise RuntimeError(f"{label} page geometry is not US Letter")
    if (page.get("/Rotate") or 0) != 0:
        raise RuntimeError(f"{label} page rotation is not 0")
    extracted = "".join((page.extract_text() or "").split())
    if len(extracted) < MIN_EXTRACTED_PAGE_CHARACTERS:
        raise RuntimeError(f"{label} page is blank or near-blank")


def compile_manifest(path: Path, mode: str, output: Path) -> None:
    if mode != "draft":
        raise ValueError("manifest assembly is currently available only in draft mode")
    from pypdf import PdfReader, PdfWriter
    entries = load_manifest(path)
    expanded = path.name != "manifest.yaml"
    accented = path.name in {"manifest-v5.yaml", "manifest-v6.yaml", "manifest-v7.yaml"}
    expected_pages = sum(item["page_budget"] for item in entries)
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    with tempfile.TemporaryDirectory(prefix="binder-manifest-") as tmp_name:
        for index, item in enumerate(entries, 1):
            style = {"category": CATEGORY_BY_ENTRY[item["id"]]} if accented and item["kind"] != "supplemental" else {}
            individual = Path(tmp_name) / f"{index:02d}-{item['id']}.pdf"
            if item["kind"] == "profile":
                if expanded:
                    compile_entry(*load_entry(item["id"], mode), individual, expanded=True, **style)
                else:
                    compile_entry(*load_entry(item["id"], mode), individual)
            elif item["kind"] in {"numbers", "propagation"}:
                compile_companion(item["id"], item["kind"], mode, individual, **style)
            elif item["kind"] in ANIMAL_PAGE_KINDS:
                compile_animal(item["id"], item["kind"], mode, individual, **style)
            else:
                if item["id"] in {"watering-log-tracked", "watering-log-blank"}:
                    compile_logs(entries, individual, blank=item["id"] == "watering-log-blank")
                elif expanded:
                    compile_entry(supplemental_path(item["id"]), {}, {}, individual,
                                  kind="supplemental", expanded=True)
                else:
                    compile_supplemental(item["id"], mode, individual)
            reader = PdfReader(individual)
            if len(reader.pages) != item["page_budget"]:
                raise RuntimeError(
                    f"{item['id']} rendered {len(reader.pages)} pages, "
                    f"expected page_budget {item['page_budget']}"
                )
            for page in reader.pages:
                _validate_page(page, item["id"])
                writer.add_page(page)
        writer.add_metadata({"/Title": "Aquiloop care binder — draft", "/Producer": "Aquiloop deterministic binder builder"})
        with output.open("wb") as stream:
            writer.write(stream)
    assembled = PdfReader(output)
    if len(assembled.pages) != expected_pages:
        raise RuntimeError(
            f"combined binder rendered {len(assembled.pages)} pages, "
            f"expected {expected_pages}"
        )
    for index, page in enumerate(assembled.pages, 1):
        _validate_page(page, f"combined page {index}")
    print(f"built {output} ({expected_pages} pages, sha256 {hashlib.sha256(output.read_bytes()).hexdigest()})")


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--entry")
    source.add_argument("--supplemental")
    source.add_argument("--manifest", type=Path)
    parser.add_argument("--mode", choices=("draft", "final"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kind", choices=("profile", *COMPANION_LABELS), default="profile")
    args = parser.parse_args()
    try:
        if args.entry:
            if args.kind == "profile":
                compile_entry(*load_entry(args.entry, args.mode), args.output)
            elif args.kind in ANIMAL_PAGE_KINDS:
                compile_animal(args.entry, args.kind, args.mode, args.output)
            else:
                compile_companion(args.entry, args.kind, args.mode, args.output)
        elif args.supplemental:
            compile_supplemental(args.supplemental, args.mode, args.output)
        else:
            compile_manifest(args.manifest, args.mode, args.output)
    except (OSError,ValueError,RuntimeError,json.JSONDecodeError) as exc: parser.exit(1,f"error: {exc}\n")
    return 0
if __name__ == "__main__": raise SystemExit(main())
