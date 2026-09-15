#!/usr/bin/env python3
"""Validate and build one care-binder entry with LuaLaTeX."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY_ROOT = ROOT / "binder" / "entries"
REQUIRED = {"id", "path", "kind", "subjects", "alt", "caption", "source"}
SOURCE_REQUIRED = {"photographer", "provenance", "rights"}
SELECTION = re.compile(r"\\def\\(HeroAsset|DetailOneAsset|DetailTwoAsset)\{([^}]*)\}")
UNRESOLVED = {"", "unknown", "pending", "unresolved"}


class BinderError(ValueError):
    pass


def load_entry(entry_dir: Path, mode: str) -> tuple[dict[str, dict], dict[str, str]]:
    catalog = json.loads((entry_dir / "assets.json").read_text(encoding="utf-8"))
    if catalog.get("schema_version") != 1:
        raise BinderError("assets.json: only schema_version 1 is supported")
    assets: dict[str, dict] = {}
    for index, asset in enumerate(catalog.get("assets", [])):
        missing = REQUIRED - asset.keys()
        if missing:
            raise BinderError(f"asset {index}: missing {', '.join(sorted(missing))}")
        if not isinstance(asset["subjects"], list) or not asset["subjects"]:
            raise BinderError(f"asset {asset['id']}: subjects must be a non-empty list")
        source = asset.get("source", {})
        missing_source = SOURCE_REQUIRED - source.keys()
        if missing_source:
            raise BinderError(f"asset {asset['id']}: missing source.{', source.'.join(sorted(missing_source))}")
        if asset["id"] in assets:
            raise BinderError(f"duplicate asset ID: {asset['id']}")
        path = (entry_dir / asset["path"]).resolve()
        try:
            path.relative_to(entry_dir.resolve())
        except ValueError as exc:
            raise BinderError(f"asset {asset['id']}: path escapes entry directory") from exc
        if not path.is_file():
            raise BinderError(f"asset {asset['id']}: missing local file {asset['path']}")
        asset["resolved_path"] = str(path)
        if asset["kind"] != "placeholder":
            try:
                from PIL import Image
                with Image.open(path) as image:
                    asset["measured"] = {"width": image.width, "height": image.height,
                                         "format": image.format, "bytes": path.stat().st_size}
            except (ImportError, OSError) as exc:
                raise BinderError(f"asset {asset['id']}: cannot measure raster: {exc}") from exc
        assets[asset["id"]] = asset

    page = (entry_dir / "page.tex").read_text(encoding="utf-8")
    selections = {name: value.strip() for name, value in SELECTION.findall(page)}
    if not selections.get("HeroAsset"):
        raise BinderError("page.tex: exactly one hero must be selected")
    details = [selections.get("DetailOneAsset", ""), selections.get("DetailTwoAsset", "")]
    for selected in [selections["HeroAsset"], *filter(None, details)]:
        if selected not in assets:
            raise BinderError(f"page.tex: selected asset does not exist: {selected}")
        asset = assets[selected]
        if asset["kind"] != "placeholder":
            measured = asset["measured"]
            minimum = (792, 792) if selected == selections["HeroAsset"] else (492, 324)
            if measured["width"] < minimum[0] or measured["height"] < minimum[1]:
                raise BinderError(
                    f"selected asset {selected}: {measured['width']}x{measured['height']} px; "
                    f"minimum rendered crop is {minimum[0]}x{minimum[1]} px"
                )
        if mode == "final":
            rights = str(asset["source"]["rights"]).strip().lower()
            if asset["kind"] == "placeholder":
                raise BinderError(f"final mode rejects selected placeholder: {selected}")
            if rights in UNRESOLVED:
                raise BinderError(f"final mode rejects unresolved rights: {selected}")
    if len([value for value in details if value]) > 2:
        raise BinderError("a profile supports at most two detail images")
    return assets, selections


def tex_escape_path(path: str) -> str:
    return path.replace("\\", "/").replace("#", "\\#").replace("%", "\\%")


def build(entry: str, mode: str, output: Path) -> None:
    entry_dir = (ENTRY_ROOT / entry).resolve()
    if not entry_dir.is_dir() or entry_dir.parent != ENTRY_ROOT.resolve():
        raise BinderError(f"unknown entry: {entry}")
    assets, selections = load_entry(entry_dir, mode)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aquiloop-binder-") as raw_tmp:
        tmp = Path(raw_tmp)
        definitions = [f"\\def\\EntryDir{{{tex_escape_path(str(entry_dir))}}}",
                       f"\\def\\BinderMode{{{mode}}}"]
        selected = {value for value in selections.values() if value}
        for asset_id in selected:
            asset = assets[asset_id]
            placeholder = "1" if asset["kind"] == "placeholder" else "0"
            definitions += [
                f"\\expandafter\\def\\csname assetpath@{asset_id}\\endcsname{{{tex_escape_path(asset['resolved_path'])}}}",
                f"\\expandafter\\def\\csname placeholder@{asset_id}\\endcsname{{{placeholder}}}",
            ]
        definitions += [
            r"\def\AssetPath#1{\csname assetpath@#1\endcsname}",
            r"\def\AssetIsPlaceholder#1{\csname placeholder@#1\endcsname}",
            f"\\input{{{tex_escape_path(str(ROOT / 'binder' / 'template.tex'))}}}",
        ]
        driver = tmp / "driver.tex"
        driver.write_text("\n".join(definitions), encoding="utf-8")
        command = ["lualatex", "-halt-on-error", "-interaction=nonstopmode",
                   f"-output-directory={tmp}", str(driver)]
        for _ in range(2):
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            if result.returncode:
                sys.stderr.write(result.stdout[-5000:] + result.stderr)
                raise BinderError("LuaLaTeX compilation failed")
        log = (tmp / "driver.log").read_text(encoding="utf-8", errors="replace")
        if "Overfull \\hbox" in log or "Overfull \\vbox" in log:
            warnings = " | ".join(line for line in log.splitlines() if line.startswith("Overfull"))
            raise BinderError(f"LuaLaTeX reported an overfull box; refusing clipped output: {warnings}")
        proof = tmp / "driver.pdf"
        info = subprocess.run(["pdfinfo", str(proof)], text=True, capture_output=True)
        if info.returncode or not re.search(r"^Pages:\s+1$", info.stdout, re.MULTILINE):
            raise BinderError("entry must produce exactly one page")
        if not re.search(r"^Page size:\s+612 x 792 pts", info.stdout, re.MULTILINE):
            raise BinderError("entry page must be portrait US Letter (612 x 792 points)")
        shutil.copyfile(proof, output)
    print(f"built {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--mode", choices=("draft", "final"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        build(args.entry, args.mode, args.output)
    except (BinderError, FileNotFoundError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
