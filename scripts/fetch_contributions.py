#!/usr/bin/env python3
"""
fetch_contributions.py — pull a user's real contribution calendar with
zero auth. GitHub serves the calendar as public HTML at
https://github.com/users/<username>/contributions — the same fragment
the profile page itself embeds. No GraphQL API, no personal access token.

Usage:
    python scripts/fetch_contributions.py [username]
Output:
    data/contributions.json
"""
import sys
import os
import json
import datetime
import requests
from bs4 import BeautifulSoup

USERNAME = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GH_USERNAME", "RaghavSingh01")
URL = f"https://github.com/users/{USERNAME}/contributions"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "contributions.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (profile-readme-bot; +https://github.com)"
}


def fetch_days():
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Current GitHub markup: each day is a <td class="ContributionCalendar-day">
    # with data-date/data-level/id, but the human-readable count lives in a
    # separate <tool-tip for="{cell-id}">N contributions on <date>.</tool-tip>
    # element — not inline on the cell itself. Build an id -> tooltip-text map
    # first, then join by id.
    tooltip_by_target = {}
    for tip in soup.select("tool-tip[for]"):
        tooltip_by_target[tip.get("for")] = tip.get_text(strip=True)

    def parse_count(tooltip_text: str) -> int:
        if not tooltip_text:
            return 0
        if tooltip_text.lower().startswith("no contributions"):
            return 0
        first_tok = tooltip_text.split(" ")[0]
        return int(first_tok) if first_tok.isdigit() else 0

    days = []
    cells = soup.select("td.ContributionCalendar-day[data-date]")
    for cell in cells:
        date_str = cell.get("data-date")
        if not date_str:
            continue
        level = int(cell.get("data-level", 0))
        tooltip_text = tooltip_by_target.get(cell.get("id"), "")
        count = parse_count(tooltip_text)
        days.append({"date": date_str, "count": count, "level": level})

    days.sort(key=lambda d: d["date"])
    return days


def derive_stats(days):
    if not days:
        return {}

    total = sum(d["count"] for d in days)

    # current streak: consecutive days with count > 0, ending at most recent day
    current_streak = 0
    for d in reversed(days):
        if d["count"] > 0:
            current_streak += 1
        else:
            break

    # longest streak overall
    longest_streak = 0
    running = 0
    for d in days:
        if d["count"] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    best_day = max(days, key=lambda d: d["count"])

    monthly = {}
    for d in days:
        month_key = d["date"][:7]  # YYYY-MM
        monthly[month_key] = monthly.get(month_key, 0) + d["count"]

    return {
        "total_contributions": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": {"date": best_day["date"], "count": best_day["count"]},
        "monthly_totals": monthly,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    print(f"Fetching {URL} ...")
    days = fetch_days()
    print(f"Parsed {len(days)} day cells")

    stats = derive_stats(days)
    print(f"Total contributions (visible range): {stats.get('total_contributions')}")
    print(f"Current streak: {stats.get('current_streak')}  Longest streak: {stats.get('longest_streak')}")

    out = {"username": USERNAME, "days": days, "stats": stats}
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {OUT_PATH}")
