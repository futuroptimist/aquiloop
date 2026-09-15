#!/usr/bin/env python3
"""Validate one binder entry and compile its one-page LuaLaTeX proof."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"id", "path", "kind", "subjects", "alt", "caption", "source"}
SOURCE_REQUIRED = {"photographer", "provenance", "rights"}
ASPECT_TOLERANCE = .005
KINDS = {"photograph", "placeholder"}
PLACEMENT = re.compile(r"^% binder-placement (hero|detail[12]) ([^;]+);")


def load_entry(entry: str, mode: str) -> tuple[Path, dict[str, dict], dict[str, str]]:
    base = (ROOT / "binder" / "entries" / entry).resolve()
    entries = (ROOT / "binder" / "entries").resolve()
    if entries not in base.parents or not base.is_dir():
        raise ValueError(f"unknown entry: {entry}")
    data = json.loads((base / "assets.json").read_text())
    if data.get("schema_version") != 1:
        raise ValueError("assets.json must use supported schema_version 1")
    records: dict[str, dict] = {}
    for record in data.get("assets", []):
        if not isinstance(record, dict):
            raise ValueError("each asset must be an object")
        missing = REQUIRED - record.keys()
        if missing:
            raise ValueError(f"asset missing required metadata: {sorted(missing)}")
        if not isinstance(record["source"], dict):
            raise ValueError(f"asset {record['id']} source metadata must be an object")
        source_missing = SOURCE_REQUIRED - record["source"].keys()
        if source_missing:
            raise ValueError(f"asset {record['id']} missing source metadata: {sorted(source_missing)}")
        if record["id"] in records:
            raise ValueError(f"duplicate asset ID: {record['id']}")
        if record["kind"] not in KINDS:
            raise ValueError(f"asset {record['id']} has unsupported kind: {record['kind']}")
        records[record["id"]] = record
    selected = {}
    for line in (base / "page.tex").read_text().splitlines():
        match = PLACEMENT.match(line)
        if match:
            selected[match.group(1)] = match.group(2).strip()
    if "hero" not in selected or len([x for x in selected if x.startswith("detail")]) > 2:
        raise ValueError("page must select one hero and no more than two details")
    for role, asset_id in selected.items():
        if asset_id not in records:
            raise ValueError(f"selected {role} references unknown asset: {asset_id}")
        record = records[asset_id]
        path = (base / record["path"]).resolve()
        if base not in path.parents or not path.is_file():
            raise ValueError(f"asset path must resolve within entry: {record['path']}")
        if mode == "final" and (record["kind"] == "placeholder" or record["source"].get("rights_reviewed") is not True):
            raise ValueError(f"selected asset {asset_id} is not qualified for final mode")
        if record["kind"] == "photograph":
            try:
                from PIL import Image
                with Image.open(path) as image:
                    width, height, image_format = image.width, image.height, image.format
            except (ImportError, OSError) as exc:
                raise ValueError(f"cannot measure raster asset {asset_id}: {exc}") from exc
            if image_format not in {"JPEG", "PNG"}:
                raise ValueError(f"unsupported raster format for {asset_id}: {image_format}")
            if path.stat().st_size > 1024 * 1024:
                raise ValueError(f"raster asset {asset_id} exceeds 1 MiB")
            required = (792, 792) if role == "hero" else (492, 324)
            if width < required[0] or height < required[1]:
                raise ValueError(f"selected {role} {asset_id} is below {required[0]} x {required[1]} px")
            frame_ratio = 1 if role == "hero" else 2.05 / 1.35
            if abs(width / height - frame_ratio) > ASPECT_TOLERANCE:
                raise ValueError(f"selected {role} {asset_id} aspect ratio does not match its frame")
            print(f"asset {asset_id}: {width} x {height} px, {image_format}, {path.stat().st_size} bytes")
    return base, records, selected


def compile_entry(base: Path, records: dict[str, dict], selected: dict[str, str], output: Path) -> None:
    if not shutil.which("lualatex"):
        raise RuntimeError("lualatex is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="binder-") as tmp_name:
        tmp = Path(tmp_name)
        shutil.copy(ROOT / "binder" / "template.tex", tmp)
        shutil.copy(base / "page.tex", tmp)
        lines = []
        commands = {"hero": "AssetHero", "detail1": "AssetDetailOne", "detail2": "AssetDetailTwo"}
        for role in ("hero", "detail1", "detail2"):
            command = commands[role]
            if role not in selected:
                lines.append(rf"\newcommand{{\{command}}}{{}}")
                continue
            record = records[selected[role]]
            if record["kind"] == "placeholder":
                rendered = r"\HeroPlaceholder" if role == "hero" else ""
            else:
                path = (base / record["path"]).resolve().as_posix()
                if any(character in path for character in "{}\r\n"):
                    raise ValueError(f"asset path contains unsupported characters: {record['path']}")
                latex_path = rf"\detokenize{{{path}}}"
                rendered = rf"\HeroImage{{{latex_path}}}" if role == "hero" else rf"\DetailImage{{{latex_path}}}"
            lines.append(rf"\newcommand{{\{command}}}{{{rendered}}}")
        details = [rf"\{commands[role]}" for role in ("detail1", "detail2") if role in selected]
        lines.append(r"\newcommand{\AssetDetails}{" + (r"\par\vspace{.08in}" + r"\hfill".join(details) if details else "") + "}")
        (tmp / "resolved-assets.tex").write_text("\n".join(lines) + "\n")
        for _ in range(2):
            result = subprocess.run(["lualatex", "-halt-on-error", "-interaction=nonstopmode", "template.tex"], cwd=tmp, text=True, capture_output=True)
            if result.returncode:
                sys.stderr.write(result.stdout[-4000:])
                raise RuntimeError("LuaLaTeX compilation failed")
        log = (tmp / "template.log").read_text(errors="replace")
        if "Overfull" in log:
            raise RuntimeError("LuaLaTeX reported an overfull box")
        pdf = tmp / "template.pdf"
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf)
            if len(reader.pages) != 1:
                raise RuntimeError(f"entry rendered {len(reader.pages)} pages, expected 1")
            box = reader.pages[0].mediabox
            if abs(float(box.width) - 612) > .1 or abs(float(box.height) - 792) > .1:
                raise RuntimeError(f"page geometry is {float(box.width)} x {float(box.height)} pt")
        except ImportError as exc:
            raise RuntimeError("pypdf is required for independent page validation") from exc
        shutil.copyfile(pdf, output)
        print(f"built {output} (1 page, 612 x 792 pt, sha256 {hashlib.sha256(output.read_bytes()).hexdigest()})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", required=True)
    parser.add_argument("--mode", choices=("draft", "final"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        base, records, selected = load_entry(args.entry, args.mode)
        compile_entry(base, records, selected, args.output)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
