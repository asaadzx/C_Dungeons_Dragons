# ---------------------------------------------------------------------------
# app/news/feeds.py
# Fetch public RSS feeds for the "Global News" section.
#
# Design notes:
#   * Fetches happen with a short timeout so a slow feed never blocks a page.
#   * Results are cached in memory for CACHE_SECONDS so we do not hit the
#     feeds on every page view (they are external services).
#   * Every failure mode is non-fatal: a broken or offline feed is simply
#     skipped, and the page shows the feeds that did work.
# ---------------------------------------------------------------------------

import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html import unescape

import feedparser

# Cache the combined feed result for 15 minutes.
CACHE_SECONDS = 15 * 60

# Feeds chosen to be interesting for high-school students: technology,
# science, space, and general world news. Each entry is (label, url).
FEEDS = [
    ("Hacker News", "https://hnrss.org/frontpage"),
    ("ScienceDaily", "https://www.sciencedaily.com/rss/top/science.xml"),
    ("NASA", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
]

# How long to wait for each feed, in seconds. Feeds are fetched in parallel,
# so the whole refresh takes about this long even though there are several.
FETCH_TIMEOUT = 3

# Simple in-process cache: {"items": [...], "fetched_at": timestamp}.
_cache = {"items": [], "fetched_at": 0.0}


def _clean(text):
    """Strip HTML tags and excess whitespace from a feed summary."""
    if not text:
        return ""
    # Remove tags with a tiny state machine (no extra dependency needed).
    result = []
    inside_tag = False
    for char in text:
        if char == "<":
            inside_tag = True
        elif char == ">":
            inside_tag = False
        elif not inside_tag:
            result.append(char)
    cleaned = unescape("".join(result))
    return " ".join(cleaned.split())


def _fetch_one(url):
    """Fetch and parse a single feed. Returns a list of story dicts."""
    request = urllib.request.Request(url, headers={"User-Agent": "C1-Hub/1.0"})
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
        raw = response.read()
    parsed = feedparser.parse(raw)

    stories = []
    for entry in parsed.entries[:8]:
        stories.append(
            {
                "title": _clean(entry.get("title", "")),
                "link": entry.get("link", ""),
                "summary": _clean(entry.get("summary", ""))[:280],
                "published": entry.get("published", ""),
                "source": "",
            }
        )
    return stories


def get_global_news(force=False):
    """Return a cached list of recent global news stories.

    Each story is a dict with title, link, summary, published and source.
    Stories are sorted newest-first as reported by each feed; we simply
    interleave the feeds so no single source dominates the list.
    """
    now = time.time()
    if not force and _cache["items"] and (now - _cache["fetched_at"]) < CACHE_SECONDS:
        return _cache["items"]

    # Fetch every feed in parallel so one slow feed does not stall the page.
    # Failures are skipped on purpose.
    readings = []
    max_workers = min(len(FEEDS), 8)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [(label, pool.submit(_fetch_one, url)) for label, url in FEEDS]
        for label, future in futures:
            try:
                stories = future.result(timeout=FETCH_TIMEOUT + 1)
            except Exception:  # noqa: BLE001 - any network/parse error is non-fatal
                continue
            for story in stories:
                story["source"] = label
            readings.append(stories)

    # Interleave: take the first story from each feed, then the second, etc.
    combined = []
    index = 0
    while True:
        added = False
        for stories in readings:
            if index < len(stories):
                combined.append(stories[index])
                added = True
        if not added:
            break
        index += 1

    _cache["items"] = combined
    _cache["fetched_at"] = now
    return combined
