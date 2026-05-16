import time
import re
from datetime import datetime, timezone

try:
    import feedparser
except ImportError:
    feedparser = None


RSS_FEEDS = [
    {
        "source": "The Whisky Wash",
        "url": "https://thewhiskywash.com/feed/",
        "category": "whisky",
        "language": "en",
    },
    {
        "source": "Whisky Magazine",
        "url": "https://www.whiskymag.com/feed/",
        "category": "whisky",
        "language": "en",
    },
    {
        "source": "Scotch Whisky Association",
        "url": "https://www.scotch-whisky.org.uk/feed/",
        "category": "whisky",
        "language": "en",
    },
    {
        "source": "Decanter",
        "url": "https://www.decanter.com/feed/",
        "category": "wine",
        "language": "en",
    },
    {
        "source": "Wine Business",
        "url": "https://www.winebusiness.com/rss/news.cfm",
        "category": "wine",
        "language": "en",
    },
    {
        "source": "Wine Industry Advisor",
        "url": "https://wineindustryadvisor.com/feed",
        "category": "wine",
        "language": "en",
    },
]

MAX_ARTICLES_PER_FEED = 10

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
}


def _parse_date(entry):
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


def fetch_rss_feed(feed_info):
    if feedparser is None:
        print("  feedparser not installed: pip install feedparser")
        return []

    source = feed_info["source"]
    url = feed_info["url"]
    articles = []

    try:
        feed = feedparser.parse(url, request_headers=BROWSER_HEADERS)

        if feed.bozo and not feed.entries:
            exc = getattr(feed, "bozo_exception", "unknown error")
            print(f"  WARNING: [{source}] RSS parse failed: {exc}")
            return []

        for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
            title = _clean_text(getattr(entry, "title", ""))
            link = getattr(entry, "link", "")
            summary = _clean_text(getattr(entry, "summary", ""))

            if not title or not link:
                continue

            article = {
                "title": title,
                "link": link,
                "url": link,
                "description": summary,
                "summary": summary,
                "pub_date": _parse_date(entry),
                "source": source,
                "category": feed_info["category"],
                "language": feed_info["language"],
                "collector": "rss_global",
            }
            articles.append(article)

        print(f"  OK: [{source}] {len(articles)} articles")

    except Exception as e:
        print(f"  ERROR: [{source}] {type(e).__name__}: {e}")

    return articles


def run():
    print("\nGlobal RSS collection started...")

    if feedparser is None:
        print("  feedparser not installed: pip install feedparser")
        return []

    all_articles = []

    for feed_info in RSS_FEEDS:
        articles = fetch_rss_feed(feed_info)
        all_articles.extend(articles)
        time.sleep(1)

    from collections import Counter
    counts = Counter(a["category"] for a in all_articles)
    for cat, cnt in counts.items():
        print(f"  {cat}: {cnt} articles")

    print(f"RSS total: {len(all_articles)} articles")
    return all_articles


if __name__ == "__main__":
    results = run()
    if results:
        print(f"\nSample (top 3):")
        for article in results[:3]:
            print(f"\n[{article['source']}] [{article['category']}]")
            print(f"Title: {article['title']}")
            print(f"Link: {article['link']}")
    else:
        print("\nNo articles collected")
