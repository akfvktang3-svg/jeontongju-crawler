"""
글로벌 주류 전문 사이트 RSS 수집기
Phase 1: 기존 크롤러에 영향 없이 새 수집원 추가
"""

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
        "category": "위스키",
        "language": "en",
    },
    {
        "source": "Whisky Magazine",
        "url": "https://www.whiskymag.com/feed/",
        "category": "위스키",
        "language": "en",
    },
    {
        "source": "Scotch Whisky Association",
        "url": "https://www.scotch-whisky.org.uk/feed/",
        "category": "위스키",
        "language": "en",
    },
    {
        "source": "Decanter",
        "url": "https://www.decanter.com/feed/",
        "category": "와인",
        "language": "en",
    },
    {
        "source": "Wine Business",
        "url": "https://www.winebusiness.com/rss/news.cfm",
        "category": "와인",
        "language": "en",
    },
    {
        "source": "Wine Industry Advisor",
        "url": "https://wineindustryadvisor.com/feed",
        "category": "와인",
        "language": "en",
    },
]

MAX_ARTICLES_PER_FEED = 10

# 실제 브라우저처럼 위장하는 헤더
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
        print("  WARNING: feedparser 미설치: pip install feedparser")
        return []

    source = feed_info["source"]
    url = feed_info["url"]
    articles = []

    try:
        # 브라우저처럼 위장한 헤더로 요청
        feed = feedparser.parse(url, request_headers=BROWSER_HEADERS)

        if feed.bozo and not feed.entries:
            # bozo_exception 내용도 출력해서 디버깅 도움
            exc = getattr(feed, "bozo_exception", "알 수 없는 오류")
            print(f"  WARNING: [{source}] RSS 파싱 실패: {exc}")
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
                "description": summary,
                "summary": summary,
                "pub_date": _parse_date(entry),
                "source": source,
                "category": feed_info["category"],
                "language": feed_info["language"],
                "collector": "rss_global",
            }
            articles.append(article)

        print(f"  OK: [{source}] {len(articles)}건 수집")

    except Exception as e:
        print(f"  ERROR: [{source}] 수집 오류: {type(e).__name__}: {e}")

    return articles


def run():
    print("\n글로벌 RSS 수집 시작...")

    if feedparser is None:
        print("  WARNING: feedparser 미설치. 설치 명령: pip install feedparser")
        return []

    all_articles = []

    for feed_info in RSS_FEEDS:
        articles = fetch_rss_feed(feed_info)
        all_articles.extend(articles)
        time.sleep(1)  # 요청 간격 늘림 (차단 방지)

    from collections import Counter
    counts = Counter(a["category"] for a in all_articles)
    for cat, cnt in counts.items():
        print(f"  카테고리 {cat}: {cnt}건")

    print(f"RSS 총 수집: {len(all_articles)}건")
    return all_articles


if __name__ == "__main__":
    results = run()
    if results:
        print(f"\n수집 결과 샘플 (상위 3건):")
        for article in results[:3]:
            print(f"\n[{article['source']}] [{article['category']}]")
            print(f"제목: {article['title']}")
            print(f"링크: {article['link']}")
    else:
        print("\nWARNING: 수집된 기사 없음")
