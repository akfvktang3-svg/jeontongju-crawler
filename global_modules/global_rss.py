"""
글로벌 주류 RSS 수집기
직접 검증된 작동 사이트만 포함 (총 8곳)
"""

import time
import re
from datetime import datetime, timezone

try:
    import feedparser
except ImportError:
    feedparser = None

RSS_FEEDS = [
    # ── 위스키/스피릿 ─────────────────────────────
    {
        "source": "The Whisky Wire",
        "url": "https://thewhiskywire.com/feed/",
        "category": "위스키",
    },
    {
        "source": "Irish Whiskey Magazine",
        "url": "https://www.irishwhiskeymagazine.com/feed/",
        "category": "위스키",
    },
    {
        "source": "The Whiskey Wash",
        "url": "https://thewhiskeywash.com/feed/",
        "category": "위스키",
    },
    {
        "source": "The Spirits Business",
        "url": "https://www.thespiritsbusiness.com/feed/",
        "category": "스피릿",
    },
    {
        "source": "Whisky Intelligence",
        "url": "https://www.whiskyintelligence.com/feed/",
        "category": "위스키",
    },
    # ── 와인/음료 ──────────────────────────────────
    {
        "source": "Decanter",
        "url": "https://www.decanter.com/feed/",
        "category": "와인",
    },
    {
        "source": "Wine Industry Advisor",
        "url": "https://wineindustryadvisor.com/feed",
        "category": "와인",
    },
    {
        "source": "The Drinks Business",
        "url": "https://www.thedrinksbusiness.com/feed/",
        "category": "음료업계",
    },
]

MAX_PER_FEED = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}


def _clean(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()[:500]


def _parse_date(entry):
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def fetch_feed(feed_info):
    if feedparser is None:
        return []

    source = feed_info["source"]
    articles = []

    try:
        feed = feedparser.parse(feed_info["url"], request_headers=HEADERS)

        if feed.bozo and not feed.entries:
            exc = getattr(feed, "bozo_exception", "unknown")
            print(f"  FAIL: [{source}] {exc}")
            return []

        for entry in feed.entries[:MAX_PER_FEED]:
            title = _clean(getattr(entry, "title", ""))
            link = getattr(entry, "link", "")
            summary = _clean(getattr(entry, "summary", ""))

            if not title or not link:
                continue

            articles.append({
                "title": title,
                "url": link,
                "summary": summary,
                "pub_date": _parse_date(entry),
                "source": source,
                "category": feed_info["category"],
                "collector": "rss_global",
            })

        print(f"  OK: [{source}] {len(articles)}건 수집")

    except Exception as e:
        print(f"  ERROR: [{source}] {e}")

    return articles


def run():
    print("\n글로벌 RSS 수집 시작...")

    if feedparser is None:
        print("  feedparser 없음: pip install feedparser")
        return []

    all_articles = []
    for feed_info in RSS_FEEDS:
        articles = fetch_feed(feed_info)
        all_articles.extend(articles)
        time.sleep(1)

    from collections import Counter
    counts = Counter(a["category"] for a in all_articles)
    for cat, cnt in counts.items():
        print(f"  {cat}: {cnt}건")

    print(f"RSS 총 수집: {len(all_articles)}건")
    return all_articles
