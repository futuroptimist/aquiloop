#!/usr/bin/env python3
"""Create a non-destructive, print-qualified JPEG derivative."""
from __future__ import annotations

import argparse
import io
from pathlib import Path

FRAMES = {"hero": (3.30, 3.30, 500 * 1024), "detail": (2.05, 1.35, 1024 * 1024)}


def prepare(source: Path, output: Path, frame: str, crop: tuple[int, int, int, int] | None,
            overwrite: bool = False) -> dict:
    from PIL import Image, ImageCms, ImageOps
    if source.resolve() == output.resolve():
        raise ValueError("output must differ from the original")
    if output.exists() and not overwrite:
        raise FileExistsError("output exists; pass --overwrite to replace the derivative")
    original_bytes = source.read_bytes()
    with Image.open(io.BytesIO(original_bytes)) as opened:
        image = ImageOps.exif_transpose(opened)
        if crop:
            x, y, width, height = crop
            if min(x, y, width, height) < 0 or x + width > image.width or y + height > image.height:
                raise ValueError("crop lies outside the oriented image")
            image = image.crop((x, y, x + width, y + height))
        frame_w, frame_h, byte_goal = FRAMES[frame]
        expected = frame_w / frame_h
        if abs(image.width / image.height - expected) > 0.005:
            raise ValueError(f"crop ratio must match {frame_w}:{frame_h} printed frame")
        ppi = min(image.width / frame_w, image.height / frame_h)
        if ppi < 240:
            raise ValueError(f"insufficient resolution after crop: {ppi:.1f} ppi (240 required)")
        target = (round(frame_w * 300), round(frame_h * 300))
        if image.width > target[0] and image.height > target[1]:
            image.thumbnail(target, Image.Resampling.LANCZOS)  # one resize; never upscale
        if image.mode != "RGB":
            image = image.convert("RGB")
        icc = opened.info.get("icc_profile")
        if icc:
            source_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            image = ImageCms.profileToProfile(image, source_profile,
                                              ImageCms.createProfile("sRGB"), outputMode="RGB")
        output.parent.mkdir(parents=True, exist_ok=True)
        quality = 90
        while True:
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True,
                       icc_profile=ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
            if len(buffer.getvalue()) <= byte_goal or quality <= 72:
                break
            quality -= 3
        if len(buffer.getvalue()) > 1024 * 1024:
            raise ValueError("cannot meet 1 MiB ceiling without risking required resolution")
        output.write_bytes(buffer.getvalue())
    if source.read_bytes() != original_bytes:
        raise RuntimeError("original changed unexpectedly")
    result = {"width": image.width, "height": image.height, "bytes": output.stat().st_size,
              "effective_ppi": round(min(image.width / frame_w, image.height / frame_h), 1)}
    return result


def crop_value(value: str) -> tuple[int, int, int, int]:
    try:
        values = tuple(int(part) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("crop must be x,y,width,height") from exc
    if len(values) != 4:
        raise argparse.ArgumentTypeError("crop must be x,y,width,height")
    return values  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="camera original (kept unchanged and outside git)")
    parser.add_argument("output", type=Path, help="separate JPEG derivative")
    parser.add_argument("--frame", choices=FRAMES, required=True)
    parser.add_argument("--crop", type=crop_value, help="deliberate crop x,y,width,height after orientation")
    parser.add_argument("--overwrite", action="store_true", help="explicitly replace an existing derivative")
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.output, args.frame, args.crop, args.overwrite)
    except (ValueError, FileExistsError, OSError) as exc:
        parser.error(str(exc))
    print(f"{result['width']}x{result['height']} px; {result['bytes']} bytes; "
          f"{result['effective_ppi']:.1f} effective ppi in {args.frame} frame")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
