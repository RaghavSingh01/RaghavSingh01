#!/usr/bin/env python3
"""
make_info_card.py — hand-authored neofetch-style SVG info panel.

Rows fade + slide in on a short stagger, like the panel is printing next
to the ASCII portrait. Set STATIC=1 to emit a frozen final-state frame
(useful for local Quick Look previews where SMIL doesn't animate).

Usage:
    python scripts/make_info_card.py
    STATIC=1 python scripts/make_info_card.py
"""
import os

WIDTH = 490
LINE_HEIGHT = 26
PAD_TOP = 56
PAD_X = 22
FONT = "Consolas, Menlo, 'Courier New', monospace"

BG = "#0d1117"
BORDER = "#30363d"
TITLEBAR = "#161b22"
DOT_RED, DOT_YEL, DOT_GRN = "#ff5f56", "#ffbd2e", "#27c93f"
KEY_COLOR = "#39d353"     # neofetch-green keys
VAL_COLOR = "#c9d1d9"     # near-white values
DIM_COLOR = "#8b949e"
ACCENT = "#58a6ff"

STATIC = os.environ.get("STATIC") == "1"

ROWS = [
    ("user", "raghav@github", None),
    ("---", "", None),
    ("Now", "Associate Software Developer @ Cyberbells", None),
    ("Prev", "Fullstack Trainee @ Masai School", None),
    ("Stack", "Go · Node.js · React · PostgreSQL", None),
    ("Highlights", "Integrated delivery APIs live across 100+ stores", None),
    ("", "Migrated 100+ client stores to a new production DB", None),
    ("Focus", "Backend systems · distributed services", None),
]

STAGGER = 0.12
DUR = 0.45


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg() -> str:
    height = PAD_TOP + LINE_HEIGHT * len(ROWS) + 26

    parts = []
    parts.append(
        f'<svg viewBox="0 0 {WIDTH} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="{FONT}" font-size="14">'
    )

    # card background + border
    parts.append(
        f'<rect x="1" y="1" width="{WIDTH - 2}" height="{height - 2}" rx="10" '
        f'fill="{BG}" stroke="{BORDER}" stroke-width="1"/>'
    )

    # title bar
    parts.append(f'<path d="M1,11 a10,10 0 0 1 10,-10 h{WIDTH - 22} a10,10 0 0 1 10,10 v24 h-{WIDTH - 2} z" fill="{TITLEBAR}"/>')
    parts.append(f'<circle cx="22" cy="23" r="6" fill="{DOT_RED}"/>')
    parts.append(f'<circle cx="42" cy="23" r="6" fill="{DOT_YEL}"/>')
    parts.append(f'<circle cx="62" cy="23" r="6" fill="{DOT_GRN}"/>')
    parts.append(
        f'<text x="{WIDTH/2}" y="27" text-anchor="middle" fill="{DIM_COLOR}" '
        f'font-size="12">neofetch</text>'
    )

    y = PAD_TOP
    for i, (key, val, _) in enumerate(ROWS):
        begin_t = i * STAGGER

        if key == "---":
            line_y = y
            content = (
                f'<line x1="{PAD_X}" y1="{line_y - 5}" x2="{WIDTH - PAD_X}" '
                f'y2="{line_y - 5}" stroke="{BORDER}" stroke-width="1"/>'
            )
        elif key == "user":
            content = (
                f'<text x="{PAD_X}" y="{y}" fill="{ACCENT}" font-weight="bold">{esc(val)}</text>'
            )
        elif key == "":
            # continuation line (no key label), slightly indented
            content = (
                f'<text x="{PAD_X + 96}" y="{y}" fill="{VAL_COLOR}">{esc(val)}</text>'
            )
        else:
            content = (
                f'<text x="{PAD_X}" y="{y}" fill="{KEY_COLOR}" font-weight="bold">{esc(key)}</text>'
                f'<text x="{PAD_X + 96}" y="{y}" fill="{VAL_COLOR}">{esc(val)}</text>'
            )

        if STATIC:
            parts.append(f'<g opacity="1">{content}</g>')
        else:
            parts.append(
                f'<g opacity="0" transform="translate(-8,0)">'
                f'{content}'
                f'<animate attributeName="opacity" from="0" to="1" '
                f'begin="{begin_t:.2f}s" dur="{DUR}s" fill="freeze"/>'
                f'<animateTransform attributeName="transform" type="translate" '
                f'from="-8,0" to="0,0" begin="{begin_t:.2f}s" dur="{DUR}s" '
                f'fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
                f'</g>'
            )
        y += LINE_HEIGHT

    parts.append('</svg>')
    return "\n".join(parts)


if __name__ == "__main__":
    svg = build_svg()
    out = "info-card.svg"
    with open(out, "w") as f:
        f.write(svg)
    print(f"Wrote {out} ({'static' if STATIC else 'animated'})")
