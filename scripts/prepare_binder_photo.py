#!/usr/bin/env python3
"""Create a privacy-conscious, print-qualified JPEG derivative."""
from __future__ import annotations
import argparse, io
from pathlib import Path
from PIL import Image, ImageCms, ImageOps

FRAMES = {"hero": (3.30, 3.30, 500 * 1024), "detail": (2.05, 1.35, 1024 * 1024)}

def prepare(source: Path, output: Path, frame: str, crop: tuple[int,int,int,int] | None, overwrite: bool) -> dict:
    if source.resolve() == output.resolve(): raise ValueError("output must differ from the original")
    if output.exists() and not overwrite: raise FileExistsError("output exists; pass --overwrite to replace the derivative")
    fw, fh, goal = FRAMES[frame]
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        if crop:
            x,y,w,h=crop
            if min(x,y,w,h)<0 or not w or not h or x+w>image.width or y+h>image.height: raise ValueError("crop is outside the oriented image")
            image=image.crop((x,y,x+w,y+h))
        target_ratio=fw/fh
        if abs(image.width/image.height-target_ratio)>0.002:
            raise ValueError(f"crop must match the {fw:.2f}:{fh:.2f} printed-frame ratio")
        minimum=(round(fw*240),round(fh*240)); preferred=(round(fw*300),round(fh*300))
        if image.width<minimum[0] or image.height<minimum[1]: raise ValueError(f"insufficient crop resolution: {image.width}x{image.height}; need at least {minimum[0]}x{minimum[1]}")
        image.thumbnail(preferred, Image.Resampling.LANCZOS)  # one resize, never upscale
        profile=opened.info.get("icc_profile")
        if profile:
            try: image=ImageCms.profileToProfile(image, ImageCms.ImageCmsProfile(io.BytesIO(profile)), ImageCms.createProfile("sRGB"), outputMode="RGB")
            except ImageCms.PyCMSError: image=image.convert("RGB")
        else: image=image.convert("RGB")
        output.parent.mkdir(parents=True,exist_ok=True)
        quality=88
        while True:
            image.save(output,"JPEG",quality=quality,optimize=True,icc_profile=ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
            if output.stat().st_size<=min(goal,1024*1024) or quality<=70: break
            quality-=3
    size=output.stat().st_size
    if size>1024*1024: output.unlink(); raise ValueError("cannot meet 1 MiB ceiling without silently sacrificing resolution")
    return {"dimensions":f"{image.width}x{image.height}","bytes":size,"effective_ppi":round(min(image.width/fw,image.height/fh),1),"quality":quality}

def main():
    p=argparse.ArgumentParser(description="Prepare a separate sRGB JPEG derivative; the source is never modified.")
    p.add_argument("source",type=Path); p.add_argument("output",type=Path); p.add_argument("--frame",choices=FRAMES,required=True)
    p.add_argument("--crop",nargs=4,type=int,metavar=("X","Y","WIDTH","HEIGHT"),help="intentional crop in pixels after EXIF orientation")
    p.add_argument("--overwrite",action="store_true",help="explicitly allow replacement of an existing derivative")
    a=p.parse_args()
    try: result=prepare(a.source,a.output,a.frame,tuple(a.crop) if a.crop else None,a.overwrite)
    except (ValueError,FileExistsError,OSError) as exc: p.error(str(exc))
    print(f"wrote {a.output}: {result['dimensions']}, {result['bytes']} bytes, {result['effective_ppi']} effective ppi, JPEG quality {result['quality']}")
if __name__ == "__main__": main()
