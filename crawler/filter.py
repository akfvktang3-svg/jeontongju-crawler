"""
Claude 기반 2차 필터 (뉴스 전용)
- RSS 글로벌 기사: 키워드 필터 건너뛰고 Claude 필터만 적용
- 국내 기사: 키워드 필터 → Claude 필터
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 국내 전통주 키워드 필터
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEWS_REQUIRED_KR = [
    "전통주", "막걸리", "약주", "청주", "탁주", "동동주",
    "전통소주", "우리술", "한국술", "양조장", "증류소",
    "과실주", "민속주", "전통 술", "주류",
]

NEWS_EXCLUDE_KR = [
    "술잔", "와인잔", "맥주잔", "안주", "술집",
    "칵테일", "일본술", "사케", "맥주", "소맥",
]


def _is_global_article(article: dict) -> bool:
    return article.get("collector") == "rss_global"


def keyword_filter_news(articles: list[dict]) -> list[dict]:
    result = []
    for article in articles:
        # RSS 글로벌 기사 → 키워드 필터 건너뜀 (전문 사이트에서 수집했으므로)
        if _is_global_article(article):
            result.append(article)
            continue

        # 국내 기사 → 키워드 필터 적용
        text = (
            article.get("title", "") + " " +
            article.get("summary", article.get("description", ""))
        ).lower()

        if any(kw in text for kw in NEWS_EXCLUDE_KR):
            continue
        if any(kw in text for kw in NEWS_REQUIRED_KR):
            result.append(article)

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Claude 2차 필터
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def claude_filter_news(articles: list[dict]) -> list[dict]:
    if not articles:
        return []

    # 국내/글로벌 분리
    kr_articles = [(i, a) for i, a in enumerate(articles) if not _is_global_article(a)]
    global_articles = [(i, a) for i, a in enumerate(articles) if _is_global_article(a)]

    print(f"  Claude 뉴스 필터링 중... (국내: {len(kr_articles)}건 / 글로벌: {len(global_articles)}건)")
    passed_indices = set()
    batch_size = 10

    # 국내 기사 필터
    for i in range(0, len(kr_articles), batch_size):
        chunk = kr_articles[i:i + batch_size]
        passed = _claude_filter_kr([a for _, a in chunk])
        for j, (orig_idx, _) in enumerate(chunk):
            if j < len(passed) and passed[j]:
                passed_indices.add(orig_idx)

    # 글로벌 기사 필터
    for i in range(0, len(global_articles), batch_size):
        chunk = global_articles[i:i + batch_size]
        passed = _claude_filter_global([a for _, a in chunk])
        for j, (orig_idx, _) in enumerate(chunk):
            if j < len(passed) and passed[j]:
                passed_indices.add(orig_idx)

    result = [articles[i] for i in range(len(articles)) if i in passed_indices]
    removed = len(articles) - len(result)
    print(f"  필터 완료: {len(result)}건 통과 / {removed}건 제거")
    return result


def _claude_filter_kr(batch: list[dict]) -> list[bool]:
    items_text = "\n".join(
        f"[{i+1}] 제목: {a.get('title','')[:80]} / "
        f"요약: {a.get('summary', a.get('description',''))[:100]}"
        for i, a in enumerate(batch)
    )
    prompt = f"""당신은 전통주/우리술 전문 미디어 편집장입니다.
아래 기사들이 전통주·우리술과 직접 관련된 기사인지 판단해주세요.

통과: 전통주, 막걸리, 약주, 청주, 우리술, 양조장 등 한국 전통 주류 기사
탈락: 전통주와 무관한 일반 뉴스, 단순히 "술"만 포함된 기사

기사 목록:
{items_text}

반드시 아래 JSON 형식으로만 답하세요:
[{{"index": 1, "pass": true}}, {{"index": 2, "pass": false}}, ...]"""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        results = json.loads(raw)
        passed = [False] * len(batch)
        for r in results:
            idx = r["index"] - 1
            if 0 <= idx < len(batch):
                passed[idx] = r.get("pass", False)
        return passed
    except Exception as e:
        print(f"  WARNING: 국내 Claude 필터 오류: {e} -> 전체 통과 처리")
        return [True] * len(batch)


def _claude_filter_global(batch: list[dict]) -> list[bool]:
    items_text = "\n".join(
        f"[{i+1}] Title: {a.get('title','')[:80]} / "
        f"Summary: {a.get('summary', a.get('description',''))[:100]}"
        for i, a in enumerate(batch)
    )
    prompt = f"""You are an expert editor for a global liquor industry media.
Determine if each article is valuable news about the global spirits/wine/whisky/liquor industry.

PASS: Whisky, wine, spirits industry news, new product releases, market trends, distillery/winery news, awards
REJECT: General food/beverage news unrelated to spirits, low-quality SEO articles

Articles:
{items_text}

Reply ONLY in this JSON format:
[{{"index": 1, "pass": true}}, {{"index": 2, "pass": false}}, ...]"""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        results = json.loads(raw)
        passed = [False] * len(batch)
        for r in results:
            idx = r["index"] - 1
            if 0 <= idx < len(batch):
                passed[idx] = r.get("pass", False)
        return passed
    except Exception as e:
        print(f"  WARNING: 글로벌 Claude 필터 오류: {e} -> 전체 통과 처리")
        return [True] * len(batch)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 통합 실행 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def filter_news(articles: list[dict]) -> list[dict]:
    """
    국내 기사: 키워드 필터 → Claude 필터
    글로벌 RSS 기사: Claude 필터만 적용 (키워드 필터 건너뜀)
    """
    after_keyword = keyword_filter_news(articles)
    after_claude = claude_filter_news(after_keyword)
    return after_claude
