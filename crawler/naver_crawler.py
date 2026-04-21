"""
네이버 뉴스 + 쇼핑 수집기
전통주 관련 최신 뉴스를 네이버 API로 수집합니다.
"""

import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID     = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 검색 키워드 - 전통주/우리술에 집중
KEYWORDS = [
    "전통주 신제품",
    "전통주 출시",
    "막걸리 신제품",
    "전통주 박람회",
    "전통주 시음회",
    "우리술 행사",
    "전통주 트렌드",
    "약주 출시",
    "전통주 수출",
    "전통주 양조장",
    "막걸리 출시",
    "전통소주 출시",
    "청주 신제품",
    "전통주 한정판",
]

# 반드시 포함되어야 할 핵심 키워드 (하나라도 있어야 통과)
REQUIRED_KEYWORDS = [
    "전통주", "막걸리", "약주", "청주", "탁주", "동동주",
    "전통소주", "우리술", "한국술", "양조장", "증류소",
    "과실주", "전통 술", "민속주",
]

# 제외할 키워드 (이게 포함되면 무조건 걸러냄)
EXCLUDE_KEYWORDS = [
    "술잔", "잔", "보자기", "포장", "선물세트 박스",
    "안주", "술안주", "술집", "바(bar)", "칵테일",
    "일본술", "사케", "와인잔", "맥주잔",
]


def fetch_naver_news(keyword: str, display: int = 5) -> list[dict]:
    """네이버 뉴스 검색 API로 기사 수집"""
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id":     NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query":   keyword,
        "display": display,
        "sort":    "date",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        items = response.json().get("items", [])

        results = []
        for item in items:
            title   = _clean(item.get("title", ""))
            summary = _clean(item.get("description", ""))

            # 전통주 관련 기사만 통과
            if not _is_relevant(title, summary):
                continue

            results.append({
                "title":        title,
                "summary":      summary,
                "url":          item.get("link", ""),
                "source":       "네이버뉴스",
                "keyword":      keyword,
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        return results

    except Exception as e:
        print(f"  ⚠️  네이버 뉴스 오류 [{keyword}]: {e}")
        return []


def run() -> list[dict]:
    """네이버 뉴스 전체 수집 실행"""
    print("\n📰 네이버 뉴스 수집 중...")
    all_results = []

    for keyword in KEYWORDS:
        news = fetch_naver_news(keyword)
        all_results.extend(news)
        if news:
            print(f"  ✅ [{keyword}] {len(news)}건")

    print(f"\n  📦 네이버 뉴스 총 수집: {len(all_results)}건")
    return all_results


# ── 필터 함수 ─────────────────────────────────────────────────

def _is_relevant(title: str, summary: str) -> bool:
    """전통주 관련 기사인지 판단"""
    text = title + " " + summary

    # 제외 키워드 체크 (있으면 탈락)
    if any(kw in text for kw in EXCLUDE_KEYWORDS):
        return False

    # 필수 키워드 체크 (하나라도 있어야 통과)
    return any(kw in text for kw in REQUIRED_KEYWORDS)


def _clean(text: str) -> str:
    """HTML 태그 제거"""
    return re.sub(r"<[^>]+>", "", text).strip()
