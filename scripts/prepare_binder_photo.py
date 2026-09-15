#!/usr/bin/env python3
"""Create a privacy-conscious, print-sized JPEG derivative."""
from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

FRAMES = {"hero": (3.30, 3.30, 500 * 1024), "detail": (2.05, 1.35, 1024 * 1024)}


def crop_box(value: str) -> tuple[int, int, int, int]:
    try:
        box = tuple(int(x) for x in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("crop must be left,top,right,bottom") from exc
    if len(box) != 4:
        raise argparse.ArgumentTypeError("crop must contain four integers")
    return box  # type: ignore[return-value]


def prepare(source: Path, output: Path, frame: str, crop: tuple[int, int, int, int] | None, overwrite: bool) -> dict:
    if source.resolve() == output.resolve():
        raise ValueError("output must differ from the original")
    if output.exists() and not overwrite:
        raise ValueError("output exists; pass --overwrite to replace the derivative")
    original = source.read_bytes()
    with Image.open(io.BytesIO(original)) as opened:
        image = ImageOps.exif_transpose(opened)
        if crop:
            if crop[0] < 0 or crop[1] < 0 or crop[2] > image.width or crop[3] > image.height or crop[2] <= crop[0] or crop[3] <= crop[1]:
                raise ValueError("crop is outside the oriented image")
            image = image.crop(crop)
        width_in, height_in, target_bytes = FRAMES[frame]
        ratio = width_in / height_in
        if abs(image.width / image.height - ratio) > .005:
            raise ValueError(f"crop aspect must match the {width_in:.2f} x {height_in:.2f} inch frame")
        ppi = min(image.width / width_in, image.height / height_in)
        if ppi < 240:
            raise ValueError(f"insufficient effective resolution: {ppi:.1f} ppi (minimum 240)")
        icc = image.info.get("icc_profile")
        if icc:
            image = ImageCms.profileToProfile(image, ImageCms.ImageCmsProfile(io.BytesIO(icc)), ImageCms.createProfile("sRGB"), outputMode="RGB")
        else:
            image = image.convert("RGB")
        max_size = (round(width_in * 300), round(height_in * 300))
        if image.width > max_size[0] or image.height > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)  # one resize, never upscale
        output.parent.mkdir(parents=True, exist_ok=True)
        quality = 88
        while True:
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=quality, optimize=True, icc_profile=ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
            if len(buffer.getvalue()) <= target_bytes or quality <= 72:
                break
            quality -= 4
        if len(buffer.getvalue()) > 1024 * 1024:
            raise ValueError("cannot meet 1 MiB ceiling without silently sacrificing required resolution")
        output.write_bytes(buffer.getvalue())
    if source.read_bytes() != original:
        raise RuntimeError("original changed unexpectedly")
    return {"width": image.width, "height": image.height, "bytes": output.stat().st_size, "effective_ppi": min(image.width / width_in, image.height / height_in), "preferred_300_ppi": min(image.width / width_in, image.height / height_in) >= 300}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--frame", choices=FRAMES, required=True)
    parser.add_argument("--crop", type=crop_box, help="deliberate crop after EXIF orientation: left,top,right,bottom")
    parser.add_argument("--overwrite", action="store_true", help="explicitly replace an existing derivative")
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.output, args.frame, args.crop, args.overwrite)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"error: {exc}\n")
    print(f"wrote {args.output}: {result['width']} x {result['height']} px, {result['bytes']} bytes, {result['effective_ppi']:.1f} effective ppi; 300-ppi preference {'met' if result['preferred_300_ppi'] else 'not met'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
