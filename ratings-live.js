(function () {
  'use strict';
  const KEYS = ['lake-hamilton', 'hot-springs', 'table-rock'];
  const FEED = 'https://raw.githubusercontent.com/BREAKAWAYSTAYS/BKWY-RATINGS/main/ratings.json';
  const REFRESH_MS = 5 * 60 * 1000;

  function validateFeed(data, now = Date.now()) {
    if (!data || !data.homes || !KEYS.every(key => data.homes[key])) throw new Error('Incomplete review feed');
    const updated = Date.parse(data.updated);
    if (!Number.isFinite(updated) || updated > now + 10 * 60 * 1000) throw new Error('Invalid verification date');
    let count = 0;
    for (const key of KEYS) {
      const home = data.homes[key];
      if (!Number.isInteger(home.count) || home.count <= 0 || home.count > 1000000 || !Number.isFinite(home.rating) || home.rating <= 0 || home.rating > 5) throw new Error('Invalid property review totals');
      count += home.count;
    }
    if (count !== data.total_reviews || !Number.isFinite(data.average_rating) || data.average_rating <= 0 || data.average_rating > 5) throw new Error('Invalid portfolio totals');
    if (data.schema_version >= 2 && (data.all_verified !== true || !KEYS.every(key => data.homes[key].verified_at === data.updated))) throw new Error('Unverified review feed');
    return data;
  }

  function labels(data, now = Date.now()) {
    const date = new Intl.DateTimeFormat('en-US', {timeZone: 'America/Chicago', month: 'short', day: 'numeric', year: 'numeric'}).format(new Date(data.updated));
    const qualifier = now - Date.parse(data.updated) > 48 * 60 * 60 * 1000 ? 'last verified' : 'checked';
    return {total: `Guest reviews · ${qualifier} ${date}`, average: `Average guest rating · ${qualifier} ${date}`, date};
  }

  if (typeof module === 'object' && module.exports) module.exports = {validateFeed, labels};
  if (typeof document === 'undefined') return;
  if (window.__basReviewStatsStarted) return;
  window.__basReviewStatsStarted = true;
  let latest = null, timer = null, inFlight = false;
  function put(node, value) { if (node && node.textContent !== value) node.textContent = value; }
  function render() {
    if (!latest) return;
    const text = labels(latest);
    put(document.querySelector('[data-bas-review-total]'), latest.total_reviews.toLocaleString('en-US'));
    put(document.querySelector('[data-bas-review-average]'), latest.average_rating.toFixed(2) + '★');
    put(document.querySelector('[data-bas-review-total-label]'), text.total);
    put(document.querySelector('[data-bas-review-average-label]'), text.average);
    for (const key of KEYS) {
      const home = latest.homes[key];
      for (const badge of document.querySelectorAll(`[data-bas-review-summary="${key}"]`)) {
        put(badge, home.rating.toFixed(2) + '★ · ' + home.count + ' guest reviews');
        badge.title = 'OwnerRez public guest-review aggregate; verified ' + text.date;
      }
    }
    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
      let graph;
      try { graph = JSON.parse(script.textContent); } catch (_) { continue; }
      let changed = false;
      function visit(item) {
        if (Array.isArray(item)) { item.forEach(visit); return; }
        if (!item || typeof item !== 'object') return;
        const types = Array.isArray(item['@type']) ? item['@type'] : [item['@type']];
        if (types.some(type => type === 'LodgingBusiness' || type === 'VacationRental')) {
          const key = KEYS.find(key => item.name && (key === 'lake-hamilton' ? /lake hamilton/i : key === 'hot-springs' ? /hot springs breakaway/i : /table rock/i).test(item.name));
          if (key) {
            const rating = {'@type': 'AggregateRating', ratingValue: latest.homes[key].rating, reviewCount: latest.homes[key].count, bestRating: 5, worstRating: 1};
            if (JSON.stringify(item.aggregateRating) !== JSON.stringify(rating)) { item.aggregateRating = rating; changed = true; }
          }
        }
        Object.values(item).forEach(visit);
      }
      visit(graph);
      if (changed) script.textContent = JSON.stringify(graph);
    }
  }
  async function refresh() {
    clearTimeout(timer);
    if (inFlight || document.hidden) { timer = setTimeout(refresh, REFRESH_MS); return; }
    inFlight = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    let retry = REFRESH_MS;
    try {
      const response = await fetch(FEED + '?check=' + Math.floor(Date.now() / REFRESH_MS), {cache: 'no-store', credentials: 'omit', referrerPolicy: 'no-referrer', signal: controller.signal});
      if (!response.ok) throw new Error('Review feed HTTP ' + response.status);
      latest = validateFeed(await response.json());
      render();
    } catch (error) {
      retry = 30000;
      console.warn('Breakaway review refresh unavailable; retaining verified figures.', error.message);
    } finally {
      clearTimeout(timeout);
      inFlight = false;
      timer = setTimeout(refresh, retry);
    }
  }
  new MutationObserver(render).observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', refresh, {once: true});
  else refresh();
}());
