"""Publish verified public OwnerRez review totals; never date stale data as fresh."""
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from pathlib import Path

OUT = Path(__file__).parent / "ratings.json"
HOMES = [
    {"key": "lake-hamilton", "name": "Breakaway on Lake Hamilton", "url": "https://book.breakawaystays.com/breakaway-on-lake-hamilton-kayakshot-tubfirepitswings-orp5b742d1x"},
    {"key": "hot-springs", "name": "Hot Springs Breakaway", "url": "https://book.breakawaystays.com/hot-springs-breakaway-orp5b71b48x"},
    {"key": "table-rock", "name": "Breakaway at Table Rock", "url": "https://book.breakawaystays.com/breakaway-at-table-rock-orp5b6e559x"},
]
JSONLD_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)


def find_ratings(obj):
    if isinstance(obj, dict):
        agg = obj.get("aggregateRating")
        if isinstance(agg, dict) and "reviewCount" in agg and "ratingValue" in agg:
            yield agg
        for value in obj.values():
            yield from find_ratings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from find_ratings(value)


def parse_rating(html):
    found = set()
    for block in JSONLD_RE.findall(html):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        for agg in find_ratings(data):
            try:
                rating = Decimal(str(agg["ratingValue"]))
                count = Decimal(str(agg["reviewCount"]))
                if not rating.is_finite() or not count.is_finite():
                    continue
                if not (0 < rating <= 5 and 0 < count <= 1000000 and count == int(count)):
                    continue
                found.add((float(rating.quantize(Decimal("0.01"), rounding=ROUND_DOWN)), int(count)))
            except (InvalidOperation, ValueError, OverflowError, TypeError):
                continue
    return next(iter(found)) if len(found) == 1 else None


def fetch(url):
    last_error = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "BreakawayStays-RatingsRefresh/2.0 (+https://breakawaystays.com)", "Accept": "text/html"})
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as error:
            last_error = error
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise last_error


def main(fetch_page=fetch, out=OUT, now=None):
    try:
        previous = json.loads(out.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        previous = {"homes": {}}
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    homes, problems = {}, []
    for home in HOMES:
        try:
            result = parse_rating(fetch_page(home["url"]))
            if result is None:
                raise ValueError("no unambiguous, valid public aggregate rating")
            rating, count = result
            old = previous.get("homes", {}).get(home["key"], {})
            if old.get("count") and count < old["count"] * 0.8:
                raise ValueError(f"review count unexpectedly fell from {old['count']} to {count}")
            homes[home["key"]] = {"name": home["name"], "rating": rating, "count": count, "url": home["url"], "verified_at": stamp}
        except Exception as error:
            problems.append(f"{home['name']}: {error}")
    if problems or len(homes) != len(HOMES):
        print("Refresh failed; keeping the complete last verified feed and its original date.", file=sys.stderr)
        for problem in problems:
            print("ERROR:", problem, file=sys.stderr)
        return 1
    total = sum(home["count"] for home in homes.values())
    weighted = sum(Decimal(str(home["rating"])) * home["count"] for home in homes.values()) / total
    feed = {"schema_version": 2, "source": "OwnerRez public booking-page guest reviews", "all_verified": True, "updated": stamp, "total_reviews": total, "average_rating": float(weighted.quantize(Decimal("0.01"), rounding=ROUND_DOWN)), "homes": homes}
    temporary = out.with_suffix(".tmp")
    temporary.write_text(json.dumps(feed, indent=2) + "\n")
    temporary.replace(out)
    print(json.dumps(feed, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
