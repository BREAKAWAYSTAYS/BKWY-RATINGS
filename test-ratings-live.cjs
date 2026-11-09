const {test} = require('node:test');
const assert = require('node:assert/strict');
const {validateFeed, labels} = require('./ratings-live.js');
const fixture = {updated: '2026-11-08T17:04:05Z', total_reviews: 210, average_rating: 4.99, homes: {
  'lake-hamilton': {rating: 5, count: 65},
  'hot-springs': {rating: 4.99, count: 93},
  'table-rock': {rating: 5, count: 52}
}};
test('accepts the published feed and labels it as guest reviews', () => {
  assert.equal(validateFeed(fixture).total_reviews, 210);
  assert.match(labels(fixture, Date.parse(fixture.updated)).total, /^Guest reviews/);
  assert.doesNotMatch(labels(fixture).total, /Airbnb/);
});
test('rejects incomplete, inconsistent and future-dated feeds', () => {
  const incomplete = structuredClone(fixture); delete incomplete.homes['table-rock'];
  assert.throws(() => validateFeed(incomplete));
  const inconsistent = structuredClone(fixture); inconsistent.total_reviews++;
  assert.throws(() => validateFeed(inconsistent));
  const future = structuredClone(fixture); future.updated = '2999-01-01T00:00:00Z';
  assert.throws(() => validateFeed(future));
});
test('a stale feed keeps its real date and is labeled last verified', () => {
  const text = labels(fixture, Date.parse(fixture.updated) + 72 * 60 * 60 * 1000);
  assert.match(text.total, /last verified/);
  assert.match(text.date, /2026/);
});
test('version 2 requires each home verified at the portfolio date', () => {
  const unverified = {...structuredClone(fixture), schema_version: 2, all_verified: true};
  for (const home of Object.values(unverified.homes)) delete home.verified_at;
  assert.throws(() => validateFeed(unverified));
});
