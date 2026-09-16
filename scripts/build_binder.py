#!/usr/bin/env python3
"""Validate and build individual or manifest-assembled binder pages."""
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


def _validate_pdf(pdf: Path, expected_pages: int, label: str) -> None:
    from pypdf import PdfReader
    reader = PdfReader(pdf)
    if len(reader.pages) != expected_pages:
        raise RuntimeError(f"{label} rendered {len(reader.pages)} pages, expected {expected_pages}")
    for number, page in enumerate(reader.pages, 1):
        for box_name in ("mediabox", "cropbox"):
            box = getattr(page, box_name)
            if abs(float(box.width) - 612) > .1 or abs(float(box.height) - 792) > .1:
                raise RuntimeError(f"{label} page {number} {box_name} is not US Letter")
        if page.get("/Rotate", 0) != 0:
            raise RuntimeError(f"{label} page {number} rotation is not 0")


def _compile_tex(page: Path, resolved_assets: str, output: Path, label: str) -> None:
    if not shutil.which("lualatex"):
        raise RuntimeError("lualatex is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="binder-") as tmp_name:
        tmp = Path(tmp_name)
        shutil.copy(ROOT / "binder" / "template.tex", tmp)
        shutil.copy(page, tmp / "page.tex")
        (tmp / "resolved-assets.tex").write_text(resolved_assets, encoding="utf-8")
        env = {**os.environ, "SOURCE_DATE_EPOCH": "0", "FORCE_SOURCE_DATE": "1"}
        for _ in range(2):
            result = subprocess.run(["lualatex", "-halt-on-error", "-interaction=nonstopmode", "template.tex"], cwd=tmp, text=True, encoding="utf-8", capture_output=True, env=env)
            if result.returncode:
                sys.stderr.write(result.stdout[-4000:])
                raise RuntimeError("LuaLaTeX compilation failed")
        log = (tmp / "template.log").read_text(encoding="utf-8", errors="replace")
        if "Overfull" in log:
            raise RuntimeError("LuaLaTeX reported an overfull box")
        pdf = tmp / "template.pdf"
        _validate_pdf(pdf, 1, label)
        shutil.copyfile(pdf, output)
        print(f"built {output} (1 page, 612 x 792 pt, sha256 {hashlib.sha256(output.read_bytes()).hexdigest()})")


def compile_entry(base: Path, records: dict[str, dict], selected: dict[str, str], output: Path) -> None:
    lines, commands = [], {"hero": "AssetHero", "detail1": "AssetDetailOne", "detail2": "AssetDetailTwo"}
    for role, command in commands.items():
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
    _compile_tex(base / "page.tex", "\n".join(lines) + "\n", output, "entry")


def compile_supplemental(entry: str, output: Path) -> None:
    base = (ROOT / "binder" / "supplemental").resolve()
    page = (base / entry / "page.tex").resolve()
    if base not in page.parents or not page.is_file():
        raise ValueError(f"unknown supplemental entry: {entry}")
    _compile_tex(page, "", output, "supplemental entry")


def load_manifest(path: Path) -> list[dict]:
    manifest_path = path.resolve()
    if ROOT not in manifest_path.parents or not manifest_path.is_file():
        raise ValueError("manifest must be an existing repository file")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("entries"), list):
        raise ValueError("manifest must use schema_version 1 and contain an entries array")
    entries, seen = data["entries"], set()
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"id", "kind", "page_budget"}:
            raise ValueError("each manifest entry must contain only id, kind, and page_budget")
        if not _nonempty(item["id"]) or not ID.fullmatch(item["id"]) or item["id"] in seen:
            raise ValueError(f"invalid or duplicate manifest entry: {item.get('id')!r}")
        if item["kind"] not in {"profile", "supplemental"}:
            raise ValueError(f"unsupported manifest kind: {item['kind']}")
        if not isinstance(item["page_budget"], int) or isinstance(item["page_budget"], bool) or item["page_budget"] < 1:
            raise ValueError("manifest page_budget must be a positive integer")
        seen.add(item["id"])
    return entries


def compile_manifest(path: Path, mode: str, output: Path) -> None:
    entries = load_manifest(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="binder-manifest-") as tmp_name:
        built = []
        for index, item in enumerate(entries, 1):
            target = Path(tmp_name) / f"{index:02d}-{item['id']}.pdf"
            if item["kind"] == "profile":
                compile_entry(*load_entry(item["id"], mode), target)
            else:
                compile_supplemental(item["id"], target)
            _validate_pdf(target, item["page_budget"], item["id"])
            built.append(target)
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter()
        for pdf in built:
            for page in PdfReader(pdf).pages:
                writer.add_page(page)
        writer.add_metadata({})
        with output.open("wb") as stream:
            writer.write(stream)
    expected = sum(item["page_budget"] for item in entries)
    _validate_pdf(output, expected, "combined binder")
    print(f"built {output} ({expected} pages, sha256 {hashlib.sha256(output.read_bytes()).hexdigest()})")


def main() -> int:
    parser = argparse.ArgumentParser()
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--entry")
    choice.add_argument("--supplemental")
    choice.add_argument("--manifest", type=Path)
    parser.add_argument("--mode", choices=("draft", "final"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.entry:
            compile_entry(*load_entry(args.entry, args.mode), args.output)
        elif args.supplemental:
            compile_supplemental(args.supplemental, args.output)
        else:
            compile_manifest(args.manifest, args.mode, args.output)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
