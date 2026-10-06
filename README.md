# Breakaway Stays ratings feed

Once a day, GitHub runs `fetch_ratings.py`. It reads the rating and review count each
OwnerRez booking page already shows publicly, and saves them to `ratings.json`.
breakawaystays.com reads that file and updates its review badges.

- Feed: https://breakawaystays.github.io/BKWY-RATINGS/ratings.json
- Refresh now: Actions tab → "Daily ratings refresh" → Run workflow
- If a booking page can't be read, that home keeps its previous numbers.
- No passwords or API keys are stored here.
