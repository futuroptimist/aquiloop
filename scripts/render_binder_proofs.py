"""Render the existing Poppler proof options, optionally reusing exact pages in one job."""
from __future__ import annotations
import argparse
import io
from pathlib import Path
import subprocess
from pypdf import PdfReader, PdfWriter
from binder_reuse import activate, digest


def page_bytes(page):
    writer = PdfWriter()
    writer.add_page(page)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def render(pdf, prefix, *, dpi=150, gray=False, first=1, last=None, session=None):
    reader = PdfReader(pdf)
    count = len(reader.pages)
    last = count if last is None else last
    if not 1 <= first <= last <= count or dpi <= 0:
        raise ValueError('invalid proof range or resolution')
    prefix.parent.mkdir(parents=True, exist_ok=True)
    options = ['-r', str(dpi), *(['-gray'] if gray else []), '-png']
    # Catalog-level forms, color intents, optional content, etc. can affect page
    # rendering. Do not normalize or reuse such a document; render it cold.
    eligible = set(reader.trailer['/Root']) == {'/Type', '/Pages'}
    if session is None or not eligible:
        subprocess.run(['pdftoppm', '-f', str(first), '-l', str(last), *options, str(pdf), str(prefix)], check=True)
        return
    toolchain = session.toolchain()
    implementation = session.snapshot([Path(__file__), Path(__file__).with_name('binder_reuse.py')])
    for number in range(first, last + 1):
        key = session.key('raster', {'page': digest(page_bytes(reader.pages[number - 1])),
                                    'options': options, 'toolchain': toolchain,
                                    'implementation': implementation})
        output = Path(f'{prefix}-{number:0{len(str(count))}d}.png')
        if not session.restore('raster', key, output):
            # Rasterize the original document, not the normalized key document.
            subprocess.run(['pdftoppm', '-f', str(number), '-l', str(number), *options, str(pdf), str(prefix)], check=True)
            from PIL import Image
            with Image.open(output) as image:
                image.verify()
            session.save('raster', key, output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reuse-session', type=Path)
    parser.add_argument('-r', type=int, default=150)
    parser.add_argument('-f', type=int, default=1)
    parser.add_argument('-l', type=int)
    parser.add_argument('-gray', action='store_true')
    parser.add_argument('-png', action='store_true', required=True)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('prefix', type=Path)
    args = parser.parse_args()
    with activate(args.reuse_session) as session:
        render(args.pdf, args.prefix, dpi=args.r, gray=args.gray, first=args.f, last=args.l, session=session)


if __name__ == '__main__':
    main()
