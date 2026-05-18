"""
구글 검색 수집기
전통주 관련 최신 소식을 구글 Custom Search API로 수집합니다.
키워드 4개로 경량화 (하루 100건 무료 한도 내 운영)
"""

import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

# 4개로 경량화 (기존 8개 → 4개)
KEYWORDS = [
    "전통주 신제품",
    "전통주 행사 소식",
    "막걸리 브랜드 출시",
    "전통주 트렌드",
]

REQUIRED_KEYWORDS = [
    "전통주", "막걸리", "약주", "청주", "탁주", "동동주",
    "전통소주", "우리술", "한국술", "양조장", "증류소",
    "과실주", "민속주",
]

EXCLUDE_KEYWORDS = [
    "술잔", "잔", "보자기", "포장", "안주", "술집",
    "칵테일", "일본술", "사케",
]


def fetch_google_search(keyword: str, num: int = 5) -> list[dict]:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": keyword,
        "num": num,
        "dateRestrict": "m3",
        "lr": "lang_ko",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        items = response.json().get("items", [])
        results = []
        for item in items:
            title = item.get("title", "")
            summary = item.get("snippet", "")
            if not _is_relevant(title, summary):
                continue
            results.append({
                "title": title,
                "summary": summary,
                "url": item.get("link", ""),
                "source": "구글검색",
                "keyword": keyword,
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        return results
    except Exception as e:
        print(f"  WARNING: 구글 검색 오류 [{keyword}]: {e}")
        return []


def run() -> list[dict]:
    print("\n구글 검색 수집 중...")
    all_results = []
    for keyword in KEYWORDS:
        results = fetch_google_search(keyword)
        all_results.extend(results)
        if results:
            print(f"  [{keyword}] {len(results)}건")
    print(f"\n구글 총 수집: {len(all_results)}건")
    return all_results


def _is_relevant(title: str, summary: str) -> bool:
    text = title + " " + summary
    if any(kw in text for kw in EXCLUDE_KEYWORDS):
        return False
    return any(kw in text for kw in REQUIRED_KEYWORDS)


def _clean(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()
