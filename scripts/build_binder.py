#!/usr/bin/env python3
"""Validate and build one care-binder entry with local assets only."""
from __future__ import annotations
import argparse, json, re, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"id", "path", "kind", "subjects", "alt", "caption", "source"}
SOURCE_REQUIRED = {"photographer", "provenance", "rights"}

def load_catalog(entry: Path) -> dict[str, dict]:
    data = json.loads((entry / "assets.json").read_text())
    if data.get("schema_version") != 1 or not isinstance(data.get("assets"), list):
        raise ValueError("assets.json must use schema_version 1 and contain an assets list")
    result = {}
    for record in data["assets"]:
        missing = REQUIRED - record.keys()
        if missing or not SOURCE_REQUIRED <= set(record.get("source", {})):
            raise ValueError(f"asset missing required metadata: {sorted(missing or SOURCE_REQUIRED-set(record.get('source', {})))}")
        if record["id"] in result: raise ValueError(f"duplicate asset ID: {record['id']}")
        path = (entry / record["path"]).resolve()
        if entry.resolve() not in path.parents: raise ValueError(f"asset escapes entry directory: {record['path']}")
        record["resolved_path"] = path
        result[record["id"]] = record
    return result

def selections(page: str) -> tuple[str, list[str]]:
    hero = re.search(r"hero=\{([^}]*)\}", page)
    details = re.search(r"details=\{([^}]*)\}", page)
    if not hero: raise ValueError("page must explicitly select one hero")
    return hero.group(1).strip(), [x.strip() for x in (details.group(1) if details else "").split(",") if x.strip()]

def validate(entry: Path, mode: str) -> tuple[dict, list[str]]:
    catalog, page = load_catalog(entry), (entry / "page.tex").read_text()
    hero, details = selections(page)
    if len(details) > 2: raise ValueError("at most two detail images may be selected")
    chosen = [hero, *details]
    for asset_id in chosen:
        if asset_id not in catalog: raise ValueError(f"selected asset is not cataloged: {asset_id}")
        asset = catalog[asset_id]
        if mode == "final" and (asset["kind"] == "placeholder" or asset["source"]["rights"].strip().lower() in {"", "unknown", "pending", "unresolved"}):
            raise ValueError(f"selected asset is not final-qualified: {asset_id}")
        if asset["kind"] != "placeholder" and not asset["resolved_path"].is_file():
            raise ValueError(f"selected asset file does not exist: {asset['path']}")
        if asset["kind"] != "placeholder":
            with Image.open(asset["resolved_path"]) as image:
                asset["measured"]={"width":image.width,"height":image.height,"format":image.format,"bytes":asset["resolved_path"].stat().st_size}
            slot=(3.30,3.30) if asset_id==hero else (2.05,1.35)
            needed=(round(slot[0]*240),round(slot[1]*240))
            if asset["measured"]["width"]<needed[0] or asset["measured"]["height"]<needed[1]:
                raise ValueError(f"selected asset has insufficient resolution: {asset_id}")
    return catalog, chosen

def build(entry_name: str, mode: str, output: Path) -> None:
    entry = ROOT / "binder/entries" / entry_name
    catalog, chosen = validate(entry, mode)
    if not shutil.which("lualatex"): raise RuntimeError("lualatex not found; install TeX Live with LuaLaTeX")
    hero = catalog[chosen[0]]
    if hero["kind"] == "placeholder":
        hero_tex = r"\begin{tikzpicture}\draw[thin,color=line] (0,0) rectangle (3.30in,3.30in);\draw[color=line] (0,0)--(3.30in,3.30in) (0,3.30in)--(3.30in,0);\node[align=center,font=\sffamily\bfseries\small] at (1.65in,1.65in) {DRAFT~PLACEHOLDER\\SPECIMEN~PHOTO~REQUIRED};\end{tikzpicture}"
    else:
        hero_tex = rf"\includegraphics[width=3.30in,height=3.30in]{{{hero['resolved_path'].as_posix()}}}"
    rendered_details=[]
    for asset_id in chosen[1:]:
        asset=catalog[asset_id]
        if asset["kind"] == "placeholder":
            rendered_details.append(r"\fbox{\parbox[c][1.35in][c]{2.05in}{\centering\sffamily\small DRAFT~DETAIL\\PLACEHOLDER}}")
        else: rendered_details.append(rf"\includegraphics[width=2.05in,height=1.35in]{{{asset['resolved_path'].as_posix()}}}")
    details_tex=(r"\par\vspace{.08in}"+r"\hfill".join(rendered_details)) if rendered_details else ""
    with tempfile.TemporaryDirectory(prefix="aquiloop-binder-") as td:
        td = Path(td); page = td / "entry.tex"; page.write_text((entry / "page.tex").read_text())
        template = (ROOT / "binder/template.tex").read_text().replace("ENTRY_FILE", page.as_posix()).replace("\\BinderMode", mode.upper()).replace("\\BinderHero", hero_tex).replace("\\BinderDetails",details_tex)
        main = td / "main.tex"; main.write_text(template)
        proc = subprocess.run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=td, text=True, capture_output=True)
        if proc.returncode: raise RuntimeError(proc.stdout[-4000:])
        log = (td / "main.log").read_text(errors="replace")
        lines=log.splitlines(); overflow=[]
        for index,line in enumerate(lines):
            if line.startswith("Overfull "): overflow.append(" | ".join(lines[index:index+3]))
        if overflow: raise RuntimeError("layout overflow reported by LuaLaTeX: " + "; ".join(overflow))
        output.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(td / "main.pdf", output)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--entry", required=True); p.add_argument("--mode", choices=("draft","final"), required=True); p.add_argument("--output", type=Path, required=True)
    a=p.parse_args()
    try: build(a.entry,a.mode,a.output)
    except (ValueError,RuntimeError,FileNotFoundError,json.JSONDecodeError) as exc: p.error(str(exc))
if __name__ == "__main__": main()
