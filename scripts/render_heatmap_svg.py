#!/usr/bin/env python3
"""
render_heatmap_svg.py — draw data/contributions.json as the classic
53-week x 7-day calendar of rounded, colored boxes, GitHub-green style.

Reveals once with a diagonal, line-after-line slide-down (plays on load,
then freezes — no looping "glow"). Adds a Less->More legend and a stats
footer line.

Usage:
    python scripts/render_heatmap_svg.py
Output:
    contrib-heatmap.svg
"""
import os
import json
import datetime

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
# none -> brightest (level 5 is a neon top end; GitHub itself only uses 0-4,
# level 5 is reserved as a rarely-hit "on fire" tier for very high days)

CELL = 11
GAP = 3
LEFT_PAD = 30     # room for day-of-week labels
TOP_PAD = 24      # room for month labels
BOTTOM_PAD = 46   # room for legend + stats footer

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

STAGGER = 0.018     # seconds between diagonal reveal steps
DUR = 0.35


def load_data(path):
    with open(path) as f:
        return json.load(f)


def bucket_into_weeks(days):
    """Arrange day dicts into GitHub's week-column layout: columns are
    weeks (Sun-Sat), so the grid is indexed [week_index][weekday]."""
    if not days:
        return []

    parsed = []
    for d in days:
        dt = datetime.date.fromisoformat(d["date"])
        parsed.append((dt, d))
    parsed.sort(key=lambda x: x[0])

    first_date = parsed[0][0]
    # Roll back to the preceding Sunday so week columns align like GitHub's
    start = first_date - datetime.timedelta(days=(first_date.weekday() + 1) % 7)

    weeks = []
    week = [None] * 7
    cursor = start
    idx = 0
    last_date = parsed[-1][0]

    data_by_date = {dt: d for dt, d in parsed}

    while cursor <= last_date:
        weekday = (cursor.weekday() + 1) % 7  # 0=Sun ... 6=Sat
        day_data = data_by_date.get(cursor)
        week[weekday] = day_data
        if weekday == 6:
            weeks.append(week)
            week = [None] * 7
        cursor += datetime.timedelta(days=1)
    if any(c is not None for c in week):
        weeks.append(week)

    return weeks


def month_label_positions(weeks):
    labels = []
    last_month = None
    for wi, week in enumerate(weeks):
        for day in week:
            if day is None:
                continue
            dt = datetime.date.fromisoformat(day["date"])
            if dt.day <= 7 and dt.month != last_month:
                labels.append((wi, MONTH_ABBR[dt.month - 1]))
                last_month = dt.month
            break
    return labels


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(data):
    days = data.get("days", [])
    stats = data.get("stats", {})
    username = data.get("username", "")

    weeks = bucket_into_weeks(days)
    n_weeks = len(weeks)

    width = LEFT_PAD + n_weeks * (CELL + GAP) + 20
    height = TOP_PAD + 7 * (CELL + GAP) + BOTTOM_PAD

    parts = []
    parts.append(
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="Consolas, Menlo, \'Courier New\', monospace">'
    )
    parts.append('<rect width="100%" height="100%" fill="transparent"/>')

    # month labels
    for wi, label in month_label_positions(weeks):
        x = LEFT_PAD + wi * (CELL + GAP)
        parts.append(f'<text x="{x}" y="{TOP_PAD - 8}" font-size="10" fill="#8b949e">{label}</text>')

    # day-of-week labels (Mon/Wed/Fri, GitHub's convention)
    dow_labels = {1: "Mon", 3: "Wed", 5: "Fri"}
    for wd, label in dow_labels.items():
        y = TOP_PAD + wd * (CELL + GAP) + CELL - 2
        parts.append(f'<text x="0" y="{y}" font-size="9" fill="#8b949e">{label}</text>')

    # diagonal stagger: step index = week + weekday, so cells fill in a
    # top-left -> bottom-right diagonal sweep like the doc describes
    for wi, week in enumerate(weeks):
        for wd, day in enumerate(week):
            if day is None:
                continue
            level = max(0, min(day.get("level", 0), len(PALETTE) - 1))
            color = PALETTE[level]
            x = LEFT_PAD + wi * (CELL + GAP)
            y = TOP_PAD + wd * (CELL + GAP)
            step = wi + wd
            begin_t = step * STAGGER
            date_label = day["date"]
            count = day.get("count", 0)
            title = f"{count} contribution{'s' if count != 1 else ''} on {date_label}"

            parts.append(
                f'<rect x="{x}" y="{y - 6}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{color}" opacity="0">'
                f'<title>{esc(title)}</title>'
                f'<animate attributeName="opacity" from="0" to="1" '
                f'begin="{begin_t:.3f}s" dur="{DUR}s" fill="freeze"/>'
                f'<animate attributeName="y" from="{y - 6}" to="{y}" '
                f'begin="{begin_t:.3f}s" dur="{DUR}s" fill="freeze" '
                f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
                f'</rect>'
            )

    # legend: Less -> More
    legend_y = TOP_PAD + 7 * (CELL + GAP) + 20
    legend_x = LEFT_PAD
    parts.append(f'<text x="{legend_x}" y="{legend_y + 9}" font-size="10" fill="#8b949e">Less</text>')
    lx = legend_x + 32
    for color in PALETTE[:5]:
        parts.append(f'<rect x="{lx}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}"/>')
        lx += CELL + GAP
    parts.append(f'<text x="{lx + 4}" y="{legend_y + 9}" font-size="10" fill="#8b949e">More</text>')

    # stats footer
    total = stats.get("total_contributions", sum(d.get("count", 0) for d in days))
    streak = stats.get("current_streak", 0)
    longest = stats.get("longest_streak", 0)
    footer = f"{total:,} contributions in the last year  ·  current streak {streak}  ·  longest streak {longest}"
    parts.append(
        f'<text x="{legend_x}" y="{legend_y + 28}" font-size="11" fill="#c9d1d9">{esc(footer)}</text>'
    )

    parts.append('</svg>')
    return "\n".join(parts)


if __name__ == "__main__":
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "contributions.json")
    out_path = os.path.join(os.path.dirname(__file__), "..", "contrib-heatmap.svg")

    data = load_data(data_path)
    svg = build_svg(data)
    with open(out_path, "w") as f:
        f.write(svg)
    print(f"Wrote {out_path}")
