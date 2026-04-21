"""
구글 검색 수집기
전통주 관련 최신 소식을 구글 Custom Search API로 수집합니다.
"""

import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX      = os.getenv("GOOGLE_CX")

# 전통주/우리술에 집중된 키워드
KEYWORDS = [
    "전통주 신제품 2026",
    "전통주 박람회 행사 2026",
    "전통주 트렌드 2026",
    "막걸리 브랜드 출시 2026",
    "전통주 수출 현황",
    "우리술 페스티벌 2026",
    "전통주 양조장 소식",
    "약주 청주 신제품",
]

# 반드시 포함되어야 할 핵심 키워드
REQUIRED_KEYWORDS = [
    "전통주", "막걸리", "약주", "청주", "탁주", "동동주",
    "전통소주", "우리술", "한국술", "양조장", "증류소",
    "과실주", "민속주",
]

# 제외 키워드
EXCLUDE_KEYWORDS = [
    "술잔", "잔", "보자기", "포장", "안주",
    "술집", "칵테일", "일본술", "사케",
]


def fetch_google_search(keyword: str, num: int = 5) -> list[dict]:
    """구글 Custom Search API로 검색 결과 수집"""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key":          GOOGLE_API_KEY,
        "cx":           GOOGLE_CX,
        "q":            keyword,
        "num":          num,
        "dateRestrict": "m3",
        "lr":           "lang_ko",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        items = response.json().get("items", [])

        results = []
        for item in items:
            title   = item.get("title", "")
            summary = item.get("snippet", "")

            # 전통주 관련 기사만 통과
            if not _is_relevant(title, summary):
                continue

            results.append({
                "title":        title,
                "summary":      summary,
                "url":          item.get("link", ""),
                "source":       "구글검색",
                "keyword":      keyword,
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        return results

    except Exception as e:
        print(f"  ⚠️  구글 검색 오류 [{keyword}]: {e}")
        return []


def run() -> list[dict]:
    """구글 전체 수집 실행"""
    print("\n🔍 구글 검색 수집 중...")
    all_results = []

    for keyword in KEYWORDS:
        results = fetch_google_search(keyword)
        all_results.extend(results)
        if results:
            print(f"  ✅ [{keyword}] {len(results)}건")

    print(f"\n  📦 구글 총 수집: {len(all_results)}건")
    return all_results


def _is_relevant(title: str, summary: str) -> bool:
    """전통주 관련 기사인지 판단"""
    text = title + " " + summary
    if any(kw in text for kw in EXCLUDE_KEYWORDS):
        return False
    return any(kw in text for kw in REQUIRED_KEYWORDS)


def _clean(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()
