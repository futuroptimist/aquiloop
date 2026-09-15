"""Validation and TeX resolution helpers for the care-binder proof."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

REQUIRED = {"id", "path", "kind", "subjects", "alt", "caption", "source"}
FRAMES = {"hero": (3.30, 3.30), "detail": (2.05, 1.35)}


class BinderError(ValueError):
    pass


@dataclass(frozen=True)
class Asset:
    record: dict
    path: Path
    pixels: tuple[int, int] | None
    format: str | None
    bytes: int | None


def load_catalog(entry_dir: Path) -> dict[str, Asset]:
    raw = json.loads((entry_dir / "assets.json").read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise BinderError("assets.json must use supported schema_version 1")
    result: dict[str, Asset] = {}
    for record in raw.get("assets", []):
        missing = REQUIRED - record.keys()
        source = record.get("source", {})
        if missing or not {"provenance", "photographer", "rights"} <= source.keys():
            raise BinderError(f"asset {record.get('id', '<unknown>')} lacks required metadata")
        asset_id = record["id"]
        if asset_id in result:
            raise BinderError(f"duplicate asset ID: {asset_id}")
        path = (entry_dir / record["path"]).resolve()
        if entry_dir.resolve() not in path.parents:
            raise BinderError(f"asset path escapes entry directory: {record['path']}")
        pixels = image_format = byte_count = None
        if record["kind"] != "placeholder":
            if not path.is_file():
                raise BinderError(f"asset file does not exist: {record['path']}")
            with Image.open(path) as image:
                pixels, image_format = image.size, image.format
            byte_count = path.stat().st_size
        result[asset_id] = Asset(record, path, pixels, image_format, byte_count)
    return result


def validate_selection(catalog: dict[str, Asset], hero: str, details: list[str], mode: str) -> list[Asset]:
    if not hero:
        raise BinderError("exactly one hero asset ID is required")
    if len(details) > 2:
        raise BinderError("at most two detail asset IDs may be selected")
    selected = []
    for asset_id in [hero, *details]:
        if asset_id not in catalog:
            raise BinderError(f"selected asset ID is absent from catalog: {asset_id}")
        asset = catalog[asset_id]
        if mode == "final" and asset.record["kind"] == "placeholder":
            raise BinderError(f"final mode rejects selected placeholder: {asset_id}")
        if mode == "final" and asset.record["source"]["rights"].strip().lower() in {"", "unknown", "unresolved"}:
            raise BinderError(f"final mode rejects unresolved rights: {asset_id}")
        selected.append(asset)
    return selected


def latex_escape(value: str) -> str:
    for old, new in [("\\", r"\textbackslash{}"), ("_", r"\_"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#")]:
        value = value.replace(old, new)
    return value


def placement_tex(asset: Asset, role: str) -> str:
    width, height = FRAMES[role]
    if asset.record["kind"] == "placeholder":
        label = latex_escape(f"DRAFT PHOTO PLACEHOLDER — {asset.record['id']}")
        return (rf"\fcolorbox{{rust}}{{pale}}{{\parbox[c][{height - .03:.2f}in][c]{{{width - .03:.2f}in}}"
                rf"{{\centering\sffamily\bfseries\color{{rust}} {label}\par}}}}")
    assert asset.pixels
    minimum = (round(width * 240), round(height * 240))
    if asset.pixels[0] < minimum[0] or asset.pixels[1] < minimum[1]:
        raise BinderError(f"{asset.record['id']} is {asset.pixels[0]}x{asset.pixels[1]} px; {role} requires at least {minimum[0]}x{minimum[1]} px")
    path = latex_escape(asset.path.as_posix())
    return rf"\includegraphics[width={width:.2f}in,height={height:.2f}in]{{{path}}}"
