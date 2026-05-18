"""
Claude 기반 2차 필터 (뉴스 전용 - 쇼핑 필터 삭제)
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1차 필터: 키워드 기반
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEWS_REQUIRED_KR = [
    "전통주", "막걸리", "약주", "청주", "탁주", "동동주",
    "전통소주", "우리술", "한국술", "양조장", "증류소",
    "과실주", "민속주", "전통 술", "주류",
]

NEWS_EXCLUDE_KR = [
    "술잔", "와인잔", "맥주잔", "안주", "술집",
    "칵테일", "일본술", "사케", "맥주", "소맥", "보자기",
]

NEWS_REQUIRED_GLOBAL = [
    "whisky", "whiskey", "scotch", "bourbon", "distillery",
    "single malt", "blended", "cask",
    "wine", "vineyard", "winery", "vintage", "sommelier",
    "spirits", "rum", "gin", "vodka", "tequila",
    "craft beer", "brewery", "liquor industry",
]


def _is_global_article(article: dict) -> bool:
    return article.get("collector") == "rss_global"


def keyword_filter_news(articles: list[dict]) -> list[dict]:
    result = []
    for article in articles:
        # RSS 기사: summary/description 둘 다 확인
        text = (
            article.get("title", "") + " " +
            article.get("summary", article.get("description", ""))
        ).lower()

        if _is_global_article(article):
            if any(kw in text for kw in NEWS_REQUIRED_GLOBAL):
                result.append(article)
        else:
            if any(kw in text for kw in NEWS_EXCLUDE_KR):
                continue
            if any(kw in text for kw in NEWS_REQUIRED_KR):
                result.append(article)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2차 필터: Claude 기반
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def claude_filter_news(articles: list[dict]) -> list[dict]:
    if not articles:
        return []

    print(f"  Claude 뉴스 필터링 중... ({len(articles)}건)")
    passed = []
    batch_size = 10

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        filtered = _claude_filter_batch(batch)
        passed.extend(filtered)

    removed = len(articles) - len(passed)
    print(f"  뉴스 필터 완료: {len(passed)}건 통과 / {removed}건 제거")
    return passed


def _claude_filter_batch(batch: list[dict]) -> list[dict]:
    kr_batch = [(i, a) for i, a in enumerate(batch) if not _is_global_article(a)]
    global_batch = [(i, a) for i, a in enumerate(batch) if _is_global_article(a)]
    passed_indices = set()

    # 국내 기사 필터
    if kr_batch:
        items_text = "\n".join(
            f"[{i+1}] 제목: {a.get('title','')[:80]} / "
            f"요약: {a.get('summary', a.get('description',''))[:100]}"
            for i, a in kr_batch
        )
        prompt = f"""당신은 전통주/우리술 전문 미디어 편집장입니다.
아래 기사들이 전통주·우리술과 직접 관련된 기사인지 판단해주세요.

통과: 전통주, 막걸리, 약주, 청주, 우리술, 양조장 등 한국 전통 주류 관련 기사
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
            for r in results:
                if r.get("pass"):
                    orig_idx = kr_batch[r["index"] - 1][0]
                    passed_indices.add(orig_idx)
        except Exception as e:
            print(f"  WARNING: Claude 필터 오류: {e} -> 키워드 필터 결과 유지")
            for i, _ in kr_batch:
                passed_indices.add(i)

    # 글로벌 기사 필터
    if global_batch:
        items_text = "\n".join(
            f"[{i+1}] Title: {a.get('title','')[:80]} / "
            f"Summary: {a.get('summary', a.get('description',''))[:100]}"
            for i, a in global_batch
        )
        prompt = f"""You are an expert editor for a global liquor industry media.
Determine if each article is valuable news about the global spirits/wine/liquor industry.

PASS: Whisky, wine, spirits industry news, new products, market trends, distillery/winery news
REJECT: General food/beverage news, low-quality SEO articles, no real news value

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
            for r in results:
                if r.get("pass"):
                    orig_idx = global_batch[r["index"] - 1][0]
                    passed_indices.add(orig_idx)
        except Exception as e:
            print(f"  WARNING: Claude 글로벌 필터 오류: {e} -> 키워드 필터 결과 유지")
            for i, _ in global_batch:
                passed_indices.add(i)

    return [batch[i] for i in range(len(batch)) if i in passed_indices]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 통합 실행 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def filter_news(articles: list[dict]) -> list[dict]:
    after_keyword = keyword_filter_news(articles)
    after_claude = claude_filter_news(after_keyword)
    return after_claude
