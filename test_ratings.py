import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
import fetch_ratings as ratings

def page(value=4.99, count=70):
    return '<script type="application/ld+json">' + json.dumps({'@type': 'VacationRental', 'aggregateRating': {'ratingValue': value, 'reviewCount': count}}) + '</script>'

class RatingRegressionTests(unittest.TestCase):
    def test_invalid_and_ambiguous_values_are_rejected(self):
        self.assertEqual(ratings.parse_rating(page('4.99', '70')), (4.99, 70))
        self.assertIsNone(ratings.parse_rating(page('NaN', 70)))
        self.assertIsNone(ratings.parse_rating(page(5, 70.5)))
        self.assertIsNone(ratings.parse_rating(page(6, 70)))
        self.assertIsNone(ratings.parse_rating(page(5, 70) + page(4.5, 30)))

    def test_failed_home_preserves_feed_and_original_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'ratings.json'
            old = json.dumps({'updated': '2026-07-31T12:00:00Z', 'homes': {}})
            out.write_text(old)
            def broken(url):
                if 'table-rock' in url:
                    raise OSError('upstream unavailable')
                return page()
            self.assertEqual(ratings.main(fetch_page=broken, out=out), 1)
            self.assertEqual(out.read_text(), old)

    def test_sudden_drop_does_not_publish_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'ratings.json'
            original = json.dumps({'homes': {home['key']: {'count': 100} for home in ratings.HOMES}})
            out.write_text(original)
            self.assertEqual(ratings.main(fetch_page=lambda _: page(5, 10), out=out), 1)
            self.assertEqual(out.read_text(), original)

    def test_success_uses_count_weighting_without_float_rounding_error(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'ratings.json'
            now = datetime(2026, 11, 9, 20, tzinfo=timezone.utc)
            self.assertEqual(ratings.main(fetch_page=lambda _: page('4.99', 70), out=out, now=now), 0)
            data = json.loads(out.read_text())
            self.assertEqual(data['average_rating'], 4.99)
            self.assertEqual(data['total_reviews'], 210)
            self.assertTrue(data['all_verified'])
            self.assertTrue(all(home['verified_at'] == data['updated'] for home in data['homes'].values()))

    def test_portfolio_is_review_weighted_not_an_average_of_properties(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'ratings.json'
            values = {home['url']: value for home, value in zip(ratings.HOMES, [(5, 3), (4.8, 7), (4.9, 10)])}
            self.assertEqual(ratings.main(fetch_page=lambda url: page(*values[url]), out=out), 0)
            self.assertEqual(json.loads(out.read_text())['average_rating'], 4.88)

if __name__ == '__main__':
    unittest.main()
