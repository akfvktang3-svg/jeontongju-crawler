"""
노션 카드뉴스 데이터베이스에 크롤링 결과를 저장하는 모듈
- 기사 제목 / 카테고리 / 한줄요약 / URL / 진행여부(작업전) 저장
- 중복 URL 체크 (같은 기사 중복 저장 방지)
"""

import os
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = "372442a958a380a0996fd8ffa1045d80"
NOTION_API_URL = "https://api.notion.com/v1"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# 크롤러 카테고리 → 노션 카테고리 매핑
CATEGORY_MAP = {
    "막걸리": "전통주",
    "약주": "전통주",
    "과실주": "전통주",
    "증류주": "전통주",
    "전통주": "전통주",
    "기타": "전통주",
    "위스키": "위스키",
    "와인": "와인",
    "스피릿": "스피릿",
    "음료업계": "음료업계",
    "global": "스피릿",  # 글로벌 크롤러 기본값
}

VALID_CATEGORIES = ["전통주", "위스키", "와인", "스피릿", "음료업계"]


def _map_category(raw_category: str) -> str:
    """크롤러 카테고리를 노션 카테고리로 변환"""
    if not raw_category:
        return "전통주"
    mapped = CATEGORY_MAP.get(raw_category.strip(), None)
    if mapped:
        return mapped
    # 직접 매칭 시도
    for valid in VALID_CATEGORIES:
        if valid in raw_category:
            return valid
    return "전통주"


def _is_duplicate(url: str) -> bool:
    """노션 DB에 같은 URL이 이미 있는지 확인"""
    if not url:
        return False
    body = {
        "filter": {
            "property": "URL",
            "url": {"equals": url}
        }
    }
    res = requests.post(
        f"{NOTION_API_URL}/databases/{NOTION_DB_ID}/query",
        headers=HEADERS,
        json=body,
    )
    if res.status_code == 200:
        results = res.json().get("results", [])
        return len(results) > 0
    return False


def save_article(article: dict) -> bool:
    """
    기사 1건을 노션 DB에 저장
    반환: 저장 성공 여부 (True/False)
    """
    title = article.get("title", "").strip()
    url = article.get("url", article.get("link", "")).strip()
    summary = article.get("one_line", article.get("summary", article.get("card_summary", ""))).strip()
    raw_category = article.get("category", "")
    category = _map_category(raw_category)

    if not title:
        return False

    # 중복 체크
    if url and _is_duplicate(url):
        print(f"  [중복 skip] {title[:40]}")
        return False

    # 노션 페이지 생성
    body = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "이름": {
                "title": [{"text": {"content": title}}]
            },
            "카테고리": {
                "select": {"name": category}
            },
            "한줄요약": {
                "rich_text": [{"text": {"content": summary[:2000]}}]
            },
            "URL": {
                "url": url if url else None
            },
            "진행여부": {
                "select": {"name": "작업전"}
            },
        }
    }

    res = requests.post(
        f"{NOTION_API_URL}/pages",
        headers=HEADERS,
        json=body,
    )

    if res.status_code == 200:
        print(f"  [노션 저장] {title[:40]}")
        return True
    else:
        print(f"  [노션 오류] {res.status_code} / {title[:40]}")
        print(f"             {res.text[:200]}")
        return False


def save_articles(articles: list) -> dict:
    """
    기사 목록을 노션 DB에 일괄 저장
    반환: {"saved": 저장 수, "skipped": 중복 수, "failed": 실패 수}
    """
    saved, skipped, failed = 0, 0, 0

    for article in articles:
        url = article.get("url", article.get("link", ""))
        if url and _is_duplicate(url):
            skipped += 1
            continue
        result = save_article(article)
        if result:
            saved += 1
        else:
            failed += 1

    print(f"\n노션 저장 완료: 저장 {saved}건 / 중복 skip {skipped}건 / 실패 {failed}건")
    return {"saved": saved, "skipped": skipped, "failed": failed}
