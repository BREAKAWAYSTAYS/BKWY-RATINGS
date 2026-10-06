"""
Breakaway Stays: daily ratings refresh.

Reads the public rating and review count that each OwnerRez booking page
already publishes (schema.org AggregateRating in the page's JSON-LD) and
writes them to ratings.json, which GitHub Pages serves to the homepage.

No API keys. Standard library only.

Safety rules:
  * If a page can't be read, that home keeps yesterday's numbers.
  * If a review count suddenly drops by more than 20%, something is likely
    wrong with the page, so we keep the old value and log a warning
    instead of publishing it.
"""

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).parent / "ratings.json"

HOMES = [
    {
        "key": "lake-hamilton",
        "name": "Breakaway on Lake Hamilton",
        "url": "https://book.breakawaystays.com/breakaway-on-lake-hamilton-kayakshot-tubfirepitswings-orp5b742d1x",
    },
    {
        "key": "hot-springs",
        "name": "Hot Springs Breakaway",
        "url": "https://book.breakawaystays.com/hot-springs-breakaway-orp5b71b48x",
    },
    {
        "key": "table-rock",
        "name": "Breakaway at Table Rock",
        "url": "https://book.breakawaystays.com/breakaway-at-table-rock-orp5b6e559x",
    },
]

JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def find_rating(obj):
    """Walk any JSON-LD shape and return the first AggregateRating found."""
    if isinstance(obj, dict):
        agg = obj.get("aggregateRating")
        if isinstance(agg, dict) and "reviewCount" in agg and "ratingValue" in agg:
            return agg
        for v in obj.values():
            hit = find_rating(v)
            if hit:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = find_rating(v)
            if hit:
                return hit
    return None


def parse_rating(html):
    for block in JSONLD_RE.findall(html):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        agg = find_rating(data)
        if agg:
            rating = round(float(agg["ratingValue"]), 2)
            count = int(agg["reviewCount"])
            if 0 < rating <= 5 and count > 0:
                return rating, count
    return None


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BreakawayStays-RatingsRefresh/1.0 (+https://breakawaystays.com)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def load_previous():
    try:
        return json.loads(OUT.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"homes": {}}


def main():
    prev = load_previous()
    homes = {}
    problems = []

    for h in HOMES:
        old = prev.get("homes", {}).get(h["key"])
        try:
            got = parse_rating(fetch(h["url"]))
        except Exception as exc:  # network or HTTP error
            got = None
            problems.append(f"{h['name']}: could not load page ({exc})")

        if got is None:
            if not any(h["name"] in p for p in problems):
                problems.append(f"{h['name']}: no rating found on page")
            if old:
                homes[h["key"]] = old
            continue

        rating, count = got
        if old and count < old["count"] * 0.8:
            problems.append(
                f"{h['name']}: count fell from {old['count']} to {count}; keeping old value"
            )
            homes[h["key"]] = old
            continue

        homes[h["key"]] = {
            "name": h["name"],
            "rating": rating,
            "count": count,
            "url": h["url"],
        }

    if not homes:
        print("No data at all; leaving ratings.json untouched.", file=sys.stderr)
        for p in problems:
            print("WARN:", p, file=sys.stderr)
        return 1

    total = sum(v["count"] for v in homes.values())
    weighted = sum(v["rating"] * v["count"] for v in homes.values()) / total

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_reviews": total,
        # Rounded down to 2 places so the site never overstates the average.
        "average_rating": int(weighted * 100) / 100,
        "homes": homes,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    for p in problems:
        print("WARN:", p, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
