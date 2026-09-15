#!/usr/bin/env python3
"""Create a print-sized, metadata-clean JPEG derivative for the care binder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

FRAMES = {"hero": (3.30, 3.30, 500 * 1024), "detail": (2.05, 1.35, 1024 * 1024)}


def prepare(source: Path, output: Path, frame: str, focus: tuple[float, float], overwrite: bool = False) -> dict:
    if source.resolve() == output.resolve():
        raise ValueError("input and output must be different files")
    if output.exists() and not overwrite:
        raise ValueError("output exists; pass --overwrite to replace the derivative")
    width_in, height_in, byte_goal = FRAMES[frame]
    with Image.open(source) as opened:
        oriented = ImageOps.exif_transpose(opened)
        rgb = oriented.convert("RGB")
        target_ratio = width_in / height_in
        width, height = rgb.size
        if width / height > target_ratio:
            crop_width, crop_height = round(height * target_ratio), height
        else:
            crop_width, crop_height = width, round(width / target_ratio)
        left = round((width - crop_width) * focus[0])
        top = round((height - crop_height) * focus[1])
        cropped = rgb.crop((left, top, left + crop_width, top + crop_height))
        minimum = (round(width_in * 240), round(height_in * 240))
        preferred = (round(width_in * 300), round(height_in * 300))
        if cropped.width < minimum[0] or cropped.height < minimum[1]:
            raise ValueError(f"crop is {cropped.width}x{cropped.height} px; {frame} requires at least {minimum[0]}x{minimum[1]} px")
        target = (min(cropped.width, preferred[0]), min(cropped.height, preferred[1]))
        derivative = cropped.resize(target, Image.Resampling.LANCZOS) if cropped.size != target else cropped.copy()
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        output.parent.mkdir(parents=True, exist_ok=True)
        quality = 90
        while True:
            derivative.save(output, "JPEG", quality=quality, optimize=True, progressive=True, icc_profile=profile)
            if output.stat().st_size <= byte_goal or quality <= 70:
                break
            quality -= 5
    byte_count = output.stat().st_size
    if byte_count > 1024 * 1024:
        output.unlink(missing_ok=True)
        raise ValueError("cannot meet the 1 MiB ceiling without silently reducing required resolution")
    return {
        "dimensions": derivative.size,
        "bytes": byte_count,
        "effective_ppi": (round(derivative.width / width_in, 1), round(derivative.height / height_in, 1)),
        "quality": quality,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="camera original (retain outside git)")
    parser.add_argument("output", type=Path, help="separate JPEG derivative")
    parser.add_argument("--frame", choices=FRAMES, required=True, help="printed placement contract")
    parser.add_argument("--focus", nargs=2, type=float, default=(0.5, 0.5), metavar=("X", "Y"), help="crop focus from 0 (left/top) to 1 (right/bottom)")
    parser.add_argument("--overwrite", action="store_true", help="explicitly replace an existing derivative")
    args = parser.parse_args()
    if not all(0 <= value <= 1 for value in args.focus):
        parser.error("--focus values must be between 0 and 1")
    try:
        result = prepare(args.input, args.output, args.frame, tuple(args.focus), args.overwrite)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    width, height = result["dimensions"]
    x_ppi, y_ppi = result["effective_ppi"]
    print(f"wrote {args.output}: {width}x{height} px, {result['bytes']} bytes, {x_ppi}x{y_ppi} effective ppi, JPEG quality {result['quality']}")
    if result["bytes"] > FRAMES[args.frame][2]:
        print("warning: size goal was not reached; resolution was preserved", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
