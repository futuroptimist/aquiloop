#!/usr/bin/env python3
"""Validate, resolve, and compile one care-binder entry."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from binderlib import BinderError, load_catalog, placement_tex, validate_selection

ROOT = Path(__file__).resolve().parents[1]


def selection(page: str) -> tuple[str, list[str]]:
    def macro(name: str) -> str:
        found = re.search(rf"\\def\\{name}\{{([^}}]*)\}}", page)
        if not found:
            raise BinderError(f"page.tex lacks \\def\\{name}{{...}}")
        return found.group(1).strip()
    return macro("BinderHeroID"), [part.strip() for part in macro("BinderDetailIDs").split(",") if part.strip()]


def build(entry_name: str, mode: str, output: Path, compile_pdf: bool = True) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", entry_name):
        raise BinderError("entry must contain lowercase letters, digits, or hyphens")
    entry = ROOT / "binder" / "entries" / entry_name
    page_path = entry / "page.tex"
    if not page_path.is_file():
        raise BinderError(f"entry does not exist: {entry_name}")
    hero_id, detail_ids = selection(page_path.read_text(encoding="utf-8"))
    catalog = load_catalog(entry)
    selected = validate_selection(catalog, hero_id, detail_ids, mode)
    hero_tex = placement_tex(selected[0], "hero")
    details = [placement_tex(asset, "detail") for asset in selected[1:]]
    detail_tex = "\\hbox to \\linewidth{" + "\\hfil".join(details) + "}" if details else ""
    if not compile_pdf:
        return output
    if shutil.which("lualatex") is None:
        raise BinderError("lualatex is required but was not found on PATH")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="binder-build-") as temporary:
        work = Path(temporary)
        resolved = work / "resolved-assets.tex"
        resolved.write_text(f"\\def\\BinderHero{{{hero_tex}}}\n\\def\\BinderDetails{{{detail_tex}}}\n", encoding="utf-8")
        driver = work / "driver.tex"
        driver.write_text(
            f"\\def\\EntrySource{{{page_path.resolve().as_posix()}}}\n"
            f"\\def\\ResolvedAssets{{{resolved.as_posix()}}}\n"
            f"\\input{{{(ROOT / 'binder/template.tex').resolve().as_posix()}}}\n",
            encoding="utf-8",
        )
        run = subprocess.run(["lualatex", "-halt-on-error", "-interaction=nonstopmode", "driver.tex"], cwd=work, text=True, capture_output=True)
        if run.returncode:
            tail = "\n".join((run.stdout + run.stderr).splitlines()[-30:])
            raise BinderError(f"LuaLaTeX failed:\n{tail}")
        shutil.copy2(work / "driver.pdf", output)
    if shutil.which("pdfinfo") is None:
        output.unlink(missing_ok=True)
        raise BinderError("pdfinfo is required for independent page-contract validation")
    info = subprocess.run(["pdfinfo", output], text=True, capture_output=True)
    if info.returncode or not re.search(r"^Pages:\s+1$", info.stdout, re.MULTILINE) or not re.search(r"^Page size:\s+612 x 792 pts", info.stdout, re.MULTILINE):
        output.unlink(missing_ok=True)
        raise BinderError("compiled proof violates the one-page 612 x 792 point contract")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--mode", choices=("draft", "final"), required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(build(args.entry, args.mode, args.output))
        return 0
    except BinderError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
