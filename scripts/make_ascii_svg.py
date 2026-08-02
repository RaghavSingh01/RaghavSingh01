#!/usr/bin/env python3
"""
make_ascii_svg.py — convert a prepped grayscale photo into a self-typing,
monochrome ASCII-art SVG.

Design choices (deliberate):
  - Monochrome: one light-gray fill. Per-character rainbow coloring is
    exactly what makes most ASCII portraits look like TV static.
  - High contrast: a busy/bright background washes out to the space
    glyph, so only the subject actually prints.
  - Animation lives entirely inside the SVG (SMIL), since GitHub strips
    <script> and external CSS from READMEs but renders inline SVG
    animation fine via <img>. Each row wipes left-to-right behind a
    clipPath rect, staggered top-to-bottom, then freezes (no looping).

Usage:
    python scripts/make_ascii_svg.py [prepped.png] [output.svg]
"""
import sys
import os
import numpy as np
from PIL import Image

# bright (sparse) -> dark (dense); leading space clears background to nothing
RAMP = " .`:-=+*cs#%@"

COLS = 100          # character grid width
FONT_SIZE = 9        # px
CHAR_W_RATIO = 0.60  # monospace glyph width as a fraction of font-size
LINE_HEIGHT = 1.05    # relative to font-size
FILL_COLOR = "#8b949e"      # GitHub-dark-ish light gray, monochrome
CURSOR_COLOR = "#39d353"    # small green "cursor" block riding the wipe edge
BG = "transparent"

ROW_STAGGER = 0.035   # seconds between each row starting to type
TYPE_DURATION = 0.5   # seconds for a single row to fully wipe in


def image_to_ascii_grid(img_path: str, cols: int):
    img = Image.open(img_path).convert("L")
    w, h = img.size

    char_w_px = FONT_SIZE * CHAR_W_RATIO
    char_h_px = FONT_SIZE * LINE_HEIGHT

    # Preserve the photo's real aspect ratio in character-cell space
    rows = int((h / w) * cols * (char_w_px / char_h_px))
    rows = max(10, rows)

    small = img.resize((cols, rows), Image.LANCZOS)
    arr = np.array(small).astype(np.float32)

    ramp_len = len(RAMP)
    idx = np.clip((arr / 255.0) * (ramp_len - 1), 0, ramp_len - 1).astype(int)

    lines = []
    for r in range(rows):
        line = "".join(RAMP[idx[r, c]] for c in range(cols))
        lines.append(line.rstrip())  # trailing spaces add nothing visually

    return lines, char_w_px, char_h_px


def escape_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_svg(lines, char_w_px, char_h_px) -> str:
    cols = max(len(l) for l in lines) if lines else COLS
    rows = len(lines)

    width = cols * char_w_px + 20
    height = rows * char_h_px + 20
    pad_x, pad_y = 10, 10

    svg_parts = []
    svg_parts.append(
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="Consolas, Menlo, '
        f'\'Courier New\', monospace" font-size="{FONT_SIZE}">'
    )
    svg_parts.append(f'<rect width="100%" height="100%" fill="{BG}"/>')

    defs = ['<defs>']
    body = []

    for i, line in enumerate(lines):
        if not line.strip():
            continue
        y = pad_y + (i + 1) * char_h_px
        row_width = len(line) * char_w_px
        clip_id = f"clip{i}"
        begin_t = i * ROW_STAGGER

        # Clip rect that wipes from 0 width to full width -> left-to-right reveal
        defs.append(
            f'<clipPath id="{clip_id}">'
            f'<rect x="{pad_x}" y="{y - char_h_px}" width="0" height="{char_h_px + 4}">'
            f'<animate attributeName="width" from="0" to="{row_width:.1f}" '
            f'begin="{begin_t:.3f}s" dur="{TYPE_DURATION}s" '
            f'fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
            f'</rect>'
            f'</clipPath>'
        )

        text_escaped = escape_xml(line)
        body.append(
            f'<g clip-path="url(#{clip_id})">'
            f'<text x="{pad_x}" y="{y}" fill="{FILL_COLOR}" '
            f'xml:space="preserve">{text_escaped}</text>'
            f'</g>'
        )

        # Small block cursor riding the wipe edge of each row, fades out
        # once that row finishes typing.
        cursor_w = char_w_px * 0.8
        body.append(
            f'<rect x="{pad_x}" y="{y - char_h_px * 0.85:.1f}" '
            f'width="{cursor_w:.1f}" height="{char_h_px * 0.9:.1f}" '
            f'fill="{CURSOR_COLOR}">'
            f'<animate attributeName="x" from="{pad_x}" to="{pad_x + row_width:.1f}" '
            f'begin="{begin_t:.3f}s" dur="{TYPE_DURATION}s" fill="freeze" '
            f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
            f'<animate attributeName="opacity" values="1;1;0" '
            f'keyTimes="0;0.85;1" begin="{begin_t:.3f}s" dur="{TYPE_DURATION}s" fill="freeze"/>'
            f'</rect>'
        )

    defs.append('</defs>')

    svg_parts.extend(defs)
    svg_parts.extend(body)
    svg_parts.append('</svg>')

    return "\n".join(svg_parts)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "source-photo-prepped.png"
    out = sys.argv[2] if len(sys.argv) > 2 else "avi-ascii.svg"

    print(f"Reading {src} ...")
    lines, char_w, char_h = image_to_ascii_grid(src, COLS)
    print(f"Grid: {len(lines)} rows x {COLS} cols")

    svg = build_svg(lines, char_w, char_h)
    with open(out, "w") as f:
        f.write(svg)
    print(f"Wrote {out} ({len(svg)} bytes)")
