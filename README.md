# Breakaway Stays live guest-review statistics

This public repository contains only aggregate ratings, counts, source URLs,
refresh code and tests. No guest contacts, reservations, credentials or private
OwnerRez data are published.

`fetch_ratings.py` reads the aggregate ratings already published on the three
OwnerRez booking pages. These are **guest reviews shown by OwnerRez**, not an
Airbnb-only count. The portfolio rating is weighted by review count and rounded
down to two decimal places.

## Automatic updates

- GitHub Actions refreshes every six hours, on relevant code changes, and via
  the **Run workflow** button. Scheduled jobs can be delayed by GitHub.
- Every run tests the parser, weighted calculation and stale-data behavior.
- All three homes must verify before publishing. A failed request, ambiguous
  rating, invalid value or count drop over 20% fails the job and leaves the
  complete last verified feed and its original date unchanged.
- Public requests retry three times. No API keys are needed.

## Website connection

The Market My STR homepage loads `ratings-live.js` from this repository's
GitHub Pages site. The script reads `ratings.json` directly from the public
`main` branch, avoiding a dependency on Pages rebuilding for each bot commit.
It refreshes on each visit, every five minutes while visible, and when a tab is
reopened. Network failures retain the verified fallback and retry after 30
seconds; the verification date is never replaced with the visitor's date.

Keep the following hooks in any homepage redesign:

```html
<strong data-bas-review-total>210</strong>
<span data-bas-review-total-label>Guest reviews · checked Nov 8, 2026</span>
<strong data-bas-review-average>4.99&#9733;</strong>
<span data-bas-review-average-label>Average guest rating · checked Nov 8, 2026</span>
<span data-bas-review-summary="lake-hamilton">5.00&#9733; · 65 guest reviews</span>
<span data-bas-review-summary="hot-springs">4.99&#9733; · 93 guest reviews</span>
<span data-bas-review-summary="table-rock">5.00&#9733; · 52 guest reviews</span>
```

The date and values above are fallback examples, not current-data promises.
Use the latest verified feed when preparing a new fallback. The live labels
become **last verified** if the source is over 48 hours old. The script also
keeps the three matching property JSON-LD aggregate ratings in sync.
Airbnb awards such as Guest Favorite and Top 5% are separate from these totals.

Add this once in the hub's site Head tracking code, preserving existing code:

```html
<script defer src="https://breakawaystays.github.io/BKWY-RATINGS/ratings-live.js?v=20261109-1"></script>
```

Public JSON mirror: https://breakawaystays.github.io/BKWY-RATINGS/ratings.json

## Verification

```sh
python -m unittest -q test_ratings.py
node --test test-ratings-live.cjs
```

After publishing, confirm the website's total, date and three property badges
match `ratings.json`, test mobile layout, and verify the existing calendar links.
