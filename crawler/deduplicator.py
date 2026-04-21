"""
중복 제거 필터
여러 검색엔진에서 수집된 기사의 중복을 다단계로 걸러냅니다.

중복 판단 기준 (3단계):
  1단계: URL이 완전히 동일한 것
  2단계: 제목이 완전히 동일한 것
  3단계: 제목이 70% 이상 유사한 것 (같은 기사를 다르게 표현한 경우)
"""

import re
from difflib import SequenceMatcher


def remove_duplicates(articles: list[dict]) -> tuple[list[dict], dict]:
    """
    3단계 중복 제거 실행
    반환값: (중복 제거된 기사 목록, 제거 통계)
    """
    original_count = len(articles)

    # 1단계: URL 중복 제거
    after_url = _dedup_by_url(articles)
    url_removed = original_count - len(after_url)

    # 2단계: 제목 완전 일치 중복 제거
    after_exact = _dedup_by_exact_title(after_url)
    exact_removed = len(after_url) - len(after_exact)

    # 3단계: 제목 유사도 기반 중복 제거
    after_similar = _dedup_by_similar_title(after_exact, threshold=0.7)
    similar_removed = len(after_exact) - len(after_similar)

    stats = {
        "원본":         original_count,
        "URL중복제거":  url_removed,
        "제목중복제거": exact_removed,
        "유사중복제거": similar_removed,
        "최종":         len(after_similar),
    }

    return after_similar, stats


# ── 1단계: URL 중복 제거 ───────────────────────────────────────

def _dedup_by_url(articles: list[dict]) -> list[dict]:
    """완전히 동일한 URL 제거"""
    seen_urls = set()
    result = []
    for a in articles:
        url = _normalize_url(a.get("url", ""))
        if url and url not in seen_urls:
            seen_urls.add(url)
            result.append(a)
        elif not url:
            result.append(a)  # URL 없는 건 일단 통과
    return result


def _normalize_url(url: str) -> str:
    """URL 정규화 (파라미터 제거해서 비교)"""
    # 트래킹 파라미터 제거
    url = re.sub(r"\?.*$", "", url)
    # www. 제거
    url = re.sub(r"https?://(www\.)?", "", url)
    # 끝 슬래시 제거
    url = url.rstrip("/")
    return url.lower().strip()


# ── 2단계: 제목 완전 일치 제거 ────────────────────────────────

def _dedup_by_exact_title(articles: list[dict]) -> list[dict]:
    """정규화된 제목이 완전히 동일한 것 제거"""
    seen_titles = set()
    result = []
    for a in articles:
        title = _normalize_title(a.get("title", ""))
        if title and title not in seen_titles:
            seen_titles.add(title)
            result.append(a)
    return result


def _normalize_title(title: str) -> str:
    """제목 정규화"""
    # HTML 태그 제거
    title = re.sub(r"<[^>]+>", "", title)
    # 특수문자 제거
    title = re.sub(r"[^\w\s가-힣]", "", title)
    # 공백 정리
    title = re.sub(r"\s+", " ", title)
    # 언론사 이름 패턴 제거 (예: "[연합뉴스]", "(조선일보)")
    title = re.sub(r"[\[\(][^\]\)]+[\]\)]", "", title)
    return title.strip().lower()


# ── 3단계: 유사도 기반 중복 제거 ──────────────────────────────

def _dedup_by_similar_title(articles: list[dict], threshold: float = 0.7) -> list[dict]:
    """
    제목 유사도가 threshold 이상이면 중복으로 판단
    유사한 기사 중 더 좋은 출처(네이버뉴스 > 구글검색 > 네이버쇼핑)를 남김
    """
    # 출처 우선순위
    source_priority = {
        "네이버뉴스": 1,
        "구글검색":   2,
        "네이버쇼핑": 3,
    }

    result = []
    used_indices = set()

    for i, article_a in enumerate(articles):
        if i in used_indices:
            continue

        # i번 기사와 유사한 기사들 모두 찾기
        group = [i]
        title_a = _normalize_title(article_a.get("title", ""))

        for j, article_b in enumerate(articles):
            if j <= i or j in used_indices:
                continue
            title_b = _normalize_title(article_b.get("title", ""))
            similarity = _calc_similarity(title_a, title_b)
            if similarity >= threshold:
                group.append(j)

        # 그룹 중 가장 좋은 출처의 기사 하나만 남기기
        best_idx = _pick_best(articles, group, source_priority)
        result.append(articles[best_idx])

        for idx in group:
            used_indices.add(idx)

    return result


def _calc_similarity(a: str, b: str) -> float:
    """두 문자열의 유사도 계산 (0~1)"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _pick_best(articles: list[dict], indices: list[int],
               priority: dict) -> int:
    """그룹 중 가장 좋은 출처의 기사 인덱스 반환"""
    return min(
        indices,
        key=lambda i: priority.get(articles[i].get("source", ""), 99)
    )


# ── 리포트 출력 ────────────────────────────────────────────────

def print_dedup_report(stats: dict):
    """중복 제거 결과 출력"""
    print(f"\n🔄 중복 제거 결과:")
    print(f"  원본 수집:         {stats['원본']}건")
    print(f"  URL 중복 제거:    -{stats['URL중복제거']}건")
    print(f"  제목 중복 제거:   -{stats['제목중복제거']}건")
    print(f"  유사 기사 제거:   -{stats['유사중복제거']}건")
    print(f"  ─────────────────────")
    print(f"  최종 기사:         {stats['최종']}건")
