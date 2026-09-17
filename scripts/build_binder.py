#!/usr/bin/env python3
"""Build individual binder pages or an ordered draft binder manifest."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"id", "path", "kind", "subjects", "alt", "caption", "source"}
SOURCE_REQUIRED = {"photographer", "provenance", "rights"}
KINDS = {"photograph", "placeholder"}
ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLACEMENT = re.compile(r"^% binder-placement (hero|detail1|detail2) ([a-z0-9]+(?:-[a-z0-9]+)*);(?: .+)?$")
UNRESOLVED_RIGHTS = {"unknown", "pending", "unresolved", "permission requested", "tbd", "not reviewed", "permission denied"}
UNSAFE_TEX_PATH_CHARS = frozenset("#%{}\\\r\n")
EXPECTED_BINDER_PAGES = 6
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


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load_entry(entry: str, mode: str) -> tuple[Path, dict[str, dict], dict[str, str]]:
    entries = (ROOT / "binder" / "entries").resolve()
    base = (entries / entry).resolve()
    if entries not in base.parents or not base.is_dir():
        raise ValueError(f"unknown entry: {entry}")
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
    for line in (base / "page.tex").read_text(encoding="utf-8").splitlines():
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


def compile_entry(base: Path, records: dict[str, dict], selected: dict[str, str], output: Path) -> None:
    if not shutil.which("lualatex"):
        raise RuntimeError("lualatex is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="binder-") as tmp_name:
        tmp = Path(tmp_name)
        shutil.copy(ROOT / "binder" / "template.tex", tmp); shutil.copy(base / "page.tex", tmp)
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
            result = subprocess.run(["lualatex", "-halt-on-error", "-interaction=nonstopmode", "template.tex"], cwd=tmp, text=True, encoding="utf-8", capture_output=True, env=env)
            if result.returncode:
                sys.stderr.write(result.stdout[-4000:]); raise RuntimeError("LuaLaTeX compilation failed")
        log = (tmp / "template.log").read_text(encoding="utf-8", errors="replace")
        if "Overfull" in log:
            raise RuntimeError("LuaLaTeX reported an overfull box")
        pdf = tmp / "template.pdf"
        from pypdf import PdfReader
        reader = PdfReader(pdf)
        if len(reader.pages) != 1: raise RuntimeError(f"entry rendered {len(reader.pages)} pages, expected 1")
        _validate_page(reader.pages[0], base.name)
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
    compile_entry(supplemental_path(name), {}, {}, output)


def load_manifest(path: Path) -> list[dict]:
    manifest_path = path.resolve()
    if manifest_path != (ROOT / "binder" / "manifest.yaml").resolve():
        raise ValueError("binder/manifest.yaml is the sole supported assembly manifest")
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("manifest must use supported schema_version 1")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest entries must be a nonempty array")
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"id", "kind", "page_budget"}:
            raise ValueError("each manifest entry must define only id, kind, and page_budget")
        if not _nonempty(item["id"]) or not ID.fullmatch(item["id"]):
            raise ValueError(f"malformed manifest entry ID: {item['id']!r}")
        if item["kind"] not in {"profile", "supplemental"}:
            raise ValueError(f"unsupported manifest kind: {item['kind']}")
        if type(item["page_budget"]) is not int or item["page_budget"] != 1:
            raise ValueError("manifest page_budget must be integer 1")
    actual = tuple((item["id"], item["kind"]) for item in entries)
    if actual != EXPECTED_MANIFEST:
        raise ValueError("manifest entries must match the canonical six-entry order and kinds")
    return entries


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
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    with tempfile.TemporaryDirectory(prefix="binder-manifest-") as tmp_name:
        for index, item in enumerate(entries, 1):
            individual = Path(tmp_name) / f"{index:02d}-{item['id']}.pdf"
            if item["kind"] == "profile":
                compile_entry(*load_entry(item["id"], mode), individual)
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
    if len(assembled.pages) != EXPECTED_BINDER_PAGES:
        raise RuntimeError(
            f"combined binder rendered {len(assembled.pages)} pages, "
            f"expected {EXPECTED_BINDER_PAGES}"
        )
    for index, page in enumerate(assembled.pages, 1):
        _validate_page(page, f"combined page {index}")
    print(f"built {output} ({EXPECTED_BINDER_PAGES} pages, sha256 {hashlib.sha256(output.read_bytes()).hexdigest()})")


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--entry")
    source.add_argument("--supplemental")
    source.add_argument("--manifest", type=Path)
    parser.add_argument("--mode", choices=("draft", "final"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.entry:
            compile_entry(*load_entry(args.entry, args.mode), args.output)
        elif args.supplemental:
            compile_supplemental(args.supplemental, args.mode, args.output)
        else:
            compile_manifest(args.manifest, args.mode, args.output)
    except (OSError,ValueError,RuntimeError,json.JSONDecodeError) as exc: parser.exit(1,f"error: {exc}\n")
    return 0
if __name__ == "__main__": raise SystemExit(main())
