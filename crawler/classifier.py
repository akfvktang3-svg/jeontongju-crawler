"""
Claude 기반 기사 카테고리 분류 (Phase 2: 글로벌 주류 확장)

변경사항 (Phase 2):
- 기존 전통주 카테고리 5개 유지
- 글로벌 주류 카테고리 4개 추가 (총 9개)
- 글로벌 기사는 별도 프롬프트로 분류
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 카테고리 정의
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 국내 전통주 카테고리 (기존 유지)
KR_CATEGORIES = [
    "신제품 출시",
    "행사 소식",
    "주류 트렌드",
    "브랜드 이야기",
    "기타",
]

# 글로벌 주류 카테고리 (Phase 2 신규)
GLOBAL_CATEGORIES = [
    "위스키",       # Whisky/Whiskey/Scotch/Bourbon
    "와인",         # Wine/Vineyard
    "스피릿",       # Gin/Rum/Vodka/Tequila etc.
    "글로벌 트렌드", # RTD/Low ABV/Industry trends
    "기타",
]

# 전체 카테고리 (구글 시트 탭 구성용)
ALL_CATEGORIES = KR_CATEGORIES[:-1] + GLOBAL_CATEGORIES  # 중복 '기타' 제거


def _is_global_article(article: dict) -> bool:
    """RSS 수집기에서 온 글로벌 기사 여부 확인"""
    return article.get("collector") == "rss_global"


def _classify_kr_batch(batch: list[dict]) -> list[dict]:
    """국내 전통주 기사 분류 (기존 로직)"""
    items_text = "\n".join(
        f"[{i+1}] 제목: {a.get('title','')[:80]}"
        for i, a in enumerate(batch)
    )

    prompt = f"""당신은 전통주/우리술 전문 미디어 편집장입니다.
아래 기사들을 다음 카테고리 중 하나로 분류해주세요.

카테고리:
- 신제품 출시: 새로운 전통주 제품 출시 소식
- 행사 소식: 축제, 박람회, 이벤트, 시음회 등
- 주류 트렌드: 시장 동향, 소비 트렌드, 통계, 정책
- 브랜드 이야기: 양조장 스토리, 명인, 인터뷰, 역사
- 기타: 위에 해당하지 않는 전통주 관련 기사

기사 목록:
{items_text}

반드시 아래 JSON 형식으로만 답하세요:
[{{"index": 1, "category": "신제품 출시"}}, {{"index": 2, "category": "행사 소식"}}, ...]"""

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
            idx = r["index"] - 1
            if 0 <= idx < len(batch):
                batch[idx]["category"] = r.get("category", "기타")
        return batch
    except Exception as e:
        print(f"  ⚠️ 국내 분류 오류: {e}")
        for a in batch:
            a.setdefault("category", "기타")
        return batch


def _classify_global_batch(batch: list[dict]) -> list[dict]:
    """글로벌 주류 기사 분류 (Phase 2 신규)"""
    items_text = "\n".join(
        f"[{i+1}] Title: {a.get('title','')[:80]}"
        for i, a in enumerate(batch)
    )

    prompt = f"""You are an expert editor for a global spirits and wine industry publication.
Classify each article into one of the following categories:

Categories:
- 위스키: Whisky, whiskey, scotch, bourbon, single malt, blended
- 와인: Wine, vineyard, winery, vintage, champagne
- 스피릿: Gin, rum, vodka, tequila, cognac, brandy, mezcal
- 글로벌 트렌드: RTD cocktails, low ABV, hard seltzer, industry trends, regulations, market data
- 기타: Other liquor industry news not fitting above

Articles:
{items_text}

Reply ONLY in this JSON format:
[{{"index": 1, "category": "위스키"}}, {{"index": 2, "category": "와인"}}, ...]"""

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
            idx = r["index"] - 1
            if 0 <= idx < len(batch):
                batch[idx]["category"] = r.get("category", "기타")
                batch[idx]["is_global"] = True  # 글로벌 기사 표시
        return batch
    except Exception as e:
        print(f"  ⚠️ 글로벌 분류 오류: {e}")
        for a in batch:
            a.setdefault("category", "글로벌 트렌드")
            a["is_global"] = True
        return batch


def classify_articles(articles: list[dict]) -> list[dict]:
    """
    전체 기사 분류 실행
    - 국내 기사: 전통주 5개 카테고리
    - 글로벌 기사: 주류 5개 카테고리
    """
    if not articles:
        return []

    print(f"\n🏷️  기사 분류 중... ({len(articles)}건)")

    # 국내/글로벌 분리
    kr_articles = [(i, a) for i, a in enumerate(articles) if not _is_global_article(a)]
    global_articles = [(i, a) for i, a in enumerate(articles) if _is_global_article(a)]

    result = list(articles)  # 원본 순서 유지용 복사

    # 국내 기사 분류
    if kr_articles:
        print(f"  📰 국내 기사 분류 중... ({len(kr_articles)}건)")
        batch_size = 10
        for i in range(0, len(kr_articles), batch_size):
            chunk = [a for _, a in kr_articles[i:i + batch_size]]
            classified = _classify_kr_batch(chunk)
            for j, (orig_idx, _) in enumerate(kr_articles[i:i + batch_size]):
                result[orig_idx] = classified[j]

    # 글로벌 기사 분류
    if global_articles:
        print(f"  🌍 글로벌 기사 분류 중... ({len(global_articles)}건)")
        batch_size = 10
        for i in range(0, len(global_articles), batch_size):
            chunk = [a for _, a in global_articles[i:i + batch_size]]
            classified = _classify_global_batch(chunk)
            for j, (orig_idx, _) in enumerate(global_articles[i:i + batch_size]):
                result[orig_idx] = classified[j]

    # 분류 결과 요약
    from collections import Counter
    counts = Counter(a.get("category", "기타") for a in result)
    print("  📊 분류 결과:")
    for cat, cnt in counts.most_common():
        print(f"    {cat}: {cnt}건")

    return result
